# Error Handling Patterns

Standard error handling patterns for all FDA Predicate Assistant commands. Each command should follow these patterns for consistent user experience.

## Error Response Format

All errors follow this structure (per output-formatting.md R12):

```
ERROR: {Brief description of the problem}
  → {Specific action the user can take to fix it}
```

## Error Categories

### 1. Missing Input (User Error)

When required arguments are missing:

```
ERROR: Product code is required
  → Usage: /fda:{command} <PRODUCT_CODE> [options]
```

```
ERROR: --project NAME is required
  → Provide a project name: /fda:{command} --project my-device
```

### 2. Data Not Found (Expected)

When queried data doesn't exist in FDA databases:

```
ERROR: Product code "XYZ" not found in FDA classification database
  → Check the code at https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpcd/classification.cfm
  → Or use /fda:research --identify-code "device description" to find the code
```

```
ERROR: K-number "K999999" not found in openFDA 510(k) database
  → The device may be too new or the number may be incorrect
  → Try validating with /fda:validate K999999
```

### 3. API Unavailable (Degraded Mode)

When openFDA API is unreachable or returns errors:

```
⚠ DEGRADED MODE: openFDA API unavailable ({error details})
  Using cached data and flat files where possible.
  Some features may return incomplete results.
  → Check your network connection
  → Test API: /fda:configure --test-api
  → Disable API: /fda:configure --set openfda_enabled false
```

**Degraded mode behavior:**
- Commands continue executing with available data (flat files, cache)
- Output includes `⚠ DEGRADED` marker in title block
- Missing API data shown as `[API unavailable]` instead of blank
- No crash, no halt — always produce partial output

### 4. Missing Dependencies (Setup Error)

When required Python packages are not installed:

```
ERROR: Missing dependencies: {package list}
  → Install with: pip install {packages}
  → Full requirements: $FDA_PLUGIN_ROOT/scripts/requirements.txt
```

### 5. File System Errors

When project directories or files can't be accessed:

```
ERROR: Project directory not found: ~/fda-510k-data/projects/{name}
  → Create it: mkdir -p ~/fda-510k-data/projects/{name}
  → Or check your settings: /fda:configure --show
```

```
ERROR: Cannot write to {path}: Permission denied
  → Check directory permissions
  → Or set a different path: /fda:configure --set projects_dir /new/path
```

### 6. Plugin Not Found (Installation Error)

When the plugin installation path can't be resolved:

```
ERROR: Could not locate the FDA Predicate Assistant plugin installation
  → Make sure the plugin is installed and enabled
  → Check: ~/.claude/plugins/installed_plugins.json
```

## Standard Error Footer

Every command that encounters an error should still end with a next-steps suggestion:

```
Need help?
  → /fda:status — Check pipeline data availability
  → /fda:configure --show — View current settings
```

## Degraded Mode Specification

When any API call fails, commands enter "degraded mode":

1. **API result → null**: Replace with cached data if available, otherwise `[API unavailable]`
2. **Continue execution**: Never halt the command for API failures
3. **Mark output**: Add `⚠ DEGRADED` to the report title block
4. **Log the failure**: Note in output which data sources were unavailable
5. **Suggest recovery**: Include API test command in NEXT STEPS

### Example Degraded Output

```
  FDA Safety Intelligence Report (⚠ DEGRADED)
  OVE — Intervertebral Body Fusion Device
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: 2026-02-06 | v5.16.0

  ⚠ Some data sources were unavailable:
    MAUDE API: timeout after 15s
    Recall API: HTTP 503

AVAILABLE DATA
────────────────────────────────────────
  {Data from flat files and cache}

UNAVAILABLE DATA
────────────────────────────────────────
  MAUDE events: [API unavailable — run /fda:configure --test-api]
  Recall history: [API unavailable — cached data used if available]
```

## Centralized API Client

All commands should use the centralized API client at `scripts/fda_api_client.py` which provides:

- **LRU caching**: 7-day TTL, stored in `~/fda-510k-data/api_cache/`
- **Exponential backoff**: 3 retries with increasing wait times
- **Rate limit awareness**: Handles HTTP 429 with longer backoff
- **Degraded mode**: Returns `{"degraded": true, "error": "..."}` on failure

### Cache Management

Available via `/fda:configure`:

```
/fda:configure --cache-stats     — Show cache hit/miss/size stats
/fda:configure --clear-cache api — Clear API response cache
/fda:configure --clear-cache all — Clear all cached data
```
