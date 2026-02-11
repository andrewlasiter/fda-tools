# Risk Management Framework (ISO 14971:2019)

## Overview

ISO 14971:2019 "Medical devices — Application of risk management to medical devices" defines the process for identifying hazards, estimating and evaluating risks, controlling risks, and monitoring the effectiveness of controls throughout the product lifecycle.

## Risk Management Process

### 1. Risk Analysis

#### Hazard Identification

Common hazard categories for medical devices:

| Category | Examples | Typical Severity |
|----------|----------|-----------------|
| Biological | Biocompatibility failure, infection, cytotoxicity | Serious-Critical |
| Mechanical | Device fracture, migration, fatigue failure | Moderate-Critical |
| Thermal | Burns, tissue damage from heat | Moderate-Serious |
| Electrical | Shock, electrocution, EMI interference | Serious-Critical |
| Radiation | Unintended exposure, dosimetry error | Moderate-Critical |
| Chemical | Leachables, extractables, residuals | Moderate-Serious |
| Software | Algorithm error, data corruption, display failure | Moderate-Critical |
| Use error | Misuse, misidentification, incorrect dosage | Moderate-Critical |
| Labeling | Unclear instructions, missing warnings | Low-Moderate |

#### Severity Classification (per ISO 14971 Annex H)

| Level | Description | Example |
|-------|-------------|---------|
| Negligible | Inconvenience or temporary discomfort | Minor skin irritation |
| Minor | Temporary injury or impairment not requiring intervention | Mild allergic reaction |
| Serious | Injury or impairment requiring professional intervention | Infection requiring antibiotics |
| Critical | Life-threatening injury or permanent impairment | Nerve damage, organ failure |
| Catastrophic | Death | Fatal hemorrhage |

#### Probability Classification

| Level | Qualitative | Quantitative (per device lifetime) |
|-------|------------|-----------------------------------|
| Improbable | Almost never occurs | < 10^-6 |
| Remote | Unlikely but possible | 10^-6 to 10^-4 |
| Occasional | Might occur several times | 10^-4 to 10^-2 |
| Probable | Expected to occur | 10^-2 to 10^-1 |
| Frequent | Very likely to occur | > 10^-1 |

### 2. Risk Evaluation

#### Risk Acceptability Matrix

| | Negligible | Minor | Serious | Critical | Catastrophic |
|---|-----------|-------|---------|----------|-------------|
| **Frequent** | ALARP | Unacceptable | Unacceptable | Unacceptable | Unacceptable |
| **Probable** | Acceptable | ALARP | Unacceptable | Unacceptable | Unacceptable |
| **Occasional** | Acceptable | ALARP | ALARP | Unacceptable | Unacceptable |
| **Remote** | Acceptable | Acceptable | ALARP | ALARP | Unacceptable |
| **Improbable** | Acceptable | Acceptable | Acceptable | ALARP | ALARP |

- **Acceptable**: Risk is acceptable without further action
- **ALARP**: As Low As Reasonably Practicable — risk controls required
- **Unacceptable**: Must reduce risk or demonstrate benefit outweighs risk

### 3. Risk Control Options (in priority order per ISO 14971)

1. **Inherently safe design** — Eliminate the hazard
2. **Protective measures** — Guards, alarms, interlocks
3. **Information for safety** — Warnings, labeling, training

### 4. Residual Risk Evaluation

After applying controls, re-evaluate to verify risk is acceptable.

## Device-Type Hazard Templates

### Implantable Orthopedic Devices (e.g., OVE — intervertebral body fusion)

| Hazard ID | Hazard | Cause | Severity | Probability | Risk Control |
|-----------|--------|-------|----------|-------------|-------------|
| HAZ-001 | Implant migration | Inadequate fixation, improper sizing | Critical | Remote | Design verification, sizing guide |
| HAZ-002 | Subsidence | Insufficient mechanical strength | Serious | Occasional | Compression testing per ASTM F2077 |
| HAZ-003 | Non-fusion | Poor bone ingrowth, motion | Serious | Occasional | Surface characterization, clinical follow-up |
| HAZ-004 | Biocompatibility failure | Toxic leachables | Serious | Remote | ISO 10993 testing battery |
| HAZ-005 | Corrosion | Material degradation in vivo | Serious | Remote | Corrosion testing per ASTM F2129 |
| HAZ-006 | Fatigue fracture | Cyclic loading | Critical | Remote | Fatigue testing per ASTM F2077 |
| HAZ-007 | Sterility failure | Process deviation | Critical | Improbable | Sterilization validation |
| HAZ-008 | MRI interaction | Ferromagnetic components | Critical | Occasional | MRI safety testing per ASTM F2052/F2213 |

### Software/SaMD Devices

| Hazard ID | Hazard | Cause | Severity | Probability | Risk Control |
|-----------|--------|-------|----------|-------------|-------------|
| HAZ-S01 | Incorrect output | Algorithm error | Critical | Remote | V&V per IEC 62304, clinical validation |
| HAZ-S02 | Data loss | Software crash, corruption | Serious | Remote | Fault tolerance, backup mechanisms |
| HAZ-S03 | Delayed result | System latency, failure | Serious | Remote | Performance monitoring, timeout handling |
| HAZ-S04 | Unauthorized access | Cybersecurity vulnerability | Serious | Occasional | Security controls per FDA cyber guidance |
| HAZ-S05 | Display error | UI rendering issue | Moderate | Remote | Usability testing, HFE validation |

### Wound Care / Topical Devices (e.g., KGN — wound dressing)

| Hazard ID | Hazard | Cause | Severity | Probability | Risk Control |
|-----------|--------|-------|----------|-------------|-------------|
| HAZ-W01 | Skin irritation | Material biocompatibility | Minor | Occasional | ISO 10993-5/-10 testing |
| HAZ-W02 | Infection | Inadequate barrier properties | Serious | Remote | Bacterial barrier testing |
| HAZ-W03 | Maceration | Excessive moisture retention | Minor | Occasional | MVTR testing |
| HAZ-W04 | Adhesive trauma | Excessive adhesion to wound | Moderate | Occasional | Peel testing, clinical evaluation |

## Integration with Plugin Commands

- `/fda:traceability` — Risk rows map HAZ-* → REQ-* → TEST-*
- `/fda:test-plan --risk-based` — Prioritize tests by hazard severity
- `/fda:draft` — Risk analysis referenced in device description and SE discussion
- `/fda:submission-outline --dhf` — Risk management is a key DHF element
