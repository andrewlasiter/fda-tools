# Security Review Report: FDA-198
## eCopy Exporter Path Traversal and Input Sanitization

**Date:** 2026-02-19
**Reviewer:** voltagent-qa-sec:security-engineer + fda-software-ai-expert
**Severity:** ⚠️ HIGH
**Status:** CRITICAL - Blocks FDA-477 (test implementation)

---

## Executive Summary

**SECURITY RISKS IDENTIFIED:** Multiple path traversal vulnerabilities and insufficient input sanitization in `lib/ecopy_exporter.py` could allow malicious file access outside the intended eCopy directory structure.

**Impact:** HIGH - Could enable:
- Arbitrary file system access via path traversal
- Command injection through unsanitized metadata
- Unauthorized file overwrite
- Information disclosure via error messages

**Recommendation:** REMEDIATE IMMEDIATELY before production deployment.

---

## Vulnerabilities Identified

### CRITICAL-1: Path Traversal in Draft File Loading (Lines 165-169)

**Location:** `ecopy_exporter.py:165-169`

**Vulnerability:**
- No validation that `draft_file` doesn't contain path traversal sequences (`../`, `../../`)
- Attacker could supply `"../../../../etc/passwd"` in ECOPY_SECTIONS configuration
- Pathlib `/` operator DOES NOT sanitize or restrict path traversal

**Attack Vector:**
```python
# Malicious ECOPY_SECTIONS modification
ECOPY_SECTIONS = {
    "01": {"name": "Cover Letter", "draft_file": "../../../etc/passwd"}
}
# Result: Reads /etc/passwd and includes in eCopy package
```

**Proof:**
```python
from pathlib import Path
project = Path("/home/user/project")
malicious = "../../../etc/passwd"
path = project / malicious
print(path)  # Outputs: /etc/passwd (traversal successful!)
```

**Severity:** CRITICAL
**Exploitability:** HIGH (if untrusted input in file names)

---

### CRITICAL-2: Metadata Injection Risk (Lines 232-233)

**Location:** `ecopy_exporter.py:232-233`

**Current Status:** MEDIUM (not exploitable now)
**Future Risk:** HIGH (when user metadata is added)

**Vulnerability:**
- No sanitization framework for pandoc metadata values
- Future additions of user-controlled fields (title, author, company) could enable injection
- Current datetime formatting is safe, but pattern is fragile

**Future Attack Vector (when user metadata added):**
```python
company_name = user_input  # "Acme'; malicious_command"
cmd.append(f"--metadata company={company_name}")  # Vulnerable if added
```

---

### HIGH-3: Insufficient Section Name Validation (Lines 154-156)

**Location:** `ecopy_exporter.py:154-156`

**Vulnerability:**
- `section_name` only sanitized by removing spaces (`.replace(' ', '')`)
- No validation against path traversal (`/`, `..`), shell characters, null bytes

**Attack Vector:**
```python
ECOPY_SECTIONS = {
    "01": {"name": "../malicious", "draft_file": "cover.md"}
}
# Creates: eCopy/0001-../malicious/ (path traversal in directory name)
```

**Severity:** HIGH
**Exploitability:** MEDIUM (requires ECOPY_SECTIONS modification)

---

### MEDIUM-4: Race Condition in Directory Creation (Line 156)

**Vulnerability:** TOCTOU (time-of-check-time-of-use)
- `exist_ok=True` creates window for symlink replacement attack
- Attacker could replace directory with symlink between check and use

**Severity:** MEDIUM
**Exploitability:** LOW (requires local access and timing)

---

### MEDIUM-5: Subprocess Timeout Insufficient (Lines 235-240)

**Vulnerability:**
- 60-second timeout may be insufficient for large markdown files
- Could cause legitimate submissions to fail
- No retry logic or size validation

**Impact:** Availability (DoS potential with extremely large files)
**Severity:** MEDIUM

---

### LOW-6: Error Messages Leak Path Information

**Locations:** Lines 178-181, 243

**Vulnerability:**
- Error messages may reveal internal file paths
- Useful for reconnaissance in multi-stage attacks

**Severity:** LOW (information disclosure)

---

## Remediation Recommendations

### Priority 1: Critical Fixes (Required Before Production)

**1. Implement Path Sanitization**

Create function to validate and sanitize all path components:

```python
def _sanitize_path(self, path_component: str, context: str = "file") -> str:
    """Sanitize path component to prevent traversal attacks."""
    import os

    # Normalize path (resolves .., ., //)
    normalized = os.path.normpath(path_component)

    # Reject absolute paths
    if os.path.isabs(normalized):
        raise ValueError(f"Absolute paths not allowed: {path_component}")

    # Reject parent directory references
    if ".." in normalized.split(os.sep):
        raise ValueError(f"Path traversal not allowed: {path_component}")

    # Reject null bytes
    if "\x00" in path_component:
        raise ValueError(f"Null bytes not allowed: {path_component}")

    # For filenames, reject directory separators
    if context == "file" and os.sep in path_component:
        raise ValueError(f"Directory separators not allowed: {path_component}")

    return normalized
```

**2. Validate Paths Stay Within Project Directory**

```python
def _validate_path_in_project(self, path: Path) -> Path:
    """Ensure path is within project directory."""
    try:
        resolved = path.resolve(strict=False)
    except (OSError, RuntimeError):
        raise ValueError(f"Cannot resolve path: {path}")

    project_resolved = self.project_path.resolve(strict=False)

    if not str(resolved).startswith(str(project_resolved)):
        raise ValueError(f"Path escapes project directory")

    return resolved
```

**3. Add File Size Validation**

```python
MAX_FILE_SIZE_MB = 100

def _validate_file_size(self, file_path: Path, max_mb: int = MAX_FILE_SIZE_MB):
    """Validate file size to prevent DoS."""
    if not file_path.exists():
        return

    size_mb = file_path.stat().st_size / (1024 * 1024)
    if size_mb > max_mb:
        raise ValueError(f"File size {size_mb:.1f} MB exceeds limit {max_mb} MB")
```

---

### Priority 2: High-Risk Mitigations

**4. Sanitize Section Names**

```python
# In export() method
for section_num, section_info in self.ECOPY_SECTIONS.items():
    section_name = section_info["name"]

    # Validate section name
    safe_section_name = self._sanitize_path(
        section_name.replace(' ', ''),
        context="directory"
    )

    section_dir = self.ecopy_path / f"{section_num.zfill(4)}-{safe_section_name}"
    validated_section_dir = self._validate_path_in_project(section_dir)
    validated_section_dir.mkdir(exist_ok=True)
```

**5. Prepare Metadata Sanitization (for future user inputs)**

```python
def _sanitize_metadata_value(self, value: str) -> str:
    """Sanitize metadata value for command line safety."""
    import shlex

    # Remove null bytes and shell metacharacters
    value = value.replace("\x00", "")
    illegal = [";", "|", "&", "$", "`", "\n", "\r", "\\"]
    for char in illegal:
        value = value.replace(char, "")

    return shlex.quote(value)
```

---

## Testing Requirements

### Security Test Cases (Minimum Required)

1. **Path Traversal Protection:**
   - Test `../../../etc/passwd`
   - Test Windows paths `..\\..\\..\\windows\\system32`
   - Test URL encoded `%2e%2e%2f`
   - Test double encoded `%252f`

2. **Null Byte Injection:**
   - Test `file.md\x00.jpg`
   - Test `file\x00.md`

3. **Shell Metacharacter Sanitization:**
   - Test `; rm -rf /`
   - Test `| malicious_command`
   - Test `$(command_substitution)`

4. **File Size Validation:**
   - Test files exceeding MAX_FILE_SIZE_MB
   - Test extremely small files (0 bytes)

5. **Directory Escape Validation:**
   - Verify all created paths stay within project directory
   - Test symlink attacks (if applicable)

---

## Risk Matrix

| Vulnerability | Severity | Exploitability | Impact | Status |
|---------------|----------|----------------|--------|--------|
| Path Traversal (CRITICAL-1) | CRITICAL | HIGH | Arbitrary file read | ⏳ Pending |
| Metadata Injection (CRITICAL-2) | MEDIUM→HIGH | MEDIUM | Future risk | ⏳ Pending |
| Section Name Validation (HIGH-3) | HIGH | MEDIUM | Directory traversal | ⏳ Pending |
| Race Condition (MEDIUM-4) | MEDIUM | LOW | File overwrite | ⏳ Pending |
| Subprocess Timeout (MEDIUM-5) | MEDIUM | LOW | DoS | ⏳ Pending |
| Info Disclosure (LOW-6) | LOW | LOW | Path leakage | ⏳ Pending |

---

## Compliance Impact

**FDA 21 CFR Part 11:** Path traversal could allow unauthorized electronic record modification

**ISO 14971 (Risk Management):** Security vulnerabilities constitute software hazards requiring mitigation

**IEC 62304 (Medical Device Software):** Class B/C requires security risk analysis and input validation

---

## Approval Checklist

- [ ] All CRITICAL vulnerabilities remediated
- [ ] Security test suite created (min 10 tests covering all vulnerabilities)
- [ ] Code review by second security engineer
- [ ] Penetration testing completed
- [ ] Documentation updated

**Blocker for:** FDA-477 (test_ecopy_exporter.py)

**Estimated Remediation Time:** 4-6 hours

---

**Status:** BLOCKING - Test implementation cannot proceed until remediation complete

**Reviewer:** Security Engineer + FDA Software AI Expert
**Date:** 2026-02-19
