"""Tests for v5.4.0 features: CDRH Portal reference, eSTAR template selection
matrix, mandatory dates, QMSR alignment, and submission guidance in commands.

Validates reference file integrity, template selection content, and
cross-references across commands and references.
"""

import json
import os


BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
REFS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "references")
TOP_REFS_DIR = os.path.join(BASE_DIR, "references")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
SKILL_MD = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "SKILL.md")
PLUGIN_JSON = os.path.join(BASE_DIR, ".claude-plugin", "plugin.json")


class TestCDRHPortalReference:
    """Test cdrh-portal.md reference integrity."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "cdrh-portal.md")
        with open(path) as f:
            self.content = f.read()

    def test_skill_ref_exists(self):
        assert os.path.exists(os.path.join(REFS_DIR, "cdrh-portal.md"))

    def test_top_ref_exists(self):
        assert os.path.exists(os.path.join(TOP_REFS_DIR, "cdrh-portal.md"))

    def test_has_portal_url(self):
        assert "ccp.fda.gov" in self.content

    def test_has_file_size_limits(self):
        assert "4 GB" in self.content
        assert "1 GB" in self.content

    def test_has_all_submission_types(self):
        assert "510(k)" in self.content
        assert "De Novo" in self.content
        assert "PMA" in self.content
        assert "Pre-Submission" in self.content
        assert "IDE" in self.content
        assert "513(g)" in self.content

    def test_has_cdrh_vs_cber_routing(self):
        assert "CDRH" in self.content
        assert "CBER" in self.content
        assert "ESG" in self.content

    def test_has_processing_timeline(self):
        assert "4:00 PM ET" in self.content or "4 PM ET" in self.content

    def test_has_support_contacts(self):
        assert "ccp@fda.hhs.gov" in self.content
        assert "eSubPilot@fda.hhs.gov" in self.content
        assert "DICE@fda.hhs.gov" in self.content

    def test_has_official_correspondent(self):
        assert "official correspondent" in self.content.lower()
        assert "3514" in self.content

    def test_has_oversized_file_fallback(self):
        assert "Silver Spring" in self.content
        assert "DCC" in self.content

    def test_both_copies_match(self):
        with open(os.path.join(TOP_REFS_DIR, "cdrh-portal.md")) as f:
            top_content = f.read()
        assert self.content == top_content


class TestESTARTemplateSelection:
    """Test eSTAR structure template selection matrix and new sections."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "estar-structure.md")
        with open(path) as f:
            self.skill_content = f.read()
        path2 = os.path.join(TOP_REFS_DIR, "estar-structure.md")
        with open(path2) as f:
            self.top_content = f.read()

    def test_skill_has_template_selection_matrix(self):
        assert "Template Selection Matrix" in self.skill_content

    def test_top_has_template_selection_matrix(self):
        assert "Template Selection Matrix" in self.top_content

    def test_has_omb_control_numbers(self):
        for content in [self.skill_content, self.top_content]:
            assert "0910-0120" in content
            assert "0910-0844" in content
            assert "0910-0231" in content
            assert "0910-0756" in content
            assert "0910-0078" in content
            assert "0910-0511" in content

    def test_has_mandatory_dates(self):
        for content in [self.skill_content, self.top_content]:
            assert "October 1, 2023" in content
            assert "October 1, 2025" in content

    def test_has_qmsr_alignment(self):
        for content in [self.skill_content, self.top_content]:
            assert "QMSR" in content
            assert "February 2, 2026" in content

    def test_has_adobe_acrobat_requirement(self):
        for content in [self.skill_content, self.top_content]:
            assert "Adobe Acrobat Pro" in content

    def test_has_early_technical_screening(self):
        for content in [self.skill_content, self.top_content]:
            assert "180-day hold" in content

    def test_has_cdrh_portal_reference(self):
        for content in [self.skill_content, self.top_content]:
            assert "CDRH Portal" in content
            assert "cdrh-portal.md" in content


class TestECTDOverviewUpdates:
    """Test ectd-overview.md references CDRH Portal correctly."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "ectd-overview.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_cdrh_portal(self):
        assert "CDRH Portal" in self.content

    def test_has_cdrh_portal_url(self):
        assert "ccp.fda.gov" in self.content

    def test_de_novo_estar_mandatory(self):
        assert "Oct 1, 2025" in self.content or "October 1, 2025" in self.content

    def test_pma_voluntary_estar(self):
        assert "voluntary" in self.content.lower()

    def test_cross_references_cdrh_portal_md(self):
        assert "cdrh-portal.md" in self.content


class TestCommandSubmissionGuidance:
    """Test that export and assemble commands include CDRH Portal guidance."""

    def test_export_has_cdrh_portal(self):
        with open(os.path.join(CMDS_DIR, "export.md")) as f:
            content = f.read()
        assert "CDRH Portal" in content or "ccp.fda.gov" in content

    def test_export_has_file_size_warning(self):
        with open(os.path.join(CMDS_DIR, "export.md")) as f:
            content = f.read()
        assert "4 GB" in content

    def test_assemble_has_cdrh_portal(self):
        with open(os.path.join(CMDS_DIR, "assemble.md")) as f:
            content = f.read()
        assert "CDRH Portal" in content or "ccp.fda.gov" in content

    def test_assemble_has_cdrh_portal_ref(self):
        with open(os.path.join(CMDS_DIR, "assemble.md")) as f:
            content = f.read()
        assert "cdrh-portal.md" in content

    def test_import_has_template_selection(self):
        with open(os.path.join(CMDS_DIR, "import.md")) as f:
            content = f.read()
        assert "Template Selection" in content

    def test_import_has_qmsr_note(self):
        with open(os.path.join(CMDS_DIR, "import.md")) as f:
            content = f.read()
        assert "QMSR" in content


class TestSKILLMDUpdates:
    """Test SKILL.md lists cdrh-portal.md in resources."""

    def setup_method(self):
        with open(SKILL_MD) as f:
            self.content = f.read()

    def test_lists_cdrh_portal_reference(self):
        assert "cdrh-portal.md" in self.content

    def test_resource_count_41(self):
        assert "42 references" in self.content

    def test_command_count_40(self):
        assert "Commands (43)" in self.content or "43 commands" in self.content


class TestVersionBump:
    """Test plugin version is 5.7.0."""

    def test_plugin_json_version(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert data["version"] == '5.22.0'
