# FDA Data Manifest JSON Schema

## Overview

This directory contains JSON Schema definitions for FDA project data manifest files (`data_manifest.json`). These schemas ensure data integrity, support validation, and enable safe migration across schema versions.

## Schema Files

### data_manifest.schema.json

**Version:** 1.0.0
**Standard:** JSON Schema Draft 2020-12
**Purpose:** Defines the structure, types, and constraints for FDA project data manifests used by both 510(k) and PMA projects.

## Schema Version History

### 1.0.0 (Current)

**Release Date:** 2026-02-17
**Breaking Changes:** Initial release

**Features:**
- Support for 510(k) project manifests
- Support for PMA project manifests
- Query caching with TTL tracking
- Change detection fingerprints
- Comprehensive validation constraints
- Required `schema_version` field for migration support

**Fields:**

#### Core Fields (All Projects)
- `schema_version` (required): Semantic version string (e.g., "1.0.0")
- `project`: Human-readable project name
- `created_at`: ISO 8601 timestamp (UTC) when manifest was created
- `last_updated`: ISO 8601 timestamp (UTC) of last update
- `product_codes`: Array of three-letter FDA product codes (uppercase)
- `queries`: Cached API query results indexed by query key

#### 510(k) Specific Fields
- `fingerprints`: Change detection fingerprints by product code
  - Tracks known K-numbers, clearance counts, recall counts, adverse events
  - Used by `change_detector.py` to identify new clearances

#### PMA Specific Fields
- `total_pmas`: Total number of PMA entries
- `total_sseds_downloaded`: Count of SSED PDFs downloaded
- `total_sections_extracted`: Count of PMAs with extracted sections
- `pma_entries`: PMA-specific cache entries indexed by PMA number
  - Approval data, SSED download status, extraction metadata
- `search_cache`: Cached PMA search results

## Usage

### Python Validation

```python
from manifest_validator import validate_manifest, validate_manifest_file

# Validate in-memory manifest
is_valid, errors = validate_manifest(manifest_dict, strict=False)
if not is_valid:
    for error in errors:
        print(f"  - {error}")

# Validate file
is_valid, errors = validate_manifest_file("/path/to/data_manifest.json")

# Strict mode (raises ValidationError on failure)
from manifest_validator import ValidationError
try:
    validate_manifest(manifest_dict, strict=True)
except ValidationError as e:
    print(f"Validation failed: {e}")
    for error in e.errors:
        print(f"  - {error}")
```

### CLI Validation

```bash
# Validate a manifest file
python3 lib/manifest_validator.py /path/to/data_manifest.json

# Check schema version compatibility
python3 lib/manifest_validator.py /path/to/data_manifest.json --check-version

# Repair common validation issues
python3 lib/manifest_validator.py /path/to/data_manifest.json --repair

# Save repaired manifest
python3 lib/manifest_validator.py /path/to/data_manifest.json --repair --output repaired_manifest.json
```

### Migration

```bash
# Migrate a single project
python3 scripts/migrate_manifest.py --project my_project

# Migrate all projects
python3 scripts/migrate_manifest.py --all-projects

# Dry-run (preview changes)
python3 scripts/migrate_manifest.py --project my_project --dry-run

# Migrate PMA cache
python3 scripts/migrate_manifest.py --pma-cache
```

## Field Reference

### Query Entry Structure

```json
{
  "classification:DQY": {
    "fetched_at": "2024-01-15T09:00:00+00:00",
    "ttl_hours": 168,
    "source": "openFDA",
    "total_matches": 1,
    "summary": {
      "device_name": "Cardiovascular Catheter",
      "device_class": "2"
    },
    "api_cache_key": "classification_dqy_12345"
  }
}
```

### Fingerprint Entry Structure

```json
{
  "DQY": {
    "product_code": "DQY",
    "last_updated": "2024-01-15T09:00:00+00:00",
    "known_k_numbers": ["K241234", "K231234"],
    "total_clearances": 2,
    "latest_clearance_date": "2024-01-10",
    "total_recalls": 0,
    "total_adverse_events": 5,
    "deaths": 0,
    "injuries": 2,
    "malfunctions": 3
  }
}
```

### PMA Entry Structure

```json
{
  "P170019": {
    "pma_number": "P170019",
    "first_cached_at": "2024-01-15T08:30:00+00:00",
    "last_updated": "2024-01-15T09:00:00+00:00",
    "pma_approval_fetched_at": "2024-01-15T08:35:00+00:00",
    "device_name": "Test Device",
    "applicant": "Test Company",
    "product_code": "NMH",
    "decision_date": "2017-05-15",
    "advisory_committee": "CV",
    "supplement_count": 3,
    "ssed_downloaded": true,
    "ssed_filepath": "/path/to/ssed.pdf",
    "ssed_file_size_kb": 2500,
    "ssed_url": "https://www.accessdata.fda.gov/...",
    "ssed_downloaded_at": "2024-01-15T08:40:00+00:00",
    "sections_extracted": true,
    "section_count": 12,
    "total_word_count": 45000,
    "sections_extracted_at": "2024-01-15T08:50:00+00:00"
  }
}
```

## Validation Rules

### Pattern Constraints

- `schema_version`: Must match `^\d+\.\d+\.\d+$` (semantic versioning)
- `product_codes` items: Must match `^[A-Z]{3}$` (three uppercase letters)
- `known_k_numbers` items: Must match `^K\d{6}$` (K followed by 6 digits)
- `pma_number`: Must match `^P\d{6}[A-Z]?$` (P followed by 6 digits, optional letter)
- Timestamps: Must be ISO 8601 format with UTC timezone

### Type Constraints

- `ttl_hours`: Integer, 0-8760 (max 1 year)
- `total_matches`, `total_pmas`, counts: Non-negative integers
- `section_count`: 0-15 (PMA SSED sections)
- `source`: Enum of ["openFDA", "FDA API", "manual"]

### Required Fields

- **Top-level:** `schema_version` (all other fields optional)
- **Query entry:** `fetched_at`, `ttl_hours`, `source`
- **Fingerprint entry:** `product_code`, `last_updated`
- **PMA entry:** `pma_number`, `first_cached_at`
- **Search cache entry:** `results`, `fetched_at`, `result_count`

## Migration Path

### Legacy (no version) → 1.0.0

**Changes:**
- Add `schema_version` field
- Add/fix timezone information in all timestamps
- Normalize product codes to uppercase
- Add default timestamps if missing
- Validate all field types and patterns

**Migration Command:**
```bash
python3 scripts/migrate_manifest.py --project my_project
```

### Future Migrations

Schema migrations will follow semantic versioning:
- **Patch (1.0.x → 1.0.y):** Bug fixes, no structural changes
- **Minor (1.x.0 → 1.y.0):** New optional fields, backward compatible
- **Major (x.0.0 → y.0.0):** Breaking changes, migration required

## Best Practices

### For Developers

1. **Always validate on load:** Call `validate_manifest()` when loading manifests
2. **Add schema_version:** Use `add_schema_version()` for legacy manifests
3. **Check compatibility:** Use `check_schema_version_compatibility()` before operations
4. **Atomic writes:** Use temp-file-then-rename pattern (already in place)
5. **Backup before migration:** Keep `.bak` copies of manifests

### For Users

1. **Run migration before updates:** Ensure manifests are at current schema version
2. **Use --dry-run first:** Preview migration changes before applying
3. **Validate after manual edits:** Run `manifest_validator.py` after hand-editing
4. **Check validation errors:** Address warnings to ensure data integrity

## Error Messages

The validator provides clear error messages with context:

```
Missing required field 'schema_version' at root
Type mismatch at 'product_codes': expected array, got string
Pattern mismatch at 'product_codes.0': 'dqy' does not match pattern '^[A-Z]{3}$'
Additional property not allowed at 'queries.test': unknown_field
```

## Testing

Run the comprehensive test suite:

```bash
# Run all validation tests (41 tests)
python3 -m pytest tests/test_manifest_validator.py -v

# Run specific test class
python3 -m pytest tests/test_manifest_validator.py::TestBasicValidation -v

# Run with coverage
python3 -m pytest tests/test_manifest_validator.py --cov=lib/manifest_validator
```

## Dependencies

- **Python 3.8+**: Required for type hints and modern syntax
- **jsonschema 4.0+**: Required for JSON Schema Draft 2020-12 validation
  ```bash
  pip install jsonschema
  ```

## Integration Points

### fda_data_store.py

Validates manifests on load:
- Adds `schema_version` to legacy manifests
- Logs validation warnings (non-strict mode)
- Creates new manifests with schema version

### pma_data_store.py

Validates PMA manifests on load:
- Same behavior as fda_data_store.py
- Supports PMA-specific fields

### change_detector.py

Uses fingerprint structure:
- Relies on validated fingerprint fields
- Expects typed and validated K-numbers, timestamps

### update_manager.py

Scans manifests across projects:
- Benefits from consistent structure
- Can rely on validated timestamps for TTL

## Support

For issues or questions:
1. Check validation error messages for specific field issues
2. Run `--repair` mode to auto-fix common problems
3. Review schema file for field requirements
4. Check test suite for usage examples
5. Run migration for legacy manifests

## License

Part of the FDA Tools project. See main project LICENSE file.
