# Troubleshooting Guide - FDA Tools Plugin

Solutions to common problems and error messages.

## Table of Contents

1. [Plugin Not Working](#plugin-not-working)
2. [API Connection Issues](#api-connection-issues)
3. [Data Issues](#data-issues)
4. [Performance Issues](#performance-issues)
5. [Common Error Messages](#common-error-messages)
6. [Command-Specific Issues](#command-specific-issues)

---

## Plugin Not Working

### Plugin Not Showing in List

**Problem:** `/fda-tools:*` commands not recognized

**Solutions:**

1. **Verify installation:**
   ```bash
   claude plugin list | grep fda-tools
   ```

2. **Reinstall if missing:**
   ```bash
   claude plugin install fda-tools
   ```

3. **Check plugin directory:**
   ```bash
   ls -la ~/.claude/plugins/marketplaces/fda-tools/
   ```

4. **Restart Claude Code:**
   ```bash
   claude restart
   ```

### Commands Not Recognized

**Problem:** Command exists but not executing

**Cause:** Plugin naming changed from `fda-predicate-assistant` to `fda-tools`

**Solution:**
- Old: `/fda-predicate-assistant:command`
- New: `/fda-tools:command`

See [MIGRATION_NOTICE.md](../MIGRATION_NOTICE.md) for full migration guide.

### Permission Errors

**Problem:** `Permission denied` when executing commands

**Solutions:**

1. **Fix script permissions:**
   ```bash
   chmod +x ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/*.py
   ```

2. **Fix data directory:**
   ```bash
   chmod -R u+w ~/fda-510k-data/
   ```

3. **Check settings:**
   ```bash
   grep "fda-tools" ~/.claude/settings.local.json
   ```

---

## API Connection Issues

### openFDA API Rate Limiting

**Problem:** "429 Too Many Requests" errors

**Cause:** Exceeded 240 requests/minute (or 1000/hour) limit

**Solutions:**

1. **Add API key for higher limits:**
   ```bash
   export FDA_API_KEY="your-key"
   ```
   Get free key at: https://open.fda.gov/apis/authentication/

2. **Use delay between requests:**
   ```bash
   /fda-tools:batchfetch --product-codes DQY --years 2024 --delay 1
   ```

3. **Process in smaller batches:**
   ```bash
   # Instead of: --years 2020-2024
   # Use: --years 2024
   ```

### API Key Invalid

**Problem:** "Invalid API key" or "Authentication failed"

**Solutions:**

1. **Verify key format:**
   ```bash
   echo $FDA_API_KEY
   ```
   Should be 40-character alphanumeric string

2. **Re-export key:**
   ```bash
   export FDA_API_KEY="your-correct-key-here"
   ```

3. **Add to settings file:**
   Edit `~/.claude/fda-tools.local.md`:
   ```yaml
   ---
   fda_api_key: your-key-here
   ---
   ```

### Network Connectivity

**Problem:** "Connection refused" or "Network unreachable"

**Solutions:**

1. **Test API connectivity:**
   ```bash
   curl "https://api.fda.gov/device/510k.json?limit=1"
   ```

2. **Check firewall:**
   ```bash
   # Allow outbound HTTPS
   sudo ufw allow out 443/tcp
   ```

3. **Configure proxy (if behind corporate firewall):**
   ```bash
   export HTTP_PROXY=http://proxy:port
   export HTTPS_PROXY=http://proxy:port
   ```

---

## Data Issues

### Download Failures

**Problem:** PDFs not downloading or incomplete downloads

**Solutions:**

1. **Check disk space:**
   ```bash
   df -h ~/fda-510k-data/
   ```
   Need: 2-5 GB for full corpus

2. **Verify network:**
   ```bash
   ping api.fda.gov
   ```

3. **Retry with smaller batch:**
   ```bash
   /fda-tools:extract --product-code DQY --years 2024 --limit 10
   ```

4. **Check download directory permissions:**
   ```bash
   ls -la ~/fda-510k-data/downloads/
   chmod u+w ~/fda-510k-data/downloads/
   ```

### Extraction Errors

**Problem:** "Failed to extract predicates" or "PDF parse error"

**Cause:** PDF corrupt, password-protected, or non-standard format

**Solutions:**

1. **Check PDF validity:**
   ```bash
   file ~/fda-510k-data/downloads/DQY/K240001.pdf
   ```

2. **Re-download:**
   ```bash
   /fda-tools:gap-analysis --product-code DQY
   /fda-tools:data-pipeline --product-codes DQY --years 2024
   ```

3. **Skip problematic files:**
   Delete corrupt PDFs and continue extraction

### Missing Files

**Problem:** "File not found" or "Missing device_profile.json"

**Cause:** Project not initialized or files deleted

**Solutions:**

1. **Initialize project:**
   ```bash
   /fda-tools:research --product-code DQY --years 2024 --project my_device
   ```

2. **Check project directory:**
   ```bash
   ls -la ~/fda-510k-data/projects/my_device/
   ```

3. **Re-run research:**
   ```bash
   /fda-tools:pipeline --product-code DQY --years 2024
   ```

---

## Performance Issues

### Slow Enrichment

**Problem:** `/fda-tools:batchfetch --enrich` takes too long

**Cause:** API calls for MAUDE, recalls, and enrichment data

**Solutions:**

1. **Use `--full-auto` for unattended processing:**
   ```bash
   /fda-tools:batchfetch --product-codes DQY --years 2024 --enrich --full-auto
   ```

2. **Process smaller batches:**
   ```bash
   # Instead of all years, process one year at a time
   /fda-tools:batchfetch --product-codes DQY --years 2024 --enrich
   ```

3. **Check API rate limits:**
   Add API key to avoid throttling (see above)

4. **Use cached data:**
   ```bash
   /fda-tools:cache --project my_device
   ```
   Check freshness before re-fetching

### Memory Issues

**Problem:** "Out of memory" or system slowdown

**Cause:** Processing large datasets (1000+ records)

**Solutions:**

1. **Process in chunks:**
   ```bash
   # Instead of: --years 2020-2024
   # Use separate runs:
   /fda-tools:extract --product-code DQY --years 2024
   /fda-tools:extract --product-code DQY --years 2023
   ```

2. **Increase system swap:**
   ```bash
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

3. **Use streaming mode (Phase 5):**
   ```bash
   /fda-tools:workflow --stream --product-code DQY
   ```

### Disk Space Warnings

**Problem:** "No space left on device"

**Cause:** PDF downloads filling disk

**Solutions:**

1. **Check usage:**
   ```bash
   du -sh ~/fda-510k-data/*
   ```

2. **Clean old downloads:**
   ```bash
   find ~/fda-510k-data/downloads/ -mtime +90 -type f -delete
   ```

3. **Use external storage:**
   ```bash
   /fda-tools:configure --data-dir /mnt/external/fda-data
   ```

---

## Common Error Messages

### "K-number not found"

**Cause:** Invalid K-number format or device not in database

**Solutions:**

1. **Verify format:** K-numbers are `K` followed by 6 digits (e.g., K240001)

2. **Check with web validator:**
   ```bash
   /fda-tools:validate --k-number K240001
   ```

3. **Search by product code instead:**
   ```bash
   /fda-tools:research --product-code DQY --years 2024
   ```

### "Product code invalid"

**Cause:** Product code not recognized or typo

**Solutions:**

1. **Verify product code format:** 3-letter codes (e.g., DQY, KGN, OAP)

2. **Search for correct code:**
   ```bash
   /fda-tools:ask --question "What is the product code for [device type]?"
   ```

3. **Check device classification:**
   Visit: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPCD/classification.cfm

### "API quota exceeded"

**Cause:** Hit daily API limit (without key: low; with key: high)

**Solutions:**

1. **Wait and retry:** Quotas reset hourly/daily

2. **Add API key:**
   ```bash
   export FDA_API_KEY="your-key"
   ```

3. **Use cached data:**
   ```bash
   /fda-tools:cache --show
   ```

### "Python not found"

**Cause:** Python not installed or not in PATH

**Solutions:**

1. **Install Python 3.8+:**
   ```bash
   # Ubuntu/Debian
   sudo apt install python3 python3-pip

   # macOS
   brew install python3
   ```

2. **Verify installation:**
   ```bash
   python3 --version
   ```

3. **Use full path:**
   ```bash
   /usr/bin/python3 script.py
   ```

---

## Command-Specific Issues

### `/fda-tools:research` Not Finding Predicates

**Problem:** No predicates extracted

**Solutions:**

1. **Verify product code has clearances:**
   ```bash
   /fda-tools:analyze --product-code DQY --years 2024
   ```

2. **Expand year range:**
   ```bash
   /fda-tools:research --product-code DQY --years 2022-2024
   ```

3. **Check download status:**
   ```bash
   ls ~/fda-510k-data/downloads/DQY/
   ```

### `/fda-tools:batchfetch` Enrichment Incomplete

**Problem:** Some fields missing in enriched CSV

**Cause:** API returned no data for specific device

**Solutions:**

1. **Check quality report:**
   ```bash
   cat ~/fda-510k-data/projects/*/quality_report.md
   ```

2. **Verify K-numbers:**
   Some devices may have no MAUDE or recall data (normal)

3. **Re-run with fresh cache:**
   ```bash
   rm -rf ~/fda-510k-data/cache/
   /fda-tools:batchfetch --product-codes DQY --years 2024 --enrich
   ```

### `/fda-tools:draft` Generating TODO Placeholders

**Problem:** Drafts contain [TODO] instead of actual content

**Cause:** Missing source data (review.json, device_profile.json)

**Solutions:**

1. **Complete research first:**
   ```bash
   /fda-tools:research --product-code DQY --years 2024
   /fda-tools:review  # Accept predicates
   ```

2. **Verify project files exist:**
   ```bash
   ls ~/fda-510k-data/projects/my_device/
   ```

3. **Check device_profile.json:**
   ```bash
   cat ~/fda-510k-data/projects/my_device/device_profile.json
   ```

### `/fda-tools:pre-check` Low SRI Score

**Problem:** Submission Readiness Index < 60

**Cause:** Missing data, incomplete sections, or deficiencies

**Solutions:**

1. **Review pre-check report:**
   ```bash
   cat ~/fda-510k-data/projects/my_device/pre_check_report.md
   ```

2. **Address CRITICAL gaps first:**
   Focus on items marked CRITICAL

3. **Add missing data:**
   - Standards: `/fda-tools:standards`
   - Literature: `/fda-tools:literature`
   - Safety: `/fda-tools:safety`

4. **Re-run after fixes:**
   ```bash
   /fda-tools:pre-check
   ```

---

## Diagnostic Commands

### General Health Check

```bash
/fda-tools:status
```

Shows:
- Plugin version
- Data directory status
- Script permissions
- Record counts
- File freshness

### Project Status

```bash
/fda-tools:dashboard
```

Shows:
- Drafted sections
- Consistency results
- Readiness score
- TODO counts

### Cache Status

```bash
/fda-tools:cache --show
```

Shows:
- Cached MAUDE data
- Cached recall data
- Cached guidance
- Freshness indicators

### Audit Trail

```bash
/fda-tools:audit --recent 10
```

Shows:
- Recent command executions
- Decision rationale
- Exclusion reasons

---

## Getting Additional Help

### Built-in Help

```bash
# Ask regulatory questions
/fda-tools:ask --question "How do I...?"

# Command-specific help
/fda-tools:start  # Setup wizard

# System status
/fda-tools:status
```

### Documentation

- **Quick Start:** [QUICK_START.md](QUICK_START.md)
- **Installation:** [INSTALLATION.md](INSTALLATION.md)
- **Command Reference:** [README.md](../README.md)
- **Migration Guide:** [MIGRATION_NOTICE.md](../MIGRATION_NOTICE.md)

### Support Channels

- **GitHub Issues:** https://github.com/andrewlasiter/fda-predicate-assistant/issues
- **Documentation:** `~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/docs/`

### Debug Mode

For detailed error logging:

```bash
export FDA_DEBUG=1
/fda-tools:command --verbose
```

---

## Still Having Issues?

1. **Collect diagnostic info:**
   ```bash
   /fda-tools:status > status.txt
   /fda-tools:audit --recent 5 > audit.txt
   ```

2. **Check logs:**
   ```bash
   tail -n 100 ~/.claude/logs/fda-tools.log
   ```

3. **Report issue with:**
   - Error message
   - Command executed
   - Output of `/fda-tools:status`
   - System info (OS, Python version)

4. **Submit to:** https://github.com/andrewlasiter/fda-predicate-assistant/issues
