---
description: Search and analyze clinical/scientific literature for 510(k) submission support — PubMed search, evidence categorization, gap analysis vs guidance requirements
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch, WebSearch
argument-hint: "--product-code CODE [--device-description TEXT] [--project NAME] [--depth quick|standard|deep]"
---

# FDA 510(k) Literature Review Assistant

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

## Step 1: Build Search Strategy

### Get device context

Query openFDA for classification data (same pattern as other commands).

### Generate search terms

Based on device classification and user inputs:

```python
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

### PubMed via WebSearch

For each search category, run targeted WebSearch queries:

**Clinical evidence**:
```
WebSearch: "{device_name}" clinical trial OR clinical study site:pubmed.ncbi.nlm.nih.gov
```

**Bench testing**:
```
WebSearch: "{device_name}" bench testing OR mechanical testing OR performance testing
```

**Biocompatibility**:
```
WebSearch: "{device_name}" biocompatibility OR cytotoxicity OR ISO 10993
```

**Adverse events / complications**:
```
WebSearch: "{device_name}" adverse event OR complication OR recall
```

**Standards / Guidelines**:
```
WebSearch: "{device_name}" "{applicable_standard}" testing
```

### For --depth deep: WebFetch on top results

```
WebFetch: url="{pubmed_url}" prompt="Extract: study type, sample size, device tested, key outcomes, adverse events, and conclusion."
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

**Generated:** {date} | **Depth:** {quick|standard|deep} | **v4.0.0**

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
- PubMed (via WebSearch)
- FDA MAUDE (via openFDA API)
- FDA Recalls (via openFDA API)
{Others as applicable}

---

> **Disclaimer:** This literature review is AI-generated from web search results.
> It may not be comprehensive. A systematic review per your SOPs is recommended.
> Verify independently. Not regulatory advice.
```

## Error Handling

- **No product code**: ERROR with usage
- **No search results**: Report "No literature found for {search terms}. Consider broadening search or running with --depth deep."
- **WebSearch unavailable**: "Literature search requires web access. Run with internet connectivity."
