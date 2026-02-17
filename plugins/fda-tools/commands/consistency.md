---
description: Cross-validate all project files for internal consistency — device description, intended use, predicate list, product code alignment across all submission components
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: "--project NAME [--fix] [--output FILE]"
---

# FDA 510(k) Cross-Document Consistency Validator

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

settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
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

**4a. Cross-document IFU match:**
**PASS**: Exact same IFU text everywhere.
**WARN**: Minor formatting differences.
**FAIL**: Different IFU text in different documents. List each variant.

**4b. Form 3881 IFU match:**
If `drafts/draft_form-3881.md` exists, extract the IFU text from it and compare against:
- `drafts/draft_labeling.md` IFU text
- `drafts/draft_510k-summary.md` IFU text
- `device_profile.json` `intended_use` field
**PASS**: Form 3881 IFU matches all other documents exactly.
**FAIL**: Form 3881 IFU differs from other submission documents. This will trigger an AI request from FDA.

**4c. No competitor brand names in IFU:**
Cross-reference with Check 14 — scan the IFU text specifically for competitor company names that appear as the subject device manufacturer (not as predicate references).
**PASS**: IFU text does not contain competitor brand names as subject device manufacturer.
**FAIL**: IFU text contains competitor brand name '{company}' — likely peer-mode data leakage. This is a subset of Check 14 but specifically flagged for IFU because FDA Form 3881 inconsistency is a common RTA trigger.

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
- `draft_form-3881.md` → `03_510kSummary/`
- `draft_reprocessing.md` → `18_Other/reprocessing/`
- `draft_combination-product.md` → `18_Other/`

**PASS**: All draft files have corresponding section_map entries.
**WARN**: Unmapped draft files found (may be supplementary content).
**FAIL**: Required draft file has no section_map entry (would be excluded from export).

Flag any draft file that has no corresponding section_map entry.

### Check 12: Technical Specification Cross-Reference (HIGH)

Parse specific technical values from multiple project files and verify they are consistent:

**Files to cross-reference:**
- `drafts/draft_device-description.md` → materials, dimensions, gauges, configurations
- `se_comparison.md` → subject device column values (dimensions, materials, sterilization method)
- `device_profile.json` → any stated specs (if exists)
- `import_data.json` → imported device data (if exists)

**Extraction patterns (apply to each file):**
```python
import re

def extract_specs(text):
    specs = {}
    # Gauge values: "23G", "25 gauge", etc.
    gauges = set(re.findall(r'\b(\d+)\s*[Gg](?:auge)?\b', text))
    if gauges:
        specs['gauges'] = sorted(gauges)

    # Dimensions: "4.5 mm", "120 cm", "7 Fr", etc.
    dims = re.findall(r'(\d+(?:\.\d+)?)\s*(mm|cm|Fr|french|gauge|inches?|in)\b', text, re.I)
    if dims:
        specs['dimensions'] = [(v, u.lower()) for v, u in dims]

    # Materials: known material names
    material_patterns = [
        'PTFE', 'FEP', 'PEEK', 'stainless steel', 'titanium', 'nitinol',
        'silicone', 'polyurethane', 'polycarbonate', 'polyethylene',
        'nylon', 'polypropylene', 'cobalt.?chromium', 'tungsten',
        'nickel', 'latex', 'PVC', 'HDPE', 'UHMWPE', 'ceramic',
        'hydroxyapatite', 'acrylic', 'epoxy',
    ]
    found_materials = set()
    for mat in material_patterns:
        if re.search(mat, text, re.I):
            found_materials.add(mat.upper() if len(mat) <= 4 else mat.title())
    if found_materials:
        specs['materials'] = sorted(found_materials)

    # Sterilization method
    steril_match = re.search(r'(ethylene oxide|EO|E\.?O\.?|gamma|electron beam|e-beam|radiation|steam|autoclave)\s*steriliz', text, re.I)
    if steril_match:
        specs['sterilization'] = steril_match.group(1).strip()

    # Shelf life duration
    shelf_match = re.search(r'(?:shelf\s*life|expir\w+|dating)[^.]*?(\d+)\s*(year|month|day)s?', text, re.I)
    if shelf_match:
        specs['shelf_life'] = f"{shelf_match.group(1)} {shelf_match.group(2)}(s)"

    # Compatible equipment model numbers
    equip_match = re.findall(r'(?:compatible with|for use with|requires|generator|console|controller)[^.]*?([A-Z][A-Z0-9]{2,}[-\s]?[A-Z0-9]+)', text, re.I)
    if equip_match:
        specs['compatible_equipment'] = sorted(set(equip_match))

    # Sterilization cycle parameters (temperature, time, pressure)
    cycle_match = re.search(r'(\d+)\s*°?\s*[CF]\s*(?:for|×|x)\s*(\d+)\s*min', text, re.I)
    if cycle_match:
        specs['sterilization_cycle'] = f"{cycle_match.group(1)}°/{cycle_match.group(2)} min"

    # Steam sterilization specific: temperature and exposure time
    steam_match = re.search(r'(?:steam|autoclave)[^.]*?(\d{3})\s*°?\s*[CF][^.]*?(\d+)\s*min', text, re.I)
    if steam_match:
        specs['steam_cycle'] = f"{steam_match.group(1)}°/{steam_match.group(2)} min"

    return specs
```

**Cross-reference logic:**
1. Extract specs from each file independently
2. For each spec type (gauges, materials, sterilization), compare across all files that mention it
3. Flag contradictions — e.g., device description says "23G/25G" but SE comparison says "19G/22G/25G"

**PASS**: Same specs appear consistently across all files that mention them.
**WARN**: Minor formatting differences (e.g., "EO" vs "ethylene oxide") — semantically equivalent.
**FAIL**: Contradictory values found. Report each contradiction:
  - "Gauge mismatch: draft_device-description.md says {X}, se_comparison.md says {Y}"
  - "Material mismatch: draft_device-description.md lists {X}, se_comparison.md lists {Y}"
  - "Sterilization mismatch: draft_sterilization.md says {X}, se_comparison.md says {Y}"

### Check 13: Standards ↔ Declaration of Conformity Alignment (MEDIUM)

Compare standards listed in `standards_lookup.json` (from `/fda:standards`) against the Declaration of Conformity in `drafts/draft_doc.md`.

**Steps:**
1. Load `$PROJECTS_DIR/$PROJECT_NAME/standards_lookup.json` — extract all standard numbers (ISO, IEC, ASTM, ANSI references)
2. Load `$PROJECTS_DIR/$PROJECT_NAME/drafts/draft_doc.md` — extract all standard numbers cited in the DoC table
3. Compare: every required standard from the lookup should appear in the DoC

```python
import re

def extract_standards(text):
    """Extract standard references like ISO 10993-1, IEC 60601-1-2, ASTM F2129"""
    patterns = [
        r'ISO\s*\d{4,5}(?:-\d+)*(?::\d{4})?',
        r'IEC\s*\d{4,5}(?:-\d+)*(?::\d{4})?',
        r'ASTM\s*[A-Z]\d+(?:-\d+)*(?::\d{4})?',
        r'ANSI\s*[A-Z]?\d+(?:\.\d+)*(?::\d{4})?',
        r'EN\s*\d{4,5}(?:-\d+)*(?::\d{4})?',
        r'21\s*CFR\s*\d+(?:\.\d+)*',
    ]
    found = set()
    for p in patterns:
        for m in re.finditer(p, text, re.I):
            # Normalize: strip year suffix for comparison
            std = re.sub(r':\d{4}$', '', m.group(0))
            std = re.sub(r'\s+', ' ', std)
            found.add(std.upper())
    return found
```

**PASS**: Every standard from standards_lookup.json appears in the DoC (draft_doc.md).
**WARN**: DoC lists standards not in standards_lookup.json (may be intentionally added — acceptable).
**FAIL**: Standards in lookup missing from DoC — list which ones. Example: "ISO 11135 (EO sterilization) is in standards_lookup.json but not declared in draft_doc.md"

If `standards_lookup.json` does not exist, report: `"○ Not checked — no standards_lookup.json found. Run /fda:standards to generate."`
If `drafts/draft_doc.md` does not exist, report: `"○ Not checked — no draft_doc.md found. Run /fda:draft doc to generate."`

### Check 14: Brand Name / Applicant Consistency (CRITICAL)

Scan ALL draft files + device_profile.json fields for competitor brand names that don't match the applicant. This catches peer-mode data leakage where predicate device data was incorrectly attributed to the subject device.

**Steps:**
1. Extract `applicant` (or `applicant_name`, `company_name`) from `device_profile.json`, `import_data.json`, or `review.json`
2. Define known company names list: `KARL STORZ`, `Boston Scientific`, `Medtronic`, `Abbott`, `Johnson & Johnson`, `Ethicon`, `Stryker`, `Zimmer Biomet`, `Smith & Nephew`, `B. Braun`, `Cook Medical`, `Edwards Lifesciences`, `Becton Dickinson`, `BD`, `Baxter`, `Philips`, `GE Healthcare`, `Siemens Healthineers`, `Olympus`, `Hologic`, `Intuitive Surgical`, `Teleflex`, `ConvaTec`, `Coloplast`, `3M Health Care`, `Cardinal Health`, `Danaher`, `Integra LifeSciences`, `NuVasive`, `Globus Medical`, `DePuy Synthes`
3. For each draft file and device_profile field (intended_use, device_description, extracted_sections):
   - Search for each known company name (case-insensitive)
   - If found AND it does NOT match the `applicant` field:
     - Check context: is it a predicate reference (acceptable) or subject device attribution (FAIL)?
     - Predicate references typically appear as: "compared to {company}'s {K-number}", "predicate manufactured by {company}", "reference device from {company}"
     - Subject device attributions appear as: "{company} {device_name}", "manufactured by {company}" (without predicate context), "{company}" in IFU text as the applicant

**PASS**: No competitor brand names appear as subject device manufacturer across any file.
**FAIL**: Competitor brand name `{company}` found as subject device attribution in `{file}`. This is likely peer-mode data leakage. Quote the specific text and file location.

### Check 15: Shelf Life Claim vs Evidence (CRITICAL)

Extract shelf life claims from project data and verify supporting evidence exists.

**Steps:**
1. Search for shelf life claims in:
   - `se_comparison.md` — "Shelf Life" row, subject device column
   - `device_profile.json` — any shelf_life field
   - `drafts/draft_labeling.md` — expiration/shelf life mentions
   - `import_data.json` — shelf life fields
2. If a shelf life claim is found (e.g., "3 years", "24 months", "5 year shelf life"):
   - Check for `drafts/draft_shelf-life.md` — exists AND has non-TODO content (not >80% [TODO] placeholders)
   - Check for `calculations/shelf_life_calc.json` or `calculations/shelf_life_*.json` — exists with AAF data
   - Check for ASTM F1980 reference in any draft file
3. Score evidence:

**PASS**: Shelf life claim found AND (draft_shelf-life.md with real content OR calculations with AAF data).
**WARN**: Shelf life claim found AND draft_shelf-life.md exists but is mostly [TODO] placeholders.
**FAIL**: Shelf life claim found but NO supporting evidence (no draft, no calculations, no ASTM F1980 reference). Report: "Shelf life of '{claim}' claimed in {source_file} but no supporting evidence found. Run: /fda:draft shelf-life --project NAME and /fda:calc shelf-life --project NAME"

If no shelf life claim found in any file, report: `"○ Not checked — no shelf life claim detected in project data."`

### Check 16: Reusable Device Reprocessing Consistency (HIGH)

If the device is marked as reusable, verify reprocessing documentation exists and is consistent.

**Steps:**
1. Detect reusable device: scan device_profile.json, se_comparison.md, draft_device-description.md for "reusable", "reprocessing", "multi-use", "non-disposable", "autoclave", "endoscope", "instrument tray"
2. If reusable device detected:
   - Check for `drafts/draft_reprocessing.md` — reprocessing validation documentation
   - Check for reprocessing instructions in `drafts/draft_labeling.md` — cleaning/disinfection/sterilization IFU
   - Check for AAMI TIR30, AAMI ST91, or ISO 17664 references in any draft
3. Cross-validate:
   - Reprocessing method in draft_reprocessing.md should match sterilization section (if steam between uses)
   - Maximum reprocessing cycles should be consistent between device description and reprocessing draft
   - Cleaning agents in reprocessing section should appear in labeling IFU

**PASS**: Reusable device with reprocessing docs AND labeling includes reprocessing IFU.
**WARN**: Reusable device with reprocessing docs but missing from labeling IFU.
**FAIL**: Reusable device detected but no reprocessing documentation at all. Report: "Device appears to be reusable but no reprocessing validation found. Run: /fda:draft reprocessing --project NAME"

If device is not reusable, report: `"○ Not checked — device not identified as reusable."`

### Check 17: Compatible Equipment Consistency (MEDIUM)

If compatible equipment is mentioned in the device description, verify consistent mentions across submission documents.

**Steps:**
1. Scan `drafts/draft_device-description.md` and `device_profile.json` for equipment references: "generator", "console", "controller", "power supply", "light source", "camera head", "processor", "power unit", "energy source"
2. Extract equipment names/models if found
3. If equipment detected, check for consistent references in:
   - `drafts/draft_labeling.md` — equipment should be listed in IFU compatibility section
   - `drafts/draft_performance-summary.md` or `test_plan.md` — testing should reference the compatible equipment
   - `drafts/draft_emc-electrical.md` — EMC testing should include equipment combinations
   - `se_comparison.md` — compatible equipment row (if present)

**PASS**: Equipment mentioned in description AND referenced in labeling AND testing.
**WARN**: Equipment mentioned in description but missing from labeling OR testing. Report which documents are missing the reference.
**FAIL**: Equipment mentioned as required for operation but completely absent from labeling and testing. Report: "Compatible equipment '{equipment}' in device description but not addressed in labeling or testing documentation."

If no compatible equipment detected, report: `"○ Not checked — no compatible equipment references found in device description."`

## Step 4: Generate Report

Present the report using the standard FDA Professional CLI format (see `references/output-formatting.md`):

```
  FDA Consistency Validation Report
  Project: {project_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Files: {count} | v5.22.0

RESULTS SUMMARY
────────────────────────────────────────

  | #  | Check                  | Status | Details      |
  |----|------------------------|--------|--------------|
  | 1  | Product Code           | ✓      | {details}    |
  | 2  | Predicate List         | ✗      | {details}    |
  | 3  | Device Description     | ⚠      | {details}    |
  | 4  | Intended Use (4a/4b/4c)| ✓      | {details}    |
  | 5  | Pathway                | ✓      | {details}    |
  | 6  | Standards Coverage     | ⚠      | {details}    |
  | 7  | Dates/Freshness        | ○      | {details}    |
  | 8  | Placeholder Scan       | ✓      | {details}    |
  | 9  | Cross-Section Draft    | ✓      | {details}    |
  | 10 | eSTAR Import Align     | ○      | {details}    |
  | 11 | Section Map Align      | ✓      | {details}    |
  | 12 | Spec Cross-Ref         | ✗      | {details}    |
  | 13 | Standards ↔ DoC        | ⚠      | {details}    |
  | 14 | Brand Name / Applicant | ✗      | {details}    |
  | 15 | Shelf Life vs Evidence | ⚠      | {details}    |
  | 16 | Reprocessing Consistency| ○     | {details}    |
  | 17 | Compatible Equipment   | ○      | {details}    |

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

For each of the 17 checks, log the result:

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
