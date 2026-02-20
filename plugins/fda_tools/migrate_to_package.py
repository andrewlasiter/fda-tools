#!/usr/bin/env python3
"""
Migration script to convert codebase to proper Python package.
Eliminates sys.path manipulation by using proper package imports.

This script:
1. Removes sys.path.insert/append statements
2. Converts `from lib.x import Y` to `from fda_tools.lib.x import Y`
3. Converts `from scripts.x import Y` to `from fda_tools.scripts.x import Y`
4. Updates test imports to use package-based imports
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Patterns to match and replace
PATTERNS = [
    # Remove sys.path manipulation
    (
        r'^sys\.path\.insert\(0,\s*.*?\)\s*$',
        '',
        'Remove sys.path.insert()'
    ),
    (
        r'^sys\.path\.append\(.*?\)\s*$',
        '',
        'Remove sys.path.append()'
    ),

    # Update lib imports
    (
        r'^from lib\.([a-z_]+) import (.+)$',
        r'from fda_tools.lib.\1 import \2',
        'Update lib imports'
    ),
    (
        r'^import lib\.([a-z_]+)$',
        r'import fda_tools.lib.\1',
        'Update lib module imports'
    ),

    # Update scripts imports
    (
        r'^from scripts\.([a-z_]+) import (.+)$',
        r'from fda_tools.scripts.\1 import \2',
        'Update scripts imports'
    ),
    (
        r'^import scripts\.([a-z_]+)$',
        r'import fda_tools.scripts.\1',
        'Update scripts module imports'
    ),
]


def process_file(file_path: Path) -> Tuple[int, List[str]]:
    """
    Process a single file to update imports.

    Returns:
        (changes_count, change_descriptions)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0, []

    changes = []
    new_lines = []
    file_changed = False

    for line in lines:
        original_line = line
        line_changed = False

        for pattern, replacement, description in PATTERNS:
            match = re.match(pattern, line.strip(), re.MULTILINE)
            if match:
                # If replacement is empty, skip the line (remove it)
                if replacement == '':
                    file_changed = True
                    line_changed = True
                    if description not in changes:
                        changes.append(description)
                    line = ''  # Remove the line
                    break
                else:
                    new_line = re.sub(pattern, replacement, line.strip(), flags=re.MULTILINE) + '\n'
                    if new_line != line:
                        line = new_line
                        file_changed = True
                        line_changed = True
                        if description not in changes:
                            changes.append(description)
                        break

        # Only add non-empty lines (skip removed sys.path lines)
        if line.strip() or not line_changed:
            new_lines.append(line)

    # Write back if changed
    if file_changed:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return 0, []

    return len(changes), changes


def main():
    """Main migration function."""
    base_dir = Path(__file__).parent

    # Find all Python files (excluding this script and __pycache__)
    python_files = []
    for pattern in ['**/*.py']:
        for file_path in base_dir.glob(pattern):
            # Skip this migration script, __pycache__, and .pytest_cache
            if (
                file_path.name == 'migrate_to_package.py' or
                '__pycache__' in str(file_path) or
                '.pytest_cache' in str(file_path) or
                'venv' in str(file_path) or
                '.venv' in str(file_path)
            ):
                continue
            python_files.append(file_path)

    print(f"Found {len(python_files)} Python files to process")
    print("=" * 80)

    total_files_changed = 0
    total_changes = 0
    files_with_changes = []

    for file_path in sorted(python_files):
        changes_count, changes = process_file(file_path)

        if changes_count > 0:
            total_files_changed += 1
            total_changes += changes_count
            rel_path = file_path.relative_to(base_dir)
            files_with_changes.append((rel_path, changes))
            print(f"✓ {rel_path}: {', '.join(changes)}")

    print("=" * 80)
    print(f"\nSummary:")
    print(f"  Files processed: {len(python_files)}")
    print(f"  Files changed: {total_files_changed}")
    print(f"  Total changes: {total_changes}")

    if files_with_changes:
        print(f"\nChanged files by category:")

        test_files = [f for f, _ in files_with_changes if 'tests/' in str(f)]
        lib_files = [f for f, _ in files_with_changes if 'lib/' in str(f)]
        script_files = [f for f, _ in files_with_changes if 'scripts/' in str(f)]
        other_files = [f for f, _ in files_with_changes if f not in test_files + lib_files + script_files]

        if test_files:
            print(f"  Tests: {len(test_files)} files")
        if lib_files:
            print(f"  Library: {len(lib_files)} files")
        if script_files:
            print(f"  Scripts: {len(script_files)} files")
        if other_files:
            print(f"  Other: {len(other_files)} files")

    print(f"\nMigration complete! Run 'pip install -e .' to install the package.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
