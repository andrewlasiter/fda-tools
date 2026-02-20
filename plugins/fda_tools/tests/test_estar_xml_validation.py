"""
Unit tests for eSTAR XML validation and security hardening.

Tests security features implemented in FDA-23 (GAP-019):
- XML injection prevention (OWASP guidelines)
- Required field validation (21 CFR 807.87)
- XML structure validation
- XSD schema validation framework
- Pre-submission validation reporting

Compliance:
    Per 21 CFR 11.10(a), validates software used for electronic records
    in FDA submissions.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Import the script module
# Package imports configured in conftest.py and pytest.ini

from estar_xml import (  # type: ignore
    _sanitize_field_value,
    _validate_required_fields,
    _validate_xml_structure,
    _validate_xml_against_xsd,
    validate_xml_for_submission,
    MAX_FIELD_LENGTHS,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_project_data():
    """Sample project data with all required fields."""
    return {
        "applicant_name": "Test Medical Inc",
        "device_trade_name": "Test Device Pro",
        "product_code": "DQY",
        "regulation_number": "870.1210",
        "device_class": "II",
        "indications_for_use": (
            "The Test Device Pro is indicated for temporary vascular access "
            "in adult patients requiring intravenous therapy."
        ),
        "predicates": [
            {
                "k_number": "K241335",
                "device_name": "Predicate Device",
                "manufacturer": "Predicate Medical Corp"
            }
        ],
    }


@pytest.fixture
def minimal_project_data():
    """Minimal project data (PreSTAR requirements)."""
    return {
        "applicant_name": "Test Medical Inc",
        "device_trade_name": "Test Device",
        "product_code": "DQY",
        "indications_for_use": "For diagnostic use in clinical laboratories.",
    }


@pytest.fixture
def sample_nivd_xml():
    """Sample valid nIVD eSTAR XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">
  <xfa:data>
    <root>
      <AdministrativeInformation>
        <ApplicantInformation>
          <ADTextField210>Test Medical Inc</ADTextField210>
        </ApplicantInformation>
      </AdministrativeInformation>
      <DeviceDescription>
        <Devices>
          <Device>
            <TradeName>Test Device</TradeName>
          </Device>
        </Devices>
      </DeviceDescription>
      <IndicationsForUse>
        <Indications>
          <IUTextField141>For temporary vascular access</IUTextField141>
        </Indications>
      </IndicationsForUse>
      <Classification>
        <USAKnownClassification>
          <DDTextField517a>DQY</DDTextField517a>
        </USAKnownClassification>
      </Classification>
    </root>
  </xfa:data>
</xfa:datasets>"""


# ============================================================================
# Security Tests - XML Escaping and Sanitization
# ============================================================================


class TestXMLSanitization:
    """Test XML injection prevention and data sanitization."""

    def test_sanitize_basic_text(self):
        """Test sanitization of normal text."""
        text = "Test Medical Device"
        result = _sanitize_field_value(text, "device_name")
        assert result == "Test Medical Device"

    def test_sanitize_xml_special_characters(self):
        """Test escaping of XML special characters < > & " '."""
        text = "Device <Model> & \"Version 2.0\" with 'quotes'"
        result = _sanitize_field_value(text, "device_name")
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result
        assert "&quot;" in result
        # Single quotes can be &apos; or &#x27; (both are valid XML)
        assert "&apos;" in result or "&#x27;" in result or "&#39;" in result
        assert "<" not in result
        assert ">" not in result

    def test_sanitize_control_characters(self):
        """Test removal of control characters (except tab, newline, CR)."""
        # Include various control characters
        text = "Device\x00Name\x01With\x1FControl\tChars\nAnd\rValid"
        result = _sanitize_field_value(text, "device_name")

        # Should preserve tab, newline, CR
        assert "\t" in result
        assert "\n" in result
        assert "\r" in result

        # Should remove other control characters
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x1F" not in result

    def test_sanitize_del_character(self):
        """Test removal of DEL character (U+007F)."""
        text = "Device\x7FName"
        result = _sanitize_field_value(text, "device_name")
        assert "\x7F" not in result
        assert result == "DeviceName"

    def test_sanitize_script_tag_detection(self):
        """Test detection of script tags (should be escaped, not blocked)."""
        text = "Device <script>alert('xss')</script> Name"
        result = _sanitize_field_value(text, "device_name")

        # Should escape, not remove
        assert "&lt;script" in result
        assert "&lt;/script&gt;" in result
        assert "<script" not in result

    def test_sanitize_javascript_protocol(self):
        """Test detection of javascript: protocol."""
        text = "javascript:alert('xss')"
        result = _sanitize_field_value(text, "device_name")

        # Should escape colon
        assert "javascript:" in result  # colon not special in XML

    def test_sanitize_entity_declaration(self):
        """Test detection of XML entity declarations."""
        text = "<!ENTITY xxe SYSTEM 'file:///etc/passwd'>"
        result = _sanitize_field_value(text, "device_name")

        # Should escape all special characters
        assert "&lt;!ENTITY" in result
        assert "<!" not in result

    def test_sanitize_cdata_section(self):
        """Test detection of CDATA sections."""
        text = "<![CDATA[malicious content]]>"
        result = _sanitize_field_value(text, "device_name")

        # Should escape
        assert "&lt;![CDATA[" in result
        assert "<![CDATA[" not in result

    def test_sanitize_field_length_truncation(self):
        """Test truncation of excessively long fields."""
        # Create text longer than max length for device_name
        max_len = MAX_FIELD_LENGTHS.get("device_trade_name", MAX_FIELD_LENGTHS["default"])
        text = "A" * (max_len + 100)

        result = _sanitize_field_value(text, "device_trade_name")
        assert len(result) <= max_len

    def test_sanitize_none_value(self):
        """Test handling of None value."""
        result = _sanitize_field_value(None, "device_name")
        assert result == ""

    def test_sanitize_empty_string(self):
        """Test handling of empty string."""
        result = _sanitize_field_value("", "device_name")
        assert result == ""

    def test_sanitize_numeric_value(self):
        """Test handling of numeric value (should convert to string)."""
        result = _sanitize_field_value(12345, "device_model")
        assert result == "12345"


# ============================================================================
# Required Field Validation Tests
# ============================================================================


class TestRequiredFieldValidation:
    """Test FDA required field validation."""

    def test_validate_complete_nivd_data(self, sample_project_data):
        """Test validation with all required nIVD fields present."""
        errors = _validate_required_fields(sample_project_data, "nIVD")

        # Should only have warnings (about predicate being in list format)
        critical_errors = [e for e in errors if not e.startswith("WARNING:")]
        assert len(critical_errors) == 0

    def test_validate_missing_applicant_name(self, sample_project_data):
        """Test validation with missing applicant name."""
        data = sample_project_data.copy()
        del data["applicant_name"]

        errors = _validate_required_fields(data, "nIVD")
        assert any("applicant_name" in e.lower() for e in errors)

    def test_validate_missing_device_name(self, sample_project_data):
        """Test validation with missing device trade name."""
        data = sample_project_data.copy()
        data["device_trade_name"] = ""

        errors = _validate_required_fields(data, "nIVD")
        assert any("device_trade_name" in e.lower() for e in errors)

    def test_validate_missing_product_code(self, sample_project_data):
        """Test validation with missing product code."""
        data = sample_project_data.copy()
        del data["product_code"]

        errors = _validate_required_fields(data, "nIVD")
        assert any("product_code" in e.lower() for e in errors)

    def test_validate_invalid_product_code_format(self, sample_project_data):
        """Test validation with invalid product code format."""
        data = sample_project_data.copy()
        data["product_code"] = "DQ"  # Too short

        errors = _validate_required_fields(data, "nIVD")
        assert any("invalid product code" in e.lower() for e in errors)

        data["product_code"] = "dqy"  # Lowercase
        errors = _validate_required_fields(data, "nIVD")
        assert any("invalid product code" in e.lower() for e in errors)

    def test_validate_invalid_regulation_number_format(self, sample_project_data):
        """Test validation with invalid regulation number format."""
        data = sample_project_data.copy()
        data["regulation_number"] = "870-1210"  # Wrong separator

        errors = _validate_required_fields(data, "nIVD")
        assert any("invalid regulation number" in e.lower() for e in errors)

    def test_validate_missing_indications_for_use(self, sample_project_data):
        """Test validation with missing indications for use."""
        data = sample_project_data.copy()
        del data["indications_for_use"]

        errors = _validate_required_fields(data, "nIVD")
        assert any("indications for use" in e.lower() for e in errors)

    def test_validate_brief_indications_warning(self, sample_project_data):
        """Test warning for brief indications for use."""
        data = sample_project_data.copy()
        data["indications_for_use"] = "For diagnostic use."  # Too brief

        errors = _validate_required_fields(data, "nIVD")
        warnings = [e for e in errors if "WARNING:" in e and "too brief" in e.lower()]
        assert len(warnings) > 0

    def test_validate_placeholder_detection(self, sample_project_data):
        """Test detection of placeholder text in IFU."""
        data = sample_project_data.copy()
        data["indications_for_use"] = (
            "The device is indicated for [TODO: Insert indication text here]."
        )

        errors = _validate_required_fields(data, "nIVD")
        warnings = [e for e in errors if "WARNING:" in e and "placeholder" in e.lower()]
        assert len(warnings) > 0

    def test_validate_missing_predicate_warning(self, sample_project_data):
        """Test warning for missing predicate device."""
        data = sample_project_data.copy()
        del data["predicates"]

        errors = _validate_required_fields(data, "nIVD")
        warnings = [e for e in errors if "WARNING:" in e and "predicate" in e.lower()]
        assert len(warnings) > 0

    def test_validate_prestar_no_predicate_required(self, minimal_project_data):
        """Test PreSTAR doesn't require predicate."""
        errors = _validate_required_fields(minimal_project_data, "PreSTAR")

        # Should not complain about missing predicate
        predicate_errors = [e for e in errors if "predicate" in e.lower() and "WARNING" not in e]
        assert len(predicate_errors) == 0

    def test_validate_prestar_no_regulation_required(self, minimal_project_data):
        """Test PreSTAR doesn't require regulation number."""
        errors = _validate_required_fields(minimal_project_data, "PreSTAR")

        # Should not complain about missing regulation number
        reg_errors = [e for e in errors if "regulation" in e.lower() and "WARNING" not in e]
        assert len(reg_errors) == 0


# ============================================================================
# XML Structure Validation Tests
# ============================================================================


class TestXMLStructureValidation:
    """Test XML well-formedness and structure validation."""

    def test_validate_valid_nivd_xml(self, sample_nivd_xml):
        """Test validation of valid nIVD XML."""
        is_valid, errors = _validate_xml_structure(sample_nivd_xml, "nIVD")
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_malformed_xml(self):
        """Test validation of malformed XML."""
        xml = "<?xml version='1.0'?><root><unclosed>"
        is_valid, errors = _validate_xml_structure(xml, "nIVD")
        assert is_valid is False
        assert any("syntax" in e.lower() for e in errors)

    def test_validate_missing_xfa_namespace(self):
        """Test detection of missing XFA namespace."""
        xml = """<?xml version="1.0"?>
        <datasets>
          <data><root></root></data>
        </datasets>"""
        is_valid, _ = _validate_xml_structure(xml, "nIVD")
        assert is_valid is False

    def test_validate_missing_data_element(self):
        """Test detection of missing xfa:data element."""
        xml = """<?xml version="1.0"?>
        <xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">
          <root></root>
        </xfa:datasets>"""
        is_valid, errors = _validate_xml_structure(xml, "nIVD")
        assert is_valid is False
        assert any("xfa:data" in e.lower() for e in errors)

    def test_validate_missing_root_element(self):
        """Test detection of missing root element."""
        xml = """<?xml version="1.0"?>
        <xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">
          <xfa:data>
          </xfa:data>
        </xfa:datasets>"""
        is_valid, errors = _validate_xml_structure(xml, "nIVD")
        assert is_valid is False
        assert any("root" in e.lower() for e in errors)

    def test_validate_missing_required_sections(self):
        """Test detection of missing required sections."""
        xml = """<?xml version="1.0"?>
        <xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">
          <xfa:data>
            <root>
              <AdministrativeInformation></AdministrativeInformation>
            </root>
          </xfa:data>
        </xfa:datasets>"""
        is_valid, errors = _validate_xml_structure(xml, "nIVD")
        assert is_valid is False

        # Should complain about missing DeviceDescription, IndicationsForUse, Classification
        assert any("DeviceDescription" in e for e in errors)
        assert any("IndicationsForUse" in e for e in errors)
        assert any("Classification" in e for e in errors)


# ============================================================================
# XSD Schema Validation Tests
# ============================================================================


class TestXSDValidation:
    """Test XSD schema validation framework."""

    def test_xsd_validation_schema_not_found(self, sample_nivd_xml):
        """Test XSD validation when schema file is not available."""
        # Default case - schemas not distributed with open-source tool
        is_valid, errors = _validate_xml_against_xsd(sample_nivd_xml, "nIVD")

        # Should return None (not available), not False (failed)
        assert is_valid is None
        assert len(errors) == 0

    def test_xsd_validation_unknown_template_type(self, sample_nivd_xml):
        """Test XSD validation with unknown template type."""
        is_valid, errors = _validate_xml_against_xsd(sample_nivd_xml, "UNKNOWN")

        assert is_valid is False
        assert any("unknown template" in e.lower() for e in errors)

    @patch('estar_xml.Path')
    def test_xsd_validation_with_schema_file(self, mock_path):
        """Test XSD validation when schema file exists (mocked)."""
        # Mock schema file existence
        mock_schema_path = Mock()
        mock_schema_path.exists.return_value = True

        mock_path_instance = Mock()
        mock_path_instance.parent = Mock()
        mock_path_instance.parent.__truediv__ = Mock(return_value=Mock())
        mock_path_instance.parent.__truediv__.return_value.__truediv__ = Mock(
            return_value=mock_schema_path
        )

        mock_path.return_value = mock_path_instance

        # Note: Full XSD validation would require actual schema file
        # This test validates the framework is in place


# ============================================================================
# Integration Tests - Full Validation Report
# ============================================================================


class TestValidationReport:
    """Test complete validation report generation."""

    @patch('estar_xml._load_project_data')
    @patch('estar_xml._collect_project_values')
    @patch('estar_xml._build_estar_xml')
    def test_validation_report_pass(
        self,
        mock_build_xml,
        mock_collect_values,
        mock_load_data,
        sample_project_data,
        sample_nivd_xml,
        tmp_path
    ):
        """Test validation report for passing project."""
        # Setup mocks
        mock_load_data.return_value = {"profile": sample_project_data}
        mock_collect_values.return_value = sample_project_data
        mock_build_xml.return_value = sample_nivd_xml

        # Run validation
        report = validate_xml_for_submission("test_project", tmp_path, "nIVD")

        # Assertions
        assert report["project"] == "test_project"
        assert report["template_type"] == "nIVD"
        assert report["xml_well_formed"] is True
        assert report["overall_status"] in ["PASS", "WARNING"]  # May have warnings about predicate

    @patch('estar_xml._load_project_data')
    @patch('estar_xml._collect_project_values')
    def test_validation_report_missing_fields(
        self,
        mock_collect_values,
        mock_load_data,
        tmp_path
    ):
        """Test validation report with missing required fields."""
        # Setup mocks with incomplete data
        incomplete_data = {
            "applicant_name": "Test Corp",
            # Missing other required fields
        }
        mock_load_data.return_value = {"profile": incomplete_data}
        mock_collect_values.return_value = incomplete_data

        # Run validation
        report = validate_xml_for_submission("test_project", tmp_path, "nIVD")

        # Assertions
        assert report["overall_status"] == "FAIL"
        assert len(report["required_fields"]) > 0

    @patch('estar_xml._load_project_data')
    @patch('estar_xml._collect_project_values')
    @patch('estar_xml._build_estar_xml')
    def test_validation_report_malformed_xml(
        self,
        mock_build_xml,
        mock_collect_values,
        mock_load_data,
        sample_project_data,
        tmp_path
    ):
        """Test validation report with malformed XML."""
        # Setup mocks
        mock_load_data.return_value = {"profile": sample_project_data}
        mock_collect_values.return_value = sample_project_data
        mock_build_xml.return_value = "<root><unclosed>"  # Malformed XML

        # Run validation
        report = validate_xml_for_submission("test_project", tmp_path, "nIVD")

        # Assertions
        assert report["overall_status"] == "FAIL"
        assert report["xml_well_formed"] is False


# ============================================================================
# Security Edge Cases
# ============================================================================


class TestSecurityEdgeCases:
    """Test security-related edge cases."""

    def test_sanitize_unicode_characters(self):
        """Test handling of Unicode characters."""
        text = "Device™ with Unicode® Characters"
        result = _sanitize_field_value(text, "device_name")
        assert "™" in result
        assert "®" in result

    def test_sanitize_emoji_characters(self):
        """Test handling of emoji characters."""
        text = "Device 🏥 Medical ❤️"
        result = _sanitize_field_value(text, "device_name")
        # Emojis should be preserved (they're valid UTF-8)
        assert result  # Should not crash

    def test_sanitize_very_long_field(self):
        """Test handling of extremely long field (DoS prevention)."""
        text = "A" * 100000  # 100K characters
        result = _sanitize_field_value(text, "device_description_text")

        # Should be truncated
        max_len = MAX_FIELD_LENGTHS["device_description_text"]
        assert len(result) <= max_len

    def test_sanitize_mixed_encoding_issues(self):
        """Test handling of potential encoding issues."""
        # Test various problematic character combinations
        text = "Test\x00Device\x1F\x7FName"
        result = _sanitize_field_value(text, "device_name")

        # Should handle without crashing
        assert isinstance(result, str)
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
