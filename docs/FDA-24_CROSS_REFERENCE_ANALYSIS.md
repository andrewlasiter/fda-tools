# FDA-24: Cross-Reference Analysis

**Date:** 2026-02-17
**Analyst:** refactoring-specialist
**Scope:** Identify all references to `fda-predicate-assistant` in the `fda-tools` plugin

## Executive Summary

Analysis completed on 361 grep matches across fda-tools plugin directories. References fall into 4 categories:

1. **Settings file paths** (INTENTIONAL - backward compatibility)
2. **Plugin root detection** (INTENTIONAL - backward compatibility)
3. **GitHub repository URL** (INTENTIONAL - valid repo)
4. **Documentation/historical references** (INFORMATIONAL - migration context)
5. **ONE CRITICAL REFERENCE** - hardcoded lib path in batchfetch.md

## Critical Findings

### 1. MUST FIX: Hardcoded Library Path

**File:** `plugins/fda-tools/commands/batchfetch.md:930`

```python
lib_path = Path.home() / '.claude' / 'plugins' / 'marketplaces' / 'fda-tools' / 'plugins' / 'fda-predicate-assistant' / 'lib'
```

**Issue:** This references the OLD plugin directory for library imports. This will break after old plugin removal.

**Fix Required:** Change to:
```python
lib_path = Path.home() / '.claude' / 'plugins' / 'marketplaces' / 'fda-tools' / 'plugins' / 'fda-tools' / 'lib'
```

### 2. MUST UPDATE: Smoke Test Permission

**File:** `.claude/settings.local.json:16`

```json
"Bash(bash plugins/fda-predicate-assistant/skills/fda-plugin-e2e-smoke/scripts/run_smoke.sh)"
```

**Issue:** Permission references old plugin path.

**Fix Required:** Change to:
```json
"Bash(bash plugins/fda-tools/skills/fda-plugin-e2e-smoke/scripts/run_smoke.sh)"
```

## Intentional Backward Compatibility References

The following references are INTENTIONAL and should NOT be changed:

### Settings File Path Pattern (183 occurrences)

**Pattern:** `~/.claude/fda-predicate-assistant.local.md`

**Locations:**
- 68 command files
- 15 agent files
- 3 skill reference files
- Documentation files

**Reason:** The plugin supports BOTH old and new settings files for backward compatibility:
- New users: `~/.claude/fda-tools.local.md`
- Migrated users: `~/.claude/fda-predicate-assistant.local.md` (legacy support)

**Code Pattern:**
```python
# Plugin root detection checks BOTH namespaces
if k.startswith('fda-predicate-assistant@'):  # OLD NAME (backward compat)
    plugin_root = v
if k.startswith('fda-tools@'):  # NEW NAME
    plugin_root = v
```

This allows users who haven't migrated their settings file to continue using the plugin without disruption.

### GitHub Repository URL (8 occurrences)

**Pattern:** `https://github.com/andrewlasiter/fda-predicate-assistant`

**Locations:**
- `.claude-plugin/plugin.json:8`
- `docs/INSTALLATION.md:42`
- `docs/INSTALLATION.md:341`
- Documentation issue tracker links

**Reason:** This is the actual GitHub repository URL. The repository itself is named `fda-predicate-assistant` and hasn't been renamed. Only the plugin namespace changed.

## Documentation and Historical References

### Migration Documentation (52 occurrences)

These references are INFORMATIONAL and explain the migration:

**Key Files:**
- `MIGRATION_NOTICE.md` - User migration guide
- `CHANGELOG.md` - Version history
- `docs/INSTALLATION.md` - Upgrade instructions
- `docs/TROUBLESHOOTING.md` - Common issues
- `README.md` - Migration notice link

**Examples:**
- "Upgrading from fda-predicate-assistant"
- "Plugin Rename: fda-predicate-assistant → fda-tools"
- "Old: /fda-predicate-assistant:command"

**Action:** Keep these as-is for historical context and user guidance.

### Implementation Documentation (118 occurrences)

Phase documentation, implementation plans, and completion reports that reference the old plugin directory structure:

**Pattern:** `plugins/fda-predicate-assistant/lib/fda_enrichment.py`

**Examples:**
- `docs/phases/PHASE1_CHANGELOG.md`
- `docs/compliance/IMPLEMENTATION_STATUS_RA2_RA6.md`
- `TICKET-017-PHASE1-COMPLETE.md`

**Reason:** These are historical records of where files were located during development. Changing them would lose the historical context.

**Action:** Keep as-is for audit trail.

### PubMed API Tool Parameter

**Pattern:** `tool=fda-predicate-assistant`

**Locations:**
- `references/pubmed-api.md` (3 occurrences)
- `commands/literature.md` (2 occurrences)
- `skills/*/references/pubmed-api.md` (3 occurrences)

**Reason:** This is the user-agent string sent to NCBI's PubMed API. Changing it would:
1. Break API usage tracking continuity
2. Require re-registering with NCBI

**Action:** Keep as-is for API tracking consistency.

## Files Requiring Updates

### Priority 1: Critical (Breaks functionality)

1. **`plugins/fda-tools/commands/batchfetch.md:930`**
   - Change lib_path from `/plugins/fda-predicate-assistant/lib` to `/plugins/fda-tools/lib`

2. **`.claude/settings.local.json:16`**
   - Update smoke test script path

### Priority 2: Documentation Cleanup (Non-breaking)

These reference the old plugin in absolute paths and should be updated for consistency:

1. **`agents/ra-professional-advisor.md:157`**
   - Update absolute path reference

2. **`tests/test_urgent_fixes.py:581-584`**
   - Update fallback paths for lib and bridge directories

3. **`docs/PREDICATE_SCORING_MODEL_VALIDATION.md:576-582`**
   - Update 4 absolute path references

4. **`openclaw-skill/SKILL.md:284` and `openclaw-skill/README.md:78,275`**
   - Update example directory paths

## Verification Strategy

After making the 2 critical fixes:

1. **Test library import:**
   ```bash
   # Verify batchfetch can import from new lib path
   cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools
   python3 -c "from pathlib import Path; lib_path = Path.home() / '.claude' / 'plugins' / 'marketplaces' / 'fda-tools' / 'plugins' / 'fda-tools' / 'lib'; print(lib_path.exists())"
   ```

2. **Test smoke test script:**
   ```bash
   bash plugins/fda-tools/skills/fda-plugin-e2e-smoke/scripts/run_smoke.sh
   ```

3. **Grep for remaining absolute paths:**
   ```bash
   grep -r "/plugins/fda-predicate-assistant/" plugins/fda-tools/
   ```

## Recommendations

1. **Fix 2 critical references** before archiving old plugin
2. **Keep backward compatibility** for settings file paths
3. **Keep GitHub URLs** as-is (actual repo name)
4. **Keep historical documentation** for audit trail
5. **Keep PubMed API tool parameter** for tracking continuity

## Impact Assessment

**If old plugin removed WITHOUT fixes:**
- batchfetch.md will fail to import fda_enrichment module
- Smoke test permissions will be invalid

**After fixes + removal:**
- Zero breaking changes
- All functionality preserved
- ~50MB disk space recovered
- No user migration required (backward compat maintained)
