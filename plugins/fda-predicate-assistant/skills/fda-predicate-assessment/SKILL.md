---
name: fda-predicate-assessment
description: Assess FDA 510(k) predicate strategy, substantial equivalence, and predicate validity. Use when selecting or comparing predicate devices, evaluating intended use/technological characteristics, building predicate lineages, or producing a predicate rationale with risk flags and confidence scoring.
---

# FDA Predicate Assessment

## Overview

Provide a repeatable workflow to select and justify predicate devices for a 510(k), with explicit risk flags, confidence scoring, and a structured rationale.

## Workflow

1. Confirm the device profile.
Collect intended use, indications for use, technology characteristics, key performance claims, product code (if known), and classification.
If product code or class is unknown, consult `references/device-classes.md` and `references/pathway-decision-tree.md`.

2. Identify candidate predicates.
Prioritize legally marketed devices with the same intended use and similar technology.
Use lineage patterns from `references/predicate-lineage.md` and guidance in `references/predicate-types.md`.

3. Test substantial equivalence.
Evaluate intended use and technological characteristics.
If technology differs, list the new questions of safety/effectiveness and required performance/clinical evidence.
Use `references/predicate-analysis-framework.md` for the decision logic.

4. Flag risk factors.
Call out split predicates, differences in tech, use of reference devices, data gaps, or weak literature support.
Use `references/common-issues.md` and `references/section-patterns.md` for common failure modes.

5. Score confidence.
Assign a confidence rating and explain why, using `references/confidence-scoring.md`.

6. Output a predicate rationale.
Use the output template below with clear, actionable next steps.

## Output Template

Use this structure verbatim unless the user requests otherwise.

```
Predicate Assessment

Device Summary
- Intended use:
- Indications for use:
- Key technology characteristics:
- Product code / class:

Candidate Predicates
- Predicate 1 (K-number / name):
  - Intended use match:
  - Technology match:
  - Differences and impact:
- Predicate 2 (if needed):
  - Intended use match:
  - Technology match:
  - Differences and impact:

Substantial Equivalence Analysis
- Same intended use? (Yes/No + rationale)
- Same technological characteristics? (Yes/No + rationale)
- If different: new questions of safety/effectiveness?
- Evidence needed to address differences:

Risk Flags
- [ ] Split predicate risk
- [ ] Technology divergence
- [ ] Clinical evidence gap
- [ ] Labeling/indications mismatch
- [ ] Weak predicate lineage

Confidence Score
- Rating (High/Medium/Low):
- Rationale:

Recommended Next Steps
- 
```

## References

Load only what is needed:
- `references/predicate-analysis-framework.md` for the SE decision logic.
- `references/predicate-types.md` for single/multiple/split predicate patterns.
- `references/predicate-lineage.md` to build or validate predicate chains.
- `references/confidence-scoring.md` for risk-weighted scoring.
- `references/device-classes.md` and `references/pathway-decision-tree.md` for classification context.
- `references/common-issues.md` and `references/section-patterns.md` for common FDA feedback patterns.
- `references/openfda-api.md` and `references/openfda-data-dictionary.md` if API lookups are required.
- `references/guidance-lookup.md` and `references/fda-guidance-index.md` for device-specific guidance discovery.

## Guardrails

- Do not claim legal advice; frame as regulatory support.
- Distinguish predicates vs reference devices explicitly.
- If the product code or intended use is unclear, request it before finalizing.
