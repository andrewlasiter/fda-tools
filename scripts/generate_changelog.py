#!/usr/bin/env python3
"""Automated changelog generation script for FDA Tools.

This script generates a changelog from git commit messages between releases.

Usage:
    python scripts/generate_changelog.py
    python scripts/generate_changelog.py --from v5.35.0 --to v5.36.0
    python scripts/generate_changelog.py --output CHANGELOG.md
"""

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Commit:
    """Represents a parsed git commit."""

    hash: str
    short_hash: str
    message: str
    author: str
    date: str
    type: Optional[str] = None
    scope: Optional[str] = None
    breaking: bool = False


def run_git_command(args: List[str]) -> str:
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}", file=sys.stderr)
        sys.exit(1)


def get_latest_tag() -> Optional[str]:
    """Get the most recent git tag."""
    try:
        return run_git_command(["describe", "--tags", "--abbrev=0"])
    except SystemExit:
        return None


def get_commits(from_ref: Optional[str], to_ref: str) -> List[Commit]:
    """Get commits between two git refs.

    Args:
        from_ref: Starting reference (tag or commit). If None, gets all commits to to_ref.
        to_ref: Ending reference (tag, branch, or commit)

    Returns:
        List of Commit objects
    """
    if from_ref:
        commit_range = f"{from_ref}..{to_ref}"
    else:
        commit_range = to_ref

    # Format: hash|short_hash|author|date|message
    log_format = "%H|%h|%an|%ad|%s"
    output = run_git_command(
        ["log", commit_range, f"--pretty=format:{log_format}", "--date=short"]
    )

    commits = []
    for line in output.split("\n"):
        if not line:
            continue

        parts = line.split("|", 4)
        if len(parts) != 5:
            continue

        hash_, short_hash, author, date, message = parts
        commits.append(
            Commit(
                hash=hash_,
                short_hash=short_hash,
                author=author,
                date=date,
                message=message,
            )
        )

    return commits


def parse_conventional_commit(commit: Commit) -> Commit:
    """Parse conventional commit format.

    Format: <type>(<scope>): <description>
    Examples:
        feat(api): add new endpoint
        fix: resolve null pointer
        feat!: breaking change
    """
    # Pattern: type(scope): message or type: message
    pattern = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(([^)]+)\))?(!)?:\s*(.+)$"
    match = re.match(pattern, commit.message, re.IGNORECASE)

    if match:
        commit.type = match.group(1).lower()
        commit.scope = match.group(3)
        commit.breaking = match.group(4) == "!"
        commit.message = match.group(5)
    else:
        # Not a conventional commit, categorize as "other"
        commit.type = "other"

    # Check for BREAKING CHANGE in message
    if "BREAKING CHANGE" in commit.message:
        commit.breaking = True

    return commit


def categorize_commits(commits: List[Commit]) -> Dict[str, List[Commit]]:
    """Categorize commits by type."""
    categories = defaultdict(list)

    for commit in commits:
        commit = parse_conventional_commit(commit)
        categories[commit.type].append(commit)

    return dict(categories)


def format_changelog(
    version: str,
    categories: Dict[str, List[Commit]],
    from_ref: Optional[str],
    to_ref: str,
) -> str:
    """Format changelog in markdown."""
    lines = []

    # Header
    lines.append(f"# Release {version}")
    lines.append("")
    lines.append(f"**Release Date:** {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")

    if from_ref:
        lines.append(
            f"**Full Changelog:** "
            f"https://github.com/your-org/fda-tools/compare/{from_ref}...{to_ref}"
        )
        lines.append("")

    # Type order and labels
    type_order = [
        ("feat", "Features", "New features and enhancements"),
        ("fix", "Bug Fixes", "Bug fixes and corrections"),
        ("perf", "Performance", "Performance improvements"),
        ("refactor", "Refactoring", "Code refactoring"),
        ("docs", "Documentation", "Documentation updates"),
        ("test", "Testing", "Test updates"),
        ("build", "Build", "Build system updates"),
        ("ci", "CI/CD", "Continuous integration updates"),
        ("chore", "Chore", "Maintenance and chores"),
        ("other", "Other Changes", "Other changes"),
    ]

    # Breaking changes section
    breaking = []
    for commits in categories.values():
        breaking.extend([c for c in commits if c.breaking])

    if breaking:
        lines.append("## BREAKING CHANGES")
        lines.append("")
        for commit in breaking:
            scope = f"**{commit.scope}:** " if commit.scope else ""
            lines.append(f"- {scope}{commit.message} ({commit.short_hash})")
        lines.append("")

    # Regular sections
    for type_key, title, description in type_order:
        if type_key not in categories:
            continue

        commits = categories[type_key]
        if not commits:
            continue

        lines.append(f"## {title}")
        lines.append("")

        for commit in commits:
            if commit.breaking:
                continue  # Already listed in breaking changes

            scope = f"**{commit.scope}:** " if commit.scope else ""
            lines.append(f"- {scope}{commit.message} ({commit.short_hash})")

        lines.append("")

    # Contributors
    authors = sorted(set(c.author for c in sum(categories.values(), [])))
    if authors:
        lines.append("## Contributors")
        lines.append("")
        for author in authors:
            lines.append(f"- {author}")
        lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate changelog from git commits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--from",
        dest="from_ref",
        help="Starting git reference (tag, branch, or commit). Default: latest tag",
    )
    parser.add_argument(
        "--to",
        dest="to_ref",
        default="HEAD",
        help="Ending git reference (tag, branch, or commit). Default: HEAD",
    )
    parser.add_argument(
        "--version",
        "-v",
        help="Version number for changelog header. Default: auto-detect from to_ref",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path. Default: print to stdout",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing changelog file instead of overwriting",
    )

    args = parser.parse_args()

    # Determine from_ref
    from_ref = args.from_ref
    if not from_ref:
        from_ref = get_latest_tag()
        if from_ref:
            print(f"Using latest tag as starting point: {from_ref}", file=sys.stderr)
        else:
            print("No tags found, generating changelog from first commit", file=sys.stderr)

    # Determine version
    version = args.version
    if not version:
        if args.to_ref.startswith("v"):
            version = args.to_ref[1:]
        else:
            # Try to get version from pyproject.toml
            script_dir = Path(__file__).parent
            pyproject_path = script_dir.parent / "pyproject.toml"
            if pyproject_path.exists():
                content = pyproject_path.read_text()
                match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
                if match:
                    version = match.group(1)

    if not version:
        version = "Unreleased"

    # Get commits
    print(f"Generating changelog for {version}...", file=sys.stderr)
    commits = get_commits(from_ref, args.to_ref)
    print(f"Found {len(commits)} commits", file=sys.stderr)

    if not commits:
        print("No commits found in range", file=sys.stderr)
        return 0

    # Categorize commits
    categories = categorize_commits(commits)

    # Format changelog
    changelog = format_changelog(version, categories, from_ref, args.to_ref)

    # Output
    if args.output:
        output_path = Path(args.output)
        if args.append and output_path.exists():
            existing = output_path.read_text()
            changelog = changelog + "\n\n---\n\n" + existing
        output_path.write_text(changelog)
        print(f"Changelog written to {output_path}", file=sys.stderr)
    else:
        print(changelog)

    return 0


if __name__ == "__main__":
    sys.exit(main())
