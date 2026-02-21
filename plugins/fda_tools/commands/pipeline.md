
<!-- NOTE: This command has been migrated to use centralized FDAClient (FDA-114)
     Old pattern: urllib.request.Request + urllib.request.urlopen
     New pattern: FDAClient with caching, retry, and rate limiting
     Migration date: 2026-02-20
-->

---
description: Run the full FDA 510(k) pipeline — extract, review, analyze, guidance, presub, outline, and SE comparison in one command
allowed-tools: Bash, Read, Glob, Grep, Write, WebSearch, WebFetch
argument-hint: "<product-code> --project NAME [--device-description TEXT] [--intended-use TEXT] [--years RANGE] [--full-auto]"
---

# FDA 510(k) Full Pipeline Orchestrator

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
        if k.startswith('fda-tools@'):
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

- **Product code** (required for 510(k)) — 3-letter FDA product code (e.g., OVE, KGN, QBJ)
- `--pma NUMBER` — **PMA pathway flag**: Routes to PMA pipeline instead of 510(k) (e.g., `--pma P170019`)
- `--project NAME` (required for full pipeline) — Project name for organizing outputs
- `--device-description TEXT` — Description of the user's device (used to populate placeholders)
- `--intended-use TEXT` — Proposed indications for use (used to populate placeholders)
- `--years RANGE` — Year range for extraction (default: last 5 years)
- `--full-auto` — Pass to /fda:review for fully autonomous predicate scoring
- `--skip STEPS` — Comma-separated step numbers to skip (e.g., `--skip 3,6`)
- `--start-from N` — Start from step N (skip previous steps, assuming their outputs exist)

If no `--project` provided, auto-generate from product code: `{CODE}_{YYYY}` (e.g., `OVE_2026`).

If no `--years` provided, default to last 5 years.

## Pathway Detection (FDA-109)

**Before any pipeline steps**, determine the regulatory pathway:

```python
# Pathway detection logic
pma_flag = "--pma" in arguments  # e.g., --pma P170019
pma_number = extract_pma_number(arguments)  # P-number pattern

if pma_flag or pma_number:
    pathway = "PMA"
    # Route to PMA Pipeline below
else:
    pathway = "510k"
    # Continue with standard 510(k) pipeline steps
```

**If PMA pathway detected**: Skip Steps 1-7 below and execute the **PMA Pipeline** section instead.

**If 510(k) pathway**: Continue with standard pipeline (Steps 0-7).

## Resolve API Key

```bash
python3 << 'PYEOF'
import os, re
settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
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
| 2.5 | Diversity Gate | NON-CRITICAL | Continue with DEGRADED warning if POOR diversity |
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

settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

params = {"search": f'device_name:{search_terms}', "limit": "100"}
if api_key:
    params["api_key"] = api_key
url = f"https://api.fda.gov/device/classification.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})
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

### Step 2.5: Predicate Diversity Gate (FDA-130)

**Runs after Step 2 completes successfully.** Checks whether the accepted predicate set has adequate diversity before continuing the pipeline. A low-diversity set increases SE rejection risk.

**Skip condition**: Fewer than 2 accepted predicates in review.json.

```python
import json, sys, os

# Load accepted predicates
review_path = os.path.join(os.environ.get('PROJECT_DIR', '.'), 'review.json')
predicates = []
if os.path.exists(review_path):
    review = json.load(open(review_path))
    for k_num, v in review.get('predicates', {}).items():
        if v.get('decision') == 'accepted':
            predicates.append({
                'k_number': k_num,
                'manufacturer': v.get('manufacturer', ''),
                'device_name': v.get('device_name', ''),
                'clearance_date': v.get('clearance_date', ''),
                'product_code': v.get('product_code', ''),
                'decision_description': v.get('decision_description', ''),
                'contact_country': v.get('contact_country', ''),
            })

if len(predicates) >= 2:
    try:
        from fda_tools.lib.predicate_diversity import PredicateDiversityAnalyzer
        result = PredicateDiversityAnalyzer(predicates).analyze()
        score = result.get('total_score', 0)
        grade = result.get('grade', '?')
        print(f"DIVERSITY_GATE:score={score}|grade={grade}|n_predicates={len(predicates)}")
    except Exception as e:
        print(f"DIVERSITY_GATE:error|{e}")
else:
    print(f"DIVERSITY_GATE:skipped|n_predicates={len(predicates)}")
```

**If diversity score < 40 (POOR)**: Log a DEGRADED warning in the pipeline report:
> ⚠ DIVERSITY WARNING: Accepted predicates scored {score}/100 ({grade}). SE arguments built on a low-diversity predicate set risk FDA questions about equivalence validity. Consider adding predicates from different manufacturers or technology generations via `/fda:research --depth deep`.

**If diversity score 40-59 (FAIR)**: Log a NON-CRITICAL note:
> ℹ Predicate diversity: FAIR ({score}/100). Acceptable, but broader predicate diversity strengthens SE arguments.

**If diversity score ≥ 60 (GOOD/EXCELLENT)**: Log silently in audit log only.

Report in pipeline completion summary: "Step 2.5: Diversity Gate — {GOOD|FAIR|POOR} ({score}/100, {N} predicates)"

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
  Generated: {date} | Project: {PROJECT_NAME} | v5.22.0

STEP RESULTS
────────────────────────────────────────

  1. Extract            ✓  {details}
  2. Review             ✓  {details}
  2.5 Diversity Gate    ✓  {score}/100 — {grade} ({N} predicates)
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

### Sources Checked

Append a sources table to every output showing which external APIs were queried and their status. See [CONNECTORS.md](../CONNECTORS.md) for the standard format. Only include rows for sources this command actually uses.

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

---

## PMA Pipeline (FDA-109)

**Activated when**: `--pma NUMBER` flag is present in arguments.

PMA submissions follow 21 CFR Part 814 requirements and differ significantly from 510(k):
- **No predicate device**: PMA requires valid scientific evidence, not SE to a predicate
- **Clinical data required**: Pivotal clinical trial data is mandatory for most Class III devices
- **Manufacturing review**: Full GMP inspection is standard
- **Post-approval**: PMA devices require supplements, annual reports, and PAS tracking

### PMA Step Criticality

| Step | Name | Criticality | On Failure |
|------|------|-------------|------------|
| P1 | PMA Search & Intelligence | **CRITICAL** | HALT — no comparable PMA data for context |
| P2 | Clinical Requirements | NON-CRITICAL | Continue with DEGRADED — clinical section will be skeletal |
| P3 | Draft Sections | NON-CRITICAL | Continue with DEGRADED — user must draft manually |
| P4 | Supplement Tracking | NON-CRITICAL | Continue with DEGRADED |
| P5 | Timeline Prediction | NON-CRITICAL | Continue with DEGRADED |
| P6 | Approval Probability | NON-CRITICAL | Continue with DEGRADED |
| P7 | PMA Gap Analysis | NON-CRITICAL | Continue with DEGRADED |

### PMA Step P1: Search & Intelligence

**Command**: `/fda:pma-search --pma {PMA_NUMBER} --product-code {CODE} --intelligence --download-ssed`

**Skip condition**: `$PROJECT_DIR/pma_data/` directory exists with at least one JSON file.

**Produces**: `pma_data/*.json`, `ssed_cache/*.json`, intelligence_report.md

**On failure**: **CRITICAL — HALT PMA PIPELINE.** Report: "PMA PIPELINE HALTED: Could not locate PMA {PMA_NUMBER}. Verify the PMA number is valid and the FDA API is accessible."

Report: "PMA Step P1: Search & Intelligence — {status} ({N} comparable PMAs found, SSED: {downloaded/not downloaded})"

### PMA Step P2: Clinical Requirements Mapping

**Command**: `/fda:clinical-requirements --pma {PMA_NUMBER} --product-code {CODE}`

**Skip condition**: `$PROJECT_DIR/clinical_requirements.json` exists.

**Produces**: `clinical_requirements.json` with study design precedent from comparable PMAs.

**On failure**: NON-CRITICAL — Log warning, continue. Clinical section will require full manual population.

Report: "PMA Step P2: Clinical Requirements — {status} (study type: {design}, enrollment: {N}, follow-up: {duration})"

### PMA Step P3: Generate PMA Section Drafts

**Command**: `/fda:pma-draft --all --project {PROJECT} --pma {PMA_NUMBER} --device-description {DESC} --intended-use {IFU}`

**Generates all mandatory PMA sections:**
- `pma_draft_device-description.md`
- `pma_draft_ssed.md`
- `pma_draft_clinical.md`
- `pma_draft_manufacturing.md`
- `pma_draft_preclinical.md`
- `pma_draft_biocompatibility.md`
- `pma_draft_cover-letter.md`
- `pma_draft_summary.md`

**On failure**: NON-CRITICAL — Report which sections failed to generate. User must draft manually.

Report: "PMA Step P3: Draft Sections — {status} ({N}/{total} sections generated, {todo_count} [TODO:] items)"

### PMA Step P4: Supplement Tracking

**Command**: `/fda:pma-supplements --pma {PMA_NUMBER}`

**Skip condition**: `$PROJECT_DIR/supplement_history.json` exists.

**Produces**: `supplement_history.json` — lifecycle of supplements for the reference PMA.

**On failure**: NON-CRITICAL — Log warning. Note that supplement tracking context is unavailable.

Report: "PMA Step P4: Supplement Tracking — {status} ({N} supplements found for {PMA_NUMBER})"

### PMA Step P5: Timeline Prediction

**Command**: `/fda:pma-timeline --product-code {CODE}`

**Skip condition**: `$PROJECT_DIR/timeline_prediction.json` exists.

**Produces**: `timeline_prediction.json` — predicted review duration and milestone timeline.

**On failure**: NON-CRITICAL — Log warning. Timeline section of planning report will use historical averages.

Report: "PMA Step P5: Timeline Prediction — {status} (predicted review: {N} months, approval probability: {pct}%)"

### PMA Step P6: Approval Probability

**Command**: `/fda:approval-probability --pma {PMA_NUMBER} --product-code {CODE}`

**Skip condition**: `$PROJECT_DIR/approval_probability.json` exists.

**Produces**: `approval_probability.json` — risk score and key success factors.

**On failure**: NON-CRITICAL — Log warning.

Report: "PMA Step P6: Approval Probability — {status} (score: {N}/100, risk tier: {LOW|MEDIUM|HIGH})"

### PMA Step P7: Gap Analysis

After completing P1-P6, run PMA gap analysis:

```python
import json, os, glob

pdir = os.environ.get('PROJECT_DIR', '.')

# Check all expected PMA draft files
required_sections = [
    "pma_draft_device-description.md",
    "pma_draft_ssed.md",
    "pma_draft_clinical.md",
    "pma_draft_manufacturing.md",
    "pma_draft_preclinical.md",
    "pma_draft_biocompatibility.md",
    "pma_draft_cover-letter.md",
    "pma_draft_summary.md",
]

gaps = []
for section in required_sections:
    fpath = os.path.join(pdir, section)
    if not os.path.exists(fpath):
        gaps.append(f"MISSING:{section}")
    else:
        with open(fpath) as f:
            content = f.read()
        todos = content.count("[TODO:")
        inserts = content.count("[INSERT:")
        citations = content.count("[CITATION NEEDED]")
        print(f"SECTION:{section}|todos={todos}|inserts={inserts}|citations={citations}")

for g in gaps:
    print(g)
```

Report the gap analysis: which sections are missing, total [TODO:] and [INSERT:] counts.

### PMA Pipeline Completion Report

```
  FDA PMA Pipeline Completion Report
  {CODE} — {device_name} | PMA Reference: {PMA_NUMBER}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Project: {PROJECT_NAME} | v5.22.0

PATHWAY: PMA (21 CFR Part 814) — Class III Device

PMA STEP RESULTS
────────────────────────────────────────

  P1. Search & Intelligence  ✓  {N} comparable PMAs, SSED downloaded
  P2. Clinical Requirements  ✓  {study_type}, N={enrollment}, {months} follow-up
  P3. Draft Sections         ✓  {N}/8 sections, {todo} TODOs, {insert} INSERTs
  P4. Supplement Tracking    ✓  {N} supplements for {PMA_NUMBER}
  P5. Timeline Prediction    ✓  {months} months predicted review
  P6. Approval Probability   ✓  {score}/100 ({tier} risk)
  P7. Gap Analysis           ✓  {gaps} gaps identified

CRITICAL NEXT STEPS (PMA submissions require extensive manual input)
────────────────────────────────────────

  1. Populate clinical data in pma_draft_clinical.md with actual study results
  2. Complete all [INSERT:] items with real manufacturing/test data
  3. Resolve [TODO:] items with your RA professional and biostatistician
  4. Engage FDA Pre-Submission Meeting (Q-Sub) before finalizing PMA
  5. Conduct IDE review if clinical trials are planned
  6. Allow 180-day standard review (360-day if panel required)

⚠ PMA submissions require substantially more data than 510(k). AI-generated
  drafts serve only as structural templates — all clinical and test data must
  come from validated studies.

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```
