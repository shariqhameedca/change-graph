"""Splits regulation source text into typed sections.

ChangeGraph's demo regulation text is written as realistic prose, but each
provision is delimited by a `=== TYPE: identifier ===` marker and annotated
with bracketed tags (e.g. `<<JURISDICTION: ANY>>`). This mirrors how a real
extraction pipeline would work: the prose is what a human (or an LLM) reads,
the markers are what let the deterministic mock compiler stand in for an LLM
without needing network access or an API key.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SECTION_HEADER_RE = re.compile(
    r"^===\s*(?P<kind>DEFINITION|RULE|EXCEPTION)\s*:\s*(?P<identifier>[^=]+?)\s*===\s*$",
    re.MULTILINE,
)

# Tags use << >> rather than [ ] because condition/action values are JSON,
# which itself uses [ ] for arrays -- a bracket delimiter would truncate at
# the first array's closing bracket.
TAG_RE = re.compile(r"<<(?P<key>[A-Z_]+)\s*:\s*(?P<value>.*?)>>", re.DOTALL)


@dataclass
class Section:
    kind: str  # DEFINITION | RULE | EXCEPTION
    identifier: str  # term / "CODE | Title" / rule_code (for exceptions)
    body: str
    tags: dict[str, str] = field(default_factory=dict)


def _extract_tags(text: str) -> tuple[str, dict[str, str]]:
    tags: dict[str, str] = {}
    for match in TAG_RE.finditer(text):
        tags[match.group("key")] = match.group("value").strip()
    prose = TAG_RE.sub("", text).strip()
    return prose, tags


def split_sections(source_text: str) -> list[Section]:
    """Split raw regulation text into structured Section objects."""

    matches = list(SECTION_HEADER_RE.finditer(source_text))
    sections: list[Section] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(source_text)
        body_raw = source_text[start:end].strip()
        prose, tags = _extract_tags(body_raw)
        sections.append(
            Section(
                kind=match.group("kind"),
                identifier=match.group("identifier").strip(),
                body=prose,
                tags=tags,
            )
        )
    return sections
