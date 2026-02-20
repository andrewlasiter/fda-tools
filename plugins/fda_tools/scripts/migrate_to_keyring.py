#!/usr/bin/env python3
"""
Migrate API Keys to Secure Keyring Storage

This script helps migrate API keys from plaintext storage (environment variables
or settings files) to secure OS keyring storage.

Security Benefits (FDA-182 / SEC-003):
  - No plaintext API keys in files or .env
  - Encrypted storage using OS keyring
  - Automatic cleanup of plaintext after migration
  - Cross-platform support (macOS, Windows, Linux)

Migration Sources:
  1. Environment variables (LINEAR_API_KEY, OPENFDA_API_KEY, etc.)
  2. Legacy settings file (~/.claude/fda-tools.local.md)
  3. .env files (if present)

Supported API Keys:
  - OPENFDA_API_KEY: openFDA API access
  - LINEAR_API_KEY: Linear issue management
  - BRIDGE_API_KEY: OpenClaw bridge server
  - GEMINI_API_KEY: Google Gemini AI API

Usage:
    # Interactive mode (recommended)
    python3 scripts/migrate_to_keyring.py

    # Auto-migrate all keys from environment
    python3 scripts/migrate_to_keyring.py --auto

    # Migrate specific key
    python3 scripts/migrate_to_keyring.py --key openfda

    # Check migration status
    python3 scripts/migrate_to_keyring.py --status

    # Rollback (export keys to .env.backup)
    python3 scripts/migrate_to_keyring.py --rollback

Version: 1.0.0 (FDA-182)
"""

import os
import sys
from pathlib import Path

# Add lib directory to path
_lib_dir = Path(__file__).parent.parent / 'lib'
if str(_lib_dir) not in sys.path:

try:
    from secure_config import SecureConfig, KEYRING_ACCOUNTS, ENV_VAR_NAMES, mask_api_key
except ImportError:
    print("ERROR: secure_config module not found")
    print(f"Expected location: {_lib_dir / 'secure_config.py'}")
    sys.exit(1)


def print_header(title):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_status(config: SecureConfig):
    """Print current migration status."""
    print_header("MIGRATION STATUS")

    status = config.get_all_keys_status()

    # Summary
    total_keys = len(KEYRING_ACCOUNTS)
    keys_in_keyring = sum(1 for s in status.values() if s['keyring_set'])
    keys_in_env = sum(1 for s in status.values() if s['env_var_set'])
    keys_in_plaintext = sum(1 for s in status.values() if s['plaintext_set'])

    print(f"\nKeyring available: {'YES' if config.keyring_available else 'NO'}")
    print(f"Total supported keys: {total_keys}")
    print(f"Keys in keyring: {keys_in_keyring}")
    print(f"Keys in environment: {keys_in_env}")
    print(f"Keys in plaintext files: {keys_in_plaintext}")

    # Detailed status
    print("\nDETAILED STATUS:")
    for key_type, info in sorted(status.items()):
        print(f"\n  {key_type.upper()}:")
        print(f"    Environment ({info['env_var_name']}): {'SET' if info['env_var_set'] else 'not set'}")
        print(f"    Keyring: {'SET ✓' if info['keyring_set'] else 'not set'}")
        print(f"    Plaintext file: {'SET (⚠ migrate!)' if info['plaintext_set'] else 'not set'}")
        if info['active_source']:
            print(f"    Active source: {info['active_source']}")
            if info['masked_value']:
                print(f"    Value: {info['masked_value']}")

    # Migration recommendations
    print("\nRECOMMENDATIONS:")
    needs_migration = []

    for key_type, info in status.items():
        if info['env_var_set'] and not info['keyring_set']:
            needs_migration.append(f"  - Migrate {key_type.upper()} from environment to keyring")
        elif info['plaintext_set'] and not info['keyring_set']:
            needs_migration.append(f"  - Migrate {key_type.upper()} from plaintext to keyring")

    if needs_migration:
        for rec in needs_migration:
            print(rec)
        print(f"\n  Run: python3 scripts/migrate_to_keyring.py --auto")
    else:
        print("  ✓ All keys are already in keyring or not configured")


def migrate_key_interactive(config: SecureConfig, key_type: str) -> bool:
    """Interactively migrate a single key.

    Args:
        config: SecureConfig instance
        key_type: Key type to migrate

    Returns:
        True if migrated, False otherwise
    """
    status = config.get_key_status(key_type)

    print(f"\nMigrating {key_type.upper()} API key:")
    print(f"  Environment: {'SET' if status['env_var_set'] else 'not set'}")
    print(f"  Keyring: {'SET' if status['keyring_set'] else 'not set'}")
    print(f"  Plaintext: {'SET' if status['plaintext_set'] else 'not set'}")

    if status['keyring_set']:
        print(f"  ✓ Already in keyring, skipping")
        return True

    if not status['env_var_set'] and not status['plaintext_set']:
        print(f"  - No key found to migrate")
        return False

    # Confirm migration
    source = 'environment' if status['env_var_set'] else 'plaintext file'
    print(f"\n  Found key in {source}: {status['masked_value']}")

    response = input(f"  Migrate to keyring? (y/N): ").strip().lower()
    if response != 'y':
        print("  Skipped")
        return False

    # Migrate
    success, message = config.migrate_key(key_type)
    if success:
        print(f"  ✓ {message}")
        return True
    else:
        print(f"  ✗ {message}")
        return False


def migrate_all_auto(config: SecureConfig) -> dict:
    """Automatically migrate all keys from environment/plaintext to keyring.

    Args:
        config: SecureConfig instance

    Returns:
        Dictionary with migration results
    """
    print_header("AUTO-MIGRATION")

    if not config.keyring_available:
        print("\nERROR: Keyring not available on this system")
        print("Install keyring support:")
        print("  Linux: sudo apt install gnome-keyring")
        print("  macOS: Built-in (Keychain)")
        print("  Windows: Built-in (Credential Locker)")
        return {'migrated': 0, 'skipped': 0, 'failed': 0}

    results = {'migrated': 0, 'skipped': 0, 'failed': 0}

    for key_type in KEYRING_ACCOUNTS.keys():
        status = config.get_key_status(key_type)

        if status['keyring_set']:
            print(f"  {key_type.upper()}: Already in keyring, skipping")
            results['skipped'] += 1
            continue

        if not status['env_var_set'] and not status['plaintext_set']:
            print(f"  {key_type.upper()}: No key found, skipping")
            results['skipped'] += 1
            continue

        # Migrate
        source = 'environment' if status['env_var_set'] else 'plaintext file'
        success, message = config.migrate_key(key_type)

        if success:
            print(f"  {key_type.upper()}: ✓ Migrated from {source}")
            results['migrated'] += 1
        else:
            print(f"  {key_type.upper()}: ✗ Failed - {message}")
            results['failed'] += 1

    return results


def rollback_to_env(config: SecureConfig):
    """Export all keys from keyring to .env.backup file.

    This provides a rollback mechanism if keyring is causing issues.

    Args:
        config: SecureConfig instance
    """
    print_header("ROLLBACK TO ENVIRONMENT FILE")

    backup_file = Path.cwd() / '.env.backup'

    if backup_file.exists():
        response = input(f"\n{backup_file} already exists. Overwrite? (y/N): ").strip().lower()
        if response != 'y':
            print("Cancelled")
            return

    lines = [
        "# FDA Tools API Keys - Exported from Keyring",
        "# Generated by migrate_to_keyring.py --rollback",
        "# WARNING: This file contains plaintext API keys. Keep secure!",
        "#",
        "# To use:",
        "#   source .env.backup",
        "#   export LINEAR_API_KEY OPENFDA_API_KEY GEMINI_API_KEY BRIDGE_API_KEY",
        "",
    ]

    exported = 0

    for key_type in KEYRING_ACCOUNTS.keys():
        api_key = config.get_api_key(key_type)
        if api_key:
            env_var = ENV_VAR_NAMES.get(key_type)
            lines.append(f"{env_var}={api_key}")
            print(f"  ✓ Exported {key_type.upper()}")
            exported += 1

    if exported == 0:
        print("\nNo keys found in keyring to export")
        return

    backup_file.write_text('\n'.join(lines) + '\n')

    # Restrict permissions
    backup_file.chmod(0o600)

    print(f"\n✓ Exported {exported} keys to {backup_file}")
    print(f"\nWARNING: {backup_file} contains plaintext API keys")
    print("Keep this file secure and delete it when no longer needed")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate API Keys to Secure Keyring Storage (FDA-182)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--status', action='store_true', help='Show migration status')
    parser.add_argument('--auto', action='store_true', help='Auto-migrate all keys')
    parser.add_argument('--key', choices=list(KEYRING_ACCOUNTS.keys()),
                       help='Migrate specific key (interactive)')
    parser.add_argument('--rollback', action='store_true',
                       help='Export keys from keyring to .env.backup')

    args = parser.parse_args()

    print_header("FDA TOOLS - API KEY MIGRATION TO KEYRING")
    print("\nSecurity upgrade: FDA-182 / SEC-003")
    print("Migrating from plaintext to OS keyring storage")

    config = SecureConfig()

    if args.status:
        print_status(config)

    elif args.auto:
        results = migrate_all_auto(config)
        print(f"\n{'=' * 70}")
        print(f"MIGRATION COMPLETE")
        print(f"{'=' * 70}")
        print(f"  Migrated: {results['migrated']}")
        print(f"  Skipped:  {results['skipped']}")
        print(f"  Failed:   {results['failed']}")

        if results['migrated'] > 0:
            print(f"\n✓ {results['migrated']} keys migrated to secure keyring storage")
            print("\nNext steps:")
            print("1. Test your applications to ensure they can access keys")
            print("2. Remove API keys from environment variables (unset)")
            print("3. Delete any .env files containing API keys")
            print(f"\nTo rollback: python3 scripts/migrate_to_keyring.py --rollback")

    elif args.key:
        if migrate_key_interactive(config, args.key):
            print(f"\n✓ Migration complete")
            print(f"\nTo verify: python3 scripts/migrate_to_keyring.py --status")
        else:
            print(f"\n✗ Migration failed or skipped")

    elif args.rollback:
        rollback_to_env(config)

    else:
        # Interactive mode
        print("\nInteractive migration mode")
        print_status(config)

        print(f"\n{'=' * 70}")
        print("MIGRATION OPTIONS")
        print(f"{'=' * 70}")
        print("1. Auto-migrate all keys")
        print("2. Migrate specific key")
        print("3. Show status only")
        print("4. Rollback (export to .env.backup)")
        print("5. Exit")

        choice = input("\nSelect option (1-5): ").strip()

        if choice == '1':
            results = migrate_all_auto(config)
            print(f"\n✓ Migrated {results['migrated']} keys")

        elif choice == '2':
            print("\nAvailable keys:")
            for i, key_type in enumerate(KEYRING_ACCOUNTS.keys(), 1):
                print(f"  {i}. {key_type.upper()}")

            key_num = input("\nSelect key (1-4): ").strip()
            try:
                key_type = list(KEYRING_ACCOUNTS.keys())[int(key_num) - 1]
                migrate_key_interactive(config, key_type)
            except (ValueError, IndexError):
                print("Invalid selection")

        elif choice == '3':
            pass  # Already showed status

        elif choice == '4':
            rollback_to_env(config)

        elif choice == '5':
            print("Exiting")
            return 0

        else:
            print("Invalid choice")

    return 0


if __name__ == '__main__':
    sys.exit(main())
