# RTA (Refuse to Accept) Checklist Reference

The Refuse to Accept (RTA) policy is the #1 procedural failure reason for 510(k) submissions. FDA screens every submission for administrative and content completeness before substantive review begins. Submissions that fail the RTA checklist are returned without review.

**FDA Guidance:** "Refuse to Accept Policy for 510(k)s" (current version at fda.gov)

## Administrative Completeness Criteria

These items are checked before any scientific review. Missing any one can trigger an RTA.

| Item | Requirement | eSTAR Section | Common Failure |
|------|-------------|---------------|----------------|
| Cover letter | Identifies submission type, device, and contact | 01 | Missing contact information |
| FDA Form 3514 | CDRH Premarket Review Submission Cover Sheet, fully completed | 02 | Incomplete fields, wrong form version |
| User fee payment | MDUFA fee paid or valid small business waiver | N/A | Fee not submitted before or with application |
| 510(k) Summary OR Statement | One is required per 21 CFR 807.92/807.93 | 03 | Missing entirely; both included (choose one) |
| Truthful and Accuracy Statement | Signed statement per 21 CFR 807.87(l) | 04 | Unsigned, wrong signatory, missing date |
| Financial Certification/Disclosure | Per 21 CFR 54 for any clinical data | 05 | Omitted when clinical data is included |
| Indications for Use (Form FDA 3881) | Completed form with IFU text | 09 | Missing form; IFU in narrative but not on form |
| eSTAR format | Mandatory for submissions received on/after Oct 1, 2023 | All | Non-eSTAR submission format |

## Content Completeness Criteria

### Device Description (eSTAR Section 06)
- [ ] Physical description of the device
- [ ] Principle of operation
- [ ] Materials of construction (patient-contacting)
- [ ] Key performance specifications
- [ ] Photographs or diagrams
- [ ] Accessories and components listed
- **Common RTA reason:** Description too vague to assess; missing material characterization

### Substantial Equivalence Comparison (eSTAR Section 07)
- [ ] Predicate device identified by K-number
- [ ] Predicate is legally marketed (not pending, not withdrawn)
- [ ] Side-by-side comparison table (subject vs. predicate)
- [ ] Intended use comparison
- [ ] Technological characteristics comparison
- [ ] Discussion of differences with justification
- [ ] Clear SE conclusion statement
- **Common RTA reason:** No comparison table; predicate not legally marketed; no discussion of differences

### Proposed Labeling (eSTAR Section 09)
- [ ] Indications for Use statement (Form FDA 3881)
- [ ] Instructions for Use (IFU) — draft or final
- [ ] Device labels (package labels, device labels)
- [ ] Patient labeling (if applicable)
- [ ] Warnings and precautions
- **Common RTA reason:** No IFU provided; labeling contradicts stated intended use

### Performance Data (eSTAR Section 15)
- [ ] Testing appropriate for the device type and identified risks
- [ ] Test protocols with acceptance criteria
- [ ] Test results addressing identified risks
- [ ] Standards referenced with version numbers
- **Common RTA reason:** No performance data at all; testing does not address identified technological differences

### Software Documentation (eSTAR Section 13, if applicable)
- [ ] Software documentation level stated (Basic or Enhanced)
- [ ] Software description
- [ ] Hazard analysis
- [ ] V&V documentation appropriate to documentation level
- [ ] Cybersecurity documentation (if device has connectivity)
- **Common RTA reason:** Missing cybersecurity docs for connected device; no documentation level stated

### Biocompatibility (eSTAR Section 12, if applicable)
- [ ] Contact type and duration identified
- [ ] ISO 10993-1 evaluation plan or rationale for biocompatibility
- [ ] Test results or equivalence argument for patient-contacting materials
- **Common RTA reason:** No biocompatibility rationale for patient-contacting device

### Sterilization (eSTAR Section 10, if applicable)
- [ ] Sterilization method identified
- [ ] Validation reference or plan
- [ ] SAL stated (typically 10^-6)
- **Common RTA reason:** Device labeled sterile but no sterilization information provided

## Common RTA Rejection Reasons with Solutions

| Rejection Reason | Frequency | Solution |
|-----------------|-----------|----------|
| Missing or incomplete Form 3514 | Very common | Use latest version; fill all fields; double-check applicant info |
| No predicate comparison table | Common | Always include side-by-side table even if devices are very similar |
| Missing IFU | Common | Include at least a draft IFU; ensure it matches stated intended use |
| Wrong submission format (non-eSTAR) | Common (post-Oct 2023) | Use current eSTAR PDF form from FDA website |
| Fee not paid | Common | Submit MDUFA fee before or concurrently with application |
| No performance data | Moderate | Include at least summary test results; explain if relying on predicate precedent |
| Missing cybersecurity documentation | Increasing | Include for any device with software, connectivity, or data exchange |
| Predicate not legally marketed | Moderate | Verify predicate status in FDA database before submission |
| Labeling inconsistent with IFU | Moderate | Cross-check all labeling against Form 3881 and device description |

## Pre-Submission RTA Prevention Checklist

Run this checklist before submitting to catch RTA issues:

1. **Form check**: All required FDA forms completed, signed, dated, current version
2. **Fee check**: MDUFA fee paid or small business determination letter available
3. **Format check**: Submission in eSTAR format with correct section numbering
4. **Predicate check**: Verify predicate K-number is currently legally marketed (not recalled/withdrawn)
5. **IFU check**: Form 3881 IFU text matches IFU document matches device description
6. **Comparison check**: SE comparison table present with all technological characteristics addressed
7. **Testing check**: Performance data addresses all identified technological differences
8. **Labeling check**: All required labeling elements present and internally consistent
9. **Software check**: If device contains software, documentation level stated and appropriate docs included
10. **Cybersecurity check**: If device has any connectivity, cybersecurity documentation included

## Cross-Reference to eSTAR Sections

| RTA Criterion | eSTAR Section(s) | Plugin Command |
|--------------|-------------------|----------------|
| Administrative forms | 01, 02, 04, 05 | `/fda:assemble` generates templates |
| Device description | 06 | `/fda:draft device-description` |
| SE comparison | 07 | `/fda:compare-se` |
| Labeling | 09 | Manual — company-specific |
| Performance data | 15 | `/fda:test-plan` identifies needed tests |
| Software/cyber | 13 | `/fda:assemble` auto-detects need |
| Biocompatibility | 12 | `/fda:guidance` identifies requirements |
| Sterilization | 10 | `/fda:guidance` identifies requirements |

## FDA RTA Guidance Reference

- **Guidance document:** "Refuse to Accept Policy for 510(k)s" — available at fda.gov/medical-devices
- **RTA decision process:** FDA makes RTA determination within 15 business days of receipt
- **RTA response:** If RTA'd, applicant can either resubmit with corrections or request supervisory review of the RTA decision
- **Impact:** RTA restarts the review clock — the original submission date is not preserved
