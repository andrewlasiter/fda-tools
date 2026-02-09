---
description: Cross-project portfolio dashboard — summarize all FDA projects, shared predicates, common guidance, and submission timeline
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: "[--output FILE] [--format table|detailed]"
---

# FDA Device Portfolio Manager

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

---

You are generating a cross-project portfolio view of all FDA 510(k) projects.

## Parse Arguments

- `--output FILE` — Write portfolio report to file
- `--format table|detailed` — Output format (default: table)
- `--filter product-code|status|date` — Filter projects
- `--set-target PROJECT DATE` — Set target submission date for a project (YYYY-MM-DD format)

## Step 1: Discover All Projects

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

projects = []
for qpath in glob.glob(os.path.join(projects_dir, '*/query.json')):
    pdir = os.path.dirname(qpath)
    pname = os.path.basename(pdir)
    try:
        with open(qpath) as f:
            query = json.load(f)
    except:
        query = {}

    # Inventory project data
    has_review = os.path.exists(os.path.join(pdir, 'review.json'))
    has_guidance = os.path.isdir(os.path.join(pdir, 'guidance_cache'))
    has_presub = os.path.exists(os.path.join(pdir, 'presub_plan.md'))
    has_outline = os.path.exists(os.path.join(pdir, 'submission_outline.md'))
    has_se = os.path.exists(os.path.join(pdir, 'se_comparison.md'))
    has_estar = os.path.isdir(os.path.join(pdir, 'estar'))

    # Count extraction data
    output_csv = os.path.join(pdir, 'output.csv')
    extraction_count = 0
    if os.path.exists(output_csv):
        with open(output_csv) as f:
            extraction_count = sum(1 for _ in f) - 1  # minus header

    # Get accepted predicates
    accepted_predicates = []
    if has_review:
        with open(os.path.join(pdir, 'review.json')) as f:
            review = json.load(f)
        accepted_predicates = [k for k, v in review.get('predicates', {}).items() if v.get('decision') == 'accepted']

    product_codes = query.get('stage1', {}).get('product_codes', [])
    created = query.get('created', 'Unknown')

    completeness = sum([
        bool(extraction_count > 0),
        has_review,
        has_guidance,
        has_presub,
        has_outline,
        has_se
    ])

    print(f"PROJECT:{pname}|codes={','.join(product_codes)}|created={created}|extractions={extraction_count}|predicates={len(accepted_predicates)}|completeness={completeness}/6|review={'Y' if has_review else 'N'}|guidance={'Y' if has_guidance else 'N'}|presub={'Y' if has_presub else 'N'}|outline={'Y' if has_outline else 'N'}|se={'Y' if has_se else 'N'}|estar={'Y' if has_estar else 'N'}")

    # Output accepted predicate K-numbers for overlap analysis
    for kn in accepted_predicates:
        print(f"PREDICATE:{pname}|{kn}")
PYEOF
```

## Step 2: Analyze Cross-Project Data

### Predicate Overlap

Identify predicates shared across multiple projects:

```
Cross-Project Predicate Overlap:
  K241335 — Used in projects: OVE_2026, MAX_2026 (shared predicate)
  K234567 — Used in projects: OVE_2026 only
```

### Shared Guidance

Check if multiple projects reference the same guidance documents (from guidance_cache).

### Common Standards

Identify standards referenced across multiple projects.

## Step 2.5: Submission Timeline Planning

For each project, estimate milestone dates based on completeness and typical FDA timelines:

```bash
python3 << 'PYEOF'
import json, os, re, glob
from datetime import datetime, timedelta

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
        continue

    created = query.get('created', '')
    has_review = os.path.exists(os.path.join(pdir, 'review.json'))
    has_guidance = os.path.isdir(os.path.join(pdir, 'guidance_cache'))
    has_presub = os.path.exists(os.path.join(pdir, 'presub_plan.md'))
    has_outline = os.path.exists(os.path.join(pdir, 'submission_outline.md'))
    has_se = os.path.exists(os.path.join(pdir, 'se_comparison.md'))
    has_estar = os.path.isdir(os.path.join(pdir, 'estar'))
    draft_count = len(glob.glob(os.path.join(pdir, 'draft_*.md')))

    # Determine current stage
    if has_estar:
        stage = "Assembly"
    elif draft_count >= 6:
        stage = "Drafting"
    elif has_se and has_guidance:
        stage = "Testing"
    elif has_review:
        stage = "Review"
    elif has_guidance:
        stage = "Guidance"
    else:
        stage = "Extraction"

    # Check for user-defined target date
    target_date = None
    timeline_path = os.path.join(pdir, 'timeline.json')
    if os.path.exists(timeline_path):
        try:
            with open(timeline_path) as f:
                tl = json.load(f)
            target_date = tl.get('target_submission_date', '')
        except:
            pass

    print(f"TIMELINE:{pname}|stage={stage}|drafts={draft_count}|target={target_date or 'not set'}|created={created}")
PYEOF
```

### Gantt-Style Timeline View

Generate a text-based timeline showing each project's progress and estimated milestones:

```
SUBMISSION TIMELINE
────────────────────────────────────────

  Typical 510(k) Milestones (weeks from start):
  Extract → Review → Guidance → Testing → Drafting → Assembly → Submit → FDA Review
  [0-2]     [2-4]    [4-6]      [6-14]    [14-20]    [20-22]    [22]     [22-34]

  {For each project:}
  {name} ({product_code})
  ├─ Extraction     [████████] Complete
  ├─ Review         [████████] Complete
  ├─ Guidance       [████░░░░] In progress
  ├─ Testing        [░░░░░░░░] Not started
  ├─ Drafting       [░░░░░░░░] Not started
  ├─ Assembly       [░░░░░░░░] Not started
  └─ Target submit: {date or "Not set — use /fda:portfolio --set-target PROJECT DATE"}

  Timeline:
  |--Extract--|--Review--|--Guidance--|----Testing----|---Drafting---|--Assembly--|
  0wk        2wk       4wk         6wk           14wk           20wk        22wk
                              ▲ YOU ARE HERE

FDA REVIEW TIMELINE REFERENCE
────────────────────────────────────────
  RTA screening:    15 FDA days from receipt
  Standard review:  90 FDA days (Traditional 510(k))
  Special 510(k):   30 FDA days
  De Novo:          150 FDA days (statutory; often longer)
  AI requests:      Add 90-180 days (review clock stops)
```

### Set Target Submission Date

If `--set-target PROJECT DATE` is specified:

1. Write `{projects_dir}/{PROJECT}/timeline.json` with:
   ```json
   {
     "target_submission_date": "YYYY-MM-DD",
     "set_date": "YYYY-MM-DD",
     "milestones": {}
   }
   ```
2. Report: `"Target submission date set for {PROJECT}: {DATE}"`

## Step 3: Generate Portfolio Report

```
  FDA Device Portfolio Dashboard
  All Projects Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Projects: {N} total | v5.16.0

PROJECT SUMMARY
────────────────────────────────────────

  | Project | Product Code | Extractions | Predicates | Stage | Completeness |
  |---------|-------------|------------|-----------|-------|-------------|
  | {name} | {codes} | {count} | {count} | {stage} | {N}/6 ██████░░░░░░░░░░░░░░ |
  | {name} | {codes} | {count} | {count} | {stage} | {N}/6 ████░░░░░░░░░░░░░░░░ |

CROSS-PROJECT INTELLIGENCE
────────────────────────────────────────

  Shared Predicates: {count} predicates used in 2+ projects
  Common Standards:  {list}
  Common Guidance:   {list}

PORTFOLIO STATUS
────────────────────────────────────────

  Ready for submission  {count}  ████████████████████
  In progress           {count}  ████████████░░░░░░░░
  Early stage           {count}  ████░░░░░░░░░░░░░░░░

SUBMISSION TIMELINE
────────────────────────────────────────

  | Project | Stage | Target Date | Days Remaining |
  |---------|-------|-------------|----------------|
  | {name} | {stage} | {date or "Not set"} | {N or "—"} |

  {Gantt-style bars per project — see Step 2.5}

NEXT STEPS
────────────────────────────────────────

  1. {project-specific recommendations}
  2. Run consistency checks — `/fda:consistency --project NAME`
  3. Check for new clearances — `/fda:monitor --check`

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Error Handling

- **No projects found**: "No projects found in {projects_dir}. Use /fda:extract to create your first project."
- **Single project**: Still generate report, note "Portfolio contains 1 project."
