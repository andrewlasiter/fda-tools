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
import orjson
import ijson


def download_and_parse_csv(urls, pma_url, data_dir=None):
    csv_data = {}
    knumbers = set()
    pma_numbers = set()

    if data_dir:
        original_cwd = os.getcwd()
        os.makedirs(data_dir, exist_ok=True)
        os.chdir(data_dir)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    session = requests.Session()
    session.headers.update(headers)

    required_files = [url.split('/')[-1].replace('.zip', '.txt') for url in urls] + ['pma.txt']
    missing_files = []

    for filename in required_files:
        if not os.path.exists(filename):
            missing_files.append(filename)

    if missing_files:
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
        print("\n" + "!"*60)
        print("WARNING: No FDA database files were loaded!")
        print("The script will still process PDFs but won't be able to:")
        print("- Validate K-numbers, P-numbers, or N-numbers")
        print("- Identify product codes")
        print("- Classify devices as predicates vs reference devices")
        print("!"*60)

    if data_dir:
        os.chdir(original_cwd)

    return csv_data, knumbers, pma_numbers


def correct_number_format(number):
    number = number.replace(" ", "")
    number = number.upper().replace('O', '0').replace('I', '1').replace('l', '1').replace('S', '5').replace('B', '8').replace('G', '6').replace('Z', '2').replace('A', '4').replace('Q', '0').replace('i', '1').replace('s', '5').replace('z', '2').replace('q', '9').replace('|<.', 'K').replace('1(', 'K').replace('|(', 'K').replace('l(', 'K')
    return number


def correct_knumber_format(knumber, known_numbers):
    knumber = correct_number_format(knumber)
    if knumber.startswith('1<'):
        knumber = 'K' + knumber[2:]

    if re.match(r'K\d{6}', knumber) and len(knumber) <= 7 and knumber in known_numbers:
        return knumber
    return None


def correct_nnumber_format(nnumber, known_numbers):
    nnumber = correct_number_format(nnumber)
    if re.match(r'N\d{4,5}', nnumber) and len(nnumber) <= 6 and nnumber in known_numbers:
        return nnumber
    return None


def correct_pnumber_format(pnumber, known_numbers):
    pnumber = correct_number_format(pnumber)
    if re.match(r'P\d{6}', pnumber) and len(pnumber) <= 7 and pnumber in known_numbers:
        return pnumber
    return None


def extract_text_from_pdf(file_path):
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
                text = '\n'.join(page.extract_text() for page in pdf.pages)
            return text
        except Exception as e:
            print(f"Error processing file with pdfplumber: {file_path}. Skipping this file. Error: {e}")
            with open("error_log.txt", "a", encoding='utf-8') as log_file:
                log_file.write(f"{file_path}\n")
            return ""


def save_to_json(data, filename):
    with open(filename, 'wb') as f:
        f.write(orjson.dumps(data))


def load_large_json(filename):
    pdf_data = {}
    with open(filename, 'rb') as f:
        for prefix, event, value in ijson.parse(f):
            if prefix.endswith('.key'):
                current_key = value
            elif prefix.endswith('.value'):
                pdf_data[current_key] = value
    return pdf_data


def parse_text(text, filename, csv_data, known_knumbers, known_pma_numbers):
    regex = r'\b(?:[Kk]|1\(|l\(|\|<\.|\|\()[^dOISBGZAQsiqzl]*[\d][dOISBGZAQsiqzl\d ]{6,7}\b|\b[1l]<[^dOISBGZAQsiqzl\d ]*[\d][dOISBGZAQsiqzl\d ]{6,7}\b|\b[Nn][^dOISBGZAQsiqzl\d]*[\d][dOISBGZAQsiqzl\d ]{5,6}(?:\/S\d{3})?\b|\b[Pp][^dOISBGZAQsiqzl\d]*[\d][dOISBGZAQsiqzl\d ]{6,7}(?:\/S\d{3})?\b'

    potential_matches = re.findall(regex, text)

    corrected_knumbers = [correct_knumber_format(match, known_knumbers) for match in potential_matches]
    corrected_nnumbers = [correct_nnumber_format(match.split('/')[0], known_pma_numbers) for match in potential_matches]
    corrected_pnumbers = [correct_pnumber_format(match.split('/')[0], known_pma_numbers) for match in potential_matches]

    valid_matches = [match for match in corrected_knumbers + corrected_nnumbers + corrected_pnumbers if match]
    supplement_matches = [match for match in potential_matches if '/S' in match]

    unique_matches = list(dict.fromkeys(valid_matches))
    if filename[:-4] in unique_matches:
        unique_matches.remove(filename[:-4])

    types = ['Predicate' if csv_data.get(match) == csv_data.get(filename[:-4]) else 'Reference Device' for match in unique_matches]
    product_codes = [csv_data.get(match, '') for match in unique_matches]
    data = list(zip(unique_matches, types, product_codes))

    reference_devices = [identifier for identifier, type, product_code in data if type == 'Reference Device']
    predicates = [identifier for identifier, type, product_code in data if type == 'Predicate']
    if len(reference_devices) == 1 and not predicates:
        predicates.append(reference_devices.pop(0))
        data = [(identifier, 'Predicate', product_code) if identifier in predicates else (identifier, type, product_code) for identifier, type, product_code in data]

    return data, supplement_matches


def safe_process_file(args):
    file_path, csv_data, max_predicates, max_reference_devices, pdf_files, pdf_data, known_knumbers, known_pma_numbers = args
    filename = os.path.basename(file_path)
    text = extract_text_from_pdf(file_path)
    data, supplement_matches = parse_text(text, filename, csv_data, known_knumbers, known_pma_numbers)
    unique_matches = []
    for pdf_file in pdf_files:
        if search_knumber_in_pdf(filename[:-4], pdf_file, pdf_data):
            unique_matches.append(os.path.basename(pdf_file)[:-4])
    predicates = [identifier for identifier, type, product_code in data if type == 'Predicate']
    reference_devices = [(identifier, product_code) for identifier, type, product_code in data if type == 'Reference Device' and product_code != csv_data.get(filename[:-4])]
    row = [filename[:-4], csv_data.get(filename[:-4], '')] + predicates + [''] * (max_predicates - len(predicates)) + [identifier for identifier, product_code in reference_devices] + [''] * (max_reference_devices - len(reference_devices))
    return row, len(predicates), len(reference_devices), supplement_matches


def search_knumber_in_pdf(knumber, pdf_file, pdf_data):
    text = pdf_data.get(pdf_file)
    if text:
        return knumber in text
    return False


def process_batches(pdf_files, batch_size, csv_data, max_predicates, max_reference_devices, pdf_data, known_knumbers, known_pma_numbers, workers=4):
    results = []
    supplement_data = []
    for i in tqdm(range(0, len(pdf_files), batch_size), desc="Processing batches"):
        batch_files = pdf_files[i:i + batch_size]
        with Pool(workers) as pool:
            batch_results = pool.map(safe_process_file, [(file, csv_data, max_predicates, max_reference_devices, pdf_files, pdf_data, known_knumbers, known_pma_numbers) for file in batch_files])
            batch_results = [result for result in batch_results if result is not None]
            results.extend(batch_results)
            for res in batch_results:
                supplement_data.extend(res[3])
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
            pdf_data = {pdf_file: extract_text_from_pdf(pdf_file) for pdf_file in tqdm(pdf_files, desc="Extracting text from PDF files")}
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
                pdf_data = {pdf_file: extract_text_from_pdf(pdf_file) for pdf_file in tqdm(pdf_files, desc="Extracting text from PDF files")}
                save_to_json(pdf_data, pdf_data_file)
        else:
            use_pdf_data = messagebox.askyesno("PDF Data File Not Found", "Would you like to locate the PDF data file?")
            if use_pdf_data:
                pdf_data_file = fd.askopenfilename()
                pdf_data = load_large_json(pdf_data_file)
                print(f"Using PDF data from file: {pdf_data_file}")
            else:
                pdf_data = {pdf_file: extract_text_from_pdf(pdf_file) for pdf_file in tqdm(pdf_files, desc="Extracting text from PDF files")}
                save_to_json(pdf_data, pdf_data_file)
        root.destroy()

    max_predicates = 0
    max_reference_devices = 0
    batch_size = args.batch_size
    workers = args.workers

    results, supplement_data = process_batches(pdf_files, batch_size, csv_data, max_predicates, max_reference_devices, pdf_data, known_knumbers, known_pma_numbers, workers=workers)

    for result in results:
        max_predicates = max(max_predicates, result[1])
        max_reference_devices = max(max_reference_devices, result[2])

    filename = get_available_filename(output_dir, 'output.csv')
    supplement_filename = get_available_filename(output_dir, 'supplement.csv')

    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['510(k)', 'Product Code'] + [f'Predicate {i+1}' for i in range(max_predicates)] + [f'Reference Device {i+1}' for i in range(max_reference_devices)])

        for row in tqdm(results, desc="Writing data"):
            try:
                writer.writerow(row[0])
            except Exception as e:
                print(f"Error writing row: {row[0]}")
                print(f"Exception: {e}")

    with open(supplement_filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Number with Suffix'])
        for match in supplement_data:
            writer.writerow([match])

    elapsed = time.time() - start_time

    # Structured summary
    total_pdfs = len(pdf_files)
    total_with_predicates = sum(1 for r in results if r[1] > 0)
    total_predicates_found = sum(r[1] for r in results)
    total_reference_devices = sum(r[2] for r in results)
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
    print(f"  Time elapsed:              {elapsed:.1f}s")
    print(f"  Output:                    {filename}")
    print(f"  Supplements:               {supplement_filename}")
    print("="*60)


if __name__ == '__main__':
    main()
