---
name: pma-compare
description: Compare PMAs for clinical, device, and safety similarities with weighted scoring
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--primary P170019 --comparators P160035,P150009 [--focus clinical|device|safety|all] [--competitive --product-code NMH]"
---

# PMA Comparison Command

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

Compare PMA (Premarket Approval) devices across multiple dimensions: indications, clinical data, device specifications, safety profiles, and regulatory history. Produces structured comparison matrices with weighted similarity scores.

## Arguments

Parse the user's arguments to determine comparison mode:

| Flag | Description | Example |
|------|-------------|---------|
| `--primary PMA` | Primary PMA for comparison | `--primary P170019` |
| `--comparators LIST` | Comma-separated comparator PMAs | `--comparators P160035,P150009` |
| `--focus AREA` | Focus area(s) to compare | `--focus clinical,device` |
| `--product-code CODE` | Product code for competitive analysis | `--product-code NMH` |
| `--competitive` | Run competitive analysis mode | (flag) |
| `--output FILE` | Save results to file | `--output comparison.json` |
| `--refresh` | Force refresh from API | (flag) |
| `--download-ssed` | Download SSEDs before comparing | (flag) |
| `--extract-sections` | Extract sections before comparing | (flag) |

**Focus areas:** `indications`, `clinical_data`, `device_specs`, `safety_profile`, `regulatory_history`, `all` (default)

## Step 1: Determine Comparison Mode

Based on arguments, determine which workflow:

1. **Pairwise Comparison** (`--primary` + `--comparators`): Compare one PMA against others
2. **Competitive Analysis** (`--product-code` + `--competitive`): Compare all PMAs in a space
3. **Predicate Assessment** (`--primary` + `--assess-predicate`): Evaluate PMA as predicate

If neither `--primary` nor `--product-code` is provided, ask the user:

```
What would you like to compare?

1. Compare specific PMAs (provide P-numbers)
2. Competitive analysis for a product code
3. Assess a PMA as predicate for a 510(k) device

Enter your choice or provide PMA numbers:
```

## Step 2: Set Up Scripts

```bash
# Determine script directory
SCRIPT_DIR="$(dirname "$(find /home -path '*/fda-tools/scripts/pma_comparison.py' -type f 2>/dev/null | head -1)")"

# Verify scripts exist
ls -la "$SCRIPT_DIR/pma_comparison.py" "$SCRIPT_DIR/pma_intelligence.py" "$SCRIPT_DIR/pma_data_store.py" "$SCRIPT_DIR/pma_section_extractor.py"
```

## Step 3: Pre-fetch Data (if needed)

If `--download-ssed` flag is present, download SSED PDFs for all PMAs:

```bash
ALL_PMAS="P170019,P160035,P150009"  # Replace with actual PMAs
python3 "$SCRIPT_DIR/pma_ssed_cache.py" --list "$ALL_PMAS" --rate-limit 0.5
```

If `--extract-sections` flag is present, extract sections from SSEDs:

```bash
python3 "$SCRIPT_DIR/pma_section_extractor.py" --batch "$ALL_PMAS"
```

## Step 4: Execute Comparison

### Mode 1: Pairwise Comparison

```bash
python3 "$SCRIPT_DIR/pma_comparison.py" \
    --primary P170019 \
    --comparators P160035,P150009 \
    --focus all
```

Parse the output and format as a structured comparison report.

### Mode 2: Competitive Analysis

```bash
python3 "$SCRIPT_DIR/pma_comparison.py" \
    --product-code NMH \
    --competitive \
    --json
```

### Mode 3: Predicate Assessment

```bash
python3 "$SCRIPT_DIR/pma_intelligence.py" \
    --pma P170019 \
    --assess-predicate PRODUCT_CODE \
    --json
```

## Step 5: Format Results

### Pairwise Comparison Output

Present results as a structured markdown report:

```markdown
## PMA Comparison Report

**Primary PMA:** P170019 - FoundationOne CDx (Foundation Medicine, Inc.)
**Comparators:** P160035 - MSK-IMPACT (Memorial Sloan Kettering)
**Comparison Date:** 2026-02-16
**Overall Similarity:** 72.5/100 (MODERATE)

### Dimension Scores

| Dimension | Score | Data Quality | Key Finding |
|-----------|-------|-------------|-------------|
| Indications | 85.2/100 | Full | Both target tumor profiling |
| Clinical Data | 68.3/100 | Full | Similar study designs, different enrollment |
| Device Specs | 71.0/100 | Full | Both NGS-based, different platforms |
| Safety Profile | 62.5/100 | Full | Similar risk profiles |
| Regulatory History | 78.0/100 | Full | Same product code and committee |

### Key Differences

1. **[NOTABLE] Clinical Data** (68.3/100): Different enrollment sizes (3,162 vs 1,850 patients)
2. **[NOTABLE] Safety Profile** (62.5/100): Different adverse event categorization approaches

### Regulatory Implications

- **Strong Comparator**: P160035 shows moderate-to-high similarity (72.5/100). Useful as reference for regulatory strategy.
- **Same Product Code**: Both are NMH, suggesting same device category and review pathway.

### PMA Summaries

| Field | P170019 (Primary) | P160035 (Comparator) |
|-------|-------------------|---------------------|
| Device Name | FoundationOne CDx | MSK-IMPACT |
| Applicant | Foundation Medicine | Memorial Sloan Kettering |
| Product Code | NMH | NMH |
| Approval Date | 2017-11-30 | 2017-11-15 |
| Supplements | 29 | 12 |
| Sections Extracted | 12/15 | 10/15 |
```

### Competitive Analysis Output

```markdown
## PMA Competitive Intelligence: Product Code NMH

**Product Code:** NMH - Next Generation Sequencing
**PMAs Analyzed:** 8
**Analysis Date:** 2026-02-16

### Market Landscape

| Applicant | PMAs | Most Recent |
|-----------|------|-------------|
| Foundation Medicine | 3 | P240001 (2024) |
| Roche | 2 | P220015 (2022) |
| Memorial Sloan Kettering | 1 | P160035 (2017) |

### Most Similar Pairs

| Pair | Similarity | Notes |
|------|-----------|-------|
| P170019 vs P160035 | 78.5 | Both comprehensive tumor profiling |
| P170019 vs P220015 | 65.2 | Same applicant group |

### Approval Timeline

```
2016 |*
2017 |***
2018 |*
2019 |
2020 |*
2021 |**
2022 |*
2024 |*
```

## Step 6: Data Enrichment

After the primary comparison, check if clinical intelligence would add value:

```bash
# For each PMA in the comparison, check if intelligence report exists
python3 -c "
import sys, json
sys.path.insert(0, '$SCRIPT_DIR')
from pma_data_store import PMADataStore
store = PMADataStore()
for pma in ['P170019', 'P160035']:
    pma_dir = store.get_pma_dir(pma)
    report_path = pma_dir / 'intelligence_report.json'
    if report_path.exists():
        with open(report_path) as f:
            report = json.load(f)
        clinical = report.get('clinical_intelligence', {})
        print(f'{pma}:INTELLIGENCE_EXISTS:{clinical.get(\"has_clinical_data\", False)}')
    else:
        print(f'{pma}:NO_INTELLIGENCE')
"
```

If no intelligence exists and sections are available, suggest:

```
Clinical intelligence reports are not yet generated for these PMAs.
Would you like to generate them for deeper analysis? This will extract:
- Study designs and enrollment data
- Primary and secondary endpoints
- Efficacy results and p-values
- Adverse event profiles

This takes ~10-30 seconds per PMA.
```

## Step 7: Export Options

If `--output FILE` specified, save the comparison result:

```bash
python3 "$SCRIPT_DIR/pma_comparison.py" \
    --primary P170019 \
    --comparators P160035 \
    --output /path/to/comparison.json \
    --json
```

Also offer to save as markdown:

```bash
# Save formatted report
cat << 'EOF' > /path/to/comparison_report.md
{FORMATTED COMPARISON REPORT}
EOF
```

## Error Handling

- **PMA not found**: "PMA {number} not found in FDA database. Verify the PMA number."
- **No SSED data**: "No SSED sections extracted for {PMA}. Run with --download-ssed --extract-sections first."
- **API errors**: "FDA API temporarily unavailable. Using cached data where available."
- **Low data quality**: Note when comparison is based on metadata only vs full SSED text.

## Examples

```bash
# Compare two PMAs
/fda-tools:pma-compare --primary P170019 --comparators P160035

# Compare with focus on clinical data
/fda-tools:pma-compare --primary P170019 --comparators P160035 --focus clinical_data

# Competitive analysis for a product code
/fda-tools:pma-compare --product-code NMH --competitive

# Full pipeline: download, extract, compare
/fda-tools:pma-compare --primary P170019 --comparators P160035 --download-ssed --extract-sections

# Multiple comparators
/fda-tools:pma-compare --primary P170019 --comparators P160035,P150009,P200024
```

## Dimension Weights

The comparison uses weighted scoring:

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Indications for Use | 30% | Most critical for regulatory pathway alignment |
| Clinical Data | 25% | Study design and evidence strength |
| Device Specifications | 20% | Technology and materials similarity |
| Safety Profile | 15% | Risk profile alignment |
| Regulatory History | 10% | Pathway and review context |

## Similarity Levels

| Score Range | Level | Interpretation |
|-------------|-------|---------------|
| 75-100 | HIGH | Highly similar -- strong reference |
| 50-74 | MODERATE | Moderately similar -- useful reference |
| 25-49 | LOW | Some overlap -- limited applicability |
| 0-24 | MINIMAL | Minimal similarity -- not recommended |
