"""Tests for v5.11.0: Curated CDRH Guidance Documents Index.

Validates reference doc structure, guidance command enhancements,
SKILL.md updates, and plugin metadata.
"""

import json
import os

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
REFS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "references")
TOP_REFS_DIR = os.path.join(BASE_DIR, "references")
SKILL_MD = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "SKILL.md")
PLUGIN_JSON = os.path.join(BASE_DIR, ".claude-plugin", "plugin.json")


# -- Guidance Index Reference Document --------------------------------


class TestGuidanceIndexExists:
    """Test fda-guidance-index.md reference document exists in both locations."""

    def test_skill_ref_exists(self):
        assert os.path.exists(os.path.join(REFS_DIR, "fda-guidance-index.md"))

    def test_top_ref_exists(self):
        assert os.path.exists(os.path.join(TOP_REFS_DIR, "fda-guidance-index.md"))

    def test_both_copies_match(self):
        with open(os.path.join(REFS_DIR, "fda-guidance-index.md")) as f:
            skill_content = f.read()
        with open(os.path.join(TOP_REFS_DIR, "fda-guidance-index.md")) as f:
            top_content = f.read()
        assert skill_content == top_content


class TestGuidanceIndexStructure:
    """Test the guidance index has all required sections."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "fda-guidance-index.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_cross_cutting_section(self):
        assert "Cross-Cutting Guidance" in self.content

    def test_has_software_section(self):
        assert "Software & Digital Health Guidance" in self.content

    def test_has_emc_wireless_section(self):
        assert "Electromagnetic & Wireless Guidance" in self.content

    def test_has_pathway_section(self):
        assert "Pathway-Specific Guidance" in self.content

    def test_has_device_category_section(self):
        assert "Device-Category Specific Guidance" in self.content

    def test_has_implantable_section(self):
        assert "Implantable Device Additional Guidance" in self.content

    def test_has_combination_product_section(self):
        assert "Combination Products" in self.content

    def test_has_recent_guidance_section(self):
        assert "Recently Finalized" in self.content

    def test_has_regulation_lookup_section(self):
        assert "Regulation Number" in self.content
        assert "Quick Lookup" in self.content


class TestGuidanceIndexCrossCutting:
    """Test cross-cutting guidance entries."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "fda-guidance-index.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_biocompatibility(self):
        assert "Biocompatibility" in self.content
        assert "ISO 10993" in self.content

    def test_has_sterilization(self):
        assert "Sterilization" in self.content
        assert "ISO 11135" in self.content

    def test_has_shelf_life(self):
        assert "Shelf Life" in self.content
        assert "ASTM F1980" in self.content

    def test_has_labeling(self):
        assert "Labeling" in self.content
        assert "21 CFR 801" in self.content

    def test_has_risk_management(self):
        assert "Risk Management" in self.content
        assert "ISO 14971" in self.content

    def test_has_clinical_evidence(self):
        assert "Clinical Evidence" in self.content
        assert "Real-World Evidence" in self.content


class TestGuidanceIndexSoftware:
    """Test software/digital health guidance entries."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "fda-guidance-index.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_software_submissions(self):
        assert "Content of Premarket Submissions for Device Software Functions" in self.content

    def test_has_ai_ml_guidance(self):
        assert "Artificial Intelligence-Enabled Device Software Functions" in self.content

    def test_has_cybersecurity(self):
        assert "Cybersecurity in Medical Devices" in self.content

    def test_has_pccp(self):
        assert "Predetermined Change Control Plan" in self.content

    def test_has_samd(self):
        assert "Software as a Medical Device" in self.content

    def test_has_iec_62304(self):
        assert "IEC 62304" in self.content

    def test_has_trigger_keywords(self):
        assert "Trigger Keywords" in self.content
        assert "software" in self.content.lower()
        assert "firmware" in self.content.lower()


class TestGuidanceIndex510k:
    """Test 510(k) pathway guidance entries."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "fda-guidance-index.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_se_evaluation(self):
        assert "Evaluating Substantial Equivalence" in self.content

    def test_has_rta(self):
        assert "Refuse to Accept" in self.content

    def test_has_traditional_510k(self):
        assert "Traditional 510(k)" in self.content

    def test_has_special_510k(self):
        assert "Special 510(k)" in self.content

    def test_has_abbreviated_510k(self):
        assert "Abbreviated 510(k)" in self.content

    def test_has_estar(self):
        assert "eSTAR" in self.content

    def test_has_de_novo(self):
        assert "De Novo" in self.content

    def test_has_pma(self):
        assert "PMA" in self.content

    def test_has_q_submission(self):
        assert "Q-Submission" in self.content


class TestGuidanceIndexDeviceCategories:
    """Test device-category specific guidance entries."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "fda-guidance-index.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_cardiovascular(self):
        assert "Cardiovascular" in self.content
        assert "21 CFR 870" in self.content

    def test_has_orthopedic(self):
        assert "Orthopedic" in self.content
        assert "21 CFR 888" in self.content

    def test_has_wound_care(self):
        assert "Wound Care" in self.content
        assert "21 CFR 878" in self.content

    def test_has_ivd(self):
        assert "In Vitro Diagnostic" in self.content

    def test_has_dental(self):
        assert "Dental" in self.content
        assert "21 CFR 872" in self.content

    def test_has_ophthalmic(self):
        assert "Ophthalmic" in self.content

    def test_has_cgm(self):
        assert "Continuous Glucose" in self.content or "CGM" in self.content

    def test_has_respiratory(self):
        assert "Respiratory" in self.content

    def test_has_imaging(self):
        assert "Imaging" in self.content


class TestGuidanceIndexRecentGuidance:
    """Test recently finalized and upcoming guidance entries."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "fda-guidance-index.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_fy2026_agenda(self):
        assert "FY 2026" in self.content

    def test_has_fy2024_2025_finalized(self):
        assert "2024" in self.content
        assert "2025" in self.content

    def test_has_sterility_2024(self):
        assert "Sterility" in self.content

    def test_has_cybersecurity_2025(self):
        assert "Cybersecurity" in self.content
        assert "2025" in self.content

    def test_has_ai_2025(self):
        assert "AI" in self.content


class TestGuidanceIndexRegulationLookup:
    """Test regulation-to-guidance quick lookup table."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "fda-guidance-index.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_common_regulations(self):
        assert "878.4018" in self.content
        assert "870.4200" in self.content
        assert "862.1355" in self.content

    def test_has_guidance_availability_column(self):
        assert "Has Specific Guidance?" in self.content

    def test_marks_wound_dressing_no_guidance(self):
        # 878.4018 should be marked as no device-specific guidance
        assert "878.4018" in self.content


# -- Guidance Command Enhancement ------------------------------------


class TestGuidanceCommandUsesIndex:
    """Test guidance.md references the bundled index."""

    def setup_method(self):
        with open(os.path.join(CMDS_DIR, "guidance.md")) as f:
            self.content = f.read()

    def test_references_guidance_index(self):
        assert "fda-guidance-index.md" in self.content

    def test_has_bundled_index_lookup_step(self):
        assert "Bundled Guidance Index Lookup" in self.content

    def test_index_lookup_before_web_search(self):
        # The index lookup (2A) should come before WebSearch fallback (2C)
        idx_pos = self.content.find("Bundled Guidance Index Lookup")
        web_pos = self.content.find("WebSearch Fallback")
        assert idx_pos < web_pos, "Index lookup should come before WebSearch fallback"

    def test_still_has_web_search_fallback(self):
        assert "WebSearch" in self.content

    def test_still_has_offline_mode(self):
        assert "--offline" in self.content


# -- SKILL.md Updates ------------------------------------------------


class TestSKILLMDGuidanceIndex:
    """Test SKILL.md lists fda-guidance-index.md in resources."""

    def setup_method(self):
        with open(SKILL_MD) as f:
            self.content = f.read()

    def test_lists_guidance_index_reference(self):
        assert "fda-guidance-index.md" in self.content

    def test_resource_count_26(self):
        assert "26 references" in self.content


# -- Plugin Metadata -------------------------------------------------


class TestPluginVersionAndCounts511:
    """Test plugin.json reflects v5.11.0."""

    def test_version_is_5_11_0(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert data["version"] == "5.11.0"

    def test_description_mentions_guidance_index(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert "guidance index" in data["description"].lower()

    def test_command_count_is_37(self):
        """Verify 37 .md files in commands directory."""
        cmd_files = [f for f in os.listdir(CMDS_DIR) if f.endswith(".md")]
        assert len(cmd_files) == 37, f"Expected 37 commands, found {len(cmd_files)}: {sorted(cmd_files)}"

    def test_description_mentions_37_commands(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert "37 commands" in data["description"]
