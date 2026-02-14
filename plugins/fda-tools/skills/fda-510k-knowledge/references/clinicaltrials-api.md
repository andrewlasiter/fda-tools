# ClinicalTrials.gov API v2 Reference

The ClinicalTrials.gov API v2 provides free, unauthenticated access to clinical trial registrations. For medical device regulatory work, this enables finding clinical studies involving similar devices — useful for clinical evidence sections, SE arguments, and Pre-Sub preparation.

## Base URL

```
https://clinicaltrials.gov/api/v2/
```

**No authentication required.** Rate limit: ~50 requests/minute per IP.

## Endpoints

### 1. Search Studies

```
GET /studies?query.term=SEARCH&pageSize=N
```

| Parameter | Description |
|-----------|-------------|
| `query.term` | Free-text search across all fields |
| `query.cond` | Search by condition/disease |
| `query.intr` | Search by intervention (device name, drug name) |
| `query.titles` | Search study titles only |
| `query.outc` | Search outcome measures |
| `query.spons` | Search by sponsor/collaborator |
| `query.lead` | Search by lead sponsor |
| `query.locn` | Search by location |
| `filter.overallStatus` | RECRUITING, COMPLETED, ACTIVE_NOT_RECRUITING, etc. |
| `filter.studyType` | INTERVENTIONAL, OBSERVATIONAL, EXPANDED_ACCESS |
| `filter.phase` | EARLY_PHASE1, PHASE1, PHASE2, PHASE3, PHASE4, NA |
| `pageSize` | Results per page (max 1000, default 10) |
| `pageToken` | Pagination token from previous response |
| `countTotal` | true/false — include total count |
| `format` | json (default) or csv |
| `fields` | Comma-separated list of specific fields to return |
| `sort` | Sort field and order (e.g., `LastUpdatePostDate:desc`) |

### 2. Get Single Study

```
GET /studies/{nctId}
```

Returns full study record by NCT number.

### 3. Study Size/Stats

```
GET /stats/size
GET /stats/fieldValues/{fieldName}
```

Returns aggregate statistics.

## AREA Search Syntax

For precise field-level queries, use the AREA syntax:

```
AREA[StudyType]INTERVENTIONAL AND AREA[InterventionType]DEVICE
```

### Useful AREA fields for device searches:

| AREA Field | Description | Example |
|------------|-------------|---------|
| `StudyType` | Trial type | `INTERVENTIONAL`, `OBSERVATIONAL` |
| `InterventionType` | Intervention category | `DEVICE`, `PROCEDURE`, `COMBINATION_PRODUCT` |
| `Phase` | Trial phase | `NA` (most device trials), `PHASE1`, etc. |
| `OverallStatus` | Current status | `RECRUITING`, `COMPLETED` |
| `Condition` | Medical condition | `Spinal Fusion`, `Diabetes` |
| `InterventionName` | Device/drug name | `Cervical Fusion Cage` |
| `LeadSponsorName` | Sponsor company | `Medtronic` |
| `LocationCountry` | Study country | `United States` |
| `StartDate` | Study start | Date ranges: `RANGE[2023-01-01,MAX]` |
| `CompletionDate` | Study completion | Date ranges |
| `LastUpdatePostDate` | Last update | Date ranges |
| `ResultsFirstPostDate` | Results posted | Date ranges |

## Response Structure

```json
{
  "studies": [
    {
      "protocolSection": {
        "identificationModule": {
          "nctId": "NCT12345678",
          "briefTitle": "Study Title",
          "officialTitle": "Full Official Title",
          "organization": { "fullName": "Sponsor Name" }
        },
        "statusModule": {
          "overallStatus": "COMPLETED",
          "startDateStruct": { "date": "2023-01-15" },
          "completionDateStruct": { "date": "2024-06-30" }
        },
        "descriptionModule": {
          "briefSummary": "Study summary text...",
          "detailedDescription": "Detailed description..."
        },
        "conditionsModule": {
          "conditions": ["Spinal Fusion", "Degenerative Disc Disease"]
        },
        "designModule": {
          "studyType": "INTERVENTIONAL",
          "phases": ["NA"],
          "designInfo": {
            "allocation": "RANDOMIZED",
            "interventionModel": "PARALLEL",
            "primaryPurpose": "TREATMENT",
            "maskingInfo": { "masking": "SINGLE" }
          },
          "enrollmentInfo": { "count": 200, "type": "ACTUAL" }
        },
        "armsInterventionsModule": {
          "interventions": [
            {
              "type": "DEVICE",
              "name": "Cervical Fusion Cage",
              "description": "Device description..."
            }
          ]
        },
        "outcomesModule": {
          "primaryOutcomes": [
            {
              "measure": "Fusion Rate",
              "timeFrame": "12 months"
            }
          ]
        },
        "eligibilityModule": {
          "eligibilityCriteria": "Inclusion/exclusion text...",
          "sex": "ALL",
          "minimumAge": "18 Years",
          "maximumAge": "65 Years"
        },
        "contactsLocationsModule": {
          "locations": [
            {
              "facility": "Hospital Name",
              "city": "Minneapolis",
              "state": "Minnesota",
              "country": "United States"
            }
          ]
        }
      }
    }
  ],
  "totalCount": 42,
  "nextPageToken": "token_for_next_page"
}
```

## Example Queries

### Find device trials by intervention name

```
https://clinicaltrials.gov/api/v2/studies?query.intr=cervical+fusion+cage&filter.studyType=INTERVENTIONAL&pageSize=20&countTotal=true&format=json
```

### Find completed device trials by sponsor

```
https://clinicaltrials.gov/api/v2/studies?query.spons=Medtronic&filter.overallStatus=COMPLETED&filter.studyType=INTERVENTIONAL&pageSize=20&format=json
```

### Find all device interventions for a condition

```
https://clinicaltrials.gov/api/v2/studies?query.term=AREA[InterventionType]DEVICE+AND+AREA[Condition]spinal+fusion&pageSize=50&countTotal=true&format=json
```

### Find trials with results posted

```
https://clinicaltrials.gov/api/v2/studies?query.intr=wound+dressing&filter.overallStatus=COMPLETED&sort=ResultsFirstPostDate:desc&pageSize=20&format=json
```

## Integration with Plugin Commands

- `/fda:trials` — Primary command for clinical trial search
- `/fda:literature` — Cross-references trials with published literature
- `/fda:draft clinical` — References relevant trials in clinical evidence section
- `/fda:presub` — Includes trial landscape in Pre-Sub background
- `/fda:research` — Clinical trial count as market intelligence metric
- `/fda:test-plan` — Uses trial endpoints/outcomes as testing benchmarks
