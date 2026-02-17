# TICKET-005: IDE Pathway Support - Implementation Plan

**Ticket ID:** TICKET-005
**Priority:** MEDIUM
**Status:** NOT STARTED
**Original Estimate:** 100-140 hours (Epic)
**Created:** 2026-02-17
**Business Analyst:** Claude Code

---

## Executive Summary

This implementation plan breaks down TICKET-005 (IDE Pathway Support) into implementable phases following an MVP-first approach. The plan prioritizes high-value, low-risk features that can be delivered incrementally while deferring complex validation requirements and features with uncertain market demand.

**Key Challenge:** No FDA IDE API endpoint exists. We must build IDE support from scratch using ClinicalTrials.gov integration, regulatory frameworks (21 CFR 812), and document templates.

**Strategic Approach:**
- Leverage existing infrastructure (ClinicalTrials.gov integration via `/fda-tools:trials`)
- Build regulatory framework templates based on 21 CFR 812
- Focus on document generation and decision support tools
- Defer complex compliance monitoring until market validation

**Total Effort:** 100-140 hours broken into 5 phases
**Estimated Timeline:** Q2-Q4 2026 (phased delivery)

---

## Table of Contents

1. [Requirements Analysis](#requirements-analysis)
2. [Phase Breakdown](#phase-breakdown)
3. [Technical Approach](#technical-approach)
4. [Data Sources](#data-sources)
5. [Acceptance Criteria](#acceptance-criteria)
6. [Risk Assessment](#risk-assessment)
7. [Dependencies](#dependencies)
8. [Recommended Implementation Sequence](#recommended-implementation-sequence)

---

## Requirements Analysis

### Regulatory Framework: 21 CFR Part 812

**Primary Regulation:** 21 CFR Part 812 - Investigational Device Exemptions

**Key Concepts:**
1. **Significant Risk (SR) vs Non-Significant Risk (NSR) Determination**
   - SR devices require FDA IDE application approval
   - NSR devices require IRB approval only (abbreviated IDE)
   - Determination based on 4 criteria (21 CFR 812.3(m))

2. **IDE Application Components (21 CFR 812.20)**
   - Investigational Plan (protocol)
   - Device description and manufacturing
   - Investigator agreements
   - IRB certifications
   - Informed consent materials

3. **Compliance Obligations**
   - UADE reporting (10 working days)
   - Annual progress reports (SR devices)
   - Protocol amendments
   - Enrollment tracking

### Stakeholder Analysis

| Stakeholder | Needs | Pain Points | Tool Requirements |
|-------------|-------|-------------|-------------------|
| **Regulatory Affairs Manager** | SR/NSR determination guidance, IDE application templates | Uncertainty about risk classification, complex FDA forms | Decision tree tool, compliant templates |
| **Clinical Affairs Lead** | Protocol design, sample size calculations, endpoint selection | Statistical requirements, FDA expectations for IDE studies | Protocol generator, sample size calculator enhancements |
| **Principal Investigator** | Informed consent templates, IRB submission packages | Regulatory compliance complexity, time-consuming documentation | IRB package generator, consent templates |
| **Quality/Compliance Manager** | Compliance tracking, deadline management, audit trails | Manual tracking of UADE events and annual reports | Compliance dashboard (lower priority) |
| **Sponsor Executive** | IDE-to-marketing transition, clinical data reuse | Understanding how IDE data feeds 510(k)/PMA | Transition workflow documentation |

### Competitive Analysis

**Existing Tools:**
- **MasterControl Clinical Excellence:** $50K-100K/year, full CTMS, overkill for small studies
- **Veeva Vault CTMS:** Enterprise-level, $100K+/year
- **Manual Spreadsheets/Word:** Free, error-prone, no compliance automation

**Market Gap:** No affordable IDE-specific planning and compliance tool for small-to-mid-sized device companies (target: $1,000-5,000/year price point).

### User Journey Mapping

**Current State (Without Tool):**
1. Sponsor manually reviews 21 CFR 812 → 8-12 hours
2. Manually draft SR/NSR determination → 6-10 hours
3. Manually create protocol from FDA templates → 20-30 hours
4. Manually track compliance deadlines in spreadsheet → 2-4 hours/month
5. Manually prepare IRB packages → 8-12 hours
**Total:** 50-70 hours per IDE study

**Future State (With Tool):**
1. Run `/fda-tools:ide-risk-assessment` → 30 minutes (generates SR/NSR determination with rationale)
2. Run `/fda-tools:ide-protocol` → 2 hours (generates 80% complete protocol draft)
3. Run `/fda-tools:ide-irb-package` → 1 hour (assembles IRB submission)
4. Run `/fda-tools:ide-monitor` (optional) → 15 minutes/month (tracks deadlines)
**Total:** 8-10 hours per IDE study

**Value Proposition:** 40-60 hour time savings (80-85% reduction) per IDE study

---

## Phase Breakdown

### Phase 0: Foundation & Architecture (8-12 hours) - PREREQUISITE

**Goal:** Establish data structures and architectural patterns for IDE support

**Deliverables:**
1. **IDE Data Schema** (3 hours)
   - Define `ide_study.json` structure
   - Fields: `ide_number`, `risk_classification`, `protocol_version`, `irb_approvals`, `enrollment_data`, `uade_events`, `annual_reports`
   - Integration with existing project structure (`~/fda-510k-data/projects/{project_name}/`)

2. **Template Structure Setup** (2 hours)
   - Create directory: `data/templates/ide/`
   - Subdirectories: `protocols/`, `informed_consent/`, `irb_packages/`, `annual_reports/`

3. **Command Framework** (3-4 hours)
   - Stub commands: `ide-risk-assessment.md`, `ide-protocol.md`, `ide-irb-package.md`
   - Establish argument patterns and data flow conventions

**Acceptance Criteria:**
- [ ] `ide_study.json` schema documented
- [ ] Template directory structure created
- [ ] 3 stub command files created with frontmatter
- [ ] Architecture documented in `IDE_ARCHITECTURE.md`

**Effort:** 8-12 hours
**Priority:** PREREQUISITE (must complete before other phases)
**Risk:** Low

---

### Phase 1: SR vs NSR Determination Workflow (20-30 hours) - MVP PRIORITY

**Goal:** Implement 21 CFR 812.3(m) decision tree for risk classification

**Deliverables:**

#### 1.1 Command: `/fda-tools:ide-risk-assessment` (12-15 hours)

**Purpose:** Generate SR/NSR determination with regulatory citations

**Inputs:**
- Device description (from `device_profile.json` or user input)
- Intended use
- Device characteristics (implantable, life-supporting, invasive, energy delivery)
- Predicate device risk precedents (from 510(k) database)

**Decision Tree Logic:**
```
21 CFR 812.3(m) - Significant Risk Criteria:

1. Is device intended as IMPLANT + presents serious risk?
   → YES: SR (cite 21 CFR 812.3(m)(1))
   → NO: Continue to #2

2. Is device for SUPPORTING/SUSTAINING LIFE + presents serious risk?
   → YES: SR (cite 21 CFR 812.3(m)(2))
   → NO: Continue to #3

3. Is device of SUBSTANTIAL IMPORTANCE in diagnosing/treating disease + presents serious risk?
   → YES: SR (cite 21 CFR 812.3(m)(3))
   → NO: Continue to #4

4. Does device otherwise present SERIOUS RISK to health/safety/welfare?
   → YES: SR (cite 21 CFR 812.3(m)(4))
   → NO: NSR (cite 21 CFR 812.2(b))
```

**Risk Assessment Questionnaire:**
```markdown
## Device Characteristics Questionnaire

1. Device Type:
   - [ ] Implanted (permanent or temporary >30 days)
   - [ ] External (skin contact only)
   - [ ] Invasive (penetrates tissue)
   - [ ] Non-invasive

2. Life Support Function:
   - [ ] Device failure could result in death
   - [ ] Device is primary life support mechanism
   - [ ] Device provides backup life support
   - [ ] No life support function

3. Clinical Importance:
   - [ ] Only available treatment for condition
   - [ ] First-line therapy
   - [ ] Alternative to existing therapy
   - [ ] Adjunctive/supplementary

4. Invasiveness Level:
   - [ ] Tissue contact duration: [<24 hrs | 24hrs-30 days | >30 days]
   - [ ] Blood contact: [Yes | No]
   - [ ] Central nervous system contact: [Yes | No]

5. Energy Delivery:
   - [ ] Electrical energy to patient
   - [ ] Thermal energy (heating/cooling)
   - [ ] Radiation/ultrasound
   - [ ] No energy delivery

6. Control Group Comparison:
   - [ ] Study design includes control group
   - [ ] Single-arm study (no control)
   - [ ] Historical controls

7. Novel Technology:
   - [ ] First-in-human device of this type
   - [ ] Modification of existing device
   - [ ] Predicate devices exist with similar risk profile
```

**Output:**
```markdown
# SR/NSR Risk Determination Report
## {Device Name} - Product Code {CODE}

**Generated:** {date} | FDA Tools Plugin v5.29.0

---

## 1. Risk Classification Determination

**DETERMINATION: SIGNIFICANT RISK (SR)** or **NON-SIGNIFICANT RISK (NSR)**

**Regulatory Basis:** 21 CFR 812.3(m)

---

## 2. Risk Analysis

### Criterion 1: Implant + Serious Risk (21 CFR 812.3(m)(1))
**Assessment:** [YES/NO]
**Rationale:** {device-specific reasoning}

### Criterion 2: Life-Supporting/Sustaining (21 CFR 812.3(m)(2))
**Assessment:** [YES/NO]
**Rationale:** {device-specific reasoning}

### Criterion 3: Substantial Diagnostic/Therapeutic Importance (21 CFR 812.3(m)(3))
**Assessment:** [YES/NO]
**Rationale:** {device-specific reasoning}

### Criterion 4: Otherwise Serious Risk (21 CFR 812.3(m)(4))
**Assessment:** [YES/NO]
**Rationale:** {device-specific reasoning}

---

## 3. Regulatory Requirements Based on Determination

**IF SR DEVICE:**
- FDA IDE application required (21 CFR 812.20)
- 30-day FDA review period before study initiation
- IRB approval required
- Annual progress reports to FDA + IRBs
- UADE reporting within 10 working days
- Full compliance with 21 CFR Part 812

**IF NSR DEVICE:**
- No FDA IDE application required
- IRB approval sufficient to begin study
- Abbreviated IDE requirements (21 CFR 812.2(b))
- Annual reports to IRB only (not FDA)
- Informed consent per 21 CFR Part 50

---

## 4. Precedent Analysis

**Similar Devices:** [Search ClinicalTrials.gov for similar IDE studies]
- {NCT ID}: {Device name} - {SR/NSR determination from study record}
- {NCT ID}: {Device name} - {SR/NSR determination from study record}

**510(k) Predicate Risk Profiles:**
- {K-number}: {Predicate device} - {Risk characteristics}

---

## 5. Recommendation

**Proposed Classification:** {SR or NSR}

**Confidence Level:** [HIGH | MEDIUM | LOW]
- HIGH: Clear regulatory precedent, unambiguous device characteristics
- MEDIUM: Some ambiguity, recommend FDA Pre-Sub meeting
- LOW: Novel device type, strongly recommend FDA Pre-Sub for official determination

**Next Steps:**
1. If HIGH confidence → Proceed with IDE application (SR) or IRB submission (NSR)
2. If MEDIUM/LOW confidence → Request FDA Pre-Sub meeting using `/fda-tools:presub --pathway ide`
3. If SR → Generate IDE protocol using `/fda-tools:ide-protocol`
4. If NSR → Generate IRB package using `/fda-tools:ide-irb-package`

---

## Disclaimer
This SR/NSR determination is AI-generated for preliminary planning only. FDA is the final arbiter of SR vs NSR classification (21 CFR 812.66). For borderline cases, submit a formal request to FDA for official determination.
```

**Validation Approach:**
- **Target:** ≥90% agreement with FDA precedent (per original ticket requirement)
- **Method:** Test against 20 known IDE studies with documented SR/NSR classifications
- **Data Source:** ClinicalTrials.gov study records + published FDA guidance examples
- **Acceptance:** If ≥18/20 correct classifications → Tool validated for use
- **Limitations:** Tool cannot account for novel device types without precedent

**Effort:** 12-15 hours
- Decision tree logic: 4 hours
- Questionnaire framework: 3 hours
- Report generator: 4 hours
- Validation study: 3-4 hours

**Acceptance Criteria:**
- [ ] Decision tree implements all 4 criteria from 21 CFR 812.3(m)
- [ ] Generates determination report with regulatory citations
- [ ] Validation study shows ≥90% agreement (18/20 test cases)
- [ ] Confidence level assigned based on precedent clarity
- [ ] Integrates with `/fda-tools:presub --pathway ide` for Pre-Sub generation

---

#### 1.2 Enhanced Pre-Sub Template for IDE (8-12 hours)

**Goal:** Extend existing `/fda-tools:presub` command with IDE pathway support

**Requirements:**
1. **Pathway Detection** (2 hours)
   - Auto-detect IDE pathway when `--pathway ide` specified
   - Add IDE-specific template: `data/templates/presub_meetings/ide_presub.md` (already exists!)
   - Populate SR/NSR determination section from `ide_study.json`

2. **IDE-Specific Questions** (3-4 hours)
   - Add to `data/question_banks/presub_questions.json`:
   ```json
   {
     "ide_pathway": {
       "sr_nsr_questions": [
         "Does FDA agree with our SR/NSR determination for this device?",
         "Are there any additional risk factors we should consider in our SR/NSR analysis?",
         "Does FDA recommend a DSMB for this study given the device risk profile?"
       ],
       "protocol_questions": [
         "Does FDA agree with our proposed primary effectiveness endpoint: {endpoint}?",
         "Is our proposed sample size of {N} patients adequate for FDA review?",
         "Does FDA recommend any additional safety endpoints for this device type?"
       ],
       "clinical_design_questions": [
         "Is a single-arm study with historical controls acceptable, or does FDA require a concurrent control group?",
         "Does FDA recommend pivotal study vs feasibility study for this device?",
         "Are there any FDA-recognized clinical outcome assessments we should use?"
       ]
     }
   }
   ```

3. **Template Integration** (3-4 hours)
   - Modify `commands/presub.md` to load IDE template when `--pathway ide`
   - Auto-populate from `ide_study.json` (if exists)
   - Fall back to classification data + user inputs if no IDE study data

4. **Testing** (2-3 hours)
   - Test IDE Pre-Sub generation for 3 device types (implant, external diagnostic, minimally invasive)
   - Verify all required sections present per FDA Pre-Sub guidance

**Effort:** 8-12 hours

**Acceptance Criteria:**
- [ ] `/fda-tools:presub --pathway ide` generates IDE-specific Pre-Sub package
- [ ] SR/NSR determination section auto-populated from risk assessment
- [ ] ≥15 IDE-specific question templates available
- [ ] Template passes completeness check (all required sections present)

**Total Phase 1 Effort:** 20-30 hours
**Priority:** HIGH (MVP feature - immediate user value)
**Risk:** LOW (extends existing presub command, IDE template already exists)

---

### Phase 2: IDE Protocol Generator (30-40 hours) - HIGH VALUE

**Goal:** Generate 21 CFR 812.25-compliant Investigational Plan

**Deliverables:**

#### 2.1 Command: `/fda-tools:ide-protocol` (25-35 hours)

**Purpose:** Generate FDA-compliant IDE protocol template

**Inputs:**
- Device profile (from `device_profile.json`)
- SR/NSR determination (from Phase 1)
- Study design parameters (user-provided or inferred from predicates)
- Sample size (from enhanced `/fda-tools:calc sample-size`)
- Applicable standards (from `/fda-tools:standards`)
- Predicate clinical data (from `/fda-tools:trials`)

**21 CFR 812.25 Required Components:**

1. **Purpose of Investigation** (3 hours)
   - Intended use of device
   - Study objectives (primary/secondary)
   - Clinical rationale

2. **Protocol** (10-12 hours)
   - Study design template (RCT, single-arm, crossover, adaptive)
   - Inclusion/exclusion criteria generator
   - Sample size justification (integrate with `/fda-tools:calc`)
   - Randomization/blinding procedures
   - Follow-up schedule template
   - Statistical analysis plan outline

3. **Risk Analysis** (4-5 hours)
   - Device-related risks (from MAUDE data via `/fda-tools:safety`)
   - Comparison to standard of care
   - Risk mitigation strategies
   - Benefit-risk assessment framework

4. **Device Description** (2 hours)
   - Components, materials, principles of operation
   - Anticipated device modifications during study
   - Auto-populate from `device_profile.json`

5. **Monitoring Procedures** (3-4 hours)
   - DSMB charter template (for SR devices)
   - Interim analysis plan
   - Stopping rules (safety/futility)
   - Data quality monitoring

6. **Labeling** (2 hours)
   - Investigational use label template
   - IFU template for investigators

7. **Informed Consent** (3-4 hours)
   - 21 CFR Part 50 compliant template
   - Required elements checklist
   - Risk disclosure language
   - HIPAA authorization

8. **IRB Information** (1-2 hours)
   - Reviewing IRB template
   - IRB approval tracking

**Protocol Template Structure:**
```markdown
# Investigational Plan
## {Device Name} - {Indication}

**Protocol Version:** 1.0
**Protocol Date:** {date}
**Sponsor:** {company_name}
**Regulatory Pathway:** IDE ({SR or NSR})

---

## 1. Purpose of Investigation

### 1.1 Device Description
{Auto-populated from device_profile.json}

### 1.2 Intended Use
{From device_profile.json or user input}

### 1.3 Study Objectives

**Primary Objective:**
[TODO: User-defined primary objective]

**Secondary Objectives:**
1. [TODO: User-defined]
2. [TODO: User-defined]

---

## 2. Protocol

### 2.1 Study Design

**Design Type:** {Randomized Controlled Trial | Single-Arm Prospective | Crossover | Adaptive}

**Study Phase:** {Feasibility | Pivotal | Post-Market}

**Control Group:** {Concurrent randomized control | Historical control | Objective performance criteria | None}

**Blinding:** {Open-label | Single-blind | Double-blind}

### 2.2 Population

**Inclusion Criteria:**
1. Age ≥{age} years
2. Diagnosis of {condition}
3. {Device-specific clinical criteria from predicate studies}
4. Willing and able to provide informed consent
5. [TODO: Additional criteria]

**Exclusion Criteria:**
1. Pregnancy or lactation
2. Contraindications to {procedure/device use}
3. Participation in another investigational study within {timeframe}
4. {Device-specific exclusions}
5. [TODO: Additional criteria]

### 2.3 Sample Size Justification

**Proposed Sample Size:** {N} patients

**Power Analysis:**
- **Primary Endpoint:** {endpoint description}
- **Effect Size:** {expected difference or success rate}
- **Alpha:** 0.05 (two-sided)
- **Power (1-beta):** 0.80
- **Statistical Test:** {t-test | chi-square | survival analysis}
- **Dropout Rate:** {percentage}%

{Auto-generated from /fda-tools:calc sample-size with FDA-aligned defaults}

**Sample Size Formula:**
{Mathematical justification from calc command}

### 2.4 Randomization and Blinding

{Template based on study design selection}

### 2.5 Study Procedures

**Screening Phase:**
- Informed consent
- Medical history and physical exam
- Inclusion/exclusion verification
- Baseline assessments

**Treatment Phase:**
- Device implantation/application procedure
- Immediate post-procedure assessments
- {Device-specific procedures}

**Follow-Up Schedule:**

| Visit | Timepoint | Assessments |
|-------|-----------|-------------|
| Baseline | Day 0 | {Baseline assessments} |
| Follow-up 1 | {timeframe} | {Assessments} |
| Follow-up 2 | {timeframe} | {Assessments} |
| Final | {timeframe} | {Final assessments} |

### 2.6 Study Endpoints

**Primary Effectiveness Endpoint:**
{User-defined with guidance from predicate studies via /fda-tools:trials}

**Primary Safety Endpoint:**
Composite of major adverse events at {timeframe}:
- Death
- Device malfunction requiring intervention
- Serious adverse events related to device
- {Device-specific safety events from MAUDE analysis}

**Secondary Endpoints:**
1. {User-defined}
2. {User-defined}

### 2.7 Statistical Analysis Plan

**Primary Analysis:**
{Template based on study design and endpoint type}

**Interim Analysis:**
{Optional - DSMB charter if SR device}

**Missing Data Handling:**
{Last observation carried forward | Multiple imputation | Per-protocol analysis}

**Subgroup Analyses:**
{Pre-specified subgroups, if any}

---

## 3. Risk Analysis

### 3.1 Known Device Risks

{Auto-populated from /fda-tools:safety MAUDE analysis for product code}

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| {Risk 1 from MAUDE} | {High/Med/Low} | {%} | {Mitigation strategy} |
| {Risk 2 from MAUDE} | {High/Med/Low} | {%} | {Mitigation strategy} |

### 3.2 Study-Specific Risks

**Risks from Investigational Device:**
1. {Novel material/technology risks not in MAUDE}
2. {Risks specific to study population}

**Risks from Study Procedures:**
1. {Procedural risks}
2. {Follow-up risks}

### 3.3 Benefit-Risk Assessment

**Anticipated Clinical Benefits:**
{Based on predicate device outcomes and literature}

**Comparison to Standard of Care:**
{Current treatment options and their risk/benefit profiles}

**Conclusion:**
{Summary of why benefits justify risks for this investigation}

---

## 4. Device Description

{Auto-populated from device_profile.json}

**Anticipated Modifications During Study:**
{Template for documenting protocol amendments}

---

## 5. Monitoring Procedures

### 5.1 Data Safety Monitoring Board (DSMB)

{FOR SR DEVICES ONLY - Auto-include if SR determination}

**DSMB Composition:**
- Independent clinical expert in {specialty}
- Independent biostatistician
- Independent device safety expert

**DSMB Charter:**
{Template for DSMB responsibilities, meeting frequency, stopping rules}

### 5.2 Interim Analysis Plan

**Analysis Timepoints:**
{Based on enrollment milestones or event counts}

**Stopping Rules:**
1. **Safety Stopping:** {Criteria for early termination due to safety}
2. **Futility Stopping:** {Criteria for early termination due to futility}

### 5.3 Data Quality Monitoring

**Source Data Verification:**
{Frequency and scope of SDV}

**Monitoring Plan:**
{On-site monitoring frequency based on risk}

---

## 6. Labeling

### 6.1 Investigational Device Label

**Required Text (21 CFR 812.5):**
"CAUTION—Investigational device. Limited by Federal (or United States) law to investigational use."

### 6.2 Instructions for Use (IFU)

{Template for investigator IFU}

---

## 7. Informed Consent

### 7.1 Informed Consent Form

{21 CFR Part 50 compliant template - see Section 2.3 below}

### 7.2 HIPAA Authorization

{HIPAA template}

---

## 8. IRB Information

**Reviewing IRB:**
{Institution name and IRB contact}

**IRB Approval Status:**
{Pending | Approved on {date} | Amendments pending}

---

## Appendices

A. Sample Size Calculation Details
B. DSMB Charter (if applicable)
C. Informed Consent Form
D. Case Report Forms (CRFs)
E. Investigator Agreement
F. Device Risk Analysis (ISO 14971)

---

**Protocol Version History:**
| Version | Date | Changes |
|---------|------|---------|
| 1.0 | {date} | Initial protocol |

```

**Integration Points:**
1. `/fda-tools:calc sample-size` - Auto-populate power analysis
2. `/fda-tools:trials` - Find similar IDE studies for endpoint/design precedents
3. `/fda-tools:safety` - Extract device-specific risks from MAUDE
4. `/fda-tools:standards` - Applicable standards for device testing
5. `device_profile.json` - Auto-populate device description

**Effort:** 25-35 hours
- Template development: 15-20 hours
- Integration with existing commands: 5-8 hours
- Testing and refinement: 5-7 hours

**Acceptance Criteria:**
- [ ] Generates complete 21 CFR 812.25 Investigational Plan
- [ ] All 8 required sections present
- [ ] Auto-populates from device_profile.json
- [ ] Integrates sample size from `/fda-tools:calc`
- [ ] Includes device-specific risks from MAUDE
- [ ] SR devices automatically get DSMB charter
- [ ] NSR devices omit unnecessary SR-only sections

---

#### 2.2 Informed Consent Template Generator (5-8 hours)

**Purpose:** Generate 21 CFR Part 50 compliant informed consent forms

**Template Components:**

```markdown
# Informed Consent Form
## Clinical Investigation of {Device Name}

**Protocol Title:** {Full protocol title}
**Sponsor:** {Company name}
**Principal Investigator:** [Site-specific]
**IRB:** [Site-specific]

---

## INTRODUCTION

You are being asked to participate in a research study. This form provides information about the study. Please read it carefully and ask questions before you decide whether to participate.

**Participation is voluntary.** You may refuse to participate or withdraw at any time without penalty.

---

## 1. PURPOSE OF THE STUDY (21 CFR 50.25(a)(1))

**Why is this study being done?**

This study is testing an investigational medical device called {device_name}. The device is investigational, which means it is NOT approved by the U.S. Food and Drug Administration (FDA) for this use.

The purpose of this study is to:
{Study objectives in plain language}

---

## 2. STUDY PROCEDURES (21 CFR 50.25(a)(1))

**What will happen if you participate?**

{Detailed procedure description in patient-friendly language}

**How long will the study last?**

Your participation will last approximately {duration}. You will be asked to return for {N} follow-up visits over {timeframe}.

---

## 3. RISKS AND DISCOMFORTS (21 CFR 50.25(a)(2))

**What are the reasonably foreseeable risks?**

Risks from the investigational device may include:
{Device-specific risks from MAUDE analysis + protocol risk section}

Risks from study procedures may include:
{Procedural risks}

**How will these risks be minimized?**
{Risk mitigation strategies}

---

## 4. POTENTIAL BENEFITS (21 CFR 50.25(a)(3))

**Will you benefit from this study?**

Potential benefits to you:
{Direct benefits, if any}

**You may not receive any direct benefit from participating in this study.** The information from this study may benefit future patients with {condition}.

---

## 5. ALTERNATIVE TREATMENTS (21 CFR 50.25(a)(4))

**What are your other options?**

If you choose not to participate in this study, alternative treatments include:
1. {Standard of care option 1}
2. {Standard of care option 2}
3. No treatment

You should discuss these alternatives with your doctor.

---

## 6. COSTS AND COMPENSATION (21 CFR 50.25(a)(6))

**Will you have to pay for anything?**

{Cost disclosure - typically study device and procedures are free}

**Will you be paid?**

{Compensation disclosure - typically none for device studies, or reimbursement for travel}

---

## 7. INJURY COMPENSATION (21 CFR 50.25(a)(6))

**What happens if you are injured?**

{Sponsor statement on injury compensation - varies by sponsor policy}

If you believe you have been injured as a result of participating in this study, contact:
{Study contact information}

---

## 8. CONFIDENTIALITY (21 CFR 50.25(a)(5))

**How will your information be protected?**

Your study records will be kept confidential to the extent allowed by law. Your information may be shared with:
- The study sponsor ({company})
- The FDA and other regulatory authorities
- The Institutional Review Board (IRB)

Your name will not be used in any reports or publications.

**HIPAA Authorization:** {HIPAA language}

---

## 9. VOLUNTARY PARTICIPATION (21 CFR 50.25(a)(8))

**Can you stop participating?**

Your participation is voluntary. You may:
- Refuse to participate without penalty
- Withdraw from the study at any time
- Refuse to answer any question

If you withdraw, no new information will be collected, but information already collected may still be used.

---

## 10. CONTACT INFORMATION (21 CFR 50.25(a)(7))

**Who can you contact with questions?**

**Study Questions:** Contact the Principal Investigator:
{PI name, phone, email}

**Rights Questions:** Contact the IRB:
{IRB name, phone, email}

**Injury Reporting:** Contact the study sponsor:
{Sponsor contact, phone, 24-hour emergency line}

---

## CONSENT SIGNATURE

**Statement of Consent:**

I have read this consent form (or it has been read to me). I have had the opportunity to ask questions and all my questions have been answered to my satisfaction.

By signing below, I voluntarily agree to participate in this research study. I will receive a signed copy of this consent form.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
**Participant Signature**
**Date:**

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
**Person Obtaining Consent Signature**
**Date:**

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
**Investigator Signature** (if different from above)
**Date:**

---

**Protocol Version:** {version}
**ICF Version:** {version}
**IRB Approval Date:** {date}
**ICF Expiration Date:** {date}

```

**Auto-Population:**
- Device name and description from `device_profile.json`
- Risks from protocol Section 3 (auto-generated from MAUDE)
- Study procedures from protocol Section 2
- Alternative treatments from predicate/literature analysis

**Effort:** 5-8 hours

**Acceptance Criteria:**
- [ ] Includes all 8 required elements (21 CFR 50.25)
- [ ] Auto-populates from IDE protocol
- [ ] Plain language (Flesch-Kincaid grade level ≤8)
- [ ] Device-specific risks from MAUDE analysis
- [ ] Alternative treatments section populated

**Total Phase 2 Effort:** 30-40 hours
**Priority:** HIGH (Core IDE deliverable)
**Risk:** MEDIUM (Regulatory complexity, requires validation by IRB expert)

---

### Phase 3: Sample Size Calculator Enhancements (15-20 hours) - MEDIUM PRIORITY

**Goal:** Extend `/fda-tools:calc sample-size` with IDE-specific designs

**Current Capabilities** (from IDE_PATHWAY_SPECIFICATION.md):
- One-sample test (success rate)
- Two-sample test (comparison)
- Non-inferiority test
- Power analysis (alpha, beta, dropout)

**Enhancements Needed:**

#### 3.1 Superiority Trial Design (4-5 hours)

**Formula:**
```
n = (Zα/2 + Zβ)² × [p1(1-p1) + p2(1-p2)] / (p1 - p2)²

Where:
- p1 = treatment success rate
- p2 = control success rate
- Zα/2 = critical value for two-sided alpha
- Zβ = critical value for power
```

**Command Extension:**
```bash
/fda-tools:calc sample-size \
  --design superiority \
  --treatment-rate 0.85 \
  --control-rate 0.70 \
  --alpha 0.05 \
  --power 0.80 \
  --dropout 0.15
```

**Output:**
```
SUPERIORITY TRIAL SAMPLE SIZE CALCULATION
==========================================

Parameters:
  Treatment success rate (p1): 0.85
  Control success rate (p2): 0.70
  Difference (p1 - p2): 0.15 (15 percentage points)
  Significance level (α): 0.05 (two-sided)
  Power (1-β): 0.80
  Dropout rate: 15%

Calculation:
  Required events per group: 82 patients
  Adjusted for dropout: 97 patients per group

TOTAL SAMPLE SIZE: 194 patients (97 treatment + 97 control)

Assumptions:
  - Independent samples (not paired)
  - Normal approximation valid (np ≥ 5 for both groups)
  - Equal allocation (1:1 randomization)
```

---

#### 3.2 Equivalence Trial Design (4-5 hours)

**Formula:**
```
n = (Zα + Zβ)² × 2σ² / δ²

Where:
- δ = equivalence margin
- σ = standard deviation
- Zα = critical value for one-sided alpha
- Zβ = critical value for power
```

**Command Extension:**
```bash
/fda-tools:calc sample-size \
  --design equivalence \
  --equivalence-margin 0.10 \
  --sd 0.25 \
  --alpha 0.05 \
  --power 0.80
```

**Output:**
```
EQUIVALENCE TRIAL SAMPLE SIZE CALCULATION
=========================================

Parameters:
  Equivalence margin (δ): ±0.10 (±10%)
  Standard deviation (σ): 0.25
  Significance level (α): 0.05 (one-sided, for TOST)
  Power (1-β): 0.80

Calculation:
  Required sample size per group: 126 patients

TOTAL SAMPLE SIZE: 252 patients (126 per group)

Note: Equivalence trials require larger sample sizes than non-inferiority trials.
Use TOST (Two One-Sided Tests) for analysis.
```

---

#### 3.3 Survival Analysis (Time-to-Event) (5-7 hours)

**Formula (Freedman, 1982):**
```
Events required: E = (Zα/2 + Zβ)² × 4 / (log(HR))²

Sample size: n = E / (p_event)

Where:
- HR = hazard ratio
- p_event = probability of observing event by end of study
```

**Command Extension:**
```bash
/fda-tools:calc sample-size \
  --design survival \
  --hazard-ratio 0.65 \
  --event-rate 0.30 \
  --alpha 0.05 \
  --power 0.80 \
  --accrual-period 24 \
  --followup-period 12
```

**Output:**
```
TIME-TO-EVENT (SURVIVAL) SAMPLE SIZE CALCULATION
================================================

Parameters:
  Hazard ratio (HR): 0.65 (35% risk reduction)
  Expected event rate: 30%
  Significance level (α): 0.05 (two-sided)
  Power (1-β): 0.80
  Accrual period: 24 months
  Follow-up period: 12 months

Calculation:
  Required events: 118 events
  Expected sample size: 393 patients (118 / 0.30)

TOTAL SAMPLE SIZE: 393 patients

Timeline:
  - Enrollment: 24 months (393 patients)
  - Follow-up: 12 months
  - Total study duration: 36 months
  - Expected events at end: 118

Analysis: Log-rank test or Cox proportional hazards regression
```

---

#### 3.4 Adaptive Design Support (Documentation Only) (2-3 hours)

**Goal:** Provide guidance on adaptive trial designs (not full implementation)

**FDA Guidance Reference:** *Adaptive Designs for Medical Device Clinical Studies* (2016)

**Documentation:**
```markdown
## Adaptive Trial Designs for IDE Studies

FDA supports adaptive designs that allow modifications based on interim data while maintaining study integrity.

**Common Adaptive Features:**
1. **Sample Size Re-estimation** - Adjust N based on observed variance
2. **Interim Futility Analysis** - Stop early if treatment unlikely to succeed
3. **Dose/Parameter Selection** - Choose optimal device settings
4. **Adaptive Randomization** - Adjust allocation based on interim results

**FDA Requirements:**
- Pre-specify adaptation rules in protocol
- Maintain Type I error control
- Document all interim analyses
- Independent DSMB review required for SR devices

**For adaptive design support, consult biostatistician and consider FDA Pre-Sub meeting.**

**External Tools:**
- East (Cytel) - Commercial adaptive design software ($10K-50K/year)
- PASS (NCSS) - Power analysis software with adaptive modules ($1K-2K/year)
```

**Effort:** 15-20 hours
- Superiority: 4-5 hours
- Equivalence: 4-5 hours
- Survival: 5-7 hours
- Adaptive documentation: 2-3 hours

**Acceptance Criteria:**
- [ ] Superiority design with effect size calculation
- [ ] Equivalence design with TOST guidance
- [ ] Survival analysis with event/sample size calculation
- [ ] Adaptive design guidance document
- [ ] All calculations validated against published tables (FDA guidance appendices)

**Total Phase 3 Effort:** 15-20 hours
**Priority:** MEDIUM (Enhances existing tool, not new command)
**Risk:** LOW (Extends proven `/fda-tools:calc` architecture)

---

### Phase 4: IRB Submission Package Generator (12-18 hours) - MEDIUM PRIORITY

**Goal:** Assemble complete IRB submission package

**Deliverables:**

#### 4.1 Command: `/fda-tools:ide-irb-package` (10-15 hours)

**Purpose:** Generate IRB submission checklist and package

**Components:**

1. **IRB Application Form Template** (3-4 hours)
   - Generic IRB application (adaptable to institution-specific forms)
   - Study summary
   - Risk classification
   - Investigator qualifications

2. **Required Documents Checklist** (2-3 hours)
```markdown
# IRB Submission Checklist
## {Device Name} IDE Study

**Submission Date:** {date}
**Protocol Version:** {version}

---

## Required Documents

### Core Documents
- [ ] IRB Application Form (completed)
- [ ] Protocol Version {version}
- [ ] Informed Consent Form Version {version}
- [ ] HIPAA Authorization Form
- [ ] Investigator Brochure (if available)

### Device Information
- [ ] Device description and specifications
- [ ] Investigational Device Labeling
- [ ] SR/NSR Risk Determination Report
- [ ] Risk Analysis (ISO 14971 summary)

### Sponsor Information
- [ ] FDA IDE Approval Letter (if SR device - submit after FDA approval)
- [ ] Investigator Agreement
- [ ] Delegation of Authority Log
- [ ] Financial Disclosure Form

### Regulatory Documents
- [ ] Applicable Standards List
- [ ] Regulatory history (510(k) clearances for predicate devices)
- [ ] Clinical literature review (if available)

### Study Logistics
- [ ] Recruitment materials (flyers, ads) - if applicable
- [ ] Case Report Forms (CRFs)
- [ ] Data and Safety Monitoring Plan

---

## IRB Submission Package File Structure

```
/irb_submission_{date}/
├── 01_Application/
│   └── IRB_Application_Form.pdf
├── 02_Protocol/
│   ├── Protocol_v1.0.pdf
│   └── Protocol_Synopsis.pdf
├── 03_Consent/
│   ├── Informed_Consent_Form_v1.0.pdf
│   └── HIPAA_Authorization.pdf
├── 04_Device_Info/
│   ├── Device_Description.pdf
│   ├── Risk_Determination_Report.pdf
│   └── Investigational_Labeling.pdf
├── 05_Regulatory/
│   ├── FDA_IDE_Approval.pdf (if SR)
│   ├── Investigator_Agreement.pdf
│   └── Standards_List.pdf
└── 06_Study_Documents/
    ├── Recruitment_Flyer.pdf
    └── CRFs.pdf
```

**Validation:**
- All required documents present
- Version numbers consistent across documents
- Dates consistent
- Digital signatures where required
```

3. **Package Assembly** (3-4 hours)
   - Auto-collect documents from project folder
   - Generate cover letter for IRB
   - Create submission checklist
   - ZIP package for electronic submission

4. **IRB-Specific Customization** (2-4 hours)
   - Templates for common IRB systems:
     - Western IRB (WIRB)
     - Advarra (formerly Schulman)
     - University/hospital IRBs (generic template)

**Command Usage:**
```bash
/fda-tools:ide-irb-package --project PROJECT_NAME --irb-type wirb --output ~/Desktop/IRB_Submission.zip
```

**Effort:** 10-15 hours

**Acceptance Criteria:**
- [ ] Generates complete IRB submission checklist
- [ ] Assembles all documents from project folder
- [ ] Creates organized directory structure
- [ ] Validates document versions and dates
- [ ] Supports ≥2 major IRB systems (WIRB, Advarra)

---

#### 4.2 Investigator Brochure Outline (2-3 hours)

**Purpose:** Template for investigator brochure (if required)

**Template:**
```markdown
# Investigator Brochure
## {Device Name}

**Sponsor:** {Company}
**Version:** 1.0
**Date:** {date}

---

## 1. Summary

{Brief device description and clinical rationale}

---

## 2. Device Description

{From device_profile.json}

**Components:**
**Materials:**
**Principle of Operation:**

---

## 3. Nonclinical Studies

### 3.1 Biocompatibility
{From standards testing data}

### 3.2 Mechanical Testing
{From standards testing data}

### 3.3 Animal Studies
{If applicable - user-provided}

---

## 4. Clinical Experience

### 4.1 Prior Clinical Studies
{From /fda-tools:trials search results}

### 4.2 Published Literature
{From /fda-tools:literature search results}

---

## 5. Known Risks

### 5.1 Device-Related Risks
{From MAUDE analysis}

### 5.2 Procedure-Related Risks
{User-provided}

---

## 6. References

{Auto-generated from literature and trials searches}

---

**Version History:**
| Version | Date | Changes |
|---------|------|---------|
| 1.0 | {date} | Initial version |
```

**Effort:** 2-3 hours

**Total Phase 4 Effort:** 12-18 hours
**Priority:** MEDIUM (Nice-to-have, not critical path)
**Risk:** LOW (Document assembly, no complex logic)

---

### Phase 5: ClinicalTrials.gov Enhanced Integration (8-12 hours) - MEDIUM PRIORITY

**Goal:** Improve IDE-specific trial discovery and analysis

**Deliverables:**

#### 5.1 Enhanced `/fda-tools:trials` Command (6-8 hours)

**Current Functionality** (from trials.md):
- Search by device name, condition, sponsor
- Filter by status (completed, recruiting, all)
- Device-only filtering (`--device-only`)
- Results with NCT ID, enrollment, design, outcomes

**IDE-Specific Enhancements:**

1. **IDE Status Detection** (2-3 hours)
   - Parse study records for IDE approval language
   - Flag studies as "IDE-approved" vs "not requiring IDE"
   - Extract IDE number if mentioned (e.g., "IDE G123456")

2. **SR vs NSR Classification Hints** (2-3 hours)
   - Analyze study characteristics to infer likely SR/NSR classification:
     - Implantable device → likely SR
     - Significant risk keywords in study description
     - DSMB mentioned → likely SR
     - Annual FDA reports mentioned → SR

3. **Study Design Pattern Analysis** (2-3 hours)
   - Aggregate statistics across similar IDE studies:
     - Most common study design (RCT vs single-arm)
     - Typical enrollment (median, range)
     - Common primary endpoints
     - Typical follow-up duration

**Enhanced Output:**
```
  ClinicalTrials.gov IDE Study Analysis
  Product Code: {CODE} | Device Type: {name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Source: ClinicalTrials.gov API v2
  Total IDE studies found: {N}

IDE STUDY PATTERNS
────────────────────────────────────────

  **Study Design Distribution:**
  - Randomized Controlled: 45% (9/20 studies)
  - Single-Arm Prospective: 35% (7/20 studies)
  - Crossover: 10% (2/20 studies)
  - Other: 10% (2/20 studies)

  **Enrollment Statistics:**
  - Median: 150 patients
  - Range: 30 - 500 patients
  - Average: 185 patients

  **Risk Classification (Inferred):**
  - Likely SR: 14/20 studies (70%)
  - Likely NSR: 4/20 studies (20%)
  - Unclear: 2/20 studies (10%)

  **Common Primary Endpoints:**
  1. Device success rate at 12 months (8 studies)
  2. Major adverse events at 30 days (6 studies)
  3. Clinical improvement score at 6 months (4 studies)

DETAILED STUDY RESULTS
────────────────────────────────────────

  Study 1: {Title}
  ─────────────────
  NCT ID: {nct_id}
  Sponsor: {sponsor}
  Status: {status}

  **IDE Information:**
  - IDE Number: {extracted if available, else "Not disclosed"}
  - Risk Classification: {Likely SR | Likely NSR | Unknown}
  - Rationale: {Implantable device + DSMB mentioned}

  Design: {RCT | Single-arm | etc.}
  Enrollment: {N} patients ({actual/estimated})
  Primary Endpoint: {endpoint}

  URL: https://clinicaltrials.gov/study/{nct_id}

[... additional studies ...]

RECOMMENDATIONS FOR YOUR IDE STUDY
────────────────────────────────────────

  Based on {N} similar IDE studies:

  **Study Design:**
  Most common design is {RCT | single-arm}. Consider this as precedent for FDA expectations.

  **Sample Size:**
  Typical enrollment is {range}. Your proposed sample size of {N} is:
  - {Within | Above | Below} the typical range
  - {Recommendation if outside range}

  **Primary Endpoint:**
  Most studies use "{common_endpoint}". Consider alignment with FDA expectations.

  **Risk Classification:**
  {X}% of similar studies appear to be SR devices. Your device is likely {SR | NSR} based on:
  - {Risk factor 1}
  - {Risk factor 2}

NEXT STEPS
────────────────────────────────────────

  - Generate SR/NSR determination: `/fda-tools:ide-risk-assessment --product-code {CODE}`
  - Generate IDE protocol: `/fda-tools:ide-protocol --project {NAME}`
  - Review detailed study design for {NCT_ID}: https://clinicaltrials.gov/study/{NCT_ID}
```

**Effort:** 6-8 hours

**Acceptance Criteria:**
- [ ] Detects and flags IDE studies
- [ ] Infers likely SR/NSR classification (≥70% accuracy on validation set)
- [ ] Aggregates study design patterns
- [ ] Provides actionable recommendations for user's IDE study design

---

#### 5.2 Integration with IDE Protocol Generator (2-4 hours)

**Purpose:** Auto-populate IDE protocol from ClinicalTrials.gov precedents

**Workflow:**
1. User runs `/fda-tools:trials --product-code CODE --device-only --status completed`
2. Results saved to `clinical_trials.json`
3. User runs `/fda-tools:ide-protocol --project NAME --use-precedents`
4. Protocol generator reads `clinical_trials.json`:
   - Suggests study design based on most common precedent
   - Pre-fills typical enrollment range
   - Lists common primary endpoints for user to select
   - Identifies typical follow-up duration

**Effort:** 2-4 hours

**Total Phase 5 Effort:** 8-12 hours
**Priority:** MEDIUM (Enhances usability, not critical)
**Risk:** LOW (Extends existing trials command)

---

## Summary of Phase Breakdown

| Phase | Deliverables | Effort (hours) | Priority | Risk | Timeline |
|-------|-------------|----------------|----------|------|----------|
| **Phase 0** | Foundation & Architecture | 8-12 | PREREQUISITE | Low | Week 1 |
| **Phase 1** | SR/NSR Determination + IDE Pre-Sub | 20-30 | HIGH (MVP) | Low | Weeks 2-3 |
| **Phase 2** | IDE Protocol Generator + Consent Template | 30-40 | HIGH | Medium | Weeks 4-6 |
| **Phase 3** | Sample Size Calculator Enhancements | 15-20 | MEDIUM | Low | Week 7 |
| **Phase 4** | IRB Package Generator | 12-18 | MEDIUM | Low | Week 8 |
| **Phase 5** | ClinicalTrials.gov Enhanced Integration | 8-12 | MEDIUM | Low | Week 9 |
| **TOTAL** | **All Phases** | **93-132 hours** | - | - | **9-11 weeks** |

**Original Estimate:** 100-140 hours
**Revised Estimate:** 93-132 hours
**Variance:** -7% to -6% (within tolerance)

---

## Technical Approach

### Data Sources

Since no FDA IDE API exists, we rely on:

1. **Regulatory Framework (21 CFR 812)** - PRIMARY
   - SR/NSR criteria (21 CFR 812.3(m))
   - IDE application requirements (21 CFR 812.20)
   - Compliance obligations (21 CFR 812.150)
   - Informed consent (21 CFR Part 50)
   - **Reliability:** 100% (statutory requirements)
   - **Maintenance:** Monitor Federal Register for amendments

2. **ClinicalTrials.gov API v2** - EXTERNAL API
   - IDE study discovery
   - Study design patterns
   - Enrollment statistics
   - Primary endpoints
   - **Reliability:** 95%+ (mandatory registration for SR IDE studies per 42 CFR Part 11)
   - **Coverage:** SR devices only (NSR studies exempt from registration)
   - **Maintenance:** Daily sync recommended

3. **FDA Guidance Documents** - REFERENCE
   - *Significant Risk and Nonsignificant Risk Medical Device Studies* (2006)
   - *Investigational Device Exemptions (IDEs) for Early Feasibility Medical Device Clinical Studies* (2013)
   - *Adaptive Designs for Medical Device Clinical Studies* (2016)
   - **Reliability:** 100% (official FDA guidance)
   - **Maintenance:** Quarterly check for updates

4. **Existing Plugin Data** - INTERNAL
   - MAUDE adverse events (device-specific risks)
   - 510(k) predicate devices (risk precedents)
   - Published literature (clinical evidence)
   - Applicable standards (ISO 14155, etc.)
   - **Reliability:** Reuses validated Phase 1-2 enrichment pipelines
   - **Maintenance:** Inherits existing update schedules

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────┐
│              User Input Layer                       │
│  - Product code                                     │
│  - Device description                               │
│  - Study design parameters                          │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│           Data Enrichment Layer                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ Classification Data (OpenFDA)               │   │
│  │  → Device class, regulation, panel          │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │ Clinical Trials (ClinicalTrials.gov)        │   │
│  │  → Similar IDE studies, design patterns     │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │ Safety Data (MAUDE)                         │   │
│  │  → Device-specific risks, adverse events    │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │ Literature (PubMed)                         │   │
│  │  → Clinical evidence, published protocols   │   │
│  └─────────────────────────────────────────────┘   │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│          IDE Document Generator Layer               │
│  ┌─────────────────────────────────────────────┐   │
│  │ SR/NSR Determination Engine                 │   │
│  │  → 21 CFR 812.3(m) decision tree            │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │ Protocol Generator                          │   │
│  │  → 21 CFR 812.25 compliant template         │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │ Informed Consent Generator                  │   │
│  │  → 21 CFR Part 50 compliant template        │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │ IRB Package Assembler                       │   │
│  │  → Checklist + document collection          │   │
│  └─────────────────────────────────────────────┘   │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│              Output Layer                           │
│  - ide_study.json (metadata)                        │
│  - risk_determination_report.md                     │
│  - ide_protocol_v1.0.md                             │
│  - informed_consent_v1.0.md                         │
│  - irb_submission_checklist.md                      │
│  - presub_plan_ide.md (if Pre-Sub requested)        │
└─────────────────────────────────────────────────────┘
```

### File Structure

```
~/fda-510k-data/projects/{PROJECT_NAME}/
├── ide_study.json                      # IDE study metadata
├── risk_determination_report.md        # SR/NSR determination
├── ide_protocol_v1.0.md                # Investigational Plan
├── informed_consent_v1.0.md            # ICF template
├── investigator_brochure_v1.0.md       # IB outline (optional)
├── irb_submission_checklist.md         # IRB package checklist
├── clinical_trials.json                # Precedent IDE studies (from /fda:trials)
├── device_profile.json                 # Device characteristics (existing)
├── safety_cache/                       # MAUDE data (existing)
└── ide_monitoring/                     # Compliance tracking (Phase 6 - out of scope)
    ├── uade_events.json
    ├── enrollment_log.json
    └── annual_reports/
```

### Integration with Existing Commands

| Existing Command | IDE Integration Point |
|------------------|----------------------|
| `/fda-tools:start` | Initialize IDE project, create `ide_study.json` |
| `/fda-tools:trials` | Find precedent IDE studies, populate study design patterns |
| `/fda-tools:safety` | Extract device-specific risks for protocol Section 3 |
| `/fda-tools:literature` | Populate investigator brochure Section 4 (clinical experience) |
| `/fda-tools:standards` | Identify applicable standards (ISO 14155, ISO 14971) |
| `/fda-tools:calc` | Generate sample size justification for protocol Section 2.3 |
| `/fda-tools:presub` | Generate IDE Pre-Sub package with `--pathway ide` |
| `/fda-tools:export` | Export IDE documents to PDF/Word for submission |

---

## Validation Approach

### SR vs NSR Determination Validation (≥90% Accuracy Requirement)

**Objective:** Validate decision tree against known FDA determinations

**Method:**
1. **Test Dataset Assembly** (8-10 hours)
   - Source 20 IDE studies with documented SR/NSR classifications
   - Data sources:
     - FDA Pre-Sub meeting summaries (publicly available via FOIA)
     - Published case studies in literature
     - ClinicalTrials.gov study records (SR studies explicitly labeled)
     - FDA guidance document examples

2. **Device Type Distribution:**
   - 5 implantable devices (expected: SR)
   - 5 life-supporting devices (expected: SR)
   - 5 minimally invasive diagnostic devices (expected: NSR)
   - 5 borderline cases (e.g., temporary implants, moderate risk)

3. **Validation Execution** (4-6 hours)
   - Input device characteristics into `/fda-tools:ide-risk-assessment`
   - Compare tool determination vs actual FDA determination
   - Calculate accuracy: (Correct classifications) / (Total) × 100%

4. **Acceptance Criteria:**
   - **Target:** ≥90% agreement (18/20 correct)
   - **Minimum:** ≥85% agreement (17/20 correct)
   - **If <85%:** Refine decision tree logic and re-test

5. **Error Analysis:**
   - For misclassifications, document:
     - Device characteristics that led to error
     - FDA rationale (if available)
     - Decision tree refinement needed

**Validation Test Cases (Examples):**

| Device Type | Characteristics | Expected | Tool Result | Match? |
|-------------|----------------|----------|-------------|--------|
| Coronary stent | Implant, blood contact, life-supporting | SR | SR | ✓ |
| Glucose meter | External, diagnostic, no tissue contact | NSR | NSR | ✓ |
| Surgical robot | Invasive, critical procedure, no implant | SR (borderline) | ? | ? |
| Wound dressing (drug-eluting) | External, <24hr contact, drug component | NSR (borderline) | ? | ? |

**Validation Report Template:**
```markdown
# SR/NSR Determination Validation Report
**Date:** {date}
**Tool Version:** v5.29.0
**Test Dataset:** 20 IDE devices

---

## Results Summary

**Overall Accuracy:** 18/20 (90%)

**By Device Category:**
- Implantable: 5/5 (100%)
- Life-Supporting: 5/5 (100%)
- Minimally Invasive: 4/5 (80%)
- Borderline Cases: 4/5 (80%)

**Misclassifications:**
1. Device: {name} | Expected: NSR | Tool: SR | Root Cause: {analysis}
2. Device: {name} | Expected: SR | Tool: NSR | Root Cause: {analysis}

---

## Decision Tree Refinements

Based on misclassifications, the following refinements were made:
1. {Refinement description}
2. {Refinement description}

---

## Conclusion

Tool meets ≥90% accuracy target. Approved for production use with disclaimer that borderline cases should be submitted to FDA for official determination.
```

**Effort for Validation:** 12-16 hours (separate from implementation)
**Timeline:** Complete before Phase 1 release

---

## Acceptance Criteria

### Phase-Specific Criteria

**Phase 0: Foundation**
- [ ] `ide_study.json` schema defined and documented
- [ ] Template directory structure created
- [ ] 3 stub command files created
- [ ] Architecture diagram documented

**Phase 1: SR/NSR Determination**
- [ ] Decision tree implements all 4 criteria (21 CFR 812.3(m))
- [ ] Risk assessment questionnaire covers all relevant factors
- [ ] Determination report includes regulatory citations
- [ ] Validation study achieves ≥90% accuracy (18/20 test cases)
- [ ] Confidence level assigned (HIGH/MEDIUM/LOW)
- [ ] Integration with `/fda-tools:presub --pathway ide` functional

**Phase 2: IDE Protocol Generator**
- [ ] Generates complete 21 CFR 812.25 Investigational Plan
- [ ] All 8 required sections present
- [ ] Auto-populates from `device_profile.json`
- [ ] Integrates sample size from `/fda-tools:calc`
- [ ] Includes device-specific risks from MAUDE
- [ ] SR devices get DSMB charter automatically
- [ ] NSR devices omit SR-only sections
- [ ] Informed consent template includes all 8 required elements (21 CFR 50.25)
- [ ] Plain language (Flesch-Kincaid grade level ≤8)

**Phase 3: Sample Size Enhancements**
- [ ] Superiority design with validated formula
- [ ] Equivalence design with TOST guidance
- [ ] Survival analysis with event/sample size calculation
- [ ] Adaptive design guidance document
- [ ] All calculations match published FDA guidance tables

**Phase 4: IRB Package Generator**
- [ ] IRB submission checklist includes all required documents
- [ ] Package assembler collects documents from project folder
- [ ] Directory structure organized and validated
- [ ] Supports ≥2 major IRB systems
- [ ] Investigator brochure outline auto-populated

**Phase 5: ClinicalTrials.gov Integration**
- [ ] IDE studies flagged in search results
- [ ] SR/NSR classification inferred (≥70% accuracy on validation set)
- [ ] Study design patterns aggregated
- [ ] Recommendations provided for user's study design
- [ ] Integration with protocol generator functional

### Cross-Cutting Acceptance Criteria

**Regulatory Compliance:**
- [ ] All templates cite relevant CFR sections
- [ ] Guidance references current and accurate
- [ ] Disclaimers present on all AI-generated content

**Usability:**
- [ ] Commands follow existing plugin argument patterns
- [ ] Error messages clear and actionable
- [ ] Documentation includes usage examples
- [ ] Output formats consistent with existing commands

**Data Integrity:**
- [ ] All auto-populated data traceable to source
- [ ] Version control for templates (protocol v1.0, v1.1, etc.)
- [ ] Date stamps on all generated documents

**Testing:**
- [ ] Unit tests for decision tree logic
- [ ] Integration tests for data pipelines
- [ ] End-to-end tests for complete workflows (3 device types)

---

## Risk Assessment

### Implementation Risks

| Risk | Probability | Impact | Mitigation Strategy | Owner |
|------|------------|--------|---------------------|-------|
| **R1: SR/NSR validation <90% accuracy** | MEDIUM | HIGH | Pre-validation with 10 test cases before Phase 1 release; if <90%, engage regulatory consultant for decision tree review | Business Analyst |
| **R2: Regulatory framework changes (21 CFR 812 amendment)** | LOW | MEDIUM | Monitor Federal Register quarterly; version templates to allow rollback | Development Team |
| **R3: ClinicalTrials.gov API rate limits** | LOW | LOW | Implement caching; max 1 req/2 sec (well below 50 req/min limit) | Development Team |
| **R4: Limited market demand (IDE niche)** | MEDIUM | HIGH | Phase 1 MVP release to gauge adoption before investing in Phases 2-5; target ≥5 users in Q3 2026 | Product Manager |
| **R5: Template legal liability (incorrect guidance)** | LOW | HIGH | Prominent disclaimers on all outputs; "Not regulatory advice, verify independently"; liability insurance | Legal/Compliance |
| **R6: IRB submission requirements vary by institution** | MEDIUM | MEDIUM | Provide generic templates + customization guide; support WIRB/Advarra (covers ~40% of market) | Business Analyst |
| **R7: Sample size calculations require biostatistician validation** | LOW | MEDIUM | Validate formulas against published FDA guidance; include disclaimer recommending biostatistician review | Development Team |
| **R8: Informed consent must comply with institutional policies** | MEDIUM | MEDIUM | Template provides federal minimum (21 CFR 50); users must add institution-specific language | Business Analyst |

### Risk Mitigation: Staged Rollout

**Beta Release (Phase 1 Only):**
- Limited to 5-10 early adopters
- Collect feedback on SR/NSR determination accuracy
- Refine decision tree based on real-world usage
- **Go/No-Go Decision:** If ≥4/5 users find tool valuable + ≥90% SR/NSR accuracy → Proceed to Phase 2

**Production Release (Phases 1-3):**
- Public release with validated SR/NSR tool
- IDE protocol generator (Phase 2)
- Enhanced sample size calculator (Phase 3)
- Target: ≥25 active users by Q4 2026

**Enterprise Release (Phases 4-5):**
- IRB package generator
- Advanced ClinicalTrials.gov integration
- Consider paid tier for enterprise features ($2K-5K/year)

---

## Dependencies

### Internal Dependencies

| Dependency | Required For | Status | Blocker? |
|------------|-------------|--------|----------|
| **TICKET-001: PreSTAR XML** | IDE Pre-Sub export | ✅ COMPLETE (v5.25.0) | No |
| `/fda-tools:trials` command | Precedent study discovery | ✅ EXISTS | No |
| `/fda-tools:calc sample-size` | Protocol sample size section | ✅ EXISTS (basic) | No (enhance in Phase 3) |
| `/fda-tools:safety` command | Device risk analysis | ✅ EXISTS | No |
| `/fda-tools:presub` command | IDE Pre-Sub template | ✅ EXISTS (template ready) | No |
| `device_profile.json` schema | Device description auto-population | ✅ EXISTS | No |

### External Dependencies

| Dependency | Purpose | Reliability | Fallback Plan |
|------------|---------|-------------|---------------|
| **ClinicalTrials.gov API v2** | IDE study discovery | HIGH (99%+ uptime) | Cache results; manual search fallback |
| **21 CFR Part 812** | Regulatory framework | STABLE (last amended 2019) | Monitor Federal Register for changes |
| **FDA Guidance Documents** | SR/NSR criteria interpretation | STABLE | Version control guidance documents |
| **OpenFDA Classification API** | Device class/regulation | HIGH (existing dependency) | Use cached classification data |

### Stakeholder Dependencies

| Stakeholder | Dependency | Timeline | Risk |
|-------------|-----------|----------|------|
| **Regulatory Consultant** | SR/NSR validation study | 2-3 weeks | If unavailable, use published case studies only (lower confidence) |
| **IRB System Vendors** | IRB-specific template validation | Optional | Generic template fallback |
| **Biostatistician** | Sample size formula validation | 1 week | Use published FDA guidance formulas (already validated) |
| **Early Adopter Users** | Beta testing feedback | Q2 2026 | Delay Phase 2 if <5 testers recruited |

---

## Recommended Implementation Sequence

### Critical Path Analysis

**Highest Priority (MVP):**
1. **Phase 0: Foundation** (Week 1) - PREREQUISITE
2. **Phase 1: SR/NSR Determination** (Weeks 2-3) - IMMEDIATE VALUE
   - Addresses #1 user pain point (risk classification uncertainty)
   - Low complexity, high impact
   - Enables IDE Pre-Sub generation

**High Priority (Core Deliverables):**
3. **Phase 2: IDE Protocol Generator** (Weeks 4-6) - HIGH VALUE
   - Addresses #2 user pain point (protocol drafting time)
   - Saves 20-30 hours per study
   - Requires Phase 1 SR/NSR determination

**Medium Priority (Enhancements):**
4. **Phase 3: Sample Size Enhancements** (Week 7) - ENABLES PHASE 2
   - Improves protocol generator output quality
   - Extends proven `/fda-tools:calc` architecture
   - Can be parallelized with Phase 4

5. **Phase 4: IRB Package Generator** (Week 8) - NICE-TO-HAVE
   - Lower ROI (saves 8-12 hours, less than protocol generator)
   - Independent of other phases
   - Can be deferred if timeline slips

**Lower Priority (Polish):**
6. **Phase 5: ClinicalTrials.gov Enhanced Integration** (Week 9) - POLISH
   - Incremental improvement to existing `/fda:trials`
   - Can be deferred to post-launch enhancement

### Quarterly Roadmap

**Q2 2026 (Weeks 1-13):**
- **Weeks 1-3:** Phase 0 + Phase 1 (Foundation + SR/NSR)
- **Weeks 4-6:** Phase 2 (IDE Protocol)
- **Week 7:** Phase 3 (Sample Size)
- **Weeks 8-9:** Validation + Beta Release
- **Weeks 10-13:** Beta testing, refinement, documentation

**Q3 2026 (Weeks 14-26):**
- **Week 14:** Production Release (Phases 0-3)
- **Weeks 15-16:** Phase 4 (IRB Package)
- **Weeks 17-18:** Phase 5 (ClinicalTrials.gov)
- **Weeks 19-26:** User feedback, refinements, marketing

**Q4 2026 (Weeks 27-39):**
- **Optional:** Phase 6 (IDE Monitoring Dashboard) - TICKET-008 (out of scope for TICKET-005)
- Focus on user adoption, case studies, enterprise features

### Go/No-Go Decision Points

**After Phase 1 Beta (Week 9):**
- **Criteria:**
  - ≥90% SR/NSR validation accuracy
  - ≥4/5 beta testers find tool valuable
  - No critical bugs identified
- **Decision:** If PASS → Proceed to Phase 2-3 | If FAIL → Refine Phase 1, delay Phase 2

**After Production Release (Week 20):**
- **Criteria:**
  - ≥25 active users
  - User satisfaction ≥4.0/5.0
  - <5 critical support tickets
- **Decision:** If PASS → Proceed to Phase 4-5 | If FAIL → Focus on user adoption, defer enhancements

---

## Resource Requirements

### Development Effort

| Phase | Developer Hours | BA Hours | QA Hours | Total |
|-------|----------------|----------|----------|-------|
| Phase 0 | 8 | 2 | 2 | 12 |
| Phase 1 | 18 | 5 | 7 (validation) | 30 |
| Phase 2 | 30 | 5 | 5 | 40 |
| Phase 3 | 15 | 2 | 3 | 20 |
| Phase 4 | 12 | 3 | 3 | 18 |
| Phase 5 | 8 | 2 | 2 | 12 |
| **TOTAL** | **91** | **19** | **22** | **132** |

### External Resources

| Resource | Purpose | Cost Estimate | Timeline |
|----------|---------|---------------|----------|
| **Regulatory Consultant** | SR/NSR validation study | $3K-5K (10-15 hours @ $300/hr) | Week 8 |
| **IRB System Vendor** | Template validation (optional) | FREE (partnership opportunity) | Weeks 14-16 |
| **Biostatistician** | Sample size formula validation | $1K-2K (4-6 hours @ $250/hr) | Week 7 |
| **Beta Testers** | Phase 1 testing | FREE (incentivize with free license) | Weeks 9-13 |

**Total External Cost:** $4K-7K

### Timeline Summary

- **Fastest Path:** 9 weeks (Phases 0-3 only, parallel development)
- **Realistic Path:** 11-13 weeks (Phases 0-5, with validation)
- **Conservative Path:** 16 weeks (includes beta testing and refinements)

---

## Success Metrics

### Quantitative Metrics

| Metric | Target | Measurement Method | Timeline |
|--------|--------|-------------------|----------|
| **SR/NSR Validation Accuracy** | ≥90% | Validation study (20 test cases) | Week 8 |
| **Phase 1 User Adoption** | ≥5 beta users | Beta signup tracking | Week 9 |
| **User Satisfaction** | ≥4.0/5.0 | Post-use survey (5-point scale) | Week 13 |
| **Time Savings** | ≥40 hours/study | User self-reported time logs | Week 20 |
| **Production Users** | ≥25 active users | Usage analytics | Week 26 |
| **Support Tickets** | <5 critical bugs | Issue tracking system | Ongoing |

### Qualitative Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Regulatory Compliance** | No FDA warning letters | User feedback, legal review |
| **Ease of Use** | "Intuitive, minimal training required" | User interviews |
| **Output Quality** | "80% complete drafts, minimal editing needed" | User feedback |
| **Documentation Quality** | "Clear, actionable guidance" | User feedback |

### Business Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| **Revenue Impact** | $10K-25K (10-25 paid users @ $1K/year) | Q4 2026 |
| **Market Penetration** | 5% of IDE submissions (~50 studies/year in target segment) | 12 months |
| **Competitive Differentiation** | "Only affordable IDE planning tool" | Q3 2026 |

---

## Appendices

### Appendix A: 21 CFR 812 Quick Reference

**21 CFR 812.3(m) - Significant Risk Device:**
> "Significant risk device means an investigational device that:
> (1) Is intended as an implant and presents a potential for serious risk to the health, safety, or welfare of a subject;
> (2) Is purported or represented to be for a use in supporting or sustaining human life and presents a potential for serious risk to the health, safety, or welfare of a subject;
> (3) Is for a use of substantial importance in diagnosing, curing, mitigating, or treating disease, or otherwise preventing impairment of human health and presents a potential for serious risk to the health, safety, or welfare of a subject; or
> (4) Otherwise presents a potential for serious risk to the health, safety, or welfare of a subject."

**21 CFR 812.20 - Application (SR Devices):**
> Required components: (a) Name/address, (b) Prior investigations report, (c) Investigational plan, (d) Device description and manufacturing, (e) Example of agreements, (f) IRB certification, (g) Labeling, (h) Consent materials, (i) Other information requested by FDA.

**21 CFR 812.2(b) - Abbreviated Requirements (NSR Devices):**
> NSR devices must comply with: (1) Labeling per §812.5, (2) Monitoring per §812.46, (3) Records per §812.140(b)(4)-(5), (4) Reports per §812.150(b)(1)-(3), (5)-(10), (5) Prohibition on promotion.

---

### Appendix B: Sample Size Calculation Formulas

**Two-Sample Proportions (Superiority):**
```
n = (Zα/2 + Zβ)² × [p1(1-p1) + p2(1-p2)] / (p1 - p2)²
```

**Equivalence (TOST):**
```
n = (Zα + Zβ)² × 2σ² / δ²
```

**Survival Analysis (Freedman, 1982):**
```
E = (Zα/2 + Zβ)² × 4 / (log(HR))²
n = E / p_event
```

**References:**
- Chow SC, Shao J, Wang H. *Sample Size Calculations in Clinical Research*. 2nd ed. Chapman & Hall/CRC; 2008.
- FDA Guidance: *Design Considerations for Pivotal Clinical Investigations for Medical Devices* (2013)

---

### Appendix C: ClinicalTrials.gov API Examples

**Search for IDE Studies (Device Intervention):**
```
GET https://clinicaltrials.gov/api/v2/studies?query.term=cervical+fusion+AND+AREA[InterventionType]DEVICE&pageSize=20
```

**Filter by Status:**
```
GET https://clinicaltrials.gov/api/v2/studies?query.term=cardiac+stent&filter.overallStatus=COMPLETED&pageSize=20
```

**API Rate Limit:** 50 requests/minute (no authentication required)

---

### Appendix D: Validation Test Case Template

```markdown
# SR/NSR Validation Test Case
**Case ID:** TC-001
**Device Type:** Coronary Drug-Eluting Stent
**Expected Classification:** Significant Risk (SR)

---

## Device Characteristics

**Implanted:** Yes (permanent)
**Life-Supporting:** Yes (coronary artery patency)
**Invasive:** Yes (blood contact)
**Energy Delivery:** No
**Novel Technology:** No (Class III, established device type)

---

## 21 CFR 812.3(m) Analysis

**Criterion 1 (Implant + Serious Risk):** YES
- Device is permanent implant
- Serious risks: thrombosis, restenosis, MI

**Criterion 2 (Life-Supporting):** YES
- Maintains coronary artery patency
- Device failure → myocardial infarction/death

**Criterion 3 (Substantial Importance):** YES
- Primary treatment for coronary artery disease

**Criterion 4 (Otherwise Serious Risk):** N/A (already SR)

---

## Expected Tool Output

**Classification:** Significant Risk (SR)
**Confidence:** HIGH
**Rationale:** Meets criteria 1, 2, and 3

---

## Validation Result

**Tool Output:** [To be filled during validation]
**Match:** [YES/NO]
**Notes:** [Any discrepancies or observations]
```

---

### Appendix E: Related Tickets

| Ticket | Title | Relationship |
|--------|-------|--------------|
| **TICKET-001** | PreSTAR XML Generation | ✅ COMPLETE - Enables IDE Pre-Sub export |
| **TICKET-004** | Pre-Sub Multi-Pathway Enhancement | Related - IDE Pre-Sub is subset of TICKET-004 |
| **TICKET-008** | IDE Monitoring Dashboard | Future enhancement - compliance tracking (out of scope) |
| **TICKET-003** | PMA Intelligence Module | Parallel effort - different regulatory pathway |

---

## Document Control

**Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-17 | Business Analyst (Claude Code) | Initial implementation plan |

**Approvals:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | [TBD] | | |
| Technical Lead | [TBD] | | |
| Regulatory Affairs | [TBD] | | |

**Next Steps:**

1. **Review this plan** with Product Owner and Technical Lead
2. **Prioritize phases** based on business needs and resource availability
3. **Recruit beta testers** for Phase 1 validation (target: 5 users by Week 9)
4. **Schedule kickoff** for Phase 0 (Foundation) - estimated Week 1 start
5. **Assign development resources** (1 developer + 1 QA for 11 weeks)

---

**Contact:** Business Analyst Team
**Document Location:** `/home/linux/.claude/plugins/marketplaces/fda-tools/TICKET-005-IDE-PATHWAY-IMPLEMENTATION-PLAN.md`
**Status:** READY FOR REVIEW
