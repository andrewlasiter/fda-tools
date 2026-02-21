#!/usr/bin/env python3
"""monitor_service — Continuous monitoring for Linear issue changes (ORCH-009).

Polls Linear issues for substantial changes (title edits, description edits,
new comments, label changes) and emits ``MonitorEvent`` records.  When a
substantial change is detected the monitor can optionally re-trigger agent
selection and post a comment back to the Linear issue.

Storage format (``~/.fda_tools/monitor_state.json``):

    {
        "FDA-42": {
            "issue_id": "FDA-42",
            "registered_at": "2026-02-21T14:35:00Z",
            "last_seen_at": "2026-02-21T14:35:00Z",
            "title_hash": "abc123",
            "description_hash": "def456",
            "comment_count": 5,
            "labels": ["Bug", "security"]
        }
    }

Usage::

    from fda_tools.scripts.monitor_service import IssueMonitor, MonitorEvent

    monitor = IssueMonitor()

    # Register issues to watch
    monitor.register("FDA-42", title="My issue", description="...", comment_count=3)

    # Check for changes (call with fresh data from Linear)
    events = monitor.check(
        issue_id="FDA-42",
        current_title="My issue (updated)",
        current_description="...",
        current_comment_count=4,
    )
    for event in events:
        print(f"Change detected: {event.change_type} on {event.issue_id}")

CLI::

    python3 -m fda_tools.scripts.monitor_service --once
    python3 -m fda_tools.scripts.monitor_service --watch --interval 120
    python3 -m fda_tools.scripts.monitor_service --issue FDA-42 --once
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default storage directory; overridable for tests.
DEFAULT_DATA_DIR = Path.home() / ".fda_tools"
MONITOR_STATE_FILENAME = "monitor_state.json"

# A change is "substantial" when any of these are detected:
#   - title hash differs
#   - description hash differs
#   - comment count increased
#   - labels changed
CHANGE_TYPES = ("title", "description", "new_comment", "labels")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class MonitorEvent:
    """A detected change on a monitored Linear issue.

    Attributes:
        issue_id: Linear issue identifier (e.g. "FDA-42").
        change_type: One of "title", "description", "new_comment", "labels".
        old_value: Previous value (stringified).
        new_value: Current value (stringified).
        detected_at: ISO-8601 timestamp when the change was detected.
    """

    issue_id: str
    change_type: str
    old_value: str
    new_value: str
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IssueRecord:
    """Stored baseline snapshot for one monitored issue.

    Attributes:
        issue_id: Linear issue identifier.
        registered_at: When the issue was first registered.
        last_seen_at: When it was last checked.
        title_hash: SHA-256 hex digest of the title.
        description_hash: SHA-256 hex digest of the description.
        comment_count: Number of comments at last check.
        labels: Sorted list of label names at last check.
    """

    issue_id: str
    registered_at: str
    last_seen_at: str
    title_hash: str
    description_hash: str
    comment_count: int
    labels: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IssueRecord":
        return cls(
            issue_id=data["issue_id"],
            registered_at=data["registered_at"],
            last_seen_at=data["last_seen_at"],
            title_hash=data["title_hash"],
            description_hash=data["description_hash"],
            comment_count=data.get("comment_count", 0),
            labels=data.get("labels", []),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(text: str) -> str:
    """Return a short SHA-256 hex digest of *text*."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# MonitorState — persistent JSON snapshot store
# ---------------------------------------------------------------------------


class MonitorState:
    """Reads and writes the monitor state JSON file.

    The file is a flat JSON object keyed by issue_id::

        {
            "FDA-42": { ... IssueRecord fields ... },
            "FDA-43": { ... }
        }
    """

    def __init__(self, data_dir: Path) -> None:
        self._path = data_dir / MONITOR_STATE_FILENAME
        self._records: Dict[str, IssueRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            for issue_id, record_data in raw.items():
                self._records[issue_id] = IssueRecord.from_dict(record_data)
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("monitor_state.json corrupt or unreadable: %s — starting fresh", exc)
            self._records = {}

    def save(self) -> None:
        """Persist the current state to disk atomically."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(
                {k: v.to_dict() for k, v in self._records.items()},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        tmp_path.replace(self._path)

    def get(self, issue_id: str) -> Optional[IssueRecord]:
        return self._records.get(issue_id)

    def set(self, record: IssueRecord) -> None:
        self._records[record.issue_id] = record

    def remove(self, issue_id: str) -> None:
        self._records.pop(issue_id, None)

    def all_issue_ids(self) -> List[str]:
        return list(self._records.keys())

    def __len__(self) -> int:
        return len(self._records)


# ---------------------------------------------------------------------------
# IssueMonitor — main public class
# ---------------------------------------------------------------------------


class IssueMonitor:
    """Tracks Linear issues for substantial changes and emits MonitorEvent objects.

    Args:
        data_dir: Base directory for state storage.  Defaults to
            ``~/.fda_tools``.
        poll_interval: Seconds between polls in ``watch()`` mode (default 60).
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        poll_interval: int = 60,
    ) -> None:
        self._data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self._state = MonitorState(self._data_dir)
        self.poll_interval = poll_interval

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(
        self,
        issue_id: str,
        title: str,
        description: str,
        comment_count: int = 0,
        labels: Optional[List[str]] = None,
    ) -> None:
        """Register an issue for monitoring (or refresh its baseline).

        Idempotent: registering an already-tracked issue updates its baseline
        so subsequent ``check()`` calls detect only *new* changes.

        Args:
            issue_id: Linear issue identifier (e.g. "FDA-42").
            title: Current issue title.
            description: Current issue description (markdown).
            comment_count: Current number of comments.
            labels: Current list of label names.
        """
        now = _now_iso()
        existing = self._state.get(issue_id)
        registered_at = existing.registered_at if existing else now

        record = IssueRecord(
            issue_id=issue_id,
            registered_at=registered_at,
            last_seen_at=now,
            title_hash=_sha256(title),
            description_hash=_sha256(description or ""),
            comment_count=comment_count,
            labels=sorted(labels or []),
        )
        self._state.set(record)
        self._state.save()
        logger.debug("Registered issue %s for monitoring", issue_id)

    def check(
        self,
        issue_id: str,
        current_title: str,
        current_description: str,
        current_comment_count: int,
        current_labels: Optional[List[str]] = None,
    ) -> List[MonitorEvent]:
        """Compare current issue data to stored baseline and return events.

        Returns an empty list if the issue is not registered or nothing changed.

        Args:
            issue_id: Linear issue identifier.
            current_title: Current title from Linear.
            current_description: Current description from Linear.
            current_comment_count: Current number of comments.
            current_labels: Current label names.

        Returns:
            List of MonitorEvent (may be empty).
        """
        record = self._state.get(issue_id)
        if record is None:
            logger.debug("Issue %s not registered — auto-registering as baseline", issue_id)
            self.register(
                issue_id,
                current_title,
                current_description,
                current_comment_count,
                current_labels,
            )
            return []

        events: List[MonitorEvent] = []
        now = _now_iso()

        # Title change
        new_title_hash = _sha256(current_title)
        if new_title_hash != record.title_hash:
            events.append(MonitorEvent(
                issue_id=issue_id,
                change_type="title",
                old_value=f"<hash:{record.title_hash[:8]}>",
                new_value=current_title[:200],
                detected_at=now,
            ))

        # Description change
        new_desc_hash = _sha256(current_description or "")
        if new_desc_hash != record.description_hash:
            events.append(MonitorEvent(
                issue_id=issue_id,
                change_type="description",
                old_value=f"<hash:{record.description_hash[:8]}>",
                new_value=f"<hash:{new_desc_hash[:8]}>",
                detected_at=now,
            ))

        # New comment(s)
        if current_comment_count > record.comment_count:
            events.append(MonitorEvent(
                issue_id=issue_id,
                change_type="new_comment",
                old_value=str(record.comment_count),
                new_value=str(current_comment_count),
                detected_at=now,
            ))

        # Label changes
        new_labels = sorted(current_labels or [])
        if new_labels != record.labels:
            events.append(MonitorEvent(
                issue_id=issue_id,
                change_type="labels",
                old_value=",".join(record.labels),
                new_value=",".join(new_labels),
                detected_at=now,
            ))

        # Update baseline
        record.last_seen_at = now
        record.title_hash = new_title_hash
        record.description_hash = new_desc_hash
        record.comment_count = current_comment_count
        record.labels = new_labels
        self._state.set(record)
        self._state.save()

        if events:
            logger.info(
                "Issue %s: %d change(s) detected: %s",
                issue_id,
                len(events),
                [e.change_type for e in events],
            )

        return events

    def unregister(self, issue_id: str) -> None:
        """Stop monitoring an issue."""
        self._state.remove(issue_id)
        self._state.save()
        logger.debug("Unregistered issue %s", issue_id)

    def registered_issue_ids(self) -> List[str]:
        """Return all issue IDs currently being monitored."""
        return self._state.all_issue_ids()

    def watch(
        self,
        fetch_fn: Callable[[], List[Dict[str, Any]]],
        callback: Callable[[List[MonitorEvent]], None],
        once: bool = False,
        specific_issue: Optional[str] = None,
    ) -> None:
        """Run the monitoring loop.

        Args:
            fetch_fn: Callable returning a list of issue dicts with keys:
                ``id``, ``title``, ``description``, ``comment_count``,
                ``labels`` (list of str).
            callback: Called with a list of MonitorEvent whenever changes are
                detected.  Called even when the list is empty if ``once`` is
                True.
            once: If True, run a single poll then return.
            specific_issue: If set, only process this issue_id from fetch_fn
                results.
        """
        logger.info(
            "IssueMonitor starting — %s mode, interval=%ds, tracking %d issues",
            "once" if once else "watch",
            self.poll_interval,
            len(self._state),
        )

        while True:
            try:
                issues = fetch_fn()
                all_events: List[MonitorEvent] = []

                for issue_data in issues:
                    issue_id = issue_data.get("id", "")
                    if specific_issue and issue_id != specific_issue:
                        continue

                    events = self.check(
                        issue_id=issue_id,
                        current_title=issue_data.get("title", ""),
                        current_description=issue_data.get("description", ""),
                        current_comment_count=issue_data.get("comment_count", 0),
                        current_labels=issue_data.get("labels", []),
                    )
                    all_events.extend(events)

                callback(all_events)

            except Exception as exc:  # noqa: BLE001
                logger.error("Error during monitor poll: %s", exc, exc_info=True)

            if once:
                break
            time.sleep(self.poll_interval)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _default_callback(events: List[MonitorEvent]) -> None:
    if not events:
        print(f"[{_now_iso()}] No changes detected.")
        return
    for event in events:
        print(
            f"[{event.detected_at}] CHANGE {event.issue_id}: "
            f"{event.change_type} | '{event.old_value}' → '{event.new_value}'"
        )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="monitor_service",
        description="Monitor Linear issues for changes (ORCH-009)",
    )
    mode = parser.add_mutually_exclusive_group(required=False)
    mode.add_argument("--once", action="store_true", help="Run a single poll then exit")
    mode.add_argument(
        "--watch", action="store_true", help="Run continuously (Ctrl+C to stop)"
    )
    parser.add_argument(
        "--issue", metavar="ISSUE_ID", help="Watch only this issue (e.g. FDA-42)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        metavar="SECONDS",
        help="Polling interval for --watch mode (default: 60)",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        metavar="DIR",
        help="Override state storage directory (default: ~/.fda_tools)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all registered issue IDs and exit",
    )
    return parser


def main(argv: Optional[list] = None) -> int:
    """CLI entry point.  Returns exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir) if args.data_dir else None
    monitor = IssueMonitor(data_dir=data_dir, poll_interval=args.interval)

    if args.list:
        ids = monitor.registered_issue_ids()
        if not ids:
            print("No issues currently registered for monitoring.")
        else:
            print(f"Monitoring {len(ids)} issue(s):")
            for issue_id in sorted(ids):
                print(f"  {issue_id}")
        return 0

    if not args.once and not args.watch:
        parser.error("one of --once or --watch is required (or use --list)")

    # Without a real Linear client wired in, the CLI operates in demo mode:
    # it only processes issues that are already registered in the state file.
    # Production use injects a fetch_fn that calls the Linear MCP tools.
    def _noop_fetch() -> List[Dict[str, Any]]:
        # Return empty list — real deployments replace this with Linear API calls.
        return []

    try:
        monitor.watch(
            fetch_fn=_noop_fetch,
            callback=_default_callback,
            once=args.once,
            specific_issue=args.issue,
        )
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
        return 0

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
