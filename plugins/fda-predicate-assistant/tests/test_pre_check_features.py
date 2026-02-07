"""Tests for Tranche 7 features: /fda:pre-check command, review-simulator agent,
and cdrh-review-structure reference.

Validates reference file integrity, command structure, agent configuration,
and cross-reference patterns.
"""

import os


# Paths to reference files
BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
REFS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "references")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
AGENTS_DIR = os.path.join(BASE_DIR, "agents")


class TestCDRHReviewStructure:
    """Test cdrh-review-structure.md reference integrity."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "cdrh-review-structure.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_oht_mapping(self):
        assert "OHT1" in self.content
        assert "OHT2" in self.content
        assert "OHT3" in self.content
        assert "OHT4" in self.content
        assert "OHT5" in self.content
        assert "OHT6" in self.content
        assert "OHT7" in self.content
        assert "OHT8" in self.content

    def test_has_advisory_committee_codes(self):
        assert "AN" in self.content
        assert "CV" in self.content
        assert "OR" in self.content
        assert "SU" in self.content

    def test_has_division_level_detail(self):
        assert "DHT6A" in self.content  # Joint Arthroplasty
        assert "DHT6B" in self.content  # Spinal
        assert "DHT6C" in self.content  # Trauma

    def test_has_panel_to_oht_mapping_code(self):
        assert "PANEL_TO_OHT" in self.content
        assert '"AN": "OHT1"' in self.content
        assert '"CV": "OHT2"' in self.content

    def test_has_review_team_composition(self):
        assert "Lead Reviewer" in self.content
        assert "Team Lead" in self.content
        assert "Labeling" in self.content

    def test_has_specialist_reviewers(self):
        assert "Clinical" in self.content
        assert "Biocompatibility" in self.content
        assert "Software" in self.content
        assert "Sterilization" in self.content
        assert "Electrical/EMC" in self.content
        assert "Human Factors" in self.content
        assert "MRI Safety" in self.content

    def test_has_trigger_conditions(self):
        assert "Patient-contacting" in self.content or "patient-contacting" in self.content
        assert "software" in self.content.lower()
        assert "sterile" in self.content.lower()

    def test_has_auto_detection_logic(self):
        assert "determine_review_team" in self.content
        assert "software_keywords" in self.content or "electrical_keywords" in self.content

    def test_has_rta_checklist(self):
        assert "RTA" in self.content
        assert "Refuse to Accept" in self.content
        assert "RTA-" in self.content or "Cover letter" in self.content

    def test_has_rta_administrative_items(self):
        assert "FDA Form 3514" in self.content or "Cover Sheet" in self.content
        assert "Form 3881" in self.content or "Indications for Use" in self.content
        assert "510(k) Summary" in self.content

    def test_has_deficiency_templates(self):
        assert "Predicate Selection" in self.content or "predicate device" in self.content.lower()
        assert "SE Comparison" in self.content
        assert "Please provide" in self.content

    def test_has_lead_reviewer_deficiencies(self):
        assert "intended use" in self.content.lower()
        assert "substantial equivalence" in self.content.lower() or "SE" in self.content

    def test_has_clinical_reviewer_deficiencies(self):
        assert "Study Design" in self.content or "study design" in self.content
        assert "endpoint" in self.content.lower()

    def test_has_biocompatibility_deficiencies(self):
        assert "ISO 10993" in self.content
        assert "material characterization" in self.content.lower() or "Material Characterization" in self.content

    def test_has_software_deficiencies(self):
        assert "IEC 62304" in self.content
        assert "cybersecurity" in self.content.lower()

    def test_has_sterilization_deficiencies(self):
        assert "SAL" in self.content
        assert "ISO 11135" in self.content or "ISO 11137" in self.content

    def test_has_electrical_deficiencies(self):
        assert "IEC 60601-1" in self.content
        assert "IEC 60601-1-2" in self.content

    def test_has_human_factors_deficiencies(self):
        assert "IEC 62366" in self.content
        assert "usability" in self.content.lower()

    def test_has_se_decision_framework(self):
        assert "SE Determination" in self.content or "se determination" in self.content
        assert "same intended use" in self.content.lower()
        assert "technological characteristics" in self.content.lower()

    def test_has_se_flowchart(self):
        assert "NSE" in self.content or "Not Substantially Equivalent" in self.content

    def test_has_sopp_references(self):
        assert "SOPP 8217" in self.content
        assert "SOPP 26.2.1" in self.content

    def test_has_q_sub_program(self):
        assert "Q-Sub" in self.content or "Pre-Submission" in self.content
        assert "75" in self.content  # 75 calendar days

    def test_has_review_timelines(self):
        assert "90" in self.content  # 90 FDA days for traditional
        assert "30" in self.content  # 30 FDA days for special

    def test_has_historical_deficiency_patterns(self):
        assert "Orthopedic" in self.content
        assert "Cardiovascular" in self.content
        assert "Software" in self.content
        assert "IVD" in self.content or "In Vitro Diagnostics" in self.content

    def test_has_ortho_deficiency_patterns(self):
        assert "fatigue" in self.content.lower()
        assert "predicate age" in self.content.lower()

    def test_has_cv_deficiency_patterns(self):
        assert "hemodynamic" in self.content.lower() or "Hemodynamic" in self.content

    def test_has_software_deficiency_patterns(self):
        assert "documentation level" in self.content.lower() or "Documentation Level" in self.content
        assert "SBOM" in self.content

    def test_has_submission_readiness_scoring(self):
        assert "Readiness" in self.content
        assert "0-100" in self.content or "Score" in self.content

    def test_has_readiness_tiers(self):
        assert "Ready" in self.content
        assert "Nearly Ready" in self.content
        assert "Not Ready" in self.content

    def test_has_remediation_action_mapping(self):
        assert "/fda:propose" in self.content
        assert "/fda:compare-se" in self.content
        assert "/fda:draft" in self.content

    def test_cross_references_other_docs(self):
        assert "rta-checklist.md" in self.content
        assert "predicate-analysis-framework.md" in self.content
        assert "confidence-scoring.md" in self.content


class TestPreCheckCommand:
    """Test pre-check.md command structure and content."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "pre-check.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_valid_frontmatter(self):
        assert self.content.startswith("---")
        assert "description:" in self.content
        assert "allowed-tools:" in self.content
        assert "argument-hint:" in self.content

    def test_has_project_argument(self):
        assert "--project" in self.content

    def test_has_depth_argument(self):
        assert "--depth" in self.content
        assert "quick" in self.content
        assert "standard" in self.content
        assert "deep" in self.content

    def test_has_focus_argument(self):
        assert "--focus" in self.content
        assert "predicate" in self.content
        assert "testing" in self.content
        assert "labeling" in self.content
        assert "clinical" in self.content

    def test_has_plugin_root_resolution(self):
        assert "installed_plugins.json" in self.content
        assert "fda-predicate-assistant@" in self.content

    def test_has_full_auto_mode(self):
        assert "--full-auto" in self.content

    def test_has_project_data_inventory(self):
        assert "review.json" in self.content
        assert "query.json" in self.content
        assert "output.csv" in self.content

    def test_has_openfda_classification_query(self):
        assert "api.fda.gov/device/classification" in self.content

    def test_has_oht_mapping(self):
        assert "PANEL_TO_OHT" in self.content
        assert "OHT" in self.content

    def test_has_specialist_reviewer_identification(self):
        assert "Biocompatibility" in self.content
        assert "Software" in self.content
        assert "Sterilization" in self.content

    def test_has_rta_screening(self):
        assert "RTA" in self.content
        assert "RTA-01" in self.content or "rta_items" in self.content

    def test_has_lead_reviewer_evaluation(self):
        assert "Lead Reviewer" in self.content
        assert "Predicate Appropriateness" in self.content or "predicate" in self.content.lower()

    def test_has_se_comparison_check(self):
        assert "SE" in self.content
        assert "comparison" in self.content.lower()

    def test_has_specialist_evaluations(self):
        assert "Biocompatibility Review" in self.content
        assert "Software Review" in self.content
        assert "Sterilization Review" in self.content

    def test_has_deficiency_severity_levels(self):
        assert "CRITICAL" in self.content
        assert "MAJOR" in self.content
        assert "MINOR" in self.content

    def test_has_readiness_score(self):
        assert "readiness" in self.content.lower()
        assert "calculate_readiness_score" in self.content or "Score" in self.content

    def test_has_remediation_plan(self):
        assert "Remediation" in self.content or "remediation" in self.content

    def test_has_report_output(self):
        assert "pre_check_report.md" in self.content

    def test_has_audit_logging(self):
        assert "audit_log.jsonl" in self.content

    def test_has_error_handling(self):
        assert "No project" in self.content or "--project" in self.content
        assert "API unavailable" in self.content or "api" in self.content.lower()

    def test_references_cdrh_structure(self):
        assert "cdrh-review-structure.md" in self.content

    def test_quick_depth_rta_only(self):
        assert "quick" in self.content
        assert "RTA" in self.content

    def test_deep_depth_predicate_chain(self):
        assert "deep" in self.content
        assert "predicate chain" in self.content.lower() or "competitive" in self.content.lower()


class TestReviewSimulatorAgent:
    """Test review-simulator.md agent configuration."""

    def setup_method(self):
        path = os.path.join(AGENTS_DIR, "review-simulator.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_valid_frontmatter(self):
        assert self.content.startswith("---")
        assert "name: review-simulator" in self.content
        assert "description:" in self.content
        assert "tools:" in self.content

    def test_has_required_tools(self):
        assert "Read" in self.content
        assert "Glob" in self.content
        assert "Grep" in self.content
        assert "Bash" in self.content
        assert "Write" in self.content

    def test_has_web_tools(self):
        assert "WebFetch" in self.content
        assert "WebSearch" in self.content

    def test_has_project_discovery_phase(self):
        assert "Project Discovery" in self.content or "project" in self.content.lower()

    def test_has_data_enrichment_phase(self):
        assert "Data Enrichment" in self.content or "enrichment" in self.content.lower()

    def test_has_review_team_assembly(self):
        assert "Review Team" in self.content
        assert "OHT" in self.content

    def test_has_individual_reviewer_evaluations(self):
        assert "Lead Reviewer" in self.content
        assert "Team Lead" in self.content
        assert "Labeling" in self.content

    def test_has_specialist_evaluations(self):
        assert "Biocompatibility" in self.content
        assert "Software" in self.content
        assert "Sterilization" in self.content

    def test_has_cross_reference_phase(self):
        assert "Cross-Reference" in self.content or "Synthesis" in self.content

    def test_has_report_generation(self):
        assert "Report" in self.content
        assert "Executive Summary" in self.content

    def test_has_deficiency_structure(self):
        assert "CRITICAL" in self.content
        assert "MAJOR" in self.content
        assert "Remediation" in self.content

    def test_has_se_probability_assessment(self):
        assert "SE" in self.content
        assert "NSE" in self.content or "probability" in self.content.lower()

    def test_references_cdrh_structure(self):
        assert "cdrh-review-structure.md" in self.content

    def test_has_regulatory_context(self):
        assert "510(k)" in self.content
        assert "CDRH" in self.content
        assert "OPEQ" in self.content or "OHT" in self.content

    def test_has_communication_style(self):
        assert "specific" in self.content.lower()
        assert "conservative" in self.content.lower() or "err on the side" in self.content.lower()

    def test_has_pdf_download_capability(self):
        assert "accessdata.fda.gov" in self.content
        assert "pdf" in self.content.lower()

    def test_has_competitive_context(self):
        assert "Competitive" in self.content or "recent clearances" in self.content.lower()
