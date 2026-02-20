---
name: pma-search
description: Search and analyze PMA approvals - look up PMAs, download SSED documents, extract sections, and generate intelligence reports
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - WebFetch
  - AskUserQuestion
argument-hint: "--pma P170019 | --product-code NMH | --device 'Foundation Medicine' | --year 2024"
---

# PMA Search Command

Search, download, and analyze PMA (Premarket Approval) data from the FDA.

## Arguments

Parse the user's arguments to determine the search mode:

| Flag | Description | Example |
|------|-------------|---------|
| `--pma NUMBER` | Look up specific PMA | `--pma P170019` |
| `--product-code CODE` | Search by product code | `--product-code NMH` |
| `--device NAME` | Search by device name | `--device "Foundation Medicine"` |
| `--applicant NAME` | Search by applicant | `--applicant "Edwards"` |
| `--year YYYY` | Filter by approval year | `--year 2024` |
| `--download-ssed` | Download SSED PDFs | (flag) |
| `--extract-sections` | Parse SSED into 15 sections | (flag) |
| `--supplements` | Include supplement data | (flag) |
| `--output DIR` | Custom output directory | `--output ~/my-pma-data` |
| `--refresh` | Force refresh from API | (flag) |
| `--show-manifest` | Show PMA cache summary | (flag) |
| `--stats` | Show cache statistics | (flag) |
| `--compare` | Trigger comparison after search | (flag) |
| `--intelligence` | Generate intelligence report after search | (flag) |
| `--related` | Find comparable PMAs | (flag) |

## Step 1: Determine Search Mode

Based on the provided arguments, determine which workflow to execute:

1. **Single PMA Lookup** (`--pma P170019`): Fetch detailed PMA data
2. **Product Code Search** (`--product-code NMH`): Find all PMAs for a device type
3. **Device Name Search** (`--device "name"`): Search by trade name
4. **Applicant Search** (`--applicant "company"`): Search by company name
5. **Manifest View** (`--show-manifest`): Display cached PMA data summary
6. **Statistics** (`--stats`): Show cache statistics

## Step 2: Set Up Data Store

```bash
# Determine script directory
SCRIPT_DIR="$(dirname "$(find /home -path '*/fda-tools/scripts/pma_data_store.py' -type f 2>/dev/null | head -1)")"

# Verify scripts exist
ls -la "$SCRIPT_DIR/pma_data_store.py" "$SCRIPT_DIR/pma_ssed_cache.py" "$SCRIPT_DIR/pma_section_extractor.py"
```

## Step 3: Execute Search

### Mode 1: Single PMA Lookup

```bash
python3 "$SCRIPT_DIR/pma_data_store.py" --pma P170019
```

Parse the KEY:VALUE output:
- `PMA_NUMBER:` - PMA approval number
- `APPLICANT:` - Company name
- `DEVICE_NAME:` - Trade/device name
- `PRODUCT_CODE:` - FDA product code
- `DECISION_DATE:` - Approval date (YYYYMMDD)
- `ADVISORY_COMMITTEE:` - Review committee

If `--supplements` flag is present, also fetch supplements:
```bash
python3 "$SCRIPT_DIR/pma_data_store.py" --pma P170019
# Then check the supplements.json in the cache directory
```

### Mode 2: Product Code Search

```bash
python3 "$SCRIPT_DIR/pma_data_store.py" --product-code NMH --year 2024
```

### Mode 3: Device Name Search

Use the FDAClient search_pma method:
```bash
python3 -c "
import sys, json
sys.path.insert(0, '$SCRIPT_DIR')
from fda_api_client import FDAClient
client = FDAClient()
result = client.search_pma(device_name='Foundation Medicine', limit=25)
for r in result.get('results', []):
    print(f\"{r.get('pma_number','N/A')}|{r.get('trade_name','N/A')}|{r.get('decision_date','N/A')}|{r.get('product_code','N/A')}\")
"
```

### Mode 4: Manifest View

```bash
python3 "$SCRIPT_DIR/pma_data_store.py" --show-manifest
```

### Mode 5: Cache Statistics

```bash
python3 "$SCRIPT_DIR/pma_data_store.py" --stats
```

## Step 4: SSED Download (if --download-ssed)

If the `--download-ssed` flag is provided:

1. Collect PMA numbers from search results
2. If more than 10 PMAs, ask user for confirmation:

```
Found 25 PMAs for product code NMH. Download all 25 SSED PDFs?
This will download approximately 25-75 MB from FDA servers.
Rate limited to 2 requests/second (approximately 15-30 seconds).

Proceed? (y/n)
```

3. Execute batch download:
```bash
python3 "$SCRIPT_DIR/pma_ssed_cache.py" --list "P170019,P200024,P070004" --rate-limit 0.5
```

4. Report results:
```
SSED Download Summary:
  Downloaded: 20/25
  Skipped: 3 (already cached)
  Failed: 2 (HTTP 404)
  Total size: 45.2 MB
```

## Step 5: Section Extraction (if --extract-sections)

If the `--extract-sections` flag is provided (requires SSED download):

```bash
python3 "$SCRIPT_DIR/pma_section_extractor.py" --batch "P170019,P200024,P070004"
```

Display extraction results:
```
Section Extraction Results:
  P170019: 12/15 sections, quality=HIGH (85/100)
  P200024: 10/15 sections, quality=MEDIUM (62/100)
  P070004: 8/15 sections, quality=MEDIUM (55/100)
```

## Step 6: Format and Display Results

### Summary Table Format

Present results in a clear table format:

```markdown
## PMA Search Results

**Query:** Product Code NMH, Year 2024
**Total Results:** 12 PMAs found

| PMA Number | Device Name | Applicant | Approval Date | Product Code | SSED | Sections |
|------------|-------------|-----------|---------------|--------------|------|----------|
| P240024 | Device X | Company A | 2024-03-15 | NMH | Yes | 12/15 |
| P240018 | Device Y | Company B | 2024-01-22 | NMH | Yes | 10/15 |
...
```

### Detailed Single PMA Format

For single PMA lookup, provide comprehensive detail:

```markdown
## PMA P170019 - FoundationOne CDx

**Applicant:** Foundation Medicine, Inc.
**Device Name:** FoundationOne CDx
**Product Code:** NMH
**Decision Date:** November 30, 2017
**Advisory Committee:** Clinical Chemistry (CH)
**Decision Code:** APPR (Approved)

### Supplement History
- S029 (2021-07-16): New indication - BRCA1/2
- S028 (2021-05-21): Labeling update
...

### Extracted Sections (if available)
- General Information (500 words, HIGH confidence)
- Indications for Use (1200 words, HIGH confidence)
- Device Description (3500 words, HIGH confidence)
- Clinical Studies (8000 words, HIGH confidence)
- Overall Conclusions (600 words, MEDIUM confidence)
...
```

## Step 7: Intelligence Report (if multiple PMAs)

When analyzing multiple PMAs (product code or applicant search), generate insights:

```markdown
## PMA Intelligence Report

**Product Code:** NMH
**Time Period:** 2020-2024
**PMAs Analyzed:** 12

### Approval Trends
- Average approval timeline: 18 months
- Most active applicants: Foundation Medicine (4), Roche (2)
- Advisory committee: Clinical Chemistry (100%)

### Clinical Evidence Patterns
- All PMAs included pivotal clinical studies
- Average enrollment: 1,200 patients
- Common endpoints: sensitivity, specificity, PPA, NPA

### Common Testing Sections
- Biocompatibility: present in 8/12 (67%)
- Electrical Safety: present in 3/12 (25%)
- Software Validation: present in 10/12 (83%)
```

## Step 8: Comparison Trigger (if --compare)

If the `--compare` flag is present after a multi-PMA search:

1. Take the first PMA as primary and the rest as comparators
2. Run the comparison engine:
```bash
SCRIPT_DIR="$(dirname "$(find /home -path '*/fda-tools/scripts/pma_comparison.py' -type f 2>/dev/null | head -1)")"
python3 "$SCRIPT_DIR/pma_comparison.py" --primary P170019 --comparators P160035,P200024
```
3. Display the comparison report inline

For single PMA lookup with `--compare`, ask the user which PMAs to compare against.

## Step 9: Intelligence Trigger (if --intelligence)

If the `--intelligence` flag is present:

```bash
SCRIPT_DIR="$(dirname "$(find /home -path '*/fda-tools/scripts/pma_intelligence.py' -type f 2>/dev/null | head -1)")"
python3 "$SCRIPT_DIR/pma_intelligence.py" --pma P170019 --focus all
```

Display the intelligence report inline after the search results.

## Step 10: Related PMAs Trigger (if --related)

If the `--related` flag is present:

```bash
SCRIPT_DIR="$(dirname "$(find /home -path '*/fda-tools/scripts/pma_intelligence.py' -type f 2>/dev/null | head -1)")"
python3 "$SCRIPT_DIR/pma_intelligence.py" --pma P170019 --focus predicates --json
```

Display comparable PMAs and related 510(k) clearances.

## Error Handling

- **API errors**: Display error message with suggestion to retry with `--refresh`
- **Download failures**: Report failed PMAs with error reasons
- **No results**: Suggest alternative search terms or broader criteria
- **Missing PDF library**: Inform user to install pdfplumber (`pip install pdfplumber`)

## Examples

```bash
# Quick PMA lookup
/fda-tools:pma-search --pma P170019

# Search by product code with year filter
/fda-tools:pma-search --product-code NMH --year 2024

# Full pipeline: search, download, extract
/fda-tools:pma-search --product-code NMH --download-ssed --extract-sections

# Search by company
/fda-tools:pma-search --applicant "Edwards Lifesciences" --year 2023

# View cached data
/fda-tools:pma-search --show-manifest

# Force refresh
/fda-tools:pma-search --pma P170019 --refresh --download-ssed --extract-sections

# Search with comparison
/fda-tools:pma-search --product-code NMH --year 2024 --compare

# Search with intelligence report
/fda-tools:pma-search --pma P170019 --intelligence

# Find related PMAs
/fda-tools:pma-search --pma P170019 --related
```

## Rate Limiting

All FDA server requests are rate-limited:
- openFDA API: Automatic retry with exponential backoff
- SSED downloads: 500ms between requests (2 req/sec)
- Configurable via `--rate-limit` in batch operations

## Data Persistence

All data is cached in `~/fda-510k-data/pma_cache/`:
- API data: 7-day TTL (auto-refresh)
- SSED PDFs: Permanent (no expiration)
- Extracted sections: Permanent (no expiration)
- Search results: 24-hour TTL
- Manifest: Updated on every operation
