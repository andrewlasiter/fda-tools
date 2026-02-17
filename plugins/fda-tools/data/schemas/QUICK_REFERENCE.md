# data_manifest.json Quick Reference Card

## Validation Commands

```bash
# Validate a manifest
python3 lib/manifest_validator.py data_manifest.json

# Check schema version
python3 lib/manifest_validator.py data_manifest.json --check-version

# Auto-repair issues
python3 lib/manifest_validator.py data_manifest.json --repair --output fixed.json
```

## Migration Commands

```bash
# Migrate single project (preview)
python3 scripts/migrate_manifest.py --project my_project --dry-run

# Migrate single project (apply)
python3 scripts/migrate_manifest.py --project my_project

# Migrate all projects
python3 scripts/migrate_manifest.py --all-projects

# Migrate PMA cache
python3 scripts/migrate_manifest.py --pma-cache
```

## Python API

```python
# Import
from manifest_validator import (
    validate_manifest,
    validate_manifest_file,
    get_schema_version,
    check_schema_version_compatibility,
    create_minimal_manifest,
    validate_and_repair,
)

# Validate in-memory
is_valid, errors = validate_manifest(manifest_dict, strict=False)

# Validate file
is_valid, errors = validate_manifest_file("path/to/manifest.json")

# Get version
version = get_schema_version(manifest_dict)  # Returns "1.0.0" or None

# Check compatibility
is_compatible, msg = check_schema_version_compatibility(manifest_dict)

# Create new manifest
manifest = create_minimal_manifest("project_name")

# Auto-repair
repaired, changes = validate_and_repair(manifest_dict)
```

## Required Fields

### All Manifests
- `schema_version` (string, format: "1.0.0")

### Query Entries
- `fetched_at` (ISO 8601 timestamp with timezone)
- `ttl_hours` (integer, 0-8760)
- `source` (enum: "openFDA" | "FDA API" | "manual")

### Fingerprint Entries
- `product_code` (3 uppercase letters)
- `last_updated` (ISO 8601 timestamp)

### PMA Entries
- `pma_number` (format: P###### or P######X)
- `first_cached_at` (ISO 8601 timestamp)

## Pattern Constraints

| Field | Pattern | Example |
|-------|---------|---------|
| schema_version | `^\d+\.\d+\.\d+$` | "1.0.0" |
| product_code | `^[A-Z]{3}$` | "DQY" |
| k_number | `^K\d{6}$` | "K241234" |
| pma_number | `^P\d{6}[A-Z]?$` | "P170019" |
| timestamp | ISO 8601 with TZ | "2024-01-15T09:00:00+00:00" |

## Common Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| Missing required field 'schema_version' | Old manifest | Run migration or add field |
| Type mismatch: expected array, got string | Wrong type | Convert to correct type |
| Pattern mismatch: 'dqy' does not match | Lowercase code | Use uppercase "DQY" |
| Additional property not allowed | Extra field | Remove unknown field |
| Invalid JSON | Syntax error | Fix JSON syntax |

## Minimal Valid Manifest

```json
{
  "schema_version": "1.0.0"
}
```

## Example 510(k) Manifest

```json
{
  "schema_version": "1.0.0",
  "project": "my_510k_project",
  "created_at": "2024-01-15T08:30:00+00:00",
  "last_updated": "2024-01-15T10:45:00+00:00",
  "product_codes": ["DQY", "OVE"],
  "queries": {
    "classification:DQY": {
      "fetched_at": "2024-01-15T09:00:00+00:00",
      "ttl_hours": 168,
      "source": "openFDA",
      "total_matches": 1,
      "summary": {
        "device_name": "Cardiovascular Catheter",
        "device_class": "2"
      }
    }
  },
  "fingerprints": {
    "DQY": {
      "product_code": "DQY",
      "last_updated": "2024-01-15T09:00:00+00:00",
      "known_k_numbers": ["K241234", "K231234"],
      "total_clearances": 2,
      "latest_clearance_date": "2024-01-10",
      "total_recalls": 0,
      "total_adverse_events": 5
    }
  }
}
```

## Example PMA Manifest

```json
{
  "schema_version": "1.0.0",
  "created_at": "2024-01-15T08:30:00+00:00",
  "last_updated": "2024-01-15T10:45:00+00:00",
  "total_pmas": 1,
  "total_sseds_downloaded": 1,
  "total_sections_extracted": 1,
  "pma_entries": {
    "P170019": {
      "pma_number": "P170019",
      "first_cached_at": "2024-01-15T08:30:00+00:00",
      "last_updated": "2024-01-15T09:00:00+00:00",
      "device_name": "Test Device",
      "applicant": "Test Company",
      "product_code": "NMH",
      "decision_date": "2017-05-15",
      "ssed_downloaded": true,
      "sections_extracted": true,
      "section_count": 12
    }
  }
}
```

## Testing

```bash
# Run all tests
python3 -m pytest tests/test_manifest_validator.py -v

# Run specific test class
python3 -m pytest tests/test_manifest_validator.py::TestBasicValidation -v

# Show coverage
python3 -m pytest tests/test_manifest_validator.py --cov-report=term-missing
```

## Troubleshooting

### Problem: "jsonschema package required"
**Solution:** Install jsonschema
```bash
pip install jsonschema
```

### Problem: "Schema file not found"
**Solution:** Ensure you're running from the correct directory
```bash
cd /path/to/plugins/fda-tools
python3 lib/manifest_validator.py ...
```

### Problem: Legacy manifest fails validation
**Solution:** Run migration first
```bash
python3 scripts/migrate_manifest.py --file data_manifest.json
```

### Problem: Validation errors after migration
**Solution:** Check error messages and fix manually, or use --repair
```bash
python3 lib/manifest_validator.py data_manifest.json --repair --output fixed.json
```

## Schema Location

**File:** `/plugins/fda-tools/data/schemas/data_manifest.schema.json`
**URL:** `https://fda-tools.claude.ai/schemas/data_manifest.schema.json` (future)

## Version Compatibility

| Manifest Version | Tool Version | Compatibility |
|-----------------|--------------|---------------|
| 1.0.0 | 1.0.x | ✓ Full |
| legacy (no version) | Any | ⚠️ Needs migration |
| 2.0.0+ | 1.0.x | ✗ Incompatible |

## Support Resources

- **Full Documentation:** `data/schemas/README.md`
- **Implementation Summary:** `FDA-59-IMPLEMENTATION-SUMMARY.md`
- **Test Suite:** `tests/test_manifest_validator.py`
- **Schema File:** `data/schemas/data_manifest.schema.json`
- **Validator Source:** `lib/manifest_validator.py`
- **Migration Tool:** `scripts/migrate_manifest.py`
