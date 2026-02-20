"""
Tests for scripts/estar_xml.py

Validates eSTAR XML extraction and generation including XFA parsing,
field mapping, template detection, and XML generation for FDA submission.

Test coverage:
- Template type detection (nIVD, IVD, PreSTAR, legacy)
- XFA field mapping and extraction
- XML parsing and data normalization
- Predicate K-number extraction
- XML generation from project data
- XML escaping and control character filtering
- Project data collection from multiple sources
- Field routing to correct sections

Per 21 CFR 11.10(a), validates software used for electronic records
in FDA submissions.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open

import pytest

# Import the script module
# Package imports configured in conftest.py and pytest.ini

from estar_xml import (  # type: ignore
    detect_template_type,
    parse_xml_data,
    _xml_escape,
    _collect_project_values,
    _build_nivd_xml,
    _detect_template_from_data,
    NIVD_FIELD_MAP,
    IVD_FIELD_MAP,
    PRESTAR_FIELD_MAP,
    LEGACY_FIELD_MAP,
)


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_nivd_xml():
    """Sample nIVD eSTAR XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">
  <xfa:data>
    <root>
      <AdministrativeInformation>
        <ApplicantInformation>
          <ADTextField210>Test Medical Inc</ADTextField210>
          <ADTextField140>John</ADTextField140>
          <ADTextField130>Doe</ADTextField130>
          <ADTextField160>jdoe@testmedical.com</ADTextField160>
          <ADTextField170>555-1234</ADTextField170>
        </ApplicantInformation>
      </AdministrativeInformation>
      <DeviceDescription>
        <Devices>
          <Device>
            <TradeName>Test Catheter Pro</TradeName>
            <Model>TCP-2000</Model>
          </Device>
        </Devices>
        <Description>
          <DDTextField400>A polyurethane catheter for vascular access</DDTextField400>
        </Description>
      </DeviceDescription>
      <Classification>
        <USAKnownClassification>
          <DDTextField517a>DQY</DDTextField517a>
          <DDTextField519>870.1210</DDTextField519>
          <DDTextField518>II</DDTextField518>
        </USAKnownClassification>
      </Classification>
      <IndicationsForUse>
        <Indications>
          <IUTextField141>Indicated for temporary vascular access</IUTextField141>
        </Indications>
      </IndicationsForUse>
      <PredicatesSE>
        <PredicateReference>
          <ADTextField830>K241335</ADTextField830>
          <ADTextField840>Predicate Device Name</ADTextField840>
        </PredicateReference>
      </PredicatesSE>
    </root>
  </xfa:data>
</xfa:datasets>"""


@pytest.fixture
def sample_legacy_xml():
    """Sample legacy format XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">
  <xfa:data>
    <form1>
      <CoverLetter>
        <ApplicantName>Test Medical Inc</ApplicantName>
        <DeviceName>Test Catheter Pro</DeviceName>
        <CommonName>Catheter</CommonName>
      </CoverLetter>
      <FDA3514>
        <ProductCode>DQY</ProductCode>
        <DeviceClass>2</DeviceClass>
        <RegulationNumber>870.1210</RegulationNumber>
      </FDA3514>
      <FDA3881>
        <IndicationsText>Indicated for vascular access</IndicationsText>
      </FDA3881>
    </form1>
  </xfa:data>
</xfa:datasets>"""


@pytest.fixture
def sample_prestar_xml():
    """Sample PreSTAR XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">
  <xfa:data>
    <root>
      <GeneralIntroduction>
        <GITextField110>Form FDA 5064 - PreSTAR</GITextField110>
      </GeneralIntroduction>
      <AdministrativeInformation>
        <ApplicantInformation>
          <ADTextField210>Test Medical Inc</ADTextField210>
        </ApplicantInformation>
      </AdministrativeInformation>
      <SubmissionCharacteristics>
        <SCTextField110>Formal Pre-Submission Meeting</SCTextField110>
      </SubmissionCharacteristics>
      <Questions>
        <QPTextField110>Question 1: Is clinical data required?</QPTextField110>
      </Questions>
    </root>
  </xfa:data>
</xfa:datasets>"""


@pytest.fixture
def project_data_minimal():
    """Minimal project data for XML generation."""
    return {
        "profile": {
            "product_code": "DQY",
            "device_class": "2",
            "regulation_number": "870.1210",
            "trade_name": "Test Device",
            "applicant": "Test Medical Inc",
        },
        "import": {
            "applicant": {
                "applicant_name": "Test Medical Inc",
                "email": "test@example.com",
                "phone": "555-1234",
            },
            "classification": {
                "device_trade_name": "Test Device",
                "product_code": "DQY",
                "device_class": "2",
                "regulation_number": "870.1210",
            },
            "indications_for_use": {
                "indications_for_use": "Indicated for vascular access",
            },
            "predicates": [
                {"k_number": "K241335", "device_name": "Predicate Device"}
            ],
        },
        "drafts": {},
    }


# ============================================================================
# Template Detection Tests
# ============================================================================


class TestTemplateDetection:
    """Test suite for eSTAR template detection."""

    def test_detect_nivd_template_by_form_id(self):
        """Test nIVD template detected by Form FDA 4062."""
        xml = '<root>Form FDA 4062 - nIVD eSTAR</root>'

        template_type = detect_template_type(xml)

        assert template_type == "nIVD"

    def test_detect_ivd_template_by_form_id(self):
        """Test IVD template detected by Form FDA 4078."""
        xml = '<root>Form FDA 4078 - IVD eSTAR</root>'

        template_type = detect_template_type(xml)

        assert template_type == "IVD"

    def test_detect_prestar_template_by_form_id(self):
        """Test PreSTAR template detected by Form FDA 5064."""
        xml = '<root>Form FDA 5064 - PreSTAR</root>'

        template_type = detect_template_type(xml)

        assert template_type == "PreSTAR"

    def test_detect_legacy_template(self):
        """Test legacy template detected by form1 and CoverLetter."""
        xml = '<form1><CoverLetter>Test</CoverLetter></form1>'

        template_type = detect_template_type(xml)

        assert template_type == "legacy"

    def test_detect_ivd_by_unique_sections(self):
        """Test IVD template detected by IVD-specific sections."""
        xml = '<root><AssayInstrumentInfo>Test</AssayInstrumentInfo></root>'

        template_type = detect_template_type(xml)

        assert template_type == "IVD"

    def test_detect_prestar_by_unique_sections(self):
        """Test PreSTAR detected by PreSTAR-specific sections."""
        xml = '<root><SubmissionCharacteristics>Test</SubmissionCharacteristics></root>'

        template_type = detect_template_type(xml)

        assert template_type == "PreSTAR"

    def test_detect_nivd_default_for_root_element(self):
        """Test nIVD as default for <root> format."""
        xml = '<root><DeviceDescription>Test</DeviceDescription></root>'

        template_type = detect_template_type(xml)

        assert template_type == "nIVD"


# ============================================================================
# XML Parsing Tests
# ============================================================================


class TestXMLParsing:
    """Test suite for XML parsing and data extraction."""

    def test_parse_nivd_xml_extracts_fields(self, sample_nivd_xml):
        """Test parsing nIVD XML extracts all fields correctly."""
        result = parse_xml_data(sample_nivd_xml)

        # Check metadata
        assert result["metadata"]["template_type"] == "nIVD"
        assert result["metadata"]["source_format"] == "xfa_xml"

        # Check applicant data
        assert result["applicant"]["applicant_name"] == "Test Medical Inc"
        assert result["applicant"]["contact_first_name"] == "John"
        assert result["applicant"]["contact_last_name"] == "Doe"
        assert result["applicant"]["email"] == "jdoe@testmedical.com"
        assert result["applicant"]["phone"] == "555-1234"

        # Check classification data
        assert result["classification"]["device_trade_name"] == "Test Catheter Pro"
        assert result["classification"]["device_model"] == "TCP-2000"
        assert result["classification"]["product_code"] == "DQY"
        assert result["classification"]["regulation_number"] == "870.1210"
        assert result["classification"]["device_class"] == "II"

        # Check IFU
        assert "temporary vascular access" in result["indications_for_use"]["indications_for_use"]

        # Check sections
        assert "polyurethane catheter" in result["sections"]["device_description_text"]

    def test_parse_legacy_xml_extracts_fields(self, sample_legacy_xml):
        """Test parsing legacy XML extracts all fields correctly."""
        result = parse_xml_data(sample_legacy_xml)

        assert result["metadata"]["template_type"] == "legacy"
        assert result["applicant"]["applicant_name"] == "Test Medical Inc"
        assert result["classification"]["device_trade_name"] == "Test Catheter Pro"
        assert result["classification"]["product_code"] == "DQY"

    def test_parse_xml_extracts_predicates(self, sample_nivd_xml):
        """Test predicate K-numbers extracted from XML."""
        result = parse_xml_data(sample_nivd_xml)

        assert len(result["predicates"]) > 0
        k_numbers = [p["k_number"] for p in result["predicates"]]
        assert "K241335" in k_numbers

    def test_parse_xml_handles_missing_fields_gracefully(self):
        """Test parsing handles missing fields without errors."""
        minimal_xml = """<?xml version="1.0"?>
        <xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">
          <xfa:data>
            <root>
              <DeviceDescription>
                <Description>
                  <DDTextField400>Test</DDTextField400>
                </Description>
              </DeviceDescription>
            </root>
          </xfa:data>
        </xfa:datasets>"""

        result = parse_xml_data(minimal_xml)

        # Should not crash, just have empty sections
        assert result is not None
        assert "sections" in result


# ============================================================================
# XML Escaping Tests
# ============================================================================


class TestXMLEscaping:
    """Test suite for XML character escaping."""

    def test_xml_escape_basic_entities(self):
        """Test basic XML entity escaping."""
        text = 'Test & <text> with "quotes" and \'apostrophes\''

        result = _xml_escape(text)

        # Both &apos; and &#x27; are valid XML encodings for single quote
        assert '&amp;' in result
        assert '&lt;text&gt;' in result
        assert '&quot;quotes&quot;' in result
        assert ('&apos;apostrophes&apos;' in result or '&#x27;apostrophes&#x27;' in result)

    def test_xml_escape_filters_control_characters(self):
        """Test control characters filtered out."""
        # Include control characters (U+0001, U+0002) but keep tab/newline
        text = "Normal\x01text\x02with\ttabs\nand newlines"

        result = _xml_escape(text)

        # Control chars removed, tab/newline preserved
        assert "\x01" not in result
        assert "\x02" not in result
        assert "\t" in result
        assert "\n" in result
        assert "Normal" in result
        assert "text" in result

    def test_xml_escape_handles_none_and_empty(self):
        """Test XML escape handles None and empty strings."""
        assert _xml_escape(None) == ""
        assert _xml_escape("") == ""

    def test_xml_escape_preserves_valid_whitespace(self):
        """Test valid whitespace (tab, newline, carriage return) preserved."""
        text = "Line 1\nLine 2\r\nTabbed\tText"

        result = _xml_escape(text)

        assert "\n" in result
        assert "\r" in result
        assert "\t" in result


# ============================================================================
# Project Data Collection Tests
# ============================================================================


class TestProjectDataCollection:
    """Test suite for project data collection from multiple sources."""

    def test_collect_values_from_import_data(self, project_data_minimal):
        """Test values collected from import_data with correct priority."""
        values = _collect_project_values(project_data_minimal)

        assert values["applicant_name"] == "Test Medical Inc"
        assert values["device_trade_name"] == "Test Device"
        assert values["product_code"] == "DQY"
        assert values["device_class"] == "2"

    def test_collect_values_handles_predicates(self, project_data_minimal):
        """Test predicate list collected and formatted."""
        values = _collect_project_values(project_data_minimal)

        assert len(values["predicates"]) == 1
        assert values["predicates"][0]["k_number"] == "K241335"

    def test_collect_values_with_drafts(self, project_data_minimal):
        """Test draft content takes priority for sections."""
        project_data_minimal["drafts"] = {
            "device-description": "Draft device description content",
            "se-discussion": "Draft SE discussion content",
        }

        values = _collect_project_values(project_data_minimal)

        assert values["draft_device_description"] == "Draft device description content"
        assert values["draft_se_discussion"] == "Draft SE discussion content"

    def test_collect_values_handles_list_product_code(self):
        """Test product code extracted from list format."""
        data = {
            "profile": {"product_code": ["DQY", "MAX"]},
            "import": {},
            "drafts": {},
        }

        values = _collect_project_values(data)

        # Should extract first product code
        assert values["product_code"] == "DQY"

    def test_collect_values_with_presub_metadata(self):
        """Test PreSTAR fields collected from presub_metadata."""
        data = {
            "profile": {},
            "import": {},
            "drafts": {},
            "presub_metadata": {
                "meeting_type": "formal",
                "regulatory_pathway": "510k",
                "question_count": 3,
                "questions_generated": ["Q01", "Q02"],
                "device_description": "Test device for presub",
                "intended_use": "Test intended use",
            },
        }

        # Mock question bank file
        with patch("builtins.open", mock_open(read_data='{"questions": []}')):
            with patch("os.path.exists", return_value=False):
                values = _collect_project_values(data)

        assert "Formal Pre-Submission Meeting" in values["presub_characteristics"]
        assert "510(k)" in values["presub_characteristics"]
        assert "Number of Questions: 3" in values["presub_characteristics"]


# ============================================================================
# XML Generation Tests
# ============================================================================


class TestXMLGeneration:
    """Test suite for XML generation."""

    def test_generate_nivd_xml_structure(self, project_data_minimal):
        """Test nIVD XML generated with correct structure."""
        xml = _build_nivd_xml(project_data_minimal)

        # Verify XML declaration
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert '<xfa:datasets' in xml
        assert '</xfa:datasets>' in xml

        # Verify major sections present
        assert '<AdministrativeInformation>' in xml
        assert '<DeviceDescription>' in xml
        assert '<IndicationsForUse>' in xml
        assert '<Classification>' in xml
        assert '<PredicatesSE>' in xml

    def test_generated_xml_includes_field_values(self, project_data_minimal):
        """Test generated XML includes actual field values."""
        xml = _build_nivd_xml(project_data_minimal)

        assert "Test Medical Inc" in xml
        assert "Test Device" in xml
        assert "DQY" in xml
        assert "870.1210" in xml
        assert "K241335" in xml

    def test_generated_xml_escapes_special_characters(self):
        """Test generated XML properly escapes special characters."""
        data = {
            "profile": {},
            "import": {
                "applicant": {"applicant_name": "Test & Medical <Corp>"},
                "classification": {},
                "indications_for_use": {},
                "predicates": [],
            },
            "drafts": {},
        }

        xml = _build_nivd_xml(data)

        assert "Test &amp; Medical &lt;Corp&gt;" in xml
        assert "Test & Medical <Corp>" not in xml

    def test_detect_template_from_data_ivd_panel(self):
        """Test IVD template auto-detected from IVD review panel."""
        data = {
            "profile": {"review_panel": "CH"},  # Chemistry = IVD
            "import": {},
        }

        template_type = _detect_template_from_data(data)

        assert template_type == "IVD"

    def test_detect_template_from_data_ivd_regulation(self):
        """Test IVD template auto-detected from 862-864 regulation."""
        data = {
            "profile": {"regulation_number": "862.1234"},
            "import": {},
        }

        template_type = _detect_template_from_data(data)

        assert template_type == "IVD"

    def test_detect_template_from_data_nivd_default(self):
        """Test nIVD as default template for non-IVD devices."""
        data = {
            "profile": {"review_panel": "CV"},  # Cardiovascular = not IVD
            "import": {},
        }

        template_type = _detect_template_from_data(data)

        assert template_type == "nIVD"


# ============================================================================
# Field Mapping Tests
# ============================================================================


class TestFieldMappings:
    """Test suite for field mapping dictionaries."""

    def test_nivd_field_map_has_required_fields(self):
        """Test nIVD field map contains all required fields."""
        required_fields = [
            "ADTextField210",  # Applicant name
            "DDTextField517a",  # Product code
            "IUTextField141",  # Indications
            "ADTextField830",  # Predicate K-number
        ]

        for field_id in required_fields:
            assert field_id in NIVD_FIELD_MAP

    def test_ivd_field_map_includes_ivd_specific_fields(self):
        """Test IVD field map includes IVD-specific fields."""
        ivd_specific = [
            "DDTextField340",  # Instrument name
            "APTextField110",  # Analytical performance
            "CSTextField110",  # Clinical studies
        ]

        for field_id in ivd_specific:
            assert field_id in IVD_FIELD_MAP

    def test_prestar_field_map_includes_prestar_fields(self):
        """Test PreSTAR field map includes PreSTAR-specific fields."""
        prestar_specific = [
            "SCTextField110",  # Submission characteristics
            "QPTextField110",  # Questions
        ]

        for field_id in prestar_specific:
            assert field_id in PRESTAR_FIELD_MAP

    def test_legacy_field_map_has_semantic_names(self):
        """Test legacy field map uses semantic element names."""
        semantic_fields = [
            "applicantname",
            "productcode",
            "devicename",
            "indicationstext",
        ]

        for field_name in semantic_fields:
            assert field_name in LEGACY_FIELD_MAP


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for full workflows."""

    def test_round_trip_parse_and_generate(self, sample_nivd_xml):
        """Test parsing XML and regenerating produces similar structure."""
        # Parse original XML
        parsed_data = parse_xml_data(sample_nivd_xml)

        # Create project structure
        project_data = {
            "import": {
                "applicant": parsed_data["applicant"],
                "classification": parsed_data["classification"],
                "indications_for_use": parsed_data["indications_for_use"],
                "sections": parsed_data["sections"],
                "predicates": parsed_data["predicates"],
            },
            "profile": {},
            "drafts": {},
        }

        # Generate new XML
        generated_xml = _build_nivd_xml(project_data)

        # Verify key data preserved
        assert "Test Medical Inc" in generated_xml
        assert "Test Catheter Pro" in generated_xml
        assert "DQY" in generated_xml
        assert "K241335" in generated_xml


# ============================================================================
# Pytest Markers
# ============================================================================

pytestmark = [
    pytest.mark.unit,
    pytest.mark.scripts,
]
