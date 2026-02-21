#!/usr/bin/env python3
"""
AgentPerformanceTracker — Track and rank agent effectiveness across reviews.

Implements FDA-214 (ORCH-010) — Phase 10 of the Universal Multi-Agent Orchestrator.

Provides:

1. ``AgentRecord`` — per-agent counters (runs, findings, critical hits,
   resolutions, duplicates) plus a computed effectiveness score.
2. ``AgentPerformanceTracker`` — JSON-backed store with atomic writes,
   methods to record new review results, rank all agents, and identify
   low-performing agents for optional exclusion.
3. ``effectiveness_score()`` — composite formula:
   ``(finding_rate × 0.3) + (critical_hit_rate × 0.4)
   + (resolution_rate × 0.2) − (duplication_rate × 0.1)``

Storage format (``~/.fda_tools/agent_performance.json``):

.. code-block:: json

   {
     "voltagent-qa-sec:security-auditor": {
       "total_runs": 47,
       "total_findings": 312,
       "critical_findings": 89,
       "findings_resolved": 201,
       "duplicate_findings": 23,
       "effectiveness_score": 0.78,
       "last_updated": "2026-02-21"
     }
   }

Low-performance threshold:
   ``effectiveness_score < 0.2`` after ``≥ 20`` total runs.
   Low-performing agents are flagged but not removed unless ``--strict``
   mode is requested by the caller.

Usage (library)::

    from fda_tools.scripts.agent_performance_tracker import AgentPerformanceTracker

    tracker = AgentPerformanceTracker()
    tracker.record_run(
        agent_name="voltagent-qa-sec:security-auditor",
        findings=12,
        critical_findings=4,
        findings_resolved=9,
        duplicate_findings=1,
    )
    ranked = tracker.rank_agents()
    low = tracker.get_low_performers()
"""

import argparse
import json
import logging
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Number of runs an agent must accumulate before it can be flagged as
#: low-performing.  Below this threshold the score is considered provisional.
MIN_RUNS_FOR_FLAGGING: int = 20

#: Effectiveness score below which an agent is considered low-performing
#: (only applied after ``MIN_RUNS_FOR_FLAGGING`` runs).
LOW_PERFORMANCE_THRESHOLD: float = 0.2

#: Composite score weights — must sum to 1.0.
WEIGHT_FINDING_RATE: float = 0.3
WEIGHT_CRITICAL_HIT: float = 0.4
WEIGHT_RESOLUTION: float = 0.2
WEIGHT_DUPLICATION_PENALTY: float = 0.1  # subtracted

#: Default normalisation cap for ``finding_rate``.  Scores are clamped to
#: ``[0, 1]`` before weighting so a hyper-prolific agent cannot exceed 1.0.
FINDING_RATE_CAP: float = 10.0


# ---------------------------------------------------------------------------
# AgentRecord
# ---------------------------------------------------------------------------


@dataclass
class AgentRecord:
    """Cumulative performance counters for a single agent.

    Attributes:
        agent_name: Fully-qualified agent identifier (e.g.
            ``"voltagent-qa-sec:security-auditor"``).
        total_runs: Number of reviews the agent has participated in.
        total_findings: Cumulative findings reported across all runs.
        critical_findings: Cumulative CRITICAL + HIGH findings.
        findings_resolved: Findings confirmed resolved by a re-review or
            Linear issue close.
        duplicate_findings: Findings also reported by at least one other
            agent in the same review (overlap penalises score).
        effectiveness_score: Computed composite score (0–1 range).
        last_updated: ISO date of most recent ``record_run`` call.
        is_low_performer: True when flagged after ``MIN_RUNS_FOR_FLAGGING``
            runs with score below ``LOW_PERFORMANCE_THRESHOLD``.
    """

    agent_name: str
    total_runs: int = 0
    total_findings: int = 0
    critical_findings: int = 0
    findings_resolved: int = 0
    duplicate_findings: int = 0
    effectiveness_score: float = 0.0
    last_updated: str = ""
    is_low_performer: bool = False

    # ------------------------------------------------------------------
    # Score computation
    # ------------------------------------------------------------------

    def recompute_score(self) -> None:
        """Recompute ``effectiveness_score`` from current counters.

        Called automatically by ``AgentPerformanceTracker.record_run()``.
        Safe to call on a record with zero runs (returns 0.0).
        """
        self.effectiveness_score = effectiveness_score(
            total_runs=self.total_runs,
            total_findings=self.total_findings,
            critical_findings=self.critical_findings,
            findings_resolved=self.findings_resolved,
            duplicate_findings=self.duplicate_findings,
        )
        self.is_low_performer = (
            self.total_runs >= MIN_RUNS_FOR_FLAGGING
            and self.effectiveness_score < LOW_PERFORMANCE_THRESHOLD
        )

    def to_dict(self) -> dict:
        """Serialise to a plain dict suitable for JSON storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentRecord":
        """Deserialise from a plain dict (unknown keys silently ignored)."""
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


# ---------------------------------------------------------------------------
# Effectiveness score formula
# ---------------------------------------------------------------------------


def effectiveness_score(
    total_runs: int,
    total_findings: int,
    critical_findings: int,
    findings_resolved: int,
    duplicate_findings: int,
) -> float:
    """Compute a composite effectiveness score in ``[0.0, 1.0]``.

    Formula::

        finding_rate     = min(total_findings / (total_runs * FINDING_RATE_CAP), 1.0)
        critical_hit_rate = critical_findings / total_findings  (or 0 if no findings)
        resolution_rate   = findings_resolved / total_findings  (or 0 if no findings)
        duplication_rate  = duplicate_findings / total_findings (or 0 if no findings)

        score = (finding_rate       × WEIGHT_FINDING_RATE)
              + (critical_hit_rate  × WEIGHT_CRITICAL_HIT)
              + (resolution_rate    × WEIGHT_RESOLUTION)
              − (duplication_rate   × WEIGHT_DUPLICATION_PENALTY)

    The score is clamped to ``[0.0, 1.0]``.

    Args:
        total_runs: Number of reviews the agent participated in.
        total_findings: Total findings across all runs.
        critical_findings: CRITICAL + HIGH findings.
        findings_resolved: Findings confirmed as resolved.
        duplicate_findings: Findings also found by another agent.

    Returns:
        Effectiveness score in ``[0.0, 1.0]``.
    """
    if total_runs == 0:
        return 0.0

    finding_rate = min(
        total_findings / (total_runs * FINDING_RATE_CAP), 1.0
    )
    if total_findings > 0:
        critical_hit_rate = critical_findings / total_findings
        resolution_rate = findings_resolved / total_findings
        duplication_rate = duplicate_findings / total_findings
    else:
        critical_hit_rate = 0.0
        resolution_rate = 0.0
        duplication_rate = 0.0

    raw = (
        finding_rate * WEIGHT_FINDING_RATE
        + critical_hit_rate * WEIGHT_CRITICAL_HIT
        + resolution_rate * WEIGHT_RESOLUTION
        - duplication_rate * WEIGHT_DUPLICATION_PENALTY
    )
    return max(0.0, min(1.0, raw))


# ---------------------------------------------------------------------------
# AgentPerformanceTracker
# ---------------------------------------------------------------------------


class AgentPerformanceTracker:
    """Persistent store for per-agent performance metrics.

    Reads and writes ``~/.fda_tools/agent_performance.json`` (or a custom
    path).  Writes are atomic (write to ``.tmp`` then rename) to prevent
    partial-write corruption.

    Args:
        store_path: Path to the JSON performance store.  Defaults to
            ``~/.fda_tools/agent_performance.json``.
    """

    def __init__(self, store_path: Optional[Path] = None) -> None:
        """Initialise the tracker and load existing data from disk."""
        self.store_path = store_path or (
            Path.home() / ".fda_tools" / "agent_performance.json"
        )
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: Dict[str, AgentRecord] = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_run(
        self,
        agent_name: str,
        findings: int,
        critical_findings: int = 0,
        findings_resolved: int = 0,
        duplicate_findings: int = 0,
    ) -> AgentRecord:
        """Record the result of one review run for *agent_name*.

        Increments all counters, recomputes the effectiveness score, and
        persists to disk.

        Args:
            agent_name: Fully-qualified agent identifier.
            findings: Total findings the agent reported in this run.
            critical_findings: How many were CRITICAL or HIGH severity.
            findings_resolved: How many of the agent's findings from
                *previous* runs have been resolved (can be 0 if unknown).
            duplicate_findings: Findings that overlapped with another
                agent in the same review.

        Returns:
            Updated ``AgentRecord`` for *agent_name*.
        """
        record = self._records.get(agent_name) or AgentRecord(agent_name=agent_name)
        record.total_runs += 1
        record.total_findings += findings
        record.critical_findings += critical_findings
        record.findings_resolved += findings_resolved
        record.duplicate_findings += duplicate_findings
        record.last_updated = date.today().isoformat()
        record.recompute_score()
        self._records[agent_name] = record
        self._save()
        logger.debug(
            "Recorded run for %s: findings=%d score=%.3f",
            agent_name, findings, record.effectiveness_score,
        )
        return record

    def get_record(self, agent_name: str) -> Optional[AgentRecord]:
        """Return the ``AgentRecord`` for *agent_name*, or None if unknown."""
        return self._records.get(agent_name)

    def rank_agents(
        self,
        min_runs: int = 1,
        include_low_performers: bool = True,
    ) -> List[AgentRecord]:
        """Return agents sorted by effectiveness score (descending).

        Args:
            min_runs: Exclude agents with fewer than this many total runs.
            include_low_performers: When False, exclude flagged agents.

        Returns:
            Sorted list of ``AgentRecord`` objects.
        """
        candidates = [
            r for r in self._records.values()
            if r.total_runs >= min_runs
        ]
        if not include_low_performers:
            candidates = [r for r in candidates if not r.is_low_performer]
        return sorted(candidates, key=lambda r: r.effectiveness_score, reverse=True)

    def get_low_performers(self) -> List[AgentRecord]:
        """Return all agents flagged as low-performing.

        An agent is flagged when:
        - ``total_runs >= MIN_RUNS_FOR_FLAGGING``
        - ``effectiveness_score < LOW_PERFORMANCE_THRESHOLD``
        """
        return [r for r in self._records.values() if r.is_low_performer]

    def is_excluded(self, agent_name: str, strict: bool = False) -> bool:
        """Return True if *agent_name* should be excluded from a new review.

        In normal mode (``strict=False``) no agent is ever excluded — the
        low-performer flag is advisory only.  In strict mode, flagged agents
        are excluded unless they have fewer than ``MIN_RUNS_FOR_FLAGGING``
        runs (i.e. provisional score is always trusted).

        Args:
            agent_name: Agent to check.
            strict: When True, exclude confirmed low-performers.

        Returns:
            True if the agent should be skipped.
        """
        if not strict:
            return False
        record = self._records.get(agent_name)
        return record is not None and record.is_low_performer

    def format_report(self, top_n: int = 20, include_low_performers: bool = True) -> str:
        """Return a markdown-formatted ranked performance table.

        Args:
            top_n: Maximum rows to show.
            include_low_performers: When False, omit flagged agents.

        Returns:
            Markdown string ready to print or post as a comment.
        """
        ranked = self.rank_agents(include_low_performers=include_low_performers)[:top_n]

        if not ranked:
            return "*No agent performance data recorded yet.*\n"

        lines = [
            "## Agent Performance Report\n",
            f"*Top {min(top_n, len(ranked))} agents by effectiveness score "
            f"(threshold for flagging: score < {LOW_PERFORMANCE_THRESHOLD} "
            f"after ≥ {MIN_RUNS_FOR_FLAGGING} runs)*\n",
            "",
            "| Rank | Agent | Runs | Findings | Critical | Resolved | Dupes | Score | Flag |",
            "|------|-------|------|----------|----------|----------|-------|-------|------|",
        ]
        for rank, rec in enumerate(ranked, start=1):
            flag = "⚠️ LOW" if rec.is_low_performer else ""
            lines.append(
                f"| {rank} "
                f"| `{rec.agent_name}` "
                f"| {rec.total_runs} "
                f"| {rec.total_findings} "
                f"| {rec.critical_findings} "
                f"| {rec.findings_resolved} "
                f"| {rec.duplicate_findings} "
                f"| {rec.effectiveness_score:.3f} "
                f"| {flag} |"
            )
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> Dict[str, AgentRecord]:
        """Load records from disk; return empty dict if missing/corrupt."""
        if not self.store_path.exists():
            return {}
        try:
            raw: Dict[str, dict] = json.loads(
                self.store_path.read_text(encoding="utf-8")
            )
            return {
                name: AgentRecord.from_dict({**data, "agent_name": name})
                for name, data in raw.items()
            }
        except (json.JSONDecodeError, OSError, TypeError, KeyError) as exc:
            logger.warning(
                "Could not load performance store from %s (%s); starting fresh.",
                self.store_path, exc,
            )
            return {}

    def _save(self) -> None:
        """Atomically write records to disk."""
        payload = {
            name: {k: v for k, v in rec.to_dict().items() if k != "agent_name"}
            for name, rec in self._records.items()
        }
        tmp = self.store_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.store_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent_performance_tracker",
        description="View agent performance metrics (ORCH-010)",
    )
    action = parser.add_mutually_exclusive_group(required=False)
    action.add_argument(
        "--report",
        action="store_true",
        help="Print a performance report for all tracked agents",
    )
    action.add_argument(
        "--agent",
        metavar="AGENT_NAME",
        help="Show detailed stats for a specific agent",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        metavar="N",
        help="Limit report to top N agents (default: 20)",
    )
    parser.add_argument(
        "--no-low-performers",
        action="store_true",
        help="Exclude low-performing agents from the report",
    )
    parser.add_argument(
        "--store",
        metavar="PATH",
        help="Override performance store path",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point.  Returns exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if not args.report and not args.agent:
        parser.error("one of --report or --agent is required")

    store_path = Path(args.store) if args.store else None
    tracker = AgentPerformanceTracker(store_path=store_path)

    if args.agent:
        rec = tracker.get_record(args.agent)
        if rec is None:
            print(f"No data recorded for agent: {args.agent}")
            return 1
        print(f"\nAgent: {rec.agent_name}")
        print(f"  Total runs:          {rec.total_runs}")
        print(f"  Total findings:      {rec.total_findings}")
        print(f"  Critical findings:   {rec.critical_findings}")
        print(f"  Findings resolved:   {rec.findings_resolved}")
        print(f"  Duplicate findings:  {rec.duplicate_findings}")
        print(f"  Effectiveness score: {rec.effectiveness_score:.3f}")
        print(f"  Low performer:       {rec.is_low_performer}")
        print(f"  Last updated:        {rec.last_updated}")
        return 0

    # --report
    print(
        tracker.format_report(
            top_n=args.top,
            include_low_performers=not args.no_low_performers,
        )
    )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
