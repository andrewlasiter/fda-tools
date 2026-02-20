# MCP Integrity Verification

Quick reference for `mcp_integrity.py` - Subresource Integrity (SRI) verification for MCP server endpoints.

## Quick Start

### Verify all configured MCP servers

```bash
python3 -m lib.mcp_integrity verify
```

### Check verification status

```bash
python3 -m lib.mcp_integrity status
```

### Update hash after legitimate server update

```bash
python3 -m lib.mcp_integrity update --server c-trials --url https://mcp.deepsense.ai/clinical_trials/mcp
```

### Add fallback URL

```bash
python3 -m lib.mcp_integrity add-fallback --server c-trials --fallback-url https://backup-url.com/mcp
```

## Programmatic Usage

```python
from fda_tools.lib.mcp_integrity import MCPIntegrityVerifier

verifier = MCPIntegrityVerifier()

# Verify all servers
results = verifier.verify_all_servers()
if not all(results.values()):
    print("⚠️  Some servers failed verification")

# Verify specific server
is_valid = verifier.verify_server(
    "c-trials",
    "https://mcp.deepsense.ai/clinical_trials/mcp"
)

# Get comprehensive status
status = verifier.get_verification_status()
print(f"Verified: {status['verified_servers']}/{status['total_servers']}")
```

## Files

- **Module**: `lib/mcp_integrity.py` (520 lines)
- **Tests**: `tests/test_mcp_integrity.py` (22 tests, all passing)
- **Config**: `.mcp.json` (MCP server URLs)
- **Integrity Data**: `.mcp.integrity.json` (SHA-384 hashes)
- **Documentation**: `docs/MCP_SECURITY_GUIDE.md`

## Security Model

- Each MCP server response is hashed using SHA-384
- Hashes are pinned on first verification
- Subsequent requests must match the pinned hash
- Verification failures trigger security warnings
- Fallback URLs can be configured for critical servers

## References

- **Issue**: FDA-113 - MCP Server URL Security
- **CWE**: CWE-494 - Download of Code Without Integrity Check
- **Spec**: W3C Subresource Integrity (SRI)
