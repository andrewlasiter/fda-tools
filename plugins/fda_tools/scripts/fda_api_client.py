#!/usr/bin/env python3
"""
Centralized FDA API Client with caching and retry logic.

Provides LRU caching (7-day TTL), exponential backoff retry, and degraded mode
on failure for all openFDA Device API endpoints.

Cache files use SHA-256 integrity envelopes (GAP-011 / FDA-71) to detect
corruption or tampering. All writes are atomic (temp + replace).

Usage:
    from fda_api_client import FDAClient

    client = FDAClient()
    result = client.get_510k("K192345")
    result = client.get_classification("OVE")
    result = client.get_events("OVE", count="event_type.exact")
    result = client.get_recalls("OVE")
"""

import hashlib
import json
import logging
import os
import re
import ssl
import time
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Optional

# Import cache integrity module (GAP-011)
try:
    from cache_integrity import (  # type: ignore
        integrity_read,
        integrity_write,
        verify_checksum,
        invalidate_corrupt_file,
    )
    _INTEGRITY_AVAILABLE = True
except ImportError:
    _INTEGRITY_AVAILABLE = False
    integrity_read = None  # type: ignore
    integrity_write = None  # type: ignore
    verify_checksum = None  # type: ignore
    invalidate_corrupt_file = None  # type: ignore

# Import rate limiter (FDA-20)
try:
    from fda_tools.lib.rate_limiter import RateLimiter, RetryPolicy  # type: ignore
    _RATE_LIMITER_AVAILABLE = True
except ImportError:
    _RATE_LIMITER_AVAILABLE = False
    RateLimiter = None  # type: ignore
    RetryPolicy = None  # type: ignore

# Import cross-process rate limiter (FDA-12)
try:
    from fda_tools.lib.cross_process_rate_limiter import CrossProcessRateLimiter  # type: ignore
    _CROSS_PROCESS_LIMITER_AVAILABLE = True
except ImportError:
    _CROSS_PROCESS_LIMITER_AVAILABLE = False
    CrossProcessRateLimiter = None  # type: ignore

# Import PostgreSQL database module (FDA-191)
try:
    from fda_tools.lib.postgres_database import PostgreSQLDatabase  # type: ignore
    _POSTGRES_AVAILABLE = True
except ImportError:
    _POSTGRES_AVAILABLE = False
    PostgreSQLDatabase = None  # type: ignore


# Module logger (FDA-18 / GAP-014)
logger = logging.getLogger(__name__)

# Cache integrity audit logger
_cache_logger = logging.getLogger("fda.cache_integrity")

# Cache TTL in seconds (7 days)
CACHE_TTL = 7 * 24 * 60 * 60

# Max retries for transient failures
MAX_RETRIES = 5  # Increased from 3 to 5 for better 429 handling

# Base backoff in seconds (for legacy fallback)
BASE_BACKOFF = 1.0

# Rate limit defaults
UNAUTHENTICATED_RATE_LIMIT = 240  # requests per minute
AUTHENTICATED_RATE_LIMIT = 1000   # requests per minute

# API base URL
BASE_URL = "https://api.fda.gov/device"

# User agent
try:
    from version import PLUGIN_VERSION
    USER_AGENT = f"Mozilla/5.0 (FDA-Plugin/{PLUGIN_VERSION})"
except Exception:
    USER_AGENT = "Mozilla/5.0 (FDA-Plugin/0.0.0)"


class FDAClient:
    """Centralized openFDA API client with caching, retry, and rate limiting.

    Features:
    - LRU caching with 7-day TTL
    - SHA-256 integrity verification (GAP-011)
    - Thread-safe token bucket rate limiting (FDA-20)
    - Exponential backoff with retry (FDA-20)
    - Rate limit header inspection and warnings (FDA-20)
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        api_key: Optional[str] = None,
        rate_limit_override: Optional[int] = None,
        use_postgres: bool = False,
        postgres_host: str = 'localhost',
        postgres_port: int = 6432,
    ):
        """Initialize the FDA API client.

        Args:
            cache_dir: Directory for API response cache. Default: ~/fda-510k-data/api_cache/
            api_key: openFDA API key. If not provided, reads from env/settings.
            rate_limit_override: Override rate limit (requests per minute).
                Default: 240 (unauthenticated) or 1000 (with API key).
            use_postgres: Enable PostgreSQL caching (FDA-191). Default: False for backward compatibility.
            postgres_host: PostgreSQL/PgBouncer host. Default: localhost
            postgres_port: PostgreSQL/PgBouncer port. Default: 6432 (PgBouncer)
        """
        self.api_key = api_key or self._load_api_key()
        self.cache_dir = Path(cache_dir or os.path.expanduser("~/fda-510k-data/api_cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = self._check_enabled()
        self._stats = {"hits": 0, "misses": 0, "errors": 0, "corruptions": 0, "postgres_hits": 0}
        self._audit_events = []  # In-memory audit log for cache integrity events

        # Initialize PostgreSQL database (FDA-191)
        self.use_postgres = use_postgres and _POSTGRES_AVAILABLE
        self.db = None
        if self.use_postgres:
            try:
                self.db = PostgreSQLDatabase(  # type: ignore
                    host=postgres_host,
                    port=postgres_port,
                    pool_size=20  # Support 20+ concurrent agents
                )
                logger.info(
                    "PostgreSQL caching enabled (FDA-191): %s:%d",
                    postgres_host,
                    postgres_port,
                )
            except Exception as e:
                logger.warning(
                    "PostgreSQL initialization failed, falling back to JSON cache: %s", e
                )
                self.use_postgres = False
                self.db = None
        elif use_postgres and not _POSTGRES_AVAILABLE:
            logger.warning(
                "PostgreSQL requested but module not available. "
                "Falling back to JSON cache."
            )

        # Initialize rate limiter (FDA-20)
        if _RATE_LIMITER_AVAILABLE:
            # Determine rate limit based on API key presence
            if rate_limit_override:
                rate_limit = rate_limit_override
            elif self.api_key:
                rate_limit = AUTHENTICATED_RATE_LIMIT
            else:
                rate_limit = UNAUTHENTICATED_RATE_LIMIT

            self._rate_limiter = RateLimiter(requests_per_minute=rate_limit)  # type: ignore
            self._retry_policy = RetryPolicy(  # type: ignore
                max_attempts=MAX_RETRIES,
                base_delay=1.0,
                max_delay=60.0,
                jitter=True,
            )
            logger.info(
                "Rate limiting enabled: %d req/min (API key: %s)",
                rate_limit,
                "yes" if self.api_key else "no",
            )
        else:
            self._rate_limiter = None
            self._retry_policy = None
            logger.warning(
                "Rate limiter not available (lib.rate_limiter not imported). "
                "Running without rate limiting."
            )

        # Initialize cross-process rate limiter (FDA-12)
        if _CROSS_PROCESS_LIMITER_AVAILABLE:
            self._cross_process_limiter = CrossProcessRateLimiter(
                has_api_key=bool(self.api_key),
            )
            logger.info(
                "Cross-process rate limiting enabled (FDA-12): %d req/min",
                self._cross_process_limiter.requests_per_minute,
            )
        else:
            self._cross_process_limiter = None
            logger.debug(
                "Cross-process rate limiter not available (lib.cross_process_rate_limiter not imported)."
            )

    def _audit_logger(self, event):
        """Audit callback for cache integrity events.

        Captures integrity events for statistics and external logging.
        """
        self._audit_events.append(event)
        event_type = event.get("event", "")
        if event_type in ("corruption_detected", "checksum_mismatch"):
            self._stats["corruptions"] += 1

    def _load_api_key(self):
        """Load API key from environment, keyring, or settings file.

        Uses centralized secure_config module (FDA-182) for keyring support.
        Falls back to legacy behavior if secure_config is not available.
        """
        # Try secure_config first (FDA-182)
        try:
            from fda_tools.lib.secure_config import get_api_key  # type: ignore
            key = get_api_key('openfda')
            if key:
                return key
        except ImportError:
            logger.debug("secure_config not available, using legacy API key loading")

        # Legacy fallback: environment variable
        key = os.environ.get("OPENFDA_API_KEY")
        if key:
            return key

        # Legacy fallback: settings file
        settings_path = os.path.expanduser("~/.claude/fda-tools.local.md")
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                content = f.read()
            m = re.search(r"openfda_api_key:\s*(\S+)", content)
            if m and m.group(1) not in ("null", "keyring"):
                return m.group(1)
        return None

    def _check_enabled(self):
        """Check if API is enabled in settings."""
        settings_path = os.path.expanduser("~/.claude/fda-tools.local.md")
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                content = f.read()
            m = re.search(r"openfda_enabled:\s*(\S+)", content)
            if m and m.group(1).lower() == "false":
                return False
        return True

    def _cache_key(self, endpoint, params):
        """Generate a cache key from endpoint and params."""
        # Exclude api_key from cache key
        cache_params = {k: v for k, v in sorted(params.items()) if k != "api_key"}
        raw = f"{endpoint}:{json.dumps(cache_params, sort_keys=True)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _get_cached(self, cache_key):
        """Get a cached response if valid, with integrity verification.

        GAP-011: Reads cache file through integrity_read() which verifies
        the SHA-256 checksum. Corrupt files are auto-invalidated and logged.
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None

        if _INTEGRITY_AVAILABLE:
            # Use integrity-verified read with TTL check
            data = integrity_read(  # type: ignore
                cache_file,
                ttl_seconds=CACHE_TTL,
                audit_logger=self._audit_logger,
                auto_invalidate=True,
            )
            if data is not None:
                self._stats["hits"] += 1
            return data
        else:
            # Fallback: original behavior if cache_integrity not importable
            try:
                with open(cache_file) as f:
                    cached = json.load(f)

                # Check TTL
                cached_at = cached.get("_cached_at", 0)
                if time.time() - cached_at > CACHE_TTL:
                    cache_file.unlink(missing_ok=True)
                    return None

                self._stats["hits"] += 1
                return cached.get("data")
            except (json.JSONDecodeError, OSError):
                _cache_logger.warning(
                    "Cache read failed (no integrity module): %s", cache_file
                )
                return None

    def _get_postgres_cached(self, endpoint, params):
        """Get a cached response from PostgreSQL if valid.

        FDA-193: Query PostgreSQL database for cached OpenFDA records.
        Extracts record ID from search parameter and checks TTL freshness.

        Args:
            endpoint: API endpoint name ('510k', 'classification', etc.)
            params: Query parameters dict with 'search' parameter

        Returns:
            Cached OpenFDA response dict if found and fresh, None otherwise
        """
        if not self.db:
            return None

        # Extract record ID from search parameter
        search_param = params.get("search", "")
        if not search_param:
            return None

        # Parse search parameter to extract primary key
        # Format: "k_number:K123456" or "product_code:DQY"
        record_id = None
        if ":" in search_param:
            field, value = search_param.split(":", 1)
            # Remove quotes if present
            record_id = value.strip('"').strip("'")

        if not record_id:
            return None

        try:
            # Query PostgreSQL by primary key
            result = self.db.get_record(endpoint, record_id)
            if not result:
                return None

            # Check TTL freshness
            cached_at = result.get("cached_at")
            if cached_at and self.db.is_stale(endpoint, cached_at):
                return None

            # Return the full OpenFDA response
            openfda_json = result.get("openfda_json")
            if openfda_json:
                logger.debug(
                    "PostgreSQL cache hit: %s %s (cached %s)",
                    endpoint, record_id, cached_at
                )
                return openfda_json

        except Exception as e:
            logger.warning(
                "PostgreSQL query error for %s %s: %s",
                endpoint, record_id, e
            )

        return None

    def _set_cached(self, cache_key, data):
        """Cache a response with integrity envelope and atomic write.

        GAP-011: Uses integrity_write() for atomic writes with SHA-256
        checksum envelope. Prevents partial file corruption on crash.
        """
        cache_file = self.cache_dir / f"{cache_key}.json"

        if _INTEGRITY_AVAILABLE:
            integrity_write(  # type: ignore
                cache_file, data, audit_logger=self._audit_logger
            )
        else:
            # Fallback: original behavior
            try:
                with open(cache_file, "w") as f:
                    json.dump({"_cached_at": time.time(), "data": data}, f)
            except OSError:
                pass  # Cache write failures are non-fatal

    def _request(self, endpoint: str, params: Dict[str, str]) -> Dict:
        """Make an API request with rate limiting, retry, and exponential backoff.

        Implements:
        - Three-tier fallback: PostgreSQL → JSON cache → API (FDA-191)
        - Rate limiting (token bucket, configurable 240 or 1000 req/min)
        - Cache-first lookup
        - Exponential backoff with jitter
        - 429 (Rate Limit) detection and handling
        - Rate limit header parsing and warnings
        - Comprehensive error logging

        Args:
            endpoint: API endpoint (e.g., '510k', 'classification')
            params: Query parameters dict

        Returns:
            Parsed JSON response dict, or error dict with 'degraded': True
        """
        if not self.enabled:
            return {"error": "API disabled", "degraded": True}

        # Tier 1: PostgreSQL cache (if enabled) - FDA-191
        if self.use_postgres and self.db:
            try:
                postgres_cached = self._get_postgres_cached(endpoint, params)
                if postgres_cached is not None:
                    self._stats["postgres_hits"] += 1
                    return postgres_cached
            except Exception as e:
                logger.warning(
                    "PostgreSQL cache query failed, falling back to JSON: %s", e
                )

        # Tier 2: JSON file cache
        key = self._cache_key(endpoint, params)
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        self._stats["misses"] += 1

        # Rate limiting: Use cross-process limiter (FDA-104) when available,
        # fall back to in-memory limiter for single-process use
        if self._cross_process_limiter:
            # FDA-12: Cross-process rate limit check (file-based lock)
            xp_acquired = self._cross_process_limiter.acquire(timeout=120.0)
            if not xp_acquired:
                self._stats["errors"] += 1
                logger.error(
                    "Cross-process rate limit timeout (120s) - "
                    "too many concurrent FDA API processes"
                )
                return {
                    "error": "Cross-process rate limit timeout after 120s",
                    "degraded": True,
                }
        elif self._rate_limiter:
            # Fallback to in-memory rate limiter (single-process only)
            acquired = self._rate_limiter.acquire(tokens=1, timeout=120.0)
            if not acquired:
                self._stats["errors"] += 1
                logger.error("Rate limit acquisition timeout (120s) - API may be overloaded")
                return {
                    "error": "Rate limit acquisition timeout after 120s",
                    "degraded": True,
                }

        # Add API key if available
        if self.api_key:
            params["api_key"] = self.api_key

        # openFDA expects + as URL-encoded spaces in search queries;
        # urlencode converts spaces to + but literal + to %2B (which breaks AND/OR).
        # Fix: replace + with space in search before encoding.
        if "search" in params:
            params["search"] = params["search"].replace("+", " ")
        url = f"{BASE_URL}/{endpoint}.json?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        # FDA-107: Create SSL context with certificate verification enabled
        ssl_context = ssl.create_default_context()

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=15, context=ssl_context) as resp:
                    # Parse response
                    data = json.loads(resp.read())

                    # Update rate limiter from response headers
                    if self._rate_limiter:
                        # urllib.request.urlopen returns http.client.HTTPResponse
                        # Headers accessible via .headers (HTTPMessage object)
                        headers_dict = dict(resp.headers)
                        self._rate_limiter.update_from_headers(headers_dict)

                    # Cache and return
                    self._set_cached(key, data)
                    return data

            except urllib.error.HTTPError as e:
                # Parse headers from HTTPError (has .headers attribute)
                error_headers = dict(e.headers) if hasattr(e, "headers") else {}

                if e.code == 404:
                    # Not found is a valid response, cache it
                    result = {"results": [], "meta": {"results": {"total": 0}}}
                    self._set_cached(key, result)
                    return result

                elif e.code == 429:
                    # Rate limited -- use retry policy
                    logger.warning(
                        "Rate limit exceeded (429) on attempt %d/%d for %s",
                        attempt + 1,
                        MAX_RETRIES,
                        endpoint,
                    )

                    # Update rate limiter with headers (may contain X-RateLimit-* info)
                    if self._rate_limiter and error_headers:
                        self._rate_limiter.update_from_headers(error_headers)

                    # Calculate retry delay
                    if self._retry_policy:
                        retry_delay = self._retry_policy.get_retry_delay(attempt, error_headers)
                    else:
                        # Fallback to simple exponential backoff
                        retry_delay = BASE_BACKOFF * (2 ** attempt) * 2

                    if retry_delay is None:
                        # Max retries reached
                        logger.error(
                            "Max retries exceeded after 429 rate limit for %s",
                            endpoint,
                        )
                        break

                    logger.info("Waiting %.2fs before retry (429 rate limit)", retry_delay)
                    time.sleep(retry_delay)
                    last_error = e

                elif e.code >= 500:
                    # Server error -- retry with backoff
                    logger.warning(
                        "Server error %d on attempt %d/%d for %s: %s",
                        e.code,
                        attempt + 1,
                        MAX_RETRIES,
                        endpoint,
                        e.reason,
                    )

                    if self._retry_policy:
                        retry_delay = self._retry_policy.get_retry_delay(attempt)
                    else:
                        retry_delay = BASE_BACKOFF * (2 ** attempt)

                    if retry_delay is None:
                        break

                    logger.info("Waiting %.2fs before retry (server error)", retry_delay)
                    time.sleep(retry_delay)
                    last_error = e

                else:
                    # Client error (400, 403, etc.) -- don't retry
                    self._stats["errors"] += 1
                    logger.error(
                        "Client error %d for %s: %s",
                        e.code,
                        endpoint,
                        e.reason,
                    )
                    return {"error": f"HTTP {e.code}: {e.reason}", "degraded": True}

            except Exception as e:
                # Network error, timeout, etc. -- retry
                logger.warning(
                    "Request error on attempt %d/%d for %s: %s",
                    attempt + 1,
                    MAX_RETRIES,
                    endpoint,
                    str(e),
                )

                if self._retry_policy:
                    retry_delay = self._retry_policy.get_retry_delay(attempt)
                else:
                    retry_delay = BASE_BACKOFF * (2 ** attempt)

                if retry_delay is None:
                    break

                logger.info("Waiting %.2fs before retry (request error)", retry_delay)
                time.sleep(retry_delay)
                last_error = e

        # All retries exhausted
        self._stats["errors"] += 1
        logger.error(
            "API request failed after %d retries for %s: %s",
            MAX_RETRIES,
            endpoint,
            last_error,
        )
        return {
            "error": f"API unavailable after {MAX_RETRIES} retries: {last_error}",
            "degraded": True,
        }

    # --- Convenience Methods ---

    def get_510k(self, k_number):
        """Look up a 510(k) clearance by K-number."""
        return self._request("510k", {"search": f'k_number:"{k_number}"', "limit": "1"})

    def get_classification(self, product_code):
        """Look up device classification by product code."""
        return self._request(
            "classification", {"search": f'product_code:"{product_code}"', "limit": "1"}
        )

    def get_clearances(self, product_code, limit=100, sort="decision_date:desc"):
        """Get all 510(k) clearances for a product code."""
        params = {"search": f'product_code:"{product_code}"', "limit": str(limit)}
        if sort:
            params["sort"] = sort
        return self._request("510k", params)

    def batch_510k(self, k_numbers, limit=None):
        """Look up multiple K-numbers in a single API call using OR query."""
        if not k_numbers:
            return {"results": [], "meta": {"results": {"total": 0}}}
        search = "+OR+".join(f'k_number:"{k}"' for k in k_numbers)
        return self._request("510k", {
            "search": search,
            "limit": str(limit or len(k_numbers))
        })

    def get_events(self, product_code, count=None, limit=100):
        """Get MAUDE adverse events for a product code."""
        params = {
            "search": f'device.device_report_product_code:"{product_code}"',
            "limit": str(limit),
        }
        if count:
            params["count"] = count
            del params["limit"]
        return self._request("event", params)

    def get_recalls(self, product_code, limit=10):
        """Get recall events for a product code."""
        return self._request(
            "recall", {"search": f'product_code:"{product_code}"', "limit": str(limit)}
        )

    def get_pma(self, pma_number):
        """Look up a PMA approval by P-number."""
        return self._request("pma", {"search": f'pma_number:"{pma_number}"', "limit": "1"})

    def get_pma_supplements(self, pma_number, limit=50):
        """Get PMA supplements for a base PMA number."""
        return self._request(
            "pma", {"search": f'pma_number:"{pma_number}"', "limit": str(limit)}
        )

    def get_pma_by_product_code(self, product_code, limit=50):
        """Get PMA approvals for a product code."""
        return self._request(
            "pma", {"search": f'product_code:"{product_code}"', "limit": str(limit)}
        )

    def search_pma(self, product_code=None, applicant=None, device_name=None,
                   advisory_committee=None, year_start=None, year_end=None,
                   limit=50, sort=None):
        """Search PMA database with combined filters.

        Args:
            product_code: Filter by product code
            applicant: Filter by applicant name
            device_name: Free-text search against trade_name
            advisory_committee: Filter by advisory committee code
            year_start: Start year (YYYY) for decision_date range
            year_end: End year (YYYY) for decision_date range
            limit: Max results (default 50)
            sort: Sort field and direction (e.g., 'decision_date:desc')

        Returns:
            API response dict with results list and meta
        """
        parts = []
        if product_code:
            parts.append(f'product_code:"{product_code}"')
        if applicant:
            parts.append(f'applicant:"{applicant}"')
        if device_name:
            parts.append(f'trade_name:"{device_name}"')
        if advisory_committee:
            parts.append(f'advisory_committee:"{advisory_committee}"')
        if year_start or year_end:
            start = f"{year_start}0101" if year_start else "19760101"
            end = f"{year_end}1231" if year_end else "29991231"
            parts.append(f"decision_date:[{start}+TO+{end}]")
        if not parts:
            return {"error": "Provide at least one search filter", "degraded": True}
        search = "+AND+".join(parts)
        params = {"search": search, "limit": str(limit)}
        if sort:
            params["sort"] = sort
        return self._request("pma", params)

    def batch_pma(self, pma_numbers, limit=None):
        """Look up multiple PMA numbers in a single API call using OR query.

        Args:
            pma_numbers: List of PMA numbers (e.g., ['P170019', 'P200024'])
            limit: Max results (defaults to len of pma_numbers)

        Returns:
            API response dict with results list
        """
        if not pma_numbers:
            return {"results": [], "meta": {"results": {"total": 0}}}
        search = "+OR+".join(f'pma_number:"{p}"' for p in pma_numbers)
        return self._request("pma", {
            "search": search,
            "limit": str(limit or len(pma_numbers))
        })

    def get_udi(self, product_code=None, company_name=None, di=None, limit=10):
        """Look up UDI/GUDID records by product code, company, or device identifier."""
        if di:
            search = f'identifiers.id:"{di}"'
        elif product_code and company_name:
            search = f'product_codes.code:"{product_code}"+AND+company_name:"{company_name}"'
        elif product_code:
            search = f'product_codes.code:"{product_code}"'
        elif company_name:
            search = f'company_name:"{company_name}"'
        else:
            return {"error": "Provide product_code, company_name, or di", "degraded": True}
        return self._request("udi", {"search": search, "limit": str(limit)})

    def search_510k(self, query=None, product_code=None, applicant=None,
                    year_start=None, year_end=None, limit=25, sort=None):
        """Interactive 510(k) database search with combined filters.

        Args:
            query: Free-text search against device_name
            product_code: Filter by product code
            applicant: Filter by applicant name
            year_start: Start year (YYYY) for decision_date range
            year_end: End year (YYYY) for decision_date range
            limit: Max results (default 25)
            sort: Sort field and direction (e.g., 'decision_date:desc')
        """
        parts = []
        if query:
            parts.append(f'device_name:"{query}"')
        if product_code:
            parts.append(f'product_code:"{product_code}"')
        if applicant:
            parts.append(f'applicant:"{applicant}"')
        if year_start or year_end:
            start = f"{year_start}0101" if year_start else "19760101"
            end = f"{year_end}1231" if year_end else "29991231"
            parts.append(f"decision_date:[{start}+TO+{end}]")
        if not parts:
            return {"error": "Provide at least one search filter", "degraded": True}
        search = "+AND+".join(parts)
        params = {"search": search, "limit": str(limit)}
        if sort:
            params["sort"] = sort
        return self._request("510k", params)

    def validate_device(self, device_number):
        """Validate a device number (K, P, DEN, or N-number) against FDA data."""
        num = device_number.upper()
        if num.startswith("K"):
            return self.get_510k(device_number)
        elif num.startswith("P"):
            return self.get_pma(device_number)
        elif num.startswith("DEN"):
            # De Novo: some indexed in 510k endpoint, no dedicated endpoint
            result = self.get_510k(device_number)
            if result.get("results") or result.get("meta", {}).get("results", {}).get("total", 0) > 0:
                return result
            # Not found in 510k -- return informative result
            return {"results": [], "meta": {"results": {"total": 0}},
                    "note": "DEN number not found in 510k endpoint. openFDA has no dedicated De Novo endpoint."}
        elif num.startswith("N"):
            return {"error": "N-numbers (Pre-Amendments) are not in openFDA. Use flat file lookup.",
                    "degraded": True, "n_number": True}
        else:
            return {"error": f"Unsupported device number format: {device_number}", "degraded": True}

    def get_all_product_codes(self, use_cache=True):
        """Enumerate ALL FDA product codes from classification database.

        Returns a list of all product codes (~2000 codes total).
        Uses pagination to retrieve all results.

        Args:
            use_cache: If True, uses cached results (recommended for performance)

        Returns:
            List of product code strings (e.g., ['DQY', 'MAX', 'OVE', ...])
        """
        cache_file = self.cache_dir / "all_product_codes.json"
        product_code_ttl = 30 * 24 * 60 * 60  # 30 days

        # Try cache first if enabled
        if use_cache and cache_file.exists():
            if _INTEGRITY_AVAILABLE:
                data = integrity_read(  # type: ignore
                    cache_file,
                    ttl_seconds=product_code_ttl,
                    audit_logger=self._audit_logger,
                    auto_invalidate=True,
                )
                if data is not None:
                    return data.get("codes", data) if isinstance(data, dict) else data
            else:
                try:
                    with open(cache_file) as f:
                        cached = json.load(f)
                    if time.time() - cached.get("_cached_at", 0) < product_code_ttl:
                        return cached.get("codes", [])
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("Failed to read product code cache: %s", e)

        # Fetch all product codes via pagination
        all_codes = set()
        limit = 1000  # Max per request
        skip = 0

        logger.info("Enumerating all FDA product codes (this may take a minute)...")

        while True:
            result = self._request("classification", {"limit": str(limit), "skip": str(skip)})

            if result.get("degraded"):
                logger.warning("API degraded during enumeration: %s", result.get('error'))
                break

            results = result.get("results", [])
            if not results:
                break

            # Extract product codes
            for item in results:
                code = item.get("product_code")
                if code:
                    all_codes.add(code.upper())

            logger.debug("Fetched %d devices (total codes: %d)", len(results), len(all_codes))

            # Check if there are more results
            total = result.get("meta", {}).get("results", {}).get("total", 0)
            if skip + len(results) >= total:
                break

            skip += limit
            time.sleep(0.3)  # Rate limiting

        codes_list = sorted(list(all_codes))

        # Cache results with integrity envelope
        cache_data = {"codes": codes_list, "total": len(codes_list)}
        if _INTEGRITY_AVAILABLE:
            integrity_write(  # type: ignore
                cache_file, cache_data, audit_logger=self._audit_logger
            )
        else:
            try:
                with open(cache_file, "w") as f:
                    json.dump({
                        "_cached_at": time.time(),
                        "codes": codes_list,
                        "total": len(codes_list)
                    }, f, indent=2)
            except OSError as e:
                logger.warning("Failed to cache product codes: %s", e)

        logger.info("Found %d product codes (cached for 30 days)", len(codes_list))
        return codes_list

    def get_device_characteristics(self, product_code):
        """Get enhanced device characteristics for AI analysis.

        Retrieves device classification info plus recent 510(k) clearances
        to provide richer context for standards determination.

        Args:
            product_code: FDA product code (e.g., 'DQY')

        Returns:
            Dictionary with enhanced device information including:
                - product_code, name, class, regulation, review_panel, medical_specialty
                - recent_clearances: list of recent K-numbers with decision dates
                - submission_volume: approximate number of clearances (last 5 years)
        """
        # Get classification info
        classification = self.get_classification(product_code)

        if not classification.get("results"):
            return {
                "product_code": product_code,
                "name": "Unknown Device",
                "class": "",
                "regulation": "",
                "review_panel": "",
                "medical_specialty": "",
                "error": "Product code not found in classification database"
            }

        device = classification["results"][0]

        # Get recent clearances for additional context
        clearances = self.get_clearances(product_code, limit=5, sort="decision_date:desc")
        recent_clearances = []
        if clearances.get("results"):
            for item in clearances["results"]:
                recent_clearances.append({
                    "k_number": item.get("k_number"),
                    "decision_date": item.get("decision_date"),
                    "device_name": item.get("device_name", "")[:100]  # Truncate long names
                })

        # Get total submission volume (approximate)
        volume_result = self.get_clearances(product_code, limit=1)
        submission_volume = volume_result.get("meta", {}).get("results", {}).get("total", 0)

        return {
            "product_code": product_code,
            "name": device.get("device_name", "Unknown Device"),
            "class": device.get("device_class", ""),
            "regulation": device.get("regulation_number", ""),
            "review_panel": device.get("review_panel", ""),
            "medical_specialty": device.get("medical_specialty", ""),
            "recent_clearances": recent_clearances,
            "submission_volume": submission_volume
        }

    # --- Cache Management ---

    def cache_stats(self) -> Dict:
        """Return cache statistics including integrity and rate limiting metrics."""
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        expired = 0
        valid = 0
        integrity_verified = 0
        legacy_format = 0
        corrupt = 0

        for f in cache_files:
            try:
                if _INTEGRITY_AVAILABLE:
                    is_valid, reason = verify_checksum(f)  # type: ignore
                    if reason == "valid":
                        integrity_verified += 1
                    elif reason == "legacy_format":
                        legacy_format += 1
                    elif not is_valid:
                        corrupt += 1
                        expired += 1
                        continue

                with open(f) as fh:
                    data = json.load(fh)
                if time.time() - data.get("_cached_at", 0) > CACHE_TTL:
                    expired += 1
                else:
                    valid += 1
            except (json.JSONDecodeError, OSError):
                expired += 1
                corrupt += 1

        stats = {
            "cache_dir": str(self.cache_dir),
            "total_files": len(cache_files),
            "valid": valid,
            "expired": expired,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "session_hits": self._stats["hits"],
            "session_misses": self._stats["misses"],
            "session_errors": self._stats["errors"],
            "session_corruptions": self._stats["corruptions"],
            "integrity_verified": integrity_verified,
            "legacy_format": legacy_format,
            "corrupt_detected": corrupt,
        }

        # Add rate limiting stats (FDA-20)
        if self._rate_limiter:
            stats["rate_limiting"] = self._rate_limiter.get_stats()

        # FDA-13: Add PMA SSED cache size info if available
        try:
            pma_cache_dir = Path(os.path.expanduser("~/fda-510k-data/pma_cache"))
            if pma_cache_dir.exists():
                pma_pdf_size = sum(
                    f.stat().st_size for f in pma_cache_dir.rglob("*.pdf")
                )
                pma_pdf_count = sum(1 for _ in pma_cache_dir.rglob("*.pdf"))
                stats["pma_ssed_cache"] = {
                    "pdf_count": pma_pdf_count,
                    "total_size_mb": round(pma_pdf_size / (1024 * 1024), 2),
                }
        except OSError:
            pass  # Non-fatal: PMA cache stats are supplementary

        # FDA-12: Add cross-process rate limit status
        if self._cross_process_limiter:
            stats["cross_process_rate_limit"] = self._cross_process_limiter.get_status()

        return stats

    def rate_limit_stats(self) -> Optional[Dict]:
        """Get rate limiter statistics.

        Returns:
            Dictionary with rate limiting stats, or None if rate limiter not available.
            Includes:
            - total_requests: Total API requests made
            - total_waits: Number of times requests had to wait for tokens
            - total_wait_time_seconds: Cumulative wait time
            - avg_wait_time_seconds: Average wait time per blocked request
            - wait_percentage: Percentage of requests that had to wait
            - rate_limit_warnings: Number of "approaching limit" warnings
            - dynamic_adjustments: Number of times rate limit was adjusted
            - current_tokens: Current token bucket level
            - requests_per_minute: Configured rate limit
        """
        if self._rate_limiter:
            return self._rate_limiter.get_stats()
        return None

    def clear_cache(self, category=None):
        """Clear cached API responses.

        Args:
            category: None for all, or 'api', 'expired' to clear specific types.
        """
        count = 0
        if category == "expired":
            for f in self.cache_dir.glob("*.json"):
                try:
                    with open(f) as fh:
                        data = json.load(fh)
                    if time.time() - data.get("_cached_at", 0) > CACHE_TTL:
                        f.unlink()
                        count += 1
                except (json.JSONDecodeError, OSError):
                    f.unlink()
                    count += 1
        else:
            for f in self.cache_dir.glob("*.json"):
                f.unlink()
                count += 1

        return count

    def get_audit_events(self):
        """Return cache integrity audit events from this session.

        Returns:
            List of audit event dictionaries.
        """
        return list(self._audit_events)

    def close(self):
        """Close PostgreSQL connection pool and cleanup resources.

        FDA-193: Properly close connection pool when client is no longer needed.
        Safe to call multiple times (idempotent).
        """
        if self.db:
            try:
                self.db.close()
                logger.debug("Closed PostgreSQL connection pool")
            except Exception as e:
                logger.warning("Error closing PostgreSQL connection pool: %s", e)
            finally:
                self.db = None

    def __del__(self):
        """Cleanup on object deletion (FDA-193)."""
        self.close()


def main():
    """CLI for testing the API client."""
    import argparse

    parser = argparse.ArgumentParser(description="FDA API Client")
    parser.add_argument("--test", action="store_true", help="Test all endpoints")
    parser.add_argument("--stats", action="store_true", help="Show cache stats")
    parser.add_argument("--clear", action="store_true", help="Clear cache")
    parser.add_argument("--clear-expired", action="store_true", help="Clear expired cache")
    parser.add_argument("--lookup", help="Look up a device number (K/P/DEN)")
    parser.add_argument("--classify", help="Classify a product code")
    parser.add_argument("--get-all-codes", action="store_true", help="Enumerate all FDA product codes")
    parser.add_argument("--health-check", action="store_true", dest="health_check",
                        help="Run health check including cross-process rate limit status (FDA-12)")
    args = parser.parse_args()

    client = FDAClient()

    if args.test:
        print("Testing openFDA API endpoints...")
        tests = [
            ("510k", lambda: client.get_510k("K241335")),
            ("classification", lambda: client.get_classification("OVE")),
            ("events", lambda: client.get_events("OVE", count="event_type.exact")),
            ("recalls", lambda: client.get_recalls("OVE")),
        ]
        for name, fn in tests:
            result = fn()
            if result.get("degraded"):
                print(f"  {name:20s}  DEGRADED: {result.get('error')}")
            else:
                total = result.get("meta", {}).get("results", {}).get("total", "?")
                print(f"  {name:20s}  OK ({total} results)")
            time.sleep(0.5)

    elif args.stats:
        stats = client.cache_stats()
        print("=" * 60)
        print("CACHE STATISTICS")
        print("=" * 60)
        print(f"Cache directory: {stats['cache_dir']}")
        print(f"Files: {stats['total_files']} ({stats['valid']} valid, {stats['expired']} expired)")
        print(f"Size: {stats['total_size_mb']} MB")
        print(f"Integrity: {stats['integrity_verified']} verified, "
              f"{stats['legacy_format']} legacy, {stats['corrupt_detected']} corrupt")
        print(f"Session: {stats['session_hits']} hits, {stats['session_misses']} misses, "
              f"{stats['session_errors']} errors")

        # Show rate limiting stats if available
        if "rate_limiting" in stats:
            rl = stats["rate_limiting"]
            print("\n" + "=" * 60)
            print("RATE LIMITING STATISTICS (FDA-20)")
            print("=" * 60)
            print(f"Rate limit: {rl['requests_per_minute']} req/min")
            print(f"Total requests: {rl['total_requests']}")
            print(f"Requests blocked: {rl['total_waits']} ({rl['wait_percentage']:.1f}%)")
            if rl['total_waits'] > 0:
                print(f"Average wait time: {rl['avg_wait_time_seconds']:.3f}s")
                print(f"Total wait time: {rl['total_wait_time_seconds']:.1f}s")
            print(f"Rate limit warnings: {rl['rate_limit_warnings']}")
            print(f"Current tokens: {rl['current_tokens']:.1f} / {rl['requests_per_minute']}")

        # FDA-12: Show cross-process rate limit status
        if "cross_process_rate_limit" in stats:
            xp = stats["cross_process_rate_limit"]
            print("\n" + "=" * 60)
            print("CROSS-PROCESS RATE LIMITING (FDA-12)")
            print("=" * 60)
            print(f"Requests in last minute: {xp.get('requests_last_minute', 'N/A')}")
            print(f"Rate limit: {xp.get('requests_per_minute', 'N/A')} req/min")
            print(f"Utilization: {xp.get('utilization_percent', 'N/A')}%")
            print(f"Available: {xp.get('available', 'N/A')} requests")
            print(f"State file: {xp.get('state_file', 'N/A')}")
            print(f"Lock file: {xp.get('lock_file', 'N/A')}")
            print(f"Current PID: {xp.get('pid', 'N/A')}")
        print("=" * 60)

    elif args.clear:
        count = client.clear_cache()
        print(f"Cleared {count} cached responses")

    elif args.clear_expired:
        count = client.clear_cache("expired")
        print(f"Cleared {count} expired cached responses")

    elif args.lookup:
        result = client.validate_device(args.lookup)
        print(json.dumps(result, indent=2))

    elif args.classify:
        result = client.get_classification(args.classify)
        if result.get("results"):
            r = result["results"][0]
            print(f"Product Code: {r.get('product_code')}")
            print(f"Device Name: {r.get('device_name')}")
            print(f"Class: {r.get('device_class')}")
            print(f"Regulation: {r.get('regulation_number')}")
        else:
            print(f"Not found: {args.classify}")

    elif args.get_all_codes:
        codes = client.get_all_product_codes()
        for code in codes:
            print(code)

    elif args.health_check:
        # FDA-12: Health check with cross-process rate limit status
        print("=" * 60)
        print("FDA API CLIENT HEALTH CHECK")
        print("=" * 60)

        # API connectivity
        print("\n[API Connectivity]")
        print(f"  API enabled: {client.enabled}")
        print(f"  API key: {'configured' if client.api_key else 'not configured'}")

        # Cache stats
        cache = client.cache_stats()
        print(f"\n[Cache]")
        print(f"  Directory: {cache['cache_dir']}")
        print(f"  Files: {cache['total_files']} ({cache['valid']} valid)")
        print(f"  Size: {cache['total_size_mb']} MB")

        # In-process rate limiter
        print(f"\n[In-Process Rate Limiter (FDA-20)]")
        if client._rate_limiter:
            rl = client._rate_limiter.get_stats()
            print(f"  Status: active")
            print(f"  Rate limit: {rl['requests_per_minute']} req/min")
            print(f"  Tokens available: {rl['current_tokens']:.0f}")
        else:
            print(f"  Status: not available")

        # Cross-process rate limiter
        print(f"\n[Cross-Process Rate Limiter (FDA-12)]")
        if client._cross_process_limiter:
            health = client._cross_process_limiter.health_check()
            status = health["status"]
            print(f"  Status: {'healthy' if health['healthy'] else 'unhealthy'}")
            print(f"  Requests in window: {status.get('requests_last_minute', 'N/A')}"
                  f" / {status.get('requests_per_minute', 'N/A')}")
            print(f"  Utilization: {status.get('utilization_percent', 'N/A')}%")
            print(f"  Available: {status.get('available', 'N/A')} requests")
            print(f"  Lock file: {health['lock_exists']}")
            print(f"  State file: {health['state_exists']} "
                  f"(readable: {health['state_readable']})")
            if health["warnings"]:
                for w in health["warnings"]:
                    print(f"  WARNING: {w}")
        else:
            print(f"  Status: not available")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
