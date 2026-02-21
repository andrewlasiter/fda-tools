"""Tests for PubMed API rate limiting and retry logic (FDA-151).

Coverage:
- Default rate limit is 3 req/sec (no API key)
- Rate limit bumps to 10 req/sec when NCBI_API_KEY is supplied
- ExternalDataHub auto-loads NCBI_API_KEY from environment
- _http_get retries on HTTP 429 (rate limited by NCBI)
- _http_get retries on HTTP 500, 502, 503, 504 (transient server errors)
- _http_get does NOT retry on HTTP 404 (non-transient)
- _http_get returns error dict after all retries are exhausted
- API key is passed in request header, not in the URL
"""

import os
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pubmed_source(api_key=None, tmp_path=None):
    """Return a PubMedSource without touching the real filesystem."""
    from fda_tools.scripts.external_data_hub import PubMedSource

    cache_dir = tmp_path or Path("/tmp/test_pubmed_cache")
    return PubMedSource(cache_dir=cache_dir, api_key=api_key)


def _make_http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://example.com",
        code=code,
        msg=f"Error {code}",
        hdrs={},  # type: ignore[arg-type]
        fp=None,
    )


# ---------------------------------------------------------------------------
# Rate-limit configuration tests
# ---------------------------------------------------------------------------


class TestPubMedRateLimit:
    """Tests for rate limit configuration based on API key presence."""

    def test_default_rate_limit_is_3_rps(self, tmp_path):
        """Without API key, rate limit is 3 req/sec (NCBI unauthenticated limit)."""
        source = _make_pubmed_source(tmp_path=tmp_path)
        assert source.rate_limit == 3.0

    def test_rate_limit_with_api_key_is_10_rps(self, tmp_path):
        """With API key, rate limit upgrades to 10 req/sec (NCBI authenticated limit)."""
        source = _make_pubmed_source(api_key="test-ncbi-key", tmp_path=tmp_path)
        assert source.rate_limit == 10.0

    def test_api_key_stored_on_instance(self, tmp_path):
        """API key is accessible via self.api_key."""
        source = _make_pubmed_source(api_key="my-key", tmp_path=tmp_path)
        assert source.api_key == "my-key"

    def test_no_api_key_stored_as_none(self, tmp_path):
        """Without API key, self.api_key is None."""
        source = _make_pubmed_source(tmp_path=tmp_path)
        assert source.api_key is None


# ---------------------------------------------------------------------------
# Environment variable auto-loading tests
# ---------------------------------------------------------------------------


class TestNCBIApiKeyFromEnv:
    """Tests for ExternalDataHub auto-loading NCBI_API_KEY from environment."""

    def test_ncbi_api_key_loaded_from_env(self, tmp_path):
        """ExternalDataHub reads NCBI_API_KEY from env and passes it to PubMedSource."""
        from fda_tools.scripts.external_data_hub import ExternalDataHub

        with patch.dict(os.environ, {"NCBI_API_KEY": "env-test-key"}):
            hub = ExternalDataHub(cache_dir=tmp_path)

        pubmed_source = hub._sources["pubmed"]
        assert pubmed_source.api_key == "env-test-key"

    def test_ncbi_api_key_missing_gives_none(self, tmp_path):
        """When NCBI_API_KEY is absent from env, PubMedSource.api_key is None."""
        from fda_tools.scripts.external_data_hub import ExternalDataHub

        env_without_key = {k: v for k, v in os.environ.items() if k != "NCBI_API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            hub = ExternalDataHub(cache_dir=tmp_path)

        pubmed_source = hub._sources["pubmed"]
        assert pubmed_source.api_key is None

    def test_ncbi_api_key_in_env_sets_10_rps(self, tmp_path):
        """When NCBI_API_KEY is in env, the PubMedSource uses 10 req/sec."""
        from fda_tools.scripts.external_data_hub import ExternalDataHub

        with patch.dict(os.environ, {"NCBI_API_KEY": "env-key"}):
            hub = ExternalDataHub(cache_dir=tmp_path)

        assert hub._sources["pubmed"].rate_limit == 10.0


# ---------------------------------------------------------------------------
# Retry logic tests
# ---------------------------------------------------------------------------


class TestHttpGetRetry:
    """Tests for _http_get retry on 429/5xx and non-retry on 404."""

    def _patch_urlopen(self, source, side_effects):
        """Patch urllib.request.urlopen with a sequence of side_effects."""
        mock_urlopen = MagicMock(side_effect=side_effects)
        return patch("urllib.request.urlopen", mock_urlopen)

    def test_retries_on_429(self, tmp_path):
        """_http_get retries when the server returns HTTP 429."""
        source = _make_pubmed_source(tmp_path=tmp_path)

        # Fail twice with 429, succeed on third attempt
        ok_response = MagicMock()
        ok_response.__enter__ = lambda s: s
        ok_response.__exit__ = MagicMock(return_value=False)
        ok_response.read.return_value = b'{"result": "ok"}'

        side_effects = [
            _make_http_error(429),
            _make_http_error(429),
            ok_response,
        ]

        with patch("urllib.request.urlopen", side_effect=side_effects):
            result = source._http_get("https://example.com/test")

        assert result == {"result": "ok"}

    def test_retries_on_503(self, tmp_path):
        """_http_get retries when the server returns HTTP 503."""
        source = _make_pubmed_source(tmp_path=tmp_path)

        ok_response = MagicMock()
        ok_response.__enter__ = lambda s: s
        ok_response.__exit__ = MagicMock(return_value=False)
        ok_response.read.return_value = b'{"data": "value"}'

        side_effects = [_make_http_error(503), ok_response]

        with patch("urllib.request.urlopen", side_effect=side_effects):
            result = source._http_get("https://example.com/test")

        assert result == {"data": "value"}

    @pytest.mark.parametrize("code", [500, 502, 503, 504])
    def test_retries_on_all_transient_server_errors(self, code, tmp_path):
        """_http_get retries on each transient server error code."""
        source = _make_pubmed_source(tmp_path=tmp_path)

        ok_response = MagicMock()
        ok_response.__enter__ = lambda s: s
        ok_response.__exit__ = MagicMock(return_value=False)
        ok_response.read.return_value = b'{"ok": true}'

        side_effects = [_make_http_error(code), ok_response]

        with patch("urllib.request.urlopen", side_effect=side_effects):
            result = source._http_get("https://example.com/test")

        assert result == {"ok": True}

    def test_no_retry_on_404(self, tmp_path):
        """_http_get does NOT retry on HTTP 404 — returns error dict immediately."""
        source = _make_pubmed_source(tmp_path=tmp_path)

        call_count = 0

        def urlopen_404(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise _make_http_error(404)

        with patch("urllib.request.urlopen", side_effect=urlopen_404):
            result = source._http_get("https://example.com/missing")

        assert call_count == 1, "Should not retry on 404"
        assert "error" in result
        assert "404" in result["error"]

    def test_returns_error_dict_after_max_retries(self, tmp_path):
        """After exhausting all retries on 429, _http_get returns an error dict."""
        source = _make_pubmed_source(tmp_path=tmp_path)

        with patch("urllib.request.urlopen", side_effect=_make_http_error(429)):
            result = source._http_get("https://example.com/test")

        assert "error" in result
        assert "429" in result["error"]


# ---------------------------------------------------------------------------
# Header vs URL tests
# ---------------------------------------------------------------------------


class TestApiKeyInHeader:
    """Tests that the API key is passed in the request header, not the URL."""

    def test_api_key_in_header_not_url(self, tmp_path):
        """The NCBI API key is added to request headers, not the URL query string."""
        source = _make_pubmed_source(api_key="secret-key", tmp_path=tmp_path)

        captured_requests = []

        ok_response = MagicMock()
        ok_response.__enter__ = lambda s: s
        ok_response.__exit__ = MagicMock(return_value=False)
        ok_response.read.return_value = b'{"esearchresult": {"idlist": [], "count": "0"}}'

        def capture_urlopen(req, *args, **kwargs):
            captured_requests.append(req)
            return ok_response

        with patch("urllib.request.urlopen", side_effect=capture_urlopen):
            source.search("test query", max_results=1)

        assert captured_requests, "urlopen should have been called"
        req = captured_requests[0]

        # Key should NOT appear in the URL
        assert "secret-key" not in req.full_url
        assert "api_key=secret-key" not in req.full_url

        # Key should appear in the request headers
        assert req.get_header("Api_key") == "secret-key"
