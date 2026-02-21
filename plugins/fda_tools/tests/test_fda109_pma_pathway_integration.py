"""
Integration tests for FDA-109: PMA Pathway Workflow Integration.

Verifies that:
1. The pma-draft.md command file exists and has valid structure.
2. pipeline.md includes PMA pathway detection and PMA pipeline steps.
3. pre-check.md includes PMA readiness scoring and IS_PMA detection.
4. dashboard.md includes PMA status section and PMA-specific next steps.
5. All existing PMA command files (pma-search, pma-intelligence, etc.) exist.
6. PMA pipeline step criticality table is present.
"""

import re
from pathlib import Path

import pytest

# Plugin root relative to this test file
COMMANDS_DIR = Path(__file__).parent.parent / "commands"
TESTS_DIR = Path(__file__).parent


# ============================================================================
# Helpers
# ============================================================================

def read_command(name: str) -> str:
    """Read a command markdown file."""
    path = COMMANDS_DIR / name
    assert path.exists(), f"Command file missing: {path}"
    return path.read_text()


# ============================================================================
# 1. pma-draft.md existence and structure
# ============================================================================

class TestPmaDraftCommand:
    """pma-draft.md must exist and cover all mandatory PMA sections."""

    def test_pma_draft_md_exists(self):
        assert (COMMANDS_DIR / "pma-draft.md").exists(), (
            "pma-draft.md must exist — it is the PMA equivalent of draft.md"
        )

    def test_pma_draft_has_frontmatter(self):
        content = read_command("pma-draft.md")
        assert content.startswith("---"), "pma-draft.md must have YAML frontmatter"
        assert "description:" in content[:300]
        assert "allowed-tools:" in content[:500]

    def test_pma_draft_has_section_registry(self):
        content = read_command("pma-draft.md")
        # Must list the mandatory PMA sections per 21 CFR 814.20
        for section in ("ssed", "clinical", "manufacturing", "preclinical", "biocompatibility"):
            assert section in content, f"pma-draft.md missing section: {section}"

    def test_pma_draft_references_cfr_814(self):
        content = read_command("pma-draft.md")
        assert "814" in content, "pma-draft.md must reference 21 CFR Part 814"

    def test_pma_draft_has_cover_letter_section(self):
        content = read_command("pma-draft.md")
        assert "cover-letter" in content

    def test_pma_draft_has_ssed_section(self):
        content = read_command("pma-draft.md")
        assert "Summary of Safety and Effectiveness" in content

    def test_pma_draft_has_clinical_section(self):
        content = read_command("pma-draft.md")
        assert "Clinical" in content and "clinical" in content

    def test_pma_draft_has_manufacturing_section(self):
        content = read_command("pma-draft.md")
        assert "manufacturing" in content.lower()

    def test_pma_draft_has_confabulation_warning(self):
        """LLM confabulation risk warning must be present."""
        content = read_command("pma-draft.md")
        assert "confabulation" in content.lower() or "WARNING" in content

    def test_pma_draft_has_citation_needed_guidance(self):
        content = read_command("pma-draft.md")
        assert "CITATION NEEDED" in content

    def test_pma_draft_has_insert_placeholders(self):
        content = read_command("pma-draft.md")
        assert "[INSERT:" in content

    def test_pma_draft_has_todo_placeholders(self):
        content = read_command("pma-draft.md")
        assert "[TODO:" in content

    def test_pma_draft_has_revise_flag(self):
        content = read_command("pma-draft.md")
        assert "--revise" in content

    def test_pma_draft_has_output_flag(self):
        content = read_command("pma-draft.md")
        assert "--output" in content


# ============================================================================
# 2. pipeline.md PMA pathway integration
# ============================================================================

class TestPipelinePmaPathway:
    """pipeline.md must include PMA pathway detection and steps."""

    def test_pipeline_has_pma_flag(self):
        content = read_command("pipeline.md")
        assert "--pma" in content, "pipeline.md must accept --pma flag"

    def test_pipeline_has_pathway_detection(self):
        content = read_command("pipeline.md")
        assert "Pathway Detection" in content or "pathway" in content.lower()

    def test_pipeline_has_pma_pipeline_section(self):
        content = read_command("pipeline.md")
        assert "PMA Pipeline" in content

    def test_pipeline_pma_step_p1(self):
        content = read_command("pipeline.md")
        assert "P1" in content and "Search" in content

    def test_pipeline_pma_step_p2(self):
        content = read_command("pipeline.md")
        assert "P2" in content and "Clinical" in content

    def test_pipeline_pma_step_p3(self):
        content = read_command("pipeline.md")
        assert "P3" in content and "Draft" in content

    def test_pipeline_pma_criticality_table(self):
        content = read_command("pipeline.md")
        assert "CRITICAL" in content
        # PMA criticality table has P-prefixed steps
        assert re.search(r'P[1-7].*CRITICAL', content) is not None

    def test_pipeline_pma_completion_report(self):
        content = read_command("pipeline.md")
        assert "PMA Pipeline Completion Report" in content or "PMA PIPELINE" in content.upper()

    def test_pipeline_pma_references_cfr_814(self):
        content = read_command("pipeline.md")
        assert "814" in content

    def test_pipeline_pma_references_pma_draft_command(self):
        content = read_command("pipeline.md")
        assert "pma-draft" in content


# ============================================================================
# 3. pre-check.md PMA readiness detection
# ============================================================================

class TestPreCheckPmaReadiness:
    """pre-check.md must detect PMA projects and apply PMA readiness scoring."""

    def test_pre_check_has_pma_detection(self):
        content = read_command("pre-check.md")
        assert "IS_PMA" in content or "is_pma" in content

    def test_pre_check_has_pma_readiness_scoring(self):
        content = read_command("pre-check.md")
        assert "PMA Readiness" in content or "PRI" in content

    def test_pre_check_pma_checks_pma_data_dir(self):
        content = read_command("pre-check.md")
        assert "pma_data" in content

    def test_pre_check_pma_checks_p_number(self):
        content = read_command("pre-check.md")
        assert "pma_number" in content or "p_number" in content

    def test_pre_check_pma_section_score_table(self):
        content = read_command("pre-check.md")
        # Must have SSED in PMA scoring
        assert "ssed" in content.lower() or "SSED" in content

    def test_pre_check_pma_mentions_q_sub(self):
        """Must recommend Q-Sub pre-submission meeting."""
        content = read_command("pre-check.md")
        assert "Q-Sub" in content or "pre-submission" in content.lower() or "Pre-Submission" in content

    def test_pre_check_pma_mentions_review_timeline(self):
        """Must mention PMA review timeline (180-360 days)."""
        content = read_command("pre-check.md")
        assert "180" in content


# ============================================================================
# 4. dashboard.md PMA status section
# ============================================================================

class TestDashboardPmaStatus:
    """dashboard.md must include PMA status section."""

    def test_dashboard_has_is_pma_detection(self):
        content = read_command("dashboard.md")
        assert "IS_PMA" in content or "is_pma" in content

    def test_dashboard_has_pma_status_section(self):
        content = read_command("dashboard.md")
        assert "PMA STATUS" in content or "pma_number" in content

    def test_dashboard_pma_checks_pma_data_dir(self):
        content = read_command("dashboard.md")
        assert "pma_data" in content

    def test_dashboard_pma_next_steps(self):
        content = read_command("dashboard.md")
        assert "pma-search" in content or "pma-draft" in content

    def test_dashboard_pma_mentions_clinical_requirements(self):
        content = read_command("dashboard.md")
        assert "clinical-requirements" in content


# ============================================================================
# 5. Existing PMA command files
# ============================================================================

class TestExistingPmaCommands:
    """All PMA command files referenced in FDA-109 must exist."""

    PMA_COMMANDS = [
        "pma-search.md",
        "pma-intelligence.md",
        "pma-supplements.md",
        "pma-timeline.md",
        "pma-compare.md",
        "clinical-requirements.md",
        "annual-reports.md",
        "pas-monitor.md",
        "approval-probability.md",
    ]

    def test_all_pma_commands_exist(self):
        missing = [c for c in self.PMA_COMMANDS if not (COMMANDS_DIR / c).exists()]
        assert not missing, f"Missing PMA command files: {missing}"

    def test_pma_search_has_download_ssed_flag(self):
        content = read_command("pma-search.md")
        assert "--download-ssed" in content

    def test_pma_intelligence_has_pma_arg(self):
        content = read_command("pma-intelligence.md")
        assert "--pma" in content

    def test_pma_supplements_has_pma_arg(self):
        content = read_command("pma-supplements.md")
        assert "--pma" in content

    def test_pma_timeline_exists_and_has_content(self):
        content = read_command("pma-timeline.md")
        assert len(content) > 100


# ============================================================================
# 6. PMA pipeline step completeness
# ============================================================================

class TestPmaPipelineCompleteness:
    """PMA pipeline steps P1-P7 must all be present in pipeline.md."""

    def test_pma_steps_p1_through_p7_present(self):
        content = read_command("pipeline.md")
        for step in ("P1", "P2", "P3", "P4", "P5", "P6", "P7"):
            assert step in content, f"PMA pipeline step {step} missing from pipeline.md"

    def test_pma_pipeline_references_pma_supplements(self):
        content = read_command("pipeline.md")
        assert "pma-supplements" in content

    def test_pma_pipeline_references_pma_timeline(self):
        content = read_command("pipeline.md")
        assert "pma-timeline" in content

    def test_pma_pipeline_references_approval_probability(self):
        content = read_command("pipeline.md")
        assert "approval-probability" in content

    def test_pma_pipeline_has_not_regulatory_advice_disclaimer(self):
        content = read_command("pipeline.md")
        assert "regulatory advice" in content.lower()
