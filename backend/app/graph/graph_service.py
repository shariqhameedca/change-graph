"""Creates and queries the knowledge graph (KnowledgeNode / KnowledgeEdge)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.compiler.relationship_extractor import EdgeSpec
from app.graph.traversal import bfs_undirected
from app.models.graph import KnowledgeEdge, KnowledgeNode


def get_node(db: Session, node_type: str, entity_id: uuid.UUID) -> KnowledgeNode | None:
    return (
        db.query(KnowledgeNode)
        .filter(KnowledgeNode.node_type == node_type, KnowledgeNode.entity_id == entity_id)
        .one_or_none()
    )


def get_or_create_node(
    db: Session,
    node_type: str,
    entity_id: uuid.UUID,
    label: str,
    metadata: dict[str, Any] | None = None,
) -> KnowledgeNode:
    node = get_node(db, node_type, entity_id)
    if node:
        node.label = label
        if metadata is not None:
            node.node_metadata = metadata
        return node
    node = KnowledgeNode(
        node_type=node_type, entity_id=entity_id, label=label, node_metadata=metadata or {}
    )
    db.add(node)
    db.flush()
    return node


def add_edge(
    db: Session,
    source_type: str,
    source_id: uuid.UUID,
    target_type: str,
    target_id: uuid.UUID,
    relationship_type: str,
    metadata: dict[str, Any] | None = None,
) -> KnowledgeEdge | None:
    source_node = get_node(db, source_type, source_id)
    target_node = get_node(db, target_type, target_id)
    if source_node is None or target_node is None:
        return None

    existing = (
        db.query(KnowledgeEdge)
        .filter(
            KnowledgeEdge.source_node_id == source_node.id,
            KnowledgeEdge.target_node_id == target_node.id,
            KnowledgeEdge.relationship_type == relationship_type,
        )
        .one_or_none()
    )
    if existing:
        return existing

    edge = KnowledgeEdge(
        source_node_id=source_node.id,
        target_node_id=target_node.id,
        relationship_type=relationship_type,
        edge_metadata=metadata or {},
    )
    db.add(edge)
    db.flush()
    return edge


def apply_edge_specs(db: Session, specs: list[EdgeSpec]) -> int:
    created = 0
    for spec in specs:
        edge = add_edge(
            db, spec.source_type, spec.source_id, spec.target_type, spec.target_id, spec.relationship_type
        )
        if edge is not None:
            created += 1
    return created


def _serialize_node(node: KnowledgeNode) -> dict[str, Any]:
    return {
        "id": str(node.id),
        "type": node.node_type,
        "entity_id": str(node.entity_id),
        "label": node.label,
        "metadata": node.node_metadata,
    }


def _serialize_edge(edge: KnowledgeEdge) -> dict[str, Any]:
    return {
        "id": str(edge.id),
        "source": str(edge.source_node_id),
        "target": str(edge.target_node_id),
        "relationship": edge.relationship_type,
        "metadata": edge.edge_metadata,
    }


def build_regulation_graph(db: Session, regulation_id: uuid.UUID) -> dict[str, Any]:
    reg_node = get_node(db, "REGULATION", regulation_id)
    if reg_node is None:
        return {"nodes": [], "edges": []}

    result = bfs_undirected(db, {reg_node.id})
    nodes = db.query(KnowledgeNode).filter(KnowledgeNode.id.in_(result.node_ids)).all()

    return {
        "nodes": [_serialize_node(n) for n in nodes],
        "edges": [_serialize_edge(e) for e in result.edges],
    }


def build_node_subgraph(db: Session, node_ids: set[uuid.UUID]) -> dict[str, Any]:
    nodes = db.query(KnowledgeNode).filter(KnowledgeNode.id.in_(node_ids)).all()
    edges = (
        db.query(KnowledgeEdge)
        .filter(
            KnowledgeEdge.source_node_id.in_(node_ids),
            KnowledgeEdge.target_node_id.in_(node_ids),
        )
        .all()
    )
    return {
        "nodes": [_serialize_node(n) for n in nodes],
        "edges": [_serialize_edge(e) for e in edges],
    }
