/**
 * FDA Bridge Server TypeScript Type Definitions
 *
 * Comprehensive type definitions for the HTTP REST API bridge
 * connecting OpenClaw skills to the FDA Tools plugin.
 *
 * These types mirror the Pydantic models defined in bridge/server.py
 * and provide compile-time type safety for all bridge interactions.
 *
 * @module bridge/types
 * @version 1.0.0
 */

// ============================================================
// Data Classification
// ============================================================

/**
 * Data sensitivity classification levels.
 *
 * PUBLIC    - FDA databases, published summaries. Safe for any LLM or channel.
 * RESTRICTED - Derived intelligence, analysis. Cloud LLM with warnings.
 * CONFIDENTIAL - Company documents, draft submissions. Local LLM only, file output only.
 */
export type DataClassification = 'PUBLIC' | 'RESTRICTED' | 'CONFIDENTIAL';

/**
 * Supported LLM providers for processing FDA data.
 *
 * ollama    - Local LLM (required for CONFIDENTIAL data)
 * anthropic - Claude (cloud, safe for PUBLIC/RESTRICTED)
 * openai    - GPT (cloud, safe for PUBLIC/RESTRICTED)
 * none      - No provider available
 */
export type LLMProvider = 'ollama' | 'anthropic' | 'openai' | 'none';

// ============================================================
// Bridge Client Configuration
// ============================================================

/**
 * Configuration for the BridgeClient HTTP client.
 */
export interface BridgeClientConfig {
  /** Base URL of the FDA Bridge Server. Default: http://localhost:18790 */
  baseUrl?: string;

  /** Request timeout in milliseconds. Default: 120000 (2 minutes) */
  timeout?: number;

  /** Maximum number of retry attempts. Default: 3 */
  retries?: number;

  /** Initial retry delay in milliseconds (doubles with each retry). Default: 1000 */
  retryDelay?: number;

  /** Optional API key for authenticated requests. */
  apiKey?: string;
}

// ============================================================
// Execute Endpoint
// ============================================================

/**
 * Request body for POST /execute endpoint.
 *
 * Executes an FDA command through the bridge server with
 * security enforcement, audit logging, and session management.
 */
export interface ExecuteRequest {
  /** FDA command name (e.g., 'research', 'validate', 'draft') */
  command: string;

  /** Command arguments (e.g., '--product-code DQY --years 2024') */
  args?: string;

  /** User identifier for audit trail and session management */
  user_id: string;

  /** Session ID for conversation continuity. Creates new session if omitted. */
  session_id?: string;

  /**
   * Output channel identifier.
   * Determines security restrictions:
   * - 'file' allows all classifications
   * - 'whatsapp'/'telegram'/'slack'/'discord' blocked for CONFIDENTIAL
   * - 'webhook' depends on security config
   */
  channel: string;

  /** Additional context for the command (e.g., conversation history summary) */
  context?: string;
}

/**
 * Response body from POST /execute endpoint.
 */
export interface ExecuteResponse {
  /** Whether the command executed successfully */
  success: boolean;

  /** Command output (present when success is true) */
  result?: string;

  /** Error message (present when success is false) */
  error?: string;

  /** Data classification level assigned by SecurityGateway */
  classification: DataClassification;

  /** LLM provider selected based on classification and availability */
  llm_provider: LLMProvider;

  /** Security warnings (e.g., "RESTRICTED data: verify before sharing") */
  warnings?: string[];

  /** Session ID (may be newly created or existing) */
  session_id: string;

  /** Execution duration in milliseconds */
  duration_ms?: number;

  /** Additional metadata about the execution */
  command_metadata?: CommandMetadata;
}

/**
 * Metadata about command execution results.
 */
export interface CommandMetadata {
  /** Files that were read during execution */
  files_read: string[];

  /** Files that were written during execution */
  files_written: string[];

  /** Whether the command was found in the commands directory */
  command_found: boolean;
}

// ============================================================
// Health Endpoint
// ============================================================

/**
 * Response body from GET /health endpoint.
 */
export interface HealthResponse {
  /** Server health status */
  status: 'healthy' | 'degraded' | 'unhealthy';

  /** Bridge server version */
  version: string;

  /** Server uptime in seconds */
  uptime_seconds: number;

  /** Available LLM providers and their configuration */
  llm_providers: LLMProviderStatus;

  /** SHA-256 hash of the security config for integrity verification */
  security_config_hash?: string;

  /** Number of active sessions */
  sessions_active: number;

  /** Number of available FDA commands */
  commands_available: number;
}

/**
 * Status of available LLM providers.
 */
export interface LLMProviderStatus {
  ollama?: {
    available: boolean;
    endpoint?: string;
    models?: string[];
  };
  anthropic?: {
    available: boolean;
    api_key_set?: boolean;
  };
  openai?: {
    available: boolean;
    api_key_set?: boolean;
  };
}

// ============================================================
// Commands Endpoint
// ============================================================

/**
 * Information about a single FDA command.
 */
export interface CommandInfo {
  /** Command name (e.g., 'research', 'validate') */
  name: string;

  /** Human-readable description of the command */
  description: string;

  /** Argument hint showing expected parameters */
  args: string;

  /** Comma-separated list of allowed tools (Read, Write, Bash, etc.) */
  allowed_tools?: string;
}

/**
 * Response body from GET /commands endpoint.
 */
export interface CommandsResponse {
  /** List of available FDA commands */
  commands: CommandInfo[];

  /** Total number of commands */
  total: number;
}

// ============================================================
// Session Endpoints
// ============================================================

/**
 * Request body for POST /session endpoint.
 */
export interface SessionRequest {
  /** User identifier */
  user_id: string;

  /** Optional session ID to retrieve or create */
  session_id?: string;
}

/**
 * Response body from POST /session endpoint.
 */
export interface SessionResponse {
  /** Unique session identifier */
  session_id: string;

  /** User who owns the session */
  user_id: string;

  /** ISO 8601 timestamp of session creation */
  created_at: string;

  /** ISO 8601 timestamp of last access */
  last_accessed: string;

  /** Session context (conversation history, project info, etc.) */
  context: Record<string, unknown>;

  /** Whether this is a newly created session */
  is_new: boolean;
}

/**
 * Session detail response from GET /session/{session_id}.
 */
export interface SessionDetail {
  /** Unique session identifier */
  session_id: string;

  /** User who owns the session */
  user_id: string;

  /** ISO 8601 timestamp of session creation */
  created_at: string;

  /** ISO 8601 timestamp of last access */
  last_accessed: string;

  /** Session context data */
  context: Record<string, unknown>;

  /** Session metadata */
  metadata: Record<string, unknown>;
}

/**
 * Response from GET /sessions listing endpoint.
 */
export interface SessionListResponse {
  /** List of session summaries */
  sessions: SessionSummary[];

  /** Total number of sessions */
  total: number;
}

/**
 * Summary of a session for listing purposes.
 */
export interface SessionSummary {
  session_id: string;
  user_id: string;
  created_at: string;
  last_accessed: string;
}

// ============================================================
// Question/Answer Endpoints
// ============================================================

/**
 * A pending question queued by a command that needs user input.
 */
export interface PendingQuestion {
  /** Unique question identifier */
  id: string;

  /** Question text to display to the user */
  text: string;

  /** Session that generated the question */
  session_id: string;

  /** ISO 8601 timestamp when the question was created */
  created_at: string;
}

/**
 * Response from GET /session/{id}/questions.
 */
export interface PendingQuestionsResponse {
  /** List of pending questions */
  questions: PendingQuestion[];

  /** Number of pending questions */
  count: number;
}

/**
 * Request body for POST /session/{id}/answer.
 */
export interface AnswerSubmitRequest {
  /** ID of the question being answered */
  question_id: string;

  /** User's answer text */
  answer: string;
}

// ============================================================
// Tools Endpoint
// ============================================================

/**
 * Response from GET /tools endpoint.
 */
export interface ToolsResponse {
  /** List of available tool emulator names */
  tools: string[];

  /** Number of available tools */
  count: number;
}

// ============================================================
// Audit Endpoint
// ============================================================

/**
 * Response from GET /audit/integrity endpoint.
 */
export interface AuditIntegrityResponse {
  /** Whether the audit log integrity is valid */
  valid: boolean;

  /** Number of audit entries checked */
  entries_checked: number;

  /** Details about any integrity violations */
  violations?: string[];
}

// ============================================================
// Error Types
// ============================================================

/**
 * Error response from the bridge server.
 */
export interface BridgeError {
  /** HTTP status code */
  status: number;

  /** Error detail message */
  detail: string;
}

/**
 * Categorized error types for client-side handling.
 */
export type BridgeErrorType =
  | 'CONNECTION_REFUSED'    // Bridge server not running
  | 'TIMEOUT'               // Request timed out
  | 'AUTHENTICATION_REQUIRED' // Missing or invalid API key (HTTP 401)
  | 'SECURITY_VIOLATION'    // SecurityGateway blocked the request
  | 'RATE_LIMITED'          // Too many requests (HTTP 429)
  | 'COMMAND_NOT_FOUND'     // FDA command does not exist
  | 'SESSION_NOT_FOUND'     // Session ID not valid
  | 'INVALID_REQUEST'       // Malformed request body
  | 'SERVER_ERROR'          // Internal server error
  | 'UNKNOWN';              // Unclassified error

// ============================================================
// OpenClaw SDK Types (Ambient)
// ============================================================

/**
 * OpenClaw skill context provided to tool execute methods.
 *
 * NOTE: These types are provided by @openclaw/sdk at runtime.
 * They are defined here as ambient types for development purposes.
 */
export interface ToolContext {
  /** Authenticated user identifier */
  user_id: string;

  /** Current session identifier */
  session_id?: string;

  /** Messaging channel (whatsapp, telegram, slack, discord, etc.) */
  channel: string;

  /** Display a warning message to the user */
  warn(message: string): void;

  /** Update session metadata */
  updateSession(data: Record<string, unknown>): void;

  /** Send a progress update to the user */
  progress?(message: string, percent?: number): void;
}

/**
 * OpenClaw tool parameter definition.
 */
export interface ToolParameter {
  type: 'string' | 'number' | 'boolean';
  required?: boolean;
  description: string;
  default?: string | number | boolean;
  enum?: string[];
}

/**
 * OpenClaw tool definition interface.
 */
export interface Tool {
  name: string;
  description: string;
  parameters: Record<string, ToolParameter>;
  execute(params: Record<string, unknown>, context: ToolContext): Promise<string>;
}

/**
 * OpenClaw skill definition interface.
 */
export interface Skill {
  name: string;
  version: string;
  description: string;
  tools: Tool[];
  init?(): Promise<void>;
  cleanup?(): Promise<void>;
}
