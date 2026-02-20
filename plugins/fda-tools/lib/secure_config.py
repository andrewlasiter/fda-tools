#!/usr/bin/env python3
"""
Secure API Key Storage - Centralized keyring-based credential management.

This module provides a unified interface for storing and retrieving API keys
securely using the system keyring (macOS Keychain, Windows Credential Locker,
Linux Secret Service / libsecret).

Security Features (FDA-182 / SEC-003):
  - OS keyring storage (no plaintext files)
  - Automatic migration from legacy plaintext storage
  - Environment variable override support
  - API key redaction in logs
  - Backward compatibility with existing code

Supported API Keys:
  - OPENFDA_API_KEY: openFDA API access
  - LINEAR_API_KEY: Linear issue management
  - BRIDGE_API_KEY: OpenClaw bridge server authentication
  - GEMINI_API_KEY: Google Gemini AI API

Usage:
    from lib.secure_config import SecureConfig

    config = SecureConfig()

    # Get API key (checks: env var -> keyring -> legacy file)
    openfda_key = config.get_api_key('openfda')

    # Set API key (stores in keyring)
    config.set_api_key('openfda', 'your-key-here')

    # Migrate from environment or legacy file
    config.migrate_all_keys()

    # Remove key
    config.remove_api_key('openfda')

Architecture:
    This module consolidates the keyring functionality from setup_api_key.py
    into a reusable library that can be imported by any script. It maintains
    backward compatibility with existing code while providing a cleaner API.

Version: 1.0.0 (FDA-182)
"""

import hashlib
import logging
import os
import re
import stat
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# Keyring Service Configuration
# ============================================================

KEYRING_SERVICE = 'fda-tools-plugin'

# Account identifiers for different API keys
KEYRING_ACCOUNTS = {
    'openfda': 'openfda_api_key',
    'linear': 'linear_api_key',
    'bridge': 'bridge_api_key',
    'gemini': 'gemini_api_key',
}

# Environment variable names
ENV_VAR_NAMES = {
    'openfda': 'OPENFDA_API_KEY',
    'linear': 'LINEAR_API_KEY',
    'bridge': 'BRIDGE_API_KEY',
    'gemini': 'GEMINI_API_KEY',
}

# Legacy settings file path
SETTINGS_PATH = Path.home() / '.claude' / 'fda-tools.local.md'

# ============================================================
# API Key Redaction
# ============================================================

_API_KEY_PATTERN = re.compile(r'([a-zA-Z0-9_-]{20,})')


def mask_api_key(key: str) -> str:
    """Mask an API key for safe display, showing only first 4 and last 4 chars.

    Args:
        key: The API key string to mask.

    Returns:
        Masked string like 'abcd...wxyz' or 'REDACTED' for short keys.
    """
    if not key or len(key) < 8:
        return "REDACTED"
    return f"{key[:4]}...{key[-4:]}"


class APIKeyRedactor(logging.Filter):
    """Logging filter that redacts API key-like strings from log messages.

    Scans log message strings for patterns that look like API keys
    (20+ alphanumeric characters) and replaces them with masked versions.
    This prevents accidental key exposure in log files and console output.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact API key patterns from the log record message.

        Args:
            record: The log record to filter.

        Returns:
            Always True (record is never suppressed, only modified).
        """
        if isinstance(record.msg, str):
            record.msg = _API_KEY_PATTERN.sub(
                lambda m: mask_api_key(m.group(1)),
                record.msg,
            )
        # Also redact args if they contain strings
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: (_API_KEY_PATTERN.sub(lambda m: mask_api_key(m.group(1)), v)
                         if isinstance(v, str) else v)
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    _API_KEY_PATTERN.sub(lambda m: mask_api_key(m.group(1)), a)
                    if isinstance(a, str) else a
                    for a in record.args
                )
        return True


def install_api_key_redactor():
    """Install the APIKeyRedactor filter on all root logging handlers.

    Should be called early in application startup to ensure no handlers
    can leak API keys. Safe to call multiple times (idempotent).
    """
    redactor = APIKeyRedactor()
    # Add to root logger handlers
    for handler in logging.root.handlers:
        if not any(isinstance(f, APIKeyRedactor) for f in handler.filters):
            handler.addFilter(redactor)
    # Also add directly to root logger for any future handlers
    if not any(isinstance(f, APIKeyRedactor) for f in logging.root.filters):
        logging.root.addFilter(redactor)


# Install redactor on module import to protect from earliest possible moment
install_api_key_redactor()


# ============================================================
# Keyring Backend Access
# ============================================================

_keyring_available: Optional[bool] = None


def _is_keyring_available() -> bool:
    """Check if the keyring library is available and functional.

    Returns:
        True if keyring is available, False otherwise.
    """
    global _keyring_available
    if _keyring_available is not None:
        return _keyring_available
    try:
        import keyring as kr
        # Attempt a read to verify backend works (e.g., not a headless chroot)
        kr.get_password(KEYRING_SERVICE, '__probe__')
        _keyring_available = True
    except Exception as e:
        logger.debug("Keyring not available: %s", e)
        _keyring_available = False
    return _keyring_available


def _keyring_set(account: str, secret: str) -> bool:
    """Store a secret in OS keyring.

    Args:
        account: Account identifier (e.g., 'openfda_api_key')
        secret: Secret value to store

    Returns:
        True on success, False on failure.
    """
    try:
        import keyring as kr
        kr.set_password(KEYRING_SERVICE, account, secret)
        logger.debug("Stored key in keyring: %s", account)
        return True
    except Exception as e:
        logger.warning("Keyring write failed for %s: %s", account, e)
        return False


def _keyring_get(account: str) -> Optional[str]:
    """Retrieve a secret from OS keyring.

    Args:
        account: Account identifier (e.g., 'openfda_api_key')

    Returns:
        Secret value if found, None otherwise.
    """
    try:
        import keyring as kr
        value = kr.get_password(KEYRING_SERVICE, account)
        if value:
            logger.debug("Retrieved key from keyring: %s", account)
        return value
    except Exception as e:
        logger.debug("Keyring read failed for %s: %s", account, e)
        return None


def _keyring_delete(account: str) -> bool:
    """Delete a secret from OS keyring.

    Args:
        account: Account identifier (e.g., 'openfda_api_key')

    Returns:
        True on success, False on failure.
    """
    try:
        import keyring as kr
        kr.delete_password(KEYRING_SERVICE, account)
        logger.debug("Deleted key from keyring: %s", account)
        return True
    except Exception as e:
        logger.debug("Keyring delete failed for %s: %s", account, e)
        return False


# ============================================================
# Legacy Plaintext Storage (for migration only)
# ============================================================

def _read_plaintext_key(key_type: str) -> Optional[str]:
    """Read API key from legacy plaintext settings file (if present).

    Args:
        key_type: Key type identifier (e.g., 'openfda')

    Returns:
        API key if found, None otherwise.
    """
    if not SETTINGS_PATH.exists():
        return None

    account = KEYRING_ACCOUNTS.get(key_type)
    if not account:
        return None

    try:
        content = SETTINGS_PATH.read_text()
        pattern = rf'{account}:\s*(\S+)'
        m = re.search(pattern, content)
        if m and m.group(1) not in ('null', 'keyring'):
            logger.debug("Found plaintext key in settings file: %s", account)
            return m.group(1)
    except Exception as e:
        logger.debug("Failed to read plaintext key for %s: %s", account, e)
    return None


def _scrub_plaintext_key(key_type: str) -> bool:
    """Remove plaintext API key from settings file, replacing with 'keyring' marker.

    Args:
        key_type: Key type identifier (e.g., 'openfda')

    Returns:
        True on success, False on failure.
    """
    if not SETTINGS_PATH.exists():
        return True

    account = KEYRING_ACCOUNTS.get(key_type)
    if not account:
        return False

    try:
        content = SETTINGS_PATH.read_text()
        pattern = rf'{account}:\s*\S+'
        new_content = re.sub(pattern, f'{account}: keyring', content)
        SETTINGS_PATH.write_text(new_content)
        # Restrict file permissions (owner read/write only)
        SETTINGS_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)
        logger.info("Scrubbed plaintext key from settings file: %s", account)
        return True
    except Exception as e:
        logger.warning("Failed to scrub plaintext key for %s: %s", account, e)
        return False


# ============================================================
# SecureConfig - Main API
# ============================================================

class SecureConfig:
    """Centralized secure API key management using OS keyring.

    This class provides a unified interface for storing and retrieving API keys
    securely. It handles:
    - OS keyring storage (preferred)
    - Environment variable overrides
    - Legacy plaintext migration
    - Backward compatibility

    Resolution Order (get_api_key):
        1. Environment variable (highest priority)
        2. OS keyring
        3. Legacy plaintext file (triggers auto-migration)

    Storage (set_api_key):
        1. OS keyring (preferred)
        2. Fallback to restricted-permission file (if keyring unavailable)
    """

    def __init__(self):
        """Initialize SecureConfig instance."""
        self.keyring_available = _is_keyring_available()
        if self.keyring_available:
            logger.debug("SecureConfig initialized with keyring support")
        else:
            logger.warning(
                "Keyring not available. API keys will use environment variables only. "
                "Install keyring support: sudo apt install gnome-keyring (Linux)"
            )

    def get_api_key(self, key_type: str) -> Optional[str]:
        """Get API key with resolution order: env var -> keyring -> plaintext.

        Args:
            key_type: Key type identifier ('openfda', 'linear', 'bridge', 'gemini')

        Returns:
            API key if found, None otherwise.
        """
        if key_type not in KEYRING_ACCOUNTS:
            raise ValueError(f"Unknown key type: {key_type}. Valid types: {list(KEYRING_ACCOUNTS.keys())}")

        # 1. Environment variable takes priority
        env_var = ENV_VAR_NAMES.get(key_type)
        if env_var:
            env_key = os.environ.get(env_var)
            if env_key:
                logger.debug("Using API key from environment variable: %s", env_var)
                return env_key

        # 2. OS keyring
        if self.keyring_available:
            account = KEYRING_ACCOUNTS[key_type]
            kr_key = _keyring_get(account)
            if kr_key:
                return kr_key

        # 3. Legacy plaintext (auto-migrate if found)
        plaintext_key = _read_plaintext_key(key_type)
        if plaintext_key:
            # Auto-migrate to keyring on first read
            if self.keyring_available:
                account = KEYRING_ACCOUNTS[key_type]
                if _keyring_set(account, plaintext_key):
                    _scrub_plaintext_key(key_type)
                    logger.info("Auto-migrated %s API key from plaintext to OS keyring", key_type)
            return plaintext_key

        return None

    def set_api_key(self, key_type: str, api_key: str) -> bool:
        """Store API key securely in OS keyring.

        Args:
            key_type: Key type identifier ('openfda', 'linear', 'bridge', 'gemini')
            api_key: API key value to store

        Returns:
            True on success, False on failure.
        """
        if key_type not in KEYRING_ACCOUNTS:
            raise ValueError(f"Unknown key type: {key_type}. Valid types: {list(KEYRING_ACCOUNTS.keys())}")

        account = KEYRING_ACCOUNTS[key_type]

        if self.keyring_available:
            success = _keyring_set(account, api_key)
            if success:
                logger.info("Stored %s API key in OS keyring", key_type)
                return True
            else:
                logger.error("Failed to store %s API key in keyring", key_type)
                return False
        else:
            logger.error(
                "Cannot store %s API key: keyring not available. "
                "Set environment variable %s instead.",
                key_type,
                ENV_VAR_NAMES.get(key_type, f'{key_type.upper()}_API_KEY')
            )
            return False

    def remove_api_key(self, key_type: str) -> bool:
        """Remove API key from all storage locations.

        Args:
            key_type: Key type identifier ('openfda', 'linear', 'bridge', 'gemini')

        Returns:
            True if key was removed from at least one location, False otherwise.
        """
        if key_type not in KEYRING_ACCOUNTS:
            raise ValueError(f"Unknown key type: {key_type}. Valid types: {list(KEYRING_ACCOUNTS.keys())}")

        removed_from = []
        account = KEYRING_ACCOUNTS[key_type]

        # Remove from keyring
        if self.keyring_available:
            if _keyring_delete(account):
                removed_from.append("OS keyring")

        # Scrub from settings file
        if _scrub_plaintext_key(key_type):
            removed_from.append("settings file")

        if removed_from:
            logger.info("Removed %s API key from: %s", key_type, ', '.join(removed_from))
            return True
        else:
            logger.warning("No %s API key found to remove", key_type)
            return False

    def migrate_key(self, key_type: str, source: str = 'auto') -> Tuple[bool, str]:
        """Migrate API key from environment or plaintext file to keyring.

        Args:
            key_type: Key type identifier ('openfda', 'linear', 'bridge', 'gemini')
            source: Migration source ('auto', 'env', 'file')

        Returns:
            Tuple of (success: bool, message: str)
        """
        if key_type not in KEYRING_ACCOUNTS:
            return False, f"Unknown key type: {key_type}"

        if not self.keyring_available:
            return False, "Keyring not available on this system"

        account = KEYRING_ACCOUNTS[key_type]

        # Check if already in keyring
        if _keyring_get(account):
            return True, f"{key_type} API key already in keyring"

        # Try environment variable
        if source in ('auto', 'env'):
            env_var = ENV_VAR_NAMES.get(key_type)
            if env_var:
                env_key = os.environ.get(env_var)
                if env_key:
                    if _keyring_set(account, env_key):
                        return True, f"Migrated {key_type} API key from {env_var} to keyring"

        # Try plaintext file
        if source in ('auto', 'file'):
            plaintext_key = _read_plaintext_key(key_type)
            if plaintext_key:
                if _keyring_set(account, plaintext_key):
                    _scrub_plaintext_key(key_type)
                    return True, f"Migrated {key_type} API key from settings file to keyring"

        return False, f"No {key_type} API key found to migrate"

    def migrate_all_keys(self) -> Dict[str, Tuple[bool, str]]:
        """Migrate all supported API keys from environment/file to keyring.

        Returns:
            Dictionary mapping key_type to (success, message) tuples.
        """
        results = {}
        for key_type in KEYRING_ACCOUNTS.keys():
            results[key_type] = self.migrate_key(key_type)
        return results

    def get_key_status(self, key_type: str) -> Dict[str, any]:
        """Get detailed status of an API key across all storage locations.

        Args:
            key_type: Key type identifier ('openfda', 'linear', 'bridge', 'gemini')

        Returns:
            Dictionary with status information.
        """
        if key_type not in KEYRING_ACCOUNTS:
            raise ValueError(f"Unknown key type: {key_type}")

        status = {
            'key_type': key_type,
            'keyring_available': self.keyring_available,
            'env_var_name': ENV_VAR_NAMES.get(key_type),
            'env_var_set': bool(os.environ.get(ENV_VAR_NAMES.get(key_type, ''))),
            'keyring_set': False,
            'plaintext_set': False,
            'active_source': None,
            'masked_value': None,
        }

        # Check keyring
        if self.keyring_available:
            account = KEYRING_ACCOUNTS[key_type]
            kr_key = _keyring_get(account)
            if kr_key:
                status['keyring_set'] = True
                if not status['env_var_set']:
                    status['active_source'] = 'keyring'
                    status['masked_value'] = mask_api_key(kr_key)

        # Check plaintext
        plaintext_key = _read_plaintext_key(key_type)
        if plaintext_key:
            status['plaintext_set'] = True
            if not status['env_var_set'] and not status['keyring_set']:
                status['active_source'] = 'plaintext'
                status['masked_value'] = mask_api_key(plaintext_key)

        # Check environment
        if status['env_var_set']:
            env_key = os.environ.get(ENV_VAR_NAMES.get(key_type, ''))
            status['active_source'] = 'environment'
            status['masked_value'] = mask_api_key(env_key)

        return status

    def get_all_keys_status(self) -> Dict[str, Dict[str, any]]:
        """Get status of all supported API keys.

        Returns:
            Dictionary mapping key_type to status dictionaries.
        """
        return {key_type: self.get_key_status(key_type) for key_type in KEYRING_ACCOUNTS.keys()}

    def health_check(self) -> Dict[str, any]:
        """Run health check on secure config system.

        Returns:
            Dictionary with health status.
        """
        health = {
            'keyring_available': self.keyring_available,
            'keyring_service': KEYRING_SERVICE,
            'supported_keys': list(KEYRING_ACCOUNTS.keys()),
            'settings_file': str(SETTINGS_PATH),
            'settings_file_exists': SETTINGS_PATH.exists(),
            'keys_configured': 0,
            'keys_in_keyring': 0,
            'keys_in_plaintext': 0,
            'keys_in_env': 0,
        }

        for key_type in KEYRING_ACCOUNTS.keys():
            if self.get_api_key(key_type):
                health['keys_configured'] += 1

            status = self.get_key_status(key_type)
            if status['keyring_set']:
                health['keys_in_keyring'] += 1
            if status['plaintext_set']:
                health['keys_in_plaintext'] += 1
            if status['env_var_set']:
                health['keys_in_env'] += 1

        health['healthy'] = health['keyring_available'] or health['keys_in_env'] > 0
        health['warnings'] = []

        if not health['keyring_available']:
            health['warnings'].append("Keyring not available - using environment variables only")
        if health['keys_in_plaintext'] > 0:
            health['warnings'].append(f"{health['keys_in_plaintext']} keys in plaintext - run migrate_all_keys()")

        return health


# ============================================================
# Convenience Functions (backward compatibility)
# ============================================================

_default_config: Optional[SecureConfig] = None


def get_default_config() -> SecureConfig:
    """Get singleton SecureConfig instance.

    Returns:
        Default SecureConfig instance.
    """
    global _default_config
    if _default_config is None:
        _default_config = SecureConfig()
    return _default_config


def get_api_key(key_type: str) -> Optional[str]:
    """Convenience function to get API key using default config.

    Args:
        key_type: Key type identifier ('openfda', 'linear', 'bridge', 'gemini')

    Returns:
        API key if found, None otherwise.
    """
    return get_default_config().get_api_key(key_type)


def set_api_key(key_type: str, api_key: str) -> bool:
    """Convenience function to set API key using default config.

    Args:
        key_type: Key type identifier ('openfda', 'linear', 'bridge', 'gemini')
        api_key: API key value to store

    Returns:
        True on success, False on failure.
    """
    return get_default_config().set_api_key(key_type, api_key)


# ============================================================
# CLI Entry Point
# ============================================================

def main():
    """CLI for managing API keys."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Secure API Key Management (FDA-182 / SEC-003)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show status of all keys
  python3 lib/secure_config.py --status

  # Migrate all keys to keyring
  python3 lib/secure_config.py --migrate-all

  # Migrate specific key
  python3 lib/secure_config.py --migrate openfda

  # Set a key (interactive)
  python3 lib/secure_config.py --set linear

  # Remove a key
  python3 lib/secure_config.py --remove gemini

  # Health check
  python3 lib/secure_config.py --health
        """
    )
    parser.add_argument('--status', action='store_true', help='Show status of all API keys')
    parser.add_argument('--migrate-all', action='store_true', help='Migrate all keys to keyring')
    parser.add_argument('--migrate', metavar='KEY_TYPE', help='Migrate specific key to keyring')
    parser.add_argument('--set', metavar='KEY_TYPE', help='Set API key (interactive)')
    parser.add_argument('--remove', metavar='KEY_TYPE', help='Remove API key')
    parser.add_argument('--health', action='store_true', help='Run health check')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')

    args = parser.parse_args()
    config = SecureConfig()

    if args.status:
        status = config.get_all_keys_status()
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print("=" * 70)
            print("API KEY STATUS")
            print("=" * 70)
            for key_type, info in status.items():
                print(f"\n{key_type.upper()}:")
                print(f"  Environment variable: {info['env_var_name']} ({'SET' if info['env_var_set'] else 'not set'})")
                print(f"  Keyring: {'SET' if info['keyring_set'] else 'not set'}")
                print(f"  Plaintext file: {'SET (migrate!)' if info['plaintext_set'] else 'not set'}")
                print(f"  Active source: {info['active_source'] or 'NONE'}")
                if info['masked_value']:
                    print(f"  Value: {info['masked_value']}")

    elif args.migrate_all:
        results = config.migrate_all_keys()
        if args.json:
            print(json.dumps({k: {'success': v[0], 'message': v[1]} for k, v in results.items()}, indent=2))
        else:
            print("=" * 70)
            print("MIGRATION RESULTS")
            print("=" * 70)
            for key_type, (success, message) in results.items():
                status = "✓" if success else "✗"
                print(f"{status} {key_type}: {message}")

    elif args.migrate:
        success, message = config.migrate_key(args.migrate)
        if args.json:
            print(json.dumps({'success': success, 'message': message}, indent=2))
        else:
            status = "✓" if success else "✗"
            print(f"{status} {message}")

    elif args.set:
        if args.set not in KEYRING_ACCOUNTS:
            print(f"Error: Unknown key type '{args.set}'. Valid types: {list(KEYRING_ACCOUNTS.keys())}")
            return 1

        print(f"Setting {args.set.upper()} API key")
        print(f"Current status: {config.get_key_status(args.set)['active_source'] or 'not set'}")
        print()

        import getpass
        api_key = getpass.getpass(f"Enter {args.set.upper()} API key (input hidden): ").strip()
        if not api_key:
            print("Cancelled.")
            return 0

        if config.set_api_key(args.set, api_key):
            print(f"✓ {args.set.upper()} API key stored in keyring")
        else:
            print(f"✗ Failed to store {args.set.upper()} API key")
            return 1

    elif args.remove:
        if config.remove_api_key(args.remove):
            print(f"✓ Removed {args.remove.upper()} API key")
        else:
            print(f"✗ Failed to remove {args.remove.upper()} API key")
            return 1

    elif args.health:
        health = config.health_check()
        if args.json:
            print(json.dumps(health, indent=2))
        else:
            print("=" * 70)
            print("SECURE CONFIG HEALTH CHECK")
            print("=" * 70)
            print(f"Keyring available: {'YES' if health['keyring_available'] else 'NO'}")
            print(f"Keyring service: {health['keyring_service']}")
            print(f"Settings file: {health['settings_file']} ({'exists' if health['settings_file_exists'] else 'not found'})")
            print(f"\nSupported keys: {', '.join(health['supported_keys'])}")
            print(f"Keys configured: {health['keys_configured']}")
            print(f"Keys in keyring: {health['keys_in_keyring']}")
            print(f"Keys in environment: {health['keys_in_env']}")
            print(f"Keys in plaintext: {health['keys_in_plaintext']}")
            print(f"\nOverall status: {'HEALTHY' if health['healthy'] else 'UNHEALTHY'}")
            if health['warnings']:
                print("\nWarnings:")
                for warning in health['warnings']:
                    print(f"  ! {warning}")

    else:
        parser.print_help()
        return 0

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
