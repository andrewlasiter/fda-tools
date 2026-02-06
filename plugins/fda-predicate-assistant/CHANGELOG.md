# Changelog

## [3.0.0] - 2026-02-06

### Added — Tier 1: Autonomy
- `--full-auto` and `--auto-threshold` on `/fda:review` for zero-prompt predicate review
- `--infer` flag on guidance, presub, research, submission-outline, and compare-se for auto-detecting product codes from project data
- `--output FILE` on `/fda:summarize` for file persistence
- `--headless` flag on `predicate_extractor.py` with display detection
- TTY-aware prompts in `batchfetch.py` with non-interactive fallback
- `/fda:pipeline` command — full 7-step autonomous pipeline orchestrator
- Placeholder auto-fill: `[INSERT: ...]` → populated from `--device-description` and `--intended-use`
- Default stage selection in `/fda:extract` (no more prompts)

### Added — Tier 2: Best-in-Class Features
- `/fda:monitor` — real-time FDA clearance, recall, and MAUDE event monitoring
- `/fda:pathway` — algorithmic regulatory pathway recommendation (5 pathways scored 0-100)
- `/fda:test-plan` — risk-based testing plan with ISO 14971 gap analysis
- `/fda:assemble` — eSTAR directory structure assembly (17 sections with readiness tracking)
- `/fda:portfolio` — cross-project portfolio dashboard with shared predicate analysis
- `/fda:pccp` — Predetermined Change Control Plan generator for AI/ML devices
- `/fda:ask` — natural language regulatory Q&A
- `--competitor-deep` on `/fda:research` for applicant frequency, technology trends, and market timeline
- Extended confidence scoring (+20 bonus points: chain depth, SE table, applicant similarity, IFU overlap)

### Added — References
- `estar-structure.md` — eSTAR section structure and applicability matrix
- `pathway-decision-tree.md` — regulatory pathway decision flow and scoring weights
- `test-plan-framework.md` — ISO 14971 risk categories and device-type test lists
- `pccp-guidance.md` — FDA PCCP guidance overview and modification categories

## [2.0.0] - 2026-02-05

### Added
- `/fda:review` — interactive predicate review with 5-component confidence scoring
- `/fda:guidance` — FDA guidance lookup with requirements extraction and testing mapping
- `/fda:presub` — Pre-Submission meeting package generator
- `/fda:submission-outline` — full 510(k) outline with gap analysis
- `confidence-scoring.md` reference with scoring methodology
- `guidance-lookup.md` reference with search strategies
- `submission-structure.md` reference with outline templates

### Changed
- `/fda:extract` now includes safety scan integration
- `/fda:configure` now supports exclusion lists
- `/fda:research` now caches guidance for reuse
- `/fda:compare-se` now integrates with submission outline data
- Marketplace renamed from `local` to `fda-tools`

## [1.2.0] - 2026-02-05

### Added
- Disclaimers and warnings across all user-facing surfaces:
  - README.md: "Important Notices" section (privacy, accuracy, training data, not legal advice)
  - SKILL.md: Always-loaded disclaimer context for regulatory guidance responses
  - research.md: Disclaimer footer in research report output
  - compare-se.md: Disclaimer footer in SE comparison table output
- Section-aware predicate extraction in research command (SE sections weighted 3x)
- [SE]/[Ref] provenance tags on predicate candidates
- Extraction confidence transparency caveat in research output

## [1.1.0] - 2026-02-05

### Changed
- Portable plugin root resolution via `installed_plugins.json` runtime lookup
- Removed hardcoded paths; all data directories default to `~/fda-510k-data/`
- Added SessionStart hook as backup for `FDA_PLUGIN_ROOT` env injection
- Fixed SKILL.md frontmatter to comply with official plugin spec

### Added
- `hooks/hooks.json` with SessionStart hook for `CLAUDE_ENV_FILE` integration
- `hooks/export-plugin-root.sh` for deriving plugin root from script location
- `.gitignore` to exclude `__pycache__/`
- `LICENSE` (MIT)
- `CHANGELOG.md`
- `references/path-resolution.md` with standard resolution patterns

## [1.0.0] - 2026-02-04

### Added
- Initial release with 9 commands: extract, validate, analyze, configure, status, safety, research, compare-se, summarize
- 1 agent: extraction-analyzer
- 1 skill: fda-510k-knowledge with reference docs
- Bundled scripts: `predicate_extractor.py`, `batchfetch.py`, `setup_api_key.py`
- openFDA API integration with configurable API key
- K/P/DEN/N device number regex support
