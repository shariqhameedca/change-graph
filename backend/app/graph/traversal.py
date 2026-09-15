"""Graph traversal helpers over KnowledgeNode / KnowledgeEdge.

Two traversal modes are used by the application:

- `bfs_undirected`: renders the general knowledge graph (regulation ->
  version -> rule -> policy -> workflow, in any direction) for display.
- `bfs_reverse`: propagates change impact. An edge `A --REL--> B` is read as
  "A depends on / implements / has-exception B", so when B changes, A is
  affected. Walking edges backward from a changed node therefore finds
  everything that depends on it, transitively.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.graph import KnowledgeEdge


@dataclass
class TraversalResult:
    node_ids: set[uuid.UUID]
    edges: list[KnowledgeEdge]


def _load_all_edges(db: Session) -> list[KnowledgeEdge]:
    return db.query(KnowledgeEdge).all()


def bfs_undirected(db: Session, start_ids: set[uuid.UUID]) -> TraversalResult:
    edges = _load_all_edges(db)
    visited: set[uuid.UUID] = set(start_ids)
    frontier = set(start_ids)
    used_edges: dict[uuid.UUID, KnowledgeEdge] = {}

    while frontier:
        next_frontier: set[uuid.UUID] = set()
        for edge in edges:
            if edge.source_node_id in frontier and edge.target_node_id not in visited:
                next_frontier.add(edge.target_node_id)
                used_edges[edge.id] = edge
            elif edge.target_node_id in frontier and edge.source_node_id not in visited:
                next_frontier.add(edge.source_node_id)
                used_edges[edge.id] = edge
            elif edge.source_node_id in visited and edge.target_node_id in visited:
                used_edges.setdefault(edge.id, edge)
        visited |= next_frontier
        frontier = next_frontier

    return TraversalResult(node_ids=visited, edges=list(used_edges.values()))


@dataclass
class ImpactHop:
    node_id: uuid.UUID
    via_edge: KnowledgeEdge
    depth: int


def bfs_reverse(db: Session, start_ids: set[uuid.UUID]) -> list[ImpactHop]:
    """Walk edges backward: from each changed node, find sources pointing at it."""

    edges = _load_all_edges(db)
    visited: set[uuid.UUID] = set(start_ids)
    frontier = set(start_ids)
    depth = 0
    hops: list[ImpactHop] = []

    while frontier:
        depth += 1
        next_frontier: set[uuid.UUID] = set()
        for edge in edges:
            if edge.target_node_id in frontier and edge.source_node_id not in visited:
                next_frontier.add(edge.source_node_id)
                hops.append(ImpactHop(node_id=edge.source_node_id, via_edge=edge, depth=depth))
        visited |= next_frontier
        frontier = next_frontier
        if depth > 25:  # guards against any unexpected cycle
            break

    return hops
