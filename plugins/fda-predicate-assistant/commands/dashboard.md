---
description: Project status dashboard — aggregates drafted sections, consistency results, readiness score, TODO counts, and contextual next steps
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: "--project NAME [--save]"
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

You are generating a comprehensive project status dashboard. This is distinct from `/fda:status` which checks raw data availability and API connectivity. The dashboard focuses on **project-level progress** — what's been drafted, what's consistent, and what's left to do.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--project NAME` (required) — Project to dashboard
- `--save` — Save dashboard report as `dashboard.md` in the project directory

If no `--project` specified, check if only one project exists and use that. If multiple exist, list them and ask the user to specify.

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

## Error Handling

- **Project not found**: "Project '{name}' not found in {projects_dir}. Run `/fda:status` to see available projects."
- **Empty project**: "Project '{name}' has no data yet. Run `/fda:extract both --project {name}` to start."
- **Multiple projects, none specified**: List all projects with their stages and ask user to specify `--project NAME`.
