import { useMemo, useState } from "react";
import { GraphNodePanel } from "../components/GraphNodePanel";
import { GraphView } from "../components/GraphView";
import { EmptyState, ErrorState, GraphSkeleton } from "../components/StateViews";
import { useRegulationGraph, useRegulations } from "../hooks/useApi";
import type { Graph, GraphNode } from "../types";
import { NODE_TYPE_ORDER, colorForType } from "../utils/graphStyle";

export function KnowledgeGraphPage() {
  const regulations = useRegulations();
  const [regulationId, setRegulationId] = useState<string>("");
  const activeRegulationId = regulationId || regulations.data?.[0]?.id;
  const graph = useRegulationGraph(activeRegulationId);
  const [typeFilter, setTypeFilter] = useState<Set<string>>(new Set());
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const availableTypes = useMemo(
    () => Array.from(new Set(graph.data?.nodes.map((n) => n.type) ?? [])),
    [graph.data]
  );

  const filteredGraph: Graph | undefined = useMemo(() => {
    if (!graph.data) return undefined;
    if (typeFilter.size === 0) return graph.data;
    const nodes = graph.data.nodes.filter((n) => typeFilter.has(n.type));
    const nodeIds = new Set(nodes.map((n) => n.id));
    const edges = graph.data.edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));
    return { nodes, edges };
  }, [graph.data, typeFilter]);

  function toggleType(type: string) {
    setTypeFilter((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  return (
    <div>
      <div className="page-header">
        <span className="page-eyebrow">Data Exploration</span>
        <h1>Knowledge Graph</h1>
        <p className="page-subtitle">
          The regulation, its rules, definitions, exceptions, policies, and workflows as a single
          connected graph. Hover a node to trace its relationships.
        </p>
      </div>

      <div className="filter-bar">
        <div className="field">
          <label>Regulation</label>
          <select value={activeRegulationId ?? ""} onChange={(e) => setRegulationId(e.target.value)}>
            {regulations.data?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>
        <div className="field" style={{ flex: 1, minWidth: 260 }}>
          <label>Node types</label>
          <div className="tag-row">
            {NODE_TYPE_ORDER.filter((t) => availableTypes.includes(t)).map((t) => {
              const active = typeFilter.has(t);
              const color = colorForType(t);
              return (
                <button
                  key={t}
                  className="btn btn-sm"
                  style={{
                    background: active ? `color-mix(in srgb, ${color} 16%, transparent)` : undefined,
                    borderColor: active ? color : undefined,
                    color: active ? color : undefined,
                  }}
                  onClick={() => toggleType(t)}
                >
                  {t}
                </button>
              );
            })}
            {typeFilter.size > 0 && (
              <button className="btn btn-sm btn-ghost" onClick={() => setTypeFilter(new Set())}>
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {graph.isLoading && <GraphSkeleton />}
      {graph.isError && <ErrorState message="Failed to load graph." />}
      {filteredGraph && filteredGraph.nodes.length === 0 && <EmptyState message="No nodes match this filter." />}

      {filteredGraph && filteredGraph.nodes.length > 0 && (
        <GraphView graph={filteredGraph} onNodeClick={setSelectedNode} />
      )}

      {selectedNode && <GraphNodePanel node={selectedNode} onClose={() => setSelectedNode(null)} />}
    </div>
  );
}
