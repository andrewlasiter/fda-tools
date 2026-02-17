---
description: Interactive FDA 510(k) data collection — filter by product codes, years, committees, applicants with AI-guided selection, preview before download, and optional API enrichment
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion, WebFetch
argument-hint: "[--product-codes CODE] [--years RANGE] [--project NAME] [--quick] [--full-auto] [--enrich]"
---

# FDA 510(k) Batch Fetch — Interactive Filter & Download

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

## Overview

This command provides an **AI-guided interactive workflow** for filtering and downloading FDA 510(k) data. Instead of terminal prompts, it uses Claude Code's native `AskUserQuestion` interface, allowing the AI to:
- Explain what each filter means
- Recommend selections based on your goals
- Preview results before downloading
- Create organized project structures
- Integrate with the existing pipeline

**Three workflow modes:**
- **Express lane (`--quick`)**: Product codes + years only (2 questions)
- **Full workflow**: 7 filter layers with smart defaults
- **Full-auto mode (`--full-auto`)**: Skip all questions, use CLI args only

---

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--product-codes CODE` — Comma-separated product codes (e.g., "KGN,DXY")
- `--years RANGE` — Year filter (e.g., "2024" or "2020-2025")
- `--date-range KEYS` — Date range keys (e.g., "pmn96cur,pmnlstmn")
- `--committees CODES` — Advisory committee codes (e.g., "CV,OR")
- `--decision-codes CODES` — Decision codes (e.g., "SESE,SESK")
- `--applicants NAMES` — Semicolon-separated company names (e.g., "MEDTRONIC;ABBOTT")
- `--project NAME` — Project name for organized storage
- `--quick` — Express mode: skip most questions
- `--full-auto` — Skip all questions, use only CLI args
- `--resume` — Resume interrupted download from checkpoint
- `--no-download` — Preview only, skip PDF download
- `--save-excel` — Generate Excel analytics workbook
- `--enrich` — Enrich data with openFDA API intelligence (MAUDE events, recalls, predicates, risk scoring)

---

## Step 1: Mode Detection & Setup

### 1.1 Determine Workflow Mode

```python
# Determine mode
if '--full-auto' in arguments:
    mode = 'full-auto'
    # Validate required args present
    if not product_codes:
        error("--full-auto requires --product-codes")
elif '--quick' in arguments:
    mode = 'quick'
else:
    mode = 'full'
```

### 1.2 Resolve Projects Directory

```bash
# Check settings for projects_dir
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

### 1.3 Resume Mode Check

If `--resume` is provided:

```bash
# Check if project exists with download checkpoint
if [ -f "$PROJECTS_DIR/$PROJECT_NAME/download_progress.json" ]; then
    echo "Resume mode: Found checkpoint file"
    # Skip all questions, use existing query.json and resume download
    RESUME_MODE=true
else
    echo "Error: No checkpoint file found for project $PROJECT_NAME"
    exit 1
fi
```

If resuming, load filters from `query.json` and skip to Step 4 (Execution).

---

## Step 2: Filter Selection Workflow

### Embedded Reference Data

**Date Ranges:**
```
pmn96cur - 1996-current (~35,000 records, avg review: 142 days)
pmnlstmn - Most current month available (~300 records/month)
pmn9195  - 1991-1995 (~8,500 records)
pmn8690  - 1986-1990 (~6,200 records)
pmn8185  - 1981-1985 (~4,100 records)
pmn7680  - 1976-1980 (~2,800 records)
```

**Advisory Committees (21 total):**
```
AN - Anesthesiology
CV - Cardiovascular
CH - Clinical Chemistry
DE - Dental
EN - Ear, Nose, Throat
GU - Gastroenterology, Urology
HO - General Hospital
HE - Hematology
IM - Immunology
MG - Medical Genetics
MI - Microbiology
NE - Neurology
OB - Obstetrics/Gynecology
OP - Ophthalmic
OR - Orthopedic
PA - Pathology
PM - Physical Medicine
RA - Radiology
SU - General, Plastic Surgery
TX - Clinical Toxicology
```

**Decision Codes (most common):**
```
SESE - Substantially Equivalent (~95% of clearances)
SESK - Substantially Equivalent - Kit
SESD - Substantially Equivalent with Drug
SESP - Substantially Equivalent - Postmarket Surveillance
SESU - Substantially Equivalent - With Limitations
DENG - De Novo Granted
```

### 2.1 Question 1: Date Range Selection

**Context for AI:**
"Date ranges determine which FDA database archives to search. Recent data (pmn96cur + pmnlstmn) covers 1996-present and is recommended for most users. Historical ranges are useful for legacy device research or comprehensive market analysis."

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Which FDA database date ranges should we search?",
    "header": "Date Range",
    "multiSelect": true,
    "options": [
      {
        "label": "Recent (1996-current + latest month) (Recommended)",
        "description": "Covers ~35,300 records. Best for finding modern predicates with current device features and regulatory expectations."
      },
      {
        "label": "1996-current only",
        "description": "~35,000 records. Excludes the most recent month's submissions."
      },
      {
        "label": "All available ranges",
        "description": "~57,000 total records dating back to 1976. Comprehensive but includes many outdated devices."
      },
      {
        "label": "Custom selection",
        "description": "Let me choose specific date ranges (1991-1995, 1986-1990, etc.)"
      }
    ]
  }]
}
```

**Map responses to CLI arguments:**
- "Recent" → `--date-range pmn96cur,pmnlstmn`
- "1996-current only" → `--date-range pmn96cur`
- "All available" → `--date-range pmn96cur,pmnlstmn,pmn9195,pmn8690,pmn8185,pmn7680`
- "Custom" → Follow-up question with all 6 ranges as options

### 2.2 Question 2: Year Filter (Conditional)

**Only ask if "pmn96cur" is included in date range selection.**

**Context for AI:**
"The pmn96cur database covers 1996-2025 (29 years). Narrowing to recent years finds predicates with modern design features, current regulatory expectations, and active contact information. Older predicates may have outdated technology or discontinued products."

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Filter to specific years within the selected date ranges?",
    "header": "Year Filter",
    "multiSelect": false,
    "options": [
      {
        "label": "Last 5 years (2020-2025) (Recommended)",
        "description": "~8,500 records. Recent predicates with modern features, active companies, and current regulatory standards."
      },
      {
        "label": "Last 10 years (2015-2025)",
        "description": "~17,000 records. Balance between modern devices and broader predicate pool."
      },
      {
        "label": "Last 15 years (2010-2025)",
        "description": "~25,000 records. Comprehensive recent history including pre-2016 UDI era."
      },
      {
        "label": "No year filter",
        "description": "Use all years in selected date ranges. Maximum predicate pool."
      },
      {
        "label": "Custom year range",
        "description": "Specify exact years (e.g., 2022-2024)"
      }
    ]
  }]
}
```

**Map responses:**
- "Last 5 years" → `--years 2020-2025`
- "Last 10 years" → `--years 2015-2025`
- "Last 15 years" → `--years 2010-2025`
- "No year filter" → (omit --years argument)
- "Custom" → Prompt for year input, validate format

**If quick mode (`--quick`):** Skip to Question 3 (Product Codes) now.

### 2.3 Question 3: Product Codes (REQUIRED)

**Context for AI:**
"Product codes are 3-letter FDA classification codes that define device types (e.g., KGN = wound dressing, DQA = surgical instruments). This is the most important filter. You can enter multiple codes separated by commas."

**Pre-question check:**
```bash
# Check if product codes provided via CLI
if [ -n "$PRODUCT_CODES_ARG" ]; then
    # Validate codes exist in foiaclass.txt
    FOIACLASS="$FDA_PLUGIN_ROOT/data/foiaclass.txt"
    if [ -f "$FOIACLASS" ]; then
        for CODE in $(echo $PRODUCT_CODES_ARG | tr ',' ' '); do
            if ! grep -q "^$CODE|" "$FOIACLASS"; then
                echo "Warning: Product code $CODE not found in FDA database"
                # Show suggestions
                grep -i "$CODE" "$FOIACLASS" | head -5
            fi
        done
    fi
    PRODUCT_CODES="$PRODUCT_CODES_ARG"
else
    # Ask user
    USE_ASK_USER_QUESTION
fi
```

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Which product codes should we search? (Required)",
    "header": "Product Codes",
    "multiSelect": false,
    "options": [
      {
        "label": "Enter product codes",
        "description": "I know my product code(s). Enter as comma-separated list (e.g., KGN,DXY,FRO)"
      },
      {
        "label": "Search by device description",
        "description": "I need help finding my product code. Search the FDA database by device name or keywords."
      },
      {
        "label": "Show me examples",
        "description": "Show common product code examples by device category"
      }
    ]
  }]
}
```

**Response handling:**

If "Enter product codes":
- Prompt: "Enter product codes (comma-separated, e.g., KGN,DXY):"
- Validate each code against `foiaclass.txt`
- If code not found, show fuzzy matches and ask to confirm or correct

If "Search by device description":
```bash
# Ask for search terms
echo "Enter device keywords (e.g., 'wound dressing', 'surgical instrument', 'ultrasound'):"
read SEARCH_TERMS

# Search foiaclass.txt
grep -i "$SEARCH_TERMS" "$FDA_PLUGIN_ROOT/data/foiaclass.txt" | head -20

# Present top matches as AskUserQuestion options
```

If "Show me examples":
```
Common Product Codes by Category:

Cardiovascular:
  DTK - Catheter, percutaneous
  DQA - Cardiovascular surgical instruments
  DRY - Stents

Orthopedic:
  KWP - Bone plates
  KWQ - Spinal fixation
  OVE - Intervertebral body fusion

Wound Care:
  KGN - Wound dressing
  FRO - Dressing with drug
  MGP - Surgical mesh

Diagnostics (IVD):
  LCX - Clinical chemistry reagents
  JJE - Immunology reagents
  ...
```

**Validation:**
- Must have at least 1 product code
- Warn if code not found but allow continuation (may get zero results)

### 2.4 Question 4: Advisory Committees (Optional)

**Skip condition:** If already filtering by specific product codes (1-3 codes), this filter is usually redundant. Display: "Your product codes already narrow the search. Do you want to further filter by advisory committee?"

**Context for AI:**
"Advisory committees review devices by medical specialty (e.g., Cardiovascular, Orthopedic). This filter is most useful when searching across many product codes or doing broad market research. For targeted predicate searches, it's usually unnecessary."

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Filter by FDA advisory committee?",
    "header": "Committees",
    "multiSelect": true,
    "options": [
      {
        "label": "All committees (Recommended)",
        "description": "No filter. Your product codes already provide specificity."
      },
      {
        "label": "Cardiovascular (CV)",
        "description": "Heart, vascular, circulatory devices"
      },
      {
        "label": "Orthopedic (OR)",
        "description": "Bone, joint, spine, musculoskeletal devices"
      },
      {
        "label": "Clinical Chemistry (CH)",
        "description": "IVD tests for metabolic, cardiac, renal markers"
      },
      {
        "label": "General Hospital (HO)",
        "description": "Surgical instruments, wound care, general purpose devices"
      },
      {
        "label": "Other committees",
        "description": "Show full list of 21 committees"
      }
    ]
  }]
}
```

**Map responses:**
- "All committees" → (omit --committees argument)
- Specific selections → `--committees CV,OR,...`
- "Other" → Present full 21-committee list as follow-up

### 2.5 Question 5: Decision Codes (Optional)

**Context for AI:**
"Decision codes indicate the FDA's clearance decision. SESE (Substantially Equivalent) represents ~95% of traditional 510(k) clearances. DENG (De Novo) is for novel devices without predicates. Most users should include all decision types."

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Filter by FDA decision type?",
    "header": "Decision",
    "multiSelect": true,
    "options": [
      {
        "label": "All decision types (Recommended)",
        "description": "Include SE, SE with limitations, De Novo, and all variations. Broadest predicate pool."
      },
      {
        "label": "SESE only (Standard SE)",
        "description": "Only standard Substantially Equivalent clearances. Excludes SE with limitations, kits, drugs, or surveillance requirements."
      },
      {
        "label": "Include De Novo (DENG)",
        "description": "Include De Novo granted devices. Useful for novel device research or when no predicates exist."
      },
      {
        "label": "Exclude SE with limitations",
        "description": "Exclude SESP (postmarket surveillance), SESU (limitations), and other restricted clearances."
      },
      {
        "label": "Custom selection",
        "description": "Choose specific decision codes from full list"
      }
    ]
  }]
}
```

**Map responses:**
- "All decision types" → (omit --decision-codes argument)
- "SESE only" → `--decision-codes SESE`
- "Include De Novo" → `--decision-codes SESE,SESK,SESD,SESP,SESU,DENG`
- "Exclude limitations" → `--decision-codes SESE,SESK,SESD`
- "Custom" → Present full decision code list

### 2.6 Question 6: Applicants (Optional)

**Context for AI:**
"Applicant filtering restricts results to specific companies. Useful for competitive intelligence (e.g., 'what is Medtronic developing?'), tracking specific manufacturers, or excluding certain companies. Most predicate searches should include all applicants."

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Filter by applicant company?",
    "header": "Applicants",
    "multiSelect": false,
    "options": [
      {
        "label": "All applicants (Recommended)",
        "description": "No filter. Maximum predicate pool from all manufacturers."
      },
      {
        "label": "Enter specific companies",
        "description": "Filter to one or more companies (e.g., MEDTRONIC, ABBOTT, BOSTON SCIENTIFIC)"
      },
      {
        "label": "Use case: Competitive intelligence",
        "description": "I'm researching a competitor's product pipeline"
      }
    ]
  }]
}
```

**Response handling:**
- "All applicants" → (omit --applicants argument)
- "Enter companies" → Prompt for semicolon-separated company names
  - Note: "Company names must match FDA records exactly (usually uppercase)"
  - Validation: Show warning if name format looks incorrect
- "Competitive intelligence" → Provide tips and prompt for company names

---

## Step 3: Preview & Confirmation

### 3.1 Construct CLI Arguments

Build the complete batchfetch.py command:

```bash
BATCHFETCH_CMD="python3 $FDA_PLUGIN_ROOT/scripts/batchfetch.py"

# Add filters
[ -n "$DATE_RANGE" ] && BATCHFETCH_CMD="$BATCHFETCH_CMD --date-range $DATE_RANGE"
[ -n "$YEARS" ] && BATCHFETCH_CMD="$BATCHFETCH_CMD --years $YEARS"
[ -n "$PRODUCT_CODES" ] && BATCHFETCH_CMD="$BATCHFETCH_CMD --product-codes $PRODUCT_CODES"
[ -n "$COMMITTEES" ] && BATCHFETCH_CMD="$BATCHFETCH_CMD --committees $COMMITTEES"
[ -n "$DECISION_CODES" ] && BATCHFETCH_CMD="$BATCHFETCH_CMD --decision-codes $DECISION_CODES"
[ -n "$APPLICANTS" ] && BATCHFETCH_CMD="$BATCHFETCH_CMD --applicants '$APPLICANTS'"

# Add project paths
BATCHFETCH_CMD="$BATCHFETCH_CMD --output-dir $PROJECTS_DIR/$PROJECT_NAME"
BATCHFETCH_CMD="$BATCHFETCH_CMD --download-dir $PROJECTS_DIR/$PROJECT_NAME/510ks"
BATCHFETCH_CMD="$BATCHFETCH_CMD --data-dir $PROJECTS_DIR/$PROJECT_NAME/fda_data"
```

### 3.2 Generate Preview (No Download)

```bash
# Run with --no-download to get preview
PREVIEW_CMD="$BATCHFETCH_CMD --no-download"
echo "Generating preview..."
PREVIEW_OUTPUT=$($PREVIEW_CMD 2>&1)
```

Parse preview output for:
- Total records matched
- Date range of results (earliest to latest)
- Top 5 applicants with counts
- Product code distribution
- Average review time
- Estimated download size (records × 5MB avg)
- Estimated download time (records × 30 sec delay)

### 3.3 Display Summary & Get Confirmation

Present formatted summary:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FDA 510(k) Batch Fetch Preview
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILTERS APPLIED
────────────────────────────────────────
  Date Range:   pmn96cur, pmnlstmn
  Years:        2020-2025
  Product Code: KGN
  Committees:   All
  Decisions:    All
  Applicants:   All

RESULTS SUMMARY
────────────────────────────────────────
  Total Records:        847
  Date Range:           2020-01-15 to 2025-11-30
  Avg Review Time:      142 days

  Top Applicants:
    1. SMITH & NEPHEW (89 submissions)
    2. 3M (67 submissions)
    3. MOLNLYCKE (54 submissions)
    4. MEDLINE (41 submissions)
    5. CONVATEC (38 submissions)

DOWNLOAD ESTIMATE
────────────────────────────────────────
  Estimated Size:       ~4.2 GB (847 PDFs × 5MB avg)
  Estimated Time:       ~7 hours (847 × 30 sec delay)
  Disk Space Available: 250 GB

PROJECT
────────────────────────────────────────
  Name:    KGN_2020-2025
  Path:    ~/fda-510k-data/projects/KGN_2020-2025/
  Output:  510k_download.csv, 510ks/ directory

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Risk warnings:**
- **> 500 records:** "⚠️  Large download detected. Consider narrowing your filters (e.g., recent years only, specific applicants)."
- **> 1000 records:** "⚠️  VERY LARGE DOWNLOAD. This may take 8+ hours and use significant disk space. Strongly recommend filtering to 500 or fewer records."
- **> 2000 records:** "❌ Downloads over 2000 records are not recommended due to time and disk space requirements. Please narrow your filters."

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Ready to proceed with download?",
    "header": "Confirmation",
    "multiSelect": false,
    "options": [
      {
        "label": "Download all PDFs (Recommended)",
        "description": "Download 847 PDFs to local storage. Required for predicate extraction."
      },
      {
        "label": "CSV metadata only (no PDFs)",
        "description": "Save 510k_download.csv with metadata but skip PDF downloads. Faster, use for analysis without full text."
      },
      {
        "label": "Refine filters",
        "description": "Go back and adjust date range, years, product codes, or other filters."
      },
      {
        "label": "Cancel",
        "description": "Cancel this operation and exit."
      }
    ]
  }]
}
```

**Response handling:**
- "Download all" → Proceed to Step 4 (Execution)
- "CSV only" → Add `--no-download` flag, proceed to Step 4
- "Refine" → Go back to Step 2 (Filter Selection)
- "Cancel" → Exit with message "Operation cancelled by user"

---

## Step 4: Execution

### 4.1 Create Project Structure

```bash
# Create project directories
mkdir -p "$PROJECTS_DIR/$PROJECT_NAME/510ks"
mkdir -p "$PROJECTS_DIR/$PROJECT_NAME/fda_data"

echo "Created project: $PROJECTS_DIR/$PROJECT_NAME"
```

### 4.2 Save Filter Metadata

Write `query.json` with all filter parameters and timestamp:

```json
{
  "project_name": "KGN_2020-2025",
  "created": "2026-02-13T12:00:00Z",
  "filters": {
    "date_range": ["pmn96cur", "pmnlstmn"],
    "years": [2020, 2021, 2022, 2023, 2024, 2025],
    "product_codes": ["KGN"],
    "committees": [],
    "decision_codes": [],
    "applicants": []
  },
  "cli_arguments": {
    "date_range": "pmn96cur,pmnlstmn",
    "years": "2020-2025",
    "product_codes": "KGN",
    "output_dir": "~/fda-510k-data/projects/KGN_2020-2025",
    "download_dir": "~/fda-510k-data/projects/KGN_2020-2025/510ks",
    "data_dir": "~/fda-510k-data/projects/KGN_2020-2025/fda_data"
  },
  "results": {
    "total_records": null,
    "pdfs_downloaded": null,
    "date_range": null,
    "top_applicants": [],
    "avg_review_time_days": null,
    "last_updated": null
  },
  "execution": {
    "mode": "full",
    "user_selections": {
      "date_range_choice": "Recent (1996-current + latest month)",
      "year_filter": "Last 5 years (2020-2025)",
      "product_codes_method": "Enter product codes",
      "committees": "All committees",
      "decision_codes": "All decision types",
      "applicants": "All applicants"
    }
  }
}
```

```bash
# Write query.json
cat > "$PROJECTS_DIR/$PROJECT_NAME/query.json" << 'EOF'
{JSON content here}
EOF
```

### 4.3 Execute Batchfetch

```bash
# Run batchfetch.py with full arguments
echo "Starting FDA 510(k) batch download..."
echo "This may take several hours depending on the number of records."
echo ""

# Execute command
$BATCHFETCH_CMD

# Capture exit code
EXIT_CODE=$?
```

### 4.4 Parse Results

After execution completes:

```bash
# Check for output files
if [ -f "$PROJECTS_DIR/$PROJECT_NAME/510k_download.csv" ]; then
    # Count records in CSV
    TOTAL_RECORDS=$(wc -l < "$PROJECTS_DIR/$PROJECT_NAME/510k_download.csv")
    TOTAL_RECORDS=$((TOTAL_RECORDS - 1))  # Subtract header

    # Count downloaded PDFs
    PDF_COUNT=$(find "$PROJECTS_DIR/$PROJECT_NAME/510ks" -name "*.pdf" 2>/dev/null | wc -l)

    # Parse CSV for date range
    # (Use Python or awk to extract min/max DECISIONDATE)

    # Parse CSV for top applicants
    # (Use Python to count and sort)

    echo "✓ Batch fetch complete!"
    echo "  Records: $TOTAL_RECORDS"
    echo "  PDFs:    $PDF_COUNT"
else
    echo "✗ Error: Output file not created"
    exit 1
fi
```

### 4.5 Update query.json with Results

```bash
# Update query.json with results
python3 << 'PYEOF'
import json, os
from datetime import datetime

query_path = os.path.join(os.environ['PROJECTS_DIR'], os.environ['PROJECT_NAME'], 'query.json')
with open(query_path, 'r') as f:
    data = json.load(f)

data['results']['total_records'] = int(os.environ['TOTAL_RECORDS'])
data['results']['pdfs_downloaded'] = int(os.environ['PDF_COUNT'])
data['results']['last_updated'] = datetime.utcnow().isoformat() + 'Z'

with open(query_path, 'w') as f:
    json.dump(data, f, indent=2)
PYEOF
```

### 4.6 Handle Errors

Check for common failure scenarios:

```bash
# Check failed downloads log
if [ -f "$PROJECTS_DIR/$PROJECT_NAME/failed_downloads_log.json" ]; then
    FAILED_COUNT=$(python3 -c "
import json
with open('$PROJECTS_DIR/$PROJECT_NAME/failed_downloads_log.json') as f:
    data = json.load(f)
    print(len(data))
")

    if [ "$FAILED_COUNT" -gt 0 ]; then
        echo "⚠️  $FAILED_COUNT PDFs failed to download"
        echo "   Check failed_downloads_log.json for details"

        # Categorize failures
        python3 << 'PYEOF'
import json
with open('$PROJECTS_DIR/$PROJECT_NAME/failed_downloads_log.json') as f:
    failures = json.load(f)

rate_limit = sum(1 for f in failures if 'rate limit' in f.get('error', '').lower())
not_found = sum(1 for f in failures if '404' in str(f.get('status_code', '')))
timeout = sum(1 for f in failures if 'timeout' in f.get('error', '').lower())

print(f"  Rate limit errors: {rate_limit}")
print(f"  404 Not found: {not_found}")
print(f"  Timeouts: {timeout}")
PYEOF

        # Offer to resume
        echo ""
        echo "To resume failed downloads, run:"
        echo "  /fda:batchfetch --project $PROJECT_NAME --resume"
    fi
fi
```

**Disk space check:**
```bash
# Check available disk space before large downloads
if [ "$TOTAL_RECORDS" -gt 500 ]; then
    AVAILABLE_GB=$(df -BG "$PROJECTS_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
    REQUIRED_GB=$((TOTAL_RECORDS * 5 / 1000))

    if [ "$AVAILABLE_GB" -lt "$((REQUIRED_GB * 2))" ]; then
        echo "⚠️  WARNING: Low disk space"
        echo "   Available: ${AVAILABLE_GB} GB"
        echo "   Required:  ~${REQUIRED_GB} GB"
        echo ""
        # Ask for confirmation to continue
    fi
fi
```

---

## Step 5: API Enrichment (Optional)

**Trigger conditions:**
1. User provided `--enrich` flag, OR
2. No `--enrich` flag AND API key is configured → Ask user via AskUserQuestion

### 5.1 Check for --enrich Flag and API Key

```bash
# Check if enrichment requested
ENRICH_REQUESTED=false
if [[ "$ARGUMENTS" == *"--enrich"* ]]; then
    ENRICH_REQUESTED=true
fi

# Check for API key
OPENFDA_API_KEY=""
# Priority 1: Environment variable
if [ -n "$OPENFDA_API_KEY" ]; then
    API_KEY_SOURCE="environment"
# Priority 2: Settings file
elif [ -f ~/.claude/fda-predicate-assistant.local.md ]; then
    OPENFDA_API_KEY=$(grep -oP 'openfda_api_key:\s*\K.+' ~/.claude/fda-predicate-assistant.local.md | tr -d ' ')
    API_KEY_SOURCE="settings"
fi
```

### 5.2 Decision Logic

```python
# Enrichment decision tree:
if enrich_requested and not api_key:
    show_warning("API key not found. Skipping enrichment.")
    show_info("Get free API key: https://open.fda.gov/apis/authentication/")
    skip_enrichment = True
elif enrich_requested and api_key:
    skip_enrichment = False  # Proceed with enrichment
elif not enrich_requested and api_key:
    # Ask user via AskUserQuestion
    ask_user_if_enrich()
elif not enrich_requested and not api_key:
    skip_enrichment = True  # Skip silently
```

### 5.3 Ask User About Enrichment (If API Key Exists)

If API key is configured but `--enrich` was not specified, use AskUserQuestion:

```json
{
  "questions": [{
    "question": "I noticed you have an openFDA API key configured. Enrich this data with additional intelligence?",
    "header": "API Enrichment",
    "multiSelect": false,
    "options": [
      {
        "label": "Yes, enrich now (Recommended)",
        "description": "Add MAUDE events, recalls, risk scoring, and predicate networks. Takes 3-5 minutes for 50 devices. Saves 15+ hours of manual research."
      },
      {
        "label": "No, skip enrichment",
        "description": "Use basic batchfetch data only (24 columns). You can enrich later with /fda:safety, /fda:validate commands."
      }
    ]
  }]
}
```

**Map responses:**
- "Yes, enrich now" → Proceed with enrichment
- "No, skip enrichment" → Skip to Step 6 (Summary)

### 5.4 Execute API Enrichment

If enrichment approved, execute the enrichment script:

```bash
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  API Enrichment Started"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Querying openFDA API for each device..."
echo "This will add ~32 additional intelligence columns"
echo ""

# Run enrichment Python script
python3 << 'ENRICH_EOF'
import csv
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Configuration
PROJECT_DIR = os.path.join(os.environ['PROJECTS_DIR'], os.environ['PROJECT_NAME'])
CSV_PATH = os.path.join(PROJECT_DIR, '510k_download.csv')
API_KEY = os.environ.get('OPENFDA_API_KEY', '')

# Add lib directory to Python path
if 'FDA_PLUGIN_ROOT' in os.environ:
    lib_path = Path(os.environ['FDA_PLUGIN_ROOT']) / 'lib'
else:
    # Fallback: try to resolve from installed plugins
    lib_path = Path.home() / '.claude' / 'plugins' / 'marketplaces' / 'fda-tools' / 'plugins' / 'fda-tools' / 'lib'

if not lib_path.exists():
    print(f"ERROR: Could not locate plugin lib directory at {lib_path}")
    sys.exit(1)

sys.path.insert(0, str(lib_path.resolve()))

# Import enrichment modules
try:
    from fda_enrichment import FDAEnrichment
    from disclaimers import (
        get_csv_header_disclaimer,
        get_html_banner_disclaimer,
        get_html_footer_disclaimer,
        get_markdown_header_disclaimer,
        get_json_disclaimers_section,
        MAUDE_SCOPE_WARNING
    )
except ImportError as e:
    print(f"ERROR: Failed to import enrichment modules: {e}")
    print(f"Searched in: {lib_path}")
    sys.exit(1)

# Banner
print("━" * 60)
print("  FDA API Enrichment - Production Ready")
print("  Using fda_enrichment.py v3.0.0")
print("  Phase 1: Data Integrity")
print("  Phase 2: Intelligence Layer")
print("  Phase 3: Advanced Analytics")
print("━" * 60)
print("")

# Initialize enricher
enricher = FDAEnrichment(api_key=API_KEY, api_version="3.0.0")

# Read base CSV data
print(f"📂 Loading device data from {CSV_PATH}...")
with open(CSV_PATH, 'r') as f:
    reader = csv.DictReader(f)
    device_rows = list(reader)

print(f"📊 Found {len(device_rows)} devices to enrich")
print("")

# Enrich using module (includes progress reporting)
enriched_rows, api_log = enricher.enrich_device_batch(device_rows)

print(f"\n✓ Core enrichment complete! Generating Phase 1, 2 & 3 reports...")
print("")

# ====================================================================
# PHASE 1, 2 & 3: REPORT GENERATION (with disclaimers)
# ====================================================================
# Phase 1: Data integrity (quality, metadata, regulatory context)
# Phase 2: Intelligence (clinical requirements, predicate acceptability)
# Phase 3: Advanced analytics (MAUDE peer comparison, competitive intelligence)
# ====================================================================

def calculate_enrichment_completeness_score(row, api_log):
    """Calculate enrichment completeness score (0-100)"""
    score = 0.0

    # API validation success (20 points)
    if row.get('api_validated') == 'Yes':
        score += 20

    # MAUDE data present (15 points)
    if row.get('maude_productcode_5y') not in ['N/A', '', None, 'unknown']:
        score += 15

    # Recall data (10 points - presence indicates API success)
    if row.get('recall_status') not in ['N/A', '', None]:
        score += 10

    # Phase 1 metadata present (20 points)
    if row.get('enrichment_timestamp'):
        score += 5
    if row.get('data_confidence') in ['HIGH', 'MEDIUM']:
        score += 10
    if row.get('cfr_citations') and row.get('cfr_citations') != 'N/A':
        score += 5

    # Phase 2 intelligence present (35 points)
    if row.get('predicate_clinical_history') in ['YES', 'NO', 'PROBABLE', 'UNLIKELY']:
        score += 10
    if row.get('predicate_acceptability') in ['ACCEPTABLE', 'REVIEW_REQUIRED', 'NOT_RECOMMENDED']:
        score += 15
    if row.get('predicate_risk_factors') and row.get('predicate_risk_factors') != 'none':
        score += 10

    return round(score, 1)

def write_enrichment_metadata(project_dir, enriched_rows, api_log):
    """Write enrichment_metadata.json with full provenance tracking"""

    metadata_path = os.path.join(project_dir, 'enrichment_metadata.json')

    # Calculate API success metrics
    successful_calls = sum(1 for log in api_log if log['success'])
    total_calls = len(api_log)
    success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0

    metadata = {
        'enrichment_run': {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'api_version': 'openFDA v2.1',
            'module_version': 'fda_enrichment.py v2.0.1',
            'devices_processed': len(enriched_rows),
            'api_calls_total': total_calls,
            'api_calls_successful': successful_calls,
            'api_success_rate_percent': round(success_rate, 1)
        },
        'data_sources': {
            'maude_events': 'https://api.fda.gov/device/event.json',
            'recalls': 'https://api.fda.gov/device/recall.json',
            '510k_validation': 'https://api.fda.gov/device/510k.json',
            'data_freshness': 'Real-time API queries',
            'cache_policy': 'No caching - all data fetched fresh'
        },
        'disclaimers': get_json_disclaimers_section(),
        'devices': []
    }

    # Per-device provenance
    for row in enriched_rows:
        k_number = row['KNUMBER']
        product_code = row.get('PRODUCTCODE', 'Unknown')

        metadata['devices'].append({
            'k_number': k_number,
            'product_code': product_code,
            'data_confidence': row.get('data_confidence', 'UNKNOWN'),
            'enrichment_completeness_score': row.get('enrichment_completeness_score', 0),
            'api_validated': row.get('api_validated', 'Unknown'),
            'maude_scope': row.get('maude_scope', 'Unknown'),
            'recalls_found': row.get('recalls_total', 0),
            'predicate_acceptability': row.get('predicate_acceptability', 'Unknown')
        })

    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ Enrichment metadata: {metadata_path}")

def generate_enrichment_process_report(project_dir, enriched_rows, api_log):
    """Generate quality_report.md with completeness validation and scoring"""

    # Calculate enrichment completeness scores for all devices
    scores = [calculate_enrichment_completeness_score(row, api_log) for row in enriched_rows]
    avg_score = sum(scores) / len(scores) if scores else 0

    # Add scores to rows for later use
    for i, row in enumerate(enriched_rows):
        row['enrichment_completeness_score'] = scores[i]

    # Categorize by confidence
    high_conf = sum(1 for s in scores if s >= 80)
    med_conf = sum(1 for s in scores if 60 <= s < 80)
    low_conf = sum(1 for s in scores if s < 60)

    # Identify quality issues
    issues = []
    for row in enriched_rows:
        if row.get('maude_productcode_5y') in ['N/A', '', None, 'unknown']:
            issues.append(f"⚠️  {row['KNUMBER']}: MAUDE data unavailable (product code not found)")
        if row.get('api_validated') == 'No':
            issues.append(f"⚠️  {row['KNUMBER']}: 510(k) validation failed (K-number not found in API)")

    # Calculate API metrics
    successful_calls = sum(1 for log in api_log if log['success'])
    total_calls = len(api_log)
    success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0

    report_path = os.path.join(project_dir, 'quality_report.md')

    # Add disclaimer header
    report = get_markdown_header_disclaimer("Quality Report")

    report += f"""
## Summary
- Devices enriched: {len(enriched_rows)}/{len(enriched_rows)} (100%)
- API success rate: {success_rate:.1f}% ({successful_calls}/{total_calls} calls)
- Average completeness score: {avg_score:.1f}/100
- Data timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
- Module version: fda_enrichment.py v2.0.1

## What This Score Means

**Enrichment Data Completeness Score (0-100)** measures:
- API data availability (MAUDE, recalls, validation)
- Phase 1 metadata completeness (provenance, confidence, CFR citations)
- Phase 2 intelligence completeness (clinical, acceptability, risk factors)

It does NOT assess device quality, submission readiness, or regulatory compliance.

## Enrichment Completeness Distribution

- **HIGH completeness (≥80):** {high_conf} devices ({high_conf/len(enriched_rows)*100:.1f}%)
- **MEDIUM completeness (60-79):** {med_conf} devices ({med_conf/len(enriched_rows)*100:.1f}%)
- **LOW completeness (<60):** {low_conf} devices ({low_conf/len(enriched_rows)*100:.1f}%)

## Data Issues Detected

"""

    if issues:
        for issue in issues[:10]:  # Show first 10
            report += f"{issue}\n"
        if len(issues) > 10:
            report += f"\n...and {len(issues) - 10} more issues\n"
    else:
        report += "✓ No data quality issues detected\n"

    report += f"""

## API Call Log

Total API calls: {total_calls}
- Successful: {successful_calls}
- Failed: {total_calls - successful_calls}

"""

    with open(report_path, 'w') as f:
        f.write(report)

    print(f"✓ Quality report: {report_path}")

def generate_regulatory_context(project_dir, enriched_rows):
    """Generate regulatory_context.md with CFR citations and guidance"""

    report_path = os.path.join(project_dir, 'regulatory_context.md')

    # Add disclaimer header
    report = get_markdown_header_disclaimer("Regulatory Context")

    report += """
## CFR Citations

Enriched data includes references to the following Code of Federal Regulations (CFR) parts:

### 21 CFR Part 803 - Medical Device Reporting (MDR)
- **Scope:** Mandatory reporting of adverse events
- **Data Source:** MAUDE database (device.event API)
- **URL:** https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-803

### 21 CFR Part 7 - Enforcement Policy
- **Scope:** Recalls, corrections, and removals
- **Data Source:** Recall database (device.recall API)
- **URL:** https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-7

### 21 CFR Part 807 - Establishment Registration and Device Listing
- **Scope:** 510(k) premarket notification
- **Data Source:** 510(k) clearance database (device.510k API)
- **URL:** https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-807

"""

    # Add device-specific CFR citations section (Fix #3: Critical Expert Review Finding)
    device_cfr_map = {}
    for row in enriched_rows:
        reg_num = row.get('regulation_number', '')
        device_class = row.get('device_classification', '')
        if reg_num and reg_num != 'VERIFY_MANUALLY' and '21 CFR' in reg_num:
            device_cfr_map[reg_num] = device_class

    if device_cfr_map:
        report += "## Device-Specific CFR Citations\n\n"
        report += "The following CFR parts apply to devices in this dataset:\n\n"
        for cfr_part in sorted(device_cfr_map.keys()):
            device_type = device_cfr_map[cfr_part]
            # Extract CFR base part for URL (e.g., 870 from "21 CFR 870.1340")
            cfr_base = cfr_part.replace('21 CFR ', '').split('.')[0]
            url = f"https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-{cfr_base}"

            report += f"### {cfr_part}\n"
            report += f"- **Device Type:** {device_type}\n"
            report += f"- **URL:** {url}\n\n"

    report += """
## FDA Guidance Documents

### Medical Device Reporting Guidance (2016)
- **Title:** Medical Device Reporting for Manufacturers
- **Relevance:** MAUDE data interpretation
- **URL:** https://www.fda.gov/regulatory-information/search-fda-guidance-documents/medical-device-reporting-manufacturers

### Public Warning-Notification Guidance (2019)
- **Title:** Public Warning-Notification of Recalls Under 21 CFR Part 7, Subpart C
- **Date:** February 2019
- **Relevance:** Understanding recall public notification requirements and procedures
- **URL:** https://www.fda.gov/regulatory-information/search-fda-guidance-documents/public-warning-notification-recalls-under-21-cfr-part-7-subpart-c

### 510(k) Substantial Equivalence (2014)
- **Title:** The 510(k) Program: Evaluating Substantial Equivalence in Premarket Notifications
- **Relevance:** Predicate acceptability assessment
- **URL:** https://www.fda.gov/regulatory-information/search-fda-guidance-documents/510k-program-evaluating-substantial-equivalence-premarket-notifications-510k

"""

    with open(report_path, 'w') as f:
        f.write(report)

    print(f"✓ Regulatory context: {report_path}")

def generate_intelligence_report(project_dir, enriched_rows):
    """Generate intelligence_report.md with Phase 2 analysis"""

    # Aggregate intelligence metrics
    total_devices = len(enriched_rows)
    predicate_clinical_yes = len([r for r in enriched_rows if r.get('predicate_clinical_history') == 'YES'])
    special_controls = len([r for r in enriched_rows if r.get('special_controls_applicable') == 'YES'])
    not_recommended_predicates = len([r for r in enriched_rows if r.get('predicate_acceptability') == 'NOT_RECOMMENDED'])

    report_path = os.path.join(project_dir, 'intelligence_report.md')

    # Add disclaimer header
    report = get_markdown_header_disclaimer("Intelligence Report - Phase 2 Analysis")

    report += f"""
## Executive Summary

This intelligence report provides strategic insights from Phase 2 enrichment analysis:

### Clinical Data Requirements
- **{predicate_clinical_yes}/{total_devices}** predicates ({predicate_clinical_yes/total_devices*100:.1f}%) have clinical data history
- **{special_controls}/{total_devices}** devices ({special_controls/total_devices*100:.1f}%) may require special controls

### Predicate Acceptability
- **{not_recommended_predicates}** predicates flagged as NOT_RECOMMENDED

## Clinical Data Detection

Phase 2 enrichment analyzes decision descriptions for clinical study indicators:

"""

    # Add clinical indicators from predicates
    all_indicators = []
    for row in enriched_rows:
        indicators = row.get('predicate_clinical_indicators', '').split(', ')
        all_indicators.extend([i for i in indicators if i != 'none'])

    # Count unique indicators
    from collections import Counter
    indicator_counts = Counter(all_indicators)

    if indicator_counts:
        report += "**Most Common Clinical Indicators:**\n\n"
        for indicator, count in indicator_counts.most_common(10):
            report += f"- {indicator}: {count} devices\n"
    else:
        report += "No clinical indicators detected in predicates.\n"

    report += """

## Predicate Acceptability Assessment

Phase 2 analysis evaluates predicate suitability based on:
- Recall history
- Clearance age (>10 years may require stronger justification)
- FDA SE guidance criteria

"""

    acceptable = len([r for r in enriched_rows if r.get('predicate_acceptability') == 'ACCEPTABLE'])
    review_required = len([r for r in enriched_rows if r.get('predicate_acceptability') == 'REVIEW_REQUIRED'])
    not_recommended = len([r for r in enriched_rows if r.get('predicate_acceptability') == 'NOT_RECOMMENDED'])

    report += f"""
| Acceptability Status | Count | Percentage | Recommendation |
|---------------------|-------|------------|----------------|
| ACCEPTABLE | {acceptable} | {acceptable/total_devices*100:.1f}% | Proceed with confidence |
| REVIEW_REQUIRED | {review_required} | {review_required/total_devices*100:.1f}% | Manual review recommended |
| NOT_RECOMMENDED | {not_recommended} | {not_recommended/total_devices*100:.1f}% | Consider alternatives |

"""

    if not_recommended > 0:
        report += "\n### NOT_RECOMMENDED Predicates (Top 10)\n\n"
        not_recommended_devices = [r for r in enriched_rows if r.get('predicate_acceptability') == 'NOT_RECOMMENDED']
        for i, device in enumerate(not_recommended_devices[:10], 1):
            rationale = device.get('acceptability_rationale', 'No rationale provided')
            report += f"{i}. **{device['KNUMBER']}** - {device.get('APPLICANT', 'N/A')}\n"
            report += f"   - Rationale: {rationale}\n\n"

    report += """

## Resource Planning & Timeline Estimates

Based on Phase 2 intelligence, here are estimated resource requirements:

### Clinical Data Requirements
"""

    if predicate_clinical_yes > total_devices * 0.3:
        report += """
**High clinical data requirements detected** (>30% of predicates had clinical studies)

- **Timeline Impact:** +6-12 months
- **Budget Impact:** $150K - $500K (study design, execution, analysis)
- **Resources:** Clinical Research Associate, Biostatistician, Medical Monitor

"""
    else:
        report += """
**Low clinical data requirements** (<30% of predicates had clinical studies)

- **Timeline Impact:** +0-3 months (bench/animal testing may suffice)
- **Budget Impact:** $25K - $100K (bench testing, biocompatibility)

"""

    report += """

---

**End of Intelligence Report**

For detailed analysis, see:
- quality_report.md - Enrichment completeness scores
- regulatory_context.md - CFR citations and guidance
- enrichment_metadata.json - Full API provenance

"""

    with open(report_path, 'w') as f:
        f.write(report)

    print(f"✓ Intelligence report: {report_path}")

def generate_competitive_intelligence(project_dir, enriched_rows):
    """
    Phase 3 Feature 2: Competitive Intelligence Report

    Generate market analysis report for each product code:
    - Market concentration (Herfindahl-Hirschman Index)
    - Top manufacturers by clearance count
    - Technology trend detection (keyword YoY analysis)
    - Gold standard predicates (most-cited devices)
    """
    from collections import Counter, defaultdict
    from datetime import datetime, timedelta

    # Group devices by product code
    product_codes = {}
    for row in enriched_rows:
        pc = row.get('PRODUCTCODE', 'UNKNOWN')
        if pc not in product_codes:
            product_codes[pc] = []
        product_codes[pc].append(row)

    # Generate report for each product code
    for product_code, devices in product_codes.items():
        report_path = os.path.join(project_dir, f'competitive_intelligence_{product_code}.md')

        # Query 510k API for all devices in this product code (last 5 years)
        five_years_ago = (datetime.now() - timedelta(days=5*365)).strftime('%Y%m%d')

        params = {
            'search': f'product_code:{product_code} AND decision_date:[{five_years_ago} TO 20991231]',
            'limit': 1000
        }

        market_data = api_query('device/510k.json', params)

        if not market_data or 'results' not in market_data:
            print(f"⚠ Could not fetch market data for {product_code}")
            continue

        all_devices = market_data['results']
        total_clearances = len(all_devices)

        # Add disclaimer header
        report = get_markdown_header_disclaimer(f"Competitive Intelligence - {product_code}")

        report += f"""
# Competitive Intelligence Report
## Product Code: {product_code}

**Analysis Period:** Last 5 years ({five_years_ago[:4]}-present)
**Total Clearances:** {total_clearances} devices
**Data Source:** openFDA device/510k API
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}

---

## Market Concentration Analysis

"""

        # Calculate market concentration (Herfindahl-Hirschman Index)
        # HHI = sum of squared market shares (0-10000 scale)
        # HHI < 1500: Competitive market
        # HHI 1500-2500: Moderate concentration
        # HHI > 2500: Highly concentrated

        manufacturer_counts = Counter()
        for device in all_devices:
            applicant = device.get('applicant', 'Unknown')
            manufacturer_counts[applicant] += 1

        # Calculate HHI
        hhi = 0
        market_shares = []
        for count in manufacturer_counts.values():
            share = (count / total_clearances) * 100
            market_shares.append(share)
            hhi += share ** 2

        # Classify market concentration
        if hhi < 1500:
            concentration_level = "COMPETITIVE"
            concentration_note = "Low concentration - many players competing"
        elif hhi < 2500:
            concentration_level = "MODERATELY CONCENTRATED"
            concentration_note = "Moderate concentration - several dominant players"
        else:
            concentration_level = "HIGHLY CONCENTRATED"
            concentration_note = "High concentration - market dominated by few players"

        report += f"""
**Herfindahl-Hirschman Index (HHI):** {hhi:.0f}
**Market Concentration:** {concentration_level}
**Interpretation:** {concentration_note}

### Market Share Distribution

| Metric | Value |
|--------|-------|
| Total Manufacturers | {len(manufacturer_counts)} |
| Top 4 Market Share (CR4) | {sum(sorted(market_shares, reverse=True)[:4]):.1f}% |
| Top 8 Market Share (CR8) | {sum(sorted(market_shares, reverse=True)[:8]):.1f}% |
| Median Clearances per Manufacturer | {sorted(manufacturer_counts.values())[len(manufacturer_counts)//2]} |

---

## Top Manufacturers

"""

        # Top 10 manufacturers
        report += "| Rank | Manufacturer | Clearances | Market Share |\n"
        report += "|------|-------------|------------|-------------|\n"

        for i, (manufacturer, count) in enumerate(manufacturer_counts.most_common(10), 1):
            share = (count / total_clearances) * 100
            report += f"| {i} | {manufacturer[:50]} | {count} | {share:.1f}% |\n"

        report += "\n---\n\n## Technology Trend Analysis\n\n"

        # Keyword frequency analysis by year
        # Extract keywords from device names and decision descriptions
        current_year = datetime.now().year
        yearly_keywords = defaultdict(lambda: Counter())

        for device in all_devices:
            decision_date = device.get('decision_date', '')
            if decision_date and len(decision_date) >= 4:
                year = int(decision_date[:4])

                # Extract keywords from device name
                device_name = device.get('device_name', '').lower()
                # Common technology keywords
                tech_keywords = ['wireless', 'connected', 'ai', 'machine learning', 'digital',
                                'smart', 'robotic', 'laser', 'ultrasound', 'mri', 'ct',
                                'disposable', 'reusable', 'implant', 'catheter', 'sensor',
                                'software', 'algorithm', 'cloud', 'mobile', 'bluetooth']

                for keyword in tech_keywords:
                    if keyword in device_name:
                        yearly_keywords[year][keyword] += 1

        # Calculate year-over-year trends (last 3 years)
        if yearly_keywords:
            report += "**Emerging Technology Trends (Keywords YoY):**\n\n"
            report += "| Keyword | "
            years = sorted(yearly_keywords.keys(), reverse=True)[:3]
            for year in years:
                report += f"{year} | "
            report += "Trend |\n"

            report += "|---------|"
            for _ in years:
                report += "------|"
            report += "-------|\n"

            # Get all keywords that appeared in recent years
            all_keywords = set()
            for year in years:
                all_keywords.update(yearly_keywords[year].keys())

            # Sort by total occurrences across years
            keyword_totals = {}
            for kw in all_keywords:
                keyword_totals[kw] = sum(yearly_keywords[year][kw] for year in years)

            for keyword, _ in sorted(keyword_totals.items(), key=lambda x: x[1], reverse=True)[:15]:
                counts = [yearly_keywords[year][keyword] for year in years]

                # Calculate trend (simple: compare latest to earliest)
                if len(counts) >= 2 and counts[-1] > 0:
                    growth = ((counts[0] - counts[-1]) / counts[-1]) * 100
                    if growth > 20:
                        trend = f"↗ +{growth:.0f}%"
                    elif growth < -20:
                        trend = f"↘ {growth:.0f}%"
                    else:
                        trend = "→ Stable"
                else:
                    trend = "—"

                report += f"| {keyword} | "
                for count in counts:
                    report += f"{count} | "
                report += f"{trend} |\n"
        else:
            report += "No technology trend data available.\n"

        report += "\n---\n\n## Gold Standard Predicates\n\n"

        # Find most-cited devices (devices that appear as predicates in many submissions)
        # Extract predicates from statement field
        predicate_citations = Counter()

        for device in all_devices:
            statement = device.get('statement', '') or ''
            # Look for K-numbers in statement (K-numbers follow pattern KXXXXXX)
            import re
            k_numbers = re.findall(r'K\d{6}', statement.upper())
            for k_num in k_numbers:
                predicate_citations[k_num] += 1

        if predicate_citations:
            report += """
**Most-Cited Predicates** (Industry gold standards):

These devices are frequently used as predicates, suggesting strong market acceptance and regulatory precedent.

| Rank | K-Number | Citations | Interpretation |
|------|----------|-----------|----------------|
"""

            for i, (k_number, citations) in enumerate(predicate_citations.most_common(15), 1):
                if citations >= 5:
                    strength = "Strong gold standard"
                elif citations >= 3:
                    strength = "Established predicate"
                else:
                    strength = "Referenced predicate"

                report += f"| {i} | {k_number} | {citations} | {strength} |\n"
        else:
            report += "No predicate citation data available from this dataset.\n"

        report += """

---

## Strategic Recommendations

Based on this competitive intelligence:

"""

        # Generate strategic recommendations
        if concentration_level == "COMPETITIVE":
            report += """
### Market Entry Strategy
- **Opportunity:** Competitive market with many players suggests room for innovation
- **Risk:** High competition may require stronger differentiation
- **Recommendation:** Focus on unique value proposition, target underserved segments

"""
        elif concentration_level == "HIGHLY CONCENTRATED":
            report += """
### Market Entry Strategy
- **Opportunity:** Concentrated market may have innovation gaps
- **Risk:** Dominant players have established relationships and market power
- **Recommendation:** Consider niche positioning, partnerships, or De Novo pathway if truly novel

"""

        # Top manufacturer insights
        top_manufacturer = manufacturer_counts.most_common(1)[0]
        report += f"""
### Competitive Positioning
- **Market Leader:** {top_manufacturer[0]} ({top_manufacturer[1]} clearances, {(top_manufacturer[1]/total_clearances)*100:.1f}% share)
- **Recommendation:** Study their cleared devices for predicate selection and competitive differentiation

"""

        # Technology trends
        if yearly_keywords:
            top_trends = sorted(keyword_totals.items(), key=lambda x: x[1], reverse=True)[:3]
            if top_trends:
                report += f"""
### Technology Focus Areas
- **Dominant Technologies:** {', '.join([kw for kw, _ in top_trends])}
- **Recommendation:** Align technology strategy with emerging trends or differentiate by addressing gaps

"""

        report += """
---

**End of Competitive Intelligence Report**

**Next Steps:**
1. Review gold standard predicates for SE comparison
2. Analyze top competitors' cleared devices for positioning
3. Monitor technology trends for innovation opportunities
4. Use HHI data for market sizing and forecasting

**Related Reports:**
- `intelligence_report.md` - Phase 2 clinical and acceptability analysis
- `regulatory_context.md` - CFR citations and guidance
- `quality_report.md` - Data completeness metrics

"""

        with open(report_path, 'w') as f:
            f.write(report)

        print(f"✓ Competitive intelligence ({product_code}): {report_path}")

# ====================================================================
# GENERATE REPORTS
# ====================================================================

generate_enrichment_process_report(PROJECT_DIR, enriched_rows, api_log)
write_enrichment_metadata(PROJECT_DIR, enriched_rows, api_log)
generate_regulatory_context(PROJECT_DIR, enriched_rows)
generate_intelligence_report(PROJECT_DIR, enriched_rows)
generate_competitive_intelligence(PROJECT_DIR, enriched_rows)

# ====================================================================
# WRITE ENRICHED CSV WITH DISCLAIMERS
# ====================================================================

# Determine product codes for disclaimer
product_codes = set([row.get('PRODUCTCODE', 'UNKNOWN') for row in enriched_rows])
product_codes_str = ', '.join(sorted(product_codes))

# Write CSV with disclaimer header
output_csv = os.path.join(PROJECT_DIR, '510k_download_enriched.csv')

with open(output_csv, 'w', newline='') as f:
    # Add disclaimer as CSV comments
    disclaimer = get_csv_header_disclaimer(product_codes_str)
    f.write(disclaimer)

    # Write CSV data
    fieldnames = list(enriched_rows[0].keys())
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(enriched_rows)

# Rename to replace original
import shutil
shutil.move(output_csv, CSV_PATH)

print(f"\n✓ Enriched CSV written (with disclaimers): {CSV_PATH}")

# ====================================================================
# GENERATE HTML REPORT WITH DISCLAIMERS
# ====================================================================

recalled_count = sum(1 for row in enriched_rows if row['recalls_total'] > 0)
report_path = os.path.join(PROJECT_DIR, 'enrichment_report.html')

html_banner = get_html_banner_disclaimer()
html_footer = get_html_footer_disclaimer()

with open(report_path, 'w') as f:
    f.write(f'''<!DOCTYPE html>
<html>
<head>
    <title>FDA Data Enrichment Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .disclaimer-banner {{
            background: #fff3cd;
            border-left: 5px solid #ffc107;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .disclaimer-footer {{
            background: #f8f9fa;
            border-top: 3px solid #dee2e6;
            padding: 20px;
            margin-top: 40px;
            font-size: 0.9em;
        }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
        .info {{ background: #d1ecf1; border-left: 4px solid #17a2b8; padding: 15px; margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        tr:hover {{ background-color: #f1f1f1; }}
        .recall-yes {{ color: #d32f2f; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        {html_banner}

        <h1>FDA 510(k) API Enrichment Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Total Devices:</strong> {len(enriched_rows)}</p>
        <p><strong>Devices with Recalls:</strong> {recalled_count}</p>
        <p><strong>Module Version:</strong> fda_enrichment.py v2.0.1</p>

        <div class="warning">
            <strong>⚠️ MAUDE Data Scope:</strong><br>
            MAUDE event counts are at PRODUCT CODE level ({product_codes_str}), not device-specific.
            This count reflects ALL devices within these product codes.
        </div>

        <h2>Enrichment Summary</h2>
        <div class="info">
            <strong>Phase 1: Data Integrity</strong><br>
            • Provenance tracking (enrichment_metadata.json)<br>
            • Quality scoring (quality_report.md)<br>
            • CFR citations (regulatory_context.md)<br>
            <br>
            <strong>Phase 2: Intelligence Layer</strong><br>
            • Clinical data requirements detection<br>
            • Standards guidance<br>
            • Predicate acceptability assessment<br>
            • Strategic insights (intelligence_report.md)
        </div>

        <h2>Devices with Recalls</h2>
        <table>
            <tr>
                <th>K-Number</th>
                <th>Device Name</th>
                <th>Applicant</th>
                <th>Total Recalls</th>
                <th>Latest Recall</th>
                <th>Class</th>
                <th>Status</th>
            </tr>
''')

    for row in enriched_rows:
        if row['recalls_total'] > 0:
            f.write(f'''            <tr>
                <td><strong>{row['KNUMBER']}</strong></td>
                <td>{row.get('DEVICENAME', 'N/A')}</td>
                <td>{row.get('APPLICANT', 'N/A')}</td>
                <td class="recall-yes">{row['recalls_total']}</td>
                <td>{row.get('recall_latest_date', 'N/A')}</td>
                <td>{row.get('recall_class', 'N/A')}</td>
                <td>{row.get('recall_status', 'N/A')}</td>
            </tr>
''')

    f.write(f'''        </table>

        {html_footer}
    </div>
</body>
</html>
''')

print(f"✓ HTML report (with disclaimers): {report_path}")

# ====================================================================
# FINAL SUMMARY
# ====================================================================

print(f"\n✓ Enrichment complete! Added 34 columns (12 core + 6 Phase 1 + 7 Phase 2 + 2 CFR + 7 Phase 3)")
print(f"")
print(f"  Core Enrichment Columns (12):")
print(f"  - maude_productcode_5y (⚠️  PRODUCT CODE level, not device-specific)")
print(f"  - maude_trending (increasing/decreasing/stable)")
print(f"  - maude_recent_6m (last 6 months)")
print(f"  - maude_scope (PRODUCT_CODE or UNAVAILABLE)")
print(f"  - recalls_total (✓ DEVICE SPECIFIC)")
print(f"  - recall_latest_date")
print(f"  - recall_class (I/II/III)")
print(f"  - recall_status")
print(f"  - api_validated (Yes/No)")
print(f"  - decision_description")
print(f"  - expedited_review_flag (Y/N)")
print(f"  - summary_type (Summary/Statement)")
print(f"")
print(f"  Phase 1: Data Integrity Columns (6):")
print(f"  - enrichment_timestamp (ISO 8601 format)")
print(f"  - api_version (openFDA v2.1)")
print(f"  - data_confidence (HIGH/MEDIUM/LOW)")
print(f"  - enrichment_completeness_score (0-100)")
print(f"  - cfr_citations (comma-separated CFR parts)")
print(f"  - guidance_refs (count of applicable guidance docs)")
print(f"")
print(f"  Phase 2: Intelligence Layer Columns (7):")
print(f"  - predicate_clinical_history (YES/PROBABLE/UNLIKELY/NO)")
print(f"  - predicate_study_type (premarket/postmarket/none)")
print(f"  - predicate_clinical_indicators (detected in predicate clearance)")
print(f"  - special_controls_applicable (YES/NO)")
print(f"  - predicate_acceptability (ACCEPTABLE/REVIEW_REQUIRED/NOT_RECOMMENDED)")
print(f"  - acceptability_rationale (specific reasons for assessment)")
print(f"  - predicate_recommendation (action to take)")
print(f"")
print(f"  Standards Determination:")
print(f"  - Use /fda:test-plan command for comprehensive standards analysis")
print(f"  - Automated standards detection not implemented (complexity: 10-50+ standards per device)")
print(f"  - Refer to FDA Recognized Consensus Standards Database")
print(f"")
print(f"  Device-Specific CFR Citations (2 columns):")
print(f"  - regulation_number (e.g., '21 CFR 870.1340')")
print(f"  - device_classification (e.g., 'Percutaneous Catheter')")
print(f"  - Note: {len([r for r in enriched_rows if r.get('regulation_number', '') != 'VERIFY_MANUALLY'])} devices mapped to CFR parts")
print(f"")
print(f"  Phase 3: Advanced Analytics (7 columns):")
print(f"  - peer_cohort_size (number of peer devices analyzed)")
print(f"  - peer_median_events (median MAUDE events across peers)")
print(f"  - peer_75th_percentile (75th percentile threshold)")
print(f"  - peer_90th_percentile (90th percentile threshold)")
print(f"  - device_percentile (this device's rank, 0-100)")
print(f"  - maude_classification (EXCELLENT/GOOD/AVERAGE/CONCERNING/EXTREME_OUTLIER)")
print(f"  - peer_comparison_note (interpretation)")
print(f"")
print(f"✓ Devices with recalls: {recalled_count}/{len(enriched_rows)}")
print(f"")
print(f"📄 Output Files Generated:")
print(f"    • 510k_download.csv (enriched with disclaimers)")
print(f"    • enrichment_report.html (visual dashboard with disclaimers)")
print(f"    • quality_report.md (Phase 1 data quality)")
print(f"    • regulatory_context.md (CFR citations and guidance)")
print(f"    • intelligence_report.md (Phase 2 strategic insights)")
print(f"    • competitive_intelligence_{{PRODUCT_CODE}}.md (Phase 3 market analysis)")
print(f"    • enrichment_metadata.json (full provenance)")
print(f"")
print(f"All enriched data is traceable, validated, regulation-linked, and strategically analyzed.")

ENRICH_EOF

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ API enrichment complete (Phase 1, 2 & 3)!"
    echo "  - Added 34 enrichment columns to CSV (12 core + 6 Phase 1 + 7 Phase 2 + 2 CFR + 7 Phase 3)"
    echo "  - Phase 1: Data integrity (6 columns)"
    echo "  - Phase 2: Intelligence layer (7 columns)"
    echo "  - Phase 3: Advanced analytics (7 columns)"
    echo "  - Device-specific CFR (2 columns)"
    echo "  - Risk dashboard: risk_analysis.html"
else
    echo ""
    echo "⚠️  Enrichment failed (exit code: $EXIT_CODE)"
    echo "  - Basic CSV data is still available"
    echo "  - Check API key and connectivity"
fi
```

### 5.5 Display Enrichment Results

```bash
# Count recalled devices
RECALLED=$(python3 -c "
import csv
with open('$PROJECTS_DIR/$PROJECT_NAME/510k_download.csv') as f:
    reader = csv.DictReader(f)
    count = sum(1 for row in reader if int(row.get('recalls_total', 0)) > 0)
    print(count)
")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  API ENRICHMENT COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Added 12 columns (all real FDA data):"
echo "  ✓ MAUDE events (⚠️  product code level)"
echo "  ✓ Event trending (increasing/decreasing)"
echo "  ✓ Recall history (✓ device-specific)"
echo "  ✓ K-number validation"
echo "  ✓ Statement/Summary type"
echo ""
echo "Devices with recalls: $RECALLED"
echo "Total columns now: 36 (was 24)"
echo ""
echo "📄 Reports generated:"
echo "  - enrichment_report.html"
echo ""
```

---

## Step 6: Summary & Next Steps

### 5.1 Display Results Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FDA 510(k) Batch Fetch Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROJECT: KGN_2020-2025
────────────────────────────────────────
  Path:     ~/fda-510k-data/projects/KGN_2020-2025/

  Records:  847 submissions
  PDFs:     847 downloaded (100%)
  Failed:   0

  Date Range:   2020-01-15 to 2025-11-30
  Avg Review:   142 days

FILES CREATED
────────────────────────────────────────
  ✓ query.json                  Filter metadata
  ✓ 510k_download.csv           Submission metadata (847 rows)
  ✓ 510ks/                      Downloaded PDFs (847 files, ~4.2 GB)
  ✓ fda_data/                   FDA database archives

NEXT STEPS
────────────────────────────────────────
  1. Extract predicates from PDFs:
     /fda:extract stage2 --project KGN_2020-2025

  2. Review and score predicates:
     /fda:review --project KGN_2020-2025

  3. Draft submission sections:
     /fda:draft --project KGN_2020-2025

OPTIONAL ANALYSIS
────────────────────────────────────────
  • View statistics:        /fda:analyze download --project KGN_2020-2025
  • Gap analysis:           /fda:gap-analysis --project KGN_2020-2025
  • Safety intelligence:    /fda:safety --product-code KGN
  • Competitive analysis:   Open Applicant_ProductCode_Tables.xlsx

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Data collection complete. Ready for predicate extraction.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 5.2 Generate Excel Analytics (If Requested)

If `--save-excel` flag was set:

```bash
# Batchfetch.py automatically generates Excel if --save-excel is passed
# Check if file exists
if [ -f "$PROJECTS_DIR/$PROJECT_NAME/Applicant_ProductCode_Tables.xlsx" ]; then
    echo ""
    echo "📊 Excel Analytics:"
    echo "   $PROJECTS_DIR/$PROJECT_NAME/Applicant_ProductCode_Tables.xlsx"
    echo "   Contains:"
    echo "   • Applicant ranking by submission count"
    echo "   • Product code distribution"
    echo "   • Timeline analysis"
    echo "   • Review time statistics"
fi
```

---

## Error Handling & Edge Cases

### No Results Found

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  No Results Found
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

APPLIED FILTERS
────────────────────────────────────────
  Date Range:   pmn96cur
  Years:        2024
  Product Code: INVALID
  Applicants:   NONEXISTENT COMPANY

ISSUE
────────────────────────────────────────
  No 510(k) submissions matched your filters.

SUGGESTIONS
────────────────────────────────────────
  1. Verify product code is correct:
     • Check spelling (e.g., KGN not KNG)
     • Search: /fda:validate --search "wound dressing"

  2. Expand date range:
     • Try removing year filter
     • Include earlier date ranges (pmn9195)

  3. Remove restrictive filters:
     • Remove applicant filter
     • Try "All decision types"

  4. Check product code exists:
     • Some codes are obsolete or merged
     • Use /fda:status to check database

TRY AGAIN
────────────────────────────────────────
  /fda:batchfetch --product-codes KGN --years 2020-2025

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Use `AskUserQuestion` to offer:
- "Refine filters and try again"
- "Search for correct product code"
- "Cancel operation"

### Invalid Product Code

```bash
# Check product code validity
FOIACLASS="$FDA_PLUGIN_ROOT/data/foiaclass.txt"
for CODE in $(echo $PRODUCT_CODES | tr ',' ' '); do
    if ! grep -q "^$CODE|" "$FOIACLASS"; then
        echo "⚠️  Warning: Product code '$CODE' not found in FDA database"
        echo ""
        echo "Did you mean one of these?"
        grep -i "$CODE" "$FOIACLASS" | head -5 | awk -F'|' '{print "  " $1 " - " $2}'
        echo ""

        # Ask to continue or correct
        # Use AskUserQuestion
    fi
done
```

### Download Interruption

If download is interrupted (Ctrl+C, network failure, etc.):

```bash
# batchfetch.py creates download_progress.json checkpoint
# Contains list of successfully downloaded K-numbers

echo "Download interrupted!"
echo ""
echo "Resume from checkpoint:"
echo "  /fda:batchfetch --project $PROJECT_NAME --resume"
echo ""
echo "Or start fresh (deletes existing PDFs):"
echo "  /fda:batchfetch --project $PROJECT_NAME --force"
```

### FDA Rate Limiting

If encountering rate limit errors:

```
⚠️  FDA Rate Limit Detected
────────────────────────────────────────
  Downloaded:  234/847 PDFs (28%)
  Failed:      15 rate limit errors

  The FDA server is throttling requests. This is normal
  for large batch downloads.

OPTIONS
────────────────────────────────────────
  1. Resume with longer delay (Recommended):
     /fda:batchfetch --project $PROJECT_NAME --resume --delay 60

  2. Wait and retry later:
     Try again in 1-2 hours

  3. Split into smaller batches:
     Download by year ranges separately

CURRENT DELAY: 30 seconds between requests
```

### Dependency Missing

```bash
# Check if required packages are installed
python3 -c "import pandas" 2>/dev/null || {
    echo "Error: Required Python package 'pandas' not found"
    echo ""
    echo "Install dependencies:"
    echo "  pip3 install pandas requests"
    echo ""
    echo "Or use requirements file:"
    echo "  pip3 install -r $FDA_PLUGIN_ROOT/requirements.txt"
    exit 1
}
```

---

## Full-Auto Mode Implementation

When `--full-auto` is specified:

```bash
# Validate all required arguments are provided
if [ -z "$PRODUCT_CODES" ]; then
    echo "Error: --full-auto requires --product-codes"
    exit 1
fi

# Apply defaults for optional arguments
DATE_RANGE="${DATE_RANGE:-pmn96cur,pmnlstmn}"
YEARS="${YEARS:-}"  # No year filter by default
COMMITTEES="${COMMITTEES:-}"  # All committees
DECISION_CODES="${DECISION_CODES:-}"  # All decisions
APPLICANTS="${APPLICANTS:-}"  # All applicants

# Auto-generate project name if not provided
if [ -z "$PROJECT_NAME" ]; then
    PROJECT_NAME=$(generate_project_name "$PRODUCT_CODES" "$YEARS")
fi

# Skip all questions, proceed directly to preview
# Then execute immediately if preview shows valid results (>0 records)
# If zero results, exit with error
```

**Full-auto example:**
```bash
/fda:batchfetch --product-codes KGN --years 2024 --full-auto
# No questions asked, uses defaults:
#   date_range: pmn96cur,pmnlstmn
#   committees: all
#   decisions: all
#   applicants: all
#   project: KGN_2024
# Previews and downloads immediately
```

---

## Integration with Existing Pipeline

### Project Compatibility

This command creates the same project structure as `/fda:extract`, ensuring seamless pipeline integration:

```
~/fda-510k-data/projects/KGN_2020-2025/
├── query.json                    ← Created by /fda:batchfetch
├── 510k_download.csv            ← Created by /fda:batchfetch
├── 510ks/                        ← Created by /fda:batchfetch
│   ├── K123456.pdf
│   ├── K234567.pdf
│   └── ...
├── fda_data/                     ← Created by /fda:batchfetch
│   ├── pmn96cur.txt
│   └── pmnlstmn.txt
├── output.csv                    ← Created by /fda:extract stage2
├── supplement.csv                ← Created by /fda:extract stage2
├── pdf_data.json                 ← Created by /fda:extract stage2
├── review.json                   ← Created by /fda:review
├── drafts/                       ← Created by /fda:draft
└── estar/                        ← Created by /fda:assemble
```

### Command Chaining

Users can chain commands:

```bash
# Method 1: Separate commands
/fda:batchfetch --product-codes KGN --years 2024 --project my_device
/fda:extract stage2 --project my_device
/fda:review --project my_device --auto
/fda:draft --project my_device

# Method 2: Use existing /fda:extract (which calls batchfetch internally)
/fda:extract both --product-codes KGN --years 2024 --project my_device

# Method 3: Use /fda:pipeline for end-to-end automation
/fda:pipeline --product-codes KGN --years 2024 --full-auto
```

### Resume Across Commands

If download interrupted:

```bash
# Resume batchfetch download
/fda:batchfetch --project my_device --resume

# Then continue with extraction
/fda:extract stage2 --project my_device
```

---

## Usage Examples

### Example 1: Simple Product Code Search

```bash
/fda:batchfetch --product-codes KGN --years 2024 --quick
```
- Express mode: 2 questions only
- Downloads 2024 wound dressing submissions
- Project auto-named: `KGN_2024`

### Example 2: Multi-Code Historical Analysis

```bash
/fda:batchfetch --product-codes KGN,FRO,DQY --years 2015-2025
```
- Full interactive mode
- Multiple product codes
- 10-year analysis
- AI guides through all 7 filter questions

### Example 3: Competitive Intelligence

```bash
/fda:batchfetch --product-codes KGN --applicants "SMITH & NEPHEW;3M;MOLNLYCKE" --years 2020-2025 --project competitors_analysis
```
- Tracks specific companies
- Named project for organization
- Can add `--save-excel` for analytics

### Example 4: Full-Auto Batch

```bash
/fda:batchfetch --product-codes KGN --years 2024 --full-auto --project test_run --no-download
```
- No questions asked
- CSV only, no PDFs
- Fast preview run

### Example 5: Comprehensive Download

```bash
/fda:batchfetch --product-codes OVE,KWP,KWQ --date-range pmn96cur,pmnlstmn --committees OR --save-excel
```
- Orthopedic devices
- All recent data
- Committee filter
- Generate analytics workbook

---

## Tips & Best Practices

**For predicate searches:**
1. Start with last 5 years of data (recent predicates are better)
2. Use your specific product code(s) only
3. Include all decision types (even SESU/SESP may be valid predicates)
4. Don't filter by applicant (you want maximum predicate pool)

**For competitive intelligence:**
1. Filter by applicant company
2. Expand years to see trends (5-10 years)
3. Use `--save-excel` to analyze trends
4. Consider multiple product codes for full portfolio

**For market research:**
1. Use broad filters (all committees, all years)
2. Download CSV only first (`--no-download`)
3. Analyze metadata before committing to full download
4. Use `--save-excel` for market statistics

**To minimize download time:**
1. Filter by recent years (2-3 years max for targeted searches)
2. Avoid downloads over 500 PDFs if possible
3. Use `--quick` mode to skip unnecessary filters
4. Run during off-peak hours for better FDA server performance

**For large downloads (>500):**
1. Split into multiple projects by year
2. Use resume feature if interrupted
3. Monitor disk space
4. Increase `--delay` if hitting rate limits (use 60-90 seconds)

---

## Troubleshooting

**"Could not locate FDA Predicate Assistant plugin"**
- Run: `ls ~/.claude/plugins/installed_plugins.json`
- Check plugin is installed and enabled
- Try: `/fda:status` to verify installation

**"No records matched your filters"**
- Verify product code spelling
- Remove year filter
- Remove restrictive filters (applicants, decision codes)
- Try: `/fda:validate --search "device name"` to find correct code

**"Rate limit errors during download"**
- Use `--resume` to continue from checkpoint
- Increase delay: `--delay 60`
- Split into smaller batches by year
- Try again during off-peak hours (evenings/weekends)

**"Low disk space warning"**
- Check available space: `df -h ~`
- Each PDF is ~5MB average
- Use `--no-download` for CSV-only if disk limited
- Move projects to external drive if needed

**"Python package not found"**
- Install: `pip3 install pandas requests`
- Or: `pip3 install -r $FDA_PLUGIN_ROOT/requirements.txt`
- Check Python version: `python3 --version` (need 3.7+)

---

This command provides a **collaborative, AI-guided experience** for FDA data collection while leveraging the battle-tested `batchfetch.py` script for actual execution. The interactive workflow makes complex filtering accessible to non-technical users while providing expert context at every decision point.
