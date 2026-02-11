# Connectors

## How tool references work

Plugin files use `~~category` as a placeholder for whatever tool the user connects in that category. For example, `~~device-clearances` might mean the openFDA 510(k) API, a hospital's internal device database, or any other MCP server that exposes cleared-device data.

Plugins are **tool-agnostic** -- they describe workflows in terms of categories (device clearances, adverse events, clinical trials, etc.) rather than specific products. The `.mcp.json` pre-configures specific MCP servers for several categories, but any MCP server in that category works.

## Connectors for this plugin

| Category | Placeholder | Included servers | Other options |
|----------|-------------|-----------------|---------------|
| Device clearances | `~~device-clearances` | openFDA 510(k)* | -- |
| Device classification | `~~device-classification` | openFDA Classification* | -- |
| Adverse events | `~~adverse-events` | openFDA MAUDE* | -- |
| Recalls & enforcement | `~~recalls` | openFDA Recall/Enforcement* | -- |
| PMA approvals | `~~pma` | openFDA PMA* | -- |
| Device identifiers | `~~device-ids` | AccessGUDID* | openFDA UDI |
| Clinical trials | `~~clinical-trials` | ClinicalTrials.gov | EU Clinical Trials Register |
| Literature | `~~literature` | PubMed | Google Scholar, Semantic Scholar |
| FDA guidance | `~~guidance` | FDA.gov (WebFetch) | -- |
| 510(k) summaries | `~~510k-summaries` | FDA CDRH Portal* | -- |

\* Placeholder -- MCP URL not yet configured. See `.mcp.json` for the current server list; entries with an empty `url` are stubs awaiting a community or first-party MCP server.

## API keys

openFDA endpoints work without authentication but are rate-limited to ~40 requests/minute per IP. An optional API key raises the limit to ~240 requests/minute:

- Register at https://open.fda.gov/apis/authentication/
- Configure via `/configure` or set the `OPENFDA_API_KEY` environment variable

NCBI E-utilities recommends an API key for >3 requests/second:

- Register at https://www.ncbi.nlm.nih.gov/account/settings/

## When a source is unavailable

If an API returns errors, times out, or is rate-limited, commands should:

1. Continue with available data rather than failing entirely
2. Include a **Sources Checked** section at the end of the output
3. Flag gaps so the user knows what was not verified
4. Suggest manual verification steps for missing data

### Standard source reporting block

Every command that queries external APIs should append this section to its output:

```
### Sources Checked
| Source | Status | Notes |
|--------|--------|-------|
| ~~device-clearances | [Checked / Unavailable / Not needed] | [details] |
| ~~adverse-events | [Checked / Unavailable / Not needed] | [details] |
| ~~recalls | [Checked / Unavailable / Not needed] | [details] |
| ~~device-ids | [Checked / Unavailable / Not needed] | [details] |
| ~~clinical-trials | [Checked / Unavailable / Not needed] | [details] |
| ~~literature | [Checked / Unavailable / Not needed] | [details] |
| Local project data | [Found / Not found / Not needed] | [details] |
```

Only include rows for sources relevant to the command. If all sources returned successfully, the table may be omitted.

## Plugin scripts

The plugin bundles Python scripts in `scripts/` that wrap these APIs with retry logic, caching, and structured output:

| Script | Purpose |
|--------|---------|
| `fda_api_client.py` | Centralized openFDA client with rate limiting and User-Agent |
| `fda_http.py` | HTTP wrapper with retry, timeout, and error handling |
| `batchfetch.py` | Bulk PDF downloader for 510(k) summaries |
| `predicate_extractor.py` | PDF text extraction and predicate parsing |
| `gap_analysis.py` | Identifies missing data across the pipeline |
| `estar_xml.py` | eSTAR XML generation |
| `fda_data_store.py` | Local data caching and project file management |
| `fda_audit_logger.py` | Decision audit trail logging |
| `alert_sender.py` | Monitoring alert dispatch |
