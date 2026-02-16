---
name: pma-intelligence
description: Generate intelligence reports for PMA devices -- clinical data extraction, supplement tracking, and predicate analysis
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--pma P170019 [--focus clinical|supplements|predicates|all] [--output FILE]"
---

# PMA Intelligence Report Generator

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

Generate comprehensive intelligence reports for PMA devices. Extracts clinical trial data, tracks supplement history, identifies comparable PMAs and related 510(k)s, and provides predicate suitability assessments.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--pma NUMBER` | PMA number to analyze | `--pma P170019` |
| `--focus AREA` | Analysis focus | `--focus clinical` |
| `--output FILE` | Save report to file | `--output report.json` |
| `--refresh` | Force refresh from API | (flag) |
| `--download-ssed` | Download SSED first | (flag) |
| `--extract-sections` | Extract sections first | (flag) |
| `--find-citing-510ks` | Find related 510(k)s | (flag) |
| `--assess-predicate CODE` | Assess as predicate for product code | `--assess-predicate NMH` |
| `--batch LIST` | Analyze multiple PMAs | `--batch P170019,P160035` |

**Focus areas:** `clinical`, `supplements`, `predicates`, `all` (default)

## Step 1: Validate Input

If no `--pma` provided, ask:

```
Which PMA would you like to analyze?

Enter a PMA number (e.g., P170019):
```

Validate the PMA number format (starts with P, followed by 6 digits, optional S+digits suffix).

## Step 2: Set Up Scripts

```bash
SCRIPT_DIR="$(dirname "$(find /home -path '*/fda-tools/scripts/pma_intelligence.py' -type f 2>/dev/null | head -1)")"
ls -la "$SCRIPT_DIR/pma_intelligence.py" "$SCRIPT_DIR/pma_data_store.py" "$SCRIPT_DIR/pma_section_extractor.py"
```

## Step 3: Pre-fetch Data (if needed)

Check if PMA data is available:

```bash
python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from pma_data_store import PMADataStore
store = PMADataStore()
pma = 'P170019'  # Replace with actual PMA

# Check API data
data = store.get_pma_data(pma)
print(f'API_DATA:{\"available\" if not data.get(\"error\") else \"missing\"}'  )

# Check sections
sections = store.get_extracted_sections(pma)
if sections:
    meta = sections.get('metadata', {})
    print(f'SECTIONS:{meta.get(\"total_sections_found\", 0)}/{meta.get(\"total_possible_sections\", 15)}')
    print(f'QUALITY:{meta.get(\"quality_score\", 0)}/100')
else:
    print('SECTIONS:none')
"
```

If sections are not available and `--download-ssed` or `--extract-sections` is set:

```bash
# Download SSED
python3 "$SCRIPT_DIR/pma_ssed_cache.py" --pma P170019

# Extract sections
python3 "$SCRIPT_DIR/pma_section_extractor.py" --pma P170019
```

If sections are not available and flags are not set, inform the user:

```
No SSED sections found for P170019. The intelligence report will be based on
API metadata only. For deeper analysis, re-run with:

  /fda-tools:pma-intelligence --pma P170019 --download-ssed --extract-sections

This will download the SSED PDF and extract 15 sections for clinical analysis.
```

## Step 4: Generate Intelligence Report

### Full Report (default or --focus all)

```bash
python3 "$SCRIPT_DIR/pma_intelligence.py" --pma P170019 --focus all
```

### Clinical Intelligence Only

```bash
python3 "$SCRIPT_DIR/pma_intelligence.py" --pma P170019 --focus clinical
```

### Supplement Analysis Only

```bash
python3 "$SCRIPT_DIR/pma_intelligence.py" --pma P170019 --focus supplements
```

### Predicate Analysis Only

```bash
python3 "$SCRIPT_DIR/pma_intelligence.py" --pma P170019 --focus predicates
```

### Find Citing 510(k)s

```bash
python3 "$SCRIPT_DIR/pma_intelligence.py" --pma P170019 --find-citing-510ks
```

### Assess as Predicate

```bash
python3 "$SCRIPT_DIR/pma_intelligence.py" --pma P170019 --assess-predicate NMH
```

## Step 5: Format and Display Results

### Intelligence Report Format

Present the report in clear, structured markdown:

```markdown
## PMA Intelligence Report: P170019

**Device:** FoundationOne CDx
**Applicant:** Foundation Medicine, Inc.
**Product Code:** NMH
**Approved:** November 30, 2017
**Advisory Committee:** Clinical Chemistry (CH)

---

### Executive Summary

* FoundationOne CDx by Foundation Medicine, Inc., approved 20171130
* Study designs: Pivotal Single-Arm Study
* Total enrollment: 3,162 patients
* 8 efficacy metrics extracted
* 29 supplements filed
* 5 labeling changes identified
* 8 comparable PMAs identified
* 15 related 510(k) clearances found
* Risk Level: LOW
* Clinical Confidence: 68%

---

### Clinical Intelligence

**Confidence:** 68%
**Text Analyzed:** 8,500 words

#### Study Designs
- Pivotal Single-Arm Study (confidence: 90%)
- Prospective Cohort Study (confidence: 80%)

#### Enrollment
- **Total Patients:** 3,162
- **Clinical Sites:** 12
- **Demographics:** Mentioned

#### Primary Endpoints
- Positive percent agreement for individual variants
- Sensitivity for companion diagnostic claims

#### Secondary Endpoints
- Negative percent agreement
- Tumor mutational burden concordance

#### Efficacy Results
- Sensitivity: 99.3%
- Specificity: 99.8%
- PPA: 94.2%
- p-value: <0.001 (significant)

#### Follow-up
- Duration: 24 months

---

### Supplement Intelligence

**Total Supplements:** 29
**Active Years:** 2017-2025

#### By Category
| Category | Count |
|----------|-------|
| New Indication | 12 |
| Labeling Change | 8 |
| Design Change | 5 |
| Manufacturing | 3 |
| Post-Approval Study | 1 |

#### Supplement Frequency
- Average: 3.6 supplements/year
- Peak: 6 supplements (2021)

#### Recent Labeling Changes
1. P170019S029 (2021-07-16): New BRCA1/2 indication
2. P170019S028 (2021-05-21): Updated warnings

---

### Comparable PMAs

| PMA | Device | Applicant | Approved |
|-----|--------|-----------|----------|
| P160035 | MSK-IMPACT | Memorial Sloan Kettering | 2017-11-15 |
| P200024 | Tempus xT | Tempus | 2020-03-15 |
| P190014 | Guardant360 CDx | Guardant Health | 2020-08-07 |

### Related 510(k) Clearances

| K-Number | Device | Applicant | Cleared |
|----------|--------|-----------|---------|
| K241001 | Gene Panel X | Company A | 2024-06-15 |
| K232050 | NGS System Y | Company B | 2023-09-22 |

---

*Generated: 2026-02-16 | Intelligence Version 1.0.0*
*Data source: openFDA API + SSED extraction*

> **Disclaimer:** This intelligence report is AI-generated from public FDA data.
> Clinical data extraction is automated and may contain inaccuracies.
> All findings must be independently verified before use in regulatory decisions.
```

## Step 6: Batch Analysis

If `--batch` is provided, analyze multiple PMAs:

```bash
for PMA in P170019 P160035 P200024; do
    echo "=== Analyzing $PMA ==="
    python3 "$SCRIPT_DIR/pma_intelligence.py" --pma "$PMA" --focus clinical --json
done
```

Produce a comparative summary across all analyzed PMAs.

## Step 7: Export Options

If `--output FILE`:

```bash
python3 "$SCRIPT_DIR/pma_intelligence.py" --pma P170019 --output /path/to/report.json --json
```

Also save a readable markdown version:

```bash
python3 "$SCRIPT_DIR/pma_intelligence.py" --pma P170019 > /path/to/report.txt
```

## Error Handling

- **PMA not found**: "PMA {number} not found in FDA database. Verify the PMA number is correct."
- **No SSED available**: "SSED document not available for {PMA}. Clinical intelligence will be limited to API metadata."
- **Extraction failed**: "Section extraction failed for {PMA}. Check if pdfplumber is installed: pip install pdfplumber"
- **API errors**: "FDA API temporarily unavailable. Using cached data where available."

## Examples

```bash
# Full intelligence report
/fda-tools:pma-intelligence --pma P170019

# Clinical data focus with SSED download
/fda-tools:pma-intelligence --pma P170019 --focus clinical --download-ssed --extract-sections

# Supplement tracking
/fda-tools:pma-intelligence --pma P170019 --focus supplements

# Find related 510(k)s
/fda-tools:pma-intelligence --pma P170019 --find-citing-510ks

# Assess as predicate
/fda-tools:pma-intelligence --pma P170019 --assess-predicate NMH

# Batch analysis
/fda-tools:pma-intelligence --batch P170019,P160035,P200024

# Save JSON report
/fda-tools:pma-intelligence --pma P170019 --output ~/reports/P170019_intelligence.json
```

## Clinical Data Extraction Details

The intelligence engine extracts the following from SSED sections:

### Study Designs Detected
- Pivotal RCT
- Pivotal Single-Arm
- Randomized Controlled Trial
- Single-Arm Study
- Registry Study
- Prospective Cohort
- Retrospective Study
- Feasibility/Pilot
- Post-Approval Study
- Meta-Analysis
- Bayesian Adaptive
- Non-Inferiority
- Sham-Controlled
- Double-Blind

### Extracted Metrics
- Enrollment (total patients, sites, demographics)
- Primary/secondary/safety endpoints
- Success rates, efficacy rates, survival rates
- P-values and statistical significance
- Confidence intervals
- Sensitivity, specificity, PPA, NPA
- Adverse event rates and types
- Follow-up duration

### Confidence Scoring
Each extraction includes a confidence score (0-100%):
- **>80%**: High confidence -- clear pattern match
- **60-80%**: Moderate confidence -- likely correct but verify
- **<60%**: Low confidence -- manual verification recommended
