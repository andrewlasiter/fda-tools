---
name: fda-de-novo-support
description: Support De Novo classification requests including submission outline generation, special controls proposals, risk assessment, benefit-risk analysis, pathway decision trees, and predicate search documentation. Use for novel devices without predicates that are low-to-moderate risk.
---

# FDA De Novo Classification Request Support

## Overview

Assists with De Novo classification requests per 21 CFR 860.260 and Section 513(f)(2) of the FD&C Act. The De Novo pathway is for novel, low-to-moderate risk devices that have no legally marketed predicate device but do not require PMA-level evidence.

## When to Use

- Device has no suitable predicate for 510(k) substantial equivalence
- Device is low-to-moderate risk (not requiring PMA-level clinical evidence)
- User needs to determine whether De Novo or 510(k) is more appropriate
- User needs to develop a special controls proposal
- User needs a comprehensive risk assessment for a novel device
- User needs to document a thorough predicate search
- User needs a benefit-risk analysis for the De Novo submission

## Workflow

1. **Pathway Decision**
   Use the PathwayDecisionTree to evaluate whether De Novo or 510(k) is more appropriate.
   Key factors: predicate availability, novel technology, intended use similarity, risk level.

2. **Predicate Search Documentation**
   Document thorough predicate search across FDA databases.
   Evaluate and reject candidates with documented rationale.
   This is CRITICAL - FDA expects comprehensive predicate search documentation.

3. **Submission Outline Generation**
   Generate a structured De Novo outline per 21 CFR 860.260.
   All 16 possible sections with applicability assessment.
   Includes classification recommendation, user fee info, and timeline estimates.

4. **Risk Assessment**
   Use the DeNovoRiskAssessment framework (ISO 14971-aligned).
   Score risks by severity, probability, and detectability.
   Calculate Risk Priority Numbers (RPN) and classify risk levels.
   Map risks to proposed mitigations.

5. **Special Controls Proposal**
   Generate a special controls proposal template.
   Map each identified risk to a specific special control.
   Track risk-control traceability matrix.
   Categories: performance standards, postmarket surveillance, patient registries, labeling, premarket testing, design restrictions.

6. **Benefit-Risk Analysis**
   Structured benefit-risk analysis with scoring.
   Compare benefits (magnitude x probability) against risks (severity x probability).
   Support residual risk analysis after mitigations.
   Generate determination statement with confidence level.

## Key Regulatory References

- 21 CFR 860.260 (De Novo Classification Process)
- Section 513(f)(2) of the FD&C Act
- FDA Guidance: "De Novo Classification Process (Evaluation of Automatic Class III Designation)" (2021)
- FDA Guidance: "Acceptance Review for De Novo Classification Requests" (2023)
- Section 513(a)(1)(B) of the FD&C Act (Special Controls)
- ISO 14971 (Risk Management)

## Key Differences from 510(k)

- No predicate device comparison (no substantial equivalence)
- Must propose special controls instead of comparing to predicate
- Classification recommendation is part of the submission
- Creates a new device classification upon granting
- Granted De Novo becomes predicate for future 510(k) submissions
- User fee is higher ($130,682 FY2025 vs $22,604 for 510(k))
- Review timeline is longer (150 days vs 90 days)

## Common Pitfalls

- Insufficient predicate search documentation
- Special controls that are too vague or unenforceable
- Risk assessment that misses key hazards
- Proposed classification not justified
- Benefit-risk analysis not sufficiently structured
- Intended use too broad for available evidence

## Important Notes

- Pre-Submission meeting with FDA is STRONGLY recommended
- FDA review goal is 150 review days (MDUFA performance goal)
- Refuse-to-Accept review is 15 business days
- Small businesses may qualify for fee waivers
- This tool is for RESEARCH USE ONLY - professional review required

## Library Module

Core implementation: `lib/de_novo_support.py`

Key classes:
- `DeNovoSubmissionOutline` - Submission outline generator
- `SpecialControlsProposal` - Special controls template
- `DeNovoRiskAssessment` - ISO 14971-aligned risk assessment
- `BenefitRiskAnalysis` - Structured benefit-risk tool
- `PathwayDecisionTree` - De Novo vs 510(k) decision logic
- `PredicateSearchDocumentation` - Search documentation generator
