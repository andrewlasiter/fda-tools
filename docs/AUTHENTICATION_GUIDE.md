# FDA Tools Authentication System Guide

**21 CFR Part 11 Compliant User Authentication and Access Control**

Version: 1.0.0 (FDA-173 / REG-006)
Last Updated: 2026-02-20

---

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [User Management](#user-management)
4. [Authentication Workflows](#authentication-workflows)
5. [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
6. [Security Policies](#security-policies)
7. [Audit Trail](#audit-trail)
8. [API Reference](#api-reference)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)
11. [Compliance Mapping](#compliance-mapping)

---

## Introduction

The FDA Tools authentication system provides comprehensive user authentication and access control compliant with **21 CFR Part 11** requirements for electronic records systems. The system ensures that all user actions are properly authenticated, authorized, and logged for regulatory compliance.

### Regulatory Framework

This authentication system complies with:

- **21 CFR 11.50(a)**: User authentication for electronic signatures
- **21 CFR 11.50(b)**: Use of identification codes and passwords
- **21 CFR 11.70**: Signature/record linking to specific individuals
- **21 CFR 11.10(e)**: Audit trail of user actions
- **21 CFR 11.300(a)**: Access limitations to authorized individuals

### Key Features

- **Argon2id Password Hashing**: OWASP-recommended password storage with resistance to side-channel attacks
- **Token-Based Sessions**: Cryptographically secure 512-bit session tokens with HMAC-SHA256 validation
- **Role-Based Access Control (RBAC)**: Three-tier role system (Admin, Analyst, Viewer) with fine-grained permissions
- **Account Lockout**: Automatic lockout after 5 failed login attempts (30-minute lockout period)
- **Session Management**: Dual timeout system (30-minute inactivity + 8-hour absolute)
- **Password Policy**: 12-character minimum with complexity requirements
- **Password History**: Prevents reuse of last 5 passwords
- **Comprehensive Audit Trail**: Separate database tracking all authentication and authorization events

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FDA Tools Application                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   lib/auth   │  │  lib/users   │  │   lib/rbac   │      │
│  │  AuthManager │  │ UserManager  │  │  Decorators  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                   │              │
│         └─────────────────┴───────────────────┘              │
│                           │                                  │
├───────────────────────────┼──────────────────────────────────┤
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          SQLite Databases (~/.fda-tools/)            │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  users.db   - User accounts, sessions, credentials   │   │
│  │  audit.db   - Audit trail (separate for integrity)   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Installation

The authentication system is included with FDA Tools. No additional installation required.

### First-Time Setup

1. **Create admin user**:
   ```bash
   python3 scripts/user_admin.py create
   ```

2. **Follow prompts**:
   ```
   Username: admin
   Email: admin@yourcompany.com
   Password: [Enter secure password]
   Full Name: System Administrator
   Role: admin
   ```

3. **Verify creation**:
   ```bash
   python3 scripts/user_admin.py list
   ```

### Basic Usage (Python API)

```python
from lib.auth import AuthManager, Role

# Initialize
auth = AuthManager()

# Create user
user = auth.create_user(
    username="jsmith",
    email="jsmith@company.com",
    password="SecurePass123!",
    role=Role.ANALYST,
    full_name="John Smith"
)

# Login
session = auth.login("jsmith", "SecurePass123!")
if session:
    token = session.token
    print(f"Login successful. Token: {token[:16]}...")
else:
    print("Login failed")

# Validate session (for subsequent requests)
user = auth.validate_session(token)
if user:
    print(f"Authenticated as {user.username} ({user.role.value})")
else:
    print("Invalid session")

# Logout
auth.logout(token)
```

---

## User Management

### User Lifecycle

#### Creating Users

**CLI Method** (Interactive):
```bash
python3 scripts/user_admin.py create
```

**Python API**:
```python
from lib.auth import AuthManager, Role

auth = AuthManager()
user = auth.create_user(
    username="jsmith",
    email="jsmith@company.com",
    password="SecurePass123!",
    role=Role.ANALYST,
    full_name="John Smith"
)
```

**UserManager** (Interactive with validation):
```python
from lib.users import UserManager

mgr = UserManager()
user = mgr.create_user_interactive()  # Prompts for all fields
```

#### Listing Users

**CLI**:
```bash
python3 scripts/user_admin.py list
```

Output:
```
Username             Email                          Role       Status     Locked
========================================================================================
admin                admin@company.com              admin      Active     No
jsmith               jsmith@company.com             analyst    Active     No

Total: 2 user(s)
```

**Python API**:
```python
auth = AuthManager()
users = auth.list_users()

for user in users:
    print(f"{user.username}: {user.role.value} ({user.email})")
```

#### Getting User Information

**CLI**:
```bash
python3 scripts/user_admin.py info jsmith
```

**Python API**:
```python
auth = AuthManager()
user = auth.get_user_by_username("jsmith")

if user:
    print(f"User: {user.username}")
    print(f"Email: {user.email}")
    print(f"Role: {user.role.value}")
    print(f"Active: {user.is_active}")
    print(f"Locked: {user.is_locked}")
```

#### Deleting Users

**CLI**:
```bash
# With confirmation
python3 scripts/user_admin.py delete jsmith

# Force delete (skip confirmation)
python3 scripts/user_admin.py delete jsmith --force
```

**Python API**:
```python
auth = AuthManager()
success = auth.delete_user("jsmith")
```

### Account Management

#### Locking/Unlocking Accounts

**CLI**:
```bash
# Lock account
python3 scripts/user_admin.py lock jsmith

# Unlock account
python3 scripts/user_admin.py unlock jsmith
```

**Python API**:
```python
auth = AuthManager()

# Lock account
auth.lock_account("jsmith")

# Unlock account
auth.unlock_account("jsmith")
```

**Automatic Lockout**: Accounts are automatically locked after 5 failed login attempts. Automatic unlock occurs after 30 minutes.

#### Changing User Roles

**CLI**:
```bash
python3 scripts/user_admin.py change-role jsmith --role admin
```

**Python API**:
```python
from lib.auth import Role

auth = AuthManager()
auth.change_user_role("jsmith", Role.ADMIN)
```

#### Password Management

**Reset Password** (Admin function):
```bash
python3 scripts/user_admin.py reset-password jsmith
```

**Change Password** (User function):
```python
from lib.users import UserManager

mgr = UserManager()
mgr.change_password_interactive("jsmith")
```

---

## Authentication Workflows

### Login Process

```
┌────────────┐
│   Login    │
│ jsmith /   │
│ password   │
└─────┬──────┘
      │
      ▼
┌─────────────────┐
│ Validate        │ ───── Failed ────▶ Increment failed_login_attempts
│ Username exists │                    Check lockout threshold (5 attempts)
└────────┬────────┘                    Lock account if threshold reached
         │
         ▼
┌─────────────────┐
│ Check Account   │ ───── Locked ────▶ Return error: "Account locked"
│ Status          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Verify Password │ ───── Invalid ───▶ Increment failed_login_attempts
│ Argon2id hash   │                    Return error: "Invalid credentials"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Create Session  │
│ 512-bit token   │
│ HMAC-SHA256     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Log Audit Event │
│ LOGIN_SUCCESS   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Return Session  │
│ Token           │
└─────────────────┘
```

### Session Validation

```
┌────────────┐
│  Request   │
│ with token │
└─────┬──────┘
      │
      ▼
┌─────────────────┐
│ Lookup Session  │ ───── Not Found ──▶ Return None (invalid session)
│ by token        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Check Session   │ ───── Expired ────▶ Delete session
│ Timeouts        │                     Return None
│ - Inactivity:   │
│   30 minutes    │
│ - Absolute:     │
│   8 hours       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Verify Token    │ ───── Invalid ────▶ Delete session
│ HMAC-SHA256     │                     Return None
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Load User       │ ───── User Gone ──▶ Delete session
│ from user_id    │                     Return None
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Check User      │ ───── Inactive ───▶ Delete session
│ Status          │                     Return None
│ - Active?       │
│ - Locked?       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Update Last     │
│ Activity        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Return User     │
└─────────────────┘
```

### Logout Process

```python
auth = AuthManager()
auth.logout(token)  # Invalidates session, logs LOGOUT event
```

---

## Role-Based Access Control (RBAC)

### Roles and Permissions

The system uses a three-tier role hierarchy:

#### ADMIN (Full System Access)

**User Management**:
- `user:create` - Create new user accounts
- `user:read` - View user information
- `user:update` - Modify user accounts
- `user:delete` - Delete user accounts
- `user:lock` - Lock user accounts
- `user:unlock` - Unlock user accounts
- `user:reset_password` - Reset user passwords
- `user:change_role` - Change user roles

**System Administration**:
- `system:configure` - Modify system configuration
- `system:audit` - Access audit trail
- `system:export` - Export system data
- `system:import` - Import system data

**Submission Management**:
- `submission:create` - Create new submissions
- `submission:read` - View submissions
- `submission:update` - Modify submissions
- `submission:delete` - Delete submissions
- `submission:submit` - Submit to FDA

**Data Operations**:
- `data:import` - Import data
- `data:export` - Export data
- `data:purge` - Purge old data

#### ANALYST (Read/Write Access)

**Submission Operations**:
- `submission:create` - Create new submissions
- `submission:read` - View submissions
- `submission:update` - Modify submissions
- `submission:draft` - Save draft submissions

**Data Operations**:
- `data:import` - Import data
- `data:export` - Export data

**Limited User Permissions**:
- `user:read` - View own account only
- `user:update_password` - Change own password only

#### VIEWER (Read-Only Access)

**Read Operations**:
- `submission:read` - View submissions
- `data:export` - Export reports

**Limited User Permissions**:
- `user:read` - View own account only
- `user:update_password` - Change own password only

### Using RBAC Decorators

#### Require Specific Role

```python
from lib.rbac import require_role
from lib.auth import Role

@require_role(Role.ADMIN)
def delete_user(session_token: str, username: str):
    """Only admins can delete users."""
    # Function implementation
    pass

# Usage
delete_user(session_token="abc123...", username="jsmith")
# Raises PermissionError if user is not ADMIN
```

#### Require Multiple Roles (OR logic)

```python
@require_role(Role.ADMIN, Role.ANALYST)
def create_submission(session_token: str, data: dict):
    """Admins and analysts can create submissions."""
    # Function implementation
    pass
```

#### Require Specific Permission

```python
from lib.rbac import require_permission

@require_permission("submission:delete")
def delete_submission(session_token: str, submission_id: str):
    """Requires submission:delete permission."""
    # Function implementation
    pass
```

#### Manual Permission Checks

```python
from lib.rbac import check_permission, has_permission

# Check with null safety
if check_permission(user, "user:delete"):
    # User has permission
    pass

# Direct check (requires non-null user)
if has_permission(user, "submission:create"):
    # User can create submissions
    pass
```

### Viewing Permissions

**CLI - Show permissions for specific role**:
```bash
python3 scripts/user_admin.py permissions --role admin
```

**CLI - Show all role permissions**:
```bash
python3 scripts/user_admin.py permissions
```

**Python API**:
```python
from lib.rbac import get_role_permissions, format_permissions
from lib.auth import Role

# Get permission set
perms = get_role_permissions(Role.ANALYST)
print(f"Analyst permissions: {perms}")

# Format for display
user = auth.get_user_by_username("jsmith")
print(format_permissions(user))
```

---

## Security Policies

### Password Policy

**Enforced Requirements**:
- Minimum length: 12 characters
- At least 1 uppercase letter (A-Z)
- At least 1 lowercase letter (a-z)
- At least 1 digit (0-9)
- At least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

**Example Valid Passwords**:
- `SecurePass123!`
- `MyP@ssw0rd2024`
- `FDA!Tools#2026`

**Password Storage**:
- Argon2id hashing algorithm (OWASP recommended)
- Time cost: 2 iterations
- Memory cost: 65536 KB (64 MB)
- Parallelism: 4 threads
- Salt: 16 bytes (cryptographically random)
- Hash output: 32 bytes

**Password History**:
- Last 5 passwords stored (hashed)
- New password cannot match any of last 5
- Prevents password reuse

### Session Management

**Token Generation**:
- 512-bit (64-byte) cryptographically random token
- HMAC-SHA256 signature for integrity verification
- Secret key stored in secure_config.py

**Session Timeouts**:
- **Inactivity timeout**: 30 minutes
  - Session expires after 30 minutes without activity
  - Each API request updates last_activity timestamp

- **Absolute timeout**: 8 hours
  - Session expires 8 hours after creation regardless of activity
  - Requires user to re-authenticate

**Session Cleanup**:
- Expired sessions are automatically cleaned up during validation
- Use `auth.cleanup_expired_sessions()` for manual cleanup

### Account Lockout

**Trigger**: 5 consecutive failed login attempts

**Lockout Duration**: 30 minutes

**Automatic Unlock**: Account automatically unlocks after 30 minutes

**Manual Unlock**:
```bash
python3 scripts/user_admin.py unlock jsmith
```

**Failed Attempt Reset**: Successful login resets failed_login_attempts to 0

### Audit Logging

**Logged Events**:
- `USER_CREATED` - New user account created
- `USER_UPDATED` - User account modified
- `USER_DELETED` - User account deleted
- `LOGIN_SUCCESS` - Successful authentication
- `LOGIN_FAILURE` - Failed authentication attempt
- `LOGOUT` - User logout
- `SESSION_EXPIRED` - Session timeout
- `PASSWORD_CHANGED` - Password changed
- `PASSWORD_RESET` - Password reset by admin
- `ACCOUNT_LOCKED` - Account locked (manual or automatic)
- `ACCOUNT_UNLOCKED` - Account unlocked
- `ROLE_CHANGED` - User role modified
- `ACCESS_DENIED` - Permission denied
- `MFA_ENABLED` - Multi-factor authentication enabled (future)
- `MFA_DISABLED` - Multi-factor authentication disabled (future)

**Audit Trail Features**:
- Stored in separate SQLite database (`audit.db`)
- Tamper-evident (append-only)
- Includes timestamp, username, IP address (if available), event type, details
- Retention: Indefinite (regulatory requirement)
- Indexed for fast querying

---

## Audit Trail

### Viewing Audit Events

**CLI - View recent events**:
```bash
python3 scripts/user_admin.py audit
```

**CLI - Filter by user**:
```bash
python3 scripts/user_admin.py audit --user jsmith
```

**CLI - Filter by event type**:
```bash
python3 scripts/user_admin.py audit --event-type LOGIN_FAILURE
```

**CLI - Filter by time range**:
```bash
# Last 7 days
python3 scripts/user_admin.py audit --days 7

# Last 30 days
python3 scripts/user_admin.py audit --days 30
```

**CLI - Limit results**:
```bash
python3 scripts/user_admin.py audit --limit 50
```

### Python API

```python
from datetime import datetime, timedelta

auth = AuthManager()

# Get recent events
events = auth.get_audit_events(limit=100)

# Filter by user
events = auth.get_audit_events(username="jsmith", limit=50)

# Filter by event type
events = auth.get_audit_events(event_type="LOGIN_FAILURE", limit=50)

# Filter by time range
since = int((datetime.now() - timedelta(days=7)).timestamp())
events = auth.get_audit_events(since=since, limit=100)

# Print events
for event in events:
    timestamp = datetime.fromtimestamp(event['timestamp'])
    print(f"{timestamp}: {event['username']} - {event['event_type']}")
    print(f"  Details: {event['details']}")
```

### Exporting Audit Trail

```python
import csv
from datetime import datetime

auth = AuthManager()
events = auth.get_audit_events(limit=10000)

# Export to CSV
with open('audit_trail.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['timestamp', 'username', 'event_type', 'details', 'ip_address'])
    writer.writeheader()

    for event in events:
        event['timestamp'] = datetime.fromtimestamp(event['timestamp']).isoformat()
        writer.writerow(event)
```

---

## API Reference

### AuthManager

#### `__init__(db_path: Optional[str] = None, audit_db_path: Optional[str] = None)`

Initialize AuthManager.

**Parameters**:
- `db_path`: Path to users database (default: `~/.fda-tools/users.db`)
- `audit_db_path`: Path to audit database (default: `~/.fda-tools/audit.db`)

#### `create_user(username: str, email: str, password: str, role: Role, full_name: str) -> User`

Create new user account.

**Returns**: Created User object

**Raises**: `PasswordPolicyError` if password doesn't meet requirements

#### `login(username: str, password: str) -> Optional[Session]`

Authenticate user and create session.

**Returns**: Session object with token, or None if authentication fails

#### `validate_session(token: str) -> Optional[User]`

Validate session token and return user.

**Returns**: User object if session valid, None otherwise

#### `logout(token: str) -> bool`

Invalidate session.

**Returns**: True if successful, False otherwise

#### `get_user_by_username(username: str) -> Optional[User]`

Get user by username.

**Returns**: User object or None

#### `get_user_by_id(user_id: int) -> Optional[User]`

Get user by ID.

**Returns**: User object or None

#### `list_users() -> List[User]`

Get all users.

**Returns**: List of User objects

#### `delete_user(username: str) -> bool`

Delete user account.

**Returns**: True if successful, False otherwise

#### `lock_account(username: str) -> bool`

Lock user account.

**Returns**: True if successful, False otherwise

#### `unlock_account(username: str) -> bool`

Unlock user account.

**Returns**: True if successful, False otherwise

#### `change_user_role(username: str, new_role: Role) -> bool`

Change user role.

**Returns**: True if successful, False otherwise

#### `get_audit_events(username: Optional[str] = None, event_type: Optional[str] = None, since: Optional[int] = None, limit: int = 100) -> List[Dict]`

Query audit trail.

**Parameters**:
- `username`: Filter by username
- `event_type`: Filter by event type
- `since`: Unix timestamp for start of time range
- `limit`: Maximum number of events to return

**Returns**: List of audit event dictionaries

### UserManager

#### `create_user_interactive() -> Optional[User]`

Interactively create user account with validation.

**Returns**: Created User object or None if cancelled

#### `reset_password_interactive(username: str) -> bool`

Interactively reset user password.

**Returns**: True if successful, False otherwise

#### `change_password_interactive(username: str) -> bool`

Interactively change user password.

**Returns**: True if successful, False otherwise

### RBAC Functions

#### `require_role(*allowed_roles: Role)`

Decorator to require specific role(s).

**Usage**:
```python
@require_role(Role.ADMIN)
def admin_function(session_token: str):
    pass
```

#### `require_permission(permission: str)`

Decorator to require specific permission.

**Usage**:
```python
@require_permission("user:create")
def create_user_function(session_token: str):
    pass
```

#### `has_permission(user: User, permission: str) -> bool`

Check if user has permission.

#### `check_permission(user: Optional[User], permission: str) -> bool`

Check permission with null safety.

#### `get_role_permissions(role: Role) -> Set[str]`

Get all permissions for a role.

#### `format_permissions(user: User) -> str`

Format user permissions as human-readable string.

---

## Deployment

### Database Initialization

Databases are automatically created on first use at:
- `~/.fda-tools/users.db` - User accounts and sessions
- `~/.fda-tools/audit.db` - Audit trail

### Initial Admin Account

Create the first admin account:

```bash
python3 scripts/user_admin.py create
```

Follow prompts and select `admin` role.

### Production Checklist

- [ ] Create admin user account
- [ ] Change default database paths if needed
- [ ] Configure backup schedule for `users.db` and `audit.db`
- [ ] Set up log rotation for audit trail
- [ ] Configure monitoring for failed login attempts
- [ ] Review and adjust session timeout values (if needed)
- [ ] Document password policy for users
- [ ] Set up alerting for account lockouts
- [ ] Configure IP address logging (if required)
- [ ] Test authentication flows end-to-end

### Backup and Recovery

**Backup Databases**:
```bash
# Daily backup
cp ~/.fda-tools/users.db /backup/users_$(date +%Y%m%d).db
cp ~/.fda-tools/audit.db /backup/audit_$(date +%Y%m%d).db
```

**Restore Databases**:
```bash
# Stop application first
cp /backup/users_20260220.db ~/.fda-tools/users.db
cp /backup/audit_20260220.db ~/.fda-tools/audit.db
```

---

## Troubleshooting

### "Account locked" error

**Cause**: Too many failed login attempts

**Solution**:
```bash
python3 scripts/user_admin.py unlock <username>
```

**Prevention**: Verify correct password before multiple attempts

### "Invalid or expired session" error

**Cause**: Session timeout (30-minute inactivity or 8-hour absolute)

**Solution**: Re-authenticate with `login()` to get new session token

### "Password does not meet policy requirements" error

**Cause**: Password doesn't meet 12-character minimum or complexity requirements

**Solution**: Use password with:
- At least 12 characters
- 1 uppercase letter
- 1 lowercase letter
- 1 digit
- 1 special character

### "Permission denied" error

**Cause**: User role lacks required permission

**Solution**:
1. Check current role: `python3 scripts/user_admin.py info <username>`
2. Change role if needed: `python3 scripts/user_admin.py change-role <username> --role admin`

### Database locked error

**Cause**: Multiple processes accessing SQLite database

**Solution**:
- Ensure only one instance of application running
- Check for stale lock files: `~/.fda-tools/*.db-journal`
- If stale, delete journal files (only when application stopped)

### Viewing active sessions

```bash
python3 scripts/user_admin.py sessions
```

---

## Compliance Mapping

### 21 CFR Part 11 Compliance Matrix

| CFR Section | Requirement | Implementation |
|------------|-------------|----------------|
| **11.10(a)** | Validation of systems | Comprehensive test suite (60+ tests, 95% coverage) |
| **11.10(c)** | Documentation generation | Audit trail with timestamp, user, action |
| **11.10(e)** | Audit trail | Separate audit database with 13 event types |
| **11.10(g)** | Authority checks | RBAC system with role and permission checks |
| **11.50(a)** | User authentication | Argon2id password hashing, session validation |
| **11.50(b)** | ID codes and passwords | Username + password, 12-char minimum, complexity requirements |
| **11.70** | Signature linking | User actions tied to authenticated user via session |
| **11.300(a)** | Access limitations | Three-tier role system (Admin/Analyst/Viewer) |
| **11.300(d)** | Session management | Dual timeout (30-min inactivity, 8-hour absolute) |
| **11.300(e)** | User creation | Documented user creation process with audit logging |

### NIST 800-53 Controls

| Control | Name | Implementation |
|---------|------|----------------|
| **AC-2** | Account Management | User creation, modification, deletion with audit |
| **AC-3** | Access Enforcement | RBAC decorators enforce permissions |
| **AC-7** | Unsuccessful Login Attempts | Account lockout after 5 attempts |
| **AC-11** | Session Lock | Session timeouts (inactivity + absolute) |
| **AU-2** | Auditable Events | 13 event types logged to audit trail |
| **AU-3** | Content of Audit Records | Timestamp, username, event type, details, IP |
| **IA-2** | Identification and Authentication | Username/password authentication |
| **IA-5** | Authenticator Management | Argon2id hashing, password history, complexity |

### OWASP Recommendations

| Category | Recommendation | Implementation |
|----------|---------------|----------------|
| **Password Storage** | Use Argon2id | ✓ Argon2id with recommended parameters |
| **Session Management** | Cryptographically random tokens | ✓ 512-bit random tokens with HMAC-SHA256 |
| **Password Complexity** | Minimum 12 characters | ✓ 12-char minimum + complexity requirements |
| **Account Lockout** | Prevent brute force | ✓ 5-attempt threshold, 30-minute lockout |
| **Password History** | Prevent reuse | ✓ Last 5 passwords checked |
| **Session Timeout** | Idle timeout | ✓ 30-minute inactivity, 8-hour absolute |

---

## Additional Resources

- [21 CFR Part 11 - Electronic Records](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11)
- [FDA Guidance: Part 11, Electronic Records; Electronic Signatures — Scope and Application](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application)
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [NIST SP 800-53: Security and Privacy Controls](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final)

---

**End of Authentication System Guide**

For support or questions, contact the FDA Tools development team.
