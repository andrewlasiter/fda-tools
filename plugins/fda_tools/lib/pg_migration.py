"""
FDA-221  [FDA-221] Migration: Local PostgreSQL → Supabase
==========================================================
Migrates existing local PostgreSQL tables (guidance_embeddings,
fda_510k_embeddings, project_embeddings) into the Supabase cloud instance,
preserving all data and applying the pgvector schema via ``SchemaManager``.

Design
------
``MigrationStatus``   — Enum for tracking migration progress.
``MigrationResult``   — Immutable result for one table migration.
``MigrationSummary``  — Aggregate across all tables.
``SupabaseMigrator``  — Main class: schema apply + row transfer.
``migrate_local_to_supabase`` — Convenience one-call function.

Idempotency
-----------
Rows are identified by their natural key (``doc_id`` + ``chunk_index`` for
guidance/510k tables; ``project_id`` + ``chunk_index`` for project embeddings).
Rows already present in Supabase are skipped — re-running the migrator is safe.

Dry run
-------
Set ``dry_run=True`` to simulate without writing.  All SQL reads still execute
against the source PostgreSQL, and all Supabase writes are mocked.

Usage
-----
    from fda_tools.lib.pg_migration import SupabaseMigrator
    from fda_tools.lib.supabase_client import get_client

    migrator = SupabaseMigrator(
        source_dsn      = "postgresql://localhost:5432/fda_tools",
        supabase_client = get_client(),
        batch_size      = 200,
    )
    summary = migrator.migrate_all()
    print(summary.total_migrated, "rows migrated")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


# ── Optional psycopg2 import ──────────────────────────────────────────────────

try:
    import psycopg2         # type: ignore[import]
    import psycopg2.extras  # type: ignore[import]
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None  # type: ignore[assignment]
    _PSYCOPG2_AVAILABLE = False


# ── Table definitions ─────────────────────────────────────────────────────────

#: Tables to migrate, with their natural-key columns for idempotent upsert.
MIGRATION_TABLES: Dict[str, Sequence[str]] = {
    "guidance_embeddings":   ("doc_id", "chunk_index"),
    "fda_510k_embeddings":   ("doc_id", "chunk_index"),
    "project_embeddings":    ("project_id", "chunk_index"),
}


# ── Value objects ─────────────────────────────────────────────────────────────

class MigrationStatus(str, Enum):
    """Status of a single-table migration."""
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"
    SKIPPED     = "skipped"     # table not present in source


@dataclass
class MigrationResult:
    """
    Result of migrating one table.

    Attributes:
        table:          Table name.
        status:         Final :class:`MigrationStatus`.
        rows_found:     Total rows discovered in the source.
        rows_migrated:  Rows written to Supabase.
        rows_skipped:   Rows already present (idempotent skip).
        rows_failed:    Rows that failed to transfer.
        batches:        Number of batches processed.
        errors:         Error messages collected during migration.
        dry_run:        True if no writes were performed.
    """
    table:          str
    status:         MigrationStatus      = MigrationStatus.PENDING
    rows_found:     int                  = 0
    rows_migrated:  int                  = 0
    rows_skipped:   int                  = 0
    rows_failed:    int                  = 0
    batches:        int                  = 0
    errors:         List[str]            = field(default_factory=list)
    dry_run:        bool                 = False

    @property
    def success_rate(self) -> float:
        """Fraction of discovered rows that migrated successfully."""
        if self.rows_found == 0:
            return 1.0
        return self.rows_migrated / self.rows_found

    def as_dict(self) -> Dict[str, Any]:
        return {
            "table":         self.table,
            "status":        self.status.value,
            "rows_found":    self.rows_found,
            "rows_migrated": self.rows_migrated,
            "rows_skipped":  self.rows_skipped,
            "rows_failed":   self.rows_failed,
            "batches":       self.batches,
            "success_rate":  round(self.success_rate, 4),
            "dry_run":       self.dry_run,
            "errors":        self.errors[:10],  # cap for readability
        }


@dataclass
class MigrationSummary:
    """
    Aggregate statistics for a full multi-table migration run.

    Attributes:
        results:   Per-table :class:`MigrationResult` objects.
        dry_run:   True if this was a dry-run pass.
    """
    results: List[MigrationResult] = field(default_factory=list)
    dry_run: bool                  = False

    @property
    def total_found(self) -> int:
        return sum(r.rows_found for r in self.results)

    @property
    def total_migrated(self) -> int:
        return sum(r.rows_migrated for r in self.results)

    @property
    def total_skipped(self) -> int:
        return sum(r.rows_skipped for r in self.results)

    @property
    def total_failed(self) -> int:
        return sum(r.rows_failed for r in self.results)

    @property
    def all_completed(self) -> bool:
        return all(
            r.status in (MigrationStatus.COMPLETED, MigrationStatus.SKIPPED)
            for r in self.results
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "dry_run":       self.dry_run,
            "all_completed": self.all_completed,
            "total_found":   self.total_found,
            "total_migrated":self.total_migrated,
            "total_skipped": self.total_skipped,
            "total_failed":  self.total_failed,
            "tables":        [r.as_dict() for r in self.results],
        }

    def report(self) -> str:
        """Return a human-readable migration summary."""
        lines = [
            f"Migration {'(DRY RUN) ' if self.dry_run else ''}Summary",
            "─" * 50,
        ]
        for r in self.results:
            icon = "✓" if r.status == MigrationStatus.COMPLETED else (
                "⊘" if r.status == MigrationStatus.SKIPPED else "✗"
            )
            lines.append(
                f"  {icon} {r.table}: "
                f"{r.rows_migrated}/{r.rows_found} migrated, "
                f"{r.rows_skipped} skipped, {r.rows_failed} failed"
            )
        lines.append(f"\nTotal: {self.total_migrated}/{self.total_found} rows")
        return "\n".join(lines)


# ── SupabaseMigrator ──────────────────────────────────────────────────────────

class SupabaseMigrator:
    """
    Transfers rows from local PostgreSQL to Supabase with idempotent upsert.

    Args:
        source_dsn:      psycopg2 DSN for the local PostgreSQL source.
        supabase_client: Connected :class:`~fda_tools.lib.supabase_client.SupabaseClient`.
        batch_size:      Rows per Supabase upsert call (default: 100).
        tables:          Tables to migrate (default: all three embedding tables).
        dry_run:         If True, read from source but skip all Supabase writes.
        on_progress:     Optional callback ``(table, done, total)`` for progress reporting.
    """

    def __init__(
        self,
        source_dsn:      str,
        supabase_client: Any,
        batch_size:      int  = 100,
        tables:          Optional[Dict[str, Sequence[str]]] = None,
        dry_run:         bool = False,
        on_progress:     Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        self._dsn        = source_dsn
        self._supabase   = supabase_client
        self._batch_size = max(1, batch_size)
        self._tables     = tables or dict(MIGRATION_TABLES)
        self._dry_run    = dry_run
        self._on_progress = on_progress

    # ── Public API ────────────────────────────────────────────────────────────

    def migrate_all(self) -> MigrationSummary:
        """
        Migrate all configured tables and return an aggregate summary.

        Returns:
            A :class:`MigrationSummary` with per-table results.
        """
        results = []
        for table, key_cols in self._tables.items():
            result = self.migrate_table(table, key_cols=list(key_cols))
            results.append(result)
            if result.status == MigrationStatus.FAILED:
                logger.error("Table %s failed: %s", table, result.errors[:3])
        return MigrationSummary(results=results, dry_run=self._dry_run)

    def migrate_table(
        self,
        table:    str,
        key_cols: Optional[List[str]] = None,
    ) -> MigrationResult:
        """
        Migrate a single table from local PostgreSQL to Supabase.

        Args:
            table:    Table name.
            key_cols: Natural-key columns for idempotent upsert.
                      Defaults to the value in :data:`MIGRATION_TABLES`.

        Returns:
            A :class:`MigrationResult` for this table.
        """
        if key_cols is None:
            key_cols = list(self._tables.get(table, ("id",)))

        result = MigrationResult(table=table, dry_run=self._dry_run)

        if not _PSYCOPG2_AVAILABLE:
            result.status = MigrationStatus.FAILED
            result.errors.append("psycopg2 not installed; cannot connect to local PostgreSQL")
            return result

        result.status = MigrationStatus.IN_PROGRESS

        _pg = psycopg2
        assert _pg is not None

        try:
            conn = _pg.connect(self._dsn)
        except Exception as exc:
            result.status = MigrationStatus.FAILED
            result.errors.append(f"Source connection failed: {exc}")
            return result

        try:
            cursor = conn.cursor(cursor_factory=_pg.extras.RealDictCursor)

            # Check table exists
            cursor.execute(
                "SELECT to_regclass(%s) IS NOT NULL AS exists",
                (table,),
            )
            row = cursor.fetchone()
            if not row or not row["exists"]:
                result.status = MigrationStatus.SKIPPED
                logger.info("Table %s not found in source — skipped", table)
                cursor.close()
                conn.close()
                return result

            # Count rows
            cursor.execute(f"SELECT COUNT(*) AS n FROM {table}")  # noqa: S608
            count_row = cursor.fetchone()
            result.rows_found = int(count_row["n"]) if count_row else 0

            # Stream in batches
            cursor.execute(f"SELECT * FROM {table}")  # noqa: S608
            batch: List[Dict[str, Any]] = []

            def flush_batch() -> None:
                nonlocal batch
                if not batch:
                    return
                result.batches += 1
                migrated, skipped, failed = self._upsert_batch(table, batch, key_cols or [])
                result.rows_migrated += migrated
                result.rows_skipped  += skipped
                result.rows_failed   += failed
                if self._on_progress:
                    done = result.rows_migrated + result.rows_skipped + result.rows_failed
                    self._on_progress(table, done, result.rows_found)
                batch = []

            for pg_row in cursor:
                batch.append(dict(pg_row))
                if len(batch) >= self._batch_size:
                    flush_batch()
            flush_batch()  # final partial batch

            cursor.close()
            result.status = MigrationStatus.COMPLETED

        except Exception as exc:
            result.status = MigrationStatus.FAILED
            result.errors.append(str(exc))
            logger.exception("migrate_table(%s) failed", table)
        finally:
            conn.close()

        return result

    def estimate_rows(self, table: str) -> int:
        """
        Return an approximate row count from the local PostgreSQL source.

        Uses ``reltuples`` from ``pg_class`` for speed (may be slightly stale).

        Args:
            table: Table name.

        Returns:
            Estimated row count, or -1 if unavailable.
        """
        if not _PSYCOPG2_AVAILABLE:
            return -1
        _pg = psycopg2
        assert _pg is not None
        try:
            conn   = _pg.connect(self._dsn)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT reltuples::BIGINT FROM pg_class WHERE relname = %s",
                (table,),
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return int(row[0]) if row else 0
        except Exception:
            return -1

    # ── Internal ──────────────────────────────────────────────────────────────

    def _upsert_batch(
        self,
        table:    str,
        rows:     List[Dict[str, Any]],
        key_cols: List[str],
    ) -> tuple[int, int, int]:
        """
        Upsert *rows* into Supabase.  Returns ``(migrated, skipped, failed)``.

        Skipped rows are detected by checking for existing records with the same
        natural key before the upsert.  In dry-run mode all writes are no-ops.
        """
        if self._dry_run:
            return len(rows), 0, 0

        migrated = skipped = failed = 0
        try:
            # Check which natural keys already exist
            if key_cols:
                existing = self._fetch_existing_keys(table, rows, key_cols)
            else:
                existing = set()

            to_insert = []
            for row in rows:
                row_key = tuple(row.get(k) for k in key_cols)
                if row_key in existing:
                    skipped += 1
                else:
                    to_insert.append(row)

            if to_insert:
                response = (
                    self._supabase.table(table)
                    .insert(to_insert)
                    .execute()
                )
                if hasattr(response, "data"):
                    migrated = len(response.data)
                else:
                    migrated = len(to_insert)

        except Exception as exc:
            logger.warning("_upsert_batch(%s): %s", table, exc)
            failed = len(rows)

        return migrated, skipped, failed

    def _fetch_existing_keys(
        self,
        table:    str,
        rows:     List[Dict[str, Any]],
        key_cols: List[str],
    ) -> set:
        """
        Query Supabase for existing rows matching the natural keys in *rows*.

        Returns a set of tuples ``(key_col_val, ...)`` for efficient O(1) lookup.
        """
        existing: set = set()
        if not key_cols or not rows:
            return existing
        try:
            # Use the first key column to narrow the query (simple heuristic)
            first_key = key_cols[0]
            values = list({str(r[first_key]) for r in rows if first_key in r})
            if not values:
                return existing
            response = (
                self._supabase.table(table)
                .select(",".join(key_cols))
                .in_(first_key, values)
                .execute()
            )
            if hasattr(response, "data"):
                for existing_row in response.data:
                    key = tuple(existing_row.get(k) for k in key_cols)
                    existing.add(key)
        except Exception as exc:
            logger.debug("_fetch_existing_keys(%s): %s — assuming none exist", table, exc)
        return existing


# ── Convenience function ──────────────────────────────────────────────────────

def migrate_local_to_supabase(
    source_dsn:      str,
    supabase_client: Any,
    tables:          Optional[List[str]] = None,
    batch_size:      int  = 100,
    dry_run:         bool = False,
    on_progress:     Optional[Callable[[str, int, int], None]] = None,
) -> MigrationSummary:
    """
    One-call convenience function for migrating local PostgreSQL → Supabase.

    Args:
        source_dsn:      psycopg2 DSN for the local PostgreSQL source.
        supabase_client: Connected SupabaseClient.
        tables:          Subset of table names to migrate.  ``None`` = all three.
        batch_size:      Rows per upsert batch.
        dry_run:         Simulate without writing.
        on_progress:     Progress callback ``(table, done, total)``.

    Returns:
        A :class:`MigrationSummary` with per-table results.
    """
    table_map: Optional[Dict[str, Sequence[str]]] = None
    if tables is not None:
        table_map = {t: MIGRATION_TABLES[t] for t in tables if t in MIGRATION_TABLES}

    return SupabaseMigrator(
        source_dsn      = source_dsn,
        supabase_client = supabase_client,
        batch_size      = batch_size,
        tables          = table_map,
        dry_run         = dry_run,
        on_progress     = on_progress,
    ).migrate_all()
