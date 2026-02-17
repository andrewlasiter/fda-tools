#!/usr/bin/env python3
"""
FDA Tools Enterprise - User Enrollment CLI

Admin script for enrolling new users into the FDA Tools enterprise system.
Creates user accounts, generates enrollment tokens, and optionally sends
notifications.

Usage:
    python3 scripts/enroll_user.py \\
        --email alice@device-corp.com \\
        --name "Alice Johnson" \\
        --role ra_professional \\
        --organization "Acme Medical Devices"

    python3 scripts/enroll_user.py --list
    python3 scripts/enroll_user.py --list --organization org_acme

Author: FDA Tools Development Team
Date: 2026-02-16
Version: 1.0.0
"""

import os
import sys
import argparse
from pathlib import Path

# Add lib directory to path
SCRIPT_DIR = Path(__file__).parent.resolve()
PLUGIN_DIR = SCRIPT_DIR.parent.resolve()
LIB_DIR = PLUGIN_DIR / "lib"
sys.path.insert(0, str(LIB_DIR))

from user_manager import UserManager, VALID_ROLES
from tenant_manager import TenantManager


def create_user(args: argparse.Namespace) -> None:
    """Create a new user account and generate enrollment token."""
    user_mgr = UserManager()
    tenant_mgr = TenantManager()

    # Auto-create organization if it does not exist
    org_id = args.organization.lower().replace(' ', '_').replace('-', '_')
    if not org_id.startswith('org_'):
        org_id = 'org_{}'.format(org_id[:20])

    org = tenant_mgr.get_organization(org_id)
    if org is None:
        print("Creating organization: {}".format(args.organization))
        org = tenant_mgr.create_organization(args.organization)
        print("  Organization ID: {}".format(org.organization_id))
        org_id = org.organization_id

    # Create user
    try:
        user = user_mgr.create_user(
            email=args.email,
            name=args.name,
            role=args.role,
            organization_id=org_id
        )
    except ValueError as e:
        print("ERROR: {}".format(e))
        sys.exit(1)

    print("")
    print("User created successfully:")
    print("  User ID:      {}".format(user.user_id))
    print("  Email:        {}".format(user.email))
    print("  Name:         {}".format(user.name))
    print("  Role:         {}".format(user.role))
    print("  Organization: {}".format(user.organization_id))
    print("  Enrolled:     {}".format(user.enrolled_at))

    # Generate enrollment token
    token = user_mgr.generate_enrollment_token(
        user_id=user.user_id,
        expires_hours=args.token_expiry
    )

    print("")
    print("Enrollment token generated:")
    print("  Token:   {}".format(token))
    print("  Expires: {} hours".format(args.token_expiry))
    print("")
    print("To complete enrollment, the user should:")
    print("  1. Receive the token via secure channel (email/SMS)")
    print("  2. Connect their messaging handle:")
    print('     POST /users/complete-enrollment')
    print('     {{"token": "{}", "messaging_handles": {{"whatsapp": "+1234567890"}}}}'.format(token))
    print("")
    print("Or via messaging platform, send:")
    print('  "enroll {}"'.format(token))


def list_users(args: argparse.Namespace) -> None:
    """List existing users."""
    user_mgr = UserManager()

    org_filter = args.organization if hasattr(args, 'organization') and args.organization else None
    if org_filter and not org_filter.startswith('org_'):
        org_filter = 'org_{}'.format(org_filter.lower().replace(' ', '_')[:20])

    users = user_mgr.list_users(organization_id=org_filter)

    if not users:
        print("No users found.")
        return

    print("{:<15} {:<30} {:<20} {:<18} {:<8}".format(
        "USER ID", "EMAIL", "NAME", "ROLE", "ACTIVE"
    ))
    print("-" * 95)

    for user in users:
        print("{:<15} {:<30} {:<20} {:<18} {:<8}".format(
            user.user_id,
            user.email[:28],
            user.name[:18],
            user.role,
            "Yes" if user.is_active else "No"
        ))

    print("")
    print("Total: {} users".format(len(users)))


def list_organizations(args: argparse.Namespace) -> None:
    """List existing organizations."""
    tenant_mgr = TenantManager()
    orgs = tenant_mgr.list_organizations()

    if not orgs:
        print("No organizations found.")
        return

    print("{:<25} {:<30} {:<8}".format(
        "ORG ID", "NAME", "ACTIVE"
    ))
    print("-" * 65)

    for org in orgs:
        print("{:<25} {:<30} {:<8}".format(
            org.organization_id,
            org.name[:28],
            "Yes" if org.is_active else "No"
        ))

    print("")
    print("Total: {} organizations".format(len(orgs)))


def main():
    parser = argparse.ArgumentParser(
        description="FDA Tools Enterprise - User Enrollment CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Enroll a new RA professional:
    %(prog)s --email alice@corp.com --name "Alice Johnson" \\
             --role ra_professional --organization "Acme Medical"

  Enroll an admin:
    %(prog)s --email admin@corp.com --name "Admin User" \\
             --role admin --organization "Acme Medical"

  List all users:
    %(prog)s --list

  List users in an organization:
    %(prog)s --list --organization org_acme

  List organizations:
    %(prog)s --list-orgs

Valid roles: admin, ra_professional, reviewer, readonly
"""
    )

    # Action group
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        '--list', action='store_true',
        help='List existing users'
    )
    action_group.add_argument(
        '--list-orgs', action='store_true',
        help='List existing organizations'
    )

    # User creation arguments
    parser.add_argument(
        '--email',
        help='User email address'
    )
    parser.add_argument(
        '--name',
        help='User full name'
    )
    parser.add_argument(
        '--role',
        choices=sorted(VALID_ROLES),
        help='User role'
    )
    parser.add_argument(
        '--organization',
        help='Organization name or ID'
    )
    parser.add_argument(
        '--token-expiry',
        type=int,
        default=24,
        help='Enrollment token expiry in hours (default: 24)'
    )

    args = parser.parse_args()

    if args.list:
        list_users(args)
    elif args.list_orgs:
        list_organizations(args)
    elif args.email and args.name and args.role and args.organization:
        create_user(args)
    else:
        if not args.list and not args.list_orgs:
            print("Error: --email, --name, --role, and --organization are required for enrollment.")
            print("Use --list to view existing users, or --help for usage.")
            sys.exit(1)


if __name__ == '__main__':
    main()
