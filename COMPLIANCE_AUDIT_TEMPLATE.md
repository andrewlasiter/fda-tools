# Compliance Audit Template: FDA API Enrichment

**Purpose:** Manual deep verification of Phase 1 & 2 enrichment data accuracy for regulatory compliance

**Auditor:** _[Name]_  
**Date:** _[YYYY-MM-DD]_  
**Device:** _[K-Number]_

---

## Device Information

| Field | Value |
|-------|-------|
| K-Number | |
| Device Name | |
| Product Code | |
| Applicant | |
| Decision Date | |
| Device Class | |
| Regulation Number | |

---

## Section 1: Data Accuracy Verification

### 1.1 MAUDE Events (Product Code Level)

**Enriched Data (from CSV):**
- Column: `maude_product_code_events`
- Value: ___________ events

**FDA API Manual Verification:**
```
API Query: https://api.fda.gov/device/event.json?search=product_code:"[CODE]"&count=date_received&limit=1000
```

- API Response: ___________ events
- Match Status: ☐ EXACT MATCH  ☐ WITHIN 5%  ☐ MISMATCH

**FDA.gov Cross-Check:**
```
URL: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfmaude/search.cfm
Filter: Product Code = [CODE]
```

- FDA.gov Count: ___________ events
- Match Status: ☐ MATCH  ☐ MISMATCH

**Scope Verification:**
- Metadata JSON scope field: ☐ PRODUCT_CODE  ☐ OTHER
- CSV column name clarity: ☐ Clear  ☐ Ambiguous
- Documentation disclaimer: ☐ Present  ☐ Missing

**Assessment:** ☐ PASS  ☐ FAIL

**Notes:**
```



```

---

### 1.2 Recalls (Device-Specific)

**Enriched Data (from CSV):**
- Column: `recall_count`
- Value: ___________ recalls
- Column: `recall_classification`
- Value: ___________

**FDA API Manual Verification:**
```
API Query: https://api.fda.gov/device/recall.json?search=k_numbers:"[K-NUMBER]"&limit=10
```

- API Response: ___________ recalls
- Classifications: ___________
- Event Dates: ___________
- Match Status: ☐ EXACT MATCH  ☐ MISMATCH

**FDA.gov Cross-Check:**
```
URL: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRes/res.cfm?start_search=1&knumber=[K-NUMBER]
```

- FDA.gov Recall Count: ___________
- FDA.gov Classifications: ___________
- Match Status: ☐ MATCH  ☐ MISMATCH

**Scope Verification:**
- Metadata JSON scope field: ☐ DEVICE_SPECIFIC  ☐ OTHER
- Recall details complete: ☐ Yes  ☐ No

**Assessment:** ☐ PASS  ☐ FAIL

**Notes:**
```



```

---

### 1.3 510(k) Validation

**Enriched Data (from CSV):**
- Column: `validated`
- Value: ☐ YES  ☐ NO
- Column: `decision_description`
- Value: ___________

**FDA API Manual Verification:**
```
API Query: https://api.fda.gov/device/510k.json?search=k_number:"[K-NUMBER]"&limit=1
```

- API Response: ___________
- Decision: ___________
- Device Name: ___________
- Applicant: ___________
- Decision Date: ___________
- Match Status: ☐ EXACT MATCH  ☐ MISMATCH

**FDA.gov Cross-Check:**
```
URL: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=[K-NUMBER]
```

- FDA.gov Decision: ___________
- Match Status: ☐ MATCH  ☐ MISMATCH

**Assessment:** ☐ PASS  ☐ FAIL

**Notes:**
```



```

---

## Section 2: Data Provenance Verification

### 2.1 Enrichment Metadata (enrichment_metadata.json)

**File Existence:**
- ☐ enrichment_metadata.json present
- ☐ File is valid JSON
- ☐ Per-device entry for [K-NUMBER] present

**Global Metadata:**
- ☐ timestamp field present: ___________
- ☐ api_version field present: ___________
- ☐ source system identified

**Per-Device Provenance (MAUDE Events):**
- ☐ source: device/event.json
- ☐ query: product_code:"[CODE]"
- ☐ timestamp: ___________
- ☐ confidence: ☐ HIGH  ☐ MEDIUM  ☐ LOW
- ☐ scope: ☐ PRODUCT_CODE  ☐ OTHER

**Per-Device Provenance (Recalls):**
- ☐ source: device/recall.json
- ☐ query: k_numbers:"[K-NUMBER]"
- ☐ timestamp: ___________
- ☐ confidence: ☐ HIGH  ☐ MEDIUM  ☐ LOW
- ☐ scope: ☐ DEVICE_SPECIFIC  ☐ OTHER

**Per-Device Provenance (510(k) Validation):**
- ☐ source: device/510k.json
- ☐ query: k_number:"[K-NUMBER]"
- ☐ timestamp: ___________
- ☐ confidence: ☐ HIGH  ☐ MEDIUM  ☐ LOW
- ☐ scope: ☐ DEVICE_SPECIFIC  ☐ OTHER

**Provenance Completeness:**
- Total enriched fields: ___________
- Fields with provenance: ___________
- Coverage: ___________ %

**Assessment:** ☐ PASS (100% coverage)  ☐ FAIL (<100%)

**Notes:**
```



```

---

## Section 3: CFR Citation Verification

### 3.1 Regulatory Context File (regulatory_context.md)

**File Existence:**
- ☐ regulatory_context.md present
- ☐ CFR section present in file

**21 CFR 803 (MAUDE)**

If MAUDE data present in enrichment:

- ☐ Citation present in cfr_citations column
- ☐ Citation format: "21 CFR 803" or "21 CFR Part 803"
- ☐ Referenced in regulatory_context.md

**Manual URL Verification:**
```
URL: https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-803
```

- ☐ URL resolves (HTTP 200)
- ☐ Regulation title matches: "Medical Device Reporting"
- ☐ Regulation applies to MAUDE data
- ☐ Key sections present: 803.3, 803.50, 803.52

**Assessment:** ☐ PASS  ☐ FAIL

---

**21 CFR 7 (Recalls)**

If recall data present in enrichment:

- ☐ Citation present in cfr_citations column
- ☐ Citation format: "21 CFR 7" or "21 CFR Part 7"
- ☐ Referenced in regulatory_context.md

**Manual URL Verification:**
```
URL: https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-7
```

- ☐ URL resolves (HTTP 200)
- ☐ Regulation title matches: "Enforcement Policy"
- ☐ Subpart C covers recalls (sections 7.40-7.59)
- ☐ Recall classifications match 21 CFR 7.41(a)

**Assessment:** ☐ PASS  ☐ FAIL

---

**21 CFR 807 (510(k) Validation)**

If 510(k) validated:

- ☐ Citation present in cfr_citations column
- ☐ Citation format: "21 CFR 807" or "21 CFR Part 807 Subpart E"
- ☐ Referenced in regulatory_context.md

**Manual URL Verification:**
```
URL: https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-807/subpart-E
```

- ☐ URL resolves (HTTP 200)
- ☐ Regulation title matches: "Premarket Notification"
- ☐ Subpart E covers 510(k) (sections 807.87, 807.92, 807.95)

**Assessment:** ☐ PASS  ☐ FAIL

**CFR Citation Overall Assessment:** ☐ PASS (all applicable CFRs correct)  ☐ FAIL

---

## Section 4: Guidance Document Verification

### 4.1 Guidance References (regulatory_context.md)

**Medical Device Reporting for Manufacturers (2016)**

If MAUDE data present:

- ☐ Guidance referenced in regulatory_context.md
- ☐ Title correct: "Medical Device Reporting for Manufacturers"
- ☐ Date correct: 2016-12-19 or November 2016

**Manual URL Verification:**
```
URL: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/medical-device-reporting-manufacturers
```

- ☐ URL accessible (manual browser check)
- ☐ Docket number: FDA-2013-D-0743
- ☐ Document applies to MAUDE/MDR data
- ☐ Not superseded (checked FDA.gov search)

**Assessment:** ☐ PASS  ☐ FAIL  ☐ N/A

---

**Product Recalls, Including Removals and Corrections (2019)**

If recall data present:

- ☐ Guidance referenced in regulatory_context.md
- ☐ Title correct: "Product Recalls, Including Removals and Corrections"
- ☐ Date correct: 2019-11-07 or November 2019

**Manual URL Verification:**
```
URL: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/product-recalls-including-removals-and-corrections
```

- ☐ URL accessible (manual browser check)
- ☐ Document applies to recall classifications
- ☐ Not superseded (checked FDA.gov search)

**Assessment:** ☐ PASS  ☐ FAIL  ☐ N/A

---

**The 510(k) Program: Evaluating Substantial Equivalence (2014)**

If 510(k) validated:

- ☐ Guidance referenced in regulatory_context.md
- ☐ Title correct: "The 510(k) Program: Evaluating Substantial Equivalence..."
- ☐ Date correct: 2014-07-28 or July 2014

**Manual URL Verification:**
```
URL: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/510k-program-evaluating-substantial-equivalence-premarket-notifications-510k
```

- ☐ URL accessible (manual browser check)
- ☐ Document applies to SE determination
- ☐ Not superseded (checked FDA.gov search)

**Assessment:** ☐ PASS  ☐ FAIL  ☐ N/A

**Guidance Document Overall Assessment:** ☐ PASS (all applicable guidance valid)  ☐ FAIL

---

## Section 5: Quality Score Verification

### 5.1 Quality Report (quality_report.md)

**File Existence:**
- ☐ quality_report.md present
- ☐ Quality score for [K-NUMBER] present

**Enriched Quality Score (from CSV):**
- Column: `enrichment_quality_score`
- Value: ___________ / 100

**Manual Quality Score Calculation:**

**Formula:**
```
Score = Completeness(40) + API_Success(30) + Freshness(20) + Cross_Val(10)
```

**Completeness (40 points):**
- Fields populated: ___ / ___ = ____%
- Score: ___ × 0.40 = ___________ points

**API Success Rate (30 points):**
- API calls successful: ___ / ___ = ____%
- Score: ___ × 0.30 = ___________ points

**Freshness (20 points):**
- Data age: ___ days
- Score calculation:
  - <30 days: 20 points
  - 30-90 days: 15 points
  - 90-180 days: 10 points
  - >180 days: 5 points
- Score: ___________ points

**Cross-Validation (10 points):**
- Product code match: ☐ Yes (10 pts)  ☐ No (0 pts)
- Score: ___________ points

**Manual Calculated Score:**
___________ + ___________ + ___________ + ___________ = **___________ / 100**

**Score Comparison:**
- Enriched: ___________ / 100
- Manual: ___________ / 100
- Difference: ___________ points
- Within ±5: ☐ YES  ☐ NO

**Assessment:** ☐ PASS (within ±5 points)  ☐ FAIL

**Notes:**
```



```

---

## Section 6: Intelligence Analysis Verification

### 6.1 Clinical Data Detection (intelligence_report.md)

**File Existence:**
- ☐ intelligence_report.md present

**Enriched Data (from CSV):**
- Column: `clinical_likely`
- Value: ☐ YES  ☐ PROBABLE  ☐ UNLIKELY  ☐ NO
- Column: `clinical_indicators`
- Value: ___________

**Manual Analysis:**

Review decision_description from 510(k) record. Check for keywords:
- ☐ "clinical study"
- ☐ "clinical trial"
- ☐ "postmarket surveillance"
- ☐ "postmarket study"
- ☐ "special controls"

**Clinical Determination:**
- Manual assessment: ☐ YES  ☐ PROBABLE  ☐ UNLIKELY  ☐ NO
- Rationale: ___________

**Match:**
- Enriched vs Manual: ☐ MATCH  ☐ MISMATCH

**Assessment:** ☐ PASS (appropriate determination)  ☐ FAIL

**Notes:**
```



```

---

### 6.2 FDA Standards Intelligence

**Enriched Data (from CSV):**
- `standards_count`: ___________
- `standards_biocompat`: ___________
- `standards_electrical`: ___________
- `standards_sterile`: ___________
- `standards_software`: ___________

**Device Type Analysis:**

Based on device name, intended use, and product code, expected standards:

**Biocompatibility (ISO 10993):**
- Device contacts body: ☐ Yes  ☐ No
- Expected standards: ___________
- Enriched matches: ☐ Yes  ☐ No

**Electrical Safety (IEC 60601):**
- Device is powered/electrical: ☐ Yes  ☐ No
- Expected standards: ___________
- Enriched matches: ☐ Yes  ☐ No

**Sterilization (ISO 11135, 11137):**
- Device is sterile: ☐ Yes  ☐ No
- Expected standards: ___________
- Enriched matches: ☐ Yes  ☐ No

**Software (IEC 62304, 62366):**
- Device has software: ☐ Yes  ☐ No
- Expected standards: ___________
- Enriched matches: ☐ Yes  ☐ No

**Assessment:** ☐ PASS (standards appropriate)  ☐ FAIL (standards inappropriate)

**Notes:**
```



```

---

### 6.3 Predicate Chain Health

**Enriched Data (from CSV):**
- `chain_health`: ☐ HEALTHY  ☐ CAUTION  ☐ TOXIC
- `chain_risk_flags`: ___________

**Manual Verification:**

If predicates referenced in device record, check each predicate for recalls:

**Predicate 1:** K-___________
- Recall check URL: https://api.fda.gov/device/recall.json?search=k_numbers:"K-___________"
- Recalls found: ___ (Classes: ___)
- Status: ☐ HEALTHY  ☐ RECALLED

**Predicate 2:** K-___________
- Recall check URL: https://api.fda.gov/device/recall.json?search=k_numbers:"K-___________"
- Recalls found: ___ (Classes: ___)
- Status: ☐ HEALTHY  ☐ RECALLED

**Manual Chain Health:**
- No predicates recalled: ☐ HEALTHY
- 1 predicate recalled (Class II/III): ☐ CAUTION
- ≥2 predicates recalled or Class I: ☐ TOXIC

**Match:**
- Enriched vs Manual: ☐ MATCH  ☐ MISMATCH

**Assessment:** ☐ PASS  ☐ FAIL

**Notes:**
```



```

---

## Section 7: Overall Compliance Assessment

### 7.1 Pass/Fail Summary

| Category | Status | Notes |
|----------|--------|-------|
| Data Accuracy - MAUDE | ☐ PASS  ☐ FAIL | |
| Data Accuracy - Recalls | ☐ PASS  ☐ FAIL | |
| Data Accuracy - 510(k) | ☐ PASS  ☐ FAIL | |
| Data Provenance | ☐ PASS  ☐ FAIL | |
| CFR Citations | ☐ PASS  ☐ FAIL | |
| Guidance Documents | ☐ PASS  ☐ FAIL | |
| Quality Score | ☐ PASS  ☐ FAIL | |
| Clinical Detection | ☐ PASS  ☐ FAIL | |
| Standards Analysis | ☐ PASS  ☐ FAIL | |
| Predicate Chain | ☐ PASS  ☐ FAIL | |

**Overall Device Assessment:**
- Total categories: 10
- Passed: ___________
- Failed: ___________
- Pass rate: ___________ %

☐ **PASS** - All categories passed (100%)  
☐ **CONDITIONAL** - Minor issues, 90-99% passed  
☐ **FAIL** - Critical issues or <90% passed

---

### 7.2 Issues Identified

**Critical Issues (FDA compliance risk):**
```
1.
2.
3.
```

**High Issues (data integrity concern):**
```
1.
2.
3.
```

**Medium Issues (quality/accuracy):**
```
1.
2.
3.
```

**Low Issues (minor/cosmetic):**
```
1.
2.
3.
```

---

### 7.3 Recommendations

**Immediate Actions:**
```
1.
2.
3.
```

**Short-term Improvements:**
```
1.
2.
3.
```

**Long-term Enhancements:**
```
1.
2.
3.
```

---

## Auditor Sign-Off

**Auditor Name:** _______________________  
**Title/Role:** _______________________  
**Regulatory Affairs Professional:** ☐ Yes  ☐ No  
**Date:** _______________________  
**Signature:** _______________________

**Final Determination:**

☐ Enriched data for [K-NUMBER] is **COMPLIANT** and suitable for FDA submission support  
☐ Enriched data for [K-NUMBER] requires **CORRECTIONS** before use  
☐ Enriched data for [K-NUMBER] is **NOT COMPLIANT** and should not be used

---

**End of Audit**
