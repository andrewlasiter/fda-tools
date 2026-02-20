# Rate Limiter Migration Guide (CODE-001)

This guide helps you migrate existing code to use the consolidated rate limiting system.

## Overview

The FDA Tools plugin now has a unified rate limiting system with two complementary implementations:

- **`lib/rate_limiter.py`** - Thread-safe, in-process (recommended for most use cases)
- **`lib/cross_process_rate_limiter.py`** - Cross-process coordination (for concurrent processes)

## Migration Checklist

- [ ] Identify all rate limiting code (see "Finding Rate Limiting Code" below)
- [ ] Choose appropriate rate limiter (in-process vs cross-process)
- [ ] Replace manual delays with rate limiter calls
- [ ] Update configuration to use centralized config
- [ ] Add monitoring and statistics collection
- [ ] Test thoroughly

## Finding Rate Limiting Code

### 1. Search for time.sleep() calls

```bash
cd plugins/fda-tools
grep -r "time\.sleep" scripts/*.py lib/*.py
```

### 2. Search for custom rate limiting

```bash
grep -r -i "rate.*limit\|throttle\|delay" scripts/*.py lib/*.py
```

### 3. Check for manual timestamp tracking

```bash
grep -r "last_request\|last_call\|request_time" scripts/*.py lib/*.py
```

## Common Migration Patterns

### Pattern 1: Simple Delay Between Requests

**Before:**
```python
import time

for item in items:
    process_item(item)
    time.sleep(0.5)  # 2 requests per second
```

**After:**
```python
from lib.rate_limiter import RateLimiter

limiter = RateLimiter(requests_per_minute=120)  # 2 req/sec

for item in items:
    limiter.acquire()
    process_item(item)
```

**Benefits:**
- Automatic burst handling
- Statistics tracking
- Configurable limits
- Thread-safe

### Pattern 2: Manual Rate Limiting with Timestamps

**Before:**
```python
import time

class APIClient:
    def __init__(self):
        self.last_request_time = 0
        self.min_interval = 0.5  # 2 req/sec

    def make_request(self, endpoint):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
        return requests.get(endpoint)
```

**After:**
```python
from lib.rate_limiter import RateLimiter

class APIClient:
    def __init__(self):
        self.limiter = RateLimiter(requests_per_minute=120)

    def make_request(self, endpoint):
        self.limiter.acquire()
        return requests.get(endpoint)
```

**Benefits:**
- Simpler code (50% less code)
- No manual timestamp management
- Automatic thread safety
- Built-in statistics

### Pattern 3: Thread-Safe Rate Limiting

**Before:**
```python
import time
import threading

class APIClient:
    def __init__(self):
        self.last_request_time = 0
        self.lock = threading.Lock()

    def make_request(self, endpoint):
        with self.lock:
            elapsed = time.time() - self.last_request_time
            if elapsed < 0.5:
                time.sleep(0.5 - elapsed)
            self.last_request_time = time.time()
        return requests.get(endpoint)
```

**After:**
```python
from lib.rate_limiter import RateLimiter

class APIClient:
    def __init__(self):
        self.limiter = RateLimiter(requests_per_minute=120)

    def make_request(self, endpoint):
        self.limiter.acquire()
        return requests.get(endpoint)
```

**Benefits:**
- Built-in thread safety
- No manual lock management
- Better performance (token bucket vs simple lock)

### Pattern 4: Per-Endpoint Rate Limiting

**Before:**
```python
import time

class APIClient:
    def __init__(self):
        self.last_fda_request = 0
        self.last_pubmed_request = 0

    def fetch_fda(self, query):
        elapsed = time.time() - self.last_fda_request
        if elapsed < 0.25:  # 4 req/sec
            time.sleep(0.25 - elapsed)
        self.last_fda_request = time.time()
        return requests.get(f"https://api.fda.gov/device/510k.json?search={query}")

    def fetch_pubmed(self, query):
        elapsed = time.time() - self.last_pubmed_request
        if elapsed < 0.33:  # 3 req/sec
            time.sleep(0.33 - elapsed)
        self.last_pubmed_request = time.time()
        return requests.get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?term={query}")
```

**After:**
```python
from lib.rate_limiter import RateLimiter

class APIClient:
    def __init__(self):
        self.limiters = {
            'fda': RateLimiter(requests_per_minute=240),     # 4 req/sec
            'pubmed': RateLimiter(requests_per_minute=180),  # 3 req/sec
        }

    def fetch_fda(self, query):
        self.limiters['fda'].acquire()
        return requests.get(f"https://api.fda.gov/device/510k.json?search={query}")

    def fetch_pubmed(self, query):
        self.limiters['pubmed'].acquire()
        return requests.get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?term={query}")
```

**Benefits:**
- Independent rate limits per endpoint
- Cleaner separation of concerns
- Statistics per endpoint

### Pattern 5: Exponential Backoff on Errors

**Before:**
```python
import time

def fetch_with_retry(url, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            if response.status_code == 429:
                delay = (2 ** attempt)  # Exponential backoff
                time.sleep(delay)
                continue
            return response
        except requests.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    return None
```

**After:**
```python
from lib.rate_limiter import RateLimiter, RetryPolicy

limiter = RateLimiter(requests_per_minute=240)
retry_policy = RetryPolicy(max_attempts=5, base_delay=1.0, max_delay=60.0, jitter=True)

def fetch_with_retry(url):
    for attempt in range(retry_policy.max_attempts):
        limiter.acquire()

        try:
            response = requests.get(url)

            if response.status_code == 429:
                delay = retry_policy.get_retry_delay(attempt, response.headers)
                if delay is None:
                    break  # Max attempts exceeded
                time.sleep(delay)
                continue

            return response

        except requests.RequestException as e:
            delay = retry_policy.get_retry_delay(attempt)
            if delay is None:
                raise
            time.sleep(delay)

    return None
```

**Benefits:**
- Respects Retry-After headers
- Configurable jitter to prevent thundering herd
- Better error handling

### Pattern 6: Cross-Process Coordination

**Before (Problem: Each process has separate limits):**
```python
# Process 1 (batchfetch.py)
import time
for item in items:
    process(item)
    time.sleep(0.25)  # 4 req/sec

# Process 2 (change_detector.py)
import time
for item in items:
    process(item)
    time.sleep(0.25)  # 4 req/sec

# Problem: Total = 8 req/sec (exceeds API limit of 4 req/sec!)
```

**After (Solution: Shared rate limit):**
```python
# Process 1 (batchfetch.py)
from lib.cross_process_rate_limiter import CrossProcessRateLimiter

limiter = CrossProcessRateLimiter(has_api_key=True)  # 240 req/min shared

for item in items:
    limiter.acquire()
    process(item)

# Process 2 (change_detector.py)
from lib.cross_process_rate_limiter import CrossProcessRateLimiter

limiter = CrossProcessRateLimiter(has_api_key=True)  # Same shared limit

for item in items:
    limiter.acquire()
    process(item)

# Both processes share 240 req/min ✓
```

**Benefits:**
- True cross-process coordination
- No API limit violations
- Automatic state sharing via file locks

## Using Decorators and Context Managers

### Decorator Pattern (CODE-001)

**Before:**
```python
limiter = RateLimiter(requests_per_minute=240)

def fetch_data(k_number):
    limiter.acquire()
    return requests.get(f"https://api.fda.gov/device/510k.json?search=k_number:{k_number}")
```

**After:**
```python
from lib.rate_limiter import RateLimiter, rate_limited

limiter = RateLimiter(requests_per_minute=240)

@rate_limited(limiter, tokens=1, timeout=30)
def fetch_data(k_number):
    return requests.get(f"https://api.fda.gov/device/510k.json?search=k_number:{k_number}")
```

**Benefits:**
- Cleaner function body
- Automatic error handling on timeout
- Preserves function metadata

### Context Manager Pattern (CODE-001)

**Before:**
```python
limiter = RateLimiter(requests_per_minute=240)

def process_batch(items):
    for item in items[:5]:
        limiter.acquire()
        process(item)
```

**After:**
```python
from lib.rate_limiter import RateLimiter, RateLimitContext

limiter = RateLimiter(requests_per_minute=240)

def process_batch(items):
    with RateLimitContext(limiter, tokens=5, timeout=60):
        for item in items[:5]:
            process(item)
```

**Benefits:**
- Clear scope for rate-limited operations
- Automatic cleanup
- Better error handling

## Configuration Migration

### Before: Hard-coded Limits

```python
# scripts/fda_api_client.py
limiter = RateLimiter(requests_per_minute=240)  # Hard-coded

# scripts/pubmed_client.py
limiter = RateLimiter(requests_per_minute=180)  # Hard-coded
```

### After: Centralized Configuration

```toml
# config.toml
[rate_limiting]
rate_limit_openfda = 240
rate_limit_pubmed = 180
rate_limit_pdf_download = 2
```

```python
# scripts/fda_api_client.py
from lib.config import get_config
from lib.rate_limiter import RateLimiter

config = get_config()
limiter = RateLimiter(
    requests_per_minute=config.get_int('rate_limiting.rate_limit_openfda', 240)
)

# scripts/pubmed_client.py
from lib.config import get_config
from lib.rate_limiter import RateLimiter

config = get_config()
limiter = RateLimiter(
    requests_per_minute=config.get_int('rate_limiting.rate_limit_pubmed', 180)
)
```

**Benefits:**
- Single source of truth
- Easy to adjust limits without code changes
- Environment-specific configuration

## Testing Migration

### Testing with Rate Limiters

```python
import pytest
from lib.rate_limiter import RateLimiter

def test_api_call_with_rate_limiting():
    """Test that API calls respect rate limits."""
    limiter = RateLimiter(requests_per_minute=60)  # 1 req/sec

    # First call should be instant
    start = time.time()
    limiter.acquire()
    make_api_call()
    elapsed = time.time() - start
    assert elapsed < 0.1

    # Drain bucket
    for _ in range(59):
        limiter.try_acquire()

    # Next call should block for ~1 second
    start = time.time()
    limiter.acquire(timeout=2)
    make_api_call()
    elapsed = time.time() - start
    assert 0.5 < elapsed < 1.5
```

### Mocking for Unit Tests

```python
from unittest.mock import Mock, patch
from lib.rate_limiter import RateLimiter

def test_without_rate_limiting():
    """Test logic without actual rate limiting delay."""
    with patch.object(RateLimiter, 'acquire', return_value=True):
        limiter = RateLimiter(requests_per_minute=240)
        result = make_api_call_with_limiter(limiter)
        assert result is not None
        # No actual delay occurred
```

## Statistics and Monitoring

### Adding Statistics Collection

**Before: No Visibility**
```python
for item in items:
    time.sleep(0.5)
    process(item)
# No way to know how long we waited or if limits were hit
```

**After: Full Statistics**
```python
from lib.rate_limiter import RateLimiter

limiter = RateLimiter(requests_per_minute=120)

for item in items:
    limiter.acquire()
    process(item)

# Get detailed statistics
stats = limiter.get_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Requests blocked: {stats['total_waits']} ({stats['wait_percentage']:.1f}%)")
print(f"Average wait: {stats['avg_wait_time_seconds']:.3f}s")
print(f"Rate limit warnings: {stats['rate_limit_warnings']}")
```

### Integration with Monitoring System (FDA-190)

```python
from lib.monitoring import track_api_call
from lib.rate_limiter import RateLimiter

limiter = RateLimiter(requests_per_minute=240)

@track_api_call(endpoint="openfda", operation="get_510k")
def fetch_510k(k_number):
    limiter.acquire()
    return make_api_call(k_number)

# Metrics automatically exported to Prometheus:
# - api_request_duration_seconds
# - api_requests_total
# - api_rate_limit_wait_seconds
```

## File-by-File Migration Examples

### scripts/batchfetch.py

**Changes:**
```python
# Before (line ~850)
import time
for k_number in k_numbers:
    fetch_data(k_number)
    time.sleep(0.25)  # 4 req/sec

# After
from lib.rate_limiter import RateLimiter
limiter = RateLimiter(requests_per_minute=240)

for k_number in k_numbers:
    limiter.acquire()
    fetch_data(k_number)
```

### scripts/external_data_hub.py

**Changes:**
```python
# Before
def fetch_pubmed_data(query):
    time.sleep(0.33)  # 3 req/sec
    return make_request(query)

# After
from lib.rate_limiter import RateLimiter, rate_limited

pubmed_limiter = RateLimiter(requests_per_minute=180)

@rate_limited(pubmed_limiter)
def fetch_pubmed_data(query):
    return make_request(query)
```

### scripts/pma_ssed_cache.py

**Changes:**
```python
# Before
for pdf_url in pdf_urls:
    download_pdf(pdf_url)
    time.sleep(30)  # 30s between PDF downloads

# After
from lib.rate_limiter import RateLimiter

pdf_limiter = RateLimiter(requests_per_minute=2)  # 2 req/min = 30s delay

for pdf_url in pdf_urls:
    pdf_limiter.acquire()
    download_pdf(pdf_url)
```

## Troubleshooting Common Issues

### Issue 1: "Rate limit acquisition timeout"

**Problem:**
```python
limiter = RateLimiter(requests_per_minute=240)
limiter.acquire(timeout=1)  # Times out
```

**Diagnosis:**
```python
stats = limiter.get_stats()
print(f"Current tokens: {stats['current_tokens']}")
print(f"Total requests: {stats['total_requests']}")
```

**Solutions:**
1. Increase timeout: `limiter.acquire(timeout=30)`
2. Use try_acquire() and handle failure
3. Check if requests_per_minute is too low

### Issue 2: Cross-process limiter not coordinating

**Problem:**
Both processes seem to ignore the shared limit.

**Diagnosis:**
```python
limiter = CrossProcessRateLimiter(has_api_key=True)
health = limiter.health_check()
print(health)
```

**Solutions:**
1. Ensure all processes use same data_dir
2. Check file permissions on lock/state files
3. Verify fcntl.flock support (Unix/Linux only)

### Issue 3: Too many rate limit warnings

**Problem:**
Seeing frequent "APPROACHING RATE LIMIT" warnings.

**Diagnosis:**
```python
stats = limiter.get_stats()
print(f"Warnings: {stats['rate_limit_warnings']}")
print(f"Utilization: {stats['wait_percentage']}%")
```

**Solutions:**
1. Reduce requests_per_minute by 10-20%
2. Add burst_capacity if you have legitimate bursts
3. Consider using multiple API keys (round-robin)

## Rollback Plan

If you encounter issues after migration:

1. **Temporary Rollback:**
```python
# Quick rollback: comment out new code, restore old
# limiter = RateLimiter(requests_per_minute=240)
# limiter.acquire()
time.sleep(0.25)  # Temporary: restore old behavior
```

2. **Partial Rollback:**
Keep rate limiter but disable statistics:
```python
limiter = RateLimiter(requests_per_minute=240)
limiter.acquire()
# Don't call get_stats() or update_from_headers()
```

3. **Full Rollback:**
```bash
git revert <commit-hash>
```

## Success Criteria

Migration is successful when:

- [ ] All manual `time.sleep()` delays removed
- [ ] All API calls use rate limiters
- [ ] Configuration centralized in config.toml
- [ ] Statistics collection enabled
- [ ] Tests passing (100% coverage)
- [ ] No API rate limit violations in production
- [ ] Cross-process coordination verified (if applicable)
- [ ] Documentation updated

## Next Steps

After migration:

1. **Monitor statistics for 1 week**
   - Check `limiter.get_stats()` daily
   - Watch for rate limit warnings
   - Tune limits if needed

2. **Optimize based on data**
   - If `wait_percentage > 30%`, reduce rate limit
   - If `wait_percentage < 5%`, consider increasing
   - Adjust burst_capacity for legitimate bursts

3. **Integrate with monitoring (FDA-190)**
   - Export metrics to Prometheus
   - Set up alerts for high utilization
   - Track rate limit trends

4. **Document custom configurations**
   - Record any endpoint-specific limits
   - Document why limits were chosen
   - Create runbooks for adjusting limits

## Support

For help with migration:

1. Check this guide first
2. Review examples in `docs/RATE_LIMITER_README.md`
3. Check test files for usage examples
4. Run health checks: `python -m lib.cross_process_rate_limiter --health-check`

## Related Documentation

- [Rate Limiter README](./RATE_LIMITER_README.md) - Complete API reference
- [Configuration Guide](./CONFIGURATION_MIGRATION_GUIDE.md) - Config system (FDA-180)
- [Monitoring Integration](./MONITORING_README.md) - Metrics and monitoring (FDA-190)
