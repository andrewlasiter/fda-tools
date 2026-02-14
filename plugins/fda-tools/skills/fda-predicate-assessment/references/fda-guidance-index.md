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
| 870.3460 | MAF, NIQ | Non-Clinical Engineering Tests and Recommended Labeling for Intravascular Stents and Associated Delivery Systems | Final | 2010 (updated 2022) |
| 870.3460 | MAF, NIQ | Select Updates for Non-Clinical Engineering Tests for Intravascular Stents and Delivery Systems | Final | 2022 |
| 870.4220 | DYB | Coronary, Peripheral, and Neurovascular Guidewires — Performance Tests and Recommended Labeling | Final | 2020 |
| 870.4220 | DTB, DYB | Intravascular Catheters, Wires, and Delivery Systems — Lubricious Coatings and Labeling | Final | 2020 |
| 870.1220 | DTB, DWY | Premarket Notification [510(k)] Submissions for Short-Term and Long-Term Intravascular Catheters | Final | 1995 |
| 870.3450 | DYB | Vascular Prostheses 510(k) Submissions | Final | 2000 |
| 870.4360 | BSC | Guidance for Cardiopulmonary Bypass Oxygenators 510(k) Submissions | Final | 2000 |
| 870.4220 | DTB | Peripheral Percutaneous Transluminal Angioplasty (PTA) Catheter — 510(k) Submissions | Final | 2023 |
| 870.5700 | BSY | Extracorporeal Circuit and Accessories for Long-Term Respiratory/Cardiopulmonary Failure (ECMO) — Reclassification Special Controls | Final | 2016 |
| 870.3925 | Various | Heart Valve Prostheses (reference ISO 5840) | Final | — |
| 870.various | NIQ variants | Bench Performance Testing for Absorbable Cardiovascular Implants | Draft | FY2026 (upcoming) |

**Key standards**: ISO 10993-4 (hemocompatibility), ISO 5840, ISO 25539, ASTM F2394, ISO 25539-2 (endovascular devices), ASTM F2477 (stent fatigue), IEC 60601-2-4 (defibrillator), ISO 14708-2 (cardiac pacemaker)

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

### 5.4 In Vitro Diagnostic Devices (21 CFR 862, 864, 866)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 866.3373 | QKO | Nucleic Acid Based In Vitro Diagnostic Devices — Class II Special Controls | Final | 2017 |
| 862.1130 | CDI | Clinical Chemistry — Blood Glucose Test Systems | Final | 2020 |
| 864.7010 | GGB, GKZ | Flow Cytometry — Class II Special Controls | Final | 2019 |
| 862.3850 | JJX | Immunological Test Systems | Final | 2008 |
| Multiple | Multiple | In Vitro Diagnostic (IVD) Device Studies — Frequently Asked Questions | Final | 2010 |
| Multiple | Multiple | Statistical Guidance on Reporting Results from Studies Evaluating Diagnostic Tests | Final | 2007 |
| Multiple | Multiple | Recommendations for Dual 510(k) and CLIA Waiver by Application Studies | Final | 2020 |
| Multiple | Multiple | Replacement Reagent and Instrument Family Policy for In Vitro Diagnostic Devices | Final | 2022 |

**Key standards**: CLSI EP05, EP06, EP07, EP12, EP15, EP17, C28, ISO 15197 (glucose), ISO 18113

### 5.5 Dental Devices (21 CFR 872)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 872.3275 | EIG | Root-Form Endosseous Dental Implants and Abutments | Final | 2004 |
| 872.3640, 872.3630 | EIG, DZE | Endosseous Dental Implants and Endosseous Dental Implant Abutments — Performance Criteria for Safety and Performance Based Pathway | Final | 2024 |
| 872.3275 | Various | Dental Cements — Performance Criteria for Safety and Performance Based Pathway | Draft | 2024 |
| 872.6660, 872.3920 | Various | Dental Ceramics — Performance Criteria for Safety and Performance Based Pathway | Draft | 2024 |
| 872.3060 | EJD | Dental Impression Materials — Performance Criteria for Safety and Performance Based Pathway | Draft | 2024 |
| 872.3280 | Various | Dental Composite Resin Devices — Premarket Notification (510(k)) Submissions | Draft | 2024 |
| 872.3050 | EIG | Dental Composites — Special Controls | Final | -- |
| 872.3661 | QJK, QKE | Optical Impression Systems for CAD/CAM of Dental Restorations — Class II Special Controls (includes intraoral scanners) | Final | 2005 |
| 872.4200 | EKV, EKP | Dental Handpieces — Premarket Notification (510(k)) Submissions | Final | updated |
| 872.3930 | LYC, KGM, MMJ | Animal Studies for Dental Bone Grafting Material Devices — 510(k) Submissions | Final | 2024 |
| 872.5570 | ENR | Dental Lasers — Conformance with IEC 60825-1 and IEC 60601-2-22 (Laser Products guidance applied to dental lasers) | Final | 2019 |
| 872.5470 | EJE | Orthodontic Brackets and Wires — Class II Special Controls | Final | -- |
| 872.6730 | EKT | Dentifrice — Special Controls | Final | 2009 |
| 872.3400 | EBP | Dental Ceramic Restorative Systems | Final | 2021 |
| 872.6070 | Various | Dental Curing Lights — Premarket Notification (510(k)) Submissions | Final | 2024 |
| Various | Various | Denture Base Resins — Performance Criteria for Safety and Performance Based Pathway | Final | 2022 |

**Key standards**: ISO 14801 (dental implant dynamic loading), ISO 6872 (dental ceramics), ISO 22674 (metallic materials for dental restorations), ISO 7405 (dental implant preclinical biocompatibility), ISO 4049 (polymer-based restorative materials), ANSI/ADA Standard No. 41 (recommended standard practices for orthodontic wires), ISO 28319 (dental laser systems), ISO 9917 (dental cements)

### 5.6 Ophthalmic Devices (21 CFR 886)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 886.5895 | HQF | Retinal Prosthesis System (Class III — PMA) | Final | 2017 |
| 886.5916 | HJN | Rigid Gas Permeable Contact Lens | Final | 2006 |
| 886.5916 | MQI | Premarket Submissions of Orthokeratology Rigid Gas Permeable Contact Lenses | Final | 2004 |
| 886.1570 | MYJ, QEI | Computerized Corneal Topography | Final | 2005 |
| 886.5820 | MRC | Contact Lens Solutions and Lubricants | Final | 1997 |
| 886.3600 | HQC, HQD | Intraocular Lens (IOL) — Class III PMA; endotoxin testing, ISO 11979 series for optical/mechanical/biocompatibility performance | PMA | — |
| 886.5925 | MRC, QCT | Class II Daily Wear Contact Lenses — Premarket Notification [510(k)] Guidance Document | Final | 1994 |
| 886.5925 | LPL | Soft (Hydrophilic) Daily Wear Contact Lenses — Performance Criteria for Safety and Performance Based Pathway | Final | 2023 |
| 886.3920, 886.5700 | QFX, OXP, PIV | Premarket Studies of Implantable Minimally Invasive Glaucoma Surgical (MIGS) Devices | Final | 2015 |
| 886.3600, 886.4150 | Various | Endotoxin Testing Recommendations for Single-Use Intraocular Ophthalmic Devices | Final | 2015 |
| 886.3300 | QCR | Ophthalmic Viscosurgical Devices (OVD) — intraocular use during anterior segment surgery; ISO 15798 | Final | — |
| 886.4670 | HNO | Phacoemulsification System — emulsification and aspiration of cataracts; endotoxin and thermal safety testing required | Final | — |
| 886.3400 | HOL, HQH, HQI | Guidance on 510(k) Submissions for Keratoprostheses | Final | 2005 |
| 886.1570, 886.1120 | OBO, OAP, NKF | Ophthalmic Diagnostic Devices — OCT, fundus camera, automated perimeter; software documentation and measurement agreement studies | Final | — |
| 886.4390 | MVJ, LZA | Excimer Laser for Corneal Surgery (LASIK/PRK) — Class III PMA; ANSI Z80.11, IEC 60825-1 laser safety | PMA | — |
| 886.4150 | HQC | Third Party Review Guidance for Vitreous Aspiration and Cutting Device (Ab Interno Vitrectomy) Premarket Notification [510(k)] | Final | 2002 |
| 886.3300, 886.4150 | Various | Retinal Detachment Surgery Devices — scleral buckle, vitrectomy, endoillumination, perfluorocarbon liquids, silicone oil tamponade | Final | — |
| 886.1100 | QMZ | IOL Power Formula/Calculator (SaMD) — De Novo classification for retinal diagnostic software device; AI/ML considerations | De Novo | 2022 |
| 886.5928 | MRC, MQP | Hydrogen Peroxide-Based Contact Lens Care Products: Consumer Labeling Recommendations | Final | 2023 |
| 886.5928 | MRC | Contact Lens Care Products Labeling | Final | 2010 |

**Key standards**: ISO 11979 series (IOLs — 10 parts: -1 vocabulary, -2 optical properties, -3 mechanical properties, -4 labelling, -5 biocompatibility, -6 shelf-life, -7 clinical investigations aphakic, -8 fundamental requirements, -9 multifocal IOLs, -10 clinical investigations phakic), ISO 18369 series (contact lenses — 4 parts: -1 vocabulary/classification, -2 tolerances, -3 measuring methods, -4 physicochemical properties including Dk), ANSI Z80 series (ophthalmic optics — Z80.1 prescription lenses, Z80.9 contact lenses, Z80.11 excimer laser, Z80.20 corneal topography, Z80.28 multifocal IOLs, Z80.30 toric IOLs), ISO 15004 (ophthalmic instruments — -1 fundamental requirements, -2 light hazard protection), ISO 11810 (ophthalmic laser safety — laser/pulsed-light tissue interaction), ISO 15798 (OVDs), ISO 16671 (irrigating solutions), ISO 14729 (contact lens care antimicrobial efficacy), ISO 14730 (preservative uptake/release), USP <85> (bacterial endotoxins test for intraocular devices)

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

### 5.9 General Hospital Devices (21 CFR 880)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 880.5075 | FQM | Medical Examination Gloves — Class II Special Controls | Final | 2019 |
| 880.5725 | FRN | Infusion Pumps Total Product Life Cycle — Guidance for Industry and FDA Staff | Final | 2014 |

**Key standards for infusion pumps**: IEC 60601-2-24, IEC 62304 (software), IEC 60601-1-8 (alarms), AAMI TIR101

### 5.10 Imaging Devices (21 CFR 892)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 892.2050 | IYO, QDQ | Computer-Aided Detection/Diagnosis (CADe/CADx) — includes Clinical Performance Assessment guidance for CADe applied to radiology images (2022); standalone and reader study design; dataset diversity requirements | Final | 2022 |
| 892.1000 | IZL | Magnetic Resonance Imaging (MRI) Devices — Class II | Final | 2021 |
| 892.1700 | IZL | Diagnostic X-Ray Systems (General) — Medical X-Ray Imaging Devices Conformance with IEC Standards; covers radiographic, fluoroscopic, and CT components; 21 CFR 1020 compliance required | Final | 2020 |
| 892.1750 | JAK | Computed Tomography (CT) Systems — Class II; IEC 60601-2-44 particular standard; CTDIvol and DLP dose display required per 21 CFR 1020.33; dose check (NEMA XR 25); SSDE (NEMA XR 29) | Final | 2020 |
| 892.1720 | MYN | Digital Mammography Systems — MQSA (Mammography Quality Standards Act) facility and equipment requirements; 21 CFR 900 Subpart B; FFDM and DBT (tomosynthesis) image quality per ACR phantom; DICOM Mammography module | Final | Various |
| 892.1560 | IYO | Diagnostic Ultrasound Imaging Systems and Transducers — Marketing Clearance guidance; Track 1 (low output) / Track 3 (ODS) acoustic output pathways; MI and TI display per IEC 62359 and AIUM ODS; transducer biocompatibility for patient-contacting surfaces | Final | 2019 |
| 892.2010 | Various | Medical Image Display Devices — Display Devices for Diagnostic Radiology guidance; luminance, contrast ratio, resolution, DICOM GSDF (Grayscale Standard Display Function) calibration; covers primary diagnostic and secondary review displays | Final | 2021 |
| 892.2010 | QMT | Quantitative Imaging Biomarkers — Technical Performance Assessment: Quantitative Imaging guidance; measurement linearity, bias, repeatability, reproducibility; applies to imaging software extracting quantitative measurements | Final | 2022 |
| 892.2010 | QKQ | Picture Archiving and Communication System (PACS) — medical image storage, management, and retrieval; DICOM conformance (PS3.4 storage, query/retrieve, worklist); 892.2010/892.2040 classification; cybersecurity per Section 524B | Final | — |
| 892.1680 | IZL | Fluoroscopy Systems — image-intensified and flat-panel digital; 21 CFR 1020.32 mandatory fluoroscopic dose rate limits, last-image-hold, cumulative dose display; IEC 60601-2-43 (interventional) and IEC 60601-2-54 (general fluoroscopy) | Final | 2013 |
| 892.5050 | IYO | Radiation Therapy Systems (LINAC / Medical Electron Accelerator) — Class II; IEC 60601-2-1 particular standard; beam characterization, MLC performance, safety interlocks, treatment planning validation per IEC 62083; separate from diagnostic imaging | Final | — |
| 892.2010 | Various | Dose Management Software — radiation dose tracking, recording, and reporting; DICOM RDSR (Radiation Dose Structured Report); may be standalone SaMD or embedded in imaging system; IEC 62304 software lifecycle | Final | — |
| 892.2050, 892.2060, 892.2070, 892.2080 | QAS, QIH, QJU, QMT | AI/ML Radiology Software (expanded) — CADe (892.2050), CADx for cancer (892.2060 — De Novo special controls), medical image analyzer (892.2070 — De Novo special controls), radiological triage/notification (892.2080 — De Novo special controls); each has distinct clinical validation, dataset diversity, and labeling requirements; PCCP recommended for algorithm updates | Final | 2022 |
| 892.5650 | IYE | Ultrasonic Therapy Devices — therapeutic ultrasound for tissue treatment; IEC 60601-2-5 (ultrasound physiotherapy) and IEC 60601-2-62 (HIFU); acoustic output characterization, treatment zone mapping, thermal dose control | Final | — |
| Various | IYO, JAK, IYN | Assembler's Guide to Diagnostic X-Ray Equipment — requirements for X-ray system assemblers; component certification per 21 CFR 1010; assembly and installation compliance | Final | 2013 |
| Various | All X-ray | Pediatric Information for X-ray Imaging Device Premarket Notifications — pediatric-specific protocols, dose optimization for pediatric sizes, labeling recommendations for pediatric imaging | Final | 2017 |

**Key standards**: IEC 60601-2-44 (CT), IEC 60601-2-54 (radiography/fluoroscopy), IEC 60601-2-43 (interventional X-ray), IEC 60601-2-33 (MRI), IEC 60601-2-37 (ultrasound diagnostic), IEC 60601-2-1 (LINAC/medical electron accelerator), IEC 60601-2-5 (ultrasound physiotherapy), IEC 60601-2-62 (HIFU), IEC 62563-1 (display devices — acceptance and constancy testing), IEC 62220 (digital X-ray detectors — DQE), IEC 62464-1 (MRI image quality), IEC 62359 (ultrasound MI/TI measurement), IEC 62083 (radiotherapy treatment planning systems), NEMA XR 25 (CT dose check), NEMA XR 29 (CT SSDE), DICOM PS3 (imaging interoperability), AIUM ODS (ultrasound output display standard), ACR quality assurance phantoms

### RA Trigger Keywords
Match: `x-ray`, `x ray`, `radiographic`, `radiography`, `computed tomography`, `CT scan`, `MRI`, `magnetic resonance`, `ultrasound`, `diagnostic imaging`, `fluoroscop`, `mammograph`, `LINAC`, `linear accelerator`, `radiation therapy`, `radiotherapy`, `dose management`, `DICOM`, `PACS`, `image archiv`, `detector`, `gantry`, `collimator`, `transducer`, `CADe`, `CADx`, `triage`, `image display`, `radiology`, `angiograph`, `interventional imaging`, `image processing`, `image reconstruction`, `dose report`, `acoustic output`

#### 5.10.1 Statutory Performance Standards — Diagnostic X-ray (21 CFR 1020)

> **FEDERAL LAW — NOT VOLUNTARY GUIDANCE.** 21 CFR Part 1020 establishes mandatory performance standards for diagnostic X-ray systems. Compliance is required by statute under the Radiation Control for Health and Safety Act (now codified in 21 CFR Subchapter J).

| Subpart | Title | Applies To |
|---------|-------|-----------|
| 1020.30 | Diagnostic X-ray systems and their major components | All diagnostic X-ray devices |
| 1020.31 | Radiographic equipment | Radiographic X-ray systems |
| 1020.32 | Fluoroscopic equipment | Fluoroscopy systems |
| 1020.33 | Computed tomography (CT) equipment | CT scanners |

**Key requirements**: Radiation output limits, beam quality (HVL), automatic exposure control, dose display (CTDIvol for CT), safety interlocks, component certification (21 CFR 1010).

**Related standards**: IEC 60601-2-44 (CT), IEC 60601-2-54 (radiography/fluoroscopy), IEC 60601-2-43 (interventional), NEMA XR 25 (CT dose check), NEMA XR 29 (CT SSDE)

### 5.11 Neurological Devices (21 CFR 882)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 882.5801 | QAS | Implanted Brain Stimulator (Deep Brain Stimulation) — Class III Special Controls | Final | 2019 |
| 882.5805 | QEB | Transcranial Magnetic Stimulation (rTMS) Systems — Class II Special Controls | Final | 2018 |
| 882.1400 | GWQ | Electroencephalograph (EEG) — Class II (rely on IEC 60601-2-26) | Final | — |
| 882.5801 | — | Seizure Detection Devices — De Novo Special Controls (DEN140033) | Final | 2016 |
| 882.5801 | — | Digital Therapeutics for Neurological Conditions — De Novo Pathway (prescription digital therapeutics) | De Novo | 2017–2024 |
| 882.5870 | GZJ | External Neurostimulator (TENS, Prescription Use) — Class II | Final | — |
| 882.5880 | — | Vagus Nerve Stimulator (VNS) — Class III PMA | Final | — |
| 882.5800 | QBR | Cranial Electrotherapy Stimulator (CES) — Reclassified 2019 via De Novo | De Novo | 2019 |

**Key trend**: Neurology is experiencing rapid De Novo classification activity for digital therapeutics (prescription digital therapeutics/PDTs), AI-enabled seizure detection, and non-invasive neurostimulation. Multiple De Novo authorizations creating new special controls.

**Key standards**: IEC 60601-2-10 (nerve/muscle stimulators), IEC 60601-2-26 (EEG), IEC 60601-2-40 (EMG/EP), ISO 14708-3 (neurostimulator)

### 5.12 General/Plastic Surgery Devices (21 CFR 878)

> **Scope note**: Section 5.3 covers wound care devices (878.4018, 878.4022, 878.4400 surgical dressings) under 21 CFR 878. This section covers non-wound-care general and plastic surgery devices including surgical instruments, implantable materials, tissue management devices, and sterilization/disinfection products reviewed by OHT4.

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 878.4370 | GEI | Surgical Mesh for Hernia Repair — Premarket Notification | Final | 2021 |
| 878.4370 | GEI | Hernia Mesh — Package Labeling Recommendations | Final | 2024 |
| 878.4400 | GEI | Premarket Notification Submissions for Electrosurgical Devices for General Surgery | Final | 2016 |
| 878.4400 | BSY | Premarket Notification [510(k)] Submissions for Bipolar Electrosurgical Vessel Sealers for General Surgery | Final | 2016 |
| 878.4300 | GAB | Surgical Staplers and Staples for Internal Use — Premarket Notifications | Final | 2021 |
| 878.4300 | GAB | Surgical Staplers and Staples for Internal Use — Labeling Recommendations | Final | 2021 |
| 878.4493 | GAT | Surgical Sutures — Class II Special Controls Guidance | Final | 2003 |
| 878.4490 | Various | Absorbable Hemostatic Agent and Dressing — no standalone guidance; rely on cross-cutting biocompatibility (ISO 10993, extended battery for absorbable implants) and performance testing | — | — |
| 878.4010 | KGX | Tissue Adhesive for the Topical Approximation of Skin — Class II Special Controls | Final | 2006 |
| 878.4011 | OQG | Tissue Adhesive with Adjunct Wound Closure Device — Class II Special Controls | Final | 2010 |
| 878.4020 | Various | Tissue Adhesives / Sealants (internal use) — no single guidance; rely on biocompatibility, bond strength testing, and predicate precedent | — | — |
| 880.6885 | LRI | Content and Format of 510(k) Submissions for Liquid Chemical Sterilants/High Level Disinfectants (formaldehyde, glutaraldehyde, peracetic acid, OPA) — note: regulated under 21 CFR 880, not 878 | Final | 2000 |
| 878.4961 | QAS | Robotic Surgical Systems (Mountable Electromechanical Surgical System) — no single guidance; rely on 878.4961 special controls (2022) for Class II mountable systems | Special Controls | 2022 |
| 878.4040 | FYA | Guidance on Premarket Notification [510(k)] Submissions for Surgical Masks | Final | 2004 |
| 878.4580 | FYB | Surgical Gowns — Classification and Performance | Final | 2004 |
| 878.4370 | Various | Surgical Drapes — covered by surgical apparel guidance; Class II | — | — |
| 878.4800 | GEI | Extended Laparoscopy Devices — Guidance for the Preparation of a Premarket Notification | Final | 2003 |
| 878.4011 | Various | Wound Closure Strips / Adhesive Bandages — Class I/II; no device-specific guidance; rely on cross-cutting biocompatibility and sterilization | — | — |
| 878.4780 | FZP | Powered Suction Pump — Guidance Document for 510(k)s | Final | 2000 |
| Various | Various | Absorbable Surgical Materials (sutures, hemostatic agents, mesh components) — absorbable materials require degradation product characterization per ISO 10993-13 (polymers) and ISO 10993-16 (degradation products) | — | — |

> **Surgical stapler reclassification (2021)**: FDA reclassified surgical staplers and staples for internal use (21 CFR 878.4300) from Class I to Class II with special controls. The reclassification **mandates human factors data** in 510(k) submissions, including use-related risk analysis and summative (validation) usability testing with representative surgical end users. This applies to all internal-use staplers (linear, circular, endoscopic) whether manual or powered. See FDA final reclassification order and labeling recommendations guidance.

**Key standards**: IEC 60601-2-2 (particular standard for HF surgical equipment — essential for electrosurgical 510(k)s), IEC 80601-2-77 (particular standard for robotically assisted surgical equipment), USP &lt;881&gt; (sutures — tensile strength, knot pull, needle attachment, diameter), ASTM F1839 (surgical staplers — mechanical performance), ASTM F2392 (surgical mesh — burst strength, ball burst test method), ASTM D2261 (mesh tear resistance), ISO 10993-6 (implantation tests — local effects after implantation, required for mesh, sutures, staples, hemostatic agents), ASTM D1002 (tissue adhesive lap shear bond strength)

### SU Trigger Keywords
Match: `electrosurgical`, `coagulation`, `fulguration`, `vessel seal`, `stapler`, `surgical staple`, `suture`, `hemostatic`, `hemostasis`, `tissue adhesive`, `cyanoacrylate`, `surgical mesh`, `hernia mesh`, `sterilant`, `disinfectant`, `high-level disinfect`, `surgical robot`, `robotic surgery`, `laparoscop`, `surgical gown`, `surgical drape`, `powered suction`

### 5.13 Ear, Nose, and Throat (ENT) Devices (21 CFR 874)

| Regulation | Product Codes | Guidance / Rule | Status | Year |
|-----------|--------------|----------------|--------|------|
| 800.30 | QNJ | OTC Hearing Aid Controls — Final Rule (21 CFR 800.30) | Final Rule | 2022 |
| 874.3310 | QEB | Air-Conduction Hearing Aid — Class II Special Controls | Final | 2022 |
| 874.3310 | MHX | Cochlear Implant Systems — Class III PMA; clinical audiometric outcomes (speech perception in quiet/noise), MRI safety, telemetry validation, surgical safety | PMA | — |
| 874.3310 | QFC | Bone-Anchored Hearing Aid (BAHA) — De Novo/Class II; osseointegrated titanium fixture with audiological performance AND implant fatigue/biocompatibility testing | De Novo | — |
| 874.3540 | EWA | Tympanostomy Tubes (Ventilation Tubes) — Class II; biocompatibility (mucosal contact >=30 days), tube migration/extrusion characterization, lumen patency, delivery system safety | Final | — |
| 868.5895 (cross-ref) | BTK, PLC | Nasal CPAP / Sleep Apnea Oral Appliances — intraoral mandibular repositioning devices for snoring/OSA classified under 874.5470; nasal CPAP under 868.5895; see Section 5.8 (Respiratory) for CPAP guidance | Cross-ref | — |
| 874.4770 | EAR | ENT Endoscopes (sinuscopes, laryngoscopes, otoscopes) — Class I/II; rigid and flexible endoscopes for ear, nose, throat examination and surgery; endoscope sheath barrier guidance | Final | 1999 |
| 874.4420 | EAO | Powered ENT Surgical Instruments — Class II; powered instruments for ENT surgical procedures (microdebriders, powered sinus instruments); electrical safety per IEC 60601-1 | Final | — |
| 874.3310 | Various | Hearing Aid Accessories (programming devices, app-based fitting systems) — Class II; software documentation per IEC 62304, wireless connectivity testing, cybersecurity if Bluetooth/app-controlled | Final | — |
| 874.1050 | DZO | Audiometer — Class II; pure-tone and speech audiometry; calibration per ANSI S3.6, electroacoustic performance, electrical safety | Final | — |
| 874.1090 | EXO | Tympanometer / Acoustic Impedance Meter — Class II; middle ear function assessment; probe tone accuracy, compliance/admittance measurement, reflex threshold detection | Final | — |
| 874.3310 | MIJ | Middle Ear Implants (e.g., Vibrant Soundbridge) — Class II/III; implantable hearing device for sensorineural or conductive hearing loss; audiological performance, MRI safety, implant fatigue testing, biocompatibility | Final | 2000 |
| 874.5490 | Various | Nasal Airway Stent / Dilator — Class II; biocompatibility (mucosal contact), airway patency characterization, migration risk assessment, sterilization validation | Final | — |

**Key regulatory change**: The OTC Hearing Aid Final Rule (effective Oct 17, 2022) created a new regulatory category under 21 CFR 800.30 for OTC hearing aids intended for adults with perceived mild to moderate hearing loss. Key implications:
- No prescription, medical evaluation, or professional fitting required
- New performance and labeling requirements (output limits, ESD, self-fit)
- Supersedes state regulation of OTC hearing aids (federal preemption)
- Existing hearing aid manufacturers must comply with OTC requirements if marketing OTC

**Key standards**: ANSI/CTA-2051, IEC 60118 series (IEC 60118-0 measurement methods, IEC 60118-7 frequency response, IEC 60118-13 electromagnetic compatibility of hearing aids), ANSI S3.22 (specification of hearing aid characteristics), ANSI S3.6 (audiometers — calibration and performance), IEC 60601-2-66 (particular requirements for hearing instruments), ISO 14708-7 (cochlear implant systems — particular requirements), IEC 60268-7 (headphones and earphones — measurement methods)

### 5.14 Gastroenterology and Urology Devices (21 CFR 876)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 876.5600 | FDE | Extracorporeal Shock Wave Lithotripters for Kidney and Ureteral Calculi | Final | 2000 |
| 876.5600 | FDE | Intracorporeal Lithotripters | Final | 1998 |
| 876.1075 | FBC | Biopsy Devices Used in Gastroenterology and Urology | Final | 2003 |
| 876.5130 | EZL | Conventional and Antimicrobial Foley Catheters | Final | 2020 |
| 876.5130 | EZL | Foley Catheters — Safety and Performance Based Pathway | Final | 2020 |
| 876.5980 | MJC | Ureteral Stents — Premarket Notification | Final | 2000 |
| 876.5820 | FKP | Hemodialysis Delivery Systems | Final | 1998 |
| 876.5540 | FKO | Hemodialysis Blood Tubing Sets | Final | 2002 |
| 876.1500 | FDT | Magnetically Maneuvered Capsule Endoscopy System (De Novo) | Final | 2020 |

**Key standards**: IEC 60601-2-18 (endoscopic equipment), IEC 60601-2-36 (lithotripsy), IEC 61846 (pressure pulse lithotripters), ANSI/AAMI ST91 (endoscope processing), AAMI TIR30 (cleaning validation), ISO 10993-4 (hemocompatibility — dialysis)

### 5.15 Obstetrics and Gynecology Devices (21 CFR 884)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 884.4530 | HFC | Product Labeling for Laparoscopic Power Morcellators — includes boxed warning requirement for risk of spreading unsuspected uterine cancer | Final | 2020 |
| 884.2600 | HGJ | Fetal Electroencephalographic Monitor — fetal monitoring guidance | Final | — |
| 884.2660 | HGO | Marketing Clearance of Diagnostic Ultrasound Systems and Transducers (fetal Doppler/ultrasonic monitoring) | Final | 2023 |
| 884.5360 | HCJ, HIB | Contraceptive Intrauterine Device (IUD) and Introducer — Class III special controls, PMA required for hormonal IUDs | — | — |
| 884.1720 | HET | Hysteroscope and Accessories | — | — |
| 884.3575 | — | Pelvic Floor Repair (Transvaginal Mesh) — reclassified to Class III (2016); FDA ordered manufacturers to stop distribution for POP indication (2019) | Final (market order) | 2019 |
| 878.3530 | MQV, LPS | Breast Implants (Saline and Silicone Gel-Filled) — PMA with special labeling, boxed warning for BIA-ALCL; note: regulated under 21 CFR 878, reviewed by OB panel | Final | 2020 |
| 884.4520 | HFA | Cervical Dilators — Obstetric-Gynecologic General Use Instruments | — | — |
| 884.2730 | HGW | Home Uterine Activity Monitors — Class II Special Controls | Final | 2000 |
| 884.2740 | HGX | Computerized Labor Monitoring Systems — Class II Special Controls | Final | 2004 |

**Key regulatory actions**:
- Laparoscopic power morcellators require **boxed warning** about risk of spreading unsuspected uterine cancer (2020)
- Transvaginal mesh for POP reclassified to **Class III** (2016); most manufacturers withdrew from market
- IUDs are **Class III** devices requiring PMA
- Breast implants require **boxed warning** about BIA-ALCL (breast implant-associated anaplastic large cell lymphoma) and long-term follow-up studies

**Key standards**: IEC 60601-2-37 (ultrasonic diagnostic and monitoring equipment), IEC 60601-2-5 (ultrasonic physiotherapy), ISO 10993 series (biocompatibility for prolonged implants), IEC 60601-1-8 (alarm systems — fetal monitors), ISO 7439 (copper-bearing IUD requirements), AIUM Output Display Standard (acoustic output for fetal imaging)

### OB/GYN Trigger Keywords
Match: `fetal`, `fetal heart rate`, `cardiotocograph`, `morcellator`, `morcellation`, `IUD`, `intrauterine device`, `hysteroscope`, `uterine`, `endometrial ablation`, `contraceptive`, `obstetric`, `gynecologic`, `cervical dilator`, `colposcope`, `pelvic mesh`, `breast implant`

### 5.16 Physical Medicine Devices (21 CFR 890)

| Regulation | Product Codes | Guidance | Status | Year |
|-----------|--------------|---------|--------|------|
| 890.3860 | IOR (ITI) | Guidance for the Preparation of Premarket Notification [510(k)] Applications for Mechanical and Powered Wheelchairs, and Motorized Three-Wheeled Vehicles | Final | 1995 |
| 890.3860 | ITI | Tilt-in-Space Wheelchair — covered by wheelchair guidance above; Class II special controls | Final | 1995 |
| 890.3480 | QFR | Powered Lower Extremity Exoskeleton — De Novo classification (DEN160027); special controls codified in 21 CFR 890.3480 | De Novo | 2015 |
| 890.3420 | IQJ | External Limb Prosthetic Component — Class I/II; no device-specific FDA guidance; standards-based pathway (ISO 22523, ISO 10328, ISO 22675) | N/A | — |
| 890.5850 | IRN (ISA) | Powered Muscle Stimulator for Rehabilitation — Class II; no device-specific guidance; rely on IEC 60601-1 and IEC 60601-2-10 | N/A | — |
| 890.5150 | IOQ | Continuous Passive Motion (CPM) Device — Class II; no device-specific guidance; rely on IEC 60601-1 and cross-cutting guidance | N/A | — |
| 890.5300 | IRS | Policy Clarification and Premarket Notification [510(k)] Submissions for Ultrasonic Diathermy Devices | Final | 1993 |
| 890.5350–5380 | IRM | Guidance for the Preparation of Premarket Notification [510(k)] Applications for Exercise Equipment | Final | 1996 |

**Note**: TENS devices (transcutaneous electrical nerve stimulators for pain relief) are regulated under **21 CFR 882.5870/882.5890** (Neurological Devices), not 21 CFR 890 — see Section 5.11. Powered muscle stimulators (NMES/EMS) for rehabilitation ARE under 21 CFR 890.5850.

**Key standards**: ISO 7176 series (wheelchairs — stability, braking, fatigue, power systems), IEC 60601-2-10 (nerve and muscle stimulators), ISO 22523 (external limb prostheses — general requirements), ISO 10328 (lower-limb prosthesis structural testing), ISO 22675 (prosthetic ankle-foot device testing), IEC 60601-1 (general electrical safety), IEC 62133 (lithium battery safety)

### PM Trigger Keywords
Match: `wheelchair`, `powered wheelchair`, `power assist`, `mobility device`, `exoskeleton`, `robotic orthosis`, `muscle stimulator`, `NMES`, `neuromuscular electrical stimulation`, `prosthetic limb`, `prosthetic leg`, `prosthetic foot`, `orthotic`, `orthosis`, `diathermy`, `iontophoresis`, `continuous passive motion`, `CPM`, `exercise equipment`, `gait rehabilitation`, `rehabilitation device`

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
Match: `combination product`, `drug-device`, `drug-eluting`, `drug-coated`, `biologic-device`, `antimicrobial agent`, `drug delivery device`

---

## 7.5 Additive Manufacturing (3D Printing)

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Technical Considerations for Additive Manufactured Medical Devices | Final | 2017 | All 3D-printed / additively manufactured devices |
| Recommended Content and Format of Non-Clinical Bench Performance Testing Information in Premarket Submissions | Final | 2019 | Devices requiring bench performance data |

**Key standards**: ASTM F3001 (Ti-6Al-4V via PBF), ASTM F2924 (Ti-6Al-4V via PBF-EB), ASTM F3055 (Ni alloy via PBF), ISO/ASTM 52900 (AM terminology)

### 3D Printing Trigger Keywords
Match: `3d print`, `3d-printed`, `additive manufactur`, `selective laser sintering`, `selective laser melting`, `electron beam melting`, `fused deposition`, `binder jetting`

---

## 7.6 Animal-Derived Materials

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Guidance for FDA Reviewers and Industry: Medical Devices Containing Materials Derived from Animal Sources (Except for In Vitro Diagnostic Devices) | Final | 1998 | Devices with animal-derived components |

**Key concern**: Bovine Spongiform Encephalopathy (BSE) / Transmissible Spongiform Encephalopathy (TSE) risk assessment required for bovine, ovine, and caprine-derived materials.

### Animal-Derived Trigger Keywords
Match: `collagen`, `gelatin`, `bovine`, `porcine`, `animal-derived`, `animal tissue`, `equine`, `ovine`, `decellularized`, `xenograft`, `biologic matrix`

---

## 7.7 Home Use Devices

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Design Considerations for Devices Intended for Home Use | Final | 2014 | Devices intended for home / lay user environments |

**Key considerations**: Human factors for non-professional users (IEC 62366-1), environmental conditions, labeling for lay users, training requirements.

### Home Use Trigger Keywords
Match: `home use`, `over-the-counter`, `otc device`, `patient self-test`, `lay user`, `home monitoring`, `self-administered`

---

## 7.8 Pediatric Devices

| Document | Status | Year | Applies To |
|----------|--------|------|-----------|
| Premarket Assessment of Pediatric Medical Devices | Final | 2020 | Devices intended for pediatric populations |

**Key considerations**: Pediatric device extrapolation from adult data, growth accommodation, dose/size scaling, Pediatric Device Consortia.

### Pediatric Trigger Keywords
Match: `pediatric`, `neonatal`, `infant`, `children`, `child`, `neonate`, `newborn`, `adolescent`

---

## 7.9 Latex-Containing Devices

| Regulation | Document | Status | Applies To |
|-----------|----------|--------|-----------|
| 21 CFR 801.437 | User labeling for devices that contain natural rubber | Final | All devices containing natural rubber latex |

**Key requirements**: Labeling must state "Caution: This Product Contains Natural Rubber Latex Which May Cause Allergic Reactions." Extended ISO 10993 biocompatibility panel for latex contact.

### Latex Trigger Keywords
Match: `latex`, `natural rubber`, `natural rubber latex`

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
| 878.4370 | Surgical mesh | Yes | Hernia repair guidance + labeling (2024) |
| 878.4400 | Electrosurgical device | Yes | Electrosurgical devices for general surgery; IEC 60601-2-2 |
| 878.4300 | Surgical stapler | Yes | Reclassified Class II (2021); **human factors mandatory** |
| 878.4493 | Surgical sutures | Yes | Class II special controls; USP &lt;881&gt; |
| 878.4490 | Hemostatic agent | No | Cross-cutting biocompatibility + performance testing |
| 878.4010 | Tissue adhesive (topical) | Yes | Class II special controls |
| 878.4961 | Robotic surgical system | Yes (special controls) | 878.4961 special controls (2022); IEC 80601-2-77 |
| 878.4800 | Laparoscopic instruments | Yes | Extended laparoscopy guidance (2003) |
| 880.6885 | Liquid chemical sterilant/HLD | Yes | LCS/HLD 510(k) format guidance; note: 21 CFR 880 |
| 892.1700 | Diagnostic X-ray (general) | Yes | X-ray IEC conformance guidance; 21 CFR 1020 mandatory |
| 892.1750 | CT scanner | Yes | IEC 60601-2-44; CTDIvol/DLP dose display; NEMA XR 25/29 |
| 892.1720 | Digital mammography | Yes | MQSA requirements; 21 CFR 900 Subpart B |
| 892.1560 | Diagnostic ultrasound | Yes | Ultrasound marketing clearance guidance; MI/TI per ODS |
| 892.1680 | Fluoroscopy system | Yes | 21 CFR 1020.32; IEC 60601-2-43/-2-54 |
| 892.2010 | Medical image display / PACS | Yes | Display devices guidance; DICOM GSDF; PACS cybersecurity |
| 892.2050 | CADe/CADx | Yes | AI/ML imaging guidance; clinical performance assessment |
| 892.2060 | CADx for cancer | Yes (De Novo) | De Novo special controls — distinct from 892.2050 |
| 892.2070 | Medical image analyzer | Yes (De Novo) | De Novo special controls — quantitative imaging |
| 892.2080 | Radiological triage/notification | Yes (De Novo) | De Novo special controls — sensitivity thresholds, notification |
| 892.5050 | Radiation therapy (LINAC) | Yes | IEC 60601-2-1; separate from diagnostic imaging |
| 892.5650 | Ultrasonic therapy | Yes | IEC 60601-2-5; acoustic output characterization |
| 866.3373 | NAATx | Yes | Nucleic acid IVD guidance |
| 868.5895 | CPAP | Yes | CPAP special controls |
| 880.5075 | Exam gloves | Yes | Gloves special controls |
| 880.5725 | Infusion pump | Yes | Infusion Pump TPLC guidance |
| 872.3275 | Dental implants | Yes | Root-form implant guidance |
| 800.30 | OTC hearing aid | Yes | OTC Hearing Aid Final Rule |
| 874.3310 | Air-conduction hearing aid | Yes | Class II special controls |
| 876.5130 | Foley catheter | Yes | Foley catheter guidance |
| 876.5600 | Lithotripter | Yes | ESWL guidance |
| 876.5820 | Hemodialysis system | Yes | Hemodialysis guidance |
| 884.4530 | Power morcellator | Yes | Morcellator labeling — **boxed warning** required |
| 884.2660 | Fetal ultrasonic monitor | Yes | Ultrasound systems guidance (fetal Doppler) |
| 884.5360 | IUD (contraceptive) | Yes (Class III) | PMA required; special controls |
| 884.1720 | Hysteroscope | No | Use cross-cutting (biocompatibility, sterilization) |
| 884.3575 | Transvaginal mesh (POP) | Yes (market order) | **Class III** — POP mesh ordered off market (2019) |
| 884.4520 | Cervical dilator | No | Use cross-cutting guidance |
| 884.2730 | Home uterine activity monitor | Yes | HUAM special controls |
| 878.3530 | Breast implant | Yes | PMA with special labeling, BIA-ALCL boxed warning |
| 882.5870 | External neurostimulator (TENS) | Yes | Class II — IEC 60601-2-10 |
| 882.5805 | TMS system | Yes | rTMS Class II special controls |
| 882.5801 | Deep brain stimulator | Yes (Class III) | Class III — PMA special controls |
| 882.1400 | EEG | No (rely on standard) | Use IEC 60601-2-26 + cross-cutting |
| 882.5800 | Cranial electrotherapy stimulator | Yes | De Novo reclassified 2019 |
| 890.3860 | Powered wheelchair | Yes | Wheelchair 510(k) guidance (1995) |
| 890.3480 | Powered exoskeleton | Yes (De Novo) | DEN160027 — special controls in 21 CFR 890.3480 |
| 890.3420 | External limb prosthetic | No | Standards-based (ISO 22523, ISO 10328) |
| 890.5850 | Powered muscle stimulator | No | Use IEC 60601-2-10 + cross-cutting |
| 890.5150 | Continuous passive motion (CPM) | No | Use IEC 60601-1 + cross-cutting |
| 890.5300 | Ultrasonic diathermy | Yes | Diathermy policy clarification (1993) |

---

## Integration Notes

- `/fda:guidance` should check this index FIRST, then web-search for additional/newer guidance
- Product codes listed are representative — check the classification API for the complete mapping
- URLs may change — use WebSearch as verification/fallback
- Cross-cutting guidance triggers should be evaluated from device description keywords
- The FY 2026 agenda items are *planned* — check FDA.gov for actual publication status
