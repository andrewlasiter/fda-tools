#!/usr/bin/env python3
"""
Quick URL pattern validation test for PMA SSED documents.
Tests the hypothesis that 2000s PMAs use single-digit folders (pdf7, not pdf07).
"""

import requests
import time

def construct_ssed_url_corrected(pma_number):
    """
    Corrected URL construction with proper folder naming.

    Key fix: Years 2000-2009 use single-digit folders (pdf7, not pdf07)
    """
    if not pma_number.startswith('P'):
        raise ValueError(f"Invalid PMA number: {pma_number}")

    # Extract year digits
    year = pma_number[1:3]

    # Remove leading zero for 2000s PMAs
    if year.startswith('0') and len(year) == 2:
        year = year[1]  # "07" → "7", "05" → "5"

    base_url = f"https://www.accessdata.fda.gov/cdrh_docs/pdf{year}/"

    # Try multiple filename patterns
    patterns = [
        f"{pma_number}B.pdf",      # Standard uppercase B
        f"{pma_number}b.pdf",      # Lowercase b
        f"{pma_number.lower()}b.pdf",  # All lowercase
    ]

    return base_url, patterns


def test_url(pma_number):
    """Test if URL is accessible."""
    base_url, patterns = construct_ssed_url_corrected(pma_number)

    for pattern in patterns:
        url = base_url + pattern
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                return {'success': True, 'url': url, 'pattern': pattern}
        except Exception:
            continue

    return {'success': False, 'url': None, 'pattern': None}


# Test dataset: Known working PMAs from web search
test_pmas = [
    # 2020s
    ('P240038', 'https://www.accessdata.fda.gov/cdrh_docs/pdf24/P240038B.pdf'),
    ('P230025', 'https://www.accessdata.fda.gov/cdrh_docs/pdf23/P230025B.pdf'),

    # 2010s
    ('P160035', 'https://www.accessdata.fda.gov/cdrh_docs/pdf16/P160035B.pdf'),
    ('P170019', 'https://www.accessdata.fda.gov/cdrh_docs/pdf17/p170019b.pdf'),
    ('P170019S029', 'https://www.accessdata.fda.gov/cdrh_docs/pdf17/P170019S029B.pdf'),

    # 2000s - THE CRITICAL TEST CASES
    ('P070004', 'https://www.accessdata.fda.gov/cdrh_docs/pdf7/p070004b.pdf'),
    ('P050050', 'https://www.accessdata.fda.gov/cdrh_docs/pdf5/P050050b.pdf'),
    ('P020050', 'https://www.accessdata.fda.gov/cdrh_docs/pdf2/p020050s012b.pdf'),  # Note: supplement in example
]

print("=" * 80)
print("PMA URL PATTERN VALIDATION TEST")
print("=" * 80)
print()
print("Testing hypothesis: 2000s PMAs use single-digit folders (pdf7, not pdf07)")
print()

success_count = 0
total_count = 0

for pma_number, expected_url in test_pmas:
    total_count += 1
    print(f"Testing {pma_number}...", end=' ')

    result = test_url(pma_number)

    if result['success']:
        success_count += 1
        print(f"✓ SUCCESS - {result['url']}")
        if result['url'] == expected_url or result['url'] in expected_url:
            print(f"  ✓ Matches expected URL")
        else:
            print(f"  ⚠ Different URL than expected")
            print(f"    Expected: {expected_url}")
    else:
        print(f"✗ FAILED - No working URL found")

    time.sleep(0.5)  # Rate limiting

print()
print("=" * 80)
print(f"RESULTS: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
print("=" * 80)

if success_count / total_count >= 0.80:
    print("✓✓✓ VALIDATION PASSED - Pattern is correct!")
else:
    print("✗✗✗ VALIDATION FAILED - More research needed")
