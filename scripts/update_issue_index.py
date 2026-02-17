#!/usr/bin/env python3
"""
Issue Tracking Index Automation Tool

Helps maintain the ISSUE_TRACKING_INDEX.md document by:
- Counting completed vs pending items
- Verifying cross-references
- Calculating effort statistics
- Detecting stale data
- Generating update reports

Usage:
  python3 update_issue_index.py --scan                    # Scan all sources
  python3 update_issue_index.py --verify                  # Verify all links
  python3 update_issue_index.py --stats                   # Calculate statistics
  python3 update_issue_index.py --report                  # Generate full report
  python3 update_issue_index.py --update-timestamp        # Update document timestamp
"""

import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List


class IssueTrackingIndexUpdater:
    """Automation tool for ISSUE_TRACKING_INDEX.md maintenance."""

    def __init__(self, base_path: str = "/home/linux/.claude/plugins/marketplaces/fda-tools"):
        self.base_path = Path(base_path)
        self.docs_path = self.base_path / "docs"
        self.index_path = self.docs_path / "ISSUE_TRACKING_INDEX.md"
        self.todo_path = self.base_path / "TODO.md"
        self.gap_report_path = self.docs_path / "planning" / "GAP-ANALYSIS-REPORT.md"

        self.stats = {
            "todo_complete": 0,
            "todo_pending": 0,
            "gap_urgent": 0,
            "gap_high": 0,
            "gap_medium": 0,
            "gap_low": 0,
            "total_tests": 0,
            "passing_tests": 0,
            "failing_tests": 0,
        }

    def scan_todo_file(self) -> Dict[str, int]:
        """Count completed and pending items in TODO.md."""
        counts = {"complete": 0, "pending": 0}

        if not self.todo_path.exists():
            print(f"WARNING: TODO.md not found at {self.todo_path}")
            return counts

        with open(self.todo_path, 'r') as f:
            content = f.read()

        # Count [x] and [ ] patterns in markdown checklists
        counts["complete"] = len(re.findall(r'^\- \[x\]', content, re.MULTILINE))
        counts["pending"] = len(re.findall(r'^\- \[ \]', content, re.MULTILINE))

        self.stats["todo_complete"] = counts["complete"]
        self.stats["todo_pending"] = counts["pending"]

        return counts

    def scan_gap_analysis(self) -> Dict[str, int]:
        """Count issues by priority in GAP-ANALYSIS-REPORT.md."""
        counts = {"urgent": 0, "high": 0, "medium": 0, "low": 0}

        if not self.gap_report_path.exists():
            print(f"WARNING: GAP-ANALYSIS-REPORT.md not found at {self.gap_report_path}")
            return counts

        with open(self.gap_report_path, 'r') as f:
            content = f.read()

        # Count "Priority: URGENT" patterns
        counts["urgent"] = len(re.findall(r"^\*\*Priority\*\*:\s*URGENT", content, re.MULTILINE))
        counts["high"] = len(re.findall(r"^\*\*Priority\*\*:\s*HIGH", content, re.MULTILINE))
        counts["medium"] = len(re.findall(r"^\*\*Priority\*\*:\s*MEDIUM", content, re.MULTILINE))
        counts["low"] = len(re.findall(r"^\*\*Priority\*\*:\s*LOW", content, re.MULTILINE))

        self.stats["gap_urgent"] = counts["urgent"]
        self.stats["gap_high"] = counts["high"]
        self.stats["gap_medium"] = counts["medium"]
        self.stats["gap_low"] = counts["low"]

        return counts

    def scan_tests(self) -> Dict[str, int]:
        """Count test results from recent test runs."""
        counts = {"total": 0, "passing": 0, "failing": 0}

        test_dir = self.base_path / "plugins" / "fda-tools" / "tests"

        if not test_dir.exists():
            print(f"WARNING: Tests directory not found at {test_dir}")
            return counts

        # Look for pytest output or .json result files
        # This is a placeholder - actual implementation would parse pytest --json output

        return counts

    def verify_cross_references(self) -> List[str]:
        """Verify all file references in the index exist."""
        issues = []

        if not self.index_path.exists():
            issues.append(f"CRITICAL: Index file not found at {self.index_path}")
            return issues

        with open(self.index_path, 'r') as f:
            content = f.read()

        # Find all file references [Link](#xxx)
        file_patterns = [
            (r"TODO\.md", self.todo_path),
            (r"GAP-ANALYSIS-REPORT\.md", self.gap_report_path),
            (r"TESTING_SPEC\.md", self.base_path / "plugins" / "fda-tools" / "docs" / "TESTING_SPEC.md"),
        ]

        for pattern, expected_path in file_patterns:
            if re.search(pattern, content):
                if not expected_path.exists():
                    issues.append(f"MISSING: Referenced file {expected_path}")

        return issues

    def generate_report(self) -> str:
        """Generate a comprehensive update report."""
        self.scan_todo_file()
        gap_counts = self.scan_gap_analysis()

        report = f"""
# Issue Tracking Index - Automated Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary Statistics

### TODO.md Status
- Completed Items: {self.stats["todo_complete"]}
- Pending Items: {self.stats["todo_pending"]}
- Total: {self.stats["todo_complete"] + self.stats["todo_pending"]}

### GAP Analysis Distribution
- URGENT: {gap_counts["urgent"]} issues
- HIGH: {gap_counts["high"]} issues
- MEDIUM: {gap_counts["medium"]} issues
- LOW: {gap_counts["low"]} issues
- Total: {sum(gap_counts.values())} issues

### Cross-References
Issues Found:
"""

        verification_issues = self.verify_cross_references()
        if verification_issues:
            for issue in verification_issues:
                report += f"- ❌ {issue}\n"
        else:
            report += "- ✓ All cross-references verified\n"

        report += f"""

## Recommendations

1. TODO.md Status
   - {self.stats["todo_complete"]}/{self.stats['todo_complete'] + self.stats['todo_pending']} items complete
   - Completion rate: {100 * self.stats['todo_complete'] / (self.stats['todo_complete'] + self.stats['todo_pending']):.1f}%

2. Gap Analysis
   - Total new issues: {sum(gap_counts.values())}
   - Breakdown by priority:
     * {gap_counts['urgent']} URGENT (needs immediate attention)
     * {gap_counts['high']} HIGH (plan for next sprint)
     * {gap_counts['medium']} MEDIUM (3-month window)
     * {gap_counts['low']} LOW (backlog)

3. Next Steps
   - Review URGENT items (should block release)
   - Plan HIGH priority items for next sprint
   - Consider FE-001 through FE-010 for post-release work

## File Manifest

Required files for index:
- {self.todo_path.name}: {'✓' if self.todo_path.exists() else '❌ MISSING'}
- {self.gap_report_path.name}: {'✓' if self.gap_report_path.exists() else '❌ MISSING'}
- {self.index_path.name}: {'✓' if self.index_path.exists() else '❌ MISSING'}
"""

        return report

    def update_timestamp(self) -> bool:
        """Update the Last Updated timestamp in the index."""
        if not self.index_path.exists():
            print(f"ERROR: Index file not found at {self.index_path}")
            return False

        with open(self.index_path, 'r') as f:
            content = f.read()

        new_timestamp = datetime.now().strftime('%Y-%m-%d')
        updated_content = re.sub(
            r'(\*\*Last Updated:\*\*\s+)\d{4}-\d{2}-\d{2}',
            rf'\g<1>{new_timestamp}',
            content
        )

        if updated_content != content:
            with open(self.index_path, 'w') as f:
                f.write(updated_content)
            print(f"✓ Updated timestamp to {new_timestamp}")
            return True
        else:
            print("No timestamp change needed")
            return False

    def calculate_effort_statistics(self) -> Dict[str, float]:
        """Calculate effort statistics from gap analysis."""
        stats = {
            "total_min": 0.0,
            "total_max": 0.0,
            "average_min": 0.0,
            "average_max": 0.0,
        }

        if not self.gap_report_path.exists():
            return stats

        with open(self.gap_report_path, 'r') as f:
            content = f.read()

        # Find all effort patterns like "5-7 hours"
        efforts = re.findall(r'(\d+)-(\d+)\s+hours?', content)

        if efforts:
            min_sum = sum(int(e[0]) for e in efforts)
            max_sum = sum(int(e[1]) for e in efforts)
            count = len(efforts)

            stats["total_min"] = float(min_sum)
            stats["total_max"] = float(max_sum)
            stats["average_min"] = min_sum / count if count > 0 else 0.0
            stats["average_max"] = max_sum / count if count > 0 else 0.0

        return stats

    def print_stats(self):
        """Print formatted statistics."""
        todo_stats = self.scan_todo_file()
        gap_stats = self.scan_gap_analysis()
        effort_stats = self.calculate_effort_statistics()

        print("\n" + "="*60)
        print("ISSUE TRACKING INDEX - STATISTICS")
        print("="*60)

        print("\nTODO.md Status:")
        print(f"  Complete: {todo_stats['complete']}")
        print(f"  Pending:  {todo_stats['pending']}")
        total = todo_stats['complete'] + todo_stats['pending']
        if total > 0:
            print(f"  Rate:     {100 * todo_stats['complete'] / total:.1f}%")

        print("\nGap Analysis Distribution:")
        print(f"  URGENT:   {gap_stats['urgent']} issues")
        print(f"  HIGH:     {gap_stats['high']} issues")
        print(f"  MEDIUM:   {gap_stats['medium']} issues")
        print(f"  LOW:      {gap_stats['low']} issues")
        print(f"  TOTAL:    {sum(gap_stats.values())} issues")

        print("\nEffort Estimation:")
        print(f"  Total Effort: {effort_stats['total_min']}-{effort_stats['total_max']} hours")
        print(f"  Average Per Issue: {effort_stats['average_min']:.1f}-{effort_stats['average_max']:.1f} hours")

        print("\n" + "="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Maintain ISSUE_TRACKING_INDEX.md automation"
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan all issue sources"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify cross-references"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print statistics"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate full report"
    )
    parser.add_argument(
        "--update-timestamp",
        action="store_true",
        help="Update document timestamp"
    )

    args = parser.parse_args()

    updater = IssueTrackingIndexUpdater()

    if args.scan:
        print("Scanning issue sources...")
        todo = updater.scan_todo_file()
        gap = updater.scan_gap_analysis()
        print(f"✓ TODO.md: {todo['complete']} complete, {todo['pending']} pending")
        print(f"✓ Gap Analysis: {gap['urgent']}U {gap['high']}H {gap['medium']}M {gap['low']}L")

    if args.verify:
        print("Verifying cross-references...")
        issues = updater.verify_cross_references()
        if issues:
            for issue in issues:
                print(f"  ❌ {issue}")
        else:
            print("  ✓ All references verified")

    if args.stats:
        updater.print_stats()

    if args.report:
        report = updater.generate_report()
        print(report)
        # Save report
        report_path = updater.base_path / "docs" / "ISSUE_INDEX_REPORT.md"
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"\n✓ Report saved to {report_path}")

    if args.update_timestamp:
        print("Updating timestamp...")
        if updater.update_timestamp():
            print("✓ Timestamp updated")
        else:
            print("✗ Failed to update timestamp")

    if not any([args.scan, args.verify, args.stats, args.report, args.update_timestamp]):
        parser.print_help()


if __name__ == "__main__":
    main()
