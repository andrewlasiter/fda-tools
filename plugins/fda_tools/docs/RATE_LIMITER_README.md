# Rate Limiting Guide (CODE-001)

Comprehensive guide to rate limiting in the FDA Tools plugin.

## Overview

The FDA Tools plugin provides two complementary rate limiting implementations:

1. **`lib/rate_limiter.py`** - Thread-safe, in-process rate limiting
   - Token bucket algorithm
   - Perfect for single-process applications
   - Low overhead, fast performance
   - Statistics and monitoring built-in

2. **`lib/cross_process_rate_limiter.py`** - Cross-process rate limiting
   - File-based coordination using fcntl.flock
   - Sliding window algorithm
   - Essential for concurrent processes (e.g., multiple batchfetch runs)
   - Shared state across all processes

## Quick Start

### Basic Usage (In-Process)

```python
from lib.rate_limiter import RateLimiter

# Create limiter: 240 requests per minute
limiter = RateLimiter(requests_per_minute=240)

# Blocking acquire (waits until tokens available)
limiter.acquire()
make_api_call()

# Non-blocking acquire (returns False if tokens unavailable)
if limiter.try_acquire():
    make_api_call()
else:
    print("Rate limit exceeded, try later")
```

### Cross-Process Usage

```python
from lib.cross_process_rate_limiter import CrossProcessRateLimiter

# Create cross-process limiter
limiter = CrossProcessRateLimiter(has_api_key=True)  # 240 req/min

# Acquire (blocks until safe)
limiter.acquire()
make_api_call()

# Check status across all processes
status = limiter.get_status()
print(f"Requests in last minute: {status['requests_last_minute']}")
```

### Decorator Pattern

```python
from lib.rate_limiter import RateLimiter, rate_limited

limiter = RateLimiter(requests_per_minute=240)

@rate_limited(limiter, tokens=1, timeout=30.0)
def fetch_510k_data(k_number):
    """Rate-limited API call."""
    return requests.get(f"https://api.fda.gov/device/510k.json?search=k_number:{k_number}")

# Automatically rate-limited
data = fetch_510k_data("K241335")
```

### Context Manager Pattern

```python
from lib.rate_limiter import RateLimiter, RateLimitContext

limiter = RateLimiter(requests_per_minute=240)

# Rate limit a code block
with RateLimitContext(limiter, tokens=5, timeout=60):
    # Make up to 5 API calls
    for k_number in k_numbers[:5]:
        fetch_data(k_number)
```

## Configuration Integration

The rate limiter integrates with the centralized config system (FDA-180):

```toml
# config.toml
[rate_limiting]
enable_cross_process = true
enable_thread_safe = true
lock_timeout = 30  # seconds

# Rate limits by endpoint
rate_limit_openfda = 240  # per minute
rate_limit_pubmed = 3     # per second
rate_limit_pdf_download = 2  # per minute
```

### Loading from Config

```python
from lib.config import get_config
from lib.rate_limiter import RateLimiter

config = get_config()
rate_limit = config.get_int('rate_limiting.rate_limit_openfda', 240)

limiter = RateLimiter(requests_per_minute=rate_limit)
```

## Advanced Features

### 1. Burst Handling

```python
# Allow burst of up to 120 requests, then throttle to 60/min
limiter = RateLimiter(
    requests_per_minute=60,
    burst_capacity=120
)

# Can immediately consume 120 tokens
for i in range(120):
    limiter.acquire()
    make_api_call()

# After burst, limited to 60/min (1 per second)
```

### 2. Multiple Token Acquisition

```python
# Acquire 5 tokens for a batch operation
limiter = RateLimiter(requests_per_minute=240)

if limiter.acquire(tokens=5, timeout=10):
    # Process batch of 5 items
    for item in batch[:5]:
        process_item(item)
```

### 3. Rate Limit Header Parsing

```python
import requests

limiter = RateLimiter(requests_per_minute=240)

limiter.acquire()
response = requests.get("https://api.fda.gov/device/510k.json")

# Update limiter based on server's rate limit headers
limiter.update_from_headers(response.headers)

# Check for warnings
stats = limiter.get_stats()
if stats['rate_limit_warnings'] > 0:
    print("WARNING: Approaching rate limit!")
```

### 4. Retry Policy with Exponential Backoff

```python
from lib.rate_limiter import RateLimiter, RetryPolicy
import requests

limiter = RateLimiter(requests_per_minute=240)
retry_policy = RetryPolicy(
    max_attempts=5,
    base_delay=1.0,
    max_delay=60.0,
    jitter=True
)

for attempt in range(retry_policy.max_attempts):
    limiter.acquire()

    try:
        response = requests.get("https://api.fda.gov/device/510k.json")

        if response.status_code == 429:
            # Rate limited - get retry delay
            delay = retry_policy.get_retry_delay(attempt, response.headers)
            if delay is None:
                break  # Max attempts exceeded

            print(f"Rate limited. Waiting {delay:.1f}s...")
            time.sleep(delay)
            continue

        # Success
        data = response.json()
        break

    except requests.RequestException as e:
        delay = retry_policy.get_retry_delay(attempt)
        if delay is None:
            raise
        time.sleep(delay)
```

## Statistics and Monitoring

### Real-time Statistics

```python
limiter = RateLimiter(requests_per_minute=240)

# Make some requests...
for i in range(100):
    limiter.acquire()
    make_api_call()

# Get detailed statistics
stats = limiter.get_stats()

print(f"Total requests: {stats['total_requests']}")
print(f"Requests blocked: {stats['total_waits']} ({stats['wait_percentage']:.1f}%)")
print(f"Average wait time: {stats['avg_wait_time_seconds']:.3f}s")
print(f"Current tokens: {stats['current_tokens']:.1f} / {stats['requests_per_minute']}")
print(f"Rate limit warnings: {stats['rate_limit_warnings']}")
```

### Cross-Process Health Check

```python
limiter = CrossProcessRateLimiter(has_api_key=True)

health = limiter.health_check()

if health['healthy']:
    print(f"✓ Rate limiter healthy")
    print(f"  Utilization: {health['status']['utilization_percent']}%")
    print(f"  Available: {health['status']['available']} requests")
else:
    print(f"✗ Rate limiter unhealthy")
    for warning in health['warnings']:
        print(f"  WARNING: {warning}")
```

### Integration with Monitoring (FDA-190)

```python
from lib.monitoring import track_api_call
from lib.rate_limiter import RateLimiter

limiter = RateLimiter(requests_per_minute=240)

@track_api_call(endpoint="openfda", operation="get_510k")
def fetch_510k(k_number):
    limiter.acquire()
    return make_api_call(k_number)

# Metrics automatically tracked:
# - api_request_duration_seconds
# - api_requests_total
# - api_rate_limit_wait_seconds (from limiter stats)
```

## Migration Guide

### Migrating from time.sleep()

**Before:**
```python
import time

def fetch_data():
    time.sleep(0.5)  # Hard-coded delay
    return make_api_call()
```

**After:**
```python
from lib.rate_limiter import RateLimiter

limiter = RateLimiter(requests_per_minute=120)  # 2 req/sec

def fetch_data():
    limiter.acquire()  # Dynamic rate limiting
    return make_api_call()
```

### Migrating Custom Rate Limiting

**Before:**
```python
import time
from threading import Lock

last_request_time = 0
lock = Lock()

def fetch_data():
    global last_request_time
    with lock:
        elapsed = time.time() - last_request_time
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
        last_request_time = time.time()
    return make_api_call()
```

**After:**
```python
from lib.rate_limiter import RateLimiter

limiter = RateLimiter(requests_per_minute=120)

def fetch_data():
    limiter.acquire()
    return make_api_call()
```

### Migrating to Cross-Process (for Concurrent Scripts)

If you're running multiple processes (e.g., `batchfetch` + `data_refresh_orchestrator`), use the cross-process limiter:

**Before (each process has its own limit):**
```python
# Process 1
limiter1 = RateLimiter(requests_per_minute=240)

# Process 2
limiter2 = RateLimiter(requests_per_minute=240)

# Problem: Total requests = 480/min (exceeds API limit!)
```

**After (shared limit across processes):**
```python
# Process 1
from lib.cross_process_rate_limiter import CrossProcessRateLimiter
limiter = CrossProcessRateLimiter(has_api_key=True)

# Process 2
from lib.cross_process_rate_limiter import CrossProcessRateLimiter
limiter = CrossProcessRateLimiter(has_api_key=True)

# Both processes share the same 240 req/min limit ✓
```

## Best Practices

### 1. Choose the Right Limiter

- **Single process:** Use `RateLimiter` (faster, simpler)
- **Multiple processes:** Use `CrossProcessRateLimiter`
- **Both:** Use `CrossProcessRateLimiter` as fallback

### 2. Set Appropriate Limits

```python
# openFDA API
limiter_fda = RateLimiter(requests_per_minute=240)  # Without API key
limiter_fda_auth = RateLimiter(requests_per_minute=1000)  # With API key

# PubMed API
limiter_pubmed = RateLimiter(requests_per_minute=180)  # 3 req/sec

# PDF downloads (be conservative)
limiter_pdf = RateLimiter(requests_per_minute=2)  # 30s between downloads
```

### 3. Handle Timeouts Gracefully

```python
acquired = limiter.acquire(timeout=30.0)
if not acquired:
    logger.warning("Rate limit timeout - API may be overloaded")
    return {"error": "Rate limit timeout", "degraded": True}
```

### 4. Use Statistics for Tuning

```python
# Run for a while, then check stats
stats = limiter.get_stats()

if stats['wait_percentage'] > 50:
    print("WARNING: More than 50% of requests are waiting")
    print("Consider:")
    print("  - Increasing burst_capacity")
    print("  - Reducing requests_per_minute")
    print("  - Adding more API keys (if available)")
```

### 5. Monitor Cross-Process Utilization

```python
from lib.cross_process_rate_limiter import CrossProcessRateLimiter

limiter = CrossProcessRateLimiter(has_api_key=True)

status = limiter.get_status()
if status['utilization_percent'] > 80:
    logger.warning(
        f"High rate limit utilization: {status['utilization_percent']}% "
        f"({status['available']} requests remaining)"
    )
```

## API Reference

### RateLimiter Class

```python
class RateLimiter:
    def __init__(
        self,
        requests_per_minute: int = 240,
        burst_capacity: Optional[int] = None,
    ):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            burst_capacity: Maximum tokens that can accumulate (default: requests_per_minute)
        """

    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Acquire tokens, blocking until available.

        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum seconds to wait (None = wait forever)

        Returns:
            True if acquired, False if timeout
        """

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking.

        Returns:
            True if acquired, False if insufficient tokens
        """

    def update_from_headers(
        self,
        headers: Dict[str, str],
        warn_threshold: float = 0.1,
    ) -> None:
        """Update limiter based on API response headers.

        Args:
            headers: HTTP response headers
            warn_threshold: Warn when remaining < (threshold * limit)
        """

    def get_stats(self) -> Dict[str, float]:
        """Get rate limiter statistics."""

    def reset_stats(self) -> None:
        """Reset statistics counters."""
```

### CrossProcessRateLimiter Class

```python
class CrossProcessRateLimiter:
    def __init__(
        self,
        has_api_key: bool = True,
        data_dir: Optional[str] = None,
        requests_per_minute: Optional[int] = None,
    ):
        """Initialize cross-process rate limiter.

        Args:
            has_api_key: True = 240 req/min, False = 40 req/min
            data_dir: Directory for lock files (default: ~/fda-510k-data)
            requests_per_minute: Override rate limit
        """

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire permission to make request.

        Args:
            timeout: Maximum seconds to wait (default: 120s)

        Returns:
            True if acquired, False if timeout
        """

    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status across all processes."""

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on rate limiter."""

    def reset(self) -> None:
        """Reset shared rate limit state."""
```

### Helper Functions

```python
def rate_limited(
    limiter: RateLimiter,
    tokens: int = 1,
    timeout: Optional[float] = None,
) -> Callable:
    """Decorator to rate limit function calls."""

class RateLimitContext:
    """Context manager for rate limiting code blocks."""

def calculate_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> float:
    """Calculate exponential backoff delay."""

def parse_retry_after(retry_after_header: Optional[str]) -> Optional[float]:
    """Parse Retry-After header from HTTP response."""
```

## Performance Characteristics

### RateLimiter (In-Process)

- **Overhead:** < 1ms per acquire()
- **Memory:** ~1KB per instance
- **Thread safety:** Full (uses threading.Lock)
- **Burst support:** Yes (configurable)
- **Recommended for:** Single-process applications

### CrossProcessRateLimiter (Cross-Process)

- **Overhead:** 1-5ms per acquire() (file I/O)
- **Memory:** ~2KB per instance + shared JSON file
- **Process safety:** Full (uses fcntl.flock)
- **Burst support:** No (sliding window)
- **Recommended for:** Multi-process applications

## Troubleshooting

### Issue: Rate limit timeouts

```python
# Problem
limiter.acquire(timeout=5)  # Times out frequently

# Solution 1: Increase timeout
limiter.acquire(timeout=30)

# Solution 2: Check status before acquiring
status = limiter.get_status()
if status['available'] == 0:
    print("Rate limit full, wait before retrying")
    time.sleep(status['oldest_request_age_seconds'])
```

### Issue: Cross-process limiter not working

```python
# Check health
limiter = CrossProcessRateLimiter(has_api_key=True)
health = limiter.health_check()

if not health['healthy']:
    print("Issues found:")
    for warning in health['warnings']:
        print(f"  - {warning}")

    # Try reset
    limiter.reset()
```

### Issue: High wait times

```python
# Get statistics
stats = limiter.get_stats()

print(f"Average wait: {stats['avg_wait_time_seconds']:.3f}s")
print(f"Wait percentage: {stats['wait_percentage']:.1f}%")

# If wait percentage > 30%, consider:
# 1. Reducing requests_per_minute
# 2. Increasing burst_capacity
# 3. Using multiple API keys (round-robin)
```

## Testing

### Unit Testing with Rate Limiters

```python
import pytest
from lib.rate_limiter import RateLimiter

def test_api_call_with_rate_limiting():
    """Test API call respects rate limits."""
    limiter = RateLimiter(requests_per_minute=60)

    # First call should be instant
    start = time.time()
    limiter.acquire()
    elapsed = time.time() - start
    assert elapsed < 0.1

    # Drain bucket
    for _ in range(59):
        limiter.try_acquire()

    # Next call should block
    start = time.time()
    limiter.acquire(timeout=2)
    elapsed = time.time() - start
    assert 0.5 < elapsed < 1.5  # Should wait ~1 second
```

### Integration Testing

```python
def test_cross_process_coordination():
    """Test that multiple processes respect shared rate limit."""
    import multiprocessing

    def worker(worker_id, results):
        limiter = CrossProcessRateLimiter(has_api_key=True)
        count = 0
        for _ in range(100):
            if limiter.acquire(timeout=1):
                count += 1
        results.put((worker_id, count))

    # Start 3 processes
    results = multiprocessing.Queue()
    processes = [
        multiprocessing.Process(target=worker, args=(i, results))
        for i in range(3)
    ]

    for p in processes:
        p.start()
    for p in processes:
        p.join()

    # Total requests should respect rate limit
    total = sum(results.get()[1] for _ in range(3))
    assert total <= 240  # Rate limit respected
```

## Related Documentation

- **FDA-180**: Centralized Configuration System
- **FDA-190**: Monitoring and Metrics Integration
- **FDA-20**: Rate Limiter Implementation (original)
- **FDA-12**: Cross-Process Rate Limiter (original)
- **CODE-001**: Rate Limiter Consolidation (this document)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review test files: `tests/test_rate_limiter.py`, `tests/test_fda12_cross_process_rate_limiter.py`
3. Check configuration: `config.toml` (rate_limiting section)
4. Run health check: `python -m lib.cross_process_rate_limiter --health-check`
