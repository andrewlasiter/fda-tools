# FDA IDE (Investigational Device Exemption) Pathway Specification

**Research Date:** 2026-02-15
**Version:** 1.0
**Purpose:** Define IDE pathway requirements and integration opportunities for fda-tools plugin

---

## Executive Summary

An **Investigational Device Exemption (IDE)** allows investigational medical devices to be used in clinical studies to collect safety and effectiveness data required for marketing applications (510(k) or PMA). IDE studies are required for significant risk devices and regulated under 21 CFR Part 812.

**Key Findings:**
- IDE pathway has 3 submission types (SR, NSR, Abbreviated)
- Clinical data from IDE studies can directly feed into 510(k)/PMA submissions
- No dedicated IDE endpoint exists in openFDA API
- IDE studies must be registered on ClinicalTrials.gov
- Plugin already supports IDE trial discovery via `/fda-tools:trials` command
- **Gap:** Plugin lacks IDE-specific protocol drafting, monitoring calculators, and compliance tracking

---

## 1. IDE Submission Types

### 1.1 Significant Risk (SR) IDE

**Definition:** A device that presents potential for serious risk to health, safety, or welfare of subjects.

**Criteria for Significant Risk (any one qualifies):**
- Intended as an **implant** and presents potential for serious risk
- **Purported to support or sustain human life** and presents potential for serious risk
- Of **substantial importance in diagnosing, curing, mitigating, or treating disease** and presents potential for serious risk
- Otherwise presents **potential for serious risk** to health, safety, or welfare

**Regulatory Requirements:**
- **Full IDE application** submission to FDA (21 CFR 812.20)
- **30-day FDA review** — approval required before study begins
- **IRB approval** required
- **Full compliance** with 21 CFR Part 812 regulations
- **Annual progress reports** to FDA and all reviewing IRBs
- **UADE (Unanticipated Adverse Device Effects) reporting** to FDA within 10 working days

**Application Contents (21 CFR 812.20):**
1. Sponsor name and address
2. Report of prior investigations
3. Investigational plan (detailed protocol)
4. Device description and manufacturing information
5. Investigator agreements
6. IRB certifications
7. Device labeling
8. Informed consent forms
9. Other information requested by FDA

### 1.2 Non-Significant Risk (NSR) IDE

**Definition:** Devices that do NOT meet the criteria for significant risk and are not banned.

**Regulatory Requirements:**
- **No FDA application** required — may begin with IRB approval alone
- **Abbreviated IDE requirements** (21 CFR 812.2(b))
- **IRB approval** with brief explanation of why device is NSR
- **Informed consent** per 21 CFR Part 50
- **Limited monitoring and reporting** obligations
- **No annual reports to FDA** (IRB reports only)

**Abbreviated IDE Compliance (21 CFR 812.2(b)):**
- Device labeling: "CAUTION—Investigational device. Limited by Federal (or United States) law to investigational use"
- Monitoring per § 812.46
- Records: § 812.140(b)(4) and (5)
- Reports: § 812.150(b)(1)-(3), (5)-(10)
- Prohibition on promotion/commercialization

**FDA Authority:** FDA is the final arbiter of SR vs NSR determination. Sponsors, investigators, or IRBs can request FDA's determination if uncertain.

### 1.3 Abbreviated IDE

**Definition:** Streamlined pathway for NSR devices with minimal regulatory burden.

**Key Difference:** NSR studies automatically qualify for abbreviated requirements — no separate "Abbreviated IDE" submission exists. The term refers to the reduced regulatory obligations for NSR studies.

---

## 2. IDE to 510(k)/PMA Relationship

### 2.1 IDE as Clinical Evidence Source

**510(k) Pathway:**
- Clinical data from IDE studies is **valuable but NOT always mandatory** for 510(k) clearance
- Most 510(k)s rely on substantial equivalence without clinical data
- IDE may be requested for novel devices, new indications, or to support reimbursement
- Performance data can include bench testing, biocompatibility, software validation, etc.

**PMA Pathway:**
- Clinical data from IDE studies is **typically required** for Class III devices
- Most Class III devices require IDE approval before PMA submission
- PMA requires extensive clinical trials demonstrating safety and effectiveness
- **Exception:** Some PMA devices may leverage existing clinical data (post-cutoff date devices) and avoid new clinical trials

### 2.2 Clinical Data Reusability

**Full Reusability:** Clinical data from IDE studies conducted under GCP (Good Clinical Practice) and 21 CFR Part 812 can be directly incorporated into:
- 510(k) Special Controls section
- PMA Clinical Data section
- Post-market surveillance studies

**Requirements for Reuse:**
- Study protocol aligned with marketing application endpoints
- IRB approval documentation
- Informed consent records
- Case report forms (CRFs) and raw data
- Statistical analysis plan and results
- Compliance with 21 CFR Part 812

**Timeline Considerations:**
- IDE study duration varies: 6 months (simple devices) to 5+ years (implants, chronic conditions)
- FDA encourages **pre-submission meetings** to align IDE protocol with eventual 510(k)/PMA requirements
- Early endpoint discussions prevent costly protocol amendments

---

## 3. FDA Data Sources for IDE Studies

### 3.1 openFDA API

**Current Status:** ❌ **No dedicated IDE endpoint**

**Available Device Endpoints (as of 2026-02-15):**
- `/device/510k` — 510(k) clearances
- `/device/classification` — Device classification
- `/device/pma` — PMA approvals
- `/device/recall` — Recall enforcement
- `/device/event` — MAUDE adverse events (medical device reports)
- `/device/udi` — UDI (Unique Device Identifier) from GUDID

**IDE Data Gap:** IDE approval letters, study protocols, and enrollment data are **NOT publicly available** via openFDA API.

**Workaround:** Use ClinicalTrials.gov API v2 (see Section 3.2) to discover IDE studies via NCT identifiers.

### 3.2 ClinicalTrials.gov Integration

**Status:** ✅ **Required for IDE studies**

**Registration Requirements (42 CFR Part 11):**
- **Significant Risk IDE studies** must be registered on ClinicalTrials.gov **within 21 days of first participant enrollment**
- **Non-Significant Risk IDE studies** are **exempt** from registration
- **Device feasibility studies** (Phase 0/Phase 1) are exempt

**ClinicalTrials.gov API v2:**
- Base URL: `https://clinicaltrials.gov/api/v2/studies`
- Device intervention filter: `AREA[InterventionType]DEVICE`
- Fields: NCT ID, sponsor, enrollment, primary outcomes, study design, status
- Rate limit: 50 requests/minute
- No authentication required

**Plugin Coverage:** ✅ `/fda-tools:trials` command already supports ClinicalTrials.gov searches with device-specific filtering.

### 3.3 FDA IDE Approval Letters

**Public Access:** ❌ **Not currently available**

**Status:** As of 2026-02-15, FDA does not maintain a public database of IDE approval letters comparable to the Complete Response Letters database for drugs/biologics.

**Access Methods:**
- **FOIA (Freedom of Information Act) requests** — case-by-case basis
- **Direct sponsor disclosure** — voluntary
- **Published literature** — some sponsors publish IDE study results

**Potential Future Development:** FDA's transparency initiatives may expand to IDE approvals, similar to the recent Complete Response Letters database launch.

---

## 4. IDE-Specific Requirements

### 4.1 Investigational Plan (21 CFR 812.25)

**Required Components:**

1. **Purpose of the Investigation**
   - Intended use of the device
   - Objectives and endpoints (primary, secondary)

2. **Protocol**
   - Written, scientifically sound protocol
   - Inclusion/exclusion criteria
   - Study design (randomized, prospective, adaptive, etc.)
   - Sample size justification (statistical power analysis)
   - Duration of follow-up

3. **Risk Analysis**
   - Description of all increased risks to subjects
   - Justification for the investigation (risk-benefit)
   - Risk mitigation strategies

4. **Device Description**
   - Components, properties, principles of operation
   - Anticipated device modifications during study

5. **Monitoring Procedures**
   - Data safety monitoring board (DSMB) if high risk
   - Interim analysis plans
   - Stopping rules

6. **Labeling**
   - Investigational use labels
   - Instructions for use (IFU)

7. **Informed Consent Materials**
   - Consent forms per 21 CFR Part 50
   - HIPAA authorization

8. **IRB Information**
   - List of reviewing IRBs
   - IRB approval letters

### 4.2 IRB Approval Documentation

**SR Devices:**
- Full IRB review required
- IRB must approve before FDA submission
- FDA reviews IRB determination as part of IDE application
- Continuing review at intervals per 21 CFR Part 56

**NSR Devices:**
- IRB must receive brief explanation of why device is NSR
- IRB approval sufficient to begin study (no FDA approval needed)
- Sponsor not required to notify FDA when IRB approves NSR study

### 4.3 Informed Consent Templates

**Regulatory Basis:** 21 CFR Part 50

**Required Elements (21 CFR 50.25):**
1. Statement that the study involves research
2. Description of foreseeable risks and discomforts
3. Description of potential benefits
4. Disclosure of alternative treatments
5. Confidentiality statement
6. Compensation/injury statement
7. Contact information for questions
8. Voluntary participation statement

**IDE-Specific Additions:**
- Disclosure that device is investigational
- Statement that device is not FDA-approved for this use
- Description of device purpose and how it works
- Known device risks from prior studies

### 4.4 Monitoring and Reporting

**Unanticipated Adverse Device Effects (UADE) Reporting:**

| Event | Investigator Timeline | Sponsor Timeline | FDA Notification |
|-------|---------------------|------------------|------------------|
| **UADE Discovery** | Report to sponsor + IRB within **10 working days** | Evaluate immediately | N/A |
| **UADE Evaluation** | N/A | Complete evaluation within **10 working days** | Submit evaluation to FDA + all IRBs + investigators within **10 working days** |
| **Follow-up Information** | N/A | Submit as soon as possible | Within **15 calendar days** of notification |
| **Unreasonable Risk Determination** | N/A | Terminate all investigations within **5 working days** | Immediate notification |

**Progress Reports:**
- **SR Devices:** Annual reports to FDA + all reviewing IRBs
- **NSR Devices:** Annual reports to IRBs only (no FDA submission)
- **Treatment IDEs:** Semi-annual reports to FDA + IRBs

**Annual Report Contents (21 CFR 812.150):**
- Number of patients enrolled
- List of participating investigators
- Summary of adverse events
- Protocol modifications
- Efforts to pursue marketing approval
- Analysis of study progress

**Required Even With Zero Enrollment:** Annual reports must be submitted regardless of enrollment status.

---

## 5. Current Plugin Capability Analysis

### 5.1 `/fda-tools:trials` Command — IDE Trial Discovery

**Capabilities:**
- ✅ Search ClinicalTrials.gov API v2 for device studies
- ✅ Filter by sponsor, status, device intervention type
- ✅ Parse NCT ID, enrollment, primary outcomes, study design
- ✅ Display trial URLs for detailed review
- ✅ Save results to project folder (`clinical_trials.json`)

**IDE-Specific Features:**
- ✅ Device-only filtering (`--device-only` → `AREA[InterventionType]DEVICE`)
- ✅ Studies with results filtering (`--with-results`)
- ✅ Product code to device name resolution

**Gaps:**
- ❌ No IDE-specific status filter (cannot distinguish SR vs NSR)
- ❌ No link to IDE approval letters (not publicly available)
- ❌ No adverse event integration (MAUDE data not linked to IDE studies)

**Assessment:** Command provides strong IDE trial discovery capabilities but cannot access FDA IDE approval data.

### 5.2 `/fda-tools:calc` Command — Sample Size Calculators

**Current Capabilities:**
- ✅ ASTM F1980 accelerated aging (shelf life)
- ✅ Sample size calculator with power analysis

**Sample Size Parameters:**
- `--success-rate` — Expected success rate (e.g., 0.95)
- `--margin` — Acceptable margin/difference
- `--alpha` — Significance level (default: 0.05)
- `--power` — Statistical power (default: 0.80)
- `--design` — Study design (one-sample, two-sample, non-inferiority)
- `--dropout` — Expected dropout rate

**IDE Relevance:**
- ✅ Supports IDE investigational plan requirement for sample size justification
- ✅ Aligns with FDA/ICH guidance (80% power, 5% alpha)
- ⚠️ **Limited** — Only basic designs; no adaptive trial support, no survival analysis

**Gaps:**
- ❌ No superiority/equivalence trial support
- ❌ No time-to-event (Kaplan-Meier) sample size calculations
- ❌ No interim analysis adjustments (sequential designs)

**Assessment:** Provides foundational sample size calculations but lacks advanced IDE study designs.

### 5.3 Other Relevant Commands

**`/fda-tools:literature`** — PubMed literature search
- ✅ Can find published IDE study results
- ✅ Supports clinical evidence gathering for 510(k)/PMA

**`/fda-tools:safety`** — MAUDE adverse event analysis
- ✅ Post-market surveillance data
- ⚠️ Not linked to IDE trial data (separate databases)

**`/fda-tools:standards`** — Applicable standards lookup
- ✅ ISO 14155 (Clinical investigation of medical devices for human subjects)
- ✅ Can inform IDE protocol design

**`/fda-tools:guidance`** — FDA guidance search
- ✅ Can retrieve IDE-related guidance documents
- ✅ Examples: "Significant Risk and Nonsignificant Risk Medical Device Studies" (2006)

---

## 6. Plugin Integration Requirements

### 6.1 IDE Protocol Drafting Command

**Proposed:** `/fda-tools:ide-protocol`

**Purpose:** Generate FDA-compliant IDE investigational plan per 21 CFR 812.25

**Inputs:**
- Device name, intended use, product code
- Study design (randomized, single-arm, prospective)
- Primary/secondary endpoints
- Sample size parameters (from `/fda-tools:calc`)
- Risk classification (SR or NSR)
- Applicable standards

**Outputs:**
- Investigational Plan template (Markdown/Word)
- Risk analysis section with predicate device comparison
- Statistical analysis plan
- Monitoring procedures
- Informed consent checklist

**Data Sources:**
- Device profile from `/fda-tools:start` or `/fda-tools:import`
- Peer IDE studies from `/fda-tools:trials`
- Applicable standards from `/fda-tools:standards`
- MAUDE adverse events from `/fda-tools:safety` (historical risk data)

**Integration Points:**
- Leverage existing project structure (`~/fda-510k-data/projects/{project_name}/`)
- Save protocol to `ide_protocol.md`
- Reference predicate devices from `device_profile.json`

### 6.2 IDE Monitoring Dashboard Command

**Proposed:** `/fda-tools:ide-monitor`

**Purpose:** Track IDE compliance obligations and reporting deadlines

**Features:**
1. **UADE Tracking:**
   - Record adverse events
   - Calculate reporting deadlines (10 working days from discovery)
   - Generate UADE evaluation reports

2. **Annual Report Reminders:**
   - Track IDE approval date
   - Calculate annual report due dates
   - Generate progress report templates

3. **Enrollment Tracking:**
   - Log participant enrollment by site
   - Calculate enrollment rate
   - Project completion timeline

4. **Protocol Amendments:**
   - Track minor vs major amendments
   - Calculate submission deadlines
   - Generate amendment request templates

**Data Storage:**
- `~/fda-510k-data/projects/{project_name}/ide_monitoring.json`
- Fields: `ide_number`, `approval_date`, `enrolled`, `uade_events`, `annual_reports`, `amendments`

### 6.3 IDE-to-Marketing Application Transition

**Proposed:** `/fda-tools:ide-to-submission`

**Purpose:** Extract IDE clinical data for 510(k) or PMA submission

**Workflow:**
1. **Load IDE Data:**
   - Import enrollment data
   - Parse primary outcome results
   - Extract adverse event summary

2. **Generate Clinical Section:**
   - Populate 510(k) Section 12 (Clinical Data) or PMA Clinical Module
   - Format tables: demographics, endpoints, adverse events
   - Reference IDE approval letter and study protocol

3. **Cross-Reference:**
   - Link to predicate device clinical data (if 510(k))
   - Compare safety profiles
   - Justify endpoint selection

**Integration:**
- Extends `/fda-tools:draft clinical` command
- Reads from `clinical_trials.json` and `ide_monitoring.json`
- Outputs to submission draft sections

### 6.4 Enhanced Sample Size Calculators

**Extensions to `/fda-tools:calc sample-size`:**

1. **Superiority Trial:**
   - Parameters: baseline rate, expected improvement, power, alpha
   - Output: sample size per arm

2. **Equivalence Trial:**
   - Parameters: equivalence margin, power, alpha
   - Output: sample size per arm (higher than non-inferiority)

3. **Time-to-Event (Survival Analysis):**
   - Parameters: hazard ratio, event rate, follow-up duration
   - Output: sample size and event count required

4. **Adaptive Designs:**
   - Parameters: interim analysis timing, futility boundaries
   - Output: maximum sample size with early stopping rules

**Regulatory Alignment:**
- FDA Guidance: "Adaptive Designs for Medical Device Clinical Studies" (2016)
- ISO 14155:2020 — Clinical investigation of medical devices

---

## 7. Regulatory Framework Summary

### 7.1 Key Regulations

| Regulation | Title | IDE Relevance |
|------------|-------|---------------|
| **21 CFR Part 812** | Investigational Device Exemptions | **Primary regulation** — IDE application, SR/NSR criteria, reporting |
| **21 CFR Part 50** | Protection of Human Subjects — Informed Consent | **Required** — informed consent for all IDE studies |
| **21 CFR Part 56** | Institutional Review Boards | **Required** — IRB oversight for all IDE studies |
| **21 CFR Part 803** | Medical Device Reporting (MDR) | **Post-market** — not IDE-specific, but overlaps with UADE reporting |
| **42 CFR Part 11** | Clinical Trials Registration and Results Submission | **ClinicalTrials.gov registration** for SR IDE studies |

### 7.2 Key FDA Guidance Documents

1. **Significant Risk and Nonsignificant Risk Medical Device Studies** (January 2006)
   - SR vs NSR determination criteria
   - IRB responsibilities
   - Abbreviated IDE requirements

2. **Investigational Device Exemption (IDE) Guidance for Industry and FDA Staff** (1996, updated)
   - IDE application preparation
   - Sponsor and investigator responsibilities
   - Reporting requirements

3. **Adaptive Designs for Medical Device Clinical Studies** (2016)
   - Sample size re-estimation
   - Interim analyses
   - Early stopping rules

4. **FDA Guidance for Industry: E9 Statistical Principles for Clinical Trials** (ICH E9, 1998)
   - Sample size justification
   - Primary/secondary endpoints
   - Statistical analysis plans

### 7.3 Standards

| Standard | Title | IDE Application |
|----------|-------|-----------------|
| **ISO 14155:2020** | Clinical investigation of medical devices for human subjects | **Primary standard** — protocol design, GCP, monitoring |
| **ISO 13485:2016** | Medical devices — Quality management systems | **Manufacturing** — device quality for IDE studies |
| **ICH E6(R2)** | Good Clinical Practice (GCP) | **Harmonized practices** — data integrity, informed consent |

---

## 8. Next Steps and Recommendations

### 8.1 Immediate Opportunities (Low Effort, High Value)

1. **Document IDE Discovery Workflow:**
   - Update `/fda-tools:trials` documentation to highlight IDE study discovery
   - Add example query: `/fda-tools:trials --product-code XXX --status recruiting`

2. **Create IDE Guidance Shortcut:**
   - Add pre-configured `/fda-tools:guidance "IDE"` query to return SR/NSR guidance

3. **Sample Size Calculator Enhancements:**
   - Add equivalence and superiority trial designs to `/fda-tools:calc`
   - Provide FDA-aligned defaults (80% power, 5% alpha)

### 8.2 Medium-Term Development (Moderate Effort)

4. **IDE Protocol Template:**
   - Create `/fda-tools:ide-protocol` command with 21 CFR 812.25-compliant template
   - Populate from existing device profile data
   - Include risk analysis section referencing MAUDE data

5. **ClinicalTrials.gov Enhanced Integration:**
   - Add `--ide-only` filter to `/fda-tools:trials` (filter for interventional device studies)
   - Parse and display IDE-specific fields: IRB, enrollment status, completion dates

### 8.3 Long-Term Strategy (High Effort)

6. **IDE Monitoring Dashboard:**
   - Build `/fda-tools:ide-monitor` command for compliance tracking
   - UADE event logging and deadline calculations
   - Annual report generation

7. **IDE-to-Submission Bridge:**
   - Create `/fda-tools:ide-to-submission` command
   - Auto-populate 510(k)/PMA clinical sections from IDE data
   - Generate clinical evidence summaries

8. **Advanced Statistical Tools:**
   - Expand `/fda-tools:calc` to support adaptive trial designs
   - Time-to-event (survival) analysis sample size
   - Bayesian adaptive designs

---

## 9. Conclusion

The FDA IDE pathway is well-documented and highly structured, with clear regulatory requirements under 21 CFR Part 812. The **fda-tools plugin currently provides foundational support** for IDE trial discovery via the `/fda-tools:trials` command, which integrates with ClinicalTrials.gov API v2.

**Key Gaps:**
- No dedicated IDE protocol drafting tools
- Limited sample size calculator capabilities (basic designs only)
- No IDE compliance monitoring/tracking features
- No IDE approval letter database (not publicly available from FDA)

**Strategic Recommendations:**
1. **Enhance `/fda-tools:calc`** with equivalence/superiority trial designs
2. **Create `/fda-tools:ide-protocol`** command to generate 21 CFR 812.25-compliant investigational plans
3. **Add IDE monitoring dashboard** to track UADE events, annual reports, and enrollment
4. **Document existing IDE capabilities** in `/fda-tools:trials` and `/fda-tools:guidance` commands

**Impact:** These enhancements would position the fda-tools plugin as a comprehensive IDE lifecycle tool, supporting clinical investigators from protocol design through marketing application submission.

---

## Appendix A: IDE Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    IDE Lifecycle                                │
└─────────────────────────────────────────────────────────────────┘

1. PROTOCOL DEVELOPMENT
   ├─ Risk Determination (SR vs NSR)
   ├─ Sample Size Calculation → [/fda-tools:calc sample-size]
   ├─ Protocol Drafting → [PROPOSED: /fda-tools:ide-protocol]
   └─ Peer Study Research → [/fda-tools:trials]

2. IDE SUBMISSION (SR only)
   ├─ FDA Review (30 days)
   ├─ IRB Approval
   └─ ClinicalTrials.gov Registration

3. STUDY CONDUCT
   ├─ Enrollment Tracking → [PROPOSED: /fda-tools:ide-monitor]
   ├─ UADE Reporting (10 working days)
   ├─ Annual Reports (yearly for SR)
   └─ Protocol Amendments

4. STUDY COMPLETION
   ├─ Final Report to FDA/IRB
   ├─ ClinicalTrials.gov Results Posting
   └─ Literature Publication

5. MARKETING APPLICATION
   ├─ Clinical Data Extraction → [PROPOSED: /fda-tools:ide-to-submission]
   ├─ 510(k) or PMA Submission → [/fda-tools:draft clinical]
   └─ FDA Review

                    ↓

            MARKETING CLEARANCE/APPROVAL
```

## Appendix B: Sample IDE Protocol Outline

**Title:** Investigational Plan for [Device Name] — [Indication]

1. **Purpose of Investigation**
   - Device description and intended use
   - Study objectives (primary/secondary endpoints)

2. **Protocol**
   - Study design (RCT, single-arm, etc.)
   - Population (inclusion/exclusion criteria)
   - Sample size justification
   - Randomization/blinding procedures
   - Follow-up schedule

3. **Risk Analysis**
   - Known device risks (from predicate devices, bench testing)
   - Comparison to standard of care
   - Mitigation strategies

4. **Device Description**
   - Components, materials, sterilization
   - Anticipated modifications during study

5. **Monitoring Procedures**
   - Data safety monitoring board (DSMB) charter
   - Interim analysis plan
   - Stopping rules

6. **Labeling**
   - Investigational use label text
   - IFU for investigators

7. **IRB Information**
   - Reviewing IRB name/address
   - IRB approval status

8. **Informed Consent**
   - Consent form template
   - HIPAA authorization

---

## References

**FDA Regulations:**
- [21 CFR Part 812 — Investigational Device Exemptions](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-812)
- [21 CFR Part 50 — Protection of Human Subjects](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-50)
- [21 CFR Part 56 — Institutional Review Boards](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-56)
- [42 CFR Part 11 — Clinical Trials Registration](https://www.ecfr.gov/current/title-42/chapter-I/subchapter-A/part-11)

**FDA Guidance:**
- [Significant Risk and Nonsignificant Risk Medical Device Studies (2006)](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/significant-risk-and-nonsignificant-risk-medical-device-studies)
- [Investigational Device Exemption (IDE) Guidance](https://www.fda.gov/medical-devices/investigational-device-exemption-ide/ide-responsibilities)

**External APIs:**
- [ClinicalTrials.gov API v2](https://clinicaltrials.gov/api/v2/studies)
- [openFDA Device API](https://open.fda.gov/apis/device/)

**Standards:**
- ISO 14155:2020 — Clinical investigation of medical devices for human subjects
- ICH E6(R2) — Good Clinical Practice
- ICH E9 — Statistical Principles for Clinical Trials

---

**Document Status:** Research complete. Ready for technical review and feature prioritization.
