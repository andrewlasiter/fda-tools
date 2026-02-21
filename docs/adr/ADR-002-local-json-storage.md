# ADR-002: Local JSON File Storage for Data Persistence

**Status:** Accepted
**Date:** 2025-01-01

## Context

The tool runs on an RA professional's local workstation with no server
infrastructure. Project data includes extracted 510(k) text, predicate analysis
results, standards mappings, and enriched device profiles — all of which may
contain sensitive regulatory work-product or Protected Health Information (PHI)
from clinical data sections of submissions.

Key constraints:
- Offline-first: must function without internet for core workflows
- No PHI may leave the user's machine without explicit consent
- No IT provisioning should be required to install or run the tool
- Projects must be portable (zip a folder, share with colleague)

A flat-file approach where each project is a directory of JSON files satisfies
all constraints with zero infrastructure requirements.

## Decision

All project state is stored as JSON files within a per-project directory
(e.g., `~/fda-510k-data/projects/<project>/`). Key files: `device_profile.json`,
`review.json`, `standards_lookup.json`, `enrichment_metadata.json`.

Atomic writes use a write-to-temp-then-rename pattern to prevent corruption.

## Alternatives Considered

- **SQLite:** ACID guarantees, single-file DB. Rejected for initial prototype
  because it adds schema migration complexity and makes files opaque to RA
  professionals who expect to inspect or hand-edit them.
- **PostgreSQL:** Chosen later for the read-heavy offline device database
  (see ADR-007), but inappropriate for per-project mutable state given the
  server requirement.
- **Remote database:** Unacceptable PHI risk. Data would traverse the network
  without granular consent controls.

## Consequences

- No transactional guarantees across multiple JSON files; callers must handle
  partial-write failures gracefully.
- File locking (fcntl / msvcrt) required for concurrent agent writes.
- JSON schema versioning field (`_schema_version`) required in all files.
- Projects are trivially portable and inspectable, which aids debugging.
