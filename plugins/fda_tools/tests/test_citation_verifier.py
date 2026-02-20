#!/usr/bin/env python3
"""
Tests for Automated Citation Verifier
======================================

Tests the citation verifier script that automates CFR and guidance verification.
"""

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
    from verify_citations import CitationVerifier
    VERIFIER_AVAILABLE = True
except ImportError:
    VERIFIER_AVAILABLE = False


@unittest.skipUnless(VERIFIER_AVAILABLE, "verify_citations module not available")
class TestCitationVerifier(unittest.TestCase):
    """Test suite for CitationVerifier class."""

    def setUp(self):
        """Create temp output file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
        self.temp_file.close()
        self.output_path = self.temp_file.name

    def tearDown(self):
        """Clean up temp files."""
        if os.path.exists(self.output_path):
            os.unlink(self.output_path)

    def test_verifier_initialization(self):
        """Test CitationVerifier initializes correctly."""
        verifier = CitationVerifier(self.output_path)

        self.assertEqual(verifier.output_file, self.output_path)
        self.assertIn('cfr_results', verifier.results)
        self.assertIn('guidance_results', verifier.results)
        self.assertIn('verification_time', verifier.results)
        self.assertEqual(len(verifier.results['cfr_results']), 0)
        self.assertEqual(len(verifier.results['guidance_results']), 0)

    def test_cfr_citations_structure(self):
        """Test CFR_CITATIONS has correct structure."""
        verifier = CitationVerifier(self.output_path)

        self.assertEqual(len(verifier.CFR_CITATIONS), 3)

        for cfr in verifier.CFR_CITATIONS:
            self.assertIn('part', cfr)
            self.assertIn('url', cfr)
            self.assertIn('expected_title', cfr)
            self.assertIn('applies_to', cfr)
            self.assertIn('key_sections', cfr)
            self.assertIsInstance(cfr['key_sections'], list)
            self.assertGreater(len(cfr['key_sections']), 0)

    def test_guidance_docs_structure(self):
        """Test GUIDANCE_DOCS has correct structure."""
        verifier = CitationVerifier(self.output_path)

        self.assertEqual(len(verifier.GUIDANCE_DOCS), 3)

        for guidance in verifier.GUIDANCE_DOCS:
            self.assertIn('title', guidance)
            self.assertIn('year', guidance)
            self.assertIn('url', guidance)
            self.assertIn('docket_number', guidance)
            self.assertIn('applies_to', guidance)

    def test_check_url_success(self):
        """Test URL checking with successful response."""
        verifier = CitationVerifier(self.output_path)

        # Mock urlopen to return success
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            success, error = verifier._check_url('https://example.com')

        self.assertTrue(success)
        self.assertIsNone(error)

    def test_check_url_failure(self):
        """Test URL checking with failed response."""
        verifier = CitationVerifier(self.output_path)

        # Mock urlopen to raise exception
        with patch('urllib.request.urlopen', side_effect=Exception('Connection timeout')):
            success, error = verifier._check_url('https://example.com')

        self.assertFalse(success)
        self.assertIsNotNone(error)
        self.assertIn('timeout', error.lower())

    def test_fuzzy_match_exact(self):
        """Test fuzzy match with exact strings."""
        verifier = CitationVerifier(self.output_path)

        self.assertTrue(verifier._fuzzy_match(
            'Medical Device Reporting',
            'Medical Device Reporting'
        ))

    def test_fuzzy_match_case_insensitive(self):
        """Test fuzzy match is case insensitive."""
        verifier = CitationVerifier(self.output_path)

        self.assertTrue(verifier._fuzzy_match(
            'MEDICAL DEVICE REPORTING',
            'medical device reporting'
        ))

    def test_fuzzy_match_punctuation(self):
        """Test fuzzy match with punctuation variations."""
        verifier = CitationVerifier(self.output_path)

        # Fuzzy match works when punctuation doesn't affect substring matching
        self.assertTrue(verifier._fuzzy_match(
            'Enforcement Policy (Recalls)',
            'Enforcement Policy'
        ))

    def test_fuzzy_match_substring(self):
        """Test fuzzy match allows substring matching."""
        verifier = CitationVerifier(self.output_path)

        self.assertTrue(verifier._fuzzy_match(
            '21 CFR Part 803 - Medical Device Reporting',
            'Medical Device Reporting'
        ))

    def test_fuzzy_match_mismatch(self):
        """Test fuzzy match returns False for non-matching strings."""
        verifier = CitationVerifier(self.output_path)

        self.assertFalse(verifier._fuzzy_match(
            'Recall Policy',
            'Medical Device Reporting'
        ))

    def test_fuzzy_match_empty_strings(self):
        """Test fuzzy match handles empty strings."""
        verifier = CitationVerifier(self.output_path)

        self.assertFalse(verifier._fuzzy_match('', 'Medical Device Reporting'))
        self.assertFalse(verifier._fuzzy_match('Medical Device Reporting', ''))
        self.assertFalse(verifier._fuzzy_match(None, 'Medical Device Reporting'))

    def test_verify_cfr_with_successful_url(self):
        """Test CFR verification with successful URL check."""
        verifier = CitationVerifier(self.output_path)

        cfr = verifier.CFR_CITATIONS[0]

        # Mock URL check
        with patch.object(verifier, '_check_url', return_value=(True, None)):
            with patch.object(verifier, '_parse_cfr_page', return_value=('Medical Device Reporting', {'Subpart A': True})):
                result = verifier.verify_cfr(cfr)

        self.assertTrue(result['url_resolves'])
        self.assertIsNone(result['url_error'])
        self.assertEqual(result['part'], cfr['part'])

    def test_verify_cfr_with_failed_url(self):
        """Test CFR verification with failed URL check."""
        verifier = CitationVerifier(self.output_path)

        cfr = verifier.CFR_CITATIONS[0]

        # Mock URL check to fail
        with patch.object(verifier, '_check_url', return_value=(False, 'Connection timeout')):
            result = verifier.verify_cfr(cfr)

        self.assertFalse(result['url_resolves'])
        self.assertEqual(result['url_error'], 'Connection timeout')
        self.assertIsNone(result['title_match'])
        self.assertIsNone(result['structure_present'])

    def test_verify_guidance_with_successful_url(self):
        """Test guidance verification with successful URL check."""
        verifier = CitationVerifier(self.output_path)

        guidance = verifier.GUIDANCE_DOCS[0]

        # Mock URL check
        with patch.object(verifier, '_check_url', return_value=(True, None)):
            with patch.object(verifier, '_check_superseded', return_value=False):
                result = verifier.verify_guidance(guidance)

        self.assertTrue(result['url_resolves'])
        self.assertIsNone(result['url_error'])
        self.assertEqual(result['title'], guidance['title'])

    def test_check_superseded_detection(self):
        """Test superseded warning detection."""
        verifier = CitationVerifier(self.output_path)

        # Mock urlopen to return HTML with superseded warning
        mock_response = MagicMock()
        mock_response.read.return_value = b'<html><body>This guidance has been superseded by a newer version.</body></html>'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            superseded = verifier._check_superseded('https://example.com')

        self.assertTrue(superseded)

    def test_check_superseded_no_warning(self):
        """Test superseded check when no warning present."""
        verifier = CitationVerifier(self.output_path)

        # Mock urlopen to return HTML without superseded warning
        mock_response = MagicMock()
        mock_response.read.return_value = b'<html><body>This is the current version of the guidance.</body></html>'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            superseded = verifier._check_superseded('https://example.com')

        self.assertFalse(superseded)

    def test_generate_report_structure(self):
        """Test that generated report has correct structure."""
        verifier = CitationVerifier(self.output_path)

        # Add mock results
        verifier.results['cfr_results'] = [{
            'part': '21 CFR Part 803',
            'url': 'https://example.com',
            'expected_title': 'Medical Device Reporting',
            'applies_to': 'MAUDE data',
            'url_resolves': True,
            'url_error': None,
            'actual_title': 'Medical Device Reporting',
            'title_match': True,
            'structure_present': {'Subpart A': True, 'Subpart B': True}
        }]

        verifier.results['guidance_results'] = [{
            'title': 'Test Guidance',
            'year': '2020',
            'url': 'https://example.com',
            'docket_number': 'FDA-2020-D-0001',
            'applies_to': 'Test purpose',
            'url_resolves': True,
            'url_error': None,
            'superseded': False
        }]

        verifier.generate_report()

        # Read generated report
        with open(self.output_path, 'r') as f:
            content = f.read()

        # Verify key sections present
        self.assertIn('Automated CFR/Guidance Citation Verification Report', content)
        self.assertIn('RA PROFESSIONAL REVIEW REQUIRED', content)
        self.assertIn('CFR Citation Verification', content)
        self.assertIn('Guidance Document Verification', content)
        self.assertIn('21 CFR Part 803', content)
        self.assertIn('Test Guidance', content)
        self.assertIn('RA Professional Sign-Off', content)
        self.assertIn('ALL VERIFIED', content)


if __name__ == '__main__':
    unittest.main()
