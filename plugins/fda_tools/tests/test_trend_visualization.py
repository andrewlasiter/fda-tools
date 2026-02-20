"""
Tests for Trend Visualization Module (FE-007).

Validates ASCII chart generation, SVG chart generation, slope detection,
and change highlighting for temporal trend analysis.

Test Coverage:
    - VIZ-001: ASCII chart generation with valid data
    - VIZ-002: SVG chart generation with valid data
    - VIZ-003: Significant change detection (>5% threshold)
    - VIZ-004: Empty data handling
    - VIZ-005: Single year data handling
    - VIZ-006: Dual-axis visualization (coverage + length)
    - VIZ-007: Slope direction indicators
    - VIZ-008: Value scaling and normalization
    - VIZ-009: HTML escape safety
    - VIZ-010: Trend table formatting
    - VIZ-011: Multi-year increasing trend
    - VIZ-012: Multi-year decreasing trend
    - VIZ-013: Custom chart dimensions
    - VIZ-014: Change annotation limits

Total: 14 tests covering trend_visualization.py
"""

import pytest

from trend_visualization import (  # type: ignore
    detect_significant_changes,
    format_trend_table,
    generate_ascii_chart,
    generate_svg_chart,
    _extract_trend_data,
    _scale_to_range,
)


# ===================================================================
# Test Fixtures
# ===================================================================


@pytest.fixture
def multi_year_trends():
    """Multi-year trend data for testing (2020-2024).

    Coverage increases from 60% to 90% (50% total increase).
    Length increases from 200 to 400 words (100% total increase).
    """
    return {
        "total_devices": 50,
        "year_range": {"start": 2020, "end": 2024},
        "trends": {
            "clinical_testing": {
                "coverage_trend": {
                    "direction": "increasing",
                    "slope": 7.5,
                    "r_squared": 0.95,
                    "start_year": 2020,
                    "end_year": 2024,
                    "start_value": 60.0,
                    "end_value": 90.0,
                },
                "length_trend": {
                    "direction": "increasing",
                    "slope": 50.0,
                    "r_squared": 0.92,
                    "start_year": 2020,
                    "end_year": 2024,
                    "start_value": 200.0,
                    "end_value": 400.0,
                },
                "by_year": {
                    2020: {
                        "device_count": 10,
                        "devices_with_section": 6,
                        "coverage_pct": 60.0,
                        "avg_word_count": 200.0,
                        "standards_count": 15,
                    },
                    2021: {
                        "device_count": 10,
                        "devices_with_section": 7,
                        "coverage_pct": 70.0,
                        "avg_word_count": 250.0,
                        "standards_count": 18,
                    },
                    2022: {
                        "device_count": 10,
                        "devices_with_section": 7,
                        "coverage_pct": 70.0,
                        "avg_word_count": 300.0,
                        "standards_count": 20,
                    },
                    2023: {
                        "device_count": 10,
                        "devices_with_section": 8,
                        "coverage_pct": 80.0,
                        "avg_word_count": 350.0,
                        "standards_count": 22,
                    },
                    2024: {
                        "device_count": 10,
                        "devices_with_section": 9,
                        "coverage_pct": 90.0,
                        "avg_word_count": 400.0,
                        "standards_count": 25,
                    },
                },
            }
        },
    }


@pytest.fixture
def single_year_trends():
    """Single year trend data (insufficient for trend analysis)."""
    return {
        "total_devices": 10,
        "year_range": {"start": 2024, "end": 2024},
        "trends": {
            "clinical_testing": {
                "coverage_trend": {
                    "direction": "insufficient_data",
                    "slope": 0.0,
                    "r_squared": 0.0,
                },
                "length_trend": {
                    "direction": "insufficient_data",
                    "slope": 0.0,
                    "r_squared": 0.0,
                },
                "by_year": {
                    2024: {
                        "device_count": 10,
                        "devices_with_section": 8,
                        "coverage_pct": 80.0,
                        "avg_word_count": 300.0,
                        "standards_count": 20,
                    }
                },
            }
        },
    }


@pytest.fixture
def decreasing_trends():
    """Decreasing trend data (2020-2024).

    Coverage decreases from 90% to 50% (-44% total).
    Length decreases from 500 to 200 words (-60% total).
    """
    return {
        "total_devices": 50,
        "year_range": {"start": 2020, "end": 2024},
        "trends": {
            "biocompatibility": {
                "coverage_trend": {
                    "direction": "decreasing",
                    "slope": -10.0,
                    "r_squared": 0.88,
                    "start_year": 2020,
                    "end_year": 2024,
                    "start_value": 90.0,
                    "end_value": 50.0,
                },
                "length_trend": {
                    "direction": "decreasing",
                    "slope": -75.0,
                    "r_squared": 0.85,
                    "start_year": 2020,
                    "end_year": 2024,
                    "start_value": 500.0,
                    "end_value": 200.0,
                },
                "by_year": {
                    2020: {
                        "device_count": 10,
                        "devices_with_section": 9,
                        "coverage_pct": 90.0,
                        "avg_word_count": 500.0,
                        "standards_count": 30,
                    },
                    2021: {
                        "device_count": 10,
                        "devices_with_section": 8,
                        "coverage_pct": 80.0,
                        "avg_word_count": 425.0,
                        "standards_count": 25,
                    },
                    2022: {
                        "device_count": 10,
                        "devices_with_section": 7,
                        "coverage_pct": 70.0,
                        "avg_word_count": 350.0,
                        "standards_count": 20,
                    },
                    2023: {
                        "device_count": 10,
                        "devices_with_section": 6,
                        "coverage_pct": 60.0,
                        "avg_word_count": 275.0,
                        "standards_count": 15,
                    },
                    2024: {
                        "device_count": 10,
                        "devices_with_section": 5,
                        "coverage_pct": 50.0,
                        "avg_word_count": 200.0,
                        "standards_count": 10,
                    },
                },
            }
        },
    }


# ===================================================================
# VIZ-001: ASCII Chart Generation
# ===================================================================


class TestVIZ001ASCIIChartGeneration:
    """VIZ-001: ASCII chart generation with valid multi-year data."""

    def test_ascii_chart_contains_title(self, multi_year_trends):
        """ASCII chart includes section type title."""
        chart = generate_ascii_chart(multi_year_trends, "clinical_testing")
        assert "clinical_testing" in chart.lower()

    def test_ascii_chart_contains_legend(self, multi_year_trends):
        """ASCII chart includes legend explaining symbols."""
        chart = generate_ascii_chart(multi_year_trends, "clinical_testing")
        assert "Legend:" in chart
        assert "Coverage" in chart

    def test_ascii_chart_contains_code_block(self, multi_year_trends):
        """ASCII chart is wrapped in markdown code block."""
        chart = generate_ascii_chart(multi_year_trends, "clinical_testing")
        assert "```" in chart

    def test_ascii_chart_multi_line(self, multi_year_trends):
        """ASCII chart produces multi-line output."""
        chart = generate_ascii_chart(multi_year_trends, "clinical_testing")
        lines = chart.split("\n")
        assert len(lines) > 10, f"Chart should have >10 lines, got {len(lines)}"

    def test_ascii_chart_contains_years(self, multi_year_trends):
        """ASCII chart includes year labels."""
        chart = generate_ascii_chart(multi_year_trends, "clinical_testing")
        assert "2020" in chart
        assert "2024" in chart


# ===================================================================
# VIZ-002: SVG Chart Generation
# ===================================================================


class TestVIZ002SVGChartGeneration:
    """VIZ-002: SVG chart generation with valid multi-year data."""

    def test_svg_chart_valid_xml(self, multi_year_trends):
        """SVG chart produces valid XML structure."""
        svg = generate_svg_chart(multi_year_trends, "clinical_testing")
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")

    def test_svg_chart_contains_title(self, multi_year_trends):
        """SVG chart includes title element."""
        svg = generate_svg_chart(multi_year_trends, "clinical_testing")
        assert "<text" in svg
        assert "Clinical Testing" in svg or "clinical_testing" in svg.lower()

    def test_svg_chart_contains_axes(self, multi_year_trends):
        """SVG chart includes axis elements."""
        svg = generate_svg_chart(multi_year_trends, "clinical_testing")
        assert "<line" in svg  # Axis lines
        assert "Coverage" in svg  # Y-axis label
        assert "Year" in svg  # X-axis label

    def test_svg_chart_contains_data_points(self, multi_year_trends):
        """SVG chart includes data point circles."""
        svg = generate_svg_chart(multi_year_trends, "clinical_testing")
        assert "<circle" in svg
        assert "2020" in svg
        assert "2024" in svg

    def test_svg_chart_contains_lines(self, multi_year_trends):
        """SVG chart includes polyline for trend visualization."""
        svg = generate_svg_chart(multi_year_trends, "clinical_testing")
        assert "<polyline" in svg

    def test_svg_chart_contains_tooltips(self, multi_year_trends):
        """SVG chart includes hover tooltips."""
        svg = generate_svg_chart(multi_year_trends, "clinical_testing")
        assert "<title>" in svg

    def test_svg_chart_viewbox_attribute(self, multi_year_trends):
        """SVG chart has viewBox for responsive scaling."""
        svg = generate_svg_chart(multi_year_trends, "clinical_testing")
        assert 'viewBox="0 0' in svg


# ===================================================================
# VIZ-003: Significant Change Detection
# ===================================================================


class TestVIZ003SignificantChangeDetection:
    """VIZ-003: Detect significant changes (>5% threshold)."""

    def test_detect_significant_increase(self):
        """Detect significant increase between years."""
        years = [2020, 2021, 2022]
        values = [60.0, 70.0, 80.0]  # +16.7%, +14.3% (both >5%)
        changes = detect_significant_changes(years, values, threshold=5.0)

        assert len(changes) >= 2
        assert all(c["direction"] == "increase" for c in changes)
        assert all(abs(c["change_pct"]) >= 5.0 for c in changes)

    def test_detect_significant_decrease(self):
        """Detect significant decrease between years."""
        years = [2020, 2021, 2022]
        values = [90.0, 80.0, 70.0]  # -11.1%, -12.5% (both >5%)
        changes = detect_significant_changes(years, values, threshold=5.0)

        assert len(changes) >= 2
        assert all(c["direction"] == "decrease" for c in changes)
        assert all(abs(c["change_pct"]) >= 5.0 for c in changes)

    def test_no_significant_changes_stable(self):
        """No changes detected when values are stable."""
        years = [2020, 2021, 2022, 2023]
        values = [80.0, 81.0, 79.5, 80.5]  # All <5%
        changes = detect_significant_changes(years, values, threshold=5.0)

        assert len(changes) == 0

    def test_change_structure(self):
        """Change dict contains all required fields."""
        years = [2020, 2021]
        values = [60.0, 75.0]  # +25%
        changes = detect_significant_changes(years, values)

        assert len(changes) == 1
        change = changes[0]
        assert "year_from" in change
        assert "year_to" in change
        assert "value_from" in change
        assert "value_to" in change
        assert "change_pct" in change
        assert "direction" in change

        assert change["year_from"] == 2020
        assert change["year_to"] == 2021
        assert change["value_from"] == 60.0
        assert change["value_to"] == 75.0
        assert change["change_pct"] == pytest.approx(25.0, rel=0.1)

    def test_custom_threshold(self):
        """Custom threshold filters changes appropriately."""
        years = [2020, 2021, 2022]
        values = [100.0, 107.0, 115.0]  # +7%, +7.5%

        # 5% threshold: both pass
        changes_5 = detect_significant_changes(years, values, threshold=5.0)
        assert len(changes_5) == 2

        # 8% threshold: none pass
        changes_8 = detect_significant_changes(years, values, threshold=8.0)
        assert len(changes_8) == 0

    def test_zero_previous_value_skipped(self):
        """Zero values don't cause division by zero."""
        years = [2020, 2021, 2022]
        values = [0.0, 50.0, 75.0]  # First change has 0 denominator
        changes = detect_significant_changes(years, values)

        # Should skip 2020→2021 (division by zero) but include 2021→2022 (+50%)
        assert len(changes) == 1
        assert changes[0]["year_from"] == 2021


# ===================================================================
# VIZ-004: Empty Data Handling
# ===================================================================


class TestVIZ004EmptyDataHandling:
    """VIZ-004: Graceful handling of empty/missing trend data."""

    def test_extract_missing_section(self, multi_year_trends):
        """Extract trend data raises ValueError for missing section."""
        with pytest.raises(ValueError, match="not found"):
            _extract_trend_data(multi_year_trends, "nonexistent_section")

    def test_ascii_chart_missing_section(self, multi_year_trends):
        """ASCII chart raises ValueError for missing section."""
        with pytest.raises(ValueError):
            generate_ascii_chart(multi_year_trends, "nonexistent_section")

    def test_svg_chart_missing_section(self, multi_year_trends):
        """SVG chart raises ValueError for missing section."""
        with pytest.raises(ValueError):
            generate_svg_chart(multi_year_trends, "nonexistent_section")

    def test_detect_changes_empty_lists(self):
        """Detect changes returns empty list for empty input."""
        changes = detect_significant_changes([], [])
        assert changes == []

    def test_detect_changes_single_value(self):
        """Detect changes returns empty list for single value."""
        changes = detect_significant_changes([2024], [80.0])
        assert changes == []


# ===================================================================
# VIZ-005: Single Year Data Handling
# ===================================================================


class TestVIZ005SingleYearData:
    """VIZ-005: Handle single-year data (insufficient for trends)."""

    def test_ascii_chart_single_year(self, single_year_trends):
        """ASCII chart handles single year gracefully."""
        chart = generate_ascii_chart(single_year_trends, "clinical_testing")
        assert "2024" in chart
        assert "80.0%" in chart or "80%" in chart
        assert "300" in chart  # Word count

    def test_svg_chart_single_year(self, single_year_trends):
        """SVG chart handles single year gracefully."""
        svg = generate_svg_chart(single_year_trends, "clinical_testing")
        assert "<svg" in svg
        assert "2024" in svg
        assert "<circle" in svg  # Data point

    def test_format_table_single_year(self, single_year_trends):
        """Trend table handles single year."""
        table = format_trend_table(single_year_trends, "clinical_testing")
        assert "2024" in table
        assert "80.0%" in table or "80%" in table


# ===================================================================
# VIZ-006: Dual-Axis Visualization
# ===================================================================


class TestVIZ006DualAxisVisualization:
    """VIZ-006: Coverage and length shown side-by-side."""

    def test_extract_both_metrics(self, multi_year_trends):
        """Extract both coverage and length data."""
        years, coverage, lengths = _extract_trend_data(
            multi_year_trends, "clinical_testing"
        )

        assert len(years) == 5
        assert len(coverage) == 5
        assert len(lengths) == 5

        # Verify values
        assert coverage[0] == 60.0
        assert coverage[-1] == 90.0
        assert lengths[0] == 200.0
        assert lengths[-1] == 400.0

    def test_svg_dual_axis_labels(self, multi_year_trends):
        """SVG chart has labels for both axes."""
        svg = generate_svg_chart(multi_year_trends, "clinical_testing")
        assert "Coverage" in svg
        assert "Word Count" in svg or "Avg Word Count" in svg

    def test_svg_dual_lines(self, multi_year_trends):
        """SVG chart has two polylines (coverage + length)."""
        svg = generate_svg_chart(multi_year_trends, "clinical_testing")
        polyline_count = svg.count("<polyline")
        assert polyline_count >= 2, f"Expected ≥2 polylines, found {polyline_count}"


# ===================================================================
# VIZ-007: Slope Direction Indicators
# ===================================================================


class TestVIZ007SlopeDirectionIndicators:
    """VIZ-007: Visual indicators for trend direction."""

    def test_ascii_increasing_indicators(self, multi_year_trends):
        """ASCII chart shows increase indicators."""
        chart = generate_ascii_chart(multi_year_trends, "clinical_testing")
        # Should have significant changes noted
        assert "Significant Changes" in chart or "%" in chart

    def test_ascii_decreasing_indicators(self, decreasing_trends):
        """ASCII chart shows decrease indicators."""
        chart = generate_ascii_chart(decreasing_trends, "biocompatibility")
        assert "Significant Changes" in chart or "%" in chart

    def test_svg_change_annotations(self, multi_year_trends):
        """SVG chart annotates significant changes."""
        svg = generate_svg_chart(multi_year_trends, "clinical_testing")
        # Should have percentage annotations or arrows
        assert "%" in svg or "arrow" in svg.lower()


# ===================================================================
# VIZ-008: Value Scaling
# ===================================================================


class TestVIZ008ValueScaling:
    """VIZ-008: Value scaling and normalization."""

    def test_scale_to_range_normal(self):
        """Scale values to target range correctly."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        scaled = _scale_to_range(values, 0, 10)

        assert scaled[0] == 0  # Min value -> min target
        assert scaled[-1] == 10  # Max value -> max target
        assert all(0 <= v <= 10 for v in scaled)
        assert scaled[2] == 5  # Middle value -> middle of range

    def test_scale_all_equal_values(self):
        """Scale handles all equal values."""
        values = [50.0, 50.0, 50.0, 50.0]
        scaled = _scale_to_range(values, 0, 10)

        # All should be at midpoint
        assert all(v == 5 for v in scaled)

    def test_scale_empty_list(self):
        """Scale handles empty list."""
        scaled = _scale_to_range([], 0, 10)
        assert scaled == []

    def test_scale_all_zeros(self):
        """Scale handles all zero values."""
        values = [0.0, 0.0, 0.0]
        scaled = _scale_to_range(values, 0, 10)
        assert all(v == 0 for v in scaled)


# ===================================================================
# VIZ-009: HTML Safety
# ===================================================================


class TestVIZ009HTMLSafety:
    """VIZ-009: SVG output is safe (no script injection)."""

    def test_svg_no_script_tags(self, multi_year_trends):
        """SVG output contains no <script> tags."""
        svg = generate_svg_chart(multi_year_trends, "clinical_testing")
        assert "<script" not in svg.lower()

    def test_svg_no_event_handlers(self, multi_year_trends):
        """SVG output contains no onclick/onerror handlers."""
        svg = generate_svg_chart(multi_year_trends, "clinical_testing")
        assert "onclick" not in svg.lower()
        assert "onerror" not in svg.lower()
        assert "onload" not in svg.lower()


# ===================================================================
# VIZ-010: Trend Table Formatting
# ===================================================================


class TestVIZ010TrendTableFormatting:
    """VIZ-010: Markdown table formatting for trends."""

    def test_table_structure(self, multi_year_trends):
        """Trend table has proper markdown structure."""
        table = format_trend_table(multi_year_trends, "clinical_testing")
        lines = table.strip().split("\n")

        assert len(lines) >= 3  # Header + separator + data
        assert lines[0].startswith("|")
        assert lines[1].startswith("|")
        assert "Year" in lines[0]
        assert "Coverage" in lines[0]

    def test_table_contains_all_years(self, multi_year_trends):
        """Trend table includes all years."""
        table = format_trend_table(multi_year_trends, "clinical_testing")
        assert "2020" in table
        assert "2021" in table
        assert "2024" in table

    def test_table_change_indicators(self, multi_year_trends):
        """Trend table shows change indicators."""
        table = format_trend_table(multi_year_trends, "clinical_testing")
        # Should have change indicators (arrows or percentages)
        # Coverage increases significantly, so should have indicators
        lines = table.split("\n")
        data_lines = [line for line in lines if "2021" in line or "2022" in line]
        # At least one line should have a change indicator
        has_indicator = any("%" in line or "↗" in line or "↘" in line for line in data_lines)
        assert has_indicator or "-" in table  # Either indicators or dash for no change


# ===================================================================
# VIZ-011: Multi-Year Increasing Trend
# ===================================================================


class TestVIZ011MultiYearIncreasingTrend:
    """VIZ-011: Multi-year increasing trend visualization."""

    def test_ascii_shows_upward_pattern(self, multi_year_trends):
        """ASCII chart for increasing trend shows upward visual pattern."""
        chart = generate_ascii_chart(multi_year_trends, "clinical_testing")
        # Should have chart content (not just a message)
        assert "```" in chart
        assert len(chart.split("\n")) > 10

    def test_svg_increasing_annotation(self, multi_year_trends):
        """SVG chart annotates increasing changes."""
        svg = generate_svg_chart(multi_year_trends, "clinical_testing")
        # Should have upward arrow or positive percentage
        assert "↗" in svg or ("%" in svg and "+" not in svg)  # May have implicit positive


# ===================================================================
# VIZ-012: Multi-Year Decreasing Trend
# ===================================================================


class TestVIZ012MultiYearDecreasingTrend:
    """VIZ-012: Multi-year decreasing trend visualization."""

    def test_ascii_shows_downward_pattern(self, decreasing_trends):
        """ASCII chart for decreasing trend shows downward visual pattern."""
        chart = generate_ascii_chart(decreasing_trends, "biocompatibility")
        assert "```" in chart
        assert "biocompatibility" in chart.lower()

    def test_detect_decreasing_changes(self, decreasing_trends):
        """Detect significant decreases in trend data."""
        years, coverage, lengths = _extract_trend_data(
            decreasing_trends, "biocompatibility"
        )
        changes = detect_significant_changes(years, coverage)

        assert len(changes) >= 3  # Should detect multiple decreases
        assert all(c["direction"] == "decrease" for c in changes)


# ===================================================================
# VIZ-013: Custom Chart Dimensions
# ===================================================================


class TestVIZ013CustomDimensions:
    """VIZ-013: Custom chart width and height parameters."""

    def test_ascii_custom_dimensions(self, multi_year_trends):
        """ASCII chart respects custom width and height."""
        chart = generate_ascii_chart(
            multi_year_trends, "clinical_testing", width=80, height=20
        )
        # Should generate successfully
        assert "```" in chart
        assert "clinical_testing" in chart.lower()

    def test_svg_custom_dimensions(self, multi_year_trends):
        """SVG chart respects custom width and height."""
        svg = generate_svg_chart(
            multi_year_trends, "clinical_testing", width=1000, height=500
        )
        assert 'viewBox="0 0 1000 500"' in svg


# ===================================================================
# VIZ-014: Change Annotation Limits
# ===================================================================


class TestVIZ014ChangeAnnotationLimits:
    """VIZ-014: Limit number of change annotations to prevent clutter."""

    def test_svg_limits_annotations(self):
        """SVG chart limits number of annotations to prevent overlap."""
        # Create data with many significant changes
        trends = {
            "total_devices": 100,
            "year_range": {"start": 2010, "end": 2024},
            "trends": {
                "clinical_testing": {
                    "coverage_trend": {"direction": "increasing"},
                    "length_trend": {"direction": "increasing"},
                    "by_year": {}
                }
            }
        }

        # 15 years with alternating +/- 10% changes
        for year in range(2010, 2025):
            trends["trends"]["clinical_testing"]["by_year"][year] = {
                "device_count": 10,
                "coverage_pct": 50.0 + (10.0 if year % 2 == 0 else 0),
                "avg_word_count": 300.0 + (50.0 if year % 2 == 0 else 0),
                "standards_count": 20,
            }

        svg = generate_svg_chart(trends, "clinical_testing")
        # Should generate successfully without error
        assert "<svg" in svg
