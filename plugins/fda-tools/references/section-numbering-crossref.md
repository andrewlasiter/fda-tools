# Section Numbering Cross-Reference

Maps between three different section numbering systems used in the plugin, FDA guidance, and eSTAR templates.

## Numbering Systems

| System | Source | Range | Notes |
|--------|--------|-------|-------|
| **Plugin** | Internal convention | 01-17 (+ 18 Other) | Used in export paths, draft filenames, assembler |
| **FDA Guidance** | "Recommended Content of a Traditional 510(k)" (2019) | 1-20 | Official FDA section numbering |
| **eSTAR Pages** | nIVD eSTAR v6 template | A-V (22 lettered pages) | XFA form page identifiers |

## Cross-Reference Table

| Plugin # | Plugin Section | FDA # | FDA Section | eSTAR Page | Draft File | Export Path |
|----------|---------------|-------|-------------|------------|------------|-------------|
| 01 | Cover Letter | 1 | Cover Letter | A | `draft_cover-letter.md` | `01_CoverLetter/` |
| 02 | Cover Sheet (3514) | 2 | CDRH Premarket Review Cover Sheet (Form 3514) | B | `cover_sheet.md` | `02_CoverSheet/` |
| 03 | 510(k) Summary | 3 | 510(k) Summary or Statement | C | `draft_510k-summary.md` | `03_510kSummary/` |
| 04 | Truthful & Accuracy | 4 | Truthful and Accuracy Statement | D | `draft_truthful-accuracy.md` | `04_TruthfulAccuracy/` |
| -- | (Class III Cert) | 5 | Class III Summary and Certification | -- | N/A (conditional) | N/A |
| 05 | Financial Cert | 6 | Financial Certification or Disclosure | E | `draft_financial-certification.md` | `05_FinancialCert/` |
| 08 | Standards/Conformity | 7 | Declarations of Conformity | F | `draft_doc.md` | `08_Standards/` |
| 06 | Device Description | 8 | Device Description | G | `draft_device-description.md` | `06_DeviceDescription/` |
| 07 | SE Comparison | 9 | Substantial Equivalence Comparison | H-I | `draft_se-discussion.md` | `07_SEComparison/` |
| -- | (IFU/3881) | -- | (within Labeling) | J | N/A (form) | N/A |
| 08 | Standards (cont.) | 10 | Standards and Guidance Documents | F | (same as above) | `08_Standards/` |
| 09 | Labeling | 11 | Proposed Labeling | K | `draft_labeling.md` | `09_Labeling/` |
| 10 | Sterilization | 12 | Sterilization | L | `draft_sterilization.md` | `10_Sterilization/` |
| 11 | Shelf Life | 13 | Shelf Life / Package Testing | M | `draft_shelf-life.md` | `11_ShelfLife/` |
| 12 | Biocompatibility | 14 | Biocompatibility | N | `draft_biocompatibility.md` | `12_Biocompatibility/` |
| 13 | Software/Cybersecurity | 15 | Software Documentation | O-P | `draft_software.md` | `13_Software/` |
| 14 | EMC/Electrical | 16 | EMC and Electrical Safety | Q | `draft_emc-electrical.md` | `14_EMC/` |
| 15 | Performance Testing | 17 | Performance Testing -- Non-Clinical | R | `draft_performance-summary.md` | `15_PerformanceTesting/` |
| 16 | Clinical | 18 | Performance Testing -- Clinical | S | `draft_clinical.md` | `16_Clinical/` |
| 17 | Human Factors | 19 | Human Factors / Usability | T | `draft_human-factors.md` | `17_HumanFactors/` |
| 18 | Other | 20 | Other Submission Information | U-V | N/A | `18_Other/` |

## Key Differences

### Plugin vs. FDA Numbering
- **Plugin skips FDA #5** (Class III Certification) -- rarely needed for 510(k)
- **Plugin combines FDA #7 and #10** into Plugin #08 (Standards) -- both are Declarations of Conformity
- **Plugin renumbers FDA #8-20** to fit the 01-17 scheme
- **Plugin #02** (Cover Sheet) maps to FDA Form 3514, which is FDA #2

### Plugin vs. eSTAR Pages
- eSTAR uses lettered pages (A-V), not numbered sections
- The eSTAR template combines some sections and splits others differently
- XFA field paths reference the eSTAR page letters, not plugin numbers

## Usage

- **Drafting**: Use plugin numbers (01-17) in `draft_*.md` filenames
- **Export**: The `export.md` section_map uses plugin numbers for directory names
- **FDA Correspondence**: Reference FDA guidance numbers (1-20) when communicating with FDA
- **eSTAR Import**: Use eSTAR page letters when mapping XFA fields via `estar_xml.py`
- **Assembler**: The `submission-assembler` agent uses this table for Check 11 (Section Map Alignment)
