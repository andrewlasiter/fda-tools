#!/usr/bin/env python3
"""
Securely configure the openFDA API key for the FDA Predicate Assistant plugin.

Run this script OUTSIDE of Claude (in your terminal) so the key never
appears in conversation history.

Storage: Uses OS keyring (macOS Keychain, Windows Credential Locker,
Linux Secret Service / libsecret) via the `keyring` library.
Falls back to settings file with restricted permissions if keyring is unavailable
(e.g., headless servers).

Usage:
    python3 setup_api_key.py
    python3 setup_api_key.py --check
    python3 setup_api_key.py --remove
    python3 setup_api_key.py --migrate   # Migrate plaintext key to keyring
"""
import os
import re
import ssl
import stat
import sys
import urllib.request
import urllib.parse
import urllib.error
import json
import logging

logger = logging.getLogger(__name__)


# ============================================================
# API Key Redaction (FDA-84)
# ============================================================

# Pattern matching strings that look like API keys (20+ alphanumeric chars)
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

    Usage:
        Apply to logging handlers to automatically redact keys:
            for handler in logging.root.handlers:
                handler.addFilter(APIKeyRedactor())
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

# Keyring service and account identifiers
KEYRING_SERVICE = 'fda-tools-plugin'
KEYRING_ACCOUNT_OPENFDA = 'openfda_api_key'
KEYRING_ACCOUNT_BRIDGE = 'bridge_api_key'

# Legacy settings path (used before keyring migration)
SETTINGS_PATH = os.path.expanduser('~/.claude/fda-tools.local.md')

SETTINGS_TEMPLATE = """# FDA Predicate Assistant - Local Settings
# This file is NOT checked into git. It stores user-specific configuration.
# Edit paths below to match your local environment, then restart your session.
# NOTE: API key is stored in OS keyring. Set openfda_api_key to 'keyring'
# to indicate keyring-based storage.

openfda_api_key: keyring
openfda_enabled: true
"""

# ============================================================
# Keyring Backend
# ============================================================

_keyring_available = None


def _is_keyring_available():
    """Check if the keyring library is available and functional."""
    global _keyring_available
    if _keyring_available is not None:
        return _keyring_available
    try:
        import keyring as kr
        # Attempt a read to verify backend works (e.g., not a headless chroot)
        kr.get_password(KEYRING_SERVICE, '__probe__')
        _keyring_available = True
    except Exception:
        _keyring_available = False
    return _keyring_available


def _keyring_set(account: str, secret: str) -> bool:
    """Store a secret in OS keyring. Returns True on success."""
    try:
        import keyring as kr
        kr.set_password(KEYRING_SERVICE, account, secret)
        return True
    except Exception as e:
        logger.warning("Keyring write failed: %s", e)
        return False


def _keyring_get(account: str):
    """Retrieve a secret from OS keyring. Returns None if not found."""
    try:
        import keyring as kr
        return kr.get_password(KEYRING_SERVICE, account)
    except Exception:
        return None


def _keyring_delete(account: str) -> bool:
    """Delete a secret from OS keyring. Returns True on success."""
    try:
        import keyring as kr
        kr.delete_password(KEYRING_SERVICE, account)
        return True
    except Exception:
        return False


# ============================================================
# Legacy Plaintext Helpers (for migration only)
# ============================================================

def _read_plaintext_key():
    """Read API key from legacy plaintext settings file (if present)."""
    if not os.path.exists(SETTINGS_PATH):
        return None
    try:
        with open(SETTINGS_PATH) as f:
            content = f.read()
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) not in ('null', 'keyring'):
            return m.group(1)
    except Exception:
        pass
    return None


def _scrub_plaintext_key():
    """Remove plaintext API key from settings file, replacing with 'keyring' marker."""
    if not os.path.exists(SETTINGS_PATH):
        return
    try:
        with open(SETTINGS_PATH) as f:
            content = f.read()
        new_content = re.sub(
            r'openfda_api_key:\s*\S+',
            'openfda_api_key: keyring',
            content
        )
        with open(SETTINGS_PATH, 'w') as f:
            f.write(new_content)
        # Restrict file permissions (owner read/write only)
        os.chmod(SETTINGS_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except Exception as e:
        logger.warning("Failed to scrub plaintext key: %s", e)


# ============================================================
# Public API
# ============================================================

def get_current_key():
    """Read the current openFDA API key.

    Resolution order:
    1. OPENFDA_API_KEY environment variable
    2. OS keyring
    3. Legacy plaintext settings file (triggers auto-migration)
    """
    # 1. Environment variable takes priority
    env_key = os.environ.get('OPENFDA_API_KEY')
    if env_key:
        return env_key

    # 2. OS keyring
    if _is_keyring_available():
        kr_key = _keyring_get(KEYRING_ACCOUNT_OPENFDA)
        if kr_key:
            return kr_key

    # 3. Legacy plaintext (auto-migrate if found)
    plaintext_key = _read_plaintext_key()
    if plaintext_key:
        # Auto-migrate to keyring on first read
        if _is_keyring_available():
            if _keyring_set(KEYRING_ACCOUNT_OPENFDA, plaintext_key):
                _scrub_plaintext_key()
                logger.info("Auto-migrated API key from plaintext to OS keyring.")
        return plaintext_key

    return None


def get_bridge_key():
    """Read the bridge API key from OS keyring."""
    if _is_keyring_available():
        return _keyring_get(KEYRING_ACCOUNT_BRIDGE)
    return None


def set_bridge_key(api_key: str) -> bool:
    """Store the bridge API key in OS keyring."""
    if _is_keyring_available():
        return _keyring_set(KEYRING_ACCOUNT_BRIDGE, api_key)
    return False


def test_key(api_key):
    """Test the API key against the openFDA 510k endpoint."""
    params = {"search": 'k_number:"K241335"', "limit": "1"}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})

    # FDA-107: Create SSL context with certificate verification enabled
    ssl_context = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_context) as resp:
            data = json.loads(resp.read())
            if data.get("results"):
                return True, "Key is valid -- 120K requests/day"
            return True, "Key accepted (no results for test query, but API responded)"
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return False, "Invalid API key (HTTP 403 Forbidden)"
        return False, f"API error: HTTP {e.code}"
    except Exception as e:
        return False, f"Connection error: {e}"


def set_key(api_key):
    """Store the openFDA API key securely.

    Prefers OS keyring. Falls back to restricted-permission file.
    """
    if _is_keyring_available():
        if _keyring_set(KEYRING_ACCOUNT_OPENFDA, api_key):
            # Update settings file to indicate keyring storage
            _update_settings_marker()
            return

    # Fallback: write to settings file with restricted permissions
    _write_settings_file(api_key)


def _update_settings_marker():
    """Update settings file to show 'keyring' marker instead of actual key."""
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH) as f:
            content = f.read()
        content = re.sub(
            r'openfda_api_key:\s*\S+',
            'openfda_api_key: keyring',
            content
        )
        with open(SETTINGS_PATH, 'w') as f:
            f.write(content)
        os.chmod(SETTINGS_PATH, stat.S_IRUSR | stat.S_IWUSR)
    else:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, 'w') as f:
            f.write(SETTINGS_TEMPLATE)
        os.chmod(SETTINGS_PATH, stat.S_IRUSR | stat.S_IWUSR)


def _write_settings_file(api_key):
    """Write API key to settings file (fallback when keyring unavailable)."""
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH) as f:
            content = f.read()
        content = re.sub(
            r'openfda_api_key:\s*\S+',
            f'openfda_api_key: {api_key}',
            content
        )
        with open(SETTINGS_PATH, 'w') as f:
            f.write(content)
    else:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, 'w') as f:
            f.write(SETTINGS_TEMPLATE.replace('openfda_api_key: keyring',
                                               f'openfda_api_key: {api_key}'))
    # Restrict file permissions (owner read/write only)
    os.chmod(SETTINGS_PATH, stat.S_IRUSR | stat.S_IWUSR)


def remove_key():
    """Remove the openFDA API key from all storage locations."""
    removed_from = []

    # Remove from keyring
    if _is_keyring_available():
        if _keyring_delete(KEYRING_ACCOUNT_OPENFDA):
            removed_from.append("OS keyring")

    # Scrub from settings file
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH) as f:
            content = f.read()
        content = re.sub(
            r'openfda_api_key:\s*\S+',
            'openfda_api_key: null',
            content
        )
        with open(SETTINGS_PATH, 'w') as f:
            f.write(content)
        removed_from.append("settings file")

    if removed_from:
        print(f"API key removed from: {', '.join(removed_from)}")
    else:
        print("No API key found to remove.")


def migrate_to_keyring():
    """Explicitly migrate a plaintext API key to OS keyring.

    Returns:
        True if migration succeeded, False otherwise.
    """
    if not _is_keyring_available():
        print("ERROR: OS keyring is not available on this system.")
        print("Install a keyring backend:")
        print("  Linux: sudo apt install gnome-keyring (or libsecret)")
        print("  macOS: Keychain is built-in")
        print("  Windows: Credential Locker is built-in")
        return False

    plaintext_key = _read_plaintext_key()
    if not plaintext_key:
        # Check if already in keyring
        kr_key = _keyring_get(KEYRING_ACCOUNT_OPENFDA)
        if kr_key:
            print("API key is already stored in OS keyring. Nothing to migrate.")
            return True
        print("No plaintext API key found to migrate.")
        return False

    if _keyring_set(KEYRING_ACCOUNT_OPENFDA, plaintext_key):
        _scrub_plaintext_key()
        print("SUCCESS: API key migrated from plaintext to OS keyring.")
        print(f"Settings file updated: {SETTINGS_PATH}")
        print("Plaintext key has been scrubbed from the settings file.")
        return True
    else:
        print("ERROR: Failed to write to OS keyring.")
        return False


# ============================================================
# CLI Entry Point
# ============================================================

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        env_key = os.environ.get('OPENFDA_API_KEY')
        kr_key = _keyring_get(KEYRING_ACCOUNT_OPENFDA) if _is_keyring_available() else None
        file_key = _read_plaintext_key()

        print(f"Keyring available:   {'YES' if _is_keyring_available() else 'NO'}")

        if env_key:
            print(f"Environment variable: {env_key[:4]}...{env_key[-4:]} (active, highest priority)")
        else:
            print("Environment variable: not set")

        if kr_key:
            print(f"OS keyring:          {kr_key[:4]}...{kr_key[-4:]} (secure)")
        else:
            print("OS keyring:          not set")

        if file_key:
            print(f"Settings file:       {file_key[:4]}...{file_key[-4:]} (PLAINTEXT - run --migrate)")
        else:
            pt_marker = None
            if os.path.exists(SETTINGS_PATH):
                with open(SETTINGS_PATH) as f:
                    m = re.search(r'openfda_api_key:\s*(\S+)', f.read())
                    if m:
                        pt_marker = m.group(1)
            if pt_marker == 'keyring':
                print("Settings file:       references keyring (secure)")
            else:
                print("Settings file:       not set")

        active = env_key or kr_key or file_key
        if active:
            ok, msg = test_key(active)
            print(f"Validation:          {'PASS' if ok else 'FAIL'} -- {msg}")
        else:
            print("No API key configured. Run this script without --check to set one.")
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--remove':
        remove_key()
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--migrate':
        migrate_to_keyring()
        return

    print("=" * 60)
    print("  openFDA API Key Setup (Secure Storage)")
    print("=" * 60)
    print()
    if _is_keyring_available():
        print("Storage: OS keyring (macOS Keychain / Windows Credential Locker / Linux Secret Service)")
    else:
        print("Storage: Settings file (keyring not available)")
        print("WARNING: Key will be stored with restricted file permissions.")
        print("         Install a keyring backend for stronger security.")
    print()
    print("Get a free key at: https://open.fda.gov/apis/authentication/")
    print("Without a key: 1,000 requests/day")
    print("With a key:    120,000 requests/day")
    print()

    current = get_current_key()
    if current:
        print(f"Current key: {current[:4]}...{current[-4:]}")
        print()

    api_key = input("Paste your openFDA API key (or press Enter to cancel): ").strip()
    if not api_key:
        print("Cancelled.")
        return

    print()
    print("Testing key...", end=" ", flush=True)
    ok, msg = test_key(api_key)
    print(msg)

    if not ok:
        confirm = input("Key validation failed. Save anyway? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return

    set_key(api_key)
    print()
    if _is_keyring_available():
        print("Key saved to OS keyring (secure).")
    else:
        print(f"Key saved to {SETTINGS_PATH} (restricted permissions).")
    print()
    print("Alternatively, you can set the environment variable (takes priority):")
    print(f'  export OPENFDA_API_KEY="{mask_api_key(api_key)}"')
    print("  (Use the full key you entered above -- masked here for security)")
    print()
    print("Done!")


if __name__ == '__main__':
    main()
