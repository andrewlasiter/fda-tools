# FDA-37: Plugin Rename Migration Guide

## Breaking Change: fda-predicate-assistant → fda-tools

**Effective Date:** 2026-02-17
**Version:** 5.37.0+
**Impact:** 109 files updated, 337 references replaced

---

## What Changed

| Component | Before | After |
|-----------|--------|-------|
| **Plugin Name** | `fda-predicate-assistant` | `fda-tools` |
| **Namespace** | `fda-predicate-assistant@fda-tools` | `fda-tools@fda-tools` |
| **Command Prefix** | `/fda-predicate-assistant:*` | `/fda-tools:*` |
| **Repository** | `andrewlasiter/fda-predicate-assistant` | `andrewlasiter/fda-tools` |
| **Settings File** | `~/.claude/fda-predicate-assistant.local.md` | `~/.claude/fda-tools.local.md` |

---

## Why This Change?

1. **Namespace Simplification**: Reduces confusion with cleaner naming
2. **Reflects Comprehensive Scope**: The plugin now offers 64+ commands covering:
   - 510(k) predicate analysis
   - PMA intelligence and comparison
   - Pre-Submission (eSTAR/PreSTAR) generation
   - Real-time FDA approval monitoring
   - MAUDE safety signal detection
   - Clinical data extraction
   - Regulatory pathway recommendations
   - Advanced ML analytics
3. **Marketplace Alignment**: Plugin directory already named `fda-tools` in marketplace
4. **User Clarity**: Simpler, clearer naming for all command invocations

---

## Migration Steps

### 1. Backup Your Configuration

```bash
# Backup existing settings (if they exist)
if [ -f ~/.claude/fda-predicate-assistant.local.md ]; then
  cp ~/.claude/fda-predicate-assistant.local.md ~/.claude/fda-predicate-assistant.local.md.backup
  echo "✓ Settings backed up"
fi
```

### 2. Migrate Settings File

```bash
# Rename settings file (if it exists)
if [ -f ~/.claude/fda-predicate-assistant.local.md ]; then
  mv ~/.claude/fda-predicate-assistant.local.md ~/.claude/fda-tools.local.md
  echo "✓ Settings migrated to ~/.claude/fda-tools.local.md"
else
  echo "ℹ No existing settings file found"
fi
```

### 3. Update Custom Scripts and Automation

Replace all command invocations in your:

- **Shell scripts** (`.sh`, `.bash`)
- **Python scripts** (`.py`)
- **Documentation** (`.md`, `.txt`)
- **CI/CD workflows** (`.yml`, `.yaml`)
- **Jupyter notebooks** (`.ipynb`)

**Find & Replace Pattern:**

```bash
# Command invocations
/fda-predicate-assistant:  →  /fda-tools:

# Namespace references
fda-predicate-assistant@fda-tools  →  fda-tools@fda-tools

# General references
fda-predicate-assistant  →  fda-tools
```

**Example Script:**

```bash
#!/bin/bash
# Update all your custom scripts
find ~/my-fda-scripts -type f \( -name "*.sh" -o -name "*.py" -o -name "*.md" \) -exec \
  sed -i 's|/fda-predicate-assistant:|/fda-tools:|g; s|fda-predicate-assistant|fda-tools|g' {} +
```

### 4. Clear Old Cache (Optional but Recommended)

```bash
# Clear cached data referencing old plugin name
rm -rf ~/.cache/claude-cli-nodejs/*fda-predicate-assistant* 2>/dev/null
echo "✓ Old cache cleared"
```

### 5. Verify Migration

```bash
# Check settings file exists
ls -lh ~/.claude/fda-tools.local.md

# Test a simple command
/fda-tools:status

# Verify plugin is recognized
claude plugin list | grep fda-tools
```

---

## Breaking Changes Summary

### ❌ What Will Break

1. **Old command invocations** (all 64 commands affected):
   ```bash
   /fda-predicate-assistant:research     # ❌ Will fail
   /fda-predicate-assistant:presub       # ❌ Will fail
   /fda-predicate-assistant:pma-search   # ❌ Will fail
   ```

2. **Settings file references**:
   - Old location `~/.claude/fda-predicate-assistant.local.md` will be ignored
   - Must migrate to `~/.claude/fda-tools.local.md`

3. **Hardcoded paths** in custom scripts

### ✅ What Won't Break

1. **Data files** in `~/fda-510k-data/projects/` (unchanged)
2. **Project directories** and `.fda/` metadata (unchanged)
3. **Cached predicate data** (`.cache/510k/`, `.cache/pma/`) (unchanged)
4. **API keys** (stored in settings file, just needs migration)
5. **Command functionality** (identical behavior, only names changed)

---

## Command Reference: Before & After

### Core Commands (18 most common)

| Before | After |
|--------|-------|
| `/fda-predicate-assistant:start` | `/fda-tools:start` |
| `/fda-predicate-assistant:configure` | `/fda-tools:configure` |
| `/fda-predicate-assistant:research` | `/fda-tools:research` |
| `/fda-predicate-assistant:review` | `/fda-tools:review` |
| `/fda-predicate-assistant:compare-se` | `/fda-tools:compare-se` |
| `/fda-predicate-assistant:draft` | `/fda-tools:draft` |
| `/fda-predicate-assistant:pre-check` | `/fda-tools:pre-check` |
| `/fda-predicate-assistant:assemble` | `/fda-tools:assemble` |
| `/fda-predicate-assistant:presub` | `/fda-tools:presub` |
| `/fda-predicate-assistant:pma-search` | `/fda-tools:pma-search` |
| `/fda-predicate-assistant:batchfetch` | `/fda-tools:batchfetch` |
| `/fda-predicate-assistant:safety` | `/fda-tools:safety` |
| `/fda-predicate-assistant:standards` | `/fda-tools:standards` |
| `/fda-predicate-assistant:literature` | `/fda-tools:literature` |
| `/fda-predicate-assistant:monitor` | `/fda-tools:monitor` |
| `/fda-predicate-assistant:pipeline` | `/fda-tools:pipeline` |
| `/fda-predicate-assistant:status` | `/fda-tools:status` |
| `/fda-predicate-assistant:export` | `/fda-tools:export` |

**All 64 commands** follow the same pattern. See README.md for complete command list.

---

## Automated Migration Script

Save this as `migrate-fda-tools.sh` and run with `bash migrate-fda-tools.sh`:

```bash
#!/bin/bash
set -e

echo "========================================="
echo "FDA-37: Plugin Rename Migration Script"
echo "========================================="
echo ""

# Step 1: Backup settings
if [ -f ~/.claude/fda-predicate-assistant.local.md ]; then
  echo "[1/5] Backing up settings..."
  cp ~/.claude/fda-predicate-assistant.local.md ~/.claude/fda-predicate-assistant.local.md.backup
  echo "✓ Backup created: ~/.claude/fda-predicate-assistant.local.md.backup"
else
  echo "[1/5] No existing settings found (skipping backup)"
fi

# Step 2: Migrate settings file
if [ -f ~/.claude/fda-predicate-assistant.local.md ]; then
  echo "[2/5] Migrating settings file..."
  mv ~/.claude/fda-predicate-assistant.local.md ~/.claude/fda-tools.local.md
  echo "✓ Settings migrated: ~/.claude/fda-tools.local.md"
else
  echo "[2/5] No settings file to migrate"
fi

# Step 3: Update custom scripts (user directory - CUSTOMIZE THIS PATH)
USER_SCRIPTS_DIR="${HOME}/fda-scripts"  # ← CHANGE THIS TO YOUR SCRIPTS DIRECTORY
if [ -d "$USER_SCRIPTS_DIR" ]; then
  echo "[3/5] Updating custom scripts in $USER_SCRIPTS_DIR..."
  find "$USER_SCRIPTS_DIR" -type f \( -name "*.sh" -o -name "*.py" -o -name "*.md" \) -exec \
    sed -i.bak 's|/fda-predicate-assistant:|/fda-tools:|g; s|fda-predicate-assistant@fda-tools|fda-tools@fda-tools|g; s|fda-predicate-assistant|fda-tools|g' {} +
  echo "✓ Custom scripts updated (backups: *.bak)"
else
  echo "[3/5] No custom scripts directory found at $USER_SCRIPTS_DIR (skipping)"
fi

# Step 4: Clear old cache
echo "[4/5] Clearing old cache..."
rm -rf ~/.cache/claude-cli-nodejs/*fda-predicate-assistant* 2>/dev/null || true
echo "✓ Cache cleared"

# Step 5: Verify migration
echo "[5/5] Verifying migration..."
if [ -f ~/.claude/fda-tools.local.md ]; then
  echo "✓ Settings file: ~/.claude/fda-tools.local.md"
else
  echo "⚠ Settings file not found (may need manual creation)"
fi

echo ""
echo "========================================="
echo "Migration Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Test a command: /fda-tools:status"
echo "2. Review updated scripts in: $USER_SCRIPTS_DIR"
echo "3. Remove .bak files after verification"
echo ""
echo "Need help? See: MIGRATION_NOTICE.md"
```

---

## Troubleshooting

### Issue: "Command not found: /fda-tools:*"

**Cause:** Plugin not recognized by Claude CLI
**Solution:**
```bash
# Reinstall plugin
claude plugin uninstall fda-predicate-assistant 2>/dev/null || true
claude plugin install fda-tools

# Verify installation
claude plugin list | grep fda-tools
```

### Issue: Settings not loading

**Cause:** Settings file not migrated
**Solution:**
```bash
# Check if old file exists
ls ~/.claude/fda-predicate-assistant.local.md

# Migrate manually
mv ~/.claude/fda-predicate-assistant.local.md ~/.claude/fda-tools.local.md

# Verify new location
cat ~/.claude/fda-tools.local.md
```

### Issue: Custom scripts still reference old name

**Cause:** Scripts not updated
**Solution:**
```bash
# Find all references
grep -r "fda-predicate-assistant" ~/your-scripts-directory/

# Update with sed
find ~/your-scripts-directory/ -type f -exec \
  sed -i 's|fda-predicate-assistant|fda-tools|g' {} +
```

---

## Rollback Procedure

If you encounter critical issues, you can rollback:

```bash
# 1. Restore settings backup
mv ~/.claude/fda-predicate-assistant.local.md.backup ~/.claude/fda-predicate-assistant.local.md

# 2. Reinstall old version (if available)
claude plugin install andrewlasiter/fda-tools@5.36.0

# 3. Restore script backups
find ~/your-scripts-directory/ -name "*.bak" -exec bash -c 'mv "$1" "${1%.bak}"' _ {} \;

# 4. Report issue
# https://github.com/andrewlasiter/fda-tools/issues
```

---

## FAQ

### Q: Will my existing projects still work?

**A:** Yes! Project data in `~/fda-510k-data/projects/` is unaffected. Only command invocations need updating.

### Q: Do I need to re-configure API keys?

**A:** No, if you migrated your settings file (`~/.claude/fda-tools.local.md`), all API keys and configurations are preserved.

### Q: What about data in `.cache/` directories?

**A:** Cache data is path-independent. It will continue working. However, clearing old cache is recommended for cleanup.

### Q: Can I use both old and new names temporarily?

**A:** No. The plugin can only be installed with one name at a time. You must fully migrate.

---

## Support & Reporting Issues

- **Documentation:** [README.md](README.md), [QUICK_START.md](docs/QUICK_START.md)
- **Issues:** [GitHub Issues](https://github.com/andrewlasiter/fda-tools/issues)
- **Discussions:** [GitHub Discussions](https://github.com/andrewlasiter/fda-tools/discussions)

---

## Refactoring Summary

**Files Updated:** 109
**Total Replacements:** 337
**Patterns Replaced:**
- `fda-predicate-assistant@fda-tools` → `fda-tools@fda-tools` (3 occurrences)
- `/fda-predicate-assistant:` → `/fda-tools:` (10 occurrences)
- `fda-predicate-assistant` → `fda-tools` (324 occurrences)

**File Types Affected:**
- Markdown (`.md`): 90 files
- JSON (`.json`): 1 file
- Python (`.py`): 1 file

**Test Status:** All automated tests passing (0 remaining old references)

---

**Last Updated:** 2026-02-17
**Refactoring Ticket:** FDA-37
**Branch:** `andrewlasiter/fda-37-plugin-rename-fda-predicate-assistant-fda-tools`
