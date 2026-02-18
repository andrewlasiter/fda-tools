/**
 * FDA Bridge HTTP Client
 *
 * Robust HTTP client for communicating with the Phase 2 FDA Bridge Server.
 * Implements retry logic with exponential backoff, comprehensive error handling,
 * session management, and request/response logging.
 *
 * The client handles all HTTP interactions between the OpenClaw skill layer
 * and the FDA Bridge Server running on localhost:18790.
 *
 * @module bridge/client
 * @version 1.1.0
 */

import type {
  BridgeClientConfig,
  BridgeErrorType,
  CommandsResponse,
  ExecuteRequest,
  ExecuteResponse,
  HealthResponse,
  SessionRequest,
  SessionResponse,
  SessionDetail,
  SessionListResponse,
  PendingQuestionsResponse,
  AnswerSubmitRequest,
  ToolsResponse,
  AuditIntegrityResponse,
} from './types';

// ============================================================
// Constants
// ============================================================

const DEFAULT_BASE_URL = 'http://localhost:18790';
const DEFAULT_TIMEOUT = 120_000; // 2 minutes
const DEFAULT_RETRIES = 3;
const DEFAULT_RETRY_DELAY = 1_000; // 1 second
const API_KEY_HEADER = 'X-API-Key';

/**
 * Environment variable name for the bridge API key.
 * Set this to authenticate with the FDA Bridge Server.
 */
const API_KEY_ENV_VAR = 'FDA_BRIDGE_API_KEY';

/**
 * HTTP status codes that should trigger a retry.
 * 408: Request Timeout
 * 429: Too Many Requests
 * 500: Internal Server Error
 * 502: Bad Gateway
 * 503: Service Unavailable
 * 504: Gateway Timeout
 */
const RETRYABLE_STATUS_CODES = new Set([408, 429, 500, 502, 503, 504]);

// ============================================================
// Error Classes
// ============================================================

/**
 * Custom error class for bridge communication failures.
 * Provides structured error information for client-side handling.
 */
export class BridgeClientError extends Error {
  /** Categorized error type for programmatic handling */
  public readonly errorType: BridgeErrorType;

  /** HTTP status code (if applicable) */
  public readonly status?: number;

  /** Number of retry attempts made before failing */
  public readonly attempts: number;

  /** Original error that caused this failure */
  public readonly cause?: Error;

  constructor(
    message: string,
    errorType: BridgeErrorType,
    options?: {
      status?: number;
      attempts?: number;
      cause?: Error;
    }
  ) {
    super(message);
    this.name = 'BridgeClientError';
    this.errorType = errorType;
    this.status = options?.status;
    this.attempts = options?.attempts ?? 1;
    this.cause = options?.cause;
  }
}

// ============================================================
// Logger
// ============================================================

/**
 * Simple structured logger for bridge client operations.
 * Outputs to console with timestamps and request context.
 */
class BridgeLogger {
  private enabled: boolean;

  constructor(enabled: boolean = true) {
    this.enabled = enabled;
  }

  info(message: string, data?: Record<string, unknown>): void {
    if (!this.enabled) return;
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] [FDA-Bridge] ${message}`, data ?? '');
  }

  warn(message: string, data?: Record<string, unknown>): void {
    if (!this.enabled) return;
    const timestamp = new Date().toISOString();
    console.warn(`[${timestamp}] [FDA-Bridge] WARN: ${message}`, data ?? '');
  }

  error(message: string, data?: Record<string, unknown>): void {
    const timestamp = new Date().toISOString();
    console.error(`[${timestamp}] [FDA-Bridge] ERROR: ${message}`, data ?? '');
  }
}

// ============================================================
// Bridge Client
// ============================================================

/**
 * HTTP client for the FDA Bridge Server.
 *
 * Provides methods for all bridge API endpoints with:
 * - Retry logic with exponential backoff
 * - Comprehensive error classification
 * - Request/response logging
 * - Timeout handling via AbortSignal
 * - Session management helpers
 *
 * @example
 * ```typescript
 * const client = new BridgeClient({ baseUrl: 'http://localhost:18790' });
 *
 * // Check server health
 * const health = await client.health();
 * console.log(`Server status: ${health.status}`);
 *
 * // Execute a command
 * const result = await client.execute({
 *   command: 'research',
 *   args: '--product-code DQY',
 *   user_id: 'user-123',
 *   channel: 'whatsapp'
 * });
 *
 * if (result.success) {
 *   console.log(result.result);
 * } else {
 *   console.error(result.error);
 * }
 * ```
 */
export class BridgeClient {
  private readonly baseUrl: string;
  private readonly timeout: number;
  private readonly retries: number;
  private readonly retryDelay: number;
  private readonly apiKey: string | undefined;
  private readonly logger: BridgeLogger;

  constructor(config: BridgeClientConfig = {}) {
    this.baseUrl = (config.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, '');
    this.timeout = config.timeout ?? DEFAULT_TIMEOUT;
    this.retries = config.retries ?? DEFAULT_RETRIES;
    this.retryDelay = config.retryDelay ?? DEFAULT_RETRY_DELAY;
    // API key resolution: explicit config > environment variable > undefined
    this.apiKey = config.apiKey ?? process.env[API_KEY_ENV_VAR];
    this.logger = new BridgeLogger();

    if (!this.apiKey) {
      this.logger.warn(
        `No API key configured. Set ${API_KEY_ENV_VAR} environment variable ` +
        `or pass apiKey in BridgeClientConfig. Authenticated endpoints will return 401.`
      );
    }
  }

  // ----------------------------------------------------------
  // Public API Methods
  // ----------------------------------------------------------

  /**
   * Execute an FDA command through the bridge server.
   *
   * This is the primary method for running FDA commands. It sends the
   * command to the bridge server which handles security evaluation,
   * audit logging, and tool emulation.
   *
   * @param request - Command execution request
   * @returns Execution result with classification and session info
   * @throws {BridgeClientError} On connection, timeout, or server errors
   */
  async execute(request: ExecuteRequest): Promise<ExecuteResponse> {
    this.logger.info('Executing command', {
      command: request.command,
      args: request.args,
      channel: request.channel,
      user_id: request.user_id,
    });

    const response = await this.retryRequest<ExecuteResponse>(
      () => this.post<ExecuteResponse>('/execute', request)
    );

    this.logger.info('Command completed', {
      command: request.command,
      success: response.success,
      classification: response.classification,
      duration_ms: response.duration_ms,
    });

    return response;
  }

  /**
   * Check bridge server health status.
   *
   * Returns server status, available LLM providers, active sessions,
   * and command count. Useful for verifying the bridge is running
   * before attempting command execution.
   *
   * @returns Health status information
   * @throws {BridgeClientError} If server is not accessible
   */
  async health(): Promise<HealthResponse> {
    return this.retryRequest<HealthResponse>(
      () => this.get<HealthResponse>('/health')
    );
  }

  /**
   * List all available FDA commands.
   *
   * Returns command names, descriptions, argument hints, and
   * allowed tools parsed from command markdown frontmatter.
   *
   * @returns List of available commands with metadata
   */
  async listCommands(): Promise<CommandsResponse> {
    return this.retryRequest<CommandsResponse>(
      () => this.get<CommandsResponse>('/commands')
    );
  }

  /**
   * Create or retrieve a session.
   *
   * If session_id is provided and exists, returns the existing session.
   * Otherwise creates a new session for the given user.
   *
   * @param userId - User identifier
   * @param sessionId - Optional existing session ID
   * @returns Session details
   */
  async createSession(
    userId: string,
    sessionId?: string
  ): Promise<SessionResponse> {
    const request: SessionRequest = {
      user_id: userId,
      session_id: sessionId,
    };
    return this.retryRequest<SessionResponse>(
      () => this.post<SessionResponse>('/session', request)
    );
  }

  /**
   * Get session details by ID.
   *
   * @param sessionId - Session identifier
   * @returns Session details including context and metadata
   * @throws {BridgeClientError} With SESSION_NOT_FOUND if session does not exist
   */
  async getSession(sessionId: string): Promise<SessionDetail> {
    return this.retryRequest<SessionDetail>(
      () => this.get<SessionDetail>(`/session/${encodeURIComponent(sessionId)}`)
    );
  }

  /**
   * List active sessions, optionally filtered by user.
   *
   * @param userId - Optional user ID filter
   * @returns List of session summaries
   */
  async listSessions(userId?: string): Promise<SessionListResponse> {
    const query = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
    return this.retryRequest<SessionListResponse>(
      () => this.get<SessionListResponse>(`/sessions${query}`)
    );
  }

  /**
   * Get pending questions for a session.
   *
   * Some FDA commands may queue questions that need user input
   * before the command can complete (e.g., "Which predicate do
   * you want to select?").
   *
   * @param sessionId - Session identifier
   * @returns List of pending questions
   */
  async getPendingQuestions(
    sessionId: string
  ): Promise<PendingQuestionsResponse> {
    return this.retryRequest<PendingQuestionsResponse>(
      () =>
        this.get<PendingQuestionsResponse>(
          `/session/${encodeURIComponent(sessionId)}/questions`
        )
    );
  }

  /**
   * Submit an answer to a pending question.
   *
   * @param sessionId - Session identifier
   * @param questionId - Question identifier
   * @param answer - User's answer
   * @returns Success confirmation
   */
  async submitAnswer(
    sessionId: string,
    questionId: string,
    answer: string
  ): Promise<{ success: boolean; question_id: string }> {
    const request: AnswerSubmitRequest = {
      question_id: questionId,
      answer,
    };
    return this.retryRequest(
      () =>
        this.post<{ success: boolean; question_id: string }>(
          `/session/${encodeURIComponent(sessionId)}/answer`,
          request
        )
    );
  }

  /**
   * List available tool emulators.
   *
   * @returns List of tool names (Read, Write, Bash, Glob, Grep, AskUserQuestion)
   */
  async listTools(): Promise<ToolsResponse> {
    return this.retryRequest<ToolsResponse>(
      () => this.get<ToolsResponse>('/tools')
    );
  }

  /**
   * Verify audit log integrity.
   *
   * Checks that the append-only audit log has not been tampered with.
   *
   * @returns Integrity verification results
   */
  async verifyAuditIntegrity(): Promise<AuditIntegrityResponse> {
    return this.retryRequest<AuditIntegrityResponse>(
      () => this.get<AuditIntegrityResponse>('/audit/integrity')
    );
  }

  // ----------------------------------------------------------
  // HTTP Helpers
  // ----------------------------------------------------------

  /**
   * Build common headers for all requests, including API key authentication.
   */
  private buildHeaders(extra?: Record<string, string>): Record<string, string> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...extra,
    };
    if (this.apiKey) {
      headers[API_KEY_HEADER] = this.apiKey;
    }
    return headers;
  }

  /**
   * Send a GET request to the bridge server.
   * Includes X-API-Key header for authentication.
   */
  private async get<T>(path: string): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: this.buildHeaders(),
        signal: controller.signal,
      });

      return this.handleResponse<T>(response, 'GET', path);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Send a POST request to the bridge server.
   * Includes X-API-Key header for authentication.
   */
  private async post<T>(path: string, body: unknown): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: this.buildHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      return this.handleResponse<T>(response, 'POST', path);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Process HTTP response and extract JSON body.
   * Throws typed errors for non-2xx responses.
   */
  private async handleResponse<T>(
    response: Response,
    method: string,
    path: string
  ): Promise<T> {
    if (response.ok) {
      return (await response.json()) as T;
    }

    // Parse error body
    let detail = `${method} ${path}: ${response.status} ${response.statusText}`;
    try {
      const errorBody = await response.json();
      if (errorBody?.detail) {
        detail = errorBody.detail;
      }
    } catch {
      // Body is not JSON; use status text
    }

    // Classify error type
    const errorType = this.classifyHttpError(response.status, detail);

    throw new BridgeClientError(detail, errorType, {
      status: response.status,
    });
  }

  /**
   * Classify an HTTP error status into a BridgeErrorType.
   */
  private classifyHttpError(status: number, detail: string): BridgeErrorType {
    if (status === 401) {
      return 'AUTHENTICATION_REQUIRED';
    }
    if (status === 429) {
      return 'RATE_LIMITED';
    }
    if (status === 404) {
      if (detail.toLowerCase().includes('session')) {
        return 'SESSION_NOT_FOUND';
      }
      if (detail.toLowerCase().includes('command')) {
        return 'COMMAND_NOT_FOUND';
      }
      return 'COMMAND_NOT_FOUND';
    }
    if (status === 403 || detail.toLowerCase().includes('security')) {
      return 'SECURITY_VIOLATION';
    }
    if (status === 408) {
      return 'TIMEOUT';
    }
    if (status === 422) {
      return 'INVALID_REQUEST';
    }
    if (status >= 500) {
      return 'SERVER_ERROR';
    }
    return 'UNKNOWN';
  }

  // ----------------------------------------------------------
  // Retry Logic
  // ----------------------------------------------------------

  /**
   * Execute a request function with retry logic.
   *
   * Implements exponential backoff:
   * - Attempt 0: immediate
   * - Attempt 1: retryDelay ms
   * - Attempt 2: retryDelay * 2 ms
   * - Attempt 3: retryDelay * 4 ms
   *
   * Only retries on:
   * - Network errors (connection refused, DNS failure)
   * - Timeout errors (AbortError)
   * - Retryable HTTP status codes (408, 429, 500, 502, 503, 504)
   *
   * Does NOT retry on:
   * - 4xx client errors (except 408, 429)
   * - Security violations
   * - Command not found
   */
  private async retryRequest<T>(
    fn: () => Promise<T>,
    attempt: number = 0
  ): Promise<T> {
    try {
      return await fn();
    } catch (error) {
      const isLastAttempt = attempt >= this.retries;
      const shouldRetry = this.isRetryable(error);

      if (isLastAttempt || !shouldRetry) {
        // Wrap non-BridgeClientError errors
        if (error instanceof BridgeClientError) {
          throw new BridgeClientError(error.message, error.errorType, {
            status: error.status,
            attempts: attempt + 1,
            cause: error.cause,
          });
        }

        const classifiedError = this.classifyError(error as Error);
        throw new BridgeClientError(
          classifiedError.message,
          classifiedError.errorType,
          {
            attempts: attempt + 1,
            cause: error as Error,
          }
        );
      }

      // Exponential backoff
      const delay = this.retryDelay * Math.pow(2, attempt);
      this.logger.warn(
        `Retry attempt ${attempt + 1}/${this.retries} after ${delay}ms`,
        {
          error: (error as Error).message,
        }
      );

      await this.sleep(delay);
      return this.retryRequest(fn, attempt + 1);
    }
  }

  /**
   * Determine if an error is retryable.
   *
   * Authentication errors (401) are NEVER retried -- they indicate
   * a missing or invalid API key that will not resolve with retries.
   */
  private isRetryable(error: unknown): boolean {
    // Network errors (connection refused, etc.) are retryable
    if (error instanceof TypeError) {
      // fetch() throws TypeError for network failures
      return true;
    }

    // AbortError (timeout) is retryable
    if (error instanceof DOMException && error.name === 'AbortError') {
      return true;
    }

    // BridgeClientError with retryable status code
    if (error instanceof BridgeClientError && error.status !== undefined) {
      // Never retry authentication failures
      if (error.status === 401) {
        return false;
      }
      return RETRYABLE_STATUS_CODES.has(error.status);
    }

    return false;
  }

  /**
   * Classify a raw error into a structured BridgeClientError.
   */
  private classifyError(error: Error): {
    message: string;
    errorType: BridgeErrorType;
  } {
    const message = error.message || 'Unknown error';

    // Connection refused
    if (
      message.includes('ECONNREFUSED') ||
      message.includes('fetch failed') ||
      message.includes('Failed to fetch')
    ) {
      return {
        message:
          'FDA Bridge Server is not running. Start it with: python3 bridge/server.py',
        errorType: 'CONNECTION_REFUSED',
      };
    }

    // Timeout
    if (
      error.name === 'AbortError' ||
      message.includes('timeout') ||
      message.includes('aborted')
    ) {
      return {
        message: `Request timed out after ${this.timeout}ms`,
        errorType: 'TIMEOUT',
      };
    }

    return {
      message,
      errorType: 'UNKNOWN',
    };
  }

  /**
   * Sleep for a specified number of milliseconds.
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
