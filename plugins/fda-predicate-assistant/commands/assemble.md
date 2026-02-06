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
mkdir -p "$ESTAR_DIR"/{01_cover_letter,02_cover_sheet,03_510k_summary,04_truthful_accuracy,05_financial_certification,06_device_description,07_se_comparison,08_standards_conformity,09_labeling,10_sterilization,11_shelf_life,12_biocompatibility,13_software,14_emc_electrical,15_performance_testing,16_clinical,17_other}
```

## Step 3: Map Data to Sections

For each eSTAR section, check if project data can populate it:

| Section | eSTAR Folder | Source Data | Auto-populate? |
|---------|-------------|-------------|----------------|
| Cover Letter | 01_cover_letter | presub_plan.md (Section 1) | Partial |
| Cover Sheet | 02_cover_sheet | FDA Form 3514 template | Template |
| 510(k) Summary | 03_510k_summary | submission_outline.md | Partial |
| Truthful & Accuracy | 04_truthful_accuracy | Standard template | Template |
| Financial Cert | 05_financial_certification | Standard template | Template |
| Device Description | 06_device_description | presub_plan.md (Section 2) | If available |
| SE Comparison | 07_se_comparison | se_comparison.md | Yes |
| Standards | 08_standards_conformity | guidance_cache, test_plan.md | Partial |
| Labeling | 09_labeling | IFU from presub_plan.md | If available |
| Sterilization | 10_sterilization | test_plan.md | If applicable |
| Shelf Life | 11_shelf_life | test_plan.md | If applicable |
| Biocompatibility | 12_biocompatibility | test_plan.md, guidance_cache | Partial |
| Software | 13_software | N/A | If applicable |
| EMC/Electrical | 14_emc_electrical | N/A | If applicable |
| Performance | 15_performance_testing | test_plan.md | Partial |
| Clinical | 16_clinical | review.json (lit review) | If available |
| Other | 17_other | Remaining documents | As available |

For each section:
1. Create a `README.md` in the section folder describing what's needed
2. If data available, **auto-write content** into the section (not just copy the file):
   - **Section 06 (Device Description)**: If `--device-description` provided or presub_plan.md exists, write the device description prose into `06_device_description/device_description.md`. Mark as `DRAFT — AI-generated`.
   - **Section 07 (SE Comparison)**: If se_comparison.md exists, copy it into `07_se_comparison/se_comparison.md`. Mark as `DRAFT — AI-generated`.
   - **Section 08 (Standards)**: If guidance_cache exists, write a standards conformity declaration listing each standard and its status into `08_standards_conformity/standards_declaration.md`. Mark as `DRAFT — AI-generated`.
   - **Section 12 (Biocompatibility)**: If test_plan.md or guidance_cache has biocompatibility requirements, write a biocompatibility plan summary into `12_biocompatibility/biocompat_plan.md`. Mark as `TEMPLATE — manual completion`.
   - **Section 15 (Performance)**: If test_plan.md exists, write the performance testing plan into `15_performance_testing/performance_plan.md`. Mark as `DRAFT — AI-generated`.
3. If template needed (no data available), generate a starter template
4. Mark each section clearly as one of:
   - `DRAFT — AI-generated from project data` (has content, needs verification)
   - `TEMPLATE — manual completion required` (has structure, no content)
   - `READY — data populated` (directly from user input)

### Cybersecurity Section Auto-Detection

Check if cybersecurity documentation is needed based on the device description and product code:

```python
desc = (device_description or "").lower()
product_code = "CODE"  # From project

cyber_trigger = any(kw in desc for kw in [
    "software", "firmware", "wireless", "bluetooth", "wifi", "connected",
    "app", "samd", "algorithm", "cloud", "network", "usb", "rf",
    "iot", "telemetry", "digital"
])
```

If cybersecurity is triggered:
1. Create `13_software/cybersecurity/` subdirectory
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
| 01 | Cover Letter | {READY/PARTIAL/TEMPLATE/N/A} | {source} | {notes} |
| 02 | Cover Sheet (3514) | TEMPLATE | FDA form | Complete manually |
| 03 | 510(k) Summary | {status} | {source} | {notes} |
| ... | ... | ... | ... | ... |

**Overall Readiness: {N}/{total} sections populated**

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

## Step 5: Report

```
  FDA eSTAR Assembly Report
  {product_code} — {device_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Project: {name} | v4.0.0

ASSEMBLY SUMMARY
────────────────────────────────────────

  Output: {estar_dir}/

  | Status     | Count | Description                    |
  |------------|-------|--------------------------------|
  | ✓ Ready    | {N}   | Data available from pipeline   |
  | ⚠ Partial  | {N}   | Some data, needs completion    |
  | ○ Template | {N}   | Starter template only          |
  | — N/A      | {N}   | Not applicable to this device  |

KEY FILES
────────────────────────────────────────

  eSTAR_index.md          Master index with readiness status
  {section}/README.md     Requirements for each section

NEXT STEPS
────────────────────────────────────────

  1. Review eSTAR_index.md for gap summary
  2. Complete ○ Template sections with device-specific data
  3. Add test reports to performance and biocompatibility sections
  4. Have regulatory team review for completeness

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Error Handling

- **No --project**: ERROR: "Project name required. Usage: /fda:assemble --project NAME"
- **Empty project**: Generate eSTAR structure with all TEMPLATE status. Note: "No project data found. Run /fda:pipeline first to generate data."
- **Missing key data**: Note which sections are affected and what commands to run
