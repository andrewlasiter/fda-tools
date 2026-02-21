# Architecture Overview

This document describes the high-level architecture of FDA Tools, including system components,
data flow, and key integration points.

---

## System Architecture

```mermaid
graph TB
    subgraph User["User Interface"]
        CLI[Claude Code<br/>slash commands]
        FCLI[fda-* CLI<br/>entry points]
    end

    subgraph Plugin["FDA Tools Plugin (fda_tools)"]
        CMD[commands/<br/>42 slash commands]
        AGENTS[agents/<br/>7 autonomous agents]
        LIB[lib/<br/>49 core modules]
        SCRIPTS[scripts/<br/>CLI scripts]
        BRIDGE[bridge/<br/>FastAPI server]
    end

    subgraph Storage["Local Storage (~/.fda_tools/)"]
        PROJ[projects/<br/>device_profile.json<br/>review.json<br/>drafts/]
        CACHE[cache/<br/>rate limiter state<br/>quota tracking]
        DB[(postgres/<br/>510k database)]
    end

    subgraph External["External APIs"]
        OPENFDA[openFDA<br/>Device API]
        CLINICAL[ClinicalTrials.gov]
        PUBMED[PubMed]
        LINEAR[Linear<br/>Issue Tracker]
    end

    CLI --> CMD
    CLI --> AGENTS
    FCLI --> SCRIPTS
    CMD --> LIB
    AGENTS --> LIB
    SCRIPTS --> LIB
    BRIDGE --> LIB

    LIB --> PROJ
    LIB --> CACHE
    LIB --> DB

    SCRIPTS --> OPENFDA
    LIB --> OPENFDA
    LIB --> CLINICAL
    LIB --> PUBMED
    AGENTS --> LINEAR
```

---

## 510(k) Submission Workflow

The primary user workflow — from predicate research to submission assembly.

```mermaid
flowchart LR
    A([Start]) --> B[/batchfetch\nFind predicates]
    B --> C[/review\nAccept predicates]
    C --> D[/compare-se\nSE comparison table]
    D --> E[/draft\nGenerate 18 eSTAR sections]
    E --> F[/consistency\nCross-check 17 rules]
    F --> G[/assemble\nPackage for filing]
    G --> H[/pre-check\nSimulate RTA review]
    H --> I([Submit])

    B -.->|openFDA API| FDA[(FDA Database)]
    D -.->|device_profile.json| DP[(Project Data)]
    E -.->|standards_lookup.json| DP
    G -.->|eSTAR XML| PKG[/submission_package/]
    H -.->|SRI score| RPT[/readiness_report.md/]
```

---

## Data Flow — Batch Fetch Pipeline

How raw openFDA data is collected, enriched, and stored locally.

```mermaid
sequenceDiagram
    participant U as User
    participant BF as batchfetch.py
    participant API as openFDA API
    participant EN as fda_enrichment.py
    participant RL as CrossProcessRateLimiter
    participant DP as device_profile.json

    U->>BF: /batchfetch --product-codes DQY
    BF->>RL: acquire token (240 req/min w/ key)
    RL-->>BF: token granted
    BF->>API: GET /device/510k?device_name=...
    API-->>BF: JSON results (paginated)
    BF->>API: GET /device/classification?...
    API-->>BF: classification data
    BF->>EN: enrich(device_list)
    EN->>API: GET /device/event?... (MAUDE)
    EN->>API: GET /device/recall?...
    EN-->>BF: enriched_devices + intelligence_report
    BF->>DP: write device_profile.json
    BF-->>U: CSV export + HTML dashboard
```

---

## Library Module Dependency Map

Key relationships between the 49 `lib/` modules.

```mermaid
graph LR
    subgraph Core["Core Infrastructure"]
        CFG[config.py]
        LOG[logger.py]
        LOG2[logging_config.py]
        ERR[user_errors.py]
        IMP[import_helpers.py]
    end

    subgraph Security["Security & Access Control"]
        AUTH[auth.py]
        RBAC[rbac.py]
        SEC[secure_config.py]
        SDS[secure_data_storage.py]
        SAP[secure_argparse.py]
        MON[monitoring_security.py]
        SIG[signatures.py]
        PV[path_validator.py]
        IV[input_validators.py]
    end

    subgraph RateLimiting["Rate Limiting"]
        CPR[cross_process_rate_limiter.py]
        RL[rate_limiter.py]
        QT[quota_tracker.py]
    end

    subgraph Storage["Storage & Caching"]
        CM[cache_manager.py]
        PB[project_backup.py]
        BM[backup_manager.py]
        RC[refresh_checkpoint.py]
        PD[postgres_database.py]
    end

    subgraph Validation["Validation"]
        MV[manifest_validator.py]
        PSV[project_schema_validator.py]
        EV[expert_validator.py]
        MI[mcp_integrity.py]
    end

    subgraph Analytics["Analytics & Scoring"]
        DCS[data_completeness_scorer.py]
        PRA[predicate_ranker.py]
        PRE[predicate_diversity.py]
        PGA[predicate_gap_analyzer.py]
        GA[gap_analyzer.py]
        FA[feature_analytics.py]
        PB2[performance_baseline.py]
        MET[metrics.py]
    end

    subgraph Regulatory["Regulatory Processing"]
        FE[fda_enrichment.py]
        EFE[estar_field_extractor.py]
        SGD[standards_gap_detector.py]
        TGD[testing_gap_detector.py]
        DNS[de_novo_support.py]
        HDE[hde_support.py]
        CD[combination_detector.py]
        PMS[post_market_surveillance.py]
        RWE[rwe_integration.py]
        DIS[disclaimers.py]
        EE[ecopy_exporter.py]
    end

    subgraph Users["User Management"]
        USR[users.py]
        UE[user_errors.py]
    end

    CFG --> LOG
    CFG --> SEC
    AUTH --> RBAC
    AUTH --> USR
    CPR --> QT
    RL --> CPR
    SEC --> SDS
    FE --> CPR
    FE --> PD
    GA --> DCS
    GA --> SGD
    GA --> TGD
```

---

## Multi-Agent Orchestrator Architecture

The orchestrator coordinates specialized agents for automated code review and Linear issue creation.

```mermaid
flowchart TD
    subgraph Input["Input"]
        GIT[git diff / PR]
        ISSUE[Linear issue]
    end

    subgraph Orchestrator["Universal Orchestrator"]
        TA[TaskAnalyzer<br/>Detect languages,<br/>dimensions, complexity]
        AS[AgentSelector<br/>Score 167 agents<br/>across 12 categories]
        EC[ExecutionCoordinator<br/>4-phase parallel execution]
        AG[AggregatedResults<br/>Dedup + rank findings]
        LI[LinearIntegrator<br/>Create issues by severity]
    end

    subgraph Agents["Agent Teams (examples)"]
        FDA[FDA Regulatory<br/>23 agents]
        QA[QA / Security<br/>15 agents]
        LANG[Language Specialists<br/>24 agents]
        INFRA[Infrastructure<br/>16 agents]
    end

    subgraph Output["Output"]
        LISSUES[Linear Issues<br/>CRITICAL / HIGH / MEDIUM]
        REPORT[Review Report<br/>findings_by_severity]
    end

    GIT --> TA
    ISSUE --> TA
    TA -->|TaskProfile| AS
    AS -->|ReviewTeam| EC
    EC --> FDA
    EC --> QA
    EC --> LANG
    EC --> INFRA
    FDA & QA & LANG & INFRA --> AG
    AG --> LI
    LI --> LISSUES
    AG --> REPORT
```

**Agent selection weights (static):**

| Dimension | Weight |
|-----------|--------|
| Review dimension match | 40% |
| Language match | 30% |
| Domain match | 20% |
| Model tier | 10% |

---

## Bridge Server Integration

The FastAPI bridge server exposes `lib/` functionality over HTTP for IDE and external tool integration.

```mermaid
sequenceDiagram
    participant IDE as IDE / External Tool
    participant BR as bridge/server.py (FastAPI)
    participant AUTH as auth.py (JWT)
    participant LIB as lib/ modules
    participant DP as Project Data

    IDE->>BR: POST /api/validate {project_id, data}
    BR->>AUTH: verify JWT token
    AUTH-->>BR: claims (user, role)
    BR->>LIB: manifest_validator.validate(data)
    LIB->>DP: read device_profile.json
    DP-->>LIB: project data
    LIB-->>BR: ValidationResult
    BR-->>IDE: 200 OK {valid: true, issues: []}
```

**Available bridge endpoints:**

| Path | Description |
|------|-------------|
| `GET /health` | Health check (liveness + readiness) |
| `POST /api/validate` | Validate project data against JSON schema |
| `POST /api/export-estar` | Generate eSTAR XML package |
| `POST /api/enrichment` | Run Phase 1+2 enrichment on device list |
| `GET /api/metrics` | Prometheus-format metrics |

---

## Security Architecture

```mermaid
graph TB
    subgraph Boundary["Trust Boundary"]
        USER[User / IDE]
    end

    subgraph Bridge["Bridge Server"]
        JWT[JWT Auth<br/>auth.py]
        RBAC2[RBAC<br/>rbac.py]
        VAL[Input Validation<br/>input_validators.py]
        PATH[Path Validation<br/>path_validator.py]
    end

    subgraph Storage2["Secure Storage"]
        KR[System Keyring<br/>API keys]
        SS[SecureDataStorage<br/>AES-GCM encrypted]
        SC[SecureConfig<br/>env + .env files]
    end

    subgraph Audit["Audit & Monitoring"]
        LOG3[Structured Logging<br/>logger.py]
        MS[Security Monitoring<br/>monitoring_security.py]
        SIG2[Request Signatures<br/>signatures.py]
    end

    USER --> JWT
    JWT --> RBAC2
    RBAC2 --> VAL
    VAL --> PATH
    PATH --> SS
    SC --> KR
    SS --> LOG3
    LOG3 --> MS
    JWT --> SIG2
```

**Key security properties:**

- API keys stored in system keyring (never in config files or environment)
- All file paths validated against `~/.fda_tools/` base directory (no traversal)
- All external inputs sanitized via `input_validators.py` before processing
- JWT + RBAC for bridge server access control
- AES-GCM encryption for sensitive project data at rest

---

## Directory Structure

```
fda-tools/
├── pyproject.toml                  # Build config, dependencies, tool settings
├── mkdocs.yml                      # API documentation config
├── Makefile                        # Common dev tasks (test, lint, docs, etc.)
├── plugins/
│   └── fda_tools/                  # Python package root
│       ├── __init__.py
│       ├── lib/                    # 49 core library modules (stdlib-only, ADR-005)
│       │   ├── config.py           # Central configuration
│       │   ├── cross_process_rate_limiter.py  # Multi-process rate limiting
│       │   └── ...
│       ├── scripts/                # CLI scripts and entry points
│       │   ├── fda_api_client.py   # Centralized openFDA HTTP client
│       │   ├── batchfetch.py       # Main data collection pipeline
│       │   └── ...
│       ├── commands/               # Slash command definitions (markdown)
│       │   ├── batchfetch.md
│       │   ├── draft.md
│       │   └── ...
│       ├── bridge/                 # FastAPI bridge server
│       │   └── server.py
│       ├── tests/                  # Test suite (pytest)
│       │   ├── conftest.py
│       │   └── test_*.py
│       └── .claude-plugin/
│           └── plugin.json         # Plugin manifest
├── docs/                           # Documentation
│   ├── ARCHITECTURE.md             # This file
│   ├── DEVELOPER_GUIDE.md          # Guide for contributors
│   ├── QUICK_START.md
│   ├── INSTALLATION.md
│   ├── TROUBLESHOOTING.md
│   ├── adr/                        # Architecture Decision Records
│   └── api/                        # Auto-generated API reference (MkDocs)
├── examples/                       # Worked 510(k) example projects
│   ├── 01-basic-510k-catheter/
│   ├── 02-samd-digital-pathology/
│   └── 03-combination-product-wound-dressing/
└── tools/
    └── completions/                # Shell completion scripts
        ├── fda-tools.bash
        └── fda-tools.zsh
```

---

## Key Design Decisions

See [`docs/adr/`](adr/) for the full record. Summary of the most impactful decisions:

| ADR | Decision | Rationale |
|-----|----------|-----------|
| [ADR-001](adr/ADR-001-python-over-typescript.md) | Python over TypeScript | NumPy/pandas ecosystem; FDA tooling in Python |
| [ADR-002](adr/ADR-002-local-json-storage.md) | Local JSON storage | No server dependency; portable project files |
| [ADR-003](adr/ADR-003-multi-process-rate-limiting.md) | File-lock rate limiting | Multiple Claude sessions share one API quota |
| [ADR-004](adr/ADR-004-local-only-analytics.md) | Local-only analytics | No PII leaves device; regulatory compliance |
| [ADR-005](adr/ADR-005-stdlib-only-lib-modules.md) | stdlib-only in `lib/` | Importable without pip install; test isolation |
| [ADR-006](adr/ADR-006-dual-assignment-orchestrator.md) | Dual-assignment orchestration | Core + specialist agents reduce review blind spots |
| [ADR-007](adr/ADR-007-postgres-offline-database.md) | PostgreSQL offline DB | Zero-downtime bulk updates; sub-millisecond queries |
