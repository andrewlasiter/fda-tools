---
description: Smart predicate recommendations using FDA-compliant confidence scoring and TF-IDF similarity matching
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
argument-hint: "[--project PROJECT_NAME] [--top-n N] [--output-dir PATH]"
---

# Smart Predicate Recommendations Command

Generate AI-powered predicate recommendations using FDA-compliant confidence scoring combined with TF-IDF text similarity analysis.

## Overview

This command ranks predicates using:
- **Base scoring:** FDA-compliant confidence-scoring.md algorithm (100 pts)
- **TF-IDF enhancement:** Indications and technology text similarity (+8 pts)
- **Risk assessment:** Recalls, MAUDE events, age, web validation flags
- **Strength classification:** STRONG/GOOD/MODERATE/WEAK/POOR/REJECT

## Usage

```bash
/fda-tools:smart-predicates [--project PROJECT_NAME] [--top-n N] [--output-dir PATH]
```

### Arguments

- `--project` - Project name (defaults to current project)
- `--top-n` - Number of top predicates to return (default: 10)
- `--output-dir` - Output directory for reports (defaults to project directory)

### Examples

```bash
# Rank predicates for current project
/fda-tools:smart-predicates

# Get top 5 predicates for specific project
/fda-tools:smart-predicates --project cardiovascular-stent --top-n 5

# Custom output location
/fda-tools:smart-predicates --output-dir ~/reports/
```

## How It Works

### Step 1: Load Predicates
Loads accepted predicates from review.json or enriched CSV

### Step 2: Calculate Confidence Score
Uses FDA-compliant confidence-scoring.md algorithm:
- Section context (40 pts) - SE section vs reference
- Citation frequency (20 pts) - How widely cited
- Product code match (15 pts) - Same 3-letter code
- Recency (15 pts) - Clearance age
- Regulatory history (10 pts) - Clean vs recalled

### Step 3: TF-IDF Text Similarity
Calculates text similarity between subject device and each predicate:
- **IFU similarity:** Compares indications for use text (+0-5 pts)
- **Technology similarity:** Compares technological characteristics (+0-3 pts)

### Step 4: Risk Flag Assessment
Identifies regulatory concerns:
- RECALLED - Any recalls on record
- HIGH_MAUDE - >100 adverse events
- OLD - >15 years old
- WEB_VALIDATION_RED/YELLOW - Critical enforcement issues

### Step 5: Rank & Classify
Sorts by total score and classifies strength:
- **STRONG (85-120):** Excellent predicates - recommend as primary
- **GOOD (70-84):** Solid predicates - safe to use
- **MODERATE (55-69):** Viable - review concerns first
- **WEAK (40-54):** Marginal - consider alternatives
- **POOR/REJECT (0-39):** Low confidence - do not use

## Output Files

**smart_recommendations_report.md** (Human-readable)
- Executive summary with predicate counts
- Top N predicates with detailed breakdowns
- Score components, risk flags, recommendations
- Human review checkpoints

**smart_recommendations_data.json** (Machine-readable)
- Structured ranking data
- Full score breakdowns
- Risk flag details
- Metadata for audit trail

## Scoring Example

```
Rank 1: K234567 (STRONG - 96 pts)
├─ Base confidence: 88/100
│  ├─ Section context: 40 (SE section)
│  ├─ Citation frequency: 20 (5+ sources)
│  ├─ Product code match: 15 (exact match)
│  ├─ Recency: 10 (7 years old)
│  └─ Regulatory history: 10 (clean)
├─ IFU similarity: +5 (92% match)
└─ Tech similarity: +3 (85% match)
Total: 96/108 pts
Recommendation: Excellent predicate - recommend as primary
```

## Important Notes

### ⚠️ Human Review Required

This automation **assists** predicate selection but does NOT replace RA professional judgment:

**YOU must:**
- Review actual 510(k) summaries for Rank 1-3 predicates
- Validate indications match YOUR specific device
- Compare technological characteristics in detail
- Assess risk flag relevance to YOUR submission
- Make final predicate selection decisions

### Confidence vs. Suitability

High confidence score means the device **is** a predicate (it was cited for SE).
It does NOT guarantee the predicate is **suitable** for YOUR device.

Always verify:
- IFU compatibility with your intended use
- Technology similarity to your design
- Risk flags don't apply to your comparison
- Predicate is still legally marketed

### FDA Compliance

This system implements FDA's 2014 SE guidance criteria:
- Legally marketed (binary gate)
- 510(k) pathway (binary gate)
- Same intended use (25% scoring weight)
- Same/similar technology (bonus scoring)
- No Class I recalls (binary gate)

Citations: 21 CFR 807.92, FDA SE Guidance (2014) Section IV.B

---

## Implementation

Let me implement this command:

```python
import sys
import json
from pathlib import Path

# Parse arguments
args = sys.argv[1:]
project_name = None
top_n = 10
output_dir = None

i = 0
while i < len(args):
    if args[i] == '--project' and i + 1 < len(args):
        project_name = args[i + 1]
        i += 2
    elif args[i] == '--top-n' and i + 1 < len(args):
        top_n = int(args[i + 1])
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
print("  Smart Predicate Recommendations - Phase 4B")
print(f"  Project: {project_dir.name}")
print("━" * 60)
print("")

# Import predicate ranker (add lib to path)
lib_path = Path(__file__).parent.parent / 'lib'
sys.path.insert(0, str(lib_path))

from predicate_ranker import (
    PredicateRanker,
    generate_smart_recommendations_report
)

# Step 1: Initialize ranker
print("🔍 Step 1/4: Loading predicates...")
ranker = PredicateRanker(str(project_dir))

if not ranker.enriched_predicates:
    print("❌ Error: No predicates found")
    print("   Run /fda:propose or /fda:research first to identify predicates")
    sys.exit(1)

print(f"   Found {len(ranker.enriched_predicates)} predicate(s)")
print("")

# Step 2: Rank predicates
print(f"📊 Step 2/4: Ranking top {top_n} predicates...")
ranked = ranker.rank_predicates(top_n=top_n, min_confidence=40)

if not ranked:
    print("⚠️  No predicates met minimum confidence threshold (40 pts)")
    print("   Consider running /fda:research to find more predicates")
    sys.exit(0)

print(f"   Ranked {len(ranked)} predicate(s)")
print("")

# Display top 3 summary
print("🏆 Top 3 Predicates:")
for i, pred in enumerate(ranked[:3], 1):
    strength_icon = {
        'STRONG': '⭐',
        'GOOD': '✓',
        'MODERATE': '○'
    }.get(pred['strength'], '•')

    print(f"   {i}. {strength_icon} {pred['k_number']} - {pred['device_name'][:50]}")
    print(f"      Score: {pred['total_score']}/108 ({pred['strength']})")
    if pred['risk_flags']:
        print(f"      Flags: {', '.join(pred['risk_flags'][:2])}")
print("")

# Step 3: Generate report
print("📝 Step 3/4: Generating smart recommendations report...")
report = generate_smart_recommendations_report(ranked, project_dir.name)
report_path = output_path / 'smart_recommendations_report.md'
with open(report_path, 'w') as f:
    f.write(report)
print(f"   ✅ Report saved: {report_path}")
print("")

# Step 4: Write JSON data
print("💾 Step 4/4: Writing machine-readable data...")
json_path = output_path / 'smart_recommendations_data.json'
json_data = {
    'ranked_predicates': ranked,
    'metadata': {
        'version': 'Phase 4B - Predicate Ranker v1.0',
        'generated_at': ranker.device_profile.get('timestamp', ''),
        'project': project_dir.name,
        'top_n': top_n
    }
}

with open(json_path, 'w') as f:
    json.dump(json_data, f, indent=2)
print(f"   ✅ Data saved: {json_path}")
print("")

# Summary
print("━" * 60)
print("  Smart Recommendations Complete")
print("━" * 60)
print("")

strong_count = len([p for p in ranked if p['strength'] == 'STRONG'])
if strong_count > 0:
    print(f"✅ {strong_count} STRONG predicate(s) identified")
    print(f"   Recommend reviewing Rank 1-3 actual 510(k) summaries")
else:
    good_count = len([p for p in ranked if p['strength'] == 'GOOD'])
    if good_count > 0:
        print(f"✓ {good_count} GOOD predicate(s) available")
        print(f"   Review details in report before selecting")
    else:
        print("⚠️  No STRONG/GOOD predicates found")
        print("   Manual predicate research recommended")

print("")
print("📄 Review full report:")
print(f"   {report_path}")
print("")
print("⚠️  IMPORTANT - Human Review Required:")
print("   - Review actual 510(k) summaries for top 3 predicates")
print("   - Validate indications match YOUR device")
print("   - Check risk flags and assess relevance")
print("   - Make final predicate selection decision")
print("")
```

This command is now ready for use!
