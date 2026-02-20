# Authentication System Quick Start Guide

**FDA Tools 21 CFR Part 11 Authentication**

---

## First-Time Setup (5 minutes)

### 1. Install Dependencies

```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools
pip3 install argon2-cffi
```

### 2. Initialize System

```bash
python3 lib/auth.py
```

**Expected Output:**
```
FDA Tools Authentication System (21 CFR Part 11)
============================================================

No users found. Creating default admin account...
✓ Created admin account: admin
  Default password: ChangeMe123!
  Please change this password immediately.

Authentication system initialized.
Database: /home/linux/.fda-tools/users.db
Audit log: /home/linux/.fda-tools/audit.db
```

### 3. Create Shell Alias

```bash
# Add to ~/.bashrc or ~/.zshrc
alias fda-auth='python3 /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/auth_cli.py'

# Reload shell
source ~/.bashrc
```

### 4. Initial Login

```bash
fda-auth login
```

**Credentials:**
- Username: `admin`
- Password: `ChangeMe123!`

### 5. Change Admin Password

```bash
fda-auth change-password
```

**New Password Requirements:**
- Minimum 12 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character

---

## Common Tasks

### Login

```bash
fda-auth login
```

### Check Who's Logged In

```bash
fda-auth whoami
```

### Logout

```bash
fda-auth logout
```

---

## User Management (Admin Only)

### Create New User

```bash
fda-auth create-user
```

**Interactive Prompts:**
1. Username (3-32 characters, letters/numbers/underscore/hyphen)
2. Email address
3. Full name
4. Role (1=Admin, 2=Analyst, 3=Viewer)
5. Password (12+ chars, complexity required)
6. Confirm password
7. Confirmation (yes/no)

### List All Users

```bash
fda-auth list-users
```

**Filter Options:**
```bash
fda-auth list-users --role admin      # Only admins
fda-auth list-users --role analyst    # Only analysts
fda-auth list-users --active          # Only active users
fda-auth list-users --json            # JSON output
```

### View User Information

```bash
fda-auth user-info jsmith
```

### Reset User Password

```bash
fda-auth reset-password jsmith
```

**Note:** Generates temporary password. Share securely with user.

### Lock/Unlock Account

```bash
fda-auth lock-account jsmith
fda-auth unlock-account jsmith
```

### Enable/Disable Account

```bash
fda-auth disable-account jsmith
fda-auth enable-account jsmith
```

### Delete Account

```bash
fda-auth delete-account jsmith
```

**Warning:** Requires typing `DELETE` to confirm. Cannot be undone.

---

## Session Management

### List Your Sessions

```bash
fda-auth list-sessions
```

### List Another User's Sessions (Admin Only)

```bash
fda-auth list-sessions jsmith
```

### Revoke All Your Sessions

```bash
fda-auth revoke-sessions
```

**Note:** Logs you out immediately.

### Revoke Another User's Sessions (Admin Only)

```bash
fda-auth revoke-sessions jsmith
```

---

## Audit Log (Admin Only)

### View Recent Events

```bash
fda-auth audit-log
```

### Filter by User

```bash
fda-auth audit-log --username jsmith
```

### Filter by Event Type

```bash
fda-auth audit-log --event-type login_failure
```

**Event Types:**
- `login_success`
- `login_failure`
- `logout`
- `user_created`
- `user_updated`
- `user_deleted`
- `password_changed`
- `password_reset`
- `account_locked`
- `account_unlocked`
- `role_changed`
- `session_expired`

### Filter by Date

```bash
fda-auth audit-log --start-date 2026-02-01 --end-date 2026-02-20
```

### Export to JSON

```bash
fda-auth audit-log --json > audit_export.json
```

### Limit Results

```bash
fda-auth audit-log --limit 50
```

---

## Password Management

### Change Your Password

```bash
fda-auth change-password
```

**Prompts:**
1. Current password
2. New password
3. Confirm new password

**Password Rules:**
- Minimum 12 characters
- Uppercase + lowercase required
- Digit required
- Special character required
- Cannot reuse last 5 passwords

---

## Troubleshooting

### Forgot Password

**If you're an admin:**
```bash
fda-auth reset-password your-username
```

**If you're not an admin:**
Contact your system administrator.

### Account Locked

**Auto-unlock:** Wait 30 minutes after last failed attempt
**Manual unlock (admin):**
```bash
fda-auth unlock-account jsmith
```

### Session Expired

```bash
fda-auth login
```

**Sessions expire after:**
- 30 minutes of inactivity
- 8 hours (absolute maximum)

### Permission Denied

**Check your role:**
```bash
fda-auth whoami
```

**Admin-only operations:**
- Create users
- Reset passwords
- Lock/unlock accounts
- View audit logs
- Delete users

### Database Error

**Check database exists:**
```bash
ls -la ~/.fda-tools/
```

**Reinitialize (caution: loses data):**
```bash
rm ~/.fda-tools/users.db ~/.fda-tools/audit.db
python3 lib/auth.py
```

---

## User Roles

### Admin

**Permissions:**
- Full system access
- User management
- Password resets
- Audit log access
- Account management

**Use Case:** System administrators, IT staff

### Analyst

**Permissions:**
- Read/write FDA tools
- Submission drafting
- Report generation
- Data analysis
- Change own password

**Use Case:** Regulatory affairs professionals

### Viewer

**Permissions:**
- Read-only access
- View submissions
- View reports
- View data
- Change own password

**Use Case:** Management, auditors, reviewers

---

## Security Best Practices

### Password Security

✅ **DO:**
- Use a password manager
- Create unique passwords for each account
- Change password if suspected compromise
- Use 15+ character passwords (stronger than minimum)

❌ **DON'T:**
- Reuse passwords from other systems
- Share passwords with colleagues
- Write passwords on sticky notes
- Use dictionary words or common patterns

### Session Security

✅ **DO:**
- Logout when finished
- Lock your computer when away
- Revoke old sessions regularly

❌ **DON'T:**
- Leave sessions open overnight
- Share session tokens
- Access from untrusted computers

### Account Security

✅ **DO:**
- Report suspicious activity immediately
- Review your audit log periodically
- Update contact email if changed

❌ **DON'T:**
- Share accounts with colleagues
- Use generic usernames (create individual accounts)
- Ignore account lockout notifications

---

## Files and Locations

### Databases

- **Users/Sessions:** `~/.fda-tools/users.db`
- **Audit Trail:** `~/.fda-tools/audit.db`
- **Permissions:** 600 (owner read/write only)

### Session Token

- **Location:** `~/.fda-tools/.session_token`
- **Permissions:** 600
- **Note:** Deleted on logout

### Token Secret

- **Location:** `~/.fda-tools/.token_secret`
- **Permissions:** 600
- **Note:** Auto-generated on first run

---

## Command Reference

| Command | Description | Admin Only |
|---------|-------------|------------|
| `login` | Authenticate user | No |
| `logout` | End session | No |
| `whoami` | Show current user | No |
| `create-user` | Create new user | Yes |
| `list-users` | List all users | No |
| `user-info <username>` | Show user details | No |
| `change-password` | Change your password | No |
| `reset-password <username>` | Reset user password | Yes |
| `lock-account <username>` | Lock user account | Yes |
| `unlock-account <username>` | Unlock user account | Yes |
| `disable-account <username>` | Disable user account | Yes |
| `enable-account <username>` | Enable user account | Yes |
| `delete-account <username>` | Delete user account | Yes |
| `list-sessions [username]` | List active sessions | Admin for others |
| `revoke-sessions [username]` | Revoke sessions | Admin for others |
| `audit-log` | View audit log | Yes |

---

## Help

### Get Command Help

```bash
fda-auth --help
fda-auth login --help
fda-auth list-users --help
```

### Get System Version

```bash
python3 lib/auth.py
```

### Run Tests

```bash
python3 -m pytest tests/test_auth.py -v
```

---

## Support

### Documentation

- **Quick Start:** This document
- **Full Implementation:** `FDA-185_IMPLEMENTATION_COMPLETE.md`
- **Compliance Mapping:** `docs/CFR_PART_11_COMPLIANCE_MAPPING.md`
- **Test Suite:** `tests/test_auth.py`

### Issues

Report authentication issues to your system administrator.

---

**Last Updated:** 2026-02-20
**Version:** 1.0.0
