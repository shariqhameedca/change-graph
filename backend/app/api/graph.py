import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.graph.graph_service import build_node_subgraph, build_regulation_graph, get_node
from app.models.impact import ImpactAnalysis, ImpactItem
from app.models.regulation import Regulation
from app.schemas.graph import GraphOut

router = APIRouter(prefix="/api/graph", tags=["graph"])

MAX_DECISION_NODES = 12
RULE_CODE_RE = re.compile(r"RULE-\d+")


@router.get("/regulations/{regulation_id}", response_model=GraphOut)
def get_regulation_graph(regulation_id: uuid.UUID, db: Session = Depends(get_db)):
    regulation = db.get(Regulation, regulation_id)
    if regulation is None:
        raise HTTPException(status_code=404, detail="Regulation not found")
    return build_regulation_graph(db, regulation_id)


@router.get("/impact/{impact_analysis_id}", response_model=GraphOut)
def get_impact_graph(impact_analysis_id: uuid.UUID, db: Session = Depends(get_db)):
    analysis = db.get(ImpactAnalysis, impact_analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Impact analysis not found")

    items = db.query(ImpactItem).filter(ImpactItem.impact_analysis_id == impact_analysis_id).all()
    node_ids: set[uuid.UUID] = set()

    reg_node = get_node(db, "VERSION", analysis.regulation_version_id)
    old_reg_node = get_node(db, "VERSION", analysis.compared_to_version_id)
    for n in (reg_node, old_reg_node):
        if n:
            node_ids.add(n.id)

    rule_node_by_code: dict[str, str] = {}
    for item in items:
        if item.entity_type == "DECISION":
            continue
        node = get_node(db, item.entity_type, item.entity_id)
        if node:
            node_ids.add(node.id)
            if item.entity_type == "RULE":
                code_match = RULE_CODE_RE.search(item.explanation)
                if code_match:
                    rule_node_by_code[code_match.group(0)] = str(node.id)

    graph = build_node_subgraph(db, node_ids)

    decision_items = [i for i in items if i.entity_type == "DECISION"][:MAX_DECISION_NODES]
    for item in decision_items:
        node_id = f"decision-{item.entity_id}"
        transition_match = re.search(r"(PASS|FAIL|REVIEW) -> (PASS|FAIL|REVIEW)", item.explanation)
        label = transition_match.group(0) if transition_match else "Decision changed"
        graph["nodes"].append(
            {
                "id": node_id,
                "type": "DECISION",
                "entity_id": str(item.entity_id),
                "label": label,
                "metadata": {"explanation": item.explanation, "severity": item.severity},
            }
        )
        for code in set(RULE_CODE_RE.findall(item.explanation)):
            source_id = rule_node_by_code.get(code)
            if source_id:
                graph["edges"].append(
                    {
                        "id": f"{source_id}-{node_id}",
                        "source": source_id,
                        "target": node_id,
                        "relationship": "AFFECTS",
                        "metadata": {},
                    }
                )

    return graph
