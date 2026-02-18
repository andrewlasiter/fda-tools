# Error Recovery Guide

## Overview

This document provides error recovery procedures for all major FDA Tools plugin
scripts. Each section covers common failure modes, recovery steps, and
prevention strategies. For idempotency status of each script, see
[IDEMPOTENCY_MATRIX.md](./IDEMPOTENCY_MATRIX.md).

---

## Table of Contents

1. [batchfetch.py -- 510(k) Batch Fetch Tool](#1-batchfetchpy----510k-batch-fetch-tool)
2. [fda_api_client.py -- FDA API Client](#2-fda_api_clientpy----fda-api-client)
3. [pma_ssed_cache.py -- PMA SSED Downloader](#3-pma_ssed_cachepy----pma-ssed-downloader)
4. [data_refresh_orchestrator.py -- Data Refresh](#4-data_refresh_orchestratorpy----data-refresh)
5. [change_detector.py -- Smart Change Detector](#5-change_detectorpy----smart-change-detector)
6. [estar_xml.py -- eSTAR XML Generator](#6-estar_xmlpy----estar-xml-generator)
7. [pma_section_extractor.py -- SSED Section Extractor](#7-pma_section_extractorpy----ssed-section-extractor)
8. [seed_test_project.py -- Project Seeder](#8-seed_test_projectpy----project-seeder)
9. [backup_project.py / restore_project.py -- Backup & Restore](#9-backup_projectpy--restore_projectpy----backup--restore)
10. [cache_integrity.py -- Cache Integrity Checker](#10-cache_integritypy----cache-integrity-checker)
11. [PreSTAR XML Workflow (presub command)](#11-prestar-xml-workflow-presub-command)

---

## 1. batchfetch.py -- 510(k) Batch Fetch Tool

**Idempotency**: YES (safe to re-run; skips already-downloaded files)

### Common Errors

#### Network timeout during bulk download

**Error**: `ConnectionError`, `Timeout`, or incomplete CSV output

**Recovery**:
```bash
# Re-run with the same parameters; already-downloaded files are skipped
python3 batchfetch.py --date-range pmn96cur --years 2024 --product-codes DQY

# If using enrichment, partial results are preserved in the output directory
ls ~/fda-510k-data/projects/YOUR_PROJECT/enrichment_report.html
```

**Prevention**: Use `--rate-limit` to reduce request frequency on unstable connections.

#### Out of disk space during PDF download

**Error**: `OSError: [Errno 28] No space left on device`

**Recovery**:
```bash
# Check disk space
df -h ~/fda-510k-data/

# Clean up old downloads
rm -rf ~/fda-510k-data/downloads/old_batch_*

# Re-run (resumes from where it left off)
python3 batchfetch.py --date-range pmn96cur --years 2024
```

#### Invalid product code

**Error**: `No results found for product code XYZ`

**Recovery**:
```bash
# Verify product code exists
python3 fda_api_client.py --classify XYZ

# Check for typos -- enumerate all codes
python3 fda_api_client.py --get-all-codes | grep -i "xyz"
```

---

## 2. fda_api_client.py -- FDA API Client

**Idempotency**: YES (cached responses are reused; safe to call repeatedly)

### Common Errors

#### Rate limit exceeded (HTTP 429)

**Error**: `HTTP 429: Too Many Requests` or `Rate limit acquisition timeout`

**Recovery**:
```bash
# Check current rate limit status
python3 fda_api_client.py --health-check

# Wait for the rate limit window to reset (60 seconds)
sleep 60

# Retry the operation
python3 fda_api_client.py --lookup K241335
```

**Prevention**:
- Configure an API key for higher limits (240 req/min vs 40 req/min)
- Use `--rate-limit` flags where available
- Avoid running multiple scripts simultaneously (FDA-12 cross-process limiter helps)

#### Cache corruption

**Error**: `json.JSONDecodeError` or `checksum_mismatch` in logs

**Recovery**:
```bash
# Clear corrupted cache entries
python3 fda_api_client.py --clear-expired

# Or clear all cache and rebuild
python3 fda_api_client.py --clear

# Verify cache stats
python3 fda_api_client.py --stats
```

#### API disabled in settings

**Error**: `API disabled` in response

**Recovery**:
```bash
# Check settings file
cat ~/.claude/fda-tools.local.md

# Ensure openfda_enabled is not set to false
# Edit the file and remove or change: openfda_enabled: false
```

---

## 3. pma_ssed_cache.py -- PMA SSED Downloader

**Idempotency**: YES (skips already-downloaded PDFs unless --force is used)

### Common Errors

#### Cache size limit exceeded

**Error**: Downloads fail because cache is full

**Recovery**:
```bash
# Check current cache size
python3 pma_ssed_cache.py --show-manifest

# Clean cache to configured limit
python3 pma_ssed_cache.py --clean-cache

# Clean to a specific size (e.g., 200 MB)
python3 pma_ssed_cache.py --clean-cache --max-cache-mb 200
```

#### Insufficient disk space

**Error**: `Insufficient disk space` message

**Recovery**:
```bash
# Check free disk space
df -h ~/fda-510k-data/

# Clean SSED cache
python3 pma_ssed_cache.py --clean-cache --max-cache-mb 100

# Clean API cache
python3 fda_api_client.py --clear-expired
```

#### PDF validation failure

**Error**: `Invalid PDF content from URL (X bytes)` -- downloaded file is an HTML error page

**Recovery**:
```bash
# Force re-download
python3 pma_ssed_cache.py --pma P170019 --force

# Check if the PMA has an SSED (some older PMAs do not)
python3 pma_ssed_cache.py --pma P170019 --dry-run
```

#### HTTP 404 on all URL patterns

**Error**: `HTTP 404 on all 3 URL patterns`

**Root Cause**: Some PMAs (especially pre-2000 or supplements) do not have SSED PDFs
hosted on FDA servers.

**Recovery**: This is expected for some PMAs. No action needed. The manifest
will record the failure and the PMA can be excluded from future batches.

---

## 4. data_refresh_orchestrator.py -- Data Refresh

**Idempotency**: YES (TTL-based; only refreshes expired data)

### Common Errors

#### Stale data not refreshing

**Error**: Data appears outdated despite running refresh

**Recovery**:
```bash
# Force refresh of all data regardless of TTL
python3 data_refresh_orchestrator.py --schedule daily --force

# Check what data is stale
python3 data_refresh_orchestrator.py --status
```

#### Concurrent refresh conflicts

**Error**: `Lock acquisition timeout` or corrupted manifest

**Recovery**:
```bash
# Check for stale lock files
ls -la ~/fda-510k-data/.rate_limit.lock

# If the orchestrator crashed and left a lock, the lock file is safe to
# delete (fcntl locks are automatically released on process termination)
# But normally, just re-running will work

# Force refresh
python3 data_refresh_orchestrator.py --schedule daily
```

---

## 5. change_detector.py -- Smart Change Detector

**Idempotency**: YES (fingerprint comparison is non-destructive)

### Common Errors

#### Missing project directory

**Error**: `Project directory not found`

**Recovery**:
```bash
# List available projects
ls ~/fda-510k-data/projects/

# Create project if needed
mkdir -p ~/fda-510k-data/projects/YOUR_PROJECT

# Run change detection
python3 change_detector.py --project YOUR_PROJECT --product-code DQY
```

#### Fingerprint corruption

**Error**: Incorrect change detection (false positives/negatives)

**Recovery**:
```bash
# Reset fingerprints by clearing them from manifest
python3 -c "
import json
manifest_path = os.path.expanduser('~/fda-510k-data/projects/YOUR_PROJECT/data_manifest.json')
with open(manifest_path) as f:
    m = json.load(f)
m['fingerprints'] = {}
with open(manifest_path, 'w') as f:
    json.dump(m, f, indent=2)
print('Fingerprints reset')
"

# Next run will establish new baseline
python3 change_detector.py --project YOUR_PROJECT --product-code DQY
```

---

## 6. estar_xml.py -- eSTAR XML Generator

**Idempotency**: YES (regenerates XML from current project data)

### Common Errors

#### Missing project data files

**Error**: `device_profile.json not found` or incomplete XML output

**Recovery**:
```bash
# Check required files exist
ls -la ~/fda-510k-data/projects/YOUR_PROJECT/device_profile.json
ls -la ~/fda-510k-data/projects/YOUR_PROJECT/review.json

# If missing, run prerequisite data collection
/fda:research --product-code DQY --years 2024 --project YOUR_PROJECT

# Then regenerate XML
python3 estar_xml.py generate --project YOUR_PROJECT --format real
```

#### Invalid XML output

**Error**: FDA eSTAR portal rejects the generated XML

**Recovery**:
```bash
# Validate XML well-formedness
xmllint --noout ~/fda-510k-data/projects/YOUR_PROJECT/estar_submission.xml

# Check for control characters
cat -v ~/fda-510k-data/projects/YOUR_PROJECT/estar_submission.xml | grep '\^'

# Regenerate with clean data
python3 estar_xml.py generate --project YOUR_PROJECT --format real
```

---

## 7. pma_section_extractor.py -- SSED Section Extractor

**Idempotency**: YES (re-extraction overwrites previous results)

### Common Errors

#### PDF parsing failure

**Error**: `Failed to extract text from PDF` or empty sections

**Recovery**:
```bash
# Verify the PDF is valid
file ~/fda-510k-data/pma_cache/P170019/ssed.pdf

# Re-download the SSED
python3 pma_ssed_cache.py --pma P170019 --force

# Re-extract sections
python3 pma_section_extractor.py --pma P170019
```

#### OCR required but not installed

**Error**: `Tesseract not found` or image-based PDF with no text

**Recovery**:
```bash
# Install Tesseract OCR
sudo apt-get install tesseract-ocr  # Ubuntu/Debian
brew install tesseract               # macOS

# Re-extract with OCR enabled
python3 pma_section_extractor.py --pma P170019 --ocr
```

---

## 8. seed_test_project.py -- Project Seeder

**Idempotency**: PARTIAL (creates new project; overwrites if project exists with same name)

### Common Errors

#### API rate limit during seeding

**Error**: Seeding fails partway through data collection

**Recovery**:
```bash
# Wait for rate limit reset
sleep 60

# Re-run seeding (will retry failed API calls)
python3 seed_test_project.py --product-code DQY --project test_dqy
```

#### Incomplete project data

**Error**: Some data files are missing after seeding

**Recovery**:
```bash
# Check what files were created
ls -la ~/fda-510k-data/projects/test_dqy/

# Re-seed with --force to overwrite partial data
python3 seed_test_project.py --product-code DQY --project test_dqy --force
```

---

## 9. backup_project.py / restore_project.py -- Backup & Restore

**Idempotency**: YES (backup creates new archive; restore is non-destructive with --no-overwrite)

### Common Errors

#### Backup file too large

**Error**: `OSError: [Errno 28] No space left on device`

**Recovery**:
```bash
# Check project size before backup
du -sh ~/fda-510k-data/projects/YOUR_PROJECT/

# Free space and retry
python3 backup_project.py --project YOUR_PROJECT --output /path/with/space/
```

#### Restore to wrong directory

**Error**: Files restored to unexpected location

**Recovery**:
```bash
# Verify backup contents first
python3 restore_project.py --list --backup backup_file.zip

# Restore to specific directory
python3 restore_project.py --backup backup_file.zip --target ~/fda-510k-data/projects/
```

---

## 10. cache_integrity.py -- Cache Integrity Checker

**Idempotency**: YES (read-only verification; only modifies files when --repair is used)

### Common Errors

#### Multiple corrupt files detected

**Error**: `X files failed integrity check`

**Recovery**:
```bash
# Run integrity check to identify corrupt files
python3 cache_integrity.py --check ~/fda-510k-data/api_cache/

# Repair corrupt files (removes and re-fetches on next access)
python3 cache_integrity.py --repair ~/fda-510k-data/api_cache/

# Clear and rebuild if extensive corruption
python3 fda_api_client.py --clear
```

---

## 11. PreSTAR XML Workflow (presub command)

**Idempotency**: YES (regenerates all Pre-Sub files from current data)

### Common Errors

#### Question Bank Loading Failure

**Error**: `QUESTION_BANK_MISSING`, `QUESTION_BANK_INVALID`, or `QUESTION_BANK_SCHEMA_ERROR`

**Recovery**:
```bash
# Verify file exists
ls -lh plugins/fda-tools/data/question_banks/presub_questions.json

# Validate JSON syntax
python3 -m json.tool plugins/fda-tools/data/question_banks/presub_questions.json

# If missing, restore from git
git checkout plugins/fda-tools/data/question_banks/presub_questions.json
```

#### Metadata Generation Failure

**Error**: `ERROR: Metadata missing required fields`

**Recovery**:
```bash
# Check for existing metadata file
cat ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# Verify disk space
df -h ~/fda-510k-data/

# Regenerate by re-running command
/fda:presub DQY --project YOUR_PROJECT --device-description "..." --intended-use "..."
```

#### Schema Version Mismatch

**Error**: `WARNING: presub_metadata.json version X.X may be incompatible`

**Recovery**:
```bash
# Backup existing metadata
cp ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json \
   ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json.backup

# Regenerate with current version
/fda:presub DQY --project YOUR_PROJECT --device-description "..." --intended-use "..."
```

#### XML Generation Failure

**Error**: XML file not created

**Recovery**:
```bash
# Verify metadata is valid JSON
python3 -m json.tool ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# Manually trigger XML generation
python3 plugins/fda-tools/scripts/estar_xml.py generate \
  --project YOUR_PROJECT --template PreSTAR --format real
```

#### Auto-Trigger Misfires

**Error**: Wrong questions selected for device type

**Recovery**:
```bash
# Review auto-triggers
grep "auto_triggers_fired" ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# Edit metadata to correct question selection
nano ~/fda-510k-data/projects/YOUR_PROJECT/presub_metadata.json

# Regenerate XML
python3 plugins/fda-tools/scripts/estar_xml.py generate \
  --project YOUR_PROJECT --template PreSTAR --format real
```

---

## General Recovery Procedures

### Complete Data Directory Reset

If the entire data directory is corrupted:

```bash
# Backup what you can
cp -r ~/fda-510k-data/ ~/fda-510k-data.backup/

# Remove and recreate
rm -rf ~/fda-510k-data/
mkdir -p ~/fda-510k-data/{api_cache,pma_cache,projects}

# Rebuild as needed
python3 fda_api_client.py --test
```

### Cross-Process Rate Limit Reset

If the shared rate limiter is stuck:

```bash
# Remove lock and state files (safe -- locks are auto-released on process exit)
rm -f ~/fda-510k-data/.rate_limit.lock
rm -f ~/fda-510k-data/.rate_limit_state.json

# Verify reset
python3 fda_api_client.py --health-check
```

### Checking for Stale Processes

```bash
# Check for running FDA tools processes
ps aux | grep -E "(batchfetch|change_detector|data_refresh|pma_ssed)" | grep -v grep

# Kill stale processes if needed
kill <PID>
```

---

## Validation Checklist

After any recovery procedure, verify:

- [ ] `python3 fda_api_client.py --test` passes all endpoints
- [ ] `python3 fda_api_client.py --stats` shows healthy cache
- [ ] `python3 fda_api_client.py --health-check` shows no warnings
- [ ] Project data files are valid JSON (`python3 -m json.tool FILE`)
- [ ] XML files are well-formed (`xmllint --noout FILE`)
- [ ] No stale lock files remain

---

## Support Resources

- **Troubleshooting Guide**: `docs/TROUBLESHOOTING.md`
- **Quick Start**: `docs/QUICK_START.md`
- **Installation**: `docs/INSTALLATION.md`
- **Idempotency Matrix**: `docs/IDEMPOTENCY_MATRIX.md`

---

**Document Version**: 2.0
**Last Updated**: 2026-02-17
**Covers**: Top 10 scripts + PreSTAR workflow
