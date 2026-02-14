---
description: Simulate an FDA review team's evaluation of your 510(k) submission — identifies likely deficiencies, screens against RTA checklist, and generates a submission readiness score
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch, WebSearch
argument-hint: "--project NAME [--depth quick|standard|deep] [--focus predicate|testing|labeling|clinical|all]"
---

# FDA Pre-Check: Review Simulation

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

You are simulating an FDA CDRH review team's evaluation of a 510(k) submission. Using the organizational structure, review processes, and deficiency patterns from `references/cdrh-review-structure.md`, generate a realistic assessment of submission readiness from the perspective of FDA reviewers.

**KEY PRINCIPLE: Think like an FDA reviewer, not a regulatory consultant.** Identify what would cause an AI (Additional Information) request, an RTA (Refuse to Accept) decision, or an NSE (Not Substantially Equivalent) determination. Be thorough and conservative — FDA reviewers err on the side of requesting more data.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--project NAME` (required) — Project to evaluate
- `--product-code CODE` (optional) — Product code; auto-detect from project data if not specified
- `--depth quick|standard|deep` (default: standard)
  - `quick` — RTA checklist screening only
  - `standard` — RTA + lead reviewer + specialist reviewers
  - `deep` — standard + predicate chain + guidance compliance + competitive context
- `--focus predicate|testing|labeling|clinical|all` (default: all)
- `--infer` — Auto-detect product code from project data
- `--output FILE` — Write report to file (default: pre_check_report.md in project folder)
- `--full-auto` — Never prompt the user

**Validation:**
- If `--project` missing and NOT `--full-auto`: ask the user for a project name
- If `--project` missing and `--full-auto`: **ERROR**: "In --full-auto mode, --project is required."

## Step 1: Gather Project Data

### Resolve project directory

```bash
PROJECTS_DIR=$(python3 -c "
import os, re
settings = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
if os.path.exists(settings):
    with open(settings) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m:
            print(os.path.expanduser(m.group(1).strip()))
            exit()
print(os.path.expanduser('~/fda-510k-data/projects'))
")
echo "PROJECTS_DIR=$PROJECTS_DIR"
```

### Inventory all project files

```bash
python3 << 'PYEOF'
import os, json, glob

project_dir = os.path.expanduser("~/fda-510k-data/projects/PROJECT")  # Replace

files = {
    "review.json": os.path.exists(os.path.join(project_dir, "review.json")),
    "query.json": os.path.exists(os.path.join(project_dir, "query.json")),
    "output.csv": os.path.exists(os.path.join(project_dir, "output.csv")),
    "presub_plan.md": os.path.exists(os.path.join(project_dir, "presub_plan.md")),
    "submission_outline.md": os.path.exists(os.path.join(project_dir, "submission_outline.md")),
    "test_plan.md": os.path.exists(os.path.join(project_dir, "test_plan.md")),
    "traceability_matrix.md": os.path.exists(os.path.join(project_dir, "traceability_matrix.md")),
    "fda_correspondence.json": os.path.exists(os.path.join(project_dir, "fda_correspondence.json")),
}

# Check for draft sections
drafts_dir = os.path.join(project_dir, "drafts")
if os.path.isdir(drafts_dir):
    drafts = [f for f in os.listdir(drafts_dir) if f.startswith("draft_") and f.endswith(".md")]
    files["drafts"] = drafts
else:
    files["drafts"] = []

# Check for guidance cache
gc_dir = os.path.join(project_dir, "guidance_cache")
files["guidance_cache"] = os.path.isdir(gc_dir) and bool(os.listdir(gc_dir))

# Check for safety cache
sc_dir = os.path.join(project_dir, "safety_cache")
files["safety_cache"] = os.path.isdir(sc_dir) and bool(os.listdir(sc_dir))

# Check for SE comparison
se_files = glob.glob(os.path.join(project_dir, "se_comparison*"))
files["se_comparison"] = len(se_files) > 0

for k, v in files.items():
    print(f"FILE:{k}={v}")
PYEOF
```

### Load review.json (predicates)

```bash
cat "$PROJECTS_DIR/$PROJECT_NAME/review.json" 2>/dev/null || echo "REVIEW_DATA:not_found"
```

### Determine product code

If `--product-code` not specified:
1. Check `query.json` for `product_codes` field
2. Check `review.json` for predicate product codes
3. If `--infer`: use the most common product code from available data
4. If none found: **ERROR**: "Could not determine product code. Provide --product-code CODE."

## Step 2: Determine Review Team

Using the product code, query openFDA for classification data:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
api_enabled = True
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)
    m = re.search(r'openfda_enabled:\s*(\S+)', content)
    if m and m.group(1).lower() == 'false':
        api_enabled = False

product_code = "PRODUCTCODE"  # Replace

if api_enabled:
    params = {"search": f'product_code:"{product_code}"', "limit": "100"}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/classification.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.3.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            total = data.get("meta", {}).get("results", {}).get("total", 0)
            print(f"CLASSIFICATION_MATCHES:{total}")
            if data.get("results"):
                r = data["results"][0]
                print(f"DEVICE_NAME:{r.get('device_name', 'N/A')}")
                print(f"DEVICE_CLASS:{r.get('device_class', 'N/A')}")
                print(f"REGULATION:{r.get('regulation_number', 'N/A')}")
                print(f"PANEL:{r.get('review_panel', 'N/A')}")
                print(f"PANEL_DESC:{r.get('medical_specialty_description', 'N/A')}")
    except Exception as e:
        print(f"API_ERROR:{e}")
PYEOF
```

### Map to OHT and Division

Use the `review_panel` → OHT mapping from `references/cdrh-review-structure.md` Section 1:

```python
PANEL_TO_OHT = {
    "AN": "OHT1", "DE": "OHT1", "EN": "OHT1", "OP": "OHT1",
    "CV": "OHT2",
    "GU": "OHT3", "HO": "OHT3", "OB": "OHT3",
    "SU": "OHT4",
    "NE": "OHT5", "PM": "OHT5",
    "OR": "OHT6",
    "CH": "OHT7", "HE": "OHT7", "IM": "OHT7", "MI": "OHT7", "PA": "OHT7", "TX": "OHT7",
    "RA": "OHT8",
}
```

### Identify specialist reviewers

Apply the decision tree from `references/cdrh-review-structure.md` Section 2:

Analyze the device description and project data to determine which specialists would be assigned:
- Check for patient-contacting materials → Biocompatibility reviewer
- Check for software components → Software reviewer
- Check for sterile device → Sterilization reviewer
- Check for electrical/powered device → Electrical/EMC reviewer
- Check for user interface/home use → Human Factors reviewer
- Check for implantable/metallic → MRI Safety reviewer
- Check for reusable device → Reprocessing reviewer
- Check for clinical data → Clinical reviewer

### Device Classification Edge Cases

**Unclassified Devices (Class U)**: If `device_class` = "U" or regulation_number is empty/missing:
- Do NOT flag missing regulation number as a deficiency — Class U devices legitimately have no 21 CFR regulation number
- Note "Unclassified" status in the review team section rather than leaving regulation blank
- Class U devices are typically cleared under general controls only; do not require Class III certification or special controls documentation
- The RTA check for Class III Certification (RTA-06) should auto-pass as N/A for Class U devices

**Combination Products** (device_description or classification_device_name mentions "drug" or active pharmaceutical ingredient):
- Flag that 21 CFR Part 3/4 PMOA determination is relevant
- Note that CDER or CBER may also have review jurisdiction
- Sterilization reviewer may not apply if product is a non-sterile topical solution
- Biocompatibility review should include drug component toxicity assessment

## Step 3: RTA Screening

**This step runs at all `--depth` levels including `quick`.**

Walk through the RTA checklist from `references/cdrh-review-structure.md` Section 3:

### Administrative RTA Items

For each RTA criterion, check project data:

```python
rta_items = [
    {"id": "RTA-01", "item": "Cover letter", "check": "draft_cover-letter.md in drafts", "required": True},
    {"id": "RTA-02", "item": "FDA Form 3514 (Cover Sheet)", "check": "referenced in cover letter", "required": True},
    {"id": "RTA-03", "item": "Indications for Use (Form 3881)", "check": "draft_form-3881.md in drafts OR estar/03_510kSummary/form_3881.md — IFU text in device_profile.json alone is NOT sufficient", "required": True},
    {"id": "RTA-04", "item": "510(k) Summary or Statement", "check": "draft_510k-summary.md in drafts", "required": True},
    {"id": "RTA-05", "item": "Truthful and Accuracy Statement", "check": "draft_truthful-accuracy.md in drafts", "required": True},
    {"id": "RTA-06", "item": "Class III Certification", "check": "only if Class III", "required": "conditional"},
    {"id": "RTA-07", "item": "Financial Certification", "check": "draft_financial-certification.md if clinical", "required": "conditional"},
    {"id": "RTA-08", "item": "Declarations of Conformity", "check": "draft_doc.md if standards cited", "required": "conditional"},
    {"id": "RTA-09", "item": "Device description", "check": "draft_device-description.md or --device-description", "required": True},
    {"id": "RTA-10", "item": "SE comparison", "check": "se_comparison file or draft_se-discussion.md", "required": True},
    {"id": "RTA-11", "item": "Proposed labeling", "check": "draft_labeling.md", "required": True},
    {"id": "RTA-12", "item": "Performance data", "check": "test_plan.md or draft_performance-summary.md", "required": True},
    {"id": "RTA-13", "item": "Sterility information", "check": "draft_sterilization.md if sterile", "required": "conditional"},
    {"id": "RTA-14", "item": "Biocompatibility", "check": "draft_biocompatibility.md if patient-contacting", "required": "conditional"},
    {"id": "RTA-15", "item": "Software documentation", "check": "draft_software.md if software device", "required": "conditional"},
    {"id": "RTA-16", "item": "EMC/Electrical safety", "check": "draft_emc-electrical.md if powered", "required": "conditional"},
]
```

Report RTA screening result:

```markdown
RTA SCREENING
────────────────────────────────────────

  | # | Item | Status | Note |
  |---|------|--------|------|
  | RTA-01 | Cover letter | ✓ Present | draft_cover-letter.md |
  | RTA-02 | FDA Form 3514 | ○ Not checked | Reference in cover letter |
  | RTA-09 | Device description | ✗ MISSING | No draft_device-description.md found |
  ...

  Result: {PASS / FAIL — {N} required items missing}
```

### eSTAR Mandatory Section Completeness

In addition to RTA items, verify that all mandatory eSTAR sections have draft content:

```python
mandatory_sections = [
    {"section": "01", "name": "Cover Letter", "file": "draft_cover-letter.md", "always": True},
    {"section": "03", "name": "510(k) Summary", "file": "draft_510k-summary.md", "always": True},
    {"section": "04", "name": "Truthful & Accuracy", "file": "draft_truthful-accuracy.md", "always": True},
    {"section": "06", "name": "Device Description", "file": "draft_device-description.md", "always": True},
    {"section": "07", "name": "SE Comparison", "file": "draft_se-discussion.md", "always": True},
    {"section": "09", "name": "Labeling", "file": "draft_labeling.md", "always": True},
    {"section": "15", "name": "Performance Testing", "file": "draft_performance-summary.md", "always": True},
]
```

For each mandatory section, check:
1. Does the draft file exist in the project directory?
2. If not, does an alternative exist? (e.g., `se_comparison.md` for Section 07, `test_plan.md` for Section 15)
3. If missing: flag as **CRITICAL** deficiency — "eSTAR Section {##} ({name}) has no content. This will result in RTA."

Report:
```markdown
eSTAR SECTION COMPLETENESS
────────────────────────────────────────

  | # | Section | Status | Source |
  |---|---------|--------|--------|
  | 01 | Cover Letter | ✓ / ✗ | {file or MISSING} |
  | 03 | 510(k) Summary | ✓ / ✗ | {file or MISSING} |
  ...

  Mandatory sections present: {N}/7
```

**If `--depth quick`: Stop here.** Report the RTA result and exit.

## Step 4: Lead Reviewer Evaluation

**This step runs at `--depth standard` and `--depth deep`.**

Simulate the lead reviewer's assessment:

### 4a. Predicate Appropriateness

Load accepted predicates from review.json. For each predicate, assess:

1. **Same intended use?** — Compare subject IFU against predicate IFU (if available)
2. **Same product code?** — Verify product code match
3. **Predicate still valid?** — Check for recalls, age, decision type
4. **Predicate chain healthy?** — If `--depth deep`, trace 2-generation chain

Generate predicate assessment:
```markdown
LEAD REVIEWER — PREDICATE ASSESSMENT
────────────────────────────────────────

  Primary Predicate: {K-number} ({device_name})
  ✓ Same intended use: {assessment}
  ✓ Same product code: {CODE}
  ⚠ Predicate age: {N} years — {assessment}
  ✓ No recalls
  Predicate assessment: ACCEPTABLE / QUESTIONABLE / INAPPROPRIATE
```

### 4b. SE Comparison Adequacy

Check if SE comparison exists (from `/fda:compare-se`):
- If SE comparison file exists: Read it and assess completeness
- If no SE comparison: Flag as CRITICAL deficiency

Assess:
- All required rows present for device type?
- Subject device column filled in?
- "Different" entries have justification?
- Missing data cells?

### 4c. Intended Use Assessment

Compare the subject device's intended use against:
- Predicate IFU (keyword overlap)
- Device classification definition
- Special controls (if Class II)

Flag:
- IFU broader than predicate → MAJOR deficiency
- IFU broader than classification → CRITICAL deficiency
- IFU unclear or missing → CRITICAL deficiency (RTA)

### 4d. Brand Name Mismatch Detection

Compare the `applicant` field (from device_profile.json, import_data.json, or review.json) against company/brand names found in `intended_use`, `device_description`, and all draft files.

**Known company names to check:** `KARL STORZ`, `Boston Scientific`, `Medtronic`, `Abbott`, `Johnson & Johnson`, `Ethicon`, `Stryker`, `Zimmer Biomet`, `Smith & Nephew`, `B. Braun`, `Cook Medical`, `Edwards Lifesciences`, `Becton Dickinson`, `BD`, `Baxter`, `Philips`, `GE Healthcare`, `Siemens Healthineers`, `Olympus`, `Hologic`, `Intuitive Surgical`, `Teleflex`, `ConvaTec`, `Coloplast`, `3M Health Care`, `Cardinal Health`, `Danaher`, `Integra LifeSciences`, `NuVasive`, `Globus Medical`, `DePuy Synthes`

**Detection logic:**
1. Extract applicant name from project data
2. For each known company name, if it appears in the subject device data AND does not match the applicant:
   - Check context: predicate reference (acceptable) vs subject device attribution (CRITICAL)
   - Predicate context: "compared to", "predicate", "reference device", "{K-number}"
   - Subject context: IFU text, device description without predicate context, labeling body text
3. Flag:
   - **CRITICAL**: Competitor brand `{company}` appears as subject device manufacturer in `{file}`. Likely peer-mode data leakage.
   - Simulated AI request: `"The Indications for Use statement references '{company}' which does not match the applicant '{applicant}'. Please clarify the relationship between the applicant and the device manufacturer."`
   - Remediation: `"Review all draft files and replace competitor brand references with your company name. Consider re-running /fda:draft with the --device-description and --intended-use flags to override peer data."`

### 4e. Compatible Equipment Check

Detect keywords indicating the device requires compatible equipment: "generator", "console", "controller", "power supply", "light source", "camera head", "processor", "power unit", "energy source".

**If compatible equipment keywords detected in device description or se_comparison:**
1. Check if the specific equipment is identified (model number, specifications, or at minimum a category)
2. Check if equipment compatibility is addressed in labeling (`draft_labeling.md`)
3. Check if performance testing references the compatible equipment

**Flag:**
- **MAJOR**: Device requires compatible equipment but no specific equipment identified in project data. "Device description references {keyword} but compatible equipment specifications are not documented. FDA will request equipment compatibility information."
- **MINOR**: Equipment identified in description but missing from labeling or testing

### 4f. Shelf Life Claim Verification

Detect shelf life claims in project data: scan `se_comparison.md`, `device_profile.json`, `draft_labeling.md`, `import_data.json` for patterns like "shelf life", "expiration", "dating", "X years", "X months".

**If shelf life claim detected:**
1. Check for `drafts/draft_shelf-life.md`:
   - If missing: **CRITICAL** — "Shelf life of '{claim}' claimed but no shelf life section drafted. Run: /fda:draft shelf-life --project NAME"
   - If exists but all [TODO]: **MAJOR** — "Shelf life section exists but contains only placeholder content"
2. Check for `calculations/shelf_life_*.json`:
   - If missing: **MAJOR** — "No accelerated aging calculation found. Run: /fda:calc shelf-life --project NAME"
3. Check for ASTM F1980 reference in any draft:
   - If missing: **MINOR** — "No ASTM F1980 reference found in shelf life documentation"

**If no shelf life claim detected:** No flag (shelf life may not be applicable).

## Step 5: Specialist Reviewer Evaluations

**For each specialist reviewer identified in Step 2:**

### Biocompatibility Review

If Biocompatibility reviewer assigned:
- Check for `draft_biocompatibility.md`
- **Content adequacy**: If file exists, check that it lists specific patient-contacting materials (not just `[TODO: specify materials]`). A biocompatibility section that doesn't enumerate actual materials is incomplete.
- Check for material characterization in device description
- Identify required ISO 10993 tests based on contact type and duration
- Flag missing tests as MAJOR deficiency
- Flag file with no specific materials listed as MAJOR deficiency: "Biocompatibility section exists but does not specify materials of construction"

### Software Review

If Software reviewer assigned:
- Check for `draft_software.md`
- **Content adequacy**: If file exists, verify it specifies an IEC 62304 classification level (Class A/B/C), not just `[TODO: determine level]`
- Check for cybersecurity documentation
- Look for IEC 62304 references
- Flag missing documentation level as MAJOR deficiency

### Sterilization Review

If Sterilization reviewer assigned:
- Check for `draft_sterilization.md`
- **Content adequacy**: If file exists, verify it specifies a concrete sterilization method (EO, radiation, steam, etc.), not just `[TODO: EO or Radiation]` or similar placeholder. A sterilization section without a determined method is incomplete.
- Verify sterilization method specified
- Check for SAL reference
- Flag missing validation plan as MAJOR deficiency
- Flag file with placeholder-only method as MAJOR deficiency: "Sterilization section exists but method is not determined — still shows [TODO]"

### Electrical/EMC Review

If Electrical/EMC reviewer assigned:
- Check for `draft_emc-electrical.md`
- **Content adequacy**: If file exists, verify it references specific IEC 60601-1 edition and applicable particular standards
- Verify IEC 60601-1 referenced
- Check for EMC testing per IEC 60601-1-2
- Flag missing test reports as MAJOR deficiency

### Human Factors Review

If Human Factors reviewer assigned:
- Check for human factors data in project
- **Content adequacy**: If file exists, verify it identifies specific critical tasks and user groups, not just template placeholders
- Verify IEC 62366-1 referenced
- Check for use-related risk analysis
- Flag missing usability testing as MAJOR deficiency

### Reprocessing Review

If Reprocessing reviewer assigned (auto-trigger: device_description contains "reusable", "reprocessing", "autoclave", "multi-use", "non-disposable", "endoscope", "instrument tray", OR sterilization_method is "steam" for facility-sterilized devices):
- Check for `draft_reprocessing.md`
- **Content adequacy**: If file exists, verify it specifies cleaning validation methodology (not just [TODO: method]), lists acceptance criteria, and references AAMI TIR30 or equivalent
- Check for lifecycle/durability testing documentation (repeated reprocessing cycles)
- Check for reprocessing IFU in labeling section
- Flag missing cleaning validation as MAJOR deficiency
- Flag missing lifecycle testing as MAJOR deficiency
- Flag file with placeholder-only content as MAJOR deficiency: "Reprocessing section exists but validation methodology not determined"

**Review template:**
```
Reprocessing Reviewer Assessment:
  □ Cleaning validation per AAMI TIR30
  □ Worst-case soil challenge identified
  □ Acceptance criteria for protein/hemoglobin/endotoxin residuals
  □ Disinfection/sterilization between uses validated
  □ Lifecycle testing (N reprocessing cycles without degradation)
  □ Reprocessing IFU present in labeling
  □ Drying validation (if device has lumens/channels)
```

### Combination Product Review

If Combination Product reviewer assigned (auto-trigger: device_description or classification_device_name contains "drug", "pharmaceutical", "active ingredient", "drug-eluting", "antimicrobial agent", "medicated", "drug-device", "combination product", "OTC drug", "Drug Facts", "active pharmaceutical"):
- Check for `draft_combination-product.md`
- **PMOA determination**: Verify Primary Mode of Action is stated. PMOA missing = **CRITICAL** deficiency
- Check for drug component characterization (drug name, concentration, release kinetics)
- Check for drug-device interaction testing documentation
- If OTC device: check for OTC Drug Facts panel in labeling
- Flag missing PMOA as CRITICAL deficiency: "Combination product identified but no PMOA determination found. This is required per 21 CFR Part 3."
- Flag missing drug characterization as MAJOR deficiency

**Review template:**
```
Combination Product Reviewer Assessment:
  □ PMOA determination (device/drug/biologic)
  □ Lead center assignment (CDRH/CDER/CBER)
  □ Drug component characterized (name, concentration, class)
  □ Drug-device interaction testing
  □ Drug release kinetics/elution profile
  □ 21 CFR Part 3/4 compliance documented
  □ OTC Drug Facts panel (if OTC)
  □ cGMP for drug component (21 CFR 211)
```

### Clinical Review

If Clinical reviewer assigned:
- Check for clinical data in project (literature, study)
- **Content adequacy**: If `draft_clinical.md` exists, verify it contains either a literature summary with specific references or a study design — not just a template skeleton
- Verify study design adequacy (if clinical study)
- Check for financial certification
- Flag missing clinical evidence as CRITICAL deficiency (if required)

### MRI Safety Review

If MRI Safety reviewer assigned:
- Check for MRI safety testing references
- Verify ASTM standards cited
- Check for MR Conditional/Unsafe labeling
- Flag missing MRI testing as MAJOR deficiency

## Step 6: Generate Deficiency Report

Compile all findings into a structured report:

### Deficiency Severity Levels

| Severity | Definition | Impact |
|----------|-----------|--------|
| **CRITICAL** | Would result in RTA or NSE | Must fix before submission |
| **MAJOR** | Would result in AI request | Should fix before submission |
| **MINOR** | Would be noted but not block clearance | Fix if time allows |

### Deficiency Structure

For each deficiency:
```json
{
    "id": "DEF-001",
    "severity": "CRITICAL|MAJOR|MINOR",
    "reviewer": "Lead Reviewer|Biocompatibility|Software|...",
    "finding": "Description of the deficiency",
    "likely_ai_request": "Simulated FDA AI request text",
    "recommendation": "Specific action to remediate",
    "remediation_command": "/fda:draft device-description --project NAME"
}
```

## Step 7: Calculate Submission Readiness Index (SRI)

Use the scoring system from `references/cdrh-review-structure.md` Section 8:

```python
import re

def count_todo_markers(file_path):
    """Count [TODO markers in a file. Returns count or -1 if file not found."""
    try:
        with open(file_path) as f:
            text = f.read()
        return len(re.findall(r'\[TODO', text))
    except FileNotFoundError:
        return -1

def check_content_adequacy(project_dir, drafts):
    """Score content adequacy — penalize files that are mostly TODO placeholders.
    Returns a score from 0 to 15."""
    adequacy_score = 0

    # SE comparison has subject device column with real values (not all [TODO]): +5 pts
    se_path = os.path.join(project_dir, 'se_comparison.md')
    if os.path.exists(se_path):
        with open(se_path) as f:
            se_text = f.read()
        # Count subject device cells that are real values vs [TODO]
        todo_cells = len(re.findall(r'\[TODO[:\s]', se_text))
        total_rows = len(re.findall(r'^\|', se_text, re.MULTILINE))
        if total_rows > 0 and todo_cells < total_rows * 0.5:
            adequacy_score += 5  # Majority of cells have real data
        elif total_rows > 0 and todo_cells < total_rows * 0.8:
            adequacy_score += 2  # Some cells have real data
        # else: 0 pts — mostly placeholders

    # Sterilization section specifies a method (not [TODO: EO or Radiation]): +3 pts
    steril_path = os.path.join(project_dir, 'drafts', 'draft_sterilization.md')
    if os.path.exists(steril_path):
        with open(steril_path) as f:
            steril_text = f.read()
        # Match method in natural prose: "method is steam", "method: EO", "steam sterilization"
        has_method = bool(re.search(
            r'(?:method\b.*?\b(?:is|:)\s*(?:ethylene oxide|EO|gamma|e-beam|radiation|steam|autoclave|moist heat))|(?:(?:steam|EO|ethylene oxide|gamma|e-beam|radiation)\s+sterilization)',
            steril_text, re.I
        ))
        # Only match TODOs where the METHOD ITSELF is undetermined (not TODOs about parameters)
        has_todo_method = bool(re.search(
            r'\[TODO[^]]*(?:EO or (?:Radiation|radiation)|specify (?:sterilization )?method|determine (?:sterilization )?method)',
            steril_text, re.I
        ))
        if has_method and not has_todo_method:
            adequacy_score += 3

    # DoC lists all required standards from standards_lookup.json: +3 pts
    std_lookup = os.path.join(project_dir, 'standards_lookup.json')
    doc_path = os.path.join(project_dir, 'drafts', 'draft_doc.md')
    if os.path.exists(std_lookup) and os.path.exists(doc_path):
        with open(std_lookup) as f:
            lookup_data = json.load(f)
        with open(doc_path) as f:
            doc_text = f.read()
        # Count how many standards from lookup appear in DoC
        lookup_standards = set()
        if isinstance(lookup_data, list):
            for item in lookup_data:
                std_num = item.get('standard_number', '') or item.get('standard', '')
                if std_num:
                    lookup_standards.add(std_num.upper().split(':')[0])
        elif isinstance(lookup_data, dict):
            for key in lookup_data:
                lookup_standards.add(key.upper().split(':')[0])
        doc_upper = doc_text.upper()
        matched = sum(1 for s in lookup_standards if s in doc_upper)
        if lookup_standards and matched >= len(lookup_standards) * 0.8:
            adequacy_score += 3
        elif lookup_standards and matched >= len(lookup_standards) * 0.5:
            adequacy_score += 1

    # Biocompatibility section lists specific materials: +2 pts
    biocompat_path = os.path.join(project_dir, 'drafts', 'draft_biocompatibility.md')
    if os.path.exists(biocompat_path):
        with open(biocompat_path) as f:
            bio_text = f.read()
        material_mentions = re.findall(
            r'(PTFE|FEP|PEEK|stainless steel|titanium|nitinol|silicone|polyurethane|polycarbonate|nylon)',
            bio_text, re.I
        )
        if len(set(m.lower() for m in material_mentions)) >= 1:
            adequacy_score += 2

    # Performance section has acceptance criteria: +2 pts
    perf_path = os.path.join(project_dir, 'drafts', 'draft_performance-summary.md')
    if os.path.exists(perf_path):
        with open(perf_path) as f:
            perf_text = f.read()
        has_criteria = bool(re.search(r'acceptance criteria|pass.?fail|success criteria', perf_text, re.I))
        if has_criteria:
            adequacy_score += 2

    return adequacy_score

def calculate_readiness_score(rta_result, predicate_scores, se_comparison,
                              testing_coverage, deficiencies, drafts,
                              project_dir=None):
    score = 0

    # RTA completeness (25 pts) — with TODO penalty
    rta_present = sum(1 for item in rta_result if item["status"] == "present")
    rta_required = sum(1 for item in rta_result if item["required"])
    rta_base = 25 * (rta_present / max(rta_required, 1))

    # TODO penalty: if critical files have excessive [TODO] markers, cap RTA score
    if project_dir:
        critical_files = [
            os.path.join(project_dir, 'drafts', 'draft_device-description.md'),
            os.path.join(project_dir, 'se_comparison.md'),
            os.path.join(project_dir, 'drafts', 'draft_labeling.md'),
        ]
        high_todo_count = 0
        for cf in critical_files:
            todo_count = count_todo_markers(cf)
            if todo_count > 3:
                high_todo_count += 1
        if high_todo_count >= 2:
            rta_base = min(rta_base, 15)  # Cap at 15 if multiple critical files are TODO-heavy
    score += rta_base

    # Predicate quality (20 pts)
    if predicate_scores:
        avg_score = sum(predicate_scores) / len(predicate_scores)
        score += avg_score * 0.2

        # Predicate PDF availability penalty:
        # If source_device_text_*.txt is missing or <500 bytes for any accepted predicate, apply -5 penalty
        if project_dir:
            import glob as g
            source_texts = g.glob(os.path.join(project_dir, 'source_device_text_*.txt'))
            has_adequate_source = False
            for st in source_texts:
                if os.path.getsize(st) >= 500:
                    has_adequate_source = True
                    break
            if not has_adequate_source and source_texts:
                score -= 5  # Stub source text penalty
            elif not source_texts:
                score -= 5  # No source text at all penalty
    # else: 0 pts

    # SE comparison (15 pts)
    if se_comparison == "complete":
        score += 15
    elif se_comparison == "partial":
        score += 8

    # Content Adequacy (15 pts) — checks actual content quality
    if project_dir:
        adequacy_pts = check_content_adequacy(project_dir, drafts)

        # [TODO] density penalty: count [TODO] items across all drafts
        # If >50% of a section is TODO: -1pt; if >80%: -2pt
        drafts_path = os.path.join(project_dir, 'drafts')
        todo_penalty = 0
        if os.path.isdir(drafts_path):
            for df in os.listdir(drafts_path):
                if df.startswith('draft_') and df.endswith('.md'):
                    fpath = os.path.join(drafts_path, df)
                    with open(fpath) as f:
                        text = f.read()
                    lines = [l for l in text.split('\n') if l.strip() and not l.startswith('#') and not l.startswith('⚠') and not l.startswith('Generated')]
                    if len(lines) > 5:  # Only penalize files with meaningful content
                        todo_lines = sum(1 for l in lines if '[TODO' in l)
                        ratio = todo_lines / len(lines) if lines else 0
                        if ratio > 0.8:
                            todo_penalty += 2
                        elif ratio > 0.5:
                            todo_penalty += 1

        adequacy_pts = max(0, adequacy_pts - min(todo_penalty, 5))  # Cap penalty at 5 pts
        score += adequacy_pts
    # else: 0 pts

    # Deficiency penalty (15 pts)
    # NOTE: For Class U (unclassified) devices, do NOT count missing regulation number
    # as a deficiency. Filter out any deficiency about "missing regulation" if device_class == "U".
    critical_count = sum(1 for d in deficiencies if d["severity"] == "CRITICAL")
    major_count = sum(1 for d in deficiencies if d["severity"] == "MAJOR")
    penalty = min(15, 3 * critical_count + 1 * major_count)
    score += 15 - penalty

    # Documentation quality (10 pts) — reduced from 15 since Content Adequacy now has 15
    if drafts:
        expected_sections = ["device-description", "se-discussion", "510k-summary",
                            "labeling", "cover-letter", "truthful-accuracy"]
        present = sum(1 for s in expected_sections
                     if any(s in d for d in drafts))
        score += 10 * (present / len(expected_sections))

    return round(score)
```

### Score Breakdown (100 points total)

| Component | Points | Description |
|-----------|--------|-------------|
| RTA completeness | 25 | Required files present; capped at 15 if critical files are TODO-heavy |
| Predicate quality | 20 | Average predicate confidence score |
| SE comparison | 15 | Complete (15), partial (8), or missing (0) |
| **Content adequacy** | **15** | **NEW: Checks that content has real data, not just placeholders** |
| Deficiency penalty | 15 | Minus 3 per CRITICAL, minus 1 per MAJOR |
| Documentation | 10 | Core sections present |

## Step 8: Write Report

Write `pre_check_report.md` to the project folder:

```markdown
  FDA Pre-Check Report
  {project_name} — {device_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.22.0
  Depth: {quick|standard|deep}
  Focus: {predicate|testing|labeling|clinical|all}

REVIEW TEAM IDENTIFIED
────────────────────────────────────────

  OHT: {OHT number} — {office name}
  Division: {division}
  Review Panel: {panel} ({panel_description})

  | Reviewer | Trigger | Focus |
  |----------|---------|-------|
  | Lead Reviewer | Always | SE determination |
  | Team Lead | Always | Policy, risk |
  | Labeling | Always | 21 CFR 801, IFU |
  | {Specialist} | {Trigger} | {Focus} |
  ...

RTA SCREENING
────────────────────────────────────────

  | # | Item | Status | Note |
  |---|------|--------|------|
  | RTA-01 | Cover letter | ✓ / ✗ | {note} |
  ...

  RTA Result: {PASS / FAIL}
  {If FAIL: "Submission would be refused. Address missing items before submitting."}

{If --depth standard or deep:}

LEAD REVIEWER EVALUATION
────────────────────────────────────────

  Predicate: {K-number} — {assessment}
  SE Comparison: {Complete / Partial / Missing}
  Intended Use: {Matched / Broader / Missing}

SPECIALIST REVIEWS
────────────────────────────────────────

  {For each specialist:}
  {Reviewer Name}:
    {finding summary}
    {deficiency if applicable}

SIMULATED DEFICIENCIES
────────────────────────────────────────

  | # | Severity | Reviewer | Finding | Remediation |
  |---|----------|----------|---------|-------------|
  | DEF-001 | CRITICAL | Lead | {finding} | {command} |
  | DEF-002 | MAJOR | Biocompat | {finding} | {command} |
  | DEF-003 | MINOR | Labeling | {finding} | {command} |

  Summary: {N} CRITICAL, {N} MAJOR, {N} MINOR

{For each CRITICAL and MAJOR deficiency:}

  DEF-001 [CRITICAL] — {reviewer}
  Finding: {detailed description}
  Likely AI Request:
    "{Simulated FDA AI request text from cdrh-review-structure.md templates}"
  Recommendation: {action}
  Remediation: {/fda: command}

SUBMISSION READINESS INDEX (SRI)
────────────────────────────────────────

  SRI: {N}/100 — {Ready / Nearly Ready / Significant Gaps / Not Ready / Early Stage}

  | Component | Score | Max | Notes |
  |-----------|-------|-----|-------|
  | RTA completeness | {N} | 25 | {N}/{M} required items (capped if TODO-heavy) |
  | Predicate quality | {N} | 20 | Avg confidence: {N}/100 |
  | SE comparison | {N} | 15 | {status} |
  | Content adequacy | {N} | 15 | SE real data, steril method, DoC coverage, materials, criteria (minus [TODO] penalty) |
  | Deficiency penalty | {N} | 15 | {N} critical, {M} major |
  | Documentation | {N} | 10 | {N}/{M} core sections |

[TODO] DENSITY BY SECTION
────────────────────────────────────────

  {For each draft file with [TODO] items:}
  | Section | Total Lines | [TODO] Lines | Density | Status |
  |---------|-------------|-------------|---------|--------|
  | {section_name} | {total} | {todo_count} | {%} | ✓ OK / ⚠ High / ✗ Critical |

  Density thresholds: <50% = OK, 50-80% = High (⚠), >80% = Critical (✗)
  Content adequacy penalty: -{N} pts for high-density sections

REMEDIATION PLAN
────────────────────────────────────────

  Priority order (address CRITICAL first, then MAJOR):

  1. [CRITICAL] {action} → Run: {/fda: command}
  2. [CRITICAL] {action} → Run: {/fda: command}
  3. [MAJOR] {action} → Run: {/fda: command}
  ...

{If --depth deep:}

COMPETITIVE CONTEXT
────────────────────────────────────────

  Recent 510(k) clearances for {product_code}:
  {Query openFDA for recent clearances, show top 5}

  | K-Number | Device | Applicant | Cleared | Type |
  |----------|--------|-----------|---------|------|
  ...

  Common predicates in recent submissions: {list}
  Average review time: {estimate based on clearance data}

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Step 9: Audit Logging

Write audit log entries using `fda_audit_logger.py`:

### Log pre-check start

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command pre-check \
  --action pre_check_started \
  --subject "$PRODUCT_CODE" \
  --mode "$MODE" \
  --rationale "Pre-check started: depth=$DEPTH, focus=$FOCUS" \
  --metadata "{\"depth\":\"$DEPTH\",\"focus\":\"$FOCUS\"}"
```

### Log RTA screening result

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command pre-check \
  --action rta_screening_completed \
  --subject "$PRODUCT_CODE" \
  --decision "$RTA_RESULT" \
  --mode "$MODE" \
  --decision-type auto \
  --rationale "RTA screening $RTA_RESULT: $RTA_PRESENT/$RTA_REQUIRED required items present" \
  --metadata "{\"present\":$RTA_PRESENT,\"required\":$RTA_REQUIRED,\"missing\":$RTA_MISSING}"
```

### Log each deficiency

For each identified deficiency:

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command pre-check \
  --action deficiency_identified \
  --subject "$DEF_ID" \
  --decision "$SEVERITY" \
  --mode "$MODE" \
  --decision-type auto \
  --rationale "$FINDING_TEXT" \
  --metadata "{\"severity\":\"$SEVERITY\",\"reviewer\":\"$REVIEWER\",\"remediation_command\":\"$REMEDIATION_CMD\"}"
```

### Log SRI calculation

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command pre-check \
  --action sri_calculated \
  --subject "$PRODUCT_CODE" \
  --decision "$SRI_TIER" \
  --confidence "$SRI_SCORE" \
  --mode "$MODE" \
  --decision-type auto \
  --rationale "SRI: $SRI_SCORE/100 ($SRI_TIER). $CRITICAL_COUNT critical, $MAJOR_COUNT major deficiencies." \
  --metadata "{\"score_breakdown\":{\"rta_completeness\":$RTA_PTS,\"predicate_quality\":$PRED_PTS,\"se_comparison\":$SE_PTS,\"testing_coverage\":$TEST_PTS,\"deficiency_penalty\":$DEF_PTS,\"documentation\":$DOC_PTS}}" \
  --alternatives '["Ready","Nearly Ready","Significant Gaps","Not Ready","Early Stage"]' \
  --exclusions "$SRI_EXCLUSIONS_JSON" \
  --files-written "$PROJECTS_DIR/$PROJECT_NAME/pre_check_report.md"
```

### Log completion

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command pre-check \
  --action pre_check_report_generated \
  --decision "completed" \
  --mode "$MODE" \
  --rationale "Pre-check complete: SRI $SRI_SCORE/100, $DEF_TOTAL deficiencies ($CRITICAL_COUNT critical, $MAJOR_COUNT major, $MINOR_COUNT minor)" \
  --files-written "$PROJECTS_DIR/$PROJECT_NAME/pre_check_report.md"
```

## Error Handling

- **No project**: "Project name required. Use --project NAME."
- **Empty project**: Run pre-check with RTA-only mode. Note: "Project has no pipeline data. Run /fda:extract or /fda:propose first."
- **No review.json**: Predicate quality scores as 0. Note: "No predicates identified. Run /fda:propose or /fda:review first."
- **API unavailable**: Use flat files for classification. Skip MAUDE/recall checks. Note in report.
- **Missing guidance data**: Use cross-cutting requirements only for testing coverage. Note: "Run /fda:guidance for device-specific requirements."
- **--depth deep without sufficient data**: Degrade to standard depth. Note: "Insufficient data for deep analysis. Using standard depth."
