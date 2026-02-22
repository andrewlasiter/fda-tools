"""Sprint 5 unit tests — guidance_search, signal_cusum, signal_correlation."""
import math
import statistics
import pytest

# ── CUSUM tests ───────────────────────────────────────────────────────────────

def test_cusum_detects_spike():
    from plugins.fda_tools.lib.signal_cusum import CUSUMDetector
    baseline = [5.0] * 20
    spike    = baseline + [30.0] + [5.0] * 10
    det = CUSUMDetector(k=0.5, h=5.0)
    res = det.detect(spike)
    assert len(res.alerts) >= 1
    assert res.alerts[0].direction == "UPPER"
    assert res.alerts[0].severity in ("CRITICAL", "HIGH")


def test_cusum_no_alert_on_flat():
    from plugins.fda_tools.lib.signal_cusum import CUSUMDetector
    flat = [5.0] * 30
    det = CUSUMDetector(k=0.5, h=5.0)
    res = det.detect(flat)
    assert res.alerts == []


def test_cusum_insufficient_data():
    from plugins.fda_tools.lib.signal_cusum import CUSUMDetector
    det = CUSUMDetector()
    res = det.detect([1, 2, 3])
    assert res.insufficient_data is True


def test_cusum_fit_then_detect():
    from plugins.fda_tools.lib.signal_cusum import CUSUMDetector
    baseline = [5.0] * 30
    det = CUSUMDetector(k=0.5, h=5.0)
    det.fit(baseline)
    assert det._mu == pytest.approx(5.0)
    res = det.detect([5.0, 5.0, 30.0, 5.0, 5.0, 5.0, 5.0], dates=["2026-01-0"+str(i+1) for i in range(7)])
    assert any(a.direction == "UPPER" for a in res.alerts)
    assert res.alerts[0].date is not None


def test_cusum_interpolates_negatives():
    from plugins.fda_tools.lib.signal_cusum import _interpolate_missing
    out = _interpolate_missing([1.0, -1.0, 3.0, 4.0, 5.0])
    assert out[1] == pytest.approx(2.0)


def test_cusum_severity_mapping():
    from plugins.fda_tools.lib.signal_cusum import _severity
    assert _severity(15.0, 5.0) == "CRITICAL"   # ratio=3
    assert _severity(10.0, 5.0) == "HIGH"        # ratio=2
    assert _severity(6.0, 5.0) == "MEDIUM"       # ratio=1.2


def test_cusum_returns_traces():
    from plugins.fda_tools.lib.signal_cusum import CUSUMDetector
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    det = CUSUMDetector()
    res = det.detect(data)
    assert len(res.cusum_plus) == len(data)
    assert len(res.cusum_minus) == len(data)


# ── Correlation tests ─────────────────────────────────────────────────────────

def test_pearson_perfect_correlation():
    from plugins.fda_tools.lib.signal_correlation import _pearson
    x = [float(i) for i in range(1, 11)]
    y = [float(i) * 2 for i in range(1, 11)]
    r, p = _pearson(x, y)
    assert r == pytest.approx(1.0, abs=1e-6)
    assert p == pytest.approx(0.0, abs=1e-6)


def test_pearson_anti_correlation():
    from plugins.fda_tools.lib.signal_correlation import _pearson
    x = [float(i) for i in range(1, 11)]
    y = [10.0 - float(i) for i in range(1, 11)]
    r, p = _pearson(x, y)
    assert r == pytest.approx(-1.0, abs=1e-6)


def test_pearson_constant_series():
    from plugins.fda_tools.lib.signal_correlation import _pearson
    r, p = _pearson([5.0] * 10, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    assert r is None  # zero variance


def test_correlate_insufficient_data():
    from plugins.fda_tools.lib.signal_correlation import correlate
    rpt = correlate("DQY", window_days=10,
                    maude_series={"2026-01": 5},
                    recall_series={"2026-01": 1})
    assert rpt.insufficient_data is True


def test_correlate_with_provided_series():
    from plugins.fda_tools.lib.signal_correlation import correlate
    # Perfectly correlated monthly data
    maude   = {f"2025-{i:02d}": i * 2 for i in range(1, 10)}
    recalls = {f"2025-{i:02d}": i for i in range(1, 10)}
    rpt = correlate("TST", window_days=300, maude_series=maude, recall_series=recalls)
    assert rpt.insufficient_data is False
    assert rpt.pearson_r is not None
    assert rpt.pearson_r == pytest.approx(1.0, abs=1e-3)


def test_correlate_interpretation_strong():
    from plugins.fda_tools.lib.signal_correlation import _interpret
    msg = _interpret(0.8, 0, 0.8)
    assert "Strong" in msg or "strong" in msg


def test_correlate_interpretation_none():
    from plugins.fda_tools.lib.signal_correlation import _interpret
    msg = _interpret(None, 0, None)
    assert "constant" in msg.lower() or "insufficient" in msg.lower()


# ── GuidanceSearcher tests ────────────────────────────────────────────────────

def test_guidance_searcher_empty_query():
    from plugins.fda_tools.lib.guidance_search import GuidanceSearcher
    s = GuidanceSearcher(db_url=None)
    resp = s.search("")
    assert resp.error is not None
    assert "Empty" in resp.error


def test_guidance_searcher_whitespace_query():
    from plugins.fda_tools.lib.guidance_search import GuidanceSearcher
    s = GuidanceSearcher(db_url=None)
    resp = s.search("   ")
    assert resp.error is not None


def test_guidance_result_dataclass():
    from plugins.fda_tools.lib.guidance_search import GuidanceResult, SearchResponse
    r = GuidanceResult(id="1", doc_id="d1", doc_title="Test Doc",
                       doc_url="https://fda.gov/doc1", chunk_index=0,
                       content="content here", similarity=0.87)
    assert r.similarity == 0.87
    resp = SearchResponse(query="test", top_k=5, results=[r])
    assert resp.count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
