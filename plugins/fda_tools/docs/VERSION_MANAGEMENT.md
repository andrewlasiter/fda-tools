# Version Management Guide

This document describes the version management system for the FDA Tools plugin.

## Overview

The plugin uses a centralized version management system that ensures consistency across all project files:

- **Source of Truth**: `.claude-plugin/plugin.json`
- **Version Reader**: `scripts/version.py` (reads from plugin.json)
- **Documentation**: `CHANGELOG.md`, `README.md`

## Version Format

All versions follow [Semantic Versioning 2.0.0](https://semver.org/):

```
MAJOR.MINOR.PATCH

Example: 5.36.0
```

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## Checking Version Consistency

To check if all version references are consistent:

```bash
cd plugins/fda-tools
python3 scripts/check_version.py
```

### Verbose Output

```bash
python3 scripts/check_version.py --verbose
```

This shows:
- Current version from plugin.json
- Version found in each file
- Status (✓ match, ✗ mismatch, - not found)
- Detailed errors and warnings

### Exit Codes

- `0`: All versions match
- `1`: Version mismatch detected
- `2`: File not found or parse error

## Updating Version

To update the version atomically across all files:

```bash
python3 scripts/update_version.py X.Y.Z --message "Release description"
```

### Examples

**Major Release (Breaking Changes)**
```bash
python3 scripts/update_version.py 6.0.0 --message "Major refactor with breaking API changes"
```

**Minor Release (New Features)**
```bash
python3 scripts/update_version.py 5.37.0 --message "Add PMA timeline analysis feature"
```

**Patch Release (Bug Fixes)**
```bash
python3 scripts/update_version.py 5.36.1 --patch --message "Fix version consistency checker"
```

### Dry Run

To preview changes without modifying files:

```bash
python3 scripts/update_version.py 5.37.0 --dry-run
```

## What Gets Updated

The version updater modifies these files:

1. **`.claude-plugin/plugin.json`**
   - Updates `version` field
   - Preserves JSON formatting

2. **`CHANGELOG.md`**
   - Adds new version entry at the top
   - Includes current date
   - Adds your message (or TODO placeholder)

3. **`scripts/version.py`**
   - No changes needed (reads from plugin.json)
   - If hardcoded, updates `PLUGIN_VERSION` constant

## CI/CD Integration

### GitHub Actions

The version check runs automatically on every push and pull request:

```yaml
# .github/workflows/test.yml
jobs:
  version-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check version consistency
        run: python3 scripts/check_version.py --verbose
```

If versions are inconsistent, the CI pipeline will fail.

### Pre-commit Hooks

Install pre-commit hooks to catch version issues before committing:

**Option 1: Using pre-commit framework**
```bash
pip install pre-commit
pre-commit install
```

**Option 2: Manual Git hook installation**
```bash
./scripts/install-git-hooks.sh
```

The hook will run automatically and block commits if version files are inconsistent.

## Workflow Examples

### Standard Release Workflow

1. **Make your changes** to code and tests

2. **Update version and CHANGELOG**
   ```bash
   python3 scripts/update_version.py 5.37.0 --message "Add new feature XYZ"
   ```

3. **Verify consistency**
   ```bash
   python3 scripts/check_version.py -v
   ```

4. **Review changes**
   ```bash
   git diff
   ```

5. **Commit**
   ```bash
   git add .
   git commit -m "Release v5.37.0: Add new feature XYZ"
   ```

6. **Tag release**
   ```bash
   git tag -a v5.37.0 -m "Release v5.37.0"
   git push origin v5.37.0
   ```

### Hotfix Workflow

1. **Create hotfix branch**
   ```bash
   git checkout -b hotfix/5.36.1
   ```

2. **Fix the bug**

3. **Update version**
   ```bash
   python3 scripts/update_version.py 5.36.1 --patch --message "Fix critical bug in X"
   ```

4. **Commit and merge**
   ```bash
   git commit -am "Fix: Critical bug in X (v5.36.1)"
   git checkout main
   git merge hotfix/5.36.1
   ```

### README Version References

The version checker allows multiple versions in README.md (for historical reference like "NEW in v5.26.0").

It uses the **latest version found** for comparison. If there's a mismatch, update README manually:

```bash
# Find all version references
grep -n "v[0-9]\+\.[0-9]\+\.[0-9]\+" README.md

# Update to current version where needed
vim README.md
```

## Troubleshooting

### Version Mismatch Detected

```
✗ Version mismatch in CHANGELOG.md: found '5.35.0', expected '5.36.0'
```

**Solution**: Either update CHANGELOG.md manually or use the updater:
```bash
python3 scripts/update_version.py 5.36.0 --message "Your message"
```

### Multiple Versions in README

```
⚠ Multiple versions found in README.md: ['5.25.0', '5.26.0', '5.36.0'], using latest: 5.36.0
```

**Solution**: This is a warning, not an error. README can reference historical versions for feature documentation.

### Can't Find version.py

```
✗ Version file not found: /path/to/scripts/version.py
```

**Solution**: Run the checker from the correct directory:
```bash
cd plugins/fda-tools
python3 scripts/check_version.py
```

## Testing

Run the version management test suite:

```bash
pytest tests/test_version_consistency.py -v
```

Tests include:
- Version checker functionality
- Version updater functionality
- Atomic updates across files
- Edge cases and error handling
- Integration workflow tests

## API Reference

### VersionChecker Class

```python
from check_version import VersionChecker

checker = VersionChecker(project_root="/path/to/project")
is_consistent = checker.check_all()
checker.print_report(verbose=True)

# Access results
print(checker.version_sources)  # Dict of file -> version
print(checker.errors)           # List of error messages
print(checker.warnings)         # List of warning messages
```

### VersionUpdater Class

```python
from update_version import VersionUpdater

updater = VersionUpdater(project_root="/path/to/project")
success = updater.update_all(
    new_version="5.37.0",
    changelog_message="New features",
    dry_run=False
)
updater.print_summary()

# Access results
print(updater.changes_made)  # List of changes
print(updater.errors)        # List of errors
```

## Best Practices

1. **Always use the updater script** instead of manually editing version files
2. **Run checker before committing** version-related changes
3. **Use semantic versioning** correctly (major.minor.patch)
4. **Write meaningful CHANGELOG entries** that explain the "why" not just the "what"
5. **Tag releases** in Git with matching version numbers
6. **Keep README versions up to date** for major releases
7. **Use CI/CD checks** to prevent inconsistent versions from being merged
8. **Install pre-commit hooks** for early detection

## Related Files

- `/scripts/check_version.py` - Version consistency checker
- `/scripts/update_version.py` - Atomic version updater
- `/scripts/install-git-hooks.sh` - Git hooks installer
- `/.pre-commit-config.yaml` - Pre-commit framework config
- `/.github/workflows/test.yml` - CI/CD configuration
- `/tests/test_version_consistency.py` - Test suite
- `/docs/VERSION_MANAGEMENT.md` - This document

## See Also

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Git Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
