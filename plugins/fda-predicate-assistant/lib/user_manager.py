"""
User Manager - Multi-User Account Management for FDA Tools Enterprise

Manages user accounts, enrollment, and authentication for multi-user
enterprise deployments. Supports messaging handle mapping for WhatsApp,
Telegram, Slack, and Discord integration.

Key Features:
1. User CRUD operations with JSON persistence
2. Enrollment token generation and verification
3. Messaging handle-based authentication
4. Thread-safe operations with file locking
5. Audit-compatible user lifecycle events

Storage: ~/.claude/fda-tools.users.json

Author: FDA Tools Development Team
Date: 2026-02-16
Version: 1.0.0
"""

import os
import json
import uuid
import hmac
import hashlib
import secrets
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from copy import deepcopy


@dataclass
class User:
    """
    Represents a user account in the FDA Tools enterprise system.

    Attributes:
        user_id: Unique identifier (UUID format: usr_<hex>)
        email: User email address
        name: Full name
        role: Role assignment (admin, ra_professional, reviewer, readonly)
        organization_id: Organization/tenant identifier
        messaging_handles: Platform-to-handle mapping
        enrolled_at: ISO 8601 enrollment timestamp
        last_login: ISO 8601 last login timestamp (None if never logged in)
        is_active: Whether account is active
        metadata: Additional user data (department, title, etc.)
    """
    user_id: str
    email: str
    name: str
    role: str
    organization_id: str
    messaging_handles: Dict[str, str] = field(default_factory=dict)
    enrolled_at: str = ""
    last_login: Optional[str] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize user to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Deserialize user from dictionary."""
        return cls(
            user_id=data['user_id'],
            email=data['email'],
            name=data['name'],
            role=data['role'],
            organization_id=data['organization_id'],
            messaging_handles=data.get('messaging_handles', {}),
            enrolled_at=data.get('enrolled_at', ''),
            last_login=data.get('last_login'),
            is_active=data.get('is_active', True),
            metadata=data.get('metadata', {})
        )


@dataclass
class EnrollmentToken:
    """
    Enrollment token for user onboarding.

    Attributes:
        token: Secure random token string
        user_id: Associated user ID
        expires_at: ISO 8601 expiration timestamp
        used: Whether token has been consumed
    """
    token: str
    user_id: str
    expires_at: str
    used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize token to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnrollmentToken':
        """Deserialize token from dictionary."""
        return cls(
            token=data['token'],
            user_id=data['user_id'],
            expires_at=data['expires_at'],
            used=data.get('used', False)
        )

    def is_expired(self) -> bool:
        """Check if token has expired."""
        expires = datetime.fromisoformat(
            self.expires_at.rstrip('Z')
        ).replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires


# Valid roles
VALID_ROLES = {'admin', 'ra_professional', 'reviewer', 'readonly'}

# Valid messaging platforms
VALID_PLATFORMS = {'whatsapp', 'telegram', 'slack', 'discord', 'email', 'sms'}


class UserManager:
    """
    Manages user accounts with JSON file persistence.

    Thread-safe operations with in-memory caching and file-based storage.
    All mutations are persisted immediately to disk.

    Usage:
        manager = UserManager()
        user = manager.create_user(
            email="alice@device-corp.com",
            name="Alice Johnson",
            role="ra_professional",
            organization_id="org_acme"
        )
    """

    def __init__(self, user_db_path: Optional[str] = None):
        """
        Initialize user manager.

        Args:
            user_db_path: Path to user database JSON file
                         (default: ~/.claude/fda-tools.users.json)
        """
        if user_db_path is None:
            user_db_path = os.path.expanduser("~/.claude/fda-tools.users.json")

        self.db_path = Path(user_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._users: Dict[str, User] = {}
        self._tokens: Dict[str, EnrollmentToken] = {}
        self._email_index: Dict[str, str] = {}  # email -> user_id
        self._handle_index: Dict[str, str] = {}  # "platform:handle" -> user_id

        # Load existing data
        self._load_db()

    # ========================================
    # User CRUD Operations
    # ========================================

    def create_user(
        self,
        email: str,
        name: str,
        role: str,
        organization_id: str,
        messaging_handles: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> User:
        """
        Create a new user account.

        Args:
            email: User email address
            name: Full name
            role: Role (admin, ra_professional, reviewer, readonly)
            organization_id: Organization identifier
            messaging_handles: Optional platform-to-handle mapping
            metadata: Optional additional user data

        Returns:
            Created User object

        Raises:
            ValueError: If email already exists or role is invalid
        """
        # Validate inputs
        self._validate_email(email)
        self._validate_role(role)

        with self._lock:
            # Check for duplicate email
            if email.lower() in self._email_index:
                raise ValueError(
                    "User with email '{}' already exists".format(email)
                )

            # Generate user ID
            user_id = "usr_{}".format(uuid.uuid4().hex[:12])
            now = datetime.now(timezone.utc).isoformat() + 'Z'

            user = User(
                user_id=user_id,
                email=email.lower().strip(),
                name=name.strip(),
                role=role,
                organization_id=organization_id,
                messaging_handles=messaging_handles or {},
                enrolled_at=now,
                last_login=None,
                is_active=True,
                metadata=metadata or {}
            )

            # Store user
            self._users[user_id] = user
            self._email_index[user.email] = user_id

            # Index messaging handles
            for platform, handle in user.messaging_handles.items():
                key = "{}:{}".format(platform.lower(), handle.lower())
                self._handle_index[key] = user_id

            # Persist
            self._save_db()

        return deepcopy(user)

    def get_user(self, user_id: str) -> Optional[User]:
        """
        Retrieve a user by ID.

        Args:
            user_id: User identifier

        Returns:
            User object or None if not found
        """
        with self._lock:
            user = self._users.get(user_id)
            return deepcopy(user) if user else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by email address.

        Args:
            email: Email address

        Returns:
            User object or None if not found
        """
        with self._lock:
            user_id = self._email_index.get(email.lower().strip())
            if user_id:
                user = self._users.get(user_id)
                return deepcopy(user) if user else None
        return None

    def get_user_by_handle(self, platform: str, handle: str) -> Optional[User]:
        """
        Retrieve a user by messaging handle.

        Args:
            platform: Messaging platform (whatsapp, telegram, slack, etc.)
            handle: User's handle on the platform

        Returns:
            User object or None if not found
        """
        with self._lock:
            key = "{}:{}".format(platform.lower(), handle.lower())
            user_id = self._handle_index.get(key)
            if user_id:
                user = self._users.get(user_id)
                return deepcopy(user) if user else None
        return None

    def update_user(self, user_id: str, updates: Dict[str, Any]) -> User:
        """
        Update user attributes.

        Args:
            user_id: User identifier
            updates: Dictionary of attributes to update
                     Allowed keys: name, role, is_active, messaging_handles, metadata

        Returns:
            Updated User object

        Raises:
            ValueError: If user not found or invalid update
        """
        allowed_fields = {'name', 'role', 'is_active', 'messaging_handles', 'metadata'}

        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                raise ValueError("User not found: {}".format(user_id))

            for key, value in updates.items():
                if key not in allowed_fields:
                    raise ValueError(
                        "Cannot update field '{}'. Allowed: {}".format(
                            key, ', '.join(sorted(allowed_fields))
                        )
                    )

                if key == 'role':
                    self._validate_role(value)

                if key == 'messaging_handles':
                    # Rebuild handle index for this user
                    old_handles = user.messaging_handles or {}
                    for platform, handle in old_handles.items():
                        old_key = "{}:{}".format(platform.lower(), handle.lower())
                        self._handle_index.pop(old_key, None)

                    for platform, handle in value.items():
                        new_key = "{}:{}".format(platform.lower(), handle.lower())
                        self._handle_index[new_key] = user_id

                setattr(user, key, value)

            # Persist
            self._save_db()

            return deepcopy(user)

    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user account.

        Note: In production, prefer soft-delete (is_active=False) for
        audit trail preservation. Hard delete removes all traces.

        Args:
            user_id: User identifier

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            user = self._users.get(user_id)
            if user is None:
                return False

            # Remove from indices
            self._email_index.pop(user.email, None)
            for platform, handle in user.messaging_handles.items():
                key = "{}:{}".format(platform.lower(), handle.lower())
                self._handle_index.pop(key, None)

            # Remove user
            del self._users[user_id]

            # Remove associated tokens
            tokens_to_remove = [
                tok_id for tok_id, tok in self._tokens.items()
                if tok.user_id == user_id
            ]
            for tok_id in tokens_to_remove:
                del self._tokens[tok_id]

            # Persist
            self._save_db()

        return True

    def list_users(self, organization_id: Optional[str] = None) -> List[User]:
        """
        List users, optionally filtered by organization.

        Args:
            organization_id: Optional organization filter

        Returns:
            List of User objects
        """
        with self._lock:
            users = list(self._users.values())

            if organization_id:
                users = [
                    u for u in users
                    if u.organization_id == organization_id
                ]

            return [deepcopy(u) for u in users]

    # ========================================
    # Enrollment
    # ========================================

    def generate_enrollment_token(
        self,
        user_id: str,
        expires_hours: int = 24
    ) -> str:
        """
        Generate an enrollment token for a user.

        Args:
            user_id: User to generate token for
            expires_hours: Token validity period in hours

        Returns:
            Token string

        Raises:
            ValueError: If user not found
        """
        with self._lock:
            if user_id not in self._users:
                raise ValueError("User not found: {}".format(user_id))

            # Generate secure token
            token_str = "tok_{}".format(secrets.token_hex(16))
            expires = datetime.now(timezone.utc) + timedelta(hours=expires_hours)

            token = EnrollmentToken(
                token=token_str,
                user_id=user_id,
                expires_at=expires.isoformat() + 'Z',
                used=False
            )

            self._tokens[token_str] = token
            self._save_db()

        return token_str

    def verify_enrollment_token(self, token: str) -> Optional[User]:
        """
        Verify an enrollment token and return the associated user.

        Args:
            token: Token string to verify

        Returns:
            Associated User if token is valid, None otherwise
        """
        with self._lock:
            enrollment = self._tokens.get(token)

            if enrollment is None:
                return None

            if enrollment.used:
                return None

            if enrollment.is_expired():
                return None

            user = self._users.get(enrollment.user_id)
            return deepcopy(user) if user else None

    def complete_enrollment(
        self,
        token: str,
        messaging_handles: Dict[str, str]
    ) -> User:
        """
        Complete enrollment by consuming token and linking messaging handles.

        Args:
            token: Enrollment token
            messaging_handles: Platform-to-handle mapping to link

        Returns:
            Updated User object

        Raises:
            ValueError: If token is invalid, expired, or already used
        """
        with self._lock:
            enrollment = self._tokens.get(token)

            if enrollment is None:
                raise ValueError("Invalid enrollment token")

            if enrollment.used:
                raise ValueError("Enrollment token already used")

            if enrollment.is_expired():
                raise ValueError("Enrollment token expired")

            user = self._users.get(enrollment.user_id)
            if user is None:
                raise ValueError("User not found for token")

            # Link messaging handles
            for platform, handle in messaging_handles.items():
                user.messaging_handles[platform.lower()] = handle
                key = "{}:{}".format(platform.lower(), handle.lower())
                self._handle_index[key] = user.user_id

            # Mark token as used
            enrollment.used = True

            # Persist
            self._save_db()

            return deepcopy(user)

    # ========================================
    # Authentication
    # ========================================

    def authenticate_by_handle(
        self,
        platform: str,
        handle: str
    ) -> Optional[User]:
        """
        Authenticate a user by their messaging handle.

        This is the primary authentication method for messaging platform
        integrations (WhatsApp, Telegram, Slack, Discord).

        Args:
            platform: Messaging platform
            handle: User's handle on the platform

        Returns:
            Authenticated User if found and active, None otherwise
        """
        user = self.get_user_by_handle(platform, handle)

        if user is None:
            return None

        if not user.is_active:
            return None

        # Update last login
        self.update_last_login(user.user_id)

        return user

    def update_last_login(self, user_id: str) -> None:
        """
        Update the last login timestamp for a user.

        Args:
            user_id: User identifier
        """
        with self._lock:
            user = self._users.get(user_id)
            if user:
                user.last_login = datetime.now(timezone.utc).isoformat() + 'Z'
                self._save_db()

    # ========================================
    # Validation Helpers
    # ========================================

    @staticmethod
    def _validate_email(email: str) -> None:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Raises:
            ValueError: If email format is invalid
        """
        if not email or not isinstance(email, str):
            raise ValueError("Email is required")

        email = email.strip()
        if '@' not in email or '.' not in email.split('@')[-1]:
            raise ValueError("Invalid email format: {}".format(email))

        if len(email) > 254:
            raise ValueError("Email too long (max 254 characters)")

    @staticmethod
    def _validate_role(role: str) -> None:
        """
        Validate role assignment.

        Args:
            role: Role to validate

        Raises:
            ValueError: If role is not valid
        """
        if role not in VALID_ROLES:
            raise ValueError(
                "Invalid role '{}'. Valid roles: {}".format(
                    role, ', '.join(sorted(VALID_ROLES))
                )
            )

    # ========================================
    # Persistence
    # ========================================

    def _load_db(self) -> None:
        """Load user database from disk."""
        if not self.db_path.exists():
            return

        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        # Load users
        for user_data in data.get('users', []):
            try:
                user = User.from_dict(user_data)
                self._users[user.user_id] = user
                self._email_index[user.email] = user.user_id

                for platform, handle in user.messaging_handles.items():
                    key = "{}:{}".format(platform.lower(), handle.lower())
                    self._handle_index[key] = user.user_id
            except (KeyError, TypeError):
                continue

        # Load tokens
        for token_data in data.get('enrollment_tokens', []):
            try:
                token = EnrollmentToken.from_dict(token_data)
                self._tokens[token.token] = token
            except (KeyError, TypeError):
                continue

    def _save_db(self) -> None:
        """Save user database to disk."""
        data = {
            'users': [u.to_dict() for u in self._users.values()],
            'enrollment_tokens': [t.to_dict() for t in self._tokens.values()],
            'last_modified': datetime.now(timezone.utc).isoformat() + 'Z',
            'version': '1.0.0'
        }

        try:
            temp_path = self.db_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            temp_path.replace(self.db_path)
        except OSError:
            # If atomic write fails, try direct write
            try:
                with open(self.db_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
            except OSError:
                pass

    @property
    def user_count(self) -> int:
        """Get total number of users."""
        with self._lock:
            return len(self._users)

    @property
    def active_user_count(self) -> int:
        """Get number of active users."""
        with self._lock:
            return sum(1 for u in self._users.values() if u.is_active)


# Global singleton instance
_user_manager_instance: Optional[UserManager] = None


def get_user_manager(user_db_path: Optional[str] = None) -> UserManager:
    """
    Get global UserManager instance (singleton pattern).

    Args:
        user_db_path: Optional path to user database

    Returns:
        UserManager instance
    """
    global _user_manager_instance
    if _user_manager_instance is None:
        _user_manager_instance = UserManager(user_db_path)
    return _user_manager_instance
