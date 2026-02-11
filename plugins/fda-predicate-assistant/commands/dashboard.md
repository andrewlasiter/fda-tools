---
description: Project status dashboard — aggregates drafted sections, consistency results, readiness score, TODO counts, decision audit trail, and cross-project portfolio view
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: "--project NAME [--save] [--audit] [--portfolio] [--set-target PROJECT DATE]"
---

# FDA Project Dashboard

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

You are generating a comprehensive project status dashboard. This is distinct from `/fda:status` which checks raw data availability and API connectivity. The dashboard focuses on **project-level progress** -- what's been drafted, what's consistent, and what's left to do.

> **Consolidated command.** This command also covers decision audit trail viewing (use `--audit`) and cross-project portfolio overview (use `--portfolio`). These were previously separate commands.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--project NAME` (required unless `--portfolio`) -- Project to dashboard
- `--save` -- Save dashboard report as `dashboard.md` in the project directory
- `--audit` -- Show decision audit trail for the project (filter with `--command CMD`, `--summary`, `--decisions-only`, `--exclusions-only`)
- `--portfolio` -- Show cross-project portfolio view (no `--project` needed)
- `--set-target PROJECT DATE` -- Set target submission date for a project (YYYY-MM-DD format, used with `--portfolio`)
- `--format table|detailed` -- Portfolio output format (default: table)

If no `--project` specified and no `--portfolio`, check if only one project exists and use that. If multiple exist, list them and ask the user to specify.

## Step 1: Load Project Data

Read settings and locate project:

```bash
python3 << 'PYEOF'
import os, glob, json, re
from datetime import datetime

# Read settings
settings_path = os.path.expanduser("~/.claude/fda-predicate-assistant.local.md")
projects_dir = os.path.expanduser("~/fda-510k-data/projects")
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    m = re.search(r'projects_dir:\s*(\S+)', content)
    if m:
        projects_dir = os.path.expanduser(m.group(1))

project_name = "$PROJECT_NAME"  # Substituted by command parser
proj_dir = os.path.join(projects_dir, project_name)

if not os.path.isdir(proj_dir):
    print(f"ERROR:Project directory not found: {proj_dir}")
    exit(1)

# Inventory all files
files = {}
for f in sorted(os.listdir(proj_dir)):
    fp = os.path.join(proj_dir, f)
    if os.path.isfile(fp):
        stat = os.stat(fp)
        files[f] = {"size": stat.st_size, "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()}

print(f"PROJECT_DIR:{proj_dir}")
print(f"FILE_COUNT:{len(files)}")

# Drafts
drafts = sorted([f for f in files if f.startswith("draft_") and f.endswith(".md")])
print(f"DRAFT_COUNT:{len(drafts)}")
for d in drafts:
    fp = os.path.join(proj_dir, d)
    with open(fp) as fh:
        content = fh.read()
    words = len(content.split())
    todos = content.count("[TODO:")
    citations = content.count("[CITATION NEEDED]")
    inserts = len(re.findall(r'\[INSERT[^\]]*\]', content))
    section = d.replace("draft_", "").replace(".md", "").replace("-", " ").title()
    print(f"DRAFT:{d}|section={section}|words={words}|todos={todos}|citations={citations}|inserts={inserts}")

# Review status
review_path = os.path.join(proj_dir, "review.json")
if os.path.exists(review_path):
    with open(review_path) as fh:
        review = json.load(fh)
    preds = review.get("predicates", {})
    accepted = sum(1 for v in preds.values() if v.get("decision") == "accepted")
    rejected = sum(1 for v in preds.values() if v.get("decision", "").startswith("rejected"))
    deferred = sum(1 for v in preds.values() if v.get("decision") == "deferred")
    mode = review.get("review_mode", "unknown")
    print(f"REVIEW:mode={mode}|total={len(preds)}|accepted={accepted}|rejected={rejected}|deferred={deferred}")
else:
    print("REVIEW:none")

# Query metadata
query_path = os.path.join(proj_dir, "query.json")
if os.path.exists(query_path):
    with open(query_path) as fh:
        query = json.load(fh)
    pc = query.get("product_codes", query.get("filters", {}).get("product_codes", []))
    print(f"PRODUCT_CODES:{','.join(pc) if isinstance(pc, list) else pc}")
else:
    print("PRODUCT_CODES:unknown")

# Guidance cache
guidance_dir = os.path.join(proj_dir, "guidance_cache")
if os.path.isdir(guidance_dir):
    guidance_files = glob.glob(os.path.join(guidance_dir, "*.md"))
    print(f"GUIDANCE_COUNT:{len(guidance_files)}")
else:
    print("GUIDANCE_COUNT:0")

# SE comparison
se_files = glob.glob(os.path.join(proj_dir, "se_comparison*.md"))
print(f"SE_COMPARISON:{len(se_files)}")

# Test plan
print(f"TEST_PLAN:{'yes' if os.path.exists(os.path.join(proj_dir, 'test_plan.md')) else 'no'}")

# Safety report
print(f"SAFETY_REPORT:{'yes' if os.path.exists(os.path.join(proj_dir, 'safety_report.md')) else 'no'}")

# Literature
print(f"LITERATURE:{'yes' if os.path.exists(os.path.join(proj_dir, 'literature.md')) else 'no'}")

# Traceability
print(f"TRACEABILITY:{'yes' if os.path.exists(os.path.join(proj_dir, 'traceability_matrix.md')) else 'no'}")

# eSTAR export
estar_files = glob.glob(os.path.join(proj_dir, "estar_export_*.xml"))
print(f"ESTAR_EXPORT:{len(estar_files)}")
PYEOF
```

## Step 2: Calculate Readiness Score

Use the formula from `references/readiness-score-formula.md`:

**Mandatory Section Score** (50 pts):
Map each draft file to its mandatory section weight. Check word count for completeness (>200 words = full, <200 with TODOs = template).

**Optional Section Bonus** (15 pts):
Count applicable vs present optional sections.

**Consistency Check Score** (25 pts):
If a consistency check has been run (look for `consistency_report.md`), parse its results. Otherwise default to 12.5.

**Penalties**:
Sum all `[TODO:]`, `[CITATION NEEDED]`, and `[INSERT ...]` items across drafts.

Calculate final SRI score.

## Step 3: Determine Stage

Based on what data exists:

| Data Present | Stage |
|-------------|-------|
| No review.json | Stage 2: Data Collection |
| review.json but no drafts | Stage 3: Analysis |
| Drafts exist, <50% sections | Stage 4a: Early Drafting |
| Drafts exist, ≥50% sections | Stage 4b: Late Drafting |
| eSTAR export exists | Stage 5: Assembly |

## Step 4: Generate Dashboard

Present using standard FDA Professional CLI format:

```
  FDA Project Dashboard
  {product_code} — {project_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.22.0

SUBMISSION READINESS
────────────────────────────────────────

  SRI: {score}/100 — {tier}

  Stage: {stage_name} ({stage_description})

PREDICATE REVIEW
────────────────────────────────────────

  {If review.json exists:}
  Mode: {mode} | Accepted: {N} | Rejected: {N} | Deferred: {N}
  Top predicates: {list top 3 by score}

  {If no review.json:}
  ✗  Not yet reviewed — run /fda:review --project {name}

DRAFTED SECTIONS ({N}/18)
────────────────────────────────────────

  | # | Section | Words | TODOs | Citations | Status |
  |---|---------|-------|-------|-----------|--------|
  | 01 | Cover Letter | {n} | {n} | {n} | {DRAFT/COMPLETE/MISSING} |
  | 03 | 510(k) Summary | {n} | {n} | {n} | {status} |
  | 06 | Device Description | {n} | {n} | {n} | {status} |
  ...

  Total words: {N} | Total TODOs: {N} | Total citations needed: {N}

SUPPORTING DATA
────────────────────────────────────────

  Guidance documents: {N} cached
  SE comparison: {present/missing}
  Test plan: {present/missing}
  Safety report: {present/missing}
  Literature review: {present/missing}
  Traceability matrix: {present/missing}

SCORE BREAKDOWN
────────────────────────────────────────

  Mandatory sections:   {N}/50
  Optional sections:    {N}/15
  Consistency checks:   {N}/25
  Penalties:           -{N}
                       ─────
  SRI Total:           {N}/100

NEXT STEPS
────────────────────────────────────────

  {Context-aware recommendations based on what's missing}

  Examples:
  - "Run /fda:review --project NAME to accept predicates" (if no review.json)
  - "Run /fda:draft --project NAME to generate remaining sections" (if <50% drafted)
  - "Fill in 12 [TODO:] items in draft_device-description.md" (if TODOs exist)
  - "Run /fda:consistency --project NAME to validate cross-document alignment" (if no consistency report)
  - "Run /fda:assemble --project NAME to package for submission" (if ≥80% complete)
  - "Run /fda:pre-check --project NAME to simulate FDA review" (if SRI ≥70)

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Step 5: Save (Optional)

If `--save` flag is provided, write the dashboard report to `{project_dir}/dashboard.md`.

## Decision Audit Trail (--audit)

When `--audit` is specified, display the decision audit trail for the project. The audit log records every autonomous decision with alternatives considered, exclusion rationale, and data sources.

### Audit Arguments

- `--command CMD` -- Filter to a specific command (review, pathway, safety, etc.)
- `--action TYPE` -- Filter to a specific action type
- `--subject TEXT` -- Filter to a specific subject (K-number, product code)
- `--summary` -- Show summary statistics only
- `--decisions-only` -- Show only entries that contain a decision
- `--exclusions-only` -- Show only entries with exclusion records
- `--after DATE` -- Show entries after this date (ISO format)
- `--before DATE` -- Show entries before this date (ISO format)
- `--limit N` -- Limit to N most recent entries (default: 50)

### Fetch Audit Summary

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --summary
```

### Query Audit Log with Filters

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

### Audit Output Format

```
DECISION AUDIT TRAIL
────────────────────────────────────────

  Commands: {cmd1} ({N}), {cmd2} ({N}), ...
  Decisions: {N} auto, {N} manual, {N} deferred
  Exclusions documented: {N}

  [2026-02-09 12:00] review > predicate_accepted
    Subject: K241335 | Confidence: 85 | Mode: full-auto
    Chosen: accepted -- "Score 85/100, same product code, 3 SE citations"
    Excluded: K222222 -- "Different product code (KGN), score 35"
    Sources: output.csv, openFDA 510k API, openFDA recall API
```

If no audit log exists: "No audit log found for project '{name}'. Decision logging starts automatically when you run commands like `/fda:review`, `/fda:pathway`, `/fda:safety`, etc."

## Cross-Project Portfolio (--portfolio)

When `--portfolio` is specified, generate a cross-project portfolio view of all FDA 510(k) projects. No `--project` is required.

### Discover All Projects

```bash
python3 << 'PYEOF'
import json, os, re, glob
from datetime import datetime

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m: projects_dir = os.path.expanduser(m.group(1).strip())

for qpath in glob.glob(os.path.join(projects_dir, '*/query.json')):
    pdir = os.path.dirname(qpath)
    pname = os.path.basename(pdir)
    try:
        with open(qpath) as f:
            query = json.load(f)
    except:
        query = {}

    has_review = os.path.exists(os.path.join(pdir, 'review.json'))
    has_guidance = os.path.isdir(os.path.join(pdir, 'guidance_cache'))
    has_presub = os.path.exists(os.path.join(pdir, 'presub_plan.md'))
    has_outline = os.path.exists(os.path.join(pdir, 'submission_outline.md'))
    has_se = os.path.exists(os.path.join(pdir, 'se_comparison.md'))
    has_estar = os.path.isdir(os.path.join(pdir, 'estar'))

    output_csv = os.path.join(pdir, 'output.csv')
    extraction_count = 0
    if os.path.exists(output_csv):
        with open(output_csv) as f:
            extraction_count = sum(1 for _ in f) - 1

    accepted_predicates = []
    if has_review:
        with open(os.path.join(pdir, 'review.json')) as f:
            review = json.load(f)
        accepted_predicates = [k for k, v in review.get('predicates', {}).items() if v.get('decision') == 'accepted']

    product_codes = query.get('stage1', {}).get('product_codes', [])
    created = query.get('created', 'Unknown')
    completeness = sum([bool(extraction_count > 0), has_review, has_guidance, has_presub, has_outline, has_se])

    print(f"PROJECT:{pname}|codes={','.join(product_codes)}|created={created}|extractions={extraction_count}|predicates={len(accepted_predicates)}|completeness={completeness}/6|review={'Y' if has_review else 'N'}|guidance={'Y' if has_guidance else 'N'}|presub={'Y' if has_presub else 'N'}|outline={'Y' if has_outline else 'N'}|se={'Y' if has_se else 'N'}|estar={'Y' if has_estar else 'N'}")

    for kn in accepted_predicates:
        print(f"PREDICATE:{pname}|{kn}")
PYEOF
```

### Portfolio Output

Present a cross-project summary including:
- Project summary table (name, product code, extractions, predicates, stage, completeness)
- Cross-project intelligence (shared predicates, common standards/guidance)
- Submission timeline with Gantt-style progress bars
- Overall portfolio status (ready for submission, in progress, early stage)

### Set Target Submission Date (--set-target)

If `--set-target PROJECT DATE` is specified, write `{projects_dir}/{PROJECT}/timeline.json`.

## Error Handling

- **Project not found**: "Project '{name}' not found in {projects_dir}. Run `/fda:status` to see available projects."
- **Empty project**: "Project '{name}' has no data yet. Run `/fda:extract both --project {name}` to start."
- **Multiple projects, none specified**: List all projects with their stages and ask user to specify `--project NAME`.
- **No audit log** (for `--audit`): "No audit log found. Commands like `/fda:review`, `/fda:pathway`, `/fda:safety` will populate it."
- **No projects found** (for `--portfolio`): "No projects found in {projects_dir}. Use /fda:extract to create your first project."
