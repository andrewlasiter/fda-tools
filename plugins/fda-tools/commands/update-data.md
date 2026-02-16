---
description: Scan and update stale FDA data across projects
allowed-tools: [Bash, Read, AskUserQuestion]
argument-hint: "[--project NAME | --all-projects | --system-cache | --smart | --dry-run | --force]"
---

# FDA Data Update Manager

You are helping the user manage stale cached FDA data across their projects. This command provides batch freshness checking and update capabilities.

## Core Functionality

**Purpose:** Scan all projects for stale cached data (expired based on TTL) and provide batch update functionality with user control.

**Integration:** Uses `update_manager.py` which integrates with existing `fda_data_store.py` TTL logic (`is_expired()` and `TTL_TIERS`).

**Rate Limiting:** Updates are throttled at 500ms per request (2 req/sec) to respect API limits.

## Arguments

Parse user arguments to determine the operation mode:

- `--project NAME`: Operate on a specific project only
- `--all-projects`: Operate on all projects with stale data
- `--system-cache`: Clean expired files from the system API cache (~/.fda-510k-data/api_cache/)
- `--smart`: Smart change detection mode -- compare live API against stored fingerprints to find new clearances and recalls (see Mode E)
- `--dry-run`: Preview updates without executing (show what would be updated)
- `--force`: Skip confirmation prompts (use with caution)

**Default behavior** (no args): Scan all projects and show freshness summary, then ask user what to do.

## Command Workflow

### Step 1: Parse Arguments

Extract operation mode from user input:

```python
# Parse arguments from user input
args = parse_arguments(user_input)
# args = {
#     "project": str or None,
#     "all_projects": bool,
#     "system_cache": bool,
#     "dry_run": bool,
#     "force": bool
# }
```

### Step 2: Execute Operation Based on Mode

#### Mode A: Scan Only (default, no update flags)

1. Run scan to identify stale data:
   ```bash
   python3 plugins/fda-tools/scripts/update_manager.py --scan-all
   ```

2. Parse the scan results (JSON output with --quiet flag for scripting)

3. If stale data found, present summary to user:
   ```
   📊 Found stale data across 3 projects:

   Project: DQY_catheter_analysis
     - 5/12 queries stale (42%)
     - Oldest: recalls:DQY (15.3 days old, TTL: 1.0 days)

   Project: OVE_spinal_implant
     - 2/8 queries stale (25%)
     - Oldest: events:OVE:count:event_type.exact (26.1 days old, TTL: 1.0 days)

   Total stale: 7 queries across 3 projects
   ```

4. Ask user what to do next using AskUserQuestion:
   ```
   What would you like to do?
   Options:
   - Update all stale data (recommended)
   - Update specific project only
   - Preview updates first (dry-run)
   - Clean system cache only
   - Cancel
   ```

5. Based on user selection, proceed to the appropriate mode below.

#### Mode B: Update Specific Project

1. If `--project NAME` specified:
   - First show dry-run preview unless `--force` specified
   - Get user confirmation via AskUserQuestion
   - Execute update

2. Command sequence:
   ```bash
   # Preview (unless --force)
   python3 plugins/fda-tools/scripts/update_manager.py --project NAME --update --dry-run

   # After confirmation, execute
   python3 plugins/fda-tools/scripts/update_manager.py --project NAME --update
   ```

3. Show progress and results:
   ```
   🔄 Updating 5 stale queries for DQY_catheter_analysis...

   [1/5] Updating classification:DQY... ✅ SUCCESS
   [2/5] Updating recalls:DQY... ✅ SUCCESS
   [3/5] Updating events:DQY... ✅ SUCCESS
   [4/5] Updating events:DQY:count:event_type.exact... ✅ SUCCESS
   [5/5] Updating 510k-batch:K241335,K200123... ✅ SUCCESS

   ✅ Update complete: 5 updated, 0 failed
   ```

#### Mode C: Update All Projects

1. If `--all-projects` specified:
   - First run scan to identify all projects with stale data
   - Show summary of what will be updated
   - Get user confirmation via AskUserQuestion (unless `--force`)
   - Execute batch updates across all projects

2. Command sequence:
   ```bash
   # Scan first
   python3 plugins/fda-tools/scripts/update_manager.py --scan-all --quiet

   # Parse JSON, show summary, get confirmation

   # Execute (with or without dry-run)
   python3 plugins/fda-tools/scripts/update_manager.py --update-all [--dry-run]
   ```

3. Show overall progress:
   ```
   🔍 Found 3 projects with stale data
   📊 Total stale queries: 7

   [1/3] Project: DQY_catheter_analysis (5 stale)
   🔄 Updating 5 stale queries...
   ✅ Update complete: 5 updated, 0 failed

   [2/3] Project: OVE_spinal_implant (2 stale)
   🔄 Updating 2 stale queries...
   ✅ Update complete: 2 updated, 0 failed

   ====================================================
   🎯 Overall Summary:
     Projects updated: 3/3
     Queries updated: 7
     Queries failed: 0
   ```

#### Mode D: Clean System Cache

1. If `--system-cache` specified:
   - Scan API cache directory for expired files
   - Show preview of what will be deleted
   - Get user confirmation (unless `--force`)
   - Remove expired files and report size freed

2. Command:
   ```bash
   python3 plugins/fda-tools/scripts/update_manager.py --clean-cache
   ```

3. Show results:
   ```
   🗑️  Cleaning expired files from ~/fda-510k-data/api_cache/...
   ✅ Removed 47 expired files (125.43 MB freed)
   ```

#### Mode E: Smart Change Detection

Smart detection goes beyond TTL-based staleness checking. Instead of simply refreshing expired queries, it compares live FDA data against stored "fingerprints" to detect genuinely new data -- new 510(k) clearances, new recalls, and count changes.

**Concept: Fingerprints**

A fingerprint is a compact snapshot of what was known at the last check. It is stored in `data_manifest.json` under the `"fingerprints"` key:

```json
{
  "fingerprints": {
    "DQY": {
      "last_checked": "2026-02-16T10:00:00+00:00",
      "clearance_count": 147,
      "latest_k_number": "K251234",
      "latest_decision_date": "20260115",
      "recall_count": 3,
      "known_k_numbers": ["K251234", "K250987", "..."]
    }
  }
}
```

When `--smart` runs, it queries the live FDA API and compares against the fingerprint to identify new K-numbers and recalls that were not previously known.

**Workflow:**

1. If `--smart` specified (optionally with `--project NAME`):
   - Query live FDA API for each tracked product code
   - Compare current clearances/recalls against stored fingerprints
   - Report new items found

2. Command sequence:
   ```bash
   # Smart detection for a specific project
   python3 plugins/fda-tools/scripts/update_manager.py --smart --project NAME

   # Smart detection for all projects
   python3 plugins/fda-tools/scripts/update_manager.py --smart

   # Dry-run: preview what would be detected
   python3 plugins/fda-tools/scripts/update_manager.py --smart --project NAME --dry-run
   ```

3. Show results:
   ```
   Checking 2 product code(s) for project 'DQY_catheter_analysis'...
     [1/2] Checking DQY... 3 new clearance(s) found
     [2/2] Checking OVE... no changes

   ============================================================
   Smart Detection: DQY_catheter_analysis
   ============================================================
   Product codes checked: 2
   New clearances: 3
   New recalls: 0

     DQY: 3 new clearance(s)
       - K261001: Acme Vascular Catheter (20260210)
       - K261002: Beta Flow Catheter (20260205)
       - K261003: Gamma Access Catheter (20260201)
   ```

4. After detection, ask user if they want to trigger the pipeline:
   ```json
   {
     "questions": [
       {
         "question": "3 new clearances found for DQY. What would you like to do?",
         "header": "Smart Detection Results",
         "multiSelect": false,
         "options": [
           {
             "label": "Trigger pipeline (download + extract)",
             "description": "Run batchfetch and build_structured_cache for new K-numbers"
           },
           {
             "label": "View details only",
             "description": "Show full details of new clearances without processing"
           },
           {
             "label": "Done",
             "description": "Fingerprints updated, no further action"
           }
         ]
       }
     ]
   }
   ```

5. If user selects "Trigger pipeline", run:
   ```bash
   python3 plugins/fda-tools/scripts/change_detector.py --project NAME --trigger
   ```

**First-Time Usage:**

On the first `--smart` run for a project, the system creates a baseline fingerprint from the current API state. No changes will be detected because there is no previous state to compare against. The message will indicate "baseline created."

On subsequent runs, the system will detect any new clearances or recalls that appeared since the last check.

**Integration with change_detector.py:**

The `--smart` flag in `update_manager.py` calls `change_detector.detect_changes()` which handles:
- Loading/saving fingerprints from `data_manifest.json`
- Querying the FDA API for current clearance and recall counts
- Comparing against stored known K-numbers
- Updating fingerprints after each check

For pipeline triggering (downloading new PDFs and building structured cache), use `change_detector.trigger_pipeline()` or the standalone CLI:
```bash
python3 plugins/fda-tools/scripts/change_detector.py --project NAME --trigger
```

## User Interaction Patterns

### Pattern 1: First-Time User (No Arguments)

User types: `/fda-tools:update-data`

**Your response:**
1. Run scan
2. Show summary of stale data (if any)
3. Ask what to do next via AskUserQuestion with clear options
4. Execute based on user selection

### Pattern 2: Experienced User with Specific Intent

User types: `/fda-tools:update-data --all-projects`

**Your response:**
1. Run scan to identify stale data
2. Show "Found X queries across Y projects" summary
3. Ask for confirmation: "Proceed with batch update?"
4. Execute update if confirmed

### Pattern 3: Cautious User (Dry-Run First)

User types: `/fda-tools:update-data --all-projects --dry-run`

**Your response:**
1. Run dry-run mode
2. Show "Would update X queries" summary with details
3. Ask: "Execute these updates?"
4. If yes, re-run without --dry-run

### Pattern 4: Scripting/Automation (Force Mode)

User types: `/fda-tools:update-data --all-projects --force`

**Your response:**
1. Run update immediately without confirmation
2. Show progress and results
3. Report final status

### Pattern 5: Smart Detection (New Clearances)

User types: `/fda-tools:update-data --smart --project DQY_catheter_analysis`

**Your response:**
1. Run smart change detection for the project
2. Show summary of new clearances and recalls detected
3. If new items found, ask via AskUserQuestion whether to trigger pipeline
4. If user confirms, trigger batchfetch + structured cache build
5. Report final status including newly processed K-numbers

### Pattern 6: Smart Detection (All Projects)

User types: `/fda-tools:update-data --smart`

**Your response:**
1. Run smart change detection across all projects
2. Show per-project summary of changes
3. Show overall totals
4. For projects with changes, suggest running `--smart --project NAME` for pipeline trigger

## Error Handling

### Scenario: No Projects Found

```
⚠️  No FDA projects found in ~/fda-510k-data/projects/

This is expected if you haven't created any projects yet.
Use /fda-tools:extract or /fda-tools:research to create a project first.
```

### Scenario: No Stale Data

```
✅ All data is fresh!

No updates needed. All cached data is within TTL limits:
  - Classification data: 7 days
  - Recalls/Events: 24 hours
  - 510(k) data: 7 days
```

### Scenario: API Errors During Update

```
🔄 Updating 5 stale queries for DQY_catheter_analysis...

[1/5] Updating classification:DQY... ✅ SUCCESS
[2/5] Updating recalls:DQY... ❌ FAILED: HTTP 503: Service Unavailable
[3/5] Updating events:DQY... ⚠️  FAILED: API unavailable after 3 retries

✅ Update complete: 3 updated, 2 failed

⚠️  Some updates failed due to API errors. The failed queries will remain stale.
You can retry later by running this command again.
```

### Scenario: Invalid Project Name

```
❌ Error: Project 'invalid_name' not found

Available projects:
  - DQY_catheter_analysis
  - OVE_spinal_implant
  - GEI_electrosurgical

Use --scan-all to see all projects.
```

## TTL Reference

Remind users of the TTL tiers when explaining staleness:

- **Classification data**: 7 days (168 hours) — rarely changes
- **510(k) clearances**: 7 days (168 hours) — historical data
- **Recalls**: 24 hours — safety-critical, updates frequently
- **MAUDE events**: 24 hours — new events filed daily
- **Enforcement**: 24 hours — active enforcement changes
- **UDI data**: 7 days (168 hours) — device identifiers stable

## AskUserQuestion Usage

### Confirmation for Batch Updates

When about to update multiple queries, use AskUserQuestion:

```
{
  "questions": [
    {
      "question": "Update 7 stale queries across 3 projects?",
      "header": "Batch Update",
      "multiSelect": false,
      "options": [
        {
          "label": "Yes, update all (recommended)",
          "description": "Update all stale queries now (rate-limited to 2 req/sec)"
        },
        {
          "label": "Preview first (dry-run)",
          "description": "Show what would be updated without executing"
        },
        {
          "label": "Cancel",
          "description": "Exit without making changes"
        }
      ]
    }
  ]
}
```

### Operation Mode Selection

When user runs command with no args, ask what to do:

```
{
  "questions": [
    {
      "question": "What would you like to do with the stale data?",
      "header": "Action",
      "multiSelect": false,
      "options": [
        {
          "label": "Update all (recommended)",
          "description": "Update all 7 stale queries across 3 projects"
        },
        {
          "label": "Update specific project",
          "description": "Choose which project to update"
        },
        {
          "label": "Preview first",
          "description": "Dry-run mode to see what would change"
        },
        {
          "label": "Clean cache only",
          "description": "Remove expired API cache files to free disk space"
        }
      ]
    }
  ]
}
```

If user selects "Update specific project", follow up with another question listing the projects.

## Performance Notes

**Rate Limiting:** Updates are throttled at 500ms per request (2 req/sec) to comply with openFDA rate limits (240 req/min for unauthenticated, 1000 req/min with API key).

**Estimated Time:**
- 5 queries: ~2.5 seconds
- 20 queries: ~10 seconds
- 100 queries: ~50 seconds

**API Key Benefit:** If user has configured an API key in `~/.claude/fda-tools.local.md`, they get higher rate limits. Mention this if updating >50 queries.

## Integration Notes

**Script Location:** `plugins/fda-tools/scripts/update_manager.py`

**Dependencies:**
- Imports `fda_data_store.py` for `is_expired()`, `TTL_TIERS`, `load_manifest()`, `save_manifest()`
- Imports `fda_api_client.py` for `FDAClient` and API retry logic
- Imports `change_detector.py` for `detect_changes()`, `trigger_pipeline()` (smart mode)
- Uses existing cache in `~/fda-510k-data/api_cache/`

**Manifest Updates:** The script updates `data_manifest.json` files directly using the same logic as `fda_data_store.py`. Smart mode also writes fingerprints to `data_manifest.json` under the `"fingerprints"` key.

## Example User Sessions

### Session 1: Quick Scan and Update

```
User: /fda-tools:update-data