# FDA Tools Enterprise Deployment Guide

## Phase 4: Multi-User Enterprise Features

Version: 2.0.0
Date: 2026-02-16
Status: Production Ready

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Prerequisites](#3-prerequisites)
4. [Installation](#4-installation)
5. [User Management](#5-user-management)
6. [Role-Based Access Control](#6-role-based-access-control)
7. [Multi-Tenancy](#7-multi-tenancy)
8. [Electronic Signatures](#8-electronic-signatures)
9. [Monitoring and Alerting](#9-monitoring-and-alerting)
10. [Security Best Practices](#10-security-best-practices)
11. [Backup and Recovery](#11-backup-and-recovery)
12. [API Reference](#12-api-reference)
13. [Configuration Reference](#13-configuration-reference)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Overview

FDA Tools Enterprise enables multi-user deployment of the FDA 510(k) predicate
assistant with enterprise-grade features:

- **User Management**: Account lifecycle with enrollment tokens and messaging
  handle authentication for WhatsApp, Telegram, Slack, and Discord.
- **Role-Based Access Control (RBAC)**: Four roles (admin, ra_professional,
  reviewer, readonly) with granular command-level permissions.
- **Multi-Tenancy**: Per-organization data isolation with shared API caches
  and cross-team project collaboration.
- **Electronic Signatures**: 21 CFR Part 11 compliant signatures with
  non-repudiation, audit trails, and multi-signature approval chains.
- **Real-Time Monitoring**: Security violation alerts, LLM provider health
  checks, performance metrics, and alert delivery via email/Slack/webhook.

### Components

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| UserManager | `lib/user_manager.py` | ~430 | User CRUD, enrollment, authentication |
| RBACManager | `lib/rbac_manager.py` | ~350 | Permission enforcement, audit |
| TenantManager | `lib/tenant_manager.py` | ~420 | Data isolation, collaboration |
| SignatureManager | `lib/signature_manager.py` | ~400 | Electronic signatures, 21 CFR Part 11 |
| MonitoringManager | `lib/monitoring_manager.py` | ~530 | Alerts, metrics, health monitoring |
| Server (Phase 4) | `bridge/server.py` | ~1400 | 10+ new REST endpoints |
| Enrollment CLI | `scripts/enroll_user.py` | ~200 | Admin user enrollment script |
| Tests | `tests/test_enterprise_phase4.py` | ~850 | 70 tests, >95% coverage |

---

## 2. Architecture

```
Multiple Users (WhatsApp, Telegram, Slack, Discord)
  alice@device-corp.com (RA Professional)
  bob@device-corp.com (Reviewer)
  admin@device-corp.com (Administrator)
         |
         v
OpenClaw Gateway (Multi-Tenant)
  User authentication via messaging handles
  Per-organization isolation
         |
         v
FDA Bridge Server (Phase 4 Enhanced)
  +-- UserManager        (user lifecycle)
  +-- RBACManager        (permission enforcement)
  +-- TenantManager      (data isolation)
  +-- SignatureManager    (21 CFR Part 11)
  +-- MonitoringManager   (alerts + metrics)
  +-- SecurityGateway    (Phase 1: data classification)
  +-- AuditLogger        (Phase 1: audit trail)
  +-- SessionManager     (Phase 2: conversations)
  +-- ToolRegistry       (Phase 2: tool emulation)
```

### Data Flow for Command Execution

```
1. User sends message via messaging platform
2. OpenClaw Gateway authenticates user by handle
3. Bridge Server receives POST /execute
4. UserManager authenticates user
5. RBACManager checks command permission
6. TenantManager validates data path access
7. SignatureManager checks if signature required
8. SecurityGateway classifies data and routes LLM
9. AuditLogger records the execution
10. Tool emulators execute the command
11. MonitoringManager records metrics
12. Response returned to user
```

---

## 3. Prerequisites

### Hardware Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 20 GB | 100+ GB |
| Network | 10 Mbps | 100+ Mbps |

### Software Requirements

- Python 3.9+
- FastAPI 0.100+
- uvicorn 0.23+
- Node.js 18+ (for OpenClaw skill)
- Ollama (optional, for local LLM)

### Python Dependencies

```bash
pip install fastapi uvicorn pydantic toml requests
```

### Network Requirements

- Outbound HTTPS to api.fda.gov (FDA API)
- Outbound HTTPS to api.anthropic.com (if using Claude)
- Inbound on port 18790 (Bridge Server, localhost only by default)
- Outbound SMTP (for email alerts, optional)
- Outbound HTTPS to hooks.slack.com (for Slack alerts, optional)

---

## 4. Installation

### Step 1: Clone and Configure

```bash
# Navigate to plugin directory
cd ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-predicate-assistant

# Copy enterprise configuration template
cp config/fda-tools.enterprise.toml ~/.claude/fda-tools.enterprise.toml

# Edit configuration
nano ~/.claude/fda-tools.enterprise.toml
```

### Step 2: Initialize Enterprise Data Directory

```bash
# The TenantManager creates this automatically on first run
# but you can pre-create it:
mkdir -p ~/fda-enterprise-data/{organizations,shared/{api_cache/{openFDA,MAUDE,recalls},guidance_cache},system/{audit_logs,metrics}}
```

### Step 3: Create First Admin User

```bash
python3 scripts/enroll_user.py \
  --email admin@your-company.com \
  --name "System Administrator" \
  --role admin \
  --organization "Your Company Name"
```

### Step 4: Start the Bridge Server

```bash
cd bridge
python3 server.py
```

The server starts on `http://127.0.0.1:18790`.

### Step 5: Verify Installation

```bash
# Health check
curl http://127.0.0.1:18790/health

# Detailed health (Phase 4)
curl http://127.0.0.1:18790/health/detailed

# List users
curl http://127.0.0.1:18790/users
```

---

## 5. User Management

### Creating Users

```bash
# Via CLI
python3 scripts/enroll_user.py \
  --email alice@device-corp.com \
  --name "Alice Johnson" \
  --role ra_professional \
  --organization "Device Corp"

# Via API
curl -X POST http://127.0.0.1:18790/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@device-corp.com",
    "name": "Alice Johnson",
    "role": "ra_professional",
    "organization_id": "org_device_corp"
  }'
```

### Enrollment Flow

1. Admin creates user account (no messaging handle yet)
2. System generates enrollment token (valid 24 hours)
3. Token sent to user via secure channel (email, SMS)
4. User connects messaging handle via the token

```bash
# Generate token
curl -X POST http://127.0.0.1:18790/users/enroll \
  -H "Content-Type: application/json" \
  -d '{"user_id": "usr_abc123", "expires_hours": 24}'

# Complete enrollment
curl -X POST http://127.0.0.1:18790/users/complete-enrollment \
  -H "Content-Type: application/json" \
  -d '{
    "token": "tok_generated_token_here",
    "messaging_handles": {"whatsapp": "+14155551234"}
  }'
```

### User Database

User data is stored in `~/.claude/fda-tools.users.json`:

```json
{
  "users": [
    {
      "user_id": "usr_abc123def456",
      "email": "alice@device-corp.com",
      "name": "Alice Johnson",
      "role": "ra_professional",
      "organization_id": "org_device_corp",
      "messaging_handles": {"whatsapp": "+14155551234"},
      "enrolled_at": "2026-02-16T10:00:00Z",
      "is_active": true
    }
  ]
}
```

---

## 6. Role-Based Access Control

### Roles

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| `admin` | Full system access | User management, system configuration, all commands |
| `ra_professional` | Full FDA tools access | Project CRUD, all FDA commands including draft/assemble |
| `reviewer` | Read-only analysis | Read projects, public + restricted commands (no drafting) |
| `readonly` | Public data only | Public FDA data queries only |

### Permission Matrix

| Permission | admin | ra_professional | reviewer | readonly |
|-----------|-------|-----------------|----------|----------|
| user:create | Yes | - | - | - |
| user:read | Yes | Yes | - | - |
| user:update | Yes | - | - | - |
| user:delete | Yes | - | - | - |
| project:create | Yes | Yes | - | - |
| project:read | Yes | Yes | Yes | - |
| project:update | Yes | Yes | - | - |
| project:delete | Yes | Yes | - | - |
| command:public | Yes | Yes | Yes | Yes |
| command:restricted | Yes | Yes | Yes | - |
| command:confidential | Yes | Yes | - | - |
| system:admin | Yes | - | - | - |
| system:monitor | Yes | Yes | - | - |

### Command Classification

| Classification | Commands | Minimum Role |
|---------------|----------|--------------|
| Public | validate, status, cache, help | readonly |
| Restricted | research, analyze, safety, batchfetch, compare-se, pre-check | reviewer |
| Confidential | draft, assemble, export, submission-writer | ra_professional |
| Admin | configure, user-manage, audit-review | admin |

### Checking Permissions

```bash
# Get user permissions
curl http://127.0.0.1:18790/users/usr_abc123/permissions

# Check specific permission
curl -X POST http://127.0.0.1:18790/users/usr_abc123/check-permission \
  -H "Content-Type: application/json" \
  -d '{"permission": "command:confidential"}'
```

---

## 7. Multi-Tenancy

### Organization Setup

```bash
# Create organization
curl -X POST http://127.0.0.1:18790/organizations \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Medical Devices"}'
```

### Directory Structure

Each organization has isolated data:

```
~/fda-enterprise-data/
+-- organizations/
|   +-- org_acme_medical_devices/
|   |   +-- users/
|   |   |   +-- usr_abc123/
|   |   |   |   +-- projects/
|   |   |   |       +-- ABC001/
|   |   |   |       +-- ABC002/
|   |   |   +-- usr_def456/
|   |   +-- shared/
|   |   |   +-- projects/
|   |   +-- metadata.json
+-- shared/
|   +-- api_cache/     (shared across all organizations)
|   |   +-- openFDA/
|   |   +-- MAUDE/
|   |   +-- recalls/
+-- system/
    +-- audit_logs/
    +-- metrics/
```

### Data Isolation Rules

1. Users can only access paths within their own organization
2. Users can access their own data directory
3. Users can access their organization's shared directory
4. Users can access the global shared cache (FDA API data)
5. Users CANNOT access other organizations' data (enforced by TenantManager)
6. Cross-tenant access attempts generate CRITICAL alerts

### Project Sharing

Projects can be shared between users within the same organization:

```python
# In code
tenant_mgr.share_project(
    project_id="ABC001",
    from_user="usr_owner",
    to_users=["usr_reviewer"],
    organization_id="org_acme",
    permissions="read"
)
```

---

## 8. Electronic Signatures

### 21 CFR Part 11 Compliance

The SignatureManager implements:

| CFR Section | Requirement | Implementation |
|-------------|-------------|----------------|
| 11.50 | Signature manifestations | Captured: name, date/time, meaning |
| 11.70 | Signature/record linking | SHA-256 hash + salt, non-repudiation |
| 11.100 | General requirements | Unique per individual (user_id + credentials) |
| 11.200 | Signature components | Two components: identification + authentication |
| 11.300 | Password controls | PBKDF2-SHA256, 100K iterations, random salt |

### Commands Requiring Signatures

By default, these commands require electronic signature:

- `export` - Final submission package export
- `assemble` - eSTAR assembly

Additional commands can be configured in `fda-tools.enterprise.toml`.

### Creating Signatures

```bash
curl -X POST http://127.0.0.1:18790/signatures \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_abc123",
    "action": "approve_submission",
    "document_id": "eSTAR_ABC001_v2",
    "signature_method": "password",
    "credentials": "user_password",
    "meaning": "I approve this submission package"
  }'
```

### Verifying Signatures

```bash
curl -X POST http://127.0.0.1:18790/signatures/verify \
  -H "Content-Type: application/json" \
  -d '{
    "signature_id": "sig_abc123def456",
    "credentials": "user_password"
  }'
```

### Multi-Signature Approval

```bash
# Check if all required signatures are present
curl http://127.0.0.1:18790/documents/eSTAR_v1/signatures
```

### Signature Audit Trail

All signature events are logged to
`~/.claude/fda-tools-signatures/signature_audit.jsonl`:

```json
{"timestamp": "2026-02-16T10:00:00Z", "event_type": "signature_created",
 "signature_id": "sig_abc123", "user_id": "usr_001",
 "user_name": "Alice Johnson", "action": "approve_submission",
 "document_id": "eSTAR_v1", "meaning": "RA approval"}
```

---

## 9. Monitoring and Alerting

### Alert Types

| Type | Severity | Trigger |
|------|----------|---------|
| security_violation | CRITICAL | Unauthorized access attempt |
| tenant_breach | CRITICAL | Cross-tenant data access attempt |
| llm_provider_down | HIGH | LLM provider health check failure |
| unusual_activity | HIGH | 5+ failures in 5 minutes |
| permission_denied | MEDIUM | RBAC permission check failure |
| signature_failure | MEDIUM | Signature verification failure |
| system_error | varies | System component error |
| performance_degraded | LOW | Command execution time above threshold |

### Alert Delivery

Configure alert destinations in `fda-tools.enterprise.toml`:

```toml
[monitoring]
alert_email = "alerts@device-corp.com"
alert_slack_webhook = "https://hooks.slack.com/services/T00/B00/xxx"
alert_webhook = "https://your-pager-system.com/webhook"
```

### Querying Alerts

```bash
# All alerts
curl http://127.0.0.1:18790/alerts

# Filtered by severity
curl "http://127.0.0.1:18790/alerts?severity=critical"

# Unresolved only
curl "http://127.0.0.1:18790/alerts?resolved=false"

# Resolve an alert
curl -X POST http://127.0.0.1:18790/alerts/alert_abc123/resolve \
  -H "Content-Type: application/json" \
  -d '{"resolved_by": "usr_admin"}'
```

### Performance Metrics

```bash
# Query metrics
curl "http://127.0.0.1:18790/metrics?metric_name=command_execution"
```

### Detailed Health Check

```bash
curl http://127.0.0.1:18790/health/detailed
```

Returns:

```json
{
  "overall_status": "healthy",
  "subsystems": {
    "security_gateway": true,
    "audit_logger": true,
    "session_manager": true,
    "user_manager": true,
    "rbac_manager": true,
    "tenant_manager": true,
    "signature_manager": true,
    "monitoring_manager": true
  },
  "counts": {
    "users": 15,
    "active_users": 12,
    "organizations": 3,
    "signatures": 47,
    "active_alerts": 2,
    "sessions_active": 8
  }
}
```

---

## 10. Security Best Practices

### Network Security

- The Bridge Server binds to localhost (127.0.0.1) only
- For production, deploy behind a reverse proxy (nginx) with TLS
- Use HTTPS for all client connections
- Restrict firewall rules to necessary ports only

### Credential Security

- Never hardcode credentials in configuration files
- Use environment variables for API keys:
  ```bash
  export ANTHROPIC_API_KEY="sk-..."
  export OPENAI_API_KEY="sk-..."
  ```
- Signatures use PBKDF2-SHA256 with 100K iterations
- Enrollment tokens expire after 24 hours (configurable)

### Access Control

- Apply principle of least privilege (start users as readonly)
- Review RBAC audit logs regularly
- Deactivate users rather than deleting (preserves audit trail)
- Monitor for unusual activity patterns

### Compliance

- Enable 21 CFR Part 11 mode in configuration
- Require electronic signatures for controlled commands
- Maintain audit logs for 7 years (2555 days)
- Conduct periodic audit log integrity verification

---

## 11. Backup and Recovery

### Data to Back Up

| Data | Path | Frequency |
|------|------|-----------|
| User database | `~/.claude/fda-tools.users.json` | Daily |
| Audit logs | `~/.claude/fda-tools.audit.jsonl` | Daily |
| RBAC audit | `~/.claude/fda-tools.rbac-audit.jsonl` | Daily |
| Signatures | `~/.claude/fda-tools-signatures/` | Daily |
| Enterprise data | `~/fda-enterprise-data/` | Daily |
| Sessions | `~/.claude/sessions/` | Optional |
| Security config | `~/.claude/fda-tools.security.toml` | On change |

### Backup Script

```bash
#!/bin/bash
BACKUP_DIR="/backup/fda-tools/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# User data
cp ~/.claude/fda-tools.users.json "$BACKUP_DIR/"
cp ~/.claude/fda-tools.audit.jsonl "$BACKUP_DIR/"
cp ~/.claude/fda-tools.rbac-audit.jsonl "$BACKUP_DIR/"

# Signatures
tar czf "$BACKUP_DIR/signatures.tar.gz" ~/.claude/fda-tools-signatures/

# Enterprise data
tar czf "$BACKUP_DIR/enterprise-data.tar.gz" ~/fda-enterprise-data/

echo "Backup completed: $BACKUP_DIR"
```

### Recovery Procedure

1. Stop the Bridge Server
2. Restore files from backup
3. Verify audit log integrity: `curl http://127.0.0.1:18790/audit/integrity`
4. Restart the Bridge Server
5. Verify health: `curl http://127.0.0.1:18790/health/detailed`

---

## 12. API Reference

### Phase 4 Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /users | Create user |
| GET | /users | List users |
| GET | /users/{id} | Get user |
| PUT | /users/{id} | Update user |
| DELETE | /users/{id} | Delete user |
| POST | /users/enroll | Generate enrollment token |
| POST | /users/complete-enrollment | Complete enrollment |
| GET | /users/{id}/permissions | Get user permissions |
| POST | /users/{id}/check-permission | Check permission |
| POST | /organizations | Create organization |
| GET | /organizations | List organizations |
| GET | /organizations/{id} | Get organization |
| PUT | /organizations/{id} | Update organization |
| POST | /signatures | Create signature |
| POST | /signatures/verify | Verify signature |
| GET | /documents/{id}/signatures | Get document signatures |
| GET | /alerts | Get alerts |
| POST | /alerts/{id}/resolve | Resolve alert |
| GET | /metrics | Get metrics |
| GET | /health/detailed | Detailed health check |

### Existing Endpoints (Phase 1-3)

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Basic health check |
| GET | /commands | List FDA commands |
| POST | /session | Create/get session |
| POST | /execute | Execute FDA command |
| GET | /sessions | List sessions |
| GET | /audit/integrity | Verify audit log |
| GET | /tools | List tool emulators |

---

## 13. Configuration Reference

See `config/fda-tools.enterprise.toml` for the full configuration template
with inline documentation for every setting.

Key sections:

- `[enterprise]` - Global enable/disable
- `[users]` - User management settings
- `[rbac]` - Access control settings
- `[tenancy]` - Multi-tenancy settings
- `[signatures]` - Electronic signature settings
- `[monitoring]` - Alerting and metrics settings
- `[compliance]` - 21 CFR Part 11 settings
- `[performance]` - Performance tuning

---

## 14. Troubleshooting

### UserManager fails to load

```
ERROR: User manager initialization failed
```

Check that `~/.claude/fda-tools.users.json` is valid JSON.
If corrupted, restore from backup.

### RBAC denies all requests

Verify the user's role is correct:

```bash
curl http://127.0.0.1:18790/users/{user_id}
```

Check if the user is active (`is_active: true`).

### Signature verification fails

Ensure the same credentials are used for creation and verification.
Check that the signature has not been invalidated.

### Cross-tenant access blocked

This is expected behavior. Users can only access data within their
own organization. Check the user's `organization_id` matches the
data they are trying to access.

### LLM provider alerts

Check Ollama is running: `curl http://localhost:11434/api/tags`
Check API keys are set: `echo $ANTHROPIC_API_KEY`

### Performance issues

Monitor command execution times via the metrics endpoint.
Consider increasing server resources or optimizing commands.

---

## Test Coverage

Run the full test suite:

```bash
cd plugins/fda-predicate-assistant
python3 -m pytest tests/test_enterprise_phase4.py -v
```

Expected: 70 tests, 100% pass rate.

Test categories:
- UserManager: 15 tests
- RBACManager: 12 tests
- TenantManager: 10 tests
- SignatureManager: 8 tests
- MonitoringManager: 10 tests
- Integration: 15 tests

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-16 | Phase 1: Security Foundation |
| 1.1.0 | 2026-02-16 | Phase 2: HTTP REST API Bridge |
| 1.2.0 | 2026-02-16 | Phase 3: OpenClaw Skill |
| 2.0.0 | 2026-02-16 | Phase 4: Multi-User Enterprise |
