# Genuine Manual Audit Template - FDA API Enrichment
## Phase 1 & 2 Production Verification

**Purpose:** Independent manual verification of enrichment accuracy against real FDA sources.
**Auditor:** ________________ (Name and role)
**Audit Date:** ________________
**Enrichment Version:** FDA Predicate Assistant v2.0.1
**Status:** ☐ IN PROGRESS / ☐ COMPLETED / ☐ ISSUES FOUND

---

## Overview

This is a **genuine manual audit**, not a simulated or extrapolated assessment. The auditor will:
1. Run actual `/fda-predicate-assistant:batchfetch --enrich` commands
2. Manually compare each enriched value against FDA API responses
3. Cross-check against FDA.gov web interfaces
4. Document actual findings (not estimates)
5. Calculate actual pass rates (not extrapolated)

**Target:** ≥95% overall pass rate to achieve PRODUCTION READY status

---

## Device Selection (Pre-Audit)

Select 5 devices from different risk categories and device types:

| # | Product Code | K-Number | Device Type | Risk Level | Rationale |
|---|--------------|----------|-------------|------------|-----------|
| 1 | DQY | _______ | Cardiovascular catheter | HIGH | Clinical data, high MAUDE |
| 2 | GEI | _______ | Electrosurgical unit | MEDIUM | Electrical safety focus |
| 3 | QKQ | _______ | Digital pathology software | MEDIUM | SaMD, software validation |
| 4 | KWP | _______ | Spinal fixation implant | HIGH | Sterile, mechanical |
| 5 | FRO | _______ | Wound dressing | MEDIUM | Recalls history |

**Device selection date:** ________________
**Devices selected by:** ________________

---

## Audit Execution

For each device, complete all 9 audit sections below. Estimated time: 1 hour per device.

---

### DEVICE 1 AUDIT

**K-Number:** ________________
**Product Code:** ________________
**Audit Date/Time:** ________________

#### Section 1: MAUDE Data Accuracy (10 minutes)

**Step 1.1:** Run enrichment command
```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools
/fda-predicate-assistant:batchfetch --product-codes [PRODUCT_CODE] --years 2024 --enrich --full-auto
```

**Step 1.2:** Extract enriched MAUDE value
- Enriched value from CSV: `maude_productcode_5y = ________`
- Enriched scope: `maude_scope = ________`

**Step 1.3:** Verify against openFDA API (manual)
```bash
curl "https://api.fda.gov/device/event.json?search=product_code:\"[CODE]\"&count=date_received" | jq '.results[:60] | map(.count) | add'
```
- API response (5-year total): ________
- Calculation method: Sum of last 60 months from results

**Step 1.4:** Cross-check against FDA.gov MAUDE database
- URL: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfmaude/search.cfm
- Search by product code, last 5 years
- Web interface count: ________ events
- Match enriched value: ☐ Yes (±5%) / ☐ No

**Determination:**
- ☐ PASS - Enriched value matches API/web (±5% tolerance)
- ☐ FAIL - Enriched value differs significantly (>5%)
- Actual discrepancy: ________%
- Notes: ________________

#### Section 2: Recall Data Accuracy (10 minutes)

**Step 2.1:** Extract enriched recall value
- Enriched value from CSV: `recalls_total = ________`
- Latest recall date: `recall_latest_date = ________`
- Recall class: `recall_class = ________`

**Step 2.2:** Verify against openFDA API
```bash
curl "https://api.fda.gov/device/recall.json?search=k_numbers:\"[K-NUMBER]\"&limit=10" | jq '.results | length'
```
- API response (recall count): ________

**Step 2.3:** Cross-check against FDA.gov recall database
- URL: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfres/res.cfm
- Search by K-number
- Web interface recall count: ________
- Match enriched value: ☐ Yes / ☐ No

**Determination:**
- ☐ PASS - Enriched value matches API/web exactly
- ☐ FAIL - Enriched value differs
- Actual discrepancy: ________
- Notes: ________________

#### Section 3: 510(k) Validation Accuracy (10 minutes)

**Step 3.1:** Extract enriched validation value
- Enriched value: `api_validated = ________`
- Decision description: `decision = ________`

**Step 3.2:** Verify against openFDA API
```bash
curl "https://api.fda.gov/device/510k.json?search=k_number:\"[K-NUMBER]\"&limit=1" | jq '.results[0].decision_description'
```
- API response: ________
- K-number found: ☐ Yes / ☐ No

**Step 3.3:** Cross-check against FDA.gov 510(k) database
- URL: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm
- Search by K-number
- Web interface shows clearance: ☐ Yes / ☐ No
- Decision matches: ☐ Yes / ☐ No

**Determination:**
- ☐ PASS - Validation status and decision match API/web
- ☐ FAIL - Validation status or decision differs
- Notes: ________________

#### Section 4: Data Provenance Completeness (5 minutes)

**Step 4.1:** Open enrichment_metadata.json
```bash
cat enrichment_metadata.json | jq '.per_device["[K-NUMBER]"]'
```

**Step 4.2:** Verify provenance fields for all data types
- MAUDE events provenance: ☐ Source / ☐ Timestamp / ☐ Scope / ☐ Confidence / ☐ Caveat
- Recalls provenance: ☐ Source / ☐ Timestamp / ☐ Scope / ☐ Confidence
- Validation provenance: ☐ Source / ☐ Timestamp / ☐ Scope / ☐ Confidence

**Determination:**
- Provenance coverage: _____% (count fields present / total fields × 100)
- ☐ PASS - 100% provenance coverage
- ☐ FAIL - <100% coverage (missing: ________)
- Notes: ________________

#### Section 5: Quality Score Accuracy (10 minutes)

**Step 5.1:** Extract enriched quality score
- Enriched score from CSV: `enrichment_completeness_score = ________`

**Step 5.2:** Manually calculate quality score components
Using formula from fda_enrichment.py:
- Data Completeness (40%): Count populated fields / 6 × 40 = ________
- API Success Rate (30%): Successful calls / Total calls × 30 = ________
- Data Freshness (20%): api_validated='Yes' → 20 pts, 'No' → 10 pts = ________
- Cross-validation (10%): maude_scope valid → 10 pts = ________
- **Manual total:** ________

**Determination:**
- Enriched score: ________
- Manual score: ________
- Difference: ________
- ☐ PASS - Within ±5 points
- ☐ FAIL - Differs by >5 points
- Notes: ________________

#### Section 6: Clinical Data Detection Appropriateness (5 minutes)

**Step 6.1:** Extract enriched clinical data
- `predicate_clinical_history = ________`
- `predicate_clinical_indicators = ________`

**Step 6.2:** Review decision description from Section 3
- Decision text: ________________

**Step 6.3:** Manual assessment
- Does decision mention clinical data keywords? ☐ Yes / ☐ No
- Keywords found: ________________
- Clinical history determination appropriate? ☐ Yes / ☐ No

**Determination:**
- ☐ PASS - Clinical detection matches decision text
- ☐ FAIL - Clinical detection doesn't match decision text
- Notes: ________________

#### Section 7: Standards Guidance Appropriateness (5 minutes)

**Step 7.1:** Determine device characteristics
- Product code: ________
- Device type: ________________
- Expected standards categories (manual): ________________

**Step 7.2:** Review enrichment guidance
- Standards guidance provided: ☐ Yes / ☐ No
- Guidance appropriate for device type: ☐ Yes / ☐ No / ☐ N/A (conservative approach)

**Determination:**
- ☐ PASS - Standards guidance appropriate or appropriately conservative
- ☐ FAIL - Standards guidance inappropriate
- Notes: ________________

#### Section 8: Predicate Chain Health Accuracy (5 minutes)

**Step 8.1:** Extract enriched acceptability
- `predicate_acceptability = ________`
- `predicate_risk_factors = ________`

**Step 8.2:** Manual assessment based on audit findings
- Recalls found (Section 2): ________
- Clearance age: ________ years
- Expected acceptability: ☐ ACCEPTABLE / ☐ REVIEW_REQUIRED / ☐ NOT_RECOMMENDED

**Determination:**
- ☐ PASS - Acceptability determination matches audit findings
- ☐ FAIL - Acceptability determination doesn't match
- Notes: ________________

#### Section 9: Disclaimer Presence (5 minutes)

**Step 9.1:** Check all output files for disclaimers
- 510k_download_enriched.csv header: ☐ Disclaimer present / ☐ Missing
- enrichment_report.html banner: ☐ Disclaimer present / ☐ Missing
- quality_report.md header: ☐ Disclaimer present / ☐ Missing
- regulatory_context.md: ☐ Disclaimer present / ☐ Missing
- intelligence_report.md: ☐ Disclaimer present / ☐ Missing
- enrichment_metadata.json disclaimers section: ☐ Present / ☐ Missing

**Determination:**
- Disclaimers present: _____/6 files
- ☐ PASS - All 6 files have disclaimers
- ☐ FAIL - <6 files have disclaimers
- Notes: ________________

---

### DEVICE 1 SUMMARY

| Section | Status | Pass/Fail |
|---------|--------|-----------|
| 1. MAUDE Data Accuracy | ________ | ☐ PASS / ☐ FAIL |
| 2. Recall Data Accuracy | ________ | ☐ PASS / ☐ FAIL |
| 3. 510(k) Validation Accuracy | ________ | ☐ PASS / ☐ FAIL |
| 4. Data Provenance Completeness | ________% | ☐ PASS / ☐ FAIL |
| 5. Quality Score Accuracy | ________  | ☐ PASS / ☐ FAIL |
| 6. Clinical Data Detection | ________ | ☐ PASS / ☐ FAIL |
| 7. Standards Guidance | ________ | ☐ PASS / ☐ FAIL |
| 8. Predicate Chain Health | ________ | ☐ PASS / ☐ FAIL |
| 9. Disclaimer Presence | _____/6 | ☐ PASS / ☐ FAIL |

**Device 1 Pass Rate:** _____/9 (_____%)

---

### DEVICE 2-5 AUDITS

[Repeat sections 1-9 for each device using same template structure]

**Device 2 Pass Rate:** _____/9 (_____%)
**Device 3 Pass Rate:** _____/9 (_____%)
**Device 4 Pass Rate:** _____/9 (_____%)
**Device 5 Pass Rate:** _____/9 (_____%)

---

## Aggregate Results

### Overall Pass Rates

| Category | Total Sections | Passed | Failed | Pass Rate |
|----------|----------------|--------|--------|-----------|
| MAUDE Data Accuracy | 5 | _____ | _____ | _____% |
| Recall Data Accuracy | 5 | _____ | _____ | _____% |
| 510(k) Validation Accuracy | 5 | _____ | _____ | _____% |
| Data Provenance Completeness | 5 | _____ | _____ | _____% |
| Quality Score Accuracy | 5 | _____ | _____ | _____% |
| Clinical Data Detection | 5 | _____ | _____ | _____% |
| Standards Guidance | 5 | _____ | _____ | _____% |
| Predicate Chain Health | 5 | _____ | _____ | _____% |
| Disclaimer Presence | 5 | _____ | _____ | _____% |
| **TOTAL** | **45** | **_____** | **_____** | **_____%** |

### Critical Issues

☐ **No critical issues found**
☐ **Critical issues found** (list):

**Issue 1:** ________________
**Affected Devices:** ________________
**Impact:** ________________
**Required Fix:** ________________

**Issue 2:** ________________
**Affected Devices:** ________________
**Impact:** ________________
**Required Fix:** ________________

### Moderate Issues

☐ **No moderate issues found**
☐ **Moderate issues found** (list):

**Issue 1:** ________________
**Issue 2:** ________________

---

## Production Readiness Determination

### Success Criteria

**Required:** Overall pass rate ≥95%
**Actual:** _____% pass rate

☐ **PASS** - ≥95% pass rate achieved
☐ **FAIL** - <95% pass rate (required actions below)

### Status Determination

Based on manual audit results:

☐ **✅ PRODUCTION READY**
- Overall pass rate: ≥95%
- Zero critical issues
- All disclaimers present
- Provenance tracking complete

☐ **⚠️ CONDITIONAL APPROVAL - FIXES REQUIRED**
- Overall pass rate: 80-94%
- No critical issues but moderate issues found
- Required fixes: ________________

☐ **❌ NOT READY FOR PRODUCTION**
- Overall pass rate: <80%
- Critical issues identified
- Significant fixes required: ________________

---

## Auditor Sign-Off

**I certify that I have personally conducted this manual audit by:**
1. Running actual enrichment commands on 5 selected devices
2. Manually verifying each enriched value against official FDA sources
3. Cross-checking data against both openFDA API and FDA.gov web interfaces
4. Calculating actual pass rates based on genuine findings (not estimates)
5. Documenting all discrepancies and issues found

**This is a genuine manual audit, not a simulated or extrapolated assessment.**

**Audited By:**
- Name: ________________
- Role: ________________
- Date: ________________
- Signature: ________________

**Audit Results:**
- Overall Pass Rate: _____%
- Production Status: ☐ READY / ☐ CONDITIONAL / ☐ NOT READY
- Critical Issues: _____ found
- Moderate Issues: _____ found

**Next Steps:**
- ☐ Approve for production use (if ≥95% pass rate, zero critical issues)
- ☐ Fix issues and re-audit (if <95% or critical issues found)
- ☐ Update MEMORY.md with production status

---

**END OF GENUINE MANUAL AUDIT TEMPLATE**
