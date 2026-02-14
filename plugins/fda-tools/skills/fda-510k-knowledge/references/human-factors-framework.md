# Human Factors / Usability Engineering Framework

## Overview

FDA guidance "Applying Human Factors and Usability Engineering to Medical Devices" (2016) and IEC 62366-1:2015 define the process for ensuring safe and effective use of medical devices through human factors engineering (HFE).

## When HFE Is Required

### Applicability Decision Tree

1. **Does the device have a user interface?** (displays, controls, buttons, touchscreens)
   - No → HFE likely not required (document rationale)
   - Yes → Continue

2. **Are there critical tasks?** (tasks where use error could cause serious harm)
   - No → Minimal HFE documentation (use environment description only)
   - Yes → Full HFE required

3. **Is the user interface substantially different from predicate?**
   - No → Reference predicate HFE data with comparison
   - Yes → New HFE study required

### Common Triggers for Full HFE

- New or significantly modified user interface
- Home use devices (lay users)
- Life-sustaining/life-supporting devices
- Devices with history of use errors (MAUDE data)
- Combination products
- Software-driven clinical decision support
- Devices used by multiple user populations

### Auto-Detection Keywords

If device description contains these, HFE is likely applicable:
- "user interface", "display", "touchscreen", "control panel"
- "home use", "patient-operated", "self-administered"
- "injection", "infusion", "inhaler", "autoinjector"
- "alarm", "alert", "notification"
- "software", "app", "mobile", "connected"

## HFE Process (IEC 62366-1:2015)

### 1. Use Specification

| Element | Description |
|---------|-------------|
| Intended users | Healthcare professionals, patients, caregivers, technicians |
| Use environments | Hospital, clinic, home, ambulance, OR |
| User characteristics | Training level, physical abilities, experience |
| Medical conditions | Conditions that may affect device use |

### 2. Use-Related Risk Analysis

Identify use errors that could lead to harm:

| Use Error | Hazardous Situation | Severity | Root Cause |
|-----------|-------------------|----------|------------|
| Incorrect dose selection | Overdose/underdose | Critical | Ambiguous display |
| Missed alarm | Delayed intervention | Serious | Alarm fatigue |
| Wrong patient connection | Cross-contamination | Serious | Similar connectors |
| Misread display | Incorrect clinical decision | Serious | Poor contrast/size |

### 3. User Interface Design

Apply risk controls through design:
- **Inherently safe design**: Eliminate use error possibility
- **Protective measures**: Interlocks, confirmations, error prevention
- **Information for safety**: Labels, IFU, training

### 4. Formative Evaluation

| Study Type | Purpose | When |
|-----------|---------|------|
| Cognitive walkthrough | Expert review of UI | Early design |
| Heuristic evaluation | Usability principles check | Early-mid design |
| Simulated use study | Representative users, prototype | Mid design |

### 5. Summative (Validation) Evaluation

| Element | Requirement |
|---------|-------------|
| Participants | Minimum 15 per user group (FDA recommended) |
| Tasks | All critical tasks + representative non-critical tasks |
| Environment | Simulated actual use conditions |
| Metrics | Task success, use errors, close calls, difficulties |
| Acceptance criteria | No critical task failures, no use errors leading to harm |

## eSTAR Section 17: Human Factors

### Template Structure

```markdown
## Human Factors / Usability Engineering

### 17.1 Use Environment
[TODO: Company-specific — Describe the intended use environment(s):
- Clinical setting (hospital, clinic, physician office)
- Home environment (if applicable)
- Environmental conditions (lighting, noise, temperature)
- Other use environments]

### 17.2 User Profile
[TODO: Company-specific — Describe intended users:
- Healthcare professionals (type, training level)
- Patients/caregivers (if home use)
- Other users (biomedical technicians, etc.)
- Physical/cognitive requirements]

### 17.3 Critical Tasks
[TODO: Company-specific — List all critical tasks:
- Tasks where use error could cause serious harm
- Tasks requiring high accuracy or precision
- Tasks performed under stress or time pressure]

### 17.4 Use-Related Risk Analysis Summary
[TODO: Company-specific — Summarize use-related risk analysis:
- Identified use errors and hazardous situations
- Risk controls implemented (design, labeling, training)
- Residual risks and mitigations]

### 17.5 Formative Study Summary
[TODO: Company-specific — Summarize formative studies:
- Study type (cognitive walkthrough, heuristic evaluation, simulated use)
- Number of participants
- Key findings and design changes made]

### 17.6 Summative (Validation) Study Summary
[TODO: Company-specific — Summarize validation study:
- Study design and protocol
- Number of participants per user group
- Critical task results (success/failure)
- Use errors and close calls observed
- Conclusion: device can be used safely and effectively]
```

## Key FDA Guidance Documents

| Guidance | Year | Focus |
|----------|------|-------|
| Applying Human Factors and Usability Engineering to Medical Devices | 2016 | Comprehensive HFE guidance |
| Human Factors Considerations for Combination Products | 2016 | Combination products specific |
| Content of Human Factors Information in Medical Device Marketing Submissions | 2023 | What to include in submissions |
| Design Considerations for Devices Intended for Home Use | 2014 | Home use specific |

## Integration with Plugin Commands

- `/fda:draft human-factors` — Generate Section 17 HFE template
- `/fda:submission-outline` — HFE section applicability in outline
- `/fda:safety` — MAUDE data identifying use error patterns
- `/fda:test-plan` — HFE testing in comprehensive test plan
