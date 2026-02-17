#!/usr/bin/env python3
"""
PMA Section Extractor -- 15-section extraction engine for SSED PDFs.

Extracts structured sections from PMA Summary of Safety and Effectiveness
Data (SSED) documents. Supports 15 key section types with multiple header
pattern variations, Roman numeral detection, and quality scoring.

SSED sections typically follow this structure:
    I.    General Information
    II.   Indications for Use
    III.  Device Description
    IV.   Alternative Practices and Procedures
    V.    Marketing History
    VI.   Summary of Preclinical Studies
    VII.  Summary of Clinical Studies
    VIII. Summary of Nonclinical Testing
    IX.   Manufacturing
    X.    Labeling
    XI.   Benefit-Risk Analysis
    XII.  Panel Recommendation
    XIII. Overall Conclusions
    XIV.  Potential Risks and Adverse Effects
    XV.   Patient Perspective / Clinical Evidence Summary

Usage:
    from pma_section_extractor import PMAExtractor

    extractor = PMAExtractor()
    result = extractor.extract_from_pdf("/path/to/ssed.pdf")
    result = extractor.extract_from_text(text_content)

    # CLI usage:
    python3 pma_section_extractor.py --pdf /path/to/ssed.pdf
    python3 pma_section_extractor.py --pdf /path/to/ssed.pdf --output sections.json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pma_data_store import PMADataStore


# ------------------------------------------------------------------
# 15 PMA SSED section definitions
# ------------------------------------------------------------------

# Section name -> (display_name, list of regex pattern strings)
# Patterns match section headers in SSEDs (Roman numerals, numbered, text-based)
SSED_SECTIONS = {
    "general_information": {
        "display_name": "General Information",
        "section_number": 1,
        "patterns": [
            r"(?i)I\.\s+GENERAL\s+INFORMATION",
            r"(?i)GENERAL\s+INFORMATION",
            r"(?i)^I\.\s+General\s+",
            r"(?i)1\.?\s+GENERAL\s+INFORMATION",
            r"(?i)SECTION\s+(?:I|1)[:\.]?\s*GENERAL\s+INFORMATION",
        ],
    },
    "indications_for_use": {
        "display_name": "Indications for Use",
        "section_number": 2,
        "patterns": [
            r"(?i)II\.\s+INDICATIONS?\s+FOR\s+USE",
            r"(?i)INDICATIONS?\s+FOR\s+USE",
            r"(?i)^II\.\s+Indication",
            r"(?i)2\.?\s+INDICATIONS?\s+FOR\s+USE",
            r"(?i)INTENDED\s+USE",
            r"(?i)SECTION\s+(?:II|2)[:\.]?\s*INDICATIONS?",
        ],
    },
    "device_description": {
        "display_name": "Device Description",
        "section_number": 3,
        "patterns": [
            r"(?i)III\.\s+DEVICE\s+DESCRIPTION",
            r"(?i)DEVICE\s+DESCRIPTION",
            r"(?i)^III\.\s+Device\s+Description",
            r"(?i)3\.?\s+DEVICE\s+DESCRIPTION",
            r"(?i)DESCRIPTION\s+OF\s+(?:THE\s+)?DEVICE",
            r"(?i)SECTION\s+(?:III|3)[:\.]?\s*DEVICE",
        ],
    },
    "alternative_practices": {
        "display_name": "Alternative Practices and Procedures",
        "section_number": 4,
        "patterns": [
            r"(?i)IV\.\s+ALTERNATIVE\s+PRACTICES",
            r"(?i)ALTERNATIVE\s+PRACTICES\s+AND\s+PROCEDURES",
            r"(?i)ALTERNATIVE\s+(?:THERAPIES|TREATMENTS|APPROACHES)",
            r"(?i)4\.?\s+ALTERNATIVE\s+PRACTICES",
            r"(?i)CONTRAINDICATIONS\s+.*\s+ALTERNATIVE",
        ],
    },
    "marketing_history": {
        "display_name": "Marketing History",
        "section_number": 5,
        "patterns": [
            r"(?i)V\.\s+MARKETING\s+HISTORY",
            r"(?i)MARKETING\s+HISTORY",
            r"(?i)5\.?\s+MARKETING\s+HISTORY",
            r"(?i)DEVICE\s+MARKETING\s+HISTORY",
            r"(?i)REGULATORY\s+HISTORY",
        ],
    },
    "potential_risks": {
        "display_name": "Potential Risks and Adverse Effects",
        "section_number": 6,
        "patterns": [
            r"(?i)(?:VI|XIV)\.\s+(?:SUMMARY\s+OF\s+)?POTENTIAL\s+(?:ADVERSE|RISKS)",
            r"(?i)POTENTIAL\s+(?:ADVERSE\s+EFFECTS|RISKS\s+AND\s+ADVERSE)",
            r"(?i)RISKS?\s+AND\s+ADVERSE\s+EFFECTS?",
            r"(?i)6\.?\s+POTENTIAL\s+(?:RISKS|ADVERSE)",
            r"(?i)ADVERSE\s+(?:EFFECTS?|EVENTS?)\s+(?:AND\s+)?COMPLICATIONS?",
            r"(?i)COMPLICATIONS?\s+AND\s+ADVERSE",
        ],
    },
    "preclinical_studies": {
        "display_name": "Summary of Preclinical Studies",
        "section_number": 7,
        "patterns": [
            r"(?i)(?:VI|VII)\.\s+(?:SUMMARY\s+OF\s+)?(?:NON[- ]?CLINICAL|PRE[- ]?CLINICAL)\s+(?:STUDIES|TESTING)",
            r"(?i)(?:SUMMARY\s+OF\s+)?(?:NON[- ]?CLINICAL|PRE[- ]?CLINICAL)\s+(?:STUDIES|TESTING|DATA)",
            r"(?i)ANIMAL\s+(?:STUDIES|TESTING|DATA)",
            r"(?i)7\.?\s+(?:NON[- ]?CLINICAL|PRE[- ]?CLINICAL)",
            r"(?i)IN\s+VIVO\s+(?:STUDIES|TESTING)",
        ],
    },
    "clinical_studies": {
        "display_name": "Summary of Clinical Studies",
        "section_number": 8,
        "patterns": [
            r"(?i)(?:VII|VIII)\.\s+(?:SUMMARY\s+OF\s+)?CLINICAL\s+(?:STUDIES|DATA|EVIDENCE)",
            r"(?i)(?:SUMMARY\s+OF\s+)?CLINICAL\s+(?:STUDIES|INVESTIGATION|TRIAL|DATA)",
            r"(?i)CLINICAL\s+(?:STUDY|STUDIES)\s+(?:DESIGN|RESULTS|SUMMARY)",
            r"(?i)8\.?\s+CLINICAL\s+(?:STUDIES|DATA)",
            r"(?i)PIVOTAL\s+(?:CLINICAL\s+)?(?:STUDY|TRIAL)",
            r"(?i)HUMAN\s+CLINICAL\s+(?:STUDIES|DATA)",
        ],
    },
    "statistical_analysis": {
        "display_name": "Statistical Analysis",
        "section_number": 9,
        "patterns": [
            r"(?i)(?:SUMMARY\s+OF\s+)?STATISTICAL\s+(?:ANALYSIS|METHODS|DESIGN)",
            r"(?i)BIOSTATISTICAL\s+ANALYSIS",
            r"(?i)(?:IX|9)\.\s+(?:SUMMARY\s+OF\s+)?STATISTICAL",
            r"(?i)STATISTICAL\s+CONSIDERATIONS",
            r"(?i)STUDY\s+DESIGN\s+AND\s+STATISTICAL\s+ANALYSIS",
            r"(?i)SAMPLE\s+SIZE\s+(?:DETERMINATION|JUSTIFICATION|CALCULATION)",
        ],
    },
    "benefit_risk": {
        "display_name": "Benefit-Risk Analysis",
        "section_number": 10,
        "patterns": [
            r"(?i)(?:XI|X)\.\s+BENEFIT[- ]?RISK\s+(?:ANALYSIS|ASSESSMENT|DETERMINATION)",
            r"(?i)BENEFIT[- ]?RISK\s+(?:ANALYSIS|ASSESSMENT|DETERMINATION|CONSIDERATION)",
            r"(?i)10\.?\s+BENEFIT[- ]?RISK",
            r"(?i)RISK[- ]?BENEFIT\s+(?:ANALYSIS|ASSESSMENT)",
            r"(?i)PROBABLE\s+BENEFITS?\s+(?:AND|VERSUS)\s+PROBABLE\s+RISKS?",
        ],
    },
    "overall_conclusions": {
        "display_name": "Overall Conclusions",
        "section_number": 11,
        "patterns": [
            r"(?i)(?:XI|XII|XIII)\.\s+(?:OVERALL\s+)?CONCLUSIONS?",
            r"(?i)OVERALL\s+CONCLUSIONS?(?:\s+(?:DRAWN|OF|FROM))?",
            r"(?i)11\.?\s+(?:OVERALL\s+)?CONCLUSIONS?",
            r"(?i)(?:SUMMARY\s+AND\s+)?CONCLUSIONS?",
            r"(?i)FDA\s+CONCLUSIONS?",
            r"(?i)CDRH\s+DECISION\s+(?:SUMMARY|RATIONALE)",
        ],
    },
    "panel_recommendation": {
        "display_name": "Panel Recommendation",
        "section_number": 12,
        "patterns": [
            r"(?i)(?:XII|XIII)\.\s+(?:ADVISORY\s+)?PANEL\s+RECOMMENDATION",
            r"(?i)(?:ADVISORY\s+)?PANEL\s+RECOMMENDATION",
            r"(?i)ADVISORY\s+COMMITTEE\s+RECOMMENDATION",
            r"(?i)12\.?\s+PANEL\s+RECOMMENDATION",
            r"(?i)PANEL\s+(?:MEETING|DISCUSSION|REVIEW)",
        ],
    },
    "nonclinical_testing": {
        "display_name": "Summary of Nonclinical Testing",
        "section_number": 13,
        "patterns": [
            r"(?i)(?:VIII|IX)\.\s+(?:SUMMARY\s+OF\s+)?NON[- ]?CLINICAL\s+TESTING",
            r"(?i)NON[- ]?CLINICAL\s+(?:TESTING|BENCH\s+TESTING|PERFORMANCE)",
            r"(?i)13\.?\s+NON[- ]?CLINICAL\s+TESTING",
            r"(?i)BENCH\s+(?:TESTING|TOP\s+TESTING)",
            r"(?i)(?:SUMMARY\s+OF\s+)?PERFORMANCE\s+TESTING",
            r"(?i)BIOCOMPATIBILITY\s+(?:TESTING|EVALUATION|ASSESSMENT)",
        ],
    },
    "manufacturing": {
        "display_name": "Manufacturing and Sterilization",
        "section_number": 14,
        "patterns": [
            r"(?i)(?:IX|X)\.\s+MANUFACTUR(?:ING|E)",
            r"(?i)MANUFACTUR(?:ING|E)(?:\s+AND\s+STERILIZ(?:ATION|ING))?",
            r"(?i)14\.?\s+MANUFACTUR(?:ING|E)",
            r"(?i)STERILIZ(?:ATION|ING)\s+(?:AND\s+)?MANUFACTUR(?:ING|E)",
            r"(?i)QUALITY\s+(?:SYSTEM|ASSURANCE)\s+(?:AND\s+)?MANUFACTUR",
        ],
    },
    "labeling": {
        "display_name": "Labeling",
        "section_number": 15,
        "patterns": [
            r"(?i)(?:X|XI)\.\s+LABELING",
            r"(?i)LABELING(?:\s+(?:REQUIREMENTS?|REVIEW|SUMMARY))?",
            r"(?i)15\.?\s+LABELING",
            r"(?i)INSTRUCTIONS?\s+FOR\s+USE",
            r"(?i)PACKAGE\s+(?:INSERT|LABEL(?:ING)?)",
        ],
    },
}

# Compile all patterns for efficiency
_COMPILED_PATTERNS = {}
for section_key, section_def in SSED_SECTIONS.items():
    _COMPILED_PATTERNS[section_key] = [
        re.compile(p, re.MULTILINE) for p in section_def["patterns"]
    ]


class PMAExtractor:
    """Extract 15 structured sections from PMA SSED documents.

    Supports PDF files (via pdfplumber/PyPDF2) and raw text input.
    Uses regex-based pattern matching with multiple header variations
    per section, Roman numeral detection, and quality scoring.
    """

    def __init__(self, store: Optional[PMADataStore] = None):
        """Initialize PMA section extractor.

        Args:
            store: Optional PMADataStore for saving extracted sections.
        """
        self.store = store

    def extract_from_pdf(self, pdf_path: str) -> Dict:
        """Extract sections from a PMA SSED PDF file.

        Args:
            pdf_path: Path to SSED PDF file.

        Returns:
            Extraction result dictionary with sections and metadata.
        """
        text = self._extract_text_from_pdf(pdf_path)
        if text is None:
            return {
                "success": False,
                "error": "Could not extract text from PDF (no PDF library available)",
                "pdf_path": pdf_path,
                "sections": {},
                "metadata": {},
            }

        result = self.extract_from_text(text)
        result["pdf_path"] = pdf_path
        result["page_count"] = self._get_page_count(pdf_path)
        return result

    def extract_from_text(self, text: str) -> Dict:
        """Extract sections from raw text content.

        Args:
            text: Full text content from an SSED document.

        Returns:
            Extraction result dictionary:
            {
                "success": True,
                "sections": {
                    "general_information": {
                        "display_name": "General Information",
                        "content": "...",
                        "word_count": 500,
                        "header_matched": "I. GENERAL INFORMATION",
                        "start_pos": 0,
                        "end_pos": 5000,
                        "confidence": 0.95
                    },
                    ...
                },
                "metadata": {
                    "total_sections_found": 12,
                    "total_word_count": 25000,
                    "char_count": 150000,
                    "extraction_quality": "HIGH",
                    "quality_score": 85,
                    "missing_sections": ["panel_recommendation", "statistical_analysis"],
                    "section_order": ["general_information", "indications_for_use", ...]
                }
            }
        """
        if not text or len(text) < 100:
            return {
                "success": False,
                "error": "Text too short for section extraction",
                "sections": {},
                "metadata": {"char_count": len(text) if text else 0},
            }

        # Find section boundaries
        boundaries = self._detect_boundaries(text)

        # Extract section content
        sections = self._extract_sections(text, boundaries)

        # Build metadata
        metadata = self._build_metadata(text, sections, boundaries)

        return {
            "success": True,
            "sections": sections,
            "metadata": metadata,
        }

    def extract_and_save(self, pma_number: str, pdf_path: Optional[str] = None) -> Dict:
        """Extract sections and save to data store.

        Args:
            pma_number: PMA number for data store indexing.
            pdf_path: Optional PDF path. If None, looks in data store cache.

        Returns:
            Extraction result dictionary.
        """
        if not self.store:
            self.store = PMADataStore()

        # Find PDF path if not provided
        if pdf_path is None:
            pma_dir = self.store.get_pma_dir(pma_number.upper())
            pdf_path = str(pma_dir / "ssed.pdf")

        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "error": f"SSED PDF not found at {pdf_path}",
                "pma_number": pma_number,
                "sections": {},
                "metadata": {},
            }

        result = self.extract_from_pdf(pdf_path)
        result["pma_number"] = pma_number.upper()

        if result["success"]:
            # Save extracted sections
            self.store.save_extracted_sections(pma_number.upper(), result)

            # Update manifest
            section_count = result["metadata"].get("total_sections_found", 0)
            word_count = result["metadata"].get("total_word_count", 0)
            self.store.mark_sections_extracted(
                pma_number.upper(), section_count, word_count
            )

        return result

    # ------------------------------------------------------------------
    # Internal: text extraction from PDF
    # ------------------------------------------------------------------

    def _extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """Extract text from PDF using available library.

        Tries pdfplumber first (higher quality), falls back to PyPDF2.

        Args:
            pdf_path: Path to PDF file.

        Returns:
            Extracted text string, or None if no PDF library available.
        """
        # Try pdfplumber first
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except ImportError:
            # pdfplumber not installed, try PyPDF2
            pass
        except Exception as e:
            print(f"Warning: pdfplumber text extraction failed for {pdf_path}: {e}", file=sys.stderr)

        # Try PyPDF2
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(pdf_path)
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except ImportError:
            # Neither pdfplumber nor PyPDF2 installed
            print("Warning: No PDF library available (install pdfplumber or PyPDF2)", file=sys.stderr)
        except Exception as e:
            print(f"Warning: PyPDF2 text extraction failed for {pdf_path}: {e}", file=sys.stderr)

        return None

    def _get_page_count(self, pdf_path: str) -> int:
        """Get page count from PDF.

        Args:
            pdf_path: Path to PDF file.

        Returns:
            Page count, or 0 if unable to determine.
        """
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
        except ImportError:
            # pdfplumber not installed, try PyPDF2
            pass
        except Exception as e:
            print(f"Warning: pdfplumber page count failed for {pdf_path}: {e}", file=sys.stderr)

        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(pdf_path)
            return len(reader.pages)
        except ImportError:
            print("Warning: No PDF library available for page count (install pdfplumber or PyPDF2)", file=sys.stderr)
        except Exception as e:
            print(f"Warning: PyPDF2 page count failed for {pdf_path}: {e}", file=sys.stderr)

        return 0

    # ------------------------------------------------------------------
    # Internal: boundary detection
    # ------------------------------------------------------------------

    def _detect_boundaries(self, text: str) -> List[Tuple[int, str, str, float]]:
        """Detect section header positions in text.

        Returns a sorted list of (position, section_key, matched_header, confidence)
        tuples representing section boundaries.

        Args:
            text: Full document text.

        Returns:
            List of (start_pos, section_key, header_text, confidence) tuples.
        """
        matches = []

        for section_key, patterns in _COMPILED_PATTERNS.items():
            best_match = None
            best_confidence = 0

            for i, pattern in enumerate(patterns):
                for m in pattern.finditer(text):
                    # First pattern = highest confidence
                    confidence = 1.0 - (i * 0.1)
                    confidence = max(confidence, 0.5)

                    # Boost confidence if preceded by newline (likely a real header)
                    pos = m.start()
                    if pos == 0 or text[pos - 1] == "\n":
                        confidence = min(confidence + 0.05, 1.0)

                    # Boost if header is on its own line (short line)
                    line_start = text.rfind("\n", 0, pos) + 1
                    line_end = text.find("\n", pos)
                    if line_end == -1:
                        line_end = len(text)
                    line = text[line_start:line_end].strip()
                    if len(line) < 80:
                        confidence = min(confidence + 0.05, 1.0)

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = (pos, section_key, m.group().strip(), confidence)

            if best_match:
                matches.append(best_match)

        # Sort by position
        matches.sort(key=lambda x: x[0])

        # Deduplicate overlapping sections (keep highest confidence)
        seen_keys = set()
        deduplicated = []
        for match in matches:
            if match[1] not in seen_keys:
                deduplicated.append(match)
                seen_keys.add(match[1])

        return deduplicated

    # ------------------------------------------------------------------
    # Internal: section content extraction
    # ------------------------------------------------------------------

    def _extract_sections(self, text: str, boundaries: List[Tuple]) -> Dict:
        """Extract section content using detected boundaries.

        Args:
            text: Full document text.
            boundaries: List of (start_pos, section_key, header, confidence) tuples.

        Returns:
            Dictionary of section_key -> section data.
        """
        sections = {}

        for i, (start_pos, section_key, header, confidence) in enumerate(boundaries):
            # End position is the start of the next section or end of text
            if i + 1 < len(boundaries):
                end_pos = boundaries[i + 1][0]
            else:
                end_pos = len(text)

            content = text[start_pos:end_pos].strip()
            word_count = len(content.split())

            # Skip very short sections (likely false positive)
            if word_count < 10:
                continue

            section_def = SSED_SECTIONS.get(section_key, {})
            sections[section_key] = {
                "display_name": section_def.get("display_name", section_key),
                "section_number": section_def.get("section_number", 0),
                "content": content,
                "word_count": word_count,
                "header_matched": header,
                "start_pos": start_pos,
                "end_pos": end_pos,
                "confidence": round(confidence, 3),
            }

        return sections

    # ------------------------------------------------------------------
    # Internal: metadata and quality scoring
    # ------------------------------------------------------------------

    def _build_metadata(self, text: str, sections: Dict,
                        boundaries: List[Tuple]) -> Dict:
        """Build extraction metadata and quality metrics.

        Args:
            text: Full document text.
            sections: Extracted sections dictionary.
            boundaries: Detected boundaries.

        Returns:
            Metadata dictionary.
        """
        total_word_count = sum(s["word_count"] for s in sections.values())

        # Identify missing sections
        all_section_keys = set(SSED_SECTIONS.keys())
        found_keys = set(sections.keys())
        missing = all_section_keys - found_keys

        # Quality scoring (0-100)
        quality_score = self._calculate_quality_score(sections, text)

        # Quality level
        if quality_score >= 75:
            quality_level = "HIGH"
        elif quality_score >= 50:
            quality_level = "MEDIUM"
        else:
            quality_level = "LOW"

        # Section order as found in document
        section_order = [b[1] for b in boundaries if b[1] in sections]

        # Average confidence
        confidences = [s["confidence"] for s in sections.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "total_sections_found": len(sections),
            "total_possible_sections": len(SSED_SECTIONS),
            "total_word_count": total_word_count,
            "char_count": len(text),
            "extraction_quality": quality_level,
            "quality_score": quality_score,
            "average_confidence": round(avg_confidence, 3),
            "missing_sections": sorted(missing),
            "section_order": section_order,
            "extraction_timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
        }

    def _calculate_quality_score(self, sections: Dict, text: str) -> int:
        """Calculate extraction quality score (0-100).

        Scoring factors:
            - Section count (0-40 points): More sections = better extraction
            - Key sections present (0-30 points): Critical sections found
            - Content density (0-15 points): Sufficient word count per section
            - Confidence average (0-15 points): Pattern match confidence

        Args:
            sections: Extracted sections dictionary.
            text: Full document text.

        Returns:
            Quality score 0-100.
        """
        score = 0

        # Factor 1: Section count (0-40 points)
        section_count = len(sections)
        total_possible = len(SSED_SECTIONS)
        score += int(40 * min(section_count / total_possible, 1.0))

        # Factor 2: Key sections present (0-30 points)
        key_sections = [
            "general_information",
            "indications_for_use",
            "device_description",
            "clinical_studies",
            "overall_conclusions",
            "benefit_risk",
        ]
        key_found = sum(1 for k in key_sections if k in sections)
        score += int(30 * key_found / len(key_sections))

        # Factor 3: Content density (0-15 points)
        if sections:
            avg_words = sum(s["word_count"] for s in sections.values()) / len(sections)
            if avg_words >= 500:
                score += 15
            elif avg_words >= 200:
                score += 10
            elif avg_words >= 50:
                score += 5

        # Factor 4: Confidence average (0-15 points)
        if sections:
            confidences = [s["confidence"] for s in sections.values()]
            avg_conf = sum(confidences) / len(confidences)
            score += int(15 * avg_conf)

        return min(score, 100)

    # ------------------------------------------------------------------
    # Batch extraction
    # ------------------------------------------------------------------

    def extract_batch(self, pma_numbers: List[str],
                      progress_callback=None) -> List[Dict]:
        """Extract sections for multiple PMAs.

        Args:
            pma_numbers: List of PMA numbers.
            progress_callback: Optional callback(current, total, result).

        Returns:
            List of extraction result dicts.
        """
        if not self.store:
            self.store = PMADataStore()

        results = []
        total = len(pma_numbers)

        for i, pma_number in enumerate(pma_numbers):
            result = self.extract_and_save(pma_number)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, total, result)
            else:
                status = "OK" if result["success"] else "FAIL"
                sections = result.get("metadata", {}).get("total_sections_found", 0)
                quality = result.get("metadata", {}).get("extraction_quality", "N/A")
                print(f"[{i + 1}/{total}] {pma_number}: {status} ({sections} sections, {quality})")

        return results


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def get_section_list() -> List[Dict]:
    """Get the list of all 15 supported PMA SSED sections.

    Returns:
        List of dicts with key, display_name, section_number.
    """
    return [
        {
            "key": key,
            "display_name": sec["display_name"],
            "section_number": sec["section_number"],
        }
        for key, sec in sorted(
            SSED_SECTIONS.items(), key=lambda x: x[1]["section_number"]
        )
    ]


def print_section_list() -> None:
    """Print the 15 supported sections in order."""
    for sec in get_section_list():
        print(f"  {sec['section_number']:2d}. {sec['display_name']} ({sec['key']})")


# ------------------------------------------------------------------
# CLI interface
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PMA SSED Section Extractor -- 15-section extraction engine"
    )
    parser.add_argument("--pdf", help="Path to SSED PDF to extract")
    parser.add_argument("--pma", help="PMA number to extract (uses cached SSED)")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--list-sections", action="store_true", dest="list_sections",
                        help="List all 15 supported sections")
    parser.add_argument("--batch", help="Comma-separated PMA numbers for batch extraction")

    args = parser.parse_args()
    store = PMADataStore()
    extractor = PMAExtractor(store)

    if args.list_sections:
        print("Supported PMA SSED Sections (15 total):")
        print_section_list()
        return

    if args.pdf:
        result = extractor.extract_from_pdf(args.pdf)
    elif args.pma:
        result = extractor.extract_and_save(args.pma)
    elif args.batch:
        pma_numbers = [p.strip().upper() for p in args.batch.split(",") if p.strip()]
        results = extractor.extract_batch(pma_numbers)

        # Summary
        success = sum(1 for r in results if r["success"])
        print(f"\nBatch extraction complete: {success}/{len(results)} successful")
        for r in results:
            pma = r.get("pma_number", "unknown")
            sections = r.get("metadata", {}).get("total_sections_found", 0)
            quality = r.get("metadata", {}).get("quality_score", 0)
            print(f"  {pma}: {sections} sections, quality={quality}/100")
        return
    else:
        parser.error("Specify --pdf, --pma, --batch, or --list-sections")
        return

    # Output results
    if result.get("success"):
        meta = result.get("metadata", {})
        print(f"EXTRACTION:SUCCESS")
        print(f"SECTIONS_FOUND:{meta.get('total_sections_found', 0)}/{meta.get('total_possible_sections', 15)}")
        print(f"QUALITY:{meta.get('extraction_quality', 'N/A')} ({meta.get('quality_score', 0)}/100)")
        print(f"TOTAL_WORDS:{meta.get('total_word_count', 0)}")
        print(f"AVG_CONFIDENCE:{meta.get('average_confidence', 0):.3f}")
        if meta.get("missing_sections"):
            print(f"MISSING:{','.join(meta['missing_sections'])}")
        print("---")
        for key, sec in sorted(result["sections"].items(),
                               key=lambda x: x[1].get("section_number", 0)):
            print(f"SECTION:{sec['display_name']}|{sec['word_count']} words|conf={sec['confidence']:.2f}")
    else:
        print(f"EXTRACTION:FAILED")
        print(f"ERROR:{result.get('error', 'Unknown error')}")

    # Save to file if requested
    if args.output:
        with open(args.output, "w") as f:
            # Don't include full content in output file to keep it readable
            output_data = {
                "pma_number": result.get("pma_number", ""),
                "success": result.get("success", False),
                "metadata": result.get("metadata", {}),
                "sections_summary": {
                    key: {
                        "display_name": sec["display_name"],
                        "word_count": sec["word_count"],
                        "confidence": sec["confidence"],
                    }
                    for key, sec in result.get("sections", {}).items()
                },
            }
            json.dump(output_data, f, indent=2)
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
