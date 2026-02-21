# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for FDA Tools.
ADRs document significant technical decisions, the context in which they were
made, the alternatives considered, and the consequences of the chosen approach.

## Index

| # | Title | Status | Date |
|---|-------|--------|------|
| [001](ADR-001-python-over-typescript.md) | Python over TypeScript for main codebase | Accepted | 2025-01 |
| [002](ADR-002-local-json-storage.md) | Local JSON/SQLite storage (no remote database) | Accepted | 2025-01 |
| [003](ADR-003-multi-process-rate-limiting.md) | File-lock-based multi-process rate limiter | Accepted | 2025-04 |
| [004](ADR-004-local-only-analytics.md) | Local-only analytics (no external telemetry) | Accepted | 2025-06 |
| [005](ADR-005-stdlib-only-lib-modules.md) | stdlib-only dependencies for lib/ modules | Accepted | 2025-08 |
| [006](ADR-006-dual-assignment-orchestrator.md) | Dual-assignment model in orchestrator | Accepted | 2025-09 |
| [007](ADR-007-postgres-offline-database.md) | PostgreSQL offline database for 510(k) data | Accepted | 2026-01 |
| [008](ADR-008-defusedxml-for-xml-parsing.md) | defusedxml for all untrusted XML parsing | Accepted | 2025-03 |

## Process

### When to write an ADR

Create an ADR whenever you make a significant decision about:

- Technology or library choice affecting multiple files
- Security architecture (authentication, data storage, encryption)
- Data model or storage format changes
- Cross-cutting architectural patterns (error handling, logging, rate limiting)
- Decisions that future developers will wonder "why did they do it this way?"

Small, local decisions (e.g. variable names, single-function design) do NOT need ADRs.

### How to create an ADR

1. Copy `template.md` to `ADR-NNN-short-title.md`
2. Fill in all sections (context is the most important part)
3. Add a row to the index table above
4. Open a PR — ADRs can be merged quickly (documentation only)

### When to update or supersede an ADR

- If a decision is reversed, add a note and change status to **Superseded**
- Reference the new ADR that supersedes it
- Never delete ADRs — they are a historical record

### ADR template

See [template.md](template.md).
