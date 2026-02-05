---
description: Generate a 510(k) submission outline with section checklists, testing gap analysis, and IFU-to-testing mapping
allowed-tools: Bash, Read, Glob, Grep, Write, WebSearch
argument-hint: "<product-code> [--project NAME] [--pathway traditional|special|abbreviated|denovo]"
---

# FDA 510(k) Submission Outline Generator

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

If `$FDA_PLUGIN_ROOT` is empty, report an error: "Could not locate the FDA Predicate Assistant plugin installation. Make sure the plugin is installed and enabled."

---

You are generating a comprehensive 510(k) submission outline with section checklists, gap analysis, and IFU-to-testing mapping.

**KEY PRINCIPLE: Use all available data to pre-populate the outline.** If review data, guidance cache, or extraction data exists, incorporate it. If not, generate a useful template. The outline should be a practical roadmap for the submission.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Product code** (required) — 3-letter FDA product code
- `--project NAME` — Use data from a specific project folder
- `--pathway traditional|special|abbreviated|denovo` — Submission pathway (auto-recommend if not specified)
- `--device-description TEXT` — Description of the user's device
- `--intended-use TEXT` — Proposed indications for use
- `--output FILE` — Write outline to file (default: submission_outline.md in project folder)

If no product code provided, ask the user for it.

## Step 1: Gather Data and Determine Pathway

### Get classification

Same openFDA classification query pattern as other commands.

### Load project data if available

```bash
python3 << 'PYEOF'
import json, os, re, glob

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m:
            projects_dir = os.path.expanduser(m.group(1).strip())

project_name = "PROJECT_NAME"  # Replace
project_dir = os.path.join(projects_dir, project_name)

# Check for each data source
data_sources = {}

# Review data (Phase 1)
review_path = os.path.join(project_dir, 'review.json')
if os.path.exists(review_path):
    with open(review_path) as f:
        review = json.load(f)
    accepted = {k: v for k, v in review.get('predicates', {}).items() if v.get('decision') == 'accepted'}
    print(f"REVIEW:found|accepted={len(accepted)}")
    for kn, info in sorted(accepted.items(), key=lambda x: -x[1].get('confidence_score', 0))[:5]:
        print(f"PREDICATE:{kn}|{info.get('device_info', {}).get('device_name', '?')}|{info.get('confidence_score', '?')}")
else:
    print("REVIEW:not_found")

# Guidance cache (Phase 2)
guidance_index = os.path.join(project_dir, 'guidance_cache', 'guidance_index.json')
if os.path.exists(guidance_index):
    with open(guidance_index) as f:
        guidance = json.load(f)
    print(f"GUIDANCE:found|device_specific={len(guidance.get('device_specific_guidance', []))}|cross_cutting={len(guidance.get('cross_cutting_guidance', []))}")
    for s in guidance.get('standards', []):
        print(f"STANDARD:{s.get('standard', '?')}|{s.get('purpose', '?')}|{'required' if s.get('required') else 'recommended'}")
else:
    # Check global cache
    for idx_path in glob.glob(os.path.join(projects_dir, '*/guidance_cache/guidance_index.json')):
        try:
            with open(idx_path) as f:
                g = json.load(f)
            if g.get('product_code') == "PRODUCTCODE":  # Replace
                print(f"GUIDANCE:found_global|path={idx_path}")
                break
        except:
            continue
    else:
        print("GUIDANCE:not_found")

# Extraction data
output_csv = os.path.join(project_dir, 'output.csv')
if os.path.exists(output_csv):
    import csv
    with open(output_csv, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    print(f"EXTRACTION:found|rows={len(rows)-1}")
else:
    print("EXTRACTION:not_found")

# Pre-Sub plan
presub_path = os.path.join(project_dir, 'presub_plan.md')
if os.path.exists(presub_path):
    print("PRESUB:found")
else:
    print("PRESUB:not_found")
PYEOF
```

### Recommend Pathway

If `--pathway` not specified, recommend based on available data:

Per the decision logic in `references/submission-structure.md`:

```
1. No predicate candidates → Recommend De Novo
2. Modifying own previously cleared device → Recommend Special 510(k)
3. Strong FDA guidance coverage for device type → Consider Abbreviated 510(k)
4. Default → Traditional 510(k)
```

Present the recommendation with rationale:

```
Recommended Pathway: Traditional 510(k)

Rationale:
  • Predicate device(s) available: {K-numbers}
  • No indication this is a modification of your own device
  • Standard predicate comparison approach is most appropriate

Alternative pathways considered:
  • Abbreviated: Possible if submission relies primarily on {guidance/standard}, but Traditional is more flexible
  • De Novo: Not applicable — valid predicates exist
  • Special: Not applicable — not a modification of your own device
```

## Step 2: Generate Section Outline

Use the ToC structure from `references/submission-structure.md` for the selected pathway.

### Section Applicability Determination

Not all sections apply to every device. Determine applicability:

```python
# Determine which sections apply based on device characteristics
sections = {
    "Cover Letter": True,  # Always
    "Cover Sheet (FDA Form 3514)": True,  # Always
    "510(k) Summary or Statement": True,  # Always
    "Truthful and Accuracy Statement": True,  # Always
    "Financial Certification": True,  # Always (if clinical data)
    "Device Description": True,  # Always
    "Substantial Equivalence Comparison": True,  # Always (510(k))
    "Standards and Guidance": True,  # Always
    "Proposed Labeling": True,  # Always
    "Sterilization": False,  # If sterile
    "Shelf Life": False,  # If has expiration
    "Biocompatibility": True,  # Almost always (patient contact)
    "Software": False,  # If contains software
    "EMC / Electrical Safety": False,  # If powered
    "Performance Testing": True,  # Almost always
    "Clinical Testing": False,  # If needed
    "Human Factors": False,  # If use-related risks
}

desc = (device_description or "").lower()

if any(kw in desc for kw in ["sterile", "steriliz"]):
    sections["Sterilization"] = True
    sections["Shelf Life"] = True

if any(kw in desc for kw in ["software", "algorithm", "app", "firmware", "samd"]):
    sections["Software"] = True

if any(kw in desc for kw in ["powered", "electric", "battery", "wireless", "bluetooth"]):
    sections["EMC / Electrical Safety"] = True

if any(kw in desc for kw in ["wireless", "connected", "bluetooth", "wifi"]):
    sections["Software"] = True  # Cybersecurity required
```

## Step 3: Generate Gap Analysis Table

This is the key deliverable — mapping guidance requirements against predicate precedent.

### If both guidance cache AND review/extraction data available

Build a complete gap analysis table:

```markdown
## Gap Analysis: Guidance Requirements vs. Predicate Evidence

| Test Category | Guidance Requires | Predicate Did | Status | Notes |
|---------------|-------------------|---------------|--------|-------|
| ISO 10993-5 (Cytotoxicity) | Required (cross-cutting) | Yes (3/3) | NEEDED | All predicates included |
| ISO 10993-10 (Sensitization) | Required (cross-cutting) | Yes (3/3) | NEEDED | All predicates included |
| ISO 11135 (EO Sterilization) | Required (if sterile) | Yes (2/3) | NEEDED | 2 predicates used EO |
| ASTM F1980 (Accelerated Aging) | Recommended | Yes (1/3) | PLAN | Only 1 predicate included — plan carefully |
| EN 13726 (Dressing Performance) | Per special controls | Yes (2/3) | NEEDED | Standard for this product code |
| AATCC 100 (Antimicrobial) | If claimed | No (0/3) | CONSIDER | None included — only if you claim antimicrobial |
| IEC 62304 (Software) | If applicable | N/A | N/A | No software in this device |
| Clinical Data | Not typically required | Yes (1/3) | RECOMMENDED | 1 predicate included lit review |
```

### If only guidance cache available (no predicate data)

```markdown
## Requirements Checklist (from Guidance Analysis)

| Test Category | Guidance Requires | Standard | Status |
|---------------|-------------------|----------|--------|
| Biocompatibility | Required | ISO 10993-1, -5, -10 | NEEDED |
| Sterilization | Required (if sterile) | ISO 11135 or 11137 | NEEDED |
| Shelf Life | Required (if expiration) | ASTM F1980 | NEEDED |
| Performance | Required | Device-specific | NEEDED |
| [Others from guidance] | ... | ... | ... |

Note: Predicate testing data not available. Run `/fda:extract` and `/fda:review` for predicate-vs-guidance comparison.
```

### If only predicate data available (no guidance cache)

```markdown
## Predicate Testing Precedent

| Test Category | Predicate Evidence | Status |
|---------------|-------------------|--------|
| Biocompatibility | 3/3 predicates included | NEEDED |
| Sterilization | 2/3 predicates included | NEEDED |
| Performance | 3/3 predicates included | NEEDED |
| Clinical | 1/3 predicates included | RECOMMENDED |

Note: FDA guidance data not cached. Run `/fda:guidance {CODE} --save` for complete requirements analysis.
```

## Step 4: IFU Claim-to-Testing Mapping

If `--intended-use` is provided, parse the IFU text and map each claim to supporting tests:

```markdown
## IFU Claim-to-Testing Mapping

Proposed IFU: "{intended_use_text}"

| Claim Element | Supporting Test | Standard | Status |
|---------------|----------------|----------|--------|
| "management of partial thickness wounds" | Fluid handling, absorption | EN 13726 | PLAN |
| "full thickness wounds" | Clinical evidence or lit review | — | PLAN |
| "pressure ulcers" | Clinical evidence for indication | — | CONSIDER |
| "antimicrobial protection" | Zone of inhibition, MIC/MBC | AATCC 100 | NEEDED |
| "up to 7 days wear time" | Accelerated aging, adhesion | ASTM F1980 | PLAN |
```

If no `--intended-use` provided, include a template:

```
IFU Claim-to-Testing Mapping:
[INSERT your proposed IFU text to generate claim-to-testing mapping]
Tip: Provide --intended-use "your IFU text" to auto-generate this table.
```

## Step 5: Generate Full Outline

Write the complete submission outline document:

```markdown
# 510(k) Submission Outline
## {Device Description} — Product Code {CODE}

**Pathway:** {Traditional/Special/Abbreviated/De Novo}
**Product Code:** {CODE} — {device_name}
**Classification:** Class {class}, 21 CFR {regulation}
**Generated:** {today's date}
**Project:** {project_name or "N/A"}

---

## Submission Readiness Summary

| Section | Applicable | Data Available | Status |
|---------|-----------|----------------|--------|
| Cover Letter | Yes | Template ready | ✓ |
| Device Description | Yes | {auto/template} | {✓/○} |
| SE Comparison | Yes | {predicates identified / pending} | {✓/○} |
| Labeling (IFU) | Yes | {provided / needed} | {✓/○} |
| Biocompatibility | Yes | {testing plan / needed} | {✓/○} |
| Sterilization | {Yes/No} | {if yes: plan status} | {✓/○/—} |
| Shelf Life | {Yes/No} | {if yes: plan status} | {✓/○/—} |
| Software | {Yes/No} | {if yes: plan status} | {✓/○/—} |
| EMC/Electrical | {Yes/No} | {if yes: plan status} | {✓/○/—} |
| Performance Testing | Yes | {plan status} | {✓/○} |
| Clinical | {Yes/Likely/No} | {if yes: plan status} | {✓/○/—} |
| Human Factors | {Yes/No} | {if yes: plan status} | {✓/○/—} |

Legend: ✓ = Ready/Planned  ○ = Needs attention  — = Not applicable

---

## Table of Contents

{Full ToC from references/submission-structure.md for the selected pathway}
{For each section, include:}

### {Section Number}. {Section Name}
**Applicable:** {Yes/No}
**Status:** {Ready/Needs Data/Template}

**Required content:**
{Checklist from references/submission-structure.md section requirements}

- [ ] {Required item 1}
- [ ] {Required item 2}
- [ ] {Required item 3}

{If project data available for this section:}
**Available data:**
- {Data source}: {description}

{If testing gaps apply to this section:}
**Gap analysis:**
- {Gap item with status}

---

## Gap Analysis

{Full gap analysis table from Step 3}

---

## IFU Claim-to-Testing Mapping

{Mapping from Step 4}

---

## Predicate Strategy

{If review data available:}
**Accepted Predicates:**
| # | K-Number | Device Name | Score | Key Strength |
|---|----------|-------------|-------|-------------|
{Top accepted predicates with scores}

**SE Comparison Table:** {If compare-se was run: "Available at {path}" / "Not yet generated — run `/fda:compare-se --predicates {K-numbers}`"}

{If no review data:}
[Predicate selection pending — run `/fda:research {CODE}` then `/fda:review --project {NAME}`]

---

## Applicable Standards

{Standards list from guidance cache or default for device type}

---

## Estimated Submission Complexity

Based on available data:
- **Sections requiring new testing:** {count}
- **Sections with predicate precedent:** {count}
- **Open gaps (PLAN status):** {count}
- **FDA Pre-Sub recommended:** {Yes/No — based on gap count and novel features}

---

## Recommended Next Steps

{Ordered list based on what's missing:}

{If no extraction:} 1. Run `/fda:extract both --project {NAME}` to download and extract predicate data
{If no review:} 2. Run `/fda:review --project {NAME}` to validate predicates
{If no guidance:} 3. Run `/fda:guidance {CODE} --save --project {NAME}` to cache guidance requirements
{If no presub and gaps exist:} 4. Run `/fda:presub {CODE} --project {NAME}` to plan Pre-Sub meeting
{If no SE table:} 5. Run `/fda:compare-se --predicates {K-numbers} --project {NAME}` to build SE comparison table
{Always:} 6. Begin testing per gap analysis priorities
{Always:} 7. Prepare eSTAR submission package

---

⚠ DISCLAIMER: This submission outline is AI-generated from publicly available
FDA data and guidance documents. It is a planning tool — not a regulatory
submission. Review with your regulatory affairs team. Verify all section
requirements against current FDA guidance. This is not regulatory advice.
```

## Step 6: Write Output

```bash
# Determine output path
if [ -n "$OUTPUT_FILE" ]; then
    OUTPUT_PATH="$OUTPUT_FILE"
elif [ -n "$PROJECT_NAME" ]; then
    OUTPUT_PATH="$PROJECTS_DIR/$PROJECT_NAME/submission_outline.md"
else
    OUTPUT_PATH="$HOME/fda-510k-data/submission_outline_${PRODUCT_CODE}.md"
fi
```

Write using the Write tool.

Report:
```
Submission outline written to: {output_path}

Outline Summary:
  Pathway: {pathway}
  Applicable sections: {count}/{total}
  Sections ready: {count}
  Sections needing data: {count}
  Testing gaps: {count}
  Standards to conform: {count}

{Next steps based on gaps}
```

## Error Handling

- **No product code**: Ask the user for it
- **Invalid pathway**: "'{pathway}' is not a valid pathway. Use traditional, special, abbreviated, or denovo."
- **No project data**: Generate template outline. Note: "Outline generated without project data. Run the full pipeline for a data-enriched outline."
- **API unavailable**: Use flat files. Note which sections have reduced data.
