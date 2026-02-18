#!/usr/bin/env python3
"""
Security tests for FDA-80: Secure API key storage via OS keyring.

Verifies:
- Keyring storage and retrieval
- Migration from plaintext to keyring
- Plaintext scrubbing after migration
- Fallback behavior when keyring is unavailable
- get_current_key() resolution order (env > keyring > plaintext)
- File permission restrictions on fallback storage
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import setup_api_key


class TestKeyringStorage(unittest.TestCase):
    """Test keyring-based key storage."""

    def setUp(self):
        """Reset keyring availability cache between tests."""
        setup_api_key._keyring_available = None

    @patch('setup_api_key._is_keyring_available', return_value=True)
    @patch('setup_api_key._keyring_get', return_value='test-key-12345')
    def test_get_key_from_keyring(self, mock_get, mock_avail):
        """Key should be retrieved from keyring when available."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove OPENFDA_API_KEY if present
            env = os.environ.copy()
            env.pop('OPENFDA_API_KEY', None)
            with patch.dict(os.environ, env, clear=True):
                key = setup_api_key.get_current_key()
                self.assertEqual(key, 'test-key-12345')

    @patch('setup_api_key._is_keyring_available', return_value=True)
    @patch('setup_api_key._keyring_set', return_value=True)
    def test_set_key_uses_keyring(self, mock_set, mock_avail):
        """set_key should store in keyring when available."""
        with patch.object(setup_api_key, '_update_settings_marker'):
            setup_api_key.set_key('my-api-key-456')
            mock_set.assert_called_once_with(
                setup_api_key.KEYRING_ACCOUNT_OPENFDA,
                'my-api-key-456'
            )

    @patch('setup_api_key._is_keyring_available', return_value=True)
    @patch('setup_api_key._keyring_delete', return_value=True)
    def test_remove_key_from_keyring(self, mock_delete, mock_avail):
        """remove_key should delete from keyring."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write('openfda_api_key: keyring\n')
            temp_path = f.name

        try:
            with patch.object(setup_api_key, 'SETTINGS_PATH', temp_path):
                setup_api_key.remove_key()
                mock_delete.assert_called_once_with(
                    setup_api_key.KEYRING_ACCOUNT_OPENFDA
                )
        finally:
            os.unlink(temp_path)


class TestPlaintextMigration(unittest.TestCase):
    """Test migration from plaintext to keyring."""

    def setUp(self):
        setup_api_key._keyring_available = None

    def test_plaintext_key_detected(self):
        """_read_plaintext_key should find keys in settings file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write('openfda_api_key: ABCD1234EFGH5678\n')
            temp_path = f.name

        try:
            with patch.object(setup_api_key, 'SETTINGS_PATH', temp_path):
                key = setup_api_key._read_plaintext_key()
                self.assertEqual(key, 'ABCD1234EFGH5678')
        finally:
            os.unlink(temp_path)

    def test_keyring_marker_not_treated_as_key(self):
        """'keyring' marker should not be returned as an actual key."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write('openfda_api_key: keyring\n')
            temp_path = f.name

        try:
            with patch.object(setup_api_key, 'SETTINGS_PATH', temp_path):
                key = setup_api_key._read_plaintext_key()
                self.assertIsNone(key)
        finally:
            os.unlink(temp_path)

    def test_null_marker_not_treated_as_key(self):
        """'null' marker should not be returned as an actual key."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write('openfda_api_key: null\n')
            temp_path = f.name

        try:
            with patch.object(setup_api_key, 'SETTINGS_PATH', temp_path):
                key = setup_api_key._read_plaintext_key()
                self.assertIsNone(key)
        finally:
            os.unlink(temp_path)

    @patch('setup_api_key._is_keyring_available', return_value=True)
    @patch('setup_api_key._keyring_set', return_value=True)
    @patch('setup_api_key._keyring_get', return_value=None)
    def test_auto_migration_on_read(self, mock_get, mock_set, mock_avail):
        """Reading a plaintext key should auto-migrate to keyring."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write('openfda_api_key: PLAINTEXT_SECRET_KEY\nopenfda_enabled: true\n')
            temp_path = f.name

        try:
            with patch.object(setup_api_key, 'SETTINGS_PATH', temp_path):
                with patch.dict(os.environ, {}, clear=True):
                    env = os.environ.copy()
                    env.pop('OPENFDA_API_KEY', None)
                    with patch.dict(os.environ, env, clear=True):
                        key = setup_api_key.get_current_key()
                        self.assertEqual(key, 'PLAINTEXT_SECRET_KEY')
                        # Verify migration was attempted
                        mock_set.assert_called_once_with(
                            setup_api_key.KEYRING_ACCOUNT_OPENFDA,
                            'PLAINTEXT_SECRET_KEY'
                        )
                        # Verify plaintext was scrubbed
                        with open(temp_path) as f:
                            content = f.read()
                        self.assertNotIn('PLAINTEXT_SECRET_KEY', content)
                        self.assertIn('openfda_api_key: keyring', content)
        finally:
            os.unlink(temp_path)

    def test_scrub_plaintext_key(self):
        """_scrub_plaintext_key should replace key with 'keyring' marker."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write('openfda_api_key: MY_SECRET_KEY_123\nopenfda_enabled: true\n')
            temp_path = f.name

        try:
            with patch.object(setup_api_key, 'SETTINGS_PATH', temp_path):
                setup_api_key._scrub_plaintext_key()
                with open(temp_path) as f:
                    content = f.read()
                self.assertNotIn('MY_SECRET_KEY_123', content)
                self.assertIn('openfda_api_key: keyring', content)
                # Check file permissions are restricted
                file_stat = os.stat(temp_path)
                mode = file_stat.st_mode & 0o777
                self.assertEqual(mode, 0o600,
                    f"Expected 0600 permissions, got {oct(mode)}")
        finally:
            os.unlink(temp_path)


class TestResolutionOrder(unittest.TestCase):
    """Test key resolution priority: env > keyring > plaintext."""

    def setUp(self):
        setup_api_key._keyring_available = None

    @patch('setup_api_key._is_keyring_available', return_value=True)
    @patch('setup_api_key._keyring_get', return_value='keyring-key')
    def test_env_takes_priority_over_keyring(self, mock_get, mock_avail):
        """Environment variable should take priority over keyring."""
        with patch.dict(os.environ, {'OPENFDA_API_KEY': 'env-key'}):
            key = setup_api_key.get_current_key()
            self.assertEqual(key, 'env-key')
            # keyring should not even be consulted
            mock_get.assert_not_called()

    @patch('setup_api_key._is_keyring_available', return_value=True)
    @patch('setup_api_key._keyring_get', return_value='keyring-key')
    def test_keyring_takes_priority_over_plaintext(self, mock_get, mock_avail):
        """Keyring should take priority over plaintext file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write('openfda_api_key: file-key\n')
            temp_path = f.name

        try:
            with patch.object(setup_api_key, 'SETTINGS_PATH', temp_path):
                with patch.dict(os.environ, {}, clear=True):
                    env = os.environ.copy()
                    env.pop('OPENFDA_API_KEY', None)
                    with patch.dict(os.environ, env, clear=True):
                        key = setup_api_key.get_current_key()
                        self.assertEqual(key, 'keyring-key')
        finally:
            os.unlink(temp_path)


class TestFallbackStorage(unittest.TestCase):
    """Test fallback to file-based storage when keyring unavailable."""

    def setUp(self):
        setup_api_key._keyring_available = None

    @patch('setup_api_key._is_keyring_available', return_value=False)
    def test_fallback_sets_file_permissions(self, mock_avail):
        """Fallback file should have restricted permissions (0600)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write('openfda_api_key: null\nopenfda_enabled: true\n')
            temp_path = f.name

        try:
            with patch.object(setup_api_key, 'SETTINGS_PATH', temp_path):
                setup_api_key.set_key('fallback-key-789')
                # Verify file permissions
                file_stat = os.stat(temp_path)
                mode = file_stat.st_mode & 0o777
                self.assertEqual(mode, 0o600,
                    f"Expected 0600 permissions, got {oct(mode)}")
                # Verify key was written
                with open(temp_path) as f:
                    content = f.read()
                self.assertIn('fallback-key-789', content)
        finally:
            os.unlink(temp_path)


class TestBridgeKeyStorage(unittest.TestCase):
    """Test bridge API key storage (used by FDA-82)."""

    def setUp(self):
        setup_api_key._keyring_available = None

    @patch('setup_api_key._is_keyring_available', return_value=True)
    @patch('setup_api_key._keyring_set', return_value=True)
    def test_set_bridge_key(self, mock_set, mock_avail):
        """Bridge key should be stored in keyring."""
        result = setup_api_key.set_bridge_key('bridge-secret-abc')
        self.assertTrue(result)
        mock_set.assert_called_once_with(
            setup_api_key.KEYRING_ACCOUNT_BRIDGE,
            'bridge-secret-abc'
        )

    @patch('setup_api_key._is_keyring_available', return_value=True)
    @patch('setup_api_key._keyring_get', return_value='bridge-secret-abc')
    def test_get_bridge_key(self, mock_get, mock_avail):
        """Bridge key should be retrievable from keyring."""
        key = setup_api_key.get_bridge_key()
        self.assertEqual(key, 'bridge-secret-abc')

    @patch('setup_api_key._is_keyring_available', return_value=False)
    def test_bridge_key_returns_none_without_keyring(self, mock_avail):
        """Bridge key should return None if keyring unavailable."""
        key = setup_api_key.get_bridge_key()
        self.assertIsNone(key)


class TestNoPlaintextLeakage(unittest.TestCase):
    """Verify no plaintext keys remain after operations."""

    def setUp(self):
        setup_api_key._keyring_available = None

    @patch('setup_api_key._is_keyring_available', return_value=True)
    @patch('setup_api_key._keyring_set', return_value=True)
    def test_set_key_scrubs_file(self, mock_set, mock_avail):
        """After set_key with keyring, settings file should not contain real key."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write('openfda_api_key: OLD_PLAINTEXT_KEY\nopenfda_enabled: true\n')
            temp_path = f.name

        try:
            with patch.object(setup_api_key, 'SETTINGS_PATH', temp_path):
                setup_api_key.set_key('new-secure-key')
                with open(temp_path) as f:
                    content = f.read()
                # The new key should NOT appear in plaintext
                self.assertNotIn('new-secure-key', content)
                # Should show 'keyring' marker instead
                self.assertIn('openfda_api_key: keyring', content)
                # Old plaintext key should also be gone
                self.assertNotIn('OLD_PLAINTEXT_KEY', content)
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    unittest.main()
