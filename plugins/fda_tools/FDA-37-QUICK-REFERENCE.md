# FDA-37: Quick Reference Guide

## What Changed

```
fda-predicate-assistant  →  fda-tools
```

## Command Changes (All 64 Commands)

| Old Format | New Format |
|------------|------------|
| `/fda-predicate-assistant:*` | `/fda-tools:*` |

### Examples

```bash
# Before                                  # After
/fda-predicate-assistant:start         → /fda-tools:start
/fda-predicate-assistant:research      → /fda-tools:research
/fda-predicate-assistant:presub        → /fda-tools:presub
/fda-predicate-assistant:pma-search    → /fda-tools:pma-search
/fda-predicate-assistant:batchfetch    → /fda-tools:batchfetch
```

## Files Changed

- **Total:** 109 files
- **Replacements:** 337 occurrences
- **Command files:** 64 commands updated
- **Documentation:** 90 files updated

## Quick Migration

```bash
# 1. Migrate settings file (if it exists)
[ -f ~/.claude/fda-predicate-assistant.local.md ] && \
  mv ~/.claude/fda-predicate-assistant.local.md ~/.claude/fda-tools.local.md

# 2. Update your custom scripts
find ~/my-scripts -type f -name "*.sh" -exec \
  sed -i 's|/fda-predicate-assistant:|/fda-tools:|g' {} +

# 3. Clear old cache
rm -rf ~/.cache/claude-cli-nodejs/*fda-predicate-assistant*

# 4. Test
/fda-tools:status
```

## What Won't Break

✅ Project data in `~/fda-510k-data/projects/`
✅ Cache data in `~/fda-510k-data/.cache/`
✅ API keys (just migrate settings file)
✅ Command behavior (unchanged)
✅ All flags and options (identical)

## Full Documentation

- **Comprehensive Guide:** `MIGRATION_NOTICE.md`
- **Completion Report:** `FDA-37-REFACTORING-COMPLETE.md`
- **Updated README:** `README.md`

## Git Info

- **Branch:** `andrewlasiter/fda-37-plugin-rename-fda-predicate-assistant-fda-tools`
- **Status:** Ready for commit
- **Test Status:** ✅ All references updated

## Next Steps for User

1. Review changes: `git diff --stat`
2. Commit: `git add . && git commit -m "feat(FDA-37): Rename plugin"`
3. Push: `git push origin andrewlasiter/fda-37-plugin-rename-fda-predicate-assistant-fda-tools`
4. Do NOT merge yet - user will handle PR creation

---

**Date:** 2026-02-17 | **Ticket:** FDA-37 | **Status:** ✅ COMPLETE
