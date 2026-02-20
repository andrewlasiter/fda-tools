#!/usr/bin/env python3
"""
Build Structured Text Cache with Section Detection

Reads PDF text from per-device cache or legacy pdf_data.json and applies
3-tier section detection to structure the content. Writes structured JSON
files to ~/fda-510k-data/extraction/structured_text_cache/

Usage:
    python3 build_structured_cache.py --cache-dir ~/fda-510k-data/extraction/cache
    python3 build_structured_cache.py --legacy ~/fda-510k-data/extraction/pdf_data.json
    python3 build_structured_cache.py --both  # Process both if available
"""

import os
import sys
import json
import re
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import Counter

# Import FDA API client for metadata enrichment
try:
    from fda_api_client import FDAClient
except ImportError:
    # Fallback if not in same directory
    from fda_api_client import FDAClient

# Section detection patterns (Tier 1: Regex)
# Expanded with Priority 3 enhancements (15 new section types)
SECTION_PATTERNS = {
    'predicate_se': re.compile(
        r'(?i)(?:substantial\s+equivalen|predicate\s+(?:device|comparison|analysis|identification)'
        r'|comparison\s+(?:of|to|with)\s+predicate|SE\s+(?:comparison|discussion|summary)'
        r'|technological\s+characteristics|comparison\s+(?:table|chart|matrix)'
        r'|similarities\s+and\s+differences|comparison\s+of\s+(?:the\s+)?(?:features|technological|device))'
    ),
    'indications_for_use': re.compile(
        r'(?i)(?:indications?\s+for\s+use|intended\s+use|ifu\b|indication\s+statement'
        r'|device\s+indications?|clinical\s+indications?|approved\s+use)'
    ),
    'device_description': re.compile(
        r'(?i)(?:device\s+description|product\s+description|description\s+of\s+(?:the\s+)?device'
        r'|device\s+characteristics|physical\s+description|device\s+composition'
        r'|device\s+components|system\s+(?:description|overview)|principle\s+of\s+operation)'
    ),
    'performance_testing': re.compile(
        r'(?i)(?:non[- ]?clinical\s+(?:testing|studies|data|performance)'
        r'|performance\s+(?:testing|data|evaluation|characteristics|bench)'
        r'|bench\s+(?:testing|top\s+testing)|in\s+vitro\s+(?:testing|studies)'
        r'|mechanical\s+(?:testing|characterization)|laboratory\s+testing'
        r'|verification\s+(?:testing|studies)|validation\s+testing'
        r'|analytical\s+performance|test(?:ing)?\s+(?:summary|results|data))'
    ),
    'biocompatibility': re.compile(
        r'(?i)(?:biocompatib(?:ility|le)?|biological?\s+(?:evaluation|testing|safety|assessment)'
        r'|iso\s*10993|cytotoxicity|sensitization\s+test|irritation\s+test'
        r'|systemic\s+toxicity|genotoxicity|implantation\s+(?:testing|studies|study)'
        r'|hemocompatibility|material\s+characterization|extractables?\s+and\s+leachables?)'
    ),
    'sterilization': re.compile(
        r'(?i)(?:steriliz(?:ation|ed|ing)|sterility\s+(?:assurance|testing|validation)'
        r'|ethylene\s+oxide|eto\b|e\.?o\.?\s+(?:steriliz|residual)'
        r'|gamma\s+(?:radiation|irradiation|steriliz)|electron\s+beam|e[- ]?beam'
        r'|steam\s+steriliz|autoclave|iso\s*11135|iso\s*11137|sal\s+10'
        r'|sterility\s+assurance\s+level)'
    ),
    'clinical_testing': re.compile(
        r'(?i)(?:clinical\s+(?:testing|trial|study|studies|data|evidence|information'
        r'|evaluation|investigation|performance)|human\s+(?:subjects?|study|clinical)'
        r'|patient\s+study|pivotal\s+(?:study|trial)|feasibility\s+study'
        r'|post[- ]?market\s+(?:clinical\s+)?follow[- ]?up|pmcf'
        r'|literature\s+(?:review|search|summary|based)|clinical\s+experience)'
    ),
    'shelf_life': re.compile(
        r'(?i)(?:shelf[- ]?life|stability\s+(?:testing|studies|data)|accelerated\s+aging'
        r'|real[- ]?time\s+aging|package\s+(?:integrity|testing|validation|aging)'
        r'|astm\s*f1980|expiration\s+dat(?:e|ing)|storage\s+condition)'
    ),
    'software': re.compile(
        r'(?i)(?:software\s+(?:description|validation|verification|documentation|testing'
        r'|v&v|lifecycle|architecture|design|level\s+of\s+concern)|firmware'
        r'|algorithm\s+(?:description|validation)|cybersecurity|iec\s*62304|sloc'
        r'|soup\s+analysis|off[- ]?the[- ]?shelf\s+software|ots\s+software'
        r'|mobile\s+(?:medical\s+)?app(?:lication)?|SBOM|threat\s+model)'
    ),
    'electrical_safety': re.compile(
        r'(?i)(?:electrical\s+safety|iec\s*60601|electromagnetic\s+(?:compatibility|interference|disturbance)'
        r'|emc\b|emi\b|wireless\s+(?:coexistence|testing)|rf\s+(?:safety|testing|emissions?)'
        r'|radiation\s+safety|battery\s+safety|iec\s*62133|ul\s*1642)'
    ),
    'human_factors': re.compile(
        r'(?i)(?:human\s+factors|usability\s+(?:testing|engineering|study|evaluation)'
        r'|use[- ]?related\s+risk|iec\s*62366|formative\s+(?:evaluation|study)'
        r'|summative\s+(?:evaluation|study|test)|simulated\s+use|use\s+error)'
    ),
    'risk_management': re.compile(
        r'(?i)(?:risk\s+(?:management|analysis|assessment|evaluation)|iso\s*14971'
        r'|fmea|failure\s+mode|hazard\s+analysis|fault\s+tree|risk[- ]?benefit)'
    ),
    'labeling': re.compile(
        r'(?i)(?:label(?:ing)?\s+(?:requirements?|review)|instructions?\s+for\s+use'
        r'|package\s+(?:insert|label)|iso\s*15223|udi|unique\s+device\s+identif|user\s+manual)'
    ),
    # Priority 3: 15 new section patterns
    'regulatory_history': re.compile(
        r'(?i)(?:regulatory\s+(?:history|status|classification|pathway)|510\s*\(\s*k\s*\)\s+(?:submission|clearance|number)'
        r'|special\s+510\s*\(\s*k\s*\)|abbreviated\s+510\s*\(\s*k\s*\)|third[- ]?party\s+review'
        r'|de\s+novo\s+(?:classification|pathway)|pre[- ]?market\s+(?:notification|approval)|pma\s+(?:submission|approval)'
        r'|classification\s+name|product\s+code|regulation\s+number|advisory\s+committee|review\s+panel)'
    ),
    'reprocessing': re.compile(
        r'(?i)(?:reprocessing\s+(?:instructions?|validation|procedures?)|cleaning\s+(?:validation|instructions?|procedures?)'
        r'|disinfection\s+(?:validation|protocol)|validated\s+cleaning\s+cycle|reusable\s+device|multi[- ]?use\s+device'
        r'|cleaning\s+efficacy|residual\s+(?:contamination|soil)|worst[- ]?case\s+soil|protein\s+residue)'
    ),
    'packaging': re.compile(
        r'(?i)(?:packaging\s+(?:design|validation|materials|testing)|primary\s+packaging|secondary\s+packaging'
        r'|package\s+(?:seal\s+)?integrity|astm\s*(?:f88|f1929|f2096)|peel\s+(?:strength|testing|test)'
        r'|sterile\s+barrier\s+system|tyvek|foil\s+pouch)'
    ),
    'materials': re.compile(
        r'(?i)(?:materials?\s+(?:of\s+construction|characterization|composition|specification)|raw\s+materials?'
        r'|chemical\s+composition|material\s+(?:properties|testing)|polymer\s+characterization|metal\s+alloys?'
        r'|surface\s+(?:finish|treatment|coating)|peek|titanium|cobalt[- ]?chrome|stainless\s+steel|nitinol)'
    ),
    'environmental_testing': re.compile(
        r'(?i)(?:environmental\s+(?:testing|conditioning|simulation)|temperature\s+(?:cycling|shock|range)'
        r'|humidity\s+(?:testing|conditioning)|altitude\s+(?:testing|simulation)|vibration\s+(?:testing|test)'
        r'|shock\s+(?:testing|test)|drop\s+(?:testing|test)|transit\s+simulation|ista\s+(?:testing|standard))'
    ),
    'mechanical_testing': re.compile(
        r'(?i)(?:mechanical\s+(?:testing|properties|characterization|performance)|tensile\s+(?:strength|testing|test)'
        r'|compression\s+(?:strength|testing|test)|flexural\s+(?:strength|testing|modulus)|torsion(?:al)?\s+(?:strength|testing|test)'
        r'|fatigue\s+(?:testing|life|cycles)|wear\s+(?:testing|resistance)|burst\s+(?:pressure|test)|leak\s+(?:testing|test))'
    ),
    'functional_testing': re.compile(
        r'(?i)(?:functional\s+(?:testing|validation|performance|verification)|operational\s+(?:testing|qualification)'
        r'|performance\s+verification|device\s+function(?:ality)?|operation(?:al)?\s+testing|acceptance\s+testing)'
    ),
    'accelerated_aging': re.compile(
        r'(?i)(?:accelerated\s+ag(?:e|ing)|real[- ]?time\s+ag(?:e|ing)|aging\s+(?:protocol|study|validation)'
        r'|astm\s*f1980|aging\s+factor|q10\s+(?:factor|value)|aged\s+(?:samples?|units?)|end[- ]?of[- ]?life\s+testing)'
    ),
    'antimicrobial': re.compile(
        r'(?i)(?:antimicrobial\s+(?:efficacy|testing|effectiveness|activity)|zone\s+of\s+inhibition'
        r'|mic|mbc|minimum\s+inhibitory\s+concentration|minimum\s+bactericidal\s+concentration'
        r'|aatcc\s+100|iso\s*20743|log\s+reduction|drug\s+(?:release|elution|content))'
    ),
    'emc_detailed': re.compile(
        r'(?i)(?:iec\s*60601[- ]?1[- ]?2|wireless\s+coexistence|rf\s+(?:emissions?|immunity|testing)'
        r'|radiated\s+(?:emissions?|immunity)|conducted\s+(?:emissions?|immunity)|harmonic\s+(?:emissions?|current)'
        r'|electrostatic\s+discharge|esd\s+(?:testing|test)|surge\s+(?:immunity|test))'
    ),
    'mri_safety': re.compile(
        r'(?i)(?:mri\s+(?:safety|compatibility|conditional|conditional\s+safe)|magnetic\s+resonance\s+(?:imaging|environment)'
        r'|astm\s*f2503|astm\s*f2119|magnetically\s+induced\s+(?:displacement|torque|force)|rf[- ]?induced\s+heating'
        r'|image\s+artifact|static\s+(?:magnetic\s+)?field|whole[- ]?body\s+sar|specific\s+absorption\s+rate)'
    ),
    'animal_testing': re.compile(
        r'(?i)(?:animal\s+(?:testing|study|studies|model|trial)|pre[- ]?clinical\s+(?:testing|study|studies|trial)'
        r'|in\s+vivo\s+(?:testing|study|studies|evaluation)|ovine\s+(?:model|study)|porcine\s+(?:model|study)'
        r'|canine\s+(?:model|study)|iacuc|survival\s+study|histopathology|necropsy)'
    ),
    'literature_review': re.compile(
        r'(?i)(?:literature\s+(?:review|search|summary|analysis|evaluation|evidence)|published\s+(?:data|studies|literature)'
        r'|peer[- ]?reviewed\s+(?:publications?|articles?|studies)|scientific\s+literature|pubmed\s+search'
        r'|systematic\s+review|meta[- ]?analysis|post[- ]?market\s+(?:data|literature|surveillance))'
    ),
    'manufacturing': re.compile(
        r'(?i)(?:manufacturing\s+(?:process|site|description|location)|quality\s+(?:system|management\s+system)'
        r'|iso\s*13485|device\s+master\s+record|dmr|design\s+history\s+file|dhf|process\s+validation)'
    ),
    'special_510k': re.compile(
        r'(?i)(?:special\s+510\s*\(\s*k\s*\)|design\s+controls?|declaration\s+of\s+conformity|doc\b'
        r'|compliance\s+with\s+(?:recognized\s+)?standards?|consensus\s+standards?|design\s+changes?)'
    ),
}

# Tier 2: OCR Correction Table (from section-patterns.md)
OCR_SUBSTITUTIONS = {
    '1': 'I',  # "1ndications" → "Indications"
    '0': 'O',  # "Bi0compatibility" → "Biocompatibility"
    '5': 'S',  # "5terilization" → "Sterilization"
    '$': 'S',  # "$terilization" → "Sterilization"
    '7': 'T',  # "7esting" → "Testing"
    '3': 'E',  # "P3rformance" → "Performance"
    '8': 'B',  # "8iocompatibility" → "Biocompatibility"
    '|': 'I',  # "|ndications" → "Indications"
}


def apply_ocr_corrections(text: str, max_corrections: int = 2) -> Tuple[str, List[str]]:
    """
    Apply OCR correction table from Tier 2 pattern matching.

    Args:
        text: Text to correct
        max_corrections: Maximum number of substitutions to apply (default: 2)

    Returns:
        (corrected_text, corrections_applied)
    """
    corrections = []
    corrected = text

    # Apply character substitutions
    for ocr_char, correct_char in OCR_SUBSTITUTIONS.items():
        if ocr_char in corrected:
            old = corrected
            corrected = corrected.replace(ocr_char, correct_char)
            if corrected != old:
                corrections.append(f"{ocr_char}→{correct_char}")
                if len(corrections) >= max_corrections:
                    break

    # Handle spurious spaces (e.g., "Ste rilization" → "Sterilization")
    # Match words split by single space where removing space forms dictionary word
    space_pattern = re.compile(r'\b(\w{2,3}) (\w{2,})\b')
    matches = space_pattern.findall(corrected)
    for part1, part2 in matches:
        combined = part1 + part2
        # Check if combined version matches any section pattern
        for section_name, pattern in SECTION_PATTERNS.items():
            if pattern.search(combined):
                old = corrected
                corrected = corrected.replace(f"{part1} {part2}", combined)
                if corrected != old:
                    corrections.append(f"space removal: '{part1} {part2}'→'{combined}'")
                    break

    return corrected, corrections


def estimate_ocr_quality(text: str) -> Tuple[str, float]:
    """
    Estimate OCR quality based on common OCR error patterns.

    Returns:
        (quality_level, confidence_score)
        - quality_level: "HIGH", "MEDIUM", "LOW"
        - confidence_score: 0.0-1.0 (higher = better quality)
    """
    if not text or len(text) < 100:
        return "LOW", 0.0

    # Count OCR error indicators
    error_count = 0
    total_chars = len(text)

    # Check for common OCR errors
    for ocr_char in OCR_SUBSTITUTIONS.keys():
        # Count occurrences in non-numeric contexts (likely errors)
        pattern = re.compile(rf'[a-zA-Z]{ocr_char}|{ocr_char}[a-zA-Z]')
        error_count += len(pattern.findall(text))

    # Check for excessive pipes (| often misread as I or l)
    error_count += text.count('|') * 0.5

    # Check for spurious spaces in common words
    space_errors = len(re.findall(r'\b[A-Z][a-z]{1,2} [a-z]{2,}\b', text))
    error_count += space_errors

    # Calculate error rate
    error_rate = error_count / (total_chars / 100)  # errors per 100 chars

    # Determine quality level
    if error_rate < 0.5:
        quality = "HIGH"
        confidence = 1.0 - (error_rate / 2)
    elif error_rate < 2.0:
        quality = "MEDIUM"
        confidence = 0.7 - (error_rate / 10)
    else:
        quality = "LOW"
        confidence = max(0.0, 0.5 - (error_rate / 20))

    return quality, round(confidence, 3)


def detect_sections(text: str, apply_ocr_correction: bool = True) -> Tuple[Dict[str, Dict], Dict]:
    """
    Detect section boundaries using Tier 1 regex patterns with optional OCR correction (Tier 2).

    Args:
        text: Full text to search
        apply_ocr_correction: Apply Tier 2 OCR corrections if Tier 1 fails (default: True)

    Returns:
        (sections_dict, metadata_dict)
        - sections: {section_name: {text, start_pos, end_pos, header_matched, tier}}
        - metadata: {ocr_quality, ocr_confidence, tier1_count, tier2_count, corrections_applied}
    """
    sections = {}
    tier2_corrections = []

    # Estimate OCR quality
    ocr_quality, ocr_confidence = estimate_ocr_quality(text)

    # Tier 1: Direct regex matching (no corrections)
    matches_tier1 = []
    for section_name, pattern in SECTION_PATTERNS.items():
        for match in pattern.finditer(text):
            matches_tier1.append((match.start(), match.group(), section_name, 'tier1'))

    # Tier 2: OCR-corrected matching (if enabled and OCR quality is not HIGH)
    matches_tier2 = []
    if apply_ocr_correction and ocr_quality != "HIGH":
        # Apply OCR corrections to short header-like lines
        lines = text.split('\n')
        current_pos = 0

        for line in lines:
            if len(line.strip()) > 0 and len(line.strip()) < 80:  # Header-like lines
                corrected_line, corrections = apply_ocr_corrections(line.strip())

                if corrections:  # Only check if corrections were made
                    # Check if corrected line matches any pattern
                    for section_name, pattern in SECTION_PATTERNS.items():
                        if pattern.search(corrected_line):
                            # Find position of this line in original text
                            line_pos = text.find(line, current_pos)
                            if line_pos >= 0:
                                matches_tier2.append((
                                    line_pos,
                                    line.strip(),
                                    section_name,
                                    'tier2',
                                    corrections
                                ))
                                tier2_corrections.append({
                                    'section': section_name,
                                    'original': line.strip(),
                                    'corrected': corrected_line,
                                    'corrections': corrections
                                })

            current_pos += len(line) + 1  # +1 for newline

    # Combine Tier 1 and Tier 2 matches (Tier 1 takes precedence)
    all_matches = matches_tier1 + matches_tier2

    # Sort by position
    all_matches.sort(key=lambda x: x[0])

    # Deduplicate: if same section_name appears twice, keep Tier 1 match
    seen_sections = set()
    deduplicated_matches = []
    for match in all_matches:
        section_name = match[2]
        tier = match[3]
        if section_name not in seen_sections or tier == 'tier1':
            deduplicated_matches.append(match)
            seen_sections.add(section_name)

    # Re-sort deduplicated matches
    deduplicated_matches.sort(key=lambda x: x[0])

    # Extract section content (from header to next header or end)
    for i, match_tuple in enumerate(deduplicated_matches):
        start_pos = match_tuple[0]
        header_text = match_tuple[1]
        section_name = match_tuple[2]
        tier = match_tuple[3]

        # End position is the start of the next section or end of text
        end_pos = deduplicated_matches[i + 1][0] if i + 1 < len(deduplicated_matches) else len(text)

        # Extract section text (including header)
        section_text = text[start_pos:end_pos].strip()

        # Store section (keep longest if section appears multiple times)
        if section_name not in sections or len(section_text) > len(sections[section_name]['text']):
            section_data = {
                'text': section_text,
                'start_pos': start_pos,
                'end_pos': end_pos,
                'header_matched': header_text,
                'tier': tier
            }

            # Add OCR correction info for Tier 2 matches
            if tier == 'tier2' and len(match_tuple) > 4:
                section_data['ocr_corrections'] = match_tuple[4]

            sections[section_name] = section_data

    # Build metadata
    tier1_count = len([m for m in deduplicated_matches if m[3] == 'tier1'])
    tier2_count = len([m for m in deduplicated_matches if m[3] == 'tier2'])

    metadata = {
        'ocr_quality': ocr_quality,
        'ocr_confidence': ocr_confidence,
        'tier1_sections': tier1_count,
        'tier2_sections': tier2_count,
        'total_sections': len(sections),
        'tier2_corrections': tier2_corrections if tier2_corrections else None
    }

    return sections, metadata


def enrich_metadata_from_openfda(k_number: str, client: FDAClient) -> Dict:
    """
    Enrich metadata by querying openFDA API for K-number.

    Args:
        k_number: The K-number to look up (e.g., 'K231152')
        client: FDAClient instance for API queries

    Returns:
        Dictionary with product_code, device_class, regulation_number, review_panel
        Returns empty dict if K-number not found or API error
    """
    try:
        result = client.get_510k(k_number)

        # Check for API errors or degraded mode
        if result.get('error') or result.get('degraded'):
            return {}

        # Check if results exist
        results = result.get('results', [])
        if not results:
            return {}

        # Extract metadata from first result
        device = results[0]
        metadata = {}

        # Product code (REQUIRED for filtering)
        if device.get('product_code'):
            metadata['product_code'] = device['product_code']

        # Review advisory committee (available in 510k response)
        if device.get('review_advisory_committee'):
            metadata['review_panel'] = device['review_advisory_committee']

        # Device class and regulation number would require a second API call
        # to the classification endpoint - not included to avoid doubling API calls
        # Users can enhance metadata manually if needed for specific use cases

        return metadata

    except Exception:
        # Silently fail - metadata enrichment is optional
        return {}


def build_structured_cache(source_path: Path, output_dir: Path, source_type: str = 'per-device'):
    """
    Build structured cache from source PDF text data.

    Args:
        source_path: Path to source data (index.json or pdf_data.json)
        output_dir: Path to structured cache output directory
        source_type: 'per-device' or 'legacy'
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize FDA API client for metadata enrichment (legacy cache only)
    fda_client = None
    if source_type == 'legacy':
        try:
            fda_client = FDAClient()
            print("✓ FDA API client initialized for metadata enrichment")
        except Exception as e:
            print(f"⚠ Could not initialize FDA API client: {e}")
            print("  Continuing without metadata enrichment...")

    # Load source data
    if source_type == 'per-device':
        with open(source_path) as f:
            index = json.load(f)

        print(f"Processing {len(index)} devices from per-device cache...")

        for k_number, meta in index.items():
            device_path = source_path.parent.parent / meta['file_path']
            if not device_path.exists():
                print(f"  ⚠ Missing: {k_number} (expected at {device_path})")
                continue

            with open(device_path) as f:
                device_data = json.load(f)

            text = device_data.get('text', '')
            if not text:
                print(f"  ⚠ Empty: {k_number}")
                continue

            # Detect sections with OCR correction and quality assessment
            sections, detection_metadata = detect_sections(text)

            # Build structured output
            structured = {
                'k_number': k_number,
                'source': 'per-device-cache',
                'source_path': str(device_path),
                'extracted_at': device_data.get('extracted_at', meta.get('extracted_at', 'unknown')),
                'structured_at': datetime.now().isoformat(),
                'full_text': text,
                'full_text_length': len(text),
                'sections': sections,
                'section_count': len(sections),
                'ocr_quality': detection_metadata['ocr_quality'],
                'ocr_confidence': detection_metadata['ocr_confidence'],
                'tier1_sections': detection_metadata['tier1_sections'],
                'tier2_sections': detection_metadata['tier2_sections'],
                'tier2_corrections': detection_metadata.get('tier2_corrections'),
                'metadata': device_data.get('metadata', {})
            }

            # Write structured file
            output_file = output_dir / f"{k_number}.json"
            with open(output_file, 'w') as f:
                json.dump(structured, f, indent=2)

            print(f"  ✓ {k_number}: {len(text)} chars, {len(sections)} sections")

    elif source_type == 'legacy':
        with open(source_path) as f:
            pdf_data = json.load(f)

        print(f"Processing {len(pdf_data)} PDFs from legacy cache...")

        for filename, content in pdf_data.items():
            # Extract K-number from filename
            k_number = filename.replace('.pdf', '').upper()

            # Handle different content formats
            if isinstance(content, dict):
                text = content.get('text', '')
            else:
                text = str(content)

            if not text:
                print(f"  ⚠ Empty: {k_number}")
                continue

            # Detect sections with OCR correction and quality assessment
            sections, detection_metadata = detect_sections(text)

            # Enrich metadata from openFDA API
            metadata = {}
            if fda_client:
                metadata = enrich_metadata_from_openfda(k_number, fda_client)
                # Rate limiting: 500ms delay between API calls (2 req/sec)
                if metadata:
                    time.sleep(0.5)

            # Build structured output
            structured = {
                'k_number': k_number,
                'source': 'legacy-pdf_data.json',
                'source_path': str(source_path),
                'extracted_at': 'unknown',
                'structured_at': datetime.now().isoformat(),
                'full_text': text,
                'full_text_length': len(text),
                'sections': sections,
                'section_count': len(sections),
                'ocr_quality': detection_metadata['ocr_quality'],
                'ocr_confidence': detection_metadata['ocr_confidence'],
                'tier1_sections': detection_metadata['tier1_sections'],
                'tier2_sections': detection_metadata['tier2_sections'],
                'tier2_corrections': detection_metadata.get('tier2_corrections'),
                'metadata': metadata
            }

            # Write structured file
            output_file = output_dir / f"{k_number}.json"
            with open(output_file, 'w') as f:
                json.dump(structured, f, indent=2)

            # Enhanced output showing metadata enrichment
            metadata_info = ""
            if metadata.get('product_code'):
                metadata_info = f" [{metadata['product_code']}]"
            print(f"  ✓ {k_number}: {len(text)} chars, {len(sections)} sections{metadata_info}")

    else:
        raise ValueError(f"Unknown source_type: {source_type}")


def generate_coverage_manifest(structured_dir: Path):
    """Generate coverage manifest summarizing the structured cache with OCR quality metrics."""

    structured_files = list(structured_dir.glob('*.json'))
    if 'manifest.json' in [f.name for f in structured_files]:
        structured_files = [f for f in structured_files if f.name != 'manifest.json']

    print(f"\nGenerating coverage manifest for {len(structured_files)} files...")

    # Statistics
    total_devices = len(structured_files)
    total_chars = 0
    section_counts = Counter()
    extraction_quality = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    ocr_quality_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    tier_usage = {'tier1_only': 0, 'tier1_and_tier2': 0, 'tier2_only': 0}
    total_tier1 = 0
    total_tier2 = 0
    ocr_confidence_sum = 0.0

    for file_path in structured_files:
        with open(file_path) as f:
            data = json.load(f)

        total_chars += data['full_text_length']
        section_counts[data['section_count']] += 1

        # Section count-based quality assessment (legacy)
        if data['section_count'] >= 7:
            extraction_quality['HIGH'] += 1
        elif data['section_count'] >= 4:
            extraction_quality['MEDIUM'] += 1
        else:
            extraction_quality['LOW'] += 1

        # OCR quality tracking (Priority 3)
        ocr_quality = data.get('ocr_quality', 'UNKNOWN')
        if ocr_quality in ocr_quality_counts:
            ocr_quality_counts[ocr_quality] += 1

        ocr_confidence_sum += data.get('ocr_confidence', 0.0)

        # Tier usage tracking
        tier1 = data.get('tier1_sections', 0)
        tier2 = data.get('tier2_sections', 0)
        total_tier1 += tier1
        total_tier2 += tier2

        if tier1 > 0 and tier2 == 0:
            tier_usage['tier1_only'] += 1
        elif tier1 > 0 and tier2 > 0:
            tier_usage['tier1_and_tier2'] += 1
        elif tier1 == 0 and tier2 > 0:
            tier_usage['tier2_only'] += 1

    avg_ocr_confidence = ocr_confidence_sum / total_devices if total_devices > 0 else 0.0

    manifest = {
        'generated_at': datetime.now().isoformat(),
        'total_devices': total_devices,
        'total_text_chars': total_chars,
        'avg_text_length': total_chars // total_devices if total_devices > 0 else 0,
        'section_distribution': dict(section_counts),
        'extraction_quality': extraction_quality,
        'quality_summary': {
            'high_confidence_pct': round(100 * extraction_quality['HIGH'] / total_devices, 1) if total_devices > 0 else 0,
            'medium_confidence_pct': round(100 * extraction_quality['MEDIUM'] / total_devices, 1) if total_devices > 0 else 0,
            'low_confidence_pct': round(100 * extraction_quality['LOW'] / total_devices, 1) if total_devices > 0 else 0,
        },
        # Priority 3: OCR quality metrics
        'ocr_quality': {
            'distribution': ocr_quality_counts,
            'avg_confidence': round(avg_ocr_confidence, 3),
            'high_quality_pct': round(100 * ocr_quality_counts['HIGH'] / total_devices, 1) if total_devices > 0 else 0,
            'medium_quality_pct': round(100 * ocr_quality_counts['MEDIUM'] / total_devices, 1) if total_devices > 0 else 0,
            'low_quality_pct': round(100 * ocr_quality_counts['LOW'] / total_devices, 1) if total_devices > 0 else 0,
        },
        # Priority 3: Tier usage statistics
        'tier_usage': {
            'tier1_sections_total': total_tier1,
            'tier2_sections_total': total_tier2,
            'tier2_correction_rate': round(100 * total_tier2 / (total_tier1 + total_tier2), 1) if (total_tier1 + total_tier2) > 0 else 0,
            'devices_tier1_only': tier_usage['tier1_only'],
            'devices_tier1_and_tier2': tier_usage['tier1_and_tier2'],
            'devices_tier2_only': tier_usage['tier2_only'],
        }
    }

    manifest_path = structured_dir / 'manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"✓ Manifest written to {manifest_path}")
    print(f"\nCoverage Summary:")
    print(f"  Total devices: {total_devices}")
    print(f"  Avg text length: {manifest['avg_text_length']:,} chars")
    print(f"\n  Extraction Quality (section count-based):")
    print(f"    HIGH (7+ sections): {extraction_quality['HIGH']} ({manifest['quality_summary']['high_confidence_pct']}%)")
    print(f"    MEDIUM (4-6 sections): {extraction_quality['MEDIUM']} ({manifest['quality_summary']['medium_confidence_pct']}%)")
    print(f"    LOW (0-3 sections): {extraction_quality['LOW']} ({manifest['quality_summary']['low_confidence_pct']}%)")
    print(f"\n  OCR Quality Assessment:")
    print(f"    HIGH (clean text): {ocr_quality_counts['HIGH']} ({manifest['ocr_quality']['high_quality_pct']}%)")
    print(f"    MEDIUM (minor errors): {ocr_quality_counts['MEDIUM']} ({manifest['ocr_quality']['medium_quality_pct']}%)")
    print(f"    LOW (significant OCR issues): {ocr_quality_counts['LOW']} ({manifest['ocr_quality']['low_quality_pct']}%)")
    print(f"    Avg OCR confidence: {avg_ocr_confidence:.3f}")
    print(f"\n  Tier 2 OCR Correction Usage:")
    print(f"    Total sections detected: {total_tier1 + total_tier2}")
    print(f"    Tier 1 (direct match): {total_tier1}")
    print(f"    Tier 2 (OCR corrected): {total_tier2} ({manifest['tier_usage']['tier2_correction_rate']}%)")
    print(f"    Devices needing Tier 2: {tier_usage['tier1_and_tier2'] + tier_usage['tier2_only']} ({round(100*(tier_usage['tier1_and_tier2'] + tier_usage['tier2_only'])/total_devices,1) if total_devices > 0 else 0}%)")


def main():
    parser = argparse.ArgumentParser(
        description='Build structured text cache with section detection'
    )
    parser.add_argument('--cache-dir', type=Path,
                        help='Per-device cache directory containing index.json')
    parser.add_argument('--legacy', type=Path,
                        help='Legacy monolithic pdf_data.json file')
    parser.add_argument('--both', action='store_true',
                        help='Process both caches if available')
    parser.add_argument('--output', type=Path,
                        default=Path.home() / 'fda-510k-data' / 'extraction' / 'structured_text_cache',
                        help='Output directory for structured cache (default: ~/fda-510k-data/extraction/structured_text_cache)')

    args = parser.parse_args()

    if not (args.cache_dir or args.legacy or args.both):
        parser.error('Must specify --cache-dir, --legacy, or --both')

    print("="*60)
    print("Structured Text Cache Builder")
    print("="*60)
    print()

    # Process per-device cache
    if args.both or args.cache_dir:
        cache_dir = args.cache_dir or (Path.home() / 'fda-510k-data' / 'extraction' / 'cache')
        index_file = cache_dir / 'index.json'

        if index_file.exists():
            print(f"Processing per-device cache: {cache_dir}")
            build_structured_cache(index_file, args.output, source_type='per-device')
        else:
            print(f"⚠ Per-device cache not found at {index_file}")

    # Process legacy cache
    if args.both or args.legacy:
        legacy_file = args.legacy or (Path.home() / 'fda-510k-data' / 'extraction' / 'pdf_data.json')

        if legacy_file.exists():
            print(f"Processing legacy cache: {legacy_file}")
            build_structured_cache(legacy_file, args.output, source_type='legacy')
        else:
            print(f"⚠ Legacy cache not found at {legacy_file}")

    # Generate manifest
    generate_coverage_manifest(args.output)

    print()
    print("="*60)
    print("✓ Structured cache build complete")
    print(f"  Output: {args.output}")
    print("="*60)


if __name__ == '__main__':
    main()
