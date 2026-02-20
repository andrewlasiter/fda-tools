# Secure API Keys - Quick Reference

**Security Feature:** FDA-182 / SEC-003
**Status:** ✅ Production Ready

## TL;DR

API keys are now stored securely in OS keyring instead of plaintext files.

```bash
# Migrate your keys (ONE command)
python3 scripts/migrate_to_keyring.py --auto

# Check status
python3 lib/secure_config.py --status
```

**That's it!** Your existing code continues to work unchanged.

---

## For End Users

### First-Time Setup

```bash
# 1. Check if keyring is available
python3 lib/secure_config.py --health

# 2. Migrate keys from environment/files to keyring
python3 scripts/migrate_to_keyring.py --auto

# 3. Verify migration
python3 lib/secure_config.py --status
```

### Add New API Key

```bash
# Interactive (recommended - hides input)
python3 lib/secure_config.py --set openfda

# Or use migration script
python3 scripts/migrate_to_keyring.py --key linear
```

### Remove API Key

```bash
python3 lib/secure_config.py --remove gemini
```

### Check What Keys Are Configured

```bash
python3 lib/secure_config.py --status
```

---

## For Developers

### Use in Your Code

**Before (plaintext):**
```python
import os
api_key = os.getenv("LINEAR_API_KEY")
```

**After (secure keyring with fallback):**
```python
import os
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

# Try keyring, fallback to env
try:
    from secure_config import get_api_key
    api_key = get_api_key('linear')
except ImportError:
    api_key = os.getenv("LINEAR_API_KEY")
```

### Supported Key Types

| Key Type | Environment Variable | Purpose |
|----------|---------------------|---------|
| `openfda` | `OPENFDA_API_KEY` | FDA API access |
| `linear` | `LINEAR_API_KEY` | Linear issues |
| `bridge` | `BRIDGE_API_KEY` | Bridge server |
| `gemini` | `GEMINI_API_KEY` | Gemini AI |

### Resolution Order

API keys are resolved in this priority:

1. **Environment Variable** (highest - always works)
2. **OS Keyring** (secure storage)
3. **Legacy File** (auto-migrates on first read)

### API Reference

```python
from lib.secure_config import SecureConfig

config = SecureConfig()

# Get API key
key = config.get_api_key('openfda')

# Set API key
config.set_api_key('linear', 'your-key-here')

# Remove API key
config.remove_api_key('bridge')

# Migrate key
success, msg = config.migrate_key('gemini')

# Get status
status = config.get_key_status('openfda')

# Health check
health = config.health_check()
```

---

## Platform-Specific Notes

### Linux

**Install keyring backend:**
```bash
sudo apt install gnome-keyring libsecret-1-0  # Ubuntu/Debian
sudo dnf install gnome-keyring libsecret      # RHEL/Fedora
```

**Headless servers:** Use environment variables (keyring unavailable without GUI)

### macOS

Keychain is built-in. No installation needed.

### Windows

Credential Locker is built-in. No installation needed.

### CI/CD (GitHub Actions, GitLab CI)

Keyring not available. Use environment variables:

```yaml
env:
  OPENFDA_API_KEY: ${{ secrets.OPENFDA_API_KEY }}
  LINEAR_API_KEY: ${{ secrets.LINEAR_API_KEY }}
```

---

## Troubleshooting

### Keyring Not Available

**Symptom:** `Keyring not available on this system`

**Solution:**
```bash
# Linux: Install keyring backend
sudo apt install gnome-keyring

# Or use environment variables
export OPENFDA_API_KEY="your-key"
```

### Key Not Found After Migration

**Symptom:** Application can't find key

**Solution:**
```bash
# Check status
python3 lib/secure_config.py --status

# If key not in keyring, set manually
python3 lib/secure_config.py --set openfda
```

### Migration Failed

**Symptom:** `Migration failed` error

**Solution:**
```bash
# Check health
python3 lib/secure_config.py --health

# If keyring unavailable, use env vars
export OPENFDA_API_KEY="your-key"
```

---

## Commands Cheat Sheet

```bash
# STATUS & HEALTH
python3 lib/secure_config.py --status          # Show all keys
python3 lib/secure_config.py --health          # Health check
python3 scripts/migrate_to_keyring.py --status # Migration status

# MIGRATION
python3 scripts/migrate_to_keyring.py --auto   # Auto-migrate all
python3 scripts/migrate_to_keyring.py --key openfda  # Migrate one
python3 scripts/migrate_to_keyring.py          # Interactive

# KEY MANAGEMENT
python3 lib/secure_config.py --set linear      # Add/update key
python3 lib/secure_config.py --remove gemini   # Remove key

# ROLLBACK
python3 scripts/migrate_to_keyring.py --rollback  # Export to .env.backup
```

---

## Security Best Practices

✅ **DO:**
- Use keyring for local development
- Use environment variables for CI/CD
- Rotate keys regularly
- Run health checks monthly

❌ **DON'T:**
- Commit `.env` files to Git
- Store keys in plaintext files
- Share keys via email/chat
- Mix keyring and plaintext storage

---

## FAQ

**Q: Do I need to change my code?**
A: No. Environment variables still work. Keyring is optional but recommended.

**Q: What if keyring is unavailable?**
A: Code automatically falls back to environment variables.

**Q: Can I migrate later?**
A: Yes. Migration is optional and can be done anytime.

**Q: Will this break my existing setup?**
A: No. 100% backward compatible.

**Q: How do I rollback?**
A: `python3 scripts/migrate_to_keyring.py --rollback`

---

## Documentation

- **Full Migration Guide:** `KEYRING_MIGRATION_GUIDE.md`
- **Implementation Details:** `IMPLEMENTATION_SUMMARY_FDA-182.md`
- **Module Documentation:** `lib/secure_config.py` (docstrings)
- **Tests:** `tests/test_secure_config.py`

---

## Support

**Health Check:**
```bash
python3 lib/secure_config.py --health
```

**Status Check:**
```bash
python3 lib/secure_config.py --status
```

**Test Suite:**
```bash
python3 tests/test_secure_config.py
```

---

**Last Updated:** 2026-02-20
**Status:** ✅ Production Ready
**Breaking Changes:** None
