#!/usr/bin/env python3
"""
Securely configure the openFDA API key for the FDA Predicate Assistant plugin.

Run this script OUTSIDE of Claude (in your terminal) so the key never
appears in conversation history.

Usage:
    python3 setup_api_key.py
    python3 setup_api_key.py --check
    python3 setup_api_key.py --remove
"""
import os
import re
import sys
import urllib.request
import urllib.parse
import json

SETTINGS_PATH = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')

SETTINGS_TEMPLATE = """# FDA Predicate Assistant - Local Settings
# This file is NOT checked into git. It stores user-specific configuration.
# Edit paths below to match your local environment, then restart your session.

openfda_api_key: {api_key}
openfda_enabled: true
"""


def get_current_key():
    """Read the current API key from settings file (if any)."""
    if not os.path.exists(SETTINGS_PATH):
        return None
    with open(SETTINGS_PATH) as f:
        content = f.read()
    m = re.search(r'openfda_api_key:\s*(\S+)', content)
    if m and m.group(1) != 'null':
        return m.group(1)
    return None


def test_key(api_key):
    """Test the API key against the openFDA 510k endpoint."""
    params = {"search": 'k_number:"K241335"', "limit": "1"}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            if data.get("results"):
                return True, "Key is valid — 120K requests/day"
            return True, "Key accepted (no results for test query, but API responded)"
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return False, "Invalid API key (HTTP 403 Forbidden)"
        return False, f"API error: HTTP {e.code}"
    except Exception as e:
        return False, f"Connection error: {e}"


def set_key(api_key):
    """Write the API key to the settings file."""
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH) as f:
            content = f.read()
        # Replace existing key
        content = re.sub(
            r'openfda_api_key:\s*\S+',
            f'openfda_api_key: {api_key}',
            content
        )
        with open(SETTINGS_PATH, 'w') as f:
            f.write(content)
    else:
        # Create settings file from template
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, 'w') as f:
            f.write(SETTINGS_TEMPLATE.format(api_key=api_key))


def remove_key():
    """Remove the API key from the settings file."""
    if not os.path.exists(SETTINGS_PATH):
        print("No settings file found — nothing to remove.")
        return
    with open(SETTINGS_PATH) as f:
        content = f.read()
    content = re.sub(
        r'openfda_api_key:\s*\S+',
        'openfda_api_key: null',
        content
    )
    with open(SETTINGS_PATH, 'w') as f:
        f.write(content)
    print("API key removed from settings file.")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        env_key = os.environ.get('OPENFDA_API_KEY')
        file_key = get_current_key()
        if env_key:
            print(f"Environment variable: {env_key[:4]}...{env_key[-4:]} (active)")
        else:
            print("Environment variable: not set")
        if file_key:
            print(f"Settings file:       {file_key[:4]}...{file_key[-4:]}")
        else:
            print("Settings file:       not set")
        active = env_key or file_key
        if active:
            ok, msg = test_key(active)
            print(f"Validation:          {'PASS' if ok else 'FAIL'} — {msg}")
        else:
            print("No API key configured. Run this script without --check to set one.")
        return

    if len(sys.argv) > 1 and sys.argv[1] == '--remove':
        remove_key()
        return

    print("=" * 60)
    print("  openFDA API Key Setup")
    print("=" * 60)
    print()
    print("This script stores your API key in the settings file at:")
    print(f"  {SETTINGS_PATH}")
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
    print(f"Key saved to {SETTINGS_PATH}")
    print()
    print("Alternatively, you can set the environment variable (takes priority):")
    print(f'  export OPENFDA_API_KEY="{api_key}"')
    print()
    print("Done!")


if __name__ == '__main__':
    main()
