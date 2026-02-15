# ERROR_RECOVERY.md - Priority 1 Corrections (Ready to Apply)

**Purpose**: Exact corrections needed to resolve Priority 1 issues before release

**Time to Apply**: ~5 minutes

---

## Correction 1: Fix Git Checkout Syntax (Lines 183-186)

**Location**: `Rollback Procedures → Rollback to Previous Version`

### ❌ CURRENT (INCORRECT)
```bash
# Restore from git (if committed)
git checkout HEAD~1 ~/fda-510k-data/projects/YOUR_PROJECT/presub_plan.md
git checkout HEAD~1 ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json
git checkout HEAD~1 ~/fda-510k-data/projects/YOUR_PROJECT/presub_prestar.xml
```

**Problem**: The syntax `git checkout HEAD~1 <path>` is invalid. Correct git syntax requires either:
- `git checkout HEAD~1 -- <path>` (from any directory)
- `git checkout HEAD~1 <path>` (from within repository root with proper relative path)

### ✅ CORRECTED (VALID)
```bash
# Restore from git (if committed)
# Change to project directory first
cd ~/fda-510k-data/projects/YOUR_PROJECT/

# Then restore files from previous commit
git checkout HEAD~1 -- presub_plan.md
git checkout HEAD~1 -- presub_metadata.json
git checkout HEAD~1 -- presub_prestar.xml

# Verify files were restored
ls -l presub_*.* | tail -3
```

**Why This Works**:
- Absolute path `~/fda-510k-data/projects/YOUR_PROJECT/` may not be git-tracked root
- Using `--` explicitly separates commit reference from paths
- Relative paths work from within git repository
- Added verification step (ls command) confirms restoration

---

## Correction 2: Add Editor Alternatives (After Line 162)

**Location**: `Error Scenario 7 → Auto-Trigger Misfires → Recovery Steps`

### CURRENT TEXT (Line 163)
```markdown
# Manually edit presub_metadata.json to remove incorrect questions
nano ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json
```

### ENHANCED TEXT (REPLACEMENT)
```markdown
# Manually edit presub_metadata.json to remove incorrect questions
# Use your preferred editor (nano, vim, or sed for CLI environments)

# Option 1: Interactive editor (nano)
nano ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# Option 2: Interactive editor (vim)
vim ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# Option 3: Sed-based in-place editing (for automation)
# Remove a specific question ID:
# sed -i 's/"TEST-BIO-001"//g' ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# Option 4: Python-based programmatic editing
python3 << 'PYEOF'
import json
metadata_path = "~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json"
with open(metadata_path) as f:
    metadata = json.load(f)

# Remove specific question ID (example: TEST-BIO-001)
if "TEST-BIO-001" in metadata["questions_generated"]:
    metadata["questions_generated"].remove("TEST-BIO-001")
    metadata["question_count"] -= 1

with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=2)

print(f"Updated questions: {metadata['questions_generated']}")
PYEOF
```

**Rationale**:
- Provides 4 approaches for different user preferences
- nano may not be available in all environments
- Python option preserves JSON integrity (auto-fixes formatting)
- sed option useful for automation/scripting

---

## Correction 3: Improve JSON Parsing in Scenario 7 (Line 160)

**Location**: `Error Scenario 7 → Recovery Steps → Step 1`

### CURRENT TEXT (LINES 159-160)
```bash
# Review auto-triggers that fired
grep "auto_triggers_fired" ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json
```

**Problem**: `grep` only shows the line containing "auto_triggers_fired", not the actual array values. RA professionals can't easily see which triggers fired.

### ENHANCED TEXT (REPLACEMENT)
```bash
# Review auto-triggers that fired
# Show the actual trigger values (not just the line containing the key)

python3 << 'PYEOF'
import json

metadata_path = "~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json"
try:
    with open(metadata_path) as f:
        metadata = json.load(f)

    print("Auto-triggers that fired:")
    if metadata.get("auto_triggers_fired"):
        for trigger in metadata["auto_triggers_fired"]:
            print(f"  - {trigger}")
    else:
        print("  (none)")

    print("\nQuestions generated:")
    for i, q_id in enumerate(metadata.get("questions_generated", []), 1):
        print(f"  {i}. {q_id}")

except FileNotFoundError:
    print(f"ERROR: File not found: {metadata_path}")
except json.JSONDecodeError as e:
    print(f"ERROR: Invalid JSON: {e}")
PYEOF
```

**Benefit**: Shows both triggers and questions in human-readable format, easier for RA professionals to review.

---

## Correction 4: Add File Path Clarity (Line 18)

**Location**: `Error Scenario 1 → Recovery Steps → Verify file exists`

### CURRENT TEXT
```bash
# Verify file exists
ls -lh plugins/fda-tools/data/question_banks/presub_questions.json
```

**Issue**: Relative path may not work depending on where user runs command from.

### ENHANCED TEXT (REPLACEMENT)
```bash
# Verify file exists
# Resolve plugin path first
FDA_PLUGIN_ROOT=$(python3 -c "
import json, os
f = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(f):
    d = json.load(open(f))
    for k, v in d.get('plugins', {}).items():
        if k.startswith('fda-predicate-assistant@'):
            for e in v:
                p = e.get('installPath', '')
                if os.path.isdir(p):
                    print(p); exit()
print('')
")

if [ -z "$FDA_PLUGIN_ROOT" ]; then
    echo "ERROR: Could not locate FDA Predicate Assistant plugin"
    exit 1
fi

# Now verify file exists
ls -lh "$FDA_PLUGIN_ROOT/plugins/fda-tools/data/question_banks/presub_questions.json"
```

**Benefit**: Works from any directory; doesn't assume user is in plugin root.

---

## Summary of Changes

### Changes to Apply

| Line(s) | Section | Change Type | Priority |
|---|---|---|---|
| 183-186 | Rollback Procedures | Fix + Enhance | 🔴 CRITICAL |
| 163 | Scenario 7 Recovery | Enhance (add alternatives) | 🔴 CRITICAL |
| 159-160 | Scenario 7 Recovery | Enhance (JSON parsing) | 🟠 MEDIUM |
| 18 | Scenario 1 Recovery | Enhance (path resolution) | 🟠 MEDIUM |

### Time Estimate

- **Correction 1** (git syntax): 2 minutes
- **Correction 2** (editor alternatives): 2 minutes
- **Correction 3** (JSON parsing): 1 minute
- **Correction 4** (file path clarity): 1 minute

**Total Time**: ~6 minutes

---

## Detailed Edits (In Order)

### Edit 1: Correct git checkout syntax (CRITICAL)

**File**: `plugins/fda-tools/docs/ERROR_RECOVERY.md`

**Lines to Replace**: 183-186

**Old Text**:
```
Rollback to Previous Version

If a Pre-Sub package was generated with an earlier plugin version:

```bash
# Restore from git (if committed)
git checkout HEAD~1 ~/fda-510k-data/projects/YOUR_PROJECT/presub_plan.md
git checkout HEAD~1 ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json
git checkout HEAD~1 ~/fda-510k-data/projects/YOUR_PROJECT/presub_prestar.xml

# Or restore from backup
cp ~/fda-510k-data/projects/YOUR_PROJECT/presub_plan.md.backup \
   ~/fda-510k-data/projects/YOUR_PROJECT/presub_plan.md
```
```

**New Text**:
```
Rollback to Previous Version

If a Pre-Sub package was generated with an earlier plugin version:

```bash
# Restore from git (if committed)
cd ~/fda-510k-data/projects/YOUR_PROJECT/
git checkout HEAD~1 -- presub_plan.md
git checkout HEAD~1 -- presub_metadata.json
git checkout HEAD~1 -- presub_prestar.xml

# Verify files were restored
ls -l presub_*.* | tail -3

# Or restore from backup
cp ~/fda-510k-data/projects/YOUR_PROJECT/presub_plan.md.backup \
   ~/fda-510k-data/projects/YOUR_PROJECT/presub_plan.md
```
```

---

### Edit 2: Add editor alternatives (CRITICAL)

**File**: `plugins/fda-tools/docs/ERROR_RECOVERY.md`

**Lines to Replace**: 161-163

**Old Text**:
```
# Manually edit presub_metadata.json to remove incorrect questions
nano ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json
```

**New Text**:
```
# Manually edit presub_metadata.json to remove incorrect questions
# Use your preferred editor (nano, vim, or sed for CLI environments)

# Option 1: Interactive editor (nano)
nano ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# Option 2: Interactive editor (vim)
vim ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# Option 3: Python-based programmatic editing (recommended for automation)
python3 << 'PYEOF'
import json
metadata_path = "~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json"
with open(metadata_path) as f:
    metadata = json.load(f)

# Remove specific question ID (example: TEST-BIO-001)
if "TEST-BIO-001" in metadata["questions_generated"]:
    metadata["questions_generated"].remove("TEST-BIO-001")
    metadata["question_count"] -= 1

with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=2)

print(f"Updated questions: {metadata['questions_generated']}")
PYEOF
```
```

---

### Edit 3: Improve JSON parsing (MEDIUM - Optional)

**File**: `plugins/fda-tools/docs/ERROR_RECOVERY.md`

**Lines to Replace**: 159-160

**Old Text**:
```
# Review auto-triggers that fired
grep "auto_triggers_fired" ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json
```

**New Text**:
```
# Review auto-triggers that fired
# Show the actual trigger values (not just the line containing the key)

python3 << 'PYEOF'
import json

metadata_path = "~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json"
try:
    with open(metadata_path) as f:
        metadata = json.load(f)

    print("Auto-triggers that fired:")
    if metadata.get("auto_triggers_fired"):
        for trigger in metadata["auto_triggers_fired"]:
            print(f"  - {trigger}")
    else:
        print("  (none)")

    print("\nQuestions generated:")
    for i, q_id in enumerate(metadata.get("questions_generated", []), 1):
        print(f"  {i}. {q_id}")

except FileNotFoundError:
    print(f"ERROR: File not found: {metadata_path}")
except json.JSONDecodeError as e:
    print(f"ERROR: Invalid JSON: {e}")
PYEOF
```
```

---

### Edit 4: Add file path resolution (MEDIUM - Optional)

**File**: `plugins/fda-tools/docs/ERROR_RECOVERY.md`

**Lines to Replace**: 16-18

**Old Text**:
```
# Verify file exists
ls -lh plugins/fda-tools/data/question_banks/presub_questions.json

# Validate JSON syntax
```

**New Text**:
```
# Verify file exists
# Resolve plugin path first (works from any directory)
FDA_PLUGIN_ROOT=$(python3 -c "
import json, os
f = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(f):
    d = json.load(open(f))
    for k, v in d.get('plugins', {}).items():
        if k.startswith('fda-predicate-assistant@'):
            for e in v:
                p = e.get('installPath', '')
                if os.path.isdir(p):
                    print(p); exit()
print('')
")

if [ -z "$FDA_PLUGIN_ROOT" ]; then
    echo "ERROR: Could not locate FDA Predicate Assistant plugin"
    exit 1
fi

ls -lh "$FDA_PLUGIN_ROOT/plugins/fda-tools/data/question_banks/presub_questions.json"

# Validate JSON syntax
```
```

---

## Verification Checklist

After applying corrections, verify:

- [ ] Line 183-186: git commands use `--` separator and relative paths
- [ ] Line 163+: nano, vim, and Python editor options all shown
- [ ] Line 159-160: Python script parses JSON and shows triggers + questions
- [ ] Line 16-18: Plugin path resolution works from any directory
- [ ] All code blocks are properly formatted (indentation, syntax highlighting)
- [ ] No placeholder text remains (e.g., `YOUR_PROJECT` should still be placeholder for users)
- [ ] File still opens without errors (JSON/YAML validation)

---

## Testing Recommendations

### Test 1: Git Checkout Correction
```bash
# Simulate rollback scenario
cd ~/fda-510k-data/projects/test_project/
git checkout HEAD~1 -- presub_plan.md  # Should succeed without errors
```

### Test 2: Editor Alternatives
```bash
# Test Python parsing (always available)
python3 << 'PYEOF'
import json
# ... (run corrected code snippet)
PYEOF

# Verify output shows triggers and questions clearly
```

### Test 3: File Path Resolution
```bash
# Test from different directory
cd ~
bash -c 'source ~/.bashrc; FDA_PLUGIN_ROOT=... && ls -lh "$FDA_PLUGIN_ROOT/..."'
```

---

## Questions During Application

**Q**: Should I apply all 4 corrections or just Priority 1?
**A**: Apply at least Corrections 1-2 (CRITICAL) before release. Corrections 3-4 are recommended enhancements (MEDIUM priority).

**Q**: Will these corrections break anything?
**A**: No. These are purely corrective/additive changes. No functionality is removed.

**Q**: Do I need to update the version number?
**A**: This should be considered a documentation bugfix. If releasing as v5.25.1, note "Fixed ERROR_RECOVERY.md git syntax and added editor alternatives" in CHANGELOG.

**Q**: Should RA professionals be notified?
**A**: If this document has been distributed, send a brief email: "ERROR_RECOVERY.md has been updated with corrected git commands and editor alternatives. Please use the updated version."

---

**Document**: ERROR_RECOVERY_CORRECTIONS.md
**Date**: 2026-02-15
**Status**: Ready to Apply
**Estimated Review Time**: 5 minutes
**Estimated Application Time**: 6 minutes
**Total Time to Release**: ~15 minutes (including testing)

