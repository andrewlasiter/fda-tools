# Output Path Validation Guide (FDA-111)

## Overview

This guide documents the output path validation system implemented to prevent arbitrary file write attacks (CWE-73).

## Security Model

All output file paths must pass validation before being written to:

1. **Allowlist Enforcement**: Only paths within allowed directories are permitted
2. **Path Traversal Protection**: Blocks `../` and encoded traversal attempts
3. **Sensitive Directory Blocking**: Prevents writes to `/etc/`, `/root/`, etc.
4. **Symlink Validation**: Detects symlinks pointing to blocked locations

## Quick Start

### For New Scripts

Use `SecureArgumentParser` for automatic path validation:

```python
from fda_tools.lib.secure_argparse import create_secure_parser

parser = create_secure_parser(description="My FDA script")

# Add output argument - automatically validated
parser.add_output_argument(
    '--output', '-o',
    default='./output/data.json',
    help='Output file path'
)

args = parser.parse_args()

# args.output is now a validated Path object
with open(args.output, 'w') as f:
    json.dump(data, f)
```

### For Existing Scripts

Add validation to existing argparse scripts:

```python
import argparse
from fda_tools.lib.secure_argparse import validate_parsed_output

# Existing argparse setup
parser = argparse.ArgumentParser()
parser.add_argument('--output', default='output.json')
parser.add_argument('--export', default='export.csv')
args = parser.parse_args()

# Add validation (one line)
args = validate_parsed_output(args, ['output', 'export'])

# Now args.output and args.export are validated Paths
```

### Manual Path Validation

For non-argparse use cases:

```python
from fda_tools.lib.path_validator import validate_output_path

# Validate a path
safe_path = validate_output_path("/path/to/output.json")

# With parent directory creation
safe_path = validate_output_path(
    "/path/to/output.json",
    create_parent=True
)
```

## Allowed Directories

By default, paths are allowed in:

- `~/fda-510k-data/` - Primary data directory
- `./` - Current working directory and subdirectories
- `/tmp/fda-*` - Temporary files with fda- prefix

## Blocked Directories

The following directories are always blocked:

- `/etc/` - System configuration
- `/root/` - Root user home
- `/var/` - Variable data
- `/usr/`, `/bin/`, `/sbin/` - System binaries
- `/boot/`, `/sys/`, `/proc/`, `/dev/` - System directories
- `~/.ssh/` - SSH keys
- `~/.aws/` - AWS credentials
- `~/.config/` - User configuration
- `~/.local/bin/` - User binaries

## Customizing Allowed Directories

For scripts needing custom allowed directories:

```python
from fda_tools.lib.path_validator import OutputPathValidator

validator = OutputPathValidator(
    allowed_dirs=[
        "~/fda-510k-data/",
        "./output/",
        "/mnt/shared/fda-data/"
    ]
)

safe_path = validator.validate_output_path("/mnt/shared/fda-data/export.json")
```

## Error Handling

```python
from fda_tools.lib.path_validator import (
    validate_output_path,
    PathValidationError
)

try:
    safe_path = validate_output_path("/etc/passwd")
except PathValidationError as e:
    print(f"Security error: {e}")
    # Log security event, alert admin, etc.
```

## Migration Checklist

For migrating existing scripts to path validation:

### Minimal Migration (Quick)

1. Add import:
   ```python
   from fda_tools.lib.secure_argparse import validate_parsed_output
   ```

2. After `args = parser.parse_args()`, add:
   ```python
   args = validate_parsed_output(args, ['output'])
   ```

### Full Migration (Recommended)

1. Replace `argparse.ArgumentParser()` with:
   ```python
   from fda_tools.lib.secure_argparse import create_secure_parser
   parser = create_secure_parser(description="...")
   ```

2. Replace `parser.add_argument('--output', ...)` with:
   ```python
   parser.add_output_argument('--output', ...)
   ```

3. No changes needed to `parser.parse_args()` - validation is automatic!

## Testing

Test your path validation:

```bash
# Should succeed
python3 my_script.py --output ~/fda-510k-data/output.json

# Should fail (blocked directory)
python3 my_script.py --output /etc/cron.d/backdoor

# Should fail (path traversal)
python3 my_script.py --output ../../../etc/passwd
```

## Scripts Requiring Migration

The following 30 scripts have `--output` arguments and require migration:

1. scripts/annual_report_tracker.py
2. scripts/approval_probability.py
3. scripts/backup_project.py
4. scripts/batch_seed.py
5. scripts/batchfetch.py
6. scripts/breakthrough_designation.py
7. scripts/build_structured_cache.py
8. scripts/clinical_requirements_mapper.py
9. scripts/compare_sections.py
10. scripts/competitive_dashboard.py
11. scripts/estar_xml.py
12. scripts/fetch_predicate_data.py
13. scripts/gap_analysis.py
14. scripts/knowledge_based_generator.py
15. scripts/markdown_to_html.py
16. scripts/maude_comparison.py
17. scripts/pas_monitor.py
18. scripts/pathway_recommender.py
19. scripts/pma_comparison.py
20. scripts/pma_intelligence.py
21. scripts/pma_section_extractor.py
22. scripts/predicate_extractor.py
23. scripts/quick_standards_generator.py
24. scripts/review_time_predictor.py
25. scripts/risk_assessment.py
26. scripts/run_audit.py
27. scripts/seed_test_project.py
28. scripts/signature_cli.py
29. scripts/supplement_tracker.py
30. scripts/timeline_predictor.py
31. scripts/verify_citations.py
32. scripts/web_predicate_validator.py

**Migration Priority**:
- P0 (URGENT): Scripts exposed to untrusted input
- P1 (HIGH): Scripts used in automated pipelines
- P2 (MEDIUM): Interactive scripts with user review

## Compliance

This control addresses:

- **CWE-73**: External Control of File Name or Path
- **OWASP Top 10**: A01:2021 - Broken Access Control
- **NIST SP 800-53**: AC-3 (Access Enforcement)

## References

- **Module**: `lib/path_validator.py`
- **Helpers**: `lib/secure_argparse.py`
- **Tests**: `tests/test_path_validator.py` (37 tests)
- **Issue**: FDA-111 - Unvalidated Output Path Security
