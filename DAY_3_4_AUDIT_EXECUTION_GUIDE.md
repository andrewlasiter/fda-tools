# Day 3-4 Compliance Audit: Execution Guide

**Date:** 2026-02-13  
**Duration:** ~8 hours  
**Status:** Ready for execution

---

## Overview

This guide provides step-by-step instructions for completing the Day 3-4 Compliance Audit of FDA API Enrichment Phase 1 & 2 features.

**Objective:** Manually verify that enriched data matches FDA sources with ≥95% accuracy across 5 diverse devices.

---

## Prerequisites ✅

- [x] Day 1 & Day 2 testing complete (100% pass rate)
- [x] 5 devices selected (audit_device_selection.md)
- [x] Audit template available (COMPLIANCE_AUDIT_TEMPLATE.md)
- [x] Access to FDA.gov for manual verification
- [x] Batchfetch command functional

---

## Phase 1: Device Selection (COMPLETE)

**Selected Devices:**
1. **DQY** - Cardiovascular catheter (high-risk, clinical data)
2. **GEI** - Electrosurgical unit (powered/electrical)
3. **QKQ** - Digital pathology software (SaMD)
4. **KWP** - Spinal fixation implant (sterile)
5. **FRO** - Wound dressing (recall history)

---

## Phase 2: Run Enrichment on Each Device

### Device 1: DQY (Cardiovascular)

**Command:**
```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools
mkdir -p audit_outputs/device_1_DQY
cd audit_outputs/device_1_DQY

# Run enrichment
/fda-tools:batchfetch --product-codes DQY --years 2024 --enrich --full-auto
```

**Expected Output Files:**
1. ✅ `510k_download_enriched.csv` - CSV with 29 enrichment columns
2. ✅ `enrichment_metadata.json` - Provenance data
3. ✅ `quality_report.md` - Quality scoring report
4. ✅ `regulatory_context.md` - CFR citations and guidance
5. ✅ `intelligence_report.md` - Phase 2 analysis
6. ✅ `enrichment_report.html` - Visual dashboard

**Verification:**
```bash
ls -lh *.csv *.json *.md *.html
wc -l 510k_download_enriched.csv  # Should have rows
head -1 510k_download_enriched.csv | tr ',' '\n' | grep -E "clinical|standards|quality"
```

---

### Device 2: GEI (Electrosurgical)

**Command:**
```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools
mkdir -p audit_outputs/device_2_GEI
cd audit_outputs/device_2_GEI

/fda-tools:batchfetch --product-codes GEI --years 2024 --enrich --full-auto
```

**Expected Output Files:** (same 6 files as Device 1)

**Verification:**
```bash
ls -lh *.csv *.json *.md *.html
grep "IEC 60601" intelligence_report.md  # Should detect electrical standards
```

---

### Device 3: QKQ (Software)

**Command:**
```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools
mkdir -p audit_outputs/device_3_QKQ
cd audit_outputs/device_3_QKQ

/fda-tools:batchfetch --product-codes QKQ --years 2024 --enrich --full-auto
```

**Expected Output Files:** (same 6 files)

**Verification:**
```bash
ls -lh *.csv *.json *.md *.html
grep -E "IEC 62304|IEC 62366" intelligence_report.md  # Software standards
```

---

### Device 4: KWP (Sterile Implant)

**Command:**
```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools
mkdir -p audit_outputs/device_4_KWP
cd audit_outputs/device_4_KWP

/fda-tools:batchfetch --product-codes KWP --years 2024 --enrich --full-auto
```

**Expected Output Files:** (same 6 files)

**Verification:**
```bash
ls -lh *.csv *.json *.md *.html
grep -E "ISO 11135|ISO 11137" intelligence_report.md  # Sterilization standards
grep "ISO 10993" intelligence_report.md  # Biocompatibility
```

---

### Device 5: FRO (Wound Dressing)

**Command:**
```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools
mkdir -p audit_outputs/device_5_FRO
cd audit_outputs/device_5_FRO

/fda-tools:batchfetch --product-codes FRO --years 2024 --enrich --full-auto
```

**Expected Output Files:** (same 6 files)

**Verification:**
```bash
ls -lh *.csv *.json *.md *.html
grep -i "recall" quality_report.md  # May have recalls
```

---

## Phase 3: Manual Audit (5 hours)

For each of the 5 devices, complete the compliance audit using the template.

### Audit Checklist Per Device

**Print 5 copies of:** `COMPLIANCE_AUDIT_TEMPLATE.md`

For each device, complete these sections:

#### Section 1: Data Accuracy Verification (30 min per device)

**1.1 MAUDE Events**
- [ ] Extract `maude_product_code_events` from CSV
- [ ] Query FDA API manually:
  ```bash
  curl "https://api.fda.gov/device/event.json?search=product_code:\"DQY\"&count=date_received&limit=1000"
  ```
- [ ] Compare counts (allow ±5% for timing differences)
- [ ] Verify scope = PRODUCT_CODE in metadata.json
- [ ] Mark: ✅ PASS or ❌ FAIL

**1.2 Recalls**
- [ ] Extract `recall_count` from CSV
- [ ] Query FDA API manually:
  ```bash
  curl "https://api.fda.gov/device/recall.json?search=k_numbers:\"K######\"&limit=10"
  ```
- [ ] Compare recall counts and classifications
- [ ] Verify scope = DEVICE_SPECIFIC in metadata.json
- [ ] Mark: ✅ PASS or ❌ FAIL

**1.3 510(k) Validation**
- [ ] Extract `validated` column from CSV
- [ ] Query FDA API manually:
  ```bash
  curl "https://api.fda.gov/device/510k.json?search=k_number:\"K######\"&limit=1"
  ```
- [ ] Compare decision descriptions
- [ ] Cross-check with FDA.gov:
  ```
  https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K######
  ```
- [ ] Mark: ✅ PASS or ❌ FAIL

---

#### Section 2: Data Provenance Verification (15 min per device)

- [ ] Open `enrichment_metadata.json`
- [ ] Verify global fields present:
  - [ ] timestamp
  - [ ] api_version
  - [ ] per_device section
- [ ] For each enriched field, verify:
  - [ ] source (API endpoint)
  - [ ] query (search string)
  - [ ] timestamp
  - [ ] confidence (HIGH/MEDIUM/LOW)
  - [ ] scope (PRODUCT_CODE vs DEVICE_SPECIFIC)
- [ ] Calculate provenance coverage: (fields_with_provenance / total_enriched_fields) × 100%
- [ ] Mark: ✅ PASS (100%) or ❌ FAIL (<100%)

---

#### Section 3: CFR Citation Verification (10 min per device)

- [ ] Open `regulatory_context.md`
- [ ] For each applicable CFR (based on data present):

**21 CFR 803 (if MAUDE data present)**
- [ ] Citation present in file
- [ ] Verify URL: https://www.ecfr.gov/current/title-21/.../part-803
- [ ] URL resolves in browser
- [ ] Regulation applies to MAUDE
- [ ] Mark: ✅ PASS or ❌ FAIL

**21 CFR 7 (if recall data present)**
- [ ] Citation present in file
- [ ] Verify URL: https://www.ecfr.gov/current/title-21/.../part-7
- [ ] URL resolves in browser
- [ ] Regulation applies to recalls
- [ ] Mark: ✅ PASS or ❌ FAIL

**21 CFR 807 (if 510(k) validated)**
- [ ] Citation present in file
- [ ] Verify URL: https://www.ecfr.gov/current/title-21/.../part-807/subpart-E
- [ ] URL resolves in browser
- [ ] Regulation applies to 510(k)
- [ ] Mark: ✅ PASS or ❌ FAIL

---

#### Section 4: Guidance Document Verification (10 min per device)

- [ ] Open `regulatory_context.md`
- [ ] For each guidance document referenced:

**Medical Device Reporting (2016) - if MAUDE data**
- [ ] URL present in file
- [ ] URL accessible in browser
- [ ] Date: November 2016
- [ ] Not superseded (check FDA.gov)
- [ ] Mark: ✅ PASS or ❌ FAIL

**Product Recalls (2019) - if recall data**
- [ ] URL present in file
- [ ] URL accessible in browser
- [ ] Date: November 2019
- [ ] Not superseded
- [ ] Mark: ✅ PASS or ❌ FAIL

**510(k) Program SE (2014) - if validated**
- [ ] URL present in file
- [ ] URL accessible in browser
- [ ] Date: July 2014
- [ ] Not superseded
- [ ] Mark: ✅ PASS or ❌ FAIL

---

#### Section 5: Quality Score Verification (15 min per device)

- [ ] Extract `enrichment_quality_score` from CSV
- [ ] Open `quality_report.md`
- [ ] Manually calculate quality score:

**Formula:**
```
Score = Completeness(40) + API_Success(30) + Freshness(20) + Cross_Val(10)
```

**Completeness (40 points):**
- Count populated enrichment columns: ____ / 29
- Percentage: ____ %
- Score: ____ % × 0.40 = ____ points

**API Success (30 points):**
- From quality_report.md API call summary
- Successful calls: ____ / ____
- Percentage: ____ %
- Score: ____ % × 0.30 = ____ points

**Freshness (20 points):**
- Data age: ____ days (from metadata.json timestamp)
- Score:
  - <30 days: 20 points
  - 30-90 days: 15 points
  - 90-180 days: 10 points
  - >180 days: 5 points
- Score: ____ points

**Cross-Validation (10 points):**
- Product code match in CSV: Yes = 10, No = 0
- Score: ____ points

**Manual Total:** ____ / 100
**Enriched Total:** ____ / 100
**Difference:** ____ points

- [ ] Verify within ±5 points
- [ ] Mark: ✅ PASS or ❌ FAIL

---

#### Section 6: Intelligence Analysis Verification (20 min per device)

**6.1 Clinical Data Detection**
- [ ] Extract `clinical_likely` from CSV (YES/PROBABLE/UNLIKELY/NO)
- [ ] Extract `clinical_indicators` from CSV
- [ ] Open `intelligence_report.md`
- [ ] Review decision_description for keywords:
  - "clinical study"
  - "clinical trial"
  - "postmarket surveillance"
  - "special controls"
- [ ] Manually assess: Does determination match evidence?
- [ ] Mark: ✅ PASS (appropriate) or ❌ FAIL (inappropriate)

**6.2 FDA Standards Intelligence**
- [ ] Extract from CSV:
  - `standards_count`
  - `standards_biocompat`
  - `standards_electrical`
  - `standards_sterile`
  - `standards_software`
- [ ] Based on device type, expect:
  - **DQY (catheter):** Biocompatibility (ISO 10993)
  - **GEI (electrical):** Electrical safety (IEC 60601)
  - **QKQ (software):** Software (IEC 62304, 62366)
  - **KWP (implant):** Biocompat + Sterile (ISO 10993, 11135/11137)
  - **FRO (wound):** May vary
- [ ] Verify enriched standards match device type
- [ ] Mark: ✅ PASS (appropriate) or ❌ FAIL (inappropriate)

**6.3 Predicate Chain Health**
- [ ] Extract from CSV:
  - `chain_health` (HEALTHY/CAUTION/TOXIC)
  - `chain_risk_flags`
- [ ] If predicates are referenced in device record:
  - [ ] Check each predicate for recalls via FDA API
  - [ ] Verify chain_health matches recall findings
- [ ] Mark: ✅ PASS or ❌ FAIL

---

## Phase 4: Aggregate Report (30 min)

After completing all 5 device audits:

### Summary Statistics

**Calculate:**
- Total sections audited: ____ (10 sections × 5 devices = 50)
- Sections passed: ____
- Sections failed: ____
- Overall pass rate: ____ %

**By Category:**

| Category | Devices Passed | Pass Rate |
|----------|----------------|-----------|
| MAUDE Accuracy | ____ / 5 | ____ % |
| Recall Accuracy | ____ / 5 | ____ % |
| 510(k) Validation | ____ / 5 | ____ % |
| Provenance | ____ / 5 | ____ % |
| CFR Citations | ____ / 5 | ____ % |
| Guidance Docs | ____ / 5 | ____ % |
| Quality Score | ____ / 5 | ____ % |
| Clinical Detection | ____ / 5 | ____ % |
| Standards Analysis | ____ / 5 | ____ % |
| Predicate Chain | ____ / 5 | ____ % |
| **TOTAL** | ____ / 50 | ____ % |

### Issue Classification

**Critical Issues (FDA compliance risk):**
- [ ] List any critical issues found
- [ ] Impact assessment
- [ ] Immediate actions required

**High Issues (data integrity):**
- [ ] List any high-severity issues
- [ ] Recommendations for fixes

**Medium Issues (quality/accuracy):**
- [ ] List any medium-severity issues
- [ ] Long-term improvements

**Low Issues (minor/cosmetic):**
- [ ] List any low-severity issues
- [ ] Optional enhancements

### Final Compliance Determination

**Criteria:**
- ✅ **PRODUCTION READY:** ≥95% pass rate, 0 critical issues
- ⚠️ **CONDITIONALLY READY:** 90-95% pass rate, minor issues only
- ❌ **NOT READY:** <90% pass rate or critical issues present

**Your Determination:**
- Pass Rate: ____ %
- Critical Issues: ____
- Status: ________________

---

## Phase 5: Documentation Update

After audit completion:

1. **Update MEMORY.md:**
   ```markdown
   ## Day 3-4 Compliance Audit Results (2026-02-13)
   - Devices audited: 5 (DQY, GEI, QKQ, KWP, FRO)
   - Overall pass rate: ____%
   - Critical issues: ____
   - Compliance status: ________________
   - Date verified: 2026-02-13
   ```

2. **Create USER_GUIDE.md:**
   - How to interpret enriched CSV columns
   - Understanding quality scores
   - Scope limitations (PRODUCT_CODE vs DEVICE_SPECIFIC)
   - CFR citation usage in submissions
   - Data provenance for audits

3. **Update RELEASE_ANNOUNCEMENT.md:**
   - Mark as "Compliance Verified" if passed
   - Include audit results summary
   - Add user guide reference

---

## Expected Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Device Selection | 30 min | ✅ COMPLETE |
| Run Enrichment (5 devices) | 2 hours | ⏳ PENDING |
| Manual Audit (5 devices) | 5 hours | ⏳ PENDING |
| Aggregate Report | 30 min | ⏳ PENDING |
| Documentation Update | 30 min | ⏳ PENDING |
| **TOTAL** | **~8 hours** | **⏳ IN PROGRESS** |

---

## Quick Commands Reference

**Run enrichment:**
```bash
/fda-tools:batchfetch --product-codes [CODE] --years 2024 --enrich --full-auto --project audit_device_[N]_[CODE]
```

**Check output files:**
```bash
ls -lh audit_outputs/device_*/
```

**Extract data from CSV:**
```bash
head -1 510k_download_enriched.csv | tr ',' '\n' | nl
```

**Query FDA API:**
```bash
curl "https://api.fda.gov/device/[endpoint].json?search=k_number:\"K######\"&limit=1"
```

**Verify CFR URLs:**
```
https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-[XXX]
```

---

**END OF EXECUTION GUIDE**

Ready to begin Phase 2: Run Enrichment
