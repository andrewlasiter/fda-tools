---
name: fda-rwe-integration
description: Integrate Real World Evidence (RWE) into FDA regulatory submissions. Provides RWD source connection, quality assessment, and submission templates for 510(k) and PMA pathways aligned with the FDA RWE Framework (2018) and latest FDA guidance on RWD/RWE submissions.
---

# FDA RWE Integration

## Overview

Supports integration of Real World Evidence (RWE) and Real World Data (RWD) into FDA regulatory submissions. Aligned with the FDA Framework for Real-World Evidence Program (December 2018) and the 21st Century Cures Act Section 3022.

## When to Use

- User wants to supplement a 510(k) or PMA with real-world evidence
- User needs to evaluate quality of available RWD sources
- User needs to design an RWE study for regulatory submission
- User needs guidance on FDA-accepted analytical methods for RWE
- User is considering using registry data, EHR data, or claims data for a submission
- User needs an RWE submission template aligned with FDA expectations

## Workflow

1. **Data Source Assessment**
   Use the RWEDataSourceConnector to register and evaluate RWD sources.
   Supported source types: EHR, claims, registries, pragmatic trials, patient-generated data, natural history studies, FDA Sentinel.
   Assess compliance readiness (IRB, DUA, HIPAA).

2. **Quality Assessment**
   Use the RWDQualityAssessor to score data quality across 5 dimensions:
   - Relevance (population, exposure, outcomes, follow-up)
   - Reliability (consistency, verification, audit trail, standards)
   - Completeness (variables, follow-up, outcome ascertainment)
   - Transparency (provenance, processing, limitations, pre-specification)
   - Regulatory Alignment (design, endpoints, bias control, statistics)

3. **Source Recommendations**
   Get data source recommendations based on:
   - Submission type (510(k), PMA, HDE, De Novo)
   - Device type (implant, diagnostic, etc.)
   - Whether the device targets a rare disease

4. **Submission Template Generation**
   Generate RWE submission templates for 510(k) or PMA pathways.
   Templates include all FDA-expected sections with content guidance.
   Includes quality checklist and recommended analytical methods.

5. **Analytical Method Selection**
   Review FDA-accepted analytical methods:
   - Propensity Score Matching
   - Instrumental Variables
   - Difference-in-Differences
   - Interrupted Time Series
   - External Control Arms
   - Bayesian Adaptive Designs

## Key Regulatory References

- FDA Framework for Real-World Evidence Program (December 2018)
- 21st Century Cures Act Section 3022
- FDA Guidance: "Use of Real-World Evidence to Support Regulatory Decision-Making" (2021)
- FDA Guidance: "Submitting Documents Using Real-World Data and Real-World Evidence" (2023)

## Important Notes

- RWE can supplement but may not replace traditional clinical evidence for PMA
- Data quality assessment is critical - FDA expects documented quality framework
- Pre-Submission meeting recommended to discuss RWE strategy with FDA
- IRB approval and Data Use Agreements required before accessing most RWD
- UDI availability significantly strengthens device-specific RWE claims
- This tool is for RESEARCH USE ONLY - professional review required

## Library Module

Core implementation: `lib/rwe_integration.py`

Key classes:
- `RWEDataSourceConnector` - Register and manage RWD sources
- `RWDQualityAssessor` - Assess data quality across 5 dimensions
- `RWESubmissionTemplate` - Generate 510(k) and PMA submission templates
