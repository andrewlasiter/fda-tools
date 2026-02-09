"""Tests for v5.13.0: API contract consistency between commands and reference docs.

Validates that command .md files and their corresponding reference docs agree
on API URLs, field names, and endpoint structures. No live API calls.
"""

import os

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
REFS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "references")
TOP_REFS_DIR = os.path.join(BASE_DIR, "references")


def _read_cmd(name):
    path = os.path.join(CMDS_DIR, f"{name}.md")
    with open(path) as f:
        return f.read()


def _read_ref(name):
    path = os.path.join(REFS_DIR, f"{name}.md")
    with open(path) as f:
        return f.read()


# ── openFDA Base URL Consistency ─────────────────────────────


class TestOpenFDABaseURL:
    """Commands and refs should use consistent openFDA base URL."""

    def test_openfda_api_ref_has_base_url(self):
        ref = _read_ref("openfda-api")
        assert "api.fda.gov" in ref

    def test_research_uses_openfda(self):
        cmd = _read_cmd("research")
        assert "api.fda.gov" in cmd or "openFDA" in cmd or "fda_api_client" in cmd

    def test_safety_uses_openfda(self):
        cmd = _read_cmd("safety")
        assert "api.fda.gov" in cmd or "openFDA" in cmd or "fda_api_client" in cmd

    def test_propose_uses_openfda_base(self):
        cmd = _read_cmd("propose")
        assert "api.fda.gov" in cmd


# ── Enforcement API Consistency ──────────────────────────────


class TestEnforcementAPIConsistency:
    """warnings.md and fda-enforcement-intelligence.md should agree on API."""

    def setup_method(self):
        self.cmd = _read_cmd("warnings")
        self.ref = _read_ref("fda-enforcement-intelligence")

    def test_both_reference_enforcement_endpoint(self):
        assert "enforcement" in self.cmd
        assert "enforcement" in self.ref

    def test_both_reference_recall_fields(self):
        assert "recall" in self.cmd.lower()
        assert "recall" in self.ref.lower()

    def test_both_reference_cfr_citations(self):
        assert "21 CFR" in self.cmd
        assert "21 CFR" in self.ref

    def test_both_reference_qmsr(self):
        assert "QMSR" in self.cmd
        assert "QMSR" in self.ref


# ── ClinicalTrials.gov API Consistency ───────────────────────


class TestClinicalTrialsAPIConsistency:
    """trials.md and clinicaltrials-api.md should agree on API URL and version."""

    def setup_method(self):
        self.cmd = _read_cmd("trials")
        self.ref = _read_ref("clinicaltrials-api")

    def test_both_reference_v2_api(self):
        assert "v2" in self.cmd
        assert "v2" in self.ref

    def test_both_reference_clinicaltrials_domain(self):
        assert "clinicaltrials.gov" in self.cmd
        assert "clinicaltrials.gov" in self.ref

    def test_both_reference_studies_endpoint(self):
        assert "studies" in self.cmd
        assert "studies" in self.ref


# ── AccessGUDID API Consistency ──────────────────────────────


class TestAccessGUDIDAPIConsistency:
    """udi.md and accessgudid-api.md should agree on API details."""

    def setup_method(self):
        self.cmd = _read_cmd("udi")
        self.ref = _read_ref("accessgudid-api")

    def test_both_reference_accessgudid_domain(self):
        assert "accessgudid" in self.cmd.lower()
        assert "accessgudid" in self.ref.lower()

    def test_both_reference_v3(self):
        assert "v3" in self.cmd
        assert "v3" in self.ref

    def test_both_reference_snomed(self):
        assert "SNOMED" in self.cmd
        assert "SNOMED" in self.ref

    def test_both_reference_device_history(self):
        assert "history" in self.cmd.lower()
        assert "history" in self.ref.lower()


# ── Data Dashboard API Consistency ───────────────────────────


class TestDataDashboardAPIConsistency:
    """inspections.md and fda-dashboard-api.md should agree on API."""

    def setup_method(self):
        self.cmd = _read_cmd("inspections")
        self.ref = _read_ref("fda-dashboard-api")

    def test_both_reference_dashboard_domain(self):
        assert "api-datadashboard.fda.gov" in self.cmd
        assert "api-datadashboard.fda.gov" in self.ref

    def test_both_reference_inspections_classifications(self):
        assert "inspections_classifications" in self.cmd
        assert "inspections_classifications" in self.ref

    def test_both_reference_auth_headers(self):
        assert "Authorization-User" in self.cmd
        assert "Authorization-User" in self.ref
        assert "Authorization-Key" in self.cmd
        assert "Authorization-Key" in self.ref

    def test_both_reference_fei_number(self):
        assert "FEINumber" in self.cmd
        assert "FEINumber" in self.ref


# ── openFDA Data Dictionary Consistency ──────────────────────


class TestOpenFDADataDictionary:
    """openfda-data-dictionary.md should document key field mappings."""

    def setup_method(self):
        self.ref = _read_ref("openfda-data-dictionary")

    def test_documents_510k_fields(self):
        assert "k_number" in self.ref
        assert "device_name" in self.ref

    def test_documents_classification_fields(self):
        assert "device_class" in self.ref
        assert "product_code" in self.ref

    def test_documents_event_fields(self):
        assert "event_type" in self.ref or "device_report" in self.ref


# ── Cross-Reference: Guidance Index ──────────────────────────


class TestGuidanceIndexConsistency:
    """guidance.md and fda-guidance-index.md should share concepts."""

    def setup_method(self):
        self.cmd = _read_cmd("guidance")
        self.ref = _read_ref("fda-guidance-index")

    def test_both_reference_guidance_concept(self):
        assert "guidance" in self.cmd.lower()
        assert "guidance" in self.ref.lower()

    def test_both_reference_product_codes(self):
        assert "product code" in self.cmd.lower() or "product_code" in self.cmd
        assert "product code" in self.ref.lower() or "product_code" in self.ref
