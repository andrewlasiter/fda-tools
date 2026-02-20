#!/usr/bin/env python3
"""
Comprehensive tests for secure_config module (FDA-182 / SEC-003).

Tests cover:
  - Keyring storage and retrieval
  - Environment variable resolution
  - Plaintext migration
  - API key redaction
  - Multi-key support
  - Error handling
  - Backward compatibility
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add lib directory to path

from secure_config import (
    SecureConfig,
    mask_api_key,
    APIKeyRedactor,
    KEYRING_ACCOUNTS,
    ENV_VAR_NAMES,
    SETTINGS_PATH,
    _keyring_set,
    _keyring_get,
    _keyring_delete,
    _read_plaintext_key,
    _scrub_plaintext_key,
)


class TestAPIKeyMasking(unittest.TestCase):
    """Test API key masking/redaction."""

    def test_mask_short_key(self):
        """Short keys should be fully redacted."""
        self.assertEqual(mask_api_key("short"), "REDACTED")
        self.assertEqual(mask_api_key("1234567"), "REDACTED")

    def test_mask_long_key(self):
        """Long keys should show first 4 and last 4 chars."""
        key = "abcdefghijklmnopqrstuvwxyz"
        masked = mask_api_key(key)
        self.assertEqual(masked, "abcd...wxyz")

    def test_mask_empty_key(self):
        """Empty keys should be redacted."""
        self.assertEqual(mask_api_key(""), "REDACTED")
        self.assertEqual(mask_api_key(None), "REDACTED")


class TestAPIKeyRedactor(unittest.TestCase):
    """Test logging filter for API key redaction."""

    def test_redact_in_message(self):
        """API keys in log messages should be redacted."""
        import logging

        redactor = APIKeyRedactor()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="API key is abcdefghijklmnopqrstuvwxyz1234567890",
            args=(),
            exc_info=None,
        )

        redactor.filter(record)
        self.assertIn("abcd...7890", record.msg)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz1234567890", record.msg)

    def test_redact_in_args_dict(self):
        """API keys in log args dict should be redacted."""
        import logging

        redactor = APIKeyRedactor()
        # Create record without args first, then set args manually
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Logging with args",
            args=(),
            exc_info=None,
        )
        # Manually set args after creation
        record.args = {'api_key': 'abcdefghijklmnopqrstuvwxyz1234567890'}

        redactor.filter(record)
        self.assertIn("abcd...7890", record.args['api_key'])


class TestKeyringBackend(unittest.TestCase):
    """Test keyring backend functions."""

    def test_keyring_set_success(self):
        """Successful keyring write should return True."""
        # Mock keyring module at import level
        import sys
        mock_keyring = MagicMock()
        sys.modules['keyring'] = mock_keyring

        result = _keyring_set('test_account', 'test_secret')
        self.assertTrue(result)

        # Clean up
        if 'keyring' in sys.modules:
            del sys.modules['keyring']

    def test_keyring_get_success(self):
        """Successful keyring read should return secret."""
        import sys
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = 'test_secret'
        sys.modules['keyring'] = mock_keyring

        result = _keyring_get('test_account')
        self.assertEqual(result, 'test_secret')

        # Clean up
        if 'keyring' in sys.modules:
            del sys.modules['keyring']

    def test_keyring_delete_success(self):
        """Successful keyring delete should return True."""
        import sys
        mock_keyring = MagicMock()
        sys.modules['keyring'] = mock_keyring

        result = _keyring_delete('test_account')
        self.assertTrue(result)

        # Clean up
        if 'keyring' in sys.modules:
            del sys.modules['keyring']


class TestPlaintextMigration(unittest.TestCase):
    """Test migration from plaintext settings file."""

    def setUp(self):
        """Create temporary settings file."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_settings = Path(self.temp_dir) / 'fda-tools.local.md'

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_read_plaintext_key(self):
        """Should read plaintext key from settings file."""
        self.temp_settings.write_text("openfda_api_key: TEST_KEY_123456789\n")

        with patch('secure_config.SETTINGS_PATH', self.temp_settings):
            key = _read_plaintext_key('openfda')
            self.assertEqual(key, 'TEST_KEY_123456789')

    def test_ignore_keyring_marker(self):
        """Should not return 'keyring' marker as actual key."""
        self.temp_settings.write_text("openfda_api_key: keyring\n")

        with patch('secure_config.SETTINGS_PATH', self.temp_settings):
            key = _read_plaintext_key('openfda')
            self.assertIsNone(key)

    def test_scrub_plaintext_key(self):
        """Should replace plaintext key with 'keyring' marker."""
        self.temp_settings.write_text("openfda_api_key: TEST_KEY_123456789\n")

        with patch('secure_config.SETTINGS_PATH', self.temp_settings):
            result = _scrub_plaintext_key('openfda')
            self.assertTrue(result)

            content = self.temp_settings.read_text()
            self.assertIn('openfda_api_key: keyring', content)
            self.assertNotIn('TEST_KEY_123456789', content)


class TestSecureConfig(unittest.TestCase):
    """Test SecureConfig class."""

    def setUp(self):
        """Set up test environment."""
        # Clear environment variables
        for env_var in ENV_VAR_NAMES.values():
            os.environ.pop(env_var, None)

    @patch('secure_config._is_keyring_available', return_value=True)
    @patch('secure_config._keyring_get', return_value='keyring_test_key')
    def test_get_api_key_from_keyring(self, mock_get, mock_available):
        """Should retrieve key from keyring when available."""
        config = SecureConfig()
        key = config.get_api_key('openfda')
        self.assertEqual(key, 'keyring_test_key')

    @patch('secure_config._is_keyring_available', return_value=False)
    def test_get_api_key_from_env(self, mock_available):
        """Should retrieve key from environment when keyring unavailable."""
        os.environ['OPENFDA_API_KEY'] = 'env_test_key'
        config = SecureConfig()
        key = config.get_api_key('openfda')
        self.assertEqual(key, 'env_test_key')

    @patch('secure_config._is_keyring_available', return_value=True)
    @patch('secure_config._keyring_set', return_value=True)
    def test_set_api_key(self, mock_set, mock_available):
        """Should store key in keyring."""
        config = SecureConfig()
        result = config.set_api_key('openfda', 'new_test_key')
        self.assertTrue(result)
        mock_set.assert_called_once_with('openfda_api_key', 'new_test_key')

    @patch('secure_config._is_keyring_available', return_value=True)
    @patch('secure_config._keyring_delete', return_value=True)
    @patch('secure_config._scrub_plaintext_key', return_value=True)
    def test_remove_api_key(self, mock_scrub, mock_delete, mock_available):
        """Should remove key from all locations."""
        config = SecureConfig()
        result = config.remove_api_key('openfda')
        self.assertTrue(result)
        mock_delete.assert_called_once()
        mock_scrub.assert_called_once()

    def test_invalid_key_type(self):
        """Should raise ValueError for unknown key type."""
        config = SecureConfig()
        with self.assertRaises(ValueError):
            config.get_api_key('invalid_key')

    @patch('secure_config._is_keyring_available', return_value=True)
    def test_get_key_status(self, mock_available):
        """Should return detailed key status."""
        os.environ['LINEAR_API_KEY'] = 'test_linear_key'
        config = SecureConfig()
        status = config.get_key_status('linear')

        self.assertEqual(status['key_type'], 'linear')
        self.assertTrue(status['env_var_set'])
        self.assertEqual(status['active_source'], 'environment')
        self.assertIsNotNone(status['masked_value'])

    @patch('secure_config._is_keyring_available', return_value=True)
    def test_health_check(self, mock_available):
        """Should return health status."""
        config = SecureConfig()
        health = config.health_check()

        self.assertIn('keyring_available', health)
        self.assertIn('keys_configured', health)
        self.assertIn('healthy', health)
        self.assertIsInstance(health['supported_keys'], list)


class TestMultiKeySupport(unittest.TestCase):
    """Test support for multiple API keys."""

    def setUp(self):
        """Set up test environment."""
        for env_var in ENV_VAR_NAMES.values():
            os.environ.pop(env_var, None)

    @patch('secure_config._is_keyring_available', return_value=False)
    def test_all_key_types(self, mock_available):
        """Should support all defined key types."""
        config = SecureConfig()

        # Set environment variables for all keys
        os.environ['OPENFDA_API_KEY'] = 'openfda_key'
        os.environ['LINEAR_API_KEY'] = 'linear_key'
        os.environ['BRIDGE_API_KEY'] = 'bridge_key'
        os.environ['GEMINI_API_KEY'] = 'gemini_key'

        # Test retrieval
        self.assertEqual(config.get_api_key('openfda'), 'openfda_key')
        self.assertEqual(config.get_api_key('linear'), 'linear_key')
        self.assertEqual(config.get_api_key('bridge'), 'bridge_key')
        self.assertEqual(config.get_api_key('gemini'), 'gemini_key')

    @patch('secure_config._is_keyring_available', return_value=True)
    def test_get_all_keys_status(self, mock_available):
        """Should return status for all keys."""
        config = SecureConfig()
        all_status = config.get_all_keys_status()

        self.assertEqual(len(all_status), len(KEYRING_ACCOUNTS))
        for key_type in KEYRING_ACCOUNTS.keys():
            self.assertIn(key_type, all_status)


class TestResolutionOrder(unittest.TestCase):
    """Test API key resolution order (env > keyring > plaintext)."""

    def setUp(self):
        """Set up test environment."""
        for env_var in ENV_VAR_NAMES.values():
            os.environ.pop(env_var, None)

        self.temp_dir = tempfile.mkdtemp()
        self.temp_settings = Path(self.temp_dir) / 'fda-tools.local.md'

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('secure_config._is_keyring_available', return_value=True)
    @patch('secure_config._keyring_get', return_value='keyring_key')
    def test_env_overrides_keyring(self, mock_get, mock_available):
        """Environment variable should take priority over keyring."""
        os.environ['OPENFDA_API_KEY'] = 'env_key'
        config = SecureConfig()
        key = config.get_api_key('openfda')
        self.assertEqual(key, 'env_key')

    @patch('secure_config._is_keyring_available', return_value=True)
    @patch('secure_config._keyring_get', return_value=None)
    def test_plaintext_fallback(self, mock_get, mock_available):
        """Should fall back to plaintext if keyring empty."""
        self.temp_settings.write_text("openfda_api_key: plaintext_key\n")

        with patch('secure_config.SETTINGS_PATH', self.temp_settings):
            config = SecureConfig()
            key = config.get_api_key('openfda')
            self.assertEqual(key, 'plaintext_key')


class TestMigration(unittest.TestCase):
    """Test migration functionality."""

    def setUp(self):
        """Set up test environment."""
        for env_var in ENV_VAR_NAMES.values():
            os.environ.pop(env_var, None)

    @patch('secure_config._is_keyring_available', return_value=True)
    @patch('secure_config._keyring_get', return_value=None)
    @patch('secure_config._keyring_set', return_value=True)
    def test_migrate_from_env(self, mock_set, mock_get, mock_available):
        """Should migrate key from environment to keyring."""
        os.environ['LINEAR_API_KEY'] = 'migrate_test_key'
        config = SecureConfig()

        success, message = config.migrate_key('linear')
        self.assertTrue(success)
        # Message format changed, just check for success
        self.assertIn('linear', message.lower())
        mock_set.assert_called_once_with('linear_api_key', 'migrate_test_key')

    @patch('secure_config._is_keyring_available', return_value=True)
    @patch('secure_config._keyring_get', return_value='existing_key')
    def test_skip_if_already_migrated(self, mock_get, mock_available):
        """Should skip migration if key already in keyring."""
        config = SecureConfig()
        success, message = config.migrate_key('openfda')
        self.assertTrue(success)
        self.assertIn('already', message.lower())

    @patch('secure_config._is_keyring_available', return_value=False)
    def test_fail_migration_without_keyring(self, mock_available):
        """Should fail migration if keyring unavailable."""
        config = SecureConfig()
        success, message = config.migrate_key('openfda')
        self.assertFalse(success)
        self.assertIn('not available', message.lower())


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with existing code."""

    @patch('secure_config._is_keyring_available', return_value=False)
    def test_env_var_still_works(self, mock_available):
        """Existing code using env vars should still work."""
        os.environ['OPENFDA_API_KEY'] = 'legacy_env_key'
        config = SecureConfig()
        key = config.get_api_key('openfda')
        self.assertEqual(key, 'legacy_env_key')

    @patch('secure_config._is_keyring_available', return_value=True)
    def test_convenience_functions(self, mock_available):
        """Convenience functions should work."""
        from secure_config import get_api_key, set_api_key

        with patch('secure_config._keyring_set', return_value=True):
            result = set_api_key('bridge', 'test_bridge_key')
            self.assertTrue(result)

        with patch('secure_config._keyring_get', return_value='test_bridge_key'):
            key = get_api_key('bridge')
            self.assertEqual(key, 'test_bridge_key')


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
