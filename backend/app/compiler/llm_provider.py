"""LLM provider abstraction for the regulation compiler.

The provider's only job is turning regulation prose into the raw extraction
dict shape (`{"rules": [...], "definitions": [...], "exceptions": [...],
"warnings": [...]}`). It never sees individual records and never makes a
compliance decision -- see app/engine for that boundary.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Protocol

from app.compiler.regulation_parser import split_sections
from app.compiler.rule_extractor import extract_from_sections

logger = logging.getLogger(__name__)

EXTRACTION_INSTRUCTIONS = """You are a regulatory analyst. Read the regulation text \
and extract every rule, definition, and exception as structured JSON.

Return ONLY a JSON object with this exact shape:
{
  "rules": [
    {
      "rule_code": "RULE-001",
      "title": "...",
      "description": "...",
      "rule_type": "THRESHOLD",
      "priority": 100,
      "jurisdiction": "ANY or a specific jurisdiction",
      "effective_from": "YYYY-MM-DD",
      "effective_to": null,
      "conditions": {"all": [{"field": "loan.apr", "operator": "greater_than", "value": 18}]},
      "actions": {"verdict": "FAIL", "action": "REJECT", "message": "..."},
      "source_reference": "§4.2",
      "source_text": "...",
      "confidence": 0.9
    }
  ],
  "definitions": [
    {"term": "...", "definition": "...", "source_reference": "...", "source_text": "..."}
  ],
  "exceptions": [
    {"rule_code": "RULE-001", "description": "...", "conditions": {...}, "source_reference": "...", "source_text": "..."}
  ],
  "warnings": []
}

Valid operators: equals, not_equals, greater_than, greater_than_or_equal, \
less_than, less_than_or_equal, in, not_in, contains, starts_with, is_true, \
is_false, before, after, between, days_since.
"""


class LLMProvider(Protocol):
    async def generate_structured(self, source_text: str, jurisdiction: str) -> dict[str, Any]:
        """Extract structured regulation content from raw source text."""
        ...


class MockLLMProvider:
    """Deterministic stand-in for an LLM.

    Parses the bracket-tagged demo regulation text directly instead of
    calling a model. This lets the entire application run, with meaningful
    results, without any API key -- the default developer experience.
    """

    async def generate_structured(self, source_text: str, jurisdiction: str) -> dict[str, Any]:
        sections = split_sections(source_text)
        result = extract_from_sections(sections)
        if not sections:
            result["warnings"].append(
                "No structured provisions were found in the source text. "
                "The mock compiler expects '=== RULE: CODE | Title ===' style "
                "sections with bracketed tags; a real LLM provider would not "
                "have this restriction."
            )
        return result


class BedrockProvider:
    """Calls an Amazon Bedrock model to perform the extraction.

    Only imports boto3 lazily, and only when actually used, so the mock
    development path never requires AWS credentials or the dependency.
    """

    def __init__(self, region: str, model_id: str):
        if not region or not model_id:
            raise ValueError("AWS_REGION and BEDROCK_MODEL_ID must be set for BedrockProvider")
        self.region = region
        self.model_id = model_id

    async def generate_structured(self, source_text: str, jurisdiction: str) -> dict[str, Any]:
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for the Bedrock provider. Install it with "
                "'pip install boto3'."
            ) from exc

        def _invoke() -> tuple[str, str]:
            # Without explicit timeouts, a stalled connection or a throttled
            # request stuck in botocore's own retry/backoff loop can hang
            # the underlying socket read indefinitely -- this call would
            # then never return, and the HTTP request waiting on it would
            # appear to hang forever with no error. Bound it explicitly.
            client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
                config=Config(
                    connect_timeout=10,
                    read_timeout=180,
                    retries={"max_attempts": 2, "mode": "standard"},
                ),
            )
            response = client.converse(
                modelId=self.model_id,
                system=[{"text": EXTRACTION_INSTRUCTIONS}],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": (
                                    f"Jurisdiction context: {jurisdiction}\n\n"
                                    f"Regulation text:\n{source_text}"
                                )
                            }
                        ],
                    }
                ],
                # A regulation with many extractable rules can produce a
                # large JSON payload; 8192 was cut off mid-document for
                # rule-rich text. The model accepts up to tens of thousands
                # of output tokens, so give it real headroom.
                inferenceConfig={"temperature": 0, "maxTokens": 16384},
            )
            text = response["output"]["message"]["content"][0]["text"]
            stop_reason = response.get("stopReason", "")
            return text, stop_reason

        # boto3 is synchronous; run it off the event loop so a slow model
        # call doesn't block other requests the API is handling. The
        # wait_for is a second, independent bound on top of the client's own
        # read_timeout -- if anything still gets stuck, the request fails
        # cleanly instead of hanging forever (the orphaned worker thread is
        # abandoned, not killed, since Python cannot cancel a running thread).
        try:
            text, stop_reason = await asyncio.wait_for(asyncio.to_thread(_invoke), timeout=200)
        except asyncio.TimeoutError as exc:
            raise RuntimeError(
                "The Bedrock request did not complete within 200 seconds and was "
                "abandoned. This can happen with a very large document or during "
                "AWS throttling -- try a smaller excerpt or retry shortly."
            ) from exc

        truncated = stop_reason == "max_tokens"

        try:
            result = json.loads(text)
            if truncated:
                result.setdefault("warnings", []).append(
                    "The model's response hit the output length limit. It may have "
                    "stopped mid-document -- check whether later sections of the "
                    "regulation are missing rules."
                )
            return result
        except json.JSONDecodeError:
            pass

        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        # Both the direct parse and the outer-brace slice failed -- this is
        # what happens when the response was cut off mid-object (truncated
        # generation, not malformed output). Rather than discarding
        # everything, recover whatever complete rule/definition/exception
        # objects exist before the cutoff.
        salvaged = _salvage_partial_json(text)
        if salvaged is not None:
            if truncated:
                salvaged["warnings"].append(
                    "The model's response was cut off before it finished (output "
                    "length limit reached). Only the rules/definitions/exceptions "
                    "completed before the cutoff were recovered -- the regulation "
                    "likely has more content than was extracted. Try compiling a "
                    "shorter excerpt to capture the rest."
                )
            else:
                salvaged["warnings"].append(
                    "The model's response was not valid JSON and had to be "
                    "partially recovered; some rules, definitions, or exceptions "
                    "may be missing."
                )
            return salvaged

        logger.error("Bedrock extraction returned non-JSON output: %s", text[:2000])
        return {
            "rules": [],
            "definitions": [],
            "exceptions": [],
            "warnings": [
                "The model's response could not be parsed as JSON and no rules "
                "could be recovered."
                + (
                    " The response was cut off at the output length limit before "
                    "any complete provision was written -- try a shorter excerpt."
                    if truncated
                    else ""
                )
            ],
        }


def _salvage_partial_json(text: str) -> dict[str, Any] | None:
    """Best-effort recovery from a truncated or malformed extraction response.

    A model response cut off mid-generation (output length limit) still has
    complete `{...}` objects for the rules/definitions/exceptions it finished
    writing before the cutoff -- only the last, in-progress object and the
    closing brackets are missing. Rather than discard the whole response,
    scan for each top-level array key directly and pull out every object
    that is syntactically complete, stopping at the first incomplete one.
    Returns None if none of the expected keys could even be located.
    """
    result: dict[str, Any] = {"rules": [], "definitions": [], "exceptions": [], "warnings": []}
    found_any_key = False
    for key in ("rules", "definitions", "exceptions"):
        match = re.search(rf'"{key}"\s*:\s*\[', text)
        if not match:
            continue
        found_any_key = True
        result[key] = _extract_complete_objects(text, match.end())
    if not found_any_key:
        return None
    return result


def _extract_complete_objects(text: str, start: int) -> list[dict[str, Any]]:
    """Parse every complete top-level `{...}` object in a JSON array, starting
    just after its opening `[`, stopping at the closing `]` or at the first
    object that is cut off before its matching `}` (bracket-depth and
    string-aware, so braces inside quoted strings don't confuse the count).
    """
    objects: list[dict[str, Any]] = []
    i, n = start, len(text)
    while i < n:
        while i < n and text[i] in " \t\r\n,":
            i += 1
        if i >= n or text[i] != "{":
            break
        obj_start = i
        depth = 0
        in_string = False
        escape = False
        j = i
        closed = False
        while j < n:
            c = text[j]
            if in_string:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    in_string = False
            else:
                if c == '"':
                    in_string = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        closed = True
                        j += 1
                        break
            j += 1
        if not closed:
            break
        try:
            objects.append(json.loads(text[obj_start:j]))
        except json.JSONDecodeError:
            break
        i = j
    return objects


def get_llm_provider() -> LLMProvider:
    from app.config import get_settings

    settings = get_settings()
    if settings.llm_provider.lower() == "bedrock":
        return BedrockProvider(settings.aws_region, settings.bedrock_model_id)
    return MockLLMProvider()
