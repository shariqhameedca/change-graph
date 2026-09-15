export const NODE_TYPE_ORDER = [
  "REGULATION",
  "VERSION",
  "DEFINITION",
  "RULE",
  "EXCEPTION",
  "POLICY",
  "WORKFLOW",
  "DECISION",
  "RECORD",
];

export const NODE_TYPE_COLOR: Record<string, string> = {
  REGULATION: "#7c5cff",
  VERSION: "#9b81ff",
  DEFINITION: "#22d3ee",
  RULE: "#ef4444",
  EXCEPTION: "#f59e0b",
  POLICY: "#a78bfa",
  WORKFLOW: "#22c55e",
  DECISION: "#f59e0b",
  RECORD: "#98a4b5",
};

export function colorForType(type: string): string {
  return NODE_TYPE_COLOR[type] ?? "#98a4b5";
}

/** A very light tint of a node-type color, used as node fill on the dark
 * canvas so the graph reads as soft glowing chips rather than bare
 * outlines. */
export function softColorForType(type: string): string {
  const hex = colorForType(type).replace("#", "");
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, 0.16)`;
}
