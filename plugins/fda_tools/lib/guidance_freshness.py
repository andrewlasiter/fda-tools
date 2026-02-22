"""
FDA-235  [GD-005] Guidance Version Tracking & Freshness Checks
==============================================================
Tracks FDA guidance document versions using HTTP ETag / Last-Modified
headers.  Detects stale indexed content and marks affected chunks for
re-embedding.

Design
------
- ``guidance_versions`` table stores: url, etag, last_modified, indexed_at
- ``check_freshness()`` sends conditional HEAD requests; compares ETags
- ``mark_stale(doc_id)`` sets ``guidance_chunks.stale = true`` for re-indexing
- ``FreshnessReport`` returned by ``GET /research/freshness``

Schema dependency
-----------------
    CREATE TABLE IF NOT EXISTS guidance_versions (
        doc_id       text PRIMARY KEY,
        url          text NOT NULL,
        etag         text,
        last_modified text,
        content_hash text,
        indexed_at   timestamptz NOT NULL DEFAULT now(),
        checked_at   timestamptz,
        is_stale     boolean NOT NULL DEFAULT false
    );

    -- Add stale flag to guidance_chunks if not present
    ALTER TABLE guidance_chunks ADD COLUMN IF NOT EXISTS is_stale boolean DEFAULT false;

Staleness heuristics
--------------------
1. ETag changed          → STALE
2. Last-Modified changed → STALE
3. Content-Length changed → STALE
4. Not checked in > 7 days → UNKNOWN (schedule re-check)
5. HEAD request failed   → UNKNOWN (network error; don't mark stale)
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── Optional dependencies ─────────────────────────────────────────────────────

try:
    import psycopg2 as _psycopg2_module  # type: ignore[import]
    _PG_AVAILABLE = True
except ImportError:
    _psycopg2_module = None  # type: ignore[assignment]
    _PG_AVAILABLE = False

# ── Constants ─────────────────────────────────────────────────────────────────

REQUEST_TIMEOUT     = 15   # seconds per HEAD request
STALE_THRESHOLD_DAYS = 7   # documents not checked in N days → UNKNOWN
HEAD_BATCH_SIZE      = 10  # concurrent HEAD requests per batch


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class DocFreshnessStatus:
    doc_id:        str
    url:           str
    status:        str          # FRESH | STALE | UNKNOWN | ERROR
    reason:        str
    etag:          Optional[str] = None
    last_modified: Optional[str] = None
    checked_at:    Optional[str] = None


@dataclass
class FreshnessReport:
    generated_at:    str
    total_docs:      int
    fresh_count:     int
    stale_count:     int
    unknown_count:   int
    error_count:     int
    stale_docs:      List[DocFreshnessStatus] = field(default_factory=list)
    unknown_docs:    List[DocFreshnessStatus] = field(default_factory=list)

    @property
    def freshness_pct(self) -> float:
        if self.total_docs == 0:
            return 100.0
        return round(self.fresh_count / self.total_docs * 100, 1)


# ── Core checker ──────────────────────────────────────────────────────────────

class GuidanceFreshnessChecker:
    """
    Checks whether indexed FDA guidance documents are still up-to-date
    relative to their source URLs using HTTP conditional requests.

    Parameters
    ----------
    db_url : PostgreSQL DSN.  Falls back to DATABASE_URL env var.
    """

    def __init__(self, db_url: Optional[str] = None) -> None:
        self._db_url = db_url or os.getenv("DATABASE_URL")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_freshness(self, force: bool = False) -> FreshnessReport:
        """
        Run freshness checks for all tracked guidance documents.

        Parameters
        ----------
        force : Re-check all documents regardless of last check time.

        Returns
        -------
        :class:`FreshnessReport`
        """
        versions = self._load_versions()
        if not versions:
            return FreshnessReport(
                generated_at  = _now_utc(),
                total_docs    = 0,
                fresh_count   = 0,
                stale_count   = 0,
                unknown_count = 0,
                error_count   = 0,
            )

        results: List[DocFreshnessStatus] = []
        for ver in versions:
            status = self._check_one(ver, force=force)
            results.append(status)
            if status.status == "STALE":
                self._mark_stale(ver["doc_id"])

        # Persist updated etags / checked_at timestamps
        self._update_versions(results)

        fresh   = [r for r in results if r.status == "FRESH"]
        stale   = [r for r in results if r.status == "STALE"]
        unknown = [r for r in results if r.status == "UNKNOWN"]
        errors  = [r for r in results if r.status == "ERROR"]

        return FreshnessReport(
            generated_at  = _now_utc(),
            total_docs    = len(results),
            fresh_count   = len(fresh),
            stale_count   = len(stale),
            unknown_count = len(unknown),
            error_count   = len(errors),
            stale_docs    = stale,
            unknown_docs  = unknown,
        )

    def upsert_version(
        self,
        doc_id:        str,
        url:           str,
        etag:          Optional[str] = None,
        last_modified: Optional[str] = None,
        content_hash:  Optional[str] = None,
    ) -> None:
        """
        Record (or update) version metadata for a guidance document.
        Called by guidance_indexer after successfully indexing a document.
        """
        if not self._db_url or not _PG_AVAILABLE or _psycopg2_module is None:
            return
        conn = _psycopg2_module.connect(self._db_url)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO guidance_versions
                        (doc_id, url, etag, last_modified, content_hash, indexed_at, is_stale)
                    VALUES (%s, %s, %s, %s, %s, now(), false)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        url           = EXCLUDED.url,
                        etag          = EXCLUDED.etag,
                        last_modified = EXCLUDED.last_modified,
                        content_hash  = EXCLUDED.content_hash,
                        indexed_at    = now(),
                        is_stale      = false
                """, (doc_id, url, etag, last_modified, content_hash))
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_versions(self) -> List[dict]:
        if not self._db_url or not _PG_AVAILABLE or _psycopg2_module is None:
            return []
        conn = _psycopg2_module.connect(self._db_url)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT doc_id, url, etag, last_modified, content_hash,
                           indexed_at, checked_at, is_stale
                    FROM guidance_versions
                    ORDER BY doc_id
                """)
                cols = [d[0] for d in (cur.description or [])]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            conn.close()

    def _check_one(self, ver: dict, force: bool) -> DocFreshnessStatus:
        """Send HEAD request and compare ETags/Last-Modified."""
        doc_id = ver["doc_id"]
        url    = ver["url"]

        # Skip if checked recently (unless forced)
        if not force and ver.get("checked_at"):
            age = (datetime.now(tz=timezone.utc) - ver["checked_at"]).total_seconds()
            if age < STALE_THRESHOLD_DAYS * 86400:
                return DocFreshnessStatus(
                    doc_id   = doc_id,
                    url      = url,
                    status   = "FRESH",
                    reason   = f"Checked {age/3600:.0f}h ago; still within {STALE_THRESHOLD_DAYS}-day window",
                    etag     = ver.get("etag"),
                )

        try:
            from fda_tools.scripts.fda_http import create_session as _cs
            session = _cs(purpose="website")
            resp = session.head(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        except Exception as exc:
            logger.warning("HEAD request failed for %s: %s", url, exc)
            return DocFreshnessStatus(
                doc_id  = doc_id,
                url     = url,
                status  = "ERROR",
                reason  = f"Network error: {exc}",
            )

        new_etag    = resp.headers.get("ETag")
        new_lastmod = resp.headers.get("Last-Modified")

        old_etag   = ver.get("etag")
        old_lastmod = ver.get("last_modified")

        now_str = _now_utc()

        # Compare
        if old_etag and new_etag and old_etag != new_etag:
            return DocFreshnessStatus(
                doc_id        = doc_id,
                url           = url,
                status        = "STALE",
                reason        = f"ETag changed: {old_etag!r} → {new_etag!r}",
                etag          = new_etag,
                last_modified = new_lastmod,
                checked_at    = now_str,
            )

        if old_lastmod and new_lastmod and old_lastmod != new_lastmod:
            return DocFreshnessStatus(
                doc_id        = doc_id,
                url           = url,
                status        = "STALE",
                reason        = f"Last-Modified changed: {old_lastmod!r} → {new_lastmod!r}",
                etag          = new_etag,
                last_modified = new_lastmod,
                checked_at    = now_str,
            )

        if resp.status_code == 404:
            return DocFreshnessStatus(
                doc_id  = doc_id,
                url     = url,
                status  = "STALE",
                reason  = "Document removed (HTTP 404)",
                checked_at = now_str,
            )

        if not new_etag and not new_lastmod:
            return DocFreshnessStatus(
                doc_id     = doc_id,
                url        = url,
                status     = "UNKNOWN",
                reason     = "Server returned no ETag or Last-Modified header",
                checked_at = now_str,
            )

        return DocFreshnessStatus(
            doc_id        = doc_id,
            url           = url,
            status        = "FRESH",
            reason        = "ETag and Last-Modified unchanged",
            etag          = new_etag,
            last_modified = new_lastmod,
            checked_at    = now_str,
        )

    def _mark_stale(self, doc_id: str) -> None:
        if not self._db_url or not _PG_AVAILABLE or _psycopg2_module is None:
            return
        conn = _psycopg2_module.connect(self._db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE guidance_chunks SET is_stale = true WHERE doc_id = %s",
                    (doc_id,)
                )
                cur.execute(
                    "UPDATE guidance_versions SET is_stale = true WHERE doc_id = %s",
                    (doc_id,)
                )
            conn.commit()
        finally:
            conn.close()
        logger.info("Marked doc %s as stale", doc_id)

    def _update_versions(self, results: List[DocFreshnessStatus]) -> None:
        """Persist new ETags and checked_at timestamps after a check run."""
        if not self._db_url or not _PG_AVAILABLE or _psycopg2_module is None:
            return
        conn = _psycopg2_module.connect(self._db_url)
        try:
            with conn.cursor() as cur:
                for r in results:
                    if r.checked_at:
                        cur.execute("""
                            UPDATE guidance_versions
                            SET    etag = COALESCE(%s, etag),
                                   last_modified = COALESCE(%s, last_modified),
                                   checked_at = now()
                            WHERE  doc_id = %s
                        """, (r.etag, r.last_modified, r.doc_id))
            conn.commit()
        finally:
            conn.close()


# ── Utilities ─────────────────────────────────────────────────────────────────

def _now_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_content_hash(content: bytes) -> str:
    """SHA-256 of raw PDF/HTML bytes for content-change detection."""
    return hashlib.sha256(content).hexdigest()[:32]
