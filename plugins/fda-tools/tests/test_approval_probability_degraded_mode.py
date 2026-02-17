#!/usr/bin/env python3
"""
Test suite for approval_probability.py degraded mode behavior.

Tests GAP-031: Silent sklearn import fallback fix.
Verifies warning issuance, method_used field, and graceful degradation.
"""

import json
import os
import sys
import unittest
import warnings
from io import StringIO
from unittest.mock import MagicMock, patch

# Add scripts directory to path
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
sys.path.insert(0, SCRIPTS_DIR)


class TestSklearnDegradedMode(unittest.TestCase):
    """Test suite for sklearn import fallback behavior."""

    def setUp(self):
        """Reset module state before each test."""
        # Reset global warning flag
        import approval_probability
        approval_probability._SKLEARN_WARNING_ISSUED = False

    def test_warning_issued_when_sklearn_unavailable(self):
        """Test that warning is issued when sklearn is not available."""
        # Mock sklearn as unavailable
        with patch.dict(sys.modules, {"sklearn": None, "sklearn.ensemble": None}):
            with patch("approval_probability._HAS_SKLEARN", False):
                # Capture warnings
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")

                    # Import fresh and instantiate
                    import approval_probability
                    approval_probability._SKLEARN_WARNING_ISSUED = False
                    scorer = approval_probability.ApprovalProbabilityScorer()

                    # Verify warning was issued
                    self.assertGreater(len(w), 0, "Expected warning to be issued")
                    warning_message = str(w[0].message)
                    self.assertIn("DEGRADED MODE", warning_message)
                    self.assertIn("scikit-learn not available", warning_message)
                    self.assertIn("pip install scikit-learn", warning_message)
                    self.assertIn("rule-based fallback", warning_message)

    def test_warning_issued_only_once(self):
        """Test that warning is only issued once per session."""
        with patch("approval_probability._HAS_SKLEARN", False):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                import approval_probability
                approval_probability._SKLEARN_WARNING_ISSUED = False

                # Create multiple instances
                scorer1 = approval_probability.ApprovalProbabilityScorer()
                scorer2 = approval_probability.ApprovalProbabilityScorer()
                scorer3 = approval_probability.ApprovalProbabilityScorer()

                # Count warnings about sklearn
                sklearn_warnings = [
                    warn for warn in w
                    if "scikit-learn" in str(warn.message)
                ]
                self.assertEqual(
                    len(sklearn_warnings), 1,
                    "Warning should only be issued once per session"
                )

    def test_method_used_in_score_approval_probability_output(self):
        """Test that method_used field appears in score_approval_probability output."""
        with patch("approval_probability._HAS_SKLEARN", False):
            import approval_probability

            # Mock store to return test data
            mock_store = MagicMock()
            mock_store.get_pma_data.return_value = {
                "device_name": "Test Device",
                "applicant": "Test Applicant",
            }
            mock_store.get_supplements.return_value = [
                {
                    "supplement_number": "S001",
                    "pma_number": "P170019S001",
                    "decision_code": "APPR",
                    "decision_date": "2020-01-01",
                }
            ]

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                scorer = approval_probability.ApprovalProbabilityScorer(store=mock_store)
                result = scorer.score_approval_probability("P170019")

            # Verify method_used field exists and is correct
            self.assertIn("method_used", result, "method_used field missing from output")
            self.assertEqual(
                result["method_used"], "rule_based",
                "Expected rule_based method when sklearn unavailable"
            )
            self.assertEqual(
                result["model_type"], approval_probability.MODEL_TYPE_RULES,
                "Expected rule-based model type"
            )

    def test_method_used_in_hypothetical_supplement_output(self):
        """Test that method_used field appears in score_hypothetical_supplement output."""
        with patch("approval_probability._HAS_SKLEARN", False):
            import approval_probability

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                scorer = approval_probability.ApprovalProbabilityScorer()

            features = {
                "change_type": "labeling",
                "has_clinical_data": True,
                "regulatory_type": "180_day",
                "prior_denials": 0,
                "prior_approvals": 3,
            }

            result = scorer.score_hypothetical_supplement(features)

            # Verify method_used field exists and is correct
            self.assertIn("method_used", result, "method_used field missing from output")
            self.assertEqual(
                result["method_used"], "rule_based",
                "Expected rule_based method when sklearn unavailable"
            )

    def test_method_used_with_sklearn_available(self):
        """Test that method_used is 'ml' when sklearn is available and trained."""
        with patch("approval_probability._HAS_SKLEARN", True):
            import approval_probability

            # Mock store
            mock_store = MagicMock()
            mock_store.get_pma_data.return_value = {
                "device_name": "Test Device",
                "applicant": "Test Applicant",
            }
            mock_store.get_supplements.return_value = []

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                scorer = approval_probability.ApprovalProbabilityScorer(store=mock_store)

                # Simulate trained model
                scorer.model_type = approval_probability.MODEL_TYPE_SKLEARN
                scorer._trained_model = MagicMock()

                result = scorer.score_approval_probability("P170019")

            # Verify method_used reflects ML mode
            self.assertEqual(
                result["method_used"], "ml",
                "Expected ml method when sklearn available and trained"
            )

    def test_cli_output_shows_method_indicator(self):
        """Test that CLI formatted output includes method indicator."""
        with patch("approval_probability._HAS_SKLEARN", False):
            import approval_probability

            result = {
                "pma_number": "P170019",
                "device_name": "Test Device",
                "applicant": "Test Applicant",
                "total_supplements": 1,
                "scored_supplements": [],
                "aggregate_analysis": {"total_scored": 0},
                "model_version": "1.0.0",
                "model_type": approval_probability.MODEL_TYPE_RULES,
                "method_used": "rule_based",
                "generated_at": "2026-02-17T10:00:00Z",
            }

            formatted = approval_probability._format_scoring_result(result)

            # Verify method indicator in output
            self.assertIn("Method:", formatted, "Method label missing from CLI output")
            self.assertIn("Rule-based", formatted, "Rule-based label missing")
            self.assertIn("rule_based", formatted, "rule_based value missing")

    def test_no_breaking_changes_to_existing_functionality(self):
        """Test that existing functionality still works without sklearn."""
        with patch("approval_probability._HAS_SKLEARN", False):
            import approval_probability

            mock_store = MagicMock()
            mock_store.get_pma_data.return_value = {
                "device_name": "Test Device",
                "applicant": "Test Applicant",
            }
            mock_store.get_supplements.return_value = [
                {
                    "supplement_number": "S001",
                    "pma_number": "P170019S001",
                    "supplement_type": "180-day supplement",
                    "supplement_reason": "design change",
                    "decision_code": "APPR",
                    "decision_date": "2020-01-01",
                },
                {
                    "supplement_number": "S002",
                    "pma_number": "P170019S002",
                    "supplement_type": "30-day notice",
                    "supplement_reason": "labeling change",
                    "decision_code": "APPR",
                    "decision_date": "2020-06-01",
                },
            ]

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                scorer = approval_probability.ApprovalProbabilityScorer(store=mock_store)
                result = scorer.score_approval_probability("P170019")

            # Verify core functionality works
            self.assertEqual(result["pma_number"], "P170019")
            self.assertEqual(result["total_supplements"], 2)
            self.assertEqual(len(result["scored_supplements"]), 2)
            self.assertIn("aggregate_analysis", result)
            self.assertEqual(result["aggregate_analysis"]["total_scored"], 2)

            # Verify probabilities were computed
            for supp in result["scored_supplements"]:
                self.assertIn("approval_probability", supp)
                self.assertGreater(supp["approval_probability"], 0)
                self.assertLess(supp["approval_probability"], 100)

    def test_rule_based_fallback_uses_baseline_rates(self):
        """Test that rule-based fallback uses empirical baseline rates."""
        with patch("approval_probability._HAS_SKLEARN", False):
            import approval_probability

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                scorer = approval_probability.ApprovalProbabilityScorer()

            # Test various supplement types
            test_cases = [
                ("labeling", 94.0),  # High approval rate
                ("30_day_notice", 97.0),  # Very high approval rate
                ("panel_track", 78.0),  # Lower approval rate
                ("design_change", 85.0),  # Moderate approval rate
            ]

            for change_type, expected_base_rate in test_cases:
                features = {
                    "change_type": change_type,
                    "has_clinical_data": True,
                    "prior_denials": 0,
                    "prior_approvals": 0,
                }
                result = scorer.score_hypothetical_supplement(features)

                # Verify baseline rate is used
                self.assertEqual(
                    result["base_rate"], expected_base_rate,
                    f"Expected base rate {expected_base_rate} for {change_type}"
                )


class TestWarningMessageContent(unittest.TestCase):
    """Test the content and formatting of the warning message."""

    def test_warning_includes_installation_instructions(self):
        """Test that warning includes clear installation instructions."""
        with patch("approval_probability._HAS_SKLEARN", False):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                import approval_probability
                approval_probability._SKLEARN_WARNING_ISSUED = False
                scorer = approval_probability.ApprovalProbabilityScorer()

                warning_message = str(w[0].message)
                self.assertIn("pip install", warning_message)
                self.assertIn("scikit-learn", warning_message)

    def test_warning_explains_accuracy_implications(self):
        """Test that warning explains accuracy differences between modes."""
        with patch("approval_probability._HAS_SKLEARN", False):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                import approval_probability
                approval_probability._SKLEARN_WARNING_ISSUED = False
                scorer = approval_probability.ApprovalProbabilityScorer()

                warning_message = str(w[0].message)
                self.assertIn("Accuracy implications", warning_message)
                self.assertIn("Rule-based", warning_message)
                self.assertIn("ML-based", warning_message)

    def test_warning_mentions_output_transparency(self):
        """Test that warning mentions method_used field for transparency."""
        with patch("approval_probability._HAS_SKLEARN", False):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                import approval_probability
                approval_probability._SKLEARN_WARNING_ISSUED = False
                scorer = approval_probability.ApprovalProbabilityScorer()

                warning_message = str(w[0].message)
                self.assertIn("method_used", warning_message)
                self.assertIn("transparency", warning_message)


class TestCLIBehavior(unittest.TestCase):
    """Test CLI behavior with and without sklearn."""

    def test_cli_json_output_includes_method_used(self):
        """Test that --json output includes method_used field."""
        with patch("approval_probability._HAS_SKLEARN", False):
            import approval_probability

            mock_store = MagicMock()
            mock_store.get_pma_data.return_value = {
                "device_name": "Test Device",
                "applicant": "Test Applicant",
            }
            mock_store.get_supplements.return_value = [
                {
                    "supplement_number": "S001",
                    "pma_number": "P170019S001",
                    "decision_code": "APPR",
                    "decision_date": "2020-01-01",
                }
            ]

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                scorer = approval_probability.ApprovalProbabilityScorer(store=mock_store)
                result = scorer.score_approval_probability("P170019")

            # Verify JSON serialization works
            json_output = json.dumps(result, indent=2)
            parsed = json.loads(json_output)

            self.assertIn("method_used", parsed)
            self.assertEqual(parsed["method_used"], "rule_based")


def run_tests():
    """Run all tests and report results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSklearnDegradedMode))
    suite.addTests(loader.loadTestsFromTestCase(TestWarningMessageContent))
    suite.addTests(loader.loadTestsFromTestCase(TestCLIBehavior))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY - FDA-60 GAP-031: Degraded Mode Testing")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
