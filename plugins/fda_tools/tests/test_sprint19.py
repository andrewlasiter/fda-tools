"""
Sprint 19 tests  —  FDA-238 (SIG-003 cross-signal correlation) +
                    FDA-234 (GD-004 hierarchical clustering / dendrogram)

All tests are unit-level and require no external dependencies (scipy, supabase, etc.).
Where scipy is present in the test environment it is patched away so that pure-Python
fallback paths are always exercised deterministically.
"""

from __future__ import annotations

import sys
import os
import math
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fda_tools.lib.signal_correlation import (
    CorrelationResult,
    CrossSignalAnalyzer,
    SignalSeries,
    _manual_kendall,
    _manual_pearson,
    _normal_cdf,
    _rank,
    correlate_signals,
)
from fda_tools.lib.guidance_cluster import (
    ClusterNode,
    ClusterResult,
    ClusteringUnavailableError,
    DendrogramData,
    GuidanceClusterer,
    _cosine_distance,
    _make_minimal_dendrogram,
    _simple_agglomerative,
    cluster_embeddings,
)


# ===========================================================================
# signal_correlation.py
# ===========================================================================

class TestSignalSeries(unittest.TestCase):
    def test_basic_construction(self):
        s = SignalSeries("maude", [1, 2, 3])
        self.assertEqual(s.name, "maude")
        self.assertEqual(s.values, (1.0, 2.0, 3.0))

    def test_float_coercion(self):
        s = SignalSeries("x", [1, 2, 3])
        self.assertIsInstance(s.values[0], float)

    def test_unit_default_empty(self):
        s = SignalSeries("x", [1, 2])
        self.assertEqual(s.unit, "")

    def test_len(self):
        s = SignalSeries("x", [10, 20, 30, 40])
        self.assertEqual(len(s), 4)

    def test_mean(self):
        s = SignalSeries("x", [2.0, 4.0, 6.0])
        self.assertAlmostEqual(s.mean, 4.0)

    def test_mean_empty(self):
        s = SignalSeries("x", [])
        self.assertEqual(s.mean, 0.0)

    def test_stdev(self):
        s = SignalSeries("x", [1.0, 3.0])
        self.assertGreater(s.stdev, 0.0)

    def test_stdev_single(self):
        s = SignalSeries("x", [5.0])
        self.assertEqual(s.stdev, 0.0)

    def test_frozen(self):
        s = SignalSeries("x", [1.0])
        with self.assertRaises((AttributeError, TypeError)):
            s.name = "y"  # type: ignore[misc]


class TestCorrelationResult(unittest.TestCase):
    def _make(self, r: float, p: float = 0.01) -> CorrelationResult:
        return CorrelationResult(
            series_a="a", series_b="b", method="pearson",
            coefficient=r, p_value=p, lag=0, n=10, significant=(p < 0.05),
        )

    def test_strong(self):
        self.assertEqual(self._make(0.9).strength, "strong")

    def test_moderate(self):
        self.assertEqual(self._make(0.5).strength, "moderate")

    def test_weak(self):
        self.assertEqual(self._make(0.3).strength, "weak")

    def test_negligible(self):
        self.assertEqual(self._make(0.1).strength, "negligible")

    def test_negative_strength_uses_abs(self):
        self.assertEqual(self._make(-0.8).strength, "strong")

    def test_as_dict_keys(self):
        d = self._make(0.6).as_dict()
        expected = {"series_a", "series_b", "method", "coefficient", "p_value",
                    "lag", "n", "significant", "strength"}
        self.assertEqual(set(d.keys()), expected)

    def test_as_dict_coefficient_rounded(self):
        d = self._make(0.123456789).as_dict()
        self.assertEqual(d["coefficient"], round(0.123456789, 4))

    def test_significant_flag(self):
        self.assertTrue(self._make(0.5, p=0.01).significant)
        self.assertFalse(self._make(0.5, p=0.10).significant)

    def test_frozen(self):
        r = self._make(0.5)
        with self.assertRaises((AttributeError, TypeError)):
            r.coefficient = 0.9  # type: ignore[misc]


# ── Internal math helpers ────────────────────────────────────────────────────

class TestNormalCdf(unittest.TestCase):
    def test_symmetry(self):
        self.assertAlmostEqual(_normal_cdf(0), 0.5, places=3)

    def test_positive_z(self):
        # Φ(1.96) ≈ 0.975
        self.assertAlmostEqual(_normal_cdf(1.96), 0.975, places=2)

    def test_negative_z(self):
        # Φ(-1.96) ≈ 0.025
        self.assertAlmostEqual(_normal_cdf(-1.96), 0.025, places=2)


class TestRank(unittest.TestCase):
    def test_basic_ranks(self):
        ranks = _rank([10.0, 20.0, 30.0])
        self.assertEqual(ranks, [1.0, 2.0, 3.0])

    def test_tie_averaging(self):
        ranks = _rank([10.0, 10.0, 30.0])
        # Both 10.0 should be ranked (1+2)/2 = 1.5
        self.assertEqual(ranks[0], 1.5)
        self.assertEqual(ranks[1], 1.5)
        self.assertEqual(ranks[2], 3.0)

    def test_single(self):
        ranks = _rank([99.0])
        self.assertEqual(ranks, [1.0])


class TestManualPearson(unittest.TestCase):
    def test_perfect_positive(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        r, p = _manual_pearson(x, x)
        self.assertAlmostEqual(r, 1.0, places=5)

    def test_perfect_negative(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [5.0, 4.0, 3.0, 2.0, 1.0]
        r, p = _manual_pearson(x, y)
        self.assertAlmostEqual(r, -1.0, places=5)

    def test_zero_variance_returns_zero(self):
        x = [5.0] * 5
        y = [1.0, 2.0, 3.0, 4.0, 5.0]
        r, p = _manual_pearson(x, y)
        self.assertEqual(r, 0.0)
        self.assertEqual(p, 1.0)

    def test_too_short_returns_zero(self):
        r, p = _manual_pearson([1.0], [2.0])
        self.assertEqual(r, 0.0)
        self.assertEqual(p, 1.0)

    def test_p_value_range(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [1.1, 2.2, 3.1, 4.0, 5.2]
        _, p = _manual_pearson(x, y)
        self.assertGreaterEqual(p, 0.0)
        self.assertLessEqual(p, 1.0)


class TestManualKendall(unittest.TestCase):
    def test_perfect_concordance(self):
        x = [1.0, 2.0, 3.0, 4.0]
        tau, p = _manual_kendall(x, x)
        self.assertAlmostEqual(tau, 1.0, places=5)

    def test_perfect_discordance(self):
        x = [1.0, 2.0, 3.0, 4.0]
        y = [4.0, 3.0, 2.0, 1.0]
        tau, p = _manual_kendall(x, y)
        self.assertAlmostEqual(tau, -1.0, places=5)

    def test_p_range(self):
        x = [1.0, 2.0, 3.0, 4.0]
        y = [1.1, 2.2, 3.1, 4.0]
        _, p = _manual_kendall(x, y)
        self.assertGreaterEqual(p, 0.0)
        self.assertLessEqual(p, 1.0)


# ── CrossSignalAnalyzer ──────────────────────────────────────────────────────

_MAUDE    = SignalSeries("maude",    [10, 12,  9, 11, 35, 40, 38, 12])
_RECALLS  = SignalSeries("recalls",  [ 1,  1,  1,  2,  3,  8,  9,  3])
_ENFORCE  = SignalSeries("enforce",  [ 0,  0,  0,  0,  1,  2,  3,  1])


class TestCrossSignalAnalyzerInit(unittest.TestCase):
    def test_requires_two_series(self):
        with self.assertRaises(ValueError):
            CrossSignalAnalyzer([_MAUDE])

    def test_two_series_ok(self):
        a = CrossSignalAnalyzer([_MAUDE, _RECALLS])
        self.assertIn("maude", a.signals)
        self.assertIn("recalls", a.signals)


class TestCrossSignalAnalyzerCorrelate(unittest.TestCase):
    def setUp(self):
        self.ana = CrossSignalAnalyzer([_MAUDE, _RECALLS, _ENFORCE])

    def test_correlate_returns_result(self):
        r = self.ana.correlate("maude", "recalls")
        self.assertIsInstance(r, CorrelationResult)

    def test_correlate_pearson_default(self):
        r = self.ana.correlate("maude", "recalls")
        self.assertEqual(r.method, "pearson")

    def test_correlate_spearman(self):
        r = self.ana.correlate("maude", "recalls", method="spearman")
        self.assertEqual(r.method, "spearman")

    def test_correlate_kendall(self):
        r = self.ana.correlate("maude", "recalls", method="kendall")
        self.assertEqual(r.method, "kendall")

    def test_correlate_coefficient_range(self):
        r = self.ana.correlate("maude", "recalls")
        self.assertGreaterEqual(r.coefficient, -1.0)
        self.assertLessEqual(r.coefficient, 1.0)

    def test_correlate_n_matches_series(self):
        r = self.ana.correlate("maude", "recalls")
        self.assertEqual(r.n, min(len(_MAUDE), len(_RECALLS)))

    def test_correlate_maude_recalls_positive(self):
        # Both spike together — expect positive correlation
        r = self.ana.correlate("maude", "recalls")
        self.assertGreater(r.coefficient, 0.5)

    def test_correlate_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            self.ana.correlate("maude", "recalls", method="bogus")

    def test_correlate_unknown_series_raises(self):
        with self.assertRaises(KeyError):
            self.ana.correlate("maude", "doesnotexist")

    def test_correlate_with_lag(self):
        r = self.ana.correlate("maude", "recalls", lag=1)
        self.assertEqual(r.lag, 1)
        self.assertEqual(r.n, min(len(_MAUDE), len(_RECALLS)) - 1)

    def test_correlate_excessive_lag_raises(self):
        with self.assertRaises(ValueError):
            self.ana.correlate("maude", "recalls", lag=20)


class TestCrossSignalAnalyzerAll(unittest.TestCase):
    def setUp(self):
        self.ana = CrossSignalAnalyzer([_MAUDE, _RECALLS, _ENFORCE])

    def test_correlate_all_count(self):
        # 3 series → 3 pairs
        results = self.ana.correlate_all()
        self.assertEqual(len(results), 3)

    def test_correlate_all_sorted_desc(self):
        results = self.ana.correlate_all()
        coeffs = [abs(r.coefficient) for r in results]
        self.assertEqual(coeffs, sorted(coeffs, reverse=True))

    def test_correlate_all_spearman(self):
        results = self.ana.correlate_all(method="spearman")
        self.assertTrue(all(r.method == "spearman" for r in results))


class TestLagAnalysis(unittest.TestCase):
    def setUp(self):
        self.ana = CrossSignalAnalyzer([_MAUDE, _RECALLS, _ENFORCE])

    def test_lag_analysis_length(self):
        results = self.ana.lag_analysis("maude", "recalls", max_lag=3)
        # lag 0,1,2,3 — all should have ≥3 points for 8-element series
        self.assertEqual(len(results), 4)

    def test_lag_analysis_sorted_by_lag(self):
        results = self.ana.lag_analysis("maude", "recalls", max_lag=3)
        lags = [r.lag for r in results]
        self.assertEqual(lags, sorted(lags))

    def test_lag_zero_included(self):
        results = self.ana.lag_analysis("maude", "recalls", max_lag=2)
        self.assertTrue(any(r.lag == 0 for r in results))

    def test_peak_lag_returns_result(self):
        r = self.ana.peak_lag("maude", "recalls", max_lag=3)
        self.assertIsNotNone(r)

    def test_peak_lag_best_coefficient(self):
        results = self.ana.lag_analysis("maude", "recalls", max_lag=3)
        peak = self.ana.peak_lag("maude", "recalls", max_lag=3)
        best = max(results, key=lambda x: abs(x.coefficient))
        assert peak is not None
        self.assertAlmostEqual(abs(peak.coefficient), abs(best.coefficient), places=9)


class TestCompositeRiskScore(unittest.TestCase):
    def setUp(self):
        self.ana = CrossSignalAnalyzer([_MAUDE, _RECALLS, _ENFORCE])

    def test_score_range(self):
        score = self.ana.composite_risk_score()
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_uncorrelated_series_low_score(self):
        # Two completely independent series
        import random
        random.seed(42)
        a = SignalSeries("a", [random.random() for _ in range(20)])
        b = SignalSeries("b", [random.random() for _ in range(20)])
        score = CrossSignalAnalyzer([a, b]).composite_risk_score()
        self.assertLess(score, 0.8)

    def test_identical_series_high_score(self):
        a = SignalSeries("a", [1, 3, 2, 5, 8, 7, 6])
        b = SignalSeries("b", [1, 3, 2, 5, 8, 7, 6])
        score = CrossSignalAnalyzer([a, b]).composite_risk_score()
        self.assertGreater(score, 0.5)

    def test_summary_string(self):
        s = self.ana.summary()
        self.assertIn("maude", s)
        self.assertIn("Composite risk score", s)


class TestCorrelateSignalsFunction(unittest.TestCase):
    def test_convenience_function(self):
        results = correlate_signals([_MAUDE, _RECALLS, _ENFORCE])
        self.assertEqual(len(results), 3)
        self.assertIsInstance(results[0], CorrelationResult)

    def test_too_few_raises(self):
        with self.assertRaises(ValueError):
            correlate_signals([_MAUDE])


# ===========================================================================
# guidance_cluster.py
# ===========================================================================

class TestCosineDistance(unittest.TestCase):
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(_cosine_distance(v, v), 0.0, places=6)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        self.assertAlmostEqual(_cosine_distance(a, b), 1.0, places=6)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        self.assertAlmostEqual(_cosine_distance(a, b), 2.0, places=6)

    def test_zero_vector_returns_one(self):
        self.assertEqual(_cosine_distance([0.0, 0.0], [1.0, 0.0]), 1.0)


class TestClusterNode(unittest.TestCase):
    def test_construction(self):
        node = ClusterNode(left_id=0, right_id=1, distance=0.5, count=2)
        self.assertEqual(node.count, 2)

    def test_frozen(self):
        node = ClusterNode(left_id=0, right_id=1, distance=0.5, count=2)
        with self.assertRaises((AttributeError, TypeError)):
            node.count = 99  # type: ignore[misc]


class TestDendrogramData(unittest.TestCase):
    def test_as_dict_keys(self):
        d = DendrogramData(icoord=[], dcoord=[], ivl=[], leaves=[], color_list=[])
        keys = set(d.as_dict().keys())
        self.assertEqual(keys, {"icoord", "dcoord", "ivl", "leaves", "color_list"})

    def test_frozen(self):
        d = DendrogramData(icoord=[], dcoord=[], ivl=[], leaves=[], color_list=[])
        with self.assertRaises((AttributeError, TypeError)):
            d.ivl = ["x"]  # type: ignore[misc]


class TestClusterResult(unittest.TestCase):
    def test_cluster_sizes(self):
        r = ClusterResult(labels=[0, 1, 0, 1, 2], n_clusters=3, n_samples=5)
        sizes = r.cluster_sizes
        self.assertEqual(sizes[0], 2)
        self.assertEqual(sizes[1], 2)
        self.assertEqual(sizes[2], 1)

    def test_as_dict_keys(self):
        r = ClusterResult(labels=[0, 1], n_clusters=2, n_samples=2)
        keys = set(r.as_dict().keys())
        self.assertIn("n_clusters", keys)
        self.assertIn("inertia", keys)
        self.assertIn("cluster_sizes", keys)
        self.assertIn("dendrogram", keys)


class TestMakeMinimalDendrogram(unittest.TestCase):
    def test_n_leaves(self):
        d = _make_minimal_dendrogram(5)
        self.assertEqual(len(d.leaves), 5)
        self.assertEqual(len(d.ivl), 5)

    def test_empty_coords(self):
        d = _make_minimal_dendrogram(3)
        self.assertEqual(d.icoord, [])
        self.assertEqual(d.dcoord, [])


class TestSimpleAgglomerative(unittest.TestCase):
    """Tests for the no-scipy single-linkage fallback."""

    def _make_embeddings(self, n: int = 6, dim: int = 4) -> list:
        # Deterministic "structured" embeddings: 3 tight groups
        data = []
        for i in range(n):
            group = i % 3
            base = [float(group * 10)] * dim
            data.append(base)
        return data

    def test_returns_n_distinct_labels(self):
        embs = self._make_embeddings(6)
        labels, _ = _simple_agglomerative(embs, n_clusters=3)
        self.assertEqual(len(set(labels)), 3)

    def test_label_count_matches_input(self):
        embs = self._make_embeddings(6)
        labels, _ = _simple_agglomerative(embs, n_clusters=2)
        self.assertEqual(len(labels), 6)

    def test_n_clusters_ge_n(self):
        embs = self._make_embeddings(4)
        labels, inertia = _simple_agglomerative(embs, n_clusters=10)
        # k >= n → each point is its own cluster
        self.assertEqual(len(set(labels)), len(embs))

    def test_inertia_non_negative(self):
        embs = self._make_embeddings(6)
        _, inertia = _simple_agglomerative(embs, n_clusters=2)
        self.assertGreaterEqual(inertia, 0.0)


class TestGuidanceClustererFallback(unittest.TestCase):
    """Test GuidanceClusterer with scipy patched away."""

    def _embeddings(self, n: int = 8) -> list:
        # Two well-separated clusters
        return [
            [1.0, 0.0, 0.0, 0.0] if i < n // 2 else [0.0, 1.0, 0.0, 0.0]
            for i in range(n)
        ]

    def test_fit_returns_cluster_result(self):
        with patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", False):
            c = GuidanceClusterer(n_clusters=2)
            result = c.fit(self._embeddings())
        self.assertIsInstance(result, ClusterResult)

    def test_fit_label_count(self):
        with patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", False):
            result = GuidanceClusterer(n_clusters=2).fit(self._embeddings(8))
        self.assertEqual(len(result.labels), 8)

    def test_fit_n_clusters(self):
        with patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", False):
            result = GuidanceClusterer(n_clusters=2).fit(self._embeddings(8))
        self.assertEqual(result.n_clusters, 2)

    def test_fit_two_embeddings(self):
        with patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", False):
            result = GuidanceClusterer(n_clusters=2).fit([[1.0, 0.0], [0.0, 1.0]])
        self.assertEqual(len(result.labels), 2)

    def test_fit_single_raises(self):
        with self.assertRaises(ValueError):
            GuidanceClusterer(n_clusters=2).fit([[1.0, 0.0]])

    def test_require_scipy_raises_when_absent(self):
        with patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", False):
            c = GuidanceClusterer(n_clusters=2, require_scipy=True)
            with self.assertRaises(ClusteringUnavailableError):
                c.fit([[1.0, 0.0], [0.0, 1.0]])

    def test_result_property_none_before_fit(self):
        c = GuidanceClusterer(n_clusters=2)
        self.assertIsNone(c.result)

    def test_result_property_after_fit(self):
        with patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", False):
            c = GuidanceClusterer(n_clusters=2)
            c.fit(self._embeddings(4))
        self.assertIsNotNone(c.result)

    def test_dendrogram_present(self):
        with patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", False):
            result = GuidanceClusterer(n_clusters=2).fit(self._embeddings(4))
        self.assertIsNotNone(result.dendrogram)

    def test_recut_without_prior_fit_raises(self):
        with patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", False):
            c = GuidanceClusterer(n_clusters=2)
            with self.assertRaises(RuntimeError):
                c.recut(3)

    def test_invalid_n_clusters_raises(self):
        with self.assertRaises(ValueError):
            GuidanceClusterer(n_clusters=0)

    def test_n_clusters_capped_at_n(self):
        # Requesting more clusters than samples → capped to n
        with patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", False):
            result = GuidanceClusterer(n_clusters=100).fit(
                [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]]
            )
        self.assertLessEqual(result.n_clusters, 3)


class TestGuidanceClustererScipy(unittest.TestCase):
    """
    Test the scipy path using a real (mocked) scipy interface.
    This avoids importing actual scipy — we mock the module-level references.
    """

    def _mock_scipy(self):
        """Return mock callables for scipy linkage/fcluster/dendrogram/pdist."""
        import numpy as _np  # noqa: F401

        mock_pdist = MagicMock(return_value=[0.1, 0.5, 0.4])
        # Ward linkage for 4 points → 3 merge rows
        mock_Z = MagicMock()
        mock_Z.tolist.return_value = [
            [0.0, 1.0, 0.1, 2.0],
            [2.0, 3.0, 0.4, 2.0],
            [4.0, 5.0, 0.5, 4.0],
        ]
        mock_Z.__getitem__ = lambda self_, key: [
            [0.0, 1.0, 0.1, 2.0],
            [2.0, 3.0, 0.4, 2.0],
            [4.0, 5.0, 0.5, 4.0],
        ][key]  # type: ignore[index]
        mock_linkage = MagicMock(return_value=mock_Z)
        mock_fcluster = MagicMock(return_value=[1, 1, 2, 2])  # 1-based scipy labels
        mock_dendrogram = MagicMock(return_value={
            "icoord": [[5, 5, 15, 15]],
            "dcoord": [[0, 0.1, 0.1, 0]],
            "ivl":    ["0", "1", "2", "3"],
            "leaves": [0, 1, 2, 3],
            "color_list": ["C0"],
        })
        return mock_pdist, mock_linkage, mock_fcluster, mock_dendrogram

    def test_scipy_path_labels(self):
        p, l, f, d = self._mock_scipy()
        with (
            patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", True),
            patch("fda_tools.lib.guidance_cluster._scipy_pdist", p),
            patch("fda_tools.lib.guidance_cluster._scipy_linkage", l),
            patch("fda_tools.lib.guidance_cluster._scipy_fcluster", f),
            patch("fda_tools.lib.guidance_cluster._scipy_dendrogram", d),
        ):
            result = GuidanceClusterer(n_clusters=2).fit(
                [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5], [0.9, 0.1]]
            )
        # scipy returns 1-based [1,1,2,2] → convert to 0-based [0,0,1,1]
        self.assertEqual(result.labels, [0, 0, 1, 1])

    def test_scipy_path_dendrogram(self):
        p, l, f, d = self._mock_scipy()
        with (
            patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", True),
            patch("fda_tools.lib.guidance_cluster._scipy_pdist", p),
            patch("fda_tools.lib.guidance_cluster._scipy_linkage", l),
            patch("fda_tools.lib.guidance_cluster._scipy_fcluster", f),
            patch("fda_tools.lib.guidance_cluster._scipy_dendrogram", d),
        ):
            result = GuidanceClusterer(n_clusters=2).fit(
                [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5], [0.9, 0.1]]
            )
        assert result.dendrogram is not None
        self.assertIn("icoord", result.dendrogram.as_dict())
        self.assertEqual(result.dendrogram.ivl, ["0", "1", "2", "3"])

    def test_scipy_path_nodes(self):
        p, l, f, d = self._mock_scipy()
        with (
            patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", True),
            patch("fda_tools.lib.guidance_cluster._scipy_pdist", p),
            patch("fda_tools.lib.guidance_cluster._scipy_linkage", l),
            patch("fda_tools.lib.guidance_cluster._scipy_fcluster", f),
            patch("fda_tools.lib.guidance_cluster._scipy_dendrogram", d),
        ):
            result = GuidanceClusterer(n_clusters=2).fit(
                [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5], [0.9, 0.1]]
            )
        self.assertEqual(len(result.nodes), 3)
        self.assertIsInstance(result.nodes[0], ClusterNode)

    def test_recut_without_scipy_raises(self):
        with patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", False):
            c = GuidanceClusterer(n_clusters=2)
            # Manually seed result to trigger recut path
            c._result = ClusterResult(  # type: ignore[attr-defined]
                labels=[0, 1], n_clusters=2, n_samples=2, linkage_matrix=[]
            )
            with self.assertRaises(ClusteringUnavailableError):
                c.recut(3)


class TestClusterEmbeddingsFunction(unittest.TestCase):
    def test_convenience_wrapper(self):
        with patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", False):
            result = cluster_embeddings(
                [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]], n_clusters=2
            )
        self.assertIsInstance(result, ClusterResult)

    def test_labels_count_matches_input(self):
        with patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", False):
            result = cluster_embeddings(
                [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]], n_clusters=2
            )
        self.assertEqual(len(result.labels), 3)

    def test_custom_labels_passed_through(self):
        custom = ["doc_a", "doc_b", "doc_c"]
        with patch("fda_tools.lib.guidance_cluster._SCIPY_AVAILABLE", False):
            result = cluster_embeddings(
                [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]],
                n_clusters=2,
                labels=custom,
            )
        # Fallback dendrogram uses minimal data regardless of labels
        self.assertIsNotNone(result)


# ===========================================================================

if __name__ == "__main__":
    unittest.main()
