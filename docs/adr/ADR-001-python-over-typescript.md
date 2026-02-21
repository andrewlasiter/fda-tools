# ADR-001: Python Over TypeScript for Main Codebase

**Status:** Accepted
**Date:** 2025-01-01

## Context

The FDA regulatory workflow tool requires heavy data processing, PDF parsing, and
REST API calls against FDA public databases. The team evaluated both Python and
TypeScript as primary implementation languages at project inception.

Key requirements that drove evaluation:
- PDF extraction from 510(k) summaries and eSTAR submissions
- Tabular data manipulation for predicate comparison
- Report generation (HTML, PDF, Markdown)
- Integration with FDA open data APIs
- Batch analysis scripts run by RA professionals locally

The FDA tooling ecosystem — reportlab, pandas, tabula-py, pdfplumber — is
Python-native. Equivalent TypeScript libraries are less mature, less maintained,
and lack feature parity for regulatory document processing. The core team has
deep Python expertise. Type safety concerns are addressed via mypy strict mode
and runtime validation.

Claude Code is language-agnostic and can work with either language; the choice
is driven by ecosystem fit, not tooling constraints.

## Decision

Python 3.9+ is the primary language for all modules in `lib/`, `scripts/`, and
`plugins/`. TypeScript is permitted for future web-facing components only.

## Alternatives Considered

- **TypeScript:** Strong type system, good async support. Rejected because the
  FDA/medical document tooling ecosystem is overwhelmingly Python-native. Porting
  or wrapping libraries would add maintenance burden without benefit.
- **Mixed (Python + TypeScript):** Rejected because it doubles the dependency
  surface and complicates the single-file distribution model.

## Consequences

- mypy strict mode enforced in CI to compensate for Python's dynamic typing.
- Python 3.9+ minimum version to ensure `typing` and `importlib` stability.
- Third-party dependencies pinned in `requirements.txt` with hash verification.
- RA professionals must have Python 3.9+ installed; installer script provided.
