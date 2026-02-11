# Decision Traceability System

## Purpose

The FDA Predicate Assistant plugin makes autonomous decisions across 42 commands and 7 agents. This document describes the zero-trust audit trail that ensures every decision is independently verifiable by regulatory counsel, quality teams, and FDA reviewers.

## Why Zero-Trust Traceability

1. **Regulatory compliance**: 21 CFR Part 11 principles require that automated decisions maintain complete audit trails
2. **Legal reviewability**: Every autonomous decision (predicate selection, pathway recommendation, risk scoring) must document *why* alternatives were excluded
3. **Reproducibility**: Re-running a command should produce traceable records, not overwrite prior decisions
4. **Post-compaction recovery**: Decision records persist on disk and survive context compaction

## Decision Record Anatomy

Every autonomous decision produces an entry in `audit_log.jsonl` with these components:

### What Was Chosen
- `decision`: The outcome (e.g., "accepted", "Traditional 510(k)", "CRITICAL")
- `subject`: What was evaluated (K-number, product code, pathway name)
- `confidence_score`: Numerical confidence (0-100)

### What Alternatives Were Considered
- `alternatives_considered`: ALL options evaluated, including the chosen one
- This ensures the record shows the full decision space, not just the winner

### Why Each Alternative Was Excluded
- `exclusion_records`: For each rejected option:
  - `subject`: The rejected alternative
  - `reason`: Specific rationale with data reference
  - `data_sources`: Which databases/files informed the exclusion

### What Data Informed the Decision
- `data_sources`: External APIs and databases consulted
- `files_read`: Local files that influenced the decision
- `score_breakdown`: Component-level scoring (command-specific)

## When to Log

### Always Log
- Every predicate accepted, rejected, or deferred (`review`)
- Every pathway recommendation with all pathway scores (`pathway`)
- Every risk level assignment with methodology (`safety`)
- Every deficiency identified with severity justification (`pre-check`)
- Every consistency check result with expected vs. found (`consistency`)
- Every guidance match/exclusion with trigger tier (`guidance`)
- Every test prioritization/exclusion with rationale (`test-plan`)
- Every section draft with data sources used (`draft`)
- Every agent autonomous decision (`agent_decision`)

### Never Log
- User input (the user typed something)
- File reads without decisions
- Status checks or informational queries
- Commands that don't make autonomous decisions (`status`, `configure`, `cache`, `ask`, `monitor`)

## How to Review the Trail

### Interactive Viewer
```
/fda:audit --project NAME
```
Shows a formatted decision log with summaries, filtering, and exclusion detail.

### Programmatic Access
```bash
# All decisions for a project
python3 $FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py --project NAME --show-log

# Only predicate decisions
python3 $FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py --project NAME --show-log --command-filter review --decisions-only

# Only entries with exclusion records
python3 $FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py --project NAME --show-log --exclusions-only

# Summary statistics
python3 $FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py --project NAME --summary
```

### Pipeline Consolidation
After a full pipeline run, consolidate all entries into `pipeline_audit.json`:
```bash
python3 $FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py --project NAME --consolidate
```

## Integration with Other Project Files

| File | Relationship |
|------|-------------|
| `review.json` | Contains predicate decisions; audit log supplements with alternatives and exclusion records |
| `pipeline_audit.json` | Consolidated summary written from audit log entries |
| `pre_check_report.md` | Contains deficiency findings; audit log records each as `deficiency_identified` |
| `consistency_report.md` | Contains check results; audit log records each as `check_passed`/`check_failed`/`check_warned` |

The audit log does NOT replace any existing output file. It supplements them with the "why" — alternatives considered and reasons for exclusion.

## Schema Reference

See `references/audit-logging.md` for the complete JSONL schema, required/optional fields, and all valid action types.

## CLI Reference

See `scripts/fda_audit_logger.py` for the standalone CLI that validates and appends entries.
