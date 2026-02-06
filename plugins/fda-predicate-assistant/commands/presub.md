---
description: Plan a Pre-Submission meeting with FDA — generate cover letter template, meeting request, and discussion topics based on device and predicate analysis
allowed-tools: Bash, Read, Glob, Grep, Write, WebSearch
argument-hint: "<product-code> [--project NAME] [--device-description TEXT] [--intended-use TEXT] [--infer]"
---

# FDA Pre-Submission Meeting Planner

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

You are helping the user plan a Pre-Submission (Pre-Sub) meeting with FDA. Generate a structured Pre-Sub package based on device information, predicate analysis, and guidance requirements.

**KEY PRINCIPLE: Degrade gracefully.** If Phase 1 review data or Phase 2 guidance data is available, use it to enrich the Pre-Sub. If not, generate a useful template based on classification data and the user's inputs alone.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Product code** (required) — 3-letter FDA product code
- `--project NAME` — Use data from a specific project folder (review.json, guidance_cache, output.csv)
- `--device-description TEXT` — Description of the user's device
- `--intended-use TEXT` — Proposed indications for use
- `--meeting-type written|teleconference|in-person` — Preferred meeting type (default: teleconference)
- `--output FILE` — Write Pre-Sub plan to file (default: presub_plan.md in project folder)
- `--infer` — Auto-detect product code from project data instead of requiring explicit input

If no product code provided:
- If `--infer` AND `--project NAME` specified:
  1. Check `$PROJECTS_DIR/$PROJECT_NAME/query.json` for `product_codes` field → use first code
  2. Check `$PROJECTS_DIR/$PROJECT_NAME/output.csv` → find most-common product code in data
  3. Check `~/fda-510k-data/guidance_cache/` for directory names matching product codes
  4. If inference succeeds: log "Inferred product code: {CODE} from {source}"
  5. If inference fails: **ERROR** (not prompt): "Could not infer product code. Provide --product-code CODE or run /fda:extract first."
- If `--infer` without `--project`: check if exactly 1 project exists in projects_dir and use it
- If no `--infer` and no product code: ask the user for it.

## Step 1: Gather Available Data

### Classification data

Query openFDA for device classification (same pattern as other commands):

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
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            if data.get("results"):
                r = data["results"][0]
                print(f"DEVICE_NAME:{r.get('device_name', 'N/A')}")
                print(f"DEVICE_CLASS:{r.get('device_class', 'N/A')}")
                print(f"REGULATION:{r.get('regulation_number', 'N/A')}")
                print(f"PANEL:{r.get('medical_specialty_description', r.get('review_panel', 'N/A'))}")
    except Exception as e:
        print(f"API_ERROR:{e}")
PYEOF
```

### Check for project data (optional enrichment)

If `--project NAME` is provided, check for available data from previous pipeline steps:

```bash
# Check for review data (Phase 1)
cat "$PROJECTS_DIR/$PROJECT_NAME/review.json" 2>/dev/null && echo "REVIEW_DATA:found" || echo "REVIEW_DATA:not_found"

# Check for guidance cache (Phase 2)
cat "$PROJECTS_DIR/$PROJECT_NAME/guidance_cache/guidance_index.json" 2>/dev/null && echo "GUIDANCE_DATA:found" || echo "GUIDANCE_DATA:not_found"

# Check for extraction data
cat "$PROJECTS_DIR/$PROJECT_NAME/output.csv" 2>/dev/null | head -5 && echo "EXTRACTION_DATA:found" || echo "EXTRACTION_DATA:not_found"
```

## Step 2: Identify Top Predicate Candidates

### If review.json exists (from `/fda:review`)

Use accepted predicates with their scores and rationale:
```python
import json
with open(review_json_path) as f:
    review = json.load(f)
accepted = {k: v for k, v in review.get('predicates', {}).items() if v.get('decision') == 'accepted'}
# Sort by confidence score
top_predicates = sorted(accepted.items(), key=lambda x: -x[1].get('confidence_score', 0))[:3]
```

### If no review.json but output.csv exists

Extract the most frequently cited predicates from extraction data (same approach as extract.md safety scan).

### If no project data at all

Ask the user if they have predicate candidates in mind. If not, suggest running `/fda:research {PRODUCT_CODE}` first.

Even without predicate data, still generate the Pre-Sub template with placeholder sections.

## Step 3: Identify Testing Gaps and Questions

### If guidance_cache exists (from `/fda:guidance`)

Read the requirements matrix and identify areas needing FDA input:

```python
# Load cached requirements
with open(requirements_matrix_path) as f:
    requirements = json.load(f)

# Identify gaps where guidance requires testing but predicate precedent is thin
gaps = [r for r in requirements if r.get('priority') == 'PLAN' or r.get('gap')]
```

### If no guidance cache

Determine likely testing areas from the device classification and description. Use knowledge from `references/guidance-lookup.md` cross-cutting guidance table to identify applicable testing categories.

### Auto-Generate FDA Questions

Based on available data, generate appropriate Pre-Sub questions:

**Always include** (regardless of data availability):
1. Predicate selection question (if predicates identified)
2. Classification confirmation question

**Include if gaps identified**:
3. Testing strategy question for each major gap
4. Clinical data expectations question

**Include if novel features mentioned in device description**:
5. Novel feature question

**Include if intended use extends beyond predicate IFU**:
6. Indications for use question

Limit to 5-7 questions per FDA recommendation.

## Step 4: Generate Pre-Sub Package

### Placeholder Resolution

Before generating the document, resolve all placeholders:

**If `--device-description` provided:**
- Replace `[INSERT: Detailed description of your device...]` with the provided description
- Replace `[INSERT: How the device works...]` with a synthesized principle of operation based on the description
- Replace `[INSERT: List all components...]` with "See device description above — [TODO: Company-specific — provide detailed BOM]"
- Replace `[INSERT: Device photographs...]` with "[TODO: Company-specific — attach device images]"

**If `--intended-use` provided:**
- Replace `[INSERT: Proposed indications for use text...]` with the provided intended use

**If `--project` has existing data (review.json, guidance_cache):**
- Replace `[INSERT: Proposed predicate device(s)...]` with top accepted predicates from review.json
- Replace `[INSERT: Proposed testing strategy...]` with requirements from guidance_cache

**Remaining placeholders** that cannot be auto-filled should be changed from `[INSERT: ...]` to `[TODO: Company-specific — {description}]` to clearly distinguish auto-fillable vs truly-needs-human items.

Write the `presub_plan.md` document using the Pre-Sub format from `references/submission-structure.md`:

```markdown
# Pre-Submission Meeting Request
## {Device Description} — Product Code {CODE}

**Date:** {today's date}
**Requested Meeting Type:** {meeting_type}
**Product Code:** {CODE} — {device_name}
**Classification:** Class {class}, 21 CFR {regulation}
**Review Panel:** {panel}

---

## 1. Cover Letter

[Date]

Division of {review_panel}
Office of {office based on panel}
Center for Devices and Radiological Health
Food and Drug Administration
10903 New Hampshire Avenue
Silver Spring, MD 20993

RE: Pre-Submission Meeting Request — {device_name}

Dear Sir/Madam:

{Company Name} respectfully requests a {meeting_type} meeting with FDA to discuss the regulatory strategy for our {device_description}. We believe this device is classified under product code {CODE} (21 CFR {regulation}, Class {class}).

We are seeking FDA's feedback on the following topics:
{numbered list of question topics}

We are available for a meeting at FDA's earliest convenience. Our preferred meeting format is a {meeting_type}.

Sincerely,

{Company Name}
{Contact Information}

---

## 2. Device Description

### 2.1 Overview
{If --device-description provided: use it}
{If not: "[INSERT: Detailed description of your device including principle of operation, key components, materials of construction, and intended patient population]"}

### 2.2 Principle of Operation
[INSERT: How the device works — sensing mechanism, therapeutic action, etc.]

### 2.3 Key Components and Materials
[INSERT: List all components, especially patient-contacting materials]

### 2.4 Illustrations
[INSERT: Device photographs, diagrams, or schematics]

---

## 3. Proposed Indications for Use

{If --intended-use provided: use it}
{If not: "[INSERT: Proposed indications for use text. Model on cleared IFU language for this product code.]"}

---

## 4. Proposed Regulatory Strategy

### 4.1 Proposed Pathway
{Auto-determine based on available data:
- If predicates identified → Traditional 510(k) (most likely)
- If modifying own device → Special 510(k)
- If strong guidance/standard coverage → Abbreviated 510(k)
- If no predicates → De Novo}

**Rationale:** {Explain why this pathway is appropriate}

### 4.2 Proposed Predicate Device(s)

{If predicates available from review.json:}

| # | K-Number | Device Name | Applicant | Cleared | Score |
|---|----------|-------------|-----------|---------|-------|
| 1 | {K-number} | {name} | {company} | {date} | {score}/100 |
| 2 | {K-number} | {name} | {company} | {date} | {score}/100 |

**Predicate Justification:**
{For each predicate:}
- **{K-number}**: Selected because {rationale from review.json or auto-generated}.
  - Same intended use: {comparison}
  - Same technological characteristics: {comparison}
  - {If different technology: explain why it doesn't raise new questions}

{If no predicates:}
[INSERT: Proposed predicate device(s) with K-numbers and justification]

### 4.3 Classification Analysis
Product Code: {CODE}
Regulation: 21 CFR {regulation}
Device Name: {device_name}
Class: {class}

{If Class II: "Special controls apply per {regulation}. We plan to address these through {testing/labeling strategy}."}

---

## 5. Questions for FDA

{Auto-generated questions — 5-7 max, numbered:}

### Question 1: Predicate Selection
Does FDA agree that {K-number(s)} {device name(s)} {are/is} an appropriate predicate device for our {device description}? If not, can FDA recommend alternative predicate(s)?

### Question 2: Classification
We believe our device is appropriately classified under product code {CODE} (21 CFR {regulation}, Class {class}). Does FDA agree with this classification?

{If testing gaps identified:}
### Question 3: Testing Strategy — {Gap Category}
We propose to {testing plan} per {standard}. Does FDA agree this testing strategy is sufficient to demonstrate {performance claim}, or does FDA recommend additional testing?

{If novel features:}
### Question 4: Novel Feature — {Feature Name}
Our device includes {novel feature} not present in the proposed predicate. What additional data, if any, does FDA recommend to address this design difference?

{If clinical data question:}
### Question 5: Clinical Data Expectations
Based on predicate precedent showing {X of Y predicates included clinical data}, does FDA expect clinical data for our submission? If so, what study design would FDA recommend?

{If IFU extends beyond predicate:}
### Question 6: Indications for Use
Our proposed indications for use include {extended claims}. The predicate's IFU is limited to {predicate IFU}. Does FDA agree our proposed IFU is appropriate, or should it be narrowed?

---

## 6. Proposed Testing Strategy

{If guidance_cache available:}

| Test Category | Proposed Approach | Standard | Status |
|---------------|-------------------|----------|--------|
{From requirements matrix:}
| Biocompatibility | ISO 10993-5, -10, -11 | ISO 10993-1 | Planned |
| Sterilization | EO validation | ISO 11135 | Planned |
| Shelf Life | Accelerated aging (2 yr claim) | ASTM F1980 | Planned |
| Performance | {device-specific tests} | {standards} | Planned |

{If no guidance cache:}
[INSERT: Proposed testing strategy. Run `/fda:guidance {CODE} --save` for requirements analysis.]

---

## 7. Supporting Data

{If any data available from project:}
- Preliminary extraction analysis: {count} devices analyzed, {count} predicates identified
- Review status: {count} accepted, {count} rejected predicates
- Guidance analysis: {count} applicable guidance documents identified

{If no data:}
[INSERT: Any preliminary data, literature references, or prior testing results]

---

## Action Items After Pre-Sub

After receiving FDA feedback:
1. Update predicate selection based on FDA's response to Question 1
2. Finalize testing plan incorporating FDA's recommendations
3. Address any additional data requirements FDA identifies
4. Begin formal submission preparation
5. Consider running `/fda:submission-outline {CODE} --project {PROJECT_NAME}` to generate the full submission outline

---

⚠ DISCLAIMER: This Pre-Submission plan is AI-generated from publicly available
FDA data. It is a starting point — not a final document. Review with your
regulatory affairs team before submitting to FDA. This is not regulatory advice.
```

## Step 5: Write Output

Write the generated Pre-Sub plan:

```bash
# Determine output path
if [ -n "$OUTPUT_FILE" ]; then
    OUTPUT_PATH="$OUTPUT_FILE"
elif [ -n "$PROJECT_NAME" ]; then
    OUTPUT_PATH="$PROJECTS_DIR/$PROJECT_NAME/presub_plan.md"
else
    OUTPUT_PATH="$HOME/fda-510k-data/presub_plan_${PRODUCT_CODE}.md"
fi
```

Write the content using the Write tool.

Report to the user:
```
Pre-Submission plan written to: {output_path}

The plan includes:
  • Cover letter template
  • Device description section {auto-populated / template}
  • Proposed regulatory strategy: {pathway}
  • Predicate justification: {count} predicates {with scores / template}
  • {N} FDA questions auto-generated
  • Testing strategy: {from guidance / template}

Next steps:
  1. Fill in [INSERT: ...] placeholders with your device-specific information
  2. Review auto-generated FDA questions — add, modify, or remove as needed
  3. Have your regulatory team review the complete package
  4. Submit to FDA via the Pre-Submission program
```

## Error Handling

- **No product code**: Ask the user for it
- **API unavailable**: Use flat files for classification. Generate template with less auto-populated data.
- **No project data**: Generate a clean template. Note which sections would benefit from running `/fda:research`, `/fda:review`, or `/fda:guidance` first.
- **No predicates identified**: Include a section about predicate selection and suggest running `/fda:research` to identify candidates. Consider whether De Novo pathway applies.
