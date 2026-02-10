---
description: Assemble an eSTAR-structured submission package from project data — creates directory structure, maps sections to available data, and tracks readiness
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: "--project NAME [--product-code CODE] [--pathway traditional|special|abbreviated|denovo]"
---

# FDA eSTAR Submission Assembly

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

You are assembling an eSTAR-structured submission package from all available project data.

**KEY PRINCIPLE: Map every piece of existing project data to the appropriate eSTAR section.** Create the directory structure, populate sections with available data, and generate a readiness index showing what's complete vs. what needs work.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--project NAME` (required) — Project to assemble from
- `--product-code CODE` — Product code (auto-detect from project if not specified)
- `--pathway traditional|special|abbreviated|denovo` — Submission pathway (default: traditional)
- `--output-dir DIR` — Where to create the eSTAR structure (default: project_dir/estar/)
- `--infer` — Auto-detect product code from project
- `--attach FILE [SECTION]` — Attach a file (test report, labeling PDF, image) to a specific eSTAR section. SECTION is the 2-digit section number (e.g., `15` for Performance Testing). Can be specified multiple times.

## Step 1: Inventory Available Data

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

files_to_check = {
    "output.csv": "Extraction results",
    "output_reviewed.csv": "Reviewed extraction",
    "review.json": "Predicate review data",
    "import_data.json": "eSTAR import data",
    "presub_plan.md": "Pre-Submission plan",
    "submission_outline.md": "Submission outline",
    "se_comparison.md": "SE comparison table",
    "test_plan.md": "Testing plan",
    "query.json": "Project metadata",
    "pdf_data.json": "PDF text cache",
}

for fname, desc in files_to_check.items():
    fpath = os.path.join(pdir, fname)
    if os.path.exists(fpath):
        size = os.path.getsize(fpath)
        print(f"FOUND:{fname}|{desc}|{size}")
    else:
        print(f"MISSING:{fname}|{desc}")

# Check guidance cache
gc = os.path.join(pdir, 'guidance_cache')
if os.path.isdir(gc):
    count = len([f for f in os.listdir(gc) if not f.startswith('.')])
    print(f"FOUND:guidance_cache/|Guidance documents|{count} files")
else:
    print(f"MISSING:guidance_cache/|Guidance documents")

# Check summaries
sd = os.path.join(pdir, 'summaries')
if os.path.isdir(sd):
    count = len([f for f in os.listdir(sd) if f.endswith('.md')])
    print(f"FOUND:summaries/|Analysis summaries|{count} files")
PYEOF
```

## Step 2: Create eSTAR Directory Structure

The eSTAR (electronic Submission Template and Resource) has a defined section structure:

```bash
ESTAR_DIR="$PROJECTS_DIR/$PROJECT_NAME/estar"
mkdir -p "$ESTAR_DIR"/{01_CoverLetter,02_CoverSheet,03_510kSummary,04_TruthfulAccuracy,05_FinancialCert,06_DeviceDescription,07_SEComparison,08_Standards,09_Labeling,10_Sterilization,11_ShelfLife,12_Biocompatibility,13_Software,14_EMC,15_PerformanceTesting,16_Clinical,17_HumanFactors,18_Other}
```

## Step 3: Map Data to Sections

For each eSTAR section, check if project data can populate it:

| Section | eSTAR Folder | Source Data | Auto-populate? |
|---------|-------------|-------------|----------------|
| Cover Letter | 01_CoverLetter | presub_plan.md (Section 1) | Partial |
| Cover Sheet | 02_CoverSheet | FDA Form 3514 template | Template |
| 510(k) Summary | 03_510kSummary | submission_outline.md | Partial |
| Truthful & Accuracy | 04_TruthfulAccuracy | Standard template | Template |
| Financial Cert | 05_FinancialCert | Standard template | Template |
| Device Description | 06_DeviceDescription | presub_plan.md (Section 2) | If available |
| SE Comparison | 07_SEComparison | se_comparison.md | Yes |
| Standards | 08_Standards | guidance_cache, test_plan.md | Partial |
| Labeling | 09_Labeling | IFU from presub_plan.md | If available |
| Sterilization | 10_Sterilization | test_plan.md | If applicable |
| Shelf Life | 11_ShelfLife | test_plan.md | If applicable |
| Biocompatibility | 12_Biocompatibility | test_plan.md, guidance_cache | Partial |
| Software | 13_Software | N/A | If applicable |
| EMC/Electrical | 14_EMC | N/A | If applicable |
| Performance | 15_PerformanceTesting | test_plan.md | Partial |
| Clinical | 16_Clinical | review.json (lit review) | If available |
| Human Factors | 17_HumanFactors | draft_human-factors.md | If applicable |
| Other | 18_Other | Remaining documents | As available |

### Import Data Pre-Population

If `import_data.json` exists (from `/fda:import`), use it as a **primary data source** for pre-populating sections:
- **Section 01 (Cover Letter)**: Pre-fill applicant name, address, contact info from `import_data.applicant`
- **Section 02 (Cover Sheet)**: Pre-fill product code, regulation, device class from `import_data.classification`
- **Section 06 (Device Description)**: Use `import_data.sections.device_description_text` if available
- **Section 07 (SE Comparison)**: Use imported predicate list and comparison narrative
- **Section 09 (Labeling)**: Use `import_data.sections.ifu_text` or `import_data.indications_for_use`

`import_data.json` takes **lower priority** than project-specific files (`se_comparison.md`, `draft_*.md`) when both exist.

For each section:
1. Create a `README.md` in the section folder describing what's needed
2. If data available, **auto-write content** into the section (not just copy the file):
   - **Section 06 (Device Description)**: If `--device-description` provided or presub_plan.md exists, write the device description prose into `06_DeviceDescription/device_description.md`. Mark as `DRAFT — AI-generated`.
   - **Section 07 (SE Comparison)**: If se_comparison.md exists, copy it into `07_SEComparison/se_comparison.md`. Mark as `DRAFT — AI-generated`.
   - **Section 08 (Standards)**: If guidance_cache exists, write a standards conformity declaration listing each standard and its status into `08_Standards/standards_declaration.md`. Mark as `DRAFT — AI-generated`.
   - **Section 12 (Biocompatibility)**: If test_plan.md or guidance_cache has biocompatibility requirements, write a biocompatibility plan summary into `12_Biocompatibility/biocompat_plan.md`. Mark as `TEMPLATE — manual completion`.
   - **Section 15 (Performance)**: If test_plan.md exists, write the performance testing plan into `15_PerformanceTesting/performance_plan.md`. Mark as `DRAFT — AI-generated`.
3. If template needed (no data available), generate a starter template
4. Mark each section clearly as one of:
   - `READY` — Verified by user as submission-appropriate (only set when user explicitly marks a section as verified)
   - `DRAFT` — AI-generated from project data (has content, requires professional review before submission)
   - `TEMPLATE` — Structure only, manual completion required (no substantive content)
   - `PARTIAL` — Some data available, significant gaps remain
   - `N/A` — Not applicable to this device type

### Cybersecurity Section Auto-Detection

Check if cybersecurity documentation is needed based on the device description and product code:

```python
desc = (device_description or "").lower()
product_code = "CODE"  # From project

cyber_trigger = any(kw in desc for kw in [
    "software", "firmware", "wireless", "bluetooth", "wifi", "connected",
    "app", "samd", "algorithm", "cloud", "network", "usb data", "usb communication", "rf",
    "iot", "telemetry", "digital"
])
```

If cybersecurity is triggered:
1. Create `13_Software/cybersecurity/` subdirectory
2. Generate templates from `references/cybersecurity-framework.md`:
   - `threat_model.md` — Threat model template
   - `sbom_template.md` — SBOM scaffold
   - `patch_plan.md` — Vulnerability management plan
3. Mark as `TEMPLATE — manual completion required`
4. Note in eSTAR index: "Cybersecurity documentation required — see Section 13"

## Step 4: Generate eSTAR Index

Write `$ESTAR_DIR/eSTAR_index.md`:

```markdown
# eSTAR Submission Package Index
## {Device Description} — Product Code {CODE}

**Pathway:** {Traditional/Special/Abbreviated/De Novo} 510(k)
**Generated:** {date}
**Project:** {project_name}

---

## Submission Readiness

| # | Section | Status | Data Source | Notes |
|---|---------|--------|-----------|-------|
| 01 | Cover Letter | {READY/DRAFT/PARTIAL/TEMPLATE/N/A} | {source} | {notes} |
| 02 | Cover Sheet (3514) | TEMPLATE | FDA form | Complete manually |
| 03 | 510(k) Summary | {status} | {source} | {notes} |
| ... | ... | ... | ... | ... |
| 17 | Human Factors | {status} | {source} | {notes} |
| 18 | Other | {status} | {source} | {notes} |

**Submission Readiness: {N}/{total} sections READY (verified)**
**Pipeline Coverage: {N}/{total} sections with content (READY + DRAFT)**

Note: Only READY sections count toward Submission Readiness — these are
sections the user has verified as submission-appropriate. DRAFT sections
have AI-generated content that has not yet been verified.

---

## Files in This Package

{list of all files in estar/ with section mapping}

---

## Gaps Requiring Attention

{list of sections that are TEMPLATE or missing data}

---

## Assembly Log

{timestamp and details of assembly process}
```

## Step 4b: Process Attachments

If `--attach` flags provided, process each attachment:

1. Validate the file exists and is a supported format (PDF, PNG, JPG, SVG, DOCX, XLSX, CSV, TXT)
2. Determine the target eSTAR section folder:
   - If SECTION specified: use `{##}_{SectionName}/` (e.g., `15_PerformanceTesting/`)
   - If SECTION not specified: infer from filename keywords (e.g., "biocompat" → 12, "IEC_60601" → 14)
   - If unable to infer: place in `18_Other/`
3. Copy file to the target section folder with eSTAR naming: `Section{##}_Attachment_{filename}`
4. Update `attachments.json` in the project directory:

```json
{
  "attachments": [
    {
      "original_path": "/path/to/report.pdf",
      "estar_path": "15_PerformanceTesting/Section15_Attachment_report.pdf",
      "section": "15",
      "added": "2026-02-09T12:00:00Z",
      "size_bytes": 1234567
    }
  ]
}
```

5. Warn if any attachment exceeds 100 MB (FDA eSTAR limit per file)
6. Include attachment count in the eSTAR index

Also scan for existing attachments: check `{project_dir}/attachments/` for files placed there manually. Include them in the inventory.

## Step 5: Report

```
  FDA eSTAR Assembly Report
  {product_code} — {device_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Project: {name} | v5.22.0

ASSEMBLY SUMMARY
────────────────────────────────────────

  Output: {estar_dir}/

  | Status     | Count | Description                          |
  |------------|-------|--------------------------------------|
  | ✓ Ready    | {N}   | Verified by user, submission-ready   |
  | ⚠ Draft    | {N}   | AI-generated, needs professional review |
  | ◐ Partial  | {N}   | Some data, significant gaps remain   |
  | ○ Template | {N}   | Structure only, manual completion    |
  | — N/A      | {N}   | Not applicable to this device        |

  Submission Readiness: {N}/{total} verified (READY only)
  Pipeline Coverage:    {N}/{total} with content (READY + DRAFT)

KEY FILES
────────────────────────────────────────

  eSTAR_index.md          Master index with readiness status
  {section}/README.md     Requirements for each section

NEXT STEPS
────────────────────────────────────────

  1. Review eSTAR_index.md for gap summary
  2. Complete ○ Template sections with device-specific data
  3. Add test reports to performance and biocompatibility sections
  4. Run /fda:export --project NAME to generate eSTAR XML
  5. Have regulatory team review for completeness
  6. Run /fda:pre-check to simulate FDA review
  7. Submit via CDRH Portal (see below)

SUBMIT TO FDA
────────────────────────────────────────

  Portal: https://ccp.fda.gov/prweb/PRAuth/app/default/extsso

  Before uploading:
  - Verify total package is under 4 GB (1 GB per attachment)
  - Ensure no PDF passwords are set on any document
  - Confirm official correspondent email is correct

  For full submission procedures, see references/cdrh-portal.md

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Artwork File Manifest (Section 09 — Labeling)

When assembling the eSTAR package, check for artwork files in the project:

1. If `artwork_dir` is set in project's `query.json` or `import_data.json`, scan that directory
2. Include artwork files (PDF, PNG, SVG, AI, EPS) in the Section 09 (Labeling) directory
3. Generate an artwork manifest file (`09_Labeling/artwork_manifest.md`):

```markdown
## Label Artwork Files

| # | File | Format | Size | Included |
|---|------|--------|------|----------|
| 1 | {filename} | {ext} | {size_kb} KB | Yes |

Total artwork files: {count}
Source directory: {artwork_dir}
```

If no artwork directory configured, note in assembly report:
```
Section 09 (Labeling): No artwork files found.
  → Set artwork directory with /fda:draft labeling --artwork-dir PATH
```

## Error Handling

- **No --project**: ERROR: "Project name required. Usage: /fda:assemble --project NAME"
- **Empty project**: Generate eSTAR structure with all TEMPLATE status. Note: "No project data found. Run /fda:pipeline first to generate data."
- **Missing key data**: Note which sections are affected and what commands to run
