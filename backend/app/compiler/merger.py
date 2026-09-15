"""Merges per-chunk extraction results into one document-level result.

Each chunk is compiled by the LLM independently, with no knowledge of any
other chunk's output -- so rule codes can collide across chunks (every chunk
may independently invent "RULE-001"), and definitions can be repeated
verbatim or redefined. This module reconciles that into a single consistent
extraction before it reaches app.services.compiler_service.persist_extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.compiler.validator import ExtractedDefinition, ExtractedException, ExtractedRule


@dataclass
class ChunkExtraction:
    chunk_index: int
    rules: list[ExtractedRule] = field(default_factory=list)
    definitions: list[ExtractedDefinition] = field(default_factory=list)
    exceptions: list[ExtractedException] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MergedExtraction:
    rules: list[ExtractedRule] = field(default_factory=list)
    definitions: list[ExtractedDefinition] = field(default_factory=list)
    exceptions: list[ExtractedException] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def merge_chunk_extractions(chunk_results: list[ChunkExtraction]) -> MergedExtraction:
    ordered = sorted(chunk_results, key=lambda c: c.chunk_index)
    total = len(ordered)

    merged = MergedExtraction()
    used_codes: set[str] = set()
    seen_terms: dict[str, ExtractedDefinition] = {}

    for chunk in ordered:
        remap: dict[str, str] = {}

        for rule in chunk.rules:
            new_code = rule.rule_code
            if new_code in used_codes:
                candidate = f"{rule.rule_code}-C{chunk.chunk_index + 1}"
                suffix = 2
                while candidate in used_codes:
                    candidate = f"{rule.rule_code}-C{chunk.chunk_index + 1}-{suffix}"
                    suffix += 1
                merged.warnings.append(
                    f"Rule code '{rule.rule_code}' from chunk {chunk.chunk_index + 1} "
                    f"collided with an earlier chunk and was renumbered to '{candidate}'."
                )
                new_code = candidate
            used_codes.add(new_code)
            remap[rule.rule_code] = new_code
            merged.rules.append(
                rule if new_code == rule.rule_code else rule.model_copy(update={"rule_code": new_code})
            )

        for definition in chunk.definitions:
            key = definition.term.strip().lower()
            existing = seen_terms.get(key)
            if existing is None:
                seen_terms[key] = definition
                merged.definitions.append(definition)
            elif existing.definition.strip() != definition.definition.strip():
                merged.warnings.append(
                    f"Term '{definition.term}' was defined more than once across chunks with "
                    f"different text; kept the first definition and dropped the one from "
                    f"chunk {chunk.chunk_index + 1}."
                )

        for exception in chunk.exceptions:
            resolved_code = remap.get(exception.rule_code, exception.rule_code)
            merged.exceptions.append(
                exception
                if resolved_code == exception.rule_code
                else exception.model_copy(update={"rule_code": resolved_code})
            )

        merged.warnings.extend(f"[chunk {chunk.chunk_index + 1}/{total}] {w}" for w in chunk.warnings)

    return merged
