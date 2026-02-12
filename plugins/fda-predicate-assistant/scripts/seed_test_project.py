#!/usr/bin/env python3
"""
seed_test_project.py — Generate realistic FDA 510(k) test project directories.

Selects a product code (specific, random from all of openFDA, or random within a
review panel), queries openFDA for classification metadata + a recent clearance,
and creates a project directory with query.json and review.json for integration testing.

Data sourcing modes:
    --use-predicate-for-data   Use the predicate's 510(k) summary as subject device data
    --use-peer-for-data        Use a random peer clearance (same product code, NOT the
                               predicate) as subject device data

Usage:
    python seed_test_project.py                                          # Random, no data
    python seed_test_project.py --product-code OVE                       # Specific code
    python seed_test_project.py --k-number K241335                       # Golden demo
    python seed_test_project.py --random --use-predicate-for-data        # Random + predicate data
    python seed_test_project.py --random --use-peer-for-data             # Random + peer data
    python seed_test_project.py --random-specialty CV --use-peer-for-data
    python seed_test_project.py --dry-run                                # Preview
    python seed_test_project.py --seed 42                                # Reproducible
"""

import argparse
import json
import os
import random
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from fda_api_client import FDAClient

DEFAULT_OUTPUT_DIR = os.path.expanduser("~/fda-510k-data/projects")
DEFAULT_MAX_AGE_YEARS = 5
MAX_OPENFDA_SKIP = 25000
RANDOM_RETRY_LIMIT = 3

# PDF download settings
PDF_DOWNLOAD_TIMEOUT = 60
PDF_DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                  " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}
PDF_COOKIES = {"fda_gdpr": "true", "fda_consent": "true"}


# ---------------------------------------------------------------------------
# PDF Download & Text Extraction
# ---------------------------------------------------------------------------

def download_pdf_text(k_number):
    """Download a 510(k) summary PDF from FDA and extract text.

    Tries multiple URL patterns. Returns extracted text or None.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("  WARNING: PyMuPDF not installed — cannot extract PDF text", file=sys.stderr)
        return None

    try:
        import requests
        use_requests = True
    except ImportError:
        import urllib.request
        use_requests = False

    yy = k_number[1:3]
    urls = [
        f"https://www.accessdata.fda.gov/cdrh_docs/pdf{yy}/{k_number}.pdf",
        f"https://www.accessdata.fda.gov/cdrh_docs/reviews/{k_number}.pdf",
    ]

    for url in urls:
        try:
            print(f"  Trying {url}...")
            if use_requests:
                session = requests.Session()
                session.headers.update(PDF_DOWNLOAD_HEADERS)
                session.cookies.update(PDF_COOKIES)
                resp = session.get(url, timeout=PDF_DOWNLOAD_TIMEOUT, allow_redirects=True)
                if resp.status_code != 200:
                    continue
                content_type = resp.headers.get("Content-Type", "")
                if "pdf" not in content_type.lower() and "octet" not in content_type.lower():
                    continue
                pdf_bytes = resp.content
            else:
                req = urllib.request.Request(url, headers=PDF_DOWNLOAD_HEADERS)
                with urllib.request.urlopen(req, timeout=PDF_DOWNLOAD_TIMEOUT) as resp:
                    content_type = resp.headers.get("Content-Type", "")
                    if "pdf" not in content_type.lower() and "octet" not in content_type.lower():
                        continue
                    pdf_bytes = resp.read()

            # Skip stub PDFs (redirects, placeholders)
            if len(pdf_bytes) < 1000:
                print(f"  PDF too small ({len(pdf_bytes)} bytes) — likely a stub/redirect")
                continue

            # Write to temp file and extract with PyMuPDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = tmp.name

            try:
                doc = fitz.open(tmp_path)
                text = "\n".join(page.get_text() for page in doc)
                doc.close()
            except Exception as e:
                print(f"  PyMuPDF extraction failed: {e}")
                text = ""
            finally:
                os.unlink(tmp_path)

            if len(text.strip()) > 200:
                print(f"  SUCCESS: Extracted {len(text)} chars from {k_number} PDF")
                return text
            else:
                print(f"  PDF too short ({len(text.strip())} chars), trying next URL...")

        except Exception as e:
            print(f"  Failed: {e}")

    print(f"  Could not download PDF for {k_number}")
    return None


# ---------------------------------------------------------------------------
# Device Spec Parser — extracts structured data from 510(k) summary text
# ---------------------------------------------------------------------------

def clean_ifu_text(raw_ifu):
    """Extract the core IFU statement from noisy Form FDA 3881 text.

    The FDA IFU form (Form 3881) embeds the actual indication text inside a
    lot of boilerplate (K-number headers, PRA statements, model lists).
    This function extracts just the meaningful indication statement(s).
    """
    if not raw_ifu:
        return ""

    # Strategy: find sentences starting with "The {device}... intended/designed for..."
    # FDA IFU statements use various phrasings: "intended for use", "designed to",
    # "indicated for", "used to", etc.  Also match "MEN -" / "WOMEN -" prefixed statements.
    ifu_sentences = re.findall(
        r"((?:(?:MEN|WOMEN|MALE|FEMALE)\s*[-–—:]\s*)?(?:The\s+.{5,120}?\s+(?:is|are)\s+(?:intended\s+for|designed\s+to|indicated\s+for|used\s+(?:to|for|in))\s+.*?)(?:\.\s|\.$|\n\n))",
        raw_ifu, re.IGNORECASE | re.DOTALL,
    )

    if ifu_sentences:
        # Deduplicate similar statements (same device, different indications)
        unique = []
        seen = set()
        for s in ifu_sentences:
            # Truncate at Roman numeral section headers that bled into the match
            s = re.sub(r"\n\s*(?:I{1,3}V?|VI{0,3}|IX|X)\.\s+(?:Comparison|Device|Technological|Performance|Non-Clinical|Sterilization|Biocompat).*", "", s, flags=re.DOTALL)
            # Normalize for dedup
            key = re.sub(r"\s+", " ", s.strip().lower()[:120])
            if key not in seen:
                seen.add(key)
                unique.append(s.strip())
        return "\n\n".join(unique)

    # Fallback: strip all known boilerplate and return what's left
    cleaned = raw_ifu
    # Remove submission/form headers
    cleaned = re.sub(r"Submission\s+Number\s*\(if\s+known\)\s*\n?", "", cleaned)
    cleaned = re.sub(r"51\s*0\s*\(k\)\s*(?:Number|#).*?\n", "", cleaned)
    cleaned = re.sub(r"Device\s+(?:Trade\s+)?Name\s*\n.*?\n", "", cleaned)
    cleaned = re.sub(r"Form\s+(?:FDA\s+\d+\s*-?\s*)?Approved.*?\n", "", cleaned)
    cleaned = re.sub(r"Expiration\s+Date.*?\n", "", cleaned)
    cleaned = re.sub(r"See\s+PRA\s+Statement.*?\n", "", cleaned)
    cleaned = re.sub(r"Indications\s+for\s+Use\s*\(Describe\)\s*\n?", "", cleaned)
    # Remove PRA boilerplate (match OMB with various OCR artifacts)
    cleaned = re.sub(r"This\s+section\s+applies\s+only.*?(?:0MB|OMB)\s+number\.?\"?", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"The\s+burden\s+time.*?(?:0MB|OMB)\s+number\.?\"?", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\"An\s+agency\s+may\s+not\s+conduct.*?(?:0MB|OMB)\s+number\.?\"?", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"FORM\s+FDA\s+\d+.*", "", cleaned)
    cleaned = re.sub(r"PSC\s+Publishing.*", "", cleaned)
    cleaned = re.sub(r"DEPARTMENT\s+OF\s+HEAL?TH.*?\n", "", cleaned)
    cleaned = re.sub(r"Food\s+and\s+Drug\s+Administration\s*\n", "", cleaned)
    # Remove 510(k) Summary section headers and contact details
    cleaned = re.sub(r"510\(k\)\s+Summary\s*\n", "", cleaned)
    cleaned = re.sub(r"Prepared\s+on:.*?\n", "", cleaned)
    cleaned = re.sub(r"Contact\s+Details\s*\n", "", cleaned)
    cleaned = re.sub(r"21\s+CFR\s+807\.\d+\(a\)\(\d+\)\s*\n?", "", cleaned)
    cleaned = re.sub(r"Applicant\s+(?:Name|Address|Contact)\s*(?:Telephone|Email)?\s*\n.*?\n", "", cleaned)
    cleaned = re.sub(r"Correspondent\s+(?:Name|Address|Contact)\s*(?:Telephone|Email)?\s*\n.*?\n", "", cleaned)
    cleaned = re.sub(r"(?:Common|Classification)\s+Name\s*\n.*?\n", "", cleaned)
    cleaned = re.sub(r"Regulation\s+Number\s*\n.*?\n", "", cleaned)
    cleaned = re.sub(r"Product\s+Code\(s\)\s*\n.*?\n", "", cleaned)
    cleaned = re.sub(r"Legally\s+Marketed\s+Predicate.*?\n", "", cleaned)
    cleaned = re.sub(r"Office\s+of\s+Chief\s+Information.*?\n", "", cleaned)
    cleaned = re.sub(r"Paperwork\s+Reduction\s+Act.*?\n", "", cleaned)
    cleaned = re.sub(r"PRAStaff@fda\.hhs\.gov\s*\n?", "", cleaned)
    # Remove Type of Use checkboxes
    cleaned = re.sub(r"Type\s+of\s+Use.*?Subpart\s+[CD]\)", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"(?:Prescription|Over-The-Counter)\s+Use\s+\(.*?Subpart\s+[CD]\)\s*\n?", "", cleaned)
    cleaned = re.sub(r"CONTINUE\s+ON\s+A\s+SEPARATE.*?\n", "", cleaned)
    cleaned = re.sub(r"IZI\s+Prescription.*?\n", "", cleaned)
    cleaned = re.sub(r"D\s+Over-The-Counter.*?\n", "", cleaned)
    # Remove K-number references and addresses
    cleaned = re.sub(r"K\d{6}\s*\n", "", cleaned)
    cleaned = re.sub(r"\d+-\d+-\d+\s*\n", "", cleaned)  # phone numbers
    cleaned = re.sub(r"\S+@\S+\.\S+\s*\n", "", cleaned)  # emails
    # Collapse whitespace
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"^\s*\n", "", cleaned)
    return cleaned.strip()


def clean_section_text(text):
    """Remove trailing headers/footers that bleed into extracted sections."""
    if not text:
        return ""
    # Remove trailing page-break artifacts
    text = re.sub(r"\n\s*\f\s*", "\n", text)
    # Remove trailing company/premarket notification headers
    text = re.sub(r"\n\s*(?:KARL\s+STORZ|Premarket\s+Notification).*$", "", text, flags=re.DOTALL)
    # Remove 510(k) summary page footers (company name + page numbers)
    text = re.sub(r"\n\s*[A-Z][A-Za-z\s,\.]+(?:Ltd|Inc|Corp|LLC|Co|GmbH)\.?\s*\n\s*510\(k\)\s+Summary\s*\n\s*\d+-\d+\s*\n?\s*(?:[IVX]+\.)?$", "", text, flags=re.DOTALL)
    text = re.sub(r"\n\s*510\(k\)\s+Summary\s*$", "", text)
    # Remove trailing Roman numeral section markers
    text = re.sub(r"\n\s*(?:I{1,3}V?|VI{0,3}|IX|X)\.\s*$", "", text)
    # Remove trailing whitespace
    return text.strip()


def parse_device_specs(text, k_number, classification=None):
    """Parse device specifications from 510(k) summary PDF text.

    Returns a dict with extracted fields suitable for device_profile.json.
    """
    specs = {
        "data_source_knumber": k_number,
        "data_source_type": "510k_summary_pdf",
        "extracted_sections": {},
    }

    # --- Indications for Use / Intended Use ---
    # Handle both traditional headers ("INDICATIONS FOR USE") and
    # 510(k) summary format ("Intended Use/Indications for Use\n21 CFR 807.92(a)(5)")
    ifu = extract_section(text, [
        r"(?:INDICATIONS?\s+FOR\s+USE|INTENDED\s+USE)[:\s]*\n([\s\S]*?)(?:\n\s*(?:DEVICE\s+DESCRIPTION|TECHNOLOGICAL|SUBSTANTIAL|PREDICATE|II\.|III\.))",
        r"(?:indications?\s+for\s+use)[:\s]*\n([\s\S]*?)(?:\n\s*(?:device\s+description|technological|substantial|predicate))",
        # 510(k) summary format with CFR citation
        r"Intended\s+Use/Indications\s+for\s+Use\s*\n(?:21\s+CFR\s+807\.\d+\(a\)\(\d+\)\s*\n)?([\s\S]*?)(?:\n\s*(?:Indications\s+for\s+Use\s+Comparison|Technological\s+Comparison|Device\s+Description|Non-Clinical))",
    ])
    if ifu:
        ifu = clean_ifu_text(ifu)
        specs["intended_use"] = ifu
        specs["extracted_sections"]["indications_for_use"] = ifu

    # --- Device Description ---
    # Handle both "DEVICE DESCRIPTION" and "Device Description Summary\n21 CFR 807.92(a)(4)"
    desc = extract_section(text, [
        r"(?:DEVICE\s+DESCRIPTION)[:\s]*\n([\s\S]*?)(?:\n\s*(?:TECHNOLOGICAL|SUBSTANTIAL|PREDICATE|INDICATIONS|III\.|IV\.|STERILIZATION|BIOCOMPATIBILITY))",
        r"(?:device\s+description)[:\s]*\n([\s\S]*?)(?:\n\s*(?:technological|substantial|predicate|sterilization|biocompatibility))",
        # 510(k) summary format
        r"Device\s+Description\s+Summary\s*\n(?:21\s+CFR\s+807\.\d+\(a\)\(\d+\)\s*\n)?([\s\S]*?)(?:\n\s*(?:Intended\s+Use|Indications|Technological|Non-Clinical|Legally\s+Marketed))",
    ])
    if desc:
        desc = clean_section_text(desc)
        desc = re.sub(r"\n{3,}", "\n\n", desc).strip()
        specs["device_description"] = desc
        specs["extracted_sections"]["device_description"] = desc

    # --- Materials ---
    materials = extract_materials(text)
    if materials:
        specs["materials"] = materials

    # --- Sterilization ---
    steril = extract_section(text, [
        r"(?:STERILIZATION)[:\s]*\n([\s\S]*?)(?:\n\s*(?:BIOCOMPATIBILITY|PERFORMANCE|SOFTWARE|ELECTRICAL|SHELF\s+LIFE|CLINICAL|V\.|VI\.))",
        r"(?:sterilization)[:\s]*\n([\s\S]*?)(?:\n\s*(?:biocompatibility|performance|software|electrical|shelf\s+life|clinical))",
    ])
    if steril:
        specs["sterilization_text"] = steril.strip()
        specs["extracted_sections"]["sterilization"] = steril.strip()
        method = detect_sterilization_method(steril)
        if method:
            specs["sterilization_method"] = method

    # --- Biocompatibility ---
    biocompat = extract_section(text, [
        r"(?:BIOCOMPATIBILITY)[:\s]*\n([\s\S]*?)(?:\n\s*(?:PERFORMANCE|SOFTWARE|ELECTRICAL|STERILIZATION|SHELF\s+LIFE|CLINICAL|V\.|VI\.|VII\.))",
    ])
    if biocompat:
        specs["extracted_sections"]["biocompatibility"] = biocompat.strip()

    # --- Performance / Testing ---
    perf = extract_section(text, [
        r"(?:PERFORMANCE\s+(?:DATA|TESTING|CHARACTERISTICS))[:\s]*\n([\s\S]*?)(?:\n\s*(?:CONCLUSION|SUBSTANTIAL\s+EQUIVALENCE|BIOCOMPATIBILITY|CLINICAL|VII\.|VIII\.))",
        # 510(k) summary format
        r"Non-Clinical\s+and/or\s+Clinical\s+Tests?\s+Summary\s*(?:&\s*Conclusions?)?\s*\n(?:21\s+CFR\s+807\.\d+\(b\)\s*\n)?([\s\S]*?)(?:\n\s*(?:Based\s+on\s+the\s+above|$))",
    ])
    if perf:
        specs["extracted_sections"]["performance"] = perf.strip()

    # --- SE Comparison / Technological Characteristics ---
    tech = extract_section(text, [
        r"(?:TECHNOLOGICAL\s+CHARACTERISTICS)[:\s]*\n([\s\S]*?)(?:\n\s*(?:PERFORMANCE|BIOCOMPATIBILITY|STERILIZATION|CLINICAL|IV\.|V\.))",
        r"(?:COMPARISON\s+(?:OF|BETWEEN|TABLE))[:\s]*\n([\s\S]*?)(?:\n\s*(?:PERFORMANCE|BIOCOMPATIBILITY|STERILIZATION|CONCLUSION))",
        # 510(k) summary format
        r"Technological\s+Comparison\s*\n(?:21\s+CFR\s+807\.\d+\(a\)\(\d+\)\s*\n)?([\s\S]*?)(?:\n\s*(?:Non-Clinical|Performance|CONCLUSION|Based\s+on))",
        # IFU Comparison (also has SE-relevant data)
        r"Indications\s+for\s+Use\s+Comparison\s*\n(?:21\s+CFR\s+807\.\d+\(a\)\(\d+\)\s*\n)?([\s\S]*?)(?:\n\s*(?:Technological|Non-Clinical|Device\s+Description))",
    ])
    if tech:
        specs["extracted_sections"]["technological_characteristics"] = tech.strip()

    # --- Dimensions / Key Specs (regex patterns for common specs) ---
    dimensions = extract_dimensions(text)
    if dimensions:
        specs["dimensions"] = dimensions

    # --- Electrical specs (for powered devices) ---
    electrical = extract_electrical_specs(text)
    if electrical:
        specs["electrical"] = electrical

    # --- Standards referenced in testing section ---
    standards = extract_standards(text)
    if standards:
        specs["standards_referenced"] = standards

    return specs


def extract_section(text, patterns):
    """Try multiple regex patterns to extract a section. Returns first match or None."""
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


def extract_materials(text):
    """Extract materials list from text using keyword patterns.

    Uses word boundary matching and context filtering to avoid false positives
    like 'silver' from 'Silver Spring, MD'.
    """
    materials = set()
    # Multi-word patterns are less prone to false positives
    material_patterns = [
        r"\bstainless\s+steel(?:\s+\d+[A-Z]*)?\b",
        r"\btitanium(?:\s+alloy)?(?:\s+Ti-6Al-4V)?\b",
        r"\bPTFE\b|\bpolytetrafluoroethylene\b",
        r"\bFEP\b|\bfluorinated\s+ethylene\s+propylene\b",
        r"\bsilicone(?:\s+rubber)?\b",
        r"\bpolyurethane\b",
        r"\bpolycarbonate\b",
        r"\bpolyethylene(?:\s+(?:UHMWPE|HDPE|LDPE))?\b",
        r"\bPEEK\b|\bpolyether\s*ether\s*ketone\b",
        r"\bceramic(?:s)?\b",
        r"\boptical\s+glass\b",
        r"\bborosilicate(?:\s+glass)?\b",
        r"\bsapphire\b",
        r"\bcobalt[\s-]*chrom(?:ium|e)(?:\s+alloy)?\b",
        r"\bnitinol\b|\bnickel[\s-]*titanium\b",
        r"\btungsten\b",
        r"\bplatinum(?:[\s-]*iridium)?\b",
        r"\balumini?um(?:\s+oxide)?\b",
        r"\bnylon\b|\bpolyamide\b",
        r"\bpolypropylene\b",
        r"\bPVC\b|\bpolyvinyl\s+chloride\b",
        r"\bepoxy\b",
        r"\bacrylic\b|\bPMMA\b|\bpolymethyl\s*methacrylate\b",
        r"\bparylene\b",
        r"\bhydrogel\b",
        r"\bcollagen\b",
        r"\bePTFE\b|\bexpanded\s+PTFE\b",
        r"\bDacron\b|\bpolyester\b",
        r"\blatex\b|\bnatural\s+rubber\b",
        r"\bnitrile\b",
    ]
    # Single-element metals need context filtering — only match near material-related words
    single_metal_patterns = {
        r"\bgold\b": "gold",
        r"\bsilver\b": "silver",
        r"\bcopper\b": "copper",
    }

    for pattern in material_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            materials.add(m.strip().lower())

    # For single metals, require they appear near material-related context
    # (not in addresses, names, etc.)
    material_context = re.compile(
        r"(?:material|construct|compos|alloy|plat(?:ed|ing)|coat(?:ed|ing)|electrode|wire|tube|component)",
        re.IGNORECASE,
    )
    for pattern, name in single_metal_patterns.items():
        for m in re.finditer(pattern, text, re.IGNORECASE):
            # Check 200 chars around the match for material context
            start = max(0, m.start() - 200)
            end = min(len(text), m.end() + 200)
            context = text[start:end]
            if material_context.search(context):
                materials.add(name)

    return sorted(materials) if materials else []


def detect_sterilization_method(text):
    """Detect sterilization method from text."""
    text_lower = text.lower()
    methods = {
        "steam": [r"steam\s+steriliz", r"autoclave", r"moist\s+heat", r"121\s*[°]?\s*c",
                  r"134\s*[°]?\s*c", r"iso\s*17665"],
        "ethylene_oxide": [r"ethylene\s+oxide", r"\beo\b\s+steriliz", r"iso\s*11135"],
        "gamma": [r"gamma\s+(?:irradiation|steriliz|radiation)", r"cobalt[\s-]*60",
                  r"iso\s*11137"],
        "e_beam": [r"e[\s-]*beam", r"electron\s+beam"],
        "hydrogen_peroxide": [r"hydrogen\s+peroxide", r"vhp", r"h2o2"],
    }
    for method, patterns in methods.items():
        for p in patterns:
            if re.search(p, text_lower):
                return method
    return None


def extract_dimensions(text):
    """Extract dimensional specs like gauge, french size, length, diameter."""
    dims = {}
    # Gauge
    gauges = re.findall(r"(\d+)\s*(?:G|gauge)\b", text, re.IGNORECASE)
    if gauges:
        dims["gauges"] = sorted(set(gauges))
    # French size
    fr_sizes = re.findall(r"(\d+(?:\.\d+)?)\s*Fr\b", text)
    if fr_sizes:
        dims["french_sizes"] = sorted(set(fr_sizes))
    # Length in mm or cm
    lengths = re.findall(r"(?:length|long)[:\s]*(\d+(?:\.\d+)?)\s*(mm|cm)\b", text, re.IGNORECASE)
    if lengths:
        dims["lengths"] = [f"{v} {u}" for v, u in lengths]
    # Diameter in mm
    diameters = re.findall(r"(?:diameter|OD|ID)[:\s]*(\d+(?:\.\d+)?)\s*(mm|cm)\b", text, re.IGNORECASE)
    if diameters:
        dims["diameters"] = [f"{v} {u}" for v, u in diameters]
    # Working length
    wl = re.findall(r"(?:working\s+length)[:\s]*(\d+(?:\.\d+)?)\s*(mm|cm)\b", text, re.IGNORECASE)
    if wl:
        dims["working_length"] = f"{wl[0][0]} {wl[0][1]}"
    # FOV / Field of View
    fov = re.findall(r"(?:field\s+of\s+view|FOV)[:\s]*(\d+(?:\.\d+)?)\s*(?:°|degrees?)\b", text, re.IGNORECASE)
    if fov:
        dims["field_of_view"] = f"{fov[0]} degrees"
    return dims if dims else {}


def extract_electrical_specs(text):
    """Extract electrical specs for powered devices."""
    specs = {}
    # Power
    power = re.findall(r"(\d+(?:\.\d+)?)\s*(?:W|watts?)\b", text, re.IGNORECASE)
    if power:
        specs["power_watts"] = sorted(set(power))
    # Voltage
    voltage = re.findall(r"(\d+(?:\.\d+)?)\s*(?:V|volts?)\b", text, re.IGNORECASE)
    if voltage:
        specs["voltage"] = sorted(set(voltage))
    # Frequency
    freq = re.findall(r"(\d+(?:\.\d+)?)\s*(?:kHz|MHz|Hz)\b", text)
    if freq:
        specs["frequency"] = sorted(set(freq))
    # Applied part type
    if re.search(r"type\s+(?:BF|CF|B)\s+applied\s+part", text, re.IGNORECASE):
        m = re.search(r"type\s+(BF|CF|B)\s+applied\s+part", text, re.IGNORECASE)
        if m:
            specs["applied_part_type"] = f"Type {m.group(1).upper()}"
    return specs if specs else {}


def extract_standards(text):
    """Extract testing standard references from 510(k) summary text.

    Matches IEC, ISO, ASTM, ANSI, and EN standards with edition info.
    Returns a list of standard reference strings.
    """
    standards = set()
    # Match IEC, ISO, ASTM, ANSI, EN standards with number and optional parts
    pattern = r"((?:IEC|ISO|ASTM|ANSI|EN)\s+\d{4,6}(?:-\d+)?(?:-\d+)?(?:\s*:\s*\d{4})?)"
    for m in re.finditer(pattern, text):
        std = re.sub(r"\s+", " ", m.group(1).strip())
        standards.add(std)
    return sorted(standards)


# ---------------------------------------------------------------------------
# Project File Builders (enhanced with PDF data)
# ---------------------------------------------------------------------------

def build_device_profile_with_pdf_data(pdf_specs, clearance, classification, peers,
                                       data_source_mode):
    """Build device_profile.json using extracted PDF specs as subject device data.

    Args:
        pdf_specs: Dict from parse_device_specs()
        clearance: The predicate clearance dict (for product_code etc.)
        classification: The classification dict
        peers: List of peer clearance dicts
        data_source_mode: "predicate" or "peer"
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    product_code = clearance.get("product_code", "")

    # Use a synthetic trade name based on classification
    class_device_name = classification.get("device_name", "") if classification else ""
    synthetic_trade_name = f"Test {class_device_name}" if class_device_name else "Test Device"

    # IFU: prefer PDF-extracted, fall back to classification definition
    intended_use = pdf_specs.get("intended_use", "")
    if not intended_use and classification:
        intended_use = classification.get("definition", "")

    # Device description: prefer PDF-extracted
    device_description = pdf_specs.get("device_description", "")
    if not device_description:
        device_description = synthetic_trade_name

    peer_devices = []
    for p in peers:
        peer_devices.append({
            "k_number": p.get("k_number", ""),
            "device_name": p.get("device_name", ""),
            "applicant": p.get("applicant", ""),
            "decision_date": p.get("decision_date", ""),
            "product_code": p.get("product_code", product_code),
        })

    profile = {
        "device_name": synthetic_trade_name,
        "trade_name": synthetic_trade_name,
        "applicant": "Test Manufacturer Inc.",
        "product_code": product_code,
        "intended_use": intended_use,
        "device_description": device_description,
        "device_class": classification.get("device_class", "") if classification else "",
        "regulation_number": classification.get("regulation_number", "") if classification else "",
        "review_panel": classification.get("review_panel", "") if classification else "",
        "implant_flag": classification.get("implant_flag", "") if classification else "",
        "classification_device_name": class_device_name,
        # PDF-extracted specs
        "materials": pdf_specs.get("materials", []),
        "dimensions": pdf_specs.get("dimensions", {}),
        "sterilization_method": pdf_specs.get("sterilization_method", ""),
        "sterilization_text": pdf_specs.get("sterilization_text", ""),
        "electrical": pdf_specs.get("electrical", {}),
        "standards_referenced": pdf_specs.get("standards_referenced", []),
        # Raw extracted sections for draft commands to reference
        "extracted_sections": pdf_specs.get("extracted_sections", {}),
        # Metadata
        "data_source": {
            "mode": data_source_mode,
            "source_knumber": pdf_specs.get("data_source_knumber", ""),
            "source_type": pdf_specs.get("data_source_type", ""),
            "note": (
                f"Subject device data sourced from {pdf_specs.get('data_source_knumber', '?')} "
                f"510(k) summary PDF ({data_source_mode} mode). This is synthetic test data."
            ),
        },
        "peer_devices": peer_devices,
        "created_at": now,
        "source": f"seed_generator_{data_source_mode}_data",
    }

    return profile


def build_review_json_with_ifu(project_name, product_code, device_name, clearance,
                                intended_use=""):
    """Build review.json with intended_use populated from PDF data."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    k_number = clearance.get("k_number", "K000000")

    return {
        "project": project_name,
        "product_code": product_code,
        "device_name": device_name or "Unknown Device",
        "intended_use": intended_use,
        "created_at": now,
        "reviewed_at": now,
        "predicates": {
            k_number: {
                "device_name": clearance.get("device_name", "Unknown Device"),
                "applicant": clearance.get("applicant", "Unknown Applicant"),
                "decision_date": clearance.get("decision_date", ""),
                "product_code": product_code,
                "decision": "accepted",
                "confidence_score": 80,
                "rationale": "Seeded from recent openFDA clearance — same product code",
                "risk_flags": [],
                "source": "seed_generator",
            }
        },
        "reference_devices": {},
        "summary": {
            "total_evaluated": 1,
            "accepted": 1,
            "rejected": 0,
            "average_score": 80,
        },
    }


# ---------------------------------------------------------------------------
# Original helpers (unchanged)
# ---------------------------------------------------------------------------

def make_project_name(panel, product_code, k_number=None):
    """Generate a project name.

    For k-number mode: example_K241335_OVE_20260210
    For other modes:   seed_CV_DTC_20260210
    """
    today = datetime.now().strftime("%Y%m%d")
    if k_number:
        return f"example_{k_number}_{product_code}_{today}"
    return f"seed_{panel}_{product_code}_{today}"


def get_classification(client, product_code):
    """Fetch classification metadata for a product code. Returns dict or None."""
    resp = client.get_classification(product_code)
    if resp.get("degraded") or not resp.get("results"):
        return None
    return resp["results"][0]


def get_recent_clearance(client, product_code, max_age_years):
    """Fetch a recent 510(k) clearance for the product code. Returns dict or None."""
    cutoff_year = datetime.now().year - max_age_years
    resp = client.search_510k(
        product_code=product_code,
        year_start=str(cutoff_year),
        limit=5,
        sort="decision_date:desc",
    )
    if resp.get("degraded") or not resp.get("results"):
        return None
    return resp["results"][0]


def pick_random_product_code(client, rng, max_age_years):
    """Pick a truly random product code from openFDA 510(k) data."""
    cutoff_year = datetime.now().year - max_age_years
    search = f"decision_date:[{cutoff_year}0101 TO 29991231]"

    resp = client._request("510k", {"search": search, "limit": "1"})
    if resp.get("degraded") or not resp.get("meta"):
        return None
    total = resp["meta"]["results"]["total"]
    if total == 0:
        return None

    max_skip = min(total - 1, MAX_OPENFDA_SKIP)

    for _ in range(RANDOM_RETRY_LIMIT):
        offset = rng.randint(0, max_skip)
        resp = client._request("510k", {
            "search": search,
            "limit": "1",
            "skip": str(offset),
        })
        if resp.get("degraded") or not resp.get("results"):
            continue
        result = resp["results"][0]
        code = result.get("product_code")
        if code:
            return code

    return None


def pick_random_specialty_code(client, rng, panel, max_age_years):
    """Pick a random product code within a review panel."""
    resp = client._request("classification", {
        "search": f'review_panel:"{panel}"',
        "limit": "100",
    })
    if resp.get("degraded") or not resp.get("results"):
        return None

    codes = [r["product_code"] for r in resp["results"] if r.get("product_code")]
    if not codes:
        return None

    rng.shuffle(codes)

    for code in codes[:10]:
        clearance = get_recent_clearance(client, code, max_age_years)
        if clearance:
            return code

    return None


def fetch_clearance_by_knumber(client, k_number):
    """Fetch a 510(k) clearance by K-number. Returns clearance dict or None."""
    resp = client.get_510k(k_number)
    if resp.get("degraded") or not resp.get("results"):
        return None
    return resp["results"][0]


def fetch_peer_clearances(client, product_code, exclude_knumber, max_age_years, limit=10):
    """Fetch peer clearances for the same product code, excluding the source K-number."""
    cutoff_year = datetime.now().year - max_age_years
    resp = client.search_510k(
        product_code=product_code,
        year_start=str(cutoff_year),
        limit=limit + 5,
        sort="decision_date:desc",
    )
    if resp.get("degraded") or not resp.get("results"):
        return []
    peers = [
        r for r in resp["results"]
        if r.get("k_number", "").upper() != exclude_knumber.upper()
    ]
    return peers[:limit]


def build_device_profile(clearance, classification, peers):
    """Build device_profile.json combining clearance, classification, and peer data."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    product_code = clearance.get("product_code", "")
    device_name = clearance.get("device_name", "Unknown Device")

    definition = classification.get("definition", "") if classification else ""
    intended_use = definition if definition else ""

    if definition:
        device_description = f"{device_name}. {definition}"
    else:
        device_description = device_name

    peer_devices = []
    for p in peers:
        peer_devices.append({
            "k_number": p.get("k_number", ""),
            "device_name": p.get("device_name", ""),
            "applicant": p.get("applicant", ""),
            "decision_date": p.get("decision_date", ""),
            "product_code": p.get("product_code", product_code),
        })

    return {
        "source_clearance": clearance.get("k_number", ""),
        "device_name": device_name,
        "applicant": clearance.get("applicant", ""),
        "product_code": product_code,
        "intended_use": intended_use,
        "device_description": device_description,
        "device_class": classification.get("device_class", "") if classification else "",
        "regulation_number": classification.get("regulation_number", "") if classification else "",
        "review_panel": classification.get("review_panel", "") if classification else "",
        "implant_flag": classification.get("implant_flag", "") if classification else "",
        "classification_device_name": classification.get("device_name", "") if classification else "",
        "peer_devices": peer_devices,
        "created_at": now,
        "source": "seed_generator_example",
    }


def build_review_json_from_peers(project_name, product_code, device_name,
                                  source_clearance, peers):
    """Build review.json with the source clearance + peer predicates scored by recency."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    predicates = {}

    k_number = source_clearance.get("k_number", "K000000")
    predicates[k_number] = {
        "device_name": source_clearance.get("device_name", "Unknown Device"),
        "applicant": source_clearance.get("applicant", "Unknown Applicant"),
        "decision_date": source_clearance.get("decision_date", ""),
        "product_code": product_code,
        "decision": "accepted",
        "confidence_score": 95,
        "rationale": "Source clearance — same product code, most recent decision",
        "risk_flags": [],
        "source": "seed_generator_example",
    }

    base_score = 85
    for i, peer in enumerate(peers):
        peer_k = peer.get("k_number", "")
        if not peer_k or peer_k == k_number:
            continue
        score = max(base_score - (i * 2), 50)
        predicates[peer_k] = {
            "device_name": peer.get("device_name", "Unknown Device"),
            "applicant": peer.get("applicant", "Unknown Applicant"),
            "decision_date": peer.get("decision_date", ""),
            "product_code": peer.get("product_code", product_code),
            "decision": "accepted",
            "confidence_score": score,
            "rationale": f"Peer clearance #{i + 1} — same product code, scored by recency",
            "risk_flags": [],
            "source": "seed_generator_example",
        }

    accepted = len(predicates)
    scores = [p["confidence_score"] for p in predicates.values()]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    return {
        "project": project_name,
        "product_code": product_code,
        "device_name": device_name or "Unknown Device",
        "intended_use": "",
        "created_at": now,
        "reviewed_at": now,
        "predicates": predicates,
        "reference_devices": {},
        "summary": {
            "total_evaluated": accepted,
            "accepted": accepted,
            "rejected": 0,
            "average_score": avg_score,
        },
    }


def build_query_json(project_name, product_code, device_name, max_age_years,
                     source_knumber=None, intended_use=None):
    """Build query.json content matching fixture schema."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_year = datetime.now().year
    start_year = end_year - max_age_years
    result = {
        "project": project_name,
        "product_code": product_code,
        "device_name": device_name or "Unknown Device",
        "created_at": now,
        "filters": {
            "years": f"{start_year}-{end_year}",
            "product_codes": [product_code],
        },
    }
    if source_knumber:
        result["source_knumber"] = source_knumber
    if intended_use:
        result["intended_use"] = intended_use
    return result


def build_review_json(project_name, product_code, device_name, clearance):
    """Build review.json with one accepted predicate from a real clearance."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    k_number = clearance.get("k_number", "K000000")
    predicate_device = clearance.get("device_name", "Unknown Device")
    applicant = clearance.get("applicant", "Unknown Applicant")
    decision_date = clearance.get("decision_date", "")

    return {
        "project": project_name,
        "product_code": product_code,
        "device_name": device_name or "Unknown Device",
        "intended_use": "",
        "created_at": now,
        "reviewed_at": now,
        "predicates": {
            k_number: {
                "device_name": predicate_device,
                "applicant": applicant,
                "decision_date": decision_date,
                "product_code": product_code,
                "decision": "accepted",
                "confidence_score": 80,
                "rationale": "Seeded from recent openFDA clearance — same product code",
                "risk_flags": [],
                "source": "seed_generator",
            }
        },
        "reference_devices": {},
        "summary": {
            "total_evaluated": 1,
            "accepted": 1,
            "rejected": 0,
            "average_score": 80,
        },
    }


def print_summary(project_name, project_dir, product_code, panel, device_name,
                   clearance, dry_run, k_number=None, peer_count=0,
                   data_source=None):
    """Print a summary table and suggested commands."""
    print()
    if dry_run:
        print("=== DRY RUN — no files written ===")
    print()
    print(f"  Project:      {project_name}")
    print(f"  Directory:    {project_dir}")
    print(f"  Product Code: {product_code}")
    print(f"  Review Panel: {panel or 'unknown'}")
    print(f"  Device Name:  {device_name or 'unknown'}")
    if k_number:
        print(f"  Source K#:    {k_number}")
    if clearance:
        print(f"  Predicate:    {clearance.get('k_number', '?')} ({clearance.get('device_name', '?')})")
    if peer_count > 0:
        print(f"  Peer Devices: {peer_count}")
    if data_source:
        print(f"  Data Source:  {data_source}")
    print()

    if not dry_run:
        if k_number:
            print("Suggested commands:")
            print(f"  /fda:example --k-number {k_number} --project {project_name}")
            print()
        else:
            print("Suggested commands:")
            print(f"  /fda:compare-se --project {project_name} --infer --full-auto")
            print(f"  /fda:draft device-description --project {project_name}")
            print(f"  /fda:draft sterilization --project {project_name}")
            print(f"  /fda:draft doc --project {project_name}")
            print(f"  /fda:draft biocompatibility --project {project_name}")
            print(f"  /fda:consistency --project {project_name}")
            print(f"  /fda:pre-check --project {project_name}")
            print(f"  /fda:assemble --project {project_name}")
            print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate realistic FDA 510(k) test project directories from openFDA data.",
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--product-code",
        help="Use a specific product code",
    )
    mode_group.add_argument(
        "--k-number",
        help="Seed from a specific 510(k) clearance (e.g., K241335)",
    )
    mode_group.add_argument(
        "--random",
        action="store_true",
        default=True,
        help="Pick a truly random product code from openFDA (default)",
    )
    mode_group.add_argument(
        "--random-specialty",
        metavar="XX",
        help="Random product code within review panel XX (e.g., CV, OR, NE)",
    )

    # Data sourcing flags (mutually exclusive)
    data_group = parser.add_mutually_exclusive_group()
    data_group.add_argument(
        "--use-predicate-for-data",
        action="store_true",
        help="Use the predicate's 510(k) summary PDF as subject device data source",
    )
    data_group.add_argument(
        "--use-peer-for-data",
        action="store_true",
        help="Use a random peer clearance (same product code, NOT the predicate) "
             "as subject device data source",
    )

    parser.add_argument("--project", help="Project name (default: auto-generated)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without writing files")
    parser.add_argument(
        "--max-age-years",
        type=int,
        default=DEFAULT_MAX_AGE_YEARS,
        help=f"Predicate recency filter in years (default: {DEFAULT_MAX_AGE_YEARS})",
    )

    args = parser.parse_args()

    rng = random.Random(args.seed)
    client = FDAClient()

    product_code = None
    panel = None
    use_data_source = None  # "predicate" | "peer" | None

    if args.use_predicate_for_data:
        use_data_source = "predicate"
    elif args.use_peer_for_data:
        use_data_source = "peer"

    # --- K-number mode (example pipeline) ---
    if args.k_number:
        k_number = args.k_number.upper()
        print(f"Fetching clearance for {k_number}...")
        source_clearance = fetch_clearance_by_knumber(client, k_number)
        if not source_clearance:
            print(f"ERROR: Could not find clearance {k_number} in openFDA.", file=sys.stderr)
            sys.exit(1)

        product_code = source_clearance.get("product_code", "")
        device_name = source_clearance.get("device_name", "Unknown Device")

        print(f"Fetching classification for {product_code}...")
        classification = get_classification(client, product_code)
        if classification:
            panel = classification.get("review_panel", "")

        print(f"Fetching peer clearances for {product_code}...")
        peers = fetch_peer_clearances(
            client, product_code, k_number, args.max_age_years, limit=10,
        )
        print(f"  Found {len(peers)} peer clearances")

        project_name = args.project or make_project_name(
            panel or "XX", product_code, k_number=k_number,
        )
        project_dir = Path(args.output_dir) / project_name

        # Build all three files
        device_profile = build_device_profile(source_clearance, classification, peers)
        intended_use = device_profile.get("intended_use", "")

        query = build_query_json(
            project_name, product_code, device_name, args.max_age_years,
            source_knumber=k_number, intended_use=intended_use,
        )
        review = build_review_json_from_peers(
            project_name, product_code, device_name, source_clearance, peers,
        )

        if args.dry_run:
            print_summary(project_name, project_dir, product_code, panel, device_name,
                           source_clearance, dry_run=True, k_number=k_number,
                           peer_count=len(peers))
            print("query.json:")
            print(json.dumps(query, indent=2))
            print()
            print("review.json:")
            print(json.dumps(review, indent=2))
            print()
            print("device_profile.json:")
            print(json.dumps(device_profile, indent=2))
        else:
            project_dir.mkdir(parents=True, exist_ok=True)
            query_path = project_dir / "query.json"
            review_path = project_dir / "review.json"
            profile_path = project_dir / "device_profile.json"

            for path, data in [(query_path, query), (review_path, review),
                               (profile_path, device_profile)]:
                with open(path, "w") as f:
                    json.dump(data, f, indent=2)
                    f.write("\n")

            print_summary(project_name, project_dir, product_code, panel, device_name,
                           source_clearance, dry_run=False, k_number=k_number,
                           peer_count=len(peers))
            print(f"Created: {query_path}")
            print(f"Created: {review_path}")
            print(f"Created: {profile_path}")

        return

    # --- Selection mode ---
    if args.product_code:
        product_code = args.product_code.upper()

    elif args.random_specialty:
        panel = args.random_specialty.upper()
        print(f"Querying openFDA for a random {panel} product code...")
        product_code = pick_random_specialty_code(client, rng, panel, args.max_age_years)
        if not product_code:
            print(f"ERROR: Could not find a product code in panel {panel}.", file=sys.stderr)
            sys.exit(1)

    else:
        print("Querying openFDA for a random product code...")
        product_code = pick_random_product_code(client, rng, args.max_age_years)
        if not product_code:
            print("ERROR: Could not find a random product code from openFDA.", file=sys.stderr)
            sys.exit(1)

    # --- Fetch classification metadata ---
    print(f"Fetching classification for {product_code}...")
    classification = get_classification(client, product_code)
    device_name = None
    if classification:
        device_name = classification.get("device_name")
        if not panel:
            panel = classification.get("review_panel", "")

    # --- Fetch a recent clearance for the predicate ---
    print(f"Fetching recent clearance for {product_code}...")
    clearance = get_recent_clearance(client, product_code, args.max_age_years)
    if not clearance:
        print(f"WARNING: No clearance found for {product_code} in the last "
              f"{args.max_age_years} years. review.json will use placeholder data.",
              file=sys.stderr)

    # --- Fetch peer clearances (needed for --use-peer-for-data) ---
    peers = []
    predicate_k = clearance.get("k_number", "") if clearance else ""
    if use_data_source == "peer" and predicate_k:
        print(f"Fetching peer clearances for {product_code} (excluding {predicate_k})...")
        peers = fetch_peer_clearances(client, product_code, predicate_k,
                                       args.max_age_years, limit=10)
        print(f"  Found {len(peers)} peer clearances")

    # --- Data sourcing from PDF ---
    pdf_specs = None
    data_source_label = None
    if use_data_source and clearance:
        if use_data_source == "predicate":
            data_k = predicate_k
            data_source_label = f"predicate {data_k} PDF"
            print(f"\n--- Data sourcing: downloading predicate {data_k} PDF ---")
        elif use_data_source == "peer":
            if peers:
                # Pick a random peer
                data_peer = rng.choice(peers)
                data_k = data_peer.get("k_number", "")
                data_source_label = f"peer {data_k} PDF (not the predicate)"
                print(f"\n--- Data sourcing: downloading peer {data_k} PDF ---")
                print(f"  Peer device: {data_peer.get('device_name', '?')} "
                      f"({data_peer.get('applicant', '?')})")
            else:
                print("WARNING: No peer clearances found — cannot use --use-peer-for-data. "
                      "Falling back to no data.", file=sys.stderr)
                data_k = None
                use_data_source = None

        if use_data_source and data_k:
            # Check extraction cache first
            pdf_text = None
            cache_dir = Path(os.path.expanduser("~/fda-510k-data/extraction/cache"))
            cache_index = cache_dir / "index.json"
            if cache_index.exists():
                try:
                    with open(cache_index) as f:
                        idx = json.load(f)
                    if data_k in idx:
                        cached_path = Path(os.path.expanduser("~/fda-510k-data/extraction")) / idx[data_k]["file_path"]
                        if cached_path.exists():
                            with open(cached_path) as f:
                                cached_data = json.load(f)
                            pdf_text = cached_data.get("text", "")
                            if pdf_text and len(pdf_text.strip()) > 200:
                                print(f"  Using cached extraction for {data_k} ({len(pdf_text)} chars)")
                except Exception:
                    pass

            # Download if not cached
            if not pdf_text or len(pdf_text.strip()) < 200:
                pdf_text = download_pdf_text(data_k)

            if pdf_text:
                print(f"  Parsing device specs from {data_k} text...")
                pdf_specs = parse_device_specs(pdf_text, data_k, classification)

                # Show what was extracted
                sections = pdf_specs.get("extracted_sections", {})
                print(f"  Extracted sections: {', '.join(sections.keys()) or 'none'}")
                if pdf_specs.get("materials"):
                    print(f"  Materials found: {', '.join(pdf_specs['materials'][:5])}"
                          f"{'...' if len(pdf_specs.get('materials', [])) > 5 else ''}")
                if pdf_specs.get("sterilization_method"):
                    print(f"  Sterilization: {pdf_specs['sterilization_method']}")
                if pdf_specs.get("dimensions"):
                    print(f"  Dimensions: {json.dumps(pdf_specs['dimensions'])}")
                if pdf_specs.get("intended_use"):
                    ifu_preview = pdf_specs["intended_use"][:100]
                    print(f"  IFU: {ifu_preview}...")

                # Save raw text for reference
                if not args.dry_run:
                    project_name_tmp = args.project or make_project_name(panel or "XX", product_code)
                    project_dir_tmp = Path(args.output_dir) / project_name_tmp
                    project_dir_tmp.mkdir(parents=True, exist_ok=True)
                    raw_path = project_dir_tmp / f"source_device_text_{data_k}.txt"
                    with open(raw_path, "w") as f:
                        f.write(f"# Source: {data_k} 510(k) summary PDF\n")
                        f.write(f"# Extracted: {datetime.now(timezone.utc).isoformat()}\n")
                        f.write(f"# Mode: {use_data_source}\n\n")
                        f.write(pdf_text)
                    print(f"  Saved raw text: {raw_path}")
            else:
                print(f"  WARNING: Could not extract text from {data_k}. "
                      f"Proceeding without PDF data.", file=sys.stderr)

    # --- Build project ---
    project_name = args.project or make_project_name(panel or "XX", product_code)
    project_dir = Path(args.output_dir) / project_name

    query = build_query_json(project_name, product_code, device_name, args.max_age_years)

    # Build review.json — with IFU if we have PDF data
    intended_use = ""
    if pdf_specs and pdf_specs.get("intended_use"):
        intended_use = pdf_specs["intended_use"]

    if clearance:
        if pdf_specs:
            review = build_review_json_with_ifu(
                project_name, product_code, device_name, clearance,
                intended_use=intended_use,
            )
        else:
            review = build_review_json(project_name, product_code, device_name, clearance)
    else:
        review = build_review_json(project_name, product_code, device_name, {
            "k_number": "K000000",
            "device_name": device_name or "Placeholder Device",
            "applicant": "Placeholder Applicant",
            "decision_date": "",
        })

    # Build device_profile.json if we have PDF data
    device_profile = None
    if pdf_specs:
        device_profile = build_device_profile_with_pdf_data(
            pdf_specs, clearance or {}, classification, peers,
            data_source_mode=use_data_source,
        )
        # Also update query with intended use
        if intended_use:
            query["intended_use"] = intended_use

    # --- Write or preview ---
    if args.dry_run:
        print_summary(project_name, project_dir, product_code, panel, device_name,
                       clearance, dry_run=True, data_source=data_source_label)
        print("query.json:")
        print(json.dumps(query, indent=2))
        print()
        print("review.json:")
        print(json.dumps(review, indent=2))
        if device_profile:
            print()
            print("device_profile.json:")
            print(json.dumps(device_profile, indent=2))
    else:
        project_dir.mkdir(parents=True, exist_ok=True)
        query_path = project_dir / "query.json"
        review_path = project_dir / "review.json"

        with open(query_path, "w") as f:
            json.dump(query, f, indent=2)
            f.write("\n")
        with open(review_path, "w") as f:
            json.dump(review, f, indent=2)
            f.write("\n")

        files_created = [query_path, review_path]

        if device_profile:
            profile_path = project_dir / "device_profile.json"
            with open(profile_path, "w") as f:
                json.dump(device_profile, f, indent=2)
                f.write("\n")
            files_created.append(profile_path)

        print_summary(project_name, project_dir, product_code, panel, device_name,
                       clearance, dry_run=False, data_source=data_source_label)
        for fp in files_created:
            print(f"Created: {fp}")


if __name__ == "__main__":
    main()
