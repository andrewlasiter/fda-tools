#!/usr/bin/env python3
"""
Centralized FDA API Client with caching and retry logic.

Provides LRU caching (7-day TTL), exponential backoff retry, and degraded mode
on failure for all openFDA Device API endpoints.

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
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


# Cache TTL in seconds (7 days)
CACHE_TTL = 7 * 24 * 60 * 60

# Max retries for transient failures
MAX_RETRIES = 3

# Base backoff in seconds
BASE_BACKOFF = 1.0

# API base URL
BASE_URL = "https://api.fda.gov/device"

# User agent
USER_AGENT = "Mozilla/5.0 (FDA-Plugin/5.3.0)"


class FDAClient:
    """Centralized openFDA API client with caching and retry."""

    def __init__(self, cache_dir=None, api_key=None):
        """Initialize the FDA API client.

        Args:
            cache_dir: Directory for API response cache. Default: ~/fda-510k-data/api_cache/
            api_key: openFDA API key. If not provided, reads from env/settings.
        """
        self.api_key = api_key or self._load_api_key()
        self.cache_dir = Path(cache_dir or os.path.expanduser("~/fda-510k-data/api_cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = self._check_enabled()
        self._stats = {"hits": 0, "misses": 0, "errors": 0}

    def _load_api_key(self):
        """Load API key from environment or settings file."""
        key = os.environ.get("OPENFDA_API_KEY")
        if key:
            return key

        settings_path = os.path.expanduser("~/.claude/fda-predicate-assistant.local.md")
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                content = f.read()
            m = re.search(r"openfda_api_key:\s*(\S+)", content)
            if m and m.group(1) != "null":
                return m.group(1)
        return None

    def _check_enabled(self):
        """Check if API is enabled in settings."""
        settings_path = os.path.expanduser("~/.claude/fda-predicate-assistant.local.md")
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
        """Get a cached response if valid."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None

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
            return None

    def _set_cached(self, cache_key, data):
        """Cache a response."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump({"_cached_at": time.time(), "data": data}, f)
        except OSError:
            pass  # Cache write failures are non-fatal

    def _request(self, endpoint, params):
        """Make an API request with retry and exponential backoff.

        Returns parsed JSON data or None on failure.
        """
        if not self.enabled:
            return {"error": "API disabled", "degraded": True}

        # Check cache first
        key = self._cache_key(endpoint, params)
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        self._stats["misses"] += 1

        # Add API key if available
        if self.api_key:
            params["api_key"] = self.api_key

        url = f"{BASE_URL}/{endpoint}.json?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read())
                    self._set_cached(key, data)
                    return data
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    # Not found is a valid response, cache it
                    result = {"results": [], "meta": {"results": {"total": 0}}}
                    self._set_cached(key, result)
                    return result
                elif e.code == 429:
                    # Rate limited — wait longer
                    wait = BASE_BACKOFF * (2 ** attempt) * 2
                    time.sleep(wait)
                    last_error = e
                elif e.code >= 500:
                    # Server error — retry with backoff
                    wait = BASE_BACKOFF * (2 ** attempt)
                    time.sleep(wait)
                    last_error = e
                else:
                    # Client error (400, 403, etc.) — don't retry
                    self._stats["errors"] += 1
                    return {"error": f"HTTP {e.code}: {e.reason}", "degraded": True}
            except Exception as e:
                wait = BASE_BACKOFF * (2 ** attempt)
                time.sleep(wait)
                last_error = e

        # All retries exhausted
        self._stats["errors"] += 1
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

    def get_clearances(self, product_code, limit=100):
        """Get all 510(k) clearances for a product code."""
        return self._request(
            "510k", {"search": f'product_code:"{product_code}"', "limit": str(limit)}
        )

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
            sort: Sort field (not directly supported by openFDA, applied client-side)
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
        return self._request("510k", {"search": search, "limit": str(limit)})

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
            # Not found in 510k — return informative result
            return {"results": [], "meta": {"results": {"total": 0}},
                    "note": "DEN number not found in 510k endpoint. openFDA has no dedicated De Novo endpoint."}
        elif num.startswith("N"):
            return {"error": "N-numbers (Pre-Amendments) are not in openFDA. Use flat file lookup.",
                    "degraded": True, "n_number": True}
        else:
            return {"error": f"Unsupported device number format: {device_number}", "degraded": True}

    # --- Cache Management ---

    def cache_stats(self):
        """Return cache statistics."""
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        expired = 0
        valid = 0
        for f in cache_files:
            try:
                with open(f) as fh:
                    data = json.load(fh)
                if time.time() - data.get("_cached_at", 0) > CACHE_TTL:
                    expired += 1
                else:
                    valid += 1
            except (json.JSONDecodeError, OSError):
                expired += 1

        return {
            "cache_dir": str(self.cache_dir),
            "total_files": len(cache_files),
            "valid": valid,
            "expired": expired,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "session_hits": self._stats["hits"],
            "session_misses": self._stats["misses"],
            "session_errors": self._stats["errors"],
        }

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
        print(f"Cache directory: {stats['cache_dir']}")
        print(f"Files: {stats['total_files']} ({stats['valid']} valid, {stats['expired']} expired)")
        print(f"Size: {stats['total_size_mb']} MB")

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


if __name__ == "__main__":
    main()
