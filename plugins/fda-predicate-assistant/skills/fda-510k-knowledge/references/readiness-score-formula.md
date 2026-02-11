# Submission Readiness Index (SRI) Formula

Canonical 0-100 scoring formula for assessing 510(k) submission package completeness. Single source of truth for readiness scoring across `/fda:export`, `/fda:pre-check`, `submission-writer` agent, and `review-simulator` agent.

## Formula Overview

```
SRI = Mandatory_Section_Score + Optional_Section_Bonus + Consistency_Score - Penalties
```

**Range**: 0-100 (penalties can reduce below zero, clamped to 0)

---

## Component 1: Mandatory Section Score (50 points)

Seven sections required for every 510(k) submission, weighted by their impact on Refuse-to-Accept (RTA) screening.

| # | Section | Weight | File Check | RTA Impact |
|---|---------|--------|------------|------------|
| 01 | Cover Letter | 5 | `draft_cover-letter.md` | Administrative RTA |
| 03 | 510(k) Summary | 8 | `draft_510k-summary.md` | Content RTA |
| 06 | Device Description | 10 | `draft_device-description.md` | Core SE argument |
| 07 | SE Discussion | 10 | `draft_se-discussion.md` or `se_comparison.md` | Core SE argument |
| 09 | Labeling | 7 | `draft_labeling.md` | Content RTA |
| 15 | Performance Testing | 7 | `draft_performance-summary.md` or `test_plan.md` | Content RTA |
| IFU | Indications for Use | 3 | Form 3881 text in `review.json` or `import_data.json` | Administrative RTA |

**Scoring per section:**
- **Present with content** (>200 words or structured data): Full points
- **Template only** (has `[TODO:]` items but <200 words of substantive content): 50% of points
- **Missing**: 0 points

```
Mandatory_Score = sum(section_weight * section_completeness for each mandatory section)
```

Where `section_completeness` ∈ {0, 0.5, 1.0}

---

## Component 2: Optional Section Bonus (15 points)

Up to 10 optional sections, each worth 1.5 points, scaled to the number applicable for this device.

| # | Section | Applicable When |
|---|---------|----------------|
| 04 | Truthful & Accuracy | Always (template) |
| 05 | Financial Certification | Clinical data submitted |
| 08 | Standards | Recognized standards apply |
| 10 | Sterilization | Device labeled sterile |
| 11 | Shelf Life | Shelf life claim |
| 12 | Biocompatibility | Patient-contacting or implantable |
| 13 | Software | Has software component |
| 14 | EMC/Electrical Safety | Electrically powered |
| 16 | Clinical | Clinical data or literature |
| 17 | Human Factors | User interface or home use |

**Scoring:**
```
applicable_count = count of sections applicable to this device type
present_count = count of applicable sections with content

Optional_Bonus = (present_count / applicable_count) * 15
```

If `applicable_count` is 0, `Optional_Bonus` = 15 (no optional sections needed = full credit).

---

## Component 3: Consistency Check Score (25 points)

Eleven cross-document consistency checks from `/fda:consistency`, weighted by severity.

| # | Check | Severity | Weight | Description |
|---|-------|----------|--------|-------------|
| 1 | Product Code | CRITICAL | 4 | Same product code across all files |
| 2 | Predicate List | CRITICAL | 4 | K-numbers match review.json everywhere |
| 3 | Intended Use | CRITICAL | 4 | IFU text identical across sections |
| 4 | Device Description | HIGH | 2 | Physical description consistent |
| 5 | Pathway | HIGH | 2 | 510(k) type consistent (Traditional/Special/Abbreviated) |
| 6 | Placeholder Scan | HIGH | 2 | No `[INSERT]`, `[COMPANY]`, `[DATE]` placeholders |
| 7 | Cross-Section Draft | HIGH | 2 | Section cross-references resolve |
| 8 | Section Map | HIGH | 2 | eSTAR section numbers match content |
| 9 | Standards | MEDIUM | 1 | Standard numbers/versions consistent |
| 10 | Dates/Freshness | LOW | 1 | All referenced dates current |
| 11 | Import Alignment | MEDIUM | 1 | Imported eSTAR data matches drafts |

**Total available**: 25 points (4+4+4+2+2+2+2+2+1+1+1)

**Scoring:**
```
Consistency_Score = sum(check_weight for each PASSING check)
```

If consistency checks haven't been run, default to 12.5 (50% of maximum — assume moderate compliance).

---

## Component 4: Penalties (deductions)

Penalties reduce the score for known quality issues in drafted content.

| Issue | Penalty per Instance | Cap | Detection |
|-------|---------------------|-----|-----------|
| `[TODO:]` items | -0.5 | -10 | Grep across all `draft_*.md` |
| `[CITATION NEEDED]` items | -1.0 | -10 | Grep across all `draft_*.md` |
| `[INSERT ...]` placeholders | -2.0 | -10 | Grep across all `draft_*.md` |

```
Penalties = min(10, todo_count * 0.5) + min(10, citation_count * 1.0) + min(10, insert_count * 2.0)
```

**Maximum total penalty**: -30 points

---

## Final Score

```
SRI = max(0, Mandatory_Score + Optional_Bonus + Consistency_Score - Penalties)
```

Clamped to range [0, 100]. In practice, a perfect score requires all mandatory sections complete, all applicable optional sections present, all 11 consistency checks passing, and zero TODO/CITATION/INSERT items.

---

## Tier Definitions

| Score Range | Tier | Label | Meaning |
|-------------|------|-------|---------|
| 85-100 | 1 | **Ready** | Submission package is complete — proceed to final human review |
| 70-84 | 2 | **Nearly Ready** | Minor gaps remain — address TODOs and re-run consistency checks |
| 50-69 | 3 | **Significant Gaps** | Multiple sections incomplete or consistency failures |
| 30-49 | 4 | **Not Ready** | Major sections missing — return to drafting phase |
| 0-29 | 5 | **Early Stage** | Minimal content — data collection and analysis needed first |

---

## Display Format

Always display SRI with tier label to prevent confusion with PCS (Predicate Confidence Score):

```
SRI: 78/100 — Nearly Ready
```

Never display as just a number. Always include "SRI:" prefix and tier label.

---

## Score Disambiguation

| Attribute | SRI (Submission Readiness Index) | PCS (Predicate Confidence Score) |
|-----------|--------------------------------|--------------------------------|
| **What** | Submission package completeness | Predicate extraction accuracy |
| **Range** | 0-100 | 0-100 base + 20 bonus |
| **Used by** | export, pre-check, submission-writer, review-simulator | review, propose, research |
| **Canonical definition** | This file | `references/confidence-scoring.md` |
