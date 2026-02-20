#!/usr/bin/env python3
"""
Auto-fetch predicate device data from openFDA for SE comparison tables.

Usage:
    python3 fetch_predicate_data.py K123456
    python3 fetch_predicate_data.py K123456 K234567 K345678
    python3 fetch_predicate_data.py --json K123456
"""

import argparse
import json
import sys
from pathlib import Path

# Add scripts dir to path for imports
SCRIPT_DIR = Path(__file__).parent


# ============================================================
# Security: Path Validation (FDA-171 / SEC-004 / CWE-22)
# ============================================================

def _sanitize_path(path_input):
    """
    Sanitize file path to prevent path traversal attacks.

    Args:
        path_input: User-supplied path string

    Returns:
        Sanitized path string

    Raises:
        ValueError: If path contains traversal sequences or null bytes

    Security: FDA-171 (SEC-004) - CWE-22 Path Traversal Prevention
    """
    if not path_input:
        raise ValueError("Path cannot be empty")

    path_str = str(path_input).strip()

    # Reject null bytes (can bypass security checks)
    if '\x00' in path_str:
        raise ValueError(f"Path contains null bytes: '{path_str}'")

    # Reject explicit traversal sequences
    if '..' in path_str:
        raise ValueError(f"Path contains directory traversal sequence (..). File: {path_str}")

    return path_str


def _validate_path_safety(path_input, allowed_base_dirs=None):
    """
    Validate that a file path is safe and doesn't escape allowed directories.

    Args:
        path_input: Path to validate (string or Path object)
        allowed_base_dirs: List of allowed base directories (defaults to project root)

    Returns:
        Resolved absolute Path object

    Raises:
        ValueError: If path escapes allowed directories

    Security: FDA-171 (SEC-004) - CWE-22 Path Traversal Prevention
    """
    # Sanitize first
    sanitized = _sanitize_path(path_input)

    # Resolve to absolute canonical path
    try:
        resolved_path = Path(sanitized).resolve(strict=False)
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Cannot resolve path: {sanitized}") from e

    # If no allowed directories specified, allow anything (backwards compat)
    if allowed_base_dirs is None:
        return resolved_path

    # Ensure allowed_base_dirs are all resolved absolute paths
    allowed_resolved = []
    for base_dir in allowed_base_dirs:
        try:
            base_resolved = Path(base_dir).resolve(strict=False)
            allowed_resolved.append(base_resolved)
        except (OSError, RuntimeError):
            continue

    # Check if resolved path is within any allowed directory
    for allowed_dir in allowed_resolved:
        try:
            # Check if resolved_path is relative to allowed_dir
            resolved_path.relative_to(allowed_dir)
            return resolved_path  # Path is safe
        except ValueError:
            # Not relative to this allowed_dir, try next
            continue

    # Path escapes all allowed directories
    raise ValueError(
        f"Security violation: Path escapes allowed directories\n"
        f"  Requested: {path_input}\n"
        f"  Resolved: {resolved_path}\n"
        f"  Allowed: {', '.join(str(d) for d in allowed_resolved)}"
    )

try:
    from fda_api_client import FDAClient
except ImportError:
    print("ERROR: Could not import FDAClient. Make sure fda_api_client.py is in the same directory.", file=sys.stderr)
    sys.exit(1)


def extract_ifu(result):
    """Extract Indications for Use from 510(k) result."""
    if not result:
        return None

    # Try multiple fields where IFU might be stored
    ifu_fields = [
        'statement_or_summary',
        'openfda.device_name',
        'k_number',  # Last resort - just the K-number
    ]

    for field in ifu_fields:
        if '.' in field:
            # Nested field
            parts = field.split('.')
            value = result
            for part in parts:
                value = value.get(part) if isinstance(value, dict) else None
                if value is None:
                    break
            if value and isinstance(value, str) and len(value) > 20:
                return value.strip()
            elif value and isinstance(value, list) and len(value) > 0:
                return value[0].strip()
        else:
            value = result.get(field)
            if value and isinstance(value, str) and len(value) > 20:
                return value.strip()
            elif value and isinstance(value, list) and len(value) > 0 and isinstance(value[0], str):
                return value[0].strip()

    return None


def extract_device_description(result):
    """Extract device description from 510(k) result."""
    if not result:
        return None

    # Try statement_or_summary first (often has device description)
    summary = result.get('statement_or_summary')
    if summary and len(summary) > 50:
        # Try to extract device description section
        import re
        patterns = [
            r'(?:Device Description|Description of Device)[:\s]+(.*?)(?=\n\n|\n[A-Z][a-z]+:)',
            r'(?:The device|This device|The .* is)[^\.]+\.',
        ]
        for pattern in patterns:
            match = re.search(pattern, summary, re.IGNORECASE | re.DOTALL)
            if match:
                desc = match.group(1) if match.lastindex else match.group(0)
                return desc.strip()[:500]  # Limit to 500 chars

    # Fallback to device_name
    device_name = result.get('openfda', {}).get('device_name')
    if device_name:
        return device_name[0] if isinstance(device_name, list) else device_name

    return None


def extract_materials(result):
    """Extract materials from 510(k) result."""
    if not result:
        return None

    summary = result.get('statement_or_summary', '')
    if not summary:
        return None

    # Common material keywords
    material_keywords = [
        'stainless steel', 'titanium', 'PEEK', 'PTFE', 'silicone', 'nitinol',
        'cobalt-chromium', 'polyurethane', 'polycarbonate', 'nylon',
        'polyethylene', 'polypropylene', 'UHMWPE', 'HDPE', 'FEP',
        'acrylic', 'ceramic', 'hydroxyapatite', 'tungsten', 'nickel',
        'PVC', 'latex', 'epoxy', 'parylene', 'hydrogel', 'collagen',
        'gold', 'platinum', 'iridium', 'aluminum', 'copper'
    ]

    found = set()
    for keyword in material_keywords:
        import re
        if re.search(r'\b' + re.escape(keyword) + r'\b', summary, re.IGNORECASE):
            found.add(keyword.title())

    return ', '.join(sorted(found)) if found else None


def extract_sterilization(result):
    """Extract sterilization method from 510(k) result."""
    if not result:
        return None

    summary = result.get('statement_or_summary', '')
    if not summary:
        return None

    import re
    patterns = [
        r'(?:sterilized|sterilization) (?:by|using|with|via) ([^\.]+)',
        r'(ethylene oxide|EO|EtO|gamma radiation|steam|autoclave|dry heat)',
    ]

    for pattern in patterns:
        match = re.search(pattern, summary, re.IGNORECASE)
        if match:
            method = match.group(1) if match.lastindex else match.group(0)
            return method.strip()[:100]

    return None


def fetch_predicate_data(k_numbers, output_format='text'):
    """
    Fetch predicate data from openFDA for given K-numbers.

    Args:
        k_numbers: List of K-numbers (e.g., ['K123456', 'K234567'])
        output_format: 'text' or 'json'

    Returns:
        Dict mapping K-number to extracted data
    """
    client = FDAClient()
    results = {}

    for k_num in k_numbers:
        # Normalize K-number format
        k_num = k_num.upper().strip()
        if not k_num.startswith('K'):
            k_num = 'K' + k_num

        print(f"Fetching {k_num}...", file=sys.stderr)

        try:
            api_response = client.get_510k(k_num)

            # openFDA returns {results: [...], meta: {...}}
            if not api_response or 'results' not in api_response:
                results[k_num] = {'error': 'Not found in openFDA'}
                continue

            # Get first result
            if not api_response['results'] or len(api_response['results']) == 0:
                results[k_num] = {'error': 'No results found'}
                continue

            result = api_response['results'][0]

            # Extract key fields
            data = {
                'k_number': k_num,
                'applicant': result.get('applicant'),
                'device_name': result.get('device_name'),
                'product_code': result.get('product_code'),
                'regulation_number': result.get('openfda', {}).get('regulation_number'),
                'decision_date': result.get('decision_date'),
                'advisory_committee': result.get('advisory_committee'),
                'statement_or_summary': result.get('statement_or_summary'),

                # Extracted fields
                'ifu': extract_ifu(result),
                'device_description': extract_device_description(result),
                'materials': extract_materials(result),
                'sterilization': extract_sterilization(result),

                # Raw summary available
                'has_summary': bool(result.get('statement_or_summary')),
                'summary_length': len(result.get('statement_or_summary', '')),
            }

            results[k_num] = data

        except Exception as e:
            results[k_num] = {'error': str(e)}

    return results


def format_output(results, output_format='text'):
    """Format results as text or JSON."""
    if output_format == 'json':
        return json.dumps(results, indent=2)

    # Text format
    output = []
    for k_num, data in results.items():
        if 'error' in data:
            output.append(f"{k_num}: ERROR - {data['error']}")
            continue

        output.append(f"\n{'='*80}")
        output.append(f"K-NUMBER: {k_num}")
        output.append(f"{'='*80}")
        output.append(f"Applicant: {data.get('applicant', 'N/A')}")
        output.append(f"Device Name: {data.get('device_name', 'N/A')}")
        output.append(f"Product Code: {data.get('product_code', 'N/A')}")
        output.append(f"Regulation: {data.get('regulation_number', 'N/A')}")
        output.append(f"Decision Date: {data.get('decision_date', 'N/A')}")
        output.append(f"Advisory Committee: {data.get('advisory_committee', 'N/A')}")
        output.append(f"\nSummary Available: {'Yes' if data.get('has_summary') else 'No'}")
        if data.get('has_summary'):
            output.append(f"Summary Length: {data.get('summary_length')} chars")

        output.append(f"\n--- EXTRACTED FIELDS ---")
        ifu = data.get('ifu') or '[Not found]'
        desc = data.get('device_description') or '[Not found]'
        output.append(f"IFU: {ifu[:200]}...")
        output.append(f"Description: {desc[:200]}...")
        output.append(f"Materials: {data.get('materials', '[Not found]')}")
        output.append(f"Sterilization: {data.get('sterilization', '[Not found]')}")

    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Fetch predicate device data from openFDA for SE comparison tables'
    )
    parser.add_argument('k_numbers', nargs='+', help='One or more K-numbers')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')

    args = parser.parse_args()

    # Security: Validate output path (FDA-171 / SEC-004 / CWE-22)
    if args.output:
        try:
            # Allow writing to scripts dir, project root, or current working directory
            project_root = SCRIPT_DIR.parent.resolve()
            allowed_dirs = [
                project_root,
                Path.cwd(),
            ]
            validated_output = str(_validate_path_safety(args.output, allowed_dirs))
            args.output = validated_output
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    results = fetch_predicate_data(args.k_numbers, 'json' if args.json else 'text')
    output = format_output(results, 'json' if args.json else 'text')

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Results written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
