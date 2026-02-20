# API Key Migration to Secure Keyring Storage

**Security Upgrade:** FDA-182 / SEC-003
**Status:** Production Ready
**Platform Support:** Linux, macOS, Windows

## Overview

This guide helps you migrate API keys from plaintext storage (environment variables, `.env` files, settings files) to secure OS keyring storage.

### Security Benefits

- ✅ **Encrypted Storage**: API keys encrypted by OS keyring (macOS Keychain, Windows Credential Locker, Linux Secret Service)
- ✅ **No Plaintext Files**: Eliminates `.env` files and plaintext settings
- ✅ **Cross-Platform**: Works on Linux, macOS, and Windows
- ✅ **Automatic Redaction**: API keys automatically masked in logs
- ✅ **Backward Compatible**: Existing code continues to work during migration

### Supported API Keys

| Key Type | Environment Variable | Purpose |
|----------|---------------------|---------|
| `openfda` | `OPENFDA_API_KEY` | openFDA API access |
| `linear` | `LINEAR_API_KEY` | Linear issue management |
| `bridge` | `BRIDGE_API_KEY` | OpenClaw bridge server authentication |
| `gemini` | `GEMINI_API_KEY` | Google Gemini AI API |

## Prerequisites

### Linux

Install keyring backend (choose one):

```bash
# Ubuntu/Debian
sudo apt install gnome-keyring libsecret-1-0

# RHEL/CentOS/Fedora
sudo dnf install gnome-keyring libsecret

# Arch Linux
sudo pacman -S gnome-keyring libsecret
```

### macOS

Keychain is built-in. No installation needed.

### Windows

Credential Locker is built-in. No installation needed.

## Migration Steps

### Step 1: Check Current Status

```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools
python3 scripts/migrate_to_keyring.py --status
```

**Expected Output:**
```
MIGRATION STATUS
======================================================================

Keyring available: YES
Total supported keys: 4
Keys in keyring: 0
Keys in environment: 2
Keys in plaintext files: 1

DETAILED STATUS:

  OPENFDA:
    Environment (OPENFDA_API_KEY): SET
    Keyring: not set
    Plaintext file: not set
    Active source: environment

  LINEAR:
    Environment (LINEAR_API_KEY): SET
    Keyring: not set
    Plaintext file: not set
    Active source: environment

RECOMMENDATIONS:
  - Migrate OPENFDA from environment to keyring
  - Migrate LINEAR from environment to keyring

  Run: python3 scripts/migrate_to_keyring.py --auto
```

### Step 2: Auto-Migration (Recommended)

Automatically migrate all keys from environment variables and settings files to keyring:

```bash
python3 scripts/migrate_to_keyring.py --auto
```

**Expected Output:**
```
AUTO-MIGRATION
======================================================================
  OPENFDA: ✓ Migrated from environment
  LINEAR: ✓ Migrated from environment
  BRIDGE: No key found, skipping
  GEMINI: No key found, skipping

======================================================================
MIGRATION COMPLETE
======================================================================
  Migrated: 2
  Skipped:  2
  Failed:   0

✓ 2 keys migrated to secure keyring storage

Next steps:
1. Test your applications to ensure they can access keys
2. Remove API keys from environment variables (unset)
3. Delete any .env files containing API keys

To rollback: python3 scripts/migrate_to_keyring.py --rollback
```

### Step 3: Verify Migration

Test that applications can access keys from keyring:

```bash
# Test openFDA key
python3 scripts/fda_api_client.py --stats

# Test secure config directly
python3 lib/secure_config.py --status
```

### Step 4: Clean Up Plaintext Storage

After successful verification, remove plaintext API keys:

```bash
# Remove from environment (add to ~/.bashrc or ~/.zshrc)
unset OPENFDA_API_KEY
unset LINEAR_API_KEY
unset GEMINI_API_KEY
unset BRIDGE_API_KEY

# Remove .env files (if present)
rm -f .env .env.local

# Legacy settings file is automatically scrubbed during migration
```

### Step 5: Update Shell Configuration

Remove API key exports from shell configuration files:

```bash
# Edit your shell config
nano ~/.bashrc  # or ~/.zshrc

# Remove lines like:
# export OPENFDA_API_KEY="..."
# export LINEAR_API_KEY="..."

# Reload shell
source ~/.bashrc  # or source ~/.zshrc
```

## Alternative Migration Methods

### Interactive Migration

For more control, use interactive mode:

```bash
python3 scripts/migrate_to_keyring.py
```

Follow the prompts to migrate keys one at a time.

### Migrate Specific Key

Migrate a single API key:

```bash
python3 scripts/migrate_to_keyring.py --key openfda
```

### Manual Key Entry

Set a key manually (interactive, hidden input):

```bash
python3 lib/secure_config.py --set linear
```

## Rollback Procedure

If you encounter issues, you can rollback by exporting keys to a backup file:

```bash
# Export keys from keyring to .env.backup
python3 scripts/migrate_to_keyring.py --rollback

# Load keys into environment
source .env.backup

# Or manually set environment variables
export OPENFDA_API_KEY=$(grep OPENFDA_API_KEY .env.backup | cut -d= -f2)
export LINEAR_API_KEY=$(grep LINEAR_API_KEY .env.backup | cut -d= -f2)

# IMPORTANT: Delete .env.backup after rollback
rm .env.backup
```

## Code Changes

### No Changes Required for Most Scripts

The migration is **backward compatible**. Most scripts automatically use the new keyring system through updated imports:

- `scripts/fda_api_client.py` - ✅ Updated
- `scripts/linear_integrator.py` - ✅ Updated
- `scripts/create_linear_issues_from_manifest.py` - ✅ Updated
- `scripts/setup_api_key.py` - ✅ Already used keyring

### For Custom Scripts

If you have custom scripts that load API keys, update them to use `secure_config`:

**Before (plaintext):**
```python
import os
api_key = os.getenv("LINEAR_API_KEY")
```

**After (keyring-based):**
```python
import os
import sys
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

# Try keyring first, fallback to environment
try:
    from secure_config import get_api_key
    api_key = get_api_key('linear')
except ImportError:
    api_key = os.getenv("LINEAR_API_KEY")
```

## Troubleshooting

### Keyring Not Available

**Problem:** `Keyring not available on this system`

**Solution (Linux):**
```bash
# Install keyring backend
sudo apt install gnome-keyring libsecret-1-0

# If using headless server, use environment variables instead
export OPENFDA_API_KEY="your-key"
```

**Solution (macOS/Windows):**
Keyring should be built-in. If unavailable, use environment variables.

### Permission Denied

**Problem:** `Permission denied when accessing keyring`

**Solution:**
```bash
# Linux: Ensure gnome-keyring daemon is running
ps aux | grep gnome-keyring

# Start if not running (usually auto-started with desktop session)
gnome-keyring-daemon --start --components=secrets

# macOS: Keychain Access may need authorization
# Open Keychain Access app and grant permissions
```

### Key Not Found After Migration

**Problem:** Application can't find key after migration

**Solution:**
```bash
# Verify key is in keyring
python3 lib/secure_config.py --status

# Check application is using updated code
python3 -c "from lib.secure_config import get_api_key; print(get_api_key('openfda'))"

# If still failing, set environment variable temporarily
export OPENFDA_API_KEY="your-key"
```

### Migration Failed

**Problem:** `Migration failed` error

**Solution:**
```bash
# Check keyring availability
python3 lib/secure_config.py --health

# Manually set key
python3 lib/secure_config.py --set openfda

# Enter key when prompted (input is hidden)
```

## Security Best Practices

### After Migration

1. ✅ **Remove plaintext files**: Delete `.env`, `.env.local`, and any files containing API keys
2. ✅ **Clear shell history**: Remove API key exports from shell history
3. ✅ **Update documentation**: Remove API key references from documentation
4. ✅ **Verify `.gitignore`**: Ensure `.env*` and backup files are excluded

### Ongoing

1. ✅ **Use keyring for all keys**: Don't mix keyring and plaintext storage
2. ✅ **Rotate keys periodically**: Update keys in keyring when rotating
3. ✅ **Monitor logs**: API keys are automatically redacted in logs
4. ✅ **Use environment variables for CI/CD**: Keyring not available in CI pipelines

## Testing

Run the comprehensive test suite:

```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools
python3 tests/test_secure_config.py
```

**Expected Output:**
```
test_all_key_types ... ok
test_env_overrides_keyring ... ok
test_get_api_key_from_env ... ok
test_get_api_key_from_keyring ... ok
test_health_check ... ok
test_mask_long_key ... ok
test_migrate_from_env ... ok
test_set_api_key ... ok
...

----------------------------------------------------------------------
Ran 25 tests in 0.123s

OK
```

## CI/CD Integration

Keyring is not available in most CI/CD environments (GitHub Actions, GitLab CI, etc.). Use environment variables for CI:

### GitHub Actions

```yaml
# .github/workflows/test.yml
env:
  OPENFDA_API_KEY: ${{ secrets.OPENFDA_API_KEY }}
  LINEAR_API_KEY: ${{ secrets.LINEAR_API_KEY }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: python3 tests/test_secure_config.py
```

### GitLab CI

```yaml
# .gitlab-ci.yml
variables:
  OPENFDA_API_KEY: $OPENFDA_API_KEY
  LINEAR_API_KEY: $LINEAR_API_KEY

test:
  script:
    - python3 tests/test_secure_config.py
```

## Resolution Order

API keys are resolved in this priority order:

1. **Environment Variable** (highest priority) - `OPENFDA_API_KEY`, `LINEAR_API_KEY`, etc.
2. **OS Keyring** - Secure encrypted storage
3. **Legacy Plaintext File** - `~/.claude/fda-tools.local.md` (auto-migrates on first read)

This ensures:
- Environment variables work for CI/CD
- Keyring is used for local development
- Automatic migration for legacy installations

## Health Check

Run a comprehensive health check:

```bash
python3 lib/secure_config.py --health
```

**Expected Output:**
```
SECURE CONFIG HEALTH CHECK
======================================================================
Keyring available: YES
Keyring service: fda-tools-plugin
Settings file: /home/linux/.claude/fda-tools.local.md (exists)

Supported keys: openfda, linear, bridge, gemini
Keys configured: 2
Keys in keyring: 2
Keys in environment: 0
Keys in plaintext: 0

Overall status: HEALTHY
```

## Support

For issues or questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Run health check: `python3 lib/secure_config.py --health`
3. Check status: `python3 scripts/migrate_to_keyring.py --status`
4. Review test results: `python3 tests/test_secure_config.py`

## Related Documentation

- FDA-182: Security issue ticket
- SEC-003: Security requirement specification
- `lib/secure_config.py`: Implementation documentation
- `tests/test_secure_config.py`: Test coverage

## Summary

The keyring migration provides enterprise-grade security for API keys without breaking existing workflows. The migration is:

- ✅ **Automatic**: One-command migration
- ✅ **Backward Compatible**: Existing code works unchanged
- ✅ **Reversible**: Rollback available if needed
- ✅ **Cross-Platform**: Linux, macOS, Windows support
- ✅ **Well-Tested**: Comprehensive test coverage

**Recommended Timeline:**
- Day 1: Run status check and auto-migration
- Day 2-3: Verify all applications work with keyring
- Day 4: Clean up plaintext storage
- Ongoing: Use keyring for all new API keys
