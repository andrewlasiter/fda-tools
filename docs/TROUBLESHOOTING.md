# FDA Tools Plugin - Troubleshooting Guide

Solutions to common issues and error messages.

For command-specific troubleshooting, see [plugins/fda-tools/docs/TROUBLESHOOTING.md](../plugins/fda-tools/docs/TROUBLESHOOTING.md).

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Command Issues](#command-issues)
- [API Issues](#api-issues)
- [Performance Issues](#performance-issues)
- [Data Issues](#data-issues)
- [Export Issues](#export-issues)
- [Common Error Messages](#common-error-messages)
- [Getting Help](#getting-help)

## Quick Diagnostics

### Run System Check

```
/fda-tools:status
```

This shows:
- Plugin version
- Data directory location
- Cache status
- API connectivity
- Recent activity

### Test Basic Functionality

```bash
# 1. Validate a known K-number
/fda:validate --k-number K240001

# 2. Test API connection
/fda:research --product-code DQY --limit 5

# 3. Check data directory
/fda:cache status
```

If all three work, your installation is healthy!

## Installation Issues

### "Command not found" Error

**Problem**: `/fda:research` returns "command not found"

**Solutions**:

1. **Verify plugin is installed**:
   ```bash
   ls ~/.claude/plugins/marketplaces/fda-tools/
   ```

2. **Check Claude Code version**:
   ```bash
   claude --version
   ```
   Requires v1.0.0+

3. **Restart Claude Code**:
   ```bash
   # Exit current session, then
   claude
   ```

4. **Reinstall plugin**:
   ```bash
   claude plugin install fda-tools@fda-tools
   ```

5. **Check plugin status**:
   ```
   /plugin list
   ```

### "No module named 'requests'" Error

**Problem**: Python import fails when running commands

**Solution**: Install Python dependencies:

```bash
cd ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/
pip3 install -r requirements.txt
```

**If pip3 not found**:
```bash
python3 -m pip install -r requirements.txt
```

**Common missing packages**:
- requests
- beautifulsoup4
- lxml
- pikepdf
- python-dateutil

### Permission Denied Errors

**Problem**: Cannot write to data directory

**Solutions**:

1. **Check directory exists**:
   ```bash
   ls -la ~/fda-510k-data/
   ```

2. **Create if missing**:
   ```bash
   mkdir -p ~/fda-510k-data
   ```

3. **Fix permissions**:
   ```bash
   chmod 755 ~/fda-510k-data
   chmod -R u+w ~/fda-510k-data/
   ```

4. **Use alternate directory**:
   ```
   /fda-tools:configure
   # Set writable directory
   ```

### Plugin Not Loading

**Problem**: Plugin installed but commands not available

**Checklist**:

- [ ] Plugin directory exists: `~/.claude/plugins/marketplaces/fda-tools/`
- [ ] Plugin.json is valid: Check `plugins/fda-tools/.claude-plugin/plugin.json`
- [ ] Claude Code restarted after installation
- [ ] No conflicting plugins with same command names
- [ ] File permissions allow reading plugin files

**Debug**:
```bash
# Check plugin structure
tree -L 3 ~/.claude/plugins/marketplaces/fda-tools/

# Verify plugin.json
cat ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/.claude-plugin/plugin.json
```

## Command Issues

### Research Not Finding Predicates

**Problem**: `/fda:research` returns no results

**Possible Causes**:

1. **Invalid product code**: Check at https://www.fda.gov/medical-devices/classify-your-medical-device/product-classification
2. **Too restrictive filters**: Remove `--years` or `--min-score` filters
3. **API connectivity**: Test with `/fda:validate --k-number K240001`
4. **Sparse data**: Some product codes have few clearances

**Solutions**:

```bash
# Start broad
/fda:research --product-code DQY

# Then narrow down
/fda:research --product-code DQY --years 2020-2024

# Check what's available
/fda:extract --product-codes DQY --years 2020-2024 --summary
```

### Pre-Check Low SRI Score

**Problem**: `/fda:pre-check` shows low Submission Readiness Index

**Common Causes**:

| SRI Range | Common Issues |
|-----------|---------------|
| 0-30 | Missing device data, no predicates selected |
| 31-50 | Sparse project data, missing sections |
| 51-70 | TODO placeholders, missing standards |
| 71-85 | Minor gaps, style issues |
| 86-100 | Ready for review |

**Solutions by Score Range**:

**SRI < 30**: Complete basic setup
```bash
# 1. Add device data
/fda:import --project PROJECT --device-profile device.json

# 2. Select predicates
/fda:review --project PROJECT

# 3. Generate comparison table
/fda:compare-se --project PROJECT
```

**SRI 31-50**: Add missing sections
```bash
# Check what's missing
/fda:gap-analysis --project PROJECT

# Draft missing sections
/fda:draft --section device-description
/fda:draft --section testing-bench
/fda:draft --section biocompatibility
```

**SRI 51-70**: Remove TODO placeholders
```bash
# Find all TODOs
grep -r "TODO\|FIXME\|XXX" ~/fda-510k-data/projects/PROJECT/

# Use draft command with project context
/fda:draft --section shelf-life --load-context
```

**SRI 71-85**: Polish and consistency
```bash
# Run consistency checks
/fda:consistency --project PROJECT

# Review simulator
/fda-review-simulator
```

### Draft Generating TODO Placeholders

**Problem**: `/fda:draft` creates sections with [TODO: ...] instead of real content

**Causes**:

1. Missing project data (device specs, predicates, test results)
2. Insufficient context loaded
3. Auto-triggers not detecting device type

**Solutions**:

**Load all project data first**:
```bash
# Make sure these exist
ls ~/fda-510k-data/projects/PROJECT/device_profile.json
ls ~/fda-510k-data/projects/PROJECT/review.json
ls ~/fda-510k-data/projects/PROJECT/se_comparison.md
```

**Use context flags**:
```bash
/fda:draft --section device-description --load-context --verbose
```

**Check auto-trigger detection**:
```bash
# Draft reports what triggers it detected
# Look for: "Auto-triggers: software, sterile, reprocessing"
```

**Manually provide data**:
```bash
# If project data incomplete, provide inline
/fda:draft --section device-description --device-name "MyDevice" --indications "intended use text"
```

### Extraction Incomplete

**Problem**: `/fda:extract` or `batchfetch` missing data

**Check**:

```bash
# 1. What was actually downloaded?
ls -lh ~/fda-510k-data/downloads/510k/

# 2. Check structured cache
/fda:cache status

# 3. Review extraction log
cat ~/fda-510k-data/logs/extraction.log
```

**Solutions**:

**Missing PDFs**:
```bash
# Force re-download
/fda:extract --product-codes DQY --years 2024 --force --no-cache

# Or skip PDFs if not available
/fda:extract --product-codes DQY --skip-downloads
```

**Incomplete enrichment**:
```bash
# Use full-auto mode for complete enrichment
/fda-tools:batchfetch --product-codes DQY --years 2024 --enrich --full-auto
```

**Parsing errors**:
```bash
# Some PDFs are scanned images, not text
# Use OCR flag (if available)
/fda:extract --product-codes DQY --ocr
```

## API Issues

### Rate Limit Exceeded

**Problem**: "429 Too Many Requests" from FDA API

**FDA API Limits**:
- **Without API key**: 240 requests/minute, 1,000/hour
- **With API key**: 1,000 requests/minute, 120,000/hour

**Solutions**:

1. **Wait 60 seconds and retry** (simplest)

2. **Get FDA API key** (free):
   ```bash
   # Get key at: https://open.fda.gov/apis/authentication/
   export FDA_API_KEY=your_key_here
   ```

3. **Enable smart caching**:
   ```
   /fda-tools:configure
   # Set auto_cache=true, cache_ttl=86400
   ```

4. **Use batch mode with delays**:
   ```bash
   # Automatically throttles requests
   /fda-tools:batchfetch --product-codes DQY --rate-limit
   ```

5. **Reduce concurrent requests**:
   ```bash
   export FDA_MAX_CONCURRENT=3
   ```

### API Connection Failed

**Problem**: Cannot connect to api.fda.gov

**Debug**:

```bash
# 1. Test basic connectivity
ping api.fda.gov

# 2. Test HTTPS
curl https://api.fda.gov/device/510k.json?limit=1

# 3. Check DNS
nslookup api.fda.gov
```

**Solutions**:

1. **Check internet connection**
2. **Disable VPN** (some VPNs block FDA API)
3. **Check firewall** (allow HTTPS to api.fda.gov)
4. **Try alternate network** (mobile hotspot)
5. **Wait for FDA API** (sometimes has outages)

**Check FDA API status**: https://open.fda.gov/apis/status/

### Timeout Errors

**Problem**: Requests timing out

**Solutions**:

```bash
# Increase timeout
export FDA_API_TIMEOUT=60

# For PDF downloads
export FDA_PDF_TIMEOUT=300

# Use cached data if available
/fda:extract --product-codes DQY --cached-only
```

## Performance Issues

### Slow Command Execution

**Problem**: Commands take >30 seconds

**Optimizations**:

1. **Enable caching**:
   ```
   /fda-tools:configure
   # Set auto_cache=true
   ```

2. **Use SSD for data directory**:
   ```bash
   # Move to SSD
   mv ~/fda-510k-data /path/to/ssd/fda-510k-data
   ln -s /path/to/ssd/fda-510k-data ~/fda-510k-data
   ```

3. **Use filters to reduce data**:
   ```bash
   # Instead of all years
   /fda:extract --product-codes DQY --years 2023-2024

   # Limit results
   /fda:research --product-code DQY --limit 50
   ```

4. **Close other applications** (free RAM)

5. **Clear old cache**:
   ```bash
   /fda:cache clear --older-than 90d
   ```

6. **Use smart updates instead of full refresh**:
   ```bash
   /fda-tools:update-data --smart
   ```

### High Memory Usage

**Problem**: Python process using too much RAM

**Solutions**:

1. **Process smaller batches**:
   ```bash
   # Instead of 1000 devices at once
   /fda:extract --product-codes DQY --years 2024 --limit 100
   ```

2. **Disable PDF processing**:
   ```bash
   /fda:extract --product-codes DQY --skip-pdfs
   ```

3. **Clear cache periodically**:
   ```bash
   /fda:cache clear
   ```

4. **Increase available RAM** (close other apps, upgrade RAM)

### Disk Space Full

**Problem**: Not enough disk space

**Check usage**:
```bash
du -sh ~/fda-510k-data/*
df -h ~
```

**Solutions**:

1. **Clear old downloads**:
   ```bash
   # Remove PDFs older than 6 months
   find ~/fda-510k-data/downloads -mtime +180 -delete
   ```

2. **Clear cache**:
   ```bash
   /fda:cache clear
   ```

3. **Archive old projects**:
   ```bash
   tar -czf old_projects.tar.gz ~/fda-510k-data/projects/OLD_PROJECT/
   rm -rf ~/fda-510k-data/projects/OLD_PROJECT/
   ```

4. **Move to larger disk**:
   ```bash
   /fda-tools:configure
   # Set new data directory on larger disk
   ```

## Data Issues

### Project Not Found

**Problem**: "Project PROJECT_NAME not found"

**Solutions**:

```bash
# 1. List available projects
ls ~/fda-510k-data/projects/

# 2. Check exact name (case-sensitive)
/fda:status

# 3. Create if missing
/fda:start --project PROJECT_NAME --product-code DQY
```

### Invalid K-Number Format

**Problem**: "K-number must be K + 6 digits"

**Valid formats**:
- **510(k)**: K240001 (K + 6 digits)
- **PMA**: P240001 (P + 6 digits)
- **De Novo**: DEN240001 (DEN + 6 digits)

**Invalid**:
- k240001 (lowercase)
- K24001 (5 digits)
- K2024001 (7 digits)

### Corrupt Cache

**Problem**: Strange errors, inconsistent data

**Solution**: Clear and rebuild cache:

```bash
# 1. Backup important data
cp -r ~/fda-510k-data/projects ~/projects_backup

# 2. Clear cache
/fda:cache clear

# 3. Rebuild
/fda-tools:update-data --force
```

## Export Issues

### eSTAR XML Validation Errors

**Problem**: Generated XML fails validation

**Common causes**:

1. Missing required fields
2. Invalid field formats
3. Template type mismatch

**Solutions**:

```bash
# 1. Validate first
/fda:estar validate --project PROJECT

# 2. Review validation report
cat ~/fda-510k-data/projects/PROJECT/estar_validation.md

# 3. Fill missing fields
/fda:import --project PROJECT --device-profile updated_profile.json

# 4. Re-export
/fda:export --project PROJECT --format estar
```

**Required fields by template**:

**nIVD (FDA 4062)**:
- Trade name
- Common name
- Device description
- Manufacturer
- Regulation number

**IVD (FDA 4078)**:
- All nIVD fields plus:
- Review panel
- Analyte/test

**PreSTAR (FDA 5064)**:
- For Pre-Submission meetings
- Meeting type
- Request date
- Product code

### Form 3881 Missing

**Problem**: eSTAR package missing Form 3881

**Solution**:

Form 3881 is auto-generated for Section 03 if:
1. Project has device data
2. Export includes `--sections 03` (or `--all`)

```bash
# Generate standalone Form 3881
/fda:draft --section form-3881

# Include in export
/fda:export --project PROJECT --sections 03 --format estar
```

### PDF Generation Fails

**Problem**: Cannot generate submission PDF

**Solutions**:

1. **Check PDF dependencies**:
   ```bash
   pip3 install pikepdf reportlab
   ```

2. **Use alternate format**:
   ```bash
   # Export as Word instead
   /fda:export --project PROJECT --format docx
   ```

3. **Check disk space**:
   ```bash
   df -h ~/fda-510k-data
   ```

## Common Error Messages

### "FileNotFoundError: device_profile.json"

**Cause**: Project missing required data files

**Solution**:
```bash
# Import device data
/fda:import --project PROJECT --device-profile device.json

# Or start from research
/fda:research --product-code DQY --save-project PROJECT
```

### "JSONDecodeError: Expecting value"

**Cause**: Corrupted JSON file

**Solution**:
```bash
# Validate JSON
python3 -m json.tool ~/fda-510k-data/projects/PROJECT/device_profile.json

# If invalid, restore from backup or re-import
```

### "ValueError: No predicates selected"

**Cause**: Need to review and accept predicates before drafting

**Solution**:
```bash
# Review predicates
/fda:review --project PROJECT

# Accept predicates (use review interface)
# Then proceed with drafting
```

### "RuntimeError: Subprocess timeout"

**Cause**: Long-running operation exceeded timeout

**Solution**:
```bash
# Increase timeout
export FDA_SUBPROCESS_TIMEOUT=600

# Or process smaller batch
/fda:extract --product-codes DQY --limit 100
```

## Getting Help

### Enable Debug Logging

```bash
export FDA_DEBUG=1
/fda:research --product-code DQY
```

Logs saved to: `~/fda-510k-data/logs/fda-tools.log`

View logs:
```bash
tail -f ~/fda-510k-data/logs/fda-tools.log
```

### Collect Diagnostic Information

For bug reports, collect:

```bash
# 1. Version
/fda-tools:status > diagnostics.txt

# 2. System info
python3 --version >> diagnostics.txt
pip3 list | grep -E "requests|beautifulsoup|lxml|pikepdf" >> diagnostics.txt

# 3. Error message
# Copy exact error message

# 4. Recent logs
tail -100 ~/fda-510k-data/logs/fda-tools.log >> diagnostics.txt
```

### Support Channels

1. **Check documentation first**:
   - [QUICK_START.md](QUICK_START.md)
   - [INSTALLATION.md](INSTALLATION.md)
   - [README.md](../README.md)

2. **Search existing issues**:
   - https://github.com/andrewlasiter/fda-tools/issues

3. **Ask Claude**:
   ```
   /fda-510k-knowledge
   # Ask regulatory questions
   ```

4. **Report bug**:
   - https://github.com/andrewlasiter/fda-tools/issues/new
   - Include diagnostic information
   - Describe steps to reproduce

### Command-Specific Help

Every command has built-in help:

```bash
/fda:research --help
/fda:extract --help
/fda:draft --help
```

### Detailed Troubleshooting

For command-specific issues, see the detailed guide:

**[plugins/fda-tools/docs/TROUBLESHOOTING.md](../plugins/fda-tools/docs/TROUBLESHOOTING.md)**

Covers:
- Specific command issues
- Version-specific problems
- Advanced debugging
- Known issues

## Quick Reference

### Diagnostic Commands

| Command | Purpose |
|---------|---------|
| `/fda-tools:status` | Overall system health |
| `/fda:cache status` | Cache statistics |
| `/fda:validate --k-number K240001` | Test API connection |
| `/fda:gap-analysis --project PROJECT` | Find missing data |
| `/fda:pre-check --project PROJECT` | Submission readiness |

### Recovery Commands

| Issue | Command |
|-------|---------|
| Clear cache | `/fda:cache clear` |
| Rebuild cache | `/fda-tools:update-data --force` |
| Reset project | `rm -rf ~/fda-510k-data/projects/PROJECT` |
| Re-download PDFs | `/fda:extract --product-codes DQY --force` |

### Environment Variables

```bash
# Common debugging variables
export FDA_DEBUG=1                    # Enable debug logging
export FDA_API_TIMEOUT=60            # API timeout (seconds)
export FDA_PDF_TIMEOUT=300           # PDF download timeout
export FDA_MAX_CONCURRENT=3          # Max concurrent requests
export FDA_DATA_DIR=~/fda-510k-data # Data directory
export FDA_API_KEY=your_key          # FDA API key
```

## Still Having Issues?

If you've tried the solutions above and still have problems:

1. **Update to latest version**:
   ```bash
   claude plugin update fda-tools
   ```

2. **Try clean reinstall**:
   ```bash
   # Backup data first!
   cp -r ~/fda-510k-data ~/fda-backup

   # Uninstall
   claude plugin uninstall fda-tools

   # Reinstall
   claude plugin install fda-tools@fda-tools

   # Restore data
   cp -r ~/fda-backup/* ~/fda-510k-data/
   ```

3. **Report the issue**:
   - Include version: `/fda-tools:status`
   - Include error message
   - Include steps to reproduce
   - Include diagnostic logs

Happy troubleshooting! 🔧
