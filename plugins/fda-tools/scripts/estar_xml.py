#!/usr/bin/env python3
"""
eSTAR XML Extraction and Generation Tool

Extracts XFA form data from eSTAR PDFs and generates XML for re-import.
Uses pikepdf for PDF access and BeautifulSoup/lxml for XML parsing.

Supports both real FDA eSTAR template formats (nIVD v6.1, IVD v6.1, PreSTAR v2.1)
and the legacy format used by earlier versions of this tool.

Usage:
    python3 estar_xml.py extract <pdf-or-xml-path> [--output DIR]
    python3 estar_xml.py generate --project NAME [--template nIVD|IVD|PreSTAR] [--format real|legacy] [--output FILE]
    python3 estar_xml.py fields <pdf-path>  # List all XFA field names

References:
    - AF-VCD/pdf-xfa-tools patterns for XFA extraction
    - FDA eSTAR templates: nIVD v6.1, IVD v6.1, PreSTAR v2.1
    - Form IDs: FDA 4062 (nIVD), FDA 4078 (IVD), FDA 5064 (PreSTAR)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import pikepdf
except ImportError:
    pikepdf = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from lxml import etree
except ImportError:
    etree = None


# --- Real eSTAR Field Mappings (from actual FDA templates) ---

# Shared fields common to nIVD and IVD eSTAR templates.
# Keys are XFA field IDs (the last element of the XFA path); values are our
# internal import_data.json keys.
_BASE_FIELD_MAP = {
    # AdministrativeInformation.ApplicantInformation
    "ADTextField210": "applicant_name",        # Company Name
    "ADTextField140": "contact_first_name",    # First Name
    "ADTextField130": "contact_last_name",     # Last Name
    "ADTextField160": "email",
    "ADTextField170": "phone",
    "ADTextField220": "address_street",        # Address Line 1
    "ADTextField240": "address_city",
    "ADTextField250": "address_state",
    "ADTextField260": "address_zip",
    # DeviceDescription.Devices.Device
    "TradeName": "device_trade_name",
    "Model": "device_model",
    # DeviceDescription.Description
    "DDTextField400": "device_description_text",
    # Classification.USAKnownClassification
    "DDTextField517a": "product_code",
    "DDTextField519": "regulation_number",
    "DDTextField518": "device_class",
    # IndicationsForUse.Indications
    "IUTextField141": "indications_for_use",
    # IndicationsForUse.SubandDevice
    "IUTextField110": "ifu_device_name",
    # PredicatesSE.PredicateReference
    "ADTextField830": "predicate_k_number",
    "ADTextField840": "predicate_device_name",
    "ADTextField850": "predicate_manufacturer",
    # ReprocSter.Sterility.STMethod
    "STTextField110": "sterilization_method",
    # ReprocSter.ShelfLife
    "SLTextField110": "shelf_life_claim",
    # AdministrativeDocumentation.PMNSummary (510(k) Summary)
    "SSTextField110": "summary_applicant_name",
    "SSTextField220": "summary_device_trade_name",
    "SSTextField250": "summary_regulation_number",
    "SSTextField260": "summary_product_codes",
    "SSTextField400": "summary_text",
    # AdministrativeDocumentation.DoC
    "DCTextField120": "doc_company_name",
    "DCTextField140": "doc_device_trade_name",
    # AdministrativeDocumentation.TAStatement (Truthful & Accuracy)
    "TATextField105": "ta_certify_capacity",
    # Labeling
    "LBTextField110": "labeling_text",
    # Biocompatibility.PatientMaterials
    "BCTextField110": "biocompat_contact_type",
    "BCTextField120": "biocompat_contact_duration",
    "BCTextField130": "biocompat_materials",
    # SoftwareCyber
    "SWTextField110": "software_doc_level",
    # EMCWireless
    "EMTextField110": "emc_description",
    # PerformanceTesting.BenchTesting
    "PTTextField110": "performance_summary",
}

# nIVD eSTAR (FDA 4062) — extends base with nIVD-specific fields
NIVD_FIELD_MAP = {
    **_BASE_FIELD_MAP,
    # QualityManagement (nIVD-specific)
    "QMTextField110": "qms_info",
}

# IVD eSTAR (FDA 4078) — extends base with IVD-specific fields
IVD_FIELD_MAP = {
    **_BASE_FIELD_MAP,
    # AssayInstrumentInfo (IVD-specific)
    "DDTextField340": "instrument_name",
    "DDTextField350": "instrument_info",
    # AnalyticalPerformance (IVD-specific)
    "APTextField110": "analytical_performance",
    # ClinicalStudies (IVD-specific)
    "CSTextField110": "clinical_studies",
}

# PreSTAR (FDA 5064) — subset of base fields, no predicates/QM
PRESTAR_FIELD_MAP = {
    # Admin fields
    "ADTextField210": "applicant_name",
    "ADTextField140": "contact_first_name",
    "ADTextField130": "contact_last_name",
    "ADTextField160": "email",
    "ADTextField170": "phone",
    "ADTextField220": "address_street",
    "ADTextField240": "address_city",
    "ADTextField250": "address_state",
    "ADTextField260": "address_zip",
    # Device identification
    "TradeName": "device_trade_name",
    "Model": "device_model",
    "DDTextField400": "device_description_text",
    "DDTextField517a": "product_code",
    # IFU
    "IUTextField141": "indications_for_use",
    "IUTextField110": "ifu_device_name",
    # PreSTAR-specific
    "SCTextField110": "submission_characteristics",
    "QPTextField110": "questions_text",
}

# Maps template type to field map
TEMPLATE_FIELD_MAPS = {
    "nIVD": NIVD_FIELD_MAP,
    "IVD": IVD_FIELD_MAP,
    "PreSTAR": PRESTAR_FIELD_MAP,
}


# --- Legacy Field Mappings (backward compatibility with older generated XML) ---

LEGACY_FIELD_MAP = {
    # Applicant info
    "applicantname": "applicant_name",
    "contactname": "contact_name",
    "applicantaddress": "address",
    "street": "address_street",
    "city": "address_city",
    "state": "address_state",
    "zip": "address_zip",
    "country": "address_country",
    "phone": "phone",
    "email": "email",
    "devicename": "device_trade_name",
    "commonname": "device_common_name",
    # Classification
    "productcode": "product_code",
    "regulationnumber": "regulation_number",
    "deviceclass": "device_class",
    "panel": "review_panel",
    "panelcode": "review_panel",
    "submissiontype": "submission_type",
    "submissionnumber": "submission_number",
    # IFU (FDA 3881)
    "indicationstext": "indications_for_use",
    "indication": "indications_for_use",
    "prescription": "prescription_otc",
    # Content
    "descriptiontext": "device_description_text",
    "description": "device_description_text",
    "principleofoperation": "principle_of_operation",
    "comparisonnarrative": "se_discussion_text",
    "intendeduse": "intended_use_comparison",
    "techchrcomparison": "tech_comparison",
    "testingsummary": "performance_summary",
    "ifutext": "ifu_text",
    "softwarelevel": "software_doc_level",
    "method": "sterilization_method",
    "sterilization": "sterilization_method",
    "claimedlife": "shelf_life_claim",
    "shelflife": "shelf_life_claim",
    "materials": "biocompat_materials",
    # Biocompatibility
    "contacttype": "biocompat_contact_type",
    "contactduration": "biocompat_contact_duration",
    "materiallist": "biocompat_materials",
}

# Public alias for backward compatibility (tests import FIELD_MAP)
FIELD_MAP = LEGACY_FIELD_MAP

# K-number extraction pattern
KNUMBER_PATTERN = re.compile(
    r"\b(K\d{6}(?:/S\d{3})?|P\d{6}(?:/S\d{3})?|DEN\d{6,7}|N\d{4,5})\b"
)

# Section detection for narrative text extraction
SECTION_PATTERNS = {
    "device_description": re.compile(
        r"(?i)(?:device\s+description|description\s+of\s+(?:the\s+)?device)"
    ),
    "se_discussion": re.compile(
        r"(?i)(?:substantial\s+equivalen|predicate\s+device|SE\s+(?:comparison|discussion))"
    ),
    "performance": re.compile(
        r"(?i)(?:performance\s+(?:testing|data)|test(?:ing)?\s+(?:summary|results))"
    ),
    "indications": re.compile(
        r"(?i)(?:indications?\s+for\s+use|intended\s+use)"
    ),
    "biocompatibility": re.compile(
        r"(?i)(?:biocompatib|biological?\s+(?:evaluation|testing))"
    ),
    "sterilization": re.compile(
        r"(?i)(?:sterilizat|sterility\s+(?:assurance|testing))"
    ),
    "software": re.compile(
        r"(?i)(?:software\s+(?:description|documentation|level)|cybersecurity)"
    ),
    "labeling": re.compile(
        r"(?i)(?:label(?:ing)?\s+(?:requirements?|review)|instructions?\s+for\s+use)"
    ),
    "clinical": re.compile(
        r"(?i)(?:clinical\s+(?:data|evidence|studies?))"
    ),
    "shelf_life": re.compile(
        r"(?i)(?:shelf\s+life|accelerated\s+aging)"
    ),
    "emc_electrical": re.compile(
        r"(?i)(?:electromagnetic\s+compatib|EMC\b|electrical\s+safety)"
    ),
}


def check_dependencies():
    """Check that required libraries are installed."""
    missing = []
    if pikepdf is None:
        missing.append("pikepdf>=8.0.0")
    if BeautifulSoup is None:
        missing.append("beautifulsoup4>=4.12.0")
    if etree is None:
        missing.append("lxml>=4.9.0")
    if missing:
        print(f"ERROR: Missing dependencies: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        sys.exit(1)


# --- Template Detection ---

def detect_template_type(xml_string):
    """Detect which eSTAR template generated this XML.

    Returns: 'nIVD', 'IVD', 'PreSTAR', or 'legacy' (our old format).
    """
    # Legacy format: uses <form1> root with semantic element names
    if "<form1>" in xml_string and "<CoverLetter>" in xml_string:
        return "legacy"

    # Real template detection by Form ID
    if "Form FDA 4062" in xml_string or "FDA 4062" in xml_string:
        return "nIVD"
    if "Form FDA 4078" in xml_string or "FDA 4078" in xml_string:
        return "IVD"
    if "Form FDA 5064" in xml_string or "FDA 5064" in xml_string:
        return "PreSTAR"

    # Fallback: detect by unique section names
    if "SubmissionCharacteristics" in xml_string or "InvestigationalPlan" in xml_string:
        return "PreSTAR"
    if "AssayInstrumentInfo" in xml_string or "AnalyticalPerformance" in xml_string:
        return "IVD"

    # Real eSTAR uses <root> as top-level data element
    if "<root>" in xml_string:
        return "nIVD"  # default for root-format

    return "legacy"


def extract_xfa_from_pdf(pdf_path):
    """Extract XFA XML data stream from an eSTAR PDF.

    Returns the XFA datasets XML as a string, or None if not found.
    """
    check_dependencies()

    try:
        pdf = pikepdf.open(pdf_path)
    except Exception as e:
        print(f"ERROR: Cannot open PDF: {e}")
        return None

    # Look for XFA stream in AcroForm
    try:
        acroform = pdf.Root.get("/AcroForm")
        if acroform is None:
            print("ERROR: PDF has no AcroForm (not an XFA form)")
            return None

        xfa = acroform.get("/XFA")
        if xfa is None:
            print("ERROR: AcroForm has no XFA stream (not an eSTAR template)")
            return None

        # XFA can be a stream or an array of name/stream pairs
        if isinstance(xfa, pikepdf.Array):
            # Array format: [name1, stream1, name2, stream2, ...]
            datasets_xml = None
            for i in range(0, len(xfa), 2):
                name = str(xfa[i])
                if name == "datasets":
                    stream = xfa[i + 1]
                    if hasattr(stream, "read_bytes"):
                        datasets_xml = stream.read_bytes().decode("utf-8", errors="replace")
                    else:
                        datasets_xml = bytes(stream).decode("utf-8", errors="replace")
                    break
            if datasets_xml is None:
                # Try getting all streams concatenated
                all_xml = []
                for i in range(1, len(xfa), 2):
                    stream = xfa[i]
                    if hasattr(stream, "read_bytes"):
                        all_xml.append(stream.read_bytes().decode("utf-8", errors="replace"))
                    else:
                        all_xml.append(bytes(stream).decode("utf-8", errors="replace"))
                datasets_xml = "\n".join(all_xml)
            return datasets_xml
        elif hasattr(xfa, "read_bytes"):
            return xfa.read_bytes().decode("utf-8", errors="replace")
        else:
            return bytes(xfa).decode("utf-8", errors="replace")

    except Exception as e:
        print(f"ERROR: Failed to extract XFA: {e}")
        return None
    finally:
        pdf.close()


# --- Parsing ---

def parse_xml_data(xml_string):
    """Parse XFA XML and extract structured form data.

    Auto-detects format (real eSTAR or legacy) and returns a dict
    with mapped field names and values. Both formats produce the
    same import_data.json output structure.
    """
    check_dependencies()

    template_type = detect_template_type(xml_string)
    soup = BeautifulSoup(xml_string, "lxml-xml")
    result = {
        "metadata": {
            "extracted_at": datetime.now(tz=timezone.utc).isoformat(),
            "source_format": "xfa_xml",
            "template_type": template_type,
        },
        "applicant": {},
        "classification": {},
        "indications_for_use": {},
        "predicates": [],
        "sections": {},
        "raw_fields": {},
    }

    if template_type == "legacy":
        _parse_legacy_format(soup, result)
    else:
        _parse_real_format(soup, result, template_type)

    # Extract predicate K-numbers (works for both formats)
    _extract_predicates(soup, result)

    # Detect sections from narrative content
    for path, value in result["raw_fields"].items():
        if len(value) > 50:
            for section_name, pattern in SECTION_PATTERNS.items():
                if pattern.search(path) or (len(value) > 200 and pattern.search(value[:200])):
                    if section_name not in result["sections"]:
                        result["sections"][section_name] = value

    return result


def _parse_legacy_format(soup, result):
    """Parse XML in our legacy format (form1.CoverLetter.ApplicantName style)."""
    submission_number = None

    def walk(element, path=""):
        nonlocal submission_number
        if element.name is None:
            return
        current_path = f"{path}.{element.name}" if path else element.name
        direct_text = element.string
        full_text = element.get_text(strip=True)
        leaf_text = direct_text.strip() if direct_text and direct_text.strip() else None

        if full_text:
            result["raw_fields"][current_path] = full_text

        if leaf_text:
            path_lower = current_path.lower()
            tag_lower = element.name.lower()
            in_predicate_context = "predicatedevices" in path_lower or "performancetesting" in path_lower
            if not in_predicate_context:
                for field_suffix, mapped_key in LEGACY_FIELD_MAP.items():
                    if path_lower.endswith(field_suffix) or tag_lower == field_suffix:
                        _route_field(result, mapped_key, leaf_text)
                        if mapped_key == "submission_number":
                            submission_number = leaf_text

        for child in element.children:
            if hasattr(child, "name") and child.name:
                walk(child, current_path)

    walk(soup)

    # Filter submission number from predicates
    if submission_number:
        result["predicates"] = [
            p for p in result["predicates"]
            if p["k_number"] != submission_number
        ]


def _parse_real_format(soup, result, template_type):
    """Parse XML in real eSTAR format (root.AdministrativeInformation... style).

    Matches field IDs (e.g. ADTextField210) from the XFA field path to our
    internal keys using the template-specific field map.
    """
    field_map = TEMPLATE_FIELD_MAPS.get(template_type, NIVD_FIELD_MAP)

    def walk(element, path=""):
        if element.name is None:
            return
        current_path = f"{path}.{element.name}" if path else element.name
        direct_text = element.string
        full_text = element.get_text(strip=True)
        leaf_text = direct_text.strip() if direct_text and direct_text.strip() else None

        if full_text:
            result["raw_fields"][current_path] = full_text

        # Match by field ID (the element tag name itself)
        if leaf_text:
            tag = element.name
            if tag in field_map:
                mapped_key = field_map[tag]
                _route_field(result, mapped_key, leaf_text)

        for child in element.children:
            if hasattr(child, "name") and child.name:
                walk(child, current_path)

    walk(soup)


def _extract_predicates(soup, result):
    """Extract predicate K-numbers from any format."""
    # From predicate-related tags
    predicate_tags = soup.find_all(re.compile(
        r"(?i)predicate|kNumber|knumber|ADTextField830|ADTextField840|PredicateReference"
    ))
    for tag in predicate_tags:
        text = tag.get_text(strip=True)
        knumbers_in_tag = KNUMBER_PATTERN.findall(text)
        for kn in knumbers_in_tag:
            if kn not in [p.get("k_number") for p in result["predicates"]]:
                result["predicates"].append({"k_number": kn, "source": "xfa_xml"})

    # Scan SE-related raw fields
    se_text = ""
    for path, value in result["raw_fields"].items():
        path_lower = path.lower()
        if any(kw in path_lower for kw in ("se.", "predicate", "comparison", "PredicatesSE".lower())):
            se_text += " " + value
    knumbers = KNUMBER_PATTERN.findall(se_text)
    for kn in knumbers:
        if kn not in [p.get("k_number") for p in result["predicates"]]:
            result["predicates"].append({"k_number": kn, "source": "xfa_xml"})

    # Fallback: scan all text
    all_text = " ".join(result["raw_fields"].values())
    all_knumbers = KNUMBER_PATTERN.findall(all_text)
    for kn in all_knumbers:
        if kn not in [p.get("k_number") for p in result["predicates"]]:
            result["predicates"].append({"k_number": kn, "source": "full_text_scan"})


def _route_field(result, mapped_key, value):
    """Route a mapped field value to the correct location in result dict."""
    # Applicant fields
    if mapped_key in ("applicant_name", "contact_name", "contact_first_name",
                       "contact_last_name", "address",
                       "address_street", "address_city", "address_state", "address_zip",
                       "address_country", "phone", "email"):
        result["applicant"][mapped_key] = value
        # Assemble full address from components when we have street
        if mapped_key.startswith("address_"):
            parts = []
            a = result["applicant"]
            for k in ("address_street", "address_city", "address_state", "address_zip", "address_country"):
                if k in a:
                    parts.append(a[k])
            if parts:
                result["applicant"]["address"] = ", ".join(parts)
    # Classification fields
    elif mapped_key in ("product_code", "regulation_number", "device_class", "review_panel",
                        "submission_type", "device_trade_name", "device_common_name",
                        "device_model", "submission_date"):
        result["classification"][mapped_key] = value
    # IFU fields
    elif mapped_key in ("indications_for_use", "prescription_otc", "ifu_device_name"):
        result["indications_for_use"][mapped_key] = value
    # Predicate fields (route to classification for reference, predicates extracted separately)
    elif mapped_key in ("predicate_k_number", "predicate_device_name", "predicate_manufacturer"):
        result["classification"][mapped_key] = value
    # Section content
    else:
        result["sections"][mapped_key] = value


def extract_from_file(file_path, output_dir=None):
    """Extract data from an eSTAR PDF or plain XML file.

    Returns the path to the written import_data.json.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    # Determine if input is PDF or XML
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        print(f"Extracting XFA data from PDF: {file_path.name}")
        xml_string = extract_xfa_from_pdf(str(file_path))
        if xml_string is None:
            print("ERROR: Could not extract XFA data from PDF.")
            print("This may not be an eSTAR template, or it may use AcroForm instead of XFA.")
            print("If you exported XML from eSTAR, provide the .xml file directly.")
            sys.exit(1)
    elif suffix == ".xml":
        print(f"Parsing XML file: {file_path.name}")
        xml_string = file_path.read_text(encoding="utf-8", errors="replace")
    else:
        print(f"ERROR: Unsupported file type: {suffix}. Provide a .pdf or .xml file.")
        sys.exit(1)

    # Parse the XML
    data = parse_xml_data(xml_string)
    data["metadata"]["source_file"] = str(file_path)

    # Determine output directory
    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write import_data.json
    output_path = out_dir / "import_data.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    # Summary
    field_count = len([v for v in data["raw_fields"].values() if v.strip()])
    predicate_count = len(data["predicates"])
    section_count = len(data["sections"])
    product_code = data["classification"].get("product_code", "N/A")
    template_type = data["metadata"].get("template_type", "unknown")

    print(f"\nImport complete:")
    print(f"  Template type: {template_type}")
    print(f"  Fields extracted: {field_count}")
    print(f"  Product code: {product_code}")
    print(f"  Predicates found: {predicate_count}")
    if data["predicates"]:
        for p in data["predicates"][:5]:
            print(f"    {p['k_number']} (from {p['source']})")
        if len(data["predicates"]) > 5:
            print(f"    ... and {len(data['predicates']) - 5} more")
    print(f"  Section narratives: {section_count}")
    if data["sections"]:
        for s in list(data["sections"].keys())[:5]:
            print(f"    {s} ({len(data['sections'][s])} chars)")
    print(f"  Output: {output_path}")

    return str(output_path)


# --- XML Generation ---

def generate_xml(project_dir, template_type="nIVD", output_file=None, fmt="real"):
    """Generate eSTAR-compatible XML from project data for import into official template.

    Reads device_profile.json, review.json, draft_*.md, query.json, import_data.json,
    and presub_metadata.json to produce XML. Falls back through multiple data sources for each field.

    Args:
        project_dir: Path to the project directory.
        template_type: 'nIVD', 'IVD', or 'PreSTAR'.
        output_file: Optional output file path.
        fmt: 'real' for actual eSTAR XML paths, 'legacy' for old form1.* format.
    """
    project_dir = Path(project_dir)
    if not project_dir.exists():
        print(f"ERROR: Project directory not found: {project_dir}")
        sys.exit(1)

    # Check for empty project (no data files)
    data_files = [f for f in project_dir.iterdir() if f.is_file() and f.suffix in ('.json', '.csv', '.md')]
    if not data_files:
        print(f"WARNING: Project directory has no data files: {project_dir}")
        print("Run /fda:import or /fda:extract first to populate project data.")
        sys.exit(1)

    # Collect project data
    project_data = {}

    # Read query.json
    query_file = project_dir / "query.json"
    if query_file.exists():
        with open(query_file) as f:
            project_data["query"] = json.load(f)

    # Read review.json
    review_file = project_dir / "review.json"
    if review_file.exists():
        with open(review_file) as f:
            project_data["review"] = json.load(f)

    # Read device_profile.json (from seed generator or manual creation)
    profile_file = project_dir / "device_profile.json"
    if profile_file.exists():
        with open(profile_file) as f:
            project_data["profile"] = json.load(f)

    # Read import_data.json (from previous import)
    import_file = project_dir / "import_data.json"
    if import_file.exists():
        with open(import_file) as f:
            project_data["import"] = json.load(f)

    # Read presub_metadata.json (NEW - TICKET-001, from /fda:presub command)
    presub_file = project_dir / "presub_metadata.json"
    if presub_file.exists():
        try:
            with open(presub_file) as f:
                presub_data = json.load(f)

            # Validate schema version (CRITICAL-2 fix)
            presub_version = presub_data.get("version", "unknown")
            supported_versions = ["1.0"]
            if presub_version not in supported_versions:
                print(f"WARNING: presub_metadata.json version {presub_version} may be incompatible. "
                      f"Supported versions: {', '.join(supported_versions)}", file=sys.stderr)

            # Validate required fields
            required_fields = ["meeting_type", "questions_generated", "question_count"]
            missing_fields = [f for f in required_fields if f not in presub_data]
            if missing_fields:
                print(f"WARNING: presub_metadata.json missing required fields: {', '.join(missing_fields)}",
                      file=sys.stderr)

            project_data["presub_metadata"] = presub_data
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse presub_metadata.json: {e}", file=sys.stderr)
            # Don't load invalid data
        except Exception as e:
            print(f"ERROR: Failed to read presub_metadata.json: {e}", file=sys.stderr)

    # Read draft files
    drafts = {}
    for draft_file in project_dir.glob("draft_*.md"):
        section_name = draft_file.stem.replace("draft_", "")
        drafts[section_name] = draft_file.read_text(encoding="utf-8", errors="replace")
    project_data["drafts"] = drafts

    # Auto-detect template type if set to "auto"
    if template_type == "auto":
        template_type = _detect_template_from_data(project_data)
        print(f"Auto-detected template type: {template_type}")

    # Build XML
    if fmt == "legacy":
        xml = _build_legacy_xml(project_data, template_type)
    else:
        xml = _build_estar_xml(project_data, template_type)

    # Write output
    if output_file:
        out_path = Path(output_file)
    else:
        out_path = project_dir / f"estar_export_{template_type}.xml"

    out_path.write_text(xml, encoding="utf-8")
    print(f"eSTAR XML generated: {out_path}")
    print(f"Template type: {template_type}")
    print(f"Format: {fmt}")
    print(f"Data sources used:")
    for key in project_data:
        if key == "drafts":
            print(f"  drafts: {len(drafts)} section files")
        else:
            print(f"  {key}.json: found")
    print()
    print("Next steps:")
    print("  1. Open the official eSTAR template PDF in Adobe Acrobat")
    print("  2. Go to Form > Import Data (or Tools > Prepare Form > Import Data)")
    print(f"  3. Select: {out_path}")
    print("  4. Review populated fields for accuracy")
    print("  5. Add attachments (test reports, images) manually")
    return str(out_path)


def _detect_template_from_data(project_data):
    """Auto-detect appropriate eSTAR template type from project data.

    IVD product codes use FDA 4078 (IVD eSTAR).
    All other 510(k) devices use FDA 4062 (nIVD eSTAR).
    PreSTAR is only used for Pre-Submission meetings (not auto-detected here).
    """
    # IVD review panels: immunology, microbiology, chemistry, hematology, toxicology, pathology
    IVD_PANELS = {"IM", "MI", "CH", "HE", "TX", "PA"}

    profile = project_data.get("profile", {})
    import_data = project_data.get("import", {})
    query = project_data.get("query", {})
    classification = import_data.get("classification", {})

    panel = (
        classification.get("review_panel")
        or profile.get("review_panel")
        or ""
    ).upper()

    if panel in IVD_PANELS:
        return "IVD"

    # IVD regulation numbers are typically in 21 CFR 862-864
    reg_num = (
        classification.get("regulation_number")
        or profile.get("regulation_number")
        or ""
    )
    if reg_num:
        try:
            reg_prefix = int(str(reg_num).split(".")[0])
            if 862 <= reg_prefix <= 864:
                return "IVD"
        except (ValueError, IndexError):
            pass

    return "nIVD"


def _build_estar_xml(project_data, template_type):
    """Build real eSTAR-format XFA XML matching actual FDA template field paths."""

    if template_type == "IVD":
        return _build_ivd_xml(project_data)
    elif template_type == "PreSTAR":
        return _build_prestar_xml(project_data)
    else:
        return _build_nivd_xml(project_data)


def _collect_project_values(project_data):
    """Collect all field values from project data sources into a flat dict.

    Data priority: import_data > device_profile > query > review > drafts
    This ensures eSTAR fields get populated whether data comes from an import,
    a seed generator (device_profile.json), or manual drafts.
    """
    import_data = project_data.get("import", {})
    profile = project_data.get("profile", {})
    query = project_data.get("query", {})
    review = project_data.get("review", {})
    drafts = project_data.get("drafts", {})
    presub_metadata = project_data.get("presub_metadata", {})  # NEW - TICKET-001
    classification = import_data.get("classification", {})
    applicant = import_data.get("applicant", {})
    ifu = import_data.get("indications_for_use", {})
    sections = import_data.get("sections", {})
    profile_sections = profile.get("extracted_sections", {})

    def get_val(key, *sources):
        for source in sources:
            if isinstance(source, dict):
                val = source.get(key)
                if val:
                    return val
        return ""

    # Get product code (may be a list) — try import, profile, query
    pc = get_val("product_code", classification, profile, query)
    if isinstance(pc, list):
        pc = pc[0] if pc else ""
    pc = str(pc)

    # Get predicates from import or review
    predicates = import_data.get("predicates", [])
    if not predicates and review:
        for kn, info in review.get("predicates", {}).items():
            if info.get("decision") == "accepted":
                predicates.append({
                    "k_number": kn,
                    "device_name": info.get("device_name", ""),
                    "manufacturer": info.get("applicant", ""),
                })

    # Device trade name: import > profile > query > review
    trade_name = get_val("device_trade_name", classification)
    if not trade_name:
        trade_name = get_val("trade_name", profile)
    if not trade_name:
        trade_name = get_val("device_name", profile, query, review)

    # IFU: import > profile > query > review
    ifu_text = get_val("indications_for_use", ifu)
    if not ifu_text:
        ifu_text = get_val("intended_use", profile, query, review)

    # Device description: import sections > profile > profile extracted
    desc_text = get_val("device_description_text", sections)
    if not desc_text:
        desc_text = get_val("device_description", profile)
    if not desc_text:
        desc_text = profile_sections.get("device_description", "")

    # Materials from profile
    materials_list = profile.get("materials", [])
    materials_text = ", ".join(materials_list) if materials_list else ""

    # PreSTAR XML fields from presub_metadata.json (NEW - TICKET-001)
    presub_questions = ""
    presub_characteristics = ""

    if presub_metadata:
        # Load question bank to get full question text
        question_bank_path = os.path.join(os.path.dirname(__file__), "..", "data", "question_banks", "presub_questions.json")
        question_bank = {}
        if os.path.exists(question_bank_path):
            try:
                with open(question_bank_path) as f:
                    question_bank = json.load(f)
            except:
                pass

        # Format questions for QPTextField110
        questions_generated = presub_metadata.get("questions_generated", [])

        # Type checking for questions_generated (EDGE-2 fix)
        # Handle case where questions_generated is a string instead of list
        if not isinstance(questions_generated, list):
            print(f"Warning: questions_generated should be a list, got {type(questions_generated).__name__}",
                  file=sys.stderr)
            questions_generated = [questions_generated] if questions_generated else []

        if questions_generated and question_bank:
            questions_list = question_bank.get("questions", [])
            question_texts = []
            for q_id in questions_generated:
                # Find question by ID
                for q in questions_list:
                    if q.get("id") == q_id:
                        question_texts.append(f"{q_id}: {q.get('text', '')}")
                        break

            if question_texts:
                presub_questions = "\n\n".join([f"Question {i+1}:\n{text}" for i, text in enumerate(question_texts)])

        # Format submission characteristics for SCTextField110
        meeting_type = presub_metadata.get("meeting_type", "")
        meeting_type_display = {
            "formal": "Formal Pre-Submission Meeting",
            "written": "Written Feedback Request (Q-Sub)",
            "info": "Informational Meeting",
            "pre-ide": "Pre-IDE Meeting",
            "administrative": "Administrative Meeting",
            "info-only": "Informational Submission (No Meeting)"
        }.get(meeting_type, meeting_type)

        device_desc = presub_metadata.get("device_description", "")
        intended_use_presub = presub_metadata.get("intended_use", "")
        question_count = presub_metadata.get("question_count", 0)
        detection_rationale = presub_metadata.get("detection_rationale", "")

        characteristics_parts = []
        characteristics_parts.append(f"Meeting Type: {meeting_type_display}")
        if detection_rationale:
            characteristics_parts.append(f"Selection Rationale: {detection_rationale}")
        characteristics_parts.append(f"Number of Questions: {question_count}")
        if device_desc:
            characteristics_parts.append(f"\nDevice Description:\n{device_desc[:500]}")  # Truncate to 500 chars
        if intended_use_presub:
            characteristics_parts.append(f"\nProposed Indications for Use:\n{intended_use_presub[:500]}")  # Truncate to 500 chars

        presub_characteristics = "\n\n".join(characteristics_parts)

    return {
        "applicant_name": get_val("applicant_name", applicant) or get_val("applicant", profile),
        "contact_first_name": get_val("contact_first_name", applicant),
        "contact_last_name": get_val("contact_last_name", applicant),
        "contact_name": get_val("contact_name", applicant),
        "email": get_val("email", applicant),
        "phone": get_val("phone", applicant),
        "address_street": get_val("address_street", applicant),
        "address_city": get_val("address_city", applicant),
        "address_state": get_val("address_state", applicant),
        "address_zip": get_val("address_zip", applicant),
        "address": get_val("address", applicant),
        "device_trade_name": trade_name,
        "device_common_name": get_val("device_common_name", classification) or get_val("classification_device_name", profile),
        "device_model": get_val("device_model", classification),
        "product_code": pc,
        "regulation_number": get_val("regulation_number", classification, profile),
        "device_class": get_val("device_class", classification, profile),
        "review_panel": get_val("review_panel", classification, profile),
        "submission_type": get_val("submission_type", classification),
        "indications_for_use": ifu_text,
        "prescription_otc": get_val("prescription_otc", ifu),
        "sterilization_method": get_val("sterilization_method", sections, profile),
        "shelf_life_claim": get_val("shelf_life_claim", sections),
        "software_doc_level": get_val("software_doc_level", sections),
        "biocompat_contact_type": get_val("biocompat_contact_type", sections),
        "biocompat_contact_duration": get_val("biocompat_contact_duration", sections),
        "biocompat_materials": get_val("biocompat_materials", sections) or materials_text,
        "device_description_text": desc_text,
        "principle_of_operation": get_val("principle_of_operation", sections),
        "se_discussion_text": get_val("se_discussion_text", sections) or profile_sections.get("technological_characteristics", ""),
        "performance_summary": get_val("performance_summary", sections) or profile_sections.get("performance", ""),
        # Drafts
        "draft_device_description": drafts.get("device-description", ""),
        "draft_se_discussion": drafts.get("se-discussion", ""),
        "draft_performance": drafts.get("performance-summary", ""),
        "draft_510k_summary": drafts.get("510k-summary", ""),
        "draft_truthful_accuracy": drafts.get("truthful-accuracy", ""),
        "draft_financial_cert": drafts.get("financial-certification", ""),
        "draft_labeling": drafts.get("labeling", ""),
        "draft_software": drafts.get("software", ""),
        "draft_sterilization": drafts.get("sterilization", "") or get_val("sterilization_text", profile),
        "draft_shelf_life": drafts.get("shelf-life", ""),
        "draft_biocompatibility": drafts.get("biocompatibility", "") or profile_sections.get("biocompatibility", ""),
        "draft_emc": drafts.get("emc-electrical", ""),
        "draft_clinical": drafts.get("clinical", ""),
        "draft_doc": drafts.get("doc", ""),
        "draft_human_factors": drafts.get("human-factors", ""),
        # Predicates list
        "predicates": predicates,
        # Date
        "date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        # PreSTAR XML fields (NEW - TICKET-001)
        "presub_questions": presub_questions,
        "presub_characteristics": presub_characteristics,
    }


def _build_nivd_xml(project_data):
    """Build nIVD eSTAR XML (FDA 4062 format)."""
    v = _collect_project_values(project_data)
    e = _xml_escape

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">',
        '  <xfa:data>',
        '    <root>',
        '',
        '      <GeneralIntroduction>',
        f'        <GITextField110>Form FDA 4062 - nIVD eSTAR</GITextField110>',
        '      </GeneralIntroduction>',
        '',
        '      <AdministrativeInformation>',
        '        <ApplicantInformation>',
        f'          <ADTextField210>{e(v["applicant_name"])}</ADTextField210>',
        f'          <ADTextField140>{e(v["contact_first_name"] or v["contact_name"])}</ADTextField140>',
        f'          <ADTextField130>{e(v["contact_last_name"])}</ADTextField130>',
        f'          <ADTextField160>{e(v["email"])}</ADTextField160>',
        f'          <ADTextField170>{e(v["phone"])}</ADTextField170>',
        f'          <ADTextField220>{e(v["address_street"] or v["address"])}</ADTextField220>',
        f'          <ADTextField240>{e(v["address_city"])}</ADTextField240>',
        f'          <ADTextField250>{e(v["address_state"])}</ADTextField250>',
        f'          <ADTextField260>{e(v["address_zip"])}</ADTextField260>',
        '        </ApplicantInformation>',
        '      </AdministrativeInformation>',
        '',
        '      <DeviceDescription>',
        '        <Devices>',
        '          <Device>',
        f'            <TradeName>{e(v["device_trade_name"])}</TradeName>',
        f'            <Model>{e(v["device_model"])}</Model>',
        '          </Device>',
        '        </Devices>',
        '        <Description>',
        f'          <DDTextField400>{e(v["draft_device_description"] or v["device_description_text"])}</DDTextField400>',
        '        </Description>',
        '      </DeviceDescription>',
        '',
        '      <IndicationsForUse>',
        '        <SubandDevice>',
        f'          <IUTextField110>{e(v["device_trade_name"])}</IUTextField110>',
        '        </SubandDevice>',
        '        <Indications>',
        f'          <IUTextField141>{e(v["indications_for_use"])}</IUTextField141>',
        '        </Indications>',
        '      </IndicationsForUse>',
        '',
        '      <Classification>',
        '        <USAKnownClassification>',
        f'          <DDTextField517a>{e(v["product_code"])}</DDTextField517a>',
        f'          <DDTextField519>{e(v["regulation_number"])}</DDTextField519>',
        f'          <DDTextField518>{e(v["device_class"])}</DDTextField518>',
        '        </USAKnownClassification>',
        '      </Classification>',
        '',
        '      <PredicatesSE>',
        '        <PredicateReference>',
    ]

    # Add predicate devices
    for i, pred in enumerate(v["predicates"][:3]):
        lines.append(f'          <ADTextField{830 + i * 10}>{e(pred.get("k_number", ""))}</ADTextField{830 + i * 10}>')
        lines.append(f'          <ADTextField{840 + i * 10}>{e(pred.get("device_name", ""))}</ADTextField{840 + i * 10}>')
        lines.append(f'          <ADTextField{850 + i * 10}>{e(pred.get("manufacturer", ""))}</ADTextField{850 + i * 10}>')
    if not v["predicates"]:
        lines.append('          <ADTextField830></ADTextField830>')
        lines.append('          <ADTextField840></ADTextField840>')

    lines.extend([
        '        </PredicateReference>',
        '        <SubstantialEquivalence>',
        f'          <SETextField110>{e(v["draft_se_discussion"] or v["se_discussion_text"])}</SETextField110>',
        '        </SubstantialEquivalence>',
        '      </PredicatesSE>',
        '',
        '      <Labeling>',
        '        <GeneralLabeling>',
        f'          <LBTextField110>{e(v["draft_labeling"])}</LBTextField110>',
        '        </GeneralLabeling>',
        '      </Labeling>',
        '',
        '      <ReprocSter>',
        '        <Sterility>',
        '          <STMethod>',
        f'            <STTextField110>{e(v["sterilization_method"] or v["draft_sterilization"])}</STTextField110>',
        '          </STMethod>',
        '        </Sterility>',
        '        <ShelfLife>',
        f'          <SLTextField110>{e(v["shelf_life_claim"] or v["draft_shelf_life"])}</SLTextField110>',
        '        </ShelfLife>',
        '      </ReprocSter>',
        '',
        '      <Biocompatibility>',
        '        <PatientMaterials>',
        f'          <BCTextField110>{e(v["biocompat_contact_type"])}</BCTextField110>',
        f'          <BCTextField120>{e(v["biocompat_contact_duration"])}</BCTextField120>',
        f'          <BCTextField130>{e(v["biocompat_materials"])}</BCTextField130>',
        '        </PatientMaterials>',
    ])
    if v["draft_biocompatibility"]:
        lines.append(f'        <BCTextField400>{e(v["draft_biocompatibility"])}</BCTextField400>')
    lines.extend([
        '      </Biocompatibility>',
        '',
        '      <SoftwareCyber>',
        f'        <SWTextField110>{e(v["software_doc_level"] or v["draft_software"])}</SWTextField110>',
        '      </SoftwareCyber>',
        '',
        '      <EMCWireless>',
        f'        <EMTextField110>{e(v["draft_emc"])}</EMTextField110>',
        '      </EMCWireless>',
        '',
        '      <PerformanceTesting>',
        '        <BenchTesting>',
        f'          <PTTextField110>{e(v["draft_performance"] or v["performance_summary"])}</PTTextField110>',
        '        </BenchTesting>',
    ])
    if v["draft_clinical"]:
        lines.append('        <ClinicalTesting>')
        lines.append(f'          <CTTextField110>{e(v["draft_clinical"])}</CTTextField110>')
        lines.append('        </ClinicalTesting>')
    lines.extend([
        '      </PerformanceTesting>',
        '',
        '      <RiskManagement>',
        '      </RiskManagement>',
        '',
        '      <QualityManagement>',
        '      </QualityManagement>',
        '',
        '      <AdministrativeDocumentation>',
        '        <PMNSummary>',
        f'          <SSTextField110>{e(v["applicant_name"])}</SSTextField110>',
        f'          <SSTextField220>{e(v["device_trade_name"])}</SSTextField220>',
        f'          <SSTextField250>{e(v["regulation_number"])}</SSTextField250>',
        f'          <SSTextField260>{e(v["product_code"])}</SSTextField260>',
        f'          <SSTextField400>{e(v["draft_510k_summary"])}</SSTextField400>',
        '        </PMNSummary>',
        '        <TAStatement>',
        f'          <TATextField105>{e(v["draft_truthful_accuracy"])}</TATextField105>',
        '        </TAStatement>',
        '        <DoC>',
        f'          <DCTextField120>{e(v["applicant_name"])}</DCTextField120>',
        f'          <DCTextField140>{e(v["device_trade_name"])}</DCTextField140>',
    ])
    if v["draft_doc"]:
        lines.append(f'          <DCTextField400>{e(v["draft_doc"])}</DCTextField400>')
    lines.extend([
        '        </DoC>',
        '      </AdministrativeDocumentation>',
        '',
        '    </root>',
        '  </xfa:data>',
        '</xfa:datasets>',
    ])

    return "\n".join(lines)


def _build_ivd_xml(project_data):
    """Build IVD eSTAR XML (FDA 4078 format).

    Shares the nIVD structure but adds IVD-specific sections.
    """
    v = _collect_project_values(project_data)
    e = _xml_escape

    # Start with the same admin/device/IFU sections as nIVD
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">',
        '  <xfa:data>',
        '    <root>',
        '',
        '      <GeneralIntroduction>',
        '        <GITextField110>Form FDA 4078 - IVD eSTAR</GITextField110>',
        '      </GeneralIntroduction>',
        '',
        '      <AdministrativeInformation>',
        '        <ApplicantInformation>',
        f'          <ADTextField210>{e(v["applicant_name"])}</ADTextField210>',
        f'          <ADTextField140>{e(v["contact_first_name"] or v["contact_name"])}</ADTextField140>',
        f'          <ADTextField130>{e(v["contact_last_name"])}</ADTextField130>',
        f'          <ADTextField160>{e(v["email"])}</ADTextField160>',
        f'          <ADTextField170>{e(v["phone"])}</ADTextField170>',
        f'          <ADTextField220>{e(v["address_street"] or v["address"])}</ADTextField220>',
        f'          <ADTextField240>{e(v["address_city"])}</ADTextField240>',
        f'          <ADTextField250>{e(v["address_state"])}</ADTextField250>',
        f'          <ADTextField260>{e(v["address_zip"])}</ADTextField260>',
        '        </ApplicantInformation>',
        '      </AdministrativeInformation>',
        '',
        '      <DeviceDescription>',
        '        <Devices>',
        '          <Device>',
        f'            <TradeName>{e(v["device_trade_name"])}</TradeName>',
        f'            <Model>{e(v["device_model"])}</Model>',
        '          </Device>',
        '        </Devices>',
        '        <Description>',
        f'          <DDTextField400>{e(v["draft_device_description"] or v["device_description_text"])}</DDTextField400>',
        '        </Description>',
        '      </DeviceDescription>',
        '',
        '      <AssayInstrumentInfo>',
        f'        <DDTextField340>{e(v.get("instrument_name", ""))}</DDTextField340>',
        f'        <DDTextField350>{e(v.get("instrument_info", ""))}</DDTextField350>',
        '      </AssayInstrumentInfo>',
        '',
        '      <IndicationsForUse>',
        '        <SubandDevice>',
        f'          <IUTextField110>{e(v["device_trade_name"])}</IUTextField110>',
        '        </SubandDevice>',
        '        <Indications>',
        f'          <IUTextField141>{e(v["indications_for_use"])}</IUTextField141>',
        '        </Indications>',
        '      </IndicationsForUse>',
        '',
        '      <Classification>',
        '        <USAKnownClassification>',
        f'          <DDTextField517a>{e(v["product_code"])}</DDTextField517a>',
        f'          <DDTextField519>{e(v["regulation_number"])}</DDTextField519>',
        f'          <DDTextField518>{e(v["device_class"])}</DDTextField518>',
        '        </USAKnownClassification>',
        '      </Classification>',
        '',
        '      <PredicatesSE>',
        '        <PredicateReference>',
    ]

    for i, pred in enumerate(v["predicates"][:3]):
        lines.append(f'          <ADTextField{830 + i * 10}>{e(pred.get("k_number", ""))}</ADTextField{830 + i * 10}>')
        lines.append(f'          <ADTextField{840 + i * 10}>{e(pred.get("device_name", ""))}</ADTextField{840 + i * 10}>')
    if not v["predicates"]:
        lines.append('          <ADTextField830></ADTextField830>')

    lines.extend([
        '        </PredicateReference>',
        '        <SubstantialEquivalence>',
        f'          <SETextField110>{e(v["draft_se_discussion"] or v["se_discussion_text"])}</SETextField110>',
        '        </SubstantialEquivalence>',
        '      </PredicatesSE>',
        '',
        '      <AnalyticalPerformance>',
        f'        <APTextField110></APTextField110>',
        '      </AnalyticalPerformance>',
        '',
        '      <ClinicalStudies>',
    ])
    if v["draft_clinical"]:
        lines.append(f'        <CSTextField110>{e(v["draft_clinical"])}</CSTextField110>')
    lines.extend([
        '      </ClinicalStudies>',
        '',
        '      <Labeling>',
        '        <GeneralLabeling>',
        f'          <LBTextField110>{e(v["draft_labeling"])}</LBTextField110>',
        '        </GeneralLabeling>',
        '      </Labeling>',
        '',
        '      <ReprocSter>',
        '        <Sterility>',
        '          <STMethod>',
        f'            <STTextField110>{e(v["sterilization_method"] or v["draft_sterilization"])}</STTextField110>',
        '          </STMethod>',
        '        </Sterility>',
        '        <ShelfLife>',
        f'          <SLTextField110>{e(v["shelf_life_claim"] or v["draft_shelf_life"])}</SLTextField110>',
        '        </ShelfLife>',
        '      </ReprocSter>',
        '',
        '      <Biocompatibility>',
        '        <PatientMaterials>',
        f'          <BCTextField110>{e(v["biocompat_contact_type"])}</BCTextField110>',
        f'          <BCTextField120>{e(v["biocompat_contact_duration"])}</BCTextField120>',
        f'          <BCTextField130>{e(v["biocompat_materials"])}</BCTextField130>',
        '        </PatientMaterials>',
        '      </Biocompatibility>',
        '',
        '      <SoftwareCyber>',
        f'        <SWTextField110>{e(v["software_doc_level"] or v["draft_software"])}</SWTextField110>',
        '      </SoftwareCyber>',
        '',
        '      <EMCWireless>',
        f'        <EMTextField110>{e(v["draft_emc"])}</EMTextField110>',
        '      </EMCWireless>',
        '',
        '      <PerformanceTesting>',
        '        <BenchTesting>',
        f'          <PTTextField110>{e(v["draft_performance"] or v["performance_summary"])}</PTTextField110>',
        '        </BenchTesting>',
        '      </PerformanceTesting>',
        '',
        '      <AdministrativeDocumentation>',
        '        <PMNSummary>',
        f'          <SSTextField110>{e(v["applicant_name"])}</SSTextField110>',
        f'          <SSTextField220>{e(v["device_trade_name"])}</SSTextField220>',
        f'          <SSTextField250>{e(v["regulation_number"])}</SSTextField250>',
        f'          <SSTextField260>{e(v["product_code"])}</SSTextField260>',
        f'          <SSTextField400>{e(v["draft_510k_summary"])}</SSTextField400>',
        '        </PMNSummary>',
        '        <TAStatement>',
        f'          <TATextField105>{e(v["draft_truthful_accuracy"])}</TATextField105>',
        '        </TAStatement>',
        '        <DoC>',
        f'          <DCTextField120>{e(v["applicant_name"])}</DCTextField120>',
        f'          <DCTextField140>{e(v["device_trade_name"])}</DCTextField140>',
        '        </DoC>',
        '      </AdministrativeDocumentation>',
        '',
        '    </root>',
        '  </xfa:data>',
        '</xfa:datasets>',
    ])

    return "\n".join(lines)


def _build_prestar_xml(project_data):
    """Build PreSTAR XML (FDA 5064 format).

    Simpler structure: admin, device, IFU, questions — no predicates or QM.
    """
    v = _collect_project_values(project_data)
    e = _xml_escape

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">',
        '  <xfa:data>',
        '    <root>',
        '',
        '      <GeneralIntroduction>',
        '        <GITextField110>Form FDA 5064 - PreSTAR</GITextField110>',
        '      </GeneralIntroduction>',
        '',
        '      <AdministrativeInformation>',
        '        <ApplicantInformation>',
        f'          <ADTextField210>{e(v["applicant_name"])}</ADTextField210>',
        f'          <ADTextField140>{e(v["contact_first_name"] or v["contact_name"])}</ADTextField140>',
        f'          <ADTextField130>{e(v["contact_last_name"])}</ADTextField130>',
        f'          <ADTextField160>{e(v["email"])}</ADTextField160>',
        f'          <ADTextField170>{e(v["phone"])}</ADTextField170>',
        f'          <ADTextField220>{e(v["address_street"] or v["address"])}</ADTextField220>',
        f'          <ADTextField240>{e(v["address_city"])}</ADTextField240>',
        f'          <ADTextField250>{e(v["address_state"])}</ADTextField250>',
        f'          <ADTextField260>{e(v["address_zip"])}</ADTextField260>',
        '        </ApplicantInformation>',
        '      </AdministrativeInformation>',
        '',
        '      <DeviceDescription>',
        '        <Devices>',
        '          <Device>',
        f'            <TradeName>{e(v["device_trade_name"])}</TradeName>',
        f'            <Model>{e(v["device_model"])}</Model>',
        '          </Device>',
        '        </Devices>',
        '        <Description>',
        f'          <DDTextField400>{e(v["draft_device_description"] or v["device_description_text"])}</DDTextField400>',
        '        </Description>',
        '      </DeviceDescription>',
        '',
        '      <IndicationsForUse>',
        '        <SubandDevice>',
        f'          <IUTextField110>{e(v["device_trade_name"])}</IUTextField110>',
        '        </SubandDevice>',
        '        <Indications>',
        f'          <IUTextField141>{e(v["indications_for_use"])}</IUTextField141>',
        '        </Indications>',
        '      </IndicationsForUse>',
        '',
        '      <Classification>',
        '        <USAKnownClassification>',
        f'          <DDTextField517a>{e(v["product_code"])}</DDTextField517a>',
        '        </USAKnownClassification>',
        '      </Classification>',
        '',
        '      <SubmissionCharacteristics>',
        f'        <SCTextField110>{e(v["presub_characteristics"])}</SCTextField110>',
        '      </SubmissionCharacteristics>',
        '',
        '      <Questions>',
        f'        <QPTextField110>{e(v["presub_questions"])}</QPTextField110>',
        '      </Questions>',
        '',
        '    </root>',
        '  </xfa:data>',
        '</xfa:datasets>',
    ]

    return "\n".join(lines)


def _build_legacy_xml(project_data, _template_type):
    """Build legacy-format XFA XML (form1.* paths) for backward compatibility.

    Args:
        project_data: Project data dictionary
        _template_type: Template type (unused - legacy format is template-agnostic)
    """
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">',
        '  <xfa:data>',
        '    <form1>',
    ]

    def get_val(key, *sources):
        for source in sources:
            if isinstance(source, dict):
                val = source.get(key)
                if val:
                    return val
        return ""

    import_data = project_data.get("import", {})
    query = project_data.get("query", {})
    review = project_data.get("review", {})
    drafts = project_data.get("drafts", {})
    classification = import_data.get("classification", {})
    applicant = import_data.get("applicant", {})
    ifu = import_data.get("indications_for_use", {})

    # Cover Letter
    lines.append("      <CoverLetter>")
    lines.append(f"        <ApplicantName>{_xml_escape(get_val('applicant_name', applicant))}</ApplicantName>")
    lines.append(f"        <ContactName>{_xml_escape(get_val('contact_name', applicant))}</ContactName>")
    lines.append(f"        <Address>{_xml_escape(get_val('address', applicant))}</Address>")
    lines.append(f"        <Phone>{_xml_escape(get_val('phone', applicant))}</Phone>")
    lines.append(f"        <Email>{_xml_escape(get_val('email', applicant))}</Email>")
    lines.append(f"        <Date>{datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}</Date>")
    lines.append(f"        <DeviceName>{_xml_escape(get_val('device_trade_name', classification))}</DeviceName>")
    lines.append(f"        <CommonName>{_xml_escape(get_val('device_common_name', classification))}</CommonName>")
    lines.append("      </CoverLetter>")

    # FDA 3514 (Cover Sheet)
    lines.append("      <FDA3514>")
    pc = get_val("product_code", classification) or get_val("product_code", query)
    if isinstance(pc, list):
        pc = pc[0] if pc else ""
    lines.append(f"        <ProductCode>{_xml_escape(str(pc))}</ProductCode>")
    lines.append(f"        <RegulationNumber>{_xml_escape(get_val('regulation_number', classification))}</RegulationNumber>")
    lines.append(f"        <DeviceClass>{_xml_escape(get_val('device_class', classification))}</DeviceClass>")
    lines.append(f"        <Panel>{_xml_escape(get_val('review_panel', classification))}</Panel>")
    lines.append(f"        <SubmissionType>{_xml_escape(get_val('submission_type', classification))}</SubmissionType>")
    lines.append("      </FDA3514>")

    # FDA 3881 (Indications for Use)
    lines.append("      <FDA3881>")
    lines.append(f"        <DeviceName>{_xml_escape(get_val('device_trade_name', classification))}</DeviceName>")
    lines.append(f"        <IndicationsText>{_xml_escape(get_val('indications_for_use', ifu))}</IndicationsText>")
    lines.append(f"        <Prescription>{_xml_escape(get_val('prescription_otc', ifu))}</Prescription>")
    lines.append("      </FDA3881>")

    # Section 03: 510(k) Summary
    summary_text = drafts.get("510k-summary", "")
    lines.append("      <Summary>")
    lines.append(f"        <SummaryText>{_xml_escape(summary_text)}</SummaryText>")
    lines.append("      </Summary>")

    # Section 04: Truthful and Accuracy Statement
    ta_text = drafts.get("truthful-accuracy", "")
    lines.append("      <TruthfulAccuracy>")
    lines.append(f"        <StatementText>{_xml_escape(ta_text)}</StatementText>")
    lines.append("      </TruthfulAccuracy>")

    # Section 05: Financial Certification
    fc_text = drafts.get("financial-certification", "")
    lines.append("      <FinancialCert>")
    lines.append(f"        <CertificationText>{_xml_escape(fc_text)}</CertificationText>")
    lines.append("      </FinancialCert>")

    # Device Description
    desc_text = drafts.get("device-description", "")
    sections_data = import_data.get("sections", {})
    lines.append("      <DeviceDescription>")
    lines.append(f"        <DescriptionText>{_xml_escape(desc_text or get_val('device_description_text', sections_data))}</DescriptionText>")
    lines.append(f"        <PrincipleOfOperation>{_xml_escape(get_val('principle_of_operation', sections_data))}</PrincipleOfOperation>")
    lines.append("      </DeviceDescription>")

    # Substantial Equivalence
    lines.append("      <SE>")
    se_text = drafts.get("se-discussion", "")
    lines.append(f"        <ComparisonNarrative>{_xml_escape(se_text or get_val('se_discussion_text', sections_data))}</ComparisonNarrative>")
    lines.append(f"        <IntendedUseComparison>{_xml_escape(get_val('intended_use_comparison', sections_data))}</IntendedUseComparison>")
    lines.append(f"        <TechCharComparison>{_xml_escape(get_val('tech_comparison', sections_data))}</TechCharComparison>")

    predicates = import_data.get("predicates", [])
    if not predicates and review:
        for kn, info in review.get("predicates", {}).items():
            if info.get("decision") == "accepted":
                predicates.append({
                    "k_number": kn,
                    "device_name": info.get("device_name", ""),
                    "manufacturer": info.get("applicant", ""),
                })
    for i, pred in enumerate(predicates[:3]):
        lines.append(f"        <PredicateDevice{i}>")
        lines.append(f"          <KNumber>{_xml_escape(pred.get('k_number', ''))}</KNumber>")
        lines.append(f"          <DeviceName>{_xml_escape(pred.get('device_name', ''))}</DeviceName>")
        lines.append(f"          <Manufacturer>{_xml_escape(pred.get('manufacturer', ''))}</Manufacturer>")
        lines.append(f"        </PredicateDevice{i}>")
    lines.append("      </SE>")

    # Performance Testing
    perf_text = drafts.get("performance-summary", "")
    lines.append("      <Performance>")
    lines.append(f"        <TestingSummary>{_xml_escape(perf_text or get_val('performance_summary', sections_data))}</TestingSummary>")
    lines.append("      </Performance>")

    # Labeling
    label_text = drafts.get("labeling", "")
    lines.append("      <Labeling>")
    lines.append(f"        <IFUText>{_xml_escape(label_text or get_val('ifu_text', sections_data))}</IFUText>")
    lines.append("      </Labeling>")

    # Software
    sw_text = drafts.get("software", "")
    lines.append("      <Software>")
    lines.append(f"        <SoftwareLevel>{_xml_escape(get_val('software_doc_level', sections_data))}</SoftwareLevel>")
    if sw_text:
        lines.append(f"        <Description>{_xml_escape(sw_text)}</Description>")
    lines.append("      </Software>")

    # Sterilization
    ster_text = drafts.get("sterilization", "")
    lines.append("      <Sterilization>")
    lines.append(f"        <Method>{_xml_escape(get_val('sterilization_method', sections_data))}</Method>")
    if ster_text:
        lines.append(f"        <Description>{_xml_escape(ster_text)}</Description>")
    lines.append("      </Sterilization>")

    # Shelf Life
    sl_text = drafts.get("shelf-life", "")
    lines.append("      <ShelfLife>")
    lines.append(f"        <ClaimedLife>{_xml_escape(get_val('shelf_life_claim', sections_data))}</ClaimedLife>")
    if sl_text:
        lines.append(f"        <Description>{_xml_escape(sl_text)}</Description>")
    lines.append("      </ShelfLife>")

    # Biocompatibility
    bio_text = drafts.get("biocompatibility", "")
    lines.append("      <Biocompat>")
    lines.append(f"        <ContactType>{_xml_escape(get_val('biocompat_contact_type', sections_data))}</ContactType>")
    lines.append(f"        <ContactDuration>{_xml_escape(get_val('biocompat_contact_duration', sections_data))}</ContactDuration>")
    lines.append(f"        <MaterialList>{_xml_escape(get_val('biocompat_materials', sections_data))}</MaterialList>")
    if bio_text:
        lines.append(f"        <EvaluationSummary>{_xml_escape(bio_text)}</EvaluationSummary>")
    lines.append("      </Biocompat>")

    # EMC/Electrical
    emc_text = drafts.get("emc-electrical", "")
    lines.append("      <EMC>")
    if emc_text:
        lines.append(f"        <Description>{_xml_escape(emc_text)}</Description>")
    lines.append("      </EMC>")

    # Clinical
    clin_text = drafts.get("clinical", "")
    lines.append("      <Clinical>")
    if clin_text:
        lines.append(f"        <Description>{_xml_escape(clin_text)}</Description>")
    lines.append("      </Clinical>")

    # Standards / Declaration of Conformity
    doc_text = drafts.get("doc", "")
    lines.append("      <Standards>")
    if doc_text:
        lines.append(f"        <DeclarationOfConformity>{_xml_escape(doc_text)}</DeclarationOfConformity>")
    lines.append("      </Standards>")

    # Human Factors
    hf_text = drafts.get("human-factors", "")
    lines.append("      <HumanFactors>")
    if hf_text:
        lines.append(f"        <Description>{_xml_escape(hf_text)}</Description>")
    lines.append("      </HumanFactors>")

    lines.append("    </form1>")
    lines.append("  </xfa:data>")
    lines.append("</xfa:datasets>")

    return "\n".join(lines)


def _xml_escape(text):
    """Escape special XML characters and filter control characters.

    Filters control characters (U+0000-U+001F except tab/newline/carriage return)
    to prevent XML injection and ensure FDA eSTAR compatibility.
    """
    if not text:
        return ""
    text = str(text)

    # Filter control characters (except tab, newline, carriage return)
    # U+0000-U+001F except U+0009 (tab), U+000A (newline), U+000D (carriage return)
    filtered_text = []
    for char in text:
        code = ord(char)
        if code < 0x20 and code not in (0x09, 0x0A, 0x0D):
            # Skip control characters
            continue
        filtered_text.append(char)
    text = ''.join(filtered_text)

    # Escape XML special characters
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


def list_fields(pdf_path):
    """List all XFA field names found in an eSTAR PDF.

    Groups fields by section for clearer output.
    """
    xml_string = extract_xfa_from_pdf(pdf_path)
    if xml_string is None:
        return

    if BeautifulSoup is None:
        print("Error: BeautifulSoup not installed. Install with: pip install beautifulsoup4 lxml")
        return

    template_type = detect_template_type(xml_string)
    soup = BeautifulSoup(xml_string, "lxml-xml")

    fields = []
    current_section = None

    def walk(element, path="", depth=0):
        nonlocal current_section
        if element.name is None:
            return
        current_path = f"{path}.{element.name}" if path else element.name
        text = element.get_text(strip=True)

        # Track top-level sections for grouping
        if depth == 2:  # Direct children of <root> or <form1>
            current_section = element.name

        if text:
            fields.append((current_section or "ungrouped", current_path, text[:80]))
        for child in element.children:
            if hasattr(child, "name") and child.name:
                walk(child, current_path, depth + 1)

    walk(soup)

    print(f"XFA Fields in: {pdf_path}")
    print(f"Template type: {template_type}")
    print(f"Total fields with data: {len(fields)}")
    print()

    # Group by section
    last_section = None
    for section, path, preview in sorted(fields, key=lambda x: (x[0], x[1])):
        if section != last_section:
            print(f"\n--- {section} ---")
            last_section = section
        print(f"  {path}")
        if preview:
            print(f"    = {preview}{'...' if len(preview) >= 80 else ''}")


def get_settings():
    """Read plugin settings to find projects_dir."""
    settings_path = os.path.expanduser("~/.claude/fda-tools.local.md")
    projects_dir = os.path.expanduser("~/fda-510k-data/projects")
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            content = f.read()
        m = re.search(r"projects_dir:\s*(.+)", content)
        if m:
            projects_dir = os.path.expanduser(m.group(1).strip())
    return projects_dir


def main():
    parser = argparse.ArgumentParser(
        description="eSTAR XML Extraction and Generation Tool"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Extract command
    extract_parser = subparsers.add_parser(
        "extract", help="Extract data from eSTAR PDF or XML"
    )
    extract_parser.add_argument("file", help="Path to eSTAR PDF or exported XML file")
    extract_parser.add_argument("--output", "-o", help="Output directory for import_data.json")
    extract_parser.add_argument("--project", "-p", help="Project name (writes to project dir)")

    # Generate command
    gen_parser = subparsers.add_parser(
        "generate", help="Generate eSTAR XML from project data"
    )
    gen_parser.add_argument("--project", "-p", required=True, help="Project name")
    gen_parser.add_argument(
        "--template", "-t", default="nIVD",
        choices=["nIVD", "IVD", "PreSTAR"],
        help="eSTAR template type (default: nIVD)"
    )
    gen_parser.add_argument(
        "--format", "-f", default="real",
        choices=["real", "legacy"],
        help="XML format: 'real' for FDA template paths (default), 'legacy' for old form1.* paths"
    )
    gen_parser.add_argument("--output", "-o", help="Output XML file path")

    # Fields command
    fields_parser = subparsers.add_parser(
        "fields", help="List XFA field names in an eSTAR PDF"
    )
    fields_parser.add_argument("file", help="Path to eSTAR PDF")

    args = parser.parse_args()

    if args.command == "extract":
        projects_dir = get_settings()
        output_dir = args.output
        if args.project:
            output_dir = os.path.join(projects_dir, args.project)
        extract_from_file(args.file, output_dir)

    elif args.command == "generate":
        projects_dir = get_settings()
        project_dir = os.path.join(projects_dir, args.project)
        generate_xml(project_dir, args.template, args.output, args.format)

    elif args.command == "fields":
        check_dependencies()
        list_fields(args.file)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
