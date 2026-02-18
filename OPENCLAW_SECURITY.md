# OpenClaw Integration Security Audit (FDA-90)

**Date:** 2026-02-18
**Type:** Security Review and Threat Model
**Status:** REVIEW COMPLETE
**Risk Level:** MEDIUM (with existing mitigations)
**Reviewer:** Security Audit Team

---

## Executive Summary

This document presents a comprehensive security audit of the OpenClaw integration layer, which connects the TypeScript-based OpenClaw skill to the FDA Tools Python backend via an HTTP REST bridge server. The integration architecture involves three components: (1) the OpenClaw TypeScript skill (`openclaw-skill/`), (2) the HTTP bridge server (`plugins/fda-tools/bridge/server.py`), and (3) the FDA Tools Python backend (`plugins/fda-tools/scripts/`).

**Overall Assessment:** The integration implements reasonable security controls for a localhost-only bridge, including API key authentication, rate limiting, request sanitization, and constant-time key comparison. However, several areas require hardening before any production or multi-user deployment.

---

## 1. Architecture Overview

```
OpenClaw Skill (TypeScript)
    |
    | HTTP REST (localhost:18790)
    | X-API-Key authentication
    |
FDA Bridge Server (Python/FastAPI)
    |
    | Direct Python imports
    |
FDA Tools Backend (Python scripts)
    |
    | HTTPS
    |
openFDA Public APIs
```

### Component Inventory

| Component | Language | Location | Purpose |
|-----------|----------|----------|---------|
| Bridge Server | Python 3 | `plugins/fda-tools/bridge/server.py` | HTTP REST API gateway |
| Bridge Client | TypeScript | `openclaw-skill/bridge/client.ts` | HTTP client with retry logic |
| Type Definitions | TypeScript | `openclaw-skill/bridge/types.ts` | Shared type contracts |
| Tool Handlers | TypeScript | `openclaw-skill/tools/fda_*.ts` | OpenClaw tool wrappers |
| API Key Manager | Python 3 | `plugins/fda-tools/scripts/setup_api_key.py` | Key storage (keyring/file) |

---

## 2. Threat Model

### 2.1 Threat Actors

| Actor | Capability | Motivation |
|-------|-----------|------------|
| **T1: Local malicious process** | Can make HTTP requests to localhost:18790 | Extract FDA data, inject commands |
| **T2: Network attacker (same LAN)** | Can intercept unencrypted traffic | Steal API keys, session data |
| **T3: Malicious OpenClaw skill** | Can invoke bridge endpoints | Execute unauthorized FDA commands |
| **T4: Supply chain attacker** | Can compromise npm/pip dependencies | Inject backdoors |
| **T5: Insider with log access** | Can read server logs and audit trails | Extract sensitive data from logs |

### 2.2 Assets at Risk

| Asset | Classification | Impact if Compromised |
|-------|---------------|----------------------|
| openFDA API key | RESTRICTED | Rate limit abuse, attribution issues |
| Bridge API key | RESTRICTED | Unauthorized command execution |
| FDA submission data | CONFIDENTIAL | Competitive intelligence, regulatory strategy exposure |
| Session data | RESTRICTED | User impersonation, data leakage |
| Audit logs | RESTRICTED | Compliance failure, evidence tampering |

### 2.3 Attack Scenarios

#### AS-1: Local Process API Key Theft (T1, MEDIUM)

**Vector:** A malicious local process sends GET requests to the unauthenticated `/health` endpoint or attempts to brute-force the bridge API key.

**Current Mitigation:** API key required for all endpoints except `/health`. Rate limiting (60 req/min default). Constant-time key comparison prevents timing attacks.

**Residual Risk:** The `/health` endpoint discloses operational details (session count, command count, LLM provider status). A 32-byte hex key (256 bits) is infeasible to brute-force.

**Recommendation:**
- Minimize information in `/health` response (remove session count, command count)
- Consider IP allowlisting (127.0.0.1 only, which is already the bind address)

#### AS-2: API Key Exposure in Logs (T5, HIGH -- now MITIGATED by FDA-84)

**Vector:** The bridge server previously logged the full API key on first startup (line 154 of server.py). Log files accessible to operations staff would expose the key.

**Current Mitigation (FDA-84):** Bridge server now logs only masked key (`xxxx...yyyy`). Full key printed to stdout only (not structured logs). `APIKeyRedactor` logging filter installed globally.

**Residual Risk:** The full key is still printed to stdout on first generation. This is by design (operator must capture it) but stdout should not be redirected to persistent files.

**Recommendation:**
- Document that stdout should not be logged to persistent files during first startup
- Consider a dedicated key-display command separate from server startup

#### AS-3: Session Hijacking (T1/T3, MEDIUM)

**Vector:** Session IDs are UUIDs stored in-memory. If an attacker obtains a valid session ID (e.g., from logs), they can access session data and submit answers to pending questions.

**Current Mitigation:** All session endpoints require API key authentication. Session IDs are UUID4 (122 bits of randomness).

**Residual Risk:** No session-to-user binding enforcement. Any authenticated request can access any session. No session expiration.

**Recommendation:**
- Enforce user_id matching on session access (session owner only)
- Add session expiration (e.g., 24 hours)
- Add session invalidation endpoint

#### AS-4: Command Injection via Execute Endpoint (T3, LOW)

**Vector:** The `/execute` endpoint accepts a `command` string and `args` string. Malicious input could attempt to inject shell commands.

**Current Mitigation:** The current implementation does NOT use subprocess execution. Commands are resolved by filename lookup in the commands directory (`COMMANDS_DIR / f"{command}.md"`). Path traversal in command names is limited because the filename must match an existing `.md` file.

**Residual Risk:** If the implementation transitions to subprocess-based execution (as noted in the "TODO: Phase 2" comments), command injection becomes a critical risk.

**Recommendation:**
- Validate command names against an allowlist (alphanumeric + hyphens only)
- Never pass `args` to shell interpreters
- Use `subprocess.run()` with `shell=False` if subprocess execution is needed
- Input validation regex: `^[a-z0-9-]{1,50}$` for command names

#### AS-5: Unencrypted Localhost Communication (T2, LOW)

**Vector:** The bridge communicates over plain HTTP on localhost:18790. On a multi-user system or with port forwarding, traffic could be intercepted.

**Current Mitigation:** Server binds to 127.0.0.1 only. CORS restricted to localhost origins.

**Residual Risk:** On shared systems, other users may be able to sniff localhost traffic. The CORS configuration uses wildcard ports (`http://localhost:*`) which is overly permissive.

**Recommendation:**
- Consider TLS for the bridge (self-signed cert is acceptable for localhost)
- Restrict CORS to the specific port used by the OpenClaw client
- Add environment variable to configure allowed origins

#### AS-6: Dependency Supply Chain (T4, MEDIUM)

**Vector:** The TypeScript skill depends on npm packages. The Python bridge depends on FastAPI, uvicorn, slowapi, and pydantic. Any compromised dependency could inject malicious code.

**Current Mitigation:** None explicit. No lock file integrity verification. No dependency audit workflow.

**Recommendation:**
- Pin dependency versions in `package.json` and `requirements.txt`
- Run `npm audit` and `pip-audit` in CI/CD
- Use `package-lock.json` integrity hashes
- Consider vendoring critical dependencies

#### AS-7: Data Classification Bypass (T3, MEDIUM)

**Vector:** The bridge defines data classification levels (PUBLIC, RESTRICTED, CONFIDENTIAL) but enforcement is not yet implemented. The current implementation marks everything as PUBLIC.

**Current Mitigation:** Classification field exists in response types. Comments indicate Phase 2 will implement the SecurityGateway.

**Residual Risk:** Without enforcement, CONFIDENTIAL data (company documents, draft submissions) could be sent through cloud LLM providers or messaging channels.

**Recommendation:**
- Implement SecurityGateway before handling any non-PUBLIC data
- Add classification enforcement middleware
- Block CONFIDENTIAL data on non-file channels
- Log classification decisions in audit trail

#### AS-8: Audit Log Tampering (T1/T5, MEDIUM)

**Vector:** Audit logs are stored in-memory (`AUDIT_LOG` list). They are lost on server restart and can be modified by any code with access to the global variable. The integrity check endpoint always returns `valid: True`.

**Current Mitigation:** Audit entries include timestamps. The sanitize_for_logging function removes sensitive data.

**Residual Risk:** No cryptographic integrity chain. No persistence. No tamper detection.

**Recommendation:**
- Implement append-only file-based audit logging
- Add cryptographic hash chains (each entry hashes the previous entry)
- Implement actual integrity verification in `/audit/integrity`
- Back up audit logs to separate storage

---

## 3. Security Controls Assessment

### 3.1 Authentication

| Control | Status | Grade |
|---------|--------|-------|
| API key required for protected endpoints | Implemented | B+ |
| Constant-time key comparison (timing attack prevention) | Implemented | A |
| Key stored in OS keyring | Implemented | A |
| Key auto-generation on first startup | Implemented | B |
| Environment variable override | Implemented | B |
| Key rotation mechanism | Not implemented | F |
| Multi-user authentication | Not implemented | N/A (single-user) |

### 3.2 Authorization

| Control | Status | Grade |
|---------|--------|-------|
| Endpoint-level access control | Implemented (auth/unauth) | B |
| Command-level authorization | Not implemented | D |
| Session-level authorization | Not implemented | D |
| Data classification enforcement | Not implemented | F |
| Role-based access control | Not implemented | N/A (single-user) |

### 3.3 Input Validation

| Control | Status | Grade |
|---------|--------|-------|
| Request body validation (Pydantic) | Implemented | A |
| Command name validation | Partial (file existence check) | C |
| Args sanitization | Not implemented | D |
| Session ID validation | Partial (UUID format) | C |
| Path traversal prevention | Not explicit in bridge | C |

### 3.4 Logging and Monitoring

| Control | Status | Grade |
|---------|--------|-------|
| Request/response logging | Implemented | B+ |
| Sensitive field sanitization | Implemented | A- |
| API key redaction in logs (FDA-84) | Implemented | A |
| Auth failure logging | Implemented | A |
| Audit trail | Partial (in-memory only) | C |
| Alerting on suspicious activity | Not implemented | F |

### 3.5 Network Security

| Control | Status | Grade |
|---------|--------|-------|
| Localhost-only binding | Implemented | A |
| CORS configuration | Partial (wildcard ports) | C+ |
| TLS encryption | Not implemented | D |
| Rate limiting | Implemented (optional) | B |
| Request size limits | Not explicit | D |

---

## 4. Recommendations Summary

### Critical (Address Before Production)

1. **Implement data classification enforcement (SecurityGateway)** -- Without this, CONFIDENTIAL data has no protection against leakage through cloud LLMs or messaging channels.

2. **Add command name input validation** -- Enforce strict regex `^[a-z0-9-]{1,50}$` for command names to prevent any future injection vectors.

3. **Implement persistent audit logging** -- Replace in-memory audit log with append-only file storage and cryptographic hash chains.

### High Priority

4. **Add session expiration and owner enforcement** -- Sessions should expire after inactivity and be accessible only by their creator.

5. **Restrict CORS origins to specific ports** -- Replace `http://localhost:*` with explicit allowed origins.

6. **Pin all dependency versions** -- Add integrity verification for npm and pip dependencies.

7. **Add key rotation mechanism** -- Allow generating new bridge API keys without server restart.

### Medium Priority

8. **Minimize /health endpoint information disclosure** -- Remove session counts and command counts from unauthenticated endpoint.

9. **Add request body size limits** -- Prevent denial-of-service via oversized request bodies.

10. **Consider TLS for bridge communication** -- Even on localhost, TLS prevents local sniffing on shared systems.

11. **Run dependency audits in CI/CD** -- Automate `npm audit` and `pip-audit` checks.

### Low Priority

12. **Add structured logging format** -- JSON-formatted logs are easier to parse and monitor.

13. **Implement circuit breaker for backend calls** -- Prevent cascading failures.

14. **Add request tracing (correlation IDs)** -- Improve debugging and audit trail linkage.

---

## 5. Files Reviewed

| File | Lines | Security-Relevant Findings |
|------|-------|---------------------------|
| `plugins/fda-tools/bridge/server.py` | 929 | API key logging (fixed by FDA-84), in-memory sessions/audit, CORS wildcard |
| `plugins/fda-tools/bridge/__init__.py` | 8 | No issues |
| `openclaw-skill/bridge/client.ts` | 654 | Good retry logic, API key from env var, no key logging |
| `openclaw-skill/bridge/types.ts` | 474 | Well-typed, classification levels defined |
| `openclaw-skill/tools/fda_validate.ts` | -- | Tool wrapper, delegates to bridge |
| `openclaw-skill/tools/fda_analyze.ts` | -- | Tool wrapper, delegates to bridge |
| `openclaw-skill/tools/fda_draft.ts` | -- | Tool wrapper, delegates to bridge |
| `plugins/fda-tools/scripts/setup_api_key.py` | 434+ | Keyring storage, API key redaction (FDA-84) |
| `plugins/fda-tools/scripts/agent_registry.py` | 958+ | Path traversal fix (FDA-83), YAML safety (FDA-85) |

---

## 6. Compliance Notes

- This security audit is for **internal review purposes only**
- The FDA Tools plugin processes regulatory data; security controls should be proportional to data sensitivity
- The OpenClaw bridge is currently a **development/prototype** implementation with placeholder command execution
- Before any production deployment handling actual submission data, all CRITICAL recommendations must be addressed
- Regular security reviews should be conducted quarterly or after significant architecture changes

---

## Appendix A: CORS Configuration Detail

Current configuration (server.py lines 308-315):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Issue:** Wildcard port matching may not work as expected with Starlette's CORS middleware. The `*` in URLs is not a glob -- it is treated literally. This means CORS may be MORE restrictive than intended (rejecting all cross-origin requests) or, if a future Starlette version changes behavior, LESS restrictive.

**Recommended fix:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",     # Common dev port
        "http://localhost:18790",    # Self
        "http://127.0.0.1:18790",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)
```

## Appendix B: Rate Limiting Configuration

Current defaults:
- General endpoints: 60 requests/minute
- Execute endpoint: 30 requests/minute
- Rate limiting is OPTIONAL (depends on `slowapi` installation)

**Risk:** If slowapi is not installed, rate limiting is silently disabled. The only indication is a log warning at startup.

**Recommended fix:** Make rate limiting mandatory or implement a basic fallback rate limiter using in-memory counters.

## Appendix C: Key Generation and Storage Flow

```
First Startup:
  1. Check FDA_BRIDGE_API_KEY env var
  2. If set: use it, hash for comparison
  3. If not: check OS keyring (via setup_api_key module)
  4. If keyring has key: use it
  5. If no key anywhere: generate 32-byte hex token
  6. Store in keyring (if available)
  7. Display to stdout (masked in logs per FDA-84)

Subsequent Requests:
  1. Extract X-API-Key header
  2. SHA-256 hash the provided key
  3. Compare with cached hash (constant-time)
  4. Accept or reject (401)
```

This flow is sound. The use of SHA-256 hashing with `secrets.compare_digest` provides proper timing-attack resistance.
