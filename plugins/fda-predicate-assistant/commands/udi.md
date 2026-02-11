---
description: Look up UDI/GUDID records from openFDA and AccessGUDID — search by device identifier, product code, company, or brand name, with device history and SNOMED mapping
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch
argument-hint: "--product-code CODE | --di NUMBER | --company NAME | --brand NAME [--history] [--snomed] [--parse-udi UDI] [--project NAME] [--save]"
---

# FDA UDI/GUDID Database Lookup

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

> For external API dependencies and connection status, see [CONNECTORS.md](../CONNECTORS.md).


## Resolve Plugin Root

**Before running any bash commands that reference `$FDA_PLUGIN_ROOT`**, resolve the plugin install path:

```bash
FDA_PLUGIN_ROOT=$(python3 -c "
import json, os
f = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(f):
    d = json.load(open(f))
    for k, v in d.get('plugins', {}).items():
        if k.startswith('fda-predicate-assistant@'):
            for e in v:
                p = e.get('installPath', '')
                if os.path.isdir(p):
                    print(p); exit()
print('')
")
echo "FDA_PLUGIN_ROOT=$FDA_PLUGIN_ROOT"
```

---

You are querying the **openFDA UDI** endpoint for broad searches and the **AccessGUDID v3 API** (NLM) for detailed device lookups, history tracking, SNOMED mapping, and UDI barcode parsing.

**Data source strategy:**
- **openFDA** for searches by product code, company name, brand name (Elasticsearch queries)
- **AccessGUDID v3** for DI-specific lookups, device history, SNOMED terms, UDI parsing (authoritative, real-time)

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--product-code CODE` — Search by FDA product code (openFDA)
- `--di NUMBER` — Search by primary device identifier (openFDA + AccessGUDID for enrichment)
- `--company NAME` — Search by company name (openFDA)
- `--brand NAME` — Search by brand name (openFDA)
- `--history` — Show device modification history (AccessGUDID)
- `--snomed` — Show SNOMED CT clinical terminology mapping (AccessGUDID)
- `--parse-udi UDI` — Parse a raw UDI barcode into components (AccessGUDID)
- `--project NAME` — Associate results with a project
- `--save` — Save results to project folder
- `--limit N` — Max results (default 10)

At least one of `--product-code`, `--di`, `--company`, `--brand`, or `--parse-udi` is required.

## Step 1: Query openFDA UDI Endpoint

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time

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
    print("UDI_SKIP:api_disabled")
    exit(0)

# Build search query from arguments (replace placeholders)
search_parts = []
product_code = "PRODUCT_CODE"  # Replace or None
di = "DI_NUMBER"               # Replace or None
company = "COMPANY_NAME"       # Replace or None
brand = "BRAND_NAME"           # Replace or None
limit = 100                    # Replace with actual --limit value if provided

if product_code and product_code != "None":
    search_parts.append(f'product_codes.code:"{product_code}"')
if di and di != "None":
    search_parts.append(f'identifiers.id:"{di}"')
if company and company != "None":
    search_parts.append(f'company_name:"{company}"')
if brand and brand != "None":
    search_parts.append(f'brand_name:"{brand}"')

if not search_parts:
    print("ERROR:No search criteria provided")
    exit(1)

search = "+AND+".join(search_parts)
params = {"search": search, "limit": str(limit)}
if api_key:
    params["api_key"] = api_key

url = f"https://api.fda.gov/device/udi.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/4.9.0)"})

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        total = data.get("meta", {}).get("results", {}).get("total", 0)
        returned = len(data.get("results", []))
        print(f"TOTAL:{total}")
        print(f"SHOWING:{returned}_OF:{total}")
        for r in data.get("results", []):
            print(f"=== UDI RECORD ===")
            print(f"COMPANY:{r.get('company_name', 'N/A')}")
            print(f"BRAND:{r.get('brand_name', 'N/A')}")
            print(f"VERSION:{r.get('version_or_model_number', 'N/A')}")
            print(f"CATALOG:{r.get('catalog_number', 'N/A')}")
            print(f"DESCRIPTION:{r.get('device_description', 'N/A')}")

            # Device identifiers
            for ident in r.get("identifiers", []):
                dtype = ident.get("type", "")
                did = ident.get("id", "")
                issuing = ident.get("issuing_agency", "")
                print(f"IDENTIFIER:{dtype}|{did}|{issuing}")

            # Product codes
            for pc in r.get("product_codes", []):
                print(f"PRODUCT_CODE:{pc.get('code', '')}|{pc.get('name', '')}")

            # GMDN terms
            for gmdn in r.get("gmdn_terms", []):
                print(f"GMDN:{gmdn.get('name', '')}|{gmdn.get('definition', '')[:100]}")

            # Safety/compatibility info
            print(f"MRI_SAFETY:{r.get('mri_safety', 'N/A')}")
            print(f"LATEX:{r.get('is_natural_rubber_latex', 'N/A')}")
            print(f"SINGLE_USE:{r.get('is_single_use', 'N/A')}")
            print(f"STERILE:{r.get('is_sterile', 'N/A')}")
            print(f"STERILIZATION_PRIOR:{r.get('sterilization_prior_to_use', 'N/A')}")
            print(f"IMPLANT:{r.get('is_kit', 'N/A')}")
            print(f"RX:{r.get('is_rx', 'N/A')}")
            print(f"OTC:{r.get('is_otc', 'N/A')}")

            # Device sizes
            for size in r.get("device_sizes", []):
                print(f"SIZE:{size.get('type', '')}|{size.get('value', '')}|{size.get('unit', '')}")

            print()
except urllib.error.HTTPError as e:
    if e.code == 404:
        print("TOTAL:0")
    else:
        print(f"ERROR:HTTP {e.code}: {e.reason}")
except Exception as e:
    print(f"ERROR:{e}")
PYEOF
```

## Step 2: AccessGUDID Enrichment (when --di is provided or DI found from openFDA)

If a DI (Device Identifier) is available — either from `--di` directly or extracted from openFDA results — query AccessGUDID v3 for enrichment data.

### Device Detail Lookup

```bash
curl -s "https://accessgudid.nlm.nih.gov/api/v3/devices/lookup.json?di=DEVICE_IDENTIFIER"
```

This returns the authoritative GUDID record with:
- Manufacturer contacts (phone, email)
- Storage/handling conditions (temperature range, humidity, special conditions)
- Distribution end date (if device was discontinued)
- Device publish date

### Device History (if --history)

```bash
curl -s "https://accessgudid.nlm.nih.gov/api/v3/devices/history.json?di=DEVICE_IDENTIFIER"
```

Shows a timeline of changes to the device's GUDID record — when fields were modified, new versions published, or distribution status changed. Useful for tracking device evolution.

### SNOMED CT Mapping (if --snomed)

```bash
curl -s "https://accessgudid.nlm.nih.gov/api/v3/devices/snomed.json?di=DEVICE_IDENTIFIER"
```

Returns SNOMED CT clinical terminology codes linked to the device. Useful for:
- Clinical terminology alignment in submission documents
- Mapping device function to clinical concepts
- Cross-referencing with clinical evidence searches

### Parse UDI Barcode (if --parse-udi)

```bash
curl -s "https://accessgudid.nlm.nih.gov/api/v3/parse_udi.json?udi=ENCODED_UDI_STRING"
```

Parses a raw UDI barcode string (from GS1, HIBCC, or ICCBBA format) into structured components:
- Device Identifier (DI)
- Manufacturing date
- Expiration date
- Lot number
- Serial number
- Issuing agency

**Note:** The UDI string must be percent-encoded in the URL.

### Implantable Status Check

If the device might be implantable, also check:

```bash
curl -s "https://accessgudid.nlm.nih.gov/api/v3/devices/implantable_list.json?di=DEVICE_IDENTIFIER"
```

## Step 3: Present Results

```
  FDA UDI/GUDID Database Lookup
  {search context}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Source: openFDA UDI + AccessGUDID v3 | v5.22.0

SEARCH RESULTS ({total} records found)
────────────────────────────────────────

  Record 1:
  Company:     {company_name}
  Brand:       {brand_name}
  Model:       {version_or_model_number}
  Catalog:     {catalog_number}
  Description: {device_description}

  Identifiers:
    Primary DI: {identifier}  (Issuing Agency: {GS1/HIBCC/ICCBBA})

  Product Codes: {code} — {name}
  GMDN Terms:   {gmdn_name}

  Device Properties:
  | Property          | Value |
  |-------------------|-------|
  | MRI Safety        | {mri_safety} |
  | Latex             | {Y/N} |
  | Single Use        | {Y/N} |
  | Sterile           | {Y/N} |
  | Requires Sterilization | {Y/N} |
  | Rx/OTC            | {Rx/OTC} |

  Sizes:
    {type}: {value} {unit}

  ---

  Record 2: ...

ACCESSGUDID ENRICHMENT (if DI available)
────────────────────────────────────────

  Manufacturer Contact:
    Phone: {phone}
    Email: {email}

  Storage Conditions:
    | Condition   | Low    | High   |
    |-------------|--------|--------|
    | Temperature | 15 C   | 30 C   |
    | Humidity    | 20%    | 80%    |

  Published: {devicePublishDate}
  Distribution End: {deviceCommDistributionEndDate or "Active"}

DEVICE HISTORY (if --history)
────────────────────────────────────────

  | Date       | Change                                    |
  |------------|------------------------------------------|
  | 2024-03-15 | Initial publication                       |
  | 2024-09-01 | Updated sterilization method              |
  | 2025-01-10 | Added new product code                    |

SNOMED CT MAPPING (if --snomed)
────────────────────────────────────────

  | SNOMED Code | Preferred Term                    |
  |-------------|----------------------------------|
  | 12345678    | Orthopedic fusion cage device     |

UDI BARCODE PARSE (if --parse-udi)
────────────────────────────────────────

  UDI String: {raw_udi}
  Issuing Agency: {GS1/HIBCC/ICCBBA}
  Device Identifier (DI): {di}
  Manufacturing Date: {date or N/A}
  Expiration Date: {date or N/A}
  Lot Number: {lot or N/A}
  Serial Number: {serial or N/A}

RECOMMENDATIONS
────────────────────────────────────────

  1. UDI data helps populate eSTAR labeling section
  2. For labeling compliance: /fda:draft labeling --project NAME
  3. For full device profile: /fda:validate {K-number}
  4. Device history tracks modifications useful for SE arguments
  5. SNOMED terms align clinical terminology across submission docs

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

### Sources Checked

Append a sources table to every output showing which external APIs were queried and their status. See [CONNECTORS.md](../CONNECTORS.md) for the standard format. Only include rows for sources this command actually uses.

## Save Results (--save)

If `--save` is specified, write results to `$PROJECTS_DIR/$PROJECT_NAME/udi_lookup.json`:

```json
{
  "query": {"product_code": "OVE", "company": null, "di": null},
  "total_results": 25,
  "records": [
    {
      "company_name": "...",
      "brand_name": "...",
      "primary_di": "...",
      "product_codes": ["OVE"],
      "sterile": true,
      "mri_safety": "MR Conditional"
    }
  ],
  "queried_at": "2026-02-07T12:00:00Z"
}
```

## UDI System Reference

See `references/udi-requirements.md` for:
- UDI system overview (21 CFR 801.20)
- GUDID database structure
- DI vs PI (Device Identifier vs Production Identifier)
- Compliance dates by device class
- Issuing agencies (GS1, HIBCC, ICCBBA)

## Error Handling

- **No arguments**: Show usage with examples
- **API unavailable**: "UDI lookup requires openFDA API access. Enable with `/fda:configure --set openfda_enabled true`"
- **No results**: "No UDI records found. Try broadening your search or check that the device is registered in GUDID."
