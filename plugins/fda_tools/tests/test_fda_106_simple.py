#!/usr/bin/env python3
"""
Simple tests for FDA-106: API Key Security Fix
===============================================

Verifies that API keys are not exposed in URLs.
"""

import unittest
from urllib.parse import urlparse, parse_qs


class TestAPIKeyNotInURL(unittest.TestCase):
    """Simple tests to verify API key not in URL."""

    def test_verify_fix_pattern(self):
        """Verify that the code pattern has been fixed."""
        # Read the fixed file
        with open('scripts/external_data_hub.py', 'r') as f:
            content = f.read()

        # Verify API key is NOT added to params dictionary
        self.assertNotIn('params["api_key"] = self.api_key', content,
                        "API key should NOT be added to params dictionary")

        # Verify extra_headers parameter exists in _http_get
        self.assertIn('extra_headers', content,
                     "_http_get should accept extra_headers parameter")

        # Verify header update logic exists
        self.assertIn('if extra_headers:', content,
                     "Should check for extra_headers")
        self.assertIn('headers.update(extra_headers)', content,
                     "Should merge extra_headers into request headers")

    def test_api_key_header_pattern(self):
        """Verify that API key is passed in headers."""
        with open('scripts/external_data_hub.py', 'r') as f:
            content = f.read()

        # Look for the pattern where API key is set in headers
        self.assertIn('headers["api_key"] = self.api_key', content,
                     "API key should be set in headers dictionary")

        # Verify headers are passed to _http_get
        self.assertIn('extra_headers=headers', content,
                     "Headers should be passed to _http_get")

    def test_example_url_format(self):
        """Test that our understanding of URL format is correct."""
        # This tests what we DON'T want - API key in URL
        bad_url = "https://example.com/api?term=test&api_key=SECRET123"
        parsed = urlparse(bad_url)
        params = parse_qs(parsed.query)

        self.assertIn('api_key', params,
                     "Bad URL contains API key in query params")
        self.assertIn('SECRET123', bad_url,
                     "Bad URL contains API key value")

        # This is what we DO want - API key NOT in URL
        good_url = "https://example.com/api?term=test"
        parsed2 = urlparse(good_url)
        params2 = parse_qs(parsed2.query)

        self.assertNotIn('api_key', params2,
                        "Good URL does not contain API key")


if __name__ == '__main__':
    unittest.main()
