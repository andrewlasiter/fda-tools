# FDA Enforcement Intelligence Reference

Comprehensive guide to FDA enforcement data sources for medical devices. Covers warning letters, recall enforcement, inspections, and compliance actions. Used by `/fda:warnings`, `/fda:inspections`, and `/fda:safety`.

**Last verified**: 2026-02-08

## Data Sources Overview

| Source | Data Type | Access | Auth Required |
|--------|----------|--------|--------------|
| openFDA device/enforcement | Recall enforcement reports | REST API (JSON) | No (API key optional) |
| openFDA device/recall | Recall classifications | REST API (JSON) | No (API key optional) |
| openFDA device/event | Adverse events (MAUDE) | REST API (JSON) | No (API key optional) |
| FDA Data Dashboard | Inspections, citations, compliance actions, import refusals | REST API (JSON POST) | Yes (OII registration) |
| FDA Warning Letters page | Full warning letter text | Web scraping | No |
| FDA Enforcement Reports | Weekly recall reports | openFDA API | No |

## 1. openFDA Device Enforcement API

### Base URL
```
https://api.fda.gov/device/enforcement.json
```

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `recall_number` | string | Unique recall ID (e.g., Z-1234-2025) |
| `recalling_firm` | string | Company name |
| `product_description` | string | Description of recalled product |
| `reason_for_recall` | string | Why the recall was initiated |
| `classification` | string | Class I (most serious), II, or III |
| `status` | string | Ongoing, Completed, Terminated |
| `recall_initiation_date` | string | When recall began |
| `report_date` | string | When reported to FDA |
| `distribution_pattern` | string | Where product was distributed |
| `voluntary_mandated` | string | Voluntary or Mandated |
| `product_code` | string | FDA 3-letter product code |
| `code_info` | string | Lot/serial numbers |
| `event_id` | string | Event identifier |

### Example Queries

#### By company name
```
https://api.fda.gov/device/enforcement.json?search=recalling_firm:"Medtronic"&limit=10
```

#### By product code
```
https://api.fda.gov/device/enforcement.json?search=product_code:"KGN"&limit=10
```

#### Class I recalls (most serious) in past year
```
https://api.fda.gov/device/enforcement.json?search=classification:"Class+I"+AND+report_date:[2025-01-01+TO+2026-12-31]&limit=25
```

#### By reason keyword
```
https://api.fda.gov/device/enforcement.json?search=reason_for_recall:"software"+AND+classification:"Class+I"&limit=10
```

## 2. FDA Warning Letters (Web-Based)

Warning letters are published at:
```
https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters
```

### Year-by-Year Archives
```
https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters/{YEAR}-warning-letters
```

### CDRH-Specific Warning Letters

CDRH issues ~50-60 warning letters per year for medical devices. Common patterns:

| CFR Section | Violation Area | Frequency |
|------------|---------------|-----------|
| 21 CFR 820.90 | CAPA (Corrective and Preventive Action) | ~60% |
| 21 CFR 820.30 | Design Controls | ~45% |
| 21 CFR 820.198 | Complaint Handling | ~40% |
| 21 CFR 820.184 | Device History Record | ~35% |
| 21 CFR 820.75 | Process Validation | ~30% |
| 21 CFR 820.50 | Purchasing Controls | ~25% |
| 21 CFR 820.40 | Document Controls | ~20% |
| 21 CFR 820.22 | Quality Audit | ~15% |
| 21 CFR 803 | MDR Reporting | ~15% |

*Note: With QMSR (effective Feb 2, 2026), citations are shifting from 21 CFR 820 to ISO 13485-aligned requirements. Historical citations reference 21 CFR 820; new inspections cite QMSR-aligned sections.*

### Warning Letter Structure

Typical CDRH warning letter contains:
1. **Header**: Company name, address, FEI number, date
2. **Background**: Inspection date range, facility description
3. **Observations**: Numbered FDA-483 observations cited
4. **Violations**: Specific 21 CFR sections violated with evidence
5. **Response Assessment**: FDA's evaluation of firm's response (if any)
6. **Requested Actions**: Corrective actions required
7. **Consequences**: Potential enforcement escalation

## 3. Common Enforcement Escalation Path

```
Inspection → FDA-483 → Warning Letter → Consent Decree / Injunction / Seizure
     ↓
  NAI / VAI / OAI
```

- **NAI** (No Action Indicated): Clean inspection
- **VAI** (Voluntary Action Indicated): Minor issues, firm expected to fix
- **OAI** (Official Action Indicated): Significant issues, enforcement likely
- **Warning Letter**: Formal notice of serious regulatory violations
- **Consent Decree**: Legal agreement requiring specific corrective actions
- **Injunction**: Court order to stop operations
- **Seizure**: Government takes possession of products

## 4. Risk Signals for 510(k) Submissions

When preparing a 510(k), enforcement intelligence matters because:

1. **Predicate Risk**: A predicate device from a company with recent warning letters or Class I recalls may face extra scrutiny
2. **Product Code Risk**: High enforcement activity for a product code suggests FDA is paying close attention to that device type
3. **Competitive Intelligence**: Knowing which companies have enforcement issues helps position your submission
4. **GMP Readiness**: Understanding common violations helps prepare your QMS

### Risk Scoring

| Signal | Risk Level | Action |
|--------|-----------|--------|
| Class I recall on predicate | High | Document in SE discussion, consider alternate predicate |
| Warning letter to predicate holder | Medium | Note in research, verify predicate still valid |
| OAI inspection at applicant | High | Address all observations before submission |
| MAUDE death reports for product code | High | Include safety analysis in submission |
| Class II recall on similar device | Low | Monitor, include in safety analysis if relevant |

## 5. Integration Points

| Command | Uses Enforcement Data For |
|---------|--------------------------|
| `/fda:warnings` | Primary — warning letter search and GMP violation analysis |
| `/fda:inspections` | Inspection history, compliance actions via Data Dashboard |
| `/fda:safety` | Recall + MAUDE adverse event analysis |
| `/fda:research` | Background enforcement intelligence for submission planning |
| `/fda:review` | Risk flags on predicates from companies with enforcement issues |
| `/fda:pre-check` | Simulated review includes enforcement history check |
| `/fda:lineage` | Flag ancestors with recall history |
