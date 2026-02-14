# Phase 3 Advanced Analytics — Implementation Roadmap

**Version:** 3.0.0 (Design)
**Date:** 2026-02-13
**Total Effort:** 8 hours + 1 hour buffer = **9 hours**
**Target Completion:** 1 week sprint (2-3 hours/day)

---

## Week-at-a-Glance

```
Day 1 (Mon)    ███████░░░░░░  Sprint 1: MAUDE Peer Comparison (Part 1)
Day 2 (Tue)    ███████░░░░░░  Sprint 1: MAUDE Peer Comparison (Part 2)
Day 3 (Wed)    ██████░░░░░░░  Sprint 2: Review Time ML (Part 1)
Day 4 (Thu)    ██████░░░░░░░  Sprint 2: Review Time ML (Part 2)
Day 5 (Fri)    ████░░░░░░░░░  Sprint 3: Competitive Intelligence + Buffer
```

**Legend:** █ = Development ░ = Testing/Buffer

---

## Day-by-Day Breakdown

### Day 1 (Monday, 2.5 hours) — MAUDE Peer Comparison Foundation

**Morning Session (1.5 hours)**
- ✅ **Task 1.1:** Set up development environment
  - Install numpy (if not present)
  - Create `tests/test_phase3_feature1.py` test file
  - Review Phase 1+2 code structure
- ✅ **Task 1.2:** Implement cohort building
  - Add `build_peer_cohort()` function to `fda_enrichment.py`
  - Test on DQY product code (expect ~47 devices from 2020-2025)
  - Add caching logic (avoid re-querying same cohort)

**Afternoon Session (1 hour)**
- ✅ **Task 1.3:** Implement MAUDE collection with fallback
  - Add `get_maude_events_for_device()` with hierarchical search
  - Test K-number search → brand name fallback → combined search
  - Verify data quality scoring (HIGH/MEDIUM/LOW/ZERO_RESULTS)

**Deliverable:** Cohort building + MAUDE collection functions working
**Test:** `python3 -c "from lib.fda_enrichment import FDAEnrichment; e = FDAEnrichment(); cohort = e.build_peer_cohort('DQY', 2020); print(len(cohort))"`

---

### Day 2 (Tuesday, 2 hours) — MAUDE Peer Comparison Completion

**Morning Session (1.5 hours)**
- ✅ **Task 2.1:** Statistical analysis implementation
  - Add `analyze_maude_peer_distribution()` using numpy
  - Calculate median, percentiles (25/75/90/95), IQR
  - Test with sample cohort data
- ✅ **Task 2.2:** Device classification logic
  - Add `classify_device_maude_profile()` function
  - Implement percentile-based classification (EXCELLENT → EXTREME_OUTLIER)
  - Add recommendation text generation

**Afternoon Session (0.5 hours)**
- ✅ **Task 2.3:** Markdown report generation
  - Create `templates/maude_peer_analysis_template.md`
  - Implement report rendering with tables (statistical distribution, outlier devices)
  - Add disclaimers using `disclaimers.py` module
- ✅ **Task 2.4:** CSV integration
  - Add 7 new columns to enrichment output
  - Test with sample DQY batch

**Deliverable:** MAUDE Peer Comparison feature complete
**Test:** Run on real DQY batch (10 devices), verify markdown report generates

---

### Day 3 (Wednesday, 2 hours) — Review Time ML Foundation

**Morning Session (1.5 hours)**
- ✅ **Task 3.1:** Training data collection
  - Add `build_review_time_training_data()` function
  - Query openFDA 510k API for 2020-2025 clearances by product code
  - Calculate review_days (decision_date - date_received)
  - Test with DQY (expect ~2,000+ training samples across 5 product codes)
- ✅ **Task 3.2:** Feature engineering
  - Add `extract_device_complexity_features()` function
  - Implement keyword matching (software, implant, sterile, etc.)
  - Calculate complexity score (0-100)

**Afternoon Session (0.5 hours)**
- ✅ **Task 3.3:** Set up ML pipeline
  - Install scikit-learn (add to requirements.txt)
  - Create `tests/test_phase3_feature2.py` test file
  - Prepare training data DataFrame structure

**Deliverable:** Training data collection + feature engineering working
**Test:** Verify feature extraction on 10 sample devices

---

### Day 4 (Thursday, 1.5 hours) — Review Time ML Completion

**Morning Session (1 hour)**
- ✅ **Task 4.1:** Model training implementation
  - Add `train_review_time_model()` using RandomForestRegressor
  - Implement 5-fold cross-validation
  - Calculate feature importance
  - Add model caching (~/.fda_cache/review_time_model_{product_code}.pkl)
- ✅ **Task 4.2:** Prediction function
  - Add `predict_device_review_time()` function
  - Generate confidence intervals (80% CI using forest prediction std)
  - Classify as FASTER/AVERAGE/SLOWER vs cohort median

**Afternoon Session (0.5 hours)**
- ✅ **Task 4.3:** Markdown report generation
  - Create `templates/review_time_predictions_template.md`
  - Render model performance metrics (MAE, R², feature importance)
  - Render per-device predictions with recommendations
- ✅ **Task 4.4:** CSV integration
  - Add 6 new columns to enrichment output

**Deliverable:** Review Time ML feature complete
**Test:** Train on 2020-2024 data, validate on 2025 data, verify MAE <35 days

---

### Day 5 (Friday, 1.5 hours) — Competitive Intelligence + Testing

**Morning Session (1 hour)**
- ✅ **Task 5.1:** Competitor identification
  - Add `identify_competitors_in_product_code()` function
  - Group clearances by applicant (fuzzy matching for name variations)
  - Classify market position (DOMINANT/MAJOR/MODERATE/EMERGING)
- ✅ **Task 5.2:** Pipeline analysis
  - Add `analyze_competitor_pipeline()` function
  - Aggregate clearances, recalls, technology features per competitor
  - Parse predicates from decision descriptions (NLP)
- ✅ **Task 5.3:** Predicate network + technology trends
  - Add `analyze_predicate_usage_patterns()` — count citations, identify "gold standard"
  - Add `detect_technology_trends_in_market()` — keyword analysis with YoY comparison

**Afternoon Session (0.5 hours)**
- ✅ **Task 5.4:** Markdown report generation
  - Create `templates/competitive_intelligence_template.md`
  - Render market leaders table, predicate network, technology trends
- ✅ **Task 5.5:** Integration testing
  - Run full Phase 3 enrichment on DQY batch (10 devices)
  - Verify all 3 reports generate correctly
  - Check CSV has all 42 columns

**Deliverable:** Competitive Intelligence feature complete + Phase 3 fully integrated
**Test:** End-to-end test on DQY, GEI, QKQ product codes

---

### Buffer Time (1 hour) — Testing & Documentation

**Allocated for:**
- Bug fixes from integration testing
- Performance optimization (if needed)
- Documentation updates (README, MEMORY.md)
- Disclaimer verification (all reports have warnings)

---

## File Structure After Phase 3

```
plugins/fda-predicate-assistant/
├── lib/
│   ├── fda_enrichment.py           # MODIFIED: +3 new functions (500 lines → 750 lines)
│   ├── disclaimers.py              # NO CHANGE (disclaimers already comprehensive)
│   └── __init__.py
├── commands/
│   └── batchfetch.md               # MODIFIED: Add Phase 3 enrichment steps
├── templates/                      # NEW DIRECTORY
│   ├── maude_peer_analysis_template.md
│   ├── review_time_predictions_template.md
│   └── competitive_intelligence_template.md
├── tests/
│   ├── test_phase1.py              # EXISTING
│   ├── test_phase2.py              # EXISTING
│   ├── test_phase3_feature1.py     # NEW: MAUDE peer comparison tests
│   ├── test_phase3_feature2.py     # NEW: Review time ML tests
│   └── test_phase3_feature3.py     # NEW: Competitive intelligence tests
└── docs/
    ├── PHASE3_ADVANCED_ANALYTICS_DESIGN.md      # NEW: Full design spec
    ├── PHASE3_EXECUTIVE_SUMMARY.md              # NEW: Executive summary
    └── PHASE3_IMPLEMENTATION_ROADMAP.md         # NEW: This file

Root directory:
├── requirements.txt                # MODIFIED: Add numpy, scikit-learn
└── ~/.fda_cache/                   # NEW: Model cache directory
    ├── review_time_model_DQY.pkl
    ├── review_time_model_GEI.pkl
    └── ...
```

---

## Code Changes Summary

### `lib/fda_enrichment.py` — New Functions (7)

**Feature 1: MAUDE Peer Comparison (3 functions)**
```python
def build_peer_cohort(product_code, clearance_year_min) -> List[Dict]
def get_maude_events_for_device(k_number, brand_name, product_code) -> Dict
def analyze_maude_peer_distribution(cohort_data) -> Dict
def classify_device_maude_profile(device_events, distribution) -> Dict
def analyze_maude_peer_comparison(device_row, cohort_devices) -> Dict  # PUBLIC API
```

**Feature 2: Review Time ML (3 functions)**
```python
def build_review_time_training_data(product_codes, years) -> pd.DataFrame
def extract_device_complexity_features(device_name, decision_desc) -> Dict
def train_review_time_model(training_data) -> Dict
def predict_device_review_time(device_row) -> Dict  # PUBLIC API
def _train_or_load_review_time_model() -> Dict  # INTERNAL: caching logic
```

**Feature 3: Competitive Intelligence (4 functions)**
```python
def identify_competitors_in_product_code(product_code, years) -> List[Dict]
def analyze_competitor_pipeline(applicant, product_code, years) -> Dict
def analyze_predicate_usage_patterns(competitors) -> Dict
def detect_technology_trends_in_market(clearances) -> Dict
def analyze_competitive_landscape(product_code, years) -> Dict  # PUBLIC API
```

**Total new code:** ~300 lines (fda_enrichment.py grows from 636 → 936 lines)

---

### `commands/batchfetch.md` — New Steps (3)

**Add after existing Phase 2 enrichment:**

```markdown
## Step 5.5: MAUDE Peer Comparison (Phase 3)

For each unique product code in batch with ≥15 devices in last 5 years:

1. Build peer cohort (cached per product code)
2. For each device, call enricher.analyze_maude_peer_comparison()
3. Append 7 new columns to CSV
4. Generate maude_peer_analysis.md report

Skip if cohort <15 devices (insufficient for statistical analysis)

---

## Step 5.6: Review Time Prediction (Phase 3)

For each unique product code in batch:

1. Train or load review time model (cached at ~/.fda_cache/)
2. For each device, call enricher.predict_device_review_time()
3. Append 6 new columns to CSV
4. Generate review_time_predictions.md report

Model training takes 1-2 minutes (first run only, then cached for 30 days)

---

## Step 5.7: Competitive Intelligence (Phase 3)

For each unique product code in batch:

1. Call enricher.analyze_competitive_landscape()
2. Generate competitive_intelligence_{product_code}.md report
3. No CSV columns added (aggregate analysis only)

Execution time: ~30-60 seconds per product code
```

**Total new lines:** ~50 lines (batchfetch.md grows minimally)

---

### `requirements.txt` — New Dependencies (2)

```
numpy>=1.24.0          # Statistical calculations (already may be present)
scikit-learn>=1.3.0    # ML model (RandomForest)
```

**Note:** pandas likely already required for Phase 1+2 data handling

---

## Testing Strategy

### Unit Tests (3 new files)

**`tests/test_phase3_feature1.py` — MAUDE Peer Comparison**
```python
def test_cohort_building()
def test_maude_collection_fallback()
def test_statistical_distribution()
def test_device_classification()
def test_outlier_detection()
```

**`tests/test_phase3_feature2.py` — Review Time ML**
```python
def test_training_data_collection()
def test_feature_extraction()
def test_model_training()
def test_prediction_accuracy()
def test_confidence_intervals()
def test_model_caching()
```

**`tests/test_phase3_feature3.py` — Competitive Intelligence**
```python
def test_competitor_identification()
def test_pipeline_analysis()
def test_predicate_network()
def test_technology_trends()
def test_market_position_classification()
```

**Total test lines:** ~400 lines across 3 files

---

### Integration Tests

**Test Dataset: DQY, GEI, QKQ (3 product codes)**
- DQY: Large cohort (47 devices) — high confidence test
- GEI: Medium cohort (28 devices) — medium confidence test
- QKQ: Small cohort (15 devices) — edge case test

**Test Execution:**
```bash
# Run Phase 3 enrichment on test batch
cd /home/linux/.claude/plugins/marketplaces/fda-tools
python3 -c "
from plugins.fda_predicate_assistant.lib.fda_enrichment import FDAEnrichment
import json

# Load test batch (10 devices across DQY, GEI, QKQ)
devices = [...]  # Sample devices

# Enrich with Phase 3
enricher = FDAEnrichment()
api_log = []
enriched_devices = []

for device in devices:
    enriched = enricher.enrich_single_device(device, api_log)

    # Phase 3 Feature 1: MAUDE peer comparison
    cohort = enricher.build_peer_cohort(device['PRODUCTCODE'], 2020)
    maude_analysis = enricher.analyze_maude_peer_comparison(enriched, cohort)
    enriched.update(maude_analysis)

    # Phase 3 Feature 2: Review time prediction
    review_prediction = enricher.predict_device_review_time(enriched)
    enriched.update(review_prediction)

    enriched_devices.append(enriched)

# Phase 3 Feature 3: Competitive intelligence (per product code)
for product_code in ['DQY', 'GEI', 'QKQ']:
    competitive_intel = enricher.analyze_competitive_landscape(product_code, years=3)
    # Generate markdown report...

print(f'Enriched {len(enriched_devices)} devices with Phase 3 features')
print(f'CSV columns: {len(enriched_devices[0].keys())}')  # Should be 42
"
```

**Acceptance Criteria:**
- ✅ All 42 CSV columns present
- ✅ MAUDE peer analysis report generated for each product code
- ✅ Review time predictions report generated (aggregated)
- ✅ Competitive intelligence report generated for each product code
- ✅ No crashes or API errors
- ✅ All disclaimers present in reports

---

## Performance Benchmarks

### Target Performance (per batch of 50 devices, 3 product codes)

**Phase 3 Feature 1: MAUDE Peer Comparison**
- Cohort building: <5 seconds per product code (cached after first run)
- MAUDE collection: <30 seconds per 50-device cohort (with API rate limits)
- Statistical analysis: <1 second
- **Total:** ~45 seconds per product code

**Phase 3 Feature 2: Review Time ML**
- Training data collection: <30 seconds per product code (cached)
- Model training: <2 minutes per product code (cached for 30 days)
- Predictions: <1 second per device (instant after model loaded)
- **Total:** ~2 minutes first run, <5 seconds subsequent runs (cached model)

**Phase 3 Feature 3: Competitive Intelligence**
- Competitor identification: <10 seconds per product code
- Pipeline analysis: <20 seconds per product code (API queries)
- Predicate network + trends: <5 seconds
- **Total:** ~35 seconds per product code

**GRAND TOTAL (50 devices, 3 product codes, first run):**
- Feature 1: 3 × 45 sec = 135 sec (2.25 min)
- Feature 2: 3 × 2 min = 6 min (first run), 15 sec (cached)
- Feature 3: 3 × 35 sec = 105 sec (1.75 min)
- **Total first run:** ~10 minutes
- **Total subsequent runs:** ~5 minutes (model cached)

**User experience:** Add progress indicators for each phase

---

## Risk Mitigation

### Technical Risks & Solutions

**Risk 1: MAUDE K-number indexing gaps**
- **Probability:** HIGH (30-50% devices may have zero K-number results)
- **Impact:** MEDIUM (reduces statistical power)
- **Mitigation:** ✅ Brand name fallback hierarchy implemented
- **Acceptance:** Flag as "MEDIUM/LOW data quality" when fallback used

**Risk 2: Small training cohorts (<50 devices)**
- **Probability:** MEDIUM (rare product codes)
- **Impact:** HIGH (unreliable ML predictions)
- **Mitigation:** ✅ Require minimum 50 devices, flag LOW confidence if <50
- **Acceptance:** Use cohort median as fallback (no ML prediction)

**Risk 3: API rate limit violations**
- **Probability:** LOW (existing 0.25s delay = 4 req/sec = safe)
- **Impact:** MEDIUM (API 429 errors, failed enrichment)
- **Mitigation:** ✅ Existing rate limiting in Phase 1, add caching for cohort data
- **Acceptance:** Graceful degradation (skip phase if API fails)

**Risk 4: Model overfitting (review time ML)**
- **Probability:** MEDIUM (small training sets)
- **Impact:** LOW (predictions unreliable but flagged as LOW confidence)
- **Mitigation:** ✅ 5-fold cross-validation, limit RandomForest depth=10
- **Acceptance:** Cross-validation MAE used as confidence metric

**Risk 5: Applicant name variations (competitive intel)**
- **Probability:** HIGH (e.g., "Medtronic Inc" vs "Medtronic plc")
- **Impact:** MEDIUM (fragmented competitor counts)
- **Mitigation:** ✅ Fuzzy matching for top 10 competitors, manual verification step
- **Acceptance:** Note limitation in competitive intelligence disclaimer

---

### User Experience Risks & Solutions

**Risk 6: Overwhelming output (8 report files)**
- **Probability:** MEDIUM (users may not read all reports)
- **Impact:** LOW (valuable data underutilized)
- **Mitigation:** ✅ Add "Key Insights" section at top of each report
- **Acceptance:** HTML report provides navigation to all markdown reports

**Risk 7: Misinterpretation of ML predictions**
- **Probability:** HIGH (users citing "predicted 127 days" as fact)
- **Impact:** HIGH (regulatory misuse)
- **Mitigation:** ✅ Prominent disclaimers in all reports: "ESTIMATES FOR PLANNING ONLY"
- **Acceptance:** Add to HTML banner: "ML predictions are NOT guarantees"

**Risk 8: Confusion about MAUDE scope**
- **Probability:** MEDIUM (product-code vs device-specific confusion)
- **Impact:** MEDIUM (data misuse in submissions)
- **Mitigation:** ✅ Existing Phase 1 disclaimers + Feature 1 explicitly labels "device-specific attempts with fallback"
- **Acceptance:** Repeat disclaimer in every MAUDE table

---

## Rollout Plan

### Phase 3.0 Beta (Week 1) — Internal Testing
**Scope:** Deploy to development environment only
**Testing:** Run on DQY, GEI, QKQ batches (30 devices total)
**Validation:**
- ✅ All 3 features working
- ✅ Reports generate correctly
- ✅ CSV has 42 columns
- ✅ Disclaimers present
**Go/No-Go:** If >80% devices enrich successfully → proceed to alpha

---

### Phase 3.0 Alpha (Week 2) — Limited Release
**Scope:** Release to 3-5 early adopter RA professionals
**Feedback Collection:**
- Report clarity and usefulness
- Accuracy of MAUDE classifications (manual verification of 5 outliers)
- Review time prediction vs actual (compare predictions to real clearances)
- Competitive intelligence insights (did they discover new predicates?)

**Bug Fixes:** Address critical issues only

---

### Phase 3.0 General Release (Week 3) — Production Deployment
**Prerequisites:**
- ✅ Beta testing complete (no critical bugs)
- ✅ Alpha feedback incorporated (UX improvements)
- ✅ Documentation updated (MEMORY.md, README)
- ✅ Disclaimers verified (compliance review)

**Release Announcement:**
- Update MEMORY.md with Phase 3 features
- Create PHASE3_RELEASE_NOTES.md
- Update batchfetch command documentation

---

## Success Criteria

### Phase 3 is considered SUCCESSFUL if:

**Functional:**
- ✅ All 3 features implemented and working
- ✅ 8 report files generate correctly (5 existing + 3 new)
- ✅ CSV enrichment adds 13 new columns (7 + 6 + 0)
- ✅ No critical bugs (crashes, data corruption)

**Performance:**
- ✅ Enrichment completes in <10 minutes for 50-device batch (first run)
- ✅ Subsequent enrichment <5 minutes (model cached)
- ✅ No API rate limit violations (<4 req/sec maintained)

**Accuracy:**
- ✅ MAUDE outlier classification: 100% match manual review (5 test cases)
- ✅ Review time ML: MAE <35 days (cross-validation)
- ✅ Competitive intel: Competitor counts ±10% of manual verification

**Usability:**
- ✅ Reports are clear and actionable (validated by RA professionals)
- ✅ Disclaimers are prominent and comprehensive
- ✅ CSV columns are self-explanatory (good naming)

**Compliance:**
- ✅ All outputs include "RESEARCH USE ONLY" disclaimers
- ✅ MAUDE scope limitations clearly stated
- ✅ ML predictions flagged as estimates, not guarantees
- ✅ Competitive intel marked as NOT for FDA submission

---

## Post-Implementation Checklist

### Before Marking Phase 3 Complete:

**Code Quality:**
- [ ] All functions have docstrings (Args, Returns, Examples)
- [ ] Type hints added (e.g., `-> Dict[str, Any]`)
- [ ] Error handling implemented (graceful degradation if API fails)
- [ ] Code follows Phase 1+2 patterns (consistency)

**Testing:**
- [ ] Unit tests pass (100%)
- [ ] Integration tests pass on DQY, GEI, QKQ
- [ ] Performance benchmarks met (<10 min first run)
- [ ] Manual validation of 5 MAUDE outliers, 5 review predictions, 3 competitor analyses

**Documentation:**
- [ ] MEMORY.md updated with Phase 3 summary
- [ ] PHASE3_RELEASE_NOTES.md created
- [ ] batchfetch.md updated with new steps
- [ ] README updated (if necessary)

**Compliance:**
- [ ] Disclaimers added to all 3 new reports
- [ ] HTML report banner includes Phase 3 warnings
- [ ] CSV header includes Phase 3 scope limitations

**User Feedback:**
- [ ] Alpha testing with 3-5 RA professionals
- [ ] Usability issues addressed
- [ ] Feature requests logged for Phase 4

---

## Phase 4 Preview (Future Work)

**Once Phase 3 is stable, consider:**

1. **Automated Gap Analysis** (6 hours)
   - Compare YOUR device specs against predicate requirements
   - Identify missing tests/docs automatically

2. **Smart Predicate Recommendations** (4 hours)
   - AI-powered predicate ranking based on SE likelihood
   - Weighted scoring (feature similarity + safety + age + acceptance)

3. **Real-Time Monitoring** (4 hours)
   - Daily FDA database change alerts
   - Competitor watch lists
   - Predicate health monitoring (alert if predicate recalled)

**Total Phase 4 Effort:** 14 hours

---

## Conclusion

This roadmap provides a **detailed, day-by-day plan** for implementing Phase 3 Advanced Analytics in just **1 week** (9 hours total).

**Key Success Factors:**
- ✅ Well-scoped features (3.5 + 3 + 1.5 = 8 hours core + 1 buffer)
- ✅ Incremental delivery (Sprint 1 → 2 → 3)
- ✅ Robust testing strategy (unit + integration)
- ✅ Clear success criteria (functional, performance, accuracy, compliance)

**Ready to Start?**
1. Review this roadmap with stakeholders
2. Set up development environment (Day 1, Task 1.1)
3. Begin Sprint 1 (MAUDE Peer Comparison)

**Questions?** See full design specification: `PHASE3_ADVANCED_ANALYTICS_DESIGN.md`

---

**Roadmap Version:** 1.0
**Author:** Senior FDA Data Analytics Architect
**Date:** 2026-02-13
**Status:** READY FOR IMPLEMENTATION
