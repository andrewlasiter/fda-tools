---
description: Generate PMA submission section drafts — Summary of Safety and Effectiveness Data (SSED), clinical study summaries, manufacturing information, preclinical studies, and device description for PMA applications
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch, WebSearch
argument-hint: "<section> --project NAME [--pma P170019] [--device-description TEXT] [--intended-use TEXT]"
---

# FDA PMA Section Draft Generator

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

If `$FDA_PLUGIN_ROOT` is empty, report an error: "Could not locate the FDA Predicate Assistant plugin installation. Make sure the plugin is installed and enabled."

---

You are generating regulatory prose drafts for specific sections of a PMA (Premarket Approval) submission under 21 CFR Part 814. PMA requirements are substantially more rigorous than 510(k) — each section must demonstrate reasonable assurance of safety and effectiveness from valid scientific evidence.

> **WARNING: LLM-generated prose carries confabulation risk.** Every factual claim, citation, test result, and regulatory reference must be independently verified by a qualified regulatory affairs professional before use in any PMA submission. Mark unverified claims as `[CITATION NEEDED]`.

**KEY PRINCIPLE: Every claim must cite its source.** Use project data (pma_data/, ssed_cache/, clinical_reports/) to substantiate assertions. PMA sections must reflect actual study data — fabricated or placeholder performance values are unacceptable.

---

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Section name** (required) — One of: `device-description`, `ssed`, `clinical`, `manufacturing`, `preclinical`, `biocompatibility`, `software`, `sterilization`, `labeling`, `risk-analysis`, `cover-letter`, `truthful-accuracy`, `summary`
- `--project NAME` (required) — Project directory for this PMA
- `--pma NUMBER` — Reference PMA number for intelligence context (e.g., P170019)
- `--device-description TEXT` — Description of the subject device
- `--intended-use TEXT` — Indications for use (21 CFR 814.20(b)(3))
- `--product-code CODE` — FDA product code (optional, auto-detected from project)
- `--output FILE` — Write draft to file (default: `pma_draft_{section}.md` in project folder)
- `--revise` — Revise an existing draft while preserving user edits

## PMA Section Registry

Map the section argument to the 21 CFR 814.20 section number and draft logic:

| Section | CFR Reference | Mandatory | Description |
|---------|--------------|-----------|-------------|
| `device-description` | 814.20(b)(3) | Yes | Physical/technical device description |
| `ssed` | 814.20(b)(6) | Yes | Summary of Safety and Effectiveness Data |
| `clinical` | 814.20(b)(6)(ii) | Yes | Clinical studies summary and data |
| `manufacturing` | 814.20(b)(4) | Yes | Manufacturing methods and quality controls |
| `preclinical` | 814.20(b)(6)(i) | Yes | Bench/animal testing summaries |
| `biocompatibility` | 814.20(b)(6)(i) | Yes | ISO 10993 biocompatibility data |
| `software` | 814.20(b)(6) | Cond. | Software documentation (if software-controlled) |
| `sterilization` | 814.20(b)(6)(i) | Cond. | Sterilization validation (if sterile device) |
| `labeling` | 814.20(b)(10) | Yes | Device labeling |
| `risk-analysis` | 814.20(b)(6) | Yes | Risk analysis summary (ISO 14971) |
| `cover-letter` | 814.20(a) | Yes | Cover letter addressing 21 CFR 814.20(a) requirements |
| `truthful-accuracy` | 814.20(b)(12) | Yes | Truthful and accuracy certification |
| `summary` | 814.9 | Yes | PMA Summary (public document) |

---

## Step 0: Load Project Data

```bash
python3 << 'PYEOF'
import json, os, re, glob

settings_path = os.path.expanduser("~/.claude/fda-tools.local.md")
projects_dir = os.path.expanduser("~/fda-510k-data/projects")
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    m = re.search(r'projects_dir:\s*(\S+)', content)
    if m:
        projects_dir = os.path.expanduser(m.group(1))

project_name = "$PROJECT_NAME"  # Substituted by command parser
pdir = os.path.join(projects_dir, project_name)

if not os.path.isdir(pdir):
    print(f"ERROR:Project directory not found: {pdir}")
    exit(1)

print(f"PROJECT_DIR:{pdir}")
print(f"PROJECT_NAME:{project_name}")

# Load device profile
dp_path = os.path.join(pdir, "device_profile.json")
if os.path.exists(dp_path):
    with open(dp_path) as f:
        dp = json.load(f)
    print(f"DEVICE_NAME:{dp.get('device_name', '')}")
    print(f"PRODUCT_CODE:{dp.get('product_code', '')}")
    print(f"REGULATION_NUMBER:{dp.get('regulation_number', '')}")
    ifu = dp.get("indications_for_use", dp.get("intended_use", ""))
    print(f"INDICATIONS_FOR_USE:{ifu[:200]}")
else:
    print("DEVICE_PROFILE:missing")

# Load PMA intelligence data
pma_dir = os.path.join(pdir, "pma_data")
if os.path.isdir(pma_dir):
    pma_files = glob.glob(os.path.join(pma_dir, "*.json"))
    print(f"PMA_DATA_FILES:{len(pma_files)}")
    # Load first PMA for context
    for pf in pma_files[:1]:
        with open(pf) as f:
            pma = json.load(f)
        print(f"REF_PMA:{pma.get('pma_number', '')}|applicant={pma.get('applicant_name', '')}|date={pma.get('decision_date', '')}")
else:
    print("PMA_DATA:none")

# Load SSED cache
ssed_dir = os.path.join(pdir, "ssed_cache")
if os.path.isdir(ssed_dir):
    ssed_files = glob.glob(os.path.join(ssed_dir, "*.json"))
    print(f"SSED_FILES:{len(ssed_files)}")
else:
    print("SSED_CACHE:none")

# Load clinical reports
for fname in ["clinical_report.json", "clinical_requirements.json"]:
    fpath = os.path.join(pdir, fname)
    if os.path.exists(fpath):
        print(f"CLINICAL_DATA:{fname}")
        break
else:
    print("CLINICAL_DATA:none")

# Check for existing drafts
existing = glob.glob(os.path.join(pdir, "pma_draft_*.md"))
print(f"EXISTING_PMA_DRAFTS:{len(existing)}")
for d in sorted(existing):
    print(f"EXISTING_DRAFT:{os.path.basename(d)}")

PYEOF
```

If `PROJECT_DIR` shows an error, halt and report the error.

Detect sparse data conditions:
- If `PMA_DATA:none` AND `SSED_CACHE:none`: warn "⚠ No PMA intelligence data found. Run `/fda:pma-search --product-code {CODE}` first to populate comparable PMA data. Sections that rely on precedent analysis will use placeholder content."
- If `CLINICAL_DATA:none`: warn "⚠ No clinical data found. The `clinical` section will use a template structure requiring manual population from your clinical study reports."

---

## Step 1: Route to Section Draft

Based on the section argument, generate the appropriate draft. All sections must:
1. Use `[CITATION NEEDED]` for any claim lacking a source in project data
2. Use `[INSERT: ...]` for values requiring manual input (e.g., specific test results)
3. Use `[TODO: ...]` for structural decisions requiring RA professional judgment
4. Never fabricate clinical data, test values, or statistical results

---

### Section: `device-description`

**21 CFR 814.20(b)(3)** — A complete description of the device.

Generate a PMA-level device description covering:

**1. Device Overview**
```
{device_name} is a [type] device indicated for [indications_for_use].

The device is classified under 21 CFR [regulation_number] (Product Code: {product_code}).
It is subject to the special controls and performance standards specified in [INSERT: applicable CFR subpart].
```

**2. Components and Materials**
- List all device components with materials specifications
- Include dimensions, tolerances, and material grades
- Reference applicable ISO/ASTM material standards
- If sterile: indicate sterility method and shelf life

**3. Principles of Operation**
Describe the mechanism of action and how the device achieves its intended therapeutic or diagnostic purpose.

**4. Variations/Sizes**
Table of all device variants, sizes, and configurations included in this PMA.

**5. Accessories and Compatible Equipment**
List accessories, delivery systems, and compatible equipment included or separately marketed.

---

### Section: `ssed`

**21 CFR 814.20(b)(6)** — Summary of Safety and Effectiveness Data.

The SSED is the primary PMA document for FDA review. Structure as follows:

```markdown
# Summary of Safety and Effectiveness Data
## [Device Name] — PMA Application

### I. General Information

**Device:** [Device Name]
**Applicant:** [INSERT: Company name and address]
**Date of Panel Meeting (if applicable):** [INSERT: or N/A]
**Date of FDA Approval:** [To be completed upon approval]
**PMA Number:** [INSERT: P-number]

### II. Indications for Use

[Device name] is indicated for [indications_for_use].

[TODO: Verify indications match 21 CFR 814.20(b)(3)(ii) requirements]

### III. Device Description

[Cross-reference: see pma_draft_device-description.md]

### IV. Preclinical Studies

[Cross-reference: see pma_draft_preclinical.md]

[If SSED data available from comparable PMAs:]
Based on precedent analysis of comparable PMAs, the following preclinical study types have been accepted by FDA for this device type:

[List from ssed_cache if available, else use [CITATION NEEDED]]

### V. Clinical Studies

[Cross-reference: see pma_draft_clinical.md]

### VI. Conclusions

Based on the totality of the evidence presented, [device name] provides reasonable assurance of safety and effectiveness for its intended use.

[TODO: Align conclusions with actual study outcomes — this template requires population with real study data before submission]
```

---

### Section: `clinical`

**21 CFR 814.20(b)(6)(ii)** — Clinical investigations section.

```markdown
# Clinical Studies Summary

## Study Overview

**Primary Pivotal Study:** [INSERT: Study name/ID]
**Study Design:** [INSERT: RCT/IDE/Single-arm/Registry]
**Clinical Sites:** [INSERT: Number and locations]
**Total Enrollment:** [INSERT: N subjects]
**Follow-up Duration:** [INSERT: months/years]
**Primary Endpoint:** [INSERT: Clinical endpoint with definition]

[TODO: All values in this section MUST be populated from actual study data. Do not submit with INSERT placeholders.]

## Primary Endpoint Results

| Endpoint | Device Group | Control Group | p-value | 95% CI |
|----------|-------------|---------------|---------|--------|
| [Primary endpoint] | [INSERT] | [INSERT] | [INSERT] | [INSERT] |
| [Secondary endpoint 1] | [INSERT] | [INSERT] | [INSERT] | [INSERT] |

[CITATION NEEDED: Clinical study report]

## Safety Results

### Serious Adverse Events
| Event | Device (N=X) | Control (N=X) | p-value |
|-------|-------------|---------------|---------|
| [INSERT] | [INSERT] | [INSERT] | [INSERT] |

### Device Deficiencies
[INSERT: List of device deficiencies, malfunctions, or user errors]

## Statistical Methods

**Primary Analysis:** [INSERT: Statistical method, e.g., Bayesian, frequentist]
**Sample Size Justification:** [INSERT: Power calculation with assumptions]
**Non-Inferiority/Superiority Margin:** [INSERT: if applicable]

[If clinical_requirements.json exists, load and reference precedent study designs from comparable PMAs]
```

If `CLINICAL_DATA` is found in project, load it and populate the study design fields from the precedent analysis (study_type, enrollment, endpoints, follow_up).

---

### Section: `manufacturing`

**21 CFR 814.20(b)(4)** — Manufacturing information.

```markdown
# Manufacturing Information

## Manufacturing Sites

| Site | Location | Operations | FDA Registration |
|------|----------|------------|-----------------|
| [INSERT: Primary site] | [INSERT: City, State, Country] | Final assembly, final test | [INSERT: Reg. No.] |
| [INSERT: Component supplier] | [INSERT] | [INSERT: Component manufactured] | [INSERT] |

[TODO: All manufacturing sites must be listed. FDA inspects all sites involved in finished device manufacture.]

## Manufacturing Process Description

### 1. Component Procurement and Incoming Inspection
[INSERT: Description of incoming inspection procedures and acceptance criteria]

### 2. Assembly and Manufacturing Steps
[INSERT: High-level process flow — do not include proprietary manufacturing details in the public SSED]

### 3. In-Process Controls
[INSERT: Critical process controls, inspection points, and acceptance criteria]

### 4. Finished Device Testing
**Sterility Testing (if applicable):** [INSERT: Method, AQL]
**Functional Testing:** [INSERT: 100% test vs. sampling plan]
**Dimensional Verification:** [INSERT: Method and acceptance criteria]

## Quality System

The device is manufactured under a Quality Management System compliant with:
- 21 CFR Part 820 (Quality System Regulation / cGMP)
- ISO 13485:2016 (Medical Devices — Quality Management Systems)

[INSERT: List applicable FDA 483 observations, warning letters, or corrective actions if any exist]

## Sterilization (if applicable)

**Sterilization Method:** [INSERT: EO / Gamma / E-beam / Steam / Other]
**Sterility Assurance Level (SAL):** 10⁻⁶
**Validation Standard:** [INSERT: ISO 11135/11137/11138 as applicable]
**Bioburden Testing:** [CITATION NEEDED: Validation study reference]
```

---

### Section: `preclinical`

**21 CFR 814.20(b)(6)(i)** — Non-clinical laboratory studies.

```markdown
# Preclinical Studies Summary

> All in vitro and in vivo studies are summarized below. Full study reports are included as appendices.

## Bench Testing

### Mechanical Performance Testing
| Test | Standard | Pass Criteria | Result | Status |
|------|----------|--------------|--------|--------|
| [INSERT: e.g., Tensile strength] | [INSERT: e.g., ASTM F543] | [INSERT: ≥X N] | [INSERT] | [INSERT: PASS/FAIL] |
| [INSERT] | [INSERT] | [INSERT] | [INSERT] | [INSERT] |

[CITATION NEEDED: Test reports for each row]

### Dimensional Verification
[INSERT: Summary of dimensional testing results against design specifications]

### Fatigue/Durability Testing
[INSERT: Cycles tested, failure mode analysis, safety factor]

## Electrical Safety Testing (if applicable)
| Test | Standard | Result |
|------|----------|--------|
| Electrical safety | IEC 60601-1 | [INSERT: PASS/FAIL] |
| EMC | IEC 60601-1-2 | [INSERT: PASS/FAIL] |
| Software validation | IEC 62304 | [INSERT: PASS/FAIL] |

## Animal Studies (if applicable)

### In Vivo Biocompatibility
**Animal Model:** [INSERT: species, strain]
**Study Duration:** [INSERT: days/weeks/months]
**Endpoints:** [INSERT: histopathology, inflammatory response, encapsulation]
**Key Findings:** [INSERT: summary of findings]
**Conclusion:** [INSERT: Supports / Does not support clinical use]

[CITATION NEEDED: GLP study report with study number]

## Simulated Use Testing
[INSERT: Describe any human factors validation or simulated use testing per 21 CFR 814.20(b)(6)]
```

---

### Section: `biocompatibility`

**ISO 10993** biocompatibility evaluation for PMA:

```markdown
# Biocompatibility Evaluation

## Risk-Based Approach (ISO 10993-1:2018)

**Device Category:** [INSERT: Per ISO 10993-1 Table A.1]
**Nature of Contact:** [INSERT: Surface/External communicating/Implant]
**Contact Duration:** [INSERT: Limited (<24h) / Prolonged (24h-30d) / Permanent (>30d)]

## Biocompatibility Tests Conducted

| Test | Standard | Result | Conclusion |
|------|----------|--------|------------|
| Cytotoxicity | ISO 10993-5 | [INSERT] | [INSERT: Pass/Fail] |
| Sensitization | ISO 10993-10 | [INSERT] | [INSERT] |
| Irritation | ISO 10993-10 | [INSERT] | [INSERT] |
| Systemic Toxicity (acute) | ISO 10993-11 | [INSERT] | [INSERT] |
| Subchronic/Chronic Toxicity | ISO 10993-11 | [INSERT: if applicable] | [INSERT] |
| Genotoxicity | ISO 10993-3 | [INSERT: if applicable] | [INSERT] |
| Implantation | ISO 10993-6 | [INSERT: if implantable] | [INSERT] |
| Hemocompatibility | ISO 10993-4 | [INSERT: if blood contact] | [INSERT] |
| Pyrogenicity | ISO 10993-11 | [INSERT: if applicable] | [INSERT] |

[TODO: Tests listed above are indicative — final test matrix must be approved by toxicologist based on device-specific risk assessment per ISO 10993-1 and FDA guidance "Use of ISO 10993-1: Biological Evaluation of Medical Devices" (2020)]

## Chemical Characterization (ISO 10993-18)
[INSERT: Summary of extractables/leachables analysis and Tolerable Intake (TI) comparisons]

## Overall Biocompatibility Conclusion
Based on the ISO 10993 biological evaluation, [device name] is [INSERT: biocompatible/not biocompatible] for its intended use with [INSERT: contact type and duration].

[CITATION NEEDED: Biocompatibility evaluation report]
```

---

### Section: `cover-letter`

**21 CFR 814.20(a)** — Cover letter requirements:

```markdown
# PMA Cover Letter

[Date]

Food and Drug Administration
Center for Devices and Radiological Health
Document Mail Center — W066-G609
10903 New Hampshire Avenue
Silver Spring, MD 20993-0002

**Re:** Premarket Approval Application for [Device Name]
**21 CFR Part:** [814.20]
**Product Code:** [product_code]
**Regulation:** [regulation_number]

Dear [INSERT: Division Director or To Whom It May Concern]:

[INSERT: Company name] submits this Premarket Approval Application (PMA) for [device name], a [device type] device intended for [brief intended use].

This submission includes:

- [ ] PMA Application Form (FDA Form 3514)
- [ ] Table of Contents
- [ ] Device Description (21 CFR 814.20(b)(3))
- [ ] Proposed Labeling (21 CFR 814.20(b)(10))
- [ ] Manufacturing Information (21 CFR 814.20(b)(4))
- [ ] Summary of Safety and Effectiveness Data (21 CFR 814.20(b)(6))
- [ ] Clinical Studies Section (21 CFR 814.20(b)(6)(ii))
- [ ] Non-Clinical Studies (21 CFR 814.20(b)(6)(i))
- [ ] Truthful and Accuracy Statement (21 CFR 814.20(b)(12))
- [ ] Financial Certification or Disclosure (21 CFR Part 54)

[INSERT: Note any pending items, companion submissions, or pre-submission meeting references]

If you have questions regarding this submission, please contact:

[INSERT: Regulatory Affairs contact name, title, phone, email]

Respectfully submitted,

[INSERT: Authorized representative name and title]
[INSERT: Company name]
[INSERT: Address]

---

*This PMA application has been prepared in accordance with 21 CFR Part 814 and applicable FDA guidance documents.*
```

---

### Section: `summary`

**21 CFR 814.9** — PMA Summary (publicly releasable):

```markdown
# PMA Summary

**Device:** [Device Name]
**Applicant:** [INSERT: Company]
**Address:** [INSERT]
**Date of Decision:** [To be completed]
**Decision:** Approved / Not Approved

## Indications for Use

[indications_for_use]

## Device Description

[Brief 2-3 paragraph device description — this is the publicly released version]

## Preclinical Studies

Summary of non-clinical testing:
- [INSERT: Key bench tests and pass/fail results]
- [INSERT: Animal study conclusions if applicable]

## Clinical Studies

**Study design:** [INSERT]
**Primary endpoint:** [INSERT] — Result: [INSERT]
**Safety:** [INSERT: SAE summary]

## Summary of Reasons for Approval

The PMA is approved because:
1. There is reasonable assurance that the device is safe under the conditions of use prescribed, recommended, or suggested in its labeling.
2. There is reasonable assurance that the device is effective under such conditions of use.
3. The proposed labeling is not false or misleading.

[TODO: Populate with actual approval rationale post-approval]
```

---

## Step 2: Write Output

After generating the draft:

```bash
python3 << 'PYEOF'
import os, json
from datetime import datetime

proj_dir = os.environ.get('PROJECT_DIR', '.')
section = "$SECTION_NAME"
filename = f"pma_draft_{section}.md"
output_path = os.path.join(proj_dir, filename)

# Check for --output override
custom_output = "$OUTPUT_FILE"
if custom_output and custom_output != "$OUTPUT_FILE":
    output_path = custom_output

print(f"OUTPUT_PATH:{output_path}")
print(f"TIMESTAMP:{datetime.now().isoformat()}")
PYEOF
```

Write the generated draft to the output path. Then report:

```
✓ PMA Draft Generated: pma_draft_{section}.md
  Section: {section} (21 CFR {cfr_reference})
  Words: {word_count}
  [TODO:] items: {todo_count}
  [INSERT:] items: {insert_count}
  [CITATION NEEDED]: {citation_count}

⚠ This draft requires population with actual clinical/test data before submission.
  Run /fda:pma-intelligence --pma {pma_number} to load comparable PMA data.

Next steps:
  → Fill [INSERT:] items with actual values from your study reports
  → Resolve [TODO:] items with your RA professional
  → Add [CITATION NEEDED] source references
  → Run /fda:pma-draft summary to generate the public-facing PMA Summary
```

## Step 3: Generate All Sections (if `--all` flag)

If `--all` is specified, generate all mandatory sections in order:
1. `cover-letter`
2. `device-description`
3. `manufacturing`
4. `preclinical`
5. `biocompatibility`
6. `clinical`
7. `ssed`
8. `labeling` (report as requiring manual input — labeling is device-specific)
9. `risk-analysis`
10. `summary`
11. `truthful-accuracy`

Report progress as each section completes.

## Error Handling

- **Section not recognized**: List valid sections and suggest closest match
- **Project not found**: "Project '{name}' not found. Run `/fda:pma-search --product-code {CODE}` first."
- **No PMA data**: Warn and generate with full placeholders. Include note that precedent analysis is unavailable.
- **Revise mode**: Preserve all user text between `<!-- USER EDIT START -->` and `<!-- USER EDIT END -->` markers. Only regenerate AI-generated template content.
