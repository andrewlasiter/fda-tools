---
name: integrate-external
description: Query external data sources (ClinicalTrials.gov, PubMed, USPTO Patents) for PMA device intelligence with caching and rate limiting
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--source clinicaltrials|pubmed|patents|all --query \"device query\" [--pma P170019] [--max-results 10]"
---

# FDA External Data Integration Hub

> **Important**: External data is for research and intelligence purposes only. It should not be treated as regulatory evidence without independent verification by qualified regulatory professionals.

Query external data sources for PMA device intelligence. Integrates ClinicalTrials.gov, PubMed, and USPTO PatentsView with per-source rate limiting and response caching.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--source SOURCE` | Data source to query | `--source pubmed` |
| `--query TEXT` | Search query | `--query "heart valve replacement"` |
| `--pma P_NUMBER` | PMA number for context | `--pma P170019` |
| `--max-results N` | Maximum results | `--max-results 10` |
| `--list-sources` | List available sources | (flag) |

## Resolve Plugin Root

```bash
FDA_PLUGIN_ROOT=$(python3 -c "
import json, os
f = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(f):
    d = json.load(open(f))
    for k, v in d.get('plugins', {}).items():
        if k.startswith('fda-tools@'):
            for e in v:
                p = e.get('installPath', '')
                if os.path.isdir(p):
                    print(p); exit()
print('')
")
echo "FDA_PLUGIN_ROOT=$FDA_PLUGIN_ROOT"
```

## Step 1: List Available Sources

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/external_data_hub.py \
  --list-sources --json
```

## Step 2: Query Data Sources

### ClinicalTrials.gov

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/external_data_hub.py \
  --source clinicaltrials --query "$QUERY" --pma "$PMA_NUMBER" --json
```

### PubMed Literature

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/external_data_hub.py \
  --source pubmed --query "$QUERY" --pma "$PMA_NUMBER" --json
```

### USPTO Patents

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/external_data_hub.py \
  --source patents --query "$QUERY" --pma "$PMA_NUMBER" --json
```

### All Sources Combined

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/external_data_hub.py \
  --source all --query "$QUERY" --pma "$PMA_NUMBER" --max-results 5 --json
```

## Step 3: Present Results

### ClinicalTrials.gov Results
```
  External Data: ClinicalTrials.gov (v2)
  Query: "{query}"
  Results: {N} of {total}
------------------------------------------------------------
  NCT ID       | Title                          | Status      | Enrollment
  NCT05001234  | Phase III Trial of Device X    | Recruiting  | 500
  NCT04005678  | Post-Market Surveillance Study | Completed   | 1,200
```

### PubMed Results
```
  External Data: PubMed E-utilities (v2.0)
  Query: "{query}"
  Results: {N} of {total}
------------------------------------------------------------
  PMID       | Title                          | Journal       | Date
  39012345   | Safety Analysis of Device X    | J Med Devices | 2024
  38901234   | Long-term Outcomes Study       | JACC          | 2023
```

### Patent Results
```
  External Data: USPTO PatentsView (v1)
  Query: "{query}"
  Results: {N} of {total}
------------------------------------------------------------
  Patent #     | Title                          | Assignee      | Date
  US12345678   | Medical Device Improvement     | Company A     | 2024-01-15
  US12345679   | Diagnostic Sensor System       | Company B     | 2023-08-20
```

## Data Sources

| Source | API | Rate Limit | Cache TTL |
|--------|-----|-----------|-----------|
| ClinicalTrials.gov | v2 | 1 req/sec | 24h |
| PubMed E-utilities | v2.0 | 3 req/sec | 168h (7d) |
| USPTO PatentsView | v1 | 1 req/sec | 168h (7d) |

## PMA Context Enrichment

When `--pma` is provided, queries are automatically enriched:
- **ClinicalTrials.gov**: Device name added to query
- **PubMed**: Device name added to query
- **Patents**: Applicant/manufacturer added to query

## Error Handling

- **API unavailable**: Returns cached results if available
- **Rate limited**: Automatic delay between requests
- **Invalid source**: Lists available sources with descriptions
- **No results**: Reports empty result set with query details
