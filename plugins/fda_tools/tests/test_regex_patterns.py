"""Tests for section detection regex patterns from section-patterns.md.

Validates all section heading patterns against known 510(k) text samples.
"""

import re
import pytest


# Section heading patterns from section-patterns.md
SECTION_PATTERNS = {
    "predicate_se": re.compile(
        r"(?i)(?:substantial\s+equivalen|predicate\s+device|comparison\s+(?:of|to|with)\s+predicate|SE\s+(?:comparison|discussion|summary))"
    ),
    "indications": re.compile(
        r"(?i)(?:indications?\s+for\s+use|intended\s+use|IFU\b)"
    ),
    "device_description": re.compile(
        r"(?i)(?:device\s+description|description\s+of\s+(?:the\s+)?device|principle\s+of\s+operation)"
    ),
    "performance": re.compile(
        r"(?i)(?:performance\s+(?:testing|data|characteristics)|test(?:ing)?\s+(?:summary|results|data))"
    ),
    "biocompatibility": re.compile(
        r"(?i)(?:biocompatib|biological?\s+(?:evaluation|testing|safety))"
    ),
    "sterilization": re.compile(
        r"(?i)(?:sterilizat|sterility\s+(?:assurance|testing|validation))"
    ),
    "software": re.compile(
        r"(?i)(?:software\s+(?:description|documentation|level|validation)|cybersecurity|SBOM|threat\s+model)"
    ),
    "labeling": re.compile(
        r"(?i)(?:label(?:ing)?\s+(?:requirements?|review)|instructions?\s+for\s+use|package\s+(?:insert|label))"
    ),
    "clinical": re.compile(
        r"(?i)(?:clinical\s+(?:data|evidence|stud(?:y|ies)|information)|literature\s+review)"
    ),
    "shelf_life": re.compile(
        r"(?i)(?:shelf\s+life|accelerated\s+aging|real[\-\s]time\s+aging|package\s+(?:integrity|validation))"
    ),
    "emc_electrical": re.compile(
        r"(?i)(?:electromagnetic\s+compatib|EMC\b|electrical\s+safety|IEC\s+60601)"
    ),
}


class TestPredicateSEPattern:
    """Test Substantial Equivalence section detection."""

    @pytest.mark.parametrize("text", [
        "SUBSTANTIAL EQUIVALENCE COMPARISON",
        "Substantial Equivalence Discussion",
        "substantial equivalence",
        "Predicate Device Selection",
        "Comparison of Predicate Devices",
        "Comparison to Predicate",
        "Comparison with Predicate Device",
        "SE Comparison Table",
        "SE Discussion",
        "SE Summary",
    ])
    def test_matches(self, text):
        assert SECTION_PATTERNS["predicate_se"].search(text)

    @pytest.mark.parametrize("text", [
        "Device Description",
        "Performance Testing",
        "The device is equivalent in size",
    ])
    def test_no_match(self, text):
        assert not SECTION_PATTERNS["predicate_se"].search(text)


class TestIndicationsPattern:
    """Test Indications for Use section detection."""

    @pytest.mark.parametrize("text", [
        "INDICATIONS FOR USE",
        "Indications for Use",
        "Indication for Use",
        "Intended Use",
        "intended use of the device",
        "IFU Statement",
    ])
    def test_matches(self, text):
        assert SECTION_PATTERNS["indications"].search(text)

    @pytest.mark.parametrize("text", [
        "Device Description",
        "For use with the applicator",
    ])
    def test_no_match(self, text):
        assert not SECTION_PATTERNS["indications"].search(text)


class TestDeviceDescriptionPattern:
    """Test Device Description section detection."""

    @pytest.mark.parametrize("text", [
        "DEVICE DESCRIPTION",
        "Device Description",
        "Description of the Device",
        "Description of Device",
        "Principle of Operation",
    ])
    def test_matches(self, text):
        assert SECTION_PATTERNS["device_description"].search(text)


class TestPerformancePattern:
    """Test Performance Testing section detection."""

    @pytest.mark.parametrize("text", [
        "PERFORMANCE TESTING",
        "Performance Data",
        "Performance Characteristics",
        "Testing Summary",
        "Testing Results",
        "Test Summary",
        "Test Data",
        "test results for the device",
    ])
    def test_matches(self, text):
        assert SECTION_PATTERNS["performance"].search(text)


class TestBiocompatibilityPattern:
    """Test Biocompatibility section detection."""

    @pytest.mark.parametrize("text", [
        "BIOCOMPATIBILITY",
        "Biocompatibility Testing",
        "Biological Evaluation",
        "Biological Testing",
        "Biological Safety",
        "biological evaluation of medical devices",
    ])
    def test_matches(self, text):
        assert SECTION_PATTERNS["biocompatibility"].search(text)


class TestSterilizationPattern:
    """Test Sterilization section detection."""

    @pytest.mark.parametrize("text", [
        "STERILIZATION",
        "Sterilization Validation",
        "Sterility Assurance Level",
        "Sterility Testing",
        "Sterility Validation",
    ])
    def test_matches(self, text):
        assert SECTION_PATTERNS["sterilization"].search(text)


class TestSoftwarePattern:
    """Test Software/Cybersecurity section detection."""

    @pytest.mark.parametrize("text", [
        "SOFTWARE DESCRIPTION",
        "Software Documentation",
        "Software Level of Concern",
        "Software Validation",
        "Cybersecurity Documentation",
        "SBOM",
        "Threat Model",
    ])
    def test_matches(self, text):
        assert SECTION_PATTERNS["software"].search(text)


class TestLabelingPattern:
    """Test Labeling section detection."""

    @pytest.mark.parametrize("text", [
        "Labeling Review",
        "Labeling Requirements",
        "Labeling Requirement",
        "Instructions for Use",
        "Instruction for Use",
        "Package Insert",
        "Package Label",
    ])
    def test_matches(self, text):
        assert SECTION_PATTERNS["labeling"].search(text)

    def test_standalone_labeling_no_match(self):
        """'LABELING' alone doesn't match — pattern requires labeling + qualifier."""
        assert not SECTION_PATTERNS["labeling"].search("LABELING")


class TestClinicalPattern:
    """Test Clinical section detection."""

    @pytest.mark.parametrize("text", [
        "CLINICAL DATA",
        "Clinical Evidence",
        "Clinical Studies",
        "Clinical Study",
        "Clinical Information",
        "Literature Review",
    ])
    def test_matches(self, text):
        assert SECTION_PATTERNS["clinical"].search(text)


class TestShelfLifePattern:
    """Test Shelf Life section detection."""

    @pytest.mark.parametrize("text", [
        "SHELF LIFE",
        "Shelf Life Testing",
        "Accelerated Aging",
        "Real-Time Aging",
        "Real Time Aging",
        "Package Integrity",
        "Package Validation",
    ])
    def test_matches(self, text):
        assert SECTION_PATTERNS["shelf_life"].search(text)


class TestEMCElectricalPattern:
    """Test EMC/Electrical Safety section detection."""

    @pytest.mark.parametrize("text", [
        "ELECTROMAGNETIC COMPATIBILITY",
        "Electromagnetic Compatibility Testing",
        "EMC Testing",
        "Electrical Safety Testing",
        "IEC 60601 Compliance",
    ])
    def test_matches(self, text):
        assert SECTION_PATTERNS["emc_electrical"].search(text)


class TestPatternIndependence:
    """Verify patterns don't cross-match inappropriately."""

    def test_device_description_not_performance(self):
        assert not SECTION_PATTERNS["performance"].search("Device Description")

    def test_se_not_clinical(self):
        assert not SECTION_PATTERNS["clinical"].search("Substantial Equivalence")

    def test_sterilization_not_shelf_life(self):
        assert not SECTION_PATTERNS["shelf_life"].search("Sterilization Validation")

    def test_labeling_not_software(self):
        assert not SECTION_PATTERNS["software"].search("Labeling Requirements")


# ---------------------------------------------------------------------------
# Tier 2: OCR-Tolerant Matching Helpers & Tests
# ---------------------------------------------------------------------------

# OCR substitution table from references/section-patterns.md
# Each entry: (ocr_char, list_of_possible_replacements)
OCR_SUBSTITUTIONS = {
    "1": ["I", "l"],
    "0": ["O"],
    "5": ["S"],
    "$": ["S"],
    "7": ["T"],
    "3": ["E"],
    "8": ["B"],
    "|": ["I", "l"],
}

# Digraph substitutions (applied separately)
OCR_DIGRAPH_SUBSTITUTIONS = {
    "rn": "m",
}

# Known section words for spurious-space rejoining
_SECTION_WORDS = {
    "sterilization", "biocompatibility", "performance", "indications",
    "equivalence", "description", "clinical", "software", "electrical",
    "labeling", "shelf", "substantial",
}


def _try_substitution_variants(text, positions, ocr_chars, max_corrections=2):
    """Recursively try all substitution variants for ambiguous OCR characters.

    Returns a list of candidate corrected strings (up to max_corrections subs).
    """
    if not positions:
        return [text]

    pos = positions[0]
    remaining = positions[1:]
    ch = ocr_chars[pos]
    replacements = OCR_SUBSTITUTIONS[ch]
    candidates = []

    for repl in replacements:
        variant = text[:pos] + repl + text[pos + 1:]
        candidates.extend(_try_substitution_variants(variant, remaining, ocr_chars, max_corrections))

    return candidates


def apply_ocr_corrections(text, max_corrections=2):
    """Apply OCR substitution table to a heading candidate.

    Returns the best corrected text after at most `max_corrections` character-level
    substitutions, plus spurious space removal. For ambiguous substitutions
    (e.g., 1→I or 1→l), tries all variants and returns the one that produces
    the longest match against any Tier 1 regex. Mirrors the Tier 2 instructions
    in references/section-patterns.md.
    """
    corrected = text

    # Pass 1: Digraph substitutions (e.g., rn→m) — these don't consume a
    # "correction slot" since they fix a single visual error
    for digraph, replacement in OCR_DIGRAPH_SUBSTITUTIONS.items():
        corrected = corrected.replace(digraph, replacement)

    # Pass 2: Find positions needing substitution (up to max_corrections)
    chars = list(corrected)
    sub_positions = []
    for i, ch in enumerate(chars):
        if ch in OCR_SUBSTITUTIONS and len(sub_positions) < max_corrections:
            sub_positions.append(i)

    # Generate all variant combinations for ambiguous characters
    if sub_positions:
        candidates = _try_substitution_variants(corrected, sub_positions, corrected, max_corrections)
        # Score each candidate: pick the one that matches the most Tier 1 patterns
        best = corrected
        best_score = -1
        for candidate in candidates:
            score = sum(1 for p in SECTION_PATTERNS.values() if p.search(candidate))
            if score > best_score:
                best_score = score
                best = candidate
        corrected = best

    # Pass 3: Spurious space removal — only merge adjacent tokens when one is
    # a short fragment (<4 chars) and the joined result is a known section word.
    tokens = corrected.split()
    merged = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens):
            left, right = tokens[i], tokens[i + 1]
            # Only merge if one token is suspiciously short (OCR space artifact)
            if len(left) <= 3 or len(right) <= 3:
                joined = left + right
                if joined.lower() in _SECTION_WORDS:
                    merged.append(joined)
                    i += 2
                    continue
        merged.append(tokens[i])
        i += 1

    return " ".join(merged)


class TestTier2OCRTolerance:
    """Tier 2: OCR-degraded headings corrected via substitution table, then
    verified against Tier 1 regex patterns."""

    @pytest.mark.parametrize("ocr_text,expected_section", [
        ("1ndications for Use", "indications"),
        ("Bi0compatibility Testing", "biocompatibility"),
        ("5terilization Validation", "sterilization"),
        ("She1f Life", "shelf_life"),
        ("Perforrnance Data", "performance"),
        ("SUBSTANTIAL EQU1VALENCE", "predicate_se"),
        ("$oftware Description", "software"),
        ("Ste rilization", "sterilization"),
        ("8iocompatibility", "biocompatibility"),
        ("P3rformance 7esting", "performance"),
        ("C1inical Data", "clinical"),
        ("E1ectrical Safety", "emc_electrical"),
    ])
    def test_ocr_correction_then_regex_match(self, ocr_text, expected_section):
        """After OCR correction, the text should match the Tier 1 regex."""
        corrected = apply_ocr_corrections(ocr_text)
        pattern = SECTION_PATTERNS[expected_section]
        assert pattern.search(corrected), (
            f"OCR correction '{ocr_text}' → '{corrected}' did not match "
            f"pattern for '{expected_section}'"
        )

    def test_uncorrected_ocr_does_not_match(self):
        """Raw OCR text should NOT match Tier 1 patterns (proving Tier 2 is needed)."""
        assert not SECTION_PATTERNS["indications"].search("1ndications for Use")
        assert not SECTION_PATTERNS["sterilization"].search("5terilization Validation")
        assert not SECTION_PATTERNS["biocompatibility"].search("8iocompatibility")


# ---------------------------------------------------------------------------
# Tier 3: LLM Semantic Classification Helpers & Tests
# ---------------------------------------------------------------------------

# Non-standard heading map from references/section-patterns.md
NONSTANDARD_HEADING_MAP = {
    "intended purpose": "Indications for Use",
    "purpose and clinical application": "Indications for Use",
    "therapeutic indications": "Indications for Use",
    "product overview": "Device Description",
    "technical specifications": "Device Description",
    "design description": "Device Description",
    "predicate comparison": "Substantial Equivalence",
    "equivalence assessment": "Substantial Equivalence",
    "comparative analysis": "Substantial Equivalence",
    "bench testing": "Performance Testing",
    "verification and validation": "Performance Testing",
    "analytical performance": "Performance Testing",
    "biological safety": "Biocompatibility",
    "material biocompatibility": "Biocompatibility",
    "biological evaluation report": "Biocompatibility",
    "sterility": "Sterilization",
    "microbial control": "Sterilization",
    "reprocessing": "Sterilization",
    "stability": "Shelf Life",
    "package testing": "Shelf Life",
    "durability": "Shelf Life",
    "clinical evidence": "Clinical",
    "literature evidence": "Clinical",
    "post-market evidence": "Clinical",
    "firmware": "Software",
    "algorithm description": "Software",
    "digital health": "Software",
    "electromagnetic compatibility": "Electrical Safety",
    "wireless testing": "Electrical Safety",
    "usability engineering": "Human Factors",
    "ergonomic assessment": "Human Factors",
    "hazard analysis": "Risk Management",
    "fmea results": "Risk Management",
}

# Per-section classification signal keywords from references/section-patterns.md
SECTION_SIGNAL_KEYWORDS = {
    "Indications for Use": [
        "patient population", "anatomical site", "clinical condition",
        "prescription", "over-the-counter", "intended for",
    ],
    "Device Description": [
        "principle of operation", "components", "materials of construction",
        "dimensions", "mechanism of action",
    ],
    "Substantial Equivalence": [
        "predicate", "substantially equivalent", "comparison",
        "subject device", "technological characteristics",
    ],
    "Performance Testing": [
        "sample size", "pass/fail", "test method",
        "acceptance criteria", "bench testing",
    ],
    "Biocompatibility": [
        "ISO 10993", "cytotoxicity", "sensitization", "irritation",
        "systemic toxicity", "biocompatible", "biological evaluation",
    ],
    "Sterilization": [
        "sterility assurance level", "SAL", "ethylene oxide",
        "gamma", "ISO 11135", "ISO 11137",
    ],
    "Clinical": [
        "clinical study", "patients enrolled", "adverse events",
        "endpoints", "follow-up", "IDE", "literature review",
    ],
    "Shelf Life": [
        "accelerated aging", "real-time aging", "ASTM F1980",
        "expiration", "storage conditions", "package integrity",
    ],
    "Software": [
        "IEC 62304", "software lifecycle", "level of concern",
        "SOUP", "cybersecurity", "SBOM", "software architecture",
    ],
    "Electrical Safety": [
        "IEC 60601", "EMC", "electromagnetic", "leakage current",
        "dielectric strength", "wireless coexistence",
    ],
    "Human Factors": [
        "IEC 62366", "usability", "use error", "formative",
        "summative", "simulated use", "user interface",
    ],
    "Labeling": [
        "instructions for use", "package insert", "symbols",
        "ISO 15223", "warnings and precautions",
    ],
}


def count_section_signals(text, section_name):
    """Count how many classification signals for `section_name` appear in `text`.

    Returns the count and the list of matched signals.
    """
    keywords = SECTION_SIGNAL_KEYWORDS.get(section_name, [])
    matched = [kw for kw in keywords if kw.lower() in text.lower()]
    return len(matched), matched


class TestTier3NonStandardHeadings:
    """Tier 3: Non-standard headings mapped to canonical section names."""

    @pytest.mark.parametrize("heading,expected_canonical", [
        ("Intended Purpose", "Indications for Use"),
        ("Purpose and Clinical Application", "Indications for Use"),
        ("Therapeutic Indications", "Indications for Use"),
        ("Product Overview", "Device Description"),
        ("Technical Specifications", "Device Description"),
        ("Predicate Comparison", "Substantial Equivalence"),
        ("Equivalence Assessment", "Substantial Equivalence"),
        ("Biological Safety", "Biocompatibility"),
        ("Biological Evaluation Report", "Biocompatibility"),
        ("Sterility", "Sterilization"),
        ("Stability", "Shelf Life"),
        ("Clinical Evidence", "Clinical"),
    ])
    def test_heading_maps_to_canonical(self, heading, expected_canonical):
        """Non-standard heading should map to the correct canonical section."""
        canonical = NONSTANDARD_HEADING_MAP.get(heading.lower())
        assert canonical == expected_canonical, (
            f"Heading '{heading}' mapped to '{canonical}', "
            f"expected '{expected_canonical}'"
        )

    def test_all_map_entries_have_values(self):
        """Every entry in the heading map should have a non-empty canonical name."""
        for heading, canonical in NONSTANDARD_HEADING_MAP.items():
            assert canonical, f"Heading '{heading}' has empty canonical mapping"

    def test_map_covers_all_sections(self):
        """The heading map should cover at least 10 distinct canonical sections."""
        sections = set(NONSTANDARD_HEADING_MAP.values())
        assert len(sections) >= 10, f"Only {len(sections)} sections covered"


class TestTier3ContentSignals:
    """Tier 3: Content signal detection for section classification."""

    @pytest.mark.parametrize("text,section,min_signals", [
        (
            "The device is intended for patient population aged 18+ at the "
            "anatomical site of the lower extremity for treatment of a clinical "
            "condition involving chronic wounds. It is intended for prescription use.",
            "Indications for Use",
            3,
        ),
        (
            "Biocompatibility was evaluated per ISO 10993 series. Cytotoxicity "
            "testing demonstrated no adverse effects. Sensitization testing per "
            "ISO 10993-10 showed no delayed hypersensitivity. Irritation testing "
            "confirmed the device is non-irritating.",
            "Biocompatibility",
            3,
        ),
        (
            "Sterility assurance level (SAL) of 10^-6 was validated using "
            "ethylene oxide sterilization per ISO 11135. Half-cycle validation "
            "confirmed adequate lethality.",
            "Sterilization",
            3,
        ),
    ])
    def test_signal_count_meets_threshold(self, text, section, min_signals):
        """Text block should contain at least `min_signals` classification signals."""
        count, matched = count_section_signals(text, section)
        assert count >= min_signals, (
            f"Section '{section}': found {count} signals {matched}, "
            f"expected >= {min_signals}"
        )
