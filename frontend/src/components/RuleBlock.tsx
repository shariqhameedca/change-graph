interface ConditionLeaf {
  field: string;
  operator: string;
  value: unknown;
}

type ConditionNode =
  | ConditionLeaf
  | { all: ConditionNode[] }
  | { any: ConditionNode[] }
  | { not: ConditionNode };

function isLeaf(node: unknown): node is ConditionLeaf {
  return !!node && typeof node === "object" && "field" in (node as object);
}

function renderLine(node: ConditionNode, depth: number, key: string): JSX.Element[] {
  const indent = { paddingLeft: 14 * depth };

  if (isLeaf(node)) {
    return [
      <div className="rule-condition-line" style={indent} key={key}>
        <span className="rule-field">{node.field}</span>{" "}
        <span className="rule-op">{node.operator}</span>{" "}
        <span className="rule-value">{JSON.stringify(node.value)}</span>
      </div>,
    ];
  }

  if ("all" in node || "any" in node) {
    const kind = "all" in node ? "all" : "any";
    const children = (node as { all?: ConditionNode[]; any?: ConditionNode[] })[kind]!;
    const joiner = kind === "all" ? "AND" : "OR";
    const lines: JSX.Element[] = [];
    children.forEach((child, i) => {
      if (i > 0) {
        lines.push(
          <div className="rule-condition-line rule-logic" style={indent} key={`${key}-j${i}`}>
            {joiner}
          </div>
        );
      }
      lines.push(...renderLine(child, depth, `${key}-${i}`));
    });
    return lines;
  }

  if ("not" in node) {
    return [
      <div className="rule-condition-line rule-logic" style={indent} key={`${key}-not`}>
        NOT
      </div>,
      ...renderLine((node as { not: ConditionNode }).not, depth + 1, `${key}-not-c`),
    ];
  }

  return [];
}

/** Renders a rule's conditions/actions as pseudo-code, the way an engineer
 * reading executable logic would want to see it -- not as prose, not as
 * raw JSON. */
export function RuleBlock({
  conditions,
  actions,
  sourceReference,
}: {
  conditions: Record<string, unknown>;
  actions: Record<string, unknown>;
  sourceReference?: string | null;
}) {
  const conditionLines = renderLine(conditions as ConditionNode, 0, "c");
  const actionEntries = Object.entries(actions);

  return (
    <div className="rule-block">
      <div className="rule-block-body">
        <div className="rule-block-keyword when">WHEN</div>
        {conditionLines}
      </div>
      <div className="rule-block-body">
        <div className="rule-block-keyword then">THEN</div>
        {actionEntries.map(([k, v]) => (
          <div className="rule-condition-line" key={k}>
            <span className="rule-field">{k}</span> <span className="rule-op">=</span>{" "}
            <span className="rule-value">{JSON.stringify(v)}</span>
          </div>
        ))}
      </div>
      {sourceReference && (
        <div className="rule-block-body">
          <div className="rule-block-keyword source">SOURCE</div>
          <div className="rule-condition-line text-secondary">{sourceReference}</div>
        </div>
      )}
    </div>
  );
}
