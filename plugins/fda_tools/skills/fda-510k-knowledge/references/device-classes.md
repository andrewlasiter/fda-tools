# FDA Device Classification Reference

## Overview

The FDA classifies medical devices into three classes based on risk level and regulatory controls needed to ensure safety and effectiveness.

## Class I - Low Risk

### Characteristics
- Subject to general controls only
- Lowest risk to patients
- Simple design, well-understood technology

### Regulatory Requirements
- **General Controls:**
  - Registration and listing
  - Good Manufacturing Practices (GMP)
  - Labeling requirements
  - Premarket notification (most are exempt)

### Examples
| Device | Product Code | Description |
|--------|--------------|-------------|
| Elastic bandage | FXW | Wound dressing |
| Tongue depressor | EEI | Examination device |
| Examination gloves | FME | Protective barrier |
| Manual stethoscope | BZH | Acoustic device |

### 510(k) Status
- ~75% are exempt from 510(k)
- Exempt devices still require registration
- Non-exempt Class I requires 510(k)

## Class II - Moderate Risk

### Characteristics
- General controls insufficient alone
- Special controls needed
- Moderate risk to patients

### Regulatory Requirements
- **General Controls** (same as Class I)
- **Special Controls:**
  - Performance standards
  - Postmarket surveillance
  - Patient registries
  - Special labeling
  - Guidance documents

### Examples
| Device | Product Code | Description |
|--------|--------------|-------------|
| Powered wheelchair | ITI | Mobility device |
| Pregnancy test | LCN | Diagnostic device |
| Blood pressure monitor | DXN | Monitoring device |
| Infusion pump | FRN | Drug delivery |
| Contact lens | LPL | Vision correction |

### 510(k) Status
- Most require 510(k) clearance
- Some exempt from 510(k) but not from controls
- Predicate typically another Class II device

## Class III - High Risk

### Characteristics
- Insufficient information to ensure safety
- Life-supporting or life-sustaining
- Significant risk of illness/injury
- Usually implanted devices

### Regulatory Requirements
- **General Controls**
- **Premarket Approval (PMA):**
  - Clinical trials required
  - Extensive review process
  - Most stringent pathway

### Examples
| Device | Product Code | Description |
|--------|--------------|-------------|
| Pacemaker | DXY | Cardiac rhythm |
| Heart valve | DRQ | Cardiovascular |
| Breast implant | MYA | Implanted prosthesis |
| HIV test | BMA | Critical diagnostic |

### 510(k) Status
- Generally NOT eligible for 510(k)
- Requires PMA (Premarket Approval)
- Exception: Pre-amendments Class III devices

## Classification Determination

### How FDA Determines Class
1. **Intended Use**: What is the device for?
2. **Indications for Use**: Specific conditions/patients
3. **Risk Level**: Potential for harm
4. **Control Sufficiency**: What's needed for safety

### Product Code Assignment
- 3-letter code (e.g., DXY, FRN)
- Links to:
  - Medical specialty panel
  - Regulation number
  - Classification (I, II, III)
  - 510(k) exemption status

### Finding Device Classification
- FDA Product Classification Database
- foiclass.txt file (offline reference)
- 510(k) decision summaries

## Classification Changes

### Reclassification
Devices can be reclassified:
- Class III → Class II (down-classification)
- Based on new safety data
- Through FDA reclassification proceedings

### De Novo Pathway
For novel devices:
- Low-moderate risk
- No predicate exists
- Creates new classification
- Future devices can use as predicate

## Implications for Predicate Selection

### Class Considerations
- Predicate should be same class or lower
- Class III devices rarely valid predicates for 510(k)
- Reclassified devices may become predicates

### Product Code Matching
- Same product code: strongest predicate evidence
- Different product code: need to justify equivalence
- Cross-specialty predicates: challenging but possible
