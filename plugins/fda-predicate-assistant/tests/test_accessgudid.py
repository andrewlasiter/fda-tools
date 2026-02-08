"""Tests for v5.9.0: AccessGUDID v3 API integration (enhanced /fda:udi command).

Validates command enhancements, reference doc, and plugin metadata.
"""

import json
import os

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
REFS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "references")
PLUGIN_JSON = os.path.join(BASE_DIR, ".claude-plugin", "plugin.json")


# ── Enhanced UDI Command ───────────────────────────────────


class TestUdiCommandAccessGUDID:
    """Test udi.md has AccessGUDID v3 integration."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "udi.md")
        with open(path) as f:
            self.content = f.read()

    def test_references_accessgudid(self):
        assert "accessgudid.nlm.nih.gov" in self.content

    def test_has_v3_api(self):
        assert "/api/v3/" in self.content

    def test_has_device_lookup_endpoint(self):
        assert "devices/lookup.json" in self.content

    def test_has_device_history_endpoint(self):
        assert "devices/history.json" in self.content

    def test_has_snomed_endpoint(self):
        assert "devices/snomed.json" in self.content

    def test_has_parse_udi_endpoint(self):
        assert "parse_udi.json" in self.content

    def test_has_implantable_list_endpoint(self):
        assert "implantable_list.json" in self.content

    def test_has_history_flag(self):
        assert "--history" in self.content

    def test_has_snomed_flag(self):
        assert "--snomed" in self.content

    def test_has_parse_udi_flag(self):
        assert "--parse-udi" in self.content

    def test_has_dual_source_strategy(self):
        """Command should explain when to use openFDA vs AccessGUDID."""
        assert "openFDA" in self.content
        assert "AccessGUDID" in self.content

    def test_has_storage_conditions(self):
        assert "Storage" in self.content or "storage" in self.content

    def test_has_manufacturer_contacts(self):
        assert "Contact" in self.content or "contact" in self.content or "Phone" in self.content

    def test_has_device_history_output(self):
        assert "DEVICE HISTORY" in self.content

    def test_has_snomed_output(self):
        assert "SNOMED" in self.content

    def test_has_udi_parse_output(self):
        assert "BARCODE PARSE" in self.content or "Issuing Agency" in self.content

    def test_has_curl_for_accessgudid(self):
        assert "curl" in self.content
        assert "accessgudid.nlm.nih.gov" in self.content

    def test_still_has_openfda_query(self):
        """Existing openFDA functionality should remain."""
        assert "api.fda.gov/device/udi" in self.content

    def test_has_enrichment_section(self):
        assert "Enrichment" in self.content or "enrichment" in self.content


# ── AccessGUDID Reference Document ──────────────────────────


class TestAccessGUDIDReference:
    """Test accessgudid-api.md reference document."""

    def setup_method(self):
        path = os.path.join(REFS_DIR, "accessgudid-api.md")
        with open(path) as f:
            self.content = f.read()

    def test_file_exists(self):
        assert os.path.exists(os.path.join(REFS_DIR, "accessgudid-api.md"))

    def test_has_base_url(self):
        assert "accessgudid.nlm.nih.gov/api/v3" in self.content

    def test_documents_device_lookup(self):
        assert "Device Lookup" in self.content
        assert "devices/lookup" in self.content

    def test_documents_device_history(self):
        assert "Device History" in self.content
        assert "devices/history" in self.content

    def test_documents_parse_udi(self):
        assert "Parse UDI" in self.content
        assert "parse_udi" in self.content

    def test_documents_snomed(self):
        assert "SNOMED" in self.content
        assert "devices/snomed" in self.content

    def test_documents_implantable_list(self):
        assert "Implantable" in self.content or "implantable" in self.content

    def test_has_comparison_table(self):
        assert "openFDA" in self.content
        assert "AccessGUDID" in self.content

    def test_documents_response_fields(self):
        assert "companyName" in self.content
        assert "brandName" in self.content
        assert "deviceDescription" in self.content
        assert "storageHandling" in self.content

    def test_documents_udi_parse_fields(self):
        assert "issuingAgency" in self.content
        assert "manufacturingDate" in self.content
        assert "expirationDate" in self.content
        assert "lotNumber" in self.content
        assert "serialNumber" in self.content

    def test_documents_bulk_download(self):
        assert "download" in self.content.lower()

    def test_has_no_auth_required_note(self):
        assert "No authentication required" in self.content

    def test_documents_integration_points(self):
        assert "/fda:udi" in self.content


# ── Plugin Metadata ────────────────────────────────────────


class TestPluginVersionAndCounts59:
    """Test plugin.json reflects v5.9.0."""

    def test_version_is_5_9_0(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert data["version"] == "5.11.0"

    def test_description_mentions_accessgudid(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert "AccessGUDID" in data["description"]
