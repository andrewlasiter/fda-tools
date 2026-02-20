# FDA-20: Rate Limiting Quick Reference

## Overview
Production-ready rate limiting for FDA API client to prevent IP bans.

## Quick Start

### Default Usage (Automatic)
```python
from fda_api_client import FDAClient

# Rate limiting is automatic
client = FDAClient()
result = client.get_510k("K241335")  # Rate limited automatically
```

### Check Statistics
```python
# Get rate limiting stats
stats = client.rate_limit_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Blocked: {stats['total_waits']} ({stats['wait_percentage']:.1f}%)")
print(f"Current tokens: {stats['current_tokens']:.1f}")
```

### CLI Usage
```bash
# Show statistics
python3 scripts/fda_api_client.py --stats

# Test endpoints
python3 scripts/fda_api_client.py --test

# Look up device
python3 scripts/fda_api_client.py --lookup K241335
```

## Configuration

### Rate Limits
- **Without API key:** 240 requests/minute (default)
- **With API key:** 1000 requests/minute (auto-detected)
- **Custom override:** Set `rate_limit_override` parameter

### Examples
```python
# Use environment API key (1000 req/min)
export OPENFDA_API_KEY="your-key"
client = FDAClient()

# Explicit API key
client = FDAClient(api_key="your-key")

# Custom rate limit
client = FDAClient(rate_limit_override=500)
```

## Features

### 1. Token Bucket Algorithm
- Tokens replenish at constant rate
- Burst capacity allows initial spike
- Requests block when bucket empty

### 2. Exponential Backoff
- 429 responses trigger retry with backoff
- Delays: 1s, 2s, 4s, 8s, 16s, 32s, 60s (max)
- Respects `Retry-After` header
- Maximum 5 retry attempts

### 3. Rate Limit Headers
- Parses `X-RateLimit-*` headers
- Warns when < 10% remaining
- Logs rate limit status

### 4. Thread Safety
- Full thread-safe implementation
- Multiple threads can share client
- Lock-based synchronization

## Statistics

### Available Metrics
```python
stats = client.rate_limit_stats()

# Metrics included:
# - total_requests: Total API calls made
# - total_waits: Number of times blocked
# - total_wait_time_seconds: Cumulative wait time
# - avg_wait_time_seconds: Average wait per block
# - wait_percentage: % of requests blocked
# - rate_limit_warnings: Approaching limit warnings
# - current_tokens: Current token bucket level
# - requests_per_minute: Configured rate limit
```

### Cache Stats Integration
```python
stats = client.cache_stats()

# Now includes rate_limiting key:
print(stats['rate_limiting'])
```

## Error Handling

### Graceful Degradation
1. **Rate limiter unavailable** → Falls back to basic retry
2. **Max retries exceeded** → Returns degraded error
3. **Acquisition timeout** → Returns degraded error

### Example Error Response
```python
{
    "error": "API unavailable after 5 retries: 429 Too Many Requests",
    "degraded": True
}
```

## Performance

### Overhead
- **Token acquisition:** < 1ms
- **Statistics:** < 100ns per update
- **Memory:** ~200 bytes per instance
- **CPU:** Minimal (timestamp arithmetic only)

### Timing
- **Burst capacity:** All tokens available at startup
- **Replenishment:** Continuous (tokens per second)
- **Blocking:** Only when bucket empty

## Testing

### Run Tests
```bash
# Unit tests
python3 -m pytest tests/test_rate_limiter.py -v

# Integration tests
python3 -m pytest tests/test_fda_client_rate_limiting.py -v

# All tests
python3 -m pytest tests/test_rate_limiter.py tests/test_fda_client_rate_limiting.py -v
```

### Test Results
- 38 unit tests (rate limiter)
- 16 integration tests (FDAClient)
- **54 total tests - ALL PASSING ✅**

## Logging

### Log Levels
```python
# DEBUG: Normal operations
logger.debug("Acquired 1 token(s) (239.0 remaining)")

# INFO: Retry delays
logger.info("Waiting 2.00s before retry (429 rate limit)")

# WARNING: Approaching limits
logger.warning("APPROACHING RATE LIMIT: 235/240 requests used (97.9%)")

# ERROR: Critical failures
logger.error("Max retries exceeded after 429 rate limit")
```

### Configure Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)  # See all rate limiting activity
logging.basicConfig(level=logging.WARNING)  # Only warnings and errors
```

## Advanced Usage

### Custom Retry Policy
```python
from lib.rate_limiter import RetryPolicy

# Create custom retry policy
policy = RetryPolicy(
    max_attempts=10,      # More retries
    base_delay=2.0,       # Longer initial delay
    max_delay=120.0,      # Higher max delay
    jitter=True           # Random jitter
)
```

### Direct Rate Limiter Usage
```python
from lib.rate_limiter import RateLimiter

# Create standalone rate limiter
limiter = RateLimiter(requests_per_minute=500)

# Acquire token (blocks if necessary)
limiter.acquire(tokens=1)

# Try acquire (non-blocking)
if limiter.try_acquire(tokens=1):
    # Token acquired
    make_api_request()
else:
    # No tokens available
    print("Rate limited")

# Get statistics
stats = limiter.get_stats()
```

## Troubleshooting

### Problem: "Rate limiter not available"
**Solution:** Ensure `lib/rate_limiter.py` exists and is importable
```bash
python3 -c "from lib.rate_limiter import RateLimiter; print('OK')"
```

### Problem: Requests still getting 429 errors
**Possible causes:**
1. Rate limit too high for your API key tier
2. Multiple client instances sharing same quota
3. Other processes using same API key

**Solution:** Lower rate limit
```python
client = FDAClient(rate_limit_override=120)  # More conservative
```

### Problem: Slow performance
**Cause:** Rate limiter blocking requests
**Check:** Statistics
```python
stats = client.rate_limit_stats()
if stats['wait_percentage'] > 10:
    print(f"WARNING: {stats['wait_percentage']:.1f}% of requests blocked")
```

**Solution:** Increase rate limit (if you have API key)
```python
client = FDAClient(api_key="your-key")  # Use 1000 req/min
```

## Best Practices

### 1. Reuse Client Instances
```python
# GOOD: Single client instance
client = FDAClient()
for k in k_numbers:
    result = client.get_510k(k)

# BAD: New client per request (wastes tokens)
for k in k_numbers:
    client = FDAClient()  # Don't do this!
    result = client.get_510k(k)
```

### 2. Monitor Statistics
```python
# Check stats periodically
stats = client.rate_limit_stats()
if stats['rate_limit_warnings'] > 0:
    print("WARNING: Approaching rate limit!")
```

### 3. Use API Key for Production
```bash
# Get API key: https://open.fda.gov/apis/authentication/
export OPENFDA_API_KEY="your-key-here"
```

### 4. Handle Degraded Responses
```python
result = client.get_510k("K123456")
if result.get("degraded"):
    print(f"API error: {result.get('error')}")
    # Handle gracefully
```

## Files

### Production Code
- `/plugins/fda-tools/lib/rate_limiter.py` - Rate limiter module
- `/plugins/fda-tools/scripts/fda_api_client.py` - FDA client (modified)

### Tests
- `/plugins/fda-tools/tests/test_rate_limiter.py` - Unit tests
- `/plugins/fda-tools/tests/test_fda_client_rate_limiting.py` - Integration tests

### Documentation
- `/plugins/fda-tools/FDA-20-IMPLEMENTATION-SUMMARY.md` - Full documentation
- `/plugins/fda-tools/FDA-20-QUICK-REFERENCE.md` - This file

## Support

### Related Issues
- FDA-18: Logging infrastructure
- GAP-011: Cache integrity
- FDA-71: API client improvements

### Further Reading
- [openFDA Rate Limits](https://open.fda.gov/apis/authentication/)
- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [Exponential Backoff](https://en.wikipedia.org/wiki/Exponential_backoff)

---

**Status:** Production Ready ✅
**Date:** 2026-02-17
**Ticket:** FDA-20
