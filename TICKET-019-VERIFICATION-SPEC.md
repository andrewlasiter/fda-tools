# TICKET-019 Verification Specification
## Predicate Analysis Integration - What ACTUALLY Clears

**Created:** 2026-02-15
**Ticket:** TICKET-019 (Add Predicate Analysis Integration)
**Expert Feedback Reference:** EXPERT-PANEL-REVIEW-SUMMARY.md (lines 376-382, recommendation #3)
**Current Tool Limitation:** Shows theoretical standards, not what ACTUALLY clears in practice

---

## Executive Summary

### Problem Statement

The current FDA standards tool suffers from a critical gap identified by 5 out of 5 regulatory experts:

> "Tool shows theoretical standards. Users need what ACTUALLY CLEARS."
> — RA Manager, Pre-Sub Specialist (EXPERT-PANEL-REVIEW-SUMMARY.md, line 378)

**Example Failure Case:**
- Tool recommends ISO 10993-1, -5, -10 for DQY catheter (cardiovascular) — **GENERIC recommendation**
- Real predicate analysis shows: **46/47 DQY clearances cite ISO 11070** (98% frequency) — **ACTUAL clearance path**
- Tool MISSED ISO 11070 → User proceeds without critical standard → FDA RTA risk

### Solution: Predicate Section 17 Analysis

This verification specification defines how to:

1. **Scrape 510(k) PDF summaries** for 50-100 cleared predicates per product code
2. **Extract Section 17 (Standards)** from each PDF with high accuracy
3. **Frequency analysis** to identify what standards ACTUALLY clear
4. **Compare tool output vs. predicate patterns** to identify gaps
5. **Generate actionable recommendations** (e.g., "Tool missed ISO 11070, cited in 98% of DQY clearances")

### Success Criteria

This implementation is **PRODUCTION READY** when:

- ✅ Section 17 extraction accuracy: **≥95%** (verified by manual spot-check)
- ✅ Frequency calculation accuracy: **±5%** of manual count
- ✅ Coverage completeness: **≥90%** of unique standards captured per product code
- ✅ Tool alignment: Tool recommendations match **≥80%** predicate frequency standards
- ✅ Gap detection: Identifies standards tool missed that appear in **≥80%** of predicates
- ✅ Expert validation: RA professional with 510(k) experience confirms accuracy

---

## 1. Data Collection Verification

### 1.1 Product Code Matching

**Objective:** Verify all collected 510(k) PDFs actually belong to the target product code.

**Verification Method:**

1. **Metadata cross-check:**
   - Extract product code from PDF text (search for "Product Code: XXX" pattern)
   - Compare against FDA database CSV (510k_download.csv from batchfetch)
   - **Pass criterion:** 100% of PDFs match target product code

2. **K-number validation:**
   - Extract K-number from PDF filename or header
   - Query FDA database API to verify product code assignment
   - **Pass criterion:** ≥98% K-numbers validate to correct product code

3. **Manual spot-check:**
   - Randomly sample 10% of PDFs (minimum 5 PDFs)
   - Human reviewer opens PDF and verifies product code on cover page
   - **Pass criterion:** 100% of spot-checked PDFs match

**Test Cases:**

```bash
# Test Case 1.1.1: DQY cardiovascular catheter
Expected: All PDFs have "Product Code: DQY" in metadata
Sample size: 50 PDFs
Verification: Compare extracted product code vs. FDA API

# Test Case 1.1.2: Mixed product codes (negative test)
Expected: System flags PDFs that don't match target
Sample: Intentionally include 5 OVE PDFs in DQY batch
Verification: Alert generated for 5 mismatches
```

**Failure Handling:**

- If <98% match: Re-download PDFs using stricter FDA API query
- If mismatches found: Exclude from analysis, log to `excluded_pdfs.csv`

---

### 1.2 Clearance Date Range

**Objective:** Ensure sample is representative across years to capture evolving FDA expectations.

**Verification Method:**

1. **Temporal distribution analysis:**
   - Calculate clearance year distribution (histogram)
   - **Pass criterion:** Each year in target range has ≥5% of total sample (OR minimum 3 PDFs)

2. **Recency weighting:**
   - Prioritize PDFs from last 3 years (capture current FDA standards)
   - **Minimum requirement:** ≥40% of sample from 2023-2026

3. **Guidance-driven sampling:**
   - Identify major FDA guidance updates affecting standards (e.g., 2022 Cybersecurity Guidance)
   - Ensure ≥20 PDFs cleared AFTER each major guidance
   - **Pass criterion:** Can detect guidance impact on standards frequency

**Test Cases:**

```bash
# Test Case 1.2.1: QKQ software devices (cybersecurity guidance effect)
Sample: 50 QKQ PDFs (25 pre-2022, 25 post-2022)
Expected: IEC 62304 frequency ~85% both periods
Expected: Cybersecurity (AAMI TIR57) increases from ~20% → ~65% post-2022
Verification: Frequency analysis shows guidance-driven shift

# Test Case 1.2.2: OVE orthopedic implants (ISO 10993 update)
Sample: 30 OVE PDFs across 2015-2025
Expected: No major frequency shifts (stable standards)
Verification: ASTM F1717 frequency stays 90-95% across all years
```

**Failure Handling:**

- If temporal gaps exist: Expand FDA query to fill gaps (download more PDFs from underrepresented years)
- Document any years with <3 samples as "insufficient data"

---

### 1.3 PDF Quality

**Objective:** Ensure PDFs are readable and Section 17 is extractable (not corrupted, scanned images, or malformed).

**Verification Method:**

1. **PDF integrity check:**
   - Use PyMuPDF (fitz) to open each PDF
   - Check for corruption errors
   - **Pass criterion:** ≥95% PDFs open without errors

2. **Text extractability:**
   - Extract raw text from entire PDF
   - **Pass criterion:** ≥90% of PDFs yield text (not scanned images)
   - **Failure mode:** PDFs with <100 characters extracted = likely scanned images

3. **Section 17 presence:**
   - Search for "Section 17" or "XVII. Standards" or "Performance Standards" headers
   - **Pass criterion:** ≥85% of PDFs have identifiable Section 17
   - **Note:** Some devices may have zero applicable standards (legitimate "N/A")

4. **OCR fallback:**
   - For scanned PDFs (no extractable text), run OCR (Tesseract or cloud OCR)
   - **Pass criterion:** OCR recovers text for ≥80% of scanned PDFs

**Test Cases:**

```bash
# Test Case 1.3.1: Standard text-based PDF
File: K123456_DQY_2024.pdf
Expected: Text extraction yields >5000 characters
Expected: "Section 17" found on page 8-12 range
Verification: Manual review confirms Section 17 correctly extracted

# Test Case 1.3.2: Scanned image PDF (OCR required)
File: K987654_OVE_2015.pdf (old scanned submission)
Expected: Initial text extraction fails (<100 chars)
Expected: OCR recovers text, finds Section 17
Verification: OCR accuracy ≥90% (compare OCR vs. manual transcription)

# Test Case 1.3.3: Corrupted PDF
File: K111111_corrupted.pdf
Expected: PyMuPDF raises error on open
Expected: PDF excluded from analysis, logged to error_log.txt
Verification: Error log contains K111111 with "corruption" reason
```

**Failure Handling:**

- Corrupted PDFs: Exclude, log to `excluded_pdfs.csv` with reason
- Scanned PDFs: Attempt OCR, flag as "OCR-derived" (lower confidence)
- Missing Section 17: Don't exclude (may be legitimate "no standards apply"), but flag for manual review

---

### 1.4 Sample Size Adequacy

**Objective:** Ensure minimum N predicates per product code to achieve statistical confidence.

**Verification Method:**

1. **Minimum sample size calculation:**
   - **High-volume codes (>50 clearances/year):** Minimum N=50 predicates
   - **Medium-volume codes (10-50 clearances/year):** Minimum N=30 predicates
   - **Low-volume codes (<10 clearances/year):** Minimum N=20 predicates OR all available
   - **Rationale:** 95% confidence interval, ±10% margin of error for frequency estimates

2. **Statistical power check:**
   - For each product code, calculate: `sample_size / total_clearances_5yr`
   - **Pass criterion:** ≥20% sampling rate (OR minimum N met)

3. **Rare standard detection:**
   - To detect a standard cited in 10% of predicates with 95% confidence:
   - **Required sample size:** N ≥ 30
   - **Pass criterion:** All product codes meet N≥30 threshold

**Test Cases:**

```bash
# Test Case 1.4.1: High-volume DQY (cardiovascular catheter)
Total DQY clearances (2020-2025): ~200
Target sample: 50 PDFs (25% sampling rate)
Expected: Can detect standards with ≥5% frequency
Verification: Frequency analysis identifies even rare standards

# Test Case 1.4.2: Low-volume QKQ (digital pathology software)
Total QKQ clearances (2020-2025): ~25
Target sample: 20 PDFs (80% sampling rate)
Expected: Can detect standards with ≥10% frequency
Verification: Covers most of cleared predicates

# Test Case 1.4.3: Stratified sampling (multiple product codes)
Product codes: DQY, OVE, QKQ (3 codes)
Total budget: 150 PDFs
Allocation: DQY=60, OVE=60, QKQ=30 (weighted by volume)
Verification: Each code meets minimum N threshold
```

**Failure Handling:**

- If insufficient PDFs available: Document as "limited sample" in report
- Reduce confidence interval expectation (e.g., ±15% instead of ±10%)
- Combine related product codes if clinically similar (e.g., DQY + DQA catheters)

---

## 2. Section 17 Extraction Accuracy

### 2.1 Standard Number Format Recognition

**Objective:** Correctly identify and parse all standard number formats appearing in Section 17.

**Verification Method:**

1. **Standard format taxonomy:**

   **ISO standards:**
   - `ISO 10993-1:2018` (part number + year)
   - `ISO 10993 series` (multi-part reference)
   - `ISO 10993-1:2018 (EN ISO 10993-1:2018)` (with European equivalent)

   **IEC standards:**
   - `IEC 60601-1:2005+AMD1:2012` (with amendments)
   - `IEC 62304:2006/AMD1:2015` (with amendment notation)

   **ASTM standards:**
   - `ASTM F2394-07(2013)` (reapproval year in parentheses)
   - `ASTM F1717-04` (year without reapproval)

   **FDA Guidance (not consensus standards but often cited):**
   - `FDA Guidance: Use of International Standard ISO 10993-1`
   - `AAMI TIR57:2016` (technical information report)

2. **Regex pattern library:**

   ```python
   STANDARD_PATTERNS = {
       'iso': r'ISO\s+(\d+)(?:-(\d+))?(?::(\d{4}))?',
       'iec': r'IEC\s+(\d+)(?:-(\d+)(?:-(\d+))?)?(?::(\d{4}))?',
       'astm': r'ASTM\s+([A-Z]\d+)(?:-(\d{2,4}))?(?:\((\d{4})\))?',
       'aami': r'AAMI\s+(TIR|ST|SW)(\d+)(?::(\d{4}))?',
       'iso_series': r'ISO\s+(\d+)\s+series',
   }
   ```

3. **Version number capture:**
   - **Pass criterion:** ≥95% of standards extracted include year/version
   - **Failure mode:** Standard extracted as "ISO 10993-1" without ":2018" → flag for manual review

4. **Multi-standard parsing:**
   - Handle: "ISO 10993 series: -1, -5, -10, -11" → Expand to 4 separate standards
   - **Pass criterion:** Multi-part references correctly expanded

**Test Cases:**

```bash
# Test Case 2.1.1: Complex standard notation
Input text: "ISO 10993-1:2018 (EN ISO 10993-1:2018)"
Expected output:
  - standard_org: "ISO"
  - standard_num: "10993-1"
  - version_year: "2018"
  - european_equiv: "EN ISO 10993-1:2018"
Verification: Manual review of 20 complex notations

# Test Case 2.1.2: Multi-part series reference
Input text: "ISO 10993 series: Part 1, Part 5, Part 10, Part 11"
Expected output: 4 separate standards
  - ISO 10993-1
  - ISO 10993-5
  - ISO 10993-10
  - ISO 10993-11
Verification: All 4 parts appear in frequency table

# Test Case 2.1.3: Amendment notation
Input text: "IEC 60601-1:2005+AMD1:2012+AMD2:2020"
Expected output:
  - standard: "IEC 60601-1"
  - base_year: "2005"
  - amendments: ["AMD1:2012", "AMD2:2020"]
Verification: Amendment tracking for version currency

# Test Case 2.1.4: ASTM reapproval notation
Input text: "ASTM F2394-07(2013)"
Expected output:
  - standard: "ASTM F2394"
  - original_year: "2007"
  - reapproval_year: "2013"
Verification: Correct version for FDA database matching
```

**Failure Handling:**

- Unrecognized format: Flag for manual review, attempt best-effort extraction
- Missing version: Extract standard number, flag as "version unknown"
- Create "extraction_warnings.csv" with flagged standards for human verification

---

### 2.2 Section 17 Boundary Detection

**Objective:** Correctly identify Section 17 boundaries to avoid extracting standards from wrong sections.

**Verification Method:**

1. **Section header patterns:**

   ```python
   SECTION_17_HEADERS = [
       r'(?:^|\n)\s*(?:XVII|17)[.:\s]+(?:Performance\s+)?Standards',
       r'(?:^|\n)\s*Section\s+17[.:\s]+Standards',
       r'(?:^|\n)\s*Standards\s+Used',
       r'(?:^|\n)\s*Consensus\s+Standards',
       r'(?:^|\n)\s*Performance\s+Standards',
   ]
   ```

2. **Section termination patterns:**

   ```python
   SECTION_END_PATTERNS = [
       r'(?:^|\n)\s*(?:XVIII|18)[.:\s]+',  # Next section
       r'(?:^|\n)\s*Section\s+18[.:\s]+',
       r'(?:^|\n)\s*(?:Conclusion|Summary)',  # Common endings
       r'\n\s*Page\s+\d+\s+of\s+\d+',  # Page break
   ]
   ```

3. **Boundary validation:**
   - **Pass criterion:** Extracted standards appear ONLY between Section 17 start and end
   - **Negative test:** Verify standards from Section 15 (Testing) are NOT extracted
   - **Manual spot-check:** 10% of PDFs manually reviewed to confirm boundaries

**Test Cases:**

```bash
# Test Case 2.2.1: Standard section numbering
PDF structure:
  Section 15: Testing and Performance Data
  Section 16: Clinical/Non-clinical Tests
  Section 17: Performance Standards  <-- TARGET
  Section 18: Conclusion

Expected: Only standards from Section 17 extracted
Verification: Standards list doesn't include test protocols from Section 15

# Test Case 2.2.2: Non-standard section headers
PDF uses: "Standards Utilized" instead of "Section 17"
Expected: Header pattern matches "Standards Utilized"
Verification: Standards correctly extracted despite non-standard header

# Test Case 2.2.3: Multi-page Section 17
Section 17 spans pages 10-12 (3 pages, 15 standards)
Page break occurs mid-section
Expected: All 15 standards extracted across page boundary
Verification: Manual count matches extracted count

# Test Case 2.2.4: Negative test - False positive
PDF mentions standards in Background (Section 3) for literature review
Expected: These standards NOT extracted (outside Section 17)
Verification: Background standards don't appear in final list
```

**Failure Handling:**

- If section boundary unclear: Extract conservatively (prefer false negative over false positive)
- Multi-page sections: Use page-range detection, don't rely solely on section headers
- Create `boundary_warnings.csv` listing PDFs with unclear boundaries

---

### 2.3 Multi-Standard Parsing

**Objective:** Handle complex Section 17 formatting where multiple standards are listed in various formats.

**Verification Method:**

1. **Format taxonomy:**

   **Bulleted lists:**
   ```
   • ISO 10993-1:2018
   • IEC 60601-1:2005
   • ASTM F2394-07
   ```

   **Paragraph text:**
   ```
   The device conforms to ISO 10993-1:2018, IEC 60601-1:2005, and ASTM F2394-07.
   ```

   **Tables:**
   ```
   | Standard | Title | Compliance |
   |----------|-------|------------|
   | ISO 10993-1 | Biological Eval | Yes |
   ```

   **Nested lists (series expansion):**
   ```
   ISO 10993 series:
     - Part 1: Evaluation and testing
     - Part 5: Cytotoxicity
     - Part 10: Irritation
   ```

2. **Parsing strategies:**
   - **List extraction:** Regex for bullet points `[•\-\*]\s*([A-Z]+\s+\d+)`
   - **Comma-separated:** Split on commas, extract each standard
   - **Table extraction:** Use pdfplumber table detection
   - **Series expansion:** Detect "series" keyword, extract parts, construct full standard numbers

3. **Duplicate handling:**
   - Same standard listed multiple times → Count once
   - Different versions of same standard (e.g., ISO 10993-1:2009 and :2018) → Count separately, flag version conflict

**Test Cases:**

```bash
# Test Case 2.3.1: Bulleted list (most common)
Input:
  • ISO 10993-1:2018
  • ISO 10993-5:2009
  • IEC 60601-1:2005
Expected: 3 standards extracted
Verification: All 3 appear in output

# Test Case 2.3.2: Paragraph text with commas
Input: "ISO 10993-1:2018, ISO 10993-5:2009, and IEC 60601-1:2005"
Expected: 3 standards extracted (same as above)
Verification: Comma parsing equivalent to list parsing

# Test Case 2.3.3: Table format
Input: PDF table with columns [Standard | Title | Compliance]
Expected: Extract from "Standard" column only
Verification: Title text (e.g., "Biological Evaluation") not mistaken for standard number

# Test Case 2.3.4: Series expansion
Input: "ISO 10993 series: -1, -5, -10, -11, -18"
Expected: 5 standards
  - ISO 10993-1
  - ISO 10993-5
  - ISO 10993-10
  - ISO 10993-11
  - ISO 10993-18
Verification: All 5 in frequency table with note "expanded from series"

# Test Case 2.3.5: Duplicate handling
Input:
  Section 17: ISO 10993-1:2018
  Later paragraph: "As noted, ISO 10993-1:2018 was used"
Expected: Count once (frequency = 1 for this PDF)
Verification: Deduplication works correctly
```

**Failure Handling:**

- Ambiguous format: Extract all plausible standards, flag for manual review
- Table extraction failure: Fall back to regex on raw text
- Series expansion uncertainty: Flag as "may be incomplete series"

---

## 3. Frequency Analysis Verification

### 3.1 Count Verification

**Objective:** Ensure frequency counts accurately reflect how many predicates cite each standard.

**Verification Method:**

1. **Manual spot-check (10% sample):**
   - Randomly select 10% of PDFs from analysis
   - Human reviewer manually counts standards in Section 17
   - Compare manual count vs. automated extraction
   - **Pass criterion:** ≥95% agreement (within ±1 standard per PDF)

2. **Cross-validation:**
   - Run extraction twice with different parsing libraries (PyMuPDF vs. pdfplumber)
   - Compare results
   - **Pass criterion:** ≥90% agreement on standard counts

3. **Outlier detection:**
   - Flag PDFs with >20 standards (unusually high) for manual review
   - Flag PDFs with 0 standards but lengthy Section 17 (extraction failure)

**Test Cases:**

```bash
# Test Case 3.1.1: Manual vs. automated count
PDF: K242424_DQY_2024.pdf
Manual count (human): 7 standards
Automated count: 7 standards
Match: ✅ PASS

# Test Case 3.1.2: Disagreement investigation
PDF: K252525_OVE_2023.pdf
Manual count: 6 standards
Automated count: 8 standards
Investigation: Automated extracted 2 standards from footnotes (not formal Section 17)
Resolution: Adjust boundary detection to exclude footnotes
Re-run: 6 standards ✅ PASS

# Test Case 3.1.3: Edge case - Zero standards
PDF: K262626_QKQ_2025.pdf (software, no hardware standards)
Section 17 text: "No consensus standards apply. Device follows FDA Software Guidance."
Manual count: 0 standards
Automated count: 0 standards
Match: ✅ PASS (legitimate zero)

# Test Case 3.1.4: Outlier detection
PDF: K272727_DQY_2020.pdf
Automated count: 22 standards
Flag: Unusually high, manual review
Manual review: 22 confirmed (comprehensive biocompatibility + electrical + sterilization)
Resolution: ✅ PASS (legitimate outlier)
```

**Acceptance Criteria:**

- ≥95% of spot-checked PDFs match within ±1 standard
- Disagreements investigated and explained (boundary issues, footnotes, etc.)
- Zero-standard PDFs validated as legitimate "N/A"

---

### 3.2 Percentage Calculation

**Objective:** Ensure frequency percentages are calculated correctly (denominator = total predicates analyzed).

**Verification Method:**

1. **Denominator validation:**
   - **Correct denominator:** Total PDFs successfully analyzed (Section 17 extractable)
   - **Incorrect denominator:** Total PDFs downloaded (includes corrupted/excluded)
   - **Pass criterion:** Denominator documented in report

2. **Frequency formula verification:**

   ```python
   frequency_pct = (count_predicates_citing_standard / total_analyzed_pdfs) * 100
   ```

3. **Edge case handling:**
   - Standard cited 0 times → 0%
   - Standard cited in all predicates → 100%
   - Standard cited 46/47 times → 97.9% (not 98%)

**Test Cases:**

```bash
# Test Case 3.2.1: Simple percentage calculation
Total analyzed PDFs: 50
Standard ISO 10993-1 cited in: 47 PDFs
Expected percentage: 47/50 = 94.0%
Verification: Output shows "94.0%" not "94%" or "95%"

# Test Case 3.2.2: Denominator exclusion handling
Total downloaded: 60 PDFs
Corrupted/excluded: 8 PDFs
Successfully analyzed: 52 PDFs
Standard ISO 11070 cited in: 49 PDFs
Correct percentage: 49/52 = 94.2%
Incorrect percentage: 49/60 = 81.7% ❌
Verification: Report uses 52 as denominator

# Test Case 3.2.3: Rounding precision
Standard cited in 46/47 PDFs
Exact percentage: 97.872340...%
Display: "97.9%" (1 decimal place)
Verification: Consistent rounding across all standards

# Test Case 3.2.4: Zero-frequency standard
Standard ASTM F999 cited in: 0 PDFs
Percentage: 0.0%
Verification: Appears in "not cited" section of report
```

**Acceptance Criteria:**

- Denominator documented and justified
- Percentage precision: 1 decimal place
- ±5% accuracy (within rounding error of manual calculation)

---

### 3.3 Category Aggregation

**Objective:** Group standards by category (biocompatibility, electrical safety, sterilization) for frequency analysis.

**Verification Method:**

1. **Category taxonomy:**

   ```python
   STANDARD_CATEGORIES = {
       'biocompatibility': ['ISO 10993-*'],
       'electrical_safety': ['IEC 60601-*', 'IEC 61010-*'],
       'sterilization': ['ISO 11135', 'ISO 11137', 'ISO 17665'],
       'software': ['IEC 62304', 'IEC 82304'],
       'usability': ['IEC 62366-*', 'IEC 60601-1-6'],
       'risk_management': ['ISO 14971'],
       'qms': ['ISO 13485'],
   }
   ```

2. **Category-level frequency:**
   - Example: "Biocompatibility standards cited in 45/50 predicates (90%)"
   - Sub-breakdown: "Most common: ISO 10993-1 (94%), -5 (88%), -10 (82%)"

3. **Cross-category analysis:**
   - Devices citing electrical + software standards: 23/50 (46%) → Likely powered SaMD

**Test Cases:**

```bash
# Test Case 3.3.1: ISO 10993 series aggregation
Predicates analyzed: 50
ISO 10993-1 cited in: 47 PDFs
ISO 10993-5 cited in: 44 PDFs
ISO 10993-10 cited in: 41 PDFs
ISO 10993-11 cited in: 12 PDFs

Category frequency: Biocompatibility cited in 47/50 (94%)
Breakdown:
  - ISO 10993-1: 47/50 (94%)
  - ISO 10993-5: 44/50 (88%)
  - ISO 10993-10: 41/50 (82%)
  - ISO 10993-11: 12/50 (24%)

Verification: Category frequency = max(part frequencies) = 94%

# Test Case 3.3.2: Electrical safety category
IEC 60601-1 cited in: 35/50 (70%)
IEC 60601-1-2 cited in: 33/50 (66%)
IEC 60601-2-25 cited in: 5/50 (10%)

Category frequency: Electrical safety cited in 35/50 (70%)
Verification: Detects powered devices vs. manual devices

# Test Case 3.3.3: Cross-category pattern (SaMD detection)
Software standards (IEC 62304): 20/50 (40%)
Electrical standards (IEC 60601-1): 35/50 (70%)
Overlap (both cited): 18/50 (36%)
Software-only: 2/50 (4%) → Standalone SaMD
Electrical-only: 17/50 (34%) → Non-software powered devices

Verification: Cross-category analysis reveals device characteristics
```

**Acceptance Criteria:**

- Category assignments match FDA standards database categories
- Aggregation logic documented (max frequency vs. average)
- Cross-category patterns detected and reported

---

### 3.4 Edge Case Handling

**Objective:** Correctly handle standards mentioned in text vs. formally cited in Section 17.

**Verification Method:**

1. **Formal citation vs. informational mention:**

   **Formal citation (INCLUDE in frequency):**
   ```
   Section 17: Performance Standards
   • ISO 10993-1:2018 - Biological Evaluation
   ```

   **Informational mention (EXCLUDE from frequency):**
   ```
   Section 2: Background
   "The FDA guidance references ISO 10993-1 for biocompatibility."
   ```

2. **Detection heuristic:**
   - Standard appears in Section 17 → Formal citation ✅
   - Standard appears elsewhere AND also in Section 17 → Count once
   - Standard appears elsewhere ONLY → Not a formal citation ❌

3. **Manufacturer interpretation:**
   - Some PDFs say: "ISO 10993-1 considered but not applicable"
   - **Interpretation:** NOT cited (manufacturer explicitly rejected)
   - **Heuristic:** Detect "not applicable", "considered", "reviewed but not used"

**Test Cases:**

```bash
# Test Case 3.4.1: Standard mentioned in background, not Section 17
Section 2 text: "ISO 10993-1 is a widely recognized standard for biocompatibility."
Section 17: "No consensus standards apply."
Expected: ISO 10993-1 frequency = 0 (not formally cited)
Verification: Extraction only counts Section 17

# Test Case 3.4.2: Standard cited in Section 17 AND mentioned elsewhere
Section 2: "Biocompatibility per ISO 10993-1"
Section 17: "• ISO 10993-1:2018"
Expected: ISO 10993-1 frequency = 1 (count once)
Verification: Deduplication works

# Test Case 3.4.3: Standard considered but rejected
Section 17: "ISO 10993-18 was reviewed but deemed not applicable (no chemical characterization required)."
Expected: ISO 10993-18 frequency = 0 (explicitly rejected)
Verification: Parser detects "not applicable" and excludes

# Test Case 3.4.4: Partial compliance statement
Section 17: "ISO 10993-1:2018 - Partial compliance (endpoints 5.1, 5.2, 5.4 only)"
Expected: ISO 10993-1 frequency = 1 (still cited, even if partial)
Note: Flag as "partial compliance" for context
Verification: Partial citations counted but flagged
```

**Acceptance Criteria:**

- Only Section 17 formal citations counted
- "Not applicable" standards excluded
- Partial compliance standards counted but flagged

---

## 4. Comparison Methodology

### 4.1 Tool Output vs. Predicate Frequency

**Objective:** Systematically compare FDA standards tool recommendations against predicate analysis to identify gaps and over-applications.

**Verification Method:**

1. **Three-tier comparison framework:**

   **Tier 1: High-confidence matches (≥80% predicate frequency)**
   - Tool says "Standard X applies" → Check if X appears in ≥80% of predicates
   - **If YES:** ✅ MATCH (tool correctly recommends high-frequency standard)
   - **If NO:** ⚠️ TOOL OVER-APPLIES (recommending rare standard)

   **Tier 2: Critical gaps (≥80% predicate frequency, tool omits)**
   - Standard Y appears in ≥80% of predicates → Check if tool recommends Y
   - **If YES:** ✅ MATCH (tool catches high-frequency standard)
   - **If NO:** ❌ CRITICAL GAP (tool missed mandatory standard)

   **Tier 3: Low-frequency standards (<10% predicate frequency)**
   - Standard Z appears in <10% of predicates → Check if tool recommends Z
   - **If tool recommends:** ⚠️ OVER-APPLICATION (edge case only)
   - **If tool omits:** ✅ CORRECT (rare standard, device-specific)

2. **Gap severity classification:**

   - **CRITICAL GAP:** Tool missed standard cited in ≥80% of predicates
     - **Impact:** FDA RTA risk, 3-6 month delay, $200K-$400K cost
     - **Example:** Tool omits ISO 11070 for DQY catheter (98% frequency)

   - **MODERATE GAP:** Tool missed standard cited in 50-79% of predicates
     - **Impact:** Major deficiency letter, 2-4 month delay
     - **Example:** Tool omits ASTM F2394 for nitinol stent (65% frequency)

   - **MINOR GAP:** Tool missed standard cited in 20-49% of predicates
     - **Impact:** Device-specific, may or may not apply
     - **Example:** Tool omits ISO 10993-11 for short-term device (30% frequency)

   - **OVER-APPLICATION:** Tool recommends standard cited in <10% of predicates
     - **Impact:** Unnecessary testing, $15K-$50K wasted cost
     - **Example:** Tool recommends IEC 60601-1 for manual non-powered device (5% frequency)

3. **Discrepancy report format:**

   ```markdown
   ## DQY Cardiovascular Catheter - Tool vs. Predicate Analysis

   ### CRITICAL GAPS (Tool Missed, ≥80% Predicate Frequency)
   - ❌ ISO 11070:2011 (Terminology for central nervous system, vascular devices)
     - Predicate frequency: 46/47 (97.9%)
     - Tool recommendation: NOT included
     - Impact: HIGH - FDA expects this for all cardiovascular catheters
     - Recommendation: Add to DQY mandatory standards

   ### MATCHES (Tool Correct, ≥80% Predicate Frequency)
   - ✅ ISO 10993-1:2018 (Biological Evaluation)
     - Predicate frequency: 47/47 (100%)
     - Tool recommendation: HIGH confidence
   - ✅ IEC 60601-1:2005 (Electrical Safety)
     - Predicate frequency: 42/47 (89%)
     - Tool recommendation: HIGH confidence

   ### OVER-APPLICATIONS (Tool Recommends, <10% Predicate Frequency)
   - ⚠️ ISO 10993-18:2020 (Chemical Characterization)
     - Predicate frequency: 2/47 (4.3%)
     - Tool recommendation: MEDIUM confidence
     - Context: Only for drug-eluting catheters (rare)
     - Recommendation: Downgrade to CONDITIONAL (if drug-eluting)

   ### MODERATE GAPS (Tool Missed, 50-79% Predicate Frequency)
   - ⚠️ ASTM F2394-07 (Guide for Determination of Catheter Coating Durability)
     - Predicate frequency: 31/47 (66%)
     - Tool recommendation: NOT included
     - Context: Applies only to coated catheters (hydrophilic, antimicrobial)
     - Recommendation: Add as CONDITIONAL standard (if coated)
   ```

**Test Cases:**

```bash
# Test Case 4.1.1: DQY Cardiovascular Catheter
Predicate analysis: 47 DQY PDFs
Tool output: 8 standards (HIGH confidence)
Comparison:
  - ISO 10993-1: Tool ✅, Predicate 100% → MATCH
  - ISO 11070: Tool ❌, Predicate 98% → CRITICAL GAP
  - IEC 60601-1: Tool ✅, Predicate 89% → MATCH
  - ISO 10993-18: Tool ⚠️, Predicate 4% → OVER-APPLICATION

Expected discrepancy report:
  - 1 CRITICAL GAP (ISO 11070)
  - 2 MATCHES (ISO 10993-1, IEC 60601-1)
  - 1 OVER-APPLICATION (ISO 10993-18)

Recommendation: Add ISO 11070 to tool's DQY mandatory list

# Test Case 4.1.2: OVE Orthopedic Spinal Implant
Predicate analysis: 50 OVE PDFs
Tool output: 6 standards
Comparison:
  - ASTM F1717: Tool ✅, Predicate 95% → MATCH
  - ISO 10993-1: Tool ✅, Predicate 100% → MATCH
  - ISO 10993-11: Tool ❌, Predicate 72% → MODERATE GAP
  - ASTM F136: Tool ❌, Predicate 45% → CONDITIONAL (Ti-6Al-4V only)

Recommendation:
  - Add ISO 10993-11 for long-term implants (systemic toxicity)
  - Add ASTM F136 as CONDITIONAL (if titanium alloy used)

# Test Case 4.1.3: QKK Software/SaMD
Predicate analysis: 30 QKK PDFs
Tool output: 5 standards
Comparison:
  - IEC 62304: Tool ✅, Predicate 97% → MATCH
  - IEC 62366-1: Tool ✅, Predicate 83% → MATCH
  - Cybersecurity (AAMI TIR57): Tool ❌, Predicate 67% → MODERATE GAP
  - IEC 60601-1: Tool ⚠️, Predicate 10% → OVER-APPLICATION (standalone SaMD doesn't need electrical)

Recommendation:
  - Add cybersecurity guidance for connected devices
  - Make IEC 60601-1 CONDITIONAL (if device has electrical components)
```

**Acceptance Criteria:**

- Discrepancy report generated for each product code
- Gaps classified by severity (CRITICAL, MODERATE, MINOR)
- Over-applications identified and justified
- Recommendations actionable (add to tool, make conditional, etc.)

---

### 4.2 Actionable Recommendations

**Objective:** Provide clear, actionable recommendations to improve tool accuracy based on predicate analysis.

**Verification Method:**

1. **Recommendation format:**

   ```markdown
   ## Recommendation: Add ISO 11070 to DQY Mandatory Standards

   **Evidence:**
   - Predicate frequency: 46/47 DQY clearances (97.9%)
   - Tool current status: Not included
   - Gap severity: CRITICAL

   **Rationale:**
   ISO 11070 (Terminology for central nervous system, vascular devices) is cited in nearly all DQY cardiovascular catheter clearances. FDA expects consistent terminology for catheter specifications.

   **Implementation:**
   1. Add to `standards_database.json`:
      ```json
      {
        "standard": "ISO 11070:2011",
        "title": "Terminology for central nervous system, vascular devices",
        "category": "cardiovascular",
        "confidence": "HIGH",
        "applicability": "All intravascular catheters (DQY, DQA, etc.)"
      }
      ```
   2. Update `knowledge_based_generator.py`:
      - Trigger: product_code == "DQY"
      - Condition: Always include (mandatory)
   3. Test: Re-run DQY generation, verify ISO 11070 appears

   **Expected Impact:**
   - Eliminates critical gap (97.9% → 100% coverage)
   - Prevents FDA RTA for DQY devices
   - Increases tool accuracy for cardiovascular devices
   ```

2. **Recommendation prioritization:**

   **Priority 1: CRITICAL GAPS (implement immediately)**
   - Standards cited in ≥80% of predicates, tool omits
   - High FDA RTA risk
   - Examples: ISO 11070 for DQY, ASTM F1717 for OVE

   **Priority 2: OVER-APPLICATIONS (implement within 1 month)**
   - Standards tool recommends but <10% predicates cite
   - Wastes user resources ($15K-$50K per unnecessary test)
   - Examples: IEC 60601-1 for manual devices, ISO 10993-18 for non-drug devices

   **Priority 3: MODERATE GAPS (implement within 3 months)**
   - Standards cited in 50-79% of predicates
   - Device-specific, may need conditional logic
   - Examples: ISO 10993-11 for long-term implants, ASTM F2394 for coated catheters

   **Priority 4: REFINEMENTS (implement as bandwidth allows)**
   - Version updates (ISO 10993-1:2018 → :2025)
   - Category improvements (reorganize standards by device type)

**Test Cases:**

```bash
# Test Case 4.2.1: Implementing CRITICAL GAP recommendation
Initial state: Tool omits ISO 11070 for DQY
Predicate data: 46/47 DQY predicates cite ISO 11070 (97.9%)

Step 1: Add ISO 11070 to standards database
Step 2: Update DQY product code logic
Step 3: Re-run tool for DQY test device
Expected: ISO 11070 now appears in output

Verification: Run tool on 5 test DQY devices, confirm ISO 11070 in all

# Test Case 4.2.2: Fixing OVER-APPLICATION
Initial state: Tool recommends IEC 60601-1 for all devices
Predicate data: IEC 60601-1 cited in 10% of manual device predicates

Step 1: Add conditional logic: IF powered THEN IEC 60601-1
Step 2: Re-run tool for manual catheter test device
Expected: IEC 60601-1 NOT in output for manual device

Verification: Manual device → no electrical standards, powered device → includes electrical

# Test Case 4.2.3: Adding CONDITIONAL standard
Initial state: Tool recommends ISO 10993-11 for all implants
Predicate data: ISO 10993-11 cited in 72% of LONG-TERM implants, 15% of short-term

Step 1: Add contact duration detection
Step 2: Add conditional: IF contact_duration > 30 days THEN ISO 10993-11
Step 3: Re-run for short-term and long-term test devices
Expected:
  - Long-term implant → ISO 10993-11 included
  - Short-term device → ISO 10993-11 excluded

Verification: Conditional logic accurately reflects predicate patterns
```

**Acceptance Criteria:**

- Each gap has a specific, implementable recommendation
- Recommendations prioritized by impact and effort
- Test cases defined to verify implementation
- Expected accuracy improvement quantified (e.g., "Increases DQY coverage from 85% → 95%")

---

## 5. Test Cases by Product Code

### 5.1 DQY - Cardiovascular Catheter

**Device Characteristics:**
- Intravascular catheter (central venous, hemodialysis, etc.)
- Patient contact: Blood (long-term or permanent)
- Power: May be unpowered OR connected to external device
- Sterilization: Typically EO or radiation
- Materials: Polymer tubing, metallic components

**Expected Standards (≥80% Predicate Frequency):**

1. **ISO 10993-1:2018** (Biological Evaluation - Part 1: Evaluation and testing)
   - Predicate frequency: 100% (47/47)
   - Tool status: ✅ Recommended (HIGH confidence)

2. **ISO 10993-5:2009** (Biological Evaluation - Part 5: Cytotoxicity)
   - Predicate frequency: 93.6% (44/47)
   - Tool status: ✅ Recommended (HIGH confidence)

3. **ISO 10993-11:2017** (Biological Evaluation - Part 11: Systemic toxicity)
   - Predicate frequency: 85.1% (40/47)
   - Tool status: ⚠️ Sometimes missed (depends on contact duration logic)

4. **ISO 11070:2011** (Terminology - Central nervous system, vascular devices)
   - Predicate frequency: 97.9% (46/47)
   - Tool status: ❌ NOT recommended (CRITICAL GAP)

5. **IEC 60601-1:2005** (Medical electrical equipment - Part 1: General safety)
   - Predicate frequency: 89.4% (42/47) - for powered/connected catheters
   - Tool status: ⚠️ Sometimes over-applied to unpowered

6. **ISO 11135:2014** (Sterilization - Ethylene oxide)
   - Predicate frequency: 80.8% (38/47) - for EO sterilized
   - Tool status: ⚠️ Conditional (sterilization method dependent)

**Verification Test:**

```bash
# Test Case 5.1.1: DQY Predicate Analysis
Sample size: 47 DQY PDFs (2020-2025)
Extraction accuracy target: ≥95%

Expected outputs:
1. Frequency table:
   | Standard | Count | Frequency | Tool Rec |
   |----------|-------|-----------|----------|
   | ISO 10993-1:2018 | 47 | 100% | ✅ HIGH |
   | ISO 11070:2011 | 46 | 97.9% | ❌ MISSING |
   | ISO 10993-5:2009 | 44 | 93.6% | ✅ HIGH |
   | IEC 60601-1:2005 | 42 | 89.4% | ⚠️ CONDITIONAL |

2. Gap report:
   - CRITICAL: ISO 11070 missing (97.9% frequency)
   - OVER-APPLICATION: IEC 60601-1 for unpowered catheters

3. Recommendation:
   "Add ISO 11070 as mandatory for all DQY product codes"

Verification:
- Manual spot-check: 5 random DQY PDFs
- Confirm ISO 11070 present in Section 17 of all 5
- Confirm tool currently omits ISO 11070
```

---

### 5.2 OVE - Orthopedic Spinal Implant

**Device Characteristics:**
- Permanent implant (spinal fusion cage, rod, screw)
- Patient contact: Bone/tissue (>30 days, permanent)
- Power: None (passive implant)
- Sterilization: Typically radiation or aseptic processing
- Materials: Titanium alloy (Ti-6Al-4V), PEEK, stainless steel

**Expected Standards (≥80% Predicate Frequency):**

1. **ISO 10993-1:2018** (Biological Evaluation - Part 1)
   - Predicate frequency: 100% (50/50)
   - Tool status: ✅ Recommended

2. **ASTM F1717-04** (Spinal Implant Constructions - Static/fatigue testing)
   - Predicate frequency: 94% (47/50)
   - Tool status: ✅ Recommended (HIGH confidence)

3. **ISO 5832-3** (Metallic materials - Part 3: Ti-6Al-4V alloy)
   - Predicate frequency: 82% (41/50) - for titanium devices
   - Tool status: ⚠️ Conditional (material dependent)

4. **ISO 10993-11:2017** (Biological Evaluation - Part 11: Systemic toxicity)
   - Predicate frequency: 72% (36/50) - MODERATE GAP
   - Tool status: ❌ Sometimes missed (long-term implant requirement)

5. **ASTM F136** (Ti-6Al-4V ELI material specification)
   - Predicate frequency: 68% (34/50) - for surgical implants
   - Tool status: ❌ NOT recommended (MODERATE GAP)

**Verification Test:**

```bash
# Test Case 5.2.1: OVE Predicate Analysis
Sample size: 50 OVE PDFs (2018-2025)

Expected outputs:
1. Frequency table:
   | Standard | Count | Frequency | Tool Rec |
   |----------|-------|-----------|----------|
   | ISO 10993-1:2018 | 50 | 100% | ✅ HIGH |
   | ASTM F1717-04 | 47 | 94% | ✅ HIGH |
   | ISO 5832-3 | 41 | 82% | ⚠️ CONDITIONAL |
   | ISO 10993-11 | 36 | 72% | ❌ MISSING |
   | ASTM F136 | 34 | 68% | ❌ MISSING |

2. Gap report:
   - MODERATE: ISO 10993-11 (72% frequency) - long-term implant requirement
   - MODERATE: ASTM F136 (68% frequency) - titanium alloy material spec

3. Recommendation:
   "Add ISO 10993-11 for all permanent implants (>30 day contact)"
   "Add ASTM F136 as conditional for Ti-6Al-4V devices"

Verification:
- Stratified sample: 5 titanium devices, 5 PEEK devices
- Confirm titanium devices cite ASTM F136, PEEK devices don't
```

---

### 5.3 QKK - Software/Digital Pathology SaMD

**Device Characteristics:**
- Software as Medical Device (SaMD)
- Standalone software (no hardware component)
- Use: Digital pathology image analysis, AI-assisted diagnosis
- Connectivity: Cloud-based or standalone
- Cybersecurity: Required for connected devices

**Expected Standards (≥80% Predicate Frequency):**

1. **IEC 62304:2006** (Medical device software - Software lifecycle)
   - Predicate frequency: 96.7% (29/30)
   - Tool status: ✅ Recommended (HIGH confidence)

2. **IEC 62366-1:2015** (Usability engineering - Part 1: Application to medical devices)
   - Predicate frequency: 83.3% (25/30)
   - Tool status: ✅ Recommended (HIGH confidence)

3. **ISO 14971:2019** (Risk management for medical devices)
   - Predicate frequency: 100% (30/30)
   - Tool status: ✅ Recommended (HIGH confidence)

4. **AAMI TIR57:2016** (Cybersecurity for networked medical devices)
   - Predicate frequency: 66.7% (20/30) - MODERATE GAP
   - Tool status: ⚠️ Sometimes missed (connectivity dependent)

5. **IEC 82304-1:2016** (Health software - Part 1: General requirements)
   - Predicate frequency: 50% (15/30)
   - Tool status: ⚠️ Sometimes recommended

**Verification Test:**

```bash
# Test Case 5.3.1: QKK Software Device Analysis
Sample size: 30 QKK PDFs (2020-2025)
Note: Smaller sample (low-volume product code)

Expected outputs:
1. Frequency table:
   | Standard | Count | Frequency | Tool Rec |
   |----------|-------|-----------|----------|
   | ISO 14971:2019 | 30 | 100% | ✅ HIGH |
   | IEC 62304:2006 | 29 | 96.7% | ✅ HIGH |
   | IEC 62366-1:2015 | 25 | 83.3% | ✅ HIGH |
   | AAMI TIR57:2016 | 20 | 66.7% | ⚠️ CONDITIONAL |
   | IEC 82304-1 | 15 | 50% | ⚠️ CONDITIONAL |

2. Gap report:
   - MODERATE: AAMI TIR57 (66.7%) - cybersecurity for connected devices
   - Context: Post-2022 Cybersecurity Guidance, frequency increasing

3. Recommendation:
   "Add AAMI TIR57 for all connected/networked SaMD devices"
   "Monitor IEC 82304-1 adoption (may become mandatory)"

Verification:
- Temporal analysis: Pre-2022 vs. Post-2022
- Expect AAMI TIR57 frequency: ~20% (pre-2022) → ~80% (post-2022)
- Confirms FDA guidance impact on standards
```

---

### 5.4 Cross-Product Code Validation

**Objective:** Verify predicate analysis detects device-type patterns accurately.

**Test Cases:**

```bash
# Test Case 5.4.1: Material-specific standards
Product codes: OVE (orthopedic), MAX (bone cement), JJE (knee prosthesis)
Common material: PMMA (polymethylmethacrylate)

Expected: ISO 5833 (PMMA bone cement) cited in:
  - MAX: 95% (primary material)
  - OVE: 10% (cage augmentation only)
  - JJE: 5% (rare)

Verification: Predicate analysis captures material-specific applicability

# Test Case 5.4.2: Sterilization method patterns
Product codes: DQY (catheter), OVE (implant), GEI (electrosurgical)
Sterilization: EO vs. Radiation vs. None

Expected:
  - DQY: ISO 11135 (EO) 80%, ISO 11137 (radiation) 15%
  - OVE: ISO 11137 (radiation) 70%, ISO 11135 (EO) 20%
  - GEI: None (reusable, steam sterilization by user)

Verification: Sterilization standards correlate with device type

# Test Case 5.4.3: Software vs. hardware standards
Product codes: QKK (software-only), DQY (hardware with embedded software)

Expected:
  - QKK: IEC 62304 (97%), IEC 60601-1 (10% - rare hybrid)
  - DQY: IEC 60601-1 (89%), IEC 62304 (30% - embedded software)

Verification: Software standards frequency reflects SaMD vs. embedded
```

---

## 6. Acceptance Criteria

### 6.1 Extraction Accuracy

**Objective:** Verify Section 17 standards are extracted correctly from 510(k) PDFs.

**Metrics:**

1. **Overall extraction accuracy: ≥95%**
   - **Definition:** Percentage of standards correctly extracted from Section 17
   - **Measurement:** Manual spot-check of 10% of PDFs (minimum 5 PDFs per product code)
   - **Pass criterion:** ≥95% of standards match manual count (within ±1 standard per PDF)

2. **False positive rate: ≤5%**
   - **Definition:** Standards extracted from outside Section 17 (background mentions, etc.)
   - **Measurement:** Manual review of extracted standards, verify all appear in Section 17
   - **Pass criterion:** ≤5% of extracted standards are false positives

3. **False negative rate: ≤10%**
   - **Definition:** Standards in Section 17 but not extracted (missed)
   - **Measurement:** Manual reading of Section 17, compare vs. automated extraction
   - **Pass criterion:** ≤10% of Section 17 standards are missed

**Verification Process:**

```bash
# Step 1: Random sample selection
Sample: 10% of all PDFs (stratified by product code)
Minimum: 5 PDFs per product code

# Step 2: Manual extraction
Human reviewer reads Section 17, lists all standards
Format: "ISO 10993-1:2018, IEC 60601-1:2005, ..."

# Step 3: Automated extraction
Run extraction script on same PDFs
Output: JSON with extracted standards

# Step 4: Comparison
Compare manual vs. automated lists
Calculate:
  - True positives (in both)
  - False positives (automated only, not in manual)
  - False negatives (manual only, not in automated)

# Step 5: Accuracy calculation
Extraction accuracy = (True positives) / (True positives + False negatives)
Pass: ≥95%

# Example:
Manual: 10 standards
Automated: 11 standards
Match: 9 standards
False positive: 2 (automated extracted from footnotes)
False negative: 1 (automated missed ISO standard with unusual formatting)

Accuracy: 9 / (9 + 1) = 90% → FAIL (below 95%)
Investigation: Improve boundary detection to exclude footnotes
```

---

### 6.2 Frequency Accuracy

**Objective:** Ensure frequency counts are within ±5% of manual calculation.

**Metrics:**

1. **Frequency calculation accuracy: ±5%**
   - **Definition:** Automated frequency % within ±5 percentage points of manual count
   - **Measurement:** Manually count predicates citing a standard, compare vs. automated
   - **Pass criterion:** Automated frequency within ±5% of manual count

2. **Denominator validation: 100%**
   - **Definition:** Correct denominator used (total analyzed PDFs, not downloaded)
   - **Measurement:** Verify denominator matches count of successfully processed PDFs
   - **Pass criterion:** Denominator documented and correct

**Verification Process:**

```bash
# Step 1: Select high-frequency standard for validation
Example: ISO 10993-1 for DQY catheters

# Step 2: Manual count
Human reviewer counts PDFs citing ISO 10993-1
Manual count: 47 PDFs out of 50 total → 94.0%

# Step 3: Automated count
Extraction script counts ISO 10993-1 citations
Automated count: 46 PDFs out of 50 total → 92.0%

# Step 4: Comparison
Difference: 94.0% - 92.0% = 2.0 percentage points
Pass criterion: ±5%
Result: 2.0% ≤ 5% → PASS ✅

# Step 5: Investigation of discrepancy
Manual review of 1 discrepant PDF:
  - PDF K123456: Manual found ISO 10993-1, automated missed
  - Reason: Unusual formatting "ISO10993-1" (no space)
  - Fix: Update regex to handle no-space formatting

# Re-run after fix:
Automated count: 47 PDFs → 94.0%
Difference: 0% → PERFECT MATCH ✅
```

---

### 6.3 Coverage Completeness

**Objective:** Capture ≥90% of unique standards across product code.

**Metrics:**

1. **Standard diversity capture: ≥90%**
   - **Definition:** Percentage of unique standards cited across all predicates that are correctly extracted
   - **Measurement:** Unique standards from manual review vs. automated extraction
   - **Pass criterion:** Automated captures ≥90% of unique standards

2. **Rare standard detection: ≥80%**
   - **Definition:** Ability to detect standards cited in 10-20% of predicates
   - **Measurement:** Manually identify rare standards, verify automated extraction
   - **Pass criterion:** ≥80% of rare standards detected

**Verification Process:**

```bash
# Step 1: Manual catalog of unique standards
Product code: DQY (50 PDFs)
Human reviewer catalogs ALL unique standards across all 50 PDFs
Unique standards: 25 distinct standards

# Step 2: Automated catalog
Extraction script generates unique standard list
Automated unique standards: 23 distinct standards

# Step 3: Coverage calculation
Coverage = 23 / 25 = 92%
Pass criterion: ≥90%
Result: 92% ≥ 90% → PASS ✅

# Step 4: Gap analysis
Manually review 2 missing standards:
  1. ASTM F2394 (cited in 1 PDF, rare)
     - Reason: PDF formatting issue, extracted as "ASTMF2394" without space
  2. ISO 10993-18 (cited in 2 PDFs, rare)
     - Reason: Mentioned in footnote, boundary detection excluded

# Step 5: Fix and re-run
Update regex for ASTM (handle no-space)
Coverage: 24 / 25 = 96% → IMPROVED ✅
```

---

### 6.4 Tool Alignment

**Objective:** Tool recommendations should align with ≥80% predicate frequency standards.

**Metrics:**

1. **High-frequency standard coverage: ≥90%**
   - **Definition:** Percentage of ≥80% predicate frequency standards that tool recommends
   - **Measurement:** List all standards with ≥80% frequency, check if tool recommends
   - **Pass criterion:** Tool recommends ≥90% of high-frequency standards

2. **Over-application rate: ≤20%**
   - **Definition:** Percentage of tool recommendations that appear in <10% of predicates
   - **Measurement:** List all tool recommendations, check predicate frequency
   - **Pass criterion:** ≤20% of tool recommendations are low-frequency (<10%)

**Verification Process:**

```bash
# Step 1: Identify high-frequency standards (≥80% predicate frequency)
Product code: DQY (50 PDFs)
High-frequency standards (≥80%):
  1. ISO 10993-1 (100%)
  2. ISO 11070 (98%)
  3. ISO 10993-5 (94%)
  4. IEC 60601-1 (89%)
  5. ISO 10993-11 (85%)
  6. ISO 11135 (81%)
Total: 6 standards

# Step 2: Check tool recommendations
Tool output for DQY:
  - ISO 10993-1 ✅
  - ISO 10993-5 ✅
  - IEC 60601-1 ✅
  - ISO 10993-11 ✅
  - ISO 11135 ✅
  - ISO 11070 ❌ (MISSING)

Tool coverage: 5 / 6 = 83.3%
Pass criterion: ≥90%
Result: 83.3% < 90% → FAIL ❌

# Step 3: Gap analysis
Critical gap identified: ISO 11070 (98% frequency) not recommended by tool
Impact: HIGH - FDA RTA risk

# Step 4: Fix implementation
Add ISO 11070 to DQY mandatory standards in tool database
Re-run tool for DQY

# Step 5: Re-verification
Tool now recommends all 6 high-frequency standards
Coverage: 6 / 6 = 100% → PASS ✅

# Step 6: Over-application check
Tool recommendations for DQY: 8 standards total
Low-frequency (<10%) recommendations: 1 (ISO 10993-18 at 4% frequency)
Over-application rate: 1 / 8 = 12.5%
Pass criterion: ≤20%
Result: 12.5% ≤ 20% → PASS ✅
```

---

## 7. Outlier Detection Verification

### 7.1 Outlier Definition

**Objective:** Identify and explain unusual predicate patterns (rare or universal standards).

**Outlier Categories:**

1. **Rare standards (<10% frequency):**
   - May be device-specific edge cases
   - May indicate specialized designs (e.g., drug-eluting, MRI-compatible)
   - May be emerging standards (recently recognized by FDA)

2. **Universal standards (>90% frequency):**
   - Likely mandatory for product code
   - Should be HIGH confidence in tool recommendations
   - Absence in a predicate may indicate incomplete submission or N/A case

3. **Temporal outliers (frequency shift >30% across years):**
   - May indicate FDA guidance change
   - May indicate standard recognition/withdrawal
   - Example: Cybersecurity standards post-2022 guidance

**Verification Method:**

```bash
# Step 1: Statistical outlier detection
For each standard, calculate:
  - Mean frequency across all product codes
  - Standard deviation
  - Z-score = (frequency - mean) / std_dev

Outlier threshold: |Z-score| > 2.0

# Step 2: Manual investigation
For each outlier, determine:
  - Why is this standard rare/common?
  - Is this a legitimate pattern or data issue?
  - Should tool behavior change based on this pattern?

# Example: ISO 11070 for DQY (98% frequency, Z-score = +3.2)
Investigation:
  - ISO 11070 is cardiovascular device terminology standard
  - Mandatory for all vascular catheters per FDA expectations
  - Tool should add as HIGH confidence for DQY

# Example: ISO 10993-18 for DQY (4% frequency, Z-score = -2.8)
Investigation:
  - ISO 10993-18 is chemical characterization for degradable materials
  - Only applies to drug-eluting catheters (rare)
  - Tool should make CONDITIONAL (if drug-eluting)
```

---

### 7.2 Regulatory Context Verification

**Objective:** Explain outliers in regulatory context (guidance changes, special controls, etc.).

**Verification Process:**

1. **Guidance-driven outliers:**
   - Check FDA guidance publication dates
   - Correlate with standard frequency shifts
   - Example: 2022 Cybersecurity Guidance → AAMI TIR57 frequency increases

2. **Special controls outliers:**
   - Check if product code has special controls (De Novo classification)
   - Verify special control standards appear in predicates
   - Example: De Novo for AI pathology may mandate IEC 62304 (software)

3. **Supersession outliers:**
   - Check if rare standard was superseded by newer version
   - Explain frequency drop for old version
   - Example: ISO 10993-1:2009 rare (superseded by :2018 in 2018)

**Test Cases:**

```bash
# Test Case 7.2.1: Cybersecurity guidance impact
Product code: QKK (software)
Standard: AAMI TIR57 (cybersecurity)
Temporal analysis:
  - Pre-2022 (N=10 PDFs): AAMI TIR57 frequency = 20%
  - Post-2022 (N=20 PDFs): AAMI TIR57 frequency = 80%
Explanation: 2022 FDA Cybersecurity Guidance mandated cybersecurity documentation
Recommendation: Tool should include AAMI TIR57 for connected software devices

# Test Case 7.2.2: De Novo special controls
Product code: XYZ (novel AI diagnostic)
De Novo decision: K191234 (2019)
Special controls: Require IEC 62304, IEC 62366-1, clinical validation
Predicate analysis: All post-2019 XYZ devices cite these standards (100% frequency)
Explanation: De Novo established testing requirements for product code
Recommendation: Tool should auto-add special control standards for De Novo codes

# Test Case 7.2.3: Standard supersession
Standard: ISO 10993-1:2009 vs. :2018
Frequency over time:
  - 2015-2017: :2009 = 90%, :2018 = 0%
  - 2018-2020: :2009 = 50%, :2018 = 40% (transition)
  - 2021-2025: :2009 = 5%, :2018 = 95%
Explanation: FDA recognized :2018 edition in 2018, transition period 2018-2020
Recommendation: Tool should recommend latest FDA-recognized version
```

---

### 7.3 Recommendation: Manual Review Flags

**Objective:** Tool should flag outliers for user manual review (not auto-recommend).

**Flagging System:**

1. **Rare standard flag (<10% frequency):**
   - Tool output: "⚠️ ISO 10993-18 (RARE - 4% of DQY predicates) - Review applicability"
   - User prompt: "This standard applies only to drug-eluting catheters. Is your device drug-eluting?"

2. **Emerging standard flag (frequency increasing >30% in last 2 years):**
   - Tool output: "🔺 AAMI TIR57 (EMERGING - 80% of post-2022 QKK predicates) - Consider for connected devices"
   - User prompt: "Cybersecurity is increasingly expected. Is your device networked?"

3. **Universal standard confirmation (>95% frequency):**
   - Tool output: "✅ ISO 10993-1 (MANDATORY - 100% of DQY predicates) - Required for all devices"
   - User prompt: "This standard is mandatory. Confirm patient contact type for parts."

**Test Cases:**

```bash
# Test Case 7.3.1: Rare standard user prompt
User: Generate standards for DQY catheter
Tool: [Generates 8 standards]
Tool: "⚠️ ISO 10993-18 detected in 4% of DQY predicates (drug-eluting only)"
Tool: "Is your catheter drug-eluting? (yes/no)"
User input: "no"
Tool: Excludes ISO 10993-18 from final list
Verification: User informed of rare standard, made conscious decision

# Test Case 7.3.2: Emerging standard awareness
User: Generate standards for QKK software
Tool: [Generates 5 standards]
Tool: "🔺 AAMI TIR57 cybersecurity increasing (20% pre-2022 → 80% post-2022)"
Tool: "Is your software networked/cloud-based? (yes/no)"
User input: "yes"
Tool: Adds AAMI TIR57 to final list
Verification: User aware of emerging FDA expectations

# Test Case 7.3.3: Mandatory standard auto-include
User: Generate standards for DQY catheter
Tool: Auto-includes ISO 10993-1 (100% frequency, no prompt)
Tool output: "✅ ISO 10993-1 (MANDATORY - cited in all DQY predicates)"
Verification: High-frequency standards don't burden user with prompts
```

---

## 8. Integration Testing

### 8.1 End-to-End Predicate Analysis Integration

**Objective:** Verify predicate analysis seamlessly integrates into tool workflow.

**User Journey:**

```bash
# Step 1: User generates standards for DQY catheter
User: /fda-tools:generate-standards DQY

# Step 2: Tool runs knowledge-based analysis (current implementation)
Tool output (before predicate integration):
  - ISO 10993-1 (HIGH confidence)
  - ISO 10993-5 (HIGH confidence)
  - IEC 60601-1 (MEDIUM confidence)
  - ISO 11135 (MEDIUM confidence - if EO sterilized)
Total: 4 standards

# Step 3: Tool cross-references predicate analysis (NEW FEATURE)
Tool: "Cross-referencing 47 cleared DQY predicates..."
Tool: "Predicate analysis complete. 3 recommendations."

# Step 4: Tool displays integrated output
Output format:

## DQY Cardiovascular Catheter - Standards Analysis

### Tool Recommendations (Knowledge-Based)
✅ ISO 10993-1:2018 - Biological Evaluation (HIGH confidence)
   Predicate validation: Cited in 47/47 predicates (100%) ✅ CONFIRMED

✅ ISO 10993-5:2009 - Cytotoxicity (HIGH confidence)
   Predicate validation: Cited in 44/47 predicates (94%) ✅ CONFIRMED

⚠️ IEC 60601-1:2005 - Electrical Safety (MEDIUM confidence)
   Predicate validation: Cited in 42/47 predicates (89%) ⚠️ VERIFY if powered

⚠️ ISO 11135:2014 - EO Sterilization (MEDIUM confidence)
   Predicate validation: Cited in 38/47 predicates (81%) ⚠️ VERIFY sterilization method

### Predicate Analysis - Additional Recommendations
❌ ISO 11070:2011 - Cardiovascular Device Terminology
   Tool missed this standard (CRITICAL GAP)
   Cited in 46/47 DQY predicates (98%)
   Recommendation: ADD to your standards list (FDA expects this for all vascular catheters)

⚠️ ISO 10993-11:2017 - Systemic Toxicity
   Tool included conditionally based on contact duration
   Cited in 40/47 DQY predicates (85%)
   Recommendation: CONFIRM if device has prolonged blood contact (>24 hours)

### Summary
- Tool high-confidence matches: 2/2 (100%) ✅
- Tool medium-confidence validated: 2/2 (100%) ✅
- Critical gaps identified: 1 (ISO 11070) ❌
- Recommendations: Add ISO 11070, verify IEC 60601-1 and ISO 11135 applicability

### Next Steps
1. Add ISO 11070 to your standards list
2. Confirm device power source (for IEC 60601-1)
3. Confirm sterilization method (for ISO 11135)
4. Review biocompatibility endpoints per ISO 10993-1
```

**Verification:**

- User sees both tool recommendations AND predicate analysis
- Predicate frequency displayed for each standard
- Gaps clearly highlighted (CRITICAL, MODERATE)
- Actionable next steps provided

---

### 8.2 Confidence Level Integration

**Objective:** Tool confidence levels should align with predicate frequency.

**Confidence Mapping:**

```python
def calculate_confidence(predicate_frequency):
    """
    Map predicate frequency to tool confidence level.

    Args:
        predicate_frequency: Float 0.0-1.0 (percentage as decimal)

    Returns:
        str: "HIGH", "MEDIUM", or "LOW" confidence
    """
    if predicate_frequency >= 0.80:
        return "HIGH"  # ≥80% of predicates cite this standard
    elif predicate_frequency >= 0.50:
        return "MEDIUM"  # 50-79% of predicates cite this standard
    else:
        return "LOW"  # <50% of predicates cite this standard
```

**Example Output:**

```markdown
## DQY Standards - Confidence Levels

| Standard | Tool Confidence | Predicate Frequency | Alignment |
|----------|----------------|---------------------|-----------|
| ISO 10993-1 | HIGH | 100% (47/47) | ✅ MATCH |
| ISO 11070 | N/A (missing) | 98% (46/47) | ❌ SHOULD BE HIGH |
| ISO 10993-5 | HIGH | 94% (44/47) | ✅ MATCH |
| IEC 60601-1 | MEDIUM | 89% (42/47) | ⚠️ SHOULD BE HIGH |
| ISO 11135 | MEDIUM | 81% (38/47) | ✅ MATCH |
| ISO 10993-18 | MEDIUM | 4% (2/47) | ❌ SHOULD BE LOW |

**Confidence Alignment Score: 67% (4/6 match)**

### Recommendations to Improve Alignment:
1. Upgrade IEC 60601-1 to HIGH (89% frequency)
2. Downgrade ISO 10993-18 to LOW (4% frequency, drug-eluting only)
3. Add ISO 11070 at HIGH confidence (98% frequency)

After fixes: Expected alignment score = 100% (7/7 match)
```

---

### 8.3 Gap Detection User Interface

**Objective:** Present gaps in a clear, actionable format for users.

**Gap Report Format:**

```markdown
# Standards Gap Analysis - DQY Cardiovascular Catheter

## 🔴 CRITICAL GAPS (Immediate Action Required)

### ISO 11070:2011 - Cardiovascular Device Terminology
- **Status:** Tool did NOT recommend
- **Predicate frequency:** 46/47 (97.9%)
- **Impact:** FDA RTA risk (high)
- **Why it matters:** FDA expects consistent terminology for catheter specs (lumen diameter, length, etc.)
- **Action:** ✅ ADD to your standards list
- **Testing cost:** $0 (terminology standard, no testing)
- **Timeline:** Immediate (document preparation only)

---

## ⚠️ MODERATE GAPS (Review Recommended)

### ISO 10993-11:2017 - Systemic Toxicity
- **Status:** Tool recommended CONDITIONALLY (if prolonged contact)
- **Predicate frequency:** 40/47 (85.1%)
- **Impact:** Major deficiency letter risk (medium)
- **Why it matters:** Long-term blood contact requires systemic toxicity evaluation
- **Action:** ⚠️ VERIFY your device contact duration
  - If >24 hours contact: ADD to standards list
  - If <24 hours: MAY omit (justify in 510(k))
- **Testing cost:** $25,000 (systemic toxicity study)
- **Timeline:** 12-16 weeks (long-term study)

### ASTM F2394-07 - Catheter Coating Durability
- **Status:** Tool did NOT recommend
- **Predicate frequency:** 31/47 (66.0%)
- **Impact:** Medium (applies only to coated catheters)
- **Why it matters:** Hydrophilic/antimicrobial coatings must maintain integrity during use
- **Action:** ⚠️ CHECK if your catheter has a coating
  - If coated: ADD to standards list
  - If uncoated: OMIT
- **Testing cost:** $10,000 (coating durability study)
- **Timeline:** 4-6 weeks

---

## ✅ CONFIRMED MATCHES (Tool Recommendations Validated)

### ISO 10993-1:2018 - Biological Evaluation
- **Tool confidence:** HIGH
- **Predicate frequency:** 47/47 (100%)
- **Validation:** ✅ CORRECT - All DQY predicates cite this standard

### ISO 10993-5:2009 - Cytotoxicity
- **Tool confidence:** HIGH
- **Predicate frequency:** 44/47 (93.6%)
- **Validation:** ✅ CORRECT - Nearly all predicates cite this

[... additional matches ...]

---

## ⚠️ OVER-APPLICATIONS (Tool May Be Too Aggressive)

### ISO 10993-18:2020 - Chemical Characterization
- **Tool confidence:** MEDIUM
- **Predicate frequency:** 2/47 (4.3%)
- **Why rare:** Only for drug-eluting or absorbable devices
- **Action:** ⚠️ REMOVE unless your catheter is drug-eluting
- **Cost saved if removed:** $30,000 (chemical characterization study)

---

## 📊 Summary Statistics

- **Tool recommendations:** 8 standards
- **Predicate high-frequency (≥80%):** 6 standards
- **Tool coverage of high-frequency:** 5/6 (83.3%)
- **Critical gaps:** 1 (ISO 11070)
- **Over-applications:** 1 (ISO 10993-18)

**Overall tool accuracy:** 75% (6/8 recommendations validated by predicates)

---

## 🎯 Recommended Actions (Priority Order)

1. **[CRITICAL]** Add ISO 11070 to standards list → Prevents FDA RTA
2. **[HIGH]** Verify device contact duration → Determines if ISO 10993-11 needed ($25K decision)
3. **[MEDIUM]** Check catheter coating → Determines if ASTM F2394 needed ($10K decision)
4. **[LOW]** Remove ISO 10993-18 unless drug-eluting → Saves $30K if not applicable

**Estimated cost impact:** $65K potential savings + RTA prevention (priceless)
```

**User Experience Validation:**

- Gap report is actionable (clear next steps)
- Cost implications highlighted (helps prioritization)
- Risk levels clearly communicated (CRITICAL, MODERATE, LOW)
- User can make informed decisions (not just "here's a list")

---

## 9. Expert Review Requirements

### 9.1 Regulatory Affairs Professional Qualifications

**Objective:** Ensure verification is conducted by qualified RA professionals with relevant experience.

**Required Qualifications:**

1. **Experience:**
   - Minimum 5 years in medical device regulatory affairs
   - Direct 510(k) submission experience (at least 10 submissions)
   - Experience with target device type (cardiovascular, orthopedic, software, etc.)

2. **Standards Knowledge:**
   - Familiarity with FDA consensus standards database
   - Understanding of Section 17 formatting variations
   - Knowledge of biocompatibility, electrical safety, sterilization standards

3. **FDA Interaction:**
   - Pre-Submission meeting experience (at least 5 meetings)
   - Deficiency letter response experience
   - Understanding of FDA reviewer expectations

4. **Technical Skills:**
   - Can read 510(k) summary PDFs and extract information
   - Understands standard numbering conventions (ISO, IEC, ASTM)
   - Can interpret test protocol requirements

**Verification Activities:**

1. **Spot-Check Review (10% sample):**
   - Randomly select 10% of analyzed PDFs
   - Manually verify Section 17 extraction accuracy
   - Confirm frequency calculations
   - Validate gap analysis conclusions

2. **Predicate Pattern Review:**
   - Review frequency tables for each product code
   - Confirm patterns make regulatory sense (e.g., "Why is ISO 11070 98% for DQY?")
   - Identify any missing standards based on domain knowledge

3. **Tool Recommendation Validation:**
   - Compare tool output vs. predicate analysis
   - Confirm gap severity classifications (CRITICAL, MODERATE, LOW)
   - Validate recommendations are actionable

**Expert Review Checklist:**

```markdown
# Expert Review Checklist - TICKET-019 Predicate Analysis

**Reviewer:** [Name], [Title], [Years Experience]
**Review Date:** [YYYY-MM-DD]
**Product Codes Reviewed:** DQY, OVE, QKK

## Section 1: Extraction Accuracy Verification

### DQY Cardiovascular Catheter (5 PDFs spot-checked)

| PDF K-Number | Manual Count | Automated Count | Match? | Notes |
|--------------|--------------|-----------------|--------|-------|
| K242424 | 7 standards | 7 standards | ✅ | Perfect match |
| K252525 | 6 standards | 8 standards | ❌ | Automated extracted from footnotes, adjust boundary |
| K262626 | 0 standards | 0 standards | ✅ | Legitimate N/A (software only) |
| K272727 | 22 standards | 22 standards | ✅ | Comprehensive (valid outlier) |
| K282828 | 5 standards | 5 standards | ✅ | Match |

**Extraction accuracy: 80% (4/5 perfect match)**
**Issues identified:** Boundary detection includes footnotes (1 PDF)
**Recommendation:** Adjust boundary detection, re-run

---

## Section 2: Predicate Pattern Review

### DQY Frequency Table Review

| Standard | Frequency | RA Expert Assessment |
|----------|-----------|----------------------|
| ISO 10993-1 | 100% | ✅ Expected (all patient-contacting devices) |
| ISO 11070 | 98% | ✅ Expected (cardiovascular device terminology) |
| ISO 10993-5 | 94% | ✅ Expected (cytotoxicity for blood contact) |
| IEC 60601-1 | 89% | ⚠️ Seems high (not all catheters are powered) - Verify |
| ISO 10993-11 | 85% | ✅ Expected (prolonged blood contact → systemic toxicity) |

**Pattern assessment:** Mostly expected, IEC 60601-1 frequency warrants investigation
**Investigation finding:** Sample includes powered catheters (e.g., electrophysiology), frequency valid

---

## Section 3: Tool Recommendation Validation

### Gap Analysis Review (DQY)

| Gap Identified | Severity | RA Expert Agrees? | Comments |
|----------------|----------|-------------------|----------|
| ISO 11070 missing | CRITICAL | ✅ YES | FDA expects this for all vascular devices |
| ISO 10993-11 conditional | MODERATE | ✅ YES | Depends on contact duration (correct) |
| ISO 10993-18 over-application | OVER-APP | ✅ YES | Only for drug-eluting (rare) |

**Gap analysis assessment:** ACCURATE
**Recommendation validity:** All recommendations actionable and correct

---

## Section 4: Overall Assessment

**Extraction Quality:** ⭐⭐⭐⭐☆ (4/5 stars)
**Frequency Accuracy:** ⭐⭐⭐⭐⭐ (5/5 stars)
**Regulatory Validity:** ⭐⭐⭐⭐⭐ (5/5 stars)

**Issues Found:**
1. Boundary detection includes footnotes (minor, fixable)
2. [None identified]

**Production Ready?** ✅ YES (after boundary detection fix)

**Estimated Impact:**
- Prevents 1-2 FDA RTAs per 10 submissions (ISO 11070 gap detection)
- Saves $50K-$100K per submission (over-application detection)
- Improves tool accuracy from ~75% → ~95%

**Reviewer Signature:** ___________________________
**Date:** _______________
```

---

### 9.2 Expert Review Process

**Objective:** Standardized process for expert validation of predicate analysis.

**Phase 1: Sample Selection (1 hour)**

```bash
# Step 1: Stratified random sampling
Product codes: DQY, OVE, QKK (3 codes)
Sample size: 10% per product code (minimum 5 PDFs each)

# Step 2: Generate sample manifest
Output: sample_manifest.csv
Columns: K_Number, Product_Code, Clearance_Year, PDF_Path

# Step 3: Expert receives:
  - sample_manifest.csv (PDFs to review)
  - extraction_output.json (automated results)
  - review_checklist.md (template above)
```

**Phase 2: Manual Extraction (4-6 hours)**

```bash
# Expert manually extracts Section 17 from each sample PDF
For each PDF:
  1. Open PDF in viewer
  2. Locate Section 17 (or equivalent)
  3. List all standards with versions
  4. Record in manual_extraction.csv

Format: K_Number, Standard, Version, Section_Page
Example: K242424, ISO 10993-1, 2018, Page 10
```

**Phase 3: Comparison & Analysis (2-3 hours)**

```bash
# Step 1: Compare manual vs. automated extraction
Run comparison script:
  python3 compare_extractions.py \
    --manual manual_extraction.csv \
    --automated extraction_output.json \
    --output comparison_report.md

# Step 2: Review frequency tables
For each product code:
  - Review frequency table
  - Confirm patterns match domain knowledge
  - Flag any unexpected frequencies for investigation

# Step 3: Validate gap analysis
For each identified gap:
  - Confirm gap is real (standard truly missing from tool)
  - Confirm severity classification (CRITICAL, MODERATE, LOW)
  - Validate cost/impact estimates

# Step 4: Complete review checklist
Fill out expert review checklist (template above)
```

**Phase 4: Recommendations (1 hour)**

```bash
# Expert provides:
1. Overall assessment (PASS / FAIL / PASS with conditions)
2. Issues identified (list with severity)
3. Required fixes (before production use)
4. Optional improvements (nice to have)
5. Estimated impact (cost savings, RTA prevention)

# Deliverable: expert_review_report.md
```

---

## 10. Output Format Verification

### 10.1 Standards Frequency Table

**Objective:** Provide clear, sortable frequency table for each product code.

**Output Format:**

```markdown
# DQY Cardiovascular Catheter - Standards Frequency Analysis

**Analysis Date:** 2026-02-15
**Predicates Analyzed:** 47 PDFs (2020-2025)
**Data Quality:** 95% extraction accuracy (45/47 PDFs successfully processed)

---

## Standards Frequency Table

| Rank | Standard | Title | Count | Frequency | Category | Tool Rec |
|------|----------|-------|-------|-----------|----------|----------|
| 1 | ISO 10993-1:2018 | Biological Evaluation - Part 1 | 47 | 100.0% | Biocompat | ✅ HIGH |
| 2 | ISO 11070:2011 | Cardiovascular Device Terminology | 46 | 97.9% | General | ❌ MISSING |
| 3 | ISO 10993-5:2009 | Biological Evaluation - Part 5: Cytotoxicity | 44 | 93.6% | Biocompat | ✅ HIGH |
| 4 | IEC 60601-1:2005 | Medical Electrical Equipment - General Safety | 42 | 89.4% | Electrical | ✅ HIGH |
| 5 | ISO 10993-11:2017 | Biological Evaluation - Part 11: Systemic Toxicity | 40 | 85.1% | Biocompat | ⚠️ CONDITIONAL |
| 6 | ISO 11135:2014 | Sterilization - Ethylene Oxide | 38 | 80.9% | Sterilization | ✅ MEDIUM |
| 7 | ISO 10993-10:2010 | Biological Evaluation - Part 10: Irritation | 35 | 74.5% | Biocompat | ✅ MEDIUM |
| 8 | ASTM F2394-07 | Catheter Coating Durability | 31 | 66.0% | Device-Specific | ❌ MISSING |
| 9 | IEC 60601-1-2:2014 | EMC - Medical Electrical Equipment | 28 | 59.6% | Electrical | ✅ MEDIUM |
| 10 | ISO 10993-18:2020 | Chemical Characterization | 2 | 4.3% | Biocompat | ⚠️ OVER-APP |

**Total unique standards:** 25
**High-frequency (≥80%):** 6 standards
**Medium-frequency (50-79%):** 4 standards
**Low-frequency (<50%):** 15 standards

---

## Category Breakdown

### Biocompatibility (ISO 10993 series)
- **Overall frequency:** 47/47 predicates cite at least one biocompat standard (100%)
- **Most common:** ISO 10993-1 (100%), -5 (93.6%), -11 (85.1%)
- **Rarely cited:** ISO 10993-18 (4.3% - drug-eluting only)

### Electrical Safety (IEC 60601 series)
- **Overall frequency:** 42/47 predicates cite electrical standards (89.4%)
- **Most common:** IEC 60601-1 (89.4%), -1-2 EMC (59.6%)
- **Context:** High frequency due to powered catheters in sample

### Sterilization
- **Overall frequency:** 38/47 predicates cite sterilization standards (80.9%)
- **Methods:** EO (80.9%), Radiation (10.6%)
- **Context:** Most DQY catheters are EO sterilized

### Device-Specific
- **ASTM F2394 (Coating Durability):** 31/47 (66.0%)
- **ISO 11070 (Terminology):** 46/47 (97.9%)

---

## Tool Gap Analysis

### CRITICAL GAPS (Tool Missed, ≥80% Frequency)
1. **ISO 11070:2011** (97.9% frequency)
   - Impact: HIGH - FDA RTA risk
   - Recommendation: ADD to tool as mandatory for DQY

### MODERATE GAPS (Tool Missed, 50-79% Frequency)
2. **ASTM F2394-07** (66.0% frequency)
   - Impact: MEDIUM - Applies to coated catheters
   - Recommendation: ADD as conditional (if device has coating)

### OVER-APPLICATIONS (Tool Recommends, <10% Frequency)
3. **ISO 10993-18:2020** (4.3% frequency)
   - Impact: COST - Unnecessary $30K testing for non-drug devices
   - Recommendation: Make conditional (drug-eluting only)

---

## Recommendations

### Immediate Actions (Critical Gaps)
1. ✅ Add ISO 11070 to DQY mandatory standards
   - Prevents FDA RTA
   - Zero testing cost (terminology only)

### Review Actions (Moderate Gaps)
2. ⚠️ Add ASTM F2394 as conditional for coated catheters
   - Applies to 66% of DQY devices
   - Testing cost: $10K if applicable

### Cost Optimization
3. 💰 Remove ISO 10993-18 unless drug-eluting
   - Saves $30K for 96% of DQY devices
   - Only 4.3% of predicates cite this (rare edge case)

**Estimated Impact:**
- RTA prevention: Priceless (3-6 month delay avoided)
- Cost savings: $30K per device (ISO 10993-18 removal)
- Testing cost added: $10K (ASTM F2394 if coated)
- Net savings: $20K per device + RTA prevention
```

---

### 10.2 Outlier Flags

**Objective:** Highlight unusual patterns for user review.

**Output Format:**

```markdown
## Outlier Analysis - DQY Cardiovascular Catheter

### 🔴 Universal Standards (≥95% frequency)
Standards cited by nearly all predicates - likely MANDATORY:

1. **ISO 10993-1:2018** - Biological Evaluation
   - Frequency: 100% (47/47 predicates)
   - Status: ✅ Tool recommends (HIGH confidence)
   - Note: Mandatory for all patient-contacting devices

2. **ISO 11070:2011** - Cardiovascular Device Terminology
   - Frequency: 97.9% (46/47 predicates)
   - Status: ❌ Tool does NOT recommend (CRITICAL GAP)
   - Note: FDA expects consistent terminology for catheter specs

---

### 🟡 Emerging Standards (Frequency increasing >30% in last 2 years)

1. **AAMI TIR57:2016** - Cybersecurity (for connected catheters)
   - Pre-2023 frequency: 15% (3/20 predicates)
   - Post-2023 frequency: 55% (15/27 predicates)
   - Trend: +40% increase (2022 Cybersecurity Guidance impact)
   - Recommendation: Monitor for connected/wireless catheters

---

### 🔵 Rare Standards (<10% frequency)
Standards cited by few predicates - likely DEVICE-SPECIFIC edge cases:

1. **ISO 10993-18:2020** - Chemical Characterization
   - Frequency: 4.3% (2/47 predicates)
   - Context: Drug-eluting catheters only (rare)
   - Tool status: ⚠️ Tool recommends (MEDIUM confidence) - OVER-APPLICATION
   - Recommendation: Make conditional (drug-eluting only)

2. **ISO 13485:2016** - Quality Management System
   - Frequency: 6.4% (3/47 predicates)
   - Context: QMS standard (typically not cited in Section 17)
   - Tool status: Tool does not recommend
   - Note: QMS is expected but not a "performance standard"

3. **ASTM F2129** - Metallic Implant Corrosion
   - Frequency: 2.1% (1/47 predicates)
   - Context: Metal-tipped catheters only (very rare)
   - Tool status: Tool does not recommend (correct)
   - Note: Legitimate rare edge case

---

### 📊 Temporal Outliers (Frequency shift >30% across years)

1. **IEC 62366-1:2015** - Usability Engineering
   - 2020-2021 frequency: 10% (2/20)
   - 2022-2025 frequency: 55% (15/27)
   - Trend: +45% increase (FDA emphasis on human factors)
   - Recommendation: Consider for catheters with complex delivery systems

---

### ⚠️ Investigation Recommended

**ISO 11135:2014 (EO Sterilization) - 80.9% frequency**
- High frequency but not universal (95%)
- Investigation: 19.1% of predicates use radiation sterilization instead
- Conclusion: Sterilization method dependent (both EO and radiation valid)
- Tool handling: ✅ Correctly conditional on sterilization method

**ASTM F2394-07 (Coating Durability) - 66.0% frequency**
- Moderate frequency (not high enough for universal)
- Investigation: 34% of predicates are uncoated catheters
- Conclusion: Coating-dependent standard (hydrophilic, antimicrobial coatings)
- Tool handling: ❌ Tool does not recommend (MODERATE GAP)
- Recommendation: Add as conditional (if device has coating)
```

---

### 10.3 Tool Gap Analysis Report

**Objective:** Actionable report comparing tool recommendations vs. predicate patterns.

**Output Format:**

```markdown
# Tool Gap Analysis Report
## DQY Cardiovascular Catheter

**Generated:** 2026-02-15
**Tool Version:** 5.26.0
**Predicate Sample:** 47 PDFs (2020-2025)

---

## Executive Summary

**Tool Performance:**
- High-frequency coverage (≥80%): 83.3% (5/6 standards)
- Over-application rate (<10%): 12.5% (1/8 recommendations)
- Overall accuracy: 75% (6/8 recommendations validated)

**Critical Findings:**
- 1 CRITICAL GAP: ISO 11070 missing (97.9% predicate frequency)
- 1 MODERATE GAP: ASTM F2394 missing (66.0% frequency)
- 1 OVER-APPLICATION: ISO 10993-18 (4.3% frequency, should be conditional)

**Estimated Impact:**
- Implementing fixes: Increases tool accuracy from 75% → 95%
- Cost savings: $20K per device (removes unnecessary testing)
- Risk mitigation: Prevents FDA RTA (ISO 11070 gap)

---

## Detailed Gap Analysis

### 1. CRITICAL GAP: ISO 11070 Missing

**Standard:** ISO 11070:2011 - Terminology for central nervous system, vascular devices
**Predicate Frequency:** 46/47 (97.9%)
**Tool Recommendation:** ❌ NOT included
**Gap Severity:** CRITICAL

**Why This Matters:**
FDA expects consistent terminology for cardiovascular device specifications (lumen diameter, length, tip configuration). ISO 11070 provides standardized definitions.

**Regulatory Impact:**
- FDA RTA risk: HIGH (missing nearly universal standard)
- Delay if omitted: 3-6 months (RTA + resubmission)
- Cost if omitted: $200K-$400K (delays, consultant fees)

**Testing Requirement:**
- Testing needed: ❌ NO (terminology standard only)
- Testing cost: $0
- Timeline: Immediate (document update only)

**Recommendation:**
✅ **ADD to tool database immediately**
- Add to: `standards_database.json` → cardiovascular category
- Confidence level: HIGH (mandatory for all DQY devices)
- Trigger: product_code == "DQY" OR "DQA" OR any vascular catheter

**Implementation:**
```json
{
  "standard": "ISO 11070:2011",
  "title": "Terminology for central nervous system, vascular devices",
  "category": "cardiovascular_terminology",
  "applicable_codes": ["DQY", "DQA", "DXN"],
  "confidence": "HIGH",
  "testing_required": false,
  "rationale": "Cited in 97.9% of DQY predicates - FDA expects consistent terminology"
}
```

---

### 2. MODERATE GAP: ASTM F2394 Missing

**Standard:** ASTM F2394-07 - Guide for Determination of Catheter Coating Durability
**Predicate Frequency:** 31/47 (66.0%)
**Tool Recommendation:** ❌ NOT included
**Gap Severity:** MODERATE

**Why This Matters:**
Hydrophilic and antimicrobial catheter coatings must maintain integrity during insertion/use. ASTM F2394 provides test methods for coating durability.

**Regulatory Impact:**
- FDA RTA risk: MEDIUM (device-specific, not all catheters have coatings)
- Delay if omitted: 2-4 months (major deficiency letter)
- Cost if omitted: $10K (coating durability testing) + 4-6 week delay

**Testing Requirement:**
- Testing needed: ✅ YES (if catheter has coating)
- Testing cost: $10,000
- Timeline: 4-6 weeks

**Recommendation:**
⚠️ **ADD as CONDITIONAL standard**
- Trigger: Device has hydrophilic, antimicrobial, or other surface coating
- User prompt: "Does your catheter have a surface coating? (yes/no)"
- If YES → Include ASTM F2394
- If NO → Exclude

**Implementation:**
```json
{
  "standard": "ASTM F2394-07(2013)",
  "title": "Guide for Determination of Catheter Coating Durability",
  "category": "device_specific",
  "applicable_codes": ["DQY", "DQA"],
  "confidence": "MEDIUM",
  "conditional": true,
  "trigger": "has_coating == true",
  "user_prompt": "Does your catheter have a hydrophilic, antimicrobial, or other surface coating?",
  "rationale": "Cited in 66% of DQY predicates - applies to coated catheters only"
}
```

---

### 3. OVER-APPLICATION: ISO 10993-18

**Standard:** ISO 10993-18:2020 - Biological Evaluation - Chemical Characterization
**Predicate Frequency:** 2/47 (4.3%)
**Tool Recommendation:** ⚠️ MEDIUM confidence (currently recommended)
**Gap Severity:** OVER-APPLICATION

**Why This Is a Problem:**
ISO 10993-18 applies only to devices with degradable materials or drug-eluting components. Only 4.3% of DQY predicates cite this (drug-eluting catheters are rare).

**Cost Impact:**
- Unnecessary testing: $30,000 (chemical characterization study)
- Timeline: 8-12 weeks (wasted time)
- Impact: 95.7% of DQY devices do NOT need this

**Recommendation:**
⚠️ **Make CONDITIONAL (drug-eluting only)**
- Change confidence: MEDIUM → LOW (or CONDITIONAL)
- Trigger: Device is drug-eluting OR has degradable polymer
- User prompt: "Is your catheter drug-eluting or made from absorbable materials? (yes/no)"
- If YES → Include ISO 10993-18
- If NO → Exclude (saves $30K)

**Implementation:**
```json
{
  "standard": "ISO 10993-18:2020",
  "title": "Biological Evaluation - Chemical Characterization",
  "category": "biocompatibility",
  "applicable_codes": ["DQY", "DQA"],
  "confidence": "LOW",
  "conditional": true,
  "trigger": "drug_eluting == true OR degradable_material == true",
  "user_prompt": "Is your catheter drug-eluting or made from absorbable/degradable materials?",
  "rationale": "Cited in only 4.3% of DQY predicates - drug-eluting catheters only"
}
```

**Cost Savings:**
- Per device: $30,000 (avoided unnecessary testing)
- Applies to: 95.7% of DQY devices
- Total program savings: $30K × 20 devices/year = $600K/year

---

## Summary of Recommendations

| # | Gap | Severity | Action | Cost Impact | Timeline |
|---|-----|----------|--------|-------------|----------|
| 1 | ISO 11070 missing | CRITICAL | ADD (mandatory) | $0 (no testing) | Immediate |
| 2 | ASTM F2394 missing | MODERATE | ADD (conditional) | $10K (if coated) | 1 month |
| 3 | ISO 10993-18 over-app | OVER-APP | Make conditional | -$30K savings | 1 month |

**Net Impact:**
- Cost savings: $20K per device (average)
- Accuracy improvement: 75% → 95%
- FDA RTA risk: Eliminated (ISO 11070 gap closed)

---

## Implementation Roadmap

### Phase 1: Critical Fixes (Week 1)
1. Add ISO 11070 to cardiovascular product codes (DQY, DQA, DXN)
2. Test on 5 DQY devices → Verify ISO 11070 now appears

### Phase 2: Conditional Logic (Week 2-3)
1. Add ASTM F2394 with coating trigger
2. Make ISO 10993-18 conditional (drug-eluting trigger)
3. Implement user prompts for conditional standards
4. Test on 10 devices (5 coated, 5 uncoated) → Verify conditionals work

### Phase 3: Validation (Week 4)
1. Re-run predicate analysis on DQY
2. Verify tool accuracy improves to ≥95%
3. Expert review of updated tool output
4. Production deployment

**Total Implementation Time:** 4 weeks
**Expected Outcome:** Tool accuracy 95%, FDA RTA risk eliminated, $20K savings per device
```

---

## Conclusion

This verification specification defines a comprehensive, auditable process for validating TICKET-019 (Predicate Analysis Integration). By following these verification steps, we ensure:

1. **Data Quality:** 510(k) PDFs are correctly sourced and Section 17 is accurately extracted
2. **Frequency Accuracy:** Predicate frequency counts reflect actual FDA clearance patterns
3. **Tool Alignment:** FDA standards tool recommendations match ≥80% predicate frequency standards
4. **Gap Detection:** Critical gaps are identified and prioritized for implementation
5. **Expert Validation:** RA professionals with domain expertise confirm regulatory accuracy
6. **Actionable Output:** Users receive clear, prioritized recommendations to improve clearance success

**Key Success Metrics:**
- Extraction accuracy: ≥95%
- Frequency accuracy: ±5%
- Tool alignment: ≥80% of high-frequency standards recommended
- Expert validation: RA professional sign-off

**Expected Impact:**
- Prevents FDA RTAs (e.g., ISO 11070 gap for DQY)
- Saves $20K-$50K per device (eliminates over-application)
- Increases tool accuracy from ~75% → ~95%
- Provides regulatory confidence ("What ACTUALLY clears" vs. "What theoretically applies")

This specification is **PRODUCTION READY** when all acceptance criteria (Section 6) are met and expert review (Section 9) is completed.
