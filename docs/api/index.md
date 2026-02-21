# API Reference

Auto-generated from docstrings in `plugins/fda_tools/lib/`.

All `lib/` modules use only Python stdlib imports (see
[ADR-005](../docs/adr/ADR-005-stdlib-only-lib-modules.md)).

## Module Groups

### Core Utilities
- [`config`](lib/config.md) — Project and environment configuration
- [`input_validators`](lib/input_validators.md) — FDA number and data validation
- [`subprocess_helpers`](lib/subprocess_helpers.md) — Safe subprocess execution
- [`import_helpers`](lib/import_helpers.md) — Runtime import utilities
- [`user_errors`](lib/user_errors.md) — User-facing error classes
- [`disclaimers`](lib/disclaimers.md) — Regulatory disclaimer text

### Data & Analytics
- [`fda_enrichment`](lib/fda_enrichment.md) — Phase 1+2 device enrichment
- [`feature_analytics`](lib/feature_analytics.md) — Privacy-preserving usage tracking
- [`performance_baseline`](lib/performance_baseline.md) — Benchmark timing
- [`gap_analyzer`](lib/gap_analyzer.md) — Regulatory gap identification
- [`predicate_ranker`](lib/predicate_ranker.md) — Predicate similarity scoring
- [`predicate_diversity`](lib/predicate_diversity.md) — Predicate set diversity
- [`combination_detector`](lib/combination_detector.md) — Combination product detection
- [`standards_gap_detector`](lib/standards_gap_detector.md) — Standards coverage gaps
- [`testing_gap_detector`](lib/testing_gap_detector.md) — Testing coverage gaps
- [`rwe_integration`](lib/rwe_integration.md) — Real-world evidence integration

### Storage & Caching
- [`cache_manager`](lib/cache_manager.md) — Disk-based API response caching
- [`secure_data_storage`](lib/secure_data_storage.md) — HMAC-integrity JSON storage
- [`backup_manager`](lib/backup_manager.md) — Project backup and restore
- [`postgres_database`](lib/postgres_database.md) — PostgreSQL offline device DB

### Security & Auth
- [`auth`](lib/auth.md) — Session-based authentication
- [`rbac`](lib/rbac.md) — Role-based access control decorators
- [`users`](lib/users.md) — User account management
- [`secure_argparse`](lib/secure_argparse.md) — Path-validating argument parser
- [`path_validator`](lib/path_validator.md) — Output path security validation
- [`monitoring_security`](lib/monitoring_security.md) — Security monitoring

### Observability
- [`monitoring`](lib/monitoring.md) — Health checks and metrics collection
- [`metrics`](lib/metrics.md) — SLO/SLI metric tracking
- [`health_checks`](lib/health_checks.md) — FastAPI health endpoints
- [`logger`](lib/logger.md) — Structured logging setup
- [`quota_tracker`](lib/quota_tracker.md) — API quota management

### Regulatory Processing
- [`estar_field_extractor`](lib/estar_field_extractor.md) — eSTAR XML field extraction
- [`ecopy_exporter`](lib/ecopy_exporter.md) — eCopy submission package export
- [`signatures`](lib/signatures.md) — Digital signature utilities
- [`manifest_validator`](lib/manifest_validator.md) — Submission manifest validation
- [`expert_validator`](lib/expert_validator.md) — Multi-agent consensus validation
- [`de_novo_support`](lib/de_novo_support.md) — De Novo pathway support
- [`hde_support`](lib/hde_support.md) — Humanitarian Device Exemption support

### Rate Limiting
- [`cross_process_rate_limiter`](lib/cross_process_rate_limiter.md) — File-lock rate limiter
- [`rate_limiter`](lib/rate_limiter.md) — Deprecation shim (use cross_process_rate_limiter)
