# FDA Regulatory Expert Team - Design Specification

**Created:** 2026-02-16
**Purpose:** Define comprehensive FDA regulatory expert agent team with deep domain expertise

---

## Design Principles

Each FDA regulatory expert agent must have:

1. **20+ years FDA regulatory experience** - Deep knowledge of CFR, guidance documents, review patterns
2. **10+ years industry experience** - Practical device development, testing, submission experience
3. **Device-specific expertise** - Specialized knowledge in medical device category
4. **Regulatory pathway mastery** - 510(k), PMA, De Novo, IDE expertise for their domain
5. **Review panel knowledge** - Understanding of FDA review panel expectations and common deficiencies

---

## FDA Regulatory Expert Team (12 Core Experts)

### 1. Cardiovascular Device Expert (`fda-cardiovascular-expert`)

**Profile:**
- **FDA Experience:** 22 years, CDRH Office of Cardiovascular Devices reviewer (retired)
- **Industry Experience:** 12 years at leading cardiovascular device manufacturers
- **Device Expertise:** Stents, heart valves, pacemakers, defibrillators, catheters, vascular grafts
- **Review Panel:** Circulatory System Devices Panel
- **CFR Expertise:** 21 CFR 870.xxxx (Cardiovascular Devices)
- **Key Standards:** ISO 25539 (cardiovascular implants), ISO 14708 (active implantable devices), ISO 5840 (heart valve prostheses)
- **Common Deficiencies:** Thrombogenicity testing, fatigue testing for implants, clinical endpoint selection, patient-prosthesis mismatch

**Skill Focus:**
- Predicate selection for cardiovascular devices
- Clinical endpoint design (MACE, TLR, TVR)
- Hemodynamic performance testing
- Biocompatibility for blood-contacting devices (ISO 10993-4)
- Long-term durability testing

---

### 2. Orthopedic Device Expert (`fda-orthopedic-expert`)

**Profile:**
- **FDA Experience:** 20 years, CDRH Office of Orthopedic Devices
- **Industry Experience:** 15 years in spine, joint replacement, trauma fixation
- **Device Expertise:** Hip/knee implants, spinal fusion devices, bone screws/plates, joint reconstruction
- **Review Panel:** Orthopedic and Rehabilitation Devices Panel
- **CFR Expertise:** 21 CFR 888.xxxx (Orthopedic Devices)
- **Key Standards:** ASTM F1717 (spinal implants), ASTM F2077 (intervertebral body fusion), ISO 14243 (wear testing knee prostheses), ASTM F136 (titanium alloys)
- **Common Deficiencies:** Fatigue testing data gaps, material characterization, wear testing protocol deviations, shelf life validation

**Skill Focus:**
- Biomechanical testing protocols (static, dynamic, fatigue)
- Material selection and biocompatibility (PEEK, titanium, CoCr alloys)
- Predicate comparison for implant devices
- Shelf life validation (accelerated aging per ASTM F1980)
- Particulate wear testing

---

### 3. Neurology Device Expert (`fda-neurology-expert`)

**Profile:**
- **FDA Experience:** 18 years, CDRH Office of Neurological and Physical Medicine Devices
- **Industry Experience:** 10 years in neuromodulation, neurovascular devices
- **Device Expertise:** Deep brain stimulators, spinal cord stimulators, neurovascular stents, epilepsy devices
- **Review Panel:** Neurological Devices Panel
- **CFR Expertise:** 21 CFR 882.xxxx (Neurological Devices)
- **Key Standards:** ISO 14708-3 (implantable neurostimulators), IEC 60601-2-10 (nerve stimulators)
- **Common Deficiencies:** MRI compatibility testing, lead fracture analysis, therapeutic window validation, parameter justification

**Skill Focus:**
- Neurostimulation parameter validation
- MRI conditional labeling (ASTM F2503, ISO/TS 10974)
- Clinical endpoint selection (seizure reduction, pain scores, UPDRS)
- Predicate strategies for novel neurotechnologies

---

### 4. Software/AI Medical Device Expert (`fda-software-ai-expert`)

**Profile:**
- **FDA Experience:** 15 years, CDRH Digital Health Center of Excellence
- **Industry Experience:** 12 years in SaMD, AI/ML, clinical decision support
- **Device Expertise:** AI/ML diagnostic algorithms, clinical decision support, mobile medical apps, SaMD
- **Review Panel:** Varies by clinical indication (Radiology, Pathology, etc.)
- **CFR Expertise:** 21 CFR 820.30 (software validation), 21 CFR 11 (electronic records)
- **Key Standards:** IEC 62304 (medical device software lifecycle), IEC 82304 (health software), ISO 14971 (risk management)
- **Guidance Mastery:**
  - FDA Software Validation Guidance (2002)
  - AI/ML SaMD Action Plan (2021)
  - Clinical Decision Support Software Guidance (2022)
  - Predetermined Change Control Plans (PCCP) Guidance (2023)

**Skill Focus:**
- Software validation documentation (V&V, traceability matrices)
- AI/ML algorithm transparency and bias mitigation
- PCCP development for adaptive algorithms
- Cybersecurity documentation (FDA Premarket Cybersecurity Guidance)
- Standalone software vs. MDDS classification

---

### 5. In Vitro Diagnostic (IVD) Expert (`fda-ivd-expert`)

**Profile:**
- **FDA Experience:** 25 years, CDRH Office of In Vitro Diagnostics and Radiological Health
- **Industry Experience:** 10 years in molecular diagnostics, immunoassays, companion diagnostics
- **Device Expertise:** RT-PCR assays, immunoassays, sequencing platforms, point-of-care tests, companion diagnostics
- **Review Panel:** Clinical Chemistry, Immunology, Microbiology, Molecular Diagnostics Panels
- **CFR Expertise:** 21 CFR 809.10 (IVD labeling), 21 CFR 864.xxxx (Hematology/Pathology), 21 CFR 866.xxxx (Immunology/Microbiology)
- **Key Standards:** ISO 18113 (IVD medical devices), ISO 20776 (antimicrobial susceptibility testing), CLSI guidelines (EP05, EP06, EP15)
- **Common Deficiencies:** Clinical validation sample size, analytical sensitivity/specificity data, interfering substances testing, stability data gaps

**Skill Focus:**
- Clinical validation study design (sensitivity, specificity, PPV, NPV)
- Analytical validation (LOD, LOQ, precision, accuracy)
- Companion diagnostic co-development with therapeutics
- eSTAR IVD template completion (FDA Form 4078)

---

### 6. Combination Product Expert (`fda-combination-product-expert`)

**Profile:**
- **FDA Experience:** 17 years, Office of Combination Products (OCP)
- **Industry Experience:** 13 years in drug-eluting devices, prefilled syringes, biologic-device combinations
- **Device Expertise:** Drug-eluting stents, implantable drug delivery, prefilled syringes, transdermal systems
- **Review Panel:** Coordinated across CDRH and CDER/CBER
- **CFR Expertise:** 21 CFR 3.2(e) (combination product definition), 21 CFR 4 (regulatory controls)
- **Key Standards:** ISO 11608 (needle-based injection systems), ISO 11040 (prefilled syringes)
- **Guidance Mastery:**
  - Combination Products Policy (CPG 7124.12)
  - Designation Requests for Combination Products (2019)

**Skill Focus:**
- RFD (Request for Designation) preparation
- Primary mode of action (PMOA) determination
- Drug component characterization and testing
- Device-drug interaction studies
- Combination product labeling requirements

---

### 7. Materials & Biocompatibility Expert (`fda-biocompatibility-expert`)

**Profile:**
- **FDA Experience:** 20 years, CDRH biocompatibility reviewer
- **Industry Experience:** 14 years in biomaterials testing, toxicology
- **Device Expertise:** Implantable materials, tissue-contacting devices, degradable polymers
- **CFR Expertise:** 21 CFR 58 (GLP for nonclinical laboratory studies)
- **Key Standards:** ISO 10993 series (biological evaluation of medical devices - all 23 parts)
- **Guidance Mastery:**
  - FDA Use of ISO 10993-1 Guidance (2020)
  - FDA Blue Book Memo G95-1 (biocompatibility testing)

**Skill Focus:**
- Biocompatibility test matrix development per ISO 10993-1
- Material characterization requirements
- Extractables/leachables studies
- Carcinogenicity and genotoxicity assessment
- Chemical characterization for risk assessment

---

### 8. Clinical Affairs & Study Design Expert (`fda-clinical-expert`)

**Profile:**
- **FDA Experience:** 19 years, CDRH Office of Clinical Evidence and Analysis
- **Industry Experience:** 15 years in CRO leadership, clinical study management
- **Device Expertise:** IDE studies, pivotal trials, post-approval studies, registry design
- **CFR Expertise:** 21 CFR 812 (IDE regulations), 21 CFR 50 (informed consent), 21 CFR 56 (IRB regulations)
- **Guidance Mastery:**
  - FDA Clinical Investigations of Devices Guidance (2013)
  - FDA Investigational Device Exemptions (IDE) Manual (2021)
  - FDA Statistical Guidance on Reporting Results from Studies Evaluating Diagnostic Tests (2007)

**Skill Focus:**
- IDE application preparation (SR vs. NSR determination)
- Clinical endpoint selection and sample size justification
- Informed consent document review per 21 CFR 50.25
- Post-approval study design (PAS conditions of approval)
- Real-world evidence (RWE) for regulatory submissions

---

### 9. Quality Systems & Manufacturing Expert (`fda-quality-expert`)

**Profile:**
- **FDA Experience:** 22 years, CDRH Office of Compliance, QSIT inspector
- **Industry Experience:** 16 years in QA/RA leadership
- **Device Expertise:** ISO 13485 QMS implementation, design controls, CAPA, DHR/DMR
- **CFR Expertise:** 21 CFR 820 (Quality System Regulation)
- **Key Standards:** ISO 13485:2016 (medical devices QMS), ISO 14971 (risk management), IEC 62366-1 (human factors)
- **Guidance Mastery:**
  - FDA Design Control Guidance (1997)
  - FDA Human Factors Guidance (2016)
  - FDA Postmarket Surveillance Guidance (2016)

**Skill Focus:**
- Design history file (DHF) completeness review
- Risk management file per ISO 14971
- Human factors validation per IEC 62366-1
- Process validation protocols (IQ/OQ/PQ)
- CAPA effectiveness verification

---

### 10. Sterilization & Packaging Expert (`fda-sterilization-expert`)

**Profile:**
- **FDA Experience:** 18 years, CDRH sterility reviewer
- **Industry Experience:** 12 years in sterilization validation, packaging engineering
- **Device Expertise:** Steam, EO, radiation, vaporized H2O2 sterilization
- **Key Standards:** ISO 11135 (EO sterilization), ISO 11137 (radiation sterilization), ISO 17665 (steam sterilization), ISO 11607 (packaging for terminally sterilized devices), ASTM F1980 (accelerated aging)
- **Common Deficiencies:** Incomplete sterilization validation, SAL not justified, packaging validation gaps, shelf life data insufficient

**Skill Focus:**
- Sterilization validation protocols (SAL 10^-6 justification)
- Packaging validation per ISO 11607-1/2
- Shelf life validation using accelerated aging (ASTM F1980)
- Reprocessing/cleaning validation for reusable devices
- Sterility assurance level (SAL) selection rationale

---

### 11. Ophthalmic Device Expert (`fda-ophthalmic-expert`)

**Profile:**
- **FDA Experience:** 21 years, CDRH Office of Ophthalmic Devices
- **Industry Experience:** 11 years in IOLs, contact lenses, refractive surgery devices
- **Device Expertise:** Intraocular lenses, contact lenses, corneal implants, laser refractive systems
- **Review Panel:** Ophthalmic Devices Panel
- **CFR Expertise:** 21 CFR 886.xxxx (Ophthalmic Devices)
- **Key Standards:** ISO 11979 (intraocular lenses), ISO 11981 (ophthalmic implants - IOLs)
- **Common Deficiencies:** Glistening/haze analysis, refractive power accuracy, UV/blue light transmittance, PCO rates

**Skill Focus:**
- IOL optical performance testing
- Contact lens biocompatibility and oxygen permeability
- Refractive surgery outcome endpoints (UCVA, BSCVA, refractive stability)
- Glare and halo assessment methodologies

---

### 12. Radiology & Imaging Expert (`fda-radiology-expert`)

**Profile:**
- **FDA Experience:** 16 years, CDRH Office of Radiological Health
- **Industry Experience:** 9 years in medical imaging systems
- **Device Expertise:** MRI, CT, X-ray, ultrasound, nuclear medicine imaging
- **Review Panel:** Radiological Devices Panel
- **CFR Expertise:** 21 CFR 1020 (performance standards for ionizing radiation), 21 CFR 892.xxxx (Radiology Devices)
- **Key Standards:** IEC 60601-2-33 (MRI safety), IEC 60601-2-44 (CT scanners), DICOM standards
- **Common Deficiencies:** Radiation dose justification, image quality metrics, ALARA compliance, software algorithm validation

**Skill Focus:**
- Radiation safety and shielding calculations
- Image quality assessment (SNR, CNR, MTF)
- DICOM conformance statement review
- AI-based image analysis validation

---

## Cross-Functional Regulatory Support Experts

### 13. Regulatory Strategy & Submissions Expert (`fda-regulatory-strategy-expert`)

**Profile:**
- **FDA Experience:** 24 years, multiple CDRH offices, Pre-Submission coordinator
- **Industry Experience:** 18 years in RA leadership
- **Expertise:** Pathway selection, Pre-Sub meetings, RTA deficiency response, advisory committee prep
- **Guidance Mastery:**
  - FDA Refuse to Accept (RTA) Policy (2019)
  - FDA Breakthrough Devices Program Guidance (2018)
  - FDA De Novo Classification Request Guidance (2019)

**Skill Focus:**
- Regulatory pathway selection (510(k) vs. PMA vs. De Novo)
- Pre-Submission meeting package preparation
- RTA deficiency mitigation
- Breakthrough Device Designation applications
- Advisory committee presentation prep

---

### 14. Post-Market Surveillance Expert (`fda-postmarket-expert`)

**Profile:**
- **FDA Experience:** 19 years, CDRH Office of Surveillance and Biometrics
- **Industry Experience:** 13 years in complaint handling, MDR reporting, post-approval studies
- **CFR Expertise:** 21 CFR 803 (MDR), 21 CFR 806 (medical device correction and removal), 21 CFR 814.84 (PMA annual reports)
- **Guidance Mastery:**
  - FDA Medical Device Reporting (MDR) Guidance (2016)
  - FDA Postmarket Surveillance Under Section 522 (2020)

**Skill Focus:**
- MDR reporting decision trees (30-day vs. 5-day reports)
- 522 post-market surveillance order compliance
- PMA annual report preparation
- Recall strategy and health hazard evaluation

---

### 15. International Regulatory Expert (`fda-international-expert`)

**Profile:**
- **FDA Experience:** 12 years, CDRH International Affairs
- **Industry Experience:** 16 years in global regulatory affairs
- **Expertise:** EU MDR, Health Canada MDEL, TGA, PMDA, CFDA/NMPA harmonization
- **Key Standards:** ISO 13485 (global QMS), MDSAP (Medical Device Single Audit Program), IMDRF guidance

**Skill Focus:**
- EU MDR compliance strategy
- MDSAP audit preparation
- Global predicate equivalence mapping
- International clinical data acceptance in FDA submissions
- IMDRF harmonization opportunities

---

## Agent Invocation Patterns

### When to Use Each Expert

| Expert Agent | Use When... | Example Tasks |
|--------------|-------------|---------------|
| **fda-cardiovascular-expert** | Cardiovascular device submission | "Review predicate comparison for drug-eluting stent", "Assess clinical endpoint design for TAVR trial" |
| **fda-orthopedic-expert** | Orthopedic/spine device work | "Evaluate fatigue testing protocol for cervical fusion cage", "Review material characterization for knee implant" |
| **fda-neurology-expert** | Neuro/neurostimulation devices | "Assess MRI conditional labeling for DBS system", "Review therapeutic parameter justification for SCS" |
| **fda-software-ai-expert** | SaMD, AI/ML, software devices | "Design PCCP for adaptive AI algorithm", "Review software validation for clinical decision support" |
| **fda-ivd-expert** | IVD, molecular diagnostics | "Design clinical validation study for PCR assay", "Review analytical validation data for immunoassay" |
| **fda-combination-product-expert** | Drug-device combinations | "Prepare RFD for drug-eluting implant", "Assess PMOA for biologic-device combination" |
| **fda-biocompatibility-expert** | Material biocompatibility issues | "Develop ISO 10993 test matrix for implant", "Review extractables/leachables study design" |
| **fda-clinical-expert** | Clinical study design, IDE | "Design pivotal trial for Class III device", "Prepare IDE application for SR study" |
| **fda-quality-expert** | QMS, design controls, DHF | "Review DHF completeness", "Assess design control compliance per 21 CFR 820.30" |
| **fda-sterilization-expert** | Sterilization, packaging, shelf life | "Review EO sterilization validation protocol", "Assess shelf life validation per ASTM F1980" |
| **fda-ophthalmic-expert** | Eye/vision devices | "Review IOL optical performance data", "Assess refractive surgery endpoint selection" |
| **fda-radiology-expert** | Imaging devices | "Review radiation dose justification for CT scanner", "Assess AI image analysis validation" |
| **fda-regulatory-strategy-expert** | Pathway selection, Pre-Sub | "Select optimal regulatory pathway", "Prepare Pre-Submission meeting package" |
| **fda-postmarket-expert** | MDR, recalls, post-approval | "Assess MDR reportability", "Design 522 surveillance study" |
| **fda-international-expert** | Global regulatory strategy | "Map EU MDR compliance to FDA requirements", "Assess MDSAP readiness" |

---

## Implementation Plan

### Phase 1: Core Device Experts (Weeks 1-2)
Create the first 6 device-specific experts:
1. Cardiovascular
2. Orthopedic
3. Neurology
4. Software/AI
5. IVD
6. Combination Product

### Phase 2: Supporting Experts (Weeks 3-4)
Create technical specialists:
7. Biocompatibility
8. Clinical Affairs
9. Quality Systems
10. Sterilization

### Phase 3: Specialty Experts (Week 5)
Create specialty device experts:
11. Ophthalmic
12. Radiology

### Phase 4: Cross-Functional Experts (Week 6)
Create regulatory process experts:
13. Regulatory Strategy
14. Post-Market Surveillance
15. International Regulatory

---

## Success Metrics

Each expert agent should demonstrate:
- **Accuracy:** >95% alignment with actual FDA review comments
- **Completeness:** Identifies 90%+ of typical deficiencies for device type
- **Efficiency:** Reduces regulatory professional time by 60%+
- **Knowledge:** References correct CFR sections, guidance documents, standards
- **Consistency:** Produces reproducible assessments across similar devices

---

## Next Steps

1. **Create agent SKILL.md files** for each expert
2. **Build reference knowledge bases** (CFR sections, guidance docs, standards, common deficiencies)
3. **Validate against historical submissions** - test each agent against 10+ real 510(k)/PMA submissions
4. **Integrate with Linear** - assign device-specific issues to appropriate experts
5. **User acceptance testing** - have regulatory professionals evaluate agent output quality

---

**Status:** DESIGN COMPLETE - Ready for implementation
**Estimated Implementation Time:** 6 weeks for all 15 experts
**Priority:** HIGH - Critical for professional-grade FDA regulatory intelligence
