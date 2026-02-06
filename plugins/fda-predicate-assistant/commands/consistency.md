---
description: Cross-validate all project files for internal consistency — device description, intended use, predicate list, product code alignment across all submission components
allowed-tools: Bash, Read, Glob, Grep
argument-hint: "--project NAME [--fix] [--output FILE]"
---

# FDA 510(k) Cross-Document Consistency Validator

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

You are cross-validating all project files for internal consistency. This catches contradictions between submission components before they become FDA review issues.

**KEY PRINCIPLE: FDA reviewers check for consistency across submission sections.** Mismatched device descriptions, different predicate lists, or contradictory product codes across documents are common deficiency letter triggers. Catch them early.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--project NAME` (required) — Project to validate
- `--fix` — Attempt to auto-fix minor inconsistencies (report-only by default)
- `--output FILE` — Write report to file (default: consistency_report.md in project folder)
- `--strict` — Treat warnings as failures (for CI/automated pipelines)

## Step 1: Inventory All Project Files

```bash
python3 << 'PYEOF'
import json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m: projects_dir = os.path.expanduser(m.group(1).strip())

project = "PROJECT"  # Replace
pdir = os.path.join(projects_dir, project)

files = {}
for fname in os.listdir(pdir):
    fpath = os.path.join(pdir, fname)
    if os.path.isfile(fpath):
        files[fname] = {"path": fpath, "size": os.path.getsize(fpath)}
        print(f"FILE:{fname}|{os.path.getsize(fpath)}")
    elif os.path.isdir(fpath):
        count = sum(1 for f in os.listdir(fpath) if os.path.isfile(os.path.join(fpath, f)))
        print(f"DIR:{fname}|{count} files")
PYEOF
```

## Step 2: Extract Key Facts from Each File

For each project file, extract the key facts that should be consistent:

### From query.json
- Product code(s)
- Year range
- Project name

### From review.json
- Accepted predicate K-numbers
- Product codes for each predicate
- Decision rationale

### From se_comparison.md
- Predicate K-numbers in table headers
- Product code mentioned
- Device description text
- Intended use text

### From presub_plan.md
- Product code
- Device description
- Intended use
- Predicate K-numbers
- Pathway (Traditional/Special/Abbreviated/De Novo)

### From submission_outline.md
- Product code
- Device description
- Intended use
- Predicate K-numbers
- Pathway
- Applicable sections

### From test_plan.md
- Product code
- Testing standards referenced

### From output.csv
- Product codes extracted
- Predicate K-numbers extracted

### From guidance_cache
- Product code
- Standards referenced

## Step 3: Run Consistency Checks

### Check 1: Product Code Consistency (CRITICAL)
Every file that mentions a product code should agree.

**PASS**: All files reference the same product code.
**FAIL**: Files reference different product codes. List each file and its product code.

### Check 2: Predicate List Consistency (CRITICAL)
Accepted predicates in review.json should appear in SE comparison and submission outline.

**PASS**: All accepted predicates appear in SE comparison headers.
**WARN**: SE comparison includes predicates not in review.json (may be intentional).
**FAIL**: Accepted predicates missing from SE comparison.

### Check 3: Device Description Consistency (HIGH)
Device description text should be semantically consistent across files.

**PASS**: Device descriptions are semantically equivalent.
**WARN**: Minor wording differences (acceptable if meaning is same).
**FAIL**: Contradictory device descriptions (e.g., different materials, mechanisms).

### Check 4: Intended Use Consistency (CRITICAL)
IFU text must be identical across all submission components.

**PASS**: Exact same IFU text everywhere.
**WARN**: Minor formatting differences.
**FAIL**: Different IFU text in different documents. List each variant.

### Check 5: Pathway Consistency (HIGH)
Submission pathway should be consistent.

**PASS**: Same pathway everywhere.
**FAIL**: Different pathways in different documents.

### Check 6: Standards Consistency (MEDIUM)
Standards referenced in guidance_cache should appear in test_plan and submission_outline.

**PASS**: All required standards have corresponding tests.
**WARN**: Optional standards not covered.
**FAIL**: Required standards with no test plan.

### Check 7: Dates and Freshness (LOW)
Check that all files were generated from the same pipeline run.

**PASS**: All files generated within same session.
**WARN**: Files generated days apart (data may have changed).
**FAIL**: Files from different months (likely stale data).

### Check 8: Placeholder Scan (HIGH)
No `[INSERT: ...]` placeholders should remain in final documents.

**PASS**: No `[INSERT:` found in any file.
**WARN**: `[TODO:` items remain (expected for company-specific data).
**FAIL**: `[INSERT:` placeholders found — these were supposed to be resolved.

## Step 4: Generate Report

Present the report using the standard FDA Professional CLI format (see `references/output-formatting.md`):

```
  FDA Consistency Validation Report
  Project: {project_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Files: {count} | v4.0.0

RESULTS SUMMARY
────────────────────────────────────────

  | Check              | Status | Details      |
  |--------------------|--------|--------------|
  | Product Code       | ✓      | {details}    |
  | Predicate List     | ✗      | {details}    |
  | Device Description | ⚠      | {details}    |
  | Intended Use       | ✓      | {details}    |
  | Pathway            | ✓      | {details}    |
  | Standards Coverage | ⚠      | {details}    |
  | Dates/Freshness    | ○      | {details}    |
  | Placeholder Scan   | ✓      | {details}    |

  Status: ✓ pass, ✗ fail, ⚠ warning, ○ not checked

FAILURES (MUST FIX)
────────────────────────────────────────

  {For each ✗:}
  **{Check Name}**
  Issue: {description}
  Found in: {file1} says X, {file2} says Y
  → {how to fix}

WARNINGS (REVIEW RECOMMENDED)
────────────────────────────────────────

  {For each ⚠:}
  **{Check Name}**
  Issue: {description}
  → {action}

VERIFIED CONSISTENT FACTS
────────────────────────────────────────

  Product Code: {CODE} (consistent across {N} files)
  Predicates:   {K-numbers} (consistent across {N} files)
  Pathway:      {pathway} (consistent across {N} files)
  IFU:          "{first 80 chars...}" (consistent across {N} files)

NEXT STEPS
────────────────────────────────────────

  1. Fix all ✗ failures before submission
  2. Review ⚠ warnings with regulatory team
  3. Re-run after fixes — `/fda:consistency --project NAME`

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Error Handling

- **No project**: ERROR: "Project name required."
- **Empty project**: "Project '{name}' has no files to validate. Run /fda:pipeline first."
- **Single file only**: "Only 1 file found. Cross-document consistency requires multiple pipeline outputs."
