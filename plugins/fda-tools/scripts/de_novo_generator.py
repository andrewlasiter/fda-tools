#!/usr/bin/env python3
"""
De Novo Generator -- CLI for De Novo classification request support.

Provides command-line access to De Novo submission outline generation,
special controls proposals, risk assessment, benefit-risk analysis,
pathway decision trees, and predicate search documentation.

Usage:
    python3 de_novo_generator.py --outline --device-name "SmartPulse CM-200"
    python3 de_novo_generator.py --decision-tree --predicate-exists false --novel-technology true
    python3 de_novo_generator.py --special-controls --device-name "SmartPulse"
    python3 de_novo_generator.py --risk-assessment --device-name "SmartPulse"
    python3 de_novo_generator.py --predicate-search --device-name "SmartPulse"
"""

import argparse
import json
import os
import sys

# Import from lib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from de_novo_support import (
    DeNovoSubmissionOutline,
    SpecialControlsProposal,
    DeNovoRiskAssessment,
    BenefitRiskAnalysis,
    PathwayDecisionTree,
    PredicateSearchDocumentation,
    DE_NOVO_SUBMISSION_SECTIONS,
    DECISION_FACTORS,
)


def str_to_bool(v):
    """Convert string to boolean."""
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    raise argparse.ArgumentTypeError(f"Boolean value expected, got: {v}")


def cmd_outline(args):
    """Generate De Novo submission outline."""
    device_info = {}
    if args.device_name:
        device_info["device_name"] = args.device_name
    if args.trade_name:
        device_info["trade_name"] = args.trade_name
    if args.manufacturer:
        device_info["manufacturer"] = args.manufacturer
    if args.intended_use:
        device_info["intended_use"] = args.intended_use
    if args.proposed_class:
        device_info["proposed_class"] = args.proposed_class

    device_info["has_software"] = args.has_software
    device_info["is_electrical"] = args.is_electrical
    device_info["is_sterile"] = args.is_sterile
    device_info["has_biocompat_concern"] = not args.no_biocompat

    outline = DeNovoSubmissionOutline(device_info)

    if args.format == "json":
        result = outline.generate()
        print(json.dumps(result, indent=2))
    else:
        print(outline.to_markdown())


def cmd_decision_tree(args):
    """Evaluate De Novo vs 510(k) pathway."""
    tree = PathwayDecisionTree()

    answers = {}
    if args.predicate_exists is not None:
        answers["predicate_exists"] = args.predicate_exists
    if args.same_intended_use is not None:
        answers["same_intended_use"] = args.same_intended_use
    if args.novel_technology is not None:
        answers["novel_technology"] = args.novel_technology
    if args.different_safety_questions is not None:
        answers["different_questions_of_safety"] = args.different_safety_questions
    if args.low_moderate_risk is not None:
        answers["low_to_moderate_risk"] = args.low_moderate_risk

    context = {}
    if args.device_name:
        context["device_name"] = args.device_name

    result = tree.evaluate(answers, context)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"Regulatory Pathway Decision Analysis")
        print(f"=" * 50)
        print(f"\n  Recommendation: {result['recommendation']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  510(k) Score: {result['scores']['510k_score']}%")
        print(f"  De Novo Score: {result['scores']['de_novo_score']}%")
        print(f"\n  Factor Analysis:")
        for factor in result["factor_analysis"]:
            print(f"    - {factor['question']}: {factor['answer']}")
        print(f"\n  Next Steps:")
        for step in result["next_steps"]:
            print(f"    1. {step}")


def cmd_special_controls(args):
    """Generate special controls proposal template."""
    proposal = SpecialControlsProposal()

    # Generate with empty risks/controls as template
    template = proposal.generate(args.device_name or "Unknown Device", [], [])

    if args.format == "json":
        print(json.dumps(template, indent=2))
    else:
        print(proposal.to_markdown(template))


def cmd_risk_assessment(args):
    """Generate risk assessment framework."""
    assessment = DeNovoRiskAssessment()

    # Add example risks if requested
    if args.include_examples:
        assessment.add_risk("R-001", "Device mechanical failure", "device_related",
                           severity=4, probability=2, detectability=3)
        assessment.add_risk("R-002", "Software malfunction", "device_related",
                           severity=3, probability=3, detectability=2)
        assessment.add_risk("R-003", "User interpretation error", "use_related",
                           severity=3, probability=3, detectability=4)
        assessment.add_risk("R-004", "Skin irritation from contact", "device_related",
                           severity=2, probability=3, detectability=1)
        assessment.add_risk("R-005", "False positive diagnosis", "indirect",
                           severity=3, probability=3, detectability=3)

    if args.format == "json":
        print(json.dumps(assessment.get_assessment_summary(), indent=2))
    else:
        print(assessment.to_markdown())


def cmd_predicate_search(args):
    """Generate predicate search documentation template."""
    doc = PredicateSearchDocumentation(args.device_name or "Unknown Device")

    # Add recommended search strategies
    doc.add_search_strategy(
        "FDA 510(k) Premarket Notification Database",
        [args.device_name or "device"] + (args.search_terms or []),
    )
    doc.add_search_strategy(
        "FDA PMA Database",
        [args.device_name or "device"] + (args.search_terms or []),
    )
    doc.add_search_strategy(
        "FDA De Novo Database",
        [args.device_name or "device"] + (args.search_terms or []),
    )
    doc.add_search_strategy(
        "FDA Product Classification Database",
        [args.device_name or "device"] + (args.search_terms or []),
    )

    if args.format == "json":
        print(json.dumps(doc.generate_documentation(), indent=2))
    else:
        print(doc.to_markdown())


def main():
    parser = argparse.ArgumentParser(
        description="FDA De Novo Classification Request Support Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Mode selection
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--outline", action="store_true", help="Generate De Novo submission outline")
    mode.add_argument("--decision-tree", action="store_true", help="Evaluate De Novo vs 510(k)")
    mode.add_argument("--special-controls", action="store_true", help="Generate special controls template")
    mode.add_argument("--risk-assessment", action="store_true", help="Generate risk assessment framework")
    mode.add_argument("--predicate-search", action="store_true", help="Generate predicate search documentation")

    # Common options
    parser.add_argument("--device-name", help="Device name")
    parser.add_argument("--trade-name", help="Device trade name")
    parser.add_argument("--manufacturer", help="Manufacturer name")
    parser.add_argument("--intended-use", help="Device intended use")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")

    # De Novo-specific options
    parser.add_argument("--proposed-class", choices=["I", "II"], default="II", help="Proposed device class")
    parser.add_argument("--has-software", action="store_true", help="Device contains software")
    parser.add_argument("--is-electrical", action="store_true", help="Device is electrical/electronic")
    parser.add_argument("--is-sterile", action="store_true", help="Device is provided sterile")
    parser.add_argument("--no-biocompat", action="store_true", help="No biocompatibility concerns")

    # Decision tree options
    parser.add_argument("--predicate-exists", type=str_to_bool, default=None, help="Does a predicate exist? (true/false)")
    parser.add_argument("--same-intended-use", type=str_to_bool, default=None, help="Same intended use as existing? (true/false)")
    parser.add_argument("--novel-technology", type=str_to_bool, default=None, help="Novel technology? (true/false)")
    parser.add_argument("--different-safety-questions", type=str_to_bool, default=None, help="Different safety questions? (true/false)")
    parser.add_argument("--low-moderate-risk", type=str_to_bool, default=None, help="Low-to-moderate risk? (true/false)")

    # Risk/search options
    parser.add_argument("--include-examples", action="store_true", help="Include example risks")
    parser.add_argument("--search-terms", nargs="+", help="Additional predicate search terms")

    args = parser.parse_args()

    if args.outline:
        cmd_outline(args)
    elif args.decision_tree:
        cmd_decision_tree(args)
    elif args.special_controls:
        cmd_special_controls(args)
    elif args.risk_assessment:
        cmd_risk_assessment(args)
    elif args.predicate_search:
        cmd_predicate_search(args)


if __name__ == "__main__":
    main()
