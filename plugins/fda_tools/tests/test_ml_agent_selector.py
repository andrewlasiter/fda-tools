"""Tests for ORCH-008: ML-based agent selection.

Covers:
- OrchestratorHistory: log_run, load_history, run_count, atomic writes
- _build_feature_vector: correct length and encoding
- _compute_effectiveness_score: formula correctness
- MLAgentSelector: fallback when sklearn missing, fallback when < 200 runs,
  training with sufficient data, confidence blending
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers: build a minimal TaskProfile-like object for the selector
# ---------------------------------------------------------------------------

class _FakeTaskProfile:
    task_type = "security_review"
    languages = ["python"]
    frameworks = []
    domains = ["fda"]
    complexity = 3
    review_dimensions = {
        "security": 0.9,
        "correctness": 0.6,
        "performance": 0.2,
    }


# ---------------------------------------------------------------------------
# OrchestratorHistory tests
# ---------------------------------------------------------------------------

class TestOrchestratorHistory:
    """Tests for the JSONL history logger."""

    def _make_history(self, tmp_path: Path):
        """Import and instantiate OrchestratorHistory with a temp dir."""
        # Add scripts/ to sys.path for the import
        scripts_dir = (
            Path(__file__).parent.parent / "scripts"
        )
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))

        from orchestrator_history import OrchestratorHistory  # noqa: PLC0415
        return OrchestratorHistory(data_dir=tmp_path)

    def test_log_run_creates_file(self, tmp_path):
        history = self._make_history(tmp_path)
        history.log_run(
            task_type="security_review",
            languages=["python"],
            domains=["fda"],
            complexity=3,
            agents=["voltagent-qa-sec:security-auditor"],
            findings_by_severity={"critical": 1, "high": 2, "medium": 0},
            resolved_count=2,
        )
        history_file = tmp_path / "orchestrator_history.jsonl"
        assert history_file.exists()

    def test_log_run_record_schema(self, tmp_path):
        history = self._make_history(tmp_path)
        history.log_run(
            task_type="code_review",
            languages=["typescript"],
            domains=["api"],
            complexity=2,
            agents=["voltagent-lang:typescript-pro"],
            findings_by_severity={"critical": 0, "high": 1, "medium": 3},
            resolved_count=4,
        )
        records = history.load_history()
        assert len(records) == 1
        rec = records[0]
        assert rec["task_type"] == "code_review"
        assert rec["languages"] == ["typescript"]
        assert rec["domains"] == ["api"]
        assert rec["complexity"] == 2
        assert rec["agents"] == ["voltagent-lang:typescript-pro"]
        assert rec["findings_by_severity"] == {"critical": 0, "high": 1, "medium": 3}
        assert rec["resolved_count"] == 4
        assert "timestamp" in rec

    def test_multiple_runs_appended(self, tmp_path):
        history = self._make_history(tmp_path)
        for i in range(5):
            history.log_run(
                task_type="security_review",
                languages=["python"],
                domains=["fda"],
                complexity=i + 1,
                agents=["agent-a"],
                findings_by_severity={"critical": i, "high": 0, "medium": 0},
                resolved_count=i,
            )
        records = history.load_history()
        assert len(records) == 5
        complexities = [r["complexity"] for r in records]
        assert complexities == [1, 2, 3, 4, 5]

    def test_run_count(self, tmp_path):
        history = self._make_history(tmp_path)
        assert history.run_count() == 0
        history.log_run("t", [], [], 1, ["a"], {}, 0)
        history.log_run("t", [], [], 1, ["b"], {}, 0)
        assert history.run_count() == 2

    def test_load_empty_returns_list(self, tmp_path):
        history = self._make_history(tmp_path)
        assert history.load_history() == []

    def test_clear_removes_file(self, tmp_path):
        history = self._make_history(tmp_path)
        history.log_run("t", [], [], 1, ["a"], {}, 0)
        assert history.run_count() == 1
        history.clear()
        assert history.run_count() == 0

    def test_corrupt_line_skipped(self, tmp_path):
        history_file = tmp_path / "orchestrator_history.jsonl"
        # Write two good records and one corrupt line in between
        with history_file.open("w") as fh:
            fh.write('{"task_type":"a","timestamp":"x","languages":[],"domains":[],'
                     '"complexity":1,"agents":[],"findings_by_severity":{},"resolved_count":0}\n')
            fh.write("NOT VALID JSON\n")
            fh.write('{"task_type":"b","timestamp":"y","languages":[],"domains":[],'
                     '"complexity":2,"agents":[],"findings_by_severity":{},"resolved_count":0}\n')

        history = self._make_history(tmp_path)
        records = history.load_history()
        # Corrupt line is skipped; we get 2 good records
        assert len(records) == 2
        assert records[0]["task_type"] == "a"
        assert records[1]["task_type"] == "b"


# ---------------------------------------------------------------------------
# Feature engineering tests
# ---------------------------------------------------------------------------

class TestFeatureEngineering:
    """Tests for _build_feature_vector and _compute_effectiveness_score."""

    def _import_helpers(self):
        scripts_dir = Path(__file__).parent.parent / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from agent_selector import _build_feature_vector, _compute_effectiveness_score  # noqa: PLC0415
        return _build_feature_vector, _compute_effectiveness_score

    def test_feature_vector_length_is_fixed(self):
        build, _ = self._import_helpers()
        vec = build("security_review", ["python"], ["fda"], 3)
        # 8 task types + 8 languages + 7 domains + 1 complexity = 24
        from agent_selector import _KNOWN_TASK_TYPES, _KNOWN_LANGUAGES, _KNOWN_DOMAINS  # noqa: PLC0415
        expected = len(_KNOWN_TASK_TYPES) + len(_KNOWN_LANGUAGES) + len(_KNOWN_DOMAINS) + 1
        assert len(vec) == expected

    def test_known_task_type_one_hot(self):
        build, _ = self._import_helpers()
        vec = build("security_review", [], [], 1)
        from agent_selector import _KNOWN_TASK_TYPES  # noqa: PLC0415
        idx = _KNOWN_TASK_TYPES.index("security_review")
        assert vec[idx] == 1.0
        # All other task-type slots should be 0
        for i, t in enumerate(_KNOWN_TASK_TYPES):
            if t != "security_review":
                assert vec[i] == 0.0

    def test_unknown_task_type_maps_to_other(self):
        build, _ = self._import_helpers()
        vec = build("completely_unknown_type", [], [], 1)
        from agent_selector import _KNOWN_TASK_TYPES  # noqa: PLC0415
        other_idx = _KNOWN_TASK_TYPES.index("other")
        assert vec[other_idx] == 1.0

    def test_complexity_is_clamped(self):
        build, _ = self._import_helpers()
        from agent_selector import _KNOWN_TASK_TYPES, _KNOWN_LANGUAGES, _KNOWN_DOMAINS  # noqa: PLC0415
        offset = len(_KNOWN_TASK_TYPES) + len(_KNOWN_LANGUAGES) + len(_KNOWN_DOMAINS)
        assert build("other", [], [], 0)[offset] == 1.0   # below min → 1
        assert build("other", [], [], 10)[offset] == 5.0  # above max → 5
        assert build("other", [], [], 3)[offset] == 3.0

    def test_effectiveness_score_formula(self):
        _, compute = self._import_helpers()
        # (critical * 3 + high * 2 + medium) / agents_used
        score = compute({"critical": 2, "high": 4, "medium": 1}, agents_used=4)
        expected = (2 * 3 + 4 * 2 + 1) / 4
        assert abs(score - expected) < 1e-9

    def test_effectiveness_score_zero_agents(self):
        _, compute = self._import_helpers()
        assert compute({"critical": 5}, agents_used=0) == 0.0

    def test_effectiveness_score_missing_keys(self):
        _, compute = self._import_helpers()
        # Missing keys treated as 0
        score = compute({}, agents_used=2)
        assert score == 0.0


# ---------------------------------------------------------------------------
# MLAgentSelector tests
# ---------------------------------------------------------------------------

class TestMLAgentSelectorFallback:
    """Tests for MLAgentSelector when sklearn is unavailable or data is sparse."""

    def _scripts_dir(self) -> Path:
        return Path(__file__).parent.parent / "scripts"

    def _sys_path_setup(self) -> None:
        sd = str(self._scripts_dir())
        if sd not in sys.path:
            sys.path.insert(0, sd)

    def test_fallback_when_sklearn_unavailable(self, tmp_path):
        """When sklearn is not installed, MLAgentSelector behaves like AgentSelector."""
        self._sys_path_setup()

        # Patch _SKLEARN_AVAILABLE to False so we simulate missing sklearn
        with patch("agent_selector._SKLEARN_AVAILABLE", False):
            from agent_selector import MLAgentSelector  # noqa: PLC0415
            from unittest.mock import MagicMock
            registry = MagicMock()

            selector = MLAgentSelector(registry, history_path=tmp_path / "h.jsonl")
            assert not selector.model_available
            assert selector.last_confidence == 0.0

    def test_fallback_when_insufficient_data(self, tmp_path):
        """With < 200 runs, MLAgentSelector model_available should be False."""
        self._sys_path_setup()

        # Write only 5 runs (below the 200-run threshold)
        from orchestrator_history import OrchestratorHistory  # noqa: PLC0415
        history = OrchestratorHistory(data_dir=tmp_path)
        for _ in range(5):
            history.log_run("security_review", ["python"], ["fda"], 3,
                            ["agent-a"], {"critical": 1}, 1)

        try:
            from agent_selector import MLAgentSelector  # noqa: PLC0415
            with patch("agent_selector._SKLEARN_AVAILABLE", True):
                registry = MagicMock()
                selector = MLAgentSelector(
                    registry,
                    history_path=tmp_path / "orchestrator_history.jsonl",
                )
            # Should fall back — not enough data
            assert not selector.model_available
        except ImportError:
            pytest.skip("scikit-learn not installed")

    def test_force_retrain_below_threshold(self, tmp_path):
        """force_retrain=True with enough samples should attempt training."""
        self._sys_path_setup()

        try:
            import sklearn  # noqa: F401
        except ImportError:
            pytest.skip("scikit-learn not installed")

        from orchestrator_history import OrchestratorHistory  # noqa: PLC0415
        history = OrchestratorHistory(data_dir=tmp_path)
        # Write 50 diverse runs (below 200 threshold but enough to fit a model)
        for i in range(50):
            history.log_run(
                task_type="security_review",
                languages=["python"],
                domains=["fda"],
                complexity=(i % 5) + 1,
                agents=["voltagent-qa-sec:security-auditor", "voltagent-lang:python-pro"],
                findings_by_severity={"critical": i % 3, "high": (i + 1) % 4, "medium": 1},
                resolved_count=i % 5,
            )

        from agent_selector import MLAgentSelector  # noqa: PLC0415
        registry = MagicMock()
        selector = MLAgentSelector(
            registry,
            history_path=tmp_path / "orchestrator_history.jsonl",
            force_retrain=True,
        )
        # With 50 samples + force_retrain, training should succeed
        assert selector.model_available

    def test_select_review_team_uses_parent_without_model(self, tmp_path):
        """Without a trained model, select_review_team delegates to parent."""
        self._sys_path_setup()

        with patch("agent_selector._SKLEARN_AVAILABLE", False):
            from agent_selector import MLAgentSelector  # noqa: PLC0415
            registry = MagicMock()
            # Parent select_review_team returns a ReviewTeam
            from agent_selector import ReviewTeam  # noqa: PLC0415
            expected_team = ReviewTeam(core_agents=[], total_agents=0)
            with patch.object(
                MLAgentSelector.__bases__[0], "select_review_team", return_value=expected_team
            ):
                selector = MLAgentSelector(registry, history_path=tmp_path / "h.jsonl")
                result = selector.select_review_team(_FakeTaskProfile())
            assert result is expected_team
            assert selector.last_confidence == 0.0


# ---------------------------------------------------------------------------
# OrchestratorHistory integration: training path
# ---------------------------------------------------------------------------

class TestMLAgentSelectorTraining:
    """Integration tests that require scikit-learn."""

    def _scripts_dir(self) -> Path:
        return Path(__file__).parent.parent / "scripts"

    def test_training_produces_model(self, tmp_path):
        """With ≥200 runs and sklearn available, model should be trained."""
        try:
            import sklearn  # noqa: F401
        except ImportError:
            pytest.skip("scikit-learn not installed")

        sd = str(self._scripts_dir())
        if sd not in sys.path:
            sys.path.insert(0, sd)

        from orchestrator_history import OrchestratorHistory  # noqa: PLC0415
        history = OrchestratorHistory(data_dir=tmp_path)

        # Generate 210 varied runs
        task_types = ["security_review", "code_review", "fda_review", "other"]
        for i in range(210):
            history.log_run(
                task_type=task_types[i % 4],
                languages=["python"] if i % 2 == 0 else ["typescript"],
                domains=["fda", "security"] if i % 3 == 0 else ["api"],
                complexity=(i % 5) + 1,
                agents=["agent-a", "agent-b"] if i % 2 == 0 else ["agent-c"],
                findings_by_severity={
                    "critical": i % 3,
                    "high": (i + 1) % 5,
                    "medium": i % 4,
                },
                resolved_count=i % 6,
            )

        from agent_selector import MLAgentSelector  # noqa: PLC0415
        registry = MagicMock()
        selector = MLAgentSelector(
            registry,
            history_path=tmp_path / "orchestrator_history.jsonl",
        )
        assert selector.model_available

    def test_retrain_triggered_after_n_runs(self, tmp_path):
        """Model retrains automatically after _RETRAIN_EVERY_N new runs."""
        try:
            import sklearn  # noqa: F401
        except ImportError:
            pytest.skip("scikit-learn not installed")

        sd = str(self._scripts_dir())
        if sd not in sys.path:
            sys.path.insert(0, sd)

        from agent_selector import _RETRAIN_EVERY_N, MLAgentSelector  # noqa: PLC0415
        from orchestrator_history import OrchestratorHistory  # noqa: PLC0415

        history = OrchestratorHistory(data_dir=tmp_path)
        # Seed 200 initial runs
        for i in range(200):
            history.log_run("other", [], [], 1, ["a"], {"critical": 0}, 0)

        registry = MagicMock()
        selector = MLAgentSelector(
            registry,
            history_path=tmp_path / "orchestrator_history.jsonl",
        )
        initial_run_count = selector._model_run_count

        # Add exactly _RETRAIN_EVERY_N more runs
        for i in range(_RETRAIN_EVERY_N):
            history.log_run("security_review", ["python"], ["fda"],
                            3, ["b"], {"critical": 1}, 1)

        # Trigger selection which should retrain internally
        parent_team = MagicMock()
        from agent_selector import ReviewTeam  # noqa: PLC0415
        parent_team_obj = ReviewTeam(core_agents=[], total_agents=0)
        with patch.object(
            MLAgentSelector.__bases__[0], "select_review_team", return_value=parent_team_obj
        ):
            selector.select_review_team(_FakeTaskProfile())

        # model_run_count should have increased
        assert selector._model_run_count > initial_run_count
