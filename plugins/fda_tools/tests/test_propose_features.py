"""Tests for Tranche 6 features: /fda:propose command, predicate analysis framework,
presub Section 4.2 expansion, and modifications to status/compare-se/traceability.

Validates reference file integrity, command structure, and cross-reference patterns.
"""

import os

# Paths to reference files
BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
REFS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "references")
CMDS_DIR = os.path.join(BASE_DIR, "commands")


class TestProposeCommand:
    """Test propose.md command structure and content."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "propose.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_valid_frontmatter(self):
        assert self.content.startswith("---")
        assert "description:" in self.content
        assert "allowed-tools:" in self.content
        assert "argument-hint:" in self.content

    def test_has_predicates_argument(self):
        assert "--predicates" in self.content

    def test_has_references_argument(self):
        assert "--references" in self.content

    def test_has_project_argument(self):
        assert "--project" in self.content

    def test_has_product_code_argument(self):
        assert "--product-code" in self.content

    def test_has_rationale_argument(self):
        assert "--rationale" in self.content

    def test_has_skip_validation_flag(self):
        assert "--skip-validation" in self.content

    def test_has_force_flag(self):
        assert "--force" in self.content

    def test_has_full_auto_mode(self):
        assert "--full-auto" in self.content

    def test_has_knumber_format_validation(self):
        assert "^[KPN]\\d{6}$" in self.content or "KPN" in self.content

    def test_has_openfda_validation(self):
        assert "api.fda.gov/device/510k" in self.content

    def test_has_recall_check(self):
        assert "api.fda.gov/device/recall" in self.content

    def test_has_maude_check(self):
        assert "api.fda.gov/device/event" in self.content or "MAUDE" in self.content

    def test_has_confidence_scoring(self):
        assert "confidence_score" in self.content
        assert "score_breakdown" in self.content

    def test_manual_scoring_section_context_is_30(self):
        assert "section_context" in self.content
        assert "30 pts" in self.content or "30" in self.content

    def test_has_ifu_comparison(self):
        assert "IFU" in self.content or "ifu_comparison" in self.content
        assert "overlap" in self.content.lower()

    def test_writes_review_json(self):
        assert "review.json" in self.content
        assert '"review_mode": "manual"' in self.content

    def test_has_manual_proposal_flag(self):
        assert '"manual_proposal": true' in self.content

    def test_has_reference_devices_key(self):
        assert '"reference_devices"' in self.content

    def test_writes_query_json(self):
        assert "query.json" in self.content

    def test_has_plugin_root_resolution(self):
        assert "installed_plugins.json" in self.content
        assert "fda-tools@" in self.content

    def test_has_audit_logging(self):
        assert "audit_log.jsonl" in self.content
        assert "proposal_created" in self.content

    def test_has_risk_flags(self):
        assert "RECALLED" in self.content
        assert "OLD" in self.content
        assert "PRODUCT_CODE_MISMATCH" in self.content
        assert "DEATH_EVENTS" in self.content

    def test_has_output_formatting(self):
        assert "PROPOSED PREDICATES" in self.content
        assert "VALIDATION RESULTS" in self.content
        assert "NEXT STEPS" in self.content

    def test_has_error_handling(self):
        assert "Invalid device number format" in self.content or "invalid" in self.content.lower()
        assert "--skip-validation" in self.content

    def test_review_json_schema_compatible(self):
        # Must have same predicates schema as review.md
        assert '"decision": "accepted"' in self.content
        assert '"rationale"' in self.content
        assert '"device_info"' in self.content
        assert '"flags"' in self.content

    def test_downstream_compatibility_noted(self):
        assert "/fda:presub" in self.content
        assert "/fda:compare-se" in self.content
        assert "/fda:lineage" in self.content


class TestPredicateAnalysisFramework:
    """Test predicate-analysis-framework.md reference integrity."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "predicate-analysis-framework.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_ifu_comparison_methodology(self):
        assert "IFU Comparison Methodology" in self.content

    def test_has_keyword_overlap_analysis(self):
        assert "Jaccard" in self.content or "keyword" in self.content.lower()
        assert "overlap" in self.content.lower()

    def test_has_technological_characteristics(self):
        assert "Technological Characteristics" in self.content

    def test_has_comparison_dimensions(self):
        assert "Materials" in self.content
        assert "Principle of operation" in self.content
        assert "Energy source" in self.content

    def test_has_regulatory_history_analysis(self):
        assert "Regulatory History" in self.content
        assert "MAUDE" in self.content
        assert "Recall" in self.content

    def test_has_risk_assessment_matrix(self):
        assert "Risk Assessment" in self.content or "risk" in self.content.lower()
        assert "Low Risk" in self.content
        assert "High Risk" in self.content

    def test_has_predicate_chain_analysis(self):
        assert "Chain" in self.content
        assert "Chain Health" in self.content

    def test_has_chain_health_scoring(self):
        assert "Chain Health Score" in self.content
        assert "Deduct" in self.content

    def test_has_gap_analysis_decision_tree(self):
        assert "Gap Analysis" in self.content
        assert "TESTING_GAP" in self.content
        assert "DATA_GAP" in self.content
        assert "CLINICAL_GAP" in self.content
        assert "SE_BARRIER" in self.content

    def test_has_gap_to_question_mapping(self):
        assert "Gap-to-Question" in self.content

    def test_has_justification_narrative_template(self):
        assert "Justification Narrative" in self.content

    def test_has_narrative_quality_checklist(self):
        assert "Quality Checklist" in self.content

    def test_cross_references_other_docs(self):
        assert "confidence-scoring.md" in self.content
        assert "section-patterns.md" in self.content
        assert "openfda-api.md" in self.content

    def test_has_ifu_difference_categories(self):
        assert "Identical IFU" in self.content
        assert "Different indication" in self.content


class TestPresubDeepPredicateAnalysis:
    """Test presub.md Section 4.2 expansion with 7 subsections."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "presub.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_subsection_4_2_1_summary_table(self):
        assert "4.2.1" in self.content
        assert "Predicate Summary Table" in self.content

    def test_has_subsection_4_2_2_ifu_comparison(self):
        assert "4.2.2" in self.content
        assert "Intended Use Comparison" in self.content

    def test_has_subsection_4_2_3_tech_characteristics(self):
        assert "4.2.3" in self.content
        assert "Technological Characteristics" in self.content

    def test_has_subsection_4_2_4_regulatory_history(self):
        assert "4.2.4" in self.content
        assert "Regulatory History" in self.content

    def test_has_subsection_4_2_5_chain_analysis(self):
        assert "4.2.5" in self.content
        assert "Predicate Chain" in self.content

    def test_has_subsection_4_2_6_gap_analysis(self):
        assert "4.2.6" in self.content
        assert "Gap Analysis" in self.content

    def test_has_subsection_4_2_7_justification_narrative(self):
        assert "4.2.7" in self.content
        assert "Justification Narrative" in self.content

    def test_references_predicate_analysis_framework(self):
        assert "predicate-analysis-framework.md" in self.content

    def test_has_deep_predicate_analysis_flag(self):
        assert "--deep-predicate-analysis" in self.content

    def test_has_manual_mode_note(self):
        assert "manual" in self.content.lower()
        assert "review_mode" in self.content

    def test_has_reference_devices_section(self):
        assert "reference_devices" in self.content
        assert "Reference Devices" in self.content

    def test_has_keyword_overlap_table(self):
        assert "Overlap Score" in self.content

    def test_has_chain_health_scoring(self):
        assert "Chain health" in self.content or "chain health" in self.content

    def test_has_gap_types(self):
        assert "TESTING_GAP" in self.content
        assert "DATA_GAP" in self.content

    def test_has_api_queries_for_regulatory_history(self):
        assert "api.fda.gov/device/event" in self.content
        assert "api.fda.gov/device/recall" in self.content


class TestStatusManualProposal:
    """Test status.md displays manual proposal information."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "status.md")
        with open(path) as f:
            self.content = f.read()

    def test_checks_review_mode(self):
        assert "review_mode" in self.content

    def test_checks_manual_proposal(self):
        assert "manual_proposal" in self.content or "manual" in self.content.lower()

    def test_checks_reference_devices(self):
        assert "reference_devices" in self.content

    def test_has_review_json_check(self):
        assert "review.json" in self.content


class TestCompareSEReferenceDevices:
    """Test compare-se.md reads reference_devices from review.json."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "compare-se.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_reference_devices_in_infer(self):
        assert "reference_devices" in self.content

    def test_references_propose_command(self):
        assert "/fda:propose" in self.content


class TestTraceabilityReferenceDevices:
    """Test traceability.md includes reference devices."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "traceability.md")
        with open(path) as f:
            self.content = f.read()

    def test_has_reference_device_requirements(self):
        assert "Reference device" in self.content or "reference_devices" in self.content

    def test_loads_reference_devices_from_review_json(self):
        assert "reference_devices" in self.content

    def test_has_reference_requirement_source(self):
        assert "Reference Device:" in self.content or "REFERENCE:" in self.content
