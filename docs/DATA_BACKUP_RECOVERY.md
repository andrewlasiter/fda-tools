# FDA Project Data Backup and Recovery Guide

Complete disaster recovery procedures for FDA 510(k) project data, including backup schedules, restoration procedures, and disaster recovery scenarios.

## Table of Contents

1. [Overview](#overview)
2. [Backup Fundamentals](#backup-fundamentals)
3. [Backup Procedures](#backup-procedures)
4. [Restore Procedures](#restore-procedures)
5. [Disaster Recovery Scenarios](#disaster-recovery-scenarios)
6. [Backup Schedule Recommendations](#backup-schedule-recommendations)
7. [Backup Storage Recommendations](#backup-storage-recommendations)
8. [Automated Backup Integration](#automated-backup-integration)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Topics](#advanced-topics)

---

## Overview

The FDA-Tools backup system provides enterprise-grade data protection for 510(k) submission projects with:

- **SHA-256 checksum verification** for data integrity
- **Timestamped archives** for version control
- **Selective restore** capabilities
- **Atomic operations** with automatic rollback
- **Pre-update backup integration**

### What Gets Backed Up

All project files in `~/fda-510k-data/projects/{project_name}/`:

```
project_name/
├── device_profile.json          # Device specifications
├── review.json                  # Predicate review data
├── se_comparison.md             # Substantial equivalence table
├── standards_lookup.json        # Applicable standards
├── literature_cache.json        # PubMed articles
├── safety_cache/                # MAUDE data
├── calculations/                # Shelf life, sample sizes
├── source_device_text_*.txt     # Raw 510(k) PDFs
├── data_manifest.json           # API cache manifest
├── audit_log.jsonl              # Change audit log
└── ...all other project files
```

### Backup Format

```
{project_name}_backup_{timestamp}.zip
├── metadata.json                # Backup version, timestamp, checksums
├── checksums.txt                # File-level SHA-256 hashes
└── projects/
    └── {project_name}/
        └── ...all project files
```

**Example filename:** `batch_DQY_sterile_catheter_backup_20260217_143022.zip`

---

## Backup Fundamentals

### Checksum Verification

Every file is checksummed with SHA-256 before archiving:

```bash
# Verify backup integrity
python3 scripts/backup_project.py --verify ~/backups/project_backup.zip
```

Output:
```
✅ Backup verification PASSED: project_backup.zip
   Projects: batch_DQY_sterile_catheter
   Total files: 47
   Timestamp: 2026-02-17T14:30:22.123456+00:00
```

### Metadata Tracking

Each backup includes `metadata.json` with full provenance:

```json
{
  "backup_version": "1.0.0",
  "backup_timestamp": "2026-02-17T14:30:22.123456+00:00",
  "projects": ["batch_DQY_sterile_catheter"],
  "total_projects": 1,
  "total_files": 47,
  "checksums": {
    "batch_DQY_sterile_catheter/device_profile.json": "a3b2c1d4...",
    "batch_DQY_sterile_catheter/review.json": "e5f6g7h8...",
    ...
  },
  "created_by": "fda-tools/backup_project.py",
  "schema": {
    "version": "1.0",
    "description": "FDA project backup with integrity verification"
  }
}
```

---

## Backup Procedures

### Single Project Backup

**Basic Usage:**
```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts

# Backup single project (default output: ~/fda-510k-data/projects/backups/)
python3 backup_project.py --project batch_DQY_sterile_catheter
```

**Custom Output Directory:**
```bash
# Backup to external drive
python3 backup_project.py --project batch_DQY_sterile_catheter \
  --output-dir /media/external/fda-backups
```

**Skip Verification (faster, less safe):**
```bash
# Skip integrity verification after creation (NOT recommended for production)
python3 backup_project.py --project batch_DQY_sterile_catheter --verify-only
```

### All Projects Backup

**Backup Everything:**
```bash
# Creates: all_projects_backup_20260217_143022.zip
python3 backup_project.py --all
```

**Custom Output:**
```bash
# Backup all projects to network share
python3 backup_project.py --all --output-dir /mnt/network-share/backups
```

### List Available Backups

```bash
# List all backups in default directory
python3 backup_project.py --list-backups

# List backups in custom directory
python3 backup_project.py --list-backups --output-dir /media/external/fda-backups
```

Output:
```
📦 Available Backups (3):
================================================================================

  File: batch_DQY_sterile_catheter_backup_20260217_143022.zip
  Size: 2.45 MB
  Created: 2026-02-17T14:30:22.123456+00:00
  Projects: batch_DQY_sterile_catheter
  Total files: 47

  File: all_projects_backup_20260216_090000.zip
  Size: 128.73 MB
  Created: 2026-02-16T09:00:00.000000+00:00
  Projects: batch_CFR_ivd, batch_DPS_wireless_connected, batch_DQY_sterile_catheter, ...
  Total files: 1,234
```

### Scripted Backup (JSON Output)

```bash
# JSON output for automation
python3 backup_project.py --all --quiet > backup_result.json
```

---

## Restore Procedures

### Basic Restore

**Restore All Projects from Backup:**
```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts

python3 restore_project.py --backup-file ~/fda-510k-data/projects/backups/all_projects_backup_20260217.zip
```

**Restore Single Project:**
```bash
python3 restore_project.py \
  --backup-file ~/backups/all_projects_backup_20260217.zip \
  --project batch_DQY_sterile_catheter
```

### Preview Restore (Dry Run)

**ALWAYS preview before restoring:**
```bash
python3 restore_project.py --backup-file backup.zip --dry-run
```

Output:
```
🔍 DRY RUN MODE — No files will be modified
================================================================================
🔍 DRY RUN SUMMARY
================================================================================
Would restore: batch_DQY_sterile_catheter, batch_GEI_simple_powered
Would overwrite: batch_DQY_sterile_catheter
Total files: 94
```

### Force Overwrite

**Overwrite existing projects:**
```bash
# CAUTION: This will DELETE existing project data
python3 restore_project.py --backup-file backup.zip --force
```

**Best Practice:** Always backup current state before force overwrite:
```bash
# Step 1: Backup current state
python3 backup_project.py --project batch_DQY_sterile_catheter

# Step 2: Restore from older backup
python3 restore_project.py --backup-file old_backup.zip --force
```

### List Backup Contents

```bash
# See what's in a backup before restoring
python3 restore_project.py --backup-file backup.zip --list-contents
```

Output:
```
📦 Backup Contents:
================================================================================
Backup file: all_projects_backup_20260217_143022.zip
Created: 2026-02-17T14:30:22.123456+00:00
Total projects: 9
Total files: 423
Total size: 67.45 MB

Projects:
  - batch_CFR_ivd (52 files)
  - batch_DPS_wireless_connected (38 files)
  - batch_DQY_sterile_catheter (47 files)
  - batch_FRO_combination_product (41 files)
  - batch_GCJ_reusable_surgical (55 files)
  - batch_GEI_simple_powered (33 files)
  - batch_OAP_home_use_otc (29 files)
  - batch_OVE_orthopedic_implant (68 files)
  - batch_QKQ_samd (60 files)
```

### Verify Backup Integrity

**Before restoring, verify integrity:**
```bash
python3 restore_project.py --backup-file backup.zip --verify-only
```

Output:
```
✅ Backup verification PASSED: backup.zip
   Projects: batch_DQY_sterile_catheter, batch_GEI_simple_powered
   Total files: 80
```

### Custom Target Directory

```bash
# Restore to custom location (not standard projects directory)
python3 restore_project.py \
  --backup-file backup.zip \
  --target-dir /tmp/restored-projects
```

### Fast Restore (Skip Checksum Verification)

**NOT recommended for production:**
```bash
# Skip checksum verification (faster but less safe)
python3 restore_project.py --backup-file backup.zip --no-checksum-verify
```

---

## Disaster Recovery Scenarios

### Scenario 1: Accidental Project Deletion

**Symptom:** User accidentally deleted `batch_DQY_sterile_catheter` project.

**Recovery Steps:**

1. **Identify most recent backup:**
   ```bash
   python3 backup_project.py --list-backups
   ```

2. **Verify backup integrity:**
   ```bash
   python3 restore_project.py \
     --backup-file ~/fda-510k-data/projects/backups/batch_DQY_backup_20260217.zip \
     --verify-only
   ```

3. **Preview restore:**
   ```bash
   python3 restore_project.py \
     --backup-file ~/fda-510k-data/projects/backups/batch_DQY_backup_20260217.zip \
     --dry-run
   ```

4. **Execute restore:**
   ```bash
   python3 restore_project.py \
     --backup-file ~/fda-510k-data/projects/backups/batch_DQY_backup_20260217.zip
   ```

**Recovery Time:** 1-2 minutes for typical project (50 files, 5 MB)

---

### Scenario 2: Disk Failure

**Symptom:** Hard drive failure, entire `~/fda-510k-data/projects/` directory lost.

**Prerequisites:**
- External backup location (USB drive, network share, cloud storage)

**Recovery Steps:**

1. **Mount external backup drive:**
   ```bash
   # Example: USB drive at /media/external
   ls /media/external/fda-backups/
   ```

2. **Verify backup availability:**
   ```bash
   python3 backup_project.py --list-backups --output-dir /media/external/fda-backups
   ```

3. **Restore all projects:**
   ```bash
   python3 restore_project.py \
     --backup-file /media/external/fda-backups/all_projects_backup_20260216.zip
   ```

4. **Verify restoration:**
   ```bash
   ls ~/fda-510k-data/projects/
   # Should show all restored projects
   ```

**Recovery Time:** 10-30 minutes for full portfolio (9 projects, 500 MB)

---

### Scenario 3: Corrupted Project Data

**Symptom:** Project files corrupted after system crash, `device_profile.json` shows JSON parsing errors.

**Recovery Steps:**

1. **Backup corrupted state (for forensics):**
   ```bash
   python3 backup_project.py \
     --project batch_DQY_sterile_catheter \
     --output-dir ~/corrupted-backups
   ```

2. **Restore from last known good backup:**
   ```bash
   # Find backup BEFORE corruption occurred
   python3 backup_project.py --list-backups

   # Restore (will fail due to existing corrupted files)
   python3 restore_project.py \
     --backup-file ~/fda-510k-data/projects/backups/batch_DQY_backup_20260216.zip \
     --dry-run

   # Force overwrite corrupted files
   python3 restore_project.py \
     --backup-file ~/fda-510k-data/projects/backups/batch_DQY_backup_20260216.zip \
     --force
   ```

**Recovery Time:** 2-3 minutes

---

### Scenario 4: Pre-Update Rollback

**Symptom:** Batch update with `update_manager.py` introduced data errors, need to rollback.

**Prevention (use `--backup` flag):**
```bash
# ALWAYS backup before updates
python3 update_manager.py --update-all --backup
```

**Recovery Steps (if backup was created):**

1. **Locate pre-update backup:**
   ```bash
   python3 backup_project.py --list-backups
   # Look for backup created just before update (matching timestamp)
   ```

2. **Restore pre-update state:**
   ```bash
   python3 restore_project.py \
     --backup-file ~/fda-510k-data/projects/backups/all_projects_backup_20260217_140000.zip \
     --force
   ```

**Recovery Time:** 5-15 minutes for all projects

---

### Scenario 5: Partial Restore (Selective Files)

**Symptom:** Only need to restore specific project from multi-project backup.

**Recovery Steps:**

1. **List backup contents:**
   ```bash
   python3 restore_project.py \
     --backup-file all_projects_backup_20260217.zip \
     --list-contents
   ```

2. **Restore only target project:**
   ```bash
   python3 restore_project.py \
     --backup-file all_projects_backup_20260217.zip \
     --project batch_DQY_sterile_catheter
   ```

**Recovery Time:** 1-2 minutes per project

---

## Backup Schedule Recommendations

### Minimum Backup Schedule (Small Teams)

| Frequency | Trigger | Command |
|-----------|---------|---------|
| **Weekly** | Every Monday 9 AM | `python3 backup_project.py --all` |
| **Before Updates** | When running `--update-all` | `python3 update_manager.py --update-all --backup` |
| **Before Submission** | Manual trigger | `python3 backup_project.py --project {name}` |

### Enterprise Backup Schedule (Large Teams)

| Frequency | Trigger | Retention |
|-----------|---------|-----------|
| **Daily** | Automated cron job | 7 days |
| **Weekly** | Every Sunday 2 AM | 4 weeks |
| **Monthly** | First day of month | 12 months |
| **Before Major Updates** | Manual trigger | Indefinite |
| **Before Submission** | Manual trigger | Indefinite |

### Automated Daily Backup (Cron Example)

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts && python3 backup_project.py --all --output-dir /media/external/fda-backups --quiet >> /var/log/fda-backup.log 2>&1
```

### Automated Weekly Cleanup (Remove Old Backups)

```bash
#!/bin/bash
# cleanup_old_backups.sh — Remove backups older than 30 days

BACKUP_DIR="$HOME/fda-510k-data/projects/backups"
find "$BACKUP_DIR" -name "*_backup_*.zip" -type f -mtime +30 -delete

echo "$(date): Cleaned up backups older than 30 days" >> /var/log/fda-backup-cleanup.log
```

Run weekly:
```bash
# Add to crontab
0 3 * * 0 /home/linux/cleanup_old_backups.sh
```

---

## Backup Storage Recommendations

### Storage Locations (3-2-1 Rule)

**Best Practice:** 3 copies, 2 media types, 1 offsite

1. **Primary (local disk):** `~/fda-510k-data/projects/backups/`
2. **Secondary (external USB):** `/media/external/fda-backups/`
3. **Offsite (cloud storage):** AWS S3, Google Drive, Dropbox, etc.

### Local Storage Setup

```bash
# Create backup directory
mkdir -p ~/fda-510k-data/projects/backups

# Set permissions
chmod 700 ~/fda-510k-data/projects/backups
```

### External USB Drive Setup

```bash
# Mount USB drive (example)
sudo mount /dev/sdb1 /media/external

# Create backup directory
mkdir -p /media/external/fda-backups

# Backup to USB
python3 backup_project.py --all --output-dir /media/external/fda-backups
```

### Cloud Storage (AWS S3 Example)

```bash
# Backup to local directory first
python3 backup_project.py --all --output-dir /tmp/backups

# Upload to S3
aws s3 cp /tmp/backups/ s3://my-fda-backups/ --recursive

# Verify upload
aws s3 ls s3://my-fda-backups/
```

### Network Share (NFS/SMB Example)

```bash
# Mount network share
sudo mount -t nfs server:/share /mnt/network-share

# Backup to network
python3 backup_project.py --all --output-dir /mnt/network-share/fda-backups
```

### Capacity Planning

**Typical Project Sizes:**
- Small project (GEI, simple powered): 1-5 MB
- Medium project (DQY, sterile catheter): 5-15 MB
- Large project (OVE, orthopedic implant): 15-50 MB
- Largest project (with PDFs, literature): 50-200 MB

**Storage Requirements (9 projects, 4 weeks retention):**
- Daily backups: ~500 MB × 28 days = 14 GB
- Weekly backups: ~500 MB × 4 weeks = 2 GB
- **Total:** ~16 GB (recommend 50 GB for safety margin)

---

## Automated Backup Integration

### Pre-Update Backup

**Always backup before batch updates:**
```bash
# Automatic backup before update
python3 update_manager.py --update-all --backup
```

Output:
```
📦 Creating backup before updates...
🔍 Scanning 9 projects for stale data...
✅ Backup created: ~/fda-510k-data/projects/backups/all_projects_backup_20260217_143022.zip

🔍 Found 3 projects with stale data
📊 Total stale queries: 12

[1/3] Project: batch_DQY_sterile_catheter (5 stale)
...
```

### CI/CD Integration

```bash
#!/bin/bash
# Example: Jenkins/GitHub Actions backup script

set -e  # Exit on error

# Navigate to scripts directory
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts

# Create timestamped backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
python3 backup_project.py --all --output-dir /backups/ci-backups --quiet > /tmp/backup_result_$TIMESTAMP.json

# Verify backup succeeded
BACKUP_STATUS=$(jq -r '.status' /tmp/backup_result_$TIMESTAMP.json)
if [ "$BACKUP_STATUS" != "success" ]; then
  echo "❌ Backup failed"
  exit 1
fi

# Extract backup file path
BACKUP_FILE=$(jq -r '.backup_file' /tmp/backup_result_$TIMESTAMP.json)
echo "✅ Backup created: $BACKUP_FILE"

# Upload to S3 (optional)
aws s3 cp "$BACKUP_FILE" s3://my-ci-backups/
```

---

## Troubleshooting

### Issue 1: "Backup file already exists"

**Error:**
```
ValueError: Backup file already exists: all_projects_backup_20260217_143022.zip
```

**Cause:** Backup with same timestamp already exists.

**Solutions:**

1. Wait 1 second and retry (timestamp will change)
2. Rename existing backup
3. Use custom output directory

```bash
# Solution 1: Retry after 1 second
sleep 1 && python3 backup_project.py --all

# Solution 2: Custom output directory
python3 backup_project.py --all --output-dir ~/backups-temp
```

---

### Issue 2: Checksum Verification Failures

**Error:**
```
❌ Backup verification FAILED: backup.zip
   Error: Corrupted file in archive: projects/batch_DQY/device_profile.json
```

**Cause:** File corruption during backup creation or storage media failure.

**Solutions:**

1. **Re-create backup:**
   ```bash
   python3 backup_project.py --project batch_DQY_sterile_catheter
   ```

2. **Check disk health:**
   ```bash
   # Check for disk errors
   sudo smartctl -a /dev/sda
   ```

3. **Try different storage location:**
   ```bash
   python3 backup_project.py --all --output-dir /media/external/backups
   ```

---

### Issue 3: Out of Disk Space

**Error:**
```
OSError: [Errno 28] No space left on device
```

**Solutions:**

1. **Check disk usage:**
   ```bash
   df -h ~/fda-510k-data/projects/
   ```

2. **Clean up old backups:**
   ```bash
   # Remove backups older than 30 days
   find ~/fda-510k-data/projects/backups/ -name "*_backup_*.zip" -mtime +30 -delete
   ```

3. **Backup to external drive:**
   ```bash
   python3 backup_project.py --all --output-dir /media/external/backups
   ```

---

### Issue 4: "Projects already exist" During Restore

**Error:**
```
ValueError: Projects already exist (use --force to overwrite): batch_DQY_sterile_catheter
```

**Cause:** Attempting to restore over existing project without `--force` flag.

**Solutions:**

1. **Backup existing data first:**
   ```bash
   python3 backup_project.py --project batch_DQY_sterile_catheter
   ```

2. **Use --force to overwrite:**
   ```bash
   python3 restore_project.py --backup-file backup.zip --force
   ```

3. **Restore to different location:**
   ```bash
   python3 restore_project.py --backup-file backup.zip --target-dir /tmp/restored
   ```

---

### Issue 5: Missing tqdm Progress Bars

**Symptom:** No progress bars during backup/restore.

**Cause:** `tqdm` package not installed.

**Solution:**
```bash
pip3 install tqdm
```

Or continue without progress bars (functionality not affected).

---

## Advanced Topics

### Incremental Backups (Not Yet Implemented)

**Future Enhancement:** Backup only changed files since last backup.

Current workaround: Use rsync for incremental backups:
```bash
rsync -av --progress ~/fda-510k-data/projects/ /media/external/fda-projects-mirror/
```

### Encrypted Backups (Not Yet Implemented)

**Future Enhancement:** AES-256 encryption for backup archives.

Current workaround: Use GPG for encryption:
```bash
# Create backup
python3 backup_project.py --all

# Encrypt backup
gpg --symmetric --cipher-algo AES256 \
  ~/fda-510k-data/projects/backups/all_projects_backup_20260217.zip

# Decrypt for restore
gpg --decrypt all_projects_backup_20260217.zip.gpg > backup.zip
python3 restore_project.py --backup-file backup.zip
```

### Backup Compression Tuning

Current compression: ZIP_DEFLATED with level 6 (balanced)

For faster backups (larger files):
```python
# Edit backup_project.py line 214
# Change: compresslevel=6 → compresslevel=3
```

For smaller backups (slower):
```python
# Change: compresslevel=6 → compresslevel=9
```

### Remote Backup Over SSH

```bash
# Backup and transfer in one command
python3 backup_project.py --all --output-dir /tmp/backups && \
  scp /tmp/backups/*.zip user@remote-server:/backups/
```

### Backup Retention Policy Enforcement

```python
#!/usr/bin/env python3
"""Enforce backup retention policy (7 daily, 4 weekly, 12 monthly)."""

import os
from pathlib import Path
from datetime import datetime, timedelta

BACKUP_DIR = Path.home() / "fda-510k-data/projects/backups"
DAILY_RETENTION = 7      # Keep 7 daily backups
WEEKLY_RETENTION = 4     # Keep 4 weekly backups
MONTHLY_RETENTION = 12   # Keep 12 monthly backups

def enforce_retention():
    backups = sorted(BACKUP_DIR.glob("*_backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)

    # Categorize backups
    daily = backups[:DAILY_RETENTION]
    weekly = [b for b in backups if (datetime.now() - datetime.fromtimestamp(b.stat().st_mtime)).days % 7 == 0][:WEEKLY_RETENTION]
    monthly = [b for b in backups if (datetime.now() - datetime.fromtimestamp(b.stat().st_mtime)).days % 30 == 0][:MONTHLY_RETENTION]

    keep = set(daily + weekly + monthly)

    # Delete old backups
    for backup in backups:
        if backup not in keep:
            print(f"Deleting old backup: {backup.name}")
            backup.unlink()

if __name__ == "__main__":
    enforce_retention()
```

---

## Summary Checklist

### Before Starting Project Work
- [ ] Verify backup directory exists: `~/fda-510k-data/projects/backups/`
- [ ] Test backup command: `python3 backup_project.py --project TEST --dry-run`
- [ ] Verify external backup location accessible (USB/network/cloud)

### Weekly Maintenance
- [ ] Create full backup: `python3 backup_project.py --all`
- [ ] Verify latest backup: `python3 restore_project.py --verify-only --backup-file latest.zip`
- [ ] Copy to external location: `cp backups/*.zip /media/external/`
- [ ] Clean up old backups (>30 days)

### Before Critical Operations
- [ ] **Before updates:** `python3 update_manager.py --update-all --backup`
- [ ] **Before submission:** `python3 backup_project.py --project {name}`
- [ ] **Before manual edits:** `python3 backup_project.py --project {name}`

### After Disaster
- [ ] Verify backup integrity: `--verify-only`
- [ ] Preview restore: `--dry-run`
- [ ] Execute restore: `--force` (if needed)
- [ ] Verify restoration: check project files

---

## Support and Resources

- **Backup Script:** `/plugins/fda-tools/scripts/backup_project.py`
- **Restore Script:** `/plugins/fda-tools/scripts/restore_project.py`
- **Update Manager:** `/plugins/fda-tools/scripts/update_manager.py`

For assistance, review script help:
```bash
python3 backup_project.py --help
python3 restore_project.py --help
```
