# CDRH Review Structure Reference

Comprehensive mapping of FDA Center for Devices and Radiological Health (CDRH) organizational structure, review team composition, deficiency templates, and SE decision framework for simulating FDA review perspectives.

## 1. OHT Organizational Mapping

### Office of Product Evaluation and Quality (OPEQ) — OHT Structure

| OHT | Office Name | Advisory Committee Codes | Key Device Types |
|-----|-------------|-------------------------|------------------|
| OHT1 | Office of Ophthalmic, Anesthesia, Respiratory, ENT, and Dental Devices | AN, DE, EN, OP | Anesthesia machines, dental implants, contact lenses, ENT devices, respiratory devices |
| OHT2 | Office of Cardiovascular Devices | CV | Cardiac stents, pacemakers, heart valves, vascular grafts, catheters |
| OHT3 | Office of Gastrorenal, ObGyn, General Hospital, and Urology Devices | GU, HO, OB | GI endoscopes, renal dialysis, surgical robots, OB/GYN devices |
| OHT4 | Office of Surgical and Infection Control Devices | SU | Surgical instruments, wound care, sterilizers, surgical meshes |
| OHT5 | Office of Neurological and Physical Medicine Devices | NE, PM | Neurostimulators, EEG, physical therapy devices, wheelchairs |
| OHT6 | Office of Orthopedic Devices | OR | Hip/knee implants, spinal devices, fracture fixation, bone cement |
| OHT7 | Office of In Vitro Diagnostics | CH, HE, IM, MI, PA, TX | IVDs, clinical chemistry, hematology, immunology, microbiology |
| OHT8 | Office of Radiological Health | RA | X-ray, CT, MRI, ultrasound, radiation therapy |

### Division-Level Detail

#### OHT1 — Ophthalmic, Anesthesia, Respiratory, ENT, Dental
- **DHT1A** — Division of Ophthalmic Devices: IOLs, contact lenses, vitreoretinal devices
- **DHT1B** — Division of Anesthesia, Respiratory, and General Hospital Devices: ventilators, anesthesia machines, infusion pumps
- **DHT1C** — Division of ENT Devices: hearing aids, cochlear implants, tympanostomy tubes
- **DHT1D** — Division of Dental Devices: implants, restorative materials, orthodontic devices

#### OHT2 — Cardiovascular
- **DHT2A** — Division of Cardiac Electrical Devices: pacemakers, ICDs, CRT, leads
- **DHT2B** — Division of Cardiovascular and Peripheral Interventional Devices: stents, balloons, PTA catheters
- **DHT2C** — Division of Structural and Valvular Heart Devices: heart valves, septal occluders, LAA closure
- **DHT2D** — Division of Vascular and General Surgical Devices: vascular grafts, filters, surgical hemostats

#### OHT3 — Gastrorenal, ObGyn, General Hospital, Urology
- **DHT3A** — Division of Gastroenterology and Renal Devices: endoscopes, dialysis, lithotripsy
- **DHT3B** — Division of Reproductive, Abdominal, and Radiological Devices
- **DHT3C** — Division of General Hospital, Urological, and Gynecological Devices

#### OHT4 — Surgical and Infection Control
- **DHT4A** — Division of General and Restorative Devices: wound dressings, surgical instruments
- **DHT4B** — Division of Infection Control Devices: sterilizers, disinfectants
- **DHT4C** — Division of Surgical Devices: powered surgical instruments, electrosurgery

#### OHT5 — Neurological and Physical Medicine
- **DHT5A** — Division of Central Nervous System Devices: neurostimulators, shunts
- **DHT5B** — Division of Peripheral and Electrophysical Devices: EMG, TENS
- **DHT5C** — Division of Physical Medicine Devices: wheelchairs, prosthetics

#### OHT6 — Orthopedic
- **DHT6A** — Division of Joint Arthroplasty: hip/knee/shoulder replacements
- **DHT6B** — Division of Spinal Devices: fusion, disc replacement, pedicle screws
- **DHT6C** — Division of Trauma and Restorative Devices: fracture fixation, bone cement, scaffolds

#### OHT7 — In Vitro Diagnostics
- **DHT7A** — Division of Chemistry and Toxicology: glucose, lipids, drug testing
- **DHT7B** — Division of Microbiology: culture, susceptibility, molecular diagnostics
- **DHT7C** — Division of Immunology and Hematology: blood banking, coagulation, flow cytometry
- **DHT7D** — Division of Molecular Genetics and Pathology: NGS, FISH, companion diagnostics

#### OHT8 — Radiological Health
- **DHT8A** — Division of Imaging Diagnostics: X-ray, CT, MRI, ultrasound
- **DHT8B** — Division of Radiological Health: radiation therapy, laser, LINAC

### Product Code to OHT Mapping

Use the `review_panel` field from openFDA classification to determine OHT:

```python
PANEL_TO_OHT = {
    "AN": "OHT1", "DE": "OHT1", "EN": "OHT1", "OP": "OHT1",
    "CV": "OHT2",
    "GU": "OHT3", "HO": "OHT3", "OB": "OHT3",
    "SU": "OHT4",
    "NE": "OHT5", "PM": "OHT5",
    "OR": "OHT6",
    "CH": "OHT7", "HE": "OHT7", "IM": "OHT7", "MI": "OHT7", "PA": "OHT7", "TX": "OHT7",
    "RA": "OHT8",
}
```

## 2. Review Team Composition Decision Tree

### Core Reviewers (Always Present)

| Role | Trigger | Evaluation Focus |
|------|---------|-----------------|
| **Lead Reviewer** | Always assigned | SE determination, predicate appropriateness, intended use analysis, overall recommendation |
| **Team Lead** | Always (supervisory) | Policy consistency, risk classification, predicate precedent, quality of review |
| **Labeling Reviewer** | Always | 21 CFR 801 compliance, IFU adequacy, warnings, contraindications, user instructions |

### Specialist Reviewers (Conditionally Assigned)

| Role | Trigger Condition | Evaluation Focus | Key Standards |
|------|-------------------|-----------------|---------------|
| **Clinical Reviewer** | Clinical data submitted OR Class III OR guidance requires clinical data | Study design, statistical analysis, endpoints, patient safety | ICH GCP, FDA clinical guidance |
| **Biocompatibility Reviewer** | Patient-contacting OR implantable | ISO 10993 battery selection, material characterization, toxicological risk assessment | ISO 10993-1:2018, ISO 10993-5, -10, -11 |
| **Software Reviewer** | Has software component OR SaMD | Software level of concern, cybersecurity, AI/ML considerations, SBOM | IEC 62304, FDA cybersecurity guidance |
| **Sterilization Reviewer** | Provided sterile | Sterilization validation, SAL, residuals, reprocessing (if reusable) | ISO 11135, ISO 11137, ISO 17665 |
| **Electrical/EMC Reviewer** | Electrically powered | Electrical safety, EMC testing, RF emissions/immunity | IEC 60601-1, IEC 60601-1-2 |
| **Human Factors Reviewer** | User interface OR home use OR critical use tasks | Use-related risk analysis, formative/summative usability testing | IEC 62366-1, FDA HF guidance (2016) |
| **Reprocessing Reviewer** | Reusable device | Cleaning validation, disinfection/sterilization adequacy | FDA reprocessing guidance |
| **MRI Safety Reviewer** | Implantable OR metallic components | MR Conditional/Unsafe classification, heating, force, artifact testing | ASTM F2052, F2213, F2182, F2119 |
| **Materials Reviewer** | Novel material OR new alloy/polymer | Material characterization, biocompatibility rationale, degradation | ISO 10993-13, -14, -15 |
| **Packaging Reviewer** | Sterile barrier OR shelf life claim | Package integrity, aging validation, transport | ASTM F2095, ASTM D4169 |

### Auto-Detection Logic

```python
def determine_review_team(device_info, classification_data):
    """Determine specialist reviewers needed based on device characteristics."""
    team = ["Lead Reviewer", "Team Lead", "Labeling"]

    # Clinical
    if (classification_data.get("device_class") == "3" or
        device_info.get("clinical_data_submitted") or
        device_info.get("guidance_requires_clinical")):
        team.append("Clinical")

    # Biocompatibility
    if (device_info.get("patient_contacting") or
        device_info.get("implantable") or
        "biocompatib" in str(device_info.get("device_description", "")).lower()):
        team.append("Biocompatibility")

    # Software
    software_keywords = ["software", "firmware", "app", "algorithm", "samd",
                         "artificial intelligence", "machine learning", "ai/ml"]
    desc_lower = str(device_info.get("device_description", "")).lower()
    if any(kw in desc_lower for kw in software_keywords):
        team.append("Software")

    # Sterilization
    if device_info.get("provided_sterile") or "steril" in desc_lower:
        team.append("Sterilization")

    # Electrical/EMC
    electrical_keywords = ["electrical", "powered", "battery", "mains", "rechargeable",
                           "wireless", "bluetooth", "rf", "electromagnetic"]
    if any(kw in desc_lower for kw in electrical_keywords):
        team.append("Electrical/EMC")

    # Human Factors
    hf_keywords = ["touchscreen", "display", "user interface", "home use",
                   "patient-operated", "over-the-counter", "otc"]
    if any(kw in desc_lower for kw in hf_keywords):
        team.append("Human Factors")

    # Reprocessing
    if device_info.get("reusable") or "reusab" in desc_lower:
        team.append("Reprocessing")

    # MRI Safety
    if (device_info.get("implantable") or
        "metallic" in desc_lower or "metal" in desc_lower or
        "implant" in desc_lower):
        team.append("MRI Safety")

    return team
```

## 3. RTA (Refuse to Accept) Screening Criteria

Per SOPP 8217 and FDA's Refuse to Accept Policy for 510(k)s (2019 guidance):

### Administrative RTA Checklist

| # | Criterion | Check Method | RTA if Missing |
|---|-----------|-------------|----------------|
| 1 | Cover letter present | Check for cover_letter draft | Yes |
| 2 | CDRH Premarket Review Submission Cover Sheet (FDA Form 3514) | Check for form reference | Yes |
| 3 | Indications for Use Statement (FDA Form 3881) | Check for IFU or intended_use | Yes |
| 4 | 510(k) Summary OR Statement | Check for 510k_summary draft | Yes |
| 5 | Truthful and Accuracy Statement | Check for truthful_accuracy draft | Yes |
| 6 | Class III Summary and Certification (if Class III) | Check device class | Conditional |
| 7 | Financial Certification or Disclosure (if clinical data) | Check for financial_certification draft | Conditional |
| 8 | Declarations of Conformity (if standards cited) | Check for doc draft | Conditional |
| 9 | Device description | Check for device_description draft or --device-description | Yes |
| 10 | Predicate comparison / SE discussion | Check for se_discussion draft or compare-se output | Yes |
| 11 | Proposed labeling | Check for labeling draft | Yes |
| 12 | Performance data to support SE | Check for performance or testing data | Yes |
| 13 | Sterility information (if applicable) | Check for sterilization draft | Conditional |
| 14 | Biocompatibility information (if applicable) | Check for biocompatibility draft | Conditional |
| 15 | Software documentation (if applicable) | Check for software draft | Conditional |
| 16 | EMC/Electrical safety (if applicable) | Check for emc_electrical draft | Conditional |

### Substantive RTA Screening

| Criterion | What to Check | Common Deficiency |
|-----------|--------------|-------------------|
| Predicate identified | K-number in review.json or proposal | "No predicate device identified" |
| Same intended use | IFU comparison performed | "Intended use not compared to predicate" |
| SE comparison present | compare-se output exists | "Substantial equivalence comparison incomplete" |
| Performance data described | Test plan or results referenced | "Performance testing not described" |

## 4. Common Deficiency (AI Request) Templates

### Lead Reviewer Deficiencies

**Predicate Selection:**
> The predicate device, {K-number} ({device_name}), does not appear to have the same intended use as the subject device. Specifically, {specific IFU difference}. Please provide additional justification for why {K-number} is an appropriate predicate, or identify an alternative predicate device with the same intended use.

**SE Comparison:**
> The substantial equivalence comparison is incomplete. Please provide a comparison of the following technological characteristics between the subject and predicate devices: {missing characteristics}. For each difference identified, please explain why the difference does not raise new questions of safety and effectiveness, or provide additional data to support equivalence.

**Intended Use:**
> The proposed indications for use expand beyond those of the predicate device. Specifically, the subject device claims {expanded claim} while the predicate is limited to {predicate claim}. Please either: (1) narrow the proposed indications to match the predicate, (2) provide clinical data supporting the expanded indication, or (3) identify an additional predicate that supports the expanded claim.

**Performance Data:**
> The submission does not include adequate performance data to support substantial equivalence. Please provide the results of {specific testing} conducted in accordance with {applicable standard}.

### Clinical Reviewer Deficiencies

**Study Design:**
> The clinical study submitted in support of the {device} has the following deficiency: {specific issue}. Please provide: (1) justification for the study design, including sample size calculation; (2) the pre-specified primary endpoint and statistical analysis plan; (3) subject accountability data.

**Statistical Analysis:**
> The statistical analysis of the clinical data is insufficient. Specifically: {issue}. Please provide: (1) the pre-specified analysis plan; (2) appropriate confidence intervals; (3) missing data handling methodology.

**Clinical Relevance:**
> The clinical performance endpoints do not adequately demonstrate clinical effectiveness for the intended use. Please provide additional clinical evidence demonstrating {specific outcome} in the target patient population.

### Biocompatibility Reviewer Deficiencies

**ISO 10993 Battery:**
> The biocompatibility evaluation is incomplete per ISO 10993-1:2018. Based on the device contact type ({contact_type}) and duration ({duration}), the following tests are required but not provided: {missing tests}. Please submit the complete biocompatibility test report(s) or provide a risk-based rationale for omitting specific tests per the biocompatibility evaluation flowchart.

**Material Characterization:**
> The submission does not include adequate material characterization. Please provide: (1) chemical composition of all patient-contacting materials; (2) material specifications and certificates of analysis; (3) extractables/leachables data per ISO 10993-12 and -18.

**New Material:**
> The subject device uses {material} which was not present in the predicate device. Please provide: (1) complete biocompatibility testing per ISO 10993-1:2018 for this material; (2) a toxicological risk assessment; (3) justification for material selection.

### Software Reviewer Deficiencies

**Documentation Level:**
> The software documentation level of concern is not adequately justified. Per IEC 62304, please provide: (1) the assigned software safety classification with rationale; (2) software requirements specification; (3) software architecture design; (4) verification and validation summary.

**Cybersecurity:**
> The cybersecurity documentation is incomplete. Per the FDA cybersecurity guidance (2023), please provide: (1) a threat model; (2) cybersecurity risk assessment; (3) Software Bill of Materials (SBOM); (4) vulnerability assessment and management plan; (5) documentation of security controls implemented.

**AI/ML:**
> The device incorporates {AI/ML component}. Please provide: (1) algorithm description including training methodology; (2) training, validation, and test datasets with demographic distribution; (3) performance metrics on independent test set; (4) predetermined change control plan (if applicable per FDA's AI/ML guidance).

### Sterilization Reviewer Deficiencies

**Validation:**
> The sterilization validation is incomplete. Please provide: (1) sterilization method selection rationale; (2) bioburden data; (3) dose/cycle verification studies; (4) SAL demonstration (10^-6 minimum); (5) residuals data (if EO sterilization: EO, ECH per ISO 10993-7).

**Reprocessing:**
> For this reusable device, the reprocessing validation is incomplete. Please provide: (1) cleaning validation per FDA reprocessing guidance; (2) disinfection/sterilization validation; (3) worst-case soil challenge studies; (4) functional testing after reprocessing cycles.

### Electrical/EMC Reviewer Deficiencies

**IEC 60601-1:**
> The electrical safety testing is incomplete per IEC 60601-1:2005+A1+A2. Please provide test reports for: {missing clauses}. Include results for all applied parts and all configurations of use.

**IEC 60601-1-2:**
> The EMC testing per IEC 60601-1-2:2014+A1 is incomplete. Please provide: (1) essential performance identification; (2) immunity test results at specified levels; (3) emissions test results; (4) electromagnetic environment assessment for intended use locations.

### Human Factors Reviewer Deficiencies

**Usability Testing:**
> Human factors data is required per the FDA guidance "Applying Human Factors and Usability Engineering to Medical Devices" (2016). Please provide: (1) use-related risk analysis; (2) formative evaluation results (heuristic evaluation, cognitive walkthrough, or simulated-use study); (3) summative (validation) usability test with minimum 15 participants per user group.

**IFU Validation:**
> The Instructions for Use (IFU) have not been validated with representative users. Please provide usability test results demonstrating that users can safely and effectively use the device following the IFU, including: (1) task completion rates; (2) use errors identified; (3) close calls; (4) root cause analysis for critical use errors.

### MRI Safety Reviewer Deficiencies

**MR Conditional Labeling:**
> The device is labeled as "MR Conditional" but the testing is incomplete. Please provide: (1) magnetically induced displacement force testing per ASTM F2052; (2) magnetically induced torque testing per ASTM F2213; (3) RF heating testing per ASTM F2182; (4) artifact assessment per ASTM F2119. Specify the MR conditions under which testing was performed (static field strength, spatial gradient, RF field, SAR).

## 5. SE Decision Framework — Reviewer's Perspective

### The SE Determination Flowchart (per SOPP 26.2.1)

```
1. Does the subject device have the SAME intended use as the predicate?
   → NO: SE cannot be found. Issue NSE or request different predicate.
   → YES: Continue ↓

2. Does the subject device have the SAME technological characteristics?
   → YES: SE can be found (simplest path). Document in review memo.
   → NO: Continue ↓

3. Do the DIFFERENT technological characteristics raise NEW questions
   of safety and effectiveness?
   → NO: SE can be found. Document why differences don't raise new questions.
   → YES: Continue ↓

4. Can the NEW questions be resolved with the data provided?
   → YES: SE can be found. Document how data resolves questions.
   → NO: Issue AI request for additional data OR issue NSE determination.
```

### SE Determination Factors

| Factor | Supports SE | Opposes SE |
|--------|------------|-----------|
| Intended use | Identical or narrower | Broader or different |
| Technology | Same principle of operation | Different principle |
| Materials | Same or equivalent biocompatibility | New uncharacterized materials |
| Performance | Meets or exceeds predicate | Lower performance |
| Safety profile | Equivalent or better | New risks |
| Predicate age | Recent (<10 years) | Very old (>15 years) |
| Predicate chain | Healthy, continuous | Broken, recalled |
| Clinical data | Not required or provided | Required but missing |

### NSE (Not Substantially Equivalent) Triggers

- Different intended use with no alternative predicate
- Fundamental change in technology raising clinical questions
- Safety data showing new or increased risks
- Recall of predicate for design-related reason
- Multiple accumulated differences (predicate creep concern)

## 6. SOPP References

### Key Standard Operating Procedures

| SOPP | Title | Relevance |
|------|-------|-----------|
| SOPP 8217 | Administrative Processing and Review of 510(k)s | Overall 510(k) review process, timelines |
| SOPP 26.2.1 | SE Determination Decision-Making | How reviewers decide SE/NSE |
| SOPP 8218 | Refuse to Accept (RTA) Policy | Pre-screening criteria |
| SOPP 26.2.2 | Split Predicates in 510(k) Review | Multiple predicate policy |

### Q-Sub Program (Pre-Submission)

Per FDA's Q-Submission Program Guidance:

| Aspect | Detail |
|--------|--------|
| Meeting types | Written Feedback Only, Teleconference, In-Person |
| Timeline | FDA targets 75 calendar days from receipt to meeting |
| Content | Cover letter, device description, proposed testing, specific questions |
| Question limit | 5-7 questions recommended |
| Follow-up | Additional Q-Sub if significant changes from FDA feedback |

### Review Timelines (MDUFA V Performance Goals)

| Submission Type | Review Goal | Calendar Days |
|----------------|------------|---------------|
| Traditional 510(k) | Substantive review decision | 90 FDA days |
| Special 510(k) | Substantive review decision | 30 FDA days |
| Abbreviated 510(k) | Substantive review decision | 90 FDA days |
| De Novo | Decision | 150 FDA days |
| Pre-Sub response | Meeting/feedback | 75 calendar days |
| RTA screening | Accept/Refuse | 15 FDA days |

## 7. Historical Deficiency Patterns by Device Type

### Orthopedic Devices (OHT6)

**Most Common Deficiencies:**
1. **Fatigue testing gaps** — Missing worst-case loading, inadequate cycle count, non-physiological test setup
2. **Biocompatibility for new alloys** — Ti-6Al-4V variants, porous coatings, 3D-printed materials need full battery
3. **Predicate age** — Many ortho predicates are 15+ years old; FDA increasingly questioning relevance
4. **Wear testing** — Insufficient wear simulation duration, missing wear debris analysis
5. **Spinal fixation** — Subsidence testing, range of motion data, adjacent level effects

**Typical AI Request:**
> Please provide fatigue testing per ASTM F2077 (spinal) or ASTM F2068 (hip) under worst-case loading conditions. Include test sample size justification, failure mode analysis, and comparison to predicate test results.

### Cardiovascular Devices (OHT2)

**Most Common Deficiencies:**
1. **Biocompatibility duration** — Long-term implant contact requires extended ISO 10993 battery
2. **MRI safety** — Implantable cardiovascular devices must address MR safety per ASTM standards
3. **Clinical data expectations** — Higher-risk CV devices often need clinical evidence
4. **Hemodynamic testing** — Incomplete flow loop testing, missing physiological conditions
5. **Corrosion/degradation** — Metallic implants need corrosion testing per ASTM F2129

**Typical AI Request:**
> Please provide biocompatibility testing for permanent implant contact (>30 days) per ISO 10993-1:2018 Table A.1, including: cytotoxicity, sensitization, irritation, acute systemic toxicity, subchronic/subacute toxicity, genotoxicity, implantation, and hemocompatibility.

### Software/SaMD (Cross-OHT)

**Most Common Deficiencies:**
1. **Documentation level justification** — Inadequate rationale for IEC 62304 software safety class
2. **Cybersecurity** — Missing threat model, SBOM, vulnerability management plan
3. **AI/ML validation** — Insufficient test dataset diversity, missing subgroup analysis
4. **Interoperability** — Integration testing with intended platforms not documented
5. **Software updates** — Post-market update management plan missing

**Typical AI Request:**
> The software documentation is insufficient per IEC 62304. Please provide: (1) Software safety classification with rationale per IEC 62304 Clause 4.3; (2) Software requirements specification; (3) Software architecture; (4) Verification testing results including unit, integration, and system testing; (5) Anomaly list with risk assessment.

### In Vitro Diagnostics (OHT7)

**Most Common Deficiencies:**
1. **Analytical performance** — Insufficient precision, accuracy, linearity, LOD/LOQ data
2. **Clinical performance** — Inadequate comparison to reference method or predicate
3. **Reference standard traceability** — Missing traceability to NIST or WHO standards
4. **Interference testing** — Incomplete endogenous and exogenous substance testing
5. **Matrix effects** — Insufficient sample type validation

**Typical AI Request:**
> Please provide analytical performance data including: (1) Precision (repeatability and reproducibility) per CLSI EP05; (2) Method comparison to reference/predicate per CLSI EP09; (3) Linearity/measuring interval per CLSI EP06; (4) Limit of Detection per CLSI EP17; (5) Interference testing per CLSI EP07.

### Wound Care / Surgical (OHT4)

**Most Common Deficiencies:**
1. **Antimicrobial testing** — Inadequate zone of inhibition or time-kill studies
2. **MVTR data** — Missing moisture vapor transmission rate for wound dressings
3. **Absorption capacity** — Insufficient fluid handling characterization
4. **Dressing composition** — Incomplete material characterization for multi-layer dressings
5. **Biocompatibility** — Especially for antimicrobial agents (silver, iodine)

**Typical AI Request:**
> Please provide performance testing for the wound dressing including: (1) Fluid handling capacity per BS EN 13726-1; (2) Moisture vapor transmission rate; (3) Antimicrobial efficacy testing (zone of inhibition, time-kill) per appropriate method; (4) Biocompatibility of antimicrobial agent per ISO 10993-5 and -10.

### Respiratory / Anesthesia (OHT1)

**Most Common Deficiencies:**
1. **Breathing system compliance** — Missing ISO 80601 series testing
2. **Alarm performance** — Inadequate alarm testing per IEC 60601-1-8
3. **Gas delivery accuracy** — Insufficient flow/concentration accuracy data
4. **Patient circuit compatibility** — Missing standard connector testing
5. **Cleaning validation** — For reusable respiratory components

**Typical AI Request:**
> Please provide testing per the applicable particular standard (ISO 80601-2-{XX}) including: (1) Essential performance verification; (2) Alarm performance per IEC 60601-1-8; (3) Accuracy of gas delivery; (4) Patient circuit compliance.

### Radiological Devices (OHT8)

**Most Common Deficiencies:**
1. **Radiation dose** — Missing dose measurement or dose reduction claims not supported
2. **Image quality** — Inadequate phantom testing or MTF/NPS measurements
3. **Software** — Display software needs IEC 62304 documentation
4. **Electromagnetic compatibility** — High-power systems need thorough EMC
5. **Patient dose management** — Missing dose display or DICOM dose reporting

## 8. Submission Readiness Scoring

### Score Components (0-100)

| Component | Weight | Scoring |
|-----------|--------|---------|
| RTA completeness | 25 pts | 25 × (items present / items required) |
| Predicate quality | 20 pts | Average predicate confidence score × 0.2 |
| SE comparison | 15 pts | 15 if complete, 8 if partial, 0 if missing |
| Testing coverage | 15 pts | 15 × (tests planned / tests required from guidance) |
| Deficiency count | 15 pts | 15 - (3 × critical) - (1 × major) |
| Documentation quality | 10 pts | 10 if all sections drafted, 5 if partial |

### Readiness Tiers

| Score | Tier | Interpretation |
|-------|------|---------------|
| 85-100 | Ready | High confidence of acceptance; minor items only |
| 70-84 | Nearly Ready | A few gaps to close; address before submitting |
| 50-69 | Significant Gaps | Major items missing; address deficiencies |
| 30-49 | Not Ready | Substantial work needed; consider Pre-Sub first |
| 0-29 | Early Stage | Project in early planning; not ready for review simulation |

### Remediation Action Mapping

Each deficiency maps to a specific `/fda:` command:

| Deficiency Area | Remediation Command |
|----------------|-------------------|
| Missing predicate | `/fda:propose --predicates K123456 --project NAME` |
| Incomplete SE comparison | `/fda:compare-se --infer --project NAME` |
| Missing guidance analysis | `/fda:guidance CODE --save --project NAME` |
| Missing test plan | `/fda:test-plan --project NAME` |
| Missing draft sections | `/fda:draft SECTION --project NAME` |
| Missing safety data | `/fda:safety --product-code CODE --project NAME` |
| Missing literature | `/fda:literature CODE --project NAME` |
| Missing standards | `/fda:standards CODE --project NAME` |
| Missing traceability | `/fda:traceability --project NAME` |
| Missing DoC | `/fda:draft doc --project NAME` |
| Missing risk analysis | `/fda:draft risk-management --project NAME` |

## Cross-References

- `rta-checklist.md` — Detailed RTA screening items
- `predicate-analysis-framework.md` — Deep predicate analysis methodology
- `confidence-scoring.md` — Predicate confidence scoring algorithm
- `guidance-lookup.md` — Cross-cutting guidance requirements
- `risk-management-framework.md` — ISO 14971 risk management
- `human-factors-framework.md` — IEC 62366-1 human factors
- `cybersecurity-framework.md` — Cybersecurity documentation requirements
- `clinical-data-framework.md` — Clinical evidence requirements
- `submission-structure.md` — eSTAR section structure
