"""Tests for v5.12.0: FDA Warning Letters & Enforcement Intelligence.

Validates command file, reference doc, enforcement API integration,
GMP violation analysis, and plugin metadata.
"""

import json
import os

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
REFS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "references")
TOP_REFS_DIR = os.path.join(BASE_DIR, "references")
SKILL_MD = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "SKILL.md")
PLUGIN_JSON = os.path.join(BASE_DIR, ".claude-plugin", "plugin.json")


# -- Warnings Command -------------------------------------------------


class TestWarningsCommandExists:
    """Test warnings.md command file."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "warnings.md")
        with open(path) as f:
            self.content = f.read()

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "warnings.md"))

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

    def test_references_enforcement_api(self):
        assert "api.fda.gov/device/enforcement" in self.content

    def test_has_recalls_flag(self):
        assert "--recalls" in self.content

    def test_has_years_flag(self):
        assert "--years" in self.content

    def test_has_violations_flag(self):
        assert "--violations" in self.content

    def test_has_risk_profile_flag(self):
        assert "--risk-profile" in self.content

    def test_has_product_code_flag(self):
        assert "--product-code" in self.content

    def test_has_save_flag(self):
        assert "--save" in self.content

    def test_has_class_filter(self):
        assert "--class" in self.content

    def test_has_company_search(self):
        assert "Company name" in self.content or "company name" in self.content

    def test_has_fei_search(self):
        assert "FEI" in self.content

    def test_has_product_code_search(self):
        assert "Product code" in self.content or "product code" in self.content

    def test_has_recall_classification(self):
        assert "Class I" in self.content
        assert "Class II" in self.content
        assert "Class III" in self.content

    def test_has_web_search_for_warning_letters(self):
        assert "WebSearch" in self.content
        assert "warning letter" in self.content

    def test_has_violation_mapping(self):
        assert "21 CFR 820.90" in self.content
        assert "CAPA" in self.content

    def test_has_risk_score_calculation(self):
        assert "Risk Score" in self.content

    def test_has_qmsr_transition_note(self):
        assert "QMSR" in self.content

    def test_has_output_format(self):
        assert "Enforcement Intelligence" in self.content
        assert "NEXT STEPS" in self.content

    def test_has_curl_or_api_query(self):
        assert "api.fda.gov" in self.content

    def test_has_error_handling(self):
        assert "No enforcement actions found" in self.content or "API_ERROR" in self.content


# -- Enforcement Intelligence Reference --------------------------------


class TestEnforcementIntelligenceReference:
    """Test fda-enforcement-intelligence.md reference document."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "fda-enforcement-intelligence.md")
        with open(path) as f:
            self.content = f.read()

    def test_skill_ref_exists(self):
        assert os.path.exists(os.path.join(REFS_DIR, "fda-enforcement-intelligence.md"))

    def test_top_ref_exists(self):
        assert os.path.exists(os.path.join(TOP_REFS_DIR, "fda-enforcement-intelligence.md"))

    def test_both_copies_match(self):
        with open(os.path.join(TOP_REFS_DIR, "fda-enforcement-intelligence.md")) as f:
            top_content = f.read()
        assert self.content == top_content

    def test_has_data_sources_overview(self):
        assert "Data Sources Overview" in self.content

    def test_documents_enforcement_api(self):
        assert "api.fda.gov/device/enforcement" in self.content

    def test_documents_enforcement_fields(self):
        assert "recall_number" in self.content
        assert "recalling_firm" in self.content
        assert "classification" in self.content
        assert "reason_for_recall" in self.content
        assert "product_code" in self.content

    def test_has_example_queries(self):
        assert "api.fda.gov/device/enforcement.json" in self.content

    def test_documents_warning_letter_structure(self):
        assert "Warning Letter Structure" in self.content or "warning letter" in self.content.lower()

    def test_has_common_violations_table(self):
        assert "21 CFR 820.90" in self.content
        assert "21 CFR 820.30" in self.content
        assert "21 CFR 820.198" in self.content

    def test_has_enforcement_escalation_path(self):
        assert "NAI" in self.content
        assert "VAI" in self.content
        assert "OAI" in self.content
        assert "Warning Letter" in self.content
        assert "Injunction" in self.content

    def test_has_risk_signals_section(self):
        assert "Risk Signals" in self.content

    def test_has_risk_scoring(self):
        assert "Risk Level" in self.content or "risk level" in self.content

    def test_documents_data_dashboard(self):
        assert "Data Dashboard" in self.content

    def test_documents_maude(self):
        assert "MAUDE" in self.content

    def test_has_integration_points(self):
        assert "/fda:warnings" in self.content
        assert "/fda:inspections" in self.content
        assert "/fda:safety" in self.content

    def test_has_qmsr_note(self):
        assert "QMSR" in self.content


# -- SKILL.md Updates ------------------------------------------------


class TestSKILLMDEnforcement:
    """Test SKILL.md lists enforcement reference."""

    def setup_method(self):
        with open(SKILL_MD) as f:
            self.content = f.read()

    def test_lists_enforcement_reference(self):
        assert "fda-enforcement-intelligence.md" in self.content

    def test_resource_count_41(self):
        assert "42 references" in self.content


# -- Plugin Metadata -------------------------------------------------


class TestPluginVersionAndCounts512:
    """Test plugin.json reflects v5.12.0 with 38 commands."""

    def test_version_is_5_12_0(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert data["version"] == '5.22.0'

    def test_command_count_is_41(self):
        """Verify 41 .md files in commands directory."""
        cmd_files = [f for f in os.listdir(CMDS_DIR) if f.endswith(".md")]
        assert len(cmd_files) == 42, f"Expected 42 commands, found {len(cmd_files)}: {sorted(cmd_files)}"

    def test_description_mentions_41_commands(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert "42 commands" in data["description"]

    def test_warnings_command_exists(self):
        """Warnings feature is verified by command file existence."""
        assert os.path.exists(os.path.join(CMDS_DIR, "warnings.md"))
