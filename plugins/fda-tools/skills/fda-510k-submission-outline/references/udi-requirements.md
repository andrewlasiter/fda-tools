# UDI System Requirements

## Overview

The Unique Device Identification (UDI) system, mandated by 21 CFR 801.20, requires most medical devices distributed in the US to carry a unique identifier on their labels and packages.

## Key Regulations

| Regulation | Title |
|-----------|-------|
| 21 CFR 801.20 | Unique device identifier (UDI) on device label |
| 21 CFR 801.30 | UDI on device packages |
| 21 CFR 801.40 | Form of UDI |
| 21 CFR 801.45 | Devices required to bear a UDI as a permanent marking |
| 21 CFR 830 | Unique Device Identification (Full regulation) |
| 21 CFR 830.300 | GUDID submission requirements |

## UDI Components

### Device Identifier (DI)
- Mandatory, fixed portion of the UDI
- Identifies the labeler and specific version/model of the device
- Does NOT change between production lots
- Recorded in the GUDID (Global Unique Device Identification Database)

### Production Identifier (PI)
- Conditional (required when present on label)
- Variable portion that identifies production details:
  - Lot or batch number
  - Serial number
  - Manufacturing date
  - Expiration date
- NOT recorded in GUDID

## UDI Carrier Types

| Type | Format | Common Use |
|------|--------|-----------|
| Linear barcode | GS1-128, HIBCC | Primary packages |
| 2D barcode | GS1 DataMatrix, HIBCC | Small devices, permanent marking |
| RFID | ISO 18000-63 | High-value implants, tracking |
| Human-readable | Plain text | Always required alongside machine-readable |

## Issuing Agencies

| Agency | Standard | Website |
|--------|----------|---------|
| GS1 | GS1 Standards (GTIN-14) | gs1.org |
| HIBCC | HIBC (Health Industry Bar Code) | hibcc.org |
| ICCBBA | ISBT 128 (blood/tissue products) | iccbba.org |

## Compliance Dates by Device Class

| Device Class | Label/Package UDI | GUDID Submission | Permanent Marking (Implants) |
|-------------|-------------------|-----------------|------------------------------|
| Class III | Sept 24, 2014 | Sept 24, 2014 | Sept 24, 2016 |
| Life-Sustaining | Sept 24, 2015 | Sept 24, 2015 | Sept 24, 2017 |
| Class II | Sept 24, 2016 | Sept 24, 2016 | Sept 24, 2018 |
| Class I | Sept 24, 2018 | Sept 24, 2018 | N/A |

## GUDID Database Structure

The GUDID contains:
- Device Identifier (DI)
- Company name and labeler DUNS number
- Brand name
- Version or model number
- Catalog number
- Device description
- Product codes
- GMDN (Global Medical Device Nomenclature) terms
- Device characteristics (sterile, single-use, MRI safety, latex, Rx/OTC)
- Device sizes and dimensions

## openFDA UDI Endpoint

Query: `https://api.fda.gov/device/udi.json`

### Key Fields

| Field | Description |
|-------|-------------|
| `company_name` | Device manufacturer/labeler |
| `brand_name` | Commercial brand name |
| `version_or_model_number` | Model identifier |
| `catalog_number` | Catalog/part number |
| `device_description` | Free-text description |
| `identifiers[].id` | DI or UDI string |
| `identifiers[].type` | "Primary" or "Package" |
| `identifiers[].issuing_agency` | GS1, HIBCC, or ICCBBA |
| `product_codes[].code` | FDA product code |
| `product_codes[].name` | Product code name |
| `gmdn_terms[].name` | GMDN preferred term |
| `mri_safety` | MR Safe / MR Conditional / MR Unsafe / N/A |
| `is_sterile` | Boolean |
| `is_single_use` | Boolean |
| `is_natural_rubber_latex` | Boolean |
| `is_rx` | Prescription device |
| `is_otc` | Over-the-counter device |
| `device_sizes[].type` | Size dimension type |
| `device_sizes[].value` | Size value |
| `device_sizes[].unit` | Size unit |

### Query Examples

```
# By product code
product_codes.code:"OVE"

# By device identifier
identifiers.id:"00888104123456"

# By company
company_name:"MEDTRONIC"

# By brand name
brand_name:"PRESTIGE"

# Combined
product_codes.code:"OVE"+AND+company_name:"MEDTRONIC"
```

## Integration Points

- `/fda:udi` — Primary UDI lookup command
- `/fda:draft labeling` — Section 9: auto-populate UDI data
- `/fda:compare-se` — Materials comparison from UDI records
- `/fda:validate` — Cross-reference device properties
