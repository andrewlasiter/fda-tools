# Regulatory Calculation Edge Cases

## Purpose

This document describes known edge cases in the FDA Tools regulatory calculation
logic. These edge cases represent boundary conditions where the behavior of
regulatory rules is non-obvious and could lead to incorrect conclusions if not
properly understood.

**IMPORTANT**: This document is for RESEARCH AND PLANNING purposes only. All
regulatory determinations must be verified by qualified regulatory affairs
professionals before any action is taken.

---

## Edge Case 1: HDE Prevalence Threshold -- Exactly 8,000 Patients

### Regulatory Basis
- **Statute**: Section 520(m)(6)(A) of the FD&C Act
- **Regulation**: 21 CFR 814 Subpart H
- **Threshold**: Fewer than 8,000 individuals per year in the United States

### Edge Case Description

The HDE (Humanitarian Device Exemption) pathway is available ONLY for diseases
or conditions affecting **fewer than** 8,000 individuals per year in the US.
This is a **strict inequality** (`< 8000`), NOT a less-than-or-equal comparison.

### Boundary Behavior

| Estimated Prevalence | HDE Eligible? | Explanation |
|---------------------|---------------|-------------|
| 7,999               | YES           | Strictly less than 8,000 |
| 8,000               | **NO**        | NOT eligible -- equals threshold, not less than |
| 8,001               | NO            | Exceeds threshold |
| 0                   | YES           | Technically eligible (trivially) |
| Negative value      | ERROR         | Invalid input -- prevalence cannot be negative |

### Code Reference

**File**: `plugins/fda-tools/lib/hde_support.py`

```python
# In PrevalenceValidator.validate_prevalence():
result["eligible"] = estimated_prevalence < self.THRESHOLD  # Strict inequality

# In AnnualDistributionReport.generate_report():
"still_eligible": (
    updated_prevalence < HDE_PREVALENCE_THRESHOLD
    if updated_prevalence is not None
    else None
),
```

The constant `HDE_PREVALENCE_THRESHOLD = 8000` is defined at module level.
The comparison uses strict `<` (less than), which correctly implements the
regulatory requirement of "fewer than 8,000."

### Recommendations

1. If your disease/condition affects close to 8,000 patients (within 10% margin),
   prepare additional prevalence documentation as FDA may scrutinize closely.
2. Consider whether the condition definition can be refined to a more specific
   sub-population if prevalence is borderline.
3. Always provide multiple independent prevalence data sources from recognized
   databases (NIH/NCATS GARD, CDC WONDER, NORD, Orphanet).
4. Document the year of prevalence data collection -- FDA may request updates
   for data older than 5 years.

### Common Mistake

Do NOT assume `<= 8000` is the correct comparison. The statute uses the word
"fewer than," which in regulatory and mathematical language means strictly less
than (exclusive of 8,000).

---

## Edge Case 2: IDE 30-Day Review Clock Start Date

### Regulatory Basis
- **Regulation**: 21 CFR 812.30(a)
- **Clock**: 30 calendar days from FDA's "date of receipt"

### Edge Case Description

For Significant Risk (SR) IDE applications, FDA has 30 calendar days to review
the application. The critical edge case is that the 30-day clock starts from
FDA's **date of receipt**, which may differ from:

1. The date the sponsor mails/ships the submission
2. The date shown on the cover letter
3. The date an electronic submission is initiated
4. The date the submission arrives at the FDA mail room

### Boundary Behavior

| Scenario | Clock Start Date | Notes |
|----------|-----------------|-------|
| Electronic submission via eStar | Date FDA system acknowledges receipt | Typically same day or next business day |
| Physical mail delivery | Date FDA mail center logs receipt | May be 1-5 days after mailing |
| FedEx/courier delivery | Date of delivery signature | Trackable, recommended approach |
| Resubmission after RTA hold | Date FDA receives complete resubmission | Clock resets entirely |

### Code Reference

**File**: `plugins/fda-tools/scripts/ide_pathway_support.py`

```python
# In IDESubmissionOutline.generate():
timeline = {
    "fda_review_days": 30,
    "note": "FDA has 30 calendar days to review SR IDE. "
            "Study may begin when IDE is approved.",
}
```

The timeline uses a fixed 30-day value. In practice, the actual elapsed time
depends on when FDA acknowledges receipt.

### Recommendations

1. Always use trackable delivery (FedEx, UPS, or electronic submission) to
   establish a clear date of receipt.
2. If submitting electronically, save the acknowledgment email/confirmation
   with timestamp.
3. Do NOT begin the clinical study until FDA has affirmatively approved the
   IDE or 30 days have elapsed without FDA action (automatic approval).
4. If FDA issues a "Refuse to Accept" (RTA), the clock resets when the
   complete resubmission is received.
5. Calendar days means ALL days including weekends and federal holidays --
   but if day 30 falls on a weekend/holiday, FDA's response may come on the
   next business day.

### Common Mistake

Sponsors sometimes calculate the 30 days from their submission date rather
than FDA's receipt date. This can lead to premature study initiation, which
is a serious regulatory violation.

---

## Edge Case 3: Predicate Rejection Reasons -- Non-Empty String Requirement

### Regulatory Basis
- **Regulation**: 21 CFR 807.92(a)(3) -- Substantial equivalence determination
- **Internal Logic**: Predicate rejection tracking in device profile management

### Edge Case Description

When a predicate device is rejected during the 510(k) preparation process,
the rejection reason must be a **non-empty string**. This is enforced to
maintain data integrity in the audit trail and to support regulatory
reviewers who need to understand why specific predicates were not selected.

### Boundary Behavior

| Rejection Reason | Valid? | Explanation |
|-----------------|--------|-------------|
| `"Different intended use"` | YES | Clear, specific reason |
| `"Recalled device"` | YES | Valid safety-based reason |
| `""` (empty string) | **NO** | Must provide a reason |
| `" "` (whitespace only) | **NO** | Whitespace-only treated as empty after strip |
| `None` | **NO** | Must be a string, not None |
| `"N/A"` | DISCOURAGED | Technically valid but provides no useful information |

### Code Reference

This pattern is enforced across multiple modules:

**File**: `plugins/fda-tools/scripts/input_validators.py`

Input validators ensure that required string fields are non-empty and
properly typed. The pattern of requiring non-empty strings for rejection
reasons follows from the general principle of data integrity validation
per 21 CFR Part 11.

### Recommendations

1. Always provide specific, descriptive rejection reasons (e.g., "Different
   technological characteristics -- predicate uses mechanical valve while
   subject device uses bioprosthetic valve").
2. Include the regulatory basis for rejection when applicable (e.g.,
   "Recalled per FDA recall Z-1234-2025 -- safety concern with lead wire
   fracture").
3. Document the date of rejection and the person who made the determination.
4. If a predicate is reconsidered later, maintain the original rejection
   in the audit trail and add a new acceptance record rather than deleting
   the rejection.

### Common Mistake

Setting rejection reason to an empty string or generic placeholder like
"rejected" -- this provides no actionable information for FDA reviewers
and may be flagged during submission review.

---

## Edge Case 4: PMA Supplement Classification Confidence Thresholds

### Regulatory Basis
- **Regulation**: 21 CFR 814.39 (PMA Supplements)
- **Module**: `pma_supplement_enhanced.py`

### Edge Case Description

The supplement type classifier uses confidence thresholds to categorize
the reliability of its heuristic classification. When confidence falls
near a threshold boundary, small changes in input text can shift the
confidence label.

### Boundary Behavior

| Confidence Score | Confidence Label | Action Recommended |
|-----------------|-----------------|-------------------|
| >= 0.85 | HIGH | Classification likely correct; verify with RA professional |
| >= 0.60, < 0.85 | MEDIUM | Review alternatives; consult RA professional |
| >= 0.40, < 0.60 | LOW | Low reliability; do NOT rely on this classification |
| < 0.40 | VERY_LOW | Essentially unclassifiable; manual RA assessment required |

### Recommendations

1. For MEDIUM or lower confidence, always review the alternative types
   listed in the classification result.
2. A runtime warning is emitted when confidence falls below 50% --
   treat these results as unreliable guidance only.
3. When confidence is LOW or VERY_LOW, consider providing more specific
   change descriptions with explicit keywords (e.g., "sterilization method
   change with validation data" rather than "process update").

---

## Edge Case 5: SR/NSR Determination Score Boundary

### Regulatory Basis
- **Regulation**: 21 CFR 812.3(m) -- Definition of significant risk device
- **Module**: `ide_pathway_support.py`

### Edge Case Description

The SR/NSR (Significant Risk / Non-Significant Risk) determination uses a
threshold score of 60. Devices scoring exactly 60 are classified as
Significant Risk (SR), requiring a full IDE application to FDA.

### Boundary Behavior

| Risk Score | Determination | Regulatory Path |
|-----------|--------------|----------------|
| 59 | NSR (Non-Significant Risk) | IRB approval only; no FDA submission |
| 60 | **SR (Significant Risk)** | Full IDE application to FDA required |
| 61 | SR (Significant Risk) | Full IDE application to FDA required |

### Code Reference

```python
# In SRNSRDetermination.evaluate():
SR_THRESHOLD = 60
is_sr = risk_score >= self.SR_THRESHOLD  # >= means 60 IS significant risk
```

### Recommendations

1. For borderline scores (55-65), document the determination thoroughly and
   consider erring on the side of SR for patient safety.
2. The final SR/NSR determination is made by the sponsor with IRB concurrence --
   this tool provides guidance only.
3. If the IRB disagrees with an NSR determination, the sponsor may request
   a formal FDA determination, which is binding.

---

## Summary Table

| Edge Case | Module | Key Rule | Common Mistake |
|-----------|--------|----------|---------------|
| HDE prevalence | `hde_support.py` | Strict `< 8000` (not `<=`) | Using `<= 8000` |
| IDE 30-day clock | `ide_pathway_support.py` | Starts at FDA receipt date | Counting from submission date |
| Predicate rejection | `input_validators.py` | Reason must be non-empty string | Empty string or None |
| PMA supplement confidence | `pma_supplement_enhanced.py` | Thresholds: 0.85/0.60/0.40 | Relying on LOW confidence |
| SR/NSR threshold | `ide_pathway_support.py` | Score >= 60 is SR | Assuming 60 is NSR |

---

*Document version: 1.0.0*
*Last updated: 2026-02-18*
*Status: RESEARCH USE ONLY -- Not for direct FDA submission use*
