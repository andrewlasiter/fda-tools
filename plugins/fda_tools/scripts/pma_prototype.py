#!/usr/bin/env python3
"""
PMA Prototype Script - Phase 0 Technical Validation

Purpose:
    Validate technical feasibility of SSED scraping and parsing before Phase 1 investment.
    Test with 17 diverse PMAs from 2000 onwards (scoped per TICKET-002 findings).

Usage:
    python3 pma_prototype.py --validate

Expected Outputs:
    1. ssed_cache/ directory with downloaded PDFs
    2. prototype_results.json - Download and parsing statistics
    3. prototype_report.md - Technical feasibility assessment

Success Criteria:
    - Download success rate >=80% (for 2000+ PMAs)
    - Parsing accuracy >=70% (manual validation of 10 samples)
    - Total runtime <10 minutes for 17 PMAs

Notes:
    - TICKET-002 (2026-02-16) identified that 2000s PMAs use single-digit folders
      (pdf7, not pdf07). Pre-2000 PMAs are excluded as they are not digitized.
    - User-Agent header required for FDA servers.
    - 500ms rate limiting between requests (2 req/sec).

LEGAL NOTICE: WEB SCRAPING COMPLIANCE (SEC-002)
==============================================

This tool accesses publicly available FDA data. Users are responsible for:
1. Ensuring compliance with the Computer Fraud and Abuse Act (CFAA)
2. Respecting FDA's Terms of Service and robots.txt
3. Rate-limiting requests to avoid server overload
4. Seeking legal advice if using for commercial purposes

This tool is intended for research, regulatory intelligence, and compliance
purposes. Misuse may violate federal law. See 18 U.S.C. § 1030 (CFAA).

RECOMMENDED: Use FDA bulk download programs when available:
- openFDA API: https://open.fda.gov/
- FDA PMA Bulk Downloads: https://www.fda.gov/medical-devices/device-approvals-denials-and-clearances/pma-approvals
- FDA Data Dashboard: https://datadashboard.fda.gov/

User-Agent Configuration:
    This script uses centralized User-Agent management from fda_http.py.
    To use honest User-Agent for all requests (may cause 403 errors):

    # ~/.claude/fda-tools.config.toml
    [http]
    honest_ua_only = true
"""

import os
import sys
import json
import time
import requests
import re
from datetime import datetime
from pathlib import Path

# SEC-002 Fix: Import centralized User-Agent management
try:
    # Add parent lib directory to path
    _lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
    if _lib_dir not in sys.path:
        sys.path.insert(0, _lib_dir)

    from fda_http import FDA_WEBSITE_HEADERS, create_session
    _FDA_HTTP_AVAILABLE = True
except ImportError:
    _FDA_HTTP_AVAILABLE = False
    print("WARNING: fda_http module not found. Using fallback User-Agent.")
    print("  For honest UA configuration, install full plugin with fda_http.py")
    print("  See: SEC-002 compliance requirements")
    FDA_WEBSITE_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }


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


# Rate limiting: 500ms between requests (2 req/sec) to avoid abuse detection
RATE_LIMIT_SECONDS = 0.5

# Test dataset: 17 diverse PMAs from 2000 onwards
# TICKET-002 (2026-02-16): Pre-2000 PMAs excluded (not digitized, <5% of relevant devices)
# Selected to represent different years, device types, and complexity
TEST_PMAS = [
    # Recent (2020s) - Modern format
    {'pma_number': 'P200024', 'year': 2020, 'device_type': 'cardiovascular', 'expected_pages': 50},
    {'pma_number': 'P210015', 'year': 2021, 'device_type': 'orthopedic', 'expected_pages': 60},
    {'pma_number': 'P220018', 'year': 2022, 'device_type': 'neurology', 'expected_pages': 45},
    {'pma_number': 'P230025', 'year': 2023, 'device_type': 'radiology', 'expected_pages': 70},

    # 2010s - Mature format
    {'pma_number': 'P170019', 'year': 2017, 'device_type': 'oncology', 'expected_pages': 75},  # Foundation Medicine F1CDx
    {'pma_number': 'P160035', 'year': 2016, 'device_type': 'cardiovascular', 'expected_pages': 55},
    {'pma_number': 'P150009', 'year': 2015, 'device_type': 'orthopedic', 'expected_pages': 50},
    {'pma_number': 'P140011', 'year': 2014, 'device_type': 'neurology', 'expected_pages': 40},

    # 2000s - Transitional format (TICKET-002: uses single-digit folders, e.g. pdf7 not pdf07)
    {'pma_number': 'P100003', 'year': 2010, 'device_type': 'orthopedic', 'expected_pages': 50},
    {'pma_number': 'P070004', 'year': 2007, 'device_type': 'cardiovascular', 'expected_pages': 45},
    {'pma_number': 'P050040', 'year': 2005, 'device_type': 'general', 'expected_pages': 35},
    {'pma_number': 'P030027', 'year': 2003, 'device_type': 'orthopedic', 'expected_pages': 30},

    # Supplements (test URL construction for supplements)
    {'pma_number': 'P170019S029', 'year': 2017, 'device_type': 'oncology_supplement', 'expected_pages': 30},
    {'pma_number': 'P160035S001', 'year': 2016, 'device_type': 'cardiovascular_supplement', 'expected_pages': 25},

    # Edge cases
    {'pma_number': 'P190013', 'year': 2019, 'device_type': 'software', 'expected_pages': 65},  # SaMD
    {'pma_number': 'P180024', 'year': 2018, 'device_type': 'combination', 'expected_pages': 80},  # Combo product
    {'pma_number': 'P240024', 'year': 2024, 'device_type': 'very_recent', 'expected_pages': 50},  # Most recent available
]


def construct_ssed_url(pma_number):
    """
    Construct SSED PDF URL(s) from PMA number.

    TICKET-002 Fix (2026-02-16): 2000s PMAs (P0X####) use single-digit folder
    names (pdf7, not pdf07). This was the root cause of 100% download failure
    in the original implementation.

    Returns a list of candidate URLs to try, ordered by likelihood:
        1. {PMA}B.pdf (uppercase B) - most common
        2. {PMA}b.pdf (lowercase b)
        3. {pma_lower}b.pdf (all lowercase)

    Examples:
        P170019    -> pdf17/P170019B.pdf
        P070004    -> pdf7/P070004B.pdf   (single-digit folder, NOT pdf07)
        P030027    -> pdf3/P030027B.pdf   (single-digit folder, NOT pdf03)
        P170019S029 -> pdf17/P170019S029B.pdf
    """
    if not pma_number.startswith('P'):
        raise ValueError(f"Invalid PMA number format: {pma_number}")

    year = pma_number[1:3]

    # TICKET-002 critical fix: Remove leading zero for 2000s PMAs.
    # FDA uses single-digit folder names: pdf7, pdf5, pdf3 (not pdf07, pdf05, pdf03)
    if year.startswith('0') and len(year) == 2:
        year = year[1]  # "07" -> "7", "05" -> "5", "03" -> "3"

    base_url = f"https://www.accessdata.fda.gov/cdrh_docs/pdf{year}/"

    # Return candidate URLs in order of likelihood (case variations)
    urls = [
        f"{base_url}{pma_number}B.pdf",            # Standard uppercase B
        f"{base_url}{pma_number}b.pdf",            # Lowercase b
        f"{base_url}{pma_number.lower()}b.pdf",    # All lowercase
    ]

    return urls


def download_ssed(pma_number, cache_dir='./ssed_cache/'):
    """
    Download SSED PDF for PMA number with case-variation fallback.

    Tries multiple filename patterns (uppercase B, lowercase b, all lowercase)
    with proper User-Agent headers and rate limiting per TICKET-002 findings.

    Returns:
        dict: {
            'pma_number': 'P170019',
            'success': True,
            'filepath': './ssed_cache/P170019.pdf',
            'url': 'https://...',
            'file_size_kb': 1234,
            'error': None,
            'attempts': 1
        }
    """
    result = {
        'pma_number': pma_number,
        'success': False,
        'filepath': None,
        'url': None,
        'file_size_kb': 0,
        'error': None,
        'attempts': 0
    }

    # Security: Validate cache directory path (FDA-171 / SEC-004 / CWE-22)
    try:
        script_dir = Path(__file__).parent.resolve()
        project_root = script_dir.parent.resolve()
        allowed_dirs = [
            project_root,
            Path.cwd(),
        ]
        validated_cache_dir = str(_validate_path_safety(cache_dir, allowed_dirs))
        cache_dir = validated_cache_dir
    except ValueError as e:
        result['error'] = f"Invalid cache directory: {e}"
        return result

    try:
        # Ensure cache directory exists
        Path(cache_dir).mkdir(parents=True, exist_ok=True)

        # Get candidate URLs (includes single-digit folder fix for 2000s PMAs)
        candidate_urls = construct_ssed_url(pma_number)

        # Try each URL pattern in order
        for url in candidate_urls:
            result['attempts'] += 1
            result['url'] = url

            try:
                # SEC-002 Fix: Use centralized headers from fda_http
                response = requests.get(
                    url,
                    headers=FDA_WEBSITE_HEADERS,
                    timeout=30,
                    allow_redirects=True
                )

                if response.status_code == 200:
                    # Verify it looks like a PDF (not an error page)
                    if len(response.content) > 1000 and response.content[:4] == b'%PDF':
                        filepath = os.path.join(cache_dir, f"{pma_number}.pdf")
                        with open(filepath, 'wb') as f:
                            f.write(response.content)

                        result['success'] = True
                        result['filepath'] = filepath
                        result['file_size_kb'] = len(response.content) // 1024
                        return result

                # Rate limiting between attempts
                time.sleep(RATE_LIMIT_SECONDS)

            except requests.exceptions.Timeout:
                result['error'] = f"Timeout on {url}"
                time.sleep(RATE_LIMIT_SECONDS)
                continue
            except requests.exceptions.ConnectionError:
                result['error'] = f"Connection error on {url}"
                time.sleep(RATE_LIMIT_SECONDS)
                continue

        # All patterns exhausted
        if result['error'] is None:
            result['error'] = f"HTTP 404 on all {len(candidate_urls)} URL patterns"

    except Exception as e:
        result['error'] = str(e)

    return result


def parse_ssed_basic(pdf_path):
    """
    Basic SSED parsing to validate text extraction feasibility.

    Uses pdfplumber if available, falls back to basic checks if not.

    Returns:
        dict: {
            'text_extractable': True,
            'page_count': 50,
            'char_count': 100000,
            'sections_found': ['General Information', 'Indications', 'Clinical Studies'],
            'clinical_data_present': True,
            'enrollment_found': '300 patients',
            'parsing_notes': 'Modern format, high quality text extraction'
        }
    """
    result = {
        'text_extractable': False,
        'page_count': 0,
        'char_count': 0,
        'sections_found': [],
        'clinical_data_present': False,
        'enrollment_found': None,
        'parsing_notes': ''
    }

    try:
        # Try importing pdfplumber (optional dependency for prototype)
        try:
            import pdfplumber
            pdf_library = 'pdfplumber'
        except ImportError:
            # Fallback: use PyPDF2 if available
            try:
                from PyPDF2 import PdfReader
                pdf_library = 'PyPDF2'
            except ImportError:
                result['parsing_notes'] = 'No PDF library available (install pdfplumber or PyPDF2)'
                return result

        # Extract text based on available library
        text = ""
        if pdf_library == 'pdfplumber':
            with pdfplumber.open(pdf_path) as pdf:
                result['page_count'] = len(pdf.pages)
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text
        else:  # PyPDF2
            reader = PdfReader(pdf_path)
            result['page_count'] = len(reader.pages)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text

        result['char_count'] = len(text)
        result['text_extractable'] = len(text) > 1000  # At least 1000 chars extracted

        # Identify common SSED sections
        section_patterns = {
            'General Information': r'I\.\s+GENERAL INFORMATION',
            'Indications': r'II\.\s+INDICATIONS FOR USE',
            'Device Description': r'III\.\s+DEVICE DESCRIPTION',
            'Clinical Studies': r'(?:VII|VIII)\.\s+CLINICAL STUDIES',
            'Conclusions': r'(?:XI|XII|XIII)\.\s+CONCLUSIONS',
        }

        for section_name, pattern in section_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                result['sections_found'].append(section_name)

        # Check for clinical data
        if 'Clinical Studies' in result['sections_found']:
            result['clinical_data_present'] = True

            # Try to extract enrollment
            enrollment_patterns = [
                r'[Nn]=\s*(\d+)\s+(?:patients|subjects)',
                r'(\d+)\s+patients?\s+(?:were\s+)?enrolled',
                r'enrollment\s+of\s+(\d+)',
            ]
            for pattern in enrollment_patterns:
                match = re.search(pattern, text)
                if match:
                    result['enrollment_found'] = f"{match.group(1)} patients"
                    break

        # Assess format quality
        if result['page_count'] > 0:
            avg_chars_per_page = result['char_count'] / result['page_count']
            if avg_chars_per_page > 2000:
                result['parsing_notes'] = 'High quality text extraction (modern PDF)'
            elif avg_chars_per_page > 500:
                result['parsing_notes'] = 'Moderate quality text extraction'
            else:
                result['parsing_notes'] = 'Low quality text extraction (possibly scanned PDF, needs OCR)'

    except Exception as e:
        result['parsing_notes'] = f'Parsing error: {str(e)}'

    return result


def run_validation():
    """
    Run validation on test dataset of 17 PMAs (2000+ only, per TICKET-002 scope).

    Returns:
        dict: Comprehensive results and statistics
    """
    print("=" * 80)
    print("PMA PROTOTYPE VALIDATION - Phase 0 Technical Feasibility Test")
    print("  TICKET-002 corrected: single-digit folders for 2000s, 2000+ scope")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test dataset: {len(TEST_PMAS)} PMAs (2000+ only, per TICKET-002 scope)")
    print()

    results = {
        'test_timestamp': datetime.now().isoformat(),
        'test_pmas_count': len(TEST_PMAS),
        'downloads': [],
        'parsing': [],
        'statistics': {}
    }

    # Phase 1: Download SSEDs
    print("PHASE 1: Downloading SSED PDFs")
    print("-" * 80)

    for i, pma_info in enumerate(TEST_PMAS, 1):
        pma_number = pma_info['pma_number']
        print(f"[{i}/{len(TEST_PMAS)}] Downloading {pma_number} ({pma_info['year']}, {pma_info['device_type']})...", end=' ')

        download_result = download_ssed(pma_number)
        results['downloads'].append({**pma_info, **download_result})

        if download_result['success']:
            print(f"OK ({download_result['file_size_kb']} KB, {download_result['attempts']} attempt(s))")
        else:
            print(f"FAILED ({download_result['error']})")

        # Rate limiting between PMA downloads (additional to per-attempt limiting)
        time.sleep(RATE_LIMIT_SECONDS)

    # Calculate download statistics
    successful_downloads = [d for d in results['downloads'] if d['success']]
    failed_downloads = [d for d in results['downloads'] if not d['success']]

    print()
    print("Download Statistics:")
    print(f"  Success: {len(successful_downloads)}/{len(TEST_PMAS)} ({len(successful_downloads)/len(TEST_PMAS)*100:.1f}%)")
    print(f"  Failed:  {len(failed_downloads)}/{len(TEST_PMAS)} ({len(failed_downloads)/len(TEST_PMAS)*100:.1f}%)")
    print(f"  Total size: {sum(d['file_size_kb'] for d in successful_downloads) / 1024:.1f} MB")
    print()

    # Phase 2: Parse SSEDs
    print("PHASE 2: Parsing SSED PDFs")
    print("-" * 80)

    for i, download_result in enumerate(results['downloads'], 1):
        if not download_result['success']:
            continue

        pma_number = download_result['pma_number']
        print(f"[{i}/{len(TEST_PMAS)}] Parsing {pma_number}...", end=' ')

        parse_result = parse_ssed_basic(download_result['filepath'])
        results['parsing'].append({
            'pma_number': pma_number,
            'year': download_result['year'],
            'device_type': download_result['device_type'],
            **parse_result
        })

        if parse_result['text_extractable']:
            sections = len(parse_result['sections_found'])
            enrollment = parse_result['enrollment_found'] or 'N/A'
            print(f"✓ {sections} sections, {parse_result['page_count']} pages, enrollment={enrollment}")
        else:
            print(f"✗ {parse_result['parsing_notes']}")

    # Calculate parsing statistics
    parseable = [p for p in results['parsing'] if p['text_extractable']]
    clinical_data_found = [p for p in results['parsing'] if p['clinical_data_present']]
    enrollment_extracted = [p for p in results['parsing'] if p['enrollment_found']]

    print()
    print("Parsing Statistics:")
    print(f"  Text extractable: {len(parseable)}/{len(results['parsing'])} ({len(parseable)/len(results['parsing'])*100:.1f}%)")
    print(f"  Clinical data found: {len(clinical_data_found)}/{len(results['parsing'])} ({len(clinical_data_found)/len(results['parsing'])*100:.1f}%)")
    print(f"  Enrollment extracted: {len(enrollment_extracted)}/{len(results['parsing'])} ({len(enrollment_extracted)/len(results['parsing'])*100:.1f}%)")
    print()

    # Section detection summary
    all_sections = {}
    for p in results['parsing']:
        for section in p['sections_found']:
            all_sections[section] = all_sections.get(section, 0) + 1

    print("Section Detection Summary:")
    for section, count in sorted(all_sections.items(), key=lambda x: -x[1]):
        print(f"  {section}: {count}/{len(results['parsing'])} ({count/len(results['parsing'])*100:.1f}%)")
    print()

    # Overall statistics
    results['statistics'] = {
        'download_success_rate': len(successful_downloads) / len(TEST_PMAS),
        'parsing_success_rate': len(parseable) / len(results['parsing']) if results['parsing'] else 0,
        'clinical_data_detection_rate': len(clinical_data_found) / len(results['parsing']) if results['parsing'] else 0,
        'enrollment_extraction_rate': len(enrollment_extracted) / len(results['parsing']) if results['parsing'] else 0,
        'avg_pages': sum(p['page_count'] for p in results['parsing']) / len(results['parsing']) if results['parsing'] else 0,
        'total_chars_extracted': sum(p['char_count'] for p in results['parsing']),
    }

    # Save results to JSON
    with open('prototype_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Results saved to: prototype_results.json")

    # Generate markdown report
    generate_report(results)
    print("Report saved to: prototype_report.md")

    # Final assessment
    print()
    print("=" * 80)
    print("FINAL ASSESSMENT")
    print("=" * 80)

    download_success = results['statistics']['download_success_rate'] >= 0.80
    parsing_success = results['statistics']['parsing_success_rate'] >= 0.70
    clinical_success = results['statistics']['clinical_data_detection_rate'] >= 0.70

    print(f"Download Success Rate: {results['statistics']['download_success_rate']*100:.1f}% (target: ≥80%) {'✓ PASS' if download_success else '✗ FAIL'}")
    print(f"Parsing Success Rate:  {results['statistics']['parsing_success_rate']*100:.1f}% (target: ≥70%) {'✓ PASS' if parsing_success else '✗ FAIL'}")
    print(f"Clinical Detection:    {results['statistics']['clinical_data_detection_rate']*100:.1f}% (target: ≥70%) {'✓ PASS' if clinical_success else '✗ FAIL'}")
    print()

    if download_success and parsing_success and clinical_success:
        print("✓✓✓ VALIDATION PASSED - Proceed with Phase 1 implementation")
        recommendation = "PROCEED"
    elif download_success and parsing_success:
        print("✓✓ PARTIAL VALIDATION - Proceed with caution, clinical data extraction needs work")
        recommendation = "PROCEED_WITH_CAUTION"
    else:
        print("✗✗✗ VALIDATION FAILED - Significant technical challenges, reconsider approach")
        recommendation = "RECONSIDER"

    print()
    print(f"Recommendation: {recommendation}")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    return results


def generate_report(results):
    """Generate markdown report from validation results."""

    report = f"""# PMA Prototype Validation Report

**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Test Dataset:** {results['test_pmas_count']} diverse PMAs (2000-2024, scoped per TICKET-002)
**URL Pattern:** TICKET-002 corrected (single-digit folders for 2000s PMAs)

---

## Executive Summary

This validation test assesses the technical feasibility of SSED PDF scraping and parsing for Phase 1 PMA Intelligence implementation. Scope is limited to PMAs from 2000 onwards per TICKET-002 CONDITIONAL GO decision (pre-2000 PMAs are not digitized).

**Key Metrics:**
- Download Success Rate: **{results['statistics']['download_success_rate']*100:.1f}%** (target: ≥80%)
- Parsing Success Rate: **{results['statistics']['parsing_success_rate']*100:.1f}%** (target: ≥70%)
- Clinical Data Detection: **{results['statistics']['clinical_data_detection_rate']*100:.1f}%** (target: ≥70%)
- Enrollment Extraction: **{results['statistics']['enrollment_extraction_rate']*100:.1f}%**

---

## Download Results

| PMA Number | Year | Device Type | Status | File Size | Error |
|------------|------|-------------|--------|-----------|-------|
"""

    for d in results['downloads']:
        status = '✓' if d['success'] else '✗'
        file_size = f"{d['file_size_kb']} KB" if d['success'] else 'N/A'
        error = d['error'] or '-'
        report += f"| {d['pma_number']} | {d['year']} | {d['device_type']} | {status} | {file_size} | {error} |\n"

    report += f"""
**Summary:**
- Successful: {len([d for d in results['downloads'] if d['success']])}/{results['test_pmas_count']}
- Failed: {len([d for d in results['downloads'] if not d['success']])}/{results['test_pmas_count']}
- Total Downloaded: {sum(d['file_size_kb'] for d in results['downloads'] if d['success']) / 1024:.1f} MB

---

## Parsing Results

| PMA Number | Pages | Chars | Sections Found | Clinical Data | Enrollment | Notes |
|------------|-------|-------|----------------|---------------|------------|-------|
"""

    for p in results['parsing']:
        sections = ', '.join(p['sections_found'][:3]) if p['sections_found'] else 'None'
        clinical = '✓' if p['clinical_data_present'] else '✗'
        enrollment = p['enrollment_found'] or '-'
        report += f"| {p['pma_number']} | {p['page_count']} | {p['char_count']:,} | {sections} | {clinical} | {enrollment} | {p['parsing_notes'][:30]} |\n"

    report += f"""
**Summary:**
- Text extractable: {len([p for p in results['parsing'] if p['text_extractable']])}/{len(results['parsing'])}
- Clinical data found: {len([p for p in results['parsing'] if p['clinical_data_present']])}/{len(results['parsing'])}
- Enrollment extracted: {len([p for p in results['parsing'] if p['enrollment_found']])}/{len(results['parsing'])}
- Average pages: {results['statistics']['avg_pages']:.1f}
- Total characters extracted: {results['statistics']['total_chars_extracted']:,}

---

## Section Detection Analysis

Common SSED sections successfully detected:

"""

    all_sections = {}
    for p in results['parsing']:
        for section in p['sections_found']:
            all_sections[section] = all_sections.get(section, 0) + 1

    for section, count in sorted(all_sections.items(), key=lambda x: -x[1]):
        pct = count / len(results['parsing']) * 100 if results['parsing'] else 0
        report += f"- **{section}**: {count}/{len(results['parsing'])} ({pct:.1f}%)\n"

    report += """
---

## Validation Criteria Assessment

| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
"""

    download_success = results['statistics']['download_success_rate'] >= 0.80
    parsing_success = results['statistics']['parsing_success_rate'] >= 0.70
    clinical_success = results['statistics']['clinical_data_detection_rate'] >= 0.70

    report += f"| Download Success Rate | ≥80% | {results['statistics']['download_success_rate']*100:.1f}% | {'✓ PASS' if download_success else '✗ FAIL'} |\n"
    report += f"| Parsing Success Rate | ≥70% | {results['statistics']['parsing_success_rate']*100:.1f}% | {'✓ PASS' if parsing_success else '✗ FAIL'} |\n"
    report += f"| Clinical Detection Rate | ≥70% | {results['statistics']['clinical_data_detection_rate']*100:.1f}% | {'✓ PASS' if clinical_success else '✗ FAIL'} |\n"

    report += """
---

## Recommendations

"""

    if download_success and parsing_success and clinical_success:
        report += """### ✓✓✓ VALIDATION PASSED

**Recommendation:** Proceed with Phase 1 implementation (220-300 hours)

**Rationale:**
- SSED download mechanism is reliable (≥80% success rate)
- Text extraction works well across different PDF formats
- Clinical data detection is feasible with regex patterns
- All validation criteria met

**Next Steps:**
1. Recruit 2-3 pilot users for beta testing
2. Begin Week 1 implementation (PMA API integration)
3. Allocate 8-10 weeks for Phase 1 completion
"""
    elif download_success and parsing_success:
        report += """### ✓✓ PARTIAL VALIDATION

**Recommendation:** Proceed with Phase 1, but focus on data acquisition over clinical intelligence

**Rationale:**
- SSED download and basic parsing work well
- Clinical data extraction needs refinement
- May require manual review for clinical trial details

**Next Steps:**
1. Proceed with PMA API integration and SSED scraping
2. Start with basic competitive intelligence (approval timelines, product codes)
3. Defer advanced clinical trial intelligence to Phase 2
4. Gather user feedback on most valuable data points
"""
    else:
        report += """### ✗✗✗ VALIDATION FAILED

**Recommendation:** Reconsider technical approach or defer PMA support

**Issues Identified:**
- SSED download failures exceed acceptable threshold
- Text extraction quality insufficient for automated parsing
- Consider alternative approaches or postpone PMA support

**Alternative Approaches:**
1. Focus on PMA API data only (no SSED parsing)
2. Investigate FDA data partnerships for better data access
3. Build manual upload workflow for client-provided SSEDs
4. Defer PMA support until FDA improves data accessibility
"""

    report += """
---

## Technical Notes

**PDF Libraries Tested:**
- pdfplumber (preferred): High-quality text and table extraction
- PyPDF2 (fallback): Basic text extraction

**Parsing Challenges Identified:**
1. Older PMAs (pre-2000) may be scanned PDFs requiring OCR
2. Section numbering varies (Roman numerals I-XII or I-XV)
3. Clinical trial tables have inconsistent formats
4. Enrollment numbers appear in various contexts (need better regex)

**Recommended Improvements for Phase 1:**
1. Add OCR fallback for scanned PDFs (tesseract)
2. Build more robust section detection (multiple patterns per section)
3. Improve clinical data regex patterns (test with 50+ SSEDs)
4. Add table extraction capability (pdfplumber.Table)

---

**END OF REPORT**
"""

    with open('prototype_report.md', 'w') as f:
        f.write(report)


if __name__ == '__main__':
    if '--validate' in sys.argv:
        results = run_validation()
    else:
        print("PMA Prototype Script - Phase 0 Technical Validation")
        print("  (TICKET-002 corrected: single-digit folders, 2000+ scope)")
        print()
        print("Usage:")
        print("  python3 pma_prototype.py --validate")
        print()
        print("This will:")
        print("  1. Download 17 diverse SSED PDFs (2000+) to ./ssed_cache/")
        print("  2. Parse each PDF to extract basic information")
        print("  3. Generate prototype_results.json with detailed results")
        print("  4. Generate prototype_report.md with feasibility assessment")
        print()
        print("Expected runtime: 5-10 minutes (includes 500ms rate limiting)")
        print()
        print("Required Python packages:")
        print("  - requests")
        print("  - pdfplumber (recommended) or PyPDF2 (fallback)")
        print()
        print("Install with: pip install requests pdfplumber")
