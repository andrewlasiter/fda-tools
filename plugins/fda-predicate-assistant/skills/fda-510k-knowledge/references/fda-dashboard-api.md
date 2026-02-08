# FDA Data Dashboard API Reference

The FDA Data Dashboard API (DDAPI) provides programmatic access to FDA inspection, citation, compliance action, and import refusal data. This is enforcement intelligence not available through openFDA.

## Authentication

**Credentials required.** Register at the OII Unified Logon application to receive an `Authorization-User` (email) and `Authorization-Key` (FDA-generated).

Store credentials in `~/.claude/fda-predicate-assistant.local.md`:

```yaml
---
fda_dashboard_user: "your-email@example.com"
fda_dashboard_key: "your-fda-generated-key"
---
```

## Base URL

```
https://api-datadashboard.fda.gov/v1/
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /inspections_classifications` | Inspection outcomes (NAI/VAI/OAI) for FDA-inspected facilities |
| `POST /inspections_citations` | Specific CFR citations issued during inspections |
| `POST /compliance_actions` | Warning letters, injunctions, seizures |
| `POST /import_refusals` | Import refusals with product codes and country of origin |

## Request Format

All endpoints use HTTP POST with JSON body.

### Headers

```
Content-Type: application/json
Authorization-User: <email>
Authorization-Key: <key>
```

### Request Body Schema

```json
{
  "sort": "InspectionEndDate",
  "sortorder": "DESC",
  "filters": {
    "ProductType": ["Devices"],
    "LegalName": ["COMPANY NAME"]
  },
  "columns": ["LegalName", "InspectionEndDate", "Classification", "ProjectArea", "PostedCitations"],
  "rows": 100,
  "start": 1,
  "returntotalcount": true
}
```

**Required fields:** `sort`, `sortorder`, `filters`, `columns`
**Optional fields:** `rows` (default 5000, max 5000), `start` (default 1), `returntotalcount` (default false)

### Pagination

Results are capped at 5000 per request. Use `start` parameter to paginate:
- First page: `"start": 1`
- Next page: `"start": previous_start + resultcount`
- Continue until `resultcount < rows`

## Field Reference

### inspections_classifications

| Field | Match Type | Description |
|-------|-----------|-------------|
| FEINumber | Exact | FDA Establishment Identifier |
| LegalName | Partial | Firm name |
| City | Partial | City |
| StateCode | Exact | State code (e.g., "CA") |
| State | Exact | State name |
| CountryCode | Exact | Country code |
| CountryName | Partial | Country name |
| InspectionID | Exact | Unique inspection ID |
| InspectionEndDate | Date | Inspection end date (use From/To for ranges) |
| FiscalYear | Exact | Fiscal year of inspection |
| PostedCitations | Boolean | Whether citations were issued |
| Classification | Partial | NAI, VAI, or OAI |
| ClassificationCode | Exact | NAI / VAI / OAI |
| ProjectArea | — | Category of FDA field activity |
| ProductType | Partial | Biologics, Devices, Drugs, Food/Cosmetics, Tobacco, Veterinary |
| FirmProfile | — | URL to firm profile on Data Dashboard |

**Classification codes:**
- **NAI** (No Action Indicated) — No objectionable conditions found
- **VAI** (Voluntary Action Indicated) — Objectionable conditions found but firm expected to correct voluntarily
- **OAI** (Official Action Indicated) — Regulatory/administrative action recommended

### inspections_citations

| Field | Match Type | Description |
|-------|-----------|-------------|
| InspectionID | Exact | Links to parent inspection |
| FEINumber | Exact | FDA Establishment Identifier |
| LegalName | Partial | Firm name |
| InspectionEndDate | Date | Inspection date (use From/To) |
| FiscalYear | Exact | Fiscal year |
| ProgramArea | Partial | Regulatory category |
| CitationID | Exact | Unique citation ID |
| ActCFRNumber | Partial | CFR section cited (e.g., "21 CFR 820.30") |
| ShortDescription | Partial | Brief citation description |
| LongDescription | Partial | Detailed citation description |

### compliance_actions

| Field | Match Type | Description |
|-------|-----------|-------------|
| FEINumber | Exact | FDA Establishment Identifier |
| LegalName | Partial | Firm name |
| ProductType | Partial | Product type filter |
| Center | Exact | FDA Center (CDRH for devices) |
| ActionType | Partial | Injunction, Seizure, Warning Letter |
| ActionTakenDate | Date | Date of action (use From/To) |
| FiscalYear | Exact | Fiscal year |
| CaseInjunctionID | Exact | Unique case/injunction ID |
| Region | Exact | Foreign or domestic |

### import_refusals

| Field | Match Type | Description |
|-------|-----------|-------------|
| FEINumber | Exact | FDA Establishment Identifier |
| LegalName | Partial | Firm name |
| ProductType | Partial | Product type filter |
| CountryCode | Exact | Country of origin |
| CountryName | Partial | Country name |
| ProductCode | Exact | FDA product code |
| RefusalDate | Date | Date of refusal (use From/To) |
| FiscalYear | Exact | Fiscal year |
| RefusalCharges | Partial | Charges/reasons for refusal |

## Example Queries

### Find all device inspections for a company

```bash
curl -X POST https://api-datadashboard.fda.gov/v1/inspections_classifications \
  -H "Content-Type: application/json" \
  -H "Authorization-User: user@example.com" \
  -H "Authorization-Key: YOUR_KEY" \
  -d '{
    "sort": "InspectionEndDate",
    "sortorder": "DESC",
    "filters": {
      "ProductType": ["Devices"],
      "LegalName": ["MEDTRONIC"]
    },
    "columns": ["LegalName", "City", "State", "InspectionEndDate", "Classification", "PostedCitations"],
    "rows": 50,
    "start": 1,
    "returntotalcount": true
  }'
```

### Find CFR citations for device quality system (21 CFR 820)

```bash
curl -X POST https://api-datadashboard.fda.gov/v1/inspections_citations \
  -H "Content-Type: application/json" \
  -H "Authorization-User: user@example.com" \
  -H "Authorization-Key: YOUR_KEY" \
  -d '{
    "sort": "InspectionEndDate",
    "sortorder": "DESC",
    "filters": {
      "ActCFRNumber": ["820"]
    },
    "columns": ["LegalName", "InspectionEndDate", "ActCFRNumber", "ShortDescription", "LongDescription"],
    "rows": 100,
    "start": 1,
    "returntotalcount": true
  }'
```

### Find warning letters for device companies

```bash
curl -X POST https://api-datadashboard.fda.gov/v1/compliance_actions \
  -H "Content-Type: application/json" \
  -H "Authorization-User: user@example.com" \
  -H "Authorization-Key: YOUR_KEY" \
  -d '{
    "sort": "ActionTakenDate",
    "sortorder": "DESC",
    "filters": {
      "ProductType": ["Devices"],
      "ActionType": ["Warning Letter"]
    },
    "columns": ["LegalName", "ActionType", "ActionTakenDate", "Center"],
    "rows": 50,
    "start": 1,
    "returntotalcount": true
  }'
```

### Find import refusals by product code

```bash
curl -X POST https://api-datadashboard.fda.gov/v1/import_refusals \
  -H "Content-Type: application/json" \
  -H "Authorization-User: user@example.com" \
  -H "Authorization-Key: YOUR_KEY" \
  -d '{
    "sort": "RefusalDate",
    "sortorder": "DESC",
    "filters": {
      "ProductCode": ["KGN"]
    },
    "columns": ["LegalName", "CountryName", "ProductCode", "RefusalDate", "RefusalCharges"],
    "rows": 50,
    "start": 1,
    "returntotalcount": true
  }'
```

## Integration with Plugin Commands

- `/fda:inspections` — Primary command for all 4 endpoints
- `/fda:safety` — Cross-references MAUDE/recall data with inspection history
- `/fda:research` — Includes enforcement context for competitor analysis
- `/fda:pre-check` — Flags if predicate manufacturer has OAI history
- `/fda:presub` — References inspection trends in regulatory background
