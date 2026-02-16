---
description: Plan a Pre-Submission meeting with FDA — generate cover letter template, meeting request, and discussion topics based on device and predicate analysis. Supports 510(k), PMA, IDE, and De Novo pathways.
allowed-tools: Bash, Read, Glob, Grep, Write, WebSearch
argument-hint: "<product-code> [--pathway 510k|pma|ide|de_novo] [--project NAME] [--device-description TEXT] [--intended-use TEXT] [--infer]"
---

# FDA Pre-Submission Meeting Planner

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

You are helping the user plan a Pre-Submission (Pre-Sub) meeting with FDA. Generate a structured Pre-Sub package based on device information, predicate analysis, and guidance requirements.

**KEY PRINCIPLE: Degrade gracefully.** If Phase 1 review data or Phase 2 guidance data is available, use it to enrich the Pre-Sub. If not, generate a useful template based on classification data and the user's inputs alone.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Product code** (required) — 3-letter FDA product code
- `--pathway 510k|pma|ide|de_novo` — Regulatory pathway (default: auto-detect from device class and characteristics)
- `--project NAME` — Use data from a specific project folder (review.json, guidance_cache, output.csv)
- `--device-description TEXT` — Description of the user's device
- `--intended-use TEXT` — Proposed indications for use
- `--meeting-type written|teleconference|in-person` — Preferred meeting type (default: teleconference)
- `--qsub-type formal|written|info|pre-ide` — Q-Sub type (default: auto-detect based on question count and complexity)
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
    params = {"search": f'product_code:"{product_code}"', "limit": "100"}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/classification.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})
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

### Determine Meeting Type (ENHANCED - TICKET-001)

If `--meeting-type` not explicitly provided, auto-detect using Python function:

```bash
MEETING_TYPE_RESULT=$(python3 << 'PYEOF'
import os, sys

# Get context from environment
question_count = int(os.environ.get("QUESTION_COUNT", "0"))
device_description = os.environ.get("DEVICE_DESCRIPTION", "").lower()
has_predicates = os.environ.get("HAS_PREDICATES", "false").lower() == "true"
novel_features = any(kw in device_description for kw in ["novel", "first-of-kind", "unprecedented", "no predicate"])

# Auto-detection decision tree
def detect_meeting_type():
    # Pre-IDE: Clinical study planned
    if "clinical study" in device_description or "ide" in device_description:
        return ("pre-ide", "Clinical study planned → Pre-IDE meeting")

    # Administrative: Pathway determination without technical questions
    if "pathway" in device_description or "de novo" in device_description:
        if question_count <= 2:
            return ("administrative", "Pathway determination focus → Administrative meeting")

    # Formal meeting: Complex or high question count
    if question_count >= 4:
        return ("formal", f"{question_count} questions → formal meeting recommended")

    if novel_features:
        return ("formal", "Novel features detected → formal meeting for FDA feedback")

    # Written response: Simple, well-scoped questions
    if 1 <= question_count <= 3:
        return ("written", f"{question_count} well-scoped questions → written feedback sufficient")

    # Info-only: No questions, just notification
    if question_count == 0:
        return ("info-only", "No questions → informational meeting (no FDA feedback expected)")

    # Default: Written response
    return ("written", "Default recommendation for straightforward submissions")

meeting_type, rationale = detect_meeting_type()
print(f"{meeting_type}|{rationale}")
PYEOF
)

# Parse result
MEETING_TYPE=$(echo "$MEETING_TYPE_RESULT" | cut -d'|' -f1)
DETECTION_RATIONALE=$(echo "$MEETING_TYPE_RESULT" | cut -d'|' -f2)
DETECTION_METHOD="auto"

# Export for metadata generation
export MEETING_TYPE
export DETECTION_RATIONALE
export DETECTION_METHOD

echo "Meeting Type Auto-Detected: $MEETING_TYPE"
echo "Rationale: $DETECTION_RATIONALE"
```

**Meeting Type Descriptions:**
- **formal** — Formal Pre-Sub meeting (teleconference/in-person), 5-7 questions expected
- **written** — Written feedback only (no meeting), 1-3 well-scoped questions
- **info** — Informational meeting for FDA awareness, minimal questions
- **pre-ide** — Pre-IDE meeting for clinical study protocol discussion
- **administrative** — Administrative/pathway determination meeting
- **info-only** — Information-only communication, no FDA feedback expected

**Override:** User can force specific meeting type with `--meeting-type formal|written|info|pre-ide|administrative|info-only`

Report the recommendation: "Recommended meeting type: {meeting_type} — {rationale}"

## Step 3.25: Determine Regulatory Pathway (NEW - TICKET-004)

If `--pathway` is explicitly provided, use that value. Otherwise, auto-detect from device classification and characteristics.

```bash
PATHWAY_RESULT=$(python3 << 'PYEOF'
import os, sys

# Check if user explicitly specified a pathway
user_pathway = os.environ.get("USER_PATHWAY", "").lower().strip()
valid_pathways = ["510k", "pma", "ide", "de_novo"]

if user_pathway and user_pathway in valid_pathways:
    print(f"{user_pathway}|user-specified|User specified --pathway {user_pathway}")
    sys.exit(0)

# Auto-detect pathway from device characteristics
device_class = os.environ.get("DEVICE_CLASS", "").strip()
device_description = os.environ.get("DEVICE_DESCRIPTION", "").lower()
has_predicates = os.environ.get("HAS_PREDICATES", "false").lower() == "true"

def detect_pathway():
    # Class III devices -> PMA (unless IDE for clinical study)
    if device_class == "3":
        # Check if clinical study is planned (IDE)
        ide_keywords = ["clinical study", "clinical investigation", "clinical trial",
                        "investigational", "ide", "feasibility study", "pivotal study",
                        "first-in-human", "first in human"]
        for kw in ide_keywords:
            if kw in device_description:
                return ("ide", f"Class III device with clinical study planned -> IDE pathway")

        return ("pma", f"Class III device -> Premarket Approval (PMA) pathway")

    # Explicit De Novo indicators
    de_novo_keywords = ["no predicate", "novel device", "no legally marketed",
                        "de novo", "first-of-kind", "new device type",
                        "no substantially equivalent", "novel technology"]
    for kw in de_novo_keywords:
        if kw in device_description:
            return ("de_novo", f"Novel device type ('{kw}' detected) -> De Novo classification")

    # IDE indicators (any class)
    ide_keywords = ["clinical study", "clinical investigation", "clinical trial",
                    "investigational device", "ide", "feasibility study", "pivotal study",
                    "first-in-human", "first in human", "significant risk study",
                    "nonsignificant risk study"]
    for kw in ide_keywords:
        if kw in device_description:
            return ("ide", f"Clinical investigation planned ('{kw}' detected) -> IDE pathway")

    # Class I or II with predicates -> 510(k)
    if device_class in ("1", "2") and has_predicates:
        return ("510k", f"Class {device_class} device with predicates identified -> 510(k) pathway")

    # Class I or II without predicates -> could be 510(k) or De Novo
    if device_class in ("1", "2") and not has_predicates:
        # Default to 510(k), but note De Novo possibility
        return ("510k", f"Class {device_class} device, no predicates yet -> 510(k) (consider De Novo if no predicate found)")

    # Default to 510(k)
    return ("510k", "Default pathway -> 510(k) Premarket Notification")

pathway, rationale = detect_pathway()
print(f"{pathway}|auto|{rationale}")
PYEOF
)

# Parse result
REGULATORY_PATHWAY=$(echo "$PATHWAY_RESULT" | cut -d'|' -f1)
PATHWAY_DETECTION_METHOD=$(echo "$PATHWAY_RESULT" | cut -d'|' -f2)
PATHWAY_RATIONALE=$(echo "$PATHWAY_RESULT" | cut -d'|' -f3-)

# Export for downstream use
export REGULATORY_PATHWAY
export PATHWAY_DETECTION_METHOD
export PATHWAY_RATIONALE

echo "Regulatory Pathway: $REGULATORY_PATHWAY"
echo "Detection: $PATHWAY_DETECTION_METHOD"
echo "Rationale: $PATHWAY_RATIONALE"
```

**Pathway Descriptions:**
- **510k** — 510(k) Premarket Notification (Class I/II with predicate)
- **pma** — Premarket Approval (Class III, requires clinical evidence)
- **ide** — Investigational Device Exemption (clinical study planned)
- **de_novo** — De Novo Classification Request (novel device, no predicate)

**Override:** User can force specific pathway with `--pathway 510k|pma|ide|de_novo`

Report the recommendation: "Regulatory pathway: {pathway} — {rationale}"

## Step 3.5: Select Questions from Question Bank (NEW - TICKET-001)

Using the meeting type determined above, select appropriate questions from presub_questions.json based on meeting_type_defaults and auto_triggers.

```bash
QUESTION_SELECTION_RESULT=$(python3 << 'PYEOF'
import json, os, sys

# Load question bank with proper error handling (CRITICAL-1 fix)
question_bank_path = os.path.join(os.environ.get("FDA_PLUGIN_ROOT", ""), "data/question_banks/presub_questions.json")
if not os.path.exists(question_bank_path):
    print("ERROR: Question bank not found at: " + question_bank_path, file=sys.stderr)
    print("QUESTION_BANK_MISSING")
    sys.exit(1)

try:
    with open(question_bank_path) as f:
        question_bank = json.load(f)
except json.JSONDecodeError as e:
    print(f"ERROR: Invalid JSON in question bank: {e}", file=sys.stderr)
    print("QUESTION_BANK_INVALID")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Failed to load question bank: {e}", file=sys.stderr)
    print("QUESTION_BANK_ERROR")
    sys.exit(1)

# Validate question bank schema
required_keys = ["version", "questions", "meeting_type_defaults", "auto_triggers"]
missing_keys = [k for k in required_keys if k not in question_bank]
if missing_keys:
    print(f"ERROR: Question bank missing required keys: {', '.join(missing_keys)}", file=sys.stderr)
    print("QUESTION_BANK_SCHEMA_ERROR")
    sys.exit(1)

# Validate version compatibility
supported_versions = ["1.0", "2.0"]
bank_version = question_bank.get("version", "unknown")
if bank_version not in supported_versions:
    print(f"WARNING: Question bank version {bank_version} may be incompatible. Supported: {', '.join(supported_versions)}", file=sys.stderr)

# Get meeting type, pathway, and device characteristics
meeting_type = os.environ.get("MEETING_TYPE", "formal")
device_description = os.environ.get("DEVICE_DESCRIPTION", "").lower()
has_predicates = os.environ.get("HAS_PREDICATES", "false").lower() == "true"
regulatory_pathway = os.environ.get("REGULATORY_PATHWAY", "510k")

# Get default questions for meeting type
default_question_ids = question_bank.get("meeting_type_defaults", {}).get(meeting_type, [])
selected_ids = set(default_question_ids)

# Merge pathway-specific defaults (NEW - TICKET-004)
pathway_defaults = question_bank.get("pathway_defaults", {}).get(regulatory_pathway, [])
selected_ids.update(pathway_defaults)

# Check auto-triggers with enhanced keyword matching (CRITICAL-3 fix)
auto_triggers = question_bank.get("auto_triggers", {})

# Normalize device description for better matching (handle hyphens, spacing, British spelling)
import re
normalized_desc = device_description.lower()
normalized_desc = re.sub(r'[-_]', ' ', normalized_desc)  # Normalize hyphens/underscores to spaces

device_keywords = {
    "patient_contacting": [
        "patient contact", "contacting", "skin contact", "tissue contact",
        "body contact", "mucosal contact", "blood contact", "patient contacting",
        "external communication", "surface contact"
    ],
    "sterile_device": [
        "sterile", "sterilization", "sterilized", "sterilisation", "sterilised",
        "eto", "ethylene oxide", "e beam", "gamma irradiation", "steam sterilization",
        "aseptic", "sterility"
    ],
    "powered_device": [
        "powered", "electrical", "electronic", "battery", "electric",
        "mains powered", "ac powered", "rechargeable", "power supply",
        "electrically powered"
    ],
    "software_device": [
        "software", "algorithm", "ai", "machine learning", "ml",
        "artificial intelligence", "ai based", "ai enabled", "computer aided",
        "automated analysis", "digital", "computational"
    ],
    "implant_device": [
        "implant", "implantable", "permanent", "permanently implanted",
        "long term implant", "chronic implant", "indwelling"
    ],
    "reusable_device": [
        "reusable", "reprocessing", "cleaning", "disinfection", "reuseable",
        "multi use", "multiple use", "re usable", "reprocessable"
    ],
    "novel_technology": [
        "novel", "first of kind", "unprecedented", "no predicate",
        "first in class", "new technology", "innovative", "breakthrough"
    ],
    "pma_pathway": [
        "pma", "premarket approval", "class iii", "class 3"
    ],
    "ide_pathway": [
        "investigational", "ide", "clinical study", "clinical investigation",
        "clinical trial", "feasibility study", "pivotal study", "first in human"
    ],
    "de_novo_pathway": [
        "de novo", "novel device", "no predicate", "no legally marketed",
        "new device type", "first of kind"
    ],
    "early_feasibility": [
        "early feasibility", "first in human", "first in man",
        "efs", "early feasibility study"
    ]
}

for trigger_name, keywords in device_keywords.items():
    # Check both original and normalized descriptions for maximum coverage
    for kw in keywords:
        normalized_kw = re.sub(r'[-_]', ' ', kw.lower())
        if normalized_kw in normalized_desc or kw in device_description:
            triggered_ids = auto_triggers.get(trigger_name, [])
            selected_ids.update(triggered_ids)
            break  # Found match for this trigger, no need to check other keywords

# Get question details
questions = question_bank.get("questions", [])
selected_questions = [q for q in questions if q.get("id") in selected_ids]

# Filter by applicable_meeting_types (EDGE-1 fix)
# Questions may specify which meeting types they apply to; skip questions
# that are not applicable to the current meeting type
filtered_questions = []
for q in selected_questions:
    applicable = q.get("applicable_meeting_types", [])
    if isinstance(applicable, list) and len(applicable) > 0:
        if meeting_type not in applicable and "all" not in applicable:
            print(f"NOTE: Skipping {q.get('id', '')} - not applicable to {meeting_type} meeting type", file=sys.stderr)
            continue
    filtered_questions.append(q)
selected_questions = filtered_questions

# Filter by applicable_pathways (NEW - TICKET-004)
# Questions may specify which regulatory pathways they apply to; skip questions
# that are not applicable to the current pathway
pathway_filtered = []
for q in selected_questions:
    applicable_pathways = q.get("applicable_pathways", [])
    if isinstance(applicable_pathways, list) and len(applicable_pathways) > 0:
        if regulatory_pathway not in applicable_pathways and "all" not in applicable_pathways:
            print(f"NOTE: Skipping {q.get('id', '')} - not applicable to {regulatory_pathway} pathway", file=sys.stderr)
            continue
    pathway_filtered.append(q)
selected_questions = pathway_filtered

# Deduplicate question IDs (EDGE-3 fix)
# If auto-trigger logic or defaults select the same question twice, remove duplicates
seen_ids = set()
unique_questions = []
for q in selected_questions:
    qid = q.get("id", "")
    if qid and qid not in seen_ids:
        seen_ids.add(qid)
        unique_questions.append(q)
    elif qid:
        print(f"WARNING: Duplicate question ID {qid} skipped", file=sys.stderr)
selected_questions = unique_questions

# Sort by priority (descending)
selected_questions.sort(key=lambda q: q.get("priority", 0), reverse=True)

# Limit to 10 questions max (expanded for multi-pathway support - TICKET-004)
# 510(k) typically needs 5-7; PMA/IDE/De Novo may need up to 10
max_questions = 10 if regulatory_pathway in ("pma", "ide", "de_novo") else 7
selected_questions = selected_questions[:max_questions]

# Format output
question_count = len(selected_questions)
question_list = []
for i, q in enumerate(selected_questions, 1):
    question_list.append(f"Q{i}:{q['id']}:{q['text']}")

# Export for presub_metadata.json
question_ids_json = json.dumps([q['id'] for q in selected_questions])

# Validate question selection result (BREAK-1 fix)
# Warn if no questions were selected - this may result in incomplete submission
if question_count == 0:
    print("WARNING: No questions were selected for this Pre-Sub package!", file=sys.stderr)
    print("This may result in an incomplete submission.", file=sys.stderr)
    print("Consider:", file=sys.stderr)
    print("  1. Providing --device-description with more detail", file=sys.stderr)
    print("  2. Manually editing presub_metadata.json to add question IDs", file=sys.stderr)
    print("  3. Using --meeting-type to select appropriate meeting type", file=sys.stderr)
    print("  4. Checking that question bank is not empty", file=sys.stderr)

print(f"QUESTION_COUNT:{question_count}")
print(f"QUESTION_IDS:{question_ids_json}")
for q_line in question_list:
    print(q_line)

PYEOF
)

# Parse question selection results
export QUESTION_COUNT=$(echo "$QUESTION_SELECTION_RESULT" | grep "^QUESTION_COUNT:" | cut -d':' -f2)
export QUESTION_IDS=$(echo "$QUESTION_SELECTION_RESULT" | grep "^QUESTION_IDS:" | cut -d':' -f2-)
export SELECTED_QUESTIONS=$(echo "$QUESTION_SELECTION_RESULT" | grep "^Q[0-9]")

echo "Selected $QUESTION_COUNT questions for $MEETING_TYPE meeting"
```

## Step 3.6: Load Template File (UPDATED - TICKET-004)

Based on the regulatory pathway AND meeting type, load the appropriate template file from data/templates/presub_meetings/.

**Template Selection Logic (TICKET-004):**
- For PMA, IDE, or De Novo pathways: use pathway-specific templates (pma_presub.md, ide_presub.md, de_novo_presub.md)
- For 510(k) pathway: use meeting-type-specific templates (formal_meeting.md, written_response.md, etc.)
- Pathway-specific templates take priority over meeting-type templates when pathway is not 510(k)

```bash
# Determine template based on pathway first, then meeting type (TICKET-004)
if [ "$REGULATORY_PATHWAY" = "pma" ]; then
    TEMPLATE_FILE="pma_presub.md"
elif [ "$REGULATORY_PATHWAY" = "ide" ]; then
    TEMPLATE_FILE="ide_presub.md"
elif [ "$REGULATORY_PATHWAY" = "de_novo" ]; then
    TEMPLATE_FILE="de_novo_presub.md"
else
    # 510(k) pathway: use meeting-type-specific templates
    case "$MEETING_TYPE" in
        formal)
            TEMPLATE_FILE="formal_meeting.md"
            ;;
        written)
            TEMPLATE_FILE="written_response.md"
            ;;
        info)
            TEMPLATE_FILE="info_meeting.md"
            ;;
        pre-ide)
            TEMPLATE_FILE="pre_ide.md"
            ;;
        administrative)
            TEMPLATE_FILE="administrative_meeting.md"
            ;;
        info-only)
            TEMPLATE_FILE="info_only.md"
            ;;
        *)
            TEMPLATE_FILE="formal_meeting.md"  # Default fallback
            ;;
    esac
fi

TEMPLATE_PATH="$FDA_PLUGIN_ROOT/data/templates/presub_meetings/$TEMPLATE_FILE"

if [ ! -f "$TEMPLATE_PATH" ]; then
    echo "ERROR: Template file not found: $TEMPLATE_PATH"
    echo "Falling back to formal_meeting.md"
    TEMPLATE_FILE="formal_meeting.md"
    TEMPLATE_PATH="$FDA_PLUGIN_ROOT/data/templates/presub_meetings/$TEMPLATE_FILE"
fi

export TEMPLATE_FILE
export TEMPLATE_PATH
export TEMPLATE_USED="$TEMPLATE_FILE"

echo "Using template: $TEMPLATE_FILE (pathway: $REGULATORY_PATHWAY, meeting: $MEETING_TYPE)"
```

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

### Step 4.1: Populate Template with Data (NEW - TICKET-001)

Read the template file loaded in Step 3.6 and populate all {placeholder} variables with available data.

```bash
python3 << 'PYEOF'
import os, json, re
from datetime import datetime, timedelta

# Read template file
template_path = os.environ.get("TEMPLATE_PATH", "")
if not template_path or not os.path.exists(template_path):
    print("ERROR: Template file not found")
    exit(1)

with open(template_path) as f:
    template_content = f.read()

# Gather all available data
product_code = os.environ.get("PRODUCT_CODE", "")
device_class = os.environ.get("DEVICE_CLASS", "")
regulation_number = os.environ.get("REGULATION_NUMBER", "")
classification_device_name = os.environ.get("CLASSIFICATION_DEVICE_NAME", "")
review_panel = os.environ.get("REVIEW_PANEL", "")
device_description = os.environ.get("DEVICE_DESCRIPTION", "")
intended_use = os.environ.get("INTENDED_USE", "")
meeting_type = os.environ.get("MEETING_TYPE", "formal")
question_count = os.environ.get("QUESTION_COUNT", "0")
selected_questions_raw = os.environ.get("SELECTED_QUESTIONS", "")

# Parse selected questions
selected_questions = []
if selected_questions_raw:
    for line in selected_questions_raw.split('\n'):
        if line.startswith('Q'):
            parts = line.split(':', 2)
            if len(parts) == 3:
                q_num = parts[0]
                q_id = parts[1]
                q_text = parts[2]
                selected_questions.append({
                    'num': q_num,
                    'id': q_id,
                    'text': q_text
                })

# Format auto-generated questions
auto_generated_questions = ""
if selected_questions:
    for q in selected_questions:
        auto_generated_questions += f"### {q['num']}: {q['id']}\n\n{q['text']}\n\n"
else:
    auto_generated_questions = "[TODO: Company-specific — Add specific questions for FDA]\n\n"

# Format question summary list for cover letter
question_summary_list = ""
if selected_questions:
    for q in selected_questions:
        # Extract first sentence or 80 chars of question text
        summary = q['text'].split('.')[0][:80]
        question_summary_list += f"- {summary}\n"
else:
    question_summary_list = "- Predicate selection strategy\n- Testing requirements and standards\n"

# Get current date and calculate timeline dates
today = datetime.now()
generated_date = today.strftime("%Y-%m-%d")
cover_letter_date = today.strftime("%B %d, %Y")
presub_prep_date = (today + timedelta(weeks=2)).strftime("%Y-%m-%d")
presub_submission_date = (today + timedelta(weeks=4)).strftime("%Y-%m-%d")
fda_deadline_date = (today + timedelta(days=75, weeks=4)).strftime("%Y-%m-%d")
expected_feedback_date = fda_deadline_date
target_510k_date = (today + timedelta(weeks=20)).strftime("%Y-%m-%d")

# Build placeholder mapping
placeholders = {
    # Classification data
    'product_code': product_code,
    'device_class': device_class,
    'regulation_number': regulation_number,
    'classification_device_name': classification_device_name,
    'review_panel': review_panel,

    # Device information
    'device_description': device_description if device_description else "[TODO: Company-specific — Device description]",
    'device_description_short': device_description[:100] if device_description else "[TODO: Short device description]",
    'intended_use': intended_use if intended_use else "[TODO: Company-specific — Indications for use]",
    'primary_use_summary': "[TODO: Primary clinical use]",
    'device_type_category': "a medical device",

    # Meeting information
    'meeting_type': meeting_type,
    'meeting_format': 'teleconference' if meeting_type in ['formal', 'written', 'administrative'] else 'informational',
    'question_count': question_count,

    # Questions
    'auto_generated_questions': auto_generated_questions,
    'question_summary_list': question_summary_list,

    # Dates
    'generated_date': generated_date,
    'cover_letter_date': cover_letter_date,
    'presub_prep_date': presub_prep_date,
    'presub_submission_date': presub_submission_date,
    'fda_deadline_date': fda_deadline_date,
    'expected_feedback_date': expected_feedback_date,
    'target_510k_date': target_510k_date,

    # Contact information (placeholders for company to fill)
    'applicant_name': "[TODO: Company Name]",
    'contact_first_name': "[TODO: First Name]",
    'contact_last_name': "[TODO: Last Name]",
    'contact_title': "[TODO: Title]",
    'contact_email': "[TODO: email@company.com]",
    'contact_phone': "[TODO: Phone]",
    'device_trade_name': "[TODO: Device Trade Name]",

    # FDA office mapping
    'review_division_name': f"Division of {review_panel}" if review_panel else "[TODO: Division Name]",
    'office_name': f"Office of {review_panel.split()[0] if review_panel else 'Device Evaluation'}",

    # Features (placeholders)
    'feature_1': "[TODO: Key feature 1]",
    'feature_2': "[TODO: Key feature 2]",
    'feature_3': "[TODO: Key feature 3]",

    # Additional placeholders
    'principle_of_operation': "[TODO: Company-specific — How the device works]",
    'components_list': "[TODO: Company-specific — Device components]",
    'materials_list': "[TODO: Company-specific — Materials in patient contact]",
    'dimensions': "[TODO: Dimensions]",
    'weight': "[TODO: Weight]",
    'sterilization_method': "[TODO: Sterilization method]",
    'shelf_life_claim': "[TODO: Shelf life]",
    'rx_otc': "Rx (Prescription Use)",

    # Predicate placeholders
    'predicate_analysis_table': "[TODO: Company-specific — Run /fda:review to select predicates]",
    'primary_predicate_k_number': "[TODO: K-number]",
    'primary_predicate_device_name': "[TODO: Device name]",
    'primary_predicate_applicant': "[TODO: Applicant]",
    'primary_predicate_decision_date': "[TODO: Date]",
    'primary_predicate_product_code': product_code,
    'se_rationale_summary': "[TODO: Company-specific — SE rationale]",

    # Testing placeholders
    'biocompatibility_testing_plan': "[TODO: Company-specific — Biocompatibility testing plan]",
    'biocompat_endpoints_list': "Cytotoxicity, Sensitization, Irritation",
    'performance_testing_plan': "[TODO: Company-specific — Performance testing plan]",
    'performance_standards_list': "[TODO: Applicable standards]",
    'sterilization_testing_plan': "[TODO: Company-specific — Sterilization validation]",
    'sterilization_standards': "ISO 11135 or ISO 11137",
    'electrical_testing_plan': "[TODO: Company-specific — Electrical safety testing]",
    'software_testing_plan': "[TODO: Company-specific — Software V&V]",
    'software_level': "[TODO: Level of Concern]",
    'clinical_data_summary': "[TODO: Company-specific — Clinical data or rationale for exemption]",

    # Regulatory background
    'standards_list': "[TODO: Company-specific — Run /fda:standards {product_code}]",
    'additional_guidance_list': "[TODO: Device-specific guidance documents]",
    'safety_intelligence_summary': "[TODO: Company-specific — Run /fda:safety {product_code}]",
    'maude_event_count': "[TODO]",
    'recall_count': "[TODO]",
    'literature_summary': "[TODO: Company-specific — Run /fda:literature]",
    'competitive_analysis': "[TODO: Company-specific — Market analysis]",

    # Project metadata
    'project_name': os.environ.get("PROJECT_NAME", "[TODO: Project Name]"),

    # Pathway (UPDATED - TICKET-004)
    'proposed_pathway': {
        "510k": "Traditional 510(k)",
        "pma": "Premarket Approval (PMA)",
        "ide": "Investigational Device Exemption (IDE)",
        "de_novo": "De Novo Classification Request"
    }.get(os.environ.get("REGULATORY_PATHWAY", "510k"), "Traditional 510(k)"),
    'pathway_rationale': os.environ.get("PATHWAY_RATIONALE", "[TODO: Company-specific — Pathway selection rationale]"),

    # Additional meeting-type specific placeholders
    'development_status': "[TODO: Current development stage]",
    'preliminary_testing_summary': "[TODO: Preliminary testing completed]",
    'classification_uncertainty': "[TODO: Classification questions]",
    'pathway_option_1': "Traditional 510(k)",
    'pathway_rationale_1': "[TODO: Traditional pathway rationale]",
    'pathway_advantages_1': "[TODO: Advantages]",
    'pathway_concerns_1': "[TODO: Concerns]",
    'pathway_option_2': "De Novo",
    'pathway_rationale_2': "[TODO: De Novo pathway rationale]",
    'pathway_advantages_2': "[TODO: Advantages]",
    'pathway_concerns_2': "[TODO: Concerns]",

    # Pluralization helpers
    's': 's' if int(question_count) != 1 else '',
    'is_are': 'are' if int(question_count) != 1 else 'is',
}

# Replace all {placeholder} variables
populated_content = template_content
for key, value in placeholders.items():
    placeholder_pattern = '{' + key + '}'
    populated_content = populated_content.replace(placeholder_pattern, str(value))

# Detect unfilled placeholders (BREAK-2 fix)
# After template population, scan for any remaining {PLACEHOLDER} patterns
# that were not replaced by actual data
unfilled = re.findall(r'\{[A-Za-z_]+\}', populated_content)
# Filter out common false positives (markdown code blocks, JSON examples)
unfilled_real = [p for p in unfilled if not p.startswith('{#') and p not in ('{', '}')]
if unfilled_real:
    unique_unfilled = sorted(set(unfilled_real))
    print(f"WARNING: {len(unique_unfilled)} placeholder(s) remain unfilled in template:", file=sys.stderr)
    for placeholder in unique_unfilled[:10]:
        print(f"  {placeholder}", file=sys.stderr)
    if len(unique_unfilled) > 10:
        print(f"  ... and {len(unique_unfilled) - 10} more", file=sys.stderr)
    print("", file=sys.stderr)
    print("Review presub_plan.md and fill in these sections before submission.", file=sys.stderr)

# Also detect [TODO: ...] markers and report count
todo_markers = re.findall(r'\[TODO:[^\]]*\]', populated_content)
if todo_markers:
    unique_todos = sorted(set(todo_markers))
    print(f"INFO: {len(unique_todos)} [TODO:] sections require company-specific input", file=sys.stderr)

# Write populated template to output file
project_name = os.environ.get("PROJECT_NAME", "")
if project_name:
    projects_dir = os.path.expanduser("~/fda-510k-data/projects")
    output_path = os.path.join(projects_dir, project_name, "presub_plan.md")
else:
    output_path = "presub_plan.md"

# Create parent directory if needed
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, 'w') as f:
    f.write(populated_content)

print(f"PRESUB_PLAN_WRITTEN:{output_path}")
print(f"TEMPLATE_USED:{os.environ.get('TEMPLATE_FILE', '')}")
print(f"QUESTIONS_POPULATED:{len(selected_questions)}")
print(f"PLACEHOLDERS_TOTAL:{len(placeholders)}")

PYEOF
```

The populated template is now written. Continue with the legacy inline markdown generation below for backward compatibility:

```markdown
# Pre-Submission Meeting Request
## {Device Description} — Product Code {CODE}

**Date:** {today's date}
**Requested Meeting Type:** {meeting_type}
**Product Code:** {CODE} — {device_name}
**Generated:** {today's date} | v5.22.0
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

### 4.2 Proposed Predicate Device(s) — Deep Analysis

**Flag:** `--deep-predicate-analysis` controls this section (default: ON when predicates available, OFF when no predicates). Use `--no-deep-predicate-analysis` to revert to the simple table.

{If no predicates available:}
[TODO: Company-specific — Proposed predicate device(s) with K-numbers and justification. Run `/fda:propose --predicates K123456 --project NAME` to declare predicates.]

{If predicates available from review.json — proceed with all 7 subsections below:}

#### 4.2.1 Predicate Summary Table

| # | K-Number | Device Name | Applicant | Cleared | Score | Flags | Mode |
|---|----------|-------------|-----------|---------|-------|-------|------|
| 1 | {K-number} | {name} | {company} | {date} | {score}/100 | {flags} | {manual/extracted} |
| 2 | {K-number} | {name} | {company} | {date} | {score}/100 | {flags} | {manual/extracted} |

{If `review_mode == "manual"` in review.json:}
**Note:** These predicates were manually proposed via `/fda:propose`, not extracted from PDF analysis. Confidence scores reflect manual proposal scoring (see `references/predicate-analysis-framework.md`).

{If reference_devices key exists in review.json:}

**Reference Devices** (cited for specific feature comparison, not as predicates):

| # | K-Number | Device Name | Applicant | Cleared | Purpose |
|---|----------|-------------|-----------|---------|---------|
| 1 | {K-number} | {name} | {company} | {date} | {rationale} |

#### 4.2.2 Intended Use Comparison

For each accepted predicate, compare IFU against the subject device.

**Data source:** Extract IFU from predicate PDF text using the **3-tier section detection system from `references/section-patterns.md`**. EU-origin predicates may use "Intended Purpose" instead of "Indications for Use" — Tier 3 semantic mapping handles this automatically. If `--intended-use` was provided to propose or presub, use that as the subject IFU.

{Fetch predicate PDF text using the same download approach as `compare-se.md` Step 2. Extract IFU section.}

```markdown
| Aspect | Subject Device | Predicate: {K-number} | Predicate: {K-number} |
|--------|---------------|----------------------|----------------------|
| Target population | {subject pop} | {predicate pop} | {predicate pop} |
| Clinical indication | {subject indication} | {predicate indication} | {predicate indication} |
| Anatomical site | {subject site} | {predicate site} | {predicate site} |
| Duration of use | {subject duration} | {predicate duration} | {predicate duration} |
| Use environment | {subject env} | {predicate env} | {predicate env} |
```

**Keyword Overlap Analysis:**

| Predicate | Overlap Score | Shared Keywords | Assessment |
|-----------|--------------|-----------------|------------|
| {K-number} | {N}% | {top keywords} | {STRONG/MODERATE/LOW} OVERLAP |

{If subject IFU not available:}
[TODO: Company-specific — Provide intended use via `--intended-use TEXT` or fill in the Subject Device column to enable IFU comparison]

Use the IFU comparison methodology from `references/predicate-analysis-framework.md` Section 1.

#### 4.2.3 Technological Characteristics Comparison

For each predicate, compare key technological characteristics:

{Extract device description, materials, and technical specs from predicate PDF text using the **3-tier section detection system from `references/section-patterns.md`**.}

```markdown
| Characteristic | Subject Device | Predicate: {K-number} | Comparison |
|----------------|---------------|----------------------|------------|
| Principle of operation | {subject} | {predicate} | Same/Similar/Different |
| Materials of construction | {subject} | {predicate} | Same/Similar/Different |
| Energy source | {subject} | {predicate} | Same/Similar/Different |
| Software | {subject} | {predicate} | Same/Similar/Different |
| Key performance specs | {subject} | {predicate} | Same/Similar/Different |
```

{If `--device-description` available: auto-populate Subject Device column}
{If not: mark as "[TODO: Company-specific — specify]"}

For each "Different" entry, note: "May require additional testing per {applicable standard}."

Use technological characteristics templates from `references/predicate-analysis-framework.md` Section 2, device-type-specific rows from `compare-se.md`.

#### 4.2.4 Regulatory History Analysis

For each predicate, assess regulatory history using openFDA data:

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

knumber = "KNUMBER"  # Replace per predicate
product_code = "PRODUCTCODE"  # Replace

if api_enabled:
    # MAUDE events for product code
    params = {"search": f'device.device_report_product_code:"{product_code}"', "count": "event_type.exact"}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/event.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            for r in data.get('results', []):
                print(f"EVENT:{r['term']}|{r['count']}")
    except Exception as e:
        print(f"MAUDE_ERROR:{e}")

    # Recall check for specific K-number
    params2 = {"search": f'k_number:"{knumber}"', "limit": "100"}
    if api_key:
        params2["api_key"] = api_key
    url2 = f"https://api.fda.gov/device/recall.json?{urllib.parse.urlencode(params2)}"
    req2 = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})
    try:
        with urllib.request.urlopen(req2, timeout=15) as resp2:
            data2 = json.loads(resp2.read())
            total = data2.get('meta', {}).get('results', {}).get('total', 0)
            print(f"RECALL_TOTAL:{total}")
    except:
        print("RECALL_TOTAL:0")
PYEOF
```

Present per-predicate regulatory history:

```markdown
| Predicate | MAUDE Events | Recalls | Risk Level | Predicate Age | Decision Type |
|-----------|-------------|---------|------------|---------------|---------------|
| {K-number} | {event_count} | {recall_count} | {Low/Moderate/High} | {years} years | {SESE/SESD/SESU} |
```

{For each high-risk predicate:}
**{K-number} Risk Assessment:** {Explain the risk factors and how they may affect the Pre-Sub discussion. Reference specific MAUDE event types or recall root causes.}

Use methodology from `references/predicate-analysis-framework.md` Section 3.

#### 4.2.5 Predicate Chain Analysis

For each primary predicate, trace the predicate chain 2 generations deep:

{Use the simplified lineage approach from `lineage.md` — fetch predicate PDF, extract cited K-numbers from SE section, then repeat one more level.}

```markdown
#### Predicate Chain: {K-number}

{K-number} (2023) ← {K-parent} (2018) ← {K-grandparent} (2014)
Chain length: 3 generations | Span: 9 years
Chain health: {score}/100 — {Healthy/Moderate/Concerning}

{If chain health issues:}
Issues:
- {issue description}
```

**Chain Health Scoring** (from `references/predicate-analysis-framework.md` Section 4):
- Deduct points for recalled devices, excessive chain length, IFU drift, technology drift
- Score 80-100: Healthy chain, no issues
- Score 50-79: Moderate — some concerns to discuss with FDA
- Score <50: Concerning — consider alternative predicates

#### 4.2.6 Gap Analysis

Based on the IFU and technological characteristics comparisons, identify gaps that need testing or FDA discussion:

```markdown
| # | Gap | Type | Severity | Testing Needed | Pre-Sub Question? |
|---|-----|------|----------|----------------|-------------------|
| 1 | {description} | TESTING_GAP | {H/M/L} | {standard/method} | Yes — Q{N} |
| 2 | {description} | DATA_GAP | {H/M/L} | {data source} | Yes — Q{N} |
| 3 | {description} | SE_BARRIER | {H} | N/A — fundamental difference | Yes — Q{N} |
```

Use the gap analysis decision tree from `references/predicate-analysis-framework.md` Section 5.

**Auto-Generate FDA Questions from Gaps:**
For each identified gap, auto-generate a corresponding FDA question using the gap-to-question templates. These feed into Section 5 (Questions for FDA).

#### 4.2.7 Predicate Justification Narrative

For each accepted predicate, generate a 1-2 paragraph regulatory narrative:

{Use the template from `references/predicate-analysis-framework.md` Section 6:}

> **{K-number} ({device_name}, {applicant}, cleared {date})**
>
> {Paragraph 1: Predicate identification and relevance — same intended use, classification, applicant relationship}
>
> {Paragraph 2: SE basis — shared technological characteristics, addressed differences, planned testing}

{Generate one narrative per predicate. Use professional regulatory tone — no marketing language.}

---

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
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})
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
params = {"search": f'product_code:"{product_code}"', "limit": "100", "sort": "event_date_terminated:desc"}
if api_key:
    params["api_key"] = api_key
url = f"https://api.fda.gov/device/recall.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})
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

After generating the Pre-Sub plan, write audit log entries using `fda_audit_logger.py`. Only log if `--project` is specified.

### Log Q-Sub type recommendation

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command presub \
  --action qsub_type_recommended \
  --subject "$PRODUCT_CODE" \
  --decision "$QSUB_TYPE" \
  --mode "$MODE" \
  --decision-type auto \
  --rationale "Recommended $QSUB_TYPE based on $RATIONALE_SUMMARY" \
  --data-sources "openFDA classification,fda-guidance-index.md" \
  --alternatives '["Formal Q-Sub Meeting","Written Feedback Only","Informational Meeting","Pre-IDE"]' \
  --exclusions "$EXCLUDED_QSUB_JSON"
```

### Log predicate placeholder resolution

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command presub \
  --action placeholder_resolved \
  --subject "predicate_analysis" \
  --decision "resolved" \
  --mode "$MODE" \
  --rationale "Resolved $RESOLVED_COUNT placeholders from $DATA_SOURCE" \
  --data-sources "$DATA_SOURCE" \
  --metadata "{\"resolved_count\":$RESOLVED_COUNT,\"remaining_placeholders\":$REMAINING_COUNT}"
```

### Log testing gap summary

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command presub \
  --action testing_gap_identified \
  --subject "$PRODUCT_CODE" \
  --decision "gaps_found" \
  --mode "$MODE" \
  --rationale "Identified $GAP_COUNT testing gaps across $CATEGORY_COUNT categories" \
  --data-sources "fda-guidance-index.md,guidance-lookup.md" \
  --metadata "{\"gap_count\":$GAP_COUNT,\"categories\":$CATEGORY_LIST_JSON}"
```

### Log FDA question generation

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command presub \
  --action data_synthesized \
  --subject "fda_questions" \
  --decision "synthesized" \
  --mode "$MODE" \
  --rationale "Generated $QUESTION_COUNT FDA questions from guidance analysis and gap findings" \
  --data-sources "fda-guidance-index.md,review.json,guidance cache" \
  --metadata "{\"question_count\":$QUESTION_COUNT}"
```

### Log document generation (at completion)

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command presub \
  --action document_generated \
  --subject "$PRODUCT_CODE" \
  --decision "generated" \
  --mode "$MODE" \
  --rationale "Pre-Sub plan generated with $SECTION_COUNT sections, $QUESTION_COUNT FDA questions" \
  --files-written "$OUTPUT_PATH" \
  --metadata "{\"sections\":$SECTION_COUNT,\"questions\":$QUESTION_COUNT,\"placeholders_remaining\":$REMAINING_COUNT}"
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
  1. Fill in [TODO: ...] placeholders with your device-specific information
  2. Review auto-generated FDA questions — add, modify, or remove as needed
  3. Have your regulatory team review the complete package
  4. Submit to FDA via the Pre-Submission program
```

## Step 6: Generate Pre-Sub Metadata (NEW - TICKET-001)

Generate structured `presub_metadata.json` to capture meeting data for PreSTAR XML generation:

```bash
python3 << 'PYEOF'
import json, os, sys
from datetime import datetime, timezone

# Get project directory
project_name = os.environ.get("PROJECT_NAME", "")
projects_dir = os.path.expanduser("~/fda-510k-data/projects")
project_dir = os.path.join(projects_dir, project_name) if project_name else ""

if not project_dir or not os.path.exists(project_dir):
    print("METADATA_SKIPPED:no_project_directory")
    exit(0)

# Build metadata dict (UPDATED - TICKET-004: added pathway fields)
metadata = {
    "version": "2.0",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "meeting_type": os.environ.get("MEETING_TYPE", "formal"),
    "regulatory_pathway": os.environ.get("REGULATORY_PATHWAY", "510k"),
    "pathway_detection_method": os.environ.get("PATHWAY_DETECTION_METHOD", "auto"),
    "pathway_rationale": os.environ.get("PATHWAY_RATIONALE", ""),
    "detection_method": os.environ.get("DETECTION_METHOD", "auto"),
    "detection_rationale": os.environ.get("DETECTION_RATIONALE", ""),
    "product_code": os.environ.get("PRODUCT_CODE", ""),
    "device_class": os.environ.get("DEVICE_CLASS", ""),
    "device_description": os.environ.get("DEVICE_DESCRIPTION", ""),
    "intended_use": os.environ.get("INTENDED_USE", ""),
    "questions_generated": json.loads(os.environ.get("QUESTION_IDS", "[]")),
    "question_count": int(os.environ.get("QUESTION_COUNT", "0")),
    "template_used": os.environ.get("TEMPLATE_USED", ""),
    "fda_form": "FDA-5064",
    "expected_timeline_days": 75,
    "auto_triggers_fired": os.environ.get("AUTO_TRIGGERS", "").split(",") if os.environ.get("AUTO_TRIGGERS") else [],
    "data_sources_used": ["classification", "review.json", "guidance_cache"],
    "metadata": {
        "placeholder_count": int(os.environ.get("PLACEHOLDER_COUNT", "0")),
        "auto_filled_fields": os.environ.get("AUTO_FILLED_FIELDS", "").split(",") if os.environ.get("AUTO_FILLED_FIELDS") else [],
        "question_bank_version": "2.0",
        "pathway_specific_questions": len([q for q in json.loads(os.environ.get("QUESTION_IDS", "[]")) if q.startswith(("PMA-", "IDE-", "DENOVO-"))])
    }
}

# Validate metadata schema (HIGH-2 fix)
required_fields = ["version", "meeting_type", "questions_generated", "question_count", "fda_form"]
missing_fields = [f for f in required_fields if f not in metadata]
if missing_fields:
    print(f"ERROR: Metadata missing required fields: {', '.join(missing_fields)}", file=sys.stderr)
    sys.exit(1)

# Validate data types
if not isinstance(metadata["questions_generated"], list):
    print("ERROR: questions_generated must be a list", file=sys.stderr)
    sys.exit(1)
if not isinstance(metadata["question_count"], int):
    print("ERROR: question_count must be an integer", file=sys.stderr)
    sys.exit(1)

# Validate version
if metadata["version"] not in ["1.0", "2.0"]:
    print(f"WARNING: Metadata version {metadata['version']} may be incompatible", file=sys.stderr)

# Write metadata file atomically (RISK-1 fix)
# Use temp file + rename to prevent corruption on interrupt
import tempfile
metadata_path = os.path.join(project_dir, "presub_metadata.json")
temp_fd, temp_path = tempfile.mkstemp(dir=project_dir, suffix=".json.tmp", prefix="presub_metadata_")
try:
    # Write to temp file
    with os.fdopen(temp_fd, "w") as f:
        json.dump(metadata, f, indent=2)

    # Atomic rename (overwrites existing file)
    os.replace(temp_path, metadata_path)
    print(f"METADATA_WRITTEN:{metadata_path}")
except Exception as e:
    # Clean up temp file on error
    try:
        os.unlink(temp_path)
    except:
        pass
    print(f"ERROR: Failed to write metadata: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
```

Report metadata generation:
```
Pre-Sub metadata generated: {metadata_path}
  Regulatory Pathway: {regulatory_pathway} ({pathway_detection_method})
  Meeting Type: {meeting_type} ({detection_method})
  Questions: {question_count} generated
  Template: {template_used}
  FDA Form: FDA-5064 (PreSTAR)
  Schema Version: 2.0
```

## Step 7: Generate PreSTAR XML (NEW - TICKET-001)

Generate PreSTAR XML for FDA eSTAR import (if project directory exists):

```bash
# Only generate XML if we have a project directory
if [ -n "$PROJECT_NAME" ] && [ -d "$PROJECTS_DIR/$PROJECT_NAME" ]; then
    python3 "$FDA_PLUGIN_ROOT/scripts/estar_xml.py" generate \
        --project "$PROJECT_NAME" \
        --template PreSTAR \
        --format real \
        --output "$PROJECTS_DIR/$PROJECT_NAME/presub_prestar.xml"

    # Check if XML generation succeeded
    if [ -f "$PROJECTS_DIR/$PROJECT_NAME/presub_prestar.xml" ]; then
        echo ""
        echo "PreSTAR XML generated: $PROJECTS_DIR/$PROJECT_NAME/presub_prestar.xml"
        echo "  Template: PreSTAR (FDA 5064)"
        echo "  Questions: Populated from presub_metadata.json"
        echo "  Fields: Administrative info, device description, IFU, questions"
        echo ""
        echo "Next steps for XML:"
        echo "  1. Open FDA PreSTAR template PDF (Form FDA 5064)"
        echo "  2. In Adobe Acrobat: Form > Import Data"
        echo "  3. Select presub_prestar.xml"
        echo "  4. Review populated fields and add attachments"
        echo "  5. See docs/estar-workflow.md for detailed instructions"
    fi
else
    echo "PRESTAR_XML_SKIPPED:no_project_directory"
fi
```

Update final report to include XML status and pathway:
```
Pre-Submission plan written to: {output_path}

Regulatory Pathway: {regulatory_pathway} ({pathway_detection_method})

The plan includes:
  • Cover letter template ({pathway}-specific)
  • Device description section {auto-populated / template}
  • Proposed regulatory strategy: {pathway}
  {510k: • Predicate justification: {count} predicates {with scores / template}}
  {pma: • Clinical study design and benefit-risk assessment}
  {ide: • SR/NSR risk determination and study protocol}
  {de_novo: • Special controls proposal and risk assessment}
  • {N} FDA questions auto-generated ({pathway}-specific)
  • Testing strategy: {from guidance / template}
  • PreSTAR XML: Ready for FDA eSTAR import

Files generated:
  1. presub_plan.md — Markdown for human review
  2. presub_metadata.json — Structured meeting data (v2.0 schema)
  3. presub_prestar.xml — FDA eSTAR import-ready XML

Next steps:
  1. Fill in [TODO: ...] placeholders in presub_plan.md
  2. Review auto-generated FDA questions — add, modify, or remove as needed
  3. Import presub_prestar.xml into FDA PreSTAR template (Form FDA 5064)
  4. Have your regulatory team review the complete package
  5. Submit to FDA via the Pre-Submission program
```

## Subcommand: --track (FDA Correspondence Tracking)

When `--track` is specified, log a new FDA correspondence entry instead of generating a Pre-Sub package.

### Parse --track Arguments

- `--track` — Enter correspondence logging mode
- `--project NAME` (required with --track) — Project to associate correspondence
- `--type presub_response|rta_deficiency|fda_question|commitment` — Entry type (default: presub_response)
- `--date YYYY-MM-DD` — Date of correspondence (default: today)
- `--summary TEXT` — Brief summary of the correspondence
- `--action-items "item1;item2;item3"` — Semicolon-separated action items
- `--deadline YYYY-MM-DD` — Deadline for action items (optional)
- `--status open|resolved|overdue` — Entry status (default: open)

### Correspondence Storage

Store correspondence in `$PROJECTS_DIR/$PROJECT_NAME/fda_correspondence.json`:

```json
{
  "entries": [
    {
      "id": 1,
      "type": "presub_response",
      "date": "2026-02-07",
      "summary": "FDA recommended additional biocompatibility testing per ISO 10993-1:2025",
      "action_items": ["Update biocompatibility test plan", "Add cytotoxicity testing"],
      "deadline": "2026-04-15",
      "status": "open",
      "resolution": null,
      "created_at": "2026-02-07T12:00:00Z"
    }
  ]
}
```

### --track Implementation

```bash
python3 << 'PYEOF'
import json, os
from datetime import datetime, timezone

project_dir = os.path.expanduser("~/fda-510k-data/projects/PROJECT_NAME")
corr_path = os.path.join(project_dir, "fda_correspondence.json")

# Load existing or create new
if os.path.exists(corr_path):
    with open(corr_path) as f:
        data = json.load(f)
else:
    data = {"entries": []}

# Determine next ID
next_id = max([e.get("id", 0) for e in data["entries"]], default=0) + 1

# Create new entry (replace placeholders)
entry = {
    "id": next_id,
    "type": "ENTRY_TYPE",        # Replace with actual
    "date": "ENTRY_DATE",         # Replace with actual
    "summary": "ENTRY_SUMMARY",   # Replace with actual
    "action_items": [],            # Replace with actual parsed list
    "deadline": None,              # Replace with actual or None
    "status": "open",
    "resolution": None,
    "created_at": datetime.now(timezone.utc).isoformat()
}

data["entries"].append(entry)

os.makedirs(project_dir, exist_ok=True)
with open(corr_path, "w") as f:
    json.dump(data, f, indent=2)

print(f"ENTRY_ID:{next_id}")
print(f"ENTRIES_TOTAL:{len(data['entries'])}")
PYEOF
```

Report:
```
Correspondence entry logged:
  ID:      {id}
  Type:    {type}
  Date:    {date}
  Summary: {summary}
  Actions: {count} items
  Deadline: {deadline or "None"}
  Status:  open

Total entries in project: {total}

Next steps:
  • View correspondence: /fda:presub --correspondence --project {name}
  • Update status: /fda:presub --track --project {name} --resolve {id}
  • View project status: /fda:status --project {name}
```

## Subcommand: --correspondence (View History)

When `--correspondence` is specified, display the correspondence history for a project.

### --correspondence Implementation

Read `$PROJECTS_DIR/$PROJECT_NAME/fda_correspondence.json` and display:

```
  FDA Correspondence History
  Project: {project_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Source: Project Data | v5.22.0

SUMMARY
────────────────────────────────────────
  Total entries:  {count}
  Open:           {open_count}
  Overdue:        {overdue_count}
  Resolved:       {resolved_count}

ENTRIES
────────────────────────────────────────

  #{id} [{status}] {type}
  Date:     {date}
  Summary:  {summary}
  Actions:  {action_items}
  Deadline: {deadline} ({days_remaining} days remaining)
  ---

OVERDUE ITEMS
────────────────────────────────────────
  ⚠ #{id}: {summary} — deadline was {deadline} ({days_overdue} days ago)

────────────────────────────────────────
  This report is AI-generated from project data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

Check for overdue items: any entry with `status: "open"` and `deadline` before today's date. Flag these with severity:
- Past deadline by >30 days: critical
- Past deadline by 1-30 days: warning



## Output Format

### Sources Checked

Append a sources table to every output showing which external APIs were queried and their status. See [CONNECTORS.md](../CONNECTORS.md) for the standard format. Only include rows for sources this command actually uses.



- **No product code**: Ask the user for it
- **API unavailable**: Use flat files for classification. Generate template with less auto-populated data.
- **No project data**: Generate a clean template. Note which sections would benefit from running `/fda:research`, `/fda:review`, or `/fda:guidance` first.
- **No predicates identified**: Include a section about predicate selection and suggest running `/fda:research` to identify candidates. Consider whether De Novo pathway applies.
- **--track without --project**: "Correspondence tracking requires a project. Use `--project NAME` to specify one."
- **--correspondence with no entries**: "No correspondence entries found. Use `/fda:presub --track --project NAME` to log FDA interactions."
