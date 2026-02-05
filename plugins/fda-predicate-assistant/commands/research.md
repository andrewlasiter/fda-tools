---
description: Research and plan a 510(k) submission — predicate selection, testing strategy, IFU landscape, regulatory intelligence, and competitive analysis
allowed-tools: Read, Glob, Grep, Bash, Write, WebFetch, WebSearch
argument-hint: "<product-code> [--project NAME] [--device-description TEXT] [--intended-use TEXT]"
---

# FDA 510(k) Submission Research

You are helping the user research and plan a 510(k) submission. Given a product code (and optionally a device description and intended use), produce a comprehensive research package drawing from ALL available pipeline data.

**KEY PRINCIPLE: Do the work, don't ask the user to run other commands.** If PDF text is available, extract predicates from it yourself. If a data file exists but has no relevant records, don't mention it. The user should get a complete answer, not a todo list.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Product code** (required) — 3-letter FDA product code (e.g., KGN, DXY, QAS)
- `--device-description TEXT` — Brief description of the user's device
- `--intended-use TEXT` — The user's intended indications for use
- `--years RANGE` — Focus on specific year range (default: last 10 years)
- `--depth quick|standard|deep` — Level of analysis (default: standard)
- `--project NAME` — Use data from a specific project folder

If no product code provided, ask the user for it. If they're unsure of their product code, help them find it:
```bash
grep -i "DEVICE_KEYWORD" /mnt/c/510k/Python/PredicateExtraction/foiaclass.txt /mnt/c/510k/Python/510kBF/fda_data/foiaclass.txt 2>/dev/null | head -20
```

## Step 1: Discover Available Data

### If `--project NAME` is provided — Use project data first

```bash
PROJECTS_DIR="/mnt/c/510k/Python/510k_projects"  # or from settings
ls "$PROJECTS_DIR/$PROJECT_NAME/"*.csv "$PROJECTS_DIR/$PROJECT_NAME/"*.json 2>/dev/null
cat "$PROJECTS_DIR/$PROJECT_NAME/query.json" 2>/dev/null
```

### Also check for matching projects automatically

If no `--project` specified, check if a project exists for this product code:
```bash
ls /mnt/c/510k/Python/510k_projects/*/query.json 2>/dev/null
```

### Check data sources silently — only report what's RELEVANT

Check these locations, but **only mention sources to the user if they contain data for the requested product code**:

```bash
# FDA database files (always relevant — contain ALL product codes)
ls /mnt/c/510k/Python/PredicateExtraction/pmn*.txt 2>/dev/null

# PDF text cache (check if it has relevant PDFs)
ls -la /mnt/c/510k/Python/PredicateExtraction/pdf_data.json 2>/dev/null

# Download metadata (check if it has relevant product code records)
ls -la /mnt/c/510k/Python/510kBF/510k_download.csv 2>/dev/null

# Device classification
ls /mnt/c/510k/Python/510kBF/fda_data/foiaclass.txt /mnt/c/510k/Python/PredicateExtraction/foiaclass.txt 2>/dev/null
```

**IMPORTANT**: Do NOT report files that exist but contain no data for this query. For example, if `merged_data.csv` has 100 records but none match the requested product code, do not mention it at all. The user doesn't care about files that aren't relevant to their device.

## Step 2: Product Code Profile

Look up the product code in foiaclass.txt (if available):

```bash
grep "^PRODUCTCODE" /mnt/c/510k/Python/510kBF/fda_data/foiaclass.txt /mnt/c/510k/Python/PredicateExtraction/foiaclass.txt 2>/dev/null
```

Report:
- **Device name** (official FDA classification name)
- **Device class** (I, II, III)
- **Regulation number** (21 CFR section)
- **Advisory committee** (review panel)
- **Definition** (if available in foiaclass)

Then count total clearances for this product code:
```bash
grep -c "|PRODUCTCODE|" /mnt/c/510k/Python/PredicateExtraction/pmn96cur.txt /mnt/c/510k/Python/PredicateExtraction/pmn9195.txt 2>/dev/null
```

## Step 3: Regulatory Intelligence

### From FDA database files (pmn*.txt)

Filter all records for this product code:

```bash
grep "|PRODUCTCODE|" /mnt/c/510k/Python/PredicateExtraction/pmn96cur.txt 2>/dev/null
```

Analyze and report:
- **Total clearances** all-time and by decade
- **Decision code distribution**: SESE (substantially equivalent), SEKN (SE with conditions), SESK, etc.
- **Submission type breakdown**: Traditional vs Special 510(k) vs Abbreviated
- **Statement vs Summary ratio**: What percentage file summaries (more data available) vs statements
- **Third-party review usage**: How common for this product code
- **Review time statistics**: Average, median, fastest, slowest (compute from DATERECEIVED to DECISIONDATE)
- **Recent trend**: Are submissions increasing or decreasing in the last 5 years?

### From 510k_download.csv (only if it contains this product code)

```bash
grep "PRODUCTCODE" /mnt/c/510k/Python/510kBF/510k_download.csv 2>/dev/null
```

Additional metadata available: expedited review, review advisory committee details.

## Step 4: Predicate Landscape

### Extract predicates directly from PDF text

**Do NOT tell the user to run `/fda:extract stage2`.** Instead, extract predicate K-numbers yourself from `pdf_data.json`:

```python
# Extract K-numbers cited in each document's text
import json, re
from collections import Counter

with open('pdf_data.json') as f:
    data = json.load(f)

k_pattern = re.compile(r'K\d{6}')
cited_by = Counter()  # predicate -> count of devices citing it
graph = {}  # device -> set of predicates it cites

for filename, content in data.items():
    text = content.get('text', '') if isinstance(content, dict) else str(content)
    source_k = filename.replace('.pdf', '')
    found_ks = set(k_pattern.findall(text))
    found_ks.discard(source_k)  # Remove self-reference
    graph[source_k] = found_ks
    for k in found_ks:
        cited_by[k] += 1
```

This gives you the same predicate relationships that `output.csv` would contain, without requiring any separate extraction step.

### Also check output.csv and merged_data.csv if they exist AND have relevant data

These are supplementary sources. Only use them if they contain records for the requested product code.

### Rank predicate devices by:
1. **Citation frequency** — How often is this device cited as a predicate?
2. **Recency** — When was the predicate cleared? More recent = stronger
3. **Chain depth** — Is the predicate itself well-established (cited by many others)?
4. **Same applicant** — Predicates from the same company may indicate product line evolution
5. **Device similarity** — Match device name keywords to user's device description

### Build predicate chains

For the top predicate candidates, trace their lineage:
- What predicates did they cite?
- How many generations deep does the chain go?
- Is there a "root" device that anchors this product code?

### Cross-Product-Code Predicate Search

**CRITICAL**: If the user's device description mentions features that have little or no precedent in the primary product code, **automatically search other product codes** for supporting predicates.

For example, if the user describes a "collagen wound dressing with silver antimicrobial" and silver has <5% prevalence in KGN:

```bash
# Search ALL product codes for devices with the novel feature
python3 -c "
import csv
results = []
with open('/mnt/c/510k/Python/PredicateExtraction/pmn96cur.txt', encoding='latin-1') as f:
    reader = csv.reader(f, delimiter='|')
    header = next(reader)
    for row in reader:
        d = dict(zip(header, row))
        name = d.get('DEVICENAME','').upper()
        if 'SILVER' in name or 'ANTIMICROBIAL' in name:
            results.append(d)
# Group by product code and report
"
```

This helps identify **secondary predicates** from adjacent product codes that support novel features. Report these separately with clear rationale:

```
Secondary Predicate (for silver/antimicrobial claim):
  K123456 (Product Code: FRO) — Silver Wound Dressing
  - Supports your antimicrobial claim
  - Different product code but same wound management category
  - Consider citing alongside your primary KGN predicate
```

### Predicate recommendation

Based on the analysis, recommend the **top 3-5 predicate candidates** with rationale:

```
Recommended Predicates for [PRODUCT CODE]:

1. K123456 (Company A, 2023) — STRONGEST
   - Cited by 12 other devices
   - Most recent clearance with same intended use
   - Traditional 510(k) with Summary available
   - Review time: 95 days

2. K234567 (Company B, 2021) — STRONG
   - Cited by 8 other devices
   - Broader indications (your device fits within)
   - Has detailed clinical data in summary
   - Review time: 120 days
```

If the user provided `--intended-use`, compare their intended use against the indications associated with each predicate candidate.

If the user provided `--device-description` with novel features not found in the primary product code, include a **Secondary Predicates** section with candidates from other product codes that support those features.

## Step 4.5: Automatically Fetch Key Predicate Summaries

**CRITICAL: Do NOT ask the user to download PDFs separately.** After identifying the top 3-5 predicate candidates, check if their summary text is available. If not, **fetch it yourself**.

### Check if text is already cached

```python
import json
with open('/mnt/c/510k/Python/PredicateExtraction/pdf_data.json') as f:
    data = json.load(f)
# Check each top candidate
for knumber in top_candidates:
    if knumber + '.pdf' in data:
        print(f'{knumber}: text already cached')
    else:
        print(f'{knumber}: NOT cached — need to fetch')
```

### Fetch missing summaries directly from FDA

FDA 510(k) summary PDFs follow a predictable URL pattern:

```
https://www.accessdata.fda.gov/cdrh_docs/pdf{YY}/{KNUMBER}.pdf
```

Where `{YY}` is derived from the K-number:
- K241335 → pdf24 (first 2 digits after K)
- K183206 → pdf18
- K253710 → pdf25
- For older devices (K0xxxxx): pdf (no number) or pdf0, pdf1, etc.
- De Novo: `https://www.accessdata.fda.gov/cdrh_docs/reviews/DEN230052.pdf`

**IMPORTANT: FDA blocks simple HTTP requests.** You MUST use the same anti-detection techniques as the BatchFetch pipeline. Use **Bash with Python requests** (Method 1 below), NOT WebFetch, as the primary download method. FDA requires browser-like headers and consent cookies.

#### Method 1 (PRIMARY): Python requests with browser headers + FDA cookies

For each top predicate NOT already cached, download and extract text using Bash:

```bash
python3 << 'PYEOF'
import requests, sys, os, tempfile

knumber = "K241335"  # Replace with actual K-number
yy = knumber[1:3]    # e.g., "24" from K241335

# Try multiple URL patterns
urls = [
    f"https://www.accessdata.fda.gov/cdrh_docs/pdf{yy}/{knumber}.pdf",
    f"https://www.accessdata.fda.gov/cdrh_docs/reviews/{knumber}.pdf",
]
# For De Novo: urls = [f"https://www.accessdata.fda.gov/cdrh_docs/reviews/{denovo_number}.pdf",
#                       f"https://www.accessdata.fda.gov/cdrh_docs/pdf{yy}/{denovo_number}.pdf"]

# Use the same session/headers as BatchFetch (510BAtchFetch Working2.py)
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
})
session.cookies.update({
    'fda_gdpr': 'true',
    'fda_consent': 'true',
})

for url in urls:
    try:
        response = session.get(url, timeout=60, allow_redirects=True)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            # Save to temp file and extract text
            tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            tmp.write(response.content)
            tmp.close()

            # Try PyMuPDF first, then pdfplumber
            text = ""
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(tmp.name)
                text = "\n".join(page.get_text() for page in doc)
                doc.close()
            except ImportError:
                try:
                    import pdfplumber
                    with pdfplumber.open(tmp.name) as pdf:
                        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                except ImportError:
                    print(f"ERROR: Neither PyMuPDF nor pdfplumber installed. Install with: pip install PyMuPDF pdfplumber")
                    sys.exit(1)

            os.unlink(tmp.name)

            if len(text.strip()) > 100:
                print(f"SUCCESS: Downloaded {knumber} from {url}")
                print(f"TEXT_LENGTH: {len(text)}")
                print(f"---BEGIN_TEXT---")
                print(text)
                print(f"---END_TEXT---")
                sys.exit(0)
            else:
                print(f"WARNING: PDF from {url} had minimal text ({len(text)} chars) — may be scanned/image PDF")
                os.unlink(tmp.name) if os.path.exists(tmp.name) else None
    except Exception as e:
        print(f"FAILED: {url} — {e}")

print(f"FAILED: Could not download {knumber} from any URL pattern")
sys.exit(1)
PYEOF
```

**Rate limiting**: If downloading multiple PDFs, add a 5-second delay between downloads:
```python
import time
time.sleep(5)  # Between each PDF download
```

#### Method 2 (FALLBACK): WebSearch for summary details

If the Python download fails (e.g., dependencies not installed, FDA changes their blocking), fall back to WebSearch:

```
Use WebSearch tool:
  query: "K241335 510k summary indications testing biocompatibility clinical study MARD site:accessdata.fda.gov"
```

WebSearch can retrieve substantial text from FDA pages via search result snippets — often enough for testing strategy and IFU analysis even when direct PDF download fails.

#### Method 3 (LAST RESORT): WebFetch on non-FDA sources

If both Method 1 and Method 2 fail, try fetching from secondary sources that may have the document:
- PubMed/PMC clinical study publications
- Manufacturer press releases with clinical data
- FDA Devices@FDA listing pages

### Depth controls for fetching

**For standard depth**: Fetch the top 2-3 most important predicate summaries (primary predicate + strongest secondary).
**For deep depth**: Fetch up to 5 predicate summaries.
**For quick depth**: Skip fetching — use database records only.

After fetching, use the extracted text for Steps 5 (Testing Strategy), 6 (IFU Landscape), and predicate comparison analysis. This is what makes the research report truly useful — the user gets actual data from the predicate devices, not just K-numbers.

### What to extract from fetched summaries

For each fetched predicate summary, extract and report:
- **Indications for Use** — exact IFU text for comparison with user's intended use
- **Device Description** — what the predicate device is and how it works
- **Testing performed** — specific test methods, standards, sample sizes, results
- **Clinical data** — study design, endpoints, patient count, outcomes
- **Predicates cited** — what the predicate itself cited (chain analysis)
- **Key differences** — anything that might differentiate from user's device

## Step 5: Testing Strategy

### From PDF text (cached in pdf_data.json OR freshly fetched in Step 4.5)

Analyze the testing sections from predicate summaries. Use regex to search for testing-related content:

```python
patterns = {
    'ISO 10993': r'(?i)ISO\s*10993',
    'Biocompatibility': r'(?i)(biocompatib|cytotox|sensitiz|irritat)',
    'Sterilization': r'(?i)(steriliz|sterility|ethylene oxide|EtO|gamma)',
    'Shelf Life': r'(?i)(shelf\s*life|stability|accelerated\s*aging)',
    'Clinical': r'(?i)(clinical\s*(study|trial|data|evidence|testing))',
    'Animal Testing': r'(?i)(animal\s*(study|model|testing)|in\s*vivo)',
    # Add patterns specific to the user's device features
}
```

For each type of testing found, summarize:

**Non-Clinical / Performance Testing**:
- What test methods and standards are commonly cited? (ASTM, ISO, IEC, etc.)
- What performance endpoints are measured?
- What sample sizes are typical?

**Biocompatibility**:
- Which ISO 10993 endpoints are evaluated?
- Is this consistent across all devices or does it vary?

**Clinical Data**:
- What percentage of devices included clinical data?
- What type? (literature review, clinical study)
- Were any devices cleared WITHOUT clinical data?

**Sterilization** (if applicable):
- What sterilization methods are used?
- What validation standards are cited?

**Device-Specific Testing**: Based on the user's `--device-description`, add testing pattern searches for novel features. For example, if "silver" is mentioned, search for:
- Antimicrobial effectiveness (zone of inhibition, MIC/MBC)
- Silver content/release testing
- Silver-specific biocompatibility

### Testing recommendation

Provide a recommended testing matrix with Required/Likely Needed/Possibly Needed/Not Typically Required categories.

## Step 6: Indications for Use Landscape

Search for IFU content in PDF text for this product code. Analyze:
- **Common IFU elements**: What anatomical sites, patient populations, clinical conditions are covered?
- **Broadest cleared IFU**: Which device has the widest indications?
- **Narrowest cleared IFU**: Which is most restrictive?
- **Evolution over time**: Have indications expanded or narrowed?
- **If user provided --intended-use**: Compare their intended use against cleared IFUs. Flag any elements that go beyond what's been cleared before.

## Step 7: Competitive Landscape

### Top applicants

```bash
grep "|PRODUCTCODE|" /mnt/c/510k/Python/PredicateExtraction/pmn96cur.txt 2>/dev/null | cut -d'|' -f2 | sort | uniq -c | sort -rn | head -15
```

Report:
- **Market leaders**: Top companies by number of clearances
- **Recent entrants**: Companies that filed their first device in the last 3 years
- **Device name clustering**: Group device names to identify sub-categories
- **Active vs inactive**: Companies still submitting vs those who stopped

### Timeline

- Clearance volume by year (chart-like visualization using text)

## Output Format

Structure the research package as:

```
510(k) Submission Research: [PRODUCT CODE] — [DEVICE NAME]
============================================================

1. PRODUCT CODE PROFILE
   [Device class, regulation, advisory committee]

2. REGULATORY INTELLIGENCE
   [Clearance stats, review times, submission types]

3. PREDICATE CANDIDATES (Ranked)
   [Top 3-5 primary predicates from same product code]
   [Secondary predicates from other product codes if needed]

4. TESTING STRATEGY
   [Required, likely needed, possibly needed testing]

5. INDICATIONS FOR USE LANDSCAPE
   [IFU patterns, breadth analysis]

6. COMPETITIVE LANDSCAPE
   [Top companies, trends, sub-categories]

7. RECOMMENDATIONS & NEXT STEPS
   [Specific actionable next steps — NOT "run this command"]
```

**IMPORTANT**: The output should NOT have a "Data Gaps" section that lists files the user needs to create or commands to run. If a PDF is needed, fetch it yourself in Step 4.5. If a fetch fails, note the limitation gracefully (e.g., "The K241335 summary PDF was not accessible, so testing analysis is based on regulatory patterns for this device class") — do NOT tell the user to run another command.

## Depth Levels

### `--depth quick` (2-3 minutes)
- Product code profile + basic regulatory stats
- Top 3 predicate candidates (citation count only)
- Competitive landscape overview
- Skip PDF text analysis

### `--depth standard` (default, 5-10 minutes)
- Full regulatory intelligence
- Top 5 predicate candidates with chain analysis
- Cross-product-code search for novel features
- Testing strategy from PDF text (if available)
- IFU comparison
- Competitive landscape

### `--depth deep` (15+ minutes)
- Everything in standard
- Full predicate chain mapping (all generations)
- Document-by-document section analysis
- Detailed testing method comparison tables
- IFU evolution timeline
- Export-ready tables and findings

## Recommendations Section

End with specific, actionable next steps in plain language:

- If predicate candidates identified: "Use `/fda:validate K123456 K234567` to get detailed profiles of these predicate candidates"
- If testing strategy identified: "Use `/fda:summarize --product-codes PRODUCTCODE --sections 'Non-Clinical Testing'` to compare exact test methods across devices"
- If novel features found: "Your [feature] has limited precedent in [product code]. Consider consulting with your regulatory team about whether a secondary predicate from [other product code] strengthens your submission."
- Always: "Consult with regulatory affairs counsel before finalizing your submission strategy"

**NEVER recommend**: "Run `/fda:extract stage1`" or "Run `/fda:extract stage2`" or "Use `/fda:extract` to download PDFs" — the research command should fetch what it needs automatically. If a PDF fetch fails (404, access denied), note it gracefully and proceed with available data.
