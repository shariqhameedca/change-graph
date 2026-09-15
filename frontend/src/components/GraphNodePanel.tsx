import { Link } from "react-router-dom";
import { ArrowRight } from "./icons";
import { SidePanel } from "./SidePanel";
import { useRule } from "../hooks/useApi";
import type { GraphNode } from "../types";
import { colorForType } from "../utils/graphStyle";

/** The right-side detail panel shown when a knowledge-graph node is
 * clicked. Rule nodes get a live summary fetched from the API; every other
 * node type gets its label/metadata. Never navigates away automatically --
 * the user chooses to open the full page via the link at the bottom. */
export function GraphNodePanel({ node, onClose }: { node: GraphNode; onClose: () => void }) {
  const ruleDetail = useRule(node.type === "RULE" ? node.entity_id : undefined);
  const color = colorForType(node.type);

  return (
    <SidePanel title={node.label} eyebrow={node.type} onClose={onClose}>
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          fontSize: 11,
          fontWeight: 650,
          color,
          background: `color-mix(in srgb, ${color} 14%, transparent)`,
          border: `1px solid color-mix(in srgb, ${color} 40%, transparent)`,
          borderRadius: 999,
          padding: "3px 10px",
          marginBottom: 16,
        }}
      >
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: color }} />
        {node.type}
      </div>

      {node.type === "RULE" && ruleDetail.data && (
        <>
          <dl className="kv-list">
            <dt>Rule code</dt>
            <dd className="mono">{ruleDetail.data.rule_code}</dd>
            <dt>Jurisdiction</dt>
            <dd>{ruleDetail.data.jurisdiction}</dd>
            <dt>Priority</dt>
            <dd>{ruleDetail.data.priority}</dd>
            <dt>Exceptions</dt>
            <dd>{ruleDetail.data.exceptions.length}</dd>
            <dt>Affected decisions</dt>
            <dd>{ruleDetail.data.affected_decision_count}</dd>
            <dt>Source</dt>
            <dd className="mono">{ruleDetail.data.source_reference ?? "—"}</dd>
          </dl>
          {ruleDetail.data.description && (
            <p style={{ marginTop: 16, color: "var(--text-secondary)", fontSize: 13 }}>
              {ruleDetail.data.description}
            </p>
          )}
          <Link className="btn btn-secondary" to={`/rules/${node.entity_id}`} style={{ marginTop: 18 }}>
            View full rule
            <ArrowRight size={14} />
          </Link>
        </>
      )}

      {node.type === "RULE" && ruleDetail.isLoading && (
        <div className="skeleton skeleton-text" style={{ width: "70%" }} />
      )}

      {node.type !== "RULE" && (
        <>
          <dl className="kv-list">
            <dt>Entity ID</dt>
            <dd className="mono" style={{ fontSize: 11.5 }}>
              {node.entity_id}
            </dd>
          </dl>
          {typeof node.metadata?.explanation === "string" && (
            <p style={{ marginTop: 16, color: "var(--text-secondary)", fontSize: 13 }}>
              {node.metadata.explanation}
            </p>
          )}
        </>
      )}
    </SidePanel>
  );
}
