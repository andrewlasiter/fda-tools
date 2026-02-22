# OpenClaw E2E Usability Assessment — MDRP Platform
## FDA-310 | Generated: 2026-02-22 | Status: Sprint 31 Target

---

## Executive Summary

OpenClaw (Claude Code + FDA Tools Plugin) is the **primary human interface** to the MDRP platform. The bridge server at `localhost:18790` exposes 14 REST endpoints that translate Claude's tool calls into FDA regulatory intelligence. This assessment maps current interaction modes, identifies friction points, and proposes 8 new slash commands that reduce the time from "device concept" to "510(k) ready" by an estimated 60%.

---

## 1. Current Interaction Architecture

```
Human ──prompt──▶ OpenClaw (Claude Code)
                      │
                      ▼ (TypeScript skill tools)
              Bridge Server :18790
              ┌───────────────────────────────┐
              │ POST /execute                 │ ← Most used: run any FDA command
              │ GET  /health                  │ ← Status + system health
              │ GET  /commands                │ ← List available commands
              │ POST /session                 │ ← Create project session
              │ GET  /session/{id}/questions  │ ← HITL gate prompts
              │ POST /session/{id}/answer     │ ← HITL gate responses
              │ GET  /audit/integrity         │ ← Part 11 audit verification
              └───────────────────────────────┘
                      │
                      ▼
              FastAPI Plugin (Python)
              ┌───────────────────────────────┐
              │ FDA 510(k) Database           │
              │ MAUDE Adverse Events          │
              │ OpenFDA Recalls               │
              │ Guidance Document Embeddings  │
              │ CUSUM Signal Detection        │
              │ 21 CFR Part 11 Audit Trail    │
              │ NPD State Machine             │
              └───────────────────────────────┘
                      │
              Next.js Web App (port 3000)
              ┌───────────────────────────────┐
              │ /dashboard  — KPI overview    │
              │ /agents     — Agent control   │
              │ /research   — Search + SE     │
              │ /documents  — Draft studio    │
              │ /projects   — NPD pipeline    │
              └───────────────────────────────┘
```

### Current Interaction Modes

| Mode | Description | Status |
|------|-------------|--------|
| **Direct bridge commands** | `POST /execute` with FDA command names | ✅ Working |
| **Session-based projects** | Create session → run commands → persist state | ✅ Working |
| **HITL gate Q&A** | OpenClaw asks question → human answers → gate advances | ✅ Working |
| **Audit log verification** | `GET /audit/integrity` validates Part 11 chain | ✅ Working |
| **Web UI integration** | OpenClaw spawns browser to web app | ⚠️ Partial — demo data only |
| **pgvector semantic search** | Embedding search via Supabase | ⚠️ Stub — wiring incomplete (FDA-311) |
| **Agent orchestration** | Spawn specialized agents via bridge | ✅ Working (via /execute) |

---

## 2. Optimal Interaction Patterns by Persona

### Persona 1: RA Professional (510(k) Submission)

**Goal:** Draft a 510(k) submission with SE analysis in < 1 hour

```
1. /mdrp:new-project SFP-2024 "SmartFlow Infusion Pump" FRN
   → Creates session, seeds device profile, assigns RA agents

2. /mdrp:predicate-search --top 5
   → Cosine search 510(k) DB, ranks by SE score, returns K-numbers

3. /mdrp:compare-se K231045 K198762
   → Pulls both 510(k) summaries, generates side-by-side SE table

4. /mdrp:check-sri
   → Returns SRI score, identifies critical gaps (0-100 scale)

5. /mdrp:draft-section "device-description"
   → AI drafts section using project data + predicate text

6. /mdrp:hitl-review --gate 2
   → Triggers Gate 2 (Drafting Review), assigns to RA Lead
```

### Persona 2: R&D Engineer (Standards + Testing)

**Goal:** Identify applicable standards and testing requirements

```
1. /mdrp:classify FRN
   → Returns device class, regulation number, applicable CFR parts

2. /mdrp:standards-lookup --device-type "infusion pump"
   → Returns ISO 10993, IEC 60601-2-24, FDA 21 CFR 880 requirements

3. /mdrp:safety-signals FRN --years 3
   → CUSUM analysis on MAUDE, identifies top 5 failure modes

4. /mdrp:biocompat-matrix PEEK titanium
   → Returns ISO 10993 test battery for material combination
```

### Persona 3: Startup / First-Time Submitter

**Goal:** Understand regulatory pathway for their device

```
1. /mdrp:pathway-wizard
   → Guided Q&A: device description → risk class → 510(k)/De Novo/PMA

2. /mdrp:readiness-check
   → Plain-English readiness report: what you have, what you need

3. /mdrp:estimate-timeline
   → Historical FDA review time for similar device types
```

### Persona 4: RA Consultant (Multi-client)

**Goal:** Manage multiple projects, generate client-ready reports

```
1. /mdrp:project-list
   → Table of all projects: stage, SRI score, next action, deadline

2. /mdrp:cross-project-consistency
   → Flags SE inconsistencies across related device families

3. /mdrp:export-report --format pdf --client "AcmeMed"
   → Branded PDF with SRI score, SE table, predicate chain
```

### Persona 5: Post-Market Surveillance

**Goal:** Monitor cleared device for safety signals

```
1. /mdrp:monitor-maude FRN --alert cusum
   → Set up CUSUM watcher, notifies on spike

2. /mdrp:mdr-tracker --year 2025
   → MDR filing status, 30/5-day report deadlines

3. /mdrp:annual-report FRN 2025
   → Generates Post-Market Surveillance Report draft
```

---

## 3. Bridge API Endpoint Map

| Endpoint | Method | OpenClaw Workflow | Latency Target |
|----------|--------|-------------------|----------------|
| `/health` | GET | Startup check, status pages | < 50ms |
| `/execute` | POST | All FDA command execution | < 2s |
| `/commands` | GET | Autocomplete, /help output | < 100ms |
| `/session` | POST | Project initialization | < 200ms |
| `/session/{id}` | GET | Project state retrieval | < 100ms |
| `/sessions` | GET | Project list for RA consultant | < 200ms |
| `/session/{id}/questions` | GET | HITL gate polling | < 100ms |
| `/session/{id}/answer` | POST | HITL gate resolution | < 200ms |
| `/tools` | GET | Available tool emulators | < 100ms |
| `/tool/execute` | POST | Direct tool invocation | < 3s |
| `/audit/integrity` | GET | Part 11 compliance check | < 500ms |
| `/metrics` | GET | Agent performance dashboard | < 200ms |

**Missing endpoints (Sprint 31 targets — FDA-310/311):**
- `POST /research/search` — pgvector semantic search (FDA-311)
- `GET /projects/{id}/sri` — SRI score with breakdown
- `POST /hitl/gate/{id}/sign` — Cryptographic HITL signing (FDA-309)
- `GET /agents/status` — Live agent grid for web UI

---

## 4. Recommended New Slash Commands (8)

### `/mdrp:new-project <name> <device-desc> <product-code>`
Creates a new NPD project session. Initializes device profile, assigns stage-appropriate agent team, returns session ID and initial SRI score.

### `/mdrp:predicate-search [--top N] [--area CV|OR|NE|...]`
Cosine similarity search against the 510(k) database using current project's device description. Returns ranked predicates with similarity scores, SE gaps, and recall health status.

### `/mdrp:compare-se <K-number> [<K-number-2>]`
Runs compare-se.md for the current project against one or two predicates. Returns formatted SE comparison table ready for 510(k) Section 2.

### `/mdrp:check-sri`
Returns Submission Readiness Index (0-100) with a breakdown: which sections are complete, which have gaps, and top 3 actions to improve the score.

### `/mdrp:draft-section <section-id>`
Invokes the AI drafting agent for a specific 510(k) section. Returns draft with confidence score. Sections: `device-description`, `se-comparison`, `performance-testing`, `biocompatibility`, `sterility`, `software`, `hfe`.

### `/mdrp:safety-signals <product-code> [--years N]`
CUSUM analysis on MAUDE data. Returns signal summary: event count, spike dates, top failure mode categories, and citation-ready text for Section 4.

### `/mdrp:hitl-review [--gate N]`
Queries the HITL gate system for current project. Shows gate details, prompts for approve/reject/escalate decision, cryptographically signs the outcome with CFR_PART11_SIGNING_KEY.

### `/mdrp:status`
Quick project health check: current NPD stage, SRI score, next HITL gate, agent activity summary, open MAUDE signals. Designed for daily stand-up use.

---

## 5. Current Pain Points

### P1 — High Impact

1. **No command autocomplete**: Users must remember exact FDA command names. A `/mdrp:commands` listing with descriptions and examples would eliminate this friction.

2. **Session state not visible in web UI**: When OpenClaw creates a session via bridge, `/projects` shows demo data only. FDA-315 wires TanStack hooks to live API.

3. **HITL gate is text-only**: OpenClaw presents gate decisions as raw JSON. The web UI `HitlGateIntegration` component is never invoked from OpenClaw — a missed UX opportunity for RA professionals.

4. **No structured output format**: `/execute` returns raw Python stdout. RA professionals need typed JSON they can pipe into their own workflows and tools.

5. **60 E2E tests all skipped**: `test_e2e_openclaw_integration.py` has 60 tests marked `pytest.skip("Bridge server not running")`. A `pytest-asyncio` fixture that starts the bridge in-process would unlock these.

### P2 — Medium Impact

6. **No streaming output**: Large drafting operations (full 510(k) section) return after 30-60 seconds with no intermediate output. Users think the system is hung. Server-Sent Events needed.

7. **API key rotation gap**: `CFR_PART11_SIGNING_KEY` and `NEXT_PUBLIC_BRIDGE_API_KEY` have no rotation mechanism. Enterprise deployments need key rotation without downtime.

---

## 6. Complete E2E Workflow Examples

### Workflow A: First 510(k) Submission in 2 Hours

```
User: /mdrp:new-project "InfuFlow 510k" "Smart infusion pump" FRN
Claude: ✓ Session ffd2a4b created. SRI: 12/100. Stage: CONCEPT.
        3 agents assigned: fda-classifier, fda-predicate-search, fda-risk-analyst

User: /mdrp:predicate-search --top 3
Claude: 1. K231045 (InfuPro 3000) — SE score: 94%  ← Best predicate
        2. K198762 (FlowMaster II) — SE score: 87%
        3. K221889 (MediFlow X)   — SE score: 81%
        Recall history: K231045 HEALTHY, K198762 CAUTION (1 Class III recall 2023)

User: /mdrp:compare-se K231045
Claude: [SE table — 12 comparison rows generated]
        3 SE gaps: flow rate range, display type, BLE connectivity
        SRI updated: 12 → 41

User: /mdrp:draft-section device-description
Claude: [1,847 word draft with all required CFR elements]
        Confidence: 88%. Review flags: trade name consistency, IFU claim alignment.

User: /mdrp:check-sri
Claude: SRI Score: 67/100
        ✅ Device Description: 95%  ✅ SE Analysis: 82%
        ⚠️ Performance Testing: 43%  ❌ Form 3881: Not started
        Next: (1) Add shelf life data (2) Complete Form 3881 (3) Upload IFU

User: /mdrp:hitl-review --gate 1
Claude: Gate 1: Classification & Pathway Review
        Device: SmartFlow Infusion Pump | FRN | Class II | K231045 predicate
        [APPROVE / REJECT / ESCALATE] → approve
Claude: ✓ Gate 1 approved. HMAC signed. Part 11 audit record created.
        Stage advanced: CLASSIFY → PREDICATE
```

### Workflow B: Safety Signal Alert (Post-Market)

```
User: /mdrp:safety-signals FRN --years 2
Claude: CUSUM Analysis — FRN Infusion Pumps (2024-2026)
        Total adverse events: 1,847
        CUSUM SPIKE DETECTED: 2025-Q3 (+3.2σ above baseline)
        Top failure modes: Air-in-line alarm (34%), Occlusion mistracking (22%)
        Citation: "Signal detected per CUSUM methodology. MAUDE, FRN, 2024-01 to 2026-02."

User: /mdrp:monitor-maude FRN --alert cusum --threshold 2.5
Claude: ✓ CUSUM watcher activated for FRN
        Threshold: 2.5σ | Polling: every 24h | Notify: this session
```

### Workflow C: RA Consultant Multi-Client Dashboard

```
User: /mdrp:project-list
Claude: Active Projects (4):
        InfuFlow 510(k)    DRAFTING   SRI 74  Draft §4         Apr 30
        ScanMate 510(k)    PREDICATE  SRI 48  Predicate search  Mar 15 ⚠
        NeuroStim PMA      PRESUB     SRI 61  Pre-Sub meeting   Jun 01
        WoundGuard 510(k)  CLEARED    SRI 92  Post-market mon.  Done ✅
        ⚠ ScanMate deadline is 21 days away with SRI 48 — prioritize.
```

---

## 7. Implementation Roadmap

### Sprint 31 (FDA-310 deliverables)
- [ ] OpenAPI spec auto-generated at `/openapi.json` (FastAPI built-in, just needs enabling)
- [ ] `POST /research/search` endpoint for pgvector (FDA-311)
- [ ] `GET /agents/status` endpoint for live agent grid
- [ ] `POST /hitl/gate/{id}/sign` with HMAC signing (FDA-309)
- [ ] 8 slash command specs in `commands/mdrp-*.md`

### Sprint 32 (full integration)
- [ ] `pytest-asyncio` fixture: start bridge in-process for 60 E2E tests
- [ ] Server-Sent Events for `/execute` streaming output
- [ ] Structured JSON response wrapper for all `/execute` outputs
- [ ] Demo data replacement — all pages use TanStack hooks (FDA-315)

---

## 8. Usability Score Summary

| Dimension | Current | Target (Sprint 32) |
|-----------|---------|-------------------|
| Time to first predicate search | 15 min | 2 min |
| SE comparison table | Manual copy-paste | Automated `/mdrp:compare-se` |
| HITL gate via OpenClaw | Text-only raw JSON | Cryptographically signed, web-synced |
| Web UI live data | 0% (demo consts) | 100% (live TanStack API) |
| E2E test coverage | 0/60 (all skipped) | 60/60 |
| Slash commands | 0 | 8 |
| Bridge API completeness | 11/14 endpoints wired | 14/14 |

**Overall OpenClaw ↔ MDRP usability: 4/10 today → projected 9/10 post Sprint 32**

The platform has exceptional depth — 167 agents, full 12-stage NPD pipeline, CUSUM signal detection, 21 CFR Part 11 audit trails — but the OpenClaw ↔ Bridge ↔ Web UI integration layer is the critical gap between a powerful tool and a seamless workflow. FDA-310 + FDA-311 + FDA-315 are the critical path.
