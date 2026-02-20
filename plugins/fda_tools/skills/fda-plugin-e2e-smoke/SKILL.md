---
name: fda-plugin-e2e-smoke
description: Run deterministic live smoke tests for the FDA plugin scripts (gap analysis + predicate extraction). Use when validating install/runtime behavior, reproducing extraction regressions, or verifying fixes beyond unit tests.
---

# FDA Plugin E2E Smoke

## Overview

Use this skill to run a repeatable live smoke workflow against bundled plugin scripts, without relying on slash-command host execution.

It validates:
- `scripts/gap_analysis.py` manifest generation
- `scripts/predicate_extractor.py` extraction output
- expected CSV artifacts and key extracted identifiers

## When To Use

Use this skill when:
- A script-level regression is suspected (especially extractor behavior).
- You need post-fix verification that is stronger than unit tests.
- You need a deterministic local smoke check before release.

Skip this skill when:
- The user only wants static file checks.
- The user only wants full `pytest` suite status.

## Quick Start

Run from plugin root:

```bash
bash skills/fda-plugin-e2e-smoke/scripts/run_smoke.sh
```

Optional flags:

```bash
bash skills/fda-plugin-e2e-smoke/scripts/run_smoke.sh --tmp-dir /tmp/my-smoke
bash skills/fda-plugin-e2e-smoke/scripts/run_smoke.sh --workers 1
bash skills/fda-plugin-e2e-smoke/scripts/run_smoke.sh --cleanup
```

## What The Script Does

1. Creates a temporary smoke workspace with synthetic PMN/baseline files.
2. Runs `scripts/gap_analysis.py` to generate `gap_manifest.csv`.
3. Generates a sample PDF containing known K/DEN references.
4. Runs `scripts/predicate_extractor.py` against that PDF.
5. Validates output CSVs contain the expected extracted identifiers.

## Output Contract

On success:
- Exit code `0`
- `SMOKE_STATUS:PASS` printed
- Paths to generated artifacts printed

On failure:
- Exit code `1` for validation/script failures
- Exit code `2` for multiprocessing semaphore sandbox restrictions (SemLock)

## Guardrails

- Run from repository root so relative script paths resolve.
- Do not treat smoke results as regulatory conclusions; this is runtime QA only.
- If SemLock appears in restricted environments, rerun with elevated permissions or outside sandbox.
