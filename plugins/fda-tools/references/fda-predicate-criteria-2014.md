# FDA Predicate Selection Criteria (2014)

Extracted from FDA's "The 510(k) Program: Evaluating Substantial Equivalence in Premarket Notifications (2014)"
**Section IV.B: Selection of Appropriate Predicates**

## Required Criteria Checklist

Per FDA SE Guidance, a valid predicate device **MUST** meet ALL of the following criteria:

### 1. Legally Marketed Status
- ✓ Predicate is legally marketed in the United States
- ✓ Not withdrawn from market
- ✓ Not subject to enforcement action prohibiting marketing

**Verification:**
- Check openFDA device enforcement API for withdrawal/prohibition
- Verify no active consent decree or injunction against applicant

### 2. Regulatory Pathway
- ✓ Predicate was cleared under 510(k) process
- ✗ NOT cleared via:
  - PMA (Premarket Approval) - P-numbers
  - HDE (Humanitarian Device Exemption) - H-numbers
  - Exempt from 510(k) (unless explicitly cited in guidance)

**Verification:**
- K-numbers are valid 510(k) clearances
- P-numbers and H-numbers cannot serve as predicates
- De Novo devices (DEN) CAN serve as predicates after clearance

### 3. Not Recalled or Found NSE
- ✓ Predicate has not been recalled (Class I, II, or III)
- ✓ Predicate clearance not rescinded
- ✓ Not found Not Substantially Equivalent (NSE) in subsequent review

**Verification:**
- Check openFDA device recall API
- Search decision descriptions for "NSE", "DENG" (denied), "withdrawn"

### 4. Same Intended Use
- ✓ Predicate has the same intended use as subject device
- ✓ Indications for Use (IFU) are identical OR subject IFU is narrower subset

**FDA Interpretation:**
"Intended use refers to the objective intent of the persons legally responsible for the labeling of devices." (21 CFR 801.4)

**Examples:**
- ✓ Valid: Subject treats diabetic foot ulcers → Predicate treats chronic wounds (subset)
- ✗ Invalid: Subject treats pressure ulcers → Predicate treats burns (different indication)

### 5. Same OR Similar Technological Characteristics

**Option A: Same Technological Characteristics**
- Materials are the same
- Design principles are the same
- Energy source is the same
- Operating principles are the same

**Option B: Different Technological Characteristics with Equivalent Performance/Safety**
- IF technological characteristics differ, THEN:
  - Subject device must demonstrate equivalent performance
  - Subject device must demonstrate equivalent safety
  - May require clinical data per Section VII

---

## Additional Considerations (Best Practices)

While not FDA requirements, these factors strengthen predicate selection:

### Predicate Age
- **Preferred:** Cleared within last 10 years (current technology)
- **Acceptable:** 10-20 years if well-established
- **Caution:** >20 years (may not represent current state of the art)

### Predicate Chain Depth
- **Preferred:** 1-2 generations from original clearance
- **Caution:** >5 generations (long predicate chains may have drifted)

### Predicate Applicant
- **Advantage:** Same applicant = product line continuity
- **Neutral:** Different applicant (no disadvantage)

### Predicate Summary Availability
- **Preferred:** Summary available (provides testing details)
- **Acceptable:** Statement only (less detail but still valid)

### Product Code Match
- **Required:** Same product code OR same advisory panel
- **Acceptable with justification:** Adjacent product code with same intended use

---

## FDA Citations

### Primary Guidance
**"The 510(k) Program: Evaluating Substantial Equivalence in Premarket Notifications"**
FDA Guidance Document (2014)
https://www.fda.gov/regulatory-information/search-fda-guidance-documents/510k-program-evaluating-substantial-equivalence-premarket-notifications-510k

**Section IV.B:** Selection of Appropriate Predicates (pages 14-17)

### Supporting Regulations
**21 CFR 807.92:** Definition of Substantial Equivalence
**21 CFR 807.95:** Procedures for submitting a 510(k)
**21 CFR 801.4:** Definition of intended use

### FDA Memoranda
**"Deciding When to Submit a 510(k) for a Change to an Existing Device" (2017)**
Discusses predicate acceptability when device changes

**"Refuse to Accept Policy for 510(k)s" (2019)**
RTA Checklist includes predicate verification

---

## Automated Compliance Check Algorithm

Use this decision tree to verify predicate compliance:

```
1. Is device legally marketed? (check enforcement API)
   NO → REJECT (not valid predicate)
   YES → continue

2. Was device cleared via 510(k)? (check K-number format)
   NO (P-number, H-number) → REJECT
   YES → continue

3. Has device been recalled? (check recall API)
   Class I recall → REJECT
   Class II/III recall → FLAG for review
   NO recall → continue

4. Does predicate have same intended use? (compare IFU text)
   NO → REJECT
   YES or SUBSET → continue

5. Same technological characteristics? (compare device description)
   YES → ACCEPT
   NO → FLAG (may require clinical data per Section VII)
```

**Output:**
- `COMPLIANT` — All criteria met
- `REVIEW_REQUIRED` — Criteria met with caveats (Class II recall, old, different tech)
- `NOT_COMPLIANT` — Failed required criteria (withdrawn, NSE, different IFU)

---

## Integration with Review Workflow

This checklist should be applied in `review.md` during predicate validation:

```python
def check_fda_predicate_criteria(k_number, subject_device_ifu, subject_device_product_code):
    """
    Verify predicate meets FDA selection criteria per 2014 guidance.

    Returns: {
        'compliant': bool,
        'flags': [issues],
        'rationale': str,
        'citation': '510(k) Program (2014) Section IV.B'
    }
    """
    flags = []

    # Check 1: Legally marketed (510k_validation API)
    # Check 2: Not recalled (recall API)
    # Check 3: Not NSE (decision_description check)
    # Check 4: Same IFU (keyword overlap >70%)
    # Check 5: Same product code (classification API)

    if len(flags) == 0:
        return {'compliant': True, 'rationale': 'All FDA criteria met per 510(k) Program guidance (2014)'}
    else:
        return {'compliant': False, 'flags': flags}
```

---

## RA Professional Notes

**When to Escalate to RA Advisor:**
- Borderline IFU match (<70% keyword overlap)
- Predicate with Class II recall
- Predicate from different product code
- Long predicate chain (>5 generations)
- Technological characteristics differ

**Documentation Requirements:**
- Predicate selection rationale MUST be documented in submission
- If predicate has limitations (old, recalled, different tech), address in SE discussion
- Consider Pre-Submission meeting if predicate defensibility is uncertain

---

**Last Updated:** 2026-02-13
**Source:** FDA Guidance "The 510(k) Program" (2014), 21 CFR 807
**Maintained By:** FDA Predicate Assistant Plugin
