#!/usr/bin/env python3
"""
Demo script for Progress Bar functionality (FDA-61 / FE-006).

Demonstrates the progress bar feature with a simulated long-running
similarity matrix computation.

Usage:
    python3 demo_progress_bar.py --devices 20
    python3 demo_progress_bar.py --devices 50 --no-progress
"""

import argparse
import json
import os
import sys
import time

# Add scripts directory to path
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

from section_analytics import pairwise_similarity_matrix
from compare_sections import ProgressBar


def generate_synthetic_section_data(num_devices: int, section_type: str = "clinical_testing"):
    """Generate synthetic section data for demonstration.

    Args:
        num_devices: Number of synthetic devices to generate.
        section_type: Section type to populate.

    Returns:
        Dict of synthetic section data compatible with pairwise_similarity_matrix.
    """
    section_data = {}

    for i in range(num_devices):
        k_number = f"K2024{i:05d}"
        # Generate varied clinical testing text to produce different similarities
        base_text = [
            "The device was subjected to clinical testing per ISO 14155.",
            "Clinical endpoints included safety and efficacy metrics.",
            "A total of 120 subjects were enrolled across 5 sites.",
            "Primary endpoint was met with statistical significance (p<0.05).",
            "Adverse events were mild and resolved without intervention.",
        ]

        # Vary the content slightly for different devices
        text_sections = base_text[:3 + (i % 3)]
        if i % 2 == 0:
            text_sections.append("Biocompatibility testing was performed per ISO 10993-1.")
        if i % 3 == 0:
            text_sections.append("Device performance met all specifications.")

        section_text = " ".join(text_sections)

        section_data[k_number] = {
            "sections": {
                section_type: {
                    "text": section_text,
                    "word_count": len(section_text.split()),
                    "standards": ["ISO 14155", "ISO 10993-1"],
                }
            },
            "device_name": f"Synthetic Device {i}",
            "decision_date": "20240101",
            "metadata": {"product_code": "DQY"},
        }

    return section_data


def main():
    """Demo entry point."""
    parser = argparse.ArgumentParser(
        description="Demo: Progress Bar for Long-Running Analytics (FDA-61)"
    )
    parser.add_argument(
        "--devices", type=int, default=20,
        help="Number of synthetic devices to generate (default: 20)"
    )
    parser.add_argument(
        "--no-progress", action="store_true",
        help="Disable progress bar (show before/after comparison)"
    )
    parser.add_argument(
        "--method", default="cosine", choices=["sequence", "jaccard", "cosine"],
        help="Similarity method (default: cosine)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Progress Bar Demo for Long-Running Analytics (FDA-61 / FE-006)")
    print("=" * 70)
    print()
    print(f"Generating {args.devices} synthetic devices...")

    section_data = generate_synthetic_section_data(args.devices)
    total_pairs = (args.devices * (args.devices - 1)) // 2

    print(f"Devices: {args.devices}")
    print(f"Total pairs to compute: {total_pairs}")
    print(f"Similarity method: {args.method}")
    print()

    if args.no_progress:
        print("=" * 70)
        print("WITHOUT Progress Bar:")
        print("=" * 70)
        print("Computing similarity matrix...")
        start_time = time.time()

        result = pairwise_similarity_matrix(
            section_data,
            "clinical_testing",
            method=args.method,
            use_cache=False,
            progress_callback=None,  # No progress
        )

        elapsed = time.time() - start_time
        print(f"Done! Computed {result['pairs_computed']} pairs in {elapsed:.2f}s")
        print()
        print("User experience: Blank terminal for the entire duration!")
        print()

    else:
        print("=" * 70)
        print("WITH Progress Bar:")
        print("=" * 70)

        # Create progress bar
        progress_bar = ProgressBar(
            total=total_pairs,
            description="Computing similarity matrix...",
            width=30
        )

        def progress_callback(current: int, total: int, message: str):
            progress_bar.update(current, message)

        start_time = time.time()

        result = pairwise_similarity_matrix(
            section_data,
            "clinical_testing",
            method=args.method,
            use_cache=False,
            progress_callback=progress_callback,
        )

        progress_bar.finish()
        elapsed = time.time() - start_time

        print(f"Done! Computed {result['pairs_computed']} pairs in {elapsed:.2f}s")
        print()
        print("User experience: Live progress updates with ETA!")
        print()

    # Display results summary
    print("=" * 70)
    print("Results Summary:")
    print("=" * 70)
    stats = result["statistics"]
    print(f"Mean similarity:   {stats['mean']:.4f}")
    print(f"Median similarity: {stats['median']:.4f}")
    print(f"Std deviation:     {stats['stdev']:.4f}")
    print(f"Min similarity:    {stats['min']:.4f}")
    print(f"Max similarity:    {stats['max']:.4f}")
    print()

    most = result["most_similar_pair"]
    least = result["least_similar_pair"]
    print(f"Most similar pair:  {most['devices'][0]} & {most['devices'][1]} (score: {most['score']:.4f})")
    print(f"Least similar pair: {least['devices'][0]} & {least['devices'][1]} (score: {least['score']:.4f})")
    print()

    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
