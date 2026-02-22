"""
FDA-266  [ORCH-013] NPD Workflow Rollback & Compensation
=========================================================
Implements the Saga compensating-transaction pattern for the NPD state
machine.  Before each stage transition the orchestrator calls
``NpdRollbackManager.snapshot()``; if the transition fails (agent error,
HITL gate REJECTED, or validation failure) the caller invokes
``rollback_to_last_snapshot()`` to restore the last known-good project state.

Design
------
``NpdSnapshot`` is an immutable value object (frozen dataclass) that captures:
  - The stage name at the time of capture
  - A deep copy of the project data dict
  - A UTC timestamp and a random ``snapshot_id``
  - A ``is_good`` flag (True by default; set False when the snapshot becomes
    the "bad" state that triggered a rollback)

``NpdRollbackManager`` maintains an append-only list of snapshots.
``rollback_to_last_snapshot()`` returns the most recent *good* snapshot
without removing anything from the list — rollback history is preserved for
the audit trail.

Usage
-----
    mgr = NpdRollbackManager()

    # Before advancing from CONCEPT → CLASSIFY
    snap1 = mgr.snapshot("CONCEPT", project_data)

    try:
        state_machine.advance()
        snap2 = mgr.snapshot("CLASSIFY", updated_data)
    except TransitionError as exc:
        mgr.mark_last_bad()                       # mark the failed snap as bad
        prev = mgr.rollback_to_last_snapshot()     # returns snap1
        project_data = prev.restore()              # deep copy of snap1 data
        audit_bridge.log_rollback("CLASSIFY", str(exc), prev.snapshot_id)
"""

from __future__ import annotations

import copy
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List


# ── Exceptions ────────────────────────────────────────────────────────────────

class RollbackError(Exception):
    """Raised when no suitable snapshot is available for rollback."""


# ── Snapshot ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class NpdSnapshot:
    """
    Immutable point-in-time capture of NPD project state.

    Attributes:
        snapshot_id:  Random hex token uniquely identifying this snapshot.
        stage:        NPD stage name at time of capture (string form of NpdStage).
        project_data: Deep copy of the project data dict at capture time.
        timestamp:    UTC ISO 8601 timestamp.
        is_good:      True if this snapshot represents a valid, recoverable state.
    """
    snapshot_id:  str
    stage:        str
    project_data: Dict[str, Any]
    timestamp:    str
    is_good:      bool

    def restore(self) -> Dict[str, Any]:
        """Return a deep copy of the captured project data."""
        return copy.deepcopy(self.project_data)


# ── Manager ───────────────────────────────────────────────────────────────────

class NpdRollbackManager:
    """
    Append-only snapshot store with rollback and compensation support.

    All snapshots are kept in sequence; rollback returns the latest *good*
    snapshot without truncating history (the audit trail remains complete).
    """

    def __init__(self) -> None:
        self._snapshots: List[NpdSnapshot] = []

    # ── Snapshot creation ─────────────────────────────────────────────────────

    def snapshot(
        self,
        stage:        Any,
        project_data: Dict[str, Any],
        is_good:      bool = True,
    ) -> NpdSnapshot:
        """
        Capture the current project state before a stage transition.

        Args:
            stage:        Current NPD stage (any object whose str() is meaningful).
            project_data: Current project data dict (will be deep-copied).
            is_good:      Mark this snapshot as a valid recovery point (default True).

        Returns:
            The newly created ``NpdSnapshot``.
        """
        snap = NpdSnapshot(
            snapshot_id  = secrets.token_hex(8),
            stage        = str(stage),
            project_data = copy.deepcopy(project_data),
            timestamp    = datetime.now(timezone.utc).isoformat(),
            is_good      = is_good,
        )
        self._snapshots.append(snap)
        return snap

    # ── Rollback ──────────────────────────────────────────────────────────────

    def rollback_to_last_snapshot(self) -> NpdSnapshot:
        """
        Return the most recent *good* snapshot for recovery.

        Does NOT remove any snapshots — history is always preserved.

        Raises:
            RollbackError: If there are no good snapshots available.
        """
        good = [s for s in self._snapshots if s.is_good]
        if not good:
            raise RollbackError("No good snapshot available for rollback")
        return good[-1]

    def rollback_to_last_good_before(self, stage: Any) -> NpdSnapshot:
        """
        Return the most recent good snapshot captured *before* the given stage.

        Useful when the current stage itself is the one that failed.

        Args:
            stage: Stage to exclude (any object whose str() matches snapshot.stage).

        Raises:
            RollbackError: If no eligible good snapshot exists.
        """
        stage_str = str(stage)
        good = [s for s in self._snapshots if s.is_good and s.stage != stage_str]
        if not good:
            raise RollbackError(f"No good snapshot before stage '{stage_str}'")
        return good[-1]

    # ── Mutation helpers ──────────────────────────────────────────────────────

    def mark_last_bad(self) -> None:
        """
        Mark the most recently captured snapshot as *bad* (not a good recovery point).

        Typically called after a transition fails, before rolling back.
        NpdSnapshot is frozen, so we replace it in the list with is_good=False.
        """
        if not self._snapshots:
            return
        old = self._snapshots[-1]
        # Replace the frozen dataclass with a new instance having is_good=False
        self._snapshots[-1] = NpdSnapshot(
            snapshot_id  = old.snapshot_id,
            stage        = old.stage,
            project_data = old.project_data,
            timestamp    = old.timestamp,
            is_good      = False,
        )

    # ── Inspection ────────────────────────────────────────────────────────────

    def get_snapshot_chain(self) -> List[NpdSnapshot]:
        """Return a copy of the full ordered snapshot list (oldest first)."""
        return list(self._snapshots)

    def snapshot_count(self) -> int:
        """Total number of snapshots (good + bad)."""
        return len(self._snapshots)

    def good_snapshot_count(self) -> int:
        """Number of snapshots marked as good recovery points."""
        return sum(1 for s in self._snapshots if s.is_good)

    def latest_stage(self) -> str:
        """Stage name of the most recent snapshot, or '' if none exist."""
        return self._snapshots[-1].stage if self._snapshots else ""
