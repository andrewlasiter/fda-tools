"""
FDA-222: Three-tier database fallback router.

Provides a unified AbstractDatabase interface with automatic fallback:
  Tier 1 — Supabase (cloud, multi-tenant)
  Tier 2 — Local PostgreSQL (on-prem / desktop)
  Tier 3 — JSON files  (air-gapped / development)

Usage:
    db = DatabaseRouter.get_instance()
    db.upsert("510k", k_number="K241234", data={...})
    records = db.query("510k", filters={"product_code": "DQY"})

Config via env var:
    DATABASE_MODE=supabase   → force Tier 1
    DATABASE_MODE=postgres   → force Tier 2
    DATABASE_MODE=json       → force Tier 3
    DATABASE_MODE=auto       → try in order (default)
"""

from __future__ import annotations

import json
import logging
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Abstract interface — all tiers implement this
# ---------------------------------------------------------------------------


class AbstractDatabase(ABC):
    """Minimal interface that every database tier must implement."""

    # Subclasses set this as a class-level string attribute
    tier_name: str

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this tier can accept connections right now."""

    @abstractmethod
    def upsert(self, table: str, pk_field: str, pk_value: str, data: Dict[str, Any]) -> bool:
        """Insert or update a row. Returns True on success."""

    @abstractmethod
    def get(self, table: str, pk_field: str, pk_value: str) -> Optional[Dict[str, Any]]:
        """Fetch a single row by primary key. Returns None if not found."""

    @abstractmethod
    def query(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Return rows matching filters."""

    @abstractmethod
    def delete(self, table: str, pk_field: str, pk_value: str) -> bool:
        """Delete a row. Returns True if a row was deleted."""


# ---------------------------------------------------------------------------
# Tier 1: Supabase
# ---------------------------------------------------------------------------


class SupabaseTier(AbstractDatabase):
    """Wraps SupabaseClient for database operations."""

    tier_name = "supabase"

    def __init__(self) -> None:
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from fda_tools.lib.supabase_client import SupabaseClient  # type: ignore[import]
            self._client = SupabaseClient.get_instance()
        return self._client

    def is_available(self) -> bool:
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
        if not url or not key:
            return False
        try:
            return self._get_client().ping()
        except Exception:
            return False

    def upsert(self, table: str, pk_field: str, pk_value: str, data: Dict[str, Any]) -> bool:
        try:
            row = {pk_field: pk_value, **data}
            self._get_client().table(table).upsert(row).execute()
            return True
        except Exception as exc:
            logger.warning("Supabase upsert failed: %s", exc)
            return False

    def get(self, table: str, pk_field: str, pk_value: str) -> Optional[Dict[str, Any]]:
        try:
            resp = (
                self._get_client()
                .table(table)
                .select("*")
                .eq(pk_field, pk_value)
                .limit(1)
                .execute()
            )
            rows = resp.data
            return rows[0] if rows else None
        except Exception as exc:
            logger.warning("Supabase get failed: %s", exc)
            return None

    def query(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        try:
            q = self._get_client().table(table).select("*").limit(limit).offset(offset)
            for field, value in (filters or {}).items():
                q = q.eq(field, value)
            resp = q.execute()
            return resp.data or []
        except Exception as exc:
            logger.warning("Supabase query failed: %s", exc)
            return []

    def delete(self, table: str, pk_field: str, pk_value: str) -> bool:
        try:
            resp = (
                self._get_client()
                .table(table)
                .delete()
                .eq(pk_field, pk_value)
                .execute()
            )
            return bool(resp.data)
        except Exception as exc:
            logger.warning("Supabase delete failed: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Tier 2: Local PostgreSQL
# ---------------------------------------------------------------------------


class PostgresTier(AbstractDatabase):
    """Wraps the existing PostgreSQLDatabase for the router interface."""

    tier_name = "postgres"

    def __init__(self) -> None:
        self._db: Any = None

    def _get_db(self) -> Any:
        if self._db is None:
            from fda_tools.lib.postgres_database import PostgreSQLDatabase  # type: ignore[import]
            self._db = PostgreSQLDatabase(
                host=os.environ.get("PGHOST", "localhost"),
                port=int(os.environ.get("PGPORT", "6432")),
                database=os.environ.get("PGDATABASE", "fda_offline"),
                user=os.environ.get("PGUSER", "fda_user"),
                password=os.environ.get("PGPASSWORD"),
            )
        return self._db

    def is_available(self) -> bool:
        try:
            db = self._get_db()
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    def upsert(self, table: str, pk_field: str, pk_value: str, data: Dict[str, Any]) -> bool:
        try:
            db = self._get_db()
            # Route to the correct endpoint via existing upsert_record if possible
            endpoint = _table_to_endpoint(table)
            if endpoint:
                db.upsert_record(endpoint, data)
            else:
                # Generic JSON upsert for MDRP-specific tables
                self._generic_upsert(db, table, pk_field, pk_value, data)
            return True
        except Exception as exc:
            logger.warning("Postgres upsert failed: %s", exc)
            return False

    def _generic_upsert(
        self, db: Any, table: str, pk_field: str, pk_value: str, data: Dict[str, Any]
    ) -> None:
        import json as _json
        from psycopg2 import sql as _sql  # type: ignore[import]
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    _sql.SQL(
                        "INSERT INTO {tbl} ({pk}, data, updated_at) VALUES (%s, %s, now()) "
                        "ON CONFLICT ({pk}) DO UPDATE SET data = EXCLUDED.data, updated_at = now()"
                    ).format(tbl=_sql.Identifier(table), pk=_sql.Identifier(pk_field)),
                    [pk_value, _json.dumps(data)],
                )
            conn.commit()

    def get(self, table: str, pk_field: str, pk_value: str) -> Optional[Dict[str, Any]]:
        try:
            db = self._get_db()
            endpoint = _table_to_endpoint(table)
            if endpoint:
                return db.get_record(endpoint, pk_value)
            # Generic fallback
            from psycopg2 import sql as _sql  # type: ignore[import]
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        _sql.SQL("SELECT data FROM {tbl} WHERE {pk} = %s").format(
                            tbl=_sql.Identifier(table),
                            pk=_sql.Identifier(pk_field),
                        ),
                        [pk_value],
                    )
                    row = cur.fetchone()
                    return row[0] if row else None
        except Exception as exc:
            logger.warning("Postgres get failed: %s", exc)
            return None

    def query(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        try:
            db = self._get_db()
            endpoint = _table_to_endpoint(table)
            if endpoint:
                return db.query_records(endpoint, filters or {}, limit)
            return []
        except Exception as exc:
            logger.warning("Postgres query failed: %s", exc)
            return []

    def delete(self, table: str, pk_field: str, pk_value: str) -> bool:
        try:
            db = self._get_db()
            from psycopg2 import sql as _sql  # type: ignore[import]
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        _sql.SQL("DELETE FROM {tbl} WHERE {pk} = %s").format(
                            tbl=_sql.Identifier(table),
                            pk=_sql.Identifier(pk_field),
                        ),
                        [pk_value],
                    )
                    deleted = cur.rowcount > 0
                conn.commit()
            return deleted
        except Exception as exc:
            logger.warning("Postgres delete failed: %s", exc)
            return False


def _table_to_endpoint(table: str) -> Optional[str]:
    """Map MDRP table names → existing PostgreSQLDatabase endpoint keys."""
    _MAP = {
        "fda_510k": "510k",
        "fda_classification": "classification",
        "fda_maude_events": "maude",
        "fda_recalls": "recalls",
        "fda_pma": "pma",
        "fda_udi": "udi",
        "fda_enforcement": "enforcement",
    }
    return _MAP.get(table)


# ---------------------------------------------------------------------------
# Tier 3: JSON files
# ---------------------------------------------------------------------------


class JSONTier(AbstractDatabase):
    """
    Flat-file JSON backend.

    Data layout: {data_dir}/{table}/{pk_value}.json
    """

    tier_name = "json"

    def __init__(self, data_dir: Optional[str] = None) -> None:
        default_dir = os.environ.get(
            "MDRP_JSON_DATA_DIR",
            str(Path.home() / ".mdrp" / "data"),
        )
        self._root = Path(data_dir or default_dir)

    def is_available(self) -> bool:
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False

    def _path(self, table: str, pk_value: str) -> Path:
        return self._root / table / f"{pk_value}.json"

    def upsert(self, table: str, pk_field: str, pk_value: str, data: Dict[str, Any]) -> bool:
        try:
            p = self._path(table, pk_value)
            p.parent.mkdir(parents=True, exist_ok=True)
            payload = {pk_field: pk_value, **data}
            p.write_text(json.dumps(payload, indent=2, default=str))
            return True
        except OSError as exc:
            logger.warning("JSON upsert failed: %s", exc)
            return False

    def get(self, table: str, pk_field: str, pk_value: str) -> Optional[Dict[str, Any]]:
        p = self._path(table, pk_value)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("JSON get failed: %s", exc)
            return None

    def query(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        table_dir = self._root / table
        if not table_dir.exists():
            return []
        results: List[Dict[str, Any]] = []
        for p in sorted(table_dir.glob("*.json")):
            try:
                row = json.loads(p.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if filters and not all(row.get(k) == v for k, v in filters.items()):
                continue
            results.append(row)
        return results[offset: offset + limit]

    def delete(self, table: str, pk_field: str, pk_value: str) -> bool:
        p = self._path(table, pk_value)
        if p.exists():
            try:
                p.unlink()
                return True
            except OSError:
                return False
        return False


# ---------------------------------------------------------------------------
# Router — auto-selects the best available tier
# ---------------------------------------------------------------------------


class DatabaseRouter(AbstractDatabase):
    """
    Three-tier database router with automatic fallback.

    Tier selection order: Supabase → PostgreSQL → JSON
    Force a specific tier with DATABASE_MODE env var.

    Usage:
        db = DatabaseRouter.get_instance()
        db.upsert("guidance_chunks", "id", "uuid-123", {...})
    """

    _instance: Optional["DatabaseRouter"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._tiers: List[AbstractDatabase] = [
            SupabaseTier(),
            PostgresTier(),
            JSONTier(),
        ]
        self._forced_tier: Optional[str] = None
        self._active_tier: Optional[AbstractDatabase] = None

    @classmethod
    def get_instance(cls) -> "DatabaseRouter":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instance = None

    # ------------------------------------------------------------------

    tier_name = "router"

    def active_tier_name(self) -> str:
        t = self._resolve_tier()
        return t.tier_name if t else "none"

    def _resolve_tier(self) -> Optional[AbstractDatabase]:
        """Return the active tier, respecting DATABASE_MODE override."""
        mode = os.environ.get("DATABASE_MODE", "auto").lower().strip()

        # Forced mode — skip availability check for the forced tier
        if mode in ("supabase", "postgres", "json"):
            for tier in self._tiers:
                if tier.tier_name == mode:
                    if self._active_tier is not tier:
                        logger.info("DatabaseRouter: forced mode=%s", mode)
                        self._active_tier = tier
                    return tier

        # Auto mode — try in order, cache result
        if self._active_tier and self._active_tier.is_available():
            return self._active_tier

        for tier in self._tiers:
            if tier.is_available():
                if self._active_tier is not tier:
                    logger.info(
                        "DatabaseRouter: selected tier=%s (previous=%s)",
                        tier.tier_name,
                        self._active_tier.tier_name if self._active_tier else "none",
                    )
                    self._active_tier = tier
                return tier

        logger.error("DatabaseRouter: no tier available!")
        return None

    def is_available(self) -> bool:
        return self._resolve_tier() is not None

    def _dispatch(self, method: str, *args: Any, **kwargs: Any) -> Any:
        tier = self._resolve_tier()
        if tier is None:
            raise RuntimeError(
                "No database tier is available. "
                "Set SUPABASE_URL/SUPABASE_SECRET_KEY, PGHOST/PGPASSWORD, "
                "or MDRP_JSON_DATA_DIR."
            )
        return getattr(tier, method)(*args, **kwargs)

    def upsert(self, table: str, pk_field: str, pk_value: str, data: Dict[str, Any]) -> bool:
        return self._dispatch("upsert", table, pk_field, pk_value, data)  # type: ignore[return-value]

    def get(self, table: str, pk_field: str, pk_value: str) -> Optional[Dict[str, Any]]:
        return self._dispatch("get", table, pk_field, pk_value)  # type: ignore[return-value]

    def query(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return self._dispatch("query", table, filters, limit, offset)  # type: ignore[return-value]

    def delete(self, table: str, pk_field: str, pk_value: str) -> bool:
        return self._dispatch("delete", table, pk_field, pk_value)  # type: ignore[return-value]
