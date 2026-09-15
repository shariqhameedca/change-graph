import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.engine.decision_service import evaluate_record
from app.evaluation.benchmark import BENCHMARK_CASES
from app.models.regulation import RegulationVersion
from app.services.rule_service import load_rules_for_version

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.post("/run")
def run_evaluation_suite(
    regulation_version_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if regulation_version_id is not None:
        version = db.get(RegulationVersion, regulation_version_id)
    else:
        version = (
            db.query(RegulationVersion)
            .filter(RegulationVersion.status == "ACTIVE")
            .order_by(RegulationVersion.effective_from.desc())
            .first()
        )
    if version is None:
        raise HTTPException(status_code=404, detail="No active regulation version found")

    rules = load_rules_for_version(db, version.id)

    passed = 0
    cases = []
    for case in BENCHMARK_CASES:
        data = {**case["input"], "jurisdiction": case["jurisdiction"]}
        result = evaluate_record(rules, data, as_of=version.effective_from)
        fired_codes = sorted(t["rule_code"] for t in result["trace"] if t["fired"])
        expected_codes = sorted(case["expected_fired_rules"])
        ok = result["verdict"] == case["expected_verdict"] and fired_codes == expected_codes
        if ok:
            passed += 1
        cases.append(
            {
                "name": case["name"],
                "expected_verdict": case["expected_verdict"],
                "actual_verdict": result["verdict"],
                "expected_fired_rules": expected_codes,
                "actual_fired_rules": fired_codes,
                "passed": ok,
            }
        )

    total = len(BENCHMARK_CASES)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
        "regulation_version_id": str(version.id),
        "cases": cases,
    }
