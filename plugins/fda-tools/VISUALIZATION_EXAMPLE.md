# Trend Visualization Examples (FE-007)

This document showcases real-world examples of the trend visualization feature.

## Example 1: Increasing Coverage Trend

**Scenario:** Clinical testing section coverage increased from 60% to 90% over 5 years.

### ASCII Chart Output (Markdown)

```
### clinical_testing Trends

```

   90% │                                              ·▓▓▓█
       │                                          ··▓▓▓
       │                                      ···▓▓▓
       │                                  ···░▓▓▓
       │                              ···· ▓▓█
       │                          ····  ▓▓▓
   75% │                     ····░   ▓▓▓
       │                 ····     ▓▓▓
       │         ▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓█
       │     ▓▓▓▓···░
       │ ▓▓▓▓··
   60% │█
       └──────────────────────────────────────────────────
        2020        2021         2022        2023
```

Legend: █ Coverage %  ·· Avg Word Count

**Significant Changes (>5%):**

- ↗ Coverage: 2020-2021: 60.0% → 70.0% (+16.7%)
- ↗ Coverage: 2022-2023: 70.0% → 80.0% (+14.3%)
- ↗ Coverage: 2023-2024: 80.0% → 90.0% (+12.5%)
- ↗ Length: 2020-2021: 200 → 250 words (+25.0%)
- ↗ Length: 2021-2022: 250 → 300 words (+20.0%)
- ↗ Length: 2022-2023: 300 → 350 words (+16.7%)
- ↗ Length: 2023-2024: 350 → 400 words (+14.3%)
```

### Trend Table

| Year | Coverage % | Avg Words | Change |
|------|------------|-----------|--------|
| 2020 | 60.0% | 200 | - |
| 2021 | 70.0% | 250 | ↗ Cov +17%, ↗ Len +25% |
| 2022 | 70.0% | 300 | ↗ Len +20% |
| 2023 | 80.0% | 350 | ↗ Cov +14%, ↗ Len +17% |
| 2024 | 90.0% | 400 | ↗ Cov +13%, ↗ Len +14% |

### Interpretation

**Regulatory Insight:**
- Clinical testing sections are becoming **more prevalent** (+50% increase in coverage)
- Sections are becoming **more detailed** (+100% increase in word count)
- Change is **consistent and sustained** (every year shows growth)
- **Recommendation:** Follow the trend - include comprehensive clinical testing data

---

## Example 2: Decreasing Biocompatibility Coverage

**Scenario:** Biocompatibility section coverage decreased from 90% to 50% over 5 years.

### ASCII Chart Output

```
### biocompatibility Trends

```
   90% │█▓▓▓
       │    ▓▓▓··
       │       ▓▓▓ ··
       │          ▓▓▓ ·
   75% │             ▓▓▓··
       │                ▓▓▓ ·
       │                   ▓▓▓··
       │                      ▓▓▓ ·
   60% │                         ▓▓▓··
       │                            ▓▓▓ ·
       │                               ▓▓▓··
   50% │                                  ▓▓▓█
       └──────────────────────────────────────────────────
        2020        2021         2022        2023
```

Legend: █ Coverage %  ·· Avg Word Count

**Significant Changes (>5%):**

- ↘ Coverage: 2020-2021: 90.0% → 80.0% (-11.1%)
- ↘ Coverage: 2021-2022: 80.0% → 70.0% (-12.5%)
- ↘ Coverage: 2022-2023: 70.0% → 60.0% (-14.3%)
- ↘ Coverage: 2023-2024: 60.0% → 50.0% (-16.7%)
- ↘ Length: 2020-2021: 500 → 425 words (-15.0%)
- ↘ Length: 2021-2022: 425 → 350 words (-17.6%)
- ↘ Length: 2022-2023: 350 → 275 words (-21.4%)
- ↘ Length: 2023-2024: 275 → 200 words (-27.3%)
```

### Interpretation

**Regulatory Insight:**
- Biocompatibility sections are becoming **less common** (-44% decline)
- Remaining sections are becoming **more concise** (-60% word count reduction)
- **Possible reasons:**
  - More devices using established materials (ISO 10993 consensus)
  - Increased use of predicate data references
  - Shift to tabular formats vs. narrative
- **Recommendation:** Check if your device uses novel materials before omitting biocompatibility data

---

## Example 3: Stable Performance Testing

**Scenario:** Performance testing coverage stable at ~80% over 5 years.

### ASCII Chart Output

```
### performance_testing Trends

```
   85% │
       │    ██
       │   █  █      ██
   80% │  █    █    █  █      ██
       │ █      ████    █    █  █
       │█                 ████    ██
   75% │                              █
       └──────────────────────────────────────────────────
        2020        2021         2022        2023
```

Legend: █ Coverage %  ·· Avg Word Count

**Significant Changes (>5%):**
*(None detected - all year-over-year changes < 5%)*
```

### Interpretation

**Regulatory Insight:**
- Performance testing coverage is **stable and consistent** (~80%)
- This is a **well-established practice** across the product code
- **Recommendation:** Include performance testing to align with peer submissions

---

## Example 4: Single Year Data (Fallback Behavior)

**Scenario:** Only 2024 data available (no trend analysis possible).

### ASCII Chart Output

```
### clinical_testing Trends

Year: 2024
Coverage: 80.0%
Avg Length: 300 words
```

### Interpretation

**Regulatory Insight:**
- Temporal trend analysis requires ≥2 years of data
- Current snapshot: 80% of devices include clinical testing (300 words average)
- **Recommendation:** Expand year range (`--years 2020-2024`) for trend analysis

---

## Command Examples

### Generate Markdown Report with ASCII Charts

```bash
python3 compare_sections.py \
    --product-code DQY \
    --sections clinical,biocompat,performance \
    --years 2020-2024 \
    --trends \
    --output dqy_trends.md
```

**Output:**
- `dqy_trends.md` - Markdown report with ASCII charts embedded

### Generate HTML Report with SVG Charts

```bash
python3 compare_sections.py \
    --product-code DQY \
    --sections clinical,biocompat \
    --trends \
    --html
```

**Output:**
- `DQY_comparison.md` - Markdown with ASCII charts
- `DQY_comparison.html` - HTML with interactive SVG charts

### Multi-Product Comparison with Trends

```bash
python3 compare_sections.py \
    --product-codes DQY,OVE,GEI \
    --sections all \
    --trends \
    --html \
    --csv
```

**Output:**
- Markdown report with ASCII charts for each section
- HTML report with SVG charts
- CSV export with raw data

---

## Python API Examples

### Example 1: Generate ASCII Chart

```python
from section_analytics import analyze_temporal_trends
from trend_visualization import generate_ascii_chart

# Analyze trends
trends = analyze_temporal_trends(section_data, ['clinical_testing'])

# Generate ASCII chart
chart = generate_ascii_chart(trends, 'clinical_testing')
print(chart)
```

### Example 2: Detect Significant Changes

```python
from trend_visualization import detect_significant_changes, _extract_trend_data

# Extract data
years, coverage, lengths = _extract_trend_data(trends, 'clinical_testing')

# Detect changes
changes = detect_significant_changes(years, coverage, threshold=5.0)

# Print changes
for change in changes:
    direction = "↗" if change['direction'] == 'increase' else "↘"
    print(f"{direction} {change['year_from']}-{change['year_to']}: "
          f"{change['value_from']:.1f}% → {change['value_to']:.1f}% "
          f"({change['change_pct']:+.1f}%)")
```

**Output:**
```
↗ 2020-2021: 60.0% → 70.0% (+16.7%)
↗ 2022-2023: 70.0% → 80.0% (+14.3%)
↗ 2023-2024: 80.0% → 90.0% (+12.5%)
```

### Example 3: Generate SVG for HTML

```python
from trend_visualization import generate_svg_chart

# Generate SVG chart
svg = generate_svg_chart(trends, 'clinical_testing', width=800, height=400)

# Embed in HTML
html = f"""
<html>
<body>
    <h1>Clinical Testing Trends</h1>
    <div style="max-width: 800px; margin: 20px auto;">
        {svg}
    </div>
</body>
</html>
"""

with open('trends.html', 'w') as f:
    f.write(html)
```

---

## Advanced Use Cases

### Custom Threshold for Change Detection

```python
# Detect only major changes (>10%)
major_changes = detect_significant_changes(years, coverage, threshold=10.0)

# Detect all changes (>1%)
all_changes = detect_significant_changes(years, coverage, threshold=1.0)
```

### Custom Chart Dimensions

```python
# Wide chart for detailed view
ascii_chart = generate_ascii_chart(trends, 'clinical_testing', width=100, height=25)

# Large SVG for presentations
svg_chart = generate_svg_chart(trends, 'clinical_testing', width=1200, height=600)
```

### Trend Table with Markdown

```python
from trend_visualization import format_trend_table

# Generate markdown table
table = format_trend_table(trends, 'clinical_testing')

# Add to report
with open('report.md', 'a') as f:
    f.write("## Detailed Trends\n\n")
    f.write(table)
```

---

## Visual Interpretation Guide

### ASCII Chart Elements

| Symbol | Meaning |
|--------|---------|
| █ | Coverage percentage data point |
| ▓ | Coverage trend line (connecting points) |
| · | Average word count data point |
| ░ | Average word count trend line |
| │ | Y-axis |
| ─ | X-axis |
| └ | Corner |
| ↗ | Significant increase |
| ↘ | Significant decrease |

### SVG Chart Elements

| Element | Meaning |
|---------|---------|
| Blue solid line | Coverage percentage over time |
| Orange dashed line | Average word count over time |
| Circles | Data points (hover for exact values) |
| Arrows with % | Significant changes (>5%) |
| Left Y-axis | Coverage percentage scale |
| Right Y-axis | Word count scale |

---

## Troubleshooting

### Chart Not Appearing

**Problem:** ASCII chart shows "No trend data available"

**Solution:**
1. Verify `--trends` flag is set
2. Check that devices have decision dates
3. Ensure ≥2 different years of data
4. Verify section type exists in data

### Single Year Only

**Problem:** Chart shows single year message instead of trend line

**Cause:** Only one year of data available

**Solution:**
1. Expand year range: `--years 2020-2024`
2. Remove year filter to include all available data
3. Check if older submissions are in structured cache

### SVG Not Rendering

**Problem:** SVG chart appears as text in browser

**Cause:** File opened directly (not as HTML)

**Solution:**
1. Open `.html` file (not `.md` file)
2. Use `--html` flag to generate HTML report
3. Ensure browser supports SVG (all modern browsers do)

---

## Performance Tips

### Large Datasets (>20 Years)

For datasets with many years:

```bash
# Limit to recent years
python3 compare_sections.py --product-code DQY --sections clinical --years 2015-2024 --trends

# Use smaller chart dimensions for faster rendering
# (Modify default in trend_visualization.py or use Python API)
```

### Multiple Sections

When analyzing many sections:

```bash
# Process specific sections instead of 'all'
python3 compare_sections.py --product-code DQY --sections clinical,biocompat,performance --trends

# Use --quiet for JSON output (faster for scripting)
python3 compare_sections.py --product-code DQY --sections clinical --trends --quiet
```

---

## Best Practices

### 1. Choose Appropriate Time Range

- **Recommended:** 5-10 years for meaningful trends
- **Minimum:** 2 years (required for trend analysis)
- **Maximum:** 20 years (chart remains readable)

### 2. Select Relevant Sections

- Focus on sections relevant to your device type
- Avoid "all" unless needed - generates large reports
- Prioritize: clinical_testing, biocompatibility, performance_testing

### 3. Interpret Changes Contextually

- **Increasing coverage:** Regulators may be requesting more data
- **Decreasing coverage:** Practice may be consolidating (not necessarily bad)
- **Stable coverage:** Well-established practice (safe to follow)

### 4. Export Multiple Formats

```bash
# Generate all formats for different audiences
python3 compare_sections.py --product-code DQY --sections clinical --trends --html --csv
```

- **Markdown (.md):** For internal review, version control
- **HTML (.html):** For presentations, stakeholder sharing
- **CSV (.csv):** For data analysis, Excel pivots

---

## Related Documentation

- **Module Documentation:** `TREND_VISUALIZATION_README.md`
- **Implementation Summary:** `FE-007-IMPLEMENTATION-SUMMARY.md`
- **Test Suite:** `tests/test_trend_visualization.py`
- **Section Analytics:** `section_analytics.py` module
- **Compare Sections Tool:** `compare_sections.py` CLI

---

**Version:** 5.37.0 (FE-007)
**Last Updated:** 2026-02-17
**Test Coverage:** 48/48 tests passing
