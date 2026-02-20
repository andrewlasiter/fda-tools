# ISO 14971:2019 Risk Management File Template

**Device Name:** [Insert Device Name]
**Device Classification:** [Class I/II/III | 510(k)/PMA/De Novo]
**Manufacturer:** [Company Name]
**Date:** [Date]
**Document Version:** [Version Number]

---

## 1. Risk Management Plan

### 1.1 Scope of Risk Management Activities

**Device Description:**
[Brief description of device, intended use, patient population, use environment]

**Intended Medical Indication:**
[Specific conditions, diseases, or patient populations]

**Intended User Profile:**
[Physicians, nurses, patients, technicians - specify training level]

**Use Environment:**
[Hospital, clinic, home, ambulance - specify environmental conditions]

**Device Lifecycle Phases Covered:**
☐ Design and Development
☐ Manufacturing
☐ Sterilization and Packaging
☐ Storage and Distribution
☐ Installation and Commissioning
☐ Use (including reprocessing if applicable)
☐ Maintenance and Servicing
☐ Disposal/Decommissioning

### 1.2 Risk Management Team

| Name | Role/Title | Responsibilities | Department |
|------|-----------|------------------|-----------|
| [Name] | Risk Management Lead | Overall coordination, risk acceptability decisions | Quality/Regulatory |
| [Name] | Design Engineer | Hazard identification, design mitigations | R&D |
| [Name] | Clinical Specialist | Clinical hazard assessment, benefit-risk | Clinical Affairs |
| [Name] | Quality Engineer | Manufacturing process hazards, verification/validation | Quality |
| [Name] | Regulatory Affairs | Regulatory requirements, submission documentation | Regulatory |

**Qualifications Summary:**
[Brief summary of team qualifications, training in ISO 14971, relevant device experience]

### 1.3 Risk Acceptability Criteria

**Risk Evaluation Matrix:**

| Severity | Probability 1 (Remote) | Probability 2 (Unlikely) | Probability 3 (Possible) | Probability 4 (Probable) | Probability 5 (Frequent) |
|----------|---------|---------|---------|---------|---------|
| **5 - Catastrophic** (Death/Severe Injury) | Medium | Medium | High | High | Unacceptable |
| **4 - Critical** (Permanent Impairment) | Low | Medium | Medium | High | High |
| **3 - Serious** (Medical Intervention) | Low | Low | Medium | Medium | High |
| **2 - Minor** (Temporary Injury) | Acceptable | Low | Low | Medium | Medium |
| **1 - Negligible** (No Injury) | Acceptable | Acceptable | Low | Low | Medium |

**Risk Acceptance Criteria:**
- **Unacceptable Risk:** Cannot release device; requires design changes to reduce risk
- **High Risk:** Requires senior management review and justification; residual risk information provided to users
- **Medium Risk:** Acceptable if benefits outweigh risks; risk control measures implemented; documented in risk management file
- **Low Risk:** Acceptable; no additional risk controls required beyond standard practices
- **Acceptable Risk:** Broadly acceptable; inherent low risk

**Benefit-Risk Analysis Approach:**
[Describe how clinical benefits are weighed against residual risks; cite clinical data, literature, predicate device performance]

**ALARP Principle:**
Risks shall be reduced to As Low As Reasonably Practicable (ALARP), considering:
☐ State of the art technology
☐ Cost of risk reduction measures vs. magnitude of risk reduction
☐ Impact on device performance and usability
☐ Societal expectations and regulatory standards

### 1.4 Risk Management Process Overview

**Process Flow:**
1. **Risk Analysis:** Identify hazards, hazardous situations, and harms (Section 2)
2. **Risk Evaluation:** Estimate risk level and compare to acceptability criteria (Section 3)
3. **Risk Control:** Implement measures to reduce unacceptable risks (Section 4)
4. **Residual Risk Evaluation:** Assess remaining risk after controls (Section 5)
5. **Risk/Benefit Analysis:** Weigh residual risks against clinical benefits (Section 6)
6. **Production and Post-Production:** Monitor field data, update risk file (Section 7)

**Risk Management File Maintenance:**
- Living document updated throughout device lifecycle
- Review triggers: Design changes, post-market adverse events, new regulatory guidance, similar device incidents
- Annual review minimum; more frequent during design/development and first 2 years post-market
- Version control and document approval per QMS procedures

---

## 2. Hazard Identification and Risk Analysis

### 2.1 Hazard Analysis Methodology

**Methods Used:**
☐ Failure Modes and Effects Analysis (FMEA)
☐ Fault Tree Analysis (FTA)
☐ Hazard and Operability Study (HAZOP)
☐ Preliminary Hazard Analysis (PHA)
☐ Use-related hazard analysis (per IEC 62366-1)
☐ Software hazard analysis (per IEC 62304)
☐ Predicate device and literature review (MAUDE, MDR, peer-reviewed publications)

**Hazard Categories Considered (ISO 14971 Annex E):**
☐ Biological and chemical hazards (biocompatibility, toxicity, infection)
☐ Environmental hazards (electromagnetic interference, temperature extremes)
☐ Hazards related to device use (user error, off-label use, misuse)
☐ Functional failure, maintenance, and aging (wear, degradation, end of life)
☐ Mechanical hazards (sharp edges, moving parts, instability)
☐ Energy hazards (electrical shock, thermal burns, radiation, vibration)
☐ Combination device hazards (drug-device interaction)

### 2.2 Failure Modes and Effects Analysis (FMEA)

**FMEA Table:**

| ID | Component/ Process Step | Potential Failure Mode | Potential Effects of Failure (Harm) | Severity (S) 1-5 | Potential Causes | Probability (P) 1-5 | Current Controls | Detectability (D) 1-5 | RPN (S×P×D) | Risk Level |
|----|---------|---------|---------|:---:|---------|:---:|---------|:---:|:---:|:---:|
| H-001 | [Component] | [Failure mode] | [Harm to patient/user] | [1-5] | [Root cause] | [1-5] | [Existing design/procedural controls] | [1-5] | [RPN] | [Low/Med/High] |
| H-002 | | | | | | | | | | |
| ... | | | | | | | | | | |

**RPN Calculation:**
- RPN = Severity × Probability × Detectability
- High Priority: RPN ≥100 or Severity ≥4
- Medium Priority: RPN 50-99
- Low Priority: RPN <50

**Detectability Scale:**
1 = Detected immediately by design (fail-safe)
2 = Detected by automated testing/monitoring
3 = Detected by routine QC or inspection
4 = Detected only by user vigilance or clinical outcome
5 = Cannot detect before harm occurs

### 2.3 Device-Specific Hazard Library

**[Select applicable hazard category from plugin data]**

**For Cardiovascular Devices:**
☐ Thrombosis (H-CV001)
☐ Embolism (H-CV002)
☐ Vessel perforation (H-CV003)
☐ Restenosis (H-CV004)
☐ Infection/Endocarditis (H-CV005)
☐ Electrical shock (H-CV006)
☐ Device migration (H-CV007)
☐ Contrast media reaction (H-CV008)
☐ Arrhythmia (H-CV009)
☐ Hemocompatibility failure (H-CV010)

**For Orthopedic Devices:**
☐ Implant loosening (H-OR001)
☐ Wear debris and osteolysis (H-OR002)
☐ Infection (H-OR003)
☐ Subsidence (H-OR004)
☐ Dislocation (H-OR005)
☐ Periprosthetic fracture (H-OR006)
☐ Nerve or vascular injury (H-OR007)
☐ Metallosis (H-OR008)
☐ Component dissociation (H-OR009)
☐ Adverse tissue reaction (H-OR010)

**For Surgical Devices:**
☐ Tissue damage (H-SU001)
☐ Bleeding (H-SU002)
☐ Thermal injury (H-SU003)
☐ Organ perforation (H-SU004)
☐ Smoke/plume inhalation (H-SU005)
☐ Electrical shock (H-SU006)
☐ Infection transmission (H-SU007)
☐ Instrument breakage (H-SU008)
☐ Gas embolism (H-SU010)

**For Electrical/Active Devices:**
☐ Electrical shock - patient (H-EL001)
☐ Electrical shock - operator (H-EL002)
☐ EMI emissions (H-EL003)
☐ EMI susceptibility (H-EL004)
☐ Software failure - loss of function (H-EL005)
☐ Software failure - incorrect output (H-EL006)
☐ Cybersecurity breach (H-EL007)
☐ Thermal burn (H-EL008)
☐ Battery failure (H-EL009)
☐ Radiation exposure (H-EL010)
☐ Mechanical failure - moving parts (H-EL011)
☐ Alarm failure (H-EL012)

---

## 3. Risk Evaluation

### 3.1 Risk Estimation

**Severity Assessment Criteria:**

| Severity Level | Descriptor | Patient Harm Examples |
|:---:|-----------|---------------------|
| 5 | Catastrophic | Death, irreversible severe injury (e.g., stroke, paralysis, organ failure) |
| 4 | Critical | Permanent impairment or life-threatening injury requiring intervention (e.g., loss of limb, cardiac event) |
| 3 | Serious | Injury requiring medical/surgical intervention; temporary but significant impairment (e.g., infection requiring antibiotics, revision surgery) |
| 2 | Minor | Temporary injury requiring first aid or outpatient care (e.g., minor bleeding, skin irritation) |
| 1 | Negligible | No injury or health effect; inconvenience only (e.g., procedure delay) |

**Probability Assessment Criteria:**

| Probability Level | Descriptor | Quantitative Estimate |
|:---:|-----------|---------------------|
| 5 | Frequent | >10% occurrence rate (>1 in 10 patients/uses) |
| 4 | Probable | 1-10% (1 in 10 to 1 in 100) |
| 3 | Possible | 0.1-1% (1 in 100 to 1 in 1,000) |
| 2 | Unlikely | 0.01-0.1% (1 in 1,000 to 1 in 10,000) |
| 1 | Remote | <0.01% (<1 in 10,000) |

**Data Sources for Probability Estimation:**
☐ Design verification and validation testing results
☐ Predicate device adverse event data (FDA MAUDE, MHRA, registries)
☐ Clinical studies and published literature
☐ Manufacturer internal data (complaint rates, field corrective actions)
☐ Supplier data (component failure rates)
☐ Usability testing observations (use error rates)
☐ Expert judgment (if insufficient data)

### 3.2 Evaluated Risks Summary

**Risks Requiring Control (Medium, High, or Unacceptable):**

| Hazard ID | Hazardous Situation | Initial Risk Level (S×P) | Risk Acceptability | Action Required |
|-----------|---------------------|:---:|:---:|:---:|
| H-001 | [Description] | [e.g., 5×3=15] | High | Risk control required |
| H-002 | [Description] | [e.g., 4×2=8] | Medium | Risk control or justification |
| ... | | | | |

**Acceptable Risks (No Additional Controls):**
[List hazards with Low or Acceptable risk level; document rationale for acceptance]

---

## 4. Risk Control Measures

### 4.1 Risk Control Hierarchy (ISO 14971 Clause 7.4)

**Priority Order:**
1. **Inherent Safety by Design** (eliminate or reduce hazard)
   - Examples: Rounded edges (eliminate sharp hazard), non-toxic materials, fail-safe mechanisms
2. **Protective Measures in Device** (mitigate hazard through safety features)
   - Examples: Alarms, interlocks, redundant sensors, overpressure relief valves
3. **Information for Safety** (IFU warnings, training, labeling)
   - Examples: Contraindications, warnings about use errors, operator training requirements

**Rationale for Control Selection:**
[For each risk control, justify why that level of hierarchy was chosen; document if higher-level control not feasible]

### 4.2 Risk Control Implementation

**Risk Control Table:**

| Hazard ID | Risk Control Measure | Control Category (Design/Protective/Information) | Implementation Details | Verification Method | Responsible Party | Status | Verification Evidence |
|-----------|---------------------|:---:|---------------------|---------------------|------------------|:---:|---------------------|
| H-001 | [Control description] | Design | [Specific design feature or process change] | [Test method, acceptance criteria] | [Name/Role] | ☐ Complete ☐ Pending | [Test report, document reference] |
| H-002 | [Control description] | Protective | [Safety feature, alarm, interlock] | [Verification protocol] | [Name/Role] | ☐ Complete ☐ Pending | [Test report reference] |
| H-003 | [Control description] | Information | [IFU section, warning label, training] | [Usability testing, labeling review] | [Name/Role] | ☐ Complete ☐ Pending | [Usability report reference] |
| ... | | | | | | | |

**Verification of Risk Control Effectiveness:**
☐ Design verification testing per protocols [Reference test plans]
☐ Validation testing in simulated or actual use conditions [Reference validation plans]
☐ Usability evaluation per IEC 62366-1 [Reference usability study report]
☐ Clinical evaluation per MDR/MEDDEV 2.7/1 or FDA guidance [Reference clinical data]

### 4.3 Introduction of New Hazards

**Assessment:**
Were any new hazards introduced by risk control measures?
☐ No new hazards identified
☐ Yes - new hazards identified and analyzed below

**If yes, new hazards:**

| New Hazard ID | Description | Introduced by Control Measure | Risk Assessment | Additional Controls |
|--------------|-------------|------------------------------|----------------|-------------------|
| H-NEW-001 | [New hazard] | [Which control measure] | [S×P] | [How mitigated] |

---

## 5. Residual Risk Evaluation

### 5.1 Residual Risk Assessment

**Residual Risk Table:**

| Hazard ID | Initial Risk (S×P) | Risk Controls Implemented | Residual Risk (S×P) | Risk Reduction Achieved | Residual Risk Acceptability |
|-----------|:---:|---------------------------|:---:|:---:|:---:|
| H-001 | [5×3=15 High] | [List controls] | [5×1=5 Low] | Probability reduced 3→1 | ☐ Acceptable ☐ Justification required |
| H-002 | [4×2=8 Medium] | [List controls] | [4×1=4 Low] | Probability reduced 2→1 | ☐ Acceptable ☐ Justification required |
| ... | | | | | |

**Overall Residual Risk:**
☐ All residual risks are acceptable per criteria in Section 1.3
☐ Some residual risks require benefit-risk justification (see Section 6)

### 5.2 Completeness of Risk Control

**Checklist:**
☐ All identified hazards have been addressed (controlled or justified)
☐ No unacceptable residual risks remain
☐ Risk controls have been verified as effective
☐ No new unacceptable hazards introduced by risk controls
☐ Information for safety (IFU warnings, labeling) is comprehensive and usable
☐ Residual risks are disclosed to users in IFU and labeling

---

## 6. Risk-Benefit Analysis

### 6.1 Clinical Benefits

**Intended Clinical Benefits:**
[List clinical benefits to patient/healthcare system; cite clinical data, literature, or predicate device performance]

**Supporting Evidence:**
☐ Clinical study data [Reference clinical study report]
☐ Published literature [Cite peer-reviewed publications]
☐ Predicate device data (for 510(k)) [Reference substantial equivalence comparison]
☐ Post-market surveillance data (if available) [Reference MAUDE, registries]

**Quantification of Benefits (if possible):**
[Example: Reduction in procedural time by 30 minutes vs. predicate; reduction in target lesion revascularization rate from 15% to 8% at 12 months]

### 6.2 Benefit-Risk Determination

**For High or Medium Residual Risks:**

| Residual Risk | Clinical Benefits That Outweigh Risk | Justification | Is Risk/Benefit Favorable? |
|--------------|-------------------------------------|---------------|:---:|
| H-001: [Description, Residual S×P] | [Benefits] | [Narrative justification; why benefits outweigh risk] | ☐ Yes ☐ No |
| H-002: [Description] | [Benefits] | [Justification] | ☐ Yes ☐ No |

**Overall Benefit-Risk Conclusion:**
☐ Clinical benefits outweigh all residual risks; device is acceptable for intended use
☐ Benefit-risk is not favorable; device should not proceed to market

**Disclosure to Users:**
All residual risks and uncertainties are disclosed in:
☐ Instructions for Use (IFU) - Warnings and Precautions section
☐ Product labeling - Warnings, Contraindications, Adverse Events
☐ Physician training materials
☐ Patient labeling (if applicable)

---

## 7. Production and Post-Production Information

### 7.1 Post-Market Surveillance Plan

**Data Sources:**
☐ Customer complaints and adverse event reports
☐ FDA MAUDE database (similar devices)
☐ International adverse event databases (MHRA, Health Canada, TGA)
☐ Published literature and registry data
☐ Field corrective actions and recalls
☐ Supplier notifications of component failures
☐ Clinical post-market studies (if required by FDA or MDR)

**Review Frequency:**
☐ Quarterly review of complaints and adverse events
☐ Annual comprehensive risk management file review
☐ Ad hoc review triggered by: serious adverse event, cluster of similar events, new regulatory guidance, similar device recall

**Trending and Analysis:**
- Quantitative trending: complaint rates per units sold, adverse event rates
- Qualitative analysis: identify new hazards or failure modes not anticipated in premarket risk analysis
- Statistical process control: detect significant increases in event rates

### 7.2 Risk Management File Maintenance

**Version Control:**

| Version | Date | Author | Changes Summary | Approved By |
|:---:|----------|--------|----------------|-------------|
| 1.0 | [Date] | [Name] | Initial risk analysis for design phase | [Name, Title] |
| 2.0 | [Date] | [Name] | Updated after design verification testing | [Name, Title] |
| 3.0 | [Date] | [Name] | Updated after clinical study completion | [Name, Title] |
| X.X | [Date] | [Name] | Post-market update based on field data | [Name, Title] |

**Change Triggers:**
☐ Design changes (per design control procedures)
☐ Manufacturing process changes
☐ Supplier changes or component obsolescence
☐ Post-market adverse events or complaints trending
☐ New regulatory guidance or standards
☐ Similar device recalls or safety alerts
☐ New hazards identified from literature or internal data

### 7.3 Continuous Improvement

**Lessons Learned:**
[Document insights from post-market data; changes made to device, manufacturing, labeling, or training to reduce risks]

**Effectiveness of Risk Controls:**
[Assess whether real-world data confirms effectiveness of risk controls; any unexpected failure modes or use errors]

**Communication to Regulators:**
☐ Annual reports (for PMA devices)
☐ Periodic safety updates (for MDR/IVDR)
☐ Safety alerts or field corrective actions (if triggered)
☐ Recalls or safety communications (if required)

---

## 8. Appendices

### Appendix A: References

- ISO 14971:2019 - Medical devices — Application of risk management to medical devices
- IEC 62304:2006+A1:2015 - Medical device software — Software life cycle processes
- IEC 62366-1:2015 - Medical devices — Application of usability engineering to medical devices
- FDA Guidance: "Design Control Guidance for Medical Device Manufacturers" (1997)
- FDA Guidance: "Recognized Consensus Standards - Risk Management" (ISO 14971)
- [Device-specific FDA guidances]
- [Applicable ASTM, ISO, IEC standards for device type]

### Appendix B: Definitions and Abbreviations

- **ALARP:** As Low As Reasonably Practicable
- **FMEA:** Failure Modes and Effects Analysis
- **FTA:** Fault Tree Analysis
- **Harm:** Physical injury or damage to health of people, or damage to property or the environment
- **Hazard:** Potential source of harm
- **Hazardous Situation:** Circumstance in which people, property, or the environment are exposed to one or more hazards
- **Probability:** Used as a general term to describe the likelihood of occurrence (may be qualitative or quantitative)
- **Residual Risk:** Risk remaining after risk control measures have been implemented
- **Risk:** Combination of the probability of occurrence of harm and the severity of that harm
- **RPN:** Risk Priority Number (FMEA = Severity × Probability × Detectability)
- **Severity:** Measure of the possible consequences of a hazard

### Appendix C: Supporting Documentation

- [Reference list to design verification test reports]
- [Reference list to design validation test reports]
- [Reference to usability engineering file per IEC 62366-1]
- [Reference to software hazard analysis per IEC 62304]
- [Reference to clinical evaluation report]
- [Reference to biocompatibility test reports per ISO 10993]
- [Reference to sterilization validation per ISO 11135/11137]
- [Reference to electrical safety testing per IEC 60601-1]

---

**Document Approval:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Risk Management Lead | | | |
| Design Engineering Manager | | | |
| Quality Assurance Manager | | | |
| Regulatory Affairs Manager | | | |
| Senior Management (for final approval) | | | |

---

**End of Risk Management File**

*This template complies with ISO 14971:2019. Customize for specific device type, hazards, and risk controls.*
