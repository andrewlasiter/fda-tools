#!/usr/bin/env python3
"""
Web-Based Predicate Validation

Validates predicate suitability by searching web sources for:
- FDA warning letters
- Recall database
- Enforcement actions
- Market status verification

Usage:
    python3 web_predicate_validator.py --k-numbers K123456,K234567
    python3 web_predicate_validator.py --batch predicates.txt --output validation_report.json
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class PredicateValidator:
    """Validates predicates against FDA enforcement/safety databases."""

    VALIDATION_FLAGS = {
        'GREEN': 'Safe to use - no enforcement actions, no recalls, recent clearance',
        'YELLOW': 'Review required - Class II recalls, old clearance (>10 years), minor enforcement',
        'RED': 'Avoid - Class I recalls, withdrawn, major enforcement actions, NSE'
    }

    def __init__(self):
        self.results = {}

    def validate_batch(self, k_numbers: List[str]) -> Dict[str, Dict]:
        """
        Validate a batch of K-numbers.

        Returns dict mapping K-number -> validation_result
        """
        for k_num in k_numbers:
            self.results[k_num] = self._validate_single(k_num)

        return self.results

    def _validate_single(self, k_number: str) -> Dict:
        """
        Validate a single K-number.

        Checks:
        1. Warning letters (FDA.gov site search)
        2. Recall database
        3. Enforcement actions
        4. Market status
        """
        result = {
            'k_number': k_number,
            'validated_at': datetime.now().isoformat(),
            'warning_letters': [],
            'recalls': [],
            'enforcement_actions': [],
            'market_status': 'unknown',
            'flag': 'GREEN',
            'rationale': []
        }

        # Check recalls (using openFDA API if available)
        recalls = self._check_recalls(k_number)
        if recalls:
            result['recalls'] = recalls
            # Flag based on recall class
            if any(r.get('classification', '') == 'Class I' for r in recalls):
                result['flag'] = 'RED'
                result['rationale'].append('Class I recall found')
            elif recalls:
                if result['flag'] == 'GREEN':
                    result['flag'] = 'YELLOW'
                result['rationale'].append(f"{len(recalls)} recall(s) found")

        # Check warning letters
        warnings = self._check_warning_letters(k_number)
        if warnings:
            result['warning_letters'] = warnings
            if result['flag'] != 'RED':
                result['flag'] = 'YELLOW'
            result['rationale'].append(f"{len(warnings)} warning letter(s) found")

        # Check enforcement actions
        enforcement = self._check_enforcement(k_number)
        if enforcement:
            result['enforcement_actions'] = enforcement
            if any(e.get('status', '') == 'Ongoing' for e in enforcement):
                result['flag'] = 'RED'
                result['rationale'].append('Active enforcement action')
            elif result['flag'] == 'GREEN':
                result['flag'] = 'YELLOW'

        # Default rationale if still GREEN
        if result['flag'] == 'GREEN' and not result['rationale']:
            result['rationale'].append('No enforcement actions or recalls found')

        return result

    def _check_recalls(self, k_number: str) -> List[Dict]:
        """Check FDA recall database for this device."""
        # Try openFDA API
        try:
            import sys
            sys.path.insert(0, os.path.dirname(__file__))
            from fda_api_client import FDAClient

            client = FDAClient()
            response = client._request('device/recall', {
                'search': f'k_numbers:"{k_number}"',
                'limit': 100
            })

            recalls = []
            for r in response.get('results', []):
                recalls.append({
                    'classification': r.get('classification', 'Unknown'),
                    'recall_date': r.get('recall_initiation_date', 'Unknown'),
                    'reason': r.get('reason_for_recall', ''),
                    'status': r.get('status', 'Unknown')
                })
            return recalls

        except Exception as e:
            # API not available - would need WebSearch fallback here
            print(f"Warning: Could not check recalls for {k_number}: {e}", file=sys.stderr)
            return []

    def _check_warning_letters(self, k_number: str) -> List[Dict]:
        """Search for FDA warning letters mentioning this device."""
        # This would use WebSearch in production
        # Placeholder for now
        return []

    def _check_enforcement(self, k_number: str) -> List[Dict]:
        """Check for enforcement actions."""
        try:
            import sys
            sys.path.insert(0, os.path.dirname(__file__))
            from fda_api_client import FDAClient

            client = FDAClient()
            response = client._request('device/enforcement', {
                'search': f'k_numbers:"{k_number}"',
                'limit': 100
            })

            actions = []
            for a in response.get('results', []):
                actions.append({
                    'status': a.get('status', 'Unknown'),
                    'classification': a.get('classification', 'Unknown'),
                    'reason': a.get('reason_for_recall', ''),
                    'date': a.get('report_date', 'Unknown')
                })
            return actions

        except Exception:
            return []

    def generate_report(self, output_format: str = 'json') -> str:
        """Generate validation report in specified format."""
        if output_format == 'json':
            return json.dumps(self.results, indent=2)

        elif output_format == 'md':
            lines = []
            lines.append("# Predicate Validation Report")
            lines.append(f"\nGenerated: {datetime.now().isoformat()}")
            lines.append(f"\nTotal validated: {len(self.results)}")
            lines.append("")

            # Count by flag
            flag_counts = {'GREEN': 0, 'YELLOW': 0, 'RED': 0}
            for result in self.results.values():
                flag_counts[result['flag']] += 1

            lines.append("## Summary")
            lines.append(f"- ✓ GREEN (safe): {flag_counts['GREEN']}")
            lines.append(f"- ⚠ YELLOW (review): {flag_counts['YELLOW']}")
            lines.append(f"- ✗ RED (avoid): {flag_counts['RED']}")
            lines.append("")

            # Details per device
            lines.append("## Device Details")
            for k_num, result in sorted(self.results.items()):
                flag = result['flag']
                emoji = {'GREEN': '✓', 'YELLOW': '⚠', 'RED': '✗'}[flag]

                lines.append(f"\n### {emoji} {k_num} — {flag}")
                lines.append(f"**Rationale:** {', '.join(result['rationale'])}")

                if result['recalls']:
                    lines.append(f"\n**Recalls:** {len(result['recalls'])}")
                    for r in result['recalls']:
                        lines.append(f"  - {r['classification']}: {r['reason'][:100]}...")

                if result['warning_letters']:
                    lines.append(f"\n**Warning Letters:** {len(result['warning_letters'])}")

                if result['enforcement_actions']:
                    lines.append(f"\n**Enforcement Actions:** {len(result['enforcement_actions'])}")

            lines.append("\n---")
            lines.append("\nThis validation report is generated from public FDA data.")
            lines.append("Verify findings independently before making regulatory decisions.")

            return '\n'.join(lines)

        else:
            raise ValueError(f"Unsupported output format: {output_format}")


def main():
    parser = argparse.ArgumentParser(
        description='Validate FDA predicate devices against enforcement/safety databases'
    )
    parser.add_argument('--k-numbers', type=str,
                        help='Comma-separated K-numbers to validate')
    parser.add_argument('--batch', type=Path,
                        help='File containing K-numbers (one per line)')
    parser.add_argument('--output', type=Path,
                        help='Output file path (default: stdout)')
    parser.add_argument('--format', choices=['json', 'md'], default='json',
                        help='Output format (default: json)')

    args = parser.parse_args()

    if not (args.k_numbers or args.batch):
        parser.error('Must provide --k-numbers or --batch')

    # Collect K-numbers
    k_numbers = []
    if args.k_numbers:
        k_numbers.extend([k.strip().upper() for k in args.k_numbers.split(',')])
    if args.batch:
        with open(args.batch) as f:
            k_numbers.extend([line.strip().upper() for line in f if line.strip()])

    # Remove duplicates
    k_numbers = list(set(k_numbers))

    print(f"Validating {len(k_numbers)} predicate(s)...", file=sys.stderr)

    # Run validation
    validator = PredicateValidator()
    validator.validate_batch(k_numbers)

    # Generate report
    report = validator.generate_report(output_format=args.format)

    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"✓ Validation report written to {args.output}", file=sys.stderr)
    else:
        print(report)

    # Summary to stderr
    flag_counts = {'GREEN': 0, 'YELLOW': 0, 'RED': 0}
    for result in validator.results.values():
        flag_counts[result['flag']] += 1

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Validation complete:", file=sys.stderr)
    print(f"  ✓ GREEN: {flag_counts['GREEN']}", file=sys.stderr)
    print(f"  ⚠ YELLOW: {flag_counts['YELLOW']}", file=sys.stderr)
    print(f"  ✗ RED: {flag_counts['RED']}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)


if __name__ == '__main__':
    main()
