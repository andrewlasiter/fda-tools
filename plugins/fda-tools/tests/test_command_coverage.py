"""Tests for v5.13.0: Command coverage for previously untested commands.

Validates that all 20 commands lacking dedicated tests have proper structure:
frontmatter, description, allowed-tools, argument-hint, plugin root resolution,
and command-specific content assertions.
"""

import os

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")


def _read_cmd(name):
    """Read a command .md file and return its content."""
    path = os.path.join(CMDS_DIR, f"{name}.md")
    with open(path) as f:
        return f.read()


# ── calc.md ──────────────────────────────────────────────────


class TestCalcCommand:
    """Structural tests for /fda:calc command."""

    def setup_method(self):
        self.content = _read_cmd("calc")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "calc.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_shelf_life_calculator(self):
        assert "shelf-life" in self.content.lower() or "shelf life" in self.content.lower()

    def test_has_astm_f1980_reference(self):
        assert "ASTM F1980" in self.content

    def test_has_sample_size_section(self):
        assert "sample" in self.content.lower()

    def test_has_q10_factor(self):
        assert "Q10" in self.content or "q10" in self.content


# ── propose.md ───────────────────────────────────────────────


class TestProposeCommand:
    """Structural tests for /fda:propose command."""

    def setup_method(self):
        self.content = _read_cmd("propose")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "propose.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_predicates_flag(self):
        assert "--predicates" in self.content

    def test_has_confidence_scoring(self):
        assert "confidence" in self.content.lower()

    def test_has_review_json_writing(self):
        assert "review.json" in self.content

    def test_has_risk_flag_checks(self):
        assert "risk" in self.content.lower()


# ── pre-check.md ─────────────────────────────────────────────


class TestPreCheckCommand:
    """Structural tests for /fda:pre-check command."""

    def setup_method(self):
        self.content = _read_cmd("pre-check")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "pre-check.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_rta_screening(self):
        assert "RTA" in self.content

    def test_has_depth_flag(self):
        assert "--depth" in self.content

    def test_has_readiness_score(self):
        assert "readiness" in self.content.lower() or "Readiness" in self.content

    def test_has_deficiency_section(self):
        assert "deficien" in self.content.lower()


# ── gap-analysis.md ──────────────────────────────────────────


class TestGapAnalysisCommand:
    """Structural tests for /fda:gap-analysis command."""

    def setup_method(self):
        self.content = _read_cmd("gap-analysis")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "gap-analysis.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_years_flag(self):
        assert "--years" in self.content

    def test_has_product_codes_flag(self):
        assert "--product-codes" in self.content

    def test_has_pmn_reference(self):
        assert "PMN" in self.content or "pmn" in self.content

    def test_has_gap_analysis_script(self):
        assert "gap_analysis.py" in self.content


# ── data-pipeline.md ─────────────────────────────────────────


class TestDataPipelineCommand:
    """Structural tests for /fda:data-pipeline command."""

    def setup_method(self):
        self.content = _read_cmd("data-pipeline")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "data-pipeline.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_analyze_step(self):
        assert "analyze" in self.content

    def test_has_download_step(self):
        assert "download" in self.content

    def test_has_extract_step(self):
        assert "extract" in self.content

    def test_has_merge_step(self):
        assert "merge" in self.content

    def test_has_dry_run_flag(self):
        assert "--dry-run" in self.content

    def test_has_incremental_flag(self):
        assert "--incremental" in self.content


# ── draft.md ─────────────────────────────────────────────────


class TestDraftCommand:
    """Structural tests for /fda:draft command."""

    def setup_method(self):
        self.content = _read_cmd("draft")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "draft.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_device_description_section(self):
        assert "device-description" in self.content

    def test_has_se_discussion_section(self):
        assert "se-discussion" in self.content

    def test_has_project_flag(self):
        assert "--project" in self.content

    def test_has_output_flag(self):
        assert "--output" in self.content

    def test_has_infer_flag(self):
        assert "--infer" in self.content

    def test_lists_multiple_sections(self):
        sections = ["device-description", "se-discussion", "performance-summary",
                     "biocompatibility", "sterilization", "software"]
        found = sum(1 for s in sections if s in self.content)
        assert found >= 4, f"Expected at least 4 section types, found {found}"


# ── literature.md ────────────────────────────────────────────


class TestLiteratureCommand:
    """Structural tests for /fda:literature command."""

    def setup_method(self):
        self.content = _read_cmd("literature")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "literature.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_pubmed_reference(self):
        assert "PubMed" in self.content or "pubmed" in self.content

    def test_has_ncbi_api(self):
        assert "eutils.ncbi.nlm.nih.gov" in self.content or "NCBI" in self.content

    def test_has_product_code_flag(self):
        assert "--product-code" in self.content

    def test_has_depth_flag(self):
        assert "--depth" in self.content


# ── traceability.md ──────────────────────────────────────────


class TestTraceabilityCommand:
    """Structural tests for /fda:traceability command."""

    def setup_method(self):
        self.content = _read_cmd("traceability")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "traceability.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_project_flag(self):
        assert "--project" in self.content

    def test_has_requirements_concept(self):
        assert "requirement" in self.content.lower()

    def test_has_risk_management(self):
        assert "risk" in self.content.lower()

    def test_has_rtm_concept(self):
        assert "RTM" in self.content or "traceability matrix" in self.content.lower()


# ── consistency.md ───────────────────────────────────────────


class TestConsistencyCommand:
    """Structural tests for /fda:consistency command."""

    def setup_method(self):
        self.content = _read_cmd("consistency")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "consistency.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_project_flag(self):
        assert "--project" in self.content

    def test_has_fix_flag(self):
        assert "--fix" in self.content

    def test_has_consistency_checks(self):
        assert "consistency" in self.content.lower()


# ── assemble.md ──────────────────────────────────────────────


class TestAssembleCommand:
    """Structural tests for /fda:assemble command."""

    def setup_method(self):
        self.content = _read_cmd("assemble")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "assemble.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_project_flag(self):
        assert "--project" in self.content

    def test_has_estar_reference(self):
        assert "eSTAR" in self.content

    def test_has_pathway_flag(self):
        assert "--pathway" in self.content

    def test_has_directory_structure(self):
        assert "directory" in self.content.lower() or "folder" in self.content.lower()


# ── udi.md ───────────────────────────────────────────────────


class TestUdiCommand:
    """Structural tests for /fda:udi command."""

    def setup_method(self):
        self.content = _read_cmd("udi")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "udi.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_accessgudid_api(self):
        assert "accessgudid" in self.content.lower()

    def test_has_openfda_udi_endpoint(self):
        assert "api.fda.gov/device/udi" in self.content

    def test_has_product_code_flag(self):
        assert "--product-code" in self.content

    def test_has_history_flag(self):
        assert "--history" in self.content

    def test_has_snomed_flag(self):
        assert "--snomed" in self.content

    def test_has_parse_udi_flag(self):
        assert "--parse-udi" in self.content


# ── trials.md ────────────────────────────────────────────────


class TestTrialsCommand:
    """Structural tests for /fda:trials command."""

    def setup_method(self):
        self.content = _read_cmd("trials")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "trials.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_clinicaltrials_api(self):
        assert "clinicaltrials.gov" in self.content

    def test_has_sponsor_flag(self):
        assert "--sponsor" in self.content

    def test_has_status_flag(self):
        assert "--status" in self.content

    def test_has_device_only_flag(self):
        assert "--device-only" in self.content


# ── ask.md ───────────────────────────────────────────────────


class TestAskCommand:
    """Structural tests for /fda:ask command."""

    def setup_method(self):
        self.content = _read_cmd("ask")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "ask.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_websearch_tool(self):
        assert "WebSearch" in self.content

    def test_has_product_code_flag(self):
        assert "--product-code" in self.content

    def test_has_qa_categories(self):
        terms = ["classification", "pathway", "guidance"]
        found = sum(1 for t in terms if t.lower() in self.content.lower())
        assert found >= 2, f"Expected at least 2 Q&A categories, found {found}"


# ── pccp.md ──────────────────────────────────────────────────


class TestPccpCommand:
    """Structural tests for /fda:pccp command."""

    def setup_method(self):
        self.content = _read_cmd("pccp")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "pccp.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_modification_type_flag(self):
        assert "--modification-type" in self.content

    def test_has_pccp_concept(self):
        assert "PCCP" in self.content or "Predetermined Change Control" in self.content

    def test_has_aiml_context(self):
        assert "AI/ML" in self.content or "algorithm" in self.content.lower()


# ── portfolio.md ─────────────────────────────────────────────


class TestPortfolioCommand:
    """Structural tests for /fda:portfolio command."""

    def setup_method(self):
        self.content = _read_cmd("portfolio")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "portfolio.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_output_flag(self):
        assert "--output" in self.content

    def test_has_format_flag(self):
        assert "--format" in self.content

    def test_has_project_discovery(self):
        assert "project" in self.content.lower()


# ── monitor.md ───────────────────────────────────────────────


class TestMonitorCommand:
    """Structural tests for /fda:monitor command."""

    def setup_method(self):
        self.content = _read_cmd("monitor")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "monitor.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_check_flag(self):
        assert "--check" in self.content

    def test_has_add_watch_flag(self):
        assert "--add-watch" in self.content

    def test_has_status_flag(self):
        assert "--status" in self.content

    def test_has_alerts_flag(self):
        assert "--alerts" in self.content

    def test_has_webhook_support(self):
        assert "webhook" in self.content.lower()

    def test_has_cron_flag(self):
        assert "--cron" in self.content

    def test_has_watch_standards(self):
        assert "--watch-standards" in self.content


# ── pathway.md ───────────────────────────────────────────────


class TestPathwayCommand:
    """Structural tests for /fda:pathway command."""

    def setup_method(self):
        self.content = _read_cmd("pathway")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "pathway.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_product_code_flag(self):
        assert "--product-code" in self.content or "product-code" in self.content

    def test_has_pathway_types(self):
        pathways = ["Traditional", "Special", "Abbreviated", "De Novo", "PMA"]
        found = sum(1 for p in pathways if p in self.content)
        assert found >= 3, f"Expected at least 3 pathway types, found {found}"

    def test_has_classification_api(self):
        assert "classification" in self.content.lower()

    def test_has_scoring(self):
        assert "scor" in self.content.lower()


# ── test-plan.md ─────────────────────────────────────────────


class TestTestPlanCommand:
    """Structural tests for /fda:test-plan command."""

    def setup_method(self):
        self.content = _read_cmd("test-plan")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "test-plan.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_has_product_code_flag(self):
        assert "--product-code" in self.content

    def test_has_project_flag(self):
        assert "--project" in self.content

    def test_has_risk_framework(self):
        assert "risk" in self.content.lower()

    def test_has_test_categories(self):
        assert "test" in self.content.lower()

    def test_has_output_flag(self):
        assert "--output" in self.content


# ── inspections.md ───────────────────────────────────────────


class TestInspectionsCommandCoverage:
    """Additional structural tests for /fda:inspections."""

    def setup_method(self):
        self.content = _read_cmd("inspections")

    def test_has_all_flag(self):
        assert "--all" in self.content or "--citations" in self.content

    def test_has_data_dashboard_url(self):
        assert "api-datadashboard.fda.gov" in self.content

    def test_has_fei_handling(self):
        assert "FEI" in self.content


# ── warnings.md ──────────────────────────────────────────────


class TestWarningsCommandCoverage:
    """Additional structural tests for /fda:warnings."""

    def setup_method(self):
        self.content = _read_cmd("warnings")

    def test_has_enforcement_api(self):
        assert "api.fda.gov/device/enforcement" in self.content

    def test_has_gmp_violations(self):
        assert "GMP" in self.content or "21 CFR 820" in self.content

    def test_has_qmsr(self):
        assert "QMSR" in self.content
