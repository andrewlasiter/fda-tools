# MCP Server Security Guide (FDA-113)

## Overview

This document describes the security controls for MCP (Model Context Protocol) server integrity verification implemented to address **CWE-494: Download of Code Without Integrity Check**.

## Threat Model

### Threat: Supply Chain Attack on MCP Servers

**Attack Vector**: An adversary compromises an MCP server endpoint or performs a man-in-the-middle (MITM) attack, causing the plugin to load malicious code or receive tampered data.

**Risk Level**: HIGH

**Impact**:
- Execution of malicious code within the plugin context
- Data exfiltration from FDA projects
- Tampering with regulatory submission data
- Credential theft from environment variables

### Mitigation: Subresource Integrity (SRI) Verification

**Control**: All MCP server responses are verified against cryptographic hashes (SHA-384) before being trusted.

**Implementation**: `lib/mcp_integrity.py`

## Security Architecture

### Components

1. **Integrity Hash Store** (`.mcp.integrity.json`)
   - Stores pinned SHA-384 hashes for each MCP server
   - Includes verification timestamps and fallback URLs
   - Persisted alongside `.mcp.json` configuration

2. **Verification Module** (`lib/mcp_integrity.py`)
   - Computes SRI hashes of MCP server responses
   - Compares against stored hashes
   - Enforces hash matching before allowing server use

3. **CLI Tool** (`python3 -m lib.mcp_integrity`)
   - Manual verification and hash management
   - Status monitoring and audit reporting

### Security Properties

✓ **Integrity**: SHA-384 hashes detect any tampering with MCP server responses
✓ **Pinning**: Hashes are pinned on first use and must match on subsequent uses
✓ **Audit Trail**: All verification events are logged with timestamps
✓ **Fallback Support**: Backup URLs can be configured for critical services
✓ **Defense in Depth**: Works alongside TLS verification (FDA-107)

## Usage

### Initial Setup

When you first configure an MCP server, run verification to establish baseline hashes:

```bash
python3 -m lib.mcp_integrity verify
```

This will:
1. Fetch each MCP server endpoint
2. Compute SHA-384 hash of the response
3. Store hash in `.mcp.integrity.json`
4. Set `pinned: true` to enforce verification

### Ongoing Verification

**Before loading MCP servers** (automated):
```python
from fda_tools.lib.mcp_integrity import MCPIntegrityVerifier

verifier = MCPIntegrityVerifier()
results = verifier.verify_all_servers()

if not all(results.values()):
    raise SecurityError("MCP server integrity verification failed")
```

**Manual verification** (periodic audits):
```bash
python3 -m lib.mcp_integrity verify --verbose
```

### Legitimate Server Updates

When an MCP server legitimately updates (e.g., bug fix, new features), verification will fail:

```
✗ Hash mismatch for c-trials:
  Expected: sha384-CCIb+J4aPjONTQ64K+9VRQJblQ6Q0hMYQ8oasxJWM5VFT9jm/1clyzCkW9rSzCkL
  Actual:   sha384-NEW_HASH_HERE
```

**Action**: Investigate the change, then update hash if legitimate:

```bash
# Verify server update is legitimate (check release notes, contact vendor)
# Then update hash:
python3 -m lib.mcp_integrity update --server c-trials --url https://mcp.deepsense.ai/clinical_trials/mcp
```

### Handling Verification Failures

**Scenario 1: Hash Mismatch (Potential Attack)**

```
ERROR: Integrity verification failed for c-trials. Hash mismatch detected.
This may indicate a supply chain attack or legitimate server update.
```

**Response**:
1. **DO NOT** ignore or bypass the error
2. Investigate server changelog/release notes
3. Contact server operator to confirm legitimacy
4. Compare hash changes using: `python3 -m lib.mcp_integrity status`
5. Only update hash after confirming legitimacy

**Scenario 2: Server Unreachable**

```
WARNING: Failed to fetch c-trials: Connection timeout
```

**Response**:
1. Check network connectivity
2. Verify server status at vendor's status page
3. Try fallback URLs if configured
4. Temporarily disable MCP integration if critical

### Fallback Configuration

For production systems, configure backup URLs:

```bash
python3 -m lib.mcp_integrity add-fallback \
  --server c-trials \
  --fallback-url https://backup.mcp.deepsense.ai/clinical_trials/mcp
```

Edit `.mcp.integrity.json` to see all fallbacks:
```json
{
  "servers": { ... },
  "fallbacks": {
    "c-trials": [
      "https://backup.mcp.deepsense.ai/clinical_trials/mcp"
    ]
  }
}
```

## Integration with Other Security Controls

This control works alongside:

- **TLS Certificate Verification** (FDA-107): Prevents MITM during transport
- **Subprocess Allowlisting** (FDA-129): Prevents execution of arbitrary commands
- **Path Validation** (FDA-111): Prevents directory traversal attacks

Together, these provide defense-in-depth for supply chain security.

## Monitoring and Auditing

### Verification Status Dashboard

```bash
python3 -m lib.mcp_integrity status
```

Output:
```json
{
  "total_servers": 2,
  "verified_servers": 1,
  "unverified_servers": 1,
  "servers": {
    "c-trials": {
      "url": "https://mcp.deepsense.ai/clinical_trials/mcp",
      "has_integrity_hash": true,
      "last_verified": "2026-02-20T10:30:00Z",
      "pinned": true,
      "fallbacks": []
    }
  }
}
```

### Audit Log Review

All verification events are logged:

```
INFO: Verifying MCP server: c-trials at https://mcp.deepsense.ai/clinical_trials/mcp
INFO: ✓ Verification passed for c-trials
```

```
ERROR: ✗ Hash mismatch for c-trials:
  Expected: sha384-[original]
  Actual:   sha384-[new]
```

Review logs regularly for:
- Unexpected verification failures
- Frequent hash updates (may indicate instability or compromise)
- Unreachable servers

## Limitations

### Known Limitations

1. **Initial Trust**: First-time verification establishes baseline hash without external validation
   - **Mitigation**: Verify hashes through out-of-band channels (vendor documentation, checksums)

2. **Dynamic Content**: Some MCP servers may return dynamic content
   - **Impact**: Hash verification will fail on every request
   - **Mitigation**: Disable integrity verification for dynamic endpoints (NOT RECOMMENDED)

3. **Update Frequency**: Legitimate updates require manual hash updates
   - **Mitigation**: Subscribe to server update notifications, automate verification in CI/CD

### Not Protected Against

- **Initial Compromise**: If server is compromised on first use
- **Vendor Account Takeover**: If attacker controls vendor's deployment
- **Social Engineering**: Tricking admin to accept malicious hash updates

**Defense**: Use multiple signals (release notes, vendor announcements, community reports) before updating hashes.

## Compliance

This control addresses:

- **OWASP Top 10**: A06:2021 - Vulnerable and Outdated Components
- **CWE-494**: Download of Code Without Integrity Check
- **NIST SP 800-218**: SSDF - Verify integrity of software components
- **FDA Guidance**: Cybersecurity for Medical Devices (Premarket)

## References

- **SRI Specification**: https://www.w3.org/TR/SRI/
- **CWE-494**: https://cwe.mitre.org/data/definitions/494.html
- **OWASP Dependency Check**: https://owasp.org/www-project-dependency-check/
- **Supply Chain Levels for Software Artifacts (SLSA)**: https://slsa.dev/

## Implementation Details

**Module**: `plugins/fda_tools/lib/mcp_integrity.py`
**Tests**: `plugins/fda_tools/tests/test_mcp_integrity.py`
**Issue**: FDA-113 - MCP Server URL Security
**Date Implemented**: 2026-02-20
