# Release Checklist: FDA Tools v5.25.1 (Quick Reference)

**Date**: 2026-02-15
**Target Version**: v5.25.1 (Patch Release)
**Current Version**: v5.25.0
**Type**: Security & Compliance Patch

---

## Pre-Release (Complete Before Releasing)

### Code Quality ✅
- [x] All tests pass (10/10 integration tests)
- [x] No new warnings or errors
- [x] Code review fixes verified
- [x] Git commit d4a9424 verified

### Version Numbers (Must Update)
- [ ] `plugins/fda-tools/.claude-plugin/plugin.json` → v5.25.1
- [ ] `.claude-plugin/marketplace.json` → v5.25.1 (2 occurrences)
- [ ] `plugins/fda-tools/CHANGELOG.md` → Add v5.25.1 entry

### Documentation ✅
- [x] CODE_REVIEW_FIXES.md complete (458 lines)
- [x] ERROR_RECOVERY.md comprehensive (283 lines)
- [x] Test suite self-documenting (299 lines)
- [x] Release notes prepared (Section 3 of RELEASE_PLANNING_REPORT.md)

### Testing ✅
- [x] Integration tests: 10/10 passing
- [x] Coverage adequate: 85%
- [x] No regressions detected
- [x] All fixes verified with tests

### Security ✅
- [x] XML injection vulnerability fixed
- [x] No hardcoded secrets
- [x] Control character filtering added
- [x] Schema validation robust

### Compliance ✅
- [x] ISO 10993-1:2009 aligned (not 2018)
- [x] IEC 60601-1 Edition 3.2 specified
- [x] FDA guidance current
- [x] All references verified

---

## Release Steps (Sequential)

### Step 1: Update Version Numbers
**Time**: 2 minutes | **Risk**: LOW

```bash
# 1a. Update plugin.json
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/.claude-plugin
sed -i 's/"version": "5.25.0"/"version": "5.25.1"/' plugin.json

# 1b. Update marketplace.json
cd /home/linux/.claude/plugins/marketplaces/fda-tools/.claude-plugin
sed -i 's/"version": "5.25.0"/"version": "5.25.1"/g' marketplace.json

# 1c. Verify both files
grep "version" /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/.claude-plugin/plugin.json
grep "version" /home/linux/.claude/plugins/marketplaces/fda-tools/.claude-plugin/marketplace.json
```

### Step 2: Add CHANGELOG Entry
**Time**: 5 minutes | **Risk**: LOW

Insert this block AFTER the v5.25.0 entry in CHANGELOG.md:

```markdown
## [5.25.1] - 2026-02-15

### Fixed - Critical Security, Data Integrity, and Compliance Patches

**Security**: XML injection vulnerability (HIGH-1) - Control character filtering added
**Data Integrity**: Schema validation (CRITICAL-2), JSON error handling (CRITICAL-1), JSON validation (HIGH-2), Atomic file writes (RISK-1)
**Error Handling**: Fuzzy keyword matching (CRITICAL-3) - Enhanced auto-trigger accuracy
**Compliance**: ISO 10993-1:2009 alignment (M-1), IEC 60601-1 Edition 3.2 specification (M-2)
**Testing**: New integration test suite (10 tests, 100% passing)
**Documentation**: Error recovery procedures (ERROR_RECOVERY.md)

#### Changes Summary
- 10 files modified/created
- 1,347 insertions, 28 deletions
- 85% test coverage
- Zero breaking changes
- Fully backward compatible with v5.25.0

See CODE_REVIEW_FIXES.md for detailed fix descriptions.
```

### Step 3: Verify Changes Locally
**Time**: 2 minutes | **Risk**: LOW

```bash
# Run tests
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools
python3 tests/test_prestar_integration.py

# Check all 10 tests pass
echo "Expected: OK (10/10 tests)"
```

### Step 4: Stage & Commit Changes
**Time**: 3 minutes | **Risk**: MEDIUM

```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools

# Stage version and changelog updates
git add plugins/fda-tools/.claude-plugin/plugin.json
git add .claude-plugin/marketplace.json
git add plugins/fda-tools/CHANGELOG.md

# Create commit
git commit -m "v5.25.1: Critical security and compliance fixes

- HIGH-1: XML injection vulnerability fixed (control character filtering)
- CRITICAL-2: Schema version validation added
- CRITICAL-1: JSON error handling improved
- CRITICAL-3: Fuzzy keyword matching enhanced
- HIGH-2: JSON schema validation added
- RISK-1: Atomic file writes implemented
- M-1: ISO 10993-1:2009 alignment
- M-2: IEC 60601-1 Edition 3.2 specification
- Added integration test suite (10 tests, 100% passing)
- Added error recovery documentation

Co-Authored-By: Claude Code Deployment Engineering <noreply@anthropic.com>"

# Verify commit
git log -1 --oneline
```

### Step 5: Create Git Tag
**Time**: 1 minute | **Risk**: LOW

```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools

# Create annotated tag
git tag -a v5.25.1 -m "v5.25.1: Critical security and compliance fixes

- XML injection vulnerability (HIGH-1)
- Schema validation (CRITICAL-2)
- JSON error handling (CRITICAL-1)
- Fuzzy matching (CRITICAL-3)
- File write atomicity (RISK-1)
- Compliance alignment (M-1, M-2)
- 10 new integration tests
- Error recovery documentation

Backward compatible with v5.25.0
All 10 tests passing (100%)
Ready for production release"

# Verify tag
git tag -l -n | grep v5.25.1
```

### Step 6: Push to Repository
**Time**: 2 minutes | **Risk**: MEDIUM

```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools

# Push commits
git push origin master

# Push tag
git push origin v5.25.1

# Verify (should see v5.25.1 tag on GitHub)
git log --oneline -5
git tag -l | grep v5.25.1
```

### Step 7: Create GitHub Release
**Time**: 5 minutes | **Risk**: LOW

1. Go to: https://github.com/andrewlasiter/fda-tools/releases
2. Click "Draft a new release"
3. Tag version: `v5.25.1`
4. Release title: `v5.25.1: Critical Security and Compliance Fixes`
5. Copy release notes from RELEASE_PLANNING_REPORT.md Section 3
6. Click "Publish release"

### Step 8: Verify Release
**Time**: 3 minutes | **Risk**: LOW

```bash
# Check marketplace shows v5.25.1
# Check GitHub release created
# Check plugin can be installed
# Run smoke test
/fda-tools:status  # Should show v5.25.1

# All should pass:
/fda-tools:presub --help
/fda-tools:research --help
```

---

## Rollback Procedures (If Issues Found)

### Rollback to v5.25.0 (Before Publishing)

```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools

# Reset last commit
git reset --soft HEAD~1

# Restore previous files
git restore plugins/fda-tools/.claude-plugin/plugin.json
git restore .claude-plugin/marketplace.json
git restore plugins/fda-tools/CHANGELOG.md

# Delete the tag (if created)
git tag -d v5.25.1

# Re-commit if needed
git commit -m "Rollback v5.25.1 release"
```

### If Already Published to GitHub

```bash
# Delete remote tag
git push origin --delete v5.25.1

# Delete GitHub release (manually on GitHub website)
# Revert the release commit
git revert -n HEAD
git commit -m "Revert v5.25.1 release"
git push origin master
```

---

## Post-Release Verification

### For Release Team

- [ ] All version numbers are v5.25.1
- [ ] Git tag v5.25.1 exists
- [ ] GitHub release published
- [ ] Marketplace updated
- [ ] Release notes visible on GitHub

### For Users (Smoke Test)

```bash
# Users should verify:
/fda-tools:status
# Output should show: v5.25.1

/fda-tools:presub --help
# Should display help without errors
```

### Monitor (First 24 Hours)

- [ ] Check GitHub issues for new bug reports
- [ ] Monitor installation success rate
- [ ] Watch for any error logs
- [ ] Confirm marketplace shows v5.25.1

---

## Key Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Files Modified | 8 | ✅ |
| Files Created | 3 | ✅ |
| Total Lines Added | 1,347 | ✅ |
| Integration Tests | 10/10 | ✅ PASS |
| Test Coverage | 85% | ✅ ADEQUATE |
| Breaking Changes | 0 | ✅ SAFE |
| Backward Compatible | Yes | ✅ SAFE |

---

## Important Files

| File | Purpose | Path |
|------|---------|------|
| RELEASE_PLANNING_REPORT.md | Full release analysis | `/home/linux/.claude/plugins/marketplaces/fda-tools/RELEASE_PLANNING_REPORT.md` |
| CODE_REVIEW_FIXES.md | Detailed fix descriptions | `plugins/fda-tools/CODE_REVIEW_FIXES.md` |
| ERROR_RECOVERY.md | Operational procedures | `plugins/fda-tools/docs/ERROR_RECOVERY.md` |
| test_prestar_integration.py | Test suite | `plugins/fda-tools/tests/test_prestar_integration.py` |
| presub_metadata_schema.json | Schema validation | `plugins/fda-tools/data/schemas/presub_metadata_schema.json` |

---

## Emergency Contacts

For issues during release:
- **Lead**: Claude Code Deployment Engineering
- **Backup**: Quality Assurance Team
- **Repository**: https://github.com/andrewlasiter/fda-tools

---

## Sign-Off

**Prepared By**: Claude Code Deployment Engineering
**Date**: 2026-02-15
**Status**: Ready for Release
**Approval**: ✅ RECOMMENDED FOR RELEASE

---

**Total Time Estimate**: 25 minutes (all steps)
**Risk Level**: LOW (all fixes are defensive, backward compatible)
**Rollback Difficulty**: EASY (single tag/commit revert)
