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
| **IVD Reviewer** | Review panel in {CH, HE, IM, MI, PA, TX} OR IVD/diagnostic/assay keywords | CLIA classification, analytical validation (CLSI EP series), clinical validation, reference standards | 21 CFR 809, CLSI EP05/EP07/EP09/EP12/EP17 |

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
    reprocess_keywords = ["reusab", "reprocess", "endoscop", "bronchoscop",
                          "duodenoscop", "arthroscop", "laparoscop"]
    if device_info.get("reusable") or any(kw in desc_lower for kw in reprocess_keywords):
        team.append("Reprocessing")

    # MRI Safety
    if (device_info.get("implantable") or
        "metallic" in desc_lower or "metal" in desc_lower or
        "implant" in desc_lower):
        team.append("MRI Safety")

    # Materials
    materials_keywords = ["3d print", "additive manufactur", "novel material",
                          "novel alloy", "novel polymer", "nanostructur",
                          "titanium alloy", "peek", "nitinol", "cobalt chrome"]
    if any(kw in desc_lower for kw in materials_keywords):
        team.append("Materials")

    # Packaging
    if (device_info.get("provided_sterile") or
        device_info.get("shelf_life") or
        "sterile barrier" in desc_lower or
        "shelf life" in desc_lower or
        "package integrit" in desc_lower):
        team.append("Packaging")

    # IVD (In Vitro Diagnostic)
    ivd_panels = {"CH", "HE", "IM", "MI", "PA", "TX"}
    ivd_keywords = ["ivd", "diagnostic", "assay", "clia", "analyte", "specimen",
                    "in vitro", "reagent", "immunoassay", "clinical chemistry"]
    if (classification_data.get("review_panel") in ivd_panels or
        any(kw in desc_lower for kw in ivd_keywords)):
        team.append("IVD")

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

### Reprocessing Reviewer (if reusable device)

**Trigger:** Device labeled as reusable, requires cleaning/disinfection/sterilization between uses

**Regulatory basis:** FDA Reprocessing Guidance, 21 CFR 820.30(g), AAMI TIR12, AAMI TIR30, AAMI ST79

**Assessment criteria:**
- Reprocessing instructions present and adequate?
  - Cleaning agents specified (enzymatic, non-enzymatic)?
  - Minimum effective concentration and contact time?
  - Rinse requirements (water quality, volume)?
  - Disinfection/sterilization method if required between uses?
- Worst-case soil testing performed (AAMI TIR30)?
  - Artificial test soil composition appropriate for device use?
  - Visual and quantitative endpoints (protein, hemoglobin, endotoxin)?
- Simulated-use testing with clinically relevant protocols?
- Validation of cleaning for complex device geometries (lumens, hinges, crevices)?
- Number of reprocessing cycles validated (minimum equals device lifetime)?
- Bioburden and endotoxin limits after reprocessing?

**Deficiency template:**
> The submission does not include adequate reprocessing validation data for this reusable device. Per FDA guidance on reprocessing, validation must demonstrate that the recommended cleaning and disinfection/sterilization instructions can reliably render the device safe for reuse. Specifically, [missing element] has not been addressed.

**Score:** reprocessing items addressed / reprocessing items required

### Packaging Reviewer (if sterile device)

**Trigger:** Device labeled sterile, shipped in sterile packaging

**Regulatory basis:** ISO 11607-1 (packaging materials), ISO 11607-2 (validation), ASTM F88 (seal strength), ASTM F2095 (bubble leak), ASTM D4169 (distribution simulation)

**Assessment criteria:**
- Package design qualification complete?
  - Materials compatibility with sterilization method?
  - Microbial barrier properties verified?
  - Seal integrity validated (ASTM F88 seal strength, ASTM F2095 or equivalent)?
- Stability/aging testing performed?
  - Accelerated aging per ASTM F1980 with appropriate Q10?
  - Real-time aging data available or in progress?
  - Package integrity maintained through shelf life?
- Distribution simulation testing (ASTM D4169)?
  - Assurance level appropriate for distribution environment?
  - Package integrity maintained after simulated transport?
- Sterile barrier system (SBS) validated per ISO 11607-2?
- Labeling on packaging adequate?
  - Sterility claim on label?
  - Lot/batch identification?
  - Expiration date (if shelf life limited)?
  - UDI on package (21 CFR 801.20)?

**Deficiency template:**
> The submission does not include adequate packaging validation data for this sterile device. Per ISO 11607-1/-2, the sterile barrier system must be validated to maintain sterility through the labeled shelf life and distribution conditions. Specifically, [missing element] has not been addressed.

**Score:** packaging items addressed / packaging items required

### Materials Reviewer (if novel materials)

**Trigger:** Device uses materials not previously cleared in same contact type/duration, 3D-printed materials, novel polymers, novel metal alloys, or nanostructured materials

**Regulatory basis:** FDA guidance "Use of International Standard ISO 10993-1," 21 CFR 820.50 (purchasing controls), ISO 10993-18 (chemical characterization)

**Assessment criteria:**
- Complete material characterization per ISO 10993-18?
  - All patient-contacting materials identified by chemical name/grade?
  - Additives, colorants, processing aids documented?
  - Material specifications with acceptance criteria?
- Extractable and leachable (E&L) studies adequate?
  - Extraction conditions appropriate (ISO 10993-12)?
  - Analytical methods validated (GC-MS, LC-MS, ICP-MS)?
  - Toxicological risk assessment of identified leachables (ISO 10993-17)?
  - Threshold of Toxicological Concern (TTC) applied where appropriate?
- For 3D-printed/additive manufactured materials:
  - Process parameters documented (energy density, layer thickness, build orientation)?
  - Post-processing steps (heat treatment, machining, surface finishing) characterized?
  - Inter-build and intra-build consistency demonstrated?
  - Mechanical properties verified per device-specific standards?
- For novel alloys/polymers:
  - Composition and microstructure characterized?
  - Corrosion/degradation behavior assessed?
  - Wear debris characterization (if load-bearing application)?
- Material traceability and supplier qualification?
  - Raw material specifications and certificates of analysis?
  - Incoming material testing procedures?

**Deficiency template:**
> The submission describes the use of [material/process] which has not been previously cleared for this contact type and duration. Per FDA guidance and ISO 10993-18, a complete chemical characterization of the material is required, including extractable and leachable analysis with toxicological risk assessment. Specifically, [missing element] has not been addressed.

**Score:** materials items addressed / materials items required

### IVD Review — Analytical and Clinical Validation (OHT7 Devices)

**Trigger:** Review panel in {CH, HE, IM, MI, PA, TX} OR device description contains IVD/diagnostic/assay/CLIA keywords.

**Regulatory basis:** 21 CFR 809, CLIA '88, CLSI standards

**Evaluation categories:**
- CLIA classification (Waived / Moderate / High Complexity)?
- If CLIA waived: waiver study per CLSI EP12 (3 untrained operators, ≥120 specimens)?
- Accuracy/method comparison (CLSI EP09)?
- Precision study (CLSI EP05 — 20-day protocol)?
- Linearity/reportable range (CLSI EP06)?
- Analytical sensitivity — LOB/LOD/LOQ (CLSI EP17)?
- Interference study (CLSI EP07)?
- Reference interval (CLSI EP28)?
- Clinical agreement (sensitivity/specificity/PPA/NPA)?
- Specimen types validated?
- Calibration traceability (NIST/WHO/IFCC)?

**Deficiency templates:**

> **Analytical performance:** The submission does not include a [precision/accuracy/linearity/LOD] study per CLSI [EP05/EP09/EP06/EP17]. Please provide [study type] data to support the analytical performance claims for [analyte].

> **Clinical performance:** The clinical agreement study does not include sufficient specimens ({N} provided, ≥{M} expected) to support the intended use claim for [analyte/condition]. Please provide additional clinical data.

> **CLIA waiver:** The CLIA waiver study design is incomplete — [missing untrained operators / insufficient specimen count / no comparison to lab method]. Refer to CLSI EP12 for waiver study requirements.

> **Reference traceability:** Calibration traceability to [NIST/WHO/IFCC] reference materials is not documented. Please provide the traceability chain for calibration of [analyte].

**Score:** IVD items addressed / IVD items required

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

**Trigger:** Review panel = "OR" OR regulation number starts with "888"

**Regulatory basis:** 21 CFR 888, device-specific special controls guidance, FDA guidance on modified metallic surfaces, non-spinal bone plates guidance (2024)

**Division assignment:**
- DHT6A (Joint Arthroplasty): 888.33xx hip/knee/shoulder/ankle prostheses
- DHT6B (Spinal Devices): 888.3060-888.3085 pedicle screws, fusion, disc replacement
- DHT6C (Trauma & Restorative): 888.30xx fracture fixation, bone cement, bone grafts

**Assessment criteria:**

1. **MECHANICAL PERFORMANCE**
   - Static testing (compression, tension, torsion) per device-specific ASTM standard?
     - Spinal: ASTM F2077 (IBF), ASTM F1717 (constructs)
     - Hip: ASTM F2068 (femoral stem), ISO 7206-4/-6 (hip stem endurance)
     - Knee: ASTM F1800 (tibial tray), ISO 14879 (tibial components)
     - Trauma: ASTM F382 (bone plates), ASTM F543 (bone screws)
     - Vertebroplasty: ASTM F451, ISO 5833 (bone cement)
   - Dynamic fatigue under worst-case loading?
     - Minimum 5M cycles for joint prostheses (10M preferred)
     - Minimum 5M cycles for spinal constructs per ASTM F1717
   - Worst-case test configuration justified?
   - Sample size adequate? (Minimum N=3 per ASTM, N=6 recommended)

2. **WEAR TESTING** (if articulating surfaces)
   - Hip wear simulator per ISO 14242? (minimum 5M cycles; 10M for porous/coated)
   - Knee wear simulator per ISO 14243? (minimum 5M cycles)
   - Wear debris characterized (size, morphology, composition)?
   - Accelerated aging of polyethylene per ASTM F2003?
   - Metal ion release assessment (for CoCr bearing)?

3. **CORROSION TESTING** (if metallic implant)
   - Galvanic corrosion potential assessed (multi-metal constructs)?
   - Corrosion testing per ASTM F2129 (cyclic potentiodynamic polarization)?
   - Fretting corrosion at modular junctions per ASTM F1875?

4. **MATERIAL CHARACTERIZATION**
   - Composition per applicable ASTM spec (F136 Ti, F1537 CoCr, F138 SS, F648 UHMWPE, F2026 PEEK)?
   - Microstructure characterization?
   - Mechanical properties (tensile, yield, elongation, hardness)?

5. **SURFACE CHARACTERIZATION** (if coated/modified)
   - Porous coating: pore size, porosity, bond strength per ASTM F1147?
   - HA coating per ASTM F1185, ISO 13779?
   - 3D-printed surface per FDA AM guidance?

6. **BIOCOMPATIBILITY** (permanent implant — extended battery)
   - Full ISO 10993 battery (cytotoxicity, sensitization, irritation, acute/subchronic/chronic systemic toxicity, genotoxicity, implantation)?
   - Material equivalence per ISO 10993-18 if claiming via predicate?
   - E&L analysis for new materials/coatings?

7. **MRI SAFETY** (all metallic OR implants)
   - ASTM F2052, F2213, F2182, F2119 testing?
   - MR Conditional labeling per ASTM F2503?
   - Worst-case implant configuration tested?

8. **CLINICAL EVIDENCE** (may be required)
   - Literature review adequate for well-established predicates?
   - MAUDE adverse event analysis?
   - Fusion rates reported (spinal devices)?

**OR-Specific Deficiency Templates:**

> **Fatigue:** The submission does not include adequate fatigue testing data. Please provide fatigue testing per {ASTM F2077/F1717/F2068/ISO 7206} under worst-case loading conditions with a minimum of {5/10} million cycles. Include: (1) test sample size justification; (2) test setup and loading parameters; (3) failure mode analysis; (4) run-out criteria; (5) comparison to predicate test results.

> **Wear:** The submission does not include adequate wear testing. Please provide wear simulator testing per {ISO 14242/14243} for a minimum of {5/10} million cycles, including: (1) wear rate; (2) wear debris characterization (size distribution, morphology); (3) lubricant composition; (4) component positioning during test.

> **Corrosion:** For this multi-metal construct, corrosion susceptibility testing per ASTM F2129 and fretting corrosion testing per ASTM F1875 have not been provided. Please submit corrosion testing data.

> **MRI:** The device contains metallic components but no MRI safety testing has been provided. Per FDA guidance, please provide MRI safety testing per ASTM F2052, F2213, F2182, and F2119 for the worst-case implant configuration at {1.5T and/or 3T}.

**Score:** OR items addressed / OR items required

### Cardiovascular Devices (OHT2)

**Trigger:** Review panel = "CV" OR regulation_number starts with "870" OR product code in CV-panel codes.

**Regulatory basis:** 21 CFR Part 870, applicable device-specific guidance documents.

**DHT2A — Cardiac Electrical Devices (pacemakers, ICDs, CRT, leads):**

| Assessment Criterion | Regulatory Reference | Common Deficiency |
|---------------------|---------------------|-------------------|
| Electromagnetic compatibility at pacemaker-specific levels | IEC 60601-1-2, IEC 60601-2-31, IEC 60601-2-4 | Immunity not tested at cardiac-relevant thresholds |
| Lead conductor fatigue testing | ISO 14708-2 | Insufficient cycle count or non-physiological bending radius |
| Sensing threshold testing | ISO 14708-2, ISO 14708-6 | Sensitivity not validated across arrhythmia types |
| MRI safety per full conditional labeling | ASTM F2052, F2213, F2182, F2119; ISO/TS 10974 | Incomplete RF heating at 1.5T and 3.0T |
| Battery longevity testing | EN 45502-2-1, EN 45502-2-2 | End-of-life indicators not validated |
| Software safety classification (IEC 62304 Class C) | IEC 62304, FDA cybersecurity guidance | Missing V&V for life-sustaining software |

**DHT2B — Interventional Devices (stents, PTA balloons, guidewires):**

| Assessment Criterion | Regulatory Reference | Common Deficiency |
|---------------------|---------------------|-------------------|
| Stent radial strength and recoil | ASTM F2394, FDA stent guidance | Chronic outward force not characterized |
| Stent fatigue testing (10-year equivalent) | FDA stent guidance, ASTM F2477 | Pulsatile fatigue cycles insufficient (<4×10^8) |
| Balloon rated burst pressure testing | FDA PTA catheter guidance | Statistical basis inadequate (n < 30) |
| Catheter trackability, pushability, flexibility | FDA intravascular catheter guidance | Missing worst-case tortuous anatomy model |
| Coating integrity and particulate testing | FDA lubricious coatings guidance (2020) | Particulate characterization incomplete |
| Drug elution kinetics (if drug-coated/eluting) | Combination product guidance, 21 CFR Part 4 | Elution profile not tested under physiological flow |
| Corrosion testing | ASTM F2129, ASTM F746 | Missing accelerated corrosion for novel alloys |
| Biocompatibility — hemocompatibility emphasis | ISO 10993-4 | ISO 10993-4 endpoints incomplete — often only hemolysis tested |

**DHT2C — Structural and Valvular Heart Devices:**

| Assessment Criterion | Regulatory Reference | Common Deficiency |
|---------------------|---------------------|-------------------|
| Hydrodynamic performance (regurgitation, effective orifice area) | ISO 5840-1, ISO 5840-3 (TAVR) | Pulse duplicator test conditions not physiological |
| Structural durability (200M cycles minimum for valves) | ISO 5840-1 | Accelerated testing conditions not validated |
| Particulate/fragment release testing | ISO 5840, FDA structural heart guidance | Wear debris characterization missing |
| Delivery system performance | FDA catheter guidance | Deployment accuracy in tortuous anatomy not tested |

**DHT2D — Vascular and General Surgical:**

| Assessment Criterion | Regulatory Reference | Common Deficiency |
|---------------------|---------------------|-------------------|
| Graft porosity and water permeability | FDA vascular prostheses guidance, ANSI/AAMI VP20 | Missing compliance testing |
| Suture retention strength | ANSI/AAMI VP20 | Sample size inadequate |
| IVC filter retrievability testing | FDA filter guidance (870.4200) | Tilt and embed scenarios not tested |
| Burst strength | ANSI/AAMI VP20 | Not tested at arterial pressures |

**CV-Specific Deficiency Templates:**

> **Hemocompatibility:** The submission does not include complete hemocompatibility testing per ISO 10993-4. For a blood-contacting device with {contact_duration} contact, the following ISO 10993-4 categories are required but not provided: {missing: thrombosis, coagulation, platelets, hematology, complement}. Please submit the complete hemocompatibility test battery.

> **Stent Fatigue:** The fatigue testing data does not demonstrate adequate durability. Per FDA guidance for intravascular stents, a minimum of 4×10^8 cycles representing 10-year equivalent pulsatile loading under worst-case physiological conditions is expected. The submission provides {N} cycles. Please provide additional fatigue data or justification for the abbreviated test duration.

> **Valve Durability:** The accelerated wear test for the heart valve prosthesis does not meet the minimum 200 million cycle requirement per ISO 5840-1. Please provide complete durability data including post-test evaluation of wear, structural integrity, and hemodynamic performance.

> **Drug Elution:** The drug elution kinetics data is incomplete for this combination product. Please provide: (1) elution profile under physiological flow conditions; (2) total drug content per device; (3) drug stability data; (4) bioavailability at target site; (5) systemic drug exposure analysis.

**Score:** CV items addressed / CV items required

### Software/SaMD (Cross-OHT)

**Most Common Deficiencies:**
1. **Documentation level justification** — Inadequate rationale for IEC 62304 software safety class
2. **Cybersecurity** — Missing threat model, SBOM, vulnerability management plan
3. **AI/ML validation** — Insufficient test dataset diversity, missing subgroup analysis
4. **Interoperability** — Integration testing with intended platforms not documented
5. **Software updates** — Post-market update management plan missing

**Typical AI Request:**
> The software documentation is insufficient per IEC 62304. Please provide: (1) Software safety classification with rationale per IEC 62304 Clause 4.3; (2) Software requirements specification; (3) Software architecture; (4) Verification testing results including unit, integration, and system testing; (5) Anomaly list with risk assessment.

### In Vitro Diagnostics (OHT7 — 6 Sub-Panels)

**Trigger:** Review panel in {CH, HE, IM, MI, PA, TX} OR device description contains IVD/diagnostic/assay/CLIA keywords

**Regulatory basis:** 21 CFR 809, 21 CFR 862 (CH/TX), 21 CFR 864 (HE/PA), 21 CFR 866 (IM/MI), CLIA '88, CLSI standards

**Division assignment:**
- DHT7A (Chemistry and Toxicology): CH and TX panels — 21 CFR 862
- DHT7B (Microbiology): MI panel — 21 CFR 866 Subpart C
- DHT7C (Immunology and Hematology): IM and HE panels — 21 CFR 866 / 864
- DHT7D (Molecular Genetics and Pathology): PA panel — 21 CFR 864/866

**Cross-IVD Analytical Validation (all panels):**
- Precision per CLSI EP05 (20-day protocol)?
- Accuracy/method comparison per CLSI EP09?
- Linearity/reportable range per CLSI EP06?
- Analytical sensitivity (LOB/LOD/LOQ) per CLSI EP17?
- Interference per CLSI EP07?
- Reference interval per CLSI EP28?
- Clinical agreement (sensitivity/specificity/PPA/NPA)?
- Specimen types validated?
- Calibration traceability (NIST/WHO/IFCC)?
- CLIA classification (Waived/Moderate/High)?
- If CLIA waived: study per CLSI EP12 (3 untrained operators, ≥120 specimens)?

#### Clinical Chemistry (CH) — DHT7A

**Key regulations:** 21 CFR 862 Subparts B-C
**Product codes:** CDI (glucose), CHN/CHP (blood gas), CZD (chemistry analyzer), CDG (HbA1c)

**CH-Specific Assessment Criteria:**
- Calibration traceability to JCTLM-listed reference materials?
- Commutability of calibrators/controls demonstrated?
- Reference method comparison (isotope dilution MS for creatinine, cyanmethemoglobin for Hgb)?
- Measurement uncertainty per ISO/TS 20914?
- Sample carryover per CLSI EP10?
- High-dose hook effect (immunoturbidimetric methods)?
- Hemolysis/Icterus/Lipemia (HIL) interference panel?
- Method comparison: Deming/Passing-Bablok regression per CLSI EP09 (≥40 specimens)?

**CH Deficiency Template:**
> The submission does not demonstrate calibration traceability to [NIST SRM/WHO/IFCC] reference materials for [analyte]. Per CLSI EP09 and JCTLM recommendations, the traceability chain from the device's calibrators to a recognized reference material/method must be documented.

#### Hematology (HE) — DHT7C

**Key regulations:** 21 CFR 864 Subparts F-H, J
**Product codes:** GGB/GKZ (flow cytometry), GKM/JKA (coagulation), JHR (hematology analyzer)

**HE-Specific Assessment Criteria:**
- CBC accuracy vs. reference methods (CLSI H15 for Hgb, H20 for WBC differential)?
- WBC differential: 5-part/6-part? Manual 400-cell reference (CLSI H20)?
- Flagging performance for abnormal cells (blasts, NRBCs, IGs, variant lymphocytes)?
  - Sensitivity and specificity per FDA automated differential guidance?
- PT/INR: calibration to WHO International Reference Preparation?
  - ISI assignment validated per CLSI H54?
- APTT: heparin sensitivity documented?
- Flow cytometry: immunophenotyping panel validated?
- Blood banking: ABO/Rh typing accuracy (zero false negatives)?

**HE Deficiency Template:**
> The automated hematology analyzer does not include adequate flagging performance data. Per FDA guidance on automated differential cell counters, please provide sensitivity and specificity data for detection of [abnormal cell type] compared to manual microscopy review (400-cell differential per CLSI H20).

#### Immunology (IM) — DHT7C

**Key regulations:** 21 CFR 866 Subparts B, D; 21 CFR 862 Subpart B (immunoassay-classified chemistry)
**Product codes:** JJX (immunological test), various analyte-specific codes

**IM-Specific Assessment Criteria:**
- High-dose hook effect evaluated (sandwich immunoassays)?
  - Test at 10-100x upper measuring interval
  - Critical for hCG, tumor markers, cardiac troponin
- Heterophilic antibody interference (HAMA, RF)?
- Biotin interference (per FDA 2017 Safety Communication)?
- Cross-reactivity with structurally related analytes?
- Standardization to international reference materials?
  - Troponin: NIST SRM 2924 / IFCC
  - TSH: WHO 3rd IS 81/565
  - hCG: WHO 5th IS 07/364
- Seroconversion panel testing (infectious disease serology)?
- CDx: bridging study between trial assay and commercial assay?

**IM Deficiency Template:**
> The immunoassay does not include heterophilic antibody interference testing. Common heterophilic antibodies (HAMA, RF, anti-animal antibodies) can cause clinically significant false results in sandwich immunoassays. Please provide interference data per CLSI EP07, including testing with confirmed heterophilic-positive specimens.

#### Microbiology (MI) — DHT7B

**Key regulations:** 21 CFR 866 Subparts C, D
**Product codes:** QKO (nucleic acid IVD), various panel-specific codes

**MI-Specific Assessment Criteria:**
- AST systems:
  - Essential Agreement (EA) ≥ 90% vs. reference broth microdilution (CLSI M07)?
  - Categorical Agreement (CA) ≥ 90%?
  - Very Major Error (VME) rate < 1.5% (false susceptible)?
  - Major Error (ME) rate < 3% (false resistant)?
  - Breakpoints current per CLSI M100?
  - PCCP for breakpoint updates per FDA AST PCCP guidance (2023)?
- Molecular diagnostics (NAAT):
  - LOD in copies/mL or CFU/mL?
  - Inclusivity (diverse target strains)?
  - Exclusivity/cross-reactivity (near-neighbor organisms)?
  - Specimen types validated (NP swab, sputum, blood, stool)?
  - Clinical performance vs. culture or composite reference?
  - Internal process controls and external controls?
- Blood culture: time-to-detection, organism recovery rates?

**MI Deficiency Templates:**
> The AST system does not include error rate analysis per CLSI M23. Please provide Essential Agreement, Categorical Agreement, VME, ME, and mE rates for each organism-drug combination tested, using CLSI M07 reference broth microdilution as comparator.

> The molecular diagnostic assay does not include adequate inclusivity testing. Please provide analytical reactivity data for a panel of genetically diverse strains of [target organism] representing clinically relevant genotypes.

#### Pathology (PA) — DHT7D

**Key regulations:** 21 CFR 864 Subpart E, 21 CFR 866
**Product codes:** PWD (flow cytometry hematopoietic), various NGS/WSI De Novo codes

**PA-Specific Assessment Criteria:**
- NGS-based IVDs (per FDA NGS guidance 2018):
  - Accuracy vs. orthogonal methods (Sanger, ddPCR, FISH)?
  - Precision (within-run and between-run)?
  - LOD at clinically relevant variant allele frequency (VAF)?
  - Variant types: SNVs, indels, CNVs, fusions, MSI, TMB?
  - Bioinformatics pipeline validated (reference genome, variant caller, quality metrics)?
  - Reference materials (Genome in a Bottle, Horizon Discovery)?
  - Specimen types (FFPE, fresh tissue, liquid biopsy)?
- Whole slide imaging (per FDA WSI guidance):
  - Color fidelity, spatial resolution, stitching accuracy?
  - Pathologist concordance study (digital vs. glass)?
  - Display requirements (monitor specs)?
- IHC companion diagnostics:
  - Scoring algorithm reproducibility?
  - Pre-analytical variable control (fixation, antigen retrieval)?
  - Clinical validation linked to therapeutic outcome?
- FISH: probe specificity/sensitivity, scoring criteria?

**PA Deficiency Templates:**
> The NGS-based IVD does not include adequate bioinformatics pipeline validation. Per FDA NGS guidance (2018), please provide: (1) variant calling algorithm description; (2) analytical validation using well-characterized reference materials; (3) quality metrics and thresholds for reportable results; (4) concordance with orthogonal method.

> The whole slide imaging system does not include adequate clinical validation. Per FDA WSI guidance, please provide a pathologist concordance study demonstrating diagnostic agreement between digital and glass slide review.

#### Toxicology (TX) — DHT7A

**Key regulations:** 21 CFR 862 Subpart D
**Product codes:** Various per drug class (862.3030-3870)

**TX-Specific Assessment Criteria:**
- Cutoff concentrations match SAMHSA/regulatory guidelines?
  - THC: 50 ng/mL screening, 15 ng/mL confirmation
  - Cocaine (BZE): 150 ng/mL screening, 100 ng/mL confirmation
  - Opiates: 2000 ng/mL screening
  - Amphetamines: 500 ng/mL screening
  - PCP: 25 ng/mL screening
- Cross-reactivity with structurally related compounds?
- Near-cutoff precision (75% and 125% of cutoff)?
- Adulterant/specimen validity testing?
- CLIA waiver study per CLSI EP12 (most DOA rapid tests)?
- Visual read agreement (lateral flow — inter-reader variability with untrained operators)?
- TDM: reportable range covers therapeutic AND toxic levels?
  - Cross-reactivity with metabolites (tacrolimus vs. sirolimus)?
- Confirmation method referenced in labeling?

**TX Deficiency Templates:**
> The drugs of abuse screening test does not include adequate cross-reactivity data. Per 21 CFR 862 Subpart D, please provide cross-reactivity testing with structurally related compounds at [10%, 50%, 100%, 200%] of the assay cutoff.

> The CLIA waiver study does not meet CLSI EP12 requirements. Specifically, [untrained operators not used / specimen count insufficient / near-cutoff specimens underrepresented]. Please provide a revised waiver study.

**Cross-IVD Deficiency Templates (all panels):**

> **Analytical performance:** The submission does not include a [precision/accuracy/linearity/LOD] study per CLSI [EP05/EP09/EP06/EP17]. Please provide [study type] data to support the analytical performance claims for [analyte].

> **Clinical performance:** The clinical agreement study does not include sufficient specimens ({N} provided, ≥{M} expected) to support the intended use claim for [analyte/condition].

> **CLIA waiver:** The CLIA waiver study design is incomplete — [missing untrained operators / insufficient specimen count / no comparison to lab method]. Refer to CLSI EP12 for waiver study requirements.

> **Reference traceability:** Calibration traceability to [NIST/WHO/IFCC] reference materials is not documented. Please provide the traceability chain for [analyte].

**Key Standards:** CLSI EP05/EP06/EP07/EP09/EP12/EP17/EP28, CLSI H15/H20/H47/H54 (HE), CLSI M07/M23/M100 (MI), CLSI MM03/MM17 (PA), ISO 15197 (glucose), ISO 17511 (traceability), SAMHSA Guidelines (TX)

**Score:** IVD items addressed / IVD items required

### Surgical Devices (OHT4 — DHT4A/4B/4C)

**Trigger:** Review panel = SU, OR device description contains electrosurgical, stapler, suture, hemostatic, mesh, tissue adhesive, sterilizer, disinfectant, surgical robot, powered instrument, wound dressing

**Regulatory basis:** 21 CFR 878, applicable special controls guidance, FDA reprocessing guidance

**Wound Dressing Assessment (retained):**
- Fluid handling capacity per BS EN 13726-1?
- Moisture vapor transmission rate (MVTR)?
- Antimicrobial efficacy (zone of inhibition, time-kill)?
- Biocompatibility of antimicrobial agents per ISO 10993-5/-10?

**A. Electrosurgical Devices (878.4400):**
- Output power accuracy and stability (measured vs displayed within ±20%)?
- Power curves across impedance range (100-2000 ohm)?
- Lateral thermal spread measurement?
- IEC 60601-2-2 compliance (leakage current, output circuit isolation)?
- Neutral electrode monitoring alarm?
- Software: control algorithms, safety interlocks (IEC 62304)?

**B. Surgical Staplers (878.4301):**
- Staple formation testing (B-value measurement)?
- Firing force and staple line hemostasis?
- Human factors evaluation (mandatory per reclassification): use-related risk analysis, summative testing min 15 participants/group?
- Labeling per FDA stapler labeling guidance (staple leg length, tissue thickness range)?

**C. Surgical Mesh (878.4370):**
- Burst strength (ball burst or uniaxial tensile)?
- Tear resistance and suture pull-out strength?
- Biocompatibility (permanent implant — ISO 10993 extended battery)?
- If absorbable component: degradation characterization?
- Labeling per "Hernia Mesh — Package Labeling Recommendations" (2024)?

**D. Hemostatic Agents (878.4490/4452/4454):**
- Time-to-hemostasis in standardized animal model?
- If absorbable: degradation profile, resorption time?
- If animal-derived: BSE/TSE risk assessment?
- If contains drug (thrombin): combination product assessment?
- Swelling/expansion characterization (compression risk)?

**E. Surgical Sutures (878.4493-4495):**
- Tensile strength (straight pull and knot pull per USP)?
- Needle attachment per USP?
- In vitro degradation profile (if absorbable)?
- If barbed: tissue holding strength, wound closure performance?

**F. Tissue Adhesives (878.4010/4011):**
- Bond strength (lap shear per ASTM D1002 or T-peel)?
- Polymerization/setting time and flexibility?
- If used internally: degradation products, systemic toxicity?

**G. Sterilizers and Disinfectants (878.4160/4820):**
- Sporicidal/tuberculocidal activity per EPA/FDA standards?
- Materials compatibility with intended devices?
- If liquid chemical sterilant: per FDA LCS/HLD guidance (minimum effective concentration, simulated-use)?

**H. Robotic/Computer-Assisted Surgical Systems (878.4961):**
- Positional accuracy and repeatability?
- Latency characterization and force/torque sensing?
- IEC 60601-1, IEC 60601-1-2, IEC 80601-2-77 compliance?
- Software IEC 62304 (likely Class C), cybersecurity if networked?
- Human factors (surgeon console interaction)?

**SU-Specific Deficiency Templates:**

> **Electrosurgical:** The submission does not include adequate performance testing per IEC 60601-2-2. Please provide: (1) output power characterization across intended impedance range; (2) thermal effect testing; (3) neutral electrode monitoring alarm validation; (4) leakage current measurements.

> **Stapler:** The submission does not adequately address the special controls per 21 CFR 878.4301. Please provide: (1) staple formation testing; (2) human factors validation study per FDA HF guidance; (3) labeling compliance per surgical stapler labeling guidance (2021).

> **Mesh:** The surgical mesh submission is incomplete per FDA mesh guidance. Please provide: (1) burst strength and tear resistance; (2) suture pull-out strength; (3) biocompatibility for permanent implant contact per ISO 10993-1:2018; (4) labeling per hernia mesh package labeling guidance (2024).

**Score:** SU items addressed / SU items required

### Anesthesia and Respiratory Devices (OHT1 — DHT1B)

**Trigger:** Review panel = AN, OR regulation number starts with "868"

**Regulatory basis:** 21 CFR 868, ISO 80601-2-13 (anesthesia workstations), ISO 80601-2-12 (critical care ventilators), ISO 80601-2-70 (sleep apnea therapy), ISO 80601-2-55 (respiratory gas monitors), ISO 80601-2-61 (pulse oximeters), IEC 60601-1-8 (alarms)

**Assessment by Subtype:**

**Anesthesia Machines/Workstations (868.5160):**
- ISO 80601-2-13 compliance (essential performance)?
- Agent delivery accuracy (sevoflurane, desflurane, isoflurane)?
- Fresh gas flow accuracy and ventilator mode validation (VCV, PCV, PSV)?
- CO2 absorbent capacity monitoring?
- Alarm system per IEC 60601-1-8?
- Hypoxia prevention (O2/N2O ratio protection)?
- Software per IEC 62304, cybersecurity if networked?

**Ventilators (868.5895, 868.5905, 868.5910):**
- ISO 80601-2-12 (critical care) or -2-80 (ventilatory support)?
- Tidal volume, pressure, flow, PEEP, FiO2 accuracy?
- Alarm testing per IEC 60601-1-8?
- Battery backup duration?
- Home use considerations (if applicable)?

**Pulse Oximeters (868.2375/870.2770):**
- SpO2 accuracy claims in 70-100% range?
- Low perfusion and motion artifact testing?
- Diverse skin pigmentation testing (per FDA guidance)?

**Capnographs (868.2500):**
- ISO 80601-2-55 compliance?
- CO2 measurement accuracy, response time?
- Anesthetic agent interference testing?

**Endotracheal Tubes/LMAs (868.5270, 868.5580):**
- Biocompatibility (mucosal contact)?
- Cuff seal characterization?
- DEHP-free material characterization?
- Connector compliance (ISO 5356-1)?

**Patient Warming Systems (868.5730):**
- Temperature accuracy and uniformity?
- Maximum surface temperature safety limit?
- Thermal injury risk assessment?

**Most Common Deficiencies (expanded):**
1. **ISO 80601 particular standard gaps** — Citing only IEC 60601-1 without particular standard
2. **Alarm performance per IEC 60601-1-8** — Inadequate prioritization, escalation, audible levels
3. **Gas delivery accuracy** — Insufficient agent/FiO2/flow data across full range
4. **Patient circuit connector compatibility** — Non-compliance with ISO 5356-1/ISO 80369-6
5. **Reprocessing for reusable components** — Missing cleaning validation per AAMI TIR30
6. **Essential performance not defined** — IEC 60601-1 Clause 4.3 requirement
7. **Battery backup duration** — Inadequate testing or missing claims
8. **Pulse oximeter skin pigmentation** — Per FDA 2022 recommendations
9. **Cybersecurity for networked equipment** — Missing SBOM and threat model

**AN-Specific Deficiency Templates:**

> **Anesthesia workstation:** Per ISO 80601-2-13, please provide: (1) essential performance verification; (2) agent delivery accuracy; (3) alarm system per IEC 60601-1-8; (4) hypoxia prevention mechanism; (5) software documentation per IEC 62304.

> **Ventilator:** Per ISO 80601-2-12, please provide: (1) tidal volume and pressure accuracy; (2) alarm testing per IEC 60601-1-8; (3) essential performance under single fault; (4) battery backup duration; (5) patient circuit connector compliance per ISO 5356-1.

> **Pulse oximeter:** Per FDA guidance, please provide: (1) SpO2 accuracy across 70-100% range; (2) performance at low perfusion; (3) motion artifact testing; (4) testing across diverse skin pigmentations.

**Key Standards:** ISO 80601-2-13, -2-12, -2-55, -2-61, -2-70, IEC 60601-1-8, ISO 5356-1, ISO 80369-6, AAMI TIR30

**Score:** AN items addressed / AN items required

### Radiological Devices (OHT8 — DHT8A/8B)

**Trigger:** Review panel = RA, OR regulation number starts with "892", OR device is subject to 21 CFR 1020 performance standards

**Regulatory basis:** 21 CFR 892, 21 CFR 1020 (Radiological Health Performance Standards — mandatory for all diagnostic X-ray, CT, fluoroscopy, mammography), applicable IEC 60601-2-xx particular standards

**Division assignment:**
- DHT8A (Imaging Diagnostics): X-ray systems (892.1680), CT scanners (892.1000), MRI (892.1000), ultrasound (892.1850/1860), mammography (892.1710), fluoroscopy (892.1650)
- DHT8B (Radiological Health): LINACs (892.5050), brachytherapy (892.5700/5720), treatment planning (892.5740), therapeutic X-ray (892.5900)

**DHT8A — Imaging Diagnostics Assessment:**

**A. X-Ray Systems (892.1680/892.1720):**
- 21 CFR 1020.30-31 compliance (mandatory performance standard)?
  - Half-value layer measurements?
  - Focal spot size characterization?
  - Beam limitation/collimation testing?
  - Automatic exposure control (AEC) accuracy?
- Image quality (MTF, NPS, DQE per IEC 62220)?
- Dose indices (DAP, entrance skin dose) displayed?
- DICOM conformance (storage, RDSR)?
- Pediatric protocols provided?
- IEC 60601-2-54 compliance?

**B. CT Scanners:**
- 21 CFR 1020.33 compliance (mandatory)?
  - CTDIvol and DLP at reference protocols?
  - Dose display accuracy?
- IEC 60601-2-44 compliance?
- Spatial resolution (MTF at specified contrast)?
- Low-contrast detectability?
- Reconstruction algorithms documented (FBP, iterative, DL)?
- NEMA XR 25/29 dose check standards?
- Pediatric dose protocols?

**C. MRI Systems:**
- IEC 60601-2-33 compliance?
- SAR limits and monitoring?
- dB/dt limits (peripheral nerve stimulation)?
- Gradient performance (amplitude, slew rate)?
- Acoustic noise levels?
- IEC 62464-1 image quality parameters?
- Patient safety (projectile screening, quench system)?

**D. Ultrasound Systems (892.1850/892.1860):**
- Acoustic output per ODS/IEC 62359 (MI and TI display)?
- IEC 60601-2-37 compliance?
- Image quality (spatial/contrast resolution)?
- Transducer characterization (frequency, aperture)?
- DICOM conformance?
- If endocavitary: reprocessing validation?

**E. Mammography (892.1710):**
- MQSA (Mammography Quality Standards Act) compliance?
- IEC 60601-2-45 compliance?
- ACR phantom scoring?
- Dose per image (average glandular dose)?
- Contrast-detail resolution?

**DHT8B — Radiation Therapy Assessment:**

**F. Linear Accelerators/Radiation Therapy (892.5050/892.5900):**
- IEC 60601-2-1 compliance?
- Beam characterization (flatness, symmetry, energy)?
- MLC positioning accuracy and repeatability?
- Safety interlock and fail-safe testing?
- Dose monitoring and verification systems?

**G. Treatment Planning Systems (892.5740):**
- IEC 62083 compliance?
- Dose calculation accuracy across clinical scenarios?
- Beam model commissioning requirements?

**Software and AI/ML for Radiology (cross-divisional):**

| Assessment Criterion | Regulatory Reference | Common Deficiency |
|---------------------|---------------------|-------------------|
| Clinical validation dataset diversity | 21 CFR 892.2050-2080 special controls | Dataset lacks demographic diversity |
| Standalone performance (sensitivity, specificity, AUC) | CADe/CADx guidance (2022) | CIs not provided or sample size inadequate |
| Reader study design | Clinical Performance Assessment guidance | Study not powered for clinical difference |
| PCCP for algorithm updates | AI/ML guidance (2025), PCCP guidance (2024) | Modification protocol not specific enough |
| Image quality dependence testing | CADe guidance | Performance not characterized across acquisition parameters |
| Intended use specificity | 21 CFR 892.2050 special controls | Intended use broader than validation supports |

**Most Common Deficiencies (expanded):**
1. **21 CFR 1020 non-compliance** — Missing mandatory performance standard data for X-ray/CT
2. **Radiation dose measurement** — Dose indices not displayed or incorrectly computed
3. **Image quality metrics** — Incomplete phantom testing or non-standard methodologies
4. **Particular standard gaps** — Citing IEC 60601-1 without device-specific particular standard
5. **Software documentation** — Image reconstruction/processing algorithms not documented per IEC 62304
6. **DICOM conformance** — Incomplete RDSR or missing interoperability testing
7. **AI/ML clinical validation** — Insufficient dataset diversity, missing subgroup analysis
8. **Pediatric considerations** — Pediatric protocols and dose optimization not addressed
9. **Acoustic output (ultrasound)** — MI/TI values not validated or displayed per ODS
10. **EPRC dual submission** — Missing FDA Form 2579 for radiation-emitting products

**RA-Specific Deficiency Templates:**

> **21 CFR 1020 compliance:** This device is subject to the performance standards for diagnostic X-ray systems under 21 CFR 1020. Please provide: (1) half-value layer measurements; (2) focal spot size characterization; (3) beam limitation/collimation testing; (4) automatic exposure control accuracy; (5) dose indices as applicable.

> **Radiation dose display:** The submission does not demonstrate compliance with 21 CFR {1020.31/1020.32/1020.33} regarding radiation dose information display. Please provide: (1) validation of dose index accuracy (CTDIvol, DLP, DAP); (2) description of dose display implementation; (3) DICOM Radiation Dose Structured Report (RDSR) conformance.

> **Image quality:** The image quality data is inadequate to support substantial equivalence. Please provide: (1) MTF measurements per standard methodology; (2) noise power spectrum (NPS) at clinically relevant dose levels; (3) detective quantum efficiency (DQE) per IEC 62220 (digital detector); (4) contrast-detail phantom images at representative exposure conditions.

> **AI/ML clinical validation:** The clinical validation study for this CADe/CADx device is insufficient per 21 CFR {892.2050/892.2060/892.2070/892.2080} special controls. Please provide: (1) standalone performance on multi-site dataset with demographic distribution; (2) reader study with adequate statistical power; (3) performance stratified by acquisition parameters, anatomy, and demographics.

**Key Standards:** IEC 60601-2-44 (CT), IEC 60601-2-54 (X-ray), IEC 60601-2-33 (MRI), IEC 60601-2-37 (ultrasound), IEC 60601-2-45 (mammography), IEC 60601-2-1 (LINAC), IEC 62220 (DQE), IEC 62464-1 (MRI image quality), IEC 62359 (acoustic output), IEC 62083 (treatment planning), NEMA XR 25/29 (CT dose), 21 CFR 1020.30-33

**Score:** RA items addressed / RA items required

### Gastroenterology/Urology Devices (OHT3-GU, DHT3A)

**Trigger:** Review panel = GU, OR regulation number starts with "876"

**Regulatory basis:** 21 CFR 876, applicable special controls, FDA reprocessing guidance

**Most Common Deficiencies:**
1. **Reprocessing validation (endoscopes)** — Missing worst-case soil testing per AAMI TIR30, cleaning validation for complex lumens/channels, simulated-use testing, drying validation. FDA has issued warning letters for duodenoscope reprocessing failures.
2. **Biocompatibility for prolonged-contact devices** — Ureteral stents, Foley catheters with extended dwell times require ISO 10993 for prolonged/permanent mucosal membrane contact. Drug-coated catheters require combination product evaluation per 21 CFR Part 4.
3. **Lithotripter performance** — Missing IEC 60601-2-36 compliance, acoustic output characterization per IEC 61846, fragmentation efficacy with stone phantoms.
4. **Endoscope optical/illumination performance** — Inadequate image quality metrics (resolution, FOV, depth of field, color fidelity), IEC 60601-2-18 compliance.
5. **Dialysis device biocompatibility** — Hemocompatibility per ISO 10993-4 mandatory for blood-contacting dialysis devices (complement activation, coagulation, hematology, platelet function).

**GU-Specific Deficiency Templates:**

> **Reprocessing (endoscopes):** Per FDA reprocessing guidance and ANSI/AAMI ST91:2021, please provide: (1) cleaning validation using worst-case organic soil challenge per AAMI TIR30; (2) high-level disinfection validation; (3) simulated-use testing; (4) drying validation for all channels; (5) functional testing after maximum reprocessing cycles.

> **Lithotripter:** Please provide per IEC 60601-2-36 and IEC 61846: (1) acoustic output characterization (focal zone geometry, peak pressure); (2) stone fragmentation efficacy using validated stone phantoms; (3) treatment zone characterization; (4) tissue damage assessment.

> **Foley catheter:** Please provide per FDA Foley catheter guidance: (1) balloon integrity (inflation/deflation, burst pressure); (2) retention strength; (3) dimensional verification; (4) flow rate; (5) biocompatibility for mucosal membrane prolonged contact; (6) antimicrobial efficacy data (if antimicrobial claim).

**Key Standards:** IEC 60601-2-18, IEC 60601-2-36, IEC 61846, ANSI/AAMI ST91:2021, AAMI TIR30, ASTM F623, ASTM F1828, ISO 10993-4, ISO 20696

**Score:** GU items addressed / GU items required

### Obstetrical and Gynecological Devices (OHT3-OB, DHT3B/DHT3C)

**Trigger:** Review panel = OB, OR regulation number starts with "884"

**Regulatory basis:** 21 CFR 884, applicable special controls, FDA OB/GYN device guidance

**Most Common Deficiencies:**
1. **Fetal safety assessment** — Devices used during pregnancy must demonstrate no adverse fetal effects. Missing acoustic output limits for ultrasound-based fetal monitors (ALARA principle), pregnancy-specific risk assessment. Fetal monitors: alarm sensitivity/specificity data, signal quality across maternal positions.
2. **Morcellator tissue containment** — FDA requires containment system data per 2020 labeling guidance. Missing tissue containment bag integrity testing, visualization during morcellation. Boxed warning required regarding risk of spreading unsuspected malignancy.
3. **IUD/Implant biocompatibility** — Extended biocompatibility for implantable devices contacting reproductive tissue. Copper IUDs: corrosion testing, copper ion release rate. Hormonal IUDs: drug release kinetics per 21 CFR Part 4.
4. **Endometrial ablation completeness** — Missing ablation zone characterization, thermal spread measurement, uterine perforation risk assessment, post-ablation pregnancy risk warnings.
5. **Pelvic mesh complications** — Transvaginal mesh for POP ordered off market (2019); mesh for SUI and abdominal POP repair still requires mechanical testing, porosity characterization, long-term degradation data.

**OB-Specific Deficiency Templates:**

> **Fetal monitor:** Please provide: (1) fetal heart rate detection accuracy compared to direct scalp electrode reference; (2) alarm sensitivity and specificity for clinically significant decelerations; (3) signal quality under realistic conditions (maternal movement, obesity, multiple gestation); (4) compliance with IEC 60601-2-37 for ultrasonic output limits.

> **Power morcellator:** Per FDA labeling guidance (2020), please provide: (1) boxed warning statement regarding cancer spread risk; (2) tissue containment system performance data; (3) visualization adequacy during contained morcellation; (4) instructions for post-procedure tissue retrieval.

> **IUD:** Please provide: (1) dimensional specifications and retention mechanism data; (2) radiopacity verification; (3) biocompatibility for permanent mucosal contact per ISO 10993-1:2018; (4) removal force testing; (5) for copper IUD: corrosion and ion release characterization; (6) for hormonal IUD: drug release kinetics and combination product requirements.

**Key Standards:** IEC 60601-2-37, IEC 60601-1-8, AIUM ODS, ISO 10993-6, ISO 7439

**Score:** OB items addressed / OB items required

### General Hospital Devices (OHT3-HO, DHT3C)

**Trigger:** Review panel = HO, OR regulation number starts with "880"

**Regulatory basis:** 21 CFR 880, FDA Infusion Pump TPLC guidance (2014), applicable special controls

**Most Common Deficiencies:**
1. **Infusion pump software validation** — FDA TPLC guidance requires Enhanced Documentation Level. Common gaps: inadequate hazard analysis (missing over/under-infusion scenarios), missing alarm testing per IEC 60601-1-8, air-in-line detection, occlusion detection, free-flow protection. Multiple Class I recalls in 2024-2025 highlight ongoing software failure modes.
2. **Infusion pump dose accuracy** — Missing flow rate accuracy across full range (min to max), bolus accuracy, low-flow accuracy (<1 mL/hr), trumpet curve per IEC 60601-2-24.
3. **Barrier device testing (gloves, drapes, gowns)** — Missing barrier integrity (ASTM D3578 for gloves, ASTM F1670/F1671 for gowns/drapes), tensile strength, puncture resistance. Powder-free requirement per FDA ban (2017). Protein allergen testing for NRL gloves.
4. **Blood warmer temperature control** — Missing temperature accuracy data, flow rate effects, hemolysis testing at maximum temperature, over-temperature alarm.
5. **Sequential compression pressure profile** — Missing compression pressure vs. time characterization, limb circumference range validation, over-pressure alarm testing.

**HO-Specific Deficiency Templates:**

> **Infusion pump:** Per FDA TPLC guidance, please provide: (1) hazard analysis per ISO 14971 for all infusion hazards (over/under-infusion, air embolism, occlusion, free flow); (2) flow rate accuracy per IEC 60601-2-24; (3) alarm system testing per IEC 60601-1-8; (4) software at Enhanced Documentation Level; (5) cybersecurity per Section 524B (if networked); (6) human factors per IEC 62366-1.

> **Examination gloves:** Per FDA special controls, please provide: (1) physical dimensions per ASTM D3578/D6319; (2) tensile strength and elongation before/after aging; (3) AQL testing; (4) biocompatibility per ISO 10993-5/-10; (5) protein allergen content per ASTM D5712 (if NRL); (6) powder-free verification.

**Key Standards:** IEC 60601-2-24, IEC 60601-1-8, AAMI TIR101:2021, ASTM D3578, ASTM D6319, ASTM D5712, ASTM F1670/F1671, AAMI PB70, ISO 80369-6

**Score:** HO items addressed / HO items required

### Neurological Devices (OHT5 — DHT5A/5B)

**Trigger:** Review panel = NE, OR device description contains neurostimulator, EEG, EMG, TENS, TMS, intracranial, shunt, CSF, seizure, deep brain, vagus nerve, spinal cord stimulator, brain-computer interface, neuromodulation

**Regulatory basis:** 21 CFR 882, applicable special controls, FDA neurological device guidance

**A. Non-Invasive Neurostimulators (882.5891/5892/5893/5802/5803):**
- Stimulation parameters characterized (waveform, frequency, amplitude, pulse width)?
- Maximum output current/voltage and safety cutoffs?
- IEC 60601-2-10 compliance (patient-applied current limits)?
- Current density at electrode-skin interface and temperature rise?
- Clinical evidence for claimed indications (sham-controlled preferred)?
- If home use/OTC: human factors for lay users?

**B. EEG/EMG Diagnostic Systems (882.1870/882.1440):**
- Input impedance, CMRR, frequency response bandwidth?
- Noise floor (μV rms) and channel crosstalk?
- IEC 60601-2-26 (EEG) or IEC 60601-2-40 (EMG) compliance?
- Applied part type (BF or CF) and leakage current?
- If automated spike/seizure detection: algorithm validation?
- If AI/ML-based: per FDA AI/ML guidance?

**C. CSF Shunts and Drainage Systems (882.4060):**
- Pressure-flow characterization across full operating range?
- Opening/closing pressure accuracy?
- If programmable: magnetic field adjustment precision and reproducibility?
- Inadvertent setting change resistance (stray magnetic fields)?
- MRI safety — special concern: setting retention during MRI exposure?
- Catheter tensile strength, kink resistance, radiopacity?
- Biocompatibility (permanent implant, CNS contact)?

**D. Cranial Fixation/Repair (882.4065/882.4545):**
- Fixation strength (pull-out, toggle), fatigue testing?
- Biocompatibility (permanent implant, bone contact)?
- If 3D-printed: additive manufacturing guidance compliance?
- MRI safety for metallic components?

**E. Nerve Repair Conduits (882.5980):**
- Tensile strength, suture retention, flexibility?
- If absorbable: degradation profile matching nerve regeneration timeline?
- Nerve-specific tissue response assessment?
- Gap length supported (typically <30mm)?

**F. Seizure Detection Devices (882.5898/DEN140033):**
- Sensitivity (seizure detection rate) and specificity (false alarm rate)?
- Detection latency and performance across seizure types?
- Clinical validation vs gold standard (video-EEG)?
- Software IEC 62304, alarm management per IEC 60601-1-8?

**NE-Specific Deficiency Templates:**

> **Neurostimulation output:** Per IEC 60601-2-10 and applicable special controls, please provide: (1) complete output waveform characterization; (2) patient-applied current density measurements at electrode sites; (3) thermal testing at electrode-tissue interface; (4) single fault condition output analysis.

> **EEG system:** Per IEC 60601-2-26, please provide: (1) input impedance and CMRR measurements; (2) frequency response verification; (3) channel crosstalk data; (4) patient leakage current measurements.

> **CSF shunt:** Please provide: (1) pressure-flow characterization across full operating range; (2) valve accuracy testing; (3) for programmable valves: magnetic field adjustment precision and MRI setting retention study; (4) biocompatibility for permanent CNS contact per ISO 10993-1.

**Score:** NE items addressed / NE items required

### Dental Devices (OHT1 — DHT1D)

**Trigger:** Review panel = DE, OR regulation number starts with "872"

**Regulatory basis:** 21 CFR 872, ISO 7405:2025 (dental biocompatibility), ISO 14801 (dental implant fatigue), ISO 6872 (dental ceramics), ISO 22674 (dental metallic materials)

**Assessment by Subtype:**

**Dental Implants (872.3275, 872.3630, 872.3640):**
- Fatigue testing per ISO 14801 (≥5×10^6 cycles at worst-case 30° angle)?
- Corrosion testing per ASTM F2129?
- Implant-abutment connection characterization (torsional strength, rotational misfit)?
- Surface characterization (Ra, contact angle, surface chemistry for osseointegration)?
- Biocompatibility per ISO 7405:2025 AND ISO 10993-1:2018?
- MRI safety for metallic implants?
- Clinical data (minimum 2-year follow-up for endosseous)?

**Dental Restorative Materials (872.3280, 872.3400):**
- Flexural strength per ISO 6872 (ceramics) or ISO 4049 (composites)?
- Color stability (delta E), wear resistance, radiopacity?
- Water sorption and solubility per ISO 4049?
- Biocompatibility: cytotoxicity and oral mucosal irritation?

**Dental CAD/CAM / Intraoral Scanners (872.3661):**
- Accuracy and precision per ISO 12836?
- Software per IEC 62304?
- Milling accuracy tolerance?

**Dental Lasers (872.5570):**
- Laser safety per IEC 60825-1 and IEC 60601-2-22?
- Tissue interaction characterization (thermal damage threshold)?

**Orthodontic Devices:**
- Force delivery characterization (aligners: force/moment systems)?
- Nickel release for NiTi wires per EN 1811?
- Biocompatibility per ISO 7405 and ISO 10993-5/-10?

**Most Common Deficiencies:**
1. **ISO 7405 vs ISO 10993 confusion** — Submitters perform only ISO 10993 without dental-specific ISO 7405 tests (pulp capping, dentin barrier, jaw bone implantation)
2. **Fatigue testing inadequacy** — ISO 14801 test angle, cycle count, or loading not at worst-case
3. **Missing SPBP performance criteria** — Not addressing Sept 2024 Safety and Performance Based Pathway thresholds
4. **Insufficient corrosion data** — Missing galvanic corrosion for mixed-metal assemblies
5. **Surface characterization gaps** — Missing Ra, contact angle for osseointegration-dependent implants

**DE-Specific Deficiency Templates:**

> **Dental implant:** Please provide fatigue testing per ISO 14801 (30° offset angle, minimum 5M cycles). Include: (1) S-N curve or run-out data; (2) failure mode analysis; (3) comparison to predicate. Additionally, provide corrosion testing per ASTM F2129 and surface characterization data (Ra, surface chemistry by XPS/EDS).

> **Dental restorative:** Please provide: (1) cytotoxicity per ISO 10993-5; (2) oral mucosal irritation per ISO 10993-23; (3) if dental-specific claim: testing per ISO 7405. Additionally provide flexural strength per ISO 6872 (ceramics) or ISO 4049 (composites) with predicate comparison.

**Key Standards:** ISO 14801, ISO 6872, ISO 22674, ISO 7405:2025, ISO 4049, ISO 9917, ISO 12836, IEC 60825-1, IEC 60601-2-22, EN 1811

**Score:** DE items addressed / DE items required

### ENT Devices (OHT1 — DHT1C)

**Trigger:** Review panel = EN, OR regulation number starts with "874"

**Regulatory basis:** 21 CFR 874, 21 CFR 800.30 (OTC Hearing Aid Controls), 21 CFR 801.420-422 (hearing aid labeling), ANSI S3.22, IEC 60601-2-66, ISO 14708-7

**Assessment by Subtype:**

**Hearing Aids (874.3300, 874.3305, 874.3310, 874.3325):**
- OTC vs Prescription per 21 CFR 800.30?
- Output limits: OTC max 111 dB SPL (non-self-fitting), 117 dB SPL (self-fitting with volume limiting)?
- Electroacoustic per ANSI S3.22 (OSPL90, HFA-OSPL90, HFA-FOG, THD, equivalent input noise)?
- IEC 60601-2-66 electrical safety?
- Biocompatibility of ear-contacting components?
- Labeling per 21 CFR 801.420-422?
- Wireless/cybersecurity (if Bluetooth)?
- Human factors (fitting, insertion, battery replacement)?

**Tympanostomy Tubes (874.3880):**
- Biocompatibility (mucosal contact, ≥30 days — extended battery)?
- Tube migration/extrusion characterization?
- Lumen patency and delivery system safety?

**Intraoral Sleep Apnea Devices (874.5470):**
- Mandibular advancement range (mm) and titratability?
- Biocompatibility per ISO 7405 and ISO 10993?
- Efficacy: AHI reduction, oxygen desaturation index?
- Dental side effects assessment (tooth movement, TMJ)?
- Human factors (home use, lay user)?

**Sinus Dilation Devices:**
- Device integrity and burst pressure?
- Clinical evidence of sinus ostium patency?

**Most Common Deficiencies:**
1. **OTC hearing aid output limit non-compliance** — Exceeding 111/117 dB SPL limits
2. **Missing electroacoustic data** — Incomplete ANSI S3.22 characterization
3. **Hearing aid labeling deficiencies** — Missing 21 CFR 801.420 warnings
4. **Self-fitting algorithm validation** — Clinical study not performed per special controls
5. **Missing wireless/cybersecurity** — Bluetooth hearing aids require Section 524B documentation

**EN-Specific Deficiency Templates:**

> **Hearing aid:** Please provide: (1) electroacoustic data per ANSI S3.22 (OSPL90, HFA-FOG, THD, equivalent input noise); (2) demonstration that output does not exceed {111/117} dB SPL per 21 CFR 800.30; (3) labeling per 21 CFR 801.420; (4) if self-fitting: clinical validation per 874.3325 special controls.

> **Sleep apnea oral appliance:** Per special controls guidance, please provide: (1) biocompatibility per ISO 10993-1 and ISO 7405; (2) mandibular advancement range and titration characterization; (3) clinical evidence of AHI/RDI reduction.

**Key Standards:** ANSI S3.22, ANSI S3.7/IEC 60118-0, IEC 60601-2-66, ISO 14708-7, IEC 60118-13

**Score:** EN items addressed / EN items required

### Ophthalmic Devices (OHT1 — DHT1A)

**Trigger:** Review panel = OP, OR regulation number starts with "886"

**Regulatory basis:** 21 CFR 886, ISO 11979 series (IOLs), ISO 18369 series (contact lenses), IEC 60601-2-22 (ophthalmic lasers), IEC 60825-1 (laser safety), FDA Endotoxin Testing guidance (2015)

**Assessment by Subtype:**

**A. Intraocular Lenses (886.3600):**
- Optical performance per ISO 11979-2 (MTF at 50/100 lp/mm, spectral transmittance, refractive power tolerance)?
- Biocompatibility per ISO 11979-5 (uveal biocompatibility, LEC growth, PCO assessment, calcification)?
- Haptic design per ISO 11979-3 (compression force, loop memory, dynamic fatigue)?
- Endotoxin testing per FDA guidance (0.2 EU/mL in BSS extract)?
- Sterilization validation (material compatibility with steam/EO)?
- Glistening evaluation (hydrophobic acrylic IOLs)?
- Injector/delivery system compatibility and functional testing?
- Shelf life validation (BSS or dry storage)?

**B. Contact Lenses (886.5925/886.5916):**
- Material characterization per ISO 18369-4 (Dk, water content)?
- Dimensional tolerances per ISO 18369-3 (base curve, diameter, thickness)?
- Biocompatibility (cytotoxicity, sensitization, irritation, extractables/leachables per ISO 18369-2)?
- Spectral and UV transmittance per ISO 18369-2?
- Clinical performance (2023 Performance Criteria pathway or clinical study)?
- Labeling per 21 CFR 801 (wearing schedule, replacement frequency, care compatibility)?
- Orthokeratology: corneal topography data with recovery?

**C. Ophthalmic Diagnostic Devices (886.1120/886.1570/886.1100):**
- Software documentation per IEC 62304?
- Measurement accuracy and repeatability (IOP, corneal curvature, retinal layer thickness)?
- Clinical agreement with predicate (same-patient comparison study)?
- AI/ML validation (demographically diverse cohorts, subgroup analysis)?
- Electrical safety per IEC 60601-1 and -1-2?
- Display resolution and luminance specifications?

**D. Ophthalmic Surgical Devices (886.4150/886.4670):**
- Endotoxin testing for all intraocular fluid-contacting instruments?
- Laser performance per IEC 60825-1 and IEC 60601-2-22 (energy accuracy, beam profile, aiming beam, safety interlocks)?
- Phacoemulsification: aspiration flow rate accuracy, ultrasound power, fluidics, thermal safety?
- Vitreous cutters: cutting rate, aspiration flow, port geometry, duty cycle?
- Biocompatibility of patient-contacting components?
- Reprocessing (if reusable handpieces)?

**E. Glaucoma Devices (886.1855/886.5700):**
- MIGS: per FDA MIGS guidance (2015), IOP reduction clinical data?
- Aqueous shunts: flow characterization, biocompatibility (permanent implant)?
- Tonometers: IOP measurement accuracy vs Goldmann reference?

**F. Corneal Devices (886.5850/886.4500):**
- Corneal inlays/rings: optical characterization, biocompatibility?
- Cross-linking: UV irradiance delivery accuracy?

**G. Ophthalmic Lasers (886.4390/886.4690):**
- Energy output accuracy and reproducibility?
- Beam profile characterization?
- Aiming beam visibility?
- Safety interlock testing per IEC 60825-1?
- IEC 60601-2-22 compliance?
- Tissue effect characterization?

**Most Common Deficiencies:**
1. **Endotoxin testing** — Missing or inadequate per FDA guidance; TASS risk requires ≤0.2 EU/mL
2. **IOL optical performance** — Incomplete ISO 11979-2 testing (MTF, spectral transmittance)
3. **IOL biocompatibility** — Using only ISO 10993 without IOL-specific ISO 11979-5
4. **Contact lens characterization** — Incomplete Dk/Dk(t), dimensional tolerances per ISO 18369
5. **AI/ML ophthalmic diagnostics** — Insufficient demographic diversity in validation datasets
6. **Phacoemulsification thermal safety** — Missing corneal temperature rise data
7. **MIGS clinical evidence** — IOP reduction data insufficient or study design inadequate
8. **OTC contact lens labeling** — Missing required warnings per 21 CFR 801

**OP-Specific Deficiency Templates:**

> **IOL optical:** The submission does not include adequate optical performance testing per ISO 11979-2. Please provide: (1) MTF at 50 and 100 lp/mm for 3mm and 4.5mm apertures; (2) spectral transmittance from 300-1100nm; (3) refractive power tolerance per ISO 11979-2 Table 1. For multifocal IOLs, also provide: (4) through-focus MTF; (5) dysphotopsia characterization with quantitative metrics.

> **Endotoxin:** The endotoxin testing data is incomplete per FDA guidance "Endotoxin Testing Recommendations for Single-Use Intraocular Ophthalmic Devices." Please provide: (1) endotoxin level per device using validated LAL method per USP <85>; (2) results compared to recommended limit of 0.2 EU/mL; (3) extraction conditions and sample preparation method.

> **Contact lens:** The submission does not include adequate lens characterization per ISO 18369-2 and -4. Please provide: (1) oxygen permeability (Dk) at 35°C; (2) water content; (3) spectral transmittance from 210-780nm; (4) extractables and leachables analysis; (5) dimensional tolerances per ISO 18369-3.

> **OCT/Diagnostic:** The submission does not include adequate performance testing. Please provide: (1) measurement accuracy and repeatability; (2) clinical agreement study comparing to predicate on ≥100 eyes with diverse pathology. For AI features: (3) sensitivity and specificity with 95% CI; (4) subgroup analysis by age, race/ethnicity, and disease severity.

**Key Standards:** ISO 11979-2/-3/-5, ISO 18369-2/-3/-4, IEC 60601-2-22, IEC 60825-1, ISO 15798, ASTM F2052/F2213/F2182/F2119 (implants)

**Score:** OP items addressed / OP items required

### Physical Medicine Devices (OHT5 — DHT5C)

**Trigger:** Review panel = PM, OR regulation number starts with "890" (also partially applies to NE panel for TENS: 882.5890)

**Regulatory basis:** 21 CFR 890, 21 CFR 882.5890 (TENS), IEC 60601-2-10 (physiotherapy TENS/EMS), ISO 7176 series (wheelchairs), ISO 10328 (prosthetics), ISO 22675 (ankle-foot devices)

**Division assignment:**
- DHT5B (Peripheral & Electrophysical): TENS (882.5890), NMES (890.5850), iontophoresis (890.5525), diathermy (890.5275/5290/5300)
- DHT5C (Physical Medicine): Wheelchairs (890.3860/3890), prosthetics (890.3420), exercise equipment (890.5350-5410), exoskeletons (890.3480)

**Assessment by Subtype:**

**A. Powered Wheelchairs (890.3860/890.3890):**
- Static stability per ISO 7176-1?
- Dynamic stability per ISO 7176-2?
- Strength and fatigue per ISO 7176-8?
- Braking effectiveness per ISO 7176-3?
- Maximum speed per ISO 7176-6?
- Obstacle climbing per ISO 7176-10?
- Power and control systems per ISO 7176-14?
- Battery range per ISO 7176-4?
- Electrical safety per IEC 60601-1?
- EMC per IEC 60601-1-2?

**B. Powered Lower Extremity Exoskeletons (890.3480):**
- Special controls per 21 CFR 890.3480 (detailed requirements codified)?
- Fall protection/arrest mechanism?
- Joint range of motion limits?
- Speed limiting and emergency stop?
- Operator override capability?
- Software IEC 62304 (Class C — safety-critical real-time control)?
- Sensor validation (IMU, pressure sensors, encoders)?
- Battery safety per IEC 62133?
- Human factors with SCI user population?
- Clinical performance data?

**C. TENS/NMES Devices (882.5890/890.5850):**
- Maximum output current, voltage, and charge per pulse?
- Waveform characterization (frequency, pulse width, duty cycle)?
- Output under all impedance conditions (500, 1000 ohm, open circuit)?
- IEC 60601-2-10 compliance (patient-applied current limits)?
- Current density at electrode-skin interface?
- Temperature rise at electrode site?
- Safety cutoffs and single-fault condition analysis?
- Electrode biocompatibility (adhesive/gel, prolonged skin contact)?

**D. Prosthetic Limbs (890.3420):**
- Structural testing per ISO 10328 (static and cyclic, ≥3M cycles)?
- Ankle-foot device testing per ISO 22675?
- General requirements per ISO 22523?
- Weight capacity for intended activity level (K0-K4)?
- If microprocessor-controlled: software per IEC 62304, battery per IEC 62133?
- Biocompatibility of socket interface materials (prolonged skin contact)?
- Waterproof rating (if claimed)?

**E. Diathermy Devices (890.5275/890.5290/890.5300):**
- IEC 60601-2-3 (shortwave) or IEC 60601-2-5 (ultrasonic) compliance?
- Output power accuracy?
- Thermal safety (tissue temperature limits)?

**F. Exercise Equipment (890.5350-890.5410):**
- Structural integrity and fatigue per applicable standards?
- User weight capacity validation?
- Emergency stop mechanism?
- Display accuracy (speed, distance, heart rate)?

**Most Common Deficiencies:**
1. **Wheelchair stability testing** — Missing ISO 7176-1/-2 static/dynamic stability data
2. **TENS output characterization** — Incomplete output parameters across impedance range
3. **Exoskeleton special controls** — Not addressing all 890.3480 codified requirements
4. **Prosthetic structural testing** — Missing ISO 10328 fatigue data at appropriate activity level
5. **Home use considerations** — Inadequate lay user labeling and environmental robustness
6. **Battery safety** — Missing IEC 62133 for lithium battery packs in wheelchairs/exoskeletons
7. **Human factors for disability population** — Using able-bodied proxies instead of representative disabled users
8. **Software real-time control** — Inadequate IEC 62304 documentation for safety-critical motor control

**PM-Specific Deficiency Templates:**

> **Wheelchair stability:** The submission does not include adequate stability testing. Please provide static stability testing per ISO 7176-1 and dynamic stability testing per ISO 7176-2 for the powered wheelchair. Include all relevant slope angles and loading conditions. Also provide strength and fatigue testing per ISO 7176-8.

> **TENS output:** The submission does not adequately characterize the device output parameters. Please provide: (1) maximum output current, voltage, and charge per pulse under all impedance conditions; (2) verification that outputs do not exceed safety limits per IEC 60601-2-10; (3) essential performance criteria maintained under single-fault conditions.

> **Exoskeleton:** Per the special controls for powered lower extremity exoskeletons (21 CFR 890.3480), the submission must include: (1) biocompatibility of patient-contacting materials; (2) EMC/EMI and electrical safety testing; (3) mechanical safety testing; (4) battery performance and safety; (5) software verification and validation; (6) human factors/usability study with the intended user population; (7) clinical performance data.

> **Prosthetic:** The submission does not include structural testing of the lower-limb prosthesis per ISO 10328. Please provide static and cyclic strength test results demonstrating the device meets the structural requirements for the intended activity level.

**Key Standards:** ISO 7176-1/-2/-3/-4/-6/-8/-10/-14, ISO 10328, ISO 22675, ISO 22523, IEC 60601-2-10, IEC 60601-2-3, IEC 60601-2-5, IEC 62133, RESNA WC/Vol2

**Score:** PM items addressed / PM items required

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
