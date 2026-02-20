# PMA Plugin Implementation Plan (Phase 1 - Hybrid Intelligence)

**Version:** 1.0
**Date:** 2026-02-15
**Estimated Duration:** 8-10 weeks
**Estimated Effort:** 220-300 hours

---

## Overview

This implementation plan covers **Phase 1: Hybrid Intelligence** approach for PMA support. The goal is to provide PMA data intelligence and competitive analysis rather than full submission drafting (which requires medical expertise).

**Scope:**
- OpenFDA PMA API integration
- SSED PDF scraper and parser
- Clinical trial data extraction
- Competitive intelligence reports
- PMA vs. 510(k) pathway decision support

**Out of Scope (Phase 2+):**
- Full PMA section drafting templates
- Benefit-risk analysis automation
- IDE integration
- Modular PMA workflow

---

## Architecture Overview

### Data Flow

```
┌─────────────────┐
│  User Request   │
│ (PMA Analysis)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  BatchFetch PMA Mode        │
│  --pathway=pma              │
│  --product-codes XXX        │
│  --years YYYY               │
└────────┬────────────────────┘
         │
         ├─────────────────────────┐
         ▼                         ▼
┌──────────────────┐     ┌──────────────────┐
│ OpenFDA PMA API  │     │  SSED Scraper    │
│ - Basic metadata │     │  - Download PDFs │
│ - Decision codes │     │  - Parse sections│
└────────┬─────────┘     └────────┬─────────┘
         │                        │
         ▼                        ▼
┌─────────────────────────────────────────┐
│     PMA Enrichment Engine               │
│  - Clinical trial extraction            │
│  - Standards intelligence (reused)      │
│  - MAUDE/recall lookup (reused)         │
│  - Competitive benchmarking             │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│          Output Files                   │
│  - pma_intelligence_report.md           │
│  - pma_data.csv (enriched)              │
│  - clinical_trials_summary.md           │
│  - competitive_landscape.md             │
│  - pma_vs_510k_decision.md              │
└─────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. OpenFDA PMA API Client (Week 1-2, 30-40 hours)

**File:** `scripts/pma_api_client.py`

**Features:**
- Query PMA API with filters (product code, date range, decision code)
- Pagination handling (max 1000 records per call)
- Rate limiting (40 requests/minute per FDA guidelines)
- Caching (avoid redundant API calls)
- Error handling and retry logic

**API Fields to Capture:**
```python
PMA_FIELDS = [
    'pma_number',
    'supplement_number',
    'applicant',
    'street_1', 'street_2', 'city', 'state', 'zip', 'zip_ext',
    'generic_name',
    'trade_name',
    'product_code',
    'advisory_committee',
    'advisory_committee_description',
    'supplement_type',
    'supplement_reason',
    'expedited_review_flag',
    'date_received',
    'decision_date',
    'docket_number',
    'decision_code',
    'ao_statement',
    'fed_reg_notice_date',
    'openfda.device_name',
    'openfda.regulation_number',
    'openfda.device_class'
]
```

**Key Functions:**
```python
def query_pma_api(product_codes=None, date_range=None, decision_code=None, limit=1000):
    """Query OpenFDA PMA API with filters."""
    pass

def get_pma_by_number(pma_number):
    """Get single PMA by number."""
    pass

def get_pma_supplements(pma_number):
    """Get all supplements for a PMA."""
    pass

def count_pmas_by_field(field_name):
    """Get count statistics for a field (e.g., decision_code)."""
    pass
```

**Testing:**
- Unit tests with mock API responses
- Integration tests with live API (10 sample queries)
- Validate all 24 fields correctly parsed

---

### 2. SSED PDF Scraper (Week 3-4, 40-50 hours)

**File:** `scripts/ssed_scraper.py`

**Features:**
- Construct SSED URL from PMA number
- Download PDF with retry logic
- Handle 404s (not all PMAs have public SSEDs)
- Cache downloaded PDFs locally
- Track download success rate

**URL Construction Logic:**
```python
def construct_ssed_url(pma_number):
    """
    Construct SSED PDF URL from PMA number.

    Examples:
    - P170019 → https://www.accessdata.fda.gov/cdrh_docs/pdf17/P170019B.pdf
    - P030027 → https://www.accessdata.fda.gov/cdrh_docs/pdf03/P030027B.pdf
    - P160035S029 → https://www.accessdata.fda.gov/cdrh_docs/pdf16/P160035S029B.pdf
    """
    # Extract year from PMA number
    if pma_number.startswith('P'):
        year = pma_number[1:3]
    else:
        raise ValueError(f"Invalid PMA number format: {pma_number}")

    base_url = f"https://www.accessdata.fda.gov/cdrh_docs/pdf{year}/"
    url = f"{base_url}{pma_number}B.pdf"

    return url

def download_ssed(pma_number, cache_dir='./ssed_cache/'):
    """
    Download SSED PDF for PMA number.

    Returns:
        str: Path to downloaded PDF, or None if 404
    """
    url = construct_ssed_url(pma_number)

    # Try uppercase 'B' first
    response = requests.get(url)
    if response.status_code == 404:
        # Try lowercase 'b'
        url = url.replace('B.pdf', 'b.pdf')
        response = requests.get(url)

    if response.status_code == 200:
        filepath = os.path.join(cache_dir, f"{pma_number}.pdf")
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return filepath
    else:
        return None
```

**Download Success Tracking:**
```python
def batch_download_sseds(pma_numbers, cache_dir='./ssed_cache/'):
    """
    Batch download SSEDs and track success rate.

    Returns:
        dict: {
            'downloaded': [...],
            'failed': [...],
            'success_rate': 0.75
        }
    """
    pass
```

**Testing:**
- Download 20 diverse SSEDs (different years: 1990s, 2000s, 2010s, 2020s)
- Validate PDFs are not corrupted
- Measure success rate (target: >80%)

---

### 3. SSED Parser (Week 4-5, 50-60 hours)

**File:** `scripts/ssed_parser.py`

**Features:**
- Extract text from PDF (pdfplumber library)
- Identify section boundaries (regex patterns for headings)
- Parse structured data from each section
- Handle format variations across years

**Target Sections to Parse:**

| Section | Data to Extract | Parsing Strategy |
|---------|----------------|------------------|
| **General Information** | Device name, applicant, PMA number, approval date | Regex patterns for "PMA Number:", "Applicant:", etc. |
| **Indications for Use** | Full indication text | Section heading → next heading |
| **Device Description** | Description text, materials, components | Section heading → next heading; extract material keywords |
| **Clinical Studies** | Trial design, enrollment, sites, endpoints, results | Table detection; regex for "N=XXX patients", "p=0.XXX" |
| **Primary Clinical Study** | Pivotal trial details | Focus on "Primary" or "Pivotal" keywords |
| **Adverse Events** | Event types, rates, severity | Table detection; regex for percentages |
| **Conclusions** | Safety/effectiveness determination | Section heading → end |

**Key Functions:**
```python
def extract_text_from_pdf(pdf_path):
    """Extract all text from PDF using pdfplumber."""
    import pdfplumber
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text

def identify_sections(text):
    """
    Identify section boundaries in SSED text.

    Returns:
        dict: {
            'general_information': (start_idx, end_idx),
            'indications': (start_idx, end_idx),
            ...
        }
    """
    section_patterns = {
        'general_information': r'I\.\s+GENERAL INFORMATION',
        'indications': r'II\.\s+INDICATIONS FOR USE',
        'device_description': r'III\.\s+DEVICE DESCRIPTION',
        'clinical_studies': r'VIII\.\s+CLINICAL STUDIES',
        'conclusions': r'XI\.\s+CONCLUSIONS',
    }
    # Regex matching to find section starts
    pass

def parse_clinical_trial_data(clinical_section_text):
    """
    Extract structured clinical trial data.

    Returns:
        dict: {
            'trial_design': 'RCT' | 'single-arm' | 'observational',
            'enrollment': 300,
            'sites': 25,
            'primary_endpoint': '...',
            'primary_result': 'p<0.001',
            'adverse_event_rate': 0.15,
            'follow_up_duration': '5 years'
        }
    """
    # Regex patterns for clinical data
    patterns = {
        'enrollment': r'[Nn]=\s*(\d+)\s+(?:patients|subjects)',
        'sites': r'(\d+)\s+(?:sites|centers)',
        'p_value': r'[Pp]\s*[=<]\s*(0\.\d+)',
        'adverse_rate': r'(\d+(?:\.\d+)?)\s*%\s+(?:adverse|AE)',
    }
    pass

def extract_materials(device_description_text):
    """
    Extract materials mentioned in device description.

    Returns:
        list: ['titanium', 'PEEK', 'silicone', ...]
    """
    material_keywords = [
        'titanium', 'stainless steel', 'cobalt chromium', 'PEEK',
        'polyethylene', 'ceramic', 'silicone', 'nitinol', 'platinum',
        'polyurethane', 'polypropylene', 'PTFE', 'ePTFE'
    ]
    # Case-insensitive search for materials
    pass
```

**Parsing Accuracy Target:**
- General Information: 95%+ (structured, consistent)
- Indications for Use: 90%+ (well-defined section)
- Clinical Trial Enrollment: 80%+ (regex can find N=XXX)
- Adverse Event Rate: 70%+ (table formats vary)
- Device Description: 85%+ (text extraction)

**Testing:**
- Parse 20 diverse SSEDs
- Manual validation of extracted data
- Calculate field-level accuracy scores
- Iterate on regex patterns to improve accuracy

---

### 4. Clinical Trial Intelligence (Week 6-7, 40-50 hours)

**File:** `lib/clinical_trial_intelligence.py`

**Features:**
- Classify trial design (RCT, single-arm, observational)
- Benchmark enrollment size against product code averages
- Identify statistical significance of endpoints
- Flag underpowered studies
- Compare to FDA expectations for device type

**Key Functions:**
```python
def classify_trial_design(clinical_data):
    """
    Classify clinical trial design.

    Returns:
        str: 'RCT' | 'single-arm' | 'observational' | 'case-control' | 'unknown'
    """
    keywords_rct = ['randomized', 'controlled', 'RCT', 'control arm']
    keywords_single_arm = ['single-arm', 'single arm', 'non-randomized']
    # Keyword matching
    pass

def benchmark_enrollment(enrollment, product_code, pma_database):
    """
    Compare enrollment to other PMAs in same product code.

    Returns:
        dict: {
            'enrollment': 300,
            'product_code_avg': 250,
            'percentile': 60,  # This PMA is 60th percentile
            'assessment': 'adequate' | 'underpowered' | 'robust'
        }
    """
    pass

def extract_primary_endpoint(clinical_text):
    """
    Extract primary endpoint description.

    Returns:
        str: 'Device success rate at 1 year'
    """
    # Look for "primary endpoint", "primary outcome", "primary objective"
    pass

def assess_statistical_significance(p_value):
    """
    Assess statistical significance of primary endpoint.

    Returns:
        dict: {
            'p_value': 0.001,
            'significant': True,
            'strength': 'strong' | 'moderate' | 'weak'
        }
    """
    if p_value < 0.001:
        return {'p_value': p_value, 'significant': True, 'strength': 'strong'}
    elif p_value < 0.05:
        return {'p_value': p_value, 'significant': True, 'strength': 'moderate'}
    elif p_value < 0.1:
        return {'p_value': p_value, 'significant': False, 'strength': 'weak'}
    else:
        return {'p_value': p_value, 'significant': False, 'strength': 'none'}
```

**Benchmarking Database:**
- Build database of all extracted clinical trial data (enrollment, design, endpoints)
- Group by product code
- Calculate statistics (mean, median, quartiles)
- Flag outliers (enrollment <25th percentile = underpowered)

**Intelligence Reports:**
```python
def generate_clinical_trial_report(pma_data, benchmarks):
    """
    Generate markdown report on clinical trial.

    Sections:
    - Trial Design Overview
    - Enrollment Benchmarking
    - Endpoint Analysis
    - Statistical Strength
    - Comparison to Similar PMAs
    """
    pass
```

---

### 5. Competitive Intelligence Reports (Week 8-9, 40-50 hours)

**File:** `lib/pma_competitive_intelligence.py`

**Features:**
- Approved PMAs in same product code
- Timeline analysis (receipt to approval)
- Clinical trial design patterns
- Standards conformance patterns
- Advisory panel frequency
- Supplement activity

**Report Types:**

**5.1 Product Code Landscape Report**
```markdown
# PMA Competitive Landscape: Product Code XXX

## Overview
- Total approved PMAs: 15
- Date range: 2010-2024
- Average approval time: 280 days
- Advisory panel rate: 40%

## Approved Devices
| PMA Number | Device Name | Applicant | Approval Date | Review Time |
|------------|-------------|-----------|---------------|-------------|
| P170019 | F1CDx | Foundation Medicine | 2017-11-30 | 320 days |
| ... | ... | ... | ... | ... |

## Clinical Trial Benchmarks
- Average enrollment: 250 patients (range: 50-800)
- Most common design: RCT (70%), single-arm (30%)
- Average follow-up: 2.5 years
- Common endpoints: Device success rate, adverse event rate, quality of life

## Standards Pattern Analysis
- ISO 10993 (biocompatibility): 100% (15/15 PMAs)
- IEC 60601 (electrical safety): 60% (9/15 PMAs)
- ISO 11135 (EO sterilization): 40% (6/15 PMAs)

## Advisory Panel History
- PMAs with panel review: 6/15 (40%)
- Panel recommendation agreement: 100% (FDA followed all panel recommendations)

## Supplement Activity
- Average supplements per PMA: 3.2
- Most common supplement type: 30-Day Notice (60%)
- Average time between original and first supplement: 18 months
```

**5.2 Clinical Trial Design Comparison**
```markdown
# Clinical Trial Design Comparison

## Your Device vs. Approved PMAs in Product Code XXX

| Dimension | Your Device | Product Code Avg | Assessment |
|-----------|-------------|------------------|------------|
| Trial Design | RCT | RCT (70%) | Standard |
| Enrollment | 150 | 250 | Below average (40th percentile) |
| Sites | 10 | 18 | Below average |
| Follow-up | 1 year | 2.5 years | Shorter than typical |
| Control | Active | Active (60%), Sham (40%) | Standard |
| Primary Endpoint | Device success at 1yr | Device success (80%) | Standard |

## Recommendations
1. **Enrollment:** Consider increasing to 200+ patients (median for product code)
2. **Follow-up:** Extend to 2+ years to align with FDA expectations
3. **Sites:** Add 5-10 sites to improve generalizability
```

**5.3 Timeline Projection**
```python
def project_review_timeline(product_code, pma_database):
    """
    Project likely review timeline based on historical data.

    Returns:
        dict: {
            'product_code': 'XXX',
            'historical_avg_days': 280,
            'historical_median_days': 260,
            'projection': '9-12 months',
            'factors': [
                'Advisory panel likely (+60 days)',
                'Clinical data typical (no delay expected)',
                'Supplement history shows manufacturer responsiveness (+0 days)'
            ]
        }
    """
    pass
```

---

### 6. PMA vs. 510(k) Decision Support (Week 9, 20-30 hours)

**File:** `lib/pathway_decision_support.py`

**Features:**
- Analyze device characteristics
- Recommend pathway (PMA, 510(k), De Novo)
- Identify potential predicates (if 510(k) viable)
- Estimate costs and timelines for each pathway

**Decision Logic:**
```python
def recommend_pathway(device_data):
    """
    Recommend regulatory pathway based on device characteristics.

    Input:
        device_data = {
            'device_class': 'III',  # or 'II', 'I'
            'has_predicate': True,  # or False
            'predicate_class': 'III',
            'novel_technology': False,
            'life_sustaining': True,
            'implantable': True,
            'clinical_data_available': False
        }

    Returns:
        dict: {
            'recommended_pathway': 'PMA',
            'alternative_pathways': ['De Novo'],
            'rationale': '...',
            'estimated_cost': '$50M-$100M',
            'estimated_timeline': '3-5 years',
            'clinical_trial_likely': True
        }
    """
    # Decision tree logic
    if device_data['device_class'] == 'III':
        if device_data['has_predicate'] and device_data['predicate_class'] == 'II':
            return 'De Novo (if predicate is not appropriate) or 510(k) (if reclassified)'
        elif device_data['has_predicate'] and device_data['predicate_class'] == 'III':
            return '510(k) (if substantially equivalent) or PMA (if not equivalent)'
        else:
            return 'PMA (no predicates available)'

    elif device_data['device_class'] == 'II':
        return '510(k) (unless novel, then De Novo)'

    elif device_data['device_class'] == 'I':
        return 'Exempt or 510(k)'
```

**Pathway Comparison Report:**
```markdown
# Pathway Decision Support: [Device Name]

## Device Classification
- Device Class: III
- Product Code: XXX
- Life-sustaining: Yes
- Implantable: Yes

## Pathway Options

### Option 1: PMA (Recommended)
**Pros:**
- No Class III predicates available
- Establishes new safety/effectiveness benchmark
- No substantial equivalence burden

**Cons:**
- Clinical trials required (estimated $20M, 3 years)
- Longer review timeline (12-18 months)
- Higher user fees ($450K)

**Estimated Cost:** $50M-$100M
**Estimated Timeline:** 4-5 years (including clinical trial)
**Probability of Approval:** 70% (if well-designed trial)

### Option 2: 510(k) (Not Viable)
**Assessment:** No Class III predicates found in product code XXX. All existing devices are PMA-approved.

### Option 3: De Novo (Possible Alternative)
**Assessment:** If device can be reclassified to Class II, De Novo may be viable. Requires demonstration that Class II controls provide reasonable assurance of safety/effectiveness.

**Pros:**
- Lower cost than PMA ($5M-$15M)
- Faster timeline (18-24 months)
- Becomes predicate for future 510(k)s

**Cons:**
- FDA may not agree device can be Class II
- Still requires clinical data (likely)
- Rare for life-sustaining devices

## Recommendation
**Proceed with PMA pathway.** No viable predicates exist, and device characteristics (life-sustaining, implantable) align with Class III risk profile. Budget $50M-$100M and 4-5 years.
```

---

### 7. Integration with Existing Plugin (Week 10, 20-30 hours)

**Changes to Existing Files:**

**7.1 Extend BatchFetch Command**
`commands/batchfetch.md` (add PMA mode)

```markdown
## New Parameter: --pathway

**Values:** `510k` (default) or `pma`

**Usage:**
/fda-tools:batchfetch --pathway=pma --product-codes DQY --years 2020-2024 --enrich --full-auto

**Behavior:**
- If `--pathway=510k`: Use existing 510(k) logic (default)
- If `--pathway=pma`: Use PMA API client, SSED scraper, PMA enrichment

**PMA Output Files:**
1. `pma_data.csv` - Enriched CSV with 40+ columns
2. `pma_intelligence_report.md` - Competitive landscape
3. `clinical_trials_summary.md` - Benchmarking analysis
4. `pathway_decision.md` - PMA vs. 510(k) recommendation
5. `pma_enrichment_metadata.json` - Data provenance
```

**7.2 Reuse Existing Components**
- `lib/fda_enrichment.py` → Extend for PMA (reuse MAUDE, recalls, standards logic)
- `lib/disclaimers.py` → Add PMA-specific disclaimers
- `scripts/fda_api_client.py` → Keep for 510(k), create `scripts/pma_api_client.py`

**7.3 New Command File (Optional)**
`commands/pma-intelligence.md` (standalone PMA analysis command)

```markdown
---
description: Analyze PMA competitive landscape and clinical trial benchmarks
allowed-tools: [Bash, Read, Write]
argument-hint: --pma-number P170019 or --product-code DQY
---

# PMA Intelligence Command

Generate comprehensive competitive intelligence for PMA pathway.

## Usage

/fda-tools:pma-intelligence --pma-number P170019
/fda-tools:pma-intelligence --product-code DQY --years 2020-2024

## Steps

1. **Query PMA API** for specified PMA number or product code
2. **Download SSEDs** for all matching PMAs
3. **Parse clinical trial data** from SSEDs
4. **Generate competitive landscape report**
5. **Create clinical trial benchmarking analysis**
6. **Provide pathway decision support** (if new device characteristics provided)

## Output Files

1. `pma_intelligence_report.md`
2. `clinical_trials_summary.md`
3. `pathway_decision.md` (if applicable)
4. `pma_data.csv` (raw + enriched data)
```

---

## Testing Strategy

### Unit Tests (Throughout Development)
- `test_pma_api_client.py` - API query functions
- `test_ssed_scraper.py` - URL construction, download logic
- `test_ssed_parser.py` - Text extraction, section identification, data parsing
- `test_clinical_trial_intelligence.py` - Trial classification, benchmarking
- `test_pathway_decision.py` - Decision logic

**Coverage Target:** 80%+ code coverage

### Integration Tests (Week 10)
- End-to-end test with 5 diverse PMAs
- Validate CSV output format
- Validate report generation
- Test with `--pathway=pma` flag

### Accuracy Validation (Week 10)
- Manually validate 20 SSEDs against parser output
- Measure field-level accuracy:
  - Indications: ≥90%
  - Clinical enrollment: ≥80%
  - Trial design: ≥75%
  - Adverse events: ≥70%

### User Acceptance Testing (Post-Week 10)
- Beta test with 2-3 pilot users
- Gather feedback on report usefulness
- Iterate on report format

---

## Milestones and Deliverables

| Week | Milestone | Deliverable | Hours |
|------|-----------|-------------|-------|
| **1-2** | PMA API Integration | `pma_api_client.py`, unit tests | 30-40 |
| **3-4** | SSED Scraper | `ssed_scraper.py`, download 50+ SSEDs | 40-50 |
| **4-5** | SSED Parser | `ssed_parser.py`, 80%+ accuracy on 20 SSEDs | 50-60 |
| **6-7** | Clinical Intelligence | `clinical_trial_intelligence.py`, benchmarking DB | 40-50 |
| **8-9** | Competitive Reports | `pma_competitive_intelligence.py`, report templates | 40-50 |
| **9** | Pathway Decision | `pathway_decision_support.py`, decision logic | 20-30 |
| **10** | Integration & Testing | `batchfetch.md` updates, E2E tests, documentation | 20-30 |
| **TOTAL** | **Phase 1 Complete** | **PMA Intelligence Module** | **220-300** |

---

## Success Criteria

### Technical Success
- ✓ SSED download success rate ≥80%
- ✓ SSED parsing accuracy ≥80% (enrollment, trial design, indications)
- ✓ API integration handles 1000+ PMA records
- ✓ Reports generate in <5 minutes for 20 PMAs
- ✓ Unit test coverage ≥80%

### User Success
- ✓ 2-3 pilot users complete testing
- ✓ User satisfaction ≥4.0/5.0
- ✓ Users report time savings ≥10 hours per PMA analysis
- ✓ Reports deemed "useful" or "very useful" by ≥80% of users

### Business Success
- ✓ ≥2 pilot users convert to paid customers
- ✓ Pricing validated at $5K+/year
- ✓ Roadmap for Phase 2 validated by user demand

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **SSED parsing accuracy <80%** | Focus on most critical fields (enrollment, indications); allow manual override; iterate on regex patterns |
| **SSED download failures** | Cache successfully downloaded PDFs; provide manual upload option; document FOIA request process |
| **Clinical data too complex** | Start with simple extraction (enrollment, trial design); avoid complex interpretation; let users interpret results |
| **Low user adoption** | Gather feedback early (Week 5); adjust report format; focus on highest-value insights |

---

## Post-Phase 1 Roadmap

### Phase 2: Enhanced Features (4-6 weeks, if validated)
- Post-Approval Studies scraper
- Advisory panel prediction model
- Modular PMA workflow
- Financial disclosure templates

### Phase 3: Advanced Automation (3-4 weeks, if strong demand)
- PMA section templates (device description, manufacturing, nonclinical)
- Clinical protocol template
- Benefit-risk framework outline

---

## Resource Requirements

**Development:**
- 1 senior developer (full-time, 10 weeks)
- OR 2 developers (part-time, 10 weeks)

**Testing:**
- 2-3 pilot users (beta testers)
- 1 RA professional for accuracy validation

**Infrastructure:**
- PDF storage: ~5GB for 1000 SSEDs
- API rate limits: 40 requests/min (FDA openFDA)

---

## Conclusion

Phase 1 delivers a **PMA Intelligence Module** that provides competitive analysis and clinical trial benchmarking without attempting to replace medical judgment. This hybrid approach balances automation (data acquisition, parsing, benchmarking) with human expertise (clinical interpretation, benefit-risk analysis).

**Next Steps:**
1. Get approval to proceed with Phase 1
2. Set up development environment
3. Recruit 2-3 pilot users
4. Begin Week 1 implementation (PMA API integration)

---

**END OF IMPLEMENTATION PLAN**
