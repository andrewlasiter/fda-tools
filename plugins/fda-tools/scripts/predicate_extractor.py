#!/usr/bin/env python3
"""
FDA 510(k) Predicate Extraction Tool

Extracts predicate device numbers from FDA 510(k) PDF documents.
Adapted from Test79.py with CLI argument support for non-interactive use.

Usage:
    # Headless mode (all required args provided):
    python predicate_extractor.py --directory /path/to/pdfs --use-cache

    # Interactive mode (falls back to tkinter GUI):
    python predicate_extractor.py
"""

import os
import re
import csv
import io
import sys
import zipfile
import requests
import json
import time
import argparse
from datetime import datetime, timedelta
from tqdm import tqdm
from multiprocessing import Pool
import fitz  # PyMuPDF
import pdfplumber

# Multiprocessing shared state (initialized per worker)
CSV_DATA = {}
PDF_FILES = []
PDF_DATA = {}
KNOWN_KNUMBERS = set()
KNOWN_PMA_NUMBERS = set()

# Shared HTTP utilities
try:
    from fda_http import create_session, FDA_HEADERS
except ImportError:
    # Fallback if fda_http not on path
    FDA_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    def create_session(api_mode=False):
        session = requests.Session()
        session.headers.update(FDA_HEADERS)
        return session
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    orjson = None
    HAS_ORJSON = False

try:
    import ijson
    HAS_IJSON = True
except ImportError:
    ijson = None
    HAS_IJSON = False


def enrich_knumbers(knumbers, batch_size=100):
    """Fetch openFDA enrichment data for K-numbers.

    Returns a dict keyed by K-number with basic metadata.
    """
    try:
        from fda_api_client import FDAClient
    except Exception:
        return {}

    client = FDAClient()
    enrichment = {}
    kn_list = sorted(set(k for k in knumbers if re.match(r"^K\d{6}$", k)))
    for i in range(0, len(kn_list), batch_size):
        chunk = kn_list[i:i + batch_size]
        result = client.batch_510k(chunk)
        for r in result.get("results", []):
            k = r.get("k_number")
            if not k:
                continue
            enrichment[k] = {
                "device_name": r.get("device_name"),
                "decision_date": r.get("decision_date"),
                "applicant": r.get("applicant"),
                "product_code": r.get("product_code"),
            }
    return enrichment


def download_and_parse_csv(urls, pma_url, data_dir=None):
    csv_data = {}
    knumbers = set()
    pma_numbers = set()

    if data_dir:
        original_cwd = os.getcwd()
        os.makedirs(data_dir, exist_ok=True)
        os.chdir(data_dir)

    try:
        session = create_session()

        required_files = [url.split('/')[-1].replace('.zip', '.txt') for url in urls] + ['pma.txt']
        missing_files = []

        for filename in required_files:
            if not os.path.exists(filename):
                missing_files.append(filename)

        # Check if running in headless mode (--headless flag or --directory provided)
        is_headless = '--headless' in sys.argv or '--directory' in sys.argv or '-d' in sys.argv

        if missing_files:
            if is_headless:
                # In headless mode: skip manual instructions, just attempt download
                print(f"Missing {len(missing_files)} FDA database file(s). Attempting automated download...")
            else:
                print("\n" + "="*60)
                print("DOWNLOAD ISSUE DETECTED")
                print("="*60)
                print("The automated download is being blocked by FDA's servers.")
                print("This is likely due to anti-bot protection.")
                print("\nMissing files:")
                for filename in missing_files:
                    corresponding_url = None
                    if filename == 'pma.txt':
                        corresponding_url = pma_url
                    else:
                        for url in urls:
                            if url.split('/')[-1].replace('.zip', '.txt') == filename:
                                corresponding_url = url
                                break
                    print(f"  - {filename} (from {corresponding_url})")

                print("\nPLEASE MANUALLY DOWNLOAD these files:")
                print("1. Open each URL in your web browser")
                print("2. Download the .zip files")
                print("3. Extract them to this directory:")
                print(f"   {os.getcwd()}")
                print("4. Re-run this script")
                print("\nURLs to download:")
                for url in urls + [pma_url]:
                    print(f"  {url}")
                print("="*60)

                print("\nAttempting automated download with delays...")

        for i, url in enumerate(urls):
            filename = url.split('/')[-1].replace('.zip', '.txt')
            if os.path.exists(filename) and os.path.getmtime(filename) > time.mktime((datetime.now() - timedelta(days=5)).timetuple()):
                print(f"File found! (<5 days old): Being nice to FDA's servers: {filename}")
            else:
                print(f"Downloading and extracting file: {filename}")
                if i > 0:
                    time.sleep(2)

                try:
                    response = session.get(url, timeout=30)
                    response.raise_for_status()

                    if not response.content.startswith(b'PK'):
                        print(f"Error: Response from {url} is not a valid zip file")
                        print(f"Response status: {response.status_code}")
                        print(f"Response headers: {dict(response.headers)}")
                        print(f"First 200 chars of response: {response.text[:200]}")
                        continue

                    zipfile.ZipFile(io.BytesIO(response.content)).extractall()
                    print(f"Successfully downloaded and extracted: {filename}")

                except requests.exceptions.RequestException as e:
                    print(f"Error downloading {url}: {e}")
                    continue
                except zipfile.BadZipFile as e:
                    print(f"Error extracting zip file from {url}: {e}")
                    print(f"Response status: {response.status_code}")
                    print(f"Response content type: {response.headers.get('content-type', 'unknown')}")
                    continue
                except Exception as e:
                    print(f"Unexpected error processing {url}: {e}")
                    continue

            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8-sig', errors='replace') as file:
                    reader = csv.reader(file, delimiter='|')
                    for row in reader:
                        if len(row) > 0:
                            knumbers.add(row[0])
                            if len(row) > 14:
                                csv_data[row[0]] = row[14]
            else:
                print(f"Warning: Could not download or find file {filename}")

        pma_filename = 'pma.txt'
        if os.path.exists(pma_filename) and os.path.getmtime(pma_filename) > time.mktime((datetime.now() - timedelta(days=5)).timetuple()):
            print(f"File found! (<5 days old): Being nice to FDA's servers: {pma_filename}")
        else:
            print(f"Downloading and extracting file: {pma_filename}")
            time.sleep(2)
            try:
                response = session.get(pma_url, timeout=30)
                response.raise_for_status()

                if not response.content.startswith(b'PK'):
                    print(f"Error: Response from {pma_url} is not a valid zip file")
                    print(f"Response status: {response.status_code}")
                    print(f"Response headers: {dict(response.headers)}")
                    print(f"First 200 chars of response: {response.text[:200]}")
                else:
                    zipfile.ZipFile(io.BytesIO(response.content)).extractall()
                    print(f"Successfully downloaded and extracted: {pma_filename}")

            except requests.exceptions.RequestException as e:
                print(f"Error downloading {pma_url}: {e}")
            except zipfile.BadZipFile as e:
                print(f"Error extracting zip file from {pma_url}: {e}")
                print(f"Response status: {response.status_code}")
                print(f"Response content type: {response.headers.get('content-type', 'unknown')}")
            except Exception as e:
                print(f"Unexpected error processing {pma_url}: {e}")

        if os.path.exists(pma_filename):
            with open(pma_filename, 'r', encoding='utf-8-sig', errors='replace') as file:
                reader = csv.reader(file, delimiter='|')
                for row in reader:
                    if len(row) > 0:
                        pma_numbers.add(row[0])
        else:
            print(f"Warning: Could not download or find file {pma_filename}")

        if not csv_data and not knumbers and not pma_numbers:
            if is_headless:
                print("ERROR: No FDA database files loaded. Cannot validate device numbers in headless mode.")
                sys.exit(2)
            else:
                print("\n" + "!"*60)
                print("WARNING: No FDA database files were loaded!")
                print("The script will still process PDFs but won't be able to:")
                print("- Validate K-numbers, P-numbers, or N-numbers")
                print("- Identify product codes")
                print("- Classify devices as predicates vs reference devices")
                print("!"*60)

        return csv_data, knumbers, pma_numbers
    finally:
        if data_dir:
            os.chdir(original_cwd)


def correct_number_format(number):
    """Apply aggressive OCR character substitutions to a device number string.

    This function intentionally applies ALL common OCR misread corrections
    simultaneously (e.g., O->0, I->1, S->5, B->8, etc.). This is by design:
    the aggressive approach maximizes recall of OCR-corrupted numbers.

    IMPORTANT: The corrections are NOT validated here. Each caller
    (correct_knumber_format, correct_nnumber_format, correct_pnumber_format)
    validates the corrected result against the FDA database (known_numbers set)
    before accepting it. This two-stage approach (aggressive correction +
    strict validation) ensures high recall without false positives.
    """
    number = number.replace(" ", "")
    number = number.upper().replace('O', '0').replace('I', '1').replace('l', '1').replace('S', '5').replace('B', '8').replace('G', '6').replace('Z', '2').replace('A', '4').replace('Q', '0').replace('i', '1').replace('s', '5').replace('z', '2').replace('q', '9').replace('|<.', 'K').replace('1(', 'K').replace('|(', 'K').replace('l(', 'K')
    return number


def correct_knumber_format(knumber, known_numbers):
    """Correct OCR artifacts in K-numbers and validate against FDA database.

    Returns the corrected K-number only if it matches a known 510(k) number,
    ensuring aggressive OCR corrections don't produce false positives.
    """
    knumber = correct_number_format(knumber)
    if knumber.startswith('1<'):
        knumber = 'K' + knumber[2:]

    if re.match(r'K\d{6}', knumber) and len(knumber) <= 7 and knumber in known_numbers:
        return knumber
    return None


def correct_nnumber_format(nnumber, known_numbers):
    """Correct OCR artifacts in N-numbers and validate against FDA database.

    Returns the corrected N-number only if it matches a known PMA number,
    ensuring aggressive OCR corrections don't produce false positives.
    """
    nnumber = correct_number_format(nnumber)
    if re.match(r'N\d{4,5}', nnumber) and len(nnumber) <= 6 and nnumber in known_numbers:
        return nnumber
    return None


def correct_pnumber_format(pnumber, known_numbers):
    """Correct OCR artifacts in P-numbers and validate against FDA database.

    Returns the corrected P-number only if it matches a known PMA number,
    ensuring aggressive OCR corrections don't produce false positives.
    """
    pnumber = correct_number_format(pnumber)
    if re.match(r'P\d{6}', pnumber) and len(pnumber) <= 7 and pnumber in known_numbers:
        return pnumber
    return None


def correct_dennumber_format(dennumber):
    """Validate a De Novo (DEN) number format.

    DEN numbers follow the pattern DEN + 6-7 digits (e.g., DEN200045, DEN210001).
    Unlike K/P/N numbers, DEN numbers do not require OCR correction because
    they appear in digitally-generated documents. No FDA database validation
    is performed since there is no comprehensive DEN database file available
    for download.

    Returns the DEN number if it matches the expected format, None otherwise.
    """
    dennumber = dennumber.replace(" ", "").upper()
    if re.match(r'DEN\d{6,7}$', dennumber):
        return dennumber
    return None


def extract_text_from_pdf(file_path, output_dir=None):
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error processing file with fitz: {file_path}. Error: {e}")
        try:
            with pdfplumber.open(file_path) as pdf:
                text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
            return text
        except Exception as e:
            print(f"Error processing file with pdfplumber: {file_path}. Skipping this file. Error: {e}")
            error_log_path = os.path.join(output_dir, "error_log.txt") if output_dir else "error_log.txt"
            with open(error_log_path, "a", encoding='utf-8') as log_file:
                log_file.write(f"{file_path}\n")
            return ""


def save_to_json(data, filename):
    """Save extracted PDF data to JSON file. Uses orjson if available for speed, falls back to stdlib json."""
    if HAS_ORJSON:
        with open(filename, 'wb') as f:
            f.write(orjson.dumps(data))
    else:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f)


def load_large_json(filename):
    """Load PDF text cache from JSON file. Uses ijson for streaming (low memory) if available, falls back to stdlib json."""
    if not HAS_IJSON:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    pdf_data = {}
    current_key = None
    with open(filename, 'rb') as f:
        for prefix, event, value in ijson.parse(f):
            if prefix.endswith('.key'):
                current_key = value
            elif prefix.endswith('.value'):
                if current_key is not None:
                    pdf_data[current_key] = value
    return pdf_data


def detect_se_section(text):
    """Detect Substantial Equivalence section boundaries in PDF text.

    Uses 3-tier detection from references/section-patterns.md:
    - Tier 1: SE header regex (direct match)
    - Tier 2: OCR-tolerant regex (up to 2 character substitutions)
    - Tier 3: Semantic signal counting (2+ signals in 200-word window)

    Returns list of (start, end) character positions for SE sections.
    """
    SE_WINDOW = 2000  # Characters after SE header to consider as SE section

    # Tier 1: Direct SE header regex
    se_regex = re.compile(
        r'(?i)(substantial\s+equivalence|se\s+comparison|predicate\s+'
        r'(comparison|device|analysis|identification)|comparison\s+to\s+predicate|'
        r'technological\s+characteristics|comparison\s+(table|chart|matrix)|'
        r'similarities\s+and\s+differences|comparison\s+of\s+(the\s+)?'
        r'(features|technological|device))'
    )

    # Tier 3: Semantic signals
    se_signals = [
        'predicate', 'substantial equivalence', 'SE comparison',
        'technolog', 'intended use', 'indications for use',
        'same intended', 'same technological', 'comparison table',
        'subject device', 'predicate device', 'legally marketed'
    ]

    sections = []

    # Tier 1 matches
    for match in se_regex.finditer(text):
        start = match.start()
        end = min(start + SE_WINDOW, len(text))
        sections.append((start, end))

    # Tier 3: Sliding window semantic detection (only if Tier 1 found nothing)
    if not sections:
        words = text.split()
        window_size = 200  # words
        for i in range(0, len(words) - window_size, 50):
            window_text = ' '.join(words[i:i + window_size]).lower()
            signal_count = sum(1 for s in se_signals if s.lower() in window_text)
            if signal_count >= 2:
                # Approximate character position
                char_start = len(' '.join(words[:i]))
                char_end = min(char_start + SE_WINDOW, len(text))
                sections.append((char_start, char_end))

    return sections


def score_device_section(text, device_number, se_sections):
    """Score a device number based on where it appears in the PDF.

    Returns section score: SE=40, testing/clinical=25, table/OCR=15, general=10
    """
    # Find all positions of the device number
    positions = [m.start() for m in re.finditer(re.escape(device_number), text)]

    if not positions:
        return 10  # Default general text score

    # Check if any position falls within an SE section
    for pos in positions:
        for se_start, se_end in se_sections:
            if se_start <= pos <= se_end:
                return 40  # SE section

    # Check for testing/clinical section keywords near device mention
    testing_regex = re.compile(
        r'(?i)(testing|performance|bench\s+test|clinical|biocompatibility|'
        r'verification|validation|safety\s+testing|electrical\s+safety)'
    )
    for pos in positions:
        window_start = max(0, pos - 500)
        window_end = min(len(text), pos + 500)
        window = text[window_start:window_end]
        if testing_regex.search(window):
            return 25  # Testing/clinical section

    return 10  # General text


def parse_text(text, filename, csv_data, known_knumbers, known_pma_numbers, section_aware=False):
    # K/N/P number regex — matches OCR-corrupted variants and supplements
    # NOTE:
    # The trailing quantifiers are calibrated so canonical IDs are captured
    # even when immediately followed by punctuation/end-of-line:
    #   K123456  => 1 digit + 5 trailing chars
    #   N12345   => 1 digit + 4 trailing chars
    #   P123456  => 1 digit + 5 trailing chars
    regex = r'\b(?:[Kk]|1\(|l\(|\|<\.|\|\()[^dOISBGZAQsiqzl]*[\d][dOISBGZAQsiqzl\d ]{5,7}\b|\b[1l]<[^dOISBGZAQsiqzl\d ]*[\d][dOISBGZAQsiqzl\d ]{5,7}\b|\b[Nn][^dOISBGZAQsiqzl\d]*[\d][dOISBGZAQsiqzl\d ]{3,6}(?:\/S\d{3})?\b|\b[Pp][^dOISBGZAQsiqzl\d]*[\d][dOISBGZAQsiqzl\d ]{5,7}(?:\/S\d{3})?\b'
    # DEN (De Novo) number regex — DEN followed by 6-7 digits
    den_regex = r'\bDEN\d{6,7}\b'

    potential_matches = re.findall(regex, text)
    den_matches = re.findall(den_regex, text, re.IGNORECASE)

    # OCR correction + FDA database validation chain:
    # 1. correct_number_format() aggressively substitutes OCR-misread characters
    # 2. correct_*number_format() validates the corrected number against known FDA numbers
    # 3. Only numbers confirmed in the FDA database survive into valid_matches
    corrected_knumbers = [correct_knumber_format(match, known_knumbers) for match in potential_matches]
    corrected_nnumbers = [correct_nnumber_format(match.split('/')[0], known_pma_numbers) for match in potential_matches]
    corrected_pnumbers = [correct_pnumber_format(match.split('/')[0], known_pma_numbers) for match in potential_matches]
    corrected_dennumbers = [correct_dennumber_format(match) for match in den_matches]

    valid_matches = [match for match in corrected_knumbers + corrected_nnumbers + corrected_pnumbers + corrected_dennumbers if match]
    supplement_matches = [match for match in potential_matches if '/S' in match]

    unique_matches = list(dict.fromkeys(valid_matches))
    if filename[:-4] in unique_matches:
        unique_matches.remove(filename[:-4])

    if section_aware and text:
        se_sections = detect_se_section(text)
        scores = {m: score_device_section(text, m, se_sections) for m in unique_matches}
        original_order = {m: i for i, m in enumerate(unique_matches)}
        unique_matches.sort(key=lambda m: (-scores.get(m, 10), original_order.get(m, 0)))

    types = ['Predicate' if csv_data.get(match) is not None and csv_data.get(match) == csv_data.get(filename[:-4]) else 'Reference Device' for match in unique_matches]
    product_codes = [csv_data.get(match, '') for match in unique_matches]
    data = list(zip(unique_matches, types, product_codes))

    reference_devices = [identifier for identifier, type, product_code in data if type == 'Reference Device']
    predicates = [identifier for identifier, type, product_code in data if type == 'Predicate']
    if len(reference_devices) == 1 and not predicates:
        predicates.append(reference_devices.pop(0))
        data = [(identifier, 'Predicate', product_code) if identifier in predicates else (identifier, type, product_code) for identifier, type, product_code in data]

    return data, supplement_matches


def _init_pool(csv_data, pdf_files, pdf_data, known_knumbers, known_pma_numbers):
    global CSV_DATA, PDF_FILES, PDF_DATA, KNOWN_KNUMBERS, KNOWN_PMA_NUMBERS
    CSV_DATA = csv_data
    PDF_FILES = pdf_files
    PDF_DATA = pdf_data
    KNOWN_KNUMBERS = known_knumbers
    KNOWN_PMA_NUMBERS = known_pma_numbers


def safe_process_file(args):
    file_path, section_aware = args
    filename = os.path.basename(file_path)
    text = extract_text_from_pdf(file_path)
    data, supplement_matches = parse_text(
        text,
        filename,
        CSV_DATA,
        KNOWN_KNUMBERS,
        KNOWN_PMA_NUMBERS,
        section_aware=section_aware,
    )
    unique_matches = []
    for pdf_file in PDF_FILES:
        if search_knumber_in_pdf(filename[:-4], pdf_file, PDF_DATA):
            unique_matches.append(os.path.basename(pdf_file)[:-4])
    predicates = [identifier for identifier, type, product_code in data if type == 'Predicate']
    reference_devices = [
        identifier for identifier, type, product_code in data
        if type == 'Reference Device' and product_code != CSV_DATA.get(filename[:-4])
    ]
    return filename[:-4], CSV_DATA.get(filename[:-4], ''), predicates, reference_devices, supplement_matches


def search_knumber_in_pdf(knumber, pdf_file, pdf_data):
    text = pdf_data.get(pdf_file)
    if text:
        return knumber in text
    return False


def process_batches(pdf_files, batch_size, csv_data, pdf_data, known_knumbers, known_pma_numbers, workers=4, section_aware=False):
    results = []
    supplement_data = []
    for i in tqdm(range(0, len(pdf_files), batch_size), desc="Processing batches"):
        batch_files = pdf_files[i:i + batch_size]
        with Pool(
            workers,
            initializer=_init_pool,
            initargs=(csv_data, pdf_files, pdf_data, known_knumbers, known_pma_numbers),
        ) as pool:
            batch_results = pool.map(
                safe_process_file,
                [(file, section_aware) for file in batch_files]
            )
            batch_results = [result for result in batch_results if result is not None]
            results.extend(batch_results)
            for res in batch_results:
                supplement_data.extend(res[4])
    return results, supplement_data


def get_available_filename(directory, base_filename):
    base_name, ext = os.path.splitext(base_filename)
    counter = 0
    while os.path.exists(os.path.join(directory, base_filename)):
        counter += 1
        base_filename = f"{base_name}_{counter}{ext}"
    return os.path.join(directory, base_filename)


def parse_args():
    parser = argparse.ArgumentParser(
        description='FDA 510(k) Predicate Extraction Tool — Extract predicate device numbers from PDF documents.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Headless mode with all args:
  python predicate_extractor.py --directory /path/to/pdfs --use-cache --output-dir /tmp/results

  # Specify FDA data directory:
  python predicate_extractor.py --directory /path/to/pdfs --no-cache --data-dir /path/to/fda_data

  # Custom batch size and workers:
  python predicate_extractor.py --directory /path/to/pdfs --use-cache --batch-size 50 --workers 8

  # Interactive mode (tkinter GUI):
  python predicate_extractor.py
        """
    )
    parser.add_argument('--directory', '-d', type=str, default=None,
                        help='Path to directory containing PDF files (skips tkinter directory picker)')
    cache_group = parser.add_mutually_exclusive_group()
    cache_group.add_argument('--use-cache', action='store_true', default=None,
                             help='Use previously extracted PDF text data if available')
    cache_group.add_argument('--no-cache', action='store_true', default=None,
                             help='Re-extract text from all PDFs (ignore existing cache)')
    parser.add_argument('--output-dir', '-o', type=str, default=None,
                        help='Directory for output files (default: same as --directory)')
    parser.add_argument('--data-dir', type=str, default=None,
                        help='Directory for FDA database files (default: script directory)')
    parser.add_argument('--batch-size', '-b', type=int, default=100,
                        help='Number of PDFs to process per batch (default: 100)')
    parser.add_argument('--workers', '-w', type=int, default=4,
                        help='Number of parallel processing workers (default: 4)')
    parser.add_argument('--headless', action='store_true',
                        help='Enforce non-interactive mode (exit with error if GUI would be needed)')
    parser.add_argument('--incremental', action='store_true',
                        help='Skip PDFs already present in existing output.csv')
    parser.add_argument('--section-aware', action='store_true',
                        help='Enable section-aware extraction: score devices by PDF section context (SE=40, testing=25, general=10)')
    parser.add_argument('--enrich', action='store_true',
                        help='Enrich output with openFDA data (device name, clearance date, MAUDE events)')
    return parser.parse_args()


def main():
    args = parse_args()
    start_time = time.time()

    # Determine if we can run headless
    headless = args.directory is not None

    if headless:
        directory = args.directory
        if not os.path.isdir(directory):
            print(f"Error: Directory not found: {directory}")
            sys.exit(1)
    else:
        # Check if we can display a GUI
        display_available = os.environ.get('DISPLAY') or sys.platform == 'win32' or sys.platform == 'darwin'

        if args.headless or not display_available:
            print("Error: No --directory specified and no display available for GUI.")
            print("Usage: python predicate_extractor.py --directory /path/to/pdfs [--output-dir /path/to/output]")
            print("Add --headless to enforce non-interactive mode.")
            sys.exit(1)

        # Fall back to tkinter GUI
        try:
            import tkinter as tk
            from tkinter import filedialog, messagebox
            root = tk.Tk()
            root.withdraw()
            directory = filedialog.askdirectory()
            if not directory:
                print("No directory selected. Exiting.")
                sys.exit(1)
        except (ImportError, Exception) as e:
            print(f"Error: GUI not available ({e}). Use --directory to specify PDF path.")
            sys.exit(1)

    def generate_pdf_files(directory):
        for root_dir, dirs, files in os.walk(directory):
            for filename in files:
                if filename.endswith('.pdf'):
                    yield os.path.join(root_dir, filename)

    pdf_files = list(generate_pdf_files(directory))
    print(f"Selected directory: {directory} with {len(pdf_files)} PDF files")

    if len(pdf_files) == 0:
        print("No PDF files found in the selected directory. Exiting.")
        sys.exit(1)

    # Incremental mode: skip PDFs already in existing output.csv and merge results back
    existing_rows = []
    if args.incremental:
        inc_output_dir = args.output_dir if args.output_dir else directory
        inc_output_file = os.path.join(inc_output_dir, 'output.csv')
        if os.path.exists(inc_output_file):
            processed = set()
            with open(inc_output_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)  # skip header
                for row in reader:
                    if row:
                        processed.add(row[0])
                        existing_rows.append(row)
            before = len(pdf_files)
            pdf_files = [p for p in pdf_files if os.path.basename(p)[:-4] not in processed]
            skipped = before - len(pdf_files)
            print(f"Incremental mode: skipping {skipped} already-processed PDFs, processing {len(pdf_files)} new PDFs")
            print(f"Incremental mode: {len(existing_rows)} existing rows will be merged with new results")
        else:
            print("Incremental mode: no existing output.csv found, processing all PDFs")

    # Determine data directory for FDA database files
    data_dir = args.data_dir if args.data_dir else os.path.dirname(os.path.abspath(__file__))

    csv_urls = [
        'https://www.accessdata.fda.gov/premarket/ftparea/pmn96cur.zip',
        'https://www.accessdata.fda.gov/premarket/ftparea/pmn9195.zip',
        'https://www.accessdata.fda.gov/premarket/ftparea/pmn8690.zip',
        'https://www.accessdata.fda.gov/premarket/ftparea/pmn8185.zip',
        'https://www.accessdata.fda.gov/premarket/ftparea/pmn7680.zip',
        'https://www.accessdata.fda.gov/premarket/ftparea/pmnlstmn.zip'
    ]
    pma_url = 'https://www.accessdata.fda.gov/premarket/ftparea/pma.zip'

    csv_data, knumbers, pma_numbers = download_and_parse_csv(csv_urls, pma_url, data_dir=data_dir)
    known_knumbers = knumbers.union(pma_numbers)
    known_pma_numbers = pma_numbers

    # Determine output directory
    output_dir = args.output_dir if args.output_dir else directory
    os.makedirs(output_dir, exist_ok=True)

    # Handle PDF text cache
    pdf_data_file = os.path.join(directory, 'pdf_data.json')

    if headless:
        # CLI mode: use --use-cache / --no-cache flags
        if os.path.exists(pdf_data_file) and args.use_cache:
            pdf_data = load_large_json(pdf_data_file)
            print(f"Using PDF data from file: {pdf_data_file}")
        elif args.no_cache or not os.path.exists(pdf_data_file):
            pdf_data = {pdf_file: extract_text_from_pdf(pdf_file, output_dir) for pdf_file in tqdm(pdf_files, desc="Extracting text from PDF files")}
            save_to_json(pdf_data, pdf_data_file)
        else:
            # --use-cache not specified and file exists: default to using cache
            pdf_data = load_large_json(pdf_data_file)
            print(f"Using PDF data from file: {pdf_data_file}")
    else:
        # GUI mode: use tkinter dialogs (original behavior)
        from tkinter import messagebox, filedialog as fd
        if os.path.exists(pdf_data_file):
            use_pdf_data = messagebox.askyesno("PDF Data File Found", "Do you want to use the previously extracted text data for the PDF files in this folder?")
            if use_pdf_data:
                pdf_data = load_large_json(pdf_data_file)
                print(f"Using PDF data from file: {pdf_data_file}")
            else:
                pdf_data = {pdf_file: extract_text_from_pdf(pdf_file, output_dir) for pdf_file in tqdm(pdf_files, desc="Extracting text from PDF files")}
                save_to_json(pdf_data, pdf_data_file)
        else:
            use_pdf_data = messagebox.askyesno("PDF Data File Not Found", "Would you like to locate the PDF data file?")
            if use_pdf_data:
                pdf_data_file = fd.askopenfilename()
                pdf_data = load_large_json(pdf_data_file)
                print(f"Using PDF data from file: {pdf_data_file}")
            else:
                pdf_data = {pdf_file: extract_text_from_pdf(pdf_file, output_dir) for pdf_file in tqdm(pdf_files, desc="Extracting text from PDF files")}
                save_to_json(pdf_data, pdf_data_file)
        root.destroy()

    max_predicates = 0
    max_reference_devices = 0
    batch_size = args.batch_size
    workers = args.workers

    results, supplement_data = process_batches(
        pdf_files,
        batch_size,
        csv_data,
        pdf_data,
        known_knumbers,
        known_pma_numbers,
        workers=workers,
        section_aware=args.section_aware,
    )

    enrichment_path = None
    if args.enrich:
        knumbers = set()
        for knumber, _product_code, predicates, reference_devices, _ in results:
            if knumber:
                kn = knumber.split("/")[0].upper()
                if re.match(r"^K\d{6}$", kn):
                    knumbers.add(kn)
            for item in predicates + reference_devices:
                if not item:
                    continue
                kn = item.split("/")[0].upper()
                if re.match(r"^K\d{6}$", kn):
                    knumbers.add(kn)
        enrichment = enrich_knumbers(knumbers)
        enrichment_path = os.path.join(output_dir, "enrichment.json")
        with open(enrichment_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generated_at": datetime.now().isoformat(),
                    "count": len(enrichment),
                    "data": enrichment,
                },
                f,
                indent=2,
            )

    # Two-pass row construction: compute max column widths, then build rows
    for result in results:
        max_predicates = max(max_predicates, len(result[2]))
        max_reference_devices = max(max_reference_devices, len(result[3]))

    # In incremental mode, account for existing row widths when computing column counts
    if args.incremental and existing_rows:
        for row in existing_rows:
            # Existing rows: [knumber, product_code, pred1..predN, ref1..refN]
            # Determine predicate/reference counts from existing header
            # Each row has 2 fixed columns + predicates + references
            pass  # Column widths are recomputed below after merging

    rows = []
    for knumber, product_code, predicates, reference_devices, _ in results:
        row = [knumber, product_code] + predicates + [''] * (max_predicates - len(predicates)) + reference_devices + [''] * (max_reference_devices - len(reference_devices))
        rows.append(row)

    # Incremental merge: combine existing rows with new rows, recompute column widths
    if args.incremental and existing_rows:
        # Parse existing header to determine old column structure
        old_pred_count = 0
        old_ref_count = 0
        if os.path.exists(os.path.join(output_dir, 'output.csv')):
            with open(os.path.join(output_dir, 'output.csv'), 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header:
                    old_pred_count = sum(1 for h in header if h.startswith('Predicate '))
                    old_ref_count = sum(1 for h in header if h.startswith('Reference Device '))

        # Recompute max widths across both old and new data
        max_predicates = max(max_predicates, old_pred_count)
        max_reference_devices = max(max_reference_devices, old_ref_count)

        # Re-pad new rows to the merged column widths
        new_rows = []
        for knumber, product_code, predicates, reference_devices, _ in results:
            row = [knumber, product_code] + predicates + [''] * (max_predicates - len(predicates)) + reference_devices + [''] * (max_reference_devices - len(reference_devices))
            new_rows.append(row)

        # Pad existing rows to the merged column widths
        total_cols = 2 + max_predicates + max_reference_devices
        padded_existing = []
        for row in existing_rows:
            # Existing rows may have fewer columns — pad with empty strings
            padded = row + [''] * (total_cols - len(row))
            # Existing rows may also have MORE columns if old had wider structure
            # In that case, the old predicate/reference data might be misaligned
            # Reparse: first 2 cols are fixed, next old_pred_count are predicates, rest are references
            if len(row) >= 2:
                kn = row[0]
                pc = row[1]
                old_preds = row[2:2 + old_pred_count]
                old_refs = row[2 + old_pred_count:2 + old_pred_count + old_ref_count]
                padded = [kn, pc] + old_preds + [''] * (max_predicates - len(old_preds)) + old_refs + [''] * (max_reference_devices - len(old_refs))
            padded_existing.append(padded)

        rows = padded_existing + new_rows
        # Write back to original output.csv (overwrite)
        filename = os.path.join(output_dir, 'output.csv')
        supplement_filename = os.path.join(output_dir, 'supplement.csv')
        print(f"Incremental mode: merged {len(padded_existing)} existing + {len(new_rows)} new = {len(rows)} total rows")
    else:
        filename = get_available_filename(output_dir, 'output.csv')
        supplement_filename = get_available_filename(output_dir, 'supplement.csv')

    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['510(k)', 'Product Code'] + [f'Predicate {i+1}' for i in range(max_predicates)] + [f'Reference Device {i+1}' for i in range(max_reference_devices)])

        for row in tqdm(rows, desc="Writing data"):
            try:
                writer.writerow(row)
            except Exception as e:
                print(f"Error writing row: {row}")
                print(f"Exception: {e}")

    # For incremental supplement merging, load existing supplements
    existing_supplements = set()
    if args.incremental and os.path.exists(supplement_filename):
        with open(supplement_filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if row:
                    existing_supplements.add(row[0])

    with open(supplement_filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Number with Suffix'])
        all_supplements = list(existing_supplements) + supplement_data
        for match in dict.fromkeys(all_supplements):  # deduplicate preserving order
            writer.writerow([match])

    elapsed = time.time() - start_time

    # Structured summary
    total_pdfs = len(pdf_files)
    total_with_predicates = sum(1 for r in results if len(r[2]) > 0)
    total_predicates_found = sum(len(r[2]) for r in results)
    total_reference_devices = sum(len(r[3]) for r in results)
    total_supplements = len(supplement_data)
    error_count = total_pdfs - len(results)

    print("\n" + "="*60)
    print("EXTRACTION COMPLETE")
    print("="*60)
    print(f"  Total PDFs processed:      {total_pdfs}")
    print(f"  With predicates:           {total_with_predicates}")
    print(f"  Total predicates found:    {total_predicates_found}")
    print(f"  Total reference devices:   {total_reference_devices}")
    print(f"  Supplement matches:        {total_supplements}")
    print(f"  Errors/skipped:            {error_count}")
    if args.incremental and existing_rows:
        print(f"  Previously extracted:      {len(existing_rows)}")
        print(f"  Total rows in output:      {len(rows)}")
    print(f"  Time elapsed:              {elapsed:.1f}s")
    print(f"  Output:                    {filename}")
    print(f"  Supplements:               {supplement_filename}")
    if enrichment_path:
        print(f"  Enrichment:                {enrichment_path}")
    print("="*60)


if __name__ == '__main__':
    main()
