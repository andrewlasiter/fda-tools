# Troubleshooting Guide - FDA Tools Plugin

Solutions to common problems and error messages.

## Table of Contents

1. [Plugin Not Working](#plugin-not-working)
2. [API Connection Issues](#api-connection-issues)
3. [Data Issues](#data-issues)
4. [Performance Issues](#performance-issues)
5. [Common Error Messages](#common-error-messages)
6. [Command-Specific Issues](#command-specific-issues)
   - [/fda-tools:research](#fda-toolsresearch-not-finding-predicates)
   - [/fda-tools:batchfetch](#fda-toolsbatchfetch-enrichment-incomplete)
   - [/fda-tools:draft](#fda-toolsdraft-generating-todo-placeholders)
   - [/fda-tools:pre-check](#fda-toolspre-check-low-sri-score)
   - [/fda-tools:update-data (v5.26.0)](#fda-toolsupdate-data-issues-v5260)
   - [/fda-tools:compare-sections (v5.26.0)](#fda-toolscompare-sections-issues-v5260)
7. [Diagnostic Commands](#diagnostic-commands)

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

### `/fda-tools:update-data` Issues (v5.26.0)

#### No Projects Found

**Problem:** `--scan-all` reports "0 projects with data_manifest.json"

**Cause:** Projects don't have data_manifest.json (may use older structure)

**Solutions:**

1. **Check project structure:**
   ```bash
   ls ~/fda-510k-data/projects/*/data_manifest.json
   ```

2. **Verify projects exist:**
   ```bash
   /fda-tools:portfolio
   ```

3. **Create projects properly:**
   ```bash
   /fda-tools:research --product-code DQY --years 2024 --project my_device
   ```
   This creates data_manifest.json automatically

**Note:** Batch test projects may use different structure - this is expected

#### No Stale Data Found

**Problem:** `--scan-all` shows "0 stale queries" but data looks old

**Cause:** Data is within TTL window (7 days for stable, 24 hours for safety)

**Solutions:**

1. **Check actual freshness:**
   ```bash
   /fda-tools:cache --show
   ```

2. **Force update regardless of TTL:**
   ```bash
   python3 ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/update_manager.py \
     --project my_device --update
   ```
   (Note: Command respects TTL; use script directly to override)

3. **Verify TTL configuration:**
   - Classification: 7 days (168 hours)
   - Recalls/Events: 24 hours
   - See scripts/fda_data_store.py for full list

#### Update Failures

**Problem:** "❌ FAILED: Unknown query type" or API errors during update

**Solutions:**

1. **For "Unknown query type" errors:**
   - This indicates corrupted data_manifest.json
   - **Fix:** Remove invalid entries manually:
     ```bash
     # Edit manifest and remove lines with invalid query types
     nano ~/fda-510k-data/projects/my_device/data_manifest.json
     ```
   - Valid types: `classification`, `clearances`, `recalls`, `events`, `enforcement`

2. **For API errors:**
   - Check API connectivity:
     ```bash
     curl -I https://api.fda.gov/device/510k.json?limit=1
     ```
   - Verify API key (if used):
     ```bash
     echo $OPENFDA_API_KEY
     ```
   - Retry with `--update` (automatic retry with backoff)

3. **For rate limiting errors:**
   - Update implements 500ms delay automatically
   - If still hitting limits, wait 5 minutes and retry
   - Consider adding API key for higher limits

4. **For partial failures:**
   - Tool continues after errors (partial success mode)
   - Failed queries remain stale (timestamps not updated)
   - Review output: "✅ Update complete: X updated, Y failed"
   - Re-run to retry failed queries

#### Slow Performance

**Problem:** Updates taking too long (>5 min for 50 queries)

**Cause:** Rate limiting (500ms per query) and API response time

**Expected Performance:**
- 20 queries: ~20 seconds
- 50 queries: ~50 seconds
- 100 queries: ~100 seconds (1.7 minutes)

**Solutions:**

1. **This is normal behavior:**
   - 500ms delay between requests = 2 req/sec (API compliance)
   - Target: <10 min for 100+ queries ✓

2. **To speed up (if many projects):**
   - Update one project at a time:
     ```bash
     /fda-tools:update-data --project my_device
     ```
   - Or use `--dry-run` to preview without executing

3. **Background processing:**
   - Run in background to continue working:
     ```bash
     /fda-tools:update-data --update-all &
     ```
   - Check progress: `jobs` and `fg` to bring to foreground

#### Dry-Run Shows Different Results

**Problem:** `--dry-run` shows stale data, but `--update` finds nothing

**Cause:** Another process updated data between dry-run and update

**Solutions:**

1. **Normal behavior:**
   - TTL checked at execution time
   - Data may have been updated by another command
   - Timestamps refreshed automatically

2. **Verify freshness:**
   ```bash
   /fda-tools:cache --show
   ```

---

### `/fda-tools:compare-sections` Issues (v5.26.0)

#### No Devices Found for Product Code

**Problem:** `❌ Error: No devices found for product code OVE`

**Cause:** Structured cache missing or lacks metadata enrichment

**Solutions:**

1. **Build structured cache first:**
   ```bash
   # Using per-device cache (preferred)
   python3 ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/build_structured_cache.py \
     --cache-dir ~/fda-510k-data/extraction/cache

   # Using legacy pdf_data.json
   python3 ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/build_structured_cache.py \
     --legacy ~/fda-510k-data/projects/my_project/pdf_data.json
   ```

2. **Verify structured cache exists:**
   ```bash
   ls ~/fda-510k-data/extraction/structured_text_cache/*.json | wc -l
   ```
   Should show files for each device

3. **Check metadata enrichment:**
   ```bash
   python3 -c "
   import json
   from pathlib import Path
   files = list(Path('~/fda-510k-data/extraction/structured_text_cache').expanduser().glob('K*.json'))
   if files:
       with open(files[0]) as f:
           data = json.load(f)
       print('Sample metadata:', data.get('metadata', {}))
   "
   ```
   Should show `product_code` field

4. **Rebuild with metadata enrichment:**
   - v5.26.0+ automatically enriches metadata via openFDA API
   - Rebuilding legacy cache adds product_code to all devices
   - Takes ~2 min for 200 devices (includes API calls)

#### Structured Cache Not Found

**Problem:** `📂 Loading structured cache... ❌ Error: Cache directory not found`

**Cause:** Structured cache never built

**Solutions:**

1. **Create structured cache:**
   - Option A: From per-device cache (if you've run `/extract`):
     ```bash
     python3 ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/build_structured_cache.py \
       --cache-dir ~/fda-510k-data/extraction/cache
     ```

   - Option B: From legacy pdf_data.json:
     ```bash
     python3 ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/build_structured_cache.py \
       --legacy ~/fda-510k-data/projects/my_project/pdf_data.json
     ```

2. **Verify output directory:**
   ```bash
   ls -la ~/fda-510k-data/extraction/structured_text_cache/
   ```

3. **Check permissions:**
   ```bash
   chmod -R u+w ~/fda-510k-data/extraction/
   ```

#### Few Sections Detected

**Problem:** Coverage matrix shows 0% for all sections

**Cause:** PDF text quality issues or section patterns not matching

**Solutions:**

1. **Check structured cache quality:**
   ```bash
   cat ~/fda-510k-data/extraction/structured_text_cache/manifest.json
   ```
   Look for OCR quality metrics:
   - HIGH (clean text): Best
   - MEDIUM (minor errors): OK
   - LOW (OCR issues): May need manual review

2. **Review extraction quality:**
   - `section_count` should be 7+ for HIGH quality
   - `tier2_sections` indicates OCR corrections applied
   - Devices with 0-3 sections may have corrupt PDFs

3. **Verify PDF quality:**
   ```bash
   file ~/fda-510k-data/downloads/DQY/K240001.pdf
   ```
   Should show "PDF document"

4. **Re-download if needed:**
   ```bash
   /fda-tools:data-pipeline --product-codes DQY --years 2024
   ```

#### No Standards Detected

**Problem:** Standards frequency analysis shows 0 standards

**Cause:** Section text doesn't contain standard references, or standards are informal

**Solutions:**

1. **This may be normal:**
   - Some product codes have low standards citation rates
   - Older clearances may not cite standards explicitly
   - Standards may be referenced informally (e.g., "biocompatibility testing per ISO guidance")

2. **Check specific sections:**
   - Try different sections: `performance`, `biocompatibility`, `electrical`
   - Standards more common in testing sections

3. **Review raw text:**
   ```bash
   python3 -c "
   import json
   with open('~/fda-510k-data/extraction/structured_text_cache/K240001.json'.replace('~', '/home/linux')) as f:
       data = json.load(f)
   print(data['sections'].get('biocompatibility', {}).get('text', 'N/A')[:500])
   "
   ```

4. **Expected patterns:**
   - ISO 10993 (biocompatibility)
   - IEC 60601 (electrical safety)
   - ISO 11135/11137 (sterilization)
   - Standards detected via regex: `ISO|IEC|ASTM|ANSI`

#### Outlier Detection Not Working

**Problem:** "Outliers detected: 0" even though devices vary widely

**Cause:** Insufficient sample size or low variance

**Solutions:**

1. **Increase sample size:**
   ```bash
   /fda-tools:compare-sections --product-code DQY --sections clinical --limit 50
   ```
   Need 10+ devices for meaningful statistics

2. **Try different sections:**
   - Some sections have low variance (e.g., indications often similar)
   - Try: `performance`, `clinical`, `biocompatibility`

3. **Check Z-score threshold:**
   - Outliers defined as |Z-score| > 2 (95th percentile)
   - Only extreme outliers flagged
   - Review raw data in CSV for variance

4. **Verify section presence:**
   - If section missing from most devices, no outliers possible
   - Check coverage matrix first

#### Metadata Enrichment Slow

**Problem:** Building structured cache takes >10 minutes

**Cause:** openFDA API enrichment for metadata (product_code, review_panel)

**Expected Performance:**
- 200 devices: ~2 minutes (includes 500ms API delay per device)
- Enrichment adds ~1 minute vs. no enrichment

**Solutions:**

1. **This is normal:**
   - API rate limiting: 500ms per device (API compliance)
   - Alternative: ~1 second per device without API calls

2. **Skip enrichment (NOT recommended):**
   - Edit build_structured_cache.py to skip API calls
   - **WARNING:** Product code filtering won't work without enrichment

3. **Use cache:**
   - Enrichment only happens on rebuild
   - Subsequent `/compare-sections` uses cached metadata
   - No re-enrichment needed

4. **Progress tracking:**
   ```
   Processing 209 PDFs from legacy cache...
     ✓ K231152: 17918 chars, 19 sections [KGN]
     ✓ K140306: 7888 chars, 11 sections [FTM]
     ...
   ```
   Product codes in brackets indicate enrichment working

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
