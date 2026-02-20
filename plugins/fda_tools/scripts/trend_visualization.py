#!/usr/bin/env python3
"""
FDA 510(k) Trend Visualization Module

Provides ASCII and SVG chart generation for temporal trend analysis.
Supports dual-axis visualization (coverage + length) with slope detection
and highlighting of significant changes (slope > 5%).

Core functions:
    generate_ascii_chart(trend_data, section_type) -> str
    generate_svg_chart(trend_data, section_type) -> str
    detect_significant_changes(trend_data) -> List[Dict]
    format_trend_table(trend_data, section_type) -> str

Usage:
    from trend_visualization import generate_ascii_chart, generate_svg_chart

    # Generate ASCII chart for markdown
    ascii_chart = generate_ascii_chart(trends_results, 'clinical_testing')

    # Generate SVG chart for HTML
    svg_chart = generate_svg_chart(trends_results, 'clinical_testing')
"""

from typing import Any, Dict, List, Tuple


# ASCII chart characters
BLOCK_FULL = "█"
BLOCK_DARK = "▓"
BLOCK_LIGHT = "░"
LINE_VERTICAL = "│"
LINE_HORIZONTAL = "─"
CORNER_TL = "┌"
CORNER_BL = "└"
CORNER_TR = "┐"
CORNER_BR = "┘"
ARROW_UP = "↗"
ARROW_DOWN = "↘"
ARROW_FLAT = "→"


def _extract_trend_data(
    trends_results: Dict[str, Any], section_type: str
) -> Tuple[List[int], List[float], List[float]]:
    """Extract year, coverage, and length data from trend results.

    Args:
        trends_results: Output from analyze_temporal_trends().
        section_type: Section type to extract (e.g., 'clinical_testing').

    Returns:
        Tuple of (years, coverage_values, length_values).
        All lists have the same length and are sorted by year.

    Raises:
        ValueError: If section_type not found in trends_results.
    """
    trends = trends_results.get("trends", {})
    if section_type not in trends:
        raise ValueError(f"Section type '{section_type}' not found in trends data")

    section_trends = trends[section_type]
    by_year = section_trends.get("by_year", {})

    if not by_year:
        return [], [], []

    years = sorted(by_year.keys())
    coverage_values = []
    length_values = []

    for year in years:
        data = by_year[year]
        coverage_values.append(data.get("coverage_pct", 0.0))
        length_values.append(data.get("avg_word_count", 0.0))

    return years, coverage_values, length_values


def detect_significant_changes(
    years: List[int],
    values: List[float],
    threshold: float = 5.0
) -> List[Dict[str, Any]]:
    """Detect significant year-over-year changes in trend data.

    A change is significant if the absolute percentage change exceeds
    the threshold (default 5%).

    Args:
        years: List of years.
        values: List of values corresponding to each year.
        threshold: Percentage threshold for significance (default: 5.0).

    Returns:
        List of dicts with significant changes:
        [
            {
                'year_from': int,
                'year_to': int,
                'value_from': float,
                'value_to': float,
                'change_pct': float,
                'direction': 'increase' | 'decrease'
            }
        ]
    """
    if len(years) < 2 or len(values) < 2:
        return []

    changes = []
    for i in range(1, len(years)):
        prev_val = values[i - 1]
        curr_val = values[i]

        # Skip if previous value is zero (division by zero)
        if prev_val == 0:
            continue

        # Calculate percentage change
        change_pct = ((curr_val - prev_val) / prev_val) * 100

        if abs(change_pct) >= threshold:
            changes.append({
                "year_from": years[i - 1],
                "year_to": years[i],
                "value_from": round(prev_val, 2),
                "value_to": round(curr_val, 2),
                "change_pct": round(change_pct, 2),
                "direction": "increase" if change_pct > 0 else "decrease"
            })

    return changes


def _scale_to_range(
    values: List[float], target_min: int, target_max: int
) -> List[int]:
    """Scale values to a target range for chart rendering.

    Args:
        values: List of float values.
        target_min: Minimum value in target range.
        target_max: Maximum value in target range.

    Returns:
        List of scaled integer values.
    """
    if not values or all(v == 0 for v in values):
        return [target_min] * len(values)

    min_val = min(values)
    max_val = max(values)

    # If all values are the same, return middle of range
    if min_val == max_val:
        mid = (target_min + target_max) // 2
        return [mid] * len(values)

    # Scale to target range
    range_val = max_val - min_val
    target_range = target_max - target_min

    scaled = []
    for v in values:
        normalized = (v - min_val) / range_val
        scaled_val = int(target_min + (normalized * target_range))
        scaled.append(scaled_val)

    return scaled


def generate_ascii_chart(
    trends_results: Dict[str, Any],
    section_type: str,
    width: int = 60,
    height: int = 15
) -> str:
    """Generate ASCII line chart for temporal trends.

    Creates a dual-axis chart showing coverage percentage and average
    word count over time. Significant changes (>5%) are annotated.

    Args:
        trends_results: Output from analyze_temporal_trends().
        section_type: Section type to visualize.
        width: Chart width in characters (default: 60).
        height: Chart height in characters (default: 15).

    Returns:
        Multi-line ASCII chart string.

    Raises:
        ValueError: If section_type not found in trends_results.
    """
    years, coverage, lengths = _extract_trend_data(trends_results, section_type)

    if not years:
        return f"*No trend data available for {section_type}*\n"

    # Detect significant changes
    cov_changes = detect_significant_changes(years, coverage)
    len_changes = detect_significant_changes(years, lengths)

    # Build chart
    lines = []
    lines.append(f"### {section_type} Trends\n")

    # If only one year, just show a table
    if len(years) == 1:
        lines.append(f"Year: {years[0]}")
        lines.append(f"Coverage: {coverage[0]:.1f}%")
        lines.append(f"Avg Length: {lengths[0]:.0f} words\n")
        return "\n".join(lines)

    # Scale values to chart height
    # Reserve top 2 rows for labels, bottom 2 for axis
    chart_height = height - 4
    cov_scaled = _scale_to_range(coverage, 0, chart_height)
    len_scaled = _scale_to_range(lengths, 0, chart_height)

    # Create chart grid
    grid = [[" " for _ in range(width)] for _ in range(height)]

    # Calculate x positions for each year
    # Leave left margin for y-axis (8 chars), right margin (2 chars)
    left_margin = 8
    right_margin = 2
    chart_width = width - left_margin - right_margin
    x_step = chart_width / max(1, len(years) - 1) if len(years) > 1 else 0

    # Plot coverage line (solid blocks)
    for i, year in enumerate(years):
        x = int(left_margin + (i * x_step))
        y = height - 3 - cov_scaled[i]  # Invert y (0 at top)

        if 0 <= y < height and 0 <= x < width:
            grid[y][x] = BLOCK_FULL

        # Connect to previous point
        if i > 0:
            prev_x = int(left_margin + ((i - 1) * x_step))
            prev_y = height - 3 - cov_scaled[i - 1]

            # Draw line between points
            dx = x - prev_x
            dy = y - prev_y
            steps = max(abs(dx), abs(dy))

            if steps > 0:
                for step in range(steps + 1):
                    t = step / steps
                    interp_x = int(prev_x + t * dx)
                    interp_y = int(prev_y + t * dy)
                    if 0 <= interp_y < height and 0 <= interp_x < width:
                        if grid[interp_y][interp_x] == " ":
                            grid[interp_y][interp_x] = BLOCK_DARK

    # Plot length line (light blocks)
    for i, year in enumerate(years):
        x = int(left_margin + (i * x_step))
        y = height - 3 - len_scaled[i]

        if 0 <= y < height and 0 <= x < width:
            # Don't overwrite coverage markers
            if grid[y][x] == " ":
                grid[y][x] = BLOCK_LIGHT

        # Connect to previous point
        if i > 0:
            prev_x = int(left_margin + ((i - 1) * x_step))
            prev_y = height - 3 - len_scaled[i - 1]

            dx = x - prev_x
            dy = y - prev_y
            steps = max(abs(dx), abs(dy))

            if steps > 0:
                for step in range(steps + 1):
                    t = step / steps
                    interp_x = int(prev_x + t * dx)
                    interp_y = int(prev_y + t * dy)
                    if 0 <= interp_y < height and 0 <= interp_x < width:
                        if grid[interp_y][interp_x] == " ":
                            grid[interp_y][interp_x] = "·"

    # Add axes
    # Bottom horizontal axis
    for x in range(left_margin, width - right_margin):
        grid[height - 2][x] = LINE_HORIZONTAL

    # Left vertical axis
    for y in range(1, height - 1):
        grid[y][left_margin - 1] = LINE_VERTICAL

    # Corners
    grid[height - 2][left_margin - 1] = CORNER_BL

    # Year labels on x-axis
    for i, year in enumerate(years):
        x = int(left_margin + (i * x_step))
        year_str = str(year)
        # Place year label below axis
        if height - 1 < height and x + len(year_str) < width:
            for j, ch in enumerate(year_str):
                if x + j < width:
                    grid[height - 1][x + j] = ch

    # Y-axis labels (coverage on left)
    max_cov = max(coverage)
    min_cov = min(coverage)
    mid_cov = (max_cov + min_cov) / 2

    # Top label
    grid[1][0:6] = list(f"{max_cov:5.0f}%")
    # Middle label
    mid_y = height // 2
    grid[mid_y][0:6] = list(f"{mid_cov:5.0f}%")
    # Bottom label
    grid[height - 3][0:6] = list(f"{min_cov:5.0f}%")

    # Convert grid to string
    lines.append("```")
    for row in grid:
        lines.append("".join(row))
    lines.append("```\n")

    # Legend
    lines.append(f"Legend: {BLOCK_FULL} Coverage %  ·· Avg Word Count\n")

    # Significant changes
    if cov_changes or len_changes:
        lines.append("**Significant Changes (>5%):**\n")
        for change in cov_changes:
            arrow = ARROW_UP if change["direction"] == "increase" else ARROW_DOWN
            lines.append(
                f"- {arrow} Coverage: {change['year_from']}-{change['year_to']}: "
                f"{change['value_from']:.1f}% → {change['value_to']:.1f}% "
                f"({change['change_pct']:+.1f}%)"
            )
        for change in len_changes:
            arrow = ARROW_UP if change["direction"] == "increase" else ARROW_DOWN
            lines.append(
                f"- {arrow} Length: {change['year_from']}-{change['year_to']}: "
                f"{change['value_from']:.0f} → {change['value_to']:.0f} words "
                f"({change['change_pct']:+.1f}%)"
            )
        lines.append("")

    return "\n".join(lines)


def generate_svg_chart(
    trends_results: Dict[str, Any],
    section_type: str,
    width: int = 800,
    height: int = 400
) -> str:
    """Generate inline SVG chart for HTML reports.

    Creates a professional dual-axis chart with hover tooltips,
    responsive design, and significant change annotations.

    Args:
        trends_results: Output from analyze_temporal_trends().
        section_type: Section type to visualize.
        width: Chart width in pixels (default: 800).
        height: Chart height in pixels (default: 400).

    Returns:
        SVG markup string.

    Raises:
        ValueError: If section_type not found in trends_results.
    """
    years, coverage, lengths = _extract_trend_data(trends_results, section_type)

    if not years:
        return f"<p><em>No trend data available for {section_type}</em></p>"

    # Detect significant changes
    cov_changes = detect_significant_changes(years, coverage)
    _ = detect_significant_changes(years, lengths)  # Not used in SVG

    # Chart dimensions (with margins)
    margin_top = 40
    margin_right = 80
    margin_bottom = 60
    margin_left = 60

    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom

    # Scale functions
    def scale_x(year_idx: int) -> float:
        if len(years) == 1:
            return margin_left + chart_width / 2
        return margin_left + (year_idx / (len(years) - 1)) * chart_width

    def scale_y_coverage(value: float) -> float:
        max_val = max(coverage) if coverage else 100
        min_val = min(coverage) if coverage else 0
        range_val = max_val - min_val if max_val != min_val else 1
        normalized = (value - min_val) / range_val
        return margin_top + chart_height - (normalized * chart_height)

    def scale_y_length(value: float) -> float:
        max_val = max(lengths) if lengths else 1000
        min_val = min(lengths) if lengths else 0
        range_val = max_val - min_val if max_val != min_val else 1
        normalized = (value - min_val) / range_val
        return margin_top + chart_height - (normalized * chart_height)

    # Build SVG
    svg_lines = []
    svg_lines.append(
        f'<svg viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'style="max-width: 100%; height: auto; font-family: sans-serif;">'
    )

    # Title
    svg_lines.append(
        f'<text x="{width/2}" y="25" text-anchor="middle" '
        f'style="font-size: 16px; font-weight: bold; fill: #333;">'
        f'{section_type.replace("_", " ").title()} - Temporal Trends'
        f'</text>'
    )

    # Y-axis (left) - Coverage
    svg_lines.append(f'<line x1="{margin_left}" y1="{margin_top}" '
                     f'x2="{margin_left}" y2="{margin_top + chart_height}" '
                     f'stroke="#666" stroke-width="2"/>')

    # Y-axis label (coverage)
    svg_lines.append(
        f'<text x="{margin_left - 45}" y="{margin_top + chart_height/2}" '
        f'text-anchor="middle" transform="rotate(-90 {margin_left - 45} {margin_top + chart_height/2})" '
        f'style="font-size: 12px; fill: #1f77b4;">Coverage (%)</text>'
    )

    # Y-axis (right) - Length
    svg_lines.append(f'<line x1="{margin_left + chart_width}" y1="{margin_top}" '
                     f'x2="{margin_left + chart_width}" y2="{margin_top + chart_height}" '
                     f'stroke="#666" stroke-width="2"/>')

    # Y-axis label (length)
    svg_lines.append(
        f'<text x="{margin_left + chart_width + 45}" y="{margin_top + chart_height/2}" '
        f'text-anchor="middle" transform="rotate(90 {margin_left + chart_width + 45} {margin_top + chart_height/2})" '
        f'style="font-size: 12px; fill: #ff7f0e;">Avg Word Count</text>'
    )

    # X-axis
    svg_lines.append(f'<line x1="{margin_left}" y1="{margin_top + chart_height}" '
                     f'x2="{margin_left + chart_width}" y2="{margin_top + chart_height}" '
                     f'stroke="#666" stroke-width="2"/>')

    # X-axis label
    svg_lines.append(
        f'<text x="{margin_left + chart_width/2}" y="{height - 10}" '
        f'text-anchor="middle" style="font-size: 12px; fill: #666;">Year</text>'
    )

    # Coverage tick marks and labels (left y-axis)
    max_cov = max(coverage) if coverage else 100
    min_cov = min(coverage) if coverage else 0
    cov_ticks = [min_cov, (min_cov + max_cov) / 2, max_cov]
    for tick_val in cov_ticks:
        y = scale_y_coverage(tick_val)
        svg_lines.append(f'<line x1="{margin_left - 5}" y1="{y}" '
                        f'x2="{margin_left}" y2="{y}" stroke="#666" stroke-width="1"/>')
        svg_lines.append(
            f'<text x="{margin_left - 10}" y="{y + 4}" text-anchor="end" '
            f'style="font-size: 10px; fill: #1f77b4;">{tick_val:.0f}</text>'
        )

    # Length tick marks and labels (right y-axis)
    max_len = max(lengths) if lengths else 1000
    min_len = min(lengths) if lengths else 0
    len_ticks = [min_len, (min_len + max_len) / 2, max_len]
    for tick_val in len_ticks:
        y = scale_y_length(tick_val)
        svg_lines.append(f'<line x1="{margin_left + chart_width}" y1="{y}" '
                        f'x2="{margin_left + chart_width + 5}" y2="{y}" stroke="#666" stroke-width="1"/>')
        svg_lines.append(
            f'<text x="{margin_left + chart_width + 10}" y="{y + 4}" '
            f'style="font-size: 10px; fill: #ff7f0e;">{tick_val:.0f}</text>'
        )

    # X-axis tick marks and labels (years)
    for i, year in enumerate(years):
        x = scale_x(i)
        svg_lines.append(f'<line x1="{x}" y1="{margin_top + chart_height}" '
                        f'x2="{x}" y2="{margin_top + chart_height + 5}" stroke="#666" stroke-width="1"/>')
        svg_lines.append(
            f'<text x="{x}" y="{margin_top + chart_height + 20}" text-anchor="middle" '
            f'style="font-size: 10px; fill: #666;">{year}</text>'
        )

    # Plot coverage line
    if len(years) > 1:
        points = " ".join([f"{scale_x(i)},{scale_y_coverage(cov)}"
                          for i, cov in enumerate(coverage)])
        svg_lines.append(
            f'<polyline points="{points}" fill="none" stroke="#1f77b4" '
            f'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
        )

    # Plot length line
    if len(years) > 1:
        points = " ".join([f"{scale_x(i)},{scale_y_length(length)}"
                          for i, length in enumerate(lengths)])
        svg_lines.append(
            f'<polyline points="{points}" fill="none" stroke="#ff7f0e" '
            f'stroke-width="3" stroke-linecap="round" stroke-linejoin="round" '
            f'stroke-dasharray="5,5"/>'
        )

    # Plot data points with hover tooltips
    for i, year in enumerate(years):
        # Coverage point
        x = scale_x(i)
        y_cov = scale_y_coverage(coverage[i])
        svg_lines.append(
            f'<circle cx="{x}" cy="{y_cov}" r="5" fill="#1f77b4" stroke="#fff" stroke-width="2">'
            f'<title>{year}: {coverage[i]:.1f}% coverage</title>'
            f'</circle>'
        )

        # Length point
        y_len = scale_y_length(lengths[i])
        svg_lines.append(
            f'<circle cx="{x}" cy="{y_len}" r="5" fill="#ff7f0e" stroke="#fff" stroke-width="2">'
            f'<title>{year}: {lengths[i]:.0f} words avg</title>'
            f'</circle>'
        )

    # Annotate significant changes
    annotation_y = margin_top - 10
    if cov_changes:
        for change in cov_changes[:3]:  # Limit to 3 annotations
            year_idx = years.index(change["year_to"])
            x = scale_x(year_idx)
            arrow = "↗" if change["direction"] == "increase" else "↘"
            svg_lines.append(
                f'<text x="{x}" y="{annotation_y}" text-anchor="middle" '
                f'style="font-size: 11px; fill: #1f77b4;">'
                f'{arrow}{abs(change["change_pct"]):.0f}%</text>'
            )
            annotation_y -= 12

    # Legend
    legend_x = margin_left
    legend_y = margin_top - 15
    svg_lines.append(f'<line x1="{legend_x}" y1="{legend_y}" '
                    f'x2="{legend_x + 30}" y2="{legend_y}" stroke="#1f77b4" stroke-width="3"/>')
    svg_lines.append(
        f'<text x="{legend_x + 35}" y="{legend_y + 4}" '
        f'style="font-size: 11px; fill: #333;">Coverage</text>'
    )

    legend_x += 120
    svg_lines.append(f'<line x1="{legend_x}" y1="{legend_y}" '
                    f'x2="{legend_x + 30}" y2="{legend_y}" stroke="#ff7f0e" '
                    f'stroke-width="3" stroke-dasharray="5,5"/>')
    svg_lines.append(
        f'<text x="{legend_x + 35}" y="{legend_y + 4}" '
        f'style="font-size: 11px; fill: #333;">Avg Word Count</text>'
    )

    svg_lines.append('</svg>')

    return "\n".join(svg_lines)


def format_trend_table(
    trends_results: Dict[str, Any],
    section_type: str
) -> str:
    """Format trend data as a markdown table.

    Args:
        trends_results: Output from analyze_temporal_trends().
        section_type: Section type to format.

    Returns:
        Markdown table string.

    Raises:
        ValueError: If section_type not found in trends_results.
    """
    years, coverage, lengths = _extract_trend_data(trends_results, section_type)

    if not years:
        return f"*No trend data available for {section_type}*\n"

    lines = []
    lines.append("| Year | Coverage % | Avg Words | Change |")
    lines.append("|------|------------|-----------|--------|")

    # Detect all changes
    cov_changes_dict = {
        c["year_to"]: c for c in detect_significant_changes(years, coverage)
    }
    len_changes_dict = {
        c["year_to"]: c for c in detect_significant_changes(years, lengths)
    }

    for i, year in enumerate(years):
        change_indicators = []

        if year in cov_changes_dict:
            change = cov_changes_dict[year]
            arrow = ARROW_UP if change["direction"] == "increase" else ARROW_DOWN
            change_indicators.append(f"{arrow} Cov {change['change_pct']:+.0f}%")

        if year in len_changes_dict:
            change = len_changes_dict[year]
            arrow = ARROW_UP if change["direction"] == "increase" else ARROW_DOWN
            change_indicators.append(f"{arrow} Len {change['change_pct']:+.0f}%")

        change_str = ", ".join(change_indicators) if change_indicators else "-"

        lines.append(
            f"| {year} | {coverage[i]:.1f}% | {lengths[i]:.0f} | {change_str} |"
        )

    return "\n".join(lines) + "\n"
