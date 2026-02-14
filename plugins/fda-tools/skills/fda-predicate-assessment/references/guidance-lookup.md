# FDA Guidance Document Lookup Reference

Centralized reference for finding and mapping FDA guidance documents to device types and testing requirements. Used by `/fda:guidance` and referenced by `/fda:research`.

## FDA Guidance URL Patterns

### Search Strategies

**Primary**: Search fda.gov for device-specific guidance using the CFR regulation number and device classification name.

```
WebSearch: "{regulation_number}" guidance site:fda.gov/medical-devices
WebSearch: "{device_name}" "special controls" OR "class II" guidance site:fda.gov
WebSearch: "{device_name}" "510(k)" guidance testing requirements site:fda.gov
```

**Secondary**: Search for product-code-specific guidance pages.

```
WebSearch: "{product_code}" "product code" guidance site:fda.gov
```

**Tertiary**: Search FDA guidance database directly.

```
https://www.fda.gov/medical-devices/guidance-documents-medical-devices-and-radiation-emitting-products
```

### Common FDA Guidance URL Patterns

| Pattern | Example |
|---------|---------|
| Device-specific guidance | `https://www.fda.gov/regulatory-information/search-fda-guidance-documents/{title-slug}` |
| Special controls guidance | `https://www.fda.gov/medical-devices/guidance-documents-medical-devices-and-radiation-emitting-products/{title-slug}` |
| Draft guidance | Same patterns, look for "Draft" in title |

### Guidance Document Status

- **Final**: Represents FDA's current thinking — follow these requirements
- **Draft**: Open for comment — not binding but indicates FDA's direction
- **Withdrawn**: No longer reflects current thinking — check for replacement
- **Superseded**: Replaced by newer guidance — use the replacement

## Cross-Cutting Guidance Trigger Table

These guidances apply based on device characteristics, regardless of product code. Determined via a **3-tier priority system**: API-authoritative flags → enhanced keyword matching → classification heuristics.

### Trigger Priority

1. **Tier 1 — API Flags** (authoritative, always correct): openFDA `implant_flag`, `life_sustain_support_flag`, AccessGUDID `is_sterile`, `sterilization_methods`, `is_single_use`, `mri_safety`, `is_labeled_as_nrl`, `device_class`, review panel
2. **Tier 2 — Keyword Matching** (fallback): Word-boundary regex with negation awareness, applied to BOTH user `--device-description` AND API `definition` field
3. **Tier 3 — Classification Heuristics** (safety net): Regulation number family mapping, product code patterns

### Full Trigger Table

| Trigger Condition | API Authority | Guidance Topic | Key Guidance Document | Key Standards |
|-------------------|--------------|---------------|----------------------|---------------|
| **All devices** | — | Biocompatibility | "Use of International Standard ISO 10993-1" | ISO 10993-1, -5, -10, -11 |
| **All 510(k) devices** | — | SE determination | "The 510(k) Program: Evaluating Substantial Equivalence" | — |
| **All 510(k) devices** | — | Labeling | "Medical Device Labeling — 510(k) Guidance" | 21 CFR 801 |
| **Class II devices** | `device_class == "2"` | Special controls | Product-code-specific special controls guidance | Varies |
| **Class III devices** | `device_class == "3"` | PMA-level scrutiny | Clinical data likely required | Varies |
| **Sterile devices** | `GUDID is_sterile == true` | Sterilization validation | "Sterility Information in 510(k) Submissions" | ISO 11135/11137/17665 |
| **Sterile devices** | `GUDID is_sterile == true` | Shelf life / aging | "Shelf Life of Medical Devices" | ASTM F1980, F2097 |
| **EO sterilized** | `GUDID method contains "EO"` | EO sterilization | "Ethylene Oxide Sterilization for Medical Devices" | ISO 11135 |
| **Radiation sterilized** | `GUDID method contains "radiation/gamma"` | Radiation sterilization | "Radiation Sterilization of Medical Devices" | ISO 11137 |
| **Steam sterilized** | `GUDID method contains "steam"` | Steam sterilization | Steam sterilization guidance | ISO 17665 |
| **Patient contact** | — | Biocompatibility (extended) | "Use of ISO 10993-1" | ISO 10993-1 through -18 |
| **Implantable** | `implant_flag == "Y"` | Biocompatibility + fatigue | ISO 10993 extended + fatigue | ISO 10993-6, ASTM F2077, F1717 |
| **Implantable** | `implant_flag == "Y"` | MRI safety | "Assessment of MRI Effects" | ASTM F2052, F2213, F2182 |
| **Life-sustaining** | `life_sustain == "Y"` | Enhanced clinical review | Life-sustaining device scrutiny | — |
| **Software-containing** | Tier 2 keywords | Software documentation | "Content of Premarket Submissions for Device Software Functions" | IEC 62304, IEC 82304-1 |
| **Software-containing** | Tier 2 keywords | Cybersecurity | "Cybersecurity in Medical Devices" | AAMI TIR57 |
| **AI/ML** | Tier 2 keywords | AI/ML guidance | "AI and ML in Software as a Medical Device" | — |
| **Wireless/connected** | Tier 2 keywords | Cybersecurity | Same cybersecurity guidance | AAMI TIR57, NIST CSF |
| **Wireless/connected** | Tier 2 keywords | EMC/wireless coexistence | "Radio Frequency Wireless Technology in Medical Devices" | IEC 60601-1-2, ANSI C63.27 |
| **Electrically powered** | Tier 2 keywords | Electrical safety | IEC 60601-1 guidance | IEC 60601-1, IEC 60601-1-2 |
| **Reusable** | `GUDID is_single_use == false` | Reprocessing validation | "Reprocessing Medical Devices in Health Care Settings" | AAMI TIR30, ST79 |
| **Single-use** | `GUDID is_single_use == true` | *(suppresses reprocessing unless third-party reprocessing per 21 CFR 820.3(p) applies)* | — | — |
| **MRI safety needed** | `GUDID mri_safety != null` | MRI safety testing | "Assessment of MRI Effects" | ASTM F2052, F2213, F2182 |
| **Latex-containing** | `GUDID is_labeled_as_nrl == true` | Latex labeling + biocompat | Latex labeling guidance | 21 CFR 801.437, ISO 10993 |
| **IVD devices** | review panel in IVD set | IVD-specific guidance | Various by analyte/method | CLSI EP05-EP17 |
| **Combination products** | Tier 2 keywords | Combination product guidance | "Classification of Products as Drugs and Devices" | 21 CFR 3 |
| **Human factors** | Class II + use risks | Usability engineering | "Applying Human Factors and Usability Engineering" | IEC 62366-1, HE75 |
| **Clinical data** | device-specific | Clinical study design | Varies by device | ISO 14155 |
| **3D Printing** | Tier 2 keywords | Additive manufacturing | "Technical Considerations for Additive Manufactured Medical Devices" | ASTM F3001, F2924 |
| **Animal-Derived** | Tier 2 keywords | BSE/TSE guidance | "Bovine Spongiform Encephalopathy/TSE" guidance | — |
| **Home Use** | Tier 2 keywords | Home use design | "Design Considerations for Devices Intended for Home Use" | IEC 62366-1 |
| **Pediatric** | Tier 2 keywords | Pediatric assessment | "Premarket Assessment of Pediatric Medical Devices" | — |

### Sterilization Method → Standard Mapping

| GUDID Sterilization Method | Primary Standard | Secondary Standards |
|---------------------------|-----------------|-------------------|
| Ethylene Oxide (EO) | ISO 11135 | AAMI TIR12, ISO 10993-7 (EO residuals) |
| Gamma Radiation | ISO 11137-1, -2 | AAMI TIR33 |
| E-Beam Radiation | ISO 11137-1, -3 | — |
| Steam / Moist Heat | ISO 17665 | — |
| Dry Heat | ISO 20857 | — |
| Hydrogen Peroxide | ISO 22441 | — |
| Aseptic Processing | ISO 13408 | — |

### Keyword Lists (Tier 2)

All keywords use word-boundary regex (`\b...\b`) and negation-awareness (skip if preceded by "not ", "non-", "without ").

| Category | Keywords |
|----------|----------|
| **Sterilization** | `sterile`, `sterilized`, `sterilization`, `aseptic`, `terminally sterilized`, `gamma irradiated`, `eo sterilized`, `ethylene oxide`, `e-beam sterilized`, `radiation sterilized`, `steam sterilized` |
| **Software** | `software`, `algorithm`, `mobile app`, `software app`, `firmware`, `samd`, `software as a medical device`, `digital health`, `software function` |
| **AI/ML** | `artificial intelligence`, `ai-enabled`, `ai-based`, `ai/ml`, `machine learning`, `deep learning`, `neural network`, `computer-aided detection`, `computer-aided diagnosis`, `cadx`, `cade` |
| **Wireless** | `wireless`, `bluetooth`, `wifi`, `wi-fi`, `network-connected`, `cloud-connected`, `internet of things`, `iot device`, `rf communication`, `rf wireless`, `radio frequency`, `cellular`, `zigbee`, `lora`, `nfc` |
| **USB** | `usb data`, `usb communication`, `usb port`, `usb connectivity`, `usb interface`, `usb connection` *(triggers cybersecurity only, not EMC)* |
| **Combination** | `combination product`, `drug-device`, `drug-eluting`, `drug-coated`, `biologic-device`, `antimicrobial agent`, `drug delivery device` |
| **Implantable** | `implant`, `implantable`, `permanent implant`, `indwelling`, `prosthesis`, `prosthetic`, `endoprosthesis` |
| **Reusable** | `reusable`, `reprocessing`, `reprocessed`, `multi-use`, `cleaning validation`, `disinfection` |
| **3D Printing** | `3d print`, `3d-printed`, `additive manufactur`, `additively manufactured`, `selective laser sintering`, `selective laser melting`, `electron beam melting`, `fused deposition`, `binder jetting` |
| **Animal-Derived** | `collagen`, `gelatin`, `bovine`, `porcine`, `animal-derived`, `animal tissue`, `equine`, `ovine`, `decellularized`, `xenograft`, `biologic matrix` |
| **Home Use** | `home use`, `over-the-counter`, `otc device`, `patient self-test`, `lay user`, `home monitoring`, `self-administered` |
| **Pediatric** | `pediatric`, `neonatal`, `infant`, `children`, `child`, `neonate`, `newborn`, `adolescent` |
| **Latex** | `latex`, `natural rubber`, `natural rubber latex` |
| **Electrical** | `battery-powered`, `battery powered`, `ac mains`, `rechargeable`, `electrically powered`, `mains-powered`, `lithium battery`, `electrical stimulation` |

### Specialty Keyword Categories (v5.21.0)

| Category | Keywords |
|----------|----------|
| **Cardiovascular** | `stent`, `catheter`, `guidewire`, `balloon catheter`, `oxygenator`, `heart valve`, `pacemaker`, `defibrillator`, `vascular graft`, `angioplasty` |
| **Orthopedic** | `arthroplasty`, `joint replacement`, `pedicle screw`, `spinal fusion`, `bone cement`, `fracture fixation`, `bone plate`, `orthopedic implant` |
| **Gastroenterology/Urology** | `endoscope`, `colonoscope`, `lithotripter`, `dialysis`, `hemodialysis`, `foley catheter`, `urinary catheter`, `ureteral stent` |
| **Dental** | `dental implant`, `endosseous implant`, `orthodontic`, `dental composite`, `intraoral scanner`, `dental handpiece`, `root canal`, `endodontic` |
| **ENT** | `hearing aid`, `cochlear implant`, `tympanostomy`, `otoscope`, `audiometer`, `laryngoscope`, `sleep apnea`, `bone-anchored hearing` |
| **Anesthesia/Respiratory** | `anesthesia`, `ventilator`, `cpap`, `bipap`, `capnograph`, `endotracheal tube`, `oxygen concentrator`, `breathing circuit` |
| **Neurological** | `neurostimulator`, `deep brain stimulation`, `eeg`, `tens`, `tms`, `vagus nerve stimulator`, `spinal cord stimulator`, `brain-computer interface` |
| **Ophthalmic** | `intraocular lens`, `contact lens`, `optical coherence tomography`, `fundus camera`, `glaucoma`, `phacoemulsification`, `tonometer`, `slit lamp` |
| **Surgery** | `electrosurgical`, `surgical stapler`, `suture`, `hemostatic`, `tissue adhesive`, `surgical mesh`, `surgical robot`, `laparoscopic` |
| **Physical Medicine** | `wheelchair`, `exoskeleton`, `prosthetic limb`, `muscle stimulator`, `continuous passive motion`, `rehabilitation device`, `orthotic` |
| **General Hospital** | `infusion pump`, `syringe pump`, `patient monitor`, `vital signs monitor`, `hospital bed`, `surgical glove`, `compression device`, `thermometer` |
| **Obstetrics/Gynecology** | `fetal monitor`, `cardiotocograph`, `intrauterine device`, `hysteroscope`, `colposcope`, `morcellator`, `breast implant`, `pelvic mesh` |
| **Radiology/Imaging** | `x-ray`, `computed tomography`, `ct scan`, `mri`, `magnetic resonance`, `ultrasound`, `mammography`, `fluoroscopy`, `dicom`, `pacs` |
| **IVD (expanded)** | `blood gas`, `point-of-care`, `hba1c`, `coagulation`, `next-generation sequencing`, `flow cytometry`, `immunoassay`, `molecular diagnostic`, `pcr` |

## Recognized Consensus Standards by Device Category

### Universal Standards (All Devices)
- **ISO 10993-1**: Biological evaluation framework
- **ISO 14971**: Risk management
- **IEC 62366-1**: Usability engineering (if applicable)
- **ISO 11607**: Packaging for terminally sterilized devices
- **ASTM F1980**: Accelerated aging for shelf life

### Wound Dressings (KGN, FRO, MGP)
| Standard | Purpose |
|----------|---------|
| ISO 10993-5 | Cytotoxicity |
| ISO 10993-10 | Sensitization and irritation |
| ASTM D1777 | Thickness measurement |
| ASTM D4032 | Stiffness / circular bend |
| EN 13726 | Test methods for wound dressings (multiple parts) |
| AATCC 100 | Antimicrobial assessment of textile materials |
| ASTM E2149 | Antimicrobial activity (dynamic contact) |
| ASTM F1980 | Accelerated aging |
| ISO 11607 | Packaging for terminally sterilized devices |

### CGM / Glucose Monitors (SBA, QBJ, QLG, QDK)
| Standard | Purpose |
|----------|---------|
| ISO 15197 | Blood glucose monitoring systems |
| CLSI POCT05 | Performance metrics for CGM systems |
| IEC 62304 | Software lifecycle |
| IEC 60601-1 | Electrical safety |
| IEC 60601-1-2 | EMC |
| ISO 10993-5, -10 | Biocompatibility |
| ASTM F2761 | iCGM special controls |

### Orthopedic Implants (OHT6)
| Standard | Purpose |
|----------|---------|
| ASTM F2077 | Intervertebral body fusion devices |
| ASTM F1717 | Spinal implant constructs |
| ASTM F2068 | Femoral stem fatigue |
| ISO 7206-4, -6 | Hip stem endurance testing |
| ISO 14879 | Tibial component testing |
| ASTM F1800 | Tibial tray fatigue (knee) |
| ISO 14242 | Hip joint wear simulator |
| ISO 14243 | Knee joint wear simulator |
| ASTM F382 | Metallic bone plate bending |
| ASTM F543 | Metallic bone screw specifications |
| ASTM F2033 | Hip endoprosthesis bearing surface |
| ASTM F136 | Ti-6Al-4V alloy |
| ASTM F1537 | Wrought CoCrMo alloy |
| ASTM F648 | UHMWPE specifications |
| ASTM F2565 | Highly cross-linked UHMWPE |
| ASTM F2026 | PEEK polymers for implants |
| ASTM F2129 | Corrosion susceptibility |
| ASTM F1875 | Fretting corrosion of modular joints |
| ASTM F3129 | Taper junction material loss |
| ASTM F1295 | Ti-6Al-7Nb alloy |
| ASTM F1160 | Fatigue testing of metallic implants |
| ASTM F451 | Acrylic bone cement |
| ISO 5833 | Acrylic resin bone cements |
| ASTM F1147 | Porous coating tensile/shear bond |
| ISO 13779 | HA coatings on implants |
| ASTM F3001, F2924 | Additive manufactured Ti alloys |
| ASTM F2052, F2213, F2182, F2119 | MRI safety testing |
| ASTM F2503 | MR Conditional labeling |

### Cardiovascular Devices (OHT2)
| Standard | Purpose |
|----------|---------|
| ISO 10993-4 | Hemocompatibility |
| ISO 5840-1, -2, -3 | Heart valve prostheses |
| ISO 25539-1, -2 | Endovascular devices |
| ASTM F2394 | Balloon-expandable stent securement |
| ASTM F2477 | Stent pulsatile fatigue |
| ASTM F2129 | Corrosion susceptibility |
| ISO 14708-2, -6 | Active cardiac implants (leads, defibrillators) |
| IEC 60601-2-31 | Cardiac pacemaker safety |
| IEC 60601-2-4 | Cardiac defibrillator safety |
| EN 45502-2-1, -2-2 | Active cardiac implant performance |
| ISO/TS 10974 | MRI safety for active implants |
| ANSI/AAMI VP20 | Vascular graft prostheses |
| IEC 60601-1 | Electrical safety |
| ASTM F2052, F2213, F2182 | MRI safety |

### Surgical Devices (OHT4)
| Standard | Purpose |
|----------|---------|
| IEC 60601-2-2 | Electrosurgical equipment safety |
| IEC 60601-2-18 | Endoscopic equipment |
| IEC 80601-2-77 | Robotic-assisted surgical equipment |
| AAMI TIR30 | Worst-case soil reprocessing testing |
| AAMI ST79 | Steam sterilization in healthcare |
| ASTM D1002 | Tissue adhesive bond strength (lap shear) |
| ISO 7740 | Surgical instruments — surgical scissors |
| USP <881> | Tensile strength of sutures |

### Anesthesia and Respiratory Devices (OHT1 — AN)
| Standard | Purpose |
|----------|---------|
| ISO 80601-2-13 | Anesthesia workstations |
| ISO 80601-2-12 | Critical care ventilators |
| ISO 80601-2-70 | Sleep apnea therapy equipment |
| ISO 80601-2-55 | Respiratory gas monitors |
| ISO 80601-2-61 | Pulse oximeter equipment |
| ISO 80601-2-80 | Ventilatory support equipment |
| IEC 60601-1-8 | Alarm systems |
| ISO 5356-1 | Conical connectors (breathing systems) |
| ISO 80369-6 | Small-bore connectors (neuraxial/intrathecal) |
| AAMI TIR30 | Reprocessing worst-case soil testing |

### Dental Devices (OHT1 — DE)
| Standard | Purpose |
|----------|---------|
| ISO 14801 | Dental implant fatigue testing |
| ISO 7405:2025 | Dental biocompatibility evaluation |
| ISO 6872 | Dental ceramic properties |
| ISO 4049 | Dental composite properties |
| ISO 22674 | Dental metallic materials |
| ISO 9917 | Dental cements |
| ISO 12836 | Intraoral scanner accuracy |
| IEC 60825-1 | Laser safety |
| IEC 60601-2-22 | Laser equipment safety |
| EN 1811 | Nickel release (NiTi wires) |
| ASTM F2129 | Corrosion susceptibility |

### ENT Devices (OHT1 — EN)
| Standard | Purpose |
|----------|---------|
| ANSI S3.22 | Hearing aid electroacoustic performance |
| ANSI S3.7 / IEC 60118-0 | Hearing aid measurements |
| IEC 60601-2-66 | Hearing instrument safety |
| IEC 60118-13 | Hearing aid electromagnetic immunity |
| ISO 14708-7 | Cochlear implant systems |
| ISO 7405 | Dental/oral biocompatibility (sleep apnea appliances) |

### Ophthalmic Devices (OHT1 — OP)
| Standard | Purpose |
|----------|---------|
| ISO 11979-2 | IOL optical properties |
| ISO 11979-3 | IOL mechanical properties (haptics) |
| ISO 11979-5 | IOL biocompatibility |
| ISO 18369-2 | Contact lens — physical optics and tolerances |
| ISO 18369-3 | Contact lens — measurement methods |
| ISO 18369-4 | Contact lens — physiochemical properties (Dk) |
| ISO 15798 | Ophthalmic viscosurgical devices |
| IEC 60825-1 | Laser safety |
| IEC 60601-2-22 | Ophthalmic laser safety |
| IEC 62220 | Digital X-ray imaging — DQE (ophthalmic imaging) |

### Neurological Devices (OHT5 — NE)
| Standard | Purpose |
|----------|---------|
| IEC 60601-2-10 | TENS/NMES nerve and muscle stimulators |
| IEC 60601-2-26 | EEG electroencephalographs |
| IEC 60601-2-40 | EMG electromyographs |
| ISO 14708-3 | Active implantable — neurostimulators |
| ASTM F2052, F2213, F2182, F2119 | MRI safety (implantable NE devices) |
| IEC 60601-1-8 | Alarm systems (seizure detection) |

### Physical Medicine Devices (OHT5 — PM)
| Standard | Purpose |
|----------|---------|
| ISO 7176-1 | Wheelchair static stability |
| ISO 7176-2 | Wheelchair dynamic stability (powered) |
| ISO 7176-3 | Wheelchair braking effectiveness |
| ISO 7176-4 | Wheelchair energy consumption/range |
| ISO 7176-6 | Wheelchair maximum speed/acceleration |
| ISO 7176-8 | Wheelchair static, impact, fatigue strengths |
| ISO 7176-10 | Wheelchair obstacle climbing |
| ISO 7176-14 | Wheelchair power and control systems |
| ISO 10328 | Lower-limb prosthesis structural testing |
| ISO 22675 | Prosthetic ankle-foot device testing |
| ISO 22523 | External limb prostheses requirements |
| IEC 60601-2-10 | TENS/NMES particular standard |
| IEC 60601-2-3 | Shortwave diathermy |
| IEC 60601-2-5 | Ultrasonic diathermy |
| IEC 62133 | Lithium battery safety |

### Gastroenterology/Urology Devices (OHT3 — GU)
| Standard | Purpose |
|----------|---------|
| IEC 60601-2-18 | Endoscopic equipment |
| IEC 60601-2-36 | Lithotripsy equipment |
| IEC 61846 | Lithotripsy acoustic output |
| ANSI/AAMI ST91:2021 | Flexible endoscope reprocessing |
| AAMI TIR30 | Worst-case soil testing |
| ISO 20696 | Washer-disinfectors for medical devices |
| ASTM F623 | Foley catheter requirements |
| ASTM F1828 | Ureteral stent requirements |
| ISO 10993-4 | Hemocompatibility (dialysis) |

### Obstetrics/Gynecology Devices (OHT3 — OB)
| Standard | Purpose |
|----------|---------|
| IEC 60601-2-37 | Ultrasonic diagnostic (fetal monitors) |
| IEC 60601-1-8 | Alarm systems |
| ISO 7439 | Intrauterine contraceptive devices |
| ISO 10993-6 | Implantation effects testing |
| AIUM ODS | Ultrasound output display standard |

### General Hospital Devices (OHT3 — HO)
| Standard | Purpose |
|----------|---------|
| IEC 60601-2-24 | Infusion pump safety and performance |
| IEC 60601-1-8 | Alarm systems |
| AAMI TIR101:2021 | Infusion device clinical alarm testing |
| ASTM D3578 | Nitrile examination glove specifications |
| ASTM D6319 | Nitrile examination glove (non-powder) |
| ASTM D5712 | Protein allergen testing (NRL gloves) |
| ASTM F1670, F1671 | Gown/drape barrier integrity |
| AAMI PB70 | Protective barrier materials classification |
| ISO 80369-6 | Small-bore connectors |

### Radiological Devices (OHT8 — RA)
| Standard | Purpose |
|----------|---------|
| IEC 60601-2-44 | CT equipment safety |
| IEC 60601-2-54 | Radiographic/fluoroscopic X-ray |
| IEC 60601-2-43 | Interventional X-ray |
| IEC 60601-2-33 | MRI equipment safety |
| IEC 60601-2-37 | Ultrasonic diagnostic equipment |
| IEC 60601-2-45 | Mammographic X-ray |
| IEC 60601-2-1 | Medical electron accelerators (LINAC) |
| IEC 62220-1 | Digital X-ray detector — DQE |
| IEC 62464-1 | MRI image quality parameters |
| IEC 62359 | Ultrasound acoustic output measurement |
| IEC 62083 | Radiation therapy treatment planning systems |
| NEMA XR 25 | CT dose check |
| NEMA XR 29 | CT dose optimization attributes |
| AIUM ODS | Ultrasound output display standard |
| 21 CFR 1020.30-33 | Diagnostic X-ray performance standards (mandatory) |

### IVD Devices (OHT7 — expanded)
| Standard | Purpose |
|----------|---------|
| **Cross-IVD (EP-series):** | |
| CLSI EP05 | Precision evaluation |
| CLSI EP06 | Linearity |
| CLSI EP07 | Interference testing |
| CLSI EP09 | Method comparison / bias estimation |
| CLSI EP10 | Sample carryover evaluation |
| CLSI EP12 | CLIA waiver qualitative test evaluation |
| CLSI EP15 | Verification of precision and bias |
| CLSI EP17 | Detection capability (LOB/LOD/LOQ) |
| CLSI EP25 | Reagent stability evaluation |
| CLSI EP28 | Reference intervals (replaces C28) |
| CLSI EP30 | Specimen type characterization |
| ISO 18113 | IVD labeling |
| ISO 17511 | Traceability of calibrators/controls |
| **Hematology (H-series):** | |
| CLSI H15 | Reference procedure for hemoglobin |
| CLSI H20 | Reference WBC differential count |
| CLSI H26 | Automated hematology analyzer validation |
| CLSI H44 | Blood reference intervals |
| CLSI H47 | One-stage PT and APTT testing |
| CLSI H54 | INR validation / local PT/INR calibration |
| **Microbiology (M-series):** | |
| CLSI M02 | Disk diffusion AST |
| CLSI M07 | Dilution AST methods |
| CLSI M23 | Standards development for AST |
| CLSI M27 | Antifungal susceptibility (yeasts) |
| CLSI M100 | AST performance standards (updated annually) |
| ISO 16256 | Reference method for MIC testing |
| **Molecular (MM-series):** | |
| CLSI MM03 | Molecular methods for infectious diseases |
| CLSI MM06 | Quantitative molecular methods |
| CLSI MM17 | Nucleic acid amplification V&V |
| **Pathology:** | |
| CLSI MM09 | Nucleic acid sequencing methods |
| CLSI MM14 | Genomic copy number microarrays |
| DICOM Supplement 145 | Whole slide imaging standard |
| **Toxicology:** | |
| SAMHSA Guidelines | Federal workplace drug testing cutoffs |
| CLSI C43 | GC-MS confirmation methods |
| CLSI C50 | Mass spectrometry clinical chemistry |
| ISO 15197 | Blood glucose monitoring (CGM-specific) |
| CLSI POCT05 | CGM performance metrics |

### Software / Digital Health
| Standard | Purpose |
|----------|---------|
| IEC 62304 | Medical device software lifecycle |
| IEC 82304-1 | Health software — general requirements |
| AAMI TIR57 | Principles for medical device security |
| NIST SP 800-53 | Security and privacy controls |
| ISO 14971 | Risk management (applied to software) |
| ANSI C63.27 | Wireless coexistence testing |

## Guidance-to-Testing Category Mapping

When a guidance document is found, map its requirements to specific testing categories:

| Guidance Requirement | Testing Category | Typical Tests |
|---------------------|-----------------|---------------|
| "biocompatibility evaluation" | Biocompatibility | ISO 10993-5 (cytotoxicity), -10 (sensitization/irritation), -11 (systemic toxicity) |
| "sterilization validation" | Sterilization | ISO 11135/11137 validation, sterility testing, EO residual testing |
| "shelf life" or "stability" | Shelf Life | ASTM F1980 (accelerated aging), real-time aging, package integrity |
| "software verification and validation" | Software V&V | Unit testing, integration testing, system testing per IEC 62304 |
| "electrical safety" | Electrical Safety | IEC 60601-1 compliance testing |
| "EMC" or "electromagnetic compatibility" | EMC | IEC 60601-1-2 emissions and immunity testing |
| "cybersecurity" | Cybersecurity | SBOM, threat modeling, penetration testing per AAMI TIR57 |
| "clinical performance" | Clinical | Prospective study, retrospective analysis, or literature review |
| "human factors" | Usability | Formative evaluation, summative (validation) testing per IEC 62366 |
| "performance testing" | Bench Testing | Device-type specific performance tests |
| "antimicrobial" or "antibacterial" | Antimicrobial | AATCC 100, ASTM E2149, zone of inhibition |
| "MRI safety" | MRI Compatibility | ASTM F2052 (magnetically induced displacement), F2213 (torque), F2182 (RF heating) |
| "reprocessing" | Reprocessing Validation | Cleaning validation, disinfection/sterilization efficacy |
| "risk management" | Risk Management | ISO 14971 risk analysis, FMEA |

## Offline Cache Structure

When `/fda:guidance --save` is used, guidance data is cached locally for offline reuse:

```
~/fda-510k-data/projects/{PROJECT_NAME}/guidance_cache/
  guidance_index.json       ← Index of cached guidance documents
  {product_code}/
    classification.json     ← openFDA classification response
    device_specific/
      {guidance_slug}.md    ← Extracted guidance content
    cross_cutting/
      biocompatibility.md
      sterilization.md
      software.md
      ...
    requirements_matrix.json ← Structured requirements mapping
    standards_list.json      ← Applicable consensus standards
```

### guidance_index.json Format

```json
{
  "product_code": "KGN",
  "device_name": "Dressing, Wound, Drug",
  "device_class": "2",
  "regulation_number": "878.4018",
  "cached_at": "2026-02-05T12:00:00Z",
  "device_specific_guidance": [
    {
      "title": "Guidance Title",
      "url": "https://...",
      "status": "final",
      "year": 2023,
      "cached_file": "device_specific/guidance-slug.md"
    }
  ],
  "cross_cutting_guidance": [
    {
      "topic": "Biocompatibility",
      "title": "Use of ISO 10993-1",
      "trigger": "all_devices",
      "cached_file": "cross_cutting/biocompatibility.md"
    }
  ],
  "standards": [
    {"standard": "ISO 10993-5", "purpose": "Cytotoxicity", "required": true},
    {"standard": "ASTM F1980", "purpose": "Accelerated aging", "required": true}
  ]
}
```
