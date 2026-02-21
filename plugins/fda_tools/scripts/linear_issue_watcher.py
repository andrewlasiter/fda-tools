#!/usr/bin/env python3
"""
LinearIssueWatcher — Poll Linear issues and re-trigger review on substantial updates.

Provides continuous monitoring for the Universal Multi-Agent Orchestrator (FDA-213/ORCH-009):

1. ``LinearIssueWatcher`` — polls a set of issue IDs at a configurable interval
   and yields ``IssueUpdate`` objects whenever a watched issue has changed since
   the last poll.
2. ``SubstanceDetector`` — classifies each update as *substantial* (should
   re-trigger a review) or *informational* (log only).
3. Re-trigger logic — when a substantial update is detected the watcher posts a
   structured ``[Re-review YYYY-MM-DD]`` comment on the original issue.
4. State persistence — ``last_seen_updatedAt`` timestamps are written to a JSON
   file so the daemon survives restarts without replaying old updates.
5. Graceful shutdown — catches ``SIGINT``/``SIGTERM`` and exits cleanly.

Usage (daemon mode via CLI):
    python3 -m fda_tools.scripts.universal_orchestrator watch \\
        --issue-ids "FDA-83,FDA-96,FDA-97" \\
        --poll-interval 300

Usage (library mode):
    from fda_tools.scripts.linear_issue_watcher import LinearIssueWatcher

    watcher = LinearIssueWatcher(poll_interval_seconds=120)
    for update in watcher.watch(["FDA-83", "FDA-96"]):
        if update.is_substantial:
            watcher.post_rereview_comment(update)
"""

import json
import logging
import re
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Substance detection patterns
# ---------------------------------------------------------------------------

# Comments / descriptions that indicate code has been written or submitted.
_SUBSTANTIAL_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bfixed\b", re.IGNORECASE),
    re.compile(r"\bimplemented\b", re.IGNORECASE),
    re.compile(r"\brefactored\b", re.IGNORECASE),
    re.compile(r"\bcompleted\b", re.IGNORECASE),
    re.compile(r"\bresolve[sd]?\b", re.IGNORECASE),
    re.compile(r"\bmerged?\b", re.IGNORECASE),
    re.compile(r"\bcode change[s]?\b", re.IGNORECASE),
    re.compile(r"\bpull request\b", re.IGNORECASE),
    re.compile(r"\bPR\s+#?\d+", re.IGNORECASE),
    re.compile(r"https?://github\.com/[^/]+/[^/]+/pull/\d+"),
    re.compile(r"\bcommit\s+[0-9a-f]{6,40}\b", re.IGNORECASE),
    re.compile(r"\bpatch\b", re.IGNORECASE),
    re.compile(r"\bre-?implement\b", re.IGNORECASE),
    re.compile(r"\bready for review\b", re.IGNORECASE),
    re.compile(r"\blgtm\b", re.IGNORECASE),
]

# Patterns that are *explicitly* informational (lower priority).
_INFORMATIONAL_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bfyi\b", re.IGNORECASE),
    re.compile(r"\bblocked\b", re.IGNORECASE),
    re.compile(r"\bwaiting\b", re.IGNORECASE),
    re.compile(r"\bin progress\b", re.IGNORECASE),
    re.compile(r"\backnowledge[d]?\b", re.IGNORECASE),
    re.compile(r"\bwill do\b", re.IGNORECASE),
    re.compile(r"\bnoted\b", re.IGNORECASE),
]

# Minimum substantial-signal score before we call an update substantial.
_SUBSTANTIAL_THRESHOLD = 1


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class IssueUpdate:
    """Represents a detected change on a watched Linear issue.

    Attributes:
        issue_id: Linear identifier (e.g. ``"FDA-83"``).
        updated_at: UTC timestamp of the detected change.
        new_comments: Comment bodies added since last poll.
        description_changed: Whether the issue description changed.
        status_changed: Whether the Linear status changed.
        is_substantial: Whether the update warrants a re-review.
        substance_reason: Human-readable explanation of the classification.
    """

    issue_id: str
    updated_at: datetime
    new_comments: List[str] = field(default_factory=list)
    description_changed: bool = False
    status_changed: bool = False
    is_substantial: bool = False
    substance_reason: str = ""

    def __str__(self) -> str:
        """Return one-line summary suitable for logging."""
        kind = "SUBSTANTIAL" if self.is_substantial else "informational"
        return (
            f"[{kind}] {self.issue_id} @ {self.updated_at.isoformat()}"
            f" — {self.substance_reason or 'no reason'}"
        )


# ---------------------------------------------------------------------------
# SubstanceDetector
# ---------------------------------------------------------------------------


class SubstanceDetector:
    """Classify an ``IssueUpdate`` as substantial or informational.

    A *substantial* update is one that suggests code was written, merged, or
    reviewed — meaning a follow-up automated re-review adds value.

    An *informational* update is a status comment, acknowledgement, or
    label change that does not warrant re-running the full review pipeline.

    Scoring logic:
    - Each matching ``_SUBSTANTIAL_PATTERN`` in any comment/description adds 1.
    - Each matching ``_INFORMATIONAL_PATTERN`` subtracts 0.5 (net deduction).
    - ``description_changed`` always adds 1.
    - Score ≥ ``_SUBSTANTIAL_THRESHOLD`` → substantial.
    """

    def classify(self, update: IssueUpdate) -> IssueUpdate:
        """Classify *update* in-place and return it.

        Sets ``update.is_substantial`` and ``update.substance_reason``.
        """
        score = 0.0
        reasons: List[str] = []

        texts = list(update.new_comments)
        if update.description_changed:
            # Description change is always at least mildly substantial.
            score += 1.0
            reasons.append("description changed")

        for text in texts:
            for pattern in _SUBSTANTIAL_PATTERNS:
                if pattern.search(text):
                    score += 1.0
                    reasons.append(f"matched '{pattern.pattern}'")
                    break  # one substantial hit per comment is enough

            for pattern in _INFORMATIONAL_PATTERNS:
                if pattern.search(text):
                    score -= 0.5
                    break  # one informational hit per comment is enough

        update.is_substantial = score >= _SUBSTANTIAL_THRESHOLD
        update.substance_reason = "; ".join(reasons) if reasons else "no signal"
        return update


# ---------------------------------------------------------------------------
# LinearIssueWatcher
# ---------------------------------------------------------------------------


class LinearIssueWatcher:
    """Poll Linear issues and yield updates when they change.

    The watcher maintains a ``last_seen`` timestamp for every watched issue
    and compares it against the ``updatedAt`` field returned by the Linear
    API.  When an issue has been modified since the last poll, the watcher
    fetches new comments, classifies the update via ``SubstanceDetector``,
    and yields an ``IssueUpdate``.

    State (``last_seen`` timestamps) is persisted to a JSON file so the
    daemon survives restarts without replaying old events.

    Args:
        poll_interval_seconds: Seconds between poll cycles (default 300 = 5 min).
        state_dir: Directory for persisting state; defaults to
            ``~/.fda-510k-data/.watcher_state``.
        linear_client: Optional callable used to query Linear.  Must accept
            ``(issue_id: str) -> dict`` and return a dict with keys
            ``updatedAt`` (ISO-8601 string), ``description`` (str),
            ``comments`` (list of ``{body, createdAt}`` dicts).
            Defaults to a stub that always returns no change — suitable for
            unit-testing.  The real orchestrator injects its MCP wrapper.
        orchestrator: Optional callable used to re-trigger a review.  Must
            accept ``(issue_id: str, context: str)`` and return a markdown
            summary string.  Defaults to a no-op stub.
    """

    def __init__(
        self,
        poll_interval_seconds: int = 300,
        state_dir: Optional[Path] = None,
        linear_client=None,
        orchestrator=None,
    ) -> None:
        """Initialise the watcher."""
        self.poll_interval = poll_interval_seconds
        self.state_dir = state_dir or (
            Path.home() / ".fda-510k-data" / ".watcher_state"
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self.state_dir / "linear_watcher_state.json"

        self._linear_client = linear_client or _stub_linear_client
        self._orchestrator = orchestrator or _stub_orchestrator
        self._detector = SubstanceDetector()

        # {issue_id: last_seen_updatedAt_isoformat}
        self._last_seen: Dict[str, str] = self._load_state()

        # Shutdown flag set by SIGINT/SIGTERM handler.
        self._shutdown = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def watch(self, issue_ids: List[str]) -> Generator[IssueUpdate, None, None]:
        """Poll *issue_ids* indefinitely and yield each detected update.

        This is a blocking generator.  Each iteration polls all issues,
        sleeps ``poll_interval_seconds``, then polls again.

        The generator exits cleanly when ``self._shutdown`` is set (e.g. by
        a SIGINT handler) so callers can treat it like a normal for-loop.

        Args:
            issue_ids: Linear identifiers to monitor (e.g. ``["FDA-83"]``).

        Yields:
            ``IssueUpdate`` for every issue that changed since the last poll.
        """
        self._install_signal_handlers()
        logger.info(
            "LinearIssueWatcher started — watching %d issues, interval=%ds",
            len(issue_ids),
            self.poll_interval,
        )

        while not self._shutdown:
            for issue_id in issue_ids:
                if self._shutdown:
                    break
                try:
                    updates = self._check_issue(issue_id)
                    for upd in updates:
                        yield upd
                except Exception:
                    logger.exception("Error checking issue %s", issue_id)

            if not self._shutdown:
                logger.debug("Poll cycle complete; sleeping %ds", self.poll_interval)
                self._interruptible_sleep(self.poll_interval)

        logger.info("LinearIssueWatcher shut down cleanly.")

    def post_rereview_comment(self, update: IssueUpdate) -> str:
        """Re-trigger review for *update* and post findings as a comment.

        The orchestrator is invoked with the issue ID and the first 500 chars
        of the most-recent substantial comment (or empty string) as context.
        Results are posted back to the Linear issue as a markdown comment
        tagged ``[Re-review YYYY-MM-DD]``.

        Args:
            update: A substantial ``IssueUpdate``.

        Returns:
            The comment body that was posted.
        """
        if not update.is_substantial:
            raise ValueError(
                f"post_rereview_comment called on non-substantial update: {update}"
            )

        context = (update.new_comments[-1][:500] if update.new_comments else "")
        logger.info("Re-triggering review for %s (context: %d chars)", update.issue_id, len(context))

        review_summary = self._orchestrator(update.issue_id, context)
        date_tag = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        comment = (
            f"## [Re-review {date_tag}]\n\n"
            f"*Automatically triggered by LinearIssueWatcher — "
            f"substantial change detected: {update.substance_reason}*\n\n"
            f"{review_summary}"
        )
        logger.info("Posted re-review comment on %s", update.issue_id)
        return comment

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_issue(self, issue_id: str) -> List[IssueUpdate]:
        """Return a list of new updates for *issue_id* (empty if unchanged)."""
        data = self._linear_client(issue_id)
        remote_updated_at: str = data.get("updatedAt", "")
        last_seen = self._last_seen.get(issue_id, "")

        if not remote_updated_at or remote_updated_at == last_seen:
            return []

        # Determine what changed since last poll.
        new_comments = self._extract_new_comments(data, last_seen)
        description_changed = data.get("descriptionChanged", False)
        status_changed = data.get("statusChanged", False)

        updated_at = _parse_iso(remote_updated_at)
        upd = IssueUpdate(
            issue_id=issue_id,
            updated_at=updated_at,
            new_comments=new_comments,
            description_changed=description_changed,
            status_changed=status_changed,
        )
        self._detector.classify(upd)

        # Persist new timestamp before yielding.
        self._last_seen[issue_id] = remote_updated_at
        self._save_state()

        logger.info("%s", upd)
        return [upd]

    @staticmethod
    def _extract_new_comments(data: dict, since_iso: str) -> List[str]:
        """Return comment bodies posted after *since_iso*."""
        comments: List[dict] = data.get("comments", [])
        if not since_iso:
            return [c["body"] for c in comments if "body" in c]

        since_dt = _parse_iso(since_iso)
        new: List[str] = []
        for c in comments:
            created_raw = c.get("createdAt", "")
            if created_raw:
                try:
                    created_dt = _parse_iso(created_raw)
                    if created_dt > since_dt:
                        new.append(c.get("body", ""))
                except ValueError:
                    new.append(c.get("body", ""))
        return new

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> Dict[str, str]:
        """Load persisted ``last_seen`` timestamps from disk."""
        if not self._state_file.exists():
            return {}
        try:
            return json.loads(self._state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read watcher state from %s; starting fresh.", self._state_file)
            return {}

    def _save_state(self) -> None:
        """Atomically write ``last_seen`` timestamps to disk."""
        tmp = self._state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._last_seen, indent=2), encoding="utf-8")
        tmp.replace(self._state_file)

    # ------------------------------------------------------------------
    # Shutdown / signal handling
    # ------------------------------------------------------------------

    def _install_signal_handlers(self) -> None:
        """Register SIGINT/SIGTERM handlers for graceful shutdown.

        Signal handlers can only be installed from the main thread.  When
        ``watch()`` is called from a background thread (e.g. in tests or
        embedded usage), the installation is silently skipped and callers
        must set ``self._shutdown = True`` directly to stop the loop.
        """
        def _handler(signum, _frame):  # noqa: ANN001
            logger.info("Received signal %d — shutting down watcher…", signum)
            self._shutdown = True

        try:
            signal.signal(signal.SIGINT, _handler)
            signal.signal(signal.SIGTERM, _handler)
        except ValueError:
            # Not the main thread; signal handling not available.
            logger.debug("Signal handlers skipped (not main thread).")

    def _interruptible_sleep(self, seconds: float) -> None:
        """Sleep in 1-second increments so SIGINT wakes the loop promptly."""
        deadline = time.monotonic() + seconds
        while not self._shutdown and time.monotonic() < deadline:
            time.sleep(min(1.0, deadline - time.monotonic()))


# ---------------------------------------------------------------------------
# Stub implementations (used when no real clients are injected)
# ---------------------------------------------------------------------------


def _stub_linear_client(_issue_id: str) -> dict:
    """Stub that always reports no change.  Replace with MCP wrapper."""
    return {"updatedAt": "", "comments": [], "descriptionChanged": False, "statusChanged": False}


def _stub_orchestrator(issue_id: str, context: str) -> str:
    """Stub that returns a placeholder review summary."""
    return (
        f"*Re-review stub — no orchestrator injected.*\n\n"
        f"Issue `{issue_id}` was flagged for re-review based on a substantial update.\n"
        f"Context snippet: `{context[:200]}…`"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_iso(iso_string: str) -> datetime:
    """Parse an ISO-8601 timestamp string, always returning a UTC datetime."""
    # Python 3.9 does not support the trailing 'Z' in fromisoformat.
    cleaned = iso_string.replace("Z", "+00:00")
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
