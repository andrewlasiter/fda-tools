# PCCP Guidance Reference

## FDA PCCP Guidance Overview

**Title**: "Marketing Submission Recommendations for a Predetermined Change Control Plan for Artificial Intelligence/Machine Learning (AI/ML)-Enabled Device Software Functions"

**Status**: Final guidance (2023), updated with broader applicability (2025-2026)

## Key Concepts

### What is a PCCP?
A Predetermined Change Control Plan describes:
1. Specific planned modifications to a device
2. The methodology for implementing those modifications
3. How the modified device will be assessed

### When to Include a PCCP
- AI/ML devices with anticipated algorithm updates
- SaMD with planned feature additions
- Devices with iterative improvement cycles
- Any device where manufacturer anticipates changes post-clearance

### PCCP Elements

| Element | Description | FDA Expectation |
|---------|-------------|-----------------|
| Modification Description | What changes are planned | Specific, bounded categories |
| Modification Protocol | How changes will be validated | Detailed V&V approach |
| Impact Assessment | How to determine if change is within scope | Clear decision criteria |

### Modification Categories (from guidance)

1. **Performance/specification changes** — Updated thresholds, ranges, criteria
2. **Input changes** — New data sources, sensor types, input formats
3. **Architecture/algorithm changes** — Model updates, retraining, new algorithms
4. **Clinical use changes** — Expanded populations, new anatomical sites
5. **Labeling changes** — Updated IFU, warnings, precautions

### Boundaries
PCCPs must clearly define what changes are NOT covered:
- Changes to intended use/indications
- Changes to device classification
- Changes requiring new clinical data
- Changes exceeding defined performance boundaries

## Regulatory Citations

- **Statutory basis:** Section 515C of the FD&C Act (added by the Consolidated Appropriations Act, 2023)
- **Primary guidance:** "Marketing Submission Recommendations for a Predetermined Change Control Plan for Artificial Intelligence/Machine Learning (AI/ML)-Enabled Device Software Functions" (Docket FDA-2022-D-2628; 88 FR 19648)
- **Broader PCCP guidance:** "Predetermined Change Control Plans for Medical Devices" (Docket FDA-2023-D-3134, August 2024 draft)
- **Regulation:** Section 515C of FD&C Act — statutory basis for PCCPs in premarket submissions
- **Federal Register:** Published as final guidance; check fda.gov for current version

## Historical Context: SPS and ACP

The PCCP framework evolved from earlier concepts:
- **Software Pre-Specifications (SPS):** Originally proposed in FDA's 2021 action plan for AI/ML-based SaMD — described the types of anticipated modifications
- **Algorithm Change Protocol (ACP):** Proposed alongside SPS — described the method for implementing and validating changes
- **PCCP (final framework):** Consolidated SPS and ACP into a unified three-element structure. The term "PCCP" replaced "SPS/ACP" in the final guidance.

## FDA Review Acceptance Criteria

FDA evaluates PCCPs against these criteria:
1. **Specificity:** Modifications described with enough detail that FDA can assess risk
2. **Bounded scope:** Clear boundaries between what is/is not covered
3. **Robust validation:** V&V protocol sufficient to detect safety-relevant changes
4. **Measurable acceptance criteria:** Quantitative thresholds, not subjective assessments
5. **Risk-proportionate monitoring:** Post-implementation monitoring scaled to modification risk
6. **Decision framework:** Clear criteria for determining if a change exceeded PCCP scope

## Total Product Lifecycle (TPLC) Connection

PCCPs fit into the TPLC approach for device oversight:
- **Pre-market:** PCCP describes anticipated changes and validation approach
- **Post-market:** Manufacturer implements changes per PCCP, documents results
- **Annual reporting:** Changes made under PCCP authority may require annual summary reports to FDA
- **PCCP updates:** If the PCCP itself needs modification (new categories, revised thresholds), a supplement is needed

## Annual Reporting Requirements

For devices authorized with a PCCP:
- Changes made under PCCP authority should be documented in the design history file
- FDA may require annual reports summarizing changes implemented under the PCCP
- Real-world performance monitoring data should be tracked and available for FDA inspection
- If post-market data reveals issues with PCCP-authorized changes, the PCCP may need to be revised

## Decision Tree: Does This Change Fall Within PCCP Scope?

```
Was this type of modification described in the PCCP?
├── NO → New 510(k) or supplement required
│
└── YES → Does the change meet ALL acceptance criteria in the PCCP?
          ├── NO → New 510(k) or supplement required
          │
          └── YES → Does post-change monitoring show acceptable performance?
                    ├── NO → Remediate, consider new submission
                    │
                    └── YES → Document per PCCP, maintain in DHF
                              Include in next annual report if required
```

## Real-World Examples of Devices with PCCPs

Several AI/ML-enabled devices have been authorized with PCCPs or PCCP-like mechanisms:

| Device | Company | PCCP Scope | K-number/DEN |
|--------|---------|-----------|-------------|
| IDx-DR | Digital Diagnostics (now Digital Diagnostics) | Autonomous AI for diabetic retinopathy; PCCP for algorithm updates | DEN180001 (De Novo) |
| Caption Health (Caption AI) | Caption Health (now GE HealthCare) | AI-guided cardiac ultrasound; PCCP for model updates | K200621 |
| Viz.ai LVO | Viz.ai | AI stroke detection; subsequent clearances expanded scope | Multiple K-numbers |

Note: Specific PCCP details vary by device. Check FDA decision summaries and De Novo orders for the most current information on authorized PCCPs.

## Applicability Beyond AI/ML

While the primary guidance targets AI/ML devices, the PCCP framework is applicable to:
- **Any iteratively modified software device** — firmware updates, feature additions
- **Hardware devices with anticipated design changes** — material substitutions, dimensional modifications
- **Combination products** — where the device component may change iteratively
- **Labeling modifications** — expanding populations or indications in a controlled manner

FDA has signaled willingness to accept PCCPs for non-AI/ML devices where the manufacturer can clearly define anticipated changes and validation protocols.
