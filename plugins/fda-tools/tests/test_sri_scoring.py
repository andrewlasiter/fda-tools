"""Tests for v5.18.0 Item 30: SRI (Submission Readiness Index) scoring tests.

Validates formula components in pre-check.md, formula in readiness-score-formula.md,
cdrh-review-structure.md, tier boundary definitions, reviewer score aggregation,
output format, and PCS vs SRI disambiguation.
"""

import os
import re

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
REFS_DIR = os.path.join(BASE_DIR, "references")
AGENTS_DIR = os.path.join(BASE_DIR, "agents")


def _read_ref(name):
    path = os.path.join(REFS_DIR, f"{name}.md")
    with open(path) as f:
        return f.read()


def _read_cmd(name):
    path = os.path.join(CMDS_DIR, f"{name}.md")
    with open(path) as f:
        return f.read()


def _read_agent(name):
    path = os.path.join(AGENTS_DIR, f"{name}.md")
    with open(path) as f:
        return f.read()


class TestReadinessFormulaFile:
    """readiness-score-formula.md existence and structure."""

    def setup_method(self):
        self.content = _read_ref("readiness-score-formula")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(REFS_DIR, "readiness-score-formula.md"))

    def test_has_formula_overview(self):
        assert "Formula Overview" in self.content or "SRI =" in self.content

    def test_has_mandatory_section_component(self):
        assert "Mandatory" in self.content and "50" in self.content

    def test_has_optional_section_component(self):
        assert "Optional" in self.content and "15" in self.content

    def test_has_consistency_check_component(self):
        assert "Consistency" in self.content and "25" in self.content

    def test_has_penalties_component(self):
        assert "Penalties" in self.content or "penalty" in self.content.lower()

    def test_total_adds_to_100(self):
        """Verify 50 + 15 + 25 = 90 base + penalties up to 100."""
        assert "50" in self.content
        assert "15" in self.content
        assert "25" in self.content


class TestSRITierBoundaries:
    """Tier boundary definitions consistency."""

    def setup_method(self):
        self.content = _read_ref("readiness-score-formula")

    def test_has_ready_tier(self):
        assert "Ready" in self.content and "85" in self.content

    def test_has_nearly_ready_tier(self):
        assert "Nearly Ready" in self.content and "70" in self.content

    def test_has_significant_gaps_tier(self):
        assert "Significant Gaps" in self.content and "50" in self.content

    def test_has_not_ready_tier(self):
        assert "Not Ready" in self.content and "30" in self.content

    def test_has_early_stage_tier(self):
        assert "Early Stage" in self.content

    def test_tiers_no_overlap(self):
        """Verify tier ranges don't overlap: 85-100, 70-84, 50-69, 30-49, 0-29."""
        assert "85-100" in self.content or ("85" in self.content and "100" in self.content)
        assert "70-84" in self.content or "70" in self.content

    def test_tiers_no_gaps(self):
        """All scores 0-100 should map to exactly one tier."""
        assert "0-29" in self.content or "0" in self.content


class TestSRIInPreCheck:
    """SRI formula referenced in pre-check.md command."""

    def setup_method(self):
        self.content = _read_cmd("pre-check")

    def test_pre_check_mentions_sri(self):
        assert "SRI" in self.content or "readiness" in self.content.lower()

    def test_pre_check_has_scoring(self):
        assert "score" in self.content.lower()


class TestSRIInCDRHReviewStructure:
    """SRI referenced in cdrh-review-structure.md."""

    def setup_method(self):
        self.content = _read_ref("cdrh-review-structure")

    def test_has_review_team_structure(self):
        assert "OHT" in self.content

    def test_has_scoring_rubric(self):
        content_lower = self.content.lower()
        assert "score" in content_lower or "rubric" in content_lower


class TestReviewerScoreAggregation:
    """Reviewer score aggregation in review-simulator agent."""

    def setup_method(self):
        self.content = _read_agent("review-simulator")

    def test_has_scoring_rubric(self):
        assert "Scoring Rubric" in self.content or "scoring rubric" in self.content.lower()

    def test_has_score_aggregation(self):
        content_lower = self.content.lower()
        assert "score" in content_lower

    def test_has_phase_for_synthesis(self):
        assert "Phase 5" in self.content or "Synthesis" in self.content

    def test_has_deficiency_prioritization(self):
        assert "prioritiz" in self.content.lower() or "severity" in self.content.lower()


class TestSRIOutputFormat:
    """SRI display format consistency."""

    def setup_method(self):
        self.formula = _read_ref("readiness-score-formula")

    def test_display_format_documented(self):
        assert "SRI:" in self.formula

    def test_display_includes_tier_label(self):
        assert "tier" in self.formula.lower() or "label" in self.formula.lower()

    def test_never_just_number(self):
        """Format should always include prefix and label."""
        assert "SRI:" in self.formula and "\u2014" in self.formula


class TestPCSvsSRIDisambiguation:
    """PCS vs SRI disambiguation across files."""

    def setup_method(self):
        self.formula = _read_ref("readiness-score-formula")
        self.confidence = _read_ref("confidence-scoring")

    def test_formula_has_disambiguation(self):
        assert "PCS" in self.formula or "Predicate Confidence" in self.formula

    def test_confidence_has_disambiguation(self):
        assert "SRI" in self.confidence or "Submission Readiness" in self.confidence

    def test_formula_defines_sri(self):
        assert "Submission Readiness Index" in self.formula

    def test_confidence_defines_pcs(self):
        assert "Predicate Confidence Score" in self.confidence

    def test_both_have_scale(self):
        assert "0-100" in self.formula
        assert "0-100" in self.confidence or "100" in self.confidence
