---
description: Validate FDA device numbers against official databases and all available pipeline data
allowed-tools: Bash, Read, Grep, Glob
argument-hint: "<number> [number2] [number3] ..."
---

# FDA Device Number Validation (Enriched)

You are validating FDA device numbers against official databases AND enriching results with data from the full pipeline.

## Device Number Formats

- **K-numbers (510(k))**: K + 6 digits (e.g., K240717, K991234)
- **P-numbers (PMA)**: P + 6 digits (e.g., P190001)
- **N-numbers (De Novo)**: DEN + digits (e.g., DEN200001)

## Validation Process

### Step 1: Parse Input Numbers

Parse all device numbers from `$ARGUMENTS`. Handle comma-separated, space-separated, or mixed input.

### Step 2: Primary Validation — FDA Database Files

FDA database files may be in multiple locations. Check these in order:

1. `/mnt/c/510k/Python/PredicateExtraction/` (legacy location)
2. `/mnt/c/510k/Python/510kBF/fda_data/` (BatchFetch data-dir)
3. `$CLAUDE_PLUGIN_ROOT/scripts/` (if --data-dir pointed here)

For K-numbers (510(k)):
```bash
grep -i "KNUMBER" /mnt/c/510k/Python/PredicateExtraction/pmn*.txt /mnt/c/510k/Python/510kBF/fda_data/pmn*.txt 2>/dev/null
```

For P-numbers (PMA):
```bash
grep -i "PNUMBER" /mnt/c/510k/Python/PredicateExtraction/pma*.txt /mnt/c/510k/Python/510kBF/fda_data/pma*.txt 2>/dev/null
```

Report: Found/Not Found + full database record if found.

### Step 3: Enrichment — 510kBF Metadata

If `/mnt/c/510k/Python/510kBF/510k_download.csv` exists, search it for each number:

```bash
grep -i "KNUMBER" /mnt/c/510k/Python/510kBF/510k_download.csv 2>/dev/null
```

If found, report additional metadata:
- Applicant name
- Decision date and decision code
- Product code and device type
- Review advisory committee
- Third-party review (yes/no)
- Review time
- FDA submission URL

### Step 4: Enrichment — Predicate Relationships

If `/mnt/c/510k/Python/PredicateExtraction/output.csv` exists:

```bash
grep -i "KNUMBER" /mnt/c/510k/Python/PredicateExtraction/output.csv 2>/dev/null
```

If found, report:
- Known predicates cited by this device
- Document type (Statement vs Summary)
- Product code from extraction

Also check if this device is cited AS a predicate by others:
```bash
grep -i "KNUMBER" /mnt/c/510k/Python/PredicateExtraction/output.csv 2>/dev/null
```
(Search across all columns, not just the first)

If `/mnt/c/510k/Python/510kBF/merged_data.csv` exists, also check:
```bash
grep -i "KNUMBER" /mnt/c/510k/Python/510kBF/merged_data.csv 2>/dev/null
```

### Step 5: Enrichment — PDF Text Availability

If `/mnt/c/510k/Python/PredicateExtraction/pdf_data.json` exists, check if text is cached for this device:

```bash
grep -c "KNUMBER" /mnt/c/510k/Python/PredicateExtraction/pdf_data.json 2>/dev/null
```

Report whether the PDF text is available for deeper analysis.

### Step 6: OCR Error Suggestions

If a number is NOT found in the primary database, suggest possible OCR corrections:
- O → 0 (letter O to zero)
- I → 1 (letter I to one)
- S → 5 (letter S to five)
- B → 8 (letter B to eight)

Try common corrections and check if the corrected number exists:
```bash
# Example: try replacing common OCR errors
grep -i "CORRECTED_NUMBER" /mnt/c/510k/Python/PredicateExtraction/pmn*.txt 2>/dev/null
```

## Output Format

For each number, provide a consolidated report:

**KNUMBER** — [FOUND/NOT FOUND]
- **FDA Database**: Record details or "Not found"
- **Applicant**: Company name (from 510k_download.csv)
- **Decision**: Date, decision code (from 510k_download.csv)
- **Product Code**: Code and description
- **Review Time**: Days (from 510k_download.csv)
- **Predicates**: List of cited predicates (from output.csv/merged_data.csv)
- **Cited By**: Other devices that cite this as a predicate
- **PDF Text**: Available/Not cached
- **URL**: FDA submission link (from 510k_download.csv)

If data for a field is not available (file doesn't exist), skip that field rather than reporting "N/A" for every entry.
