"""
FDA-234  [NPD-003] NPD State Machine (CONCEPT → POST_MARKET)
=============================================================
Event-sourced state machine that governs the 12-stage NPD pipeline.

Design decisions
----------------
1. **Immutable event log** — every transition appends a `NpdEvent` to an
   append-only list.  The "current state" is always derived from the log,
   never mutated in place.  This satisfies 21 CFR Part 11 audit trail
   requirements.

2. **HITL gate enforcement** — transitions guarded by a HITL gate
   (`npd_hitl_gates.HITL_GATES`) require a `GateApprovalRecord` with
   status APPROVED before the transition is allowed.

3. **Agent preconditions** — each stage carries a set of required primary
   agents (from `npd_agent_matrix.STAGE_AGENTS`).  Attempting to advance
   without meeting minimum agent output requirements raises
   `PreconditionError`.

4. **Idempotent re-entry guard** — re-submitting a transition for the
   current stage is a no-op (returns existing state) rather than an error,
   enabling safe retries.

Transition table
----------------
CONCEPT     → CLASSIFY    (no gate)
CLASSIFY    → PREDICATE   (GATE_CLASSIFY — RA Lead)
PREDICATE   → PATHWAY     (GATE_PREDICATE — RA Lead + Engineer)
PATHWAY     → PRESUB      (GATE_PATHWAY — RA Manager)
PRESUB      → TESTING     (no gate)
TESTING     → DRAFTING    (no gate)
DRAFTING    → REVIEW      (no gate)
REVIEW      → SUBMIT      (GATE_SUBMIT — RA Manager + QA Lead)
SUBMIT      → FDA_REVIEW  (no gate)
FDA_REVIEW  → CLEARED     (GATE_CLEARED — RA Lead + QA Lead)
CLEARED     → POST_MARKET (no gate)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from plugins.fda_tools.lib.npd_agent_matrix import NpdStage, get_primary_agents
from plugins.fda_tools.lib.npd_hitl_gates import (
    GateApprovalRecord,
    GateStatus,
    get_gate_for_transition,
)


# ── Event types ───────────────────────────────────────────────────────────────


class NpdEventType(str, Enum):
    PROJECT_CREATED   = "PROJECT_CREATED"
    STAGE_ADVANCED    = "STAGE_ADVANCED"
    GATE_APPROVED     = "GATE_APPROVED"
    GATE_REJECTED     = "GATE_REJECTED"
    AGENT_COMPLETED   = "AGENT_COMPLETED"
    ERROR             = "ERROR"


# ── Errors ────────────────────────────────────────────────────────────────────


class StateMachineError(Exception):
    """Base error for all state machine violations."""


class InvalidTransitionError(StateMachineError):
    """Raised when the requested transition is not valid from current stage."""


class GateBlockedError(StateMachineError):
    """Raised when a HITL gate has not been approved."""


class PreconditionError(StateMachineError):
    """Raised when required agent outputs are missing."""


# ── Immutable event ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NpdEvent:
    """
    Single immutable entry in the project event log.
    All state changes produce an NpdEvent appended to NpdProject.events.
    """
    event_type:  NpdEventType
    timestamp:   datetime
    actor_id:    str               # user ID or agent ID that triggered the event
    from_stage:  Optional[NpdStage] = None
    to_stage:    Optional[NpdStage] = None
    gate_id:     Optional[str]     = None
    agent_id:    Optional[str]     = None
    payload:     Optional[str]     = None   # JSON-serialisable string for extras


# ── Agent completion record ───────────────────────────────────────────────────


@dataclass
class AgentOutput:
    """Records that a required primary agent has completed work for a stage."""
    agent_id:   str
    stage:      NpdStage
    summary:    str    = ""
    timestamp:  datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── Transition table ──────────────────────────────────────────────────────────


# Ordered list of valid (from_stage, to_stage) transitions.
VALID_TRANSITIONS: List[tuple[NpdStage, NpdStage]] = [
    (NpdStage.CONCEPT,     NpdStage.CLASSIFY),
    (NpdStage.CLASSIFY,    NpdStage.PREDICATE),
    (NpdStage.PREDICATE,   NpdStage.PATHWAY),
    (NpdStage.PATHWAY,     NpdStage.PRESUB),
    (NpdStage.PRESUB,      NpdStage.TESTING),
    (NpdStage.TESTING,     NpdStage.DRAFTING),
    (NpdStage.DRAFTING,    NpdStage.REVIEW),
    (NpdStage.REVIEW,      NpdStage.SUBMIT),
    (NpdStage.SUBMIT,      NpdStage.FDA_REVIEW),
    (NpdStage.FDA_REVIEW,  NpdStage.CLEARED),
    (NpdStage.CLEARED,     NpdStage.POST_MARKET),
]

_VALID_TRANSITION_SET = frozenset(VALID_TRANSITIONS)


# ── NPD Project (aggregate root) ──────────────────────────────────────────────


@dataclass
class NpdProject:
    """
    Aggregate root for a single NPD project.

    State is fully reconstructible from `events` (event sourcing pattern).
    Use the factory `NpdProject.create()` to instantiate; never construct
    directly with a pre-set stage.
    """
    project_id:     str
    device_name:    str
    created_by:     str
    events:         List[NpdEvent]          = field(default_factory=list)
    agent_outputs:  Dict[str, AgentOutput]  = field(default_factory=dict)
    # key = f"{stage.value}:{agent_id}"

    # ── Derived state ─────────────────────────────────────────────────────────

    @property
    def current_stage(self) -> NpdStage:
        """Current stage derived from the event log (never stored directly)."""
        stage = NpdStage.CONCEPT
        for event in self.events:
            if event.event_type == NpdEventType.STAGE_ADVANCED and event.to_stage:
                stage = event.to_stage
        return stage

    @property
    def is_complete(self) -> bool:
        return self.current_stage == NpdStage.POST_MARKET

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        project_id:  str,
        device_name: str,
        created_by:  str,
    ) -> "NpdProject":
        project = cls(
            project_id  = project_id,
            device_name = device_name,
            created_by  = created_by,
        )
        project.events.append(NpdEvent(
            event_type = NpdEventType.PROJECT_CREATED,
            timestamp  = datetime.now(timezone.utc),
            actor_id   = created_by,
            to_stage   = NpdStage.CONCEPT,
            payload    = f"Project '{device_name}' created",
        ))
        return project

    # ── Agent output recording ────────────────────────────────────────────────

    def record_agent_output(
        self,
        agent_id:  str,
        summary:   str  = "",
        actor_id:  str  = "system",
    ) -> None:
        """Record that a primary agent has completed its work for the current stage."""
        output = AgentOutput(
            agent_id  = agent_id,
            stage     = self.current_stage,
            summary   = summary,
        )
        key = f"{self.current_stage.value}:{agent_id}"
        self.agent_outputs[key] = output
        self.events.append(NpdEvent(
            event_type = NpdEventType.AGENT_COMPLETED,
            timestamp  = datetime.now(timezone.utc),
            actor_id   = actor_id,
            from_stage = self.current_stage,
            agent_id   = agent_id,
            payload    = summary[:200] if summary else None,
        ))

    def get_completed_agents(self, stage: NpdStage) -> List[str]:
        """Return agent IDs that have completed work for the given stage."""
        prefix = f"{stage.value}:"
        return [key[len(prefix):] for key in self.agent_outputs if key.startswith(prefix)]

    # ── Transition ────────────────────────────────────────────────────────────

    def advance(
        self,
        to_stage:        NpdStage,
        actor_id:        str,
        gate_record:     Optional[GateApprovalRecord] = None,
        skip_agent_check: bool = False,
    ) -> NpdStage:
        """
        Attempt to advance the project to `to_stage`.

        Parameters
        ----------
        to_stage:
            The target stage.
        actor_id:
            ID of the human or system initiating the transition.
        gate_record:
            Required when the transition is guarded by a HITL gate.
            Must have status == APPROVED.
        skip_agent_check:
            When True, skips the primary agent completion check.
            Use only in tests or manual overrides.

        Returns
        -------
        The new current stage (same as `to_stage` on success).

        Raises
        ------
        InvalidTransitionError
            The (current_stage → to_stage) pair is not in the transition table.
        GateBlockedError
            A HITL gate guards this transition and no approved gate_record was supplied.
        PreconditionError
            Required primary agents have not recorded outputs for the current stage.
        """
        from_stage = self.current_stage

        # Idempotent re-entry: already at target
        if from_stage == to_stage:
            return from_stage

        # Validate transition
        if (from_stage, to_stage) not in _VALID_TRANSITION_SET:
            raise InvalidTransitionError(
                f"Transition {from_stage.value} → {to_stage.value} is not valid. "
                f"Current stage: {from_stage.value}"
            )

        # Check HITL gate
        gate = get_gate_for_transition(from_stage.value, to_stage.value)
        if gate is not None:
            if gate_record is None:
                raise GateBlockedError(
                    f"Transition {from_stage.value} → {to_stage.value} requires "
                    f"approval at gate {gate.gate_id.value} before advancing."
                )
            if gate_record.gate_id.value != gate.gate_id.value:
                raise GateBlockedError(
                    f"Supplied gate record is for {gate_record.gate_id.value}, "
                    f"but this transition requires {gate.gate_id.value}."
                )
            if gate_record.status != GateStatus.APPROVED:
                raise GateBlockedError(
                    f"Gate {gate.gate_id.value} has status {gate_record.status.value}; "
                    f"must be APPROVED to advance."
                )
            # Record the gate approval in the event log
            self.events.append(NpdEvent(
                event_type = NpdEventType.GATE_APPROVED,
                timestamp  = datetime.now(timezone.utc),
                actor_id   = gate_record.reviewer_id,
                from_stage = from_stage,
                to_stage   = to_stage,
                gate_id    = gate_record.gate_id.value,
            ))

        # Check primary agent completion
        if not skip_agent_check:
            required = {a.id for a in get_primary_agents(from_stage)}
            completed = set(self.get_completed_agents(from_stage))
            missing = required - completed
            if missing:
                raise PreconditionError(
                    f"Stage {from_stage.value} has incomplete primary agents: "
                    f"{sorted(missing)}. Record agent outputs before advancing."
                )

        # Commit transition
        self.events.append(NpdEvent(
            event_type = NpdEventType.STAGE_ADVANCED,
            timestamp  = datetime.now(timezone.utc),
            actor_id   = actor_id,
            from_stage = from_stage,
            to_stage   = to_stage,
        ))
        return to_stage

    # ── Audit log ─────────────────────────────────────────────────────────────

    def audit_log(self) -> List[dict]:
        """
        Return a serialisable audit trail of all events.
        Suitable for the 21 CFR Part 11 audit log endpoint.
        """
        return [
            {
                "event_type":  e.event_type.value,
                "timestamp":   e.timestamp.isoformat(),
                "actor_id":    e.actor_id,
                "from_stage":  e.from_stage.value  if e.from_stage  else None,
                "to_stage":    e.to_stage.value    if e.to_stage    else None,
                "gate_id":     e.gate_id,
                "agent_id":    e.agent_id,
                "payload":     e.payload,
            }
            for e in self.events
        ]
