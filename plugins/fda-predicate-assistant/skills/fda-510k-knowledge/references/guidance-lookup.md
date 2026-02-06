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

These guidances apply based on device characteristics, regardless of product code. Determine applicability from openFDA classification data and the user's device description.

| Trigger Condition | Guidance Topic | Key Guidance Document | Key Standards |
|-------------------|---------------|----------------------|---------------|
| **All devices** | Biocompatibility | "Use of International Standard ISO 10993-1: Biological evaluation of medical devices" | ISO 10993-1, -5, -10, -11 |
| **All 510(k) devices** | SE determination | "The 510(k) Program: Evaluating Substantial Equivalence in Premarket Notifications" | — |
| **All 510(k) devices** | Labeling | "Medical Device Labeling — 510(k) Guidance" | 21 CFR 801 |
| **Class II devices** | Special controls | Product-code-specific special controls guidance | Varies by regulation |
| **Sterile devices** (description mentions "sterile", "sterilization", or product implies sterile) | Sterilization validation | "Submission and Review of Sterility Information in Premarket Notification (510(k)) Submissions" | ISO 11135 (EO), ISO 11137 (radiation), ISO 17665 (steam) |
| **Sterile devices** | Shelf life / aging | "Shelf Life of Medical Devices" | ASTM F1980 (accelerated aging), ASTM F2097 (flexible packaging evaluation) |
| **Devices with patient contact** | Biocompatibility (extended) | "Use of ISO 10993-1" | ISO 10993-1 through -18 as applicable |
| **Software-containing devices** (description mentions "software", "algorithm", "app", "firmware", "SaMD") | Software documentation | "Content of Premarket Submissions for Device Software Functions" | IEC 62304, IEC 82304-1 |
| **Software-containing devices** | Cybersecurity | "Cybersecurity in Medical Devices: Quality System Considerations and Content of Premarket Submissions" | AAMI TIR57 |
| **Wireless/connected devices** (description mentions "wireless", "bluetooth", "wifi", "connected", "IoT") | Cybersecurity (same as above) | Same cybersecurity guidance | AAMI TIR57, NIST CSF |
| **Wireless/connected devices** | EMC/wireless coexistence | "Radio Frequency Wireless Technology in Medical Devices" | IEC 60601-1-2, ANSI C63.27 |
| **Electrically powered devices** | Electrical safety | "Recognized Consensus Standards: IEC 60601-1" | IEC 60601-1, IEC 60601-1-2 |
| **Reusable devices** (description mentions "reusable", "reprocessing") | Reprocessing validation | "Reprocessing Medical Devices in Health Care Settings: Validation Methods and Labeling" | AAMI TIR30, AAMI ST79 |
| **Implantable devices** (description mentions "implant", "implantable") | Biocompatibility + fatigue | ISO 10993 extended + fatigue testing guidance | ISO 10993-6, ASTM F2077, ASTM F1717 |
| **Implantable devices** | MRI safety | "Assessment of the Effects of a Magnetic Resonance Diagnostic Device" | ASTM F2052, F2213, F2182 |
| **IVD devices** (review panel = clinical chemistry, microbiology, etc.) | IVD-specific guidance | Various IVD guidance documents by analyte/method | CLSI EP05, EP06, EP07, EP12, EP15 |
| **Combination products** (description mentions "drug", "biologic", "combination") | Combination product guidance | "Classification of Products as Drugs and Devices" | 21 CFR 3 |
| **Human factors required** (Class II with use-related risks) | Usability engineering | "Applying Human Factors and Usability Engineering to Medical Devices" | IEC 62366-1, ANSI/AAMI HE75 |
| **Devices with clinical data** | Clinical study design | "Clinical Investigations of Devices Indicated for the Treatment of Urinary Incontinence" (example — varies by device) | ISO 14155 |
| **Devices using AI/ML** (description mentions "AI", "machine learning", "deep learning") | AI/ML guidance | "Artificial Intelligence and Machine Learning in Software as a Medical Device" | — |

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
