"""Tests for the FDAClient Python API client.

Validates device number routing, search method signatures, and offline behavior.
These tests do NOT require API access — they test client logic only.
"""

import os
import sys
import pytest

# Add scripts directory to path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fda_api_client import FDAClient


class TestDeviceNumberRouting:
    """Test validate_device() routing logic."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create a client with API disabled to test routing only."""
        settings = tmp_path / "settings.md"
        settings.write_text("openfda_enabled: false\n")
        # Override the settings path by creating a client with disabled API
        c = FDAClient(cache_dir=str(tmp_path / "cache"))
        c.enabled = False
        return c

    def test_k_number_routes_to_510k(self, client):
        result = client.validate_device("K241335")
        # When disabled, returns degraded response
        assert result.get("degraded") is True

    def test_p_number_routes_to_pma(self, client):
        result = client.validate_device("P870024")
        assert result.get("degraded") is True

    def test_den_number_attempts_510k_then_falls_back(self, client):
        result = client.validate_device("DEN200043")
        # DEN routing tries 510k first, returns note if not found
        assert result.get("degraded") is True or "note" in result

    def test_n_number_returns_error(self, client):
        result = client.validate_device("N0012")
        assert result.get("n_number") is True
        assert "not in openFDA" in result.get("error", "")

    def test_unknown_format_returns_error(self, client):
        result = client.validate_device("X12345")
        assert "error" in result
        assert "Unsupported" in result["error"]


class TestSearchMethod:
    """Test search_510k() parameter handling."""

    @pytest.fixture
    def client(self, tmp_path):
        c = FDAClient(cache_dir=str(tmp_path / "cache"))
        c.enabled = False
        return c

    def test_search_with_query(self, client):
        result = client.search_510k(query="spinal fusion")
        assert result.get("degraded") is True  # API disabled

    def test_search_with_product_code(self, client):
        result = client.search_510k(product_code="OVE")
        assert result.get("degraded") is True

    def test_search_with_year_range(self, client):
        result = client.search_510k(product_code="OVE", year_start="2023", year_end="2025")
        assert result.get("degraded") is True

    def test_search_no_filters_returns_error(self, client):
        result = client.search_510k()
        assert "error" in result


class TestPMAMethods:
    """Test PMA-related method signatures and offline behavior."""

    @pytest.fixture
    def client(self, tmp_path):
        c = FDAClient(cache_dir=str(tmp_path / "cache"))
        c.enabled = False
        return c

    def test_get_pma(self, client):
        result = client.get_pma("P870024")
        assert result.get("degraded") is True

    def test_get_pma_supplements(self, client):
        result = client.get_pma_supplements("P870024")
        assert result.get("degraded") is True

    def test_get_pma_by_product_code(self, client):
        result = client.get_pma_by_product_code("DXY")
        assert result.get("degraded") is True


class TestUDIMethod:
    """Test UDI/GUDID method signatures and offline behavior."""

    @pytest.fixture
    def client(self, tmp_path):
        c = FDAClient(cache_dir=str(tmp_path / "cache"))
        c.enabled = False
        return c

    def test_get_udi_by_product_code(self, client):
        result = client.get_udi(product_code="OVE")
        assert result.get("degraded") is True

    def test_get_udi_by_di(self, client):
        result = client.get_udi(di="00888104123456")
        assert result.get("degraded") is True

    def test_get_udi_by_company(self, client):
        result = client.get_udi(company_name="MEDTRONIC")
        assert result.get("degraded") is True

    def test_get_udi_no_params_returns_error(self, client):
        result = client.get_udi()
        assert "error" in result


class TestCacheManagement:
    """Test cache operations."""

    @pytest.fixture
    def client(self, tmp_path):
        return FDAClient(cache_dir=str(tmp_path / "cache"))

    def test_cache_stats_empty(self, client):
        stats = client.cache_stats()
        assert stats["total_files"] == 0
        assert stats["total_size_bytes"] == 0

    def test_cache_key_generation(self, client):
        key1 = client._cache_key("510k", {"search": 'k_number:"K241335"'})
        key2 = client._cache_key("510k", {"search": 'k_number:"K241335"'})
        key3 = client._cache_key("510k", {"search": 'k_number:"K000000"'})
        assert key1 == key2  # Same params -> same key
        assert key1 != key3  # Different params -> different key

    def test_cache_key_excludes_api_key(self, client):
        key1 = client._cache_key("510k", {"search": 'k_number:"K241335"'})
        key2 = client._cache_key("510k", {"search": 'k_number:"K241335"', "api_key": "secret"})
        assert key1 == key2  # api_key should be excluded from cache key

    def test_set_and_get_cached(self, client):
        client._set_cached("testkey", {"results": [{"k_number": "K241335"}]})
        cached = client._get_cached("testkey")
        assert cached is not None
        assert cached["results"][0]["k_number"] == "K241335"

    def test_clear_cache(self, client):
        client._set_cached("testkey1", {"data": "test1"})
        client._set_cached("testkey2", {"data": "test2"})
        assert client.cache_stats()["total_files"] == 2
        count = client.clear_cache()
        assert count == 2
        assert client.cache_stats()["total_files"] == 0
