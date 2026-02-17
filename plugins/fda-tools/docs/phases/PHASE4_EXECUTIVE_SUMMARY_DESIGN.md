# Phase 4: Executive Summary Generation - Design Document

**Feature Version:** 4.0.0
**Author:** Python Expert / FDA Tools Development Team
**Date:** 2026-02-13
**Status:** Design Phase - Ready for Implementation

---

## 1. Overview

### 1.1 Problem Statement

Currently, Phase 1-3 enrichment generates 5 detailed reports totaling 20-30 pages:
- `quality_report.md` - Data quality metrics (3-5 pages)
- `intelligence_report.md` - Strategic insights (4-6 pages)
- `regulatory_context.md` - CFR citations (2-3 pages)
- `competitive_intelligence_*.md` - Market analysis per product code (5-10 pages each)
- `enrichment_metadata.json` - Raw API provenance (machine-readable)

**Challenge:** Executives and decision-makers lack time to read 20-30 pages. They need:
- 1-2 page summary with key findings
- Clear risk assessment (red flags)
- Actionable recommendations (which predicates to use/avoid)
- Resource planning estimates (time, budget)
- Next steps roadmap

### 1.2 Success Criteria

Executive summary must:
1. **Brevity:** 1-2 pages maximum (500-1000 words)
2. **Actionability:** Clear yes/no recommendations, not ambiguous findings
3. **Risk-focused:** Highlight critical issues (recalls, EXTREME_OUTLIER MAUDE, clinical data)
4. **Quantified:** Include specific numbers (%, counts, $, months)
5. **Standalone:** Readable without other reports (but link to details)

---

## 2. Data Sources & Inputs

### 2.1 Available Data Structures

**From `enriched_rows` (List[Dict])** - 53 columns per device:

**Phase 1 - Data Integrity (12 cols):**
- `maude_productcode_5y`: int - 5-year MAUDE event count (product code level)
- `maude_trending`: str - 'increasing' | 'stable' | 'decreasing'
- `maude_scope`: str - 'PRODUCT_CODE' | 'UNAVAILABLE'
- `recalls_total`: int - Number of recalls for this K-number
- `recall_latest_date`: str - ISO date of most recent recall
- `recall_class`: str - 'Class I' | 'Class II' | 'Class III'
- `api_validated`: str - 'Yes' | 'No'
- `enrichment_completeness_score`: float - 0-100 quality score
- `enrichment_timestamp`: str - ISO timestamp
- `api_version`: str - Version string
- `regulation_number`: str - CFR citation (e.g., '21 CFR 870.1340')
- `device_classification`: str - Device type description

**Phase 2 - Intelligence Layer (11 cols):**
- `predicate_clinical_history`: str - 'YES' | 'NO' | 'UNKNOWN'
- `predicate_study_type`: str - 'premarket' | 'postmarket' | 'none'
- `predicate_clinical_indicators`: str - Comma-separated indicators
- `special_controls_applicable`: str - 'YES' | 'NO'
- `predicate_acceptability`: str - 'ACCEPTABLE' | 'REVIEW_REQUIRED' | 'NOT_RECOMMENDED'
- `acceptability_rationale`: str - Human-readable explanation
- `predicate_risk_factors`: str - Comma-separated risk factors
- `predicate_recommendation`: str - Action recommendation
- `assessment_basis`: str - Methodology reference

**Phase 3 - Advanced Analytics (7 cols):**
- `peer_cohort_size`: int - Number of peer devices analyzed
- `peer_median_events`: float - Median MAUDE events in peer group
- `peer_75th_percentile`: float - 75th percentile MAUDE events
- `peer_90th_percentile`: float - 90th percentile MAUDE events
- `device_percentile`: float - This device's percentile rank (0-100)
- `maude_classification`: str - 'EXCELLENT' | 'GOOD' | 'AVERAGE' | 'CONCERNING' | 'EXTREME_OUTLIER' | 'INSUFFICIENT_DATA'
- `peer_comparison_note`: str - Interpretation text

**Base 510(k) Data (24+ cols):**
- `KNUMBER`: str - K-number
- `APPLICANT`: str - Company name
- `DEVICENAME`: str - Trade name
- `PRODUCTCODE`: str - Product code
- `DECISIONDATE`: str - Clearance date
- `ADVISORY_COMMITTEE`: str - Review panel
- `DECISION`: str - Decision code (e.g., 'SESE')
- `REVIEWADVISECOMM`: str - Committee name
- etc.

**From Existing Reports:**
- `quality_report.md`: Aggregate quality score, API success rate
- `intelligence_report.md`: Clinical data percentages, acceptability breakdown
- `competitive_intelligence_*.md`: Market concentration (HHI), top manufacturers
- `regulatory_context.md`: CFR citations, guidance document currency

### 2.2 Key Metrics to Extract

**Risk Metrics (Highest Priority):**
1. Count of devices with `maude_classification == 'EXTREME_OUTLIER'`
2. Count of devices with `predicate_acceptability == 'NOT_RECOMMENDED'`
3. Count of devices with `recalls_total >= 2`
4. Count of devices with `recall_class == 'Class I'` (most severe)
5. Count of devices with `predicate_clinical_history == 'YES'`

**Quality Metrics:**
1. Average `enrichment_completeness_score` across all devices
2. Count of `api_validated == 'Yes'` devices
3. Percentage of devices with complete Phase 3 peer data

**Market Metrics (from competitive_intelligence):**
1. Total unique manufacturers (applicants)
2. Market concentration (HHI index if available)
3. Number of product codes analyzed

**Resource Planning Metrics:**
1. Percentage with clinical data history
2. Estimated testing costs based on standards/clinical requirements
3. Timeline estimates (months)

---

## 3. Algorithm Design

### 3.1 Data Aggregation Logic

**Step 1: Calculate Risk Scores**

```python
def calculate_risk_summary(enriched_rows: List[Dict]) -> Dict[str, Any]:
    """
    Aggregate risk metrics across all devices.

    Returns:
        {
            'extreme_outlier_count': int,
            'not_recommended_count': int,
            'recalled_devices': int,
            'class_i_recalls': int,
            'clinical_data_required': int,
            'total_devices': int,
            'critical_risk_level': str  # 'HIGH' | 'MEDIUM' | 'LOW'
        }
    """
    total = len(enriched_rows)

    extreme_outliers = sum(1 for r in enriched_rows
                          if r.get('maude_classification') == 'EXTREME_OUTLIER')

    not_recommended = sum(1 for r in enriched_rows
                         if r.get('predicate_acceptability') == 'NOT_RECOMMENDED')

    recalled = sum(1 for r in enriched_rows
                  if r.get('recalls_total', 0) > 0)

    class_i_recalls = sum(1 for r in enriched_rows
                         if r.get('recall_class', '') == 'Class I')

    clinical_yes = sum(1 for r in enriched_rows
                      if r.get('predicate_clinical_history') == 'YES')

    # Calculate overall risk level
    critical_issues = extreme_outliers + not_recommended + class_i_recalls

    if critical_issues > total * 0.3:  # >30% critical issues
        risk_level = 'HIGH'
    elif critical_issues > total * 0.1:  # 10-30% critical issues
        risk_level = 'MEDIUM'
    else:
        risk_level = 'LOW'

    return {
        'extreme_outlier_count': extreme_outliers,
        'not_recommended_count': not_recommended,
        'recalled_devices': recalled,
        'class_i_recalls': class_i_recalls,
        'clinical_data_required': clinical_yes,
        'total_devices': total,
        'critical_risk_level': risk_level,
        'risk_percentage': round((critical_issues / total) * 100, 1)
    }
```

**Step 2: Identify Best Predicates**

```python
def identify_best_predicates(enriched_rows: List[Dict], top_n: int = 5) -> List[Dict]:
    """
    Rank predicates by suitability and return top N.

    Scoring Algorithm:
    - Start with 100 points
    - MAUDE classification: EXCELLENT (+20), GOOD (+10), AVERAGE (0), CONCERNING (-20), EXTREME_OUTLIER (-100)
    - Acceptability: ACCEPTABLE (+20), REVIEW_REQUIRED (-10), NOT_RECOMMENDED (-100)
    - Recalls: 0 recalls (+10), 1 recall (-20), 2+ recalls (-100)
    - Clearance age: <5 years (+10), 5-10 years (0), >10 years (-10), >15 years (-20)
    - Clinical data: NO (+10), UNKNOWN (0), YES (-5)  # Less data = simpler path

    Returns:
        List of top N device dicts sorted by score
    """
    scored_devices = []

    for device in enriched_rows:
        score = 100

        # MAUDE classification
        maude_class = device.get('maude_classification', 'AVERAGE')
        maude_scores = {
            'EXCELLENT': 20, 'GOOD': 10, 'AVERAGE': 0,
            'CONCERNING': -20, 'EXTREME_OUTLIER': -100,
            'INSUFFICIENT_DATA': 0, 'NO_MAUDE_DATA': 5
        }
        score += maude_scores.get(maude_class, 0)

        # Acceptability
        acceptability = device.get('predicate_acceptability', 'ACCEPTABLE')
        accept_scores = {
            'ACCEPTABLE': 20, 'REVIEW_REQUIRED': -10, 'NOT_RECOMMENDED': -100
        }
        score += accept_scores.get(acceptability, 0)

        # Recalls
        recalls = device.get('recalls_total', 0)
        if recalls == 0:
            score += 10
        elif recalls == 1:
            score -= 20
        else:
            score -= 100

        # Clearance age
        try:
            clearance_date = device.get('DECISIONDATE', '')
            if clearance_date:
                from datetime import datetime
                clearance_year = int(clearance_date[:4])
                age_years = datetime.now().year - clearance_year

                if age_years < 5:
                    score += 10
                elif age_years > 15:
                    score -= 20
                elif age_years > 10:
                    score -= 10
        except:
            pass

        # Clinical data (simpler is better for faster clearance)
        clinical = device.get('predicate_clinical_history', 'NO')
        if clinical == 'NO':
            score += 10
        elif clinical == 'YES':
            score -= 5

        # Add score to device
        device_with_score = device.copy()
        device_with_score['predicate_score'] = score
        scored_devices.append(device_with_score)

    # Sort by score descending, return top N
    scored_devices.sort(key=lambda x: x['predicate_score'], reverse=True)
    return scored_devices[:top_n]
```

**Step 3: Calculate Resource Estimates**

```python
def estimate_resources(enriched_rows: List[Dict]) -> Dict[str, Any]:
    """
    Estimate timeline and budget based on enrichment data.

    Returns:
        {
            'timeline_months_min': int,
            'timeline_months_max': int,
            'budget_min': int,
            'budget_max': int,
            'key_cost_drivers': List[str]
        }
    """
    total = len(enriched_rows)

    # Base assumptions
    base_timeline = 6  # 6 months baseline
    base_budget = 50000  # $50K baseline

    # Clinical data impact
    clinical_pct = sum(1 for r in enriched_rows
                      if r.get('predicate_clinical_history') == 'YES') / total

    if clinical_pct > 0.3:  # >30% predicates had clinical data
        clinical_timeline = 12  # +12 months
        clinical_budget = 350000  # +$350K
    elif clinical_pct > 0.1:  # 10-30%
        clinical_timeline = 6  # +6 months
        clinical_budget = 150000  # +$150K
    else:
        clinical_timeline = 0
        clinical_budget = 0

    # Special controls impact
    special_controls_pct = sum(1 for r in enriched_rows
                              if r.get('special_controls_applicable') == 'YES') / total

    if special_controls_pct > 0.3:
        special_controls_timeline = 3  # +3 months
        special_controls_budget = 75000  # +$75K
    else:
        special_controls_timeline = 0
        special_controls_budget = 0

    # Calculate totals
    timeline_min = base_timeline + clinical_timeline + special_controls_timeline
    timeline_max = timeline_min + 6  # Add buffer

    budget_min = base_budget + clinical_budget + special_controls_budget
    budget_max = int(budget_min * 1.5)  # 50% contingency

    # Identify key cost drivers
    cost_drivers = ['Base 510(k) preparation']

    if clinical_timeline > 0:
        cost_drivers.append(f'Clinical studies ({clinical_pct*100:.0f}% of predicates had clinical data)')

    if special_controls_pct > 0.3:
        cost_drivers.append(f'Special controls compliance ({special_controls_pct*100:.0f}% of devices)')

    return {
        'timeline_months_min': timeline_min,
        'timeline_months_max': timeline_max,
        'budget_min': budget_min,
        'budget_max': budget_max,
        'key_cost_drivers': cost_drivers
    }
```

### 3.2 Natural Language Generation Strategy

**Approach: Template-Based with Dynamic Content Insertion**

**Why Template-Based (vs. Claude API NLG):**
1. **Speed:** Instant generation, no API latency
2. **Determinism:** Consistent output format, easier testing
3. **Cost:** Zero marginal cost per summary
4. **Control:** Full control over compliance disclaimers
5. **Offline:** Works without internet connectivity

**Template Structure:**

```python
def generate_executive_summary(enriched_rows: List[Dict],
                               project_dir: str,
                               quality_report_exists: bool = True) -> str:
    """
    Generate executive summary from enrichment data.

    Args:
        enriched_rows: List of enriched device dicts
        project_dir: Path to project directory
        quality_report_exists: Whether quality_report.md exists

    Returns:
        Markdown formatted executive summary string
    """
    # Calculate all metrics
    risk_summary = calculate_risk_summary(enriched_rows)
    best_predicates = identify_best_predicates(enriched_rows, top_n=5)
    worst_predicates = identify_best_predicates(enriched_rows, top_n=5)[-5:]  # Bottom 5
    resources = estimate_resources(enriched_rows)

    # Get product codes
    product_codes = sorted(set(r.get('PRODUCTCODE', 'N/A') for r in enriched_rows))

    # Generate summary
    from datetime import datetime

    summary = f"""# Executive Summary - FDA 510(k) Predicate Analysis

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
**Project:** {os.path.basename(project_dir)}
**Scope:** {risk_summary['total_devices']} devices across {len(product_codes)} product code(s): {', '.join(product_codes)}

---

## 🎯 Key Findings

### Overall Risk Assessment: **{risk_summary['critical_risk_level']}**

{generate_risk_narrative(risk_summary)}

### Top 3 Insights

{generate_top_insights(enriched_rows, risk_summary, resources)}

---

## ⚠️ Devices to Avoid (Critical Risks)

{generate_avoid_list(worst_predicates, risk_summary)}

---

## ✅ Recommended Predicates (Top 5)

{generate_recommendation_list(best_predicates)}

---

## 💰 Resource Planning

**Estimated Timeline:** {resources['timeline_months_min']}-{resources['timeline_months_max']} months
**Estimated Budget:** ${resources['budget_min']:,} - ${resources['budget_max']:,}

**Key Cost Drivers:**
{generate_cost_driver_list(resources['key_cost_drivers'])}

---

## 📋 Next Steps

{generate_next_steps(risk_summary, resources)}

---

## 📚 Detailed Reports

For comprehensive analysis, see:
- `quality_report.md` - Data quality and API validation
- `intelligence_report.md` - Clinical data and acceptability analysis
- `competitive_intelligence_*.md` - Market analysis per product code
- `regulatory_context.md` - CFR citations and FDA guidance
- `enrichment_report.html` - Interactive visual dashboard

---

**IMPORTANT DISCLAIMER:** This executive summary is generated from FDA openFDA API data
and is intended for research and intelligence purposes only. All findings MUST be
independently verified by qualified Regulatory Affairs professionals before being
relied upon for submission decisions. See individual reports for detailed disclaimers.
"""

    return summary
```

**Supporting Template Functions:**

```python
def generate_risk_narrative(risk_summary: Dict) -> str:
    """Generate risk assessment narrative"""
    total = risk_summary['total_devices']
    risk_pct = risk_summary['risk_percentage']

    if risk_summary['critical_risk_level'] == 'HIGH':
        return f"""
**CRITICAL CONCERNS IDENTIFIED** ({risk_pct}% of devices have critical issues)

- 🚨 **{risk_summary['extreme_outlier_count']} devices** flagged as EXTREME_OUTLIER for MAUDE events (DO NOT USE)
- ⚠️ **{risk_summary['not_recommended_count']} devices** marked NOT_RECOMMENDED due to recalls/age
- 📊 **{risk_summary['recalled_devices']} devices** have recall history ({risk_summary['class_i_recalls']} Class I)

**RECOMMENDATION:** Conduct thorough manual review before proceeding. Consider expanding search
to find safer predicates.
"""
    elif risk_summary['critical_risk_level'] == 'MEDIUM':
        return f"""
**MODERATE RISKS DETECTED** ({risk_pct}% of devices have notable issues)

- ⚠️ **{risk_summary['extreme_outlier_count']} devices** flagged as EXTREME_OUTLIER (avoid these)
- 📋 **{risk_summary['recalled_devices']} devices** have recall history (review details)
- ✅ **{total - risk_summary['not_recommended_count']} devices** are potentially acceptable

**RECOMMENDATION:** Focus on devices marked ACCEPTABLE. Review recalled predicates carefully.
"""
    else:
        return f"""
**LOW RISK COHORT** ({risk_pct}% of devices have critical issues)

- ✅ Most devices have clean safety records
- 📋 **{risk_summary['recalled_devices']} devices** have recalls (review but likely manageable)
- 🎯 **{total - risk_summary['not_recommended_count']} devices** suitable as predicates

**RECOMMENDATION:** Proceed with confidence. Select from ACCEPTABLE predicates.
"""

def generate_top_insights(enriched_rows: List[Dict],
                         risk_summary: Dict,
                         resources: Dict) -> str:
    """Generate top 3 insights"""
    insights = []

    # Insight 1: Clinical data requirements
    clinical_pct = (risk_summary['clinical_data_required'] / risk_summary['total_devices']) * 100

    if clinical_pct > 30:
        insights.append(f"1. **High Clinical Data Burden:** {clinical_pct:.0f}% of predicates used clinical studies. Budget {resources['timeline_months_min']}-{resources['timeline_months_max']} months and ${resources['budget_min']:,}+ for clinical work.")
    elif clinical_pct < 10:
        insights.append(f"1. **Favorable Clinical Profile:** Only {clinical_pct:.0f}% of predicates needed clinical data. Bench testing likely sufficient.")
    else:
        insights.append(f"1. **Moderate Clinical Risk:** {clinical_pct:.0f}% of predicates had clinical data. Plan for possible clinical studies.")

    # Insight 2: Market concentration
    manufacturers = set(r.get('APPLICANT', 'N/A') for r in enriched_rows)
    top_manufacturer = max(manufacturers,
                          key=lambda m: sum(1 for r in enriched_rows if r.get('APPLICANT') == m))
    top_count = sum(1 for r in enriched_rows if r.get('APPLICANT') == top_manufacturer)

    if top_count > risk_summary['total_devices'] * 0.5:
        insights.append(f"2. **Concentrated Market:** {top_manufacturer} dominates ({top_count}/{risk_summary['total_devices']} devices, {top_count/risk_summary['total_devices']*100:.0f}%). Consider competitive positioning.")
    else:
        insights.append(f"2. **Fragmented Market:** {len(manufacturers)} manufacturers. No dominant player.")

    # Insight 3: MAUDE safety profile
    excellent_count = sum(1 for r in enriched_rows
                         if r.get('maude_classification') in ['EXCELLENT', 'GOOD'])

    if excellent_count > risk_summary['total_devices'] * 0.6:
        insights.append(f"3. **Strong Safety Profile:** {excellent_count}/{risk_summary['total_devices']} devices ({excellent_count/risk_summary['total_devices']*100:.0f}%) have EXCELLENT/GOOD MAUDE ratings.")
    else:
        insights.append(f"3. **Mixed Safety Profile:** Only {excellent_count}/{risk_summary['total_devices']} devices have favorable MAUDE ratings. Scrutinize predicate selection.")

    return '\n'.join(insights)

def generate_avoid_list(worst_predicates: List[Dict],
                       risk_summary: Dict) -> str:
    """Generate list of devices to avoid"""
    # Get devices with critical issues
    avoid_devices = [d for d in worst_predicates
                    if d.get('predicate_acceptability') == 'NOT_RECOMMENDED'
                    or d.get('maude_classification') == 'EXTREME_OUTLIER'
                    or d.get('recalls_total', 0) >= 2]

    if not avoid_devices:
        return "✅ **No critical risk devices identified.** All devices in dataset are potentially acceptable.\n"

    avoid_list = "| K-Number | Manufacturer | Critical Issues | Rationale |\n"
    avoid_list += "|----------|--------------|-----------------|----------|\n"

    for device in avoid_devices[:10]:  # Max 10
        k_num = device.get('KNUMBER', 'N/A')
        mfr = device.get('APPLICANT', 'N/A')[:30]  # Truncate long names

        issues = []
        if device.get('maude_classification') == 'EXTREME_OUTLIER':
            issues.append('EXTREME_OUTLIER MAUDE')
        if device.get('recalls_total', 0) >= 2:
            issues.append(f"{device.get('recalls_total')} recalls")
        if device.get('predicate_acceptability') == 'NOT_RECOMMENDED':
            issues.append('NOT_RECOMMENDED')

        issues_str = ', '.join(issues)
        rationale = device.get('acceptability_rationale', 'See detailed reports')[:50]

        avoid_list += f"| {k_num} | {mfr} | {issues_str} | {rationale} |\n"

    return avoid_list

def generate_recommendation_list(best_predicates: List[Dict]) -> str:
    """Generate list of recommended predicates"""
    rec_list = "| Rank | K-Number | Manufacturer | Score | Key Strengths |\n"
    rec_list += "|------|----------|--------------|-------|---------------|\n"

    for i, device in enumerate(best_predicates, 1):
        k_num = device.get('KNUMBER', 'N/A')
        mfr = device.get('APPLICANT', 'N/A')[:30]
        score = device.get('predicate_score', 0)

        strengths = []
        if device.get('maude_classification') in ['EXCELLENT', 'GOOD']:
            strengths.append(f"{device.get('maude_classification')} MAUDE")
        if device.get('recalls_total', 0) == 0:
            strengths.append('No recalls')
        if device.get('predicate_clinical_history') == 'NO':
            strengths.append('No clinical data')

        strengths_str = ', '.join(strengths) if strengths else 'ACCEPTABLE'

        rec_list += f"| {i} | {k_num} | {mfr} | {score} | {strengths_str} |\n"

    return rec_list

def generate_cost_driver_list(cost_drivers: List[str]) -> str:
    """Format cost drivers as bullet list"""
    return '\n'.join([f"- {driver}" for driver in cost_drivers])

def generate_next_steps(risk_summary: Dict, resources: Dict) -> str:
    """Generate actionable next steps"""
    steps = []

    # Step 1: Always review top predicates
    steps.append("1. **Review Top 5 Recommended Predicates** - Verify technical similarity and commercial availability")

    # Step 2: Risk-dependent actions
    if risk_summary['critical_risk_level'] == 'HIGH':
        steps.append("2. **Critical Risk Mitigation** - Conduct manual FDA MAUDE analysis for EXTREME_OUTLIER devices")
        steps.append("3. **Expand Predicate Search** - Consider alternative product codes to find safer predicates")
    else:
        steps.append("2. **Technical Comparison** - Perform detailed SE comparison with top 2-3 predicates")

    # Step 3: Clinical data planning
    clinical_pct = (risk_summary['clinical_data_required'] / risk_summary['total_devices']) * 100

    if clinical_pct > 30:
        steps.append(f"3. **Clinical Strategy** - {clinical_pct:.0f}% of predicates needed clinical data. Engage clinical team early.")
    else:
        steps.append("3. **Testing Plan** - Define bench and animal testing protocols based on predicate comparison")

    # Step 4: Budget/timeline confirmation
    steps.append(f"4. **Budget Approval** - Secure ${resources['budget_min']:,}-${resources['budget_max']:,} budget and {resources['timeline_months_min']}-{resources['timeline_months_max']} month timeline")

    # Step 5: Regulatory consultation
    steps.append("5. **RA Professional Review** - Have qualified regulatory expert verify all findings before submission")

    return '\n'.join(steps)
```

---

## 4. Implementation Plan

### 4.1 File Structure

**New File:** `/plugins/fda-tools/lib/executive_summary.py`

```python
"""
Executive Summary Generation Module - Phase 4
==============================================

Generates 1-2 page executive summaries from enrichment data for decision-makers.

Version: 4.0.0
Date: 2026-02-13
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import os

# All functions from Section 3 go here
```

**Integration Point:** `/plugins/fda-tools/commands/batchfetch.md`

Add after `generate_intelligence_report()` call (around line 1362):

```python
# Phase 4: Executive Summary Generation
if '--enrich' in arguments:
    from lib.executive_summary import generate_executive_summary, save_executive_summary

    print("\n📋 Generating executive summary...")
    exec_summary = generate_executive_summary(
        enriched_rows=enriched_rows,
        project_dir=PROJECT_DIR,
        quality_report_exists=os.path.exists(os.path.join(PROJECT_DIR, 'quality_report.md'))
    )

    summary_path = save_executive_summary(exec_summary, PROJECT_DIR)
    print(f"✓ Executive summary: {summary_path}")
```

### 4.2 Testing Strategy

**Unit Tests:** `/plugins/fda-tools/tests/test_executive_summary.py`

```python
import pytest
from lib.executive_summary import (
    calculate_risk_summary,
    identify_best_predicates,
    estimate_resources,
    generate_executive_summary
)

def test_calculate_risk_summary_high_risk():
    """Test high risk scenario (>30% critical issues)"""
    devices = [
        {'maude_classification': 'EXTREME_OUTLIER', 'predicate_acceptability': 'NOT_RECOMMENDED',
         'recalls_total': 3, 'recall_class': 'Class I', 'predicate_clinical_history': 'YES'},
        {'maude_classification': 'EXTREME_OUTLIER', 'predicate_acceptability': 'NOT_RECOMMENDED',
         'recalls_total': 2, 'recall_class': 'Class II', 'predicate_clinical_history': 'YES'},
        {'maude_classification': 'GOOD', 'predicate_acceptability': 'ACCEPTABLE',
         'recalls_total': 0, 'recall_class': '', 'predicate_clinical_history': 'NO'},
    ]

    result = calculate_risk_summary(devices)

    assert result['total_devices'] == 3
    assert result['extreme_outlier_count'] == 2
    assert result['not_recommended_count'] == 2
    assert result['critical_risk_level'] == 'HIGH'
    assert result['risk_percentage'] == pytest.approx(66.7, abs=0.1)

def test_identify_best_predicates_scoring():
    """Test predicate scoring algorithm"""
    devices = [
        {'KNUMBER': 'K240001', 'maude_classification': 'EXCELLENT',
         'predicate_acceptability': 'ACCEPTABLE', 'recalls_total': 0,
         'DECISIONDATE': '2024-01-15', 'predicate_clinical_history': 'NO'},
        {'KNUMBER': 'K190001', 'maude_classification': 'EXTREME_OUTLIER',
         'predicate_acceptability': 'NOT_RECOMMENDED', 'recalls_total': 3,
         'DECISIONDATE': '2019-06-20', 'predicate_clinical_history': 'YES'},
    ]

    best = identify_best_predicates(devices, top_n=2)

    assert best[0]['KNUMBER'] == 'K240001'  # Should rank first
    assert best[0]['predicate_score'] > best[1]['predicate_score']
    assert best[1]['KNUMBER'] == 'K190001'  # Should rank last

def test_estimate_resources_high_clinical():
    """Test resource estimation with high clinical data requirements"""
    devices = [
        {'predicate_clinical_history': 'YES', 'special_controls_applicable': 'YES'},
        {'predicate_clinical_history': 'YES', 'special_controls_applicable': 'NO'},
        {'predicate_clinical_history': 'NO', 'special_controls_applicable': 'NO'},
    ]

    result = estimate_resources(devices)

    # 67% clinical data -> should trigger high clinical impact
    assert result['timeline_months_min'] >= 18  # 6 base + 12 clinical
    assert result['budget_min'] >= 400000  # 50K base + 350K clinical
    assert 'Clinical studies' in result['key_cost_drivers'][0]

def test_generate_executive_summary_structure():
    """Test executive summary generation produces valid markdown"""
    devices = [
        {'KNUMBER': 'K240001', 'PRODUCTCODE': 'DQY', 'APPLICANT': 'Test Corp',
         'DEVICENAME': 'Test Device', 'DECISIONDATE': '2024-01-15',
         'maude_classification': 'EXCELLENT', 'predicate_acceptability': 'ACCEPTABLE',
         'recalls_total': 0, 'predicate_clinical_history': 'NO',
         'special_controls_applicable': 'NO', 'maude_productcode_5y': 100,
         'predicate_score': 150}
    ]

    summary = generate_executive_summary(devices, '/tmp/test_project')

    # Structure assertions
    assert '# Executive Summary' in summary
    assert '## Key Findings' in summary
    assert '## Devices to Avoid' in summary
    assert '## Recommended Predicates' in summary
    assert '## Resource Planning' in summary
    assert '## Next Steps' in summary
    assert 'IMPORTANT DISCLAIMER' in summary

    # Content assertions
    assert 'DQY' in summary  # Product code mentioned
    assert '1 device' in summary  # Device count
    assert 'LOW' in summary or 'MEDIUM' in summary  # Risk level present
```

**Integration Test:** Test with real Phase 1-3 data from test suite

```python
def test_executive_summary_integration_dqy():
    """Integration test with DQY (cardiovascular) product code"""
    # Load DQY enriched data from test fixtures
    import json
    with open('/home/linux/fda-510k-data/projects/rounds/round_fix1/DQY/enriched_devices.json') as f:
        enriched_rows = json.load(f)

    summary = generate_executive_summary(enriched_rows, '/tmp/dqy_test')

    # Validate DQY-specific expectations
    assert 'DQY' in summary
    assert len(enriched_rows) in summary  # Device count

    # Should contain valid recommendations
    assert '## Recommended Predicates' in summary
    assert 'K' in summary  # K-numbers present
```

### 4.3 Output File Format

**File:** `executive_summary.md`

**Location:** `{project_dir}/executive_summary.md`

**Example Output:**

```markdown
# Executive Summary - FDA 510(k) Predicate Analysis

**Generated:** 2026-02-13 14:30 UTC
**Project:** DQY_2024_Predicates
**Scope:** 47 devices across 1 product code(s): DQY

---

## 🎯 Key Findings

### Overall Risk Assessment: **MEDIUM**

**MODERATE RISKS DETECTED** (12.8% of devices have notable issues)

- ⚠️ **2 devices** flagged as EXTREME_OUTLIER (avoid these)
- 📋 **6 devices** have recall history (review details)
- ✅ **41 devices** are potentially acceptable

**RECOMMENDATION:** Focus on devices marked ACCEPTABLE. Review recalled predicates carefully.

### Top 3 Insights

1. **Favorable Clinical Profile:** Only 8% of predicates needed clinical data. Bench testing likely sufficient.
2. **Fragmented Market:** 23 manufacturers. No dominant player.
3. **Strong Safety Profile:** 32/47 devices (68%) have EXCELLENT/GOOD MAUDE ratings.

---

## ⚠️ Devices to Avoid (Critical Risks)

| K-Number | Manufacturer | Critical Issues | Rationale |
|----------|--------------|-----------------|-----------|
| K193456 | ACME MEDICAL | EXTREME_OUTLIER MAUDE, 3 recalls | Multiple recalls indicate systematic issues |
| K184521 | BETA DEVICES | NOT_RECOMMENDED, 2 recalls | Review recall details to assess if design issues... |

---

## ✅ Recommended Predicates (Top 5)

| Rank | K-Number | Manufacturer | Score | Key Strengths |
|------|----------|--------------|-------|---------------|
| 1 | K241234 | GAMMA TECH | 165 | EXCELLENT MAUDE, No recalls, No clinical data |
| 2 | K235678 | DELTA SYSTEMS | 155 | GOOD MAUDE, No recalls |
| 3 | K229876 | EPSILON CORP | 145 | EXCELLENT MAUDE, No recalls |
| 4 | K213456 | ZETA MEDICAL | 140 | GOOD MAUDE, No recalls, No clinical data |
| 5 | K207890 | ETA DEVICES | 135 | EXCELLENT MAUDE |

---

## 💰 Resource Planning

**Estimated Timeline:** 6-12 months
**Estimated Budget:** $50,000 - $75,000

**Key Cost Drivers:**
- Base 510(k) preparation

---

## 📋 Next Steps

1. **Review Top 5 Recommended Predicates** - Verify technical similarity and commercial availability
2. **Technical Comparison** - Perform detailed SE comparison with top 2-3 predicates
3. **Testing Plan** - Define bench and animal testing protocols based on predicate comparison
4. **Budget Approval** - Secure $50,000-$75,000 budget and 6-12 month timeline
5. **RA Professional Review** - Have qualified regulatory expert verify all findings before submission

---

## 📚 Detailed Reports

For comprehensive analysis, see:
- `quality_report.md` - Data quality and API validation
- `intelligence_report.md` - Clinical data and acceptability analysis
- `competitive_intelligence_DQY.md` - Market analysis per product code
- `regulatory_context.md` - CFR citations and FDA guidance
- `enrichment_report.html` - Interactive visual dashboard

---

**IMPORTANT DISCLAIMER:** This executive summary is generated from FDA openFDA API data
and is intended for research and intelligence purposes only. All findings MUST be
independently verified by qualified Regulatory Affairs professionals before being
relied upon for submission decisions. See individual reports for detailed disclaimers.
```

---

## 5. Prioritization Rules

### 5.1 Issue Priority Matrix

| Priority | Criteria | Action | Weight |
|----------|----------|--------|--------|
| **CRITICAL** | `maude_classification == 'EXTREME_OUTLIER'` | DO NOT USE - must appear in "Devices to Avoid" | -100 pts |
| **CRITICAL** | `predicate_acceptability == 'NOT_RECOMMENDED'` | DO NOT USE - must appear in "Devices to Avoid" | -100 pts |
| **CRITICAL** | `recall_class == 'Class I'` AND `recalls_total >= 2` | DO NOT USE - patient safety risk | -100 pts |
| **HIGH** | `recalls_total >= 2` (any class) | REVIEW REQUIRED - multiple quality issues | -50 pts |
| **HIGH** | `maude_classification == 'CONCERNING'` | REVIEW REQUIRED - above 75th percentile | -20 pts |
| **MEDIUM** | `predicate_clinical_history == 'YES'` | Budget for clinical studies | -5 pts |
| **MEDIUM** | `predicate_acceptability == 'REVIEW_REQUIRED'` | Manual review before use | -10 pts |
| **LOW** | Clearance age > 15 years | Verify current standard compliance | -20 pts |
| **POSITIVE** | `maude_classification == 'EXCELLENT'` | Strong safety record | +20 pts |
| **POSITIVE** | `recalls_total == 0` | No quality issues | +10 pts |
| **POSITIVE** | `predicate_clinical_history == 'NO'` | Simpler regulatory path | +10 pts |
| **POSITIVE** | Clearance age < 5 years | Recent standards compliance | +10 pts |

### 5.2 Summary Section Priority

**Order of sections (most to least important):**

1. **Risk Assessment** (ALWAYS first - executives need to know "can we proceed?")
2. **Devices to Avoid** (Safety critical - prevent bad decisions)
3. **Recommended Predicates** (Actionable - what should we use?)
4. **Resource Planning** (Budget/timeline - business critical)
5. **Top Insights** (Context - "why these numbers?")
6. **Next Steps** (Actionable roadmap)

**Length Constraints:**
- Risk Assessment: 150-300 words
- Devices to Avoid: Max 10 devices, table format
- Recommended Predicates: Max 5 devices, table format
- Resource Planning: 100-200 words
- Top Insights: 3 insights, 50 words each
- Next Steps: 5 steps, bullet format

**Total Length Target:** 800-1200 words (2 pages printed)

---

## 6. Implementation Complexity Estimate

### 6.1 Development Effort

| Task | Complexity | Time Estimate | Rationale |
|------|------------|---------------|-----------|
| Core algorithm functions | Medium | 4 hours | Straightforward aggregation logic |
| Template generation functions | Low | 2 hours | String formatting, no complex logic |
| Integration with batchfetch.md | Low | 1 hour | Single function call insertion |
| Unit tests (10 tests) | Medium | 3 hours | Need diverse test scenarios |
| Integration tests (3 scenarios) | Medium | 2 hours | Test with real Phase 1-3 data |
| Documentation | Low | 1 hour | Docstrings and README updates |
| **TOTAL** | **Medium** | **13 hours** | ~2 working days |

### 6.2 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Template too verbose | Medium | Low | User testing, iteration on length |
| Scoring algorithm bias | Medium | Medium | Validate against RA professional judgment |
| Missing edge cases | Low | Medium | Comprehensive unit tests |
| Integration breaks existing flow | Low | High | Thorough integration testing |

### 6.3 Dependencies

**Code Dependencies:**
- `lib/fda_enrichment.py` - MUST exist (Phase 1-3 complete)
- `lib/disclaimers.py` - For compliance disclaimers
- Python stdlib only: `typing`, `datetime`, `os`, `json`

**Data Dependencies:**
- `enriched_rows` with all 53 Phase 1-3 columns
- `quality_report.md` (optional - for cross-reference)
- `intelligence_report.md` (optional - for cross-reference)

**No External APIs Required** - All data from in-memory enriched_rows

---

## 7. Success Metrics

### 7.1 Functional Metrics

- [ ] Executive summary generates successfully for all 9 test archetypes
- [ ] Summary length: 800-1200 words (fits on 2 pages)
- [ ] Risk assessment matches manual expert classification (>90% agreement)
- [ ] Top 5 predicates scoring validated by RA professional
- [ ] Resource estimates within ±30% of actual project costs

### 7.2 Quality Metrics

- [ ] Test coverage >90% for executive_summary.py module
- [ ] All 13 unit tests pass
- [ ] 3 integration tests pass with real Phase 1-3 data
- [ ] Type hints on all functions (mypy strict mode)
- [ ] Docstrings on all public functions (Google style)

### 7.3 User Adoption Metrics

- [ ] Executives can make go/no-go decision from summary alone (validated with 3 stakeholders)
- [ ] Summary reduces report review time by >75% (from 2 hours to <30 min)
- [ ] Zero critical defects in production use (first 10 projects)

---

## 8. Future Enhancements (Phase 5+)

### 8.1 Optional Features (NOT in v4.0.0)

1. **Multi-format Output**
   - PDF generation with charts (using matplotlib/reportlab)
   - PowerPoint slide deck (using python-pptx)
   - Email-friendly HTML version

2. **Interactive Summary**
   - Web-based dashboard with drill-down
   - Filterable predicate tables (by manufacturer, clearance date)
   - Click-through to detailed reports

3. **Comparative Summaries**
   - Side-by-side comparison of multiple product codes
   - Trend analysis across quarterly batches
   - Competitive benchmarking

4. **AI-Enhanced Insights**
   - Use Claude API to generate natural language insights
   - Automatic anomaly detection in data patterns
   - Predictive timeline modeling based on historical data

### 8.2 Integration Opportunities

- **Email Notification:** Auto-send summary to stakeholders on completion
- **Slack/Teams Integration:** Post summary to channels
- **Project Management:** Auto-create tasks in Jira from Next Steps
- **Dashboard Integration:** Feed metrics into BI tools (Tableau, PowerBI)

---

## 9. Conclusion

### 9.1 Design Summary

This design delivers a **simple, template-based executive summary generator** that:

✅ **Solves the core problem:** Reduces 20-30 pages to 1-2 actionable pages
✅ **Low complexity:** 13 hours implementation, stdlib-only dependencies
✅ **High value:** Executives get go/no-go decision in <30 minutes
✅ **Production-ready:** Comprehensive testing, type hints, disclaimers
✅ **Maintainable:** Clear functions, well-documented, extensible

### 9.2 Recommended Implementation Approach

1. **Phase 4.1 (Week 1):** Implement core algorithm functions + unit tests
2. **Phase 4.2 (Week 1):** Implement template generation + integration tests
3. **Phase 4.3 (Week 2):** Integrate with batchfetch.md + validate with test suite
4. **Phase 4.4 (Week 2):** User acceptance testing with RA professionals
5. **Phase 4.5 (Week 3):** Documentation, deployment, monitoring

### 9.3 Key Decision: Template vs. AI

**RECOMMENDATION: Use template-based approach (as designed)**

**Rationale:**
- **Speed:** Instant generation vs 5-10 sec API latency
- **Cost:** $0 vs ~$0.05 per summary (at scale: $500/10K summaries)
- **Determinism:** Reproducible results for compliance
- **Offline:** Works without internet
- **Control:** Full control over disclaimers and legal language

**When to switch to AI:**
- User feedback indicates templates too rigid/repetitive
- Need for nuanced insights beyond data aggregation
- Budget allows $500+/month for API costs

---

## 10. Appendix

### 10.1 Example Test Data

**High Risk Scenario (test_executive_summary_high_risk.json):**
```json
[
  {
    "KNUMBER": "K240001",
    "PRODUCTCODE": "DQY",
    "APPLICANT": "ACME MEDICAL",
    "DEVICENAME": "CardioStent Pro",
    "DECISIONDATE": "2024-01-15",
    "maude_classification": "EXTREME_OUTLIER",
    "predicate_acceptability": "NOT_RECOMMENDED",
    "recalls_total": 3,
    "recall_class": "Class I",
    "predicate_clinical_history": "YES",
    "special_controls_applicable": "YES"
  }
]
```

### 10.2 Scoring Algorithm Validation

**Validation Dataset:** 50 devices manually scored by RA professional

**Expected Correlation:** Pearson r > 0.85 between algorithm score and expert score

**Calibration:** Adjust weights if correlation < 0.80

---

**END OF DESIGN DOCUMENT**

**Ready for Implementation:** Yes
**Approval Required:** Product Manager, RA Lead, Engineering Lead
**Estimated Delivery:** 3 weeks from approval
