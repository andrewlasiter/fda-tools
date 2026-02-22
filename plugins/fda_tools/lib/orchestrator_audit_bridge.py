"""
FDA-265  [ORCH-012] Orchestrator Decision Audit Trail
======================================================
Wires orchestrator execution decisions — team selection, phase transitions,
workflow completion, permission violations, and rollbacks — into the
21 CFR Part 11–compliant ``Part11AuditLog``.

The bridge is *additive*: ``OrchestratorHistory`` (JSONL) continues to work
unchanged.  The bridge simply ensures that every governance-relevant decision
is also captured in the tamper-evident append-only audit log.

Usage
-----
    from fda_tools.lib.cfr_part11 import Part11AuditLog
    from fda_tools.lib.orchestrator_audit_bridge import OrchestratorAuditBridge

    log    = Part11AuditLog()
    bridge = OrchestratorAuditBridge(log=log)

    bridge.log_team_selection(
        team_data={"core_agents": ["security-auditor"], "total_agents": 1},
        task_profile_data={"task_type": "security_review", "complexity": "high"},
        user_id="alice@example.com",
    )
    bridge.log_phase_start(phase=1, agents=["security-auditor"], user_id="system")
    bridge.log_phase_complete(phase=1, findings_count=3, user_id="system")
    bridge.log_workflow_complete(run_summary={"run_id": "abc123"}, user_id="system")

    assert len(log.records()) == 4
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from fda_tools.lib.cfr_part11 import AuditAction, AuditRecord, Part11AuditLog

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorAuditBridge:
    """
    Bridge between the orchestrator execution pipeline and the Part 11 audit log.

    Every public method creates an ``AuditRecord``, appends it to *log*, and
    returns it so callers can attach signatures or inspect the record.

    Attributes:
        log:                The ``Part11AuditLog`` instance to write into.
        system_user_id:     User ID attributed to automated orchestrator actions.
        system_display_name: Human-readable label for the orchestrator system.
    """

    log:                 Part11AuditLog
    system_user_id:      str = "orchestrator@system"
    system_display_name: str = "Orchestrator System"

    # ── Private helper ────────────────────────────────────────────────────────

    def _append(
        self,
        action:      AuditAction,
        subject_id:  str,
        content_data: Dict[str, Any],
    ) -> AuditRecord:
        record = AuditRecord.create(
            user_id      = self.system_user_id,
            display_name = self.system_display_name,
            action       = action,
            record_type  = "orchestrator_event",
            subject_id   = subject_id,
            content      = json.dumps(content_data, default=str),
        )
        self.log.append(record)
        logger.debug("OrchestratorAuditBridge: appended %s for subject '%s'", action.value, subject_id)
        return record

    # ── Public logging methods ────────────────────────────────────────────────

    def log_team_selection(
        self,
        team_data:         Dict[str, Any],
        task_profile_data: Dict[str, Any],
        user_id:           str = "",
    ) -> AuditRecord:
        """Record which agent team was selected and why (task profile)."""
        return self._append(
            AuditAction.CREATE,
            f"team_selection:{task_profile_data.get('task_type', 'unknown')}",
            {
                "event":         "team_selection",
                "requested_by":  user_id or self.system_user_id,
                "task_profile":  task_profile_data,
                "team":          team_data,
            },
        )

    def log_phase_start(
        self,
        phase:   int,
        agents:  List[str],
        user_id: str = "",
    ) -> AuditRecord:
        """Record the start of an execution phase and which agents are involved."""
        return self._append(
            AuditAction.CREATE,
            f"phase_{phase}_start",
            {
                "event":        "phase_start",
                "phase":        phase,
                "agents":       agents,
                "requested_by": user_id or self.system_user_id,
            },
        )

    def log_phase_complete(
        self,
        phase:          int,
        findings_count: int,
        user_id:        str = "",
    ) -> AuditRecord:
        """Record successful completion of a phase with its finding count."""
        return self._append(
            AuditAction.UPDATE,
            f"phase_{phase}_complete",
            {
                "event":          "phase_complete",
                "phase":          phase,
                "findings_count": findings_count,
                "completed_by":   user_id or self.system_user_id,
            },
        )

    def log_workflow_complete(
        self,
        run_summary: Dict[str, Any],
        user_id:     str = "",
    ) -> AuditRecord:
        """Record the end of a full orchestrator workflow run."""
        return self._append(
            AuditAction.EXPORT,
            f"workflow_complete:{run_summary.get('run_id', 'unknown')}",
            {
                "event":        "workflow_complete",
                "run_summary":  run_summary,
                "completed_by": user_id or self.system_user_id,
            },
        )

    def log_permission_violation(
        self,
        agent_id: str,
        action:   str,
        user_id:  str = "",
    ) -> AuditRecord:
        """Record a pre-flight permission check failure (§11.10(d) access control)."""
        return self._append(
            AuditAction.ACCESS_DENIED,
            f"permission_violation:{agent_id}",
            {
                "event":       "permission_violation",
                "agent_id":    agent_id,
                "action":      action,
                "detected_by": user_id or self.system_user_id,
            },
        )

    def log_rollback(
        self,
        stage:       str,
        reason:      str,
        snapshot_id: str,
        user_id:     str = "",
    ) -> AuditRecord:
        """Record an NPD workflow rollback to a prior snapshot."""
        return self._append(
            AuditAction.UPDATE,
            f"rollback:{stage}",
            {
                "event":        "workflow_rollback",
                "stage":        stage,
                "reason":       reason,
                "snapshot_id":  snapshot_id,
                "triggered_by": user_id or self.system_user_id,
            },
        )

    def log_agent_performance(
        self,
        agent_id:      str,
        run_id:        str,
        score:         float,
        finding_count: int,
        user_id:       str = "",
    ) -> AuditRecord:
        """Record agent performance metrics for a completed run."""
        return self._append(
            AuditAction.UPDATE,
            f"agent_performance:{agent_id}:{run_id}",
            {
                "event":         "agent_performance",
                "agent_id":      agent_id,
                "run_id":        run_id,
                "score":         score,
                "finding_count": finding_count,
                "recorded_by":   user_id or self.system_user_id,
            },
        )
