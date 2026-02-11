---
name: fda-510k-submission-outline
description: Build 510(k) submission outlines, RTA readiness checklists, and evidence plans for device clearance. Use when structuring a 510(k), mapping evidence to sections, or identifying gaps in testing, clinical, human factors, cybersecurity, and labeling.
---

# FDA 510(k) Submission Outline

## Overview

Create a section-by-section 510(k) outline aligned to RTA and CDRH expectations, with required evidence and gap flags.

## Workflow

1. Confirm device scope.
Capture intended use, indications, product code/class, technology overview, and predicate strategy.

2. Select the submission structure.
Use `references/submission-structure.md` and `references/estar-structure.md` for required sections.
Check `references/cdrh-review-structure.md` to align with review expectations.

3. Map evidence to sections.
Identify required test reports, clinical data, HF/UE data, cybersecurity, and risk management.
Use `references/test-plan-framework.md`, `references/clinical-data-framework.md`, `references/clinical-study-framework.md`, and `references/human-factors-framework.md`.

4. Apply special controls and standards.
Use `references/special-controls.md`, `references/standards-tracking.md`, and `references/standards-database.md`.

5. Run RTA readiness check.
Use `references/rta-checklist.md` and `references/section-patterns.md` to highlight missing items.

6. Output a structured outline with gaps.
Use the template below and flag evidence gaps explicitly.

## Output Template

Use this structure verbatim unless the user requests otherwise.

```
510(k) Submission Outline

Device Overview
- Intended use:
- Indications for use:
- Product code / class:
- Predicate strategy:

Section-by-Section Outline
1. Administrative
   - Content:
   - Evidence / artifacts:
   - Gaps:
2. Device Description
   - Content:
   - Evidence / artifacts:
   - Gaps:
3. Substantial Equivalence
   - Content:
   - Evidence / artifacts:
   - Gaps:
4. Labeling
   - Content:
   - Evidence / artifacts:
   - Gaps:
5. Performance Testing
   - Content:
   - Evidence / artifacts:
   - Gaps:
6. Clinical / Human Factors (if applicable)
   - Content:
   - Evidence / artifacts:
   - Gaps:
7. Risk Management / Cybersecurity (if applicable)
   - Content:
   - Evidence / artifacts:
   - Gaps:

RTA Readiness Flags
- 

Recommended Next Steps
- 
```

## References

Load only what is needed:
- `references/submission-structure.md`, `references/estar-structure.md`, `references/cdrh-review-structure.md` for structure.
- `references/rta-checklist.md` and `references/section-patterns.md` for readiness checks.
- `references/test-plan-framework.md`, `references/clinical-data-framework.md`, `references/clinical-study-framework.md`, `references/human-factors-framework.md` for evidence mapping.
- `references/cybersecurity-framework.md` and `references/risk-management-framework.md` for risk sections.
- `references/special-controls.md`, `references/standards-tracking.md`, `references/standards-database.md` for controls/standards.
- `references/udi-requirements.md` for labeling/UDI expectations.
- `references/pccp-guidance.md` if device is AI/ML-enabled.

## Guardrails

- Do not promise clearance outcomes; focus on completeness and evidence readiness.
- If product code or predicate strategy is missing, request it before finalizing.
