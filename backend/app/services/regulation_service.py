from __future__ import annotations

import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.compiler.relationship_extractor import version_supersedes_edge
from app.graph.graph_service import add_edge, get_or_create_node
from app.models.compile_job import CompileJob
from app.models.evaluation import Decision, DecisionTrace
from app.models.graph import KnowledgeEdge, KnowledgeNode
from app.models.impact import ImpactAnalysis, ImpactItem
from app.models.regulation import Regulation, RegulationVersion
from app.models.rule import Definition, Rule, RuleException


def create_regulation(db: Session, name: str, description: str | None, jurisdiction: str, source_url: str | None) -> Regulation:
    regulation = Regulation(
        name=name, description=description, jurisdiction=jurisdiction, source_url=source_url
    )
    db.add(regulation)
    db.flush()
    get_or_create_node(db, "REGULATION", regulation.id, regulation.name)
    db.flush()
    return regulation


def create_version(
    db: Session,
    regulation: Regulation,
    version: str,
    effective_from,
    effective_to,
    status: str,
    source_text: str,
) -> RegulationVersion:
    previous = (
        db.query(RegulationVersion)
        .filter(RegulationVersion.regulation_id == regulation.id)
        .order_by(RegulationVersion.created_at.desc())
        .first()
    )

    new_version = RegulationVersion(
        regulation_id=regulation.id,
        version=version,
        effective_from=effective_from,
        effective_to=effective_to,
        status=status,
        source_text=source_text,
    )
    db.add(new_version)
    db.flush()

    get_or_create_node(db, "VERSION", new_version.id, f"{regulation.name} {new_version.version}")
    edge_spec = version_supersedes_edge(new_version.id, previous.id) if previous else None
    if edge_spec:
        add_edge(
            db,
            edge_spec.source_type,
            edge_spec.source_id,
            edge_spec.target_type,
            edge_spec.target_id,
            edge_spec.relationship_type,
        )

    db.flush()
    return new_version


def preview_delete_regulation(db: Session, regulation: Regulation) -> dict[str, int]:
    """Counts what a delete would remove, for a confirmation prompt."""

    version_ids = [
        v.id for v in db.query(RegulationVersion.id).filter(RegulationVersion.regulation_id == regulation.id)
    ]
    rule_ids = [r.id for r in db.query(Rule.id).filter(Rule.regulation_version_id.in_(version_ids))] if version_ids else []
    decision_count = (
        db.query(Decision).filter(Decision.regulation_version_id.in_(version_ids)).count() if version_ids else 0
    )
    impact_count = (
        db.query(ImpactAnalysis)
        .filter(
            or_(
                ImpactAnalysis.regulation_version_id.in_(version_ids),
                ImpactAnalysis.compared_to_version_id.in_(version_ids),
            )
        )
        .count()
        if version_ids
        else 0
    )
    return {
        "versions": len(version_ids),
        "rules": len(rule_ids),
        "decisions": decision_count,
        "impact_analyses": impact_count,
    }


def delete_regulation(db: Session, regulation: Regulation) -> None:
    """Deletes a regulation and everything derived from it.

    SQLAlchemy's ORM cascades (`cascade="all, delete-orphan"`) already
    handle Regulation -> RegulationVersion -> Rule/Definition ->
    RuleException when `db.delete(regulation)` is called. Everything else
    here -- Decisions/DecisionTraces, ImpactAnalyses/ImpactItems,
    CompileJobs (their CompileJobChunk rows cascade at the DB level via
    ondelete=CASCADE), and the KnowledgeNode/KnowledgeEdge rows -- is linked
    by plain UUID columns rather than ORM relationships, so it has to be
    cleaned up explicitly or it would be left orphaned, pointing at ids that
    no longer exist (or, for CompileJob's FK, block the delete outright).
    """

    version_ids = [
        v.id for v in db.query(RegulationVersion.id).filter(RegulationVersion.regulation_id == regulation.id)
    ]
    rule_ids = [r.id for r in db.query(Rule.id).filter(Rule.regulation_version_id.in_(version_ids))] if version_ids else []
    exception_ids = (
        [e.id for e in db.query(RuleException.id).filter(RuleException.rule_id.in_(rule_ids))] if rule_ids else []
    )
    definition_ids = (
        [d.id for d in db.query(Definition.id).filter(Definition.regulation_version_id.in_(version_ids))]
        if version_ids
        else []
    )

    if version_ids:
        decision_ids = [
            d.id for d in db.query(Decision.id).filter(Decision.regulation_version_id.in_(version_ids))
        ]
        if decision_ids:
            db.query(DecisionTrace).filter(DecisionTrace.decision_id.in_(decision_ids)).delete(
                synchronize_session=False
            )
            db.query(Decision).filter(Decision.id.in_(decision_ids)).delete(synchronize_session=False)

        impact_analysis_ids = [
            a.id
            for a in db.query(ImpactAnalysis.id).filter(
                or_(
                    ImpactAnalysis.regulation_version_id.in_(version_ids),
                    ImpactAnalysis.compared_to_version_id.in_(version_ids),
                )
            )
        ]
        if impact_analysis_ids:
            db.query(ImpactItem).filter(ImpactItem.impact_analysis_id.in_(impact_analysis_ids)).delete(
                synchronize_session=False
            )
            db.query(ImpactAnalysis).filter(ImpactAnalysis.id.in_(impact_analysis_ids)).delete(
                synchronize_session=False
            )

    node_filters = [(KnowledgeNode.node_type == "REGULATION") & (KnowledgeNode.entity_id == regulation.id)]
    if version_ids:
        node_filters.append((KnowledgeNode.node_type == "VERSION") & KnowledgeNode.entity_id.in_(version_ids))
    if rule_ids:
        node_filters.append((KnowledgeNode.node_type == "RULE") & KnowledgeNode.entity_id.in_(rule_ids))
    if definition_ids:
        node_filters.append(
            (KnowledgeNode.node_type == "DEFINITION") & KnowledgeNode.entity_id.in_(definition_ids)
        )
    if exception_ids:
        node_filters.append(
            (KnowledgeNode.node_type == "EXCEPTION") & KnowledgeNode.entity_id.in_(exception_ids)
        )

    if version_ids:
        db.query(CompileJob).filter(CompileJob.regulation_version_id.in_(version_ids)).delete(
            synchronize_session=False
        )

    node_ids = [n.id for n in db.query(KnowledgeNode.id).filter(or_(*node_filters))]
    if node_ids:
        db.query(KnowledgeEdge).filter(
            or_(KnowledgeEdge.source_node_id.in_(node_ids), KnowledgeEdge.target_node_id.in_(node_ids))
        ).delete(synchronize_session=False)
        db.query(KnowledgeNode).filter(KnowledgeNode.id.in_(node_ids)).delete(synchronize_session=False)

    db.delete(regulation)
    db.flush()
