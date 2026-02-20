# TICKET-020: Verification Framework Specification
## QMS-Compliant Standards Determination Verification

**Document Version:** 1.0
**Date:** 2026-02-15
**Status:** DRAFT SPECIFICATION
**Author:** Senior QMS Auditor
**Regulatory Basis:** 21 CFR 820.30, ISO 13485:2016 Section 7.3.6

---

## Executive Summary

This specification defines a QMS-compliant verification framework for AI-generated FDA consensus standards determinations. The framework ensures compliance with 21 CFR 820.30(c) design verification requirements by requiring human expert verification with objective evidence documentation.

**Critical Regulatory Finding from Expert Panel:**
> "During FDA audit, I can't say 'An AI told me.' I need TRACEABLE RATIONALE with design-specific justification backed by risk assessment, material data, or guidance citations. The AI skips objective evidence entirely." — QA Director, 15+ years experience

**Core Requirement:** Tool output = DRAFT recommendation. User verification = MANDATORY. Objective evidence = AUDIT-READY.

---

## 1. Regulatory Compliance Requirements

### 1.1 21 CFR 820.30(c) — Design Input Requirements

**Regulation Text:**
> "Design input requirements shall be documented and shall be reviewed and approved by a designated individual(s). The approval, including the date and signature of the individual(s) approving the requirements, shall be documented."

**Application to Standards Determination:**
- Standards constitute "design input requirements" under 820.30(c)
- Each standard must have documented rationale (not just "AI said so")
- Rationale must be traceable to:
  - Device-specific risk assessment (ISO 14971)
  - Material characterization data (e.g., biocompatibility for polymers)
  - FDA guidance citations (e.g., 2016 Biocompatibility Guidance)
  - Predicate analysis (what cleared devices tested to)
- Verification must include review and approval by designated individual(s)
- Approval date and signature required (electronic signature acceptable)

**Compliance Evidence Required:**
- [ ] Design input document listing each applicable standard
- [ ] Rationale for inclusion/exclusion of each standard
- [ ] Reference to source documents (risk assessment, guidance, predicates)
- [ ] Review and approval signatures with dates
- [ ] Traceability to device design characteristics

### 1.2 21 CFR 820.30(e) — Design Output Documentation

**Regulation Text:**
> "Design output shall be documented, reviewed, and approved before release. The approval, including the date and signature of the individual(s) approving the output, shall be documented."

**Application to Standards Determination:**
- Final verified standards list = design output
- Cannot release standards list for use until verified and approved
- Must prevent export/use of unverified tool output
- Version control required (distinguish draft vs. approved versions)

**Compliance Evidence Required:**
- [ ] Approved standards list (not draft AI output)
- [ ] Approval signatures and dates
- [ ] Version control (v1.0 DRAFT → v1.1 VERIFIED → v2.0 APPROVED)
- [ ] Release authorization before use in test planning

### 1.3 21 CFR 820.70(i) — Automated Process Validation

**Regulation Text:**
> "Where computers or automated data processing systems are used as part of production or the quality system, the manufacturer shall validate computer software for its intended use according to an established protocol."

**Application to AI Standards Generation:**
- AI tool = automated process used in quality system (design controls)
- Must validate software accuracy per established protocol
- Validation must include:
  - Installation Qualification (IQ): Software installed correctly
  - Operational Qualification (OQ): Software operates per specifications
  - Performance Qualification (PQ): Software produces accurate results
- Accuracy metrics required (not just claims of "95% accuracy")
- Validation report required for DHF

**Compliance Evidence Required (See TICKET-017):**
- [ ] Validation protocol (IQ/OQ/PQ)
- [ ] Test cases with known correct answers (500+ product codes)
- [ ] Actual accuracy metrics (precision, recall, F1 score)
- [ ] Worst-case testing (edge cases: combination products, novel materials)
- [ ] Validation report signed by Quality Assurance

### 1.4 21 CFR 820.75 — Process Validation Documentation

**Regulation Text:**
> "Where the results of a process cannot be fully verified by subsequent inspection and test, the process shall be validated with a high degree of assurance and approved according to established procedures."

**Application to Standards Determination:**
- Standards determination = process with long verification lag
  - Cannot verify correctness until FDA review (6-12 months later)
  - If wrong standard identified, cannot detect until RTA or deficiency
- Therefore, process requires high degree of assurance = validation
- Validation records must be maintained in DHF

**Compliance Evidence Required:**
- [ ] Process validation master plan
- [ ] Validation protocol execution records
- [ ] Statistical evidence of process capability
- [ ] Revalidation triggers (e.g., software updates, database changes)

### 1.5 ISO 13485:2016 Section 7.3.6 — Design Verification

**Standard Text:**
> "Design and development verification shall be performed in accordance with planned arrangements to ensure that the design and development outputs meet the design and development input requirements. Records of the results and conclusions of the verification and any necessary actions shall be maintained."

**Application to Standards Determination:**
- Verification = confirming standards list meets device requirements
- Planned arrangements = verification checklist and procedure
- Records must document:
  - What was verified (each standard)
  - How it was verified (reference sources)
  - Results (applicable / not applicable)
  - Conclusions (approved list)
  - Actions (if discrepancies found)

**Compliance Evidence Required:**
- [ ] Verification plan (procedure for verifying standards)
- [ ] Verification records (completed checklist per standard)
- [ ] Results and conclusions documented
- [ ] Actions for discrepancies (e.g., "AI missed ISO 10993-4, added per risk assessment")
- [ ] Verification approval (signature and date)

---

## 2. Verification Workflow Definition

### 2.1 Workflow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: AI GENERATION (Automated)                             │
├─────────────────────────────────────────────────────────────────┤
│ 1. Tool analyzes device characteristics (product code, class)   │
│ 2. Tool queries knowledge base and FDA database                 │
│ 3. Tool generates DRAFT standards list with confidence levels   │
│ 4. Tool creates verification checklist for each standard        │
│ 5. Status: UNVERIFIED - Cannot be used for FDA submission       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: HUMAN VERIFICATION (Manual - RA Professional)         │
├─────────────────────────────────────────────────────────────────┤
│ 1. RA professional receives draft list + verification checklist │
│ 2. For EACH standard, RA professional verifies:                 │
│    a. Standard is FDA-recognized (check FDA database)           │
│    b. Standard is current version (not superseded)              │
│    c. Standard is applicable (check risk assessment)            │
│    d. Standard is justified (cite predicates/guidance)          │
│ 3. RA professional documents verification rationale             │
│ 4. RA professional signs verification checklist                 │
│ 5. Status: VERIFIED - Awaiting final approval                   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: SME REVIEW (Manual - Subject Matter Experts)          │
├─────────────────────────────────────────────────────────────────┤
│ 1. Biocompatibility expert reviews ISO 10993 determinations     │
│ 2. Electrical safety expert reviews IEC 60601 determinations    │
│ 3. Mechanical engineer reviews ASTM mechanical standards        │
│ 4. Each expert signs off on their domain                        │
│ 5. Status: SME-REVIEWED - Awaiting QA approval                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 4: QA APPROVAL (Manual - Quality Assurance)              │
├─────────────────────────────────────────────────────────────────┤
│ 1. QA reviews verification completeness                         │
│ 2. QA checks all signatures present                             │
│ 3. QA verifies traceability to risk assessment                  │
│ 4. QA approves final standards list                             │
│ 5. Status: APPROVED - Ready for DHF and test planning           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 5: DHF INTEGRATION (Automated + Manual)                  │
├─────────────────────────────────────────────────────────────────┤
│ 1. Tool generates objective evidence package                    │
│ 2. Tool exports verification records to DHF folder              │
│ 3. Tool creates traceability matrix entry                       │
│ 4. RA professional files in DHF Section 4 (Design Input)        │
│ 5. Status: DHF-FILED - Audit-ready                              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Step-by-Step Procedure

#### Step 1: Tool Generates Draft Standards List (Automated)

**Inputs:**
- Device profile (product code, device class, materials, contact duration)
- Risk assessment (if available)
- Predicate analysis (if available)

**Process:**
1. Tool queries FDA standards database
2. Tool applies keyword matching or AI analysis
3. Tool assigns confidence levels (HIGH/MEDIUM/LOW)
4. Tool generates DRAFT standards list JSON

**Outputs:**
- `standards_draft.json` (UNVERIFIED status)
- `verification_checklist.md` (one per standard)

**Status:** UNVERIFIED - Do not use for FDA submissions

---

#### Step 2: RA Professional Receives Verification Checklist (Notification)

**Notification Email Template:**
```
Subject: ACTION REQUIRED - Verify Standards Determination for [Device Name]

Dear [RA Professional Name],

The AI standards generation tool has completed a draft standards determination
for [Device Name] (Product Code: [CODE], Class: [CLASS]).

STATUS: UNVERIFIED - NOT READY FOR FDA SUBMISSION

ACTION REQUIRED:
1. Review draft standards list: [Link to standards_draft.json]
2. Complete verification checklist for each standard
3. Document verification rationale
4. Sign and date verification checklist
5. Submit for SME review

DEADLINE: [5 business days from generation]

WARNING: Do NOT use unverified standards list for test planning, DHF
documentation, or FDA submissions. Verification is MANDATORY per 21 CFR 820.30(c).

[Link to Verification Dashboard]
```

**RA Professional Responsibilities:**
- Review draft list within 5 business days
- Complete verification checklist (see Section 3)
- Document rationale for each standard
- Escalate discrepancies (AI errors) to development team
- Sign verification checklist

---

#### Step 3: RA Professional Verifies Each Standard (Manual Execution)

**For EACH standard in draft list, RA professional executes verification checklist:**

See Section 3 (Verification Checklist Design) for detailed checklist template.

**Key Verification Steps:**
1. Verify standard number format is correct (e.g., "ISO 10993-1:2018")
2. Check FDA Recognition Database (is standard currently recognized?)
3. Check version currency (is this the latest recognized version or superseded?)
4. Check applicability to device type (does our device match standard scope?)
5. Check requirement status (required by regulation, guidance, or predicate precedent?)
6. Document traceable reasoning (cite risk assessment, guidance, or predicate K-number)

**Time Estimate:**
- Universal standards (ISO 13485, ISO 14971): 5-10 minutes each (simple verification)
- Device-specific standards (ISO 10993-4, ASTM F1717): 20-30 minutes each (requires risk assessment review)
- Novel/complex standards: 30-60 minutes (may require SME consultation)

**Outputs:**
- Completed verification checklist for each standard (signed and dated)
- Discrepancy log (if AI errors found)
- Updated `standards_verified.json` (VERIFIED status)

---

#### Step 4: RA Professional Documents Verification Results (Objective Evidence)

**For each standard, RA professional creates objective evidence documentation:**

See Section 4 (Objective Evidence Requirements) for detailed template.

**Required Documentation:**
- Verification checklist (completed)
- Reference sources cited (FDA guidance title, predicate K-number, risk assessment section)
- Verification date and time
- Verifier identification (name, credentials, signature)
- Discrepancy resolution (if tool output was incorrect)

**Example Discrepancy Resolution:**
```markdown
## Discrepancy Report: ISO 10993-4 Missing from AI Output

**Standard:** ISO 10993-4:2017 (Selection of tests for interactions with blood)

**AI Determination:** NOT RECOMMENDED (not in draft list)

**RA Professional Determination:** REQUIRED

**Rationale:**
- Device has blood contact (intravascular catheter, 21 days max contact duration)
- Risk assessment REQ-BIO-003 identifies thrombogenicity as Medium risk (P2 × S3)
- Predicate K240123 cites ISO 10993-4 (full hemocompatibility panel)
- FDA 2016 Biocompatibility Guidance Section 5.4 requires blood-contacting devices ≥24 hours

**Action Taken:**
- Added ISO 10993-4:2017 to verified standards list
- Notified development team of AI error (keyword "blood contact" may not trigger)
- Filed discrepancy in TICKET-017 validation error log

**Approved By:** [RA Manager Name], [Date]
```

---

#### Step 5: RA Professional Signs Off on Verification (Accountability)

**Verification Sign-Off Requirements:**

**Signature Block Template:**
```markdown
## Verification Approval

I certify that I have reviewed the AI-generated draft standards determination
for [Device Name] and have independently verified each standard against:
- FDA Recognized Consensus Standards Database
- Device-specific risk assessment (ISO 14971)
- Recent cleared predicate devices (K-numbers: [list])
- Applicable FDA guidance documents

I confirm that the VERIFIED standards list represents my professional judgment
as a qualified Regulatory Affairs professional and is suitable for inclusion
in the Design History File.

Verifier Name: ________________________________
Credentials: RA/C, [Degree], [Years Experience]
Signature: ____________________________________
Date: _________________________________________

Discrepancies Found: [X] None  [ ] See Discrepancy Log
```

**Credentials Requirement:**
- RA/C (Regulatory Affairs Certification) OR
- 3+ years FDA regulatory experience OR
- Engineering degree + 2+ years medical device experience

**Independence Requirement:**
- Verifier must NOT be the developer of the AI tool
- Verifier must NOT have financial interest in tool performance metrics
- Verifier must be different person than QA approver (segregation of duties)

---

#### Step 6: Verification Record Stored in DHF (Traceability)

**DHF Filing Procedure:**

**DHF Location:**
```
Design History File (DHF)/
├── 01_Design_Planning/
├── 02_Design_Input/
│   ├── Device_Requirements_Specification.pdf
│   ├── Risk_Management_File.pdf
│   └── Standards_Determination/
│       ├── standards_verified.json (APPROVED version)
│       ├── verification_checklist_ISO-10993-1.pdf
│       ├── verification_checklist_ISO-14971.pdf
│       ├── verification_checklist_IEC-60601-1.pdf
│       ├── objective_evidence_summary.pdf
│       └── verification_approval_signatures.pdf
├── 03_Design_Output/
├── 04_Design_Verification/
├── 05_Design_Validation/
└── 06_Design_Transfer/
```

**File Naming Convention:**
```
[PROJECT_CODE]_STANDARDS_VERIFICATION_[DATE].pdf

Example: DQY-2024-001_STANDARDS_VERIFICATION_2026-02-15.pdf
```

**Metadata Requirements:**
- Document Type: Design Input - Standards Determination
- Document Number: Auto-generated (DHF-02-STD-001)
- Version: 1.0 APPROVED
- Date: [Verification completion date]
- Author: [RA Professional Name]
- Approver: [QA Manager Name]
- Linked Documents:
  - Risk Management File (DHF-02-RISK-001)
  - Device Requirements Specification (DHF-02-REQ-001)
  - Requirements Traceability Matrix (DHF-10-RTM-001)

**Audit Trail:**
- Document creation timestamp
- Document modification history (if revised)
- Access log (who viewed, when)
- Approval workflow (RA → SME → QA)

---

## 3. Verification Checklist Design

### 3.1 Universal Standards Checklist Template

**For standards applicable to ALL devices (ISO 13485, ISO 14971, ISO 10993-1):**

```markdown
# Verification Checklist: [Standard Number]

**Device:** [Device Name] (Product Code: [CODE], Class: [CLASS])
**Standard:** [Standard Number:Version]
**Standard Title:** [Full Title]
**AI Confidence:** [HIGH / MEDIUM / LOW]
**Verification Date:** [YYYY-MM-DD]
**Verifier:** [RA Professional Name]

---

## 1. Standard Number Format Verification

☐ Standard number matches FDA naming convention (e.g., "ISO 10993-1:2018")
☐ Standard number matches organization format (ISO/IEC/ASTM/AAMI/ANSI)
☐ Edition year included in citation (required for traceability)

**Result:** ☐ PASS  ☐ FAIL - Correction: _______________

---

## 2. FDA Recognition Verification

☐ Checked FDA Recognized Consensus Standards Database (https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/search.cfm)

**Search Results:**
- Standard Number: _______________________
- Recognition Date: _______________________
- Recognition List: _____ (e.g., List 63)
- Status: ☐ Currently Recognized  ☐ Withdrawn  ☐ Superseded

**FDA Database URL:** [Paste direct link to FDA record]

**Result:** ☐ PASS - FDA-recognized  ☐ FAIL - Not FDA-recognized or withdrawn

---

## 3. Version Currency Verification

☐ Checked if newer version exists (search standard organization website)

**Version Analysis:**
- Version in draft list: _______________________
- Latest FDA-recognized version: _______________________
- Newer version exists (not FDA-recognized yet)? ☐ Yes ☐ No

**Supersession Status:**
- ☐ Current version (use this)
- ☐ Superseded version (update to newer FDA-recognized version)
- ☐ Legacy version (acceptable under grandfather clause)

**Result:** ☐ PASS - Current version  ☐ FAIL - Update version to: _______________

---

## 4. Applicability to Device Type

☐ Reviewed standard scope statement (Section 1 of standard)
☐ Compared device characteristics to scope

**Device Characteristics Relevant to This Standard:**
- Device classification: Class _____
- Patient contact: ☐ Yes ☐ No - Duration: _____________
- Sterile: ☐ Yes ☐ No
- Powered: ☐ Yes ☐ No
- Software: ☐ Yes ☐ No
- Implantable: ☐ Yes ☐ No
- Reusable: ☐ Yes ☐ No

**Standard Scope Match Analysis:**
[Explain why this standard applies to this specific device type]

**Predicate Comparison:**
Checked 3-5 recent predicates in same product code:
- K______: ☐ Cites this standard  ☐ Does not cite
- K______: ☐ Cites this standard  ☐ Does not cite
- K______: ☐ Cites this standard  ☐ Does not cite

**Predicate Frequency:** ___% of checked predicates cite this standard

**Result:** ☐ APPLICABLE  ☐ NOT APPLICABLE - Justification: _______________

---

## 5. Required vs. Optional Determination

☐ Checked if standard is MANDATORY per regulation
☐ Checked if standard is EXPECTED per FDA guidance
☐ Checked if standard is COMMON PRACTICE per predicates

**Regulatory Requirement Analysis:**

**Is this standard REQUIRED by regulation?**
☐ Yes - Citation: 21 CFR _______________
☐ No - Not explicitly required by regulation

**Is this standard EXPECTED per FDA guidance?**
☐ Yes - Guidance: _______________
☐ No - Not mentioned in guidance

**Is this standard COMMON PRACTICE per predicates?**
☐ Yes - ___% of predicates cite this standard
☐ No - Rare or device-specific

**Determination:**
- ☐ REQUIRED (must include in test plan)
- ☐ RECOMMENDED (strong expectation, should include)
- ☐ OPTIONAL (acceptable if justified by risk assessment)

**Result:** [REQUIRED / RECOMMENDED / OPTIONAL]

---

## 6. Traceable Reasoning Documentation

**Rationale for Inclusion/Exclusion of This Standard:**

[Provide device-specific justification with reference to objective sources]

**Reference Sources (cite at least 2):**
1. Risk Assessment: [Section/Hazard ID] - [Brief summary]
2. FDA Guidance: [Title and date] - [Section reference]
3. Predicate Analysis: [K-number] - [Standard citation in Section 17]
4. Material Data: [Material characterization report reference]
5. Other: _______________________

**Example for ISO 10993-1:**
```
This device is a Class II intravascular catheter with blood contact <24 hours.
Per risk assessment REQ-BIO-001, biocompatibility is a Medium risk (P2 × S3).
FDA's 2016 Biocompatibility Guidance Section 4.1 requires all patient-contacting
devices to follow ISO 10993-1 framework. Predicates K240123, K233456, and K232789
all cite ISO 10993-1:2018. This standard is REQUIRED and APPLICABLE.
```

**Discrepancy with AI Output:**
☐ No discrepancy - AI correctly identified this standard
☐ Discrepancy - AI error: [Describe error and correction]

---

## 7. Verification Approval

**Verification Conclusion:**
☐ Standard is VERIFIED and APPROVED for inclusion in test plan
☐ Standard is VERIFIED as NOT APPLICABLE (exclude from test plan)
☐ Standard requires FURTHER REVIEW by SME before approval
☐ Standard determination is INCORRECT - Escalate to development team

**Verifier Certification:**

I certify that I have independently verified this standard determination using
the methods described in this checklist and that my determination is based on
objective evidence documented above.

Verifier Name: ________________________________
Signature: ____________________________________
Date: _________________________________________

---

## 8. SME Review (If Applicable)

**SME Required For:**
☐ Biocompatibility standards (ISO 10993 series)
☐ Electrical safety standards (IEC 60601 series)
☐ Software standards (IEC 62304, IEC 82304)
☐ Mechanical standards (ASTM F1717, etc.)
☐ Sterilization standards (ISO 11135, ISO 17665)

**SME Review:**

SME Name: ________________________________
SME Credentials: ________________________________
SME Determination: ☐ CONCUR  ☐ DISAGREE - Comments: _______________
SME Signature: ____________________________________
Date: _________________________________________

---

## 9. Checklist Completion Summary

**Overall Verification Status:**
☐ VERIFIED - APPROVED for use
☐ VERIFIED - NOT APPLICABLE
☐ VERIFICATION FAILED - Requires correction

**Next Steps:**
☐ File in DHF Section 02 (Design Input)
☐ Link to Requirements Traceability Matrix
☐ Include in test plan development
☐ Escalate discrepancy to development team

**Checklist Completed By:** ________________________________
**Date:** _________________________________________
```

---

### 3.2 Device-Specific Standards Checklist Template

**For standards requiring device-specific analysis (ISO 10993-4, ASTM F1717):**

Add these additional sections to Universal Checklist:

```markdown
## 10. Device-Specific Applicability Analysis

**Device Design Characteristics Triggering This Standard:**

[Describe specific design features that trigger this standard requirement]

**Examples:**
- ISO 10993-4: Blood contact pathway (intravascular placement)
- ASTM F1717: Spinal implant construct (load-bearing fixation)
- IEC 60601-2-24: Infusion pump (fluid delivery mechanism)

**Risk Assessment Cross-Reference:**

Hazard ID(s) that this standard addresses:
- Hazard ID: _____ - Description: _______________ - Risk Score: _____
- Hazard ID: _____ - Description: _______________ - Risk Score: _____

**Material Characterization Cross-Reference (if biocompatibility standard):**

Materials in device requiring this testing:
- Material 1: _____ - Patient contact: _____ - Contact duration: _____
- Material 2: _____ - Patient contact: _____ - Contact duration: _____

---

## 11. Standard Sections Applicability

**This standard has multiple sections/parts. Which apply to this device?**

[For ISO 10993-1, list applicable endpoints]
[For IEC 60601-1, list applicable clauses]
[For ASTM standards, list applicable test methods]

**Example for ISO 10993-1:**
☐ 5.1 Cytotoxicity - REQUIRED (all patient-contacting devices)
☐ 5.2 Sensitization - REQUIRED (all patient-contacting devices)
☐ 5.3 Irritation - REQUIRED (mucosal membrane contact)
☐ 5.4 Acute systemic toxicity - NOT APPLICABLE (no systemic exposure pathway)
☐ 5.5 Subacute/subchronic toxicity - REQUIRED (contact >24 hours)
☐ 5.6 Genotoxicity - REQUIRED (all patient-contacting devices)
☐ 5.7 Implantation - NOT APPLICABLE (not implantable)
☐ 5.8 Hemocompatibility - REQUIRED (blood-contacting device)

---

## 12. Alternative Methods Evaluation

**Are there alternative consensus standards or FDA-accepted methods?**

☐ No alternatives - This standard is the only recognized method
☐ Alternatives exist:
   - Alternative 1: _____ - Why not selected: _____
   - Alternative 2: _____ - Why not selected: _____

**Can this standard be fulfilled by literature review instead of testing?**

☐ Testing required (no literature exemption)
☐ Literature may be acceptable - Criteria: _______________ (see FDA 2016 Biocompat Guidance)

---

## 13. Predicate Testing Detail Analysis

**For predicates that cite this standard, what testing was performed?**

Predicate K______:
- Test method: _______________________
- Test lab: _______________________
- Sample size: _______________________
- Results summary: _______________________

Predicate K______:
- Test method: _______________________
- Test lab: _______________________
- Sample size: _______________________
- Results summary: _______________________

**Conclusion:**
☐ Our device should test similarly to predicates (standard practice)
☐ Our device may need more rigorous testing (higher risk)
☐ Our device may need less testing (lower risk or literature support)
```

---

## 4. Objective Evidence Requirements

### 4.1 Objective Evidence Package Contents

For EACH verified standard, the following objective evidence must be compiled:

**1. Completed Verification Checklist**
- All checkboxes completed
- All questions answered
- Signature and date present
- SME review (if applicable)

**2. Reference Source Documentation**
- Screenshot or PDF of FDA Recognition Database entry (with URL)
- Copy of relevant FDA guidance section (with citation)
- Copy of predicate 510(k) summary Section 17 (standards citations)
- Excerpt from risk assessment (hazard-standard linkage)
- Material characterization data (if biocompatibility standard)

**3. Verification Date and Time**
- Timestamp when verification completed
- Version of FDA database checked (List number and effective date)
- Version of AI tool used to generate draft (for traceability)

**4. Verifier Identification**
- Name, credentials (RA/C, degree, years experience)
- Electronic signature (acceptable per 21 CFR Part 11)
- Contact information (for audit inquiries)

**5. Discrepancy Resolution Documentation**
- If AI output was incorrect, document what was changed
- Rationale for change (why AI was wrong)
- Corrective action taken (notify development team)
- Impact assessment (did error affect other determinations?)

**6. Final Approved Standards List**
- JSON file with APPROVED status
- Version control (v2.0 APPROVED, not v1.0 DRAFT)
- Approval signatures (RA professional, SME, QA)
- Effective date (when approved for use)

---

### 4.2 Objective Evidence Template

```markdown
# Objective Evidence: Standards Determination Verification
## [Device Name] - [Product Code]

**Document Number:** DHF-02-STD-001
**Version:** 2.0 APPROVED
**Effective Date:** [YYYY-MM-DD]
**Prepared By:** [RA Professional Name]
**Approved By:** [QA Manager Name]

---

## 1. Device Identification

**Device Name:** _______________________
**Product Code:** _______________________
**Device Class:** Class _____
**Regulation Number:** 21 CFR _______________
**Intended Use:** [Brief summary]
**Key Device Characteristics:**
- Patient contact: ☐ Yes ☐ No - Duration: _____________
- Sterile: ☐ Yes ☐ No
- Powered: ☐ Yes ☐ No
- Implantable: ☐ Yes ☐ No

---

## 2. Standards Determination Summary

**Total Standards Identified:** _____
**Breakdown:**
- Required by regulation: _____
- Expected per FDA guidance: _____
- Common practice per predicates: _____
- Device-specific risk mitigation: _____

**AI Tool Performance:**
- Correctly identified: _____
- False positives (AI over-applied): _____
- False negatives (AI missed): _____
- Accuracy: _____%

---

## 3. Verification Methodology

**Verification Date:** [YYYY-MM-DD]
**FDA Database Checked:** Recognized Consensus Standards, List ___ (effective [date])
**Predicates Analyzed:** [List K-numbers]
**Risk Assessment Version:** [Document number and version]
**FDA Guidance Referenced:** [List guidance documents]

**Verification Procedure:**
1. For each standard in AI draft list, completed verification checklist
2. Cross-checked FDA Recognition Database for recognition status
3. Reviewed 3-5 recent predicate 510(k) summaries (Section 17)
4. Linked standards to device-specific risk assessment hazards
5. Consulted SMEs for biocompatibility and electrical safety standards
6. Documented rationale for inclusion/exclusion of each standard

---

## 4. Standards Verification Results

### 4.1 Universal Standards (Required for All Devices)

| Standard | AI Confidence | Verification Result | Rationale |
|----------|---------------|---------------------|-----------|
| ISO 13485:2016 | HIGH | ✅ VERIFIED - REQUIRED | QMS foundational standard, required for all manufacturers |
| ISO 14971:2019 | HIGH | ✅ VERIFIED - REQUIRED | Risk management required per FDA guidance and regulations |
| ISO 10993-1:2018 | HIGH | ✅ VERIFIED - REQUIRED | Patient contact device, biocompatibility framework required |

### 4.2 Device-Specific Standards

| Standard | AI Confidence | Verification Result | Rationale |
|----------|---------------|---------------------|-----------|
| ISO 10993-4:2017 | MEDIUM | ✅ VERIFIED - REQUIRED | Blood contact, hemocompatibility required per risk REQ-BIO-003 |
| IEC 60601-1:2005+A2 | HIGH | ✅ VERIFIED - REQUIRED | Powered device, electrical safety required per 21 CFR 898.12 |
| ASTM F2394:2021 | LOW | ✅ VERIFIED - REQUIRED | Catheter tensile strength, cited by 81% of predicates (38/47) |
| ISO 10993-11:2017 | HIGH | ❌ NOT APPLICABLE | Contact <24 hours, systemic toxicity not required per 2016 Guidance |

### 4.3 Standards Missed by AI (False Negatives)

| Standard | AI Confidence | Verification Result | Rationale |
|----------|---------------|---------------------|-----------|
| ISO 11070:2015 | NOT RECOMMENDED | ⚠️ ADDED - REQUIRED | Vascular access devices, cited by 98% of DQY predicates (46/47) |

**Discrepancy Analysis:**
AI missed ISO 11070 due to database gap (not in 54-standard core database).
This is a DQY-specific standard commonly cited by predicates.
Development team notified via TICKET-018 (expand FDA database coverage).

---

## 5. Traceability to Device Design

### 5.1 Risk Assessment Linkage

Each standard linked to specific hazards in Risk Management File:

| Standard | Hazard ID | Hazard Description | Risk Score | Risk Control |
|----------|-----------|-------------------|------------|--------------|
| ISO 10993-4 | REQ-BIO-003 | Thrombogenicity from polymer leachables | P2 × S3 = 6 | Hemocompatibility testing |
| IEC 60601-1 | REQ-ELEC-001 | Electric shock from powered components | P1 × S4 = 4 | Electrical safety testing |
| ASTM F2394 | REQ-MECH-005 | Catheter breakage during insertion | P2 × S3 = 6 | Tensile strength testing |

### 5.2 Material Characterization Linkage

Biocompatibility standards linked to device materials:

| Standard | Material | Patient Contact | Contact Duration | Contact Type |
|----------|----------|-----------------|------------------|--------------|
| ISO 10993-1 | Medical-grade silicone | Yes | <24 hours | Blood (intravascular) |
| ISO 10993-4 | Polyurethane coating | Yes | <24 hours | Blood (intravascular) |
| ISO 10993-5 | Both materials | Yes | <24 hours | In vitro cytotoxicity |

### 5.3 Predicate Analysis Summary

**Predicates Reviewed:** K240123, K233456, K232789, K231045, K224567

**Standards Frequency Analysis:**

| Standard | Predicate Frequency | Industry Norm |
|----------|---------------------|---------------|
| ISO 13485 | 47/47 (100%) | Universal |
| ISO 14971 | 47/47 (100%) | Universal |
| ISO 10993-1 | 46/47 (98%) | Near-universal |
| ISO 11070 | 46/47 (98%) | DQY-specific, near-universal |
| ASTM F2394 | 38/47 (81%) | DQY-specific, common |
| ISO 10993-4 | 35/47 (74%) | Blood-contacting DQY devices |
| IEC 60601-1 | 12/47 (26%) | Powered DQY devices only |

**Conclusion:**
Our device standards list aligns with predicate norms. All standards cited by ≥70%
of predicates are included. Standards cited by <30% are included only if device-specific
characteristics apply (e.g., IEC 60601-1 because our device is powered).

---

## 6. SME Review Documentation

### 6.1 Biocompatibility Standards Review

**SME:** Dr. [Name], Biocompatibility Toxicologist, [Credentials]
**Review Date:** [YYYY-MM-DD]

**Standards Reviewed:**
- ISO 10993-1:2018 - Biocompatibility framework
- ISO 10993-4:2017 - Hemocompatibility
- ISO 10993-5:2009 - Cytotoxicity
- ISO 10993-10:2021 - Sensitization

**SME Determination:**
☑ CONCUR with RA professional's determination
☐ DISAGREE - Comments: _______________

**SME Rationale:**
"Device has intravascular blood contact <24 hours. ISO 10993-1 framework is appropriate.
Hemocompatibility (ISO 10993-4) is required due to blood contact. Cytotoxicity (ISO 10993-5)
and sensitization (ISO 10993-10) are required for all patient-contacting devices per
FDA 2016 Biocompatibility Guidance. Systemic toxicity (ISO 10993-11) is NOT required
for short-term contact <24 hours per Table 1 of 2016 Guidance. Determination is correct."

**SME Signature:** _______________
**Date:** _______________

### 6.2 Electrical Safety Standards Review

**SME:** [Name], Electrical Engineer, PE, [Credentials]
**Review Date:** [YYYY-MM-DD]

**Standards Reviewed:**
- IEC 60601-1:2005+A2:2020 - General electrical safety
- IEC 60601-1-2:2014 - EMC requirements

**SME Determination:**
☑ CONCUR with RA professional's determination
☐ DISAGREE - Comments: _______________

**SME Rationale:**
"Device is powered (battery-operated pump). IEC 60601-1 general requirements apply.
IEC 60601-1-2 EMC applies due to electronic components. No particular standard
(IEC 60601-2-24 for infusion pumps) applies because device is not an infusion pump
per se (catheter with integrated sensor). Determination is correct."

**SME Signature:** _______________
**Date:** _______________

---

## 7. Discrepancy Log

### 7.1 AI False Negative: ISO 11070 (Missed Standard)

**Standard:** ISO 11070:2015 (Vascular access devices)
**AI Determination:** NOT RECOMMENDED (not in draft list)
**RA Professional Determination:** REQUIRED

**Discrepancy Analysis:**
- AI tool uses 54-standard core database
- ISO 11070 is NOT in core database (database coverage gap)
- ISO 11070 is DQY-specific, cited by 98% of predicates
- This is a systematic error affecting all DQY devices

**Corrective Action:**
- Added ISO 11070 to verified standards list
- Notified development team (TICKET-018: Expand FDA database to 1,900+ standards)
- Filed error in AI validation log (TICKET-017 tracking)

**Impact Assessment:**
- Affects ALL DQY product code determinations
- High severity (missing a near-universal DQY standard could delay FDA clearance)

### 7.2 AI False Positive: ISO 10993-11 (Over-Applied Standard)

**Standard:** ISO 10993-11:2017 (Systemic toxicity)
**AI Determination:** HIGH confidence - REQUIRED
**RA Professional Determination:** NOT APPLICABLE

**Discrepancy Analysis:**
- AI recommends ISO 10993-11 for all patient-contacting devices
- FDA 2016 Biocompatibility Guidance Table 1: Systemic toxicity required for contact ≥24 hours
- Our device: Contact <24 hours (short-term use)
- AI over-applied standard (did not check contact duration)

**Corrective Action:**
- Removed ISO 10993-11 from verified standards list
- Documented rationale: Contact <24 hours per FDA Guidance Table 1
- Notified development team (AI logic needs contact duration parameter)

**Impact Assessment:**
- Low severity (removing unnecessary test saves $20K-$35K)
- Good catch by verification process (prevents over-testing)

---

## 8. Final Approved Standards List

### 8.1 Required Standards (Must Test/Comply)

| Standard | Category | Regulatory Basis | Estimated Cost | Lead Time |
|----------|----------|------------------|----------------|-----------|
| ISO 13485:2016 | QMS | All manufacturers | Integrated QMS | N/A |
| ISO 14971:2019 | Risk Management | All devices | Internal process | N/A |
| ISO 10993-1:2018 | Biocompatibility Framework | Patient contact | $0 (framework only) | N/A |
| ISO 10993-4:2017 | Hemocompatibility | Blood contact | $35K-$50K | 8-12 weeks |
| ISO 10993-5:2009 | Cytotoxicity | Patient contact | $8K-$12K | 2-3 weeks |
| ISO 10993-10:2021 | Sensitization | Patient contact | $12K-$18K | 4-6 weeks |
| IEC 60601-1:2005+A2 | Electrical Safety | Powered device | $25K-$40K | 4-6 weeks |
| IEC 60601-1-2:2014 | EMC | Powered device | $15K-$25K | 4-6 weeks |
| ASTM F2394:2021 | Tensile Strength | Catheter | $10K-$15K | 3-4 weeks |
| ISO 11070:2015 | Vascular Access | DQY product code | $5K-$8K | 2-3 weeks |

**Total Estimated Testing Cost:** $110K-$178K
**Critical Path Lead Time:** 8-12 weeks (hemocompatibility)

### 8.2 Optional Standards (Not Required, But May Support Equivalence)

| Standard | Rationale for Exclusion | If Included, Benefit |
|----------|-------------------------|----------------------|
| ISO 10993-11:2017 | Contact <24 hours, not required per FDA Guidance | Additional safety margin for systemic toxicity |
| ISO 10993-18:2020 | Chemical characterization, can use literature | Comprehensive leachables data |

---

## 9. Verification Approval

### 9.1 RA Professional Certification

I certify that I have independently verified each standard determination using
the verification checklists and objective evidence documented in this package.
I confirm that the APPROVED standards list is suitable for inclusion in the
Design History File and use in test planning.

**RA Professional Name:** ________________________________
**Credentials:** RA/C, [Degree], [Years Experience]
**Signature:** ____________________________________
**Date:** _________________________________________

### 9.2 QA Manager Approval

I have reviewed the verification package for completeness and compliance with
21 CFR 820.30 design control requirements. I approve this standards determination
for release as Design Input documentation.

**QA Manager Name:** ________________________________
**Signature:** ____________________________________
**Date:** _________________________________________

### 9.3 DHF Filing Authorization

This document is approved for filing in Design History File Section 02 (Design Input).

**Document Number:** DHF-02-STD-001
**Version:** 2.0 APPROVED
**Effective Date:** [YYYY-MM-DD]
**Filed By:** ________________________________
**Date Filed:** _________________________________________

---

## 10. Audit Readiness Checklist

**FDA Audit Preparation:**

☐ All verification checklists complete with signatures
☐ All reference sources documented with URLs/citations
☐ Discrepancies documented with corrective actions
☐ Traceability to risk assessment established
☐ SME reviews complete for all specialized standards
☐ QA approval obtained
☐ Document filed in DHF with correct numbering
☐ Linked to Requirements Traceability Matrix
☐ Can retrieve this document within 5 minutes during audit

**Audit Question Preparation:**

**Q: "How did you determine ISO 10993-4 was required for this device?"**
A: See Section 5.1 (Risk Assessment Linkage) - Blood contact identified as Medium risk (REQ-BIO-003). See Section 5.3 (Predicate Analysis) - 35/47 blood-contacting DQY predicates cite ISO 10993-4. See Section 6.1 (SME Review) - Biocompatibility toxicologist concurred.

**Q: "Who verified these standards determinations?"**
A: See Section 9.1 - [RA Professional Name], RA/C with [X] years experience. See Section 6 - SME reviews by biocompatibility toxicologist and electrical engineer.

**Q: "Show me the objective evidence for each standard."**
A: See Section 4 (Objective Evidence Package) - Verification checklists, FDA database screenshots, predicate analysis, risk assessment linkage, SME reviews all attached.

**Q: "Did you use an AI tool to generate this list?"**
A: Yes, AI tool generated DRAFT list. Per 21 CFR 820.30(c), we independently VERIFIED each standard with human expert review. See Section 7 (Discrepancy Log) - We caught 2 AI errors (1 false negative, 1 false positive) during verification.

**Q: "How do you know the AI tool is accurate?"**
A: See TICKET-017 Validation Report (separate document). AI tool is validated per 21 CFR 820.70(i) with IQ/OQ/PQ testing on 500+ product codes. Accuracy metrics documented. However, we do NOT rely solely on AI output - all determinations are HUMAN-VERIFIED.

---

**END OF OBJECTIVE EVIDENCE PACKAGE**
```

---

## 5. Verification Tracking System

### 5.1 Status States

```
UNVERIFIED (Draft)
   ↓
VERIFICATION_IN_PROGRESS (RA professional reviewing)
   ↓
VERIFIED_PENDING_SME (Awaiting SME review)
   ↓
SME_REVIEWED_PENDING_QA (Awaiting QA approval)
   ↓
APPROVED (Ready for DHF filing)
   ↓
DHF_FILED (Audit-ready)
   ↓
IN_USE (Referenced in test plans, DHF verification)
```

### 5.2 Verification History Tracking

**JSON Schema for Verification Status:**

```json
{
  "device_name": "Example Intravascular Catheter",
  "product_code": "DQY",
  "standards_determination": {
    "draft_version": {
      "version": "1.0",
      "status": "UNVERIFIED",
      "generated_date": "2026-02-15T10:30:00Z",
      "generated_by": "AI Standards Generation Tool v5.26.0",
      "ai_method": "knowledge_based",
      "total_standards": 12,
      "confidence_breakdown": {
        "HIGH": 8,
        "MEDIUM": 3,
        "LOW": 1
      }
    },
    "verified_version": {
      "version": "2.0",
      "status": "VERIFIED_PENDING_SME",
      "verified_date": "2026-02-20T14:15:00Z",
      "verified_by": "Jane Smith, RA/C",
      "total_standards": 11,
      "changes_from_draft": {
        "added": ["ISO 11070:2015"],
        "removed": ["ISO 10993-11:2017"],
        "unchanged": 10
      },
      "discrepancies": 2,
      "verification_time_hours": 6.5
    },
    "sme_reviewed_version": {
      "version": "2.1",
      "status": "SME_REVIEWED_PENDING_QA",
      "sme_review_date": "2026-02-22T09:00:00Z",
      "sme_biocompatibility": {
        "name": "Dr. John Doe, Toxicologist",
        "determination": "CONCUR",
        "comments": "Biocompatibility standards appropriate for device contact profile"
      },
      "sme_electrical": {
        "name": "Mike Johnson, PE",
        "determination": "CONCUR",
        "comments": "Electrical safety standards correct for powered catheter"
      }
    },
    "approved_version": {
      "version": "3.0",
      "status": "APPROVED",
      "qa_approval_date": "2026-02-25T11:30:00Z",
      "qa_approver": "Sarah Lee, QA Manager",
      "dhf_number": "DHF-02-STD-001",
      "effective_date": "2026-02-25"
    },
    "dhf_filed_version": {
      "version": "3.0",
      "status": "DHF_FILED",
      "filed_date": "2026-02-25T14:00:00Z",
      "filed_by": "Jane Smith, RA/C",
      "dhf_location": "/DHF/02_Design_Input/Standards_Determination/",
      "audit_ready": true
    }
  },
  "verification_metadata": {
    "total_verification_time_hours": 10.5,
    "verifiers": ["Jane Smith (RA)", "Dr. John Doe (SME-Bio)", "Mike Johnson (SME-Elec)", "Sarah Lee (QA)"],
    "predicates_analyzed": ["K240123", "K233456", "K232789", "K231045", "K224567"],
    "fda_database_checked": "FDA Recognized Consensus Standards List 63 (effective 2024-12-22)",
    "discrepancies_found": 2,
    "discrepancies_resolved": 2,
    "audit_readiness_score": 100
  }
}
```

---

### 5.3 Batch Verification Dashboard

**For organizations with multiple devices/projects:**

```markdown
# Standards Verification Dashboard

## Active Verifications

| Device | Product Code | Status | Verifier | Due Date | Progress |
|--------|--------------|--------|----------|----------|----------|
| Catheter A | DQY | VERIFICATION_IN_PROGRESS | Jane Smith | 2026-02-27 | 75% (9/12 standards) |
| Implant B | OVE | UNVERIFIED | Not assigned | 2026-03-05 | 0% (draft generated) |
| Monitor C | DPS | SME_REVIEWED_PENDING_QA | Mike Johnson | 2026-02-26 | 90% (awaiting QA) |

## Verification Backlog

| Device | Product Code | Draft Date | Days Waiting | Priority |
|--------|--------------|------------|--------------|----------|
| Implant B | OVE | 2026-02-14 | 11 days | HIGH |
| Pump D | NBW | 2026-02-20 | 5 days | MEDIUM |

## Completed Verifications (Last 30 Days)

| Device | Product Code | Verified Date | Verifier | Discrepancies | Status |
|--------|--------------|---------------|----------|---------------|--------|
| Catheter A | DQY | 2026-02-25 | Jane Smith | 2 | DHF_FILED |
| Monitor C | DPS | 2026-02-23 | Mike Johnson | 0 | DHF_FILED |

## Discrepancy Trends

| Discrepancy Type | Count (Last 30 Days) | Impact |
|------------------|----------------------|--------|
| False Negative (AI missed standard) | 5 | HIGH - Manual addition required |
| False Positive (AI over-applied) | 3 | MEDIUM - Remove from list |
| Version Error (AI cited superseded version) | 2 | LOW - Update version number |

## AI Tool Performance Metrics

| Metric | Value | Target |
|--------|-------|--------|
| Accuracy (% correct) | 87% | ≥95% (see TICKET-017) |
| False Negative Rate | 8% | <5% |
| False Positive Rate | 5% | <5% |
| Average Verification Time | 6.5 hours | <4 hours |
```

---

### 5.4 Re-Verification Triggers

**When must standards determinations be RE-VERIFIED?**

**Trigger 1: AI Tool Software Update**
- If AI tool is updated (new version), all UNVERIFIED drafts must be regenerated
- Previously APPROVED standards lists are grandfathered (do not re-verify unless device changes)

**Trigger 2: FDA Database Update**
- If FDA publishes new Recognized Standards List (every 2-4 months), check for:
  - New standards recognized (may add to list)
  - Standards withdrawn (must remove or justify continued use)
  - Standards superseded (update version number)
- Re-verification required if changes affect device

**Trigger 3: Device Design Change**
- If device design changes (materials, contact duration, power source), re-verify standards applicability
- Example: If catheter contact duration increases from <24 hours to ≥24 hours, ISO 10993-11 becomes required

**Trigger 4: New FDA Guidance**
- If FDA publishes new guidance affecting standards expectations, re-verify applicability
- Example: 2016 Biocompatibility Guidance superseded older guidance, changed ISO 10993 endpoints

**Trigger 5: Predicate Shift**
- If clearing predicates in product code shift to new standards pattern, consider updating
- Example: If 90% of recent predicates start citing a new standard, evaluate if applicable

**Re-Verification Procedure:**
1. Notify verifier of trigger event
2. Re-run verification checklist for affected standards
3. Document changes in verification history
4. Update version number (e.g., v3.0 → v3.1 REVISED)
5. Obtain QA approval for revised list
6. Update DHF with revised version

---

## 6. Acceptance Criteria for Verification

### 6.1 Completeness Criteria

**Verification is COMPLETE when:**

☑ 100% of standards in draft list have verification checklist completed
☑ 100% of standards have reference sources cited (minimum 2 per standard)
☑ All verification checklists signed and dated by verifier
☑ SME reviews completed for specialized standards (biocompatibility, electrical, software)
☑ Discrepancies documented with resolution (if any)
☑ Objective evidence package compiled
☑ Final approved standards list generated
☑ QA approval obtained
☑ Document filed in DHF with correct numbering

**Incompleteness Blockers:**

❌ Missing signatures on verification checklists
❌ Reference sources not cited ("AI said so" is not acceptable)
❌ SME review pending for biocompatibility standards
❌ Discrepancies unresolved (AI error not documented)
❌ QA approval not obtained
❌ Document not filed in DHF

---

### 6.2 Acceptability Criteria

**Verification is ACCEPTABLE when:**

**Criterion 1: Verifier Credentials**
- ☑ Verifier is RA/C certified OR has 3+ years FDA regulatory experience OR has engineering degree + 2+ years medical device experience
- ☑ Verifier is NOT the developer of the AI tool (independence)
- ☑ Verifier is different person than QA approver (segregation of duties)

**Criterion 2: Reference Sources**
- ☑ Each standard has ≥2 reference sources cited
- ☑ Reference sources are objective (FDA database, guidance, predicates, risk assessment)
- ☑ Reference sources are current (FDA guidance not superseded, predicates from last 5 years)

**Criterion 3: Traceability**
- ☑ Each required standard is linked to risk assessment hazard OR regulation OR FDA guidance
- ☑ Can trace from standard → design characteristic → risk → mitigation
- ☑ Can answer "Why is this standard required for THIS device?" with device-specific rationale

**Criterion 4: Discrepancy Resolution**
- ☑ All AI errors documented (false positives, false negatives)
- ☑ Discrepancies resolved with corrective action
- ☑ Development team notified of systematic errors (for future AI improvement)

**Criterion 5: SME Concurrence**
- ☑ Biocompatibility expert reviewed ISO 10993 standards
- ☑ Electrical engineer reviewed IEC 60601 standards (if applicable)
- ☑ Software engineer reviewed IEC 62304 standards (if applicable)
- ☑ All SMEs concur with RA professional's determination (or discrepancies documented)

**Criterion 6: Audit Readiness**
- ☑ Can retrieve verification package within 5 minutes
- ☑ Can answer FDA audit questions with documented evidence
- ☑ No reliance on "AI told me" - all rationale is human-expert verified

---

### 6.3 Rejection Criteria

**Verification is REJECTED if:**

❌ Verifier lacks required credentials (not qualified RA professional)
❌ Reference sources insufficient ("AI said so" is not acceptable)
❌ Traceability missing (cannot link standard to device risk or requirement)
❌ Discrepancies unresolved (AI error noted but not fixed)
❌ SME review missing for specialized standards
❌ QA approval not obtained
❌ Document incomplete (missing signatures, dates, or sections)

**Rejection Resolution:**
1. Notify verifier of deficiencies
2. Verifier corrects deficiencies
3. Re-submit for QA approval
4. QA re-reviews corrected version
5. Approve or reject again

---

## 7. Integration with DHF

### 7.1 DHF Location and Structure

**Design History File Organization:**

```
Design_History_File/
├── 01_Design_Planning/
│   ├── Design_Plan.pdf
│   ├── Resource_Allocation.pdf
│   └── Regulatory_Strategy.pdf
│
├── 02_Design_Input/
│   ├── Device_Requirements_Specification.pdf (REQ-001)
│   ├── Risk_Management_File.pdf (RISK-001)
│   ├── Standards_Determination/ (STD-001) ← VERIFICATION PACKAGE HERE
│   │   ├── standards_verified.json
│   │   ├── objective_evidence_summary.pdf
│   │   ├── verification_checklist_ISO-13485.pdf
│   │   ├── verification_checklist_ISO-14971.pdf
│   │   ├── verification_checklist_ISO-10993-1.pdf
│   │   ├── verification_checklist_ISO-10993-4.pdf
│   │   ├── verification_checklist_IEC-60601-1.pdf
│   │   ├── sme_review_biocompatibility.pdf
│   │   ├── sme_review_electrical.pdf
│   │   └── qa_approval_signature.pdf
│   ├── Labeling_Requirements.pdf (LABEL-001)
│   └── Interface_Requirements.pdf (INTERFACE-001)
│
├── 03_Design_Output/
│   ├── Device_Specifications.pdf
│   ├── Manufacturing_Specifications.pdf
│   └── Packaging_Labeling_Specifications.pdf
│
├── 04_Design_Verification/
│   ├── Verification_Plan.pdf
│   ├── Biocompatibility_Test_Reports/ ← TEST RESULTS REFERENCE STANDARDS
│   │   ├── ISO-10993-4_Hemocompatibility_Report.pdf (references STD-001)
│   │   ├── ISO-10993-5_Cytotoxicity_Report.pdf (references STD-001)
│   │   └── ISO-10993-10_Sensitization_Report.pdf (references STD-001)
│   ├── Electrical_Safety_Test_Reports/
│   │   ├── IEC-60601-1_Test_Report.pdf (references STD-001)
│   │   └── IEC-60601-1-2_EMC_Report.pdf (references STD-001)
│   └── Mechanical_Test_Reports/
│       └── ASTM-F2394_Tensile_Strength_Report.pdf (references STD-001)
│
├── 05_Design_Validation/
│   ├── Validation_Plan.pdf
│   ├── Clinical_Evidence.pdf
│   └── Human_Factors_Validation.pdf
│
├── 06_Design_Transfer/
│   ├── Process_Validation.pdf
│   └── Manufacturing_Training.pdf
│
├── 07_Design_Changes/
│   └── Change_Control_Records/
│
└── 10_Requirements_Traceability/
    └── Traceability_Matrix.xlsx (links STD-001 to verification tests)
```

---

### 7.2 File Naming Convention

**Pattern:** `[DEVICE_CODE]_[DOCUMENT_TYPE]_[VERSION]_[DATE].pdf`

**Examples:**
- `DQY-2024-001_STANDARDS_VERIFICATION_v3.0_2026-02-25.pdf`
- `OVE-2025-003_STANDARDS_CHECKLIST_ISO-10993-1_v1.0_2026-03-01.pdf`
- `GEI-2024-007_SME_REVIEW_BIOCOMPATIBILITY_v1.0_2026-02-28.pdf`

**JSON Files:**
- `DQY-2024-001_standards_verified_v3.0.json` (machine-readable)

**Metadata Requirements in PDF:**
- Document Number: DHF-02-STD-001
- Version: 3.0 APPROVED
- Effective Date: 2026-02-25
- Author: Jane Smith, RA/C
- Approver: Sarah Lee, QA Manager
- Linked Documents: REQ-001 (Requirements), RISK-001 (Risk Management), RTM-001 (Traceability Matrix)

---

### 7.3 Linkage to Other DHF Records

**Traceability Matrix Entry Example:**

| Requirement ID | Requirement Description | Source | Design Input | Design Output | Verification Test | Validation | Status |
|----------------|------------------------|--------|--------------|---------------|-------------------|------------|--------|
| REQ-BIO-001 | Device shall be biocompatible per ISO 10993-1 | Risk Assessment RISK-001, Hazard ID H-003 | **STD-001** (Standards Determination) | Device Material Specification SPEC-002 | ISO 10993-5 Cytotoxicity Report TEST-005 | Clinical Use Validation VAL-001 | ✅ VERIFIED |
| REQ-BIO-003 | Device shall demonstrate hemocompatibility per ISO 10993-4 | Risk Assessment RISK-001, Hazard ID H-007 | **STD-001** (Standards Determination) | Blood Contact Materials SPEC-004 | ISO 10993-4 Hemocompatibility Report TEST-008 | Clinical Use Validation VAL-001 | ✅ VERIFIED |
| REQ-ELEC-001 | Device shall meet IEC 60601-1 electrical safety | 21 CFR 898.12, FDA Guidance | **STD-001** (Standards Determination) | Electrical Schematic SPEC-010 | IEC 60601-1 Test Report TEST-015 | N/A | ✅ VERIFIED |

**Traceability Flow:**
```
Risk Assessment (RISK-001)
   ↓
Standards Determination (STD-001) ← Verification documented here
   ↓
Test Planning (Design Verification Plan)
   ↓
Test Execution (Test Reports TEST-005, TEST-008, TEST-015)
   ↓
Traceability Matrix (RTM-001) links all
```

---

### 7.4 Audit Trail Requirements

**Who accessed verification records, when, and why?**

**Audit Log Example:**

| Date/Time | User | Action | Document | Purpose |
|-----------|------|--------|----------|---------|
| 2026-02-15 10:30 | AI Tool | GENERATED | standards_draft.json v1.0 | Initial AI generation |
| 2026-02-20 09:15 | Jane Smith | REVIEWED | standards_draft.json v1.0 | Begin verification |
| 2026-02-20 14:15 | Jane Smith | VERIFIED | standards_verified.json v2.0 | Verification complete |
| 2026-02-22 09:00 | Dr. John Doe | REVIEWED | standards_verified.json v2.0 | SME biocompatibility review |
| 2026-02-22 10:30 | Mike Johnson | REVIEWED | standards_verified.json v2.0 | SME electrical safety review |
| 2026-02-25 11:30 | Sarah Lee | APPROVED | standards_verified.json v3.0 | QA approval |
| 2026-02-25 14:00 | Jane Smith | FILED | DHF-02-STD-001 v3.0 | Filed in DHF |
| 2026-03-10 13:45 | FDA Inspector | VIEWED | DHF-02-STD-001 v3.0 | FDA audit request |

**Access Control:**
- Read access: All project team members
- Write access: RA professionals, SMEs, QA only
- Approve access: QA Manager only
- Deletion: Prohibited (version control instead)

---

## 8. Test Cases for Verification Workflow

### 8.1 Test Case 1: Complete Verification Workflow (Happy Path)

**Objective:** Verify end-to-end workflow from AI generation to DHF filing

**Preconditions:**
- Device profile complete (DQY catheter, blood contact <24 hours, powered)
- Risk assessment complete (RISK-001)
- RA professional assigned (Jane Smith, RA/C)

**Test Steps:**
1. AI tool generates draft standards list → 12 standards, 3 with HIGH confidence
2. Verification dashboard notifies Jane Smith → Email received, deadline 2026-02-27
3. Jane Smith completes verification checklists for all 12 standards → 11 approved, 1 removed (ISO 10993-11)
4. Jane Smith adds 1 missing standard (ISO 11070) → Total 11 standards
5. Jane Smith documents 2 discrepancies (1 false negative, 1 false positive)
6. SMEs review specialized standards → Biocompat expert concurs, Electrical expert concurs
7. QA Manager reviews package → Approves DHF-02-STD-001 v3.0
8. Jane Smith files in DHF → Document available in DHF/02_Design_Input/Standards_Determination/
9. Simulate FDA audit request → Document retrieved in 2 minutes ✅

**Expected Results:**
- ✅ All 11 standards have completed verification checklists
- ✅ All checklists have signatures and dates
- ✅ Discrepancies documented with resolution
- ✅ Objective evidence package complete
- ✅ QA approval obtained
- ✅ Document filed in DHF
- ✅ Audit-ready (can answer all FDA questions with documented evidence)

**Pass/Fail:** PASS if all expected results achieved

---

### 8.2 Test Case 2: AI Error Detection (Verifier Catches Incorrect Standard)

**Objective:** Verify that verifier catches AI false positive

**Preconditions:**
- AI tool incorrectly includes ISO 10993-11 (systemic toxicity) for short-term contact device (<24 hours)

**Test Steps:**
1. AI tool generates draft with ISO 10993-11 (HIGH confidence)
2. Verifier reviews FDA 2016 Biocompatibility Guidance Table 1
3. Verifier determines: Contact <24 hours → ISO 10993-11 NOT REQUIRED
4. Verifier marks ISO 10993-11 as NOT APPLICABLE
5. Verifier documents discrepancy in log
6. Verifier notifies development team (AI logic error)
7. Development team files error in TICKET-017 validation tracking

**Expected Results:**
- ✅ Verifier removed ISO 10993-11 from final list
- ✅ Discrepancy documented with FDA Guidance citation
- ✅ Development team notified (for AI improvement)
- ✅ Verification prevents unnecessary testing (saves $20K-$35K)

**Pass/Fail:** PASS if verifier catches error and documents resolution

---

### 8.3 Test Case 3: Batch Verification (10 Devices)

**Objective:** Verify workflow scales to multiple devices

**Preconditions:**
- 10 devices across different product codes (DQY, OVE, GEI, QKQ, FRO, NBW, MSF, DPS, CFR, GCJ)
- 3 RA professionals assigned (load balanced)

**Test Steps:**
1. AI tool generates drafts for all 10 devices → 10 draft standards lists
2. Verification dashboard shows 10 active verifications
3. RA professionals complete verifications over 10 business days
4. SME reviews batched (biocompat expert reviews all 10 in one session)
5. QA Manager approves all 10 packages
6. All 10 filed in respective DHFs

**Expected Results:**
- ✅ All 10 devices have complete verification packages
- ✅ Average verification time <8 hours per device
- ✅ No backlog (all completed within deadline)
- ✅ Batch SME review efficient (6 hours for biocompat expert vs. 10+ hours if separate)

**Pass/Fail:** PASS if all 10 devices verified within resource budget

---

### 8.4 Test Case 4: FDA Audit Simulation (5 Random Devices)

**Objective:** Verify audit readiness and retrieval speed

**Preconditions:**
- 5 random devices selected (DQY-2024-001, OVE-2025-003, GEI-2023-007, QKQ-2024-011, FRO-2025-002)
- All have DHF-filed verification packages

**Test Steps:**
1. FDA inspector requests standards verification records for 5 devices
2. RA professional receives request at 9:00 AM
3. RA professional retrieves 5 DHF packages from DHF folders
4. RA professional compiles into single PDF (all 5 verification packages)
5. RA professional provides to FDA inspector by 9:30 AM (30 minutes)

**Expected Results:**
- ✅ All 5 verification packages retrieved within 30 minutes
- ✅ All packages complete (no missing signatures or sections)
- ✅ FDA inspector can trace each standard to device-specific rationale
- ✅ FDA inspector satisfied with objective evidence quality

**Pass/Fail:** PASS if retrieval <30 minutes and FDA inspector satisfied

---

### 8.5 Test Case 5: Re-Verification After Tool Update

**Objective:** Verify re-verification workflow when AI tool updated

**Preconditions:**
- Device DQY-2024-001 has APPROVED standards list (v3.0) from AI tool v5.26.0
- AI tool updated to v5.27.0 (TICKET-018: expanded FDA database to 1,900+ standards)

**Test Steps:**
1. Development team notifies users: "AI tool updated to v5.27.0, re-verify all UNVERIFIED drafts"
2. Previously APPROVED lists (v3.0) are grandfathered (no re-verification required)
3. New device DQY-2024-015 generates draft with AI tool v5.27.0 → Includes ISO 11070 (now in database)
4. Verifier completes verification checklist
5. No discrepancies found (AI tool improved, no longer missing ISO 11070)

**Expected Results:**
- ✅ APPROVED lists not affected by tool update (grandfathered)
- ✅ New drafts use updated tool version
- ✅ AI accuracy improved (no ISO 11070 false negative)
- ✅ Re-verification only required for in-progress verifications

**Pass/Fail:** PASS if grandfathering works and new tool version performs better

---

## 9. Auditor Verification Requirements

### 9.1 Mock FDA Audit Protocol

**Scenario:** FDA inspector arrives for routine inspection, requests design control records

**Audit Scope:** Request verification records for 5 random devices

**Audit Procedure:**

**Step 1: Request Verification Records (Inspector)**
- Inspector selects 5 random DHF folders from document library
- Inspector requests: "Show me the standards determination verification records for these 5 devices"

**Step 2: Retrieval (Auditee - RA Professional)**
- RA professional retrieves DHF-02-STD-001 documents for all 5 devices
- Target retrieval time: <5 minutes
- Provides inspector with:
  - Objective evidence summary (PDF)
  - Verification checklists (all standards)
  - SME reviews
  - QA approval signatures
  - Linked documents (risk assessment, predicates)

**Step 3: Completeness Check (Inspector)**

**For each of 5 devices, inspector verifies:**

☐ **Completeness Checklist:**
  - [ ] All verification checklists present (100% of standards)
  - [ ] All checklists signed and dated
  - [ ] Reference sources cited (≥2 per standard)
  - [ ] SME reviews present for specialized standards
  - [ ] QA approval signature present
  - [ ] Document filed in DHF with correct numbering

**Pass Criteria:** 100% of items checked for all 5 devices

---

**Step 4: Traceability Check (Inspector)**

**Inspector selects 3 standards across the 5 devices and asks:**

**Question 1: "How did you determine ISO 10993-4 was required for Device A?"**

**Acceptable Answer:**
- Auditee retrieves verification checklist for ISO 10993-4
- Points to Section 4 (Applicability): "Device has blood contact (intravascular catheter)"
- Points to Section 6 (Traceable Reasoning): "Risk assessment REQ-BIO-003 identifies thrombogenicity as Medium risk"
- Points to Section 6 (Traceable Reasoning): "Predicate K240123 cites ISO 10993-4"
- Points to SME review: "Biocompatibility toxicologist concurred"

**Unacceptable Answer:**
- "The AI tool said it was required" (no human verification)
- "It's a standard for catheters" (too generic, not device-specific)
- "I don't know, I just followed the tool output" (no verification)

**Pass Criteria:** Auditee can trace standard to device-specific rationale with documented evidence

---

**Question 2: "Who verified these standards determinations?"**

**Acceptable Answer:**
- Auditee points to signature block: "Jane Smith, RA/C, 8 years experience"
- Auditee provides Jane Smith's credentials: RA/C certification, resume on file
- Auditee explains: "Jane independently verified each standard against FDA database, predicates, and risk assessment"
- Auditee notes: "SME reviews by Dr. John Doe (biocompatibility) and Mike Johnson (electrical safety)"

**Unacceptable Answer:**
- "The AI tool verified it" (no human verification)
- "I don't know who verified it" (no accountability)
- "It was auto-generated" (no verification)

**Pass Criteria:** Verifier identified with documented credentials

---

**Question 3: "Show me the objective evidence for ISO 10993-4."**

**Acceptable Answer:**
- Auditee provides verification checklist for ISO 10993-4
- Provides FDA database screenshot (ISO 10993-4:2017 recognized, List 63)
- Provides risk assessment excerpt (Hazard H-007: Thrombogenicity, Risk Score 6)
- Provides predicate 510(k) summary (K240123 Section 17 cites ISO 10993-4)
- Provides SME review (Dr. John Doe concurred)

**Unacceptable Answer:**
- "The AI tool determined it" (no objective evidence)
- "It's a standard for blood-contacting devices" (no device-specific evidence)
- Provides only AI output JSON (not human verification records)

**Pass Criteria:** Objective evidence package includes ≥2 reference sources per standard

---

**Step 5: Accountability Check (Inspector)**

**Inspector asks: "How do you ensure the AI tool is accurate?"**

**Acceptable Answer:**
- Auditee provides TICKET-017 Validation Report (IQ/OQ/PQ testing on 500+ product codes)
- Auditee explains: "AI tool is validated per 21 CFR 820.70(i), but we do NOT rely solely on AI output"
- Auditee explains: "All AI outputs are VERIFIED by qualified RA professionals before use"
- Auditee shows discrepancy log: "We caught 2 AI errors during verification (1 false negative, 1 false positive)"

**Unacceptable Answer:**
- "The AI is 95% accurate" (no validation evidence)
- "We trust the AI output" (no verification)
- "It's AI-powered, so it's accurate" (misleading claim)

**Pass Criteria:** Tool validation documented AND human verification mandatory

---

**Step 6: Timeliness Check (Inspector)**

**Inspector asks: "When was this verification completed relative to device development?"**

**Acceptable Answer:**
- Auditee shows timeline:
  - Design input phase: Standards determination verified (BEFORE test planning)
  - Design verification phase: Tests executed per verified standards list
  - Design validation phase: Clinical validation
- Verification completed BEFORE tests ordered (not after)

**Unacceptable Answer:**
- Verification completed AFTER tests (retroactive justification)
- Verification completed AFTER 510(k) submission (too late)
- No timestamps (cannot verify timeliness)

**Pass Criteria:** Verification completed before use in test planning

---

### 9.2 Audit Readiness Scoring

**For each of 5 devices audited, score:**

| Criterion | Points | Device A | Device B | Device C | Device D | Device E |
|-----------|--------|----------|----------|----------|----------|----------|
| Completeness (all checklists present, signed) | 20 | 20 | 20 | 18 | 20 | 20 |
| Traceability (can cite source for each standard) | 20 | 20 | 20 | 20 | 20 | 18 |
| Accountability (verifier identified, credentials) | 20 | 20 | 20 | 20 | 20 | 20 |
| Objective Evidence (≥2 sources per standard) | 20 | 18 | 20 | 20 | 20 | 20 |
| Timeliness (verified before use) | 20 | 20 | 20 | 20 | 20 | 20 |
| **TOTAL** | **100** | **98** | **100** | **98** | **100** | **98** |

**Overall Audit Score:** 494/500 = 98.8%

**Audit Result:**
- ≥95%: **PASS** - Compliant with 21 CFR 820.30 design controls
- 85-94%: **CONDITIONAL PASS** - Minor findings, corrective action required
- <85%: **FAIL** - Major findings, 483 observation likely

---

## 10. Training and Competency Requirements

### 10.1 Who Is Qualified to Perform Verification?

**Required Qualifications (Must meet at least ONE):**

**Option 1: Regulatory Affairs Certification**
- RA/C (Regulatory Affairs Certification) from RAPS
- 3+ years medical device regulatory experience

**Option 2: Engineering + Regulatory Experience**
- Bachelor's degree in Engineering (Biomedical, Electrical, Mechanical)
- 2+ years medical device industry experience
- Training on FDA regulations (21 CFR Part 820, 510(k) process)

**Option 3: Quality Assurance Background**
- ISO 13485 Lead Auditor certification
- 5+ years QMS experience in medical device industry
- Knowledge of FDA recognized consensus standards

**Disqualifications:**
- Developer of AI tool (conflict of interest)
- Junior RA professional with <2 years experience (unless supervised)
- Non-technical administrative staff (insufficient knowledge)

---

### 10.2 Training Requirements

**Training Module 1: 21 CFR 820.30 Design Control Requirements (4 hours)**

**Topics:**
- Design input requirements (820.30(c))
- Design output requirements (820.30(d))
- Design verification requirements (820.30(f))
- Objective evidence for design controls
- FDA inspection expectations

**Assessment:**
- Written exam (80% pass required)
- Practical exercise: Review sample verification package, identify deficiencies

---

**Training Module 2: FDA Recognized Consensus Standards (4 hours)**

**Topics:**
- How to use FDA Recognition Database
- Universal standards (ISO 13485, ISO 14971, ISO 10993-1)
- Device-specific standards (biocompatibility, electrical, mechanical)
- How to determine applicability
- Version currency (superseded standards)

**Assessment:**
- Practical exercise: Given device profile, identify applicable standards
- Practical exercise: Check FDA database for 10 standards, verify recognition status

---

**Training Module 3: Verification Checklist Procedure (4 hours)**

**Topics:**
- Step-by-step walkthrough of verification checklist
- How to cite reference sources (FDA guidance, predicates, risk assessment)
- How to document traceable reasoning
- How to identify AI errors (false positives, false negatives)
- How to escalate discrepancies

**Assessment:**
- Practical exercise: Complete verification checklist for 3 standards
- Practical exercise: Review AI output, identify 2 intentional errors

---

**Training Module 4: Objective Evidence and DHF Integration (2 hours)**

**Topics:**
- How to compile objective evidence package
- DHF filing requirements
- Linkage to requirements traceability matrix
- Audit preparation and FDA inspection readiness

**Assessment:**
- Practical exercise: Compile objective evidence package for sample device
- Mock FDA audit: Answer inspector questions using documentation

---

**Total Training:** 14 hours

**Competency Verification:**
- Pass all 4 module assessments (≥80% each)
- Complete supervised verification for 2 devices (under RA Manager oversight)
- Demonstrate competency in mock FDA audit scenario

**Retraining Triggers:**
- New FDA guidance published (e.g., 2016 Biocompatibility Guidance updated)
- Major AI tool update (e.g., TICKET-018 database expansion)
- Annual refresher training (2 hours per year)

---

### 10.3 Training Documentation

**Training Record Template:**

```markdown
# Training Record: Standards Verification Framework

**Trainee Name:** ________________________________
**Job Title:** ________________________________
**Department:** Regulatory Affairs / Quality Assurance

---

## Training Modules Completed

| Module | Date Completed | Trainer | Assessment Score | Pass/Fail |
|--------|----------------|---------|------------------|-----------|
| Module 1: 21 CFR 820.30 Design Controls | [Date] | [Trainer Name] | 92% | PASS |
| Module 2: FDA Consensus Standards | [Date] | [Trainer Name] | 88% | PASS |
| Module 3: Verification Checklist Procedure | [Date] | [Trainer Name] | 85% | PASS |
| Module 4: Objective Evidence & DHF | [Date] | [Trainer Name] | 90% | PASS |

**Overall Training Score:** 88.75% (PASS ≥80%)

---

## Practical Competency Demonstration

**Supervised Verification #1:**
- Device: DQY-2024-001 (Intravascular Catheter)
- Supervisor: Jane Smith, RA/C
- Date: [Date]
- Competency: ✅ DEMONSTRATED
- Supervisor Comments: "Trainee correctly identified ISO 11070 false negative, documented rationale clearly"

**Supervised Verification #2:**
- Device: OVE-2025-003 (Spinal Fusion Device)
- Supervisor: Jane Smith, RA/C
- Date: [Date]
- Competency: ✅ DEMONSTRATED
- Supervisor Comments: "Trainee correctly linked ASTM F1717 to risk assessment, cited predicates"

**Mock FDA Audit:**
- Date: [Date]
- Scenario: Inspector requests standards verification for 3 devices
- Result: ✅ PASS
- Auditor Comments: "Trainee retrieved records in 4 minutes, answered all questions with documented evidence"

---

## Competency Certification

I certify that [Trainee Name] has completed all required training and demonstrated
competency to perform independent standards verification per this framework.

**RA Manager Name:** ________________________________
**Signature:** ____________________________________
**Date:** _________________________________________

---

## Authorized Verification Activities

☑ Independently verify universal standards (ISO 13485, ISO 14971, ISO 10993-1)
☑ Independently verify device-specific standards (with SME consultation for specialized standards)
☐ Approve final verification packages (requires QA Manager authority)
☑ Compile objective evidence packages for DHF filing

**Authorization Effective Date:** [Date]
**Next Retraining Due:** [Date + 1 year]
```

---

## Appendix A: Verification Checklist Templates

**Included in this specification:**
- Universal Standards Checklist (Section 3.1)
- Device-Specific Standards Checklist (Section 3.2)

**Additional templates available in:**
- `/templates/verification_checklist_universal.md`
- `/templates/verification_checklist_device_specific.md`
- `/templates/verification_checklist_biocompatibility.md`
- `/templates/verification_checklist_electrical.md`
- `/templates/verification_checklist_software.md`

---

## Appendix B: Regulatory References

**21 CFR Part 820 — Quality System Regulation**
- 820.30(c): Design input requirements
- 820.30(d): Design output requirements
- 820.30(e): Design review requirements
- 820.30(f): Design verification requirements
- 820.70(i): Automated process validation

**ISO 13485:2016 — Medical Devices QMS**
- Section 7.3.3: Design and development inputs
- Section 7.3.4: Design and development outputs
- Section 7.3.6: Design and development verification

**FDA Guidance Documents:**
- Design Control Guidance for Medical Device Manufacturers (1997)
- Use of International Standard ISO 10993-1 (2016)
- Recognized Consensus Standards Database (https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/search.cfm)

---

## Appendix C: Implementation Timeline

**Phase 1: Framework Setup (2 weeks)**
- Week 1: Create verification checklist templates
- Week 2: Set up DHF folder structure, train RA professionals

**Phase 2: Pilot Testing (4 weeks)**
- Week 3-4: Pilot with 3 devices (DQY, OVE, GEI)
- Week 5-6: Refine checklists based on pilot feedback

**Phase 3: Full Deployment (2 weeks)**
- Week 7: Train all RA professionals (14 hours per person)
- Week 8: Deploy verification workflow for all new devices

**Phase 4: Audit Preparation (1 week)**
- Week 9: Mock FDA audit with 5 devices
- Week 10: Correct any deficiencies, finalize DHF packages

**Total Implementation Time:** 10 weeks (2.5 months)

---

## Document Approval

**Prepared By:**
Name: ________________________________
Title: Senior QMS Auditor
Signature: ____________________________________
Date: _________________________________________

**Reviewed By:**
Name: ________________________________
Title: RA Manager
Signature: ____________________________________
Date: _________________________________________

**Approved By:**
Name: ________________________________
Title: VP Quality Assurance
Signature: ____________________________________
Date: _________________________________________

---

**END OF VERIFICATION FRAMEWORK SPECIFICATION**

**Document Control:**
- Document Number: TICKET-020-SPEC
- Version: 1.0 DRAFT
- Effective Date: [Pending approval]
- Next Review: [1 year from effective date]
- Distribution: RA Department, QA Department, Development Team
