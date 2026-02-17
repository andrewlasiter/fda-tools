# Changelog

All notable changes to the FDA Tools Plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Current Version: 5.36.0

For the complete, detailed changelog, see [plugins/fda-tools/CHANGELOG.md](plugins/fda-tools/CHANGELOG.md).

## Recent Highlights

### [5.36.0] - 2026-02-16

**Smart Auto-Update & Section Analytics**

- Smart auto-update system with fingerprint-based FDA change detection
- Multi-product-code section comparison analysis
- Text similarity scoring (SequenceMatcher, Jaccard, Cosine algorithms)
- Temporal trend analysis for 510(k) submission sections
- Cross-product-code benchmarking capabilities

### [5.35.0] - 2026-02-15

**Real-time Data Pipelines & Monitoring (PMA Intelligence Phase 5)**

- Auto-refresh workflows for PMA data
- Section-level change detection
- Monitoring dashboard with severity classification
- Automated pipeline orchestration

### [5.34.0] - 2026-02-14

**Advanced Analytics & Machine Learning (PMA Intelligence Phase 4)**

- Approval probability scoring using decision trees
- Review time prediction with ML models
- Competitive intelligence dashboard
- Risk assessment capabilities

### [5.33.0] - 2026-02-13

**External Data Integration (PMA Intelligence Phase 3)**

- ClinicalTrials.gov integration
- PubMed literature search
- USPTO patent integration
- Automated data updates

### [5.32.0] - 2026-02-13

**Supplement Lifecycle Tracking (PMA Intelligence Phase 2)**

- Complete supplement tracking system
- Annual report compliance monitoring
- Post-approval study (PAS) monitoring
- Supplement approval probability scoring

### [5.31.0] - 2026-02-12

**PMA Comparison Engine (PMA Intelligence Phase 1)**

- Unified 510(k)/PMA predicate interface
- Cross-pathway comparison capabilities
- PMA-specific data extraction
- Clinical requirements mapping

### [5.30.0] - 2026-02-11

**SSED Download & Extraction**

- Automated SSED summary download
- 15-section structured extraction
- Integration with PMA workflow
- Comparison engine support

## Older Versions

See the [full CHANGELOG](plugins/fda-tools/CHANGELOG.md) for complete version history from 1.0.0 through 5.29.0.

## Version Numbering

FDA Tools follows semantic versioning:

- **Major** (X.0.0): Breaking changes to commands or data formats
- **Minor** (x.Y.0): New features, backward-compatible
- **Patch** (x.y.Z): Bug fixes, documentation updates

## Migration Guides

When upgrading across major versions, consult the migration guides in `docs/migrations/`.
