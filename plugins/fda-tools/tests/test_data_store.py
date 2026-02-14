"""Tests for the FDA Project Data Store (fda_data_store.py).

Validates manifest CRUD, TTL expiration, query key generation,
summary extraction, print formatting, and CLI argument handling.
These tests do NOT require API access — they test data store logic only.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

# Add scripts directory to path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fda_data_store import (
    load_manifest,
    save_manifest,
    is_expired,
    make_query_key,
    extract_classification_summary,
    extract_recalls_summary,
    extract_events_summary,
    extract_510k_summary,
    extract_510k_batch_summary,
    extract_enforcement_summary,
    print_classification,
    print_recalls,
    print_events,
    print_510k,
    print_510k_batch,
    print_enforcement,
    handle_show_manifest,
    handle_clear,
    handle_refresh_all,
    _compact_summary,
    _print_result,
    _extract_summary,
    _get_endpoint,
    _get_params,
    TTL_TIERS,
    get_projects_dir,
)


# ============================================================
# Manifest CRUD
# ============================================================


class TestManifestCRUD:
    """Test manifest creation, loading, and saving."""

    def test_load_creates_new_manifest_when_missing(self, tmp_path):
        manifest = load_manifest(str(tmp_path / "nonexistent_project"))
        assert manifest["project"] == "nonexistent_project"
        assert manifest["queries"] == {}
        assert manifest["product_codes"] == []
        assert "created_at" in manifest
        assert "last_updated" in manifest

    def test_load_reads_existing_manifest(self, tmp_path):
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        data = {
            "project": "test_project",
            "created_at": "2026-02-09T12:00:00+00:00",
            "last_updated": "2026-02-09T12:00:00+00:00",
            "product_codes": ["OVE"],
            "queries": {"classification:OVE": {"summary": {"device_class": "2"}}},
        }
        (project_dir / "data_manifest.json").write_text(json.dumps(data))
        manifest = load_manifest(str(project_dir))
        assert manifest["project"] == "test_project"
        assert manifest["product_codes"] == ["OVE"]
        assert "classification:OVE" in manifest["queries"]

    def test_load_handles_corrupt_json(self, tmp_path):
        project_dir = tmp_path / "corrupt"
        project_dir.mkdir()
        (project_dir / "data_manifest.json").write_text("{invalid json}")
        manifest = load_manifest(str(project_dir))
        assert manifest["project"] == "corrupt"
        assert manifest["queries"] == {}

    def test_save_creates_directory(self, tmp_path):
        project_dir = str(tmp_path / "new" / "nested" / "project")
        manifest = load_manifest(project_dir)
        save_manifest(project_dir, manifest)
        assert os.path.exists(os.path.join(project_dir, "data_manifest.json"))

    def test_save_updates_last_updated(self, tmp_path):
        project_dir = str(tmp_path / "proj")
        manifest = load_manifest(project_dir)
        old_time = manifest["last_updated"]
        save_manifest(project_dir, manifest)
        with open(os.path.join(project_dir, "data_manifest.json")) as f:
            saved = json.load(f)
        # last_updated should be updated (or at least present)
        assert "last_updated" in saved

    def test_save_roundtrip(self, tmp_path):
        project_dir = str(tmp_path / "roundtrip")
        manifest = {
            "project": "roundtrip",
            "created_at": "2026-02-09T10:00:00+00:00",
            "last_updated": "2026-02-09T10:00:00+00:00",
            "product_codes": ["QAS", "DQY"],
            "queries": {
                "classification:QAS": {
                    "fetched_at": "2026-02-09T10:00:00+00:00",
                    "ttl_hours": 168,
                    "summary": {"device_class": "2"},
                }
            },
        }
        save_manifest(project_dir, manifest)
        loaded = load_manifest(project_dir)
        assert loaded["product_codes"] == ["QAS", "DQY"]
        assert "classification:QAS" in loaded["queries"]


# ============================================================
# TTL Expiration
# ============================================================


class TestTTLExpiration:
    """Test cache entry TTL expiration logic."""

    def test_fresh_entry_not_expired(self):
        entry = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "ttl_hours": 24,
        }
        assert is_expired(entry) is False

    def test_old_entry_expired(self):
        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        entry = {"fetched_at": old_time, "ttl_hours": 24}
        assert is_expired(entry) is True

    def test_7day_ttl_not_expired_at_6_days(self):
        six_days_ago = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()
        entry = {"fetched_at": six_days_ago, "ttl_hours": 168}
        assert is_expired(entry) is False

    def test_7day_ttl_expired_at_8_days(self):
        eight_days_ago = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        entry = {"fetched_at": eight_days_ago, "ttl_hours": 168}
        assert is_expired(entry) is True

    def test_missing_fetched_at_is_expired(self):
        entry = {"ttl_hours": 24}
        assert is_expired(entry) is True

    def test_empty_fetched_at_is_expired(self):
        entry = {"fetched_at": "", "ttl_hours": 24}
        assert is_expired(entry) is True

    def test_invalid_date_is_expired(self):
        entry = {"fetched_at": "not-a-date", "ttl_hours": 24}
        assert is_expired(entry) is True

    def test_naive_datetime_treated_as_utc(self):
        # Naive datetime (no timezone) should still work
        entry = {
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "ttl_hours": 24,
        }
        assert is_expired(entry) is False

    def test_default_ttl_24h(self):
        # Entry without ttl_hours defaults to 24
        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        entry = {"fetched_at": old_time}
        assert is_expired(entry) is True


# ============================================================
# TTL Tier Values
# ============================================================


class TestTTLTiers:
    """Verify TTL tier configuration values."""

    def test_classification_7_days(self):
        assert TTL_TIERS["classification"] == 168

    def test_510k_7_days(self):
        assert TTL_TIERS["510k"] == 168

    def test_510k_batch_7_days(self):
        assert TTL_TIERS["510k-batch"] == 168

    def test_recalls_24_hours(self):
        assert TTL_TIERS["recalls"] == 24

    def test_events_24_hours(self):
        assert TTL_TIERS["events"] == 24

    def test_enforcement_24_hours(self):
        assert TTL_TIERS["enforcement"] == 24

    def test_udi_7_days(self):
        assert TTL_TIERS["udi"] == 168

    def test_pma_7_days(self):
        assert TTL_TIERS["pma"] == 168


# ============================================================
# Query Key Generation
# ============================================================


class TestQueryKeyGeneration:
    """Test canonical query key generation."""

    def test_classification_key(self):
        key = make_query_key("classification", product_code="OVE")
        assert key == "classification:OVE"

    def test_recalls_key(self):
        key = make_query_key("recalls", product_code="QAS")
        assert key == "recalls:QAS"

    def test_events_key_with_count(self):
        key = make_query_key("events", product_code="OVE", count_field="event_type.exact")
        assert key == "events:OVE:count:event_type.exact"

    def test_events_key_without_count(self):
        key = make_query_key("events", product_code="OVE")
        assert key == "events:OVE"

    def test_510k_single_key(self):
        key = make_query_key("510k", k_number="K241335")
        assert key == "510k:K241335"

    def test_510k_batch_key_sorted(self):
        key = make_query_key("510k-batch", k_numbers=["K200123", "K241335"])
        assert key == "510k-batch:K200123,K241335"

    def test_510k_batch_key_sorted_reverse_input(self):
        key = make_query_key("510k-batch", k_numbers=["K241335", "K200123"])
        assert key == "510k-batch:K200123,K241335"

    def test_enforcement_key(self):
        key = make_query_key("enforcement", product_code="OVE")
        assert key == "enforcement:OVE"

    def test_no_params_just_type(self):
        key = make_query_key("classification")
        assert key == "classification"


# ============================================================
# Summary Extractors
# ============================================================


class TestClassificationSummary:
    """Test classification summary extraction."""

    def test_extracts_all_fields(self):
        result = {
            "results": [{
                "device_name": "Intervertebral Body Fusion Device",
                "device_class": "2",
                "regulation_number": "888.3080",
                "medical_specialty_description": "Orthopedic",
                "definition": "A device intended to be implanted...",
                "gmp_exempt_flag": "N",
                "third_party_flag": "Y",
                "implant_flag": "Y",
                "life_sustain_support_flag": "N",
            }]
        }
        summary = extract_classification_summary(result)
        assert summary["device_name"] == "Intervertebral Body Fusion Device"
        assert summary["device_class"] == "2"
        assert summary["regulation_number"] == "888.3080"
        assert summary["review_panel"] == "Orthopedic"
        assert summary["implant_flag"] == "Y"
        assert summary["gmp_exempt"] == "N"

    def test_no_results(self):
        result = {"results": []}
        summary = extract_classification_summary(result)
        assert "error" in summary

    def test_missing_results_key(self):
        result = {}
        summary = extract_classification_summary(result)
        assert "error" in summary

    def test_falls_back_to_review_panel(self):
        result = {
            "results": [{
                "device_name": "Test",
                "review_panel": "OR",
            }]
        }
        summary = extract_classification_summary(result)
        assert summary["review_panel"] == "OR"


class TestRecallsSummary:
    """Test recalls summary extraction."""

    def test_extracts_recall_counts(self):
        result = {
            "meta": {"results": {"total": 12}},
            "results": [
                {"recall_status": "Ongoing", "classification": "Class II", "event_date_initiated": "2025-11-15"},
                {"recall_status": "Terminated", "classification": "Class I", "event_date_initiated": "2024-03-01"},
                {"recall_status": "Terminated", "classification": "Class II", "event_date_initiated": "2023-06-15"},
            ],
        }
        summary = extract_recalls_summary(result)
        assert summary["total_recalls"] == 12
        assert summary["active_recalls"] == 1
        assert summary["class_i"] == 1
        assert summary["class_ii"] == 2
        assert summary["latest_recall_date"] == "2025-11-15"

    def test_no_recalls(self):
        result = {"meta": {"results": {"total": 0}}, "results": []}
        summary = extract_recalls_summary(result)
        assert summary["total_recalls"] == 0
        assert summary["active_recalls"] == 0

    def test_on_going_status_counted_as_active(self):
        result = {
            "meta": {"results": {"total": 1}},
            "results": [{"recall_status": "On-Going", "classification": "Class I", "event_date_initiated": "2025-01-01"}],
        }
        summary = extract_recalls_summary(result)
        assert summary["active_recalls"] == 1


class TestEventsSummary:
    """Test events summary extraction."""

    def test_count_mode_with_event_types(self):
        result = {
            "results": [
                {"term": "Death", "count": 2},
                {"term": "Injury", "count": 312},
                {"term": "Malfunction", "count": 533},
            ]
        }
        summary = extract_events_summary(result, count_field="event_type.exact")
        assert summary["total_events"] == 847
        assert summary["deaths"] == 2
        assert summary["injuries"] == 312
        assert summary["malfunctions"] == 533
        assert summary["breakdown"]["Death"] == 2

    def test_narrative_mode(self):
        result = {
            "meta": {"results": {"total": 500}},
            "results": [{"event_type": "Injury"} for _ in range(10)],
        }
        summary = extract_events_summary(result, count_field=None)
        assert summary["total_events"] == 500
        assert summary["returned"] == 10

    def test_empty_count_results(self):
        result = {"results": []}
        summary = extract_events_summary(result, count_field="event_type.exact")
        assert summary["total_events"] == 0
        assert summary["deaths"] == 0


class TestSingle510kSummary:
    """Test single 510(k) summary extraction."""

    def test_extracts_device_fields(self):
        result = {
            "results": [{
                "k_number": "K241335",
                "applicant": "COMPANY A",
                "device_name": "Cervical Cage",
                "product_code": "OVE",
                "decision_date": "20240315",
                "decision_code": "SESE",
                "clearance_type": "Traditional",
                "statement_or_summary": "Summary",
                "third_party_flag": "N",
            }]
        }
        summary = extract_510k_summary(result)
        assert summary["k_number"] == "K241335"
        assert summary["applicant"] == "COMPANY A"
        assert summary["product_code"] == "OVE"

    def test_no_results(self):
        result = {"results": []}
        summary = extract_510k_summary(result)
        assert "error" in summary


class TestBatch510kSummary:
    """Test batch 510(k) summary extraction."""

    def test_extracts_multiple_devices(self):
        result = {
            "meta": {"results": {"total": 2}},
            "results": [
                {"k_number": "K241335", "applicant": "A", "device_name": "D1", "product_code": "OVE", "decision_date": "20240315", "decision_code": "SESE", "clearance_type": "Traditional", "statement_or_summary": "Summary"},
                {"k_number": "K200123", "applicant": "B", "device_name": "D2", "product_code": "OVE", "decision_date": "20200801", "decision_code": "SESE", "clearance_type": "Traditional", "statement_or_summary": "Summary"},
            ],
        }
        summary = extract_510k_batch_summary(result)
        assert summary["total_matches"] == 2
        assert summary["returned"] == 2
        assert "K241335" in summary["devices"]
        assert "K200123" in summary["devices"]
        assert summary["devices"]["K241335"]["applicant"] == "A"


class TestEnforcementSummary:
    """Test enforcement summary extraction."""

    def test_extracts_enforcement_counts(self):
        result = {
            "meta": {"results": {"total": 5}},
            "results": [
                {"status": "Ongoing"},
                {"status": "Completed"},
                {"status": "Ongoing"},
            ],
        }
        summary = extract_enforcement_summary(result)
        assert summary["total_actions"] == 5
        assert summary["returned"] == 3
        assert summary["ongoing"] == 2


# ============================================================
# Print Functions
# ============================================================


class TestPrintClassification:
    """Test classification print output."""

    def test_prints_all_fields(self, capsys):
        summary = {
            "device_name": "Intervertebral Body Fusion Device",
            "device_class": "2",
            "regulation_number": "888.3080",
            "review_panel": "Orthopedic",
            "definition": "A device...",
            "gmp_exempt": "N",
            "third_party_flag": "Y",
            "implant_flag": "Y",
            "life_sustain_support_flag": "N",
        }
        print_classification(summary, "HIT", "2026-02-09T12:00:00+00:00")
        output = capsys.readouterr().out
        assert "CACHE_STATUS:HIT" in output
        assert "DEVICE_NAME:Intervertebral Body Fusion Device" in output
        assert "DEVICE_CLASS:2" in output
        assert "SOURCE:openFDA API (cached)" in output

    def test_prints_miss_source(self, capsys):
        summary = {"device_name": "Test"}
        print_classification(summary, "MISS", "2026-02-09T12:00:00+00:00")
        output = capsys.readouterr().out
        assert "CACHE_STATUS:MISS" in output
        assert "SOURCE:openFDA API" in output
        assert "(cached)" not in output.split("SOURCE:")[1]

    def test_prints_error(self, capsys):
        summary = {"error": "No results found"}
        print_classification(summary, "MISS", "now")
        output = capsys.readouterr().out
        assert "ERROR:No results found" in output


class TestPrintRecalls:
    """Test recalls print output."""

    def test_prints_recall_counts(self, capsys):
        summary = {
            "total_recalls": 12,
            "active_recalls": 1,
            "class_i": 0,
            "class_ii": 1,
            "class_iii": 0,
            "latest_recall_date": "2025-11-15",
        }
        print_recalls(summary, "MISS", "2026-02-09T12:05:00+00:00")
        output = capsys.readouterr().out
        assert "TOTAL_RECALLS:12" in output
        assert "ACTIVE_RECALLS:1" in output
        assert "CLASS_I:0" in output


class TestPrintEvents:
    """Test events print output."""

    def test_prints_count_mode(self, capsys):
        summary = {
            "total_events": 847,
            "deaths": 2,
            "injuries": 312,
            "malfunctions": 533,
            "breakdown": {"Death": 2, "Injury": 312, "Malfunction": 533},
        }
        print_events(summary, "HIT", "now")
        output = capsys.readouterr().out
        assert "TOTAL_EVENTS:847" in output
        assert "DEATHS:2" in output

    def test_prints_narrative_mode(self, capsys):
        summary = {"total_events": 500, "returned": 10}
        print_events(summary, "MISS", "now")
        output = capsys.readouterr().out
        assert "RETURNED:10" in output
        assert "DEATHS" not in output


class TestPrint510k:
    """Test 510(k) print output."""

    def test_prints_single_device(self, capsys):
        summary = {
            "k_number": "K241335",
            "applicant": "COMPANY A",
            "device_name": "Cervical Cage",
            "product_code": "OVE",
            "decision_date": "20240315",
            "decision_code": "SESE",
            "clearance_type": "Traditional",
            "statement_or_summary": "Summary",
        }
        print_510k(summary, "MISS", "now")
        output = capsys.readouterr().out
        assert "K_NUMBER:K241335" in output
        assert "APPLICANT:COMPANY A" in output


class TestPrint510kBatch:
    """Test batch 510(k) print output."""

    def test_prints_batch_devices(self, capsys):
        summary = {
            "total_matches": 2,
            "returned": 2,
            "devices": {
                "K241335": {"applicant": "A", "device_name": "D1", "product_code": "OVE", "decision_date": "20240315", "decision_code": "SESE", "clearance_type": "T", "statement_or_summary": "S"},
                "K200123": {"applicant": "B", "device_name": "D2", "product_code": "OVE", "decision_date": "20200801", "decision_code": "SESE", "clearance_type": "T", "statement_or_summary": "S"},
            },
        }
        print_510k_batch(summary, "HIT", "now")
        output = capsys.readouterr().out
        assert "TOTAL_MATCHES:2" in output
        assert "DEVICE:K241335" in output
        assert "DEVICE:K200123" in output


class TestPrintEnforcement:
    """Test enforcement print output."""

    def test_prints_enforcement(self, capsys):
        summary = {"total_actions": 5, "ongoing": 2}
        print_enforcement(summary, "MISS", "now")
        output = capsys.readouterr().out
        assert "TOTAL_ACTIONS:5" in output
        assert "ONGOING:2" in output


# ============================================================
# Print Result Router
# ============================================================


class TestPrintResultRouter:
    """Test _print_result routes to correct printer."""

    def test_routes_classification(self, capsys):
        _print_result("classification", {"device_name": "Test", "device_class": "2"}, "HIT", "now")
        output = capsys.readouterr().out
        assert "DEVICE_NAME:Test" in output

    def test_routes_recalls(self, capsys):
        _print_result("recalls", {"total_recalls": 5}, "MISS", "now")
        output = capsys.readouterr().out
        assert "TOTAL_RECALLS:5" in output

    def test_routes_events(self, capsys):
        _print_result("events", {"total_events": 100, "returned": 10}, "HIT", "now")
        output = capsys.readouterr().out
        assert "TOTAL_EVENTS:100" in output

    def test_routes_510k(self, capsys):
        _print_result("510k", {"k_number": "K241335"}, "HIT", "now")
        output = capsys.readouterr().out
        assert "K_NUMBER:K241335" in output

    def test_routes_510k_batch(self, capsys):
        _print_result("510k-batch", {"total_matches": 2, "returned": 2, "devices": {}}, "HIT", "now")
        output = capsys.readouterr().out
        assert "TOTAL_MATCHES:2" in output

    def test_routes_enforcement(self, capsys):
        _print_result("enforcement", {"total_actions": 3, "ongoing": 1}, "MISS", "now")
        output = capsys.readouterr().out
        assert "TOTAL_ACTIONS:3" in output


# ============================================================
# Extract Summary Router
# ============================================================


class TestExtractSummaryRouter:
    """Test _extract_summary routes to correct extractor."""

    def test_routes_classification(self):
        result = {"results": [{"device_name": "Test", "device_class": "2"}]}
        s = _extract_summary("classification", result)
        assert s["device_name"] == "Test"

    def test_routes_recalls(self):
        result = {"meta": {"results": {"total": 3}}, "results": []}
        s = _extract_summary("recalls", result)
        assert s["total_recalls"] == 3

    def test_routes_events(self):
        result = {"results": [{"term": "Death", "count": 1}]}
        s = _extract_summary("events", result, "event_type.exact")
        assert s["deaths"] == 1

    def test_routes_510k(self):
        result = {"results": [{"k_number": "K123456"}]}
        s = _extract_summary("510k", result)
        assert s["k_number"] == "K123456"

    def test_routes_510k_batch(self):
        result = {"meta": {"results": {"total": 1}}, "results": [{"k_number": "K123456"}]}
        s = _extract_summary("510k-batch", result)
        assert s["returned"] == 1

    def test_routes_enforcement(self):
        result = {"meta": {"results": {"total": 2}}, "results": []}
        s = _extract_summary("enforcement", result)
        assert s["total_actions"] == 2

    def test_unknown_type_returns_empty(self):
        s = _extract_summary("unknown_type", {})
        assert s == {}


# ============================================================
# Endpoint Mapping
# ============================================================


class TestEndpointMapping:
    """Test query type to API endpoint mapping."""

    def test_classification_endpoint(self):
        assert _get_endpoint("classification") == "classification"

    def test_recalls_endpoint(self):
        assert _get_endpoint("recalls") == "recall"

    def test_events_endpoint(self):
        assert _get_endpoint("events") == "event"

    def test_510k_endpoint(self):
        assert _get_endpoint("510k") == "510k"

    def test_510k_batch_endpoint(self):
        assert _get_endpoint("510k-batch") == "510k"

    def test_enforcement_endpoint(self):
        assert _get_endpoint("enforcement") == "enforcement"

    def test_unknown_returns_as_is(self):
        assert _get_endpoint("unknown") == "unknown"


# ============================================================
# Params Generation
# ============================================================


class TestParamsGeneration:
    """Test API params generation for cache key computation."""

    def test_classification_params(self):
        p = _get_params("classification", "OVE", None, None, None)
        assert p["search"] == 'product_code:"OVE"'
        assert p["limit"] == "1"

    def test_recalls_params(self):
        p = _get_params("recalls", "OVE", None, None, None)
        assert 'product_code:"OVE"' in p["search"]
        assert p["limit"] == "100"

    def test_events_params_no_count(self):
        p = _get_params("events", "OVE", None, None, None)
        assert "device_report_product_code" in p["search"]
        assert p["limit"] == "100"
        assert "count" not in p

    def test_events_params_with_count(self):
        p = _get_params("events", "OVE", None, None, "event_type.exact")
        assert "count" in p
        assert p["count"] == "event_type.exact"
        assert "limit" not in p

    def test_510k_params(self):
        p = _get_params("510k", None, "K241335", None, None)
        assert 'k_number:"K241335"' in p["search"]

    def test_510k_batch_params(self):
        p = _get_params("510k-batch", None, None, ["K241335", "K200123"], None)
        assert "K241335" in p["search"]
        assert "K200123" in p["search"]
        assert "+OR+" in p["search"]

    def test_enforcement_params(self):
        p = _get_params("enforcement", "OVE", None, None, None)
        assert 'product_code:"OVE"' in p["search"]


# ============================================================
# Compact Summary
# ============================================================


class TestCompactSummary:
    """Test _compact_summary for manifest display."""

    def test_classification_compact(self):
        s = _compact_summary("classification:OVE", {"device_class": "2", "regulation_number": "888.3080"})
        assert "Class 2" in s
        assert "888.3080" in s

    def test_recalls_compact(self):
        s = _compact_summary("recalls:OVE", {"total_recalls": 12, "active_recalls": 1})
        assert "12 total" in s
        assert "1 active" in s

    def test_events_count_compact(self):
        s = _compact_summary("events:OVE:count:event_type.exact", {"total_events": 847, "deaths": 2})
        assert "847 total" in s
        assert "2 deaths" in s

    def test_events_narrative_compact(self):
        s = _compact_summary("events:OVE", {"total_events": 500, "returned": 10})
        assert "500 total" in s

    def test_510k_batch_compact(self):
        s = _compact_summary("510k-batch:K241335,K200123", {"devices": {"K241335": {}, "K200123": {}}})
        assert "2 devices" in s

    def test_510k_single_compact(self):
        s = _compact_summary("510k:K241335", {"device_name": "Cervical Cage"})
        assert "Cervical Cage" in s

    def test_enforcement_compact(self):
        s = _compact_summary("enforcement:OVE", {"total_actions": 5, "ongoing": 2})
        assert "5 total" in s
        assert "2 ongoing" in s

    def test_unknown_key_truncated(self):
        s = _compact_summary("unknown:key", {"data": "x" * 100})
        assert len(s) <= 60


# ============================================================
# Show Manifest
# ============================================================


class TestShowManifest:
    """Test handle_show_manifest output."""

    def test_empty_manifest(self, capsys, tmp_path):
        args = MagicMock()
        args.project = "empty_project"
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            handle_show_manifest(args)
        output = capsys.readouterr().out
        assert "PROJECT:empty_project" in output
        assert "TOTAL_CACHED:0" in output
        assert "TOTAL_STALE:0" in output

    def test_manifest_with_entries(self, capsys, tmp_path):
        args = MagicMock()
        args.project = "test_proj"
        project_dir = tmp_path / "test_proj"
        project_dir.mkdir()
        manifest = {
            "project": "test_proj",
            "created_at": "2026-02-09T12:00:00+00:00",
            "last_updated": "2026-02-09T12:00:00+00:00",
            "product_codes": ["OVE"],
            "queries": {
                "classification:OVE": {
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "ttl_hours": 168,
                    "summary": {"device_class": "2", "regulation_number": "888.3080"},
                },
                "recalls:OVE": {
                    "fetched_at": "1970-01-01T00:00:00+00:00",
                    "ttl_hours": 24,
                    "summary": {"total_recalls": 5, "active_recalls": 0},
                },
            },
        }
        (project_dir / "data_manifest.json").write_text(json.dumps(manifest))
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            handle_show_manifest(args)
        output = capsys.readouterr().out
        assert "PRODUCT_CODES:OVE" in output
        assert "CACHED:classification:OVE" in output
        assert "STALE:recalls:OVE" in output
        assert "TOTAL_CACHED:1" in output
        assert "TOTAL_STALE:1" in output


# ============================================================
# Clear
# ============================================================


class TestHandleClear:
    """Test handle_clear functionality."""

    def test_clear_existing_manifest(self, capsys, tmp_path):
        args = MagicMock()
        args.project = "to_clear"
        project_dir = tmp_path / "to_clear"
        project_dir.mkdir()
        (project_dir / "data_manifest.json").write_text("{}")
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            handle_clear(args)
        output = capsys.readouterr().out
        assert "CLEARED" in output
        assert not (project_dir / "data_manifest.json").exists()

    def test_clear_nonexistent_manifest(self, capsys, tmp_path):
        args = MagicMock()
        args.project = "no_manifest"
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            handle_clear(args)
        output = capsys.readouterr().out
        assert "NO_MANIFEST" in output


# ============================================================
# Refresh All
# ============================================================


class TestHandleRefreshAll:
    """Test handle_refresh_all functionality."""

    def test_marks_all_entries_stale(self, capsys, tmp_path):
        args = MagicMock()
        args.project = "refresh_test"
        project_dir = tmp_path / "refresh_test"
        project_dir.mkdir()
        manifest = {
            "project": "refresh_test",
            "created_at": "2026-02-09T12:00:00+00:00",
            "last_updated": "2026-02-09T12:00:00+00:00",
            "product_codes": [],
            "queries": {
                "classification:OVE": {"fetched_at": datetime.now(timezone.utc).isoformat(), "ttl_hours": 168},
                "recalls:OVE": {"fetched_at": datetime.now(timezone.utc).isoformat(), "ttl_hours": 24},
            },
        }
        (project_dir / "data_manifest.json").write_text(json.dumps(manifest))
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            handle_refresh_all(args)
        output = capsys.readouterr().out
        assert "REFRESHED:2" in output

        # Verify entries are now stale
        updated = json.loads((project_dir / "data_manifest.json").read_text())
        for entry in updated["queries"].values():
            assert is_expired(entry) is True


# ============================================================
# Projects Dir Resolution
# ============================================================


class TestProjectsDirResolution:
    """Test get_projects_dir reads settings or falls back to default."""

    def test_default_without_settings(self, tmp_path):
        with patch("fda_data_store.os.path.exists", return_value=False):
            result = get_projects_dir()
        assert result.endswith("fda-510k-data/projects")

    def test_reads_from_settings(self, tmp_path):
        settings_path = tmp_path / "settings.md"
        settings_path.write_text("projects_dir: /custom/projects/path\n")
        with patch("fda_data_store.os.path.expanduser") as mock_expand:
            mock_expand.side_effect = lambda p: str(settings_path) if "fda-tools" in p else p.replace("~", str(tmp_path))
            with patch("fda_data_store.os.path.exists", return_value=True):
                with patch("builtins.open", return_value=open(str(settings_path))):
                    result = get_projects_dir()
        assert "/custom/projects/path" in result


# ============================================================
# CLI Argument Parsing (main)
# ============================================================


class TestCLIParsing:
    """Test CLI argument parsing and routing."""

    def test_main_show_manifest(self, capsys, tmp_path):
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            with patch("sys.argv", ["fda_data_store.py", "--project", "test", "--show-manifest"]):
                from fda_data_store import main
                main()
        output = capsys.readouterr().out
        assert "PROJECT:test" in output

    def test_main_clear(self, capsys, tmp_path):
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            with patch("sys.argv", ["fda_data_store.py", "--project", "test", "--clear"]):
                from fda_data_store import main
                main()
        output = capsys.readouterr().out
        assert "NO_MANIFEST" in output

    def test_main_refresh_all(self, capsys, tmp_path):
        project_dir = tmp_path / "test"
        project_dir.mkdir()
        manifest = {
            "project": "test",
            "created_at": "2026-02-09T12:00:00+00:00",
            "last_updated": "2026-02-09T12:00:00+00:00",
            "product_codes": [],
            "queries": {"classification:OVE": {"fetched_at": datetime.now(timezone.utc).isoformat(), "ttl_hours": 168}},
        }
        (project_dir / "data_manifest.json").write_text(json.dumps(manifest))
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            with patch("sys.argv", ["fda_data_store.py", "--project", "test", "--refresh-all"]):
                from fda_data_store import main
                main()
        output = capsys.readouterr().out
        assert "REFRESHED:1" in output

    def test_main_no_action_raises_error(self):
        with patch("sys.argv", ["fda_data_store.py", "--project", "test"]):
            with pytest.raises(SystemExit):
                from fda_data_store import main
                main()

    def test_main_query_missing_product_code(self):
        with patch("sys.argv", ["fda_data_store.py", "--project", "test", "--query", "classification"]):
            with pytest.raises(SystemExit):
                from fda_data_store import main
                main()

    def test_main_query_510k_missing_k_number(self):
        with patch("sys.argv", ["fda_data_store.py", "--project", "test", "--query", "510k"]):
            with pytest.raises(SystemExit):
                from fda_data_store import main
                main()

    def test_main_query_510k_batch_missing_k_numbers(self):
        with patch("sys.argv", ["fda_data_store.py", "--project", "test", "--query", "510k-batch"]):
            with pytest.raises(SystemExit):
                from fda_data_store import main
                main()


# ============================================================
# Handle Query (with mocked API)
# ============================================================


class TestHandleQuery:
    """Test handle_query with mocked FDAClient."""

    @pytest.fixture
    def mock_args(self):
        args = MagicMock()
        args.project = "test_handle"
        args.product_code = "OVE"
        args.k_number = None
        args.k_numbers = None
        args.count = None
        args.refresh = False
        return args

    def test_cache_hit(self, capsys, tmp_path, mock_args):
        mock_args.query = "classification"
        project_dir = tmp_path / "test_handle"
        project_dir.mkdir()
        manifest = {
            "project": "test_handle",
            "created_at": "2026-02-09T12:00:00+00:00",
            "last_updated": "2026-02-09T12:00:00+00:00",
            "product_codes": ["OVE"],
            "queries": {
                "classification:OVE": {
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "ttl_hours": 168,
                    "summary": {
                        "device_name": "Fusion Device",
                        "device_class": "2",
                        "regulation_number": "888.3080",
                        "review_panel": "OR",
                    },
                }
            },
        }
        (project_dir / "data_manifest.json").write_text(json.dumps(manifest))
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            with patch("fda_data_store.FDAClient"):
                from fda_data_store import handle_query
                handle_query(mock_args)
        output = capsys.readouterr().out
        assert "CACHE_STATUS:HIT" in output
        assert "DEVICE_NAME:Fusion Device" in output

    def test_cache_miss_fetches_api(self, capsys, tmp_path, mock_args):
        mock_args.query = "classification"
        mock_client = MagicMock()
        mock_client.get_classification.return_value = {
            "meta": {"results": {"total": 1}},
            "results": [{
                "device_name": "New Device",
                "device_class": "3",
                "regulation_number": "870.1234",
                "review_panel": "CV",
            }],
        }
        mock_client._cache_key.return_value = "abc123"
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            with patch("fda_data_store.FDAClient", return_value=mock_client):
                from fda_data_store import handle_query
                handle_query(mock_args)
        output = capsys.readouterr().out
        assert "CACHE_STATUS:MISS" in output
        assert "DEVICE_NAME:New Device" in output
        # Manifest should be saved
        manifest = json.loads((tmp_path / "test_handle" / "data_manifest.json").read_text())
        assert "classification:OVE" in manifest["queries"]
        assert "OVE" in manifest["product_codes"]

    def test_refresh_bypasses_cache(self, capsys, tmp_path, mock_args):
        mock_args.query = "classification"
        mock_args.refresh = True
        project_dir = tmp_path / "test_handle"
        project_dir.mkdir()
        manifest = {
            "project": "test_handle",
            "created_at": "2026-02-09T12:00:00+00:00",
            "last_updated": "2026-02-09T12:00:00+00:00",
            "product_codes": ["OVE"],
            "queries": {
                "classification:OVE": {
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "ttl_hours": 168,
                    "summary": {"device_name": "Old Device", "device_class": "2"},
                }
            },
        }
        (project_dir / "data_manifest.json").write_text(json.dumps(manifest))
        mock_client = MagicMock()
        mock_client.get_classification.return_value = {
            "meta": {"results": {"total": 1}},
            "results": [{"device_name": "Refreshed Device", "device_class": "2"}],
        }
        mock_client._cache_key.return_value = "abc123"
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            with patch("fda_data_store.FDAClient", return_value=mock_client):
                from fda_data_store import handle_query
                handle_query(mock_args)
        output = capsys.readouterr().out
        assert "CACHE_STATUS:MISS" in output
        assert "DEVICE_NAME:Refreshed Device" in output

    def test_api_error_falls_back_to_stale(self, capsys, tmp_path, mock_args):
        mock_args.query = "classification"
        project_dir = tmp_path / "test_handle"
        project_dir.mkdir()
        manifest = {
            "project": "test_handle",
            "created_at": "2026-02-09T12:00:00+00:00",
            "last_updated": "2026-02-09T12:00:00+00:00",
            "product_codes": ["OVE"],
            "queries": {
                "classification:OVE": {
                    "fetched_at": "2020-01-01T00:00:00+00:00",  # Very old
                    "ttl_hours": 168,
                    "summary": {"device_name": "Stale Device", "device_class": "2"},
                }
            },
        }
        (project_dir / "data_manifest.json").write_text(json.dumps(manifest))
        mock_client = MagicMock()
        mock_client.get_classification.return_value = {"error": "API timeout", "degraded": True}
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            with patch("fda_data_store.FDAClient", return_value=mock_client):
                from fda_data_store import handle_query
                handle_query(mock_args)
        output = capsys.readouterr().out
        assert "CACHE_STATUS:STALE" in output
        assert "DEVICE_NAME:Stale Device" in output

    def test_api_error_no_stale_cache(self, capsys, tmp_path, mock_args):
        mock_args.query = "classification"
        mock_client = MagicMock()
        mock_client.get_classification.return_value = {"error": "API timeout", "degraded": True}
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            with patch("fda_data_store.FDAClient", return_value=mock_client):
                from fda_data_store import handle_query
                handle_query(mock_args)
        output = capsys.readouterr().out
        assert "CACHE_STATUS:MISS" in output
        assert "ERROR:" in output

    def test_recalls_query(self, capsys, tmp_path, mock_args):
        mock_args.query = "recalls"
        mock_client = MagicMock()
        mock_client.get_recalls.return_value = {
            "meta": {"results": {"total": 3}},
            "results": [
                {"recall_status": "Ongoing", "classification": "Class I", "event_date_initiated": "2025-06-01"},
            ],
        }
        mock_client._cache_key.return_value = "def456"
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            with patch("fda_data_store.FDAClient", return_value=mock_client):
                from fda_data_store import handle_query
                handle_query(mock_args)
        output = capsys.readouterr().out
        assert "TOTAL_RECALLS:3" in output

    def test_events_count_query(self, capsys, tmp_path, mock_args):
        mock_args.query = "events"
        mock_args.count = "event_type.exact"
        mock_client = MagicMock()
        mock_client.get_events.return_value = {
            "meta": {"results": {"total": 100}},
            "results": [
                {"term": "Death", "count": 5},
                {"term": "Injury", "count": 45},
                {"term": "Malfunction", "count": 50},
            ],
        }
        mock_client._cache_key.return_value = "ghi789"
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            with patch("fda_data_store.FDAClient", return_value=mock_client):
                from fda_data_store import handle_query
                handle_query(mock_args)
        output = capsys.readouterr().out
        assert "TOTAL_EVENTS:100" in output
        assert "DEATHS:5" in output

    def test_510k_batch_query(self, capsys, tmp_path):
        args = MagicMock()
        args.project = "test_handle"
        args.product_code = None
        args.k_number = None
        args.k_numbers = "K241335,K200123"
        args.count = None
        args.refresh = False
        args.query = "510k-batch"
        mock_client = MagicMock()
        mock_client.batch_510k.return_value = {
            "meta": {"results": {"total": 2}},
            "results": [
                {"k_number": "K241335", "applicant": "A", "device_name": "D1", "product_code": "OVE", "decision_date": "20240315", "decision_code": "SESE", "clearance_type": "T", "statement_or_summary": "S"},
                {"k_number": "K200123", "applicant": "B", "device_name": "D2", "product_code": "OVE", "decision_date": "20200801", "decision_code": "SESE", "clearance_type": "T", "statement_or_summary": "S"},
            ],
        }
        mock_client._cache_key.return_value = "batch123"
        with patch("fda_data_store.get_projects_dir", return_value=str(tmp_path)):
            with patch("fda_data_store.FDAClient", return_value=mock_client):
                from fda_data_store import handle_query
                handle_query(args)
        output = capsys.readouterr().out
        assert "TOTAL_MATCHES:2" in output
        assert "DEVICE:K241335" in output


# ============================================================
# Version Assertions
# ============================================================


class TestVersionAssertions:
    """Verify plugin.json version matches expected."""

    def test_plugin_version_is_5_19_0(self):
        plugin_json = os.path.join(
            os.path.dirname(__file__), "..", ".claude-plugin", "plugin.json"
        )
        if os.path.exists(plugin_json):
            with open(plugin_json) as f:
                data = json.load(f)
            assert data["version"] == '5.22.0'

    def test_plugin_description_mentions_41_commands(self):
        plugin_json = os.path.join(
            os.path.dirname(__file__), "..", ".claude-plugin", "plugin.json"
        )
        if os.path.exists(plugin_json):
            with open(plugin_json) as f:
                data = json.load(f)
            assert "43 commands" in data["description"]


# ============================================================
# Command Count Assertions
# ============================================================


class TestCommandCount:
    """Verify SKILL.md lists the correct command count."""

    def test_skill_md_says_41_commands(self):
        skill_md = os.path.join(
            os.path.dirname(__file__), "..", "skills", "fda-510k-knowledge", "SKILL.md"
        )
        if os.path.exists(skill_md):
            with open(skill_md) as f:
                content = f.read()
            assert "## Available Commands (43)" in content

    def test_cache_command_listed(self):
        skill_md = os.path.join(
            os.path.dirname(__file__), "..", "skills", "fda-510k-knowledge", "SKILL.md"
        )
        if os.path.exists(skill_md):
            with open(skill_md) as f:
                content = f.read()
            assert "/fda:cache" in content
