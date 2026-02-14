# Phase 4: Gap Analysis — Quick Reference Card

## Feature Summary

**What:** Automated comparison of subject device against FDA predicates to identify specification, feature, and testing gaps.

**Why:** Regulatory teams need systematic gap identification to:
- Plan submission scope and testing strategy
- Assess regulatory risk early
- Prioritize remediation efforts
- Track closure status

**Output:** CSV (34 cols) + Markdown report + Excel tracking sheet

---

## Key Concepts at a Glance

### Gap Severity Tiers

| Severity | Score | Testing | FDA Risk | Example |
|----------|-------|---------|----------|---------|
| **MAJOR** | 71-100 | New testing required | AI request expected | New indication, novel material, extended shelf life |
| **MODERATE** | 31-70 | Comparative testing | May trigger AI | Different sensor principle, modified sterilization |
| **MINOR** | 0-30 | Documentation only | None expected | UI update, cosmetic change, color difference |

### Gap Detection Rules

```
Rule 1: TEXT COMPARISON       → Indications, IFU, intended use
Rule 2: FEATURE PARITY         → New/missing features
Rule 3: QUANTITATIVE RANGE    → Size, power, accuracy specs
Rule 4: STANDARDS & TESTING   → ISO, IEC, ASTM compliance
Rule 5: NOVEL CLAIMS          → Precedent search across predicate chain
```

### Severity Scoring Algorithm

```
Base Score (gap type):        40-90 pts
+ Testing Burden:            0-40 pts
+ Precedent Strength:        -30 to +10 pts
+ Predicate Risk Adjustment: 0-20 pts
= Final Score (0-100)
```

---

## CSV Output Format (34 Columns)

```
1.  gap_id                    GA-001-MAJOR-IFU
2.  dimension                 "Indications for Use"
3.  category                  "Identity & Regulatory"
4.  subject_value             "Type 1 & 2 diabetes"
5.  predicate_knumber         K241335
6.  predicate_device_name     "Guardian CGM"
7.  predicate_value           "Type 1 diabetes"
8.  gap_type                  NEW_INDICATION
9.  gap_description           "Subject adds type 2 diabetes"
10. severity_score            68
11. severity_category         MAJOR
12. regulatory_risk           "HIGH — AI request expected"
13. testing_required          TRUE
14. testing_type              "Clinical validation study"
15. testing_standard          "FDA Draft Guidance (2019)"
16. estimated_effort_hours    600
17. precedent_strength        0.67
18. remediation_recommendation "Multi-site study, N=150+, 90-day follow-up"
19. remediation_priority      HIGH
20. fda_guidance_reference    "21 CFR 807.87(b)"
21. status                    OPEN
22. owner                     "Clinical Affairs"
23. target_close_date         2026-06-30
24. closure_evidence          "Clinical study results"
25. predicate_risk_flag       FALSE
26. predicate_health          HEALTHY
27. alternative_predicate_found FALSE
28. notes                     "Type 2 diabetes is common indication"
29. created_date              2026-02-13T10:30:00Z
30. last_updated              2026-02-13T10:30:00Z
31. predicate_comparison_url  https://...
[+ 3 reserved fields]
```

---

## Device Templates (By Product Code)

### How Templates Work

Each product code has a device-specific comparison template:
```
Product Code QAS (PACS) → 25 dimensions
  ├── Intended Use
  ├── Display Resolution
  ├── DICOM Conformance
  ├── Workstation Specifications
  └── ... (22 more)

Product Code HCE (Hip) → 40 dimensions
  ├── Intended Use
  ├── Fixation Method
  ├── Materials & Surface Treatment
  ├── Fatigue Testing
  ├── Wear Testing
  └── ... (35 more)
```

### Template Selection (5-Tier Matching)

```
Tier 1: Exact product code match
  SBA, QBJ, QLG → CGM_TEMPLATE (70 dimensions)

Tier 2: Device class family match
  HCE, HCF, HDP → HIP_ARTHROPLASTY_TEMPLATE (40 dimensions)

Tier 3: Regulatory pathway match
  Class II ortho → ORTHOPEDIC_IMPLANT_TEMPLATE (35 dimensions)

Tier 4: Fallback to device type
  Unknown code, but "stent" detected → STENT_TEMPLATE

Tier 5: Generic template
  No match → GENERIC_TEMPLATE (15 universal dimensions)
```

---

## Conditional Dimensions (Auto-Added)

Template base dimensions + conditional adds:

```
Base dimensions (from template)
↓
IF device is reusable:
  + Reprocessing Method
  + Maximum Reprocessing Cycles
  + Cleaning Agents
↓
IF device is powered/wireless:
  + Power Source & Battery Life
  + Wireless Protocol & SAR
  + Cybersecurity & Authentication
↓
IF device contains software:
  + IEC 62304 Classification Level
  + Software Verification & Validation
  + Cybersecurity Assessment
↓
IF shelf life claim >2 years:
  + Claimed Duration
  + Aging Methodology
  + Q10 Value
  + Package Integrity Testing
```

---

## Gap Detection Examples

### Example 1: Text Gap (Intended Use)

```
Subject: "Blood glucose monitoring for type 1 & 2 diabetes"
Predicate: "Blood glucose monitoring for type 1 diabetes"

Detection: NEW_INDICATION
Severity: 68/100 (MAJOR)
Testing: Clinical study (N=150+, 90-day, HbA1c ≥6.5%)
Effort: 600 hours
FDA Risk: HIGH (AI request expected)
```

### Example 2: Quantitative Gap (Dimensions)

```
Subject: Weight = 150g
Predicate: Weight = 120g
Tolerance: ±10%

Outside range: 150 > 120 × 1.10 = 132
Detection: LARGER_THAN_PREDICATE
Severity: 35/100 (MINOR)
Testing: None (cosmetic concern)
FDA Risk: LOW
```

### Example 3: Standards Gap (Biocompatibility)

```
Subject standards: ISO 10993-5, ISO 10993-10
Predicate standards: ISO 10993-5, ISO 10993-10, ISO 10993-11
Required for permanent implants: ISO 10993-11

Detection: MISSING_STANDARD
Severity: 55/100 (MODERATE)
Testing: ISO 10993-11 biocompatibility panel
Effort: 200 hours
```

### Example 4: Feature Gap (Wireless)

```
Subject features: [Bluetooth, Cloud, Real-time alerts, ...WiFi]
Predicate features: [Non-connected, Standalone only]

Detection: NEW_FEATURE (Wireless/Connectivity)
Severity: 75/100 (MAJOR)
Testing: EMC (IEC 60601-1-2) + Cybersecurity assessment
Effort: 300 hours
FDA Risk: HIGH (new functionality)
```

---

## Integration with Other Commands

### Pre-Check Command (`/fda:pre-check`)

Gap analysis feeds into RTA risk scoring:
```
MAJOR gaps found: +15 points to RTA risk
MODERATE gaps:    +8 points to AI request likelihood
MINOR gaps:       +2 points to documentation quality
```

### Compare-SE Command (`/fda:compare-se`)

Gap data populates SE table "Comparison" column:
```
| Characteristic | Subject | Predicate | Comparison |
|---|---|---|---|
| Intended Use | Type 1&2 | Type 1 only | **Different** — See gap GA-001 for remediation |
```

### Draft Command (`/fda:draft`)

Section generation can reference gap remediations:
```
Section 5.2 (Shelf Life):
"Claimed shelf life of 5 years per gap analysis remediation GA-012.
Aging study per ASTM F1980 with Q10=2.0..."
```

---

## Workflow: From Gap to Remediation

```
1. RUN GAP ANALYSIS
   └─> Identify all gaps across dimensions

2. PRIORITIZE BY SEVERITY
   └─> MAJOR gaps first (blocking issues)
       → MODERATE gaps (refinement)
       → MINOR gaps (polish)

3. ASSIGN OWNERS & DEADLINES
   └─> Gap tracking spreadsheet
       Clinical Affairs → Clinical studies
       QA → Testing & standards
       Engineering → Design changes

4. EXECUTE REMEDIATION
   └─> Per gap-specific guidance
       Track progress in spreadsheet

5. CLOSE GAPS
   └─> Upload evidence to closure_evidence field
       Update status to RESOLVED
       Reference in submission package

6. SUBMIT
   └─> Include gap analysis report as appendix
       Cross-reference closures in each section
```

---

## Command Usage

### Quick Start

```bash
/fda-predicate-assistant:gap-analysis --project my_project
```

### Full Options

```bash
/fda-predicate-assistant:gap-analysis \
  --project my_project \
  --predicates K241335,K234567 \
  --product-code SBA \
  --depth standard \
  --output-dir ~/analysis \
  --full-auto
```

### Output Files

```
{PROJECT}/gap_analysis.csv              34 columns, all gaps
{PROJECT}/gap_analysis_report.md        Formatted markdown report
{PROJECT}/gap_tracking.xlsx             Project management spreadsheet
{PROJECT}/remediation_roadmap.md        Timeline & cost estimates
{PROJECT}/gap_analysis_metadata.json    Analysis parameters
```

---

## Decision Tree: Is This a GAP?

```
START: Compare subject to predicate for dimension X

├─ VALUES IDENTICAL?
│  └─ YES → NO GAP ✅
│
├─ VALUES TEXTUALLY SIMILAR (>85%)?
│  └─ YES → NO GAP ✅
│
├─ QUANTITATIVE WITHIN TOLERANCE?
│  └─ YES → NO GAP ✅
│
├─ SUBJECT ADDS NEW FEATURES/INDICATIONS?
│  └─ YES → GAP DETECTED (severity HIGH) ⚠️
│
├─ SUBJECT MISSING PREDICATE FEATURES?
│  └─ YES → GAP DETECTED (severity LOW-MED) ⚠️
│
├─ SUBJECT MISSING REQUIRED STANDARD?
│  └─ YES → GAP DETECTED (severity CRITICAL) 🔴
│
├─ SUBJECT CLAIMS NOVEL CAPABILITY?
│  └─ YES → GAP DETECTED (severity HIGH) ⚠️
│
└─ NO GAPS DETECTED → Similar/Equivalent ✅
```

---

## Severity Scoring Quick Reference

### What Gets Scored HIGH (70+)?

- New indications for use (clinical data needed)
- Novel materials not in predicates
- Drug delivery component (new drug)
- Wireless/connectivity features
- AI/ML algorithms
- Extended shelf life claims (>3 years vs predicate)
- New sterilization method
- Software modifications

### What Gets Scored MEDIUM (30-70)?

- Different measurement principle (but comparable accuracy)
- Modified sterilization method (validation needed)
- Software updates (code review needed)
- New hardware interface
- Different test methodology (but same standard)

### What Gets Scored LOW (0-30)?

- UI/UX changes (no functionality change)
- Color or cosmetic changes
- Dimensions within tolerance (±10%)
- Labeling updates
- Packaging changes
- Display format changes
- Optional feature addition

---

## Regulatory Risk Assessment

### FDA Response Likelihood by Severity

```
MAJOR Gap (71-100):
  • Probability of AI request: 80-95%
  • Typical AI timeframe: 2-4 weeks for response
  • Required evidence: New testing or literature
  • Submission impact: May delay until gap closed

MODERATE Gap (31-70):
  • Probability of AI request: 30-60%
  • Can often proceed if well-documented
  • Required evidence: Comparative testing or justification
  • Submission impact: Plan to address in resubmission if needed

MINOR Gap (0-30):
  • Probability of AI request: <5%
  • Usually documentation only
  • Required evidence: Cross-reference or narrative
  • Submission impact: No delay expected
```

---

## Cost & Timeline Estimates

Effort hours by gap type:

```
NEW_INDICATION          600 hrs  (~8 weeks)   Clinical study
NEW_MATERIAL            200 hrs  (~4 weeks)   Biocompatibility
NEW_FEATURE             300 hrs  (~6 weeks)   Validation testing
EXTENDED_SHELF_LIFE     200 hrs  (~8 weeks)   Aging study
MISSING_STANDARD        150 hrs  (~3 weeks)   Standard testing
DIFFERENT_TEST_METHOD    80 hrs  (~2 weeks)   Study design & execution
NEW_WIRELESS             300 hrs  (~6 weeks)   EMC + cybersecurity
MINOR_CHANGES             20 hrs  (<1 week)   Documentation
```

---

## Common Pitfalls & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Too many MAJOR gaps | Poor predicate selection | Re-run with better predicates via `/fda:research` |
| Gap severity seems wrong | Incorrect device template | Verify product code or select template explicitly |
| No testing recommended | Incomplete gap data | Ensure subject device specs complete in device_profile.json |
| AI request anyway despite closure | Gap not properly closed | Verify closure_evidence is FDA-quality |
| Predicate health CAUTION flag | Recalls on predicate | Consider alternative predicate if available |

---

## Files to Review

**Specification:** `PHASE4_GAP_ANALYSIS_SPECIFICATION.md`
- Full technical specification (50+ pages)
- All comparison rules with pseudocode
- 50+ device template definitions
- Output format specifications

**Implementation Guide:** `PHASE4_IMPLEMENTATION_GUIDE.md`
- Architecture & file structure
- Week-by-week development plan
- Code examples & stubs
- Integration checklist

**Quick Reference:** This file
- At-a-glance reference
- Common examples
- Quick decision trees

---

**Version:** 1.0 (Phase 4 Specification)
**Last Updated:** 2026-02-13
**Status:** READY FOR IMPLEMENTATION

