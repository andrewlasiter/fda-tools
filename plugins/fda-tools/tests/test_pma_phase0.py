"""
Comprehensive test suite for PMA Intelligence Module - Phase 0.

Tests cover all 5 core modules:
    1. TestPMAAPIClient -- fda_api_client.py PMA methods
    2. TestPMADataStore -- pma_data_store.py cache and manifest
    3. TestSSEDDownloader -- pma_ssed_cache.py download orchestration
    4. TestSectionExtractor -- pma_section_extractor.py 15-section parsing
    5. TestPMASearchCommand -- pma-search.md command interface

Target: 90% code coverage with 50+ tests.
All tests run offline (no network access) using mocks.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


# ============================================================
# 1. TestPMAAPIClient -- fda_api_client.py PMA methods
# ============================================================


class TestPMAAPIClient:
    """Test PMA-specific methods on FDAClient."""

    @pytest.fixture
    def client(self):
        """Create a mock-friendly FDAClient."""
        with patch("fda_api_client.FDAClient._check_enabled", return_value=True):
            with patch("fda_api_client.FDAClient._load_api_key", return_value=None):
                from fda_api_client import FDAClient
                c = FDAClient()
                c._request = MagicMock()
                return c

    def test_get_pma_calls_correct_endpoint(self, client):
        client._request.return_value = {"results": [{"pma_number": "P170019"}]}
        result = client.get_pma("P170019")
        client._request.assert_called_once_with(
            "pma", {"search": 'pma_number:"P170019"', "limit": "1"}
        )
        assert result["results"][0]["pma_number"] == "P170019"

    def test_get_pma_supplements_calls_correct_endpoint(self, client):
        client._request.return_value = {"results": []}
        client.get_pma_supplements("P170019", limit=100)
        client._request.assert_called_once_with(
            "pma", {"search": 'pma_number:"P170019"', "limit": "100"}
        )

    def test_get_pma_by_product_code(self, client):
        client._request.return_value = {"results": [{"product_code": "NMH"}]}
        result = client.get_pma_by_product_code("NMH", limit=25)
        client._request.assert_called_once_with(
            "pma", {"search": 'product_code:"NMH"', "limit": "25"}
        )

    def test_search_pma_with_product_code(self, client):
        client._request.return_value = {"results": [], "meta": {"results": {"total": 0}}}
        client.search_pma(product_code="NMH")
        call_args = client._request.call_args
        assert call_args[0][0] == "pma"
        assert 'product_code:"NMH"' in call_args[0][1]["search"]

    def test_search_pma_with_year_range(self, client):
        client._request.return_value = {"results": []}
        client.search_pma(product_code="NMH", year_start=2024, year_end=2024)
        call_args = client._request.call_args
        assert "20240101" in call_args[0][1]["search"]
        assert "20241231" in call_args[0][1]["search"]

    def test_search_pma_with_applicant(self, client):
        client._request.return_value = {"results": []}
        client.search_pma(applicant="Foundation Medicine")
        call_args = client._request.call_args
        assert 'applicant:"Foundation Medicine"' in call_args[0][1]["search"]

    def test_search_pma_with_device_name(self, client):
        client._request.return_value = {"results": []}
        client.search_pma(device_name="CDx")
        call_args = client._request.call_args
        assert 'trade_name:"CDx"' in call_args[0][1]["search"]

    def test_search_pma_no_filters_returns_error(self, client):
        result = client.search_pma()
        assert result.get("degraded") is True
        assert "error" in result

    def test_search_pma_with_sort(self, client):
        client._request.return_value = {"results": []}
        client.search_pma(product_code="NMH", sort="decision_date:desc")
        call_args = client._request.call_args
        assert call_args[0][1].get("sort") == "decision_date:desc"

    def test_batch_pma_with_multiple_numbers(self, client):
        client._request.return_value = {
            "results": [
                {"pma_number": "P170019"},
                {"pma_number": "P200024"},
            ]
        }
        result = client.batch_pma(["P170019", "P200024"])
        call_args = client._request.call_args
        assert 'pma_number:"P170019"' in call_args[0][1]["search"]
        assert 'pma_number:"P200024"' in call_args[0][1]["search"]
        assert "+OR+" in call_args[0][1]["search"]

    def test_batch_pma_empty_list(self, client):
        result = client.batch_pma([])
        assert result["results"] == []
        assert result["meta"]["results"]["total"] == 0


# ============================================================
# 2. TestPMADataStore -- pma_data_store.py
# ============================================================


class TestPMADataStoreManifest:
    """Test PMA data store manifest operations."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a PMADataStore with tmp directory."""
        with patch("pma_data_store.FDAClient"):
            from pma_data_store import PMADataStore
            return PMADataStore(cache_dir=str(tmp_path))

    def test_get_manifest_creates_new(self, store):
        manifest = store.get_manifest()
        assert manifest["schema_version"] == "1.0.0"
        assert manifest["total_pmas"] == 0
        assert manifest["pma_entries"] == {}
        assert "created_at" in manifest

    def test_save_manifest_creates_file(self, store, tmp_path):
        store.get_manifest()
        store.save_manifest()
        assert (tmp_path / "data_manifest.json").exists()

    def test_save_manifest_updates_last_updated(self, store):
        store.get_manifest()
        store.save_manifest()
        manifest = store.get_manifest()
        assert "last_updated" in manifest

    def test_save_manifest_roundtrip(self, store, tmp_path):
        manifest = store.get_manifest()
        manifest["pma_entries"]["P170019"] = {
            "pma_number": "P170019",
            "device_name": "TestDevice",
        }
        store.save_manifest()

        # Create new store pointing to same directory
        with patch("pma_data_store.FDAClient"):
            from pma_data_store import PMADataStore
            store2 = PMADataStore(cache_dir=str(tmp_path))
        manifest2 = store2.get_manifest()
        assert "P170019" in manifest2["pma_entries"]
        assert manifest2["pma_entries"]["P170019"]["device_name"] == "TestDevice"

    def test_save_manifest_counts_totals(self, store):
        manifest = store.get_manifest()
        manifest["pma_entries"]["P170019"] = {
            "ssed_downloaded": True,
            "sections_extracted": True,
        }
        manifest["pma_entries"]["P200024"] = {
            "ssed_downloaded": True,
            "sections_extracted": False,
        }
        manifest["pma_entries"]["P070004"] = {
            "ssed_downloaded": False,
            "sections_extracted": False,
        }
        store.save_manifest()
        saved = store.get_manifest()
        assert saved["total_pmas"] == 3
        assert saved["total_sseds_downloaded"] == 2
        assert saved["total_sections_extracted"] == 1

    def test_update_manifest_entry_creates_new(self, store):
        store.update_manifest_entry("P170019", {"device_name": "CDx"})
        manifest = store.get_manifest()
        assert "P170019" in manifest["pma_entries"]
        assert manifest["pma_entries"]["P170019"]["device_name"] == "CDx"
        assert "first_cached_at" in manifest["pma_entries"]["P170019"]

    def test_update_manifest_entry_merges(self, store):
        store.update_manifest_entry("P170019", {"device_name": "CDx"})
        store.update_manifest_entry("P170019", {"applicant": "Foundation"})
        entry = store.get_manifest()["pma_entries"]["P170019"]
        assert entry["device_name"] == "CDx"
        assert entry["applicant"] == "Foundation"

    def test_update_manifest_entry_uppercases_key(self, store):
        store.update_manifest_entry("p170019", {"device_name": "Test"})
        manifest = store.get_manifest()
        assert "P170019" in manifest["pma_entries"]

    def test_manifest_corrupt_json_creates_new(self, tmp_path):
        (tmp_path / "data_manifest.json").write_text("{invalid json!")
        with patch("pma_data_store.FDAClient"):
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
        manifest = store.get_manifest()
        assert manifest["schema_version"] == "1.0.0"
        assert manifest["pma_entries"] == {}


class TestPMADataStoreTTL:
    """Test PMA data store TTL expiration."""

    @pytest.fixture
    def store(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_data_store import PMADataStore
            return PMADataStore(cache_dir=str(tmp_path))

    def test_fresh_entry_not_expired(self, store):
        now = datetime.now(timezone.utc).isoformat()
        store.update_manifest_entry("P170019", {
            "pma_approval_fetched_at": now,
        })
        assert store.is_expired("P170019", "pma_approval") is False

    def test_old_entry_expired(self, store):
        old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        store.update_manifest_entry("P170019", {
            "pma_approval_fetched_at": old,
        })
        assert store.is_expired("P170019", "pma_approval") is True

    def test_ssed_never_expires_when_downloaded(self, store):
        store.update_manifest_entry("P170019", {
            "ssed_downloaded": True,
        })
        assert store.is_expired("P170019", "pma_ssed") is False

    def test_ssed_expired_when_not_downloaded(self, store):
        store.update_manifest_entry("P170019", {
            "ssed_downloaded": False,
        })
        assert store.is_expired("P170019", "pma_ssed") is True

    def test_sections_never_expire_when_extracted(self, store):
        store.update_manifest_entry("P170019", {
            "sections_extracted": True,
        })
        assert store.is_expired("P170019", "pma_sections") is False

    def test_missing_entry_is_expired(self, store):
        assert store.is_expired("P999999", "pma_approval") is True

    def test_missing_timestamp_is_expired(self, store):
        store.update_manifest_entry("P170019", {"device_name": "Test"})
        assert store.is_expired("P170019", "pma_approval") is True

    def test_supplements_24h_ttl(self, store):
        recent = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
        store.update_manifest_entry("P170019", {
            "pma_supplements_fetched_at": recent,
        })
        assert store.is_expired("P170019", "pma_supplements") is False

        old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        store.update_manifest_entry("P170019", {
            "pma_supplements_fetched_at": old,
        })
        assert store.is_expired("P170019", "pma_supplements") is True


class TestPMADataStoreAPI:
    """Test PMA data store API data operations."""

    @pytest.fixture
    def store(self, tmp_path):
        mock_client = MagicMock()
        with patch("pma_data_store.FDAClient", return_value=mock_client):
            from pma_data_store import PMADataStore
            s = PMADataStore(cache_dir=str(tmp_path))
            s.client = mock_client
            return s

    def test_get_pma_data_from_api(self, store):
        store.client.get_pma.return_value = {
            "results": [{
                "pma_number": "P170019",
                "applicant": "Foundation Medicine",
                "trade_name": "FoundationOne CDx",
                "generic_name": "IVD Panel",
                "product_code": "NMH",
                "decision_date": "20171130",
                "decision_code": "APPR",
                "advisory_committee": "CH",
            }],
            "meta": {"results": {"total": 1}},
        }
        data = store.get_pma_data("P170019")
        assert data["pma_number"] == "P170019"
        assert data["applicant"] == "Foundation Medicine"
        assert data["device_name"] == "FoundationOne CDx"
        assert data["product_code"] == "NMH"
        assert data["_cache_status"] == "fresh"

    def test_get_pma_data_uses_cache(self, store, tmp_path):
        # Pre-populate cache
        pma_dir = tmp_path / "P170019"
        pma_dir.mkdir()
        cached_data = {
            "pma_number": "P170019",
            "device_name": "Cached Device",
            "_fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        (pma_dir / "pma_data.json").write_text(json.dumps(cached_data))

        # Mark as not expired
        store.update_manifest_entry("P170019", {
            "pma_approval_fetched_at": datetime.now(timezone.utc).isoformat(),
        })

        data = store.get_pma_data("P170019")
        assert data["device_name"] == "Cached Device"
        # API should not be called
        store.client.get_pma.assert_not_called()

    def test_get_pma_data_refresh_bypasses_cache(self, store, tmp_path):
        # Pre-populate cache
        pma_dir = tmp_path / "P170019"
        pma_dir.mkdir()
        (pma_dir / "pma_data.json").write_text(json.dumps({"pma_number": "P170019"}))
        store.update_manifest_entry("P170019", {
            "pma_approval_fetched_at": datetime.now(timezone.utc).isoformat(),
        })

        store.client.get_pma.return_value = {
            "results": [{"pma_number": "P170019", "trade_name": "Refreshed"}],
            "meta": {"results": {"total": 1}},
        }
        data = store.get_pma_data("P170019", refresh=True)
        store.client.get_pma.assert_called_once()
        assert data["device_name"] == "Refreshed"

    def test_get_pma_data_api_error_returns_stale(self, store, tmp_path):
        # Pre-populate stale cache
        pma_dir = tmp_path / "P170019"
        pma_dir.mkdir()
        (pma_dir / "pma_data.json").write_text(json.dumps({
            "pma_number": "P170019",
            "device_name": "Stale Device",
        }))

        store.client.get_pma.return_value = {"error": "API timeout", "degraded": True}
        data = store.get_pma_data("P170019")
        assert data["device_name"] == "Stale Device"
        assert data["_cache_status"] == "stale"

    def test_get_pma_data_api_error_no_cache(self, store):
        store.client.get_pma.return_value = {"error": "API timeout", "degraded": True}
        data = store.get_pma_data("P999999")
        assert "error" in data

    def test_save_pma_data_atomic_write(self, store, tmp_path):
        store.save_pma_data("P170019", {"pma_number": "P170019", "test": True})
        data_path = tmp_path / "P170019" / "pma_data.json"
        assert data_path.exists()
        with open(data_path) as f:
            saved = json.load(f)
        assert saved["test"] is True


class TestPMADataStoreSections:
    """Test extracted sections operations."""

    @pytest.fixture
    def store(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_data_store import PMADataStore
            return PMADataStore(cache_dir=str(tmp_path))

    def test_save_and_load_sections(self, store, tmp_path):
        sections = {
            "general_information": {"content": "test", "word_count": 100},
        }
        store.save_extracted_sections("P170019", sections)
        loaded = store.get_extracted_sections("P170019")
        assert loaded["general_information"]["word_count"] == 100

    def test_get_sections_returns_none_when_missing(self, store):
        result = store.get_extracted_sections("P999999")
        assert result is None

    def test_mark_sections_extracted_updates_manifest(self, store):
        store.mark_sections_extracted("P170019", 12, 25000)
        manifest = store.get_manifest()
        entry = manifest["pma_entries"]["P170019"]
        assert entry["sections_extracted"] is True
        assert entry["section_count"] == 12
        assert entry["total_word_count"] == 25000


class TestPMADataStoreSearchCache:
    """Test search result caching."""

    @pytest.fixture
    def store(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_data_store import PMADataStore
            return PMADataStore(cache_dir=str(tmp_path))

    def test_cache_and_retrieve_search(self, store):
        results = [{"pma_number": "P170019"}, {"pma_number": "P200024"}]
        store.cache_search_results("product_code:NMH:year:2024", results)
        cached = store.get_cached_search("product_code:NMH:year:2024")
        assert cached is not None
        assert len(cached) == 2

    def test_expired_search_returns_none(self, store):
        manifest = store.get_manifest()
        manifest["search_cache"]["test_key"] = {
            "results": [{"pma_number": "P170019"}],
            "fetched_at": (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(),
            "result_count": 1,
        }
        cached = store.get_cached_search("test_key")
        assert cached is None

    def test_missing_search_returns_none(self, store):
        assert store.get_cached_search("nonexistent") is None


class TestPMADataStoreMaintenance:
    """Test cache maintenance operations."""

    @pytest.fixture
    def store(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_data_store import PMADataStore
            return PMADataStore(cache_dir=str(tmp_path))

    def test_clear_pma(self, store, tmp_path):
        # Create PMA directory and manifest entry
        pma_dir = tmp_path / "P170019"
        pma_dir.mkdir()
        (pma_dir / "pma_data.json").write_text("{}")
        store.update_manifest_entry("P170019", {"device_name": "Test"})
        store.save_manifest()

        assert store.clear_pma("P170019") is True
        assert not pma_dir.exists()
        assert "P170019" not in store.get_manifest()["pma_entries"]

    def test_clear_pma_not_found(self, store):
        assert store.clear_pma("P999999") is False

    def test_clear_all(self, store, tmp_path):
        for pn in ["P170019", "P200024"]:
            pma_dir = tmp_path / pn
            pma_dir.mkdir()
            (pma_dir / "pma_data.json").write_text("{}")
            store.update_manifest_entry(pn, {"device_name": "Test"})
        store.save_manifest()

        count = store.clear_all()
        assert count == 2
        assert not (tmp_path / "P170019").exists()
        assert not (tmp_path / "data_manifest.json").exists()

    def test_list_cached_pmas(self, store):
        store.update_manifest_entry("P170019", {
            "device_name": "CDx",
            "decision_date": "20171130",
            "ssed_downloaded": True,
        })
        store.update_manifest_entry("P200024", {
            "device_name": "Device B",
            "decision_date": "20200115",
        })
        pmas = store.list_cached_pmas()
        assert len(pmas) == 2
        # Should be sorted by date descending
        assert pmas[0]["pma_number"] == "P200024"

    def test_get_stats(self, store):
        store.update_manifest_entry("P170019", {
            "product_code": "NMH",
            "ssed_downloaded": True,
            "ssed_file_size_kb": 500,
            "sections_extracted": True,
        })
        stats = store.get_stats()
        assert stats["total_pmas"] == 1
        assert stats["total_sseds_downloaded"] == 1
        assert stats["unique_product_codes"] == 1
        assert "NMH" in stats["product_codes"]

    def test_clear_expired_searches(self, store):
        manifest = store.get_manifest()
        manifest["search_cache"]["old_key"] = {
            "results": [],
            "fetched_at": (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(),
        }
        manifest["search_cache"]["fresh_key"] = {
            "results": [],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        store.save_manifest()
        count = store.clear_expired_searches()
        assert count == 1
        assert "fresh_key" in store.get_manifest()["search_cache"]
        assert "old_key" not in store.get_manifest()["search_cache"]


# ============================================================
# 3. TestSSEDDownloader -- pma_ssed_cache.py
# ============================================================


class TestSSEDURLConstruction:
    """Test SSED URL construction with TICKET-002 patterns."""

    def test_standard_pma_url(self):
        from pma_ssed_cache import construct_ssed_url
        urls = construct_ssed_url("P170019")
        assert len(urls) == 3
        assert "pdf17/P170019B.pdf" in urls[0]
        assert "pdf17/P170019b.pdf" in urls[1]

    def test_2000s_pma_single_digit_folder(self):
        """TICKET-002: 2000s PMAs use single-digit folders."""
        from pma_ssed_cache import construct_ssed_url
        urls = construct_ssed_url("P070004")
        assert "pdf7/" in urls[0]  # NOT pdf07
        assert "P070004B.pdf" in urls[0]

    def test_2000s_pma_year_05(self):
        from pma_ssed_cache import construct_ssed_url
        urls = construct_ssed_url("P050040")
        assert "pdf5/" in urls[0]  # NOT pdf05

    def test_2000s_pma_year_03(self):
        from pma_ssed_cache import construct_ssed_url
        urls = construct_ssed_url("P030027")
        assert "pdf3/" in urls[0]  # NOT pdf03

    def test_2010s_pma_double_digit_folder(self):
        from pma_ssed_cache import construct_ssed_url
        urls = construct_ssed_url("P100003")
        assert "pdf10/" in urls[0]

    def test_2020s_pma(self):
        from pma_ssed_cache import construct_ssed_url
        urls = construct_ssed_url("P240024")
        assert "pdf24/" in urls[0]

    def test_supplement_url(self):
        from pma_ssed_cache import construct_ssed_url
        urls = construct_ssed_url("P170019S029")
        assert "P170019S029B.pdf" in urls[0]
        assert "pdf17/" in urls[0]

    def test_lowercase_b_variant(self):
        from pma_ssed_cache import construct_ssed_url
        urls = construct_ssed_url("P170019")
        assert any("b.pdf" in u and "B.pdf" not in u for u in urls)

    def test_all_lowercase_variant(self):
        from pma_ssed_cache import construct_ssed_url
        urls = construct_ssed_url("P170019")
        assert any("p170019b.pdf" in u for u in urls)

    def test_invalid_pma_raises_error(self):
        from pma_ssed_cache import construct_ssed_url
        with pytest.raises(ValueError):
            construct_ssed_url("K241335")


class TestPDFValidation:
    """Test PDF content validation."""

    def test_valid_pdf(self):
        from pma_ssed_cache import validate_pdf
        content = b"%PDF-1.4 " + b"x" * 5000
        assert validate_pdf(content) is True

    def test_too_small_pdf(self):
        from pma_ssed_cache import validate_pdf
        content = b"%PDF-1.4 " + b"x" * 100
        assert validate_pdf(content) is False

    def test_html_error_page(self):
        from pma_ssed_cache import validate_pdf
        content = b"<html><body>Not Found</body></html>" + b" " * 2000
        assert validate_pdf(content) is False

    def test_empty_content(self):
        from pma_ssed_cache import validate_pdf
        assert validate_pdf(b"") is False


class TestSSEDDownloader:
    """Test SSED batch download orchestration."""

    @pytest.fixture
    def downloader(self, tmp_path):
        with patch("pma_data_store.FDAClient"):
            from pma_ssed_cache import SSEDDownloader
            from pma_data_store import PMADataStore
            store = PMADataStore(cache_dir=str(tmp_path))
            return SSEDDownloader(store=store, rate_limit=0.0)

    def test_download_skips_cached(self, downloader, tmp_path):
        """Already downloaded SSEDs should be skipped."""
        pma_dir = tmp_path / "P170019"
        pma_dir.mkdir()
        pdf_path = pma_dir / "ssed.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 " + b"x" * 5000)

        result = downloader.download_ssed("P170019")
        assert result["success"] is True
        assert result["skipped"] is True

    def test_download_force_redownloads(self, downloader, tmp_path):
        """Force flag should re-download even if cached."""
        pma_dir = tmp_path / "P170019"
        pma_dir.mkdir()
        pdf_path = pma_dir / "ssed.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 " + b"x" * 5000)

        with patch.object(downloader, "_try_download") as mock_dl:
            mock_dl.return_value = {
                "success": True,
                "content": b"%PDF-1.4 " + b"x" * 10000,
                "attempts": 1,
                "error": None,
            }
            result = downloader.download_ssed("P170019", force=True)
            assert result["success"] is True
            assert result["skipped"] is False

    def test_download_handles_all_404s(self, downloader):
        """When all URL patterns return 404, report failure."""
        with patch.object(downloader, "_try_download") as mock_dl:
            mock_dl.return_value = {
                "success": False,
                "content": None,
                "attempts": 1,
                "error": "HTTP 404",
            }
            result = downloader.download_ssed("P999999")
            assert result["success"] is False
            assert "404" in result["error"]

    def test_download_invalid_pma_format(self, downloader):
        result = downloader.download_ssed("INVALID")
        assert result["success"] is False
        assert "Invalid PMA" in result["error"]

    def test_batch_download(self, downloader, tmp_path):
        """Test batch download tracks progress."""
        # Pre-populate one PMA to test skip logic
        pma_dir = tmp_path / "P170019"
        pma_dir.mkdir()
        (pma_dir / "ssed.pdf").write_bytes(b"%PDF-1.4 " + b"x" * 5000)

        with patch.object(downloader, "_try_download") as mock_dl:
            mock_dl.return_value = {
                "success": True,
                "content": b"%PDF-1.4 " + b"x" * 8000,
                "attempts": 1,
                "error": None,
            }
            results = downloader.download_batch(["P170019", "P200024"])

        assert len(results) == 2
        # First should be skipped (cached), second downloaded
        assert results[0]["skipped"] is True
        assert results[1]["success"] is True

    def test_get_stats(self, downloader, tmp_path):
        # Pre-cache one PMA
        pma_dir = tmp_path / "P170019"
        pma_dir.mkdir()
        (pma_dir / "ssed.pdf").write_bytes(b"%PDF-1.4 " + b"x" * 5000)

        downloader.download_ssed("P170019")
        stats = downloader.get_stats()
        assert stats["attempted"] == 1
        assert stats["skipped"] == 1
        assert stats["downloaded"] == 0
        assert stats["failed"] == 0


# ============================================================
# 4. TestSectionExtractor -- pma_section_extractor.py
# ============================================================


class TestSectionPatterns:
    """Test section pattern definitions and compilation."""

    def test_all_15_sections_defined(self):
        from pma_section_extractor import SSED_SECTIONS
        assert len(SSED_SECTIONS) == 15

    def test_section_list_returns_15(self):
        from pma_section_extractor import get_section_list
        sections = get_section_list()
        assert len(sections) == 15

    def test_sections_have_required_fields(self):
        from pma_section_extractor import SSED_SECTIONS
        for key, section in SSED_SECTIONS.items():
            assert "display_name" in section, f"{key} missing display_name"
            assert "section_number" in section, f"{key} missing section_number"
            assert "patterns" in section, f"{key} missing patterns"
            assert len(section["patterns"]) >= 2, f"{key} needs at least 2 patterns"

    def test_section_numbers_unique(self):
        from pma_section_extractor import SSED_SECTIONS
        numbers = [s["section_number"] for s in SSED_SECTIONS.values()]
        assert len(numbers) == len(set(numbers)), "Duplicate section numbers"


class TestSectionExtraction:
    """Test section extraction from text."""

    @pytest.fixture
    def extractor(self):
        from pma_section_extractor import PMAExtractor
        return PMAExtractor()

    def _make_ssed_text(self):
        """Create realistic SSED text for testing."""
        return """
I. GENERAL INFORMATION

This document provides a summary of the safety and effectiveness data
for the FoundationOne CDx test. The applicant is Foundation Medicine, Inc.
The device is an in vitro diagnostic test using next-generation sequencing.

II. INDICATIONS FOR USE

FoundationOne CDx is indicated for use as a companion diagnostic to identify
patients who may benefit from treatment with specific FDA-approved therapies.
The test is a qualitative next-generation sequencing-based in vitro diagnostic test
that uses DNA isolated from formalin-fixed paraffin-embedded tumor tissue specimens.

III. DEVICE DESCRIPTION

The FoundationOne CDx test is performed on the Illumina HiSeq 4000 instrument
platform. The test analyzes 324 genes, two genomic signatures, and reports
tumor mutational burden and microsatellite instability status.

IV. ALTERNATIVE PRACTICES AND PROCEDURES

Alternative approaches to companion diagnostic testing include single-gene
tests and other multi-gene panel tests. Currently available companion
diagnostics are listed in the FDA companion diagnostic database.

V. MARKETING HISTORY

This is the first PMA application for the FoundationOne CDx test.
Foundation Medicine previously received FDA clearance for related products.

VI. POTENTIAL RISKS AND ADVERSE EFFECTS

The primary risks associated with FoundationOne CDx include false positive
results that may lead to inappropriate treatment, and false negative results
that may lead to withholding appropriate therapy. Sample collection involves
minimal risk as it uses tissue already collected for biopsy.

VII. SUMMARY OF CLINICAL STUDIES

A pivotal clinical validation study was conducted enrolling 3,162 patients
across 12 clinical sites. The study demonstrated analytical sensitivity of
99.3% and specificity of 99.8%. Overall positive percent agreement was 94.2%.
Primary endpoints included positive percent agreement and negative percent agreement.

VIII. STATISTICAL ANALYSIS

Statistical methods included calculation of point estimates and two-sided
95% confidence intervals for PPA and NPA. Sample size was determined using
the Wilson score method. Pre-specified success criteria required the lower
bound of the 95% CI to exceed the threshold values.

IX. NONCLINICAL TESTING

Nonclinical performance testing included analytical validation studies
for accuracy, precision, limit of detection, and reproducibility.
Biocompatibility testing was not applicable as this is an IVD device.

X. MANUFACTURING AND STERILIZATION

FoundationOne CDx is manufactured at the Foundation Medicine facility
in Cambridge, Massachusetts. The manufacturing process includes DNA
extraction, library preparation, sequencing, and bioinformatic analysis.

XI. BENEFIT-RISK ANALYSIS

The probable benefits of FoundationOne CDx include identification of
patients who may benefit from targeted therapy. The risks are primarily
related to incorrect test results. The benefit-risk profile is favorable.

XII. OVERALL CONCLUSIONS

Based on review of the clinical and nonclinical data, FDA concludes
that there is reasonable assurance of safety and effectiveness for
FoundationOne CDx when used in accordance with the indications for use.

XIII. PANEL RECOMMENDATION

The Clinical Chemistry and Clinical Toxicology Devices Panel reviewed
the PMA application and recommended approval with conditions.

XIV. LABELING

The labeling includes instructions for use, package insert, and
specimen collection guide. All labeling has been reviewed and found
to adequately describe the device and its proper use.
"""

    def test_extract_from_text_success(self, extractor):
        text = self._make_ssed_text()
        result = extractor.extract_from_text(text)
        assert result["success"] is True
        assert len(result["sections"]) > 0
        assert "metadata" in result

    def test_finds_general_information(self, extractor):
        text = self._make_ssed_text()
        result = extractor.extract_from_text(text)
        assert "general_information" in result["sections"]

    def test_finds_indications_for_use(self, extractor):
        text = self._make_ssed_text()
        result = extractor.extract_from_text(text)
        assert "indications_for_use" in result["sections"]

    def test_finds_device_description(self, extractor):
        text = self._make_ssed_text()
        result = extractor.extract_from_text(text)
        assert "device_description" in result["sections"]

    def test_finds_clinical_studies(self, extractor):
        text = self._make_ssed_text()
        result = extractor.extract_from_text(text)
        assert "clinical_studies" in result["sections"]

    def test_finds_overall_conclusions(self, extractor):
        text = self._make_ssed_text()
        result = extractor.extract_from_text(text)
        assert "overall_conclusions" in result["sections"]

    def test_section_has_word_count(self, extractor):
        text = self._make_ssed_text()
        result = extractor.extract_from_text(text)
        for key, section in result["sections"].items():
            assert "word_count" in section
            assert section["word_count"] > 0

    def test_section_has_confidence(self, extractor):
        text = self._make_ssed_text()
        result = extractor.extract_from_text(text)
        for key, section in result["sections"].items():
            assert "confidence" in section
            assert 0 <= section["confidence"] <= 1.0

    def test_metadata_quality_score(self, extractor):
        text = self._make_ssed_text()
        result = extractor.extract_from_text(text)
        meta = result["metadata"]
        assert "quality_score" in meta
        assert 0 <= meta["quality_score"] <= 100

    def test_metadata_extraction_quality(self, extractor):
        text = self._make_ssed_text()
        result = extractor.extract_from_text(text)
        quality = result["metadata"]["extraction_quality"]
        assert quality in ("HIGH", "MEDIUM", "LOW")

    def test_metadata_missing_sections(self, extractor):
        text = self._make_ssed_text()
        result = extractor.extract_from_text(text)
        assert "missing_sections" in result["metadata"]
        assert isinstance(result["metadata"]["missing_sections"], list)

    def test_short_text_fails(self, extractor):
        result = extractor.extract_from_text("short")
        assert result["success"] is False

    def test_empty_text_fails(self, extractor):
        result = extractor.extract_from_text("")
        assert result["success"] is False

    def test_none_text_fails(self, extractor):
        result = extractor.extract_from_text(None)
        assert result["success"] is False

    def test_numbered_section_detection(self, extractor):
        """Test numbered format (1. 2. 3.) instead of Roman numerals."""
        text = """
1. GENERAL INFORMATION

This is the general information section for the device.
The applicant submitted a PMA for this novel device.

2. INDICATIONS FOR USE

The device is indicated for treatment of condition X.
Detailed indications follow below.
"""
        result = extractor.extract_from_text(text)
        assert result["success"] is True
        assert "general_information" in result["sections"]
        assert "indications_for_use" in result["sections"]


class TestQualityScoring:
    """Test extraction quality scoring."""

    @pytest.fixture
    def extractor(self):
        from pma_section_extractor import PMAExtractor
        return PMAExtractor()

    def test_high_quality_many_sections(self, extractor):
        # Create text with many key sections
        sections_text = ""
        for header in [
            "I. GENERAL INFORMATION", "II. INDICATIONS FOR USE",
            "III. DEVICE DESCRIPTION", "VII. SUMMARY OF CLINICAL STUDIES",
            "XI. BENEFIT-RISK ANALYSIS", "XII. OVERALL CONCLUSIONS",
        ]:
            sections_text += f"\n\n{header}\n\n" + "word " * 600

        result = extractor.extract_from_text(sections_text)
        assert result["metadata"]["quality_score"] >= 60

    def test_low_quality_few_sections(self, extractor):
        text = """
I. GENERAL INFORMATION

Brief overview with minimal content. This document has very little information
and only covers one section out of the fifteen possible SSED sections. The
extraction quality should be rated as low due to the sparse content.
"""
        result = extractor.extract_from_text(text)
        assert result["metadata"]["quality_score"] < 50


# ============================================================
# 5. TestPMASearchCommand -- Integration / CLI tests
# ============================================================


class TestPMADataStoreCLI:
    """Test PMA data store CLI argument handling."""

    def test_main_show_manifest(self, capsys, tmp_path):
        with patch("pma_data_store._get_pma_cache_dir", return_value=str(tmp_path)):
            with patch("pma_data_store.FDAClient"):
                from pma_data_store import main
                with patch("sys.argv", ["pma_data_store.py", "--show-manifest"]):
                    main()
        output = capsys.readouterr().out
        assert "PMA_CACHE_DIR:" in output
        assert "TOTAL_PMAS:" in output

    def test_main_stats(self, capsys, tmp_path):
        with patch("pma_data_store._get_pma_cache_dir", return_value=str(tmp_path)):
            with patch("pma_data_store.FDAClient"):
                from pma_data_store import main
                with patch("sys.argv", ["pma_data_store.py", "--stats"]):
                    main()
        output = capsys.readouterr().out
        assert "total_pmas" in output

    def test_main_clear_all(self, capsys, tmp_path):
        with patch("pma_data_store._get_pma_cache_dir", return_value=str(tmp_path)):
            with patch("pma_data_store.FDAClient"):
                from pma_data_store import main
                with patch("sys.argv", ["pma_data_store.py", "--clear-all"]):
                    main()
        output = capsys.readouterr().out
        assert "CLEARED:" in output

    def test_main_no_args_errors(self):
        with patch("pma_data_store._get_pma_cache_dir", return_value="/tmp/test"):
            with patch("pma_data_store.FDAClient"):
                from pma_data_store import main
                with patch("sys.argv", ["pma_data_store.py"]):
                    with pytest.raises(SystemExit):
                        main()


class TestSSEDDownloaderCLI:
    """Test SSED downloader CLI."""

    def test_dry_run(self, capsys):
        from pma_ssed_cache import main
        with patch("pma_data_store.FDAClient"):
            with patch("sys.argv", ["pma_ssed_cache.py", "--pma", "P170019", "--dry-run"]):
                main()
        output = capsys.readouterr().out
        assert "P170019" in output
        assert "pdf17" in output


class TestSectionExtractorCLI:
    """Test section extractor CLI."""

    def test_list_sections(self, capsys):
        from pma_section_extractor import main
        with patch("sys.argv", ["pma_section_extractor.py", "--list-sections"]):
            main()
        output = capsys.readouterr().out
        assert "General Information" in output
        assert "Indications for Use" in output
        assert "Clinical Studies" in output


# ============================================================
# Integration Tests
# ============================================================


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_data_store_to_sections_pipeline(self, tmp_path):
        """Test the full pipeline: store -> save -> load -> extract."""
        with patch("pma_data_store.FDAClient"):
            from pma_data_store import PMADataStore
            from pma_section_extractor import PMAExtractor

            store = PMADataStore(cache_dir=str(tmp_path))
            extractor = PMAExtractor(store=store)

            # Simulate API data
            store.save_pma_data("P170019", {
                "pma_number": "P170019",
                "device_name": "TestDevice",
                "product_code": "NMH",
            })

            # Verify data can be loaded
            data = store.get_extracted_sections("P170019")
            assert data is None  # Not yet extracted

            # Save mock extracted sections
            sections = {
                "general_information": {
                    "display_name": "General Information",
                    "content": "Test content",
                    "word_count": 100,
                    "confidence": 0.95,
                },
                "metadata": {
                    "total_sections_found": 1,
                    "quality_score": 50,
                },
            }
            store.save_extracted_sections("P170019", sections)
            store.mark_sections_extracted("P170019", 1, 100)

            # Verify sections can be loaded
            loaded = store.get_extracted_sections("P170019")
            assert loaded is not None
            assert "general_information" in loaded

            # Verify manifest updated
            manifest = store.get_manifest()
            entry = manifest["pma_entries"]["P170019"]
            assert entry["sections_extracted"] is True

    def test_ttl_tiers_configured(self):
        """Verify all TTL tiers are properly configured."""
        from pma_data_store import PMA_TTL_TIERS
        assert PMA_TTL_TIERS["pma_approval"] == 168  # 7 days
        assert PMA_TTL_TIERS["pma_ssed"] == 0         # Never expires
        assert PMA_TTL_TIERS["pma_supplements"] == 24  # 24 hours
        assert PMA_TTL_TIERS["pma_search"] == 24       # 24 hours
        assert PMA_TTL_TIERS["pma_sections"] == 0      # Never expires
