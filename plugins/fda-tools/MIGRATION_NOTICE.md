# IMPORTANT: Plugin Rename Migration Guide

The FDA regulatory plugin has been renamed from `fda-predicate-assistant` to `fda-tools`.

## What Changed
- Plugin name: `fda-predicate-assistant` → `fda-tools`
- Namespace: `fda-predicate-assistant@fda-tools` → `fda-tools@fda-tools`
- All commands: `/fda-predicate-assistant:*` → `/fda-tools:*`

## Migration Steps

### 1. Backup Your Settings
```bash
cp ~/.claude/fda-predicate-assistant.local.md ~/.claude/fda-predicate-assistant.local.md.backup
```

### 2. Migrate Settings File
```bash
mv ~/.claude/fda-predicate-assistant.local.md ~/.claude/fda-tools.local.md
```

### 3. Update Saved Scripts
Replace all instances of `/fda-predicate-assistant:` with `/fda-tools:` in:
- Shell scripts
- Notebooks
- Documentation
- Automation workflows

### 4. Clear Old Cache (Optional)
```bash
rm -rf ~/.cache/claude-cli-nodejs/*fda-predicate-assistant*
```

### 5. Re-install Plugin
```bash
claude plugin uninstall fda-predicate-assistant
claude plugin install fda-tools
```

## Breaking Changes
- Old command invocations will fail
- Settings files MUST be renamed manually
- Cached data in old paths will be ignored

## Why This Change?

The rename simplifies the plugin namespace from `fda-predicate-assistant@fda-tools` to `fda-tools@fda-tools` and better reflects the comprehensive nature of the tools suite (not just predicate assistance).

## Need Help?

If you encounter issues during migration:
- Check that your settings file was migrated correctly: `ls ~/.claude/fda-tools.local.md`
- Verify commands work: `/fda-tools:status`
- Clear all cache if problems persist: `rm -rf ~/.cache/claude-cli-nodejs/`
- Report issues at: https://github.com/andrewlasiter/fda-predicate-assistant/issues
