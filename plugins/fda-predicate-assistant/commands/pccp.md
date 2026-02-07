---
description: Generate a Predetermined Change Control Plan (PCCP) for AI/ML-enabled or iteratively modified medical devices per FDA guidance
allowed-tools: Bash, Read, Glob, Grep, Write, WebSearch
argument-hint: "<product-code> [--project NAME] [--device-description TEXT] [--modification-type algorithm|hardware|software|labeling]"
---

# FDA Predetermined Change Control Plan (PCCP) Generator

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

You are generating a Predetermined Change Control Plan (PCCP) per FDA's PCCP guidance for marketing authorization applications.

**KEY PRINCIPLE: PCCPs allow manufacturers to describe anticipated modifications and validation protocols BEFORE making changes, enabling faster iteration without new submissions.**

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Product code** (required) — 3-letter FDA product code
- `--project NAME` — Use existing project data
- `--device-description TEXT` — Current device description
- `--modification-type algorithm|hardware|software|labeling` — Type of anticipated changes
- `--output FILE` — Write PCCP to file
- `--infer` — Auto-detect product code

## Step 1: Determine PCCP Applicability

PCCPs are most relevant for:
- AI/ML-enabled devices (algorithm updates, retraining)
- Software devices (SaMD, firmware updates)
- Iteratively improved hardware (material changes, design refinements)
- Labeling modifications (expanded indications)

Query device classification and check if the device falls into applicable categories.

## Step 2: PCCP Framework

The PCCP has three required elements per FDA guidance:

### Element 1: Description of Planned Modifications

For each anticipated modification type:

**Algorithm/ML Modifications:**
- Retraining with new data (describe data types, sources, quality requirements)
- Algorithm architecture changes (describe allowed architecture modifications)
- Performance threshold updates (describe acceptable performance ranges)

**Software Modifications:**
- Feature additions (describe planned feature categories)
- UI/UX changes (describe user interaction modifications)
- Backend/infrastructure changes (describe system changes)

**Hardware Modifications:**
- Material substitutions (describe allowed material changes)
- Dimensional changes (describe allowed tolerance modifications)
- Manufacturing process changes (describe process modification categories)

**Labeling Modifications:**
- Indication expansions (describe planned indication broadening)
- Warning/precaution updates (describe safety labeling changes)
- IFU updates (describe instruction modifications)

### Element 2: Modification Protocol

For each modification category, define:
- Verification and validation approach
- Acceptance criteria
- Test methods and sample sizes
- Risk assessment updates required
- Documentation requirements

### Element 3: Impact Assessment

- How to evaluate if a modification stays within PCCP scope
- Decision tree for determining if a new submission is needed
- Monitoring and feedback mechanisms

## Step 3: Generate PCCP Document

Generate the PCCP document (see `references/output-formatting.md` for formatting standards):

```markdown
# Predetermined Change Control Plan (PCCP)
## {Device Description} — Product Code {CODE}

**Date:** {today}
**Generated:** {today} | v4.6.0
**Device Class:** {class}
**Marketing Authorization:** {K-number or pending}
**PCCP Version:** 1.0

---

## 1. Device Overview

{Device description and current authorized configuration}

## 2. Scope of PCCP

This PCCP covers the following categories of anticipated modifications:

{Based on --modification-type:}

### 2.1 Modification Categories

| Category | Description | Risk Impact | Validation Approach |
|----------|-------------|-------------|---------------------|
| {type} | {description} | {low/medium/high} | {approach} |

## 3. Description of Planned Modifications

### 3.1 {Modification Type} Modifications

**Allowed modifications:**
{detailed description of what changes are anticipated}

**Boundaries (modifications NOT covered by this PCCP):**
{what would require a new submission}

## 4. Modification Protocol

### 4.1 Verification and Validation

| Test | Method | Acceptance Criteria | Frequency |
|------|--------|---------------------|-----------|
| {test} | {method} | {criteria} | {per change / periodic} |

### 4.2 Risk Assessment

Per ISO 14971, each modification must be assessed for:
- New hazards introduced
- Changes to existing hazard severity/probability
- Impact on risk-benefit profile

### 4.3 Documentation Requirements

For each modification implemented under this PCCP:
- [ ] Modification description and rationale
- [ ] Updated risk analysis
- [ ] V&V test results
- [ ] Comparison to acceptance criteria
- [ ] Impact assessment conclusion
- [ ] Approval signatures

## 5. Performance Monitoring

### 5.1 Real-World Monitoring

{Performance monitoring plan for detecting issues post-modification}

### 5.2 Triggers for PCCP Re-evaluation

- Adverse event rate exceeding baseline by > {threshold}
- Customer complaint trend change
- Technology change exceeding PCCP boundaries
- Regulatory landscape change

## 6. Reporting to FDA

{Annual report requirements, if applicable}

---

> **Disclaimer:** This PCCP is AI-generated from public FDA data.
> Verify independently. Not regulatory advice.
```

## Example Output: CADe SaMD for Diabetic Retinopathy Screening

Below is an example of populated PCCP tables for a Computer-Aided Detection (CADe) SaMD:

**Modification Table Example:**

| Category | Description | Risk Impact | Validation Approach |
|----------|-------------|-------------|---------------------|
| Algorithm retraining | Retraining with expanded dataset (new imaging devices, demographics) | Medium | Performance on locked test set must meet or exceed baseline |
| Architecture update | Replace CNN backbone (e.g., ResNet-50 → EfficientNet-B4) | Medium | Full analytical validation + clinical validation subset |
| Threshold adjustment | Adjust sensitivity/specificity operating point within defined range | Low | Performance on locked test set, clinical impact analysis |
| Input expansion | Add support for new fundus camera models | Low | Cross-device equivalence testing on paired images |

**V&V Table Example:**

| Test | Method | Acceptance Criteria | Frequency |
|------|--------|---------------------|-----------|
| Analytical accuracy | Locked test set (N=1000, demographically balanced) | Sensitivity ≥ 87%, Specificity ≥ 90% | Per algorithm change |
| Clinical validation | Retrospective reader study (3 ophthalmologists, N=500) | AUC ≥ 0.95 | Per major architecture change |
| Bias assessment | Stratified performance by age, sex, ethnicity, camera model | No subgroup sensitivity < 80% | Per retraining |
| Regression testing | Prior version test cases pass at equal or better rate | ≤ 2% regression on any metric | Per any change |

**Boundary Definition Example:**

Changes WITHIN this PCCP scope:
- Retraining on fundus images from FDA-cleared camera models
- Architecture modifications that maintain input/output format
- Sensitivity threshold adjustment within 85-95% range

Changes OUTSIDE this PCCP scope (require new submission):
- Adding new imaging modalities (e.g., OCT)
- Expanding to new disease detection (beyond diabetic retinopathy)
- Changing from screening aid to autonomous diagnosis
- Performance below minimum acceptance criteria on any metric

## Step 4: Write Output

Default path: `$PROJECTS_DIR/$PROJECT_NAME/pccp_plan.md`

## Error Handling

- **Not an AI/ML device**: Note that PCCPs are most relevant for AI/ML devices but can apply to any iteratively modified device
- **Class III**: Note that PCCP for PMA devices has different requirements
