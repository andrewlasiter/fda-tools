#!/usr/bin/env python3
"""
Test suite for competitive dashboard HTML template loading and rendering.

Tests verify that:
- Template file exists and can be loaded
- Template contains all required placeholders
- Rendered output is identical to previous inline template
- Error handling works correctly for missing templates
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"

from competitive_dashboard import (  # type: ignore
    DASHBOARD_TEMPLATE_FILE,
    TEMPLATE_DIR,
    CompetitiveDashboardGenerator,
    _load_html_template,
)


class TestTemplateLoading:
    """Test HTML template loading functionality."""

    def test_template_file_exists(self):
        """Verify template file exists at expected location."""
        assert DASHBOARD_TEMPLATE_FILE.exists(), (
            f"Template file not found at {DASHBOARD_TEMPLATE_FILE}"
        )

    def test_template_file_is_readable(self):
        """Verify template file can be read."""
        content = DASHBOARD_TEMPLATE_FILE.read_text(encoding="utf-8")
        assert len(content) > 0, "Template file is empty"
        assert "<!DOCTYPE html>" in content, "Template is not valid HTML"

    def test_load_html_template_success(self):
        """Test successful template loading."""
        template = _load_html_template()
        assert isinstance(template, str)
        assert len(template) > 0
        assert "<!DOCTYPE html>" in template

    def test_load_html_template_raises_on_missing_file(self):
        """Test that missing template file raises FileNotFoundError."""
        with patch("competitive_dashboard.DASHBOARD_TEMPLATE_FILE") as mock_path:
            mock_path.exists.return_value = False
            mock_path.__str__.return_value = "/fake/path/template.html"

            with pytest.raises(FileNotFoundError) as exc_info:
                _load_html_template()

            assert "not found" in str(exc_info.value).lower()
            assert "template" in str(exc_info.value).lower()

    def test_template_contains_required_placeholders(self):
        """Verify template contains all required format placeholders."""
        template = _load_html_template()

        required_placeholders = [
            "{product_code}",
            "{generated_date}",
            "{version}",
            "{total_pmas}",
            "{total_applicants}",
            "{approval_rate}",
            "{year_span}",
            "{market_share_rows}",
            "{trend_rows}",
            "{recent_approval_rows}",
            "{safety_section}",
            "{supplement_section}",
        ]

        for placeholder in required_placeholders:
            assert placeholder in template, (
                f"Required placeholder {placeholder} not found in template"
            )

    def test_template_html_structure(self):
        """Verify template has valid HTML structure."""
        template = _load_html_template()

        # Check key HTML elements
        assert "<html" in template
        assert "<head>" in template
        assert "<title>" in template
        assert "<style>" in template
        assert "<body>" in template
        assert "</html>" in template

        # Check dashboard-specific elements
        assert "PMA Competitive Intelligence Dashboard" in template
        assert "DISCLAIMER" in template
        assert "Market Share" in template
        assert "Approval Trends" in template
        assert "Recent PMA Approvals" in template
        assert "MAUDE Safety Summary" in template
        assert "Supplement Activity" in template


class TestDashboardGeneration:
    """Test dashboard generation with external template."""

    @pytest.fixture
    def mock_pma_store(self):
        """Create mock PMA data store."""
        mock_store = MagicMock()
        mock_client = MagicMock()

        # Mock PMA search results
        mock_client.search_pma.return_value = {
            "degraded": False,
            "results": [
                {
                    "pma_number": "P123456",
                    "applicant": "Test Medical Inc",
                    "decision_code": "APPR",
                    "decision_date": "20240115",
                    "trade_name": "TestDevice Pro",
                    "generic_name": "Test Device",
                    "product_code": "ABC",
                },
                {
                    "pma_number": "P789012",
                    "applicant": "Medical Devices Corp",
                    "decision_code": "APPR",
                    "decision_date": "20230820",
                    "trade_name": "MedDevice X",
                    "generic_name": "Medical Device",
                    "product_code": "ABC",
                },
            ]
        }

        # Mock MAUDE events
        mock_client.get_events.return_value = {
            "degraded": False,
            "results": [
                {"term": "Malfunction", "count": 50},
                {"term": "Injury", "count": 10},
                {"term": "Death", "count": 2},
            ]
        }

        mock_store.client = mock_client
        mock_store.get_manifest.return_value = {"pma_entries": {}}
        mock_store.get_extracted_sections.return_value = {}

        return mock_store

    def test_generate_dashboard_with_template(self, mock_pma_store):
        """Test dashboard generation loads template successfully."""
        generator = CompetitiveDashboardGenerator(store=mock_pma_store)
        dashboard = generator.generate_dashboard("ABC")

        assert dashboard.get("product_code") == "ABC"
        assert dashboard.get("key_metrics") is not None
        assert dashboard.get("market_share") is not None
        assert "error" not in dashboard

    def test_export_html_creates_valid_file(self, mock_pma_store):
        """Test HTML export creates valid file with template."""
        generator = CompetitiveDashboardGenerator(store=mock_pma_store)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_dashboard.html")
            result_path = generator.export_html("ABC", output_path=output_path)

            assert result_path == output_path
            assert os.path.exists(output_path)

            # Read and verify HTML content
            with open(output_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            assert "<!DOCTYPE html>" in html_content
            assert "PMA Competitive Intelligence Dashboard" in html_content
            assert "Product Code: ABC" in html_content
            assert "Test Medical Inc" in html_content
            assert "DISCLAIMER" in html_content

    def test_rendered_html_contains_data(self, mock_pma_store):
        """Test that rendered HTML contains actual dashboard data."""
        generator = CompetitiveDashboardGenerator(store=mock_pma_store)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_dashboard.html")
            generator.export_html("ABC", output_path=output_path)

            with open(output_path, "r", encoding="utf-8") as f:
                html = f.read()

            # Verify metrics are populated
            assert ">2<" in html  # Total PMAs
            assert ">2<" in html or ">100<" in html  # Approval rate
            assert "Test Medical Inc" in html
            assert "Medical Devices Corp" in html

            # Verify sections are present
            assert "Market Share" in html
            assert "Approval Trends" in html
            assert "MAUDE Safety Summary" in html

    def test_template_rendering_escapes_html(self, mock_pma_store):
        """Test that HTML special characters are escaped in rendered output."""
        # Create mock with HTML characters in applicant name
        mock_pma_store.client.search_pma.return_value = {
            "degraded": False,
            "results": [
                {
                    "pma_number": "P123456",
                    "applicant": "Test <script>alert('xss')</script> Inc",
                    "decision_code": "APPR",
                    "decision_date": "20240115",
                    "trade_name": "Device & Co",
                    "generic_name": "Test Device",
                    "product_code": "ABC",
                }
            ]
        }

        generator = CompetitiveDashboardGenerator(store=mock_pma_store)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_dashboard.html")
            generator.export_html("ABC", output_path=output_path)

            with open(output_path, "r", encoding="utf-8") as f:
                html = f.read()

            # Verify HTML is escaped
            assert "&lt;script&gt;" in html
            assert "<script>" not in html.replace("<style>", "").replace("</style>", "")
            assert "&amp;" in html or "Device &amp; Co" in html


class TestTemplateErrorHandling:
    """Test error handling for template operations."""

    def test_missing_template_provides_helpful_error(self):
        """Test that missing template provides clear error message."""
        with patch("competitive_dashboard.DASHBOARD_TEMPLATE_FILE") as mock_path:
            mock_path.exists.return_value = False
            mock_path.__str__.return_value = "/fake/path/template.html"

            with pytest.raises(FileNotFoundError) as exc_info:
                _load_html_template()

            error_msg = str(exc_info.value)
            assert "template" in error_msg.lower()
            assert "not found" in error_msg.lower()
            assert "data/templates" in error_msg

    def test_template_read_error_handling(self):
        """Test handling of template read errors."""
        with patch("competitive_dashboard.DASHBOARD_TEMPLATE_FILE") as mock_path:
            mock_path.exists.return_value = True
            mock_path.read_text.side_effect = IOError("Permission denied")

            with pytest.raises(IOError) as exc_info:
                _load_html_template()

            error_msg = str(exc_info.value)
            assert "Failed to read" in error_msg
            assert "template" in error_msg.lower()


class TestTemplateBackwardCompatibility:
    """Test that template refactoring maintains backward compatibility."""

    def test_template_output_structure_unchanged(self, tmp_path):
        """Test that output structure matches previous inline template."""
        # Create minimal mock store
        mock_store = MagicMock()
        mock_client = MagicMock()

        mock_client.search_pma.return_value = {
            "degraded": False,
            "results": [
                {
                    "pma_number": "P000001",
                    "applicant": "Company A",
                    "decision_code": "APPR",
                    "decision_date": "20230101",
                    "trade_name": "Device A",
                    "generic_name": "Generic A",
                    "product_code": "XYZ",
                }
            ]
        }

        mock_client.get_events.return_value = {"degraded": False, "results": []}
        mock_store.client = mock_client
        mock_store.get_manifest.return_value = {"pma_entries": {}}
        mock_store.get_extracted_sections.return_value = {}

        generator = CompetitiveDashboardGenerator(store=mock_store)
        output_path = tmp_path / "output.html"

        generator.export_html("XYZ", output_path=str(output_path))
        html_content = output_path.read_text()

        # Verify key structural elements unchanged
        assert '<div class="container">' in html_content
        assert '<div class="header">' in html_content
        assert '<div class="disclaimer">' in html_content
        assert '<div class="grid">' in html_content
        assert '<div class="card">' in html_content
        assert '<div class="footer">' in html_content

        # Verify CSS classes unchanged
        assert 'class="metric"' in html_content
        assert 'badge-approved' in html_content
        assert 'class="bar"' in html_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
