"""Policies and workflows for the demo, plus which rules/policies they
depend on. These dependencies become IMPLEMENTS / REQUIRES graph edges so
that change impact can propagate from a rule to the policies and workflows
that rely on it."""

from __future__ import annotations

POLICIES = [
    {
        "name": "Fair Lending Compliance Policy",
        "description": "Governs APR thresholds and rate-based fairness requirements across all lending products.",
        "owner": "Compliance Office",
        "version": "3.1",
        "source_text": "Internal policy implementing the Part's APR and high-cost loan provisions.",
        "implements_rules": ["RULE-017", "RULE-042", "RULE-011", "RULE-012", "RULE-013", "RULE-019"],
    },
    {
        "name": "Underwriting Standards Policy",
        "description": "Sets minimum eligibility and underwriting criteria for consumer credit decisions.",
        "owner": "Credit Risk",
        "version": "2.0",
        "source_text": "Internal policy implementing the Part's eligibility and threshold provisions.",
        "implements_rules": ["RULE-002", "RULE-003", "RULE-004", "RULE-005", "RULE-009"],
    },
    {
        "name": "Consumer Protection Disclosure Policy",
        "description": "Defines disclosure obligations triggered by loan characteristics.",
        "owner": "Legal",
        "version": "1.4",
        "source_text": "Internal policy implementing the Part's disclosure provisions.",
        "implements_rules": ["RULE-009", "RULE-010", "RULE-018", "RULE-016"],
    },
    {
        "name": "Vulnerable Borrower Protection Policy",
        "description": "Additional protections for military, elder, and payday-loan borrowers.",
        "owner": "Compliance Office",
        "version": "1.0",
        "source_text": "Internal policy implementing the Part's vulnerable-borrower provisions.",
        "implements_rules": ["RULE-013", "RULE-010", "RULE-006", "RULE-042"],
    },
]

WORKFLOWS = [
    {
        "name": "Consumer Loan Origination Workflow",
        "description": "The end-to-end origination flow for new consumer loan applications.",
        "implementation_reference": "orig-svc/consumer-loan",
        "status": "ACTIVE",
        "requires_policies": ["Fair Lending Compliance Policy", "Underwriting Standards Policy"],
    },
    {
        "name": "Manual Underwriting Review Workflow",
        "description": "Human review queue for applications flagged by the deterministic engine.",
        "implementation_reference": "review-svc/manual-underwriting",
        "status": "ACTIVE",
        "requires_policies": ["Underwriting Standards Policy", "Vulnerable Borrower Protection Policy"],
    },
    {
        "name": "Compliance Disclosure Generation Workflow",
        "description": "Generates required borrower disclosures based on loan characteristics.",
        "implementation_reference": "disclosure-svc/generate",
        "status": "ACTIVE",
        "requires_policies": ["Consumer Protection Disclosure Policy"],
    },
    {
        "name": "Military Borrower Servicing Workflow",
        "description": "Specialized servicing path for military and dependent borrowers.",
        "implementation_reference": "servicing-svc/military",
        "status": "ACTIVE",
        "requires_policies": ["Fair Lending Compliance Policy", "Vulnerable Borrower Protection Policy"],
    },
    {
        "name": "State Regulatory Reporting Workflow",
        "description": "Periodic reporting of high-cost loan activity to state regulators.",
        "implementation_reference": "reporting-svc/state-regulatory",
        "status": "ACTIVE",
        "requires_policies": ["Fair Lending Compliance Policy"],
    },
]
