#!/usr/bin/env python3
"""
FDA 510(k) Batch Fetch Tool

Filters the FDA device catalog and downloads 510(k) PDF documents.
Adapted from 510BAtchFetch Working2.py with CLI argument support for non-interactive use.

Usage:
    # Non-interactive mode (all filters via CLI):
    python batchfetch.py --date-range pmn96cur --years 2020-2025 --product-codes KGN,DXY

    # Interactive mode (original behavior):
    python batchfetch.py --interactive

    # Mixed mode (some filters via CLI, rest interactive):
    python batchfetch.py --date-range pmn96cur --years 2024

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
- FDA 510(k) Bulk Downloads: https://www.fda.gov/medical-devices/510k-clearances/downloadable-510k-files
- FDA Data Dashboard: https://datadashboard.fda.gov/

User-Agent Configuration:
    This script uses centralized User-Agent management from fda_http.py.
    To use honest User-Agent for all requests (may cause 403 errors):

    # ~/.claude/fda-tools.config.toml
    [http]
    honest_ua_only = true
"""

import os
import re
import sys
import csv
import time
import json
import math
import shutil
import random
import argparse
import requests
import zipfile
import textwrap
import numpy as np
import pandas as pd
import concurrent.futures
from io import BytesIO
from tqdm import tqdm
from datetime import datetime
from collections import defaultdict
from itertools import zip_longest
from threading import Lock
from colorama import init, Fore, Style

# Shared HTTP utilities (SEC-002 fix)
try:
    from fda_http import create_session, FDA_WEBSITE_HEADERS, get_headers
    _FDA_HTTP_AVAILABLE = True
except ImportError:
    _FDA_HTTP_AVAILABLE = False
    print("=" * 80)
    print("WARNING: fda_http module not found. User-Agent configuration unavailable.")
    print("  Install the full plugin to enable honest UA and configuration options.")
    print("  See: plugins/fda_tools/scripts/fda_http.py")
    print("  For compliance, see SEC-002 requirements in security documentation.")
    print("=" * 80)
    print()

    FDA_WEBSITE_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    def create_session(api_mode=False, purpose=None):
        session = requests.Session()
        session.headers.update(FDA_WEBSITE_HEADERS)
        return session

    def get_headers(purpose='website'):
        return FDA_WEBSITE_HEADERS.copy()

# FDA-12: Cross-process rate limiter
try:
    from fda_tools.lib.cross_process_rate_limiter import CrossProcessRateLimiter  # type: ignore
    _CROSS_PROCESS_LIMITER_AVAILABLE = True
except ImportError:
    _CROSS_PROCESS_LIMITER_AVAILABLE = False

# Initialize colorama
init(autoreset=True)

# Auto-detect Tesseract
def detect_tesseract():
    tesseract_cmd = shutil.which('tesseract')
    if not tesseract_cmd:
        for path in [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/opt/homebrew/bin/tesseract',
        ]:
            if os.path.exists(path):
                tesseract_cmd = path
                break
    return tesseract_cmd

try:
    import pytesseract
    tesseract_cmd = detect_tesseract()
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
except ImportError:
    pytesseract = None

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

try:
    from PyPDF2 import PdfReader, PdfWriter
except ImportError:
    PdfReader = None

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
except ImportError:
    canvas = None

# FDA zip file sources
zip_dict = {
    "pmnlstmn": "https://www.accessdata.fda.gov/premarket/ftparea/pmnlstmn.zip",
    "pmn96cur": "https://www.accessdata.fda.gov/premarket/ftparea/pmn96cur.zip",
    "pmn9195": "https://www.accessdata.fda.gov/premarket/ftparea/pmn9195.zip",
    "pmn8690": "https://www.accessdata.fda.gov/premarket/ftparea/pmn8690.zip",
    "pmn8185": "https://www.accessdata.fda.gov/premarket/ftparea/pmn8185.zip",
    "pmn7680": "https://www.accessdata.fda.gov/premarket/ftparea/pmn7680.zip"
}

zip_descriptions = {
    "pmnlstmn": "Most current month available",
    "pmn96cur": "1996-current",
    "pmn9195": "1991-1995",
    "pmn8690": "1986-1990",
    "pmn8185": "1981-1985",
    "pmn7680": "1976-1980"
}

# Review Advisory Committee descriptions
review_advisory_committee_descriptions = {
    "AN": "Anesthesiology",
    "CV": "Cardiovascular",
    "CH": "Clinical Chemistry",
    "DE": "Dental",
    "EN": "Ear, Nose, Throat",
    "GU": "Gastroenterology, Urology",
    "HO": "General Hospital",
    "HE": "Hematology",
    "IM": "Immunology",
    "MG": "Medical Genetics",
    "MI": "Microbiology",
    "NE": "Neurology",
    "OB": "Obstetrics/Gynecology",
    "OP": "Ophthalmic",
    "OR": "Orthopedic",
    "PA": "Pathology",
    "PM": "Physical Medicine",
    "RA": "Radiology",
    "SU": "General, Plastic Surgery",
    "TX": "Clinical Toxicology"
}

# Decision Code descriptions
decision_code_descriptions = {
    "SEKD": "Substantially Equivalent - Kit with Drugs",
    "SESD": "Substantially Equivalent with Drug",
    "SESE": "Substantially Equivalent",
    "SESK": "Substantially Equivalent - Kit",
    "SESP": "Substantially Equivalent - Postmarket Surveillance Required",
    "SESU": "Substantially Equivalent - With Limitations",
    "SESR": "Potential Recall",
    "DENG": "De Novo Granted",
    "KD": "Substantially Equivalent - Kit with Drugs",
    "PR": "Substantially Equivalent - Proposed Recision",
    "PT": "Substantially Equivalent - Subject to Tracking & PMS",
    "RN": "Substantially Equivalent - Rescind Non-Substantial Equivalence",
    "SA": "Substantially Equivalent - Awaiting Device Approval",
    "SD": "Substantially Equivalent with Drug",
    "SE": "Substantially Equivalent",
    "SF": "Substantially Equivalent - Awaiting Future Policies",
    "SI": "Substantially Equivalent - Market after Inspection",
    "SK": "Substantially Equivalent - Kit",
    "SN": "Substantially Equivalent for Some Indications",
    "SP": "Substantially Equivalent - PostMarket Surveillance Required",
    "ST": "Substantially Equivalent - Subject to Tracking Reg.",
    "SU": "Substantially Equivalent - With Limitations",
    "SW": "Substantially Equivalent - Awaiting Drug Approval"
}


def parse_args():
    parser = argparse.ArgumentParser(
        description='FDA 510(k) Batch Fetch Tool — Filter the FDA catalog and download 510(k) PDF documents.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all 2024 submissions for product code KGN:
  python batchfetch.py --date-range pmn96cur --years 2024 --product-codes KGN

  # Multiple date ranges, specific decision codes:
  python batchfetch.py --date-range pmn96cur,pmnlstmn --years 2020-2025 --decision-codes SESE

  # Filter by applicant and committee:
  python batchfetch.py --date-range pmn96cur --years 2023 --applicants "MEDTRONIC;ABBOTT" --committees CV

  # Interactive mode:
  python batchfetch.py --interactive

  # Save Excel workbook:
  python batchfetch.py --date-range pmn96cur --years 2024 --product-codes KGN --save-excel

  # Check installed dependencies:
  python batchfetch.py --check-deps

Available date range keys:
  pmnlstmn  - Most current month available
  pmn96cur  - 1996-current
  pmn9195   - 1991-1995
  pmn8690   - 1986-1990
  pmn8185   - 1981-1985
  pmn7680   - 1976-1980
        """
    )
    parser.add_argument('--date-range', type=str, default=None,
                        help='Comma-separated pmn keys (e.g., "pmn96cur,pmnlstmn")')
    parser.add_argument('--years', type=str, default=None,
                        help='Comma-separated years or ranges (e.g., "2020-2025" or "2020,2022,2024")')
    parser.add_argument('--submission-types', type=str, default=None,
                        help='Comma-separated submission types to include')
    parser.add_argument('--committees', type=str, default=None,
                        help='Comma-separated advisory committee codes (e.g., "CV,OR")')
    parser.add_argument('--decision-codes', type=str, default=None,
                        help='Comma-separated decision codes (e.g., "SESE,SESK")')
    parser.add_argument('--applicants', type=str, default=None,
                        help='Semicolon-separated applicant names (e.g., "MEDTRONIC;ABBOTT")')
    parser.add_argument('--product-codes', type=str, default=None,
                        help='Comma-separated product codes (e.g., "KGN,DXY")')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Directory for 510k_download.csv and Excel output')
    parser.add_argument('--download-dir', type=str, default=None,
                        help='Directory for downloaded PDFs (default: ./510ks)')
    parser.add_argument('--data-dir', type=str, default=None,
                        help='Directory for FDA database files (default: ./fda_data)')
    parser.add_argument('--save-excel', action='store_true',
                        help='Save Applicant/ProductCode tables to Excel workbook')
    parser.add_argument('--interactive', action='store_true',
                        help='Force interactive mode (prompts for all filters)')
    parser.add_argument('--no-download', action='store_true',
                        help='Skip PDF download step (only filter and save CSV)')
    parser.add_argument('--delay', type=float, default=30.0,
                        help='Delay between downloads in seconds (default: 30)')
    parser.add_argument('--from-manifest', type=str, default=None,
                        help='Path to gap_manifest.csv from /fda:gap-analysis — download only need_download rows')
    parser.add_argument('--resume', action='store_true',
                        help='Resume interrupted download using download_progress.json checkpoint file')
    parser.add_argument('--check-deps', action='store_true',
                        help='Check installed dependencies and exit (shows which features are available)')
    return parser.parse_args()


def load_manifest(manifest_path):
    """Load a gap manifest CSV from /fda:gap-analysis and filter to need_download rows.

    Returns a list of K-numbers that need downloading.
    """
    knumbers = []
    with open(manifest_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get('STATUS', row.get('status', ''))
            if status.strip().lower() == 'need_download':
                knum = row.get('KNUMBER', row.get('knumber', row.get('K-number', '')))
                if knum:
                    knumbers.append(knum.strip())
    return knumbers


def load_progress(output_dir):
    """Load download progress checkpoint file for --resume support.

    Returns dict with completed/failed/skipped K-number sets.
    """
    progress_path = os.path.join(output_dir, 'download_progress.json')
    if os.path.exists(progress_path):
        with open(progress_path, 'r') as f:
            data = json.load(f)
        return {
            'completed': set(data.get('completed', [])),
            'failed': set(data.get('failed', [])),
            'skipped': set(data.get('skipped', [])),
        }
    return {'completed': set(), 'failed': set(), 'skipped': set()}


def save_progress(output_dir, progress):
    """Save download progress atomically (temp file + rename)."""
    progress_path = os.path.join(output_dir, 'download_progress.json')
    tmp_path = progress_path + '.tmp'
    data = {
        'completed': sorted(progress['completed']),
        'failed': sorted(progress['failed']),
        'skipped': sorted(progress['skipped']),
        'last_updated': datetime.now().isoformat(),
    }
    with open(tmp_path, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, progress_path)


def parse_year_list(years_str):
    """Parse year string like '2020-2025' or '2020,2022,2024' into list of ints."""
    year_list = []
    for part in years_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            year_list.extend(range(start, end + 1))
        else:
            year_list.append(int(part))
    return year_list


def sortKey(item):
    product_code, details = item
    _, _, _, _, avg_review_time = details
    return float('inf') if avg_review_time == 'N/A' else float(avg_review_time)


def prompt_user(prompt_message, default_option=None):
    # In non-TTY environments, skip interactive prompts
    if not sys.stdin.isatty():
        if default_option is not None:
            print(f"[Non-TTY] Auto-selecting default for: {prompt_message.strip()[:80]}...")
            return default_option
        else:
            print(f"[Non-TTY] Skipping prompt (no default available): {prompt_message.strip()[:80]}...")
            return ''
    user_input = input(prompt_message).strip()
    if default_option is not None and user_input == '':
        return default_option
    return user_input


def format_review_time_product(value, days):
    if isinstance(days, str) or days == 'N/A':
        return value
    days = int(days)
    if days > 365:
        return f"{Fore.RED}{value}{Style.RESET_ALL}".center(8)
    elif days > 179:
        return f"{Fore.LIGHTYELLOW_EX}{value}{Style.RESET_ALL}".center(8)
    elif days > 89:
        return f"{Fore.YELLOW}{value}{Style.RESET_ALL}".center(8)
    else:
        return f"{Fore.GREEN}{value}{Style.RESET_ALL}".center(8)


def display_table_with_total(df, group_col, col_name, count_col_name, avg_col_name, descriptions=None):
    grouped_df = df.groupby(group_col).agg(
        count=('APPLICANT', 'size'),
        avg_review_time=('REVIEWTIME', 'mean'),
        sum_review_time=('REVIEWTIME', 'sum')
    ).reset_index()

    if grouped_df.empty:
        return grouped_df

    total_count = grouped_df['count'].sum()
    total_sum_review_time = grouped_df['sum_review_time'].sum()
    total_avg_review_time = total_sum_review_time / total_count

    total_row = pd.DataFrame({
        group_col: ["Total"],
        'count': [total_count],
        'avg_review_time': [total_avg_review_time],
        'sum_review_time': [total_sum_review_time]
    })
    grouped_df = pd.concat([grouped_df, total_row])

    if descriptions:
        grouped_df[group_col] = grouped_df[group_col].apply(lambda x: f"{x} = {descriptions[x]}" if x in descriptions else x)

    col_width1 = max(len(col_name), grouped_df[group_col].apply(len).max()) + 5
    col_width2 = max(len(count_col_name), grouped_df['count'].astype(str).str.len().max()) + 2
    col_width3 = max(len(avg_col_name), grouped_df['avg_review_time'].astype(str).str.len().max()) + 2

    header = f"| {col_name:<{col_width1}} | {count_col_name:<{col_width2}} | {avg_col_name:^{col_width3}} |"
    divider = f"+{'-' * (col_width1 + 2)}+{'-' * (col_width2 + 2)}+{'-' * (col_width3 + 2)}+"

    print(divider)
    print(header)
    print(divider)

    for idx, row in grouped_df.iterrows():  # type: ignore
        if row[group_col] == "Total":
            print(divider)
        value1 = f"{idx + 1}. {row[group_col]}" if row[group_col] != "Total" else row[group_col]  # type: ignore
        value2 = row['count']
        value3 = int(round(row['avg_review_time']))  # type: ignore
        value3_colored = format_review_time_product(value3, value3)
        formatted_row = f"| {str(value1):<{col_width1}} | {str(value2):<{col_width2}} | {value3_colored:^{col_width3 + 9}} |"
        print(formatted_row)

    print(divider)
    return grouped_df


def display_product_code_table(product_codes_dict):
    if not product_codes_dict:
        print("No product codes found.")
        return

    col_width1 = max(len("Product Code"), max(len(str(code)) for code in product_codes_dict.keys())) + 2
    col_width2 = max(len("Device Name"), max(len(str(details[0])) for details in product_codes_dict.values())) + 2
    col_width3 = max(len("Class"), max(len(str(details[1])) for details in product_codes_dict.values())) + 2
    col_width4 = max(len("Regulation"), max(len(str(details[2])) for details in product_codes_dict.values())) + 2
    col_width5 = max(len("Total #"), max(len(str(details[3])) for details in product_codes_dict.values())) + 2
    col_width6 = max(len("Review"), max(len(str(details[4])) for details in product_codes_dict.values())) + 2

    header = f"| {'Product Code':^{col_width1}} | {'Device Name':<{col_width2}} | {'Class':^{col_width3}} | {'Regulation':^{col_width4}} | {'Total #':^{col_width5}} | {'Review':^{col_width6}} |"
    divider = f"+{'-' * (col_width1 + 2)}+{'-' * (col_width2 + 2)}+{'-' * (col_width3 + 2)}+{'-' * (col_width4 + 2)}+{'-' * (col_width5 + 2)}+{'-' * (col_width6 + 2)}+"

    print(divider)
    print(header)
    print(divider)

    for product_code, details in product_codes_dict.items():
        device_name, device_class, regulation_number, count, avg_review_time = details
        try:
            if '.' in regulation_number:
                regulation_number_parts = regulation_number.split('.')
                regulation_number = f"{int(regulation_number_parts[0]):03d}.{regulation_number_parts[1].ljust(4, '0')}"
            else:
                regulation_number = f"{int(regulation_number):03d}.0000"
        except (ValueError, TypeError):
            regulation_number = "000.0000"

        avg_review_time_colored = format_review_time_product(avg_review_time, avg_review_time)
        row = f"| {product_code:^{col_width1}} | {device_name:<{col_width2}} | {device_class:^{col_width3}} | {regulation_number:^{col_width4}} | {count:^{col_width5}} | {avg_review_time_colored:^{col_width6 + 9}} |"
        print(row)

    print(divider)


def display_date_range_table(data_dir):
    date_ranges = []
    for idx, key in enumerate(zip_dict.keys(), 1):
        df = process_zip_file(key, data_dir)
        count = df['KNUMBER'].nunique() if not df.empty else 0
        avg_review_time = df['REVIEWTIME'].mean() if not df.empty else 'N/A'
        avg_review_time = int(round(avg_review_time)) if avg_review_time != 'N/A' else 'N/A'
        date_ranges.append((f"{idx}. {zip_descriptions[key]}", count, avg_review_time))

    date_range_df = pd.DataFrame(date_ranges, columns=['Date Range', 'COUNT', 'AVG REVIEW'])  # type: ignore

    total_count = date_range_df['COUNT'].sum()
    total_avg_review_time = (date_range_df['COUNT'] * date_range_df['AVG REVIEW'].replace('N/A', 0)).sum() / total_count
    total_avg_review_time = int(round(total_avg_review_time))

    total_row = pd.DataFrame({
        'Date Range': ['Total'],
        'COUNT': [total_count],
        'AVG REVIEW': [total_avg_review_time]
    })

    date_range_df = pd.concat([date_range_df, total_row], ignore_index=True)

    col_width1 = max(len("Date Range"), date_range_df['Date Range'].astype(str).str.len().max()) + 2
    col_width2 = max(len("COUNT"), date_range_df['COUNT'].astype(str).str.len().max()) + 2
    col_width3 = max(len("AVG REVIEW"), date_range_df['AVG REVIEW'].astype(str).str.len().max()) + 8

    header = f"| {'Date Range':<{col_width1}} | {'COUNT':^{col_width2}} | {'AVG REVIEW':^{col_width3}} |"
    divider = f"+{'-' * (col_width1 + 2)}+{'-' * (col_width2 + 2)}+{'-' * (col_width3 + 2)}+"

    print(divider)
    print(header)
    print(divider)

    for idx, row in date_range_df.iterrows():
        value1 = row['Date Range']
        value2 = row['COUNT']
        value3 = row['AVG REVIEW']
        value3_colored = format_review_time_product(value3, value3)
        formatted_row = f"| {str(value1):<{col_width1}} | {str(value2):^{col_width2}} | {value3_colored:^{col_width3}} |"

        if value1 == 'Total':
            print(divider)
        print(formatted_row)
        if value1 == 'Total':
            print(divider)

    return date_range_df


def process_zip_file(key, data_dir):
    key = key.strip()
    zip_url = zip_dict[key]

    headers = dict(FDA_WEBSITE_HEADERS)
    headers['Referer'] = 'https://www.accessdata.fda.gov/'

    extract_path = data_dir
    file_path = os.path.join(extract_path, key + ".txt")

    # Check if file already exists and is fresh (< 5 days old)
    if os.path.exists(file_path):
        file_age_days = (time.time() - os.path.getmtime(file_path)) / 86400
        if file_age_days < 5:
            print(f"File found! (<5 days old): {file_path}")
            df = pd.read_csv(file_path, sep="|", encoding='ISO-8859-1')
            df["APPLICANT"] = df["APPLICANT"].str.upper()
            df["DATERECEIVED"] = pd.to_datetime(df["DATERECEIVED"])
            df["DECISIONDATE"] = pd.to_datetime(df["DECISIONDATE"])
            df["REVIEWTIME"] = (df["DECISIONDATE"] - df["DATERECEIVED"]).dt.days
            return df

    try:
        response = requests.get(zip_url, headers=headers, allow_redirects=True, timeout=60)
        response.raise_for_status()
        zip_file = zipfile.ZipFile(BytesIO(response.content))
    except (requests.exceptions.RequestException, zipfile.BadZipFile) as e:
        print(f"Failed to download or open zip file {zip_url}: {e}")
        # Fall back to existing file if present
        if os.path.exists(file_path):
            print(f"Using existing (possibly stale) file: {file_path}")
            df = pd.read_csv(file_path, sep="|", encoding='ISO-8859-1')
            df["APPLICANT"] = df["APPLICANT"].str.upper()
            df["DATERECEIVED"] = pd.to_datetime(df["DATERECEIVED"])
            df["DECISIONDATE"] = pd.to_datetime(df["DECISIONDATE"])
            df["REVIEWTIME"] = (df["DECISIONDATE"] - df["DATERECEIVED"]).dt.days
            return df
        return pd.DataFrame()

    try:
        zip_file.extractall(path=extract_path)
    except PermissionError:
        print(f"Permission denied: unable to write to {extract_path}. Please check permissions.")
        return pd.DataFrame()

    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist after extraction.")
        return pd.DataFrame()

    df = pd.read_csv(file_path, sep="|", encoding='ISO-8859-1')
    df["APPLICANT"] = df["APPLICANT"].str.upper()
    df["DATERECEIVED"] = pd.to_datetime(df["DATERECEIVED"])
    df["DECISIONDATE"] = pd.to_datetime(df["DECISIONDATE"])
    df["REVIEWTIME"] = (df["DECISIONDATE"] - df["DATERECEIVED"]).dt.days
    return df


def ocr_from_pdf(file_path):
    if convert_from_path is None or pytesseract is None:
        print("Warning: pytesseract or pdf2image not available. Skipping OCR.")
        return ""
    images = convert_from_path(file_path)
    text = '\n'.join(pytesseract.image_to_string(image) for image in images)
    return text


def select_date_range_interactive(data_dir):
    date_range_df = display_date_range_table(data_dir)
    option_numbers = prompt_user(
        "Enter the numbers separated by commas (or type 'all' to include all, leave blank for default 1 & 2): ",
        default_option='1,2'
    )

    if option_numbers.lower() == 'all':
        return list(zip_dict.keys())
    elif option_numbers == '':
        return list(zip_dict.keys())[:2]
    else:
        return [list(zip_dict.keys())[int(num) - 1] for num in option_numbers.split(',')]


def select_years_interactive(selected_keys):
    if "pmn96cur" in selected_keys:
        years = prompt_user("Enter the year (received by the FDA) separated by commas or ranges (e.g., 2001,2005 or 2001-2005): ", default_option='')
        if years.strip():
            return parse_year_list(years)
    return []


def select_submission_types_interactive(df):
    submission_type_df = display_table_with_total(df, 'TYPE', 'Submission Type', 'COUNT', 'AVG REVIEW')

    option_numbers = prompt_user(
        "Enter the numbers of the submission types you want to include separated by commas (or leave blank to include all): ",
        default_option=''
    ).split(',')

    if option_numbers and option_numbers[0] != '':
        selected_types = [submission_type_df.iloc[int(num) - 1]['TYPE'] for num in option_numbers]
        return selected_types
    else:
        return []


def select_review_committees_interactive(df):
    review_committees_df = display_table_with_total(df, 'REVIEWADVISECOMM', 'Advisory Committees', 'COUNT', 'AVG REVIEW', review_advisory_committee_descriptions)

    option_numbers = prompt_user(
        "Enter the two letter code(s) of the Review Advisory Committees you want to include separated by commas (or leave blank to include all): ",
        default_option=''
    ).split(',')

    selected_committees = []
    if option_numbers and option_numbers[0].strip().upper() != '':
        for num in option_numbers:
            num = num.strip().upper()
            if num.isdigit():
                selected_committees.append(review_committees_df.iloc[int(num) - 1]['REVIEWADVISECOMM'])
            elif num in review_advisory_committee_descriptions:
                selected_committees.append(num)
            else:
                print(f"Invalid input: {num}. Please enter valid advisory committee codes.")
    else:
        selected_committees = list(review_advisory_committee_descriptions.keys())

    return selected_committees


def select_decision_codes_interactive(df):
    unique_decision_codes = df["DECISION"].unique()
    available_decision_codes = {code: decision_code_descriptions[code] for code in unique_decision_codes if code in decision_code_descriptions}

    if not available_decision_codes:
        print("No matching decision codes found.")
        return []

    decision_codes_df = display_table_with_total(df, 'DECISION', 'Decision Codes', 'COUNT', 'AVG REVIEW', available_decision_codes)

    option_numbers = prompt_user(
        "Enter the decision codes you want to include separated by commas (or leave blank to include all): ",
        default_option=''
    ).split(',')

    selected_codes = []
    if option_numbers and option_numbers[0] != '':
        for num in option_numbers:
            num = num.strip().upper()
            if num.isdigit():
                selected_codes.append(decision_codes_df.iloc[int(num) - 1]['DECISION'])
            elif num in available_decision_codes:
                selected_codes.append(num)
            else:
                print(f"Invalid input: {num}. Please enter valid indices or decision codes.")
    else:
        selected_codes = list(available_decision_codes.keys())

    return selected_codes


def select_applicants_interactive():
    applicants = prompt_user(
        "Enter the Applicants separated by semicolon (leave blank to download all): ",
        default_option=''
    ).split(';')
    return [applicant.strip().upper() for applicant in applicants if applicant.strip()]


def wrap_text(text, width):
    if len(text) > width:
        return '\n'.join(textwrap.wrap(text, width))
    else:
        return text


def format_review_time(days, col_width):
    if days > 365:
        return f"{Fore.RED}{days} Days{Style.RESET_ALL}".center(col_width + len(Fore.RED) + len(Style.RESET_ALL))
    elif days > 179:
        return f"{Fore.LIGHTYELLOW_EX}{days} Days{Style.RESET_ALL}".center(col_width + len(Fore.LIGHTYELLOW_EX) + len(Style.RESET_ALL))
    elif days > 89:
        return f"{Fore.YELLOW}{days} Days{Style.RESET_ALL}".center(col_width + len(Fore.YELLOW) + len(Style.RESET_ALL))
    else:
        return f"{Fore.GREEN}{days} Days{Style.RESET_ALL}".center(col_width + len(Fore.GREEN) + len(Style.RESET_ALL))


def display_applicants_table(df, applicant_stats):
    unique_applicants = df["APPLICANT"].unique().tolist()
    unique_applicants.sort()

    unique_applicants1 = unique_applicants[::2]
    unique_applicants2 = unique_applicants[1::2]

    applicant_col_width = max(len(applicant) for applicant in unique_applicants) + 2
    count_col_width = max(len("COUNT"), max(len(str(count)) for count in applicant_stats['count'])) + 2
    review_time_col_width = max(len("AVG REVIEW"), max(len(str(int(round(t)))) for t in applicant_stats['avg_review_time'])) + 2

    header_single = f"| {'APPLICANT':<{applicant_col_width}} | {'COUNT':^{count_col_width}} | {'AVG REVIEW':<{review_time_col_width}} |"
    divider_single = f"+{'-' * (applicant_col_width + 2)}+{'-' * (count_col_width + 2)}+{'-' * (review_time_col_width + 2)}+"
    header_double = f"| {'APPLICANT':<{applicant_col_width}} | {'COUNT':^{count_col_width}} | {'AVG REVIEW':<{review_time_col_width}} | {'APPLICANT':<{applicant_col_width}} | {'COUNT':^{count_col_width}} | {'AVG REVIEW':<{review_time_col_width}} |"
    divider_double = f"+{'-' * (applicant_col_width + 2)}+{'-' * (count_col_width + 2)}+{'-' * (review_time_col_width + 2)}+{'-' * (applicant_col_width + 2)}+{'-' * (count_col_width + 2)}+{'-' * (review_time_col_width + 2)}+"

    total_clearances = 0

    if len(unique_applicants) <= 1:
        print("Unique Applicants:")
        print(divider_single)
        print(header_single)
        print(divider_single)
        for applicant in unique_applicants:
            applicant_row = applicant_stats[applicant_stats['APPLICANT'] == applicant].iloc[0]
            count = applicant_row['count']
            avg_review = format_review_time(int(round(applicant_row['avg_review_time'])), review_time_col_width)
            total_clearances += count
            row = f"| {wrap_text(applicant, applicant_col_width):<{applicant_col_width}} | {str(count):^{count_col_width}} | {avg_review:<{review_time_col_width}} |"
            print(row)
        print(divider_single)
    else:
        print("Unique Applicants:")
        print(divider_double)
        print(header_double)
        print(divider_double)
        for applicant1, applicant2 in zip_longest(unique_applicants1, unique_applicants2, fillvalue=''):
            if applicant1:
                applicant1_row = applicant_stats[applicant_stats['APPLICANT'] == applicant1].iloc[0]
                count1 = applicant1_row['count']
                avg_review1 = format_review_time(int(round(applicant1_row['avg_review_time'])), review_time_col_width)
                total_clearances += count1
            else:
                applicant1 = ''
                count1 = ''
                avg_review1 = ''

            if applicant2:
                applicant2_row = applicant_stats[applicant_stats['APPLICANT'] == applicant2].iloc[0]
                count2 = applicant2_row['count']
                avg_review2 = format_review_time(int(round(applicant2_row['avg_review_time'])), review_time_col_width)
                total_clearances += count2
            else:
                applicant2 = ''
                count2 = ''
                avg_review2 = ''

            row = f"| {wrap_text(applicant1, applicant_col_width):<{applicant_col_width}} | {str(count1):^{count_col_width}} | {avg_review1:<{review_time_col_width}} | {wrap_text(applicant2, applicant_col_width):<{applicant_col_width}} | {str(count2):^{count_col_width}} | {avg_review2:<{review_time_col_width}} |"
            print(row)
        print(divider_double)

    print(f"Total number of clearances: {total_clearances}")


def check_dependencies():
    """Check and report status of all dependencies (--check-deps flag)."""
    import importlib
    try:
        import importlib.metadata as metadata
    except ImportError:
        import importlib_metadata as metadata  # type: ignore

    # Color codes (use colorama if available)
    try:
        GREEN = Fore.GREEN
        YELLOW = Fore.YELLOW
        RED = Fore.RED
        CYAN = Fore.CYAN
        RESET = Style.RESET_ALL
    except NameError:
        GREEN = YELLOW = RED = CYAN = RESET = ""

    def check_dep(module_name, package_name=None, import_from=None):
        """Check if a dependency is installed and get its version."""
        pkg_name = package_name or module_name
        import_desc = f"{module_name}.{import_from}" if import_from else module_name

        try:
            if import_from:
                mod = importlib.import_module(module_name)
                getattr(mod, import_from)
            else:
                importlib.import_module(module_name)

            try:
                version = metadata.version(pkg_name)
            except Exception:
                version = "unknown"

            return True, version, import_desc
        except (ImportError, AttributeError):
            return False, None, import_desc

    # Header
    print("=" * 80)
    print(f"{CYAN}FDA 510(k) Batch Fetch - Dependency Status Report{RESET}")
    print("=" * 80)
    print()

    # Required dependencies
    print(f"{CYAN}REQUIRED DEPENDENCIES{RESET}")
    print("-" * 80)

    required_deps = [
        ('requests', 'requests', None, 'HTTP client for FDA API and PDF downloads'),
        ('pandas', 'pandas', None, 'DataFrame operations for data filtering/analysis'),
        ('numpy', 'numpy', None, 'Numerical operations (used by pandas)'),
    ]

    all_required_present = True
    for module, package, import_from, purpose in required_deps:
        installed, version, import_desc = check_dep(module, package, import_from)

        if installed:
            print(f"{GREEN}✓{RESET} {import_desc:20s} v{version:12s} {purpose}")
        else:
            all_required_present = False
            print(f"{RED}✗{RESET} {import_desc:20s} {'MISSING':12s} {purpose}")
            print(f"  Install: pip install {package}")

    print()

    if not all_required_present:
        print(f"{RED}ERROR: One or more required dependencies are missing.{RESET}")
        print(f"Install all required dependencies: pip install requests pandas numpy")
        print()
        sys.exit(1)

    # Optional dependencies
    print(f"{CYAN}OPTIONAL DEPENDENCIES{RESET}")
    print("-" * 80)

    optional_deps = [
        ('tqdm', 'tqdm', None,
         'Progress bars during download',
         'Falls back to simple print statements'),
        ('colorama', 'colorama', None,
         'Colored terminal output',
         'Falls back to uncolored text'),
        ('pytesseract', 'pytesseract', None,
         'OCR for image-based PDFs (requires tesseract binary)',
         'Skips OCR, returns empty text for image PDFs'),
        ('pdf2image', 'pdf2image', None,
         'PDF to image conversion for OCR',
         'Skips OCR feature entirely'),
        ('PyPDF2', 'PyPDF2', 'PdfReader',
         'PDF validation during download',
         'Skips validation checks'),
        ('reportlab', 'reportlab', None,
         'PDF generation for reports',
         'Report generation features disabled'),
        ('openpyxl', 'openpyxl', None,
         'Excel file generation (--save-excel)',
         'Excel export unavailable, use CSV'),
    ]

    missing_optional = []
    for module, package, import_from, purpose, fallback in optional_deps:
        installed, version, import_desc = check_dep(module, package, import_from)

        if installed:
            print(f"{GREEN}✓{RESET} {import_desc:20s} v{version:12s} {purpose}")
        else:
            missing_optional.append((package, purpose, fallback))
            print(f"{YELLOW}○{RESET} {import_desc:20s} {'MISSING':12s} {purpose}")
            print(f"  Fallback: {fallback}")

    print()

    # Summary
    print(f"{CYAN}SUMMARY{RESET}")
    print("-" * 80)

    if missing_optional:
        print(f"{YELLOW}⚠{RESET}  {len(missing_optional)} optional dependencies missing")
        print()
        print(f"{CYAN}Impact of Missing Dependencies:{RESET}")
        for package, purpose, fallback in missing_optional:
            print(f"  • {package}: {purpose}")
            print(f"    → {fallback}")
        print()
        print(f"{CYAN}Installation Commands:{RESET}")
        missing_packages = ' '.join([pkg for pkg, _, _ in missing_optional])
        print(f"  pip install {missing_packages}")
        print()
        print(f"{GREEN}Note:{RESET} All core functionality is available. Optional features will gracefully degrade.")
    else:
        print(f"{GREEN}✓{RESET} All dependencies installed!")
        print(f"  All features are available including progress bars, OCR, PDF validation,")
        print(f"  colored output, and Excel export.")

    print()
    print("=" * 80)
    print(f"{CYAN}Dependency check complete. You can now run batchfetch.{RESET}")
    print("=" * 80)


def main():
    args = parse_args()

    # Handle --check-deps flag
    if args.check_deps:
        check_dependencies()
        sys.exit(0)

    start_time = time.time()

    # Determine directories
    data_dir = args.data_dir if args.data_dir else os.path.join(os.getcwd(), "fda_data")
    pdf_dir = args.download_dir if args.download_dir else os.path.join(os.getcwd(), "510ks")
    output_dir = args.output_dir if args.output_dir else os.getcwd()

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # Determine if fully non-interactive
    has_cli_filters = any([args.date_range, args.years, args.submission_types,
                           args.committees, args.decision_codes, args.applicants,
                           args.product_codes])
    interactive = args.interactive or not has_cli_filters

    # Override: never go interactive in non-TTY environment
    if interactive and not sys.stdin.isatty():
        print("[Non-TTY] Interactive mode requested but no TTY available. Using CLI filters only.")
        if not has_cli_filters:
            print("Error: No CLI filters provided and no TTY for interactive mode.")
            print("Usage: python batchfetch.py --date-range pmn96cur --years 2020-2025 --product-codes CODE")
            sys.exit(1)
        interactive = False

    # Failed downloads log
    log_file_path = os.path.join(output_dir, "failed_downloads_log.json")
    try:
        with open(log_file_path, 'r') as f:
            failed_downloads_log = json.load(f)
    except FileNotFoundError:
        failed_downloads_log = {}

    failed_downloads_log_lock = Lock()

    # ---- Step 1: Select date ranges ----
    if args.date_range:
        keys = [k.strip() for k in args.date_range.split(',')]
        for k in keys:
            if k not in zip_dict:
                print(f"Error: Unknown date range key '{k}'. Valid keys: {', '.join(zip_dict.keys())}")
                sys.exit(1)
        print(f"Using date ranges: {', '.join(keys)}")
    elif interactive:
        keys = select_date_range_interactive(data_dir)
    else:
        keys = ['pmn96cur', 'pmnlstmn']
        print(f"Using default date ranges: {', '.join(keys)}")

    # ---- Step 2: Select years ----
    if args.years:
        selected_years = parse_year_list(args.years)
        print(f"Filtering by years: {selected_years}")
    elif interactive and "pmn96cur" in keys:
        selected_years = select_years_interactive(keys)
    else:
        selected_years = []

    # ---- Download and process zip files ----
    num_cores = os.cpu_count()
    num_workers = max(1, num_cores if num_cores else 1)
    print(f"Using {num_workers} workers for concurrent tasks.")

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(process_zip_file, key, data_dir) for key in keys]
        dfs = [future.result() for future in concurrent.futures.as_completed(futures)]

    df = pd.concat(dfs) if dfs else pd.DataFrame()

    if "pmn96cur" in keys and selected_years:
        df = df[df["DATERECEIVED"].dt.year.isin(selected_years)]

    if df.empty:
        print("No records found after applying the selected filters.")
        sys.exit(1)

    # ---- Step 3: Filter by submission types ----
    if args.submission_types:
        submission_types = [t.strip() for t in args.submission_types.split(',')]
        df = df[df['TYPE'].isin(submission_types)]
        print(f"Filtered by submission types: {submission_types}")
    elif interactive:
        print("Submission Types Table")
        submission_types = select_submission_types_interactive(df)
        if submission_types:
            df = df[df['TYPE'].isin(submission_types)]

    if df.empty:
        print("No records found after applying submission type filter.")
        sys.exit(1)

    # ---- Step 4: Filter by advisory committees ----
    if args.committees:
        committees = [c.strip().upper() for c in args.committees.split(',')]
        df = df[df['REVIEWADVISECOMM'].isin(committees)]
        print(f"Filtered by advisory committees: {committees}")
    elif interactive:
        print("Review Advisory Committees Table")
        committees = select_review_committees_interactive(df)
        if committees:
            df = df[df['REVIEWADVISECOMM'].isin(committees)]

    if df.empty:
        print("No records found after applying advisory committee filter.")
        sys.exit(1)

    # ---- Step 5: Filter by decision codes ----
    if args.decision_codes:
        decision_codes = [c.strip().upper() for c in args.decision_codes.split(',')]
        df = df[df['DECISION'].isin(decision_codes)]
        print(f"Filtered by decision codes: {decision_codes}")
    elif interactive:
        print("Decision Codes Table")
        selected_decision_codes = select_decision_codes_interactive(df)
        if selected_decision_codes and selected_decision_codes[0] != '':
            df = df[df["DECISION"].isin(selected_decision_codes)]

    if df.empty:
        print("No records found after applying decision code filter.")
        sys.exit(1)

    # ---- Step 6: Display applicant stats and filter ----
    applicant_stats = df.groupby('APPLICANT').agg(
        count=('APPLICANT', 'size'),
        avg_review_time=('REVIEWTIME', 'mean')
    ).reset_index()

    if applicant_stats.empty:
        print("No records found.")
        sys.exit(1)

    display_applicants_table(df, applicant_stats)

    if args.applicants:
        applicants = [a.strip().upper() for a in args.applicants.split(';') if a.strip()]
        df = df[df["APPLICANT"].isin(applicants)]
        print(f"Filtered by applicants: {applicants}")
    elif interactive:
        applicants = select_applicants_interactive()
        if applicants and applicants[0] != '':
            if not set(applicants).issubset(set(df["APPLICANT"].unique())):
                print("Warning: Some applicants not found in data.")
            df = df[df["APPLICANT"].isin(applicants)]
    else:
        applicants = []

    df = df.sort_values("APPLICANT")

    # ---- Step 7: Fetch FOI Class data and display product codes ----
    dl_headers = dict(FDA_WEBSITE_HEADERS)

    foiclass_url = "https://www.accessdata.fda.gov/premarket/ftparea/foiclass.zip"
    foiclass_file_path = os.path.join(data_dir, "foiclass.txt")

    # Check if foiclass.txt is fresh
    foiclass_fresh = (os.path.exists(foiclass_file_path) and
                      (time.time() - os.path.getmtime(foiclass_file_path)) / 86400 < 5)

    if foiclass_fresh:
        print(f"FOI class file found (<5 days old): {foiclass_file_path}")
        foiclass_df = pd.read_csv(foiclass_file_path, sep="|", encoding='ISO-8859-1')
    else:
        try:
            response = requests.get(foiclass_url, headers=dl_headers, allow_redirects=True, timeout=60)
            response.raise_for_status()
            zip_file = zipfile.ZipFile(BytesIO(response.content))
            zip_file.extractall(path=data_dir)
            foiclass_df = pd.read_csv(foiclass_file_path, sep="|", encoding='ISO-8859-1')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching FOI Class data: {e}")
            if os.path.exists(foiclass_file_path):
                print(f"Using existing foiclass.txt")
                foiclass_df = pd.read_csv(foiclass_file_path, sep="|", encoding='ISO-8859-1')
            else:
                print("Cannot proceed without FOI class data.")
                sys.exit(1)

    product_code_to_device_name = dict(zip(foiclass_df['PRODUCTCODE'], foiclass_df['DEVICENAME']))
    product_code_to_device_class = dict(zip(foiclass_df['PRODUCTCODE'], foiclass_df['DEVICECLASS']))
    product_code_to_regulation_number = dict(zip(foiclass_df['PRODUCTCODE'], foiclass_df['REGULATIONNUMBER'].astype(str)))

    product_codes_dict = {}
    product_codes_in_df = df["PRODUCTCODE"].unique()
    for product_code in product_codes_in_df:
        device_name = product_code_to_device_name.get(product_code, 'Unknown')
        device_class = product_code_to_device_class.get(product_code, 'Unknown')
        regulation_number = product_code_to_regulation_number.get(product_code, 'Unknown')
        if applicants and applicants[0] != '':
            count = df[(df["APPLICANT"].isin(applicants)) & (df["PRODUCTCODE"] == product_code)].shape[0]
            avg_review_time = df[(df["APPLICANT"].isin(applicants)) & (df["PRODUCTCODE"] == product_code)]["REVIEWTIME"].mean()
        else:
            count = df[df["PRODUCTCODE"] == product_code].shape[0]
            avg_review_time = df[df["PRODUCTCODE"] == product_code]["REVIEWTIME"].mean()
        product_codes_dict[product_code] = (device_name, device_class, regulation_number, count, math.ceil(avg_review_time) if not pd.isna(avg_review_time) else 'N/A')

    product_codes_dict = dict(sorted(product_codes_dict.items(), key=sortKey))

    print("Product Code Table")
    display_product_code_table(product_codes_dict)

    # ---- Step 8: Save Excel if requested ----
    df_counts = df.groupby(['APPLICANT', 'PRODUCTCODE']).size().reset_index(name='counts')

    if args.save_excel:
        save_excel = True
    elif interactive:
        save_excel = prompt_user(
            "Do you want to save the Applicant Table and Product Code Table to an Excel file? (yes/no): ",
            default_option='no'
        ).strip().lower() == "yes"
    else:
        save_excel = False

    if save_excel:
        excel_file_path = os.path.join(output_dir, "Applicant_ProductCode_Tables.xlsx")
        try:
            with pd.ExcelWriter(excel_file_path) as writer:
                df_counts.to_excel(writer, sheet_name="Applicant Table", index=False)
                product_codes_df = pd.DataFrame.from_dict(product_codes_dict, orient='index', columns=["Device Name", "Class", "Regulation", "Total #", "Review"])
                product_codes_df.to_excel(writer, sheet_name="Product Code Table", index_label="Pro Code")
                df.to_excel(writer, sheet_name="510k Data", index=False)
            print(f"Tables saved to {excel_file_path}.")
        except PermissionError:
            print(f"Permission denied: Unable to write to {excel_file_path}.")
        except Exception as e:
            print(f"Error saving Excel: {e}")

    # ---- Step 9: Filter by product codes for download ----
    if args.product_codes:
        product_codes_filter = [c.strip() for c in args.product_codes.split(',')]
        df = df[df["PRODUCTCODE"].isin(product_codes_filter)]
        print(f"Filtered by product codes for download: {product_codes_filter}")
    elif interactive:
        product_codes_input = prompt_user(
            "Enter the Product Codes separated by comma (leave blank to download all): ",
            default_option=''
        ).split(',')
        product_codes_input = [code.strip() for code in product_codes_input]
        if product_codes_input and product_codes_input[0] != '':
            df = df[df["PRODUCTCODE"].isin(product_codes_input)]
            print(f"Selected Product Codes: {product_codes_input}")

    if df.empty:
        print("No records found with the selected product code filter.")
        sys.exit(1)

    # ---- Step 10: Build URLs and save CSV ----
    base_url = "https://www.accessdata.fda.gov/cdrh_docs/"
    year_pdf_dict = {year: f'pdf{year - 2000}' if year >= 2002 else 'pdf' for year in range(1976, 2101)}

    df["URL"] = [
        base_url + year_pdf_dict[row.DATERECEIVED.year] + "/" + row.KNUMBER + ".pdf"
        for row in tqdm(df.itertuples(), total=df.shape[0], desc="Building URLs")
    ]

    df = df[df["URL"].notna()]

    csv_output_path = os.path.join(output_dir, "510k_download.csv")
    try:
        df.to_csv(csv_output_path, index=False)
        print(f"Download list saved to {csv_output_path}")
    except PermissionError:
        print("Permission denied: unable to write CSV.")
    except Exception as e:
        print(f"Error saving CSV: {e}")

    # ---- Step 11: Download PDFs (unless --no-download) ----
    total_successful = 0
    total_failed = 0
    total_skipped = 0

    if args.no_download:
        print("Skipping PDF download (--no-download flag set).")
    else:
        failed_downloads = defaultdict(int)
        successful_downloads = defaultdict(int)
        skipped_files = []
        download_delay = args.delay  # Capture for use in nested function

        def download_and_process_pdf(row, max_retries=3):
            url = row.URL
            dir_path = os.path.join(pdf_dir, str(row.DATERECEIVED.year), re.sub(r'\W+', '', str(row.APPLICANT)), str(row.PRODUCTCODE), str(row.TYPE))
            file_path = os.path.join(dir_path, row.KNUMBER + ".pdf")
            file_path = os.path.normpath(file_path)

            if os.path.exists(file_path):
                return f"File {file_path} already exists. Skipping download."

            if url in failed_downloads_log:
                return f"Skipping {url} because it failed to download previously."

            for attempt in range(max_retries):
                try:
                    session = requests.Session()
                    session.max_redirects = 5
                    adapter = requests.adapters.HTTPAdapter(
                        max_retries=3,
                        pool_connections=10,
                        pool_maxsize=10
                    )
                    session.mount("http://", adapter)
                    session.mount("https://", adapter)

                    session.cookies.update({
                        'fda_gdpr': 'true',
                        'fda_consent': 'true'
                    })

                    response = session.get(url,
                        headers=dl_headers,
                        timeout=60,
                        allow_redirects=True,
                        stream=True
                    )

                    if 'application/pdf' not in response.headers.get('Content-Type', ''):
                        raise ValueError(f"Unexpected content type: {response.headers.get('Content-Type')}")

                    os.makedirs(dir_path, exist_ok=True)
                    with open(file_path, 'wb') as f:
                        f.write(response.content)

                    if PdfReader:
                        try:
                            PdfReader(file_path)
                            successful_downloads[row.DATERECEIVED.year] += 1
                            return f"Successfully downloaded {file_path}"
                        except Exception:
                            os.remove(file_path)
                            raise ValueError("Downloaded file is not a valid PDF")
                    else:
                        successful_downloads[row.DATERECEIVED.year] += 1
                        return f"Successfully downloaded {file_path}"

                except requests.exceptions.TooManyRedirects:
                    return f"Too many redirects for {url}"
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        with failed_downloads_log_lock:
                            failed_downloads_log[url] = True
                        return f"Failed to download {url} after {max_retries} attempts: {e}"
                    time.sleep(2 ** attempt)
                except Exception as e:
                    if attempt == max_retries - 1:
                        with failed_downloads_log_lock:
                            failed_downloads_log[url] = True
                        return f"Failed to process {url} after {max_retries} attempts: {e}"
                    time.sleep(2 ** attempt)

            return f"Successfully downloaded {file_path}"

        def download_with_delay(row_and_count):
            row, count = row_and_count
            time.sleep(download_delay)

            try:
                result = download_and_process_pdf(row)

                if "Successfully" in result:
                    delay = download_delay
                else:
                    delay = min(300, download_delay * (2 ** failed_downloads[row.DATERECEIVED.year]))
                    failed_downloads[row.DATERECEIVED.year] += 1

                time.sleep(delay)

                if count % 10 == 0:
                    with failed_downloads_log_lock:
                        with open(log_file_path, 'w') as f:
                            json.dump(failed_downloads_log, f)

                return result

            except Exception as e:
                time.sleep(60)
                return f"Error processing {row.KNUMBER}: {str(e)}"

        print(f"\nDownloading {len(df)} PDFs to {pdf_dir}...")
        rows_with_counts = list(zip(df.itertuples(), range(df.shape[0])))

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            results = list(tqdm(executor.map(download_with_delay, rows_with_counts), total=len(rows_with_counts), desc="Downloading PDFs"))

        for result in results:
            print(result)

        with failed_downloads_log_lock:
            with open(log_file_path, 'w') as f:
                json.dump(failed_downloads_log, f)

        total_successful = sum(successful_downloads.values())
        total_failed = len([r for r in results if "Failed" in r])
        total_skipped = len([r for r in results if "Skipping" in r or "already exists" in r])

    elapsed = time.time() - start_time

    # ---- Structured summary ----
    print("\n" + "="*60)
    print("BATCH FETCH COMPLETE")
    print("="*60)
    print(f"  Total records in catalog:  {len(df)}")
    print(f"  Date ranges:               {', '.join(keys)}")
    if selected_years:
        print(f"  Year filter:               {selected_years}")
    print(f"  CSV output:                {csv_output_path}")
    if not args.no_download:
        print(f"  PDFs downloaded:           {total_successful}")
        print(f"  PDFs skipped (existing):   {total_skipped}")
        print(f"  PDFs failed:               {total_failed}")
        print(f"  Download directory:        {pdf_dir}")
    print(f"  Time elapsed:              {elapsed:.1f}s")
    print("="*60)

    # Process monthly files if needed
    def should_download_monthly_file(key):
        today = datetime.today()
        if today.day >= 10 and key in ["pmnlstmn", "pmn96cur"]:
            return True
        return False

    for key in zip_dict.keys():
        if should_download_monthly_file(key):
            process_zip_file(key, data_dir)

    try:
        pd.set_option('future.no_silent_downcasting', True)
    except Exception:
        # Expected: older pandas may not support this option
        pass


if __name__ == '__main__':
    main()
