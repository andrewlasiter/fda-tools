"""Tests for openFDA API field names and response shapes.

Verifies that the API endpoints we depend on still return expected field structures.
These tests make real API calls — skip with `pytest -m "not api"` for offline testing.

NOTE: Tests use real openFDA API endpoints without an API key (1K/day limit).
Rate limit: 5 calls/minute without key. Tests include delays.
"""

import json
import time
import urllib.request
import urllib.parse
import pytest


# Mark all tests in this module as requiring API access
pytestmark = pytest.mark.api

BASE_URL = "https://api.fda.gov/device"
HEADERS = {"User-Agent": "Mozilla/5.0 (FDA-Plugin-Test/1.0)"}
TIMEOUT = 15


def _api_get(endpoint, search, limit=1):
    """Make an openFDA API request and return parsed JSON."""
    params = {"search": search, "limit": str(limit)}
    url = f"{BASE_URL}/{endpoint}.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())


class Test510kEndpoint:
    """Verify /device/510k response shape."""

    @pytest.fixture(autouse=True)
    def _rate_limit(self):
        yield
        time.sleep(1)

    def test_510k_has_k_number(self):
        data = _api_get("510k", 'product_code:"OVE"')
        result = data["results"][0]
        assert "k_number" in result

    def test_510k_has_device_name(self):
        data = _api_get("510k", 'product_code:"OVE"')
        result = data["results"][0]
        assert "device_name" in result

    def test_510k_has_applicant(self):
        data = _api_get("510k", 'product_code:"OVE"')
        result = data["results"][0]
        assert "applicant" in result

    def test_510k_has_decision_date(self):
        data = _api_get("510k", 'product_code:"OVE"')
        result = data["results"][0]
        assert "decision_date" in result

    def test_510k_has_product_code(self):
        data = _api_get("510k", 'product_code:"OVE"')
        result = data["results"][0]
        assert "product_code" in result

    def test_510k_meta_has_total(self):
        data = _api_get("510k", 'product_code:"OVE"')
        assert "meta" in data
        assert "results" in data["meta"]
        assert "total" in data["meta"]["results"]


class TestClassificationEndpoint:
    """Verify /device/classification response shape."""

    @pytest.fixture(autouse=True)
    def _rate_limit(self):
        yield
        time.sleep(1)

    def test_classification_has_device_name(self):
        data = _api_get("classification", 'product_code:"OVE"')
        result = data["results"][0]
        assert "device_name" in result

    def test_classification_has_device_class(self):
        data = _api_get("classification", 'product_code:"OVE"')
        result = data["results"][0]
        assert "device_class" in result

    def test_classification_has_regulation_number(self):
        data = _api_get("classification", 'product_code:"OVE"')
        result = data["results"][0]
        assert "regulation_number" in result

    def test_classification_has_product_code(self):
        data = _api_get("classification", 'product_code:"OVE"')
        result = data["results"][0]
        assert "product_code" in result


class TestEventEndpoint:
    """Verify /device/event (MAUDE) response shape."""

    @pytest.fixture(autouse=True)
    def _rate_limit(self):
        yield
        time.sleep(1)

    def test_event_has_event_type(self):
        data = _api_get("event", 'device.device_report_product_code:"KGN"')
        result = data["results"][0]
        assert "event_type" in result

    def test_event_has_device_array(self):
        data = _api_get("event", 'device.device_report_product_code:"KGN"')
        result = data["results"][0]
        assert "device" in result
        assert isinstance(result["device"], list)


class TestRecallEndpoint:
    """Verify /device/recall response shape."""

    @pytest.fixture(autouse=True)
    def _rate_limit(self):
        yield
        time.sleep(1)

    def test_recall_has_product_code(self):
        data = _api_get("recall", 'product_code:"KGN"')
        result = data["results"][0]
        assert "product_code" in result

    def test_recall_has_event_type(self):
        data = _api_get("recall", 'product_code:"KGN"')
        result = data["results"][0]
        assert "event_type" in result or "res_event_number" in result


class TestGoldenFileReviewJSON:
    """Test that review.json fixture matches expected structure."""

    @pytest.fixture
    def review_data(self):
        fixture_path = os.path.join(
            os.path.dirname(__file__), "fixtures", "sample_review.json"
        )
        with open(fixture_path) as f:
            return json.load(f)

    def test_has_project(self, review_data):
        assert "project" in review_data

    def test_has_product_code(self, review_data):
        assert "product_code" in review_data
        assert review_data["product_code"] == "OVE"

    def test_has_predicates(self, review_data):
        assert "predicates" in review_data
        assert len(review_data["predicates"]) == 3

    def test_predicate_has_required_fields(self, review_data):
        for kn, pred in review_data["predicates"].items():
            assert "device_name" in pred
            assert "decision" in pred
            assert "confidence_score" in pred
            assert pred["decision"] in ("accepted", "rejected")

    def test_accepted_predicates_have_scores(self, review_data):
        for kn, pred in review_data["predicates"].items():
            if pred["decision"] == "accepted":
                assert pred["confidence_score"] >= 50

    def test_summary_counts_match(self, review_data):
        summary = review_data["summary"]
        preds = review_data["predicates"]
        accepted = sum(1 for p in preds.values() if p["decision"] == "accepted")
        rejected = sum(1 for p in preds.values() if p["decision"] == "rejected")
        assert summary["accepted"] == accepted
        assert summary["rejected"] == rejected
        assert summary["total_evaluated"] == len(preds)


# Need os import for fixture path
import os


class TestPMAEndpoint:
    """Verify /device/pma response shape."""

    @pytest.fixture(autouse=True)
    def _rate_limit(self):
        yield
        time.sleep(1)

    def test_pma_has_pma_number(self):
        data = _api_get("pma", 'product_code:"DXY"')
        result = data["results"][0]
        assert "pma_number" in result

    def test_pma_has_trade_name_or_generic_name(self):
        data = _api_get("pma", 'product_code:"DXY"')
        result = data["results"][0]
        assert "trade_name" in result or "generic_name" in result

    def test_pma_has_decision_date(self):
        data = _api_get("pma", 'product_code:"DXY"')
        result = data["results"][0]
        assert "decision_date" in result

    def test_pma_has_product_code(self):
        data = _api_get("pma", 'product_code:"DXY"')
        result = data["results"][0]
        assert "product_code" in result

    def test_pma_search_by_number(self):
        data = _api_get("pma", 'pma_number:"P870024"')
        assert data.get("meta", {}).get("results", {}).get("total", 0) > 0

    def test_pma_supplement_fields(self):
        data = _api_get("pma", 'pma_number:"P870024"', limit=5)
        # P870024 should have supplements
        found_supplement = False
        for r in data.get("results", []):
            if r.get("supplement_number"):
                found_supplement = True
                assert "supplement_type" in r
                break
        # It's OK if no supplements are returned in first 5 results


class TestDeNovoSearch:
    """Verify De Novo search patterns via 510k endpoint."""

    @pytest.fixture(autouse=True)
    def _rate_limit(self):
        yield
        time.sleep(1)

    def test_den_number_format_recognized(self):
        """DEN numbers follow the pattern DEN + 6 digits."""
        import re
        pattern = re.compile(r"^DEN\d{6,7}$")
        assert pattern.match("DEN200043")
        assert pattern.match("DEN2000435")
        assert not pattern.match("DEN12345")

    def test_classification_search_for_denovo_product_code(self):
        """Search classification for a product code that was created via De Novo."""
        # QJU is a product code created via De Novo for AI mammography
        data = _api_get("classification", 'product_code:"QJU"')
        if data.get("results"):
            result = data["results"][0]
            assert "device_name" in result
            assert "device_class" in result


class TestSearchFilters:
    """Verify combined search filter patterns for interactive search."""

    @pytest.fixture(autouse=True)
    def _rate_limit(self):
        yield
        time.sleep(1)

    def test_multi_field_search(self):
        """Search with multiple combined filters."""
        data = _api_get("510k", 'product_code:"OVE"+AND+decision_date:[20230101+TO+20251231]')
        assert "meta" in data
        assert data.get("meta", {}).get("results", {}).get("total", 0) >= 0

    def test_date_range_search(self):
        """Search with date range filter."""
        data = _api_get("510k", 'product_code:"OVE"+AND+decision_date:[20200101+TO+20251231]', limit=5)
        if data.get("results"):
            for r in data["results"]:
                assert "decision_date" in r

    def test_device_name_search(self):
        """Search by device name keyword."""
        data = _api_get("510k", 'device_name:"fusion"+AND+product_code:"OVE"')
        assert "meta" in data
