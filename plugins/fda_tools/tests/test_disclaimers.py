"""
Comprehensive tests for disclaimers.py module.

Tests all disclaimer generation functions for CSV, HTML, Markdown, and JSON
output formats, ensuring consistent warning messages and regulatory compliance.

Test Coverage:
    - Core disclaimer text constants
    - CSV header disclaimers
    - HTML banner and footer disclaimers
    - Markdown header disclaimers
    - JSON disclaimers section
    - Context-specific formatters
    - Product code substitution
    - Quality score interpretation
"""

import pytest
from lib import disclaimers


class TestCoreDisclaimers:
    """Test core disclaimer text constants."""

    def test_maude_scope_warning_contains_product_code_placeholder(self):
        """MAUDE warning should have product_code and k_number placeholders."""
        assert "{product_code}" in disclaimers.MAUDE_SCOPE_WARNING
        assert "{k_number}" in disclaimers.MAUDE_SCOPE_WARNING

    def test_maude_scope_warning_has_manual_review_requirement(self):
        """MAUDE warning should mention manual review requirement."""
        assert "manual review" in disclaimers.MAUDE_SCOPE_WARNING.lower() or \
               "manual verification" in disclaimers.MAUDE_SCOPE_WARNING.lower()

    def test_maude_scope_warning_emphasizes_not_device_specific(self):
        """MAUDE warning should emphasize aggregation at product code level."""
        assert "PRODUCT CODE" in disclaimers.MAUDE_SCOPE_WARNING
        assert "NOT device-specific" in disclaimers.MAUDE_SCOPE_WARNING

    def test_enrichment_verification_disclaimer_requires_ra_professional(self):
        """Verification disclaimer should mention RA professionals."""
        assert "Regulatory Affairs" in disclaimers.ENRICHMENT_VERIFICATION_DISCLAIMER

    def test_enrichment_verification_disclaimer_prohibits_direct_use(self):
        """Verification disclaimer should prohibit direct FDA submission use."""
        assert "MUST" in disclaimers.ENRICHMENT_VERIFICATION_DISCLAIMER
        assert "verified" in disclaimers.ENRICHMENT_VERIFICATION_DISCLAIMER.lower()

    def test_cfr_citation_disclaimer_mentions_currency(self):
        """CFR disclaimer should mention checking for most current version."""
        assert "current" in disclaimers.CFR_CITATION_DISCLAIMER.lower()
        assert "ecfr.gov" in disclaimers.CFR_CITATION_DISCLAIMER.lower()

    def test_quality_score_disclaimer_clarifies_not_compliance(self):
        """Quality score disclaimer should clarify it's NOT compliance certification."""
        assert "NOT" in disclaimers.QUALITY_SCORE_DISCLAIMER
        assert "compliance" in disclaimers.QUALITY_SCORE_DISCLAIMER.lower()

    def test_clinical_data_disclaimer_mentions_pre_submission(self):
        """Clinical data disclaimer should reference Pre-Submission meeting."""
        assert "Pre-Submission" in disclaimers.CLINICAL_DATA_DISCLAIMER

    def test_standards_disclaimer_lists_determination_methods(self):
        """Standards disclaimer should list how to determine applicable standards."""
        assert "FDA Recognized Standards" in disclaimers.STANDARDS_DISCLAIMER
        assert "guidance" in disclaimers.STANDARDS_DISCLAIMER.lower()


class TestCSVHeaderDisclaimers:
    """Test CSV header disclaimer generation."""

    def test_csv_header_basic_structure(self):
        """CSV header should be comment lines starting with #."""
        disclaimer = disclaimers.get_csv_header_disclaimer("DQY")
        lines = disclaimer.split("\n")
        assert all(line.startswith("#") or line == "" for line in lines)

    def test_csv_header_includes_product_code(self):
        """CSV header should include provided product code."""
        disclaimer = disclaimers.get_csv_header_disclaimer("DQY")
        assert "DQY" in disclaimer

    def test_csv_header_multiple_product_codes(self):
        """CSV header should handle multiple product codes."""
        disclaimer = disclaimers.get_csv_header_disclaimer("DQY, GEI, OVE")
        assert "DQY, GEI, OVE" in disclaimer

    def test_csv_header_has_maude_limitation(self):
        """CSV header should mention MAUDE data scope limitation."""
        disclaimer = disclaimers.get_csv_header_disclaimer("DQY")
        assert "MAUDE" in disclaimer
        assert "PRODUCT CODE" in disclaimer

    def test_csv_header_has_verification_requirement(self):
        """CSV header should require data verification."""
        disclaimer = disclaimers.get_csv_header_disclaimer("DQY")
        assert "verification" in disclaimer.lower() or "verified" in disclaimer.lower()

    def test_csv_header_has_approved_use_case(self):
        """CSV header should state approved use case."""
        disclaimer = disclaimers.get_csv_header_disclaimer("DQY")
        assert "Research" in disclaimer or "intelligence" in disclaimer

    def test_csv_header_has_prohibited_use_case(self):
        """CSV header should state prohibited use case."""
        disclaimer = disclaimers.get_csv_header_disclaimer("DQY")
        assert "PROHIBITED" in disclaimer or "NOT" in disclaimer


class TestHTMLDisclaimers:
    """Test HTML disclaimer generation."""

    def test_html_banner_is_valid_html_div(self):
        """HTML banner should be a valid div element."""
        banner = disclaimers.get_html_banner_disclaimer()
        assert banner.strip().startswith("<div")
        assert "</div>" in banner

    def test_html_banner_has_inline_styles(self):
        """HTML banner should have inline styles for portability."""
        banner = disclaimers.get_html_banner_disclaimer()
        assert 'style="' in banner
        assert "background-color" in banner

    def test_html_banner_has_warning_emoji(self):
        """HTML banner should have warning emoji for visibility."""
        banner = disclaimers.get_html_banner_disclaimer()
        assert "⚠️" in banner

    def test_html_banner_lists_maude_limitation(self):
        """HTML banner should list MAUDE data limitation."""
        banner = disclaimers.get_html_banner_disclaimer()
        assert "MAUDE" in banner
        assert "PRODUCT CODE" in banner

    def test_html_banner_lists_verification_requirement(self):
        """HTML banner should list verification requirement."""
        banner = disclaimers.get_html_banner_disclaimer()
        assert "Verification Required" in banner or "verified" in banner.lower()

    def test_html_banner_has_approved_prohibited_use_cases(self):
        """HTML banner should list approved and prohibited use cases."""
        banner = disclaimers.get_html_banner_disclaimer()
        assert "APPROVED USE" in banner
        assert "PROHIBITED USE" in banner

    def test_html_footer_is_valid_html_div(self):
        """HTML footer should be a valid div element."""
        footer = disclaimers.get_html_footer_disclaimer()
        assert footer.strip().startswith("<div")
        assert "</div>" in footer

    def test_html_footer_has_regulatory_advice_disclaimer(self):
        """HTML footer should have regulatory advice disclaimer."""
        footer = disclaimers.get_html_footer_disclaimer()
        assert "Regulatory Advice" in footer or "regulatory advice" in footer

    def test_html_footer_lists_data_sources(self):
        """HTML footer should list data sources."""
        footer = disclaimers.get_html_footer_disclaimer()
        assert "openFDA" in footer

    def test_html_footer_has_tool_version(self):
        """HTML footer should show tool version."""
        footer = disclaimers.get_html_footer_disclaimer()
        assert "FDA Predicate Assistant" in footer or "Tool Version" in footer


class TestMarkdownDisclaimers:
    """Test Markdown disclaimer generation."""

    def test_markdown_header_has_h1_title(self):
        """Markdown header should start with H1 title."""
        disclaimer = disclaimers.get_markdown_header_disclaimer("Quality Report")
        assert "# Quality Report" in disclaimer

    def test_markdown_header_has_critical_disclaimers_section(self):
        """Markdown header should have CRITICAL DISCLAIMERS section."""
        disclaimer = disclaimers.get_markdown_header_disclaimer()
        assert "## ⚠️ CRITICAL DISCLAIMERS" in disclaimer

    def test_markdown_header_has_research_use_only(self):
        """Markdown header should state RESEARCH USE ONLY."""
        disclaimer = disclaimers.get_markdown_header_disclaimer()
        assert "RESEARCH USE ONLY" in disclaimer
        assert "NOT FOR DIRECT FDA SUBMISSION" in disclaimer

    def test_markdown_header_has_maude_examples(self):
        """Markdown header should have correct/incorrect MAUDE usage examples."""
        disclaimer = disclaimers.get_markdown_header_disclaimer()
        assert "❌ **INCORRECT:**" in disclaimer
        assert "✅ **CORRECT:**" in disclaimer

    def test_markdown_header_custom_report_type(self):
        """Markdown header should use custom report type."""
        disclaimer = disclaimers.get_markdown_header_disclaimer("Intelligence Report")
        assert "# Intelligence Report" in disclaimer

    def test_markdown_header_lists_verification_items(self):
        """Markdown header should list items requiring verification."""
        disclaimer = disclaimers.get_markdown_header_disclaimer()
        assert "MAUDE event counts" in disclaimer
        assert "CFR citations" in disclaimer
        assert "Standards recommendations" in disclaimer


class TestJSONDisclaimers:
    """Test JSON disclaimers section generation."""

    def test_json_disclaimers_returns_dict(self):
        """JSON disclaimers should return a dictionary."""
        result = disclaimers.get_json_disclaimers_section()
        assert isinstance(result, dict)

    def test_json_disclaimers_has_scope_limitations(self):
        """JSON disclaimers should have scope_limitations section."""
        result = disclaimers.get_json_disclaimers_section()
        assert "scope_limitations" in result
        assert isinstance(result["scope_limitations"], dict)

    def test_json_disclaimers_has_verification_requirements(self):
        """JSON disclaimers should have verification_requirements section."""
        result = disclaimers.get_json_disclaimers_section()
        assert "verification_requirements" in result
        assert "all_enriched_data" in result["verification_requirements"]

    def test_json_disclaimers_has_approved_use_cases_list(self):
        """JSON disclaimers should have list of approved use cases."""
        result = disclaimers.get_json_disclaimers_section()
        assert "approved_use_cases" in result
        assert isinstance(result["approved_use_cases"], list)
        assert len(result["approved_use_cases"]) > 0

    def test_json_disclaimers_has_prohibited_use_cases_list(self):
        """JSON disclaimers should have list of prohibited use cases."""
        result = disclaimers.get_json_disclaimers_section()
        assert "prohibited_use_cases" in result
        assert isinstance(result["prohibited_use_cases"], list)
        assert len(result["prohibited_use_cases"]) > 0

    def test_json_disclaimers_has_quality_assurance(self):
        """JSON disclaimers should have quality_assurance section."""
        result = disclaimers.get_json_disclaimers_section()
        assert "quality_assurance" in result
        assert "data_provenance" in result["quality_assurance"]

    def test_json_disclaimers_has_regulatory_status(self):
        """JSON disclaimers should have regulatory_status field."""
        result = disclaimers.get_json_disclaimers_section()
        assert "regulatory_status" in result
        assert "RESEARCH USE ONLY" in result["regulatory_status"]

    def test_json_disclaimers_has_required_actions_pending(self):
        """JSON disclaimers should list required actions pending."""
        result = disclaimers.get_json_disclaimers_section()
        assert "required_actions_pending" in result
        assert isinstance(result["required_actions_pending"], list)


class TestContextSpecificFormatters:
    """Test context-specific disclaimer formatters."""

    def test_format_maude_disclaimer_substitutes_product_code(self):
        """format_maude_disclaimer_for_device should substitute product_code."""
        result = disclaimers.format_maude_disclaimer_for_device("DQY", "K123456", 1847)
        assert "DQY" in result

    def test_format_maude_disclaimer_substitutes_k_number(self):
        """format_maude_disclaimer_for_device should substitute k_number."""
        result = disclaimers.format_maude_disclaimer_for_device("DQY", "K123456", 1847)
        assert "K123456" in result

    def test_format_maude_disclaimer_preserves_warning_text(self):
        """format_maude_disclaimer_for_device should preserve warning text."""
        result = disclaimers.format_maude_disclaimer_for_device("DQY", "K123456", 1847)
        assert "PRODUCT CODE" in result or "product code" in result

    def test_format_quality_score_high_confidence(self):
        """format_quality_score_disclaimer should show HIGH for score >= 80."""
        result = disclaimers.format_quality_score_disclaimer(87.5)
        assert "87.5/100" in result
        assert "HIGH" in result

    def test_format_quality_score_medium_confidence(self):
        """format_quality_score_disclaimer should show MEDIUM for 60 <= score < 80."""
        result = disclaimers.format_quality_score_disclaimer(65.0)
        assert "65" in result or "65.0" in result
        assert "MEDIUM" in result

    def test_format_quality_score_low_confidence(self):
        """format_quality_score_disclaimer should show LOW for score < 60."""
        result = disclaimers.format_quality_score_disclaimer(42.0)
        assert "42" in result or "42.0" in result
        assert "LOW" in result

    def test_format_quality_score_includes_disclaimer(self):
        """format_quality_score_disclaimer should include quality score disclaimer."""
        result = disclaimers.format_quality_score_disclaimer(87.5)
        assert disclaimers.QUALITY_SCORE_DISCLAIMER in result

    def test_format_quality_score_edge_case_80(self):
        """format_quality_score_disclaimer should show HIGH for exactly 80."""
        result = disclaimers.format_quality_score_disclaimer(80.0)
        assert "HIGH" in result

    def test_format_quality_score_edge_case_60(self):
        """format_quality_score_disclaimer should show MEDIUM for exactly 60."""
        result = disclaimers.format_quality_score_disclaimer(60.0)
        assert "MEDIUM" in result


class TestModuleExports:
    """Test module __all__ exports."""

    def test_all_constants_exported(self):
        """All core disclaimer constants should be in __all__."""
        expected = [
            'MAUDE_SCOPE_WARNING',
            'ENRICHMENT_VERIFICATION_DISCLAIMER',
            'CFR_CITATION_DISCLAIMER',
            'QUALITY_SCORE_DISCLAIMER',
            'CLINICAL_DATA_DISCLAIMER',
            'STANDARDS_DISCLAIMER',
        ]
        for item in expected:
            assert item in disclaimers.__all__

    def test_all_functions_exported(self):
        """All disclaimer functions should be in __all__."""
        expected = [
            'get_csv_header_disclaimer',
            'get_html_banner_disclaimer',
            'get_html_footer_disclaimer',
            'get_markdown_header_disclaimer',
            'get_json_disclaimers_section',
            'format_maude_disclaimer_for_device',
            'format_quality_score_disclaimer',
        ]
        for item in expected:
            assert item in disclaimers.__all__


class TestRegulatoryCompliance:
    """Test compliance with regulatory best practices."""

    def test_all_disclaimers_mention_verification(self):
        """All major disclaimers should mention verification/validation."""
        csv_disclaimer = disclaimers.get_csv_header_disclaimer("DQY")
        html_banner = disclaimers.get_html_banner_disclaimer()
        md_header = disclaimers.get_markdown_header_disclaimer()

        assert "verif" in csv_disclaimer.lower()
        assert "verif" in html_banner.lower()
        assert "verif" in md_header.lower()

    def test_all_disclaimers_prohibit_direct_submission_use(self):
        """All major disclaimers should prohibit direct FDA submission use."""
        csv_disclaimer = disclaimers.get_csv_header_disclaimer("DQY")
        html_banner = disclaimers.get_html_banner_disclaimer()
        md_header = disclaimers.get_markdown_header_disclaimer()

        # Check for prohibition language
        for disclaimer in [csv_disclaimer, html_banner, md_header]:
            has_prohibition = (
                "NOT" in disclaimer or
                "PROHIBIT" in disclaimer or
                "without verification" in disclaimer.lower()
            )
            assert has_prohibition

    def test_maude_disclaimers_emphasize_product_code_aggregation(self):
        """MAUDE disclaimers should emphasize product code level aggregation."""
        csv_disclaimer = disclaimers.get_csv_header_disclaimer("DQY")
        html_banner = disclaimers.get_html_banner_disclaimer()
        md_header = disclaimers.get_markdown_header_disclaimer()

        for disclaimer in [csv_disclaimer, html_banner, md_header]:
            assert "PRODUCT CODE" in disclaimer or "product code" in disclaimer
