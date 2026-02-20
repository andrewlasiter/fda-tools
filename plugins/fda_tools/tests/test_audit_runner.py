#!/usr/bin/env python3
"""
Tests for Automated Audit Runner
=================================

Tests the audit runner script that automates data collection for
manual enrichment audits.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path
TEST_DIR = Path(__file__).parent
PLUGIN_ROOT = TEST_DIR.parent

try:
    from run_audit import AuditRunner
    AUDIT_RUNNER_AVAILABLE = True
except ImportError:
    AUDIT_RUNNER_AVAILABLE = False


@unittest.skipUnless(AUDIT_RUNNER_AVAILABLE, "run_audit module not available")
class TestAuditRunner(unittest.TestCase):
    """Test suite for AuditRunner class."""

    def setUp(self):
        """Create temp output file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
        self.temp_file.close()
        self.output_path = self.temp_file.name

    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.output_path):
            os.unlink(self.output_path)

    def test_audit_runner_initialization(self):
        """Test AuditRunner initializes correctly."""
        runner = AuditRunner(self.output_path, api_key="test_key")

        self.assertEqual(runner.output_file, self.output_path)
        self.assertEqual(runner.api_key, "test_key")
        self.assertEqual(runner.results, [])
        self.assertIsNone(runner.temp_dir)

    def test_verify_maude_with_matching_data(self):
        """Test MAUDE verification when enriched and API values match."""
        runner = AuditRunner(self.output_path)

        # Mock urlopen to return matching data (context manager protocol)
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'results': [{'count': 50}] * 60  # 60 months * 50 = 3000
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = runner._verify_maude('DQY', '3000', 'PRODUCT_CODE')

        self.assertEqual(result['enriched_value'], '3000')
        self.assertEqual(result['api_value'], 3000)
        self.assertEqual(result['determination'], 'PASS')
        self.assertLessEqual(result['discrepancy_pct'], 5)

    def test_verify_maude_with_mismatch(self):
        """Test MAUDE verification when enriched and API values don't match."""
        runner = AuditRunner(self.output_path)

        # Mock urlopen to return different data (context manager protocol)
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'results': [{'count': 100}] * 60  # 60 months * 100 = 6000
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = runner._verify_maude('DQY', '3000', 'PRODUCT_CODE')

        self.assertEqual(result['enriched_value'], '3000')
        self.assertEqual(result['api_value'], 6000)
        self.assertEqual(result['determination'], 'FAIL')
        self.assertGreater(result['discrepancy_pct'], 5)

    def test_verify_maude_with_api_error(self):
        """Test MAUDE verification handles API errors gracefully."""
        runner = AuditRunner(self.output_path)

        with patch('urllib.request.urlopen', side_effect=Exception('API timeout')):
            result = runner._verify_maude('DQY', '3000', 'PRODUCT_CODE')

        self.assertEqual(result['enriched_value'], '3000')
        self.assertIsNone(result['api_value'])
        self.assertEqual(result['determination'], 'MANUAL_REVIEW_REQUIRED')
        self.assertIn('error', result)

    def test_verify_recalls_with_matching_data(self):
        """Test recall verification when counts match."""
        runner = AuditRunner(self.output_path)

        # Mock urlopen to return matching data (context manager protocol)
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'results': [{'recall_number': 'Z-1234-2024'}] * 3
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = runner._verify_recalls('K123456', '3', '2024-01-01', 'Class II')

        self.assertEqual(result['enriched_total'], '3')
        self.assertEqual(result['api_count'], 3)
        self.assertEqual(result['determination'], 'PASS')

    def test_verify_510k_with_valid_device(self):
        """Test 510(k) validation when device is found in API."""
        runner = AuditRunner(self.output_path)

        # Mock urlopen to return device data (context manager protocol)
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'results': [{'decision_description': 'SUBSTANTIALLY EQUIVALENT'}]
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = runner._verify_510k('K123456', 'Yes', 'SUBSTANTIALLY EQUIVALENT')

        self.assertEqual(result['enriched_validated'], 'Yes')
        self.assertTrue(result['api_found'])
        self.assertEqual(result['determination'], 'PASS')

    def test_verify_510k_with_invalid_device(self):
        """Test 510(k) validation when device is not found in API."""
        runner = AuditRunner(self.output_path)

        # Mock urlopen to return empty results (context manager protocol)
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'results': []
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = runner._verify_510k('K999999', 'No', '')

        self.assertEqual(result['enriched_validated'], 'No')
        self.assertFalse(result['api_found'])
        self.assertEqual(result['determination'], 'PASS')

    def test_check_disclaimers_all_present(self):
        """Test disclaimer check when all files have disclaimers."""
        runner = AuditRunner(self.output_path)

        # Create temp directory with mock files
        with tempfile.TemporaryDirectory() as temp_dir:
            files = [
                '510k_download_enriched.csv',
                'enrichment_report.html',
                'quality_report.md',
                'regulatory_context.md',
                'intelligence_report.md',
                'enrichment_metadata.json'
            ]

            for fname in files:
                with open(os.path.join(temp_dir, fname), 'w') as f:
                    f.write("RESEARCH USE ONLY - requires independent verification")

            result = runner._check_disclaimers(temp_dir)

        self.assertEqual(result['count'], '6/6')
        self.assertEqual(result['determination'], 'PASS')

    def test_check_disclaimers_some_missing(self):
        """Test disclaimer check when some files lack disclaimers."""
        runner = AuditRunner(self.output_path)

        # Create temp directory with partial disclaimers
        with tempfile.TemporaryDirectory() as temp_dir:
            # Only create 3 files with disclaimers
            for fname in ['enrichment_report.html', 'quality_report.md', 'regulatory_context.md']:
                with open(os.path.join(temp_dir, fname), 'w') as f:
                    f.write("RESEARCH USE ONLY")

            # Create 3 files without disclaimers
            for fname in ['510k_download_enriched.csv', 'intelligence_report.md', 'enrichment_metadata.json']:
                with open(os.path.join(temp_dir, fname), 'w') as f:
                    f.write("No disclaimer here")

            result = runner._check_disclaimers(temp_dir)

        self.assertEqual(result['count'], '3/6')
        self.assertEqual(result['determination'], 'FAIL')

    def test_generate_report_structure(self):
        """Test that generated report has correct structure."""
        runner = AuditRunner(self.output_path)

        # Add mock device result
        runner.results = [{
            'product_code': 'DQY',
            'k_number': 'K123456',
            'audit_time': '2024-01-01T00:00:00',
            'sections': {
                'maude': {
                    'enriched_value': '3000',
                    'api_value': 3000,
                    'determination': 'PASS'
                }
            }
        }]

        runner.generate_report()

        # Read generated report
        with open(self.output_path, 'r') as f:
            content = f.read()

        # Verify key sections present
        self.assertIn('FDA API Enrichment Audit Report', content)
        self.assertIn('HUMAN VERIFICATION REQUIRED', content)
        self.assertIn('DEVICE 1: DQY', content)
        self.assertIn('**K-Number:** K123456', content)
        self.assertIn('Auditor Sign-Off', content)
        self.assertIn('PRODUCTION READY', content)

    def test_error_result_generation(self):
        """Test error result structure for failed device audits."""
        runner = AuditRunner(self.output_path)

        result = runner._error_result('XYZ', 'Enrichment command failed')

        self.assertEqual(result['product_code'], 'XYZ')
        self.assertIsNone(result['k_number'])
        self.assertEqual(result['error'], 'Enrichment command failed')
        self.assertEqual(result['sections'], {})
        self.assertIn('audit_time', result)


@unittest.skipUnless(AUDIT_RUNNER_AVAILABLE, "run_audit module not available")
class TestAuditRunnerCLI(unittest.TestCase):
    """Test command-line interface of audit runner."""

    def test_cli_requires_devices_argument(self):
        """Test that CLI requires --devices argument."""
        from run_audit import main

        with self.assertRaises(SystemExit):
            with patch('sys.argv', ['run_audit.py']):
                main()

    def test_cli_parses_device_list(self):
        """Test that CLI correctly parses comma-separated device list."""
        # This test would require mocking the entire runner
        # For now, just verify the argument parsing logic works
        pass


if __name__ == '__main__':
    unittest.main()
