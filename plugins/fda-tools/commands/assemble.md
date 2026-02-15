---
description: Assemble an eSTAR-structured submission package from project data — creates directory structure, maps sections to available data, and tracks readiness
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: "--project NAME [--product-code CODE] [--pathway traditional|special|abbreviated|denovo]"
---

# FDA eSTAR Submission Assembly

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
- `--refresh` — Lightweight update mode: detect stale eSTAR sections (where draft is newer than eSTAR copy), re-import updated drafts, and regenerate the eSTAR index. Skips full directory creation (Step 2) and section mapping (Step 3) if eSTAR directory already exists.

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

## Step 1b: Draft-vs-eSTAR Freshness Check

After inventorying project files, compare modification times of draft files against their eSTAR copies to detect stale sections:

```bash
python3 << 'PYEOF'
import os, glob, json

project = "PROJECT"  # Replace
projects_dir = os.path.expanduser("~/fda-510k-data/projects")
# ... resolve from settings ...
pdir = os.path.join(projects_dir, project)
estar_dir = os.path.join(pdir, "estar")
drafts_dir = os.path.join(pdir, "drafts")

# Mapping: draft filename → eSTAR section folder
draft_to_estar = {
    "draft_cover-letter.md": "01_CoverLetter",
    "draft_510k-summary.md": "03_510kSummary",
    "draft_truthful-accuracy.md": "04_TruthfulAccuracy",
    "draft_financial-certification.md": "05_FinancialCert",
    "draft_device-description.md": "06_DeviceDescription",
    "draft_se-discussion.md": "07_SEComparison",
    "draft_doc.md": "08_Standards",
    "draft_labeling.md": "09_Labeling",
    "draft_sterilization.md": "10_Sterilization",
    "draft_shelf-life.md": "11_ShelfLife",
    "draft_biocompatibility.md": "12_Biocompatibility",
    "draft_software.md": "13_Software",
    "draft_emc-electrical.md": "14_EMC",
    "draft_performance-summary.md": "15_PerformanceTesting",
    "draft_clinical.md": "16_Clinical",
    "draft_human-factors.md": "17_HumanFactors",
    "draft_form-3881.md": "03_510kSummary",
    "draft_reprocessing.md": "18_Other",
    "draft_combination-product.md": "18_Other",
}

stale = []
fresh = []
missing_estar = []

if os.path.isdir(estar_dir) and os.path.isdir(drafts_dir):
    for draft_name, estar_section in draft_to_estar.items():
        draft_path = os.path.join(drafts_dir, draft_name)
        if not os.path.exists(draft_path):
            continue

        draft_mtime = os.path.getmtime(draft_path)

        # Find corresponding eSTAR file
        estar_section_dir = os.path.join(estar_dir, estar_section)
        if not os.path.isdir(estar_section_dir):
            missing_estar.append(draft_name)
            continue

        # Check if any file in the eSTAR section matches
        estar_files = glob.glob(os.path.join(estar_section_dir, "*.md"))
        if not estar_files:
            missing_estar.append(draft_name)
            continue

        newest_estar = max(os.path.getmtime(f) for f in estar_files)
        if draft_mtime > newest_estar:
            stale.append((draft_name, estar_section, draft_mtime - newest_estar))
        else:
            fresh.append((draft_name, estar_section))

    for s in stale:
        print(f"STALE:{s[0]}|{s[1]}|{s[2]:.0f}s behind")
    for f in fresh:
        print(f"FRESH:{f[0]}|{f[1]}")
    for m in missing_estar:
        print(f"MISSING_ESTAR:{m}")
    print(f"SUMMARY:stale={len(stale)},fresh={len(fresh)},missing={len(missing_estar)}")
else:
    if not os.path.isdir(estar_dir):
        print("ESTAR_DIR:not_found")
    if not os.path.isdir(drafts_dir):
        print("DRAFTS_DIR:not_found")
PYEOF
```

**If `--refresh` mode:**
1. If eSTAR directory does not exist: **ERROR**: "No existing eSTAR directory found. Run `/fda:assemble --project NAME` first to create the initial eSTAR structure, then use `--refresh` for updates."
2. For each STALE section: re-copy the updated draft into the eSTAR section folder, preserving eSTAR naming conventions
3. For each MISSING_ESTAR draft: copy into the appropriate section folder (new section added since last assembly)
4. Regenerate `eSTAR_index.md` with updated timestamps
5. Skip Steps 2-3 (directory creation and full section mapping)
6. Proceed to Step 4 (index generation) and Step 5 (report)

**If NOT `--refresh` mode:** Report stale sections in assembly output as warnings, then proceed with full assembly.

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
| Cover Sheet (3514) | 02_CoverSheet | FDA Form 3514 — auto-populated from project data | Partial |
| 510(k) Summary | 03_510kSummary | submission_outline.md | Partial |
| Truthful & Accuracy | 04_TruthfulAccuracy | Standard template + signature block | Template |
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

### Form FDA 3881 (Indications for Use) — Section 03

Check for `draft_form-3881.md` in the drafts directory. This is a **CRITICAL RTA item** — every 510(k) submission requires Form 3881.

**If `draft_form-3881.md` exists:**
1. Copy to `03_510kSummary/form_3881.md`
2. Verify IFU text consistency: compare the IFU text in Form 3881 against:
   - `draft_labeling.md` (Section 09) IFU text
   - `draft_510k-summary.md` (Section 03) IFU text
   - `device_profile.json` `intended_use` field
3. If IFU text differs across documents, add a **CRITICAL** warning to the assembly report:
   `"⚠ CRITICAL: IFU text in Form 3881 does not match labeling/510k-summary. FDA requires identical IFU text across all submission documents."`
4. Mark as `DRAFT` status in the eSTAR index

**If `draft_form-3881.md` does NOT exist:**
1. Flag as **CRITICAL** gap in the assembly report:
   `"✗ CRITICAL GAP: Form FDA 3881 (Indications for Use) missing. This is a mandatory RTA item. Run: /fda:draft form-3881 --project NAME"`
2. Mark Section 03 entry as `CRITICAL GAP` in the eSTAR index (even if `draft_510k-summary.md` exists)
3. Add to remediation commands list: `/fda:draft form-3881 --project NAME`

### Import Data Pre-Population

If `import_data.json` exists (from `/fda:import`), use it as a **primary data source** for pre-populating sections:
- **Section 01 (Cover Letter)**: Pre-fill applicant name, address, contact info from `import_data.applicant`
- **Section 02 (Cover Sheet)**: Pre-fill product code, regulation, device class from `import_data.classification`
- **Section 06 (Device Description)**: Use `import_data.sections.device_description_text` if available
- **Section 07 (SE Comparison)**: Use imported predicate list and comparison narrative
- **Section 09 (Labeling)**: Use `import_data.sections.ifu_text` or `import_data.indications_for_use`

`import_data.json` takes **lower priority** than project-specific files (`se_comparison.md`, `draft_*.md`) when both exist.

### Section 02 — FDA Form 3514 (Cover Sheet) Generation

Generate an FDA Form 3514 template pre-populated from project data. Write to `02_CoverSheet/fda_form_3514.md`:

```markdown
# FDA Form 3514 — CDRH Premarket Review Submission Cover Sheet

## Section A: Applicant Information
- **Applicant (Legal Name):** {from import_data.json applicant.company_name or device_profile.json, else [TODO: Company Legal Name]}
- **Address:** {from import_data.json applicant.address, else [TODO: Street Address, City, State, ZIP]}
- **Contact Person:** {from import_data.json applicant.contact_name, else [TODO: Regulatory Contact Name]}
- **Phone:** {from import_data.json applicant.phone, else [TODO: Phone Number]}
- **Email:** {from import_data.json applicant.email, else [TODO: Email Address]}
- **Establishment Registration Number:** [TODO: Company-specific — FEI Number]

## Section B: Device Information
- **Device Trade/Proprietary Name:** {from device_profile.json trade_name or import_data.json, else [TODO: Device Trade Name]}
- **Common/Usual Name:** {from openFDA classification device_name for product code}
- **Product Code:** {detected product_code}
- **Device Class:** {from openFDA classification — I, II, or III}
- **Regulation Number:** 21 CFR {from openFDA classification regulation_number}
- **Is this a combination product?** [TODO: Yes/No]

## Section C: Submission Information
- **Submission Type:** 510(k) Premarket Notification
- **510(k) Type:** {from --pathway argument: Traditional / Special / Abbreviated}
- **Is a predicate device identified?** Yes
- **Predicate Device 510(k) Number(s):** {from review.json accepted predicates — list all K-numbers}
- **Predicate Device Name(s):** {from review.json or openFDA — list device names}

## Section D: Certification
- **Clinical data included?** {If draft_clinical.md exists and is not N/A: "Yes" else "No — bench testing only"}
- **If clinical data: Financial Certification/Disclosure (21 CFR Part 54)?** {If clinical: "[TODO: Attached — Form 3454/3455]" else "N/A"}

---
*This form template is auto-generated from project data. Verify all fields before submission.*
*Generated: {date} | Project: {project_name}*
```

### Section 04 — Truthful & Accuracy Statement with Signature Block

When generating the Truthful & Accuracy section, include a proper signature block. Write to `04_TruthfulAccuracy/truthful_accuracy.md` (or use existing `draft_truthful-accuracy.md` if available):

If `draft_truthful-accuracy.md` exists in the drafts directory, copy it to `04_TruthfulAccuracy/`. If it does NOT contain a signature block, append the following:

```markdown
---

## Certification

I certify that, in my capacity as {[TODO: Title]} of {[TODO: Company Legal Name]}, I believe to the best of my knowledge, that all data and information submitted in and with this premarket notification are truthful and accurate and that no material fact has been omitted.

**Signature:** _________________________________ **Date:** ___________

**Printed Name:** [TODO: Authorized Representative]

**Title:** [TODO: Title]

**Company:** [TODO: Company Legal Name]
```

If no `draft_truthful-accuracy.md` exists, generate the full standard template per 21 CFR 807.87(l) with the signature block included.

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

### Reprocessing Section — Auto-Detection (Section 18)

Auto-detect reusable device and create reprocessing documentation structure:

**Detection logic:** Check device description, se_comparison.md, and device_profile.json for reusable device indicators:
- Keywords: "reusable", "reprocessing", "autoclave", "multi-use", "non-disposable", "endoscope", "instrument tray"
- Sterilization method is "steam" for facility-sterilized (not terminal) devices

**If reusable device detected:**
1. Create `18_Other/reprocessing/` subdirectory
2. If `draft_reprocessing.md` exists in drafts: copy to `18_Other/reprocessing/reprocessing_validation.md`, mark as `DRAFT`
3. If `draft_reprocessing.md` does NOT exist: generate `18_Other/reprocessing/README.md` with:
   ```markdown
   # Reprocessing Validation — Required

   This device has been identified as a reusable medical device requiring reprocessing documentation.

   ## Required Documentation
   - Cleaning validation per AAMI TIR30
   - Disinfection/sterilization validation between uses
   - Lifecycle/durability testing (repeated reprocessing cycles)
   - Reprocessing IFU validation

   ## Generate Draft
   Run: `/fda:draft reprocessing --project {project_name}`

   ## References
   - AAMI TIR30: Cleaning validation for reusable medical devices
   - AAMI ST91: Flexible endoscope reprocessing (if applicable)
   - FDA Guidance: Reprocessing Medical Devices in Health Care Settings
   ```
4. Mark as `TEMPLATE` status in eSTAR index

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

SECTION FRESHNESS
────────────────────────────────────────

  | Section | Draft Date | eSTAR Date | Status |
  |---------|-----------|-----------|--------|
  | {section_name} | {draft_mtime} | {estar_mtime} | ✓ Fresh / ⚠ Stale / — No draft |

  {If any STALE sections:}
  ⚠ {N} sections have newer drafts than eSTAR copies.
  Run: /fda:assemble --project NAME --refresh

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

If no artwork directory configured, flag as **CRITICAL** gap in assembly report:
```
✗ CRITICAL GAP: Section 09 (Labeling) — No artwork files found.
  FDA requires proposed labeling including actual label artwork for RTA acceptance.
  Required artwork checklist:
    □ Package label (outer packaging)
    □ Device label (on-device or immediate container)
    □ IFU layout (formatted Instructions for Use)
    □ Sterile barrier label (if sterile device)
    □ Patient labeling (if patient-facing)
  → Provide artwork directory: /fda:draft labeling --artwork-dir PATH
  → Or attach individual files: /fda:assemble --project NAME --attach label.pdf 09
```

Include missing artwork in the eSTAR index as `CRITICAL GAP` status for Section 09.

## Combination Product Readiness Checks

**Auto-trigger:** If `device_profile['combination_product']['is_combination'] == True`

Perform specialized readiness checks for combination products per 21 CFR Part 3:

### 1. Section 15 Required

**Check:** Does `estar/15_CombinationProduct/` directory exist with content?

- ✅ **PASS:** Section 15 present with substantive content (not just template)
- ❌ **CRITICAL GAP:** Section 15 (Combination Product Information) MISSING
  ```
  ✗ CRITICAL GAP: Section 15 (Combination Product Information) MISSING
    This is a {combination_type} combination product.
    FDA requires combination product documentation per 21 CFR Part 3.
    → Run: /fda:draft combination-product --project NAME
  ```

### 2. Cover Letter Disclosure

**Check:** Does `draft_cover-letter.md` state combination product status and RHO?

Required statements:
- "This is a {combination_type} combination product."
- "{rho_assignment} is the Responsible Health Organization (RHO) per 21 CFR Part 3."

- ✅ **PASS:** Combination product status disclosed in cover letter
- ❌ **CRITICAL GAP:** Cover letter must disclose combination product status and RHO
  ```
  ✗ CRITICAL GAP: Cover letter does not disclose combination product status
    FDA requires explicit statement of combination product type and RHO assignment.
    → Add to cover letter:
      "This submission is for a {combination_type} combination product.
       Per 21 CFR Part 3, {rho_assignment} is the Responsible Health Organization (RHO)."
  ```

### 3. PMOA Statement

**Check:** Is Primary Mode of Action clearly stated in Section 04 (Device Description) or Section 15?

Search for: "primary mode of action", "PMOA", "primary mechanism"

- ✅ **PASS:** PMOA clearly stated
- ❌ **CRITICAL GAP:** Primary Mode of Action not stated
  ```
  ✗ CRITICAL GAP: Primary Mode of Action (PMOA) not stated
    21 CFR Part 3 requires PMOA determination for all combination products.
    → Add PMOA statement to Section 04 or Section 15:
      "The primary mode of action is [mechanical/pharmacological/immunological]
       because [scientific justification]."
  ```

### 4. Drug/Biologic Specifications

**Check (if drug-device):** Does Section 15 include:
- Drug chemical name and CAS number
- Drug concentration/load
- Drug release profile (elution kinetics)
- Drug stability data

- ✅ **PASS:** Drug specifications complete
- ❌ **MAJOR GAP:** Drug specifications incomplete
  ```
  ⚠ MAJOR GAP: Drug component specifications incomplete
    Missing one or more required elements:
    □ Chemical name and CAS number
    □ Drug concentration/load (e.g., µg/mm²)
    □ Elution kinetics (24h, 7d, 28d release percentages)
    □ Stability data (shelf life, storage conditions)
    → Complete Section 15.3 (Drug Component Specifications)
  ```

**Check (if device-biologic):** Does Section 15 include:
- Biologic source material
- Donor screening procedures
- Disease transmission mitigation
- Immunogenicity assessment

- ✅ **PASS:** Biologic specifications complete
- ❌ **MAJOR GAP:** Biologic specifications incomplete
  ```
  ⚠ MAJOR GAP: Biologic component specifications incomplete
    Missing one or more required elements:
    □ Biologic source and processing
    □ Donor screening and viral testing
    □ Disease transmission mitigation (SAL, validation)
    □ Immunogenicity risk characterization
    → Complete Section 15.4 (Biologic Component Specifications)
  ```

### 5. RHO Consultation

**Check:** Is consultation with CDER/CBER documented?

- ✅ **PASS:** Center consultation documented in Section 15.7
- ⚠️ **WARNING:** Consultation with {consultation_required} recommended but not documented
  ```
  ⚠ WARNING: Center consultation not documented
    Recommended: Consult with {consultation_required} on {drug/biologic} component assessment
    → Document consultation in Section 15.7 (Regulatory Pathway and OCP Coordination)
    → OR: Note in cover letter if consultation is planned pre-submission
  ```

### 6. OCP RFD (if needed)

**Check:** For complex PMOA or "UNCERTAIN" RHO, is OCP Request for Designation referenced?

- ✅ **PASS:** OCP RFD submitted or not needed (clear RHO assignment)
- ❌ **CRITICAL GAP:** Complex PMOA requires OCP RFD - not submitted
  ```
  ✗ CRITICAL GAP: OCP Request for Designation (RFD) required but not submitted
    This {drug-device-biologic / UNCERTAIN RHO} product requires OCP RFD per 21 CFR 3.7
    Rationale: {rho_rationale}
    → Submit OCP RFD BEFORE 510(k) submission
    → Reference RFD number in Section 15.7 and cover letter
  ```
- ⚠️ **RECOMMENDED:** Consider OCP RFD for clarity
  ```
  ⚠ RECOMMENDED: Consider OCP Request for Designation (RFD)
    While RHO assignment appears clear ({rho_assignment}), an OCP RFD can provide
    regulatory certainty and avoid review delays.
    → Optional: Submit OCP Pre-Sub or RFD to confirm RHO assignment
  ```

### Combination Product Gap Summary

Generate summary report:

```markdown
COMBINATION_PRODUCT_READINESS
────────────────────────────────────────

Combination Type: {drug-device / device-biologic / drug-device-biologic}
RHO: {CDRH / CDER / CBER / UNCERTAIN}
Detection Confidence: {HIGH / MEDIUM / LOW}

CRITICAL Gaps (must fix before submission):
  {count}/6 checks PASSED

  {If any CRITICAL gaps:}
  - Section 15 missing (0/1) → Run /fda:draft combination-product
  - Cover letter missing combination disclosure (0/1) → Update cover letter
  - PMOA not stated (0/1) → Add PMOA to Section 04 or 15
  - OCP RFD required but not submitted (0/1) → Submit RFD per 21 CFR 3.7

MAJOR Gaps (strongly recommended to fix):
  - Drug specifications incomplete (0/1) → Complete Section 15.3
  - Biologic specifications incomplete (0/1) → Complete Section 15.4

WARNINGS (recommended but not blocking):
  - CDER/CBER consultation not documented
  - Consider OCP RFD for regulatory certainty

Recommendations:
  {List of specific actions from combination_product['recommendations']}
```

**Integration with eSTAR Index:**

Mark combination product gaps in the eSTAR index:
- Section 15 missing → `CRITICAL GAP` status
- PMOA missing → Add note to Section 04 and Section 15 entries
- Drug/biologic specs incomplete → Mark Section 15 as `PARTIAL` with gap note

Include missing artwork in the eSTAR index as `CRITICAL GAP` status for Section 09.

## MRI Safety Readiness Checks (Sprint 6 - NEW)

**Auto-trigger:** If `device_profile['mri_safety']['required'] == True` (implantable device detected in Step 0.65)

Perform MRI safety readiness checks per FDA guidance "Establishing Safety and Compatibility of Passive Implants in the Magnetic Resonance (MR) Environment" (August 2021):

### 1. Section 19 Present

**Check:** Does `estar/19_MRI_Safety/` directory exist with content?

- ✅ **PASS:** Section 19 present with substantive content (not just template)
- ❌ **CRITICAL GAP:** Section 19 (MRI Safety) MISSING
  ```
  ✗ CRITICAL GAP: Section 19 (MRI Safety) MISSING
    This is an implantable device (product code: {product_code}).
    FDA requires MRI safety information per August 2021 guidance.
    → Run: /fda:draft mri-safety --project NAME
  ```

### 2. ASTM F2182 Testing Documented

**Check:** Does Section 19.2 include RF heating, displacement force, and artifact test data?

Search for placeholders: `{{max_delta_t}}`, `{{scanner_model}}`, `{{max_force}}`

- ✅ **PASS:** ASTM F2182/F2052/F2119 test results documented (no placeholders)
- ❌ **CRITICAL GAP:** ASTM F2182 testing results NOT documented
  ```
  ✗ CRITICAL GAP: ASTM F2182 testing results NOT documented
    Section 19 contains template placeholders ({{max_delta_t}}, {{scanner_model}}, etc.)

    Required Testing:
    □ ASTM F2182-19e2: RF-induced heating at 1.5T and 3T
    □ ASTM F2052-21: Magnetically induced displacement force
    □ ASTM F2119-07: Image artifact characterization
    {If orthopedic: □ ASTM F2213-17: Magnetically induced torque}

    → Complete ASTM F2182/F2052/F2119 testing at accredited lab (~$5K-$15K, 2-4 weeks)
    → Update Section 19.2 with actual test results
    → Remove all {{placeholder}} variables
  ```

### 3. MRI Safety Classification Stated

**Check:** Does Section 19.1 state "MR Safe", "MR Conditional", or "MR Unsafe"?

Search for: `{{mri_classification}}` placeholder or actual classification statement

- ✅ **PASS:** MRI safety classification clearly stated
- ❌ **CRITICAL GAP:** MRI safety classification NOT determined
  ```
  ✗ CRITICAL GAP: MRI safety classification NOT determined
    Section 19.1 contains placeholder {{mri_classification}}

    Determine Classification Based on ASTM F2182 Results:
    - If all materials are polymers (PEEK, UHMWPE) → MR Safe
    - If metallic with ΔT ≤2.0°C and force/weight <1.0 → MR Conditional
    - If ΔT >2.0°C or force/weight ≥1.0 → MR Unsafe (RARE - review materials)

    → Based on ASTM F2182 results, determine classification
    → Update Section 19.1 with final classification
  ```

### 4. IFU Section 7.2 (MRI Safety) Present

**Check:** Does IFU include Section 7.2 with MRI safety information?

Search draft_labeling.md or IFU files for: "MRI", "MR Conditional", "magnetic resonance"

- ✅ **PASS:** IFU includes MRI safety information in Section 7.2
- ❌ **CRITICAL GAP:** IFU missing MRI safety information
  ```
  ✗ CRITICAL GAP: IFU missing MRI safety information
    FDA requires MRI safety labeling for all implantable devices.

    Required IFU Content (Section 7.2):
    □ MRI safety classification (MR Safe/Conditional/Unsafe)
    □ Maximum field strength (e.g., ≤3.0 Tesla)
    □ Maximum SAR limit (e.g., ≤2.0 W/kg)
    □ Maximum scan duration (e.g., ≤15 minutes)
    □ Patient warnings and instructions
    □ Image artifact extent disclosure

    → Add IFU Section 7.2 using template from Section 19.4
    → Ensure consistency between Section 19 and IFU labeling
  ```

### 5. MR Conditional Labeling Complete (if applicable)

**Check (if MR Conditional):** Does Section 19.3 specify all conditional parameters?

Required parameters for MR Conditional:
- Maximum static field strength (Tesla)
- Maximum spatial gradient (T/m)
- Maximum whole-body-averaged SAR (W/kg)
- Maximum scan duration (minutes)
- MR scanning mode restrictions

- ✅ **PASS:** All MR Conditional parameters specified
- ❌ **CRITICAL GAP:** MR Conditional parameters incomplete
  ```
  ✗ CRITICAL GAP: MR Conditional parameters incomplete
    Device classified as MR Conditional but labeling conditions not fully specified.

    Missing Parameters:
    {List placeholders found: {{max_field_strength}}, {{max_sar}}, etc.}

    → Complete Section 19.3 with all conditional parameters
    → Ensure parameters are based on ASTM F2182 test conditions
  ```

### 6. Test Lab Accreditation Documented

**Check:** Does Section 19.5 reference accredited test lab with report numbers?

Search for: test lab name, ISO/IEC 17025, report numbers

- ✅ **PASS:** Test lab accreditation and report traceability documented
- ⚠️ **MAJOR GAP:** Test lab accreditation not documented
  ```
  ⚠ MAJOR GAP: Test lab accreditation not documented
    Section 19.5 missing test lab information and report numbers.

    Required Documentation:
    □ Test lab name and accreditation (ISO/IEC 17025)
    □ Test report numbers for RF heating, displacement, artifact
    □ Test dates and test article serial numbers
    □ Statement of test article representativeness

    → Add test lab information to Section 19.5
    → Attach test reports to eSTAR Section 19 folder
  ```

### MRI Safety Gap Summary

Generate summary report:

```markdown
MRI_SAFETY_READINESS_SCORECARD
────────────────────────────────────────

Device: {device_name}
Product Code: {product_code}
Device Type: Implantable
Expected MRI Classification: {expected_classification}
Materials Detected: {material_list}

Readiness: {n}/6 checks PASSED

CRITICAL Gaps (MUST fix before submission):
  {count}/4 core checks PASSED

  {If any CRITICAL gaps:}
  - Section 19 missing (0/1) → Run /fda:draft mri-safety
  - ASTM F2182 testing not documented (0/1) → Complete testing, update Section 19.2
  - MRI classification not determined (0/1) → Determine from test results, update Section 19.1
  - IFU Section 7.2 missing (0/1) → Add MRI safety information to IFU
  {If MR Conditional:}
  - MR Conditional parameters incomplete (0/1) → Complete Section 19.3

MAJOR Gaps (strongly recommended to fix):
  - Test lab accreditation not documented (0/1) → Complete Section 19.5

Recommendations:
  Priority 1: Complete ASTM F2182 testing (external test lab, ~$5K-$15K, 2-4 weeks)
  Priority 2: Determine MRI safety classification based on test results
  Priority 3: Update Section 19 with actual test data (remove all placeholders)
  Priority 4: Add MRI safety information to IFU Section 7.2
  Priority 5: Ensure consistency between Section 19 and IFU labeling

External Testing Required:
  - ASTM F2182-19e2: RF heating test (15-minute scan, temperature probes)
  - ASTM F2052-21: Magnetically induced displacement test (deflection angle)
  - ASTM F2119-07: Image artifact characterization (T1, T2, GRE sequences)
  {If orthopedic implant:}
  - ASTM F2213-17: Magnetically induced torque test

Test Lab Resources:
  - Accredited labs: [List of ASTM F2182 certified test laboratories]
  - Typical cost: $5,000-$15,000 for complete MRI safety testing suite
  - Typical turnaround: 2-4 weeks from test article receipt
```

**Integration with eSTAR Index:**

Mark MRI safety gaps in the eSTAR index:
- Section 19 missing → `CRITICAL GAP` status
- Test data incomplete (placeholders present) → Mark Section 19 as `TEMPLATE` with gap note
- IFU Section 7.2 missing → Add note to Section 09 (Labeling) entry
- All checks passed → Mark Section 19 as `DRAFT` (requires professional review)

**Example Gap Detection Output:**

```
MRI_SAFETY_READINESS_SCORECARD
────────────────────────────────────────
Device: SpineFix Lumbar Interbody Cage
Product Code: OVE
Device Type: Implantable
Expected MRI Classification: MR Conditional
Materials Detected: Ti-6Al-4V, PEEK, CoCrMo

Readiness: 2/6 checks PASSED

CRITICAL Gaps (MUST fix before submission):
  2/4 core checks PASSED

  ✗ ASTM F2182 testing not documented (0/1)
  ✗ IFU Section 7.2 missing (0/1)

MAJOR Gaps (strongly recommended to fix):
  ✗ Test lab accreditation not documented (0/1)

Recommendations:
  Priority 1: Complete ASTM F2182 testing (external test lab, ~$10K, 3 weeks)
  Priority 2: Update Section 19.2 with actual test data (remove placeholders)
  Priority 3: Add IFU Section 7.2 with MR Conditional labeling
  Priority 4: Document test lab accreditation in Section 19.5

External Testing Required:
  - ASTM F2182-19e2: RF heating test at 1.5T and 3T
  - ASTM F2052-21: Displacement force test
  - ASTM F2119-07: Image artifact characterization
  - ASTM F2213-17: Torque test (orthopedic implant)
```

## Error Handling

- **No --project**: ERROR: "Project name required. Usage: /fda:assemble --project NAME"
- **Empty project**: Generate eSTAR structure with all TEMPLATE status. Note: "No project data found. Run /fda:pipeline first to generate data."
- **Missing key data**: Note which sections are affected and what commands to run
