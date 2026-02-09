#!/usr/bin/env python3
"""
eSTAR XML Extraction and Generation Tool

Extracts XFA form data from eSTAR PDFs and generates XML for re-import.
Uses pikepdf for PDF access and BeautifulSoup/lxml for XML parsing.

Usage:
    python3 estar_xml.py extract <pdf-or-xml-path> [--output DIR]
    python3 estar_xml.py generate --project NAME [--template nIVD|IVD|PreSTAR] [--output FILE]
    python3 estar_xml.py fields <pdf-path>  # List all XFA field names

References:
    - AF-VCD/pdf-xfa-tools patterns for XFA extraction
    - FDA eSTAR templates: nIVD v6, IVD v6, PreSTAR v2
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
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


# --- XFA Field Mappings ---

# Maps XFA field path suffixes (case-insensitive) to structured import_data.json keys.
# Both XFA-style (ApplicantName) and standard XML (applicantName) tags are handled
# by performing case-insensitive suffix matching.
FIELD_MAP = {
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


def parse_xml_data(xml_string):
    """Parse XFA XML and extract structured form data.

    Returns a dict with mapped field names and values.
    """
    check_dependencies()

    soup = BeautifulSoup(xml_string, "lxml-xml")
    result = {
        "metadata": {
            "extracted_at": datetime.now(tz=__import__('datetime').timezone.utc).isoformat(),
            "source_format": "xfa_xml",
        },
        "applicant": {},
        "classification": {},
        "indications_for_use": {},
        "predicates": [],
        "sections": {},
        "raw_fields": {},
    }

    # Track the submission number to filter it from predicates later
    submission_number = None

    # Extract all text nodes with their paths (case-insensitive field matching)
    def walk(element, path=""):
        nonlocal submission_number
        if element.name is None:
            return
        current_path = f"{path}.{element.name}" if path else element.name
        # Only use leaf-node text (direct text, not recursive) for field mapping
        direct_text = element.string
        full_text = element.get_text(strip=True)
        leaf_text = direct_text.strip() if direct_text and direct_text.strip() else None

        if full_text:
            result["raw_fields"][current_path] = full_text

        # Map known fields using leaf text (avoids concatenated parent text)
        # Skip FIELD_MAP matching for elements inside predicateDevices or
        # performanceTesting — those contain predicate/test-specific data
        # that should NOT overwrite device-level fields.
        if leaf_text:
            path_lower = current_path.lower()
            tag_lower = element.name.lower()
            in_predicate_context = "predicatedevices" in path_lower or "performancetesting" in path_lower
            if not in_predicate_context:
                for field_suffix, mapped_key in FIELD_MAP.items():
                    if path_lower.endswith(field_suffix) or tag_lower == field_suffix:
                        _route_field(result, mapped_key, leaf_text)
                        if mapped_key == "submission_number":
                            submission_number = leaf_text

        for child in element.children:
            if hasattr(child, "name") and child.name:
                walk(child, current_path)

    walk(soup)

    # Extract predicate K-numbers from predicate-related fields
    # Use find_all to handle duplicate elements (e.g., multiple <predicate> tags)
    predicate_tags = soup.find_all(re.compile(r"(?i)predicate|kNumber|knumber"))
    for tag in predicate_tags:
        text = tag.get_text(strip=True)
        knumbers_in_tag = KNUMBER_PATTERN.findall(text)
        for kn in knumbers_in_tag:
            if kn not in [p.get("k_number") for p in result["predicates"]]:
                result["predicates"].append({"k_number": kn, "source": "xfa_xml"})

    # Also scan SE-related raw fields
    se_text = ""
    for path, value in result["raw_fields"].items():
        path_lower = path.lower()
        if "se." in path_lower or "predicate" in path_lower or "comparison" in path_lower:
            se_text += " " + value
    knumbers = KNUMBER_PATTERN.findall(se_text)
    for kn in knumbers:
        if kn not in [p.get("k_number") for p in result["predicates"]]:
            result["predicates"].append({"k_number": kn, "source": "xfa_xml"})

    # Fallback: scan all text for K-numbers
    all_text = " ".join(result["raw_fields"].values())
    all_knumbers = KNUMBER_PATTERN.findall(all_text)
    for kn in all_knumbers:
        if kn not in [p.get("k_number") for p in result["predicates"]]:
            result["predicates"].append({"k_number": kn, "source": "full_text_scan"})

    # Filter out the submission number from predicates (it's not a predicate)
    if submission_number:
        result["predicates"] = [
            p for p in result["predicates"]
            if p["k_number"] != submission_number
        ]

    # Detect sections from narrative content
    for path, value in result["raw_fields"].items():
        if len(value) > 50:  # Only consider substantial text blocks
            for section_name, pattern in SECTION_PATTERNS.items():
                if pattern.search(path) or (len(value) > 200 and pattern.search(value[:200])):
                    if section_name not in result["sections"]:
                        result["sections"][section_name] = value

    return result


def _route_field(result, mapped_key, value):
    """Route a mapped field value to the correct location in result dict."""
    # Applicant fields
    if mapped_key in ("applicant_name", "contact_name", "address",
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
                        "submission_type", "device_trade_name", "device_common_name", "submission_date"):
        result["classification"][mapped_key] = value
    # IFU fields
    elif mapped_key in ("indications_for_use", "prescription_otc", "ifu_device_name"):
        result["indications_for_use"][mapped_key] = value
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

    print(f"\nImport complete:")
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


def generate_xml(project_dir, template_type="nIVD", output_file=None):
    """Generate eSTAR-compatible XML from project data for import into official template.

    Reads review.json, draft_*.md, query.json, and import_data.json to produce XML.
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

    # Read import_data.json (from previous import)
    import_file = project_dir / "import_data.json"
    if import_file.exists():
        with open(import_file) as f:
            project_data["import"] = json.load(f)

    # Read draft files
    drafts = {}
    for draft_file in project_dir.glob("draft_*.md"):
        section_name = draft_file.stem.replace("draft_", "")
        drafts[section_name] = draft_file.read_text(encoding="utf-8", errors="replace")
    project_data["drafts"] = drafts

    # Build XML
    xml = _build_estar_xml(project_data, template_type)

    # Write output
    if output_file:
        out_path = Path(output_file)
    else:
        out_path = project_dir / f"estar_export_{template_type}.xml"

    out_path.write_text(xml, encoding="utf-8")
    print(f"eSTAR XML generated: {out_path}")
    print(f"Template type: {template_type}")
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


def _build_estar_xml(project_data, template_type):
    """Build XFA-compatible XML from project data."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">',
        '  <xfa:data>',
        '    <form1>',
    ]

    # Helper to get value from multiple sources
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
    lines.append(f"        <Date>{datetime.now(tz=__import__('datetime').timezone.utc).strftime('%Y-%m-%d')}</Date>")
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

    # Predicate devices
    predicates = import_data.get("predicates", [])
    if not predicates and review:
        # Pull from review.json accepted predicates
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

    # Human Factors (Section 17 — always generated for round-trip import support)
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
    """Escape special XML characters."""
    if not text:
        return ""
    text = str(text)
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&apos;")
    return text


def list_fields(pdf_path):
    """List all XFA field names found in an eSTAR PDF."""
    xml_string = extract_xfa_from_pdf(pdf_path)
    if xml_string is None:
        return

    soup = BeautifulSoup(xml_string, "lxml-xml")

    fields = []

    def walk(element, path=""):
        if element.name is None:
            return
        current_path = f"{path}.{element.name}" if path else element.name
        text = element.get_text(strip=True)
        if text:
            fields.append((current_path, text[:80]))
        for child in element.children:
            if hasattr(child, "name") and child.name:
                walk(child, current_path)

    walk(soup)

    print(f"XFA Fields in: {pdf_path}")
    print(f"Total fields with data: {len(fields)}")
    print()
    for path, preview in sorted(fields):
        print(f"  {path}")
        if preview:
            print(f"    = {preview}{'...' if len(preview) >= 80 else ''}")


def get_settings():
    """Read plugin settings to find projects_dir."""
    settings_path = os.path.expanduser("~/.claude/fda-predicate-assistant.local.md")
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
        generate_xml(project_dir, args.template, args.output)

    elif args.command == "fields":
        check_dependencies()
        list_fields(args.file)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
