#!/usr/bin/env python3
"""
Demo script for FE-004: Fingerprint Diff Reporting feature.

Demonstrates field-level change detection and markdown report generation
for existing K-numbers in the FDA database.

Usage:
    python3 demo_diff_reporting.py
"""

import os
import sys
from datetime import datetime, timezone

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from change_detector import _detect_field_changes, _generate_diff_report


def demo_basic_detection():
    """Demonstrate basic field-level change detection."""
    print("=" * 60)
    print("FE-004 Demo: Field-Level Change Detection")
    print("=" * 60)
    print()

    # Simulate stored device data from previous fingerprint
    stored_devices = {
        "K241001": {
            "k_number": "K241001",
            "device_name": "Cardiovascular Catheter System",
            "applicant": "OldMedTech Corp",
            "decision_date": "20240315",
            "decision_code": "SESE",
            "clearance_type": "Traditional",
            "product_code": "DQY",
        },
        "K241002": {
            "k_number": "K241002",
            "device_name": "Digital Pathology Imaging System",
            "applicant": "BioVision Inc",
            "decision_date": "20240401",
            "decision_code": "SESE",
            "clearance_type": "Traditional",
            "product_code": "QKQ",
        },
    }

    # Simulate current API data with changes
    current_devices = [
        {
            "k_number": "K241001",
            "device_name": "Cardiovascular Catheter System",
            "applicant": "NewMedTech LLC",  # Company acquired
            "decision_date": "20240320",  # FDA backdated correction
            "decision_code": "SESE",
            "clearance_type": "Traditional",
            "product_code": "DQY",
        },
        {
            "k_number": "K241002",
            "device_name": "Digital Pathology Imaging System v2",  # Name updated
            "applicant": "BioVision Inc",
            "decision_date": "20240401",
            "decision_code": "SESE",
            "clearance_type": "Traditional",
            "product_code": "QKQ",
        },
    ]

    print("Stored Device Data (from fingerprint):")
    print("-" * 40)
    for k_num, device in stored_devices.items():
        print(f"  {k_num}:")
        print(f"    Applicant: {device['applicant']}")
        print(f"    Decision Date: {device['decision_date']}")
        print(f"    Device Name: {device['device_name']}")
    print()

    print("Current API Data:")
    print("-" * 40)
    for device in current_devices:
        k_num = device["k_number"]
        print(f"  {k_num}:")
        print(f"    Applicant: {device['applicant']}")
        print(f"    Decision Date: {device['decision_date']}")
        print(f"    Device Name: {device['device_name']}")
    print()

    # Detect changes
    changes = _detect_field_changes(stored_devices, current_devices)

    print(f"Changes Detected: {len(changes)}")
    print("-" * 40)
    for change in changes:
        print(f"  K-Number: {change['k_number']}")
        print(f"  Field: {change['field']}")
        print(f"  Before: {change['before']}")
        print(f"  After: {change['after']}")
        print()

    return changes


def demo_report_generation(changes):
    """Demonstrate markdown report generation."""
    print("=" * 60)
    print("Generating Markdown Diff Report")
    print("=" * 60)
    print()

    timestamp = datetime.now(timezone.utc).isoformat()
    report = _generate_diff_report(
        changes,
        "DQY, QKQ",
        timestamp,
        output_path="/tmp/field_changes_demo.md",
    )

    print("Report generated successfully!")
    print(f"Location: /tmp/field_changes_demo.md")
    print()
    print("Report Preview:")
    print("-" * 40)
    # Show first 30 lines of report
    lines = report.split("\n")
    for line in lines[:30]:
        print(line)
    if len(lines) > 30:
        print(f"... ({len(lines) - 30} more lines)")
    print()


def demo_use_cases():
    """Demonstrate real-world use cases."""
    print("=" * 60)
    print("Real-World Use Cases")
    print("=" * 60)
    print()

    use_cases = [
        {
            "scenario": "Company Acquisition",
            "description": "FDA updates applicant name after M&A",
            "example": "OldCorp Inc -> NewCorp LLC",
            "benefit": "Track ownership changes automatically",
        },
        {
            "scenario": "Decision Date Correction",
            "description": "FDA backdates clearance to correct decision date",
            "example": "20240315 -> 20240301",
            "benefit": "Catch FDA database corrections",
        },
        {
            "scenario": "Device Name Update",
            "description": "FDA corrects device name typo or adds version",
            "example": "Catheter System -> Catheter System v2",
            "benefit": "Maintain accurate device records",
        },
        {
            "scenario": "Reclassification",
            "description": "FDA changes clearance type (rare)",
            "example": "Traditional -> Abbreviated",
            "benefit": "Detect regulatory reclassifications",
        },
    ]

    for i, use_case in enumerate(use_cases, 1):
        print(f"{i}. {use_case['scenario']}")
        print(f"   Description: {use_case['description']}")
        print(f"   Example: {use_case['example']}")
        print(f"   Benefit: {use_case['benefit']}")
        print()


def demo_cli_usage():
    """Demonstrate CLI usage examples."""
    print("=" * 60)
    print("CLI Usage Examples")
    print("=" * 60)
    print()

    examples = [
        {
            "command": "python3 change_detector.py --project my_project --diff-report",
            "description": "Run change detection with diff reporting enabled",
        },
        {
            "command": "python3 change_detector.py --project my_project --diff-report --json",
            "description": "Get JSON output with field change counts",
        },
        {
            "command": "python3 change_detector.py --project my_project --diff-report --trigger",
            "description": "Detect changes, generate report, and trigger pipeline",
        },
    ]

    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['description']}")
        print(f"   $ {example['command']}")
        print()


def main():
    """Run all demos."""
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  FE-004: Fingerprint Diff Reporting Feature Demo".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    # Run demos
    changes = demo_basic_detection()
    demo_report_generation(changes)
    demo_use_cases()
    demo_cli_usage()

    print("=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print()
    print("Next Steps:")
    print("  1. Run tests: pytest tests/test_change_detector.py::TestFE004* -v")
    print("  2. Try CLI: python3 change_detector.py --project <name> --diff-report")
    print("  3. Check report: cat <project_dir>/field_changes_report.md")
    print()


if __name__ == "__main__":
    main()
