# FDA Project Backup & Restore — Quick Start Guide

**5-Minute Setup for Data Protection**

---

## Essential Commands

### Backup Single Project
```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts
python3 backup_project.py --project YOUR_PROJECT_NAME
```

### Backup All Projects
```bash
python3 backup_project.py --all
```

### List Available Backups
```bash
python3 backup_project.py --list-backups
```

### Restore from Backup
```bash
# Preview first (dry-run)
python3 restore_project.py --backup-file BACKUP.zip --dry-run

# Execute restore
python3 restore_project.py --backup-file BACKUP.zip
```

### Backup Before Updates
```bash
python3 update_manager.py --update-all --backup
```

---

## Backup Locations

**Default location:**
```
~/fda-510k-data/projects/backups/
```

**Backup filename format:**
```
{project_name}_backup_{YYYYMMDD_HHMMSS}.zip
```

**Example:**
```
batch_DQY_sterile_catheter_backup_20260217_143022.zip
```

---

## Common Scenarios

### Scenario 1: Weekly Backup
```bash
# Backup all projects every Monday
python3 backup_project.py --all
```

### Scenario 2: Pre-Submission Backup
```bash
# Backup specific project before submission
python3 backup_project.py --project batch_DQY_sterile_catheter
```

### Scenario 3: Recover Deleted Project
```bash
# Step 1: Find backup
python3 backup_project.py --list-backups

# Step 2: Verify backup
python3 restore_project.py --backup-file BACKUP.zip --verify-only

# Step 3: Restore
python3 restore_project.py --backup-file BACKUP.zip
```

### Scenario 4: Backup to External Drive
```bash
# Mount USB drive first
sudo mount /dev/sdb1 /media/external

# Backup to USB
python3 backup_project.py --all --output-dir /media/external/fda-backups
```

---

## Safety Checks

### Before Backup
- [ ] Project directory exists
- [ ] Sufficient disk space (check with `df -h`)

### Before Restore
- [ ] Verify backup integrity: `--verify-only`
- [ ] Preview restore: `--dry-run`
- [ ] Backup current state if overwriting

### Weekly Checklist
- [ ] Create full backup: `--all`
- [ ] Verify latest backup
- [ ] Copy to external location
- [ ] Clean up old backups (>30 days)

---

## Troubleshooting

### "Backup file already exists"
**Solution:** Wait 1 second and retry, or use custom output directory.

### "Projects already exist"
**Solution:** Use `--force` to overwrite, or backup current state first.

### "No space left on device"
**Solution:** Clean up old backups or use external drive.

### Missing progress bars
**Solution:** Install tqdm: `pip3 install tqdm` (optional)

---

## Automated Backups

### Setup Weekly Cron Job
```bash
# Edit crontab
crontab -e

# Add this line (runs every Sunday at 2 AM)
0 2 * * 0 cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts && python3 backup_project.py --all --quiet >> /var/log/fda-backup.log 2>&1
```

---

## Full Documentation

For detailed documentation, see:
- **Complete Guide:** `/docs/DATA_BACKUP_RECOVERY.md`
- **Implementation Details:** `/FDA-7-IMPLEMENTATION-COMPLETE.md`

---

## Support

```bash
# Help commands
python3 backup_project.py --help
python3 restore_project.py --help

# Run tests
python3 test_backup_restore.py
```

---

**Last Updated:** 2026-02-17
**Status:** Production Ready
