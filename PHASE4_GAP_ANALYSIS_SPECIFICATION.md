# Phase 4: Automated Gap Analysis Specification

## Executive Summary

The **Automated Gap Analysis** feature (Phase 4) provides systematic comparison between a subject device (under development) and FDA-accepted predicate devices to identify specifications, features, and testing differences that require justification or additional data in the 510(k) submission.

The gap analysis operates as an intelligent assistant that:
- **Compares** subject device against multiple predicates across 50+ standardized comparison dimensions
- **Categorizes** gaps by severity (MAJOR/MODERATE/MINOR) and regulatory risk
- **Recommends** testing methodologies, standards, and evidence needed to address each gap
- **Tracks** gap resolution status throughout submission development
- **Generates** gap reports for regulatory team review and submission inclusion

**Key Deliverables:**
- Gap analysis CSV with 34 columns (predicate data + gap assessment)
- Gap report markdown with actionable remediation guidance
- Gap tracking spreadsheet for project management
- Integration with submission outline and pre-check scoring

---

## 1. Input Data Structure

### 1.1 Subject Device Data Sources

The gap analysis pulls subject device specifications from the project data ecosystem:

```
SUBJECT DEVICE SOURCES (priority order):
├── device_profile.json              [Primary: all device specs]
├── import_data.json                 [Secondary: eSTAR imported data]
├── drafts/draft_device-description.md  [Tertiary: detailed descriptions]
├── review.json                      [Predicate list & decisions]
├── se_comparison.md                 [Prior SE table data]
└── calculations/shelf_life_calc.json [Performance data]
```

**device_profile.json schema** (subject device):
```json
{
  "device_name": "string",
  "intended_use": "string",
  "indications_for_use": "string",
  "product_code": "string",
  "device_description": "string",
  "materials": ["string"],
  "sterilization_method": "string",
  "shelf_life_months": "number",
  "software_description": "string",
  "dimensions": {
    "length_mm": "number",
    "width_mm": "number",
    "height_mm": "number"
  },
  "weight_g": "number",
  "power_requirements": "string",
  "wireless_connectivity": "string",
  "biocompatibility_tested": "boolean",
  "standards_applied": ["string"],
  "performance_characteristics": {
    "specification_name": "value"
  },
  "features": ["string"],
  "extracted_sections": ["string"]
}
```

**review.json schema** (predicate list):
```json
{
  "predicates": {
    "K241335": {
      "device_name": "string",
      "applicant": "string",
      "decision_date": "string",
      "product_code": "string",
      "decision": "accepted|rejected",
      "confidence_score": "number",
      "rationale": "string"
    }
  }
}
```

### 1.2 Predicate Device Data Sources

Predicate specifications are sourced from multiple FDA databases:

```
PREDICATE DATA SOURCES (priority order):
├── Cached 510(k) PDF text           [Extracted sections]
├── openFDA API batch query          [K-number lookup]
├── FDA PMN database files           [pmn96cur.txt, pmnlstmn.txt]
├── PDF extraction cache             [~/fda-510k-data/extraction/]
└── Web search fallback              [Recent devices, missing data]
```

**Enriched Predicate Data** (from batchfetch --enrich):
```
Base 24 columns + Enrichment 29 columns:
├── Core predicate info (K-number, device name, company, dates)
├── Phase 1: Data integrity (MAUDE events, recall history, API quality)
├── Phase 2: Intelligence (clinical likelihood, standards detected, risk scoring)
└── Specialized fields (chain health, regulatory citations, guidance context)
```

### 1.3 Extraction Mapping: Device Profile → Gap Analysis

**Core specifications extracted:**

| Category | Field | Source | Data Type | Critical |
|----------|-------|--------|-----------|----------|
| **Identity** | Device Name | device_profile.json | String | Yes |
| | Product Code | device_profile.json | String | Yes |
| | Intended Use | device_profile.json | String | Yes |
| **Physical** | Materials | device_profile.json, draft | List[String] | Yes |
| | Dimensions (L×W×H) | device_profile.json | Float×3 | Conditional |
| | Weight | device_profile.json | Float | Conditional |
| | Sterilization Method | device_profile.json | String | Conditional |
| **Functional** | Power Requirements | device_profile.json | String | Conditional |
| | Wireless Connectivity | device_profile.json | String | Conditional |
| | Software | device_profile.json | String | Conditional |
| **Performance** | Key Specs (device-specific) | device_profile.json | Dict | Conditional |
| | Shelf Life | calculations/ | Integer (months) | Conditional |
| | Biocompatibility Testing | device_profile.json | Boolean | Conditional |
| **Regulatory** | Standards Applied | device_profile.json | List[String] | Yes |
| | Features List | device_profile.json | List[String] | No |

---

## 2. Gap Detection Logic

### 2.1 Comparison Framework

Gap analysis uses a **5-dimension comparison matrix** for each device specification:

```
┌─────────────────────────────────────────────────────────┐
│ SPECIFICATION (e.g., "Sterilization Method")            │
├─────────────────────────────────────────────────────────┤
│ Dimension 1: TEXTUAL EQUIVALENCE                        │
│   Subject: "Ethylene oxide"                             │
│   Predicate: "Ethylene oxide"                           │
│   → IDENTICAL                                            │
│                                                          │
│ Dimension 2: FEATURE PARITY                             │
│   Subject features: [wireless, cloud, FDA]              │
│   Predicate features: [cloud, FDA]                      │
│   → SUBJECT HAS ADDITIONAL FEATURES                     │
│                                                          │
│ Dimension 3: QUANTITATIVE RANGE                         │
│   Subject: 50-500 µL sample volume                      │
│   Predicate: 30-400 µL                                  │
│   → SUBJECT OUTSIDE PREDICATE RANGE (gap: wider range)  │
│                                                          │
│ Dimension 4: STANDARDS & TESTING                        │
│   Subject: ISO 10993-5, 10993-10                        │
│   Predicate: ISO 10993-5, 10993-10, 10993-11            │
│   → SUBJECT MISSING 10993-11 TESTING                    │
│                                                          │
│ Dimension 5: NOVEL CLAIMS                               │
│   Subject: "AI-assisted diagnosis" (new)                │
│   Predicate: N/A                                        │
│   → NOVEL FEATURE REQUIRES NEW EVIDENCE                 │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Gap Detection Rules

#### Rule 1: Text Comparison (Indications, Intended Use)

**Pattern Matching Logic:**

```python
def detect_text_gap(subject_text, predicate_text, field_type):
    """
    Detect textual differences in IFU, intended use, indications.
    Returns: (gap_detected, gap_type, confidence, explanation)
    """

    if not subject_text or not predicate_text:
        return (True, 'MISSING_DATA', 0.0, 'Predicate or subject data unavailable')

    # Normalize: lowercase, remove punctuation, extra whitespace
    subj_norm = normalize_text(subject_text)
    pred_norm = normalize_text(predicate_text)

    # Exact match
    if subj_norm == pred_norm:
        return (False, 'SAME', 1.0, 'Identical text')

    # Semantic similarity (Levenshtein ratio)
    similarity = textual_similarity(subj_norm, pred_norm)
    if similarity > 0.85:
        return (False, 'SIMILAR', similarity, f'{int(similarity*100)}% text overlap')

    # Keyword presence
    subject_keywords = extract_medical_keywords(subj_norm)
    predicate_keywords = extract_medical_keywords(pred_norm)

    missing_keywords = predicate_keywords - subject_keywords
    new_keywords = subject_keywords - predicate_keywords

    if new_keywords:
        return (True, 'NEW_INDICATION', 0.7, f'Subject adds: {new_keywords}')

    if missing_keywords:
        return (False, 'NARROWER_USE', 0.6, f'Subject removes: {missing_keywords}')

    # Fallback: text is different but we can't determine the impact
    return (True, 'DIFFERENT_IFU', 0.4, 'Textual differences require review')
```

**Medical Keyword Extraction:**
```
Extract and normalize condition names, anatomical sites,
disease states, measurement parameters, and use contexts.

Examples:
- "glucose monitoring in type 2 diabetes patients"
  → [glucose, monitoring, type-2-diabetes, patients]
- "intracranial pressure measurement"
  → [intracranial-pressure, measurement, monitoring]
- "wound dressing for chronic wounds"
  → [wound-dressing, chronic-wounds, wound-care]
```

---

#### Rule 2: Feature Parity (Presence/Absence)

**Detection Logic:**

```python
def detect_feature_gap(subject_features, predicate_features):
    """
    Detect when subject has features not in predicate (requires justification)
    or when subject is missing key features from predicate.
    """

    subject_set = set(normalize_feature(f) for f in subject_features)
    predicate_set = set(normalize_feature(f) for f in predicate_features)

    gaps = []

    # Subject ADDS features not in predicate (new claims)
    new_features = subject_set - predicate_set
    for feature in new_features:
        risk = assess_feature_risk(feature)  # HIGH/MEDIUM/LOW
        gaps.append({
            'type': 'NEW_FEATURE',
            'feature': feature,
            'risk_category': risk,
            'explanation': f'Subject adds {feature} — predicate does not have this',
            'testing_required': True
        })

    # Subject MISSING features present in predicate (potential weakness)
    missing_features = predicate_set - subject_set
    for feature in missing_features:
        gaps.append({
            'type': 'MISSING_FEATURE',
            'feature': feature,
            'explanation': f'Predicate has {feature} — subject does not (may need justification)',
            'severity': 'MINOR'  # Only minor unless marked critical
        })

    return gaps
```

**Feature Risk Assessment:**
```
HIGH RISK (new testing required):
- AI/ML algorithms
- Drug delivery systems (new drug)
- Wireless/connectivity features
- Cybersecurity features
- Novel materials
- Novel measurement principles

MEDIUM RISK (comparative testing required):
- Software updates
- Firmware changes
- Modified hardware interfaces
- New sterilization methods
- Extended shelf life claims

LOW RISK (documentation only):
- UI/UX improvements
- Display enhancements
- Packaging changes
- Updated labeling
- Cosmetic modifications
```

---

#### Rule 3: Quantitative Ranges (Size, Power, Performance)

**Detection Logic:**

```python
def detect_quantitative_gap(subject_value, predicate_value, spec_name, unit):
    """
    Detect when subject specification falls outside predicate range.
    Returns: (gap_detected, gap_type, severity, explanation)
    """

    # Parse numeric values with units
    subj_num = parse_numeric(subject_value, unit)
    pred_num = parse_numeric(predicate_value, unit)

    if not (subj_num and pred_num):
        return (True, 'UNPARSEABLE', 'MEDIUM', 'Cannot compare values')

    # Case 1: Single predicate value vs range
    if isinstance(pred_num, tuple):  # range (min, max)
        pred_min, pred_max = pred_num
        if subj_num < pred_min:
            return (True, 'SMALLER_THAN_PREDICATE', 'MEDIUM',
                   f'Subject {subj_num}{unit} < predicate min {pred_min}{unit}')
        elif subj_num > pred_max:
            return (True, 'LARGER_THAN_PREDICATE', 'MEDIUM',
                   f'Subject {subj_num}{unit} > predicate max {pred_max}{unit}')
        else:
            return (False, 'WITHIN_PREDICATE_RANGE', 'NONE', f'Subject within range')

    # Case 2: Both single values
    tolerance = calculate_tolerance(spec_name)  # e.g., ±10% for electrical
    if abs(subj_num - pred_num) <= tolerance:
        return (False, 'EQUIVALENT', 'NONE', f'Within {tolerance} tolerance')
    elif subj_num > pred_num * 1.5:
        return (True, 'SIGNIFICANTLY_HIGHER', 'LOW',
               f'Subject {subj_num}{unit} vs predicate {pred_num}{unit}')
    else:
        return (True, 'DIFFERENT_VALUE', 'LOW',
               f'Subject {subj_num}{unit} vs predicate {pred_num}{unit}')
```

**Tolerance Defaults by Category:**
```
Electrical (voltage, current):        ±5%
Mechanical (size, force):             ±10%
Performance (accuracy, response):     ±15%
Biocompatibility (test results):      Same methodology required
Shelf life (months):                  ±3 months
Temperature (storage):                ±2°C
```

---

#### Rule 4: Standards & Testing (Biocompatibility, Sterilization, etc.)

**Detection Logic:**

```python
def detect_standards_gap(subject_standards, predicate_standards, product_code):
    """
    Detect missing standards testing or deviations from predicate.
    Returns list of standard gaps with remediation guidance.
    """

    gaps = []
    required_standards = get_required_standards_for_product(product_code)

    # Parse standards lists (e.g., "ISO 10993-5, ISO 10993-10")
    subj_standards = parse_standards_list(subject_standards)
    pred_standards = parse_standards_list(predicate_standards)

    # MISSING STANDARDS: predicate did them, subject did not
    for standard in pred_standards:
        if standard not in subj_standards:
            criticality = get_standard_criticality(standard, product_code)
            gaps.append({
                'type': 'MISSING_STANDARD',
                'standard': standard,
                'criticality': criticality,  # CRITICAL/REQUIRED/OPTIONAL
                'explanation': f'{standard} performed in predicate but not subject',
                'remediation': f'Perform {standard} testing or provide justification'
            })

    # REQUIRED BUT MISSING: FDA-required standard not in subject
    for required in required_standards:
        if required not in subj_standards:
            gaps.append({
                'type': 'REQUIRED_STANDARD_MISSING',
                'standard': required,
                'criticality': 'CRITICAL',
                'explanation': f'{required} required by FDA but not performed',
                'remediation': f'Mandatory: perform {required} testing'
            })

    # DIFFERENT METHODOLOGY: same standard, different methodology
    # (e.g., different ISO 10993-5 extraction methodology)
    for standard in (subj_standards & pred_standards):
        if has_different_methodology(subject_standards, predicate_standards, standard):
            gaps.append({
                'type': 'DIFFERENT_TEST_METHODOLOGY',
                'standard': standard,
                'criticality': 'MEDIUM',
                'explanation': f'Different {standard} methodology than predicate',
                'remediation': 'Provide justification for methodology difference'
            })

    return gaps
```

**Standard Criticality Matrix** (by product type):

```
BIOCOMPATIBILITY (all implants & extended contact):
├── CRITICAL: ISO 10993-5 (cytotoxicity) — ALWAYS required
├── CRITICAL: ISO 10993-10 (sensitization) — ALWAYS required
├── REQUIRED: ISO 10993-1 (evaluation plan) — ALWAYS required
├── REQUIRED: ISO 10993-11 (systemic toxicity) — for permanent implants
├── REQUIRED: ISO 10993-23 (irritation) — for temporary implants
└── OPTIONAL: ISO 10993-4 (hemocompatibility) — blood-contacting devices

STERILIZATION:
├── CRITICAL: ISO 11135 (EO) or ISO 11137 (radiation) — ALWAYS required
├── REQUIRED: ISO 11135-1 for EO (validation)
├── REQUIRED: Shelf life stability data after sterilization
└── OPTIONAL: Alternative sterilization method validation

ELECTRICAL SAFETY (powered devices):
├── CRITICAL: IEC 60601-1 (general requirements)
├── REQUIRED: IEC 60601-2-X (device-specific part)
├── REQUIRED: IEC 60601-1-2 (EMC requirements)
└── OPTIONAL: IEC 60601-1-6 (usability)

SOFTWARE (devices with software):
├── CRITICAL: IEC 62304 (software lifecycle)
├── REQUIRED: SOC/SIL documentation (if safety-critical)
├── REQUIRED: Cybersecurity assessment (if networked/wireless)
└── OPTIONAL: Algorithm validation documentation
```

---

#### Rule 5: Novel Claims & New Characteristics

**Detection Logic:**

```python
def detect_novel_claims(subject_description, predicate_descriptions, product_code):
    """
    Detect when subject makes claims NOT made by ANY predicate.
    These require independent evidence.
    """

    gaps = []

    # Extract claim phrases from subject device
    subject_claims = extract_claims(subject_description)

    # Collect all predicate claims
    all_predicate_claims = set()
    for pred_desc in predicate_descriptions:
        all_predicate_claims.update(extract_claims(pred_desc))

    # Novel claims: in subject, not in any predicate
    novel_claims = subject_claims - all_predicate_claims

    for claim in novel_claims:
        risk = assess_claim_risk(claim)
        gaps.append({
            'type': 'NOVEL_CLAIM',
            'claim': claim,
            'risk_level': risk,  # HIGH/MEDIUM/LOW
            'explanation': f'Subject makes claim "{claim}" not found in predicates',
            'testing_required': True,
            'evidence_type': recommend_evidence_type(claim)
        })

    return gaps

def extract_claims(device_description):
    """
    Extract marketing/clinical claims using pattern matching.

    Patterns:
    - "enables X" / "allows X" / "provides X"
    - "reduces X" / "minimizes X"
    - "first X to..." / "only X that..."
    - "AI-assisted" / "machine learning"
    - "smartphone compatible" / "cloud-connected"
    - "real-time X"
    - "predictive" / "diagnostic"
    """
    claim_patterns = [
        r'(?:enables|allows|provides|improves|enhances|offers)\s+([^,.]+)',
        r'(?:reduces|minimizes|decreases|limits)\s+([^,.]+)',
        r'(?:first|only|novel|unique)\s+([^,.]+)',
        r'(AI-assisted|machine learning|predictive|diagnostic|real-time)',
        r'(?:compatible|connected)\s+(?:with\s+)?([^,.]+)',
    ]

    claims = set()
    for pattern in claim_patterns:
        matches = re.findall(pattern, device_description, re.IGNORECASE)
        claims.update(m.strip() for m in matches)

    return claims
```

---

### 2.3 Gap Severity Classification

Each gap is categorized by regulatory risk and remediation effort:

#### MAJOR Gaps
**Characteristics:**
- Requires new clinical or non-clinical testing
- Subject specification significantly different from predicate
- Predicate has no precedent for subject's approach
- New biocompatibility concerns or sterilization method

**Examples:**
- Novel drug formulation not tested in predicate
- Subject uses new material (e.g., graphene) not in predicate
- Subject claims real-time AI diagnosis (no predicate precedent)
- Subject extends intended use to new patient population
- Subject adds wireless connectivity (requires EMC testing)
- Shelf life extended beyond predicate validation

**Remediation:**
- Bench testing (material, performance)
- Biocompatibility testing (ISO 10993 suite)
- Clinical data (if safety/effectiveness claim affected)
- Standards validation (IEC, ISO)
- Risk analysis update

**FDA Risk:** Likely AI (Additional Information) request

---

#### MODERATE Gaps
**Characteristics:**
- Requires comparative testing or validation
- Subject similar to predicate but with meaningful differences
- Testing methodology established, but not yet performed
- Predicate provides partial precedent

**Examples:**
- Different sensor operating principle (but similar accuracy requirements)
- Modified sterilization method (requires validation per ISO 11135)
- Extended shelf life claim (accelerated aging study needed)
- Software modification (code review + testing)
- Material change within same family (e.g., titanium alloy → different alloy)
- Additional clinical endpoints vs. predicate

**Remediation:**
- Comparative performance testing
- Risk analysis (gap-specific)
- Standards compliance documentation
- Software/firmware validation
- Shelf life study (if extended)

**FDA Risk:** May trigger AI request; likely acceptable if well-documented

---

#### MINOR Gaps
**Characteristics:**
- Descriptive/documentation differences only
- No new testing required
- Predicate sets strong precedent
- Difference clearly immaterial to safety/effectiveness

**Examples:**
- Different device color or cosmetic design
- Updated user interface (no functional change)
- Slightly different dimensions (within 5% tolerance)
- Labeling/packaging changes
- Additional optional features (UI improvements)
- Updated software version (no algorithm change)

**Remediation:**
- Documentation update
- Cross-reference to predicate
- Labeling comparison table
- Risk assessment (low risk)

**FDA Risk:** Typically no impact; transparency recommended

---

### 2.4 Gap Severity Scoring Algorithm

```python
def calculate_gap_severity(gap_dict, product_code, predicate_risk_profile):
    """
    Calculate severity score (0-100) where:
    - 0-30: MINOR gaps
    - 31-70: MODERATE gaps
    - 71-100: MAJOR gaps

    Scoring factors (weighted):
    - Gap type risk coefficient (40%)
    - Testing burden estimate (30%)
    - FDA precedent strength (20%)
    - Predicate risk profile (10%)
    """

    # Base risk by gap type
    type_risk_map = {
        'NEW_CLAIM': 85,
        'NOVEL_FEATURE': 75,
        'REQUIRED_STANDARD_MISSING': 90,
        'NEW_MATERIAL': 70,
        'EXTENDED_SHELF_LIFE': 65,
        'DIFFERENT_TEST_METHODOLOGY': 45,
        'MISSING_STANDARD': 55,
        'DIFFERENT_IFU': 50,
        'QUANTITATIVE_MISMATCH': 35,
        'MISSING_FEATURE': 20,
    }

    base_score = type_risk_map.get(gap_dict['type'], 50)

    # Testing burden (0-40 points)
    testing_burden = estimate_testing_burden(gap_dict)
    testing_score = min(40, testing_burden * 4)

    # FDA precedent strength (-30 to +10 points)
    precedent_strength = search_predicate_chain_for_precedent(gap_dict, product_code)
    precedent_score = -30 if precedent_strength > 0.8 else (-10 if precedent_strength > 0.5 else 0)

    # Predicate risk profile adjustment
    predicate_adjustment = predicate_risk_profile.get('risk_penalty', 0)

    final_score = max(0, min(100, base_score + testing_score + precedent_score + predicate_adjustment))

    return {
        'severity_score': final_score,
        'severity_category': categorize_by_score(final_score),
        'components': {
            'base_risk': base_score,
            'testing_burden': testing_score,
            'precedent': precedent_score,
            'predicate_adjustment': predicate_adjustment
        }
    }
```

---

## 3. Comparison Categories & Dimensions

Gap analysis compares 50+ standardized dimensions organized by device type. Below is the **master taxonomy**:

### 3.1 Universal Dimensions (All Devices)

```
IDENTITY & REGULATORY
├── Device Name
├── Intended Use Statement
├── Indications for Use
├── Product Code
└── 510(k) Classification Pathway

BASIC PHYSICAL CHARACTERISTICS
├── Device Type/Configuration
├── Overall Dimensions (L×W×H)
├── Weight
├── Material Composition (BOM)
├── Color/Finish
└── Packaging

INTENDED USE CONTEXT
├── Patient Population
├── Anatomical Site (if applicable)
├── Contact Duration
├── Contact Type (patient/non-patient)
├── Labeling Language
└── User Skill Level

BIOCOMPATIBILITY & SAFETY
├── Biocompatibility Testing (ISO 10993 parts)
├── Sterilization Method & Standard
├── Shelf Life Duration
├── Storage Conditions
├── Safety Warnings/Contraindications
└── MRI Safety Classification (if applicable)

PERFORMANCE & EFFECTIVENESS
├── Primary Performance Parameter (device-specific)
├── Accuracy/Precision Metrics
├── Sensitivity/Specificity (if diagnostic)
├── Reportable Range (if measurement device)
├── Response Time
└── Durability/Reusability Claims

REGULATORY ARTIFACTS
├── Standards Applied (ISO, IEC, ASTM)
├── Clinical Data Type (if required)
├── Software/Firmware (IEC 62304 level)
├── Cybersecurity Documentation (if networked)
└── User Training Requirements
```

---

### 3.2 Device-Type Specific Dimensions

#### A. CGM / Continuous Glucose Monitoring (SBA, QBJ, QLG, QDK)

```
MEASUREMENT PRINCIPLE
├── Sensing Technology (electrochemical, optical, etc.)
├── Measurement Substrate (glucose oxidase, etc.)
├── Calibration Type (factory vs. user)
├── Calibration Frequency

ANALYTE & RANGE
├── Analyte (glucose in ISF, blood, etc.)
├── Reportable Range (mg/dL)
├── Accuracy Metric (MARD %)
├── Within ±20/20% Rate
├── Within ±30/30% Rate

SENSOR CHARACTERISTICS
├── Sensor Duration (days/months)
├── Warm-up Time
├── Sensor Placement Site
├── Sensor Adhesive Type
├── Number of Sensors per Pack

CONNECTIVITY & DISPLAY
├── Transmitter Battery Life
├── Transmitter Recharging Method
├── Receiver Type (dedicated vs. smartphone)
├── Wireless Protocol (Bluetooth, NFC, etc.)
├── Data Display Format
├── Cloud Connectivity
├── Data Sharing Features

INTEGRATED DEVICE FUNCTIONALITY
├── Automatic Insulin Dosing (AID) Compatibility
├── Alarm Thresholds (hypo/hyper)
├── Predictive Alert Capability
├── Noise Rejection (motion artifact)
├── Low Glucose Suspend (if applicable)

CLINICAL DATA
├── Study Design (randomized, open-label, etc.)
├── Number of Subjects
├── Study Duration
├── Comparison Method (reference, gold standard)
├── Primary Endpoint Results
├── Key Safety Events
```

---

#### B. Orthopedic Implants — Hip Arthroplasty (HCE, HCF, HDO, HDP, HEA, HEB)

```
DEVICE CONFIGURATION
├── Prosthesis Type (primary, revision, bipolar)
├── Fixation Method (cemented, uncemented, hybrid)
├── Bearing Surface Type (metal-on-metal, ceramic-on-ceramic, etc.)
├── Stem Design (straight, curved, anatomic)
├── Head Size (mm)
├── Neck Offset
├── Neck Angle

MATERIALS & SURFACE TREATMENT
├── Stem Material (alloy designation, e.g., Ti-6Al-4V)
├── Cup Material
├── Head Material
├── Bearing Surface Composition
├── Surface Treatment (porous coating, HA, 3D-printed)
├── Surface Roughness (Ra µm, if specified)

BIOCOMPATIBILITY & TESTING
├── ISO 10993 Parts Tested
├── Corrosion Testing (ASTM F2129, cyclic polarization)
├── Material Characterization Testing
├── Fretting Corrosion Testing
├── Long-term Stability

MECHANICAL TESTING
├── Fatigue Testing (ASTM F2068 hip, ISO 7206)
├── Fatigue Test Cycles Achieved
├── Torsional Rigidity
├── Bending Rigidity
├── Push-out/Push-pull Testing
├── Wear Testing (ISO 14242, cycles & wear rate)
├── Wear Debris Analysis

DESIGN FEATURES
├── Modular Components
├── Revision Capability
├── Size Range (mm)
├── Bearing Surface Clearance
├── Head Taper Design/Specifications

MRI SAFETY & IMAGING
├── MRI Conditional Status (per ASTM F2052)
├── Specific Absorption Rate (SAR) Limits
├── Artifact Size/Grade
├── Imaging Compatibility

CLINICAL DATA
├── Patient Population (age, BMI, activity level)
├── Follow-up Duration (minimum 2 years)
├── Implant Survival Rate (%)
├── Revision Rate
├── Complication Rates (infection, dislocation, etc.)
├── Patient-Reported Outcomes (HHS, OHS)
```

---

#### C. Cardiovascular — Drug-Eluting Stent (DXY, NIQ)

```
STENT DESIGN
├── Stent Type (open-cell, closed-cell)
├── Expansion Mechanism (balloon, self-expanding)
├── Strut Thickness (mm)
├── Strut Material
├── Strut Coating (if applicable)

DIMENSIONS & PERFORMANCE
├── Diameter Range (mm)
├── Length Range (mm)
├── Radial Strength (N/mm²)
├── Recoil (%)
├── Foreshortening (%)
├── Flexibility Score
├── Trackability

COATING & DRUG DELIVERY
├── Polymeric Coating Material
├── Drug Identity
├── Drug Dose (µg)
├── Elution Time (90%, 95%, 99%)
├── Elution Profile (zero-order, first-order)
├── In Vivo vs. In Vitro Data

BIOCOMPATIBILITY
├── ISO 10993 Parts Tested
├── Coating Biocompatibility
├── Thrombogenicity Assessment (ISO 10993-4)
├── Hemolysis Testing

FATIGUE & DURABILITY
├── Fatigue Testing (ASTM F2477 minimum ≥4×10^8 cycles)
├── Corrosion Testing (ASTM F2129)
├── Accelerated Aging Data

DELIVERY SYSTEM
├── Catheter Diameter (Fr)
├── Guidewire Compatibility
├── Deployment Mechanism
├── Crossing Profile

MRI SAFETY
├── MRI Conditional Classification
├── MRI Heating Assessment (per ASTM F2182)
├── Artifact Assessment

CLINICAL DATA
├── Study Name & Registry
├── Number of Patients & Lesions
├── Follow-up Duration
├── Target Lesion Revascularization (TLR) Rate
├── Major Adverse Cardiac Events (MACE) Rate
├── In-stent Restenosis Rate
├── Thrombosis Rate (acute, subacute, late)
├── Compare to Predicate Outcomes
```

---

#### D. Software as Medical Device (SaMD) — Imaging AI (QAS, QIH)

```
ALGORITHM & MODEL
├── Algorithm Type (DNN, CNN, GBM, ensemble)
├── Network Architecture (if DNN: layers, parameters)
├── Training Dataset Size (images/samples)
├── Training Dataset Source (internal, public, multi-institution)
├── Training Data Diversity (demographics, pathology)
├── Validation Dataset Source & Size
├── Test Dataset Source & Size

PERFORMANCE METRICS
├── Sensitivity (%)
├── Specificity (%)
├── Area Under Curve (AUC)
├── Positive Predictive Value (PPV)
├── Negative Predictive Value (NPV)
├── F1-Score / Dice Score (if segmentation)
├── Processing Time per Image (ms)

CLINICAL CONTEXT
├── Target Anatomy/Pathology
├── Compatible Input Modalities (CT, MRI, X-ray, ultrasound)
├── Clinical Setting (screening vs. diagnostic)
├── Intended User (radiologist vs. non-specialist)
├── Reader Study Type (standalone, reader-assist)
├── Reader Study Sample Size
├── Reader Study Pathology Prevalence

REGULATORY & STANDARDS
├── IEC 62304 Software Safety Classification (A, B, C)
├── Software Documentation Level
├── Version Control Procedures
├── Cybersecurity Assessment (if networked)
├── Cloud Infrastructure Security (if cloud-based)
├── PCCP (if using predicate labeling updates)

LABELING & PERFORMANCE
├── Labeling Claims (sensitivity, specificity values)
├── Performance Statement (standalone vs. assistant)
├── Limitations Statement
├── Required Disclaimers (e.g., not for autonomous diagnosis)
├── Intended Use Statement Precision

PREDICATE EQUIVALENCE
├── Predicate Algorithm Type Match
├── Predicate Performance Comparison
├── Predicate Dataset Comparison
├── Predicate Clinical Context Match
```

---

#### E. Wound Care — Foam Dressing (KGN)

```
PHYSICAL CHARACTERISTICS
├── Dressing Type/Category (foam, hydrocolloid, gel, etc.)
├── Layer Structure (single, dual, multi-layer)
├── Contact Layer Material & Properties
├── Absorbent Layer Material
├── Backing Material
├── Adhesive Type (silicone, acrylic, or non-adhesive)
├── Adhesive Border Width (if applicable)
├── Thickness (mm)

DIMENSIONS & CONFIGURATIONS
├── Available Sizes (cm × cm, count)
├── Surface Finish (perforated, non-perforated)
├── Contoured Configurations (heel, sacral)
├── Foam Density (kg/m³, if relevant)

FLUID HANDLING
├── Absorption Capacity (g/100 cm²)
├── Moisture Vapor Transmission Rate (MVTR) (g/m²/24h)
├── Exudate Retention (% by weight)
├── Strike-through Time (hours)
├── Fluid Handling Under Shear

BIOCOMPATIBILITY
├── ISO 10993 Parts Tested
├── Antimicrobial Agent (if applicable)
├── Antimicrobial Testing Method (AATCC 100, AAMI, etc.)
├── Antimicrobial Efficacy (log reduction)
├── Sensitization Risk Assessment

PERFORMANCE TESTING
├── Tensile Strength (N, before/after saturation)
├── Tear Resistance
├── Adhesion Strength (N/100 mm)
├── Thermal Stability
├── Mold/Mildew Growth Testing
├── Wound Fluid Compatibility

INTENDED USE CONTEXT
├── Wound Types (pressure ulcers, diabetic, venous, burns)
├── Wound Depth (shallow, deep, cavity-filling)
├── Exudate Level (low, moderate, high)
├── Frequency of Change (days per dressing)
├── Wear Duration (hours/days)

CLINICAL DATA
├── Study Type (observational, comparative)
├── Sample Size (N patients)
├── Wound Healing Rate (days to closure)
├── Infection Rate
├── Patient Comfort Scores
├── Adherence/Compliance Data
├── Cost-effectiveness Data (optional)

LABELING & SAFETY
├── Contraindications (e.g., third-degree burns)
├── Precautions (surgical sites, 3rd-degree)
├── Application Instructions
├── Patient Instruction Clarity
├── Symbols/Pictograms
```

---

### 3.3 Conditional Dimensions (Based on Device Features)

#### If Device is Reusable/Reprocessable:

```
REPROCESSING
├── Maximum Reprocessing Cycles (per labeling)
├── Cleaning Method (manual, ultrasonic, automated)
├── Cleaning Solution Specification
├── Drying Method
├── Sterilization Cycles Validated
├── Functional Testing Post-reprocessing
├── Material Degradation Assessment
├── Lumen/Channel Inspection
├── Reprocessing IFU Clarity
├── Quality Control Checkpoints
```

#### If Device is Powered or Uses Wireless:

```
POWER & CONNECTIVITY
├── Power Source Type (battery, mains, wireless charging)
├── Battery Chemistry (Li-ion, Ni-MH, etc.)
├── Battery Life (hours/days/years)
├── Battery Recharging Time
├── Charging Safety (thermal limits, overcharge protection)
├── Wireless Protocol (WiFi, Bluetooth, NFC, cellular)
├── Wireless Power Transmission (SAR compliance)
├── EMC Testing (IEC 60601-1-2)
├── Cybersecurity & Authentication
├── Over-the-Air Update Capability
├── Data Encryption
└── Cloud Integration Security
```

#### If Device Contains Software:

```
SOFTWARE & CYBERSECURITY
├── IEC 62304 Classification Level
├── Software Architecture
├── Version Control & Change Tracking
├── Verification & Validation Documentation
├── Code Review Procedures
├── Security Assessment & Penetration Testing
├── Vulnerability Disclosure Procedure
├── Patch/Update Management
├── Cybersecurity Training Documentation
└── Third-Party Component Management
```

#### If Shelf Life Claim >2 Years:

```
SHELF LIFE EXTENDED
├── Claimed Shelf Life Duration
├── Sterilization Compatibility (post-sterilization stability)
├── Real-Time Aging Data (years completed, years remaining)
├── Accelerated Aging Data (ASTM F1980 equivalent)
├── Q10 Value & Justification
├── Package Integrity Testing
├── Oxidative Stability (if relevant)
├── Microbiological Challenge Testing
├── Environmental Conditions (temperature, humidity)
└── Shelf Life Study Report Reference
```

---

## 4. Output Format Design

### 4.1 Gap Analysis CSV

**Purpose:** Machine-readable gap manifest for tracking and reporting

**Columns (34 total):**

```
| # | Column Name | Source | Type | Example |
|----|-------------|--------|------|---------|
| 1 | gap_id | Generated | String | GA-001-MAJOR-IFU |
| 2 | dimension | Taxonomy | String | "Intended Use Statement" |
| 3 | category | Taxonomy | String | "Identity & Regulatory" |
| 4 | subject_value | Project data | String | "Blood glucose monitoring for diabetic patients" |
| 5 | predicate_knumber | review.json | String | K241335 |
| 6 | predicate_device_name | openFDA | String | "Guardian CGM System" |
| 7 | predicate_value | Extract | String | "Blood glucose monitoring for type 1 & 2 diabetes" |
| 8 | gap_type | Logic | String | NEW_INDICATION |
| 9 | gap_detected | Logic | Boolean | TRUE |
| 10 | gap_description | Logic | String | "Subject adds type 2 diabetes indication (predicate is type 1 only)" |
| 11 | textual_difference | Logic | String | "Subject broader patient population" |
| 12 | severity_score | Scoring | Integer | 62 |
| 13 | severity_category | Scoring | String | MODERATE |
| 14 | regulatory_risk | Scoring | String | "May require AI for clinical evidence" |
| 15 | testing_required | Logic | Boolean | TRUE |
| 16 | testing_type | Recommendation | String | "Clinical validation study" |
| 17 | testing_standard | Reference | String | "None — new indication requires clinical data" |
| 18 | estimated_effort_hours | Estimation | Integer | 600 |
| 19 | precedent_search_result | Analysis | String | "Found 3 predicates with type 2 diabetes claims" |
| 20 | precedent_strength | Score | Float | 0.67 |
| 21 | remediation_recommendation | Guidance | String | "Clinical study minimum N=150 subjects with HbA1c ≥6.5%, 90-day minimum follow-up" |
| 22 | remediation_priority | Guidance | String | HIGH |
| 23 | fda_guidance_reference | Reference | String | "Draft Guidance for Continuous Glucose Monitoring (2019)" |
| 24 | status | Tracking | String | OPEN |
| 25 | owner | Tracking | String | "Clinical Affairs" |
| 26 | target_close_date | Tracking | Date | 2026-08-31 |
| 27 | closure_evidence | Tracking | String | "Clinical study XYZ results" |
| 28 | predicate_risk_flag | Assessment | Boolean | FALSE |
| 29 | predicate_health | Assessment | String | HEALTHY |
| 30 | alternative_predicate_found | Analysis | Boolean | FALSE |
| 31 | notes | Free-form | Text | "Type 2 diabetes is common; recommend clinical study with diverse population" |
| 32 | created_date | Metadata | Timestamp | 2026-02-13T10:30:00Z |
| 33 | last_updated | Metadata | Timestamp | 2026-02-13T10:30:00Z |
| 34 | predicate_comparison_url | Reference | String | "https://www.accessdata.fda.gov/cdrh_docs/pdf24/K241335.pdf" |
```

---

### 4.2 Gap Analysis Report (Markdown)

**Purpose:** Human-readable summary for regulatory team review

**Structure:**

```markdown
# Gap Analysis Report
**Project:** {PROJECT_NAME}
**Device:** {DEVICE_NAME} ({PRODUCT_CODE})
**Subject Device:** {DEVICE_DESCRIPTION}
**Predicates Analyzed:** {K_NUMBERS} ({COUNT})
**Generated:** {TIMESTAMP}
**Analysis Scope:** {DEVICE_TYPE_TEMPLATE} ({ROW_COUNT} dimensions)

---

## Executive Summary

- **Total Gaps Identified:** {N}
- **Major Gaps:** {N} (requires new testing)
- **Moderate Gaps:** {N} (requires comparative testing)
- **Minor Gaps:** {N} (documentation only)
- **Estimated Remediation Effort:** {TOTAL_HOURS} hours (~{WEEKS} weeks)
- **Critical Path Item:** {MOST_URGENT_GAP}

---

## Gap Summary by Severity

### MAJOR GAPS ({N})
[For each major gap]
- **{DIMENSION}**: {GAP_DESCRIPTION}
  - Severity: {SCORE}/100
  - Testing Required: {TESTING_TYPE}
  - Standard: {STANDARD}
  - Estimated Effort: {HOURS} hours
  - Priority: {PRIORITY}
  - Remediation: {SPECIFIC_GUIDANCE}
  - FDA Risk: {RISK_LEVEL}

### MODERATE GAPS ({N})
[Similar structure]

### MINOR GAPS ({N})
[Similar structure]

---

## Predicate Chain Analysis

### Predicate Selection Rationale
- **K241335** (Guardian CGM): 92% confidence — same product code, recent clearance, similar intended use
- **K191234** (FreeStyle Libre): 85% confidence — complementary technology, different sensor duration claim
- **K170567** (Medtronic): 78% confidence — older predicate, useful for baseline comparison

### Predicate Health Status
| K-number | Device | Health | Reason | Risk Flag |
|----------|--------|--------|--------|-----------|
| K241335 | Guardian | HEALTHY | No recalls, normal review time | None |
| K191234 | FreeStyle | HEALTHY | One field action (labeling), resolved | Minor |
| K170567 | Medtronic | CAUTION | Two recalls (firmware, sensor adhesive) | Medium |

### Predicate Chain Gaps
- Recall history found for 2 of 3 predicates (firmware, adhesive adhesion)
- Recommendation: Verify subject device does not repeat failure modes

---

## Detailed Gap Analysis by Category

### IDENTITY & REGULATORY

**Intended Use Statement**
- Status: MODERATE GAP
- Subject: "Continuous glucose monitoring for insulin-dependent diabetes"
- Predicate (K241335): "Glucose monitoring in diabetes mellitus"
- Difference: Subject narrows to insulin-dependent; predicates broader
- Severity: 45/100
- Remediation: Minor — narrower use is less stringent
- FDA Impact: None expected

**Indications for Use**
- Status: MAJOR GAP
- Gap Description: Subject adds type 2 diabetes without insulin
- Severity: 62/100
- Testing Required: Clinical validation study (N=150+, 90-day, HbA1c ≥6.5%)
- Standard: No specific FDA standard; follows Draft Guidance (2019)
- Estimated Effort: 600 hours (study design, execution, analysis)
- Remediation: Conduct multi-site clinical study with balanced demographics
- FDA Risk: HIGH — likely AI request without clinical data

---

[Continue for all gaps...]

---

## Remediation Roadmap

### Critical Path (0-8 weeks)
1. Design clinical study protocol (Week 1-2)
2. IRB submission & approval (Week 2-3)
3. Recruit subjects (Week 3-4)
4. Conduct study (ongoing through Week 8)

### Secondary Path (4-12 weeks)
1. Perform extended shelf life aging study (Week 4-8)
2. Complete EMC testing for wireless features (Week 6-8)
3. Finalize biocompatibility testing (Week 8-12)

### Documentation Path (0-4 weeks)
1. Comparative testing reports (Week 1-2)
2. Standards compliance documentation (Week 2-3)
3. Risk analysis updates (Week 3-4)

---

## Cost & Timeline Estimates

| Remediation Item | Effort (hrs) | Timeline | Cost Est. | Owner |
|---|---|---|---|---|
| Clinical Study | 600 | 8 weeks | $180K | Clinical Affairs |
| Shelf Life Study | 120 | 8 weeks | $40K | QA |
| EMC Testing | 80 | 6 weeks | $30K | Engineering |
| Biocompatibility | 200 | 10 weeks | $60K | QA |
| Documentation | 100 | 4 weeks | $15K | Regulatory |
| **TOTAL** | **1,100** | **10 weeks** | **$325K** | **Cross-functional** |

---

## Next Steps

1. **Week 1:** Circulate gap report to project team; assign owners to each remediation item
2. **Week 2:** Begin protocol development for clinical study
3. **Week 3:** Initiate biocompatibility and shelf life studies
4. **Week 4-10:** Execute remediation plan per roadmap
5. **Week 10:** Consolidate all remediation evidence into submission package
6. **Week 11:** Regulatory review & pre-submission meeting request (optional)
7. **Week 12:** Submission package finalization

---

## Regulatory Compliance Notes

- All recommendations align with FDA Draft Guidance (2019) and 21 CFR 807.87(b)
- Gap severity scores calculated per Phase 4 Specification v1.0
- Predicate chain validated via openFDA API (2026-02-13)
- No RTA-level deficiencies identified

---

*This report is AI-generated from FDA public data. Review with qualified regulatory professionals before submission.*
```

---

### 4.3 Gap Tracking Spreadsheet

**Purpose:** Project management / status tracking

**Columns:**
```
Gap ID | Dimension | Category | Status | Owner | Target Date | Evidence | % Complete | Notes
GA-001 | Intended Use | Identity | IN PROGRESS | Clinical Affairs | 2026-04-15 | Clinical Study Protocol | 25% | IRB submission in progress
GA-002 | Shelf Life | Performance | NOT STARTED | QA | 2026-06-30 | ASTM F1980 Study | 0% | Awaiting budget approval
GA-003 | Materials | Physical | RESOLVED | Engineering | 2026-02-13 | Material Cert (Titanium Grade 5) | 100% | Cross-referenced to predicate
...
```

---

## 5. Gap Analysis Algorithm (Unified Pseudocode)

```python
def perform_gap_analysis(
    subject_device_path,
    predicate_knumbers,
    product_code,
    output_dir,
    depth='standard'
):
    """
    Main orchestration function for gap analysis.

    Returns: (gap_csv, gap_report, gap_tracking_sheet)
    """

    # PHASE 1: DATA LOADING
    print("Loading subject device data...")
    subject = load_subject_device(subject_device_path)

    print("Fetching predicate devices...")
    predicates = fetch_predicates_from_fda(predicate_knumbers)

    print("Detecting device type template...")
    template = select_device_template(product_code)

    # PHASE 2: COMPARISON DIMENSION SELECTION
    print(f"Loading {template.name} template...")
    all_dimensions = load_template_dimensions(template)

    # Apply conditional dimensions
    if is_reusable_device(subject):
        all_dimensions.extend(REPROCESSING_DIMENSIONS)
    if has_software(subject):
        all_dimensions.extend(SOFTWARE_DIMENSIONS)
    if has_extended_shelf_life(subject):
        all_dimensions.extend(SHELF_LIFE_EXTENDED_DIMENSIONS)

    dimensions_to_compare = all_dimensions  # or filtered by --depth
    print(f"Comparing across {len(dimensions_to_compare)} dimensions")

    # PHASE 3: GAP DETECTION LOOP
    gaps = []
    for dimension in dimensions_to_compare:
        print(f"  Analyzing: {dimension['name']}...")

        # Extract subject value for this dimension
        subject_value = extract_dimension_value(subject, dimension)

        # Compare against each predicate
        for knumber, predicate in predicates.items():
            predicate_value = extract_dimension_value(predicate, dimension)

            # Multi-dimensional comparison
            gap_result = comprehensive_gap_detection(
                subject_value,
                predicate_value,
                dimension,
                product_code
            )

            if gap_result['gap_detected']:
                # Calculate severity
                severity = calculate_gap_severity(
                    gap_result,
                    product_code,
                    predicate['risk_profile']
                )

                # Recommend remediation
                remediation = recommend_remediation(
                    gap_result,
                    dimension,
                    product_code
                )

                # Assess precedent strength
                precedent = search_predicate_chain_for_precedent(
                    gap_result,
                    product_code
                )

                gap_record = {
                    'gap_id': generate_gap_id(),
                    'dimension': dimension['name'],
                    'category': dimension['category'],
                    'subject_value': subject_value,
                    'predicate_knumber': knumber,
                    'predicate_value': predicate_value,
                    'gap_type': gap_result['gap_type'],
                    'gap_description': gap_result['explanation'],
                    'severity_score': severity['score'],
                    'severity_category': severity['category'],
                    'testing_required': remediation['testing_required'],
                    'testing_type': remediation['type'],
                    'testing_standard': remediation['standard'],
                    'estimated_effort_hours': remediation['hours'],
                    'precedent_strength': precedent['strength'],
                    'remediation_recommendation': remediation['guidance'],
                    'fda_guidance_reference': remediation['guidance_ref'],
                    'status': 'OPEN',
                    'regulatory_risk': severity['fda_risk_level'],
                }

                gaps.append(gap_record)

    # PHASE 4: PREDICATE HEALTH CHECK
    print("Assessing predicate chain health...")
    for gap in gaps:
        knumber = gap['predicate_knumber']
        health = assess_predicate_health(knumber)
        gap['predicate_health'] = health['status']
        gap['predicate_risk_flag'] = health['has_risk']

    # PHASE 5: OUTPUT GENERATION
    print("Generating outputs...")

    # Gap CSV
    gap_csv_path = write_gap_csv(gaps, output_dir)

    # Gap Report (Markdown)
    gap_report_path = write_gap_report(
        gaps,
        subject,
        predicates,
        template,
        output_dir
    )

    # Gap Tracking Sheet
    gap_tracking_path = write_gap_tracking_sheet(gaps, output_dir)

    print(f"Gap analysis complete!")
    print(f"  - {len(gaps)} gaps identified")
    print(f"    MAJOR: {count_by_severity(gaps, 'MAJOR')}")
    print(f"    MODERATE: {count_by_severity(gaps, 'MODERATE')}")
    print(f"    MINOR: {count_by_severity(gaps, 'MINOR')}")
    print(f"  - CSV: {gap_csv_path}")
    print(f"  - Report: {gap_report_path}")
    print(f"  - Tracking: {gap_tracking_path}")

    return {
        'gap_csv': gap_csv_path,
        'gap_report': gap_report_path,
        'gap_tracking': gap_tracking_path,
        'total_gaps': len(gaps),
        'gaps': gaps
    }

def comprehensive_gap_detection(subject_val, predicate_val, dimension, product_code):
    """
    Execute all 5 comparison rules for a single dimension.
    Returns: {gap_detected, gap_type, explanation, confidence}
    """

    results = []

    # Rule 1: Text comparison
    if dimension['comparison_type'] == 'text':
        results.append(detect_text_gap(subject_val, predicate_val, dimension))

    # Rule 2: Feature parity
    if dimension['comparison_type'] == 'features':
        results.append(detect_feature_gap(subject_val, predicate_val))

    # Rule 3: Quantitative
    if dimension['comparison_type'] == 'numeric':
        results.append(detect_quantitative_gap(
            subject_val, predicate_val, dimension['name'], dimension['unit']
        ))

    # Rule 4: Standards
    if dimension['comparison_type'] == 'standards':
        results.append(detect_standards_gap(subject_val, predicate_val, product_code))

    # Rule 5: Novel claims
    if dimension.get('check_novelty', False):
        results.append(detect_novel_claims(subject_val, [predicate_val], product_code))

    # Synthesize results: if ANY rule detected gap, report gap
    gap_detected = any(r[0] for r in results if r)
    if gap_detected:
        # Use the result with highest confidence/risk
        best_result = max(results, key=lambda r: r[2] if len(r) > 2 else 0)
        return {
            'gap_detected': True,
            'gap_type': best_result[1],
            'explanation': best_result[3] if len(best_result) > 3 else '',
            'confidence': best_result[2] if len(best_result) > 2 else 0.5
        }
    else:
        return {
            'gap_detected': False,
            'gap_type': 'SAME',
            'explanation': 'No gap detected',
            'confidence': 1.0
        }
```

---

## 6. Integration Points

### 6.1 With Pre-Check Command

Gap severity scores feed into **Pre-Check review simulation**:
- MAJOR gaps → +15 points to RTA risk
- MODERATE gaps → +8 points to AI request likelihood
- MINOR gaps → +2 points to documentation robustness

### 6.2 With Compare-SE Command

Gap analysis output can be:
- **Input:** Reference to predicate comparison tables
- **Output:** Feed gap data into SE table's "Comparison" column with links to gap report

### 6.3 With Submission Outline

Gap tracking spreadsheet integrates into project management:
- Gap remediations listed as submission tasks
- Timeline estimates used for project scheduling
- Status updates tracked in submission milestone tracking

### 6.4 With Draft Command

Draft section generation can reference:
- Gap remediation recommendations (e.g., "Shelf Life: 3 years per gap analysis remediation GA-002")
- Test plan references from gap analysis

---

## 7. Examples & Use Cases

### Example 1: CGM Device with Type 2 Diabetes Expansion

**Subject Device:** Continuous glucose sensor for both type 1 and type 2 diabetes

**Predicate:** K241335 (Guardian CGM, type 1 diabetes only)

**Major Gap Detected:**
```
Gap ID: GA-001-MAJOR-INDICATION
Dimension: Indications for Use
Subject: "...type 1 and type 2 diabetes patients"
Predicate: "...type 1 diabetes patients"
Gap Type: NEW_INDICATION
Severity: 68/100 (MAJOR)
Testing Required: Clinical validation study
Standard: FDA Draft Guidance (2019)
Remediation: Multi-site study, N=150+, 90-day follow-up, HbA1c ≥6.5%
Effort: 600 hours (~8 weeks)
FDA Risk: HIGH — AI request expected without clinical data
```

**Resolution Path:**
1. Design clinical study protocol (2 weeks)
2. IRB approval (2 weeks)
3. Recruit subjects (2 weeks)
4. Run study (8 weeks parallel)
5. Analyze & report (2 weeks)
6. Incorporate into submission (1 week)

---

### Example 2: Orthopedic Implant with Extended Shelf Life

**Subject Device:** Hip prosthesis with 5-year shelf life claim

**Predicate:** K190123 (same hip, 3-year shelf life)

**Moderate Gap Detected:**
```
Gap ID: GA-012-MODERATE-SHELF-LIFE
Dimension: Shelf Life Duration
Subject: "5 years"
Predicate: "3 years"
Gap Type: EXTENDED_SHELF_LIFE
Severity: 52/100 (MODERATE)
Testing Required: Accelerated aging study (ASTM F1980)
Standard: ASTM F1980, F1471 (sterilization compatibility)
Remediation: Real-time + accelerated aging to 5 years, Q10=2.0 conservative
Effort: 200 hours (~8 weeks)
FDA Risk: MEDIUM — AI request likely; acceptable if well-documented
```

**Resolution Path:**
1. Design aging study protocol (1 week)
2. Initiate real-time + accelerated aging (ongoing)
3. Generate interim reports at 3-year mark (1 week)
4. Finalize 5-year data (8 weeks to real-time completion)

---

### Example 3: Software-Based Device with Cybersecurity as New Feature

**Subject Device:** Cloud-connected glucose meter (new wireless feature)

**Predicate:** K170456 (non-connected version)

**Major Gap Detected:**
```
Gap ID: GA-003-MAJOR-WIRELESS
Dimension: Wireless Connectivity (NEW DIMENSION)
Subject: "Bluetooth 5.0 + cloud API"
Predicate: "Standalone (no connectivity)"
Gap Type: NEW_FEATURE
Severity: 75/100 (MAJOR)
Testing Required: EMC testing, cybersecurity assessment, privacy review
Standard: IEC 60601-1-2, FDA Cybersecurity Guidance (2018)
Remediation: Full EMC suite + penetration testing + FDA cybersecurity questionnaire
Effort: 300 hours (~6 weeks)
FDA Risk: HIGH — new functionality requires comprehensive security documentation
```

---

## 8. Command Integration

### CLI Signature

```bash
/fda-predicate-assistant:gap-analysis \
  --project PROJECT_NAME \
  [--predicates K241335,K234567] \
  [--product-code CODE] \
  [--depth quick|standard|deep] \
  [--output-dir PATH] \
  [--full-auto]
```

### Output Files Generated

```
{PROJECT_DIR}/
├── gap_analysis.csv               [34 columns, all gaps]
├── gap_analysis_report.md         [Formatted report]
├── gap_tracking.xlsx              [Project management spreadsheet]
├── gap_analysis_metadata.json     [Analysis parameters & metadata]
└── remediation_roadmap.md         [Timeline & cost estimates]
```

---

## 9. Validation & Quality Assurance

### Pre-Analysis Checks

```python
def validate_analysis_inputs():
    """Validate before gap analysis execution."""

    # Subject device completeness
    assert device_profile['device_name'], "Device name required"
    assert device_profile['intended_use'], "Intended use required"
    assert device_profile['product_code'], "Product code required"

    # Predicate availability
    assert len(predicates) >= 1, "At least one predicate required"
    for knumber in predicates:
        assert fetch_predicate_success(knumber), f"Cannot fetch {knumber}"

    # Template availability
    assert template_exists(product_code), f"No template for {product_code}"
```

### Post-Analysis Validation

```python
def validate_gap_analysis_output(gaps):
    """Validate output quality."""

    # Check for duplicates
    gap_ids = [g['gap_id'] for g in gaps]
    assert len(gap_ids) == len(set(gap_ids)), "Duplicate gap IDs detected"

    # Severity score sanity checks
    for gap in gaps:
        assert 0 <= gap['severity_score'] <= 100, f"Invalid severity: {gap}"
        assert gap['severity_category'] in ['MAJOR', 'MODERATE', 'MINOR']

    # Remediation coverage
    major_gaps_with_remediation = [g for g in gaps
                                   if g['severity_category'] == 'MAJOR'
                                   and g['remediation_recommendation']]
    assert len(major_gaps_with_remediation) >= len([g for g in gaps
                                                      if g['severity_category'] == 'MAJOR'])

    print(f"Validation passed: {len(gaps)} gaps, all required fields present")
```

---

## 10. Future Enhancements

### Phase 4a: Automated Remediation Pathways

- Smart recommendation engine based on gap type
- Integration with testing lab databases
- Automated quotation requests for biocompatibility labs
- Project timeline generation with resource planning

### Phase 4b: Comparative Gap Analysis

- Multi-predicate gap synthesis (e.g., "3 of 4 predicates use EO sterilization")
- Predicate disagreement detection (when predicates contradict each other)
- Consensus recommendation generation

### Phase 4c: Machine Learning Gap Prediction

- Predict likely gaps based on device type + intended use
- Suggest additional predicates to reduce gap count
- Risk scoring refinement using FDA clearance history

---

## Appendix A: Device Template Mapping

```
Product Code → Template Selection:

CGM/Glucose: SBA, QBJ, QLG, QDK, NBW, CGA, LFR, SAF → CGM_TEMPLATE
Hip Arthroplasty: HCE, HCF, HDO, HDP, HEA, HEB → HIP_TEMPLATE
Knee Arthroplasty: HFK, HFG → KNEE_TEMPLATE
Cardiovascular: DXY, NIQ, DTB, DXA → CV_TEMPLATE
Wound Dressings: KGN, FRO, MGP → WOUND_TEMPLATE
Electrosurgical: GEI, GEX → ESURGICAL_TEMPLATE
Endoscopes: FDS, FDT, FGB → ENDOSCOPE_TEMPLATE
IVD - Chemistry: CZD, CRJ, CHN → IVD_CHEMISTRY_TEMPLATE
IVD - Hematology: JHR, JJX → IVD_HEMATOLOGY_TEMPLATE
Software/AI: QAS, QIH, QMT → SOFTWARE_TEMPLATE
[+30 more templates...]
Default: GENERIC_TEMPLATE (15 universal dimensions)
```

---

## Appendix B: FDA Guidance References

**Primary References for Gap Analysis Remediation:**

1. **510(k) Substantial Equivalence Guidance** (21 CFR 807.87)
2. **FDA Biocompatibility Guidance** (ISO 10993-1:2025 adoption)
3. **FDA Cybersecurity Guidance** (2018, updated 2023)
4. **Device-Specific Guidance** (by product code):
   - Draft Guidance for Continuous Glucose Monitoring (2019)
   - Guidance for Orthopedic Spinal Devices (2007)
   - Guidance for Cardiovascular Stents (2010)
5. **Standards References:**
   - ISO 10993 series (biocompatibility)
   - IEC 60601 series (electrical safety)
   - IEC 62304 (software lifecycle)
   - ASTM F series (materials & orthopedics)

---

**Specification Version:** 1.0 (Phase 4)
**Last Updated:** 2026-02-13
**Status:** DRAFT FOR IMPLEMENTATION

