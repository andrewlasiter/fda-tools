
<!-- NOTE: This command has been migrated to use centralized FDAClient (FDA-114)
     Old pattern: urllib.request.Request + urllib.request.urlopen
     New pattern: FDAClient with caching, retry, and rate limiting
     Migration date: 2026-02-20
-->

---
description: Search and analyze clinical/scientific literature for 510(k) submission support — PubMed search, evidence categorization, gap analysis vs guidance requirements
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch, WebSearch
argument-hint: "--product-code CODE [--device-description TEXT] [--project NAME] [--depth quick|standard|deep]"
---

# FDA 510(k) Literature Review Assistant

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

---

You are conducting a literature search to support a 510(k) submission. The goal is to find and categorize relevant clinical and scientific evidence, then identify gaps vs guidance requirements.

**KEY PRINCIPLE: Structured, reproducible searches.** Document search terms, databases, and results so the literature review can be reproduced and updated.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--product-code CODE` (required unless --infer) — 3-letter FDA product code
- `--device-description TEXT` — Device description (used to refine search terms)
- `--intended-use TEXT` — IFU text (used to identify clinical claims needing evidence)
- `--project NAME` — Save results to project folder
- `--depth quick|standard|deep` — Search depth (default: standard)
- `--infer` — Auto-detect product code from project data
- `--focus CATEGORY` — Focus on specific evidence category (clinical, bench, biocompat, adverse)
- `--output FILE` — Write results to file
- `--refresh` — Force re-query all sources, ignoring cached results

## Step 1: Build Search Strategy

### Get device context

Query openFDA for classification data (same pattern as other commands).

### Generate search terms

Based on device classification and user inputs:

```python
from fda_tools.scripts.fda_api_client import FDAClient

client = FDAClient()
# Use client methods:
# - client.get_510k(k_number)
# - client.get_classification(product_code)
# - client.get_clearances(product_code, limit=100)
# - client.get_events(product_code)
# - client.get_recalls(product_code)
# - client.search_pma(product_code=code, applicant=name)

# Build structured search terms
search_terms = {
    "device_terms": [],     # Device name variants
    "clinical_terms": [],   # Clinical outcome terms
    "safety_terms": [],     # Safety/adverse event terms
    "standard_terms": [],   # Testing standard terms
}

# Device name variants from classification
device_name = "CLASSIFICATION_DEVICE_NAME"
search_terms["device_terms"] = [
    device_name,
    # Add common synonyms/variants
]

# Clinical terms from IFU
if intended_use:
    # Parse IFU claims into searchable terms
    pass

# Safety terms from MAUDE common failure modes
search_terms["safety_terms"] = [
    f'"{device_name}" adverse event',
    f'"{device_name}" complication',
    f'"{device_name}" failure',
]
```

## Step 2: Execute Searches

### 2A: PubMed via NCBI E-utilities API (Clinical Evidence)

Use the NCBI E-utilities API for structured, reproducible PubMed searches. See `references/pubmed-api.md` for endpoint details and MeSH term mapping.

**Check for NCBI API key** (optional — increases rate limit from 3 to 10 requests/sec):

```bash
python3 << 'PYEOF'
import os, re
ncbi_key = os.environ.get('NCBI_API_KEY')
if not ncbi_key:
    settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            m = re.search(r'ncbi_api_key:\s*(\S+)', f.read())
            if m and m.group(1) != 'null':
                ncbi_key = m.group(1)
print(f"NCBI_KEY:{'yes' if ncbi_key else 'no'}")
PYEOF
```

**Search PubMed using E-utilities:**

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time, xml.etree.ElementTree as ET

# Get NCBI API key
ncbi_key = os.environ.get('NCBI_API_KEY')
if not ncbi_key:
    settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            m = re.search(r'ncbi_api_key:\s*(\S+)', f.read())
            if m and m.group(1) != 'null':
                ncbi_key = m.group(1)

device_name = "DEVICE_NAME"  # Replace from Step 1
intended_use = "INTENDED_USE"  # Replace or empty

base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

def esearch(query, retmax=20):
    """Search PubMed and return PMIDs."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": str(retmax),
        "retmode": "json",
        "sort": "relevance",
        "tool": "fda-tools",
        "email": "plugin@example.com"
    }
    if ncbi_key:
        params["api_key"] = ncbi_key
    url = f"{base_url}/esearch.fcgi?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "FDA-Plugin/5.21.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return data.get("esearchresult", {})

def efetch(pmids):
    """Fetch article details for given PMIDs."""
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
        "tool": "fda-tools",
        "email": "plugin@example.com"
    }
    if ncbi_key:
        params["api_key"] = ncbi_key
    url = f"{base_url}/efetch.fcgi?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "FDA-Plugin/5.21.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return ET.parse(resp)

# Search categories with structured queries
searches = {
    "clinical": f'("{device_name}"[Title/Abstract]) AND (clinical trial[Publication Type] OR clinical study[Title/Abstract] OR randomized[Title/Abstract])',
    "safety": f'("{device_name}"[Title/Abstract]) AND (adverse event[Title/Abstract] OR complication[Title/Abstract] OR safety[Title/Abstract])',
    "biocompat": f'("{device_name}"[Title/Abstract]) AND (biocompatibility[Title/Abstract] OR cytotoxicity[Title/Abstract] OR "ISO 10993"[Title/Abstract])',
}

results = {}
for category, query in searches.items():
    try:
        sr = esearch(query)
        pmids = sr.get("idlist", [])
        total = sr.get("count", "0")
        print(f"CATEGORY:{category}|TOTAL:{total}|RETURNED:{len(pmids)}")
        if pmids:
            results[category] = pmids
            # Fetch details
            time.sleep(0.4 if ncbi_key else 1.0)
            tree = efetch(pmids[:10])  # Fetch top 10
            for article in tree.findall(".//PubmedArticle"):
                pmid = article.findtext(".//PMID", "")
                title = article.findtext(".//ArticleTitle", "N/A")
                year = article.findtext(".//PubDate/Year", "N/A")
                journal = article.findtext(".//Journal/Title", "N/A")
                pub_type = article.findtext(".//PublicationType", "")
                print(f"ARTICLE:{category}|PMID:{pmid}|YEAR:{year}|TITLE:{title[:120]}|JOURNAL:{journal}|TYPE:{pub_type}")
        time.sleep(0.4 if ncbi_key else 1.0)
    except Exception as e:
        print(f"ESEARCH_ERROR:{category}|{e}")

print(f"\nSEARCH_QUERIES_USED:")
for cat, q in searches.items():
    print(f"  {cat}: {q}")
PYEOF
```

**If E-utilities API fails**, fall back to WebSearch:
```
WebSearch: "{device_name}" clinical trial OR clinical study site:pubmed.ncbi.nlm.nih.gov
```

### 2B: Bench Testing, Standards, and Other Literature (via WebSearch)

For non-PubMed categories, use WebSearch:

**Bench testing**:
```
WebSearch: "{device_name}" bench testing OR mechanical testing OR performance testing
```

**Standards / Guidelines**:
```
WebSearch: "{device_name}" "{applicable_standard}" testing
```

**Adverse events / complications** (supplement MAUDE data):
```
WebSearch: "{device_name}" adverse event OR complication OR recall
```

### 2C: Deep Fetch (--depth deep only)

For top PubMed results, fetch full abstracts:
```
WebFetch: url="https://pubmed.ncbi.nlm.nih.gov/{PMID}/" prompt="Extract: study type, sample size, device tested, key outcomes, adverse events, and conclusion."
```

## Step 2.5: Search Result Caching

### Cache Structure

When `--project` is specified, cache search results to `{projects_dir}/{project_name}/literature_cache.json`:

```json
{
  "cached_date": "2026-02-08T14:30:00Z",
  "product_code": "OVE",
  "device_name": "Device Name",
  "search_queries": {
    "clinical": "(...query...)",
    "safety": "(...query...)",
    "biocompat": "(...query...)"
  },
  "results": {
    "clinical": [
      {"pmid": "38123456", "title": "...", "year": "2024", "journal": "...", "pub_type": "Clinical Trial"}
    ],
    "safety": [],
    "biocompat": []
  },
  "web_results": {
    "bench": [{"title": "...", "url": "...", "snippet": "..."}]
  },
  "total_unique": 15,
  "cache_version": "1.0"
}
```

### Cache Behavior

**Default (no flag):**
1. Check if `literature_cache.json` exists in project directory
2. If cache exists and is less than 7 days old, use cached results and skip API calls
3. If cache is stale or missing, run full search and update cache
4. Report: `"Using cached results from {date} ({N} articles). Use --refresh to re-query."`

**`--refresh` mode:**
1. Ignore any existing cache
2. Run full search against all sources
3. Write new `literature_cache.json` to project directory
4. Report: `"Cache refreshed with {N} new results."`

### Write Cache After Search

After Step 2 completes (all searches done), write results to cache:

```bash
python3 << 'PYEOF'
import json, os, re
from datetime import datetime

settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m: projects_dir = os.path.expanduser(m.group(1).strip())

project_name = "PROJECT_NAME"  # Replace with actual
cache_path = os.path.join(projects_dir, project_name, 'literature_cache.json')

cache = {
    "cached_date": datetime.utcnow().isoformat() + "Z",
    "product_code": "CODE",  # Replace
    "device_name": "NAME",   # Replace
    "search_queries": {},     # Populated from Step 2 queries
    "results": {},            # Populated from Step 2 PubMed results
    "web_results": {},        # Populated from Step 2 WebSearch results
    "total_unique": 0,        # Count
    "cache_version": "1.0"
}

os.makedirs(os.path.dirname(cache_path), exist_ok=True)
with open(cache_path, 'w') as f:
    json.dump(cache, f, indent=2)
print(f"CACHE_WRITTEN:{cache_path}")
PYEOF
```

## Step 3: Categorize Results

Organize found literature into categories:

```markdown
## Literature Review Results

### Category 1: Clinical Studies ({count} found)

| # | Title | Type | N | Device | Key Finding | Relevance |
|---|-------|------|---|--------|-------------|-----------|
| 1 | {title} | RCT | 120 | {device} | {finding} | High |
| 2 | {title} | Case series | 45 | {device} | {finding} | Medium |

### Category 2: Bench/Performance Testing ({count} found)

| # | Title | Test Type | Standard | Key Result | Relevance |
|---|-------|-----------|----------|------------|-----------|

### Category 3: Biocompatibility ({count} found)

| # | Title | ISO 10993 Part | Material | Result | Relevance |

### Category 4: Adverse Events / Safety ({count} found)

| # | Title | Type | Key Finding | Relevance |

### Category 5: Standards / Regulatory ({count} found)

| # | Title | Standard | Applicability | Notes |
```

## Step 4: Gap Analysis vs Guidance Requirements

If `--project` has guidance_cache, compare literature findings against guidance requirements:

```markdown
## Literature Gap Analysis

| Guidance Requirement | Literature Support | Gap Status |
|---------------------|--------------------|------------|
| Biocompatibility (ISO 10993) | 3 studies found | SUPPORTED |
| Mechanical testing (ASTM) | 1 bench study | PARTIAL |
| Clinical outcomes | 0 clinical trials | GAP |
| Sterilization validation | 2 studies | SUPPORTED |
| Shelf life | 0 studies | GAP |

### Gaps Requiring Attention
1. **Clinical outcomes**: No clinical trials found for this specific device type.
   → Recommendation: Consider literature review of analogous devices, or plan clinical study.
2. **Shelf life**: No accelerated aging literature found.
   → Recommendation: Standard ASTM F1980 testing — literature not typically needed.
```

## Step 5: Generate Report

Write `literature_review.md` to the project folder:

This is a document-format command (writes to file). Use markdown headings per R11 from `references/output-formatting.md`, but include standard status indicators (R5), score format (R6), and disclaimer:

```markdown
# Literature Review: {Product Code} — {Device Name}

**Generated:** {date} | **Depth:** {quick|standard|deep} | **v5.22.0**

---

## Search Summary

| Category          | Sources Found |
|-------------------|---------------|
| Clinical studies  | {N}           |
| Bench testing     | {N}           |
| Biocompatibility  | {N}           |
| Adverse events    | {N}           |
| Standards         | {N}           |
| **Total unique**  | **{N}**       |

## Categorized Results

{Results tables per category}

## Gap Analysis

{Gap analysis if guidance data available}

## Recommendations

{Based on gap analysis}

## Search Reproducibility

**Search terms used:**
{List all search queries executed}

**Databases searched:**
- PubMed (via NCBI E-utilities API — esearch + efetch)
- General web (via WebSearch — bench testing, standards)
- FDA MAUDE (via openFDA API)
- FDA Recalls (via openFDA API)
{Others as applicable}

**PubMed API queries (reproducible):**
{List exact esearch queries with PMIDs returned}

---



## Output Format

### Sources Checked

Append a sources table to every output showing which external APIs were queried and their status. See [CONNECTORS.md](../CONNECTORS.md) for the standard format. Only include rows for sources this command actually uses.



> It may not be comprehensive. A systematic review per your SOPs is recommended.
> Verify independently. Not regulatory advice.
```

## Error Handling

- **No product code**: ERROR with usage
- **No search results**: Report "No literature found for {search terms}. Consider broadening search or running with --depth deep."
- **WebSearch unavailable**: "Literature search requires web access. Run with internet connectivity."
