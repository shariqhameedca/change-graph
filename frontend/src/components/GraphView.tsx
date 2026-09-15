import { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  type Edge,
  type Node,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import type { Graph, GraphNode } from "../types";
import { NODE_TYPE_ORDER, colorForType, softColorForType } from "../utils/graphStyle";

const COLUMN_WIDTH = 230;
const ROW_HEIGHT = 58;

function layout(graph: Graph): Node[] {
  const grouped = new Map<string, GraphNode[]>();
  for (const node of graph.nodes) {
    const list = grouped.get(node.type) ?? [];
    list.push(node);
    grouped.set(node.type, list);
  }

  const orderedTypes = [
    ...NODE_TYPE_ORDER.filter((t) => grouped.has(t)),
    ...Array.from(grouped.keys()).filter((t) => !NODE_TYPE_ORDER.includes(t)),
  ];

  const nodes: Node[] = [];
  orderedTypes.forEach((type, colIndex) => {
    const items = grouped.get(type) ?? [];
    items.forEach((n, rowIndex) => {
      nodes.push({
        id: n.id,
        data: { label: n.label, nodeType: n.type },
        position: { x: colIndex * COLUMN_WIDTH, y: rowIndex * ROW_HEIGHT },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      });
    });
  });
  return nodes;
}

function baseNodeStyle(type: string): React.CSSProperties {
  const color = colorForType(type);
  return {
    border: `1.5px solid ${color}`,
    borderRadius: 8,
    padding: "7px 11px",
    fontSize: 11.5,
    fontWeight: 500,
    background: softColorForType(type),
    color: "#f4f7fb",
    maxWidth: 190,
    boxShadow: `0 0 0 0 transparent`,
    transition: "opacity 0.15s ease, box-shadow 0.15s ease",
  };
}

export function GraphView({
  graph,
  onNodeClick,
}: {
  graph: Graph;
  onNodeClick?: (node: GraphNode) => void;
}) {
  // Recomputed whenever `graph` itself changes (switching the selected
  // regulation, toggling a node-type filter, a background refetch) --
  // this used to be `useState(() => layout(graph))`, which only ran once on
  // mount. Every other derived value here (nodeById, neighborMap,
  // typesPresent) already reacted to `graph` changes, so a stale
  // flowNodesBase meant clicks looked up the *new* graph's nodes by ids that
  // only existed in whatever graph was loaded first -- clicks silently did
  // nothing, and edges pointed at node ids no longer present at all.
  const flowNodesBase = useMemo(() => layout(graph), [graph]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // A hovered node id from the *previous* graph can outlive it (nothing
  // clears hoveredId when `graph` swaps). Left dangling, neighborMap.get()
  // for that id resolves to an empty set instead of null, which -- per the
  // dimming logic below -- dims every single node in the new graph to 25%
  // opacity, i.e. the whole graph appears to have "disappeared".
  useEffect(() => {
    setHoveredId(null);
  }, [graph]);

  // Forces the internal React Flow instance (viewport, zoom, fitView) to
  // fully reset only when the actual set of nodes/edges changes -- not on
  // every hover-driven style update, which would otherwise cause visible
  // flicker on every mouse move. Without this, `fitView` (which React Flow
  // only ever applies once, on mount) keeps framing whatever graph was
  // first loaded, so a structurally different graph can render entirely
  // outside the current viewport.
  const graphSignature = useMemo(
    () => `${graph.nodes.map((n) => n.id).sort().join(",")}::${graph.edges.length}`,
    [graph]
  );

  const neighborMap = useMemo(() => {
    const map = new Map<string, Set<string>>();
    for (const e of graph.edges) {
      if (!map.has(e.source)) map.set(e.source, new Set());
      if (!map.has(e.target)) map.set(e.target, new Set());
      map.get(e.source)!.add(e.target);
      map.get(e.target)!.add(e.source);
    }
    return map;
  }, [graph.edges]);

  const connected = hoveredId ? neighborMap.get(hoveredId) ?? new Set<string>() : null;

  const flowNodes: Node[] = useMemo(
    () =>
      flowNodesBase.map((n) => {
        const isDimmed = connected && hoveredId !== n.id && !connected.has(n.id);
        const isHovered = hoveredId === n.id;
        return {
          ...n,
          style: {
            ...baseNodeStyle(n.data.nodeType),
            opacity: isDimmed ? 0.25 : 1,
            boxShadow: isHovered
              ? `0 0 0 1px ${colorForType(n.data.nodeType)}, 0 0 20px -2px ${colorForType(n.data.nodeType)}`
              : "none",
          },
        };
      }),
    [flowNodesBase, connected, hoveredId]
  );

  const flowEdges: Edge[] = useMemo(
    () =>
      graph.edges.map((e) => {
        const isActive = hoveredId && (e.source === hoveredId || e.target === hoveredId);
        const isDimmed = hoveredId && !isActive;
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.relationship,
          labelStyle: { fontSize: 10, fill: "#98a4b5" },
          labelBgStyle: { fill: "#0c1118" },
          style: {
            stroke: isActive ? "#7c5cff" : "#344155",
            strokeWidth: isActive ? 2 : 1,
            opacity: isDimmed ? 0.2 : 1,
            transition: "opacity 0.15s ease, stroke 0.15s ease",
          },
          animated: false,
        };
      }),
    [graph.edges, hoveredId]
  );

  const nodeById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph.nodes]);
  const typesPresent = useMemo(() => Array.from(new Set(graph.nodes.map((n) => n.type))), [graph.nodes]);

  return (
    <div>
      <div className="graph-wrap">
        <ReactFlow
          key={graphSignature}
          nodes={flowNodes}
          edges={flowEdges}
          onNodeClick={(_, node) => {
            const original = nodeById.get(node.id);
            if (original && onNodeClick) onNodeClick(original);
          }}
          onNodeMouseEnter={(_, node) => setHoveredId(node.id)}
          onNodeMouseLeave={() => setHoveredId(null)}
          fitView
          fitViewOptions={{ padding: 0.2, maxZoom: 1.1 }}
          minZoom={0.1}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={18} color="#1b2330" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div className="legend">
        {typesPresent.map((t) => (
          <span key={t}>
            <span className="legend-dot" style={{ background: colorForType(t) }} />
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}
