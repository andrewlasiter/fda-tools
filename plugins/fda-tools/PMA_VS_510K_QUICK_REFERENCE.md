# PMA vs. 510(k): Quick Reference Guide

**Date:** 2026-02-15
**Purpose:** Fast comparison and decision support for PMA plugin development

---

## At a Glance: PMA vs. 510(k)

| Dimension | 510(k) | PMA | Winner for Plugin |
|-----------|--------|-----|-------------------|
| **Annual Volume** | ~4,500 submissions | ~60 original PMAs | 510(k) (75x larger) |
| **Development Cost** | $100K-$500K | $10M-$100M | PMA (higher stakes = higher value) |
| **Timeline** | 6-12 months | 2-5 years | PMA (longer engagement) |
| **Predicate Concept** | Central requirement | N/A (no predicates) | 510(k) (predicate matching is automatable) |
| **Clinical Trials** | Rarely required | Almost always required | PMA (clinical intelligence = high value) |
| **Public Data** | Excellent (bulk ZIP, full summaries) | Limited (individual PDFs, no bulk) | 510(k) (easier data acquisition) |
| **OpenFDA API** | 40+ fields, full-text search | 24 fields, basic search | 510(k) (richer data) |
| **Standards** | Heavy reliance possible | Required + clinical data | TIE (same standards apply) |
| **Automation Potential** | High (predicate matching, SE tables) | Medium (clinical data needs expertise) | 510(k) |
| **User Expertise** | RA generalists | RA specialists + clinical | PMA (higher barrier = more need for help) |

**VERDICT:** 510(k) is better for volume/automation; PMA is better for value-per-customer

---

## The Big Differences (What Makes PMA Hard)

### 1. No Predicates = Different Logic
**510(k):** "My device is substantially equivalent to K123456 (predicate)"
**PMA:** "My device is safe and effective based on clinical trials showing X, Y, Z outcomes"

**Plugin Impact:** Can't reuse predicate selection, SE comparison, or predicate chain logic

### 2. Clinical Trials = Complex Data
**510(k):** Bench testing report: "Tested to ASTM F1717, passed"
**PMA:** 100-page clinical study report: "300-patient RCT at 25 sites, primary endpoint p<0.001, 15% adverse event rate, 5-year follow-up..."

**Plugin Impact:** Need medical expertise to interpret; hard to automate benefit-risk analysis

### 3. Limited Public Data = Scraping Challenge
**510(k):** Monthly ZIP file with all summaries; rich openFDA API
**PMA:** Individual SSED PDFs (must construct URLs and scrape); basic openFDA API

**Plugin Impact:** Data acquisition is 3x harder; no "batch download" shortcut

### 4. Supplement Complexity
**510(k):** Mostly "Traditional" or "Special" supplements
**PMA:** 180-Day, Real-Time, 30-Day Notice, Annual Report (each with different rules)

**Plugin Impact:** More complex workflow logic needed

---

## What's Reusable from 510(k) Plugin?

### Directly Reusable (90%+ code reuse)
- Standards intelligence (ISO 10993, IEC 60601, sterilization, software, orthopedic)
- MAUDE adverse events
- Recall tracking
- Product code classification
- Regulatory citations framework (21 CFR)
- Environmental assessment
- Financial disclosure templates

### Adaptable (50-70% code reuse)
- Device description templates (PMA needs more detail)
- Manufacturing section (PMA needs quality control detail)
- Labeling requirements (similar but PMA more restrictive)
- Enrichment metadata (same provenance tracking approach)
- Quality scoring (different criteria, same framework)

### Not Reusable (0% code reuse)
- Predicate selection
- SE comparison tables
- Predicate chain validation
- 510(k) summary parsing (different document structure)
- eSTAR field mapping (PMA uses eCopy, not eSTAR for modular)

---

## Development Effort: Three Options

### Option 1: Full PMA Support (430-600 hours = 3-4 months)
**Includes:**
- SSED PDF scraper and parser
- Clinical trial data extraction and intelligence
- PMA submission drafting templates (all 15 sections)
- Post-approval studies scraper
- Advisory panel analysis
- Modular PMA support
- IDE integration

**Pros:** Comprehensive solution comparable to 510(k) plugin
**Cons:** Large investment for small market (60 PMAs/year)
**Target Customer:** Large med device companies with Class III portfolios

---

### Option 2: Hybrid Approach (220-300 hours = 2-2.5 months) ⭐ RECOMMENDED
**Includes:**
- OpenFDA PMA API integration
- SSED PDF scraper and basic parser
- Clinical trial data extraction (enrollment, endpoints, results)
- Competitive intelligence reports (approved PMAs in product code)
- PMA vs. 510(k) pathway decision support
- Standards intelligence (reuse from 510(k))
- MAUDE/recall integration (reuse from 510(k))

**Excludes:**
- Full PMA drafting templates (clinical sections too device-specific)
- Benefit-risk analysis automation (requires medical judgment)
- IDE integration
- Modular PMA workflow

**Pros:** Focuses on high-value intelligence; avoids areas requiring deep medical expertise
**Cons:** Won't be a "complete PMA writer" like 510(k) plugin
**Target Customer:** RA professionals who need data/intelligence but will write submissions themselves

---

### Option 3: PMA Lite (100-150 hours = 3-4 weeks)
**Includes:**
- OpenFDA PMA API integration (query, export CSV)
- SSED PDF downloader (no parsing)
- Basic PMA vs. 510(k) comparison tables
- Product code statistics (approved PMAs, timelines)

**Excludes:**
- SSED parsing
- Clinical trial extraction
- Drafting templates
- Advanced intelligence

**Pros:** Fast to market; low risk
**Cons:** Limited value-add (mostly data access)
**Target Customer:** Users who just need PMA data organized

---

## Recommended Phasing

### Phase 0: Market Validation (2-3 weeks, minimal dev)
1. Survey existing 510(k) plugin users: "Would you use PMA features?"
2. Identify 1-2 pilot customers developing Class III devices
3. Prototype SSED scraper to validate technical feasibility
4. Estimate willingness to pay (PMA users may pay premium)

**Go/No-Go Decision:** If ≥3 committed pilot users OR enterprise customer requests → Proceed to Phase 1

---

### Phase 1: Core Intelligence (8-10 weeks) - OPTION 2
1. **Week 1-2:** OpenFDA PMA API integration
   - Query interface similar to BatchFetch
   - Decision code breakdown
   - Supplement tracking

2. **Week 3-5:** SSED PDF scraper and parser
   - Construct URLs from PMA numbers
   - Download PDFs
   - Extract: indications, device description, clinical trial summary

3. **Week 6-7:** Clinical trial data extraction
   - Parse trial design (RCT, single-arm, etc.)
   - Extract enrollment, endpoints, results
   - Build benchmarking database (compare new device to approved PMAs)

4. **Week 8-9:** Competitive intelligence reports
   - "Approved PMAs in your product code" report
   - Clinical trial design comparison
   - Standards conformance patterns

5. **Week 10:** Integration and testing
   - Extend BatchFetch: `--pathway=pma`
   - Quality testing with 20 diverse PMAs
   - Documentation

**Deliverable:** PMA Intelligence Module (not full drafting support)

---

### Phase 2: Enhanced Features (4-6 weeks) - IF Phase 1 validated
1. PAS database scraper
2. Advisory panel prediction
3. Modular PMA support
4. Financial disclosure templates

---

### Phase 3: Advanced Automation (3-4 weeks) - IF strong demand
1. PMA section templates (device description, manufacturing, nonclinical)
2. Clinical protocol template
3. Benefit-risk framework

---

## Technical Architecture Considerations

### Data Sources

| Data Source | 510(k) | PMA | Difficulty |
|-------------|--------|-----|------------|
| OpenFDA API | ✓ Rich (40+ fields) | ✓ Basic (24 fields) | Easy (both) |
| Summary PDFs | ✓ Bulk ZIP | ✗ Individual scrape | Medium (PMA requires URL construction) |
| Full-text search | ✓ Via API | ✗ Not available | Hard (would need local indexing) |
| MAUDE | ✓ Shared | ✓ Shared | Easy (reuse) |
| Recalls | ✓ Shared | ✓ Shared | Easy (reuse) |
| Standards | ✓ Shared | ✓ Shared | Easy (reuse) |
| Post-market studies | N/A | ✓ PAS database (scrape) | Medium (no API) |

### SSED URL Construction Logic

```python
def construct_ssed_url(pma_number):
    """
    Construct SSED PDF URL from PMA number.

    Examples:
    - P170019 → https://www.accessdata.fda.gov/cdrh_docs/pdf17/P170019B.pdf
    - P030027 → https://www.accessdata.fda.gov/cdrh_docs/pdf03/P030027B.pdf
    - P160035S029 → https://www.accessdata.fda.gov/cdrh_docs/pdf16/P160035S029B.pdf
    """
    # Extract year from PMA number (e.g., P17xxxx → 17)
    year = pma_number[1:3]

    # Base URL
    base_url = f"https://www.accessdata.fda.gov/cdrh_docs/pdf{year}/"

    # Full URL
    url = f"{base_url}{pma_number}B.pdf"

    # Note: Some use lowercase 'b', try both if 404
    return url
```

**Challenge:** Not all SSEDs follow this pattern; some are missing; some use different suffixes

### Parsing Strategy

**Option A: PDF Text Extraction (pypdf2, pdfplumber)**
- Pros: Fast, simple
- Cons: Format varies 1976-2026; tables difficult; may miss key data

**Option B: OCR + NLP (tesseract + spaCy)**
- Pros: Handles scanned PDFs, more robust
- Cons: Slower, requires ML models

**Option C: Hybrid (text extraction + fallback OCR)**
- Pros: Best of both worlds
- Cons: More complex code

**RECOMMENDATION:** Start with Option A (text extraction), add OCR only if needed

---

## ROI Analysis

### 510(k) Plugin ROI (for comparison)
- **Market size:** 4,500 submissions/year
- **Potential users:** RA professionals, small med device companies, consultants
- **Value prop:** Faster predicate research (6.5 hrs saved), better compliance, competitive intelligence
- **Pricing:** $500-$2,000/year per user (estimated)
- **Estimated market:** 500-2,000 potential users

### PMA Plugin ROI (Option 2 - Hybrid)
- **Market size:** 60 original PMAs/year
- **Potential users:** Large med device companies (top 50), specialized RA consultants
- **Value prop:** Clinical trial benchmarking, competitive intelligence, faster SSED analysis (10-20 hrs saved)
- **Pricing:** $2,000-$10,000/year per user (premium for Class III)
- **Estimated market:** 50-200 potential users (smaller but higher value)

**Development cost:** 220-300 hours × $150/hr = $33,000-$45,000

**Break-even analysis:**
- **Pessimistic:** 10 users × $2,000/yr = $20,000/yr → 2.3 years to break even
- **Realistic:** 25 users × $5,000/yr = $125,000/yr → 4 months to break even
- **Optimistic:** 50 users × $10,000/yr = $500,000/yr → <1 month to break even

**Verdict:** If you can land 2-3 enterprise customers ($10K+/year), ROI is excellent

---

## Risk Assessment

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SSED PDFs not parseable | Medium | High | Prototype with 20 diverse PMAs first |
| Clinical data too complex to automate | High | Medium | Focus on extraction, not interpretation |
| OpenFDA API changes | Low | Medium | Version locking, fallback strategies |
| URL construction fails for some PMAs | Medium | Low | Manual fallback, FOIA request guidance |

### Market Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Market too small | Medium | High | Phase 0 validation with pilot customers |
| Users want full drafting (not just intelligence) | Medium | Medium | Educate on value of intelligence; Phase 3 if demand |
| Large companies build in-house | Medium | High | Focus on mid-size companies, consultants |
| PMA volume declines (shift to De Novo) | Low | Medium | Monitor FDA trends, add De Novo support |

### Regulatory Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| FDA changes PMA requirements | Low | Medium | Monitor guidance documents, update quarterly |
| SSED data becomes restricted | Very Low | High | Archive historical SSEDs, FOIA advocacy |

---

## Decision Matrix

### Should We Build PMA Support?

**YES, invest in Option 2 (Hybrid) IF:**
- ✓ ≥3 pilot customers commit to testing
- ✓ Enterprise customer requests feature
- ✓ 510(k) plugin has proven product-market fit
- ✓ Team has 2-3 months dev capacity
- ✓ Can charge premium ($5K+/year) to PMA users

**NO, skip or do Option 3 (Lite) IF:**
- ✗ <2 pilot customers interested
- ✗ 510(k) plugin still finding product-market fit
- ✗ Dev capacity constrained (<2 months)
- ✗ Can't justify premium pricing
- ✗ Technical prototype shows SSED parsing too hard

**DEFER IF:**
- Need more market research
- Want to validate 510(k) plugin first
- Waiting for FDA to improve PMA data access

---

## Next Steps (Assuming GO Decision)

### Immediate (Week 1-2)
1. Set up PMA API test queries
2. Download 20 diverse SSED PDFs (different years, device types)
3. Prototype text extraction (test 3 approaches)
4. Survey 10 existing users about PMA interest

### Short-term (Week 3-4)
1. Build SSED scraper and basic parser
2. Validate parsing accuracy (target: 80%+ fields extracted correctly)
3. Design PMA intelligence report format
4. Recruit 2-3 pilot users

### Medium-term (Week 5-10)
1. Implement Phase 1 (Option 2 features)
2. Beta test with pilot users
3. Iterate based on feedback
4. Document and release PMA Intelligence Module

### Long-term (Month 4+)
1. Gather usage analytics
2. Decide on Phase 2 investment
3. Explore enterprise licensing
4. Consider De Novo pathway support

---

## Conclusion

**PMA plugin is viable but strategic:**
- Smaller market than 510(k) (60 vs. 4,500 annual submissions)
- Higher value per customer (Class III = high stakes)
- Different technical approach (intelligence > automation)
- Requires pilot validation before full investment

**Recommended path:**
1. **Phase 0:** Validate with 2-3 pilot customers (3 weeks)
2. **Phase 1:** Build hybrid intelligence module (8-10 weeks)
3. **Phase 2:** Expand if validated (4-6 weeks)

**Success criteria:**
- ≥25 paid users within 12 months
- $125K+ ARR (average $5K/user)
- 80%+ SSED parsing accuracy
- 4.0+ user satisfaction score

---

**RECOMMENDATION: Proceed with Phase 0 market validation, then decide on Phase 1 investment based on pilot feedback.**

