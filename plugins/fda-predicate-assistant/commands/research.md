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

### 2A: openFDA API Classification (Primary)

Query the classification endpoint for the richest data. Uses the template from `references/openfda-api.md`:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')  # Env var takes priority (never enters chat)
api_enabled = True
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:  # Only check file if env var not set
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)
    m = re.search(r'openfda_enabled:\s*(\S+)', content)
    if m and m.group(1).lower() == 'false':
        api_enabled = False

product_code = "PRODUCTCODE"  # Replace

if api_enabled:
    def fda_query(endpoint, search, limit=10, count_field=None):
        params = {"search": search, "limit": str(limit)}
        if count_field:
            params["count"] = count_field
        if api_key:
            params["api_key"] = api_key
        url = f"https://api.fda.gov/device/{endpoint}.json?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"results": []}
            return {"error": f"HTTP {e.code}"}
        except Exception as e:
            return {"error": str(e)}

    # Classification lookup
    result = fda_query("classification", f'product_code:"{product_code}"')
    if result.get("results"):
        r = result["results"][0]
        print(f"DEVICE_NAME:{r.get('device_name', 'N/A')}")
        print(f"DEVICE_CLASS:{r.get('device_class', 'N/A')}")
        print(f"REGULATION:{r.get('regulation_number', 'N/A')}")
        print(f"PANEL:{r.get('medical_specialty_description', r.get('review_panel', 'N/A'))}")
        print(f"DEFINITION:{r.get('definition', 'N/A')}")
        print(f"GMP_EXEMPT:{r.get('gmp_exempt_flag', 'N/A')}")
        print(f"THIRD_PARTY_FLAG:{r.get('third_party_flag', 'N/A')}")
        print(f"SOURCE:openFDA API")
    else:
        print("API_FALLBACK:true")

    # Also get total 510(k) clearance count from the API
    import time
    time.sleep(0.5)
    count_result = fda_query("510k", f'product_code:"{product_code}"', limit=1)
    total = count_result.get("meta", {}).get("results", {}).get("total", 0)
    print(f"TOTAL_CLEARANCES:{total}")
else:
    print("API_FALLBACK:true")
PYEOF
```

### 2B: Flat-File Fallback

If API is unavailable, fall back to foiaclass.txt:

```bash
grep "^PRODUCTCODE" /mnt/c/510k/Python/510kBF/fda_data/foiaclass.txt /mnt/c/510k/Python/PredicateExtraction/foiaclass.txt 2>/dev/null
```

And count total clearances from flat files:
```bash
grep -c "|PRODUCTCODE|" /mnt/c/510k/Python/PredicateExtraction/pmn96cur.txt /mnt/c/510k/Python/PredicateExtraction/pmn9195.txt 2>/dev/null
```

Report:
- **Device name** (official FDA classification name)
- **Device class** (I, II, III)
- **Regulation number** (21 CFR section)
- **Advisory committee** (review panel)
- **Definition** (if available)
- **Total clearances** (all-time)

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

## Step 3.5: Safety Intelligence (API)

**If the openFDA API is available**, query MAUDE event counts and recall data for this product code. This provides critical safety context for predicate selection and testing strategy.

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')  # Env var takes priority (never enters chat)
api_enabled = True
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:  # Only check file if env var not set
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)
    m = re.search(r'openfda_enabled:\s*(\S+)', content)
    if m and m.group(1).lower() == 'false':
        api_enabled = False

if not api_enabled:
    print("SAFETY_SKIP:api_disabled")
    exit(0)

product_code = "PRODUCTCODE"  # Replace

def fda_query(endpoint, search, limit=10, count_field=None):
    params = {"search": search, "limit": str(limit)}
    if count_field:
        params["count"] = count_field
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/{endpoint}.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"results": []}
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}

# MAUDE event count by type
print("=== MAUDE SUMMARY ===")
events = fda_query("event", f'device.product_code:"{product_code}"', count_field="event_type.exact")
if "results" in events:
    total = sum(r["count"] for r in events["results"])
    print(f"TOTAL_EVENTS:{total}")
    for r in events["results"]:
        print(f"EVENT_TYPE:{r['term']}:{r['count']}")
else:
    print("TOTAL_EVENTS:0")

# Recall count by classification
time.sleep(0.5)
print("\n=== RECALL SUMMARY ===")
recalls = fda_query("recall", f'product_code:"{product_code}"', count_field="classification.exact")
if "results" in recalls:
    total_r = sum(r["count"] for r in recalls["results"])
    print(f"TOTAL_RECALLS:{total_r}")
    for r in recalls["results"]:
        print(f"RECALL_CLASS:{r['term']}:{r['count']}")
else:
    print("TOTAL_RECALLS:0")

# Active recalls
time.sleep(0.5)
active = fda_query("recall", f'product_code:"{product_code}"+AND+recall_status:"Ongoing"', limit=5)
if active.get("results"):
    print(f"\nACTIVE_RECALLS:{len(active['results'])}")
    for r in active["results"]:
        print(f"ACTIVE:{r.get('recalling_firm','N/A')}|{r.get('classification','N/A')}|{r.get('reason_for_recall','N/A')[:100]}")
else:
    print("\nACTIVE_RECALLS:0")
PYEOF
```

**Include in the research report as a brief safety summary:**
- Total MAUDE events (by type) and events-per-clearance ratio
- Total recalls (by class) and any active recalls
- If high event rate or Class I recalls: Flag as a pre-submission discussion point
- If death events >0: Flag prominently

**For deeper analysis**: Suggest `/fda:safety --product-code CODE` in the Recommendations section. Do NOT run the full safety analysis inline (it's too detailed for the research report).

## Step 4: Predicate Landscape

### Extract predicates directly from PDF text

**Do NOT tell the user to run `/fda:extract stage2`.** Instead, extract predicate device numbers yourself from cached PDF text.

**Cache format detection**: The system may use either per-device cache (new) or a monolithic pdf_data.json (legacy). Check both:

```python
import json, re, os
from collections import Counter

device_pattern = re.compile(r'\b(?:K\d{6}|P\d{6}|DEN\d{6}|N\d{4,5})\b', re.IGNORECASE)
cited_by = Counter()
graph = {}

# Try per-device cache first (scalable)
cache_dir = '/mnt/c/510k/Python/PredicateExtraction/cache'
index_file = os.path.join(cache_dir, 'index.json')

if os.path.exists(index_file):
    with open(index_file) as f:
        index = json.load(f)
    for knumber, meta in index.items():
        device_path = os.path.join('/mnt/c/510k/Python/PredicateExtraction', meta['file_path'])
        if os.path.exists(device_path):
            with open(device_path) as f:
                device_data = json.load(f)
            text = device_data.get('text', '')
            found_devices = set(m.upper() for m in device_pattern.findall(text))
            found_devices.discard(knumber.upper())
            graph[knumber] = found_devices
            for d in found_devices:
                cited_by[d] += 1
else:
    # Legacy: monolithic pdf_data.json
    pdf_json = '/mnt/c/510k/Python/PredicateExtraction/pdf_data.json'
    if os.path.exists(pdf_json):
        with open(pdf_json) as f:
            data = json.load(f)
        for filename, content in data.items():
            text = content.get('text', '') if isinstance(content, dict) else str(content)
            source_id = filename.replace('.pdf', '').upper()
            found_devices = set(m.upper() for m in device_pattern.findall(text))
            found_devices.discard(source_id)
            graph[source_id] = found_devices
            for d in found_devices:
                cited_by[d] += 1
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
import json, os

cache_dir = '/mnt/c/510k/Python/PredicateExtraction/cache'
index_file = os.path.join(cache_dir, 'index.json')

# Try per-device cache first (scalable)
if os.path.exists(index_file):
    with open(index_file) as f:
        index = json.load(f)
    for knumber in top_candidates:
        if knumber in index:
            device_path = os.path.join('/mnt/c/510k/Python/PredicateExtraction', index[knumber]['file_path'])
            if os.path.exists(device_path):
                print(f'{knumber}: text cached (per-device)')
            else:
                print(f'{knumber}: index entry exists but file missing — need to fetch')
        else:
            print(f'{knumber}: NOT cached — need to fetch')
else:
    # Legacy: monolithic pdf_data.json
    pdf_json = '/mnt/c/510k/Python/PredicateExtraction/pdf_data.json'
    if os.path.exists(pdf_json):
        with open(pdf_json) as f:
            data = json.load(f)
        for knumber in top_candidates:
            if knumber + '.pdf' in data:
                print(f'{knumber}: text cached (legacy pdf_data.json)')
            else:
                print(f'{knumber}: NOT cached — need to fetch')
    else:
        print('No cache found — all candidates need fetching')
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

### From PDF text (cached in per-device cache or legacy pdf_data.json, OR freshly fetched in Step 4.5)

Analyze the testing sections from predicate summaries. Use the centralized patterns from `references/section-patterns.md` for section detection. Key patterns:

```python
# Universal section patterns (from references/section-patterns.md)
patterns = {
    'Biocompatibility': r'(?i)(biocompatib(ility|le)?|biological\s+(evaluation|testing|safety|assessment)|iso\s*10993|cytotoxicity|sensitization\s+test|irritation\s+test|systemic\s+toxicity|genotoxicity|implantation\s+(testing|studies|study)|hemocompatibility|material\s+characterization|extractables?\s+and\s+leachables?)',
    'Sterilization': r'(?i)(steriliz(ation|ed|ing)|sterility\s+(assurance|testing|validation)|ethylene\s+oxide|eto|gamma\s+(radiation|irradiation|steriliz)|electron\s+beam|e[-]?beam|steam\s+steriliz|autoclave|iso\s*11135|iso\s*11137|sal\s+10)',
    'Shelf Life': r'(?i)(shelf[-]?life|stability\s+(testing|studies|data)|accelerated\s+aging|real[-]?time\s+aging|package\s+(integrity|testing|validation|aging)|astm\s*f1980|expiration\s+dat(e|ing)|storage\s+condition)',
    'Non-Clinical Testing': r'(?i)(non[-]?clinical\s+(testing|studies|data|performance)|performance\s+(testing|data|evaluation|characteristics|bench)|bench\s+(testing|top\s+testing)|in\s+vitro\s+(testing|studies)|mechanical\s+(testing|characterization)|laboratory\s+testing|verification\s+(testing|studies)|validation\s+testing|analytical\s+performance)',
    'Clinical': r'(?i)(clinical\s+(testing|trial|study|studies|data|evidence|information|evaluation|investigation|performance)|human\s+(subjects?|study|clinical)|patient\s+study|pivotal\s+(study|trial)|feasibility\s+study|post[-]?market\s+(clinical\s+)?follow[-]?up|pmcf|literature\s+(review|search|summary|based)|clinical\s+experience)',
    'Software': r'(?i)(software\s+(description|validation|verification|documentation|testing|v&v|lifecycle|architecture|design)|firmware|algorithm\s+(description|validation)|cybersecurity|iec\s*62304)',
    'Electrical Safety': r'(?i)(electrical\s+safety|iec\s*60601|electromagnetic\s+(compatibility|interference)|emc|emi|wireless\s+(coexistence|testing))',
}
# Also apply device-type-specific patterns from references/section-patterns.md
# based on the product code (CGM, wound dressings, orthopedic, cardiovascular, IVD)
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

## Step 4.75: Inline Validation for Top Predicates

**For standard depth or higher**: After identifying the top 3-5 predicate candidates and fetching their PDFs, automatically include the detailed validation profile for each — the SAME information `/fda:validate` would show. Do NOT tell the user to run `/fda:validate` separately.

### API-Enhanced Predicate Profiles

**If the openFDA API is available**, query `/device/510k.json` for each top predicate to get full metadata. This is faster and more complete than grep on flat files:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')  # Env var takes priority (never enters chat)
api_enabled = True
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:  # Only check file if env var not set
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)
    m = re.search(r'openfda_enabled:\s*(\S+)', content)
    if m and m.group(1).lower() == 'false':
        api_enabled = False

# Replace with actual top predicate K-numbers
top_predicates = ["K241335", "K234567", "K345678"]

for knumber in top_predicates:
    if api_enabled:
        params = {"search": f'k_number:"{knumber}"', "limit": "1"}
        if api_key:
            params["api_key"] = api_key
        url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                if data.get("results"):
                    r = data["results"][0]
                    print(f"=== {knumber} ===")
                    print(f"APPLICANT:{r.get('applicant', 'N/A')}")
                    print(f"DEVICE_NAME:{r.get('device_name', 'N/A')}")
                    print(f"DECISION:{r.get('decision_code', 'N/A')} on {r.get('decision_date', 'N/A')}")
                    print(f"PRODUCT_CODE:{r.get('product_code', 'N/A')}")
                    print(f"CLEARANCE_TYPE:{r.get('clearance_type', 'N/A')}")
                    print(f"ADVISORY_COMMITTEE:{r.get('advisory_committee_description', 'N/A')}")
                    print(f"THIRD_PARTY:{r.get('third_party', 'N/A')}")
                    print(f"STATEMENT_OR_SUMMARY:{r.get('statement_or_summary', 'N/A')}")
                    dr = r.get('date_received', '')
                    dd = r.get('decision_date', '')
                    if dr and dd and len(dr) == 8 and len(dd) == 8:
                        from datetime import datetime
                        try:
                            days = (datetime.strptime(dd, '%Y%m%d') - datetime.strptime(dr, '%Y%m%d')).days
                            print(f"REVIEW_DAYS:{days}")
                        except:
                            pass
                    print(f"SOURCE:openFDA API")
                else:
                    print(f"=== {knumber} ===")
                    print(f"API_FOUND:false")
        except Exception as e:
            print(f"=== {knumber} ===")
            print(f"API_ERROR:{e}")
        time.sleep(0.5)
    else:
        print(f"=== {knumber} ===")
        print("API_SKIP:disabled")
PYEOF
```

If the API is unavailable, fall back to `grep` on flat files (pmn*.txt) as before.

For each top predicate candidate, include in the report:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{KNUMBER} — DETAILED PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Applicant: {from API or pmn database}
Decision: {SESE/DENG/etc.} on {date} ({review_days} days)
Product Code: {CODE} | Type: {Traditional/Special/etc.} | Summary: {Yes/No}
Advisory Committee: {panel}
Third Party Review: {Yes/No}
FDA URL: https://www.accessdata.fda.gov/cdrh_docs/pdf{YY}/{KNUMBER}.pdf

Indications for Use:
"{exact IFU text extracted from PDF}"

Predicates cited by this device: {list from PDF text}
Cited BY these other devices: {list from citation analysis}
MAUDE Events (product code): {count} total
Recalls (this device): {count} or None
PDF Summary: {text_length} chars available ({extraction status})
```

This eliminates the need for the user to run `/fda:validate` as a separate step.

## Step 5.5: Cross-Device Testing Comparison (Deep Depth Only)

**For deep depth**: After extracting testing information from predicate PDFs (Step 5), automatically compare test methods across the top 3 predicates — the SAME analysis `/fda:summarize --sections "Non-Clinical Testing"` would produce.

Use section patterns from `references/section-patterns.md` to extract testing sections from each predicate, then present as a comparison table:

```
| Test Category    | {K-number 1} | {K-number 2} | {K-number 3} |
|------------------|--------------|--------------|--------------|
| Biocompatibility | ISO 10993-5, -10 (n=X) | ISO 10993-5, -10, -23 | ISO 10993-5, -10 |
| Sterilization    | EO, ISO 11135 | Gamma, ISO 11137 | EO, ISO 11135 |
| Performance      | ASTM D1777 (n=30) | ASTM D1777 (n=20) | Not specified |
```

This eliminates the need for the user to run `/fda:summarize` as a separate step.

## Recommendations Section

End with specific, actionable next steps:

- If predicate candidates identified and user provided device description: "Use `/fda:compare-se --predicates K123456,K234567 --device-description \"your device\" --intended-use \"your IFU\"` to generate a formal Substantial Equivalence comparison table for your submission."
- If novel features found: "Your [feature] has limited precedent in [product code]. Consider consulting with your regulatory team about whether a secondary predicate from [other product code] strengthens your submission."
- Always: "Consult with regulatory affairs counsel before finalizing your submission strategy"

**NEVER recommend**: "Run `/fda:extract stage1`", "Run `/fda:extract stage2`", "Use `/fda:extract` to download PDFs", "Use `/fda:validate`" (inline it instead), or "Use `/fda:summarize --sections`" for content already covered in the research. The research command should do the work automatically. If a PDF fetch fails (404, access denied), note it gracefully and proceed with available data.
