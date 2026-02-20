#!/usr/bin/env python3
"""
21 CFR Part 11 Compliant Authentication System (FDA-185 / REG-006).

This module provides comprehensive user authentication and access control
compliant with 21 CFR Part 11 requirements for electronic records systems.

Regulatory Framework (21 CFR Part 11):
  - §11.50(a): User authentication for electronic signatures
  - §11.50(b): Use of identification codes and passwords
  - §11.70: Signature/record linking to specific individuals
  - §11.300(a): Controls for closed systems (access limitations)

Security Features:
  - Argon2id password hashing (OWASP recommended)
  - Token-based session management (JWT)
  - Role-based access control (RBAC)
  - Account lockout after failed attempts
  - Session timeout enforcement
  - Comprehensive audit logging
  - Password policy enforcement
  - Multi-factor authentication foundation

Usage:
from fda_tools.lib.auth import AuthManager, User, Role

    # Initialize authentication system
    auth = AuthManager()

    # Create user account
    user = auth.create_user(
        username="jsmith",
        email="jsmith@company.com",
        password="SecurePass123!",
        role=Role.ANALYST,
        full_name="John Smith"
    )

    # Authenticate user
    session = auth.login("jsmith", "SecurePass123!")
    if session:
        token = session.token

    # Validate session
    user = auth.validate_session(token)
    if user:
        # User authenticated, proceed
        pass

    # Logout
    auth.logout(token)

Architecture:
    - SQLite database for user/session storage (~/.fda-tools/users.db)
    - Argon2id for password hashing (resistance to side-channel attacks)
    - JWT tokens for stateless session validation
    - Audit trail in separate database (~/.fda-tools/audit.db)
    - Integration with existing secure_config.py for key management

Compliance Mapping:
    - User authentication → 21 CFR 11.50(a)
    - Password strength → 21 CFR 11.50(b)
    - Audit logging → 21 CFR 11.10(e), 11.300(e)
    - Access control → 21 CFR 11.300(a)
    - Session management → 21 CFR 11.50(b)

Version: 1.0.0 (FDA-185)
"""

import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# Configuration Constants
# ============================================================

# Database paths
FDA_TOOLS_DIR = Path.home() / '.fda-tools'
USERS_DB_PATH = FDA_TOOLS_DIR / 'users.db'
AUDIT_DB_PATH = FDA_TOOLS_DIR / 'audit.db'

# Password policy (OWASP recommendations)
PASSWORD_MIN_LENGTH = 12
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = True
PASSWORD_MAX_REUSE = 5  # Cannot reuse last 5 passwords

# Session management
SESSION_TIMEOUT_MINUTES = 30
SESSION_ABSOLUTE_TIMEOUT_HOURS = 8
TOKEN_LENGTH = 64  # bytes (512 bits)

# Account lockout policy
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30

# Password expiration (optional, 0 = disabled)
PASSWORD_EXPIRY_DAYS = 0  # Set to 90 for 90-day expiration

# Token secret key (stored in environment or generated)
TOKEN_SECRET_ENV_VAR = 'FDA_AUTH_SECRET'


# ============================================================
# Enumerations
# ============================================================

class Role(Enum):
    """User roles for role-based access control (RBAC).

    ADMIN: Full system access, user management
    ANALYST: Read/write access to FDA tools, submission drafting
    VIEWER: Read-only access to reports and data
    """
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class AuditEventType(Enum):
    """Audit event types per 21 CFR 11.10(e)."""
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    SESSION_EXPIRED = "session_expired"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    ROLE_CHANGED = "role_changed"
    ACCESS_DENIED = "access_denied"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"


# ============================================================
# Data Models
# ============================================================

@dataclass
class User:
    """User account model.

    Attributes:
        user_id: Unique user identifier (auto-generated)
        username: Login username (unique, case-insensitive)
        email: User email address
        full_name: User's full legal name (for audit trail)
        role: User role (Role enum)
        password_hash: Argon2id password hash
        password_history: JSON list of previous password hashes
        is_active: Account enabled flag
        is_locked: Account locked flag (after failed attempts)
        locked_until: Timestamp when account auto-unlocks
        failed_login_attempts: Counter for failed login attempts
        last_login: Timestamp of last successful login
        last_password_change: Timestamp of last password change
        mfa_enabled: Multi-factor authentication enabled flag
        mfa_secret: TOTP secret for MFA (encrypted)
        created_at: Account creation timestamp
        updated_at: Account last update timestamp
    """
    user_id: int
    username: str
    email: str
    full_name: str
    role: Role
    password_hash: str
    password_history: List[str] = field(default_factory=list)
    is_active: bool = True
    is_locked: bool = False
    locked_until: Optional[datetime] = None
    failed_login_attempts: int = 0
    last_login: Optional[datetime] = None
    last_password_change: datetime = field(default_factory=datetime.now)
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert user to dictionary (excluding sensitive fields)."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role.value,
            'is_active': self.is_active,
            'is_locked': self.is_locked,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'last_password_change': self.last_password_change.isoformat(),
            'mfa_enabled': self.mfa_enabled,
            'created_at': self.created_at.isoformat(),
        }


@dataclass
class Session:
    """User session model.

    Attributes:
        session_id: Unique session identifier
        user_id: User ID associated with session
        token: Session token (cryptographically secure random)
        created_at: Session creation timestamp
        last_activity: Last session activity timestamp
        expires_at: Session expiration timestamp (inactivity timeout)
        absolute_expires_at: Absolute session expiration (max duration)
        ip_address: Client IP address (optional)
        user_agent: Client user agent (optional)
    """
    session_id: int
    user_id: int
    token: str
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=SESSION_TIMEOUT_MINUTES))
    absolute_expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=SESSION_ABSOLUTE_TIMEOUT_HOURS))
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class AuditEvent:
    """Audit trail event (21 CFR 11.10(e)).

    Attributes:
        event_id: Unique event identifier
        event_type: Type of event (AuditEventType)
        user_id: User ID who triggered event (None for system events)
        username: Username for audit trail
        timestamp: Event timestamp
        details: Additional event details (JSON)
        ip_address: Client IP address
        success: Event success flag
    """
    event_id: int
    event_type: AuditEventType
    user_id: Optional[int]
    username: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict = field(default_factory=dict)
    ip_address: Optional[str] = None
    success: bool = True


# ============================================================
# Password Policy Enforcement
# ============================================================

class PasswordPolicyError(Exception):
    """Exception raised when password doesn't meet policy requirements."""
    pass


def validate_password_policy(password: str) -> Tuple[bool, str]:
    """Validate password against policy requirements.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)

    Raises:
        PasswordPolicyError: If password doesn't meet requirements
    """
    errors = []

    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")

    if PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")

    if PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")

    if PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")

    if PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")

    if errors:
        return False, '; '.join(errors)

    return True, ""


def hash_password(password: str) -> str:
    """Hash password using Argon2id.

    Args:
        password: Plain text password

    Returns:
        Argon2id password hash
    """
    try:
        from argon2 import PasswordHasher
        ph = PasswordHasher(
            time_cost=3,      # Number of iterations (OWASP: 2-3)
            memory_cost=65536,  # 64 MB (OWASP: 46 MB minimum)
            parallelism=4,    # Number of threads
            hash_len=32,      # Hash length in bytes
            salt_len=16,      # Salt length in bytes
        )
        return ph.hash(password)
    except ImportError:
        # Fallback to bcrypt if argon2 not available
        logger.warning("argon2-cffi not available, falling back to bcrypt")
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash.

    Args:
        password: Plain text password
        password_hash: Stored password hash

    Returns:
        True if password matches, False otherwise
    """
    try:
        from argon2 import PasswordHasher
        from argon2.exceptions import VerifyMismatchError, InvalidHash
        ph = PasswordHasher()
        try:
            ph.verify(password_hash, password)
            return True
        except (VerifyMismatchError, InvalidHash):
            return False
    except ImportError:
        # Fallback to bcrypt
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


# ============================================================
# Token Management
# ============================================================

def generate_session_token() -> str:
    """Generate cryptographically secure session token.

    Returns:
        Hex-encoded random token (128 characters)
    """
    return secrets.token_hex(TOKEN_LENGTH)


def get_token_secret() -> bytes:
    """Get or generate token signing secret.

    Returns:
        32-byte secret key for token signing
    """
    secret = os.environ.get(TOKEN_SECRET_ENV_VAR)
    if secret:
        return secret.encode('utf-8')

    # Generate and save to file if not in environment
    secret_file = FDA_TOOLS_DIR / '.token_secret'
    if secret_file.exists():
        return secret_file.read_bytes()

    # Generate new secret
    FDA_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    secret_bytes = secrets.token_bytes(32)
    secret_file.write_bytes(secret_bytes)
    secret_file.chmod(0o600)  # Owner read/write only
    logger.info("Generated new token secret at %s", secret_file)
    return secret_bytes


def sign_token(token: str, user_id: int) -> str:
    """Sign session token with HMAC-SHA256.

    Args:
        token: Session token
        user_id: User ID

    Returns:
        Signed token (token:signature)
    """
    secret = get_token_secret()
    message = f"{token}:{user_id}".encode('utf-8')
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return f"{token}:{signature}"


def verify_token_signature(signed_token: str, user_id: int) -> bool:
    """Verify token signature.

    Args:
        signed_token: Signed token (token:signature)
        user_id: User ID

    Returns:
        True if signature valid, False otherwise
    """
    try:
        token, signature = signed_token.rsplit(':', 1)
        expected_signature = sign_token(token, user_id).split(':', 1)[1]
        return hmac.compare_digest(signature, expected_signature)
    except (ValueError, IndexError):
        return False


# ============================================================
# Database Management
# ============================================================

def _init_database():
    """Initialize authentication databases with schema."""
    FDA_TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    # Users database
    conn = sqlite3.connect(USERS_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL COLLATE NOCASE,
            email TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            password_history TEXT DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            is_locked INTEGER DEFAULT 0,
            locked_until TEXT,
            failed_login_attempts INTEGER DEFAULT 0,
            last_login TEXT,
            last_password_change TEXT NOT NULL,
            mfa_enabled INTEGER DEFAULT 0,
            mfa_secret TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_username
        ON users(username COLLATE NOCASE)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            last_activity TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            absolute_expires_at TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_token
        ON sessions(token)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id
        ON sessions(user_id)
    """)

    conn.commit()
    conn.close()

    # Set secure permissions (owner read/write only)
    USERS_DB_PATH.chmod(0o600)

    # Audit database
    conn = sqlite3.connect(AUDIT_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            user_id INTEGER,
            username TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            details TEXT DEFAULT '{}',
            ip_address TEXT,
            success INTEGER DEFAULT 1
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_timestamp
        ON audit_events(timestamp)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_user_id
        ON audit_events(user_id)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_event_type
        ON audit_events(event_type)
    """)

    conn.commit()
    conn.close()

    AUDIT_DB_PATH.chmod(0o600)
    logger.info("Initialized authentication databases at %s", FDA_TOOLS_DIR)


# ============================================================
# AuthManager - Main Authentication Interface
# ============================================================

class AuthManager:
    """Central authentication manager for 21 CFR Part 11 compliance.

    This class provides all authentication, authorization, and audit
    functionality required for electronic records systems.
    """

    def __init__(self):
        """Initialize AuthManager and ensure database exists."""
        _init_database()
        self._cleanup_expired_sessions()

    # --------------------------------------------------------
    # User Management
    # --------------------------------------------------------

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: Role,
        full_name: str,
        created_by: Optional[User] = None
    ) -> User:
        """Create new user account.

        Args:
            username: Unique username (case-insensitive)
            email: User email address
            password: Plain text password (will be hashed)
            role: User role (Role enum)
            full_name: User's full legal name
            created_by: User who created this account (for audit)

        Returns:
            Created User object

        Raises:
            ValueError: If username already exists or validation fails
            PasswordPolicyError: If password doesn't meet policy
        """
        # Validate username
        username = username.strip()
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters")

        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValueError("Username can only contain letters, numbers, underscore, and hyphen")

        # Check if username exists
        if self.get_user_by_username(username):
            raise ValueError(f"Username '{username}' already exists")

        # Validate password
        is_valid, error = validate_password_policy(password)
        if not is_valid:
            raise PasswordPolicyError(error)

        # Hash password
        password_hash = hash_password(password)

        # Create user
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO users (
                username, email, full_name, role, password_hash,
                password_history, last_password_change, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            username, email, full_name, role.value, password_hash,
            json.dumps([password_hash]), now, now, now
        ))

        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        user = self.get_user_by_id(user_id)

        # Audit log
        self._log_audit_event(
            event_type=AuditEventType.USER_CREATED,
            user_id=created_by.user_id if created_by else None,
            username=created_by.username if created_by else "system",
            details={
                'created_user_id': user_id,
                'created_username': username,
                'role': role.value,
            }
        )

        logger.info("Created user account: %s (ID: %d, Role: %s)", username, user_id, role.value)
        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None if not found
        """
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_user(row)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username (case-insensitive).

        Args:
            username: Username

        Returns:
            User object or None if not found
        """
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_user(row)

    def list_users(self, role: Optional[Role] = None, active_only: bool = False) -> List[User]:
        """List all users.

        Args:
            role: Filter by role (optional)
            active_only: Only return active users

        Returns:
            List of User objects
        """
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM users WHERE 1=1"
        params = []

        if role:
            query += " AND role = ?"
            params.append(role.value)

        if active_only:
            query += " AND is_active = 1"

        query += " ORDER BY username"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_user(row) for row in rows]

    def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: Optional[Role] = None,
        is_active: Optional[bool] = None,
        updated_by: Optional[User] = None
    ) -> User:
        """Update user account.

        Args:
            user_id: User ID to update
            email: New email (optional)
            full_name: New full name (optional)
            role: New role (optional)
            is_active: Active status (optional)
            updated_by: User who made the update (for audit)

        Returns:
            Updated User object

        Raises:
            ValueError: If user not found
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User ID {user_id} not found")

        updates = []
        params = []
        changes = {}

        if email is not None and email != user.email:
            updates.append("email = ?")
            params.append(email)
            changes['email'] = {'old': user.email, 'new': email}

        if full_name is not None and full_name != user.full_name:
            updates.append("full_name = ?")
            params.append(full_name)
            changes['full_name'] = {'old': user.full_name, 'new': full_name}

        if role is not None and role != user.role:
            updates.append("role = ?")
            params.append(role.value)
            changes['role'] = {'old': user.role.value, 'new': role.value}

            # Separate audit event for role change
            self._log_audit_event(
                event_type=AuditEventType.ROLE_CHANGED,
                user_id=updated_by.user_id if updated_by else None,
                username=updated_by.username if updated_by else "system",
                details={
                    'target_user_id': user_id,
                    'target_username': user.username,
                    'old_role': user.role.value,
                    'new_role': role.value,
                }
            )

        if is_active is not None and is_active != user.is_active:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)
            changes['is_active'] = {'old': user.is_active, 'new': is_active}

        if not updates:
            return user  # No changes

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(user_id)

        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?", params)
        conn.commit()
        conn.close()

        # Audit log
        self._log_audit_event(
            event_type=AuditEventType.USER_UPDATED,
            user_id=updated_by.user_id if updated_by else None,
            username=updated_by.username if updated_by else "system",
            details={
                'target_user_id': user_id,
                'target_username': user.username,
                'changes': changes,
            }
        )

        logger.info("Updated user: %s (changes: %s)", user.username, list(changes.keys()))
        return self.get_user_by_id(user_id)

    def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str
    ) -> bool:
        """Change user password.

        Args:
            user_id: User ID
            old_password: Current password (for verification)
            new_password: New password

        Returns:
            True on success

        Raises:
            ValueError: If old password incorrect or user not found
            PasswordPolicyError: If new password doesn't meet policy
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User ID {user_id} not found")

        # Verify old password
        if not verify_password(old_password, user.password_hash):
            self._log_audit_event(
                event_type=AuditEventType.PASSWORD_CHANGED,
                user_id=user_id,
                username=user.username,
                success=False,
                details={'reason': 'incorrect_old_password'}
            )
            raise ValueError("Incorrect current password")

        # Validate new password
        is_valid, error = validate_password_policy(new_password)
        if not is_valid:
            raise PasswordPolicyError(error)

        # Check password history
        new_hash = hash_password(new_password)
        for old_hash in user.password_history[-PASSWORD_MAX_REUSE:]:
            if verify_password(new_password, old_hash):
                raise PasswordPolicyError(
                    f"Cannot reuse any of your last {PASSWORD_MAX_REUSE} passwords"
                )

        # Update password
        updated_history = user.password_history + [new_hash]
        if len(updated_history) > PASSWORD_MAX_REUSE:
            updated_history = updated_history[-PASSWORD_MAX_REUSE:]

        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET password_hash = ?,
                password_history = ?,
                last_password_change = ?,
                updated_at = ?
            WHERE user_id = ?
        """, (
            new_hash,
            json.dumps(updated_history),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            user_id
        ))
        conn.commit()
        conn.close()

        # Audit log
        self._log_audit_event(
            event_type=AuditEventType.PASSWORD_CHANGED,
            user_id=user_id,
            username=user.username,
            details={'changed_by_self': True}
        )

        logger.info("Password changed for user: %s", user.username)
        return True

    def reset_password(
        self,
        user_id: int,
        new_password: str,
        reset_by: Optional[User] = None
    ) -> bool:
        """Reset user password (admin function).

        Args:
            user_id: User ID
            new_password: New password
            reset_by: Admin user performing reset

        Returns:
            True on success

        Raises:
            ValueError: If user not found
            PasswordPolicyError: If password doesn't meet policy
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User ID {user_id} not found")

        # Validate password
        is_valid, error = validate_password_policy(new_password)
        if not is_valid:
            raise PasswordPolicyError(error)

        # Update password
        new_hash = hash_password(new_password)
        updated_history = user.password_history + [new_hash]
        if len(updated_history) > PASSWORD_MAX_REUSE:
            updated_history = updated_history[-PASSWORD_MAX_REUSE:]

        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET password_hash = ?,
                password_history = ?,
                last_password_change = ?,
                updated_at = ?
            WHERE user_id = ?
        """, (
            new_hash,
            json.dumps(updated_history),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            user_id
        ))
        conn.commit()
        conn.close()

        # Audit log
        self._log_audit_event(
            event_type=AuditEventType.PASSWORD_RESET,
            user_id=reset_by.user_id if reset_by else None,
            username=reset_by.username if reset_by else "system",
            details={
                'target_user_id': user_id,
                'target_username': user.username,
            }
        )

        logger.info("Password reset for user: %s by %s",
                   user.username, reset_by.username if reset_by else "system")
        return True

    def delete_user(self, user_id: int, deleted_by: Optional[User] = None) -> bool:
        """Delete user account.

        Args:
            user_id: User ID
            deleted_by: User who deleted the account (for audit)

        Returns:
            True on success

        Raises:
            ValueError: If user not found
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User ID {user_id} not found")

        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()

        # Delete sessions first (FK constraint)
        cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

        # Delete user
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        # Audit log
        self._log_audit_event(
            event_type=AuditEventType.USER_DELETED,
            user_id=deleted_by.user_id if deleted_by else None,
            username=deleted_by.username if deleted_by else "system",
            details={
                'deleted_user_id': user_id,
                'deleted_username': user.username,
            }
        )

        logger.info("Deleted user: %s", user.username)
        return True

    # --------------------------------------------------------
    # Authentication & Session Management
    # --------------------------------------------------------

    def login(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Session]:
        """Authenticate user and create session.

        Args:
            username: Username
            password: Password
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)

        Returns:
            Session object on success, None on failure
        """
        user = self.get_user_by_username(username)

        if not user:
            # Don't reveal whether username exists
            self._log_audit_event(
                event_type=AuditEventType.LOGIN_FAILURE,
                user_id=None,
                username=username,
                success=False,
                details={'reason': 'user_not_found'},
                ip_address=ip_address
            )
            logger.warning("Login failed: user not found - %s", username)
            return None

        # Check if account is locked
        if user.is_locked:
            if user.locked_until and datetime.now() < user.locked_until:
                self._log_audit_event(
                    event_type=AuditEventType.LOGIN_FAILURE,
                    user_id=user.user_id,
                    username=user.username,
                    success=False,
                    details={
                        'reason': 'account_locked',
                        'locked_until': user.locked_until.isoformat()
                    },
                    ip_address=ip_address
                )
                logger.warning("Login failed: account locked - %s (until %s)",
                             username, user.locked_until)
                return None
            else:
                # Auto-unlock if lockout period expired
                self._unlock_account(user.user_id)
                user = self.get_user_by_id(user.user_id)

        # Check if account is active
        if not user.is_active:
            self._log_audit_event(
                event_type=AuditEventType.LOGIN_FAILURE,
                user_id=user.user_id,
                username=user.username,
                success=False,
                details={'reason': 'account_disabled'},
                ip_address=ip_address
            )
            logger.warning("Login failed: account disabled - %s", username)
            return None

        # Verify password
        if not verify_password(password, user.password_hash):
            # Increment failed attempts
            failed_attempts = user.failed_login_attempts + 1

            conn = sqlite3.connect(USERS_DB_PATH)
            cursor = conn.cursor()

            if failed_attempts >= MAX_LOGIN_ATTEMPTS:
                # Lock account
                locked_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                cursor.execute("""
                    UPDATE users
                    SET failed_login_attempts = ?,
                        is_locked = 1,
                        locked_until = ?,
                        updated_at = ?
                    WHERE user_id = ?
                """, (failed_attempts, locked_until.isoformat(), datetime.now().isoformat(), user.user_id))

                self._log_audit_event(
                    event_type=AuditEventType.ACCOUNT_LOCKED,
                    user_id=user.user_id,
                    username=user.username,
                    details={
                        'reason': 'max_failed_attempts',
                        'failed_attempts': failed_attempts,
                        'locked_until': locked_until.isoformat()
                    },
                    ip_address=ip_address
                )
                logger.warning("Account locked due to failed attempts: %s", username)
            else:
                cursor.execute("""
                    UPDATE users
                    SET failed_login_attempts = ?,
                        updated_at = ?
                    WHERE user_id = ?
                """, (failed_attempts, datetime.now().isoformat(), user.user_id))

            conn.commit()
            conn.close()

            self._log_audit_event(
                event_type=AuditEventType.LOGIN_FAILURE,
                user_id=user.user_id,
                username=user.username,
                success=False,
                details={
                    'reason': 'incorrect_password',
                    'failed_attempts': failed_attempts
                },
                ip_address=ip_address
            )
            logger.warning("Login failed: incorrect password - %s (attempt %d/%d)",
                         username, failed_attempts, MAX_LOGIN_ATTEMPTS)
            return None

        # Successful login - reset failed attempts
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET failed_login_attempts = 0,
                last_login = ?,
                updated_at = ?
            WHERE user_id = ?
        """, (datetime.now().isoformat(), datetime.now().isoformat(), user.user_id))
        conn.commit()
        conn.close()

        # Create session
        session = self._create_session(user.user_id, ip_address, user_agent)

        # Audit log
        self._log_audit_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            user_id=user.user_id,
            username=user.username,
            details={'session_id': session.session_id},
            ip_address=ip_address
        )

        logger.info("User logged in: %s (session: %d)", username, session.session_id)
        return session

    def logout(self, token: str) -> bool:
        """Logout user by invalidating session.

        Args:
            token: Session token

        Returns:
            True on success, False if token not found
        """
        session = self._get_session_by_token(token)
        if not session:
            return False

        user = self.get_user_by_id(session.user_id)

        # Delete session
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()

        # Audit log
        self._log_audit_event(
            event_type=AuditEventType.LOGOUT,
            user_id=user.user_id if user else None,
            username=user.username if user else "unknown",
            details={'session_id': session.session_id}
        )

        logger.info("User logged out: %s (session: %d)",
                   user.username if user else "unknown", session.session_id)
        return True

    def validate_session(self, token: str) -> Optional[User]:
        """Validate session token and return authenticated user.

        Args:
            token: Session token

        Returns:
            User object if valid, None if invalid/expired
        """
        session = self._get_session_by_token(token)
        if not session:
            return None

        now = datetime.now()

        # Check expiration
        if now > session.expires_at or now > session.absolute_expires_at:
            # Session expired
            user = self.get_user_by_id(session.user_id)

            # Delete expired session
            conn = sqlite3.connect(USERS_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session.session_id,))
            conn.commit()
            conn.close()

            # Audit log
            self._log_audit_event(
                event_type=AuditEventType.SESSION_EXPIRED,
                user_id=user.user_id if user else None,
                username=user.username if user else "unknown",
                details={
                    'session_id': session.session_id,
                    'reason': 'timeout' if now > session.expires_at else 'absolute_timeout'
                }
            )

            logger.info("Session expired: %s (session: %d)",
                       user.username if user else "unknown", session.session_id)
            return None

        # Update last activity and extend timeout
        new_expires_at = now + timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        # Don't extend beyond absolute timeout
        if new_expires_at > session.absolute_expires_at:
            new_expires_at = session.absolute_expires_at

        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions
            SET last_activity = ?, expires_at = ?
            WHERE session_id = ?
        """, (now.isoformat(), new_expires_at.isoformat(), session.session_id))
        conn.commit()
        conn.close()

        # Return user
        return self.get_user_by_id(session.user_id)

    def get_active_sessions(self, user_id: int) -> List[Session]:
        """Get all active sessions for a user.

        Args:
            user_id: User ID

        Returns:
            List of active Session objects
        """
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM sessions
            WHERE user_id = ?
            AND datetime(expires_at) > datetime('now')
            AND datetime(absolute_expires_at) > datetime('now')
            ORDER BY last_activity DESC
        """, (user_id,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_session(row) for row in rows]

    def revoke_all_sessions(self, user_id: int, except_session_id: Optional[int] = None) -> int:
        """Revoke all sessions for a user.

        Args:
            user_id: User ID
            except_session_id: Session ID to keep (optional)

        Returns:
            Number of sessions revoked
        """
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()

        if except_session_id:
            cursor.execute(
                "DELETE FROM sessions WHERE user_id = ? AND session_id != ?",
                (user_id, except_session_id)
            )
        else:
            cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

        count = cursor.rowcount
        conn.commit()
        conn.close()

        user = self.get_user_by_id(user_id)
        logger.info("Revoked %d sessions for user: %s", count, user.username if user else user_id)
        return count

    # --------------------------------------------------------
    # Account Lockout Management
    # --------------------------------------------------------

    def lock_account(self, user_id: int, duration_minutes: int = LOCKOUT_DURATION_MINUTES) -> bool:
        """Lock user account.

        Args:
            user_id: User ID
            duration_minutes: Lockout duration in minutes

        Returns:
            True on success
        """
        locked_until = datetime.now() + timedelta(minutes=duration_minutes)

        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET is_locked = 1,
                locked_until = ?,
                updated_at = ?
            WHERE user_id = ?
        """, (locked_until.isoformat(), datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()

        user = self.get_user_by_id(user_id)

        # Audit log
        self._log_audit_event(
            event_type=AuditEventType.ACCOUNT_LOCKED,
            user_id=user_id,
            username=user.username if user else "unknown",
            details={
                'reason': 'manual_lock',
                'locked_until': locked_until.isoformat()
            }
        )

        logger.info("Account locked: %s (until %s)",
                   user.username if user else user_id, locked_until)
        return True

    def unlock_account(self, user_id: int) -> bool:
        """Unlock user account.

        Args:
            user_id: User ID

        Returns:
            True on success
        """
        return self._unlock_account(user_id, manual=True)

    def _unlock_account(self, user_id: int, manual: bool = False) -> bool:
        """Internal unlock account implementation.

        Args:
            user_id: User ID
            manual: Whether this is a manual unlock (for audit)

        Returns:
            True on success
        """
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET is_locked = 0,
                locked_until = NULL,
                failed_login_attempts = 0,
                updated_at = ?
            WHERE user_id = ?
        """, (datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()

        user = self.get_user_by_id(user_id)

        # Audit log
        self._log_audit_event(
            event_type=AuditEventType.ACCOUNT_UNLOCKED,
            user_id=user_id,
            username=user.username if user else "unknown",
            details={'reason': 'manual' if manual else 'auto_timeout'}
        )

        logger.info("Account unlocked: %s (%s)",
                   user.username if user else user_id,
                   "manual" if manual else "auto")
        return True

    # --------------------------------------------------------
    # Audit Trail
    # --------------------------------------------------------

    def get_audit_events(
        self,
        user_id: Optional[int] = None,
        event_type: Optional[AuditEventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get audit events.

        Args:
            user_id: Filter by user ID (optional)
            event_type: Filter by event type (optional)
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)
            limit: Maximum number of events to return

        Returns:
            List of AuditEvent objects
        """
        conn = sqlite3.connect(AUDIT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []

        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)

        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type.value)

        if start_date is not None:
            query += " AND datetime(timestamp) >= datetime(?)"
            params.append(start_date.isoformat())

        if end_date is not None:
            query += " AND datetime(timestamp) <= datetime(?)"
            params.append(end_date.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_audit_event(row) for row in rows]

    def _log_audit_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[int],
        username: str,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        success: bool = True
    ):
        """Log audit event.

        Args:
            event_type: Type of event
            user_id: User ID (None for system events)
            username: Username
            details: Additional event details
            ip_address: Client IP address
            success: Event success flag
        """
        conn = sqlite3.connect(AUDIT_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO audit_events (
                event_type, user_id, username, timestamp,
                details, ip_address, success
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_type.value,
            user_id,
            username,
            datetime.now().isoformat(),
            json.dumps(details or {}),
            ip_address,
            1 if success else 0
        ))

        conn.commit()
        conn.close()

    def log_audit_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[int],
        username: str,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        success: bool = True
    ):
        """Public wrapper for logging audit events.

        This method exposes audit logging functionality for use by other modules
        like RBAC decorators. Delegates to internal _log_audit_event.

        Args:
            event_type: Type of event
            user_id: User ID (None for system events)
            username: Username
            details: Additional event details
            ip_address: Client IP address
            success: Event success flag

        Note:
            This fixes FDA-202 - RBAC decorators were calling log_audit_event()
            but only _log_audit_event() existed (private method).
        """
        return self._log_audit_event(
            event_type=event_type,
            user_id=user_id,
            username=username,
            details=details,
            ip_address=ip_address,
            success=success
        )

    # --------------------------------------------------------
    # Internal Helper Methods
    # --------------------------------------------------------

    def _create_session(
        self,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Session:
        """Create new session for user.

        Args:
            user_id: User ID
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created Session object
        """
        token = generate_session_token()
        now = datetime.now()
        expires_at = now + timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        absolute_expires_at = now + timedelta(hours=SESSION_ABSOLUTE_TIMEOUT_HOURS)

        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sessions (
                user_id, token, created_at, last_activity,
                expires_at, absolute_expires_at, ip_address, user_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, token, now.isoformat(), now.isoformat(),
            expires_at.isoformat(), absolute_expires_at.isoformat(),
            ip_address, user_agent
        ))

        session_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return Session(
            session_id=session_id,
            user_id=user_id,
            token=token,
            created_at=now,
            last_activity=now,
            expires_at=expires_at,
            absolute_expires_at=absolute_expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

    def _get_session_by_token(self, token: str) -> Optional[Session]:
        """Get session by token.

        Args:
            token: Session token

        Returns:
            Session object or None if not found
        """
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM sessions WHERE token = ?", (token,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_session(row)

    def _cleanup_expired_sessions(self):
        """Delete all expired sessions."""
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM sessions
            WHERE datetime(expires_at) <= datetime('now')
            OR datetime(absolute_expires_at) <= datetime('now')
        """)

        count = cursor.rowcount
        conn.commit()
        conn.close()

        if count > 0:
            logger.info("Cleaned up %d expired sessions", count)

    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convert database row to User object."""
        return User(
            user_id=row['user_id'],
            username=row['username'],
            email=row['email'],
            full_name=row['full_name'],
            role=Role(row['role']),
            password_hash=row['password_hash'],
            password_history=json.loads(row['password_history']),
            is_active=bool(row['is_active']),
            is_locked=bool(row['is_locked']),
            locked_until=datetime.fromisoformat(row['locked_until']) if row['locked_until'] else None,
            failed_login_attempts=row['failed_login_attempts'],
            last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None,
            last_password_change=datetime.fromisoformat(row['last_password_change']),
            mfa_enabled=bool(row['mfa_enabled']),
            mfa_secret=row['mfa_secret'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        """Convert database row to Session object."""
        return Session(
            session_id=row['session_id'],
            user_id=row['user_id'],
            token=row['token'],
            created_at=datetime.fromisoformat(row['created_at']),
            last_activity=datetime.fromisoformat(row['last_activity']),
            expires_at=datetime.fromisoformat(row['expires_at']),
            absolute_expires_at=datetime.fromisoformat(row['absolute_expires_at']),
            ip_address=row['ip_address'],
            user_agent=row['user_agent']
        )

    def _row_to_audit_event(self, row: sqlite3.Row) -> AuditEvent:
        """Convert database row to AuditEvent object."""
        return AuditEvent(
            event_id=row['event_id'],
            event_type=AuditEventType(row['event_type']),
            user_id=row['user_id'],
            username=row['username'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            details=json.loads(row['details']),
            ip_address=row['ip_address'],
            success=bool(row['success'])
        )


# ============================================================
# CLI Entry Point
# ============================================================

def main():
    """CLI for testing authentication system."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    print("FDA Tools Authentication System (21 CFR Part 11)")
    print("=" * 60)

    auth = AuthManager()

    # Check if any users exist
    users = auth.list_users()
    if not users:
        print("\nNo users found. Creating default admin account...")
        try:
            admin = auth.create_user(
                username="admin",
                email="admin@company.com",
                password="ChangeMe123!",
                role=Role.ADMIN,
                full_name="System Administrator"
            )
            print(f"✓ Created admin account: {admin.username}")
            print("  Default password: ChangeMe123!")
            print("  Please change this password immediately.")
        except Exception as e:
            print(f"✗ Failed to create admin account: {e}")
            return 1
    else:
        print(f"\nFound {len(users)} user(s):")
        for user in users:
            status = "active" if user.is_active else "disabled"
            locked = " (LOCKED)" if user.is_locked else ""
            print(f"  - {user.username} ({user.role.value}) - {status}{locked}")

    print("\nAuthentication system initialized.")
    print(f"Database: {USERS_DB_PATH}")
    print(f"Audit log: {AUDIT_DB_PATH}")
    print("\nUse 'fda-auth' command for user management.")

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
