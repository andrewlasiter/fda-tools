# Quick Start Guide - FDA Tools Plugin

Get started with the FDA Tools plugin in minutes.

## Prerequisites

- **Claude Code** installed and running
- **Python 3.8+** for optional batch scripts
- **Internet connection** for openFDA API access
- **Optional:** openFDA API key for enrichment features

## First Steps

### 1. Run the Setup Wizard

```bash
/fda-tools:start
```

The interactive wizard will:
- Detect existing FDA data
- Ask about your device type and regulatory stage
- Recommend a personalized command sequence
- Set up your data directory

### 2. Configure Data Directory

```bash
/fda-tools:configure
```

Set or verify your FDA data directory (default: `~/fda-510k-data/`).

### 3. Check System Status

```bash
/fda-tools:status
```

Verify:
- Data pipeline availability
- Script permissions
- Record counts
- File freshness

## Common Workflows

### Workflow 1: Research Predicates for Your Device

**Goal:** Find similar cleared devices to use as predicates

```bash
# Step 1: Search for predicates
/fda-tools:research --product-code DQY --years 2024 --project my_device

# Step 2: Review extracted predicates
/fda-tools:review

# Step 3: Analyze predicate relationships
/fda-tools:lineage --k-number K123456
```

**What happens:**
- Downloads 510(k) summaries for your product code
- Extracts predicate citations and device specifications
- Creates a project directory with organized data
- Generates review.json with confidence scores

### Workflow 2: Generate 510(k) Submission Outline

**Goal:** Create a structured submission plan

```bash
# Step 1: Research and accept predicates
/fda-tools:research --product-code KGN --years 2023-2024
/fda-tools:review  # Accept your best predicates

# Step 2: Generate submission outline
/fda-tools:submission-outline

# Step 3: Generate SE comparison table
/fda-tools:compare-se

# Step 4: Draft specific sections
/fda-tools:draft --section device-description
```

**What happens:**
- Creates 510(k) section checklist
- Identifies testing gaps based on FDA guidance
- Maps IFU claims to testing requirements
- Generates device-type specific comparison tables

### Workflow 3: Full Pipeline (Autonomous)

**Goal:** Run complete research → review → analysis pipeline

```bash
/fda-tools:pipeline --product-code DQY --years 2024
```

**What happens:**
- Extracts predicates
- Reviews and scores each predicate
- Analyzes results
- Looks up FDA guidance
- Plans Pre-Submission strategy
- Generates submission outline
- Creates SE comparison table

### Workflow 4: API Enrichment & Intelligence

**Goal:** Add safety, recall, and clinical data to predicate research

```bash
# Basic enrichment
/fda-tools:batchfetch --product-codes DQY --years 2024 --enrich

# Full intelligence suite
/fda-tools:batchfetch --product-codes DQY --years 2024 --enrich --full-auto
```

**What happens:**
- Downloads 510(k) summaries
- Enriches with MAUDE adverse events
- Adds recall history
- Detects clinical data requirements
- Identifies applicable FDA standards
- Validates predicate chain health
- Generates intelligence report

**Outputs:**
- `output.csv` - Enriched predicate data (53 columns)
- `enrichment_report.html` - Visual dashboard
- `quality_report.md` - Data quality metrics
- `regulatory_context.md` - CFR citations and guidance
- `intelligence_report.md` - Strategic insights

## Quick Examples

### Example 1: Find Predicates for Cardiovascular Catheter
```bash
/fda-tools:research --product-code DQY --years 2024 --project my_catheter
```

### Example 2: Validate a K-Number
```bash
/fda-tools:validate --k-number K240123
```

### Example 3: Check Safety Profile
```bash
/fda-tools:safety --product-code DQY --years 5
```

### Example 4: Look Up FDA Guidance
```bash
/fda-tools:guidance --product-code DQY
```

### Example 5: Generate Risk-Based Test Plan
```bash
/fda-tools:test-plan
```

### Example 6: Search Clinical Trials
```bash
/fda-tools:trials --condition "heart failure" --intervention "catheter"
```

### Example 7: Smart Predicate Recommendations
```bash
/fda-tools:smart-predicates --k-numbers K240001,K230456,K220789
```

### Example 8: Automated Gap Analysis
```bash
/fda-tools:auto-gap-analysis
```

## Command Categories

### Data Collection (6 commands)
- `/fda-tools:extract` - Download & extract predicates
- `/fda-tools:batchfetch` - Batch download with enrichment
- `/fda-tools:data-pipeline` - Maintain data corpus
- `/fda-tools:import` - Import from eSTAR PDF/XML
- `/fda-tools:gap-analysis` - Identify missing data
- `/fda-tools:cache` - View cached data

### Analysis (8 commands)
- `/fda-tools:analyze` - Analyze extraction results
- `/fda-tools:review` - Interactive predicate review
- `/fda-tools:lineage` - Trace predicate chains
- `/fda-tools:propose` - Manual predicate proposal
- `/fda-tools:smart-predicates` - ML-powered recommendations
- `/fda-tools:auto-gap-analysis` - Automated deficiency detection
- `/fda-tools:cluster` - Device similarity clustering
- `/fda-tools:semantic-search` - Semantic device search

### Planning (7 commands)
- `/fda-tools:pathway` - Recommend regulatory pathway
- `/fda-tools:presub` - Plan Pre-Sub meeting
- `/fda-tools:submission-outline` - Generate submission plan
- `/fda-tools:test-plan` - Risk-based testing strategy
- `/fda-tools:traceability` - Requirements traceability matrix
- `/fda-tools:pccp` - AI/ML change control plan
- `/fda-tools:workflow` - Custom workflow orchestration

### Drafting (4 commands)
- `/fda-tools:draft` - Generate section prose
- `/fda-tools:compare-se` - SE comparison tables
- `/fda-tools:assemble` - Build eSTAR package
- `/fda-tools:export` - Export as eSTAR XML

### Intelligence (9 commands)
- `/fda-tools:safety` - MAUDE & recall analysis
- `/fda-tools:guidance` - FDA guidance lookup
- `/fda-tools:standards` - Standards database search
- `/fda-tools:literature` - PubMed clinical evidence
- `/fda-tools:trials` - ClinicalTrials.gov search
- `/fda-tools:warnings` - Warning letters & enforcement
- `/fda-tools:inspections` - Establishment inspection history
- `/fda-tools:udi` - UDI/GUDID lookup
- `/fda-tools:monitor` - Automated database monitoring

### Quality (5 commands)
- `/fda-tools:pre-check` - FDA review simulation
- `/fda-tools:consistency` - Cross-file validation
- `/fda-tools:dashboard` - Project status overview
- `/fda-tools:validate` - K-number verification
- `/fda-tools:audit` - Decision audit trail

### Utilities (4 commands)
- `/fda-tools:start` - Setup wizard
- `/fda-tools:configure` - Settings management
- `/fda-tools:status` - System health check
- `/fda-tools:ask` - Regulatory Q&A

## Next Steps

1. **Read:** [INSTALLATION.md](INSTALLATION.md) for detailed setup
2. **Explore:** [Command Reference](README.md#commands) for all 43 commands
3. **Troubleshoot:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
4. **Learn:** Review example projects in `docs/examples/`

## Getting Help

- **Command help:** `/fda-tools:ask --question "How do I..."`
- **System status:** `/fda-tools:status`
- **Documentation:** See `plugins/fda-tools/docs/`
- **Issues:** https://github.com/andrewlasiter/fda-predicate-assistant/issues

## Important Notes

### Research Use Only
This plugin is approved for **research and intelligence gathering ONLY**. Not approved for direct FDA submission use without independent verification by qualified RA professionals.

### API Rate Limits
- openFDA API: 240 requests/minute (1000/hour with API key)
- Use `--delay` flag for large batches
- Consider using `--full-auto` for unattended enrichment

### Data Freshness
- Check file dates with `/fda-tools:status`
- Re-run `/fda-tools:data-pipeline` quarterly
- Monitor FDA updates with `/fda-tools:monitor`
