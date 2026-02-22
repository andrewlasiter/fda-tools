"""Sprint 6 unit tests — guidance_cluster, guidance_freshness, maude_classifier."""
import hashlib
import json
import math
import pytest


# ── guidance_cluster tests ────────────────────────────────────────────────────

def test_elbow_k_picks_reasonable_k():
    """_elbow_k should return a value within [min_k, max_k]."""
    from plugins.fda_tools.scripts.guidance_cluster import _elbow_k
    import numpy as np

    # Build a trivial linkage matrix where later merges are much larger
    # Structure: Z columns are [left, right, distance, count]
    Z = np.array([
        [0, 1, 1.0,  2],
        [2, 3, 1.2,  2],
        [4, 5, 1.3,  4],
        [6, 7, 5.0,  8],  # big jump here → elbow
        [8, 9, 8.0, 16],
    ])
    k = _elbow_k(Z, min_k=2, max_k=5, n_docs=10)
    assert 2 <= k <= 5


def test_elbow_k_minimum_docs():
    """When n_docs <= min_k, return n_docs."""
    from plugins.fda_tools.scripts.guidance_cluster import _elbow_k
    import numpy as np

    Z = np.array([[0, 1, 1.0, 2]])
    k = _elbow_k(Z, min_k=3, max_k=10, n_docs=2)
    assert k == 2


def test_auto_label_extracts_bigram():
    """_auto_label should find the most common non-stop bigram."""
    from plugins.fda_tools.scripts.guidance_cluster import _auto_label, ClusterDoc

    docs = [
        ClusterDoc("d1", "Software Validation Requirements", ""),
        ClusterDoc("d2", "Software Testing Guidance", ""),
        ClusterDoc("d3", "Software Validation Process", ""),
    ]
    label = _auto_label(0, docs)
    # "software" + "validation" appears twice; "software" + "testing" once
    assert "Software" in label or "software" in label.lower()


def test_auto_label_fallback_empty():
    """_auto_label with all-stopword titles falls back to 'Cluster N'."""
    from plugins.fda_tools.scripts.guidance_cluster import _auto_label, ClusterDoc

    docs = [ClusterDoc("d1", "Guidance for the Device", "")]
    label = _auto_label(0, docs)
    assert "Cluster" in label


def test_serialize_deserialize_roundtrip():
    """_serialize / _deserialize should be lossless."""
    from plugins.fda_tools.scripts.guidance_cluster import (
        _serialize, _deserialize, ClusterResult, Cluster, ClusterDoc, DendrogramData,
    )

    original = ClusterResult(
        k=2,
        n_docs=4,
        generated_at="2026-02-21T12:00:00Z",
        cache_hash="abc123",
        clusters=[
            Cluster(0, "Signal Processing", 2, [
                ClusterDoc("d1", "Doc One", "https://fda.gov/d1"),
                ClusterDoc("d2", "Doc Two", "https://fda.gov/d2"),
            ]),
            Cluster(1, "Clinical Safety", 2, [
                ClusterDoc("d3", "Doc Three", "https://fda.gov/d3"),
            ]),
        ],
        dendrogram=DendrogramData(
            icoord=[[5.0, 5.0, 15.0, 15.0]],
            dcoord=[[0.0, 1.0, 1.0, 0.0]],
            labels=["Doc One", "Doc Two"],
        ),
    )

    data   = _serialize(original)
    result = _deserialize(data)

    assert result.k            == 2
    assert result.n_docs       == 4
    assert result.cache_hash   == "abc123"
    assert len(result.clusters) == 2
    assert result.clusters[0].label == "Signal Processing"
    assert result.clusters[1].docs[0].doc_id == "d3"
    assert result.dendrogram.icoord == [[5.0, 5.0, 15.0, 15.0]]


def test_cluster_guidance_raises_without_db():
    """cluster_guidance raises EnvironmentError when DATABASE_URL is unset."""
    import os
    from plugins.fda_tools.scripts.guidance_cluster import cluster_guidance

    saved = os.environ.pop("DATABASE_URL", None)
    try:
        with pytest.raises(EnvironmentError, match="DATABASE_URL"):
            cluster_guidance(db_url=None)
    finally:
        if saved:
            os.environ["DATABASE_URL"] = saved


# ── guidance_freshness tests ──────────────────────────────────────────────────

def test_freshness_pct_all_fresh():
    from plugins.fda_tools.lib.guidance_freshness import FreshnessReport
    report = FreshnessReport(
        generated_at="2026-02-21T00:00:00Z",
        total_docs=10, fresh_count=10, stale_count=0,
        unknown_count=0, error_count=0,
    )
    assert report.freshness_pct == 100.0


def test_freshness_pct_mixed():
    from plugins.fda_tools.lib.guidance_freshness import FreshnessReport
    report = FreshnessReport(
        generated_at="2026-02-21T00:00:00Z",
        total_docs=10, fresh_count=7, stale_count=2,
        unknown_count=1, error_count=0,
    )
    assert report.freshness_pct == 70.0


def test_freshness_pct_no_docs():
    """freshness_pct returns 100.0 when no docs are tracked."""
    from plugins.fda_tools.lib.guidance_freshness import FreshnessReport
    report = FreshnessReport(
        generated_at="2026-02-21T00:00:00Z",
        total_docs=0, fresh_count=0, stale_count=0,
        unknown_count=0, error_count=0,
    )
    assert report.freshness_pct == 100.0


def test_doc_freshness_status_fields():
    from plugins.fda_tools.lib.guidance_freshness import DocFreshnessStatus
    s = DocFreshnessStatus(
        doc_id="g1", url="https://fda.gov/g1",
        status="STALE", reason="ETag changed",
        etag='"new-etag"', last_modified="Wed, 01 Jan 2026 00:00:00 GMT",
    )
    assert s.status == "STALE"
    assert s.etag   == '"new-etag"'


def test_compute_content_hash_deterministic():
    from plugins.fda_tools.lib.guidance_freshness import compute_content_hash
    data = b"PDF content bytes for testing"
    h1 = compute_content_hash(data)
    h2 = compute_content_hash(data)
    assert h1 == h2
    assert len(h1) == 32  # truncated SHA-256


def test_compute_content_hash_differs():
    from plugins.fda_tools.lib.guidance_freshness import compute_content_hash
    assert compute_content_hash(b"aaa") != compute_content_hash(b"bbb")


def test_checker_empty_report_without_db():
    """GuidanceFreshnessChecker with no DB returns empty FreshnessReport."""
    from plugins.fda_tools.lib.guidance_freshness import GuidanceFreshnessChecker
    checker = GuidanceFreshnessChecker(db_url=None)
    report  = checker.check_freshness()
    assert report.total_docs   == 0
    assert report.fresh_count  == 0
    assert report.freshness_pct == 100.0


# ── maude_classifier tests ────────────────────────────────────────────────────

def test_classify_regex_death():
    from plugins.fda_tools.scripts.maude_classifier import _classify_regex
    r = _classify_regex("evt1", "Patient died following device failure.")
    assert r.harm_type      == "DEATH"
    assert r.severity       == "CRITICAL"
    assert r.patient_outcome == "DEATH"
    assert r.method         == "regex"
    assert 0 < r.confidence < 1.0


def test_classify_regex_software():
    from plugins.fda_tools.scripts.maude_classifier import _classify_regex
    r = _classify_regex("evt2", "The firmware crashed and the device rebooted unexpectedly.")
    assert r.failure_mode == "SOFTWARE"


def test_classify_regex_no_injury():
    """'malfunction' (exact word) should match before 'no injury' in priority order."""
    from plugins.fda_tools.scripts.maude_classifier import _classify_regex
    r = _classify_regex("evt3", "Device had a malfunction but no injury occurred.")
    assert r.harm_type == "MALFUNCTION"  # malfunction pattern precedes no_injury


def test_classify_regex_unknown_narrative():
    from plugins.fda_tools.scripts.maude_classifier import _classify_regex
    r = _classify_regex("evt4", "xyz abc 123")
    assert r.harm_type      == "UNKNOWN"
    assert r.failure_mode   == "UNKNOWN"
    assert r.severity       == "UNKNOWN"
    assert r.patient_outcome == "UNKNOWN"


def test_parse_haiku_response_valid():
    from plugins.fda_tools.scripts.maude_classifier import _parse_haiku_response
    batch = [
        {"event_id": "e1", "text": "Patient injured after pump failure."},
        {"event_id": "e2", "text": "Device stopped; no harm."},
    ]
    payload = json.dumps([
        {"harm_type": "INJURY", "failure_mode": "MECHANICAL",
         "severity": "HIGH", "patient_outcome": "TEMPORARY_IMPAIRMENT",
         "confidence": 0.88},
        {"harm_type": "MALFUNCTION", "failure_mode": "OTHER",
         "severity": "LOW", "patient_outcome": "NO_OUTCOME",
         "confidence": 0.75},
    ])
    results = _parse_haiku_response(payload, batch)
    assert len(results)    == 2
    assert results[0].event_id    == "e1"
    assert results[0].harm_type   == "INJURY"
    assert results[0].confidence  == pytest.approx(0.88)
    assert results[1].patient_outcome == "NO_OUTCOME"
    assert all(r.method == "haiku" for r in results)


def test_parse_haiku_response_markdown_fence():
    """_parse_haiku_response should strip ```json fences."""
    from plugins.fda_tools.scripts.maude_classifier import _parse_haiku_response
    batch = [{"event_id": "e1", "text": "test"}]
    payload = "```json\n[{\"harm_type\":\"DEATH\",\"failure_mode\":\"OTHER\",\"severity\":\"CRITICAL\",\"patient_outcome\":\"DEATH\",\"confidence\":0.95}]\n```"
    results = _parse_haiku_response(payload, batch)
    assert len(results) == 1
    assert results[0].harm_type == "DEATH"


def test_parse_haiku_response_invalid_json():
    from plugins.fda_tools.scripts.maude_classifier import _parse_haiku_response
    batch   = [{"event_id": "e1", "text": "test"}]
    results = _parse_haiku_response("not json at all", batch)
    assert results == []


def test_classify_batch_empty():
    from plugins.fda_tools.scripts.maude_classifier import classify_batch
    assert classify_batch([]) == []


def test_classify_batch_regex_fallback():
    """classify_batch with use_haiku=False should use regex for all items."""
    from plugins.fda_tools.scripts.maude_classifier import classify_batch
    narratives = [
        {"event_id": "a1", "text": "Patient died from device failure."},
        {"event_id": "a2", "text": "Software crash caused incorrect readings."},
    ]
    results = classify_batch(narratives, use_haiku=False, use_cache=False)
    assert len(results) == 2
    methods = {r.event_id: r.method for r in results}
    assert all(m == "regex" for m in methods.values())
    # DEATH event
    death_r = next(r for r in results if r.event_id == "a1")
    assert death_r.harm_type == "DEATH"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
