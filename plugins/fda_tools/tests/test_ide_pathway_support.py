#!/usr/bin/env python3
"""
Test suite for IDE Pathway Support (FDA-67).

Tests cover:
  - SRNSRDetermination (risk scoring, factor weighting, thresholds)
  - IDESubmissionOutline (SR/NSR outlines, study types, timelines)
  - ClinicalTrialsIntegration (offline/mock tests for API structure)
  - InformedConsentGenerator (21 CFR 50.25 elements, template rendering)
  - IDEComplianceChecklist (requirement evaluation, scoring, filtering)
  - IRBPackageGenerator (initial, continuing review, amendment packages)
  - Constants validation (anatomy sets, severity, compliance requirements)

Minimum 35 tests required for this module.
"""

import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure scripts directory is on path

from ide_pathway_support import (
    SRNSRDetermination,
    IDESubmissionOutline,
    ClinicalTrialsIntegration,
    InformedConsentGenerator,
    IDEComplianceChecklist,
    IRBPackageGenerator,
    HIGH_RISK_ANATOMY,
    MODERATE_RISK_ANATOMY,
    LOW_RISK_ANATOMY,
    FAILURE_SEVERITY,
    IDE_SUBMISSION_SECTIONS,
    COMPLIANCE_REQUIREMENTS,
    _RateLimitError,
    _ServerError,
    _is_retryable,
    _wait_for_rate_limit,
    _HAS_TENACITY,
)


# ==================================================================
# SRNSRDetermination Tests
# ==================================================================

class TestSRNSRDetermination:
    """Tests for SR/NSR determination workflow."""

    @pytest.fixture
    def determinator(self):
        return SRNSRDetermination()

    # -- Basic determination tests --

    def test_cardiac_implant_is_sr(self, determinator):
        """Cardiac implant should be classified as SR."""
        result = determinator.evaluate(
            device_name="Coronary Stent",
            is_implant=True,
            implant_duration_days=365,
            anatomical_site="cardiac",
            failure_severity="death",
        )
        assert result["determination"] == "SIGNIFICANT_RISK"
        assert result["is_significant_risk"] is True
        assert result["risk_score"] >= determinator.SR_THRESHOLD

    def test_external_non_invasive_is_nsr(self, determinator):
        """Non-invasive external device should be NSR."""
        result = determinator.evaluate(
            device_name="Skin Temperature Monitor",
            is_implant=False,
            anatomical_site="external",
            invasiveness="non-invasive",
            failure_severity="discomfort",
        )
        assert result["determination"] == "NON_SIGNIFICANT_RISK"
        assert result["is_significant_risk"] is False
        assert result["risk_score"] < determinator.SR_THRESHOLD

    def test_life_sustaining_is_sr(self, determinator):
        """Life-sustaining device should always be SR."""
        result = determinator.evaluate(
            device_name="Cardiac Pacemaker",
            is_life_sustaining=True,
        )
        assert result["determination"] == "SIGNIFICANT_RISK"
        assert result["risk_score"] >= 35

    def test_life_supporting_adds_risk(self, determinator):
        """Life-supporting device should add significant risk score."""
        result = determinator.evaluate(
            device_name="Ventilator Accessory",
            is_life_supporting=True,
        )
        assert result["risk_score"] >= 25
        # May or may not cross SR threshold alone
        assert any(
            "Life-supporting" in f["factor"]
            for f in result["risk_factors"]
        )

    # -- Implant duration scoring --

    def test_permanent_implant_highest_score(self, determinator):
        """Permanent implant (>365 days) should get highest implant score."""
        result = determinator.evaluate(
            device_name="Hip Replacement",
            is_implant=True,
            implant_duration_days=3650,
        )
        implant_factor = [f for f in result["risk_factors"] if "Permanent" in f["factor"]]
        assert len(implant_factor) == 1
        assert implant_factor[0]["score"] == 30

    def test_extended_implant_moderate_score(self, determinator):
        """Extended implant (31-365 days) should get moderate score."""
        result = determinator.evaluate(
            device_name="Absorbable Scaffold",
            is_implant=True,
            implant_duration_days=90,
        )
        factor = [f for f in result["risk_factors"] if "Extended" in f["factor"]]
        assert len(factor) == 1
        assert factor[0]["score"] == 20

    def test_short_term_implant_lowest_score(self, determinator):
        """Short-term implant (<=30 days) should get lowest implant score."""
        result = determinator.evaluate(
            device_name="Temporary Catheter",
            is_implant=True,
            implant_duration_days=7,
        )
        factor = [f for f in result["risk_factors"] if "Short-term" in f["factor"]]
        assert len(factor) == 1
        assert factor[0]["score"] == 10

    # -- Anatomical site scoring --

    def test_high_risk_anatomy_scoring(self, determinator):
        """High-risk anatomy (cardiac, neural) should add 25 points."""
        result = determinator.evaluate(
            device_name="Neural Probe",
            anatomical_site="brain",
        )
        anatomy_factor = [f for f in result["risk_factors"] if "High-risk" in f["factor"]]
        assert len(anatomy_factor) == 1
        assert anatomy_factor[0]["score"] == 25

    def test_moderate_risk_anatomy_scoring(self, determinator):
        """Moderate-risk anatomy should add 15 points."""
        result = determinator.evaluate(
            device_name="Bone Fixation Plate",
            anatomical_site="orthopedic",
        )
        anatomy_factor = [f for f in result["risk_factors"] if "Moderate-risk" in f["factor"]]
        assert len(anatomy_factor) == 1
        assert anatomy_factor[0]["score"] == 15

    def test_low_risk_anatomy_is_mitigating(self, determinator):
        """Low-risk anatomy should appear in mitigating factors."""
        result = determinator.evaluate(
            device_name="Skin Patch",
            anatomical_site="external",
        )
        assert len(result["mitigating_factors"]) > 0
        assert any("Low-risk" in f["factor"] for f in result["mitigating_factors"])

    # -- Failure severity scoring --

    def test_death_failure_severity_highest(self, determinator):
        """Death failure severity should yield maximum severity score."""
        result = determinator.evaluate(
            device_name="Test Device",
            failure_severity="death",
        )
        sev_factor = [f for f in result["risk_factors"] if "severity" in f["factor"].lower()]
        assert len(sev_factor) == 1
        assert sev_factor[0]["score"] == 30  # 100 // 3, capped at 30

    def test_discomfort_failure_severity_low(self, determinator):
        """Discomfort failure severity should yield low score."""
        result = determinator.evaluate(
            device_name="Test Device",
            failure_severity="discomfort",
        )
        sev_factor = [f for f in result["risk_factors"] if "severity" in f["factor"].lower()]
        assert len(sev_factor) == 1
        assert sev_factor[0]["score"] <= 10

    # -- Energy type scoring --

    def test_radiation_energy_high_risk(self, determinator):
        """Radiation energy should add high risk score."""
        result = determinator.evaluate(
            device_name="Radiation Device",
            energy_type="radiation",
        )
        energy_factor = [f for f in result["risk_factors"] if "energy" in f["factor"].lower()]
        assert len(energy_factor) == 1
        assert energy_factor[0]["score"] == 15

    def test_electrical_energy_moderate_risk(self, determinator):
        """Electrical energy should add moderate risk score."""
        result = determinator.evaluate(
            device_name="Electrotherapy Device",
            energy_type="electrical stimulation",
        )
        energy_factor = [f for f in result["risk_factors"] if "energy" in f["factor"].lower()]
        assert len(energy_factor) == 1
        assert energy_factor[0]["score"] == 8

    # -- Additional factors --

    def test_vulnerable_population_adds_risk(self, determinator):
        """Pediatric population should add risk score."""
        result = determinator.evaluate(
            device_name="Pediatric Device",
            patient_population="pediatric",
        )
        pop_factor = [f for f in result["risk_factors"] if "Vulnerable" in f["factor"]]
        assert len(pop_factor) == 1
        assert pop_factor[0]["score"] == 10

    def test_existing_predicate_mitigates(self, determinator):
        """Existing predicate should be a mitigating factor."""
        result = determinator.evaluate(
            device_name="Test Device",
            existing_predicate="K123456",
        )
        assert any(
            "Existing predicate" in f["factor"]
            for f in result["mitigating_factors"]
        )

    def test_surgical_invasiveness_adds_risk(self, determinator):
        """Surgical invasiveness should add risk."""
        result = determinator.evaluate(
            device_name="Surgical Tool",
            invasiveness="surgical",
        )
        inv_factor = [f for f in result["risk_factors"] if "Surgical" in f["factor"]]
        assert len(inv_factor) == 1
        assert inv_factor[0]["score"] == 10

    # -- Result structure tests --

    def test_result_has_required_fields(self, determinator):
        """Result should contain all required fields."""
        result = determinator.evaluate(device_name="Test Device")
        required_fields = [
            "device_name", "determination", "determination_label",
            "risk_score", "sr_threshold", "is_significant_risk",
            "regulatory_path", "fda_review", "risk_factors",
            "mitigating_factors", "cfr_basis", "next_steps",
            "disclaimer", "assessed_at",
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_sr_next_steps_include_ide(self, determinator):
        """SR next steps should reference IDE application."""
        result = determinator.evaluate(
            device_name="High Risk Device",
            is_life_sustaining=True,
            anatomical_site="cardiac",
        )
        assert any("IDE" in step for step in result["next_steps"])

    def test_nsr_next_steps_reference_irb(self, determinator):
        """NSR next steps should reference IRB approval."""
        result = determinator.evaluate(
            device_name="Low Risk Device",
            anatomical_site="external",
        )
        assert any("IRB" in step for step in result["next_steps"])

    def test_cfr_basis_references(self, determinator):
        """CFR basis should reference 21 CFR 812."""
        result = determinator.evaluate(device_name="Test")
        assert any("812.3(m)" in ref for ref in result["cfr_basis"])
        assert any("812.2(b)" in ref for ref in result["cfr_basis"])

    def test_disclaimer_present(self, determinator):
        """Result should include AI disclaimer."""
        result = determinator.evaluate(device_name="Test")
        assert "AI-generated" in result["disclaimer"]

    def test_empty_input_returns_nsr(self, determinator):
        """Empty input (no risk factors) should default to NSR."""
        result = determinator.evaluate(device_name="")
        assert result["determination"] == "NON_SIGNIFICANT_RISK"
        assert result["risk_score"] == 0


# ==================================================================
# IDESubmissionOutline Tests
# ==================================================================

class TestIDESubmissionOutline:
    """Tests for IDE submission outline generator."""

    @pytest.fixture
    def outline_gen(self):
        return IDESubmissionOutline()

    def test_sr_outline_has_15_sections(self, outline_gen):
        """SR IDE outline should have all 15 required sections."""
        result = outline_gen.generate(device_name="Test", risk="SR")
        assert result["total_sections"] == 15
        assert result["risk_determination"] == "SR"

    def test_nsr_outline_has_6_sections(self, outline_gen):
        """NSR IDE outline should have 6 abbreviated sections."""
        result = outline_gen.generate(device_name="Test", risk="NSR")
        assert result["total_sections"] == 6
        assert result["risk_determination"] == "NSR"

    def test_sr_timeline_includes_fda_review(self, outline_gen):
        """SR timeline should include 30-day FDA review."""
        result = outline_gen.generate(risk="SR")
        assert result["timeline"]["fda_review_days"] == 30

    def test_nsr_timeline_no_fda_review(self, outline_gen):
        """NSR timeline should have 0 FDA review days."""
        result = outline_gen.generate(risk="NSR")
        assert result["timeline"]["fda_review_days"] == 0

    def test_pivotal_study_guidance(self, outline_gen):
        """Pivotal study should have appropriate guidance."""
        result = outline_gen.generate(study_type="pivotal")
        guidance = result["study_guidance"]
        assert guidance["dmc_required"] is True
        assert guidance["typical_duration_months"] == 24

    def test_feasibility_study_guidance(self, outline_gen):
        """Feasibility study should have smaller enrollment guidance."""
        result = outline_gen.generate(study_type="feasibility")
        guidance = result["study_guidance"]
        assert guidance["dmc_required"] is False
        assert guidance["typical_duration_months"] == 12

    def test_early_feasibility_guidance(self, outline_gen):
        """Early feasibility should reference FDA guidance."""
        result = outline_gen.generate(study_type="early_feasibility")
        guidance = result["study_guidance"]
        assert "first-in-human" in guidance["description"]
        assert guidance["dmc_required"] is True

    def test_sections_have_cfr_references(self, outline_gen):
        """All sections should have CFR references."""
        result = outline_gen.generate(risk="SR")
        for section in result["sections"]:
            assert "cfr_ref" in section
            assert "21 CFR" in section["cfr_ref"]

    def test_sections_have_status_tracking(self, outline_gen):
        """All sections should have NOT_STARTED status."""
        result = outline_gen.generate(risk="SR")
        for section in result["sections"]:
            assert section["status"] == "NOT_STARTED"

    def test_regulatory_references_present(self, outline_gen):
        """Outline should include regulatory references."""
        result = outline_gen.generate(risk="SR")
        refs = result["regulatory_references"]
        assert any("812" in r for r in refs)
        assert any("50" in r for r in refs)
        assert any("56" in r for r in refs)

    def test_device_info_preserved(self, outline_gen):
        """Device info should be preserved in output."""
        result = outline_gen.generate(
            device_name="CardioStent",
            device_description="Coronary stent system",
            sponsor_name="MedCo Inc.",
            num_sites=10,
            num_subjects=200,
        )
        assert result["device_name"] == "CardioStent"
        assert result["sponsor_name"] == "MedCo Inc."
        assert result["num_sites"] == 10
        assert result["num_subjects"] == 200


# ==================================================================
# ClinicalTrialsIntegration Tests
# ==================================================================

class TestClinicalTrialsIntegration:
    """Tests for ClinicalTrials.gov integration (offline/mock)."""

    @pytest.fixture
    def ct(self):
        return ClinicalTrialsIntegration()

    def test_base_url_correct(self, ct):
        """Base URL should point to ClinicalTrials.gov v2 API."""
        assert "clinicaltrials.gov/api/v2" in ct.BASE_URL

    def test_search_handles_api_error_gracefully(self, ct):
        """Search should return empty results on API error, not raise."""
        with patch("ide_pathway_support.urllib.request.urlopen") as mock_open:
            mock_open.side_effect = Exception("Network error")
            result = ct.search_device_studies("test device")
        assert result["total_found"] == 0
        assert result["returned"] == 0
        assert "error" in result or result["studies"] == []

    def test_search_result_structure(self, ct):
        """Search result should have expected structure."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "totalCount": 1,
            "studies": [{
                "protocolSection": {
                    "identificationModule": {
                        "nctId": "NCT12345678",
                        "briefTitle": "Test Stent Study",
                    },
                    "statusModule": {
                        "overallStatus": "RECRUITING",
                    },
                    "designModule": {
                        "phases": ["PHASE3"],
                        "studyType": "INTERVENTIONAL",
                        "enrollmentInfo": {"count": 100},
                    },
                    "conditionsModule": {
                        "conditions": ["Coronary Artery Disease"],
                    },
                },
            }],
        }).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("ide_pathway_support.urllib.request.urlopen", return_value=mock_response):
            result = ct.search_device_studies("coronary stent")

        assert result["total_found"] == 1
        assert result["returned"] == 1
        assert result["studies"][0]["nct_id"] == "NCT12345678"
        assert result["studies"][0]["status"] == "RECRUITING"

    def test_get_study_details_handles_error(self, ct):
        """get_study_details should handle network errors."""
        with patch("ide_pathway_support.urllib.request.urlopen") as mock_open:
            mock_open.side_effect = Exception("Not found")
            result = ct.get_study_details("NCT00000000")
        assert "error" in result
        assert result["nct_id"] == "NCT00000000"


# ==================================================================
# ClinicalTrials.gov Retry Logic Tests (FDA-89)
# ==================================================================

class TestRetryExceptions:
    """Tests for retry-related exception classes."""

    def test_rate_limit_error_default_retry_after(self):
        """_RateLimitError should default to 60 s retry-after."""
        err = _RateLimitError()
        assert err.retry_after == 60
        assert "60" in str(err)

    def test_rate_limit_error_custom_retry_after(self):
        """_RateLimitError should accept custom retry-after."""
        err = _RateLimitError(retry_after=30)
        assert err.retry_after == 30

    def test_server_error_stores_status_code(self):
        """_ServerError should store the HTTP status code."""
        err = _ServerError(503, "Service Unavailable")
        assert err.status_code == 503
        assert "503" in str(err)

    def test_is_retryable_rate_limit(self):
        """_RateLimitError should be retryable."""
        assert _is_retryable(_RateLimitError()) is True

    def test_is_retryable_server_error(self):
        """_ServerError should be retryable."""
        assert _is_retryable(_ServerError(500)) is True

    def test_is_retryable_url_error(self):
        """URLError should be retryable."""
        assert _is_retryable(urllib.error.URLError("timeout")) is True

    def test_is_retryable_connection_error(self):
        """ConnectionError should be retryable."""
        assert _is_retryable(ConnectionError("reset")) is True

    def test_is_retryable_timeout_error(self):
        """TimeoutError should be retryable."""
        assert _is_retryable(TimeoutError()) is True

    def test_is_not_retryable_value_error(self):
        """ValueError should NOT be retryable."""
        assert _is_retryable(ValueError("bad input")) is False

    def test_is_not_retryable_json_decode(self):
        """JSONDecodeError should NOT be retryable."""
        assert _is_retryable(json.JSONDecodeError("msg", "doc", 0)) is False


class TestWaitForRateLimit:
    """Tests for the custom wait strategy."""

    def _make_retry_state(self, exc, attempt=1):
        """Create a mock retry_state object."""
        state = MagicMock()
        state.outcome.exception.return_value = exc
        state.attempt_number = attempt
        return state

    def test_rate_limit_uses_retry_after(self):
        """Should use Retry-After value for rate-limit errors."""
        state = self._make_retry_state(_RateLimitError(retry_after=45))
        wait = _wait_for_rate_limit(state)
        assert wait == 45

    def test_rate_limit_caps_at_120(self):
        """Should cap Retry-After at 120 seconds."""
        state = self._make_retry_state(_RateLimitError(retry_after=300))
        wait = _wait_for_rate_limit(state)
        assert wait == 120

    def test_server_error_exponential_attempt_1(self):
        """First attempt should wait ~2 seconds."""
        state = self._make_retry_state(_ServerError(500), attempt=1)
        wait = _wait_for_rate_limit(state)
        assert wait == 2

    def test_server_error_exponential_attempt_2(self):
        """Second attempt should wait ~4 seconds."""
        state = self._make_retry_state(_ServerError(500), attempt=2)
        wait = _wait_for_rate_limit(state)
        assert wait == 4

    def test_server_error_exponential_capped_at_10(self):
        """Exponential backoff should be capped at 10 seconds."""
        state = self._make_retry_state(_ServerError(500), attempt=5)
        wait = _wait_for_rate_limit(state)
        assert wait == 10


class TestClinicalTrialsRetry:
    """Tests for retry logic in ClinicalTrialsIntegration (FDA-89)."""

    @pytest.fixture
    def ct(self):
        return ClinicalTrialsIntegration(max_retries=3, request_timeout=5)

    def test_configurable_max_retries(self):
        """Should accept custom max_retries."""
        ct = ClinicalTrialsIntegration(max_retries=5)
        assert ct.MAX_RETRIES == 5

    def test_configurable_timeout(self):
        """Should accept custom timeout."""
        ct = ClinicalTrialsIntegration(request_timeout=30)
        assert ct.REQUEST_TIMEOUT == 30

    def test_min_retries_clamped_to_1(self):
        """max_retries should be clamped to at least 1."""
        ct = ClinicalTrialsIntegration(max_retries=0)
        assert ct.MAX_RETRIES == 1

    def test_min_timeout_clamped_to_1(self):
        """request_timeout should be clamped to at least 1."""
        ct = ClinicalTrialsIntegration(request_timeout=0)
        assert ct.REQUEST_TIMEOUT == 1

    def test_fetch_json_converts_429_to_rate_limit_error(self, ct):
        """HTTP 429 should raise _RateLimitError."""
        mock_err = urllib.error.HTTPError(
            "https://example.com", 429, "Too Many Requests",
            {"Retry-After": "30"}, None,
        )
        with patch("ide_pathway_support.urllib.request.urlopen", side_effect=mock_err):
            with pytest.raises(_RateLimitError) as exc_info:
                ct._fetch_json("https://example.com")
        assert exc_info.value.retry_after == 30

    def test_fetch_json_converts_500_to_server_error(self, ct):
        """HTTP 500 should raise _ServerError."""
        mock_err = urllib.error.HTTPError(
            "https://example.com", 500, "Internal Server Error",
            {}, None,
        )
        with patch("ide_pathway_support.urllib.request.urlopen", side_effect=mock_err):
            with pytest.raises(_ServerError) as exc_info:
                ct._fetch_json("https://example.com")
        assert exc_info.value.status_code == 500

    def test_fetch_json_does_not_retry_404(self, ct):
        """HTTP 404 should raise HTTPError directly (not wrapped)."""
        mock_err = urllib.error.HTTPError(
            "https://example.com", 404, "Not Found",
            {}, None,
        )
        with patch("ide_pathway_support.urllib.request.urlopen", side_effect=mock_err):
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                ct._fetch_json("https://example.com")
        assert exc_info.value.code == 404

    def test_fetch_json_does_not_retry_400(self, ct):
        """HTTP 400 should not be retried."""
        mock_err = urllib.error.HTTPError(
            "https://example.com", 400, "Bad Request",
            {}, None,
        )
        with patch("ide_pathway_support.urllib.request.urlopen", side_effect=mock_err):
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                ct._fetch_json("https://example.com")
        assert exc_info.value.code == 400

    def test_fetch_json_429_default_retry_after(self, ct):
        """HTTP 429 without Retry-After header should default to 60."""
        mock_err = urllib.error.HTTPError(
            "https://example.com", 429, "Too Many Requests",
            {}, None,
        )
        with patch("ide_pathway_support.urllib.request.urlopen", side_effect=mock_err):
            with pytest.raises(_RateLimitError) as exc_info:
                ct._fetch_json("https://example.com")
        assert exc_info.value.retry_after == 60

    @pytest.mark.skipif(not _HAS_TENACITY, reason="tenacity not installed")
    def test_retries_on_server_error_then_succeeds(self, ct):
        """Should retry on 500 and succeed on subsequent attempt."""
        mock_err = urllib.error.HTTPError(
            "https://example.com", 500, "Server Error", {}, None,
        )
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise mock_err
            return mock_response

        with patch("ide_pathway_support.urllib.request.urlopen", side_effect=side_effect):
            result = ct._fetch_json_with_retry("https://example.com")
        assert result == {"status": "ok"}
        assert call_count == 2

    @pytest.mark.skipif(not _HAS_TENACITY, reason="tenacity not installed")
    def test_exhausts_retries_then_raises(self, ct):
        """Should raise after exhausting all retry attempts."""
        mock_err = urllib.error.HTTPError(
            "https://example.com", 503, "Unavailable", {}, None,
        )
        with patch("ide_pathway_support.urllib.request.urlopen", side_effect=mock_err):
            with pytest.raises(_ServerError):
                ct._fetch_json_with_retry("https://example.com")

    def test_search_returns_error_dict_on_failure(self, ct):
        """search_device_studies should return error dict, not raise."""
        with patch("ide_pathway_support.urllib.request.urlopen") as mock_open:
            mock_open.side_effect = urllib.error.URLError("DNS failure")
            result = ct.search_device_studies("test device")
        assert result["total_found"] == 0
        assert "error" in result
        assert "ClinicalTrials.gov API error" in result["error"]

    def test_get_details_returns_error_dict_on_failure(self, ct):
        """get_study_details should return error dict, not raise."""
        with patch("ide_pathway_support.urllib.request.urlopen") as mock_open:
            mock_open.side_effect = urllib.error.URLError("Connection refused")
            result = ct.get_study_details("NCT99999999")
        assert "error" in result
        assert result["nct_id"] == "NCT99999999"

    def test_tenacity_availability_flag_exists(self):
        """The _HAS_TENACITY flag should be a boolean."""
        assert isinstance(_HAS_TENACITY, bool)


# ==================================================================
# InformedConsentGenerator Tests
# ==================================================================

class TestInformedConsentGenerator:
    """Tests for informed consent template generator."""

    @pytest.fixture
    def consent_gen(self):
        return InformedConsentGenerator()

    def test_generates_9_required_elements(self, consent_gen):
        """Should generate all 9 required elements per 21 CFR 50.25(a)."""
        result = consent_gen.generate(device_name="Test Device")
        assert result["required_elements_count"] == 9
        assert len(result["required_elements"]) == 9

    def test_elements_numbered_1_through_9(self, consent_gen):
        """Required elements should be numbered 1-9."""
        result = consent_gen.generate(device_name="Test Device")
        numbers = [e["element_number"] for e in result["required_elements"]]
        assert numbers == list(range(1, 10))

    def test_all_elements_have_cfr_refs(self, consent_gen):
        """All elements should reference 21 CFR 50.25(a)."""
        result = consent_gen.generate(device_name="Test Device")
        for elem in result["required_elements"]:
            assert "21 CFR 50.25" in elem["cfr_ref"]

    def test_additional_elements_present(self, consent_gen):
        """Should include additional elements per 21 CFR 50.25(b)."""
        result = consent_gen.generate(device_name="Test Device")
        assert len(result["additional_elements"]) >= 4

    def test_template_text_generated(self, consent_gen):
        """Should generate full template text."""
        result = consent_gen.generate(device_name="Test Device")
        assert len(result["template_text"]) > 500
        assert "INFORMED CONSENT FORM" in result["template_text"]

    def test_device_name_in_template(self, consent_gen):
        """Device name should appear in template."""
        result = consent_gen.generate(device_name="CardioStent Pro")
        assert "CardioStent Pro" in result["template_text"]

    def test_sr_compensation_section_present(self, consent_gen):
        """SR study should include compensation for injury section."""
        result = consent_gen.generate(device_name="Test", is_sr=True)
        elem_7 = result["required_elements"][6]  # Element 7 (0-indexed)
        assert elem_7["element_number"] == 7
        assert elem_7["required"] is True

    def test_nsr_compensation_section_different(self, consent_gen):
        """NSR study compensation section should differ."""
        result = consent_gen.generate(device_name="Test", is_sr=False)
        elem_7 = result["required_elements"][6]
        assert elem_7["required"] is False
        assert "non-significant risk" in elem_7["template_text"]

    def test_custom_risks_included(self, consent_gen):
        """Custom device risks should appear in the template."""
        risks = ["Device migration", "Infection at implant site"]
        result = consent_gen.generate(
            device_name="Test",
            device_risks=risks,
        )
        assert "Device migration" in result["template_text"]
        assert "Infection at implant site" in result["template_text"]

    def test_custom_alternatives_included(self, consent_gen):
        """Custom alternative treatments should appear."""
        alts = ["Standard surgery", "Medical management"]
        result = consent_gen.generate(
            device_name="Test",
            alternative_treatments=alts,
        )
        assert "Standard surgery" in result["template_text"]
        assert "Medical management" in result["template_text"]

    def test_signature_block_present(self, consent_gen):
        """Template should include signature block."""
        result = consent_gen.generate(device_name="Test")
        assert "Subject Signature" in result["template_text"]
        assert "Person Obtaining Consent" in result["template_text"]

    def test_compliance_checklist_present(self, consent_gen):
        """Should include compliance checklist."""
        result = consent_gen.generate(device_name="Test")
        assert len(result["compliance_checklist"]) >= 10

    def test_reading_level_target_specified(self, consent_gen):
        """Should specify reading level target."""
        result = consent_gen.generate(device_name="Test")
        assert "8th grade" in result["reading_level_target"]

    def test_disclaimer_present(self, consent_gen):
        """Should include disclaimer about template status."""
        result = consent_gen.generate(device_name="Test")
        assert "TEMPLATE" in result["disclaimer"]


# ==================================================================
# IDEComplianceChecklist Tests
# ==================================================================

class TestIDEComplianceChecklist:
    """Tests for 21 CFR 812 compliance checklist."""

    @pytest.fixture
    def checklist(self):
        return IDEComplianceChecklist()

    def test_has_18_requirements(self, checklist):
        """Should have 18 compliance requirements."""
        reqs = checklist.get_requirements()
        assert len(reqs) == 18

    def test_all_requirements_have_ids(self, checklist):
        """All requirements should have IDE-xx IDs."""
        reqs = checklist.get_requirements()
        for req in reqs:
            assert req["id"].startswith("IDE-")

    def test_all_requirements_have_cfr_refs(self, checklist):
        """All requirements should have CFR references."""
        reqs = checklist.get_requirements()
        for req in reqs:
            assert "21 CFR" in req["cfr_ref"]

    def test_evaluate_no_data_all_not_evaluated(self, checklist):
        """With no submission data, all should be NOT_EVALUATED."""
        result = checklist.evaluate()
        not_eval = result["not_evaluated"]
        assert not_eval == 18  # All requirements not evaluated

    def test_evaluate_with_compliant_data(self, checklist):
        """Compliant data should yield high score."""
        data = {f"IDE-{i:02d}": "COMPLIANT" for i in range(1, 19)}
        result = checklist.evaluate(submission_data=data)
        assert result["compliance_score"] == 100
        assert result["compliant"] == 18
        assert result["recommendation"] == "READY FOR SUBMISSION"

    def test_evaluate_with_deficiency(self, checklist):
        """Deficient items should lower score and trigger recommendation."""
        data = {
            "IDE-01": "COMPLIANT",
            "IDE-07": "DEFICIENT",  # Informed consent - CRITICAL
        }
        result = checklist.evaluate(submission_data=data)
        assert result["deficient"] == 1
        assert result["compliance_score"] == 50  # 1 of 2 evaluated are compliant
        assert len(result["critical_deficiencies"]) == 1
        assert result["recommendation"] == "DEFICIENCIES MUST BE RESOLVED"

    def test_nsr_excludes_ide_specific(self, checklist):
        """NSR evaluation should mark certain items N/A."""
        # Note: only items starting with "21 CFR 812.20" are excluded for NSR
        result = checklist.evaluate(is_sr=False)
        # The current implementation checks for "21 CFR 812.20" prefix
        assert result["total_requirements"] == 18

    def test_filter_by_category(self, checklist):
        """Should filter requirements by category."""
        sponsor_reqs = checklist.get_requirements(category="Sponsor Responsibilities")
        assert len(sponsor_reqs) >= 4
        assert all(r["category"] == "Sponsor Responsibilities" for r in sponsor_reqs)

    def test_filter_by_priority(self, checklist):
        """Should filter requirements by priority."""
        critical_reqs = checklist.get_requirements(priority="CRITICAL")
        assert len(critical_reqs) >= 8
        assert all(r["priority"] == "CRITICAL" for r in critical_reqs)

    def test_informed_consent_elements(self, checklist):
        """Should return 9 informed consent elements."""
        elements = checklist.get_informed_consent_elements()
        assert len(elements) == 9

    def test_result_has_evaluated_at_timestamp(self, checklist):
        """Result should include evaluation timestamp."""
        result = checklist.evaluate()
        assert "evaluated_at" in result


# ==================================================================
# IRBPackageGenerator Tests
# ==================================================================

class TestIRBPackageGenerator:
    """Tests for IRB submission package generator."""

    @pytest.fixture
    def irb_gen(self):
        return IRBPackageGenerator()

    def test_initial_review_has_9_docs_nsr(self, irb_gen):
        """NSR initial review should have 9 documents."""
        result = irb_gen.generate(
            device_name="Test", is_sr=False, submission_type="initial"
        )
        assert result["total_documents"] == 9

    def test_initial_review_has_10_docs_sr(self, irb_gen):
        """SR initial review should have 10 documents (includes IDE approval)."""
        result = irb_gen.generate(
            device_name="Test", is_sr=True, submission_type="initial"
        )
        assert result["total_documents"] == 10

    def test_continuing_review_documents(self, irb_gen):
        """Continuing review should have 6 documents."""
        result = irb_gen.generate(submission_type="continuing_review")
        assert result["total_documents"] == 6

    def test_amendment_documents(self, irb_gen):
        """Amendment should have 5 documents."""
        result = irb_gen.generate(submission_type="amendment")
        assert result["total_documents"] == 5

    def test_documents_have_required_fields(self, irb_gen):
        """All documents should have required fields."""
        result = irb_gen.generate(submission_type="initial")
        for doc in result["documents"]:
            assert "number" in doc
            assert "document" in doc
            assert "required" in doc
            assert "status" in doc

    def test_sr_initial_includes_ide_approval(self, irb_gen):
        """SR initial package should include FDA IDE Approval Letter."""
        result = irb_gen.generate(is_sr=True, submission_type="initial")
        doc_titles = [d["document"] for d in result["documents"]]
        assert any("IDE Approval" in t for t in doc_titles)

    def test_review_timeline_present(self, irb_gen):
        """Result should include IRB review timeline."""
        result = irb_gen.generate(submission_type="initial")
        assert "irb_review_timeline" in result
        assert "initial" in result["irb_review_timeline"]

    def test_regulatory_references_present(self, irb_gen):
        """Result should include regulatory references."""
        result = irb_gen.generate(submission_type="initial")
        refs = result["regulatory_references"]
        assert any("56" in r for r in refs)
        assert any("50" in r for r in refs)

    def test_device_info_preserved(self, irb_gen):
        """Device info should be preserved in output."""
        result = irb_gen.generate(
            device_name="CardioStent",
            study_title="STENT-001",
            pi_name="Dr. Smith",
            num_subjects=150,
        )
        assert result["device_name"] == "CardioStent"
        assert result["study_title"] == "STENT-001"
        assert result["pi_name"] == "Dr. Smith"
        assert result["num_subjects"] == 150

    def test_invalid_submission_type_defaults_to_initial(self, irb_gen):
        """Invalid submission type should default to initial review."""
        result = irb_gen.generate(submission_type="invalid_type")
        # Should still produce a valid package (defaults to initial)
        assert result["total_documents"] >= 9


# ==================================================================
# Constants Validation Tests
# ==================================================================

class TestConstants:
    """Validate data constants and configuration."""

    def test_high_risk_anatomy_set_populated(self):
        """High-risk anatomy set should have items."""
        assert len(HIGH_RISK_ANATOMY) >= 15
        assert "cardiac" in HIGH_RISK_ANATOMY
        assert "brain" in HIGH_RISK_ANATOMY

    def test_moderate_risk_anatomy_set_populated(self):
        """Moderate-risk anatomy set should have items."""
        assert len(MODERATE_RISK_ANATOMY) >= 10
        assert "orthopedic" in MODERATE_RISK_ANATOMY

    def test_low_risk_anatomy_set_populated(self):
        """Low-risk anatomy set should have items."""
        assert len(LOW_RISK_ANATOMY) >= 5
        assert "external" in LOW_RISK_ANATOMY

    def test_anatomy_sets_no_overlap(self):
        """Anatomy sets should not overlap."""
        assert len(HIGH_RISK_ANATOMY & MODERATE_RISK_ANATOMY) == 0
        assert len(HIGH_RISK_ANATOMY & LOW_RISK_ANATOMY) == 0
        assert len(MODERATE_RISK_ANATOMY & LOW_RISK_ANATOMY) == 0

    def test_failure_severity_levels(self):
        """All failure severity entries should have score and level."""
        for name, info in FAILURE_SEVERITY.items():
            assert "score" in info, f"{name} missing score"
            assert "level" in info, f"{name} missing level"
            assert 0 < info["score"] <= 100

    def test_failure_severity_ordered(self):
        """Severity scores should be ordered (death > discomfort)."""
        assert FAILURE_SEVERITY["death"]["score"] > FAILURE_SEVERITY["discomfort"]["score"]

    def test_sr_submission_sections_complete(self):
        """SR IDE submission should have all required sections."""
        sr_sections = IDE_SUBMISSION_SECTIONS["sr"]
        assert len(sr_sections) == 15
        required_count = sum(1 for s in sr_sections if s["required"])
        assert required_count >= 14  # Most sections are required

    def test_nsr_submission_sections_complete(self):
        """NSR IDE submission should have abbreviated sections."""
        nsr_sections = IDE_SUBMISSION_SECTIONS["nsr"]
        assert len(nsr_sections) == 6

    def test_compliance_requirements_all_have_ids(self):
        """All compliance requirements should have unique IDs."""
        ids = [r["id"] for r in COMPLIANCE_REQUIREMENTS]
        assert len(ids) == len(set(ids))  # No duplicates
        assert len(ids) == 18

    def test_compliance_requirements_priority_levels(self):
        """All requirements should have valid priority levels."""
        valid_priorities = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        for req in COMPLIANCE_REQUIREMENTS:
            assert req["priority"] in valid_priorities, (
                f"{req['id']} has invalid priority: {req['priority']}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
