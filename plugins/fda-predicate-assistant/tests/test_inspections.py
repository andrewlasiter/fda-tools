"""Tests for v5.8.0: FDA Data Dashboard API integration (/fda:inspections command).

Validates command file, reference doc, API field coverage, and plugin metadata.
"""

import json
import os

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
REFS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "references")
PLUGIN_JSON = os.path.join(BASE_DIR, ".claude-plugin", "plugin.json")


# ── Command File ────────────────────────────────────────────


class TestInspectionsCommandExists:
    """Test inspections.md command file."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "inspections.md")
        with open(path) as f:
            self.content = f.read()

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "inspections.md"))

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

    def test_references_data_dashboard_api(self):
        assert "api-datadashboard.fda.gov" in self.content

    def test_has_inspections_classifications_endpoint(self):
        assert "inspections_classifications" in self.content

    def test_has_inspections_citations_endpoint(self):
        assert "inspections_citations" in self.content

    def test_has_compliance_actions_endpoint(self):
        assert "compliance_actions" in self.content

    def test_has_import_refusals_endpoint(self):
        assert "import_refusals" in self.content

    def test_has_auth_header_user(self):
        assert "Authorization-User" in self.content

    def test_has_auth_header_key(self):
        assert "Authorization-Key" in self.content

    def test_has_citations_flag(self):
        assert "--citations" in self.content

    def test_has_compliance_flag(self):
        assert "--compliance" in self.content

    def test_has_imports_flag(self):
        assert "--imports" in self.content

    def test_has_product_code_flag(self):
        assert "--product-code" in self.content

    def test_has_years_flag(self):
        assert "--years" in self.content

    def test_has_all_flag(self):
        assert "--all" in self.content

    def test_has_classification_codes(self):
        """Ensure NAI/VAI/OAI classification codes are documented."""
        assert "NAI" in self.content
        assert "VAI" in self.content
        assert "OAI" in self.content

    def test_has_output_format(self):
        assert "Enforcement Intelligence" in self.content
        assert "NEXT STEPS" in self.content

    def test_has_credential_setup_guidance(self):
        assert "fda_dashboard_user" in self.content
        assert "fda_dashboard_key" in self.content

    def test_filters_by_product_type_devices(self):
        assert '"Devices"' in self.content

    def test_has_fei_number_handling(self):
        """Command should handle FEI numbers as input."""
        assert "FEI" in self.content
        assert "FEINumber" in self.content

    def test_has_curl_commands(self):
        assert "curl" in self.content

    def test_has_json_request_body(self):
        assert '"sort"' in self.content
        assert '"sortorder"' in self.content
        assert '"filters"' in self.content
        assert '"columns"' in self.content

    def test_has_risk_assessment_section(self):
        assert "RISK ASSESSMENT" in self.content

    def test_has_error_handling(self):
        assert "401" in self.content or "Unauthorized" in self.content


# ── Reference Document ─────────────────────────────────────


class TestDashboardApiReference:
    """Test fda-dashboard-api.md reference document."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "fda-dashboard-api.md")
        with open(path) as f:
            self.content = f.read()

    def test_file_exists(self):
        assert os.path.exists(os.path.join(REFS_DIR, "fda-dashboard-api.md"))

    def test_has_base_url(self):
        assert "api-datadashboard.fda.gov" in self.content

    def test_documents_all_4_endpoints(self):
        assert "inspections_classifications" in self.content
        assert "inspections_citations" in self.content
        assert "compliance_actions" in self.content
        assert "import_refusals" in self.content

    def test_has_auth_instructions(self):
        assert "Authorization-User" in self.content
        assert "Authorization-Key" in self.content

    def test_documents_classification_codes(self):
        assert "No Action Indicated" in self.content or "NAI" in self.content
        assert "Voluntary Action Indicated" in self.content or "VAI" in self.content
        assert "Official Action Indicated" in self.content or "OAI" in self.content

    def test_has_field_reference_tables(self):
        assert "FEINumber" in self.content
        assert "LegalName" in self.content
        assert "InspectionEndDate" in self.content
        assert "ClassificationCode" in self.content

    def test_has_example_queries(self):
        assert "curl" in self.content
        assert "POST" in self.content

    def test_documents_pagination(self):
        assert "rows" in self.content
        assert "start" in self.content
        assert "5000" in self.content

    def test_documents_product_types(self):
        assert "Devices" in self.content
        assert "Drugs" in self.content

    def test_has_compliance_action_types(self):
        assert "Warning Letter" in self.content
        assert "Injunction" in self.content
        assert "Seizure" in self.content

    def test_has_cfr_citation_fields(self):
        assert "ActCFRNumber" in self.content
        assert "ShortDescription" in self.content

    def test_has_import_refusal_fields(self):
        assert "RefusalDate" in self.content
        assert "RefusalCharges" in self.content

    def test_documents_integration_points(self):
        assert "/fda:inspections" in self.content
        assert "/fda:safety" in self.content


# ── Plugin Metadata ────────────────────────────────────────


class TestPluginVersionAndCounts58:
    """Test plugin.json reflects v5.8.0 with 36 commands."""

    def test_version_is_5_8_0(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert data["version"] == "5.15.0"

    def test_command_count_is_37(self):
        """Verify 37 .md files in commands directory."""
        cmd_files = [f for f in os.listdir(CMDS_DIR) if f.endswith(".md")]
        assert len(cmd_files) == 38, f"Expected 38 commands, found {len(cmd_files)}: {sorted(cmd_files)}"

    def test_description_mentions_36_commands(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert "38 commands" in data["description"]

    def test_inspections_command_exists(self):
        """Inspections feature is verified by command file existence."""
        assert os.path.exists(os.path.join(CMDS_DIR, "inspections.md"))
