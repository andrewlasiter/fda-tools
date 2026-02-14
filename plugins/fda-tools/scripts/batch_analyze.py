#!/usr/bin/env python3
"""
batch_analyze.py — Aggregate and analyze results across batch-seeded projects.

Reads pre-check reports, drafts, SE comparisons, and consistency reports
from a round directory, then produces scoreboard, deficiency taxonomy,
and cross-round comparison views.

Usage:
    python3 batch_analyze.py --round rounds/round_baseline/
    python3 batch_analyze.py --round rounds/round_baseline/ --taxonomy
    python3 batch_analyze.py --compare rounds/round_baseline/ rounds/round_fix1/
    python3 batch_analyze.py --round rounds/round_baseline/ --json
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Parsers — extract structured data from markdown reports
# ---------------------------------------------------------------------------

def parse_pre_check(report_path):
    """Parse a pre_check_report.md and extract key metrics.

    Returns dict with: sri_score, sri_max, deficiencies (list of dicts),
    rta_present, rta_total, specialists (list), estar_sections, etc.
    """
    result = {
        "exists": False,
        "sri_score": None,
        "sri_max": 100,
        "rta_present": 0,
        "rta_total": 0,
        "rta_result": "",
        "deficiencies": [],
        "specialists": [],
        "estar_sections_present": 0,
        "estar_sections_missing": 0,
    }

    if not report_path.exists():
        return result

    text = report_path.read_text(errors="replace")
    result["exists"] = True

    # SRI score: "SRI: 63/100"
    m = re.search(r"SRI:\s*(\d+)/(\d+)", text)
    if m:
        result["sri_score"] = int(m.group(1))
        result["sri_max"] = int(m.group(2))

    # RTA result: "9/11 required items present"
    m = re.search(r"RTA\s+Result:\s*(\d+)/(\d+)", text)
    if m:
        result["rta_present"] = int(m.group(1))
        result["rta_total"] = int(m.group(2))
        result["rta_result"] = f"{m.group(1)}/{m.group(2)}"

    # Deficiencies table: "| DEF-001 | CRITICAL | Admin | ..."
    for m in re.finditer(
        r"\|\s*(DEF-\d+)\s*\|\s*(CRITICAL|MAJOR|MINOR)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
        text,
    ):
        result["deficiencies"].append({
            "id": m.group(1),
            "severity": m.group(2),
            "reviewer": m.group(3).strip(),
            "finding": m.group(4).strip(),
        })

    # Specialists from "REVIEW TEAM IDENTIFIED" table
    for m in re.finditer(
        r"\|\s*(\w[\w\s/]+?)\s*\|\s*(?:Always|[A-Z][\w\s,-]+?)\s*\|",
        text,
    ):
        spec = m.group(1).strip()
        if spec not in ("Reviewer", "#", "---", ""):
            result["specialists"].append(spec)

    # eSTAR sections: count DRAFT vs MISSING in completeness table
    for m in re.finditer(r"\|\s*\d+\s*\|\s*[^|]+\|\s*(DRAFT|PRESENT|MISSING|N/A)\s*\|", text):
        status = m.group(1)
        if status in ("DRAFT", "PRESENT"):
            result["estar_sections_present"] += 1
        elif status == "MISSING":
            result["estar_sections_missing"] += 1

    return result


def parse_consistency(report_path):
    """Parse a consistency_report.md and extract check results.

    Returns dict with: checks (list of {number, name, status, details}),
    pass_count, warn_count, fail_count, skip_count.
    """
    result = {
        "exists": False,
        "checks": [],
        "pass_count": 0,
        "warn_count": 0,
        "fail_count": 0,
        "skip_count": 0,
    }

    if not report_path.exists():
        return result

    text = report_path.read_text(errors="replace")
    result["exists"] = True

    # Parse "Status: PASS=9, WARN=3, FAIL=0, SKIP=2"
    m = re.search(r"PASS=(\d+).*?WARN=(\d+).*?FAIL=(\d+).*?SKIP=(\d+)", text)
    if m:
        result["pass_count"] = int(m.group(1))
        result["warn_count"] = int(m.group(2))
        result["fail_count"] = int(m.group(3))
        result["skip_count"] = int(m.group(4))

    # Parse individual checks: "| 1  | Product Code | PASS | ..."
    for m in re.finditer(
        r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(PASS|WARN|FAIL|SKIP)\s*\|\s*([^|]*?)\s*\|",
        text,
    ):
        result["checks"].append({
            "number": int(m.group(1)),
            "name": m.group(2).strip(),
            "status": m.group(3),
            "details": m.group(4).strip(),
        })

    return result


def parse_drafts(project_dir):
    """Count drafts, words, and [TODO] items in a project.

    Looks for draft_*.md in both the project root and a drafts/ subdirectory.
    Returns dict with: draft_count, total_words, total_todos, drafts (list).
    """
    result = {
        "draft_count": 0,
        "total_words": 0,
        "total_todos": 0,
        "drafts": [],
    }

    # Collect draft files from both locations (dedup by stem)
    draft_paths = {}
    drafts_dir = project_dir / "drafts"
    if drafts_dir.exists():
        for p in drafts_dir.glob("draft_*.md"):
            draft_paths[p.stem] = p
    # Project root drafts (override if same name exists in both)
    for p in project_dir.glob("draft_*.md"):
        draft_paths[p.stem] = p

    for stem in sorted(draft_paths):
        draft_path = draft_paths[stem]
        text = draft_path.read_text(errors="replace")
        words = len(text.split())
        todos = len(re.findall(r"\[TODO", text, re.IGNORECASE))
        section_name = stem.replace("draft_", "")
        result["drafts"].append({
            "name": section_name,
            "words": words,
            "todos": todos,
        })
        result["draft_count"] += 1
        result["total_words"] += words
        result["total_todos"] += todos

    return result


def parse_se_comparison(se_path):
    """Parse se_comparison.md for row count and TODO cells.

    Returns dict with: exists, row_count, todo_cells.
    """
    result = {
        "exists": False,
        "row_count": 0,
        "todo_cells": 0,
    }

    if not se_path.exists():
        return result

    text = se_path.read_text(errors="replace")
    result["exists"] = True

    # Count table rows (lines starting with |, excluding header/separator)
    rows = [
        line for line in text.split("\n")
        if line.strip().startswith("|")
        and not re.match(r"^\s*\|[\s-]+\|", line)  # Skip separator rows
        and "Feature" not in line  # Skip header row
    ]
    result["row_count"] = len(rows)
    result["todo_cells"] = len(re.findall(r"\[TODO", text, re.IGNORECASE))

    return result


def parse_manifest(round_dir):
    """Load round_manifest.json from a round directory."""
    manifest_path = round_dir / "round_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f)
    return None


def discover_projects(round_dir):
    """Discover project directories in a round directory.

    Projects can be direct children (batch_CODE_archetype/) or listed in manifest.
    Also supports non-round directories by looking for project marker files.
    """
    projects = []
    manifest = parse_manifest(round_dir)

    if manifest and manifest.get("projects"):
        # Use manifest for project list
        for entry in manifest["projects"]:
            proj_dir = round_dir / entry["project_name"]
            if proj_dir.exists():
                projects.append({
                    "dir": proj_dir,
                    "name": entry["project_name"],
                    "archetype_id": entry.get("archetype_id", ""),
                    "product_code": entry.get("product_code", ""),
                    "panel": entry.get("panel", ""),
                    "seed_status": entry.get("seed_status", "unknown"),
                    "manifest_entry": entry,
                })
    else:
        # Discover by scanning for directories with query.json or review.json
        for child in sorted(round_dir.iterdir()):
            if child.is_dir() and (
                (child / "query.json").exists() or
                (child / "review.json").exists()
            ):
                # Try to extract product code from directory name
                name = child.name
                code_match = re.match(r"(?:batch|seed)_(?:\w+_)?(\w{2,5})_", name)
                code = code_match.group(1) if code_match else ""
                projects.append({
                    "dir": child,
                    "name": name,
                    "archetype_id": "",
                    "product_code": code,
                    "panel": "",
                    "seed_status": "unknown",
                    "manifest_entry": None,
                })

    return projects


# ---------------------------------------------------------------------------
# Analysis Views
# ---------------------------------------------------------------------------

def analyze_round(round_dir, include_taxonomy=False):
    """Analyze all projects in a round. Returns structured analysis dict."""
    projects = discover_projects(round_dir)
    if not projects:
        print(f"ERROR: No projects found in {round_dir}", file=sys.stderr)
        return None

    results = []
    all_deficiencies = []

    for proj in projects:
        pdir = proj["dir"]
        pre_check = parse_pre_check(pdir / "pre_check_report.md")
        consistency = parse_consistency(pdir / "consistency_report.md")
        drafts = parse_drafts(pdir)
        se_path = pdir / "se_comparison.md"
        if not se_path.exists():
            # Fallback: check drafts/ subdirectory
            se_path = pdir / "drafts" / "se_comparison.md"
        se = parse_se_comparison(se_path)

        entry = {
            "project_name": proj["name"],
            "archetype_id": proj["archetype_id"],
            "product_code": proj["product_code"],
            "panel": proj["panel"],
            "seed_status": proj["seed_status"],
            "pre_check": pre_check,
            "consistency": consistency,
            "drafts": drafts,
            "se_comparison": se,
        }
        results.append(entry)

        # Collect deficiencies with project context
        for d in pre_check.get("deficiencies", []):
            all_deficiencies.append({
                **d,
                "project": proj["name"],
                "product_code": proj["product_code"],
                "archetype_id": proj["archetype_id"],
            })

    analysis = {
        "round_dir": str(round_dir),
        "project_count": len(results),
        "results": results,
    }

    if include_taxonomy:
        analysis["taxonomy"] = build_deficiency_taxonomy(all_deficiencies, len(results))

    return analysis


def build_deficiency_taxonomy(deficiencies, project_count):
    """Group deficiencies into normalized patterns with frequency and severity.

    Returns list of pattern dicts sorted by priority (frequency * severity_weight).
    """
    SEVERITY_WEIGHT = {"CRITICAL": 3, "MAJOR": 2, "MINOR": 1}

    # Normalize findings into pattern keys
    patterns = defaultdict(lambda: {
        "pattern": "",
        "severity": "",
        "reviewer": "",
        "count": 0,
        "projects": set(),
        "examples": [],
        "root_cause": "",
    })

    for d in deficiencies:
        # Create a normalized pattern key from finding text
        finding = d["finding"]
        key = normalize_finding(finding)
        severity = d["severity"]

        p = patterns[key]
        p["pattern"] = key
        if not p["severity"] or SEVERITY_WEIGHT.get(severity, 0) > SEVERITY_WEIGHT.get(p["severity"], 0):
            p["severity"] = severity
        p["reviewer"] = d.get("reviewer", "")
        p["count"] += 1
        p["projects"].add(d.get("product_code", "?"))
        if len(p["examples"]) < 3:
            p["examples"].append({
                "project": d.get("project", ""),
                "finding": finding,
            })
        p["root_cause"] = guess_root_cause(key)

    # Convert sets to lists and sort by priority
    result = []
    for p in patterns.values():
        p["projects"] = sorted(p["projects"])
        p["frequency"] = f"{len(p['projects'])}/{project_count}"
        p["priority_score"] = len(p["projects"]) * SEVERITY_WEIGHT.get(p["severity"], 1)
        result.append(p)

    result.sort(key=lambda x: (-x["priority_score"], -x["count"]))
    return result


def normalize_finding(finding):
    """Normalize a deficiency finding into a pattern key."""
    finding = finding.lower().strip()

    # Map specific findings to pattern categories
    if "cover letter" in finding:
        return "Missing cover letter"
    if "truthful" in finding and "accuracy" in finding:
        return "Missing truthful & accuracy statement"
    if "ifu" in finding or "indications for use" in finding:
        return "IFU not specified (TODO placeholders)"
    if "material" in finding and ("not specified" in finding or "not listed" in finding or "todo" in finding):
        return "Materials of construction not specified"
    if "device description" in finding and ("incomplete" in finding or "todo" in finding or "placeholder" in finding):
        return "Device description incomplete (TODO placeholders)"
    if "shelf life" in finding:
        return "Shelf life section missing or incomplete"
    if "clinical" in finding and ("missing" in finding or "not drafted" in finding):
        return "Clinical evidence section not drafted"
    if "sterilization" in finding and "residual" in finding:
        return "Sterilization residual test data missing"
    if "software" in finding and "missing" in finding:
        return "Software section missing for SaMD/firmware"
    if "human factors" in finding:
        return "Human factors evaluation missing"
    if "reprocessing" in finding:
        return "Reprocessing validation missing"
    if "cybersecurity" in finding or "524b" in finding:
        return "Cybersecurity documentation missing"
    if "labeling" in finding and "missing" in finding:
        return "Labeling section missing"
    if "form 3881" in finding:
        return "Form 3881 missing"
    if "brand" in finding or "trade name" in finding:
        return "Brand/trade name mismatch"
    if "estar" in finding and "stale" in finding:
        return "Stale eSTAR data"
    if "equipment" in finding or "compatible" in finding:
        return "Compatible equipment not documented"
    if "mri" in finding:
        return "MRI safety documentation missing"
    if "emc" in finding or "electromagnetic" in finding:
        return "EMC testing documentation missing"

    # Fallback: truncate and return as-is
    return finding[:80] if len(finding) > 80 else finding


def guess_root_cause(pattern):
    """Map a deficiency pattern to its likely root cause command/file."""
    CAUSE_MAP = {
        "Missing cover letter": "draft.md (cover-letter section)",
        "Missing truthful & accuracy statement": "draft.md (truthful-accuracy section)",
        "IFU not specified (TODO placeholders)": "Company input needed (not a command gap)",
        "Materials of construction not specified": "compare-se.md / draft.md (material extraction)",
        "Device description incomplete (TODO placeholders)": "draft.md (device-description) + seed data quality",
        "Shelf life section missing or incomplete": "draft.md (shelf-life auto-trigger)",
        "Clinical evidence section not drafted": "draft.md (clinical section)",
        "Sterilization residual test data missing": "Company test data needed",
        "Software section missing for SaMD/firmware": "draft.md (software auto-trigger for SaMD)",
        "Human factors evaluation missing": "draft.md (human-factors auto-trigger)",
        "Reprocessing validation missing": "draft.md (reprocessing auto-trigger)",
        "Cybersecurity documentation missing": "draft.md (cybersecurity / Section 524B)",
        "Form 3881 missing": "assemble.md (Form 3881 generation)",
        "Brand/trade name mismatch": "draft.md Step 0.75 (brand validation)",
        "Stale eSTAR data": "assemble.md (--refresh mode)",
        "Compatible equipment not documented": "compare-se.md (equipment subsection)",
        "MRI safety documentation missing": "draft.md (mri-safety section)",
        "EMC testing documentation missing": "draft.md (electrical-safety section)",
    }
    return CAUSE_MAP.get(pattern, "Unknown — investigate")


# ---------------------------------------------------------------------------
# Display Functions
# ---------------------------------------------------------------------------

def print_scoreboard(analysis):
    """Print per-project scoreboard table."""
    results = analysis["results"]

    print(f"\n{'='*90}")
    print(f"  SCOREBOARD — {analysis['round_dir']}")
    print(f"  {analysis['project_count']} projects analyzed")
    print(f"{'='*90}\n")

    # Header
    header = (
        f"  {'Code':<6} {'Archetype':<22} {'SRI':>5} "
        f"{'Def':>4} {'Drafts':>6} {'Words':>7} {'TODOs':>6} "
        f"{'SE':>4} {'Con':>5} {'Status':<10}"
    )
    print(header)
    print(f"  {'-'*88}")

    sri_scores = []
    for r in results:
        code = r["product_code"]
        arch = r["archetype_id"][:21]
        sri = r["pre_check"].get("sri_score")
        sri_str = f"{sri}" if sri is not None else "-"
        if sri is not None:
            sri_scores.append(sri)

        defs = len(r["pre_check"].get("deficiencies", []))
        drafts = r["drafts"]["draft_count"]
        words = r["drafts"]["total_words"]
        todos = r["drafts"]["total_todos"]
        se_rows = r["se_comparison"]["row_count"] if r["se_comparison"]["exists"] else 0

        con = r["consistency"]
        if con["exists"]:
            con_str = f"{con['pass_count']}P"
            if con["warn_count"]:
                con_str += f"/{con['warn_count']}W"
            if con["fail_count"]:
                con_str += f"/{con['fail_count']}F"
        else:
            con_str = "-"

        status = r["seed_status"]

        print(
            f"  {code:<6} {arch:<22} {sri_str:>5} "
            f"{defs:>4} {drafts:>6} {words:>7,} {todos:>6} "
            f"{se_rows:>4} {con_str:>5} {status:<10}"
        )

    # Summary row
    if sri_scores:
        avg_sri = sum(sri_scores) / len(sri_scores)
        min_sri = min(sri_scores)
        max_sri = max(sri_scores)
        print(f"\n  SRI: avg={avg_sri:.0f}, min={min_sri}, max={max_sri} (n={len(sri_scores)})")

    total_defs = sum(
        len(r["pre_check"].get("deficiencies", []))
        for r in results
    )
    crit = sum(
        1 for r in results
        for d in r["pre_check"].get("deficiencies", [])
        if d["severity"] == "CRITICAL"
    )
    major = sum(
        1 for r in results
        for d in r["pre_check"].get("deficiencies", [])
        if d["severity"] == "MAJOR"
    )
    minor = sum(
        1 for r in results
        for d in r["pre_check"].get("deficiencies", [])
        if d["severity"] == "MINOR"
    )
    print(f"  Deficiencies: {total_defs} total ({crit} CRITICAL, {major} MAJOR, {minor} MINOR)")
    print()


def print_taxonomy(taxonomy, project_count):
    """Print deficiency taxonomy with frequency and root causes."""
    print(f"\n{'='*90}")
    print(f"  DEFICIENCY TAXONOMY")
    print(f"{'='*90}\n")

    if not taxonomy:
        print("  No deficiencies found.")
        return

    print(f"  {'#':<4} {'Pattern':<45} {'Sev':<9} {'Freq':<7} {'Pri':>4} {'Root Cause'}")
    print(f"  {'-'*3:<4} {'-'*44:<45} {'-'*8:<9} {'-'*6:<7} {'-'*3:>4} {'-'*30}")

    for i, p in enumerate(taxonomy, 1):
        pattern = p["pattern"][:44]
        severity = p["severity"]
        freq = p["frequency"]
        pri = p["priority_score"]
        cause = p["root_cause"][:40]

        print(f"  {i:<4} {pattern:<45} {severity:<9} {freq:<7} {pri:>4} {cause}")

    # Expanded details for top patterns
    print(f"\n  TOP PATTERNS (detail):")
    for i, p in enumerate(taxonomy[:5], 1):
        print(f"\n  {i}. {p['pattern']}")
        print(f"     Severity: {p['severity']} | Frequency: {p['frequency']} | Priority: {p['priority_score']}")
        print(f"     Root cause: {p['root_cause']}")
        print(f"     Affected codes: {', '.join(p['projects'])}")
        if p["examples"]:
            print(f"     Example: {p['examples'][0]['finding'][:100]}")
    print()


def print_comparison(analysis_before, analysis_after):
    """Print cross-round comparison."""
    print(f"\n{'='*90}")
    print(f"  CROSS-ROUND COMPARISON")
    print(f"  Before: {analysis_before['round_dir']}")
    print(f"  After:  {analysis_after['round_dir']}")
    print(f"{'='*90}\n")

    # Build code->result maps
    before_map = {r["product_code"]: r for r in analysis_before["results"]}
    after_map = {r["product_code"]: r for r in analysis_after["results"]}

    all_codes = sorted(set(list(before_map.keys()) + list(after_map.keys())))

    # SRI comparison
    print(f"  {'Code':<6} {'Archetype':<22} {'SRI Before':>10} {'SRI After':>10} {'Delta':>7} {'Def Before':>10} {'Def After':>10}")
    print(f"  {'-'*5:<6} {'-'*21:<22} {'-'*9:>10} {'-'*9:>10} {'-'*6:>7} {'-'*9:>10} {'-'*9:>10}")

    improved = 0
    regressed = 0
    unchanged = 0

    for code in all_codes:
        b = before_map.get(code)
        a = after_map.get(code)

        arch = (a or b or {}).get("archetype_id", "?")[:21]

        sri_b = b["pre_check"].get("sri_score") if b else None
        sri_a = a["pre_check"].get("sri_score") if a else None

        sri_b_str = str(sri_b) if sri_b is not None else "-"
        sri_a_str = str(sri_a) if sri_a is not None else "-"

        if sri_b is not None and sri_a is not None:
            delta = sri_a - sri_b
            if delta > 0:
                delta_str = f"+{delta}"
                improved += 1
            elif delta < 0:
                delta_str = str(delta)
                regressed += 1
            else:
                delta_str = "0"
                unchanged += 1
        else:
            delta_str = "?"

        def_b = len(b["pre_check"].get("deficiencies", [])) if b else 0
        def_a = len(a["pre_check"].get("deficiencies", [])) if a else 0

        print(
            f"  {code:<6} {arch:<22} {sri_b_str:>10} {sri_a_str:>10} {delta_str:>7} "
            f"{def_b:>10} {def_a:>10}"
        )

    print(f"\n  Improved: {improved}, Regressed: {regressed}, Unchanged: {unchanged}")

    # Pattern-level comparison
    tax_before = analysis_before.get("taxonomy", [])
    tax_after = analysis_after.get("taxonomy", [])

    before_patterns = {p["pattern"] for p in tax_before}
    after_patterns = {p["pattern"] for p in tax_after}

    resolved = before_patterns - after_patterns
    new_patterns = after_patterns - before_patterns
    persistent = before_patterns & after_patterns

    if resolved:
        print(f"\n  RESOLVED patterns ({len(resolved)}):")
        for p in sorted(resolved):
            print(f"    [FIXED] {p}")

    if new_patterns:
        print(f"\n  NEW patterns ({len(new_patterns)}):")
        for p in sorted(new_patterns):
            print(f"    [NEW] {p}")

    if persistent:
        print(f"\n  PERSISTENT patterns ({len(persistent)}):")
        for p in sorted(persistent):
            # Check if frequency changed
            freq_b = next((t["count"] for t in tax_before if t["pattern"] == p), 0)
            freq_a = next((t["count"] for t in tax_after if t["pattern"] == p), 0)
            delta = freq_a - freq_b
            indicator = f" (count: {freq_b} -> {freq_a})" if delta != 0 else ""
            print(f"    [STILL] {p}{indicator}")

    print()


# ---------------------------------------------------------------------------
# JSON Output
# ---------------------------------------------------------------------------

def write_analysis_json(analysis, output_path):
    """Write analysis results as JSON for programmatic consumption."""
    # Clean up non-serializable types
    clean = json.loads(json.dumps(analysis, default=str))
    with open(output_path, "w") as f:
        json.dump(clean, f, indent=2)
        f.write("\n")
    print(f"  JSON output: {output_path}")


# ---------------------------------------------------------------------------
# Update Manifest
# ---------------------------------------------------------------------------

def update_manifest_with_results(round_dir, analysis):
    """Update round_manifest.json with pipeline results from analysis."""
    manifest_path = round_dir / "round_manifest.json"
    if not manifest_path.exists():
        return

    with open(manifest_path) as f:
        manifest = json.load(f)

    # Build result map
    result_map = {r["project_name"]: r for r in analysis["results"]}

    for proj in manifest.get("projects", []):
        name = proj.get("project_name", "")
        if name in result_map:
            r = result_map[name]
            proj["pipeline_results"] = {
                "sri_score": r["pre_check"].get("sri_score"),
                "deficiency_count": len(r["pre_check"].get("deficiencies", [])),
                "draft_count": r["drafts"]["draft_count"],
                "total_words": r["drafts"]["total_words"],
                "total_todos": r["drafts"]["total_todos"],
                "se_rows": r["se_comparison"]["row_count"],
                "consistency_pass": r["consistency"]["pass_count"],
                "consistency_warn": r["consistency"]["warn_count"],
                "consistency_fail": r["consistency"]["fail_count"],
            }

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(f"  Updated manifest: {manifest_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Analyze batch-seeded FDA 510(k) test project results.",
    )

    parser.add_argument("--round", metavar="DIR",
                        help="Round directory to analyze")
    parser.add_argument("--compare", metavar="DIR", nargs=2,
                        help="Compare two round directories (before after)")
    parser.add_argument("--taxonomy", action="store_true",
                        help="Include deficiency taxonomy in output")
    parser.add_argument("--json", action="store_true",
                        help="Write analysis as JSON file")
    parser.add_argument("--update-manifest", action="store_true",
                        help="Update round_manifest.json with pipeline results")

    args = parser.parse_args()

    if not args.round and not args.compare:
        parser.error("Either --round or --compare is required")

    if args.compare:
        dir_before = Path(args.compare[0])
        dir_after = Path(args.compare[1])

        if not dir_before.exists():
            print(f"ERROR: {dir_before} not found", file=sys.stderr)
            sys.exit(1)
        if not dir_after.exists():
            print(f"ERROR: {dir_after} not found", file=sys.stderr)
            sys.exit(1)

        analysis_before = analyze_round(dir_before, include_taxonomy=True)
        analysis_after = analyze_round(dir_after, include_taxonomy=True)

        if not analysis_before or not analysis_after:
            sys.exit(1)

        print_scoreboard(analysis_before)
        print_scoreboard(analysis_after)
        print_comparison(analysis_before, analysis_after)

    elif args.round:
        round_dir = Path(args.round)
        if not round_dir.exists():
            print(f"ERROR: {round_dir} not found", file=sys.stderr)
            sys.exit(1)

        analysis = analyze_round(round_dir, include_taxonomy=args.taxonomy)
        if not analysis:
            sys.exit(1)

        print_scoreboard(analysis)

        if args.taxonomy and analysis.get("taxonomy"):
            print_taxonomy(analysis["taxonomy"], analysis["project_count"])

        if args.json:
            json_path = round_dir / "analysis.json"
            write_analysis_json(analysis, json_path)

        if args.update_manifest:
            update_manifest_with_results(round_dir, analysis)


if __name__ == "__main__":
    main()
