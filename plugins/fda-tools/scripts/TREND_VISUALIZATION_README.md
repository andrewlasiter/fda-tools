# Trend Visualization Module

**Version:** 5.37.0 (FE-007)
**Status:** Production Ready
**Test Coverage:** 48/48 tests passing (100%)

## Overview

The Trend Visualization module provides professional ASCII and SVG chart generation for FDA 510(k) temporal trend analysis. It enables regulatory professionals to visualize section coverage and content length trends over time with automatic detection and highlighting of significant changes.

## Features

### 1. ASCII Line Charts for Markdown
- Clean, professional ASCII art charts
- Dual-axis visualization (coverage % + word count)
- Year labels and axis markers
- Automatic scaling and normalization
- Significant change annotations (>5% threshold)
- Works in any terminal or markdown viewer

### 2. SVG Charts for HTML
- Responsive inline SVG with viewBox
- Professional styling with sans-serif fonts
- Hover tooltips showing exact values
- Dual-axis with clear labels
- Color-coded metrics (blue=coverage, orange=length)
- Change annotations with arrows and percentages

### 3. Significant Change Detection
- Automatic detection of year-over-year changes >5%
- Direction indicators (↗ increase, ↘ decrease)
- Percentage change calculations
- Customizable threshold
- Handles edge cases (zero values, single year)

### 4. Trend Table Formatting
- Markdown tables with change indicators
- Year-by-year coverage and length data
- Visual change markers
- Sortable and searchable

## Usage

### Command Line

```bash
# Generate markdown report with ASCII charts
python3 compare_sections.py --product-code DQY --sections clinical,biocompat --trends

# Generate HTML report with SVG charts
python3 compare_sections.py --product-code DQY --sections clinical --trends --html

# Multi-product comparison with trends
python3 compare_sections.py --product-codes DQY,OVE --sections all --trends --html
```

### Python API

```python
from trend_visualization import (
    generate_ascii_chart,
    generate_svg_chart,
    detect_significant_changes,
    format_trend_table,
)

# Generate ASCII chart
ascii_chart = generate_ascii_chart(trends_results, 'clinical_testing')
print(ascii_chart)

# Generate SVG chart for HTML
svg_chart = generate_svg_chart(trends_results, 'clinical_testing', width=800, height=400)

# Detect significant changes
years, coverage, lengths = _extract_trend_data(trends_results, 'clinical_testing')
changes = detect_significant_changes(years, coverage, threshold=5.0)

for change in changes:
    print(f"{change['year_from']}-{change['year_to']}: {change['change_pct']:+.1f}%")

# Format as markdown table
table = format_trend_table(trends_results, 'clinical_testing')
print(table)
```

## Chart Examples

### ASCII Chart Example

```
### clinical_testing Trends

```
  90%   │
        │    ████
        │   ██  ██
  75%   │  ██    ██
        │ ██      ··
        │██      ··
  60%   ███     ··
        └────────────────────
        2020  2022  2024
```

Legend: █ Coverage %  ·· Avg Word Count

**Significant Changes (>5%):**
- ↗ Coverage: 2020-2021: 60.0% → 70.0% (+16.7%)
- ↗ Coverage: 2023-2024: 80.0% → 90.0% (+12.5%)
- ↗ Length: 2020-2021: 200 → 250 words (+25.0%)
```

### SVG Chart Features

The SVG charts include:

- **Responsive design:** Scales to container width
- **Hover tooltips:** Exact values on data points
- **Dual Y-axes:** Left for coverage %, right for word count
- **Color coding:** Blue solid line = coverage, Orange dashed = length
- **Annotations:** Significant changes marked with arrows and percentages
- **Professional styling:** Clean, publication-ready appearance

## API Reference

### Core Functions

#### `generate_ascii_chart(trends_results, section_type, width=60, height=15)`

Generate ASCII line chart for markdown reports.

**Parameters:**
- `trends_results` (dict): Output from `analyze_temporal_trends()`
- `section_type` (str): Section to visualize (e.g., 'clinical_testing')
- `width` (int): Chart width in characters (default: 60)
- `height` (int): Chart height in characters (default: 15)

**Returns:**
- Multi-line ASCII chart string with legend and change annotations

**Raises:**
- `ValueError`: If section_type not found in trends_results

---

#### `generate_svg_chart(trends_results, section_type, width=800, height=400)`

Generate inline SVG chart for HTML reports.

**Parameters:**
- `trends_results` (dict): Output from `analyze_temporal_trends()`
- `section_type` (str): Section to visualize
- `width` (int): Chart width in pixels (default: 800)
- `height` (int): Chart height in pixels (default: 400)

**Returns:**
- SVG markup string with inline styles

**Raises:**
- `ValueError`: If section_type not found in trends_results

---

#### `detect_significant_changes(years, values, threshold=5.0)`

Detect year-over-year changes exceeding threshold.

**Parameters:**
- `years` (List[int]): List of years
- `values` (List[float]): Corresponding values
- `threshold` (float): Percentage threshold for significance (default: 5.0)

**Returns:**
- List of dicts with change information:
  ```python
  [
      {
          'year_from': 2020,
          'year_to': 2021,
          'value_from': 60.0,
          'value_to': 70.0,
          'change_pct': 16.67,
          'direction': 'increase'  # or 'decrease'
      }
  ]
  ```

---

#### `format_trend_table(trends_results, section_type)`

Format trend data as markdown table with change indicators.

**Parameters:**
- `trends_results` (dict): Output from `analyze_temporal_trends()`
- `section_type` (str): Section to format

**Returns:**
- Markdown table string

**Raises:**
- `ValueError`: If section_type not found in trends_results

## Integration with compare_sections.py

The visualization module integrates seamlessly with the section comparison tool:

### Markdown Reports

When `--trends` flag is used, ASCII charts are automatically embedded in Section 6 (Temporal Trend Analysis):

```markdown
## 6. Temporal Trend Analysis

### clinical_testing

**Coverage trend:** increasing (R²=0.95, slope=7.50)
**Section length trend:** increasing (R²=0.92)

[ASCII Chart Here]

**Significant Changes (>5%):**
- ↗ Coverage: 2020-2021: 60.0% → 70.0% (+16.7%)
...
```

### HTML Reports

When `--trends --html` flags are used, interactive SVG charts replace ASCII:

```html
<h2>Temporal Trend Analysis</h2>
<h3>Clinical Testing - Temporal Trends</h3>
<div class="chart-container">
    <svg viewBox="0 0 800 400" ...>
        <!-- Interactive chart with tooltips -->
    </svg>
</div>
```

## Technical Details

### Scaling Algorithm

Values are normalized using min-max scaling:

```python
normalized = (value - min_value) / (max_value - min_value)
scaled_value = target_min + (normalized * target_range)
```

Special cases:
- **All equal values:** Placed at midpoint of range
- **All zeros:** Placed at minimum of range
- **Empty list:** Returns empty list

### Change Detection Algorithm

Percentage change calculated as:

```python
change_pct = ((current_value - previous_value) / previous_value) * 100
```

Edge cases:
- **Zero previous value:** Change skipped (division by zero)
- **Single data point:** Returns empty list
- **Threshold filtering:** Only changes where `abs(change_pct) >= threshold`

### Chart Rendering

#### ASCII Charts
1. Scale coverage and length to chart height
2. Create 2D character grid
3. Plot coverage line with solid blocks (█, ▓)
4. Plot length line with light blocks (░, ·)
5. Add axes with box-drawing characters (│, ─, └)
6. Label years on x-axis, percentages on y-axis

#### SVG Charts
1. Calculate chart area (minus margins)
2. Create scale functions for x (years) and y (values)
3. Draw axes with labels
4. Plot coverage line (blue solid) and length line (orange dashed)
5. Add data point circles with hover tooltips
6. Annotate significant changes (limit 3 per metric)

## Performance

- **ASCII generation:** <10ms for 5 years of data
- **SVG generation:** <20ms for 5 years of data
- **Change detection:** O(n) where n = number of years
- **Memory usage:** <1MB for typical datasets

## Error Handling

The module handles errors gracefully:

```python
try:
    ascii_chart = generate_ascii_chart(trends_results, section_type)
    f.write(ascii_chart)
except ValueError as e:
    f.write(f"*Unable to generate chart: {e}*\n")
```

Common errors:
- **Missing section:** `ValueError: Section type 'xxx' not found in trends data`
- **Invalid data structure:** Returns empty string or fallback message
- **Zero/NaN values:** Handled with special case logic

## Testing

Comprehensive test suite with 48 tests:

```bash
pytest tests/test_trend_visualization.py -v
```

**Test Categories:**
- VIZ-001 to VIZ-014: Core functionality (14 test classes)
- Edge cases: Empty data, single year, all zeros
- Safety: HTML injection prevention
- Performance: Large datasets
- Integration: compare_sections.py compatibility

**Coverage:** 100% of public functions and edge cases

## Security

### XSS Prevention

SVG output is safe from script injection:
- No `<script>` tags
- No event handlers (onclick, onerror, onload)
- All text content is literal (no user-controlled JavaScript)

Tested with:
```python
def test_svg_no_script_tags(self, multi_year_trends):
    svg = generate_svg_chart(multi_year_trends, "clinical_testing")
    assert "<script" not in svg.lower()
    assert "onclick" not in svg.lower()
```

## Future Enhancements

Planned improvements for v5.38.0+:
- [ ] Interactive JavaScript charts (optional)
- [ ] Export charts as PNG/PDF
- [ ] Multiple metrics on same chart (>2)
- [ ] Confidence intervals for trends
- [ ] Comparative charts (multiple product codes side-by-side)
- [ ] Animation for HTML charts

## License

Part of FDA Tools Plugin. See main LICENSE file.

## Support

For issues or feature requests:
1. Check existing tests in `tests/test_trend_visualization.py`
2. Review examples in this README
3. File issue with minimal reproducible example

## Changelog

**v5.37.0 (2026-02-17)** - FE-007
- Initial release
- ASCII chart generation
- SVG chart generation
- Significant change detection
- Dual-axis visualization
- 48 comprehensive tests
