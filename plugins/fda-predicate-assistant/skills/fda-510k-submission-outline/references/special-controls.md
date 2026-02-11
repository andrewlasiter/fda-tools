# Special Controls Reference

## What Are Special Controls?

Special controls are device-specific regulatory requirements beyond general controls (21 CFR 820 QMS, labeling, MDR) that apply to **Class II medical devices**. Every Class II device has special controls — they are the regulatory basis for why the device is Class II rather than Class III.

**Regulatory basis:** Section 513(a)(1)(B) of the FD&C Act — Class II devices require "special controls" to provide "reasonable assurance of safety and effectiveness."

## General Controls vs. Special Controls vs. Premarket Requirements

| Control Level | Applies To | Examples | Where Defined |
|--------------|-----------|---------|---------------|
| General controls | All devices (Class I, II, III) | QMS (21 CFR 820), MDR (21 CFR 803), registration/listing, labeling, premarket notification | FD&C Act §513(a)(1)(A) |
| Special controls | Class II devices | Performance standards, guidance documents, special labeling, postmarket surveillance | FD&C Act §513(a)(1)(B) |
| Premarket approval | Class III devices | PMA clinical evidence of safety and effectiveness | FD&C Act §513(a)(1)(C) |

## How to Identify Special Controls for a Device

### Step 1: Find the Regulation Number

From the product code (e.g., OVE), look up the regulation number:
- openFDA: `/device/classification?search=product_code:"OVE"` → `regulation_number: "888.3080"`
- Flat file: `foiaclass.txt` → product code row → regulation number column

### Step 2: Find the 21 CFR Section

The regulation number maps to a 21 CFR section:
- `888.3080` → 21 CFR 888.3080 (Intervertebral body fusion device)
- Within that CFR section, paragraph (b) typically lists the special controls

### Step 3: Read the Special Controls

Special controls are listed in the CFR regulation text and may include:
1. **Referenced guidance documents** — FDA guidance with specific testing expectations
2. **Performance standards** — Recognized consensus standards the device must meet
3. **Labeling requirements** — Specific information required on labeling
4. **Postmarket requirements** — Surveillance, registries, or reporting beyond standard MDR
5. **Restricted sale/distribution** — Prescription-only, specific practitioner requirements

### Step 4: Check for De Novo Special Controls

If the device was classified through De Novo, the special controls are listed in:
- The De Novo authorization order
- The resulting 21 CFR regulation text
- FDA's De Novo database

## Types of Special Controls

### Performance Standards
Device must meet specific performance criteria, often by conforming to recognized consensus standards.

**Examples:**
- IVD devices: Must meet analytical performance standards (accuracy, precision, specificity)
- Powered devices: Must meet IEC 60601-1 electrical safety
- Software devices: Must meet IEC 62304 software lifecycle requirements

### Guidance Documents
FDA guidance documents that describe testing expectations and submission content.

**Examples:**
- Product-specific guidance (e.g., "Class II Special Controls Guidance Document: Implantable Radiofrequency Transponder System for Patient Identification and Health Information")
- Device-type guidance (e.g., CGM guidance, wound dressing guidance)

### Special Labeling Requirements
Labeling must include specific information beyond general labeling requirements.

**Examples:**
- MRI compatibility information (conditional/unsafe/safe designation)
- Specific training requirements for device users
- Patient labeling with particular warnings
- Specific shelf life and storage condition statements

### Postmarket Surveillance
Requirements for ongoing monitoring after device marketing.

**Examples:**
- 522 postmarket surveillance orders for specific product codes
- Patient registries
- Annual reporting requirements (beyond standard MDUFA reporting)

### Restricted Sale/Distribution
Limitations on who can purchase, prescribe, or use the device.

**Examples:**
- Prescription device only (21 CFR 801.109)
- Use limited to specific clinical settings
- User training requirements

## Demonstrating Conformance in a 510(k)

### In a Traditional 510(k)
1. Identify all applicable special controls from the CFR regulation
2. For each special control, include a conformance statement or testing data
3. Reference specific standards tested against with version numbers
4. Include test reports or summary data as attachments
5. In the SE comparison, note how both subject and predicate address special controls

### In an Abbreviated 510(k)
The Abbreviated 510(k) pathway is specifically designed for devices where conformance to recognized standards and special controls provides the primary basis for SE determination:
1. Declarations of Conformity for each applicable standard
2. Summary test reports for each declaration
3. Conformance to any guidance-based special controls
4. Minimal additional data (only for aspects not covered by standards/guidance)

### In the eSTAR
- **Section 08 (Standards/Guidance)**: List all standards addressed as special controls
- **Section 15 (Performance Testing)**: Include test data demonstrating conformance
- **Section 09 (Labeling)**: Show that labeling meets any special labeling requirements

## Common Product Codes and Their Special Controls

| Product Code | Device | Key Special Controls |
|-------------|--------|---------------------|
| QAS | PACS / medical image management | IEC 62304, cybersecurity, interoperability |
| QMT | CADe/CADx software | IEC 62304, clinical performance, standalone software guidance |
| OVE | Intervertebral fusion device | Mechanical testing (ASTM F2077), biocompatibility, MRI safety |
| DQY | PTCA balloon catheter | Burst testing, compliance, fatigue, biocompatibility |
| KGN | Wound dressing | Fluid handling, biocompatibility, antimicrobial (if claimed) |
| QBJ | Glucose monitor | Analytical accuracy (ISO 15197), user labeling, alarm performance |
| HQF | Orthodontic bracket | Bond strength, biocompatibility, corrosion resistance |

## Mapping Special Controls to Testing Plan

Special controls directly inform the testing plan. For each special control:

```
Special Control → Required Test Category → Applicable Standard → Testing Plan Entry
```

| Special Control Type | Maps to Testing Plan |
|---------------------|---------------------|
| Performance standard | Specific bench tests per standard |
| Guidance document requirements | Device-type testing categories |
| Labeling requirement | Labeling verification (not bench testing) |
| Biocompatibility (ISO 10993) | ISO 10993 test battery per contact type/duration |
| Software (IEC 62304) | Software V&V documentation level |
| Electrical safety (IEC 60601) | Electrical safety + EMC testing |

Use `/fda:test-plan` to automatically map special controls to required tests for a given product code.
