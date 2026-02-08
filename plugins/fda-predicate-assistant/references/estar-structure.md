# eSTAR Section Structure & XFA Field Mapping

Reference for eSTAR (electronic Submission Template And Resource) structure, section numbering, and XFA XML field mappings.

## eSTAR Templates

| Template | Version | Device Types | FDA Download |
|----------|---------|-------------|-------------|
| nIVD eSTAR | v6 | Non-IVD medical devices | `fda.gov/media/174458/download` |
| IVD eSTAR | v6 | In Vitro Diagnostic devices | `fda.gov/media/174459/download` |
| PreSTAR | v2 | Pre-Submission requests | `fda.gov/media/169327/download` |

## Template Selection Matrix

Which eSTAR template to use for each submission type and device category:

| Template | Submission Types | Device Types | OMB Control Numbers |
|----------|-----------------|-------------|---------------------|
| nIVD eSTAR v6 | 510(k), De Novo, PMA | Non-IVD devices | 0910-0120, 0910-0844, 0910-0231 |
| IVD eSTAR v6 | 510(k), De Novo, PMA | In Vitro Diagnostic devices | 0910-0120, 0910-0844, 0910-0231 |
| PreSTAR v2 | Pre-Submissions, IDE, 513(g) | All device types | 0910-0756, 0910-0078, 0910-0511 |

**Decision logic:** Use nIVD for non-IVD devices, IVD for in vitro diagnostics, and PreSTAR for pre-submission meetings or IDE applications regardless of device type.

## Mandatory eSTAR Dates

| Submission Type | eSTAR Status | Effective Date | Authority |
|----------------|-------------|----------------|-----------|
| 510(k) | **Mandatory** | October 1, 2023 | 87 FR 57910 (Sept 22, 2022) |
| De Novo | **Mandatory** | October 1, 2025 | Final guidance |
| PMA / PMA Supplement | Voluntary | — | eSTAR accepted, not required |
| Pre-Submission (Q-Sub) | Voluntary | — | PreSTAR accepted, not required |
| IDE | Voluntary | — | PreSTAR accepted, not required |

## QMSR Alignment (February 2, 2026)

As of February 2, 2026, nIVD and IVD eSTAR templates (v6) align with the new Quality Management System Regulation (QMSR), which replaced the current Good Manufacturing Practice (cGMP/QSR) requirements. PMA applicants using older eSTAR versions should attach QMS documentation in the "Other Quality System Information" section. Download the latest template versions to ensure QMSR alignment.

## Technical Requirements

### Software
- **Adobe Acrobat Pro 2017 or later** (primary supported platform)
- 64-bit operating system recommended for performance with large eSTAR files
- Disable Protected Mode in Acrobat if experiencing slowness

### File Preparation
- Compress images to JPEG format to reduce file size
- Compress videos to AVC or HEVC MP4 format
- **Do not set PDF passwords** — passwords block FDA's redaction workflow
- Combine similar attachments into single PDFs with bookmarks and table of contents
- Built-in eSTAR forms replace separate FDA Forms 3881, 3514, and 510(k) Summary forms

### Downloading Templates
- **Right-click the download link → "Save Link As"** (browser-specific wording)
- Save the file before opening in Acrobat — eSTAR PDFs cannot be opened directly in web browsers
- Download URLs:
  - nIVD eSTAR v6: `fda.gov/media/174458/download`
  - IVD eSTAR v6: `fda.gov/media/174459/download`
  - PreSTAR v2: `fda.gov/media/169327/download`
  - FDA eSTAR guidance document: `fda.gov/media/152429/download`

### Early Technical Screening
FDA performs Early Technical Screening on eSTAR submissions. If the eSTAR fails screening, a **180-day hold** is placed on the submission. Use `/fda:pre-check` to simulate FDA review before submitting.

### Submission Portal
Submit completed eSTAR packages via the **CDRH Portal**: `https://ccp.fda.gov/prweb/PRAuth/app/default/extsso`. See `references/cdrh-portal.md` for portal details, file size limits, and submission procedures.

## eSTAR Section Structure (nIVD v6)

> **Note:** The actual eSTAR template uses 22 lettered pages (A-V). The numbered sections below (01-17) are a **plugin convention** for organizing submission content and do not correspond to the FDA 2019 guidance 20-section format or actual eSTAR page letters. XFA field paths are derived from observed template structures and may vary across eSTAR versions.

| # | Section | eSTAR Tab/Page | Required? | Auto-Populate? |
|---|---------|----------------|-----------|----------------|
| 01 | Cover Letter | Cover Letter | Yes | Partial |
| 02 | Cover Sheet (FDA 3514) | Indications for Use | Yes | Template |
| 03 | 510(k) Summary or Statement | 510(k) Summary | Yes | Partial |
| 04 | Truthful & Accuracy Statement | Truthful and Accuracy | Yes | Template |
| 05 | Financial Certification | Financial Certification | Yes | Template |
| 06 | Device Description | Device Description | Yes | If data available |
| 07 | SE Comparison | Substantial Equivalence | Yes | Yes |
| 08 | Standards/Conformity | Standards | Conditional | Partial |
| 09 | Labeling | Labeling | Yes | If data available |
| 10 | Sterilization | Sterilization | Conditional | If applicable |
| 11 | Shelf Life | Shelf Life | Conditional | If applicable |
| 12 | Biocompatibility | Biocompatibility | Conditional | Partial |
| 13 | Software/Cybersecurity | Software | Conditional | If applicable |
| 14 | EMC/Electrical Safety | EMC/Electrical | Conditional | If applicable |
| 15 | Performance Testing | Performance Testing | Yes | Partial |
| 16 | Clinical | Clinical | Conditional | If available |
| 17 | Other | Additional Information | Optional | As available |

## XFA XML Field Mapping

eSTAR PDFs use XFA (XML Forms Architecture) to store form data. The XFA stream is embedded in the PDF under the `/AcroForm/XFA` key.

### Core Identification Fields

| XFA Field Path | Human Name | Maps To |
|----------------|-----------|---------|
| `form1.CoverLetter.ApplicantName` | Applicant/Company Name | `applicant_name` |
| `form1.CoverLetter.ContactName` | Contact Person | `contact_name` |
| `form1.CoverLetter.Address` | Company Address | `address` |
| `form1.CoverLetter.Phone` | Phone Number | `phone` |
| `form1.CoverLetter.Email` | Email Address | `email` |
| `form1.CoverLetter.Date` | Submission Date | `submission_date` |
| `form1.CoverLetter.DeviceName` | Trade/Proprietary Name | `device_trade_name` |
| `form1.CoverLetter.CommonName` | Common/Usual Name | `device_common_name` |

### Classification Fields

| XFA Field Path | Human Name | Maps To |
|----------------|-----------|---------|
| `form1.FDA3514.ProductCode` | Product Code | `product_code` |
| `form1.FDA3514.RegulationNumber` | Regulation Number | `regulation_number` |
| `form1.FDA3514.DeviceClass` | Device Class | `device_class` |
| `form1.FDA3514.Panel` | Review Panel | `review_panel` |
| `form1.FDA3514.SubmissionType` | 510(k) Type | `submission_type` |

### Indications for Use (FDA 3881)

| XFA Field Path | Human Name | Maps To |
|----------------|-----------|---------|
| `form1.FDA3881.DeviceName` | Device Name | `ifu_device_name` |
| `form1.FDA3881.IndicationsText` | Indications for Use Text | `indications_for_use` |
| `form1.FDA3881.Prescription` | Rx/OTC | `prescription_otc` |

### Predicate Information

| XFA Field Path | Human Name | Maps To |
|----------------|-----------|---------|
| `form1.SE.PredicateDevice[0].KNumber` | Primary Predicate K-Number | `predicates[0].k_number` |
| `form1.SE.PredicateDevice[0].DeviceName` | Primary Predicate Name | `predicates[0].device_name` |
| `form1.SE.PredicateDevice[0].Manufacturer` | Primary Predicate Manufacturer | `predicates[0].manufacturer` |
| `form1.SE.PredicateDevice[1].KNumber` | Secondary Predicate K-Number | `predicates[1].k_number` |
| `form1.SE.PredicateDevice[1].DeviceName` | Secondary Predicate Name | `predicates[1].device_name` |

### Section Content Fields

| XFA Field Path | Human Name | Maps To |
|----------------|-----------|---------|
| `form1.DeviceDescription.DescriptionText` | Device Description Narrative | `device_description_text` |
| `form1.DeviceDescription.PrincipleOfOperation` | Principle of Operation | `principle_of_operation` |
| `form1.SE.ComparisonNarrative` | SE Discussion Narrative | `se_discussion_text` |
| `form1.SE.IntendedUseComparison` | Intended Use Comparison | `intended_use_comparison` |
| `form1.SE.TechCharComparison` | Tech Characteristics Comparison | `tech_comparison` |
| `form1.Performance.TestingSummary` | Performance Testing Summary | `performance_summary` |
| `form1.Labeling.IFUText` | Instructions for Use | `ifu_text` |
| `form1.Software.SoftwareLevel` | Software Level of Documentation | `software_doc_level` |
| `form1.Sterilization.Method` | Sterilization Method | `sterilization_method` |
| `form1.ShelfLife.ClaimedLife` | Claimed Shelf Life | `shelf_life_claim` |

### Biocompatibility Fields

| XFA Field Path | Human Name | Maps To |
|----------------|-----------|---------|
| `form1.Biocompat.ContactType` | Patient Contact Type | `biocompat_contact_type` |
| `form1.Biocompat.ContactDuration` | Contact Duration | `biocompat_contact_duration` |
| `form1.Biocompat.MaterialList` | Materials of Construction | `biocompat_materials` |

## XFA XML Extraction Process

1. Open PDF with `pikepdf`
2. Access `/Root/AcroForm/XFA` array
3. Extract the `datasets` element (contains form data XML)
4. Parse with `BeautifulSoup` / `lxml`
5. Navigate field paths to extract values
6. Map to structured `import_data.json`

### XML Import Notes

- XML import is **Replace-only** (not Append) — attachments on shared pages are lost on import
- Generated XML must match the exact XFA schema of the target eSTAR template
- Attachments (test reports, images) must be added manually in Adobe Acrobat after XML import
- The `xfa:datasets` root element wraps all form data

## Section-to-Draft Mapping

Maps eSTAR sections to `/fda:draft` section names:

| eSTAR # | eSTAR Section | Draft Section Name | Status |
|---------|--------------|-------------------|--------|
| 01 | Cover Letter | `cover-letter` | v4.3.0 |
| 03 | 510(k) Summary | `510k-summary` | v4.6.0 |
| 06 | Device Description | `device-description` | v4.6.0 |
| 07 | SE Comparison | `se-discussion` | v4.6.0 |
| 08 | Standards | (via `/fda:test-plan`) | — |
| 09 | Labeling | `labeling` | v4.3.0 |
| 10 | Sterilization | `sterilization` | v4.3.0 |
| 11 | Shelf Life | `shelf-life` | v4.3.0 |
| 12 | Biocompatibility | `biocompatibility` | v4.3.0 |
| 13 | Software | `software` | v4.3.0 |
| 14 | EMC/Electrical | `emc-electrical` | v4.3.0 |
| 15 | Performance Testing | `performance-summary` | v4.6.0 |
| 16 | Clinical | `clinical` | v4.3.0 |

## Section Number to XML Element Mapping

Used for parsing eSTAR XML and routing to correct project data fields:

| Section # | XML Element Root | Pattern Regex |
|-----------|-----------------|---------------|
| 01 | `form1.CoverLetter` | `CoverLetter\\.` |
| 02 | `form1.FDA3514` | `FDA3514\\.` |
| 03 | `form1.Summary` | `Summary\\.` |
| 04 | `form1.TruthfulAccuracy` | `TruthfulAccuracy\\.` |
| 06 | `form1.DeviceDescription` | `DeviceDescription\\.` |
| 07 | `form1.SE` | `SE\\.` |
| 08 | `form1.Standards` | `Standards\\.` |
| 09 | `form1.Labeling` | `Labeling\\.` |
| 10 | `form1.Sterilization` | `Sterilization\\.` |
| 11 | `form1.ShelfLife` | `ShelfLife\\.` |
| 12 | `form1.Biocompat` | `Biocompat\\.` |
| 13 | `form1.Software` | `Software\\.` |
| 14 | `form1.EMC` | `EMC\\.` |
| 15 | `form1.Performance` | `Performance\\.` |
| 16 | `form1.Clinical` | `Clinical\\.` |
