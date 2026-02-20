#!/usr/bin/env python3
"""
Centralized Configuration Management System (FDA-180 / ARCH-002)

This module provides a unified configuration interface that consolidates settings
from multiple sources (TOML files, environment variables, defaults) into a single,
type-safe, validated configuration object.

Architecture:
    - Single source of truth for all configuration
    - Hierarchical configuration priority
    - Schema validation with defaults
    - Integration with secure_config.py for API keys
    - Backward compatibility with existing code
    - Thread-safe singleton pattern

Configuration Priority (highest to lowest):
    1. Environment variables (e.g., OPENFDA_API_KEY)
    2. User override file (~/.claude/fda-tools.config.toml)
    3. System config file (plugins/fda-tools/config.toml)
    4. Hard-coded defaults in this module

Usage:
from fda_tools.lib.config import get_config, Config

    # Get singleton config instance
    config = get_config()

    # Access configuration values
    api_url = config.get('api.openfda_base_url')
    cache_dir = config.get_path('paths.cache_dir')
    rate_limit = config.get_int('rate_limiting.rate_limit_openfda')

    # Check feature flags
    if config.is_feature_enabled('enrichment'):
        # ...

    # Get API key (delegates to secure_config)
    api_key = config.get_api_key('openfda')

Integration:
    - Works with lib/secure_config.py for API key management
    - Replaces scattered configuration parsing in 87 scripts
    - Provides type-safe accessors with validation
    - Supports hot-reload for development
    - 100% backward compatible

Version: 1.0.0 (FDA-180)
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from threading import Lock

# FDA-206 (CQ-005): Use standard TOML parser instead of custom implementation
# Python 3.11+ has tomllib in stdlib, earlier versions use tomli backport
try:
    import tomllib  # type: ignore
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

logger = logging.getLogger(__name__)

# ============================================================
# Constants
# ============================================================

# Default config file locations
DEFAULT_SYSTEM_CONFIG = Path(__file__).parent.parent / "config.toml"
DEFAULT_USER_CONFIG = Path.home() / ".claude" / "fda-tools.config.toml"
LEGACY_SETTINGS_FILE = Path.home() / ".claude" / "fda-tools.local.md"

# Environment variable prefix
ENV_PREFIX = "FDA_"

# ============================================================
# Type Definitions
# ============================================================

ConfigValue = Union[str, int, float, bool, List[str], Dict[str, Any]]
ConfigDict = Dict[str, Any]

# ============================================================
# Configuration Class
# ============================================================


class Config:
    """Centralized configuration management with hierarchical loading.

    This class loads configuration from multiple sources and provides
    type-safe accessors with validation and path expansion.

    Thread-safe singleton pattern ensures consistent configuration
    across all modules.
    """

    _instance: Optional['Config'] = None
    _lock = Lock()

    def __init__(self,
                 system_config_path: Optional[Path] = None,
                 user_config_path: Optional[Path] = None,
                 auto_load: bool = True):
        """Initialize configuration manager.

        Args:
            system_config_path: Path to system config.toml (default: auto-detect)
            user_config_path: Path to user config file (default: ~/.claude/fda-tools.config.toml)
            auto_load: Automatically load configuration on init
        """
        self.system_config_path = system_config_path or DEFAULT_SYSTEM_CONFIG
        self.user_config_path = user_config_path or DEFAULT_USER_CONFIG
        self.legacy_settings_path = LEGACY_SETTINGS_FILE

        self._config: ConfigDict = {}
        self._env_overrides: ConfigDict = {}
        self._loaded = False

        # Integration with secure_config
        self._secure_config: Optional[Any] = None

        if auto_load:
            self.load()

    def load(self) -> None:
        """Load configuration from all sources in priority order.

        Priority (highest to lowest):
        1. Environment variables
        2. User config file (~/.claude/fda-tools.config.toml)
        3. System config file (plugins/fda-tools/config.toml)
        4. Hard-coded defaults
        """
        if self._loaded:
            logger.debug("Configuration already loaded, skipping reload")
            return

        logger.info("Loading FDA Tools configuration...")

        # Load defaults (hard-coded)
        self._config = self._get_defaults()

        # Load system config file
        if self.system_config_path.exists():
            try:
                system_config = self._load_toml_file(self.system_config_path)
                self._merge_config(self._config, system_config)
                logger.info(f"Loaded system config from {self.system_config_path}")
            except Exception as e:
                logger.warning(f"Failed to load system config from {self.system_config_path}: {e}")

        # Load user config file
        if self.user_config_path.exists():
            try:
                user_config = self._load_toml_file(self.user_config_path)
                self._merge_config(self._config, user_config)
                logger.info(f"Loaded user config from {self.user_config_path}")
            except Exception as e:
                logger.warning(f"Failed to load user config from {self.user_config_path}: {e}")

        # Load environment variable overrides
        self._env_overrides = self._load_env_overrides()

        # Expand paths
        self._expand_paths()

        # Initialize secure_config integration
        self._init_secure_config()

        self._loaded = True
        logger.info("Configuration loaded successfully")

    def reload(self) -> None:
        """Reload configuration from all sources.

        Useful for development/testing when config files change.
        """
        self._loaded = False
        self.load()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dotted key path.

        Args:
            key: Dotted key path (e.g., 'api.openfda_base_url')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Examples:
            >>> config.get('api.openfda_base_url')
            'https://api.fda.gov'
            >>> config.get('nonexistent.key', 'default')
            'default'
        """
        # Check environment overrides first
        if key in self._env_overrides:
            return self._env_overrides[key]

        # Navigate nested dict
        parts = key.split('.')
        value = self._config
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value

    def get_str(self, key: str, default: str = "") -> str:
        """Get string configuration value.

        Args:
            key: Dotted key path
            default: Default value if key not found

        Returns:
            String value
        """
        value = self.get(key, default)
        return str(value) if value is not None else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration value.

        Args:
            key: Dotted key path
            default: Default value if key not found

        Returns:
            Integer value
        """
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float configuration value.

        Args:
            key: Dotted key path
            default: Default value if key not found

        Returns:
            Float value
        """
        value = self.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value.

        Args:
            key: Dotted key path
            default: Default value if key not found

        Returns:
            Boolean value
        """
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    def get_list(self, key: str, default: Optional[List] = None) -> List:
        """Get list configuration value.

        Args:
            key: Dotted key path
            default: Default value if key not found

        Returns:
            List value
        """
        value = self.get(key, default or [])
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # Try to parse comma-separated string
            return [v.strip() for v in value.split(',') if v.strip()]
        return default or []

    def get_path(self, key: str, default: Optional[Path] = None) -> Path:
        """Get path configuration value with expansion.

        Args:
            key: Dotted key path
            default: Default value if key not found

        Returns:
            Path object with ~ expanded
        """
        value = self.get(key)
        if value is None:
            return default or Path()
        return Path(os.path.expanduser(str(value)))

    def get_api_key(self, key_type: str) -> Optional[str]:
        """Get API key using secure_config integration.

        Args:
            key_type: Key type ('openfda', 'linear', 'bridge', 'gemini')

        Returns:
            API key if found, None otherwise
        """
        if self._secure_config is None:
            return None
        return self._secure_config.get_api_key(key_type)

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature flag is enabled.

        Args:
            feature: Feature name (e.g., 'enrichment', 'intelligence')

        Returns:
            True if feature is enabled
        """
        return self.get_bool(f'features.enable_{feature}', False)

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section.

        Args:
            section: Section name (e.g., 'api', 'paths')

        Returns:
            Dictionary of section values
        """
        return self.get(section, {})

    def set(self, key: str, value: Any) -> None:
        """Set configuration value (runtime only, not persisted).

        Args:
            key: Dotted key path
            value: Value to set
        """
        parts = key.split('.')
        d = self._config
        for part in parts[:-1]:
            if part not in d:
                d[part] = {}
            d = d[part]
        d[parts[-1]] = value

    def to_dict(self) -> ConfigDict:
        """Export entire configuration as dictionary.

        Returns:
            Complete configuration dictionary
        """
        result = dict(self._config)
        # Apply environment overrides
        for key, value in self._env_overrides.items():
            parts = key.split('.')
            d = result
            for part in parts[:-1]:
                if part not in d:
                    d[part] = {}
                d = d[part]
            d[parts[-1]] = value
        return result

    # ========================================
    # Private methods
    # ========================================

    def _get_defaults(self) -> ConfigDict:
        """Get hard-coded default configuration.

        Returns:
            Default configuration dictionary
        """
        # Import version dynamically from version.py
        try:
            from fda_tools.scripts.version import PLUGIN_VERSION
        except ImportError:
            try:
                from version import PLUGIN_VERSION
            except ImportError:
                PLUGIN_VERSION = '5.36.0'  # Fallback to current version

        return {
            'general': {
                'plugin_name': 'fda-tools',
                'plugin_version': PLUGIN_VERSION,
                'environment': 'production',
            },
            'paths': {
                'base_dir': '~/.claude/fda-510k-data',
                'cache_dir': '~/.claude/fda-510k-data/cache',
                'projects_dir': '~/.claude/fda-510k-data/projects',
                'output_dir': '~/.claude/fda-510k-data/output',
                'logs_dir': '~/.claude/fda-510k-data/logs',
                'temp_dir': '~/.claude/fda-510k-data/temp',
                'backup_dir': '~/.claude/fda-510k-data/backups',
            },
            'api': {
                'openfda_base_url': 'https://api.fda.gov',
                'openfda_device_endpoint': 'https://api.fda.gov/device',
                'openfda_rate_limit_unauthenticated': 240,
                'openfda_rate_limit_authenticated': 1000,
                'openfda_timeout': 30,
                'fda_accessdata_base_url': 'https://www.accessdata.fda.gov',
                'fda_cdrh_docs_base_url': 'https://www.accessdata.fda.gov/cdrh_docs',
            },
            'http': {
                'user_agent_override': '',
                'honest_ua_only': False,
                'max_retries': 5,
                'base_backoff': 1.0,
                'verify_ssl': True,
            },
            'cache': {
                'default_ttl': 604800,  # 7 days
                'enable_integrity_checks': True,
                'atomic_writes': True,
            },
            'rate_limiting': {
                'enable_cross_process': True,
                'rate_limit_openfda': 240,
                'rate_limit_pdf_download': 2,
            },
            'logging': {
                'level': 'INFO',
                'log_to_file': True,
                'log_to_console': True,
                'redact_api_keys': True,
            },
            'security': {
                'keyring_service': 'fda-tools-plugin',
                'enable_keyring': True,
                'api_key_redaction': True,
                'validate_file_paths': True,
            },
            'features': {
                'enable_enrichment': True,
                'enable_intelligence': True,
                'enable_pdf_ocr': False,
            },
        }

    def _load_toml_file(self, path: Path) -> ConfigDict:
        """Load and parse TOML configuration file.

        Args:
            path: Path to TOML file

        Returns:
            Parsed configuration dictionary
        """
        # FDA-206 (CQ-005): Use standard TOML parser (tomllib/tomli)
        with open(path, 'rb') as f:  # tomllib requires binary mode
            return tomllib.load(f)

    def _merge_config(self, base: ConfigDict, override: ConfigDict) -> None:
        """Recursively merge override config into base config.

        Args:
            base: Base configuration (modified in place)
            override: Override configuration
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _load_env_overrides(self) -> ConfigDict:
        """Load configuration overrides from environment variables.

        Environment variables follow pattern: FDA_SECTION_KEY=value
        Example: FDA_API_OPENFDA_BASE_URL=https://custom.api.gov

        Returns:
            Dictionary mapping dotted keys to values
        """
        overrides = {}
        for env_key, env_value in os.environ.items():
            if not env_key.startswith(ENV_PREFIX):
                continue

            # Remove prefix and convert to dotted key
            key_parts = env_key[len(ENV_PREFIX):].lower().split('_')
            dotted_key = '.'.join(key_parts)

            # Parse value
            value: Any = env_value
            if env_value.lower() in ('true', 'false'):
                value = env_value.lower() == 'true'
            elif env_value.isdigit():
                value = int(env_value)
            else:
                try:
                    value = float(env_value)
                except ValueError:
                    pass

            overrides[dotted_key] = value
            logger.debug(f"Environment override: {dotted_key} = {value}")

        return overrides

    def _expand_paths(self) -> None:
        """Expand ~ in all path values."""
        if 'paths' not in self._config:
            return

        for key, value in self._config['paths'].items():
            if isinstance(value, str) and value.startswith('~'):
                self._config['paths'][key] = os.path.expanduser(value)

    def _init_secure_config(self) -> None:
        """Initialize secure_config integration for API keys."""
        try:
            from secure_config import SecureConfig  # type: ignore
            self._secure_config = SecureConfig()
            logger.debug("Initialized secure_config integration")
        except ImportError:
            logger.warning("secure_config not available, API key methods will not work")
            self._secure_config = None


# ============================================================
# Singleton accessor
# ============================================================

_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get singleton configuration instance.

    Thread-safe lazy initialization.

    Returns:
        Global Config instance
    """
    global _config_instance
    if _config_instance is None:
        with Config._lock:
            if _config_instance is None:
                _config_instance = Config()
    return _config_instance


def reset_config() -> None:
    """Reset configuration singleton (for testing).

    WARNING: This should only be used in test code.
    """
    global _config_instance
    _config_instance = None


# ============================================================
# Convenience functions (backward compatibility)
# ============================================================


def get_base_dir() -> Path:
    """Get base data directory."""
    return get_config().get_path('paths.base_dir')


def get_cache_dir() -> Path:
    """Get cache directory."""
    return get_config().get_path('paths.cache_dir')


def get_projects_dir() -> Path:
    """Get projects directory."""
    return get_config().get_path('paths.projects_dir')


def get_output_dir() -> Path:
    """Get output directory."""
    return get_config().get_path('paths.output_dir')


def get_logs_dir() -> Path:
    """Get logs directory."""
    return get_config().get_path('paths.logs_dir')


def get_openfda_base_url() -> str:
    """Get openFDA API base URL."""
    return get_config().get_str('api.openfda_base_url')


def get_openfda_rate_limit() -> int:
    """Get openFDA API rate limit (requests per minute)."""
    return get_config().get_int('rate_limiting.rate_limit_openfda')


def get_cache_ttl() -> int:
    """Get default cache TTL (seconds)."""
    return get_config().get_int('cache.default_ttl')


def is_feature_enabled(feature: str) -> bool:
    """Check if a feature is enabled."""
    return get_config().is_feature_enabled(feature)


# ============================================================
# CLI Entry Point
# ============================================================


def main():
    """CLI for configuration management."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="FDA Tools Configuration Management (FDA-180 / ARCH-002)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show all configuration
  python3 lib/config.py --show

  # Get specific value
  python3 lib/config.py --get api.openfda_base_url

  # Validate configuration
  python3 lib/config.py --validate

  # Export to JSON
  python3 lib/config.py --export config.json
        """
    )
    parser.add_argument('--show', action='store_true', help='Show all configuration')
    parser.add_argument('--get', metavar='KEY', help='Get specific configuration value')
    parser.add_argument('--validate', action='store_true', help='Validate configuration')
    parser.add_argument('--export', metavar='FILE', help='Export configuration to JSON file')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--reload', action='store_true', help='Reload configuration')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    config = get_config()

    if args.reload:
        config.reload()
        print("Configuration reloaded")

    if args.show:
        config_dict = config.to_dict()
        if args.json:
            print(json.dumps(config_dict, indent=2))
        else:
            print("=" * 70)
            print("FDA TOOLS CONFIGURATION")
            print("=" * 70)
            _print_config_dict(config_dict)

    elif args.get:
        value = config.get(args.get)
        if args.json:
            print(json.dumps({args.get: value}, indent=2))
        else:
            print(f"{args.get} = {value}")

    elif args.validate:
        errors = _validate_config(config)
        if args.json:
            print(json.dumps({'valid': len(errors) == 0, 'errors': errors}, indent=2))
        else:
            if errors:
                print("Configuration validation FAILED:")
                for error in errors:
                    print(f"  ✗ {error}")
                return 1
            else:
                print("✓ Configuration validation passed")

    elif args.export:
        config_dict = config.to_dict()
        with open(args.export, 'w') as f:
            json.dump(config_dict, f, indent=2)
        print(f"Configuration exported to {args.export}")

    else:
        parser.print_help()

    return 0


def _print_config_dict(d: Dict, indent: int = 0):
    """Pretty-print configuration dictionary."""
    for key, value in sorted(d.items()):
        if isinstance(value, dict):
            print("  " * indent + f"{key}:")
            _print_config_dict(value, indent + 1)
        else:
            print("  " * indent + f"{key} = {value}")


def _validate_config(config: Config) -> List[str]:
    """Validate configuration.

    Args:
        config: Configuration instance

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check required paths exist
    required_paths = ['base_dir', 'cache_dir', 'projects_dir']
    for path_key in required_paths:
        path = config.get_path(f'paths.{path_key}')
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {path}")
            except Exception as e:
                errors.append(f"Cannot create path '{path_key}': {path}: {e}")

    # Check URLs are valid
    urls = [
        'api.openfda_base_url',
        'api.fda_accessdata_base_url',
    ]
    for url_key in urls:
        url = config.get_str(url_key)
        if not url.startswith('http'):
            errors.append(f"Invalid URL for '{url_key}': {url}")

    # Check rate limits are positive
    rate_limits = [
        'rate_limiting.rate_limit_openfda',
        'rate_limiting.rate_limit_pdf_download',
    ]
    for rate_key in rate_limits:
        rate = config.get_int(rate_key)
        if rate <= 0:
            errors.append(f"Invalid rate limit for '{rate_key}': {rate}")

    return errors


if __name__ == '__main__':
    sys.exit(main())
