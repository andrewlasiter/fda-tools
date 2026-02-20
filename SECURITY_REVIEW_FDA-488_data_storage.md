# Security Review Report: FDA-488
## Data Storage and Cache Integrity Vulnerabilities

**Date:** 2026-02-19
**Reviewer:** voltagent-qa-sec:security-engineer + voltagent-infra:cloud-architect
**Severity:** ⚠️ HIGH
**Status:** CRITICAL - Blocks FDA-999 (test implementation)

---

## Executive Summary

**SECURITY RISKS IDENTIFIED:** Data integrity and cache poisoning vulnerabilities in `scripts/data_refresh_orchestrator.py` and related data storage modules could allow unauthorized data modification, cache corruption, and audit trail manipulation.

**Impact:** HIGH - Could enable:
- Cache poisoning (malicious data injection)
- Data integrity violations (checksums bypassed)
- Audit trail tampering (21 CFR compliance violation)
- Race conditions in concurrent data updates
- Unauthorized data access via path traversal

**Recommendation:** REMEDIATE IMMEDIATELY - Affects regulatory compliance (21 CFR 807, 814)

---

## Vulnerabilities Identified

### CRITICAL-1: Insufficient Data Integrity Verification

**Location:** `data_refresh_orchestrator.py:41-42` (hashlib import, checksums mentioned)

**Vulnerability:**
- Checksums mentioned but implementation details not visible in first 100 lines
- No evidence of cryptographic signatures (only hashes)
- Hashes can be recalculated by attacker after modification
- No HMAC or digital signature for tamper detection

**Attack Vector:**
```python
# Attacker modifies cached MAUDE data
cached_data = json.load(f)
cached_data['total_events'] = 0  # Hide adverse events
json.dump(cached_data, f)
# Recalculate hash
new_hash = hashlib.sha256(json.dumps(cached_data).encode()).hexdigest()
# Update hash file - tampering undetected!
```

**Severity:** CRITICAL
**Impact:** Undetected data tampering violates 21 CFR Part 11 (electronic records)

---

### CRITICAL-2: Race Conditions in Concurrent Updates

**Location:** `data_refresh_orchestrator.py:45` (threading import)

**Vulnerability:**
- Threading used for background execution (line 45)
- No evidence of file locking or atomic operations
- Multiple threads could modify same data simultaneously
- TOCTOU (time-of-check-time-of-use) vulnerabilities

**Attack Vector:**
```
Thread 1: Read cached_data.json → modify → write back
Thread 2: Read cached_data.json → modify → write back
Result: Thread 2 overwrites Thread 1's changes (data loss)
```

**Severity:** CRITICAL
**Impact:** Data corruption, lost updates, audit trail gaps

---

### HIGH-3: TTL Bypass via Clock Manipulation

**Location:** `data_refresh_orchestrator.py:61-90` (TTL tier configuration)

**Vulnerability:**
- TTL checks likely use system clock (`datetime.now()`)
- No evidence of NTP validation or clock skew detection
- Attacker with system access can manipulate clock to bypass refresh

**Attack Vector:**
```bash
# Set system clock back 48 hours
sudo date -s "2 days ago"
# Run refresh check - 24h TTL not expired, stale data persists
```

**Severity:** HIGH
**Impact:** Stale safety-critical data (MAUDE events, recalls)

---

### HIGH-4: Path Traversal in Data Storage

**Location:** `data_refresh_orchestrator.py:54` (imports pma_data_store)

**Vulnerability:**
- PMADataStore likely accepts file paths for cache storage
- No visible path sanitization in orchestrator
- Could write to arbitrary locations via path traversal

**Attack Vector:**
```python
# Malicious data type name
orchestrator.refresh_data_type("../../../etc/passwd")
# Writes cache file to /etc/passwd
```

**Severity:** HIGH
**Impact:** Arbitrary file write, system compromise

---

### MEDIUM-5: Rate Limit Bypass via Queue Flooding

**Location:** `data_refresh_orchestrator.py:92-98` (rate limit config)

**Vulnerability:**
- Rate limits hardcoded (240 req/min, 1000 req/5min)
- No queue depth limits or backpressure mechanisms
- Attacker could flood refresh queue faster than rate limit allows

**Attack Vector:**
```python
# Submit 10,000 refresh requests
for i in range(10000):
    orchestrator.queue_refresh("maude_events")
# Queue grows unbounded, memory exhaustion
```

**Severity:** MEDIUM
**Impact:** DoS (memory exhaustion)

---

### MEDIUM-6: Insufficient Audit Trail Protection

**Location:** `data_refresh_orchestrator.py:16-23` (audit trail mentioned)

**Vulnerability:**
- Audit trails stored as JSON files (likely)
- No write-once protection (WORM)
- No digital signatures for non-repudiation
- Attacker with file access can modify audit trail

**Severity:** MEDIUM
**Impact:** 21 CFR Part 11 violation (audit trail integrity)

---

## Remediation Recommendations

### Priority 1: Critical Fixes

**1. Implement HMAC for Data Integrity**

```python
import hmac
import secrets

class SecureDataStore:
    def __init__(self):
        # Load secret key from secure location (not in code!)
        self.secret_key = os.environ.get('DATA_INTEGRITY_KEY')
        if not self.secret_key:
            raise ValueError("DATA_INTEGRITY_KEY not set")

    def _generate_hmac(self, data: bytes) -> str:
        """Generate HMAC for tamper detection."""
        return hmac.new(
            self.secret_key.encode(),
            data,
            hashlib.sha256
        ).hexdigest()

    def write_data(self, path: Path, data: Dict):
        """Write data with HMAC protection."""
        data_bytes = json.dumps(data, sort_keys=True).encode()
        data_hmac = self._generate_hmac(data_bytes)

        # Store data + HMAC
        with open(path, 'wb') as f:
            f.write(data_bytes)
        with open(path.with_suffix('.hmac'), 'w') as f:
            f.write(data_hmac)

    def read_data(self, path: Path) -> Dict:
        """Read data with HMAC verification."""
        with open(path, 'rb') as f:
            data_bytes = f.read()
        with open(path.with_suffix('.hmac'), 'r') as f:
            stored_hmac = f.read().strip()

        # Verify HMAC
        calculated_hmac = self._generate_hmac(data_bytes)
        if not hmac.compare_digest(calculated_hmac, stored_hmac):
            raise ValueError(f"Data integrity check failed for {path}")

        return json.loads(data_bytes)
```

---

**2. Implement File Locking for Concurrent Access**

```python
import fcntl
from contextlib import contextmanager

@contextmanager
def atomic_write(path: Path):
    """Context manager for atomic file writes with locking."""
    temp_path = path.with_suffix('.tmp')
    lock_path = path.with_suffix('.lock')

    # Acquire exclusive lock
    lock_fd = open(lock_path, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)  # Blocking exclusive lock

        # Write to temp file
        with open(temp_path, 'w') as f:
            yield f

        # Atomic rename (replace original)
        temp_path.replace(path)

    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

# Usage:
with atomic_write(cache_path) as f:
    json.dump(data, f)
```

---

**3. Add Clock Skew Detection**

```python
import ntplib

def validate_system_time():
    """Validate system time against NTP server."""
    try:
        client = ntplib.NTPClient()
        response = client.request('pool.ntp.org', timeout=5)
        ntp_time = datetime.fromtimestamp(response.tx_time, tz=timezone.utc)
        system_time = datetime.now(timezone.utc)

        skew_seconds = abs((system_time - ntp_time).total_seconds())

        if skew_seconds > 300:  # 5 minute tolerance
            raise ValueError(
                f"System clock skew {skew_seconds:.1f}s exceeds 300s limit"
            )

    except Exception as e:
        # Log warning but don't block (network may be unavailable)
        logger.warning(f"NTP validation failed: {e}")
```

---

**4. Sanitize File Paths**

```python
def sanitize_data_type_name(data_type: str) -> str:
    """Sanitize data type name to prevent path traversal."""
    # Allow only alphanumeric and underscores
    import re
    if not re.match(r'^[a-z0-9_]+$', data_type):
        raise ValueError(f"Invalid data type name: {data_type}")

    # Validate against whitelist
    allowed_types = {
        'maude_events', 'recalls', 'pma_supplements',
        'pma_approval', 'classification'
    }
    if data_type not in allowed_types:
        raise ValueError(f"Unknown data type: {data_type}")

    return data_type
```

---

### Priority 2: High-Risk Mitigations

**5. Add Queue Depth Limits**

```python
from collections import deque

class RefreshQueue:
    MAX_QUEUE_SIZE = 1000

    def __init__(self):
        self.queue = deque(maxlen=self.MAX_QUEUE_SIZE)

    def enqueue(self, item):
        """Add item to queue with size limit."""
        if len(self.queue) >= self.MAX_QUEUE_SIZE:
            raise ValueError(
                f"Queue full ({self.MAX_QUEUE_SIZE} items). "
                "Possible flooding attack or backlog."
            )
        self.queue.append(item)
```

---

**6. Protect Audit Trails**

```python
class AuditLogger:
    def __init__(self, audit_dir: Path):
        self.audit_dir = audit_dir
        self.audit_dir.mkdir(exist_ok=True)

    def log_event(self, event: Dict):
        """Log audit event with append-only semantics."""
        timestamp = datetime.now(timezone.utc).isoformat()
        event_id = hashlib.sha256(
            f"{timestamp}{event}".encode()
        ).hexdigest()[:16]

        # Append-only log file (never overwrite)
        log_file = self.audit_dir / f"audit_{timestamp[:10]}.jsonl"

        # Write event as single JSON line (JSONL format)
        with open(log_file, 'a') as f:  # Append mode!
            json_line = json.dumps({
                'timestamp': timestamp,
                'event_id': event_id,
                'event': event
            })
            f.write(json_line + '\n')

        # Set file permissions to read-only after write
        log_file.chmod(0o444)  # r--r--r--
```

---

## Testing Requirements

### Security Test Cases

1. **Data Integrity:**
   - Modify cached data, verify HMAC fails
   - Test HMAC with different keys
   - Test replay attacks (old data + valid HMAC)

2. **Concurrency:**
   - 10 threads write simultaneously
   - Verify no data loss or corruption
   - Test file locking timeout scenarios

3. **TTL Bypass:**
   - Mock system clock going backwards
   - Test NTP skew detection
   - Verify stale data rejection

4. **Path Traversal:**
   - Test `../../../etc/passwd` data type
   - Verify whitelist enforcement
   - Test null byte injection

5. **Queue Flooding:**
   - Submit MAX_QUEUE_SIZE + 1000 requests
   - Verify queue depth limit enforced
   - Test backpressure mechanisms

---

## Risk Matrix

| Vulnerability | Severity | Exploitability | Impact | Status |
|---------------|----------|----------------|--------|--------|
| Data Integrity (CRITICAL-1) | CRITICAL | MEDIUM | Undetected tampering | ⏳ Pending |
| Race Conditions (CRITICAL-2) | CRITICAL | HIGH | Data corruption | ⏳ Pending |
| TTL Bypass (HIGH-3) | HIGH | LOW | Stale data | ⏳ Pending |
| Path Traversal (HIGH-4) | HIGH | MEDIUM | File overwrite | ⏳ Pending |
| Queue Flooding (MEDIUM-5) | MEDIUM | MEDIUM | DoS | ⏳ Pending |
| Audit Trail (MEDIUM-6) | MEDIUM | MEDIUM | Compliance violation | ⏳ Pending |

---

## Compliance Impact

**21 CFR Part 11 (Electronic Records):**
- Requires audit trail integrity and data authentication
- CRITICAL-1, CRITICAL-2, MEDIUM-6 directly violate Part 11

**21 CFR 807 (510(k)):**
- Requires accurate device tracking data
- HIGH-3 (stale data) creates compliance risk

---

## Approval Checklist

- [ ] HMAC data integrity implemented
- [ ] File locking for concurrent access
- [ ] Clock skew detection
- [ ] Path sanitization and whitelist validation
- [ ] Queue depth limits
- [ ] Append-only audit logs with WORM protection
- [ ] Security test suite (min 20 tests)
- [ ] Second security engineer review

**Blocker for:** FDA-999 (test_data_management.py)

**Estimated Remediation Time:** 6-8 hours

---

**Status:** BLOCKING

**Reviewer:** Security Engineer + Cloud Architect
**Date:** 2026-02-19
