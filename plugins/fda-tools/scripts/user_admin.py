#!/usr/bin/env python3
"""
User Administration CLI Tool (FDA-173 / REG-006).

Command-line interface for managing users in the 21 CFR Part 11
authentication system. Provides comprehensive user lifecycle management
with full audit trail integration.

Features:
  - User creation, deletion, and modification
  - Password management (reset, change policy)
  - Account locking and unlocking
  - Session management and monitoring
  - Audit trail viewing
  - Role assignment and permission display
  - Batch user operations

Usage:
    # Create user
    python3 scripts/user_admin.py create

    # List users
    python3 scripts/user_admin.py list

    # Get user info
    python3 scripts/user_admin.py info jsmith

    # Lock/unlock account
    python3 scripts/user_admin.py lock jsmith
    python3 scripts/user_admin.py unlock jsmith

    # View sessions
    python3 scripts/user_admin.py sessions

    # View audit trail
    python3 scripts/user_admin.py audit --user jsmith --days 7

    # Reset password
    python3 scripts/user_admin.py reset-password jsmith

    # Delete user
    python3 scripts/user_admin.py delete jsmith

Regulatory Compliance:
  - 21 CFR 11.10(e): Audit trail of user management actions
  - 21 CFR 11.300(a): Authorized access limitations
  - 21 CFR 11.50: User authentication and identification

Version: 1.0.0 (FDA-173)
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.auth import AuthManager, Role, User, AuditEventType
from lib.users import UserManager
from lib.rbac import format_permissions, get_role_permissions


# ============================================================
# Command Implementations
# ============================================================

def cmd_create(args):
    """Create new user account interactively."""
    mgr = UserManager()
    user = mgr.create_user_interactive()

    if user:
        print(f"\n✓ User '{user.username}' created successfully")
        print(f"  Email: {user.email}")
        print(f"  Role: {user.role.value}")
        print(f"  Status: {'Active' if user.is_active else 'Inactive'}")
        return 0
    else:
        print("\n✗ User creation cancelled")
        return 1


def cmd_list(args):
    """List all users."""
    auth = AuthManager()
    users = auth.list_users()

    if not users:
        print("No users found")
        return 0

    print(f"\n{'Username':<20} {'Email':<30} {'Role':<10} {'Status':<10} {'Locked':<8}")
    print("=" * 88)

    for user in sorted(users, key=lambda u: u.username):
        status = "Active" if user.is_active else "Inactive"
        locked = "Yes" if user.is_locked else "No"
        print(f"{user.username:<20} {user.email:<30} {user.role.value:<10} {status:<10} {locked:<8}")

    print(f"\nTotal: {len(users)} user(s)")
    return 0


def cmd_info(args):
    """Display detailed user information."""
    auth = AuthManager()
    user = auth.get_user_by_username(args.username)

    if not user:
        print(f"✗ User '{args.username}' not found")
        return 1

    print("\n" + "=" * 60)
    print(f"USER: {user.username}")
    print("=" * 60)
    print(f"Email:           {user.email}")
    print(f"Full Name:       {user.full_name}")
    print(f"Role:            {user.role.value}")
    print(f"Status:          {'Active' if user.is_active else 'Inactive'}")
    print(f"Locked:          {'Yes' if user.is_locked else 'No'}")
    if user.is_locked and user.locked_until:
        locked_until_dt = datetime.fromtimestamp(user.locked_until)
        print(f"Locked Until:    {locked_until_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Failed Attempts: {user.failed_login_attempts}")
    print(f"Created:         {datetime.fromtimestamp(user.created_at).strftime('%Y-%m-%d %H:%M:%S')}")
    if user.last_login:
        last_login_dt = datetime.fromtimestamp(user.last_login)
        print(f"Last Login:      {last_login_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"Last Login:      Never")

    print("\n" + "-" * 60)
    print("PERMISSIONS")
    print("-" * 60)
    print(format_permissions(user))

    return 0


def cmd_delete(args):
    """Delete user account."""
    auth = AuthManager()
    user = auth.get_user_by_username(args.username)

    if not user:
        print(f"✗ User '{args.username}' not found")
        return 1

    # Confirm deletion
    if not args.force:
        print(f"\nWARNING: About to delete user '{args.username}'")
        print(f"  Email: {user.email}")
        print(f"  Role: {user.role.value}")
        confirm = input("\nType username to confirm deletion: ").strip()
        if confirm != args.username:
            print("✗ Deletion cancelled")
            return 1

    success = auth.delete_user(args.username)
    if success:
        print(f"✓ User '{args.username}' deleted")
        return 0
    else:
        print(f"✗ Failed to delete user '{args.username}'")
        return 1


def cmd_lock(args):
    """Lock user account."""
    auth = AuthManager()
    user = auth.get_user_by_username(args.username)

    if not user:
        print(f"✗ User '{args.username}' not found")
        return 1

    if user.is_locked:
        print(f"ℹ User '{args.username}' is already locked")
        return 0

    success = auth.lock_account(args.username)
    if success:
        print(f"✓ User '{args.username}' locked")
        return 0
    else:
        print(f"✗ Failed to lock user '{args.username}'")
        return 1


def cmd_unlock(args):
    """Unlock user account."""
    auth = AuthManager()
    user = auth.get_user_by_username(args.username)

    if not user:
        print(f"✗ User '{args.username}' not found")
        return 1

    if not user.is_locked:
        print(f"ℹ User '{args.username}' is not locked")
        return 0

    success = auth.unlock_account(args.username)
    if success:
        print(f"✓ User '{args.username}' unlocked")
        return 0
    else:
        print(f"✗ Failed to unlock user '{args.username}'")
        return 1


def cmd_sessions(args):
    """List active sessions."""
    auth = AuthManager()
    sessions = auth.list_active_sessions()

    if not sessions:
        print("No active sessions")
        return 0

    print(f"\n{'Username':<20} {'Token (first 16)':<20} {'Created':<20} {'Last Activity':<20}")
    print("=" * 88)

    for session in sorted(sessions, key=lambda s: s.created_at, reverse=True):
        user = auth.get_user_by_id(session.user_id)
        username = user.username if user else f"ID:{session.user_id}"
        created = datetime.fromtimestamp(session.created_at).strftime('%Y-%m-%d %H:%M:%S')
        last_activity = datetime.fromtimestamp(session.last_activity).strftime('%Y-%m-%d %H:%M:%S')
        token_preview = session.token[:16] + "..."

        print(f"{username:<20} {token_preview:<20} {created:<20} {last_activity:<20}")

    print(f"\nTotal: {len(sessions)} active session(s)")
    return 0


def cmd_audit(args):
    """View audit trail."""
    auth = AuthManager()

    # Calculate time range
    if args.days:
        since = int((datetime.now() - timedelta(days=args.days)).timestamp())
    else:
        since = None

    # Get audit events
    events = auth.get_audit_events(
        username=args.user,
        event_type=args.event_type,
        since=since,
        limit=args.limit
    )

    if not events:
        print("No audit events found")
        return 0

    print(f"\n{'Timestamp':<20} {'Username':<20} {'Event Type':<25} {'Details':<40}")
    print("=" * 115)

    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        username = event['username'] or 'N/A'
        event_type = event['event_type']
        details = event['details'][:40] if event['details'] else ''

        print(f"{timestamp:<20} {username:<20} {event_type:<25} {details:<40}")

    print(f"\nTotal: {len(events)} event(s)")
    return 0


def cmd_reset_password(args):
    """Reset user password."""
    mgr = UserManager()
    success = mgr.reset_password_interactive(args.username)

    if success:
        print(f"✓ Password reset for '{args.username}'")
        return 0
    else:
        print(f"✗ Password reset failed")
        return 1


def cmd_change_role(args):
    """Change user role."""
    auth = AuthManager()
    user = auth.get_user_by_username(args.username)

    if not user:
        print(f"✗ User '{args.username}' not found")
        return 1

    # Parse new role
    try:
        new_role = Role(args.role.lower())
    except ValueError:
        print(f"✗ Invalid role '{args.role}'. Valid roles: admin, analyst, viewer")
        return 1

    if user.role == new_role:
        print(f"ℹ User '{args.username}' already has role '{new_role.value}'")
        return 0

    # Confirm role change
    if not args.force:
        print(f"\nChanging role for user '{args.username}':")
        print(f"  Current role: {user.role.value}")
        print(f"  New role:     {new_role.value}")
        confirm = input("\nConfirm role change? (yes/no): ").strip().lower()
        if confirm not in ('yes', 'y'):
            print("✗ Role change cancelled")
            return 1

    success = auth.change_user_role(args.username, new_role)
    if success:
        print(f"✓ Role changed to '{new_role.value}' for user '{args.username}'")
        return 0
    else:
        print(f"✗ Failed to change role")
        return 1


def cmd_permissions(args):
    """Display role permissions."""
    if args.role:
        # Show permissions for specific role
        try:
            role = Role(args.role.lower())
        except ValueError:
            print(f"✗ Invalid role '{args.role}'. Valid roles: admin, analyst, viewer")
            return 1

        perms = get_role_permissions(role)
        print(f"\nPermissions for role '{role.value.upper()}':")
        print("=" * 60)

        # Group by category
        categorized = {}
        for perm in sorted(perms):
            if ':' in perm:
                category, action = perm.split(':', 1)
                if category not in categorized:
                    categorized[category] = []
                categorized[category].append(action)

        for category, actions in sorted(categorized.items()):
            print(f"\n{category.capitalize()}:")
            for action in sorted(actions):
                print(f"  - {action}")
    else:
        # Show all role permissions
        print("\nRole Permissions Summary:")
        print("=" * 60)

        for role in [Role.ADMIN, Role.ANALYST, Role.VIEWER]:
            perms = get_role_permissions(role)
            print(f"\n{role.value.upper()} ({len(perms)} permissions)")

    return 0


# ============================================================
# Main CLI
# ============================================================

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="FDA Tools User Administration (21 CFR Part 11 Compliant)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create user
  %(prog)s create

  # List all users
  %(prog)s list

  # Get user details
  %(prog)s info jsmith

  # Lock/unlock account
  %(prog)s lock jsmith
  %(prog)s unlock jsmith

  # View active sessions
  %(prog)s sessions

  # View audit trail
  %(prog)s audit --user jsmith --days 7

  # Reset password
  %(prog)s reset-password jsmith

  # Change user role
  %(prog)s change-role jsmith --role analyst

  # Delete user
  %(prog)s delete jsmith

  # View role permissions
  %(prog)s permissions --role admin
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Create user
    create_parser = subparsers.add_parser('create', help='Create new user account')

    # List users
    list_parser = subparsers.add_parser('list', help='List all users')

    # User info
    info_parser = subparsers.add_parser('info', help='Display user information')
    info_parser.add_argument('username', help='Username to display')

    # Delete user
    delete_parser = subparsers.add_parser('delete', help='Delete user account')
    delete_parser.add_argument('username', help='Username to delete')
    delete_parser.add_argument('--force', action='store_true', help='Skip confirmation')

    # Lock account
    lock_parser = subparsers.add_parser('lock', help='Lock user account')
    lock_parser.add_argument('username', help='Username to lock')

    # Unlock account
    unlock_parser = subparsers.add_parser('unlock', help='Unlock user account')
    unlock_parser.add_argument('username', help='Username to unlock')

    # List sessions
    sessions_parser = subparsers.add_parser('sessions', help='List active sessions')

    # Audit trail
    audit_parser = subparsers.add_parser('audit', help='View audit trail')
    audit_parser.add_argument('--user', help='Filter by username')
    audit_parser.add_argument('--event-type', help='Filter by event type')
    audit_parser.add_argument('--days', type=int, help='Show events from last N days')
    audit_parser.add_argument('--limit', type=int, default=100, help='Maximum events to show (default: 100)')

    # Reset password
    reset_parser = subparsers.add_parser('reset-password', help='Reset user password')
    reset_parser.add_argument('username', help='Username to reset password')

    # Change role
    role_parser = subparsers.add_parser('change-role', help='Change user role')
    role_parser.add_argument('username', help='Username to modify')
    role_parser.add_argument('--role', required=True, choices=['admin', 'analyst', 'viewer'], help='New role')
    role_parser.add_argument('--force', action='store_true', help='Skip confirmation')

    # Permissions
    perms_parser = subparsers.add_parser('permissions', help='Display role permissions')
    perms_parser.add_argument('--role', choices=['admin', 'analyst', 'viewer'], help='Show permissions for specific role')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to command handler
    command_handlers = {
        'create': cmd_create,
        'list': cmd_list,
        'info': cmd_info,
        'delete': cmd_delete,
        'lock': cmd_lock,
        'unlock': cmd_unlock,
        'sessions': cmd_sessions,
        'audit': cmd_audit,
        'reset-password': cmd_reset_password,
        'change-role': cmd_change_role,
        'permissions': cmd_permissions,
    }

    handler = command_handlers.get(args.command)
    if handler:
        try:
            return handler(args)
        except Exception as e:
            print(f"✗ Error: {e}")
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
