#!/usr/bin/env python3
"""
HDE Submission Generator -- CLI for Humanitarian Device Exemption support.

Provides command-line access to HDE submission outline generation,
prevalence validation, probable benefit analysis, IRB tracking,
and annual distribution report generation.

Usage:
    python3 hde_generator.py --outline --device-name "OrphanStent VG-100"
    python3 hde_generator.py --validate-prevalence --condition "Takayasu Arteritis" --prevalence 3000
    python3 hde_generator.py --probable-benefit --device-name "OrphanStent" --condition "Takayasu Arteritis"
    python3 hde_generator.py --irb-summary
    python3 hde_generator.py --annual-report --hde-number H250001 --period-start 2025-01-01 --period-end 2025-12-31
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Import from lib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from hde_support import (  # type: ignore
    HDESubmissionOutline,
    PrevalenceValidator,
    ProbableBenefitAnalyzer,
    IRBApprovalTracker,
    AnnualDistributionReport,
    HDE_PREVALENCE_THRESHOLD,
)


def cmd_outline(args):
    """Generate HDE submission outline."""
    device_info = {}
    if args.device_name:
        device_info["device_name"] = args.device_name
    if args.trade_name:
        device_info["trade_name"] = args.trade_name
    if args.manufacturer:
        device_info["manufacturer"] = args.manufacturer
    if args.condition:
        device_info["disease_condition"] = args.condition
    if args.intended_use:
        device_info["intended_use"] = args.intended_use
    if args.hud_number:
        device_info["hud_designation_number"] = args.hud_number

    device_info["has_software"] = args.has_software
    device_info["has_biocompat_concern"] = not args.no_biocompat

    outline = HDESubmissionOutline(device_info)

    if args.format == "json":
        result = outline.generate()
        print(json.dumps(result, indent=2))
    else:
        print(outline.to_markdown())


def cmd_validate_prevalence(args):
    """Validate disease prevalence for HDE eligibility."""
    validator = PrevalenceValidator()

    sources = []
    if args.sources:
        for s in args.sources:
            sources.append({"name": s, "url": "", "date": ""})

    result = validator.validate_prevalence(
        args.condition,
        args.prevalence,
        sources,
        args.year,
    )

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        status = "ELIGIBLE" if result["eligible"] else "INELIGIBLE"
        print(f"Prevalence Validation: {args.condition}")
        print(f"  Estimated: {args.prevalence:,} patients/year")
        print(f"  Threshold: {HDE_PREVALENCE_THRESHOLD:,} patients/year")
        print(f"  Status: {status}")
        print(f"  Margin: {result['margin']:,} ({result['margin_percentage']}%)")
        print(f"  Data Quality Score: {result['data_quality_score']}/100")
        if result["warnings"]:
            print("\n  Warnings:")
            for w in result["warnings"]:
                print(f"    - {w}")
        if result["recommendations"]:
            print("\n  Recommendations:")
            for r in result["recommendations"]:
                print(f"    - {r}")


def cmd_probable_benefit(args):
    """Generate probable benefit analysis template."""
    analyzer = ProbableBenefitAnalyzer()
    template = analyzer.generate_template(
        args.device_name or "Unknown Device",
        args.condition or "Unknown Condition",
    )

    if args.format == "json":
        print(json.dumps(template, indent=2))
    else:
        print(analyzer.to_markdown(template))


def cmd_annual_report(args):
    """Generate annual distribution report."""
    report = AnnualDistributionReport(
        args.hde_number or "H000000",
        args.device_name or "Unknown Device",
        args.manufacturer or "Unknown Company",
    )

    result = report.generate_report(
        args.period_start or "2025-01-01",
        args.period_end or "2025-12-31",
        devices_distributed=args.devices_distributed or 0,
    )

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(report.to_markdown())


def main():
    parser = argparse.ArgumentParser(
        description="FDA HDE Submission Support Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Mode selection
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--outline", action="store_true", help="Generate HDE submission outline")
    mode.add_argument("--validate-prevalence", action="store_true", help="Validate disease prevalence")
    mode.add_argument("--probable-benefit", action="store_true", help="Generate probable benefit template")
    mode.add_argument("--annual-report", action="store_true", help="Generate annual distribution report")

    # Common options
    parser.add_argument("--device-name", help="Device name")
    parser.add_argument("--trade-name", help="Device trade name")
    parser.add_argument("--manufacturer", help="Manufacturer name")
    parser.add_argument("--condition", help="Disease/condition name")
    parser.add_argument("--intended-use", help="Device intended use")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")

    # Prevalence options
    parser.add_argument("--prevalence", type=int, help="Estimated prevalence (patients/year)")
    parser.add_argument("--year", type=int, help="Year of prevalence data")
    parser.add_argument("--sources", nargs="+", help="Data source names")

    # HDE-specific options
    parser.add_argument("--hud-number", help="HUD designation number")
    parser.add_argument("--hde-number", help="HDE number")
    parser.add_argument("--has-software", action="store_true", help="Device contains software")
    parser.add_argument("--no-biocompat", action="store_true", help="No biocompatibility concerns")

    # Annual report options
    parser.add_argument("--period-start", help="Reporting period start (YYYY-MM-DD)")
    parser.add_argument("--period-end", help="Reporting period end (YYYY-MM-DD)")
    parser.add_argument("--devices-distributed", type=int, help="Number of devices distributed")

    args = parser.parse_args()

    if args.outline:
        cmd_outline(args)
    elif args.validate_prevalence:
        if not args.condition or args.prevalence is None:
            parser.error("--validate-prevalence requires --condition and --prevalence")
        cmd_validate_prevalence(args)
    elif args.probable_benefit:
        cmd_probable_benefit(args)
    elif args.annual_report:
        cmd_annual_report(args)


if __name__ == "__main__":
    main()
