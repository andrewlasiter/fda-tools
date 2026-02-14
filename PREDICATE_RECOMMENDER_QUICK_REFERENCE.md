# Predicate Recommender - Quick Reference Card

**Version:** 1.0.0
**Last Updated:** 2026-02-13

---

## Installation

```bash
# Install dependencies
pip install scikit-learn>=1.0.0 numpy>=1.21.0

# Verify
python3 -c "from sklearn.feature_extraction.text import TfidfVectorizer; print('OK')"
```

---

## Basic Usage

```python
from lib.predicate_recommender import PredicateRecommender
import json

# Initialize
recommender = PredicateRecommender()

# Load inputs
subject_device = json.load(open('device_profile.json'))
predicates = recommender.load_csv('510k_download_enriched.csv')

# Generate recommendations
recommendations = recommender.recommend_predicates(subject_device, predicates, top_n=5)

# Export
recommender.export_markdown(recommendations, 'output.md')
recommender.export_json(recommendations, 'output.json')
```

---

## Command-Line Usage

```bash
# Basic usage
python3 lib/predicate_recommender.py device_profile.json 510k_download_enriched.csv 5

# With batchfetch integration
/fda-predicate-assistant:batchfetch \
  --subject-device device_profile.json \
  --product-codes DQY \
  --years 2020-2025 \
  --enrich \
  --recommend-predicates \
  --full-auto
```

---

## Algorithm Weights (Tunable)

```python
# Default configuration
recommender = PredicateRecommender(
    similarity_weights={'text': 0.6, 'features': 0.4},
    ranking_weights={'similarity': 0.7, 'risk': 0.3}
)

# SaMD-optimized (emphasize text over materials)
recommender = PredicateRecommender(
    similarity_weights={'text': 0.85, 'features': 0.15},
    ranking_weights={'similarity': 0.7, 'risk': 0.3}
)

# Risk-averse (emphasize safety over similarity)
recommender = PredicateRecommender(
    similarity_weights={'text': 0.6, 'features': 0.4},
    ranking_weights={'similarity': 0.5, 'risk': 0.5}
)
```

---

## Scoring Formulas

### Similarity Score (0-100)
```
Similarity = (Text_Score × 0.6) + (Feature_Score × 0.4)

Text_Score = TF-IDF_Cosine_Similarity × 100

Feature_Score = Sterilization(15) + Materials(10) + Standards(5) + Dimensions(10)
```

### Risk Score (0-100, higher is better)
```
Risk = Base(100) + Bonuses - Penalties

Bonuses:
  + No recalls: +5
  + Recent clearance (≤2y): +10
  + MAUDE EXCELLENT: +10
  + No clinical data: +5

Penalties:
  - 1 recall: -15
  - ≥2 recalls: -30
  - MAUDE CONCERNING: -15
  - Clinical data required: -20
  - Age > 10 years: -2 per year (max -15)
```

### Final Score (0-100)
```
Final = (Similarity × 0.7) + (Risk × 0.3)
```

---

## Input Requirements

### device_profile.json (Subject Device)
```json
{
  "product_code": "DQY",                    // REQUIRED
  "device_name": "Test Catheter",           // REQUIRED
  "intended_use": "Device for...",          // REQUIRED (for text similarity)
  "device_description": "Consists of...",   // REQUIRED (for text similarity)
  "sterilization_method": "ethylene_oxide", // Optional (15 pts if match)
  "materials": ["titanium", "PEEK"],        // Optional (10 pts for overlap)
  "standards_referenced": ["ISO 10993-1"],  // Optional (5 pts for overlap)
  "indications_for_use": "Treatment of..."  // Optional (adds to text corpus)
}
```

### 510k_download_enriched.csv (Predicate Pool)
Must include Phase 1-3 enrichment columns:
- `KNUMBER`, `PRODUCTCODE`, `DEVICENAME`, `APPLICANT`, `DECISIONDATE`
- `decision_description`, `statement_or_summary` (for text similarity)
- `recalls_total`, `recall_class`, `recall_status`
- `maude_classification`, `maude_productcode_5y`
- `predicate_clinical_history`, `predicate_acceptability`
- `api_validated`

---

## Output Format

### predicate_recommendations.json
```json
{
  "subject_device": {...},
  "recommendations": [
    {
      "rank": 1,
      "k_number": "K252417",
      "device_name": "Amplatzer Piccolo Delivery System",
      "final_score": 87.4,
      "similarity_breakdown": {
        "similarity_score": 92.1,
        "text_score": 89.3,
        "feature_score": 96.5,
        "sterilization_match": "ethylene_oxide",
        "materials_overlap": "2/3",
        "standards_overlap": "3/4"
      },
      "risk_breakdown": {
        "risk_score": 75.0,
        "recalls_total": 0,
        "maude_classification": "GOOD",
        "bonuses": ["No recalls (+5 pts)", "Recent clearance (+10 pts)"],
        "penalties": []
      }
    }
  ],
  "search_summary": {
    "total_predicates_searched": 2000,
    "after_filtering": 287,
    "scored_candidates": 287,
    "recommendation_count": 5
  }
}
```

---

## Filter Chain (Stage 1)

```python
# All filters must pass (AND logic)
candidate_passes = (
    predicate['PRODUCTCODE'] == subject['product_code'] and
    predicate['maude_classification'] != 'EXTREME_OUTLIER' and
    predicate['predicate_acceptability'] != 'NOT_RECOMMENDED' and
    (current_year - clearance_year) <= 15 and
    predicate['api_validated'] == 'Yes'
)
```

---

## Performance Targets

| Candidate Pool Size | Target Time | Memory |
|---------------------|-------------|--------|
| 50 devices          | < 0.5s      | < 5 MB |
| 200 devices         | < 2.0s      | < 10 MB |
| 500 devices         | < 5.0s      | < 20 MB |
| 1000 devices        | < 10.0s     | < 30 MB |

---

## Testing

```bash
# Run unit tests
pytest tests/test_predicate_recommender.py -v

# Run specific test class
pytest tests/test_predicate_recommender.py::TestTextSimilarity -v

# Run with coverage
pytest tests/test_predicate_recommender.py --cov=lib.predicate_recommender
```

---

## Common Issues & Solutions

### Issue: Low similarity scores (< 60%) across all candidates
**Cause:** Subject device has sparse intended_use/device_description text
**Solution:** Add more text to `indications_for_use` field or reduce `top_n` to 3

### Issue: No candidates pass filtering
**Cause:** Product code has limited recent devices
**Solution:** Expand year range to 2015-2025 or relax age filter to 20 years

### Issue: TF-IDF vectorization fails
**Cause:** Empty text fields in subject or predicates
**Solution:** Check for null/empty `intended_use` and `decision_description` fields

### Issue: All recommendations have same score
**Cause:** Predicate pool has identical text (e.g., all "Device description not available")
**Solution:** Use `--enrich` flag to populate `statement_or_summary` from FDA API

---

## Debugging

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check filtering results
candidates = recommender.filter_candidates(subject, predicates)
print(f"Filtered: {len(predicates)} → {len(candidates)}")

# Inspect text similarity
subject_text = ' '.join([subject['intended_use'], subject['device_description']])
predicate_texts = [p.get('DEVICENAME', '') for p in candidates[:5]]
similarities = recommender.calculate_text_similarity(subject_text, predicate_texts)
print(f"Text similarities: {similarities}")

# Check feature extraction
for pred in candidates[:3]:
    sterilization = recommender.extract_sterilization(pred)
    materials = recommender.extract_materials(pred)
    print(f"{pred['KNUMBER']}: {sterilization}, {materials}")
```

---

## Customization Examples

### Increase weight of recent devices
```python
# Modify calculate_risk_score() in predicate_recommender.py
if age_years <= 2:
    bonus = 20  # Increased from 10
```

### Add custom material keywords
```python
recommender.material_keywords.update({'hdpe', 'uhmwpe', 'zirconia'})
```

### Require specific standard
```python
# After scoring, filter recommendations
filtered_recs = [
    r for r in recommendations['recommendations']
    if 'ISO 13485' in recommender.extract_standards(r['predicate'])
]
```

---

## API Reference

### PredicateRecommender Class

**Methods:**
- `filter_candidates(subject, predicates) → List[Dict]`
- `calculate_text_similarity(subject_text, predicate_texts) → ndarray`
- `calculate_feature_similarity(subject, predicate) → Dict`
- `calculate_risk_score(predicate) → Dict`
- `calculate_final_score(similarity, risk) → float`
- `recommend_predicates(subject, pool, top_n=5) → Dict`
- `load_csv(csv_path) → List[Dict]`
- `export_json(recommendations, output_path)`
- `export_markdown(recommendations, output_path)`

**Attributes:**
- `similarity_weights` (dict): {'text': 0.6, 'features': 0.4}
- `ranking_weights` (dict): {'similarity': 0.7, 'risk': 0.3}
- `vectorizer` (TfidfVectorizer): Trained TF-IDF model
- `material_keywords` (set): Material keyword dictionary
- `standards_patterns` (list): Regex patterns for standards extraction

---

## Known Limitations

1. **Sparse data:** Overestimates similarity by 5-10% when summaries are sparse
2. **Software standards:** IEC 62304/62366 not always extracted from text
3. **Large pools:** Performance degrades to 9-10s for 1000+ devices
4. **Combination products:** No explicit detection flag (Phase 4.1)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-13 | Initial release |

---

## Support & Documentation

- **Full Design:** SMART_PREDICATE_RECOMMENDATIONS_ML_DESIGN.md
- **Implementation Guide:** PREDICATE_RECOMMENDER_IMPLEMENTATION_GUIDE.md
- **Validation Results:** PREDICATE_RECOMMENDATION_VALIDATION.md
- **Executive Summary:** PHASE4_SMART_RECOMMENDATIONS_EXECUTIVE_SUMMARY.md

---

**Quick Reference Card Version:** 1.0
**Fits on:** 2-page printed document (double-sided)
**Target Audience:** Developers and RA professionals using the algorithm
