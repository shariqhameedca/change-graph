import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, POLL_TIMEOUT_MS } from "../api/client";
import type {
  CompileJob,
  CompileJobStatus,
  ConflictFinding,
  Decision,
  DecisionChange,
  DecisionDetail,
  DefinitionOut,
  DeletePreview,
  EvaluateResponse,
  EvaluationRecord,
  EvaluationSuiteResult,
  ExceptionOut,
  Graph,
  ImpactAnalysis,
  ImpactAnalysisDetail,
  Regulation,
  RegulationDetail,
  RegulationVersion,
  Rule,
  RuleDetail,
} from "../types";

export function useRegulations() {
  return useQuery({ queryKey: ["regulations"], queryFn: () => api.get<Regulation[]>("/regulations") });
}

export function useCreateRegulation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      name: string;
      jurisdiction: string;
      description?: string;
      source_url?: string;
    }) => api.post<Regulation>("/regulations", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["regulations"] });
    },
  });
}

export function useDeletePreview(regulationId: string | undefined) {
  return useQuery({
    queryKey: ["delete-preview", regulationId],
    queryFn: () => api.get<DeletePreview>(`/regulations/${regulationId}/delete-preview`),
    enabled: !!regulationId,
  });
}

export function useDeleteRegulation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (regulationId: string) => api.delete<void>(`/regulations/${regulationId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["regulations"] });
    },
  });
}

export function useExtractDocumentText() {
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.postForm<{ filename: string; text: string; character_count: number }>(
        "/documents/extract-text",
        formData
      );
    },
  });
}

export function useRegulation(id: string | undefined) {
  return useQuery({
    queryKey: ["regulation", id],
    queryFn: () => api.get<RegulationDetail>(`/regulations/${id}`),
    enabled: !!id,
  });
}

export function useRegulationVersions(regulationId: string | undefined) {
  return useQuery({
    queryKey: ["regulation-versions", regulationId],
    queryFn: () => api.get<RegulationVersion[]>(`/regulations/${regulationId}/versions`),
    enabled: !!regulationId,
  });
}

export function useVersion(regulationId: string | undefined, versionId: string | undefined) {
  return useQuery({
    queryKey: ["version", regulationId, versionId],
    queryFn: () => api.get<RegulationVersion>(`/regulations/${regulationId}/versions/${versionId}`),
    enabled: !!regulationId && !!versionId,
  });
}

export function useCompileVersion(regulationId: string | undefined) {
  // Compilation now runs as a background job: this only starts it and
  // returns the job id almost instantly -- poll its progress with
  // useCompileJob, and invalidate regulation-versions/rules once terminal
  // (not here, since the job isn't done yet when this resolves).
  return useMutation({
    mutationFn: (versionId: string) =>
      api.post<CompileJob>(`/regulations/${regulationId}/versions/${versionId}/compile`),
  });
}

const TERMINAL_JOB_STATUSES: CompileJobStatus[] = ["SUCCEEDED", "FAILED", "COMPLETED_WITH_WARNINGS", "CANCELLED"];

export function useCompileJob(jobId: string | undefined) {
  return useQuery({
    queryKey: ["compile-job", jobId],
    queryFn: () => api.get<CompileJob>(`/jobs/${jobId}`, POLL_TIMEOUT_MS),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && TERMINAL_JOB_STATUSES.includes(status) ? false : 1500;
    },
  });
}

export function useDefinitions(regulationId: string | undefined, versionId: string | undefined) {
  return useQuery({
    queryKey: ["definitions", regulationId, versionId],
    queryFn: () =>
      api.get<DefinitionOut[]>(`/regulations/${regulationId}/versions/${versionId}/definitions`),
    enabled: !!regulationId && !!versionId,
  });
}

export function useVersionExceptions(regulationId: string | undefined, versionId: string | undefined) {
  return useQuery({
    queryKey: ["version-exceptions", regulationId, versionId],
    queryFn: () =>
      api.get<ExceptionOut[]>(`/regulations/${regulationId}/versions/${versionId}/exceptions`),
    enabled: !!regulationId && !!versionId,
  });
}

export function useCreateVersion(regulationId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { version: string; effective_from: string; source_text: string }) =>
      api.post<RegulationVersion>(`/regulations/${regulationId}/versions`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["regulation-versions", regulationId] });
    },
  });
}

export function useVersionLookup() {
  return useQuery({
    queryKey: ["version-lookup"],
    queryFn: async () => {
      const regulations = await api.get<Regulation[]>("/regulations");
      const versionLists = await Promise.all(
        regulations.map((r) => api.get<RegulationVersion[]>(`/regulations/${r.id}/versions`))
      );
      const map = new Map<string, RegulationVersion & { regulation_name: string }>();
      regulations.forEach((r, i) => {
        versionLists[i].forEach((v) => map.set(v.id, { ...v, regulation_name: r.name }));
      });
      return map;
    },
  });
}

export function useRules(regulationVersionId?: string) {
  return useQuery({
    queryKey: ["rules", regulationVersionId],
    queryFn: () =>
      api.get<Rule[]>(
        regulationVersionId ? `/rules?regulation_version_id=${regulationVersionId}` : "/rules"
      ),
  });
}

export function useRule(id: string | undefined) {
  return useQuery({
    queryKey: ["rule", id],
    queryFn: () => api.get<RuleDetail>(`/rules/${id}`),
    enabled: !!id,
  });
}

export function useConflicts(regulationVersionId: string | undefined) {
  return useMutation({
    mutationFn: () =>
      api.post<ConflictFinding[]>(
        `/rules/conflicts/analyze${regulationVersionId ? `?regulation_version_id=${regulationVersionId}` : ""}`
      ),
  });
}

export function useRecords() {
  return useQuery({ queryKey: ["records"], queryFn: () => api.get<EvaluationRecord[]>("/records?limit=500") });
}

export function useDecisions(regulationVersionId?: string) {
  return useQuery({
    queryKey: ["decisions", regulationVersionId],
    queryFn: () =>
      api.get<Decision[]>(
        regulationVersionId ? `/decisions?regulation_version_id=${regulationVersionId}` : "/decisions"
      ),
  });
}

export function useDecision(id: string | undefined) {
  return useQuery({
    queryKey: ["decision", id],
    queryFn: () => api.get<DecisionDetail>(`/decisions/${id}`),
    enabled: !!id,
  });
}

export function useEvaluate() {
  return useMutation({
    mutationFn: (payload: { record_id: string; regulation_version_id: string }) =>
      api.post<EvaluateResponse>("/evaluate", payload),
  });
}

export function useSimulate() {
  return useMutation({
    mutationFn: (payload: {
      regulation_version_id: string;
      jurisdiction: string;
      input_data: Record<string, unknown>;
    }) => api.post<EvaluateResponse>("/evaluate/simulate", payload),
  });
}

export function useImpactAnalyses() {
  return useQuery({ queryKey: ["impact-analyses"], queryFn: () => api.get<ImpactAnalysis[]>("/impact-analysis") });
}

export function useImpactAnalysis(id: string | undefined) {
  return useQuery({
    queryKey: ["impact-analysis", id],
    queryFn: () => api.get<ImpactAnalysisDetail>(`/impact-analysis/${id}`),
    enabled: !!id,
  });
}

export function useCreateImpactAnalysis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { old_version_id: string; new_version_id: string }) =>
      api.post<ImpactAnalysisDetail>("/impact-analysis", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["impact-analyses"] });
    },
  });
}

export function useReEvaluateImpact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<ImpactAnalysisDetail>(`/impact-analysis/${id}/re-evaluate`),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["impact-analysis", id] });
      queryClient.invalidateQueries({ queryKey: ["impact-analyses"] });
      queryClient.invalidateQueries({ queryKey: ["decision-changes", id] });
    },
  });
}

export function useDecisionChanges(impactAnalysisId: string | undefined) {
  return useQuery({
    queryKey: ["decision-changes", impactAnalysisId],
    queryFn: () => api.get<DecisionChange[]>(`/impact-analysis/${impactAnalysisId}/decisions`),
    enabled: !!impactAnalysisId,
  });
}

export function useRegulationGraph(regulationId: string | undefined) {
  return useQuery({
    queryKey: ["graph-regulation", regulationId],
    queryFn: () => api.get<Graph>(`/graph/regulations/${regulationId}`),
    enabled: !!regulationId,
  });
}

export function useImpactGraph(impactAnalysisId: string | undefined) {
  return useQuery({
    queryKey: ["graph-impact", impactAnalysisId],
    queryFn: () => api.get<Graph>(`/graph/impact/${impactAnalysisId}`),
    enabled: !!impactAnalysisId,
  });
}

export function useEvaluationSuite() {
  return useMutation({
    mutationFn: (regulationVersionId?: string) =>
      api.post<EvaluationSuiteResult>(
        `/evaluation/run${regulationVersionId ? `?regulation_version_id=${regulationVersionId}` : ""}`
      ),
  });
}
