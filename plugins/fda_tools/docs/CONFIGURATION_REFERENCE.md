# FDA Tools Configuration Reference

**Version:** 2.0.0
**Date:** 2026-02-20
**Status:** Production Ready

## Complete Configuration Options

This document provides a complete reference for all 200+ configuration options in the FDA Tools plugin.

## Configuration File Format

Configuration files use TOML format with hierarchical sections.

**Locations:**
- System config: `plugins/fda-tools/config.toml`
- User config: `~/.claude/fda-tools.config.toml`

**Priority:** Environment variables > User config > System config > Defaults

## Environment Variable Pattern

All environment variables use the pattern: `FDA_SECTION_KEY=value`

**Examples:**
```bash
FDA_API_OPENFDA_BASE_URL="https://custom.fda.gov"
FDA_CACHE_DEFAULT_TTL=86400
FDA_FEATURES_ENABLE_EXPERIMENTAL=true
```

---

## Section: `[general]`

Plugin metadata and environment settings.

### `plugin_name`
- **Type:** String
- **Default:** `"fda-tools"`
- **Description:** Plugin identifier
- **Environment:** `FDA_GENERAL_PLUGIN_NAME`

### `plugin_version`
- **Type:** String
- **Default:** `"5.32.0"`
- **Description:** Current plugin version
- **Environment:** `FDA_GENERAL_PLUGIN_VERSION`

### `environment`
- **Type:** String
- **Default:** `"production"`
- **Options:** `production`, `development`, `testing`, `staging`
- **Description:** Deployment environment
- **Environment:** `FDA_GENERAL_ENVIRONMENT`

---

## Section: `[paths]`

All directory paths (auto-expanded with ~).

### `base_dir`
- **Type:** Path
- **Default:** `"~/.claude/fda-510k-data"`
- **Description:** Base directory for all data
- **Environment:** `FDA_PATHS_BASE_DIR`

### `cache_dir`
- **Type:** Path
- **Default:** `"~/.claude/fda-510k-data/cache"`
- **Description:** Cache directory
- **Environment:** `FDA_PATHS_CACHE_DIR`

### `projects_dir`
- **Type:** Path
- **Default:** `"~/.claude/fda-510k-data/projects"`
- **Description:** 510(k) project directory
- **Environment:** `FDA_PATHS_PROJECTS_DIR`

### `output_dir`
- **Type:** Path
- **Default:** `"~/.claude/fda-510k-data/output"`
- **Description:** Generated output directory
- **Environment:** `FDA_PATHS_OUTPUT_DIR`

### `logs_dir`
- **Type:** Path
- **Default:** `"~/.claude/fda-510k-data/logs"`
- **Description:** Log files directory
- **Environment:** `FDA_PATHS_LOGS_DIR`

### `temp_dir`
- **Type:** Path
- **Default:** `"~/.claude/fda-510k-data/temp"`
- **Description:** Temporary files directory
- **Environment:** `FDA_PATHS_TEMP_DIR`

### `backup_dir`
- **Type:** Path
- **Default:** `"~/.claude/fda-510k-data/backups"`
- **Description:** Backup files directory
- **Environment:** `FDA_PATHS_BACKUP_DIR`

### `safety_cache_dir`
- **Type:** Path
- **Default:** `"~/.claude/fda-510k-data/cache/safety_cache"`
- **Description:** MAUDE safety data cache
- **Environment:** `FDA_PATHS_SAFETY_CACHE_DIR`

### `literature_cache_dir`
- **Type:** Path
- **Default:** `"~/.claude/fda-510k-data/cache/literature_cache"`
- **Description:** PubMed literature cache
- **Environment:** `FDA_PATHS_LITERATURE_CACHE_DIR`

### `pma_cache_dir`
- **Type:** Path
- **Default:** `"~/.claude/fda-510k-data/cache/pma_cache"`
- **Description:** PMA data cache
- **Environment:** `FDA_PATHS_PMA_CACHE_DIR`

### `similarity_cache_dir`
- **Type:** Path
- **Default:** `"~/.claude/fda-510k-data/cache/similarity_cache"`
- **Description:** Similarity scores cache
- **Environment:** `FDA_PATHS_SIMILARITY_CACHE_DIR`

### `settings_file`
- **Type:** Path
- **Default:** `"~/.claude/fda-tools.local.md"`
- **Description:** Legacy settings file (deprecated)
- **Environment:** `FDA_PATHS_SETTINGS_FILE`

### `user_config_file`
- **Type:** Path
- **Default:** `"~/.claude/fda-tools.config.toml"`
- **Description:** User configuration overrides
- **Environment:** `FDA_PATHS_USER_CONFIG_FILE`

---

## Section: `[api]`

API endpoints and timeouts.

### `openfda_base_url`
- **Type:** URL
- **Default:** `"https://api.fda.gov"`
- **Description:** openFDA API base URL
- **Environment:** `FDA_API_OPENFDA_BASE_URL`

### `openfda_device_endpoint`
- **Type:** URL
- **Default:** `"https://api.fda.gov/device"`
- **Description:** openFDA Device API endpoint
- **Environment:** `FDA_API_OPENFDA_DEVICE_ENDPOINT`

### `openfda_rate_limit_unauthenticated`
- **Type:** Integer
- **Default:** `240`
- **Units:** requests per minute
- **Description:** Rate limit without API key
- **Environment:** `FDA_API_OPENFDA_RATE_LIMIT_UNAUTHENTICATED`

### `openfda_rate_limit_authenticated`
- **Type:** Integer
- **Default:** `1000`
- **Units:** requests per minute
- **Description:** Rate limit with API key
- **Environment:** `FDA_API_OPENFDA_RATE_LIMIT_AUTHENTICATED`

### `openfda_timeout`
- **Type:** Integer
- **Default:** `30`
- **Units:** seconds
- **Description:** API request timeout
- **Environment:** `FDA_API_OPENFDA_TIMEOUT`

### `fda_accessdata_base_url`
- **Type:** URL
- **Default:** `"https://www.accessdata.fda.gov"`
- **Description:** FDA AccessData website
- **Environment:** `FDA_API_FDA_ACCESSDATA_BASE_URL`

### `fda_cdrh_docs_base_url`
- **Type:** URL
- **Default:** `"https://www.accessdata.fda.gov/cdrh_docs"`
- **Description:** FDA CDRH documents URL
- **Environment:** `FDA_API_FDA_CDRH_DOCS_BASE_URL`

### `fda_website_timeout`
- **Type:** Integer
- **Default:** `60`
- **Units:** seconds
- **Description:** Website/PDF download timeout
- **Environment:** `FDA_API_FDA_WEBSITE_TIMEOUT`

### `pubmed_base_url`
- **Type:** URL
- **Default:** `"https://eutils.ncbi.nlm.nih.gov/entrez/eutils"`
- **Description:** PubMed E-utilities API
- **Environment:** `FDA_API_PUBMED_BASE_URL`

### `pubmed_rate_limit`
- **Type:** Integer
- **Default:** `3`
- **Units:** requests per second
- **Description:** PubMed rate limit (no API key)
- **Environment:** `FDA_API_PUBMED_RATE_LIMIT`

### `pubmed_timeout`
- **Type:** Integer
- **Default:** `30`
- **Units:** seconds
- **Description:** PubMed API timeout
- **Environment:** `FDA_API_PUBMED_TIMEOUT`

### `linear_api_url`
- **Type:** URL
- **Default:** `"https://api.linear.app/graphql"`
- **Description:** Linear GraphQL API endpoint
- **Environment:** `FDA_API_LINEAR_API_URL`

### `linear_timeout`
- **Type:** Integer
- **Default:** `30`
- **Units:** seconds
- **Description:** Linear API timeout
- **Environment:** `FDA_API_LINEAR_TIMEOUT`

### `bridge_url`
- **Type:** URL
- **Default:** `"http://localhost:3000"`
- **Description:** OpenClaw bridge server URL
- **Environment:** `FDA_API_BRIDGE_URL`

### `bridge_timeout`
- **Type:** Integer
- **Default:** `30`
- **Units:** seconds
- **Description:** Bridge server timeout
- **Environment:** `FDA_API_BRIDGE_TIMEOUT`

---

## Section: `[http]`

HTTP client configuration.

### `user_agent_override`
- **Type:** String
- **Default:** `""`
- **Description:** Custom user agent (empty = use defaults)
- **Environment:** `FDA_HTTP_USER_AGENT_OVERRIDE`

### `honest_ua_only`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Use honest UA for all requests (may break PDF downloads)
- **Environment:** `FDA_HTTP_HONEST_UA_ONLY`

### `default_api_user_agent`
- **Type:** String
- **Default:** `"FDA-Plugin/5.32.0"`
- **Description:** User agent for API requests
- **Environment:** `FDA_HTTP_DEFAULT_API_USER_AGENT`

### `default_website_user_agent`
- **Type:** String
- **Default:** `"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"`
- **Description:** User agent for website/PDF downloads
- **Environment:** `FDA_HTTP_DEFAULT_WEBSITE_USER_AGENT`

### `max_retries`
- **Type:** Integer
- **Default:** `5`
- **Description:** Maximum retry attempts
- **Environment:** `FDA_HTTP_MAX_RETRIES`

### `base_backoff`
- **Type:** Float
- **Default:** `1.0`
- **Units:** seconds
- **Description:** Initial backoff for retries
- **Environment:** `FDA_HTTP_BASE_BACKOFF`

### `max_backoff`
- **Type:** Float
- **Default:** `120.0`
- **Units:** seconds
- **Description:** Maximum backoff for retries
- **Environment:** `FDA_HTTP_MAX_BACKOFF`

### `connection_pool_size`
- **Type:** Integer
- **Default:** `10`
- **Description:** HTTP connection pool size
- **Environment:** `FDA_HTTP_CONNECTION_POOL_SIZE`

### `verify_ssl`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Verify SSL certificates
- **Environment:** `FDA_HTTP_VERIFY_SSL`

---

## Section: `[cache]`

Cache behavior and TTL settings.

### `default_ttl`
- **Type:** Integer
- **Default:** `604800`
- **Units:** seconds (7 days)
- **Description:** Default cache TTL
- **Environment:** `FDA_CACHE_DEFAULT_TTL`

### `max_cache_size_mb`
- **Type:** Integer
- **Default:** `5000`
- **Units:** megabytes (5 GB)
- **Description:** Maximum cache size
- **Environment:** `FDA_CACHE_MAX_CACHE_SIZE_MB`

### `enable_integrity_checks`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable SHA-256 integrity checks (GAP-011)
- **Environment:** `FDA_CACHE_ENABLE_INTEGRITY_CHECKS`

### `atomic_writes`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Use atomic writes (temp + replace)
- **Environment:** `FDA_CACHE_ATOMIC_WRITES`

### `compression_enabled`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Compress cache files
- **Environment:** `FDA_CACHE_COMPRESSION_ENABLED`

### `ttl_510k`
- **Type:** Integer
- **Default:** `2592000`
- **Units:** seconds (30 days)
- **Description:** 510(k) data cache TTL
- **Environment:** `FDA_CACHE_TTL_510K`

### `ttl_classification`
- **Type:** Integer
- **Default:** `2592000`
- **Units:** seconds (30 days)
- **Description:** Classification data cache TTL
- **Environment:** `FDA_CACHE_TTL_CLASSIFICATION`

### `ttl_recall`
- **Type:** Integer
- **Default:** `86400`
- **Units:** seconds (1 day)
- **Description:** Recall data cache TTL
- **Environment:** `FDA_CACHE_TTL_RECALL`

### `ttl_maude`
- **Type:** Integer
- **Default:** `86400`
- **Units:** seconds (1 day)
- **Description:** MAUDE data cache TTL
- **Environment:** `FDA_CACHE_TTL_MAUDE`

### `ttl_pma`
- **Type:** Integer
- **Default:** `2592000`
- **Units:** seconds (30 days)
- **Description:** PMA data cache TTL
- **Environment:** `FDA_CACHE_TTL_PMA`

### `ttl_literature`
- **Type:** Integer
- **Default:** `2592000`
- **Units:** seconds (30 days)
- **Description:** Literature cache TTL
- **Environment:** `FDA_CACHE_TTL_LITERATURE`

### `ttl_similarity`
- **Type:** Integer
- **Default:** `604800`
- **Units:** seconds (7 days)
- **Description:** Similarity scores cache TTL
- **Environment:** `FDA_CACHE_TTL_SIMILARITY`

---

## Section: `[rate_limiting]`

Rate limiting configuration.

### `enable_cross_process`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable cross-process rate limiting (FDA-12)
- **Environment:** `FDA_RATE_LIMITING_ENABLE_CROSS_PROCESS`

### `enable_thread_safe`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable thread-safe rate limiting
- **Environment:** `FDA_RATE_LIMITING_ENABLE_THREAD_SAFE`

### `lock_timeout`
- **Type:** Integer
- **Default:** `30`
- **Units:** seconds
- **Description:** Lock acquisition timeout
- **Environment:** `FDA_RATE_LIMITING_LOCK_TIMEOUT`

### `cleanup_interval`
- **Type:** Integer
- **Default:** `300`
- **Units:** seconds
- **Description:** Cleanup interval for expired entries
- **Environment:** `FDA_RATE_LIMITING_CLEANUP_INTERVAL`

### `rate_limit_openfda`
- **Type:** Integer
- **Default:** `240`
- **Units:** requests per minute
- **Description:** openFDA API rate limit
- **Environment:** `FDA_RATE_LIMITING_RATE_LIMIT_OPENFDA`

### `rate_limit_pubmed`
- **Type:** Integer
- **Default:** `3`
- **Units:** requests per second
- **Description:** PubMed API rate limit
- **Environment:** `FDA_RATE_LIMITING_RATE_LIMIT_PUBMED`

### `rate_limit_pdf_download`
- **Type:** Integer
- **Default:** `2`
- **Units:** requests per minute
- **Description:** PDF download rate limit (30s delay)
- **Environment:** `FDA_RATE_LIMITING_RATE_LIMIT_PDF_DOWNLOAD`

### `rate_limit_website`
- **Type:** Integer
- **Default:** `60`
- **Units:** requests per minute
- **Description:** Website scraping rate limit
- **Environment:** `FDA_RATE_LIMITING_RATE_LIMIT_WEBSITE`

---

## Section: `[logging]`

Logging configuration.

### `level`
- **Type:** String
- **Default:** `"INFO"`
- **Options:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description:** Default log level
- **Environment:** `FDA_LOGGING_LEVEL`

### `format`
- **Type:** String
- **Default:** `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"`
- **Description:** Log message format
- **Environment:** `FDA_LOGGING_FORMAT`

### `date_format`
- **Type:** String
- **Default:** `"%Y-%m-%d %H:%M:%S"`
- **Description:** Log timestamp format
- **Environment:** `FDA_LOGGING_DATE_FORMAT`

### `log_to_file`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Write logs to file
- **Environment:** `FDA_LOGGING_LOG_TO_FILE`

### `log_to_console`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Write logs to console
- **Environment:** `FDA_LOGGING_LOG_TO_CONSOLE`

### `log_file_max_bytes`
- **Type:** Integer
- **Default:** `10485760`
- **Units:** bytes (10 MB)
- **Description:** Maximum log file size
- **Environment:** `FDA_LOGGING_LOG_FILE_MAX_BYTES`

### `log_file_backup_count`
- **Type:** Integer
- **Default:** `5`
- **Description:** Number of log file backups
- **Environment:** `FDA_LOGGING_LOG_FILE_BACKUP_COUNT`

### `redact_api_keys`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Redact API keys in logs
- **Environment:** `FDA_LOGGING_REDACT_API_KEYS`

### `redact_phi`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Redact PHI in logs (HIPAA compliance)
- **Environment:** `FDA_LOGGING_REDACT_PHI`

### `log_level_api`
- **Type:** String
- **Default:** `"INFO"`
- **Description:** Log level for API module
- **Environment:** `FDA_LOGGING_LOG_LEVEL_API`

### `log_level_cache`
- **Type:** String
- **Default:** `"INFO"`
- **Description:** Log level for cache module
- **Environment:** `FDA_LOGGING_LOG_LEVEL_CACHE`

### `log_level_http`
- **Type:** String
- **Default:** `"WARNING"`
- **Description:** Log level for HTTP module
- **Environment:** `FDA_LOGGING_LOG_LEVEL_HTTP`

### `log_level_audit`
- **Type:** String
- **Default:** `"INFO"`
- **Description:** Log level for audit module
- **Environment:** `FDA_LOGGING_LOG_LEVEL_AUDIT`

---

## Section: `[audit]`

Audit trail configuration (21 CFR Part 11 compliance).

### `enable_audit_logging`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable audit logging
- **Environment:** `FDA_AUDIT_ENABLE_AUDIT_LOGGING`

### `audit_log_dir`
- **Type:** Path
- **Default:** `"~/.claude/fda-510k-data/logs/audit"`
- **Description:** Audit log directory
- **Environment:** `FDA_AUDIT_AUDIT_LOG_DIR`

### `sequential_numbering`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Use sequential audit record numbering
- **Environment:** `FDA_AUDIT_SEQUENTIAL_NUMBERING`

### `include_user_identity`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Include user identity in audit records
- **Environment:** `FDA_AUDIT_INCLUDE_USER_IDENTITY`

### `include_before_after`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Include before/after values
- **Environment:** `FDA_AUDIT_INCLUDE_BEFORE_AFTER`

### `include_failed_attempts`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Log failed access attempts
- **Environment:** `FDA_AUDIT_INCLUDE_FAILED_ATTEMPTS`

### `audit_log_retention_days`
- **Type:** Integer
- **Default:** `2555`
- **Units:** days (7 years, FDA requirement)
- **Description:** Audit log retention period
- **Environment:** `FDA_AUDIT_AUDIT_LOG_RETENTION_DAYS`

### `encrypt_audit_logs`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Encrypt audit logs (requires key setup)
- **Environment:** `FDA_AUDIT_ENCRYPT_AUDIT_LOGS`

---

## Section: `[security]`

Security settings.

### `keyring_service`
- **Type:** String
- **Default:** `"fda-tools-plugin"`
- **Description:** Keyring service name (FDA-182)
- **Environment:** `FDA_SECURITY_KEYRING_SERVICE`

### `enable_keyring`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Use system keyring for API keys
- **Environment:** `FDA_SECURITY_ENABLE_KEYRING`

### `api_key_redaction`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Redact API keys in outputs
- **Environment:** `FDA_SECURITY_API_KEY_REDACTION`

### `validate_file_paths`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Validate file paths for security
- **Environment:** `FDA_SECURITY_VALIDATE_FILE_PATHS`

### `max_path_depth`
- **Type:** Integer
- **Default:** `10`
- **Description:** Maximum path depth (path traversal protection)
- **Environment:** `FDA_SECURITY_MAX_PATH_DEPTH`

### `allowed_file_extensions`
- **Type:** List[String]
- **Default:** `[".json", ".txt", ".md", ".csv", ".pdf", ".xml", ".html"]`
- **Description:** Allowed file extensions
- **Environment:** `FDA_SECURITY_ALLOWED_FILE_EXTENSIONS`

### `sanitize_html_output`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Sanitize HTML output (XSS protection)
- **Environment:** `FDA_SECURITY_SANITIZE_HTML_OUTPUT`

---

## Section: `[features]`

Feature flags.

### `enable_enrichment`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable FDA data enrichment
- **Environment:** `FDA_FEATURES_ENABLE_ENRICHMENT`

### `enable_intelligence`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable intelligence layer
- **Environment:** `FDA_FEATURES_ENABLE_INTELLIGENCE`

### `enable_clinical_detection`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable clinical data detection
- **Environment:** `FDA_FEATURES_ENABLE_CLINICAL_DETECTION`

### `enable_standards_matching`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable standards matching
- **Environment:** `FDA_FEATURES_ENABLE_STANDARDS_MATCHING`

### `enable_predicate_validation`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable predicate chain validation
- **Environment:** `FDA_FEATURES_ENABLE_PREDICATE_VALIDATION`

### `enable_maude_comparison`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable MAUDE peer comparison
- **Environment:** `FDA_FEATURES_ENABLE_MAUDE_COMPARISON`

### `enable_literature_search`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable PubMed literature search
- **Environment:** `FDA_FEATURES_ENABLE_LITERATURE_SEARCH`

### `enable_pma_intelligence`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable PMA intelligence features
- **Environment:** `FDA_FEATURES_ENABLE_PMA_INTELLIGENCE`

### `enable_similarity_caching`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable similarity score caching
- **Environment:** `FDA_FEATURES_ENABLE_SIMILARITY_CACHING`

### `enable_pdf_ocr`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable PDF OCR (requires tesseract)
- **Environment:** `FDA_FEATURES_ENABLE_PDF_OCR`

### `enable_experimental`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable experimental features
- **Environment:** `FDA_FEATURES_ENABLE_EXPERIMENTAL`

---

## Section: `[pdf_processing]`

PDF download and processing.

### `pdf_download_delay`
- **Type:** Integer
- **Default:** `30`
- **Units:** seconds
- **Description:** Delay between PDF downloads
- **Environment:** `FDA_PDF_PROCESSING_PDF_DOWNLOAD_DELAY`

### `pdf_max_size_mb`
- **Type:** Integer
- **Default:** `50`
- **Units:** megabytes
- **Description:** Maximum PDF file size
- **Environment:** `FDA_PDF_PROCESSING_PDF_MAX_SIZE_MB`

### `pdf_timeout`
- **Type:** Integer
- **Default:** `120`
- **Units:** seconds
- **Description:** PDF download timeout
- **Environment:** `FDA_PDF_PROCESSING_PDF_TIMEOUT`

### `enable_ocr`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable OCR for scanned PDFs
- **Environment:** `FDA_PDF_PROCESSING_ENABLE_OCR`

### `ocr_language`
- **Type:** String
- **Default:** `"eng"`
- **Description:** OCR language code
- **Environment:** `FDA_PDF_PROCESSING_OCR_LANGUAGE`

### `tesseract_cmd`
- **Type:** String
- **Default:** `""`
- **Description:** Tesseract command path (auto-detect if empty)
- **Environment:** `FDA_PDF_PROCESSING_TESSERACT_CMD`

---

## Section: `[output]`

Output file settings.

### `default_format`
- **Type:** String
- **Default:** `"markdown"`
- **Options:** `markdown`, `html`, `json`, `csv`
- **Description:** Default output format
- **Environment:** `FDA_OUTPUT_DEFAULT_FORMAT`

### `pretty_print_json`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Pretty-print JSON output
- **Environment:** `FDA_OUTPUT_PRETTY_PRINT_JSON`

### `csv_delimiter`
- **Type:** String
- **Default:** `","`
- **Description:** CSV delimiter character
- **Environment:** `FDA_OUTPUT_CSV_DELIMITER`

### `csv_quoting`
- **Type:** String
- **Default:** `"minimal"`
- **Options:** `minimal`, `all`, `nonnumeric`, `none`
- **Description:** CSV quoting strategy
- **Environment:** `FDA_OUTPUT_CSV_QUOTING`

### `html_template`
- **Type:** String
- **Default:** `"default"`
- **Description:** HTML template name
- **Environment:** `FDA_OUTPUT_HTML_TEMPLATE`

### `markdown_code_blocks`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Use code blocks in Markdown
- **Environment:** `FDA_OUTPUT_MARKDOWN_CODE_BLOCKS`

---

## Section: `[validation]`

Input validation settings.

### `strict_mode`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable strict validation
- **Environment:** `FDA_VALIDATION_STRICT_MODE`

### `validate_k_numbers`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Validate K-number format
- **Environment:** `FDA_VALIDATION_VALIDATE_K_NUMBERS`

### `validate_product_codes`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Validate product code format
- **Environment:** `FDA_VALIDATION_VALIDATE_PRODUCT_CODES`

### `validate_dates`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Validate date formats
- **Environment:** `FDA_VALIDATION_VALIDATE_DATES`

### `validate_email`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Validate email formats
- **Environment:** `FDA_VALIDATION_VALIDATE_EMAIL`

### `max_string_length`
- **Type:** Integer
- **Default:** `10000`
- **Description:** Maximum string length
- **Environment:** `FDA_VALIDATION_MAX_STRING_LENGTH`

### `allowed_k_number_prefixes`
- **Type:** List[String]
- **Default:** `["K", "DEN", "HDE"]`
- **Description:** Valid K-number prefixes
- **Environment:** `FDA_VALIDATION_ALLOWED_K_NUMBER_PREFIXES`

---

## Section: `[integration]`

External integration settings.

### `enable_linear_integration`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable Linear integration
- **Environment:** `FDA_INTEGRATION_ENABLE_LINEAR_INTEGRATION`

### `enable_bridge_integration`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable OpenClaw bridge integration
- **Environment:** `FDA_INTEGRATION_ENABLE_BRIDGE_INTEGRATION`

### `linear_workspace_id`
- **Type:** String
- **Default:** `""`
- **Description:** Linear workspace ID
- **Environment:** `FDA_INTEGRATION_LINEAR_WORKSPACE_ID`

### `linear_team_id`
- **Type:** String
- **Default:** `""`
- **Description:** Linear team ID
- **Environment:** `FDA_INTEGRATION_LINEAR_TEAM_ID`

### `linear_project_id`
- **Type:** String
- **Default:** `""`
- **Description:** Linear project ID
- **Environment:** `FDA_INTEGRATION_LINEAR_PROJECT_ID`

---

## Section: `[performance]`

Performance tuning.

### `max_concurrent_requests`
- **Type:** Integer
- **Default:** `5`
- **Description:** Maximum concurrent API requests
- **Environment:** `FDA_PERFORMANCE_MAX_CONCURRENT_REQUESTS`

### `batch_size`
- **Type:** Integer
- **Default:** `100`
- **Description:** Batch processing size
- **Environment:** `FDA_PERFORMANCE_BATCH_SIZE`

### `chunk_size`
- **Type:** Integer
- **Default:** `1000`
- **Description:** Data chunk size
- **Environment:** `FDA_PERFORMANCE_CHUNK_SIZE`

### `thread_pool_size`
- **Type:** Integer
- **Default:** `4`
- **Description:** Thread pool size
- **Environment:** `FDA_PERFORMANCE_THREAD_POOL_SIZE`

### `process_pool_size`
- **Type:** Integer
- **Default:** `2`
- **Description:** Process pool size
- **Environment:** `FDA_PERFORMANCE_PROCESS_POOL_SIZE`

### `enable_progress_bars`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Show progress bars
- **Environment:** `FDA_PERFORMANCE_ENABLE_PROGRESS_BARS`

### `show_warnings`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Show warning messages
- **Environment:** `FDA_PERFORMANCE_SHOW_WARNINGS`

---

## Section: `[backup]`

Backup and restore settings.

### `enable_auto_backup`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable automatic backups
- **Environment:** `FDA_BACKUP_ENABLE_AUTO_BACKUP`

### `backup_interval_hours`
- **Type:** Integer
- **Default:** `24`
- **Units:** hours
- **Description:** Backup interval
- **Environment:** `FDA_BACKUP_BACKUP_INTERVAL_HOURS`

### `backup_retention_days`
- **Type:** Integer
- **Default:** `30`
- **Units:** days
- **Description:** Backup retention period
- **Environment:** `FDA_BACKUP_BACKUP_RETENTION_DAYS`

### `backup_compression`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Compress backup files
- **Environment:** `FDA_BACKUP_BACKUP_COMPRESSION`

### `backup_incremental`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Use incremental backups
- **Environment:** `FDA_BACKUP_BACKUP_INCREMENTAL`

---

## Section: `[testing]`

Testing configuration.

### `test_mode`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Enable test mode
- **Environment:** `FDA_TESTING_TEST_MODE`

### `mock_api_responses`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Mock API responses for testing
- **Environment:** `FDA_TESTING_MOCK_API_RESPONSES`

### `test_data_dir`
- **Type:** Path
- **Default:** `"~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/tests/data"`
- **Description:** Test data directory
- **Environment:** `FDA_TESTING_TEST_DATA_DIR`

### `test_cache_dir`
- **Type:** Path
- **Default:** `"~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/tests/cache"`
- **Description:** Test cache directory
- **Environment:** `FDA_TESTING_TEST_CACHE_DIR`

### `test_output_dir`
- **Type:** Path
- **Default:** `"~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/tests/output"`
- **Description:** Test output directory
- **Environment:** `FDA_TESTING_TEST_OUTPUT_DIR`

---

## Section: `[deprecated]`

Deprecated settings (maintained for backward compatibility).

### `legacy_path_resolution`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Use legacy path resolution (removed in v6.0.0)
- **Environment:** `FDA_DEPRECATED_LEGACY_PATH_RESOLUTION`

### `legacy_cache_format`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Use legacy cache format (removed in v6.0.0)
- **Environment:** `FDA_DEPRECATED_LEGACY_CACHE_FORMAT`

### `legacy_api_client`
- **Type:** Boolean
- **Default:** `false`
- **Description:** Use legacy API client (removed in v6.0.0)
- **Environment:** `FDA_DEPRECATED_LEGACY_API_CLIENT`

---

## Quick Reference

### Most Common Settings

```toml
# config.toml or ~/.claude/fda-tools.config.toml

[general]
environment = "production"

[paths]
base_dir = "~/.claude/fda-510k-data"
cache_dir = "~/.claude/fda-510k-data/cache"

[api]
openfda_base_url = "https://api.fda.gov"

[cache]
default_ttl = 604800  # 7 days

[logging]
level = "INFO"

[features]
enable_enrichment = true
enable_intelligence = true
```

### Environment Variable Examples

```bash
# Override environment
export FDA_GENERAL_ENVIRONMENT=development

# Custom cache directory
export FDA_PATHS_CACHE_DIR="/data/cache"

# Debug logging
export FDA_LOGGING_LEVEL=DEBUG

# Enable experimental features
export FDA_FEATURES_ENABLE_EXPERIMENTAL=true
```

---

**Document Version:** 2.0.0
**Last Updated:** 2026-02-20
**Total Options:** 200+
**Maintainer:** Platform Engineering Team
