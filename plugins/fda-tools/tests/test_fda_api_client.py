"""
Tests for scripts/fda_api_client.py

Validates the centralized FDA API client including caching, retry logic,
degraded mode, and all endpoint methods (510k, PMA, classification, etc.).

Test coverage:
- Client initialization and configuration
- Cache key generation and TTL validation
- API request retry with exponential backoff
- 510(k) endpoint methods
- PMA endpoint methods
- Classification and UDI endpoints
- Batch operations
- Cache management
- Error handling and degraded mode

Per 21 CFR 820.70(i), validates software modules used for regulatory
data retrieval with comprehensive unit testing.
"""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

# Use proper package import
from scripts.fda_api_client import FDAClient


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def mock_api_response_510k():
    """Sample 510(k) API response."""
    return {
        "results": [
            {
                "k_number": "K241335",
                "device_name": "Test Catheter Device",
                "applicant": "Test Medical Inc",
                "product_code": "DQY",
                "decision_date": "20240615",
                "clearance_type": "Traditional",
                "review_panel": "CV",
                "regulation_number": "21 CFR 870.1210",
            }
        ],
        "meta": {"results": {"total": 1}},
    }


@pytest.fixture
def mock_api_response_pma():
    """Sample PMA API response."""
    return {
        "results": [
            {
                "pma_number": "P170019",
                "device_name": "Test PMA Device",
                "applicant": "Advanced Medical Corp",
                "product_code": "NMH",
                "decision_date": "20170501",
                "advisory_committee": "CV",
            }
        ],
        "meta": {"results": {"total": 1}},
    }


@pytest.fixture
def mock_api_response_classification():
    """Sample classification API response."""
    return {
        "results": [
            {
                "product_code": "DQY",
                "device_name": "Catheter, Intravascular, Diagnostic",
                "device_class": "2",
                "regulation_number": "870.1210",
                "review_panel": "CV",
                "medical_specialty": "Cardiovascular",
            }
        ],
        "meta": {"results": {"total": 1}},
    }


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Temporary cache directory for testing."""
    cache_dir = tmp_path / "api_cache"
    cache_dir.mkdir()
    return str(cache_dir)


# ============================================================================
# Client Initialization Tests
# ============================================================================


class TestFDAClientInitialization:
    """Test suite for FDAClient initialization."""

    def test_client_initializes_with_defaults(self, temp_cache_dir):
        """Test client initializes with default settings."""
        client = FDAClient(cache_dir=temp_cache_dir)

        assert client.cache_dir == Path(temp_cache_dir)
        assert client.enabled is True
        assert client._stats == {"hits": 0, "misses": 0, "errors": 0}

    def test_client_loads_api_key_from_env(self, temp_cache_dir, monkeypatch):
        """Test API key loaded from environment variable."""
        monkeypatch.setenv("OPENFDA_API_KEY", "test_key_123")

        client = FDAClient(cache_dir=temp_cache_dir)

        assert client.api_key == "test_key_123"

    def test_client_accepts_custom_api_key(self, temp_cache_dir):
        """Test client accepts API key passed at initialization."""
        client = FDAClient(cache_dir=temp_cache_dir, api_key="custom_key_456")

        assert client.api_key == "custom_key_456"

    def test_client_creates_cache_directory(self, tmp_path):
        """Test client creates cache directory if it doesn't exist."""
        cache_dir = tmp_path / "new_cache"

        client = FDAClient(cache_dir=str(cache_dir))

        assert cache_dir.exists()
        assert cache_dir.is_dir()

    @patch("fda_api_client.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="openfda_enabled: false\n")
    def test_client_respects_disabled_setting(self, mock_file, mock_exists, temp_cache_dir):
        """Test client respects openfda_enabled: false in settings."""
        mock_exists.return_value = True

        client = FDAClient(cache_dir=temp_cache_dir)

        assert client.enabled is False


# ============================================================================
# Cache Management Tests
# ============================================================================


class TestCacheManagement:
    """Test suite for cache key generation and management."""

    def test_cache_key_generation(self, temp_cache_dir):
        """Test cache key generated from endpoint and params."""
        client = FDAClient(cache_dir=temp_cache_dir)

        key1 = client._cache_key("510k", {"search": 'k_number:"K241335"', "limit": "1"})
        key2 = client._cache_key("510k", {"search": 'k_number:"K241335"', "limit": "1"})
        key3 = client._cache_key("510k", {"search": 'k_number:"K241336"', "limit": "1"})

        # Same params should generate same key
        assert key1 == key2
        # Different params should generate different key
        assert key1 != key3
        # Keys should be hex strings
        assert len(key1) == 16
        assert all(c in "0123456789abcdef" for c in key1)

    def test_cache_key_excludes_api_key(self, temp_cache_dir):
        """Test api_key param excluded from cache key generation."""
        client = FDAClient(cache_dir=temp_cache_dir)

        key1 = client._cache_key("510k", {"search": "test", "api_key": "key1"})
        key2 = client._cache_key("510k", {"search": "test", "api_key": "key2"})

        # Different API keys should produce same cache key
        assert key1 == key2

    def test_cache_write_and_read(self, temp_cache_dir):
        """Test writing and reading from cache."""
        client = FDAClient(cache_dir=temp_cache_dir)
        test_data = {"test": "data", "value": 123}

        cache_key = "test_cache_key"
        client._set_cached(cache_key, test_data)

        # Verify cache file exists
        cache_file = Path(temp_cache_dir) / f"{cache_key}.json"
        assert cache_file.exists()

        # Read back from cache
        cached_data = client._get_cached(cache_key)
        assert cached_data == test_data

    def test_cache_ttl_expiration(self, temp_cache_dir):
        """Test cache expires after TTL."""
        client = FDAClient(cache_dir=temp_cache_dir)
        test_data = {"test": "data"}
        cache_key = "expire_test"

        # Write cache with old timestamp
        cache_file = Path(temp_cache_dir) / f"{cache_key}.json"
        old_time = time.time() - (8 * 24 * 60 * 60)  # 8 days ago (> 7 day TTL)
        cache_file.write_text(json.dumps({
            "_cached_at": old_time,
            "data": test_data
        }))

        # Attempt to read expired cache
        cached_data = client._get_cached(cache_key)

        # Should return None for expired cache
        assert cached_data is None
        # Cache file should be deleted
        assert not cache_file.exists()

    def test_cache_stats(self, temp_cache_dir):
        """Test cache statistics generation."""
        client = FDAClient(cache_dir=temp_cache_dir)

        # Create some cache files
        client._set_cached("key1", {"data": "test1"})
        client._set_cached("key2", {"data": "test2"})

        # Generate stats
        stats = client.cache_stats()

        assert stats["cache_dir"] == temp_cache_dir
        assert stats["total_files"] == 2
        assert stats["valid"] == 2
        assert stats["expired"] == 0
        assert stats["total_size_bytes"] > 0

    def test_clear_cache(self, temp_cache_dir):
        """Test clearing all cache files."""
        client = FDAClient(cache_dir=temp_cache_dir)

        # Create cache files
        client._set_cached("key1", {"data": "test1"})
        client._set_cached("key2", {"data": "test2"})

        # Clear cache
        count = client.clear_cache()

        assert count == 2
        assert len(list(Path(temp_cache_dir).glob("*.json"))) == 0

    def test_clear_expired_cache_only(self, temp_cache_dir):
        """Test clearing only expired cache files."""
        client = FDAClient(cache_dir=temp_cache_dir)

        # Create fresh cache
        client._set_cached("fresh", {"data": "new"})

        # Create expired cache
        old_cache = Path(temp_cache_dir) / "expired.json"
        old_time = time.time() - (8 * 24 * 60 * 60)
        old_cache.write_text(json.dumps({
            "_cached_at": old_time,
            "data": {"old": "data"}
        }))

        # Clear only expired
        count = client.clear_cache("expired")

        assert count == 1
        assert (Path(temp_cache_dir) / "fresh.json").exists()
        assert not old_cache.exists()


# ============================================================================
# 510(k) Endpoint Tests
# ============================================================================


class Test510kEndpoints:
    """Test suite for 510(k) API methods."""

    @patch("fda_api_client.urllib.request.urlopen")
    def test_get_510k_success(self, mock_urlopen, temp_cache_dir, mock_api_response_510k):
        """Test successful 510(k) lookup by K-number."""
        # Mock API response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_api_response_510k).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = FDAClient(cache_dir=temp_cache_dir)
        result = client.get_510k("K241335")

        assert result["results"][0]["k_number"] == "K241335"
        assert result["results"][0]["device_name"] == "Test Catheter Device"
        assert mock_urlopen.called

    @patch("fda_api_client.urllib.request.urlopen")
    def test_get_510k_not_found(self, mock_urlopen, temp_cache_dir):
        """Test 510(k) lookup for non-existent K-number returns 404."""
        from urllib.error import HTTPError

        # Mock 404 response
        mock_urlopen.side_effect = HTTPError(
            "http://test", 404, "Not Found", {}, None
        )

        client = FDAClient(cache_dir=temp_cache_dir)
        result = client.get_510k("K999999")

        # Should return empty results for 404
        assert result["results"] == []
        assert result["meta"]["results"]["total"] == 0

    @patch("fda_api_client.urllib.request.urlopen")
    def test_get_510k_uses_cache(self, mock_urlopen, temp_cache_dir, mock_api_response_510k):
        """Test 510(k) lookup uses cached data on second call."""
        # Mock API response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_api_response_510k).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = FDAClient(cache_dir=temp_cache_dir)

        # First call hits API
        result1 = client.get_510k("K241335")
        assert client._stats["misses"] == 1
        assert client._stats["hits"] == 0

        # Second call uses cache
        result2 = client.get_510k("K241335")
        assert client._stats["misses"] == 1
        assert client._stats["hits"] == 1

        # Results should match
        assert result1 == result2
        # API should only be called once
        assert mock_urlopen.call_count == 1

    @patch("fda_api_client.urllib.request.urlopen")
    def test_batch_510k_query(self, mock_urlopen, temp_cache_dir):
        """Test batch 510(k) lookup with OR query."""
        batch_response = {
            "results": [
                {"k_number": "K241335", "device_name": "Device 1"},
                {"k_number": "K241336", "device_name": "Device 2"},
            ],
            "meta": {"results": {"total": 2}},
        }

        mock_response = Mock()
        mock_response.read.return_value = json.dumps(batch_response).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = FDAClient(cache_dir=temp_cache_dir)
        result = client.batch_510k(["K241335", "K241336"])

        assert len(result["results"]) == 2
        assert result["meta"]["results"]["total"] == 2

    @patch("fda_api_client.urllib.request.urlopen")
    def test_search_510k_with_filters(self, mock_urlopen, temp_cache_dir, mock_api_response_510k):
        """Test 510(k) search with combined filters."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_api_response_510k).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = FDAClient(cache_dir=temp_cache_dir)
        result = client.search_510k(
            product_code="DQY",
            year_start=2024,
            year_end=2024,
            limit=10
        )

        assert result["results"][0]["product_code"] == "DQY"


# ============================================================================
# PMA Endpoint Tests
# ============================================================================


class TestPMAEndpoints:
    """Test suite for PMA API methods."""

    @patch("fda_api_client.urllib.request.urlopen")
    def test_get_pma_success(self, mock_urlopen, temp_cache_dir, mock_api_response_pma):
        """Test successful PMA lookup by P-number."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_api_response_pma).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = FDAClient(cache_dir=temp_cache_dir)
        result = client.get_pma("P170019")

        assert result["results"][0]["pma_number"] == "P170019"
        assert result["results"][0]["device_name"] == "Test PMA Device"

    @patch("fda_api_client.urllib.request.urlopen")
    def test_batch_pma_query(self, mock_urlopen, temp_cache_dir):
        """Test batch PMA lookup with OR query."""
        batch_response = {
            "results": [
                {"pma_number": "P170019", "device_name": "PMA Device 1"},
                {"pma_number": "P180020", "device_name": "PMA Device 2"},
            ],
            "meta": {"results": {"total": 2}},
        }

        mock_response = Mock()
        mock_response.read.return_value = json.dumps(batch_response).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = FDAClient(cache_dir=temp_cache_dir)
        result = client.batch_pma(["P170019", "P180020"])

        assert len(result["results"]) == 2

    @patch("fda_api_client.urllib.request.urlopen")
    def test_search_pma_with_filters(self, mock_urlopen, temp_cache_dir, mock_api_response_pma):
        """Test PMA search with combined filters."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_api_response_pma).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = FDAClient(cache_dir=temp_cache_dir)
        result = client.search_pma(
            product_code="NMH",
            year_start=2017,
            year_end=2017,
            limit=10
        )

        assert result["results"][0]["product_code"] == "NMH"


# ============================================================================
# Classification and Other Endpoint Tests
# ============================================================================


class TestOtherEndpoints:
    """Test suite for classification, UDI, and other endpoints."""

    @patch("fda_api_client.urllib.request.urlopen")
    def test_get_classification(self, mock_urlopen, temp_cache_dir, mock_api_response_classification):
        """Test device classification lookup by product code."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_api_response_classification).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = FDAClient(cache_dir=temp_cache_dir)
        result = client.get_classification("DQY")

        assert result["results"][0]["product_code"] == "DQY"
        assert result["results"][0]["device_class"] == "2"

    @patch("fda_api_client.urllib.request.urlopen")
    def test_validate_device_k_number(self, mock_urlopen, temp_cache_dir, mock_api_response_510k):
        """Test device validation for K-number."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_api_response_510k).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = FDAClient(cache_dir=temp_cache_dir)
        result = client.validate_device("K241335")

        assert result["results"][0]["k_number"] == "K241335"

    @patch("fda_api_client.urllib.request.urlopen")
    def test_validate_device_pma_number(self, mock_urlopen, temp_cache_dir, mock_api_response_pma):
        """Test device validation for P-number."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_api_response_pma).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = FDAClient(cache_dir=temp_cache_dir)
        result = client.validate_device("P170019")

        assert result["results"][0]["pma_number"] == "P170019"

    def test_validate_device_n_number(self, temp_cache_dir):
        """Test device validation returns error for N-numbers."""
        client = FDAClient(cache_dir=temp_cache_dir)
        result = client.validate_device("N12345")

        assert result.get("degraded") is True
        assert result.get("n_number") is True
        assert "Pre-Amendments" in result.get("error", "")


# ============================================================================
# Error Handling and Retry Tests
# ============================================================================


class TestErrorHandling:
    """Test suite for error handling and retry logic."""

    @patch("fda_api_client.urllib.request.urlopen")
    @patch("fda_api_client.time.sleep")
    def test_retry_on_server_error(self, mock_sleep, mock_urlopen, temp_cache_dir):
        """Test retry with exponential backoff on 500 error."""
        from urllib.error import HTTPError

        # First two calls fail with 500, third succeeds
        mock_urlopen.side_effect = [
            HTTPError("http://test", 500, "Server Error", {}, None),
            HTTPError("http://test", 500, "Server Error", {}, None),
            Mock(
                read=lambda: json.dumps({"results": [], "meta": {}}).encode(),
                __enter__=lambda self: self,
                __exit__=lambda *args: False,
            ),
        ]

        client = FDAClient(cache_dir=temp_cache_dir)
        result = client.get_510k("K241335")

        # Should have retried and eventually succeeded
        assert not result.get("degraded")
        assert mock_urlopen.call_count == 3
        assert mock_sleep.call_count == 2  # Slept between retries

    @patch("fda_api_client.urllib.request.urlopen")
    @patch("fda_api_client.time.sleep")
    def test_degraded_mode_after_max_retries(self, mock_sleep, mock_urlopen, temp_cache_dir):
        """Test degraded mode after max retries exhausted."""
        from urllib.error import HTTPError

        # All retries fail
        mock_urlopen.side_effect = HTTPError("http://test", 500, "Server Error", {}, None)

        client = FDAClient(cache_dir=temp_cache_dir)
        result = client.get_510k("K241335")

        # Should return degraded result
        assert result.get("degraded") is True
        assert "unavailable after" in result.get("error", "").lower()
        assert client._stats["errors"] == 1

    @patch("fda_api_client.urllib.request.urlopen")
    def test_api_disabled_returns_degraded(self, mock_urlopen, temp_cache_dir):
        """Test degraded mode when API is disabled."""
        client = FDAClient(cache_dir=temp_cache_dir)
        client.enabled = False

        result = client.get_510k("K241335")

        assert result.get("degraded") is True
        assert result.get("error") == "API disabled"
        # Should not call API
        assert not mock_urlopen.called


# ============================================================================
# Pytest Markers
# ============================================================================

pytestmark = [
    pytest.mark.unit,
    pytest.mark.scripts,
]
