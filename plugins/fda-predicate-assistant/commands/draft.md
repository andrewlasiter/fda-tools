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

You are generating regulatory prose drafts for specific sections of a 510(k) submission. Unlike outline/template commands, this produces first-draft regulatory prose that requires professional review, verification, and refinement before submission.

> **WARNING: LLM-generated prose carries confabulation risk.** Every factual claim, citation, and regulatory reference in the output must be independently verified by a qualified regulatory affairs professional before use in any submission. `[Source: ...]` tags reference internal plugin data files, not authoritative regulatory citations.

**KEY PRINCIPLE: Every claim must cite its source.** Use project data (review.json, guidance_cache, se_comparison.md) to substantiate every assertion. Mark unverified claims as `[CITATION NEEDED]`.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Section name** (required) — One of: `device-description`, `se-discussion`, `performance-summary`, `testing-rationale`, `predicate-justification`, `510k-summary`, `labeling`, `sterilization`, `shelf-life`, `biocompatibility`, `software`, `emc-electrical`, `clinical`, `cover-letter`, `truthful-accuracy`, `financial-certification`
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

### 7. labeling

Generates Section 9 of the eSTAR: Labeling (package label, IFU, patient labeling).

**Required data**: indications_for_use from import_data.json or `--intended-use`
**Enriched by**: openFDA classification, guidance_cache, predicate IFU

**Output structure**: See `references/draft-templates.md` Section 09. Includes:
- 9.1 Package Label template with UDI, Rx symbol, storage conditions
- 9.2 Instructions for Use with IFU text, contraindications, warnings, precautions, directions
- 9.3 Patient Labeling (if applicable)
- 9.4 Promotional Materials (if applicable)

### 8. sterilization

Generates Section 10 of the eSTAR: Sterilization.

**Required data**: sterilization_method from import_data.json or test_plan.md
**Enriched by**: guidance_cache sterilization requirements

**Output structure**: See `references/draft-templates.md` Section 10. Includes:
- 10.1 Sterilization Method (EO, radiation, steam, or N/A)
- 10.2 SAL target
- 10.3 Validation summary (auto-selects standard by method: ISO 11135/11137/17665)
- 10.4 EO residuals (if applicable, per ISO 10993-7)
- 10.5 Packaging validation (ISO 11607)

Auto-detect if sterilization is applicable from device description keywords: "sterile", "sterilized", "implant", "surgical", "invasive".

### 9. shelf-life

Generates Section 11 of the eSTAR: Shelf Life.

**Required data**: shelf_life_claim from import_data.json or test_plan.md
**Enriched by**: guidance_cache

**Output structure**: See `references/draft-templates.md` Section 11. Includes:
- 11.1 Claimed shelf life
- 11.2 Aging study design (accelerated per ASTM F1980 + real-time)
- 11.3 Testing protocol (package integrity, sterility, functionality)
- 11.4 Results summary

### 10. biocompatibility

Generates Section 12 of the eSTAR: Biocompatibility.

**Required data**: biocompat_contact_type, biocompat_materials from import_data.json or test_plan.md
**Enriched by**: guidance_cache, predicate materials from se_comparison.md

**Output structure**: See `references/draft-templates.md` Section 12. Includes:
- 12.1 Contact classification per ISO 10993-1:2025 (or ISO 10993-1:2018 during transition)
- 12.2 Biological evaluation plan with endpoint matrix
- 12.3 Testing summary
- 12.4 Predicate material equivalence justification (if applicable)

Auto-determine required endpoints based on contact type and duration.

### 11. software

Generates Section 13 of the eSTAR: Software/Cybersecurity.

**Required data**: software_doc_level from import_data.json or device description
**Enriched by**: guidance_cache, cybersecurity-framework.md

**Output structure**: See `references/draft-templates.md` Section 13. Includes:
- 13.1 Software classification (IEC 62304 Class A/B/C)
- 13.2 Software description
- 13.3 Software testing
- 13.4 Cybersecurity documentation (if Section 524B applies)

Auto-detect if cybersecurity applies from keywords: "wireless", "bluetooth", "wifi", "connected", "cloud", "network", "usb".

### 12. emc-electrical

Generates Section 14 of the eSTAR: EMC/Electrical Safety.

**Required data**: Device description indicating electrical/electronic device
**Enriched by**: guidance_cache, standards-tracking.md

**Output structure**: See `references/draft-templates.md` Section 14. Includes:
- 14.1 Applicable standards table (IEC 60601-1, 60601-1-2, particular standards)
- 14.2 EMC testing summary
- 14.3 Electrical safety testing summary
- 14.4 Declaration of Conformity

Auto-detect applicability from keywords: "powered", "electronic", "electrical", "battery", "AC/DC".

### 13. clinical

Generates Section 16 of the eSTAR: Clinical Evidence.

**Required data**: literature.md from `/fda:literature`, safety_report.md from `/fda:safety`
**Enriched by**: review.json (predicate clinical data precedent), guidance_cache

**Output structure**: See `references/draft-templates.md` Section 16. Includes:
- 16.1 Clinical evidence strategy (data/literature/exemption)
- 16.2 Clinical data summary with literature review
- 16.3 Adverse event analysis from MAUDE data
- 16.4 Clinical conclusion

Auto-determine strategy: if predicates had no clinical data, default to "no clinical data needed" with predicate precedent rationale.

### 14. cover-letter

Generates Section 1 of the eSTAR: Cover Letter.

**Required data**: applicant info from import_data.json, product code, predicate list
**Enriched by**: openFDA classification, review.json

**Output structure**: See `references/draft-templates.md` Section 01. Formal letter addressed to appropriate CDRH division.

### 15. truthful-accuracy

Generates Section 4 of the eSTAR: Truthful and Accuracy Statement.

**Required data**: applicant_name from import_data.json
**Output**: Standard certification text per 21 CFR 807.87(l). Minimal auto-population — mostly a template requiring authorized signature.

### 16. financial-certification

Generates Section 5 of the eSTAR: Financial Certification/Disclosure.

**Required data**: None (template-only)
**Output**: Template referencing FDA Forms 3454/3455 and 21 CFR Part 54. Indicates which form applies based on whether clinical data is submitted.

## Generation Rules

1. **Regulatory tone**: Formal, factual, third-person. Use standard FDA regulatory language patterns.
2. **Citations required**: Every factual claim must reference its data source in `[Source: ...]` format.
3. **DRAFT disclaimer**: Every generated section starts with:
   ```
   ⚠ DRAFT — AI-generated regulatory prose. Review with regulatory affairs team before submission.
   Generated: {date} | Project: {name} | Plugin: fda-predicate-assistant v4.6.0
   ```
4. **Unverified claims**: Anything that cannot be substantiated from project data gets `[CITATION NEEDED]` or `[TODO: Company-specific — verify]`.
5. **No fabrication**: Never invent test results, clinical data, or device specifications. If data isn't available, say so.
6. **Standard references**: Use proper CFR/ISO/ASTM citation format (e.g., "per 21 CFR 807.87(f)", "ISO 10993-1:2025").

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

- **Unknown section name**: "Unknown section '{name}'. Available: device-description, se-discussion, performance-summary, testing-rationale, predicate-justification, 510k-summary, labeling, sterilization, shelf-life, biocompatibility, software, emc-electrical, clinical, cover-letter, truthful-accuracy, financial-certification"
- **No project data**: "Project '{name}' has no pipeline data. Run /fda:pipeline first to generate data for draft generation."
- **Insufficient data for section**: Generate what's possible, mark rest as [TODO]. Note which commands to run for more complete drafts.
