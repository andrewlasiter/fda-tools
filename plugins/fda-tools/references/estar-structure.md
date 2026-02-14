# eSTAR Section Structure & XFA Field Mapping

Reference for eSTAR (electronic Submission Template And Resource) structure, section numbering, and XFA XML field mappings.

## eSTAR Templates

| Template | Form ID | Version | Device Types | FDA Download |
|----------|---------|---------|-------------|-------------|
| nIVD eSTAR | FDA 4062 | v6.1 | Non-IVD medical devices | `fda.gov/media/174458/download` |
| IVD eSTAR | FDA 4078 | v6.1 | In Vitro Diagnostic devices | `fda.gov/media/174459/download` |
| PreSTAR | FDA 5064 | v2.1 | Pre-Submission requests | `fda.gov/media/169327/download` |

## Template Selection Matrix

Which eSTAR template to use for each submission type and device category:

| Template | Submission Types | Device Types | OMB Control Numbers |
|----------|-----------------|-------------|---------------------|
| nIVD eSTAR v6.1 | 510(k), De Novo, PMA | Non-IVD devices | 0910-0120, 0910-0844, 0910-0231 |
| IVD eSTAR v6.1 | 510(k), De Novo, PMA | In Vitro Diagnostic devices | 0910-0120, 0910-0844, 0910-0231 |
| PreSTAR v2.1 | Pre-Submissions, IDE, 513(g) | All device types | 0910-0756, 0910-0078, 0910-0511 |

**Decision logic:** Use nIVD for non-IVD devices, IVD for in vitro diagnostics, and PreSTAR for pre-submission meetings or IDE applications regardless of device type.

## Template Differences

| Template | Form ID | Text Fields | Unique Sections |
|----------|---------|-------------|-----------------|
| nIVD v6.1 | FDA 4062 | ~265 | `QualityManagement`, `PAS`, `RiskManagement`, `PredicatesSE` |
| IVD v6.1 | FDA 4078 | ~316 | `AssayInstrumentInfo`, `AnalyticalPerformance`, `ClinicalStudies` |
| PreSTAR v2.1 | FDA 5064 | ~193 | `SubmissionCharacteristics`, `Questions`, `InvestigationalPlan`, `ClinicalInformation` |

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
  - nIVD eSTAR v6.1: `fda.gov/media/174458/download`
  - IVD eSTAR v6.1: `fda.gov/media/174459/download`
  - PreSTAR v2.1: `fda.gov/media/169327/download`
  - FDA eSTAR guidance document: `fda.gov/media/152429/download`

### Early Technical Screening
FDA performs Early Technical Screening on eSTAR submissions. If the eSTAR fails screening, a **180-day hold** is placed on the submission. Use `/fda:pre-check` to simulate FDA review before submitting.

### Submission Portal
Submit completed eSTAR packages via the **CDRH Portal**: `https://ccp.fda.gov/prweb/PRAuth/app/default/extsso`. See `references/cdrh-portal.md` for portal details, file size limits, and submission procedures.

## Real eSTAR Section Structure

> **Note:** The actual eSTAR template uses 22 lettered pages (A-V). The numbered sections below (01-17) are a **plugin convention** for organizing submission content and do not correspond to the FDA 2019 guidance 20-section format or actual eSTAR page letters. XFA field paths below are extracted from the actual FDA eSTAR templates (nIVD v6.1, IVD v6.1).

### XML Hierarchy (shared across nIVD and IVD)

```
root
├── GeneralIntroduction
├── ApplicationType
├── AdministrativeInformation
│   ├── ApplicantInformation (ADTextField210, ADTextField140, ADTextField130, ...)
│   ├── CorrespondentInformation
│   ├── Standards
│   └── RelatedSubmissions
├── DeviceDescription
│   ├── Devices → Device (TradeName, Model)
│   ├── GeneralCharacteristics
│   ├── Description (DDTextField400)
│   └── Guidance
├── IndicationsForUse
│   ├── SubandDevice (IUTextField110)
│   ├── Indications (IUTextField141)
│   ├── IntendedPopulation
│   └── TypeOfUse
├── Classification
│   ├── USAKnownClassification (DDTextField517a, DDTextField519, DDTextField518)
│   └── USAProposedClassification
├── PredicatesSE [nIVD/IVD only]
│   ├── PredicateReference (ADTextField830, ADTextField840, ADTextField850)
│   └── SubstantialEquivalence (SETextField110)
├── RiskManagement (SpecialControls) [nIVD/IVD only]
├── Labeling
│   ├── GeneralLabeling (LBTextField110)
│   ├── SpecificLabeling
│   └── Guidance
├── ReprocSter
│   ├── Reprocessing
│   ├── Sterility → STMethod (STTextField110)
│   ├── ShelfLife (SLTextField110)
│   └── Guidance
├── Biocompatibility
│   └── PatientMaterials (BCTextField110, BCTextField120, BCTextField130)
├── SoftwareCyber
│   ├── Cybersecurity
│   └── Interoperability
├── EMCWireless
│   ├── EMC (EMTextField110)
│   └── Wireless
├── PerformanceTesting
│   ├── BenchTesting (PTTextField110)
│   ├── AnimalTesting
│   ├── ClinicalTesting
│   └── Guidance
├── QualityManagement [nIVD/IVD only]
├── PAS [nIVD/IVD only]
├── References
├── AdministrativeDocumentation
│   ├── UserFee
│   ├── TAStatement (TATextField105)
│   ├── DoC (DCTextField120, DCTextField140)
│   └── PMNSummary (SSTextField110, SSTextField220, SSTextField250, SSTextField260, SSTextField400)
├── Amendment
└── Verification (metadata)
```

| # | Section | Real XML Path | Required? | Auto-Populate? |
|---|---------|---------------|-----------|----------------|
| 01 | Cover Letter | `root.AdministrativeInformation.ApplicantInformation` | Yes | Partial |
| 02 | Cover Sheet (FDA 3514) | `root.Classification.USAKnownClassification` | Yes | Template |
| 03 | 510(k) Summary or Statement | `root.AdministrativeDocumentation.PMNSummary` | Yes | Partial |
| 04 | Truthful & Accuracy Statement | `root.AdministrativeDocumentation.TAStatement` | Yes | Template |
| 05 | Financial Certification | (attachment in eSTAR) | Yes | Template |
| 06 | Device Description | `root.DeviceDescription.Description` | Yes | If data available |
| 07 | SE Comparison | `root.PredicatesSE.SubstantialEquivalence` | Yes | Yes |
| 08 | Standards/Conformity | `root.AdministrativeDocumentation.DoC` | Conditional | Partial |
| 09 | Labeling | `root.Labeling.GeneralLabeling` | Yes | If data available |
| 10 | Sterilization | `root.ReprocSter.Sterility.STMethod` | Conditional | If applicable |
| 11 | Shelf Life | `root.ReprocSter.ShelfLife` | Conditional | If applicable |
| 12 | Biocompatibility | `root.Biocompatibility.PatientMaterials` | Conditional | Partial |
| 13 | Software/Cybersecurity | `root.SoftwareCyber` | Conditional | If applicable |
| 14 | EMC/Electrical Safety | `root.EMCWireless` | Conditional | If applicable |
| 15 | Performance Testing | `root.PerformanceTesting.BenchTesting` | Yes | Partial |
| 16 | Clinical | `root.PerformanceTesting.ClinicalTesting` | Conditional | If available |
| 17 | Human Factors | (attachment/guidance section) | Conditional | If applicable |
| 18 | Other | `root.QualityManagement` / attachments | Optional | As available |

## XFA XML Field Mapping (Real eSTAR Format)

eSTAR PDFs use XFA (XML Forms Architecture) to store form data. The XFA stream is embedded in the PDF under the `/AcroForm/XFA` key. The fields below use the **real field IDs** from the official FDA templates.

### Core Identification Fields

| Real XFA Field ID | XML Section Path | Human Name | Maps To |
|-------------------|-----------------|-----------|---------|
| `ADTextField210` | `root.AdministrativeInformation.ApplicantInformation` | Company Name | `applicant_name` |
| `ADTextField140` | `root.AdministrativeInformation.ApplicantInformation` | Contact First Name | `contact_first_name` |
| `ADTextField130` | `root.AdministrativeInformation.ApplicantInformation` | Contact Last Name | `contact_last_name` |
| `ADTextField160` | `root.AdministrativeInformation.ApplicantInformation` | Email | `email` |
| `ADTextField170` | `root.AdministrativeInformation.ApplicantInformation` | Phone | `phone` |
| `ADTextField220` | `root.AdministrativeInformation.ApplicantInformation` | Address Line 1 | `address_street` |
| `ADTextField240` | `root.AdministrativeInformation.ApplicantInformation` | City | `address_city` |
| `ADTextField250` | `root.AdministrativeInformation.ApplicantInformation` | State | `address_state` |
| `ADTextField260` | `root.AdministrativeInformation.ApplicantInformation` | ZIP | `address_zip` |

### Device Description & Classification Fields

| Real XFA Field ID | XML Section Path | Human Name | Maps To |
|-------------------|-----------------|-----------|---------|
| `TradeName` | `root.DeviceDescription.Devices.Device` | Trade/Proprietary Name | `device_trade_name` |
| `Model` | `root.DeviceDescription.Devices.Device` | Model Number | `device_model` |
| `DDTextField400` | `root.DeviceDescription.Description` | Device Description Text | `device_description_text` |
| `DDTextField517a` | `root.Classification.USAKnownClassification` | Product Code | `product_code` |
| `DDTextField519` | `root.Classification.USAKnownClassification` | Regulation Number | `regulation_number` |
| `DDTextField518` | `root.Classification.USAKnownClassification` | Device Class | `device_class` |

### Indications for Use

| Real XFA Field ID | XML Section Path | Human Name | Maps To |
|-------------------|-----------------|-----------|---------|
| `IUTextField110` | `root.IndicationsForUse.SubandDevice` | Device Name on IFU | `ifu_device_name` |
| `IUTextField141` | `root.IndicationsForUse.Indications` | Indications for Use Text | `indications_for_use` |

### Predicate Information

| Real XFA Field ID | XML Section Path | Human Name | Maps To |
|-------------------|-----------------|-----------|---------|
| `ADTextField830` | `root.PredicatesSE.PredicateReference` | Primary Predicate K-Number | `predicate_k_number` |
| `ADTextField840` | `root.PredicatesSE.PredicateReference` | Primary Predicate Device Name | `predicate_device_name` |
| `ADTextField850` | `root.PredicatesSE.PredicateReference` | Primary Predicate Manufacturer | `predicate_manufacturer` |
| `SETextField110` | `root.PredicatesSE.SubstantialEquivalence` | SE Discussion Text | `se_discussion_text` |

### Sterilization, Shelf Life, and Reprocessing

| Real XFA Field ID | XML Section Path | Human Name | Maps To |
|-------------------|-----------------|-----------|---------|
| `STTextField110` | `root.ReprocSter.Sterility.STMethod` | Sterilization Method | `sterilization_method` |
| `SLTextField110` | `root.ReprocSter.ShelfLife` | Shelf Life Claim | `shelf_life_claim` |

### Biocompatibility

| Real XFA Field ID | XML Section Path | Human Name | Maps To |
|-------------------|-----------------|-----------|---------|
| `BCTextField110` | `root.Biocompatibility.PatientMaterials` | Contact Type | `biocompat_contact_type` |
| `BCTextField120` | `root.Biocompatibility.PatientMaterials` | Contact Duration | `biocompat_contact_duration` |
| `BCTextField130` | `root.Biocompatibility.PatientMaterials` | Materials | `biocompat_materials` |

### Software & EMC

| Real XFA Field ID | XML Section Path | Human Name | Maps To |
|-------------------|-----------------|-----------|---------|
| `SWTextField110` | `root.SoftwareCyber` | Software Documentation Level | `software_doc_level` |
| `EMTextField110` | `root.EMCWireless` | EMC Description | `emc_description` |

### Performance Testing

| Real XFA Field ID | XML Section Path | Human Name | Maps To |
|-------------------|-----------------|-----------|---------|
| `PTTextField110` | `root.PerformanceTesting.BenchTesting` | Performance Summary | `performance_summary` |

### Administrative Documentation (510(k) Summary, DoC, T&A)

| Real XFA Field ID | XML Section Path | Human Name | Maps To |
|-------------------|-----------------|-----------|---------|
| `SSTextField110` | `root.AdministrativeDocumentation.PMNSummary` | Summary Applicant Name | `summary_applicant_name` |
| `SSTextField220` | `root.AdministrativeDocumentation.PMNSummary` | Summary Device Trade Name | `summary_device_trade_name` |
| `SSTextField250` | `root.AdministrativeDocumentation.PMNSummary` | Summary Regulation Number | `summary_regulation_number` |
| `SSTextField260` | `root.AdministrativeDocumentation.PMNSummary` | Summary Product Codes | `summary_product_codes` |
| `SSTextField400` | `root.AdministrativeDocumentation.PMNSummary` | 510(k) Summary Text | `summary_text` |
| `TATextField105` | `root.AdministrativeDocumentation.TAStatement` | T&A Certification | `ta_certify_capacity` |
| `DCTextField120` | `root.AdministrativeDocumentation.DoC` | DoC Company Name | `doc_company_name` |
| `DCTextField140` | `root.AdministrativeDocumentation.DoC` | DoC Device Trade Name | `doc_device_trade_name` |

### IVD-Specific Fields (FDA 4078 only)

| Real XFA Field ID | XML Section Path | Human Name | Maps To |
|-------------------|-----------------|-----------|---------|
| `DDTextField340` | `root.AssayInstrumentInfo` | Instrument Name | `instrument_name` |
| `DDTextField350` | `root.AssayInstrumentInfo` | Instrument Info | `instrument_info` |
| `APTextField110` | `root.AnalyticalPerformance` | Analytical Performance | `analytical_performance` |
| `CSTextField110` | `root.ClinicalStudies` | Clinical Studies | `clinical_studies` |

### PreSTAR-Specific Fields (FDA 5064 only)

| Real XFA Field ID | XML Section Path | Human Name | Maps To |
|-------------------|-----------------|-----------|---------|
| `SCTextField110` | `root.SubmissionCharacteristics` | Submission Characteristics | `submission_characteristics` |
| `QPTextField110` | `root.Questions` | Questions for FDA | `questions_text` |

## Legacy XFA Field Mapping (form1.* format)

The legacy format was used by earlier versions of this tool before real template analysis. It uses `form1.*` paths with semantic element names. Legacy XML is still supported for import (auto-detected).

| Legacy XFA Path | Maps To |
|----------------|---------|
| `form1.CoverLetter.ApplicantName` | `applicant_name` |
| `form1.CoverLetter.ContactName` | `contact_name` |
| `form1.FDA3514.ProductCode` | `product_code` |
| `form1.FDA3881.IndicationsText` | `indications_for_use` |
| `form1.DeviceDescription.DescriptionText` | `device_description_text` |
| `form1.SE.PredicateDevice0.KNumber` | predicate K-number |
| `form1.Sterilization.Method` | `sterilization_method` |
| `form1.ShelfLife.ClaimedLife` | `shelf_life_claim` |
| `form1.Summary.SummaryText` | 510(k) summary text |

## XFA XML Extraction Process

1. Open PDF with `pikepdf`
2. Access `/Root/AcroForm/XFA` array
3. Extract the `datasets` element (contains form data XML)
4. Auto-detect template type (nIVD, IVD, PreSTAR, or legacy)
5. Parse with `BeautifulSoup` / `lxml`
6. Match field IDs to import_data.json keys using template-specific field maps
7. Write structured `import_data.json`

### XML Import Notes

- XML import is **Replace-only** (not Append) — attachments on shared pages are lost on import
- Generated XML must match the exact XFA schema of the target eSTAR template
- Attachments (test reports, images) must be added manually in Adobe Acrobat after XML import
- The `xfa:datasets` root element wraps all form data
- Real format uses `<root>` as the data container; legacy format uses `<form1>`
- Use `--format legacy` when generating XML to get the old form1.* format

## Section-to-Draft Mapping

Maps eSTAR sections to `/fda:draft` section names:

| eSTAR # | eSTAR Section | Draft Section Name | Status |
|---------|--------------|-------------------|--------|
| 01 | Cover Letter | `cover-letter` | v4.3.0 |
| 03 | 510(k) Summary | `510k-summary` | v4.6.0 |
| 04 | Truthful & Accuracy | `truthful-accuracy` | v4.6.0 |
| 05 | Financial Certification | `financial-certification` | v4.6.0 |
| 06 | Device Description | `device-description` | v4.6.0 |
| 07 | SE Comparison | `se-discussion` | v4.6.0 |
| — | Predicate Justification | `predicate-justification` | v4.6.0 |
| — | Testing Rationale | `testing-rationale` | v4.6.0 |
| 08 | Standards | (via `/fda:test-plan`) | — |
| 09 | Labeling | `labeling` | v4.3.0 |
| 10 | Sterilization | `sterilization` | v4.3.0 |
| 11 | Shelf Life | `shelf-life` | v4.3.0 |
| 12 | Biocompatibility | `biocompatibility` | v4.3.0 |
| 13 | Software | `software` | v4.3.0 |
| 14 | EMC/Electrical | `emc-electrical` | v4.3.0 |
| 15 | Performance Testing | `performance-summary` | v4.6.0 |
| 16 | Clinical | `clinical` | v4.3.0 |
| — | Declaration of Conformity | `doc` | v5.0.0 |
| — | Human Factors | `human-factors` | v5.1.0 |

## Section Number to XML Element Mapping

Used for parsing eSTAR XML and routing to correct project data fields. Shows both real and legacy paths:

| Section # | Real XML Path | Legacy XML Element | Legacy Pattern Regex |
|-----------|---------------|-------------------|---------------------|
| 01 | `root.AdministrativeInformation.ApplicantInformation` | `form1.CoverLetter` | `CoverLetter\.` |
| 02 | `root.Classification.USAKnownClassification` | `form1.FDA3514` | `FDA3514\.` |
| 03 | `root.AdministrativeDocumentation.PMNSummary` | `form1.Summary` | `Summary\.` |
| 04 | `root.AdministrativeDocumentation.TAStatement` | `form1.TruthfulAccuracy` | `TruthfulAccuracy\.` |
| 05 | (attachment) | `form1.FinancialCert` | `FinancialCert\.` |
| 06 | `root.DeviceDescription.Description` | `form1.DeviceDescription` | `DeviceDescription\.` |
| 07 | `root.PredicatesSE` | `form1.SE` | `SE\.` |
| 08 | `root.AdministrativeDocumentation.DoC` | `form1.Standards` | `Standards\.` |
| 09 | `root.Labeling.GeneralLabeling` | `form1.Labeling` | `Labeling\.` |
| 10 | `root.ReprocSter.Sterility` | `form1.Sterilization` | `Sterilization\.` |
| 11 | `root.ReprocSter.ShelfLife` | `form1.ShelfLife` | `ShelfLife\.` |
| 12 | `root.Biocompatibility.PatientMaterials` | `form1.Biocompat` | `Biocompat\.` |
| 13 | `root.SoftwareCyber` | `form1.Software` | `Software\.` |
| 14 | `root.EMCWireless` | `form1.EMC` | `EMC\.` |
| 15 | `root.PerformanceTesting.BenchTesting` | `form1.Performance` | `Performance\.` |
| 16 | `root.PerformanceTesting.ClinicalTesting` | `form1.Clinical` | `Clinical\.` |
| 17 | (attachment/guidance) | `form1.HumanFactors` | `HumanFactors\.` |
