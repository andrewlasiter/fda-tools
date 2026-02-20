# Idempotency Matrix

## Overview

This document lists all scripts in the FDA Tools plugin and their idempotency
status. A script is considered **idempotent** if running it multiple times with
the same input produces the same result without unintended side effects.

For error recovery procedures, see [ERROR_RECOVERY.md](./ERROR_RECOVERY.md).

---

## Idempotency Status Legend

| Status | Meaning |
|--------|---------|
| YES | Safe to re-run. Produces identical results. No data loss risk. |
| PARTIAL | Safe to re-run with caveats. May overwrite existing data. |
| NO | Not safe to re-run blindly. May cause duplicates or data loss. |
| READ-ONLY | Does not modify any data. Always safe. |

---

## Script Idempotency Matrix

### Core Data Scripts

| Script | Idempotent | Resume Support | Side Effects | Notes |
|--------|-----------|----------------|--------------|-------|
| `batchfetch.py` | YES | YES | Downloads PDFs, creates CSV | Skips already-downloaded files |
| `fda_api_client.py` | YES | N/A (per-request) | Writes to API cache | Cache prevents duplicate API calls |
| `pma_ssed_cache.py` | YES | YES | Downloads PDFs to cache | Skips existing PDFs unless --force |
| `pma_data_store.py` | YES | N/A | Writes PMA data to cache | TTL-based refresh; safe to re-run |
| `fda_data_store.py` | YES | N/A | Writes 510(k) data | Manifest-based dedup |

### Analysis & Intelligence Scripts

| Script | Idempotent | Resume Support | Side Effects | Notes |
|--------|-----------|----------------|--------------|-------|
| `change_detector.py` | YES | N/A | Updates fingerprints in manifest | Non-destructive comparison |
| `data_refresh_orchestrator.py` | YES | YES | Refreshes expired data only | TTL-based; only touches stale data |
| `pma_section_extractor.py` | YES | N/A | Writes extracted_sections.json | Overwrites previous extraction |
| `pma_comparison.py` | READ-ONLY | N/A | None (stdout only) | Pure comparison, no file writes |
| `pma_intelligence.py` | YES | N/A | Writes intelligence reports | Overwrites previous report |
| `gap_analysis.py` | YES | N/A | Writes gap analysis report | Overwrites previous analysis |
| `risk_assessment.py` | READ-ONLY | N/A | None (stdout only) | Pure analysis |
| `approval_probability.py` | READ-ONLY | N/A | None (stdout only) | Pure calculation |
| `pathway_recommender.py` | READ-ONLY | N/A | None (stdout only) | Pure recommendation |
| `review_time_predictor.py` | READ-ONLY | N/A | None (stdout only) | Pure prediction |
| `timeline_predictor.py` | READ-ONLY | N/A | None (stdout only) | Pure prediction |
| `clinical_requirements_mapper.py` | READ-ONLY | N/A | None (stdout only) | Pure analysis |
| `maude_comparison.py` | YES | N/A | Writes comparison report | Overwrites previous report |

### Generation & Export Scripts

| Script | Idempotent | Resume Support | Side Effects | Notes |
|--------|-----------|----------------|--------------|-------|
| `estar_xml.py` | YES | N/A | Writes XML file | Overwrites previous XML |
| `markdown_to_html.py` | YES | N/A | Writes HTML file | Overwrites previous HTML |
| `quick_standards_generator.py` | YES | N/A | Writes standards list | Overwrites previous list |
| `auto_generate_device_standards.py` | YES | N/A | Writes standards data | Knowledge-based generation |
| `knowledge_based_generator.py` | YES | N/A | Writes generated content | Overwrites previous output |
| `competitive_dashboard.py` | YES | N/A | Writes dashboard data | Overwrites previous dashboard |
| `trend_visualization.py` | YES | N/A | Writes visualization data | Overwrites previous output |

### Project Management Scripts

| Script | Idempotent | Resume Support | Side Effects | Notes |
|--------|-----------|----------------|--------------|-------|
| `seed_test_project.py` | PARTIAL | N/A | Creates/overwrites project | Use --force to overwrite existing |
| `backup_project.py` | YES | N/A | Creates backup archive | New archive per run (timestamped) |
| `restore_project.py` | PARTIAL | N/A | Restores project files | May overwrite existing files |
| `migrate_manifest.py` | YES | N/A | Updates manifest schema | Detects current version; no-op if current |

### Monitoring & Tracking Scripts

| Script | Idempotent | Resume Support | Side Effects | Notes |
|--------|-----------|----------------|--------------|-------|
| `fda_approval_monitor.py` | YES | N/A | Updates monitoring state | Tracks what has been seen |
| `pas_monitor.py` | YES | N/A | Updates PAS tracking state | Tracks condition status |
| `supplement_tracker.py` | YES | N/A | Updates supplement state | Tracks new supplements |
| `annual_report_tracker.py` | YES | N/A | Updates report tracking | Tracks deadlines |
| `alert_sender.py` | NO | N/A | Sends notifications | May send duplicate alerts |
| `section_analytics.py` | READ-ONLY | N/A | None (stdout/report) | Pure analysis |

### Cache & Integrity Scripts

| Script | Idempotent | Resume Support | Side Effects | Notes |
|--------|-----------|----------------|--------------|-------|
| `cache_integrity.py` | READ-ONLY | N/A | None (unless --repair) | --repair removes corrupt files |
| `build_structured_cache.py` | YES | N/A | Rebuilds cache structure | Overwrites previous structure |
| `similarity_cache.py` | YES | N/A | Writes similarity data | Cache with dedup |

### Utility Scripts

| Script | Idempotent | Resume Support | Side Effects | Notes |
|--------|-----------|----------------|--------------|-------|
| `version.py` | READ-ONLY | N/A | None | Returns version string |
| `check_version.py` | READ-ONLY | N/A | None | Checks for updates |
| `update_version.py` | YES | N/A | Updates version file | Sets to specified version |
| `update_manager.py` | YES | N/A | Downloads/applies updates | Checks version before applying |
| `setup_api_key.py` | YES | N/A | Writes settings file | Overwrites existing key |
| `input_validators.py` | READ-ONLY | N/A | None (library) | Pure validation functions |
| `compliance_disclaimer.py` | READ-ONLY | N/A | None (library) | Returns disclaimer text |
| `subprocess_utils.py` | READ-ONLY | N/A | None (library) | Helper functions |
| `fda_http.py` | READ-ONLY | N/A | None (library) | HTTP session factory |
| `fda_audit_logger.py` | YES | N/A | Writes audit log | Append-only log file |

### Search & Validation Scripts

| Script | Idempotent | Resume Support | Side Effects | Notes |
|--------|-----------|----------------|--------------|-------|
| `full_text_search.py` | READ-ONLY | N/A | None | Pure search |
| `web_predicate_validator.py` | READ-ONLY | N/A | None | Pure validation |
| `unified_predicate.py` | YES | N/A | Writes combined results | Overwrites previous output |
| `predicate_extractor.py` | YES | N/A | Writes extracted data | Overwrites previous extraction |
| `fetch_predicate_data.py` | YES | N/A | Writes predicate data | Cache-first approach |
| `compare_sections.py` | READ-ONLY | N/A | None (stdout) | Pure comparison |
| `external_data_hub.py` | YES | N/A | Writes hub data | Aggregates external sources |
| `change_detection.py` | YES | N/A | Updates detection state | Compares against baseline |

### Test & Demo Scripts

| Script | Idempotent | Resume Support | Side Effects | Notes |
|--------|-----------|----------------|--------------|-------|
| `batch_seed.py` | PARTIAL | N/A | Creates test projects | Overwrites existing test projects |
| `batch_analyze.py` | READ-ONLY | N/A | Writes analysis report | Reads existing data |
| `verify_enhancement.py` | READ-ONLY | N/A | None | Verification only |
| `demo_diff_reporting.py` | READ-ONLY | N/A | None (stdout) | Demo output |
| `demo_progress_bar.py` | READ-ONLY | N/A | None (stdout) | Demo output |
| `demo_sklearn_warning.py` | READ-ONLY | N/A | None (stdout) | Demo output |
| `benchmark_similarity_cache.py` | READ-ONLY | N/A | None (stdout) | Performance benchmark |
| `test_backup_restore.py` | YES | N/A | Creates temp files | Cleans up after itself |

---

## Resume / Recovery Flag Support

The following scripts support explicit resume or recovery mechanisms:

| Script | Flag | Behavior |
|--------|------|----------|
| `batchfetch.py` | (automatic) | Skips already-downloaded files based on filename |
| `pma_ssed_cache.py` | `--force` | Re-downloads even if cached (without flag: skips existing) |
| `data_refresh_orchestrator.py` | `--force` | Refreshes all data regardless of TTL |
| `pma_ssed_cache.py` | `--clean-cache` | Evicts LRU files to fit within size limit |
| `cache_integrity.py` | `--repair` | Removes corrupt cache files |
| `seed_test_project.py` | `--force` | Overwrites existing project data |
| `restore_project.py` | `--no-overwrite` | Skips files that already exist at destination |

---

## Data Loss Risk Assessment

### No Risk (Safe to run anytime)

All READ-ONLY scripts and YES-idempotent scripts can be run at any time
without risk of data loss.

### Low Risk (Overwrites own output)

Scripts marked YES that write files will overwrite their own previous output.
The previous version is lost unless backed up. This is generally expected
behavior and not considered data loss.

### Medium Risk (May overwrite project data)

Scripts marked PARTIAL may overwrite user-modified project data. Always
back up important projects before using `--force` or re-running these scripts:

- `seed_test_project.py --force`
- `restore_project.py` (without --no-overwrite)
- `batch_seed.py`

### High Risk (External effects)

- `alert_sender.py` may send duplicate notifications if re-run. Use
  deduplication tracking in the monitoring scripts to prevent this.

---

## Best Practices

1. **Always check `--help`** before running a script for the first time.
2. **Back up projects** before running scripts with PARTIAL idempotency.
3. **Use `--dry-run`** where available to preview what will happen.
4. **Monitor disk space** when running batch downloads.
5. **Check rate limit status** with `python3 fda_api_client.py --health-check`
   before running multiple scripts in parallel.
6. **Use the --force flag sparingly** -- it bypasses safety checks.

---

**Document Version**: 1.0
**Last Updated**: 2026-02-17
**Total Scripts Documented**: 55+
