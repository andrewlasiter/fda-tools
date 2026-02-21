"""
Unit tests for PostMarketSurveillance (FDA-119).

All API calls are mocked — no live network access required.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from fda_tools.lib.post_market_surveillance import (
    PostMarketSurveillance,
    _maude_safety_score,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(events=None, recalls=None):
    """Return a mock FDAClient with configurable responses."""
    client = MagicMock()
    client.get_events.return_value = {"results": events or []}
    client.get_recalls.return_value = {"results": recalls or []}
    return client


def _event(year: int) -> dict:
    """Build a minimal MAUDE event dict for a given year."""
    return {"date_of_event": f"{year}0601", "event_type": "malfunction"}


def _recall(firm: str = "Acme", reason: str = "Contamination") -> dict:
    return {"recalling_firm": firm, "reason_for_recall": reason}


# ---------------------------------------------------------------------------
# 1. _maude_safety_score helper
# ---------------------------------------------------------------------------


class TestMaudeSafetyScore:
    def test_zero_events_is_perfect(self):
        assert _maude_safety_score(0) == 10

    def test_up_to_10_per_year_is_7(self):
        assert _maude_safety_score(5) == 7
        assert _maude_safety_score(10) == 7

    def test_up_to_50_per_year_is_4(self):
        assert _maude_safety_score(25) == 4
        assert _maude_safety_score(50) == 4

    def test_up_to_100_per_year_is_2(self):
        assert _maude_safety_score(75) == 2
        assert _maude_safety_score(100) == 2

    def test_over_100_per_year_is_zero(self):
        assert _maude_safety_score(101) == 0
        assert _maude_safety_score(500) == 0


# ---------------------------------------------------------------------------
# 2. calculate_maude_risk_score
# ---------------------------------------------------------------------------


class TestCalculateMaudeRiskScore:
    def setup_method(self):
        self.pms = PostMarketSurveillance(_make_client())

    def test_delegates_to_helper(self):
        assert self.pms.calculate_maude_risk_score(0) == 10
        assert self.pms.calculate_maude_risk_score(200) == 0

    def test_boundary_at_10(self):
        assert self.pms.calculate_maude_risk_score(10) == 7
        assert self.pms.calculate_maude_risk_score(11) == 4


# ---------------------------------------------------------------------------
# 3. analyze_trends
# ---------------------------------------------------------------------------


class TestAnalyzeTrends:
    def test_empty_response_returns_defaults(self):
        client = _make_client(events=[])
        pms = PostMarketSurveillance(client)
        result = pms.analyze_trends("DQY")
        assert result["total_events"] == 0
        assert result["trend"] == "STABLE"
        assert result["events_per_year"] == 0.0
        assert result["yoy_change"] is None

    def test_none_response_returns_defaults(self):
        client = MagicMock()
        client.get_events.return_value = None
        client.get_recalls.return_value = {"results": []}
        pms = PostMarketSurveillance(client)
        result = pms.analyze_trends("DQY")
        assert result["total_events"] == 0

    def test_events_bucketed_by_year(self):
        current_year = datetime.now().year
        events = [_event(current_year), _event(current_year), _event(current_year - 1)]
        client = _make_client(events=events)
        pms = PostMarketSurveillance(client)
        result = pms.analyze_trends("DQY", years=5)
        assert result["events_by_year"].get(current_year) == 2
        assert result["events_by_year"].get(current_year - 1) == 1

    def test_events_per_year_calculation(self):
        current_year = datetime.now().year
        events = [_event(current_year) for _ in range(10)]
        client = _make_client(events=events)
        pms = PostMarketSurveillance(client)
        result = pms.analyze_trends("DQY", years=5)
        assert result["total_events"] == 10
        assert result["events_per_year"] == 2.0  # 10 / 5

    def test_trend_increasing(self):
        current_year = datetime.now().year
        # 10 events last year, 20 this year → +100% YoY → INCREASING
        events = [_event(current_year - 1)] * 10 + [_event(current_year)] * 20
        client = _make_client(events=events)
        pms = PostMarketSurveillance(client)
        result = pms.analyze_trends("DQY", years=5)
        assert result["trend"] == "INCREASING"
        assert result["yoy_change"] == pytest.approx(1.0, abs=0.01)

    def test_trend_decreasing(self):
        current_year = datetime.now().year
        # 20 events prior year, 5 this year → -75% YoY → DECREASING
        events = [_event(current_year - 1)] * 20 + [_event(current_year)] * 5
        client = _make_client(events=events)
        pms = PostMarketSurveillance(client)
        result = pms.analyze_trends("DQY", years=5)
        assert result["trend"] == "DECREASING"

    def test_trend_stable(self):
        current_year = datetime.now().year
        # 10 last year, 11 this year → +10% → STABLE
        events = [_event(current_year - 1)] * 10 + [_event(current_year)] * 11
        client = _make_client(events=events)
        pms = PostMarketSurveillance(client)
        result = pms.analyze_trends("DQY", years=5)
        assert result["trend"] == "STABLE"

    def test_old_events_excluded(self):
        # Events 10 years ago should be excluded with years=5
        old_year = datetime.now().year - 10
        events = [_event(old_year) for _ in range(50)]
        client = _make_client(events=events)
        pms = PostMarketSurveillance(client)
        result = pms.analyze_trends("DQY", years=5)
        assert result["total_events"] == 0


# ---------------------------------------------------------------------------
# 4. get_predicate_risk_data
# ---------------------------------------------------------------------------


class TestGetPredicateRiskData:
    def test_empty_input_returns_empty(self):
        pms = PostMarketSurveillance(_make_client())
        assert pms.get_predicate_risk_data([]) == {}

    def test_returns_entry_per_k_number(self):
        client = _make_client(events=[], recalls=[])
        pms = PostMarketSurveillance(client)
        result = pms.get_predicate_risk_data(["K001", "K002"], product_code="DQY")
        assert "K001" in result
        assert "K002" in result

    def test_risk_data_keys_present(self):
        client = _make_client(events=[], recalls=[])
        pms = PostMarketSurveillance(client)
        result = pms.get_predicate_risk_data(["K001"], product_code="DQY")
        entry = result["K001"]
        assert "maude_events_per_year" in entry
        assert "maude_safety_score" in entry
        assert "recall_count" in entry
        assert "recall_score" in entry
        assert "combined_risk_score" in entry
        assert "risk_level" in entry

    def test_zero_recalls_max_recall_score(self):
        client = _make_client(events=[], recalls=[])
        pms = PostMarketSurveillance(client)
        result = pms.get_predicate_risk_data(["K001"], product_code="DQY")
        assert result["K001"]["recall_score"] == 10
        assert result["K001"]["recall_count"] == 0

    def test_recall_count_reduces_score(self):
        client = _make_client(events=[], recalls=[_recall(), _recall()])
        pms = PostMarketSurveillance(client)
        result = pms.get_predicate_risk_data(["K001"], product_code="DQY")
        # 10 - 2 recalls * 5 = 0
        assert result["K001"]["recall_score"] == 0
        assert result["K001"]["recall_count"] == 2

    def test_recall_score_floor_is_zero(self):
        client = _make_client(events=[], recalls=[_recall()] * 5)
        pms = PostMarketSurveillance(client)
        result = pms.get_predicate_risk_data(["K001"], product_code="DQY")
        assert result["K001"]["recall_score"] == 0  # never negative

    def test_low_risk_level_when_no_issues(self):
        client = _make_client(events=[], recalls=[])
        pms = PostMarketSurveillance(client)
        result = pms.get_predicate_risk_data(["K001"], product_code="DQY")
        assert result["K001"]["risk_level"] == "LOW"

    def test_critical_risk_level_with_many_events_and_recalls(self):
        current_year = datetime.now().year
        # 600 events / 5yr = 120/yr → maude_safety_score = 0
        many_events = [_event(current_year) for _ in range(100)]
        many_recalls = [_recall() for _ in range(3)]
        client = _make_client(events=many_events, recalls=many_recalls)
        pms = PostMarketSurveillance(client)
        result = pms.get_predicate_risk_data(["K001"], product_code="DQY")
        # combined = 0 + max(0, 10-15) = 0 → CRITICAL
        assert result["K001"]["risk_level"] == "CRITICAL"


# ---------------------------------------------------------------------------
# 5. generate_safety_report
# ---------------------------------------------------------------------------


class TestGenerateSafetyReport:
    def test_report_is_string(self):
        pms = PostMarketSurveillance(_make_client())
        report = pms.generate_safety_report("DQY")
        assert isinstance(report, str)

    def test_report_contains_product_code(self):
        pms = PostMarketSurveillance(_make_client())
        report = pms.generate_safety_report("DQY")
        assert "DQY" in report

    def test_report_contains_required_sections(self):
        pms = PostMarketSurveillance(_make_client())
        report = pms.generate_safety_report("DQY")
        assert "## Summary" in report
        assert "Risk Level" in report
        assert "Disclaimer" in report

    def test_report_shows_recall_details(self):
        recalls = [_recall("MedCo Inc", "Contaminated batch")]
        client = _make_client(recalls=recalls)
        pms = PostMarketSurveillance(client)
        report = pms.generate_safety_report("DQY")
        assert "MedCo Inc" in report

    def test_report_no_recall_message_when_empty(self):
        pms = PostMarketSurveillance(_make_client())
        report = pms.generate_safety_report("DQY")
        assert "No recalls found" in report

    def test_report_includes_events_by_year(self):
        current_year = datetime.now().year
        events = [_event(current_year)] * 3
        client = _make_client(events=events)
        pms = PostMarketSurveillance(client)
        report = pms.generate_safety_report("DQY")
        assert "## MAUDE Events by Year" in report
        assert str(current_year) in report


# ---------------------------------------------------------------------------
# 6. get_dashboard_summary
# ---------------------------------------------------------------------------


class TestGetDashboardSummary:
    def test_returns_required_keys(self):
        pms = PostMarketSurveillance(_make_client())
        summary = pms.get_dashboard_summary("DQY")
        for key in ("product_code", "total_events", "events_per_year", "trend",
                    "recall_count", "maude_safety_score", "risk_level"):
            assert key in summary, f"Missing key: {key}"

    def test_product_code_matches(self):
        pms = PostMarketSurveillance(_make_client())
        summary = pms.get_dashboard_summary("DQY")
        assert summary["product_code"] == "DQY"


# ---------------------------------------------------------------------------
# 7. predicate_ranker integration (FDA-119 MAUDE score feeds _estimate_confidence_score)
# ---------------------------------------------------------------------------


class TestPredicateRankerMaudeIntegration:
    """Verify predicate_ranker applies MAUDE scoring from FDA-119."""

    def _make_ranker(self, tmpdir):
        import json
        from pathlib import Path
        from fda_tools.lib.predicate_ranker import PredicateRanker

        project_dir = Path(str(tmpdir))
        # Minimal device_profile
        (project_dir / "device_profile.json").write_text(
            json.dumps({"product_code": "DQY", "indications_for_use": "cardiac monitoring"})
        )
        # review.json with two predicates — one clean, one high-MAUDE
        (project_dir / "review.json").write_text(
            json.dumps({
                "accepted_predicates": [
                    {
                        "k_number": "K111111",
                        "device_name": "Clean Device",
                        "product_code": "DQY",
                        "decision_date": "20220101",
                        "confidence_score": 70,
                        "maude_productcode_5y": 0,    # 0 events → maude_score 10
                        "recalls_total": 0,
                    },
                    {
                        "k_number": "K222222",
                        "device_name": "High MAUDE Device",
                        "product_code": "DQY",
                        "decision_date": "20220101",
                        "confidence_score": 70,
                        "maude_productcode_5y": 600,  # 120/yr → maude_score 0
                        "recalls_total": 0,
                    },
                ]
            })
        )
        return PredicateRanker(str(project_dir))

    def test_high_maude_device_scores_lower(self, tmp_path):
        ranker = self._make_ranker(tmp_path)
        ranked = ranker.rank_predicates(top_n=10)
        k_numbers = [p["k_number"] for p in ranked]
        assert "K111111" in k_numbers
        assert "K222222" in k_numbers
        # Clean device should rank higher than high-MAUDE device
        clean_idx = k_numbers.index("K111111")
        maude_idx = k_numbers.index("K222222")
        assert clean_idx < maude_idx

    def test_high_maude_flag_threshold(self, tmp_path):
        ranker = self._make_ranker(tmp_path)
        ranked = ranker.rank_predicates(top_n=10)
        high_maude = next(p for p in ranked if p["k_number"] == "K222222")
        # 120/yr > 10/yr threshold → HIGH_MAUDE flag
        assert any("HIGH_MAUDE" in f for f in high_maude["risk_flags"])

    def test_zero_maude_no_flag(self, tmp_path):
        ranker = self._make_ranker(tmp_path)
        ranked = ranker.rank_predicates(top_n=10)
        clean = next(p for p in ranked if p["k_number"] == "K111111")
        assert not any("HIGH_MAUDE" in f for f in clean["risk_flags"])
