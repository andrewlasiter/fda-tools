# Audit Logging Standard

## Purpose

Provides a regulatory audit trail for all autonomous decisions made by the FDA Predicate Assistant plugin. Designed for traceability per 21 CFR Part 11 principles — every automated decision is logged with timestamp, rationale, and data sources.

## Log File Location

- **Per-command log**: `$PROJECT_DIR/audit_log.jsonl` (append-only, one JSON object per line)
- **Pipeline consolidated log**: `$PROJECT_DIR/pipeline_audit.json` (written at pipeline completion)

## Schema

Each audit log entry is a single JSON object on one line:

```json
{
  "timestamp": "2026-02-05T12:00:00Z",
  "command": "review",
  "version": "4.6.0",
  "mode": "full-auto",
  "action": "predicate_accepted",
  "subject": "K241335",
  "decision": "accepted",
  "rationale": "Auto-accepted (full-auto, score >= 70). Score: 85/100. SE section citations: 3, product code match: yes, no recalls.",
  "confidence_score": 85,
  "data_sources": ["output.csv", "openFDA 510k API", "openFDA recall API"],
  "files_read": ["~/fda-510k-data/projects/OVE_2026/output.csv"],
  "files_written": ["~/fda-510k-data/projects/OVE_2026/review.json"],
  "warnings": [],
  "error": null
}
```

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 string | When the action occurred |
| `command` | string | Which plugin command generated this entry |
| `version` | string | Plugin version (for schema evolution) |
| `mode` | string | "full-auto", "auto", "interactive", or "pipeline" |
| `action` | string | What happened (see Action Types below) |

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `subject` | string | The entity acted upon (K-number, product code, file path) |
| `decision` | string | The decision made (accepted, rejected, deferred, skipped) |
| `rationale` | string | Human-readable explanation of why this decision was made |
| `confidence_score` | number | Confidence score if applicable |
| `data_sources` | string[] | External data sources consulted |
| `files_read` | string[] | Input files read |
| `files_written` | string[] | Output files written or modified |
| `warnings` | string[] | Any warnings generated |
| `error` | string | Error message if the action failed |
| `duration_ms` | number | How long the action took |
| `metadata` | object | Command-specific additional data |

## Action Types

### Review Command
- `predicate_accepted` — Predicate accepted (with score and rationale)
- `predicate_rejected` — Predicate rejected (with reason)
- `predicate_deferred` — Predicate deferred for manual review
- `predicate_reclassified` — Predicate reclassified from original extraction
- `review_completed` — Full review session completed

### Pipeline Command
- `pipeline_started` — Pipeline execution began
- `step_started` — Individual step began
- `step_completed` — Individual step completed successfully
- `step_failed` — Individual step failed (with error)
- `step_skipped` — Step skipped (output already exists)
- `step_degraded` — Step completed with degraded output
- `pipeline_completed` — Pipeline finished (with summary)
- `pipeline_halted` — Pipeline halted due to critical failure

### Pre-Sub / Outline Commands
- `placeholder_resolved` — A [INSERT:] placeholder was auto-filled
- `placeholder_converted` — A [INSERT:] was converted to [TODO:]
- `data_synthesized` — Data was synthesized from project/API sources
- `document_generated` — Output document was written

### Compare-SE Command
- `predicate_inferred` — Predicates inferred from project data
- `table_generated` — SE comparison table created
- `cell_auto_populated` — Table cell auto-filled from FDA data

### Safety Command
- `safety_query_completed` — MAUDE/recall query finished
- `safety_data_unavailable` — API unavailable, degraded output

### Extract Command
- `extraction_started` — PDF extraction began
- `extraction_completed` — PDF extraction finished

## Writing Audit Logs

Commands should append to the audit log using this pattern:

```python
import json, os
from datetime import datetime, timezone

def append_audit_log(project_dir, entry):
    """Append a single audit entry to the project's audit log."""
    entry.setdefault('timestamp', datetime.now(timezone.utc).isoformat())
    entry.setdefault('version', '4.6.0')
    log_path = os.path.join(project_dir, 'audit_log.jsonl')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
```

## Pipeline Consolidated Log

At pipeline completion, read `audit_log.jsonl` and write a summary `pipeline_audit.json`:

```json
{
  "pipeline_version": "4.6.0",
  "project": "OVE_2026",
  "started_at": "2026-02-05T12:00:00Z",
  "completed_at": "2026-02-05T12:15:00Z",
  "duration_seconds": 900,
  "mode": "full-auto",
  "steps": {
    "extract": {"status": "completed", "duration_ms": 120000},
    "review": {"status": "completed", "duration_ms": 45000, "accepted": 5, "rejected": 2},
    "safety": {"status": "degraded", "reason": "API timeout"},
    "guidance": {"status": "completed", "duration_ms": 30000},
    "presub": {"status": "completed", "duration_ms": 15000},
    "outline": {"status": "completed", "duration_ms": 20000},
    "compare_se": {"status": "completed", "duration_ms": 60000}
  },
  "total_decisions": 7,
  "auto_decisions": 7,
  "manual_decisions": 0,
  "warnings": ["Safety data degraded — API timeout"],
  "files_generated": [
    "output.csv", "review.json", "presub_plan.md",
    "submission_outline.md", "se_comparison.md"
  ]
}
```
