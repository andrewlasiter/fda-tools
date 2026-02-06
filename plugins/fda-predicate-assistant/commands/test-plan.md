---
description: Generate a risk-based testing plan with gap analysis — maps guidance requirements, predicate precedent, and standards into a prioritized test matrix
allowed-tools: Bash, Read, Glob, Grep, Write, WebSearch
argument-hint: "<product-code> [--project NAME] [--device-description TEXT] [--intended-use TEXT] [--output FILE]"
---

# FDA 510(k) Testing Plan Generator

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

You are generating a comprehensive, risk-based testing plan for a 510(k) submission.

**KEY PRINCIPLE: Combine guidance requirements with predicate precedent to create an actionable test matrix.** Each test item is prioritized by regulatory risk and includes specific standards, methods, and acceptance criteria.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Product code** (required) — 3-letter FDA product code
- `--project NAME` — Use project data (guidance_cache, review.json)
- `--device-description TEXT` — Device description for applicability determination
- `--intended-use TEXT` — IFU for claim-to-test mapping
- `--output FILE` — Write test plan to file
- `--infer` — Auto-detect product code from project data
- `--risk-framework iso14971|fmea` — Risk assessment framework (default: iso14971)

If no product code and `--infer` active, use inference logic.

## Step 1: Gather Requirements Data

### From guidance cache (if --project)

```bash
python3 << 'PYEOF'
import json, os, re, glob

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m: projects_dir = os.path.expanduser(m.group(1).strip())

project_name = "PROJECT"  # Replace

# Check guidance cache
guidance_path = os.path.join(projects_dir, project_name, 'guidance_cache', 'guidance_index.json')
if os.path.exists(guidance_path):
    with open(guidance_path) as f:
        guidance = json.load(f)
    print("GUIDANCE:found")
    for s in guidance.get('standards', []):
        print(f"STANDARD:{s.get('standard','')}|{s.get('purpose','')}|{'required' if s.get('required') else 'recommended'}")
else:
    print("GUIDANCE:not_found")

# Check review data for predicate testing info
review_path = os.path.join(projects_dir, project_name, 'review.json')
if os.path.exists(review_path):
    with open(review_path) as f:
        review = json.load(f)
    accepted = sum(1 for v in review.get('predicates', {}).values() if v.get('decision') == 'accepted')
    print(f"REVIEW:found|accepted={accepted}")
else:
    print("REVIEW:not_found")
PYEOF
```

### Classification data

Query openFDA classification API (standard pattern).

## Step 2: Build Test Categories

Based on device classification, description, and guidance:

### Required Tests (from guidance + regulation)

| Category | Standard | Test Method | Acceptance Criteria | Priority | Risk Level |
|----------|----------|-------------|---------------------|----------|-----------|
| Biocompatibility | ISO 10993-1 | Risk-based evaluation | Per ISO 10993 endpoints | Required | High |
| Biocompatibility | ISO 10993-5 | Cytotoxicity (MEM elution) | Grade 0-1 reactivity | Required | High |
| Biocompatibility | ISO 10993-10 | Sensitization (GPMT/LLNA) | No sensitization | Required | High |
| Biocompatibility | ISO 10993-23 | Irritation (in vitro/in vivo) | No irritation | Required | High |
| Sterilization | ISO 11135 or 11137 | EO/Gamma validation | SAL 10^-6 | Required (if sterile) | High |
| Shelf Life | ASTM F1980 | Accelerated aging | Package integrity at EOL | Required (if expiration) | Medium |
| Performance | Device-specific | Per guidance | Per guidance criteria | Required | High |

### Tests Based on Predicate Precedent

| Category | Predicate Used | Count | Standard | Notes |
|----------|---------------|-------|----------|-------|
| {test} | {K-numbers} | {N/total} predicates | {standard} | {precedent notes} |

### Gap Analysis: Tests Guidance Requires But Predicates Didn't Document

| Test Category | Guidance Requirement | Predicate Evidence | Risk | Recommendation |
|---------------|---------------------|-------------------|------|----------------|
| {category} | {requirement} | {evidence} | {risk level} | {recommendation} |

### IFU Claim-to-Test Mapping (if --intended-use provided)

| IFU Claim | Supporting Test | Standard | Status |
|-----------|----------------|----------|--------|
| {claim element} | {test needed} | {standard} | {PLAN/NEEDED/OPTIONAL} |

## Step 3: Risk Prioritization

Prioritize tests using ISO 14971 risk categories:

- **Critical (must complete before submission)**: Tests where failure = safety issue
- **Major (strongly recommended)**: Tests guidance explicitly requires
- **Standard (recommended)**: Tests most predicates performed
- **Informational (consider)**: Tests some predicates performed

## Step 4: Generate Test Plan

Write the complete test plan:

```markdown
# 510(k) Testing Plan
## {Device Description} — Product Code {CODE}

**Generated:** {date}
**Risk Framework:** ISO 14971
**Project:** {project_name or "N/A"}

---

## Testing Summary

| Priority | Category | Count | Status |
|----------|----------|-------|--------|
| Critical | Safety-critical tests | {N} | {PLAN} |
| Major | Guidance-required tests | {N} | {PLAN} |
| Standard | Predicate-precedent tests | {N} | {PLAN} |
| Informational | Optional/supplementary | {N} | {CONSIDER} |

---

## Detailed Test Matrix

{Full table with all test items, grouped by priority}

---

## Gap Analysis

{Tests guidance requires but predicates didn't document}

---

## IFU Claim Mapping

{If --intended-use provided}

---

## Estimated Testing Timeline

| Phase | Tests | Estimated Duration | Dependencies |
|-------|-------|-------------------|-------------|
| Phase 1: Biocompatibility | ISO 10993-5, -10 | 8-12 weeks | Material selection |
| Phase 2: Performance | Device-specific | 4-8 weeks | Prototype |
| Phase 3: Sterilization | ISO 11135 | 6-10 weeks | Final packaging |
| Phase 4: Shelf Life | ASTM F1980 | 2-4 weeks (accelerated) | Final packaging |
| Phase 5: Clinical (if needed) | Study design | Variable | IRB approval |

---

## Standards Referenced

{Complete list of applicable standards with full titles}

---

> **Disclaimer:** This test plan is AI-generated from public FDA data.
> Verify independently. Not regulatory advice.
```

## Step 5: Write Output

Write test plan to file if `--output` or `--project` specified.

Default path: `$PROJECTS_DIR/$PROJECT_NAME/test_plan.md`

## Error Handling

- **No product code**: Use --infer or ask user
- **No guidance cache**: Generate baseline test plan from classification data + common testing requirements
- **No predicate data**: Generate guidance-only test plan, note predicate comparison unavailable
