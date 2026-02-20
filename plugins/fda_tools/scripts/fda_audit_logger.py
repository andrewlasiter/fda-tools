#!/usr/bin/env python3
"""
FDA Decision Audit Logger — Zero-Trust Audit Trail.

Standalone CLI that commands call via bash to append structured decision entries
to $PROJECT_DIR/audit_log.jsonl. Every autonomous decision documents what was
chosen, what alternatives were considered, why each was excluded, and what data
informed the decision.

Usage:
    # Append a decision entry
    python3 fda_audit_logger.py --project NAME --command review \
      --action predicate_accepted --subject K241335 \
      --decision accepted --confidence 85 --mode full-auto \
      --rationale "Score 85/100, same product code, 3 SE citations" \
      --data-sources "output.csv,openFDA 510k API" \
      --alternatives '["K241335","K222222"]' \
      --exclusions '{"K222222":"Different product code (KGN), score 35"}' \
      --metadata '{"score_breakdown":{"section_context":40}}'

    # Query the log
    python3 fda_audit_logger.py --project NAME --show-log \
      [--command CMD] [--action TYPE] [--subject K#] \
      [--after DATE] [--before DATE] [--decisions-only] \
      [--exclusions-only] [--limit N]

    # Summary statistics
    python3 fda_audit_logger.py --project NAME --summary

    # Pipeline consolidation
    python3 fda_audit_logger.py --project NAME --consolidate
"""

import argparse
import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ── Valid action types (must match references/audit-logging.md) ──

VALID_ACTIONS = {
    # Review
    "predicate_accepted", "predicate_rejected", "predicate_deferred",
    "predicate_reclassified", "review_completed",
    # Pipeline
    "pipeline_started", "step_started", "step_completed", "step_failed",
    "step_skipped", "step_degraded", "pipeline_completed", "pipeline_halted",
    # Pre-Sub / Outline
    "placeholder_resolved", "placeholder_converted", "data_synthesized",
    "document_generated", "qsub_type_recommended",
    "testing_gap_identified", "section_applicability_determined",
    # Compare-SE
    "predicate_inferred", "table_generated", "cell_auto_populated",
    "template_selected", "comparison_decision",
    # Safety
    "safety_query_completed", "safety_data_unavailable",
    "risk_level_assigned", "peer_benchmark_completed",
    # Extract
    "extraction_started", "extraction_completed",
    # Pathway (v5.20.0)
    "pathway_recommended", "pathway_alternative_excluded",
    # Guidance (v5.20.0)
    "guidance_matched", "guidance_excluded", "guidance_trigger_fired",
    # Test-Plan (v5.20.0)
    "test_prioritized", "test_excluded",
    # Draft (v5.20.0)
    "section_drafted", "content_decision",
    # Consistency (v5.20.0)
    "check_passed", "check_failed", "check_warned",
    # Pre-Check (v5.20.0)
    "deficiency_identified", "rta_screening_completed", "sri_calculated",
    "pre_check_started", "review_team_identified", "pre_check_report_generated",
    "readiness_sri_calculated",
    # Propose (v5.20.0)
    "predicate_proposed", "predicate_validation_result",
    # Research (v5.22.0)
    "predicate_ranked", "report_generated",
    # Agent (v5.20.0)
    "agent_step_started", "agent_step_completed", "agent_decision",
}

VALID_DECISION_TYPES = {"auto", "manual", "deferred"}

try:
    from version import PLUGIN_VERSION
except Exception:
    PLUGIN_VERSION = "5.22.0"


def get_projects_dir():
    """Determine the projects directory from settings or default."""
    settings_path = os.path.expanduser("~/.claude/fda-tools.local.md")
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            m = re.search(r"projects_dir:\s*(.+)", f.read())
            if m:
                return os.path.expanduser(m.group(1).strip())
    return os.path.expanduser("~/fda-510k-data/projects")


def get_log_path(project_dir):
    """Get the audit log file path for a project."""
    return os.path.join(project_dir, "audit_log.jsonl")


def validate_entry(entry):
    """Validate a log entry has required fields and valid action type."""
    errors = []
    for field in ("timestamp", "command", "version", "action"):
        if field not in entry or not entry[field]:
            errors.append(f"Missing required field: {field}")
    if entry.get("action") and entry["action"] not in VALID_ACTIONS:
        errors.append(f"Invalid action type: {entry['action']}. "
                       f"Valid actions: {sorted(VALID_ACTIONS)}")
    if entry.get("decision_type") and entry["decision_type"] not in VALID_DECISION_TYPES:
        errors.append(f"Invalid decision_type: {entry['decision_type']}. "
                       f"Valid types: {sorted(VALID_DECISION_TYPES)}")
    if entry.get("confidence_score") is not None:
        try:
            score = float(entry["confidence_score"])
            if score < 0 or score > 100:
                errors.append(f"confidence_score must be 0-100, got {score}")
        except (ValueError, TypeError):
            errors.append(f"confidence_score must be numeric, got {entry['confidence_score']}")
    return errors


def append_entry(project_dir, entry):
    """Validate and append a single audit entry to the project's audit log.

    Returns (entry_id, errors). If errors is non-empty, entry was not written.
    """
    # Auto-populate defaults
    entry.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    entry.setdefault("version", PLUGIN_VERSION)
    entry_id = str(uuid.uuid4())[:8]
    entry["entry_id"] = entry_id

    # Cross-command linking (v5.22.0)
    # parent_entry_id and related_entries are optional — pass through if present
    if "parent_entry_id" in entry and not entry["parent_entry_id"]:
        del entry["parent_entry_id"]
    if "related_entries" in entry and not entry["related_entries"]:
        del entry["related_entries"]

    errors = validate_entry(entry)
    if errors:
        return entry_id, errors

    os.makedirs(project_dir, exist_ok=True)
    log_path = get_log_path(project_dir)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry_id, []


def read_log(project_dir):
    """Read all entries from the audit log."""
    log_path = get_log_path(project_dir)
    entries = []
    if not os.path.exists(log_path):
        return entries
    with open(log_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Malformed entry at line %d", line_num)
    return entries


def query_log(project_dir, filters):
    """Read and filter the audit log."""
    entries = read_log(project_dir)
    filtered = []

    for entry in entries:
        if filters.get("command") and entry.get("command") != filters["command"]:
            continue
        if filters.get("action") and entry.get("action") != filters["action"]:
            continue
        if filters.get("subject") and entry.get("subject") != filters["subject"]:
            continue
        if filters.get("after"):
            ts = entry.get("timestamp", "")
            if ts < filters["after"]:
                continue
        if filters.get("before"):
            ts = entry.get("timestamp", "")
            if ts > filters["before"]:
                continue
        if filters.get("decisions_only"):
            if not entry.get("decision"):
                continue
        if filters.get("exclusions_only"):
            if not entry.get("exclusion_records"):
                continue
        filtered.append(entry)

    limit = filters.get("limit")
    if limit:
        filtered = filtered[-limit:]

    return filtered


def summarize_log(project_dir):
    """Generate summary statistics from the audit log."""
    entries = read_log(project_dir)
    if not entries:
        return {
            "total_entries": 0,
            "commands": {},
            "decision_types": {"auto": 0, "manual": 0, "deferred": 0},
            "exclusions_documented": 0,
            "date_range": {"earliest": None, "latest": None},
        }

    commands = {}
    decision_types = {"auto": 0, "manual": 0, "deferred": 0}
    exclusions = 0
    timestamps = []

    for entry in entries:
        cmd = entry.get("command", "unknown")
        commands[cmd] = commands.get(cmd, 0) + 1

        dt = entry.get("decision_type")
        if dt in decision_types:
            decision_types[dt] += 1

        if entry.get("exclusion_records"):
            exclusions += len(entry["exclusion_records"])

        ts = entry.get("timestamp")
        if ts:
            timestamps.append(ts)

    timestamps.sort()

    return {
        "total_entries": len(entries),
        "commands": commands,
        "decision_types": decision_types,
        "exclusions_documented": exclusions,
        "date_range": {
            "earliest": timestamps[0] if timestamps else None,
            "latest": timestamps[-1] if timestamps else None,
        },
    }


def consolidate_pipeline(project_dir, project_name):
    """Write a pipeline_audit.json from the audit log entries."""
    entries = read_log(project_dir)
    if not entries:
        print("NO_ENTRIES:audit_log.jsonl is empty or missing")
        return

    # Find pipeline start/end
    started = None
    completed = None
    steps = {}
    total_decisions = 0
    auto_decisions = 0
    manual_decisions = 0
    warnings = []
    files_generated = set()

    for entry in entries:
        action = entry.get("action", "")
        if action == "pipeline_started":
            started = entry.get("timestamp")
        elif action == "pipeline_completed":
            completed = entry.get("timestamp")
        elif action.startswith("step_"):
            step_name = entry.get("subject", "unknown")
            status = action.replace("step_", "")
            steps[step_name] = {
                "status": status,
                "duration_ms": entry.get("duration_ms"),
            }
            if entry.get("metadata"):
                steps[step_name].update(entry["metadata"])

        if entry.get("decision"):
            total_decisions += 1
            if entry.get("decision_type") == "auto":
                auto_decisions += 1
            elif entry.get("decision_type") == "manual":
                manual_decisions += 1

        if entry.get("warnings"):
            warnings.extend(entry["warnings"])

        if entry.get("files_written"):
            files_generated.update(entry["files_written"])

    # Calculate duration
    duration_seconds = None
    if started and completed:
        try:
            t1 = datetime.fromisoformat(started)
            t2 = datetime.fromisoformat(completed)
            duration_seconds = int((t2 - t1).total_seconds())
        except (ValueError, TypeError) as e:
            logger.warning("Could not calculate pipeline duration: %s", e)

    consolidated = {
        "pipeline_version": PLUGIN_VERSION,
        "project": project_name,
        "started_at": started,
        "completed_at": completed,
        "duration_seconds": duration_seconds,
        "steps": steps,
        "total_decisions": total_decisions,
        "auto_decisions": auto_decisions,
        "manual_decisions": manual_decisions,
        "warnings": list(set(warnings)),
        "files_generated": sorted(files_generated),
    }

    output_path = os.path.join(project_dir, "pipeline_audit.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(consolidated, f, indent=2)

    print(f"CONSOLIDATED:{output_path}")
    print(f"TOTAL_ENTRIES:{len(entries)}")
    print(f"TOTAL_DECISIONS:{total_decisions}")
    print(f"AUTO_DECISIONS:{auto_decisions}")
    print(f"MANUAL_DECISIONS:{manual_decisions}")


def print_query_results(entries):
    """Print query results in KEY:VALUE format."""
    print(f"TOTAL_RESULTS:{len(entries)}")
    print("---")
    for entry in entries:
        ts = entry.get("timestamp", "?")[:19]
        cmd = entry.get("command", "?")
        action = entry.get("action", "?")
        subject = entry.get("subject", "")
        decision = entry.get("decision", "")
        confidence = entry.get("confidence_score", "")

        print(f"[{ts}] {cmd} > {action}")
        if subject:
            print(f"  Subject: {subject}", end="")
            if confidence:
                print(f" | Confidence: {confidence}", end="")
            if entry.get("decision_type"):
                print(f" | Mode: {entry['decision_type']}", end="")
            print()
        if decision:
            rationale = entry.get("rationale", "")[:200]
            print(f"  Chosen: {decision} — \"{rationale}\"")

        for excl in entry.get("exclusion_records", []):
            subj = excl.get("subject") or excl.get("device") or excl.get("pathway") or "?"
            reason = excl.get("reason", "?")[:150]
            print(f"  Excluded: {subj} — \"{reason}\"")

        sources = entry.get("data_sources", [])
        if sources:
            print(f"  Sources: {', '.join(sources)}")

        # Cross-command links (v5.22.0)
        if entry.get("parent_entry_id"):
            print(f"  Parent: {entry['parent_entry_id']}")
        if entry.get("related_entries"):
            print(f"  Related: {', '.join(entry['related_entries'])}")

        print()


def print_summary(summary):
    """Print summary statistics in KEY:VALUE format."""
    print(f"TOTAL_ENTRIES:{summary['total_entries']}")

    dr = summary.get("date_range", {})
    if dr.get("earliest"):
        print(f"DATE_RANGE:{dr['earliest'][:10]} to {dr['latest'][:10]}")

    print("---")
    print("COMMANDS:")
    for cmd, count in sorted(summary["commands"].items(), key=lambda x: -x[1]):
        print(f"  {cmd}: {count}")

    dt = summary["decision_types"]
    print(f"DECISIONS:auto={dt['auto']},manual={dt['manual']},deferred={dt['deferred']}")
    print(f"EXCLUSIONS_DOCUMENTED:{summary['exclusions_documented']}")


# ── CLI ──

def handle_append(args):
    """Handle the append subcommand."""
    projects_dir = get_projects_dir()
    project_dir = os.path.join(projects_dir, args.project)

    entry = {
        "command": args.command,
        "action": args.action,
        "mode": args.mode or "interactive",
    }

    if args.subject:
        entry["subject"] = args.subject
    if args.decision:
        entry["decision"] = args.decision
    if args.confidence is not None:
        entry["confidence_score"] = args.confidence
    if args.rationale:
        entry["rationale"] = args.rationale
    if args.data_sources:
        entry["data_sources"] = [s.strip() for s in args.data_sources.split(",")]
    if args.decision_type:
        entry["decision_type"] = args.decision_type

    # Parse JSON arguments
    if args.alternatives:
        try:
            entry["alternatives_considered"] = json.loads(args.alternatives)
        except json.JSONDecodeError:
            entry["alternatives_considered"] = [s.strip() for s in args.alternatives.split(",")]

    if args.exclusions:
        try:
            raw = json.loads(args.exclusions)
            if isinstance(raw, dict):
                entry["exclusion_records"] = [
                    {"subject": k, "reason": v} for k, v in raw.items()
                ]
            elif isinstance(raw, list):
                entry["exclusion_records"] = raw
        except json.JSONDecodeError:
            logger.warning("Could not parse --exclusions as JSON")

    if args.metadata:
        try:
            meta = json.loads(args.metadata)
            if isinstance(meta, dict):
                # Promote score_breakdown to top-level
                if "score_breakdown" in meta:
                    entry["score_breakdown"] = meta.pop("score_breakdown")
                if meta:
                    entry["metadata"] = meta
        except json.JSONDecodeError:
            logger.warning("Could not parse --metadata as JSON")

    if args.files_read:
        entry["files_read"] = [s.strip() for s in args.files_read.split(",")]
    if args.files_written:
        entry["files_written"] = [s.strip() for s in args.files_written.split(",")]

    # Cross-command linking (v5.22.0)
    if args.parent_entry_id:
        entry["parent_entry_id"] = args.parent_entry_id
    if args.related_entries:
        entry["related_entries"] = [s.strip() for s in args.related_entries.split(",")]

    entry_id, errors = append_entry(project_dir, entry)

    if errors:
        for err in errors:
            print(f"AUDIT_ERROR:{err}")
        sys.exit(1)

    print(f"AUDIT_STATUS:OK")
    print(f"AUDIT_ENTRY_ID:{entry_id}")


def handle_query(args):
    """Handle the --show-log subcommand."""
    projects_dir = get_projects_dir()
    project_dir = os.path.join(projects_dir, args.project)

    filters = {}
    if args.command_filter:
        filters["command"] = args.command_filter
    if args.action_filter:
        filters["action"] = args.action_filter
    if args.subject_filter:
        filters["subject"] = args.subject_filter
    if args.after:
        filters["after"] = args.after
    if args.before:
        filters["before"] = args.before
    if args.decisions_only:
        filters["decisions_only"] = True
    if args.exclusions_only:
        filters["exclusions_only"] = True
    if args.limit:
        filters["limit"] = args.limit

    entries = query_log(project_dir, filters)
    print_query_results(entries)


def handle_summary(args):
    """Handle the --summary subcommand."""
    projects_dir = get_projects_dir()
    project_dir = os.path.join(projects_dir, args.project)
    summary = summarize_log(project_dir)
    print_summary(summary)


def handle_consolidate(args):
    """Handle the --consolidate subcommand."""
    projects_dir = get_projects_dir()
    project_dir = os.path.join(projects_dir, args.project)
    consolidate_pipeline(project_dir, args.project)


def main():
    parser = argparse.ArgumentParser(
        description="FDA Decision Audit Logger — Zero-Trust Audit Trail"
    )
    parser.add_argument("--project", required=True, help="Project name")

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--show-log", action="store_true", dest="show_log",
                            help="Query and display the audit log")
    mode_group.add_argument("--summary", action="store_true",
                            help="Show summary statistics")
    mode_group.add_argument("--consolidate", action="store_true",
                            help="Write pipeline_audit.json from audit log")

    # Append fields (used when not --show-log, --summary, or --consolidate)
    parser.add_argument("--command", help="Command name (e.g., review, pathway)")
    parser.add_argument("--action", help="Action type (e.g., predicate_accepted)")
    parser.add_argument("--subject", help="Entity acted upon (K-number, product code)")
    parser.add_argument("--decision", help="Decision made (accepted, rejected, etc.)")
    parser.add_argument("--confidence", type=float, help="Confidence score (0-100)")
    parser.add_argument("--mode", help="Mode (full-auto, auto, interactive, pipeline)")
    parser.add_argument("--rationale", help="Human-readable rationale")
    parser.add_argument("--data-sources", dest="data_sources",
                        help="Comma-separated data sources")
    parser.add_argument("--decision-type", dest="decision_type",
                        help="Decision type: auto, manual, deferred")
    parser.add_argument("--alternatives", help="JSON array of alternatives considered")
    parser.add_argument("--exclusions", help="JSON object/array of exclusion records")
    parser.add_argument("--metadata", help="JSON object of additional metadata")
    parser.add_argument("--files-read", dest="files_read",
                        help="Comma-separated input files")
    parser.add_argument("--files-written", dest="files_written",
                        help="Comma-separated output files")
    # Cross-command linking (v5.22.0)
    parser.add_argument("--parent-entry-id", dest="parent_entry_id",
                        help="Entry ID of parent decision (cross-command linking)")
    parser.add_argument("--related-entries", dest="related_entries",
                        help="Comma-separated entry IDs of related decisions")

    # Query filters (used with --show-log)
    parser.add_argument("--command-filter", dest="command_filter",
                        help="Filter by command name")
    parser.add_argument("--action-filter", dest="action_filter",
                        help="Filter by action type")
    parser.add_argument("--subject-filter", dest="subject_filter",
                        help="Filter by subject")
    parser.add_argument("--after", help="Filter entries after this ISO date")
    parser.add_argument("--before", help="Filter entries before this ISO date")
    parser.add_argument("--decisions-only", action="store_true", dest="decisions_only",
                        help="Show only entries with decisions")
    parser.add_argument("--exclusions-only", action="store_true", dest="exclusions_only",
                        help="Show only entries with exclusion records")
    parser.add_argument("--limit", type=int, help="Limit number of results")

    args = parser.parse_args()

    if args.show_log:
        handle_query(args)
    elif args.summary:
        handle_summary(args)
    elif args.consolidate:
        handle_consolidate(args)
    elif args.command and args.action:
        handle_append(args)
    else:
        parser.error("Specify --command and --action to append, "
                      "or --show-log, --summary, --consolidate to query")


if __name__ == "__main__":
    main()
