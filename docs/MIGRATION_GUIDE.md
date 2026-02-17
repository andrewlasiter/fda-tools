# Migration Guide: fda-predicate-assistant → fda-tools

**Date:** 2026-02-17
**Plugin Version:** 5.36.0+
**Change Type:** Plugin Namespace Rename

## Overview

The FDA plugin has been renamed from `fda-predicate-assistant` to `fda-tools` for clarity and to better reflect the comprehensive nature of the tools suite (not just predicate assistance).

## What Changed

### Plugin Naming

- **Old plugin name:** fda-predicate-assistant
- **New plugin name:** fda-tools
- **Old namespace:** fda-predicate-assistant@fda-tools
- **New namespace:** fda-tools@fda-tools

### Command Prefix

- **Old command prefix:** `/fda-predicate-assistant:command`
- **New command prefix:** `/fda-tools:command` OR `/fda:command` (shorthand)

### Examples

| Old Command | New Command (Full) | New Command (Short) |
|-------------|-------------------|---------------------|
| `/fda-predicate-assistant:research` | `/fda-tools:research` | `/fda:research` |
| `/fda-predicate-assistant:batchfetch` | `/fda-tools:batchfetch` | `/fda:batchfetch` |
| `/fda-predicate-assistant:draft` | `/fda-tools:draft` | `/fda:draft` |

## Migration Steps

### For End Users

#### 1. Your Data is Safe

All existing data is preserved at `~/fda-510k-data/`:
- Project data
- Downloaded PDFs
- Database caches
- Configuration files

**No data migration needed.**

#### 2. Settings File Migration (Optional)

The plugin now uses a new settings file path but still supports the old one for backward compatibility.

**Option A: Keep using old settings file (no action required)**
- Path: `~/.claude/fda-predicate-assistant.local.md`
- Status: Still supported, works seamlessly
- Action: Nothing - just keep using the plugin

**Option B: Migrate to new settings file (recommended)**

```bash
# Backup old settings
cp ~/.claude/fda-predicate-assistant.local.md ~/.claude/fda-predicate-assistant.local.md.backup

# Copy to new location
cp ~/.claude/fda-predicate-assistant.local.md ~/.claude/fda-tools.local.md

# Optionally remove old file (after verifying new one works)
# rm ~/.claude/fda-predicate-assistant.local.md
```

#### 3. Update Command Usage

If you have saved scripts, aliases, or documentation that reference the old command prefix:

**OLD:**
```bash
/fda-predicate-assistant:research --product-code DQY
```

**NEW:**
```bash
/fda:research --product-code DQY
# or
/fda-tools:research --product-code DQY
```

#### 4. Old Plugin Archive

The old plugin directory has been archived (not deleted) at:

```
/home/linux/.claude/plugins/marketplaces/fda-tools/archives/fda-predicate-assistant_20260217.tar.gz
```

**Archive Details:**
- Size: 21 MB compressed (75 MB uncompressed)
- Files: 3,345 files
- Retention: Permanent (for rollback if needed)

To restore from archive:
```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/
tar -xzf ../archives/fda-predicate-assistant_20260217.tar.gz
```

### For Developers

#### 1. Import Path Updates

If you have custom scripts that import from the plugin:

**OLD:**
```python
from fda_predicate_assistant.lib import fda_enrichment
```

**NEW:**
```python
# Plugin lib is accessed via plugin root detection
# See plugins/fda-tools/references/path-resolution.md
```

#### 2. Script Path References

Update any hardcoded paths:

**OLD:**
```bash
python3 plugins/fda-predicate-assistant/scripts/build_structured_cache.py
```

**NEW:**
```bash
python3 plugins/fda-tools/scripts/build_structured_cache.py
```

#### 3. Absolute Path References

If you have documentation or scripts with absolute paths:

**OLD:**
```
/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-predicate-assistant/
```

**NEW:**
```
/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/
```

#### 4. Plugin Root Detection (Backward Compatible)

The plugin root detection code supports BOTH old and new namespace for backward compatibility:

```python
# Get plugin root from environment (works with both namespaces)
for k, v in os.environ.items():
    if k.startswith('fda-predicate-assistant@'):  # OLD NAME (still supported)
        plugin_root = v
    if k.startswith('fda-tools@'):  # NEW NAME
        plugin_root = v
```

This ensures existing installations continue to work without modifications.

## Breaking Changes

**None** - all functionality has been preserved through backward compatibility layers.

### What Still Works

1. **Old settings file:** `~/.claude/fda-predicate-assistant.local.md` still works
2. **Plugin root detection:** Checks both `fda-predicate-assistant@` and `fda-tools@` namespaces
3. **API tool parameters:** PubMed API still uses `tool=fda-predicate-assistant` for continuity
4. **All commands:** Full backward compatibility maintained

## Rollback Procedure

If you encounter issues after the migration:

### 1. Extract Archive

```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/
tar -xzf ../archives/fda-predicate-assistant_20260217.tar.gz
```

### 2. Verify Restoration

```bash
ls -la fda-predicate-assistant/
# Should show all original files restored
```

### 3. Report Issue

File an issue at: https://github.com/andrewlasiter/fda-predicate-assistant/issues

Include:
- Error message
- Command you were running
- Plugin version (`/fda:status`)
- Operating system

## Technical Details

### Files Modified in Migration

Only 2 files were updated to complete the migration:

1. **`plugins/fda-tools/commands/batchfetch.md:930`**
   - Updated lib path fallback from `plugins/fda-predicate-assistant/lib` to `plugins/fda-tools/lib`

2. **`.claude/settings.local.json:16`**
   - Updated smoke test script path from `plugins/fda-predicate-assistant/skills/` to `plugins/fda-tools/skills/`

### Disk Space Recovered

- **Before:** 75 MB used by old plugin (3,345 files)
- **After:** 21 MB archive (compressed)
- **Space saved:** 54 MB (72% reduction)

### Settings File Backward Compatibility

The plugin checks for settings files in this order:

1. `~/.claude/fda-tools.local.md` (new, preferred)
2. `~/.claude/fda-predicate-assistant.local.md` (old, still supported)
3. Default values if neither exists

You can continue using either file indefinitely.

## FAQ

### Q: Do I need to reinstall the plugin?

**A:** No. The plugin is already updated. Just start using `/fda:` instead of `/fda-predicate-assistant:` commands.

### Q: Will my old commands stop working?

**A:** No. The old namespace `fda-predicate-assistant@` is still recognized for plugin root detection. However, you should use the new `/fda:` command prefix.

### Q: What happens to my settings file?

**A:** It continues to work. The plugin checks both old and new locations. You can migrate it when convenient.

### Q: Can I delete the archive after verifying everything works?

**A:** Yes, but we recommend keeping it for at least 30 days in case you need to rollback.

### Q: Do I need to update my API keys?

**A:** No. API keys are read from whichever settings file exists (old or new location).

### Q: What about my project data at ~/fda-510k-data/?

**A:** Completely unaffected. All project data, PDFs, and caches remain intact.

## Version History

| Version | Date | Change |
|---------|------|--------|
| 5.22.0 | 2025-01-15 | Plugin renamed from fda-predicate-assistant to fda-tools |
| 5.36.0+ | 2026-02-17 | Old plugin archived, migration guide created |

## References

- **Original Migration Notice:** [MIGRATION_NOTICE.md](../MIGRATION_NOTICE.md)
- **Cross-Reference Analysis:** [FDA-24_CROSS_REFERENCE_ANALYSIS.md](FDA-24_CROSS_REFERENCE_ANALYSIS.md)
- **GitHub Repository:** https://github.com/andrewlasiter/fda-predicate-assistant
- **Issue Tracker:** https://github.com/andrewlasiter/fda-predicate-assistant/issues

## Support

If you need help with migration:

1. **Check troubleshooting:** [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. **Review changelog:** [CHANGELOG.md](../CHANGELOG.md)
3. **File an issue:** https://github.com/andrewlasiter/fda-predicate-assistant/issues

Include relevant details:
- Error message
- Command you were running
- Plugin version
- Operating system
- Settings file location you're using
