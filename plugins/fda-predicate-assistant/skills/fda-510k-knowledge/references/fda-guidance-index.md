# FDA CDRH Guidance Documents Index

Curated index of key FDA guidance documents for medical device premarket submissions. Organized by category with document URLs, status, and applicability. Used by `/fda:guidance` for structured lookup before web searching.

**Last verified**: 2026-02-08

## How to Use This Index

1. Check **Cross-Cutting Guidance** (applies to most/all devices)
2. Check **Device-Category Guidance** by matching regulation number or product code family
3. Check **Pathway-Specific Guidance** for submission type requirements
4. Use `/fda:guidance` `--depth deep` to web-search for additional device-specific guidance not in this index

---

## 1. Cross-Cutting Guidance (All or Most Devices)

### 1.1 Biocompatibility

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Use of International Standard ISO 10993-1: Biological Evaluation of Medical Devices — Part 1: Evaluation and Testing Within a Risk Management Process | Final | 2023 | All patient-contacting devices |
| Biocompatibility Testing of Medical Devices — Toxicology Profiles | Final | 2024 | All patient-contacting devices |

**Key standards**: ISO 10993-1 (framework), -5 (cytotoxicity), -10 (irritation/sensitization), -11 (systemic toxicity), -6 (implantation), -4 (hemocompatibility)

### 1.2 Sterilization

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Submission and Review of Sterility Information in Premarket Notification (510(k)) Submissions for Devices Labeled as Sterile | Final | 2024 | All sterile devices |
| Ethylene Oxide Sterilization for Medical Devices | Final | 2023 | EO-sterilized devices |
| Radiation Sterilization of Medical Devices | Final | 2022 | Radiation-sterilized devices |
| Reprocessing Medical Devices in Health Care Settings: Validation Methods and Labeling | Final | 2015 | Reusable devices |

**Key standards**: ISO 11135 (EO), ISO 11137 (radiation), ISO 17665 (steam), AAMI TIR12, ISO 11607 (packaging)

### 1.3 Shelf Life & Packaging

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Shelf Life of Medical Devices | Final | 1991 | All packaged devices |

**Key standards**: ASTM F1980 (accelerated aging), ASTM F2097 (packaging evaluation), ISO 11607 (packaging for terminally sterilized), ASTM D4169 (shipping)

### 1.4 Labeling

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Medical Device Labeling — 510(k) Guidance | Final | 2023 | All 510(k) devices |
| Guidelines for Reliability Testing of Reusable Medical Devices | Final | 1995 | Reusable devices |

**Regulation**: 21 CFR 801 (general labeling), 21 CFR 809 (IVD labeling)

### 1.5 Risk Management

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Factors to Consider When Making Benefit-Risk Determinations in Medical Device Premarket Approval and De Novo Classifications | Final | 2019 | PMA, De Novo |
| Applying Human Factors and Usability Engineering to Medical Devices | Final | 2016 | Devices with use-related risks |

**Key standards**: ISO 14971, IEC 62366-1, ANSI/AAMI HE75

### 1.6 Clinical Evidence

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Use of Real-World Evidence to Support Regulatory Decision-Making for Medical Devices | Final | 2024 | Devices citing RWE |
| Acceptance of Clinical Data to Support Medical Device Applications and Submissions | Final | 2018 | Devices with clinical data from outside US |
| Design Considerations for Pivotal Clinical Investigations for Medical Devices | Final | 2013 | IDE studies |
| Statistical Guidance on Reporting Results from Studies Evaluating Diagnostic Tests | Final | 2007 | IVD/diagnostic devices |

**Key standards**: ISO 14155 (clinical investigation), MEDDEV 2.7/1 (clinical evaluation)

---

## 2. Software & Digital Health Guidance

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Content of Premarket Submissions for Device Software Functions | Final | 2023 | Software-containing devices |
| Artificial Intelligence-Enabled Device Software Functions: Lifecycle Management and Marketing Submission Recommendations | Final | 2025 | AI/ML devices |
| Marketing Submission Recommendations for a Predetermined Change Control Plan for AI-Enabled Device Software Functions | Final | 2024 | AI/ML devices with PCCP |
| Cybersecurity in Medical Devices: Quality System Considerations and Content of Premarket Submissions | Final | 2025 | All connected/networked devices |
| Policy for Device Software Functions and Mobile Medical Applications | Final | 2022 | Mobile apps, SaMD |
| Clinical Decision Support Software | Final | 2022 | CDS functions |
| Software as a Medical Device (SaMD): Clinical Evaluation | Final | 2017 | SaMD |
| Off-The-Shelf Software Use in Medical Devices | Final | 2019 | OTS software components |
| General Principles of Software Validation | Final | 2002 | All software-containing devices |
| Computer Software Assurance for Production and Quality System Software | Final | 2022 | QMS software |

**Key standards**: IEC 62304, IEC 82304-1, AAMI TIR57, AAMI SW96, NIST SP 800-53

### Software Trigger Keywords
Match in device description: `software`, `algorithm`, `app`, `firmware`, `SaMD`, `digital`, `AI`, `machine learning`, `deep learning`, `neural network`, `connected`, `cloud`, `mobile`

---

## 3. Electromagnetic & Wireless Guidance

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Radio Frequency Wireless Technology in Medical Devices | Final | 2013 | Wireless devices |
| Electromagnetic Compatibility (EMC) of Medical Devices | Final | 2016 | Electrically powered devices |
| Information to Support a Claim of Electromagnetic Compatibility (EMC) of Electrically Powered Medical Devices | Final | 2016 | IEC 60601-1-2 compliance |

**Key standards**: IEC 60601-1 (safety), IEC 60601-1-2 (EMC), ANSI C63.27 (wireless coexistence)

### EMC/Wireless Trigger Keywords
Match: `wireless`, `bluetooth`, `wifi`, `connected`, `IoT`, `RF`, `electrical`, `powered`, `battery`, `rechargeable`

---

## 4. Pathway-Specific Guidance

### 4.1 510(k) Submissions

| Document | Status | Year | Notes |
|----------|--------|------|-------|
| The 510(k) Program: Evaluating Substantial Equivalence in Premarket Notifications | Final | 2014 | Core SE guidance |
| Refuse to Accept Policy for 510(k)s | Final | 2022 | RTA checklist |
| How to Prepare a Traditional 510(k) | Final | 2023 | eSTAR format required Oct 2023 |
| The Special 510(k) Program | Final | 2019 | Design control-based |
| The Abbreviated 510(k) Program | Final | 2019 | Standards-based |
| 510(k) Third Party Review Program | Final | 2024 | Accredited persons |
| Transfer of a Premarket Notification (510(k)) Clearance — Questions and Answers | Draft | 2025 | Clearance transfers |
| Electronic Submission Template for Medical Device 510(k) Submissions (eSTAR) | Final | 2023 | Mandatory since Oct 1, 2023 |

### 4.2 De Novo Submissions

| Document | Status | Year | Notes |
|----------|--------|------|-------|
| De Novo Classification Process (Evaluation of Automatic Class III Designation) | Final | 2021 | Core De Novo guidance |
| Acceptance Review for De Novo Classification Requests | Final | 2023 | Acceptance checklist |

### 4.3 PMA Submissions

| Document | Status | Year | Notes |
|----------|--------|------|-------|
| Premarket Approval Application Modular Review | Final | 2025 | Modular PMA |
| PMA Review Process | Final | 2019 | PMA expectations |

### 4.4 Pre-Submissions

| Document | Status | Year | Notes |
|----------|--------|------|-------|
| Requests for Feedback and Meetings for Medical Device Submissions: The Q-Submission Program | Final | 2025 | Pre-Sub, Q-Sub |

---

## 5. Device-Category Specific Guidance

### 5.1 Cardiovascular Devices (21 CFR 870)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 870.4200 | DXY | Guidance for Cardiovascular Intravascular Filter 510(k) Submissions | Final | 2020 |
| 870.4220 | DTB | Guidance for the Submission of Research and Marketing Applications for Interventional Cardiology Devices | Final | 2013 |
| 870.1025 | DSI, DQO | Non-Invasive Blood Pressure (NIBP) Monitoring Devices | Final | 2022 |
| 870.2300 | DSG | Cardiac Monitor Guidance (Including Cardiotocographic Monitors) | Final | 2003 |
| 870.2770 | QDV | Oximeters, Pulse — Class II Special Controls | Final | 2013 |

**Key standards**: ISO 10993-4 (hemocompatibility), ISO 5840, ISO 25539, ASTM F2394

### 5.2 Orthopedic Devices (21 CFR 888)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 888.3080 | MAX | Intervertebral Body Fusion Device | Final | 2007 |
| 888.3060 | HVE, HWE | Pedicle Screw Spinal Systems — Class II Special Controls | Final | 2003 |
| 888.3027 | OTM | Restorative Cement for Vertebroplasty/Vertebral Augmentation | Final | 2024 |
| 888.3 | Various | Class II Special Controls for Orthopedic Bone Plates/Screws | Final | 2019 |

**Key standards**: ASTM F2077, F1717, F136, F1295, F2129, F1160, ISO 12189

### 5.3 Wound Care Devices (21 CFR 878)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 878.4018 | KGN | Wound Dressing with Drugs | — | — |
| 878.4022 | FRO | Hydrophilic Wound Dressing | — | — |
| 878.4400 | MGP, FQP | Surgical Dressing | — | — |

*Note: No device-specific guidance for most wound dressings — rely on cross-cutting biocompatibility, sterilization, and shelf life guidance plus predicate precedent.*

**Key standards**: EN 13726, ASTM D1777, ASTM D4032, AATCC 100, ISO 10993-5/-10

### 5.4 In Vitro Diagnostic Devices (21 CFR 862, 864, 866, 868)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 866.3373 | QKO | Nucleic Acid Based In Vitro Diagnostic Devices — Class II Special Controls | Final | 2017 |
| 862.1130 | CDI | Clinical Chemistry — Blood Glucose Test Systems | Final | 2020 |
| 864.7010 | GGB, GKZ | Flow Cytometry — Class II Special Controls | Final | 2019 |
| 862.3850 | JJX | Immunological Test Systems | Final | 2008 |
| Multiple | Multiple | In Vitro Diagnostic (IVD) Device Studies — Frequently Asked Questions | Final | 2010 |
| Multiple | Multiple | Statistical Guidance on Reporting Results from Studies Evaluating Diagnostic Tests | Final | 2007 |

**Key standards**: CLSI EP05, EP06, EP07, EP12, EP15, EP17, C28, ISO 15197 (glucose), ISO 18113

### 5.5 Dental Devices (21 CFR 872)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 872.3275 | EIG | Root-Form Endosseous Dental Implants and Abutments | Final | 2004 |
| 872.6730 | EKT | Dentifrice — Special Controls | Final | 2009 |
| 872.3400 | EBP | Dental Ceramic Restorative Systems | Final | 2021 |

**Key standards**: ISO 14801, ISO 6872, ISO 22674, ISO 7405

### 5.6 Ophthalmic Devices (21 CFR 886)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 886.5916 | QMO | Retinal Prosthesis | Final | 2017 |
| 886.1570 | MYJ, QEI | Computerized Corneal Topography | Final | 2005 |
| 886.5820 | MRC | Contact Lens Solutions and Lubricants | Final | 1997 |

### 5.7 Continuous Glucose Monitors (CGM) / Blood Glucose

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 862.1355 | QBJ | Integrated Continuous Glucose Monitoring System (iCGM) — Special Controls | Final | 2019 |
| 862.1130 | CDI | Self-Monitoring Blood Glucose Test Systems for Over-the-Counter Use | Final | 2020 |
| 862.1130 | NBW | Blood Glucose Monitoring Test Systems for Prescription Use | Final | 2020 |

**Key standards**: ISO 15197, CLSI POCT05, IEC 62304, IEC 60601-1/-1-2, ASTM F2761

### 5.8 Respiratory Devices (21 CFR 868)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 868.5895 | BTK, CBK | Continuous Positive Airway Pressure (CPAP) — Class II Special Controls | Final | 2022 |
| 868.5910 | BZD | Powered Emergency Ventilator | Final | 2020 |
| 868.2375 | QDV | Pulse Oximeters — Premarket Notification (510(k)) | Final | 2013 |

### 5.9 General Hospital / Surgical Devices (21 CFR 878, 880, 882)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 878.4370 | GEI | Surgical Mesh for Hernia Repair — Premarket Notification | Final | 2021 |
| 882.5801 | QAS | Implanted Brain Stimulator — Class III Special Controls | Final | 2019 |
| 880.5075 | FQM | Medical Examination Gloves — Class II Special Controls | Final | 2019 |

### 5.10 Imaging Devices (21 CFR 892)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 892.2050 | IYO, QDQ | Computer-Aided Detection/Diagnosis (CADe/CADx) | Final | 2022 |
| 892.1000 | IZL | Magnetic Resonance Imaging (MRI) Devices — Class II | Final | 2021 |

---

## 6. Implantable Device Additional Guidance

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Assessment of the Effects of a Magnetic Resonance Diagnostic Device on Medical Devices Containing Magnetically Susceptible Material | Final | 2021 | All implantable devices |
| Select Updates for Non-Clinical Engineering Tests | Final | 2021 | Implants requiring bench testing |

**Key standards**: ASTM F2052 (magnetically induced displacement), F2213 (torque), F2182 (RF heating), F2119 (image artifact)

### Implant Trigger Keywords
Match: `implant`, `implantable`, `permanent`, `indwelling`, `prosthesis`, `prosthetic`

---

## 7. Combination Products

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Classification of Products as Drugs and Devices & Additional Product Classification Issues | Final | 2017 | Drug-device, biologic-device combinations |
| Current Good Manufacturing Practice Requirements for Combination Products | Final | 2017 | Manufacturing requirements |
| Principles of Premarket Pathways for Combination Products | Final | 2022 | Regulatory pathway selection |

**Regulation**: 21 CFR Part 3, 21 CFR Part 4

### Combination Product Trigger Keywords
Match: `drug`, `biologic`, `combination`, `drug-device`, `drug-eluting`, `antimicrobial`, `coated`

---

## 8. Recently Finalized / Upcoming Guidance (2024–2026)

### Finalized in FY 2024–2025

| Document | Finalized | Topic |
|----------|-----------|-------|
| Sterility Information in 510(k) Submissions | Jan 2024 | Sterilization |
| GUDID Guidance Update | Dec 2024 | UDI |
| PCCP for AI-Enabled Software Functions | Dec 2024 | AI/ML |
| AI-Enabled Device Software Functions | Jan 2025 | AI/ML |
| Q-Submission Program | May 2025 | Pre-Sub meetings |
| Cybersecurity in Medical Devices | Jun 2025 | Cybersecurity |
| 510(k) Third Party Review Program | Nov 2024 | Third-party review |
| PMA Modular Review | Jan 2025 | PMA |

### FY 2026 A-List (Priority)

| Document | Expected Action | Topic |
|----------|----------------|-------|
| Real-World Evidence (Final) | Finalize | Clinical evidence |
| PCCP Lifecycle Management (Final) | Finalize | AI/ML |
| Diagnostics for Emerging Pathogens (Final) | Finalize | IVD |
| Voluntary Patient Preference Information (Final) | Finalize | Clinical evidence |
| Diversity Action Plans for Device Clinical Studies (Draft) | Publish | Clinical studies |
| Bench Performance Testing for Absorbable Cardiovascular Implants (Draft) | Publish | Cardiovascular |
| Recommendations for Device Labeling (Draft) | Publish | Labeling |
| Breakthrough Devices Program (Draft) | Publish | Regulatory pathway |

---

## 9. Regulation Number → Guidance Quick Lookup

For the most common device regulations encountered in 510(k) work:

| Regulation | Device Type | Has Specific Guidance? | Notes |
|-----------|------------|----------------------|-------|
| 878.4018 | Wound dressing, drug | No | Use cross-cutting (biocompatibility, sterilization) |
| 870.4200 | Intravascular filter | Yes | Cardiovascular filter guidance |
| 870.2770 | Pulse oximeter | Yes | Pulse ox special controls |
| 862.1355 | iCGM | Yes | iCGM special controls |
| 888.3080 | Spinal fusion | Yes | IBF guidance |
| 878.4370 | Surgical mesh | Yes | Hernia repair guidance |
| 892.2050 | CADe/CADx | Yes | AI/ML imaging guidance |
| 866.3373 | NAATx | Yes | Nucleic acid IVD guidance |
| 868.5895 | CPAP | Yes | CPAP special controls |
| 880.5075 | Exam gloves | Yes | Gloves special controls |
| 872.3275 | Dental implants | Yes | Root-form implant guidance |

---

## Integration Notes

- `/fda:guidance` should check this index FIRST, then web-search for additional/newer guidance
- Product codes listed are representative — check the classification API for the complete mapping
- URLs may change — use WebSearch as verification/fallback
- Cross-cutting guidance triggers should be evaluated from device description keywords
- The FY 2026 agenda items are *planned* — check FDA.gov for actual publication status
