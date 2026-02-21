# ADR-005: stdlib-Only Constraint for lib/ Modules

**Status:** Accepted
**Date:** 2025-08-01

## Context

The codebase is split into two layers:
- `lib/` — the stable, importable library layer used by both scripts and agents
- `scripts/` — task-specific scripts that may have richer dependencies

Third-party packages introduce several risks in `lib/`:
- Version conflicts when multiple scripts or plugins pin different versions
- Security surface (each additional package is an additional supply-chain risk)
- Installation failures on restricted workstations where pip is blocked or
  network access is limited
- API churn requiring lib/ changes when upstream packages release breaking changes

Python 3.9+ stdlib is stable, well-documented, and sufficient for the core
abstractions: file I/O, JSON, HTTP (urllib), multiprocessing, and logging.

## Decision

All modules under `lib/` import only from the Python standard library.
Third-party imports in `lib/` are a CI-enforced hard failure. Scripts under
`scripts/` and plugins may import third-party packages, but must not re-export
them through `lib/`.

A pre-commit hook (`scripts/check_lib_imports.py`) statically verifies this
constraint on every commit.

## Alternatives Considered

- **Allow requests in lib/:** `requests` is more ergonomic than `urllib`.
  Rejected because `urllib` is sufficient for the simple FDA API calls in lib/,
  and `requests` pulls in `certifi`, `charset-normalizer`, `idna`, `urllib3` —
  all of which need pinning and auditing.
- **Allow pydantic in lib/:** Strong runtime validation. Rejected because pydantic
  v1/v2 API fragmentation has caused widespread breakage; the constraint is
  better enforced via mypy at development time.
- **No restriction (everything can import anything):** Rejected because it
  results in transitive dependency conflicts that are difficult to debug and
  reproduce across different user environments.

## Consequences

- lib/ code is more verbose in places (urllib vs requests, manual JSON
  validation vs pydantic).
- The constraint eliminates an entire category of dependency-related bugs.
- New contributors must be informed of this rule; the CI check enforces it.
- scripts/ has no restriction and uses pandas, reportlab, etc. freely.
