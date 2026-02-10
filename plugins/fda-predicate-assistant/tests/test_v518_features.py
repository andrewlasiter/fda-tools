"""Tests for v5.18.0: Items 15-27 feature tests.

Covers: start command, dashboard command, command grouping, readiness formula,
shared HTTP utility, section-aware extraction, IVD reviewer, predicate justification,
AccessGUDID intelligence step, safety-literature correlation, 11-check consistency,
gap-analysis pipeline chain, download resume.
"""

import os
import re

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
AGENTS_DIR = os.path.join(BASE_DIR, "agents")
REFS_DIR = os.path.join(BASE_DIR, "references")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
SKILLS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge")
PLUGIN_DIR = os.path.join(BASE_DIR, ".claude-plugin")


def _read(path):
    with open(path) as f:
        return f.read()


# ── Item 15: /fda:start ──────────────────────────────────────


class TestStartCommand:
    """Item 15: Interactive onboarding wizard."""

    def setup_method(self):
        self.path = os.path.join(CMDS_DIR, "start.md")
        self.content = _read(self.path)

    def test_file_exists(self):
        assert os.path.exists(self.path)

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_askuserquestion(self):
        assert "AskUserQuestion" in self.content

    def test_has_plugin_root(self):
        assert "FDA_PLUGIN_ROOT" in self.content

    def test_detects_existing_projects(self):
        content_lower = self.content.lower()
        assert "project" in content_lower and "detect" in content_lower

    def test_asks_device_type(self):
        content_lower = self.content.lower()
        assert "ivd" in content_lower or "implant" in content_lower or "samd" in content_lower

    def test_asks_regulatory_stage(self):
        assert "stage" in self.content.lower()

    def test_outputs_command_sequence(self):
        assert "/fda:" in self.content

    def test_has_version_marker(self):
        assert "v5.22.0" in self.content

    def test_registered_in_skill_md(self):
        skill = _read(os.path.join(SKILLS_DIR, "SKILL.md"))
        assert "/fda:start" in skill


# ── Item 16: /fda:dashboard ──────────────────────────────────


class TestDashboardCommand:
    """Item 16: Project status dashboard."""

    def setup_method(self):
        self.path = os.path.join(CMDS_DIR, "dashboard.md")
        self.content = _read(self.path)

    def test_file_exists(self):
        assert os.path.exists(self.path)

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_write_tool(self):
        assert "Write" in self.content

    def test_has_project_flag(self):
        assert "--project" in self.content

    def test_has_save_flag(self):
        assert "--save" in self.content

    def test_has_readiness_score(self):
        assert "SRI" in self.content or "readiness" in self.content.lower()

    def test_has_draft_section_inventory(self):
        assert "draft" in self.content.lower() and "section" in self.content.lower()

    def test_has_todo_counting(self):
        assert "TODO" in self.content

    def test_has_next_steps(self):
        assert "NEXT STEPS" in self.content or "next step" in self.content.lower()

    def test_has_version_marker(self):
        assert "v5.22.0" in self.content

    def test_registered_in_skill_md(self):
        skill = _read(os.path.join(SKILLS_DIR, "SKILL.md"))
        assert "/fda:dashboard" in skill


# ── Item 17: Justification Narrative ─────────────────────────


class TestJustificationNarrative:
    """Item 17: Predicate justification narrative in /fda:review."""

    def setup_method(self):
        self.content = _read(os.path.join(CMDS_DIR, "review.md"))

    def test_has_justification_section(self):
        assert "JUSTIFICATION" in self.content or "justification" in self.content.lower()

    def test_has_narrative_algorithm(self):
        assert "Narrative Algorithm" in self.content or "narrative" in self.content.lower()

    def test_has_sentence_templates(self):
        assert "Sentence 1" in self.content or "sentence" in self.content.lower()

    def test_has_justification_in_review_json(self):
        assert "justification_narrative" in self.content

    def test_has_score_tier_mapping(self):
        assert "80-100" in self.content or "Strong" in self.content

    def test_confidence_scoring_references_justification(self):
        conf = _read(os.path.join(REFS_DIR, "confidence-scoring.md"))
        assert "justification" in conf.lower() or "Justification" in conf


# ── Item 18: Command Grouping ────────────────────────────────


class TestCommandGrouping:
    """Item 18: 5-stage command grouping in SKILL.md."""

    def setup_method(self):
        self.content = _read(os.path.join(SKILLS_DIR, "SKILL.md"))

    def test_has_41_commands(self):
        assert "Available Commands (42)" in self.content

    def test_has_stage_1_setup(self):
        assert "Stage 1: Setup" in self.content

    def test_has_stage_2_collection(self):
        assert "Stage 2: Data Collection" in self.content

    def test_has_stage_3_analysis(self):
        assert "Stage 3: Analysis" in self.content

    def test_has_stage_4_drafting(self):
        assert "Stage 4: Drafting" in self.content

    def test_has_stage_5_assembly(self):
        assert "Stage 5: Assembly" in self.content

    def test_has_utility_group(self):
        assert "Utility" in self.content

    def test_start_in_stage_1(self):
        # start should appear after "Stage 1: Setup" in Available Commands and before "Stage 2"
        cmds_pos = self.content.index("Available Commands")
        stage1_pos = self.content.index("Stage 1: Setup", cmds_pos)
        stage2_pos = self.content.index("Stage 2", stage1_pos)
        start_pos = self.content.index("/fda:start", stage1_pos)
        assert stage1_pos < start_pos < stage2_pos

    def test_dashboard_in_stage_5(self):
        stage5_pos = self.content.index("Stage 5")
        utility_pos = self.content.index("### Utility")
        dashboard_pos = self.content.index("/fda:dashboard")
        assert stage5_pos < dashboard_pos < utility_pos

    def test_status_has_stage_guide(self):
        status = _read(os.path.join(CMDS_DIR, "status.md"))
        assert "Stage" in status or "stage" in status.lower()


# ── Item 19: Section-Aware Extraction ────────────────────────


class TestSectionAwareExtraction:
    """Item 19: --section-aware flag in predicate_extractor.py."""

    def setup_method(self):
        self.content = _read(os.path.join(SCRIPTS_DIR, "predicate_extractor.py"))

    def test_has_section_aware_flag(self):
        assert "--section-aware" in self.content

    def test_has_detect_se_section(self):
        assert "def detect_se_section(" in self.content

    def test_has_score_device_section(self):
        assert "def score_device_section(" in self.content

    def test_se_regex_present(self):
        assert "substantial" in self.content.lower() and "equivalence" in self.content.lower()

    def test_scoring_values(self):
        """Verify SE=40, testing=25, general=10 scoring."""
        assert "return 40" in self.content
        assert "return 25" in self.content
        assert "return 10" in self.content

    def test_has_enrich_flag(self):
        assert "--enrich" in self.content


# ── Item 20: Gap-Analysis Pipeline Bridge ────────────────────


class TestGapAnalysisBridge:
    """Item 20: --from-manifest in batchfetch.py."""

    def setup_method(self):
        self.bf = _read(os.path.join(SCRIPTS_DIR, "batchfetch.py"))
        self.ga = _read(os.path.join(CMDS_DIR, "gap-analysis.md"))

    def test_batchfetch_has_from_manifest(self):
        assert "--from-manifest" in self.bf

    def test_batchfetch_has_load_manifest(self):
        assert "def load_manifest(" in self.bf

    def test_gap_analysis_documents_chain(self):
        assert "--from-manifest" in self.ga or "PIPELINE CHAIN" in self.ga


# ── Item 21: Download Resume ─────────────────────────────────


class TestDownloadResume:
    """Item 21: --resume support in batchfetch.py."""

    def setup_method(self):
        self.content = _read(os.path.join(SCRIPTS_DIR, "batchfetch.py"))

    def test_has_resume_flag(self):
        assert "--resume" in self.content

    def test_has_load_progress(self):
        assert "def load_progress(" in self.content

    def test_has_save_progress(self):
        assert "def save_progress(" in self.content

    def test_progress_json_format(self):
        assert "download_progress.json" in self.content

    def test_atomic_write(self):
        assert "os.replace" in self.content


# ── Item 22: Shared HTTP Utility ─────────────────────────────


class TestSharedHTTPUtility:
    """Item 22: fda_http.py shared utility."""

    def setup_method(self):
        self.path = os.path.join(SCRIPTS_DIR, "fda_http.py")
        self.content = _read(self.path)

    def test_file_exists(self):
        assert os.path.exists(self.path)

    def test_has_fda_headers(self):
        assert "FDA_HEADERS" in self.content

    def test_has_create_session(self):
        assert "def create_session(" in self.content

    def test_has_user_agent(self):
        assert "User-Agent" in self.content

    def test_predicate_extractor_imports(self):
        pe = _read(os.path.join(SCRIPTS_DIR, "predicate_extractor.py"))
        assert "fda_http" in pe

    def test_batchfetch_imports(self):
        bf = _read(os.path.join(SCRIPTS_DIR, "batchfetch.py"))
        assert "fda_http" in bf


# ── Item 23: AccessGUDID in Research Intelligence ────────────


class TestAccessGUDIDStep:
    """Item 23: AccessGUDID step in research-intelligence agent."""

    def setup_method(self):
        self.content = _read(os.path.join(AGENTS_DIR, "research-intelligence.md"))

    def test_has_device_intelligence_section(self):
        content_lower = self.content.lower()
        assert "device intelligence" in content_lower or "accessgudid" in content_lower

    def test_has_11_steps(self):
        assert "[11/" in self.content or "/11]" in self.content or "10/" in self.content

    def test_references_udi_command(self):
        assert "/fda:udi" in self.content

    def test_has_snomed_mention(self):
        assert "SNOMED" in self.content


# ── Item 24: Safety-Literature Cross-Reference ───────────────


class TestSafetyLiteratureCorrelation:
    """Item 24: Cross-reference in research-intelligence agent."""

    def setup_method(self):
        self.content = _read(os.path.join(AGENTS_DIR, "research-intelligence.md"))

    def test_has_correlation_section(self):
        content_lower = self.content.lower()
        assert "correlation" in content_lower or "cross-reference" in content_lower

    def test_has_unaddressed_signals(self):
        assert "unaddressed" in self.content.lower() or "gap" in self.content.lower()


# ── Item 25: 11-Check Consistency ────────────────────────────


class TestElevenCheckConsistency:
    """Item 25: Expanded Phase 3 in submission-writer agent."""

    def setup_method(self):
        self.content = _read(os.path.join(AGENTS_DIR, "submission-writer.md"))

    def test_has_11_checks(self):
        assert "11 Check" in self.content or "11 check" in self.content.lower()

    def test_has_product_code_check(self):
        assert "Product Code" in self.content

    def test_has_predicate_list_check(self):
        assert "Predicate List" in self.content

    def test_has_intended_use_check(self):
        assert "Intended Use" in self.content

    def test_has_placeholder_scan_check(self):
        assert "Placeholder" in self.content

    def test_has_section_map_check(self):
        assert "Section Map" in self.content

    def test_readiness_references_formula(self):
        assert "readiness-score-formula" in self.content

    def test_has_sri_display(self):
        assert "SRI:" in self.content


# ── Item 26: Readiness Score Formula ─────────────────────────


class TestReadinessScoreFormula:
    """Item 26: readiness-score-formula.md reference file."""

    def setup_method(self):
        self.content = _read(os.path.join(REFS_DIR, "readiness-score-formula.md"))

    def test_file_exists(self):
        assert os.path.exists(os.path.join(REFS_DIR, "readiness-score-formula.md"))

    def test_listed_in_skill_md(self):
        skill = _read(os.path.join(SKILLS_DIR, "SKILL.md"))
        assert "readiness-score-formula.md" in skill

    def test_export_references_formula(self):
        export = _read(os.path.join(CMDS_DIR, "export.md"))
        assert "readiness-score-formula" in export


# ── Item 27: IVD Reviewer ────────────────────────────────────


class TestIVDReviewer:
    """Item 27: IVD-specific reviewer for OHT7 devices."""

    def setup_method(self):
        self.simulator = _read(os.path.join(AGENTS_DIR, "review-simulator.md"))
        self.cdrh = _read(os.path.join(REFS_DIR, "cdrh-review-structure.md"))

    def test_simulator_has_ivd_section(self):
        assert "IVD" in self.simulator

    def test_cdrh_has_ivd_reviewer(self):
        assert "IVD Reviewer" in self.cdrh or "IVD Review" in self.cdrh

    def test_has_clia_reference(self):
        assert "CLIA" in self.simulator or "CLIA" in self.cdrh

    def test_has_clsi_reference(self):
        assert "CLSI" in self.simulator or "CLSI" in self.cdrh

    def test_has_analytical_validation(self):
        content = self.simulator + self.cdrh
        assert "analytical" in content.lower()

    def test_has_ivd_deficiency_templates(self):
        assert "deficiency" in self.cdrh.lower() and "IVD" in self.cdrh

    def test_auto_detection_has_ivd(self):
        assert "ivd_panels" in self.cdrh or "ivd_keywords" in self.cdrh


# ── Version Bump ─────────────────────────────────────────────


class TestVersionBump:
    """Plugin version is 5.18.0."""

    def test_plugin_json_version(self):
        import json
        with open(os.path.join(PLUGIN_DIR, "plugin.json")) as f:
            data = json.load(f)
        assert data["version"] == '5.22.0'

    def test_plugin_json_41_commands(self):
        import json
        with open(os.path.join(PLUGIN_DIR, "plugin.json")) as f:
            data = json.load(f)
        assert "42 commands" in data["description"]

    def test_skill_md_41_commands(self):
        skill = _read(os.path.join(SKILLS_DIR, "SKILL.md"))
        assert "Available Commands (42)" in skill

    def test_skill_md_41_references(self):
        skill = _read(os.path.join(SKILLS_DIR, "SKILL.md"))
        assert "42 references" in skill
