#!/usr/bin/env python3
"""
Test suite for centralized configuration system (FDA-180 / ARCH-002)

This test suite verifies:
- TOML parsing
- Configuration loading from multiple sources
- Priority hierarchy (env > user > system > defaults)
- Type-safe accessors
- Path expansion
- Feature flags
- Backward compatibility
- Thread safety
- Integration with secure_config

Test Coverage: 30+ tests
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from threading import Thread
from unittest.mock import Mock, patch

# Add parent directory to path for imports
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from lib.config import (
    Config,
    SimpleTomlParser,
    get_config,
    reset_config,
    get_base_dir,
    get_cache_dir,
    is_feature_enabled,
)


class TestSimpleTomlParser(unittest.TestCase):
    """Test TOML parser functionality."""

    def test_parse_empty(self):
        """Test parsing empty TOML content."""
        result = SimpleTomlParser.parse("")
        self.assertEqual(result, {})

    def test_parse_comments(self):
        """Test that comments are ignored."""
        content = """
        # This is a comment
        [section]
        # Another comment
        key = "value"  # inline comment
        """
        result = SimpleTomlParser.parse(content)
        self.assertEqual(result, {'section': {'key': 'value'}})

    def test_parse_strings(self):
        """Test parsing string values."""
        content = """
        [strings]
        double = "hello"
        single = 'world'
        empty = ""
        """
        result = SimpleTomlParser.parse(content)
        self.assertEqual(result['strings']['double'], 'hello')
        self.assertEqual(result['strings']['single'], 'world')
        self.assertEqual(result['strings']['empty'], '')

    def test_parse_numbers(self):
        """Test parsing numeric values."""
        content = """
        [numbers]
        integer = 42
        negative = -10
        float = 3.14
        """
        result = SimpleTomlParser.parse(content)
        self.assertEqual(result['numbers']['integer'], 42)
        self.assertEqual(result['numbers']['negative'], -10)
        self.assertAlmostEqual(result['numbers']['float'], 3.14)

    def test_parse_booleans(self):
        """Test parsing boolean values."""
        content = """
        [booleans]
        true_val = true
        false_val = false
        """
        result = SimpleTomlParser.parse(content)
        self.assertTrue(result['booleans']['true_val'])
        self.assertFalse(result['booleans']['false_val'])

    def test_parse_arrays(self):
        """Test parsing array values."""
        content = """
        [arrays]
        strings = ["a", "b", "c"]
        numbers = [1, 2, 3]
        empty = []
        """
        result = SimpleTomlParser.parse(content)
        self.assertEqual(result['arrays']['strings'], ['a', 'b', 'c'])
        self.assertEqual(result['arrays']['numbers'], [1, 2, 3])
        self.assertEqual(result['arrays']['empty'], [])

    def test_parse_nested_sections(self):
        """Test parsing nested sections."""
        content = """
        [parent.child]
        key = "value"

        [parent.child.grandchild]
        nested = true
        """
        result = SimpleTomlParser.parse(content)
        self.assertEqual(result['parent']['child']['key'], 'value')
        self.assertTrue(result['parent']['child']['grandchild']['nested'])


class TestConfigLoading(unittest.TestCase):
    """Test configuration loading from multiple sources."""

    def setUp(self):
        """Set up test fixtures."""
        reset_config()
        self.temp_dir = tempfile.mkdtemp()
        self.system_config_path = Path(self.temp_dir) / "system.toml"
        self.user_config_path = Path(self.temp_dir) / "user.toml"

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        reset_config()

    def test_load_defaults(self):
        """Test loading with defaults only."""
        config = Config(
            system_config_path=Path("/nonexistent/system.toml"),
            user_config_path=Path("/nonexistent/user.toml"),
            auto_load=True
        )
        # Should load defaults
        self.assertEqual(config.get_str('general.plugin_name'), 'fda-tools')
        self.assertEqual(config.get_str('api.openfda_base_url'), 'https://api.fda.gov')

    def test_load_system_config(self):
        """Test loading system configuration file."""
        # Write system config
        self.system_config_path.write_text("""
        [general]
        plugin_name = "custom-name"

        [api]
        openfda_base_url = "https://custom.api.gov"
        """)

        config = Config(
            system_config_path=self.system_config_path,
            user_config_path=Path("/nonexistent/user.toml"),
            auto_load=True
        )

        self.assertEqual(config.get_str('general.plugin_name'), 'custom-name')
        self.assertEqual(config.get_str('api.openfda_base_url'), 'https://custom.api.gov')

    def test_load_user_config_overrides_system(self):
        """Test that user config overrides system config."""
        # Write system config
        self.system_config_path.write_text("""
        [api]
        openfda_base_url = "https://system.api.gov"
        openfda_timeout = 30
        """)

        # Write user config
        self.user_config_path.write_text("""
        [api]
        openfda_base_url = "https://user.api.gov"
        """)

        config = Config(
            system_config_path=self.system_config_path,
            user_config_path=self.user_config_path,
            auto_load=True
        )

        # User overrides system
        self.assertEqual(config.get_str('api.openfda_base_url'), 'https://user.api.gov')
        # System value retained for non-overridden keys
        self.assertEqual(config.get_int('api.openfda_timeout'), 30)

    @patch.dict(os.environ, {'FDA_API_OPENFDA_BASE_URL': 'https://env.api.gov'})
    def test_env_overrides_all(self):
        """Test that environment variables override all config files."""
        # Write user config
        self.user_config_path.write_text("""
        [api]
        openfda_base_url = "https://user.api.gov"
        """)

        config = Config(
            system_config_path=Path("/nonexistent/system.toml"),
            user_config_path=self.user_config_path,
            auto_load=True
        )

        # Environment overrides user config
        self.assertEqual(config.get('api.openfda.base.url'), 'https://env.api.gov')

    def test_reload_config(self):
        """Test configuration reload."""
        # Initial config
        self.user_config_path.write_text("""
        [api]
        openfda_base_url = "https://v1.api.gov"
        """)

        config = Config(
            system_config_path=Path("/nonexistent/system.toml"),
            user_config_path=self.user_config_path,
            auto_load=True
        )
        self.assertEqual(config.get_str('api.openfda_base_url'), 'https://v1.api.gov')

        # Update config file
        self.user_config_path.write_text("""
        [api]
        openfda_base_url = "https://v2.api.gov"
        """)

        # Reload
        config.reload()
        self.assertEqual(config.get_str('api.openfda_base_url'), 'https://v2.api.gov')


class TestConfigAccessors(unittest.TestCase):
    """Test type-safe configuration accessors."""

    def setUp(self):
        """Set up test fixtures."""
        reset_config()

    def tearDown(self):
        """Clean up test fixtures."""
        reset_config()

    def test_get_str(self):
        """Test string accessor."""
        config = get_config()
        value = config.get_str('general.plugin_name')
        self.assertIsInstance(value, str)
        self.assertEqual(value, 'fda-tools')

    def test_get_int(self):
        """Test integer accessor."""
        config = get_config()
        value = config.get_int('api.openfda_timeout')
        self.assertIsInstance(value, int)
        self.assertEqual(value, 30)

    def test_get_float(self):
        """Test float accessor."""
        config = get_config()
        config.set('test.float_value', 3.14)
        value = config.get_float('test.float_value')
        self.assertIsInstance(value, float)
        self.assertAlmostEqual(value, 3.14)

    def test_get_bool(self):
        """Test boolean accessor."""
        config = get_config()
        value = config.get_bool('http.verify_ssl')
        self.assertIsInstance(value, bool)
        self.assertTrue(value)

    def test_get_list(self):
        """Test list accessor."""
        config = get_config()
        config.set('test.list_value', ['a', 'b', 'c'])
        value = config.get_list('test.list_value')
        self.assertIsInstance(value, list)
        self.assertEqual(value, ['a', 'b', 'c'])

    def test_get_path(self):
        """Test path accessor with expansion."""
        config = get_config()
        config.set('test.path', '~/test/path')
        value = config.get_path('test.path')
        self.assertIsInstance(value, Path)
        self.assertFalse(str(value).startswith('~'))
        self.assertTrue(str(value).startswith(str(Path.home())))

    def test_get_default(self):
        """Test default value handling."""
        config = get_config()
        value = config.get('nonexistent.key', 'default')
        self.assertEqual(value, 'default')

    def test_get_section(self):
        """Test getting entire configuration section."""
        config = get_config()
        api_section = config.get_section('api')
        self.assertIsInstance(api_section, dict)
        self.assertIn('openfda_base_url', api_section)

    def test_set_and_get(self):
        """Test runtime configuration setting."""
        config = get_config()
        config.set('test.runtime_key', 'runtime_value')
        value = config.get('test.runtime_key')
        self.assertEqual(value, 'runtime_value')


class TestFeatureFlags(unittest.TestCase):
    """Test feature flag functionality."""

    def setUp(self):
        """Set up test fixtures."""
        reset_config()

    def tearDown(self):
        """Clean up test fixtures."""
        reset_config()

    def test_is_feature_enabled_true(self):
        """Test enabled feature flag."""
        config = get_config()
        # Enrichment is enabled by default
        self.assertTrue(config.is_feature_enabled('enrichment'))

    def test_is_feature_enabled_false(self):
        """Test disabled feature flag."""
        config = get_config()
        # OCR is disabled by default
        self.assertFalse(config.is_feature_enabled('pdf_ocr'))

    def test_is_feature_enabled_nonexistent(self):
        """Test nonexistent feature flag."""
        config = get_config()
        self.assertFalse(config.is_feature_enabled('nonexistent_feature'))


class TestPathExpansion(unittest.TestCase):
    """Test path expansion functionality."""

    def setUp(self):
        """Set up test fixtures."""
        reset_config()

    def tearDown(self):
        """Clean up test fixtures."""
        reset_config()

    def test_expand_tilde_in_paths(self):
        """Test that ~ is expanded in path values."""
        config = get_config()
        base_dir = config.get_path('paths.base_dir')
        self.assertFalse(str(base_dir).startswith('~'))
        self.assertTrue(str(base_dir).startswith(str(Path.home())))

    def test_get_path_convenience_functions(self):
        """Test convenience path functions."""
        base_dir = get_base_dir()
        self.assertIsInstance(base_dir, Path)
        self.assertFalse(str(base_dir).startswith('~'))

        cache_dir = get_cache_dir()
        self.assertIsInstance(cache_dir, Path)


class TestSingleton(unittest.TestCase):
    """Test singleton pattern."""

    def setUp(self):
        """Set up test fixtures."""
        reset_config()

    def tearDown(self):
        """Clean up test fixtures."""
        reset_config()

    def test_singleton_same_instance(self):
        """Test that get_config returns same instance."""
        config1 = get_config()
        config2 = get_config()
        self.assertIs(config1, config2)

    def test_singleton_thread_safe(self):
        """Test that singleton is thread-safe."""
        instances = []

        def get_instance():
            instances.append(get_config())

        threads = [Thread(target=get_instance) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All instances should be the same
        for instance in instances[1:]:
            self.assertIs(instance, instances[0])

    def test_reset_config(self):
        """Test configuration reset."""
        config1 = get_config()
        reset_config()
        config2 = get_config()
        self.assertIsNot(config1, config2)


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility functions."""

    def setUp(self):
        """Set up test fixtures."""
        reset_config()

    def tearDown(self):
        """Clean up test fixtures."""
        reset_config()

    def test_get_base_dir(self):
        """Test get_base_dir convenience function."""
        base_dir = get_base_dir()
        self.assertIsInstance(base_dir, Path)

    def test_get_cache_dir(self):
        """Test get_cache_dir convenience function."""
        cache_dir = get_cache_dir()
        self.assertIsInstance(cache_dir, Path)

    def test_is_feature_enabled(self):
        """Test is_feature_enabled convenience function."""
        enabled = is_feature_enabled('enrichment')
        self.assertIsInstance(enabled, bool)


class TestSecureConfigIntegration(unittest.TestCase):
    """Test integration with secure_config module."""

    def setUp(self):
        """Set up test fixtures."""
        reset_config()

    def tearDown(self):
        """Clean up test fixtures."""
        reset_config()

    def test_secure_config_integration(self):
        """Test that Config integrates with SecureConfig."""
        # Create a mock SecureConfig instance
        mock_secure_config = Mock()
        mock_secure_config.get_api_key.return_value = 'test-api-key'

        # Inject mock into config
        config = Config(auto_load=False)
        config._secure_config = mock_secure_config
        config._loaded = True

        api_key = config.get_api_key('openfda')

        mock_secure_config.get_api_key.assert_called_once_with('openfda')
        self.assertEqual(api_key, 'test-api-key')

    def test_secure_config_unavailable(self):
        """Test behavior when secure_config is not available."""
        config = Config(auto_load=False)
        config._secure_config = None
        config._loaded = True

        api_key = config.get_api_key('openfda')
        self.assertIsNone(api_key)


class TestConfigExport(unittest.TestCase):
    """Test configuration export functionality."""

    def setUp(self):
        """Set up test fixtures."""
        reset_config()

    def tearDown(self):
        """Clean up test fixtures."""
        reset_config()

    def test_to_dict(self):
        """Test exporting configuration to dictionary."""
        config = get_config()
        config_dict = config.to_dict()
        self.assertIsInstance(config_dict, dict)
        self.assertIn('general', config_dict)
        self.assertIn('api', config_dict)
        self.assertIn('paths', config_dict)

    def test_to_dict_includes_overrides(self):
        """Test that to_dict includes runtime overrides."""
        config = get_config()
        config.set('test.key', 'test_value')
        config_dict = config.to_dict()
        self.assertEqual(config_dict['test']['key'], 'test_value')


class TestEnvironmentVariables(unittest.TestCase):
    """Test environment variable handling."""

    def setUp(self):
        """Set up test fixtures."""
        reset_config()

    def tearDown(self):
        """Clean up test fixtures."""
        reset_config()

    @patch.dict(os.environ, {'FDA_API_OPENFDA_TIMEOUT': '60'})
    def test_env_var_integer(self):
        """Test environment variable integer parsing."""
        config = Config(auto_load=True)
        # Environment variable should override default
        timeout = config.get('api.openfda.timeout')
        self.assertEqual(timeout, 60)

    @patch.dict(os.environ, {'FDA_FEATURES_ENABLE_ENRICHMENT': 'false'})
    def test_env_var_boolean(self):
        """Test environment variable boolean parsing."""
        config = Config(auto_load=True)
        enabled = config.get('features.enable.enrichment')
        self.assertFalse(enabled)

    @patch.dict(os.environ, {'FDA_HTTP_BASE_BACKOFF': '2.5'})
    def test_env_var_float(self):
        """Test environment variable float parsing."""
        config = Config(auto_load=True)
        backoff = config.get('http.base.backoff')
        self.assertAlmostEqual(backoff, 2.5)


if __name__ == '__main__':
    unittest.main()
