---
description: Compare 510(k) sections across devices for regulatory intelligence
allowed-tools: [Bash, Read, AskUserQuestion]
argument-hint: "--product-code CODE --sections TYPES [--product-codes CODES] [--similarity] [--trends] [--years RANGE] [--limit N] [--csv]"
---

# FDA 510(k) Section Comparison Tool

You are helping the user analyze and compare specific sections (clinical data, biocompatibility, performance testing, etc.) across all 510(k) summaries for a product code. This provides competitive intelligence and regulatory strategy insights.

## Core Functionality

**Purpose:** Batch section comparison tool for regulatory intelligence - compare how peers structure sections, identify common patterns, detect outliers, and benchmark standards usage.

**Integration:** Uses `compare_sections.py` which processes structured cache data from `build_structured_cache.py` extraction pipeline.

**Output:** Markdown report + optional CSV export with coverage matrix, standards analysis, outlier detection, text similarity, temporal trends, and cross-product comparison.

## Arguments

Parse user arguments to determine the comparison parameters:

- `--product-code CODE`: FDA product code (e.g., DQY, OVE, GEI). Required unless `--product-codes` is used.
- `--product-codes CODES`: Multiple product codes for cross-comparison (e.g., `DQY,OVE,GEI`). Enables cross-product comparison mode. The first code is used as the primary for single-code analysis.
- `--sections TYPES`: **(Required)** Comma-separated section types or "all"
  - Examples: `clinical,biocompatibility`, `performance,sterilization`, `all`
- `--similarity`: Compute pairwise text similarity for each section type. Adds Section 5 to the report.
- `--similarity-method METHOD`: Similarity computation method. Options: `sequence` (difflib), `jaccard` (word sets), `cosine` (TF vectors). Default: `cosine`.
- `--similarity-sample N`: Max devices for similarity matrix (default: 30). Limits pairwise computation for performance.
- `--trends`: Analyze year-over-year temporal trends. Adds Section 6 to the report.
- `--years RANGE`: Filter by decision year (e.g., `2024`, `2020-2025`)
- `--limit N`: Limit analysis to N most recent devices
- `--csv`: Generate CSV export in addition to markdown report
- `--output FILE`: Custom output path (default: auto-generated timestamp)

**Default behavior** (no optional args): Analyze all devices for product code across all years.

**Auto-build behavior:** If no structured cache exists but extraction cache files are available, the tool will automatically run `build_structured_cache.py` before proceeding.

## Section Types Reference

### Common Aliases (user-friendly → canonical)

Users may use friendly names - map to canonical section types:

- `clinical` → `clinical_testing`
- `biocompat`, `biocompatibility` → `biocompatibility`
- `performance` → `performance_testing`
- `predicate`, `se`, `substantial_equivalence` → `predicate_se`
- `device_desc`, `description` → `device_description`
- `indications`, `ifu` → `indications_for_use`
- `sterilization` → `sterilization`
- `shelf_life` → `shelf_life`
- `software` → `software`
- `electrical` → `electrical_safety`
- `human_factors`, `hf` → `human_factors`
- `risk` → `risk_management`
- `labeling` → `labeling`
- `all` → analyze all 40+ section types

### Full Section Type List

Available section types (from `SECTION_PATTERNS` in build_structured_cache.py):

**Core Sections:**
- `predicate_se`, `indications_for_use`, `device_description`, `performance_testing`
- `biocompatibility`, `sterilization`, `clinical_testing`, `shelf_life`

**Safety & Testing:**
- `electrical_safety`, `human_factors`, `risk_management`, `software`
- `mechanical_testing`, `functional_testing`, `environmental_testing`

**Advanced:**
- `regulatory_history`, `reprocessing`, `packaging`, `materials`
- `accelerated_aging`, `antimicrobial`, `emc_detailed`, `mri_safety`
- `animal_testing`, `literature_review`, `manufacturing`, `special_510k`

## Command Workflow

### Step 1: Validate Prerequisites

**Check 1:** Verify structured cache exists
```bash
ls ~/fda-510k-data/extraction/structured_text_cache/*.json | wc -l
```

If zero files:
```
❌ No structured cache found!

You need to run extraction first:
  /fda-tools:extract --product-code <CODE> --years 2024

This will download PDFs and build the structured cache.
```

**Check 2:** Verify product code has data
```bash
python3 plugins/fda-tools/scripts/compare_sections.py --product-code <CODE> --sections all --quiet
```

If fails with "No devices found":
```
❌ No devices found for product code <CODE>

Either:
1. The product code hasn't been extracted yet
2. The product code is invalid

Run /fda-tools:extract first to download and extract data.
```

### Step 2: Parse and Validate Arguments

**Parse sections argument:**
- If user says "all" → use all section types
- If user provides list → map aliases to canonical names
- Validate each section type exists in `SECTION_PATTERNS`

**Example validation:**
```
User input: --sections clinical,biocompat,performance

Validated sections:
  ✓ clinical → clinical_testing
  ✓ biocompat → biocompatibility
  ✓ performance → performance_testing

Will analyze 3 section types across devices.
```

### Step 3: Preview Scope (if no --limit specified)

Before running full analysis, show user the scope:

```bash
# Count devices that will be analyzed
python3 plugins/fda-tools/scripts/compare_sections.py \
  --product-code <CODE> \
  --sections <SECTIONS> \
  [--years <RANGE>] \
  --quiet
```

Parse JSON output and present to user:
```
📊 Analysis Scope Preview:

Product Code: DQY
Devices Found: 147
Year Range: All years
Sections: clinical_testing, biocompatibility, performance_testing

This analysis will process 147 devices. This may take 1-2 minutes.
```

**Ask user if scope is reasonable via AskUserQuestion:**

If >100 devices, suggest using `--limit` or `--years` filter:
```json
{
  "questions": [
    {
      "question": "Analyze all 147 devices or filter the scope?",
      "header": "Scope",
      "multiSelect": false,
      "options": [
        {
          "label": "Analyze all (recommended)",
          "description": "Process all 147 devices for comprehensive analysis"
        },
        {
          "label": "Recent only (limit 50)",
          "description": "Analyze 50 most recent devices for faster results"
        },
        {
          "label": "Recent years (2020-2025)",
          "description": "Filter by year range for recent submissions"
        },
        {
          "label": "Custom filter",
          "description": "Specify custom --years or --limit"
        }
      ]
    }
  ]
}
```

Based on user selection:
- "All" → proceed with full analysis
- "Recent only" → add `--limit 50`
- "Recent years" → add `--years 2020-2025`
- "Custom" → ask user for specific filters

### Step 4: Execute Analysis

Run the comparison script:
```bash
python3 plugins/fda-tools/scripts/compare_sections.py \
  --product-code <CODE> \
  --sections <SECTIONS> \
  [--years <RANGE>] \
  [--limit <N>] \
  [--csv]
```

**Show progress:**
```
🔄 Running Section Comparison Analysis...

📂 Loading structured cache...
🔍 Filtering by product code: DQY
✅ Processing 147 devices...
📝 Analyzing 3 section types...
📊 Generating coverage matrix...
🔬 Analyzing standards frequency...
🎯 Detecting outliers...
📄 Writing markdown report...
```

### Step 5: Present Results

Parse script output and present key findings:

```
✅ Analysis Complete!

📊 Summary:
  - Devices analyzed: 147
  - Sections analyzed: 3 (clinical_testing, biocompatibility, performance_testing)
  - Standards identified: 45 unique citations
  - Outliers detected: 12 unusual section lengths

📄 Report: ~/fda-510k-data/projects/section_comparison_DQY_20260215_143022/DQY_comparison.md
💾 CSV: ~/fda-510k-data/projects/section_comparison_DQY_20260215_143022/DQY_comparison.csv

Key Findings:
✓ clinical_testing: 98.6% coverage (145/147 devices)
✓ biocompatibility: 100.0% coverage (147/147 devices)
⚠️  performance_testing: 67.3% coverage (99/147 devices)

Top Standards:
  1. ISO10993-1: 98.0% of devices (biocompatibility)
  2. ISO10993-5: 95.2% of devices (cytotoxicity)
  3. IEC60601-1: 87.1% of devices (electrical safety)
```

**Ask user if they want to view the report:**
```json
{
  "questions": [
    {
      "question": "View the comparison report?",
      "header": "Next Step",
      "multiSelect": false,
      "options": [
        {
          "label": "View key findings",
          "description": "Display coverage matrix and top standards"
        },
        {
          "label": "View full report",
          "description": "Read complete markdown report"
        },
        {
          "label": "Done",
          "description": "Report saved, no need to view now"
        }
      ]
    }
  ]
}
```

If user selects "View key findings", read the report and extract:
- Section 1 (Coverage Matrix table)
- Section 2 (Top 10 standards table)
- Section 3 (Key findings bullet points)

If user selects "View full report", read and display complete report.

## Output File Structure

### Markdown Report Contents

1. **Header** - Product code, analysis date, device count
2. **Section 1: Coverage Matrix** - Which devices have which sections (table)
3. **Section 2: Standards Frequency** - Most cited standards (overall + by section)
4. **Section 3: Key Findings** - Low coverage sections, ubiquitous standards
5. **Section 4: Outliers** - Devices with unusual section lengths (Z-score > 2)
6. **Section 5: Text Similarity** - (if `--similarity` flag used) Pairwise similarity statistics, most/least similar pairs, interpretation
7. **Section 6: Temporal Trends** - (if `--trends` flag used) Year-over-year coverage and section length trends with direction
8. **Section 7: Cross-Product Comparison** - (if `--product-codes` with multiple codes) Side-by-side comparison of coverage, section lengths, and top standards across product codes

### CSV Export Contents

Structured data for further analysis:
- Columns: k_number, device_name, decision_date, product_code
- `has_<section_type>`: Binary flags (1/0)
- `<section_type>_words`: Word counts
- `<section_type>_standards`: Semicolon-separated standards list

**Example CSV row:**
```csv
K241234,Acme Catheter,2024-05-15,DQY,1,1,0,450,890,0,ISO10993-1; ISO10993-5,IEC60601-1,
```

## Use Cases & Examples

### Use Case 1: Clinical Data Benchmarking

User wants to see if clinical data is typically included for cardiovascular catheters:

```
User: /fda-tools:compare-sections --product-code DQY --sections clinical

Your workflow:
1. Check cache exists
2. Run: --product-code DQY --sections clinical_testing
3. Present findings:
   "Clinical testing coverage: 98.6% (145/147 devices)
    → Clinical data is nearly universal for DQY catheters
    → Only 2 devices lack clinical sections (K190123, K180456)"
```

**Regulatory insight:** User learns clinical data is expected by FDA for this device type.

### Use Case 2: Biocompatibility Testing Standards

User wants to know which ISO 10993 parts are most common:

```
User: /fda-tools:compare-sections --product-code DQY --sections biocompatibility --csv

Your workflow:
1. Run analysis with CSV export
2. Extract biocompat standards frequency
3. Present top 10:
   "ISO10993-1 (biocompatibility framework): 98.0%
    ISO10993-5 (cytotoxicity): 95.2%
    ISO10993-10 (irritation/sensitization): 87.8%
    ISO10993-11 (systemic toxicity): 82.3%"
```

**Regulatory insight:** User identifies which tests are industry standard.

### Use Case 3: Performance Testing Gaps

User suspects performance testing varies widely for orthopedic implants:

```
User: /fda-tools:compare-sections --product-code OVE --sections performance

Your workflow:
1. Run analysis
2. Identify outliers (Z-score analysis)
3. Report:
   "Performance testing coverage: 67.3% (only 2/3 devices)

    Outliers:
    - K230145: 45 words (unusually short, -2.3σ)
    - K220789: 3,450 words (unusually long, +3.1σ)

    → High variability suggests no standard approach"
```

**Regulatory insight:** User learns submission strategy varies - opportunity for competitive advantage.

### Use Case 4: Multi-Section Strategy Analysis

User preparing 510(k) wants to see typical section structure:

```
User: /fda-tools:compare-sections --product-code DQY --sections clinical,biocompat,performance,sterilization,shelf_life --years 2022-2025

Your workflow:
1. Filter to recent submissions
2. Run multi-section analysis
3. Generate coverage matrix:
   "Recent DQY Catheters (2022-2025): 42 devices

    Section Coverage:
    biocompatibility: 100% (universal)
    clinical_testing: 97.6% (nearly universal)
    sterilization: 95.2% (very common)
    performance_testing: 71.4% (common)
    shelf_life: 33.3% (optional)

    → Your submission should include: biocompat, clinical, sterilization, performance
    → Shelf life is optional (only if device has expiration)"
```

**Regulatory insight:** User learns which sections are mandatory vs optional.

### Use Case 5: Cross-Product Code Comparison

User wants to compare how cardiovascular catheters (DQY) differ from orthopedic implants (OVE) in their section structure:

```
User: /fda-tools:compare-sections --product-codes DQY,OVE --sections clinical,biocompat,performance,sterilization

Your workflow:
1. Load full structured cache
2. Run cross-product comparison for both codes
3. Present side-by-side table:
   "Cross-Product Comparison:

    Section           | DQY (147 devices)  | OVE (89 devices)
    clinical_testing  | 98.6% coverage     | 45.2% coverage
    biocompatibility  | 100.0% coverage    | 98.9% coverage
    performance       | 67.3% coverage     | 92.1% coverage
    sterilization     | 95.2% coverage     | 82.0% coverage

    Key insight: Clinical data is nearly universal for catheters
    but much less common for orthopedic implants."
```

**Regulatory insight:** User understands how submission expectations differ by device type.

### Use Case 6: Text Similarity Analysis

User wants to know if biocompatibility sections are formulaic or highly variable:

```
User: /fda-tools:compare-sections --product-code DQY --sections biocompatibility --similarity

Your workflow:
1. Run similarity analysis with cosine method
2. Present statistics:
   "Biocompatibility Section Similarity (DQY):
    - Method: cosine
    - Pairs computed: 10,731 (from 147 devices)
    - Mean similarity: 0.823 (HIGH)
    - Std deviation: 0.098
    - Most similar: K241001 & K241002 (0.97)
    - Least similar: K190034 & K241099 (0.41)

    Interpretation: HIGH similarity -- sections follow consistent
    structure. Your submission should align with the established pattern."
```

**Regulatory insight:** High similarity means there is a clear template/expectation.

### Use Case 7: Temporal Trend Analysis

User preparing a 2026 submission wants to see if clinical data requirements are increasing:

```
User: /fda-tools:compare-sections --product-code DQY --sections clinical --trends --years 2018-2025

Your workflow:
1. Run temporal trend analysis
2. Present year-by-year data:
   "Clinical Testing Trends for DQY (2018-2025):

    Year | Devices | Coverage | Avg Words | Standards
    2018 | 12      | 83.3%    | 320       | 4
    2019 | 15      | 86.7%    | 355       | 5
    2020 | 18      | 88.9%    | 410       | 6
    2021 | 20      | 95.0%    | 490       | 7
    2022 | 22      | 95.5%    | 550       | 8
    2023 | 25      | 96.0%    | 610       | 9
    2024 | 28      | 100.0%   | 680       | 10
    2025 | 10      | 100.0%   | 720       | 11

    Coverage trend: INCREASING (R2=0.92, slope=2.1%/year)
    Section length trend: INCREASING (R2=0.98, slope=55 words/year)

    Interpretation: FDA expectations for clinical data are clearly
    growing. Plan for more comprehensive clinical sections."
```

**Regulatory insight:** User can see that clinical data sections are getting longer and more common over time, informing their submission strategy.

### Use Case 8: Combined Advanced Analysis

User wants the complete picture for a competitive analysis:

```
User: /fda-tools:compare-sections --product-codes DQY,OVE,GEI --sections all --similarity --trends --years 2020-2025 --csv

Your workflow:
1. Run full analysis with all advanced features enabled
2. Generate comprehensive report with all 7+ sections
3. Present executive summary covering coverage, similarity, trends, and cross-product insights
```

## Error Handling

### Scenario: No Structured Cache

```
❌ Error: No structured cache found

The section comparison tool requires extracted PDF text.

Run extraction first:
  /fda-tools:extract --product-code DQY --years 2024

This will:
1. Download 510(k) summary PDFs
2. Extract text and structure by sections
3. Build structured cache for analysis
```

### Scenario: Product Code Not Found

```
❌ Error: No devices found for product code XYZ

Possible causes:
1. Product code is invalid (typo?)
2. Product code exists but hasn't been extracted yet

Check valid product codes:
  /fda-tools:validate --product-code XYZ

If valid, run extraction:
  /fda-tools:extract --product-code XYZ --years 2024
```

### Scenario: Invalid Section Type

```
⚠️  Warning: Unknown section type 'clincal' (typo?), skipping

Did you mean:
  - clinical (→ clinical_testing)
  - clinical_testing

Available sections: clinical, biocompat, performance, sterilization, ...
Use --sections all to analyze all section types.
```

### Scenario: Sparse Section Data

```
✅ Analysis complete, but limited data found:

Sections analyzed: clinical_testing
Devices with clinical sections: 12/147 (8.2%)

⚠️  Only 8.2% of devices have clinical sections - results may not be representative.

Recommendation:
- Try --sections all to find which sections ARE common
- DQY devices may not typically include clinical data
```

## Performance Notes

**Processing Speed:**
- ~100 devices: 10-15 seconds
- ~500 devices: 30-45 seconds
- ~1000 devices: 60-90 seconds

**Bottlenecks:**
- Loading structured cache (one-time per command)
- Standards extraction (regex matching across all text)
- Z-score outlier calculation (statistical analysis)
- Similarity matrix (O(n^2) pairwise comparisons -- use `--similarity-sample` for large datasets)

**Similarity Performance:**
- 30 devices (default sample): ~5 seconds (435 pairs)
- 50 devices: ~15 seconds (1,225 pairs)
- 100 devices: ~60 seconds (4,950 pairs)
- Use `--similarity-sample 30` to cap computation time

**Optimization Tips:**
- Use `--limit` for exploratory analysis (e.g., `--limit 50`)
- Use `--years` filter for recent submissions
- Use `--similarity-sample 20` for quick similarity checks
- Cache is pre-structured, so multiple section comparisons are fast
- Auto-build runs automatically if structured cache is missing but extraction cache exists

## Integration Notes

**Script Location:** `plugins/fda-tools/scripts/compare_sections.py`

**Dependencies:**
- Reads from: `~/fda-510k-data/extraction/structured_text_cache/*.json`
- Imports: `build_structured_cache.py` (for `SECTION_PATTERNS`)
- Imports: `section_analytics.py` (for `compute_similarity`, `pairwise_similarity_matrix`, `analyze_temporal_trends`, `cross_product_compare`)
- Writes to: `~/fda-510k-data/projects/section_comparison_<CODE>_<TIMESTAMP>/`
- Auto-invokes: `build_structured_cache.py` if structured cache is empty (subprocess)

**Structured Cache Format:**
```json
{
  "k_number": "K241234",
  "device_name": "Acme Catheter",
  "product_code": "DQY",
  "decision_date": "2024-05-15",
  "sections": {
    "clinical_testing": {
      "text": "...",
      "word_count": 450,
      "confidence": 0.95
    },
    "biocompatibility": {
      "text": "...",
      "word_count": 890,
      "confidence": 0.98
    }
  }
}
```

## Regulatory Intelligence Value

**For Regulatory Professionals:**

1. **Competitive Benchmarking:**
   - See how peers structure submissions
   - Identify industry norms for section inclusion
   - Detect gaps in competitor submissions

2. **Standards Roadmap:**
   - Learn which ISO/IEC/ASTM standards are expected
   - Prioritize testing based on >95% citation rate
   - Estimate budget (typically $10K-$30K per standard)

3. **Risk Mitigation:**
   - Avoid submitting unusual/outlier approaches
   - Align with FDA reviewer expectations (based on peer precedent)
   - Identify "optional" vs "mandatory" sections by coverage %

4. **Strategic Positioning:**
   - Find opportunities for competitive advantage (areas with low coverage)
   - Justify testing scope with peer comparison data
   - Build defensible predicate comparison arguments

## Example User Sessions

### Session 1: Quick Clinical Data Check

```
User: Compare clinical sections for DQY catheters