---
name: fda-safety-signal-triage
description: Triage FDA safety signals for 510(k) devices, including recalls, MAUDE adverse events, complaint trends, and post-market requirements. Use when assessing safety risk, recall exposure, or building a risk/mitigation summary for a device or predicate set.
---

# FDA Safety Signal Triage

## Overview

Provide a structured workflow to identify and summarize safety signals for 510(k) devices, with clear risk flags and mitigation next steps.

## Workflow

1. Confirm the device scope.
Capture product code, regulation, intended use, known predicates, and timeframe for analysis.

2. Pull safety signal sources.
Review MAUDE events and recalls when available.
If using API lookups, follow `references/openfda-api.md` and `references/openfda-data-dictionary.md`.

3. Classify the signal.
Group signals by harm type, severity, and recurrence.
Use `references/complaint-handling-framework.md` and `references/post-market-requirements.md`.

4. Identify enforcement patterns.
Check for enforcement trends, warning themes, or required special controls.
Use `references/fda-enforcement-intelligence.md` and `references/common-issues.md`.

5. Assess risk controls.
Map signals to risk controls and documentation gaps.
Use `references/risk-management-framework.md` and `references/cybersecurity-framework.md` where applicable.

6. Produce a triage summary.
Use the output template below, with actions and open questions.

## Output Template

Use this structure verbatim unless the user requests otherwise.

```
Safety Signal Triage

Device Scope
- Product code / class:
- Intended use:
- Predicates or comparable devices:
- Timeframe reviewed:

Signal Summary
- Recalls:
- MAUDE event themes:
- Complaint trends:
- Other enforcement signals:

Risk Assessment
- Severity: (Low/Medium/High)
- Likelihood: (Low/Medium/High)
- Key drivers:

Mitigations / Controls
- Existing controls:
- Gaps / needed evidence:
- Documentation updates:

Recommended Next Steps
- 
```

## References

Load only what is needed:
- `references/openfda-api.md` and `references/openfda-data-dictionary.md` for data access.
- `references/complaint-handling-framework.md` and `references/post-market-requirements.md` for triage logic.
- `references/fda-enforcement-intelligence.md` and `references/common-issues.md` for enforcement patterns.
- `references/risk-management-framework.md` and `references/cybersecurity-framework.md` for control mapping.
- `references/audit-logging.md` if traceability expectations are in scope.

## Guardrails

- Distinguish observed signals from hypotheses.
- Avoid medical or legal advice; focus on regulatory risk framing.
- If device scope is unclear, request product code and intended use before rating risk.
