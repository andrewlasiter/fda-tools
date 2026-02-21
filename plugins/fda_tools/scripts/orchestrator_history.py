#!/usr/bin/env python3
"""orchestrator_history — Append-only JSONL log for orchestrator runs.

Each orchestrator run appends one JSON record to
``~/.fda_tools/orchestrator_history.jsonl``.  The records are later
consumed by :class:`MLAgentSelector` to train the gradient-boosted
agent selection model (ORCH-008).

Storage format (one JSON object per line)::

    {
      "timestamp": "2026-02-21T14:35:00Z",
      "task_type": "security_review",
      "languages": ["python"],
      "domains": ["fda", "medical_devices"],
      "complexity": 3,
      "agents": ["voltagent-qa-sec:security-auditor", "..."],
      "findings_by_severity": {"critical": 2, "high": 5, "medium": 3},
      "resolved_count": 6
    }

Usage::

    from fda_tools.scripts.orchestrator_history import OrchestratorHistory

    history = OrchestratorHistory()
    history.log_run(
        task_type="security_review",
        languages=["python"],
        domains=["fda"],
        complexity=3,
        agents=["voltagent-qa-sec:security-auditor"],
        findings_by_severity={"critical": 2, "high": 5, "medium": 3},
        resolved_count=6,
    )
    runs = history.load_history()
    print(f"Total runs: {len(runs)}")
"""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default storage directory; overridable for tests.
DEFAULT_DATA_DIR = Path.home() / ".fda_tools"
HISTORY_FILENAME = "orchestrator_history.jsonl"


class OrchestratorHistory:
    """Append-only JSONL log of orchestrator runs.

    Args:
        data_dir: Base directory for FDA Tools data.  Defaults to
            ``~/.fda_tools``.  The history file is written to
            ``{data_dir}/orchestrator_history.jsonl``.
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self._history_path = self._data_dir / HISTORY_FILENAME

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_run(
        self,
        task_type: str,
        languages: list[str],
        domains: list[str],
        complexity: int,
        agents: list[str],
        findings_by_severity: dict[str, int],
        resolved_count: int,
    ) -> None:
        """Append one orchestrator run record to the history file.

        The write is atomic: the record is first written to a temporary
        file in the same directory, then renamed into place so that a
        crash mid-write cannot corrupt the existing history.

        Args:
            task_type: Orchestrator task type string (e.g. "security_review").
            languages: Programming languages detected in the task.
            domains: Domain tags for the task (e.g. ["fda", "medical_devices"]).
            complexity: Task complexity on a 1–5 ordinal scale.
            agents: List of agent names that were selected and executed.
            findings_by_severity: Counts of findings by severity level.
                Expected keys: "critical", "high", "medium", "low".
            resolved_count: Number of findings that were resolved after
                Linear issues were created and closed.
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_type": task_type,
            "languages": list(languages),
            "domains": list(domains),
            "complexity": int(complexity),
            "agents": list(agents),
            "findings_by_severity": dict(findings_by_severity),
            "resolved_count": int(resolved_count),
        }
        self._append_record(record)
        logger.debug("Logged orchestrator run: task_type=%s, agents=%d", task_type, len(agents))

    def load_history(self) -> list[dict[str, Any]]:
        """Load all history records from the JSONL file.

        Returns:
            List of run records ordered from oldest to newest.
            Returns an empty list if no history file exists yet.
        """
        if not self._history_path.exists():
            return []

        records: list[dict[str, Any]] = []
        with self._history_path.open("r", encoding="utf-8") as fh:
            for line_num, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    # Skip corrupt lines rather than aborting — the log may have been
                    # truncated by a crash, and the remaining records are still valid.
                    logger.warning("Skipping corrupt history record on line %d: %s", line_num, exc)

        return records

    def run_count(self) -> int:
        """Return the number of logged runs without loading full records into memory."""
        if not self._history_path.exists():
            return 0
        count = 0
        with self._history_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    count += 1
        return count

    def clear(self) -> None:
        """Delete the history file (useful for tests and resets)."""
        if self._history_path.exists():
            self._history_path.unlink()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append_record(self, record: dict[str, Any]) -> None:
        """Write a single record to the JSONL file atomically."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n"

        # Write to a temp file in the same directory so that os.rename()
        # is atomic on POSIX (same filesystem).
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self._data_dir,
            prefix=".history_tmp_",
            delete=False,
            suffix=".jsonl",
        ) as tmp:
            tmp_path = Path(tmp.name)
            # Copy existing file content before appending the new record.
            if self._history_path.exists():
                with self._history_path.open("r", encoding="utf-8") as existing:
                    for existing_line in existing:
                        tmp.write(existing_line)
            tmp.write(line)

        # Rename is atomic on POSIX; on Windows it overwrites the destination.
        tmp_path.replace(self._history_path)
