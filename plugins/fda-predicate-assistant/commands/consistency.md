---
description: Cross-validate all project files for internal consistency — device description, intended use, predicate list, product code alignment across all submission components
allowed-tools: Bash, Read, Glob, Grep, Write
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

### Check 9: Cross-Section Draft Consistency (HIGH)
When multiple draft_*.md files exist, validate consistency across sections:

**IFU alignment**: The indications for use text in draft_labeling.md must match draft_510k-summary.md and draft_se-discussion.md.
**K-number references**: All draft files that mention predicate K-numbers must reference the same set of accepted predicates.
**Standard citations**: Standards referenced in draft_sterilization.md, draft_biocompatibility.md, draft_emc-electrical.md must appear in test_plan.md.
**Device description**: Core device description in draft_device-description.md must be semantically consistent with the description in draft_510k-summary.md and draft_cover-letter.md.

**PASS**: All cross-section references are consistent.
**WARN**: Minor wording differences in device description across sections.
**FAIL**: IFU text differs between labeling and 510k-summary sections.

### Check 10: eSTAR Import Data Alignment (MEDIUM)
If import_data.json exists, check that project files align with imported eSTAR data:

**PASS**: Product code, predicates, and IFU match import_data.json.
**WARN**: Project data has been modified since import (expected if user updated).
**FAIL**: Product code in import_data.json differs from project data with no documented change.

### Check 11: eSTAR Section Map Alignment (HIGH)
Verify that every draft file maps to a section in the export section_map. Expected mappings (must match `export.md` section_map):

- `draft_cover-letter.md` → `01_CoverLetter/`
- `cover_sheet.md` → `02_CoverSheet/`
- `draft_510k-summary.md` → `03_510kSummary/`
- `draft_truthful-accuracy.md` → `04_TruthfulAccuracy/`
- `draft_financial-certification.md` → `05_FinancialCert/`
- `draft_device-description.md` → `06_DeviceDescription/`
- `draft_se-discussion.md` → `07_SEComparison/`
- `draft_doc.md` → `08_Standards/`
- `draft_labeling.md` → `09_Labeling/`
- `draft_sterilization.md` → `10_Sterilization/`
- `draft_shelf-life.md` → `11_ShelfLife/`
- `draft_biocompatibility.md` → `12_Biocompatibility/`
- `draft_software.md` → `13_Software/`
- `draft_emc-electrical.md` → `14_EMC/`
- `draft_performance-summary.md` → `15_PerformanceTesting/`
- `draft_clinical.md` → `16_Clinical/`
- `draft_human-factors.md` → `17_HumanFactors/`

**PASS**: All draft files have corresponding section_map entries.
**WARN**: Unmapped draft files found (may be supplementary content).
**FAIL**: Required draft file has no section_map entry (would be excluded from export).

Flag any draft file that has no corresponding section_map entry.

## Step 4: Generate Report

Present the report using the standard FDA Professional CLI format (see `references/output-formatting.md`):

```
  FDA Consistency Validation Report
  Project: {project_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Files: {count} | v5.22.0

RESULTS SUMMARY
────────────────────────────────────────

  | #  | Check               | Status | Details      |
  |----|---------------------|--------|--------------|
  | 1  | Product Code        | ✓      | {details}    |
  | 2  | Predicate List      | ✗      | {details}    |
  | 3  | Device Description  | ⚠      | {details}    |
  | 4  | Intended Use        | ✓      | {details}    |
  | 5  | Pathway             | ✓      | {details}    |
  | 6  | Standards Coverage  | ⚠      | {details}    |
  | 7  | Dates/Freshness     | ○      | {details}    |
  | 8  | Placeholder Scan    | ✓      | {details}    |
  | 9  | Cross-Section Draft | ✓      | {details}    |
  | 10 | eSTAR Import Align  | ○      | {details}    |
  | 11 | Section Map Align   | ✓      | {details}    |

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

## Audit Logging

After all consistency checks are complete, log each result using `fda_audit_logger.py`:

### Log each check result

For each of the 11 checks, log the result:

```bash
# For passed checks:
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command consistency \
  --action check_passed \
  --subject "Check $CHECK_NUM: $CHECK_NAME" \
  --decision "pass" \
  --mode interactive \
  --decision-type auto \
  --rationale "$CHECK_DETAILS"

# For failed checks:
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command consistency \
  --action check_failed \
  --subject "Check $CHECK_NUM: $CHECK_NAME" \
  --decision "fail" \
  --mode interactive \
  --decision-type auto \
  --rationale "Expected: $EXPECTED. Found: $FOUND. Files: $FILE1 vs $FILE2" \
  --data-sources "$FILES_CHECKED"

# For warnings:
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command consistency \
  --action check_warned \
  --subject "Check $CHECK_NUM: $CHECK_NAME" \
  --decision "warn" \
  --mode interactive \
  --decision-type auto \
  --rationale "$WARNING_DETAILS"
```

## Error Handling

- **No project**: ERROR: "Project name required."
- **Empty project**: "Project '{name}' has no files to validate. Run /fda:pipeline first."
- **Single file only**: "Only 1 file found. Cross-document consistency requires multiple pipeline outputs."
