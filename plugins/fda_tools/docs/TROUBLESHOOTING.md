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
7. [Agent Registry Failures](#agent-registry-failures)
8. [ClinicalTrials.gov API Failures](#clinicaltrialsgov-api-failures)
9. [PMA Supplement Analysis Failures](#pma-supplement-analysis-failures)
10. [Bridge Server Failures](#bridge-server-failures)
11. [Preventive Maintenance](#preventive-maintenance)
12. [Diagnostic Commands](#diagnostic-commands)
13. [Linear API Issues](#linear-api-issues)
    - [Linear API Rate Limit Exceeded](#linear-api-rate-limit-exceeded)
    - [Linear Authentication Failed](#linear-authentication-failed)
    - [Linear Custom Fields Not Found](#linear-custom-fields-not-found)
    - [Linear Issue Creation Failed](#linear-issue-creation-failed)
    - [Linear Circuit Breaker Triggered](#linear-circuit-breaker-triggered)
14. [Orchestrator Agent Selection Issues](#orchestrator-agent-selection-issues)
    - [No Agents Selected for Task](#no-agents-selected-for-task)
    - [Agent Registry Load Failed](#agent-registry-load-failed)
    - [Wrong Agents Assigned](#wrong-agents-assigned)
    - [Execution Coordinator Failures](#execution-coordinator-failures)
    - [Performance Optimization](#performance-optimization)

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

**Cause:** Plugin naming changed from `fda-tools` to `fda-tools`

**Solution:**
- Old: `/fda-tools:command`
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

## Agent Registry Failures

### Error: "Skills directory not found"

**Cause:** The agent registry cannot locate the skills directory. This happens when `SKILLS_DIR` is not set, points to an invalid path, or the skills directory was moved or deleted.

**Recovery:**

1. **Check the default skills path:**
   ```bash
   ls -la ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/skills/
   ```
   Should show 18+ agent subdirectories (e.g., `fda-regulatory-strategy-expert/`, `fda-clinical-expert/`).

2. **Verify the agent registry resolves the path correctly:**
   ```bash
   python3 -c "
   from pathlib import Path
   skills = Path.home() / '.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/skills'
   print(f'Exists: {skills.exists()}')
   print(f'Agent count: {len([d for d in skills.iterdir() if d.is_dir() and not d.name.startswith(\".\")])}')
   "
   ```

3. **If the directory is missing, reinstall the plugin:**
   ```bash
   claude plugin install fda-tools
   ```

4. **Run the skills validator:**
   ```bash
   python3 ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/validate_skills.py
   ```

### Error: "Invalid agent.yaml syntax"

**Cause:** Malformed YAML in an agent definition file. Common issues include tabs instead of spaces, unclosed quotes, or invalid UTF-8 characters.

**Recovery:**

1. **Identify the broken file:**
   ```bash
   python3 -c "
   import yaml, sys
   from pathlib import Path
   skills = Path.home() / '.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/skills'
   for agent_dir in sorted(skills.iterdir()):
       yaml_file = agent_dir / 'agent.yaml'
       if yaml_file.exists():
           try:
               yaml.safe_load(yaml_file.read_text())
               print(f'  OK: {agent_dir.name}')
           except yaml.YAMLError as e:
               print(f'  BROKEN: {agent_dir.name} -- {e}', file=sys.stderr)
   "
   ```

2. **Common YAML fixes:**
   - Replace tabs with 2 spaces
   - Ensure all strings with colons are quoted: `description: "My: value"`
   - Remove trailing whitespace on lines with multiline strings
   - Verify UTF-8 encoding: `file agent.yaml` should show "UTF-8 Unicode text"

3. **Validate after fixing:**
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('agent.yaml'))"
   ```

### Error: "SKILL.md not found for agent"

**Cause:** An agent subdirectory exists but is missing its `SKILL.md` definition file.

**Recovery:**

1. **List agents missing SKILL.md:**
   ```bash
   for dir in ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/skills/*/; do
     if [ ! -f "$dir/SKILL.md" ]; then
       echo "MISSING: $dir"
     fi
   done
   ```

2. **If an agent directory has agent.yaml but no SKILL.md:**
   - The registry silently skips it (by design)
   - Check git status: `git -C ~/.claude/plugins/marketplaces/fda-tools/ status`
   - Restore from git: `git -C ~/.claude/plugins/marketplaces/fda-tools/ checkout -- plugins/fda-tools/skills/`

### Error: "Path traversal attempt blocked"

**Cause:** The agent registry detected a symlink or `..` sequence attempting to escape the skills directory boundary. This is a security protection (FDA-83).

**Recovery:**

1. **This is working as intended.** The registry blocks any path that resolves outside the skills base directory.

2. **Check for suspicious symlinks:**
   ```bash
   find ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/skills/ -type l
   ```

3. **Remove any symlinks found:**
   ```bash
   find ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/skills/ -type l -delete
   ```

4. **If a legitimate agent was blocked, check its path:**
   ```bash
   realpath ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/skills/<agent-name>
   ```
   The resolved path must be within the `skills/` directory.

### Error: "Circular dependency detected"

**Cause:** Two or more agents reference each other in their dependency chains, creating an unresolvable cycle.

**Recovery:**

1. **Identify the cycle:**
   ```bash
   python3 ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/agent_registry.py validate
   ```

2. **Review agent SKILL.md files for cross-references.**

3. **Break the cycle** by removing one direction of the dependency in the less critical agent's definition.

---

## ClinicalTrials.gov API Failures

### Error: "Request timeout after 15 seconds"

**Cause:** The ClinicalTrials.gov API did not respond within the configured timeout window. This is common during peak hours or API maintenance.

**Recovery:**

1. **Check API availability:**
   ```bash
   curl -s -o /dev/null -w "HTTP %{http_code} in %{time_total}s\n" \
     "https://clinicaltrials.gov/api/v2/studies?pageSize=1&format=json"
   ```
   Expected: `HTTP 200` in under 5 seconds.

2. **Increase timeout (if consistently slow):**
   ```python
   from ide_pathway_support import ClinicalTrialsIntegration
   ct = ClinicalTrialsIntegration(request_timeout=30)  # default is 15s
   ```

3. **The retry logic (FDA-89) automatically retries timeouts:**
   - Attempt 1: immediate
   - Attempt 2: wait ~2 seconds
   - Attempt 3: wait ~4 seconds
   - If all 3 fail, the error dict is returned (no exception raised)

4. **Check ClinicalTrials.gov status page:**
   - Visit: https://clinicaltrials.gov
   - If the site itself is down, wait and retry later

### Error: "429 Too Many Requests"

**Cause:** ClinicalTrials.gov rate limit exceeded. The API enforces request quotas per IP address.

**Recovery:**

1. **The retry logic handles this automatically (FDA-89):**
   - Reads the `Retry-After` response header
   - Waits the specified number of seconds (capped at 120s)
   - Retries up to 3 times total
   - Logs a warning: `"ClinicalTrials.gov rate limit hit (429)"`

2. **If rate limiting persists after retries:**
   - Reduce search frequency
   - Add delays between searches:
     ```python
     import time
     ct = ClinicalTrialsIntegration()
     for device in device_list:
         result = ct.search_device_studies(device)
         time.sleep(2)  # 2-second delay between requests
     ```
   - Batch searches during off-peak hours (evenings, weekends US time)

3. **Check current rate limit status:**
   ```bash
   curl -s -D - -o /dev/null "https://clinicaltrials.gov/api/v2/studies?pageSize=1&format=json" 2>&1 | grep -i "rate\|retry\|limit"
   ```

### Error: "HTTP 404 Not Found" (for study details)

**Cause:** The NCT ID does not exist or the study was removed from ClinicalTrials.gov.

**Recovery:**

1. **This is a client error (4xx) -- NOT retried by design.**

2. **Verify the NCT ID format:**
   - Must match pattern: `NCT` followed by 8 digits (e.g., `NCT12345678`)
   - Check: `echo "NCT12345678" | grep -E '^NCT[0-9]{8}$'`

3. **Search the web interface:**
   - Visit: `https://clinicaltrials.gov/study/NCT12345678`
   - If the study was removed, it will show "No Study Found"

4. **Try searching by keyword instead:**
   ```python
   ct = ClinicalTrialsIntegration()
   results = ct.search_device_studies("your device name")
   ```

### Error: "HTTP 5xx Server Error"

**Cause:** ClinicalTrials.gov server-side failure. These are transient and automatically retried.

**Recovery:**

1. **Automatic retry handles this (FDA-89):**
   - 500, 502, 503, 504 errors are retried with exponential backoff
   - Wait times: ~2s, ~4s, ~8s (capped at 10s)
   - After 3 failures, returns an error dict (does not raise)

2. **If persistent, check API status:**
   ```bash
   curl -v "https://clinicaltrials.gov/api/v2/studies?pageSize=1&format=json" 2>&1 | tail -5
   ```

3. **Increase retry count for known unstable periods:**
   ```python
   ct = ClinicalTrialsIntegration(max_retries=5)
   ```

### Error: "Malformed JSON response"

**Cause:** The API returned non-JSON content (e.g., HTML error page). This is NOT retried because the response was received successfully but contained unexpected content.

**Recovery:**

1. **Check what the API is actually returning:**
   ```bash
   curl -s "https://clinicaltrials.gov/api/v2/studies?pageSize=1&format=json" | head -c 200
   ```
   Should start with `{`. If it starts with `<html>`, the API may be in maintenance mode.

2. **Wait and retry manually** -- this usually resolves within minutes.

---

## PMA Supplement Analysis Failures

### Error: "Insufficient data for classification"

**Cause:** The PMA supplement classifier could not determine the supplement type because the change description was too vague or missing required context.

**Recovery:**

1. **Provide a more detailed change description:**
   ```python
   from pma_supplement_enhanced import SupplementTypeClassifier
   classifier = SupplementTypeClassifier()
   # Too vague:
   # result = classifier.classify("minor change")
   # Better:
   result = classifier.classify("Manufacturing site relocation for sterilization process from Plant A to Plant B with validated EO sterilization")
   ```

2. **Include key context keywords:**
   - Manufacturing: "manufacturing site", "process change", "supplier change"
   - Labeling: "labeling update", "IFU change", "new indication"
   - Design: "design modification", "material change", "dimensions"
   - Clinical: "clinical data", "new clinical study", "post-market data"

3. **Use the decision tree for guided classification:**
   ```python
   from pma_supplement_enhanced import SupplementDecisionTree
   tree = SupplementDecisionTree()
   result = tree.evaluate(
       change_description="new sterilization site",
       has_clinical_data=False,
       is_design_change=False,
   )
   ```

### Error: "PMA number not found"

**Cause:** The specified PMA number does not exist in the openFDA database or has an invalid format.

**Recovery:**

1. **Verify PMA number format:** `P` followed by 6 digits (e.g., `P170019`)

2. **Search for the PMA:**
   ```bash
   curl -s "https://api.fda.gov/device/pma.json?search=pma_number:P170019&limit=1" | python3 -m json.tool
   ```

3. **Check if it is a supplement number** (format: `P170019/S001`) -- the base PMA number excludes the supplement suffix.

### Error: "Threshold edge case - manual review recommended"

**Cause:** The change impact score falls near the boundary between supplement types, making automated classification unreliable.

**Recovery:**

1. **Review the detailed scoring breakdown:**
   ```python
   from pma_supplement_enhanced import ChangeImpactAssessor
   assessor = ChangeImpactAssessor()
   impact = assessor.assess_impact(
       change_type="manufacturing_site",
       affected_components=["sterilization"],
       has_performance_data=True,
   )
   print(f"Score: {impact['impact_score']}")
   print(f"Category: {impact['impact_category']}")
   print(f"Details: {impact['scoring_details']}")
   ```

2. **When the score is borderline, consult these resources:**
   - 21 CFR 814.39(a)-(f) for supplement type definitions
   - FDA Guidance: "Modifications to Devices Subject to PMA" (2020)
   - Consider a Pre-Submission (Q-Sub) for FDA guidance on the correct supplement type

3. **This is an expected safety feature** -- the tool flags uncertainty rather than making a potentially incorrect automated decision.

---

## Bridge Server Failures

### Error: "Address already in use (port 18790)"

**Cause:** Another process is already bound to the bridge server port (default: 18790). This can happen if a previous server instance did not shut down cleanly.

**Recovery:**

1. **Find the process using the port:**
   ```bash
   lsof -i :18790
   # or
   ss -tlnp | grep 18790
   ```

2. **Kill the stale process:**
   ```bash
   kill $(lsof -t -i :18790)
   ```

3. **If the port is used by another service, change the bridge port:**
   ```bash
   export FDA_BRIDGE_PORT=18791
   ```

4. **Restart the bridge server:**
   ```bash
   python3 ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/bridge/server.py
   ```

### Error: "Connection refused" (bridge server)

**Cause:** The bridge server is not running or crashed during operation.

**Recovery:**

1. **Check if the server is running:**
   ```bash
   curl -s http://127.0.0.1:18790/health
   ```
   Expected: JSON response with `"status": "healthy"` and uptime information.

2. **Start the server if not running:**
   ```bash
   cd ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/bridge/
   python3 server.py &
   ```

3. **Check for import errors (missing dependencies):**
   ```bash
   python3 -c "import fastapi, uvicorn, pydantic; print('Dependencies OK')"
   ```
   If imports fail:
   ```bash
   pip install -r ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/bridge/requirements.txt
   ```

4. **Check the server logs for crash details:**
   ```bash
   tail -n 50 ~/.claude/logs/fda-bridge.log
   ```

### Error: "401 Unauthorized" or "Invalid API Key"

**Cause:** The bridge server requires API key authentication (via `X-API-Key` header). The key is stored in the OS keyring and generated on first startup.

**Recovery:**

1. **The `/health` endpoint does NOT require authentication** -- use it to confirm the server is running.

2. **Retrieve the current API key:**
   ```bash
   python3 -c "
   try:
       import keyring
       key = keyring.get_password('fda-tools-bridge', 'api-key')
       print(f'Key exists: {key is not None}')
       if key:
           print(f'Key prefix: {key[:8]}...')
   except Exception as e:
       print(f'Keyring error: {e}')
   "
   ```

3. **If the keyring is inaccessible (headless server):**
   ```bash
   export FDA_BRIDGE_API_KEY="your-generated-key"
   ```

4. **Regenerate the key (resets all clients):**
   ```bash
   python3 ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/setup_api_key.py --reset bridge
   ```

### Error: "Session expired" or "Session not found"

**Cause:** Bridge server sessions are stored in memory and lost when the server restarts. Sessions also expire after inactivity.

**Recovery:**

1. **Create a new session:**
   ```bash
   curl -s -X POST http://127.0.0.1:18790/session \
     -H "X-API-Key: YOUR_KEY" \
     -H "Content-Type: application/json" \
     -d '{"project": "my_device"}'
   ```

2. **List active sessions:**
   ```bash
   curl -s http://127.0.0.1:18790/sessions -H "X-API-Key: YOUR_KEY"
   ```

3. **For persistent sessions, note:** The current implementation uses in-memory storage. Sessions do not survive server restarts. This is documented in the server source code as a known limitation.

### Error: "Rate limit exceeded" (bridge server)

**Cause:** The bridge server enforces rate limits (default: 60 requests/minute general, 30 requests/minute for execute).

**Recovery:**

1. **Wait and retry.** Rate limits reset each minute.

2. **Increase rate limits (development only):**
   ```bash
   export FDA_BRIDGE_RATE_LIMIT="120/minute"
   export FDA_BRIDGE_RATE_LIMIT_EXECUTE="60/minute"
   ```

3. **Check if `slowapi` is installed** (rate limiting is optional):
   ```bash
   python3 -c "import slowapi; print('Rate limiting active')" 2>/dev/null || echo "Rate limiting disabled (slowapi not installed)"
   ```

---

## Preventive Maintenance

### Health Check Script

Run the automated health check to verify all components:

```bash
bash ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/health_check.sh
```

This checks:
- Skills directory and agent count
- Python dependencies
- ClinicalTrials.gov API connectivity
- openFDA API connectivity
- Bridge server status
- Disk space for data directory

### Log Monitoring

Monitor for recurring issues:

```bash
# Check for recent errors
grep -i "error\|failed\|exception" ~/.claude/logs/fda-tools.log | tail -20

# Check for rate limiting events
grep -i "rate.limit\|429\|too.many" ~/.claude/logs/fda-tools.log | tail -10

# Check retry activity (FDA-89)
grep -i "retrying\|retry\|backoff" ~/.claude/logs/fda-tools.log | tail -10
```

### Backup Procedures

Protect project data:

```bash
# Backup all project data
tar -czf ~/fda-backup-$(date +%Y%m%d).tar.gz ~/fda-510k-data/projects/

# Backup plugin configuration
cp ~/.claude/settings.local.json ~/fda-backup-settings.json
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

## Linear API Issues

### Linear API Rate Limit Exceeded

**Problem:** "429 Too Many Requests" from Linear API

**Cause:** Exceeded 100 requests/minute rate limit

**Solutions:**

1. **Built-in rate limiter** (automatically enforced):
   ```python
   # Rate limiter in linear_integrator.py limits to 100 calls/min
   linear_rate_limiter = RateLimiter(calls_per_minute=100)
   ```

2. **Process in smaller batches:**
   ```bash
   python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py batch \
     --issues "FDA-92,FDA-93,FDA-94" \
     --batch-size 10  # Process 10 at a time
   ```

3. **Wait for cooldown:**
   - Circuit breaker triggers after 5 failures
   - 60-second recovery timeout
   - Automatic retry with exponential backoff

### Linear Authentication Failed

**Problem:** "Invalid API key" or "Unauthorized" errors

**Solutions:**

1. **Verify API key:**
   ```bash
   echo $LINEAR_API_KEY
   ```
   Should start with `lin_api_`

2. **Check API key permissions:**
   - Go to https://linear.app/settings/api
   - Verify key has **write** permissions
   - Regenerate if needed

3. **Test authentication:**
   ```bash
   python3 $FDA_PLUGIN_ROOT/scripts/test_linear_auth.py
   ```

4. **Check environment variable:**
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export LINEAR_API_KEY="lin_api_your_key_here"
   source ~/.bashrc
   ```

### Linear Custom Fields Not Found

**Problem:** "Delegate field not found" or "Reviewers field missing"

**Cause:** Custom fields not created in Linear workspace

**Solutions:**

1. **Create delegate field:**
   - Go to Linear → Settings → Custom Fields
   - Click "Create custom field"
   - Name: `delegate`
   - Type: `User` (single select)
   - Teams: Select "FDA tools" team

2. **Create reviewers field:**
   - Name: `reviewers`
   - Type: `User` (multi-select)
   - Teams: Select "FDA tools" team

3. **Verify fields exist:**
   ```bash
   curl https://api.linear.app/graphql \
     -H "Authorization: $LINEAR_API_KEY" \
     -d '{"query": "{ teams { nodes { id name customFields { nodes { name type } } } } }"}'
   ```

### Linear Issue Creation Failed

**Problem:** "Failed to create Linear issue" with GraphQL error

**Solutions:**

1. **Check team ID:**
   ```bash
   echo $LINEAR_TEAM_ID
   ```
   Should be a UUID like `5e4df6d3-2006-4e51-b862-b65ba71bff04`

2. **Verify project exists:**
   ```bash
   /linear:list_projects
   ```

3. **Check issue title length:**
   - Maximum: 255 characters
   - If title too long, truncate or summarize

4. **Validate priority value:**
   - Must be 0-4 (0=None, 1=Urgent, 2=High, 3=Normal, 4=Low)

5. **Check description markdown:**
   - Linear supports GitHub-flavored markdown
   - Avoid unsupported HTML tags

### Linear Circuit Breaker Triggered

**Problem:** "Circuit breaker open - service unavailable"

**Cause:** 5+ consecutive Linear API failures

**Solutions:**

1. **Wait for recovery:**
   - Circuit breaker opens after 5 failures
   - 60-second recovery timeout
   - Automatically retries after cooldown

2. **Check Linear API status:**
   - Visit https://linear.app/status
   - Check for ongoing incidents

3. **Manual circuit breaker reset:**
   ```python
   from linear_integrator import linear_circuit_breaker
   linear_circuit_breaker.reset()
   ```

4. **Increase failure threshold** (if needed):
   ```python
   # In linear_integrator.py
   linear_circuit_breaker = CircuitBreaker(
       failure_threshold=10,  # Increase from 5
       recovery_timeout=120   # Increase from 60s
   )
   ```

---

## Orchestrator Agent Selection Issues

### No Agents Selected for Task

**Problem:** "No suitable agents found for task"

**Cause:** Task description too vague or domain not recognized

**Solutions:**

1. **Improve task description:**
   ```bash
   # Bad:
   --task "Fix the bug"

   # Good:
   --task "Fix authentication vulnerability in FastAPI endpoint - SQL injection risk in user login"
   ```

2. **Add language/framework hints:**
   ```bash
   --task "Review authentication system (Python, FastAPI, PostgreSQL)"
   ```

3. **Specify review dimensions:**
   ```bash
   --task "Security audit focusing on authentication, authorization, and input validation"
   ```

4. **Increase max agents:**
   ```bash
   --max-agents 15  # Default is 10
   ```

### Agent Registry Load Failed

**Problem:** "Failed to load agent registry" or "AgentRegistry import error"

**Solutions:**

1. **Verify registry file exists:**
   ```bash
   ls -la $FDA_PLUGIN_ROOT/scripts/agent_registry.py
   ```

2. **Check Python syntax:**
   ```bash
   python3 -m py_compile $FDA_PLUGIN_ROOT/scripts/agent_registry.py
   ```

3. **Reinstall plugin:**
   ```bash
   claude plugin reinstall fda-tools@fda-tools
   ```

4. **Manual registry update:**
   ```bash
   cd $FDA_PLUGIN_ROOT
   git pull origin master
   ```

### Wrong Agents Assigned

**Problem:** Agents don't match task type (e.g., frontend agent for backend task)

**Cause:** Task classification inaccurate

**Solutions:**

1. **Be specific in task description:**
   ```bash
   # Specify "backend" or "frontend" explicitly
   --task "Backend API security review for FastAPI endpoints"
   ```

2. **List file paths explicitly:**
   ```bash
   --files "api/auth.py,api/db.py,models/user.py"
   # Helps detect Python backend context
   ```

3. **Override agent selection:**
   - Edit `task_analyzer.py` detection patterns
   - Add custom keywords for your domain

4. **Use batch mode with manual assignment:**
   ```bash
   python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py assign \
     --issue "FDA-102" \
     --task "Security review" \
     --agent "security-auditor"  # Force specific agent
   ```

### Execution Coordinator Failures

**Problem:** "Phase execution failed" or "Agent invocation error"

**Cause:** Individual agent failures during multi-phase execution

**Solutions:**

1. **Check agent simulation:**
   - The orchestrator currently uses simulated agent execution
   - Real Task tool integration pending

2. **Review error logs:**
   ```bash
   tail -n 50 ~/.claude/logs/orchestrator.log | grep ERROR
   ```

3. **Enable debug mode:**
   ```bash
   export FDA_DEBUG=1
   python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py execute \
     --task "..." \
     --files "..." \
     --debug
   ```

4. **Reduce team size:**
   ```bash
   --max-agents 5  # Smaller teams = fewer failure points
   ```

### Performance Optimization

**Problem:** Orchestrator too slow for large files or complex reviews

**Solutions:**

1. **Limit file scope:**
   ```bash
   # Instead of:
   --files "**/*.py"  # All Python files

   # Use:
   --files "api/*.py,models/*.py"  # Specific directories
   ```

2. **Process in batches:**
   ```bash
   # Split large reviews into smaller chunks
   python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py review \
     --task "Security audit - Phase 1: Authentication" \
     --files "api/auth.py,api/oauth.py" \
     --max-agents 8

   # Then Phase 2, Phase 3, etc.
   ```

3. **Use caching:**
   - Agent registry cached for 24 hours
   - Task profiles cached during batch operations

4. **Parallelize independent reviews:**
   ```bash
   # Run multiple orchestrators in parallel (different files)
   python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py review \
     --task "API security review" \
     --files "api/*.py" &

   python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py review \
     --task "Database security review" \
     --files "models/*.py" &
   ```

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
- **Linear Integration:** [LINEAR_INTEGRATION.md](LINEAR_INTEGRATION.md)
- **FDA Examples:** [FDA_EXAMPLES.md](FDA_EXAMPLES.md)
- **Orchestrator Architecture:** [../ORCHESTRATOR_ARCHITECTURE.md](../ORCHESTRATOR_ARCHITECTURE.md)
- **Command Reference:** [README.md](../README.md)
- **Migration Guide:** [MIGRATION_NOTICE.md](../MIGRATION_NOTICE.md)

### Support Channels

- **GitHub Issues:** https://github.com/andrewlasiter/fda-tools/issues
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

4. **Submit to:** https://github.com/andrewlasiter/fda-tools/issues
