const OPERATOR_PHRASES: Record<string, (field: string, value: unknown) => string> = {
  equals: (f, v) => `${f} is ${JSON.stringify(v)}`,
  not_equals: (f, v) => `${f} is not ${JSON.stringify(v)}`,
  greater_than: (f, v) => `${f} is greater than ${v}`,
  greater_than_or_equal: (f, v) => `${f} is at least ${v}`,
  less_than: (f, v) => `${f} is less than ${v}`,
  less_than_or_equal: (f, v) => `${f} is at most ${v}`,
  in: (f, v) => `${f} is one of ${JSON.stringify(v)}`,
  not_in: (f, v) => `${f} is none of ${JSON.stringify(v)}`,
  contains: (f, v) => `${f} contains ${JSON.stringify(v)}`,
  starts_with: (f, v) => `${f} starts with ${JSON.stringify(v)}`,
  is_true: (f) => `${f} is true`,
  is_false: (f) => `${f} is false`,
  before: (f, v) => `${f} is before ${v}`,
  after: (f, v) => `${f} is after ${v}`,
  between: (f, v) => `${f} is between ${Array.isArray(v) ? v.join(" and ") : v}`,
  days_since: (f, v) => `at least ${v} days have passed since ${f}`,
};

export function describeCondition(node: unknown): string {
  if (!node || typeof node !== "object") return "";
  const obj = node as Record<string, unknown>;

  if (Array.isArray(obj.all)) {
    return obj.all.map(describeCondition).join(" AND ");
  }
  if (Array.isArray(obj.any)) {
    return `(${obj.any.map(describeCondition).join(" OR ")})`;
  }
  if (obj.not) {
    return `NOT (${describeCondition(obj.not)})`;
  }
  if (typeof obj.field === "string" && typeof obj.operator === "string") {
    const phrase = OPERATOR_PHRASES[obj.operator];
    return phrase ? phrase(obj.field, obj.value) : `${obj.field} ${obj.operator} ${JSON.stringify(obj.value)}`;
  }
  return "";
}
