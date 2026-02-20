# AccessGUDID API Reference (NLM)

AccessGUDID is the authoritative public interface to the FDA's Global Unique Device Identification Database (GUDID), maintained by the National Library of Medicine (NLM). It provides device lookup, history tracking, UDI parsing, and SNOMED CT mapping — data not fully available through openFDA.

## Base URL

```
https://accessgudid.nlm.nih.gov/api/v3/
```

**No authentication required** for basic lookups. API key authentication available for higher rate limits.

## Endpoints

### 1. Device Lookup

Retrieve full GUDID record for a device by its identifier.

**JSON:** `GET /api/v3/devices/lookup.json`
**XML:** `GET /api/v3/devices/lookup.xml`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `di` | One of di/udi/record_key | Device Identifier string |
| `udi` | One of di/udi/record_key | Full UDI string (percent-encoded) |
| `record_key` | One of di/udi/record_key | Public Device Record Key |

**Example:**
```
https://accessgudid.nlm.nih.gov/api/v3/devices/lookup.json?di=08717648200274
```

**Response fields:**
- `gudid.device` — Core device record with:
  - `versionModelNumber`, `catalogNumber`, `companyName`, `brandName`
  - `deviceDescription`, `devicePublishDate`, `deviceCommDistributionEndDate`
  - `gmdnTerms[]` — GMDN classification terms
  - `productCodes[]` — FDA product codes with `productCode`, `productCodeName`
  - `identifiers[]` — DI, PI, issuing agency
  - `contacts[]` — Manufacturer contacts with phone, email, ext
  - `deviceSizes[]` — Physical dimensions
  - `sterilization` — Sterilization info (prior use, method)
  - `storageHandling[]` — Storage conditions (temperature, humidity)
  - `MRISafetyStatus` — MR Safe / MR Conditional / MR Unsafe
  - `labeledContainsNRL` — Natural rubber latex flag
  - `labeledNoNRL` — Labeled as not containing NRL
  - `rxPremarket`, `otcPremarket` — Rx/OTC status

### 2. Device History

Track changes to a device's GUDID record over time.

**JSON:** `GET /api/v3/devices/history.json`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `di` | Yes | Device Identifier |

**Example:**
```
https://accessgudid.nlm.nih.gov/api/v3/devices/history.json?di=08717648200274
```

**Response:** Array of historical records showing when fields changed — useful for tracking device modifications, publication dates, and distribution status changes.

### 3. Parse UDI

Parse a raw UDI barcode string into its structured components.

**JSON:** `GET /api/v3/parse_udi.json`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `udi` | Yes | Full UDI string (percent-encoded) |

**Example:**
```
https://accessgudid.nlm.nih.gov/api/v3/parse_udi.json?udi=%2808717648200274%29
```

**Response fields:**
- `udi` — Original UDI string
- `issuingAgency` — GS1 / HIBCC / ICCBBA / UNKNOWN
- `di` — Parsed Device Identifier
- `manufacturingDate` — Parsed manufacturing date (if encoded)
- `expirationDate` — Parsed expiration date (if encoded)
- `lotNumber` — Parsed lot number (if encoded)
- `serialNumber` — Parsed serial number (if encoded)
- `donationId` — Parsed donation ID (if encoded)

### 4. Device SNOMED

Look up SNOMED CT clinical terminology codes mapped to a device.

**JSON:** `GET /api/v3/devices/snomed.json`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `di` | Yes | Device Identifier |

**Example:**
```
https://accessgudid.nlm.nih.gov/api/v3/devices/snomed.json?di=08717648200274
```

**Response:** SNOMED CT concept IDs and preferred terms linked to the device — useful for clinical terminology alignment in submission documents.

**Note:** SNOMED data requires a valid UMLS ticket for full access.

### 5. Implantable Device List

Check if a device is on the implantable device list.

**JSON:** `GET /api/v3/devices/implantable_list.json`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `di` | Yes | Device Identifier |

**Response:** Implantable device status and classification.

## Bulk Data Downloads

For large-scale analysis, AccessGUDID provides full database downloads:

```
https://accessgudid.nlm.nih.gov/download
```

Available formats: delimited text files (devices, identifiers, contacts, product codes).

## Rate Limits

- No authentication required for basic use
- Rate limiting applies (exact limits undocumented — approximately 100 req/min)
- For higher throughput, register for an API key at AccessGUDID

## Comparison: AccessGUDID vs openFDA UDI

| Feature | openFDA UDI | AccessGUDID v3 |
|---------|------------|----------------|
| Data freshness | Periodic snapshot | Real-time |
| Device history | No | Yes |
| UDI parsing | No | Yes |
| SNOMED mapping | No | Yes |
| Implantable list | No | Yes |
| Storage conditions | Partial | Full |
| Manufacturer contacts | No | Yes |
| Search flexibility | Elasticsearch queries | DI/UDI/record_key lookup |
| Bulk download | Yes (JSON) | Yes (delimited text) |

**Recommendation:** Use openFDA for broad searches (by product code, company name). Use AccessGUDID for detailed lookups on specific devices (history, SNOMED, UDI parsing, contacts).

## Integration with Plugin Commands

- `/fda:udi` — Primary consumer: enriches openFDA results with AccessGUDID data
- `/fda:validate` — Cross-reference device identifier data
- `/fda:compare-se` — Use SNOMED terms for clinical terminology alignment
- `/fda:draft labeling` — Populate labeling fields from GUDID record
- `/fda:research` — Storage conditions and implantable status for competitor devices
