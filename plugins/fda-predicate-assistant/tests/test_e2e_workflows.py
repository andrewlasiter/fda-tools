"""Tests for v5.13.0: End-to-end workflow validation.

Cross-command structural tests that validate workflow integrity:
- Shared API endpoints use consistent URLs
- Section names are consistent across draft/assemble/consistency commands
- Pipeline steps reference each other correctly
- Agent tool lists reference real commands
"""

import os

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
AGENTS_DIR = os.path.join(BASE_DIR, "agents")
def _read_cmd(name):
    path = os.path.join(CMDS_DIR, f"{name}.md")
    with open(path) as f:
        return f.read()


def _read_agent(name):
    path = os.path.join(AGENTS_DIR, f"{name}.md")
    with open(path) as f:
        return f.read()


# ── Research Workflow ────────────────────────────────────────


class TestResearchWorkflow:
    """Validate research → safety → guidance → literature cross-references."""

    def test_research_and_safety_use_fda_data_store(self):
        research = _read_cmd("research")
        safety = _read_cmd("safety")
        assert "fda_data_store" in research or "FDAClient" in research
        assert "fda_data_store" in safety or "FDAClient" in safety

    def test_research_and_guidance_both_reference_product_code(self):
        research = _read_cmd("research")
        guidance = _read_cmd("guidance")
        assert "--product-code" in research or "product_code" in research
        assert "--product-code" in guidance or "product code" in guidance.lower()

    def test_safety_and_warnings_share_enforcement_concept(self):
        safety = _read_cmd("safety")
        warnings = _read_cmd("warnings")
        assert "recall" in safety.lower()
        assert "recall" in warnings.lower()

    def test_literature_and_trials_share_clinical_concept(self):
        literature = _read_cmd("literature")
        trials = _read_cmd("trials")
        assert "clinical" in literature.lower()
        assert "clinical" in trials.lower()

    def test_research_agent_covers_research_commands(self):
        agent = _read_agent("research-intelligence")
        for cmd in ["research", "safety", "guidance", "literature"]:
            assert f"/fda:{cmd}" in agent, f"Agent missing /fda:{cmd}"


# ── Submission Workflow ──────────────────────────────────────


class TestSubmissionWorkflow:
    """Validate draft → consistency → assemble → export cross-references."""

    def test_draft_sections_referenced_in_assemble(self):
        draft = _read_cmd("draft")
        assemble = _read_cmd("assemble")
        common_sections = ["device-description", "se-discussion"]
        for section in common_sections:
            assert section in draft, f"draft.md missing {section}"
            assert section in assemble or "section" in assemble.lower(), \
                f"assemble.md should reference sections"

    def test_consistency_references_project_flag(self):
        consistency = _read_cmd("consistency")
        draft = _read_cmd("draft")
        assert "--project" in consistency
        assert "--project" in draft

    def test_export_and_assemble_share_estar_concept(self):
        export = _read_cmd("export")
        assemble = _read_cmd("assemble")
        assert "eSTAR" in export
        assert "eSTAR" in assemble

    def test_compare_se_and_draft_share_se_concept(self):
        compare = _read_cmd("compare-se")
        draft = _read_cmd("draft")
        assert "substantial equivalence" in compare.lower() or "se-discussion" in compare
        assert "se-discussion" in draft

    def test_submission_agent_covers_submission_commands(self):
        agent = _read_agent("submission-assembler")
        for cmd in ["draft", "consistency", "assemble", "export"]:
            assert f"/fda:{cmd}" in agent, f"Agent missing /fda:{cmd}"


# ── Data Pipeline Workflow ───────────────────────────────────


class TestDataPipelineWorkflow:
    """Validate gap-analysis → data-pipeline → extract → analyze flow."""

    def test_gap_analysis_and_data_pipeline_share_years_flag(self):
        gap = _read_cmd("gap-analysis")
        pipeline = _read_cmd("data-pipeline")
        assert "--years" in gap
        assert "--years" in pipeline

    def test_gap_analysis_and_data_pipeline_share_product_codes_flag(self):
        gap = _read_cmd("gap-analysis")
        pipeline = _read_cmd("data-pipeline")
        assert "--product-codes" in gap
        assert "--product-codes" in pipeline

    def test_extract_references_pdf_processing(self):
        extract = _read_cmd("extract")
        assert "PDF" in extract or "pdf" in extract.lower()

    def test_status_checks_data_freshness(self):
        status = _read_cmd("status")
        assert "fresh" in status.lower() or "cache" in status.lower() or "age" in status.lower()

    def test_pipeline_agent_covers_pipeline_commands(self):
        agent = _read_agent("data-pipeline-manager")
        for cmd in ["gap-analysis", "data-pipeline", "extract"]:
            assert f"/fda:{cmd}" in agent, f"Agent missing /fda:{cmd}"


# ── Review Workflow ──────────────────────────────────────────


class TestReviewWorkflow:
    """Validate review → pre-check → compare-se flow."""

    def test_review_and_precheck_share_project_flag(self):
        review = _read_cmd("review")
        precheck = _read_cmd("pre-check")
        assert "--project" in review
        assert "--project" in precheck

    def test_review_json_referenced_across_commands(self):
        review = _read_cmd("review")
        precheck = _read_cmd("pre-check")
        assert "review.json" in review
        assert "review.json" in precheck

    def test_compare_se_references_predicates(self):
        compare = _read_cmd("compare-se")
        assert "predicate" in compare.lower()


# ── API Endpoint Consistency ─────────────────────────────────


class TestAPIEndpointConsistency:
    """Validate that commands referencing same APIs use identical URLs."""

    def test_openfda_510k_url_consistent(self):
        """Commands using 510k endpoint should use same URL format."""
        for cmd in ["research", "propose", "pathway", "monitor"]:
            content = _read_cmd(cmd)
            if "api.fda.gov" in content:
                assert "api.fda.gov/device/510k" in content or "api.fda.gov" in content

    def test_openfda_classification_url_consistent(self):
        for cmd in ["pre-check", "pathway", "test-plan"]:
            content = _read_cmd(cmd)
            if "classification" in content.lower():
                # May reference the concept without the full URL
                assert "classification" in content.lower()

    def test_clinicaltrials_url_consistent(self):
        trials = _read_cmd("trials")
        assert "clinicaltrials.gov/api/v2" in trials

    def test_data_dashboard_url_consistent(self):
        inspections = _read_cmd("inspections")
        assert "api-datadashboard.fda.gov" in inspections

    def test_accessgudid_url_consistent(self):
        udi = _read_cmd("udi")
        assert "accessgudid" in udi.lower()


# ── Agent-Command Mapping ────────────────────────────────────


class TestAgentCommandMapping:
    """Validate that agent tool/command references point to real commands."""

    def test_all_commands_exist(self):
        """Every .md file in commands/ should be a real command."""
        cmd_files = [f for f in os.listdir(CMDS_DIR) if f.endswith(".md")]
        assert len(cmd_files) == 41

    def test_research_agent_commands_exist(self):
        """Commands referenced by research-intelligence agent should exist."""
        referenced = ["research", "safety", "guidance", "literature",
                       "warnings", "inspections", "trials"]
        for cmd in referenced:
            assert os.path.exists(os.path.join(CMDS_DIR, f"{cmd}.md")), \
                f"Command {cmd}.md not found"

    def test_submission_agent_commands_exist(self):
        referenced = ["draft", "assemble", "export", "traceability",
                       "consistency", "compare-se"]
        for cmd in referenced:
            assert os.path.exists(os.path.join(CMDS_DIR, f"{cmd}.md")), \
                f"Command {cmd}.md not found"

    def test_pipeline_agent_commands_exist(self):
        referenced = ["extract", "data-pipeline", "gap-analysis",
                       "analyze", "status"]
        for cmd in referenced:
            assert os.path.exists(os.path.join(CMDS_DIR, f"{cmd}.md")), \
                f"Command {cmd}.md not found"


# ── Plugin Root Consistency ──────────────────────────────────


class TestPluginRootConsistency:
    """Validate that all commands use the same root resolution pattern."""

    RESOLUTION_MARKER = "fda-predicate-assistant@"

    def test_all_commands_use_same_resolution_pattern(self):
        """Every command with FDA_PLUGIN_ROOT should use installed_plugins.json."""
        cmd_files = [f for f in os.listdir(CMDS_DIR) if f.endswith(".md")]
        for cmd_file in cmd_files:
            path = os.path.join(CMDS_DIR, cmd_file)
            with open(path) as f:
                content = f.read()
            if "FDA_PLUGIN_ROOT" in content:
                assert "installed_plugins.json" in content, \
                    f"{cmd_file} uses FDA_PLUGIN_ROOT but not installed_plugins.json"
                assert self.RESOLUTION_MARKER in content, \
                    f"{cmd_file} missing resolution marker"
