"""Compares an old and a new Decision for the same underlying record."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.evaluation import Decision


@dataclass
class DecisionComparison:
    old_decision: Decision
    new_decision: Decision
    changed: bool

    @property
    def transition(self) -> str:
        return f"{self.old_decision.verdict} -> {self.new_decision.verdict}"


def compare_decisions(old_decision: Decision, new_decision: Decision) -> DecisionComparison:
    return DecisionComparison(
        old_decision=old_decision,
        new_decision=new_decision,
        changed=old_decision.verdict != new_decision.verdict,
    )
