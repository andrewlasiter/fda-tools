"""
Sprint 18 — Cosine Search API + CUSUM Signal Detection
=======================================================
Tests for:
  - plugins/fda_tools/lib/guidance_search.py   (FDA-233 / GD-003)
  - plugins/fda_tools/lib/signal_cusum.py      (SIG-002)

No real Supabase connection or sentence-transformer model required.
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fda_tools.lib.guidance_search import (
    GuidanceSearchClient,
    GuidanceSearchResult,
    _parse_result,
    search_guidance,
)
from fda_tools.lib.signal_cusum import (
    CusumDetector,
    CusumPoint,
    CusumSummary,
    auto_target,
    run_cusum,
    threshold_for_arl,
)
from fda_tools.lib.guidance_embedder import EMBEDDING_DIM


# ══════════════════════════════════════════════════════════════════════════════
#  GuidanceSearchResult
# ══════════════════════════════════════════════════════════════════════════════

class TestGuidanceSearchResult(unittest.TestCase):

    def _make(self, **kw) -> GuidanceSearchResult:
        defaults = dict(
            content="Risk management per ISO 14971.",
            similarity=0.87,
            doc_id="ucm001",
            title="Design Controls",
            section="4.1",
            chunk_index=3,
            metadata={"doc_id": "ucm001", "year": 2023},
            row_id=42,
        )
        defaults.update(kw)
        return GuidanceSearchResult(**defaults)

    def test_frozen_immutable(self) -> None:
        r = self._make()
        with self.assertRaises(Exception):
            r.similarity = 0.5  # type: ignore[misc]

    def test_as_dict_keys(self) -> None:
        r = self._make()
        d = r.as_dict()
        for key in ("row_id", "doc_id", "title", "section", "chunk_index",
                    "similarity", "content", "metadata"):
            self.assertIn(key, d)

    def test_as_dict_similarity_rounded(self) -> None:
        r = self._make(similarity=0.876543)
        self.assertEqual(r.as_dict()["similarity"], 0.8765)

    def test_default_values(self) -> None:
        r = GuidanceSearchResult(content="text", similarity=0.9)
        self.assertEqual(r.doc_id, "")
        self.assertEqual(r.row_id, None)
        self.assertEqual(r.metadata, {})


# ══════════════════════════════════════════════════════════════════════════════
#  _parse_result
# ══════════════════════════════════════════════════════════════════════════════

class TestParseResult(unittest.TestCase):

    def test_parses_full_row(self) -> None:
        row = {
            "id": 7,
            "content": "FDA guidance text.",
            "similarity": 0.91,
            "metadata": {
                "doc_id": "ucm999",
                "title": "Software Guidance",
                "section": "3.2",
                "chunk_index": 5,
            },
        }
        r = _parse_result(row)
        self.assertEqual(r.row_id, 7)
        self.assertEqual(r.doc_id, "ucm999")
        self.assertAlmostEqual(r.similarity, 0.91)
        self.assertEqual(r.section, "3.2")
        self.assertEqual(r.chunk_index, 5)

    def test_parses_minimal_row(self) -> None:
        r = _parse_result({"content": "text", "similarity": 0.5})
        self.assertEqual(r.content, "text")
        self.assertAlmostEqual(r.similarity, 0.5)
        self.assertEqual(r.doc_id, "")

    def test_missing_metadata_defaults(self) -> None:
        r = _parse_result({"content": "t", "similarity": 0.6, "metadata": None})
        self.assertEqual(r.metadata, {})


# ══════════════════════════════════════════════════════════════════════════════
#  GuidanceSearchClient
# ══════════════════════════════════════════════════════════════════════════════

def _mock_supabase(rows: list) -> MagicMock:
    """Build a mock SupabaseClient whose vector_search returns *rows*."""
    mc = MagicMock()
    mock_response = MagicMock()
    mock_response.data = rows
    mc.vector_search.return_value.execute.return_value = mock_response
    return mc


def _mock_embedder() -> MagicMock:
    """Build a mock SentenceEmbedder that returns a single zero vector."""
    emb = MagicMock()
    emb.embed.return_value = [[0.0] * EMBEDDING_DIM]
    return emb


_SAMPLE_ROWS = [
    {
        "id": 1,
        "content": "Risk management is required for all medical devices.",
        "similarity": 0.92,
        "metadata": {"doc_id": "ucm001", "title": "Risk Management", "section": "1", "chunk_index": 0},
    },
    {
        "id": 2,
        "content": "Design controls shall be established per 21 CFR 820.30.",
        "similarity": 0.85,
        "metadata": {"doc_id": "ucm002", "title": "Design Controls", "section": "2", "chunk_index": 0},
    },
    {
        "id": 3,
        "content": "Software validation is required for SaMD products.",
        "similarity": 0.78,
        "metadata": {"doc_id": "ucm001", "title": "Risk Management", "section": "4", "chunk_index": 2},
    },
]


class TestGuidanceSearchClientSearch(unittest.TestCase):

    def _client(self, rows=None) -> GuidanceSearchClient:
        return GuidanceSearchClient(
            supabase_client=_mock_supabase(_SAMPLE_ROWS if rows is None else rows),
            embedder=_mock_embedder(),
        )

    def test_search_returns_results(self) -> None:
        client = self._client()
        results = client.search("risk management")
        self.assertEqual(len(results), 3)

    def test_results_sorted_by_similarity_desc(self) -> None:
        client = self._client()
        results = client.search("risk management")
        sims = [r.similarity for r in results]
        self.assertEqual(sims, sorted(sims, reverse=True))

    def test_search_embeds_query(self) -> None:
        emb = _mock_embedder()
        client = GuidanceSearchClient(
            supabase_client=_mock_supabase(_SAMPLE_ROWS),
            embedder=emb,
        )
        client.search("test query")
        emb.embed.assert_called_once_with(["test query"])

    def test_search_calls_vector_search(self) -> None:
        mc = _mock_supabase(_SAMPLE_ROWS)
        client = GuidanceSearchClient(supabase_client=mc, embedder=_mock_embedder())
        client.search("query", k=5, threshold=0.8)
        mc.vector_search.assert_called_once()
        kwargs = mc.vector_search.call_args[1]
        self.assertEqual(kwargs["match_count"], 5)
        self.assertAlmostEqual(kwargs["match_threshold"], 0.8)

    def test_filter_by_doc_id(self) -> None:
        client = self._client()
        results = client.search("query", filter_by={"doc_id": "ucm001"})
        for r in results:
            self.assertEqual(r.doc_id, "ucm001")
        self.assertEqual(len(results), 2)

    def test_empty_response_returns_empty_list(self) -> None:
        client = self._client(rows=[])
        results = client.search("query")
        self.assertEqual(results, [])

    def test_result_fields_populated(self) -> None:
        client = self._client()
        r = client.search("query")[0]
        self.assertEqual(r.doc_id, "ucm001")
        self.assertEqual(r.title, "Risk Management")
        self.assertIsInstance(r.similarity, float)
        self.assertIsInstance(r.content, str)


class TestGuidanceSearchClientHelpers(unittest.TestCase):

    def _client(self) -> GuidanceSearchClient:
        return GuidanceSearchClient(
            supabase_client=_mock_supabase(_SAMPLE_ROWS),
            embedder=_mock_embedder(),
        )

    def test_search_by_doc_filters_correctly(self) -> None:
        results = self._client().search_by_doc("query", doc_id="ucm002")
        self.assertTrue(all(r.doc_id == "ucm002" for r in results))

    def test_top_result_returns_highest(self) -> None:
        r = self._client().top_result("query", threshold=0.5)
        self.assertIsNotNone(r)
        assert r is not None
        self.assertAlmostEqual(r.similarity, 0.92)

    def test_top_result_none_when_no_match(self) -> None:
        client = GuidanceSearchClient(
            supabase_client=_mock_supabase([]),
            embedder=_mock_embedder(),
        )
        self.assertIsNone(client.top_result("query"))

    def test_explain_returns_string(self) -> None:
        result = self._client().explain("risk management")
        self.assertIsInstance(result, str)
        self.assertIn("risk management", result)

    def test_explain_no_results(self) -> None:
        client = GuidanceSearchClient(
            supabase_client=_mock_supabase([]),
            embedder=_mock_embedder(),
        )
        result = client.explain("query")
        self.assertIn("No results", result)


class TestSearchGuidanceFunction(unittest.TestCase):

    def test_convenience_function_returns_list(self) -> None:
        results = search_guidance(
            query="risk management",
            supabase_client=_mock_supabase(_SAMPLE_ROWS),
            embedder=_mock_embedder(),
        )
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 3)


# ══════════════════════════════════════════════════════════════════════════════
#  CusumPoint + CusumSummary
# ══════════════════════════════════════════════════════════════════════════════

class TestCusumPoint(unittest.TestCase):

    def test_frozen(self) -> None:
        p = CusumPoint(index=0, value=10.0, cusum_high=1.0, cusum_low=0.0, alarm=False)
        with self.assertRaises(Exception):
            p.value = 99.0  # type: ignore[misc]

    def test_alarm_direction_default_empty(self) -> None:
        p = CusumPoint(index=0, value=10.0, cusum_high=0.0, cusum_low=0.0, alarm=False)
        self.assertEqual(p.alarm_direction, "")


class TestCusumSummary(unittest.TestCase):

    def _make(self, n_alarms=2, n_points=10) -> CusumSummary:
        return CusumSummary(
            n_points=n_points,
            n_alarms=n_alarms,
            first_alarm=3 if n_alarms else None,
            max_cusum_high=25.0,
            max_cusum_low=0.0,
        )

    def test_alarm_rate(self) -> None:
        s = self._make(n_alarms=2, n_points=10)
        self.assertAlmostEqual(s.alarm_rate, 0.2)

    def test_alarm_rate_zero_points(self) -> None:
        s = CusumSummary(n_points=0, n_alarms=0, first_alarm=None,
                          max_cusum_high=0.0, max_cusum_low=0.0)
        self.assertEqual(s.alarm_rate, 0.0)

    def test_has_alarm_true(self) -> None:
        self.assertTrue(self._make(n_alarms=1).has_alarm)

    def test_has_alarm_false(self) -> None:
        self.assertFalse(self._make(n_alarms=0).has_alarm)


# ══════════════════════════════════════════════════════════════════════════════
#  CusumDetector
# ══════════════════════════════════════════════════════════════════════════════

class TestCusumDetectorInit(unittest.TestCase):

    def test_invalid_allowance_raises(self) -> None:
        with self.assertRaises(ValueError):
            CusumDetector(target=10.0, allowance=0.0, threshold=20.0)

    def test_invalid_threshold_raises(self) -> None:
        with self.assertRaises(ValueError):
            CusumDetector(target=10.0, allowance=2.0, threshold=0.0)

    def test_initial_state_zero(self) -> None:
        det = CusumDetector(target=10.0, allowance=2.0, threshold=20.0)
        self.assertEqual(det.cusum_high, 0.0)
        self.assertEqual(det.cusum_low, 0.0)


class TestCusumDetectorUpdate(unittest.TestCase):

    def _det(self, target=10.0, k=2.0, h=20.0) -> CusumDetector:
        return CusumDetector(target=target, allowance=k, threshold=h)

    def test_no_alarm_on_target_value(self) -> None:
        det = self._det()
        point = det.update(10.0)
        self.assertFalse(point.alarm)

    def test_cusum_high_increases_on_high_value(self) -> None:
        det = self._det()
        p = det.update(20.0)   # 20 - 10 - 2 = 8 > 0
        self.assertGreater(p.cusum_high, 0.0)

    def test_cusum_high_stays_zero_on_low_value(self) -> None:
        det = self._det()
        p = det.update(5.0)    # 5 - 10 - 2 = -7 < 0 → clamped to 0
        self.assertEqual(p.cusum_high, 0.0)

    def test_alarm_fires_when_threshold_exceeded(self) -> None:
        det = self._det(target=10.0, k=1.0, h=5.0)
        points = [det.update(15.0) for _ in range(10)]
        alarm_points = [p for p in points if p.alarm]
        self.assertTrue(len(alarm_points) > 0)
        self.assertEqual(alarm_points[0].alarm_direction, "high")

    def test_downward_alarm(self) -> None:
        det = self._det(target=10.0, k=1.0, h=5.0)
        points = [det.update(2.0) for _ in range(10)]
        alarm_points = [p for p in points if p.alarm]
        self.assertTrue(len(alarm_points) > 0)
        self.assertEqual(alarm_points[0].alarm_direction, "low")

    def test_index_increments(self) -> None:
        det = self._det()
        for i in range(5):
            p = det.update(10.0)
            self.assertEqual(p.index, i)

    def test_reset_clears_state(self) -> None:
        det = self._det(target=10.0, k=1.0, h=5.0)
        for _ in range(5):
            det.update(20.0)
        self.assertGreater(det.cusum_high, 0.0)
        det.reset()
        self.assertEqual(det.cusum_high, 0.0)
        self.assertEqual(det.cusum_low, 0.0)

    def test_reset_on_alarm(self) -> None:
        det = CusumDetector(target=10.0, allowance=1.0, threshold=5.0, reset_on_alarm=True)
        alarms = []
        for _ in range(20):
            p = det.update(20.0)
            if p.alarm:
                alarms.append(p)
        # With reset_on_alarm, should get multiple alarms (not just one)
        self.assertGreater(len(alarms), 1)

    def test_run_returns_summary(self) -> None:
        det = self._det()
        summary = det.run([8, 9, 10, 11, 12])
        self.assertIsInstance(summary, CusumSummary)
        self.assertEqual(summary.n_points, 5)

    def test_run_resets_before_processing(self) -> None:
        det = self._det()
        det.update(100.0)  # dirty state
        summary = det.run([10.0] * 5)
        # Should start fresh; in-target values should produce no alarm
        self.assertFalse(summary.has_alarm)


# ══════════════════════════════════════════════════════════════════════════════
#  run_cusum convenience function
# ══════════════════════════════════════════════════════════════════════════════

class TestRunCusum(unittest.TestCase):

    def test_empty_series_raises(self) -> None:
        with self.assertRaises(ValueError):
            run_cusum([], target=10.0)

    def test_stable_series_no_alarm(self) -> None:
        # Stable series near target → no alarm
        series = [10.0, 10.5, 9.8, 10.2, 10.1, 9.9, 10.3]
        summary = run_cusum(series, target=10.0)
        self.assertFalse(summary.has_alarm)

    def test_spike_series_triggers_alarm(self) -> None:
        # Sudden sustained shift from 10 to 25
        series = [10.0] * 6 + [25.0] * 6
        summary = run_cusum(series, target=10.0, allowance=2.0, threshold=10.0)
        self.assertTrue(summary.has_alarm)

    def test_first_alarm_after_shift(self) -> None:
        series = [10.0] * 6 + [25.0] * 6
        summary = run_cusum(series, target=10.0, allowance=2.0, threshold=10.0)
        # Alarm should be in the second half
        assert summary.first_alarm is not None
        self.assertGreaterEqual(summary.first_alarm, 6)

    def test_all_points_returned(self) -> None:
        series = list(range(1, 11))
        summary = run_cusum(series, target=5.0)
        self.assertEqual(summary.n_points, 10)
        self.assertEqual(len(summary.points), 10)

    def test_custom_allowance_and_threshold(self) -> None:
        series = [10.0] * 5 + [30.0] * 5
        summary = run_cusum(series, target=10.0, allowance=1.0, threshold=5.0)
        self.assertTrue(summary.has_alarm)

    def test_max_cusum_high_tracked(self) -> None:
        series = [10.0, 20.0, 30.0]
        summary = run_cusum(series, target=10.0, allowance=1.0, threshold=100.0)
        self.assertGreater(summary.max_cusum_high, 0.0)


# ══════════════════════════════════════════════════════════════════════════════
#  Helper functions
# ══════════════════════════════════════════════════════════════════════════════

class TestAutoTarget(unittest.TestCase):

    def test_returns_mean_and_allowance(self) -> None:
        series = [10.0, 10.2, 9.8, 10.1, 9.9]
        mu, k = auto_target(series)
        self.assertAlmostEqual(mu, 10.0, places=1)
        self.assertGreater(k, 0.0)

    def test_too_few_raises(self) -> None:
        with self.assertRaises(ValueError):
            auto_target([5.0])

    def test_k_scales_with_k_sigma(self) -> None:
        series = [10.0, 12.0, 8.0, 11.0, 9.0]
        _, k1 = auto_target(series, k_sigma=0.5)
        _, k2 = auto_target(series, k_sigma=1.0)
        self.assertAlmostEqual(k2, 2 * k1, places=5)


class TestThresholdForArl(unittest.TestCase):

    def test_positive_result(self) -> None:
        h = threshold_for_arl(sigma=2.0, target_arl=500.0)
        self.assertGreater(h, 0.0)

    def test_larger_arl_gives_larger_threshold(self) -> None:
        h500  = threshold_for_arl(sigma=2.0, target_arl=500.0)
        h1000 = threshold_for_arl(sigma=2.0, target_arl=1000.0)
        self.assertGreater(h1000, h500)

    def test_larger_sigma_gives_larger_threshold(self) -> None:
        h1 = threshold_for_arl(sigma=1.0)
        h3 = threshold_for_arl(sigma=3.0)
        self.assertGreater(h3, h1)

    def test_arl_1_edge_case(self) -> None:
        # target_arl=1 → log(1)=0 → h=0
        h = threshold_for_arl(sigma=2.0, target_arl=1.0)
        self.assertAlmostEqual(h, 0.0, places=5)


if __name__ == "__main__":
    unittest.main()
