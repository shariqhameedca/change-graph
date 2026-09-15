"""Orchestrates the regulation compiler: persistence + knowledge graph
construction for an already-validated extraction result.

Nothing an LLM provider returns reaches storage or the deterministic engine
without first passing through `app.compiler.validator.validate_extraction`
(and, for multi-chunk documents, `app.compiler.merger.merge_chunk_extractions`)
-- see `app.services.compile_job_service` for the code that drives a compile
end to end (chunking, calling the provider per chunk, merging, then calling
`persist_extraction` here).
"""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.compiler.relationship_extractor import (
    DefinitionLike,
    ExceptionLike,
    RuleLike,
    structural_edges_for_version,
)
from app.compiler.merger import MergedExtraction
from app.compiler.validator import ExtractionResult
from app.graph.graph_service import apply_edge_specs, get_or_create_node
from app.models.graph import KnowledgeEdge, KnowledgeNode
from app.models.regulation import Regulation, RegulationVersion
from app.models.rule import Definition, Rule, RuleException


def _clear_version_content(db: Session, version_id) -> None:
    old_rules = db.query(Rule).filter(Rule.regulation_version_id == version_id).all()
    old_rule_ids = [r.id for r in old_rules]
    old_exception_ids = (
        [e.id for e in db.query(RuleException).filter(RuleException.rule_id.in_(old_rule_ids)).all()]
        if old_rule_ids
        else []
    )
    old_defs = db.query(Definition).filter(Definition.regulation_version_id == version_id).all()
    old_def_ids = [d.id for d in old_defs]

    stale_node_ids = [
        n.id
        for n in db.query(KnowledgeNode)
        .filter(
            or_(
                (KnowledgeNode.node_type == "RULE") & KnowledgeNode.entity_id.in_(old_rule_ids or [None]),
                (KnowledgeNode.node_type == "EXCEPTION") & KnowledgeNode.entity_id.in_(old_exception_ids or [None]),
                (KnowledgeNode.node_type == "DEFINITION") & KnowledgeNode.entity_id.in_(old_def_ids or [None]),
            )
        )
        .all()
    ]
    if stale_node_ids:
        db.query(KnowledgeEdge).filter(
            or_(
                KnowledgeEdge.source_node_id.in_(stale_node_ids),
                KnowledgeEdge.target_node_id.in_(stale_node_ids),
            )
        ).delete(synchronize_session=False)
        db.query(KnowledgeNode).filter(KnowledgeNode.id.in_(stale_node_ids)).delete(
            synchronize_session=False
        )

    for rule in old_rules:
        db.delete(rule)
    for definition in old_defs:
        db.delete(definition)
    db.flush()


def persist_extraction(
    db: Session,
    regulation: Regulation,
    version: RegulationVersion,
    extraction: ExtractionResult | MergedExtraction,
) -> dict:
    """Writes an already-validated (and, for multi-chunk jobs, already-merged)
    extraction result to the database: clears any prior compile of this
    version, persists Definitions/Rules/Exceptions, builds structural graph
    edges, marks the version ACTIVE, and returns a CompilationReport-shaped
    dict. Pure persistence -- no LLM call happens here."""

    _clear_version_content(db, version.id)

    get_or_create_node(db, "REGULATION", regulation.id, regulation.name)
    get_or_create_node(db, "VERSION", version.id, f"{regulation.name} {version.version}")

    created_definitions: list[Definition] = []
    for item in extraction.definitions:
        definition = Definition(
            regulation_version_id=version.id,
            term=item.term,
            definition=item.definition,
            source_reference=item.source_reference,
            source_text=item.source_text,
        )
        db.add(definition)
        db.flush()
        get_or_create_node(db, "DEFINITION", definition.id, definition.term)
        created_definitions.append(definition)

    created_rules: dict[str, Rule] = {}
    for item in extraction.rules:
        rule = Rule(
            regulation_version_id=version.id,
            rule_code=item.rule_code,
            title=item.title,
            description=item.description,
            rule_type=item.rule_type,
            priority=item.priority,
            jurisdiction=item.jurisdiction,
            effective_from=item.effective_from,
            effective_to=item.effective_to,
            conditions=item.conditions,
            actions=item.actions,
            source_reference=item.source_reference,
            source_text=item.source_text,
            confidence=item.confidence,
        )
        db.add(rule)
        db.flush()
        get_or_create_node(db, "RULE", rule.id, f"{rule.rule_code}: {rule.title}")
        created_rules[rule.rule_code] = rule

    created_exceptions: list[RuleException] = []
    warnings = list(extraction.warnings)
    for item in extraction.exceptions:
        rule = created_rules.get(item.rule_code)
        if rule is None:
            warnings.append(
                f"Exception for unknown rule '{item.rule_code}' was skipped."
            )
            continue
        exception = RuleException(
            rule_id=rule.id,
            description=item.description,
            conditions=item.conditions,
            source_reference=item.source_reference,
            source_text=item.source_text,
        )
        db.add(exception)
        db.flush()
        get_or_create_node(db, "EXCEPTION", exception.id, f"Exception: {rule.rule_code}")
        created_exceptions.append(exception)

    edge_specs = structural_edges_for_version(
        regulation.id,
        version.id,
        [RuleLike(r.id, r.description, r.source_text) for r in created_rules.values()],
        [DefinitionLike(d.id, d.term) for d in created_definitions],
        [ExceptionLike(e.id, e.rule_id) for e in created_exceptions],
    )
    relationships_created = apply_edge_specs(db, edge_specs)

    version.status = "ACTIVE"
    db.flush()

    return {
        "rules_created": len(created_rules),
        "definitions_created": len(created_definitions),
        "exceptions_created": len(created_exceptions),
        "relationships_created": relationships_created,
        "warnings": warnings,
    }
