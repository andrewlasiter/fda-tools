# Trend Visualization Quick Start Guide

**5-Minute Guide to Enhanced FDA 510(k) Trend Visualization**

---

## What's New in v5.37.0 (FE-007)

Professional trend charts for temporal analysis:
- **ASCII charts** for markdown reports
- **SVG charts** for HTML reports
- **Automatic change detection** (>5% threshold)
- **Side-by-side metrics** (coverage + word count)

---

## Quick Start (3 Commands)

### 1. Basic Trend Analysis (Markdown)

```bash
python3 scripts/compare_sections.py \
    --product-code DQY \
    --sections clinical \
    --trends
```

**Output:** Markdown report with ASCII trend charts

### 2. Interactive HTML Charts

```bash
python3 scripts/compare_sections.py \
    --product-code DQY \
    --sections clinical \
    --trends \
    --html
```

**Output:** HTML report with interactive SVG charts (hover for values)

### 3. Complete Analysis (All Formats)

```bash
python3 scripts/compare_sections.py \
    --product-code DQY \
    --sections clinical,biocompat,performance \
    --years 2020-2024 \
    --trends \
    --html \
    --csv
```

**Output:** Markdown + HTML + CSV with full trend analysis

---

## Sample Output

### ASCII Chart (Markdown)

```
### clinical_testing Trends

```
   90% │                                              ·▓▓▓█
       │                                          ··▓▓▓
       │                                      ···▓▓▓
   75% │                     ····░   ▓▓▓
       │         ▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓█
   60% │█
       └──────────────────────────────────────────────────
        2020        2021         2022        2023
```

Legend: █ Coverage %  ·· Avg Word Count

**Significant Changes (>5%):**
- ↗ Coverage: 2020-2021: 60.0% → 70.0% (+16.7%)
- ↗ Length: 2020-2021: 200 → 250 words (+25.0%)
```

### SVG Chart (HTML)

**Features:**
- Blue solid line = Coverage %
- Orange dashed line = Word count
- Hover circles for exact values
- Arrows mark significant changes
- Responsive (scales to screen)

---

## Python API (1 Minute)

```python
from section_analytics import analyze_temporal_trends
from trend_visualization import generate_ascii_chart, detect_significant_changes

# Analyze trends
trends = analyze_temporal_trends(section_data, ['clinical_testing'])

# Generate chart
chart = generate_ascii_chart(trends, 'clinical_testing')
print(chart)

# Detect changes
years, coverage, _ = _extract_trend_data(trends, 'clinical_testing')
changes = detect_significant_changes(years, coverage)

for c in changes:
    print(f"{c['year_from']}-{c['year_to']}: {c['change_pct']:+.1f}%")
```

---

## Common Use Cases

### 1. Single Section Trend

```bash
python3 scripts/compare_sections.py --product-code DQY --sections clinical --trends
```

**When to use:** Quick analysis of one section

### 2. Multi-Section Comparison

```bash
python3 scripts/compare_sections.py --product-code DQY --sections clinical,biocompat,performance --trends --html
```

**When to use:** Compare multiple sections side-by-side

### 3. Year Range Filter

```bash
python3 scripts/compare_sections.py --product-code DQY --sections clinical --years 2020-2024 --trends
```

**When to use:** Focus on recent trends only

### 4. Multi-Product Benchmark

```bash
python3 scripts/compare_sections.py --product-codes DQY,OVE --sections clinical --trends --html
```

**When to use:** Compare trends across product codes

---

## Interpreting Results

### Increasing Coverage (Good Sign)

```
↗ Coverage: 2020-2021: 60.0% → 70.0% (+16.7%)
```

**Meaning:** More devices include this section
**Action:** Follow the trend - include comprehensive data

### Decreasing Coverage (Context Needed)

```
↘ Coverage: 2020-2021: 90.0% → 80.0% (-11.1%)
```

**Meaning:** Fewer devices include this section
**Possible reasons:**
- Regulators accepting less data (good)
- Practice consolidating (neutral)
- Your device may be exception (check carefully)

### Stable Coverage (Safe to Follow)

```
No significant changes detected
```

**Meaning:** Well-established practice
**Action:** Follow peer submissions

---

## Troubleshooting (30 Seconds)

### "No trend data available"

**Cause:** Less than 2 years of data
**Fix:** Expand year range or remove `--years` filter

### Chart shows single year only

**Cause:** All devices from same year
**Fix:** Use broader product code or remove filters

### SVG not showing in browser

**Cause:** Opened .md file instead of .html
**Fix:** Use `--html` flag and open .html file

---

## Next Steps

### Learn More
- **Full Documentation:** `TREND_VISUALIZATION_README.md`
- **Examples:** `VISUALIZATION_EXAMPLE.md`
- **Implementation:** `FE-007-IMPLEMENTATION-SUMMARY.md`

### Try Advanced Features
- Custom change threshold (Python API)
- Larger chart dimensions (Python API)
- Multiple metrics (coverage + length shown by default)

### Integration
- Embed charts in regulatory submissions
- Export to presentation software
- Combine with similarity analysis (`--similarity --trends`)

---

## Support

**Tests:** `pytest tests/test_trend_visualization.py -v`
**Version:** 5.37.0 (FE-007)
**Status:** Production Ready (48/48 tests passing)

---

## Cheat Sheet

| Flag | Purpose |
|------|---------|
| `--trends` | Enable temporal trend analysis |
| `--html` | Generate HTML report with SVG charts |
| `--csv` | Export data to CSV |
| `--years 2020-2024` | Filter by year range |
| `--product-codes DQY,OVE` | Compare multiple codes |
| `--sections clinical,biocompat` | Analyze specific sections |
| `--quiet` | JSON output (for scripting) |

**Default behavior:** Markdown with ASCII charts

---

**That's it!** You now have professional trend visualization for FDA 510(k) analysis.

**Most common command:**
```bash
python3 scripts/compare_sections.py --product-code DQY --sections clinical --trends --html
```

---

*Created: 2026-02-17*
*Feature: FE-007 Enhanced Trend Visualization*
*Test Coverage: 48/48 passing (100%)*
