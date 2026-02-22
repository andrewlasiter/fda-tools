/**
 * FDA-244 — Typed REST client for the MDRP FastAPI bridge server.
 *
 * Architecture:
 *  - Native fetch (no Axios); base URL from NEXT_PUBLIC_API_URL env var
 *  - Supabase access token auto-injected as Bearer header for server endpoints
 *  - Bridge API key injected from NEXT_PUBLIC_BRIDGE_API_KEY for direct bridge calls
 *  - All response shapes are typed; error path throws ApiError
 *  - React Query v5 hooks exported for each key read endpoint
 *
 * Bridge server runs at localhost:18790 by default.
 * In cloud/production the FastAPI service lives at NEXT_PUBLIC_API_URL.
 */

import { useQuery, useMutation, type UseQueryOptions } from "@tanstack/react-query";
import { getSupabaseClient } from "@/lib/supabase";

// ── Base URL ─────────────────────────────────────────────────────────────────

const API_BASE =
  (typeof process !== "undefined" ? process.env.NEXT_PUBLIC_API_URL : undefined) ??
  "http://localhost:18790";

// ── Error type ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Response models (mirror FastAPI Pydantic schemas) ────────────────────────

export interface LlmProvider {
  available: boolean;
  endpoint?: string;
  api_key_set?: boolean;
}

export interface HealthAlert {
  type: string;
  severity: "WARNING" | "CRITICAL";
  threshold_pct?: number;
  current_pct?: number;
  threshold_ms?: number;
  current_p95_ms?: number;
  threshold?: number;
  current?: number;
  message: string;
}

export interface HealthResponse {
  status: "healthy" | "degraded";
  version: string;
  auth_required: boolean;
  rate_limiting: boolean;
  uptime_seconds: number;
  llm_providers: Record<string, LlmProvider>;
  sessions_active: number;
  commands_available: number;
  last_request_at: string | null;
  alerts: HealthAlert[];
  alerts_active: number;
}

export interface ReadinessResponse {
  ready: boolean;
  issues: string[];
}

export interface CommandInfo {
  name: string;
  description: string;
  args: string;
  allowed_tools: string;
}

export interface CommandsResponse {
  commands: CommandInfo[];
  total: number;
}

export interface ExecuteRequest {
  command: string;
  args?: string;
  user_id: string;
  session_id?: string;
  channel: string;
  context?: string;
}

export interface CommandMetadata {
  files_read: string[];
  files_written: string[];
  command_found: boolean;
  exit_code?: number;
  timeout?: boolean;
  timeout_seconds?: number;
  security_blocked?: boolean;
  exception?: string;
}

export interface ExecuteResponse {
  success: boolean;
  result?: string;
  error?: string;
  classification: "PUBLIC" | "RESTRICTED" | "CONFIDENTIAL";
  llm_provider: string;
  warnings: string[];
  session_id: string;
  duration_ms?: number;
  command_metadata?: CommandMetadata;
}

export interface SessionRequest {
  user_id: string;
  session_id?: string;
}

export interface SessionResponse {
  session_id: string;
  user_id: string;
  created_at: string;
  last_accessed: string;
  context: Record<string, unknown>;
  is_new: boolean;
}

export interface SessionSummary {
  session_id: string;
  user_id: string;
  created_at: string;
  last_accessed: string;
}

export interface SessionsResponse {
  sessions: SessionSummary[];
  total: number;
}

export interface PendingQuestion {
  id: string;
  question: string;
  created_at: string;
}

export interface QuestionsResponse {
  questions: PendingQuestion[];
  count: number;
}

export interface AnswerRequest {
  question_id: string;
  answer: string;
}

export interface AnswerResponse {
  success: boolean;
  question_id: string;
}

export interface MetricsRequests {
  total: number;
  errors: number;
  error_rate_pct: number;
}

export interface MetricsResponseTime {
  avg: number;
  p50: number;
  p95: number;
  p99: number;
  samples: number;
}

export interface MetricsResponse {
  requests: MetricsRequests;
  response_time_ms: MetricsResponseTime;
  sessions: { active: number };
  memory_mb: number;
  last_request_at: string | null;
  alerts_active: number;
  uptime_seconds: number;
}

export interface AuditIntegrityResponse {
  valid: boolean;
  entries_checked: number;
  violations: string[];
}

export interface ToolExecuteRequest {
  tool: "Read" | "Write" | "Bash" | "Grep" | "Glob" | "AskUserQuestion";
  session_id: string;
  project_root: string;
  params: Record<string, unknown>;
}

export interface ToolExecuteResponse {
  success: boolean;
  result: unknown;
  tool: string;
}

// ── Future MDRP domain types (used by planned routes FDA-232+) ───────────────

export type NpdStage =
  | "CONCEPT"
  | "CLASSIFY"
  | "PREDICATE"
  | "PATHWAY"
  | "PRESUB"
  | "TESTING"
  | "DRAFTING"
  | "REVIEW"
  | "SUBMIT"
  | "FDA_REVIEW"
  | "CLEARED"
  | "POST_MARKET";

export interface Project {
  id: string;
  tenant_id: string;
  name: string;
  device_name: string;
  product_code?: string;
  stage: NpdStage;
  sri_score: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectsResponse {
  projects: Project[];
  total: number;
}

export type AgentStatus = "idle" | "running" | "waiting" | "done" | "failed";

export interface AgentRun {
  id: string;
  project_id?: string;
  name: string;
  status: AgentStatus;
  task?: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  output?: string;
  score?: number;
}

export interface AgentsResponse {
  agents: AgentRun[];
  total: number;
}

export interface ResearchResult {
  id: string;
  source: "k510" | "guidance" | "maude" | "recall" | "pubmed";
  title: string;
  snippet: string;
  score: number;
  url?: string;
}

export interface ResearchResponse {
  query: string;
  results: ResearchResult[];
  total: number;
  duration_ms: number;
}

export interface Document {
  id: string;
  project_id: string;
  section: string;
  title: string;
  content: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentsResponse {
  documents: Document[];
  total: number;
}

// ── Core fetch client ─────────────────────────────────────────────────────────

async function getAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // Inject Supabase access token for MDRP JWT-protected endpoints
  try {
    const supabase = getSupabaseClient();
    const { data } = await supabase.auth.getSession();
    if (data.session?.access_token) {
      headers["Authorization"] = `Bearer ${data.session.access_token}`;
    }
  } catch {
    // No session — request proceeds without auth (public endpoints will succeed)
  }

  // Inject bridge API key when present (development / self-hosted mode)
  const bridgeKey =
    typeof process !== "undefined"
      ? process.env.NEXT_PUBLIC_BRIDGE_API_KEY
      : undefined;
  if (bridgeKey) {
    headers["X-API-Key"] = bridgeKey;
  }

  return headers;
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = await getAuthHeaders();
  const url = `${API_BASE}${path}`;

  const res = await fetch(url, {
    ...options,
    headers: { ...headers, ...(options.headers as Record<string, string> | undefined) },
  });

  if (!res.ok) {
    let detail: unknown;
    try {
      detail = await res.json();
    } catch {
      detail = await res.text();
    }
    const message =
      typeof detail === "object" && detail !== null && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `HTTP ${res.status}`;
    throw new ApiError(res.status, message, detail);
  }

  return res.json() as Promise<T>;
}

// ── API methods ───────────────────────────────────────────────────────────────

export const api = {
  // Health & readiness (unauthenticated)
  health: () =>
    apiFetch<HealthResponse>("/health"),

  readiness: () =>
    apiFetch<ReadinessResponse>("/ready"),

  // Commands (authenticated)
  commands: () =>
    apiFetch<CommandsResponse>("/commands"),

  // Execute (authenticated, rate-limited 30/min)
  execute: (body: ExecuteRequest) =>
    apiFetch<ExecuteResponse>("/execute", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Sessions (authenticated)
  createSession: (body: SessionRequest) =>
    apiFetch<SessionResponse>("/session", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getSession: (sessionId: string) =>
    apiFetch<SessionResponse>(`/session/${encodeURIComponent(sessionId)}`),

  listSessions: (userId?: string) =>
    apiFetch<SessionsResponse>(
      userId ? `/sessions?user_id=${encodeURIComponent(userId)}` : "/sessions",
    ),

  getQuestions: (sessionId: string) =>
    apiFetch<QuestionsResponse>(
      `/session/${encodeURIComponent(sessionId)}/questions`,
    ),

  submitAnswer: (sessionId: string, body: AnswerRequest) =>
    apiFetch<AnswerResponse>(
      `/session/${encodeURIComponent(sessionId)}/answer`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  // Tools (authenticated)
  executeTool: (body: ToolExecuteRequest) =>
    apiFetch<ToolExecuteResponse>("/tool/execute", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Metrics & audit (authenticated)
  metrics: () =>
    apiFetch<MetricsResponse>("/metrics"),

  auditIntegrity: () =>
    apiFetch<AuditIntegrityResponse>("/audit/integrity"),

  // ── Planned MDRP domain endpoints (FDA-232+) ───────────────────────────────

  projects: {
    list: () =>
      apiFetch<ProjectsResponse>("/projects"),
    get: (id: string) =>
      apiFetch<Project>(`/projects/${encodeURIComponent(id)}`),
  },

  agents: {
    list: (projectId?: string) =>
      apiFetch<AgentsResponse>(
        projectId
          ? `/agents?project_id=${encodeURIComponent(projectId)}`
          : "/agents",
      ),
    get: (id: string) =>
      apiFetch<AgentRun>(`/agents/${encodeURIComponent(id)}`),
  },

  research: {
    search: (query: string, projectId?: string) =>
      apiFetch<ResearchResponse>(
        `/research?q=${encodeURIComponent(query)}` +
          (projectId ? `&project_id=${encodeURIComponent(projectId)}` : ""),
      ),
  },

  documents: {
    list: (projectId: string) =>
      apiFetch<DocumentsResponse>(
        `/documents?project_id=${encodeURIComponent(projectId)}`,
      ),
    get: (id: string) =>
      apiFetch<Document>(`/documents/${encodeURIComponent(id)}`),
  },
} as const;

// ── Query keys ────────────────────────────────────────────────────────────────

export const queryKeys = {
  health: ["health"] as const,
  readiness: ["readiness"] as const,
  commands: ["commands"] as const,
  metrics: ["metrics"] as const,
  session: (id: string) => ["session", id] as const,
  sessions: (userId?: string) => ["sessions", userId] as const,
  questions: (sessionId: string) => ["questions", sessionId] as const,
  projects: () => ["projects"] as const,
  project: (id: string) => ["projects", id] as const,
  agents: (projectId?: string) => ["agents", projectId] as const,
  agent: (id: string) => ["agents", "detail", id] as const,
  research: (query: string, projectId?: string) =>
    ["research", query, projectId] as const,
  documents: (projectId: string) => ["documents", projectId] as const,
  document: (id: string) => ["documents", "detail", id] as const,
  auditIntegrity: ["auditIntegrity"] as const,
} as const;

// ── React Query v5 hooks ──────────────────────────────────────────────────────

export function useHealth(
  options?: Partial<UseQueryOptions<HealthResponse>>,
) {
  return useQuery<HealthResponse>({
    queryKey: queryKeys.health,
    queryFn: api.health,
    refetchInterval: 30_000,
    ...options,
  });
}

export function useReadiness() {
  return useQuery<ReadinessResponse>({
    queryKey: queryKeys.readiness,
    queryFn: api.readiness,
    refetchInterval: 60_000,
  });
}

export function useCommands(
  options?: Partial<UseQueryOptions<CommandsResponse>>,
) {
  return useQuery<CommandsResponse>({
    queryKey: queryKeys.commands,
    queryFn: api.commands,
    staleTime: 5 * 60_000, // commands change rarely
    ...options,
  });
}

export function useMetrics(
  options?: Partial<UseQueryOptions<MetricsResponse>>,
) {
  return useQuery<MetricsResponse>({
    queryKey: queryKeys.metrics,
    queryFn: api.metrics,
    refetchInterval: 15_000,
    ...options,
  });
}

export function useSessions(userId?: string) {
  return useQuery<SessionsResponse>({
    queryKey: queryKeys.sessions(userId),
    queryFn: () => api.listSessions(userId),
  });
}

export function useSession(sessionId: string) {
  return useQuery<SessionResponse>({
    queryKey: queryKeys.session(sessionId),
    queryFn: () => api.getSession(sessionId),
    enabled: Boolean(sessionId),
  });
}

export function useQuestions(sessionId: string) {
  return useQuery<QuestionsResponse>({
    queryKey: queryKeys.questions(sessionId),
    queryFn: () => api.getQuestions(sessionId),
    refetchInterval: 5_000,
    enabled: Boolean(sessionId),
  });
}

export function useProjects(
  options?: Partial<UseQueryOptions<ProjectsResponse>>,
) {
  return useQuery<ProjectsResponse>({
    queryKey: queryKeys.projects(),
    queryFn: api.projects.list,
    ...options,
  });
}

export function useProject(id: string) {
  return useQuery<Project>({
    queryKey: queryKeys.project(id),
    queryFn: () => api.projects.get(id),
    enabled: Boolean(id),
  });
}

export function useAgents(projectId?: string) {
  return useQuery<AgentsResponse>({
    queryKey: queryKeys.agents(projectId),
    queryFn: () => api.agents.list(projectId),
    refetchInterval: 5_000, // poll while agents may be running
  });
}

export function useAgent(id: string) {
  return useQuery<AgentRun>({
    queryKey: queryKeys.agent(id),
    queryFn: () => api.agents.get(id),
    enabled: Boolean(id),
  });
}

export function useResearch(query: string, projectId?: string) {
  return useQuery<ResearchResponse>({
    queryKey: queryKeys.research(query, projectId),
    queryFn: () => api.research.search(query, projectId),
    enabled: query.trim().length >= 2,
    staleTime: 60_000,
  });
}

export function useDocuments(projectId: string) {
  return useQuery<DocumentsResponse>({
    queryKey: queryKeys.documents(projectId),
    queryFn: () => api.documents.list(projectId),
    enabled: Boolean(projectId),
  });
}

// ── Research: semantic search types / hooks (FDA-233) ────────────────────────

export interface GuidanceSearchRequest {
  query:     string;
  top_k?:    number;
  threshold?: number;
}

export interface GuidanceChunkResult {
  id:          string;
  doc_id:      string;
  doc_title:   string;
  doc_url:     string;
  chunk_index: number;
  content:     string;
  similarity:  number;
}

export interface GuidanceSearchResponse {
  query:   string;
  count:   number;
  results: GuidanceChunkResult[];
  model:   string;
  error?:  string | null;
}

export interface SignalResult {
  date:        string;
  count:       number;
  severity:    "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  description: string;
  event_types: string[];
  z_score:     number;
}

export interface SignalResponse {
  product_code:  string;
  window_days:   number;
  generated_at:  string;
  total_events:  number;
  signals:       SignalResult[];
  baseline_stats: {
    mean:   number;
    std:    number;
    median: number;
    n_days: number;
  };
}

export function useGuidanceSearch() {
  return useMutation<GuidanceSearchResponse, ApiError, GuidanceSearchRequest>({
    mutationFn: (body) =>
      apiFetch<GuidanceSearchResponse>("/research/search", {
        method: "POST",
        body:   JSON.stringify(body),
      }),
  });
}

export function useSignals(productCode: string, days = 90) {
  return useQuery<SignalResponse>({
    queryKey: ["signals", productCode, days],
    queryFn: () =>
      apiFetch<SignalResponse>(
        `/research/signals/${encodeURIComponent(productCode)}?days=${days}`,
      ),
    enabled: productCode.trim().length >= 2,
    staleTime: 60_000,
  });
}

// ── Research: clustering types / hooks (FDA-234) ─────────────────────────────

export interface ClusterDoc {
  doc_id:    string;
  doc_title: string;
  doc_url:   string;
}

export interface GuidanceCluster {
  cluster_id: number;
  label:      string;
  doc_count:  number;
  docs:       ClusterDoc[];
}

export interface DendrogramData {
  icoord: number[][];
  dcoord: number[][];
  labels: string[];
}

export interface ClusterResult {
  k:            number;
  n_docs:       number;
  generated_at: string;
  cache_hash:   string;
  clusters:     GuidanceCluster[];
  dendrogram:   DendrogramData;
}

// ── Research: freshness types / hooks (FDA-235) ───────────────────────────────

export interface DocFreshnessStatus {
  doc_id:        string;
  url:           string;
  status:        "FRESH" | "STALE" | "UNKNOWN" | "ERROR";
  reason:        string;
  etag?:         string | null;
  last_modified?: string | null;
  checked_at?:   string | null;
}

export interface FreshnessReport {
  generated_at:  string;
  total_docs:    number;
  fresh_count:   number;
  stale_count:   number;
  unknown_count: number;
  error_count:   number;
  freshness_pct: number;
  stale_docs:    DocFreshnessStatus[];
  unknown_docs:  DocFreshnessStatus[];
}

export function useClusters(force = false) {
  return useQuery<ClusterResult, ApiError>({
    queryKey: ["clusters", force],
    queryFn:  () =>
      apiFetch<ClusterResult>(`/research/clusters${force ? "?force=true" : ""}`),
    staleTime: 60 * 60_000, // 1 hour — matches 12h server cache
  });
}

export function useFreshness(force = false) {
  return useQuery<FreshnessReport, ApiError>({
    queryKey: ["freshness", force],
    queryFn:  () =>
      apiFetch<FreshnessReport>(`/research/freshness${force ? "?force=true" : ""}`),
    staleTime: 30 * 60_000,
  });
}

// ── Mutation hooks ────────────────────────────────────────────────────────────

export function useExecuteCommand() {
  return useMutation<ExecuteResponse, ApiError, ExecuteRequest>({
    mutationFn: api.execute,
  });
}

export function useCreateSession() {
  return useMutation<SessionResponse, ApiError, SessionRequest>({
    mutationFn: api.createSession,
  });
}

export function useSubmitAnswer(sessionId: string) {
  return useMutation<AnswerResponse, ApiError, AnswerRequest>({
    mutationFn: (body) => api.submitAnswer(sessionId, body),
  });
}
