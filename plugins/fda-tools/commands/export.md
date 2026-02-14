---
description: Export project data as eSTAR-compatible XML or zip package — validates completeness and generates readiness report
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: "--project NAME [--format xml|zip] [--template nIVD|IVD|PreSTAR] [--validate]"
---

# FDA eSTAR Export

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

You are exporting project data into an eSTAR-compatible format for submission preparation. This is the final step in the drafting pipeline — it validates completeness, packages section files, and generates eSTAR XML for import into the official FDA template.

> **Note:** This generates data files for import into the official eSTAR template. It does NOT generate a finished eSTAR PDF. The user must import the XML into Adobe Acrobat and add attachments manually.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--project NAME` (required) — Project to export
- `--format xml|zip` (default: xml) — Export format:
  - `xml`: Generate eSTAR-compatible XML for Adobe Acrobat import
  - `zip`: Package all section files + XML in eSTAR naming convention
- `--template nIVD|IVD|PreSTAR` (default: nIVD) — eSTAR template type
- `--validate` — Run completeness validation before export
- `--output FILE` — Output file path (default: project_dir/estar_export_{template}.{xml|zip})
- `--attach FILE [SECTION]` — Include an attachment file in the ZIP package. SECTION is the 2-digit section number. Can be specified multiple times. Also includes any files in `attachments.json`.

## Step 1: Inventory Project Data

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

# Check all possible data sources
sources = {
    "import_data.json": "eSTAR import data",
    "review.json": "Predicate review",
    "query.json": "Project metadata",
    "se_comparison.md": "SE comparison table",
    "test_plan.md": "Testing plan",
    "presub_plan.md": "Pre-Sub plan",
    "submission_outline.md": "Submission outline",
    "literature.md": "Literature review",
    "safety_report.md": "Safety analysis",
    "consistency_report.md": "Consistency report",
}

drafts_found = []
for fname in os.listdir(pdir) if os.path.isdir(pdir) else []:
    if fname.startswith('draft_') and fname.endswith('.md'):
        drafts_found.append(fname)

# Check estar/ directory
estar_dir = os.path.join(pdir, 'estar')
estar_sections = 0
if os.path.isdir(estar_dir):
    for d in os.listdir(estar_dir):
        if os.path.isdir(os.path.join(estar_dir, d)):
            estar_sections += 1

print(f"PROJECT_DIR:{pdir}")
for fname, desc in sources.items():
    fpath = os.path.join(pdir, fname)
    if os.path.exists(fpath):
        print(f"FOUND:{fname}|{desc}|{os.path.getsize(fpath)}")
    else:
        print(f"MISSING:{fname}|{desc}")

print(f"DRAFTS:{len(drafts_found)}|{','.join(sorted(drafts_found))}")
print(f"ESTAR_SECTIONS:{estar_sections}")
PYEOF
```

## Step 2: Validate Completeness (if --validate or always)

Run pre-export validation checks:

### Mandatory Sections Check
These sections MUST have content (DRAFT or READY status in eSTAR) for a valid 510(k):
1. Cover Letter (01)
2. Cover Sheet / FDA 3514 (02) — Template acceptable
3. 510(k) Summary or Statement (03)
4. Truthful & Accuracy Statement (04) — Template acceptable
5. Device Description (06)
6. SE Comparison (07)
7. Indications for Use (IFU/3881)

### Content Quality Checks
- No `[CITATION NEEDED]` in critical sections (SE discussion, device description)
- No orphan `[TODO:]` in auto-populated fields (fields that should have been filled from data)
- Product code consistent across all files (run consistency check 1)
- Predicate K-numbers consistent across all files (run consistency check 2)

### Report Validation Results

```
EXPORT VALIDATION
────────────────────────────────────────

  | Check                    | Status | Details          |
  |--------------------------|--------|------------------|
  | Mandatory sections       | {✓/✗}  | {N}/7 present    |
  | [CITATION NEEDED] scan   | {✓/⚠}  | {N} found        |
  | [TODO:] scan             | ○      | {N} remaining    |
  | Product code consistency | {✓/✗}  | {details}        |
  | Predicate consistency    | {✓/✗}  | {details}        |
```

If any mandatory section is missing, warn but still allow export (user may be doing partial export).

## Step 3: Generate Export

### Format: XML (default)

Call the estar_xml.py generate command:

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/estar_xml.py" generate --project "PROJECT_NAME" --template "TEMPLATE"
```

This reads all project data and produces an XFA-compatible XML file.

### Format: ZIP

Package all relevant files in eSTAR naming convention:

```bash
python3 << 'PYEOF'
import json, os, re, shutil, zipfile
from datetime import datetime

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m: projects_dir = os.path.expanduser(m.group(1).strip())

project = "PROJECT"  # Replace
pdir = os.path.join(projects_dir, project)

# eSTAR section mapping for filenames
section_map = {
    "draft_cover-letter.md": "01_CoverLetter/cover_letter.md",
    "cover_sheet.md": "02_CoverSheet/cover_sheet.md",
    "draft_510k-summary.md": "03_510kSummary/510k_summary.md",
    "draft_truthful-accuracy.md": "04_TruthfulAccuracy/truthful_accuracy.md",
    "draft_financial-certification.md": "05_FinancialCert/financial_certification.md",
    "draft_device-description.md": "06_DeviceDescription/device_description.md",
    "draft_se-discussion.md": "07_SEComparison/se_discussion.md",
    "se_comparison.md": "07_SEComparison/se_comparison_table.md",
    "draft_labeling.md": "09_Labeling/labeling.md",
    "draft_sterilization.md": "10_Sterilization/sterilization.md",
    "draft_shelf-life.md": "11_ShelfLife/shelf_life.md",
    "draft_biocompatibility.md": "12_Biocompatibility/biocompatibility.md",
    "draft_software.md": "13_Software/software.md",
    "draft_emc-electrical.md": "14_EMC/emc_electrical.md",
    "draft_performance-summary.md": "15_PerformanceTesting/performance_testing.md",
    "draft_clinical.md": "16_Clinical/clinical_evidence.md",
    "draft_predicate-justification.md": "07_SEComparison/predicate_justification.md",
    "draft_testing-rationale.md": "15_PerformanceTesting/testing_rationale.md",
    "draft_doc.md": "08_Standards/declaration_of_conformity.md",
    "draft_human-factors.md": "17_HumanFactors/human_factors.md",
    "test_plan.md": "15_PerformanceTesting/test_plan.md",
    "literature.md": "16_Clinical/literature_review.md",
}

zip_name = f"eSTAR_package_{project}_{datetime.utcnow().strftime('%Y%m%d')}.zip"
zip_path = os.path.join(pdir, zip_name)

included = 0
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    # Add mapped files
    for src_name, dst_name in section_map.items():
        src_path = os.path.join(pdir, src_name)
        if os.path.exists(src_path):
            zf.write(src_path, dst_name)
            included += 1

    # Add eSTAR index
    index_path = os.path.join(pdir, 'eSTAR_index.md')
    if os.path.exists(index_path):
        zf.write(index_path, 'eSTAR_index.md')
        included += 1

    # Add XML data file
    xml_path = os.path.join(pdir, f'estar_export_nIVD.xml')
    if os.path.exists(xml_path):
        zf.write(xml_path, 'estar_data.xml')
        included += 1

    # Add attachments from attachments.json
    att_path = os.path.join(pdir, 'attachments.json')
    if os.path.exists(att_path):
        with open(att_path) as af:
            att_data = json.load(af)
        for att in att_data.get('attachments', []):
            orig = att.get('original_path', '')
            estar = att.get('estar_path', '')
            if os.path.exists(orig) and estar:
                zf.write(orig, estar)
                included += 1

    # Add any files from attachments/ directory
    att_dir = os.path.join(pdir, 'attachments')
    if os.path.isdir(att_dir):
        for fname in os.listdir(att_dir):
            fpath = os.path.join(att_dir, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, f'18_Other/{fname}')
                included += 1

    # Add readiness report
    readme = f"# eSTAR Export Package\\n\\nProject: {project}\\nGenerated: {datetime.utcnow().isoformat()}Z\\nFiles: {included}\\n\\nImport estar_data.xml into the official eSTAR template using Adobe Acrobat.\\nReview all attachments for completeness.\\n"
    zf.writestr('README.md', readme)

print(f"ZIP_CREATED:{zip_path}|{included} files")
PYEOF
```

## Step 4: Generate Readiness Report

Write `eSTAR_readiness.md` to the project directory:

```markdown
# eSTAR Readiness Report
## {device_name} — Product Code {product_code}

**Generated:** {date}
**Project:** {project_name}
**Template:** {template_type}

---

## Section Readiness

| # | Section | Status | Source | Notes |
|---|---------|--------|--------|-------|
| 01 | Cover Letter | {Green/Yellow/Red} | {source} | {notes} |
| 02 | Cover Sheet (3514) | Yellow | Template | Complete in eSTAR |
| 03 | 510(k) Summary | {status} | {source} | {notes} |
| 04 | Truthful & Accuracy | Yellow | Template | Needs signature |
| 05 | Financial Cert | Yellow | Template | Complete FDA form |
| 06 | Device Description | {status} | {source} | {notes} |
| 07 | SE Comparison | {status} | {source} | {notes} |
| 08 | Standards | {status} | {source} | {notes} |
| 09 | Labeling | {status} | {source} | {notes} |
| 10 | Sterilization | {status} | {source} | {notes} |
| 11 | Shelf Life | {status} | {source} | {notes} |
| 12 | Biocompatibility | {status} | {source} | {notes} |
| 13 | Software | {status} | {source} | {notes} |
| 14 | EMC/Electrical | {status} | {source} | {notes} |
| 15 | Performance | {status} | {source} | {notes} |
| 16 | Clinical | {status} | {source} | {notes} |

**Status key:** Green = READY (user verified), Yellow = DRAFT (AI-generated, needs review), Red = MISSING

**Readiness scoring:** Use the canonical SRI formula from `references/readiness-score-formula.md` (0-100 scale with 5 tiers: Ready/Nearly Ready/Significant Gaps/Not Ready/Early Stage).

## Remaining Work

{List of [TODO:] items across all draft files}

## Export Files

- `estar_export_{template}.xml` — Import into eSTAR template
- `eSTAR_readiness.md` — This report
{If zip:} - `eSTAR_package_{project}_{date}.zip` — Complete package

> **Disclaimer:** This export is AI-generated from public FDA data.
> Verify independently. Not regulatory advice.
```

## Step 5: Report

Present using standard FDA Professional CLI format:

```
  FDA eSTAR Export Report
  {product_code} — {device_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Project: {name} | v5.22.0

EXPORT SUMMARY
────────────────────────────────────────

  Format: {XML / ZIP}
  Template: {nIVD v6 / IVD v6 / PreSTAR v2}
  Output: {file_path}

  | Status  | Sections | Description                     |
  |---------|----------|---------------------------------|
  | Green   | {N}      | Ready (user verified)           |
  | Yellow  | {N}      | Draft (needs professional review)|
  | Red     | {N}      | Missing (no content)            |

  Completeness: {N}/16 sections with content
  [TODO:] items remaining: {N}

NEXT STEPS
────────────────────────────────────────

  1. Open official eSTAR template in Adobe Acrobat
  2. Import estar_export_{template}.xml via Form > Import Data
  3. Review all populated fields for accuracy
  4. Add attachments (test reports, images, declarations)
  5. Complete remaining [TODO:] sections
  6. Have regulatory team perform final review
  7. Run /fda:pre-check to simulate FDA review
  8. Submit via CDRH Portal (see below)

SUBMIT TO FDA
────────────────────────────────────────

  Portal: https://ccp.fda.gov/prweb/PRAuth/app/default/extsso

  Before uploading:
  - Verify total package is under 4 GB (1 GB per attachment)
  - Ensure no PDF passwords are set on any document
  - Confirm official correspondent email is correct
  - Run eSTAR built-in validation (no red X indicators)

  After submitting:
  - Save your confirmation number
  - Monitor the portal dashboard for status updates

  For full portal details, see references/cdrh-portal.md

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Error Handling

- **No project**: "ERROR: --project NAME is required."
- **Empty project**: "WARNING: Project has no draft data. Run `/fda:draft` first to generate section content, or `/fda:import` to import existing eSTAR data."
- **Missing estar_xml.py dependencies**: Provide install instructions for pikepdf, beautifulsoup4, lxml
- **No mandatory sections**: "WARNING: {N}/7 mandatory sections missing. Export will be incomplete. Missing: {list}"
- **eCTD format requested**: "NOTE: eCTD format is NOT required for 510(k) submissions. The required format is eSTAR (electronic Submission Template And Resource). This export generates eSTAR XML. For PMA or IDE submissions requiring eCTD, consult FDA ESG guidance at https://www.fda.gov/industry/electronic-submissions-gateway. See `references/ectd-overview.md` for details."
