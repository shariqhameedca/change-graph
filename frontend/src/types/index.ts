export type Verdict = "PASS" | "FAIL" | "REVIEW";

export interface Regulation {
  id: string;
  name: string;
  description: string | null;
  jurisdiction: string;
  source_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface RegulationVersion {
  id: string;
  regulation_id: string;
  version: string;
  effective_from: string;
  effective_to: string | null;
  status: string;
  source_text: string;
  created_at: string;
}

export interface RegulationDetail extends Regulation {
  versions: RegulationVersion[];
}

export interface CompilationReport {
  rules_created: number;
  definitions_created: number;
  exceptions_created: number;
  relationships_created: number;
  warnings: string[];
}

export type CompileJobStatus =
  | "QUEUED"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "COMPLETED_WITH_WARNINGS"
  | "CANCELLED";

export interface CompileJobChunk {
  id: string;
  chunk_index: number;
  status: CompileJobStatus;
  char_start: number;
  char_end: number;
  rules_extracted: number;
  definitions_extracted: number;
  exceptions_extracted: number;
  warnings: string[];
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface CompileJob {
  id: string;
  regulation_id: string;
  regulation_version_id: string;
  status: CompileJobStatus;
  current_step: string | null;
  chunks_total: number;
  chunks_completed: number;
  chunks_failed: number;
  llm_provider: string;
  error_message: string | null;
  result: CompilationReport | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  chunks: CompileJobChunk[];
}

export interface DeletePreview {
  versions: number;
  rules: number;
  decisions: number;
  impact_analyses: number;
}

export interface ExceptionOut {
  id: string;
  rule_id: string;
  description: string;
  conditions: Record<string, unknown>;
  source_reference: string | null;
  source_text: string | null;
}

export interface DefinitionOut {
  id: string;
  regulation_version_id: string;
  term: string;
  definition: string;
  source_reference: string | null;
  source_text: string | null;
}

export interface Rule {
  id: string;
  regulation_version_id: string;
  rule_code: string;
  title: string;
  description: string | null;
  rule_type: string;
  priority: number;
  jurisdiction: string;
  effective_from: string;
  effective_to: string | null;
  conditions: Record<string, unknown>;
  actions: Record<string, unknown>;
  source_reference: string | null;
  source_text: string | null;
  confidence: number;
  created_at: string;
  updated_at: string;
}

export interface RuleDetail extends Rule {
  exceptions: ExceptionOut[];
  affected_decision_count: number;
}

export interface ConflictFinding {
  type: string;
  rule_a: string;
  rule_b: string;
  description: string;
}

export interface EvaluationRecord {
  id: string;
  external_reference: string;
  jurisdiction: string;
  record_type: string;
  input_data: Record<string, unknown>;
  created_at: string;
}

export interface DecisionTrace {
  id: string;
  decision_id: string;
  rule_id: string;
  rule_code: string;
  rule_title: string;
  evaluation_result: string;
  input_snapshot: Record<string, unknown>;
  condition_results: Record<string, unknown>;
  explanation: string;
  source_reference: string | null;
  source_text: string | null;
}

export interface Decision {
  id: string;
  evaluation_record_id: string;
  regulation_version_id: string;
  verdict: Verdict;
  evaluated_at: string;
  engine_version: string;
  summary: string;
  changed_from_decision_id: string | null;
}

export interface DecisionDetail extends Decision {
  trace: DecisionTrace[];
}

export interface EvaluateResponse {
  decision_id: string | null;
  verdict: Verdict;
  summary: string;
  rules_evaluated: number;
  rules_applicable: number;
  rules_fired: number;
  trace: Array<{
    rule_id: string;
    rule_code: string;
    title: string;
    applicable: boolean;
    evaluation_result: string;
    explanation: string;
    action: { verdict?: string; action?: string; message?: string } | null;
    condition_result: unknown;
    exception_matched: { description: string; source_reference?: string | null } | null;
    source_reference: string | null;
    source_text: string | null;
  }>;
}

export interface ImpactSummary {
  rules_added: number;
  rules_removed: number;
  rules_modified: number;
  rules_affected: number;
  definitions_changed: number;
  exceptions_changed: number;
  policies_affected: number;
  workflows_affected: number;
  decisions_affected: number;
  decisions_changed: number;
  transitions?: Record<string, number>;
}

export interface ImpactItem {
  id: string;
  impact_analysis_id: string;
  entity_type: string;
  entity_id: string;
  impact_type: string;
  severity: string;
  explanation: string;
}

export interface ImpactAnalysis {
  id: string;
  regulation_version_id: string;
  compared_to_version_id: string;
  status: string;
  summary: ImpactSummary;
  created_at: string;
}

export interface ImpactAnalysisDetail extends ImpactAnalysis {
  items: ImpactItem[];
}

export interface DecisionChange {
  record_reference: string;
  jurisdiction: string;
  old_decision_id: string;
  new_decision_id: string;
  old_verdict: Verdict;
  new_verdict: Verdict;
  changed: boolean;
  reason: string;
}

export interface GraphNode {
  id: string;
  type: string;
  entity_id: string;
  label: string;
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship: string;
  metadata: Record<string, unknown>;
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Policy {
  id: string;
  name: string;
  description: string | null;
  owner: string | null;
  version: string;
  source_text: string | null;
}

export interface Workflow {
  id: string;
  name: string;
  description: string | null;
  implementation_reference: string | null;
  status: string;
}

export interface EvaluationSuiteCase {
  name: string;
  expected_verdict: Verdict;
  actual_verdict: Verdict;
  expected_fired_rules: string[];
  actual_fired_rules: string[];
  passed: boolean;
}

export interface EvaluationSuiteResult {
  total: number;
  passed: number;
  failed: number;
  accuracy: number;
  regulation_version_id: string;
  cases: EvaluationSuiteCase[];
}
