---
description: Generate regulatory prose drafts for 510(k) submission sections — device description, SE discussion, performance summary, testing rationale, predicate justification
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch, WebSearch
argument-hint: "<section> --project NAME [--device-description TEXT] [--intended-use TEXT] [--output FILE]"
---

# FDA 510(k) Section Draft Generator

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

You are generating regulatory prose drafts for specific sections of a 510(k) submission. Unlike outline/template commands, this produces actual submission-quality text with citations.

**KEY PRINCIPLE: Every claim must cite its source.** Use project data (review.json, guidance_cache, se_comparison.md) to substantiate every assertion. Mark unverified claims as `[CITATION NEEDED]`.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Section name** (required) — One of: `device-description`, `se-discussion`, `performance-summary`, `testing-rationale`, `predicate-justification`, `510k-summary`
- `--project NAME` (required) — Project with pipeline data
- `--device-description TEXT` — Description of the user's device
- `--intended-use TEXT` — Proposed indications for use
- `--product-code CODE` — Product code (auto-detect from project if not specified)
- `--output FILE` — Write draft to file (default: draft_{section}.md in project folder)
- `--infer` — Auto-detect product code from project data

## Available Sections

### 1. device-description

Generates Section 6 of the eSTAR: Device Description.

**Required data**: `--device-description` or device info from query.json
**Enriched by**: openFDA classification, guidance_cache

**Output structure**:
```markdown
## Device Description

### 6.1 Device Overview
{Synthesized from --device-description, enriched with classification data}

### 6.2 Principle of Operation
{Inferred from device description and product code classification}

### 6.3 Components and Materials
[TODO: Company-specific — provide detailed component list and materials of construction]

### 6.4 Accessories and Packaging
[TODO: Company-specific — list accessories, packaging components, and sterilization barrier]

### 6.5 Illustrations
[TODO: Company-specific — attach device photographs, diagrams, and schematics]
```

### 2. se-discussion

Generates Section 7 narrative: Substantial Equivalence Discussion.

**Required data**: review.json (accepted predicates), se_comparison.md
**Enriched by**: predicate PDF text, openFDA data

**Output structure**:
```markdown
## Substantial Equivalence Discussion

### 7.1 Predicate Device Selection
The subject device is compared to {predicate K-number(s)} as the primary predicate device(s).
{Predicate K-number} was selected because: {rationale from review.json}.
[Source: review.json, confidence score: {score}/100]

### 7.2 Intended Use Comparison
The subject device and predicate share the same intended use: {IFU text}.
[Source: openFDA 510k API, predicate IFU from PDF text]

### 7.3 Technological Characteristics Comparison
{For each row in se_comparison.md where Comparison != "Same":}
The subject device differs from the predicate in {characteristic}:
- Subject: {value}
- Predicate: {value}
This difference does not raise new questions of safety or effectiveness because {justification}.
[Source: se_comparison.md]

### 7.4 Conclusion
Based on the comparison above, the subject device is substantially equivalent to {predicate(s)}
as defined under Section 513(i)(1)(A) of the Federal Food, Drug, and Cosmetic Act.
```

### 3. performance-summary

Generates performance testing summary from test-plan and guidance data.

**Required data**: test_plan.md or guidance_cache
**Enriched by**: predicate precedent from review.json

### 4. testing-rationale

Generates testing strategy rationale — why each test was selected.

**Required data**: guidance_cache, test_plan.md
**Enriched by**: predicate testing precedent

### 5. predicate-justification

Generates detailed predicate selection justification narrative.

**Required data**: review.json (accepted predicates with scores)
**Enriched by**: openFDA data, se_comparison.md, lineage.json

### 6. 510k-summary

Generates the full 510(k) Summary (per 21 CFR 807.92) — combines device description, IFU, SE discussion, and performance summary into a single document.

**Required data**: Multiple project files
**Enriched by**: All available pipeline data

## Generation Rules

1. **Regulatory tone**: Formal, factual, third-person. Use standard FDA regulatory language patterns.
2. **Citations required**: Every factual claim must reference its data source in `[Source: ...]` format.
3. **DRAFT disclaimer**: Every generated section starts with:
   ```
   ⚠ DRAFT — AI-generated regulatory prose. Review with regulatory affairs team before submission.
   Generated: {date} | Project: {name} | Plugin: fda-predicate-assistant v4.0.0
   ```
4. **Unverified claims**: Anything that cannot be substantiated from project data gets `[CITATION NEEDED]` or `[TODO: Company-specific — verify]`.
5. **No fabrication**: Never invent test results, clinical data, or device specifications. If data isn't available, say so.
6. **Standard references**: Use proper CFR/ISO/ASTM citation format (e.g., "per 21 CFR 807.87(f)", "ISO 10993-1:2018").

## Output

Write the draft to `$PROJECTS_DIR/$PROJECT_NAME/draft_{section}.md`.

Report:
```
Section draft generated: {section}
Output: {file_path}

Data sources used:
  {list of files and APIs consulted}

Completeness:
  Auto-populated: {N} paragraphs
  [TODO:] items: {N} (require company-specific data)
  [CITATION NEEDED]: {N} (need verification)

Next steps:
  1. Review draft for accuracy
  2. Fill in [TODO:] items with company-specific data
  3. Verify [CITATION NEEDED] items
  4. Have regulatory team review for compliance

> **Disclaimer:** This draft is AI-generated from public FDA data.
> Verify independently. Not regulatory advice.
```

## Error Handling

- **Unknown section name**: "Unknown section '{name}'. Available: device-description, se-discussion, performance-summary, testing-rationale, predicate-justification, 510k-summary"
- **No project data**: "Project '{name}' has no pipeline data. Run /fda:pipeline first to generate data for draft generation."
- **Insufficient data for section**: Generate what's possible, mark rest as [TODO]. Note which commands to run for more complete drafts.
