#!/usr/bin/env python3
"""
Verification Script for Predicate Selection Enhancement

Tests that all components of the comprehensive enhancement are properly integrated.
"""

import os
import sys
from pathlib import Path

def check_file_exists(file_path: Path, description: str) -> bool:
    """Check if a file exists and report status"""
    exists = file_path.exists()
    status = "✓" if exists else "✗"
    print(f"  {status} {description}: {file_path.name}")
    return exists

def check_function_in_file(file_path: Path, function_name: str) -> bool:
    """Check if a function exists in a Python file"""
    if not file_path.exists():
        return False
    
    with open(file_path) as f:
        content = f.read()
    
    exists = f"def {function_name}" in content
    status = "✓" if exists else "✗"
    print(f"  {status} Function: {function_name}()")
    return exists

def check_integration_point(file_path: Path, pattern: str, description: str) -> bool:
    """Check if an integration point exists in a file"""
    if not file_path.exists():
        return False
    
    with open(file_path) as f:
        content = f.read()
    
    exists = pattern in content
    status = "✓" if exists else "✗"
    print(f"  {status} {description}")
    return exists

def main():
    print("="*60)
    print("Predicate Selection Enhancement - Verification")
    print("="*60)
    print()

    plugin_root = Path(__file__).parent.parent
    scripts_dir = plugin_root / 'scripts'
    commands_dir = plugin_root / 'commands'
    agents_dir = plugin_root / 'agents'
    references_dir = plugin_root / 'references'

    total_checks = 0
    passed_checks = 0

    # Phase 1: Data Integration & Full-Text Search
    print("Phase 1: Data Integration & Full-Text Search")
    print("-"*60)

    checks = [
        check_file_exists(scripts_dir / 'build_structured_cache.py', "Structured cache builder"),
        check_file_exists(scripts_dir / 'full_text_search.py', "Full-text search module"),
        check_file_exists(commands_dir / 'search-predicates.md', "Search-predicates command"),
    ]
    
    print("\n  Functions in full_text_search.py:")
    checks.extend([
        check_function_in_file(scripts_dir / 'full_text_search.py', "search_all_sections"),
        check_function_in_file(scripts_dir / 'full_text_search.py', "find_predicates_by_feature"),
    ])

    total_checks += len(checks)
    passed_checks += sum(checks)
    print()

    # Phase 2: Predicate Validation & FDA Guidance
    print("Phase 2: Predicate Validation & FDA Guidance")
    print("-"*60)

    checks = [
        check_file_exists(scripts_dir / 'web_predicate_validator.py', "Web predicate validator"),
        check_file_exists(references_dir / 'fda-predicate-criteria-2014.md', "FDA criteria reference"),
    ]

    print("\n  Integration in review.md:")
    checks.extend([
        check_integration_point(
            commands_dir / 'review.md',
            'web_predicate_validator.py',
            "Web validation integration"
        ),
        check_integration_point(
            commands_dir / 'review.md',
            'check_fda_predicate_criteria',
            "FDA criteria compliance check"
        ),
    ])

    total_checks += len(checks)
    passed_checks += sum(checks)
    print()

    # Phase 3: RA Professional Integration
    print("Phase 3: RA Professional Integration")
    print("-"*60)

    checks = [
        check_file_exists(agents_dir / 'ra-professional-advisor.md', "RA professional advisor agent"),
    ]

    print("\n  Integration in research.md:")
    checks.extend([
        check_integration_point(
            commands_dir / 'research.md',
            'Step 7: RA Professional Review of Recommendations',
            "RA review in research phase"
        ),
        check_integration_point(
            commands_dir / 'research.md',
            'ra-professional-advisor',
            "RA agent invocation"
        ),
    ])

    print("\n  Integration in review.md:")
    checks.extend([
        check_integration_point(
            commands_dir / 'review.md',
            'Step 5: RA Professional Final Review',
            "RA final review in review phase"
        ),
        check_integration_point(
            commands_dir / 'review.md',
            'fda_audit_logger.py',
            "Audit trail logging"
        ),
    ])

    total_checks += len(checks)
    passed_checks += sum(checks)
    print()

    # Section Detection
    print("Section Detection System")
    print("-"*60)

    checks = [
        check_file_exists(references_dir / 'section-patterns.md', "Section patterns reference"),
    ]

    print("\n  Section detection in build_structured_cache.py:")
    checks.extend([
        check_integration_point(
            scripts_dir / 'build_structured_cache.py',
            'detect_sections',
            "Section detection function"
        ),
        check_integration_point(
            scripts_dir / 'build_structured_cache.py',
            'apply_ocr_corrections',
            "OCR correction function"
        ),
        check_integration_point(
            scripts_dir / 'build_structured_cache.py',
            'estimate_ocr_quality',
            "OCR quality estimation"
        ),
    ])

    total_checks += len(checks)
    passed_checks += sum(checks)
    print()

    # Summary
    print("="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    print(f"Total checks: {total_checks}")
    print(f"Passed: {passed_checks}")
    print(f"Failed: {total_checks - passed_checks}")
    print(f"Success rate: {passed_checks/total_checks*100:.1f}%")
    print()

    if passed_checks == total_checks:
        print("✓ All components verified - Enhancement is COMPLETE")
        return 0
    else:
        print("✗ Some components missing - Enhancement is INCOMPLETE")
        return 1

if __name__ == '__main__':
    sys.exit(main())
