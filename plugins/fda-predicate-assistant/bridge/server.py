"""
FDA Bridge Server - HTTP REST API Bridge for FDA Tools Plugin

FastAPI server that wraps Claude Code FDA plugin execution with:
1. Security enforcement (SecurityGateway from Phase 1)
2. Audit logging (AuditLogger from Phase 1)
3. Tool emulation (Read, Write, Bash, Glob, Grep, AskUserQuestion)
4. Session management (conversation context persistence)
5. User management and RBAC (Phase 4)
6. Multi-tenancy (Phase 4)
7. Electronic signatures - 21 CFR Part 11 (Phase 4)
8. Real-time monitoring and alerting (Phase 4)

Architecture:
  OpenClaw Skill (TypeScript) --> HTTP POST /execute --> FDA Bridge Server
  FDA Bridge Server --> SecurityGateway --> RBAC --> AuditLogger --> Tool Emulators
  Tool Emulators --> FDA Tools Plugin (subprocess)

Author: FDA Tools Development Team
Date: 2026-02-16
Version: 2.0.0 (Phase 4 Enterprise)
"""

import os
import re
import sys
import json
import uuid
import time
import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add parent directories to path for imports
BRIDGE_DIR = Path(__file__).parent.resolve()
PLUGIN_DIR = BRIDGE_DIR.parent.resolve()
LIB_DIR = PLUGIN_DIR / "lib"

sys.path.insert(0, str(LIB_DIR))
sys.path.insert(0, str(BRIDGE_DIR))

# Phase 1 imports
from security_gateway import (
    SecurityGateway,
    DataClassification,
    LLMProvider,
    SecurityDecision,
)
from audit_logger import AuditLogger

# Phase 2 imports
from session_manager import SessionManager, Session
from tool_emulators import ToolRegistry, ToolResult

# Phase 4 imports
from user_manager import UserManager, User
from rbac_manager import RBACManager, Permission, COMMAND_PERMISSIONS
from tenant_manager import TenantManager
from signature_manager import SignatureManager
from monitoring_manager import MonitoringManager, AlertType, AlertSeverity

# ============================================================
# Configuration
# ============================================================

BRIDGE_VERSION = "2.0.0"
BRIDGE_PORT = 18790
BRIDGE_HOST = "127.0.0.1"

# FDA commands directory
FDA_COMMANDS_DIR = PLUGIN_DIR.parent / "fda-tools" / "commands"
FDA_SCRIPTS_DIR = PLUGIN_DIR.parent / "fda-tools" / "scripts"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("fda-bridge")

# ============================================================
# Global state (initialized in lifespan)
# ============================================================

gateway: Optional[SecurityGateway] = None
audit_logger: Optional[AuditLogger] = None
session_mgr: Optional[SessionManager] = None
tool_registry: Optional[ToolRegistry] = None

# Phase 4 global state
user_mgr: Optional[UserManager] = None
rbac_mgr: Optional[RBACManager] = None
tenant_mgr: Optional[TenantManager] = None
signature_mgr: Optional[SignatureManager] = None
monitoring_mgr: Optional[MonitoringManager] = None


# ============================================================
# Pydantic Models
# ============================================================

class ExecuteRequest(BaseModel):
    """Request body for /execute endpoint."""
    command: str = Field(..., description="FDA command name (e.g., 'research', 'validate')")
    args: Optional[str] = Field(None, description="Command arguments (e.g., '--product-code DQY')")
    user_id: str = Field(..., description="User identifier")
    session_id: Optional[str] = Field(None, description="Session ID (creates new if not provided)")
    channel: str = Field("file", description="Output channel (whatsapp, telegram, slack, file, webhook)")
    context: Optional[str] = Field(None, description="Additional context for the command")


class ExecuteResponse(BaseModel):
    """Response body for /execute endpoint."""
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    classification: str
    llm_provider: str
    warnings: Optional[List[str]] = None
    session_id: str
    duration_ms: Optional[int] = None
    command_metadata: Optional[Dict[str, Any]] = None


class SessionRequest(BaseModel):
    """Request body for POST /session endpoint."""
    user_id: str = Field(..., description="User identifier")
    session_id: Optional[str] = Field(None, description="Optional session ID to retrieve/create")


class SessionResponse(BaseModel):
    """Response body for POST /session endpoint."""
    session_id: str
    user_id: str
    created_at: str
    last_accessed: str
    context: Dict[str, Any]
    is_new: bool


class HealthResponse(BaseModel):
    """Response body for GET /health endpoint."""
    status: str
    version: str
    uptime_seconds: float
    llm_providers: Dict[str, Any]
    security_config_hash: Optional[str] = None
    sessions_active: int
    commands_available: int


class CommandInfo(BaseModel):
    """Information about a single FDA command."""
    name: str
    description: str
    args: str
    allowed_tools: Optional[str] = None


class CommandsResponse(BaseModel):
    """Response body for GET /commands endpoint."""
    commands: List[CommandInfo]
    total: int


class QuestionSubmitRequest(BaseModel):
    """Request body for submitting answers to pending questions."""
    question_id: str
    answer: str


# ============================================================
# Phase 4 Pydantic Models
# ============================================================

class CreateUserRequest(BaseModel):
    """Request body for POST /users."""
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="Full name")
    role: str = Field(..., description="Role: admin, ra_professional, reviewer, readonly")
    organization_id: str = Field(..., description="Organization ID")
    messaging_handles: Optional[Dict[str, str]] = Field(None, description="Platform-to-handle mapping")


class UpdateUserRequest(BaseModel):
    """Request body for PUT /users/{user_id}."""
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    messaging_handles: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class EnrollmentRequest(BaseModel):
    """Request body for POST /users/enroll."""
    user_id: str = Field(..., description="User ID to generate token for")
    expires_hours: int = Field(24, description="Token validity in hours")


class CompleteEnrollmentRequest(BaseModel):
    """Request body for POST /users/complete-enrollment."""
    token: str = Field(..., description="Enrollment token")
    messaging_handles: Dict[str, str] = Field(..., description="Platform-to-handle mapping")


class CreateOrganizationRequest(BaseModel):
    """Request body for POST /organizations."""
    name: str = Field(..., description="Organization name")
    settings: Optional[Dict[str, Any]] = None


class UpdateOrganizationRequest(BaseModel):
    """Request body for PUT /organizations/{org_id}."""
    name: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class CheckPermissionRequest(BaseModel):
    """Request body for POST /users/{user_id}/check-permission."""
    permission: str = Field(..., description="Permission to check")
    command: Optional[str] = Field(None, description="Optional command context")


class CreateSignatureRequest(BaseModel):
    """Request body for POST /signatures."""
    user_id: str
    action: str
    document_id: str
    signature_method: str = Field("password", description="password, token, or biometric")
    credentials: str
    meaning: Optional[str] = None


class VerifySignatureRequest(BaseModel):
    """Request body for POST /signatures/verify."""
    signature_id: str
    credentials: str


class ResolveAlertRequest(BaseModel):
    """Request body for POST /alerts/{alert_id}/resolve."""
    resolved_by: Optional[str] = None


# ============================================================
# Lifespan (startup/shutdown)
# ============================================================

_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize and cleanup resources."""
    global gateway, audit_logger, session_mgr, tool_registry
    global user_mgr, rbac_mgr, tenant_mgr, signature_mgr, monitoring_mgr

    logger.info("FDA Bridge Server starting up...")

    # Initialize SecurityGateway
    try:
        config_path = os.path.expanduser("~/.claude/fda-tools.security.toml")
        gateway = SecurityGateway(config_path)
        logger.info("SecurityGateway initialized (config: %s)", config_path)
    except (FileNotFoundError, PermissionError, ValueError) as e:
        logger.warning(
            "SecurityGateway initialization failed: %s. "
            "Running in permissive mode (no security enforcement).",
            e
        )
        gateway = None

    # Initialize AuditLogger
    try:
        audit_log_path = os.path.expanduser("~/.claude/fda-tools.audit.jsonl")
        audit_logger = AuditLogger(audit_log_path)
        logger.info("AuditLogger initialized (log: %s)", audit_log_path)
    except Exception as e:
        logger.warning("AuditLogger initialization failed: %s", e)
        audit_logger = None

    # Initialize SessionManager
    sessions_dir = os.path.expanduser("~/.claude/sessions")
    session_mgr = SessionManager(sessions_dir=sessions_dir)
    logger.info("SessionManager initialized (dir: %s)", sessions_dir)

    # Initialize ToolRegistry
    tool_registry = ToolRegistry(
        working_dir=os.path.expanduser("~/fda-510k-data")
    )
    logger.info("ToolRegistry initialized with %d tools", len(tool_registry.list_tools()))

    # Initialize Phase 4: UserManager
    try:
        user_db_path = os.path.expanduser("~/.claude/fda-tools.users.json")
        user_mgr = UserManager(user_db_path)
        logger.info("UserManager initialized (db: %s, users: %d)", user_db_path, user_mgr.user_count)
    except Exception as e:
        logger.warning("UserManager initialization failed: %s", e)
        user_mgr = None

    # Initialize Phase 4: RBACManager
    try:
        rbac_audit_path = os.path.expanduser("~/.claude/fda-tools.rbac-audit.jsonl")
        rbac_mgr = RBACManager(rbac_audit_path)
        logger.info("RBACManager initialized")
    except Exception as e:
        logger.warning("RBACManager initialization failed: %s", e)
        rbac_mgr = None

    # Initialize Phase 4: TenantManager
    try:
        data_root = os.path.expanduser("~/fda-enterprise-data")
        tenant_mgr = TenantManager(data_root)
        logger.info("TenantManager initialized (root: %s, orgs: %d)", data_root, tenant_mgr.organization_count)
    except Exception as e:
        logger.warning("TenantManager initialization failed: %s", e)
        tenant_mgr = None

    # Initialize Phase 4: SignatureManager
    try:
        sig_path = os.path.expanduser("~/.claude/fda-tools-signatures")
        signature_mgr = SignatureManager(sig_path)
        logger.info("SignatureManager initialized (dir: %s)", sig_path)
    except Exception as e:
        logger.warning("SignatureManager initialization failed: %s", e)
        signature_mgr = None

    # Initialize Phase 4: MonitoringManager
    try:
        monitoring_mgr = MonitoringManager()
        logger.info("MonitoringManager initialized")
    except Exception as e:
        logger.warning("MonitoringManager initialization failed: %s", e)
        monitoring_mgr = None

    # Log startup
    if audit_logger:
        audit_logger.log_event(
            event_type="server_start",
            user_id="system",
            session_id="system",
            command="bridge_server",
            classification="PUBLIC",
            llm_provider="none",
            channel="system",
            allowed=True,
            args="version={}, port={}".format(BRIDGE_VERSION, BRIDGE_PORT)
        )

    logger.info(
        "FDA Bridge Server ready on %s:%d (version %s)",
        BRIDGE_HOST, BRIDGE_PORT, BRIDGE_VERSION
    )

    yield

    # Shutdown
    logger.info("FDA Bridge Server shutting down...")

    # Cleanup expired sessions
    if session_mgr:
        cleaned = session_mgr.cleanup_expired()
        logger.info("Cleaned up %d expired sessions", cleaned)

    if audit_logger:
        audit_logger.log_event(
            event_type="server_stop",
            user_id="system",
            session_id="system",
            command="bridge_server",
            classification="PUBLIC",
            llm_provider="none",
            channel="system",
            allowed=True
        )

    logger.info("FDA Bridge Server stopped.")


# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="FDA Bridge Server",
    description=(
        "HTTP REST API Bridge for FDA Tools Claude Code Plugin. "
        "Provides secure command execution with audit logging, "
        "session management, and tool emulation."
    ),
    version=BRIDGE_VERSION,
    lifespan=lifespan,
)

# CORS middleware (localhost only for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ============================================================
# Middleware: Request logging
# ============================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    logger.info(
        "%s %s %d (%.0fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration
    )
    return response


# ============================================================
# Endpoints
# ============================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns server status, available LLM providers,
    security config hash, active sessions, and command count.
    """
    uptime = time.time() - _start_time

    # Detect LLM providers
    llm_info = {
        'ollama': {'available': False, 'models': []},
        'anthropic': {'available': False},
        'openai': {'available': False}
    }

    if gateway:
        try:
            available = gateway.detect_llm_providers()
            if LLMProvider.OLLAMA in available:
                llm_info['ollama']['available'] = True
                llm_info['ollama']['models'] = gateway.policy.ollama_models
            if LLMProvider.ANTHROPIC in available:
                llm_info['anthropic']['available'] = True
            if LLMProvider.OPENAI in available:
                llm_info['openai']['available'] = True
        except Exception:
            pass
    else:
        # No security gateway -- check directly
        if os.environ.get('ANTHROPIC_API_KEY'):
            llm_info['anthropic']['available'] = True
        if os.environ.get('OPENAI_API_KEY'):
            llm_info['openai']['available'] = True

    # Security config hash
    config_hash = None
    if gateway:
        try:
            config_hash = gateway.get_config_hash()
        except Exception:
            pass

    # Active sessions
    active_sessions = session_mgr.cache_size if session_mgr else 0

    # Available commands
    commands_count = len(_discover_commands())

    return HealthResponse(
        status="healthy",
        version=BRIDGE_VERSION,
        uptime_seconds=round(uptime, 2),
        llm_providers=llm_info,
        security_config_hash=config_hash,
        sessions_active=active_sessions,
        commands_available=commands_count
    )


@app.get("/commands", response_model=CommandsResponse)
async def list_commands():
    """
    List all available FDA commands with descriptions.

    Parses YAML frontmatter from command markdown files.
    """
    commands = _discover_commands()
    return CommandsResponse(
        commands=commands,
        total=len(commands)
    )


@app.post("/session", response_model=SessionResponse)
async def manage_session(request: SessionRequest):
    """
    Create or retrieve a session.

    If session_id is provided and exists, returns existing session.
    Otherwise creates a new session.
    """
    if not session_mgr:
        raise HTTPException(
            status_code=503,
            detail="Session manager not available"
        )

    is_new = False

    if request.session_id:
        session = session_mgr.get_session(request.session_id)
        if session is None:
            session = session_mgr.create_session(
                user_id=request.user_id,
                session_id=request.session_id
            )
            is_new = True
    else:
        session = session_mgr.create_session(user_id=request.user_id)
        is_new = True

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        created_at=session.created_at,
        last_accessed=session.last_accessed,
        context=session.context,
        is_new=is_new
    )


@app.post("/execute", response_model=ExecuteResponse)
async def execute_command(request: ExecuteRequest):
    """
    Execute an FDA command with security enforcement.

    Flow:
    1. Get/create session
    2. SecurityGateway evaluation (classify, route LLM, validate channel)
    3. AuditLogger event
    4. If blocked, return error
    5. Execute command (subprocess or tool emulators)
    6. Return result with metadata
    """
    start_time = time.time()

    # Step 1: Session management
    if not session_mgr:
        raise HTTPException(
            status_code=503,
            detail="Session manager not available"
        )

    session = session_mgr.get_or_create_session(
        user_id=request.user_id,
        session_id=request.session_id
    )
    session_id = session.session_id

    # Extract file paths from command arguments
    file_paths = _extract_file_paths(request.args or "")

    # Step 2: Security evaluation
    if gateway:
        try:
            decision = gateway.evaluate(
                command=request.command,
                file_paths=file_paths,
                channel=request.channel,
                user_id=request.user_id,
                session_id=session_id
            )
        except Exception as e:
            logger.error("Security evaluation failed: %s", e)
            decision = SecurityDecision(
                allowed=True,
                classification=DataClassification.RESTRICTED,
                llm_provider=LLMProvider.NONE,
                channel_allowed=True,
                warnings=["Security evaluation error (permissive fallback): {}".format(e)],
                errors=[],
                audit_metadata={
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'user_id': request.user_id,
                    'session_id': session_id,
                    'command': request.command,
                    'classification': 'RESTRICTED',
                    'llm_provider': 'none',
                    'channel': request.channel,
                    'allowed': True,
                    'file_paths': file_paths,
                    'warnings_count': 1,
                    'errors_count': 0
                }
            )
    else:
        # No security gateway -- permissive mode
        decision = SecurityDecision(
            allowed=True,
            classification=DataClassification.PUBLIC,
            llm_provider=LLMProvider.NONE,
            channel_allowed=True,
            warnings=["Security gateway not configured -- running in permissive mode"],
            errors=[],
            audit_metadata={
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_id': request.user_id,
                'session_id': session_id,
                'command': request.command,
                'classification': 'PUBLIC',
                'llm_provider': 'none',
                'channel': request.channel,
                'allowed': True,
                'file_paths': file_paths,
                'warnings_count': 1,
                'errors_count': 0
            }
        )

    classification = decision.classification.value
    llm_provider = decision.llm_provider.value
    warnings = decision.warnings or []

    # Step 3: Audit logging
    if audit_logger:
        try:
            audit_logger.log_event(
                event_type="execute" if decision.allowed else "security_violation",
                user_id=request.user_id,
                session_id=session_id,
                command=request.command,
                classification=classification,
                llm_provider=llm_provider,
                channel=request.channel,
                allowed=decision.allowed,
                args=request.args,
                violations=decision.errors if not decision.allowed else None,
                warnings=warnings
            )
        except Exception as e:
            logger.error("Audit logging failed: %s", e)

    # Step 4: Block if not allowed
    if not decision.allowed:
        duration_ms = int((time.time() - start_time) * 1000)

        # Record in session
        session_mgr.add_to_conversation(
            session_id=session_id,
            role="system",
            content="BLOCKED: {}".format('; '.join(decision.errors)),
            command=request.command
        )

        return ExecuteResponse(
            success=False,
            error="\n".join(decision.errors),
            classification=classification,
            llm_provider=llm_provider,
            warnings=warnings,
            session_id=session_id,
            duration_ms=duration_ms
        )

    # Step 5: Execute command
    try:
        result = await _execute_fda_command(
            command=request.command,
            args=request.args,
            context=request.context,
            llm_provider=decision.llm_provider,
            session=session,
            file_paths=file_paths
        )
    except Exception as e:
        logger.error("Command execution failed: %s", e)
        result = {
            'success': False,
            'output': None,
            'error': str(e),
            'files_read': [],
            'files_written': []
        }

    duration_ms = int((time.time() - start_time) * 1000)

    # Step 6: Update audit with execution result
    if audit_logger:
        try:
            audit_logger.log_event(
                event_type="execute_complete",
                user_id=request.user_id,
                session_id=session_id,
                command=request.command,
                classification=classification,
                llm_provider=llm_provider,
                channel=request.channel,
                allowed=True,
                args=request.args,
                success=result.get('success', False),
                duration_ms=duration_ms,
                files_read=result.get('files_read', []),
                files_written=result.get('files_written', [])
            )
        except Exception as e:
            logger.error("Audit logging (completion) failed: %s", e)

    # Record in session
    session_mgr.add_to_conversation(
        session_id=session_id,
        role="user",
        content="/{} {}".format(request.command, request.args or '').strip(),
        command=request.command
    )

    if result.get('success'):
        output_preview = (result.get('output') or '')[:500]
        session_mgr.add_to_conversation(
            session_id=session_id,
            role="assistant",
            content=output_preview,
            command=request.command
        )

    # Track file paths
    for fp in result.get('files_read', []):
        session_mgr.add_file_path(session_id, fp)
    for fp in result.get('files_written', []):
        session_mgr.add_file_path(session_id, fp)

    return ExecuteResponse(
        success=result.get('success', False),
        result=result.get('output'),
        error=result.get('error'),
        classification=classification,
        llm_provider=llm_provider,
        warnings=warnings if warnings else None,
        session_id=session_id,
        duration_ms=duration_ms,
        command_metadata={
            'files_read': result.get('files_read', []),
            'files_written': result.get('files_written', []),
            'command_found': result.get('command_found', True)
        }
    )


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Retrieve session details by ID."""
    if not session_mgr:
        raise HTTPException(status_code=503, detail="Session manager not available")

    session = session_mgr.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found: {}".format(session_id))

    return {
        'session_id': session.session_id,
        'user_id': session.user_id,
        'created_at': session.created_at,
        'last_accessed': session.last_accessed,
        'context': session.context,
        'metadata': session.metadata
    }


@app.get("/session/{session_id}/questions")
async def get_pending_questions(session_id: str):
    """Get pending questions for a session."""
    if not tool_registry:
        raise HTTPException(status_code=503, detail="Tool registry not available")

    questions = tool_registry.ask_user.get_pending_questions(session_id)
    return {'questions': questions, 'count': len(questions)}


@app.post("/session/{session_id}/answer")
async def submit_answer(session_id: str, request: QuestionSubmitRequest):
    """Submit an answer to a pending question."""
    if not tool_registry:
        raise HTTPException(status_code=503, detail="Tool registry not available")

    success = tool_registry.ask_user.submit_answer(
        question_id=request.question_id,
        answer=request.answer
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Question not found: {}".format(request.question_id)
        )

    return {'success': True, 'question_id': request.question_id}


@app.get("/sessions")
async def list_sessions(user_id: Optional[str] = None):
    """List active sessions, optionally filtered by user."""
    if not session_mgr:
        raise HTTPException(status_code=503, detail="Session manager not available")

    sessions = session_mgr.list_sessions(user_id=user_id)
    return {'sessions': sessions, 'total': len(sessions)}


@app.get("/audit/integrity")
async def audit_integrity():
    """Verify audit log integrity."""
    if not audit_logger:
        raise HTTPException(status_code=503, detail="Audit logger not available")

    results = audit_logger.verify_integrity()
    return results


@app.get("/tools")
async def list_tools():
    """List available tool emulators."""
    if not tool_registry:
        raise HTTPException(status_code=503, detail="Tool registry not available")

    return {
        'tools': tool_registry.list_tools(),
        'count': len(tool_registry.list_tools())
    }


# ============================================================
# Phase 4 Endpoints: User Management
# ============================================================

@app.post("/users")
async def create_user(request: CreateUserRequest):
    """Create a new user (admin only in production)."""
    if not user_mgr:
        raise HTTPException(status_code=503, detail="User manager not available")

    try:
        user = user_mgr.create_user(
            email=request.email,
            name=request.name,
            role=request.role,
            organization_id=request.organization_id,
            messaging_handles=request.messaging_handles
        )
        return user.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/users")
async def list_users_endpoint(organization_id: Optional[str] = None):
    """List users, optionally filtered by organization."""
    if not user_mgr:
        raise HTTPException(status_code=503, detail="User manager not available")

    users = user_mgr.list_users(organization_id=organization_id)
    return {
        'users': [u.to_dict() for u in users],
        'total': len(users)
    }


@app.get("/users/{user_id}")
async def get_user_endpoint(user_id: str):
    """Get user details."""
    if not user_mgr:
        raise HTTPException(status_code=503, detail="User manager not available")

    user = user_mgr.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found: {}".format(user_id))

    return user.to_dict()


@app.put("/users/{user_id}")
async def update_user_endpoint(user_id: str, request: UpdateUserRequest):
    """Update user attributes."""
    if not user_mgr:
        raise HTTPException(status_code=503, detail="User manager not available")

    updates = {}
    if request.name is not None:
        updates['name'] = request.name
    if request.role is not None:
        updates['role'] = request.role
    if request.is_active is not None:
        updates['is_active'] = request.is_active
    if request.messaging_handles is not None:
        updates['messaging_handles'] = request.messaging_handles
    if request.metadata is not None:
        updates['metadata'] = request.metadata

    try:
        user = user_mgr.update_user(user_id, updates)
        if rbac_mgr:
            rbac_mgr.invalidate_cache(user_id)
        return user.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/users/{user_id}")
async def delete_user_endpoint(user_id: str):
    """Delete a user account."""
    if not user_mgr:
        raise HTTPException(status_code=503, detail="User manager not available")

    success = user_mgr.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found: {}".format(user_id))

    if rbac_mgr:
        rbac_mgr.invalidate_cache(user_id)

    return {'success': True, 'deleted': user_id}


@app.post("/users/enroll")
async def generate_enrollment(request: EnrollmentRequest):
    """Generate an enrollment token for a user."""
    if not user_mgr:
        raise HTTPException(status_code=503, detail="User manager not available")

    try:
        token = user_mgr.generate_enrollment_token(
            user_id=request.user_id,
            expires_hours=request.expires_hours
        )
        return {
            'token': token,
            'user_id': request.user_id,
            'expires_hours': request.expires_hours
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/users/complete-enrollment")
async def complete_enrollment(request: CompleteEnrollmentRequest):
    """Complete enrollment with token and messaging handles."""
    if not user_mgr:
        raise HTTPException(status_code=503, detail="User manager not available")

    try:
        user = user_mgr.complete_enrollment(
            token=request.token,
            messaging_handles=request.messaging_handles
        )
        return user.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# Phase 4 Endpoints: RBAC
# ============================================================

@app.get("/users/{user_id}/permissions")
async def get_user_permissions(user_id: str):
    """Get all permissions for a user."""
    if not user_mgr or not rbac_mgr:
        raise HTTPException(status_code=503, detail="User/RBAC manager not available")

    user = user_mgr.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found: {}".format(user_id))

    permissions = rbac_mgr.get_user_permissions(user)
    allowed_commands = rbac_mgr.get_allowed_commands(user)

    return {
        'user_id': user_id,
        'role': user.role,
        'permissions': [p.value for p in permissions],
        'allowed_commands': allowed_commands
    }


@app.post("/users/{user_id}/check-permission")
async def check_user_permission(user_id: str, request: CheckPermissionRequest):
    """Check if a user has a specific permission."""
    if not user_mgr or not rbac_mgr:
        raise HTTPException(status_code=503, detail="User/RBAC manager not available")

    user = user_mgr.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found: {}".format(user_id))

    try:
        permission = Permission(request.permission)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid permission: {}".format(request.permission)
        )

    allowed = rbac_mgr.check_permission(user, permission)

    return {
        'user_id': user_id,
        'permission': request.permission,
        'allowed': allowed,
        'role': user.role
    }


# ============================================================
# Phase 4 Endpoints: Organizations
# ============================================================

@app.post("/organizations")
async def create_organization(request: CreateOrganizationRequest):
    """Create a new organization."""
    if not tenant_mgr:
        raise HTTPException(status_code=503, detail="Tenant manager not available")

    try:
        org = tenant_mgr.create_organization(
            name=request.name,
            settings=request.settings
        )
        return org.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/organizations")
async def list_organizations():
    """List all organizations."""
    if not tenant_mgr:
        raise HTTPException(status_code=503, detail="Tenant manager not available")

    orgs = tenant_mgr.list_organizations()
    return {
        'organizations': [o.to_dict() for o in orgs],
        'total': len(orgs)
    }


@app.get("/organizations/{org_id}")
async def get_organization(org_id: str):
    """Get organization details."""
    if not tenant_mgr:
        raise HTTPException(status_code=503, detail="Tenant manager not available")

    org = tenant_mgr.get_organization(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found: {}".format(org_id))

    return org.to_dict()


@app.put("/organizations/{org_id}")
async def update_organization(org_id: str, request: UpdateOrganizationRequest):
    """Update organization attributes."""
    if not tenant_mgr:
        raise HTTPException(status_code=503, detail="Tenant manager not available")

    updates = {}
    if request.name is not None:
        updates['name'] = request.name
    if request.is_active is not None:
        updates['is_active'] = request.is_active
    if request.settings is not None:
        updates['settings'] = request.settings

    try:
        org = tenant_mgr.update_organization(org_id, updates)
        return org.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# Phase 4 Endpoints: Electronic Signatures
# ============================================================

@app.post("/signatures")
async def create_signature(request: CreateSignatureRequest):
    """Create an electronic signature (21 CFR Part 11)."""
    if not signature_mgr:
        raise HTTPException(status_code=503, detail="Signature manager not available")

    # Get user details for signature
    user_name = request.user_id
    user_email = ""
    if user_mgr:
        user = user_mgr.get_user(request.user_id)
        if user:
            user_name = user.name
            user_email = user.email

    try:
        sig = signature_mgr.create_signature(
            user_id=request.user_id,
            user_name=user_name,
            user_email=user_email,
            action=request.action,
            document_id=request.document_id,
            signature_method=request.signature_method,
            credentials=request.credentials,
            meaning=request.meaning or ""
        )

        # Return signature info without hash/salt
        result = sig.to_dict()
        result.pop('signature_hash', None)
        result.pop('salt', None)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/signatures/verify")
async def verify_signature(request: VerifySignatureRequest):
    """Verify an electronic signature."""
    if not signature_mgr:
        raise HTTPException(status_code=503, detail="Signature manager not available")

    valid = signature_mgr.verify_signature(
        signature_id=request.signature_id,
        credentials=request.credentials
    )

    return {
        'signature_id': request.signature_id,
        'valid': valid
    }


@app.get("/documents/{doc_id}/signatures")
async def get_document_signatures(doc_id: str):
    """Get all signatures for a document."""
    if not signature_mgr:
        raise HTTPException(status_code=503, detail="Signature manager not available")

    signatures = signature_mgr.get_signatures_for_document(doc_id)
    results = []
    for sig in signatures:
        d = sig.to_dict()
        d.pop('signature_hash', None)
        d.pop('salt', None)
        results.append(d)

    return {
        'document_id': doc_id,
        'signatures': results,
        'total': len(results)
    }


# ============================================================
# Phase 4 Endpoints: Monitoring
# ============================================================

@app.get("/alerts")
async def get_alerts(
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 100
):
    """Get recent alerts with optional filters."""
    if not monitoring_mgr:
        raise HTTPException(status_code=503, detail="Monitoring manager not available")

    alerts = monitoring_mgr.get_alerts(
        severity=severity,
        alert_type=alert_type,
        resolved=resolved,
        limit=limit
    )

    return {
        'alerts': [a.to_dict() for a in alerts],
        'total': len(alerts)
    }


@app.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, request: ResolveAlertRequest):
    """Resolve an alert."""
    if not monitoring_mgr:
        raise HTTPException(status_code=503, detail="Monitoring manager not available")

    alert = monitoring_mgr.resolve_alert(
        alert_id=alert_id,
        resolved_by=request.resolved_by
    )

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found: {}".format(alert_id))

    return alert.to_dict()


@app.get("/metrics")
async def get_metrics(
    metric_name: str = "command_execution",
    limit: int = 100
):
    """Get performance metrics."""
    if not monitoring_mgr:
        raise HTTPException(status_code=503, detail="Monitoring manager not available")

    metrics = monitoring_mgr.get_metrics(
        metric_name=metric_name,
        limit=limit
    )

    return {
        'metric_name': metric_name,
        'metrics': metrics,
        'total': len(metrics)
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with all subsystems.

    Returns comprehensive health status including:
    - LLM providers
    - Phase 4 managers (users, RBAC, tenants, signatures, monitoring)
    - Active alerts
    - Performance metrics
    """
    uptime = time.time() - _start_time

    # Base health from monitoring
    health = {}
    if monitoring_mgr:
        health = monitoring_mgr.get_system_health()
    else:
        health = {'overall_status': 'unknown'}

    # Add subsystem status
    health['subsystems'] = {
        'security_gateway': gateway is not None,
        'audit_logger': audit_logger is not None,
        'session_manager': session_mgr is not None,
        'tool_registry': tool_registry is not None,
        'user_manager': user_mgr is not None,
        'rbac_manager': rbac_mgr is not None,
        'tenant_manager': tenant_mgr is not None,
        'signature_manager': signature_mgr is not None,
        'monitoring_manager': monitoring_mgr is not None,
    }

    health['version'] = BRIDGE_VERSION
    health['uptime_seconds'] = round(uptime, 2)

    # Add counts
    health['counts'] = {
        'users': user_mgr.user_count if user_mgr else 0,
        'active_users': user_mgr.active_user_count if user_mgr else 0,
        'organizations': tenant_mgr.organization_count if tenant_mgr else 0,
        'signatures': signature_mgr.signature_count if signature_mgr else 0,
        'active_alerts': monitoring_mgr.active_alert_count if monitoring_mgr else 0,
        'sessions_active': session_mgr.cache_size if session_mgr else 0,
    }

    return health


# ============================================================
# Helper Functions
# ============================================================

def _discover_commands() -> List[CommandInfo]:
    """
    Discover FDA commands from markdown files.

    Parses YAML frontmatter from commands/*.md files.
    """
    commands = []

    if not FDA_COMMANDS_DIR.exists():
        logger.warning("Commands directory not found: %s", FDA_COMMANDS_DIR)
        return commands

    for cmd_file in sorted(FDA_COMMANDS_DIR.glob("*.md")):
        try:
            with open(cmd_file, 'r') as f:
                content = f.read()

            # Parse YAML frontmatter
            frontmatter = _parse_frontmatter(content)
            if frontmatter:
                commands.append(CommandInfo(
                    name=cmd_file.stem,
                    description=frontmatter.get('description', '(no description)'),
                    args=frontmatter.get('argument-hint', ''),
                    allowed_tools=frontmatter.get('allowed-tools', '')
                ))
        except Exception as e:
            logger.warning("Error parsing command %s: %s", cmd_file.name, e)

    return commands


def _parse_frontmatter(content: str) -> Optional[Dict[str, str]]:
    """
    Parse YAML frontmatter from markdown content.

    Expects format:
    ---
    key: value
    ---
    """
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None

    frontmatter = {}
    for line in match.group(1).strip().split('\n'):
        # Simple key: value parsing (handles quoted values)
        kv_match = re.match(r'^(\S+?):\s*(.+)$', line.strip())
        if kv_match:
            key = kv_match.group(1)
            value = kv_match.group(2).strip()
            # Remove surrounding quotes
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            frontmatter[key] = value

    return frontmatter


def _extract_file_paths(args: str) -> List[str]:
    """
    Extract file paths from command arguments.

    Looks for patterns like:
    - Absolute paths: /home/user/file.json
    - Home-relative paths: ~/data/file.json
    - --project NAME patterns
    """
    paths = []

    # Absolute paths
    for match in re.finditer(r'(/[\w/\-._]+\.\w+)', args):
        paths.append(match.group(1))

    # Home-relative paths
    for match in re.finditer(r'(~/[\w/\-._]+)', args):
        paths.append(os.path.expanduser(match.group(1)))

    # --project NAME -> project directory
    project_match = re.search(r'--project\s+(\S+)', args)
    if project_match:
        project_name = project_match.group(1)
        project_dir = os.path.expanduser(
            "~/fda-510k-data/projects/{}".format(project_name)
        )
        paths.append(project_dir)

    return paths


async def _execute_fda_command(
    command: str,
    args: Optional[str],
    context: Optional[str],
    llm_provider: LLMProvider,
    session: Session,
    file_paths: List[str]
) -> Dict[str, Any]:
    """
    Execute an FDA command.

    Strategy:
    1. Check if command has a corresponding Python script
    2. If so, execute via subprocess (using asyncio.create_subprocess_exec
       with explicit argument lists to avoid shell injection)
    3. Otherwise, read command markdown and gather data with tool emulators
    4. Return gathered data as the result

    Args:
        command: FDA command name
        args: Command arguments
        context: Additional context
        llm_provider: Selected LLM provider
        session: User session
        file_paths: Extracted file paths

    Returns:
        Dict with success, output, error, files_read, files_written
    """
    files_read = []
    files_written = []

    # Check for matching Python script
    script_name = command.replace('-', '_') + ".py"
    script_path = FDA_SCRIPTS_DIR / script_name
    if script_path.exists():
        return await _execute_python_script(
            script_path=str(script_path),
            args=args,
            context=context
        )

    # Check for command markdown file
    command_file = FDA_COMMANDS_DIR / "{}.md".format(command)
    if not command_file.exists():
        return {
            'success': False,
            'output': None,
            'error': "Command not found: {}. Use GET /commands to list available commands.".format(command),
            'files_read': [],
            'files_written': [],
            'command_found': False
        }

    # Read command definition
    try:
        with open(command_file, 'r') as f:
            command_content = f.read()
        files_read.append(str(command_file))
    except Exception as e:
        return {
            'success': False,
            'output': None,
            'error': "Cannot read command file: {}".format(e),
            'files_read': [],
            'files_written': [],
            'command_found': True
        }

    # Parse frontmatter for allowed tools
    frontmatter = _parse_frontmatter(command_content)
    allowed_tools_str = frontmatter.get('allowed-tools', '') if frontmatter else ''
    description = frontmatter.get('description', command) if frontmatter else command

    # Execute command using tool emulators
    result = await _execute_with_tools(
        command=command,
        args=args,
        context=context,
        command_content=command_content,
        allowed_tools=allowed_tools_str,
        description=description,
        session=session,
        file_paths=file_paths
    )

    result['files_read'] = files_read + result.get('files_read', [])
    result['files_written'] = files_written + result.get('files_written', [])
    result['command_found'] = True

    return result


async def _execute_python_script(
    script_path: str,
    args: Optional[str],
    context: Optional[str]
) -> Dict[str, Any]:
    """
    Execute a Python script as a subprocess using asyncio.create_subprocess_exec.

    Uses explicit argument lists (not shell=True) to prevent injection.

    Args:
        script_path: Path to Python script
        args: Command arguments
        context: Additional context

    Returns:
        Dict with execution results
    """
    cmd_parts = ["python3", script_path]
    if args:
        # Split args safely
        import shlex
        try:
            cmd_parts.extend(shlex.split(args))
        except ValueError:
            cmd_parts.extend(args.split())

    env = os.environ.copy()
    env['FDA_BRIDGE_CONTEXT'] = context or ''
    env['FDA_BRIDGE_MODE'] = 'true'

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.expanduser("~/fda-510k-data"),
            env=env
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=120
        )

        output = stdout.decode('utf-8', errors='replace')
        error_output = stderr.decode('utf-8', errors='replace')

        return {
            'success': process.returncode == 0,
            'output': output or error_output or "(no output)",
            'error': error_output if process.returncode != 0 else None,
            'files_read': [script_path],
            'files_written': []
        }

    except asyncio.TimeoutError:
        return {
            'success': False,
            'output': None,
            'error': "Script execution timed out (120s): {}".format(script_path),
            'files_read': [script_path],
            'files_written': []
        }
    except Exception as e:
        return {
            'success': False,
            'output': None,
            'error': "Script execution failed: {}".format(e),
            'files_read': [script_path],
            'files_written': []
        }


async def _execute_with_tools(
    command: str,
    args: Optional[str],
    context: Optional[str],
    command_content: str,
    allowed_tools: str,
    description: str,
    session: Session,
    file_paths: List[str]
) -> Dict[str, Any]:
    """
    Execute an FDA command using tool emulators.

    This function:
    1. Determines what data the command needs
    2. Uses tool emulators to gather that data
    3. Returns the gathered data as the result

    For commands that primarily need file reading (validate, research, etc.),
    we read relevant project files and return them.

    Args:
        command: FDA command name
        args: Command arguments
        context: Additional context
        command_content: Command markdown content
        allowed_tools: Comma-separated list of allowed tools
        description: Command description
        session: User session
        file_paths: Extracted file paths

    Returns:
        Dict with execution results
    """
    if not tool_registry:
        return {
            'success': False,
            'output': None,
            'error': 'Tool registry not available',
            'files_read': [],
            'files_written': []
        }

    all_files_read = []
    all_files_written = []
    output_parts = []

    # Add command info header
    output_parts.append("=== FDA Command: {} ===".format(command))
    output_parts.append("Description: {}".format(description))
    output_parts.append("Arguments: {}".format(args or '(none)'))
    output_parts.append("")

    # Extract project name from args
    project_name = None
    if args:
        project_match = re.search(r'--project\s+(\S+)', args)
        if project_match:
            project_name = project_match.group(1)

    # If we have file paths, read them
    if file_paths:
        output_parts.append("--- Referenced Files ---")
        for fp in file_paths:
            result = tool_registry.read.execute(fp)
            if result.success:
                output_parts.append("")
                output_parts.append("--- {} ---".format(fp))
                output_parts.append(result.output)
                all_files_read.extend(result.files_read)
            else:
                output_parts.append("")
                output_parts.append("[Could not read {}: {}]".format(fp, result.error))

    # If we have a project, read project data files
    if project_name:
        project_dir = os.path.expanduser(
            "~/fda-510k-data/projects/{}".format(project_name)
        )
        data_files = [
            "device_profile.json",
            "review.json",
            "se_comparison.md",
            "standards_lookup.json",
            "import_data.json",
        ]

        output_parts.append("")
        output_parts.append("--- Project: {} ---".format(project_name))

        for df in data_files:
            df_path = os.path.join(project_dir, df)
            result = tool_registry.read.execute(df_path)
            if result.success:
                output_parts.append("")
                output_parts.append("--- {} ---".format(df))
                # For JSON files, show condensed output
                output_parts.append(result.output[:2000])
                all_files_read.extend(result.files_read)

    # For commands that involve data fetching, use Bash tool for FDA API queries
    if command in ['validate', 'research', 'batchfetch', 'safety', 'warnings']:
        if args:
            # Product code pattern
            pc_match = re.search(r'\b([A-Z]{3})\b', args)
            # K-number pattern
            kn_match = re.search(r'\b(K\d{6})\b', args)

            if kn_match:
                k_number = kn_match.group(1)
                output_parts.append("")
                output_parts.append("--- openFDA Query: {} ---".format(k_number))
                api_url = "https://api.fda.gov/device/510k.json?search=k_number:{}&limit=1".format(k_number)
                bash_result = tool_registry.bash.execute(
                    "curl -s '{}'".format(api_url),
                    timeout=30
                )
                if bash_result.success:
                    output_parts.append(bash_result.output[:3000])

            elif pc_match:
                product_code = pc_match.group(1)
                output_parts.append("")
                output_parts.append("--- openFDA Query: product_code={} ---".format(product_code))
                api_url = "https://api.fda.gov/device/510k.json?search=product_code:{}&limit=5&sort=decision_date:desc".format(product_code)
                bash_result = tool_registry.bash.execute(
                    "curl -s '{}'".format(api_url),
                    timeout=30
                )
                if bash_result.success:
                    output_parts.append(bash_result.output[:3000])

    # Compile output
    output = '\n'.join(output_parts)

    # Add command instruction note
    output += (
        "\n\n--- Bridge Note ---\n"
        "This is a data-gathering execution via the FDA Bridge Server. "
        "The command markdown instructions have been loaded, and relevant "
        "data has been gathered using tool emulators. In a full Claude Code "
        "session, the AI would process this data according to the command "
        "instructions to produce the final output.\n"
        "Command definition: {}".format(str(FDA_COMMANDS_DIR / '{}.md'.format(command)))
    )

    return {
        'success': True,
        'output': output,
        'error': None,
        'files_read': all_files_read,
        'files_written': all_files_written
    }


# ============================================================
# Main entry point
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=BRIDGE_HOST,
        port=BRIDGE_PORT,
        reload=True,
        log_level="info"
    )
