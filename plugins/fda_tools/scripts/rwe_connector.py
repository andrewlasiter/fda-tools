#!/usr/bin/env python3
"""
RWE Connector -- CLI for Real World Evidence integration support.

Provides command-line access to RWE data source management,
quality assessment, and submission template generation.

Usage:
    python3 rwe_connector.py --assess-quality --source-name "Epic EHR" --source-type ehr
    python3 rwe_connector.py --recommend --submission-type 510k
    python3 rwe_connector.py --template --submission-type 510k --device-name "DeviceX" --question "Is device safe?"
    python3 rwe_connector.py --template --submission-type pma --device-name "DeviceY" --question "Effective?"
    python3 rwe_connector.py --list-sources
    python3 rwe_connector.py --list-methods
"""

import argparse
import json
import os
import sys

# Import from lib
from rwe_integration import (
    RWEDataSourceConnector,
    RWDQualityAssessor,
    RWESubmissionTemplate,
    RWD_SOURCE_TYPES,
    RWD_QUALITY_DIMENSIONS,
    RWE_ANALYTICAL_METHODS,
)


def cmd_assess_quality(args):
    """Assess quality of an RWD source."""
    assessor = RWDQualityAssessor()

    # Build dimension scores from arguments if provided
    dimension_scores = {}
    if args.relevance_score is not None:
        dimension_scores["relevance"] = {
            sub: args.relevance_score
            for sub in RWD_QUALITY_DIMENSIONS["relevance"]["sub_criteria"]
        }
    if args.reliability_score is not None:
        dimension_scores["reliability"] = {
            sub: args.reliability_score
            for sub in RWD_QUALITY_DIMENSIONS["reliability"]["sub_criteria"]
        }
    if args.completeness_score is not None:
        dimension_scores["completeness"] = {
            sub: args.completeness_score
            for sub in RWD_QUALITY_DIMENSIONS["completeness"]["sub_criteria"]
        }

    result = assessor.assess_source(
        args.source_name,
        args.source_type,
        dimension_scores if dimension_scores else None,
    )

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(assessor.to_markdown(result))


def cmd_recommend(args):
    """Recommend RWD sources for a submission type."""
    connector = RWEDataSourceConnector()
    recs = connector.recommend_sources(
        submission_type=args.submission_type,
        device_type=args.device_type,
        is_rare_disease=args.rare_disease,
    )

    if args.format == "json":
        print(json.dumps(recs, indent=2))
    else:
        print(f"Recommended RWD Sources for {args.submission_type.upper()} Submission")
        print("=" * 60)
        for rec in recs:
            source_def = RWD_SOURCE_TYPES.get(rec["source_type"], {})
            print(f"\n  [{rec['priority']}] {source_def.get('name', rec['source_type'])}")
            print(f"  Rationale: {rec['rationale']}")


def cmd_template(args):
    """Generate RWE submission template."""
    gen = RWESubmissionTemplate(args.submission_type)
    template = gen.generate(
        args.device_name,
        args.question,
        study_design=args.study_design,
        analytical_method=args.method,
    )

    if args.format == "json":
        print(json.dumps(template, indent=2))
    else:
        print(gen.to_markdown(template))


def cmd_list_sources(args):
    """List all supported RWD source types."""
    if args.format == "json":
        print(json.dumps(RWD_SOURCE_TYPES, indent=2))
    else:
        print("Supported Real-World Data Source Types")
        print("=" * 50)
        for source_id, source_def in RWD_SOURCE_TYPES.items():
            print(f"\n  {source_id}: {source_def['name']}")
            print(f"  {source_def['description']}")
            print(f"  FDA Recognized: {'Yes' if source_def['fda_recognized'] else 'No'}")
            print(f"  Typical Quality: {source_def['typical_quality']}")


def cmd_list_methods(args):
    """List all FDA-accepted analytical methods."""
    if args.format == "json":
        print(json.dumps(RWE_ANALYTICAL_METHODS, indent=2))
    else:
        print("FDA-Accepted Analytical Methods for RWE")
        print("=" * 50)
        for method in RWE_ANALYTICAL_METHODS:
            accepted = "FDA Accepted" if method["fda_accepted"] else "Not Accepted"
            print(f"\n  {method['method']} ({accepted})")
            print(f"  {method['description']}")
            print(f"  Best for: {', '.join(method['best_for'])}")


def main():
    parser = argparse.ArgumentParser(
        description="FDA Real World Evidence Integration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Mode selection
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--assess-quality", action="store_true", help="Assess RWD source quality")
    mode.add_argument("--recommend", action="store_true", help="Recommend RWD sources")
    mode.add_argument("--template", action="store_true", help="Generate RWE submission template")
    mode.add_argument("--list-sources", action="store_true", help="List supported RWD source types")
    mode.add_argument("--list-methods", action="store_true", help="List FDA-accepted analytical methods")

    # Common options
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")

    # Quality assessment options
    parser.add_argument("--source-name", help="Name of the data source")
    parser.add_argument("--source-type", choices=list(RWD_SOURCE_TYPES.keys()), help="Type of data source")
    parser.add_argument("--relevance-score", type=int, choices=range(0, 6), help="Relevance score (0-5)")
    parser.add_argument("--reliability-score", type=int, choices=range(0, 6), help="Reliability score (0-5)")
    parser.add_argument("--completeness-score", type=int, choices=range(0, 6), help="Completeness score (0-5)")

    # Recommendation options
    parser.add_argument("--submission-type", choices=["510k", "pma", "hde", "de_novo"], help="Submission type")
    parser.add_argument("--device-type", help="Device type (e.g., implant, diagnostic)")
    parser.add_argument("--rare-disease", action="store_true", help="Device targets a rare disease")

    # Template options
    parser.add_argument("--device-name", help="Device name")
    parser.add_argument("--question", help="Regulatory question RWE addresses")
    parser.add_argument("--study-design", help="Study design description")
    parser.add_argument("--method", help="Primary analytical method")

    args = parser.parse_args()

    if args.assess_quality:
        if not args.source_name or not args.source_type:
            parser.error("--assess-quality requires --source-name and --source-type")
        cmd_assess_quality(args)
    elif args.recommend:
        if not args.submission_type:
            parser.error("--recommend requires --submission-type")
        cmd_recommend(args)
    elif args.template:
        if not args.submission_type or not args.device_name or not args.question:
            parser.error("--template requires --submission-type, --device-name, and --question")
        cmd_template(args)
    elif args.list_sources:
        cmd_list_sources(args)
    elif args.list_methods:
        cmd_list_methods(args)


if __name__ == "__main__":
    main()
