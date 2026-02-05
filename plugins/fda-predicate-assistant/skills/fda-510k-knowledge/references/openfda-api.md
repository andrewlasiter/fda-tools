# openFDA Device API Reference

Centralized reference for all 7 openFDA Device API endpoints. All commands should use this as the single source of truth for API queries.

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

## 7 Endpoints Reference

### 1. `/device/510k` — 510(k) Clearances

**Purpose**: Look up 510(k) clearance records (same data as pmn*.txt flat files but real-time).

**Key searchable fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `k_number` | 510(k) number | `k_number:"K241335"` |
| `applicant` | Company name | `applicant:"MEDTRONIC"` |
| `product_code` | 3-letter code | `product_code:"KGN"` |
| `decision_date` | Clearance date (YYYYMMDD) | `decision_date:[20200101+TO+20251231]` |
| `decision_code` | SESE, SEKN, etc. | `decision_code:"SESE"` |
| `device_name` | Device name | `device_name:"wound+dressing"` |
| `advisory_committee` | Review panel code | `advisory_committee:"SU"` |
| `clearance_type` | Traditional, Special, etc. | `clearance_type:"Traditional"` |
| `third_party` | Third party review | `third_party:"Y"` |
| `statement_or_summary` | Summary or Statement | `statement_or_summary:"Summary"` |

**Response fields** (per result):
- `k_number`, `applicant`, `contact`, `address_1`, `address_2`, `city`, `state`, `zip_code`, `country_code`
- `date_received`, `decision_date`, `decision_code`, `decision_description`
- `product_code`, `device_name`, `clearance_type`, `advisory_committee`, `advisory_committee_description`
- `third_party`, `expedited_review_flag`, `statement_or_summary`
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

**Response fields**:
- `product_code`, `device_name`, `device_class`, `regulation_number`
- `review_panel`, `medical_specialty`, `medical_specialty_description`
- `definition`, `submission_type_id`, `gmp_exempt_flag`, `third_party_flag`
- `openfda.regulation_number`, `openfda.device_name`, `openfda.device_class`

**Common queries**:
```python
# Look up a product code
fda_api("classification", 'product_code:"KGN"')

# Search by keyword
fda_api("classification", 'device_name:"glucose+monitor"', limit=20)

# Find all Class III devices in a specialty
fda_api("classification", 'device_class:"3"+AND+medical_specialty:"CV"', limit=50)
```

### 3. `/device/event` — MAUDE Adverse Events

**Purpose**: Search the MAUDE (Manufacturer and User Facility Device Experience) database for adverse event reports.

**Key searchable fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `device.generic_name` | Device generic name | `device.generic_name:"wound+dressing"` |
| `device.brand_name` | Brand/trade name | `device.brand_name:"ACME+DRESSING"` |
| `device.product_code` | Product code | `device.product_code:"KGN"` |
| `device.manufacturer_d_name` | Manufacturer | `device.manufacturer_d_name:"MEDTRONIC"` |
| `event_type` | Injury/Malfunction/Death | `event_type:"Injury"` |
| `date_received` | FDA received date | `date_received:[20200101+TO+20251231]` |
| `mdr_text.text` | MDR narrative text | `mdr_text.text:"infection"` |
| `device.openfda.device_name` | FDA device name | |

**Response fields**:
- `event_type`, `date_received`, `date_of_event`
- `device[].generic_name`, `device[].brand_name`, `device[].product_code`, `device[].manufacturer_d_name`, `device[].device_operator`
- `mdr_text[].text`, `mdr_text[].text_type_code` (Description, Patient, Additional Manufacturer Narrative)
- `patient[].patient_sequence_number`, `patient[].date_received`, `patient[].sequence_number_outcome`
- `remedial_action`, `report_source_code`, `manufacturer_name`

**Common queries**:
```python
# Count events by type for a product code
fda_api("event", 'device.product_code:"KGN"', count_field="event_type.exact")

# Recent adverse events for a product code
fda_api("event", 'device.product_code:"KGN"+AND+date_received:[20230101+TO+20251231]', limit=25)

# Search narrative text for specific issues
fda_api("event", 'device.product_code:"KGN"+AND+mdr_text.text:"infection"', limit=10)

# Count events by year
fda_api("event", 'device.product_code:"KGN"', count_field="date_received")
```

### 4. `/device/recall` — Device Recalls

**Purpose**: Search FDA device recall data — recall class, reason, status, affected products.

**Key searchable fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `product_code` | Product code | `product_code:"KGN"` |
| `k_number` | Associated 510(k) | `k_number:"K241335"` |
| `recalling_firm` | Company name | `recalling_firm:"MEDTRONIC"` |
| `res_event_number` | Recall event ID | `res_event_number:"Z-1234-2024"` |
| `event_date_initiated` | Recall start date | `event_date_initiated:[20200101+TO+20251231]` |
| `product_description` | Product description | `product_description:"wound+dressing"` |
| `reason_for_recall` | Recall reason text | `reason_for_recall:"sterility"` |
| `openfda.device_name` | Device name | |
| `openfda.device_class` | Device class | |

**Response fields**:
- `res_event_number`, `event_date_initiated`, `event_date_terminated`
- `recall_status` (Ongoing, Completed, Terminated)
- `classification` (Class I, Class II, Class III — recall severity, NOT device class)
- `product_description`, `code_info`, `reason_for_recall`
- `recalling_firm`, `city`, `state`, `country`
- `product_quantity`, `distribution_pattern`, `voluntary_mandated`
- `k_number`, `product_code`
- `openfda.device_name`, `openfda.device_class`, `openfda.regulation_number`

**Common queries**:
```python
# Recalls for a specific K-number
fda_api("recall", 'k_number:"K241335"')

# Recalls for a product code
fda_api("recall", 'product_code:"KGN"', limit=50)

# Count recalls by classification (severity)
fda_api("recall", 'product_code:"KGN"', count_field="classification.exact")

# Active recalls only
fda_api("recall", 'product_code:"KGN"+AND+recall_status:"Ongoing"')
```

### 5. `/device/pma` — Premarket Approvals

**Purpose**: Look up PMA (Premarket Approval) records for Class III devices.

**Key searchable fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `pma_number` | PMA number | `pma_number:"P190001"` |
| `applicant` | Company name | `applicant:"MEDTRONIC"` |
| `product_code` | Product code | `product_code:"DXY"` |
| `decision_date` | Approval date | `decision_date:[20200101+TO+20251231]` |
| `advisory_committee` | Review panel | `advisory_committee:"CV"` |
| `generic_name` | Device generic name | `generic_name:"pacemaker"` |

**Response fields**:
- `pma_number`, `supplement_number`, `supplement_type`, `supplement_reason`
- `applicant`, `address_1`, `city`, `state`, `zip_code`
- `decision_date`, `decision_code`
- `product_code`, `generic_name`, `trade_name`
- `advisory_committee`, `advisory_committee_description`
- `openfda.device_name`, `openfda.device_class`, `openfda.regulation_number`

**Common queries**:
```python
# Look up a PMA
fda_api("pma", 'pma_number:"P190001"')

# PMAs for a product code
fda_api("pma", 'product_code:"DXY"', limit=50)
```

### 6. `/device/registrationlisting` — Establishment Registration & Listing

**Purpose**: Find registered medical device establishments and their listed devices.

**Key searchable fields**:
| Field | Description | Example |
|-------|-------------|---------|
| `products.product_code` | Product code | `products.product_code:"KGN"` |
| `products.k_number` | Associated 510(k) | `products.k_number:"K241335"` |
| `establishment_type` | Type of facility | |
| `registration.name` | Facility name | `registration.name:"MEDTRONIC"` |
| `registration.owner_operator.firm_name` | Owner | |

**Response fields**:
- `registration.name`, `registration.fei_number`, `registration.status_code`
- `registration.owner_operator.firm_name`, `registration.owner_operator.contact_address`
- `products[].product_code`, `products[].k_number`, `products[].created_date`
- `products[].openfda.device_name`, `products[].openfda.device_class`

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

**Response fields**:
- `identifiers[].id`, `identifiers[].type` (Primary, Secondary, Unit of Use, etc.)
- `brand_name`, `version_or_model_number`, `catalog_number`
- `company_name`, `device_description`
- `product_codes[].code`, `product_codes[].name`
- `sterilization.is_sterile`, `sterilization.sterilization_methods`
- `storage[].type`, `storage[].high`, `storage[].low`
- `mri_safety`, `latex`
- `device_sizes[].type`, `device_sizes[].value`, `device_sizes[].unit`

## Field Mapping: openFDA Names to Human Labels

Use these mappings when displaying API results to users:

```python
FIELD_LABELS = {
    # 510(k) fields
    "k_number": "K-Number",
    "applicant": "Applicant",
    "decision_date": "Decision Date",
    "decision_code": "Decision Code",
    "decision_description": "Decision",
    "device_name": "Device Name",
    "product_code": "Product Code",
    "clearance_type": "Clearance Type",
    "advisory_committee": "Advisory Committee",
    "advisory_committee_description": "Advisory Committee",
    "third_party": "Third Party Review",
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

    # MAUDE fields
    "event_type": "Event Type",
    "date_of_event": "Event Date",
    "generic_name": "Generic Name",
    "brand_name": "Brand Name",
    "manufacturer_d_name": "Manufacturer",

    # Recall fields
    "res_event_number": "Recall Event Number",
    "recall_status": "Recall Status",
    "classification": "Recall Class",
    "reason_for_recall": "Reason",
    "recalling_firm": "Recalling Firm",
    "event_date_initiated": "Recall Initiated",
    "product_description": "Product Description",
}

def format_date(date_str):
    """Convert YYYYMMDD to YYYY-MM-DD for display."""
    if date_str and len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return date_str or "N/A"
```

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
