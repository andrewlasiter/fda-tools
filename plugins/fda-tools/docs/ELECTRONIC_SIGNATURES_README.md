# Electronic Signatures System (FDA-184)

**21 CFR Part 11 Compliant Electronic Signatures**

## Overview

The FDA Tools Electronic Signatures system provides comprehensive electronic signature functionality compliant with 21 CFR Part 11 requirements for FDA regulatory submissions.

**Key Features:**
- ✅ 21 CFR Part 11 compliance (§11.50, §11.70, §11.100, §11.200, §11.300)
- ✅ Cryptographic signature binding (HMAC-SHA256)
- ✅ Tamper detection (SHA-256 document hashing)
- ✅ Multi-signatory workflow support
- ✅ Comprehensive audit trail
- ✅ Signature manifest generation (JSON/XML)
- ✅ Integration with authentication system (FDA-185)

## Quick Start

### Installation

The signatures system is integrated into FDA Tools. No additional installation required.

**Dependencies:**
- Python 3.8+
- argon2-cffi (password hashing)
- Standard library (sqlite3, hashlib, hmac)

### Basic Usage

#### 1. Apply Signature

```python
from lib.auth import AuthManager
from lib.signatures import SignatureManager, SignatureMeaning

# Initialize
auth = AuthManager()
sig_mgr = SignatureManager()

# Authenticate user
session = auth.login("jsmith", "password")
user = auth.validate_session(session.token)

# Apply signature
signature = sig_mgr.sign_document(
    document_path="/path/to/submission.pdf",
    user=user,
    password="password",  # Re-authentication required
    meaning=SignatureMeaning.AUTHOR,
    comments="Final review complete"
)

print(f"Signature ID: {signature.signature_id}")
```

#### 2. Verify Signature

```python
# Verify specific signature
is_valid = sig_mgr.verify_signature(signature.signature_id)

if is_valid:
    print("✓ Signature valid")
else:
    print("✗ Signature invalid")

# Verify all signatures on document
results = sig_mgr.verify_document("/path/to/submission.pdf")
print(f"Valid: {results['valid_signatures']}/{results['total_signatures']}")
```

#### 3. Export Manifest

```python
# Generate manifest for FDA submission
manifest = sig_mgr.export_manifest(
    document_path="/path/to/submission.pdf",
    generated_by=user,
    format='json'
)

# Save to file
with open('signature_manifest.json', 'w') as f:
    f.write(manifest)
```

## CLI Usage

The signature CLI provides command-line access to all signature functions.

### Apply Signature

```bash
python3 scripts/signature_cli.py sign \
    --document submission.pdf \
    --meaning author \
    --comments "Final review complete"
```

### Verify Signature

```bash
# Verify specific signature
python3 scripts/signature_cli.py verify --signature 123

# Verify document
python3 scripts/signature_cli.py verify --document submission.pdf
```

### List Signatures

```bash
# List signatures for document
python3 scripts/signature_cli.py list --document submission.pdf

# List signatures by user
python3 scripts/signature_cli.py list --user jsmith --verbose
```

### Revoke Signature

```bash
python3 scripts/signature_cli.py revoke \
    --signature 123 \
    --reason "User departed company"
```

### Export Manifest

```bash
# JSON format (default)
python3 scripts/signature_cli.py manifest \
    --document submission.pdf \
    --output manifest.json

# XML format
python3 scripts/signature_cli.py manifest \
    --document submission.pdf \
    --output manifest.xml \
    --format xml
```

### View Audit Trail

```bash
# Audit trail for signature
python3 scripts/signature_cli.py audit --signature 123 --verbose

# Audit trail for document
python3 scripts/signature_cli.py audit --document submission.pdf
```

## Signature Meanings

Per 21 CFR 11.50(a)(3), each signature must indicate its meaning:

- **author** - Document author/creator
- **reviewer** - Technical or quality reviewer
- **approver** - Final approval authority
- **witness** - Witnessing execution of activity
- **quality_assurance** - QA review/release
- **regulatory_affairs** - RA approval for submission
- **authorized_representative** - Company representative
- **consultant** - External expert review

## Multi-Signatory Workflows

### Standard Workflow

1. **Author** - Creates and signs document
2. **Reviewer** - Reviews and signs document
3. **Approver** - Provides final approval signature

```python
# Check workflow status
required = sig_mgr.get_required_signatories("submission.pdf")
for meaning, completed in required.items():
    status = "✓" if completed else "○"
    print(f"{status} {meaning.value}")

# Check if complete
if sig_mgr.is_workflow_complete("submission.pdf"):
    print("All required signatures present")
```

### Batch Signing

```python
# Sign multiple documents
results = sig_mgr.sign_document_batch(
    document_paths=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
    user=user,
    password="password",
    meaning=SignatureMeaning.AUTHOR
)

for path, success, signature, error in results:
    if success:
        print(f"✓ {path}: Signature {signature.signature_id}")
    else:
        print(f"✗ {path}: {error}")
```

## Security Features

### Cryptographic Binding

Signatures use HMAC-SHA256 to bind signature to document:

```python
signature_hash = HMAC-SHA256(
    secret_key,
    document_hash + user_id + timestamp + meaning
)
```

**Properties:**
- Cannot be excised (hash becomes invalid)
- Cannot be copied (hash unique to document)
- Cannot be transferred (hash binds to specific document)

### Tamper Detection

Document SHA-256 hash stored with signature. Verification fails if:
- Document modified
- Signature hash invalid
- Signature revoked
- User account invalid

### Authentication

Two-component authentication per 21 CFR 11.50(b):
1. **Component 1:** User session (proves identity)
2. **Component 2:** Password re-entry (knowledge factor)

## Audit Trail

All signature operations logged per 21 CFR 11.10(e):

**Events Logged:**
- Signature application
- Signature verification
- Signature verification failures
- Document tampering
- Signature revocation
- Manifest export

**Audit Record Contents:**
- Event type
- Timestamp (computer-generated)
- User performing action
- Signature/document affected
- Success/failure status
- Detailed event information

## Compliance

### 21 CFR Part 11 Requirements

| Requirement | Implementation | Status |
|------------|----------------|--------|
| §11.50(a)(1) - Printed name | `user_full_name` field | ✅ |
| §11.50(a)(2) - Date/time | `timestamp` field (ISO 8601) | ✅ |
| §11.50(a)(3) - Meaning | `meaning` field (enum) | ✅ |
| §11.50(b) - Authentication | Two-component (session + password) | ✅ |
| §11.70 - Signature linking | HMAC-SHA256 binding | ✅ |
| §11.100 - Unique to individual | User ID + full name | ✅ |
| §11.200 - Components | Username + password | ✅ |
| §11.300 - Password controls | Via FDA-185 auth system | ✅ |
| §11.10(e) - Audit trail | Complete event logging | ✅ |

**Full compliance documentation:** [ELECTRONIC_SIGNATURES_CFR_COMPLIANCE.md](ELECTRONIC_SIGNATURES_CFR_COMPLIANCE.md)

## Testing

### Run Full Test Suite

```bash
# All 40+ tests
pytest plugins/fda-tools/tests/test_signatures.py -v

# Specific test class
pytest plugins/fda-tools/tests/test_signatures.py::TestSignatureApplication -v

# Integration test
python3 plugins/fda-tools/tests/test_signatures_integration.py
```

### Test Coverage

- ✅ Signature application (6 tests)
- ✅ Signature verification (6 tests)
- ✅ Multi-signatory workflows (3 tests)
- ✅ Signature revocation (4 tests)
- ✅ Manifest generation (4 tests)
- ✅ Cryptographic functions (4 tests)
- ✅ Audit trail (4 tests)
- ✅ Signature retrieval (4 tests)

**Total:** 40+ tests

## Database Schema

### Signatures Table

```sql
CREATE TABLE signatures (
    signature_id INTEGER PRIMARY KEY,
    document_path TEXT NOT NULL,
    document_hash TEXT NOT NULL,        -- SHA-256
    user_id INTEGER NOT NULL,
    user_full_name TEXT NOT NULL,       -- §11.50(a)(1)
    timestamp TEXT NOT NULL,            -- §11.50(a)(2)
    meaning TEXT NOT NULL,              -- §11.50(a)(3)
    comments TEXT,
    authentication_method TEXT NOT NULL,
    signature_hash TEXT NOT NULL,       -- HMAC-SHA256
    status TEXT NOT NULL,
    revoked_at TEXT,
    revoked_by INTEGER,
    revocation_reason TEXT,
    created_at TEXT NOT NULL
);
```

### Audit Table

```sql
CREATE TABLE signature_audit (
    audit_id INTEGER PRIMARY KEY,
    event_type TEXT NOT NULL,
    signature_id INTEGER,
    document_path TEXT NOT NULL,
    user_id INTEGER,
    username TEXT,
    timestamp TEXT NOT NULL,
    details TEXT DEFAULT '{}',
    success INTEGER DEFAULT 1
);
```

## Architecture

```
┌────────────────────────────────────────────┐
│         Electronic Signatures               │
│          (lib/signatures.py)                │
├────────────────────────────────────────────┤
│                                             │
│  SignatureManager                           │
│  ├── sign_document()                        │
│  ├── verify_signature()                     │
│  ├── revoke_signature()                     │
│  ├── export_manifest()                      │
│  └── get_audit_trail()                      │
│                                             │
│  Cryptographic Functions                    │
│  ├── hash_file() - SHA-256                  │
│  ├── compute_signature_hash() - HMAC        │
│  └── verify_signature_hash()                │
│                                             │
└─────────────────┬──────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────┐
│       Authentication System                 │
│          (lib/auth.py - FDA-185)            │
├────────────────────────────────────────────┤
│  • User authentication                      │
│  • Password policy                          │
│  • Session management                       │
│  • Access control                           │
└────────────────────────────────────────────┘
```

## API Reference

### SignatureManager

**Main Class:** `lib.signatures.SignatureManager`

#### sign_document()

```python
def sign_document(
    document_path: str,
    user: User,
    password: str,
    meaning: SignatureMeaning,
    comments: Optional[str] = None
) -> Signature
```

Apply electronic signature to document.

**Parameters:**
- `document_path` - Absolute path to document
- `user` - Authenticated user object
- `password` - Password for re-authentication
- `meaning` - Signature meaning (SignatureMeaning enum)
- `comments` - Optional signature comments

**Returns:** Signature object

**Raises:**
- `FileNotFoundError` - Document doesn't exist
- `ValueError` - Authentication failed or user not authorized

#### verify_signature()

```python
def verify_signature(signature_id: int) -> bool
```

Verify signature integrity and validity.

**Checks:**
1. Signature exists and is active
2. Signature hash is valid
3. Document not tampered
4. User account valid

**Returns:** True if valid, False otherwise

#### verify_document()

```python
def verify_document(document_path: str) -> Dict
```

Verify all signatures on document.

**Returns:** Dictionary with verification results:
- `valid` - All signatures valid
- `total_signatures` - Number of signatures
- `valid_signatures` - Number of valid
- `invalid_signatures` - Number of invalid
- `signatures` - List of (signature, is_valid) tuples

#### export_manifest()

```python
def export_manifest(
    document_path: str,
    generated_by: Optional[User] = None,
    format: str = 'json'
) -> str
```

Export signature manifest.

**Parameters:**
- `document_path` - Path to document
- `generated_by` - User generating manifest (optional)
- `format` - 'json' or 'xml'

**Returns:** Manifest as JSON or XML string

## Troubleshooting

### Common Issues

**Issue:** "Authentication failed"
**Solution:** Ensure correct password for re-authentication. Password must match user account.

**Issue:** "Document not found"
**Solution:** Use absolute path to document. Verify file exists.

**Issue:** "Signature invalid after document modification"
**Solution:** This is expected - tamper detection working. Document must not be modified after signing.

**Issue:** "Permission denied on database"
**Solution:** Check file permissions on `~/.fda-tools/signatures.db`. Should be 0600.

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

### 1. Use Absolute Paths

Always use absolute paths for documents:

```python
from pathlib import Path
doc_path = Path("submission.pdf").resolve()
signature = sig_mgr.sign_document(str(doc_path), ...)
```

### 2. Verify Before Export

Always verify signatures before exporting manifest:

```python
results = sig_mgr.verify_document(doc_path)
if results['valid']:
    manifest = sig_mgr.export_manifest(doc_path)
```

### 3. Handle Revocation

Revoke signatures when users depart:

```python
sig_mgr.revoke_signature(
    signature_id=123,
    revoked_by=admin_user,
    reason="Employee departed 2026-02-20"
)
```

### 4. Preserve Audit Trail

Never delete signature or audit records. Use revocation instead.

### 5. Regular Backups

Backup signature database regularly:

```bash
cp ~/.fda-tools/signatures.db ~/.fda-tools/backups/signatures_$(date +%Y%m%d).db
```

## Support

**Documentation:**
- [Compliance Mapping](ELECTRONIC_SIGNATURES_CFR_COMPLIANCE.md)
- [Test Suite](../tests/test_signatures.py)
- [Integration Test](../tests/test_signatures_integration.py)

**Issue Tracking:**
- Linear: FDA-184
- Type: REG-001 (Regulatory compliance)

**Related Systems:**
- Authentication (FDA-185)
- Secure Config (FDA-182)

## License

Part of FDA Tools plugin for regulatory submissions.

---

**Implementation:** FDA-184 / REG-001
**Compliance:** 21 CFR Part 11
**Version:** 1.0.0
**Date:** 2026-02-20
