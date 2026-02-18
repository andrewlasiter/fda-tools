# FDA User-Agent Quick Reference

## TL;DR

```python
from fda_http import FDA_API_HEADERS, FDA_WEBSITE_HEADERS

# For api.fda.gov (device classification, 510(k) search, etc.):
import requests
requests.get('https://api.fda.gov/...', headers=FDA_API_HEADERS)

# For accessdata.fda.gov (PDF downloads, database files):
requests.get('https://accessdata.fda.gov/...', headers=FDA_WEBSITE_HEADERS)
```

## Decision Tree

```
Is your endpoint on api.fda.gov?
│
├── YES → Use FDA_API_HEADERS
│         (Honest UA: "FDA-Plugin/5.36.0")
│
└── NO → Is it a PDF download from accessdata.fda.gov?
          │
          ├── YES → Use FDA_WEBSITE_HEADERS
          │         (Browser UA for CDN compatibility)
          │
          └── NO → Default to FDA_API_HEADERS
                    (When in doubt, be honest)
```

## Header Contents

### FDA_API_HEADERS
```python
{
    'User-Agent': 'FDA-Plugin/5.36.0',
    'Accept': 'application/json'
}
```

### FDA_WEBSITE_HEADERS
```python
{
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}
```

## Which Scripts Use Which?

| Script                         | Headers              | Why                                    |
|--------------------------------|---------------------|----------------------------------------|
| `fda_api_client.py`            | `FDA_API_HEADERS`   | openFDA API wrapper                    |
| `knowledge_based_generator.py` | `FDA_API_HEADERS`   | Device classification API              |
| `batchfetch.py`                | `FDA_WEBSITE_HEADERS` | PDF/database downloads from CDN      |
| `predicate_extractor.py`       | `FDA_WEBSITE_HEADERS` | Database file downloads (pmn96cur.zip)|

## Using create_session()

### New API (Recommended)
```python
from fda_http import create_session

# For API calls:
api_session = create_session(purpose='api')
response = api_session.get('https://api.fda.gov/device/classification.json')

# For PDF downloads:
pdf_session = create_session(purpose='website')
response = pdf_session.get('https://accessdata.fda.gov/cdrh_docs/pdf24/K240001.pdf')
```

### Old API (Deprecated but still works)
```python
from fda_http import create_session

# For API calls:
api_session = create_session(api_mode=True)

# For PDF downloads:
pdf_session = create_session(api_mode=False)
```

## Configuration Override

Create `~/.claude/fda-tools.config.toml`:

```toml
[http]
# Override UA for all requests:
user_agent_override = "MyCompany-FDATools/2.0"

# Force honest UA everywhere (may break PDF downloads):
honest_ua_only = false
```

## Common Mistakes

### ❌ Wrong: Using browser UA for API calls
```python
# DON'T DO THIS:
requests.get('https://api.fda.gov/device/classification.json',
             headers=FDA_WEBSITE_HEADERS)
```

### ✅ Right: Using honest UA for API calls
```python
# DO THIS:
requests.get('https://api.fda.gov/device/classification.json',
             headers=FDA_API_HEADERS)
```

### ❌ Wrong: Using honest UA for PDF downloads
```python
# DON'T DO THIS (will get HTTP 403):
requests.get('https://accessdata.fda.gov/cdrh_docs/pdf24/K240001.pdf',
             headers=FDA_API_HEADERS)
```

### ✅ Right: Using browser UA for PDF downloads
```python
# DO THIS (technical necessity):
requests.get('https://accessdata.fda.gov/cdrh_docs/pdf24/K240001.pdf',
             headers=FDA_WEBSITE_HEADERS)
```

## Testing Your Code

```bash
# Check what UA your code will use:
python3 -c "
from fda_http import FDA_API_HEADERS, FDA_WEBSITE_HEADERS
print('API UA:', FDA_API_HEADERS['User-Agent'])
print('Website UA:', FDA_WEBSITE_HEADERS['User-Agent'][:50])
"
```

## Full Documentation

See `/plugins/fda-tools/scripts/FDA_HTTP_CONFIGURATION.md` for:
- Detailed compliance rationale
- Technical explanation of CDN behavior
- Configuration file format
- Troubleshooting guide
- FDA Terms of Service compliance details
