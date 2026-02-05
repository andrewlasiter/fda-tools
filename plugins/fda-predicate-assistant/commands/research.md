---
description: Research and plan a 510(k) submission — predicate selection, testing strategy, IFU landscape, regulatory intelligence, and competitive analysis
allowed-tools: Read, Glob, Grep, Bash
argument-hint: "<product-code> [--project NAME] [--device-description TEXT] [--intended-use TEXT]"
---

# FDA 510(k) Submission Research

You are helping the user research and plan a 510(k) submission. Given a product code (and optionally a device description and intended use), produce a comprehensive research package drawing from ALL available pipeline data.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Product code** (required) — 3-letter FDA product code (e.g., KGN, DXY, QAS)
- `--device-description TEXT` — Brief description of the user's device
- `--intended-use TEXT` — The user's intended indications for use
- `--years RANGE` — Focus on specific year range (default: last 10 years)
- `--depth quick|standard|deep` — Level of analysis (default: standard)

If no product code provided, ask the user for it. If they're unsure of their product code, help them find it:
```bash
grep -i "DEVICE_KEYWORD" /mnt/c/510k/Python/PredicateExtraction/foiaclass.txt /mnt/c/510k/Python/510kBF/fda_data/foiaclass.txt 2>/dev/null | head -20
```

## Step 1: Discover Available Data

### If `--project NAME` is provided — Use project data

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

If a matching project is found, use its data and tell the user.

### Check all data sources (project + legacy + global)

```bash
# Project data (if applicable)
ls "$PROJECTS_DIR/$PROJECT_NAME/"*.csv "$PROJECTS_DIR/$PROJECT_NAME/pdf_data.json" 2>/dev/null
# Legacy locations
ls -la /mnt/c/510k/Python/510kBF/510k_download.csv 2>/dev/null
ls -la /mnt/c/510k/Python/PredicateExtraction/output.csv 2>/dev/null
ls -la /mnt/c/510k/Python/PredicateExtraction/pdf_data.json 2>/dev/null
ls -la /mnt/c/510k/Python/510kBF/merged_data.csv 2>/dev/null
# Global FDA databases (shared across projects)
ls -la /mnt/c/510k/Python/PredicateExtraction/pmn96cur.txt /mnt/c/510k/Python/PredicateExtraction/pma.txt 2>/dev/null
ls -la /mnt/c/510k/Python/510kBF/fda_data/foiaclass.txt /mnt/c/510k/Python/PredicateExtraction/foiaclass.txt 2>/dev/null
```

Adapt analysis to what exists. More data = richer research. Report any gaps and how to fill them (e.g., "Run `/fda:extract stage1 --product-codes KGN` to download PDFs for deeper analysis").

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

### From 510k_download.csv (if available, may have richer data)

```bash
grep "PRODUCTCODE" /mnt/c/510k/Python/510kBF/510k_download.csv 2>/dev/null
```

Additional metadata available: expedited review, review advisory committee details.

## Step 4: Predicate Landscape

### Identify predicate candidates

From output.csv or merged_data.csv, find the most commonly cited predicates for this product code:

```bash
grep "PRODUCTCODE" /mnt/c/510k/Python/PredicateExtraction/output.csv 2>/dev/null
grep "PRODUCTCODE" /mnt/c/510k/Python/510kBF/merged_data.csv 2>/dev/null
```

Rank predicate devices by:
1. **Citation frequency** — How often is this device cited as a predicate?
2. **Recency** — When was the predicate cleared? More recent = stronger
3. **Chain depth** — Is the predicate itself well-established (cited by many others)?
4. **Same applicant** — Predicates from the same company may indicate product line evolution

### Build predicate chains

For the top predicate candidates, trace their lineage:
- What predicates did they cite?
- How many generations deep does the chain go?
- Is there a "root" device that anchors this product code?

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

3. K345678 (Company C, 2019) — MODERATE
   - Well-established predicate chain (3 generations)
   - Narrower indications than your intended use
   - Statement only (less public data available)
```

If the user provided `--intended-use`, compare their intended use against the indications associated with each predicate candidate.

## Step 5: Testing Strategy

### From PDF text (pdf_data.json)

If PDF text is available for devices with this product code, analyze the testing sections:

Search for non-clinical and clinical testing content across matched documents. For each type of testing found, summarize:

**Non-Clinical / Performance Testing**:
- What test methods and standards are commonly cited? (ASTM, ISO, IEC, etc.)
- What performance endpoints are measured?
- What sample sizes are typical?
- Are there mandatory standards for this product code?

**Biocompatibility**:
- Which ISO 10993 endpoints are evaluated? (cytotoxicity, sensitization, irritation, etc.)
- Is this consistent across all devices or does it vary?
- Any trends in testing scope over time?

**Clinical Data**:
- What percentage of devices included clinical data?
- What type? (bench-to-clinical correlation, literature review, clinical study)
- What were typical study sizes and endpoints?
- Were any devices cleared WITHOUT clinical data?

**Sterilization** (if applicable):
- What sterilization methods are used? (EtO, gamma, steam, etc.)
- What validation standards are cited?

**Software** (if applicable):
- What level of concern? (minor, moderate, major)
- What documentation was provided?

**Electrical Safety** (if applicable):
- Which IEC 60601 editions/sections cited?
- Any product-specific standards?

### Testing recommendation

Provide a recommended testing matrix:

```
Recommended Testing Strategy for [PRODUCT CODE]:

Required / Expected:
  ✓ Performance testing per [STANDARD] — all devices did this
  ✓ Biocompatibility per ISO 10993 — cytotoxicity, sensitization, irritation
  ✓ Sterilization validation per ISO 11135 (EtO) — 85% of devices used EtO

Likely Needed:
  ~ Shelf life / package testing — 60% of devices included this
  ~ Software documentation (Level of Concern: Moderate) — if device has software

Possibly Needed:
  ? Clinical data — only 30% included clinical, mostly literature reviews
  ? Electrical safety per IEC 60601 — only if electrically powered

Not Typically Required:
  ✗ Animal studies — 0% of recent devices included this
```

## Step 6: Indications for Use Landscape

Search for IFU content in PDF text for this product code:

```bash
# Search pdf_data.json for IFU-related content in matching documents
```

Analyze:
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
- **Device name clustering**: Group device names to identify sub-categories within the product code
- **Active vs inactive**: Companies still submitting vs those who stopped

### Timeline

- Clearance volume by year (chart-like visualization using text)
- Notable events (new entrants, spikes in submissions, etc.)

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
   [Top 3-5 with rationale]

4. TESTING STRATEGY
   [Required, likely needed, possibly needed testing]

5. INDICATIONS FOR USE LANDSCAPE
   [IFU patterns, breadth analysis]

6. COMPETITIVE LANDSCAPE
   [Top companies, trends, sub-categories]

7. RECOMMENDATIONS & NEXT STEPS
   [Specific actions for the user]

8. DATA GAPS
   [What additional data would strengthen this analysis]
```

## Depth Levels

### `--depth quick` (2-3 minutes)
- Product code profile + basic regulatory stats
- Top 3 predicate candidates (citation count only)
- Competitive landscape overview
- Skip PDF text analysis

### `--depth standard` (default, 5-10 minutes)
- Full regulatory intelligence
- Top 5 predicate candidates with chain analysis
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

Always end with specific, actionable next steps:

- If PDFs not downloaded: "Run `/fda:extract stage1 --product-codes PRODUCTCODE --years 2020-2025` to download relevant PDFs"
- If text not extracted: "Run `/fda:extract stage2` to extract text for section analysis"
- If predicate candidates identified: "Run `/fda:validate K123456 K234567` for detailed predicate profiles"
- If testing strategy identified: "Run `/fda:summarize --product-codes PRODUCTCODE --sections 'Non-Clinical Testing'` for detailed test method comparison"
- If IFU analysis done: "Run `/fda:summarize --product-codes PRODUCTCODE --sections 'Indications for Use'` for full IFU text comparison"
- Always: "Consult with regulatory affairs counsel before finalizing your submission strategy"
