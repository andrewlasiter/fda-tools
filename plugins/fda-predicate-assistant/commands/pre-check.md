---
description: Simulate an FDA review team's evaluation of your 510(k) submission — identifies likely deficiencies, screens against RTA checklist, and generates a submission readiness score
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch, WebSearch
argument-hint: "--project NAME [--depth quick|standard|deep] [--focus predicate|testing|labeling|clinical|all]"
---

# FDA Pre-Check: Review Simulation

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
    params = {"search": f'product_code:"{product_code}"', "limit": "1"}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/classification.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.3.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
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

## Step 3: RTA Screening

**This step runs at all `--depth` levels including `quick`.**

Walk through the RTA checklist from `references/cdrh-review-structure.md` Section 3:

### Administrative RTA Items

For each RTA criterion, check project data:

```python
rta_items = [
    {"id": "RTA-01", "item": "Cover letter", "check": "draft_cover-letter.md in drafts", "required": True},
    {"id": "RTA-02", "item": "FDA Form 3514 (Cover Sheet)", "check": "referenced in cover letter", "required": True},
    {"id": "RTA-03", "item": "Indications for Use (Form 3881)", "check": "IFU in review.json or --intended-use", "required": True},
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

## Step 5: Specialist Reviewer Evaluations

**For each specialist reviewer identified in Step 2:**

### Biocompatibility Review

If Biocompatibility reviewer assigned:
- Check for `draft_biocompatibility.md`
- Check for material characterization in device description
- Identify required ISO 10993 tests based on contact type and duration
- Flag missing tests as MAJOR deficiency

### Software Review

If Software reviewer assigned:
- Check for `draft_software.md`
- Check for cybersecurity documentation
- Look for IEC 62304 references
- Flag missing documentation level as MAJOR deficiency

### Sterilization Review

If Sterilization reviewer assigned:
- Check for `draft_sterilization.md`
- Verify sterilization method specified
- Check for SAL reference
- Flag missing validation plan as MAJOR deficiency

### Electrical/EMC Review

If Electrical/EMC reviewer assigned:
- Check for `draft_emc-electrical.md`
- Verify IEC 60601-1 referenced
- Check for EMC testing per IEC 60601-1-2
- Flag missing test reports as MAJOR deficiency

### Human Factors Review

If Human Factors reviewer assigned:
- Check for human factors data in project
- Verify IEC 62366-1 referenced
- Check for use-related risk analysis
- Flag missing usability testing as MAJOR deficiency

### Clinical Review

If Clinical reviewer assigned:
- Check for clinical data in project (literature, study)
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

## Step 7: Calculate Submission Readiness Score

Use the scoring system from `references/cdrh-review-structure.md` Section 8:

```python
def calculate_readiness_score(rta_result, predicate_scores, se_comparison,
                              testing_coverage, deficiencies, drafts):
    score = 0

    # RTA completeness (25 pts)
    rta_present = sum(1 for item in rta_result if item["status"] == "present")
    rta_required = sum(1 for item in rta_result if item["required"])
    score += 25 * (rta_present / max(rta_required, 1))

    # Predicate quality (20 pts)
    if predicate_scores:
        avg_score = sum(predicate_scores) / len(predicate_scores)
        score += avg_score * 0.2
    # else: 0 pts

    # SE comparison (15 pts)
    if se_comparison == "complete":
        score += 15
    elif se_comparison == "partial":
        score += 8

    # Testing coverage (15 pts)
    if testing_coverage:
        score += 15 * testing_coverage

    # Deficiency penalty (15 pts)
    critical_count = sum(1 for d in deficiencies if d["severity"] == "CRITICAL")
    major_count = sum(1 for d in deficiencies if d["severity"] == "MAJOR")
    penalty = min(15, 3 * critical_count + 1 * major_count)
    score += 15 - penalty

    # Documentation quality (10 pts)
    if drafts:
        expected_sections = ["device-description", "se-discussion", "510k-summary",
                            "labeling", "cover-letter", "truthful-accuracy"]
        present = sum(1 for s in expected_sections
                     if any(s in d for d in drafts))
        score += 10 * (present / len(expected_sections))

    return round(score)
```

## Step 8: Write Report

Write `pre_check_report.md` to the project folder:

```markdown
  FDA Pre-Check Report
  {project_name} — {device_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.3.0
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

SUBMISSION READINESS SCORE
────────────────────────────────────────

  Score: {N}/100 — {Ready / Nearly Ready / Significant Gaps / Not Ready / Early Stage}

  | Component | Score | Max | Notes |
  |-----------|-------|-----|-------|
  | RTA completeness | {N} | 25 | {N}/{M} required items |
  | Predicate quality | {N} | 20 | Avg confidence: {N}/100 |
  | SE comparison | {N} | 15 | {status} |
  | Testing coverage | {N} | 15 | {N}/{M} tests planned |
  | Deficiency penalty | {N} | 15 | {N} critical, {M} major |
  | Documentation | {N} | 10 | {N}/{M} core sections |

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

Write audit log entries per `references/audit-logging.md`:

- `pre_check_started` entry with depth, focus, project
- `review_team_identified` entry with OHT, specialists
- `rta_screening_completed` entry with pass/fail and item counts
- For each deficiency: `deficiency_identified` entry
- `readiness_score_calculated` entry with score and tier
- At completion: `pre_check_report_generated` entry

Append all entries to `$PROJECTS_DIR/$PROJECT_NAME/audit_log.jsonl`.

## Error Handling

- **No project**: "Project name required. Use --project NAME."
- **Empty project**: Run pre-check with RTA-only mode. Note: "Project has no pipeline data. Run /fda:extract or /fda:propose first."
- **No review.json**: Predicate quality scores as 0. Note: "No predicates identified. Run /fda:propose or /fda:review first."
- **API unavailable**: Use flat files for classification. Skip MAUDE/recall checks. Note in report.
- **Missing guidance data**: Use cross-cutting requirements only for testing coverage. Note: "Run /fda:guidance for device-specific requirements."
- **--depth deep without sufficient data**: Degrade to standard depth. Note: "Insufficient data for deep analysis. Using standard depth."
