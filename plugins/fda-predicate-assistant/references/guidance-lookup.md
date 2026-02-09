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
| **Single-use** | `GUDID is_single_use == true` | *(suppresses reprocessing)* | — | — |
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
| **Combination** | `combination product`, `drug-device`, `drug-eluting`, `drug-coated`, `biologic-device`, `antimicrobial agent`, `drug delivery device` |
| **Implantable** | `implant`, `implantable`, `permanent implant`, `indwelling`, `prosthesis`, `prosthetic`, `endoprosthesis` |
| **Reusable** | `reusable`, `reprocessing`, `reprocessed`, `multi-use`, `cleaning validation`, `disinfection` |
| **3D Printing** | `3d print`, `3d-printed`, `additive manufactur`, `additively manufactured`, `selective laser sintering`, `selective laser melting`, `electron beam melting`, `fused deposition`, `binder jetting` |
| **Animal-Derived** | `collagen`, `gelatin`, `bovine`, `porcine`, `animal-derived`, `animal tissue`, `equine`, `ovine`, `decellularized`, `xenograft`, `biologic matrix` |
| **Home Use** | `home use`, `over-the-counter`, `otc device`, `patient self-test`, `lay user`, `home monitoring`, `self-administered` |
| **Pediatric** | `pediatric`, `neonatal`, `infant`, `children`, `child`, `neonate`, `newborn`, `adolescent` |
| **Latex** | `latex`, `natural rubber`, `natural rubber latex` |
| **Electrical** | `battery-powered`, `battery powered`, `ac mains`, `rechargeable`, `electrically powered`, `mains-powered`, `lithium battery`, `electrical stimulation` |

## Recognized Consensus Standards by Device Category

### Universal Standards (All Devices)
- **ISO 10993-1**: Biological evaluation framework
- **ISO 14971**: Risk management
- **IEC 62366-1**: Usability engineering (if applicable)

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

### Orthopedic Implants
| Standard | Purpose |
|----------|---------|
| ASTM F2077 | Test methods for intervertebral body fusion devices |
| ASTM F1717 | Spinal implant constructs |
| ASTM F136 | Ti-6Al-4V alloy |
| ASTM F1295 | Ti-6Al-7Nb alloy |
| ASTM F2129 | Corrosion susceptibility |
| ASTM F1160 | Fatigue testing of metallic implants |
| ISO 12189 | Implants for surgery — mechanical testing |

### Cardiovascular Devices (DXY, DTB)
| Standard | Purpose |
|----------|---------|
| ISO 10993-4 | Hemocompatibility |
| ISO 5840 | Cardiovascular implants — cardiac valve prostheses |
| ISO 25539 | Endovascular devices |
| ASTM F2394 | Measuring securement of balloon-expandable stents |
| IEC 60601-1 | Electrical safety |
| ASTM F2052, F2213, F2182 | MRI safety |

### IVD Devices
| Standard | Purpose |
|----------|---------|
| CLSI EP05 | Precision evaluation |
| CLSI EP06 | Linearity |
| CLSI EP07 | Interference testing |
| CLSI EP12 | User protocol for evaluation of qualitative tests |
| CLSI EP15 | Verification of precision and estimation of bias |
| CLSI EP17 | Detection capability |
| CLSI C28 | Reference intervals |
| ISO 18113 | IVD labeling |

### Software / Digital Health
| Standard | Purpose |
|----------|---------|
| IEC 62304 | Medical device software lifecycle |
| IEC 82304-1 | Health software — general requirements |
| AAMI TIR57 | Principles for medical device security |
| NIST SP 800-53 | Security and privacy controls |
| ISO 14971 | Risk management (applied to software) |

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
