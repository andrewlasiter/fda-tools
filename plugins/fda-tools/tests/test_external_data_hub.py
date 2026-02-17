"""
Comprehensive test suite for external_data_hub.py -- External Data Integration Hub.

Tests cover:
    - ClinicalTrials.gov API integration with response parsing
    - PubMed E-utilities API integration (esearch + esummary)
    - USPTO PatentsView API integration
    - Rate limiter token bucket algorithm under load
    - Cache behavior (TTL, expiry, key generation)
    - PMA context enrichment
    - Error handling and graceful degradation
    - Hub statistics and source management

Target: 15+ tests with comprehensive mocking (no network access).
Related to: FDA-58 (GAP-035) -- PubMed/ClinicalTrials.gov integration testing gap.
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


# ============================================================
# Mock response data for all 3 external APIs
# ============================================================

MOCK_CLINICALTRIALS_RESPONSE = {
    "totalCount": 2,
    "studies": [
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT05001234",
                    "briefTitle": "Study of Next Generation Sequencing Device",
                },
                "statusModule": {
                    "overallStatus": "RECRUITING",
                    "startDateStruct": {"date": "2024-01-15"},
                },
                "designModule": {
                    "studyType": "INTERVENTIONAL",
                    "enrollmentInfo": {"count": 500},
                },
                "descriptionModule": {
                    "briefSummary": "A clinical trial evaluating the safety and effectiveness of a next generation sequencing diagnostic device for oncology applications."
                },
            },
        },
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT05002345",
                    "briefTitle": "Companion Diagnostic Validation Study",
                },
                "statusModule": {
                    "overallStatus": "COMPLETED",
                    "startDateStruct": {"date": "2023-06-01"},
                },
                "designModule": {
                    "studyType": "OBSERVATIONAL",
                    "enrollmentInfo": {"count": 300},
                },
                "descriptionModule": {
                    "briefSummary": "Validation study for companion diagnostic device."
                },
            },
        },
    ],
}

MOCK_PUBMED_ESEARCH_RESPONSE = {
    "esearchresult": {
        "count": "10",
        "idlist": ["39012345", "39012346", "39012347"],
    },
}

MOCK_PUBMED_ESUMMARY_RESPONSE = {
    "result": {
        "39012345": {
            "uid": "39012345",
            "title": "Safety and Efficacy of Next Generation Sequencing Devices in Clinical Oncology",
            "authors": [
                {"name": "Smith J"},
                {"name": "Johnson A"},
                {"name": "Williams R"},
            ],
            "fulljournalname": "Journal of Medical Devices",
            "pubdate": "2024 Jan",
            "elocationid": "10.1234/jmd.2024.001",
        },
        "39012346": {
            "uid": "39012346",
            "title": "Regulatory Perspectives on Companion Diagnostics",
            "authors": [
                {"name": "Brown K"},
                {"name": "Davis M"},
            ],
            "fulljournalname": "Regulatory Science Review",
            "pubdate": "2024 Feb",
            "elocationid": "10.5678/rsr.2024.002",
        },
        "39012347": {
            "uid": "39012347",
            "title": "Clinical Validation of NGS-Based Diagnostic Tests",
            "authors": [
                {"name": "Martinez L"},
            ],
            "fulljournalname": "Clinical Chemistry",
            "pubdate": "2023 Dec",
            "elocationid": "10.9012/cc.2023.003",
        },
    },
}

MOCK_PATENTS_RESPONSE = {
    "patents": [
        {
            "patent_number": "US12345678",
            "patent_title": "Methods and Systems for Next Generation Sequencing Analysis",
            "patent_abstract": "The present invention relates to methods and systems for analyzing next generation sequencing data for diagnostic purposes. The invention provides improved accuracy and speed...",
            "patent_date": "2024-01-15",
            "assignees": [
                {"assignee_organization": "Foundation Medicine, Inc."},
            ],
        },
        {
            "patent_number": "US12345679",
            "patent_title": "Companion Diagnostic Device for Cancer Treatment",
            "patent_abstract": "A companion diagnostic device for identifying patients who may benefit from targeted cancer therapies...",
            "patent_date": "2023-11-20",
            "assignees": [
                {"assignee_organization": "Genomic Health, Inc."},
                {"assignee_organization": "Roche Diagnostics"},
            ],
        },
    ],
    "total_patent_count": 15,
}


def _create_mock_pma_store():
    """Create mock PMADataStore with sample PMA data."""
    store = MagicMock()
    store.get_pma_data.return_value = {
        "pma_number": "P170019",
        "device_name": "FoundationOne CDx",
        "applicant": "FOUNDATION MEDICINE, INC.",
        "product_code": "NMH",
    }
    return store


# ============================================================
# Test ClinicalTrials.gov Integration (5 tests)
# ============================================================

class TestClinicalTrialsSource:
    """Test suite for ClinicalTrials.gov API integration."""

    def setup_method(self):
        from external_data_hub import ClinicalTrialsSource  # type: ignore
        self.tmpdir = tempfile.mkdtemp()
        self.source = ClinicalTrialsSource(cache_dir=Path(self.tmpdir) / "ct")

    @patch("external_data_hub.ClinicalTrialsSource._http_get")
    def test_search_success(self, mock_get):
        """Test successful ClinicalTrials.gov search with response parsing."""
        mock_get.return_value = MOCK_CLINICALTRIALS_RESPONSE

        result = self.source.search("next generation sequencing", max_results=10)

        assert result["source"] == "ClinicalTrials.gov"
        assert result["api_version"] == "v2"
        assert result["total_results"] == 2
        assert result["returned_results"] == 2
        assert len(result["trials"]) == 2

        # Verify first trial parsing
        trial1 = result["trials"][0]
        assert trial1["nct_id"] == "NCT05001234"
        assert trial1["title"] == "Study of Next Generation Sequencing Device"
        assert trial1["status"] == "RECRUITING"
        assert trial1["start_date"] == "2024-01-15"
        assert trial1["study_type"] == "INTERVENTIONAL"
        assert trial1["enrollment"] == 500
        assert "safety and effectiveness" in trial1["brief_summary"]

    @patch("external_data_hub.ClinicalTrialsSource._http_get")
    def test_search_with_status_filter(self, mock_get):
        """Test search with status filter applied."""
        mock_get.return_value = MOCK_CLINICALTRIALS_RESPONSE

        result = self.source.search(
            "diagnostic device",
            max_results=5,
            status_filter="RECRUITING"
        )

        # Verify filter was passed to API
        call_args = mock_get.call_args[0][0]
        assert "filter.overallStatus=RECRUITING" in call_args

    @patch("external_data_hub.ClinicalTrialsSource._http_get")
    def test_api_error_handling(self, mock_get):
        """Test graceful handling of API errors."""
        mock_get.return_value = {
            "error": "HTTP 500: Internal Server Error",
            "status_code": 500,
        }

        result = self.source.search("test query")

        assert result["total_results"] == 0
        assert result["trials"] == []
        assert "error" in result
        assert "500" in result["error"]

    def test_cache_key_generation(self):
        """Test cache key generation is deterministic."""
        params1 = {"query.term": "device", "pageSize": "10"}
        params2 = {"pageSize": "10", "query.term": "device"}
        params3 = {"query.term": "different", "pageSize": "10"}

        key1 = self.source._cache_key(params1)
        key2 = self.source._cache_key(params2)
        key3 = self.source._cache_key(params3)

        # Same params (different order) should give same key
        assert key1 == key2
        # Different params should give different key
        assert key1 != key3

    @patch("external_data_hub.ClinicalTrialsSource._http_get")
    def test_caching_behavior(self, mock_get):
        """Test that results are cached and retrieved from cache."""
        mock_get.return_value = MOCK_CLINICALTRIALS_RESPONSE

        # First call - should hit API
        result1 = self.source.search("device test", max_results=5)
        assert "_from_cache" not in result1
        assert mock_get.call_count == 1

        # Second call - should retrieve from cache
        result2 = self.source.search("device test", max_results=5)
        assert result2["_from_cache"] is True
        assert mock_get.call_count == 1  # No additional API call


# ============================================================
# Test PubMed Integration (5 tests)
# ============================================================

class TestPubMedSource:
    """Test suite for PubMed E-utilities API integration."""

    def setup_method(self):
        from external_data_hub import PubMedSource  # type: ignore
        self.tmpdir = tempfile.mkdtemp()
        self.source = PubMedSource(cache_dir=Path(self.tmpdir) / "pubmed")

    @patch("external_data_hub.PubMedSource._http_get")
    def test_search_success(self, mock_get):
        """Test successful PubMed search with two-step API flow."""
        # Mock esearch, then esummary
        mock_get.side_effect = [
            MOCK_PUBMED_ESEARCH_RESPONSE,
            MOCK_PUBMED_ESUMMARY_RESPONSE,
        ]

        result = self.source.search("medical device safety", max_results=10)

        assert result["source"] == "PubMed E-utilities"
        assert result["api_version"] == "v2.0"
        assert result["total_results"] == 10
        assert result["returned_results"] == 3
        assert len(result["articles"]) == 3

        # Verify article parsing
        article1 = result["articles"][0]
        assert article1["pmid"] == "39012345"
        assert "Next Generation Sequencing" in article1["title"]
        assert len(article1["authors"]) == 3
        assert article1["authors"][0] == "Smith J"
        assert article1["journal"] == "Journal of Medical Devices"
        assert article1["pub_date"] == "2024 Jan"
        assert article1["doi"] == "10.1234/jmd.2024.001"

    @patch("external_data_hub.PubMedSource._http_get")
    def test_no_results(self, mock_get):
        """Test PubMed search with no results."""
        mock_get.return_value = {
            "esearchresult": {"count": "0", "idlist": []},
        }

        result = self.source.search("nonexistent device query")

        assert result["total_results"] == 0
        assert result["returned_results"] == 0
        assert result["articles"] == []

    @patch("external_data_hub.PubMedSource._http_get")
    def test_api_key_inclusion(self, mock_get):
        """Test that API key is included when provided."""
        from external_data_hub import PubMedSource  # type: ignore
        source_with_key = PubMedSource(
            cache_dir=Path(self.tmpdir) / "pubmed_key",
            api_key="test_api_key_12345"
        )

        mock_get.return_value = {
            "esearchresult": {"count": "0", "idlist": []},
        }

        source_with_key.search("test query")

        # Verify API key was included in URL
        call_args = mock_get.call_args[0][0]
        assert "api_key=test_api_key_12345" in call_args

    @patch("external_data_hub.PubMedSource._http_get")
    def test_esearch_error_handling(self, mock_get):
        """Test handling of esearch API errors."""
        mock_get.return_value = {
            "error": "HTTP 429: Too Many Requests",
        }

        result = self.source.search("test query")

        assert result["total_results"] == 0
        assert "error" in result

    @patch("external_data_hub.PubMedSource._http_get")
    def test_esummary_error_handling(self, mock_get):
        """Test handling of esummary API errors."""
        # esearch succeeds, esummary fails
        mock_get.side_effect = [
            {"esearchresult": {"count": "2", "idlist": ["12345", "67890"]}},
            {"error": "Failed to fetch summaries"},
        ]

        result = self.source.search("test query")

        # Should return placeholder articles with error
        assert len(result["articles"]) == 2
        assert result["articles"][0]["error"] == "Failed to fetch"


# ============================================================
# Test USPTO Patents Integration (3 tests)
# ============================================================

class TestPatentsViewSource:
    """Test suite for USPTO PatentsView API integration."""

    def setup_method(self):
        from external_data_hub import PatentsViewSource  # type: ignore
        self.tmpdir = tempfile.mkdtemp()
        self.source = PatentsViewSource(cache_dir=Path(self.tmpdir) / "patents")

    @patch("external_data_hub.PatentsViewSource._http_get")
    def test_search_success(self, mock_get):
        """Test successful patent search with response parsing."""
        mock_get.return_value = MOCK_PATENTS_RESPONSE

        result = self.source.search("next generation sequencing", max_results=10)

        assert result["source"] == "USPTO PatentsView"
        assert result["api_version"] == "v1"
        assert result["total_results"] == 15
        assert result["returned_results"] == 2
        assert len(result["patents"]) == 2

        # Verify patent parsing
        patent1 = result["patents"][0]
        assert patent1["patent_number"] == "US12345678"
        assert "Next Generation Sequencing" in patent1["title"]
        assert len(patent1["abstract"]) <= 300  # Abstract truncation
        assert patent1["date"] == "2024-01-15"
        assert "Foundation Medicine, Inc." in patent1["assignees"]

    @patch("external_data_hub.PatentsViewSource._http_get")
    def test_query_structure(self, mock_get):
        """Test that query is properly structured for PatentsView API."""
        mock_get.return_value = {"patents": [], "total_patent_count": 0}

        self.source.search("medical device", max_results=5)

        call_args = mock_get.call_args[0][0]
        # Verify JSON query structure
        assert "%22_text_any%22" in call_args or "q=" in call_args

    @patch("external_data_hub.PatentsViewSource._http_get")
    def test_api_error_handling(self, mock_get):
        """Test handling of patent API errors."""
        mock_get.return_value = {
            "error": "HTTP 503: Service Unavailable",
        }

        result = self.source.search("test query")

        assert result["total_results"] == 0
        assert result["patents"] == []
        assert "error" in result


# ============================================================
# Test Rate Limiter (3 tests)
# ============================================================

class TestRateLimiting:
    """Test suite for rate limiting behavior."""

    def setup_method(self):
        from external_data_hub import ClinicalTrialsSource  # type: ignore
        self.tmpdir = tempfile.mkdtemp()

    def test_rate_limit_wait_enforcement(self):
        """Test that rate limiter enforces minimum interval between requests."""
        from external_data_hub import ClinicalTrialsSource  # type: ignore
        # 2 requests per second = 0.5 second minimum interval
        source = ClinicalTrialsSource(cache_dir=Path(self.tmpdir) / "ct_rate")
        source.rate_limit = 2.0

        start = time.monotonic()
        source._rate_limit_wait()
        first = time.monotonic()
        source._rate_limit_wait()
        second = time.monotonic()

        # Second wait should enforce delay
        elapsed = second - first
        assert elapsed >= 0.4  # Allow for timing precision (0.5 - 0.1 margin)

    def test_rate_limit_disabled(self):
        """Test that rate limit 0 disables waiting."""
        from external_data_hub import ClinicalTrialsSource  # type: ignore
        source = ClinicalTrialsSource(cache_dir=Path(self.tmpdir) / "ct_norl")
        source.rate_limit = 0.0

        start = time.monotonic()
        for _ in range(5):
            source._rate_limit_wait()
        elapsed = time.monotonic() - start

        # Should complete almost instantly
        assert elapsed < 0.1

    def test_request_count_tracking(self):
        """Test that request count is tracked correctly."""
        from external_data_hub import ClinicalTrialsSource  # type: ignore
        source = ClinicalTrialsSource(cache_dir=Path(self.tmpdir) / "ct_count")

        # Mock at urllib.request level so _http_get logic executes
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"totalCount": 0, "studies": []}
            ).encode()
            mock_response.__enter__ = lambda self: self
            mock_response.__exit__ = lambda self, *args: None
            mock_urlopen.return_value = mock_response

            # Use different queries to avoid cache hits
            source.search("query1")
            source.search("query2")
            source.search("query3")

            stats = source.get_stats()
            # requests_made should be tracked
            assert stats["requests_made"] == 3


# ============================================================
# Test Cache Behavior (5 tests)
# ============================================================

class TestCacheBehavior:
    """Test suite for caching mechanism."""

    def setup_method(self):
        from external_data_hub import ClinicalTrialsSource  # type: ignore
        self.tmpdir = tempfile.mkdtemp()
        self.source = ClinicalTrialsSource(cache_dir=Path(self.tmpdir) / "ct_cache")

    def test_cache_save_and_load(self):
        """Test that cache can be saved and loaded."""
        test_data = {
            "source": "test",
            "results": [1, 2, 3],
        }

        key = self.source._cache_key({"test": "params"})
        self.source._set_cached(key, test_data)

        loaded = self.source._get_cached(key)
        assert loaded is not None
        assert loaded["source"] == "test"
        assert loaded["results"] == [1, 2, 3]

    def test_cache_ttl_expiry(self):
        """Test that cache respects TTL and expires old entries."""
        key = self.source._cache_key({"test": "expire"})

        # Write cache with timestamp from 48 hours ago
        cache_file = self.source.cache_dir / f"{key}.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        with open(cache_file, "w") as f:
            json.dump({
                "_cached_at": old_time.isoformat(),
                "source": "clinicaltrials",
                "data": {"old": True},
            }, f)

        # Should be expired (TTL is 24 hours)
        result = self.source._get_cached(key)
        assert result is None

    def test_cache_ttl_valid(self):
        """Test that fresh cache entries are not expired."""
        key = self.source._cache_key({"test": "fresh"})

        # Write cache with recent timestamp
        cache_file = self.source.cache_dir / f"{key}.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        fresh_time = datetime.now(timezone.utc) - timedelta(hours=1)
        with open(cache_file, "w") as f:
            json.dump({
                "_cached_at": fresh_time.isoformat(),
                "source": "clinicaltrials",
                "data": {"fresh": True},
            }, f)

        # Should not be expired
        result = self.source._get_cached(key)
        assert result is not None
        assert result["fresh"] is True

    def test_cache_corrupted_file(self):
        """Test handling of corrupted cache files."""
        key = self.source._cache_key({"test": "corrupt"})
        cache_file = self.source.cache_dir / f"{key}.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON
        with open(cache_file, "w") as f:
            f.write("{invalid json content")

        # Should return None for corrupted cache
        result = self.source._get_cached(key)
        assert result is None

    def test_cache_directory_creation(self):
        """Test that cache directories are created automatically."""
        from external_data_hub import PubMedSource  # type: ignore

        custom_dir = Path(self.tmpdir) / "custom" / "nested" / "cache"
        source = PubMedSource(cache_dir=custom_dir)

        assert source.cache_dir == custom_dir
        assert custom_dir.exists()


# ============================================================
# Test ExternalDataHub Integration (6 tests)
# ============================================================

class TestExternalDataHub:
    """Test suite for ExternalDataHub unified interface."""

    def setup_method(self):
        from external_data_hub import ExternalDataHub  # type: ignore
        self.tmpdir = tempfile.mkdtemp()
        self.store = _create_mock_pma_store()
        self.hub = ExternalDataHub(
            store=self.store,
            cache_dir=Path(self.tmpdir) / "hub_cache"
        )

    def test_get_available_sources(self):
        """Test listing available data sources."""
        sources = self.hub.get_available_sources()

        assert len(sources) == 3
        source_names = [s["name"] for s in sources]
        assert "clinicaltrials" in source_names
        assert "pubmed" in source_names
        assert "patents" in source_names

        # Verify source details
        ct_source = [s for s in sources if s["name"] == "clinicaltrials"][0]
        assert ct_source["label"] == "ClinicalTrials.gov"
        assert ct_source["rate_limit"] == 1.0
        assert ct_source["cache_ttl_hours"] == 24

    def test_search_unknown_source(self):
        """Test error handling for unknown data source."""
        result = self.hub.search("nonexistent_source", "test query")

        assert "error" in result
        assert "Unknown source" in result["error"]

    @patch("external_data_hub.ClinicalTrialsSource._http_get")
    def test_pma_context_enrichment_clinical_trials(self, mock_get):
        """Test that PMA context enriches query with device name."""
        mock_get.return_value = {"totalCount": 0, "studies": []}

        result = self.hub.search_clinical_trials(
            "diagnostic",
            pma_number="P170019",
            max_results=5
        )

        # Should have called store to get PMA data
        self.store.get_pma_data.assert_called_with("P170019")

        # Result should include PMA context
        assert result.get("pma_context") == "P170019"
        assert "hub_version" in result

    @patch("external_data_hub.PubMedSource._http_get")
    def test_pma_context_enrichment_pubmed(self, mock_get):
        """Test PMA context enrichment for PubMed searches."""
        mock_get.return_value = {
            "esearchresult": {"count": "0", "idlist": []},
        }

        result = self.hub.search_pubmed(
            "safety",
            pma_number="P170019",
            max_results=5
        )

        self.store.get_pma_data.assert_called_with("P170019")
        assert result.get("pma_context") == "P170019"

    @patch("external_data_hub.PatentsViewSource._http_get")
    def test_pma_context_enrichment_patents(self, mock_get):
        """Test PMA context enrichment for patent searches."""
        mock_get.return_value = {"patents": [], "total_patent_count": 0}

        result = self.hub.search_patents(
            "sequencing device",
            pma_number="P170019",
            max_results=5
        )

        self.store.get_pma_data.assert_called_with("P170019")
        assert result.get("pma_context") == "P170019"

    @patch("external_data_hub.ClinicalTrialsSource._http_get")
    @patch("external_data_hub.PubMedSource._http_get")
    @patch("external_data_hub.PatentsViewSource._http_get")
    def test_search_all_sources(self, mock_pat, mock_pub, mock_ct):
        """Test searching all sources simultaneously."""
        mock_ct.return_value = {"totalCount": 0, "studies": []}
        mock_pub.side_effect = [
            {"esearchresult": {"count": "0", "idlist": []}},
        ]
        mock_pat.return_value = {"patents": [], "total_patent_count": 0}

        result = self.hub.search_all_sources(
            "medical device test",
            max_results=3
        )

        assert result["query"] == "medical device test"
        assert "results" in result
        assert len(result["sources_queried"]) == 3

        # Verify all sources were queried
        assert "clinical_trials" in result["results"]
        assert "pubmed" in result["results"]
        assert "patents" in result["results"]

        # Verify disclaimer
        assert "disclaimer" in result
        assert "research" in result["disclaimer"].lower()


# ============================================================
# Test Hub Statistics (2 tests)
# ============================================================

class TestHubStatistics:
    """Test suite for hub statistics and monitoring."""

    def setup_method(self):
        from external_data_hub import ExternalDataHub  # type: ignore
        self.tmpdir = tempfile.mkdtemp()
        self.store = _create_mock_pma_store()
        self.hub = ExternalDataHub(
            store=self.store,
            cache_dir=Path(self.tmpdir) / "hub_stats"
        )

    def test_hub_stats_after_requests(self):
        """Test hub statistics track requests across sources."""
        # Mock at urllib.request level so request counting works
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"totalCount": 0, "studies": []}
            ).encode()
            mock_response.__enter__ = lambda self: self
            mock_response.__exit__ = lambda self, *args: None
            mock_urlopen.return_value = mock_response

            # Make several requests with different queries to avoid cache
            self.hub.search_clinical_trials("query1")
            self.hub.search_clinical_trials("query2")

            stats = self.hub.get_hub_stats()

            assert "total_requests" in stats
            assert "sources" in stats
            # Each unique query triggers one HTTP request
            assert stats["total_requests"] >= 2
            assert "clinicaltrials" in stats["sources"]

    def test_source_stats(self):
        """Test individual source statistics."""
        from external_data_hub import PubMedSource  # type: ignore

        source = PubMedSource(cache_dir=Path(self.tmpdir) / "pm_stats")
        stats = source.get_stats()

        assert stats["source"] == "pubmed"
        assert stats["label"] == "PubMed E-utilities"
        assert stats["api_version"] == "v2.0"
        assert stats["rate_limit_per_sec"] == 3.0
        assert stats["cache_ttl_hours"] == 168


# ============================================================
# Test Error Handling and Edge Cases (3 tests)
# ============================================================

class TestErrorHandling:
    """Test suite for error handling and edge cases."""

    def setup_method(self):
        from external_data_hub import ExternalDataHub  # type: ignore
        self.tmpdir = tempfile.mkdtemp()
        self.store = _create_mock_pma_store()
        self.hub = ExternalDataHub(
            store=self.store,
            cache_dir=Path(self.tmpdir) / "hub_errors"
        )

    @patch("external_data_hub.ClinicalTrialsSource._http_get")
    def test_network_timeout_error(self, mock_get):
        """Test handling of network timeout errors."""
        mock_get.return_value = None  # Simulates timeout

        result = self.hub.search_clinical_trials("test query")

        assert result["total_results"] == 0
        assert "error" in result

    @patch("external_data_hub.PubMedSource._http_get")
    def test_malformed_api_response(self, mock_get):
        """Test handling of malformed API responses."""
        # Missing expected fields
        mock_get.return_value = {"unexpected": "structure"}

        result = self.hub.search_pubmed("test query")

        # Should handle gracefully
        assert isinstance(result, dict)

    def test_pma_context_with_api_error(self):
        """Test PMA context enrichment when store API fails."""
        self.store.get_pma_data.return_value = {"error": "PMA not found"}

        with patch("external_data_hub.ClinicalTrialsSource._http_get") as mock_get:
            mock_get.return_value = {"totalCount": 0, "studies": []}

            # Should not crash, just skip enrichment
            result = self.hub.search_clinical_trials(
                "diagnostic",
                pma_number="P999999"
            )

            assert result is not None


# ============================================================
# Pytest markers
# ============================================================

pytestmark = [
    pytest.mark.scripts,
    pytest.mark.unit,
    pytest.mark.phase5,
]
