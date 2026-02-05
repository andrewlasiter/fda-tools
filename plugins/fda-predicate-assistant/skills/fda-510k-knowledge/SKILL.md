---
name: FDA 510(k) Knowledge
description: Use this skill when discussing 510(k) submissions, predicate devices, substantial equivalence, FDA clearance, K-numbers, PMA approval, De Novo pathways, product codes, or medical device classification.
version: 1.2.0
---

# FDA 510(k) Regulatory Knowledge

You have expertise in FDA medical device regulations, particularly the 510(k) premarket notification process. You also know how the local data pipeline works and where to find data.

## Data Pipeline Overview

This project uses a two-stage pipeline for FDA 510(k) predicate analysis:

### Stage 1: BatchFetch
- **Script:** `$CLAUDE_PLUGIN_ROOT/scripts/batchfetch.py`
- **Purpose:** Filter the FDA device catalog by year, product code, applicant, etc., then download 510(k) PDF documents
- **CLI flags:** `--date-range`, `--years`, `--product-codes`, `--applicants`, `--committees`, `--decision-codes`, `--output-dir`, `--download-dir`, `--data-dir`, `--save-excel`, `--no-download`, `--interactive`
- **Outputs:**
  - `510k_download.csv` — Full metadata (24 cols: KNUMBER, APPLICANT, DECISIONDATE, PRODUCTCODE, TYPE, STATEORSUMM, REVIEWADVISECOMM, THIRDPARTY, EXPEDITEDREVIEW, etc.)
  - `Applicant_ProductCode_Tables.xlsx` — Analytics workbook (3 sheets)
  - `merged_data.csv` — K-number + up to 6 predicates (7 cols)
  - Downloaded PDFs in: `DOWNLOAD_DIR/YEAR/APPLICANT/PRODUCTCODE/TYPE/`

### Stage 2: PredicateExtraction
- **Script:** `$CLAUDE_PLUGIN_ROOT/scripts/predicate_extractor.py`
- **Purpose:** Extract predicate device numbers from PDF documents using text extraction, regex parsing, and OCR error correction
- **CLI flags:** `--directory`, `--use-cache`, `--no-cache`, `--output-dir`, `--data-dir`, `--batch-size`, `--workers`
- **Outputs:**
  - `output.csv` — K-number, ProductCode, Predicate1..PredicateN, ReferenceDevice1..N
  - `supplement.csv` — Devices with supplement suffixes
  - `pdf_data.json` — Cached PDF text keyed by filename
  - `error_log.txt` — Failed PDFs

### Key Data Locations

| Data | Path |
|------|------|
| Plugin scripts | `$CLAUDE_PLUGIN_ROOT/scripts/` |
| 510kBF output | `/mnt/c/510k/Python/510kBF/` |
| PredicateExtraction output | `/mnt/c/510k/Python/PredicateExtraction/` |
| Downloaded PDFs | `/mnt/c/510k/Python/510kBF/510ks/` |
| Organized PDFs (by year) | `/mnt/c/510k/Python/PredicateExtraction/2024/`, `2025/` |
| FDA database files | `/mnt/c/510k/Python/PredicateExtraction/pmn*.txt` or configurable via `--data-dir` |
| Dependencies | `$CLAUDE_PLUGIN_ROOT/scripts/requirements.txt` |

When answering questions about specific devices, check these data sources for real information before relying solely on general knowledge.

## Core Concepts

### 510(k) Premarket Notification

A 510(k) is a premarket submission made to FDA to demonstrate that a device is **substantially equivalent** to a legally marketed device (predicate) that is not subject to premarket approval (PMA).

**Key points:**
- Required for most Class II devices and some Class I devices
- Submission must establish substantial equivalence to a predicate
- FDA has 90 days to review (standard) or 30 days (special 510(k))
- Clearance allows commercial distribution in the US

### Predicate Device

A predicate device is a legally marketed device to which a new device is compared:

**Criteria for valid predicates:**
1. Same intended use as the new device
2. Same technological characteristics, OR
3. Different technology but doesn't raise new safety/effectiveness questions

**Predicate strategies:**
- Single predicate: Most straightforward
- Multiple predicates: Different aspects from different devices
- Split predicate: Intended use from one, technology from another

### Substantial Equivalence

A device is substantially equivalent if:
1. It has the **same intended use** as the predicate, AND
2. It has the **same technological characteristics**, OR
3. Has different technological characteristics but:
   - Information demonstrates equivalent safety and effectiveness
   - Doesn't raise new questions about safety and effectiveness

### Reference Devices

Not all cited devices are predicates. Reference devices may be cited for:
- Comparison data
- Clinical study context
- State-of-the-art discussion
- But NOT for establishing substantial equivalence

## Device Classification

### Class I (Low Risk)
- General controls sufficient
- Examples: bandages, tongue depressors
- Most exempt from 510(k)

### Class II (Moderate Risk)
- General controls + special controls
- Examples: powered wheelchairs, pregnancy tests
- Most require 510(k)

### Class III (High Risk)
- General controls + PMA required
- Examples: heart valves, pacemakers
- 510(k) not applicable (usually)

## Device Numbering

### K-Numbers (510(k))
- Format: K + 6 digits (e.g., K240717)
- First 2 digits = fiscal year
- K24xxxx = cleared in FY2024

### P-Numbers (PMA)
- Format: P + 6 digits (e.g., P190001)
- Indicates PMA approval, not 510(k)

### DEN Numbers (De Novo)
- Format: DEN + 6 digits (e.g., DEN200001)
- Novel low/moderate risk devices without predicates

## Product Codes

FDA assigns 3-letter product codes indicating:
- Medical specialty (panel)
- Device type
- Regulation number

Examples:
- **DXY**: Cardiovascular diagnostic devices
- **FRN**: Dental devices
- **LYZ**: Orthopedic implants

## Common Extraction Issues

### OCR Errors
- O (letter) → 0 (zero)
- I (letter) → 1 (one)
- S → 5
- B → 8

### Document Types
- **510(k) Summary**: Public summary of submission (more detail)
- **510(k) Statement**: Brief statement (less detail, harder to extract)

### Missing Predicates
Possible causes:
- Document is a Statement (minimal detail)
- Predicates mentioned in tables/images (OCR needed)
- Non-standard document format
- Redacted information

## Resources

For detailed reference information, see:
- `references/device-classes.md` - Device classification details
- `references/predicate-types.md` - Predicate selection guidance
- `references/common-issues.md` - Troubleshooting extraction problems
