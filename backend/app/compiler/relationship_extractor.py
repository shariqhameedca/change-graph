"""Derives knowledge-graph edges from compiled regulation content.

Produces plain edge specs keyed by (entity_type, entity_id) pairs; the
graph service is responsible for resolving those to KnowledgeNode rows and
persisting KnowledgeEdge rows.
"""

from __future__ import annotations

import uuid
from typing import NamedTuple


class EdgeSpec(NamedTuple):
    source_type: str
    source_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    relationship_type: str


class RuleLike(NamedTuple):
    id: uuid.UUID
    description: str
    source_text: str | None


class DefinitionLike(NamedTuple):
    id: uuid.UUID
    term: str


class ExceptionLike(NamedTuple):
    id: uuid.UUID
    rule_id: uuid.UUID


def structural_edges_for_version(
    regulation_id: uuid.UUID,
    version_id: uuid.UUID,
    rules: list[RuleLike],
    definitions: list[DefinitionLike],
    exceptions: list[ExceptionLike],
) -> list[EdgeSpec]:
    edges: list[EdgeSpec] = [
        EdgeSpec("REGULATION", regulation_id, "VERSION", version_id, "DEFINES")
    ]

    for rule in rules:
        edges.append(EdgeSpec("VERSION", version_id, "RULE", rule.id, "DEFINES"))

    for definition in definitions:
        edges.append(
            EdgeSpec("VERSION", version_id, "DEFINITION", definition.id, "DEFINES")
        )

    for exc in exceptions:
        edges.append(EdgeSpec("RULE", exc.rule_id, "EXCEPTION", exc.id, "HAS_EXCEPTION"))

    for rule in rules:
        haystack = f"{rule.description} {rule.source_text or ''}".lower()
        for definition in definitions:
            if definition.term.lower() in haystack:
                edges.append(
                    EdgeSpec("RULE", rule.id, "DEFINITION", definition.id, "DEPENDS_ON")
                )

    return edges


def version_supersedes_edge(new_version_id: uuid.UUID, old_version_id: uuid.UUID) -> EdgeSpec:
    return EdgeSpec("VERSION", new_version_id, "VERSION", old_version_id, "SUPERSEDES")
