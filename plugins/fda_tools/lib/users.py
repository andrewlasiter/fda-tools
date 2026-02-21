#!/usr/bin/env python3
"""
User Management Module (FDA-185 / REG-006).

This module provides high-level user management functions and utilities
for the 21 CFR Part 11 authentication system.

Features:
  - User account lifecycle management
  - Password strength validation
  - Role assignment and validation
  - User status reporting
  - Batch user operations
  - Integration with audit logging

Usage:
from fda_tools.lib.users import UserManager

    mgr = UserManager()

    # Create user
    user = mgr.create_user_interactive()

    # List users
    users = mgr.list_users_formatted()

    # User info
    info = mgr.get_user_info("jsmith")

Version: 1.0.0 (FDA-185)
"""

import getpass
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from fda_tools.lib.auth import AuthManager, Role, User, PasswordPolicyError

logger = logging.getLogger(__name__)


# ============================================================
# User Management
# ============================================================

class UserManager:
    """High-level user management interface."""

    def __init__(self) -> None:
        """Initialize UserManager."""
        self.auth = AuthManager()

    # --------------------------------------------------------
    # User Creation
    # --------------------------------------------------------

    def create_user_interactive(
        self,
        created_by: Optional[User] = None
    ) -> Optional[User]:
        """Interactively create user account.

        Args:
            created_by: User who is creating the account (for audit)

        Returns:
            Created User object or None on cancellation
        """
        print("\n" + "=" * 60)
        print("CREATE USER ACCOUNT")
        print("=" * 60)

        # Username
        while True:
            username = input("\nUsername (3-32 chars, letters/numbers/underscore/hyphen): ").strip()
            if not username:
                print("Cancelled.")
                return None

            if len(username) < 3 or len(username) > 32:
                print("✗ Username must be 3-32 characters")
                continue

            if not re.match(r'^[a-zA-Z0-9_-]+$', username):
                print("✗ Username can only contain letters, numbers, underscore, and hyphen")
                continue

            if self.auth.get_user_by_username(username):
                print(f"✗ Username '{username}' already exists")
                continue

            break

        # Email
        while True:
            email = input("Email: ").strip()
            if not email:
                print("Cancelled.")
                return None

            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                print("✗ Invalid email format")
                continue

            break

        # Full name
        full_name = input("Full name: ").strip()
        if not full_name:
            print("Cancelled.")
            return None

        # Role
        print("\nAvailable roles:")
        print("  1. Admin   - Full system access, user management")
        print("  2. Analyst - Read/write access to FDA tools, submission drafting")
        print("  3. Viewer  - Read-only access to reports and data")

        while True:
            role_input = input("Role (1-3): ").strip()
            if not role_input:
                print("Cancelled.")
                return None

            role_map = {
                '1': Role.ADMIN,
                '2': Role.ANALYST,
                '3': Role.VIEWER,
            }

            role = role_map.get(role_input)
            if not role:
                print("✗ Invalid role selection")
                continue

            break

        # Password
        print("\nPassword requirements:")
        print("  - Minimum 12 characters")
        print("  - At least one uppercase letter")
        print("  - At least one lowercase letter")
        print("  - At least one digit")
        print("  - At least one special character (!@#$%^&*...)")

        while True:
            password = getpass.getpass("\nPassword (hidden): ")
            if not password:
                print("Cancelled.")
                return None

            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                print("✗ Passwords do not match")
                continue

            try:
                from fda_tools.lib.auth import validate_password_policy
                is_valid, error = validate_password_policy(password)
                if not is_valid:
                    print(f"✗ {error}")
                    continue
            except Exception as e:
                print(f"✗ Password validation failed: {e}")
                continue

            break

        # Confirmation
        print("\n" + "-" * 60)
        print("CONFIRM USER CREATION")
        print("-" * 60)
        print(f"Username:  {username}")
        print(f"Email:     {email}")
        print(f"Full name: {full_name}")
        print(f"Role:      {role.value}")

        confirm = input("\nCreate user? (yes/no): ").strip().lower()
        if confirm not in ('yes', 'y'):
            print("Cancelled.")
            return None

        # Create user
        try:
            user = self.auth.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                full_name=full_name,
                created_by=created_by
            )
            print(f"\n✓ User created successfully: {user.username} (ID: {user.user_id})")
            return user
        except Exception as e:
            print(f"\n✗ Failed to create user: {e}")
            return None

    def create_user_batch(
        self,
        username: str,
        email: str,
        password: str,
        role: Role,
        full_name: str,
        created_by: Optional[User] = None
    ) -> Tuple[bool, str, Optional[User]]:
        """Create user account (batch mode).

        Args:
            username: Username
            email: Email
            password: Password
            role: User role
            full_name: Full name
            created_by: User who created the account

        Returns:
            Tuple of (success, message, user)
        """
        try:
            user = self.auth.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                full_name=full_name,
                created_by=created_by
            )
            return True, f"Created user: {username}", user
        except Exception as e:
            return False, f"Failed to create user {username}: {e}", None

    # --------------------------------------------------------
    # User Information
    # --------------------------------------------------------

    def get_user_info(self, username: str) -> Optional[Dict]:
        """Get detailed user information.

        Args:
            username: Username

        Returns:
            Dictionary with user info or None if not found
        """
        user = self.auth.get_user_by_username(username)
        if not user:
            return None

        active_sessions = self.auth.get_active_sessions(user.user_id)

        info = {
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role.value,
            'is_active': user.is_active,
            'is_locked': user.is_locked,
            'locked_until': user.locked_until.isoformat() if user.locked_until else None,
            'failed_login_attempts': user.failed_login_attempts,
            'last_login': user.last_login.isoformat() if user.last_login else "Never",
            'last_password_change': user.last_password_change.isoformat(),
            'mfa_enabled': user.mfa_enabled,
            'created_at': user.created_at.isoformat(),
            'updated_at': user.updated_at.isoformat(),
            'active_sessions': len(active_sessions),
        }

        # Password age
        password_age = datetime.now() - user.last_password_change
        info['password_age_days'] = password_age.days

        return info

    def print_user_info(self, username: str) -> None:
        """Print formatted user information.

        Args:
            username: Username
        """
        info = self.get_user_info(username)
        if not info:
            print(f"User not found: {username}")
            return

        print("\n" + "=" * 60)
        print(f"USER INFORMATION: {username}")
        print("=" * 60)
        print(f"User ID:         {info['user_id']}")
        print(f"Email:           {info['email']}")
        print(f"Full name:       {info['full_name']}")
        print(f"Role:            {info['role']}")
        print(f"Status:          {'Active' if info['is_active'] else 'Disabled'}")

        if info['is_locked']:
            if info['locked_until']:
                print(f"Account locked:  Until {info['locked_until']}")
            else:
                print(f"Account locked:  Yes")
        else:
            print(f"Account locked:  No")

        if info['failed_login_attempts'] > 0:
            print(f"Failed attempts: {info['failed_login_attempts']}")

        print(f"\nLast login:      {info['last_login']}")
        print(f"Active sessions: {info['active_sessions']}")
        print(f"MFA enabled:     {'Yes' if info['mfa_enabled'] else 'No'}")

        print(f"\nPassword age:    {info['password_age_days']} days")
        print(f"Last changed:    {info['last_password_change']}")

        print(f"\nAccount created: {info['created_at']}")
        print(f"Last updated:    {info['updated_at']}")

    # --------------------------------------------------------
    # User Listing
    # --------------------------------------------------------

    def list_users_formatted(
        self,
        role: Optional[Role] = None,
        active_only: bool = False
    ) -> None:
        """Print formatted user list.

        Args:
            role: Filter by role (optional)
            active_only: Only show active users
        """
        users = self.auth.list_users(role=role, active_only=active_only)

        if not users:
            print("No users found.")
            return

        print("\n" + "=" * 100)
        print(f"USER LIST ({len(users)} user{'s' if len(users) != 1 else ''})")
        print("=" * 100)

        # Header
        print(f"{'ID':<5} {'Username':<20} {'Full Name':<25} {'Role':<10} {'Status':<10} {'Last Login':<20}")
        print("-" * 100)

        # Users
        for user in users:
            user_id = str(user.user_id)
            username = user.username[:19]
            full_name = user.full_name[:24]
            role_str = user.role.value
            status = "Active" if user.is_active else "Disabled"
            if user.is_locked:
                status = "LOCKED"
            last_login = user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "Never"

            print(f"{user_id:<5} {username:<20} {full_name:<25} {role_str:<10} {status:<10} {last_login:<20}")

    def list_users_json(
        self,
        role: Optional[Role] = None,
        active_only: bool = False
    ) -> List[Dict]:
        """Get user list as JSON.

        Args:
            role: Filter by role (optional)
            active_only: Only show active users

        Returns:
            List of user dictionaries
        """
        users = self.auth.list_users(role=role, active_only=active_only)
        return [user.to_dict() for user in users]

    # --------------------------------------------------------
    # Password Management
    # --------------------------------------------------------

    def change_password_interactive(self, username: str) -> bool:
        """Interactively change user password.

        Args:
            username: Username

        Returns:
            True on success, False otherwise
        """
        user = self.auth.get_user_by_username(username)
        if not user:
            print(f"User not found: {username}")
            return False

        print("\n" + "=" * 60)
        print(f"CHANGE PASSWORD: {username}")
        print("=" * 60)

        # Current password
        old_password = getpass.getpass("\nCurrent password: ")
        if not old_password:
            print("Cancelled.")
            return False

        # New password
        print("\nPassword requirements:")
        print("  - Minimum 12 characters")
        print("  - At least one uppercase letter")
        print("  - At least one lowercase letter")
        print("  - At least one digit")
        print("  - At least one special character")

        while True:
            new_password = getpass.getpass("\nNew password: ")
            if not new_password:
                print("Cancelled.")
                return False

            confirm_password = getpass.getpass("Confirm new password: ")
            if new_password != confirm_password:
                print("✗ Passwords do not match")
                continue

            break

        # Change password
        try:
            self.auth.change_password(user.user_id, old_password, new_password)
            print("\n✓ Password changed successfully")
            return True
        except Exception as e:
            print(f"\n✗ Failed to change password: {e}")
            return False

    def reset_password_interactive(
        self,
        username: str,
        admin_user: Optional[User] = None
    ) -> bool:
        """Interactively reset user password (admin function).

        Args:
            username: Username
            admin_user: Admin user performing reset

        Returns:
            True on success, False otherwise
        """
        user = self.auth.get_user_by_username(username)
        if not user:
            print(f"User not found: {username}")
            return False

        print("\n" + "=" * 60)
        print(f"RESET PASSWORD: {username}")
        print("=" * 60)
        print("\nWARNING: This will reset the user's password.")
        print("The user should change their password on first login.")

        confirm = input("\nContinue? (yes/no): ").strip().lower()
        if confirm not in ('yes', 'y'):
            print("Cancelled.")
            return False

        # Generate temporary password
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(16))

        # Ensure it meets policy
        temp_password = "Temp" + temp_password + "1!"

        try:
            self.auth.reset_password(user.user_id, temp_password, admin_user)
            print("\n✓ Password reset successfully")
            print(f"\nTemporary password: {temp_password}")
            print("\nIMPORTANT: Share this password securely with the user.")
            print("Instruct them to change it immediately upon login.")
            return True
        except Exception as e:
            print(f"\n✗ Failed to reset password: {e}")
            return False

    # --------------------------------------------------------
    # Account Management
    # --------------------------------------------------------

    def lock_account_interactive(self, username: str) -> bool:
        """Interactively lock user account.

        Args:
            username: Username

        Returns:
            True on success, False otherwise
        """
        user = self.auth.get_user_by_username(username)
        if not user:
            print(f"User not found: {username}")
            return False

        if user.is_locked:
            print(f"Account already locked: {username}")
            return False

        print("\n" + "=" * 60)
        print(f"LOCK ACCOUNT: {username}")
        print("=" * 60)

        confirm = input("\nLock this account? (yes/no): ").strip().lower()
        if confirm not in ('yes', 'y'):
            print("Cancelled.")
            return False

        try:
            self.auth.lock_account(user.user_id)
            print(f"\n✓ Account locked: {username}")
            return True
        except Exception as e:
            print(f"\n✗ Failed to lock account: {e}")
            return False

    def unlock_account_interactive(self, username: str) -> bool:
        """Interactively unlock user account.

        Args:
            username: Username

        Returns:
            True on success, False otherwise
        """
        user = self.auth.get_user_by_username(username)
        if not user:
            print(f"User not found: {username}")
            return False

        if not user.is_locked:
            print(f"Account not locked: {username}")
            return False

        print("\n" + "=" * 60)
        print(f"UNLOCK ACCOUNT: {username}")
        print("=" * 60)

        confirm = input("\nUnlock this account? (yes/no): ").strip().lower()
        if confirm not in ('yes', 'y'):
            print("Cancelled.")
            return False

        try:
            self.auth.unlock_account(user.user_id)
            print(f"\n✓ Account unlocked: {username}")
            return True
        except Exception as e:
            print(f"\n✗ Failed to unlock account: {e}")
            return False

    def disable_account_interactive(self, username: str, admin_user: Optional[User] = None) -> bool:
        """Interactively disable user account.

        Args:
            username: Username
            admin_user: Admin user performing action

        Returns:
            True on success, False otherwise
        """
        user = self.auth.get_user_by_username(username)
        if not user:
            print(f"User not found: {username}")
            return False

        if not user.is_active:
            print(f"Account already disabled: {username}")
            return False

        print("\n" + "=" * 60)
        print(f"DISABLE ACCOUNT: {username}")
        print("=" * 60)
        print("\nThis will prevent the user from logging in.")
        print("All active sessions will remain valid until they expire.")

        confirm = input("\nDisable this account? (yes/no): ").strip().lower()
        if confirm not in ('yes', 'y'):
            print("Cancelled.")
            return False

        try:
            self.auth.update_user(user.user_id, is_active=False, updated_by=admin_user)
            print(f"\n✓ Account disabled: {username}")
            return True
        except Exception as e:
            print(f"\n✗ Failed to disable account: {e}")
            return False

    def enable_account_interactive(self, username: str, admin_user: Optional[User] = None) -> bool:
        """Interactively enable user account.

        Args:
            username: Username
            admin_user: Admin user performing action

        Returns:
            True on success, False otherwise
        """
        user = self.auth.get_user_by_username(username)
        if not user:
            print(f"User not found: {username}")
            return False

        if user.is_active:
            print(f"Account already enabled: {username}")
            return False

        print("\n" + "=" * 60)
        print(f"ENABLE ACCOUNT: {username}")
        print("=" * 60)

        confirm = input("\nEnable this account? (yes/no): ").strip().lower()
        if confirm not in ('yes', 'y'):
            print("Cancelled.")
            return False

        try:
            self.auth.update_user(user.user_id, is_active=True, updated_by=admin_user)
            print(f"\n✓ Account enabled: {username}")
            return True
        except Exception as e:
            print(f"\n✗ Failed to enable account: {e}")
            return False

    def delete_account_interactive(self, username: str, admin_user: Optional[User] = None) -> bool:
        """Interactively delete user account.

        Args:
            username: Username
            admin_user: Admin user performing deletion

        Returns:
            True on success, False otherwise
        """
        user = self.auth.get_user_by_username(username)
        if not user:
            print(f"User not found: {username}")
            return False

        print("\n" + "=" * 60)
        print(f"DELETE ACCOUNT: {username}")
        print("=" * 60)
        print("\nWARNING: This action cannot be undone!")
        print("User data will be permanently deleted.")

        confirm = input("\nType 'DELETE' to confirm: ").strip()
        if confirm != 'DELETE':
            print("Cancelled.")
            return False

        try:
            self.auth.delete_user(user.user_id, admin_user)
            print(f"\n✓ Account deleted: {username}")
            return True
        except Exception as e:
            print(f"\n✗ Failed to delete account: {e}")
            return False

    # --------------------------------------------------------
    # Session Management
    # --------------------------------------------------------

    def list_sessions(self, username: str) -> None:
        """Print active sessions for user.

        Args:
            username: Username
        """
        user = self.auth.get_user_by_username(username)
        if not user:
            print(f"User not found: {username}")
            return

        sessions = self.auth.get_active_sessions(user.user_id)

        if not sessions:
            print(f"\nNo active sessions for: {username}")
            return

        print("\n" + "=" * 100)
        print(f"ACTIVE SESSIONS: {username} ({len(sessions)} session{'s' if len(sessions) != 1 else ''})")
        print("=" * 100)

        # Header
        print(f"{'ID':<8} {'Created':<20} {'Last Activity':<20} {'IP Address':<20} {'Expires':<20}")
        print("-" * 100)

        # Sessions
        for session in sessions:
            session_id = str(session.session_id)
            created = session.created_at.strftime("%Y-%m-%d %H:%M:%S")
            last_activity = session.last_activity.strftime("%Y-%m-%d %H:%M:%S")
            ip_address = session.ip_address or "N/A"
            expires = session.expires_at.strftime("%Y-%m-%d %H:%M:%S")

            print(f"{session_id:<8} {created:<20} {last_activity:<20} {ip_address:<20} {expires:<20}")

    def revoke_sessions_interactive(self, username: str) -> bool:
        """Interactively revoke all sessions for user.

        Args:
            username: Username

        Returns:
            True on success, False otherwise
        """
        user = self.auth.get_user_by_username(username)
        if not user:
            print(f"User not found: {username}")
            return False

        sessions = self.auth.get_active_sessions(user.user_id)
        if not sessions:
            print(f"\nNo active sessions for: {username}")
            return True

        print("\n" + "=" * 60)
        print(f"REVOKE SESSIONS: {username}")
        print("=" * 60)
        print(f"\nActive sessions: {len(sessions)}")

        confirm = input("\nRevoke all sessions? (yes/no): ").strip().lower()
        if confirm not in ('yes', 'y'):
            print("Cancelled.")
            return False

        try:
            count = self.auth.revoke_all_sessions(user.user_id)
            print(f"\n✓ Revoked {count} session{'s' if count != 1 else ''}")
            return True
        except Exception as e:
            print(f"\n✗ Failed to revoke sessions: {e}")
            return False


# ============================================================
# CLI Entry Point
# ============================================================

def main() -> None:
    """CLI for user management testing."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    mgr = UserManager()
    mgr.list_users_formatted()

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
