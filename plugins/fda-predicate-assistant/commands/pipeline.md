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

## Pre-Flight Validation

Before starting any pipeline steps, perform these checks:

1. **Project directory writable**: Verify `$PROJECTS_DIR/$PROJECT_NAME/` can be created/written to. If not, ERROR and halt.
2. **Product code valid**: Query openFDA classification for the product code. If not found, WARN but continue (flat-file fallback may work).
3. **Full-auto requirements**: If `--full-auto` is active, verify `--device-description` and `--intended-use` are provided (or can be synthesized from `--project` data). If missing, ERROR: "In --full-auto mode, --device-description and --intended-use are required for steps 5-7."
4. **Dependencies installed**: Run the dependencies check (Python packages). If missing, attempt `pip install` before starting.

## Step Criticality Classification

Steps are classified as **CRITICAL** or **NON-CRITICAL**:

| Step | Name | Criticality | On Failure |
|------|------|-------------|------------|
| 1 | Extract | **CRITICAL** | HALT pipeline — no data to work with |
| 2 | Review | **CRITICAL** | HALT pipeline — predicate validation required for downstream |
| 3 | Safety | NON-CRITICAL | Continue with DEGRADED warning |
| 4 | Guidance | NON-CRITICAL | Continue with DEGRADED warning |
| 5 | Pre-Sub Plan | NON-CRITICAL | Continue with DEGRADED warning |
| 6 | Submission Outline | NON-CRITICAL | Continue with DEGRADED warning |
| 7 | SE Comparison | NON-CRITICAL | Continue with DEGRADED warning |

**CRITICAL step failure** = Pipeline halts immediately. Report which step failed, what the error was, and which downstream steps were skipped.

**NON-CRITICAL step failure** = Pipeline continues. Mark the step as `DEGRADED` in the completion report. Downstream steps that depend on the failed step's output will have reduced data quality (noted in their own output).

## Argument Threading Table

Arguments provided to `/fda:pipeline` MUST be threaded to downstream steps:

| Argument | Steps That Receive It |
|----------|----------------------|
| `--product-code` | 1 (extract), 3 (safety), 4 (guidance), 5 (presub), 6 (outline), 7 (compare-se) |
| `--project` | 1 (extract), 2 (review), 4 (guidance), 5 (presub), 6 (outline), 7 (compare-se) |
| `--device-description` | 4 (guidance), 5 (presub), 6 (outline), 7 (compare-se) |
| `--intended-use` | 5 (presub), 6 (outline), 7 (compare-se) |
| `--years` | 1 (extract) |
| `--full-auto` | 2 (review as --full-auto), 5 (presub), 6 (outline), 7 (compare-se) |

**Verify each step invocation includes all threaded arguments.** Missing a threaded argument (e.g., not passing `--device-description` to step 5) causes placeholder issues downstream.

## Pipeline Steps

Execute the following steps in order. Before each step, check if its output already exists (skip if so, unless `--force` is set). After each step, record timing and status.

### Step 0: Product Code Auto-Identification (if needed)

**Runs when**: `--product-code` not provided but `--device-description` is available.

Auto-identify the product code from the device description:

1. **openFDA classification search**: Query `https://api.fda.gov/device/classification.json` with keywords from the device description
2. **foiaclass.txt keyword matching**: Grep `foiaclass.txt` for key terms from the device description
3. **Rank candidates**: Score by keyword match relevance, return top 5 candidates
4. **Auto-select**: Use the highest-ranked candidate. Log: "Auto-identified product code: {CODE} ({device_name}) from device description. Confidence: {score}."

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

# Extract keywords from device description
description = "DEVICE_DESCRIPTION"  # Replace
keywords = [w for w in description.lower().split() if len(w) > 3 and w not in {'with', 'that', 'this', 'from', 'have', 'been', 'used', 'device'}]
search_terms = '+AND+'.join(f'"{kw}"' for kw in keywords[:5])

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

params = {"search": f'device_name:{search_terms}', "limit": "5"}
if api_key:
    params["api_key"] = api_key
url = f"https://api.fda.gov/device/classification.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        if data.get("results"):
            for i, r in enumerate(data["results"]):
                print(f"CANDIDATE:{i+1}|{r.get('product_code','?')}|{r.get('device_name','?')}|{r.get('device_class','?')}|{r.get('regulation_number','?')}")
except Exception as e:
    print(f"ERROR:{e}")
PYEOF
```

If auto-identification fails, ERROR: "Could not identify product code from device description. Provide --product-code explicitly."

### Step 1/7: Extract (Download PDFs + Extract Predicates)

**Command**: `/fda:extract both --project {PROJECT} --product-codes {CODE} --years {YEARS}`

**Skip condition**: `$PROJECTS_DIR/$PROJECT/output.csv` exists and has > 0 data rows

**Produces**: output.csv, supplement.csv, pdf_data.json, 510k_download.csv

**On failure**: **CRITICAL — HALT PIPELINE.** Report: "PIPELINE HALTED: Step 1 (Extract) failed. No extraction data available for downstream steps. Error: {error}. Skipped steps: 2-7."

Report: "Step 1/7: Extract — {status} ({N} records in output.csv, {N} PDFs processed)"

### Step 2/7: Review (Score and Validate Predicates)

**Command**: `/fda:review --project {PROJECT} --full-auto` (if `--full-auto` flag set) or `/fda:review --project {PROJECT} --auto` (if not)

**Skip condition**: `$PROJECTS_DIR/$PROJECT/review.json` exists

**Depends on**: Step 1 output (output.csv)

**Produces**: review.json, output_reviewed.csv

**On failure**: **CRITICAL — HALT PIPELINE.** Report: "PIPELINE HALTED: Step 2 (Review) failed. Predicate validation is required for SE comparison and submission planning. Error: {error}. Skipped steps: 3-7."

Report: "Step 2/7: Review — {status} ({N} accepted, {N} rejected, {N} deferred)"

### Step 3/7: Safety Intelligence

**Command**: `/fda:safety --product-code {CODE}`

**Skip condition**: Never skip (always run for latest safety data)

**Produces**: Console output only (safety summary)

**On failure**: NON-CRITICAL — Log warning, mark as DEGRADED, continue. Report: "Step 3/7: Safety — DEGRADED (API unavailable or error: {error}). Downstream steps will lack safety intelligence data."

Report: "Step 3/7: Safety — {status} ({N} MAUDE events, {N} recalls)"

### Step 4/7: Guidance Lookup

**Command**: `/fda:guidance {CODE} --save --project {PROJECT} --depth standard`

If `--device-description` provided, add: `--device-description "{TEXT}"`

**Skip condition**: `$PROJECTS_DIR/$PROJECT/guidance_cache/guidance_index.json` exists

**Produces**: guidance_cache/ directory with guidance_index.json, requirements_matrix.json

**On failure**: NON-CRITICAL — Log warning, mark as DEGRADED, continue. Report: "Step 4/7: Guidance — DEGRADED (error: {error}). Submission outline and pre-sub plan will have reduced guidance data."

Report: "Step 4/7: Guidance — {status} ({N} device-specific, {N} cross-cutting guidance documents)"

### Step 5/7: Pre-Submission Plan

**Command**: `/fda:presub {CODE} --project {PROJECT}`

If `--device-description` provided, add: `--device-description "{TEXT}"`
If `--intended-use` provided, add: `--intended-use "{TEXT}"`

**Skip condition**: `$PROJECTS_DIR/$PROJECT/presub_plan.md` exists

**Depends on**: Steps 2, 4 outputs (optional enrichment)

**Produces**: presub_plan.md

**On failure**: NON-CRITICAL — Log warning, mark as DEGRADED, continue. Report: "Step 5/7: Pre-Sub Plan — DEGRADED (error: {error})."

Report: "Step 5/7: Pre-Sub Plan — {status}"

### Step 6/7: Submission Outline

**Command**: `/fda:submission-outline {CODE} --project {PROJECT} --pathway traditional`

If `--device-description` provided, add: `--device-description "{TEXT}"`
If `--intended-use` provided, add: `--intended-use "{TEXT}"`

**Skip condition**: `$PROJECTS_DIR/$PROJECT/submission_outline.md` exists

**Depends on**: Steps 2, 4 outputs (optional enrichment)

**Produces**: submission_outline.md

**On failure**: NON-CRITICAL — Log warning, mark as DEGRADED, continue. Report: "Step 6/7: Submission Outline — DEGRADED (error: {error})."

Report: "Step 6/7: Submission Outline — {status}"

### Step 7/7: SE Comparison Table

**Command**: `/fda:compare-se --predicates {TOP_3_PREDICATES} --product-code {CODE} --project {PROJECT}`

Where `{TOP_3_PREDICATES}` are the top 3 accepted predicates from review.json (by confidence score).

If `--device-description` provided, add: `--device-description "{TEXT}"`
If `--intended-use` provided, add: `--intended-use "{TEXT}"`

**Skip condition**: `$PROJECTS_DIR/$PROJECT/se_comparison.md` exists

**Depends on**: Step 2 output (review.json — for predicate selection)

**Produces**: se_comparison.md

**On failure**: NON-CRITICAL — Log warning, mark as DEGRADED. Report: "Step 7/7: SE Comparison — DEGRADED (error: {error})."

Report: "Step 7/7: SE Comparison — {status} ({N} predicates compared)"

## Audit Logging

The pipeline writes audit log entries per the schema in `references/audit-logging.md`:

1. **At pipeline start**: Write `pipeline_started` entry with all arguments and pre-flight validation results
2. **Before each step**: Write `step_started` entry
3. **After each step**: Write `step_completed`, `step_failed`, `step_skipped`, or `step_degraded` entry with timing
4. **At pipeline end**: Write `pipeline_completed` or `pipeline_halted` entry with full summary

All entries append to `$PROJECTS_DIR/$PROJECT_NAME/audit_log.jsonl`.

At pipeline completion, also write `$PROJECTS_DIR/$PROJECT_NAME/pipeline_audit.json` with the consolidated summary (see `references/audit-logging.md` for schema).

## Pipeline Completion Report

After all steps complete, present a summary using the standard FDA Professional CLI format (see `references/output-formatting.md`):

```
  FDA Pipeline Completion Report
  {CODE} — {device_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Project: {PROJECT_NAME} | v4.0.0

STEP RESULTS
────────────────────────────────────────

  1. Extract            ✓  {details}
  2. Review             ✓  {details}
  3. Safety             ⚠  DEGRADED — {details}
  4. Guidance           ✓  {details}
  5. Pre-Sub Plan       ✓  {details}
  6. Submission Outline ✓  {details}
  7. SE Comparison      ✗  FAILED — {details}

  Use status indicators: ✓ done, ✗ failed, ⚠ degraded, ○ skipped

FILES GENERATED
────────────────────────────────────────

  {list each file with size}

NEXT STEPS
────────────────────────────────────────

  1. Review accepted predicates in review.json
  2. Fill in [INSERT: ...] placeholders in presub_plan.md
  3. Complete [YOUR DEVICE: ...] cells in SE comparison table
  4. Review submission outline gap analysis
  5. Consult regulatory affairs team before FDA submission

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Error Handling

- **No product code**: ERROR: "Product code is required. Usage: /fda:pipeline OVE --project my-project"
- **Step dependency failure**: Log which steps were affected, continue with available data
- **API unavailable**: Note in summary, continue with flat-file data
- **All steps fail**: Present error summary with troubleshooting suggestions
