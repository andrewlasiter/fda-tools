#!/usr/bin/env python3
"""
Compliance Disclaimer Module for FDA Tools CLI Scripts.

Provides a shared compliance disclaimer that MUST be displayed at runtime
before any research-use-only functionality executes. This addresses the
requirement that users are clearly informed about the limitations of
auto-generated outputs before relying on them.

FDA Regulatory Basis:
    - 21 CFR Part 11: Electronic records/signatures must include clear
      attribution and context regarding their intended use.
    - The disclaimer ensures no auto-generated standards data is
      mistakenly treated as validated for direct FDA submission.

Usage:
    from compliance_disclaimer import show_disclaimer

    # In main() before any processing:
    show_disclaimer("standards-generator", accept_flag=args.accept_disclaimer)
"""

import os
import sys
from datetime import datetime, timezone

# Disclaimer text constant -- single source of truth
DISCLAIMER_TEXT = """
================================================================================
  RESEARCH USE ONLY -- NOT FOR DIRECT FDA SUBMISSION
================================================================================

  This tool generates standards and regulatory data using automated analysis
  of FDA databases. The output has NOT been independently verified by a
  qualified Regulatory Affairs (RA) professional and MUST NOT be used
  directly in FDA submissions without expert review.

  Limitations:
    - Standards mappings are auto-generated from historical 510(k) data
    - Confidence scores are statistical estimates, not regulatory judgments
    - FDA Recognized Consensus Standards change periodically
    - Device-specific applicability requires expert RA assessment

  Required Before Submission Use:
    1. Independent verification by qualified RA professional
    2. Cross-reference against current FDA Recognized Consensus Standards
    3. Device-specific applicability assessment per 21 CFR 860 / 807

  By proceeding, you acknowledge this tool is for RESEARCH and PLANNING
  purposes only.
================================================================================
"""

DISCLAIMER_SHORT = (
    "[RESEARCH USE ONLY] Output not validated for direct FDA submission. "
    "See --help for details."
)


def show_disclaimer(tool_name, accept_flag=False, quiet=False):
    """Display the compliance disclaimer and optionally require acceptance.

    This function MUST be called at the start of any CLI script that
    produces research-use-only output (e.g., standards generators,
    ML-based predictors, auto-generated regulatory content).

    Args:
        tool_name: Identifier for the calling tool (used in audit log).
        accept_flag: If True, the user has passed --accept-disclaimer on
            the CLI and the interactive prompt is skipped.
        quiet: If True, show only the short disclaimer (for piped output).

    Returns:
        True if the user accepted (or accept_flag was set).

    Raises:
        SystemExit: If the user declines the disclaimer in interactive mode.
    """
    if quiet:
        print(DISCLAIMER_SHORT, file=sys.stderr)
        _log_disclaimer_event(tool_name, "accepted_quiet")
        return True

    print(DISCLAIMER_TEXT, file=sys.stderr)

    if accept_flag:
        print("  [--accept-disclaimer flag set: proceeding automatically]",
              file=sys.stderr)
        _log_disclaimer_event(tool_name, "accepted_flag")
        return True

    # Interactive mode: require explicit acceptance if stdin is a TTY
    if sys.stdin.isatty():
        try:
            response = input("  Do you acknowledge this disclaimer? [y/N]: ")
            if response.strip().lower() in ("y", "yes"):
                _log_disclaimer_event(tool_name, "accepted_interactive")
                return True
            else:
                print("\n  Disclaimer not accepted. Exiting.", file=sys.stderr)
                _log_disclaimer_event(tool_name, "declined_interactive")
                sys.exit(1)
        except (EOFError, KeyboardInterrupt):
            print("\n  Interrupted. Exiting.", file=sys.stderr)
            _log_disclaimer_event(tool_name, "interrupted")
            sys.exit(1)
    else:
        # Non-interactive (piped) without --accept-disclaimer
        print(
            "  ERROR: Non-interactive mode requires --accept-disclaimer flag.",
            file=sys.stderr,
        )
        print(
            "  Add --accept-disclaimer to acknowledge research-use-only status.",
            file=sys.stderr,
        )
        _log_disclaimer_event(tool_name, "rejected_noninteractive")
        sys.exit(1)


def add_disclaimer_args(parser):
    """Add standard disclaimer CLI arguments to an argparse parser.

    Call this in every script that uses show_disclaimer() so that the
    --accept-disclaimer flag is available.

    Args:
        parser: argparse.ArgumentParser instance to augment.
    """
    parser.add_argument(
        "--accept-disclaimer",
        action="store_true",
        default=False,
        dest="accept_disclaimer",
        help=(
            "Acknowledge that output is RESEARCH USE ONLY and not validated "
            "for direct FDA submission. Required for non-interactive use."
        ),
    )


def _log_disclaimer_event(tool_name, action):
    """Log disclaimer acceptance/rejection to the audit trail.

    Writes a JSON-lines entry to the global audit log if it exists.
    Failures are silently ignored to avoid blocking the main workflow.

    Args:
        tool_name: Name of the tool that showed the disclaimer.
        action: One of 'accepted_flag', 'accepted_interactive',
            'accepted_quiet', 'declined_interactive',
            'rejected_noninteractive', 'interrupted'.
    """
    try:
        # Determine audit log path
        log_dir = os.path.expanduser("~/fda-510k-data/logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "disclaimer_audit.jsonl")

        import json
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "action": action,
            "pid": os.getpid(),
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        # Never let audit logging failure block the tool
        pass
