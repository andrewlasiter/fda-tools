#!/usr/bin/env python3
"""
Rate Limiter Demonstration (CODE-001)

This script demonstrates the consolidated rate limiting features,
including the new decorator and context manager patterns.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports

from fda_tools.lib.rate_limiter import (
    RateLimiter,
    RetryPolicy,
    rate_limited,
    RateLimitContext,
)


def demo_basic_usage():
    """Demonstrate basic rate limiter usage."""
    print("=" * 70)
    print("DEMO 1: Basic Rate Limiter Usage")
    print("=" * 70)

    # Create a limiter: 12 requests per minute (0.2 req/sec)
    limiter = RateLimiter(requests_per_minute=12)

    print("\nMaking 5 requests with rate limiting...")
    for i in range(5):
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start
        print(f"  Request {i+1}: acquired after {elapsed:.3f}s")

    # Get statistics
    stats = limiter.get_stats()
    print(f"\nStatistics:")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Requests blocked: {stats['total_waits']}")
    print(f"  Wait percentage: {stats['wait_percentage']:.1f}%")
    print(f"  Average wait: {stats['avg_wait_time_seconds']:.3f}s")
    print(f"  Current tokens: {stats['current_tokens']:.1f}")


def demo_decorator_pattern():
    """Demonstrate decorator pattern (CODE-001)."""
    print("\n" + "=" * 70)
    print("DEMO 2: Decorator Pattern (CODE-001)")
    print("=" * 70)

    limiter = RateLimiter(requests_per_minute=12)

    @rate_limited(limiter)
    def fetch_data(item_id):
        """Simulated API call."""
        time.sleep(0.1)  # Simulate network delay
        return f"Data for item {item_id}"

    print("\nMaking 3 decorated function calls...")
    for i in range(3):
        start = time.time()
        result = fetch_data(i + 1)
        elapsed = time.time() - start
        print(f"  {result} (took {elapsed:.3f}s)")


def demo_context_manager():
    """Demonstrate context manager pattern (CODE-001)."""
    print("\n" + "=" * 70)
    print("DEMO 3: Context Manager Pattern (CODE-001)")
    print("=" * 70)

    limiter = RateLimiter(requests_per_minute=12)

    print("\nProcessing batch of 3 items with context manager...")
    start = time.time()
    with RateLimitContext(limiter, tokens=3):
        for i in range(3):
            print(f"  Processing item {i+1}")
            time.sleep(0.05)

    elapsed = time.time() - start
    print(f"\nBatch completed in {elapsed:.3f}s")


def demo_burst_handling():
    """Demonstrate burst capacity."""
    print("\n" + "=" * 70)
    print("DEMO 4: Burst Handling")
    print("=" * 70)

    # Create limiter with burst capacity
    limiter = RateLimiter(requests_per_minute=60, burst_capacity=20)

    print("\nBurst capacity: 20 tokens")
    print("Sustained rate: 60 req/min (1 req/sec)")

    # Burst: use all 20 tokens immediately
    print("\nBurst phase: consuming 20 tokens immediately...")
    start = time.time()
    for i in range(20):
        result = limiter.try_acquire()
        if result:
            print(f"  Token {i+1}: acquired ✓")
        else:
            print(f"  Token {i+1}: failed ✗")

    elapsed = time.time() - start
    print(f"Burst completed in {elapsed:.3f}s (should be nearly instant)")

    # Next request should fail (no tokens left)
    print("\nTrying to acquire one more token...")
    result = limiter.try_acquire()
    print(f"  Result: {'acquired ✓' if result else 'failed ✗ (as expected)'}")

    # Wait for replenishment
    print("\nWaiting 2 seconds for token replenishment...")
    time.sleep(2.0)

    result = limiter.try_acquire()
    print(f"  After wait: {'acquired ✓ (tokens replenished!)' if result else 'failed ✗'}")


def demo_retry_policy():
    """Demonstrate retry policy with exponential backoff."""
    print("\n" + "=" * 70)
    print("DEMO 5: Retry Policy with Exponential Backoff")
    print("=" * 70)

    policy = RetryPolicy(max_attempts=5, base_delay=0.5, max_delay=5.0, jitter=False)

    print("\nExponential backoff delays:")
    for attempt in range(5):
        delay = policy.get_retry_delay(attempt)
        if delay is not None:
            print(f"  Attempt {attempt}: {delay:.3f}s")
        else:
            print(f"  Attempt {attempt}: Max attempts exceeded")


def demo_statistics():
    """Demonstrate comprehensive statistics."""
    print("\n" + "=" * 70)
    print("DEMO 6: Comprehensive Statistics")
    print("=" * 70)

    limiter = RateLimiter(requests_per_minute=60)

    # Make some requests
    print("\nMaking 10 requests...")
    for i in range(10):
        limiter.acquire()

    # Drain bucket to force some waits
    print("Draining bucket to force waits...")
    for i in range(50):
        limiter.try_acquire()

    # Make more requests (these will wait)
    print("Making 5 more requests (will wait for tokens)...")
    for i in range(5):
        limiter.acquire(timeout=2)

    # Get detailed statistics
    stats = limiter.get_stats()

    print("\nDetailed Statistics:")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Total waits: {stats['total_waits']}")
    print(f"  Wait percentage: {stats['wait_percentage']:.1f}%")
    print(f"  Total wait time: {stats['total_wait_time_seconds']:.3f}s")
    print(f"  Average wait time: {stats['avg_wait_time_seconds']:.3f}s")
    print(f"  Rate limit warnings: {stats['rate_limit_warnings']}")
    print(f"  Current tokens: {stats['current_tokens']:.1f}")
    print(f"  Configured limit: {stats['requests_per_minute']} req/min")


def demo_timeout_handling():
    """Demonstrate timeout handling."""
    print("\n" + "=" * 70)
    print("DEMO 7: Timeout Handling")
    print("=" * 70)

    limiter = RateLimiter(requests_per_minute=12)  # Very slow: 0.2 req/sec

    # Drain bucket
    print("\nDraining bucket completely...")
    for _ in range(12):
        limiter.try_acquire()

    # Try to acquire with short timeout
    print("\nTrying to acquire with 0.5s timeout (should fail)...")
    start = time.time()
    result = limiter.acquire(timeout=0.5)
    elapsed = time.time() - start

    print(f"  Result: {'success ✓' if result else 'timeout ✗ (as expected)'}")
    print(f"  Elapsed: {elapsed:.3f}s")

    # Try with longer timeout
    print("\nTrying to acquire with 1.5s timeout (should succeed)...")
    start = time.time()
    result = limiter.acquire(timeout=1.5)
    elapsed = time.time() - start

    print(f"  Result: {'success ✓' if result else 'timeout ✗'}")
    print(f"  Elapsed: {elapsed:.3f}s")


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "RATE LIMITER DEMONSTRATION (CODE-001)" + " " * 15 + "║")
    print("╚" + "=" * 68 + "╝")

    demos = [
        ("Basic Usage", demo_basic_usage),
        ("Decorator Pattern", demo_decorator_pattern),
        ("Context Manager", demo_context_manager),
        ("Burst Handling", demo_burst_handling),
        ("Retry Policy", demo_retry_policy),
        ("Statistics", demo_statistics),
        ("Timeout Handling", demo_timeout_handling),
    ]

    for name, demo_func in demos:
        try:
            demo_func()
        except Exception as e:
            print(f"\n⚠️  Error in {name} demo: {e}")

    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nFor more information, see:")
    print("  - docs/RATE_LIMITER_README.md")
    print("  - docs/RATE_LIMITER_MIGRATION_GUIDE.md")
    print("  - CODE-001_IMPLEMENTATION_SUMMARY.md")
    print()


if __name__ == "__main__":
    main()
