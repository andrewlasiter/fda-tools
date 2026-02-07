"""Tests for Tranche 5 features: BOM tracking, eCTD overview, labeling artwork,
human factors template, complaint handling.

Validates reference file integrity, command modifications, and cross-reference patterns.
"""

import os

# Paths to reference files
BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
REFS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "references")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
TEMPLATES_DIR = os.path.join(BASE_DIR, "references")


class TestECTDOverview:
    """Test ectd-overview.md reference integrity."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "ectd-overview.md")
        with open(path) as f:
            self.content = f.read()

    def test_clarifies_not_required_for_510k(self):
        assert "NOT" in self.content
        assert "510(k)" in self.content
        assert "eSTAR" in self.content

    def test_has_ectd_modules(self):
        assert "Module 1" in self.content
        assert "Module 5" in self.content

    def test_has_estar_comparison(self):
        assert "eSTAR" in self.content
        assert "eCTD" in self.content

    def test_has_applicable_submission_types(self):
        assert "PMA" in self.content
        assert "IDE" in self.content

    def test_mentions_fda_esg(self):
        assert "ESG" in self.content or "Electronic Submissions Gateway" in self.content


class TestHumanFactorsFramework:
    """Test human-factors-framework.md reference integrity."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "human-factors-framework.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_iec_62366_reference(self):
        assert "IEC 62366-1:2015" in self.content

    def test_has_applicability_decision_tree(self):
        assert "user interface" in self.content
        assert "critical tasks" in self.content

    def test_has_formative_evaluation(self):
        assert "Formative" in self.content
        assert "Cognitive walkthrough" in self.content or "cognitive walkthrough" in self.content

    def test_has_summative_evaluation(self):
        assert "Summative" in self.content
        assert "15" in self.content  # Minimum 15 participants

    def test_has_estar_section_19(self):
        assert "Section 19" in self.content or "19.1" in self.content

    def test_has_use_related_risk(self):
        assert "Use-Related Risk" in self.content or "use-related risk" in self.content

    def test_has_auto_detection_keywords(self):
        assert "touchscreen" in self.content
        assert "home use" in self.content

    def test_has_fda_guidance_references(self):
        assert "Applying Human Factors" in self.content
        assert "2016" in self.content


class TestComplaintHandlingFramework:
    """Test complaint-handling-framework.md reference integrity."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "complaint-handling-framework.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_regulatory_basis(self):
        assert "21 CFR 820.198" in self.content
        assert "21 CFR 803" in self.content

    def test_has_complaint_intake_template(self):
        assert "Complaint ID" in self.content
        assert "Date received" in self.content

    def test_has_mdr_reportability_decision_tree(self):
        assert "REPORTABLE" in self.content
        assert "5 working days" in self.content
        assert "30 calendar days" in self.content

    def test_has_serious_injury_definition(self):
        assert "Serious Injury" in self.content or "serious injury" in self.content
        assert "life-threatening" in self.content or "Life-threatening" in self.content

    def test_has_complaint_categories(self):
        assert "Malfunction" in self.content
        assert "Injury" in self.content
        assert "Death" in self.content

    def test_has_trend_analysis(self):
        assert "Trend" in self.content
        assert "quarter" in self.content or "Quarter" in self.content

    def test_has_maude_integration(self):
        assert "MAUDE" in self.content
        assert "/fda:safety" in self.content


class TestDraftBOMSection:
    """Test draft.md has BOM/materials in device-description."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "draft.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_bom_in_device_description(self):
        assert "Bill of Materials" in self.content

    def test_bom_has_patient_contacting(self):
        assert "Patient-Contacting" in self.content

    def test_bom_has_biocompatibility_crossref(self):
        assert "ISO 10993-1" in self.content

    def test_has_materials_table_structure(self):
        assert "Component" in self.content
        assert "Material" in self.content
        assert "Supplier" in self.content


class TestDraftHumanFactorsSection:
    """Test draft.md has human-factors as 18th section."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "draft.md")
        with open(path) as f:
            self.content = f.read()

    def test_human_factors_in_section_list(self):
        assert "`human-factors`" in self.content

    def test_human_factors_section_defined(self):
        assert "### 18. human-factors" in self.content

    def test_has_section_19_reference(self):
        # Section 19 of eSTAR
        hf_section = self.content[self.content.index("### 18. human-factors"):]
        assert "Section 19" in hf_section

    def test_has_auto_detection(self):
        hf_section = self.content[self.content.index("### 18. human-factors"):]
        assert "auto-detect" in hf_section.lower() or "Applicability auto-detection" in hf_section

    def test_references_hf_framework(self):
        hf_section = self.content[self.content.index("### 18. human-factors"):]
        assert "human-factors-framework.md" in hf_section


class TestDraftArtworkTracking:
    """Test draft.md has artwork file tracking in labeling section."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "draft.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_artwork_tracking(self):
        assert "--artwork-dir" in self.content

    def test_has_artwork_manifest(self):
        assert "Artwork Files" in self.content

    def test_artwork_supports_formats(self):
        assert "PDF" in self.content
        assert "PNG" in self.content
        assert "SVG" in self.content


class TestCompareSEMaterials:
    """Test compare-se.md has materials comparison row."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "compare-se.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_materials_comparison_section(self):
        assert "Materials Comparison" in self.content

    def test_has_bom_integration(self):
        assert "BOM" in self.content

    def test_flags_biocompatibility_differences(self):
        assert "Biocompatibility" in self.content or "biocompatibility" in self.content
        assert "ISO 10993" in self.content

    def test_has_patient_contacting_note(self):
        assert "Patient-contacting" in self.content or "patient-contacting" in self.content


class TestSafetyComplaintTemplate:
    """Test safety.md has --complaint-template flag."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "safety.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_complaint_template_flag(self):
        assert "--complaint-template" in self.content

    def test_has_mdr_reportability(self):
        # In the complaint template section
        assert "21 CFR 803" in self.content

    def test_has_complaint_categories(self):
        assert "COMPLAINT HANDLING PROCEDURE" in self.content

    def test_references_complaint_framework(self):
        assert "complaint-handling-framework.md" in self.content


class TestExportECTDNote:
    """Test export.md has eCTD note."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "export.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_ectd_note(self):
        assert "eCTD" in self.content

    def test_clarifies_estar_required(self):
        assert "eSTAR" in self.content
        assert "NOT required" in self.content or "not required" in self.content


class TestAssembleArtwork:
    """Test assemble.md has artwork manifest."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "assemble.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_artwork_manifest(self):
        assert "Artwork" in self.content or "artwork" in self.content

    def test_has_section_09_labeling(self):
        assert "Section 09" in self.content or "section_09" in self.content

    def test_has_file_format_list(self):
        assert "PDF" in self.content
        assert "PNG" in self.content


class TestDraftTemplatesHumanFactors:
    """Test draft-templates.md has Section 19 Human Factors template."""

    def setup_method(self):
        path = os.path.join(TEMPLATES_DIR, "draft-templates.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_section_19(self):
        assert "Section 19" in self.content

    def test_has_use_environment(self):
        assert "19.1" in self.content
        assert "Use Environment" in self.content

    def test_has_user_profile(self):
        assert "19.2" in self.content
        assert "User Profile" in self.content

    def test_has_critical_tasks(self):
        assert "19.3" in self.content
        assert "Critical Tasks" in self.content

    def test_has_summative_table(self):
        assert "Successes" in self.content
        assert "Use Errors" in self.content or "use errors" in self.content


class TestPluginVersion:
    """Test plugin.json is at v5.1.0."""

    def setup_method(self):
        import json
        path = os.path.join(BASE_DIR, ".claude-plugin", "plugin.json")
        with open(path) as f:
            self.plugin = json.load(f)

    def test_version_is_5_1_0(self):
        assert self.plugin["version"] == "5.1.0"

    def test_description_mentions_new_features(self):
        desc = self.plugin["description"]
        assert "BOM" in desc or "materials" in desc
        assert "human factors" in desc
        assert "complaint" in desc
