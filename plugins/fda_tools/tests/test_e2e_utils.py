"""
Tests for E2E Test Infrastructure

Validates the E2E helper utilities and regulatory validators.

Version: 1.0.0
Date: 2026-02-20
Issue: FDA-174 (QA-001)
"""

import json
import pytest
from datetime import datetime
from pathlib import Path

from tests.utils.e2e_helpers import (
    E2EWorkflowRunner,
    E2EDataManager,
    E2EAssertions,
    WorkflowStage,
    WorkflowResult,
)

from tests.utils.regulatory_validators import (
    CFRValidator,
    EStarValidator,
    PredicateValidator,
    SubstantialEquivalenceValidator,
    ValidationSeverity,
)


class TestE2EWorkflowRunner:
    """Test E2EWorkflowRunner functionality."""

    def test_workflow_runner_initialization(self, tmp_path):
        """Test workflow runner initialization."""
        project_dir = tmp_path / "test_project"
        runner = E2EWorkflowRunner(project_dir, workflow_type="traditional_510k")

        assert runner.project_dir == project_dir
        assert runner.workflow_type == "traditional_510k"
        assert runner.mock_mode is True
        assert len(runner.results) == 0

        # Check standard directories created
        assert (project_dir / "data").exists()
        assert (project_dir / "drafts").exists()

    def test_setup_project_with_product_code(self, tmp_path):
        """Test project setup with product code."""
        project_dir = tmp_path / "test_project"
        runner = E2EWorkflowRunner(project_dir)

        result = runner.setup_project(product_code="DQY")

        assert result.stage == WorkflowStage.INITIALIZATION
        assert result.success is True
        assert result.passed is True
        assert "device_profile" in result.artifacts
        assert "query" in result.artifacts

        # Check files created
        device_profile_path = project_dir / "device_profile.json"
        assert device_profile_path.exists()

        with open(device_profile_path) as f:
            profile = json.load(f)
        assert profile["product_code"] == "DQY"

    def test_setup_project_with_custom_profile(self, tmp_path):
        """Test project setup with custom device profile."""
        project_dir = tmp_path / "test_project"
        runner = E2EWorkflowRunner(project_dir)

        device_profile = {
            "product_code": "QAS",
            "device_name": "Custom PACS System",
            "device_class": "II",
        }

        result = runner.setup_project(device_profile=device_profile)

        assert result.passed is True
        assert result.metrics["product_code"] == "QAS"

    def test_run_data_collection_with_mock_data(self, tmp_path):
        """Test data collection with mock data."""
        project_dir = tmp_path / "test_project"
        runner = E2EWorkflowRunner(project_dir, mock_mode=True)

        mock_data = {
            "clearances": [
                {"k_number": "K241001", "product_code": "DQY"},
                {"k_number": "K241002", "product_code": "DQY"},
            ]
        }

        result = runner.run_data_collection(
            product_code="DQY",
            mock_data=mock_data,
        )

        assert result.passed is True
        assert result.metrics["clearances_count"] == 2
        assert "output_csv" in result.artifacts

    def test_run_predicate_review(self, tmp_path):
        """Test predicate review stage."""
        project_dir = tmp_path / "test_project"
        runner = E2EWorkflowRunner(project_dir)

        review_data = {
            "project": "test_project",
            "product_code": "DQY",
            "predicates": {
                "K213456": {
                    "device_name": "Test Predicate",
                    "decision": "accepted",
                    "confidence_score": 92,
                }
            },
            "summary": {
                "total_evaluated": 1,
                "accepted": 1,
                "rejected": 0,
            },
        }

        result = runner.run_predicate_review(review_data=review_data)

        assert result.passed is True
        assert result.metrics["total_predicates"] == 1
        assert result.metrics["accepted_predicates"] == 1

        # Check review.json created
        review_path = project_dir / "review.json"
        assert review_path.exists()

    def test_run_drafting(self, tmp_path):
        """Test drafting stage."""
        project_dir = tmp_path / "test_project"
        runner = E2EWorkflowRunner(project_dir)

        sections = ["device-description", "se-discussion"]
        result = runner.run_drafting(sections=sections)

        assert result.passed is True
        assert result.metrics["sections_drafted"] == 2

        # Check draft files created
        for section in sections:
            draft_path = project_dir / "drafts" / f"{section}.md"
            assert draft_path.exists()
            assert draft_path.read_text().startswith("#")

    def test_run_assembly(self, tmp_path):
        """Test assembly stage."""
        project_dir = tmp_path / "test_project"
        runner = E2EWorkflowRunner(project_dir)

        # Create some draft files first
        runner.run_drafting()

        result = runner.run_assembly()

        assert result.passed is True
        assert "package_dir" in result.artifacts

        package_dir = project_dir / "submission_package"
        assert package_dir.exists()

    def test_complete_workflow(self, tmp_path):
        """Test complete workflow execution."""
        project_dir = tmp_path / "test_project"
        runner = E2EWorkflowRunner(project_dir)

        # Run complete workflow
        runner.setup_project(product_code="DQY")
        runner.run_data_collection(product_code="DQY", mock_data={"clearances": []})
        runner.run_predicate_review()
        runner.run_drafting()
        runner.run_assembly()

        # Check all stages completed
        results = runner.get_results()
        assert len(results) == 5

        # Get summary
        summary = runner.get_summary()
        assert summary["total_stages"] == 5
        assert summary["passed_stages"] == 5
        assert summary["failed_stages"] == 0

    def test_workflow_error_handling(self, tmp_path):
        """Test workflow error handling."""
        project_dir = tmp_path / "test_project"
        runner = E2EWorkflowRunner(project_dir)

        # Try to setup without product code or profile (should fail)
        result = runner.setup_project()

        assert result.success is False
        assert not result.passed
        assert len(result.errors) > 0


class TestE2EDataManager:
    """Test E2EDataManager functionality."""

    def test_create_device_profile_basic(self):
        """Test basic device profile creation."""
        profile = E2EDataManager.create_device_profile(
            product_code="DQY",
            device_class="II",
        )

        assert profile["product_code"] == "DQY"
        assert profile["device_class"] == "II"
        assert "device_name" in profile
        assert "intended_use" in profile

    def test_create_device_profile_with_software(self):
        """Test device profile with software components."""
        profile = E2EDataManager.create_device_profile(
            product_code="QKQ",
            include_software=True,
        )

        assert profile["samd"] is True
        assert "software_level" in profile

    def test_create_device_profile_combination_product(self):
        """Test combination product profile."""
        profile = E2EDataManager.create_device_profile(
            product_code="FRO",
            combination_product=True,
        )

        assert profile["combination_product"] is True
        assert "primary_mode_of_action" in profile

    def test_create_predicate_data_accepted(self):
        """Test accepted predicate data creation."""
        predicate = E2EDataManager.create_predicate_data(
            k_number="K213456",
            product_code="DQY",
            decision="accepted",
            confidence_score=92,
        )

        assert predicate["decision"] == "accepted"
        assert predicate["confidence_score"] == 92
        assert len(predicate["risk_flags"]) == 0

    def test_create_predicate_data_rejected(self):
        """Test rejected predicate data creation."""
        predicate = E2EDataManager.create_predicate_data(
            k_number="K190987",
            product_code="DQY",
            decision="rejected",
            confidence_score=35,
        )

        assert predicate["decision"] == "rejected"
        assert len(predicate["risk_flags"]) > 0

    def test_create_review_data(self):
        """Test review data creation."""
        predicates = {
            "K213456": E2EDataManager.create_predicate_data(
                "K213456", "DQY", "accepted", 92
            ),
            "K190987": E2EDataManager.create_predicate_data(
                "K190987", "DQY", "rejected", 35
            ),
        }

        review = E2EDataManager.create_review_data("DQY", predicates)

        assert review["product_code"] == "DQY"
        assert review["summary"]["total_evaluated"] == 2
        assert review["summary"]["accepted"] == 1
        assert review["summary"]["rejected"] == 1


class TestE2EAssertions:
    """Test E2EAssertions functionality."""

    def test_assert_project_structure_valid(self, tmp_path):
        """Test project structure validation."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create required files and directories
        (project_dir / "device_profile.json").write_text("{}")
        (project_dir / "query.json").write_text("{}")
        (project_dir / "drafts").mkdir()
        (project_dir / "data").mkdir()

        # Should not raise
        E2EAssertions.assert_project_structure_valid(project_dir)

    def test_assert_project_structure_missing_file(self, tmp_path):
        """Test project structure validation with missing file."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        with pytest.raises(AssertionError, match="Missing required file"):
            E2EAssertions.assert_project_structure_valid(project_dir)

    def test_assert_device_profile_valid(self):
        """Test device profile validation."""
        profile = {
            "product_code": "DQY",
            "device_class": "II",
            "device_name": "Test Device",
        }

        # Should not raise
        E2EAssertions.assert_device_profile_valid(profile)

    def test_assert_device_profile_invalid_product_code(self):
        """Test device profile validation with invalid product code."""
        profile = {
            "product_code": "invalid",  # Must be 3 uppercase letters
            "device_class": "II",
            "device_name": "Test Device",
        }

        with pytest.raises(AssertionError, match="Product code must be 3 characters"):
            E2EAssertions.assert_device_profile_valid(profile)

    def test_assert_review_data_valid(self):
        """Test review data validation."""
        review = {
            "product_code": "DQY",
            "predicates": {
                "K213456": {"decision": "accepted"},
                "K190987": {"decision": "rejected"},
            },
            "summary": {
                "total_evaluated": 2,
                "accepted": 1,
                "rejected": 1,
            },
        }

        # Should not raise
        E2EAssertions.assert_review_data_valid(review)

    def test_assert_review_data_count_mismatch(self):
        """Test review data validation with count mismatch."""
        review = {
            "product_code": "DQY",
            "predicates": {
                "K213456": {"decision": "accepted"},
            },
            "summary": {
                "total_evaluated": 2,  # Incorrect count
                "accepted": 1,
                "rejected": 0,
            },
        }

        with pytest.raises(AssertionError, match="total count mismatch"):
            E2EAssertions.assert_review_data_valid(review)

    def test_assert_workflow_completed_successfully(self):
        """Test workflow completion validation."""
        results = [
            WorkflowResult(
                stage=WorkflowStage.INITIALIZATION,
                success=True,
                duration=0.5,
            ),
            WorkflowResult(
                stage=WorkflowStage.DRAFTING,
                success=True,
                duration=1.2,
            ),
        ]

        # Should not raise
        E2EAssertions.assert_workflow_completed_successfully(results)

    def test_assert_workflow_with_failure(self):
        """Test workflow validation with failed stage."""
        results = [
            WorkflowResult(
                stage=WorkflowStage.INITIALIZATION,
                success=True,
                duration=0.5,
            ),
            WorkflowResult(
                stage=WorkflowStage.DRAFTING,
                success=False,
                duration=0.1,
                errors=["Test error"],
            ),
        ]

        with pytest.raises(AssertionError, match="failed"):
            E2EAssertions.assert_workflow_completed_successfully(results)

    def test_assert_draft_section_valid(self, tmp_path):
        """Test draft section validation."""
        section_path = tmp_path / "device-description.md"
        section_path.write_text("# Device Description\n\nTest content")

        # Should not raise
        E2EAssertions.assert_draft_section_valid(section_path)

    def test_assert_clearances_csv_valid(self, tmp_path):
        """Test clearances CSV validation."""
        csv_path = tmp_path / "output.csv"
        csv_path.write_text("K-Number,Product Code\nK241001,DQY\nK241002,DQY\n")

        # Should not raise
        E2EAssertions.assert_clearances_csv_valid(csv_path, min_rows=2)


class TestCFRValidator:
    """Test CFRValidator functionality."""

    def test_validate_part_11_compliance_with_signatures(self):
        """Test Part 11 validation with signatures."""
        validator = CFRValidator()

        submission_data = {
            "signatures": [
                {"name": "John Doe", "role": "Authorized Representative"},
            ],
            "audit_trail": [],
            "version": "1.0",
        }

        results = validator.validate_part_11_compliance(submission_data)

        # Should have results for signatures, audit trail, version
        assert len(results) >= 3
        assert validator.get_summary()["passed"] >= 3

    def test_validate_part_11_compliance_missing_elements(self):
        """Test Part 11 validation with missing elements."""
        validator = CFRValidator()

        submission_data = {}  # Missing everything

        results = validator.validate_part_11_compliance(submission_data)

        # Should have warnings/failures
        summary = validator.get_summary()
        assert summary["failed"] > 0

    def test_validate_device_classification_valid(self):
        """Test device classification validation with valid data."""
        validator = CFRValidator()

        results = validator.validate_device_classification(
            product_code="DQY",
            device_class="II",
            regulation_number="21 CFR 870.1340",
        )

        # All checks should pass
        assert all(r.passed for r in results)
        assert validator.get_summary()["overall_status"] == "PASS"

    def test_validate_device_classification_invalid_product_code(self):
        """Test device classification with invalid product code."""
        validator = CFRValidator()

        results = validator.validate_device_classification(
            product_code="invalid",  # Not 3 uppercase letters
            device_class="II",
        )

        # Should have error for product code
        assert any(r.severity == ValidationSeverity.ERROR for r in results)

    def test_validate_device_classification_invalid_class(self):
        """Test device classification with invalid class."""
        validator = CFRValidator()

        results = validator.validate_device_classification(
            product_code="DQY",
            device_class="IV",  # Invalid class
        )

        # Should have error for device class
        assert any(r.severity == ValidationSeverity.ERROR for r in results)


class TestPredicateValidator:
    """Test PredicateValidator functionality."""

    def test_validate_predicate_acceptability_same_product_code(self):
        """Test predicate validation with matching product codes."""
        validator = PredicateValidator()

        subject = {"product_code": "DQY"}
        predicate = {
            "product_code": "DQY",
            "decision": "SUBSTANTIALLY EQUIVALENT",
            "decision_date": "2023-01-15",
        }

        results = validator.validate_predicate_acceptability(subject, predicate)

        # Should pass product code and cleared checks
        passed = [r for r in results if r.passed]
        assert len(passed) >= 2

    def test_validate_predicate_acceptability_different_product_code(self):
        """Test predicate validation with different product codes."""
        validator = PredicateValidator()

        subject = {"product_code": "DQY"}
        predicate = {
            "product_code": "QAS",  # Different
            "decision": "SUBSTANTIALLY EQUIVALENT",
        }

        results = validator.validate_predicate_acceptability(subject, predicate)

        # Should have error for different product codes
        assert any(
            r.check_name == "same_product_code" and not r.passed
            for r in results
        )

    def test_validate_predicate_acceptability_not_cleared(self):
        """Test predicate validation with non-cleared device."""
        validator = PredicateValidator()

        subject = {"product_code": "DQY"}
        predicate = {
            "product_code": "DQY",
            "decision": "NOT SUBSTANTIALLY EQUIVALENT",  # NSE
        }

        results = validator.validate_predicate_acceptability(subject, predicate)

        # Should have critical error for NSE predicate
        assert any(
            r.check_name == "predicate_cleared"
            and r.severity == ValidationSeverity.CRITICAL
            for r in results
        )

    def test_validate_predicate_chain_single_predicate(self):
        """Test predicate chain with single predicate."""
        validator = PredicateValidator()

        predicates = [{"product_code": "DQY"}]

        results = validator.validate_predicate_chain(predicates)

        # Should pass with single predicate
        assert validator.get_summary()["overall_status"] == "PASS"

    def test_validate_predicate_chain_many_predicates(self):
        """Test predicate chain with many predicates."""
        validator = PredicateValidator()

        predicates = [{"product_code": "DQY"} for _ in range(5)]

        results = validator.validate_predicate_chain(predicates)

        # Should have warning about too many predicates
        assert any(
            r.check_name == "predicate_count" and r.severity == ValidationSeverity.WARNING
            for r in results
        )


class TestSubstantialEquivalenceValidator:
    """Test SubstantialEquivalenceValidator functionality."""

    def test_validate_se_comparison_equivalent_intended_use(self):
        """Test SE comparison with equivalent intended use."""
        validator = SubstantialEquivalenceValidator()

        comparison_data = {
            "intended_use": {"equivalent": True},
            "technology": {"differences": []},
            "performance_data": {"bench_testing": {}, "biocompatibility": {}},
        }

        results = validator.validate_se_comparison(comparison_data)

        # Should have passing results
        assert validator.get_summary()["overall_status"] == "PASS"

    def test_validate_se_comparison_different_intended_use(self):
        """Test SE comparison with different intended use."""
        validator = SubstantialEquivalenceValidator()

        comparison_data = {
            "intended_use": {"equivalent": False},
        }

        results = validator.validate_se_comparison(comparison_data)

        # Should have critical error
        assert validator.has_critical_errors()

    def test_validate_se_discussion_complete(self, tmp_path):
        """Test SE discussion validation with complete content."""
        validator = SubstantialEquivalenceValidator()

        discussion_path = tmp_path / "se-discussion.md"
        discussion_path.write_text("""
# Substantial Equivalence Discussion

## Intended Use
The subject device has the same intended use as predicate K213456.

## Technological Characteristics
The devices share the same technological characteristics with minor differences
in materials.

## Performance Testing
Bench testing demonstrates equivalence. Testing included:
- Biocompatibility per ISO 10993
- Performance validation
        """)

        results = validator.validate_se_discussion(discussion_path)

        # Should have mostly passing results
        passed = [r for r in results if r.passed]
        assert len(passed) >= 3

    def test_validate_se_discussion_missing_sections(self, tmp_path):
        """Test SE discussion validation with missing content."""
        validator = SubstantialEquivalenceValidator()

        discussion_path = tmp_path / "se-discussion.md"
        discussion_path.write_text("# Very short discussion\n\nNot enough content.")

        results = validator.validate_se_discussion(discussion_path)

        # Should have warnings about missing sections
        assert any(not r.passed for r in results)
