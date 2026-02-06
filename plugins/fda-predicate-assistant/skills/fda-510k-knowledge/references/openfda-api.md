# openFDA Device API Reference

Centralized reference for the primary openFDA Device API endpoints. All commands should use this as the single source of truth for API queries. Note: openFDA provides 9 device endpoints total (the 7 documented below plus `/device/enforcement` for enforcement reports and `/device/covid19serology` for COVID-19 serology tests); only the 7 most relevant to 510(k) predicate work are covered here.

## Base Configuration

- **Base URL**: `https://api.fda.gov/device/`
- **Auth**: Optional API key as query param `?api_key=KEY`
- **Rate Limits**:
  - Without key: 240 requests/minute, 1,000/day
  - With key: 240 requests/minute, 120,000/day
- **Response format**: JSON

## Settings Integration

Commands should read API settings from `~/.claude/fda-predicate-assistant.local.md`:

```yaml
openfda_api_key: null       # Optional API key for higher rate limits
openfda_enabled: true       # Set to false for offline-only mode
```

**Check before every API call:**
```python
# Read API key: environment variable takes priority (never enters chat),
# then fall back to settings file, then no key (lower rate limit)
import os, re
settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')  # Env var takes priority (never enters chat)
api_enabled = True
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:  # Only check file if env var not set
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)
    m = re.search(r'openfda_enabled:\s*(\S+)', content)
    if m and m.group(1).lower() == 'false':
        api_enabled = False
```

## Reusable Python Query Template

All commands should use this pattern — stdlib only, no external dependencies:

```python
import urllib.request, urllib.parse, json, os, re

def fda_api(endpoint, search, limit=10, count_field=None):
    """Query an openFDA Device API endpoint.

    Args:
        endpoint: One of: 510k, classification, event, recall, pma, registrationlisting, udi
        search: Search query string (e.g., 'k_number:"K241335"')
        limit: Max results (1-1000, default 10)
        count_field: If set, return counts grouped by this field instead of results

    Returns:
        dict with 'results' list or 'error' string
    """
    # Read settings — env var takes priority (never enters chat)
    settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
    api_key = os.environ.get('OPENFDA_API_KEY')
    api_enabled = True
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            content = f.read()
        if not api_key:
            m = re.search(r'openfda_api_key:\s*(\S+)', content)
            if m and m.group(1) != 'null':
                api_key = m.group(1)
        m = re.search(r'openfda_enabled:\s*(\S+)', content)
        if m and m.group(1).lower() == 'false':
            api_enabled = False

    if not api_enabled:
        return {"error": "openFDA API disabled (openfda_enabled: false)"}

    # Build URL
    params = {"search": search, "limit": str(limit)}
    if count_field:
        params["count"] = count_field
    if api_key:
        params["api_key"] = api_key

    url = f"https://api.fda.gov/device/{endpoint}.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"error": "No results found", "status": 404}
        elif e.code == 429:
            return {"error": "Rate limit exceeded — wait 60 seconds or add API key", "status": 429}
        else:
            return {"error": f"HTTP {e.code}: {e.reason}", "status": e.code}
    except urllib.error.URLError as e:
        return {"error": f"Network error: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}
```

## Device Number to Endpoint Routing

When validating or looking up a device number, route to the correct endpoint based on the number prefix:

| Device Number Type | Format | API Endpoint | Search Field | Notes |
|--------------------|--------|-------------|--------------|-------|
| **K-numbers** (510(k)) | K + 6 digits | `/device/510k` | `k_number` | Primary path |
| **P-numbers** (PMA) | P + 6 digits | `/device/pma` | `pma_number` | Class III devices |
| **DEN numbers** (De Novo) | DEN + 6 digits | `/device/510k` | `k_number` | Some indexed here; no dedicated De Novo endpoint |
| **N-numbers** (Pre-Amendments) | N + 4-5 digits | *Not in openFDA* | — | Use flat files (pmn*.txt) only |

**Pattern for routing in code:**
```python
number_upper = device_number.upper()
if number_upper.startswith('P'):
    endpoint, field = "pma", "pma_number"
elif number_upper.startswith('DEN'):
    endpoint, field = "510k", "k_number"  # some DEN numbers indexed here
elif number_upper.startswith('K'):
    endpoint, field = "510k", "k_number"
else:  # N-numbers
    # Skip API — use flat file lookup only
```

## Primary Endpoints Reference (7 of 9 total)

### 1. `/device/510k` — 510(k) Clearances

**Purpose**: Look up 510(k) clearance records (same data as pmn*.txt flat files but real-time).

**Key searchable fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `k_number` | 510(k) number | `k_number:"K241335"` |
| `applicant` | Company name | `applicant:"MEDTRONIC"` |
| `contact` | Contact person | `contact:"SMITH"` |
| `product_code` | 3-letter code | `product_code:"KGN"` |
| `device_name` | Device name | `device_name:"wound+dressing"` |
| `decision_date` | Clearance date (YYYYMMDD) | `decision_date:[20200101+TO+20251231]` |
| `decision_code` | SESE, SEKN, etc. | `decision_code:"SESE"` |
| `decision_description` | Decision text | `decision_description:"Substantially+Equivalent"` |
| `date_received` | Submission received date (YYYYMMDD) | `date_received:[20240101+TO+20241231]` |
| `advisory_committee` | Review panel code | `advisory_committee:"SU"` |
| `review_advisory_committee` | Review committee (may differ from advisory_committee) | |
| `clearance_type` | Traditional, Special, etc. | `clearance_type:"Traditional"` |
| `third_party_flag` | Third party review flag | `third_party_flag:"Y"` |
| `expedited_review_flag` | Expedited review | `expedited_review_flag:"Y"` |
| `statement_or_summary` | Summary or Statement | `statement_or_summary:"Summary"` |
| `address_1` | Street address | |
| `city` | City | `city:"MINNEAPOLIS"` |
| `state` | State | `state:"MN"` |
| `country_code` | Country | `country_code:"US"` |
| `zip_code` | Zip code | |
| `postal_code` | Postal code (alias for zip_code) | |

**Response fields** (per result):
- `k_number`, `applicant`, `contact`, `address_1`, `address_2`, `city`, `state`, `zip_code`, `postal_code`, `country_code`
- `date_received`, `decision_date`, `decision_code`, `decision_description`
- `product_code`, `device_name`, `clearance_type`, `advisory_committee`, `advisory_committee_description`, `review_advisory_committee`
- `third_party_flag`, `expedited_review_flag`, `statement_or_summary`
- `openfda.device_name`, `openfda.device_class`, `openfda.regulation_number`

**Common queries**:
```python
# Look up a specific K-number
fda_api("510k", 'k_number:"K241335"')

# All clearances for a product code in a year range
fda_api("510k", 'product_code:"KGN"+AND+decision_date:[20200101+TO+20251231]', limit=100)

# Count clearances by product code
fda_api("510k", 'decision_date:[20200101+TO+20251231]', count_field="product_code.exact")

# Search by applicant
fda_api("510k", 'applicant:"DEXCOM"+AND+product_code:"QBJ"', limit=50)
```

### 2. `/device/classification` — Device Classification

**Purpose**: Look up FDA device classification, regulation numbers, device class.

**Key searchable fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `product_code` | 3-letter code | `product_code:"KGN"` |
| `device_name` | Classification name | `device_name:"wound+dressing"` |
| `device_class` | 1, 2, or 3 | `device_class:"2"` |
| `regulation_number` | CFR regulation | `regulation_number:"878.4018"` |
| `review_panel` | Advisory panel | `review_panel:"SU"` |
| `medical_specialty` | Specialty area | `medical_specialty:"SU"` |
| `implant_flag` | Whether device is an implant | `implant_flag:"Y"` |
| `life_sustain_support_flag` | Life-sustaining/supporting device | `life_sustain_support_flag:"Y"` |
| `gmp_exempt_flag` | GMP exemption | `gmp_exempt_flag:"N"` |
| `third_party_flag` | Third-party review eligible | `third_party_flag:"Y"` |
| `submission_type_id` | Submission type | |
| `review_code` | Review code | |
| `summary_malfunction_reporting` | Summary malfunction reporting eligibility | |
| `unclassified_reason` | Reason for unclassified status | |

**Response fields**:
- `product_code`, `device_name`, `device_class`, `regulation_number`
- `review_panel`, `medical_specialty`, `medical_specialty_description`
- `definition`, `submission_type_id`, `gmp_exempt_flag`, `third_party_flag`
- `implant_flag`, `life_sustain_support_flag`, `review_code`
- `summary_malfunction_reporting`, `unclassified_reason`
- `openfda.regulation_number`, `openfda.device_name`, `openfda.device_class`

**Common queries**:
```python
# Look up a product code
fda_api("classification", 'product_code:"KGN"')

# Search by keyword
fda_api("classification", 'device_name:"glucose+monitor"', limit=20)

# Find all Class III devices in a specialty
fda_api("classification", 'device_class:"3"+AND+medical_specialty:"CV"', limit=50)

# Find all implantable devices in a specialty
fda_api("classification", 'implant_flag:"Y"+AND+medical_specialty:"OR"', limit=50)
```

### 3. `/device/event` — MAUDE Adverse Events

**Purpose**: Search the MAUDE (Manufacturer and User Facility Device Experience) database for adverse event reports.

**Key searchable fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `device.generic_name` | Device generic name | `device.generic_name:"wound+dressing"` |
| `device.brand_name` | Brand/trade name | `device.brand_name:"ACME+DRESSING"` |
| `device.device_report_product_code` | Product code | `device.device_report_product_code:"KGN"` |
| `device.manufacturer_d_name` | Manufacturer | `device.manufacturer_d_name:"MEDTRONIC"` |
| `event_type` | Injury/Malfunction/Death | `event_type:"Injury"` |
| `date_received` | FDA received date | `date_received:[20200101+TO+20251231]` |
| `date_of_event` | When event occurred | `date_of_event:[20240101+TO+20241231]` |
| `date_report` | Report date | |
| `report_number` | MDR report number | `report_number:"1234567-2024-00001"` |
| `mdr_text.text` | MDR narrative text | `mdr_text.text:"infection"` |
| `adverse_event_flag` | Adverse event indicator | `adverse_event_flag:"Y"` |
| `product_problem_flag` | Product problem indicator | `product_problem_flag:"Y"` |
| `event_location` | Where event occurred | `event_location:"HOSPITAL"` |
| `health_professional` | Reported by HCP | `health_professional:"Y"` |
| `reporter_occupation_code` | Reporter type | |
| `report_source_code` | Source (manufacturer/user facility/voluntary) | `report_source_code:"Manufacturer report"` |
| `manufacturer_name` | Manufacturer name | `manufacturer_name:"MEDTRONIC"` |
| `single_use_flag` | Single-use device | `single_use_flag:"Y"` |
| `reprocessed_and_reused_flag` | Reprocessed device | `reprocessed_and_reused_flag:"Y"` |
| `number_devices_in_event` | Device count | |
| `number_patients_in_event` | Patient count | |
| `device.openfda.device_name` | FDA device name | |

**Response fields** (organized by group):

*Report metadata*:
- `mdr_report_key`, `report_number`, `event_type`
- `date_received`, `date_of_event`, `date_report`, `date_report_to_fda`, `date_report_to_manufacturer`, `date_facility_aware`
- `report_source_code`, `type_of_report[]`, `source_type[]`
- `health_professional`, `reporter_occupation_code`
- `initial_report_to_fda`, `report_to_fda`, `report_to_manufacturer`

*Event details*:
- `adverse_event_flag`, `product_problem_flag`, `event_location`
- `number_devices_in_event`, `number_patients_in_event`
- `previous_use_code`, `single_use_flag`, `reprocessed_and_reused_flag`
- `removal_correction_number`, `product_problems[]`
- `remedial_action[]`

*Device info*:
- `device[].generic_name`, `device[].brand_name`, `device[].product_code`
- `device[].manufacturer_d_name`, `device[].device_operator`, `device[].device_availability`
- `device[].device_report_product_code`, `device[].device_age_text`
- `device[].device_evaluated_by_manufacturer`, `device[].implant_flag`
- `device[].lot_number`, `device[].model_number`, `device[].catalog_number`
- `device[].expiration_date_of_device`, `device[].device_sequence_number`
- `device[].date_removed_flag`, `device[].date_received`

*Narrative text*:
- `mdr_text[].text`, `mdr_text[].text_type_code` (Description, Patient, Additional Manufacturer Narrative)

*Patient*:
- `patient[].patient_sequence_number`, `patient[].date_received`, `patient[].sequence_number_outcome`

*Manufacturer details*:
- `manufacturer_name`, `manufacturer_address_1`, `manufacturer_address_2`
- `manufacturer_city`, `manufacturer_state`, `manufacturer_country`
- `manufacturer_postal_code`, `manufacturer_zip_code`
- `manufacturer_g1_name`, `manufacturer_g1_address_1`, `manufacturer_g1_city`, `manufacturer_g1_state`, `manufacturer_g1_zip_code`, `manufacturer_g1_country`
- `manufacturer_contact_t_name`, `manufacturer_contact_address_1`, `manufacturer_contact_city`, `manufacturer_contact_state`, `manufacturer_contact_zip_code`, `manufacturer_contact_country`, `manufacturer_contact_phone_number`

*Distributor*:
- `distributor_name`, `distributor_address_1`, `distributor_address_2`
- `distributor_city`, `distributor_state`, `distributor_zip_code`

**Useful count fields**: `product_problems.exact`, `report_source_code.exact`, `event_type.exact`, `device.manufacturer_d_name.exact`, `date_received`

**Common queries**:
```python
# Count events by type for a product code
fda_api("event", 'device.device_report_product_code:"KGN"', count_field="event_type.exact")

# Recent adverse events for a product code
fda_api("event", 'device.device_report_product_code:"KGN"+AND+date_received:[20230101+TO+20251231]', limit=25)

# Search narrative text for specific issues
fda_api("event", 'device.device_report_product_code:"KGN"+AND+mdr_text.text:"infection"', limit=10)

# Count events by year
fda_api("event", 'device.device_report_product_code:"KGN"', count_field="date_received")

# What problems are reported for this product code?
fda_api("event", 'device.device_report_product_code:"KGN"', count_field="product_problems.exact")
```

### 4. `/device/recall` — Device Recalls

**Purpose**: Search FDA device recall data — recall class, reason, status, affected products.

**Key searchable fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `product_code` | Product code | `product_code:"KGN"` |
| `k_number` | Associated 510(k) (single string) | `k_number:"K241335"` |
| `k_numbers` | Associated 510(k) numbers (array — note plural) | |
| `pma_numbers` | Associated PMA numbers (array) | |
| `recalling_firm` | Company name | `recalling_firm:"MEDTRONIC"` |
| `res_event_number` | Recall event ID | `res_event_number:"Z-1234-2024"` |
| `cfres_id` | Unique recall record ID | |
| `firm_fei_number` | Firm FEI number | `firm_fei_number:"1234567"` |
| `event_date_initiated` | Recall start date | `event_date_initiated:[20200101+TO+20251231]` |
| `event_date_created` | Record creation date | |
| `event_date_posted` | Public posting date | |
| `event_date_terminated` | Recall termination date | |
| `product_description` | Product description | `product_description:"wound+dressing"` |
| `reason_for_recall` | Recall reason text | `reason_for_recall:"sterility"` |
| `root_cause_description` | Root cause of recall | `root_cause_description:"software"` |
| `recall_status` | Recall status | `recall_status:"Ongoing"` |
| `classification` | Recall severity class (I/II/III) | `classification:"Class+I"` |
| `action` | Required corrective action | |
| `product_res_number` | Product resolution number | |
| `other_submission_description` | Other submission info | |
| `additional_info_contact` | Contact information | |
| `address_1`, `address_2` | Firm street address | |
| `city`, `state`, `postal_code`, `country` | Firm location | |
| `openfda.device_name` | Device name | |
| `openfda.device_class` | Device class | |

> **Note**: The recall API uses `k_numbers` (plural, array) for associated clearances, not `k_number` (singular string) like the 510k endpoint. Both may appear in results.

**Response fields**:
- `res_event_number`, `cfres_id`, `product_res_number`
- `event_date_initiated`, `event_date_created`, `event_date_posted`, `event_date_terminated`
- `recall_status` (Ongoing, Completed, Terminated) — NOTE: `classification` (Class I/II/III recall severity) is in `/device/enforcement`, NOT `/device/recall`
- `product_description`, `code_info`, `reason_for_recall`, `root_cause_description`
- `recalling_firm`, `firm_fei_number`, `address_1`, `address_2`, `city`, `state`, `postal_code`, `country`
- `additional_info_contact`, `action`
- `product_quantity`, `distribution_pattern`, `voluntary_mandated`
- `k_numbers[]`, `pma_numbers[]`, `product_code` (note: no singular `k_number` in recall API)
- `other_submission_description`
- `openfda.device_name`, `openfda.device_class`, `openfda.regulation_number`

**Common queries**:
```python
# Recalls for a specific K-number (note: recall API uses k_numbers plural)
fda_api("recall", 'k_numbers:"K241335"')

# Recalls for a product code
fda_api("recall", 'product_code:"KGN"', limit=50)

# Count recalls by status
fda_api("recall", 'product_code:"KGN"', count_field="recall_status")

# Active recalls only
fda_api("recall", 'product_code:"KGN"+AND+recall_status:"Ongoing"')

# Root causes for recalls in this product code
fda_api("recall", 'product_code:"KGN"', count_field="root_cause_description.exact")
```

### 5. `/device/pma` — Premarket Approvals

**Purpose**: Look up PMA (Premarket Approval) records for Class III devices.

**Key searchable fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `pma_number` | PMA number | `pma_number:"P190001"` |
| `applicant` | Company name | `applicant:"MEDTRONIC"` |
| `product_code` | Product code | `product_code:"DXY"` |
| `generic_name` | Device generic name | `generic_name:"pacemaker"` |
| `trade_name` | Commercial/trade name | `trade_name:"COREVALVE"` |
| `decision_date` | Approval date | `decision_date:[20200101+TO+20251231]` |
| `decision_code` | Decision code | `decision_code:"APPR"` |
| `date_received` | Submission date | `date_received:[20200101+TO+20251231]` |
| `advisory_committee` | Review panel | `advisory_committee:"CV"` |
| `docket_number` | FDA docket number | |
| `ao_statement` | Advisory Opinion statement | |
| `fed_reg_notice_date` | Federal Register notice date | |
| `expedited_review_flag` | Expedited review | `expedited_review_flag:"Y"` |
| `supplement_number` | Supplement number | |
| `supplement_type` | Supplement type | |
| `street_1` | Address (NOT `address_1` — PMA uses different naming) | |
| `city` | City | |
| `state` | State | |
| `zip`, `zip_ext` | Zip code (NOT `zip_code` — PMA uses different naming) | |

> **Note**: PMA address fields use `street_1`/`street_2` and `zip`/`zip_ext`, NOT `address_1`/`address_2` and `zip_code` like 510(k). This is an API inconsistency.

**Response fields**:
- `pma_number`, `supplement_number`, `supplement_type`, `supplement_reason`
- `applicant`, `street_1`, `street_2`, `city`, `state`, `zip`, `zip_ext`
- `decision_date`, `decision_code`, `date_received`
- `product_code`, `generic_name`, `trade_name`
- `advisory_committee`, `advisory_committee_description`
- `docket_number`, `ao_statement`, `fed_reg_notice_date`
- `expedited_review_flag`
- `openfda.device_name`, `openfda.device_class`, `openfda.regulation_number`

**Common queries**:
```python
# Look up a PMA
fda_api("pma", 'pma_number:"P190001"')

# PMAs for a product code
fda_api("pma", 'product_code:"DXY"', limit=50)

# Search by trade name
fda_api("pma", 'trade_name:"COREVALVE"', limit=10)
```

### 6. `/device/registrationlisting` — Establishment Registration & Listing

**Purpose**: Find registered medical device establishments and their listed devices.

**Key searchable fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `registration.name` | Facility name | `registration.name:"MEDTRONIC"` |
| `registration.fei_number` | FEI number | `registration.fei_number:"1234567"` |
| `registration.registration_number` | Registration number | |
| `registration.status_code` | Active/inactive status | `registration.status_code:"1"` |
| `registration.iso_country_code` | Country | `registration.iso_country_code:"US"` |
| `registration.owner_operator.firm_name` | Owner/operator | |
| `registration.owner_operator.official_correspondent.firm_name` | Correspondent | |
| `products.product_code` | Product code | `products.product_code:"KGN"` |
| `products.k_number` | Associated 510(k) | `products.k_number:"K241335"` |
| `products.pma_number` | Associated PMA | |
| `products.created_date` | Listing creation date | |
| `establishment_type` | Facility type (array) | |
| `proprietary_name` | Proprietary/brand names (array) | |
| `k_number` | K-number (top-level alias) | |
| `pma_number` | PMA number (top-level alias) | |

**Response fields** (organized by group):

*Registration*:
- `registration.name`, `registration.fei_number`, `registration.registration_number`
- `registration.status_code`, `registration.initial_importer_flag`
- `registration.iso_country_code`, `registration.city`, `registration.state_code`
- `registration.address_line_1`, `registration.address_line_2`
- `registration.zip_code`, `registration.postal_code`

*Owner/operator*:
- `registration.owner_operator.firm_name`, `registration.owner_operator.owner_operator_number`
- `registration.owner_operator.contact_address.address_1`, `registration.owner_operator.contact_address.address_2`
- `registration.owner_operator.contact_address.city`, `registration.owner_operator.contact_address.state_code`
- `registration.owner_operator.contact_address.zip_code`, `registration.owner_operator.contact_address.iso_country_code`
- `registration.owner_operator.official_correspondent.firm_name`

*Products*:
- `products[].product_code`, `products[].k_number`, `products[].pma_number`
- `products[].created_date`, `products[].exempt`
- `products[].openfda.device_name`, `products[].openfda.device_class`, `products[].openfda.regulation_number`

*Other*:
- `establishment_type[]`, `proprietary_name[]`

### 7. `/device/udi` — Unique Device Identification

**Purpose**: Look up UDI (Unique Device Identification) records for specific devices.

**Key searchable fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `identifiers.id` | UDI-DI or GTIN | `identifiers.id:"00888104123456"` |
| `brand_name` | Brand name | `brand_name:"ACME+DRESSING"` |
| `company_name` | Company | `company_name:"MEDTRONIC"` |
| `product_codes.code` | Product code | `product_codes.code:"KGN"` |
| `version_or_model_number` | Model number | |
| `catalog_number` | Catalog number | |
| `device_description` | Full device description | `device_description:"wound+dressing"` |
| `is_single_use` | Single-use device | `is_single_use:true` |
| `is_rx` | Prescription required | `is_rx:true` |
| `is_otc` | Over-the-counter | `is_otc:true` |
| `is_combination_product` | Combination product | `is_combination_product:true` |
| `is_kit` | Kit | `is_kit:true` |
| `is_hct_p` | Human cells/tissues product | |
| `is_labeled_as_nrl` | Contains natural rubber latex | `is_labeled_as_nrl:true` |
| `is_labeled_as_no_nrl` | No natural rubber latex | |
| `is_pm_exempt` | Premarket exempt | |
| `is_direct_marking_exempt` | Direct marking exempt | |
| `has_serial_number` | Has serial number | |
| `has_lot_or_batch_number` | Has lot/batch | |
| `has_manufacturing_date` | Has manufacturing date | |
| `has_expiration_date` | Has expiration date | |
| `has_donation_id_number` | Has donation ID | |
| `commercial_distribution_status` | In/out of distribution | |
| `mri_safety` | MRI safety classification | `mri_safety:"MR+Conditional"` |
| `labeler_duns_number` | DUNS number | |
| `record_status` | Record status | |
| `gmdn_terms.name` | GMDN term name | |
| `premarket_submissions.submission_number` | Linked K/P/DEN number | `premarket_submissions.submission_number:"K241335"` |

**Response fields** (organized by group):

*Identification*:
- `identifiers[].id`, `identifiers[].type` (Primary, Secondary, Unit of Use, etc.)
- `identifiers[].issuing_agency`, `identifiers[].package_status`
- `identifiers[].package_discontinue_date`, `identifiers[].package_type`
- `identifiers[].quantity_per_package`, `identifiers[].unit_of_use_id`

*Device info*:
- `brand_name`, `version_or_model_number`, `catalog_number`
- `company_name`, `device_description`, `device_count_in_base_package`

*Classification flags*:
- `is_single_use`, `is_rx`, `is_otc`, `is_combination_product`, `is_kit`
- `is_hct_p`, `is_labeled_as_nrl`, `is_labeled_as_no_nrl`
- `is_pm_exempt`, `is_direct_marking_exempt`

*Tracking flags*:
- `has_serial_number`, `has_lot_or_batch_number`, `has_manufacturing_date`
- `has_expiration_date`, `has_donation_id_number`

*Safety*:
- `mri_safety`
- `sterilization.is_sterile`, `sterilization.sterilization_methods`
- `storage[].type`, `storage[].high`, `storage[].low`, `storage[].unit`

*Sizes*:
- `device_sizes[].type`, `device_sizes[].value`, `device_sizes[].unit`, `device_sizes[].text`

*Nomenclature*:
- `gmdn_terms[].name`, `gmdn_terms[].definition`
- `product_codes[].code`, `product_codes[].name`, `product_codes[].openfda.*`

*Regulatory links*:
- `premarket_submissions[].submission_number`, `premarket_submissions[].supplement_number`

*Contacts*:
- `customer_contacts[].phone`, `customer_contacts[].email`, `customer_contacts[].ext`

*Distribution*:
- `commercial_distribution_status`, `commercial_distribution_end_date`
- `labeler_duns_number`

*Versioning*:
- `publish_date`, `public_version_date`, `public_version_number`
- `public_version_status`, `record_key`, `record_status`

**Common queries**:
```python
# Find UDI records linked to a specific K-number
fda_api("udi", 'premarket_submissions.submission_number:"K241335"', limit=10)

# Single-use wound dressings
fda_api("udi", 'product_codes.code:"KGN"+AND+is_single_use:true', limit=20)
```

## Field Mapping: openFDA Names to Human Labels

Use these mappings when displaying API results to users:

```python
FIELD_LABELS = {
    # 510(k) fields
    "k_number": "K-Number",
    "applicant": "Applicant",
    "contact": "Contact",
    "decision_date": "Decision Date",
    "decision_code": "Decision Code",
    "decision_description": "Decision",
    "device_name": "Device Name",
    "product_code": "Product Code",
    "clearance_type": "Clearance Type",
    "advisory_committee": "Advisory Committee",
    "advisory_committee_description": "Advisory Committee",
    "review_advisory_committee": "Review Advisory Committee",
    "third_party_flag": "Third Party Review",
    "expedited_review_flag": "Expedited Review",
    "statement_or_summary": "Statement/Summary",
    "date_received": "Date Received",

    # Classification fields
    "device_class": "Device Class",
    "regulation_number": "Regulation Number",
    "review_panel": "Review Panel",
    "definition": "Definition",
    "medical_specialty": "Medical Specialty",
    "medical_specialty_description": "Medical Specialty",
    "implant_flag": "Implant",
    "life_sustain_support_flag": "Life Sustaining/Supporting",
    "gmp_exempt_flag": "GMP Exempt",
    "third_party_flag": "Third Party Review Eligible",
    "review_code": "Review Code",
    "submission_type_id": "Submission Type",

    # MAUDE fields
    "event_type": "Event Type",
    "date_of_event": "Event Date",
    "generic_name": "Generic Name",
    "brand_name": "Brand Name",
    "manufacturer_d_name": "Manufacturer",
    "adverse_event_flag": "Adverse Event",
    "product_problem_flag": "Product Problem",
    "health_professional": "Health Professional Report",
    "number_devices_in_event": "Devices in Event",
    "number_patients_in_event": "Patients in Event",
    "single_use_flag": "Single Use Device",
    "reprocessed_and_reused_flag": "Reprocessed/Reused",
    "report_number": "Report Number",
    "mdr_report_key": "MDR Report Key",
    "report_source_code": "Report Source",
    "event_location": "Event Location",
    "manufacturer_name": "Manufacturer Name",

    # Recall fields
    "res_event_number": "Recall Event Number",
    "recall_status": "Recall Status",
    "classification": "Recall Class",
    "reason_for_recall": "Reason",
    "recalling_firm": "Recalling Firm",
    "event_date_initiated": "Recall Initiated",
    "product_description": "Product Description",
    "root_cause_description": "Root Cause",
    "cfres_id": "Recall ID",
    "event_date_created": "Record Created",
    "event_date_posted": "Posted Date",
    "event_date_terminated": "Recall Terminated",
    "firm_fei_number": "Firm FEI",

    # PMA fields
    "pma_number": "PMA Number",
    "trade_name": "Trade Name",
    "docket_number": "Docket Number",
    "fed_reg_notice_date": "Fed Register Date",
    "ao_statement": "Advisory Opinion",
    "supplement_number": "Supplement Number",
    "supplement_type": "Supplement Type",
    "supplement_reason": "Supplement Reason",

    # UDI fields
    "device_description": "Device Description",
    "commercial_distribution_status": "Distribution Status",
    "mri_safety": "MRI Safety",
    "is_single_use": "Single Use",
    "is_rx": "Prescription",
    "is_otc": "Over-the-Counter",
    "is_combination_product": "Combination Product",
    "is_kit": "Kit",
    "company_name": "Company",
    "version_or_model_number": "Model Number",
    "catalog_number": "Catalog Number",
}

def format_date(date_str):
    """Normalize date to YYYY-MM-DD for display.

    API search params use YYYYMMDD but response fields return YYYY-MM-DD.
    This handles both formats: converts 8-char YYYYMMDD; passes through YYYY-MM-DD unchanged.
    """
    if date_str and len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return date_str or "N/A"
```

## Field Name Inconsistencies Across Endpoints

The openFDA API is NOT consistent with field names across endpoints:

| Concept | 510(k) | Classification | PMA | Recall | MAUDE |
|---------|--------|---------------|-----|--------|-------|
| Address | `address_1` | -- | `street_1` | `address_1` | `manufacturer_address_1` |
| Zip | `zip_code` | -- | `zip` | `postal_code` | `manufacturer_zip_code` |
| Third party | `third_party_flag` | `third_party_flag` | -- | -- | -- |
| K-number | `k_number` (string) | -- | -- | `k_numbers` (array) | -- |
| Device name | `device_name` | `device_name` | `generic_name` | -- | `device.generic_name` |

Always check the endpoint-specific field names rather than assuming consistency.

## Error Handling Patterns

### Rate Limit Recovery
```python
import time

def fda_api_with_retry(endpoint, search, limit=10, count_field=None, max_retries=2):
    for attempt in range(max_retries + 1):
        result = fda_api(endpoint, search, limit, count_field)
        if result.get("status") == 429:
            if attempt < max_retries:
                time.sleep(60)
                continue
        return result
    return result
```

### Graceful Fallback
```python
def validate_with_fallback(knumber):
    """Try API first, fall back to flat files."""
    result = fda_api("510k", f'k_number:"{knumber}"')

    if "error" not in result and result.get("results"):
        return {"source": "openFDA API", "data": result["results"][0]}

    # Fallback to flat files
    # ... grep pmn*.txt ...
    return {"source": "flat files (offline fallback)", "data": flat_file_result}
```

### Offline Detection
```python
def check_api_available():
    """Quick check if API is reachable."""
    result = fda_api("510k", 'k_number:"K241335"', limit=1)
    if "error" in result and "Network error" in result["error"]:
        return False
    return True
```

## Search Syntax Notes

- **Exact match**: `field:"value"` (with quotes)
- **AND**: `field1:"val1"+AND+field2:"val2"`
- **OR**: `field1:"val1"+OR+field2:"val2"`
- **Date range**: `date_field:[YYYYMMDD+TO+YYYYMMDD]`
- **Wildcard**: Not supported in search; use broader queries and filter client-side
- **Spaces in values**: Use `+` instead of spaces: `device_name:"wound+dressing"`
- **Count endpoint**: Add `count=field.exact` to get aggregated counts instead of results
- **Limit**: Max 1000 per request; use `skip` parameter for pagination (max skip: 25000)
