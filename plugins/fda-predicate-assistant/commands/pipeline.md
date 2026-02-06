---
description: Run the full FDA 510(k) pipeline — extract, review, analyze, guidance, presub, outline, and SE comparison in one command
allowed-tools: Bash, Read, Glob, Grep, Write, WebSearch, WebFetch
argument-hint: "<product-code> --project NAME [--device-description TEXT] [--intended-use TEXT] [--years RANGE] [--full-auto]"
---

# FDA 510(k) Full Pipeline Orchestrator

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

You are running the **full FDA 510(k) pipeline** end-to-end. This command orchestrates all plugin commands in dependency order to produce a complete pre-submission package from a product code alone.

**KEY PRINCIPLE: Run autonomously with zero user prompts.** Each step checks preconditions, runs the appropriate command, and records results. Failures are logged and skipped — the pipeline continues to the next step.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Product code** (required) — 3-letter FDA product code (e.g., OVE, KGN, QBJ)
- `--project NAME` (required for full pipeline) — Project name for organizing outputs
- `--device-description TEXT` — Description of the user's device (used to populate placeholders)
- `--intended-use TEXT` — Proposed indications for use (used to populate placeholders)
- `--years RANGE` — Year range for extraction (default: last 5 years)
- `--full-auto` — Pass to /fda:review for fully autonomous predicate scoring
- `--skip STEPS` — Comma-separated step numbers to skip (e.g., `--skip 3,6`)
- `--start-from N` — Start from step N (skip previous steps, assuming their outputs exist)

If no `--project` provided, auto-generate from product code: `{CODE}_{YYYY}` (e.g., `OVE_2026`).

If no `--years` provided, default to last 5 years.

## Resolve API Key

```bash
python3 << 'PYEOF'
import os, re
settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)
if api_key:
    print(f"API_KEY:available")
else:
    print(f"API_KEY:none")
PYEOF
```

## Pipeline Steps

Execute the following steps in order. Before each step, check if its output already exists (skip if so, unless `--force` is set). After each step, record timing and status.

### Step 1/7: Extract (Download PDFs + Extract Predicates)

**Command**: `/fda:extract both --project {PROJECT} --product-codes {CODE} --years {YEARS}`

**Skip condition**: `$PROJECTS_DIR/$PROJECT/output.csv` exists and has > 0 data rows

**Produces**: output.csv, supplement.csv, pdf_data.json, 510k_download.csv

**On failure**: Log error. Pipeline can continue to Step 3 (safety) using API-only data, but Steps 2, 5, 7 will have limited data.

Report: "Step 1/7: Extract — {status} ({N} records in output.csv, {N} PDFs processed)"

### Step 2/7: Review (Score and Validate Predicates)

**Command**: `/fda:review --project {PROJECT} --full-auto` (if `--full-auto` flag set) or `/fda:review --project {PROJECT} --auto` (if not)

**Skip condition**: `$PROJECTS_DIR/$PROJECT/review.json` exists

**Depends on**: Step 1 output (output.csv)

**Produces**: review.json, output_reviewed.csv

**On failure**: Log error. Pipeline continues — later steps fall back to unreviewed predicates.

Report: "Step 2/7: Review — {status} ({N} accepted, {N} rejected, {N} deferred)"

### Step 3/7: Safety Intelligence

**Command**: `/fda:safety --product-code {CODE}`

**Skip condition**: Never skip (always run for latest safety data)

**Produces**: Console output only (safety summary)

**On failure**: Log warning. Pipeline continues.

Report: "Step 3/7: Safety — {status} ({N} MAUDE events, {N} recalls)"

### Step 4/7: Guidance Lookup

**Command**: `/fda:guidance {CODE} --save --project {PROJECT} --depth standard`

If `--device-description` provided, add: `--device-description "{TEXT}"`

**Skip condition**: `$PROJECTS_DIR/$PROJECT/guidance_cache/guidance_index.json` exists

**Produces**: guidance_cache/ directory with guidance_index.json, requirements_matrix.json

**On failure**: Log error. Pipeline continues — later steps fall back to predicate-only data.

Report: "Step 4/7: Guidance — {status} ({N} device-specific, {N} cross-cutting guidance documents)"

### Step 5/7: Pre-Submission Plan

**Command**: `/fda:presub {CODE} --project {PROJECT}`

If `--device-description` provided, add: `--device-description "{TEXT}"`
If `--intended-use` provided, add: `--intended-use "{TEXT}"`

**Skip condition**: `$PROJECTS_DIR/$PROJECT/presub_plan.md` exists

**Depends on**: Steps 2, 4 outputs (optional enrichment)

**Produces**: presub_plan.md

**On failure**: Log error. Pipeline continues.

Report: "Step 5/7: Pre-Sub Plan — {status}"

### Step 6/7: Submission Outline

**Command**: `/fda:submission-outline {CODE} --project {PROJECT} --pathway traditional`

If `--device-description` provided, add: `--device-description "{TEXT}"`
If `--intended-use` provided, add: `--intended-use "{TEXT}"`

**Skip condition**: `$PROJECTS_DIR/$PROJECT/submission_outline.md` exists

**Depends on**: Steps 2, 4 outputs (optional enrichment)

**Produces**: submission_outline.md

**On failure**: Log error. Pipeline continues.

Report: "Step 6/7: Submission Outline — {status}"

### Step 7/7: SE Comparison Table

**Command**: `/fda:compare-se --predicates {TOP_3_PREDICATES} --product-code {CODE} --project {PROJECT}`

Where `{TOP_3_PREDICATES}` are the top 3 accepted predicates from review.json (by confidence score).

If `--device-description` provided, add: `--device-description "{TEXT}"`
If `--intended-use` provided, add: `--intended-use "{TEXT}"`

**Skip condition**: `$PROJECTS_DIR/$PROJECT/se_comparison.md` exists

**Depends on**: Step 2 output (review.json — for predicate selection)

**Produces**: se_comparison.md

**On failure**: Log error. This is the last step.

Report: "Step 7/7: SE Comparison — {status} ({N} predicates compared)"

## Pipeline Completion Report

After all steps complete, present a summary:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FDA 510(k) PIPELINE COMPLETE — {PROJECT_NAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Product Code: {CODE} — {device_name}
Project Dir:  {PROJECTS_DIR}/{PROJECT}

Step Results:
  1. Extract:          {DONE/SKIPPED/FAILED} — {details}
  2. Review:           {DONE/SKIPPED/FAILED} — {details}
  3. Safety:           {DONE/SKIPPED/FAILED} — {details}
  4. Guidance:         {DONE/SKIPPED/FAILED} — {details}
  5. Pre-Sub Plan:     {DONE/SKIPPED/FAILED} — {details}
  6. Submission Outline: {DONE/SKIPPED/FAILED} — {details}
  7. SE Comparison:    {DONE/SKIPPED/FAILED} — {details}

Files Generated:
  {list each file with size}

Steps Skipped: {list with reason}
Steps Failed:  {list with error}

Next Steps for Manual Review:
  1. Review accepted predicates in review.json
  2. Fill in [INSERT: ...] placeholders in presub_plan.md
  3. Complete [YOUR DEVICE: ...] cells in SE comparison table
  4. Review submission outline gap analysis
  5. Consult regulatory affairs team before FDA submission

⚠ All generated documents are AI-assisted starting points.
  Review with your regulatory team before submission.
```

## Error Handling

- **No product code**: ERROR: "Product code is required. Usage: /fda:pipeline OVE --project my-project"
- **Step dependency failure**: Log which steps were affected, continue with available data
- **API unavailable**: Note in summary, continue with flat-file data
- **All steps fail**: Present error summary with troubleshooting suggestions
