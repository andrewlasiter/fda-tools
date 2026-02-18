---
name: FDA Regulatory Intelligence
description: FDA 510(k)/PMA intelligence, predicate research, submission planning, safety analysis, and regulatory drafting via secure bridge API
version: 1.0.0
triggers:
  - "fda predicate"
  - "510k clearance"
  - "510(k)"
  - "medical device submission"
  - "substantial equivalence"
  - "pma approval"
  - "fda research"
  - "predicate device"
  - "device classification"
  - "fda safety"
  - "fda guidance"
  - "fda standards"
  - "fda validate"
  - "fda draft"
  - "fda assemble"
  - "regulatory pathway"
  - "maude adverse"
  - "fda recall"
  - "clinical trials device"
  - "fda warning letters"
  - "eSTAR submission"
  - "fda pipeline"
  - "predicate search"
  - "submission readiness"
  - "fda pre-check"
author: FDA Tools Development Team
license: MIT
bridge_url: http://localhost:18790
bridge_required: true
---

# FDA Regulatory Intelligence

Use this skill when the user needs:
- 510(k) predicate research and substantial equivalence comparison
- PMA approval intelligence and competitive analysis
- Submission planning and readiness assessment
- Safety signal triage (MAUDE adverse events, recalls)
- Clinical trials intelligence for medical devices
- Testing requirements and recognized standards lookup
- Guidance document analysis and requirements mapping
- Regulatory pathway recommendations (510(k)/De Novo/PMA)
- Regulatory prose drafting for submission sections
- eSTAR submission assembly and export
- Warning letter and enforcement action analysis
- UDI/GUDID device identifier lookup
- Portfolio management across multiple submissions

## Security Classification

**CRITICAL:** This skill handles regulatory documents with varying sensitivity levels.

The SecurityGateway enforces a 3-tier data classification model that determines
which LLM providers and communication channels are permitted:

### PUBLIC Data
- FDA databases (openFDA, GUDID, ClinicalTrials.gov)
- Published 510(k) summaries and PMA approval orders
- FDA guidance documents and recognized standards lists
- MAUDE adverse event reports (public record)
- Recall and warning letter databases

**Allowed:** Any LLM provider, any channel (WhatsApp, Telegram, Slack, Discord, file)

### RESTRICTED Data
- Derived intelligence reports and analysis
- Competitive dashboards and market analysis
- Predicate comparison matrices
- Safety signal triage reports

**Allowed:** Cloud LLM with warnings displayed, most channels with disclaimers

### CONFIDENTIAL Data
- Company device specifications and test data
- Draft submission sections and regulatory prose
- eSTAR packages and assembled submissions
- Project-specific device profiles and review decisions
- Internal predicate scoring and strategy documents

**Allowed:** Local LLM (Ollama) ONLY, file output ONLY. Cloud LLMs and messaging
channels are BLOCKED. The SecurityGateway enforces this IMMUTABLY.

## Available Commands (68 Total)

### Getting Started
| Command | Description |
|---------|-------------|
| `start` | Interactive onboarding wizard -- detects existing data, recommends command sequence |
| `configure` | View or modify settings and data directory paths |
| `example` | Randomized end-to-end exercise of all plugin commands |
| `ask` | Natural language Q&A about FDA regulatory topics |

### Core Research Commands
| Command | Description |
|---------|-------------|
| `research` | Research and plan a 510(k) submission -- predicate selection, testing strategy, regulatory intelligence |
| `validate` | Validate FDA device numbers (K/P/DEN/N-numbers) against official databases |
| `analyze` | Analyze FDA data from any pipeline stage -- extraction results, predicate relationships |
| `extract` | Run the FDA 510(k) two-stage pipeline -- download PDFs then extract predicates |
| `propose` | Manually propose predicate and reference devices with confidence scoring |
| `search-predicates` | Feature-based predicate discovery across all 510(k) summary sections |
| `smart-predicates` | Smart predicate recommendations using TF-IDF similarity matching |
| `batchfetch` | Interactive FDA 510(k) data collection with AI-guided selection and API enrichment |
| `pathway` | Recommend optimal FDA regulatory pathway with scoring and cost estimates |

### Safety and Surveillance
| Command | Description |
|---------|-------------|
| `safety` | Analyze MAUDE adverse events and recall history for safety intelligence |
| `warnings` | Search FDA warning letters and enforcement actions |
| `inspections` | Look up FDA inspection history and compliance actions |
| `trials` | Search ClinicalTrials.gov for clinical studies involving similar devices |
| `lineage` | Trace predicate citation chains, flag recalled ancestors, score chain health |
| `monitor` | Monitor FDA databases for new clearances, recalls, and guidance updates |

### Standards and Guidance
| Command | Description |
|---------|-------------|
| `standards` | Look up FDA Recognized Consensus Standards by product code or keyword |
| `generate-standards` | Identify potentially applicable standards using knowledge-based analysis |
| `guidance` | Look up FDA guidance documents, extract requirements, map to testing needs |
| `literature` | Search and analyze clinical/scientific literature via PubMed |
| `traceability` | Generate requirements traceability matrix mapping guidance to tests and evidence |

### Analysis and Comparison
| Command | Description |
|---------|-------------|
| `compare-se` | Generate FDA Substantial Equivalence comparison tables |
| `compare-sections` | Compare 510(k) sections across devices for regulatory intelligence |
| `consistency` | Cross-validate all project files for internal consistency (17 checks) |
| `gap-analysis` | Analyze gaps in 510(k) data -- missing K-numbers, PDFs, extractions |
| `auto-gap-analysis` | Automated gap analysis identifying missing data, weak predicates, testing gaps |
| `summarize` | Summarize and compare sections across multiple 510(k) summary PDFs |

### Drafting and Submission
| Command | Description |
|---------|-------------|
| `draft` | Generate regulatory prose drafts for submission sections |
| `assemble` | Assemble eSTAR-structured submission package from project data |
| `export` | Export submission package in FDA eCopy format, eSTAR XML, or zip |
| `pre-check` | Simulate FDA review team evaluation, generate submission readiness score |
| `presub` | Plan a Pre-Submission meeting with FDA -- cover letter, meeting request, topics |
| `submission-outline` | Generate 510(k) submission outline with section checklists and testing gap analysis |
| `test-plan` | Generate risk-based testing plan with gap analysis and prioritized test matrix |

### Project Management
| Command | Description |
|---------|-------------|
| `status` | Show available FDA pipeline data, file freshness, and record counts |
| `cache` | Show cached FDA data for a project -- freshness and summary |
| `dashboard` | Project status dashboard -- drafted sections, readiness score, next steps |
| `portfolio` | Cross-project portfolio dashboard -- shared predicates, common guidance, timeline |
| `review` | Interactive review of extracted predicates -- reclassify, score, accept/reject |
| `audit` | View decision audit trail -- filter by command, action, date |
| `import` | Import eSTAR data from PDF or XML into project data |
| `update-data` | Scan and update stale FDA data across projects |
| `data-pipeline` | Run the 510(k) data maintenance pipeline |
| `pipeline` | Run the full FDA 510(k) pipeline end-to-end |

### Calculators and Utilities
| Command | Description |
|---------|-------------|
| `calc` | Regulatory calculators -- shelf life (ASTM F1980), sample size, sterilization dose |
| `udi` | Look up UDI/GUDID records from openFDA and AccessGUDID |
| `pccp` | Generate Predetermined Change Control Plan for AI/ML-enabled devices |

### PMA Intelligence
| Command | Description |
|---------|-------------|
| `pma-search` | Search and analyze PMA approvals, download SSED documents |
| `pma-compare` | Compare PMAs for clinical, device, and safety similarities |
| `pma-intelligence` | Generate intelligence reports for PMA devices |
| `pma-supplements` | Track PMA supplement lifecycle and compliance |
| `pma-timeline` | Predict PMA approval timeline with milestones and risk factors |
| `pma-risk` | Systematic FMEA-style risk assessment for PMA devices |
| `annual-reports` | Track PMA annual report obligations per 21 CFR 814.84 |
| `pas-monitor` | Monitor PMA Post-Approval Study obligations |
| `clinical-requirements` | Map clinical trial requirements from PMA precedent |

### Advanced Analytics (PMA)
| Command | Description |
|---------|-------------|
| `predict-review-time` | Predict PMA or supplement review duration using ML models |
| `approval-probability` | Score PMA supplement approval likelihood with risk flags |
| `maude-comparison` | Compare adverse event profiles across PMA devices |
| `competitive-dashboard` | Generate market intelligence dashboard for PMA device categories |
| `refresh-data` | Trigger automated data refresh workflows for PMA data |
| `monitor-approvals` | Configure FDA approval monitoring with watchlists and alerts |
| `detect-changes` | Detect and track changes in PMA data between refresh cycles |
| `integrate-external` | Query external data sources for PMA device intelligence |

### Evaluation
| Command | Description |
|---------|-------------|
| `expert-eval` | Start expert evaluation session for medical device professionals |
| `analyze-expert-evals` | Analyze aggregated expert evaluation results |
| `simulate-expert-panel` | Simulate expert panel evaluation with AI regulatory experts |

## Example Conversations

### Example 1: Predicate Research (PUBLIC)

**User:** "I need to find predicates for a cardiovascular catheter with product code DQY"

**Skill action:** Executes `research` with args `--product-code DQY`
- Classification: PUBLIC (FDA database query)
- LLM Provider: anthropic (cloud safe for public data)
- Channel: whatsapp (allowed for PUBLIC)
- Result: Returns list of relevant predicates with clearance details, testing strategy,
  and regulatory intelligence

### Example 2: Device Validation (PUBLIC)

**User:** "Can you validate K240001 and tell me about that device?"

**Skill action:** Executes `validate` with args `K240001`
- Classification: PUBLIC (published 510(k) clearance)
- LLM Provider: anthropic (cloud safe)
- Channel: telegram (allowed for PUBLIC)
- Result: Returns device details, applicant, clearance date, predicate chain

### Example 3: Draft Section (CONFIDENTIAL -- BLOCKED on messaging)

**User:** "Draft the device description section for my project ABC001"

**Skill action:** Attempts `draft` with args `device-description --project ABC001`
- Classification: CONFIDENTIAL (project data)
- Channel: whatsapp (NOT allowed for CONFIDENTIAL)
- Result: BLOCKED with security warning
- Message: "This command accesses CONFIDENTIAL project data. Messaging channels
  are not permitted for confidential data. Please use file output or a local
  terminal session instead."

### Example 4: Safety Analysis (PUBLIC)

**User:** "Show me adverse events for product code GEI electrosurgical devices"

**Skill action:** Executes `safety` with args `--product-code GEI`
- Classification: PUBLIC (MAUDE public database)
- LLM Provider: anthropic (cloud safe)
- Channel: slack (allowed for PUBLIC)
- Result: Returns MAUDE event analysis, recall history, safety signal triage

### Example 5: Regulatory Pathway (PUBLIC/RESTRICTED)

**User:** "What regulatory pathway should I use for a new AI-powered diagnostic device?"

**Skill action:** Executes `pathway` with args from conversation context
- Classification: RESTRICTED (derived intelligence)
- LLM Provider: anthropic (with warnings)
- Channel: discord (allowed for RESTRICTED with disclaimer)
- Result: Returns pathway recommendation with scoring, cost estimates, timeline

## Error Handling

The skill handles errors at multiple levels:

1. **Bridge Server Unavailable:** Returns instructions to start the bridge server
2. **Security Violation:** Returns classification details and what is permitted
3. **Command Not Found:** Lists available commands with brief descriptions
4. **API Timeout:** Retries with exponential backoff (3 attempts)
5. **Invalid Arguments:** Returns command usage hint from frontmatter

## Installation

1. Copy this skill directory to OpenClaw skills:
   ```bash
   cp -r /path/to/openclaw-skill ~/.openclaw/workspace/skills/fda-tools
   ```

2. Install dependencies:
   ```bash
   cd ~/.openclaw/workspace/skills/fda-tools
   npm install
   ```

3. Start the FDA Bridge Server:
   ```bash
   cd /path/to/fda-tools
   python3 bridge/server.py
   ```

4. Restart OpenClaw to load the skill

5. Test with: "fda research for product code DQY"

## Architecture

```
Messaging Platform --> OpenClaw Gateway (ws://127.0.0.1:18789)
                          |
                          | trigger phrase match
                          v
                    FDA Tools Skill (this skill)
                          |
                          | HTTP POST
                          v
                    FDA Bridge Server (http://localhost:18790)
                          |
                          | SecurityGateway + AuditLogger
                          v
                    FDA Tools Plugin (68 commands)
```
