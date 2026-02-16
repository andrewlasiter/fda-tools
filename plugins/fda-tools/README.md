# FDA Predicate Assistant

Your regulatory assistant for FDA 510(k) submissions -- predicate research, substantial equivalence analysis, and submission drafting.

> **CONFIDENTIAL DATA WARNING**
>
> This plugin processes text through Anthropic's Claude LLM. **Do not submit trade secrets, proprietary device designs, unpublished clinical data, or confidential regulatory strategies.** See [Protecting Your Data](#protecting-your-data) below.

## Installation

```
/install andrewlasiter/fda-tools fda-tools
/start
```

For detailed installation instructions, see [INSTALLATION.md](docs/INSTALLATION.md).

## Getting Started

### Quick Start
New to the plugin? Follow these steps:

1. **Run the setup wizard:** `/fda-tools:start`
2. **Configure your data directory:** `/fda-tools:configure`
3. **Try a simple workflow:** See [QUICK_START.md](docs/QUICK_START.md)

### Common Workflows

**Keep your FDA data fresh (NEW in v5.26.0):**
```bash
/fda-tools:update-data --scan-all      # Check for stale data
/fda-tools:update-data --update-all    # Update all projects
```

**Analyze competitive landscape (NEW in v5.26.0):**
```bash
/fda-tools:compare-sections --product-code DQY --sections clinical,biocompatibility
# Output: Coverage matrix, standards frequency, outliers
```

**Research predicates for your device:**
```bash
/fda-tools:research --product-code DQY --years 2024 --project my_device
/fda-tools:review
```

**Generate submission outline:**
```bash
/fda-tools:submission-outline
/fda-tools:compare-se
```

**Run full pipeline:**
```bash
/fda-tools:pipeline --product-code DQY --years 2024
```

**Generate Pre-Submission package with FDA eSTAR XML (supports 510k, PMA, IDE, De Novo):**
```bash
# 510(k) Pre-Sub (default)
/fda-tools:presub DQY --project my_device \
  --device-description "Catheter for vascular access" \
  --intended-use "To provide vascular access for medication delivery"

# PMA Pre-Sub (auto-detected for Class III, or specify explicitly)
/fda-tools:presub QAS --pathway pma --project my_pma_device \
  --device-description "Class III cardiac implant"

# IDE Pre-Sub (auto-detected when clinical study keywords present)
/fda-tools:presub OVE --pathway ide --project my_ide_study \
  --device-description "Novel cervical fusion device for clinical investigation"

# De Novo Pre-Sub (auto-detected for novel devices without predicate)
/fda-tools:presub NEW --pathway de_novo --project my_novel_device \
  --device-description "Novel digital therapeutic with no legally marketed predicate"
```
Generates:
- `presub_plan.md` - Human-readable Pre-Sub plan (pathway-specific, 5-10 questions)
- `presub_metadata.json` - Structured meeting data (v2.0 schema with pathway info)
- `presub_prestar.xml` - FDA Form 5064 XML (import into Adobe Acrobat)

For more workflows, see [QUICK_START.md](docs/QUICK_START.md).

**Search and analyze PMA approvals (NEW in v5.29.0, enhanced in v5.30.0):**
```bash
# Look up a specific PMA
/fda-tools:pma-search --pma P170019

# Search by product code and year
/fda-tools:pma-search --product-code NMH --year 2024

# Full pipeline: search, download SSED, extract sections
/fda-tools:pma-search --product-code NMH --download-ssed --extract-sections

# Search with comparison (NEW in v5.30.0)
/fda-tools:pma-search --product-code NMH --year 2024 --compare

# Search with intelligence report (NEW in v5.30.0)
/fda-tools:pma-search --pma P170019 --intelligence

# Find related PMAs (NEW in v5.30.0)
/fda-tools:pma-search --pma P170019 --related

# Search by company
/fda-tools:pma-search --applicant "Edwards Lifesciences" --year 2023

# View cached PMA data
/fda-tools:pma-search --show-manifest
```

**Compare PMAs (NEW in v5.30.0):**
```bash
# Compare two PMAs across all dimensions
/fda-tools:pma-compare --primary P170019 --comparators P160035

# Multiple comparators with clinical focus
/fda-tools:pma-compare --primary P170019 --comparators P160035,P200024 --focus clinical_data

# Competitive analysis for a product code
/fda-tools:pma-compare --product-code NMH --competitive
```

**Generate PMA intelligence reports (NEW in v5.30.0):**
```bash
# Full intelligence report (clinical + supplements + predicates)
/fda-tools:pma-intelligence --pma P170019

# Clinical data extraction only
/fda-tools:pma-intelligence --pma P170019 --focus clinical

# Assess PMA as predicate for a product code
/fda-tools:pma-intelligence --pma P170019 --assess-predicate NMH
```

**PMA Post-Approval Monitoring (NEW in v5.33.0):**
```bash
# Supplement lifecycle tracking with regulatory type classification
/fda-tools:pma-supplements --pma P170019
/fda-tools:pma-supplements --pma P170019 --impact
/fda-tools:pma-supplements --pma P170019 --risk-flags

# Annual report compliance calendar per 21 CFR 814.84
/fda-tools:annual-reports --pma P170019
/fda-tools:annual-reports --batch P170019,P200024,P160035
/fda-tools:annual-reports --pma P170019 --compliance-status

# Post-approval study monitoring per 21 CFR 814.82
/fda-tools:pas-monitor --pma P170019
/fda-tools:pas-monitor --pma P170019 --compliance
/fda-tools:pas-monitor --pma P170019 --milestones
```

**PMA Advanced Analytics (NEW in v5.32.0):**
```bash
# Map clinical trial requirements from PMA precedent
/fda-tools:clinical-requirements --pma P170019
/fda-tools:clinical-requirements --pma P170019 --compare P160035,P150009
/fda-tools:clinical-requirements --product-code NMH

# Predict PMA approval timeline
/fda-tools:pma-timeline --pma P170019
/fda-tools:pma-timeline --product-code NMH --submission-date 2026-06-01
/fda-tools:pma-timeline --product-code NMH --historical

# FMEA-style risk assessment
/fda-tools:pma-risk --pma P170019
/fda-tools:pma-risk --pma P170019 --compare P160035,P150009
/fda-tools:pma-risk --product-code NMH

# Enhanced pathway recommendation with clinical evidence requirements
/fda-tools:pathway NMH --detailed --device-description "Class III cardiac device"
```

**Mixed 510(k)/PMA predicate analysis (NEW in v5.31.0):**
```bash
# Analyze any device number (K or P)
python3 scripts/unified_predicate.py --device P170019
python3 scripts/unified_predicate.py --device K241335

# Compare devices across pathways (510(k) vs PMA)
python3 scripts/unified_predicate.py --compare K241335 P170019

# Assess a PMA as predicate for your 510(k)
python3 scripts/unified_predicate.py --assess P170019 --product-code NMH

# SE comparison table with PMA predicate
/fda-tools:compare-se --predicates K241335,P170019 --product-code NIQ

# Pre-Sub with PMA predicate reference
/fda-tools:presub NIQ --project my_device --predicates K241335,P170019

# Research with PMA competitive intelligence
/fda-tools:research --product-code NMH --include-pma
```

## Feature Spotlight

### NEW in v5.33.0: PMA Post-Approval Monitoring (TICKET-003 Phase 3)

Complete post-approval lifecycle management for PMA devices covering supplement tracking, annual report compliance, and post-approval study monitoring.

**Supplement Lifecycle Tracker (`/fda-tools:pma-supplements`):**
```bash
# Full supplement lifecycle report with regulatory type classification
/fda-tools:pma-supplements --pma P170019

# Change impact analysis
/fda-tools:pma-supplements --pma P170019 --impact

# Risk flags (high-frequency changes, denied supplements, etc.)
/fda-tools:pma-supplements --pma P170019 --risk-flags
```

**Supplement Analysis Output:**
- 7 regulatory types per 21 CFR 814.39 (180-day, real-time, 30-day notice, panel-track, PAS-related, manufacturing, other)
- Change impact scoring with burden analysis
- Frequency analysis with trend detection (accelerating/stable/decelerating)
- 7 risk flags for compliance monitoring
- Supplement dependency detection and lifecycle phase tracking

**Annual Report Compliance Calendar (`/fda-tools:annual-reports`):**
```bash
# Full compliance calendar
/fda-tools:annual-reports --pma P170019

# Batch calendar for multiple PMAs
/fda-tools:annual-reports --batch P170019,P200024,P160035

# Project 5 years forward
/fda-tools:annual-reports --pma P170019 --years-forward 5
```

**Annual Report Features:**
- Due date calculation from approval anniversary + 60-day grace period (21 CFR 814.84)
- 8 required report sections mapped to CFR subsections
- Device characteristic detection (sterile, implantable, software)
- Compliance risk identification and historical assessment
- Batch calendar generation for portfolio management

**Post-Approval Study Monitor (`/fda-tools:pas-monitor`):**
```bash
# Full PAS report
/fda-tools:pas-monitor --pma P170019

# Compliance assessment with alerts
/fda-tools:pas-monitor --pma P170019 --compliance

# Milestone timeline
/fda-tools:pas-monitor --pma P170019 --milestones
```

**PAS Monitoring Features:**
- 4 PAS types: continued approval, pediatric, Section 522, voluntary
- PAS requirement detection from approval order, supplement history, and SSED
- 10 milestone timeline with status tracking
- Compliance assessment (COMPLIANT/ON_TRACK/AT_RISK/NON_COMPLIANT)
- Alert generation for overdue milestones

### NEW in v5.32.0: PMA Advanced Analytics (TICKET-003 Phase 2)

Complete PMA analytics toolkit for clinical planning, risk assessment, and regulatory strategy.

**Clinical Trial Requirements Mapping (`/fda-tools:clinical-requirements`):**
```bash
# Extract requirements from a single PMA
/fda-tools:clinical-requirements --pma P170019

# Compare requirements across PMAs
/fda-tools:clinical-requirements --pma P170019 --compare P160035,P150009

# Analyze all PMAs for a product code
/fda-tools:clinical-requirements --product-code NMH
```

**Extracted Data:**
- Study design (11 types: RCT, single-arm, non-inferiority, bayesian adaptive, etc.)
- Enrollment targets and clinical sites
- Primary, secondary, and safety endpoints (7 categories)
- Follow-up duration requirements
- Cost estimates (per-patient by trial type)
- Timeline estimates (startup, enrollment, follow-up, analysis)
- Data requirements (DSMB, core lab, CEC, interim analysis)
- Statistical requirements (analysis populations, methods, power, alpha)

**PMA Approval Timeline Prediction (`/fda-tools:pma-timeline`):**
```bash
# Device-specific prediction
/fda-tools:pma-timeline --pma P170019 --submission-date 2026-06-01

# Product code historical analysis
/fda-tools:pma-timeline --product-code NMH --historical

# Applicant track record
/fda-tools:pma-timeline --pma P170019 --applicant "Edwards Lifesciences"
```

**Timeline Features:**
- Three scenarios (optimistic/realistic/pessimistic)
- Key milestone dates (RTA, MDUFA clock, panel meeting, decision)
- 8 risk factor types with calibrated impact and probability
- Advisory committee panel analysis
- Applicant track record assessment

**Risk Assessment Framework (`/fda-tools:pma-risk`):**
```bash
# Single PMA FMEA-style assessment
/fda-tools:pma-risk --pma P170019

# Compare risk profiles
/fda-tools:pma-risk --pma P170019 --compare P160035,P150009

# Product code risk landscape
/fda-tools:pma-risk --product-code NMH
```

**Risk Analysis Output:**
- 21 risk factors across 4 categories (device, clinical, regulatory, manufacturing)
- Risk Priority Number (RPN = Severity x Probability x Detectability)
- 5x5 risk matrix (probability vs severity)
- Mitigation strategies extracted from SSED safety sections
- Evidence requirements mapped to high/medium priority risks
- Residual risk assessment (HIGH/MODERATE/LOW/ACCEPTABLE)

**Enhanced Pathway Recommendation (`/fda-tools:pathway`):**
```bash
# Detailed pathway analysis with clinical evidence requirements
/fda-tools:pathway NMH --detailed --device-description "Class III cardiac device"
```

### NEW in v5.31.0: Unified Predicate Interface (TICKET-003 Phase 1.5)

Seamlessly mix 510(k) K-numbers and PMA P-numbers in all predicate workflows. The unified predicate interface auto-detects device number format and retrieves normalized data from the appropriate source.

**Key capabilities:**
- Auto-detect K/P/DEN device number formats
- Cross-pathway comparison (510(k) vs PMA, PMA vs PMA, mixed)
- PMA data mapped to SE table rows via SSED section extraction
- PMA predicates in Pre-Sub packages with supplement and clinical data status
- Enhanced PMA intelligence in research reports

### v5.30.0: PMA Comparison & Clinical Intelligence (TICKET-003 Phase 1)

Compare PMAs and extract clinical intelligence from SSED documents.

**PMA Comparison Engine (`/fda-tools:pma-compare`):**
```bash
# Compare two PMAs across 5 dimensions
/fda-tools:pma-compare --primary P170019 --comparators P160035

# Focus on clinical data comparison only
/fda-tools:pma-compare --primary P170019 --comparators P160035 --focus clinical_data

# Competitive landscape for a product code
/fda-tools:pma-compare --product-code NMH --competitive
```

**Comparison Dimensions (weighted):**
| Dimension | Weight | Method |
|-----------|--------|--------|
| Indications for Use | 30% | Cosine + Jaccard + key terms |
| Clinical Data | 25% | Study design + endpoints + enrollment |
| Device Specifications | 20% | Description similarity + product code |
| Safety Profile | 15% | AE text + safety key terms |
| Regulatory History | 10% | Product code + committee + date proximity |

**Clinical Intelligence (`/fda-tools:pma-intelligence`):**
```bash
# Full intelligence report
/fda-tools:pma-intelligence --pma P170019

# Clinical data focus
/fda-tools:pma-intelligence --pma P170019 --focus clinical

# Supplement tracking
/fda-tools:pma-intelligence --pma P170019 --focus supplements

# Find related 510(k) clearances
/fda-tools:pma-intelligence --pma P170019 --find-citing-510ks

# Assess PMA as predicate reference
/fda-tools:pma-intelligence --pma P170019 --assess-predicate NMH
```

**Clinical Data Extracted:**
- 14 study design types (RCT, single-arm, registry, bayesian, sham-controlled, etc.)
- Enrollment data (sample size, sites, demographics)
- Primary, secondary, and safety endpoints
- Efficacy results (success rates, p-values, sensitivity/specificity, PPA/NPA)
- Adverse event rates and specific event types
- Follow-up duration
- All with per-extraction confidence scoring

**Supplement Intelligence:**
- 6-category classification (labeling, design change, indication expansion, PAS, manufacturing, panel track)
- Chronological timeline and frequency analysis
- Labeling change tracking and post-approval study identification

### v5.29.0: PMA Intelligence Module (TICKET-003 Phase 0)

Search, download, and analyze PMA approval data with SSED document intelligence.

**Capabilities:**
- Search PMAs by number, product code, device name, applicant, or year
- Download SSED PDFs with rate limiting and resume capability
- Extract 15 structured sections from SSED documents
- Cache all data with TTL-based freshness management
- Generate intelligence reports from multi-PMA analysis

**15 SSED Sections Extracted:**
General Information, Indications for Use, Device Description, Alternative Practices, Marketing History, Potential Risks, Preclinical Studies, Clinical Studies, Statistical Analysis, Benefit-Risk Analysis, Overall Conclusions, Panel Recommendation, Nonclinical Testing, Manufacturing, Labeling

### NEW in v5.28.0: Multi-Pathway Pre-Submission Support (TICKET-004)

Pre-Sub packages now support all four major FDA regulatory pathways with pathway-specific
templates, questions, and auto-detection.

**Supported Pathways:**
| Pathway | Template | Auto-Detection |
|---------|----------|----------------|
| 510(k) | 6 meeting-type templates | Class I/II with predicates |
| PMA | pma_presub.md | Class III devices |
| IDE | ide_presub.md | Clinical study keywords |
| De Novo | de_novo_presub.md | Novel device / no predicate |

**Question Bank v2.0:** 55+ questions across 26 categories with pathway-specific filtering.

### NEW in v5.26.0: Automated Data Management & Regulatory Intelligence

Two major productivity features for FDA data management and competitive intelligence.

#### Feature 1: Auto-Update Data Manager

**Purpose:** Keep your FDA data fresh across all projects with automated batch updates.

**The Problem:** FDA data becomes stale over time:
- Safety data (MAUDE events, recalls): 24-hour TTL
- Classification data: 7-day TTL
- Multiple projects with outdated data
- Manual refresh is tedious and error-prone

**The Solution:** Automated staleness detection and batch updates with user control.

**Quick Start:**
```bash
# Scan all projects for stale data
/fda-tools:update-data --scan-all

# Preview updates without executing (dry-run)
/fda-tools:update-data --project my_device --dry-run

# Update a single project
/fda-tools:update-data --project my_device

# Update ALL projects with stale data
/fda-tools:update-data --update-all

# Clean expired API cache
/fda-tools:update-data --clean-cache
```

**Key Features:**
- **Smart TTL-Based Detection**: Automatically identifies stale data (7-day for stable, 24-hour for safety)
- **Batch Processing**: Update 100+ queries in <2 minutes with rate limiting (2 req/sec)
- **Multi-Project Support**: Update all projects in one command
- **Dry-Run Mode**: Preview updates without executing
- **Error Recovery**: Partial success support (continues if some queries fail)
- **Progress Tracking**: Real-time progress display with success/failure counts

**Example Output:**
```
🔍 Found 3 projects with stale data
📊 Total stale queries: 5

[1/3] Project: catheter_device (2 stale)
🔄 Updating 2 stale queries for catheter_device...
  [1/2] Updating classification:DQY... ✅ SUCCESS
  [2/2] Updating recalls:DQY... ✅ SUCCESS

[2/3] Project: wound_dressing (1 stale)
🔄 Updating 1 stale queries for wound_dressing...
  [1/1] Updating events:FRO... ✅ SUCCESS

============================================================
🎯 Overall Summary:
  Projects updated: 3/3
  Queries updated: 5
  Queries failed: 0
```

**TTL Tiers (automatically applied):**
- **7 days**: classification, clearances
- **24 hours**: recalls, MAUDE events, enforcement actions

**Time Savings:** 80-90% reduction in manual data freshness management (5-10 min → <1 min per project)

---

#### Feature 2: Section Comparison Tool

**Purpose:** Compare sections across 100+ 510(k) summaries for competitive intelligence and gap analysis.

**The Problem:** Manual section comparison is time-consuming:
- 8-10 hours to read and tabulate sections for one product code
- No systematic approach to identify common testing patterns
- Difficult to spot regulatory outliers
- Missing regulatory intelligence for strategic decisions

**The Solution:** Automated section extraction, comparison, and outlier detection with FDA standards analysis.

**Quick Start:**
```bash
# Compare clinical and biocompatibility sections for DQY devices
/fda-tools:compare-sections --product-code DQY --sections clinical,biocompatibility

# Compare all sections with year filtering
/fda-tools:compare-sections --product-code OVE --sections all --years 2020-2025

# Limit to 30 most recent devices
/fda-tools:compare-sections --product-code DQY --sections performance --limit 30
```

**Key Features:**
- **Product Code Filtering**: Analyze all devices for a specific product code (with openFDA metadata enrichment)
- **Section Coverage Matrix**: Shows which devices have which sections (percentage coverage)
- **FDA Standards Frequency**: Identifies common standards citations (ISO/IEC/ASTM)
- **Statistical Outlier Detection**: Flags devices with unusual approaches (Z-score >2)
- **Professional Reports**: Markdown format suitable for regulatory review
- **Flexible Sections**: clinical, biocompatibility, performance, predicate, software, human_factors, and 30+ more

**Example Output:**
```
📂 Loading structured cache...
🔍 Filtering by product code: DQY
⚠️  Limiting to 30 devices (from 147 available)
✅ Processing 30 devices...
📊 Generating coverage matrix...
🔬 Analyzing standards frequency...
🎯 Detecting outliers...

============================================================
✅ Analysis Complete!
============================================================
Devices analyzed: 29
Sections analyzed: 2
Standards identified: 3
Outliers detected: 2

Report: ~/fda-510k-data/projects/section_comparison_DQY_*/DQY_comparison.md
```

**Sample Report (DQY_comparison.md):**
```markdown
# Section Coverage Matrix

| Section Type | Devices | Coverage % |
|-------------|---------|------------|
| biocompatibility | 29/29 | 100.0% |
| clinical_testing | 12/29 | 41.4% |

# FDA Standards Frequency

| Standard | Citations | Percentage |
|----------|-----------|------------|
| ISO 10993-1 | 27/29 | 93.1% |
| ISO 10993-5 | 24/29 | 82.8% |
| ISO 10993-10 | 18/29 | 62.1% |

# Key Findings

- **clinical_testing**: Only 41.4% coverage - consider clinical data requirements
- **ISO 10993-1**: Cited by 93.1% of devices - essential for biocompatibility
- **Outliers**: K234567 has unusually long biocompatibility section (Z-score 3.2)
```

**Section Types Supported (40+ sections):**
- Core: `clinical`, `biocompatibility`, `performance`, `predicate`, `device_description`, `indications`
- Testing: `sterilization`, `shelf_life`, `electrical`, `mechanical`, `environmental`
- Special: `software`, `human_factors`, `risk`, `labeling`, `reprocessing`

**Performance:**
- 200+ devices analyzed in <2 minutes
- Automatic metadata enrichment via openFDA API (100% coverage)
- Graceful degradation if API unavailable

**Time Savings:** ~95% reduction in manual section comparison (8-10 hours → 2 minutes for 200+ devices)

**Use Cases:**
1. **Competitive Intelligence**: Identify common testing approaches in your product code
2. **Gap Analysis**: Find which sections competitors include that you're missing
3. **Standards Strategy**: Discover which standards are cited by 90%+ of devices
4. **Outlier Detection**: Flag unusual regulatory approaches that may carry risk
5. **Pre-Submission Planning**: Understand regulatory landscape before investing in testing

---

### v5.25.0: PreSTAR XML Generation for Pre-Submission Meetings

Complete FDA Pre-Submission workflow with eSTAR-ready XML export for FDA Form 5064.

**Key Features:**
- **6 Meeting Types**: Formal, Written, Info, Pre-IDE, Administrative, Info-Only
- **35-Question Bank**: Centralized questions across 10 regulatory categories
- **Auto-Detection**: Intelligent meeting type selection based on device characteristics
- **Auto-Triggers**: Automatically selects relevant questions (e.g., sterile device → sterilization questions)
- **Template System**: 80+ placeholders auto-populated from project data
- **FDA eSTAR Ready**: Direct XML import into FDA Form 5064 (Adobe Acrobat)

**Workflow:**
1. **Generate Pre-Sub Package**:
   ```bash
   /fda-tools:presub DQY --project catheter_device \
     --device-description "Single-use vascular access catheter" \
     --intended-use "To provide temporary vascular access"
   ```

2. **Output Files Generated**:
   - `presub_plan.md` - Complete Pre-Sub document (formatted, ready for review)
   - `presub_metadata.json` - Structured meeting data
   - `presub_prestar.xml` - FDA eSTAR XML (FDA Form 5064)

3. **Import into FDA Form**:
   - Open FDA Form 5064 (PreSTAR template) in Adobe Acrobat
   - Form > Import Data > Select `presub_prestar.xml`
   - Fields auto-populate: Admin info, device description, IFU, questions, meeting characteristics
   - Add attachments and submit to FDA

**Meeting Type Examples:**
- **Formal** (5-7 questions): Complex devices, novel technology, multiple regulatory questions
- **Written** (1-3 questions): Straightforward devices, well-scoped technical questions
- **Pre-IDE**: Clinical study planning, IDE protocol discussion
- **Administrative**: Pathway determination (510(k) vs De Novo vs PMA), classification questions

**Question Categories:**
- Predicate selection, Classification, Testing (biocompatibility, sterilization, shelf life, performance, electrical, software, cybersecurity, human factors), Clinical evidence, Novel technology, Labeling, Manufacturing, Regulatory pathway

**Auto-Triggers** (automatically add questions based on device description):
- Patient-contacting device → Biocompatibility questions
- Sterile device → Sterilization + Shelf life questions
- Powered device → Electrical safety questions
- Software device → Software V&V questions
- Implantable device → Long-term biocompatibility questions
- Reusable device → Reprocessing validation questions
- Novel technology → Novel feature discussion questions

**Time Savings**: 2-4 hours per Pre-Sub (automated question selection + template population + XML export)

## Documentation

- **[Quick Start Guide](docs/QUICK_START.md)** - Get started in minutes
- **[Installation Guide](docs/INSTALLATION.md)** - Detailed setup instructions
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Migration Notice](MIGRATION_NOTICE.md)** - Upgrading from fda-predicate-assistant
- **[Changelog](CHANGELOG.md)** - Version history and release notes

## What's included

### Commands

#### Getting started
- `/start` -- Interactive onboarding wizard
- `/status` -- Check available data, scripts, and record counts
- `/configure` -- Set up API keys, data directories, and preferences

#### NEW: Knowledge-Based Standards Generation (v5.26.0) - RESEARCH USE ONLY
- `/fda-tools:generate-standards` -- Identify potentially applicable FDA Recognized Consensus Standards using knowledge-based analysis

  **⚠️ DISCLAIMER:** This tool is for research and regulatory planning only. Output must be independently verified by qualified regulatory affairs professionals before use in FDA submissions. Accuracy has not been independently validated.

  **Key Features:**
  - **Knowledge-Based Analysis**: Autonomous agent uses rule-based logic to identify potentially applicable standards
  - **Flexible Scope**: Process specific codes, top N by clearance volume, or all ~7000 FDA product codes
  - **Resilient Processing**: Automatic checkpoint/resume, exponential backoff retry, progress tracking with ETA
  - **Multi-Agent Validation**: Internal quality framework for consistency checking
  - **Multiple Output Formats**: Individual JSON files + consolidated HTML reports + validation summaries
  - **No API Keys Required**: Uses your Claude Code access (agent-based, no external API dependencies)

  **Important Limitations:**
  - Database contains 54 standards (3.5% of ~1,900 FDA-recognized standards)
  - Uses keyword matching and rules, not machine learning
  - Does not analyze actual cleared predicate standards
  - Requires verification against cleared 510(k) summaries

  **Usage Examples:**
  ```bash
  # Generate standards for specific product codes
  /fda-tools:generate-standards DQY OVE GEI

  # Process top 100 devices by clearance volume
  /fda-tools:generate-standards --top 100

  # Process ALL FDA product codes (7000+ codes, 4-6 hours)
  /fda-tools:generate-standards --all

  # Force restart (clear existing checkpoint)
  /fda-tools:generate-standards --all --force-restart

  # Resume from checkpoint after interruption
  /fda-tools:generate-standards --all  # Auto-resumes if checkpoint exists
  ```

  **Output Files:**
  - `data/standards/{category}/{code}.json` - Individual standard determinations with reasoning
  - `data/validation_report.html` - Visual dashboard with coverage + quality metrics
  - `data/standards_coverage_report.md` - Detailed coverage analysis
  - `data/standards_quality_report.md` - Quality assessment with recommendations

  **Progress Tracking:**
  - Real-time progress display (X/Y codes, Z% complete)
  - Live ETA calculation based on current processing rate
  - Automatic checkpointing every 10 codes
  - Category breakdown summary every 50 codes
  - Graceful handling of API failures with retry logic

#### Research and analysis
- `/research` -- Comprehensive submission research for a product code
- `/analyze` -- Statistics and pattern analysis across extraction results
- `/ask` -- Natural language Q&A about FDA regulatory topics
- `/validate` -- Look up any device number against FDA databases
- `/pathway` -- Recommend the best regulatory pathway (510(k), De Novo, PMA)
- `/literature` -- Search PubMed for clinical evidence and identify gaps
- `/safety` -- Pull adverse events and recall history
- `/inspections` -- FDA inspection history, CFR citations, and compliance actions
- `/trials` -- Search ClinicalTrials.gov for similar device studies
- `/warnings` -- FDA warning letters and enforcement actions
- `/udi` -- Look up UDI/GUDID records and device history
- `/standards` -- FDA Recognized Consensus Standards lookup
- `/guidance` -- Find relevant FDA guidance documents
- `/lineage` -- Trace predicate citation chains across clearance generations

#### Predicate workflow
- `/extract` -- Download 510(k) PDFs and extract predicate relationships
- `/data-pipeline` -- 4-step data maintenance: gap analysis, download, extract, merge
- `/review` -- Score and triage extracted predicates with justification narratives
- `/propose` -- Manually propose predicates with validation and confidence scoring
- `/compare-se` -- Generate substantial equivalence comparison tables
- `/compare-sections` -- **NEW in v5.26.0**: Batch section comparison for regulatory intelligence - product code filtering, coverage matrix, FDA standards frequency analysis, statistical outlier detection (Z-score), professional markdown reports

#### PMA Intelligence (NEW in v5.29.0-v5.32.0)
- `/pma-search` -- **v5.29.0**: Search and analyze PMA approvals - single PMA lookup, product code/device/applicant search, SSED download, 15-section extraction, with comparison and intelligence triggers (v5.30.0)
- `/pma-compare` -- **v5.30.0**: Compare PMAs across 5 weighted dimensions (indications, clinical data, device specs, safety, regulatory history) with similarity scoring and competitive analysis
- `/pma-intelligence` -- **v5.30.0**: Generate PMA intelligence reports - clinical data extraction (14 study types, enrollment, endpoints, efficacy), supplement tracking (6 categories), predicate suitability assessment
- `/clinical-requirements` -- **NEW in v5.32.0**: Map clinical trial requirements from PMA precedent -- study design, enrollment, endpoints, follow-up, cost and timeline estimates
- `/pma-timeline` -- **NEW in v5.32.0**: Predict PMA approval timeline with milestones, risk factors, and confidence intervals from historical FDA data
- `/pma-risk` -- **NEW in v5.32.0**: Systematic FMEA-style risk assessment for PMA devices with Risk Priority Numbers, risk matrices, and evidence requirement mapping

#### Submission preparation
- `/draft` -- Write regulatory prose for 18 submission sections with citations
- `/submission-outline` -- Generate a 510(k) submission outline with section checklists
- `/traceability` -- Generate a requirements traceability matrix
- `/summarize` -- Summarize and compare sections from 510(k) summary PDFs
- `/pccp` -- Generate a Predetermined Change Control Plan for AI/ML devices
- `/test-plan` -- Generate a risk-based testing plan with gap analysis
- `/pre-check` -- Simulate FDA review team evaluation and RTA screening
- `/consistency` -- Validate device descriptions and predicates match across files
- `/assemble` -- Assemble an eSTAR-structured submission package
- `/export` -- Export project data as eSTAR-compatible XML or zip
- `/presub` -- Create Pre-Submission meeting package with PreSTAR XML export (v5.25.0: 6 meeting types, 35-question bank, auto-detection)

#### Project management
- `/dashboard` -- Project status with Submission Readiness Index (SRI)
- `/audit` -- View the decision audit trail
- `/cache` -- Show cached FDA data for a project
- `/update-data` -- **NEW in v5.26.0**: Automated data freshness management - scan all projects, identify stale data (TTL-based), batch update with progress tracking, dry-run preview, error recovery with partial success
- `/gap-analysis` -- Analyze gaps in 510(k) data pipeline
- `/portfolio` -- Cross-project portfolio dashboard
- `/pipeline` -- Run all stages autonomously end-to-end
- `/import` -- Import eSTAR data from PDF or XML
- `/monitor` -- Watch FDA databases for new clearances, recalls, and events
- `/calc` -- Regulatory calculators (shelf life, sample size, sterilization dose)

### Skills

- **FDA 510(k) Knowledge** -- Local data pipeline, openFDA integration, 510(k) terminology
- **Predicate Assessment** -- Predicate strategy, substantial equivalence, confidence scoring
- **Safety Signal Triage** -- Recalls, MAUDE adverse events, complaint trends, risk summaries
- **510(k) Submission Outline** -- Section-by-section outlines, RTA readiness checklists, evidence plans
- **E2E Smoke Tests** -- Deterministic live smoke tests for plugin scripts

### Agents

15 autonomous agents for multi-step workflows, including:
- **Standards Generation** (v5.26.0) - RESEARCH USE ONLY:
  - `standards-ai-analyzer` - Uses rule-based logic to identify potentially applicable FDA Recognized Consensus Standards
  - `standards-coverage-auditor` - Internal consistency check for standards coverage within embedded database
  - `standards-quality-reviewer` - Internal review of standards determinations for consistency
  - **Note:** These agents provide internal quality checks only, NOT independent regulatory validation
- **Core Workflows**: Extraction analysis, submission writing, pre-sub planning, FDA review simulation
- **Intelligence**: Research intelligence, data pipeline management, submission assembly
- **Validation**: Multi-agent consensus framework for quality assurance

Agents are invoked automatically by Claude when relevant, or manually via `/fda-tools:generate-standards`.

### Connected data sources

10 connector categories for FDA clearances, adverse events, clinical trials, literature, and more.
See [CONNECTORS.md](CONNECTORS.md) for details and [.mcp.json](.mcp.json) for MCP server configuration.

## Protecting Your Data

All text you provide -- device descriptions, intended use statements, file contents, command arguments -- is sent to Anthropic's Claude LLM for processing.

| Account Type | Trained On? | Recommendation |
|-------------|-------------|----------------|
| **Free / Pro / Max** | Yes, by default | Disable model improvement in [privacy settings](https://claude.ai/settings/data-privacy-controls) before using with sensitive content |
| **Team / Enterprise** | No | Already protected by commercial terms |
| **API / Bedrock / Vertex** | No | Already protected |

**Never submit** trade secrets, unpublished clinical data, proprietary designs, patient-identifiable information, or confidential regulatory strategies through any consumer account.

The plugin does NOT send your files to any server other than Anthropic's API. openFDA queries go directly to api.fda.gov. PDF downloads come directly from accessdata.fda.gov.

## Testing & Compliance Status

### Test Results (v5.32.0)
- **Overall Pass Rate:** 96.6% (28/29 core tests)
- **Phase 1 (Data Integrity):** 22/22 tests passing
- **Phase 2 (Intelligence):** 4/4 devices verified
- **Phase 3 (Intelligence Suite):** 31/31 tests passing
- **Phase 4A (Gap Analysis):** 9/9 tests passing
- **Phase 4B (Smart Predicates):** 10/10 tests passing
- **Phase 5 (Workflows):** 19/19 tests passing
- **PMA Phase 0 (TICKET-003):** 95/95 tests passing
- **PMA Phase 1 (TICKET-003):** 80+ tests (comparison, clinical intelligence, supplement tracking)
- **PMA Phase 1.5 (TICKET-003):** 25+ tests (unified predicate, cross-pathway comparison)
- **PMA Phase 2 (TICKET-003):** 50+ tests (clinical requirements, timeline, risk, pathway recommender, cross-module integration, edge cases)

### New in v5.26.0
- **Knowledge-Based Standards Generation (RESEARCH USE ONLY):** Comprehensive validation pending
  - Agent-based framework implemented (internal quality checks for consistency)
  - Checkpoint/resume functionality verified
  - External standards database (54 standards, 10 categories - 3.5% of FDA-recognized standards)
  - HTML report generation validated
  - **Important:** Accuracy not independently validated; requires verification before regulatory use

### Compliance Status
- **Status:** CONDITIONAL APPROVAL - Research use only
- **CFR Citations:** 100% accurate (3/3 verified)
- **FDA Guidance:** 100% current (3/3 verified)

**Important:** This plugin is approved for research and intelligence gathering ONLY. Not approved for direct FDA submission use without independent verification by qualified RA professionals.

See [Testing Complete Summary](docs/testing/TESTING_COMPLETE_FINAL_SUMMARY.md) for details.

## Important notices

**Research purposes only.** This tool analyzes publicly available FDA data. LLM outputs may contain errors, omissions, or hallucinations. Always independently verify every device number, predicate relationship, regulatory citation, and testing recommendation. Consult qualified regulatory affairs professionals before making submission decisions.

## License

MIT
