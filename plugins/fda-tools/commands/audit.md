---
description: View the decision audit trail — filter by command, action, date, subject; full exclusion rationale
allowed-tools: Bash, Read
argument-hint: "--project NAME [--command CMD] [--summary] [--decisions-only] [--exclusions-only]"
---

# FDA Decision Audit Trail Viewer

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

> For external API dependencies and connection status, see [CONNECTORS.md](../CONNECTORS.md).

## Resolve Plugin Root

**Before running any bash commands that reference `$FDA_PLUGIN_ROOT`**, resolve the plugin install path:

```bash
FDA_PLUGIN_ROOT=$(python3 -c "
import json, os
f = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(f):
    d = json.load(open(f))
    for k, v in d.get('plugins', {}).items():
        if k.startswith('fda-predicate-assistant@'):
            for e in v:
                p = e.get('installPath', '')
                if os.path.isdir(p):
                    print(p); exit()
print('')
")
echo "FDA_PLUGIN_ROOT=$FDA_PLUGIN_ROOT"
```

If `$FDA_PLUGIN_ROOT` is empty, report an error: "Could not locate the FDA Predicate Assistant plugin installation. Make sure the plugin is installed and enabled."

---

You are displaying the decision audit trail for a project. The audit log records every autonomous decision with alternatives considered, exclusion rationale, and data sources.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--project NAME` (required) — Project to view
- `--command CMD` — Filter to a specific command (review, pathway, safety, etc.)
- `--action TYPE` — Filter to a specific action type
- `--subject TEXT` — Filter to a specific subject (K-number, product code)
- `--summary` — Show summary statistics only
- `--decisions-only` — Show only entries that contain a decision
- `--exclusions-only` — Show only entries with exclusion records
- `--after DATE` — Show entries after this date (ISO format)
- `--before DATE` — Show entries before this date (ISO format)
- `--limit N` — Limit to N most recent entries (default: 50)

## Step 1: Resolve Project Directory

```bash
PROJECTS_DIR=$(python3 -c "
import os, re
settings = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
if os.path.exists(settings):
    with open(settings) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m:
            print(os.path.expanduser(m.group(1).strip()))
            exit()
print(os.path.expanduser('~/fda-510k-data/projects'))
")
echo "PROJECTS_DIR=$PROJECTS_DIR"
```

Check that the project exists and `audit_log.jsonl` is present:
```bash
ls -la "$PROJECTS_DIR/$PROJECT_NAME/audit_log.jsonl" 2>/dev/null || echo "NO_AUDIT_LOG"
```

If no audit log exists: "No audit log found for project '{name}'. Decision logging starts automatically when you run commands like `/fda:review`, `/fda:pathway`, `/fda:safety`, `/fda:pre-check`, etc."

## Step 2: Get Summary

Always start by fetching the summary:

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --summary
```

## Step 3: Query the Log

If `--summary` was specified, stop after Step 2 and present just the summary.

Otherwise, query with filters:

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --show-log \
  ${COMMAND_FILTER:+--command-filter "$COMMAND_FILTER"} \
  ${ACTION_FILTER:+--action-filter "$ACTION_FILTER"} \
  ${SUBJECT_FILTER:+--subject-filter "$SUBJECT_FILTER"} \
  ${AFTER:+--after "$AFTER"} \
  ${BEFORE:+--before "$BEFORE"} \
  ${DECISIONS_ONLY:+--decisions-only} \
  ${EXCLUSIONS_ONLY:+--exclusions-only} \
  --limit ${LIMIT:-50}
```

## Step 4: Present Output

Format the output using the standard FDA Professional CLI format:

```
  FDA Decision Audit Trail
  Project: {project_name} | {total} entries | {date_range}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.22.0

SUMMARY
────────────────────────────────────────

  Commands: {cmd1} ({N}), {cmd2} ({N}), ...
  Decisions: {N} auto, {N} manual, {N} deferred
  Exclusions documented: {N}

DECISION LOG
────────────────────────────────────────

  [2026-02-09 12:00] review > predicate_accepted
    Subject: K241335 | Confidence: 85 | Mode: full-auto
    Chosen: accepted — "Score 85/100, same product code, 3 SE citations"
    Excluded: K222222 — "Different product code (KGN), score 35"
    Excluded: K111111 — "Class I recall 2024, score 12"
    Sources: output.csv, openFDA 510k API, openFDA recall API

  [2026-02-09 12:01] pathway > pathway_recommended
    Subject: OVE | Confidence: 87 | Mode: auto
    Chosen: Traditional 510(k) — "Score 87/100, 45 predicates, strong guidance"
    Excluded: Special 510(k) — "No prior clearance. Score: 30/100"
    Excluded: De Novo — "45 existing clearances. Score: 15/100"
    Excluded: PMA — "Class II device. Score: 10/100"
    Sources: openFDA classification, openFDA 510k, fda-guidance-index.md

────────────────────────────────────────
  This audit trail is auto-generated. See references/decision-traceability.md
  for the traceability system documentation.
────────────────────────────────────────
```

Adapt the format to the actual data. If there are many entries, group by command and show a count for each.

## Error Handling

- **No project**: "Project name required. Use `--project NAME`."
- **No audit log**: "No audit log found. Commands like `/fda:review`, `/fda:pathway`, `/fda:safety` will populate it."
- **Empty log**: "Audit log exists but contains no entries."
- **Parse errors**: Report any malformed lines but continue displaying valid entries.
