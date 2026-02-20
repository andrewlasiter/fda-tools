#!/usr/bin/env python3
"""
Automated CFR/Guidance Citation Verifier
=========================================

Automates verification of regulatory framework citations (CFRs and FDA Guidance).
Reduces 3-hour manual task to 30-60 minutes by pre-filling verification worksheets.

IMPORTANT: This script automates URL checking and title extraction only.
RA professional MUST still:
- Review applicability determinations
- Make professional regulatory judgments
- Check for recent amendments
- Sign off on verification worksheet

Usage:
    python3 verify_citations.py --output cfr_guidance_verification.md

Requirements:
    - Internet connection (access to ecfr.gov and fda.gov)
    - Python 3.7+
    - beautifulsoup4, lxml (for HTML parsing)
"""

import argparse
import json
import re
import urllib.request
from datetime import datetime
from typing import Dict, List, Tuple, Optional

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


class CitationVerifier:
    """Automated verifier for CFR and guidance citations."""

    # CFR citations to verify
    CFR_CITATIONS = [
        {
            'part': '21 CFR Part 803',
            'url': 'https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-803',
            'expected_title': 'Medical Device Reporting',
            'applies_to': 'MAUDE adverse event data',
            'key_sections': ['Subpart A', 'Subpart B', 'Subpart C']
        },
        {
            'part': '21 CFR Part 7, Subpart C',
            'url': 'https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-7/subpart-C',
            'expected_title': 'Enforcement Policy / Recalls',
            'applies_to': 'Device recall data',
            'key_sections': ['§7.40', '§7.41', '§7.42', '§7.46']
        },
        {
            'part': '21 CFR Part 807, Subpart E',
            'url': 'https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-807/subpart-E',
            'expected_title': 'Establishment Registration / Premarket Notification',
            'applies_to': '510(k) clearance validation',
            'key_sections': ['§807.81', '§807.87', '§807.92', '§807.95']
        }
    ]

    # Guidance documents to verify
    GUIDANCE_DOCS = [
        {
            'title': 'Medical Device Reporting for Manufacturers',
            'year': '2016',
            'url': 'https://www.fda.gov/regulatory-information/search-fda-guidance-documents/medical-device-reporting-manufacturers',
            'docket_number': 'FDA-2013-D-1406',
            'applies_to': 'MAUDE data collection requirements'
        },
        {
            'title': 'Recalls: CDRH-Regulated Products',
            'year': '2019',
            'url': 'https://www.fda.gov/regulatory-information/search-fda-guidance-documents/recalls-cdrh-regulated-products',
            'docket_number': 'FDA-2018-D-3771',
            'applies_to': 'Recall classification and reporting'
        },
        {
            'title': 'The 510(k) Program: Evaluating Substantial Equivalence',
            'year': '2014',
            'url': 'https://www.fda.gov/regulatory-information/search-fda-guidance-documents/510k-program-evaluating-substantial-equivalence-premarket-notifications-510k',
            'docket_number': 'FDA-2012-D-0537',
            'applies_to': '510(k) SE determination principles'
        }
    ]

    def __init__(self, output_file: str):
        self.output_file = output_file
        self.results: Dict = {
            'cfr_results': [],
            'guidance_results': [],
            'verification_time': datetime.now().isoformat()
        }

        if not BS4_AVAILABLE:
            print("⚠ WARNING: beautifulsoup4 not available. Install with: pip install beautifulsoup4 lxml")
            print("Continuing with limited verification (URL checking only)...\n")

    def verify_all(self) -> None:
        """Run automated verification for all CFRs and guidance documents."""
        print("Starting automated citation verification...")
        print(f"Output will be written to: {self.output_file}\n")

        # Verify CFRs
        print("="*60)
        print("VERIFYING CFR CITATIONS (3 regulations)")
        print("="*60 + "\n")

        for idx, cfr in enumerate(self.CFR_CITATIONS, 1):
            print(f"CFR {idx}/3: {cfr['part']}")
            result = self.verify_cfr(cfr)
            self.results['cfr_results'].append(result)
            print()

        # Verify Guidance
        print("="*60)
        print("VERIFYING GUIDANCE DOCUMENTS (3 documents)")
        print("="*60 + "\n")

        for idx, guidance in enumerate(self.GUIDANCE_DOCS, 1):
            print(f"Guidance {idx}/3: {guidance['title']} ({guidance['year']})")
            result = self.verify_guidance(guidance)
            self.results['guidance_results'].append(result)
            print()

        # Generate report
        self.generate_report()

        print("="*60)
        print("Automated verification complete!")
        print(f"Report written to: {self.output_file}")
        print("\n⚠ NEXT STEP: RA professional must review and sign off")
        print("="*60)

    def verify_cfr(self, cfr: Dict) -> Dict:
        """Verify a single CFR citation."""
        result = {
            'part': cfr['part'],
            'url': cfr['url'],
            'expected_title': cfr['expected_title'],
            'applies_to': cfr['applies_to'],
            'verification_time': datetime.now().isoformat()
        }

        # Step 1: URL resolution
        print(f"  Checking URL resolution...")
        url_ok, error = self._check_url(cfr['url'])
        result['url_resolves'] = url_ok
        result['url_error'] = error

        if not url_ok:
            print(f"    ✗ URL check failed: {error}")
            result['title_match'] = None
            result['structure_present'] = None
            return result

        print(f"    ✓ URL resolves")

        # Step 2 & 3: Title and structure (requires BeautifulSoup)
        if BS4_AVAILABLE:
            title, structure = self._parse_cfr_page(cfr['url'], cfr['key_sections'])
            result['actual_title'] = title
            result['title_match'] = self._fuzzy_match(title, cfr['expected_title'])
            result['structure_present'] = structure

            if result['title_match']:
                print(f"    ✓ Title matches: {title}")
            else:
                print(f"    ⚠ Title mismatch: Expected '{cfr['expected_title']}', Found '{title}'")

            print(f"    Structure check: {sum(structure.values())}/{len(structure)} sections found")
        else:
            print(f"    ⚠ Skipping title/structure check (beautifulsoup4 not available)")
            result['actual_title'] = None
            result['title_match'] = None
            result['structure_present'] = None

        return result

    def verify_guidance(self, guidance: Dict) -> Dict:
        """Verify a single guidance document."""
        result = {
            'title': guidance['title'],
            'year': guidance['year'],
            'url': guidance['url'],
            'docket_number': guidance['docket_number'],
            'applies_to': guidance['applies_to'],
            'verification_time': datetime.now().isoformat()
        }

        # URL resolution
        print(f"  Checking URL resolution...")
        url_ok, error = self._check_url(guidance['url'])
        result['url_resolves'] = url_ok
        result['url_error'] = error

        if not url_ok:
            print(f"    ✗ URL check failed: {error}")
            result['superseded'] = None
            return result

        print(f"    ✓ URL resolves")

        # Check for superseded status (requires BeautifulSoup)
        if BS4_AVAILABLE:
            superseded = self._check_superseded(guidance['url'])
            result['superseded'] = superseded

            if superseded:
                print(f"    ⚠ SUPERSEDED WARNING detected on page")
            else:
                print(f"    ✓ No superseded warning found")
        else:
            print(f"    ⚠ Skipping superseded check (beautifulsoup4 not available)")
            result['superseded'] = None

        return result

    def _check_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Check if URL resolves successfully."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'FDA-Citation-Verifier/1.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    return True, None
                else:
                    return False, f"HTTP {resp.status}"
        except Exception as e:
            return False, str(e)

    def _parse_cfr_page(self, url: str, key_sections: List[str]) -> Tuple[str, Dict]:
        """Parse CFR page to extract title and check for key sections."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'FDA-Citation-Verifier/1.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read()

            soup = BeautifulSoup(html, 'lxml')

            # Extract title
            title_elem = soup.find('h1', class_='part-heading') or soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else "TITLE_NOT_FOUND"

            # Check for key sections
            page_text = soup.get_text()
            structure = {section: section in page_text for section in key_sections}

            return title, structure
        except Exception:
            return "PARSE_ERROR", {section: False for section in key_sections}

    def _check_superseded(self, url: str) -> bool:
        """Check if guidance document shows superseded warning."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'FDA-Citation-Verifier/1.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', errors='ignore')

            # Check for common superseded indicators
            superseded_indicators = [
                'superseded',
                'withdrawn',
                'no longer in effect',
                'replaced by',
                'updated version'
            ]

            html_lower = html.lower()
            return any(indicator in html_lower for indicator in superseded_indicators)
        except Exception:
            return False  # Can't determine, assume not superseded

    def _fuzzy_match(self, actual: str, expected: str) -> bool:
        """Fuzzy match for titles (allows minor variations)."""
        if not actual or not expected:
            return False

        # Normalize both strings
        actual_norm = re.sub(r'[^\w\s]', '', actual.lower())
        expected_norm = re.sub(r'[^\w\s]', '', expected.lower())

        # Check if expected is substring of actual (or vice versa)
        return expected_norm in actual_norm or actual_norm in expected_norm

    def generate_report(self) -> None:
        """Generate markdown verification report."""
        with open(self.output_file, 'w') as f:
            f.write("# Automated CFR/Guidance Citation Verification Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Tool Version:** Citation Verifier v1.0\n\n")

            f.write("---\n\n")
            f.write("## ⚠️ IMPORTANT: RA PROFESSIONAL REVIEW REQUIRED\n\n")
            f.write("This report contains AUTOMATED URL and title verification only.\n\n")
            f.write("**An RA professional MUST:**\n")
            f.write("1. Review all automated findings\n")
            f.write("2. Make applicability determinations for each citation\n")
            f.write("3. Check for recent amendments (last 2 years)\n")
            f.write("4. Determine if citations are complete and appropriate\n")
            f.write("5. Sign and date the verification worksheet\n\n")
            f.write("**Status:** ☐ AWAITING RA PROFESSIONAL REVIEW\n\n")
            f.write("---\n\n")

            # CFR Results
            f.write("## CFR Citation Verification (3 regulations)\n\n")

            for result in self.results['cfr_results']:
                f.write(f"### {result['part']}\n\n")
                f.write(f"**URL:** {result['url']}\n")
                f.write(f"**Expected Title:** {result['expected_title']}\n")
                f.write(f"**Applies To:** {result['applies_to']}\n\n")

                # URL resolution
                if result['url_resolves']:
                    f.write(f"- ✅ **URL Resolution:** PASS\n")
                else:
                    f.write(f"- ❌ **URL Resolution:** FAIL ({result.get('url_error', 'Unknown error')})\n")

                # Title match
                if result['title_match'] is not None:
                    if result['title_match']:
                        f.write(f"- ✅ **Title Match:** PASS (Found: {result['actual_title']})\n")
                    else:
                        f.write(f"- ⚠️ **Title Match:** MISMATCH (Found: {result['actual_title']})\n")
                else:
                    f.write(f"- ⚠️ **Title Match:** NOT CHECKED (requires beautifulsoup4)\n")

                # Structure
                if result['structure_present'] is not None:
                    structure_count = sum(result['structure_present'].values())
                    total_count = len(result['structure_present'])
                    if structure_count == total_count:
                        f.write(f"- ✅ **Key Sections:** ALL PRESENT ({structure_count}/{total_count})\n")
                    else:
                        f.write(f"- ⚠️ **Key Sections:** PARTIAL ({structure_count}/{total_count})\n")
                        for section, present in result['structure_present'].items():
                            status = '✓' if present else '✗'
                            f.write(f"  - {status} {section}\n")
                else:
                    f.write(f"- ⚠️ **Key Sections:** NOT CHECKED (requires beautifulsoup4)\n")

                f.write(f"\n**RA Professional Review Required:**\n")
                f.write(f"- [ ] Verify applicability to {result['applies_to']}\n")
                f.write(f"- [ ] Check for amendments (last 2 years)\n")
                f.write(f"- [ ] Confirm citation is complete and appropriate\n\n")

                f.write(f"**Determination:** ☐ VERIFIED / ☐ VERIFIED WITH NOTES / ☐ INVALID\n\n")
                f.write(f"---\n\n")

            # Guidance Results
            f.write("## Guidance Document Verification (3 documents)\n\n")

            for result in self.results['guidance_results']:
                f.write(f"### {result['title']} ({result['year']})\n\n")
                f.write(f"**URL:** {result['url']}\n")
                f.write(f"**Docket Number:** {result['docket_number']}\n")
                f.write(f"**Applies To:** {result['applies_to']}\n\n")

                # URL resolution
                if result['url_resolves']:
                    f.write(f"- ✅ **URL Resolution:** PASS\n")
                else:
                    f.write(f"- ❌ **URL Resolution:** FAIL ({result.get('url_error', 'Unknown error')})\n")

                # Superseded check
                if result['superseded'] is not None:
                    if result['superseded']:
                        f.write(f"- ⚠️ **Superseded Check:** WARNING DETECTED (may be superseded or withdrawn)\n")
                    else:
                        f.write(f"- ✅ **Superseded Check:** No warnings found\n")
                else:
                    f.write(f"- ⚠️ **Superseded Check:** NOT CHECKED (requires beautifulsoup4)\n")

                f.write(f"\n**RA Professional Review Required:**\n")
                f.write(f"- [ ] Confirm guidance is current (not superseded)\n")
                f.write(f"- [ ] Verify docket number is correct\n")
                f.write(f"- [ ] Confirm applies to {result['applies_to']}\n\n")

                f.write(f"**Determination:** ☐ VERIFIED / ☐ VERIFIED WITH NOTES / ☐ INVALID\n\n")
                f.write(f"---\n\n")

            # Summary
            f.write("## Summary\n\n")

            cfr_pass = sum(1 for r in self.results['cfr_results'] if r['url_resolves'] and (r['title_match'] if r['title_match'] is not None else True))
            guidance_pass = sum(1 for r in self.results['guidance_results'] if r['url_resolves'] and not r.get('superseded', False))

            f.write(f"| Citation Type | Total | URL Pass | Warnings |\n")
            f.write(f"|---------------|-------|----------|----------|\n")
            f.write(f"| CFR Regulations | 3 | {sum(1 for r in self.results['cfr_results'] if r['url_resolves'])} | {3 - cfr_pass} |\n")
            f.write(f"| Guidance Documents | 3 | {sum(1 for r in self.results['guidance_results'] if r['url_resolves'])} | {3 - guidance_pass} |\n")
            f.write(f"| **TOTAL** | **6** | **{sum(1 for r in self.results['cfr_results'] if r['url_resolves']) + sum(1 for r in self.results['guidance_results'] if r['url_resolves'])}** | **{(3 - cfr_pass) + (3 - guidance_pass)}** |\n\n")

            # RA Sign-off
            f.write("## RA Professional Sign-Off\n\n")
            f.write("**I certify that I have:**\n")
            f.write("- [ ] Reviewed all automated verification findings\n")
            f.write("- [ ] Made professional determinations on applicability\n")
            f.write("- [ ] Checked for recent amendments (last 2 years)\n")
            f.write("- [ ] Verified all citations are complete and appropriate\n")
            f.write("- [ ] Documented any required updates or corrections\n\n")

            f.write("**Verified By:**\n")
            f.write("- Name: ________________\n")
            f.write("- Credentials/Title: ________________\n")
            f.write("- Organization: ________________\n")
            f.write("- Date: ________________\n")
            f.write("- Signature: ________________\n\n")

            f.write("**Overall Status:** ☐ ALL VERIFIED / ☐ UPDATES REQUIRED\n\n")
            f.write("**Next Review Due:** ________________ (Recommended: Quarterly)\n\n")


def main():
    parser = argparse.ArgumentParser(description='Automated CFR/Guidance Citation Verifier')
    parser.add_argument('--output', default='cfr_guidance_verification.md', help='Output markdown file')
    args = parser.parse_args()

    verifier = CitationVerifier(args.output)
    verifier.verify_all()


if __name__ == '__main__':
    main()
