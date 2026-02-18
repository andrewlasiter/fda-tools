---
name: fda-hde-support
description: Support Humanitarian Device Exemption (HDE) submissions including outline generation, prevalence validation, probable benefit analysis, IRB tracking, and annual distribution reports. Use when working with devices for rare diseases affecting fewer than 8,000 patients per year in the US.
---

# FDA HDE Support

## Overview

Assists with Humanitarian Device Exemption (HDE) submissions per 21 CFR 814 Subpart H. For devices intended to treat or diagnose diseases or conditions affecting fewer than 8,000 individuals per year in the United States.

## When to Use

- Device targets a rare disease or condition (<8,000 US patients/year)
- User has or needs a Humanitarian Use Designation (HUD) from OOPD
- User needs to prepare an HDE submission package
- User needs to validate disease prevalence data
- User needs to track IRB approvals across facilities
- User needs to generate annual distribution reports

## Workflow

1. **Prevalence Validation**
   Confirm the disease/condition affects <8,000 patients/year in the US.
   Use the PrevalenceValidator to assess eligibility and data quality.
   Recommend credible data sources (NIH GARD, CDC WONDER, NORD, Orphanet).

2. **HDE Submission Outline**
   Generate a structured outline per 21 CFR 814.104 with all required sections.
   Identify gaps in device information and documentation.
   Include HDE-specific requirements (profit restriction, IRB supervision).

3. **Probable Benefit Analysis**
   Build a probable benefit template covering all evidence categories.
   Note: HDE does NOT require proof of effectiveness, only probable benefit.
   Assess evidence strength across bench testing, animal studies, clinical experience, literature, and alternatives analysis.

4. **IRB Approval Tracking**
   Track IRB approval status at each facility where the device will be used.
   Monitor for expiring approvals and generate compliance alerts.
   Per 21 CFR 814.124, IRB approval is required at each use facility.

5. **Annual Distribution Reporting**
   Generate annual reports per 21 CFR 814.126(b).
   Track device distribution, adverse events, profit status, and prevalence updates.

## Key Regulatory References

- 21 CFR 814 Subpart H (Humanitarian Use Devices)
- Section 520(m) of the FD&C Act
- FDA Guidance: "Humanitarian Device Exemption (HDE) Program" (2019)
- 21 CFR 814.124 (IRB Approval)
- 21 CFR 814.126(b) (Annual Reporting)

## Important Notes

- HUD designation must be obtained from OOPD BEFORE submitting the HDE
- HDE devices are generally limited to cost recovery (non-profit) unless pediatric
- IRB approval is required at EACH facility where the device is used
- Annual distribution reports must be submitted to FDA
- This tool is for RESEARCH USE ONLY - professional review required before FDA submission

## Library Module

Core implementation: `lib/hde_support.py`

Key classes:
- `HDESubmissionOutline` - Submission outline generator
- `PrevalenceValidator` - Prevalence eligibility validator
- `ProbableBenefitAnalyzer` - Probable benefit template generator
- `IRBApprovalTracker` - Multi-facility IRB tracker
- `AnnualDistributionReport` - Annual report generator
