# ADR-007: PostgreSQL for Offline 510(k) Device Database

**Status:** Accepted
**Date:** 2026-01-01

## Context

The tool ships with a local database of 150,000+ FDA 510(k) device records for
offline predicate search. The initial implementation scanned JSON files on disk
using Python, resulting in O(n) query time: 30-60 seconds per predicate search.
This latency made the tool impractical for interactive use — RA professionals
expect sub-second typeahead filtering.

The database is read-heavy: records are written once during the periodic FDA
data sync and read many times during predicate analysis. The data model includes
semi-structured JSONB fields (device specs, contact info, product codes) that
benefit from index-accelerated containment queries.

The database runs on the local machine; no network connectivity is required
after the initial data sync.

## Decision

PostgreSQL with JSONB indexing replaces the file-scanning approach for the
offline device database. A GIN index on the JSONB `device_data` column
reduces predicate search from 30-60s to under 200ms (50-200x improvement).
Zero-downtime updates use a blue-green table swap: new data loads into a shadow
table, then a single `ALTER TABLE RENAME` swaps it into production.

## Alternatives Considered

- **SQLite:** Embeddable, zero-server. Rejected because SQLite lacks parallel
  read support (WAL mode helps but does not fully parallelize) and has no native
  JSONB indexing — the semi-structured fields would require full-table scans or
  schema flattening.
- **Elasticsearch:** Excellent full-text and JSON search. Rejected as too heavy
  a dependency for a CLI tool running on a workstation; requires JVM, significant
  RAM, and complex setup.
- **In-memory (dict/list):** Fast queries once loaded. Rejected because loading
  150K records into RAM takes 8-12 seconds at startup and consumes ~800MB.
- **Redis:** Fast key-value and JSON support. Rejected because it is not
  persistent by default and requires careful AOF/RDB tuning; also adds an
  unfamiliar operational dependency for RA professionals.

## Consequences

- PostgreSQL must be installed and running locally; an install script is provided.
- DB connection is localhost-only; no network exposure.
- Schema migrations managed with Alembic; migration files committed to the repo.
- The file-scanning fallback is retained as a degraded mode when PG is unavailable.
