#!/usr/bin/env python3
"""
FDA-221: Local PostgreSQL → Supabase migration script.

Migrates FDA offline data, audit logs, and rate-limiter state from local
PostgreSQL to Supabase with tenant isolation and progress checkpointing.

Usage:
    python3 migrate_to_supabase.py --dry-run          # validate only
    python3 migrate_to_supabase.py --batch-size 500   # migrate in batches
    python3 migrate_to_supabase.py --resume           # resume from checkpoint
    python3 migrate_to_supabase.py --tables 510k maude # specific tables only

Required env vars:
    SUPABASE_URL, SUPABASE_SECRET_KEY   (destination)
    PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD   (source)
    MIGRATION_TENANT_ID   UUID for the tenant that owns the migrated data
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────

CHECKPOINT_PATH = Path.home() / ".mdrp" / "migration_checkpoint.json"

# Tables to migrate and their primary keys
MIGRATION_PLAN: Dict[str, Dict[str, Any]] = {
    "fda_510k":          {"pk": "k_number",      "batch": 500},
    "fda_classification": {"pk": "product_code",  "batch": 1000},
    "fda_maude_events":  {"pk": "event_key",      "batch": 500},
    "fda_recalls":       {"pk": "recall_number",  "batch": 500},
    "fda_pma":           {"pk": "pma_number",     "batch": 500},
    "fda_udi":           {"pk": "di",             "batch": 1000},
    "fda_enforcement":   {"pk": "recall_number",  "batch": 500},
}


# ── Postgres source helper ─────────────────────────────────────────────

class _SourceDB:
    """Thin wrapper around local PostgreSQL for reading rows."""

    def __init__(self) -> None:
        import psycopg2  # type: ignore[import]
        from psycopg2.extras import RealDictCursor  # type: ignore[import]
        self._psycopg2 = psycopg2
        self._cursor_factory = RealDictCursor
        self._conn = psycopg2.connect(
            host=os.environ.get("PGHOST", "localhost"),
            port=int(os.environ.get("PGPORT", "6432")),
            dbname=os.environ.get("PGDATABASE", "fda_offline"),
            user=os.environ.get("PGUSER", "fda_user"),
            password=os.environ.get("PGPASSWORD", ""),
        )
        self._conn.autocommit = True

    def count(self, table: str) -> int:
        with self._conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def table_exists(self, table: str) -> bool:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = %s AND table_schema = 'public'",
                [table],
            )
            return cur.fetchone() is not None

    def iter_rows(
        self, table: str, batch_size: int = 500, offset: int = 0
    ) -> Iterator[List[Dict[str, Any]]]:
        """Yield batches of rows as lists of dicts."""
        while True:
            with self._conn.cursor(cursor_factory=self._cursor_factory) as cur:
                cur.execute(
                    f'SELECT * FROM "{table}" ORDER BY ctid LIMIT %s OFFSET %s',
                    [batch_size, offset],
                )
                rows = [dict(r) for r in cur.fetchall()]
            if not rows:
                break
            yield rows
            offset += len(rows)
            if len(rows) < batch_size:
                break

    def close(self) -> None:
        self._conn.close()


# ── Supabase destination helper ────────────────────────────────────────

class _DestDB:
    """Thin wrapper around SupabaseClient for writing rows."""

    def __init__(self, tenant_id: str) -> None:
        from fda_tools.lib.supabase_client import SupabaseClient  # type: ignore[import]
        self._client = SupabaseClient.get_instance()
        self._tenant_id = tenant_id

    def upsert_batch(self, table: str, rows: List[Dict[str, Any]]) -> int:
        """Upsert a batch. Returns count of rows written."""
        # Inject tenant_id if the table supports it
        tenant_aware = table in (
            "fda_510k", "fda_maude_events", "fda_recalls",
            "fda_pma", "fda_udi", "fda_enforcement", "fda_classification",
        )
        if tenant_aware:
            for row in rows:
                row.setdefault("tenant_id", self._tenant_id)

        # Serialize datetime objects
        cleaned = [_serialize_row(r) for r in rows]

        resp = self._client.table(table).upsert(cleaned).execute()
        return len(resp.data) if resp.data else len(cleaned)


def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert datetime objects to ISO strings for Supabase REST."""
    out: Dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


# ── Checkpoint ─────────────────────────────────────────────────────────

def _load_checkpoint() -> Dict[str, Any]:
    if CHECKPOINT_PATH.exists():
        try:
            return json.loads(CHECKPOINT_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _save_checkpoint(state: Dict[str, Any]) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(json.dumps(state, indent=2))


def _clear_checkpoint() -> None:
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()


# ── Schema compatibility check ─────────────────────────────────────────

def _check_schema(src: _SourceDB, tables: List[str]) -> List[str]:
    """Return list of missing tables (will be skipped, not errored)."""
    missing = []
    for table in tables:
        if not src.table_exists(table):
            missing.append(table)
    return missing


# ── Main migration ─────────────────────────────────────────────────────

def run_migration(
    dry_run: bool,
    batch_size: int,
    resume: bool,
    tables: Optional[List[str]],
    tenant_id: str,
) -> int:
    """Execute migration. Returns exit code (0 = success)."""
    _setup_logging()

    # Validate required env vars
    _require_env("SUPABASE_URL")
    _require_env("SUPABASE_SECRET_KEY")
    _require_env("MIGRATION_TENANT_ID")

    plan = {k: v for k, v in MIGRATION_PLAN.items() if not tables or k in tables}

    # Connect
    logger.info("Connecting to source PostgreSQL…")
    try:
        src = _SourceDB()
    except Exception as exc:
        logger.error("Cannot connect to source PostgreSQL: %s", exc)
        return 1

    dest: Optional[_DestDB] = None
    if dry_run:
        logger.info("DRY RUN — no data will be written to Supabase")
    else:
        logger.info("Connecting to destination Supabase…")
        dest = _DestDB(tenant_id)

    # Schema check
    missing = _check_schema(src, list(plan.keys()))
    for t in missing:
        logger.warning("Table not found in source, skipping: %s", t)
    plan = {k: v for k, v in plan.items() if k not in missing}

    # Load checkpoint if resuming
    checkpoint = _load_checkpoint() if resume else {}
    if resume and checkpoint:
        logger.info("Resuming from checkpoint: %s", checkpoint.get("_summary", "unknown"))

    # Migrate each table
    total_rows = 0
    start_time = time.monotonic()

    for table, config in plan.items():
        pk = config["pk"]
        effective_batch = min(batch_size, config["batch"])
        start_offset = checkpoint.get(table, {}).get("offset", 0)

        row_count = src.count(table)
        logger.info("Migrating %-25s  rows=%-8d pk=%s", table, row_count, pk)

        if row_count == 0:
            continue

        rows_done = start_offset
        try:
            for batch in src.iter_rows(table, effective_batch, start_offset):
                if not dry_run and dest is not None:
                    written = dest.upsert_batch(table, batch)
                else:
                    written = len(batch)

                rows_done += written
                total_rows += written

                # Progress
                pct = (rows_done / row_count * 100) if row_count else 100
                logger.info(
                    "  %-25s  %5d / %5d  (%3.0f%%)", table, rows_done, row_count, pct
                )

                # Save checkpoint after each batch
                checkpoint[table] = {"offset": rows_done, "total": row_count}
                checkpoint["_summary"] = (
                    f"last_table={table} rows_done={rows_done} ts={datetime.now(timezone.utc).isoformat()}"
                )
                _save_checkpoint(checkpoint)

        except Exception as exc:
            logger.error("Error migrating %s at offset %d: %s", table, rows_done, exc)
            logger.error("Run with --resume to continue from this point.")
            src.close()
            return 1

    src.close()
    elapsed = time.monotonic() - start_time

    if not dry_run:
        _clear_checkpoint()

    logger.info(
        "%s complete: %d total rows in %.1fs",
        "Dry-run" if dry_run else "Migration",
        total_rows,
        elapsed,
    )
    return 0


# ── Helpers ────────────────────────────────────────────────────────────

def _require_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"ERROR: {name} is not set. Export it before running.", file=sys.stderr)
        sys.exit(1)
    return val


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )


# ── CLI ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate local PostgreSQL → Supabase for MDRP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate and count rows without writing to Supabase",
    )
    parser.add_argument(
        "--batch-size", type=int, default=500, metavar="N",
        help="Rows per batch (default: 500)",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--tables", nargs="+", metavar="TABLE",
        help="Migrate only these tables (default: all)",
    )
    args = parser.parse_args()

    tenant_id = os.environ.get("MIGRATION_TENANT_ID", "")
    if not tenant_id and not args.dry_run:
        print("ERROR: MIGRATION_TENANT_ID is required.", file=sys.stderr)
        sys.exit(1)

    rc = run_migration(
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        resume=args.resume,
        tables=args.tables,
        tenant_id=tenant_id,
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
