#!/usr/bin/env python3
"""
Fix indentation issues introduced by migration script.

The migration script removed sys.path lines but sometimes left
broken indentation for import statements that followed.
"""

import re
from pathlib import Path


def fix_file_indentation(file_path):
    """Fix indentation issues in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

    original_content = content

    # Fix 1: Add indentation after "try:" for "from fda_tools" imports
    content = re.sub(
        r'(try:)\n(from fda_tools\.)',
        r'\1\n    \2',
        content
    )

    # Fix 2: Add indentation after "if" statements for "try:" blocks
    content = re.sub(
        r'(if .+:)\n(try:)\n',
        r'\1\n    \2\n',
        content
    )

    # Fix 3: Empty try blocks (try: followed immediately by except:)
    # Add a pass statement
    content = re.sub(
        r'(try:)\n(except )',
        r'\1\n    pass\n\2',
        content
    )

    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False

    return False


def main():
    """Fix indentation in all Python files."""
    base_dir = Path(__file__).parent

    # Find all Python files
    python_files = []
    for pattern in ['**/*.py']:
        for file_path in base_dir.glob(pattern):
            if (
                file_path.name == 'fix_indentation.py' or
                '__pycache__' in str(file_path) or
                '.pytest_cache' in str(file_path)
            ):
                continue
            python_files.append(file_path)

    print(f"Fixing indentation in {len(python_files)} files...")

    fixed_count = 0
    for file_path in sorted(python_files):
        if fix_file_indentation(file_path):
            rel_path = file_path.relative_to(base_dir)
            print(f"✓ Fixed {rel_path}")
            fixed_count += 1

    print(f"\nFixed indentation in {fixed_count} files")


if __name__ == '__main__':
    main()
