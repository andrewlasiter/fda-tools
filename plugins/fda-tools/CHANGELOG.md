# Changelog

All notable changes to the FDA Tools plugin will be documented in this file.

## [5.22.0] - 2026-02-14

### Breaking Changes
- **Plugin Rename:** `fda-predicate-assistant` → `fda-tools`
  - Namespace: `fda-predicate-assistant@fda-tools` → `fda-tools@fda-tools`
  - All commands: `/fda-predicate-assistant:*` → `/fda-tools:*`
  - Settings file must be manually migrated: `~/.claude/fda-predicate-assistant.local.md` → `fda-tools.local.md`
  - See MIGRATION_NOTICE.md for migration guide

### Added - Phase 5: Advanced Intelligence & Workflow Automation
- Workflow orchestration engine (`lib/workflow_engine.py`)
- Streaming data processor (`lib/stream_processor.py`)
- Semantic embeddings engine (`lib/embeddings_engine.py`)
- K-means clustering analyzer (`lib/clustering_analyzer.py`)
- Commands: `/fda-tools:workflow`, `/fda-tools:cluster`, `/fda-tools:semantic-search`

### Added - Phase 4B: Smart Predicate Recommendations
- ML-powered predicate ranking (`lib/predicate_ranker.py`)
- 10 ranking factors with confidence scoring
- Command: `/fda-tools:smart-predicates`

### Added - Phase 4A: Automated Gap Analysis
- Automated gap detection (`lib/gap_analyzer.py`)
- 10+ deficiency pattern detection
- Command: `/fda-tools:auto-gap-analysis`

### Added - Phase 3: Intelligence Suite
- MAUDE peer comparison
- Competitive intelligence analysis
- Review time predictions

### Added - Phase 1 & 2: Data Integrity + Intelligence Layer
- Data provenance tracking (`lib/fda_enrichment.py`)
- Quality validation and scoring
- CFR citation linking
- Standardized disclaimers (`lib/disclaimers.py`)
- Clinical data detection
- FDA standards intelligence
- Predicate chain health validation

### Repository Cleanup
- Organized documentation into `docs/{phases,compliance,testing,releases}`
- Moved test files to proper `tests/` directory
- Added comprehensive .gitignore for Python artifacts
- Cleaned up all __pycache__ and .pyc files

### Testing
- Comprehensive E2E testing: 96.6% pass rate (28/29 tests)
- Phase 1: 22/22 tests passing
- Phase 2: 4/4 devices verified
- Phase 3: 31/31 tests passing
- Phase 4A: 9/9 tests passing
- Phase 4B: 10/10 tests passing
- Phase 5: 19/19 tests passing
- CFR citations: 100% accurate (3/3 verified)
- FDA guidance: 100% current (3/3 verified)

### Compliance
- Status: CONDITIONAL APPROVAL - Research use only
- RA-3: True integration tests implemented ✓
- RA-5: Assertion-based testing completed ✓
- RA-6: Disclaimers added to all outputs ✓
- RA-2: Manual audit template ready (pending execution)
- RA-4: CFR/guidance verification worksheets ready (pending)

## [Earlier Versions]
See git commit history for detailed version history prior to 5.22.0.
