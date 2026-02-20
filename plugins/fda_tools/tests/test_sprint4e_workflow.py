"""Sprint 4E Tests — User Workflow

Tests for:
- C-09: Sample size calculator exact binomial for edge cases
- H-03: Draft revision workflow (--revise flag)
- H-06: Portfolio timeline planning (Gantt-style)
- H-08: Readiness score calculation tests
- H-09: PubMed API reference expansion
- H-11: Offline/cached mode for literature search
- M-02: N/A section handling guidance in draft
"""

import os
import pytest

# Paths
PLUGIN_ROOT = os.path.join(os.path.dirname(__file__), '..')
COMMANDS_DIR = os.path.join(PLUGIN_ROOT, 'commands')
REFERENCES_DIR = os.path.join(PLUGIN_ROOT, 'references')
SKILL_REFS_DIR = os.path.join(PLUGIN_ROOT, 'skills', 'fda-510k-knowledge', 'references')


# ===== C-09: Sample Size Calculator Improvements =====

class TestSampleSizeCalculator:
    """calc.md must have exact binomial method for edge cases."""

    @pytest.fixture
    def calc_content(self):
        with open(os.path.join(COMMANDS_DIR, 'calc.md')) as f:
            return f.read()

    def test_exact_binomial_method(self, calc_content):
        """Must have exact binomial calculation method."""
        assert "exact binomial" in calc_content.lower()

    def test_clopper_pearson_reference(self, calc_content):
        """Must reference Clopper-Pearson method."""
        assert "Clopper-Pearson" in calc_content

    def test_method_selection_logic(self, calc_content):
        """Must have method selection logic based on parameters."""
        assert "use_exact" in calc_content

    def test_normal_approximation_validity_check(self, calc_content):
        """Must check np > 5 and nq > 5 for normal approximation."""
        assert "NORMAL_APPROX_VALID" in calc_content

    def test_edge_case_threshold_095(self, calc_content):
        """Must use exact method when p >= 0.95."""
        assert "p0 >= 0.95" in calc_content

    def test_edge_case_threshold_005(self, calc_content):
        """Must use exact method when p <= 0.05."""
        assert "p0 <= 0.05" in calc_content

    def test_small_margin_threshold(self, calc_content):
        """Must use exact method for small margins."""
        assert "delta < 0.05" in calc_content

    def test_biostatistician_consultation_note(self, calc_content):
        """Must recommend biostatistician for pivotal studies."""
        assert "biostatistician" in calc_content.lower()

    def test_limitations_section(self, calc_content):
        """Must have LIMITATIONS section in output format."""
        assert "LIMITATIONS" in calc_content

    def test_method_output_field(self, calc_content):
        """Must output which method was used."""
        assert "METHOD:" in calc_content

    def test_margin_parameter(self, calc_content):
        """Must accept margin/delta parameter."""
        assert "MARGIN:" in calc_content


# ===== H-03: Draft Revision Workflow =====

class TestDraftRevisionWorkflow:
    """draft.md must support --revise flag for regeneration."""

    @pytest.fixture
    def draft_content(self):
        with open(os.path.join(COMMANDS_DIR, 'draft.md')) as f:
            return f.read()

    def test_revise_flag_defined(self, draft_content):
        """Must accept --revise flag."""
        assert "--revise" in draft_content

    def test_revision_workflow_section(self, draft_content):
        """Must have Revision Workflow section."""
        assert "## Revision Workflow" in draft_content

    def test_user_edit_markers(self, draft_content):
        """Must support USER EDIT START/END markers."""
        assert "USER EDIT START" in draft_content
        assert "USER EDIT END" in draft_content

    def test_preserve_user_edits(self, draft_content):
        """Must describe preserving user edits."""
        assert "Preserve" in draft_content

    def test_load_existing_draft_step(self, draft_content):
        """Must load existing draft before revision."""
        assert "Load Existing Draft" in draft_content

    def test_identify_user_edits_step(self, draft_content):
        """Must identify user-edited content."""
        assert "Identify User Edits" in draft_content

    def test_regenerate_ai_content_step(self, draft_content):
        """Must regenerate AI content."""
        assert "Regenerate AI Content" in draft_content

    def test_revision_report_format(self, draft_content):
        """Must output revision report with counts."""
        assert "Updated:" in draft_content
        assert "Preserved:" in draft_content


# ===== M-02: N/A Section Handling =====

class TestNASectionHandling:
    """draft.md must support --na flag for marking sections as not applicable."""

    @pytest.fixture
    def draft_content(self):
        with open(os.path.join(COMMANDS_DIR, 'draft.md')) as f:
            return f.read()

    def test_na_flag_defined(self, draft_content):
        """Must accept --na flag."""
        assert "--na" in draft_content

    def test_na_section_heading(self, draft_content):
        """Must have N/A Section Handling section."""
        assert "N/A Section Handling" in draft_content

    def test_na_rationale_template(self, draft_content):
        """Must include rationale template."""
        assert "Rationale" in draft_content
        assert "Not Applicable" in draft_content

    def test_na_sterilization_rationale(self, draft_content):
        """Must have sterilization N/A rationale example."""
        assert "non-sterile" in draft_content.lower()

    def test_na_software_rationale(self, draft_content):
        """Must have software N/A rationale example."""
        assert "does not contain software" in draft_content.lower()

    def test_na_biocompatibility_rationale(self, draft_content):
        """Must have biocompatibility N/A rationale example."""
        assert "no direct or indirect patient contact" in draft_content.lower() or "no body contact" in draft_content.lower()

    def test_na_estar_guidance(self, draft_content):
        """Must reference eSTAR guidance about N/A sections."""
        assert "eSTAR" in draft_content


# ===== H-06: Portfolio Timeline Planning =====

class TestPortfolioTimelinePlanning:
    """portfolio.md must have Gantt-style timeline view."""

    @pytest.fixture
    def portfolio_content(self):
        with open(os.path.join(COMMANDS_DIR, 'portfolio.md')) as f:
            return f.read()

    def test_timeline_section_exists(self, portfolio_content):
        """Must have Submission Timeline Planning section."""
        assert "Submission Timeline Planning" in portfolio_content

    def test_gantt_style_view(self, portfolio_content):
        """Must have Gantt-style timeline view."""
        assert "Gantt" in portfolio_content

    def test_milestone_tracking(self, portfolio_content):
        """Must track milestones."""
        assert "Milestone" in portfolio_content or "milestone" in portfolio_content

    def test_stage_detection(self, portfolio_content):
        """Must detect project stages."""
        assert "Extraction" in portfolio_content
        assert "Drafting" in portfolio_content
        assert "Assembly" in portfolio_content

    def test_fda_review_timeline_reference(self, portfolio_content):
        """Must reference FDA review timeline."""
        assert "RTA screening" in portfolio_content
        assert "90 FDA days" in portfolio_content

    def test_set_target_flag(self, portfolio_content):
        """Must support --set-target flag."""
        assert "--set-target" in portfolio_content

    def test_timeline_json(self, portfolio_content):
        """Must use timeline.json for storing target dates."""
        assert "timeline.json" in portfolio_content

    def test_timeline_in_report(self, portfolio_content):
        """Must include timeline in portfolio report output."""
        assert "SUBMISSION TIMELINE" in portfolio_content


# ===== H-08: Readiness Score Calculation Tests =====

class TestReadinessScoreCalculation:
    """pre-check.md must have deterministic SRI calculation."""

    @pytest.fixture
    def precheck_content(self):
        with open(os.path.join(COMMANDS_DIR, 'pre-check.md')) as f:
            return f.read()

    def test_sri_function_exists(self, precheck_content):
        """Must have calculate_readiness_score function."""
        assert "calculate_readiness_score" in precheck_content

    def test_rta_completeness_weight(self, precheck_content):
        """RTA completeness must be 25 points."""
        assert "25" in precheck_content
        # Verify it's specifically the RTA component
        assert "RTA completeness" in precheck_content or "rta_present" in precheck_content

    def test_predicate_quality_weight(self, precheck_content):
        """Predicate quality must be 20 points."""
        assert "20" in precheck_content

    def test_se_comparison_weight(self, precheck_content):
        """SE comparison must be 15 points."""
        assert "se_comparison" in precheck_content

    def test_testing_coverage_weight(self, precheck_content):
        """Testing coverage must contribute to score."""
        assert "testing_coverage" in precheck_content

    def test_deficiency_penalty(self, precheck_content):
        """Deficiencies must have penalty scoring."""
        assert "penalty" in precheck_content
        assert "critical_count" in precheck_content
        assert "major_count" in precheck_content

    def test_documentation_quality_weight(self, precheck_content):
        """Documentation quality must be 10 points."""
        assert "Documentation quality" in precheck_content or "drafts" in precheck_content

    def test_score_tiers(self, precheck_content):
        """Must have score tier labels."""
        assert "Ready" in precheck_content
        assert "Not Ready" in precheck_content

    def test_sri_output_in_report(self, precheck_content):
        """SRI must appear in report output."""
        assert "SRI:" in precheck_content

    def test_total_possible_100(self, precheck_content):
        """Total possible score must be 100."""
        # 25 + 20 + 15 + 15 + 15 + 10 = 100
        # Verify via the score components adding to 100
        assert "/100" in precheck_content


class TestReadinessScoreScenarios:
    """Deterministic scoring scenarios for SRI calculation."""

    @pytest.fixture
    def precheck_content(self):
        with open(os.path.join(COMMANDS_DIR, 'pre-check.md')) as f:
            return f.read()

    def test_perfect_score_achievable(self, precheck_content):
        """All components present and clean should yield 100."""
        # Verify that all scoring components exist
        assert "score += 25" in precheck_content or "25 *" in precheck_content  # RTA
        assert "score += 15" in precheck_content  # SE or testing or deficiency

    def test_critical_deficiency_penalty_is_3(self, precheck_content):
        """Each critical deficiency should cost 3 points."""
        assert "3 * critical_count" in precheck_content

    def test_major_deficiency_penalty_is_1(self, precheck_content):
        """Each major deficiency should cost 1 point."""
        assert "1 * major_count" in precheck_content

    def test_penalty_capped_at_15(self, precheck_content):
        """Deficiency penalty must be capped at 15."""
        assert "min(15," in precheck_content

    def test_partial_se_scores_8(self, precheck_content):
        """Partial SE comparison should score 8 points."""
        assert '8' in precheck_content
        assert "partial" in precheck_content

    def test_complete_se_scores_15(self, precheck_content):
        """Complete SE comparison should score 15 points."""
        # The SE comparison block awards 15 for complete
        assert '"complete"' in precheck_content

    def test_expected_sections_listed(self, precheck_content):
        """Expected sections for documentation scoring must be listed."""
        assert "device-description" in precheck_content
        assert "se-discussion" in precheck_content
        assert "510k-summary" in precheck_content
        assert "labeling" in precheck_content
        assert "cover-letter" in precheck_content


# ===== H-09: PubMed API Reference Expansion =====

class TestPubMedAPIReference:
    """pubmed-api.md must have expanded documentation."""

    @pytest.fixture
    def pubmed_skill_content(self):
        with open(os.path.join(SKILL_REFS_DIR, 'pubmed-api.md')) as f:
            return f.read()

    @pytest.fixture
    def pubmed_mirror_content(self):
        with open(os.path.join(REFERENCES_DIR, 'pubmed-api.md')) as f:
            return f.read()

    def test_efetch_parameters_documented(self, pubmed_skill_content):
        """efetch must have full parameter documentation."""
        assert "rettype=abstract" in pubmed_skill_content
        assert "retmode=xml" in pubmed_skill_content
        assert "max 200 per request" in pubmed_skill_content

    def test_xml_response_structure(self, pubmed_skill_content):
        """Must document XML response structure."""
        assert "PubmedArticleSet" in pubmed_skill_content
        assert "MedlineCitation" in pubmed_skill_content

    def test_xpath_parsing_table(self, pubmed_skill_content):
        """Must have XPath parsing table."""
        assert ".//PMID" in pubmed_skill_content
        assert ".//ArticleTitle" in pubmed_skill_content
        assert ".//AbstractText" in pubmed_skill_content

    def test_publication_types_table(self, pubmed_skill_content):
        """Must have publication types with evidence levels."""
        assert "Randomized Controlled Trial" in pubmed_skill_content
        assert "Evidence Level" in pubmed_skill_content

    def test_elink_endpoint_documented(self, pubmed_skill_content):
        """Must document elink endpoint."""
        assert "## elink" in pubmed_skill_content
        assert "neighbor_score" in pubmed_skill_content

    def test_date_range_filter(self, pubmed_skill_content):
        """Must document absolute date range filter."""
        assert "[PDat]" in pubmed_skill_content

    def test_humans_mesh_filter(self, pubmed_skill_content):
        """Must document humans MeSH filter."""
        assert '"humans"[MeSH]' in pubmed_skill_content

    def test_common_filter_combinations(self, pubmed_skill_content):
        """Must have common filter combination examples."""
        assert "Common Filter Combinations" in pubmed_skill_content

    def test_mirror_matches_skill(self, pubmed_skill_content, pubmed_mirror_content):
        """Top-level reference must match skill reference."""
        assert pubmed_skill_content == pubmed_mirror_content


# ===== H-11: Cached Mode for Literature =====

class TestLiteratureCacheMode:
    """literature.md must support caching and --refresh."""

    @pytest.fixture
    def literature_content(self):
        with open(os.path.join(COMMANDS_DIR, 'literature.md')) as f:
            return f.read()

    def test_refresh_flag_defined(self, literature_content):
        """Must accept --refresh flag."""
        assert "--refresh" in literature_content

    def test_cache_structure_section(self, literature_content):
        """Must have cache structure documentation."""
        assert "literature_cache.json" in literature_content

    def test_cache_json_structure(self, literature_content):
        """Must document cache JSON format."""
        assert "cached_date" in literature_content
        assert "search_queries" in literature_content
        assert "cache_version" in literature_content

    def test_cache_staleness_check(self, literature_content):
        """Must check cache age (7 days)."""
        assert "7 days" in literature_content

    def test_refresh_mode_description(self, literature_content):
        """Must describe refresh mode behavior."""
        assert "Ignore any existing cache" in literature_content or "Force re-query" in literature_content

    def test_cache_write_after_search(self, literature_content):
        """Must write cache after search completes."""
        assert "CACHE_WRITTEN" in literature_content

    def test_no_offline_flag(self, literature_content):
        """--offline flag should not exist (plugin requires internet)."""
        assert "--offline" not in literature_content
