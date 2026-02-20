"""Tests for Tranche 4 features: DoC template, Risk management, DHF checklist,
Clinical study guidance, Shelf life calculator.

Validates reference file integrity, calculation logic, and cross-reference patterns.
"""

import math
import os

# Paths to reference files
BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
REFS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "references")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
TEMPLATES_DIR = os.path.join(BASE_DIR, "references")


class TestShelfLifeCalculation:
    """Test ASTM F1980 accelerated aging calculations."""

    def test_aaf_default_parameters(self):
        """AAF = Q10^((55-25)/10) = 2^3 = 8."""
        Q10 = 2.0
        T_accel = 55
        T_ambient = 25
        AAF = Q10 ** ((T_accel - T_ambient) / 10)
        assert AAF == 8.0

    def test_aaf_q10_1_8(self):
        """AAF with Q10=1.8 (worst-case sensitivity)."""
        AAF = 1.8 ** ((55 - 25) / 10)
        assert round(AAF, 2) == 5.83

    def test_accelerated_duration_2_years(self):
        """2-year shelf life / AAF 8.0 = 3 months."""
        AAF = 8.0
        shelf_life_months = 24
        accel_months = shelf_life_months / AAF
        assert accel_months == 3.0

    def test_accelerated_duration_3_years(self):
        """3-year shelf life / AAF 8.0 = 4.5 months."""
        AAF = 8.0
        shelf_life_months = 36
        accel_months = shelf_life_months / AAF
        assert accel_months == 4.5

    def test_accelerated_duration_5_years(self):
        """5-year shelf life / AAF 8.0 = 7.5 months."""
        AAF = 8.0
        shelf_life_months = 60
        accel_months = shelf_life_months / AAF
        assert accel_months == 7.5

    def test_aaf_different_temperatures(self):
        """AAF at 60C with Q10=2.0: 2^((60-25)/10) = 2^3.5."""
        AAF = 2.0 ** ((60 - 25) / 10)
        assert round(AAF, 2) == 11.31

    def test_aaf_lower_temperature_differential(self):
        """AAF at 40C with Q10=2.0: 2^((40-25)/10) = 2^1.5."""
        AAF = 2.0 ** ((40 - 25) / 10)
        assert round(AAF, 2) == 2.83


class TestSampleSizeCalculation:
    """Test basic sample size calculation logic."""

    def test_one_sample_binomial_approx(self):
        """Basic one-sample binomial sample size estimate."""
        p0 = 0.90
        z_alpha = 1.645  # One-sided 0.05
        delta = 0.05  # Margin
        n = math.ceil((z_alpha ** 2 * p0 * (1 - p0)) / (delta ** 2))
        assert n > 0
        assert n < 500  # Sanity check

    def test_dropout_adjustment(self):
        """Sample size increases with dropout rate."""
        n_evaluable = 100
        dropout = 0.10
        n_enrolled = math.ceil(n_evaluable / (1 - dropout))
        assert n_enrolled == 112

    def test_higher_success_rate_needs_fewer_subjects(self):
        """Higher success rate → smaller sample for same margin."""
        z = 1.645
        delta = 0.05
        n_90 = math.ceil((z ** 2 * 0.90 * 0.10) / (delta ** 2))
        n_95 = math.ceil((z ** 2 * 0.95 * 0.05) / (delta ** 2))
        assert n_95 < n_90


class TestRiskManagementReference:
    """Test risk-management-framework.md reference integrity."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "risk-management-framework.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_iso_14971_reference(self):
        assert "ISO 14971:2019" in self.content

    def test_has_severity_classification(self):
        assert "Negligible" in self.content
        assert "Catastrophic" in self.content

    def test_has_probability_classification(self):
        assert "Improbable" in self.content
        assert "Frequent" in self.content

    def test_has_risk_acceptability_matrix(self):
        assert "ALARP" in self.content
        assert "Unacceptable" in self.content
        assert "Acceptable" in self.content

    def test_has_risk_control_priority(self):
        assert "Inherently safe design" in self.content
        assert "Protective measures" in self.content
        assert "Information for safety" in self.content

    def test_has_orthopedic_hazard_template(self):
        assert "HAZ-001" in self.content
        assert "Implant migration" in self.content

    def test_has_software_hazard_template(self):
        assert "HAZ-S01" in self.content
        assert "Incorrect output" in self.content

    def test_has_integration_points(self):
        assert "/fda:traceability" in self.content
        assert "/fda:test-plan" in self.content


class TestDHFChecklist:
    """Test dhf-checklist.md reference integrity."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "dhf-checklist.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_regulatory_basis(self):
        assert "21 CFR 820.30" in self.content
        assert "ISO 13485:2016" in self.content

    def test_has_all_dhf_sections(self):
        required_sections = [
            "Design and Development Planning",
            "Design Input",
            "Design Output",
            "Design Review",
            "Design Verification",
            "Design Validation",
            "Design Transfer",
            "Design Changes",
            "Risk Management",
            "Requirements Traceability",
        ]
        for section in required_sections:
            assert section in self.content, f"Missing DHF section: {section}"

    def test_has_status_indicators(self):
        assert "Complete" in self.content
        assert "In Progress" in self.content
        assert "Gap" in self.content

    def test_has_qmsr_transition_notes(self):
        assert "QMSR" in self.content
        assert "February 2, 2026" in self.content


class TestClinicalStudyFramework:
    """Test clinical-study-framework.md reference integrity."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "clinical-study-framework.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_decision_tree(self):
        assert "Decision Tree" in self.content

    def test_has_study_types(self):
        assert "Pivotal Clinical Study" in self.content
        assert "Feasibility" in self.content
        assert "Literature-Based" in self.content

    def test_has_sample_size_guidance(self):
        assert "Sample Size" in self.content

    def test_has_clinical_endpoints(self):
        assert "Clinical Endpoints" in self.content

    def test_has_regulatory_references(self):
        assert "21 CFR 807.87(j)" in self.content

    def test_has_integration_points(self):
        assert "/fda:draft clinical" in self.content
        assert "/fda:literature" in self.content


class TestCalcCommand:
    """Test calc.md command file structure."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "calc.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_shelf_life_subcommand(self):
        assert "shelf-life" in self.content

    def test_has_sample_size_subcommand(self):
        assert "sample-size" in self.content

    def test_has_astm_f1980_reference(self):
        assert "ASTM F1980" in self.content

    def test_has_q10_formula(self):
        assert "Q10" in self.content
        assert "AAF" in self.content

    def test_has_error_handling(self):
        assert "Error Handling" in self.content


class TestDraftTemplatesDoC:
    """Test draft-templates.md has DoC section."""

    def setup_method(self):
        path = os.path.join(TEMPLATES_DIR, "draft-templates.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_doc_section(self):
        assert "Declaration of Conformity" in self.content

    def test_has_manufacturer_info(self):
        assert "Manufacturer Information" in self.content

    def test_has_standards_table(self):
        assert "Applicable Standards" in self.content

    def test_has_astm_f1980_example(self):
        assert "ASTM F1980" in self.content
        assert "AAF" in self.content

    def test_has_shelf_life_formula(self):
        assert "Q10^((T_accelerated - T_ambient) / 10)" in self.content


class TestDraftCommandDocSection:
    """Test draft.md has doc as 17th section."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "draft.md")
        with open(path) as f:
            self.content = f.read()

    def test_doc_in_section_list(self):
        assert "`doc`" in self.content

    def test_doc_section_defined(self):
        assert "### 17. doc" in self.content

    def test_doc_references_standards(self):
        # The doc section should reference standards-tracking.md
        doc_section = self.content[self.content.index("### 17. doc"):]
        assert "standards-tracking.md" in doc_section

    def test_clinical_references_framework(self):
        assert "clinical-study-framework.md" in self.content

    def test_shelf_life_references_calc(self):
        assert "/fda:calc shelf-life" in self.content
