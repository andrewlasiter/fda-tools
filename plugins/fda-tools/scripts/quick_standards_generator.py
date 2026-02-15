#!/usr/bin/env python3
"""
Quick Standards Generator - Pragmatic Implementation

Uses openFDA API directly to analyze 510(k) summaries and extract common standards.
Works without requiring BatchFetch or local PDF processing.

Usage:
    python3 quick_standards_generator.py DQY
    python3 quick_standards_generator.py MAX JJE  # Multiple codes
    python3 quick_standards_generator.py --all --top 50  # Top 50 codes
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set
import time

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Install with: pip3 install requests")
    sys.exit(1)


class QuickStandardsGenerator:
    """Quick standards generation using openFDA API"""

    OPENFDA_BASE = "https://api.fda.gov/device/510k.json"

    # Standard patterns
    STANDARD_PATTERNS = [
        (r'ISO\s+(\d+(?:-\d+)?(?::\d{4})?(?:/A\d+:\d{4})?)', 'ISO'),
        (r'IEC\s+(\d+(?:-\d+)?(?::\d{4})?)', 'IEC'),
        (r'ASTM\s+([A-Z]\d+(?:-\d+)?)', 'ASTM'),
        (r'AAMI\s+([A-Z0-9]+)', 'AAMI'),
        (r'CLSI\s+([A-Z0-9]+(?:-[A-Z0-9]+)?)', 'CLSI'),
    ]

    MIN_FREQUENCY = 0.40  # 40% threshold (more lenient for quick generation)

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_recent_clearances(self, product_code: str, limit: int = 100) -> List[Dict]:
        """Get recent 510(k) clearances for a product code"""
        print(f"  📡 Querying openFDA for {product_code}...")

        try:
            params = {
                'search': f'product_code:"{product_code}"',
                'limit': min(limit, 100),  # API max is 100
                'sort': 'date_received:desc'
            }

            response = requests.get(self.OPENFDA_BASE, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get('results', [])
            print(f"  ✅ Found {len(results)} clearances")
            return results

        except Exception as e:
            print(f"  ❌ API error: {e}")
            return []

    def extract_standards_from_text(self, text: str) -> List[str]:
        """Extract standard references from text"""
        if not text:
            return []

        standards = []
        text_upper = text.upper()

        for pattern, prefix in self.STANDARD_PATTERNS:
            matches = re.finditer(pattern, text_upper, re.IGNORECASE)
            for match in matches:
                std_num = match.group(0).strip()
                # Normalize
                std_num = re.sub(r'\s+', ' ', std_num)
                standards.append(std_num)

        return standards

    def analyze_clearances(self, clearances: List[Dict]) -> Counter:
        """Analyze clearances to find common standards"""
        print(f"  🔍 Analyzing {len(clearances)} clearances...")

        standards_counter = Counter()

        for clearance in clearances:
            # Extract text from various fields
            text_fields = [
                clearance.get('statement_or_summary', ''),
                clearance.get('device_name', ''),
                ' '.join(clearance.get('openfda', {}).get('device_class', [])),
            ]

            text = ' '.join(text_fields)
            standards = self.extract_standards_from_text(text)
            standards_counter.update(standards)

        print(f"  ✅ Found {len(standards_counter)} unique standards")
        return standards_counter

    def rank_standards(self, counter: Counter, total: int) -> List[tuple]:
        """Rank standards by frequency"""
        ranked = []

        for standard, count in counter.most_common():
            frequency = count / total if total > 0 else 0

            if frequency < self.MIN_FREQUENCY:
                continue

            # Confidence based on frequency
            if frequency >= 0.70:
                confidence = 'HIGH'
            elif frequency >= 0.50:
                confidence = 'MEDIUM'
            else:
                confidence = 'LOW'

            ranked.append((standard, frequency, confidence, count))

        return ranked

    def get_device_info(self, product_code: str) -> Dict:
        """Get device classification info"""
        try:
            url = "https://api.fda.gov/device/classification.json"
            params = {'search': f'product_code:"{product_code}"', 'limit': 1}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get('results'):
                result = data['results'][0]
                return {
                    'name': result.get('device_name', 'Unknown Device'),
                    'class': result.get('device_class', ''),
                    'regulation': result.get('regulation_number', ''),
                    'review_panel': result.get('review_panel', '')
                }
        except:
            pass

        return {'name': 'Unknown Device', 'class': '', 'regulation': '', 'review_panel': ''}

    def generate_json(self, product_code: str, device_info: Dict,
                     standards: List[tuple], total_analyzed: int) -> Dict:
        """Generate standards JSON file"""

        # Categorize device
        name_lower = device_info['name'].lower()

        categories = {
            'Cardiovascular': ['heart', 'cardiac', 'vascular', 'catheter', 'stent'],
            'Orthopedic': ['bone', 'joint', 'spine', 'hip', 'knee', 'implant'],
            'Neurological': ['brain', 'neural', 'neuro', 'stimulator'],
            'Diagnostic': ['diagnostic', 'test', 'assay', 'ivd'],
            'Surgical': ['surgical', 'scalpel', 'forceps'],
            'Ophthalmic': ['eye', 'ophthalmic', 'lens'],
            'Dental': ['dental', 'tooth'],
        }

        category = 'General Medical Devices'
        for cat, keywords in categories.items():
            if any(kw in name_lower for kw in keywords):
                category = cat
                break

        # Build standards list
        applicable_standards = []
        for standard, frequency, confidence, count in standards:
            applicable_standards.append({
                'number': standard,
                'title': f'Standard applicable to {product_code} devices',
                'applicability': f'Found in {count}/{total_analyzed} clearances ({frequency*100:.1f}%)',
                'frequency': round(frequency, 3),
                'confidence': confidence
            })

        return {
            'category': category,
            'product_codes': [product_code],
            'device_examples': [device_info['name']],
            'device_class': device_info['class'],
            'regulation_number': device_info['regulation'],
            'applicable_standards': applicable_standards,
            'generation_metadata': {
                'method': 'quick_auto_generated',
                'source': 'openFDA_api',
                'devices_analyzed': total_analyzed,
                'confidence_threshold': self.MIN_FREQUENCY,
                'manual_review_required': any(s[2] == 'LOW' for s in standards)
            }
        }

    def save_json(self, product_code: str, data: Dict):
        """Save JSON file"""
        category = data['category'].lower().replace(' ', '_')
        filename = f"standards_{category}_{product_code.lower()}.json"
        filepath = self.output_dir / filename

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"  💾 Saved: {filepath}")
        return filepath

    def process_product_code(self, product_code: str):
        """Process a single product code"""
        print(f"\n{'='*60}")
        print(f"Processing {product_code}")
        print(f"{'='*60}")

        # Get device info
        device_info = self.get_device_info(product_code)
        print(f"  📋 {device_info['name']}")

        # Get recent clearances
        clearances = self.get_recent_clearances(product_code, limit=100)

        if not clearances:
            print(f"  ⚠️  No clearances found")
            return None

        # Analyze for standards
        standards_counter = self.analyze_clearances(clearances)

        if not standards_counter:
            print(f"  ⚠️  No standards found")
            return None

        # Rank standards
        ranked = self.rank_standards(standards_counter, len(clearances))

        if not ranked:
            print(f"  ⚠️  No standards meet threshold")
            return None

        # Generate JSON
        json_data = self.generate_json(
            product_code, device_info, ranked, len(clearances)
        )

        # Save file
        filepath = self.save_json(product_code, json_data)

        print(f"  ✅ Success: {len(ranked)} standards")
        for std, freq, conf, count in ranked[:5]:  # Show top 5
            print(f"     • {std} ({freq*100:.0f}%, {conf})")

        return filepath


def main():
    parser = argparse.ArgumentParser(description='Quick standards generation')
    parser.add_argument('codes', nargs='*', help='Product codes to process')
    parser.add_argument('--all', action='store_true', help='Process all codes')
    parser.add_argument('--top', type=int, help='Process top N codes by volume')
    parser.add_argument('--output', type=Path,
                       default=Path(__file__).parent.parent / 'data' / 'standards',
                       help='Output directory')

    args = parser.parse_args()

    if not args.codes and not args.all and not args.top:
        parser.error('Specify product codes, --all, or --top N')

    generator = QuickStandardsGenerator(args.output)

    # Determine codes to process
    codes = args.codes or []

    if args.all or args.top:
        # Get top codes (simplified - using known high-volume codes)
        top_codes = [
            'DQY', 'KGN', 'MAX', 'FRN', 'DSI', 'GEI', 'OVE', 'NIQ',
            'DTK', 'JJE', 'LCX', 'QIH', 'GZB', 'OLO', 'QBH'
        ]
        if args.top:
            codes = top_codes[:args.top]
        else:
            codes = top_codes

    # Process each code
    print(f"\n{'='*60}")
    print(f"QUICK STANDARDS GENERATION")
    print(f"Processing {len(codes)} product codes")
    print(f"{'='*60}")

    success = 0
    failed = 0

    for code in codes:
        try:
            result = generator.process_product_code(code.upper())
            if result:
                success += 1
            else:
                failed += 1
            time.sleep(0.5)  # Rate limiting
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted")
            break
        except Exception as e:
            print(f"  ❌ Error: {e}")
            failed += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  ✅ Success: {success}")
    print(f"  ❌ Failed:  {failed}")
    print(f"  📊 Total:   {success + failed}")


if __name__ == '__main__':
    main()
