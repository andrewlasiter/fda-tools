#!/usr/bin/env python3
"""
FDA Tools Authentication CLI (FDA-185 / REG-006).

Command-line interface for 21 CFR Part 11 compliant user authentication
and access control management.

Commands:
  - login              Authenticate user
  - logout             End session
  - create-user        Create new user account
  - list-users         List all users
  - user-info          Show user information
  - change-password    Change your password
  - reset-password     Reset user password (admin)
  - lock-account       Lock user account (admin)
  - unlock-account     Unlock user account (admin)
  - disable-account    Disable user account (admin)
  - enable-account     Enable user account (admin)
  - delete-account     Delete user account (admin)
  - list-sessions      List active sessions
  - revoke-sessions    Revoke user sessions
  - audit-log          View audit log

Usage:
    python3 scripts/auth_cli.py login
    python3 scripts/auth_cli.py create-user
    python3 scripts/auth_cli.py list-users
    python3 scripts/auth_cli.py user-info jsmith

Version: 1.0.0 (FDA-185)
"""

import argparse
import getpass
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add lib to path
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.resolve()
LIB_DIR = PROJECT_ROOT / "lib"
sys.path.insert(0, str(LIB_DIR))

from auth import AuthManager, Role, AuditEventType, Session, User
from users import UserManager

logger = logging.getLogger(__name__)

# Session token storage
SESSION_TOKEN_FILE = Path.home() / '.fda-tools' / '.session_token'


# ============================================================
# Session Token Storage
# ============================================================

def save_session_token(token: str):
    """Save session token to file.

    Args:
        token: Session token
    """
    SESSION_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_TOKEN_FILE.write_text(token)
    SESSION_TOKEN_FILE.chmod(0o600)


def load_session_token() -> Optional[str]:
    """Load session token from file.

    Returns:
        Session token or None if not found
    """
    if not SESSION_TOKEN_FILE.exists():
        return None
    return SESSION_TOKEN_FILE.read_text().strip()


def delete_session_token():
    """Delete saved session token."""
    if SESSION_TOKEN_FILE.exists():
        SESSION_TOKEN_FILE.unlink()


def get_current_user(auth: AuthManager) -> Optional[User]:
    """Get currently authenticated user.

    Args:
        auth: AuthManager instance

    Returns:
        User object or None if not authenticated
    """
    token = load_session_token()
    if not token:
        return None

    user = auth.validate_session(token)
    if not user:
        # Session expired, clean up
        delete_session_token()
        return None

    return user


# ============================================================
# Commands
# ============================================================

def cmd_login(args, auth: AuthManager, user_mgr: UserManager):
    """Login command."""
    print("\n" + "=" * 60)
    print("FDA TOOLS LOGIN")
    print("=" * 60)

    # Check if already logged in
    current_user = get_current_user(auth)
    if current_user:
        print(f"\nAlready logged in as: {current_user.username}")
        print(f"Role: {current_user.role.value}")
        choice = input("\nLogout and login as different user? (yes/no): ").strip().lower()
        if choice not in ('yes', 'y'):
            return 0
        # Logout
        token = load_session_token()
        auth.logout(token)
        delete_session_token()
        print("Logged out.\n")

    # Get credentials
    username = input("Username: ").strip()
    if not username:
        print("Cancelled.")
        return 1

    password = getpass.getpass("Password: ")
    if not password:
        print("Cancelled.")
        return 1

    # Login
    session = auth.login(username, password)
    if not session:
        print("\n✗ Login failed. Check your username and password.")
        return 1

    # Save session token
    save_session_token(session.token)

    user = auth.get_user_by_id(session.user_id)
    print(f"\n✓ Login successful")
    print(f"Welcome, {user.full_name}!")
    print(f"Role: {user.role.value}")

    if user.last_login:
        print(f"Last login: {user.last_login.strftime('%Y-%m-%d %H:%M:%S')}")

    return 0


def cmd_logout(args, auth: AuthManager, user_mgr: UserManager):
    """Logout command."""
    token = load_session_token()
    if not token:
        print("Not logged in.")
        return 0

    auth.logout(token)
    delete_session_token()

    print("✓ Logged out successfully")
    return 0


def cmd_create_user(args, auth: AuthManager, user_mgr: UserManager):
    """Create user command."""
    # Check if logged in as admin
    current_user = get_current_user(auth)
    if not current_user:
        print("✗ You must be logged in to create users.")
        print("Run: fda-auth login")
        return 1

    if current_user.role != Role.ADMIN:
        print("✗ Only administrators can create users.")
        return 1

    # Create user interactively
    user = user_mgr.create_user_interactive(created_by=current_user)
    return 0 if user else 1


def cmd_list_users(args, auth: AuthManager, user_mgr: UserManager):
    """List users command."""
    # Parse filters
    role = None
    if args.role:
        try:
            role = Role(args.role.lower())
        except ValueError:
            print(f"✗ Invalid role: {args.role}")
            print(f"Valid roles: {', '.join([r.value for r in Role])}")
            return 1

    active_only = args.active

    # List users
    if args.json:
        users = user_mgr.list_users_json(role=role, active_only=active_only)
        print(json.dumps(users, indent=2))
    else:
        user_mgr.list_users_formatted(role=role, active_only=active_only)

    return 0


def cmd_user_info(args, auth: AuthManager, user_mgr: UserManager):
    """User info command."""
    username = args.username

    if args.json:
        info = user_mgr.get_user_info(username)
        if not info:
            print(json.dumps({'error': 'User not found'}, indent=2))
            return 1
        print(json.dumps(info, indent=2))
    else:
        user_mgr.print_user_info(username)

    return 0


def cmd_change_password(args, auth: AuthManager, user_mgr: UserManager):
    """Change password command."""
    current_user = get_current_user(auth)
    if not current_user:
        print("✗ You must be logged in to change your password.")
        print("Run: fda-auth login")
        return 1

    success = user_mgr.change_password_interactive(current_user.username)
    return 0 if success else 1


def cmd_reset_password(args, auth: AuthManager, user_mgr: UserManager):
    """Reset password command (admin)."""
    current_user = get_current_user(auth)
    if not current_user:
        print("✗ You must be logged in to reset passwords.")
        print("Run: fda-auth login")
        return 1

    if current_user.role != Role.ADMIN:
        print("✗ Only administrators can reset passwords.")
        return 1

    username = args.username
    success = user_mgr.reset_password_interactive(username, admin_user=current_user)
    return 0 if success else 1


def cmd_lock_account(args, auth: AuthManager, user_mgr: UserManager):
    """Lock account command (admin)."""
    current_user = get_current_user(auth)
    if not current_user:
        print("✗ You must be logged in to lock accounts.")
        print("Run: fda-auth login")
        return 1

    if current_user.role != Role.ADMIN:
        print("✗ Only administrators can lock accounts.")
        return 1

    username = args.username
    success = user_mgr.lock_account_interactive(username)
    return 0 if success else 1


def cmd_unlock_account(args, auth: AuthManager, user_mgr: UserManager):
    """Unlock account command (admin)."""
    current_user = get_current_user(auth)
    if not current_user:
        print("✗ You must be logged in to unlock accounts.")
        print("Run: fda-auth login")
        return 1

    if current_user.role != Role.ADMIN:
        print("✗ Only administrators can unlock accounts.")
        return 1

    username = args.username
    success = user_mgr.unlock_account_interactive(username)
    return 0 if success else 1


def cmd_disable_account(args, auth: AuthManager, user_mgr: UserManager):
    """Disable account command (admin)."""
    current_user = get_current_user(auth)
    if not current_user:
        print("✗ You must be logged in to disable accounts.")
        print("Run: fda-auth login")
        return 1

    if current_user.role != Role.ADMIN:
        print("✗ Only administrators can disable accounts.")
        return 1

    username = args.username
    success = user_mgr.disable_account_interactive(username, admin_user=current_user)
    return 0 if success else 1


def cmd_enable_account(args, auth: AuthManager, user_mgr: UserManager):
    """Enable account command (admin)."""
    current_user = get_current_user(auth)
    if not current_user:
        print("✗ You must be logged in to enable accounts.")
        print("Run: fda-auth login")
        return 1

    if current_user.role != Role.ADMIN:
        print("✗ Only administrators can enable accounts.")
        return 1

    username = args.username
    success = user_mgr.enable_account_interactive(username, admin_user=current_user)
    return 0 if success else 1


def cmd_delete_account(args, auth: AuthManager, user_mgr: UserManager):
    """Delete account command (admin)."""
    current_user = get_current_user(auth)
    if not current_user:
        print("✗ You must be logged in to delete accounts.")
        print("Run: fda-auth login")
        return 1

    if current_user.role != Role.ADMIN:
        print("✗ Only administrators can delete accounts.")
        return 1

    username = args.username

    # Prevent self-deletion
    if username == current_user.username:
        print("✗ You cannot delete your own account.")
        return 1

    success = user_mgr.delete_account_interactive(username, admin_user=current_user)
    return 0 if success else 1


def cmd_list_sessions(args, auth: AuthManager, user_mgr: UserManager):
    """List sessions command."""
    username = args.username

    # If no username specified, show current user's sessions
    if not username:
        current_user = get_current_user(auth)
        if not current_user:
            print("✗ You must be logged in or specify a username.")
            print("Run: fda-auth login")
            return 1
        username = current_user.username
    else:
        # Check permission to view other users' sessions
        current_user = get_current_user(auth)
        if not current_user:
            print("✗ You must be logged in to view sessions.")
            print("Run: fda-auth login")
            return 1
        if current_user.role != Role.ADMIN and current_user.username != username:
            print("✗ You can only view your own sessions.")
            return 1

    user_mgr.list_sessions(username)
    return 0


def cmd_revoke_sessions(args, auth: AuthManager, user_mgr: UserManager):
    """Revoke sessions command."""
    username = args.username

    # If no username specified, revoke current user's sessions
    if not username:
        current_user = get_current_user(auth)
        if not current_user:
            print("✗ You must be logged in or specify a username.")
            print("Run: fda-auth login")
            return 1
        username = current_user.username
    else:
        # Check permission to revoke other users' sessions
        current_user = get_current_user(auth)
        if not current_user:
            print("✗ You must be logged in to revoke sessions.")
            print("Run: fda-auth login")
            return 1
        if current_user.role != Role.ADMIN and current_user.username != username:
            print("✗ You can only revoke your own sessions.")
            return 1

    success = user_mgr.revoke_sessions_interactive(username)

    # If revoking own sessions, logout
    if success and username == current_user.username:
        delete_session_token()
        print("\nYou have been logged out.")

    return 0 if success else 1


def cmd_audit_log(args, auth: AuthManager, user_mgr: UserManager):
    """Audit log command."""
    # Check if logged in as admin
    current_user = get_current_user(auth)
    if not current_user:
        print("✗ You must be logged in to view audit logs.")
        print("Run: fda-auth login")
        return 1

    if current_user.role != Role.ADMIN:
        print("✗ Only administrators can view audit logs.")
        return 1

    # Parse filters
    user_id = None
    if args.username:
        user = auth.get_user_by_username(args.username)
        if not user:
            print(f"✗ User not found: {args.username}")
            return 1
        user_id = user.user_id

    event_type = None
    if args.event_type:
        try:
            event_type = AuditEventType(args.event_type)
        except ValueError:
            print(f"✗ Invalid event type: {args.event_type}")
            print(f"Valid types: {', '.join([e.value for e in AuditEventType])}")
            return 1

    start_date = None
    if args.start_date:
        try:
            start_date = datetime.fromisoformat(args.start_date)
        except ValueError:
            print(f"✗ Invalid start date: {args.start_date}")
            print("Format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
            return 1

    end_date = None
    if args.end_date:
        try:
            end_date = datetime.fromisoformat(args.end_date)
        except ValueError:
            print(f"✗ Invalid end date: {args.end_date}")
            print("Format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
            return 1

    limit = args.limit or 100

    # Get audit events
    events = auth.get_audit_events(
        user_id=user_id,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )

    if not events:
        print("\nNo audit events found.")
        return 0

    if args.json:
        events_json = [
            {
                'event_id': e.event_id,
                'event_type': e.event_type.value,
                'user_id': e.user_id,
                'username': e.username,
                'timestamp': e.timestamp.isoformat(),
                'details': e.details,
                'ip_address': e.ip_address,
                'success': e.success,
            }
            for e in events
        ]
        print(json.dumps(events_json, indent=2))
    else:
        print("\n" + "=" * 120)
        print(f"AUDIT LOG ({len(events)} event{'s' if len(events) != 1 else ''})")
        print("=" * 120)

        # Header
        print(f"{'ID':<8} {'Timestamp':<20} {'Event Type':<20} {'Username':<20} {'Status':<8} {'Details':<40}")
        print("-" * 120)

        # Events
        for event in events:
            event_id = str(event.event_id)
            timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            event_type_str = event.event_type.value[:19]
            username = event.username[:19]
            status = "✓" if event.success else "✗"
            details = json.dumps(event.details)[:39] if event.details else ""

            print(f"{event_id:<8} {timestamp:<20} {event_type_str:<20} {username:<20} {status:<8} {details:<40}")

    return 0


def cmd_whoami(args, auth: AuthManager, user_mgr: UserManager):
    """Show current user."""
    current_user = get_current_user(auth)
    if not current_user:
        print("Not logged in.")
        print("Run: fda-auth login")
        return 1

    print(f"\nLogged in as: {current_user.username}")
    print(f"Full name: {current_user.full_name}")
    print(f"Role: {current_user.role.value}")
    print(f"Email: {current_user.email}")

    # Active sessions
    sessions = auth.get_active_sessions(current_user.user_id)
    print(f"\nActive sessions: {len(sessions)}")

    return 0


# ============================================================
# Main CLI
# ============================================================

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="FDA Tools Authentication CLI (21 CFR Part 11)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Login
  fda-auth login

  # Create user (admin only)
  fda-auth create-user

  # List users
  fda-auth list-users
  fda-auth list-users --role admin
  fda-auth list-users --active

  # User information
  fda-auth user-info jsmith
  fda-auth whoami

  # Password management
  fda-auth change-password
  fda-auth reset-password jsmith  # Admin only

  # Account management (admin only)
  fda-auth lock-account jsmith
  fda-auth unlock-account jsmith
  fda-auth disable-account jsmith
  fda-auth enable-account jsmith
  fda-auth delete-account jsmith

  # Session management
  fda-auth list-sessions
  fda-auth list-sessions jsmith  # Admin only
  fda-auth revoke-sessions
  fda-auth revoke-sessions jsmith  # Admin only

  # Audit log (admin only)
  fda-auth audit-log
  fda-auth audit-log --username jsmith
  fda-auth audit-log --event-type login_success
  fda-auth audit-log --start-date 2026-02-01 --limit 50

  # Logout
  fda-auth logout
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Login
    parser_login = subparsers.add_parser('login', help='Authenticate user')

    # Logout
    parser_logout = subparsers.add_parser('logout', help='End session')

    # Create user
    parser_create_user = subparsers.add_parser('create-user', help='Create new user account (admin only)')

    # List users
    parser_list_users = subparsers.add_parser('list-users', help='List all users')
    parser_list_users.add_argument('--role', help='Filter by role (admin, analyst, viewer)')
    parser_list_users.add_argument('--active', action='store_true', help='Show only active users')
    parser_list_users.add_argument('--json', action='store_true', help='Output as JSON')

    # User info
    parser_user_info = subparsers.add_parser('user-info', help='Show user information')
    parser_user_info.add_argument('username', help='Username')
    parser_user_info.add_argument('--json', action='store_true', help='Output as JSON')

    # Change password
    parser_change_password = subparsers.add_parser('change-password', help='Change your password')

    # Reset password
    parser_reset_password = subparsers.add_parser('reset-password', help='Reset user password (admin only)')
    parser_reset_password.add_argument('username', help='Username')

    # Lock account
    parser_lock_account = subparsers.add_parser('lock-account', help='Lock user account (admin only)')
    parser_lock_account.add_argument('username', help='Username')

    # Unlock account
    parser_unlock_account = subparsers.add_parser('unlock-account', help='Unlock user account (admin only)')
    parser_unlock_account.add_argument('username', help='Username')

    # Disable account
    parser_disable_account = subparsers.add_parser('disable-account', help='Disable user account (admin only)')
    parser_disable_account.add_argument('username', help='Username')

    # Enable account
    parser_enable_account = subparsers.add_parser('enable-account', help='Enable user account (admin only)')
    parser_enable_account.add_argument('username', help='Username')

    # Delete account
    parser_delete_account = subparsers.add_parser('delete-account', help='Delete user account (admin only)')
    parser_delete_account.add_argument('username', help='Username')

    # List sessions
    parser_list_sessions = subparsers.add_parser('list-sessions', help='List active sessions')
    parser_list_sessions.add_argument('username', nargs='?', help='Username (defaults to current user)')

    # Revoke sessions
    parser_revoke_sessions = subparsers.add_parser('revoke-sessions', help='Revoke user sessions')
    parser_revoke_sessions.add_argument('username', nargs='?', help='Username (defaults to current user)')

    # Audit log
    parser_audit_log = subparsers.add_parser('audit-log', help='View audit log (admin only)')
    parser_audit_log.add_argument('--username', help='Filter by username')
    parser_audit_log.add_argument('--event-type', help='Filter by event type')
    parser_audit_log.add_argument('--start-date', help='Filter by start date (YYYY-MM-DD)')
    parser_audit_log.add_argument('--end-date', help='Filter by end date (YYYY-MM-DD)')
    parser_audit_log.add_argument('--limit', type=int, help='Maximum events to show (default: 100)')
    parser_audit_log.add_argument('--json', action='store_true', help='Output as JSON')

    # Whoami
    parser_whoami = subparsers.add_parser('whoami', help='Show current user')

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    # Initialize managers
    auth = AuthManager()
    user_mgr = UserManager()

    # Command routing
    commands = {
        'login': cmd_login,
        'logout': cmd_logout,
        'create-user': cmd_create_user,
        'list-users': cmd_list_users,
        'user-info': cmd_user_info,
        'change-password': cmd_change_password,
        'reset-password': cmd_reset_password,
        'lock-account': cmd_lock_account,
        'unlock-account': cmd_unlock_account,
        'disable-account': cmd_disable_account,
        'enable-account': cmd_enable_account,
        'delete-account': cmd_delete_account,
        'list-sessions': cmd_list_sessions,
        'revoke-sessions': cmd_revoke_sessions,
        'audit-log': cmd_audit_log,
        'whoami': cmd_whoami,
    }

    if not args.command:
        parser.print_help()
        return 0

    command_func = commands.get(args.command)
    if not command_func:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        return 1

    try:
        return command_func(args, auth, user_mgr)
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        return 130
    except Exception as e:
        logger.exception("Command failed")
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
