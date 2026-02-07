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
- `--include-literature` — Include literature summary from literature.md (default: on if data available)
- `--include-safety` — Include MAUDE/recall safety intelligence (default: on if data available)
- `--no-literature` — Explicitly exclude literature section even if data available
- `--no-safety` — Explicitly exclude safety section even if data available

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

Before generating the document, resolve all placeholders using this priority system:

#### Full-Auto Validation

**If `--full-auto` is active:**
- `--device-description` and `--intended-use` are **REQUIRED**. If either is missing:
  - If `--project` is provided: attempt to synthesize from `query.json` product_codes + openFDA classification data (device name, definition, regulation). Log: "Synthesized device description from openFDA classification for {product_code}."
  - If synthesis fails or no `--project`: **ERROR**: "In --full-auto mode, --device-description and --intended-use are required. Provide both arguments or use --project with product code data for auto-synthesis."

#### Standard Placeholder Rules

**If `--device-description` provided:**
- Replace `[TODO: Company-specific — Detailed description of your device...]` with the provided description
- Replace `[TODO: Company-specific — How the device works...]` with a synthesized principle of operation based on the description
- Replace `[TODO: Company-specific — List all components...]` with "See device description above — [TODO: Company-specific — provide detailed BOM]"
- Replace `[TODO: Company-specific — Device photographs...]` with "[TODO: Company-specific — attach device images]"

**If `--intended-use` provided:**
- Replace `[TODO: Company-specific — Proposed indications for use text...]` with the provided intended use

**If `--project` has existing data (review.json, guidance_cache):**
- Replace `[TODO: Company-specific — Proposed predicate device(s)...]` with top accepted predicates from review.json
- Replace `[TODO: Company-specific — Proposed testing strategy...]` with requirements from guidance_cache

#### Final Placeholder Conversion

**VERIFY: No `[INSERT: ...]` placeholders** should appear in the final output. The template already uses `[TODO: Company-specific — ...]` format. If any `[INSERT: ...]` markers are inadvertently generated, convert them to `[TODO: Company-specific — {description}]` before writing. This ensures:
- Users can clearly see what needs human input vs what was auto-filled
- Automated tools can grep for `[TODO:` to find remaining work items
- The document is always complete (no empty/broken sections)

Write the `presub_plan.md` document using the Pre-Sub format from `references/submission-structure.md` and `references/output-formatting.md`:

```markdown
# Pre-Submission Meeting Request
## {Device Description} — Product Code {CODE}

**Date:** {today's date}
**Requested Meeting Type:** {meeting_type}
**Product Code:** {CODE} — {device_name}
**Generated:** {today's date} | v4.6.0
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
{If not: "[TODO: Company-specific — Detailed description of your device including principle of operation, key components, materials of construction, and intended patient population]"}

### 2.2 Principle of Operation
[TODO: Company-specific — How the device works — sensing mechanism, therapeutic action, etc.]

### 2.3 Key Components and Materials
[TODO: Company-specific — List all components, especially patient-contacting materials]

### 2.4 Illustrations
[TODO: Company-specific — Device photographs, diagrams, or schematics]

---

## 3. Proposed Indications for Use

{If --intended-use provided: use it}
{If not: "[TODO: Company-specific — Proposed indications for use text. Model on cleared IFU language for this product code.]"}

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
[TODO: Company-specific — Proposed predicate device(s) with K-numbers and justification]

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
[TODO: Company-specific — Proposed testing strategy. Run `/fda:guidance {CODE} --save` for requirements analysis.]

---

## 7. Regulatory Background

### 7.1 Regulatory History of Device Type
{Auto-generated from openFDA data:}
Product code {CODE} ({device_name}) has been regulated under 21 CFR {regulation} since {earliest clearance year from openFDA}.

**Clearance Statistics (from openFDA 510k API):**
- Total 510(k) clearances for this product code: {total count}
- Recent clearances (last 5 years): {count}
- Predominant submission type: {Traditional/Special/Abbreviated}
- Common predicate devices: {top 3 most-cited predicates with counts}

{If De Novo history exists:}
The product code was established via De Novo classification: {DEN number, date}.

### 7.2 Clinical Need
[TODO: Company-specific — Describe the unmet clinical need addressed by the device:
- Patient population
- Current standard of care
- Limitations of existing devices
- How the subject device addresses the need]

### 7.3 Applicable Guidance Documents
{If guidance_cache available from /fda:guidance:}

| # | Guidance Document | Year | Relevance |
|---|-------------------|------|-----------|
{For each guidance in cache:}
| {n} | {title} | {year} | {summary of key requirements} |

[Source: guidance_cache]

{If no guidance cache:}
[TODO: Run `/fda:guidance {CODE}` to identify applicable guidance documents]

---

## 8. Preliminary Data Summary

### 8.1 Testing Completed
{If test_plan.md exists from /fda:test-plan:}

| Test Category | Standard | Status | Summary |
|---------------|----------|--------|---------|
{For each test in test_plan.md:}
| {category} | {standard} | {Planned/In Progress/Complete} | {brief summary} |

[Source: test_plan.md]

{If no test plan:}
[TODO: Company-specific — Summarize any preliminary testing:
- Bench testing results
- Biocompatibility testing
- Software verification
- Electrical safety testing
- Sterilization validation]

### 8.2 Literature Evidence
{If literature.md exists from /fda:literature AND --include-literature (or default on):}

A literature review was conducted to support the clinical evidence strategy.

**Search Summary:**
- Databases searched: {databases from literature.md}
- Key search terms: {terms}
- Articles identified: {count}
- Articles included: {count}

**Key Findings:**
{Top 3-5 findings from literature.md relevant to device safety and effectiveness}

[Source: literature.md]

{If --no-literature or no data:}
[TODO: Run `/fda:literature {CODE}` for literature review, or provide preliminary literature references]

### 8.3 Prior Submissions
[TODO: Company-specific — List any prior FDA interactions:
- Previous Pre-Sub meetings (Q-Sub numbers)
- Previous 510(k) submissions for related devices
- Previous FDA correspondence]

---

## 9. Safety Intelligence

{If safety data available from /fda:safety AND --include-safety (or default on):}

### 9.1 MAUDE Adverse Event Analysis
{Auto-query openFDA MAUDE events for product code:}

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

product_code = "PRODUCTCODE"  # Replace
params = {"search": f'device.device_report_product_code:"{product_code}"', "count": "event_type.exact"}
if api_key:
    params["api_key"] = api_key
url = f"https://api.fda.gov/device/event.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        total = sum(r.get('count', 0) for r in data.get('results', []))
        print(f"MAUDE_TOTAL:{total}")
        for r in data.get('results', []):
            print(f"EVENT_TYPE:{r['term']}|{r['count']}")
except Exception as e:
    print(f"MAUDE_ERROR:{e}")
PYEOF
```

**MAUDE Event Summary for {product_code}:**

| Event Type   | Count | % of Total |
|-------------|-------|------------|
| Malfunction | {count} | {pct}%  |
| Injury      | {count} | {pct}%  |
| Death       | {count} | {pct}%  |

**Total events:** {total}
**Assessment:** {Low/Moderate/High concern based on event rates vs clearance volume}
[Source: openFDA MAUDE API]

### 9.2 Recall History
{Auto-query openFDA recalls for product code:}

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

product_code = "PRODUCTCODE"  # Replace
params = {"search": f'product_code:"{product_code}"', "limit": "5", "sort": "event_date_terminated:desc"}
if api_key:
    params["api_key"] = api_key
url = f"https://api.fda.gov/device/recall.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        total = data.get('meta', {}).get('results', {}).get('total', 0)
        print(f"RECALL_TOTAL:{total}")
        for r in data.get('results', [])[:5]:
            print(f"RECALL:{r.get('res_event_number', 'N/A')}|{r.get('event_type', 'N/A')}|{r.get('product_description', 'N/A')[:80]}")
except Exception as e:
    print(f"RECALL_ERROR:{e}")
PYEOF
```

**Recall History for {product_code}:**
- Total recalls: {count}
- Class I (most serious): {count}
- Class II: {count}
- Class III: {count}

{If recalls exist:}
**Recent Recalls:**

| # | Event | Class | Description |
|---|-------|-------|-------------|
{Top 3 recalls:}
| 1 | {event_number} | {class} | {description} |

**Pre-Sub Relevance:** {How safety data should inform FDA questions — e.g., "Recall history suggests FDA may focus on {failure mode}. Consider addressing in Question {N}."}

[Source: openFDA Recall API]

### 9.3 Safety Summary for FDA Discussion
Based on the MAUDE and recall analysis:
- **Primary safety concern:** {identified from event/recall patterns or "No dominant safety signal identified"}
- **Recommended FDA question:** Consider asking FDA about specific testing to address {concern} (see Question {N})
- **Predicate safety comparison:** {If predicate recall/MAUDE data available, compare rates}

{If --no-safety or API unavailable:}
[TODO: Run `/fda:safety --product-code {CODE}` for MAUDE + recall analysis, or provide your own safety data summary]

---

## 10. Supporting Data

{If any data available from project:}
- Preliminary extraction analysis: {count} devices analyzed, {count} predicates identified
- Review status: {count} accepted, {count} rejected predicates
- Guidance analysis: {count} applicable guidance documents identified

{If no data:}
[TODO: Company-specific — Any preliminary data, literature references, or prior testing results]

---

## 11. Meeting Logistics

### 11.1 Submission Timeline
{Auto-calculate based on today's date:}
- **Pre-Sub preparation target:** {today + 2 weeks}
- **Pre-Sub submission to FDA:** {today + 4 weeks}
- **FDA 75-day meeting deadline:** {submission date + 75 calendar days}
- **Expected FDA feedback by:** {submission date + 75 days}
- **510(k) submission target:** {feedback date + time for incorporation}

**Note:** FDA aims to hold Pre-Sub meetings within 75 calendar days of receipt (per MDUFA performance goals). Written-only responses are typically faster.

### 11.2 Preferred Meeting Format
**Requested format:** {meeting_type}

{If teleconference:}
Teleconference preferred. FDA typically schedules 60-minute Pre-Sub meetings.

{If written:}
Written feedback only (Q-Sub). This is the fastest option — FDA provides written responses without a meeting.

{If in-person:}
In-person meeting at FDA White Oak campus. Note: In-person meetings may have longer scheduling timelines.

### 11.3 Proposed Agenda
1. **Introductions** (5 min)
2. **Device overview and intended use** (10 min)
3. **Predicate selection and regulatory strategy** (15 min)
4. **Testing strategy discussion** (15 min)
5. **FDA questions and feedback** (15 min)

### 11.4 Proposed Attendees
**From {applicant_name}:**
- [TODO: Company-specific — Regulatory Affairs lead]
- [TODO: Company-specific — Engineering/R&D lead]
- [TODO: Company-specific — Quality/clinical lead (if applicable)]

**From FDA:**
- Lead reviewer (assigned after submission)
- Team lead (CDRH division based on review panel)

---

## Action Items After Pre-Sub

After receiving FDA feedback:
1. Update predicate selection based on FDA's response to Question 1
2. Finalize testing plan incorporating FDA's recommendations
3. Address any additional data requirements FDA identifies
4. Begin formal submission preparation
5. Consider running `/fda:submission-outline {CODE} --project {PROJECT_NAME}` to generate the full submission outline

---

> **Disclaimer:** This Pre-Submission plan is AI-generated from public FDA data.
> Verify independently. Not regulatory advice.
```

## Audit Logging

After generating the Pre-Sub plan, write audit log entries per `references/audit-logging.md`:

- For each resolved placeholder: write a `placeholder_resolved` entry with what was filled and from which data source
- For each remaining placeholder converted: write a `placeholder_converted` entry
- For any synthesized data: write a `data_synthesized` entry
- At completion: write a `document_generated` entry with the output file path

Append all entries to `$PROJECTS_DIR/$PROJECT_NAME/audit_log.jsonl`.

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
  1. Fill in [TODO: ...] placeholders with your device-specific information
  2. Review auto-generated FDA questions — add, modify, or remove as needed
  3. Have your regulatory team review the complete package
  4. Submit to FDA via the Pre-Submission program
```

## Error Handling

- **No product code**: Ask the user for it
- **API unavailable**: Use flat files for classification. Generate template with less auto-populated data.
- **No project data**: Generate a clean template. Note which sections would benefit from running `/fda:research`, `/fda:review`, or `/fda:guidance` first.
- **No predicates identified**: Include a section about predicate selection and suggest running `/fda:research` to identify candidates. Consider whether De Novo pathway applies.
