# ADR-003: File-Lock-Based Multi-Process Rate Limiter

**Status:** Accepted
**Date:** 2025-04-01

## Context

Multiple concurrent Claude agents execute FDA API calls simultaneously during
batch enrichment workflows. The FDA open.fda.gov API enforces rate limits
(1000 req/day for unauthenticated, 120 req/min for authenticated). Exceeding
limits results in 429 responses and temporary bans that block all agents.

Standard Python `threading.Lock` only coordinates threads within a single
process. When multiple Python processes are spawned (one per agent), each
process has its own lock state and can independently exceed the rate limit.

The solution must work cross-process without requiring a network service or
heavy infrastructure on the RA professional's laptop.

## Decision

`lib/cross_process_rate_limiter.py` implements a token-bucket rate limiter
using a lock file (`~/.fda-tools/rate_limit.lock`) and a shared state file
(`~/.fda-tools/rate_limit_state.json`). Processes acquire an exclusive fcntl
lock, read current token count and timestamp, consume tokens, write state, and
release the lock. On Windows, `msvcrt.locking` is used as the fallback.

## Alternatives Considered

- **Redis:** Production-grade distributed rate limiting. Rejected because it
  requires a running Redis server, which RA professionals cannot be expected
  to provision. Adds a heavyweight dependency for a single coordination task.
- **threading.Lock:** Insufficient — in-process only. Would allow N processes
  to each run at full rate, multiplying API load by N.
- **Sleep/retry with jitter:** No coordination between processes; still causes
  burst violations. Too slow when N agents all back off simultaneously.
- **Shared memory (mmap):** More complex than file locking; cross-platform
  support is inconsistent in Python 3.9.

## Consequences

- File I/O overhead on every API call (~1ms per acquisition). Acceptable given
  network latency dominates.
- Stale lock files must be cleaned up if a process crashes; a 5-second lock
  timeout with SIGALRM handles this on POSIX.
- Windows support requires the msvcrt fallback path, which is tested in CI.
- Rate limit configuration is centralized in one file, not per-script.
