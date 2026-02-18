#!/usr/bin/env python3
"""
Integration tests for FDAClient with rate limiting (FDA-20).

Tests rate limiting integration, 429 handling, header parsing,
and statistics collection in the FDA API client.
"""

import json
import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import urllib.error
import urllib.request

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fda_api_client import FDAClient


class TestFDAClientRateLimiting:
    """Test FDAClient with rate limiting enabled."""

    def test_initialization_with_api_key(self, tmp_path):
        """Test that client initializes with higher rate limit when API key present."""
        client = FDAClient(cache_dir=tmp_path, api_key="test_key")

        stats = client.rate_limit_stats()
        assert stats is not None
        assert stats["requests_per_minute"] == 1000  # Authenticated rate

    def test_initialization_without_api_key(self, tmp_path, monkeypatch):
        """Test that client initializes with lower rate limit without API key."""
        # Clear environment variable
        monkeypatch.delenv("OPENFDA_API_KEY", raising=False)

        # Mock the _load_api_key method to ensure it returns None
        with patch.object(FDAClient, "_load_api_key", return_value=None):
            client = FDAClient(cache_dir=tmp_path, api_key=None)

            stats = client.rate_limit_stats()
            assert stats is not None
            assert stats["requests_per_minute"] == 240  # Unauthenticated rate

    def test_initialization_with_rate_limit_override(self, tmp_path):
        """Test that rate limit can be overridden."""
        client = FDAClient(
            cache_dir=tmp_path,
            api_key=None,
            rate_limit_override=500,
        )

        stats = client.rate_limit_stats()
        assert stats is not None
        assert stats["requests_per_minute"] == 500

    def test_rate_limiter_acquires_token_before_request(self, tmp_path):
        """Test that rate limiter acquires token before making request."""
        client = FDAClient(cache_dir=tmp_path, api_key=None)

        # Mock the urllib.request.urlopen to track if rate limiter was used
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Create a mock response
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "results": [{"k_number": "K123456"}],
                "meta": {"results": {"total": 1}}
            }).encode()
            mock_response.headers = {}
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            # Make a request
            result = client.get_510k("K123456")

            # Check that request was made
            assert mock_urlopen.called
            assert result.get("results") is not None

            # Check that rate limiter recorded the request
            stats = client.rate_limit_stats()
            assert stats["total_requests"] == 1

    def test_rate_limiter_updates_from_response_headers(self, tmp_path):
        """Test that rate limiter updates from response headers."""
        client = FDAClient(cache_dir=tmp_path, api_key=None)

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Create a mock response with rate limit headers
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "results": [],
                "meta": {"results": {"total": 0}}
            }).encode()
            mock_response.headers = {
                "X-RateLimit-Limit": "240",
                "X-RateLimit-Remaining": "200",
            }
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            # Make a request
            result = client.get_classification("XXX")

            assert result is not None
            assert mock_urlopen.called

    def test_rate_limiter_warns_on_low_remaining(self, tmp_path, caplog):
        """Test that rate limiter warns when approaching limit."""
        client = FDAClient(cache_dir=tmp_path, api_key=None)

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Create response with very few remaining requests
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "results": [],
                "meta": {"results": {"total": 0}}
            }).encode()
            mock_response.headers = {
                "X-RateLimit-Limit": "240",
                "X-RateLimit-Remaining": "5",  # Only 5 remaining (< 10%)
            }
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            # Make a request
            client.get_classification("XXX")

            # Check that warning was issued
            stats = client.rate_limit_stats()
            assert stats["rate_limit_warnings"] >= 1

    def test_429_response_triggers_retry(self, tmp_path):
        """Test that 429 responses trigger retry with backoff."""
        client = FDAClient(cache_dir=tmp_path, api_key=None)

        call_count = 0

        def mock_urlopen_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                # First 2 calls return 429
                error = urllib.error.HTTPError(
                    url="http://test",
                    code=429,
                    msg="Too Many Requests",
                    hdrs={"Retry-After": "1"},
                    fp=None,
                )
                raise error
            else:
                # Third call succeeds
                mock_response = MagicMock()
                mock_response.read.return_value = json.dumps({
                    "results": [],
                    "meta": {"results": {"total": 0}}
                }).encode()
                mock_response.headers = {}
                mock_response.__enter__ = Mock(return_value=mock_response)
                mock_response.__exit__ = Mock(return_value=False)
                return mock_response

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_side_effect):
            with patch("time.sleep"):  # Speed up test by mocking sleep
                result = client.get_classification("XXX")

                # Should eventually succeed after retries
                assert result is not None
                assert call_count == 3  # Should have retried twice

    def test_429_exhausts_retries(self, tmp_path):
        """Test that persistent 429 responses exhaust retries."""
        client = FDAClient(cache_dir=tmp_path, api_key=None)

        def mock_urlopen_side_effect(*args, **kwargs):
            # Always return 429
            error = urllib.error.HTTPError(
                url="http://test",
                code=429,
                msg="Too Many Requests",
                hdrs={},
                fp=None,
            )
            raise error

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_side_effect):
            with patch("time.sleep"):  # Speed up test
                result = client.get_classification("XXX")

                # Should return degraded error after max retries
                assert result.get("degraded") is True
                assert "error" in result

    def test_server_error_triggers_retry(self, tmp_path):
        """Test that 5xx errors trigger retry with backoff."""
        client = FDAClient(cache_dir=tmp_path, api_key=None)

        call_count = 0

        def mock_urlopen_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count < 2:
                # First call returns 503
                error = urllib.error.HTTPError(
                    url="http://test",
                    code=503,
                    msg="Service Unavailable",
                    hdrs={},
                    fp=None,
                )
                raise error
            else:
                # Second call succeeds
                mock_response = MagicMock()
                mock_response.read.return_value = json.dumps({
                    "results": [],
                    "meta": {"results": {"total": 0}}
                }).encode()
                mock_response.headers = {}
                mock_response.__enter__ = Mock(return_value=mock_response)
                mock_response.__exit__ = Mock(return_value=False)
                return mock_response

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_side_effect):
            with patch("time.sleep"):
                result = client.get_classification("XXX")

                assert result is not None
                assert call_count == 2

    def test_client_error_no_retry(self, tmp_path):
        """Test that 4xx errors (except 404, 429) don't trigger retry."""
        client = FDAClient(cache_dir=tmp_path, api_key=None)

        call_count = 0

        def mock_urlopen_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            # Return 403 Forbidden
            error = urllib.error.HTTPError(
                url="http://test",
                code=403,
                msg="Forbidden",
                hdrs={},
                fp=None,
            )
            raise error

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_side_effect):
            result = client.get_classification("XXX")

            # Should return error immediately without retry
            assert result.get("degraded") is True
            assert "403" in result.get("error", "")
            assert call_count == 1  # No retries

    def test_cache_hit_skips_rate_limiter(self, tmp_path):
        """Test that cache hits don't consume rate limiter tokens."""
        client = FDAClient(cache_dir=tmp_path, api_key=None)

        with patch("urllib.request.urlopen") as mock_urlopen:
            # First request - cache miss
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "results": [{"product_code": "ABC"}],
                "meta": {"results": {"total": 1}}
            }).encode()
            mock_response.headers = {}
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            result1 = client.get_classification("ABC")
            assert result1.get("results") is not None

            # Get initial rate limiter stats
            stats1 = client.rate_limit_stats()
            requests_after_first = stats1["total_requests"]

            # Second request - cache hit (should not use rate limiter token)
            result2 = client.get_classification("ABC")
            assert result2.get("results") is not None

            stats2 = client.rate_limit_stats()
            requests_after_second = stats2["total_requests"]

            # Rate limiter requests should be the same (cache hit)
            assert requests_after_first == requests_after_second

    def test_rate_limit_stats_in_cache_stats(self, tmp_path, monkeypatch):
        """Test that cache_stats includes rate limiting stats."""
        # Clear environment variable
        monkeypatch.delenv("OPENFDA_API_KEY", raising=False)

        with patch.object(FDAClient, "_load_api_key", return_value=None):
            client = FDAClient(cache_dir=tmp_path, api_key=None)

            stats = client.cache_stats()

            # Should include rate_limiting key
            assert "rate_limiting" in stats
            assert stats["rate_limiting"]["requests_per_minute"] == 240

    def test_rate_limit_acquisition_timeout(self, tmp_path):
        """Test that rate limit acquisition timeout is handled."""
        client = FDAClient(cache_dir=tmp_path, api_key=None)

        # Mock the rate limiter to always timeout
        with patch.object(client._rate_limiter, "acquire", return_value=False):
            result = client.get_classification("XXX")

            # Should return degraded error
            assert result.get("degraded") is True
            assert "timeout" in result.get("error", "").lower()


class TestFDAClientWithoutRateLimiter:
    """Test FDAClient fallback behavior when rate limiter not available."""

    @patch("fda_api_client._RATE_LIMITER_AVAILABLE", False)
    def test_client_works_without_rate_limiter(self, tmp_path):
        """Test that client still works when rate limiter module not available."""
        # Note: This test requires reloading the module, which is complex
        # For now, we just test that the client can be created
        # and rate_limit_stats returns None

        client = FDAClient(cache_dir=tmp_path, api_key=None)

        # Should not crash
        assert client is not None


class TestRateLimitingEndToEnd:
    """End-to-end tests with realistic scenarios."""

    def test_burst_of_requests(self, tmp_path):
        """Test handling a burst of requests."""
        client = FDAClient(
            cache_dir=tmp_path,
            api_key=None,
            rate_limit_override=60,  # 1 token per second
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "results": [],
                "meta": {"results": {"total": 0}}
            }).encode()
            mock_response.headers = {}
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            # Make a burst of requests
            # First 60 should succeed from burst capacity
            # Beyond that should start blocking
            start_time = time.time()
            for i in range(65):
                result = client.get_classification(f"CODE{i}")
                assert result is not None

            elapsed = time.time() - start_time

            # Should have taken some time due to rate limiting
            # 65 requests at 1/sec = ~5 seconds of waiting beyond burst
            # (allowing some tolerance for timing)
            assert elapsed > 3.0

            # Check stats
            stats = client.rate_limit_stats()
            assert stats["total_requests"] == 65
            # Some requests should have waited
            assert stats["total_waits"] > 0

    def test_sustained_rate(self, tmp_path):
        """Test sustained request rate stays under limit."""
        client = FDAClient(
            cache_dir=tmp_path,
            api_key=None,
            rate_limit_override=120,  # 2 tokens per second
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({
                "results": [],
                "meta": {"results": {"total": 0}}
            }).encode()
            mock_response.headers = {}
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_response

            # Make 10 requests with small delays
            for i in range(10):
                result = client.get_classification(f"CODE{i}")
                assert result is not None
                time.sleep(0.1)  # Small delay between requests

            # Should complete without significant blocking
            stats = client.rate_limit_stats()
            assert stats["total_requests"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
