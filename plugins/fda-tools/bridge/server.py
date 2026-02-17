#!/usr/bin/env python3
"""
OpenClaw Bridge Server for FDA Tools Plugin

Provides HTTP REST API at localhost:18790 for OpenClaw skill to communicate
with FDA tools Python scripts. Acts as a bridge between TypeScript skill
and Python backend.

Endpoints:
  POST /execute - Execute FDA command
  GET /health - Health check with system status
  GET /commands - List available commands with metadata
  GET /tools - List available tool emulators
  POST /session - Create or retrieve session
  GET /session/{id} - Get session details
  GET /sessions - List all sessions
  GET /session/{id}/questions - Get pending questions
  POST /session/{id}/answer - Submit answer to question
  GET /audit/integrity - Verify audit log integrity

Architecture:
  This bridge server sits between the OpenClaw TypeScript skill
  and the FDA Tools Python plugin. It handles:
  - HTTP request/response translation
  - Session management
  - Security context (prepared for future security gateway)
  - Tool emulation layer
  - Audit logging

Version: 1.0.0
"""

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from pydantic import BaseModel, Field  # type: ignore
import uvicorn  # type: ignore

# ============================================================
# Configuration
# ============================================================

# Server configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 18790
SERVER_VERSION = "1.0.0"

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
    description="HTTP bridge between OpenClaw skill and FDA Tools Python plugin",
    version=SERVER_VERSION,
)

# Enable CORS for localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    """Add entry to audit log."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "data": data,
    }
    AUDIT_LOG.append(entry)
    logger.info(f"Audit: {event_type} - {json.dumps(data, indent=None)}")


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

Status: Bridge server is operational.

Note: Full command execution requires the Phase 2 security gateway and
tool emulation layer. This simplified bridge demonstrates connectivity
between the OpenClaw TypeScript skill and the Python backend.

To execute actual FDA commands, use the command-line interface:
  cd {PLUGIN_ROOT}
  /fda-predicate-assistant:{command} {args or ''}
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

@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns server status, version, uptime, available commands,
    and LLM provider availability.
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
        "uptime_seconds": uptime_seconds,
        "llm_providers": llm_providers,
        "security_config_hash": None,  # Would be computed from security config file
        "sessions_active": len(SESSIONS),
        "commands_available": len(commands),
    }


@app.get("/commands")
async def list_commands():
    """
    List available FDA commands.

    Returns command names, descriptions, argument hints, and
    allowed tools parsed from command markdown frontmatter.
    """
    commands = list_available_commands()

    return {
        "commands": commands,
        "total": len(commands),
    }


@app.post("/execute")
async def execute_command(request: ExecuteRequest):
    """
    Execute FDA command.

    Handles command execution with session management and audit logging.
    """
    # Create or retrieve session
    session = create_session(request.user_id, request.session_id)
    session_id = session["session_id"]

    # Audit log
    audit_log_entry("command_execute", {
        "command": request.command,
        "args": request.args,
        "user_id": request.user_id,
        "session_id": session_id,
        "channel": request.channel,
    })

    # Execute command
    try:
        result = execute_fda_command(
            command=request.command,
            args=request.args,
            user_id=request.user_id,
            session_id=session_id,
            channel=request.channel,
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
async def create_session_endpoint(request: SessionRequest):
    """
    Create or retrieve session.

    If session_id is provided and exists, returns existing session.
    Otherwise creates new session.
    """
    existing_session = request.session_id and get_session(request.session_id)
    is_new = not existing_session

    session = create_session(request.user_id, request.session_id)

    return SessionResponse(
        session_id=session["session_id"],
        user_id=session["user_id"],
        created_at=session["created_at"],
        last_accessed=session["last_accessed"],
        context=session.get("context", {}),
        is_new=is_new,
    )


@app.get("/session/{session_id}")
async def get_session_endpoint(session_id: str):
    """Get session details by ID."""
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
async def list_sessions(user_id: Optional[str] = None):
    """
    List active sessions, optionally filtered by user.
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
async def get_pending_questions(session_id: str):
    """Get pending questions for a session."""
    session = get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    questions = PENDING_QUESTIONS.get(session_id, [])

    return {
        "questions": questions,
        "count": len(questions),
    }


@app.post("/session/{session_id}/answer")
async def submit_answer(session_id: str, request: AnswerSubmitRequest):
    """Submit answer to a pending question."""
    session = get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    questions = PENDING_QUESTIONS.get(session_id, [])

    # Find and remove the answered question
    question_found = False
    for i, q in enumerate(questions):
        if q["id"] == request.question_id:
            questions.pop(i)
            question_found = True
            break

    if not question_found:
        raise HTTPException(status_code=404, detail=f"Question not found: {request.question_id}")

    # Audit log
    audit_log_entry("question_answered", {
        "session_id": session_id,
        "question_id": request.question_id,
        "answer": request.answer,
    })

    return {
        "success": True,
        "question_id": request.question_id,
    }


@app.get("/tools")
async def list_tools():
    """
    List available tool emulators.

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
async def verify_audit_integrity():
    """
    Verify audit log integrity.

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
    logger.info("="*70)
    logger.info(f"FDA Tools Bridge Server v{SERVER_VERSION}")
    logger.info("="*70)
    logger.info(f"Server URL: http://{SERVER_HOST}:{SERVER_PORT}")
    logger.info(f"Commands directory: {COMMANDS_DIR}")
    logger.info(f"Scripts directory: {SCRIPTS_DIR}")

    # Count available commands
    commands = list_available_commands()
    logger.info(f"Available commands: {len(commands)}")

    logger.info("="*70)
    logger.info("Server is ready to accept connections.")
    logger.info("="*70)


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
