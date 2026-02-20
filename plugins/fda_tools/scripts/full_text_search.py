#!/usr/bin/env python3
"""
Full-Text Search Module for FDA 510(k) Predicate Discovery

Enables comprehensive searching across ALL sections of 510(k) summaries,
not just the Substantial Equivalence section.

Usage:
    from full_text_search import search_all_sections, find_predicates_by_feature

    # Search for keywords across all sections
    results = search_all_sections(['wireless', 'Bluetooth'], product_code='DQY')

    # Find predicates by material/technology features
    predicates = find_predicates_by_feature(
        features=['PEEK', 'titanium'],
        product_codes=['OVE', 'OVF']
    )
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Set, Optional
from collections import defaultdict, Counter


def load_structured_cache() -> Dict:
    """Load the structured text cache index."""
    structured_dir = Path.home() / 'fda-510k-data' / 'extraction' / 'structured_text_cache'

    if not structured_dir.exists():
        # Try legacy cache
        legacy = Path.home() / 'fda-510k-data' / 'extraction' / 'pdf_data.json'
        if legacy.exists():
            with open(legacy) as f:
                data = json.load(f)
            # Convert to structured format
            structured = {}
            for filename, content in data.items():
                k_number = filename.replace('.pdf', '').upper()
                text = content.get('text', '') if isinstance(content, dict) else str(content)
                structured[k_number] = {'full_text': text, 'sections': {}}
            return structured

    # Load from structured cache
    structured = {}
    for file_path in structured_dir.glob('*.json'):
        with open(file_path) as f:
            data = json.load(f)
        structured[data['k_number']] = data

    return structured


def search_all_sections(
    search_terms: List[str],
    k_number_list: Optional[List[str]] = None,
    product_codes: Optional[List[str]] = None,
    sections: Optional[List[str]] = None
) -> List[Dict]:
    """
    Search across ALL sections of 510(k) summaries.

    Args:
        search_terms: Keywords or phrases to search for
        k_number_list: Optional filter to specific K-numbers
        product_codes: Optional filter to specific product codes
        sections: Optional filter to specific sections (default: all)

    Returns:
        List of {k_number, section, matched_text_snippet, confidence, context}
    """
    structured_cache = load_structured_cache()
    results = []

    # Load product code mappings if filtering by product code
    product_code_map = {}
    if product_codes:
        # Try to load from FDA database files
        pmn_files = [
            Path.home() / 'fda-510k-data' / 'extraction' / 'pmn96cur.txt',
            Path.home() / 'fda-510k-data' / 'extraction' / 'pmn9195.txt',
        ]
        for pmn_file in pmn_files:
            if pmn_file.exists():
                with open(pmn_file, encoding='latin-1') as f:
                    import csv
                    reader = csv.reader(f, delimiter='|')
                    for row in reader:
                        if len(row) > 14:
                            k_num = row[0]
                            prod_code = row[14]
                            if prod_code in product_codes:
                                product_code_map[k_num] = prod_code

    # Filter K-numbers if needed
    k_numbers_to_search = k_number_list
    if product_codes and not k_number_list:
        k_numbers_to_search = list(product_code_map.keys())
    elif not k_numbers_to_search:
        k_numbers_to_search = list(structured_cache.keys())

    # Compile search patterns (case-insensitive)
    patterns = [re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE) for term in search_terms]

    # Search each document
    for k_number in k_numbers_to_search:
        if k_number not in structured_cache:
            continue

        doc = structured_cache[k_number]

        # Search in sections
        doc_sections = doc.get('sections', {})

        # Section-aware search
        sections_to_search = sections if sections else list(doc_sections.keys()) + ['full_text']

        for section_name in sections_to_search:
            if section_name == 'full_text':
                text = doc.get('full_text', '')
                section_context = 'general'
            else:
                if section_name not in doc_sections:
                    continue
                text = doc_sections[section_name].get('text', '')
                section_context = section_name

            # Search for each term
            for i, pattern in enumerate(patterns):
                for match in pattern.finditer(text):
                    # Extract context window (500 chars around match)
                    start = max(0, match.start() - 250)
                    end = min(len(text), match.end() + 250)
                    snippet = text[start:end]

                    # Clean up snippet
                    snippet = snippet.replace('\n', ' ').strip()
                    snippet = re.sub(r'\s+', ' ', snippet)

                    # Confidence scoring based on section
                    if section_name == 'predicate_se':
                        confidence = 40  # SE section
                    elif section_name in ['performance_testing', 'clinical_testing', 'biocompatibility']:
                        confidence = 25  # Testing sections
                    elif section_name == 'device_description':
                        confidence = 20  # Device description
                    else:
                        confidence = 10  # General

                    results.append({
                        'k_number': k_number,
                        'section': section_context,
                        'matched_term': search_terms[i],
                        'matched_text_snippet': snippet,
                        'confidence': confidence,
                        'context': section_name,
                        'match_position': match.start()
                    })

    # Sort by confidence (highest first)
    results.sort(key=lambda x: (-x['confidence'], x['k_number']))

    return results


def find_predicates_by_feature(
    features: List[str],
    product_codes: Optional[List[str]] = None,
    min_confidence: int = 10
) -> Dict[str, Dict]:
    """
    Feature-based predicate discovery.

    Searches for predicates by material, technology, or feature keywords.

    Args:
        features: Feature keywords (e.g., ['wireless', 'Bluetooth'], ['PEEK', 'titanium'])
        product_codes: Optional filter to specific product codes
        min_confidence: Minimum confidence score to include (default: 10)

    Returns:
        Dict mapping K-number -> {features_found, sections, confidence, summary}

    Examples:
        # Material search
        find_predicates_by_feature(['PEEK', 'titanium', 'cobalt-chrome'])

        # Technology search
        find_predicates_by_feature(['Bluetooth', 'wireless', 'RF communication'])

        # Testing method search
        find_predicates_by_feature(['fatigue testing', 'torsion testing'])
    """
    # Search for all features
    search_results = search_all_sections(
        search_terms=features,
        product_codes=product_codes
    )

    # Group by K-number
    by_knumber = defaultdict(lambda: {
        'features_found': set(),
        'sections': set(),
        'confidence_scores': [],
        'snippets': []
    })

    for result in search_results:
        if result['confidence'] < min_confidence:
            continue

        k_num = result['k_number']
        by_knumber[k_num]['features_found'].add(result['matched_term'])
        by_knumber[k_num]['sections'].add(result['section'])
        by_knumber[k_num]['confidence_scores'].append(result['confidence'])
        by_knumber[k_num]['snippets'].append({
            'feature': result['matched_term'],
            'section': result['section'],
            'snippet': result['matched_text_snippet']
        })

    # Build final results
    predicates = {}
    for k_number, data in by_knumber.items():
        # Aggregate confidence (average of section scores)
        avg_confidence = sum(data['confidence_scores']) / len(data['confidence_scores'])

        predicates[k_number] = {
            'features_found': list(data['features_found']),
            'feature_count': len(data['features_found']),
            'sections': list(data['sections']),
            'confidence': int(avg_confidence),
            'match_count': len(data['snippets']),
            'snippets': data['snippets'],
            'summary': f"Found {len(data['features_found'])} features across {len(data['sections'])} sections"
        }

    # Sort by feature count (most features first), then confidence
    sorted_predicates = dict(sorted(
        predicates.items(),
        key=lambda x: (-x[1]['feature_count'], -x[1]['confidence'])
    ))

    return sorted_predicates


def find_cross_product_code_predicates(
    novel_features: List[str],
    primary_product_code: str,
    search_all_codes: bool = True
) -> Dict[str, List[Dict]]:
    """
    Cross-product-code search for novel features with little precedent.

    When a feature has limited precedent in the primary product code,
    automatically search other product codes for supporting predicates.

    Args:
        novel_features: Features with limited precedent
        primary_product_code: Primary product code of subject device
        search_all_codes: If True, search across all product codes

    Returns:
        Dict mapping feature -> [list of secondary predicates from other codes]
    """
    secondary_predicates = {}

    for feature in novel_features:
        # Search across all product codes (or specific ones)
        results = find_predicates_by_feature(
            features=[feature],
            product_codes=None if search_all_codes else []
        )

        # Filter out primary product code devices
        # (we want SECONDARY predicates from other codes)
        # Note: Would need product code lookup here
        secondary_predicates[feature] = results

    return secondary_predicates


if __name__ == '__main__':
    # CLI interface for testing
    import argparse

    parser = argparse.ArgumentParser(description='Full-text search for FDA 510(k) predicates')
    parser.add_argument('--features', nargs='+', required=True,
                        help='Feature keywords to search for')
    parser.add_argument('--product-codes', nargs='+',
                        help='Filter to specific product codes')
    parser.add_argument('--min-confidence', type=int, default=10,
                        help='Minimum confidence score (default: 10)')
    parser.add_argument('--limit', type=int, default=20,
                        help='Max results to return (default: 20)')

    args = parser.parse_args()

    print("="*60)
    print("FDA 510(k) Full-Text Feature Search")
    print("="*60)
    print(f"Features: {', '.join(args.features)}")
    if args.product_codes:
        print(f"Product Codes: {', '.join(args.product_codes)}")
    print()

    results = find_predicates_by_feature(
        features=args.features,
        product_codes=args.product_codes,
        min_confidence=args.min_confidence
    )

    print(f"Found {len(results)} predicates\n")

    for i, (k_number, data) in enumerate(results.items(), 1):
        if i > args.limit:
            break

        print(f"{i}. {k_number}")
        print(f"   Features: {', '.join(data['features_found'])}")
        print(f"   Sections: {', '.join(data['sections'])}")
        print(f"   Confidence: {data['confidence']}/40")
        print(f"   Matches: {data['match_count']}")
        print()
