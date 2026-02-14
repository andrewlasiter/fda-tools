"""Tests for eSTAR XML parser (estar_xml.py).

Validates import parsing: section detection, product code extraction, predicate finding.
Tests both real eSTAR format (root.* paths) and legacy format (form1.* paths).
"""

import os
import sys
import pytest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from estar_xml import (
    _xml_escape,
    _route_field,
    parse_xml_data,
    detect_template_type,
    FIELD_MAP,
    LEGACY_FIELD_MAP,
    NIVD_FIELD_MAP,
    IVD_FIELD_MAP,
    PRESTAR_FIELD_MAP,
    TEMPLATE_FIELD_MAPS,
    _BASE_FIELD_MAP,
    KNUMBER_PATTERN,
    SECTION_PATTERNS,
)

# Check if XML parsing deps are available (parse_xml_data calls check_dependencies at runtime)
try:
    import pikepdf  # noqa: F401
    from bs4 import BeautifulSoup  # noqa: F401
    from lxml import etree  # noqa: F401
    HAS_XML_DEPS = True
except ImportError:
    HAS_XML_DEPS = False


class TestXMLEscape:
    """Test XML special character escaping."""

    def test_ampersand(self):
        assert _xml_escape("A & B") == "A &amp; B"

    def test_less_than(self):
        assert _xml_escape("A < B") == "A &lt; B"

    def test_greater_than(self):
        assert _xml_escape("A > B") == "A &gt; B"

    def test_double_quote(self):
        assert _xml_escape('A "B"') == "A &quot;B&quot;"

    def test_single_quote(self):
        assert _xml_escape("A 'B'") == "A &apos;B&apos;"

    def test_empty_string(self):
        assert _xml_escape("") == ""

    def test_none(self):
        assert _xml_escape(None) == ""

    def test_multiple_specials(self):
        assert _xml_escape("<a & b>") == "&lt;a &amp; b&gt;"


class TestFieldMapping:
    """Test XFA field name to structured key mapping."""

    def test_all_mapped_fields_have_targets(self):
        for field, target in FIELD_MAP.items():
            assert target, f"Field {field} maps to empty target"

    def test_route_applicant_fields(self):
        result = {
            "applicant": {},
            "classification": {},
            "indications_for_use": {},
            "sections": {},
        }
        _route_field(result, "applicant_name", "ACME Corp")
        assert result["applicant"]["applicant_name"] == "ACME Corp"

    def test_route_classification_fields(self):
        result = {
            "applicant": {},
            "classification": {},
            "indications_for_use": {},
            "sections": {},
        }
        _route_field(result, "product_code", "OVE")
        assert result["classification"]["product_code"] == "OVE"

    def test_route_ifu_fields(self):
        result = {
            "applicant": {},
            "classification": {},
            "indications_for_use": {},
            "sections": {},
        }
        _route_field(result, "indications_for_use", "For spinal fusion")
        assert result["indications_for_use"]["indications_for_use"] == "For spinal fusion"

    def test_route_section_fields(self):
        result = {
            "applicant": {},
            "classification": {},
            "indications_for_use": {},
            "sections": {},
        }
        _route_field(result, "device_description_text", "A fusion device...")
        assert result["sections"]["device_description_text"] == "A fusion device..."

    def test_route_predicate_fields(self):
        result = {
            "applicant": {},
            "classification": {},
            "indications_for_use": {},
            "sections": {},
        }
        _route_field(result, "predicate_k_number", "K192345")
        assert result["classification"]["predicate_k_number"] == "K192345"

    def test_route_contact_first_name(self):
        result = {
            "applicant": {},
            "classification": {},
            "indications_for_use": {},
            "sections": {},
        }
        _route_field(result, "contact_first_name", "John")
        assert result["applicant"]["contact_first_name"] == "John"

    def test_route_device_model(self):
        result = {
            "applicant": {},
            "classification": {},
            "indications_for_use": {},
            "sections": {},
        }
        _route_field(result, "device_model", "Model-X100")
        assert result["classification"]["device_model"] == "Model-X100"


class TestRealFieldMapping:
    """Test template-specific field maps for real eSTAR templates."""

    def test_base_field_map_has_core_fields(self):
        """Base map must include all shared admin/device/IFU fields."""
        assert "ADTextField210" in _BASE_FIELD_MAP  # applicant_name
        assert "DDTextField517a" in _BASE_FIELD_MAP  # product_code
        assert "IUTextField141" in _BASE_FIELD_MAP  # indications_for_use
        assert "ADTextField830" in _BASE_FIELD_MAP  # predicate_k_number
        assert "STTextField110" in _BASE_FIELD_MAP  # sterilization_method
        assert "TradeName" in _BASE_FIELD_MAP  # device_trade_name

    def test_nivd_inherits_base(self):
        """nIVD map must include all base fields plus nIVD-specific."""
        for key in _BASE_FIELD_MAP:
            assert key in NIVD_FIELD_MAP, f"nIVD missing base field: {key}"
        assert "QMTextField110" in NIVD_FIELD_MAP  # nIVD-specific

    def test_ivd_inherits_base(self):
        """IVD map must include all base fields plus IVD-specific."""
        for key in _BASE_FIELD_MAP:
            assert key in IVD_FIELD_MAP, f"IVD missing base field: {key}"
        assert "DDTextField340" in IVD_FIELD_MAP  # IVD-specific
        assert "APTextField110" in IVD_FIELD_MAP  # IVD-specific

    def test_prestar_has_subset(self):
        """PreSTAR map must have admin fields but not predicates."""
        assert "ADTextField210" in PRESTAR_FIELD_MAP  # admin
        assert "DDTextField517a" in PRESTAR_FIELD_MAP  # product code
        assert "ADTextField830" not in PRESTAR_FIELD_MAP  # no predicates
        assert "SCTextField110" in PRESTAR_FIELD_MAP  # PreSTAR-specific

    def test_template_field_maps_dict(self):
        """TEMPLATE_FIELD_MAPS must map all 3 template types."""
        assert "nIVD" in TEMPLATE_FIELD_MAPS
        assert "IVD" in TEMPLATE_FIELD_MAPS
        assert "PreSTAR" in TEMPLATE_FIELD_MAPS

    def test_field_map_is_legacy(self):
        """FIELD_MAP alias must point to LEGACY_FIELD_MAP for backward compat."""
        assert FIELD_MAP is LEGACY_FIELD_MAP


class TestTemplateDetection:
    """Test auto-detection of eSTAR template type from XML content."""

    def test_detect_legacy_format(self):
        xml = '<form1><CoverLetter><ApplicantName>Test</ApplicantName></CoverLetter></form1>'
        assert detect_template_type(xml) == "legacy"

    def test_detect_nivd_by_form_id(self):
        xml = '<root><GeneralIntroduction>Form FDA 4062</GeneralIntroduction></root>'
        assert detect_template_type(xml) == "nIVD"

    def test_detect_ivd_by_form_id(self):
        xml = '<root><GeneralIntroduction>Form FDA 4078</GeneralIntroduction></root>'
        assert detect_template_type(xml) == "IVD"

    def test_detect_prestar_by_form_id(self):
        xml = '<root><GeneralIntroduction>Form FDA 5064</GeneralIntroduction></root>'
        assert detect_template_type(xml) == "PreSTAR"

    def test_detect_ivd_by_section(self):
        xml = '<root><AssayInstrumentInfo><DDTextField340>Test</DDTextField340></AssayInstrumentInfo></root>'
        assert detect_template_type(xml) == "IVD"

    def test_detect_prestar_by_section(self):
        xml = '<root><SubmissionCharacteristics><SCTextField110>Test</SCTextField110></SubmissionCharacteristics></root>'
        assert detect_template_type(xml) == "PreSTAR"

    def test_detect_nivd_by_root_default(self):
        xml = '<root><AdministrativeInformation></AdministrativeInformation></root>'
        assert detect_template_type(xml) == "nIVD"

    def test_detect_legacy_for_unknown(self):
        xml = '<unknown><something>test</something></unknown>'
        assert detect_template_type(xml) == "legacy"


class TestKNumberPatternInParser:
    """Test the K-number pattern used by the parser."""

    def test_finds_knumber(self):
        assert KNUMBER_PATTERN.findall("K192345") == ["K192345"]

    def test_finds_supplement(self):
        assert KNUMBER_PATTERN.findall("K192345/S001") == ["K192345/S001"]

    def test_finds_pnumber(self):
        assert KNUMBER_PATTERN.findall("P190001") == ["P190001"]

    def test_finds_den(self):
        assert KNUMBER_PATTERN.findall("DEN200045") == ["DEN200045"]

    def test_finds_nnumber(self):
        assert KNUMBER_PATTERN.findall("N0012") == ["N0012"]

    def test_multiple_in_text(self):
        text = "Predicates: K192345, K181234, and P190001"
        matches = KNUMBER_PATTERN.findall(text)
        assert len(matches) == 3


class TestSectionDetection:
    """Test section detection patterns used during import."""

    def test_device_description_detected(self):
        assert SECTION_PATTERNS["device_description"].search("Device Description")

    def test_se_discussion_detected(self):
        assert SECTION_PATTERNS["se_discussion"].search("Substantial Equivalence Comparison")

    def test_performance_detected(self):
        assert SECTION_PATTERNS["performance"].search("Performance Testing Summary")

    def test_indications_detected(self):
        assert SECTION_PATTERNS["indications"].search("Indications for Use")

    def test_biocompatibility_detected(self):
        assert SECTION_PATTERNS["biocompatibility"].search("Biocompatibility Testing")


@pytest.mark.skipif(not HAS_XML_DEPS, reason="pikepdf/lxml/bs4 not installed")
class TestParseXMLData:
    """Test parsing of legacy-format XFA XML data."""

    def _make_xml(self, **fields):
        """Build a minimal legacy-format XFA XML string with given fields."""
        parts = ['<?xml version="1.0"?>', '<xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">', '<xfa:data>', '<form1>']

        if "product_code" in fields:
            parts.append(f'<FDA3514><ProductCode>{fields["product_code"]}</ProductCode></FDA3514>')

        if "applicant_name" in fields:
            parts.append(f'<CoverLetter><ApplicantName>{fields["applicant_name"]}</ApplicantName></CoverLetter>')

        if "ifu" in fields:
            parts.append(f'<FDA3881><IndicationsText>{fields["ifu"]}</IndicationsText></FDA3881>')

        if "predicate_knumber" in fields:
            parts.append(f'<SE><PredicateDevice0><KNumber>{fields["predicate_knumber"]}</KNumber></PredicateDevice0></SE>')

        if "description" in fields:
            parts.append(f'<DeviceDescription><DescriptionText>{fields["description"]}</DescriptionText></DeviceDescription>')

        parts.extend(['</form1>', '</xfa:data>', '</xfa:datasets>'])
        return '\n'.join(parts)

    def test_extracts_product_code(self):
        xml = self._make_xml(product_code="OVE")
        result = parse_xml_data(xml)
        assert result["classification"].get("product_code") == "OVE"

    def test_extracts_applicant(self):
        xml = self._make_xml(applicant_name="ACME Medical")
        result = parse_xml_data(xml)
        assert result["applicant"].get("applicant_name") == "ACME Medical"

    def test_extracts_ifu(self):
        xml = self._make_xml(ifu="For intervertebral body fusion")
        result = parse_xml_data(xml)
        assert "intervertebral" in result["indications_for_use"].get("indications_for_use", "")

    def test_extracts_predicate_knumber(self):
        xml = self._make_xml(predicate_knumber="K192345")
        result = parse_xml_data(xml)
        knumbers = [p["k_number"] for p in result["predicates"]]
        assert "K192345" in knumbers

    def test_extracts_device_description(self):
        xml = self._make_xml(description="A PEEK interbody fusion device with titanium endplates for lumbar spine fusion.")
        result = parse_xml_data(xml)
        assert "PEEK" in result["sections"].get("device_description_text", "") or \
               "PEEK" in result.get("raw_fields", {}).get("form1.DeviceDescription.DescriptionText", "")

    def test_metadata_present(self):
        xml = self._make_xml(product_code="OVE")
        result = parse_xml_data(xml)
        assert "metadata" in result
        assert "extracted_at" in result["metadata"]
        assert result["metadata"]["source_format"] == "xfa_xml"

    def test_metadata_includes_template_type(self):
        xml = self._make_xml(product_code="OVE")
        result = parse_xml_data(xml)
        assert result["metadata"]["template_type"] == "legacy"

    def test_empty_xml(self):
        xml = '<?xml version="1.0"?><root></root>'
        result = parse_xml_data(xml)
        assert result["predicates"] == []
        assert result["classification"] == {}

    def test_raw_fields_populated(self):
        xml = self._make_xml(product_code="OVE", applicant_name="Test Corp")
        result = parse_xml_data(xml)
        assert len(result["raw_fields"]) > 0


@pytest.mark.skipif(not HAS_XML_DEPS, reason="pikepdf/lxml/bs4 not installed")
class TestParseRealFormat:
    """Test parsing of real eSTAR format XML data (root.* paths)."""

    def _make_real_xml(self, template_id="FDA 4062", **fields):
        """Build a minimal real-format XFA XML string."""
        parts = [
            '<?xml version="1.0"?>',
            '<xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">',
            '<xfa:data>',
            '<root>',
            f'<GeneralIntroduction><GITextField110>Form {template_id}</GITextField110></GeneralIntroduction>',
        ]

        if "applicant_name" in fields:
            parts.append(
                f'<AdministrativeInformation><ApplicantInformation>'
                f'<ADTextField210>{fields["applicant_name"]}</ADTextField210>'
                f'</ApplicantInformation></AdministrativeInformation>'
            )

        if "product_code" in fields:
            parts.append(
                f'<Classification><USAKnownClassification>'
                f'<DDTextField517a>{fields["product_code"]}</DDTextField517a>'
                f'</USAKnownClassification></Classification>'
            )

        if "ifu" in fields:
            parts.append(
                f'<IndicationsForUse><Indications>'
                f'<IUTextField141>{fields["ifu"]}</IUTextField141>'
                f'</Indications></IndicationsForUse>'
            )

        if "predicate_knumber" in fields:
            parts.append(
                f'<PredicatesSE><PredicateReference>'
                f'<ADTextField830>{fields["predicate_knumber"]}</ADTextField830>'
                f'</PredicateReference></PredicatesSE>'
            )

        if "device_description" in fields:
            parts.append(
                f'<DeviceDescription><Description>'
                f'<DDTextField400>{fields["device_description"]}</DDTextField400>'
                f'</Description></DeviceDescription>'
            )

        if "trade_name" in fields:
            parts.append(
                f'<DeviceDescription><Devices><Device>'
                f'<TradeName>{fields["trade_name"]}</TradeName>'
                f'</Device></Devices></DeviceDescription>'
            )

        if "sterilization" in fields:
            parts.append(
                f'<ReprocSter><Sterility><STMethod>'
                f'<STTextField110>{fields["sterilization"]}</STTextField110>'
                f'</STMethod></Sterility></ReprocSter>'
            )

        parts.extend(['</root>', '</xfa:data>', '</xfa:datasets>'])
        return '\n'.join(parts)

    def test_detects_nivd_template(self):
        xml = self._make_real_xml(template_id="FDA 4062")
        result = parse_xml_data(xml)
        assert result["metadata"]["template_type"] == "nIVD"

    def test_detects_ivd_template(self):
        xml = self._make_real_xml(template_id="FDA 4078")
        result = parse_xml_data(xml)
        assert result["metadata"]["template_type"] == "IVD"

    def test_extracts_applicant_name(self):
        xml = self._make_real_xml(applicant_name="MedDevice Inc")
        result = parse_xml_data(xml)
        assert result["applicant"].get("applicant_name") == "MedDevice Inc"

    def test_extracts_product_code(self):
        xml = self._make_real_xml(product_code="DQY")
        result = parse_xml_data(xml)
        assert result["classification"].get("product_code") == "DQY"

    def test_extracts_ifu(self):
        xml = self._make_real_xml(ifu="For cardiovascular catheterization procedures")
        result = parse_xml_data(xml)
        assert "cardiovascular" in result["indications_for_use"].get("indications_for_use", "")

    def test_extracts_predicate(self):
        xml = self._make_real_xml(predicate_knumber="K201234")
        result = parse_xml_data(xml)
        knumbers = [p["k_number"] for p in result["predicates"]]
        assert "K201234" in knumbers

    def test_extracts_device_description(self):
        xml = self._make_real_xml(device_description="A catheter for vascular access")
        result = parse_xml_data(xml)
        assert "catheter" in result["sections"].get("device_description_text", "")

    def test_extracts_trade_name(self):
        xml = self._make_real_xml(trade_name="CathPro 3000")
        result = parse_xml_data(xml)
        assert result["classification"].get("device_trade_name") == "CathPro 3000"

    def test_extracts_sterilization(self):
        xml = self._make_real_xml(sterilization="Ethylene Oxide (EO)")
        result = parse_xml_data(xml)
        assert result["sections"].get("sterilization_method") == "Ethylene Oxide (EO)"

    def test_raw_fields_use_real_paths(self):
        xml = self._make_real_xml(product_code="GEI")
        result = parse_xml_data(xml)
        # Real format paths include root.Classification...
        found_real_path = any("Classification" in path for path in result["raw_fields"])
        assert found_real_path, "Raw fields should include real eSTAR paths"


@pytest.mark.skipif(not HAS_XML_DEPS, reason="pikepdf/lxml/bs4 not installed")
class TestRoundTrip:
    """Test that generating XML and parsing it back preserves key fields."""

    def test_nivd_round_trip(self):
        from estar_xml import _build_estar_xml
        project_data = {
            "import": {
                "classification": {"product_code": "OVE", "device_trade_name": "FusionMax"},
                "applicant": {"applicant_name": "SpineCorp"},
                "indications_for_use": {"indications_for_use": "For lumbar fusion"},
                "predicates": [{"k_number": "K192345", "device_name": "PredDevice"}],
                "sections": {},
            },
            "query": {},
            "review": {},
            "drafts": {},
        }
        xml = _build_estar_xml(project_data, "nIVD")
        result = parse_xml_data(xml)

        assert result["metadata"]["template_type"] == "nIVD"
        assert result["classification"].get("product_code") == "OVE"
        assert result["applicant"].get("applicant_name") == "SpineCorp"
        assert "lumbar fusion" in result["indications_for_use"].get("indications_for_use", "")
        knumbers = [p["k_number"] for p in result["predicates"]]
        assert "K192345" in knumbers

    def test_legacy_round_trip(self):
        from estar_xml import _build_legacy_xml
        project_data = {
            "import": {
                "classification": {"product_code": "FJL", "device_trade_name": "SteamClean"},
                "applicant": {"applicant_name": "SterilTech"},
                "indications_for_use": {"indications_for_use": "For surgical instrument sterilization"},
                "predicates": [],
                "sections": {},
            },
            "query": {},
            "review": {},
            "drafts": {},
        }
        xml = _build_legacy_xml(project_data, "nIVD")
        result = parse_xml_data(xml)

        assert result["metadata"]["template_type"] == "legacy"
        assert result["classification"].get("product_code") == "FJL"
        assert result["applicant"].get("applicant_name") == "SterilTech"
