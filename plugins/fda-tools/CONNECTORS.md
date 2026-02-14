# Connectors

## How data source references work

Commands reference external FDA and biomedical APIs to fetch device data, safety signals, clinical evidence, and regulatory intelligence. All APIs used are public and do not require authentication unless noted.

Commands are **source-aware** -- they describe workflows in terms of data categories (device clearances, adverse events, clinical trials, etc.) and fall back gracefully when a source is unreachable or returns no results.

## Data sources for this plugin

| Category | API / Source | Base URL | Auth Required | Integration |
|----------|-------------|----------|---------------|-------------|
| Device clearances (510(k)) | openFDA Device 510(k) | `https://api.fda.gov/device/510k.json` | No (API key optional) | Scripts |
| Device classification | openFDA Device Classification | `https://api.fda.gov/device/classification.json` | No (API key optional) | Scripts |
| Adverse events (MAUDE) | openFDA Device Events | `https://api.fda.gov/device/event.json` | No (API key optional) | Scripts |
| Recalls & enforcement | openFDA Device Recall / Enforcement | `https://api.fda.gov/device/recall.json` | No (API key optional) | Scripts |
| PMA approvals | openFDA Device PMA | `https://api.fda.gov/device/pma.json` | No (API key optional) | Scripts |
| UDI / device identifiers | openFDA Device UDI | `https://api.fda.gov/device/udi.json` | No (API key optional) | Scripts |
| Device characteristics (GUDID) | AccessGUDID | `https://accessgudid.nlm.nih.gov/api/v3/` | No | Scripts |
| Clinical trials | ClinicalTrials.gov v2 | `https://clinicaltrials.gov/api/v2/studies` | No | Scripts + MCP |
| Literature (PubMed) | NCBI E-utilities | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils` | No (API key recommended) | Scripts + MCP |
| FDA guidance documents | FDA.gov | `https://www.fda.gov/` (WebFetch) | No | WebFetch |
| Warning letters | openFDA Device Enforcement | `https://api.fda.gov/device/enforcement.json` | No (API key optional) | Scripts |
| 510(k) summary PDFs | FDA CDRH Portal | `https://www.accessdata.fda.gov/` | No | Scripts |

## MCP servers

The `.mcp.json` file configures MCP servers for data sources that have hosted MCP endpoints. Currently two are available:

| Server | MCP endpoint | Source |
|--------|-------------|--------|
| `pubmed` | `https://pubmed.mcp.claude.com/mcp` | PubMed literature search |
| `c-trials` | `https://mcp.deepsense.ai/clinical_trials/mcp` | ClinicalTrials.gov |

All other data sources are accessed directly via the bundled Python scripts in `scripts/`, which provide rate limiting, retry logic, caching, and structured output.

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
| openFDA 510(k) | [Checked / Unavailable / Not needed] | [details] |
| openFDA MAUDE | [Checked / Unavailable / Not needed] | [details] |
| openFDA Recalls | [Checked / Unavailable / Not needed] | [details] |
| AccessGUDID | [Checked / Unavailable / Not needed] | [details] |
| ClinicalTrials.gov | [Checked / Unavailable / Not needed] | [details] |
| PubMed | [Checked / Unavailable / Not needed] | [details] |
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
| `setup_api_key.py` | Interactive openFDA API key configuration |
| `version.py` | Plugin version constant |
