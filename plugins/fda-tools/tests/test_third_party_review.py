"""
Tests for FDA-42: 510(k) Third Party Review Integration.

Tests the three main components:
    1. AccreditedPersonsRegistry: Reviewer lookup and filtering
    2. ThirdPartyReviewChecker: Device eligibility determination
    3. ThirdPartyPackageGenerator: Submission document generation

All tests use mocks for API calls (no network access required).
"""

import json
import os

import pytest
from unittest.mock import MagicMock

from third_party_review import (  # type: ignore
    AccreditedPersonsRegistry,
    ThirdPartyReviewChecker,
    ThirdPartyPackageGenerator,
    ACCREDITED_PERSONS,
    ADVISORY_COMMITTEES,
    INELIGIBLE_CRITERIA,
)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def registry():
    """Create a standard AccreditedPersonsRegistry."""
    return AccreditedPersonsRegistry()


@pytest.fixture
def custom_registry():
    """Create a registry with a minimal custom set for testing."""
    return AccreditedPersonsRegistry(custom_registry=[
        {
            "organization": "Test Reviewer Alpha",
            "abbreviation": "TRA",
            "accreditation_number": "AP-TEST-1",
            "specialties": ["Software/SaMD", "Cardiovascular"],
            "advisory_committees": ["CV", "SU", "OR"],
            "contact_url": "https://test-alpha.example.com",
            "status": "active",
        },
        {
            "organization": "Test Reviewer Beta",
            "abbreviation": "TRB",
            "accreditation_number": "AP-TEST-2",
            "specialties": ["Orthopedic", "Dental"],
            "advisory_committees": ["OR", "DE"],
            "contact_url": "https://test-beta.example.com",
            "status": "active",
        },
        {
            "organization": "Inactive Reviewer",
            "abbreviation": "IR",
            "accreditation_number": "AP-TEST-3",
            "specialties": ["General"],
            "advisory_committees": ["SU", "OR", "CV"],
            "contact_url": "https://inactive.example.com",
            "status": "inactive",
        },
    ])


@pytest.fixture
def mock_client_eligible():
    """Mock FDAClient returning data for an eligible Class II device."""
    client = MagicMock()

    # Classification response: Class II, third_party_flag=Y
    client.get_classification.return_value = {
        "results": [{
            "device_class": "2",
            "device_name": "Cardiovascular Catheter",
            "advisory_committee": "CV",
            "regulation_number": "870.1220",
            "third_party_flag": "Y",
            "gmp_exempt_flag": "N",
            "life_sustain_support_flag": "N",
            "product_code": "DQY",
        }],
        "meta": {"results": {"total": 1}},
    }

    # Clearance response: some with third_party_flag
    client.get_clearances.return_value = {
        "results": [
            {"k_number": "K241001", "third_party_flag": "Y",
             "device_name": "Dev A", "decision_date": "20240601"},
            {"k_number": "K241002", "third_party_flag": "N",
             "device_name": "Dev B", "decision_date": "20240501"},
            {"k_number": "K241003", "third_party_flag": "Y",
             "device_name": "Dev C", "decision_date": "20240401"},
        ],
        "meta": {"results": {"total": 3}},
    }

    return client


@pytest.fixture
def mock_client_class3():
    """Mock FDAClient returning data for a Class III device."""
    client = MagicMock()

    client.get_classification.return_value = {
        "results": [{
            "device_class": "3",
            "device_name": "Heart Valve Prosthesis",
            "advisory_committee": "CV",
            "regulation_number": "870.3925",
            "third_party_flag": "N",
            "life_sustain_support_flag": "Y",
            "product_code": "MAF",
        }],
        "meta": {"results": {"total": 1}},
    }

    return client


@pytest.fixture
def mock_client_ineligible():
    """Mock FDAClient returning data for a life-supporting device."""
    client = MagicMock()

    client.get_classification.return_value = {
        "results": [{
            "device_class": "2",
            "device_name": "Ventilator",
            "advisory_committee": "AN",
            "regulation_number": "868.5895",
            "third_party_flag": "N",
            "life_sustain_support_flag": "Y",
            "product_code": "BTK",
        }],
        "meta": {"results": {"total": 1}},
    }

    return client


@pytest.fixture
def mock_client_api_error():
    """Mock FDAClient that returns API errors."""
    client = MagicMock()
    client.get_classification.return_value = {
        "error": "API unavailable",
        "degraded": True,
    }
    return client


@pytest.fixture
def tmp_project_dir(tmp_path):
    """Create a temporary project directory with manifest."""
    proj_dir = tmp_path / "test_project"
    proj_dir.mkdir()
    manifest = {
        "project": "test_project",
        "product_codes": ["DQY"],
        "queries": {},
    }
    (proj_dir / "data_manifest.json").write_text(json.dumps(manifest, indent=2))
    return str(proj_dir)


# ===================================================================
# Tests: AccreditedPersonsRegistry
# ===================================================================


class TestAccreditedPersonsRegistry:
    """Tests for the Accredited Persons Registry."""

    def test_default_registry_has_entries(self, registry):
        """Default registry contains accredited persons."""
        assert len(registry.persons) > 0

    def test_get_all_active(self, registry):
        """get_all_active returns only active reviewers."""
        active = registry.get_all_active()
        assert len(active) > 0
        for person in active:
            assert person["status"] == "active"

    def test_find_reviewers_by_committee(self, custom_registry):
        """Finds reviewers matching advisory committee code."""
        reviewers = custom_registry.find_reviewers(advisory_committee="CV")
        assert len(reviewers) == 1
        assert reviewers[0]["abbreviation"] == "TRA"

    def test_find_reviewers_excludes_inactive(self, custom_registry):
        """Active-only filter excludes inactive reviewers."""
        reviewers = custom_registry.find_reviewers(
            advisory_committee="SU",
            active_only=True,
        )
        # Only TRA is active with SU panel
        assert len(reviewers) == 1
        assert reviewers[0]["abbreviation"] == "TRA"

    def test_find_reviewers_includes_inactive(self, custom_registry):
        """Can include inactive reviewers when active_only=False."""
        reviewers = custom_registry.find_reviewers(
            advisory_committee="SU",
            active_only=False,
        )
        assert len(reviewers) == 2  # TRA + Inactive

    def test_find_reviewers_by_specialty(self, custom_registry):
        """Finds reviewers matching specialty keyword."""
        reviewers = custom_registry.find_reviewers(specialty="software")
        assert len(reviewers) >= 1
        assert any(r["abbreviation"] == "TRA" for r in reviewers)

    def test_find_reviewers_no_match(self, custom_registry):
        """Returns empty list when no reviewers match."""
        reviewers = custom_registry.find_reviewers(advisory_committee="TX")
        assert len(reviewers) == 0

    def test_reviewers_sorted_by_score(self, custom_registry):
        """Reviewers are sorted by match_score (descending)."""
        reviewers = custom_registry.find_reviewers(advisory_committee="OR")
        assert len(reviewers) == 2  # TRA and TRB both have OR
        # Both should have match_score = 10 (advisory committee match)
        assert all(r["match_score"] >= 10 for r in reviewers)

    def test_get_committees_covered(self, custom_registry):
        """Returns coverage map of committees to reviewer count."""
        coverage = custom_registry.get_committees_covered()
        assert coverage.get("OR") == 2  # TRA and TRB
        assert coverage.get("CV") == 1  # TRA only
        assert coverage.get("DE") == 1  # TRB only

    def test_all_persons_have_required_fields(self):
        """All built-in accredited persons have required fields."""
        required_fields = {"organization", "accreditation_number",
                          "specialties", "advisory_committees", "status"}
        for person in ACCREDITED_PERSONS:
            for field in required_fields:
                assert field in person, f"Missing '{field}' in {person.get('organization', '?')}"


# ===================================================================
# Tests: ThirdPartyReviewChecker
# ===================================================================


class TestThirdPartyReviewChecker:
    """Tests for the eligibility checker."""

    def test_eligible_class2_device(self, mock_client_eligible, custom_registry):
        """Class II device with third_party_flag=Y is eligible."""
        checker = ThirdPartyReviewChecker(
            client=mock_client_eligible,
            registry=custom_registry,
        )
        result = checker.check_eligibility("DQY")

        assert result["eligible"] is True
        assert result["confidence"] == "high"
        assert result["device_class"] == 2
        assert result["third_party_flag"] == "Y"
        assert result["product_code"] == "DQY"
        assert len(result["reasons"]) > 0
        assert result["available_reviewers"] >= 1

    def test_ineligible_class3_device(self, mock_client_class3, custom_registry):
        """Class III device is NOT eligible for third-party review."""
        checker = ThirdPartyReviewChecker(
            client=mock_client_class3,
            registry=custom_registry,
        )
        result = checker.check_eligibility("MAF")

        assert result["eligible"] is False
        assert result["confidence"] == "high"
        assert result["device_class"] == 3
        assert any("Class III" in r for r in result["reasons"])

    def test_ineligible_life_supporting(self, mock_client_ineligible, custom_registry):
        """Life-supporting device is NOT eligible."""
        checker = ThirdPartyReviewChecker(
            client=mock_client_ineligible,
            registry=custom_registry,
        )
        result = checker.check_eligibility("BTK")

        assert result["eligible"] is False
        assert any("life-sustaining" in r.lower() or "life-supporting" in r.lower()
                    for r in result["reasons"])

    def test_api_error_handling(self, mock_client_api_error, custom_registry):
        """Handles API errors gracefully."""
        checker = ThirdPartyReviewChecker(
            client=mock_client_api_error,
            registry=custom_registry,
        )
        result = checker.check_eligibility("XXX")

        assert result["eligible"] is False
        assert result["confidence"] == "low"
        assert any("API error" in r for r in result["reasons"])

    def test_historical_precedent_detection(self, mock_client_eligible, custom_registry):
        """Detects historical third-party reviews for product code."""
        checker = ThirdPartyReviewChecker(
            client=mock_client_eligible,
            registry=custom_registry,
        )
        result = checker.check_eligibility("DQY")

        # Should mention historical third-party reviews
        assert any("recent clearances" in r.lower() for r in result["reasons"])

    def test_recommendations_for_eligible(self, mock_client_eligible, custom_registry):
        """Eligible devices get actionable recommendations."""
        checker = ThirdPartyReviewChecker(
            client=mock_client_eligible,
            registry=custom_registry,
        )
        result = checker.check_eligibility("DQY")

        assert len(result["recommendations"]) > 0
        assert any("contact" in r.lower() for r in result["recommendations"])

    def test_recommendations_for_ineligible(self, mock_client_class3, custom_registry):
        """Ineligible devices get appropriate recommendations."""
        checker = ThirdPartyReviewChecker(
            client=mock_client_class3,
            registry=custom_registry,
        )
        result = checker.check_eligibility("MAF")

        assert any("directly to FDA" in r.lower() or "traditional" in r.lower()
                    for r in result["recommendations"])

    def test_batch_check(self, custom_registry):
        """batch_check processes multiple product codes."""
        client = MagicMock()

        # DQY eligible
        def mock_classification(pc):
            if pc.upper() == "DQY":
                return {
                    "results": [{"device_class": "2", "device_name": "Catheter",
                                "advisory_committee": "CV", "regulation_number": "870.1220",
                                "third_party_flag": "Y", "life_sustain_support_flag": "N",
                                "product_code": "DQY"}],
                    "meta": {"results": {"total": 1}},
                }
            return {
                "results": [{"device_class": "3", "device_name": "Valve",
                            "advisory_committee": "CV", "regulation_number": "870.3925",
                            "third_party_flag": "N", "life_sustain_support_flag": "Y",
                            "product_code": "MAF"}],
                "meta": {"results": {"total": 1}},
            }

        client.get_classification.side_effect = mock_classification
        client.get_clearances.return_value = {"results": [], "meta": {"results": {"total": 0}}}

        checker = ThirdPartyReviewChecker(client=client, registry=custom_registry)
        results = checker.batch_check(["DQY", "MAF"], verbose=False)

        assert "DQY" in results
        assert "MAF" in results
        assert results["DQY"]["eligible"] is True
        assert results["MAF"]["eligible"] is False

    def test_result_has_checked_at_timestamp(self, mock_client_eligible, custom_registry):
        """Result includes a checked_at timestamp."""
        checker = ThirdPartyReviewChecker(
            client=mock_client_eligible,
            registry=custom_registry,
        )
        result = checker.check_eligibility("DQY")
        assert "checked_at" in result
        assert len(result["checked_at"]) > 10  # ISO format

    def test_reviewer_list_in_result(self, mock_client_eligible, custom_registry):
        """Result includes matching reviewers when eligible."""
        checker = ThirdPartyReviewChecker(
            client=mock_client_eligible,
            registry=custom_registry,
        )
        result = checker.check_eligibility("DQY")

        assert result["available_reviewers"] >= 1
        assert len(result["reviewers"]) >= 1
        # Reviewer entries should have essential fields
        for reviewer in result["reviewers"]:
            assert "organization" in reviewer
            assert "contact_url" in reviewer


# ===================================================================
# Tests: ThirdPartyPackageGenerator
# ===================================================================


class TestThirdPartyPackageGenerator:
    """Tests for the submission package generator."""

    def test_generate_creates_documents(self, tmp_project_dir):
        """Generate creates all required documents."""
        projects_dir = os.path.dirname(tmp_project_dir)

        generator = ThirdPartyPackageGenerator(projects_dir=projects_dir)
        result = generator.generate(
            "test_project",
            reviewer_org="TUV SUD America Inc.",
        )

        assert result["status"] == "completed"
        assert len(result["documents_generated"]) == 4
        assert "tp_cover_letter.md" in result["documents_generated"]
        assert "tp_eligibility_declaration.md" in result["documents_generated"]
        assert "tp_reviewer_selection.md" in result["documents_generated"]
        assert "tp_package_checklist.md" in result["documents_generated"]

    def test_generated_files_exist(self, tmp_project_dir):
        """All generated files physically exist on disk."""
        projects_dir = os.path.dirname(tmp_project_dir)

        generator = ThirdPartyPackageGenerator(projects_dir=projects_dir)
        result = generator.generate(
            "test_project",
            reviewer_org="BSI",
        )

        output_dir = result["output_directory"]
        for doc in result["documents_generated"]:
            path = os.path.join(output_dir, doc)
            assert os.path.exists(path), f"File not found: {path}"

    def test_cover_letter_content(self, tmp_project_dir):
        """Cover letter contains required elements."""
        projects_dir = os.path.dirname(tmp_project_dir)

        generator = ThirdPartyPackageGenerator(projects_dir=projects_dir)
        result = generator.generate(
            "test_project",
            reviewer_org="TUV SUD",
        )

        cover_path = os.path.join(result["output_directory"], "tp_cover_letter.md")
        with open(cover_path) as f:
            content = f.read()

        assert "TUV SUD" in content
        assert "Section 523" in content
        assert "DQY" in content  # From manifest product_codes
        assert "21 CFR 807.87" in content

    def test_eligibility_declaration_content(self, tmp_project_dir):
        """Eligibility declaration includes required sections."""
        projects_dir = os.path.dirname(tmp_project_dir)

        generator = ThirdPartyPackageGenerator(projects_dir=projects_dir)
        result = generator.generate(
            "test_project",
            reviewer_org="BSI",
        )

        elig_path = os.path.join(result["output_directory"], "tp_eligibility_declaration.md")
        with open(elig_path) as f:
            content = f.read()

        assert "Declaration" in content
        assert "Device Classification" in content
        assert "Life-Sustaining" in content
        assert "Attestation" in content

    def test_checklist_content(self, tmp_project_dir):
        """Checklist includes standard 510(k) items."""
        projects_dir = os.path.dirname(tmp_project_dir)

        generator = ThirdPartyPackageGenerator(projects_dir=projects_dir)
        result = generator.generate(
            "test_project",
            reviewer_org="DEKRA",
        )

        checklist_path = os.path.join(result["output_directory"], "tp_package_checklist.md")
        with open(checklist_path) as f:
            content = f.read()

        assert "Cover Sheet" in content or "Cover Letter" in content
        assert "MDUFA" in content
        assert "eSTAR" in content

    def test_nonexistent_project_returns_error(self, tmp_path):
        """Generating for nonexistent project returns error."""
        generator = ThirdPartyPackageGenerator(projects_dir=str(tmp_path))
        result = generator.generate(
            "nonexistent_project",
            reviewer_org="TUV SUD",
        )

        assert result["status"] == "error"
        assert "not found" in result.get("error", "")

    def test_eligibility_result_integrated(self, tmp_project_dir):
        """Eligibility result is integrated into the declaration."""
        projects_dir = os.path.dirname(tmp_project_dir)

        eligibility = {
            "eligible": True,
            "reasons": [
                "Classification database indicates third-party review eligible",
                "2/3 recent clearances used third-party review",
            ],
        }

        generator = ThirdPartyPackageGenerator(projects_dir=projects_dir)
        result = generator.generate(
            "test_project",
            reviewer_org="TUV SUD",
            eligibility_result=eligibility,
        )

        elig_path = os.path.join(result["output_directory"], "tp_eligibility_declaration.md")
        with open(elig_path) as f:
            content = f.read()

        assert "Classification database indicates" in content
        assert "recent clearances" in content


# ===================================================================
# Tests: Data Integrity
# ===================================================================


class TestDataIntegrity:
    """Tests verifying data quality in reference data."""

    def test_advisory_committees_complete(self):
        """All advisory committee codes used in persons are defined."""
        for person in ACCREDITED_PERSONS:
            for ac in person.get("advisory_committees", []):
                assert ac in ADVISORY_COMMITTEES, \
                    f"Unknown committee '{ac}' in {person.get('organization', '?')}"

    def test_accredited_persons_unique_ids(self):
        """All accreditation numbers are unique."""
        ids = [p["accreditation_number"] for p in ACCREDITED_PERSONS]
        assert len(ids) == len(set(ids)), "Duplicate accreditation numbers found"

    def test_all_persons_have_url(self):
        """All accredited persons have a contact URL."""
        for person in ACCREDITED_PERSONS:
            assert person.get("contact_url"), \
                f"Missing URL for {person.get('organization', '?')}"

    def test_ineligible_criteria_defined(self):
        """Ineligibility criteria are properly defined."""
        assert 3 in INELIGIBLE_CRITERIA["device_classes"]
        assert "life_sustaining" in INELIGIBLE_CRITERIA["exclusion_flags"]
