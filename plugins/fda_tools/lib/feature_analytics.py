#!/usr/bin/env python3
"""
Feature-Level Analytics for FDA Tools Plugin (FDA-154).

Provides structured, privacy-preserving tracking of command invocations,
workflow steps, and error patterns so product decisions can be made with
data rather than intuition.

Distinct from ``scripts/usage_analytics.py`` (FDA-53) in that:

* Events are typed (``EventType`` enum) rather than freeform.
* Workflow funnel tracking records multi-step sequence completion rates.
* Lives in ``lib/`` for direct import by other modules.
* Error patterns are tracked by error *type*, not message text.

All data is stored locally in ``~/fda-510k-data/.feature_analytics/``.
**Nothing is transmitted externally.**  The module is disabled by default;
analytics are recorded only when explicitly enabled via :meth:`enable`.

Usage::

    from fda_tools.lib.feature_analytics import FeatureAnalytics, EventType

    fa = FeatureAnalytics()
    fa.enable()

    # Record a command invocation
    fa.record_command("batchfetch", success=True, duration_ms=1234.5)

    # Record an error
    fa.record_error("batchfetch", error_type="TimeoutError")

    # Record a workflow step
    fa.record_workflow_step(workflow_id="session-abc", step="predicate_search",
                            command="batchfetch")

    # Analyse usage
    top = fa.top_commands(n=5, days=30)
    errors = fa.error_summary(days=30)
    funnel = fa.workflow_funnels("predicate_workflow", days=30)
"""

from __future__ import annotations

import json
import os
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ANALYTICS_DIR = os.path.expanduser(
    "~/fda-510k-data/.feature_analytics"
)
EVENTS_FILE = "events.jsonl"
STATE_FILE = "state.json"

# Maximum events to retain in the JSONL file (soft cap; pruned on write)
MAX_EVENTS = 10_000

# Safe metadata keys that may be recorded (no PII, no PHI)
SAFE_META_KEYS = frozenset(
    {
        "product_code",
        "product_code_count",
        "k_number_count",
        "result_count",
        "cache_hit",
        "retry_count",
        "page_count",
        "command_version",
    }
)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class EventType(str, Enum):
    """Typed event categories emitted by :class:`FeatureAnalytics`."""

    COMMAND_INVOKED = "command_invoked"
    COMMAND_SUCCEEDED = "command_succeeded"
    COMMAND_FAILED = "command_failed"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_STEP_COMPLETED = "workflow_step_completed"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class FeatureEvent:
    """A single analytics event.

    Attributes:
        event_type: One of the :class:`EventType` values.
        command: Command or feature that generated the event.
        session_id: Per-session random UUID (not tied to identity).
        timestamp: ISO-8601 UTC timestamp.
        duration_ms: Wall-clock duration, if applicable.
        workflow_id: Opaque workflow grouping key, if applicable.
        workflow_step: Step name within a workflow, if applicable.
        error_type: Exception class name, if applicable.
        metadata: Safe key/value context (no PII).
    """

    event_type: EventType
    command: str
    session_id: str
    timestamp: str
    duration_ms: Optional[float] = None
    workflow_id: Optional[str] = None
    workflow_step: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def as_dict(self) -> Dict:
        """Serialize to a plain dictionary (JSON-safe)."""
        d: Dict = {
            "event_type": self.event_type.value,
            "command": self.command,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
        }
        if self.duration_ms is not None:
            d["duration_ms"] = round(self.duration_ms, 2)
        if self.workflow_id is not None:
            d["workflow_id"] = self.workflow_id
        if self.workflow_step is not None:
            d["workflow_step"] = self.workflow_step
        if self.error_type is not None:
            d["error_type"] = self.error_type
        if self.metadata:
            d["metadata"] = self.metadata
        return d


# ---------------------------------------------------------------------------
# FeatureAnalytics
# ---------------------------------------------------------------------------


class FeatureAnalytics:
    """Structured, opt-in feature usage tracker.

    All recordings are no-ops when analytics are disabled.

    Args:
        analytics_dir: Directory for event log and state files.
        session_id: Per-session identifier (auto-generated if not provided).
    """

    def __init__(
        self,
        analytics_dir: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        self._dir = Path(analytics_dir or DEFAULT_ANALYTICS_DIR)
        self._events_path = self._dir / EVENTS_FILE
        self._state_path = self._dir / STATE_FILE
        self._session_id = session_id or str(uuid.uuid4())

    # ------------------------------------------------------------------
    # Enable / disable
    # ------------------------------------------------------------------

    def enable(self) -> None:
        """Enable analytics recording (opt-in)."""
        self._dir.mkdir(parents=True, exist_ok=True)
        self._write_state({"enabled": True})

    def disable(self) -> None:
        """Disable analytics recording."""
        self._write_state({"enabled": False})

    def is_enabled(self) -> bool:
        """Return True if analytics recording is enabled."""
        return self._read_state().get("enabled", False)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_command(
        self,
        command: str,
        *,
        success: bool,
        duration_ms: Optional[float] = None,
        **metadata,
    ) -> None:
        """Record a command invocation with outcome.

        Args:
            command: Command or feature name.
            success: Whether the command completed without error.
            duration_ms: Execution time in milliseconds.
            **metadata: Optional safe context keys (filtered to SAFE_META_KEYS).
        """
        if not self.is_enabled():
            return
        safe_meta = {k: v for k, v in metadata.items() if k in SAFE_META_KEYS}
        event_type = (
            EventType.COMMAND_SUCCEEDED if success else EventType.COMMAND_FAILED
        )
        self._append(
            FeatureEvent(
                event_type=event_type,
                command=command,
                session_id=self._session_id,
                timestamp=self._now(),
                duration_ms=duration_ms,
                metadata=safe_meta,
            )
        )

    def record_error(
        self,
        command: str,
        *,
        error_type: str,
        **metadata,
    ) -> None:
        """Record an error occurrence (by type only — no message text).

        Args:
            command: Command or feature that raised the error.
            error_type: Exception class name (e.g. ``"TimeoutError"``).
            **metadata: Optional safe context keys.
        """
        if not self.is_enabled():
            return
        safe_meta = {k: v for k, v in metadata.items() if k in SAFE_META_KEYS}
        self._append(
            FeatureEvent(
                event_type=EventType.ERROR_OCCURRED,
                command=command,
                session_id=self._session_id,
                timestamp=self._now(),
                error_type=error_type,
                metadata=safe_meta,
            )
        )

    def record_workflow_step(
        self,
        workflow_id: str,
        step: str,
        command: str,
    ) -> None:
        """Record completion of one step in a multi-step workflow.

        Args:
            workflow_id: Opaque identifier grouping steps of one workflow
                run (e.g. a session ID).
            step: Step name within the workflow.
            command: Command that completed this step.
        """
        if not self.is_enabled():
            return
        self._append(
            FeatureEvent(
                event_type=EventType.WORKFLOW_STEP_COMPLETED,
                command=command,
                session_id=self._session_id,
                timestamp=self._now(),
                workflow_id=workflow_id,
                workflow_step=step,
            )
        )

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def top_commands(self, n: int = 10, days: int = 30) -> List[Dict]:
        """Return the *n* most-used commands in the last *days* days.

        Returns:
            List of ``{"command": str, "count": int}`` dicts sorted by
            count descending.
        """
        events = self._load_events(days=days)
        counter: Counter = Counter()
        for ev in events:
            if ev.get("event_type") in (
                EventType.COMMAND_SUCCEEDED.value,
                EventType.COMMAND_FAILED.value,
            ):
                counter[ev["command"]] += 1
        return [
            {"command": cmd, "count": cnt}
            for cmd, cnt in counter.most_common(n)
        ]

    def error_summary(self, days: int = 30) -> Dict:
        """Return error counts grouped by error type and command.

        Returns:
            Dictionary mapping ``error_type`` → ``{"total": int,
            "by_command": {command: count}}``.
        """
        events = self._load_events(days=days)
        result: Dict[str, Dict] = defaultdict(
            lambda: {"total": 0, "by_command": Counter()}
        )
        for ev in events:
            if ev.get("event_type") == EventType.ERROR_OCCURRED.value:
                etype = ev.get("error_type", "Unknown")
                result[etype]["total"] += 1
                result[etype]["by_command"][ev.get("command", "")] += 1
        # Convert Counter → plain dict for JSON serialisation
        return {
            etype: {"total": d["total"], "by_command": dict(d["by_command"])}
            for etype, d in result.items()
        }

    def workflow_funnels(self, workflow_id: str, days: int = 30) -> Dict:
        """Return step completion rates for *workflow_id*.

        Counts how many times each step name was recorded for the given
        workflow identifier.

        Returns:
            Dictionary mapping step name → completion count.
        """
        events = self._load_events(days=days)
        step_counts: Counter = Counter()
        for ev in events:
            if (
                ev.get("event_type") == EventType.WORKFLOW_STEP_COMPLETED.value
                and ev.get("workflow_id") == workflow_id
            ):
                step_counts[ev.get("workflow_step", "")] += 1
        return dict(step_counts)

    def get_events(self, days: int = 30) -> List[Dict]:
        """Return raw event dicts recorded within the last *days* days."""
        return self._load_events(days=days)

    def clear(self) -> None:
        """Delete all recorded events."""
        self._events_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append(self, event: FeatureEvent) -> None:
        """Append *event* to the JSONL file."""
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._events_path, "a") as f:
            f.write(json.dumps(event.as_dict()) + "\n")

    def _load_events(self, days: int = 30) -> List[Dict]:
        """Read JSONL events newer than *days* days."""
        if not self._events_path.exists():
            return []
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=days)
        ).isoformat()
        events: List[Dict] = []
        try:
            with open(self._events_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                        if ev.get("timestamp", "") >= cutoff:
                            events.append(ev)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
        return events

    def _read_state(self) -> Dict:
        if not self._state_path.exists():
            return {}
        try:
            with open(self._state_path, "r") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_state(self, state: Dict) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        tmp = self._state_path.with_suffix(".tmp")
        try:
            with open(tmp, "w") as f:
                json.dump(state, f)
            tmp.replace(self._state_path)
        except OSError:
            tmp.unlink(missing_ok=True)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
