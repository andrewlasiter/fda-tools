"""
E2E Coverage Expansion Tests (FDA-132)
=======================================

Extends the Traditional 510(k) E2E test suite to cover missing workflow
variations identified in FDA-132:

  - TestDeviceTypeVariations: SaMD, combination, Class U, sterile device
  - TestErrorRecovery: missing predicate, corrupt JSON, incomplete profile,
    missing SE table, empty clearances
  - TestWorkflowInterruption: partial assembly, incomplete draft, checkpoint resume

Test count: 15
Target: pytest plugins/fda_tools/tests/test_fda132_e2e_coverage.py -v
"""

import pytest

from fda_tools.tests.utils.e2e_helpers import (
    E2EWorkflowRunner,
    E2EDataManager,
    load_json_safe,
)
from fda_tools.tests.utils.regulatory_validators import RegulatoryValidator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project(tmp_path):
    """Fresh E2EWorkflowRunner in a temp directory."""
    runner = E2EWorkflowRunner(tmp_path / "test_project", mock_mode=True)
    return runner


@pytest.fixture
def project_dir(tmp_path):
    """Bare project directory path with standard sub-directories."""
    d = tmp_path / "project"
    d.mkdir()
    (d / "estar").mkdir()
    return d


# ---------------------------------------------------------------------------
# TestDeviceTypeVariations
# ---------------------------------------------------------------------------


class TestDeviceTypeVariations:
    """Four device-type scenarios that exercise different workflow branches."""

    def test_samd_device_profile(self, tmp_path):
        """SaMD (Software as a Medical Device) device profile is structured
        correctly and the software flag is preserved through workflow setup."""
        samd_profile = E2EDataManager.create_device_profile(
            product_code="QAS",
            device_class="II",
            include_software=True,
        )
        runner = E2EWorkflowRunner(tmp_path / "samd", mock_mode=True)
        result = runner.setup_project(device_profile=samd_profile)

        assert result.success
        profile_path = tmp_path / "samd" / "device_profile.json"
        data, err = load_json_safe(profile_path)
        assert err == "", f"Profile load error: {err}"
        assert data.get("samd") is True
        assert data.get("software_level") == "moderate"

    def test_combination_product_profile(self, tmp_path):
        """Combination product (device + drug) profile is written and the
        combination_product flag is round-tripped through JSON."""
        combo_profile = E2EDataManager.create_device_profile(
            product_code="FRO",
            device_class="U",
            combination_product=True,
        )
        runner = E2EWorkflowRunner(tmp_path / "combo", mock_mode=True)
        result = runner.setup_project(device_profile=combo_profile)

        assert result.success
        data, err = load_json_safe(tmp_path / "combo" / "device_profile.json")
        assert err == ""
        assert data.get("combination_product") is True
        assert data.get("primary_mode_of_action") == "device"

    def test_class_u_device_profile(self, tmp_path):
        """Class U (unclassified) device profile stores device_class='U' and
        does not have a regulation_number requirement."""
        class_u_profile = {
            "product_code": "XXX",
            "device_class": "U",
            "device_name": "Novel Unclassified Monitor",
            "regulation_number": None,
            "intended_use": "Continuous physiological monitoring.",
        }
        runner = E2EWorkflowRunner(tmp_path / "class_u", mock_mode=True)
        result = runner.setup_project(device_profile=class_u_profile)

        assert result.success
        data, err = load_json_safe(tmp_path / "class_u" / "device_profile.json")
        assert err == ""
        assert data.get("device_class") == "U"
        # Missing regulation_number must NOT block project setup
        assert result.errors == []

    def test_sterile_device_profile(self, tmp_path):
        """Sterile device profile carries sterilization metadata and
        workflow setup succeeds without errors."""
        sterile_profile = {
            "product_code": "DQY",
            "device_class": "II",
            "device_name": "Sterile Diagnostic Catheter",
            "regulation_number": "21 CFR 870.1220",
            "intended_use": "Cardiac catheterization.",
            "sterile": True,
            "sterilization_method": "Ethylene oxide",
            "shelf_life_months": 24,
        }
        runner = E2EWorkflowRunner(tmp_path / "sterile", mock_mode=True)
        result = runner.setup_project(device_profile=sterile_profile)

        assert result.success
        data, err = load_json_safe(tmp_path / "sterile" / "device_profile.json")
        assert err == ""
        assert data.get("sterile") is True
        assert data.get("sterilization_method") == "Ethylene oxide"


# ---------------------------------------------------------------------------
# TestErrorRecovery
# ---------------------------------------------------------------------------


class TestErrorRecovery:
    """Five error-recovery scenarios ensuring graceful degradation."""

    def test_missing_predicate_data(self, tmp_path):
        """Workflow initialises successfully even when review.json has no
        accepted predicates — downstream stages must not crash."""
        runner = E2EWorkflowRunner(tmp_path / "no_pred", mock_mode=True)
        runner.setup_project(product_code="DQY")

        empty_review = {
            "project": "no_pred",
            "product_code": "DQY",
            "predicates": {},
            "summary": {"total_evaluated": 0, "accepted": 0, "rejected": 0},
        }
        result = runner.run_predicate_review(review_data=empty_review)

        assert result.success
        assert result.metrics["accepted_predicates"] == 0
        # No exception raised; errors list is empty
        assert result.errors == []

    def test_corrupt_device_profile_json(self, tmp_path):
        """load_json_safe returns a non-empty error string (not an exception)
        when the JSON file contains invalid syntax."""
        corrupt = tmp_path / "device_profile.json"
        corrupt.write_text("{invalid json <<<")

        data, error = load_json_safe(corrupt)
        assert error != "", "Expected an error message for corrupt JSON"
        assert isinstance(data, dict)  # Always returns dict even on error

    def test_incomplete_device_profile_fields(self, tmp_path):
        """A device profile missing optional fields is written and readable;
        workflow setup must succeed with a minimal required-field profile."""
        minimal = {"product_code": "OVE", "device_class": "II", "device_name": "Spinal Screw"}
        runner = E2EWorkflowRunner(tmp_path / "minimal", mock_mode=True)
        result = runner.setup_project(device_profile=minimal)

        assert result.success
        data, err = load_json_safe(tmp_path / "minimal" / "device_profile.json")
        assert err == ""
        assert "product_code" in data

    def test_missing_se_table_handled(self, tmp_path):
        """Projects without se_comparison.md are recognised by SRI scoring
        as incomplete; score reflects the missing file but no exception."""
        runner = E2EWorkflowRunner(tmp_path / "no_se", mock_mode=True)
        runner.setup_project(product_code="DQY")

        validator = RegulatoryValidator(str(tmp_path / "no_se"))
        result = validator.calculate_sri_score()

        assert 0 <= result.score <= 100
        assert isinstance(result.passed, bool)
        # se_comparison.md is absent, so its points should be 0
        assert result.category_scores.get("se_comparison.md", 0) == 0

    def test_empty_clearances_does_not_crash(self, tmp_path):
        """Data collection with zero clearances produces an empty but valid
        CSV file and the stage result is marked successful."""
        runner = E2EWorkflowRunner(tmp_path / "empty_data", mock_mode=True)
        runner.setup_project(product_code="GEI")
        result = runner.run_data_collection(
            product_code="GEI",
            mock_data={"clearances": []},
        )

        assert result.success
        assert result.metrics["clearances_count"] == 0
        csv_path = tmp_path / "empty_data" / "output.csv"
        assert csv_path.exists()


# ---------------------------------------------------------------------------
# TestWorkflowInterruption
# ---------------------------------------------------------------------------


class TestWorkflowInterruption:
    """Three interruption scenarios that test incomplete-workflow behaviour."""

    def test_partial_assembly_recoverable(self, tmp_path):
        """Assembly stage with some (not all) draft sections present must
        succeed — it copies whatever drafts exist into the package."""
        runner = E2EWorkflowRunner(tmp_path / "partial", mock_mode=True)
        runner.setup_project(product_code="DQY")

        # Only draft one section (simulates interrupted drafting)
        result_draft = runner.run_drafting(sections=["device-description"])
        assert result_draft.success

        result_assembly = runner.run_assembly()
        assert result_assembly.success

        package_dir = tmp_path / "partial" / "submission_package"
        assert package_dir.exists()
        assert any(package_dir.glob("*.md")), "At least one draft should be assembled"

    def test_drafting_with_no_prior_data_collection(self, tmp_path):
        """Drafting may be invoked without running data collection first;
        it should complete with generic section content."""
        runner = E2EWorkflowRunner(tmp_path / "no_data", mock_mode=True)
        runner.setup_project(product_code="DQY")
        # Skip data collection; go straight to drafting
        result = runner.run_drafting(sections=["device-description", "se-discussion"])

        assert result.success
        assert result.metrics["sections_drafted"] == 2
        for section_name in ("device-description", "se-discussion"):
            assert (tmp_path / "no_data" / "drafts" / f"{section_name}.md").exists()

    def test_resume_from_checkpoint_device_profile_intact(self, tmp_path):
        """Simulates server restart: re-instantiating the workflow runner
        pointing at an existing project preserves device_profile.json."""
        # First run: initialise project
        runner1 = E2EWorkflowRunner(tmp_path / "checkpoint", mock_mode=True)
        profile = E2EDataManager.create_device_profile("DQY")
        runner1.setup_project(device_profile=profile)

        # Second run: resume by creating new runner on same directory
        runner2 = E2EWorkflowRunner(tmp_path / "checkpoint", mock_mode=True)
        data, err = load_json_safe(tmp_path / "checkpoint" / "device_profile.json")

        assert err == "", f"Profile should still be readable after re-init: {err}"
        assert data.get("product_code") == "DQY"
        # New runner should be able to continue drafting without errors
        result = runner2.run_drafting(sections=["device-description"])
        assert result.success
