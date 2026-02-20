# Expert Feedback Implementation Plan
## Based on Simulated Expert Panel Evaluation Results

**Generated:** 2026-02-14
**Based on:** 9 simulated expert evaluations (avg: 49.7/60, 82.8%)
**Goal:** Increase average score from 49.7/60 → 55/60 (92%)

---

## Executive Summary

Based on feedback from 9 diverse medical device regulatory experts, we've identified **13 improvements** prioritized by impact and effort. Implementing the top 5 improvements would address concerns raised by **89% of experts** and potentially increase adoption from 89% to 100%.

**Quick Wins (1-2 weeks):**
- Sterilization auto-triggers (affects 44% of experts)
- Shelf life packaging configuration (affects 11% of experts)

**High-Impact (1-2 months):**
- Device-type specific standards database (affects 78% of experts)
- Combination product auto-detection (affects 33% of experts)
- ISO 14971 risk management templates (affects 56% of experts)

**Strategic (3-6 months):**
- Clinical endpoint libraries
- AI/ML validation framework
- Device-specific terminology

---

## Priority 1: Quick Wins (1-2 Weeks)

### 1.1 Sterilization Method Auto-Triggers
**Requested by:** 44% of experts (4/9) - Chen, Torres, Park, Rodriguez
**Impact:** Medium (prevents missing critical standards)
**Effort:** Low (2-4 hours)
**Current State:** Plugin extracts sterilization methods but doesn't auto-add standards
**Target State:** Auto-populate standards when sterilization method detected

#### Implementation

**File to modify:** `plugins/fda-tools/commands/draft.md`

**Step 1: Add sterilization detection logic (Phase 0.5)**

In the "Step 0.5: Load All Project Data" section, add sterilization detection:

```markdown
### Sterilization Method Detection
Scan device_profile.json, source_device_text, and IFU for:
- **EO sterilization:** "ethylene oxide", "EO sterilized", "EtO"
- **Radiation:** "gamma radiation", "e-beam", "irradiation"
- **Steam:** "autoclave", "steam sterilization", "steam sterile"
- **Other:** "aseptic processing", "dry heat"

Store detected methods in device_profile.json:
```json
{
  "sterilization": {
    "methods": ["EO", "Radiation"],
    "standards_triggered": ["ISO 11135", "ISO 11137"]
  }
}
```
```

**Step 2: Auto-add to standards list**

In the standards lookup section, add:

```markdown
### Auto-Triggered Standards (Sterilization)

If sterilization methods detected in Step 0.5:
- **EO (Ethylene Oxide):**
  - ISO 11135:2014 - Sterilization of health-care products - Ethylene oxide
  - ISO 10993-7 - Ethylene oxide sterilization residuals

- **Radiation (Gamma/E-beam):**
  - ISO 11137-1:2006 - Sterilization of health care products - Radiation - Part 1: Requirements
  - ISO 11137-2:2013 - Sterilization of health care products - Radiation - Part 2: Establishing the sterilization dose

- **Steam:**
  - ISO 17665-1:2006 - Sterilization of health care products - Moist heat
  - ISO 11134 - Sterilization of health-care products - Steam (for reusable devices)

- **Aseptic Processing:**
  - ISO 13408-1 - Aseptic processing of health care products - General requirements
```

**Step 3: Add to Declaration of Conformity**

In DoC section generation, include auto-triggered sterilization standards in formal table.

#### Testing

Create test cases:
```bash
# Test 1: EO sterilization device (DQY catheter)
/fda-tools:draft --section device-description
# Verify: ISO 11135 appears in standards list

# Test 2: Radiation sterilization (orthopedic implant)
/fda-tools:draft --section device-description
# Verify: ISO 11137-1, ISO 11137-2 appear

# Test 3: Multiple methods (combination)
# Verify: All relevant standards appear
```

#### Success Criteria
- ✅ ISO 11135 auto-added when "EO" or "ethylene oxide" detected
- ✅ ISO 11137 auto-added when "radiation" or "gamma" detected
- ✅ ISO 17665 auto-added when "steam" or "autoclave" detected
- ✅ Standards appear in both standards_lookup.json AND DoC table
- ✅ No false positives (verify with 10 test devices)

#### Expert Validation
- Re-run evaluation with Chen (cardiovascular), Torres (orthopedic)
- Expected score increase: +1 point on Completeness dimension

---

### 1.2 Shelf Life Packaging Configuration
**Requested by:** 11% of experts (1/9) - Chen (cardiovascular)
**Impact:** Low (affects niche use case)
**Effort:** Low (1-2 hours)
**Current State:** AAF calculations don't account for packaging type
**Target State:** Add optional packaging input field

#### Implementation

**File to modify:** `plugins/fda-tools/commands/calc.md`

**Add to shelf life calculator:**

```markdown
### Step 3: Packaging Configuration (Optional)

Ask user:
> Does your device have moisture barrier packaging?
> - No (direct primary package only)
> - Yes - Single moisture barrier bag
> - Yes - Double moisture barrier bag
> - Yes - Foil pouch

**Packaging factors for AAF adjustment:**
- **No barrier:** AAF = standard Q10 calculation
- **Single barrier:** AAF multiplier = 0.9 (10% margin)
- **Double barrier:** AAF multiplier = 0.85 (15% margin)
- **Foil pouch:** AAF multiplier = 0.8 (20% margin)

**Adjusted AAF Formula:**
```
AAF_adjusted = AAF_base × packaging_multiplier
Real-time aging = AAF_adjusted × Accelerated_time
```

**Example:**
- Base AAF (Q10=2, 55°C) = 8
- Double moisture barrier multiplier = 0.85
- Adjusted AAF = 8 × 0.85 = 6.8
- 52 weeks accelerated = 6.8 × 52 = 353.6 weeks real-time (6.8 years)
```

#### Testing
```bash
# Test with and without packaging
/fda-tools:calc --shelf-life --target-years 5 --packaging double-barrier
# Verify: Conservative AAF used
```

#### Success Criteria
- ✅ Packaging option available in calculator
- ✅ AAF adjusted conservatively for moisture barriers
- ✅ Results documented in calculations output

---

## Priority 2: High-Impact Improvements (1-2 Months)

### 2.1 Device-Type Specific Standards Database
**Requested by:** 78% of experts (7/9) - ALL EXCEPT Torres, Weber
**Impact:** CRITICAL (highest-requested improvement)
**Effort:** High (40-60 hours across multiple product codes)
**Current State:** Generic standards only (ISO 10993, IEC 60601-1, etc.)
**Target State:** Device-type specific standards auto-triggered by product code

#### Implementation Strategy

**Phase 1: Robotics Standards (Rodriguez - 14y exp)**

**File to create:** `plugins/fda-tools/lib/standards_robotics.json`

```json
{
  "product_codes": ["QBH", "OZO", "IYE"],
  "device_types": ["Surgical Robotic System", "Robot-Assisted Surgery"],
  "keywords": ["robotic", "robot-assisted", "surgical navigation"],
  "standards": [
    {
      "number": "ISO 13482:2014",
      "title": "Robots and robotic devices - Safety requirements for personal care robots",
      "category": "Robotics Safety",
      "applicability": "All surgical robots",
      "priority": "Required"
    },
    {
      "number": "IEC 80601-2-77:2019",
      "title": "Medical electrical equipment - Part 2-77: Particular requirements for robotically assisted surgical equipment",
      "category": "Electrical Safety",
      "applicability": "Electrically powered surgical robots",
      "priority": "Required"
    },
    {
      "number": "IEC 62304:2006/AMD1:2015",
      "title": "Medical device software - Software life cycle processes",
      "category": "Software",
      "applicability": "All robotic systems (software-driven)",
      "priority": "Required"
    },
    {
      "number": "IEC 62366-1:2015",
      "title": "Medical devices - Application of usability engineering to medical devices",
      "category": "Human Factors",
      "applicability": "Complex user interfaces",
      "priority": "Required"
    },
    {
      "number": "ISO 14971:2019",
      "title": "Medical devices - Application of risk management to medical devices",
      "category": "Risk Management",
      "applicability": "All devices",
      "priority": "Required"
    },
    {
      "number": "IEC 60601-1-2:2014",
      "title": "Medical electrical equipment - Part 1-2: General requirements - Electromagnetic compatibility",
      "category": "EMC",
      "applicability": "All electrically powered robots",
      "priority": "Required"
    }
  ]
}
```

**Phase 2: Neurostimulation Standards (Anderson - 6y exp)**

**File to create:** `plugins/fda-tools/lib/standards_neurostim.json`

```json
{
  "product_codes": ["GZB", "LYP", "MWN", "OLO"],
  "device_types": ["Neurostimulator", "Spinal Cord Stimulator", "Deep Brain Stimulator"],
  "keywords": ["neurostimulation", "electrical stimulation", "neuromodulation"],
  "standards": [
    {
      "number": "IEC 60601-2-40:2016",
      "title": "Medical electrical equipment - Part 2-40: Particular requirements for basic safety and essential performance of electromyography and evoked response equipment",
      "category": "Neurostimulation Safety",
      "applicability": "All neurostimulation devices",
      "priority": "Required"
    },
    {
      "number": "IEC 60601-2-10:2012",
      "title": "Medical electrical equipment - Part 2-10: Particular requirements for nerve and muscle stimulators",
      "category": "Electrical Safety",
      "applicability": "Peripheral nerve stimulators",
      "priority": "Required"
    },
    {
      "number": "ISO 14708-3:2017",
      "title": "Implants for surgery - Active implantable medical devices - Part 3: Implantable neurostimulators",
      "category": "Implantable Device Safety",
      "applicability": "Implanted neurostimulators",
      "priority": "Required"
    },
    {
      "number": "IEC 60601-1:2005/AMD1:2012",
      "title": "Medical electrical equipment - Part 1: General requirements for basic safety and essential performance",
      "category": "Electrical Safety",
      "applicability": "All electrically powered devices",
      "priority": "Required"
    },
    {
      "number": "ISO 10993-1:2018",
      "title": "Biological evaluation of medical devices - Part 1: Evaluation and testing within a risk management process",
      "category": "Biocompatibility",
      "applicability": "All implanted components",
      "priority": "Required"
    },
    {
      "number": "IEC 60601-2-33:2010/AMD1:2013",
      "title": "Medical electrical equipment - Part 2-33: Particular requirements for MRI equipment",
      "category": "MRI Safety",
      "applicability": "MRI-conditional neurostimulators",
      "priority": "Conditional"
    }
  ]
}
```

**Phase 3: IVD Analytical Validation (Park - 9y exp)**

**File to create:** `plugins/fda-tools/lib/standards_ivd.json`

```json
{
  "product_codes": ["LCX", "JJE", "OBP"],
  "device_types": ["In Vitro Diagnostic", "Point-of-Care Test", "Clinical Chemistry"],
  "keywords": ["IVD", "diagnostic test", "assay", "analytical"],
  "standards": [
    {
      "number": "CLSI EP05-A3",
      "title": "Evaluation of Precision of Quantitative Measurement Procedures",
      "category": "Analytical Validation",
      "applicability": "All quantitative IVDs",
      "priority": "Required"
    },
    {
      "number": "CLSI EP06-A",
      "title": "Evaluation of Linearity of Quantitative Measurement Procedures",
      "category": "Analytical Validation",
      "applicability": "Quantitative assays",
      "priority": "Required"
    },
    {
      "number": "CLSI EP07-A2",
      "title": "Interference Testing in Clinical Chemistry",
      "category": "Analytical Validation",
      "applicability": "Clinical chemistry assays",
      "priority": "Required"
    },
    {
      "number": "CLSI EP09-A3",
      "title": "Measurement Procedure Comparison and Bias Estimation Using Patient Samples",
      "category": "Method Comparison",
      "applicability": "All IVDs (vs. predicate comparison)",
      "priority": "Required"
    },
    {
      "number": "CLSI EP12-A2",
      "title": "User Protocol for Evaluation of Qualitative Test Performance",
      "category": "Analytical Validation",
      "applicability": "Qualitative IVDs (positive/negative)",
      "priority": "Conditional"
    },
    {
      "number": "CLSI EP17-A2",
      "title": "Evaluation of Detection Capability for Clinical Laboratory Measurement Procedures",
      "category": "Limit of Detection",
      "applicability": "All quantitative IVDs",
      "priority": "Required"
    },
    {
      "number": "ISO 15189:2012",
      "title": "Medical laboratories - Requirements for quality and competence",
      "category": "Quality Management",
      "applicability": "Laboratory-developed tests",
      "priority": "Conditional"
    }
  ]
}
```

**Phase 4: SaMD/AI-ML Standards (Kim - 10y exp)**

**File to create:** `plugins/fda-tools/lib/standards_samd.json`

```json
{
  "product_codes": ["QIH", "QJT", "QBG"],
  "device_types": ["Software as Medical Device", "AI/ML Diagnostic", "Clinical Decision Support"],
  "keywords": ["SaMD", "artificial intelligence", "machine learning", "algorithm"],
  "standards": [
    {
      "number": "IEC 62304:2006/AMD1:2015",
      "title": "Medical device software - Software life cycle processes",
      "category": "Software Development",
      "applicability": "All SaMD",
      "priority": "Required"
    },
    {
      "number": "IEC 82304-1:2016",
      "title": "Health software - Part 1: General requirements for product safety",
      "category": "Software Safety",
      "applicability": "Standalone health software",
      "priority": "Required"
    },
    {
      "number": "ISO 13485:2016",
      "title": "Medical devices - Quality management systems",
      "category": "QMS",
      "applicability": "All medical device software",
      "priority": "Required"
    },
    {
      "number": "ISO 14971:2019",
      "title": "Medical devices - Application of risk management to medical devices",
      "category": "Risk Management",
      "applicability": "All devices",
      "priority": "Required"
    },
    {
      "number": "IEC 62366-1:2015",
      "title": "Medical devices - Application of usability engineering to medical devices",
      "category": "Human Factors",
      "applicability": "User-facing software",
      "priority": "Required"
    },
    {
      "number": "ISO/IEC 25010:2011",
      "title": "Systems and software engineering - Systems and software Quality Requirements and Evaluation (SQuaRE)",
      "category": "Software Quality",
      "applicability": "All software",
      "priority": "Recommended"
    }
  ],
  "ai_ml_specific": [
    {
      "number": "ISO/IEC TR 24028:2020",
      "title": "Information technology - Artificial intelligence - Overview of trustworthiness in artificial intelligence",
      "category": "AI/ML Trust",
      "applicability": "AI/ML algorithms",
      "priority": "Recommended"
    },
    {
      "number": "ISO/IEC 23894:2023",
      "title": "Information technology - Artificial intelligence - Guidance on risk management",
      "category": "AI Risk",
      "applicability": "AI/ML systems",
      "priority": "Recommended"
    }
  ],
  "fda_guidance": [
    {
      "title": "Clinical Decision Support Software (2022)",
      "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software",
      "applicability": "CDS software"
    },
    {
      "title": "Artificial Intelligence/Machine Learning (AI/ML)-Based Software as a Medical Device (SaMD) Action Plan",
      "url": "https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-and-machine-learning-aiml-enabled-medical-devices",
      "applicability": "AI/ML SaMD"
    }
  ]
}
```

**Integration: Modify draft.md to load device-type standards**

```markdown
### Step 0.6: Load Device-Type Specific Standards

Based on product code and keywords:

1. **Check product code match:**
   - If product_code in standards_robotics.json → load robotics standards
   - If product_code in standards_neurostim.json → load neurostim standards
   - If product_code in standards_ivd.json → load IVD standards
   - If product_code in standards_samd.json → load SaMD standards

2. **Check keyword match:**
   Scan device name, intended use, and description for:
   - "robotic", "robot-assisted" → robotics standards
   - "neurostimulation", "electrical stimulation" → neurostim standards
   - "IVD", "diagnostic test", "assay" → IVD standards
   - "SaMD", "AI", "machine learning" → SaMD standards

3. **Merge with existing standards:**
   - Add device-type standards to standards_lookup.json
   - Mark as "Auto-detected (Device-Type Specific)"
   - Preserve any manually added standards

4. **Priority handling:**
   - Required: MUST be in submission
   - Conditional: Include if applicable (e.g., MRI safety only if MRI-conditional)
   - Recommended: Best practice but not mandatory
```

#### Testing Plan
```bash
# Test 1: Robotics (QBH)
/fda-tools:standards --product-code QBH
# Expected: ISO 13482, IEC 80601-2-77, IEC 62304

# Test 2: Neurostim (GZB)
/fda-tools:standards --product-code GZB
# Expected: IEC 60601-2-40, IEC 60601-2-10, ISO 14708-3

# Test 3: IVD (LCX)
/fda-tools:standards --product-code LCX
# Expected: CLSI EP05, EP06, EP07, EP09, EP17

# Test 4: SaMD (QIH)
/fda-tools:standards --product-code QIH
# Expected: IEC 62304, IEC 82304-1, ISO/IEC TR 24028
```

#### Success Criteria
- ✅ 4 device-type standards libraries created (Robotics, Neurostim, IVD, SaMD)
- ✅ Auto-detection by product code AND keywords
- ✅ Standards appear in standards_lookup.json
- ✅ DoC table includes device-specific standards
- ✅ Re-run Rodriguez evaluation: Expected +2 points on Completeness
- ✅ Re-run Anderson evaluation: Expected +2 points on Completeness
- ✅ Re-run Park evaluation: Expected +2 points on Completeness
- ✅ Re-run Kim evaluation: Expected +1 point on Completeness

#### Estimated Impact
- **Before:** Completeness avg = 7.7/10
- **After:** Completeness avg = 8.5/10 (+0.8 points)
- **Overall score increase:** 49.7 → 50.5/60

---

### 2.2 Combination Product Auto-Detection
**Requested by:** 33% of experts (3/9) - Chen, Sharma, Kim
**Impact:** CRITICAL (for 30% of market - combo products)
**Effort:** Medium (15-20 hours)
**Current State:** No detection of drug/biologic components
**Target State:** Auto-flag combination products, trigger RHO pathways

#### Implementation

**File to create:** `plugins/fda-tools/lib/combination_product_detector.py`

```python
"""
Combination Product Detection Module
Identifies device-drug and device-biologic combinations
Triggers RHO consultation pathways per 21 CFR 3.2(e)
"""

import re
from typing import Dict, List, Optional

class CombinationProductDetector:

    DRUG_KEYWORDS = [
        # Drug-eluting/coated
        "drug-eluting", "drug-coated", "drug eluting", "drug coated",
        "paclitaxel", "sirolimus", "everolimus", "zotarolimus",
        "antibiotic", "antimicrobial", "antiseptic",
        "heparin-coated", "heparin coated",

        # Specific drugs
        "silver sulfadiazine", "minocycline", "rifampin",
        "vancomycin", "gentamicin",

        # Drug delivery
        "drug reservoir", "drug release", "controlled release",
        "sustained release", "extended release"
    ]

    BIOLOGIC_KEYWORDS = [
        "biologic", "biological",
        "growth factor", "BMP", "bone morphogenetic protein",
        "collagen", "fibrin", "thrombin",
        "platelet-rich plasma", "PRP",
        "cellular", "cell-based", "tissue-engineered",
        "allograft", "xenograft",
        "hyaluronic acid", "hyaluronan"
    ]

    COMBINATION_INDICATORS = [
        "combination product",
        "device-drug combination",
        "device-biologic combination",
        "primary mode of action",
        "PMOA",
        "RHO assignment",
        "CDER consultation",
        "CBER consultation"
    ]

    def detect(self, device_data: Dict) -> Dict:
        """
        Detect combination product status

        Returns:
        {
            "is_combination": bool,
            "combination_type": "device-drug" | "device-biologic" | "none",
            "detected_components": List[str],
            "confidence": "high" | "medium" | "low",
            "rho_assignment": "CDRH" | "CDER" | "CBER" | "undetermined",
            "consultation_required": bool,
            "regulatory_pathway": "21 CFR 3.2(e)" | "standard 510(k)"
        }
        """

        # Scan all text fields
        text_to_scan = " ".join([
            device_data.get("device_name", ""),
            device_data.get("intended_use", ""),
            device_data.get("device_description", ""),
            device_data.get("indications_for_use", ""),
            " ".join(device_data.get("extracted_sections", {}).values())
        ]).lower()

        # Check for explicit combination product mention
        explicit_combo = any(
            indicator in text_to_scan
            for indicator in self.COMBINATION_INDICATORS
        )

        # Check for drug components
        drug_components = [
            keyword for keyword in self.DRUG_KEYWORDS
            if keyword.lower() in text_to_scan
        ]

        # Check for biologic components
        biologic_components = [
            keyword for keyword in self.BIOLOGIC_KEYWORDS
            if keyword.lower() in text_to_scan
        ]

        # Determine combination status
        is_combination = (
            explicit_combo or
            len(drug_components) > 0 or
            len(biologic_components) > 0
        )

        if not is_combination:
            return {
                "is_combination": False,
                "combination_type": "none",
                "detected_components": [],
                "confidence": "high",
                "rho_assignment": "CDRH",
                "consultation_required": False,
                "regulatory_pathway": "standard 510(k)"
            }

        # Determine type
        if drug_components:
            combo_type = "device-drug"
            components = drug_components
            # Most drug-device combos are CDRH-led (device PMOA)
            rho = "CDRH"  # Assume device PMOA unless stated otherwise
            consult = "CDER"
        elif biologic_components:
            combo_type = "device-biologic"
            components = biologic_components
            # Biologics often require CBER consultation
            rho = "CDRH"  # Assume device PMOA unless stated otherwise
            consult = "CBER"
        else:
            combo_type = "undetermined"
            components = []
            rho = "undetermined"
            consult = None

        # Confidence level
        if explicit_combo:
            confidence = "high"
        elif len(components) >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "is_combination": True,
            "combination_type": combo_type,
            "detected_components": components,
            "confidence": confidence,
            "rho_assignment": rho,
            "consultation_center": consult,
            "consultation_required": True,
            "regulatory_pathway": "21 CFR 3.2(e) - Combination Product",
            "recommendation": f"Consult with {consult} for {combo_type} combination product assessment"
        }
```

**Integration into draft.md:**

```markdown
### Step 0.55: Combination Product Detection (NEW)

Run combination product detector:

```python
from lib.combination_product_detector import CombinationProductDetector

detector = CombinationProductDetector()
combo_result = detector.detect(device_profile)

if combo_result["is_combination"]:
    # Flag in device profile
    device_profile["combination_product"] = combo_result

    # Add warning to output
    print(f"""
    ⚠️ COMBINATION PRODUCT DETECTED
    Type: {combo_result["combination_type"]}
    Components: {", ".join(combo_result["detected_components"])}
    Confidence: {combo_result["confidence"]}

    RHO Assignment: {combo_result["rho_assignment"]} (Primary Mode of Action assumed: Device)
    Consultation Required: {combo_result["consultation_center"]}

    Regulatory Pathway: 21 CFR 3.2(e) - Combination Product

    NEXT STEPS:
    1. Verify Primary Mode of Action (PMOA) - Device vs. Drug/Biologic
    2. Submit RHO Request to FDA if PMOA unclear
    3. Coordinate with {combo_result["consultation_center"]} for consultation
    4. Use device-drug/biologic combination templates
    """)
```

**Add combination product templates:**

Create `plugins/fda-tools/templates/combination-product-device-description.md`:

```markdown
# Device Description (Combination Product)

## 1. Device Component Description
[Standard device description]

## 2. Drug/Biologic Component Description

### 2.1 Active Ingredient
- **Chemical name:** [e.g., Paclitaxel]
- **Concentration:** [e.g., 3 µg/mm²]
- **Form:** [e.g., Coating on balloon surface]
- **Source:** [e.g., Synthetic/Natural/Recombinant]

### 2.2 Mechanism of Action
[How the drug/biologic works in conjunction with device]

### 2.3 Pharmacokinetics (if applicable)
- **Release profile:** [e.g., 90% released within 60 seconds of inflation]
- **Systemic absorption:** [e.g., Minimal systemic exposure, <5% bioavailability]
- **Clearance:** [e.g., Hepatic metabolism]

## 3. Primary Mode of Action (PMOA) Determination

**PMOA:** Device [Justify why device PMOA vs. drug PMOA]

**Rationale:**
- The [device component] provides the primary therapeutic effect
- The [drug/biologic] serves an [adjunctive/coating/enhancing] role
- Clinical outcomes are primarily driven by [device mechanism]

## 4. RHO Assignment

**Lead Center:** CDRH (Device PMOA)
**Consulting Center:** [CDER for drug / CBER for biologic]
**21 CFR 3.2(e) Consultation:** [Required/Completed/Pending]

## 5. Regulatory History
[Any previous RHO requests, precedent combinations, etc.]
```

#### Testing
```bash
# Test 1: Drug-eluting catheter (DQY)
device = {
    "device_name": "DrugCoat Balloon Catheter",
    "description": "Paclitaxel-coated balloon for coronary intervention"
}
# Expected: device-drug, CDRH-led, CDER consultation

# Test 2: BMP spine cage (MAX)
device = {
    "device_name": "SpineFusion Cage with BMP-2",
    "description": "Titanium cage with bone morphogenetic protein"
}
# Expected: device-biologic, CDRH-led, CBER consultation

# Test 3: Silver dressing (FRO)
device = {
    "device_name": "SilverHeal Wound Dressing",
    "description": "Foam dressing with silver sulfadiazine"
}
# Expected: device-drug, CDRH-led, CDER consultation
```

#### Success Criteria
- ✅ Detector identifies drug-eluting devices
- ✅ Detector identifies biologic-containing devices
- ✅ RHO assignment logic (CDRH vs. CDER vs. CBER)
- ✅ Warning displayed during draft generation
- ✅ Combination product templates available
- ✅ Re-run Chen evaluation: Expected +2 points on Completeness
- ✅ Re-run Sharma evaluation: Expected +4 points (44 → 48/60)

#### Estimated Impact
- **Chen (cardiovascular):** 52 → 54/60
- **Sharma (combination):** 44 → 48/60 (LOWEST → FAIR)
- **Overall avg:** 49.7 → 50.4/60

---

### 2.3 ISO 14971 Risk Management Templates
**Requested by:** 56% of experts (5/9) - Chen, Martinez, Park, Rodriguez, Anderson
**Impact:** HIGH (required for ALL submissions)
**Effort:** Medium (20-25 hours)
**Current State:** No risk management templates
**Target State:** Automated risk analysis tables and FMEA templates

#### Implementation

**File to create:** `plugins/fda-tools/templates/iso-14971-risk-analysis.md`

```markdown
# ISO 14971 Risk Management File

**Device:** {{device_name}}
**Manufacturer:** {{manufacturer}}
**Date:** {{date}}
**Version:** 1.0

## 1. Risk Management Plan

### 1.1 Scope
This risk management file applies to the {{device_name}} and all associated accessories, software, and labeling.

### 1.2 Risk Acceptability Criteria

| Risk Level | Severity | Probability | Action Required |
|------------|----------|-------------|-----------------|
| **High** | Catastrophic/Critical | Probable/Occasional | Unacceptable - Must mitigate |
| **Medium** | Marginal | Probable | Mitigate if possible (ALARP) |
| **Low** | Negligible | Remote/Improbable | Acceptable - Monitor |

### 1.3 Risk Management Team
[List team members and roles]

## 2. Hazard Identification

### 2.1 Intended Use Hazards
| Hazard ID | Hazard Description | Hazardous Situation | Potential Harm |
|-----------|-------------------|---------------------|----------------|
| H-001 | [e.g., Device migration] | Device migrates from implant site | Tissue damage, reoperation |
| H-002 | [e.g., Material fracture] | Device fractures under load | Fragment embolism, device failure |
| H-003 | [e.g., Biocompatibility] | Allergic reaction to materials | Inflammation, tissue necrosis |

### 2.2 Foreseeable Misuse Hazards
| Hazard ID | Misuse Scenario | Hazardous Situation | Potential Harm |
|-----------|-----------------|---------------------|----------------|
| M-001 | Oversizing device | User selects wrong size | Vessel trauma, perforation |
| M-002 | Reuse of single-use device | Device reprocessed incorrectly | Infection, device failure |

### 2.3 System/Component Failure Hazards
| Hazard ID | Failure Mode | Hazardous Situation | Potential Harm |
|-----------|--------------|---------------------|----------------|
| F-001 | Coating delamination | Drug coating detaches | Embolism, reduced efficacy |
| F-002 | Software error | Algorithm miscalculation | Incorrect diagnosis |

## 3. Risk Analysis (FMEA)

| Hazard ID | Severity (1-5) | Probability (1-5) | Detectability (1-5) | RPN | Risk Level |
|-----------|----------------|-------------------|---------------------|-----|------------|
| H-001 | 4 (Critical) | 2 (Remote) | 3 (Moderate) | 24 | Medium |
| H-002 | 5 (Catastrophic) | 1 (Improbable) | 4 (Low) | 20 | Medium |
| H-003 | 3 (Marginal) | 2 (Remote) | 2 (High) | 12 | Low |
| M-001 | 4 (Critical) | 3 (Occasional) | 3 (Moderate) | 36 | High |
| F-001 | 4 (Critical) | 2 (Remote) | 3 (Moderate) | 24 | Medium |

**RPN = Severity × Probability × Detectability**

## 4. Risk Control Measures

| Hazard ID | Risk Control Measure | Type | Verification Method |
|-----------|---------------------|------|---------------------|
| H-001 | Fixation mechanism (barbs) | Inherently safe design | Bench testing per ASTM F2077 |
| H-002 | Material fatigue testing | Design verification | Fatigue testing per ASTM F1717 |
| H-003 | Biocompatibility testing | Verification | ISO 10993 battery |
| M-001 | Sizing guide in IFU | Information for safety | Human factors validation |
| F-001 | Adhesion testing | Verification | Per ISO 25539-2 |

## 5. Residual Risk Evaluation

| Hazard ID | Pre-Mitigation RPN | Risk Control | Post-Mitigation RPN | Acceptable? |
|-----------|-------------------|--------------|---------------------|-------------|
| H-001 | 24 (Medium) | Fixation mechanism | 12 (Low) | ✓ Yes |
| H-002 | 20 (Medium) | Fatigue testing | 10 (Low) | ✓ Yes |
| M-001 | 36 (High) | IFU warnings + sizing guide | 18 (Medium) | ✓ Yes (ALARP) |

## 6. Risk/Benefit Analysis

**Overall Benefit:** [Describe clinical benefit]

**Residual Risks:** [List remaining risks]

**Conclusion:** The residual risks are outweighed by the clinical benefits when the device is used according to its intended use. All high risks have been mitigated to medium or low levels.

## 7. Production and Post-Production Information

### 7.1 Complaint Monitoring
- Monitor MAUDE database quarterly
- Track complaints for trending
- Update risk file if new hazards identified

### 7.2 Post-Market Surveillance
- Annual review of risk management file
- Trigger for review: Any serious injury or death

---

**Risk Management File Approved:**

Signature: _________________ Date: _______
Name: Risk Management Lead
```

**Create command to generate risk analysis:**

**File:** `plugins/fda-tools/commands/risk-analysis.md`

```markdown
---
description: Generate ISO 14971 risk management file with FMEA tables
allowed-tools:
  - Read
  - Write
  - Bash
argument-hint: "[--hazards N] [--include-fmea] [--include-fta]"
---

# Generate Risk Analysis

Create ISO 14971 compliant risk management file with automated hazard identification and FMEA tables.

## Step 1: Load Device Data
Read device_profile.json to understand:
- Device type and intended use
- Materials and components
- Electrical/mechanical features
- Software components
- User interactions

## Step 2: Identify Common Hazards by Device Type

**For implantable devices:**
- H-001: Device migration/dislodgement
- H-002: Material fracture/fatigue
- H-003: Biocompatibility reactions
- H-004: Infection from implantation
- H-005: Thrombosis/embolism

**For electrical devices:**
- E-001: Electrical shock
- E-002: Electromagnetic interference
- E-003: Excessive heating
- E-004: Software malfunction
- E-005: Battery failure

**For surgical devices:**
- S-001: Tissue trauma from use
- S-002: User error (misuse)
- S-003: Device fracture during use
- S-004: Contamination/sterility breach

**For software/SaMD:**
- SW-001: Algorithm error (false positive/negative)
- SW-002: Cybersecurity breach
- SW-003: Data corruption
- SW-004: Integration failure with other systems

## Step 3: Populate FMEA Table
For each hazard, estimate:
- **Severity:** 1-5 (Negligible to Catastrophic)
- **Probability:** 1-5 (Improbable to Frequent)
- **Detectability:** 1-5 (High to None)
- **RPN:** Severity × Probability × Detectability

## Step 4: Suggest Risk Controls
Based on device type and hazards:
- Inherently safe design
- Protective measures
- Information for safety (IFU warnings)

## Step 5: Generate Output
Write ISO 14971 risk management file to:
`~/fda-510k-data/projects/{{project}}/risk-management/ISO_14971_Risk_File.md`

Include:
- Risk management plan
- Hazard identification tables
- FMEA with RPN calculations
- Risk control measures
- Residual risk evaluation
- Risk/benefit analysis
```

#### Testing
```bash
# Test: Generate risk analysis for cardiovascular device
/fda-tools:risk-analysis --project DQY_balloon

# Expected output:
# - ISO_14971_Risk_File.md created
# - 10-15 hazards identified
# - FMEA table with RPN
# - Risk controls suggested
```

#### Success Criteria
- ✅ ISO 14971 template created
- ✅ Device-type specific hazard libraries
- ✅ FMEA table auto-generated
- ✅ Risk control suggestions
- ✅ Re-run Martinez evaluation: Expected +1 point
- ✅ 5/9 experts (56%) who requested this see value

#### Estimated Impact
- **Overall avg:** 49.7 → 50.2/60

---

## Priority 3: Strategic Improvements (3-6 Months)

### 3.1 Clinical Endpoint Libraries
**Requested by:** 44% of experts (4/9)
**Effort:** High (30-40 hours)

**Device-specific endpoint templates:**
- Cardiovascular: TLR, MACE, device success rate
- Orthopedic: PROs (VAS, KOOS, ODI), radiographic fusion
- Neurology: Stimulation parameters, responder rates

### 3.2 AI/ML Validation Framework
**Requested by:** 33% of experts (3/9)
**Effort:** Very High (40-60 hours)

**Components:**
- Algorithm transparency templates
- Training/validation dataset documentation
- Performance metrics (sensitivity, specificity, AUC)
- Bias/fairness assessment checklists

### 3.3 Device-Specific Terminology Libraries
**Requested by:** 44% of experts (4/9)
**Effort:** Medium (20-30 hours per domain)

**Domains:**
- Cardiovascular: Balloon inflation, guide wire compatibility
- Orthopedic: Osseointegration, load-bearing capacity
- IVD: Analytical sensitivity, limit of detection

---

## Implementation Timeline

### Sprint 1 (Week 1-2): Quick Wins
- [ ] Sterilization auto-triggers (4 hours)
- [ ] Shelf life packaging (2 hours)
- [ ] Test and validate (2 hours)

**Deliverable:** +0.5 points on Completeness

### Sprint 2 (Week 3-6): Device-Specific Standards
- [ ] Robotics standards library (10 hours)
- [ ] Neurostimulation standards library (10 hours)
- [ ] IVD standards library (12 hours)
- [ ] SaMD standards library (10 hours)
- [ ] Integration and testing (8 hours)

**Deliverable:** +0.8 points on Completeness

### Sprint 3 (Week 7-10): Combination Products
- [ ] Combination product detector (10 hours)
- [ ] RHO assignment logic (5 hours)
- [ ] Combination product templates (5 hours)
- [ ] Testing and validation (5 hours)

**Deliverable:** +0.7 points average (critical for combo specialists)

### Sprint 4 (Week 11-14): Risk Management
- [ ] ISO 14971 template (8 hours)
- [ ] Device-type hazard libraries (10 hours)
- [ ] FMEA auto-generation (7 hours)
- [ ] Risk command implementation (5 hours)

**Deliverable:** +0.5 points on Completeness

### Sprint 5-8 (Month 4-6): Strategic Features
- [ ] Clinical endpoint libraries (30 hours)
- [ ] AI/ML validation framework (40 hours)
- [ ] Terminology libraries (60 hours)

**Deliverable:** +1.0 points overall

---

## Success Metrics

### Quantitative Targets

| Metric | Current | Target (After Quick Wins) | Target (After High-Impact) | Target (After Strategic) |
|--------|---------|---------------------------|---------------------------|-------------------------|
| **Overall Score** | 49.7/60 (82.8%) | 50.2/60 (83.7%) | 52.0/60 (86.7%) | 55.0/60 (91.7%) |
| **Completeness** | 7.7/10 | 8.2/10 | 9.0/10 | 9.5/10 |
| **Adoption Rate** | 89% (8/9) | 89% | 100% (9/9) | 100% |
| **Time Savings** | 68% | 70% | 72% | 75% |
| **Would Pay** | 78% | 80% | 90% | 95% |

### Qualitative Targets

**After Quick Wins:**
- ✅ No more "missing sterilization standards" complaints
- ✅ Catheter devices get packaging-adjusted AAF

**After High-Impact:**
- ✅ Robotics expert (Rodriguez) increases from 53 → 55/60
- ✅ Neurology expert (Anderson) increases from 49 → 51/60
- ✅ IVD expert (Park) increases from 48 → 50/60
- ✅ Combination expert (Sharma) increases from 44 → 48/60
- ✅ SaMD expert (Kim) increases from 50 → 52/60
- ✅ 100% adoption (Sharma moves from "Maybe" to "Yes")

**After Strategic:**
- ✅ All experts rate Completeness 9-10/10
- ✅ Clinical experts praise endpoint libraries
- ✅ SaMD experts praise AI/ML framework
- ✅ All domains have device-specific terminology

---

## Resource Requirements

### Development Team
- **Lead Developer:** 120 hours (full implementation)
- **Regulatory SME:** 40 hours (standards research, template review)
- **QA/Testing:** 20 hours (validation across device types)

### External Resources
- **CLSI Standards:** Purchase for IVD templates (~$500)
- **ISO Standards:** Access to ISO 13482, IEC 80601-2-77, etc. (~$1,000)
- **Regulatory Consultation:** 5 hours with RA professional (~$1,500)

**Total Investment:** ~160 hours + $3,000

**Expected ROI:**
- Increase adoption from 89% → 100%
- Enable $150-300/month pricing (78% → 95% would pay)
- Potential user base increase by 11% (get Sharma on board)

---

## Next Steps

### Immediate Actions (This Week)
1. ✅ Review this implementation plan
2. ✅ Prioritize which improvements to tackle first
3. ✅ Assign development resources
4. ✅ Set Sprint 1 kickoff date

### Validation (After Each Sprint)
1. Re-run simulated expert evaluations
2. Recruit 1-2 real experts from affected domains
3. Compare scores before/after
4. Adjust priorities based on feedback

### Continuous Improvement
1. After each improvement, update expert evaluation results
2. Track score progression: 49.7 → 50.2 → 52.0 → 55.0/60
3. Celebrate wins with team when adoption hits 100%
4. Use improved scores in marketing materials

---

**Implementation Plan Created:** 2026-02-14
**Total Improvements:** 13 (3 Quick Wins + 3 High-Impact + 7 Strategic)
**Expected Score Increase:** 49.7 → 55.0/60 (+5.3 points, +10.8%)
**Timeline:** 6 months for full implementation
**Investment:** ~160 hours + $3K resources
**ROI:** 100% adoption, 95% would pay, stronger market position
