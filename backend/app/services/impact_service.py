"""Orchestrates change-impact analysis: diffing two regulation versions,
walking the knowledge graph, and (on request) re-running historical
decisions against the new version."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.evaluation.historical_runner import find_affected_decisions, re_evaluate_decisions
from app.graph.impact_analyzer import (
    build_impact_items,
    diff_definitions,
    diff_exceptions,
    diff_rules,
)
from app.models.impact import ImpactAnalysis, ImpactItem
from app.models.regulation import RegulationVersion
from app.models.rule import Definition, Rule, RuleException


class ImpactAnalysisError(ValueError):
    pass


def create_impact_analysis(
    db: Session, old_version_id: uuid.UUID, new_version_id: uuid.UUID
) -> ImpactAnalysis:
    old_version = db.get(RegulationVersion, old_version_id)
    new_version = db.get(RegulationVersion, new_version_id)
    if old_version is None or new_version is None:
        raise ImpactAnalysisError("Both regulation versions must exist")
    if old_version.regulation_id != new_version.regulation_id:
        raise ImpactAnalysisError("Versions must belong to the same regulation")

    old_rules = db.query(Rule).filter(Rule.regulation_version_id == old_version.id).all()
    new_rules = db.query(Rule).filter(Rule.regulation_version_id == new_version.id).all()
    old_defs = db.query(Definition).filter(Definition.regulation_version_id == old_version.id).all()
    new_defs = db.query(Definition).filter(Definition.regulation_version_id == new_version.id).all()
    old_exceptions = (
        db.query(RuleException).filter(RuleException.rule_id.in_([r.id for r in old_rules])).all()
        if old_rules
        else []
    )
    new_exceptions = (
        db.query(RuleException).filter(RuleException.rule_id.in_([r.id for r in new_rules])).all()
        if new_rules
        else []
    )

    rule_diffs = diff_rules(old_rules, new_rules)
    definition_diffs = diff_definitions(old_defs, new_defs)
    exception_diffs = diff_exceptions(
        old_exceptions,
        new_exceptions,
        {r.id: r.rule_code for r in old_rules},
        {r.id: r.rule_code for r in new_rules},
    )

    drafts = build_impact_items(db, old_version.id, rule_diffs, definition_diffs, exception_diffs)
    candidate_decisions = find_affected_decisions(db, old_version, rule_diffs)

    def count(entity_type: str) -> int:
        return len({d.entity_id for d in drafts if d.entity_type == entity_type})

    summary = {
        "rules_added": len([d for d in rule_diffs if d.kind == "ADDED"]),
        "rules_removed": len([d for d in rule_diffs if d.kind == "REMOVED"]),
        "rules_modified": len([d for d in rule_diffs if d.kind == "MODIFIED"]),
        "rules_affected": count("RULE"),
        "definitions_changed": len([d for d in definition_diffs if d.kind != "ADDED"]),
        "exceptions_changed": len([d for d in exception_diffs]),
        "policies_affected": count("POLICY"),
        "workflows_affected": count("WORKFLOW"),
        "decisions_affected": len(candidate_decisions),
        "decisions_changed": 0,
    }

    analysis = ImpactAnalysis(
        regulation_version_id=new_version.id,
        compared_to_version_id=old_version.id,
        status="PENDING",
        summary=summary,
    )
    db.add(analysis)
    db.flush()

    for draft in drafts:
        db.add(
            ImpactItem(
                impact_analysis_id=analysis.id,
                entity_type=draft.entity_type,
                entity_id=draft.entity_id,
                impact_type=draft.impact_type,
                severity=draft.severity,
                explanation=draft.explanation,
            )
        )

    db.flush()
    return analysis


def run_re_evaluation(db: Session, impact_analysis: ImpactAnalysis) -> ImpactAnalysis:
    old_version = db.get(RegulationVersion, impact_analysis.compared_to_version_id)
    new_version = db.get(RegulationVersion, impact_analysis.regulation_version_id)
    if old_version is None or new_version is None:
        raise ImpactAnalysisError("Regulation versions for this analysis no longer exist")

    old_rules = db.query(Rule).filter(Rule.regulation_version_id == old_version.id).all()
    new_rules = db.query(Rule).filter(Rule.regulation_version_id == new_version.id).all()
    rule_diffs = diff_rules(old_rules, new_rules)

    affected_decisions = find_affected_decisions(db, old_version, rule_diffs)
    result = re_evaluate_decisions(db, impact_analysis.id, affected_decisions, new_version)

    summary = dict(impact_analysis.summary)
    summary["decisions_affected"] = result["decisions_analyzed"]
    summary["decisions_changed"] = result["decisions_changed"]
    summary["transitions"] = result["transitions"]
    impact_analysis.summary = summary
    impact_analysis.status = "COMPLETED"

    db.flush()
    return impact_analysis
