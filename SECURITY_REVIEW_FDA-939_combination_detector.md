# Security Review Report: FDA-939
## Combination Detector Drug Name Parsing and Injection Vulnerabilities

**Date:** 2026-02-19
**Reviewer:** voltagent-qa-sec:security-engineer + fda-software-ai-expert
**Severity:** ⚠️ HIGH
**Status:** CRITICAL - Blocks FDA-563 (test implementation)

---

## Executive Summary

**SECURITY RISKS IDENTIFIED:** Regular expression injection vulnerabilities and insufficient input sanitization in `lib/combination_detector.py` could allow malicious pattern matching, ReDoS (Regular Expression Denial of Service) attacks, and unintended combination product classification.

**Impact:** HIGH - Could enable:
- ReDoS attacks via malicious device descriptions
- False positive/negative combination product detection
- Regulatory misclassification (incorrect RHO assignment)
- Resource exhaustion (CPU/memory)

**Recommendation:** REMEDIATE IMMEDIATELY - Classification errors have regulatory compliance impact.

---

## Vulnerabilities Identified

### CRITICAL-1: Regular Expression Denial of Service (ReDoS) Risk

**Location:** `combination_detector.py:162-163` (keyword matching in user input)

**Vulnerability:**
- User-controlled input (`device_description`, `trade_name`, `intended_use`) is matched against keyword lists
- Simple `in` operator is safe, BUT if regex matching is added in the future, ReDoS risk exists
- No input length validation (could provide 10MB device description)

**Attack Vector (if regex added):**
```python
# If code is changed to use re.search() instead of 'in':
malicious_description = "a" * 1000000 + "drug-eluting"  # 1MB of 'a's
# With naive regex: re.search(r'.*drug-eluting', malicious_description)
# Result: Catastrophic backtracking, CPU exhaustion
```

**Current Risk:** MEDIUM (not directly vulnerable, but fragile)
**Future Risk:** CRITICAL (if regex matching is added without anchoring)

**Evidence of Risk:** Lines 162-163, 191-192 use `in` operator (safe), but pattern is risky

---

### HIGH-2: Unvalidated Input Length (No Limits)

**Location:** `combination_detector.py:68-89` (constructor accepts arbitrary-length strings)

**Vulnerability:**
- No validation of input length for `device_description`, `trade_name`, `intended_use`
- Could accept multi-megabyte strings
- Combined text in line 85-89 concatenates all inputs without size limits

**Attack Vector:**
```python
device_data = {
    'device_description': 'A' * 10_000_000,  # 10MB string
    'trade_name': 'B' * 10_000_000,  # 10MB string
    'intended_use': 'C' * 10_000_000,  # 10MB string
}
detector = CombinationProductDetector(device_data)
# combined_text is 30MB, memory exhaustion
```

**Impact:**
- Memory exhaustion (30MB+ combined text)
- Slow string operations (keyword matching on huge strings)
- Potential DoS

**Severity:** HIGH
**Exploitability:** MEDIUM (requires API access with untrusted input)

---

### HIGH-3: Case-Insensitive Matching on Entire Input (Performance Risk)

**Location:** `combination_detector.py:89`

```python
self.combined_text = ' '.join([
    self.device_description,
    self.trade_name,
    self.intended_use
]).lower()  # .lower() on potentially huge string
```

**Vulnerability:**
- `.lower()` operation on multi-megabyte strings is expensive
- Performed in constructor (before any validation)
- No short-circuit if inputs are empty

**Impact:**
- CPU exhaustion for large inputs
- Unnecessary memory allocation

**Severity:** HIGH (performance)
**Exploitability:** MEDIUM

---

### MEDIUM-4: Keyword List Pollution Risk

**Location:** `combination_detector.py:27-59` (hardcoded keyword lists)

**Vulnerability:**
- Keyword lists are class-level constants (not instance variables)
- If modified at runtime, affects ALL detector instances globally
- No immutability protection

**Attack Vector:**
```python
# Malicious code modifies class constant
CombinationProductDetector.DRUG_DEVICE_KEYWORDS.append('benign_term')
# Now all devices with 'benign_term' are classified as combination products
```

**Current Risk:** LOW (requires code modification)
**Impact:** Global misclassification of devices

---

### MEDIUM-5: Unicode Normalization Issues

**Location:** `combination_detector.py:89` (.lower() without normalization)

**Vulnerability:**
- No Unicode normalization before keyword matching
- Different Unicode representations of same character may bypass detection
- Example: "paclitaxel" vs "paclitaxel" (Unicode lookalike characters)

**Attack Vector:**
```python
# Use Unicode lookalike for 'a' (U+0430 Cyrillic 'a')
device_description = "pаclitaxel-coated"  # Cyrillic 'а' instead of Latin 'a'
# Keyword matching fails, drug component not detected
```

**Severity:** MEDIUM
**Exploitability:** LOW (requires Unicode knowledge)
**Impact:** False negative detection

---

### LOW-6: Information Leakage via Detailed Error Messages

**Location:** Throughout file (exceptions may leak internal logic)

**Vulnerability:**
- If exceptions are raised and exposed to users, reveals keyword lists
- Attacker learns exactly what terms trigger combination product detection
- Useful for evasion

**Severity:** LOW (information disclosure)

---

## Remediation Recommendations

### Priority 1: Critical Fixes (Required Before Production)

**1. Add Input Length Validation**

```python
MAX_INPUT_LENGTH = 50_000  # 50KB per field (generous for device descriptions)

def __init__(self, device_data: Dict):
    """Initialize detector with validated device data."""
    self.device_data = device_data

    # Validate input lengths BEFORE any processing
    self.device_description = self._validate_input(
        device_data.get('device_description', ''),
        'device_description'
    )
    self.trade_name = self._validate_input(
        device_data.get('trade_name', ''),
        'trade_name'
    )
    self.intended_use = self._validate_input(
        device_data.get('intended_use', ''),
        'intended_use'
    )

    # Safe to combine now (validated lengths)
    self.combined_text = ' '.join([
        self.device_description,
        self.trade_name,
        self.intended_use
    ]).lower()

def _validate_input(self, text: str, field_name: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """Validate input text length and type."""
    if not isinstance(text, str):
        raise ValueError(f"{field_name} must be a string")

    if len(text) > max_length:
        raise ValueError(
            f"{field_name} exceeds maximum length {max_length} "
            f"(got {len(text)} characters)"
        )

    return text
```

---

**2. Add Unicode Normalization**

```python
import unicodedata

def _normalize_text(self, text: str) -> str:
    """Normalize Unicode text to prevent lookalike bypasses."""
    # NFC normalization (canonical composition)
    normalized = unicodedata.normalize('NFC', text)

    # Convert to lowercase
    lowercased = normalized.lower()

    # Remove non-ASCII characters (optional, depends on requirements)
    # ascii_only = lowercased.encode('ascii', errors='ignore').decode('ascii')

    return lowercased

# Usage in __init__:
self.combined_text = self._normalize_text(' '.join([
    self.device_description,
    self.trade_name,
    self.intended_use
]))
```

---

**3. Make Keyword Lists Immutable**

```python
# Use tuples instead of lists (immutable)
DRUG_DEVICE_KEYWORDS = (
    'drug-eluting', 'drug-coated', 'drug eluting', 'drug coated',
    # ... rest of keywords
)

DEVICE_BIOLOGIC_KEYWORDS = (
    'collagen', 'tissue-engineered', 'tissue engineered',
    # ... rest of keywords
)

EXCLUSIONS = (
    'compatible with', 'may be used with', 'can be used with',
    # ... rest of exclusions
)

# Or use frozenset for faster lookup
DRUG_DEVICE_KEYWORDS_SET = frozenset([
    'drug-eluting', 'drug-coated', ...
])

# Keyword matching with set (O(1) lookup instead of O(n))
def _detect_drug(self) -> Tuple[bool, List[str], str]:
    detected_drugs = [
        kw for kw in self.DRUG_DEVICE_KEYWORDS_SET
        if kw in self.combined_text
    ]
    # ... rest of method
```

---

### Priority 2: High-Risk Mitigations

**4. Add Timeout Protection for Keyword Matching**

```python
import signal
from contextlib import contextmanager

@contextmanager
def timeout(seconds):
    """Context manager for operation timeout."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation exceeded {seconds} seconds")

    # Set alarm (Unix only, use threading.Timer for cross-platform)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def detect(self) -> Dict:
    """Detect combination product with timeout protection."""
    try:
        with timeout(10):  # 10 second max for detection
            # ... existing detection logic
            pass
    except TimeoutError:
        return {
            'is_combination': False,
            'error': 'Detection timeout (input too complex)',
            # ... rest of error result
        }
```

---

**5. Add Input Sanitization**

```python
def _sanitize_input(self, text: str) -> str:
    """Sanitize input to remove potentially dangerous patterns."""
    # Remove null bytes
    text = text.replace('\x00', '')

    # Remove excessive whitespace
    text = ' '.join(text.split())

    # Limit consecutive repeated characters (ReDoS protection)
    import re
    # Replace 5+ consecutive chars with just 4 (e.g., "aaaaa" -> "aaaa")
    text = re.sub(r'(.)\1{4,}', r'\1\1\1\1', text)

    return text
```

---

## Testing Requirements

### Security Test Cases (Minimum Required)

1. **Input Length Validation:**
   - Test 0-byte input (should pass)
   - Test MAX_INPUT_LENGTH input (should pass)
   - Test MAX_INPUT_LENGTH + 1 input (should reject)
   - Test 10MB input (should reject)

2. **Unicode Normalization:**
   - Test "paclitaxel" (Latin characters)
   - Test "pаclitaxel" (Cyrillic 'а')
   - Test combining characters (é vs e + ́)
   - Verify normalization makes them equivalent

3. **Performance/DoS Protection:**
   - Test 100KB device description (measure time)
   - Test 1MB device description (should timeout or reject)
   - Test repeated character attack (aaaaa...drug-eluting)

4. **Keyword Immutability:**
   - Verify DRUG_DEVICE_KEYWORDS cannot be modified at runtime
   - Test that keyword pollution doesn't affect other instances

5. **False Positive/Negative Detection:**
   - Test exclusions ("drug-free device")
   - Test legitimate combinations ("drug-eluting stent")
   - Test edge cases (partial matches)

---

## Risk Matrix

| Vulnerability | Severity | Exploitability | Impact | Status |
|---------------|----------|----------------|--------|--------|
| ReDoS Risk (CRITICAL-1) | MEDIUM→CRITICAL | HIGH (if regex added) | CPU exhaustion | ⏳ Pending |
| Input Length (HIGH-2) | HIGH | MEDIUM | Memory/CPU DoS | ⏳ Pending |
| Performance (HIGH-3) | HIGH | MEDIUM | CPU exhaustion | ⏳ Pending |
| Keyword Pollution (MEDIUM-4) | MEDIUM | LOW | Misclassification | ⏳ Pending |
| Unicode Bypass (MEDIUM-5) | MEDIUM | LOW | False negatives | ⏳ Pending |
| Info Leakage (LOW-6) | LOW | LOW | Keyword exposure | ⏳ Pending |

---

## Regulatory Impact

**21 CFR Part 3 (RHO Assignment):**
- Incorrect combination product detection → wrong RHO assignment
- Regulatory pathway errors (510(k) vs PMA vs BLA)
- Could delay approval or cause rejection

**Impact Severity:** CRITICAL for regulatory compliance

---

## Approval Checklist

- [ ] Input length validation implemented (MAX_INPUT_LENGTH)
- [ ] Unicode normalization added
- [ ] Keyword lists made immutable (tuples/frozenset)
- [ ] Timeout protection added for long-running operations
- [ ] Security test suite created (min 15 tests)
- [ ] Performance testing completed (1MB input benchmark)
- [ ] Code review by second security engineer

**Blocker for:** FDA-563 (test_combination_detector.py)

**Estimated Remediation Time:** 4-6 hours

---

**Status:** BLOCKING - Test implementation cannot proceed until remediation complete

**Reviewer:** Security Engineer + FDA Software AI Expert
**Date:** 2026-02-19
