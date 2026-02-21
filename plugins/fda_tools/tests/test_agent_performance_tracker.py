"""Tests for AgentPerformanceTracker (FDA-214 / ORCH-010).

Coverage:
- effectiveness_score(): formula correctness, zero-run guard, clamp to [0,1]
- AgentRecord.recompute_score(): updates score + is_low_performer flag
- AgentPerformanceTracker.record_run(): counter increments, score update, disk write
- AgentPerformanceTracker.rank_agents(): sorted descending, min_runs filter,
  include_low_performers filter
- AgentPerformanceTracker.get_low_performers(): threshold logic
- AgentPerformanceTracker.is_excluded(): strict vs normal mode
- AgentPerformanceTracker.format_report(): markdown columns present, empty state
- State persistence: save/load round-trip, corruption handling, atomic write
"""

import json
import math
from pathlib import Path

import pytest

from fda_tools.scripts.agent_performance_tracker import (
    MIN_RUNS_FOR_FLAGGING,
    LOW_PERFORMANCE_THRESHOLD,
    FINDING_RATE_CAP,
    AgentRecord,
    AgentPerformanceTracker,
    effectiveness_score,
    main as tracker_main,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tracker(tmp_path: Path) -> AgentPerformanceTracker:
    """Return a tracker backed by a temp directory."""
    return AgentPerformanceTracker(store_path=tmp_path / "agent_performance.json")


def _record_n_runs(
    tracker: AgentPerformanceTracker,
    agent: str,
    n: int,
    findings: int = 5,
    critical: int = 2,
    resolved: int = 3,
    dupes: int = 0,
) -> None:
    """Add *n* identical runs for *agent*."""
    for _ in range(n):
        tracker.record_run(agent, findings, critical, resolved, dupes)


# ---------------------------------------------------------------------------
# effectiveness_score() formula tests
# ---------------------------------------------------------------------------


class TestEffectivenessScore:
    """Unit tests for the standalone effectiveness_score function."""

    def test_zero_runs_returns_zero(self):
        assert effectiveness_score(0, 0, 0, 0, 0) == 0.0

    def test_pure_findings_no_critical_no_resolution(self):
        # 10 findings / 1 run / cap=10 → finding_rate=1.0
        # 0 critical, 0 resolved, 0 dupes
        score = effectiveness_score(1, 10, 0, 0, 0)
        expected = 1.0 * 0.3 + 0.0 * 0.4 + 0.0 * 0.2 - 0.0 * 0.1
        assert math.isclose(score, expected, rel_tol=1e-9)

    def test_all_critical_all_resolved(self):
        # 1 run, 5 findings, 5 critical, 5 resolved, 0 dupes
        # finding_rate = min(5/10, 1) = 0.5
        # critical_hit = 1.0, resolution = 1.0, duplication = 0.0
        score = effectiveness_score(1, 5, 5, 5, 0)
        expected = 0.5 * 0.3 + 1.0 * 0.4 + 1.0 * 0.2 - 0.0
        assert math.isclose(score, expected, rel_tol=1e-9)

    def test_duplication_penalty_reduces_score(self):
        score_no_dupe = effectiveness_score(1, 5, 5, 5, 0)
        score_with_dupe = effectiveness_score(1, 5, 5, 5, 5)
        assert score_with_dupe < score_no_dupe

    def test_score_clamped_to_zero_minimum(self):
        # All duplicates, no resolutions: duplication penalty can't push below 0
        score = effectiveness_score(1, 100, 0, 0, 100)
        assert score >= 0.0

    def test_score_clamped_to_one_maximum(self):
        # Unrealistically good: cap finding rate, all critical, all resolved
        score = effectiveness_score(1, 1000, 1000, 1000, 0)
        assert score <= 1.0

    def test_finding_rate_capped_at_one(self):
        # 100 findings / 1 run / cap=10 → rate should be capped to 1.0, not 10.0
        score_overflow = effectiveness_score(1, 100, 0, 0, 0)
        score_cap = effectiveness_score(1, 10, 0, 0, 0)
        assert math.isclose(score_overflow, score_cap, rel_tol=1e-9)

    def test_no_findings_no_criticals(self):
        # Agent ran but found nothing: finding_rate=0, all rates=0
        score = effectiveness_score(5, 0, 0, 0, 0)
        assert score == 0.0


# ---------------------------------------------------------------------------
# AgentRecord
# ---------------------------------------------------------------------------


class TestAgentRecord:
    """Tests for AgentRecord dataclass methods."""

    def test_recompute_score_sets_effectiveness(self):
        rec = AgentRecord(
            agent_name="my-agent",
            total_runs=1,
            total_findings=5,
            critical_findings=5,
            findings_resolved=5,
            duplicate_findings=0,
        )
        rec.recompute_score()
        assert rec.effectiveness_score > 0.0

    def test_low_performer_flagged_after_min_runs(self):
        rec = AgentRecord(
            agent_name="bad-agent",
            total_runs=MIN_RUNS_FOR_FLAGGING,
            total_findings=0,
            critical_findings=0,
            findings_resolved=0,
            duplicate_findings=0,
        )
        rec.recompute_score()
        assert rec.is_low_performer

    def test_low_performer_not_flagged_below_min_runs(self):
        rec = AgentRecord(
            agent_name="new-agent",
            total_runs=MIN_RUNS_FOR_FLAGGING - 1,
            total_findings=0,
        )
        rec.recompute_score()
        assert not rec.is_low_performer

    def test_good_performer_not_flagged(self):
        rec = AgentRecord(
            agent_name="good-agent",
            total_runs=MIN_RUNS_FOR_FLAGGING,
            total_findings=50,
            critical_findings=30,
            findings_resolved=40,
            duplicate_findings=2,
        )
        rec.recompute_score()
        assert not rec.is_low_performer

    def test_round_trip_serialisation(self):
        rec = AgentRecord(
            agent_name="test-agent",
            total_runs=10,
            total_findings=20,
            effectiveness_score=0.55,
        )
        d = rec.to_dict()
        rec2 = AgentRecord.from_dict(d)
        assert rec2.agent_name == rec.agent_name
        assert rec2.total_runs == rec.total_runs
        assert rec2.effectiveness_score == rec.effectiveness_score

    def test_from_dict_ignores_unknown_keys(self):
        d = {"agent_name": "x", "total_runs": 3, "future_field": "ignored"}
        rec = AgentRecord.from_dict(d)
        assert rec.total_runs == 3


# ---------------------------------------------------------------------------
# AgentPerformanceTracker.record_run
# ---------------------------------------------------------------------------


class TestRecordRun:
    """Tests for tracking individual review runs."""

    def test_first_run_creates_record(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        rec = tracker.record_run("agent-a", findings=3)
        assert rec.total_runs == 1
        assert rec.total_findings == 3

    def test_counters_accumulate_across_runs(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        tracker.record_run("agent-a", findings=3, critical_findings=1)
        tracker.record_run("agent-a", findings=5, critical_findings=2)
        rec = tracker.get_record("agent-a")
        assert rec.total_runs == 2
        assert rec.total_findings == 8
        assert rec.critical_findings == 3

    def test_score_recomputed_after_each_run(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        r1 = tracker.record_run("agent-b", findings=0)
        # Capture the score before the second run mutates the same record object.
        score_after_run1 = r1.effectiveness_score
        tracker.record_run("agent-b", findings=10, critical_findings=5, findings_resolved=8)
        rec = tracker.get_record("agent-b")
        assert rec.effectiveness_score > score_after_run1

    def test_last_updated_set_to_today(self, tmp_path):
        from datetime import date
        tracker = _make_tracker(tmp_path)
        rec = tracker.record_run("agent-c", findings=1)
        assert rec.last_updated == date.today().isoformat()

    def test_record_persisted_to_disk(self, tmp_path):
        store = tmp_path / "agent_performance.json"
        tracker = AgentPerformanceTracker(store_path=store)
        tracker.record_run("agent-d", findings=2)
        assert store.exists()
        data = json.loads(store.read_text())
        assert "agent-d" in data


# ---------------------------------------------------------------------------
# rank_agents
# ---------------------------------------------------------------------------


class TestRankAgents:
    """Tests for agent ranking."""

    def test_sorted_by_effectiveness_descending(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        # Good agent: many critical findings resolved
        _record_n_runs(tracker, "good", 5, findings=10, critical=8, resolved=9, dupes=0)
        # Bad agent: finds nothing
        _record_n_runs(tracker, "bad", 5, findings=0, critical=0, resolved=0, dupes=0)
        ranked = tracker.rank_agents()
        assert ranked[0].agent_name == "good"
        assert ranked[-1].agent_name == "bad"

    def test_min_runs_filter(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        _record_n_runs(tracker, "veteran", 10, findings=5)
        _record_n_runs(tracker, "newbie", 1, findings=5)
        ranked = tracker.rank_agents(min_runs=5)
        names = [r.agent_name for r in ranked]
        assert "veteran" in names
        assert "newbie" not in names

    def test_exclude_low_performers(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        # Low performer: 20+ runs, 0 findings
        _record_n_runs(tracker, "loser", MIN_RUNS_FOR_FLAGGING, findings=0)
        _record_n_runs(tracker, "winner", MIN_RUNS_FOR_FLAGGING, findings=10, critical=5, resolved=8)
        ranked = tracker.rank_agents(include_low_performers=False)
        names = [r.agent_name for r in ranked]
        assert "loser" not in names
        assert "winner" in names

    def test_empty_store_returns_empty_list(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        assert tracker.rank_agents() == []


# ---------------------------------------------------------------------------
# get_low_performers / is_excluded
# ---------------------------------------------------------------------------


class TestLowPerformers:
    """Tests for low-performance flagging and exclusion."""

    def test_flagged_after_min_runs_with_low_score(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        _record_n_runs(tracker, "slacker", MIN_RUNS_FOR_FLAGGING, findings=0)
        lp = tracker.get_low_performers()
        assert any(r.agent_name == "slacker" for r in lp)

    def test_not_flagged_below_min_runs(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        _record_n_runs(tracker, "rookie", MIN_RUNS_FOR_FLAGGING - 1, findings=0)
        lp = tracker.get_low_performers()
        assert not any(r.agent_name == "rookie" for r in lp)

    def test_not_flagged_with_high_score(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        _record_n_runs(tracker, "star", MIN_RUNS_FOR_FLAGGING, findings=10, critical=8, resolved=9)
        lp = tracker.get_low_performers()
        assert not any(r.agent_name == "star" for r in lp)

    def test_is_excluded_strict_excludes_low_performer(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        _record_n_runs(tracker, "slow", MIN_RUNS_FOR_FLAGGING, findings=0)
        assert tracker.is_excluded("slow", strict=True)

    def test_is_excluded_non_strict_never_excludes(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        _record_n_runs(tracker, "slow", MIN_RUNS_FOR_FLAGGING, findings=0)
        assert not tracker.is_excluded("slow", strict=False)

    def test_is_excluded_unknown_agent_returns_false(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        assert not tracker.is_excluded("unknown-agent", strict=True)


# ---------------------------------------------------------------------------
# format_report
# ---------------------------------------------------------------------------


class TestFormatReport:
    """Tests for the markdown report renderer."""

    def test_empty_store_returns_placeholder(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        report = tracker.format_report()
        assert "No agent performance data" in report

    def test_report_contains_agent_name(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        tracker.record_run("my-agent", findings=5, critical_findings=2, findings_resolved=4)
        report = tracker.format_report()
        assert "my-agent" in report

    def test_report_contains_table_headers(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        tracker.record_run("agent-x", findings=1)
        report = tracker.format_report()
        assert "Rank" in report
        assert "Score" in report

    def test_report_top_n_limits_rows(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        for i in range(10):
            tracker.record_run(f"agent-{i}", findings=i)
        report = tracker.format_report(top_n=3)
        # Should have at most 3 data rows (plus header rows)
        data_lines = [l for l in report.splitlines() if l.startswith("| ") and "Rank" not in l and "---" not in l]
        assert len(data_lines) <= 3

    def test_low_performer_flagged_in_report(self, tmp_path):
        tracker = _make_tracker(tmp_path)
        _record_n_runs(tracker, "weak-agent", MIN_RUNS_FOR_FLAGGING, findings=0)
        report = tracker.format_report()
        assert "LOW" in report or "⚠" in report


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------


class TestStatePersistence:
    """Tests for JSON load/save round-trip."""

    def test_records_survive_reload(self, tmp_path):
        store = tmp_path / "perf.json"
        t1 = AgentPerformanceTracker(store_path=store)
        t1.record_run("persistent-agent", findings=7, critical_findings=3)

        t2 = AgentPerformanceTracker(store_path=store)
        rec = t2.get_record("persistent-agent")
        assert rec is not None
        assert rec.total_findings == 7
        assert rec.critical_findings == 3

    def test_corrupted_file_returns_empty(self, tmp_path):
        store = tmp_path / "perf.json"
        store.write_text("not json", encoding="utf-8")
        tracker = AgentPerformanceTracker(store_path=store)
        assert tracker.rank_agents() == []

    def test_atomic_write_no_tmp_file_left(self, tmp_path):
        store = tmp_path / "perf.json"
        tracker = AgentPerformanceTracker(store_path=store)
        tracker.record_run("x", findings=1)
        tmp = store.with_suffix(".tmp")
        assert not tmp.exists()

    def test_agent_name_not_stored_as_key_in_record_dict(self, tmp_path):
        """agent_name should be the JSON key, not duplicated inside the value dict."""
        store = tmp_path / "perf.json"
        tracker = AgentPerformanceTracker(store_path=store)
        tracker.record_run("my-agent", findings=2)
        data = json.loads(store.read_text())
        assert "my-agent" in data
        assert "agent_name" not in data["my-agent"]


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class TestCLI:
    """Tests for the agent_performance_tracker CLI (--report / --agent)."""

    def test_report_empty_store(self, tmp_path, capsys):
        store = tmp_path / "perf.json"
        rc = tracker_main(["--report", "--store", str(store)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "No agent performance data" in out

    def test_report_with_data(self, tmp_path, capsys):
        store = tmp_path / "perf.json"
        t = AgentPerformanceTracker(store_path=store)
        t.record_run("agent-a", findings=5, critical_findings=2, findings_resolved=4)
        rc = tracker_main(["--report", "--store", str(store)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "agent-a" in out
        assert "Score" in out

    def test_agent_flag_known_agent(self, tmp_path, capsys):
        store = tmp_path / "perf.json"
        t = AgentPerformanceTracker(store_path=store)
        t.record_run("my-agent", findings=3)
        rc = tracker_main(["--agent", "my-agent", "--store", str(store)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "my-agent" in out
        assert "Total runs" in out

    def test_agent_flag_unknown_agent(self, tmp_path, capsys):
        store = tmp_path / "perf.json"
        rc = tracker_main(["--agent", "ghost-agent", "--store", str(store)])
        assert rc == 1
        out = capsys.readouterr().out
        assert "No data" in out

    def test_no_action_exits_with_error(self, tmp_path):
        import pytest
        store = tmp_path / "perf.json"
        with pytest.raises(SystemExit) as exc_info:
            tracker_main(["--store", str(store)])
        assert exc_info.value.code != 0

    def test_report_top_n_flag(self, tmp_path, capsys):
        store = tmp_path / "perf.json"
        t = AgentPerformanceTracker(store_path=store)
        for i in range(5):
            t.record_run(f"agent-{i}", findings=i + 1)
        rc = tracker_main(["--report", "--top", "2", "--store", str(store)])
        assert rc == 0
        out = capsys.readouterr().out
        # At most 2 data rows (header rows + separator excluded)
        data_rows = [
            line for line in out.splitlines()
            if line.startswith("| ") and "Rank" not in line and "---" not in line
        ]
        assert len(data_rows) <= 2

    def test_no_low_performers_flag_excludes_them(self, tmp_path, capsys):
        store = tmp_path / "perf.json"
        t = AgentPerformanceTracker(store_path=store)
        _record_n_runs(t, "weak", MIN_RUNS_FOR_FLAGGING, findings=0)
        _record_n_runs(t, "strong", MIN_RUNS_FOR_FLAGGING, findings=10, critical=8, resolved=9)
        rc = tracker_main(["--report", "--no-low-performers", "--store", str(store)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "weak" not in out
        assert "strong" in out


# ---------------------------------------------------------------------------
# AgentSelector integration tests
# ---------------------------------------------------------------------------


class TestAgentSelectorIntegration:
    """Tests for AgentSelector performance-weighted ranking."""

    @staticmethod
    def _make_mock_agent(name: str, model: str = "sonnet") -> dict:
        return {
            "name": name,
            "model": model,
            "selection_reason": "dimension",
            "dimension_score": 0.8,
            "matched_dimension": "code_quality",
        }

    @staticmethod
    def _make_mock_registry():
        """Return a minimal mock registry (no real lookups needed)."""
        class _MockRegistry:
            def find_agents_by_review_dimension(self, dim):
                return []
            def find_agents_by_language(self, lang):
                return []
            def search_universal_agents(self, **kw):
                return []
        return _MockRegistry()

    @staticmethod
    def _make_mock_task_profile(languages=None, domains=None):
        return type("_MockProfile", (), {
            "task_type": "code_review",
            "complexity": 3,
            "review_dimensions": {"code_quality": 0.9},
            "languages": languages or [],
            "domains": domains or [],
        })()

    def test_no_tracker_ranks_normally(self, tmp_path):
        """AgentSelector without tracker still ranks agents."""
        from fda_tools.scripts.agent_selector import AgentSelector
        registry = self._make_mock_registry()
        selector = AgentSelector(registry)
        agents = [
            self._make_mock_agent("agent-a"),
            self._make_mock_agent("agent-b"),
        ]
        profile = self._make_mock_task_profile()
        ranked = selector._rank_agents(agents, profile)
        assert len(ranked) == 2

    def test_high_performer_ranked_above_neutral(self, tmp_path):
        """Agent with high effectiveness score ranks above untracked agent."""
        from fda_tools.scripts.agent_selector import AgentSelector
        store = tmp_path / "perf.json"
        tracker = AgentPerformanceTracker(store_path=store)
        # Make "star-agent" a high performer
        _record_n_runs(
            tracker, "star-agent",
            MIN_RUNS_FOR_FLAGGING,
            findings=10, critical=8, resolved=9, dupes=0,
        )

        registry = self._make_mock_registry()
        selector = AgentSelector(registry, tracker=tracker)

        # Both agents have identical static scores
        agents = [
            {**self._make_mock_agent("unknown-agent"), "dimension_score": 0.8},
            {**self._make_mock_agent("star-agent"), "dimension_score": 0.8},
        ]
        profile = self._make_mock_task_profile()
        ranked = selector._rank_agents(agents, profile)
        ranked_names = [a["name"] for a in ranked]
        assert ranked_names[0] == "star-agent"

    def test_low_performer_ranked_below_neutral(self, tmp_path):
        """Low-performing agent (score < threshold) is ranked below untracked agents."""
        from fda_tools.scripts.agent_selector import AgentSelector
        store = tmp_path / "perf.json"
        tracker = AgentPerformanceTracker(store_path=store)
        # Make "weak-agent" a low performer
        _record_n_runs(
            tracker, "weak-agent",
            MIN_RUNS_FOR_FLAGGING,
            findings=0, critical=0, resolved=0, dupes=0,
        )

        registry = self._make_mock_registry()
        selector = AgentSelector(registry, tracker=tracker)

        agents = [
            {**self._make_mock_agent("unknown-agent"), "dimension_score": 0.8},
            {**self._make_mock_agent("weak-agent"), "dimension_score": 0.8},
        ]
        profile = self._make_mock_task_profile()
        ranked = selector._rank_agents(agents, profile)
        ranked_names = [a["name"] for a in ranked]
        assert ranked_names[-1] == "weak-agent"

    def test_tracker_attribute_accessible(self):
        """AgentSelector exposes tracker attribute."""
        from fda_tools.scripts.agent_selector import AgentSelector
        registry = self._make_mock_registry()
        tracker = AgentPerformanceTracker()
        selector = AgentSelector(registry, tracker=tracker)
        assert selector.tracker is tracker

    def test_tracker_none_by_default(self):
        """AgentSelector tracker defaults to None."""
        from fda_tools.scripts.agent_selector import AgentSelector
        registry = self._make_mock_registry()
        selector = AgentSelector(registry)
        assert selector.tracker is None
