# Version Management Quick Reference

## Common Commands

### Check Version Consistency
```bash
python3 scripts/check_version.py
```

### Update Version
```bash
# New feature (minor)
python3 scripts/update_version.py 5.37.0 --message "Add feature X"

# Bug fix (patch)
python3 scripts/update_version.py 5.36.1 --message "Fix bug in Y"

# Breaking change (major)
python3 scripts/update_version.py 6.0.0 --message "Breaking: API redesign"
```

### Dry Run (Preview)
```bash
python3 scripts/update_version.py 5.37.0 --dry-run
```

### Install Git Hooks
```bash
./scripts/install-git-hooks.sh
```

## Files Tracked

| File | Purpose | Updated By |
|------|---------|------------|
| `.claude-plugin/plugin.json` | Source of truth | `update_version.py` |
| `scripts/version.py` | Version reader | Reads from plugin.json |
| `CHANGELOG.md` | Version history | `update_version.py` |
| `README.md` | Documentation | Manual updates |

## Version Format

```
MAJOR.MINOR.PATCH
  │      │     │
  │      │     └─ Bug fixes (5.36.0 → 5.36.1)
  │      └─────── New features (5.36.0 → 5.37.0)
  └────────────── Breaking changes (5.36.0 → 6.0.0)
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success / All versions match |
| 1 | Version mismatch detected |
| 2 | File not found or parse error |

## Troubleshooting

**Version mismatch?**
```bash
python3 scripts/update_version.py X.Y.Z --message "Fix version"
```

**Pre-commit hook failing?**
```bash
python3 scripts/check_version.py -v
# Fix issues, then:
git commit
```

**Bypass hook (not recommended)?**
```bash
git commit --no-verify
```

## Workflow

1. Make changes
2. `python3 scripts/update_version.py X.Y.Z --message "..."`
3. `python3 scripts/check_version.py -v`
4. `git commit -m "Release vX.Y.Z: ..."`
5. `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
6. `git push origin vX.Y.Z`

## Links

- [Full Documentation](VERSION_MANAGEMENT.md)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
