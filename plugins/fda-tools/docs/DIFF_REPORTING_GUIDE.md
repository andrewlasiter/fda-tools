# Fingerprint Diff Reporting - User Guide

## Overview

The fingerprint diff reporting feature automatically detects and reports field-level changes in existing FDA 510(k) clearances. This helps you track:

- **Decision date corrections** (FDA backdating)
- **Applicant name changes** (company acquisitions/mergers)
- **Device name updates** (version changes, typo corrections)
- **Regulatory reclassifications** (rare but important)

## Quick Start

### Enable Diff Reporting

Add the `--diff-report` flag to your change detection command:

```bash
python3 change_detector.py --project my_project --diff-report
```

### Check the Report

After running, find the generated markdown report:

```bash
cat ~/fda-510k-data/projects/my_project/field_changes_report.md
```

## CLI Options

### Basic Usage

```bash
# Detect changes with diff reporting
python3 change_detector.py --project my_project --diff-report
```

### JSON Output

Get structured JSON output with field change counts:

```bash
python3 change_detector.py --project my_project --diff-report --json
```

Example JSON output:
```json
{
  "project": "my_project",
  "status": "completed",
  "total_new_clearances": 2,
  "total_new_recalls": 0,
  "total_field_changes": 3,
  "changes": [
    {
      "product_code": "DQY",
      "change_type": "field_changes",
      "count": 3,
      "details": {
        "devices_affected": 2
      }
    }
  ]
}
```

### Automated Pipeline

Combine with `--trigger` to automatically process new clearances:

```bash
python3 change_detector.py --project my_project --diff-report --trigger
```

### Quiet Mode

Minimal output for scripting:

```bash
python3 change_detector.py --project my_project --diff-report --quiet
```

## Understanding the Report

### Report Structure

```markdown
# FDA Field-Level Change Report

**Product Code:** DQY
**Detection Time:** 2026-02-17T10:00:00+00:00
**Changes Detected:** 3

## Summary

Field changes detected across 2 device(s).

### Changes by Field Type

- **applicant**: 2 change(s)
- **decision_date**: 1 change(s)

## Detailed Changes

### K241001

| Field | Before | After |
|-------|--------|-------|
| applicant | OldCorp Inc | NewCorp LLC |
| decision_date | 20240315 | 20240320 |

### K241002

| Field | Before | After |
|-------|--------|-------|
| applicant | BioTech Co | MegaCorp Global |
```

### Monitored Fields

The system monitors these 6 fields for changes:

1. **device_name** - Official device name
2. **applicant** - Company/organization name
3. **decision_date** - FDA clearance decision date (YYYYMMDD)
4. **decision_code** - Clearance decision code (e.g., SESE)
5. **clearance_type** - Type of 510(k) submission
6. **product_code** - FDA product classification code

### Interpreting Changes

#### Decision Date Changes
```
Field: decision_date
Before: 20240315
After: 20240301
```

**Meaning:** FDA corrected the decision date, backdating the clearance by 14 days.

**Action:** Update internal records, check if timeline impacts competitive analysis.

#### Applicant Name Changes
```
Field: applicant
Before: StartupMed Inc
After: BigPharma Global LLC
```

**Meaning:** Company acquisition or merger. StartupMed was acquired by BigPharma.

**Action:** Update competitive intelligence, review predicate device ownership.

#### Device Name Changes
```
Field: device_name
Before: Cardiac Monitor System
After: Cardiac Monitor System v2.0
```

**Meaning:** Device version update or FDA correction of device name.

**Action:** Verify if new version impacts substantial equivalence comparisons.

## Console Output

When diff reporting is enabled, console output includes field change information:

```
============================================================
Smart Change Detection Results
============================================================
Project: cardiovascular_devices
Product codes checked: 1
New clearances found: 2
New recalls found: 0
Field changes detected: 3

Changes Detected:
----------------------------------------
  DQY: new_clearances (2 new)
    - K261001: Advanced Catheter System (20260215)
    - K261002: Vascular Access Device (20260220)

  DQY: field_changes (3 new)
    Devices affected: 2
    - K241001: applicant changed
      'OldMedTech Corp' -> 'NewMedTech LLC'
    - K241001: decision_date changed
      '20240315' -> '20240320'

Diff report written to: ~/fda-510k-data/projects/cardiovascular_devices/field_changes_report.md
```

## Real-World Scenarios

### Scenario 1: Company Acquisition

**Situation:** You're tracking predicates and notice applicant name changed.

**Example:**
```bash
$ python3 change_detector.py --project my_510k --diff-report
...
Field changes detected: 1
  K241001: applicant changed
    'InnovateMed Inc' -> 'GlobalHealth Corp'
```

**Impact:** Your predicate device is now owned by a different company. May affect:
- Correspondence with manufacturer
- Quality system documentation references
- Competitive landscape analysis

**Action:** Update your 510(k) submission references and contact information.

### Scenario 2: Decision Date Correction

**Situation:** FDA backdates a clearance decision.

**Example:**
```bash
$ python3 change_detector.py --project competitor_analysis --diff-report
...
Field changes detected: 1
  K240501: decision_date changed
    '20240420' -> '20240401'
```

**Impact:** Competitor's device was actually cleared 19 days earlier than originally reported.

**Action:** Review timeline implications for first-to-market claims, update competitive analysis.

### Scenario 3: Version Update

**Situation:** FDA updates device name with version number.

**Example:**
```bash
$ python3 change_detector.py --project predicates --diff-report
...
Field changes detected: 1
  K230101: device_name changed
    'Surgical Robot System' -> 'Surgical Robot System v3.5'
```

**Impact:** Predicate device has version information that wasn't previously available.

**Action:** Verify which version applies to substantial equivalence comparison.

## Integration with Existing Workflow

### Daily Change Detection

Add to your daily monitoring script:

```bash
#!/bin/bash
# daily_check.sh

PROJECTS=("cardiovascular" "orthopedic" "digital_pathology")

for project in "${PROJECTS[@]}"; do
    echo "Checking $project..."
    python3 change_detector.py \
        --project "$project" \
        --diff-report \
        --trigger \
        --quiet
done

echo "Reports generated in ~/fda-510k-data/projects/*/field_changes_report.md"
```

### Automated Email Reports

Combine with email notification:

```bash
#!/bin/bash
# check_and_notify.sh

python3 change_detector.py \
    --project my_project \
    --diff-report \
    --json > /tmp/changes.json

if [ $(jq '.total_field_changes' /tmp/changes.json) -gt 0 ]; then
    cat ~/fda-510k-data/projects/my_project/field_changes_report.md | \
        mail -s "FDA Field Changes Detected" regulatory@company.com
fi
```

### CI/CD Integration

Add to GitHub Actions workflow:

```yaml
name: FDA Change Detection

on:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM UTC

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Run Change Detection
        run: |
          python3 change_detector.py \
            --project ${{ matrix.project }} \
            --diff-report \
            --json

      - name: Upload Report
        uses: actions/upload-artifact@v2
        with:
          name: field-changes-report
          path: ~/fda-510k-data/projects/*/field_changes_report.md
```

## Troubleshooting

### No Changes Detected

**Symptoms:** `Field changes detected: 0` even when you expect changes.

**Causes:**
1. Diff reporting not enabled (missing `--diff-report` flag)
2. No stored device_data in fingerprint (first run)
3. Changes in fields not monitored

**Solution:**
```bash
# First run establishes baseline
python3 change_detector.py --project my_project --diff-report

# Subsequent runs detect changes
python3 change_detector.py --project my_project --diff-report
```

### False Positives

**Symptoms:** Changes reported for whitespace differences.

**Cause:** This should not happen - whitespace is normalized.

**Solution:** Report as bug if encountered.

### Report Not Generated

**Symptoms:** No field_changes_report.md file created.

**Causes:**
1. No field changes detected (working as designed)
2. Project directory doesn't exist
3. Permission issue writing file

**Solution:**
```bash
# Check project directory exists
ls ~/fda-510k-data/projects/my_project/

# Check permissions
ls -la ~/fda-510k-data/projects/my_project/

# Run with verbose output
python3 change_detector.py --project my_project --diff-report
```

## Best Practices

### 1. Run Regularly

Detect changes early by running daily:

```bash
# Add to crontab
0 9 * * * cd /path/to/scripts && python3 change_detector.py --project my_project --diff-report
```

### 2. Review Reports

Manually review generated reports for critical changes:
- Decision date corrections affecting timelines
- Applicant changes indicating acquisitions
- Device name updates suggesting new versions

### 3. Archive Reports

Keep historical record of field changes:

```bash
# Archive with timestamp
cp field_changes_report.md \
   "field_changes_$(date +%Y%m%d).md"
```

### 4. Combine with Other Flags

Use `--trigger` to automate new clearance processing:

```bash
python3 change_detector.py \
    --project my_project \
    --diff-report \
    --trigger \
    --json > changes.json
```

### 5. Monitor Critical Fields

Pay special attention to:
- **decision_date** - Impacts competitive timelines
- **applicant** - Affects manufacturer relationships
- **device_name** - May indicate version changes

## API Usage

### Python Integration

Use diff detection programmatically:

```python
from change_detector import detect_changes
from fda_api_client import FDAClient

client = FDAClient()

# Detect changes with field diff enabled
result = detect_changes(
    project_name="my_project",
    client=client,
    verbose=True,
    detect_field_diffs=True,  # Enable diff detection
)

# Check for field changes
if result["total_field_changes"] > 0:
    print(f"Found {result['total_field_changes']} field changes")

    # Process field changes
    for change in result["changes"]:
        if change["change_type"] == "field_changes":
            for item in change["new_items"]:
                print(f"{item['k_number']}: {item['field']}")
                print(f"  Before: {item['before']}")
                print(f"  After: {item['after']}")
```

### Generate Custom Report

```python
from change_detector import _generate_diff_report

# Custom field changes
changes = [
    {
        "k_number": "K241001",
        "field": "applicant",
        "before": "OldCorp",
        "after": "NewCorp",
    }
]

# Generate report
report = _generate_diff_report(
    changes,
    product_code="DQY",
    timestamp="2026-02-17T10:00:00+00:00",
    output_path="/tmp/custom_report.md",
)

print(report)
```

## FAQ

**Q: Does diff reporting slow down change detection?**
A: No. Overhead is <5ms per product code (negligible).

**Q: How much additional storage does device_data require?**
A: ~200 bytes per K-number. For 100 devices: ~20 KB total.

**Q: Can I customize which fields are monitored?**
A: Not currently. All 6 fields are always monitored. Future enhancement.

**Q: What happens on the first run?**
A: First run establishes baseline (stores device_data). Second run detects changes.

**Q: Can I disable diff reporting after enabling it?**
A: Yes. Simply omit `--diff-report` flag. Device_data remains in fingerprint but is not used.

**Q: Does this work with multiple product codes?**
A: Yes. Diff detection runs for all product codes in the project.

**Q: Are new K-numbers included in diff reports?**
A: No. New K-numbers are reported separately as "new_clearances". Diff reports only show changes to existing K-numbers.

**Q: How do I know which fields changed most often?**
A: Check the "Changes by Field Type" section in the markdown report for frequency statistics.

## Support

For issues or questions:

1. Check this guide first
2. Review test examples in `tests/test_change_detector.py`
3. Run demo script: `python3 demo_diff_reporting.py`
4. File issue on GitHub with example and error message

## Version History

**v1.0 (2026-02-17)** - Initial release
- Field-level diff detection for 6 monitored fields
- Markdown report generation
- CLI integration with --diff-report flag
- 18 comprehensive tests
- Complete backward compatibility
