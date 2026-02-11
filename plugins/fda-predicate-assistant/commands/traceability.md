---
description: Generate a requirements traceability matrix mapping guidance requirements to risks, tests, and evidence — identifies gaps in submission coverage
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: "--project NAME [--product-code CODE] [--output FILE]"
---

# FDA 510(k) Requirements Traceability Matrix

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

> For external API dependencies and connection status, see [CONNECTORS.md](../CONNECTORS.md).

## Resolve Plugin Root

**Before running any bash commands that reference `$FDA_PLUGIN_ROOT`**, resolve the plugin install path:

```bash
FDA_PLUGIN_ROOT=$(python3 -c "
import json, os
f = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(f):
    d = json.load(open(f))
    for k, v in d.get('plugins', {}).items():
        if k.startswith('fda-predicate-assistant@'):
            for e in v:
                p = e.get('installPath', '')
                if os.path.isdir(p):
                    print(p); exit()
print('')
")
echo "FDA_PLUGIN_ROOT=$FDA_PLUGIN_ROOT"
```

---

You are generating a Requirements Traceability Matrix (RTM) that maps FDA guidance requirements to risks, tests, and evidence. This is a key regulatory deliverable that demonstrates complete coverage of all requirements.

**KEY PRINCIPLE: Every requirement must trace to either a test, a risk mitigation, or an explicit justification for exclusion.** Gaps in traceability are submission risks.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--project NAME` (required) — Project with pipeline data
- `--product-code CODE` — Product code (auto-detect from project if not specified)
- `--output FILE` — Write matrix to file (default: traceability_matrix.md in project folder)
- `--infer` — Auto-detect product code from project data
- `--format md|csv|json` — Output format (default: md)

## Step 1: Gather Requirements Sources

### From guidance_cache (if available)

```bash
python3 << 'PYEOF'
import json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m: projects_dir = os.path.expanduser(m.group(1).strip())

project = "PROJECT"  # Replace
pdir = os.path.join(projects_dir, project)

# Load requirements matrix
req_path = os.path.join(pdir, 'guidance_cache', 'requirements_matrix.json')
if os.path.exists(req_path):
    with open(req_path) as f:
        reqs = json.load(f)
    for r in reqs:
        print(f"REQ:{r.get('category','?')}|{r.get('requirement','?')}|{r.get('standard','?')}|{r.get('priority','?')}")
else:
    print("REQUIREMENTS:not_found")

# Load standards list
std_path = os.path.join(pdir, 'guidance_cache', 'standards_list.json')
if os.path.exists(std_path):
    with open(std_path) as f:
        stds = json.load(f)
    for s in stds:
        print(f"STD:{s.get('standard','?')}|{s.get('purpose','?')}|{s.get('required','?')}")
else:
    print("STANDARDS:not_found")
PYEOF
```

### From review.json (predicate and reference devices)

```bash
python3 << 'PYEOF'
import json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m: projects_dir = os.path.expanduser(m.group(1).strip())

project = "PROJECT"  # Replace
review_path = os.path.join(projects_dir, project, 'review.json')
if os.path.exists(review_path):
    with open(review_path) as f:
        review = json.load(f)
    # Accepted predicates
    for k, v in review.get('predicates', {}).items():
        if v.get('decision') == 'accepted':
            print(f"PREDICATE:{k}|{v.get('device_info', {}).get('product_code', '?')}|{v.get('confidence_score', 0)}")
    # Reference devices (from /fda:propose)
    for k, v in review.get('reference_devices', {}).items():
        print(f"REFERENCE:{k}|{v.get('device_info', {}).get('product_code', '?')}|{v.get('rationale', 'N/A')}")
    print(f"REVIEW_MODE:{review.get('review_mode', 'unknown')}")
else:
    print("REVIEW:not_found")
PYEOF
```

### From safety data (risk identification)

```bash
# Check for safety intelligence data
cat "$PROJECTS_DIR/$PROJECT_NAME/safety_cache/safety_summary.json" 2>/dev/null || echo "SAFETY:not_found"
```

### From test plan (if available)

```bash
cat "$PROJECTS_DIR/$PROJECT_NAME/test_plan.md" 2>/dev/null || echo "TEST_PLAN:not_found"
```

### From submission outline (gap analysis)

```bash
cat "$PROJECTS_DIR/$PROJECT_NAME/submission_outline.md" 2>/dev/null || echo "OUTLINE:not_found"
```

## Step 2: Build Requirements List

Compile all requirements from available sources:

1. **Guidance requirements**: From guidance_cache/requirements_matrix.json
2. **Cross-cutting requirements**: From `references/guidance-lookup.md` (biocompatibility, sterilization, shelf life, etc.)
3. **Safety-identified risks**: From safety data (common failure modes → requirements)
4. **IFU claim requirements**: From intended use → each claim needs supporting evidence
5. **Reference device requirements**: If review.json contains a `reference_devices` key (from `/fda:propose`), include requirements derived from reference device characteristics. For each reference device:
   - Extract the device's product code and look up its classification requirements
   - If the reference device was cited for a specific feature (stored in rationale), trace that feature's regulatory requirements
   - Add requirements with source = "Reference Device: {K-number} — {rationale}"
   - These appear in the RTM under a "Reference Device Requirements" category

Assign each requirement a unique ID: `REQ-{category}-{number}` (e.g., REQ-BIOCOMPAT-001)

## Step 3: Map to Risks

For each requirement, identify associated risks:

| Risk Source | How to Identify |
|-------------|----------------|
| Safety data | Common failure modes from MAUDE analysis |
| Guidance | Risks called out in guidance documents |
| Device description | Material, electrical, software risks |
| IFU claims | Clinical claims requiring evidence |
| Predicate history | Recalled predicates → failure modes |

Assign risk IDs: `RISK-{number}` (e.g., RISK-001)

## Step 4: Map to Tests and Evidence

For each requirement, identify the test or evidence that addresses it:

| Evidence Type | Source |
|--------------|--------|
| Bench testing | test_plan.md, guidance requirements |
| Biocompatibility | ISO 10993 test plan |
| Sterilization | Sterilization validation plan |
| Shelf life | Accelerated aging plan |
| Clinical | Literature review, clinical study |
| Predicate precedent | Predicate testing from SE comparison |

Assign test IDs: `TEST-{category}-{number}` (e.g., TEST-BIOCOMPAT-001)

## Step 5: Generate Traceability Matrix

Generate the RTM document (see `references/output-formatting.md` for formatting standards):

```markdown
# Requirements Traceability Matrix
## {Device Description} — Product Code {CODE}

**Generated:** {date} | v5.22.0
**Project:** {project_name}
**Requirements sources:** {list}

---

## Full Traceability Matrix

| Req ID | Requirement | Source | Risk ID | Risk | Test ID | Test/Evidence | Status |
|--------|------------|--------|---------|------|---------|---------------|--------|
| REQ-BIOCOMPAT-001 | ISO 10993-5 Cytotoxicity | Cross-cutting guidance | RISK-001 | Cytotoxic reaction | TEST-BIOCOMPAT-001 | ISO 10993-5 testing | PLANNED |
| REQ-BIOCOMPAT-002 | ISO 10993-10 Sensitization | Cross-cutting guidance | RISK-002 | Allergic reaction | TEST-BIOCOMPAT-002 | ISO 10993-10 testing | PLANNED |
| REQ-STERIL-001 | Sterilization validation | Cross-cutting guidance | RISK-003 | Non-sterile device | TEST-STERIL-001 | ISO 11135 validation | PLANNED |
| REQ-PERF-001 | {Device-specific test} | Device guidance | RISK-004 | {failure mode} | TEST-PERF-001 | {test method} | PLANNED |
| REQ-IFU-001 | {IFU claim} evidence | IFU analysis | RISK-005 | Unsupported claim | TEST-CLIN-001 | Literature review | GAP |

---

## Coverage Summary

| Category | Requirements | With Tests | With Risks | Gaps |
|----------|-------------|-----------|-----------|------|
| Biocompatibility | {N} | {N} | {N} | {N} |
| Sterilization | {N} | {N} | {N} | {N} |
| Performance | {N} | {N} | {N} | {N} |
| Clinical | {N} | {N} | {N} | {N} |
| **Total** | **{N}** | **{N}** | **{N}** | **{N}** |

## Gaps Requiring Attention

{For each requirement without a mapped test:}
- **{Req ID}**: {Requirement} — No test or evidence mapped.
  → Recommendation: {specific action}

## Risk-to-Requirement Mapping

{For each risk without a mapped requirement:}
- **{Risk ID}**: {Risk} — Identified from {source} but no formal requirement addresses it.
  → Recommendation: {specific action}

---

> **Disclaimer:** This traceability matrix is AI-generated from public FDA data.
> Verify independently. Not regulatory advice.
```

## Output Formats

The `--format` flag controls the output format:

### Markdown (default: `--format md`)
Standard markdown table output — human-readable, suitable for review and GitHub rendering.

### CSV (`--format csv`)
Comma-separated values compatible with import into requirements management tools:
- **Spreadsheet-based QMS**: Direct open in spreadsheet applications, compatible with quality system templates

CSV columns: `Req_ID, Requirement, Source, Risk_ID, Risk, Test_ID, Test_Evidence, Status, Category`

### JSON (`--format json`)
Structured JSON for programmatic consumption and integration with automated QMS tools.

## Design History File (DHF) Context

Per **21 CFR 820.30** (Design Controls), the Design History File must contain or reference:
- Design and development planning records
- Design input and output records
- Design review records
- Design verification and validation records
- **Requirements traceability** — this RTM fulfills this requirement

### How This RTM Fits Into the DHF

| DHF Element | RTM Contribution |
|-------------|------------------|
| Design Input | Requirements column (REQ-*) traces to guidance/regulatory inputs |
| Design Output | Test/Evidence column (TEST-*) traces to verification outputs |
| Risk Management | Risk column (RISK-*) links to ISO 14971 risk analysis |
| Verification | Test protocols and acceptance criteria in TEST-* entries |
| Validation | Clinical evidence entries in TEST-CLIN-* entries |

> **Note:** Requirement IDs generated by this plugin (REQ-BIOCOMPAT-001, TEST-PERF-001, etc.) are internal plugin identifiers. They must be mapped to your company's actual requirements management system IDs before inclusion in the formal DHF.

## Step 6: Write Output

Write to `$PROJECTS_DIR/$PROJECT_NAME/traceability_matrix.md` (or specified output).

If `--format csv`, write `traceability_matrix.csv`:
```csv
Req_ID,Requirement,Source,Risk_ID,Risk,Test_ID,Test_Evidence,Status,Category
REQ-BIOCOMPAT-001,ISO 10993-5 Cytotoxicity,Cross-cutting guidance,RISK-001,Cytotoxic reaction,TEST-BIOCOMPAT-001,ISO 10993-5 testing,PLANNED,Biocompatibility
```

Also write `traceability_matrix.json` for programmatic use:

```json
{
  "version": 1,
  "generated_at": "2026-02-05T12:00:00Z",
  "project": "PROJECT_NAME",
  "requirements": [...],
  "risks": [...],
  "tests": [...],
  "traces": [
    {"requirement": "REQ-BIOCOMPAT-001", "risk": "RISK-001", "test": "TEST-BIOCOMPAT-001", "status": "PLANNED"}
  ],
  "gaps": [...]
}
```

## Step 7: Risk Management Integration

When building the traceability matrix, include a dedicated risk management row type that maps:

```
Hazard → Risk Control → Verification Test → Evidence
```

### Auto-Populate Hazards from Device Type

Use `references/risk-management-framework.md` hazard templates to pre-populate risk rows based on device type:

1. **Determine device type** from product code classification (implant, SaMD, wound care, electrical)
2. **Load hazard template** matching the device type
3. **Generate risk rows** with format: `RISK-HAZ-{number}`

### Risk Management Rows in RTM

```markdown
## Risk Management Traceability

| Hazard ID | Hazard | Severity | Risk Control | Verification | Evidence | Status |
|-----------|--------|----------|-------------|-------------|----------|--------|
| HAZ-001 | {hazard from template} | {severity} | {control measure} | TEST-{id} | {test method} | PLANNED |
| HAZ-002 | {hazard from template} | {severity} | {control measure} | TEST-{id} | {test method} | PLANNED |
```

### Cross-Reference

Each risk row should map to:
- At least one requirement (REQ-*) that the risk control satisfies
- At least one test (TEST-*) that verifies the risk control
- The ISO 14971 risk evaluation (severity x probability = risk level)

If a hazard has no mapped test: flag as **GAP** with recommendation.

## Error Handling

- **No project**: ERROR: "Project name required."
- **No guidance data**: Generate matrix from cross-cutting requirements only. Note: "Run /fda:guidance first for device-specific requirements."
- **No safety data**: Generate matrix without risk mapping. Note: "Run /fda:safety for risk identification from MAUDE data."
- **No test plan**: Generate requirements and risks, mark all tests as "NOT PLANNED". Note: "Run /fda:test-plan for test planning."
- **Unknown device type for risk templates**: Use generic hazard categories from `references/risk-management-framework.md`. Note: "Using generic hazard template. Provide device description for device-specific risk analysis."
