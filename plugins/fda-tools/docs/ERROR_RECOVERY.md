# PreSTAR XML Error Recovery Workflows

## Overview

This document describes error recovery procedures for the PreSTAR XML generation workflow (`/fda:presub` command).

## Common Error Scenarios

### 1. Question Bank Loading Failure

**Error**: `QUESTION_BANK_MISSING`, `QUESTION_BANK_INVALID`, or `QUESTION_BANK_SCHEMA_ERROR`

**Root Cause**: Missing or corrupted `presub_questions.json` file

**Recovery Steps**:
```bash
# Verify file exists
ls -lh plugins/fda-tools/data/question_banks/presub_questions.json

# Validate JSON syntax
python3 -m json.tool plugins/fda-tools/data/question_banks/presub_questions.json

# If missing, restore from git
git checkout plugins/fda-tools/data/question_banks/presub_questions.json
```

**Prevention**: Do not manually edit `presub_questions.json` without validating JSON syntax

---

### 2. Metadata Generation Failure

**Error**: `ERROR: Metadata missing required fields`, `ERROR: Failed to write metadata`

**Root Cause**: Invalid metadata structure or file system error

**Recovery Steps**:
```bash
# Check for existing metadata file
cat ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# Verify disk space
df -h ~/fda-510k-data/

# Check file permissions
ls -l ~/fda-510k-data/projects/YOUR_PROJECT/

# If corrupted, regenerate by re-running command
/fda:presub DQY --project YOUR_PROJECT --device-description "..." --intended-use "..."
```

**Prevention**: Ensure adequate disk space and proper directory permissions before running `/fda:presub`

---

### 3. Schema Version Mismatch

**Error**: `WARNING: presub_metadata.json version X.X may be incompatible`

**Root Cause**: Outdated metadata file from previous plugin version

**Recovery Steps**:
```bash
# Backup existing metadata
cp ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json \
   ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json.backup

# Regenerate with current version
/fda:presub DQY --project YOUR_PROJECT --device-description "..." --intended-use "..."

# Compare old vs new (optional)
diff presub_metadata.json.backup presub_metadata.json
```

**Prevention**: Regenerate Pre-Sub packages after major plugin updates

---

### 4. XML Generation Failure

**Error**: XML file not created in Step 7

**Root Cause**: Invalid presub_metadata.json or estar_xml.py execution error

**Recovery Steps**:
```bash
# Verify metadata file exists and is valid
cat ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json
python3 -m json.tool ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# Manually trigger XML generation
python3 plugins/fda-tools/scripts/estar_xml.py generate \
  --project YOUR_PROJECT \
  --template PreSTAR \
  --format real \
  --output ~/fda-510k-data/projects/YOUR_PROJECT/presub_prestar.xml

# Check for error messages
echo $?  # Should return 0 for success
```

**Prevention**: Ensure presub_metadata.json is valid before XML generation

---

### 5. Template Population Errors

**Error**: `[TODO: ...]` placeholders not replaced in presub_plan.md

**Root Cause**: Missing project data files (device_profile.json, review.json, etc.)

**Recovery Steps**:
```bash
# Check for required data files
ls -lh ~/fda-510k-data/projects/YOUR_PROJECT/device_profile.json
ls -lh ~/fda-510k-data/projects/YOUR_PROJECT/review.json

# If missing, run prerequisite commands
/fda:research --product-code DQY --years 2024 --project YOUR_PROJECT
/fda:review

# Regenerate Pre-Sub with enriched data
/fda:presub DQY --project YOUR_PROJECT --device-description "..." --intended-use "..."
```

**Prevention**: Complete predicate research and review before running `/fda:presub`

---

### 6. Control Character Corruption

**Error**: FDA eSTAR import fails with "Invalid XML" error

**Root Cause**: Control characters in device description or intended use

**Recovery Steps**:
```bash
# Check for control characters in metadata
cat -v ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# If found, regenerate with cleaned input
/fda:presub DQY --project YOUR_PROJECT \
  --device-description "$(echo 'YOUR_DESC' | tr -d '\000-\010\013-\014\016-\037')" \
  --intended-use "..."
```

**Prevention**: Avoid copying device descriptions from PDFs or external sources with formatting

---

### 7. Auto-Trigger Misfires

**Error**: Wrong questions selected (e.g., biocompatibility questions for non-patient-contacting device)

**Root Cause**: Device description keywords triggered incorrect auto-triggers

**Recovery Steps**:
```bash
# Review auto-triggers that fired
grep "auto_triggers_fired" ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# Manually edit presub_metadata.json to remove incorrect questions
nano ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# Regenerate XML with updated metadata
python3 plugins/fda-tools/scripts/estar_xml.py generate \
  --project YOUR_PROJECT \
  --template PreSTAR \
  --format real
```

**Prevention**: Use precise device descriptions that match intended regulatory scope

---

## Rollback Procedures

### Rollback to Previous Version

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

### Complete Regeneration

To start fresh with a clean slate:

```bash
# Backup existing files
cd ~/fda-510k-data/projects/YOUR_PROJECT
mkdir -p backup_$(date +%Y%m%d)
cp presub_* backup_$(date +%Y%m%d)/

# Remove existing Pre-Sub files
rm presub_plan.md presub_metadata.json presub_prestar.xml

# Regenerate from scratch
/fda:presub DQY --project YOUR_PROJECT \
  --device-description "Single-use vascular access catheter" \
  --intended-use "To provide temporary vascular access for medication delivery"
```

---

## Validation Checklist

After recovery, verify the following:

- [ ] presub_plan.md exists and is readable
- [ ] presub_metadata.json is valid JSON (test with `python3 -m json.tool`)
- [ ] presub_prestar.xml is valid XML (test with `xmllint --noout presub_prestar.xml`)
- [ ] Question count matches between metadata and plan document
- [ ] Meeting type is correct for device characteristics
- [ ] All auto-populated fields have values (not `[TODO: ...]`)
- [ ] No control characters in XML (test with `cat -v presub_prestar.xml | grep '\^'`)

---

## Diagnostic Tools

### Validate JSON Schema

```bash
# Install jsonschema validator
pip3 install jsonschema

# Validate presub_metadata.json
python3 << 'EOF'
import json
from jsonschema import validate, ValidationError

with open("plugins/fda-tools/data/schemas/presub_metadata_schema.json") as f:
    schema = json.load(f)

with open("~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json") as f:
    metadata = json.load(f)

try:
    validate(instance=metadata, schema=schema)
    print("✓ Metadata is valid")
except ValidationError as e:
    print(f"✗ Validation error: {e.message}")
EOF
```

### Check XML Well-Formedness

```bash
# Install xmllint (usually pre-installed on Linux/macOS)
xmllint --noout ~/fda-510k-data/projects/YOUR_PROJECT/presub_prestar.xml
```

### Verify Question Bank Integrity

```bash
# Run integration tests
cd plugins/fda-tools
python3 tests/test_prestar_integration.py
```

---

## Support Resources

- **Documentation**: `plugins/fda-tools/docs/PRESTAR_WORKFLOW.md`
- **JSON Schema**: `plugins/fda-tools/data/schemas/presub_metadata_schema.json`
- **Integration Tests**: `plugins/fda-tools/tests/test_prestar_integration.py`
- **Issue Tracker**: https://github.com/andrewlasiter/fda-predicate-assistant/issues

---

**Document Version**: 1.0
**Last Updated**: 2026-02-15
**Plugin Version**: v5.25.0+
