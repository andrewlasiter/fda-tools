# FDA Tools Plugin - Quick Start Guide

Get started with the FDA Tools Plugin in 5 minutes.

## Prerequisites

- Python 3.9+
- Internet connection for FDA API access
- ~100MB disk space for plugin
- ~500MB-5GB for FDA data (varies by usage)

## Installation

### 1. Install Plugin

From your terminal:

```bash
claude plugin marketplace add andrewlasiter/fda-tools
claude plugin install fda-tools@fda-tools
```

Or from inside a Claude Code or Claude Desktop session:

```
/plugin marketplace add andrewlasiter/fda-tools
/plugin install fda-tools@fda-tools
```

Start a new session after installing to load the plugin.

### 2. Verify Installation

The plugin is installed at:
```
~/.claude/plugins/marketplaces/fda-tools/
```

Verify it works:

```
/fda:validate --k-number K240001
```

Expected output: "K240001 is valid"

### 3. Configure Data Directory

Set your FDA data directory (default: `~/fda-510k-data/`):

```
/fda-tools:configure
```

This creates the directory structure:
```
~/fda-510k-data/
├── cache/           # API cache
├── downloads/       # PDF downloads
├── structured/      # Parsed data
└── projects/        # Your projects
```

## Essential Commands

### Research a 510(k) Submission

Find suitable predicates for your device:

```
/fda:research --product-code DQY --device "coronary catheter"
```

This searches FDA databases, analyzes predicate chains, and recommends suitable predicates.

### Download 510(k) Data

Extract clearance data for analysis:

```
/fda:extract --product-codes DQY --years 2024
```

With full enrichment (MAUDE, recalls, clinical data):

```
/fda-tools:batchfetch --product-codes DQY --years 2024 --enrich --full-auto
```

### Generate eSTAR XML

Export your project data to eSTAR format:

```
/fda:export --project MY_PROJECT --format estar
```

Supports multiple template types:
- nIVD (FDA 4062)
- IVD (FDA 4078)
- PreSTAR (FDA 5064)

### Pre-Submission Validation

Check your submission before filing:

```
/fda:pre-check --project MY_PROJECT
```

This runs 50+ validation checks against RTA checklists and identifies likely deficiencies.

### PMA Intelligence

Search PMA approvals:

```
/fda:pma-search --product-code DQY
```

Generate intelligence report:

```
/fda:pma-intelligence --product-code DQY
```

Predict review timeline:

```
/fda:pma-timeline --product-code DQY
```

## Common Workflows

### Complete 510(k) Workflow

1. **Research predicates**:
   ```
   /fda:research --product-code DQY
   ```

2. **Extract detailed data**:
   ```
   /fda:extract --product-codes DQY --years 2023-2024
   ```

3. **Review and select predicates**:
   ```
   /fda:review --project DQY_PROJECT
   ```

4. **Draft submission sections**:
   ```
   /fda:draft --section device-description
   /fda:draft --section substantial-equivalence
   /fda:draft --section testing-bench
   ```

5. **Validate submission**:
   ```
   /fda:pre-check --project DQY_PROJECT
   ```

6. **Export for filing**:
   ```
   /fda:export --project DQY_PROJECT --format estar
   ```

### Quick Predicate Research

Find the best predicates in one command:

```
/fda:research --product-code DQY --device "coronary catheter" --years 2022-2024 --min-score 70
```

### Safety & Recall Analysis

Check adverse events for a product code:

```
/fda:safety --product-code DQY --comparison peer
```

Check recall history:

```
/fda-tools:batchfetch --product-codes DQY --years 2020-2024 --enrich
```

The enrichment includes:
- MAUDE adverse events with peer comparison
- Recall history and health status
- Clinical data detection
- Standards intelligence

### Standards Lookup

Find applicable consensus standards:

```
/fda:standards --product-code DQY
```

Search by standard number:

```
/fda:standards --number "ISO 10993"
```

## Agent-Powered Workflows

FDA Tools includes 7 autonomous agents for complex tasks:

### 1. Research Intelligence Agent

Comprehensive predicate research and analysis:

```
/fda-research-intelligence
```

Handles:
- Multi-database search
- Predicate chain validation
- Competitive intelligence
- Strategic recommendations

### 2. Submission Writer Agent

Complete submission drafting:

```
/fda-submission-writer
```

Features:
- 18 eSTAR section templates
- Auto-trigger detection (software, reprocessing, sterile)
- Brand validation
- Consistency checking

### 3. Review Simulator Agent

Simulate FDA review before filing:

```
/fda-review-simulator
```

Identifies:
- RTA deficiencies
- Consistency issues
- Missing documentation
- Likely questions

### 4. Pre-Sub Planner Agent

Generate Pre-Submission packages:

```
/fda-presub-planner
```

Creates:
- Meeting request forms
- Background packages
- Question lists
- Submission strategies

### 5. Extraction Analyzer Agent

Analyze extracted 510(k) data:

```
/fda-extraction-analyzer
```

### 6. PMA Intelligence Agent

Comprehensive PMA analysis:

```
/fda-pma-intelligence
```

### 7. Clinical Requirements Agent

Map clinical data requirements:

```
/fda-clinical-requirements
```

## Expert Skills

FDA Tools includes specialized expert skills for deep regulatory knowledge:

### FDA 510(k) Knowledge Expert

```
/fda-510k-knowledge
```

Deep knowledge of:
- 510(k) regulatory pathways
- RTA checklists
- Submission requirements
- eSTAR structure

### FDA Predicate Assessment Expert

```
/fda-predicate-assessment
```

Expertise in:
- Predicate selection criteria
- Substantial equivalence analysis
- Indications for use comparison
- Technological characteristics

### FDA Clinical Expert

```
/fda-clinical-expert
```

Specializes in:
- Clinical data requirements
- Study design
- Endpoints and outcomes
- Risk-benefit analysis

### FDA Quality Expert

```
/fda-quality-expert
```

Knowledge of:
- Design controls
- Manufacturing processes
- Quality systems
- Validation protocols

### FDA Postmarket Expert

```
/fda-postmarket-expert
```

Expertise in:
- PMA supplements
- Annual reports
- Post-approval studies
- MAUDE reporting

### FDA Regulatory Strategy Expert

```
/fda-regulatory-strategy
```

Strategic guidance on:
- Pathway selection (510(k), PMA, De Novo, IDE)
- Breakthrough designation
- Pre-Sub strategies
- Regulatory timelines

### FDA Software/AI Expert

```
/fda-software-ai-expert
```

Specializes in:
- Software documentation
- Cybersecurity
- AI/ML considerations
- SaMD requirements

## Data Management

### Update FDA Data

Smart update with change detection:

```
/fda-tools:update-data --smart
```

Full refresh:

```
/fda-tools:update-data --force
```

### Monitor Changes

Watch for new clearances:

```
/fda:monitor --product-code DQY --alerts
```

### Cache Management

View cache status:

```
/fda:cache status
```

Clear cache:

```
/fda:cache clear
```

## Advanced Features

### Competitive Intelligence

Market analysis and manufacturer rankings:

```
/fda:dashboard --product-code DQY
```

Includes:
- Market concentration (HHI)
- Top manufacturers
- Technology trends
- Gold standard predicates

### Section Comparison

Compare submission sections across devices:

```
/fda-tools:compare-sections --product-code DQY --section device-description --similarity --trends
```

Cross-product code comparison:

```
/fda-tools:compare-sections --product-codes DQY,OVE --similarity --similarity-method cosine
```

### Literature Search

Find relevant PubMed articles:

```
/fda:literature --product-code DQY --query "biocompatibility"
```

### Clinical Trials Integration

Search ClinicalTrials.gov:

```
/fda:trials --product-code DQY
```

## Troubleshooting

### Command Not Found

If commands don't work:
1. Verify plugin installed: `ls ~/.claude/plugins/marketplaces/fda-tools/`
2. Restart Claude Code
3. Check Claude Code version (requires v1.0.0+)

### Slow Performance

For faster operations:
1. Enable caching: `/fda:configure`
2. Use product code filters
3. Increase available RAM (8GB+ recommended)

### API Rate Limits

If you hit rate limits:
1. Wait 60 seconds and retry
2. Use `--enrich` less frequently
3. Set FDA API key: `export FDA_API_KEY=your_key`

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more solutions.

## Next Steps

- Read [INSTALLATION.md](INSTALLATION.md) for detailed setup
- See [README.md](../README.md) for full command reference
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- Review [CHANGELOG.md](../CHANGELOG.md) for latest features

## Support

- **GitHub Issues**: [Report a bug](https://github.com/andrewlasiter/fda-tools/issues)
- **Documentation**: `/home/linux/.claude/plugins/marketplaces/fda-tools/docs/`
- **Plugin Version**: 5.36.0

## Example: Complete New Device Submission

Here's a complete workflow for a new coronary catheter device:

```bash
# 1. Research predicates
/fda:research --product-code DQY --device "coronary catheter" --years 2022-2024

# 2. Extract detailed data with enrichment
/fda-tools:batchfetch --product-codes DQY --years 2022-2024 --enrich --full-auto

# 3. Analyze safety profile
/fda:safety --product-code DQY --comparison peer

# 4. Look up applicable standards
/fda:standards --product-code DQY

# 5. Start submission project
/fda:start --project CORONARY_CATH_510K --product-code DQY

# 6. Use submission writer agent to draft sections
/fda-submission-writer

# 7. Run pre-check validation
/fda:pre-check --project CORONARY_CATH_510K

# 8. Export to eSTAR format
/fda:export --project CORONARY_CATH_510K --format estar

# 9. Generate Pre-Sub package
/fda-presub-planner
```

This workflow takes you from initial research through ready-to-file submission package.

## Pro Tips

1. **Always enrich data** when doing serious analysis: `--enrich --full-auto`
2. **Use agents** for complex multi-step tasks instead of running commands manually
3. **Enable smart updates** to avoid re-downloading unchanged data: `--smart`
4. **Run pre-check early** to catch issues before drafting all sections
5. **Cross-reference multiple predicates** to find the strongest equivalence arguments
6. **Monitor your product code** for new clearances that might be better predicates
7. **Use expert skills** when you need deep regulatory knowledge on specific topics
8. **Cache aggressively** for faster repeated analysis

## Quick Command Reference

| Task | Command |
|------|---------|
| Research predicates | `/fda:research --product-code CODE` |
| Extract data | `/fda:extract --product-codes CODE --years YYYY` |
| Validate K-number | `/fda:validate --k-number KXXXXXX` |
| Safety analysis | `/fda:safety --product-code CODE` |
| Standards lookup | `/fda:standards --product-code CODE` |
| Pre-check submission | `/fda:pre-check --project NAME` |
| Export eSTAR | `/fda:export --project NAME --format estar` |
| PMA search | `/fda:pma-search --product-code CODE` |
| Monitor changes | `/fda:monitor --product-code CODE` |
| Update data | `/fda-tools:update-data --smart` |
| Configure | `/fda-tools:configure` |

For the complete list of 64+ commands, see the [main README](../README.md).
