# 510(k) Submission Structure Reference

Knowledge base for submission formatting, pathway decision criteria, and Pre-Submission planning. Used by `/fda:presub`, `/fda:submission-outline`, and referenced by `/fda:research`.

## 510(k) Submission Pathways

### Decision Criteria

| Criterion | Traditional | Special | Abbreviated | De Novo |
|-----------|-------------|---------|-------------|---------|
| Predicate exists | Yes | Yes | Yes | No |
| Same intended use | Yes | Yes | Yes | N/A |
| Same technology | Maybe | Yes (modified only) | Maybe | N/A |
| Relies on guidance/standard | Maybe | No | Yes (primarily) | N/A |
| Modification to own device | No | Yes | No | N/A |
| Typical review time | 90 days | 30 days | 90 days | 150 days |
| Best for | New market entrants | Device modifications | Guidance/standard-driven | Novel low/moderate risk |

### Pathway Selection Logic

```
IF no predicate device exists:
  → De Novo (or PMA if high-risk)

ELSE IF modifying your own previously cleared device:
  AND change does not affect intended use:
  AND change does not alter fundamental technology:
  → Special 510(k)

ELSE IF FDA guidance document or recognized standard covers the device:
  AND submission can rely primarily on conformance to guidance/standard:
  → Abbreviated 510(k)

ELSE:
  → Traditional 510(k) (default)
```

### Pathway Details

**Traditional 510(k)**
- Most common pathway (~85% of submissions)
- Full comparison to predicate device
- Performance data, biocompatibility, clinical (if needed)
- No restrictions on predicate selection
- ~90 day FDA review

**Special 510(k)**
- For modifications to your OWN previously cleared device
- Must demonstrate modification does NOT affect safety/effectiveness
- Can use design controls (risk analysis, V&V) instead of new testing
- Faster review (~30 days)
- Limited to modifications — not for new market entrants

**Abbreviated 510(k)**
- Relies on FDA guidance document or recognized consensus standard
- Summary report referencing conformance
- Less data than Traditional (guidance/standard provides the framework)
- Appropriate when FDA has published specific guidance for the device type

**De Novo**
- For novel devices with no predicate
- Must demonstrate low-to-moderate risk
- Creates a new classification and regulation number
- Future 510(k)s can cite the De Novo as a predicate
- Longer review (~150 days)

## Standard 510(k) Table of Contents

### Traditional 510(k)

Per FDA guidance "Recommended Content of a Traditional 510(k) Submission":

```
1.  Cover Letter
2.  CDRH Premarket Review Submission Cover Sheet (FDA Form 3514)
3.  510(k) Summary or 510(k) Statement (21 CFR 807.92/807.93)
4.  Truthful and Accuracy Statement (21 CFR 807.87(j))
5.  Class III Summary and Certification (if applicable)
6.  Financial Certification or Disclosure Statement (21 CFR 54)
7.  Declarations of Conformity and Summary Reports (if Abbreviated)
8.  Device Description
9.  Substantial Equivalence Comparison
    9a. Comparison Table (subject device vs. predicate(s))
    9b. Comparison Discussion
10. Standards and Guidance Documents
    10a. Recognized Consensus Standards (declarations of conformity)
    10b. Applicable FDA Guidance Documents
11. Proposed Labeling
    11a. Indications for Use Statement (Form FDA 3881)
    11b. Instructions for Use (IFU)
    11c. Device Labels
    11d. Patient Labeling (if applicable)
12. Sterilization (if applicable)
    12a. Sterilization Method Description
    12b. Sterilization Validation Summary
    12c. Sterility Assurance Level (SAL)
    12d. Pyrogenicity / Endotoxin Testing
13. Shelf Life / Package Testing (if applicable)
    13a. Accelerated Aging Protocol and Results
    13b. Real-Time Aging (if available)
    13c. Package Integrity Testing
    13d. Transportation / Shipping Validation
14. Biocompatibility
    14a. Biocompatibility Evaluation Summary
    14b. Material Characterization
    14c. ISO 10993 Test Reports (or summaries)
15. Software Documentation (if applicable)
    15a. Level of Concern
    15b. Software Description
    15c. Software Risk Analysis
    15d. Software Requirements Specification (SRS)
    15e. Architecture Design Chart
    15f. Software Design Specification (SDS)
    15g. Traceability Analysis
    15h. Software Development Environment Description
    15i. V&V Documentation
    15j. Revision Level History
    15k. Unresolved Anomalies (Bug List)
    15l. Cybersecurity Documentation (if connected/networked)
16. Electromagnetic Compatibility (EMC) and Electrical Safety (if applicable)
    16a. IEC 60601-1 Compliance
    16b. IEC 60601-1-2 EMC Test Report
    16c. Wireless Testing (if applicable)
17. Performance Testing — Non-Clinical
    17a. Test Protocols
    17b. Test Reports
    17c. Device-Type Specific Testing
18. Performance Testing — Clinical (if applicable)
    18a. Clinical Study Report or Literature Review
    18b. Clinical Data Analysis
    18c. Adverse Event Summary
19. Human Factors / Usability (if applicable)
    19a. Use-Related Risk Analysis
    19b. Formative Studies Summary
    19c. Summative (Validation) Study Report
20. Other Submission Information
```

### Special 510(k)

```
1.  Cover Letter (stating Special 510(k))
2.  CDRH Premarket Review Submission Cover Sheet
3.  510(k) Summary or Statement
4.  Truthful and Accuracy Statement
5.  Financial Certification or Disclosure Statement
6.  Device Description
    6a. Original Device Description
    6b. Modification Description
    6c. Modification Summary
7.  Substantial Equivalence — Comparison to Own Prior Device
    7a. Original cleared K-number
    7b. Changes made (design, manufacturing, labeling, materials)
    7c. Comparison table: original vs. modified
8.  Risk Analysis
    8a. Updated risk analysis addressing the modification
    8b. Impact assessment: safety and effectiveness
9.  Design Verification and Validation
    9a. Design Controls documentation for the modification
    9b. V&V results demonstrating modification doesn't adversely affect safety/effectiveness
10. Proposed Labeling (updated if modification affects labeling)
11. Summary of Supporting Data (if any new testing required)
```

### Abbreviated 510(k)

```
1.  Cover Letter (stating Abbreviated 510(k))
2.  CDRH Premarket Review Submission Cover Sheet
3.  510(k) Summary or Statement
4.  Truthful and Accuracy Statement
5.  Financial Certification or Disclosure Statement
6.  Device Description
7.  Substantial Equivalence Comparison
8.  Declarations of Conformity
    8a. FDA-recognized consensus standard declarations
    8b. Summary test reports for each standard
9.  Guidance Document Conformity
    9a. Identification of applicable guidance
    9b. Summary of conformance to guidance recommendations
10. Proposed Labeling
11. Summary Data (only for aspects not covered by standards/guidance)
```

### eSTAR (Electronic Submission Template)

FDA's recommended electronic submission format. Same content as above but organized into the eSTAR template:

```
eSTAR Sections:
1.  Applicant Information
2.  Device Information
3.  Predicate Device Information
4.  Device Description
5.  Substantial Equivalence Comparison
6.  Proposed Labeling
7.  Sterilization
8.  Shelf Life
9.  Biocompatibility
10. Software
11. EMC / Electrical Safety
12. Performance Testing
13. Clinical Testing
14. Other
```

The eSTAR maps directly to the Traditional 510(k) ToC. FDA strongly recommends using eSTAR format.

## Pre-Submission (Pre-Sub) Meeting Format

### What is a Pre-Sub?

A Pre-Submission meeting request to FDA (formerly "Pre-IDE") allows you to:
- Get FDA feedback on your proposed regulatory strategy
- Clarify testing requirements before conducting expensive studies
- Discuss predicate selection
- Resolve classification questions
- Understand clinical data expectations

### Pre-Sub Package Contents

Per FDA guidance "Requests for Feedback and Meetings for Medical Device Submissions: The Q-Submission Program":

```
1.  Cover Letter
    - Request for Pre-Submission meeting
    - Subject device name and product code
    - Preferred meeting type (written feedback only, teleconference, in-person)
    - Proposed meeting date range (FDA targets 75 days after receipt)

2.  Device Description
    - Detailed description of the device
    - Principle of operation
    - Key components and materials
    - Intended use / Indications for Use (proposed)
    - Illustrations / diagrams

3.  Proposed Regulatory Strategy
    - Proposed pathway (Traditional, Special, Abbreviated, De Novo)
    - Rationale for pathway selection
    - Proposed predicate device(s) with justification
    - Classification and product code analysis

4.  Specific Questions for FDA (numbered)
    - Testing strategy questions
    - Clinical data questions
    - Predicate selection questions
    - Classification questions
    - Labeling questions
    - Max ~5-7 focused questions

5.  Supporting Data (if available)
    - Preliminary testing results
    - Literature references
    - Predicate comparison table (draft)
    - Risk analysis summary
```

### Pre-Sub Meeting Types

| Type | Format | Best For |
|------|--------|----------|
| Written Feedback Only | No meeting — FDA responds in writing | Simple questions, clear regulatory path |
| Teleconference | 60-min call with FDA review team | Moderate complexity, few questions |
| In-Person / Virtual | FDA campus or video meeting | Complex devices, many questions, novel technology |

### Pre-Sub Question Categories

Common question topics and templates:

**Predicate Selection**:
"Does FDA agree that {K-number} ({device name}) is an appropriate predicate for our {device description}? If not, can FDA recommend an alternative predicate?"

**Testing Strategy**:
"We propose to conduct {test type} per {standard} to demonstrate {performance claim}. Does FDA agree this testing strategy is sufficient, or does FDA recommend additional testing?"

**Clinical Data**:
"Based on the predicate precedent showing {X}, is FDA's current expectation that clinical data will be needed for our submission? If so, what study design would FDA recommend?"

**Classification**:
"We believe our device is classified under product code {CODE} (21 CFR {regulation}). Does FDA agree with this classification?"

**Indications for Use**:
"We propose the following indications for use: '{IFU text}'. Does FDA agree these indications are appropriate, or does FDA recommend modifications?"

**Novel Features**:
"Our device includes {novel feature} not present in the predicate. What additional data, if any, does FDA recommend to address this difference?"

## Section-by-Section Requirements Reference

### Section: Device Description
**Required content**:
- Physical description (dimensions, weight, appearance)
- Materials of construction (all patient-contacting materials)
- Principle of operation
- Key performance specifications
- Components list (for multi-component devices)
- Accessories (if any)
- Photographs or diagrams

### Section: Substantial Equivalence Comparison
**Required content** (21 CFR 807.87(f)):
- Side-by-side comparison of subject and predicate
- Intended use comparison
- Technological characteristics comparison
- Performance data comparison
- Discussion of similarities and differences
- Justification for any differences
- Statement of substantial equivalence

### Section: Indications for Use (Form FDA 3881)
**Required fields**:
- Device name (trade name)
- Indications for use text
- Type of use: prescription / OTC / both
- Previous 510(k) number (if applicable)

### Section: Biocompatibility
**Required** (per ISO 10993-1 flowchart):
- Nature of body contact (surface, external communicating, implant)
- Contact duration (<24hr, 24hr-30 days, >30 days)
- ISO 10993 test battery based on contact category
- Material characterization (ISO 10993-18)
- Biological evaluation plan and results

### Section: Sterilization
**Required** (if device is provided sterile):
- Sterilization method description
- Validation per applicable standard
- Sterility Assurance Level (typically SAL 10^-6)
- Residual levels (EO: ISO 10993-7)
- Pyrogenicity testing (if applicable)

### Section: Shelf Life
**Required** (if device has an expiration date):
- Accelerated aging protocol (ASTM F1980 Q10 method)
- Real-time aging data (if available)
- Package integrity testing
- Storage conditions
- Labeled shelf life with supporting data

## Gap Analysis Framework

Used by `/fda:submission-outline` to identify testing gaps:

```
For each testing category:
  1. Check if FDA guidance REQUIRES it for this device type
  2. Check if predicates INCLUDED it in their submissions
  3. Determine status:
     - NEEDED: Required by guidance AND done by predicates
     - PLAN: Required by guidance but NOT done by most predicates
     - RECOMMENDED: Not required but done by most predicates
     - CONSIDER: Not required, done by some predicates
     - N/A: Not applicable to this device type
```

### Status Definitions

| Status | Meaning | Action |
|--------|---------|--------|
| **NEEDED** | Required — must include in submission | Plan and budget for this testing |
| **PLAN** | Required but precedent is thin — plan carefully | May need Pre-Sub question about expectations |
| **RECOMMENDED** | Not required but commonly included | Include if possible; justify omission if not |
| **CONSIDER** | Optional — some predicates included it | Include if it strengthens submission |
| **N/A** | Not applicable to this device type | Do not include |
