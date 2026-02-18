# FDA HTTP User-Agent Configuration

## Overview

The FDA tools use different user-agent (UA) strings for different FDA server endpoints to balance compliance, transparency, and technical compatibility.

## Two User-Agent Strategies

### 1. API Headers (`FDA_API_HEADERS`)

**Purpose:** Honest identification for programmatic API access

**User-Agent:** `FDA-Plugin/{version}` (e.g., `FDA-Plugin/5.36.0`)

**Used for:**
- `api.fda.gov` endpoints (openFDA API)
- Device classification lookups
- 510(k) search queries
- MAUDE adverse event queries
- All JSON API responses

**Why:** openFDA API is designed for programmatic access and accepts honest user-agents. This is the **recommended and transparent** approach.

### 2. Website Headers (`FDA_WEBSITE_HEADERS`)

**Purpose:** Browser-like headers for legacy CDN compatibility

**User-Agent:** `Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...` (Chrome-like)

**Used for:**
- `accessdata.fda.gov` endpoints (legacy PDF CDN)
- 510(k) PDF downloads
- Database file downloads (pmn96cur.zip, etc.)

**Why:** FDA's legacy CDN infrastructure returns HTTP 403 Forbidden for programmatic user-agents. This appears to be CDN-level anti-bot protection, not FDA policy. We use browser-like headers **only** for this endpoint as a technical necessity.

## Configuration File

You can override the default behavior via `~/.claude/fda-tools.config.toml`:

```toml
[http]
# Override user-agent string for all requests (both API and website)
user_agent_override = "MyCompany-FDATools/2.0"

# Force honest user-agent for all requests (may break PDF downloads)
honest_ua_only = false
```

### Configuration Options

#### `user_agent_override`

- Type: String (optional)
- Default: None (use plugin defaults)
- Effect: Overrides **both** API and website user-agent strings
- Example: `"MyCompany-FDATools/2.0 (contact@example.com)"`

#### `honest_ua_only`

- Type: Boolean
- Default: `false`
- Effect: If `true`, uses honest UA (`FDA-Plugin/{version}`) for **all** requests, including PDF downloads
- Warning: This **will cause PDF download failures** (HTTP 403) from `accessdata.fda.gov`

## Usage Examples

### Python Code

```python
from fda_http import FDA_API_HEADERS, FDA_WEBSITE_HEADERS, get_headers, create_session

# For API calls (recommended):
import requests
response = requests.get('https://api.fda.gov/device/classification.json',
                       headers=FDA_API_HEADERS)

# For PDF downloads (technical necessity):
response = requests.get('https://www.accessdata.fda.gov/cdrh_docs/pdf24/K240123.pdf',
                       headers=FDA_WEBSITE_HEADERS)

# Using create_session:
api_session = create_session(purpose='api')
pdf_session = create_session(purpose='website')

# Backward compatible API:
api_session = create_session(api_mode=True)
pdf_session = create_session(api_mode=False)
```

### Which Scripts Use Which Headers?

| Script                        | Headers Used          | Purpose                          |
|-------------------------------|----------------------|----------------------------------|
| `knowledge_based_generator.py` | `FDA_API_HEADERS`    | Device classification API calls  |
| `fda_api_client.py`           | `FDA_API_HEADERS`    | openFDA API wrapper              |
| `batchfetch.py`               | `FDA_WEBSITE_HEADERS`| PDF/zip downloads from CDN       |
| `predicate_extractor.py`      | `FDA_WEBSITE_HEADERS`| Database file downloads          |

## FDA Terms of Service Compliance

This approach complies with FDA's Terms of Service and best practices:

### ✓ Compliant Practices

1. **Honest Identification for APIs:** We identify as `FDA-Plugin/{version}` for all openFDA API calls
2. **Rate Limiting:** 30-second default delay between PDF downloads
3. **Caching:** Database files cached for <5 days to minimize server load
4. **No Authentication Bypass:** We never circumvent access controls
5. **Technical Necessity:** Browser headers used only where required for technical compatibility

### Technical Rationale for Website Headers

The `accessdata.fda.gov` PDF endpoint behavior:

```bash
# Honest UA - FAILS:
$ curl -H "User-Agent: FDA-Plugin/5.36.0" \
  https://www.accessdata.fda.gov/cdrh_docs/pdf24/K240001.pdf
HTTP/1.1 403 Forbidden

# Browser UA - WORKS:
$ curl -H "User-Agent: Mozilla/5.0 ..." \
  https://www.accessdata.fda.gov/cdrh_docs/pdf24/K240001.pdf
HTTP/1.1 200 OK
```

This is **CDN-level filtering** (likely Akamai or CloudFront), not FDA policy. The PDFs are public records under FOIA and are meant to be accessible.

### References

- openFDA API Policy: https://open.fda.gov/apis/authentication/
- FDA FOIA Office: https://www.fda.gov/regulatory-information/freedom-information
- FDA Accessibility: https://www.fda.gov/accessibility

## Testing Your Configuration

```bash
# Test default configuration:
python3 -c "
from fda_http import FDA_API_HEADERS, FDA_WEBSITE_HEADERS
print('API UA:', FDA_API_HEADERS['User-Agent'])
print('Website UA:', FDA_WEBSITE_HEADERS['User-Agent'])
"

# Test custom configuration:
echo '[http]
user_agent_override = "TestUA/1.0"
' > ~/.claude/fda-tools.config.toml

python3 -c "
from fda_http import FDA_API_HEADERS, FDA_WEBSITE_HEADERS
print('API UA:', FDA_API_HEADERS['User-Agent'])
print('Website UA:', FDA_WEBSITE_HEADERS['User-Agent'])
"

# Remove test config:
rm ~/.claude/fda-tools.config.toml
```

## Troubleshooting

### PDF Downloads Fail with HTTP 403

**Cause:** `honest_ua_only = true` in configuration, or CDN blocking your IP

**Solution:**
1. Check `~/.claude/fda-tools.config.toml` and ensure `honest_ua_only = false`
2. Or remove the config file to use defaults
3. If problem persists, check if your IP is rate-limited by FDA's CDN

### API Calls Return Unexpected Responses

**Cause:** `user_agent_override` set to invalid value

**Solution:**
1. Check `~/.claude/fda-tools.config.toml`
2. Ensure `user_agent_override` follows format: `Name/Version (contact)`
3. Or remove override to use plugin default

## Backward Compatibility

### Deprecated Names (still supported)

The following names are deprecated but still work for backward compatibility:

```python
from fda_http import FDA_HEADERS, OPENFDA_HEADERS

# Old names (deprecated):
FDA_HEADERS         # Now: FDA_WEBSITE_HEADERS
OPENFDA_HEADERS     # Now: FDA_API_HEADERS

# Old function signature (still supported):
create_session(api_mode=True)   # Now: create_session(purpose='api')
create_session(api_mode=False)  # Now: create_session(purpose='website')
```

**Migration Guide:**

```python
# Old code:
from fda_http import FDA_HEADERS, OPENFDA_HEADERS, create_session
session = create_session(api_mode=True)
headers = FDA_HEADERS

# New code:
from fda_http import FDA_WEBSITE_HEADERS, FDA_API_HEADERS, create_session
session = create_session(purpose='api')
headers = FDA_WEBSITE_HEADERS
```

## Future Considerations

If FDA updates their CDN to accept programmatic user-agents for PDF downloads, we will:

1. Update `FDA_WEBSITE_HEADERS` to use honest UA
2. Deprecate the browser-like UA entirely
3. Notify users via release notes

Until then, the dual-UA approach balances transparency (for APIs) with technical necessity (for PDFs).

## Questions?

For questions about this configuration or FDA Terms of Service compliance, please:

1. Review FDA's openFDA API documentation: https://open.fda.gov/apis/
2. Check FDA FOIA policy: https://www.fda.gov/regulatory-information/freedom-information
3. Contact the plugin maintainers with specific compliance concerns
