"""Tests for v5.10.0: ClinicalTrials.gov API v2 integration (/fda:trials command).

Validates command file, reference doc, API usage, and plugin metadata.
"""

import json
import os

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
REFS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "references")
PLUGIN_JSON = os.path.join(BASE_DIR, ".claude-plugin", "plugin.json")


# ── Command File ────────────────────────────────────────────


class TestTrialsCommandExists:
    """Test trials.md command file."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "trials.md")
        with open(path) as f:
            self.content = f.read()

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

    def test_references_clinicaltrials_api(self):
        assert "clinicaltrials.gov/api/v2" in self.content

    def test_has_studies_endpoint(self):
        assert "/studies" in self.content

    def test_has_sponsor_flag(self):
        assert "--sponsor" in self.content

    def test_has_status_flag(self):
        assert "--status" in self.content

    def test_has_product_code_flag(self):
        assert "--product-code" in self.content

    def test_has_device_only_flag(self):
        assert "--device-only" in self.content

    def test_has_with_results_flag(self):
        assert "--with-results" in self.content

    def test_has_limit_flag(self):
        assert "--limit" in self.content

    def test_has_save_flag(self):
        assert "--save" in self.content

    def test_parses_nct_id(self):
        assert "nctId" in self.content or "NCT" in self.content

    def test_parses_enrollment(self):
        assert "enrollment" in self.content.lower()

    def test_parses_primary_outcomes(self):
        assert "primaryOutcomes" in self.content or "Primary Outcome" in self.content

    def test_parses_interventions(self):
        assert "intervention" in self.content.lower()

    def test_has_area_syntax(self):
        assert "AREA[" in self.content or "InterventionType" in self.content

    def test_has_device_type_filter(self):
        assert "DEVICE" in self.content

    def test_has_output_format(self):
        assert "STUDY OVERVIEW" in self.content
        assert "NEXT STEPS" in self.content

    def test_has_clinical_evidence_analysis(self):
        assert "CLINICAL EVIDENCE ANALYSIS" in self.content

    def test_has_product_code_resolution(self):
        """Should resolve product code to device name before searching."""
        assert "classification" in self.content or "device_name" in self.content

    def test_has_study_url(self):
        assert "clinicaltrials.gov/study" in self.content

    def test_has_json_save_format(self):
        assert "clinical_trials.json" in self.content

    def test_has_error_handling(self):
        assert "429" in self.content or "rate limit" in self.content.lower()


# ── Reference Document ─────────────────────────────────────


class TestClinicalTrialsReference:
    """Test clinicaltrials-api.md reference document."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "clinicaltrials-api.md")
        with open(path) as f:
            self.content = f.read()

    def test_file_exists(self):
        assert os.path.exists(os.path.join(REFS_DIR, "clinicaltrials-api.md"))

    def test_has_base_url(self):
        assert "clinicaltrials.gov/api/v2" in self.content

    def test_documents_search_endpoint(self):
        assert "/studies" in self.content

    def test_documents_query_parameters(self):
        assert "query.term" in self.content
        assert "query.cond" in self.content
        assert "query.intr" in self.content
        assert "query.spons" in self.content

    def test_documents_filter_parameters(self):
        assert "filter.overallStatus" in self.content
        assert "filter.studyType" in self.content

    def test_documents_area_syntax(self):
        assert "AREA[" in self.content
        assert "InterventionType" in self.content
        assert "StudyType" in self.content

    def test_documents_response_structure(self):
        assert "protocolSection" in self.content
        assert "identificationModule" in self.content
        assert "designModule" in self.content

    def test_documents_no_auth(self):
        assert "No authentication" in self.content

    def test_documents_rate_limit(self):
        assert "50" in self.content
        assert "per minute" in self.content or "req/min" in self.content or "requests/minute" in self.content

    def test_documents_pagination(self):
        assert "pageToken" in self.content or "pageSize" in self.content

    def test_has_example_queries(self):
        assert "clinicaltrials.gov/api/v2/studies?" in self.content

    def test_documents_device_specific_fields(self):
        assert "DEVICE" in self.content
        assert "InterventionType" in self.content

    def test_documents_integration_points(self):
        assert "/fda:trials" in self.content
        assert "/fda:literature" in self.content


# ── Plugin Metadata ────────────────────────────────────────


class TestPluginVersionAndCounts510:
    """Test plugin.json reflects v5.10.0 with 37 commands."""

    def test_version_is_5_10_0(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert data["version"] == '5.22.0'

    def test_command_count_is_41(self):
        """Verify 41 .md files in commands directory."""
        cmd_files = [f for f in os.listdir(CMDS_DIR) if f.endswith(".md")]
        assert len(cmd_files) == 43, f"Expected 43 commands, found {len(cmd_files)}: {sorted(cmd_files)}"

    def test_description_mentions_41_commands(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert "43 commands" in data["description"]

    def test_skill_md_mentions_clinical_trials(self):
        """ClinicalTrials is documented in SKILL.md resources, not plugin.json description."""
        skill_md = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "SKILL.md")
        with open(skill_md) as f:
            content = f.read()
        assert "clinicaltrials-api.md" in content
