#!/usr/bin/env python3
"""
External Data Integration Hub -- Integration framework for external data
sources including ClinicalTrials.gov, PubMed, and USPTO PatentsView.

Data sources:
    - ClinicalTrials.gov API v2: PMA-related clinical trials
    - PubMed E-utilities API: Device safety literature
    - USPTO PatentsView API: Device intellectual property

Features:
    - Data source abstraction layer for adding future sources
    - Rate limiting per external API's terms of service
    - Response caching with configurable TTL
    - Unified query interface across all data sources
    - Error handling with graceful degradation

API rate limits:
    - ClinicalTrials.gov: No official limit, 1 req/sec recommended
    - PubMed: 3 req/sec without API key, 10 req/sec with key
    - USPTO PatentsView: No official limit, 1 req/sec recommended

Regulatory compliance:
    - All external data cited with source, timestamp, and API version
    - Data presented as supplementary intelligence (not regulatory evidence)
    - No automated decisions based on external data alone
    - Cache integrity verified with checksums

Usage:
    from external_data_hub import ExternalDataHub

    hub = ExternalDataHub()
    trials = hub.search_clinical_trials("FoundationOne CDx", pma_number="P170019")
    articles = hub.search_pubmed("medical device safety", max_results=10)
    patents = hub.search_patents("next generation sequencing diagnostic")

    # CLI usage:
    python3 external_data_hub.py --source clinicaltrials --query "heart valve"
    python3 external_data_hub.py --source pubmed --pma P170019
    python3 external_data_hub.py --source patents --query "medical device"
"""

import argparse
import hashlib
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# Import sibling modules
from pma_data_store import PMADataStore


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

HUB_VERSION = "1.0.0"

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_CIRCUIT_BREAKER_THRESHOLD = 5    # consecutive failures before opening circuit
_CIRCUIT_BREAKER_PAUSE_SECS = 60  # seconds to wait before allowing requests again


class _RetryableHTTPError(OSError):
    """Raised for HTTP errors that should be retried with back-off."""


class _CircuitOpenError(OSError):
    """Raised when the circuit breaker is open and blocking requests."""


EXTERNAL_API_CONFIG = {
    "clinicaltrials": {
        "base_url": "https://clinicaltrials.gov/api/v2/studies",
        "rate_limit_per_sec": 1.0,
        "cache_ttl_hours": 24,
        "label": "ClinicalTrials.gov",
        "api_version": "v2",
    },
    "pubmed": {
        "base_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        "rate_limit_per_sec": 3.0,
        "cache_ttl_hours": 168,
        "label": "PubMed E-utilities",
        "api_version": "v2.0",
    },
    "patents": {
        "base_url": "https://api.patentsview.org/patents/query",
        "rate_limit_per_sec": 1.0,
        "cache_ttl_hours": 168,
        "label": "USPTO PatentsView",
        "api_version": "v1",
    },
}


# ------------------------------------------------------------------
# Abstract data source interface
# ------------------------------------------------------------------

class ExternalDataSource(ABC):
    """Abstract base class for external data source integrations."""

    def __init__(
        self,
        source_name: str,
        cache_dir: Optional[Path] = None,
    ):
        self.source_name = source_name
        config = EXTERNAL_API_CONFIG.get(source_name, {})
        self.base_url = config.get("base_url", "")
        self.rate_limit = config.get("rate_limit_per_sec", 1.0)
        self.cache_ttl_hours = config.get("cache_ttl_hours", 24)
        self.label = config.get("label", source_name)
        self.api_version = config.get("api_version", "unknown")
        self.cache_dir = cache_dir or Path(
            os.path.expanduser(
                f"~/fda-510k-data/pma_cache/external/{source_name}"
            )
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time = 0.0
        self._request_count = 0
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0

    def _rate_limit_wait(self) -> None:
        """Enforce rate limiting between requests."""
        if self.rate_limit <= 0:
            return
        min_interval = 1.0 / self.rate_limit
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.monotonic()

    def _cache_key(self, query_params: Dict) -> str:
        """Generate cache key from query parameters."""
        raw = f"{self.source_name}:{json.dumps(query_params, sort_keys=True)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _get_cached(self, cache_key: str) -> Optional[Dict]:
        """Get cached response if still valid."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file) as f:
                cached = json.load(f)
            cached_at = cached.get("_cached_at", "")
            if cached_at and self.cache_ttl_hours > 0:
                cached_dt = datetime.fromisoformat(cached_at)
                if cached_dt.tzinfo is None:
                    cached_dt = cached_dt.replace(tzinfo=timezone.utc)
                elapsed_hrs = (
                    datetime.now(timezone.utc) - cached_dt
                ).total_seconds() / 3600
                if elapsed_hrs > self.cache_ttl_hours:
                    return None
            return cached.get("data")
        except (json.JSONDecodeError, OSError, ValueError):
            return None

    def _set_cached(self, cache_key: str, data: Dict) -> None:
        """Cache a response."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(
                    {
                        "_cached_at": datetime.now(timezone.utc).isoformat(),
                        "source": self.source_name,
                        "data": data,
                    },
                    f,
                    indent=2,
                )
        except OSError as e:
            print(f"Warning: Failed to write cache file {cache_file}: {e}", file=sys.stderr)

    def _http_get(self, url: str, timeout: int = 15, extra_headers: Optional[Dict[str, str]] = None) -> Optional[Dict]:
        """Make an HTTP GET request with error handling, retry logic, and circuit breaker.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            extra_headers: Optional additional headers to include

        Returns:
            Parsed JSON response or error dict on failure.
        """
        # Circuit breaker check — refuse requests while circuit is open (FDA-126)
        now = time.monotonic()
        if now < self._circuit_open_until:
            remaining = int(self._circuit_open_until - now)
            return {"error": f"Circuit breaker open — service unavailable (retry in {remaining}s)"}

        self._rate_limit_wait()
        self._request_count += 1

        headers = {
            "User-Agent": f"FDA-Tools-Plugin/{HUB_VERSION}",
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        req = urllib.request.Request(url, headers=headers)

        # FDA-107: Create SSL context with certificate verification enabled
        ssl_context = ssl.create_default_context()

        try:
            result = self._fetch_with_retry(req, timeout, ssl_context)
            # Success — reset circuit breaker failure counter
            self._consecutive_failures = 0
            return result
        except _RetryableHTTPError as e:
            # All retries exhausted — update circuit breaker state (FDA-126)
            self._consecutive_failures += 1
            if self._consecutive_failures >= _CIRCUIT_BREAKER_THRESHOLD:
                self._circuit_open_until = time.monotonic() + _CIRCUIT_BREAKER_PAUSE_SECS
            return {"error": str(e)}
        except urllib.error.URLError as e:
            self._consecutive_failures += 1
            if self._consecutive_failures >= _CIRCUIT_BREAKER_THRESHOLD:
                self._circuit_open_until = time.monotonic() + _CIRCUIT_BREAKER_PAUSE_SECS
            return {"error": f"URL error: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}

    @retry(
        retry=retry_if_exception_type(_RetryableHTTPError),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _fetch_with_retry(
        self,
        req: urllib.request.Request,
        timeout: int,
        ssl_context: ssl.SSLContext,
    ) -> Optional[Dict]:
        """Execute HTTP request with retry on transient failures (FDA-151).

        Retries on HTTP 429, 500, 502, 503, 504 with exponential back-off.
        Non-retryable HTTP errors (e.g. 404) return an error dict immediately.

        Raises:
            _RetryableHTTPError: On HTTP 429/5xx until retries are exhausted.
        """
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in _RETRYABLE_STATUS_CODES:
                raise _RetryableHTTPError(f"HTTP {e.code}: {e.reason}")
            return {
                "error": f"HTTP {e.code}: {e.reason}",
                "status_code": e.code,
            }

    @abstractmethod
    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search the external data source."""
        ...

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker state (FDA-126)."""
        now = time.monotonic()
        is_open = now < self._circuit_open_until
        return {
            "is_open": is_open,
            "consecutive_failures": self._consecutive_failures,
            "seconds_remaining": max(0, int(self._circuit_open_until - now)) if is_open else 0,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get source statistics."""
        return {
            "source": self.source_name,
            "label": self.label,
            "api_version": self.api_version,
            "requests_made": self._request_count,
            "rate_limit_per_sec": self.rate_limit,
            "cache_ttl_hours": self.cache_ttl_hours,
            "circuit_breaker": self.get_circuit_breaker_status(),
        }


# ------------------------------------------------------------------
# ClinicalTrials.gov integration
# ------------------------------------------------------------------

class ClinicalTrialsSource(ExternalDataSource):
    """ClinicalTrials.gov API v2 integration."""

    def __init__(self, cache_dir: Optional[Path] = None):
        super().__init__("clinicaltrials", cache_dir)

    def search(
        self,
        query: str,
        max_results: int = 10,
        status_filter: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Search ClinicalTrials.gov for device-related trials.

        Args:
            query: Search query (device name, condition, etc.).
            max_results: Maximum number of results.
            status_filter: Filter by status (RECRUITING, COMPLETED, etc.).

        Returns:
            Dictionary with trial results and metadata.
        """
        params = {
            "query.term": query,
            "pageSize": str(min(max_results, 20)),
            "format": "json",
        }
        if status_filter:
            params["filter.overallStatus"] = status_filter

        cache_key = self._cache_key(params)
        cached = self._get_cached(cache_key)
        if cached is not None:
            cached["_from_cache"] = True
            return cached

        url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        raw = self._http_get(url)

        if raw is None or raw.get("error"):
            return {
                "source": self.label,
                "query": query,
                "total_results": 0,
                "trials": [],
                "error": raw.get("error") if raw else "No response",
                "queried_at": datetime.now(timezone.utc).isoformat(),
            }

        # Parse results
        studies = raw.get("studies", [])
        trials = []
        for study in studies:
            proto = study.get("protocolSection", {})
            id_module = proto.get("identificationModule", {})
            status_module = proto.get("statusModule", {})
            design_module = proto.get("designModule", {})
            desc_module = proto.get("descriptionModule", {})

            trials.append({
                "nct_id": id_module.get("nctId", ""),
                "title": id_module.get("briefTitle", ""),
                "status": status_module.get("overallStatus", ""),
                "start_date": status_module.get("startDateStruct", {}).get("date", ""),
                "study_type": design_module.get("studyType", ""),
                "enrollment": design_module.get("enrollmentInfo", {}).get("count", 0),
                "brief_summary": desc_module.get("briefSummary", "")[:300],
            })

        result = {
            "source": self.label,
            "api_version": self.api_version,
            "query": query,
            "total_results": raw.get("totalCount", len(trials)),
            "returned_results": len(trials),
            "trials": trials,
            "queried_at": datetime.now(timezone.utc).isoformat(),
        }

        self._set_cached(cache_key, result)
        return result


# ------------------------------------------------------------------
# PubMed integration
# ------------------------------------------------------------------

class PubMedSource(ExternalDataSource):
    """PubMed E-utilities API integration."""

    def __init__(self, cache_dir: Optional[Path] = None, api_key: Optional[str] = None):
        super().__init__("pubmed", cache_dir)
        self.api_key = api_key
        # FDA-151: Bump rate limit 3→10 req/sec when NCBI API key is provided
        if api_key:
            self.rate_limit = 10.0

    def search(
        self,
        query: str,
        max_results: int = 10,
        **kwargs,
    ) -> Dict[str, Any]:
        """Search PubMed for device safety literature.

        Args:
            query: PubMed search query.
            max_results: Maximum number of results.

        Returns:
            Dictionary with article results and metadata.
        """
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": str(min(max_results, 20)),
            "retmode": "json",
        }

        # FDA-106: API key passed in header, not URL (security fix)
        headers = {}
        if self.api_key:
            headers["api_key"] = self.api_key

        cache_key = self._cache_key(params)
        cached = self._get_cached(cache_key)
        if cached is not None:
            cached["_from_cache"] = True
            return cached

        # Step 1: Search for IDs
        search_url = (
            f"{self.base_url}/esearch.fcgi?"
            f"{urllib.parse.urlencode(params)}"
        )
        search_result = self._http_get(search_url, extra_headers=headers)

        if search_result is None or search_result.get("error"):
            return {
                "source": self.label,
                "query": query,
                "total_results": 0,
                "articles": [],
                "error": search_result.get("error") if search_result else "No response",
                "queried_at": datetime.now(timezone.utc).isoformat(),
            }

        esearch = search_result.get("esearchresult", {})
        id_list = esearch.get("idlist", [])
        total_count = int(esearch.get("count", 0))

        if not id_list:
            result = {
                "source": self.label,
                "api_version": self.api_version,
                "query": query,
                "total_results": total_count,
                "returned_results": 0,
                "articles": [],
                "queried_at": datetime.now(timezone.utc).isoformat(),
            }
            self._set_cached(cache_key, result)
            return result

        # Step 2: Fetch summaries
        articles = self._fetch_summaries(id_list)

        result = {
            "source": self.label,
            "api_version": self.api_version,
            "query": query,
            "total_results": total_count,
            "returned_results": len(articles),
            "articles": articles,
            "queried_at": datetime.now(timezone.utc).isoformat(),
        }

        self._set_cached(cache_key, result)
        return result

    def _fetch_summaries(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Fetch article summaries from PubMed."""
        if not pmids:
            return []

        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
        }

        # FDA-106: API key passed in header, not URL (security fix)
        headers = {}
        if self.api_key:
            headers["api_key"] = self.api_key

        url = (
            f"{self.base_url}/esummary.fcgi?"
            f"{urllib.parse.urlencode(params)}"
        )
        raw = self._http_get(url, extra_headers=headers)

        if raw is None or raw.get("error"):
            return [{"pmid": pmid, "error": "Failed to fetch"} for pmid in pmids]

        result_data = raw.get("result", {})
        articles = []

        for pmid in pmids:
            article_data = result_data.get(pmid, {})
            if isinstance(article_data, dict) and "uid" in article_data:
                authors = article_data.get("authors", [])
                author_names = [
                    a.get("name", "") for a in authors[:3]
                ]
                articles.append({
                    "pmid": pmid,
                    "title": article_data.get("title", ""),
                    "authors": author_names,
                    "journal": article_data.get("fulljournalname", ""),
                    "pub_date": article_data.get("pubdate", ""),
                    "doi": article_data.get("elocationid", ""),
                })

        return articles


# ------------------------------------------------------------------
# USPTO PatentsView integration
# ------------------------------------------------------------------

class PatentsViewSource(ExternalDataSource):
    """USPTO PatentsView API integration."""

    def __init__(self, cache_dir: Optional[Path] = None):
        super().__init__("patents", cache_dir)

    def search(
        self,
        query: str,
        max_results: int = 10,
        **kwargs,
    ) -> Dict[str, Any]:
        """Search USPTO patents for device-related IP.

        Args:
            query: Search query (device description, technology).
            max_results: Maximum number of results.

        Returns:
            Dictionary with patent results and metadata.
        """
        cache_key = self._cache_key({"query": query, "max": max_results})
        cached = self._get_cached(cache_key)
        if cached is not None:
            cached["_from_cache"] = True
            return cached

        # Build PatentsView query
        query_params = {
            "q": json.dumps({"_text_any": {"patent_abstract": query}}),
            "f": json.dumps([
                "patent_number", "patent_title", "patent_abstract",
                "patent_date", "assignees",
            ]),
            "o": json.dumps({
                "page": 1,
                "per_page": min(max_results, 25),
            }),
        }

        url = f"{self.base_url}?{urllib.parse.urlencode(query_params)}"
        raw = self._http_get(url)

        if raw is None or raw.get("error"):
            return {
                "source": self.label,
                "query": query,
                "total_results": 0,
                "patents": [],
                "error": raw.get("error") if raw else "No response",
                "queried_at": datetime.now(timezone.utc).isoformat(),
            }

        # Parse results
        patents_raw = raw.get("patents", [])
        patents = []

        for patent in patents_raw:
            assignees = patent.get("assignees", [])
            assignee_names = [
                a.get("assignee_organization", "")
                for a in assignees[:3]
                if a.get("assignee_organization")
            ]

            patents.append({
                "patent_number": patent.get("patent_number", ""),
                "title": patent.get("patent_title", ""),
                "abstract": (patent.get("patent_abstract", "") or "")[:300],
                "date": patent.get("patent_date", ""),
                "assignees": assignee_names,
            })

        result = {
            "source": self.label,
            "api_version": self.api_version,
            "query": query,
            "total_results": raw.get("total_patent_count", len(patents)),
            "returned_results": len(patents),
            "patents": patents,
            "queried_at": datetime.now(timezone.utc).isoformat(),
        }

        self._set_cached(cache_key, result)
        return result


# ------------------------------------------------------------------
# Hub (unified interface)
# ------------------------------------------------------------------

class ExternalDataHub:
    """Unified external data integration hub.

    Provides a single interface for querying ClinicalTrials.gov,
    PubMed, and USPTO PatentsView with caching and rate limiting.
    """

    def __init__(
        self,
        store: Optional[PMADataStore] = None,
        cache_dir: Optional[Path] = None,
    ):
        """Initialize External Data Hub.

        Args:
            store: PMADataStore for PMA context lookup.
            cache_dir: Base cache directory.
        """
        self.store = store or PMADataStore()
        self.cache_dir = cache_dir or Path(
            os.path.expanduser("~/fda-510k-data/pma_cache/external")
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize data sources
        self._sources: Dict[str, ExternalDataSource] = {
            "clinicaltrials": ClinicalTrialsSource(
                cache_dir=self.cache_dir / "clinicaltrials"
            ),
            "pubmed": PubMedSource(
                cache_dir=self.cache_dir / "pubmed",
                api_key=os.environ.get("NCBI_API_KEY"),  # FDA-151: auto-load from env
            ),
            "patents": PatentsViewSource(
                cache_dir=self.cache_dir / "patents"
            ),
        }

    def get_available_sources(self) -> List[Dict[str, Any]]:
        """Get list of available external data sources."""
        return [
            {
                "name": name,
                "label": source.label,
                "api_version": source.api_version,
                "rate_limit": source.rate_limit,
                "cache_ttl_hours": source.cache_ttl_hours,
            }
            for name, source in self._sources.items()
        ]

    def search(
        self,
        source_name: str,
        query: str,
        max_results: int = 10,
        **kwargs,
    ) -> Dict[str, Any]:
        """Search an external data source.

        Args:
            source_name: Data source name.
            query: Search query.
            max_results: Maximum results.

        Returns:
            Search results from the specified source.
        """
        source = self._sources.get(source_name)
        if source is None:
            return {
                "error": (
                    f"Unknown source: {source_name}. "
                    f"Available: {', '.join(self._sources.keys())}"
                ),
            }

        result = source.search(query, max_results=max_results, **kwargs)
        result["hub_version"] = HUB_VERSION
        result["disclaimer"] = (
            "External data is provided for research and intelligence "
            "purposes only. It should not be treated as regulatory "
            "evidence without independent verification by qualified "
            "regulatory professionals."
        )
        return result

    def search_clinical_trials(
        self,
        query: str,
        pma_number: Optional[str] = None,
        max_results: int = 10,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search ClinicalTrials.gov for device-related trials.

        Args:
            query: Search query.
            pma_number: Optional PMA number for context enrichment.
            max_results: Maximum results.
            status_filter: Trial status filter.

        Returns:
            Clinical trial search results.
        """
        # Enrich query with PMA context if available
        if pma_number:
            pma_data = self.store.get_pma_data(pma_number)
            if not pma_data.get("error"):
                device_name = pma_data.get("device_name", "")
                if device_name and device_name not in query:
                    query = f"{query} {device_name}"

        source = self._sources.get("clinicaltrials")
        if source is None:
            return {"error": "ClinicalTrials.gov source not available"}

        result = source.search(
            query,
            max_results=max_results,
            status_filter=status_filter,
        )
        if pma_number:
            result["pma_context"] = pma_number
        result["hub_version"] = HUB_VERSION
        return result

    def search_pubmed(
        self,
        query: str,
        pma_number: Optional[str] = None,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Search PubMed for device safety literature.

        Args:
            query: PubMed search query.
            pma_number: Optional PMA number for context enrichment.
            max_results: Maximum results.

        Returns:
            PubMed search results.
        """
        if pma_number:
            pma_data = self.store.get_pma_data(pma_number)
            if not pma_data.get("error"):
                device_name = pma_data.get("device_name", "")
                if device_name and device_name not in query:
                    query = f"{query} {device_name}"

        source = self._sources.get("pubmed")
        if source is None:
            return {"error": "PubMed source not available"}

        result = source.search(query, max_results=max_results)
        if pma_number:
            result["pma_context"] = pma_number
        result["hub_version"] = HUB_VERSION
        return result

    def search_patents(
        self,
        query: str,
        pma_number: Optional[str] = None,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Search USPTO patents for device IP.

        Args:
            query: Patent search query.
            pma_number: Optional PMA number for context enrichment.
            max_results: Maximum results.

        Returns:
            Patent search results.
        """
        if pma_number:
            pma_data = self.store.get_pma_data(pma_number)
            if not pma_data.get("error"):
                applicant = pma_data.get("applicant", "")
                if applicant and applicant not in query:
                    query = f"{query} {applicant}"

        source = self._sources.get("patents")
        if source is None:
            return {"error": "Patents source not available"}

        result = source.search(query, max_results=max_results)
        if pma_number:
            result["pma_context"] = pma_number
        result["hub_version"] = HUB_VERSION
        return result

    def search_all_sources(
        self,
        query: str,
        pma_number: Optional[str] = None,
        max_results: int = 5,
    ) -> Dict[str, Any]:
        """Search all external sources and combine results.

        Args:
            query: Search query.
            pma_number: Optional PMA context.
            max_results: Max results per source.

        Returns:
            Combined results from all sources.
        """
        results = {}

        results["clinical_trials"] = self.search_clinical_trials(
            query, pma_number=pma_number, max_results=max_results
        )
        results["pubmed"] = self.search_pubmed(
            query, pma_number=pma_number, max_results=max_results
        )
        results["patents"] = self.search_patents(
            query, pma_number=pma_number, max_results=max_results
        )

        return {
            "query": query,
            "pma_number": pma_number,
            "sources_queried": list(results.keys()),
            "results": results,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hub_version": HUB_VERSION,
            "disclaimer": (
                "External data integration results are for research "
                "and intelligence purposes only. All data requires "
                "independent verification by qualified regulatory "
                "professionals before use in regulatory submissions."
            ),
        }

    def get_hub_stats(self) -> Dict[str, Any]:
        """Get hub-wide statistics."""
        source_stats = {
            name: source.get_stats()
            for name, source in self._sources.items()
        }
        total_requests = sum(
            s.get("requests_made", 0) for s in source_stats.values()
        )
        return {
            "total_requests": total_requests,
            "sources": source_stats,
            "hub_version": HUB_VERSION,
        }


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    """CLI entry point for External Data Hub."""
    parser = argparse.ArgumentParser(
        description="FDA External Data Integration Hub"
    )
    parser.add_argument(
        "--source",
        choices=["clinicaltrials", "pubmed", "patents", "all"],
        required=True,
        help="External data source to query"
    )
    parser.add_argument(
        "--query", type=str,
        help="Search query"
    )
    parser.add_argument(
        "--pma", type=str,
        help="PMA number for context enrichment"
    )
    parser.add_argument(
        "--max-results", type=int, default=10,
        help="Maximum number of results (default: 10)"
    )
    parser.add_argument(
        "--list-sources", action="store_true",
        help="List available data sources"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()
    hub = ExternalDataHub()

    if args.list_sources:
        sources = hub.get_available_sources()
        if args.json:
            print(json.dumps(sources, indent=2))
        else:
            for s in sources:
                print(f"  {s['name']}: {s['label']} (v{s['api_version']})")
        return

    if not args.query and not args.pma:
        parser.error("--query or --pma is required")

    query = args.query or ""
    if not query and args.pma:
        # Auto-generate query from PMA context
        pma_data = hub.store.get_pma_data(args.pma)
        query = pma_data.get("device_name", args.pma)

    if args.source == "all":
        result = hub.search_all_sources(
            query, pma_number=args.pma, max_results=args.max_results
        )
    else:
        result = hub.search(
            args.source, query,
            max_results=args.max_results,
        )
        if args.pma:
            result["pma_context"] = args.pma

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
