---
description: Automated gap analysis for 510(k) submissions - identifies missing data, weak predicates, and testing gaps
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
argument-hint: "[--project PROJECT_NAME] [--output-dir PATH]"
---

# Automated Gap Analysis Command

Run automated gap analysis to identify missing device data, weak predicates, testing gaps, and standards gaps in your 510(k) project.

## Overview

This command analyzes your project files and generates:
- **Gap Analysis Report** (markdown) - Human-readable findings with priorities
- **Gap Data** (JSON) - Machine-readable gap data for automation
- **Updated Metadata** - Enrichment metadata with gap analysis results

## Usage

```bash
/fda-predicate-assistant:auto-gap-analysis [--project PROJECT_NAME] [--output-dir PATH]
```

### Arguments

- `--project` - Project name (defaults to current project)
- `--output-dir` - Output directory for reports (defaults to project directory)

### Examples

```bash
# Analyze current project
/fda-predicate-assistant:auto-gap-analysis

# Analyze specific project
/fda-predicate-assistant:auto-gap-analysis --project cardiovascular-stent

# Custom output location
/fda-predicate-assistant:auto-gap-analysis --output-dir ~/reports/
```

## What Gets Analyzed

**1. Missing Device Data** (device_profile.json)
- HIGH priority: Indications, technological characteristics, materials, product code
- MEDIUM priority: Sterilization, shelf life, intended user, power source
- LOW priority: Accessories, packaging, storage conditions

**2. Weak Predicates** (review.json)
- HIGH priority: ≥2 recalls on record
- MEDIUM priority: >15 years old, ≥5 SE differences

**3. Testing Gaps** (standards_lookup.json vs device_profile.json)
- Expected standards not declared
- Missing test documentation

**4. Standards Gaps** (FDA Recognition Database)
- Applicable standards not referenced

## Confidence Scoring

Gap analysis includes confidence score (0-100) based on:
- **Data completeness (40%)**: How complete is device_profile.json
- **Predicate quality (30%)**: Recall history, age of predicates
- **Gap clarity (20%)**: How definitive are detected gaps
- **Cross-validation (10%)**: Agreement between detection methods

**Confidence Levels:**
- **HIGH (≥90%)**: Comprehensive and reliable analysis
- **MEDIUM (70-89%)**: Generally reliable, validate HIGH priority gaps
- **LOW (<70%)**: May be incomplete, MANUAL REVIEW REQUIRED

## Output Files

**gap_analysis_report.md** (Human-readable)
- Executive summary with confidence
- Gaps organized by category
- Priority-ordered recommended actions
- Human review checkpoints

**gap_analysis_data.json** (Machine-readable)
- Structured gap data for automation
- Full confidence breakdown
- Metadata for audit trail

**enrichment_metadata.json** (Updated)
- Gap analysis timestamp and results
- Confidence score and level
- Human review requirement flag

---

## Implementation

Step 1: Parse arguments and determine project directory
Step 2: Run gap analysis using gap_analyzer.py
Step 3: Calculate confidence score
Step 4: Generate markdown report
Step 5: Write JSON data
Step 6: Update enrichment metadata
Step 7: Display summary to user

Let me implement this command:

```python
import sys
import json
from pathlib import Path

# Parse arguments
args = sys.argv[1:]
project_name = None
output_dir = None

i = 0
while i < len(args):
    if args[i] == '--project' and i + 1 < len(args):
        project_name = args[i + 1]
        i += 2
    elif args[i] == '--output-dir' and i + 1 < len(args):
        output_dir = args[i + 1]
        i += 2
    else:
        i += 1

# Determine project directory
if project_name:
    projects_dir = Path.home() / 'fda-510k-data' / 'projects'
    project_dir = projects_dir / project_name
else:
    # Use current project from environment
    import os
    project_dir = Path(os.environ.get('PROJECT_DIR', '.'))

if not project_dir.exists():
    print(f"❌ Error: Project directory not found: {project_dir}")
    sys.exit(1)

# Set output directory
if output_dir:
    output_path = Path(output_dir)
else:
    output_path = project_dir

output_path.mkdir(parents=True, exist_ok=True)

print("━" * 60)
print("  Automated Gap Analysis - Phase 4")
print(f"  Project: {project_dir.name}")
print("━" * 60)
print("")

# Import gap analyzer (add lib to path)
lib_path = Path(__file__).parent.parent / 'lib'
sys.path.insert(0, str(lib_path))

from gap_analyzer import (
    GapAnalyzer,
    calculate_gap_analysis_confidence,
    generate_gap_analysis_report,
    write_gap_data_json,
    update_enrichment_metadata
)

# Step 1: Run gap analysis
print("🔍 Step 1/5: Analyzing project files...")
analyzer = GapAnalyzer(str(project_dir))
gap_results = analyzer.analyze_all_gaps()

summary = gap_results.get('summary', {})
print(f"   Found {summary.get('total_gaps', 0)} gaps:")
print(f"   - CRITICAL: {summary.get('critical', 0)}")
print(f"   - HIGH: {summary.get('high_priority', 0)}")
print(f"   - MEDIUM: {summary.get('medium_priority', 0)}")
print(f"   - LOW: {summary.get('low_priority', 0)}")
print("")

# Step 2: Calculate confidence
print("📊 Step 2/5: Calculating confidence score...")
confidence = calculate_gap_analysis_confidence(gap_results, analyzer.device_profile)
conf_score = confidence.get('confidence_score', 0)
conf_level = confidence.get('confidence_level', 'UNKNOWN')
print(f"   Confidence: {conf_score}% ({conf_level})")
print(f"   {confidence.get('interpretation', '')}")
print("")

# Step 3: Generate markdown report
print("📝 Step 3/5: Generating gap analysis report...")
report = generate_gap_analysis_report(gap_results, confidence, project_dir.name)
report_path = output_path / 'gap_analysis_report.md'
with open(report_path, 'w') as f:
    f.write(report)
print(f"   ✅ Report saved: {report_path}")
print("")

# Step 4: Write JSON data
print("💾 Step 4/5: Writing machine-readable gap data...")
json_path = output_path / 'gap_analysis_data.json'
write_gap_data_json(gap_results, confidence, str(json_path))
print(f"   ✅ Data saved: {json_path}")
print("")

# Step 5: Update enrichment metadata
print("🔄 Step 5/5: Updating enrichment metadata...")
update_enrichment_metadata(str(project_dir), gap_results, confidence)
metadata_path = project_dir / 'enrichment_metadata.json'
print(f"   ✅ Metadata updated: {metadata_path}")
print("")

# Display summary
print("━" * 60)
print("  Gap Analysis Complete")
print("━" * 60)
print("")

if conf_level == 'LOW':
    print("⚠️  WARNING: Low confidence analysis")
    print("   MANUAL REVIEW REQUIRED before proceeding")
    print("")

if summary.get('critical', 0) > 0 or summary.get('high_priority', 0) > 0:
    print("🔴 CRITICAL/HIGH Priority Gaps Detected:")
    print(f"   {summary.get('critical', 0) + summary.get('high_priority', 0)} gaps require immediate attention")
    print(f"   See {report_path} for details")
    print("")

print("📄 Review full report:")
print(f"   {report_path}")
print("")
print("✅ Next steps:")
print("   1. Review gap_analysis_report.md")
print("   2. Address CRITICAL and HIGH priority gaps")
print("   3. Check human review checkboxes")
print("   4. Re-run analysis after addressing gaps")
print("")
```

This command is now ready for use!
