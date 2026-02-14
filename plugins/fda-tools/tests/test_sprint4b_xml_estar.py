"""Sprint 4B Tests — XML & eSTAR Completeness

Tests for:
- C-07: estar_xml.py generates XML for Sections 03/04/05
- H-02: Mandatory section completeness check in pre-check/review-simulator
- H-07: Attachment management in assemble/export
- M-11: XML field paths for Sections 05/17 in estar-structure.md
- L-06: Human Factors XML always generated (round-trip support)
"""

import os
import re
import sys
import pytest

# Paths
PLUGIN_ROOT = os.path.join(os.path.dirname(__file__), '..')
SCRIPTS_DIR = os.path.join(PLUGIN_ROOT, 'scripts')
COMMANDS_DIR = os.path.join(PLUGIN_ROOT, 'commands')
AGENTS_DIR = os.path.join(PLUGIN_ROOT, 'agents')
REFERENCES_DIR = os.path.join(PLUGIN_ROOT, 'references')
SKILL_REFS_DIR = os.path.join(PLUGIN_ROOT, 'skills', 'fda-510k-knowledge', 'references')

sys.path.insert(0, SCRIPTS_DIR)

from estar_xml import _build_estar_xml, _build_legacy_xml, _xml_escape


# ===== C-07: XML Section Builders for 03/04/05 =====

class TestXMLSection03Summary:
    """Legacy format: estar_xml.py must generate <Summary> element for Section 03."""

    def _generate(self, drafts=None):
        project_data = {
            "import": {"classification": {}, "applicant": {}, "indications_for_use": {}, "predicates": [], "sections": {}},
            "query": {},
            "review": {},
            "drafts": drafts or {},
        }
        return _build_legacy_xml(project_data, "nIVD")

    def test_summary_element_present(self):
        xml = self._generate()
        assert "<Summary>" in xml
        assert "</Summary>" in xml

    def test_summary_text_populated(self):
        xml = self._generate(drafts={"510k-summary": "This device is substantially equivalent."})
        assert "<SummaryText>" in xml
        assert "substantially equivalent" in xml

    def test_summary_text_empty_when_no_draft(self):
        xml = self._generate()
        assert "<SummaryText></SummaryText>" in xml


class TestXMLSection04TruthfulAccuracy:
    """Legacy format: estar_xml.py must generate <TruthfulAccuracy> element for Section 04."""

    def _generate(self, drafts=None):
        project_data = {
            "import": {"classification": {}, "applicant": {}, "indications_for_use": {}, "predicates": [], "sections": {}},
            "query": {},
            "review": {},
            "drafts": drafts or {},
        }
        return _build_legacy_xml(project_data, "nIVD")

    def test_truthful_accuracy_element_present(self):
        xml = self._generate()
        assert "<TruthfulAccuracy>" in xml
        assert "</TruthfulAccuracy>" in xml

    def test_truthful_accuracy_populated(self):
        xml = self._generate(drafts={"truthful-accuracy": "I certify that all data is accurate."})
        assert "<StatementText>" in xml
        assert "I certify" in xml

    def test_truthful_accuracy_empty_when_no_draft(self):
        xml = self._generate()
        assert "<StatementText></StatementText>" in xml


class TestXMLSection05FinancialCert:
    """Legacy format: estar_xml.py must generate <FinancialCert> element for Section 05."""

    def _generate(self, drafts=None):
        project_data = {
            "import": {"classification": {}, "applicant": {}, "indications_for_use": {}, "predicates": [], "sections": {}},
            "query": {},
            "review": {},
            "drafts": drafts or {},
        }
        return _build_legacy_xml(project_data, "nIVD")

    def test_financial_cert_element_present(self):
        xml = self._generate()
        assert "<FinancialCert>" in xml
        assert "</FinancialCert>" in xml

    def test_financial_cert_populated(self):
        xml = self._generate(drafts={"financial-certification": "No financial conflicts."})
        assert "<CertificationText>" in xml
        assert "No financial conflicts" in xml

    def test_financial_cert_empty_when_no_draft(self):
        xml = self._generate()
        assert "<CertificationText></CertificationText>" in xml


# ===== L-06: Human Factors XML Always Generated =====

class TestXMLHumanFactorsAlwaysPresent:
    """Legacy format: HumanFactors XML element must always be generated (not conditional)."""

    def _generate(self, drafts=None):
        project_data = {
            "import": {"classification": {}, "applicant": {}, "indications_for_use": {}, "predicates": [], "sections": {}},
            "query": {},
            "review": {},
            "drafts": drafts or {},
        }
        return _build_legacy_xml(project_data, "nIVD")

    def test_human_factors_present_without_draft(self):
        """HumanFactors element must exist even when no draft_human-factors.md."""
        xml = self._generate()
        assert "<HumanFactors>" in xml
        assert "</HumanFactors>" in xml

    def test_human_factors_populated_with_draft(self):
        xml = self._generate(drafts={"human-factors": "Usability testing was conducted."})
        assert "<HumanFactors>" in xml
        assert "Usability testing" in xml

    def test_human_factors_empty_element_valid(self):
        """Empty HumanFactors should produce valid element pair."""
        xml = self._generate()
        # Should have opening and closing tags with nothing or only whitespace between
        hf_match = re.search(r'<HumanFactors>(.*?)</HumanFactors>', xml, re.DOTALL)
        assert hf_match is not None
        # Content should be empty or whitespace only (no Description tag if no draft)
        inner = hf_match.group(1).strip()
        assert "<Description>" not in inner


# ===== XML Section Order =====

class TestXMLSectionOrder:
    """Legacy format: Verify all 18 sections appear in the legacy XML."""

    def _generate(self, drafts=None):
        project_data = {
            "import": {"classification": {}, "applicant": {}, "indications_for_use": {}, "predicates": [], "sections": {}},
            "query": {},
            "review": {},
            "drafts": drafts or {},
        }
        return _build_legacy_xml(project_data, "nIVD")

    def test_all_legacy_section_elements_present(self):
        """All legacy eSTAR section XML elements must be present."""
        xml = self._generate()
        expected_elements = [
            "CoverLetter",       # 01
            "FDA3514",           # 02
            "FDA3881",           # IFU
            "Summary",           # 03
            "TruthfulAccuracy",  # 04
            "FinancialCert",     # 05
            "DeviceDescription", # 06
            "SE",                # 07
            "Performance",       # 15
            "Labeling",          # 09
            "Software",          # 13
            "Sterilization",     # 10
            "ShelfLife",         # 11
            "Biocompat",         # 12
            "EMC",               # 14
            "Clinical",          # 16
            "Standards",         # 08
            "HumanFactors",      # 17
        ]
        for elem in expected_elements:
            assert f"<{elem}>" in xml, f"Missing legacy XML element: <{elem}>"
            assert f"</{elem}>" in xml, f"Missing legacy closing tag: </{elem}>"


# ===== M-11: estar-structure.md XML Field Paths =====

class TestEstarStructureXMLPaths:
    """estar-structure.md must have XML field paths for all sections including 05 and 17."""

    @pytest.fixture
    def structure_content(self):
        path = os.path.join(REFERENCES_DIR, 'estar-structure.md')
        with open(path) as f:
            return f.read()

    def test_section_05_xml_path(self, structure_content):
        """Section 05 (Financial Cert) must have XML element mapping."""
        assert "FinancialCert" in structure_content

    def test_section_17_xml_path(self, structure_content):
        """Section 17 (Human Factors) must have XML element mapping."""
        assert "HumanFactors" in structure_content

    def test_all_sections_have_xml_paths(self, structure_content):
        """All 17 content sections (01-17) should have XML element mappings."""
        required_sections = ["01", "02", "03", "04", "05", "06", "07", "08",
                             "09", "10", "11", "12", "13", "14", "15", "16", "17"]
        for section in required_sections:
            # Table has both real and legacy columns; check legacy column still present
            pattern = rf'\|\s*{section}\s*\|.*form1\.'
            assert re.search(pattern, structure_content), \
                f"Section {section} missing legacy path from XML Element Mapping table"

    def test_all_sections_have_real_xml_paths(self, structure_content):
        """All sections should have real eSTAR XML paths in the mapping table."""
        # Real XML paths use root.* notation
        real_path_sections = {
            "01": "AdministrativeInformation",
            "02": "Classification",
            "03": "AdministrativeDocumentation",
            "06": "DeviceDescription",
            "07": "PredicatesSE",
            "08": "AdministrativeDocumentation",
            "09": "Labeling",
            "10": "ReprocSter",
            "11": "ReprocSter",
            "12": "Biocompatibility",
            "13": "SoftwareCyber",
            "14": "EMCWireless",
            "15": "PerformanceTesting",
            "16": "PerformanceTesting",
        }
        for section, real_elem in real_path_sections.items():
            pattern = rf'\|\s*{section}\s*\|.*{real_elem}'
            assert re.search(pattern, structure_content), \
                f"Section {section} missing real path '{real_elem}' in mapping table"


class TestEstarStructureSkillMirror:
    """Skill mirror of estar-structure.md must also have XML paths."""

    @pytest.fixture
    def skill_content(self):
        path = os.path.join(SKILL_REFS_DIR, 'estar-structure.md')
        with open(path) as f:
            return f.read()

    def test_skill_mirror_has_xml_mapping_table(self, skill_content):
        """Skill mirror must have Section Number to XML Element Mapping table."""
        assert "Section Number to XML Element Mapping" in skill_content \
            or "XML Element Root" in skill_content

    def test_skill_mirror_has_section_17(self, skill_content):
        """Skill mirror must include Section 17 (Human Factors)."""
        assert "HumanFactors" in skill_content

    def test_skill_mirror_has_section_05(self, skill_content):
        """Skill mirror must include Section 05 (FinancialCert)."""
        assert "FinancialCert" in skill_content


# ===== H-02: Mandatory Section Completeness Check =====

class TestPreCheckMandatorySections:
    """pre-check.md must include mandatory eSTAR section completeness check."""

    @pytest.fixture
    def precheck_content(self):
        path = os.path.join(COMMANDS_DIR, 'pre-check.md')
        with open(path) as f:
            return f.read()

    def test_mandatory_sections_check_present(self, precheck_content):
        """pre-check.md must have eSTAR mandatory section completeness check."""
        assert "eSTAR Mandatory Section Completeness" in precheck_content \
            or "mandatory_sections" in precheck_content

    def test_mandatory_section_list_complete(self, precheck_content):
        """Check references all always-required sections."""
        required_sections = ["Cover Letter", "510(k) Summary", "Truthful",
                             "Device Description", "SE Comparison", "Labeling",
                             "Performance"]
        for section in required_sections:
            assert section in precheck_content, \
                f"Mandatory section '{section}' not in pre-check completeness list"

    def test_mandatory_section_files_listed(self, precheck_content):
        """Check lists the expected draft file for each mandatory section."""
        expected_files = [
            "draft_cover-letter.md",
            "draft_510k-summary.md",
            "draft_truthful-accuracy.md",
            "draft_device-description.md",
            "draft_se-discussion.md",
            "draft_labeling.md",
            "draft_performance-summary.md",
        ]
        for f in expected_files:
            assert f in precheck_content, \
                f"Expected draft file '{f}' not in pre-check mandatory sections"


class TestReviewSimulatorMandatorySections:
    """review-simulator.md must include mandatory section completeness check."""

    @pytest.fixture
    def simulator_content(self):
        path = os.path.join(AGENTS_DIR, 'review-simulator.md')
        with open(path) as f:
            return f.read()

    def test_mandatory_section_table_present(self, simulator_content):
        """review-simulator must have mandatory section completeness table."""
        assert "eSTAR Mandatory Section Completeness" in simulator_content

    def test_section_numbers_present(self, simulator_content):
        """Table must include the always-required section numbers."""
        for num in ["01", "03", "04", "06", "07", "09", "15"]:
            assert num in simulator_content


# ===== H-07: Attachment Management =====

class TestAssembleAttachmentSupport:
    """assemble.md must support --attach flag for file attachments."""

    @pytest.fixture
    def assemble_content(self):
        path = os.path.join(COMMANDS_DIR, 'assemble.md')
        with open(path) as f:
            return f.read()

    def test_attach_flag_documented(self, assemble_content):
        """assemble.md must document --attach flag."""
        assert "--attach" in assemble_content

    def test_attachment_processing_step(self, assemble_content):
        """assemble.md must have attachment processing step."""
        assert "Process Attachments" in assemble_content \
            or "attachments.json" in assemble_content

    def test_attachment_json_format(self, assemble_content):
        """assemble.md must describe attachments.json format."""
        assert "attachments.json" in assemble_content

    def test_attachment_size_warning(self, assemble_content):
        """assemble.md must warn about 100 MB limit."""
        assert "100 MB" in assemble_content


class TestExportAttachmentSupport:
    """export.md must include attachments in ZIP export."""

    @pytest.fixture
    def export_content(self):
        path = os.path.join(COMMANDS_DIR, 'export.md')
        with open(path) as f:
            return f.read()

    def test_attach_flag_documented(self, export_content):
        """export.md must document --attach flag."""
        assert "--attach" in export_content

    def test_attachments_json_included_in_zip(self, export_content):
        """export.md must include attachments from attachments.json in ZIP."""
        assert "attachments.json" in export_content

    def test_attachments_dir_scanned(self, export_content):
        """export.md must scan attachments/ directory."""
        assert "attachments/" in export_content or "att_dir" in export_content


# ===== Submission Assembler Consistency Checks =====

class TestSubmissionAssemblerConsistency:
    """submission-assembler.md must have 11 consistency checks including section map alignment."""

    @pytest.fixture
    def assembler_content(self):
        path = os.path.join(AGENTS_DIR, 'submission-assembler.md')
        with open(path) as f:
            return f.read()

    def test_has_11_consistency_checks(self, assembler_content):
        """Assembler must reference 11 consistency checks."""
        assert "11" in assembler_content
        assert "eSTAR Section Map Alignment" in assembler_content

    def test_section_map_check_covers_all_sections(self, assembler_content):
        """Section map alignment check must list all 17 draft-to-folder mappings."""
        expected_drafts = [
            "draft_cover-letter.md",
            "draft_510k-summary.md",
            "draft_truthful-accuracy.md",
            "draft_financial-certification.md",
            "draft_device-description.md",
            "draft_se-discussion.md",
            "draft_doc.md",
            "draft_labeling.md",
            "draft_sterilization.md",
            "draft_shelf-life.md",
            "draft_biocompatibility.md",
            "draft_software.md",
            "draft_emc-electrical.md",
            "draft_performance-summary.md",
            "draft_clinical.md",
            "draft_human-factors.md",
        ]
        for draft in expected_drafts:
            assert draft in assembler_content, \
                f"Assembler section map check missing: {draft}"

    def test_cover_sheet_in_section_map(self, assembler_content):
        """Section map must include cover_sheet.md → 02_CoverSheet/."""
        assert "cover_sheet.md" in assembler_content
        assert "02_CoverSheet" in assembler_content


# ===== XML Escape in New Sections =====

class TestXMLEscapeInNewSections:
    """Verify XML escaping works in legacy section content."""

    def _generate(self, drafts=None):
        project_data = {
            "import": {"classification": {}, "applicant": {}, "indications_for_use": {}, "predicates": [], "sections": {}},
            "query": {},
            "review": {},
            "drafts": drafts or {},
        }
        return _build_legacy_xml(project_data, "nIVD")

    def test_summary_escapes_ampersand(self):
        xml = self._generate(drafts={"510k-summary": "Device A & Device B"})
        assert "Device A &amp; Device B" in xml

    def test_truthful_accuracy_escapes_less_than(self):
        xml = self._generate(drafts={"truthful-accuracy": "Score < 5"})
        assert "Score &lt; 5" in xml

    def test_financial_cert_escapes_quotes(self):
        xml = self._generate(drafts={"financial-certification": 'No "conflicts"'})
        assert "No &quot;conflicts&quot;" in xml


# ===== Real eSTAR Format Tests =====

class TestRealXMLGeneration:
    """Verify _build_estar_xml produces real eSTAR format (root.* paths)."""

    def _generate(self, template="nIVD", drafts=None, import_data=None):
        project_data = {
            "import": import_data or {
                "classification": {}, "applicant": {}, "indications_for_use": {},
                "predicates": [], "sections": {},
            },
            "query": {},
            "review": {},
            "drafts": drafts or {},
        }
        return _build_estar_xml(project_data, template)

    def test_real_xml_has_root_element(self):
        """Real format must use <root> not <form1>."""
        xml = self._generate()
        assert "<root>" in xml
        assert "</root>" in xml
        assert "<form1>" not in xml

    def test_real_xml_has_xfa_wrapper(self):
        """Real format must have xfa:datasets wrapper."""
        xml = self._generate()
        assert "xfa:datasets" in xml
        assert "xfa:data" in xml

    def test_nivd_has_form_id(self):
        """nIVD XML must contain FDA 4062 form identifier."""
        xml = self._generate(template="nIVD")
        assert "FDA 4062" in xml

    def test_ivd_has_form_id(self):
        """IVD XML must contain FDA 4078 form identifier."""
        xml = self._generate(template="IVD")
        assert "FDA 4078" in xml

    def test_prestar_has_form_id(self):
        """PreSTAR XML must contain FDA 5064 form identifier."""
        xml = self._generate(template="PreSTAR")
        assert "FDA 5064" in xml

    def test_nivd_real_sections_present(self):
        """nIVD real format must contain all major real eSTAR sections."""
        xml = self._generate(template="nIVD")
        expected = [
            "AdministrativeInformation",
            "DeviceDescription",
            "IndicationsForUse",
            "Classification",
            "PredicatesSE",
            "Labeling",
            "ReprocSter",
            "Biocompatibility",
            "SoftwareCyber",
            "EMCWireless",
            "PerformanceTesting",
            "AdministrativeDocumentation",
        ]
        for elem in expected:
            assert f"<{elem}>" in xml, f"Missing real section: <{elem}>"
            assert f"</{elem}>" in xml, f"Missing closing: </{elem}>"

    def test_ivd_has_ivd_specific_sections(self):
        """IVD format must contain IVD-specific sections."""
        xml = self._generate(template="IVD")
        assert "<AssayInstrumentInfo>" in xml
        assert "<AnalyticalPerformance>" in xml
        assert "<ClinicalStudies>" in xml

    def test_prestar_lacks_predicates(self):
        """PreSTAR format must NOT contain PredicatesSE."""
        xml = self._generate(template="PreSTAR")
        assert "<PredicatesSE>" not in xml
        assert "<SubmissionCharacteristics>" in xml
        assert "<Questions>" in xml

    def test_real_xml_applicant_field_ids(self):
        """Real format uses coded field IDs like ADTextField210."""
        xml = self._generate(import_data={
            "classification": {}, "predicates": [], "sections": {},
            "applicant": {"applicant_name": "Acme Medical"},
            "indications_for_use": {},
        })
        assert "<ADTextField210>Acme Medical</ADTextField210>" in xml

    def test_real_xml_classification_field_ids(self):
        """Real format uses DDTextField517a for product code."""
        xml = self._generate(import_data={
            "applicant": {}, "predicates": [], "sections": {},
            "classification": {"product_code": "FJL"},
            "indications_for_use": {},
        })
        assert "<DDTextField517a>FJL</DDTextField517a>" in xml

    def test_real_xml_ifu_field_ids(self):
        """Real format uses IUTextField141 for indications."""
        xml = self._generate(import_data={
            "applicant": {}, "classification": {}, "predicates": [], "sections": {},
            "indications_for_use": {"indications_for_use": "Urological catheter"},
        })
        assert "<IUTextField141>Urological catheter</IUTextField141>" in xml

    def test_real_xml_summary_in_admin_docs(self):
        """510(k) summary goes in AdministrativeDocumentation.PMNSummary."""
        xml = self._generate(drafts={"510k-summary": "This device is SE."})
        assert "<PMNSummary>" in xml
        assert "<SSTextField400>This device is SE.</SSTextField400>" in xml

    def test_real_xml_truthful_accuracy_in_admin_docs(self):
        """TA statement goes in AdministrativeDocumentation.TAStatement."""
        xml = self._generate(drafts={"truthful-accuracy": "I certify accuracy."})
        assert "<TAStatement>" in xml
        assert "<TATextField105>I certify accuracy.</TATextField105>" in xml

    def test_real_xml_predicate_fields(self):
        """Predicate K-number uses ADTextField830."""
        xml = self._generate(import_data={
            "applicant": {}, "classification": {}, "indications_for_use": {}, "sections": {},
            "predicates": [{"k_number": "K201234", "device_name": "Test Device", "manufacturer": "Acme"}],
        })
        assert "<ADTextField830>K201234</ADTextField830>" in xml
        assert "<ADTextField840>Test Device</ADTextField840>" in xml
        assert "<ADTextField850>Acme</ADTextField850>" in xml

    def test_real_xml_escaping(self):
        """Real format must also XML-escape special characters."""
        xml = self._generate(drafts={"510k-summary": "A & B < C"})
        assert "A &amp; B &lt; C" in xml

    def test_real_xml_device_description(self):
        """Device description uses DDTextField400."""
        xml = self._generate(drafts={"device-description": "A surgical catheter."})
        assert "<DDTextField400>A surgical catheter.</DDTextField400>" in xml

    def test_real_xml_sterilization(self):
        """Sterilization method uses STTextField110 under ReprocSter."""
        xml = self._generate(import_data={
            "applicant": {}, "classification": {}, "indications_for_use": {},
            "predicates": [],
            "sections": {"sterilization_method": "EO"},
        })
        assert "<STTextField110>EO</STTextField110>" in xml
        assert "<ReprocSter>" in xml


class TestRealVsLegacyFormatConsistency:
    """Verify real and legacy formats both contain the same data, just different structure."""

    def _project_data(self):
        return {
            "import": {
                "classification": {"product_code": "FJL", "device_trade_name": "TestCath"},
                "applicant": {"applicant_name": "Acme Med", "email": "test@acme.com"},
                "indications_for_use": {"indications_for_use": "Urological use"},
                "predicates": [{"k_number": "K201234", "device_name": "PredCath"}],
                "sections": {},
            },
            "query": {},
            "review": {},
            "drafts": {"510k-summary": "SE summary text", "device-description": "Catheter desc"},
        }

    def test_both_formats_contain_applicant(self):
        data = self._project_data()
        real = _build_estar_xml(data, "nIVD")
        legacy = _build_legacy_xml(data, "nIVD")
        assert "Acme Med" in real
        assert "Acme Med" in legacy

    def test_both_formats_contain_product_code(self):
        data = self._project_data()
        real = _build_estar_xml(data, "nIVD")
        legacy = _build_legacy_xml(data, "nIVD")
        assert "FJL" in real
        assert "FJL" in legacy

    def test_both_formats_contain_ifu(self):
        data = self._project_data()
        real = _build_estar_xml(data, "nIVD")
        legacy = _build_legacy_xml(data, "nIVD")
        assert "Urological use" in real
        assert "Urological use" in legacy

    def test_both_formats_contain_predicate(self):
        data = self._project_data()
        real = _build_estar_xml(data, "nIVD")
        legacy = _build_legacy_xml(data, "nIVD")
        assert "K201234" in real
        assert "K201234" in legacy

    def test_real_uses_root_legacy_uses_form1(self):
        data = self._project_data()
        real = _build_estar_xml(data, "nIVD")
        legacy = _build_legacy_xml(data, "nIVD")
        assert "<root>" in real
        assert "<form1>" not in real
        assert "<form1>" in legacy
        assert "<root>" not in legacy
