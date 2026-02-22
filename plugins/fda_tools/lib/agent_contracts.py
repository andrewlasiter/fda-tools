"""
FDA-268  [ORCH-015] Agent I/O Contract Enforcement
====================================================
Pydantic v2 schemas for agent inputs and outputs, with validation at every
agent boundary in the ExecutionCoordinator pipeline.

Problem
-------
Multi-agent workflows currently pass data as untyped dicts.  Schema
divergence (e.g. a finding dict missing the ``severity`` key) is only
discovered at Linear issue creation or NPD state transitions — far downstream
from the agent that produced the bad data.

Solution
--------
Three Pydantic v2 models define the contract:

    AgentFinding      — a single finding from one agent (severity, location, etc.)
    AgentOutput       — the full output of one agent in one phase
    AggregatedResults — the merged output of all agents across all phases

``validate_agent_output(raw)`` wraps ``AgentOutput.model_validate()`` and
raises ``AgentContractViolation`` (not a raw Pydantic error) on mismatch,
providing agent_id, field_path, expected_type, and received_value for
debuggability.

Pydantic fallback
-----------------
If Pydantic v2 is not installed, lightweight dataclass-based stubs are used
so the module always imports.  Validation in the stub path checks only
required fields and types (not nested schemas).

Usage
-----
    from fda_tools.lib.agent_contracts import validate_agent_output, build_finding, aggregate

    raw = {
        "agent_id": "voltagent-qa-sec:security-auditor",
        "phase": 2,
        "findings": [
            {
                "finding_id": "abc123",
                "severity": "high",
                "location": "api/auth.py:45",
                "description": "Missing rate limiting",
                "recommendation": "Add rate limiting middleware",
                "agent_id": "voltagent-qa-sec:security-auditor",
                "confidence": 0.92,
            }
        ],
        "metadata": {},
    }
    output = validate_agent_output(raw)   # AgentOutput
    results = aggregate([output])         # AggregatedResults
"""

from __future__ import annotations

import secrets
from typing import Any, Dict, List, Literal, Optional

# Pydantic v2 optional import
field_validator: Any = None  # reassigned below if pydantic available
try:
    from pydantic import BaseModel, field_validator, ValidationError as _PydanticValidationError
    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PYDANTIC_AVAILABLE = False
    BaseModel = object                        # type: ignore[assignment,misc]
    _PydanticValidationError = Exception      # type: ignore[assignment,misc]


# ── Exception ─────────────────────────────────────────────────────────────────

class AgentContractViolation(Exception):
    """
    Raised when an agent output fails schema validation.

    Attributes:
        agent_id:       The agent that produced the invalid output.
        field_path:     Dot-notation path to the offending field (e.g. "findings.0.severity").
        expected_type:  Human-readable description of the expected type.
        received_value: The actual value that was received.
    """

    def __init__(
        self,
        agent_id:       str,
        field_path:     str,
        expected_type:  str,
        received_value: Any,
    ) -> None:
        self.agent_id       = agent_id
        self.field_path     = field_path
        self.expected_type  = expected_type
        self.received_value = received_value
        super().__init__(
            f"Contract violation for agent '{agent_id}': "
            f"field '{field_path}' expected {expected_type}, "
            f"got {type(received_value).__name__!r} = {received_value!r}"
        )


# ── Pydantic v2 models (primary path) ────────────────────────────────────────

if _PYDANTIC_AVAILABLE:

    class AgentFinding(BaseModel):  # type: ignore[valid-type]
        """A single finding emitted by one agent."""
        finding_id:     str
        severity:       Literal["critical", "high", "medium", "low"]
        location:       str
        description:    str
        recommendation: str
        agent_id:       str
        confidence:     float = 1.0

        @field_validator("confidence")
        @classmethod
        def _confidence_range(cls, v: float) -> float:
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"confidence must be 0.0–1.0, got {v}")
            return v

    class AgentOutput(BaseModel):  # type: ignore[valid-type]
        """The complete output of one agent for one execution phase."""
        agent_id:  str
        phase:     int
        findings:  List[AgentFinding] = []
        metadata:  Dict[str, Any] = {}

    class AggregatedResults(BaseModel):  # type: ignore[valid-type]
        """Merged findings from all agents across all phases of a workflow run."""
        run_id:         str
        findings:       List[AgentFinding] = []
        agent_outputs:  List[AgentOutput] = []
        total_findings: int = 0

# ── Fallback stubs (no Pydantic) ──────────────────────────────────────────────

else:
    _VALID_SEVERITIES = frozenset({"critical", "high", "medium", "low"})

    class AgentFinding:  # type: ignore[no-redef]
        """Minimal stub when Pydantic is not available."""

        def __init__(
            self,
            finding_id:     str,
            severity:       str,
            location:       str,
            description:    str,
            recommendation: str,
            agent_id:       str,
            confidence:     float = 1.0,
        ) -> None:
            if severity not in _VALID_SEVERITIES:
                raise ValueError(f"Invalid severity '{severity}'; must be one of {sorted(_VALID_SEVERITIES)}")
            if not 0.0 <= confidence <= 1.0:
                raise ValueError(f"confidence must be 0.0–1.0, got {confidence}")
            self.finding_id     = finding_id
            self.severity       = severity
            self.location       = location
            self.description    = description
            self.recommendation = recommendation
            self.agent_id       = agent_id
            self.confidence     = confidence

    class AgentOutput:  # type: ignore[no-redef]
        """Minimal stub when Pydantic is not available."""

        def __init__(
            self,
            agent_id:  str,
            phase:     int,
            findings:  Optional[List[Any]] = None,
            metadata:  Optional[Dict[str, Any]] = None,
        ) -> None:
            self.agent_id = agent_id
            self.phase    = phase
            self.findings = findings or []
            self.metadata = metadata or {}

    class AggregatedResults:  # type: ignore[no-redef]
        """Minimal stub when Pydantic is not available."""

        def __init__(
            self,
            run_id:         str,
            findings:       Optional[List[Any]] = None,
            agent_outputs:  Optional[List[Any]] = None,
            total_findings: int = 0,
        ) -> None:
            self.run_id         = run_id
            self.findings       = findings or []
            self.agent_outputs  = agent_outputs or []
            self.total_findings = total_findings


# ── Public API ────────────────────────────────────────────────────────────────

def validate_agent_output(raw: Dict[str, Any]) -> "AgentOutput":  # type: ignore[type-arg]
    """
    Validate a raw dict as an ``AgentOutput`` schema.

    Args:
        raw: Untyped dict from an agent execution result.

    Returns:
        A validated ``AgentOutput`` instance.

    Raises:
        AgentContractViolation: On any schema mismatch.
    """
    agent_id = raw.get("agent_id", "unknown")
    try:
        if _PYDANTIC_AVAILABLE:
            return AgentOutput.model_validate(raw)  # type: ignore[attr-defined,return-value]
        # ── Minimal manual validation (stub path) ──────────────────────────
        if "agent_id" not in raw or not isinstance(raw["agent_id"], str):
            raise AgentContractViolation(agent_id, "agent_id", "str", raw.get("agent_id"))
        if "phase" not in raw:
            raise AgentContractViolation(agent_id, "phase", "int", None)
        if not isinstance(raw["phase"], int):
            raise AgentContractViolation(agent_id, "phase", "int", raw["phase"])
        return AgentOutput(  # type: ignore[return-value]
            agent_id = raw["agent_id"],
            phase    = raw["phase"],
            findings = raw.get("findings", []),
            metadata = raw.get("metadata", {}),
        )
    except AgentContractViolation:
        raise
    except _PydanticValidationError as exc:
        # Unwrap Pydantic error to our domain exception
        errors = exc.errors() if hasattr(exc, "errors") else []  # type: ignore[attr-defined]
        field_path     = ".".join(str(loc) for loc in errors[0]["loc"]) if errors else "unknown"
        expected_type  = errors[0].get("type", "unknown") if errors else "unknown"
        received_value = errors[0].get("input") if errors else raw
        raise AgentContractViolation(agent_id, field_path, expected_type, received_value) from exc
    except Exception as exc:
        raise AgentContractViolation(agent_id, str(exc), "AgentOutput", raw) from exc


def build_finding(
    agent_id:       str,
    severity:       str,
    location:       str,
    description:    str,
    recommendation: str,
    confidence:     float = 1.0,
) -> "AgentFinding":  # type: ignore[type-arg]
    """
    Convenience factory for creating a valid ``AgentFinding``.

    Auto-generates a ``finding_id`` using ``secrets.token_hex(8)``.
    """
    if _PYDANTIC_AVAILABLE:
        return AgentFinding(  # type: ignore[call-arg,return-value]
            finding_id     = secrets.token_hex(8),
            severity       = severity,
            location       = location,
            description    = description,
            recommendation = recommendation,
            agent_id       = agent_id,
            confidence     = confidence,
        )
    return AgentFinding(  # type: ignore[return-value]
        finding_id     = secrets.token_hex(8),
        severity       = severity,
        location       = location,
        description    = description,
        recommendation = recommendation,
        agent_id       = agent_id,
        confidence     = confidence,
    )


def aggregate(
    agent_outputs: "List[AgentOutput]",  # type: ignore[type-arg]
    run_id:        Optional[str] = None,
) -> "AggregatedResults":  # type: ignore[type-arg]
    """
    Merge a list of ``AgentOutput`` objects into a single ``AggregatedResults``.

    Args:
        agent_outputs: Results from all agents in the workflow.
        run_id:        Optional run identifier; auto-generated if not provided.

    Returns:
        An ``AggregatedResults`` containing all findings across all agents.
    """
    all_findings: List[Any] = []
    for output in agent_outputs:
        all_findings.extend(output.findings)

    rid = run_id or secrets.token_hex(8)

    if _PYDANTIC_AVAILABLE:
        return AggregatedResults(  # type: ignore[call-arg,return-value]
            run_id         = rid,
            findings       = all_findings,
            agent_outputs  = agent_outputs,
            total_findings = len(all_findings),
        )
    return AggregatedResults(  # type: ignore[return-value]
        run_id         = rid,
        findings       = all_findings,
        agent_outputs  = agent_outputs,
        total_findings = len(all_findings),
    )
