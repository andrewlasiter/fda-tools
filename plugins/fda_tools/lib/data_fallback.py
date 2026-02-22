"""
FDA-222  [FDA-222] Three-Tier Fallback: Supabase → Local PostgreSQL → JSON Cache
==================================================================================
Provides a resilient data access layer that cascades through three tiers when
higher-priority tiers are unavailable.

Tier priority
-------------
1. **Supabase** (cloud) — primary; pgvector cosine search, RLS, multi-tenant.
2. **Local PostgreSQL** — on-premise / desktop fallback; same schema via psycopg2.
3. **JSON cache** — air-gapped / offline fallback; flat files on disk, no SQL.

A query is attempted at Tier 1 first.  If it raises any exception (connection
error, timeout, unavailable), the fallback advances to Tier 2, and then Tier 3.
The result always records *which tier answered* so callers can log or alert.

Design
------
``DataTier``           — Enum of the three tiers.
``FallbackResult``     — Immutable result value: data + tier + latency + errors.
``FallbackConfig``     — Per-instance tuning (timeouts, cache paths, retry count).
``JsonCacheStore``     — Simple dict-keyed JSON file cache (no SQL required).
``ThreeTierFallback``  — Main facade; wires Supabase + local PG + JSON cache.

Usage
-----
    from fda_tools.lib.data_fallback import ThreeTierFallback, FallbackConfig
    from fda_tools.lib.supabase_client import get_client

    fallback = ThreeTierFallback(
        supabase_client = get_client(),
        json_cache_dir  = "/var/fda-tools/cache",
    )
    result = fallback.query("guidance_embeddings", filters={"doc_id": "ucm123456"})
    print(result.tier, len(result.data))

Vector search
-------------
    result = fallback.vector_search(
        table        = "guidance_embeddings",
        query_vector = embedder.embed(["risk management"])[0],
        k            = 10,
        threshold    = 0.75,
    )

Health check
------------
    statuses = fallback.health_check()
    # {DataTier.SUPABASE: True, DataTier.LOCAL_PG: False, DataTier.JSON_CACHE: True}
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Optional psycopg2 import ──────────────────────────────────────────────────

try:
    import psycopg2         # type: ignore[import]
    import psycopg2.extras  # type: ignore[import]
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None  # type: ignore[assignment]
    _PSYCOPG2_AVAILABLE = False


# ── Enums and value objects ───────────────────────────────────────────────────

class DataTier(str, Enum):
    """The three data source tiers, in priority order."""
    SUPABASE   = "supabase"
    LOCAL_PG   = "local_pg"
    JSON_CACHE = "json_cache"


@dataclass(frozen=True)
class FallbackResult:
    """
    Immutable result of a fallback query.

    Attributes:
        tier:             Which tier ultimately answered the query.
        data:             List of row dicts returned by the query.
        latency_ms:       Time taken by the successful tier (milliseconds).
        attempted_tiers:  Tiers attempted before success (including the successful one).
        error_by_tier:    Error message for each failed tier, keyed by tier name.
        source_key:       The query key / table name used.
    """
    tier:             DataTier
    data:             List[Dict[str, Any]]
    latency_ms:       float
    attempted_tiers:  List[DataTier]
    error_by_tier:    Dict[str, str]
    source_key:       str = ""

    @property
    def degraded(self) -> bool:
        """True if a fallback tier was used (not Supabase)."""
        return self.tier != DataTier.SUPABASE

    @property
    def fully_degraded(self) -> bool:
        """True if the JSON cache was the answering tier."""
        return self.tier == DataTier.JSON_CACHE

    def as_dict(self) -> Dict[str, Any]:
        return {
            "tier":            self.tier.value,
            "row_count":       len(self.data),
            "latency_ms":      round(self.latency_ms, 2),
            "degraded":        self.degraded,
            "attempted_tiers": [t.value for t in self.attempted_tiers],
            "errors":          self.error_by_tier,
        }


@dataclass
class FallbackConfig:
    """
    Configuration for ``ThreeTierFallback``.

    Attributes:
        supabase_timeout_s:  Seconds before Supabase query is considered failed.
        local_pg_dsn:        psycopg2 DSN for local PostgreSQL (e.g. ``postgresql://...``).
        json_cache_dir:      Directory for JSON cache files.  ``None`` disables JSON tier.
        max_retries:         Per-tier retry count before failing over.
        log_degradation:     If True, emit WARNING when a fallback tier is used.
    """
    supabase_timeout_s: float       = 5.0
    local_pg_dsn:       Optional[str] = None
    json_cache_dir:     Optional[str] = None
    max_retries:        int           = 1
    log_degradation:    bool          = True


# ── JSON cache store ──────────────────────────────────────────────────────────

class JsonCacheStore:
    """
    Simple file-backed JSON cache keyed by ``{table}/{filter_hash}``.

    Each cache entry is a ``{table}__{key}.json`` file holding a list of row
    dicts.  This provides an offline fallback when neither Supabase nor local
    PostgreSQL is reachable.

    Args:
        cache_dir: Root directory for cache files.  Created if absent.
    """

    def __init__(self, cache_dir: str) -> None:
        self._root = Path(cache_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, table: str, key: str) -> Path:
        safe_key = key.replace("/", "_").replace(":", "_")[:80]
        return self._root / f"{table}__{safe_key}.json"

    def get(self, table: str, key: str) -> Optional[List[Dict[str, Any]]]:
        """Return cached rows for *table*/*key*, or ``None`` if not found."""
        p = self._path(table, key)
        if not p.exists():
            return None
        try:
            with p.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("JsonCacheStore.get: %s", exc)
            return None

    def put(self, table: str, key: str, rows: List[Dict[str, Any]]) -> None:
        """Persist *rows* for *table*/*key*."""
        p = self._path(table, key)
        try:
            with p.open("w", encoding="utf-8") as fh:
                json.dump(rows, fh)
        except OSError as exc:
            logger.warning("JsonCacheStore.put: %s", exc)

    def delete(self, table: str, key: str) -> bool:
        """Remove the cache entry; return True if it existed."""
        p = self._path(table, key)
        if p.exists():
            p.unlink()
            return True
        return False

    def list_keys(self, table: str) -> List[str]:
        """Return all cached keys for *table*."""
        prefix = f"{table}__"
        return [
            f.name[len(prefix):-5]  # strip prefix and .json suffix
            for f in self._root.iterdir()
            if f.name.startswith(prefix) and f.name.endswith(".json")
        ]

    def clear(self, table: Optional[str] = None) -> int:
        """Remove all cache files for *table* (or all tables if ``None``).  Returns count."""
        count = 0
        prefix = f"{table}__" if table else None
        for f in list(self._root.iterdir()):
            if f.suffix == ".json" and (prefix is None or f.name.startswith(prefix)):
                f.unlink()
                count += 1
        return count


# ── Three-tier fallback ───────────────────────────────────────────────────────

class ThreeTierFallback:
    """
    Data access facade with three-tier resilience.

    Falls back through: **Supabase → Local PostgreSQL → JSON Cache**

    Args:
        supabase_client: A :class:`~fda_tools.lib.supabase_client.SupabaseClient`
                         instance (or any object with ``.table()`` and
                         ``.vector_search()`` methods).
        local_pg_dsn:    psycopg2 connection string for local PostgreSQL.
                         ``None`` disables Tier 2.
        json_cache_dir:  Path to the JSON cache directory.
                         ``None`` disables Tier 3.
        config:          Optional :class:`FallbackConfig` for tuning.
    """

    def __init__(
        self,
        supabase_client: Any,
        local_pg_dsn:    Optional[str] = None,
        json_cache_dir:  Optional[str] = None,
        config:          Optional[FallbackConfig] = None,
    ) -> None:
        self._supabase    = supabase_client
        self._pg_dsn      = local_pg_dsn
        self._config      = config or FallbackConfig(
            local_pg_dsn   = local_pg_dsn,
            json_cache_dir = json_cache_dir,
        )
        self._cache: Optional[JsonCacheStore] = (
            JsonCacheStore(json_cache_dir) if json_cache_dir else None
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def query(
        self,
        table:   str,
        filters: Optional[Dict[str, Any]] = None,
        limit:   int = 100,
    ) -> FallbackResult:
        """
        Execute a filtered table query across all tiers.

        Args:
            table:   Table name.
            filters: Column→value equality filters (applied as ``eq`` in Supabase,
                     ``WHERE col = val`` in local PG, key filter in JSON cache).
            limit:   Maximum rows to return.

        Returns:
            A :class:`FallbackResult` from the first available tier.
        """
        filters = filters or {}
        cache_key = self._cache_key("query", table, filters, limit)
        return self._cascade(
            supabase_fn  = lambda: self._supabase_query(table, filters, limit),
            local_pg_fn  = lambda: self._pg_query(table, filters, limit),
            json_cache_fn= lambda: self._json_query(table, cache_key),
            source_key   = cache_key,
            write_through= True,
            table        = table,
        )

    def vector_search(
        self,
        table:        str,
        query_vector: List[float],
        k:            int   = 10,
        threshold:    float = 0.75,
    ) -> FallbackResult:
        """
        Cosine similarity vector search with tier fallback.

        Tier 1 (Supabase): Uses pgvector ``match_<table>`` RPC.
        Tier 2 (Local PG): Uses local pgvector ``match_<table>`` RPC.
        Tier 3 (JSON cache): Returns cached results for the same vector hash.

        Args:
            table:        Target embeddings table.
            query_vector: Query embedding vector.
            k:            Maximum results.
            threshold:    Minimum cosine similarity.

        Returns:
            A :class:`FallbackResult` from the first available tier.
        """
        vec_hash = hash(tuple(query_vector[:8]))  # short hash for cache key
        cache_key = f"vsearch__{table}__{k}__{vec_hash}"
        return self._cascade(
            supabase_fn  = lambda: self._supabase_vector_search(table, query_vector, k, threshold),
            local_pg_fn  = lambda: self._pg_vector_search(table, query_vector, k, threshold),
            json_cache_fn= lambda: self._json_query(table, cache_key),
            source_key   = cache_key,
            write_through= True,
            table        = table,
        )

    def health_check(self) -> Dict[DataTier, bool]:
        """
        Ping each tier and return availability status.

        Returns:
            Dict mapping each :class:`DataTier` to True/False.
        """
        statuses: Dict[DataTier, bool] = {
            DataTier.SUPABASE:   False,
            DataTier.LOCAL_PG:   False,
            DataTier.JSON_CACHE: False,
        }
        # Tier 1
        try:
            self._supabase.health_check()
            statuses[DataTier.SUPABASE] = True
        except Exception:
            pass
        # Tier 2
        if self._pg_dsn and _PSYCOPG2_AVAILABLE:
            assert psycopg2 is not None
            try:
                conn = psycopg2.connect(self._pg_dsn, connect_timeout=2)
                conn.close()
                statuses[DataTier.LOCAL_PG] = True
            except Exception:
                pass
        # Tier 3
        if self._cache is not None:
            statuses[DataTier.JSON_CACHE] = True  # always available if dir is writable
        return statuses

    def write_to_cache(
        self,
        table:  str,
        key:    str,
        rows:   List[Dict[str, Any]],
    ) -> bool:
        """
        Manually populate the JSON cache (e.g. from a pre-flight sync).

        Returns:
            True if the cache tier is configured, False otherwise.
        """
        if self._cache is None:
            return False
        self._cache.put(table, key, rows)
        return True

    # ── Cascade engine ────────────────────────────────────────────────────────

    def _cascade(
        self,
        supabase_fn:   Any,
        local_pg_fn:   Any,
        json_cache_fn: Any,
        source_key:    str,
        write_through: bool,
        table:         str,
    ) -> FallbackResult:
        attempts: List[DataTier] = []
        errors: Dict[str, str]   = {}

        tier_fns = [
            (DataTier.SUPABASE,   supabase_fn),
            (DataTier.LOCAL_PG,   local_pg_fn   if self._pg_dsn else None),
            (DataTier.JSON_CACHE, json_cache_fn if self._cache  else None),
        ]

        for tier, fn in tier_fns:
            if fn is None:
                continue
            attempts.append(tier)
            t0 = time.monotonic()
            try:
                rows = fn()
                latency = (time.monotonic() - t0) * 1000
                if rows is not None:
                    if write_through and tier != DataTier.SUPABASE and self._cache:
                        self._cache.put(table, source_key, rows)
                    if tier != DataTier.SUPABASE and self._config.log_degradation:
                        logger.warning(
                            "ThreeTierFallback degraded to %s for key %r",
                            tier.value, source_key,
                        )
                    return FallbackResult(
                        tier            = tier,
                        data            = rows,
                        latency_ms      = latency,
                        attempted_tiers = list(attempts),
                        error_by_tier   = dict(errors),
                        source_key      = source_key,
                    )
                errors[tier.value] = "returned None"
            except Exception as exc:
                errors[tier.value] = str(exc)
                logger.debug("ThreeTierFallback tier %s failed: %s", tier.value, exc)

        # All tiers exhausted — return empty result
        return FallbackResult(
            tier            = DataTier.JSON_CACHE,
            data            = [],
            latency_ms      = 0.0,
            attempted_tiers = list(attempts),
            error_by_tier   = dict(errors),
            source_key      = source_key,
        )

    # ── Tier implementations ──────────────────────────────────────────────────

    def _supabase_query(
        self,
        table:   str,
        filters: Dict[str, Any],
        limit:   int,
    ) -> List[Dict[str, Any]]:
        q = self._supabase.table(table).select("*").limit(limit)
        for col, val in filters.items():
            q = q.eq(col, val)
        response = q.execute()
        return list(response.data) if hasattr(response, "data") else []

    def _supabase_vector_search(
        self,
        table:        str,
        query_vector: List[float],
        k:            int,
        threshold:    float,
    ) -> List[Dict[str, Any]]:
        response = self._supabase.vector_search(
            table            = table,
            embedding_column = "embedding",
            query_vector     = query_vector,
            match_threshold  = threshold,
            match_count      = k,
        ).execute()
        return list(response.data) if hasattr(response, "data") else []

    def _pg_query(
        self,
        table:   str,
        filters: Dict[str, Any],
        limit:   int,
    ) -> Optional[List[Dict[str, Any]]]:
        if not _PSYCOPG2_AVAILABLE or not self._pg_dsn:
            return None
        _pg = psycopg2
        assert _pg is not None
        try:
            conn   = _pg.connect(self._pg_dsn)
            cursor = conn.cursor(cursor_factory=_pg.extras.RealDictCursor)
            where  = " AND ".join(f"{col} = %s" for col in filters) if filters else "TRUE"
            params = list(filters.values())
            cursor.execute(
                f"SELECT * FROM {table} WHERE {where} LIMIT %s",  # noqa: S608
                params + [limit],
            )
            rows = [dict(r) for r in cursor.fetchall()]
            cursor.close()
            conn.close()
            return rows
        except Exception:
            raise

    def _pg_vector_search(
        self,
        table:        str,
        query_vector: List[float],
        k:            int,
        threshold:    float,
    ) -> Optional[List[Dict[str, Any]]]:
        if not _PSYCOPG2_AVAILABLE or not self._pg_dsn:
            return None
        _pg = psycopg2
        assert _pg is not None
        try:
            conn   = _pg.connect(self._pg_dsn)
            cursor = conn.cursor(cursor_factory=_pg.extras.RealDictCursor)
            vec_str = f"[{','.join(str(v) for v in query_vector)}]"
            cursor.execute(
                f"SELECT * FROM match_{table}(%s::vector, %s, %s)",  # noqa: S608
                (vec_str, threshold, k),
            )
            rows = [dict(r) for r in cursor.fetchall()]
            cursor.close()
            conn.close()
            return rows
        except Exception:
            raise

    def _json_query(
        self,
        table: str,
        key:   str,
    ) -> Optional[List[Dict[str, Any]]]:
        if self._cache is None:
            return None
        return self._cache.get(table, key)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(op: str, table: str, filters: Dict[str, Any], limit: int) -> str:
        filter_str = "_".join(f"{k}={v}" for k, v in sorted(filters.items()))
        return f"{op}__{table}__{filter_str}__{limit}"
