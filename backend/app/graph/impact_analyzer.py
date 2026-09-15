"""Structural + dependency-based change-impact analysis.

Given two regulation versions, this module determines which rules,
definitions and exceptions changed, then walks the knowledge graph backward
from those changes to find dependent policies and workflows. It does NOT
touch historical decisions -- that is `app.evaluation.historical_runner`'s
job, since re-running the deterministic engine against every historical
record is a distinct, explicit step (see POST .../re-evaluate).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.graph.graph_service import get_node
from app.graph.traversal import bfs_reverse
from app.models.rule import Definition, Rule, RuleException

SEVERITY_BY_NODE_TYPE = {
    "RULE": "HIGH",
    "DEFINITION": "MEDIUM",
    "EXCEPTION": "MEDIUM",
    "POLICY": "MEDIUM",
    "WORKFLOW": "HIGH",
    "DECISION": "HIGH",
}


@dataclass
class RuleDiff:
    rule_code: str
    kind: str  # ADDED | REMOVED | MODIFIED
    old_rule: Rule | None = None
    new_rule: Rule | None = None
    changed_fields: list[str] = field(default_factory=list)


@dataclass
class DefinitionDiff:
    term: str
    kind: str
    old_definition: Definition | None = None
    new_definition: Definition | None = None


@dataclass
class ExceptionDiff:
    rule_code: str
    kind: str
    old_exception: RuleException | None = None
    new_exception: RuleException | None = None


RULE_COMPARE_FIELDS = ["conditions", "actions", "jurisdiction", "effective_from", "effective_to", "priority"]


def diff_rules(old_rules: list[Rule], new_rules: list[Rule]) -> list[RuleDiff]:
    old_by_code = {r.rule_code: r for r in old_rules}
    new_by_code = {r.rule_code: r for r in new_rules}
    diffs: list[RuleDiff] = []

    for code, old_rule in old_by_code.items():
        if code not in new_by_code:
            diffs.append(RuleDiff(rule_code=code, kind="REMOVED", old_rule=old_rule))

    for code, new_rule in new_by_code.items():
        old_rule = old_by_code.get(code)
        if old_rule is None:
            diffs.append(RuleDiff(rule_code=code, kind="ADDED", new_rule=new_rule))
            continue
        changed = [
            f for f in RULE_COMPARE_FIELDS if getattr(old_rule, f) != getattr(new_rule, f)
        ]
        if changed:
            diffs.append(
                RuleDiff(
                    rule_code=code,
                    kind="MODIFIED",
                    old_rule=old_rule,
                    new_rule=new_rule,
                    changed_fields=changed,
                )
            )

    return diffs


def diff_definitions(old_defs: list[Definition], new_defs: list[Definition]) -> list[DefinitionDiff]:
    old_by_term = {d.term: d for d in old_defs}
    new_by_term = {d.term: d for d in new_defs}
    diffs: list[DefinitionDiff] = []

    for term, old_def in old_by_term.items():
        if term not in new_by_term:
            diffs.append(DefinitionDiff(term=term, kind="REMOVED", old_definition=old_def))

    for term, new_def in new_by_term.items():
        old_def = old_by_term.get(term)
        if old_def is None:
            diffs.append(DefinitionDiff(term=term, kind="ADDED", new_definition=new_def))
        elif old_def.definition != new_def.definition:
            diffs.append(
                DefinitionDiff(
                    term=term, kind="MODIFIED", old_definition=old_def, new_definition=new_def
                )
            )

    return diffs


def diff_exceptions(
    old_exceptions: list[RuleException],
    new_exceptions: list[RuleException],
    old_rule_id_to_code: dict[uuid.UUID, str],
    new_rule_id_to_code: dict[uuid.UUID, str],
) -> list[ExceptionDiff]:
    def key(exc: RuleException, mapping: dict[uuid.UUID, str]) -> str:
        return f"{mapping.get(exc.rule_id, '?')}::{exc.description.strip().lower()}"

    old_by_key = {key(e, old_rule_id_to_code): e for e in old_exceptions}
    new_by_key = {key(e, new_rule_id_to_code): e for e in new_exceptions}
    diffs: list[ExceptionDiff] = []

    for k, old_exc in old_by_key.items():
        if k not in new_by_key:
            diffs.append(
                ExceptionDiff(
                    rule_code=old_rule_id_to_code.get(old_exc.rule_id, "?"),
                    kind="REMOVED",
                    old_exception=old_exc,
                )
            )

    for k, new_exc in new_by_key.items():
        if k not in old_by_key:
            diffs.append(
                ExceptionDiff(
                    rule_code=new_rule_id_to_code.get(new_exc.rule_id, "?"),
                    kind="ADDED",
                    new_exception=new_exc,
                )
            )
        else:
            old_exc = old_by_key[k]
            if old_exc.conditions != new_exc.conditions:
                diffs.append(
                    ExceptionDiff(
                        rule_code=new_rule_id_to_code.get(new_exc.rule_id, "?"),
                        kind="MODIFIED",
                        old_exception=old_exc,
                        new_exception=new_exc,
                    )
                )

    return diffs


@dataclass
class ImpactItemDraft:
    entity_type: str
    entity_id: uuid.UUID
    impact_type: str
    severity: str
    explanation: str


def propagate_dependencies(
    db: Session, changed_old_node_ids: set[uuid.UUID]
) -> list[ImpactItemDraft]:
    """Reverse-BFS from changed nodes (in the OLD version's graph) to find
    dependent policies and workflows that existed at the time."""

    hops = bfs_reverse(db, changed_old_node_ids)
    drafts: list[ImpactItemDraft] = []
    from app.models.graph import KnowledgeNode

    seen: set[uuid.UUID] = set()
    for hop in hops:
        if hop.node_id in seen:
            continue
        seen.add(hop.node_id)
        node = db.get(KnowledgeNode, hop.node_id)
        if node is None or node.node_type not in ("POLICY", "WORKFLOW", "RULE"):
            continue
        severity = SEVERITY_BY_NODE_TYPE.get(node.node_type, "MEDIUM")
        drafts.append(
            ImpactItemDraft(
                entity_type=node.node_type,
                entity_id=node.entity_id,
                impact_type="AFFECTED",
                severity=severity,
                explanation=(
                    f"{node.node_type.title()} '{node.label}' depends on "
                    f"'{hop.via_edge.relationship_type}' a provision that changed "
                    f"between regulation versions."
                ),
            )
        )
    return drafts


def build_impact_items(
    db: Session,
    old_version_id: uuid.UUID,
    rule_diffs: list[RuleDiff],
    definition_diffs: list[DefinitionDiff],
    exception_diffs: list[ExceptionDiff],
) -> list[ImpactItemDraft]:
    items: dict[tuple[str, uuid.UUID], ImpactItemDraft] = {}

    def upsert(draft: ImpactItemDraft) -> None:
        key = (draft.entity_type, draft.entity_id)
        existing = items.get(key)
        if existing is None:
            items[key] = draft
            return
        rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        if rank.get(draft.severity, 0) > rank.get(existing.severity, 0):
            items[key] = draft

    changed_old_node_ids: set[uuid.UUID] = set()

    for rd in rule_diffs:
        if rd.kind == "ADDED":
            upsert(
                ImpactItemDraft(
                    "RULE", rd.new_rule.id, "ADDED", "MEDIUM",
                    f"Rule {rd.rule_code} is new in this version."
                )
            )
        elif rd.kind == "REMOVED":
            upsert(
                ImpactItemDraft(
                    "RULE", rd.old_rule.id, "REMOVED", "HIGH",
                    f"Rule {rd.rule_code} was removed in this version."
                )
            )
            node = get_node(db, "RULE", rd.old_rule.id)
            if node:
                changed_old_node_ids.add(node.id)
        elif rd.kind == "MODIFIED":
            upsert(
                ImpactItemDraft(
                    "RULE", rd.old_rule.id, "MODIFIED", "HIGH",
                    f"Rule {rd.rule_code} changed: {', '.join(rd.changed_fields)}."
                )
            )
            node = get_node(db, "RULE", rd.old_rule.id)
            if node:
                changed_old_node_ids.add(node.id)

    for dd in definition_diffs:
        if dd.kind == "MODIFIED":
            upsert(
                ImpactItemDraft(
                    "DEFINITION", dd.old_definition.id, "MODIFIED", "MEDIUM",
                    f"Definition '{dd.term}' changed."
                )
            )
            node = get_node(db, "DEFINITION", dd.old_definition.id)
            if node:
                changed_old_node_ids.add(node.id)
        elif dd.kind == "REMOVED":
            upsert(
                ImpactItemDraft(
                    "DEFINITION", dd.old_definition.id, "REMOVED", "MEDIUM",
                    f"Definition '{dd.term}' was removed."
                )
            )
        elif dd.kind == "ADDED":
            upsert(
                ImpactItemDraft(
                    "DEFINITION", dd.new_definition.id, "ADDED", "LOW",
                    f"Definition '{dd.term}' is new in this version."
                )
            )

    for ed in exception_diffs:
        if ed.kind == "MODIFIED" and ed.old_exception:
            upsert(
                ImpactItemDraft(
                    "EXCEPTION", ed.old_exception.id, "MODIFIED", "MEDIUM",
                    f"Exception on rule {ed.rule_code} changed."
                )
            )
            rule_node = get_node(db, "RULE", ed.old_exception.rule_id)
            if rule_node:
                changed_old_node_ids.add(rule_node.id)
        elif ed.kind == "REMOVED" and ed.old_exception:
            upsert(
                ImpactItemDraft(
                    "EXCEPTION", ed.old_exception.id, "REMOVED", "MEDIUM",
                    f"Exception on rule {ed.rule_code} was removed."
                )
            )
        elif ed.kind == "ADDED" and ed.new_exception:
            upsert(
                ImpactItemDraft(
                    "EXCEPTION", ed.new_exception.id, "ADDED", "LOW",
                    f"A new exception was added to rule {ed.rule_code}."
                )
            )

    for draft in propagate_dependencies(db, changed_old_node_ids):
        upsert(draft)

    return list(items.values())
