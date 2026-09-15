"""Seeds the full ChangeGraph demo dataset.

Run with `python -m app.seed`. Idempotent: if the demo regulation already
exists, seeding is skipped so re-running the container doesn't duplicate
data.

Order of operations mirrors the product narrative: compile v1 from prose,
evaluate 120+ synthetic historical records against it, compile v2 (the
amendment), then run change-impact analysis and re-evaluate the affected
historical decisions against v2.
"""

from __future__ import annotations

import asyncio
import logging

from app.compiler.llm_provider import MockLLMProvider
from app.database import Base, SessionLocal, engine
from app.graph.graph_service import add_edge, get_or_create_node
from app.models.evaluation import EvaluationRecord
from app.models.regulation import Regulation, RegulationVersion
from app.models.rule import Rule
from app.models.policy import Policy
from app.models.workflow import Workflow
from app.seed.content import (
    V1_EFFECTIVE_FROM,
    V2_EFFECTIVE_FROM,
    build_v1_content,
    build_v2_content,
    render_source_text,
)
from app.seed.programs import POLICIES, WORKFLOWS
from app.seed.records import generate_records
from app.compiler.validator import validate_extraction
from app.services.compiler_service import persist_extraction
from app.services.decision_service import evaluate_and_persist
from app.services.impact_service import create_impact_analysis, run_re_evaluation
from app.services.regulation_service import create_regulation, create_version

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("changegraph.seed")

REGULATION_NAME = "Consumer Lending Fairness Regulation"


async def _compile(db, regulation, version) -> dict:
    # Seed content is small synthetic fixture text, so it's compiled directly
    # in one call rather than through the chunked CompileJob pipeline (which
    # exists for real, arbitrarily large documents) -- same
    # extract -> validate -> persist steps a single-chunk job would run.
    provider = MockLLMProvider()
    raw = await provider.generate_structured(version.source_text, regulation.jurisdiction)
    extraction = validate_extraction(raw)
    return persist_extraction(db, regulation, version, extraction)


def _wire_policies_and_workflows(db, v1_rules: dict[str, Rule], v2_rules: dict[str, Rule]) -> None:
    policy_id_by_name: dict[str, str] = {}

    for policy_data in POLICIES:
        policy = Policy(
            name=policy_data["name"],
            description=policy_data["description"],
            owner=policy_data["owner"],
            version=policy_data["version"],
            source_text=policy_data["source_text"],
        )
        db.add(policy)
        db.flush()
        get_or_create_node(db, "POLICY", policy.id, policy.name)
        policy_id_by_name[policy.name] = policy.id

        for rule_code in policy_data["implements_rules"]:
            for rules_by_code in (v1_rules, v2_rules):
                rule = rules_by_code.get(rule_code)
                if rule:
                    add_edge(db, "POLICY", policy.id, "RULE", rule.id, "IMPLEMENTS")

    for workflow_data in WORKFLOWS:
        workflow = Workflow(
            name=workflow_data["name"],
            description=workflow_data["description"],
            implementation_reference=workflow_data["implementation_reference"],
            status=workflow_data["status"],
        )
        db.add(workflow)
        db.flush()
        get_or_create_node(db, "WORKFLOW", workflow.id, workflow.name)

        for policy_name in workflow_data["requires_policies"]:
            policy_id = policy_id_by_name.get(policy_name)
            if policy_id:
                add_edge(db, "WORKFLOW", workflow.id, "POLICY", policy_id, "REQUIRES")

    db.flush()


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        existing = db.query(Regulation).filter(Regulation.name == REGULATION_NAME).one_or_none()
        if existing is not None:
            logger.info("Demo data already exists (regulation id=%s); skipping seed.", existing.id)
            return

        logger.info("Creating regulation and versions...")
        regulation = create_regulation(
            db,
            name=REGULATION_NAME,
            description=(
                "Synthetic demonstration regulation modeling consumer lending "
                "fairness requirements. Not legal advice."
            ),
            jurisdiction="United States",
            source_url=None,
        )

        def_v1, rules_v1, exceptions_v1 = build_v1_content()
        def_v2, rules_v2, exceptions_v2 = build_v2_content()

        v1 = create_version(
            db,
            regulation,
            version="1.0",
            effective_from=V1_EFFECTIVE_FROM,
            effective_to=None,
            status="DRAFT",
            source_text=render_source_text(def_v1, rules_v1, exceptions_v1),
        )
        v2 = create_version(
            db,
            regulation,
            version="2.0",
            effective_from=V2_EFFECTIVE_FROM,
            effective_to=None,
            status="DRAFT",
            source_text=render_source_text(def_v2, rules_v2, exceptions_v2),
        )

        logger.info("Compiling version 1.0...")
        report_v1 = asyncio.run(_compile(db, regulation, v1))
        logger.info("v1.0 compiled: %s", report_v1)

        logger.info("Compiling version 2.0...")
        report_v2 = asyncio.run(_compile(db, regulation, v2))
        logger.info("v2.0 compiled: %s", report_v2)

        v1.status = "SUPERSEDED"
        v2.status = "ACTIVE"
        db.flush()

        v1_rules = {r.rule_code: r for r in db.query(Rule).filter(Rule.regulation_version_id == v1.id).all()}
        v2_rules = {r.rule_code: r for r in db.query(Rule).filter(Rule.regulation_version_id == v2.id).all()}

        logger.info("Creating policies and workflows...")
        _wire_policies_and_workflows(db, v1_rules, v2_rules)

        logger.info("Generating synthetic historical records...")
        record_dicts = generate_records(count=150)
        records = []
        for rd in record_dicts:
            record = EvaluationRecord(
                external_reference=rd["external_reference"],
                jurisdiction=rd["jurisdiction"],
                record_type=rd["record_type"],
                input_data=rd["input_data"],
            )
            db.add(record)
            records.append(record)
        db.flush()

        logger.info("Evaluating %d records against v1.0...", len(records))
        for record in records:
            evaluate_and_persist(db, record, v1)
        db.flush()

        logger.info("Running change-impact analysis v1.0 -> v2.0...")
        analysis = create_impact_analysis(db, v1.id, v2.id)
        db.flush()
        logger.info("Impact analysis created: %s", analysis.summary)

        analysis = run_re_evaluation(db, analysis)
        db.commit()
        logger.info("Re-evaluation complete: %s", analysis.summary)

        logger.info("Seed complete.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
