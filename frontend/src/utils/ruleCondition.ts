/** Finds the first leaf condition in a (possibly nested) condition tree,
 * used for compact one-line previews in list views. */
export function getPrimaryLeaf(node: unknown): { field: string; operator: string; value: unknown } | null {
  if (!node || typeof node !== "object") return null;
  const obj = node as Record<string, unknown>;

  if (typeof obj.field === "string" && typeof obj.operator === "string") {
    return { field: obj.field, operator: obj.operator, value: obj.value };
  }
  for (const key of ["all", "any"]) {
    if (Array.isArray(obj[key])) {
      for (const child of obj[key] as unknown[]) {
        const found = getPrimaryLeaf(child);
        if (found) return found;
      }
    }
  }
  if (obj.not) return getPrimaryLeaf(obj.not);
  return null;
}

export function previewCondition(node: unknown): string {
  const leaf = getPrimaryLeaf(node);
  if (!leaf) return "";
  return `${leaf.field} ${leaf.operator} ${JSON.stringify(leaf.value)}`;
}
