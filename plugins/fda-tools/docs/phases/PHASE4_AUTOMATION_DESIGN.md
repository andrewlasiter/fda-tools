# Phase 4: Automation Design Specification

**Project:** FDA API Enrichment - Phase 4 Automation
**Version:** 1.0
**Date:** February 13, 2026
**Estimated Implementation:** 6 hours
**Status:** Design Complete - Awaiting Approval

---

## Executive Summary

Phase 4 delivers **conservative, transparent automation** that augments RA professionals' decision-making without replacing their expert judgment. The two automation features—**Automated Gap Analysis** and **Smart Predicate Recommendations**—are designed with regulatory submission zero-tolerance requirements in mind.

### Design Philosophy

1. **Conservative over risky** - When uncertain, flag for human review
2. **Transparent reasoning** - Show decision logic, not just recommendations
3. **Confidence-scored** - Every recommendation includes HIGH/MEDIUM/LOW confidence
4. **Fail-safe defaults** - Automation failures result in informative warnings, not crashes
5. **Audit trail** - Every automated decision logged with full provenance
6. **Human-in-the-loop** - Critical checkpoints require RA professional confirmation

### Value Proposition

**Time Savings:**
- Gap analysis: 3-4 hours → 15 minutes (85% reduction)
- Predicate selection: 6-8 hours → 30 minutes (90% reduction)
- **Total per project:** 9-12 hours → 45 minutes (94% reduction)

**Quality Improvements:**
- Systematic gap detection (no missed requirements)
- Data-driven predicate ranking (objective scoring)
- Consistency across projects (standardized criteria)

**Risk Mitigation:**
- Prominently flags uncertainty (LOW confidence = manual review required)
- Conservative thresholds (HIGH confidence ≥90%, MEDIUM ≥70%)
- Explicit limitations documented in every output

---

## Feature 1: Automated Gap Analysis

### 1.1 Feature Specification

#### User Value Proposition

**Manual Process (3-4 hours):**
1. Compare subject device specs to predicate specs (30-60 min)
2. Identify missing data fields in project files (15-30 min)
3. Review predicate testing sections from PDFs (60-90 min)
4. Cross-check required standards vs declared standards (30-45 min)
5. Identify weak predicates (poor SE comparison) (45-60 min)
6. Document all gaps in structured format (15-30 min)

**Automated Process (15 minutes):**
1. Run gap analysis command (2 min)
2. Review automated gap report with priority flags (8 min)
3. Validate HIGH priority gaps and assign remediation (5 min)

**What Automation Eliminates:**
- Manual field-by-field comparison
- PDF text searching for testing sections
- Standards cross-referencing
- Weak predicate identification
- Gap documentation formatting

#### Input Requirements

**Triggers Automation:**
- User runs `/fda:auto-gap-analysis` OR
- User runs `/fda:batchfetch --enrich --gap-analysis` (integrated mode)

**Required Data (from existing project):**
```
~/fda-510k-data/projects/{PROJECT_NAME}/
├── device_profile.json         # Subject device specs
├── 510k_download_enriched.csv  # Predicate data with enrichment
├── se_comparison.md (optional) # Existing SE comparison table
├── standards_lookup.json (opt) # Declared standards list
└── review.json (optional)      # Accepted predicates
```

**Minimum Viable Data:**
- At least 1 predicate device in CSV
- Subject device profile (can be minimal - gaps will be flagged)

#### Output Format

**Primary Output:** `gap_analysis_report.md` (Markdown)

**Structure:**
```markdown
# Automated Gap Analysis Report

## Executive Summary
- Total gaps identified: 12
- HIGH priority (blocking issues): 3
- MEDIUM priority (recommended): 6
- LOW priority (optional): 3
- Automation confidence: 87% (HIGH)

## Gap Categories
### 1. Missing Subject Device Data (3 gaps)
### 2. Weak Predicate Choices (2 gaps)
### 3. Testing Gaps (4 gaps)
### 4. Standards Gaps (3 gaps)

## Recommended Actions (Priority Order)
1. [HIGH] Obtain subject device sterilization method
2. [HIGH] Replace predicate K234567 (2 recalls)
3. [MEDIUM] Add biocompatibility test data
...

## Automation Metadata
- Analysis timestamp
- Confidence score
- Data sources
- Human review checkpoints
```

**Secondary Outputs:**
- `gap_analysis_data.json` - Machine-readable gap data
- Appended to `enrichment_metadata.json` - Audit trail

#### Decision Confidence

**Confidence Scoring Methodology:**

```python
def calculate_gap_analysis_confidence(gaps: List[Gap]) -> Dict[str, Any]:
    """
    Calculate overall confidence in automated gap detection.

    Confidence Factors:
    1. Data completeness (40%) - % of expected fields populated
    2. Predicate quality (30%) - Enrichment scores of predicates
    3. Gap clarity (20%) - % of gaps with unambiguous detection
    4. Cross-validation (10%) - % of gaps confirmed by multiple checks
    """

    # Data completeness score
    expected_fields = ['device_name', 'indications', 'technological_characteristics',
                       'sterilization', 'materials', 'predicates']
    populated = count_populated_fields(device_profile, expected_fields)
    completeness_score = (populated / len(expected_fields)) * 40

    # Predicate quality score
    avg_enrichment_score = mean([p['enrichment_completeness_score']
                                 for p in predicates])
    quality_score = (avg_enrichment_score / 100) * 30

    # Gap clarity score (can we definitively say it's a gap?)
    clear_gaps = count_clear_gaps(gaps)  # Gaps with definitive evidence
    clarity_score = (clear_gaps / len(gaps)) * 20 if gaps else 20

    # Cross-validation score
    cross_validated = count_cross_validated_gaps(gaps)
    validation_score = (cross_validated / len(gaps)) * 10 if gaps else 10

    confidence_pct = completeness_score + quality_score + clarity_score + validation_score

    if confidence_pct >= 90:
        confidence = "HIGH"
        recommendation = "Gap analysis ready for RA professional review"
    elif confidence_pct >= 70:
        confidence = "MEDIUM"
        recommendation = "Review flagged gaps; some may need manual verification"
    else:
        confidence = "LOW"
        recommendation = "MANUAL GAP ANALYSIS REQUIRED - Automated analysis unreliable"

    return {
        'confidence_percentage': round(confidence_pct, 1),
        'confidence_level': confidence,
        'recommendation': recommendation,
        'factors': {
            'data_completeness': round(completeness_score, 1),
            'predicate_quality': round(quality_score, 1),
            'gap_clarity': round(clarity_score, 1),
            'cross_validation': round(validation_score, 1)
        }
    }
```

**Confidence Thresholds:**
- **HIGH (≥90%):** Gap analysis trustworthy, proceed with remediation
- **MEDIUM (70-89%):** Review flagged gaps, manual verification of ambiguous gaps
- **LOW (<70%):** Manual gap analysis required, automation unreliable

### 1.2 Automation Logic

#### Gap Detection Decision Tree

```
START: Load project data
  │
  ├─→ Check data completeness
  │   ├─ device_profile.json exists? → YES: Continue | NO: CRITICAL GAP
  │   ├─ predicates CSV exists? → YES: Continue | NO: CRITICAL GAP
  │   └─ Confidence threshold: ≥50% fields populated
  │
  ├─→ CATEGORY 1: Missing Subject Device Data
  │   │
  │   ├─ Scan device_profile.json for empty/null fields
  │   ├─ Priority assignment:
  │   │   ├─ HIGH: indications, technological_characteristics, materials
  │   │   ├─ MEDIUM: sterilization, shelf_life, intended_users
  │   │   └─ LOW: optional marketing fields
  │   │
  │   └─ For each gap:
  │       ├─ Check if predicate has this data → suggest sourcing strategy
  │       ├─ Confidence: HIGH (definitive - field is empty)
  │       └─ Remediation: "Obtain from design docs / technical file"
  │
  ├─→ CATEGORY 2: Weak Predicate Choices
  │   │
  │   ├─ Load predicate enrichment data from CSV
  │   ├─ Apply predicate quality filters:
  │   │   ├─ Recalls: ≥2 recalls → HIGH priority gap (NOT_RECOMMENDED)
  │   │   ├─ Clearance age: >15 years → MEDIUM priority gap (REVIEW_REQUIRED)
  │   │   ├─ MAUDE trending: "increasing" + high count → MEDIUM priority gap
  │   │   └─ Enrichment score: <60 → LOW priority (data quality issue)
  │   │
  │   ├─ Cross-check with se_comparison.md:
  │   │   ├─ Parse "Differences" column
  │   │   ├─ Count # of differences per predicate
  │   │   ├─ If ≥5 differences → MEDIUM priority gap (weak SE)
  │   │   └─ Confidence: MEDIUM (requires SE judgment)
  │   │
  │   └─ For each weak predicate:
  │       ├─ Provide specific reason (recall count, age, differences)
  │       ├─ Suggest alternatives from same product code
  │       └─ Confidence: HIGH for recall-based, MEDIUM for SE-based
  │
  ├─→ CATEGORY 3: Testing Gaps
  │   │
  │   ├─ Load standards_lookup.json (if exists)
  │   ├─ Identify applicable testing from:
  │   │   ├─ Predicate PDF extracted sections (biocompatibility, electrical, etc.)
  │   │   ├─ Device characteristics (sterile? → sterilization validation)
  │   │   ├─ Product code guidance (special controls)
  │   │   └─ Enrichment clinical indicators (clinical study needed?)
  │   │
  │   ├─ Cross-check declared vs expected testing:
  │   │   ├─ Expected: Parse predicate testing sections
  │   │   ├─ Declared: Check project files for test data/reports
  │   │   └─ Gap = Expected AND NOT Declared
  │   │
  │   ├─ Priority assignment:
  │   │   ├─ HIGH: Safety-critical (biocompatibility, electrical safety)
  │   │   ├─ MEDIUM: Performance (shelf life, human factors)
  │   │   └─ LOW: Optional (usability, packaging)
  │   │
  │   └─ For each testing gap:
  │       ├─ Source: Which predicate required this test
  │       ├─ Standard reference: ISO/IEC number (if known)
  │       ├─ Confidence: MEDIUM (requires technical judgment)
  │       └─ Remediation: "Conduct [test] per [standard]"
  │
  ├─→ CATEGORY 4: Standards Gaps
  │   │
  │   ├─ Load device-specific standards from FDA Recognized DB
  │   │   (via product code + device characteristics)
  │   ├─ Compare to standards_lookup.json (declared standards)
  │   ├─ Gap = Required AND NOT Declared
  │   │
  │   ├─ Priority assignment:
  │   │   ├─ HIGH: Consensus standards in special controls
  │   │   ├─ MEDIUM: Common standards for device type (biocompat, electrical)
  │   │   └─ LOW: Optional/informational standards
  │   │
  │   └─ For each standards gap:
  │       ├─ Standard number and title
  │       ├─ Why required (predicate used? special controls?)
  │       ├─ Confidence: MEDIUM (judgment needed)
  │       └─ Remediation: "Add to test plan, conduct testing"
  │
  └─→ GENERATE REPORT
      │
      ├─ Calculate overall confidence score
      ├─ Rank gaps by priority (HIGH → MEDIUM → LOW)
      ├─ Add human review checkpoints:
      │   ├─ "Review all HIGH priority gaps before submission"
      │   ├─ "Validate MEDIUM confidence gaps with RA professional"
      │   └─ "Consider LOW priority gaps if time permits"
      │
      ├─ Generate actionable recommendations:
      │   ├─ What to do (specific action)
      │   ├─ Why (gap rationale)
      │   ├─ How (suggested approach)
      │   └─ When (priority timeline)
      │
      └─ Output gap_analysis_report.md + gap_analysis_data.json
```

#### Human-in-the-Loop Checkpoints

**Checkpoint 1: Pre-Analysis Validation (AUTOMATED)**
- System checks: Do we have minimum viable data?
- If NO: Abort with clear message "Cannot perform gap analysis - missing device_profile.json"
- If YES: Proceed

**Checkpoint 2: Confidence Gate (AUTOMATED)**
- If overall confidence < 70%: Add prominent banner
  ```
  ⚠️ LOW CONFIDENCE ANALYSIS
  Automated gap detection unreliable due to sparse data.
  MANUAL GAP ANALYSIS REQUIRED by RA professional.
  Use this report as starting point only.
  ```

**Checkpoint 3: High-Priority Gap Review (MANUAL)**
- User MUST review all HIGH priority gaps before submission
- Report includes checkbox: `[ ] All HIGH priority gaps reviewed and addressed`

**Checkpoint 4: Weak Predicate Confirmation (MANUAL if flagged)**
- If any predicate flagged as weak, user must:
  - Confirm predicate replacement OR
  - Provide justification for keeping predicate
- Report includes: `[ ] Weak predicates reviewed: [Replace/Keep + rationale]`

#### Fallback Strategies

**Fallback 1: Missing Subject Device Data**
```python
if device_profile is None or device_profile == {}:
    return {
        'category': 'CRITICAL_ERROR',
        'message': 'Cannot perform gap analysis without device_profile.json',
        'remediation': 'Run /fda:seed or manually create device_profile.json',
        'confidence': 'N/A'
    }
```

**Fallback 2: No Predicates Found**
```python
if len(predicates) == 0:
    return {
        'category': 'CRITICAL_ERROR',
        'message': 'Cannot perform gap analysis without predicates',
        'remediation': 'Run /fda:batchfetch to identify predicates OR manually add to review.json',
        'confidence': 'N/A'
    }
```

**Fallback 3: Cannot Parse SE Comparison**
```python
if se_comparison_parse_error:
    # Fallback: Use basic spec comparison
    logger.warning("Could not parse se_comparison.md - using basic comparison")
    gaps.append({
        'category': 'Weak Predicate Detection',
        'priority': 'LOW',
        'message': 'Could not assess SE strength - manual review of se_comparison.md required',
        'confidence': 'LOW'
    })
```

**Fallback 4: Standards Database Unavailable**
```python
if fda_standards_db_error:
    # Fallback: Use predicate standards only
    logger.warning("FDA standards DB unavailable - using predicate standards only")
    gaps.append({
        'category': 'Standards Gaps',
        'priority': 'MEDIUM',
        'message': 'Could not access FDA standards DB - verify standards list manually',
        'confidence': 'LOW',
        'remediation': 'Visit https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/search.cfm'
    })
```

**Fallback 5: Edge Case - All Data Perfect**
```python
if len(gaps) == 0:
    return {
        'summary': 'No gaps detected',
        'confidence': calculate_confidence(device_profile, predicates),
        'note': 'Zero gaps may indicate insufficient gap detection coverage. Manual review recommended.',
        'human_review_required': True
    }
```

### 1.3 Implementation Plan

#### Time Estimate: 3 hours

**Hour 1: Core Gap Detection Logic (60 min)**
- Implement 4 gap detection functions:
  - `detect_missing_device_data()` - 15 min
  - `detect_weak_predicates()` - 20 min
  - `detect_testing_gaps()` - 15 min
  - `detect_standards_gaps()` - 10 min

**Hour 2: Confidence Scoring & Report Generation (60 min)**
- Implement `calculate_gap_analysis_confidence()` - 15 min
- Implement `generate_gap_analysis_report()` - 25 min
- Implement `write_gap_data_json()` - 10 min
- Add audit trail to `enrichment_metadata.json` - 10 min

**Hour 3: Integration & Testing (60 min)**
- Add `/fda:auto-gap-analysis` command handler - 10 min
- Add `--gap-analysis` flag to batchfetch - 10 min
- Write 6 test cases (pytest) - 30 min
- Document in user guide - 10 min

#### Dependencies

**Phase 1 & 2 (COMPLETE):**
- ✅ Enrichment data structure (`enrichment_completeness_score`, `predicate_acceptability`)
- ✅ Provenance tracking (`enrichment_metadata.json`)
- ✅ Standards intelligence (removed but FDA DB URLs available)

**Existing Data Files:**
- ✅ `device_profile.json` - Subject device specs
- ✅ `510k_download_enriched.csv` - Predicate enrichment data
- ⚠️ `se_comparison.md` - Optional, fallback if missing
- ⚠️ `standards_lookup.json` - Optional, fallback if missing

**External Resources:**
- ⚠️ FDA Recognized Standards Database (web query) - Fallback to predicate standards if unavailable
- ✅ No new API dependencies

#### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **False Positive Gaps** (flags non-gap as gap) | MEDIUM | MEDIUM | Conservative thresholds, manual review checkpoints |
| **False Negative Gaps** (misses real gap) | LOW | HIGH | Cross-validation, MEDIUM confidence = manual check |
| **Predicate PDF Parsing Errors** | MEDIUM | LOW | Fallback to basic comparison, log parsing failures |
| **Standards DB Unavailable** | LOW | MEDIUM | Fallback to predicate standards, add manual review note |
| **User Misinterprets LOW Confidence** | HIGH | HIGH | Prominent banner, explicit "MANUAL REVIEW REQUIRED" |
| **Automation Overrides RA Judgment** | LOW | CRITICAL | Human checkboxes, audit trail, no auto-remediation |

**Critical Risk: User bypasses manual review of LOW confidence analysis**

**Mitigation:**
1. Require manual checkbox confirmation for HIGH priority gaps
2. Add expiration warning: "Gap analysis valid for 7 days - re-run before submission"
3. Log all gap analysis runs with confidence scores in audit trail

#### Testing Strategy

**Unit Tests (6 tests):**
```python
# test_gap_analysis.py

def test_detect_missing_device_data_perfect():
    """Test with complete device profile - should find 0 gaps"""
    assert len(gaps) == 0
    assert confidence == "HIGH"

def test_detect_missing_device_data_sparse():
    """Test with minimal device profile - should find 5+ gaps"""
    assert len(gaps) >= 5
    assert all(g['priority'] in ['HIGH', 'MEDIUM', 'LOW'] for g in gaps)

def test_detect_weak_predicates_recalls():
    """Test predicate with 2 recalls - should flag as HIGH priority"""
    predicate = {'recalls_total': 2, 'predicate_acceptability': 'NOT_RECOMMENDED'}
    gaps = detect_weak_predicates([predicate])
    assert gaps[0]['priority'] == 'HIGH'
    assert 'recall' in gaps[0]['message'].lower()

def test_confidence_calculation_high():
    """Test confidence with complete data and clear gaps"""
    confidence_data = calculate_gap_analysis_confidence(gaps_clear, device_complete)
    assert confidence_data['confidence_level'] == 'HIGH'
    assert confidence_data['confidence_percentage'] >= 90

def test_confidence_calculation_low():
    """Test confidence with sparse data"""
    confidence_data = calculate_gap_analysis_confidence(gaps_ambiguous, device_sparse)
    assert confidence_data['confidence_level'] == 'LOW'
    assert confidence_data['confidence_percentage'] < 70

def test_fallback_no_predicates():
    """Test fallback when no predicates available"""
    result = run_gap_analysis(device_profile={}, predicates=[])
    assert result['category'] == 'CRITICAL_ERROR'
    assert 'Cannot perform gap analysis' in result['message']
```

**Integration Test (1 end-to-end):**
```python
def test_gap_analysis_end_to_end():
    """Test complete workflow: load data → detect gaps → generate report"""
    # Setup test project with known gaps
    project = create_test_project_with_gaps()

    # Run automation
    result = run_auto_gap_analysis(project_name='test_gap_project')

    # Verify outputs
    assert Path('gap_analysis_report.md').exists()
    assert Path('gap_analysis_data.json').exists()

    # Verify gap detection
    gaps = json.load(open('gap_analysis_data.json'))
    assert len(gaps['missing_data']) >= 2
    assert len(gaps['weak_predicates']) >= 1

    # Verify confidence
    assert gaps['metadata']['confidence_level'] in ['HIGH', 'MEDIUM', 'LOW']
```

**Manual Validation Test:**
1. Run on 3 real projects with known gaps
2. Compare automated gaps vs manually identified gaps
3. Target: ≥90% recall (finds 90%+ of real gaps), ≤10% false positives

### 1.4 Integration Points

#### New Command: `/fda:auto-gap-analysis`

**Command File:** `plugins/fda-predicate-assistant/commands/auto-gap-analysis.md`

```markdown
---
description: Automated gap analysis for 510(k) projects
allowed-tools: Bash, Read, Glob, Write
argument-hint: "[--project NAME] [--output-dir PATH]"
---

# Automated Gap Analysis

Systematically identifies missing data, weak predicates, testing gaps,
and standards gaps in 510(k) project.

**Usage:**
/fda:auto-gap-analysis --project my_device_project

**Outputs:**
- gap_analysis_report.md (human-readable)
- gap_analysis_data.json (machine-readable)
- Updated enrichment_metadata.json (audit trail)

**Confidence Levels:**
- HIGH (≥90%): Gap analysis trustworthy
- MEDIUM (70-89%): Review flagged gaps
- LOW (<70%): MANUAL ANALYSIS REQUIRED
```

#### Integration with Batchfetch

**Modified:** `plugins/fda-predicate-assistant/commands/batchfetch.md`

**Add flag:** `--gap-analysis`

```bash
# Run enrichment with automatic gap analysis
/fda:batchfetch --product-codes DQY --years 2024 --enrich --gap-analysis --full-auto
```

**Logic:**
```python
if '--gap-analysis' in arguments:
    # After enrichment completes
    print("\n🔍 Running automated gap analysis...")

    # Run gap detection
    gaps = run_auto_gap_analysis(project_name=project_name)

    # Write reports
    write_gap_analysis_report(gaps)

    # Show summary
    print(f"✅ Gap analysis complete: {len(gaps['all_gaps'])} gaps identified")
    print(f"   Confidence: {gaps['metadata']['confidence_level']}")
    print(f"   Report: gap_analysis_report.md")
```

#### New Reports Generated

**1. gap_analysis_report.md**
- Executive summary with gap counts
- Gap categories (4 sections)
- Recommended actions (priority-ordered)
- Automation metadata (confidence, sources, checkpoints)

**2. gap_analysis_data.json**
```json
{
  "metadata": {
    "analysis_timestamp": "2026-02-13T14:23:45Z",
    "project_name": "my_device",
    "automation_version": "2.1.0",
    "confidence_level": "HIGH",
    "confidence_percentage": 87.3,
    "data_sources": ["device_profile.json", "510k_download_enriched.csv"]
  },
  "gaps": {
    "missing_data": [
      {
        "field": "sterilization_method",
        "priority": "HIGH",
        "reason": "Required for sterile device clearance",
        "remediation": "Obtain from design documentation",
        "confidence": "HIGH"
      }
    ],
    "weak_predicates": [...],
    "testing_gaps": [...],
    "standards_gaps": [...]
  },
  "summary": {
    "total_gaps": 12,
    "high_priority": 3,
    "medium_priority": 6,
    "low_priority": 3
  },
  "human_review_required": [
    "All HIGH priority gaps must be reviewed before submission",
    "MEDIUM confidence gaps should be validated by RA professional"
  ]
}
```

#### User Interaction Model

**Workflow 1: Standalone Gap Analysis**
```bash
# User runs dedicated command
/fda:auto-gap-analysis --project my_device

# System loads data and runs analysis
# System writes gap_analysis_report.md

# User reviews report
# User addresses HIGH priority gaps
# User validates MEDIUM confidence gaps
# User re-runs analysis to verify gaps closed
```

**Workflow 2: Integrated with Batchfetch**
```bash
# User runs batchfetch with gap analysis flag
/fda:batchfetch --product-codes DQY --years 2024 --enrich --gap-analysis --full-auto

# System enriches predicates
# System automatically runs gap analysis
# System writes enrichment reports + gap analysis report

# User reviews all outputs together
```

**Workflow 3: Iterative Gap Closure**
```bash
# Initial analysis
/fda:auto-gap-analysis --project my_device
# Result: 12 gaps (3 HIGH, 6 MEDIUM, 3 LOW)

# User addresses 3 HIGH priority gaps
# Updates device_profile.json with missing data

# Re-run analysis
/fda:auto-gap-analysis --project my_device
# Result: 9 gaps (0 HIGH, 6 MEDIUM, 3 LOW)

# Repeat until acceptable gap count
```

---

## Feature 2: Smart Predicate Recommendations

### 2.1 Feature Specification

#### User Value Proposition

**Manual Process (6-8 hours):**
1. Search FDA database by product code (30-45 min)
2. Review 50-100 K-numbers for relevance (2-3 hours)
3. Check each predicate's indications for use (1-2 hours)
4. Check recall history for each candidate (1-2 hours)
5. Compare technological characteristics (1-2 hours)
6. Rank predicates and select top 3-5 (30-60 min)

**Automated Process (30 minutes):**
1. Run smart recommendations (5 min)
2. Review top 10 ranked predicates with confidence scores (15 min)
3. Validate HIGH confidence recommendations and proceed (10 min)

**What Automation Eliminates:**
- Manual database searching (all handled by batchfetch)
- Manual recall checking (enrichment data)
- Manual ranking (ML-powered scoring)
- Subjective predicate selection (objective criteria)

#### Input Requirements

**Triggers Automation:**
- User runs `/fda:smart-predicates --subject-device {K_NUMBER}` OR
- User runs `/fda:batchfetch --smart-recommend` (integrated mode)

**Required Data:**
```
Subject Device Specs (from device_profile.json):
- indications_for_use (text)
- technological_characteristics (text)
- product_code
- device_name
- materials (optional)
- sterilization_method (optional)

Predicate Pool (from 510k_download_enriched.csv):
- All predicates for product code
- Enrichment data (recalls, MAUDE, clinical indicators)
- Decision descriptions
- Clearance dates
```

**Minimum Viable Data:**
- Subject indications (IFU text)
- At least 10 predicates in pool

#### Output Format

**Primary Output:** `smart_predicate_recommendations.md`

```markdown
# Smart Predicate Recommendations

## Executive Summary
- Predicates analyzed: 47
- Top recommendations: 10
- Confidence level: HIGH (92%)
- Recommendation: Use Rank 1-3 as primary predicates

## Top 10 Recommended Predicates

### Rank 1: K234567 (Confidence: 96% - HIGH) ⭐ BEST MATCH
**Device:** CardioStent Pro System
**Clearance:** 2022-08-15 (2 years old)
**Match Score:** 96/100

**Strengths:**
- ✅ Indications: 98% match (percutaneous coronary intervention)
- ✅ Technology: 95% match (drug-eluting stent, balloon catheter)
- ✅ Safety: HEALTHY (0 recalls, stable MAUDE trending)
- ✅ Regulatory: Recent clearance, no special controls

**Considerations:**
- ⚠️ Material difference: PEEK vs titanium (addressable via biocompatibility)

**Recommendation:** PRIMARY PREDICATE - Excellent match, clean safety record

---

### Rank 2: K198765 (Confidence: 89% - HIGH)
**Device:** VascularAccess Stent
**Match Score:** 89/100
...

## Rejected Predicates (Not Recommended)

### K111222 - REJECTED: Multiple recalls (3)
### K333444 - REJECTED: Clearance age >15 years (1998)
### K555666 - REJECTED: Indications mismatch (orthopedic, not cardiovascular)

## Automation Metadata
- Analysis timestamp: 2026-02-13T10:15:30Z
- Algorithm version: SmartPredict v2.1
- Similarity model: TF-IDF + Cosine Similarity
- Confidence calculation: Multi-factor scoring (6 dimensions)
```

**Secondary Outputs:**
- `predicate_ranking_data.json` - Machine-readable scores
- Appended to `enrichment_metadata.json` - Audit trail

#### Decision Confidence

**Confidence Scoring Methodology:**

```python
def calculate_predicate_recommendation_confidence(
    subject_device: Dict,
    predicate: Dict,
    similarity_scores: Dict
) -> Dict[str, Any]:
    """
    Calculate confidence in predicate recommendation.

    Confidence Dimensions (6 factors):
    1. Indications Similarity (30%) - Text match quality
    2. Technology Similarity (25%) - Spec match quality
    3. Safety Record (20%) - Recall/MAUDE confidence
    4. Data Quality (10%) - Enrichment completeness
    5. Regulatory Currency (10%) - Clearance age appropriateness
    6. Cross-Validation (5%) - Multiple similarity metrics agree
    """

    # 1. Indications Similarity (30 points)
    ifu_similarity = similarity_scores['indications_cosine']
    indications_score = ifu_similarity * 30

    # 2. Technology Similarity (25 points)
    tech_similarity = similarity_scores['tech_characteristics_cosine']
    technology_score = tech_similarity * 25

    # 3. Safety Record (20 points)
    if predicate['recalls_total'] == 0 and predicate['maude_trending'] == 'stable':
        safety_score = 20
    elif predicate['recalls_total'] == 1 or predicate['maude_trending'] == 'decreasing':
        safety_score = 10
    else:
        safety_score = 0  # 2+ recalls or increasing MAUDE

    # 4. Data Quality (10 points)
    enrichment_quality = predicate['enrichment_completeness_score']
    quality_score = (enrichment_quality / 100) * 10

    # 5. Regulatory Currency (10 points)
    clearance_year = int(predicate['DECISIONDATE'][:4])
    years_old = 2026 - clearance_year
    if years_old <= 5:
        currency_score = 10
    elif years_old <= 10:
        currency_score = 7
    elif years_old <= 15:
        currency_score = 3
    else:
        currency_score = 0

    # 6. Cross-Validation (5 points)
    # Multiple similarity methods agree?
    cosine_rank = similarity_scores['indications_rank']
    jaccard_rank = similarity_scores['indications_jaccard_rank']
    if abs(cosine_rank - jaccard_rank) <= 2:
        crossval_score = 5  # Agreement
    else:
        crossval_score = 2  # Disagreement

    # Total confidence
    confidence_pct = (indications_score + technology_score + safety_score +
                     quality_score + currency_score + crossval_score)

    # Classify confidence
    if confidence_pct >= 90:
        confidence = "HIGH"
        recommendation = "Strongly recommended as primary predicate"
    elif confidence_pct >= 75:
        confidence = "MEDIUM"
        recommendation = "Recommended as secondary predicate; validate indications match"
    elif confidence_pct >= 60:
        confidence = "LOW"
        recommendation = "Consider only if no better alternatives; manual validation required"
    else:
        confidence = "VERY_LOW"
        recommendation = "NOT RECOMMENDED - significant gaps or safety concerns"

    return {
        'confidence_percentage': round(confidence_pct, 1),
        'confidence_level': confidence,
        'recommendation': recommendation,
        'factors': {
            'indications_match': round(indications_score, 1),
            'technology_match': round(technology_score, 1),
            'safety_record': round(safety_score, 1),
            'data_quality': round(quality_score, 1),
            'regulatory_currency': round(currency_score, 1),
            'cross_validation': round(crossval_score, 1)
        },
        'strengths': identify_strengths(predicate, similarity_scores),
        'considerations': identify_considerations(predicate, similarity_scores)
    }
```

**Confidence Thresholds:**
- **HIGH (≥90%):** Strongly recommended, proceed with confidence
- **MEDIUM (75-89%):** Good match, validate specific areas
- **LOW (60-74%):** Consider if no alternatives, thorough validation needed
- **VERY LOW (<60%):** NOT RECOMMENDED

### 2.2 Automation Logic

#### Predicate Ranking Decision Tree

```
START: Load subject device + predicate pool
  │
  ├─→ STEP 1: Data Validation
  │   ├─ Subject IFU exists? → YES: Continue | NO: CRITICAL ERROR
  │   ├─ Predicate pool ≥10? → YES: Continue | NO: WARNING (small pool)
  │   └─ Enrichment data available? → YES: Continue | NO: Run without enrichment
  │
  ├─→ STEP 2: Indications Matching (30% weight)
  │   │
  │   ├─ Text Preprocessing:
  │   │   ├─ Lowercase, remove stopwords
  │   │   ├─ Extract key terms (TF-IDF)
  │   │   └─ Normalize medical terminology (IVD → in vitro diagnostic)
  │   │
  │   ├─ Similarity Calculation:
  │   │   ├─ Method 1: Cosine similarity (TF-IDF vectors)
  │   │   ├─ Method 2: Jaccard similarity (term overlap)
  │   │   └─ Cross-validate: If methods disagree by >20%, flag as LOW confidence
  │   │
  │   └─ Scoring:
  │       ├─ Cosine ≥0.8 → 30 points (excellent match)
  │       ├─ Cosine 0.6-0.79 → 20 points (good match)
  │       ├─ Cosine 0.4-0.59 → 10 points (moderate match)
  │       └─ Cosine <0.4 → 0 points (poor match)
  │
  ├─→ STEP 3: Technology Matching (25% weight)
  │   │
  │   ├─ Extract technological characteristics:
  │   │   ├─ From subject: device_profile['technological_characteristics']
  │   │   ├─ From predicate: decision_description + extracted_sections
  │   │   └─ Key terms: materials, power source, mechanism of action
  │   │
  │   ├─ Similarity Calculation:
  │   │   ├─ Same as indications (TF-IDF + cosine)
  │   │   ├─ Material-specific matching (exact match bonus)
  │   │   └─ If tech_characteristics empty: Default to 12.5 points (MEDIUM conf)
  │   │
  │   └─ Scoring:
  │       ├─ Cosine ≥0.8 → 25 points
  │       ├─ Cosine 0.6-0.79 → 17 points
  │       ├─ Cosine 0.4-0.59 → 10 points
  │       └─ Cosine <0.4 → 0 points
  │
  ├─→ STEP 4: Safety Record Scoring (20% weight)
  │   │
  │   ├─ Recall Filter (Phase 2 enrichment data):
  │   │   ├─ 0 recalls → 10 points
  │   │   ├─ 1 recall → 5 points
  │   │   ├─ ≥2 recalls → 0 points (auto-reject)
  │   │
  │   ├─ MAUDE Trending (Phase 1 enrichment data):
  │   │   ├─ 'decreasing' → 10 points
  │   │   ├─ 'stable' → 10 points
  │   │   ├─ 'increasing' → 5 points
  │   │   └─ 'unknown' → 5 points (neutral)
  │   │
  │   └─ Combined Safety Score: recalls_score + maude_score (max 20)
  │
  ├─→ STEP 5: Data Quality Scoring (10% weight)
  │   │
  │   ├─ Use enrichment_completeness_score (Phase 1):
  │   │   └─ Scale 0-100 → 0-10 points
  │   │
  │   └─ If no enrichment: Default to 5 points (MEDIUM conf)
  │
  ├─→ STEP 6: Regulatory Currency (10% weight)
  │   │
  │   ├─ Calculate clearance age:
  │   │   ├─ Age = 2026 - clearance_year
  │   │   ├─ ≤5 years → 10 points (current)
  │   │   ├─ 6-10 years → 7 points (acceptable)
  │   │   ├─ 11-15 years → 3 points (aging)
  │   │   └─ >15 years → 0 points (outdated)
  │   │
  │   └─ Rationale: Recent devices reflect current regulatory expectations
  │
  ├─→ STEP 7: Cross-Validation (5% weight)
  │   │
  │   ├─ Compare rankings from different similarity methods:
  │   │   ├─ Cosine similarity rank
  │   │   ├─ Jaccard similarity rank
  │   │   └─ If ranks differ by ≤2 positions → 5 points (agreement)
  │   │       If ranks differ by >2 positions → 2 points (disagreement)
  │   │
  │   └─ Purpose: Detect when one method produces outlier results
  │
  ├─→ STEP 8: Calculate Total Score & Confidence
  │   │
  │   ├─ Total = Sum of 6 dimension scores (max 100)
  │   ├─ Classify confidence level:
  │   │   ├─ ≥90 → HIGH
  │   │   ├─ 75-89 → MEDIUM
  │   │   ├─ 60-74 → LOW
  │   │   └─ <60 → VERY_LOW (auto-reject)
  │   │
  │   └─ Add qualitative factors:
  │       ├─ Identify strengths (scores ≥80% in dimension)
  │       ├─ Identify considerations (scores <50% in dimension)
  │       └─ Generate recommendation text
  │
  ├─→ STEP 9: Rank & Filter
  │   │
  │   ├─ Sort predicates by total score (descending)
  │   ├─ Apply filters:
  │   │   ├─ Remove: recalls_total ≥2 (safety reject)
  │   │   ├─ Remove: confidence = VERY_LOW (<60)
  │   │   ├─ Remove: indications_similarity <0.3 (relevance reject)
  │   │   └─ Keep: Top 10 after filters
  │   │
  │   └─ Separate rejected predicates for transparency
  │
  └─→ STEP 10: Generate Report
      │
      ├─ Top 10 section (detailed for each):
      │   ├─ Rank, K-number, device name
      │   ├─ Total score + confidence level
      │   ├─ Breakdown of 6 dimension scores
      │   ├─ Strengths (checkmarks)
      │   ├─ Considerations (warnings)
      │   └─ Recommendation text
      │
      ├─ Rejected section (brief listing):
      │   ├─ K-number
      │   ├─ Rejection reason
      │   └─ Score (for reference)
      │
      ├─ Automation metadata:
      │   ├─ Overall confidence in ranking
      │   ├─ Algorithm version
      │   ├─ Data sources
      │   └─ Human review guidance
      │
      └─ Output smart_predicate_recommendations.md + JSON
```

#### Human-in-the-Loop Checkpoints

**Checkpoint 1: Subject Device Data Validation (AUTOMATED)**
```python
if subject_indications is None or len(subject_indications) < 50:
    return {
        'error': 'INSUFFICIENT_SUBJECT_DATA',
        'message': 'Subject device indications too short (<50 chars) for reliable matching',
        'remediation': 'Provide detailed indications for use in device_profile.json',
        'confidence': 'N/A'
    }
```

**Checkpoint 2: Small Predicate Pool Warning (AUTOMATED)**
```python
if len(predicate_pool) < 10:
    warnings.append({
        'type': 'SMALL_POOL',
        'message': f'Only {len(predicate_pool)} predicates available for analysis',
        'impact': 'Recommendations may be limited; consider broader search'
    })
```

**Checkpoint 3: Top Recommendation Validation (MANUAL)**
```markdown
## Human Review Checklist

Before using recommended predicates, validate:

[ ] Rank 1-3 indications match YOUR intended use (not just similar)
[ ] Rank 1-3 technological characteristics match YOUR device design
[ ] You have reviewed actual predicate 510(k) summaries (not just automation)
[ ] You understand any flagged "Considerations" and have mitigation plans
```

**Checkpoint 4: Low Confidence Escalation (AUTOMATED)**
```python
if top_recommendation['confidence_level'] in ['LOW', 'VERY_LOW']:
    banner = """
    ⚠️ LOW CONFIDENCE RECOMMENDATIONS

    The top recommended predicate has LOW confidence ({confidence}%).
    This may indicate:
    - Subject device is novel/unique (few similar predicates)
    - Indications poorly specified in device_profile.json
    - Product code has limited clearances

    MANUAL PREDICATE SELECTION REQUIRED
    Use these recommendations as starting point only.
    """
```

#### Fallback Strategies

**Fallback 1: No Enrichment Data Available**
```python
if enrichment_data_missing:
    logger.warning("No enrichment data - using basic similarity only")
    # Fallback scoring:
    # - Indications: 50% weight (was 30%)
    # - Technology: 40% weight (was 25%)
    # - Clearance age: 10% weight (was 10%)
    # - Safety/quality: Skip (was 30%)
    # Total still 100%, but confidence downgraded to MEDIUM max
    max_confidence = "MEDIUM"
```

**Fallback 2: Subject Technology Characteristics Missing**
```python
if subject_tech_characteristics is None:
    logger.warning("No tech characteristics for subject - using indications only")
    # Redistribute technology weight to indications:
    # - Indications: 55% weight (30 + 25)
    # - Other dimensions: unchanged
    confidence_penalty = 15  # Reduce confidence by 15 points
```

**Fallback 3: TF-IDF Vectorization Fails (extremely rare)**
```python
if tfidf_error:
    logger.error("TF-IDF failed - falling back to keyword matching")
    # Fallback: Simple keyword overlap
    # Extract top 10 keywords from subject IFU
    # Count matches in predicate IFU
    # Score = (matches / 10) * 100
    confidence_level = "LOW"  # Always low confidence
```

**Fallback 4: All Predicates Rejected (no good matches)**
```python
if len(recommended_predicates) == 0:
    return {
        'summary': 'No suitable predicates found',
        'reason': 'All candidates failed minimum criteria (safety, relevance, or age)',
        'recommendations': [
            'Consider broader product code search',
            'Review subject device classification (may be novel)',
            'Consult with RA professional for predicate strategy'
        ],
        'confidence': 'N/A'
    }
```

**Fallback 5: Duplicate Devices (same K-number in pool multiple times)**
```python
# Deduplicate by K-number before ranking
unique_predicates = deduplicate_by_knumber(predicate_pool)
if len(unique_predicates) < len(predicate_pool):
    logger.info(f"Removed {len(predicate_pool) - len(unique_predicates)} duplicates")
```

### 2.3 Implementation Plan

#### Time Estimate: 3 hours

**Hour 1: Similarity Calculation Engine (60 min)**
- Implement `calculate_text_similarity()` (TF-IDF + cosine) - 25 min
- Implement `extract_technological_terms()` (keyword extraction) - 15 min
- Implement cross-validation logic (compare methods) - 10 min
- Write unit tests for similarity functions (5 test cases) - 10 min

**Hour 2: Predicate Scoring & Ranking (60 min)**
- Implement `score_predicate()` (6-dimension scoring) - 20 min
- Implement `rank_predicates()` (sort + filter) - 15 min
- Implement `identify_strengths_and_considerations()` - 15 min
- Write unit tests for scoring (4 test cases) - 10 min

**Hour 3: Report Generation & Integration (60 min)**
- Implement `generate_smart_recommendations_report()` - 20 min
- Implement `write_ranking_data_json()` - 10 min
- Add `/fda:smart-predicates` command handler - 10 min
- Add `--smart-recommend` flag to batchfetch - 5 min
- Write integration test (end-to-end workflow) - 10 min
- Document in user guide - 5 min

#### Dependencies

**Phase 1 & 2 (COMPLETE):**
- ✅ Enrichment data (`enrichment_completeness_score`, `recalls_total`, `maude_trending`)
- ✅ Predicate acceptability assessment (`predicate_acceptability`)

**Existing Data Files:**
- ✅ `device_profile.json` - Subject device specs (especially IFU)
- ✅ `510k_download_enriched.csv` - Predicate pool with enrichment

**External Libraries:**
- 🆕 scikit-learn (TF-IDF, cosine similarity) - May need pip install
  - Fallback: Implement basic TF-IDF manually if unavailable

#### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Over-reliance on automation** | HIGH | CRITICAL | Manual validation checkboxes, "not regulatory advice" disclaimers |
| **IFU similarity misses regulatory nuance** | MEDIUM | HIGH | Require RA review of top 3, provide detailed reasoning |
| **Novel devices get LOW scores** | MEDIUM | MEDIUM | Detect and flag "no good match" scenario explicitly |
| **Computational cost (large pools)** | LOW | LOW | Limit analysis to top 100 predicates by date |
| **Missing enrichment data degrades scores** | MEDIUM | MEDIUM | Fallback scoring without enrichment, downgrade confidence |
| **User misses "Considerations" warnings** | HIGH | HIGH | Visual warnings (⚠️), prominent placement in report |

**Critical Risk: RA professional relies solely on Rank 1 without validation**

**Mitigation:**
1. Require manual checkbox: "I have reviewed actual 510(k) summaries for Rank 1-3"
2. Add expiration: "Recommendations valid for 30 days - market may have newer predicates"
3. Log all recommendation runs with confidence scores in audit trail
4. Add disclaimer: "Automation suggests candidates; YOU determine SE"

#### Testing Strategy

**Unit Tests (9 tests):**
```python
# test_smart_predicates.py

def test_text_similarity_identical():
    """Test similarity for identical IFU text"""
    text1 = "Device for percutaneous coronary intervention"
    text2 = "Device for percutaneous coronary intervention"
    similarity = calculate_text_similarity(text1, text2)
    assert similarity >= 0.99

def test_text_similarity_different():
    """Test similarity for completely different IFU"""
    text1 = "Cardiovascular stent"
    text2 = "Orthopedic bone screw"
    similarity = calculate_text_similarity(text1, text2)
    assert similarity < 0.2

def test_score_predicate_perfect_match():
    """Test scoring for ideal predicate (0 recalls, recent, high similarity)"""
    subject = {'indications': 'cardiac stent', 'tech': 'drug-eluting'}
    predicate = {
        'decision_description': 'cardiac stent for coronary intervention',
        'technological_characteristics': 'drug-eluting polymer coating',
        'recalls_total': 0,
        'maude_trending': 'stable',
        'enrichment_completeness_score': 95,
        'DECISIONDATE': '2024-01-15'
    }
    score = score_predicate(subject, predicate)
    assert score['confidence_level'] == 'HIGH'
    assert score['confidence_percentage'] >= 90

def test_score_predicate_with_recalls():
    """Test scoring for predicate with 2 recalls (should auto-reject)"""
    predicate = {'recalls_total': 2, ...}
    score = score_predicate(subject, predicate)
    assert score['confidence_level'] == 'VERY_LOW'
    assert score['recommendation'].startswith('NOT RECOMMENDED')

def test_rank_predicates_top_10():
    """Test ranking returns top 10 sorted by score"""
    predicates = create_test_predicates(count=50)
    ranked = rank_predicates(subject, predicates)
    assert len(ranked['top_10']) == 10
    # Verify descending order
    for i in range(9):
        assert ranked['top_10'][i]['score'] >= ranked['top_10'][i+1]['score']

def test_rank_predicates_filters_unsafe():
    """Test ranking filters predicates with 2+ recalls"""
    predicates = [
        {'KNUMBER': 'K111111', 'recalls_total': 0, ...},  # Keep
        {'KNUMBER': 'K222222', 'recalls_total': 2, ...},  # Reject
        {'KNUMBER': 'K333333', 'recalls_total': 3, ...},  # Reject
    ]
    ranked = rank_predicates(subject, predicates)
    knumbers = [p['KNUMBER'] for p in ranked['top_10']]
    assert 'K111111' in knumbers
    assert 'K222222' not in knumbers
    assert 'K333333' not in knumbers

def test_fallback_no_enrichment():
    """Test fallback when enrichment data unavailable"""
    predicates_no_enrichment = [{'KNUMBER': 'K123456', ...}]  # Missing enrichment fields
    ranked = rank_predicates(subject, predicates_no_enrichment)
    assert ranked['metadata']['max_confidence'] == 'MEDIUM'

def test_fallback_no_subject_tech():
    """Test fallback when subject tech characteristics missing"""
    subject_no_tech = {'indications': 'cardiac stent'}  # No 'tech' field
    score = score_predicate(subject_no_tech, predicate)
    assert score['confidence_percentage'] < 90  # Confidence penalty applied

def test_edge_case_empty_pool():
    """Test handling of empty predicate pool"""
    ranked = rank_predicates(subject, predicates=[])
    assert ranked['summary'] == 'No suitable predicates found'
    assert len(ranked['top_10']) == 0
```

**Integration Test (1 end-to-end):**
```python
def test_smart_recommendations_end_to_end():
    """Test complete workflow: load data → score → rank → generate report"""
    # Setup test project with subject device + 20 predicates
    project = create_test_project_with_predicates(count=20)

    # Run automation
    result = run_smart_predicate_recommendations(
        project_name='test_smart_predict',
        subject_device_name='Test Cardiac Stent'
    )

    # Verify outputs
    assert Path('smart_predicate_recommendations.md').exists()
    assert Path('predicate_ranking_data.json').exists()

    # Verify ranking
    rankings = json.load(open('predicate_ranking_data.json'))
    assert len(rankings['top_10']) == 10
    assert rankings['top_10'][0]['confidence_level'] in ['HIGH', 'MEDIUM', 'LOW']
    assert rankings['metadata']['algorithm_version'] == 'SmartPredict v2.1'
```

**Manual Validation Test:**
1. Run on 5 real devices with known good predicates
2. Compare automated Rank 1-3 vs RA professional selections
3. Target: ≥80% overlap (automated top 3 includes RA professional choice)

### 2.4 Integration Points

#### New Command: `/fda:smart-predicates`

**Command File:** `plugins/fda-predicate-assistant/commands/smart-predicates.md`

```markdown
---
description: AI-powered predicate ranking and recommendation
allowed-tools: Bash, Read, Glob, Write
argument-hint: "--subject-device {NAME} [--project NAME] [--top-n 10]"
---

# Smart Predicate Recommendations

ML-powered predicate selection based on 6-dimensional similarity scoring.

**Usage:**
/fda:smart-predicates --subject-device "CardioStent Pro" --project my_device

**Algorithm:**
1. Indications matching (TF-IDF similarity, 30% weight)
2. Technology matching (spec similarity, 25% weight)
3. Safety record (recalls + MAUDE, 20% weight)
4. Data quality (enrichment completeness, 10% weight)
5. Regulatory currency (clearance age, 10% weight)
6. Cross-validation (method agreement, 5% weight)

**Outputs:**
- smart_predicate_recommendations.md (top 10 ranked)
- predicate_ranking_data.json (full scores)
- Updated enrichment_metadata.json (audit trail)

**Confidence Levels:**
- HIGH (≥90%): Strongly recommended
- MEDIUM (75-89%): Good match, validate specifics
- LOW (60-74%): Manual validation required
- VERY LOW (<60%): NOT RECOMMENDED
```

#### Integration with Batchfetch

**Modified:** `plugins/fda-predicate-assistant/commands/batchfetch.md`

**Add flag:** `--smart-recommend`

```bash
# Run enrichment with smart predicate recommendations
/fda:batchfetch --product-codes DQY --years 2024 --enrich --smart-recommend --full-auto
```

**Logic:**
```python
if '--smart-recommend' in arguments:
    # After enrichment completes
    print("\n🧠 Running smart predicate recommendations...")

    # Prompt for subject device (if not in args)
    if '--subject-device' not in arguments:
        subject_device = ask_user("Enter subject device name (from device_profile.json):")

    # Run ranking
    rankings = run_smart_predicate_recommendations(
        subject_device=subject_device,
        project_name=project_name
    )

    # Write reports
    write_smart_recommendations_report(rankings)

    # Show summary
    top_k = rankings['top_10'][0]['KNUMBER']
    top_conf = rankings['top_10'][0]['confidence_level']
    print(f"✅ Smart recommendations complete")
    print(f"   Top predicate: {top_k} (Confidence: {top_conf})")
    print(f"   Report: smart_predicate_recommendations.md")
```

#### New Reports Generated

**1. smart_predicate_recommendations.md**
- Executive summary (predicates analyzed, top count, overall confidence)
- Top 10 ranked predicates (detailed breakdown per predicate)
- Rejected predicates (brief listing with reasons)
- Automation metadata (algorithm version, data sources, human review guidance)

**2. predicate_ranking_data.json**
```json
{
  "metadata": {
    "analysis_timestamp": "2026-02-13T15:45:30Z",
    "project_name": "cardio_stent_project",
    "subject_device": "CardioStent Pro System",
    "algorithm_version": "SmartPredict v2.1",
    "predicates_analyzed": 47,
    "similarity_method": "TF-IDF + Cosine Similarity"
  },
  "top_10": [
    {
      "rank": 1,
      "KNUMBER": "K234567",
      "device_name": "CardioStent Pro System",
      "clearance_date": "2022-08-15",
      "total_score": 96.3,
      "confidence_level": "HIGH",
      "confidence_percentage": 96.3,
      "dimension_scores": {
        "indications_match": 29.4,
        "technology_match": 23.8,
        "safety_record": 20.0,
        "data_quality": 9.5,
        "regulatory_currency": 10.0,
        "cross_validation": 5.0
      },
      "similarity_metrics": {
        "indications_cosine": 0.98,
        "indications_jaccard": 0.87,
        "tech_cosine": 0.95
      },
      "enrichment_data": {
        "recalls_total": 0,
        "maude_trending": "stable",
        "enrichment_completeness_score": 95
      },
      "strengths": [
        "Excellent indications match (98% similarity)",
        "Strong technology match (95% similarity)",
        "Clean safety record (0 recalls, stable MAUDE)",
        "Recent clearance (2 years old)"
      ],
      "considerations": [
        "Material difference: PEEK vs titanium (addressable via biocompatibility)"
      ],
      "recommendation": "PRIMARY PREDICATE - Excellent match, clean safety record"
    },
    ...
  ],
  "rejected": [
    {
      "KNUMBER": "K111222",
      "reason": "Multiple recalls (3)",
      "score": 45.2
    },
    ...
  ],
  "human_review_guidance": [
    "Validate top 3 indications match YOUR intended use",
    "Review actual 510(k) summaries (not just automation)",
    "Confirm technological characteristics alignment",
    "Verify you understand all flagged 'Considerations'"
  ]
}
```

#### User Interaction Model

**Workflow 1: Standalone Smart Recommendations**
```bash
# User runs dedicated command
/fda:smart-predicates --subject-device "CardioStent Pro" --project my_device

# System loads subject device from device_profile.json
# System loads predicates from 510k_download_enriched.csv
# System scores and ranks predicates
# System writes smart_predicate_recommendations.md

# User reviews top 10 recommendations
# User validates Rank 1-3 against actual 510(k) summaries
# User selects primary and secondary predicates
```

**Workflow 2: Integrated with Batchfetch**
```bash
# User runs batchfetch with smart recommend flag
/fda:batchfetch --product-codes DQY --years 2024 --enrich --smart-recommend \
  --subject-device "CardioStent Pro" --full-auto

# System enriches predicates
# System automatically runs smart recommendations
# System writes enrichment reports + smart recommendations

# User reviews all outputs together
# User has enrichment data + ranking in one workflow
```

**Workflow 3: Iterative Refinement**
```bash
# Initial recommendations (with sparse subject data)
/fda:smart-predicates --subject-device "MyDevice" --project my_device
# Result: Top predicate confidence = MEDIUM (78%)

# User improves device_profile.json (adds tech characteristics)

# Re-run recommendations
/fda:smart-predicates --subject-device "MyDevice" --project my_device
# Result: Top predicate confidence = HIGH (92%)

# User validates and proceeds
```

---

## Implementation Sequence & Timeline

### Phase 4 Implementation Roadmap

**Total Time:** 6 hours (3 hrs per feature)

#### Week 1: Feature 1 - Automated Gap Analysis (3 hours)

**Day 1 (Hour 1): Core Gap Detection**
- [ ] Implement `detect_missing_device_data()` (15 min)
- [ ] Implement `detect_weak_predicates()` (20 min)
- [ ] Implement `detect_testing_gaps()` (15 min)
- [ ] Implement `detect_standards_gaps()` (10 min)

**Day 1 (Hour 2): Scoring & Reports**
- [ ] Implement `calculate_gap_analysis_confidence()` (15 min)
- [ ] Implement `generate_gap_analysis_report()` (25 min)
- [ ] Implement `write_gap_data_json()` (10 min)
- [ ] Add audit trail updates (10 min)

**Day 1 (Hour 3): Integration & Testing**
- [ ] Create `/fda:auto-gap-analysis` command (10 min)
- [ ] Add `--gap-analysis` flag to batchfetch (10 min)
- [ ] Write 6 pytest unit tests (30 min)
- [ ] Update user documentation (10 min)

#### Week 1: Feature 2 - Smart Predicate Recommendations (3 hours)

**Day 2 (Hour 1): Similarity Engine**
- [ ] Implement `calculate_text_similarity()` TF-IDF (25 min)
- [ ] Implement `extract_technological_terms()` (15 min)
- [ ] Implement cross-validation logic (10 min)
- [ ] Write 5 similarity unit tests (10 min)

**Day 2 (Hour 2): Scoring & Ranking**
- [ ] Implement `score_predicate()` 6-dimension scoring (20 min)
- [ ] Implement `rank_predicates()` sort + filter (15 min)
- [ ] Implement `identify_strengths_and_considerations()` (15 min)
- [ ] Write 4 scoring unit tests (10 min)

**Day 2 (Hour 3): Integration & Testing**
- [ ] Implement `generate_smart_recommendations_report()` (20 min)
- [ ] Implement `write_ranking_data_json()` (10 min)
- [ ] Create `/fda:smart-predicates` command (10 min)
- [ ] Add `--smart-recommend` flag to batchfetch (5 min)
- [ ] Write end-to-end integration test (10 min)
- [ ] Update user documentation (5 min)

#### Dependencies Checklist

**Before Starting Implementation:**
- [x] Phase 1 complete (data integrity)
- [x] Phase 2 complete (intelligence layer)
- [x] Enrichment data structure finalized
- [x] Device profile schema stable
- [ ] scikit-learn library available (or fallback implemented)
- [ ] pytest framework configured

**During Implementation:**
- [ ] Access to test projects with device_profile.json
- [ ] Access to enriched CSV files for testing
- [ ] FDA standards database URLs verified
- [ ] Sample 510(k) summaries for validation

---

## Risk Mitigation Strategies

### Critical Risks & Mitigations

#### Risk 1: Over-Reliance on Automation (CRITICAL)

**Risk:** RA professionals trust automation completely without manual validation

**Likelihood:** HIGH
**Impact:** CRITICAL (FDA submission deficiency, 510(k) rejection)

**Mitigation:**
1. **Prominent Disclaimers:**
   ```markdown
   ⚠️ AUTOMATION ASSISTS, DOES NOT REPLACE RA JUDGMENT

   This automation provides data-driven recommendations.
   YOU (RA professional) are responsible for:
   - Validating indications match YOUR device
   - Reviewing actual 510(k) summaries
   - Determining substantial equivalence
   - Final predicate selection
   ```

2. **Manual Validation Checkboxes:**
   - All reports include: "[ ] I have manually validated these recommendations"
   - Gap analysis: "[ ] All HIGH priority gaps reviewed and addressed"
   - Predicates: "[ ] I have reviewed actual 510(k) summaries for Rank 1-3"

3. **Confidence Gates:**
   - LOW confidence (gap analysis <70%, predicate <75%) → MANUAL REVIEW REQUIRED banner
   - Automation explicitly states limitations in every output

4. **Audit Trail:**
   - Log all automation runs with confidence scores
   - Include "human_review_required" flags in JSON output

#### Risk 2: False Negatives (Missed Gaps/Poor Predicates)

**Risk:** Automation misses critical gaps or recommends unsuitable predicates

**Likelihood:** MEDIUM
**Impact:** HIGH (FDA questions, submission delays)

**Mitigation:**
1. **Conservative Thresholds:**
   - Gap detection: Flag anything uncertain as gap (better false positive than false negative)
   - Predicate ranking: Require ≥90% confidence for HIGH rating

2. **Cross-Validation:**
   - Use multiple similarity methods (TF-IDF + Jaccard)
   - Flag when methods disagree (→ LOW confidence)

3. **Safety Filters:**
   - Auto-reject predicates with ≥2 recalls (hard rule)
   - Flag predicates >15 years old (soft rule)

4. **Testing Against Known Cases:**
   - Validate on 5 real projects with known gaps
   - Target: ≥90% recall (finds 90%+ of real gaps)

#### Risk 3: Computational Performance (Low Risk, Medium Impact)

**Risk:** Large predicate pools (100+ devices) cause slow processing

**Likelihood:** LOW (most product codes have <100 recent predicates)
**Impact:** MEDIUM (user frustration, timeout)

**Mitigation:**
1. **Pool Limiting:**
   - Cap predicate pool at 100 most recent devices
   - Sort by clearance date, take top 100

2. **Progress Indicators:**
   - Show "Processing predicate 10/47..." during scoring
   - Estimated time remaining

3. **Caching:**
   - Cache TF-IDF models for repeated runs
   - Cache similarity matrices if subject unchanged

#### Risk 4: Data Quality Dependencies

**Risk:** Poor enrichment data quality → poor automation quality

**Likelihood:** MEDIUM (depends on FDA API uptime, data completeness)
**Impact:** MEDIUM (reduced confidence, manual fallback)

**Mitigation:**
1. **Fallback Modes:**
   - If enrichment missing: Use basic similarity only, downgrade confidence
   - If subject data sparse: Flag as LOW confidence, require manual input

2. **Quality Gates:**
   - Check enrichment_completeness_score before automation
   - If <60 for majority of predicates → warn user

3. **Graceful Degradation:**
   - Missing recall data → skip safety scoring, reduce max confidence
   - Missing MAUDE → skip trending, reduce max confidence

---

## Success Criteria

### Functional Requirements

**Gap Analysis:**
- [x] Detects 4 gap categories (missing data, weak predicates, testing, standards)
- [x] Assigns priority levels (HIGH, MEDIUM, LOW)
- [x] Calculates confidence score (0-100%)
- [x] Generates actionable recommendations
- [x] Outputs markdown report + JSON data
- [x] Integrates with batchfetch (`--gap-analysis` flag)
- [x] Includes audit trail in enrichment_metadata.json

**Smart Predicates:**
- [x] Scores predicates on 6 dimensions (indications, tech, safety, quality, currency, validation)
- [x] Ranks predicates by total score
- [x] Filters unsafe/irrelevant predicates
- [x] Generates top 10 recommendations with confidence
- [x] Outputs markdown report + JSON data
- [x] Integrates with batchfetch (`--smart-recommend` flag)
- [x] Includes audit trail in enrichment_metadata.json

### Quality Requirements

**Accuracy:**
- [ ] Gap analysis: ≥90% recall (finds 90%+ of real gaps) - validate on 5 projects
- [ ] Gap analysis: ≤10% false positive rate - validate on 5 projects
- [ ] Predicate ranking: ≥80% overlap with RA professional top 3 - validate on 5 projects

**Reliability:**
- [ ] All tests pass (15 unit tests + 2 integration tests)
- [ ] Fallback strategies handle missing data gracefully
- [ ] No crashes on edge cases (empty data, API failures)

**Transparency:**
- [ ] Every recommendation includes confidence score
- [ ] Every recommendation shows decision reasoning
- [ ] Rejected predicates explained with reasons
- [ ] Audit trail captures all automation runs

**Usability:**
- [ ] Reports readable by non-technical RA professionals
- [ ] Recommendations actionable (specific, clear next steps)
- [ ] Human review checkpoints clearly marked
- [ ] Output consistent with Phase 1 & 2 format

### Performance Requirements

**Speed:**
- [ ] Gap analysis: <30 seconds for typical project (10 predicates)
- [ ] Smart predicates: <60 seconds for 50 predicate pool
- [ ] No blocking on API calls (use cached enrichment data)

**Scalability:**
- [ ] Handles projects with 1-100 predicates
- [ ] Handles subject devices with 50-5000 character IFU
- [ ] Graceful degradation for larger pools (limit to 100 most recent)

---

## Documentation & User Guidance

### User Documentation Required

**1. User Guide Update (PHASE1_SUMMARY.md)**

Add section:
```markdown
## Phase 4: Automation Features

### Automated Gap Analysis

**What it does:** Systematically identifies missing data, weak predicates,
testing gaps, and standards gaps in your 510(k) project.

**When to use:** After identifying predicates but before drafting submission.

**How to run:**
```bash
/fda:auto-gap-analysis --project my_device_project
```

**Outputs:**
- `gap_analysis_report.md` - Human-readable gap report
- `gap_analysis_data.json` - Machine-readable gap data

**Interpreting confidence:**
- HIGH (≥90%): Trust gap analysis, proceed with remediation
- MEDIUM (70-89%): Review flagged gaps manually
- LOW (<70%): MANUAL GAP ANALYSIS REQUIRED

### Smart Predicate Recommendations

**What it does:** AI-powered ranking of predicates based on 6-dimensional
similarity scoring (indications, technology, safety, quality, currency, validation).

**When to use:** After collecting predicates via batchfetch, before selecting
final primary/secondary predicates.

**How to run:**
```bash
/fda:smart-predicates --subject-device "MyDevice" --project my_device_project
```

**Outputs:**
- `smart_predicate_recommendations.md` - Top 10 ranked predicates
- `predicate_ranking_data.json` - Full scoring data

**Interpreting confidence:**
- HIGH (≥90%): Strongly recommended as primary predicate
- MEDIUM (75-89%): Good match, validate specific areas
- LOW (60-74%): Manual validation required
- VERY LOW (<60%): NOT RECOMMENDED
```

**2. Technical Documentation (PHASE4_CHANGELOG.md)**

Create file documenting:
- Functions implemented
- Algorithms used
- Files modified
- Test results
- API changes

**3. RA Professional Guidance (PHASE4_RA_GUIDANCE.md)**

Create file addressing:
- When automation is appropriate vs when manual analysis required
- How to validate automated recommendations
- Common pitfalls and how to avoid them
- Regulatory considerations for using AI tools

---

## Conclusion

Phase 4 Automation delivers **94% time savings** (9-12 hours → 45 minutes per project) while maintaining **regulatory rigor** through:

1. **Conservative automation** - When uncertain, flag for human review
2. **Transparent reasoning** - Show decision logic, not black box
3. **Confidence scoring** - Every recommendation includes HIGH/MEDIUM/LOW confidence
4. **Fail-safe defaults** - Graceful degradation when data missing
5. **Audit trails** - Full provenance for every automated decision
6. **Human-in-the-loop** - Manual checkboxes for critical decisions

**Key Innovation:** This automation doesn't replace RA professionals—it amplifies their expertise by eliminating tedious manual work while preserving critical judgment.

**Next Steps:**
1. Review this design specification
2. Approve for implementation (6 hours)
3. Execute implementation sequence
4. Validate on 5 real projects
5. Deploy to production

---

**Design Date:** February 13, 2026
**Designer:** Medical Device Regulatory Automation Expert
**Status:** READY FOR APPROVAL
**Implementation Time:** 6 hours (3 hrs per feature)

---

*FDA Predicate Assistant - Phase 4: Intelligent Automation for Regulatory Excellence*
