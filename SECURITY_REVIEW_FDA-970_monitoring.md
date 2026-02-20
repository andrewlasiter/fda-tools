# Security Review Report: FDA-970
## Monitoring API and Notification System Vulnerabilities

**Date:** 2026-02-19
**Reviewer:** voltagent-qa-sec:security-engineer + voltagent-infra:cloud-architect
**Severity:** ⚠️ HIGH
**Status:** CRITICAL - Blocks FDA-274 (test implementation)

**Files Reviewed:**
- `scripts/fda_approval_monitor.py` (approval monitoring)
- Related notification and alert systems

---

## Executive Summary

**SECURITY RISKS IDENTIFIED:** Alert injection, notification flooding, and insufficient input validation in FDA approval monitoring system could allow malicious alert generation, DoS via notification spam, and unauthorized watchlist manipulation.

**Impact:** HIGH - Could enable:
- Alert injection (fake safety alerts)
- Notification flooding (DoS)
- Watchlist poisoning (unauthorized product code monitoring)
- Deduplication bypass (duplicate alerts)
- Severity escalation attacks (INFO → CRITICAL)

**Recommendation:** REMEDIATE IMMEDIATELY - Affects regulatory alert integrity

---

## Vulnerabilities Identified

### CRITICAL-1: Alert Injection via Product Code Manipulation

**Location:** `fda_approval_monitor.py:25-26` (add_watchlist method)

**Vulnerability:**
- Watchlist accepts arbitrary product codes without validation
- No verification that product codes exist in FDA database
- Attacker can monitor fake product codes and inject fabricated alerts

**Attack Vector:**
```python
# Attacker adds malicious watchlist
monitor.add_watchlist(["FAKE123", "INJECT456"])

# System generates alerts for fake product codes
# Alerts appear legitimate but contain attacker-controlled data
```

**Impact:**
- False regulatory alerts distributed to stakeholders
- Confusion during regulatory reviews
- Credibility damage

**Severity:** CRITICAL
**Exploitability:** HIGH (if API exposed)

---

### CRITICAL-2: Deduplication Bypass via Hash Collision

**Location:** `fda_approval_monitor.py:85-93` (alert dedup key generation)

```python
def _alert_dedup_key(alert: Dict[str, Any]) -> str:
    """Generate a deduplication key for an alert."""
    raw = (
        f"{alert.get('alert_type', '')}"
        f"|{alert.get('pma_number', '')}"
        f"|{alert.get('product_code', '')}"
        f"|{alert.get('data_key', '')}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]  # Only 16 chars!
```

**Vulnerability:**
- Truncated SHA-256 to 16 hex characters (64 bits)
- Hash collision probability: ~2^-32 with 2^16 alerts
- Birthday attack: 50% collision chance with ~2^32 alerts

**Attack Vector:**
```python
# Craft two different alerts with same 16-char hash prefix
alert1 = {"alert_type": "RECALL", "pma_number": "P123456", ...}
alert2 = {"alert_type": "RECALL", "pma_number": "P123457", ...}
# If hash[:16] matches, alert2 is deduplicated (false negative)
```

**Impact:**
- Critical safety alerts suppressed (false negatives)
- Duplicate alerts sent (false positives)

**Severity:** CRITICAL
**Exploitability:** MEDIUM (requires crafting collisions)

---

### HIGH-3: Severity Escalation via Alert Manipulation

**Location:** `fda_approval_monitor.py:55-80` (severity definitions)

**Vulnerability:**
- No validation that severity matches alert content
- Attacker could mark INFO alert as CRITICAL
- No audit trail for severity changes

**Attack Vector:**
```python
alert = {
    'alert_type': 'NEW_APPROVAL',  # Actually INFO severity
    'severity': 'CRITICAL',  # Escalated!
    'product_code': 'ABC',
    'message': 'Routine approval'  # Non-critical content
}
monitor._send_alert(alert)
# CRITICAL alert sent for routine approval
```

**Severity:** HIGH
**Impact:** False critical alerts cause unnecessary panic/investigation

---

### HIGH-4: Notification Flooding (DoS)

**Location:** `fda_approval_monitor.py:27-28` (digest generation)

**Vulnerability:**
- No rate limiting on alert generation or notification sending
- Single product code could generate thousands of alerts
- No queue depth limits

**Attack Vector:**
```python
# Attacker triggers mass approval import
monitor.add_watchlist(["ABC"])  # Popular product code
# If 10,000 historical approvals imported, 10,000 alerts generated
# Email/notification system overwhelmed
```

**Severity:** HIGH
**Exploitability:** MEDIUM
**Impact:** DoS (notification system failure)

---

### MEDIUM-5: Watchlist Persistence Tampering

**Location:** Implied file-based watchlist storage

**Vulnerability:**
- Watchlist likely stored in JSON file
- No HMAC or signature protection
- Attacker with file access can modify watchlist

**Attack Vector:**
```bash
# Modify watchlist file
echo '["MALICIOUS", "FAKE123"]' > watchlist.json
# Monitor processes fake product codes
```

**Severity:** MEDIUM
**Impact:** Unauthorized monitoring, resource waste

---

### MEDIUM-6: Alert History Manipulation

**Location:** `fda_approval_monitor.py:13` (alert history persistence)

**Vulnerability:**
- Alert history used for deduplication and audit
- No protection against modification
- Attacker could delete alerts to bypass deduplication

**Severity:** MEDIUM
**Impact:** Duplicate alerts, audit trail gaps

---

## Remediation Recommendations

### Priority 1: Critical Fixes

**1. Validate Product Codes Against FDA Database**

```python
class FDAApprovalMonitor:
    # Valid product codes from FDA database
    VALID_PRODUCT_CODES_CACHE = None
    CACHE_TTL_HOURS = 24

    @classmethod
    def _get_valid_product_codes(cls) -> Set[str]:
        """Get valid FDA product codes with caching."""
        if cls.VALID_PRODUCT_CODES_CACHE is None:
            # Load from FDA classification database
            from classification_lookup import get_all_product_codes
            cls.VALID_PRODUCT_CODES_CACHE = set(get_all_product_codes())

        return cls.VALID_PRODUCT_CODES_CACHE

    def add_watchlist(self, product_codes: List[str]):
        """Add product codes to watchlist with validation."""
        valid_codes = self._get_valid_product_codes()

        for code in product_codes:
            # Sanitize input
            code = code.upper().strip()

            # Validate against FDA database
            if code not in valid_codes:
                raise ValueError(
                    f"Invalid product code: {code}. "
                    f"Not found in FDA classification database."
                )

            self.watchlist.add(code)
```

---

**2. Use Full SHA-256 for Deduplication**

```python
def _alert_dedup_key(alert: Dict[str, Any]) -> str:
    """Generate a deduplication key with full hash."""
    # Include all relevant fields for uniqueness
    dedup_fields = {
        'alert_type': alert.get('alert_type', ''),
        'pma_number': alert.get('pma_number', ''),
        'product_code': alert.get('product_code', ''),
        'supplement_number': alert.get('supplement_number', ''),
        'decision_date': alert.get('decision_date', ''),
        'data_key': alert.get('data_key', '')
    }

    # Sort keys for consistent hashing
    raw = json.dumps(dedup_fields, sort_keys=True)

    # Use full SHA-256 (256 bits, collision-resistant)
    return hashlib.sha256(raw.encode()).hexdigest()  # Full 64 chars
```

---

**3. Validate Alert Severity**

```python
def _validate_alert_severity(alert: Dict[str, Any]) -> str:
    """Validate alert severity matches content."""
    alert_type = alert.get('alert_type', '')
    claimed_severity = alert.get('severity', '')

    # Auto-assign severity based on alert type
    if alert_type in ['RECALL_CLASS_I', 'SAFETY_ALERT', 'MAUDE_DEATH_SPIKE']:
        required_severity = 'CRITICAL'
    elif alert_type in ['RECALL_CLASS_II', 'SUPPLEMENT_SAFETY']:
        required_severity = 'WARNING'
    else:
        required_severity = 'INFO'

    # Validate claimed severity matches
    if claimed_severity != required_severity:
        logger.warning(
            f"Alert severity mismatch: claimed={claimed_severity}, "
            f"required={required_severity}. Correcting to {required_severity}."
        )
        alert['severity'] = required_severity

    return alert['severity']
```

---

**4. Add Rate Limiting for Alerts**

```python
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_per_hour: int = 100):
        self.max_per_hour = max_per_hour
        self.alert_timestamps = defaultdict(list)  # product_code -> [timestamps]

    def check_rate_limit(self, product_code: str) -> bool:
        """Check if alert rate limit is exceeded."""
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        # Clean old timestamps
        self.alert_timestamps[product_code] = [
            ts for ts in self.alert_timestamps[product_code]
            if ts > one_hour_ago
        ]

        # Check limit
        if len(self.alert_timestamps[product_code]) >= self.max_per_hour:
            raise ValueError(
                f"Rate limit exceeded for {product_code}: "
                f"{self.max_per_hour} alerts/hour"
            )

        # Record new alert
        self.alert_timestamps[product_code].append(now)
        return True
```

---

### Priority 2: High-Risk Mitigations

**5. Protect Watchlist with HMAC**

```python
import hmac

def save_watchlist_secure(watchlist: Set[str], path: Path, secret_key: str):
    """Save watchlist with HMAC protection."""
    data = json.dumps(sorted(watchlist), indent=2)
    data_bytes = data.encode()

    # Generate HMAC
    hmac_value = hmac.new(
        secret_key.encode(),
        data_bytes,
        hashlib.sha256
    ).hexdigest()

    # Save data + HMAC
    with open(path, 'w') as f:
        f.write(data)
    with open(path.with_suffix('.hmac'), 'w') as f:
        f.write(hmac_value)

def load_watchlist_secure(path: Path, secret_key: str) -> Set[str]:
    """Load watchlist with HMAC verification."""
    with open(path, 'rb') as f:
        data_bytes = f.read()
    with open(path.with_suffix('.hmac'), 'r') as f:
        stored_hmac = f.read().strip()

    # Verify HMAC
    calculated_hmac = hmac.new(
        secret_key.encode(),
        data_bytes,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hmac, stored_hmac):
        raise ValueError("Watchlist integrity check failed!")

    return set(json.loads(data_bytes))
```

---

**6. Add Alert Queue Management**

```python
from collections import deque

class AlertQueue:
    MAX_QUEUE_SIZE = 10000

    def __init__(self):
        self.queue = deque(maxlen=self.MAX_QUEUE_SIZE)
        self.overflow_count = 0

    def enqueue(self, alert: Dict):
        """Add alert to queue with overflow detection."""
        if len(self.queue) >= self.MAX_QUEUE_SIZE:
            self.overflow_count += 1
            logger.error(
                f"Alert queue overflow! {self.overflow_count} alerts dropped."
            )
            raise ValueError("Alert queue full (possible flooding attack)")

        self.queue.append(alert)
```

---

## Testing Requirements

### Security Test Cases

1. **Product Code Validation:**
   - Test valid codes (should accept)
   - Test invalid codes like "FAKE123" (should reject)
   - Test SQL injection attempts in product code

2. **Deduplication:**
   - Generate 1000 unique alerts, verify all processed
   - Test hash collision resistance
   - Verify full SHA-256 is used

3. **Severity Validation:**
   - Test INFO alert with CRITICAL severity (should auto-correct)
   - Test recall alert with INFO severity (should escalate)

4. **Rate Limiting:**
   - Send 100 alerts in 1 second (should accept)
   - Send 101 alerts (should reject 101st)
   - Test rate limit reset after 1 hour

5. **Watchlist Integrity:**
   - Modify watchlist file, verify HMAC fails
   - Test watchlist persistence across restarts

---

## Risk Matrix

| Vulnerability | Severity | Exploitability | Impact | Status |
|---------------|----------|----------------|--------|--------|
| Alert Injection (CRITICAL-1) | CRITICAL | HIGH | Fake alerts | ⏳ Pending |
| Dedup Bypass (CRITICAL-2) | CRITICAL | MEDIUM | Suppressed alerts | ⏳ Pending |
| Severity Escalation (HIGH-3) | HIGH | MEDIUM | False criticality | ⏳ Pending |
| Notification Flooding (HIGH-4) | HIGH | MEDIUM | DoS | ⏳ Pending |
| Watchlist Tampering (MEDIUM-5) | MEDIUM | LOW | Unauthorized monitoring | ⏳ Pending |
| Alert History (MEDIUM-6) | MEDIUM | LOW | Duplicate alerts | ⏳ Pending |

---

## Compliance Impact

**21 CFR Part 11:** Alert integrity critical for regulatory decisions

**MedWatch Alignment:** False severity escalation violates MedWatch reporting standards

---

## Approval Checklist

- [ ] Product code validation against FDA database
- [ ] Full SHA-256 deduplication keys
- [ ] Automatic severity validation
- [ ] Rate limiting (100 alerts/hour per product code)
- [ ] Watchlist HMAC protection
- [ ] Alert queue overflow management
- [ ] Security test suite (min 15 tests)
- [ ] Second security engineer review

**Blocker for:** FDA-274 (test_monitoring.py)

**Estimated Remediation Time:** 5-7 hours

---

**Status:** BLOCKING

**Reviewer:** Security Engineer + Cloud Architect
**Date:** 2026-02-19
