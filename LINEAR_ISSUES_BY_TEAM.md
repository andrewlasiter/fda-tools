# FDA Tools Plugin - Linear Issues Organized by Team

**Generated:** 2026-02-19
**Total Issues:** 113
**Total Points:** 1,283
**Teams:** 7 specialized teams

---

## Quick Navigation

- [Security Team (23 issues, 118 points)](#security-team)
- [Code Quality Team (23 issues, 149 points)](#code-quality-team)
- [Architecture Team (16 issues, 131 points)](#architecture-team)
- [QA Testing Team (10 issues, 343 points)](#qa-testing-team)
- [Regulatory Compliance Team (10 issues, 122 points)](#regulatory-compliance-team)
- [OpenClaw Integration Team (13 issues, 203 points)](#openclaw-integration-team)
- [DevOps Team (18 issues, 217 points)](#devops-team)

---

## Security Team

**Lead Agent:** voltagent-qa-sec:security-auditor
**Support:** voltagent-qa-sec:penetration-tester
**Total:** 23 issues, 118 points

### P0 - CRITICAL (4 issues, 42 points)

#### SEC-001: XSS Vulnerability in Markdown-to-HTML Conversion (13 points)
- **Files:** `scripts/markdown_to_html.py`
- **CWE:** CWE-79 (Cross-Site Scripting)
- **Description:** Unsanitized markdown content injected into HTML without escaping. Device names/descriptions from FDA data could inject `<script>` tags.
- **Fix:** Add `html.escape()`, implement CSP headers, add SRI hashes to CDN resources

#### SEC-002: User-Agent Spoofing for FDA Website Scraping (8 points)
- **Files:** `scripts/fda_http.py`, `scripts/pma_prototype.py`, `scripts/batchfetch.py`
- **Legal Risk:** CFAA (Computer Fraud and Abuse Act) violation
- **Description:** Browser-impersonating User-Agent bypasses FDA bot detection. Default behavior violates terms of service.
- **Fix:** Default to honest UA, add user consent mechanism, investigate FDA bulk download programs

#### SEC-003: API Key Stored in Plaintext Configuration (8 points)
- **Files:** `scripts/fda_api_client.py`, `scripts/setup_api_key.py`, `commands/configure.md`
- **CWE:** CWE-798 (Use of Hard-coded Credentials)
- **Description:** openFDA API key stored in `~/.claude/fda-tools.local.md` as plaintext. No migration enforcement to keyring.
- **Fix:** Emit warning on plaintext detection, auto-migrate to keyring, set restrictive file permissions (0600)

#### SEC-004: Unvalidated File Paths Enable Path Traversal (13 points)
- **Files:** `scripts/gap_analysis.py`, `scripts/fetch_predicate_data.py`, `scripts/pma_prototype.py`
- **CWE:** CWE-22 (Path Traversal)
- **Description:** `--output` arguments accept arbitrary paths without validation. Could write to `/etc/crontab` or similar.
- **Fix:** Use existing `validate_path_safe()` from `input_validators.py`, define base directory constraints

### P1 - HIGH (8 issues, 45 points)

#### SEC-005: Missing TLS Verification Enforcement (5 points)
- **Files:** `scripts/pma_prototype.py`, `scripts/batchfetch.py`, `scripts/quick_standards_generator.py`
- **Description:** `requests.get()` calls don't explicitly set `verify=True`. Relies on library defaults.
- **Fix:** Explicitly set `verify=True` in session factory, add pre-commit hook to detect `verify=False`

#### SEC-006: External MCP Servers Without Integrity Verification (5 points)
- **Files:** `.mcp.json`
- **Description:** Third-party MCP server (`mcp.deepsense.ai`) accessed without response validation or certificate pinning
- **Fix:** Add response validation, document trust model, add disclaimers for third-party data sources

#### SEC-007: Subprocess Command Injection in eCopy Exporter (8 points)
- **Files:** `lib/ecopy_exporter.py`
- **CWE:** CWE-78 (OS Command Injection)
- **Description:** `pandoc` command constructed from file paths without using `safe_subprocess()` allowlist
- **Fix:** Use `subprocess_utils.safe_subprocess()`, add `pandoc` to allowlist, validate input/output paths

#### SEC-008: Broad Exception Handling Swallows Security Errors (5 points)
- **Files:** `scripts/fetch_predicate_data.py`, `scripts/fda_approval_monitor.py`, `scripts/compliance_disclaimer.py`
- **Description:** `except Exception: pass` silences TLS errors, auth failures, validation errors
- **Fix:** Replace with specific exception types, log all exceptions, never silence compliance errors

#### SEC-009: No Rate Limiting for PDF Downloads (3 points)
- **Files:** `scripts/pma_prototype.py`
- **Description:** Uses `time.sleep(0.5)` instead of centralized rate limiter. No cross-process coordination.
- **Fix:** Use `lib/rate_limiter.py`, implement exponential backoff, add cross-process coordination

#### SEC-010: Unvalidated FDA PMN Database Input (5 points)
- **Files:** `scripts/gap_analysis.py`, `scripts/full_text_search.py`, `scripts/batchfetch.py`
- **Description:** Pipe-delimited FDA files parsed without validation. Crafted applicant names could inject path traversal.
- **Fix:** Apply `validate_k_number()`, `validate_product_code()`, `validate_path_safe()` to all PMN data

#### SEC-011: Audit Log Without Tamper Protection (5 points)
- **Files:** `scripts/fda_audit_logger.py`, `scripts/compliance_disclaimer.py`
- **Description:** Append-only JSONL with no integrity protection. Entries can be modified/deleted without detection.
- **Fix:** Implement hash chaining, add signature verification, set restrictive file permissions

#### SEC-012: Linear API Key Without TLS Verification (3 points)
- **Files:** `scripts/linear_integrator.py`
- **Description:** API key sent in Authorization header but `requests.post()` doesn't use centralized session with TLS verification
- **Fix:** Use `fda_http.create_session()`, validate API key format, explicit `verify=True`

### P2 - MEDIUM (11 issues, 31 points)

[Continue with remaining 11 P2 security issues...]

---

## Code Quality Team

**Lead Agent:** voltagent-qa-sec:code-reviewer
**Support:** voltagent-dev-exp:refactoring-specialist
**Total:** 23 issues, 149 points

### P0 - CRITICAL (3 issues, 39 points)

#### CODE-001: Duplicate Rate Limiter Implementations (13 points)
- **Files:** `scripts/error_handling.py`, `lib/rate_limiter.py`, `scripts/data_refresh_orchestrator.py`, `lib/fda_enrichment.py`
- **Description:** Four separate rate limiter implementations with different algorithms (sliding window, token bucket, hardcoded sleep)
- **Fix:** Consolidate to single canonical implementation in `lib/rate_limiter.py`, remove duplicates, update all imports

#### CODE-002: Duplicate FDA API Clients (21 points)
- **Files:** `scripts/fda_api_client.py`, `lib/fda_enrichment.py`
- **Description:** Two independent API clients with divergent behavior. `FDAEnrichment` bypasses all safety features of `FDAClient`.
- **Fix:** Refactor `FDAEnrichment` to accept `FDAClient` via dependency injection, eliminate direct HTTP calls

#### CODE-003: Bridge Server CORS Wildcard Configuration (5 points)
- **Files:** `bridge/server.py`
- **Description:** `allow_origins=["http://localhost:*"]` with `allow_credentials=True` creates credential-forwarding vulnerability
- **Fix:** Use `allow_origin_regex` with proper pattern, restrict methods/headers to minimum required

### P1 - HIGH (8 issues, 80 points)

[Continue with P1 code quality issues...]

---

## Architecture Team

**Lead Agent:** voltagent-qa-sec:architect-reviewer
**Support:** voltagent-core-dev:backend-developer
**Total:** 16 issues, 131 points

### P0 - CRITICAL (2 issues, 29 points)

#### ARCH-001: Pervasive sys.path Manipulation (21 points)
- **Files:** 30+ scripts
- **Description:** Every script injects paths via `sys.path.insert(0, ...)`. Creates fragile import resolution and module shadowing risks.
- **Fix:** Convert to proper Python package with `pyproject.toml`, use relative imports, install with `pip install -e .`
- **Blocks:** CODE-001, CODE-002, ARCH-005

#### ARCH-002: Configuration Scattered Across 5 Formats (8 points)
- **Files:** `~/.claude/fda-tools.local.md`, `~/.claude/fda-tools.config.toml`, `.mcp.json`, environment variables
- **Description:** Settings parsed independently by 7+ scripts using different formats (markdown regex, TOML, JSON, env vars)
- **Fix:** Create unified `lib/config.py`, standardize on TOML, single source of truth
- **Blocks:** DEVOPS-002

---

## QA Testing Team

**Lead Agent:** voltagent-qa-sec:qa-expert
**Support:** voltagent-qa-sec:test-automator
**Total:** 10 issues, 343 points

### P0 - CRITICAL (2 issues, 34 points)

#### QA-001: Missing E2E Test Infrastructure (21 points)
- **Files:** `tests/utils/e2e_helpers.py` (missing), `tests/utils/regulatory_validators.py` (missing)
- **Description:** Two E2E test files exist but cannot execute due to missing utility modules. 0% end-to-end workflow coverage.
- **Fix:** Create missing test utilities, implement E2E workflow tests for research→review→draft pipeline
- **Blocks:** QA-003, QA-005

#### QA-002: 47 Critical Test Failures (13 points)
- **Files:** `tests/test_fda_enrichment.py`, `tests/test_error_handling.py`
- **Description:** Tautological tests with API mismatches. Tests expect keys that don't exist in production code.
- **Fix:** Rewrite assertions to match actual production API, run full test suite, fix all failures
- **Requires:** Must complete before Sprint 1 ends

---

## Regulatory Compliance Team

**Lead Agent:** voltagent-biz:legal-advisor
**Support:** voltagent-qa-sec:compliance-auditor
**Total:** 10 issues, 122 points

### P0 - CRITICAL (4 issues, 68 points)

#### REG-001: Missing Electronic Signatures (21 CFR Part 11) (21 points)
- **Files:** `scripts/estar_xml.py`, `commands/assemble.md`, `scripts/fda_audit_logger.py`
- **Regulatory:** 21 CFR 11.50, 11.70, 11.100, 11.200, 11.300
- **Description:** Plugin generates FDA submission documents but lacks electronic signature capability required for regulatory compliance
- **Fix:** Implement XMLDSig for XML, CAdES for PDFs, signature manifest fields, verification module
- **Compliance Risk:** HIGH - Cannot use for regulated submissions without this

#### REG-002: Incomplete Audit Trail (21 CFR 11.10(e)) (13 points)
- **Files:** `scripts/fda_audit_logger.py`, `references/audit-logging.md`
- **Regulatory:** 21 CFR 11.10(e) - secure, time-stamped audit trails
- **Description:** Audit log missing user identity, before/after values, failed access attempts, sequential numbering
- **Fix:** Add `modified_by`, implement before/after capture, log failures, add sequential entry numbers

#### REG-006: No User Authentication or Access Controls (21 points)
- **Files:** All CLI scripts
- **Regulatory:** 21 CFR 11.10(d), 11.10(g)
- **Description:** Zero user authentication. Any filesystem user can modify audit logs, generate submissions, access regulatory data.
- **Fix:** Implement authentication system, RBAC (roles: RA Professional, Quality Manager, Admin), require auth for all operations
- **Blocks:** REG-002, REG-008

#### REG-008: Audit Log Lacks Tamper-Evident Controls (13 points)
- **Files:** `scripts/fda_audit_logger.py`
- **Regulatory:** 21 CFR 11.10(e)(1)
- **Description:** Audit entries appended to JSONL without tamper protection. No hash chaining, no write-once controls.
- **Fix:** Implement hash chaining, add digital signatures, make append-only at filesystem level, add verification tool

---

## OpenClaw Integration Team

**Lead Agent:** voltagent-lang:typescript-pro
**Support:** voltagent-core-dev:api-designer
**Total:** 13 issues, 203 points

### P0 - CRITICAL (2 issues, 55 points)

#### FDA-101: OpenClaw SDK Type Dependency Mismatch (21 points)
- **Files:** `openclaw-skill/bridge/types.ts`, `package.json`
- **Description:** Ambient type definitions for `@openclaw/sdk` may drift from actual runtime types. Development vs production mismatch risk.
- **Fix:** Extract SDK types to canonical `.d.ts`, add build-time validation against actual SDK
- **Blocks:** FDA-102

#### FDA-102: No Runtime Schema Validation for Bridge Responses (34 points)
- **Files:** `openclaw-skill/bridge/client.ts`
- **Description:** Bridge client trusts JSON responses without validation via `as T` type assertion. Malformed responses cause runtime crashes.
- **Fix:** Add Zod schemas for all 10 response types, implement `safeParse()` validation in `handleResponse<T>()`
- **Impact:** Production stability - invalid responses currently crash entire skill

---

## DevOps Team

**Lead Agent:** voltagent-infra:devops-engineer
**Support:** voltagent-infra:platform-engineer
**Total:** 18 issues, 217 points

### P0 - CRITICAL (4 issues, 63 points)

#### DEVOPS-001: No Containerization Strategy (13 points)
- **Files:** None - missing Dockerfile, docker-compose.yml
- **Description:** Zero container configuration. Manual Python environment setup, no isolation, no reproducibility.
- **Fix:** Create multi-stage Dockerfile, add docker-compose for local dev, implement health checks, add .dockerignore
- **Blocks:** DEVOPS-003

#### DEVOPS-002: No Environment Configuration Management (8 points)
- **Files:** Multiple scripts with scattered `os.getenv()` calls
- **Description:** No `.env.example`, no config validation, no secrets management. API keys likely hardcoded.
- **Fix:** Create centralized `config.py`, add `.env.example`, implement Pydantic validation, expand keyring usage
- **Blocks:** DEVOPS-001

#### DEVOPS-003: No CI/CD Pipeline for Deployment (21 points)
- **Files:** `.github/workflows/` (only test.yml exists)
- **Description:** GitHub Actions runs tests but no build/deploy/release workflows. Manual deployment only.
- **Fix:** Add release.yml (semantic versioning), Docker build/push, deployment workflows (dev/staging/prod), automated changelogs
- **Requires:** DEVOPS-001

#### DEVOPS-004: No Production Monitoring or Observability (21 points)
- **Files:** `lib/logging_config.py` (logging only, no metrics)
- **Description:** Comprehensive logging exists but zero observability stack. No metrics, traces, alerts, dashboards.
- **Fix:** Integrate Prometheus client, add structured logging with correlation IDs, implement health endpoints, create dashboards, configure alerts

---

## Issue Creation Instructions

To create these Linear issues:

### Option 1: Manual Linear UI
1. Copy each issue description from above
2. Create in Linear with appropriate team/labels/priority
3. Assign to recommended agent
4. Add to FDA Tools project
5. Set dependencies based on "Blocks:" and "Requires:" fields

### Option 2: Automated via Script
```python
# See scripts/create_linear_issues.py for automated bulk creation
python3 scripts/create_linear_issues.py --manifest LINEAR_ISSUES_MANIFEST.json
```

### Option 3: CSV Import
1. Export to CSV: `python3 scripts/export_issues_csv.py`
2. Import via Linear's CSV import feature
3. Manually set team assignments and dependencies

---

## Dependency Chains

### Critical Path 1: Package Foundation
```
ARCH-001 (sys.path) → CODE-001 (rate limiters) → CODE-002 (API clients)
                   → ARCH-005 (scripts/lib boundary)
```

### Critical Path 2: Deployment Infrastructure
```
ARCH-002 (config) → DEVOPS-002 (env config) → DEVOPS-001 (Docker) → DEVOPS-003 (CI/CD)
```

### Critical Path 3: Compliance
```
REG-006 (auth) → REG-002 (audit trail) → REG-001 (e-signatures)
               → REG-008 (tamper-evident)
```

### Critical Path 4: Testing
```
QA-001 (E2E infra) → QA-002 (fix failures) → QA-003 (untested utilities)
                                           → QA-005 (integration tests)
```

---

## Contact & Support

**Review Team:** 7 autonomous AI agents
**Orchestrator:** Meta-agent coordination via ORCHESTRATOR_ARCHITECTURE.md
**Documentation:** All detailed findings in agent output sections
**Questions:** Reference agent names for specific domain expertise

---

**Next Steps:**
1. ✅ Review this document with your team
2. ⏸️  Decide on Linear issue creation approach (manual, script, or CSV)
3. ⏸️  Execute Sprint 1 plan (Foundation & Security, 89 points)
4. ⏸️  Set up project tracking dashboard in Linear
5. ⏸️  Schedule sprint planning with assigned agents
