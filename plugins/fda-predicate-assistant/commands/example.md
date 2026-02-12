---
description: Randomized end-to-end exercise of ALL plugin commands, skills, and agent workflows — generates a complete example project from a random or specified 510(k) clearance
allowed-tools: Bash, Read, Glob, Grep, Write, WebSearch, WebFetch
argument-hint: "[--k-number K241335] [--product-code CODE --intended-use TEXT] [--project NAME] [--skip STEPS] [--start-from N]"
---

# FDA 510(k) Example — Full Plugin E2E

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

You are running the **full plugin example** — a comprehensive end-to-end exercise of every command, skill, and agent workflow in the FDA Predicate Assistant plugin. This generates a complete example project directory showing all work products the plugin can produce.

**Randomized by default**: When no `--k-number` or `--product-code` is provided, the seed script picks a random recent 510(k) clearance from openFDA. Each run demonstrates a different device. Use `--k-number` to pin a specific clearance for reproducibility.

**KEY PRINCIPLE: Run autonomously with zero user prompts.** Each step checks preconditions, runs the appropriate command, and records results. Failures are logged and skipped — the pipeline continues to the next step. Every step is NON-CRITICAL except Step 0 (Seed).

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--k-number KXXXXXX` — Pin to a specific 510(k) clearance (e.g., K241335). Optional.
- `--product-code CODE` — Pin to a specific product code (requires `--intended-use`). Optional.
- `--intended-use TEXT` — Required with `--product-code`, auto-derived otherwise.
- `--device-description TEXT` — Optional override (auto-derived from classification).
- `--project NAME` — Project name (default: `example_{K}_{CODE}_{DATE}` or `example_random_{CODE}_{DATE}`).
- `--skip STEPS` — Comma-separated step numbers to skip (e.g., `--skip 3,6,22`).
- `--start-from N` — Resume from step N (skip previous steps, assuming their outputs exist).

**Validation**:
- If neither `--k-number` nor `--product-code` provided: **random mode** — the seed script picks a random clearance. This is the default.
- If `--product-code` provided without `--intended-use`: ERROR: "When using --product-code, --intended-use is required. Use --k-number or omit both for random mode."

## Resolve Projects Directory

```bash
PROJECTS_DIR=$(python3 -c "
import os, re
settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    m = re.search(r'projects_dir:\s*(\S+)', content)
    if m and m.group(1) != 'null':
        projects_dir = os.path.expanduser(m.group(1))
print(projects_dir)
")
echo "PROJECTS_DIR=$PROJECTS_DIR"
```

## Coverage Map

This command exercises **all 42 plugin commands**, **5 skills**, and **7 agents** organized into 37 steps across 9 phases. Commands that are interactive-only or meta-orchestrators are noted as OBSERVE (read-only invocation) or SKIP (with rationale logged).

### Commands (42)

| # | Command | Step | Mode |
|---|---------|------|------|
| 1 | `status` | 1 | RUN |
| 2 | `configure` | 2 | OBSERVE (read-only `--show`) |
| 3 | `cache` | 3 | OBSERVE (read-only) |
| 4 | `safety` | 4 | RUN |
| 5 | `guidance` | 5 | RUN |
| 6 | `pathway` | 6 | RUN |
| 7 | `standards` | 7 | RUN |
| 8 | `warnings` | 8 | RUN |
| 9 | `inspections` | 9 | RUN |
| 10 | `literature` | 10 | RUN |
| 11 | `trials` | 11 | RUN |
| 12 | `udi` | 12 | RUN |
| 13 | `monitor` | 13 | RUN (`--add-watch` then `--check`) |
| 14 | `research` | 14 | RUN |
| 15 | `extract` | 15 | RUN |
| 16 | `gap-analysis` | 16 | RUN |
| 17 | `analyze` | 17 | RUN |
| 18 | `summarize` | 18 | RUN |
| 19 | `review` | 19 | RUN (`--full-auto`) |
| 20 | `validate` | 20 | RUN |
| 21 | `propose` | 21 | RUN |
| 22 | `lineage` | 22 | RUN |
| 23 | `presub` | 23 | RUN |
| 24 | `test-plan` | 24 | RUN |
| 25 | `traceability` | 25 | RUN |
| 26 | `submission-outline` | 26 | RUN |
| 27 | `pccp` | 27 | RUN |
| 28 | `calc` | 28 | RUN (shelf-life + sample-size) |
| 29 | `draft` | 29 | RUN (x18 sections) |
| 30 | `compare-se` | 30 | RUN |
| 31 | `ask` | 31 | RUN |
| 32 | `consistency` | 32 | RUN |
| 33 | `pre-check` | 33 | RUN |
| 34 | `dashboard` | 34 | RUN |
| 35 | `assemble` | 35 | RUN |
| 36 | `export` | 36 | RUN |
| 37 | `audit` | 37 | RUN |
| 38 | `portfolio` | 37 | RUN (combined with audit) |
| 39 | `start` | — | SKIP (interactive wizard) |
| 40 | `import` | — | SKIP (requires external PDF/XML) |
| 41 | `pipeline` | — | SKIP (subset of this command) |
| 42 | `data-pipeline` | — | SKIP (overlaps with extract) |

### Skills (5)

| Skill | Exercised At |
|-------|-------------|
| `fda-predicate-assessment` | Step 21 (propose) — triggers predicate strategy assessment |
| `fda-510k-knowledge` | Step 17 (analyze) — triggers pipeline knowledge |
| `fda-safety-signal-triage` | Step 4 (safety) — triggers safety signal triage |
| `fda-510k-submission-outline` | Step 26 (submission-outline) — triggers outline knowledge |
| `fda-plugin-e2e-smoke` | Step 15 (extract) — exercises the same scripts |

### Agents (7)

| Agent | Step | Invocation |
|-------|------|------------|
| `research-intelligence` | 14 | Spawned by `/fda:research` |
| `data-pipeline-manager` | 15 | Spawned by `/fda:extract` |
| `extraction-analyzer` | 17 | Spawned by `/fda:analyze` |
| `presub-planner` | 23 | Spawned by `/fda:presub` |
| `submission-writer` | 29 | Spawned by `/fda:draft` |
| `review-simulator` | 33 | Spawned by `/fda:pre-check` |
| `submission-assembler` | 35 | Spawned by `/fda:assemble` |

## Step Criticality

**Step 0 is CRITICAL** — if seeding fails there is no project data. All other steps (1–37) are **NON-CRITICAL**. Failures are logged as DEGRADED and the pipeline continues. Partial output is still a valid demonstration.

## Argument Threading

After Step 0, read `device_profile.json` and `review.json` to extract threading values used by all downstream steps:

| Value | Source | Used By |
|-------|--------|---------|
| `PRODUCT_CODE` | `device_profile.json` | All steps |
| `DEVICE_NAME` | `device_profile.json` | Steps needing device context |
| `DEVICE_DESCRIPTION` | `device_profile.json` | 5, 10, 14, 23–29, 30, 31 |
| `INTENDED_USE` | `device_profile.json` | 14, 23–29, 30, 31 |
| `APPLICANT` | `device_profile.json` | 9, 13 |
| `TOP3_PREDICATES` | `review.json` (top 3 by confidence) | 20, 22, 30 |
| `PRIMARY_PREDICATE` | `review.json` (highest confidence) | 20, 21 |
| `PROJECT_NAME` | `--project` or auto-generated | All steps |

## Pipeline Steps

Execute steps in order. Before each step, check `--skip` and `--start-from`. After each step, record timing and status.

---

### Step 0: Seed Project (CRITICAL)

**Phase**: Seed

If `--k-number` provided:
```bash
python3 "$FDA_PLUGIN_ROOT/scripts/seed_test_project.py" --k-number {K_NUMBER} --project {PROJECT_NAME} --output-dir "$PROJECTS_DIR"
```

If `--product-code` provided:
```bash
python3 "$FDA_PLUGIN_ROOT/scripts/seed_test_project.py" --product-code {CODE} --project {PROJECT_NAME} --output-dir "$PROJECTS_DIR"
```

If neither provided (random mode):
```bash
python3 "$FDA_PLUGIN_ROOT/scripts/seed_test_project.py" --random --project {PROJECT_NAME} --output-dir "$PROJECTS_DIR"
```

Note: Random mode produces `query.json` and `review.json` but not `device_profile.json`. If `device_profile.json` is missing after seed, construct a minimal one from `query.json` and classification data:

```bash
python3 << 'PYEOF'
import json, os
project_dir = os.path.join("PROJECTS_DIR", "PROJECT_NAME")
profile_path = os.path.join(project_dir, "device_profile.json")
if not os.path.exists(profile_path):
    query_path = os.path.join(project_dir, "query.json")
    if os.path.exists(query_path):
        with open(query_path) as f:
            query = json.load(f)
        # Minimal profile for random mode
        profile = {
            "product_code": query.get("product_code", ""),
            "device_name": query.get("device_name", ""),
            "intended_use": query.get("intended_use", ""),
            "device_description": query.get("device_name", ""),
            "source": "seed_generator_random_minimal"
        }
        with open(profile_path, "w") as f:
            json.dump(profile, f, indent=2)
            f.write("\n")
        print("CREATED_MINIMAL_PROFILE")
    else:
        print("ERROR:no query.json")
else:
    print("PROFILE_EXISTS")
PYEOF
```

**Post-step**: Read `device_profile.json` and `review.json` to extract all threading values (PRODUCT_CODE, INTENDED_USE, DEVICE_DESCRIPTION, DEVICE_NAME, APPLICANT, TOP3_PREDICATES, PRIMARY_PREDICATE).

**Produces**: `query.json`, `review.json`, `device_profile.json`

**On failure**: **CRITICAL — HALT.** "Step 0 (Seed) failed. No project data. Error: {error}."

---

### Phase 1: Environment (Steps 1–3)

#### Step 1: Status

**Command**: `/fda:status`

**Produces**: Console output (data freshness, script availability, record counts)

#### Step 2: Configure (read-only)

**Command**: `/fda:configure --show`

**Produces**: Console output (current settings)

#### Step 3: Cache

**Command**: `/fda:cache --project {PROJECT_NAME}`

**Produces**: Console output (cached data summary)

---

### Phase 2: Research & Intelligence (Steps 4–14)

#### Step 4: Safety Intelligence

**Command**: `/fda:safety --product-code {PRODUCT_CODE}`

**Produces**: Console output (MAUDE events, recalls)

#### Step 5: Guidance Lookup

**Command**: `/fda:guidance {PRODUCT_CODE} --save --project {PROJECT_NAME}`

Thread: `--device-description "{DEVICE_DESCRIPTION}"` if available.

**Produces**: `guidance_cache/` directory

#### Step 6: Pathway Analysis

**Command**: `/fda:pathway {PRODUCT_CODE}`

**Produces**: Console output (pathway recommendation with scoring)

#### Step 7: Standards Lookup

**Command**: `/fda:standards --product-code {PRODUCT_CODE} --save --project {PROJECT_NAME}`

**Produces**: Console output + cached standards data

#### Step 8: Warning Letters

**Command**: `/fda:warnings {PRODUCT_CODE} --recalls --risk-profile --save`

**Produces**: Console output (warning letters, enforcement trends)

#### Step 9: Inspections

**Command**: `/fda:inspections "{APPLICANT}" --product-code {PRODUCT_CODE} --citations --compliance`

**Produces**: Console output (inspection history, CFR citations)

#### Step 10: Literature Search

**Command**: `/fda:literature --product-code {PRODUCT_CODE} --device-description "{DEVICE_DESCRIPTION}" --project {PROJECT_NAME} --depth quick`

**Produces**: Console output (PubMed results, evidence categorization)

#### Step 11: Clinical Trials

**Command**: `/fda:trials "{DEVICE_NAME}" --product-code {PRODUCT_CODE} --project {PROJECT_NAME} --save`

**Produces**: Console output (ClinicalTrials.gov matches)

#### Step 12: UDI Lookup

**Command**: `/fda:udi --product-code {PRODUCT_CODE} --save --project {PROJECT_NAME}`

**Produces**: Console output (GUDID records)

#### Step 13: Monitor Setup

**Command**: `/fda:monitor --add-watch {PRODUCT_CODE}` then `/fda:monitor --check`

**Produces**: Console output (watch list confirmation, current alerts)

#### Step 14: Research & Competitive Intelligence

**Command**: `/fda:research {PRODUCT_CODE} --project {PROJECT_NAME} --device-description "{DEVICE_DESCRIPTION}" --intended-use "{INTENDED_USE}"`

**Produces**: Console output (predicate landscape, competitive analysis)

**Agent**: Triggers `research-intelligence` agent.

---

### Phase 3: Data Pipeline (Steps 15–18)

#### Step 15: Extract (Download + Extract Predicates)

**Command**: `/fda:extract both --project {PROJECT_NAME} --product-codes {PRODUCT_CODE} --years {LAST_5_YEARS}`

**Produces**: `output.csv`, `supplement.csv`, `pdf_data.json`

**Agent**: Triggers `data-pipeline-manager` agent.

#### Step 16: Gap Analysis

**Command**: `/fda:gap-analysis --product-codes {PRODUCT_CODE} --project {PROJECT_NAME}`

**Produces**: Console output (missing K-numbers, PDFs, extractions)

#### Step 17: Analyze Extraction Results

**Command**: `/fda:analyze --project {PROJECT_NAME}`

**Produces**: Console output (extraction statistics, predicate relationships)

**Agent**: Triggers `extraction-analyzer` agent.

#### Step 18: Summarize 510(k) PDFs

**Command**: `/fda:summarize --project {PROJECT_NAME} --product-codes {PRODUCT_CODE}`

**Produces**: Console output (cross-device section comparisons)

---

### Phase 4: Predicate Work (Steps 19–22)

#### Step 19: Review Predicates

**Command**: `/fda:review --project {PROJECT_NAME} --full-auto`

**Produces**: `review.json` (updated), `output_reviewed.csv`

**Post-step**: Re-read `review.json` to refresh TOP3_PREDICATES and PRIMARY_PREDICATE for downstream steps.

#### Step 20: Validate Device Numbers

**Command**: `/fda:validate {TOP3_PREDICATES (space-separated)} --project {PROJECT_NAME}`

**Produces**: Console output (validation results for each K-number)

#### Step 21: Propose Predicates

**Command**: `/fda:propose --predicates {PRIMARY_PREDICATE} --project {PROJECT_NAME}`

**Produces**: Console output (predicate validation, IFU comparison, confidence scoring)

**Skill**: Triggers `fda-predicate-assessment`.

#### Step 22: Lineage Graph

**Command**: `/fda:lineage --predicates {TOP3_PREDICATES}`

**Produces**: Console output or `lineage.json` (predicate citation chains)

---

### Phase 5: Planning (Steps 23–28)

#### Step 23: Pre-Submission Plan

**Command**: `/fda:presub {PRODUCT_CODE} --project {PROJECT_NAME}`

Thread: `--device-description "{DEVICE_DESCRIPTION}"` and `--intended-use "{INTENDED_USE}"` if available.

**Produces**: `presub_plan.md`

**Agent**: Triggers `presub-planner` agent.

#### Step 24: Test Plan

**Command**: `/fda:test-plan {PRODUCT_CODE} --project {PROJECT_NAME}`

Thread: `--device-description "{DEVICE_DESCRIPTION}"` and `--intended-use "{INTENDED_USE}"` if available.

**Produces**: `test_plan.md`

#### Step 25: Traceability Matrix

**Command**: `/fda:traceability --project {PROJECT_NAME}`

Thread: `--device-description "{DEVICE_DESCRIPTION}"` and `--intended-use "{INTENDED_USE}"` if available.

**Produces**: `traceability_matrix.md`

#### Step 26: Submission Outline

**Command**: `/fda:submission-outline {PRODUCT_CODE} --project {PROJECT_NAME}`

Thread: `--device-description "{DEVICE_DESCRIPTION}"` and `--intended-use "{INTENDED_USE}"` if available.

**Produces**: `submission_outline.md`

**Skill**: Triggers `fda-510k-submission-outline`.

#### Step 27: PCCP (Predetermined Change Control Plan)

**Command**: `/fda:pccp --project {PROJECT_NAME} --product-code {PRODUCT_CODE}`

Thread: `--device-description "{DEVICE_DESCRIPTION}"` and `--intended-use "{INTENDED_USE}"` if available.

**Produces**: `pccp.md` or console output

#### Step 28: Regulatory Calculators

Run two calculations:

**28a — Shelf Life**:
`/fda:calc shelf-life --ambient-temp 25 --accelerated-temp 55 --desired-shelf-life 24`

**28b — Sample Size**:
`/fda:calc sample-size --confidence 95 --margin 5 --expected-rate 1`

**Produces**: Console output (calculation results)

---

### Phase 6: Drafting (Steps 29–31)

#### Step 29: Draft All 18 eSTAR Sections

Draft each section sequentially:

**Command** (per section): `/fda:draft {SECTION} --project {PROJECT_NAME} --device-description "{DEVICE_DESCRIPTION}" --intended-use "{INTENDED_USE}"`

Sections in order:

1. `device-description`
2. `predicate-justification`
3. `se-discussion`
4. `510k-summary`
5. `cover-letter`
6. `performance-summary`
7. `testing-rationale`
8. `biocompatibility`
9. `sterilization`
10. `shelf-life`
11. `software`
12. `emc-electrical`
13. `clinical`
14. `labeling`
15. `human-factors`
16. `truthful-accuracy`
17. `financial-certification`
18. `doc`

**Produces**: `draft_{section}.md` for each (18 files)

**Agent**: Triggers `submission-writer` agent.

**On failure per section**: Log which sections failed, continue with the rest. Report: "Step 29: Draft — {N}/18 sections drafted, {M} failed"

#### Step 30: SE Comparison Table

**Command**: `/fda:compare-se --predicates {TOP3_PREDICATES} --product-code {PRODUCT_CODE} --project {PROJECT_NAME}`

Thread: `--device-description "{DEVICE_DESCRIPTION}"` and `--intended-use "{INTENDED_USE}"` if available.

**Produces**: `se_comparison.md`

#### Step 31: Ask (Regulatory Q&A)

**Command**: `/fda:ask "What are the key testing requirements for a {PRODUCT_CODE} device with intended use: {INTENDED_USE (first 100 chars)}?" --product-code {PRODUCT_CODE} --project {PROJECT_NAME}`

**Produces**: Console output (regulatory Q&A response)

---

### Phase 7: Quality & Review (Steps 32–34)

#### Step 32: Consistency Check

**Command**: `/fda:consistency --project {PROJECT_NAME}`

**Produces**: Console output (cross-validation results)

#### Step 33: Pre-Check (FDA Review Simulation)

**Command**: `/fda:pre-check --project {PROJECT_NAME}`

**Produces**: Console output (readiness score, deficiency list)

**Agent**: Triggers `review-simulator` agent.

#### Step 34: Dashboard

**Command**: `/fda:dashboard --project {PROJECT_NAME} --save`

**Produces**: Console output + saved dashboard summary

---

### Phase 8: Packaging (Steps 35–36)

#### Step 35: Assemble eSTAR

**Command**: `/fda:assemble --project {PROJECT_NAME}`

**Produces**: `estar/` directory with structured submission package

**Agent**: Triggers `submission-assembler` agent.

#### Step 36: Export Package

**Command**: `/fda:export --project {PROJECT_NAME} --format zip`

**Produces**: ZIP package of the complete submission

---

### Phase 9: Audit & Portfolio (Step 37)

#### Step 37: Audit Trail + Portfolio

**37a — Audit**:
`/fda:audit --project {PROJECT_NAME} --summary`

**Produces**: Console output (decision audit trail)

**37b — Portfolio**:
`/fda:portfolio`

**Produces**: Console output (cross-project summary)

---

## Skipped Commands (logged in report)

These commands are intentionally not executed, with rationale:

| Command | Reason |
|---------|--------|
| `start` | Interactive onboarding wizard — requires user prompts |
| `import` | Requires an external eSTAR PDF/XML file as input |
| `pipeline` | This command is a strict subset of `/fda:example` |
| `data-pipeline` | Overlaps with `extract` + `gap-analysis` (Steps 15–16) |

---

## Audit Logging

1. **At start**: Write `example_e2e_started` entry with all arguments and random seed info
2. **Before each step**: Write `step_started` entry
3. **After each step**: Write `step_completed`, `step_failed`, `step_skipped`, or `step_degraded` entry with timing
4. **At end**: Write `example_e2e_completed` entry with full coverage summary

All entries append to `$PROJECTS_DIR/$PROJECT_NAME/audit_log.jsonl`.

## Completion Report

After all steps complete, present the full coverage summary:

```
  FDA Plugin Example — Full E2E Report
  {PRODUCT_CODE} — {DEVICE_NAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Project: {PROJECT_NAME}
  Mode: {random | k-number K241335 | product-code OVE}

STEP RESULTS (37 steps)
────────────────────────────────────────

  Phase 0: Seed
   0. Seed Project         ✓  {CODE} — {N} predicates

  Phase 1: Environment
   1. Status               ✓
   2. Configure             ✓  (read-only)
   3. Cache                ✓

  Phase 2: Research & Intelligence
   4. Safety               ✓  {N} MAUDE events, {N} recalls
   5. Guidance             ✓  {N} documents cached
   6. Pathway              ✓  Recommended: {pathway}
   7. Standards            ✓  {N} recognized standards
   8. Warnings             ✓  {N} warning letters
   9. Inspections          ✓  {N} inspections found
  10. Literature           ✓  {N} PubMed results
  11. Trials               ✓  {N} clinical trials
  12. UDI                  ✓  {N} GUDID records
  13. Monitor              ✓  Watch added for {CODE}
  14. Research             ✓  Competitive landscape complete

  Phase 3: Data Pipeline
  15. Extract              ✓  {N} records, {N} PDFs
  16. Gap Analysis         ✓  {N} gaps identified
  17. Analyze              ✓  Extraction analysis complete
  18. Summarize            ✓  {N} summaries compared

  Phase 4: Predicate Work
  19. Review               ✓  {N} accepted, {N} rejected
  20. Validate             ✓  {N}/{N} valid
  21. Propose              ✓  Predicate strategy scored
  22. Lineage              ✓  {N}-generation chain

  Phase 5: Planning
  23. Pre-Sub Plan         ✓  presub_plan.md
  24. Test Plan            ✓  test_plan.md
  25. Traceability         ✓  traceability_matrix.md
  26. Submission Outline   ✓  submission_outline.md
  27. PCCP                 ✓  pccp.md
  28. Calculators          ✓  shelf-life + sample-size

  Phase 6: Drafting
  29. Draft Sections       ✓  {N}/18 sections
  30. SE Comparison        ✓  {N} predicates compared
  31. Ask Q&A              ✓  Response generated

  Phase 7: Quality & Review
  32. Consistency          ✓  {N} issues
  33. Pre-Check            ✓  Score: {N}/100
  34. Dashboard            ✓  Dashboard saved

  Phase 8: Packaging
  35. Assemble eSTAR       ✓  estar/ directory
  36. Export               ✓  ZIP package

  Phase 9: Audit
  37. Audit + Portfolio    ✓  Audit trail complete

  Status: ✓ done  ✗ failed  ⚠ degraded  ○ skipped

COVERAGE SUMMARY
────────────────────────────────────────

  Commands:  {N}/42 exercised ({M} skipped: start, import, pipeline, data-pipeline)
  Skills:    5/5 triggered
  Agents:    7/7 invoked
  Files:     {N} work products generated

SKIPPED (with rationale)
────────────────────────────────────────

  start          — Interactive wizard (requires user prompts)
  import         — Requires external PDF/XML input
  pipeline       — Strict subset of this command
  data-pipeline  — Overlaps with extract + gap-analysis

FILES GENERATED
────────────────────────────────────────

  {list each file with size}

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Error Handling

- **Step 0 failure**: HALT. "Seed failed — no project to work with. Error: {error}."
- **Any other step failure**: Log as DEGRADED, continue. Record in completion report.
- **No arguments (random mode)**: This is the default — not an error.
- **--product-code without --intended-use**: ERROR with instructions.
- **API unavailable**: Note in report, continue with cached/flat-file data.
- **All steps fail after seed**: Present error summary with troubleshooting suggestions.
