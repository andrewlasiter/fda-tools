/**
 * FDA-226 [FE-006] FastAPI → Next.js REST Client
 * ================================================
 * Typed Axios client for the FDA Tools bridge server (FastAPI on :18790).
 * Provides:
 *   - Typed request/response interfaces for every endpoint
 *   - Axios instance with base URL from NEXT_PUBLIC_API_URL env var
 *   - X-API-Key injected from NEXT_PUBLIC_FDA_API_KEY env var
 *   - Authorization header auto-injected from Supabase session token
 *   - Structured error types (APIError, ValidationError)
 *   - React Query hooks for all key endpoints
 *
 * Environment variables:
 *   NEXT_PUBLIC_API_URL      — Base URL (default: http://localhost:18790)
 *   NEXT_PUBLIC_FDA_API_KEY  — Bridge server API key
 */

import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosError,
} from "axios";
import { useQuery, useMutation, type UseQueryOptions } from "@tanstack/react-query";
import { getAccessToken } from "@/lib/supabase";

// ── Error types ────────────────────────────────────────────────────────────

/** Structured error returned by the bridge server. */
export interface APIError {
  type:    "api_error";
  status:  number;
  detail:  string;
  path?:   string;
  method?: string;
}

/** Validation error (422 Unprocessable Entity) from FastAPI/Pydantic. */
export interface ValidationError {
  type:   "validation_error";
  status: 422;
  errors: Array<{
    loc:  string[];
    msg:  string;
    type: string;
  }>;
}

/** Union of all client-side error types. */
export type FDAClientError = APIError | ValidationError;

// ── Request / Response types ───────────────────────────────────────────────

export interface HealthResponse {
  status:    "ok" | "degraded" | "error";
  version:   string;
  uptime_s:  number;
  commands:  number;
  sessions:  number;
  timestamp: string;
}

export interface CommandInfo {
  name:        string;
  description: string;
  plugin:      string;
  has_args:    boolean;
}

export interface CommandsResponse {
  commands: CommandInfo[];
  count:    number;
}

export interface ToolInfo {
  name:        string;
  description: string;
  input_schema: Record<string, unknown>;
}

export interface ToolsResponse {
  tools:  ToolInfo[];
  count:  number;
}

export interface ExecuteRequest {
  command:    string;
  args?:      string;
  session_id?: string;
  context?:   Record<string, unknown>;
}

export interface ExecuteResponse {
  output:     string;
  session_id: string;
  command:    string;
  duration_s: number;
  success:    boolean;
  questions?:  PendingQuestion[];
}

export interface SessionCreateRequest {
  session_id?: string;
  metadata?:   Record<string, unknown>;
}

export interface SessionInfo {
  session_id:   string;
  created_at:   string;
  last_used_at: string;
  command_count: number;
  metadata:     Record<string, unknown>;
}

export interface SessionsResponse {
  sessions: SessionInfo[];
  count:    number;
}

export interface PendingQuestion {
  id:       string;
  question: string;
  options?: string[];
  required: boolean;
}

export interface QuestionsResponse {
  session_id: string;
  questions:  PendingQuestion[];
}

export interface AnswerRequest {
  question_id: string;
  answer:      string;
}

export interface AnswerResponse {
  session_id:  string;
  question_id: string;
  accepted:    boolean;
}

export interface AuditIntegrityResponse {
  valid:       boolean;
  entries:     number;
  checksum:    string;
  last_entry:  string | null;
  verified_at: string;
}

// ── Axios instance factory ─────────────────────────────────────────────────

function createAxiosInstance(): AxiosInstance {
  const baseURL =
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:18790";

  const instance = axios.create({
    baseURL,
    timeout: 30_000,
    headers: {
      "Content-Type": "application/json",
      Accept:         "application/json",
    },
  });

  // Request interceptor — inject API key + Supabase Bearer token.
  instance.interceptors.request.use(async (config) => {
    const apiKey = process.env.NEXT_PUBLIC_FDA_API_KEY;
    if (apiKey) {
      config.headers["X-API-Key"] = apiKey;
    }
    // Inject Supabase session token when available.
    const token = await getAccessToken().catch(() => null);
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  });

  // Response interceptor — normalize errors to FDAClientError.
  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      const status = error.response?.status ?? 0;
      const data   = error.response?.data as Record<string, unknown> | undefined;

      if (status === 422 && data && "detail" in data) {
        const ve: ValidationError = {
          type:   "validation_error",
          status: 422,
          errors: data.detail as ValidationError["errors"],
        };
        return Promise.reject(ve);
      }

      const ae: APIError = {
        type:   "api_error",
        status,
        detail: (data?.detail as string) ?? error.message ?? "Unknown error",
        path:   error.config?.url,
        method: error.config?.method?.toUpperCase(),
      };
      return Promise.reject(ae);
    }
  );

  return instance;
}

/** Singleton Axios instance — reused across all API calls. */
let _axiosInstance: AxiosInstance | null = null;

function getAxiosInstance(): AxiosInstance {
  if (!_axiosInstance) _axiosInstance = createAxiosInstance();
  return _axiosInstance;
}

// ── Low-level client ───────────────────────────────────────────────────────

/** Raw API client with one method per endpoint. */
export const fdaApi = {
  // -- Health ----------------------------------------------------------------

  health(config?: AxiosRequestConfig): Promise<HealthResponse> {
    return getAxiosInstance()
      .get<HealthResponse>("/health", config)
      .then((r) => r.data);
  },

  // -- Commands --------------------------------------------------------------

  listCommands(config?: AxiosRequestConfig): Promise<CommandsResponse> {
    return getAxiosInstance()
      .get<CommandsResponse>("/commands", config)
      .then((r) => r.data);
  },

  // -- Tools -----------------------------------------------------------------

  listTools(config?: AxiosRequestConfig): Promise<ToolsResponse> {
    return getAxiosInstance()
      .get<ToolsResponse>("/tools", config)
      .then((r) => r.data);
  },

  // -- Execute ---------------------------------------------------------------

  execute(
    body: ExecuteRequest,
    config?: AxiosRequestConfig
  ): Promise<ExecuteResponse> {
    return getAxiosInstance()
      .post<ExecuteResponse>("/execute", body, config)
      .then((r) => r.data);
  },

  // -- Sessions --------------------------------------------------------------

  createSession(
    body: SessionCreateRequest,
    config?: AxiosRequestConfig
  ): Promise<SessionInfo> {
    return getAxiosInstance()
      .post<SessionInfo>("/session", body, config)
      .then((r) => r.data);
  },

  getSession(
    sessionId: string,
    config?: AxiosRequestConfig
  ): Promise<SessionInfo> {
    return getAxiosInstance()
      .get<SessionInfo>(`/session/${sessionId}`, config)
      .then((r) => r.data);
  },

  listSessions(config?: AxiosRequestConfig): Promise<SessionsResponse> {
    return getAxiosInstance()
      .get<SessionsResponse>("/sessions", config)
      .then((r) => r.data);
  },

  // -- Questions / Answers ---------------------------------------------------

  getQuestions(
    sessionId: string,
    config?: AxiosRequestConfig
  ): Promise<QuestionsResponse> {
    return getAxiosInstance()
      .get<QuestionsResponse>(`/session/${sessionId}/questions`, config)
      .then((r) => r.data);
  },

  answerQuestion(
    sessionId: string,
    body: AnswerRequest,
    config?: AxiosRequestConfig
  ): Promise<AnswerResponse> {
    return getAxiosInstance()
      .post<AnswerResponse>(`/session/${sessionId}/answer`, body, config)
      .then((r) => r.data);
  },

  // -- Audit -----------------------------------------------------------------

  auditIntegrity(
    config?: AxiosRequestConfig
  ): Promise<AuditIntegrityResponse> {
    return getAxiosInstance()
      .get<AuditIntegrityResponse>("/audit/integrity", config)
      .then((r) => r.data);
  },
} as const;

// ── React Query hooks ──────────────────────────────────────────────────────

/** Query key factory — centralises all cache key structures. */
export const queryKeys = {
  health:      ["fda", "health"]                  as const,
  commands:    ["fda", "commands"]                as const,
  tools:       ["fda", "tools"]                   as const,
  sessions:    ["fda", "sessions"]                as const,
  session:     (id: string) => ["fda", "session", id] as const,
  questions:   (id: string) => ["fda", "questions", id] as const,
  audit:       ["fda", "audit", "integrity"]      as const,
} as const;

// -- useHealth ---------------------------------------------------------------

/** Poll the bridge server health endpoint every 30 seconds. */
export function useHealth(
  options?: Omit<UseQueryOptions<HealthResponse>, "queryKey" | "queryFn">
) {
  return useQuery<HealthResponse>({
    queryKey:        queryKeys.health,
    queryFn:         () => fdaApi.health(),
    refetchInterval: 30_000,
    ...options,
  });
}

// -- useCommands -------------------------------------------------------------

export function useCommands(
  options?: Omit<UseQueryOptions<CommandsResponse>, "queryKey" | "queryFn">
) {
  return useQuery<CommandsResponse>({
    queryKey: queryKeys.commands,
    queryFn:  () => fdaApi.listCommands(),
    ...options,
  });
}

// -- useTools ----------------------------------------------------------------

export function useTools(
  options?: Omit<UseQueryOptions<ToolsResponse>, "queryKey" | "queryFn">
) {
  return useQuery<ToolsResponse>({
    queryKey: queryKeys.tools,
    queryFn:  () => fdaApi.listTools(),
    ...options,
  });
}

// -- useSessions -------------------------------------------------------------

export function useSessions(
  options?: Omit<UseQueryOptions<SessionsResponse>, "queryKey" | "queryFn">
) {
  return useQuery<SessionsResponse>({
    queryKey: queryKeys.sessions,
    queryFn:  () => fdaApi.listSessions(),
    ...options,
  });
}

// -- useSession --------------------------------------------------------------

export function useSession(
  sessionId: string,
  options?: Omit<UseQueryOptions<SessionInfo>, "queryKey" | "queryFn">
) {
  return useQuery<SessionInfo>({
    queryKey: queryKeys.session(sessionId),
    queryFn:  () => fdaApi.getSession(sessionId),
    enabled:  Boolean(sessionId),
    ...options,
  });
}

// -- useQuestions ------------------------------------------------------------

export function useQuestions(
  sessionId: string,
  options?: Omit<UseQueryOptions<QuestionsResponse>, "queryKey" | "queryFn">
) {
  return useQuery<QuestionsResponse>({
    queryKey: queryKeys.questions(sessionId),
    queryFn:  () => fdaApi.getQuestions(sessionId),
    enabled:  Boolean(sessionId),
    ...options,
  });
}

// -- useAuditIntegrity -------------------------------------------------------

export function useAuditIntegrity(
  options?: Omit<UseQueryOptions<AuditIntegrityResponse>, "queryKey" | "queryFn">
) {
  return useQuery<AuditIntegrityResponse>({
    queryKey: queryKeys.audit,
    queryFn:  () => fdaApi.auditIntegrity(),
    ...options,
  });
}

// -- useExecute (mutation) ---------------------------------------------------

/**
 * Mutation hook for running FDA commands.
 *
 * @example
 *   const exec = useExecute()
 *   exec.mutateAsync({ command: "/fda:analyze", args: "--code DQY" })
 */
export function useExecute() {
  return useMutation<ExecuteResponse, FDAClientError, ExecuteRequest>({
    mutationFn: (body) => fdaApi.execute(body),
  });
}

// -- useAnswerQuestion (mutation) --------------------------------------------

export function useAnswerQuestion(sessionId: string) {
  return useMutation<AnswerResponse, FDAClientError, AnswerRequest>({
    mutationFn: (body) => fdaApi.answerQuestion(sessionId, body),
  });
}
