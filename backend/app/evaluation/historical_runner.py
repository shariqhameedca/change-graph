"""Re-runs historical decisions against a new regulation version and records
what changed. This is where deterministic re-evaluation happens -- no
history is ever mutated, only new Decision rows are appended and linked
back to the decision they supersede.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.engine.applicability import rule_is_applicable
from app.graph.impact_analyzer import RuleDiff
from app.models.evaluation import Decision, DecisionTrace, EvaluationRecord
from app.models.impact import ImpactItem
from app.models.regulation import RegulationVersion
from app.models.rule import Rule
from app.services.decision_service import evaluate_and_persist


def find_affected_decisions(
    db: Session,
    old_version: RegulationVersion,
    rule_diffs: list[RuleDiff],
) -> list[Decision]:
    """Candidate historical decisions whose verdict *might* change.

    A decision is a candidate if a rule that was applicable to it changed or
    was removed, or if a newly added rule would apply to its record.
    """

    changed_codes = {rd.rule_code for rd in rule_diffs if rd.kind in ("MODIFIED", "REMOVED")}
    added_rules = [rd.new_rule for rd in rule_diffs if rd.kind == "ADDED" and rd.new_rule]

    decisions = (
        db.query(Decision).filter(Decision.regulation_version_id == old_version.id).all()
    )
    if not decisions:
        return []

    record_ids = {d.evaluation_record_id for d in decisions}
    records = {
        r.id: r
        for r in db.query(EvaluationRecord).filter(EvaluationRecord.id.in_(record_ids)).all()
    }

    traces = (
        db.query(DecisionTrace)
        .filter(DecisionTrace.decision_id.in_([d.id for d in decisions]))
        .all()
    )
    rule_ids = {t.rule_id for t in traces}
    rules_by_id = {r.id: r for r in db.query(Rule).filter(Rule.id.in_(rule_ids)).all()}

    traces_by_decision: dict[uuid.UUID, list[DecisionTrace]] = {}
    for t in traces:
        traces_by_decision.setdefault(t.decision_id, []).append(t)

    affected: list[Decision] = []
    for decision in decisions:
        touched = False
        for t in traces_by_decision.get(decision.id, []):
            rule = rules_by_id.get(t.rule_id)
            if rule and rule.rule_code in changed_codes:
                touched = True
                break

        if not touched and added_rules:
            record = records.get(decision.evaluation_record_id)
            if record:
                for new_rule in added_rules:
                    applicable, _ = rule_is_applicable(
                        {
                            "jurisdiction": new_rule.jurisdiction,
                            "effective_from": new_rule.effective_from,
                            "effective_to": new_rule.effective_to,
                        },
                        record.input_data,
                    )
                    if applicable:
                        touched = True
                        break

        if touched:
            affected.append(decision)

    return affected


def re_evaluate_decisions(
    db: Session,
    impact_analysis_id: uuid.UUID,
    affected_decisions: list[Decision],
    new_version: RegulationVersion,
) -> dict:
    """Re-run each affected decision against `new_version`, persist the new
    decision, and record an ImpactItem for every verdict that changed."""

    record_ids = {d.evaluation_record_id for d in affected_decisions}
    records = {
        r.id: r
        for r in db.query(EvaluationRecord).filter(EvaluationRecord.id.in_(record_ids)).all()
    }

    changed_count = 0
    transitions: dict[str, int] = {}

    for old_decision in affected_decisions:
        record = records.get(old_decision.evaluation_record_id)
        if record is None:
            continue

        new_decision, _ = evaluate_and_persist(
            db, record, new_version, changed_from_decision_id=old_decision.id
        )

        if new_decision.verdict != old_decision.verdict:
            changed_count += 1
            transition = f"{old_decision.verdict}_TO_{new_decision.verdict}"
            transitions[transition] = transitions.get(transition, 0) + 1

            reasons = _explain_transition(db, old_decision, new_decision)
            db.add(
                ImpactItem(
                    impact_analysis_id=impact_analysis_id,
                    entity_type="DECISION",
                    entity_id=new_decision.id,
                    impact_type="OUTCOME_CHANGED",
                    severity="HIGH",
                    explanation=(
                        f"Record {record.external_reference}: "
                        f"{old_decision.verdict} -> {new_decision.verdict}. {reasons}"
                    ),
                )
            )

    db.flush()

    return {
        "decisions_analyzed": len(affected_decisions),
        "decisions_changed": changed_count,
        "transitions": transitions,
    }


def _explain_transition(db: Session, old_decision: Decision, new_decision: Decision) -> str:
    old_fired = {
        t.rule_id
        for t in db.query(DecisionTrace).filter(
            DecisionTrace.decision_id == old_decision.id,
            DecisionTrace.evaluation_result == "MATCH",
        )
    }
    new_fired = {
        t.rule_id
        for t in db.query(DecisionTrace).filter(
            DecisionTrace.decision_id == new_decision.id,
            DecisionTrace.evaluation_result == "MATCH",
        )
    }
    newly_fired = new_fired - old_fired
    no_longer_fired = old_fired - new_fired

    rule_ids = newly_fired | no_longer_fired
    codes = {r.id: r.rule_code for r in db.query(Rule).filter(Rule.id.in_(rule_ids)).all()}

    parts = []
    if newly_fired:
        parts.append("now triggered: " + ", ".join(codes.get(r, str(r)) for r in newly_fired))
    if no_longer_fired:
        parts.append("no longer triggered: " + ", ".join(codes.get(r, str(r)) for r in no_longer_fired))
    return "; ".join(parts) if parts else "Verdict changed due to rule re-evaluation."
