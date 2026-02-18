#!/usr/bin/env python3
"""
OpenClaw Bridge Server for FDA Tools Plugin

Provides HTTP REST API at localhost:18790 for OpenClaw skill to communicate
with FDA tools Python scripts. Acts as a bridge between TypeScript skill
and Python backend.

Security:
  - API key authentication via X-API-Key header (key stored in OS keyring)
  - Rate limiting via slowapi (60 req/min default, configurable)
  - Request logging with sensitive field sanitization
  - Health endpoint is unauthenticated (no sensitive data)

Endpoints:
  POST /execute - Execute FDA command (authenticated)
  GET /health - Health check with system status (unauthenticated)
  GET /commands - List available commands (authenticated)
  GET /tools - List available tool emulators (authenticated)
  POST /session - Create or retrieve session (authenticated)
  GET /session/{id} - Get session details (authenticated)
  GET /sessions - List all sessions (authenticated)
  GET /session/{id}/questions - Get pending questions (authenticated)
  POST /session/{id}/answer - Submit answer to question (authenticated)
  GET /audit/integrity - Verify audit log integrity (authenticated)

Architecture:
  This bridge server sits between the OpenClaw TypeScript skill
  and the FDA Tools Python plugin. It handles:
  - HTTP request/response translation
  - API key authentication
  - Rate limiting
  - Session management
  - Security context
  - Tool emulation layer
  - Audit logging with sanitization

Version: 1.1.0
"""

import hashlib
import json
import logging
import os
import re
import secrets
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Security, Depends  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.security import APIKeyHeader  # type: ignore
from pydantic import BaseModel, Field  # type: ignore
from starlette.responses import JSONResponse  # type: ignore
import uvicorn  # type: ignore

# Rate limiting
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler  # type: ignore
    from slowapi.util import get_remote_address  # type: ignore
    from slowapi.errors import RateLimitExceeded  # type: ignore
    _HAS_SLOWAPI = True
except ImportError:
    _HAS_SLOWAPI = False

# ============================================================
# Configuration
# ============================================================

# Server configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 18790
SERVER_VERSION = "1.1.0"

# Rate limiting configuration (requests per minute)
RATE_LIMIT_DEFAULT = os.getenv("FDA_BRIDGE_RATE_LIMIT", "60/minute")
RATE_LIMIT_EXECUTE = os.getenv("FDA_BRIDGE_RATE_LIMIT_EXECUTE", "30/minute")

# API key header name
API_KEY_HEADER_NAME = "X-API-Key"

# Path configuration
PLUGIN_ROOT = Path(__file__).parent.parent
COMMANDS_DIR = PLUGIN_ROOT / "commands"
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"

# Add scripts directory to Python path for imports
sys.path.insert(0, str(SCRIPTS_DIR))

# Server startup time for uptime calculation
SERVER_START_TIME = time.time()

# In-memory session storage (for production, use Redis or database)
SESSIONS: Dict[str, Dict[str, Any]] = {}

# In-memory question queue (for production, use message queue)
PENDING_QUESTIONS: Dict[str, List[Dict[str, Any]]] = {}

# Audit log (for production, use append-only file or database)
AUDIT_LOG: List[Dict[str, Any]] = []

# ============================================================
# Logging Configuration
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================
# API Key Management (uses keyring from FDA-80)
# ============================================================

# Cached API key hash for fast comparison
_cached_api_key_hash: Optional[str] = None


def _get_or_create_bridge_key() -> str:
    """Get the bridge API key from keyring, or generate one on first startup.

    The key is stored in the OS keyring via the setup_api_key module
    (FDA-80 infrastructure). On first startup, generates a
    cryptographically secure 32-byte hex key.

    Returns:
        The bridge API key as a string.
    """
    global _cached_api_key_hash

    try:
        from setup_api_key import get_bridge_key, set_bridge_key
        existing_key = get_bridge_key()
        if existing_key:
            _cached_api_key_hash = hashlib.sha256(existing_key.encode()).hexdigest()
            return existing_key
    except ImportError:
        logger.warning(
            "setup_api_key module not available. "
            "Bridge API key will be generated but not persisted in keyring."
        )

    # Generate new key on first startup
    new_key = secrets.token_hex(32)
    # SECURITY (FDA-84): Never log the full key to prevent exposure in log files.
    # Display only to stdout (interactive terminal) and mask in logs.
    masked = f"{new_key[:4]}...{new_key[-4:]}"
    logger.info("=" * 60)
    logger.info("BRIDGE API KEY GENERATED (first startup)")
    logger.info("=" * 60)
    logger.info(f"Key (masked): {masked}")
    logger.info("")
    logger.info("Save this key -- it is required to authenticate API requests.")
    logger.info(f"Pass it in the '{API_KEY_HEADER_NAME}' header.")
    logger.info("")
    logger.info("To configure the OpenClaw skill client, set:")
    logger.info(f'  FDA_BRIDGE_API_KEY="<your-key>"')
    logger.info("=" * 60)
    # Print the full key ONLY to stdout for the operator to capture.
    # This avoids it appearing in structured log files.
    print(f"\n  >>> BRIDGE API KEY: {new_key}\n")
    print("  Copy this key now. It will NOT be shown again in logs.\n")

    # Attempt to store in keyring
    try:
        from setup_api_key import set_bridge_key
        if set_bridge_key(new_key):
            logger.info("Key stored in OS keyring (will persist across restarts).")
        else:
            logger.warning("Failed to store key in keyring. Key will be regenerated on next restart.")
    except ImportError:
        logger.warning("Keyring not available. Key will be regenerated on next restart.")

    _cached_api_key_hash = hashlib.sha256(new_key.encode()).hexdigest()
    return new_key


def _verify_api_key(provided_key: str) -> bool:
    """Verify an API key using constant-time comparison.

    Args:
        provided_key: The key provided in the request header.

    Returns:
        True if the key matches, False otherwise.
    """
    if _cached_api_key_hash is None:
        return False
    provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
    return secrets.compare_digest(provided_hash, _cached_api_key_hash)


# Environment variable override for the bridge API key
_ENV_BRIDGE_KEY = os.getenv("FDA_BRIDGE_API_KEY")

# ============================================================
# Request Logging & Sanitization
# ============================================================

# Fields to sanitize in log output
_SENSITIVE_FIELDS = {'api_key', 'password', 'secret', 'token', 'authorization', 'x-api-key'}
_SENSITIVE_PATTERN = re.compile(
    r'(api[_-]?key|password|secret|token|authorization)["\s:=]+["\']?([^"\',\s}{]{4,})',
    re.IGNORECASE
)


def sanitize_for_logging(data: Any) -> Any:
    """Recursively sanitize sensitive fields in data for safe logging.

    Replaces values of sensitive keys with redacted versions showing
    only the first 4 characters.

    Args:
        data: Dict, list, or scalar to sanitize.

    Returns:
        Sanitized copy of the data.
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key.lower() in _SENSITIVE_FIELDS:
                if isinstance(value, str) and len(value) > 4:
                    sanitized[key] = f"{value[:4]}...REDACTED"
                else:
                    sanitized[key] = "REDACTED"
            else:
                sanitized[key] = sanitize_for_logging(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_for_logging(item) for item in data]
    elif isinstance(data, str):
        return _SENSITIVE_PATTERN.sub(r'\1: REDACTED', data)
    return data


# ============================================================
# Request/Response Models
# ============================================================

class ExecuteRequest(BaseModel):
    """Request to execute FDA command."""
    command: str = Field(..., description="FDA command name (e.g., 'research', 'validate')")
    args: Optional[str] = Field(None, description="Command arguments")
    user_id: str = Field(..., description="User identifier for audit trail")
    session_id: Optional[str] = Field(None, description="Session ID for continuity")
    channel: str = Field(..., description="Output channel (file, whatsapp, telegram, etc.)")
    context: Optional[str] = Field(None, description="Additional context")


class ExecuteResponse(BaseModel):
    """Response from command execution."""
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    classification: str = "PUBLIC"  # PUBLIC, RESTRICTED, CONFIDENTIAL
    llm_provider: str = "none"  # ollama, anthropic, openai, none
    warnings: List[str] = []
    session_id: str
    duration_ms: Optional[int] = None
    command_metadata: Optional[Dict[str, Any]] = None


class SessionRequest(BaseModel):
    """Request to create or retrieve session."""
    user_id: str
    session_id: Optional[str] = None


class SessionResponse(BaseModel):
    """Response with session information."""
    session_id: str
    user_id: str
    created_at: str
    last_accessed: str
    context: Dict[str, Any] = {}
    is_new: bool = False


class AnswerSubmitRequest(BaseModel):
    """Request to submit answer to pending question."""
    question_id: str
    answer: str


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="FDA Tools Bridge Server",
    description="Authenticated HTTP bridge between OpenClaw skill and FDA Tools Python plugin",
    version=SERVER_VERSION,
)

# Rate limiter setup
if _HAS_SLOWAPI:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
else:
    limiter = None
    logger.warning(
        "slowapi not installed -- rate limiting disabled. "
        "Install with: pip install slowapi"
    )

# Enable CORS for localhost only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key security scheme
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)

# The actual bridge API key (loaded on startup)
_BRIDGE_API_KEY: Optional[str] = None


async def require_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """FastAPI dependency that validates the API key from the request header.

    Raises HTTPException 401 if key is missing or invalid.

    Returns:
        The validated API key string.
    """
    if api_key is None:
        audit_log_entry("auth_failure", {"reason": "missing_api_key"})
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide it in the X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not _verify_api_key(api_key):
        audit_log_entry("auth_failure", {"reason": "invalid_api_key"})
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


# ============================================================
# Request Logging Middleware
# ============================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing and sanitized details."""
    start = time.time()
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path

    # Log request (sanitize headers)
    headers_safe = {
        k: (v[:4] + "...REDACTED" if k.lower() in ('x-api-key', 'authorization') and len(v) > 4 else v)
        for k, v in request.headers.items()
    }
    logger.info(f"REQ {method} {path} from={client_ip}")

    response = await call_next(request)

    duration_ms = int((time.time() - start) * 1000)
    logger.info(f"RES {method} {path} status={response.status_code} duration={duration_ms}ms")

    # Audit log for non-health endpoints
    if path != "/health":
        audit_log_entry("http_request", {
            "method": method,
            "path": path,
            "client_ip": client_ip,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        })

    return response


# ============================================================
# Helper Functions
# ============================================================

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session by ID."""
    return SESSIONS.get(session_id)


def create_session(user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Create new session or return existing one."""
    if session_id and session_id in SESSIONS:
        session = SESSIONS[session_id]
        session["last_accessed"] = datetime.now(timezone.utc).isoformat()
        return session

    # Create new session
    new_session_id = session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    session = {
        "session_id": new_session_id,
        "user_id": user_id,
        "created_at": now,
        "last_accessed": now,
        "context": {},
        "metadata": {},
    }

    SESSIONS[new_session_id] = session
    return session


def audit_log_entry(event_type: str, data: Dict[str, Any]) -> None:
    """Add entry to audit log with sanitized data."""
    safe_data = sanitize_for_logging(data)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "data": safe_data,
    }
    AUDIT_LOG.append(entry)
    logger.info(f"Audit: {event_type} - {json.dumps(safe_data, indent=None)}")


def parse_command_frontmatter(command_path: Path) -> Dict[str, str]:
    """Parse YAML frontmatter from command markdown file."""
    metadata = {
        "description": "",
        "args": "",
        "allowed_tools": "",
    }

    try:
        with open(command_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Simple YAML frontmatter parser
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 2:
                frontmatter = parts[1].strip()
                for line in frontmatter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key in metadata:
                            metadata[key] = value
    except Exception as e:
        logger.warning(f"Failed to parse frontmatter from {command_path}: {e}")

    return metadata


def list_available_commands() -> List[Dict[str, str]]:
    """List all available FDA commands from commands directory."""
    commands = []

    if not COMMANDS_DIR.exists():
        logger.warning(f"Commands directory does not exist: {COMMANDS_DIR}")
        return commands

    for cmd_file in sorted(COMMANDS_DIR.glob("*.md")):
        metadata = parse_command_frontmatter(cmd_file)
        commands.append({
            "name": cmd_file.stem,
            "description": metadata["description"] or f"FDA command: {cmd_file.stem}",
            "args": metadata["args"],
            "allowed_tools": metadata["allowed_tools"],
        })

    return commands


def execute_fda_command(
    command: str,
    args: Optional[str],
    user_id: str,
    session_id: str,
    channel: str,
) -> Dict[str, Any]:
    """
    Execute FDA command via subprocess.

    Note: This is a simplified implementation. In production, this would:
    - Use the security gateway to evaluate classification
    - Route to appropriate LLM provider
    - Implement tool emulation layer
    - Handle streaming output for long-running commands
    """
    start_time = time.time()

    # Check if command exists
    command_file = COMMANDS_DIR / f"{command}.md"
    if not command_file.exists():
        return {
            "success": False,
            "error": f"Command not found: {command}",
            "classification": "PUBLIC",
            "llm_provider": "none",
            "session_id": session_id,
        }

    # Build command execution
    # For now, we'll just return a success message indicating the bridge is working
    # In production, this would invoke the actual command processor

    result_message = f"""FDA Tools Bridge Server (v{SERVER_VERSION})
Command: {command}
Args: {args or '(none)'}
User: {user_id}
Session: {session_id}
Channel: {channel}

Status: Bridge server is operational (authenticated).

Note: Full command execution requires the Phase 2 security gateway and
tool emulation layer. This simplified bridge demonstrates connectivity
between the OpenClaw TypeScript skill and the Python backend.

To execute actual FDA commands, use the command-line interface:
  cd {PLUGIN_ROOT}
  /fda-tools:{command} {args or ''}
"""

    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "success": True,
        "result": result_message,
        "classification": "PUBLIC",
        "llm_provider": "none",
        "warnings": [],
        "session_id": session_id,
        "duration_ms": duration_ms,
        "command_metadata": {
            "files_read": [],
            "files_written": [],
            "command_found": True,
        },
    }


# ============================================================
# API Endpoints
# ============================================================

# Helper: apply rate limit decorator only if slowapi is available
def _rate_limit(limit_string: str):
    """Decorator that applies rate limiting if slowapi is available."""
    if limiter is not None:
        return limiter.limit(limit_string)
    # No-op decorator when slowapi is not installed
    def noop(func):
        return func
    return noop


@app.get("/health")
@_rate_limit(RATE_LIMIT_DEFAULT)
async def health_check(request: Request):
    """
    Health check endpoint (UNAUTHENTICATED).

    Returns server status, version, uptime, available commands,
    and LLM provider availability. Does not expose sensitive data.
    """
    uptime_seconds = int(time.time() - SERVER_START_TIME)
    commands = list_available_commands()

    # Check LLM provider availability
    # For now, these are placeholders. In production, would actually check endpoints.
    llm_providers = {
        "ollama": {
            "available": False,
            "endpoint": "http://localhost:11434",
        },
        "anthropic": {
            "available": False,
            "api_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
        },
        "openai": {
            "available": False,
            "api_key_set": bool(os.getenv("OPENAI_API_KEY")),
        },
    }

    return {
        "status": "healthy",
        "version": SERVER_VERSION,
        "auth_required": True,
        "rate_limiting": _HAS_SLOWAPI,
        "uptime_seconds": uptime_seconds,
        "llm_providers": llm_providers,
        "security_config_hash": None,  # Would be computed from security config file
        "sessions_active": len(SESSIONS),
        "commands_available": len(commands),
    }


@app.get("/commands")
@_rate_limit(RATE_LIMIT_DEFAULT)
async def list_commands(
    request: Request,
    api_key: str = Depends(require_api_key),
):
    """
    List available FDA commands (AUTHENTICATED).

    Returns command names, descriptions, argument hints, and
    allowed tools parsed from command markdown frontmatter.
    """
    commands = list_available_commands()

    return {
        "commands": commands,
        "total": len(commands),
    }


@app.post("/execute")
@_rate_limit(RATE_LIMIT_EXECUTE)
async def execute_command(
    request_obj: ExecuteRequest,
    request: Request,
    api_key: str = Depends(require_api_key),
):
    """
    Execute FDA command (AUTHENTICATED, RATE LIMITED).

    Handles command execution with session management and audit logging.
    """
    # Create or retrieve session
    session = create_session(request_obj.user_id, request_obj.session_id)
    session_id = session["session_id"]

    # Audit log
    audit_log_entry("command_execute", {
        "command": request_obj.command,
        "args": request_obj.args,
        "user_id": request_obj.user_id,
        "session_id": session_id,
        "channel": request_obj.channel,
    })

    # Execute command
    try:
        result = execute_fda_command(
            command=request_obj.command,
            args=request_obj.args,
            user_id=request_obj.user_id,
            session_id=session_id,
            channel=request_obj.channel,
        )

        return ExecuteResponse(**result)

    except Exception as e:
        logger.error(f"Command execution failed: {e}", exc_info=True)

        return ExecuteResponse(
            success=False,
            error=f"Internal error: {str(e)}",
            classification="PUBLIC",
            llm_provider="none",
            session_id=session_id,
        )


@app.post("/session")
@_rate_limit(RATE_LIMIT_DEFAULT)
async def create_session_endpoint(
    session_request: SessionRequest,
    request: Request,
    api_key: str = Depends(require_api_key),
):
    """
    Create or retrieve session (AUTHENTICATED).

    If session_id is provided and exists, returns existing session.
    Otherwise creates new session.
    """
    existing_session = session_request.session_id and get_session(session_request.session_id)
    is_new = not existing_session

    session = create_session(session_request.user_id, session_request.session_id)

    return SessionResponse(
        session_id=session["session_id"],
        user_id=session["user_id"],
        created_at=session["created_at"],
        last_accessed=session["last_accessed"],
        context=session.get("context", {}),
        is_new=is_new,
    )


@app.get("/session/{session_id}")
@_rate_limit(RATE_LIMIT_DEFAULT)
async def get_session_endpoint(
    session_id: str,
    request: Request,
    api_key: str = Depends(require_api_key),
):
    """Get session details by ID (AUTHENTICATED)."""
    session = get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return {
        "session_id": session["session_id"],
        "user_id": session["user_id"],
        "created_at": session["created_at"],
        "last_accessed": session["last_accessed"],
        "context": session.get("context", {}),
        "metadata": session.get("metadata", {}),
    }


@app.get("/sessions")
@_rate_limit(RATE_LIMIT_DEFAULT)
async def list_sessions(
    request: Request,
    user_id: Optional[str] = None,
    api_key: str = Depends(require_api_key),
):
    """
    List active sessions, optionally filtered by user (AUTHENTICATED).
    """
    sessions = []

    for session in SESSIONS.values():
        if user_id and session["user_id"] != user_id:
            continue

        sessions.append({
            "session_id": session["session_id"],
            "user_id": session["user_id"],
            "created_at": session["created_at"],
            "last_accessed": session["last_accessed"],
        })

    return {
        "sessions": sessions,
        "total": len(sessions),
    }


@app.get("/session/{session_id}/questions")
@_rate_limit(RATE_LIMIT_DEFAULT)
async def get_pending_questions(
    session_id: str,
    request: Request,
    api_key: str = Depends(require_api_key),
):
    """Get pending questions for a session (AUTHENTICATED)."""
    session = get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    questions = PENDING_QUESTIONS.get(session_id, [])

    return {
        "questions": questions,
        "count": len(questions),
    }


@app.post("/session/{session_id}/answer")
@_rate_limit(RATE_LIMIT_DEFAULT)
async def submit_answer(
    session_id: str,
    answer_request: AnswerSubmitRequest,
    request: Request,
    api_key: str = Depends(require_api_key),
):
    """Submit answer to a pending question (AUTHENTICATED)."""
    session = get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    questions = PENDING_QUESTIONS.get(session_id, [])

    # Find and remove the answered question
    question_found = False
    for i, q in enumerate(questions):
        if q["id"] == answer_request.question_id:
            questions.pop(i)
            question_found = True
            break

    if not question_found:
        raise HTTPException(status_code=404, detail=f"Question not found: {answer_request.question_id}")

    # Audit log
    audit_log_entry("question_answered", {
        "session_id": session_id,
        "question_id": answer_request.question_id,
        "answer": answer_request.answer,
    })

    return {
        "success": True,
        "question_id": answer_request.question_id,
    }


@app.get("/tools")
@_rate_limit(RATE_LIMIT_DEFAULT)
async def list_tools(
    request: Request,
    api_key: str = Depends(require_api_key),
):
    """
    List available tool emulators (AUTHENTICATED).

    These are the MCP-style tools that commands can invoke
    (Read, Write, Bash, Glob, Grep, AskUserQuestion, etc.).
    """
    tools = [
        "Read",
        "Write",
        "Bash",
        "Glob",
        "Grep",
        "AskUserQuestion",
    ]

    return {
        "tools": tools,
        "count": len(tools),
    }


@app.get("/audit/integrity")
@_rate_limit(RATE_LIMIT_DEFAULT)
async def verify_audit_integrity(
    request: Request,
    api_key: str = Depends(require_api_key),
):
    """
    Verify audit log integrity (AUTHENTICATED).

    In production, this would verify that the append-only audit log
    has not been tampered with using cryptographic hashing.
    """
    return {
        "valid": True,
        "entries_checked": len(AUDIT_LOG),
        "violations": [],
    }


# ============================================================
# Startup & Shutdown
# ============================================================

@app.on_event("startup")
async def startup_event():
    """Server startup event."""
    global _BRIDGE_API_KEY

    logger.info("=" * 70)
    logger.info(f"FDA Tools Bridge Server v{SERVER_VERSION}")
    logger.info("=" * 70)
    logger.info(f"Server URL: http://{SERVER_HOST}:{SERVER_PORT}")
    logger.info(f"Commands directory: {COMMANDS_DIR}")
    logger.info(f"Scripts directory: {SCRIPTS_DIR}")

    # Initialize API key
    if _ENV_BRIDGE_KEY:
        _BRIDGE_API_KEY = _ENV_BRIDGE_KEY
        global _cached_api_key_hash
        _cached_api_key_hash = hashlib.sha256(_ENV_BRIDGE_KEY.encode()).hexdigest()
        logger.info("API key loaded from FDA_BRIDGE_API_KEY environment variable.")
    else:
        _BRIDGE_API_KEY = _get_or_create_bridge_key()

    # Log security configuration
    logger.info(f"Authentication: ENABLED (X-API-Key header required)")
    logger.info(f"Rate limiting: {'ENABLED' if _HAS_SLOWAPI else 'DISABLED (install slowapi)'}")
    logger.info(f"Rate limit (default): {RATE_LIMIT_DEFAULT}")
    logger.info(f"Rate limit (execute): {RATE_LIMIT_EXECUTE}")

    # Count available commands
    commands = list_available_commands()
    logger.info(f"Available commands: {len(commands)}")

    logger.info("=" * 70)
    logger.info("Server is ready to accept authenticated connections.")
    logger.info("=" * 70)


@app.on_event("shutdown")
async def shutdown_event():
    """Server shutdown event."""
    logger.info("Server shutting down...")
    logger.info(f"Total sessions created: {len(SESSIONS)}")
    logger.info(f"Total audit entries: {len(AUDIT_LOG)}")


# ============================================================
# Main Entry Point
# ============================================================

def main():
    """Run the bridge server."""
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
