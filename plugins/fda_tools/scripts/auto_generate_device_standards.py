#!/usr/bin/env python3
"""
Auto-Generate Device-Specific Standards for ALL FDA Product Codes

This script uses BatchFetch + AI extraction to automatically generate
device-specific standards JSON files for all active FDA product codes.

Architecture:
1. Query openFDA for all active product codes
2. For each code: Download last 50-100 510(k) summaries
3. Extract standards references from PDFs using AI pattern matching
4. Rank by frequency (>50% = applicable standard)
5. Generate standards_[category].json files
6. Flag low-confidence entries for human review

Usage:
    # Generate for all codes (recommended)
    python3 auto_generate_device_standards.py --all

    # Generate for specific code
    python3 auto_generate_device_standards.py --product-code DQY

    # Generate for top N codes by volume
    python3 auto_generate_device_standards.py --top 500

    # Dry run (no file writes)
    python3 auto_generate_device_standards.py --all --dry-run
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import Counter, defaultdict
from datetime import datetime
import tempfile

from fda_tools.lib.subprocess_helpers import run_subprocess  # type: ignore


class DeviceStandardsGenerator:
    """Auto-generates device-specific standards from FDA 510(k) data"""

    # Standards patterns for extraction
    STANDARD_PATTERNS = [
        r'ISO\s+(\d+(?:-\d+)?(?::\d+)?(?:/A\d+:\d+)?)',
        r'IEC\s+(\d+(?:-\d+)?(?::\d+)?(?:/A\d+:\d+)?)',
        r'ASTM\s+([A-Z]\d+(?:-\d+)?(?::\d+)?)',
        r'ANSI/AAMI\s+([A-Z0-9]+(?::\d+)?)',
        r'AAMI\s+([A-Z0-9]+(?::\d+)?)',
        r'CLSI\s+([A-Z0-9]+(?:-[A-Z0-9]+)?)',
        r'EN\s+(\d+(?:-\d+)?(?::\d+)?)',
    ]

    # Minimum frequency for inclusion (50% = standard appears in half of devices)
    MIN_FREQUENCY = 0.50

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.75  # ≥75% frequency
    MEDIUM_CONFIDENCE = 0.60  # 60-74% frequency
    LOW_CONFIDENCE = 0.50  # 50-59% frequency (flag for review)

    def __init__(self, data_dir: Path, output_dir: Path, dry_run: bool = False):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.dry_run = dry_run

        # Load existing standards for deduplication
        self.existing_standards = self._load_existing_standards()

    def _load_existing_standards(self) -> Dict[str, Set[str]]:
        """Load existing standards files to avoid duplicates"""
        existing = {}
        standards_dir = self.output_dir / 'standards'

        if not standards_dir.exists():
            return existing

        for json_file in standards_dir.glob('standards_*.json'):
            with open(json_file) as f:
                data = json.load(f)
                for code in data.get('product_codes', []):
                    existing[code] = set(
                        s['number'] for s in data.get('applicable_standards', [])
                    )

        return existing

    def get_all_product_codes(self) -> List[Tuple[str, int, str]]:
        """
        Query openFDA for all active product codes with submission counts

        Returns:
            List of (product_code, submission_count, device_name) tuples
        """
        print("📊 Querying openFDA for all active product codes...")

        # Use openFDA API to get product code statistics
        # This queries the device classification endpoint
        try:
            import requests

            url = "https://api.fda.gov/device/classification.json"
            params = {
                'limit': 1000,
                'count': 'product_code.exact'
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Extract product codes with counts
            codes = []
            for result in data.get('results', []):
                product_code = result.get('term', '')
                count = result.get('count', 0)

                if product_code and count > 0:
                    # Get device name for this code
                    device_name = self._get_device_name(product_code)
                    codes.append((product_code, count, device_name))

            # Sort by submission count (descending)
            codes.sort(key=lambda x: x[1], reverse=True)

            print(f"✅ Found {len(codes)} active product codes")
            return codes

        except Exception as e:
            print(f"⚠️  openFDA query failed: {e}")
            print("📁 Falling back to local data...")
            return self._get_codes_from_local_data()

    def _get_device_name(self, product_code: str) -> str:
        """Get human-readable device name for product code"""
        try:
            import requests
            url = f"https://api.fda.gov/device/classification.json"
            params = {
                'search': f'product_code:"{product_code}"',
                'limit': 1
            }
            response = requests.get(url, params=params)
            data = response.json()

            if data.get('results'):
                return data['results'][0].get('device_name', 'Unknown Device')

        except (Exception,) as exc:
            print(f"  WARNING: Could not fetch device name for {product_code}: {exc}",
                  file=sys.stderr)

        return 'Unknown Device'

    def _get_codes_from_local_data(self) -> List[Tuple[str, int, str]]:
        """Fallback: Extract product codes from local 510(k) data"""
        codes_counter = Counter()

        # Scan all project directories
        projects_dir = Path.home() / 'fda-510k-data' / 'projects'

        if not projects_dir.exists():
            return []

        for csv_file in projects_dir.rglob('510k_download.csv'):
            try:
                with open(csv_file) as f:
                    for line in f:
                        match = re.search(r',([A-Z]{3}),', line)
                        if match:
                            codes_counter[match.group(1)] += 1
            except (OSError, UnicodeDecodeError) as exc:
                print(f"  WARNING: Could not read {csv_file}: {exc}",
                      file=sys.stderr)
                continue

        # Convert to sorted list
        codes = [
            (code, count, self._get_device_name(code))
            for code, count in codes_counter.most_common()
        ]

        return codes

    def download_predicates(self, product_code: str, limit: int = 100) -> List[str]:
        """
        Download recent 510(k) summaries for a product code using BatchFetch

        Args:
            product_code: FDA product code
            limit: Maximum number of predicates to download

        Returns:
            List of PDF file paths
        """
        print(f"  📥 Downloading up to {limit} predicates for {product_code}...")

        # Create temporary project for this product code
        temp_dir = tempfile.mkdtemp(prefix=f'auto_gen_{product_code}_')

        try:
            # Run batchfetch command
            cmd = [
                'bash', '-c',
                f'cd {PLUGIN_ROOT} && '
                f'bash scripts/batchfetch.sh '
                f'--product-codes {product_code} '
                f'--years 2020-2024 '
                f'--project auto_gen_{product_code} '
                f'--limit {limit} '
                f'--no-enrich'
            ]

            result = run_command(
                cmd=cmd,
                step_name=f"batchfetch_{product_code}",
                timeout=600,
                cwd=str(PLUGIN_ROOT),
                verbose=False
            )

            if result["status"] != "success":
                if result["status"] == "timeout":
                    print(f"  ⏱️  Timeout downloading {product_code}")
                else:
                    error_msg = result.get("error", "Unknown error")
                    print(f"  ⚠️  BatchFetch failed: {error_msg}")
                return []

            # Find downloaded PDFs
            pdf_dir = Path(temp_dir) / 'pdfs'
            if pdf_dir.exists():
                pdfs = list(pdf_dir.glob('*.pdf'))
                print(f"  ✅ Downloaded {len(pdfs)} PDFs")
                return [str(p) for p in pdfs]

        except Exception as e:
            print(f"  ❌ Error: {e}")

        return []

    def extract_standards_from_pdfs(self, pdf_paths: List[str]) -> Counter:
        """
        Extract standards references from 510(k) summary PDFs

        Args:
            pdf_paths: List of PDF file paths

        Returns:
            Counter of standard numbers and their frequencies
        """
        print(f"  🔍 Extracting standards from {len(pdf_paths)} PDFs...")

        standards_counter = Counter()

        for pdf_path in pdf_paths:
            try:
                # Extract text from PDF using pdftotext or similar
                text = self._extract_pdf_text(pdf_path)

                # Find all standards references
                standards = self._find_standards_in_text(text)
                standards_counter.update(standards)

            except Exception as e:
                print(f"    ⚠️  Failed to process {Path(pdf_path).name}: {e}")
                continue

        print(f"  ✅ Found {len(standards_counter)} unique standards")
        return standards_counter

    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text content from PDF file"""
        try:
            # Try pdftotext first (fastest)
            result = run_command(
                cmd=['pdftotext', pdf_path, '-'],                timeout=30,
                cwd=str(Path(pdf_path).parent),
                verbose=False
            )
            if result["status"] == "success":
                return result["output"]
        except (OSError, Exception) as exc:
            # pdftotext not available or failed — try Python fallback
            print(f"  DEBUG: pdftotext failed for {pdf_path}: {exc}",
                  file=sys.stderr)

        # Fallback: Try pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            text = ''
            for page in reader.pages:
                text += page.extract_text()
            return text
        except (ImportError, OSError, ValueError) as exc:
            # pypdf not available or PDF is corrupt
            print(f"  DEBUG: pypdf failed for {pdf_path}: {exc}",
                  file=sys.stderr)

        return ''

    def _find_standards_in_text(self, text: str) -> List[str]:
        """Find all standards references in text using regex patterns"""
        standards = []

        for pattern in self.STANDARD_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Normalize standard number
                std_num = match.group(0).strip()
                standards.append(std_num)

        return standards

    def rank_standards(
        self,
        standards_counter: Counter,
        total_devices: int
    ) -> List[Tuple[str, float, str]]:
        """
        Rank standards by frequency and assign confidence levels

        Args:
            standards_counter: Counter of standard occurrences
            total_devices: Total number of devices analyzed

        Returns:
            List of (standard, frequency, confidence) tuples
        """
        ranked = []

        for standard, count in standards_counter.most_common():
            frequency = count / total_devices

            # Skip if below minimum threshold
            if frequency < self.MIN_FREQUENCY:
                continue

            # Assign confidence level
            if frequency >= self.HIGH_CONFIDENCE:
                confidence = 'HIGH'
            elif frequency >= self.MEDIUM_CONFIDENCE:
                confidence = 'MEDIUM'
            else:
                confidence = 'LOW'

            ranked.append((standard, frequency, confidence))

        return ranked

    def generate_json_file(
        self,
        product_code: str,
        device_name: str,
        standards: List[Tuple[str, float, str]],
        total_devices: int
    ) -> Dict:
        """
        Generate standards JSON file for a product code

        Args:
            product_code: FDA product code
            device_name: Human-readable device name
            standards: List of (standard, frequency, confidence) tuples
            total_devices: Total devices analyzed

        Returns:
            Generated JSON data structure
        """
        # Determine category from device name
        category = self._categorize_device(device_name)

        # Build applicable standards list
        applicable_standards = []

        for standard, frequency, confidence in standards:
            # Parse standard to get full details
            std_dict = self._parse_standard(standard, frequency, confidence)
            applicable_standards.append(std_dict)

        # Build JSON structure
        data = {
            "category": category,
            "product_codes": [product_code],
            "device_examples": [device_name],
            "applicable_standards": applicable_standards,
            "generation_metadata": {
                "method": "auto_generated",
                "timestamp": datetime.now().isoformat(),
                "devices_analyzed": total_devices,
                "confidence_threshold": self.MIN_FREQUENCY,
                "manual_review_required": any(
                    s[2] == 'LOW' for s in standards
                )
            }
        }

        return data

    def _categorize_device(self, device_name: str) -> str:
        """Determine device category from name"""
        name_lower = device_name.lower()

        # Category keywords
        categories = {
            'cardiovascular': ['heart', 'cardiac', 'vascular', 'catheter', 'stent', 'valve'],
            'orthopedic': ['bone', 'joint', 'spine', 'hip', 'knee', 'orthopedic', 'implant'],
            'neurological': ['brain', 'neural', 'neuro', 'stimulator'],
            'diagnostic': ['diagnostic', 'test', 'assay', 'analyzer'],
            'surgical': ['surgical', 'scalpel', 'forceps', 'retractor'],
            'ophthalmic': ['eye', 'ophthalmic', 'vision', 'lens'],
            'dental': ['dental', 'tooth', 'orthodontic'],
            'respiratory': ['lung', 'respiratory', 'ventilator', 'oxygen'],
            'software': ['software', 'algorithm', 'digital', 'computer'],
        }

        for category, keywords in categories.items():
            if any(kw in name_lower for kw in keywords):
                return category.title()

        return 'General Medical Devices'

    def _parse_standard(
        self,
        standard: str,
        frequency: float,
        confidence: str
    ) -> Dict:
        """Parse standard string into structured dict"""
        # Extract standard number and title (if available)
        # This is a simplified version - could be enhanced with database lookup

        return {
            "number": standard,
            "title": f"Standard for {standard}",  # Placeholder
            "applicability": f"Found in {frequency*100:.1f}% of {standard.split()[0]} devices",
            "frequency": round(frequency, 3),
            "confidence": confidence
        }

    def save_json_file(self, product_code: str, data: Dict):
        """Save generated JSON to file"""
        # Determine filename from category
        category = data['category'].lower().replace(' ', '_')
        filename = f"standards_{category}_{product_code.lower()}.json"

        output_path = self.output_dir / 'standards' / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.dry_run:
            print(f"  🔍 DRY RUN: Would save to {output_path}")
            print(f"     Standards: {len(data['applicable_standards'])}")
            return

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"  ✅ Saved {output_path}")

    def process_product_code(self, product_code: str, device_name: str = None):
        """
        Process a single product code: download, extract, generate

        Args:
            product_code: FDA product code
            device_name: Optional device name
        """
        print(f"\n{'='*60}")
        print(f"Processing {product_code}: {device_name or 'Unknown Device'}")
        print(f"{'='*60}")

        # Skip if already processed
        if product_code in self.existing_standards:
            print(f"  ⏭️  Skipping {product_code} (already has standards)")
            return

        # Download predicates
        pdf_paths = self.download_predicates(product_code, limit=100)

        if not pdf_paths:
            print(f"  ⚠️  No data available for {product_code}")
            return

        # Extract standards
        standards_counter = self.extract_standards_from_pdfs(pdf_paths)

        if not standards_counter:
            print(f"  ⚠️  No standards found for {product_code}")
            return

        # Rank standards
        ranked_standards = self.rank_standards(
            standards_counter,
            len(pdf_paths)
        )

        if not ranked_standards:
            print(f"  ⚠️  No standards meet frequency threshold for {product_code}")
            return

        # Generate JSON
        json_data = self.generate_json_file(
            product_code,
            device_name or 'Unknown Device',
            ranked_standards,
            len(pdf_paths)
        )

        # Save file
        self.save_json_file(product_code, json_data)

        print(f"  ✅ {product_code} complete: {len(ranked_standards)} standards")


def main():
    parser = argparse.ArgumentParser(
        description='Auto-generate device-specific standards for FDA product codes'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Generate for all active product codes (recommended)'
    )

    parser.add_argument(
        '--product-code',
        type=str,
        help='Generate for specific product code'
    )

    parser.add_argument(
        '--top',
        type=int,
        help='Generate for top N codes by submission volume'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing files'
    )

    parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path.home() / 'fda-510k-data',
        help='Data directory path'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=PLUGIN_ROOT / 'data',
        help='Output directory for generated JSON files'
    )

    # Add compliance disclaimer flags
    try:
        from compliance_disclaimer import add_disclaimer_args, show_disclaimer
        add_disclaimer_args(parser)
        _has_disclaimer = True
    except ImportError:
        _has_disclaimer = False
        # Define stub functions for type checker
        def add_disclaimer_args(parser):  # type: ignore
            pass
        def show_disclaimer(tool_name, accept_flag=False, quiet=False):  # type: ignore
            return True

    args = parser.parse_args()

    # Show compliance disclaimer before any processing (FDA-34)
    if _has_disclaimer:
        show_disclaimer(
            "auto-generate-device-standards",
            accept_flag=getattr(args, "accept_disclaimer", False),
        )

    # Validate arguments
    if not any([args.all, args.product_code, args.top]):
        parser.error('Must specify --all, --product-code, or --top')

    # Initialize generator
    generator = DeviceStandardsGenerator(
        args.data_dir,
        args.output_dir,
        args.dry_run
    )

    # Get product codes to process
    if args.product_code:
        codes = [(args.product_code, 0, generator._get_device_name(args.product_code))]
    else:
        codes = generator.get_all_product_codes()

        if args.top:
            codes = codes[:args.top]

    # Process each code
    print(f"\n{'='*60}")
    print(f"AUTO-GENERATING STANDARDS FOR {len(codes)} PRODUCT CODES")
    print(f"{'='*60}\n")

    success_count = 0
    fail_count = 0
    skip_count = 0

    for product_code, count, device_name in codes:
        try:
            generator.process_product_code(product_code, device_name)
            success_count += 1
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"  ❌ Error processing {product_code}: {e}")
            fail_count += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  ✅ Success: {success_count}")
    print(f"  ❌ Failed:  {fail_count}")
    print(f"  ⏭️  Skipped: {skip_count}")
    print(f"  📊 Total:   {success_count + fail_count + skip_count}")


if __name__ == '__main__':
    main()
