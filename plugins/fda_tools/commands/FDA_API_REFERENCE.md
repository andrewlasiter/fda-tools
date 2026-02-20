# FDA API Reference Guide

> **Purpose:** Centralized reference for openFDA API access via FDAClient
> **Created:** 2026-02-20 (FDA-114)
> **Replaces:** Duplicated urllib.request boilerplate across 15+ commands

---

## Quick Start

```python
from fda_tools.scripts.fda_api_client import FDAClient

# Initialize client (auto-loads API key from env or settings)
client = FDAClient()

# Get a specific 510(k)
result = client.get_510k("K192345")

# Get all clearances for a product code
clearances = client.get_clearances("DQY", limit=100)

# Search PMAs
pmas = client.search_pma(product_code="OVE", applicant="Medtronic")
```

---

## Available Methods

### 510(k) Clearances

**Single 510(k):**
```python
result = client.get_510k(k_number)
# Returns: Dict with full 510(k) record
```

**Batch 510(k)s:**
```python
results = client.batch_510k(["K192345", "K183456"], limit=100)
# Returns: List[Dict] - Up to 100 records per K-number
```

**All clearances for product code:**
```python
clearances = client.get_clearances(
    product_code="DQY",
    limit=100,
    sort="decision_date:desc"
)
# Returns: List[Dict] - Most recent 100 clearances
```

### Classification & Product Codes

**Get classification info:**
```python
classification = client.get_classification(product_code="DQY")
# Returns: Dict with regulation number, device name, class, etc.
```

### MAUDE Adverse Events

**Get events for product code:**
```python
events = client.get_events(
    product_code="DQY",
    count="event_type.exact",  # Optional: group by event type
    limit=100
)
# Returns: List[Dict] - MAUDE event records
```

### Recalls

**Get recalls for product code:**
```python
recalls = client.get_recalls(product_code="DQY", limit=10)
# Returns: List[Dict] - Recall records
```

### PMA Data

**Single PMA:**
```python
pma = client.get_pma(pma_number="P120001")
# Returns: Dict with PMA record
```

**PMA supplements:**
```python
supplements = client.get_pma_supplements(pma_number="P120001", limit=50)
# Returns: List[Dict] - PMA supplement records
```

**Search PMAs:**
```python
results = client.search_pma(
    product_code="OVE",
    applicant="Medtronic",
    device_name="spinal fusion",
    limit=50
)
# Returns: List[Dict] - Matching PMAs
```

**Batch PMAs:**
```python
results = client.batch_pma(["P120001", "P150002"], limit=50)
# Returns: List[Dict] - Up to 50 records per PMA
```

### UDI (Unique Device Identification)

**Search UDI database:**
```python
udis = client.get_udi(
    product_code="DQY",
    company_name="Abbott",
    di="00884838003471",  # Device Identifier
    limit=10
)
# Returns: List[Dict] - UDI/GUDID records
```

---

## Features

### Automatic Caching (7-day TTL)
- All API responses cached locally (`~/fda-510k-data/api_cache/`)
- SHA-256 integrity verification (GAP-011)
- Atomic writes with temp + replace pattern

### Rate Limiting
- **Unauthenticated:** 240 requests/minute
- **With API key:** 1000 requests/minute
- Thread-safe token bucket implementation
- Shared across all commands (FDA-20)

### Retry Logic
- Max 5 attempts with exponential backoff
- Handles 429 (rate limit) and 5xx (server errors)
- Jittered delays to prevent thundering herd
- Degraded mode on total failure

### Error Handling
```python
try:
    result = client.get_510k("K999999")  # Invalid K-number
except Exception as e:
    # Client returns graceful error dict:
    # {"error": "Not found", "k_number": "K999999"}
    pass
```

---

## Configuration

### API Key (Optional, Recommended)

Set via environment variable:
```bash
export OPENFDA_API_KEY="your-key-here"
```

Or in `~/.claude/fda-tools.local.md`:
```markdown
openfda_api_key: your-key-here
```

Get an API key: https://open.fda.gov/apis/authentication/

### Custom Cache Directory

```python
client = FDAClient(cache_dir="/custom/cache/path")
```

### Rate Limit Override

```python
client = FDAClient(rate_limit_override=500)  # 500 req/min
```

---

## Migration from urllib.request

**OLD (raw urllib):**
```python
import urllib.request
import urllib.parse
import json

url = f"https://api.fda.gov/device/510k.json?search=k_number:{k_number}"
req = urllib.request.Request(url, headers={"User-Agent": "..."})
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read())
    results = data.get("results", [])
```

**NEW (FDAClient):**
```python
from fda_tools.scripts.fda_api_client import FDAClient

client = FDAClient()
result = client.get_510k(k_number)
# Results cached, rate-limited, with automatic retry
```

**Benefits:**
- ✅ No manual URL construction
- ✅ No duplicate error handling
- ✅ Consistent rate limiting across all commands
- ✅ Automatic caching (7-day TTL)
- ✅ Exponential backoff retry
- ✅ SHA-256 integrity verification
- ✅ Thread-safe
- ✅ Single point for TLS verification (SEC-04 fix)

---

## Advanced Usage

### Custom SSL Context

```python
import ssl
context = ssl.create_default_context()
# Client automatically uses secure TLS 1.2+ settings
```

### Audit Log Access

```python
client = FDAClient()
# ... make API calls ...
stats = client._stats
# {"hits": 15, "misses": 3, "errors": 0, "corruptions": 0}
```

### Cache Invalidation

```bash
# Clear all cache
rm -rf ~/fda-510k-data/api_cache/*

# Clear specific endpoint
rm ~/fda-510k-data/api_cache/510k_*
```

---

## Related Documentation

- openFDA Device API: https://open.fda.gov/apis/device/
- Rate limiting: `lib/rate_limiter.py`
- Cache integrity: `lib/cache_integrity.py`
- Cross-process rate limiting: `lib/cross_process_rate_limiter.py`

---

**Migration Status (FDA-114):**
- ✅ FDAClient implemented with full feature set
- ✅ Reference guide created
- 📋 Commands should reference this guide instead of duplicating urllib code
- 📋 15 commands identified for cleanup (see FDA-114 in Linear)
