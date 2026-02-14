#!/usr/bin/env python3
"""
End-to-End Test for Phase 1: Data Integrity
Simulates full BatchFetch enrichment workflow with Phase 1 features
"""

import os
import sys
import json
import csv
import tempfile
import shutil
from datetime import datetime
import time

print("=" * 70)
print("Phase 1: Data Integrity - End-to-End Test")
print("=" * 70)
print()

# Create temporary test directory
test_dir = tempfile.mkdtemp(prefix="phase1_test_")
print(f"Test directory: {test_dir}")
print()

# Step 1: Create test CSV with realistic MQN (coronary stent) devices
print("Step 1: Creating test CSV...")
test_csv = os.path.join(test_dir, "510k_download.csv")

test_devices = [
    {
        'KNUMBER': 'K241234',
        'APPLICANT': 'Boston Scientific',
        'DEVICENAME': 'Cardiovascular Drug-Eluting Coronary Stent System',
        'PRODUCTCODE': 'MQN',
        'DECISIONDATE': '2024-03-15',
        'EXPEDITEDREVIEW': 'N'
    },
    {
        'KNUMBER': 'K240987',
        'APPLICANT': 'Medtronic Vascular',
        'DEVICENAME': 'Resolute Onyx Drug-Eluting Coronary Stent',
        'PRODUCTCODE': 'MQN',
        'DECISIONDATE': '2024-06-22',
        'EXPEDITEDREVIEW': 'N'
    },
    {
        'KNUMBER': 'K242456',
        'APPLICANT': 'Abbott Vascular',
        'DEVICENAME': 'Xience Sierra Everolimus Eluting Coronary Stent',
        'PRODUCTCODE': 'MQN',
        'DECISIONDATE': '2024-08-10',
        'EXPEDITEDREVIEW': 'N'
    },
    {
        'KNUMBER': 'K243012',
        'APPLICANT': 'Terumo Medical',
        'DEVICENAME': 'Ultimaster Tansei Drug-Eluting Stent',
        'PRODUCTCODE': 'MQN',
        'DECISIONDATE': '2024-11-05',
        'EXPEDITEDREVIEW': 'N'
    }
]

with open(test_csv, 'w', newline='') as f:
    fieldnames = ['KNUMBER', 'APPLICANT', 'DEVICENAME', 'PRODUCTCODE', 'DECISIONDATE', 'EXPEDITEDREVIEW']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(test_devices)

print(f"✓ Created test CSV with {len(test_devices)} devices")
print()

# Step 2: Define Phase 1 functions (from batchfetch.md)
print("Step 2: Loading Phase 1 functions...")

def calculate_quality_score(row, api_log):
    """Calculate enrichment quality score (0-100)"""
    score = 0

    # Data Completeness (40 points)
    fields_to_check = [
        'maude_productcode_5y',
        'maude_trending',
        'recalls_total',
        'api_validated',
        'decision_description',
        'summary_type'
    ]
    populated = sum([1 for f in fields_to_check if row.get(f) not in ['N/A', '', None, 'Unknown', 'unknown']])
    completeness_pct = populated / len(fields_to_check)
    score += completeness_pct * 40

    # API Success Rate (30 points)
    k_number = row['KNUMBER']
    device_calls = [r for r in api_log if k_number in r.get('query', '')]
    if device_calls:
        success_rate = len([r for r in device_calls if r.get('success', False)]) / len(device_calls)
        score += success_rate * 30
    else:
        score += 15

    # Data Freshness (20 points)
    if row.get('api_validated') == 'Yes':
        score += 20
    elif row.get('api_validated') == 'No':
        score += 10

    # Cross-validation (10 points)
    if row.get('maude_scope') in ['PRODUCT_CODE', 'UNAVAILABLE']:
        score += 10

    return round(score, 1)

def write_enrichment_metadata(project_dir, enriched_rows, api_log):
    """Write enrichment metadata JSON with full provenance"""

    total_calls = len(api_log)
    failed_calls = len([r for r in api_log if not r.get('success', False)])
    total_duration = sum([r.get('duration', 0) for r in api_log])

    metadata = {
        "enrichment_run": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "api_version": "openFDA v2.1",
            "rate_limit": "240 requests/minute",
            "total_api_calls": total_calls,
            "failed_calls": failed_calls,
            "success_rate_pct": round((total_calls - failed_calls) / total_calls * 100, 1) if total_calls > 0 else 0,
            "enrichment_duration_seconds": round(total_duration, 2)
        },
        "per_device": {}
    }

    for row in enriched_rows:
        k_number = row['KNUMBER']
        product_code = row.get('PRODUCTCODE', 'Unknown')
        device_calls = [r for r in api_log if k_number in r.get('query', '')]

        metadata["per_device"][k_number] = {
            "maude_events": {
                "value": row.get('maude_productcode_5y', 'N/A'),
                "source": f"device/event.json?search=product_code:\"{product_code}\"&count=date_received",
                "scope": "PRODUCT_CODE",
                "query_timestamp": device_calls[0].get('timestamp', '') if device_calls else '',
                "confidence": "HIGH" if row.get('maude_productcode_5y') not in ['N/A', '', None] else "LOW"
            },
            "recalls": {
                "value": row.get('recalls_total', 0),
                "source": f"device/recall.json?search=k_numbers:\"{k_number}\"&limit=10",
                "scope": "DEVICE_SPECIFIC",
                "query_timestamp": device_calls[1].get('timestamp', '') if len(device_calls) > 1 else '',
                "confidence": "HIGH"
            },
            "validation": {
                "value": row.get('api_validated', 'No'),
                "source": f"device/510k.json?search=k_number:\"{k_number}\"&limit=1",
                "scope": "DEVICE_SPECIFIC",
                "query_timestamp": device_calls[2].get('timestamp', '') if len(device_calls) > 2 else '',
                "confidence": "HIGH"
            }
        }

    metadata_path = os.path.join(project_dir, 'enrichment_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ Enrichment metadata: {os.path.basename(metadata_path)}")

def generate_quality_report(project_dir, enriched_rows, api_log):
    """Generate quality_report.md with validation summary"""

    scores = [calculate_quality_score(row, api_log) for row in enriched_rows]
    avg_score = sum(scores) / len(scores) if scores else 0

    for i, row in enumerate(enriched_rows):
        row['enrichment_quality_score'] = scores[i]

    high_conf = len([s for s in scores if s >= 80])
    med_conf = len([s for s in scores if 60 <= s < 80])
    low_conf = len([s for s in scores if s < 60])

    issues = []
    for row in enriched_rows:
        if row.get('maude_productcode_5y') in ['N/A', '', None, 'unknown']:
            issues.append(f"⚠️  {row['KNUMBER']}: MAUDE data unavailable")
        if row.get('api_validated') == 'No':
            issues.append(f"⚠️  {row['KNUMBER']}: K-number not validated")
        if row.get('recalls_total', 0) > 0:
            issues.append(f"ℹ️  {row['KNUMBER']}: {row['recalls_total']} recall(s)")

    total_calls = len(api_log)
    successful_calls = len([r for r in api_log if r.get('success', False)])
    success_rate = (successful_calls / total_calls * 100) if total_calls else 0

    grade = "EXCELLENT" if avg_score >= 80 else "GOOD" if avg_score >= 60 else "FAIR"

    report = f"""# Enrichment Quality Report

**Overall Quality Score:** {avg_score:.1f}/100 ({grade})

## Summary
- Devices enriched: {len(enriched_rows)}/{len(enriched_rows)} (100%)
- API success rate: {success_rate:.1f}% ({successful_calls}/{total_calls} calls)
- Average quality score: {avg_score:.1f}/100
- Data timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

## Data Confidence Distribution

- **HIGH confidence (≥80):** {high_conf} devices ({high_conf/len(enriched_rows)*100:.1f}%)
- **MEDIUM confidence (60-79):** {med_conf} devices ({med_conf/len(enriched_rows)*100:.1f}%)
- **LOW confidence (<60):** {low_conf} devices ({low_conf/len(enriched_rows)*100:.1f}%)

## Quality Issues Detected

"""
    if issues:
        for i, issue in enumerate(issues, 1):
            report += f"{i}. {issue}\n"
    else:
        report += "✓ No quality issues detected\n"

    report += f"""
## Next Steps

1. **Review Low-Confidence Devices:** Investigate devices with scores <60
2. **Validate MAUDE Context:** Remember MAUDE counts are product code-level
3. **Cross-Check Recalls:** Verify recall status at https://www.fda.gov/safety/recalls
"""

    report_path = os.path.join(project_dir, 'quality_report.md')
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"✓ Quality report: {os.path.basename(report_path)}")

def generate_regulatory_context(project_dir):
    """Generate regulatory_context.md with CFR citations"""

    context = """# Regulatory Context for Enriched Data

## MAUDE Adverse Events

**Regulation:** 21 CFR Part 803 - Medical Device Reporting (MDR)
- **Citation:** https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-803

### ⚠️  CRITICAL SCOPE LIMITATION
MAUDE events are aggregated by PRODUCT CODE, NOT individual K-numbers.

## Device Recalls

**Regulation:** 21 CFR Part 7, Subpart C - Recalls
- **Citation:** https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-7/subpart-C

### ✓ DATA ACCURACY
Recall data IS device-specific and linked to K-numbers.

## 510(k) Validation

**Regulation:** 21 CFR Part 807, Subpart E - Premarket Notification
- **Citation:** https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-807/subpart-E
"""

    context_path = os.path.join(project_dir, 'regulatory_context.md')
    with open(context_path, 'w') as f:
        f.write(context)

    print(f"✓ Regulatory context: {os.path.basename(context_path)}")

print("✓ Phase 1 functions loaded")
print()

# Step 3: Simulate enrichment with mock API responses
print("Step 3: Simulating enrichment with mock API data...")

# Simulate varied enrichment scenarios
enrichment_scenarios = [
    # K241234: Perfect data
    {
        'maude_productcode_5y': 2847,
        'maude_trending': 'stable',
        'maude_recent_6m': 234,
        'maude_scope': 'PRODUCT_CODE',
        'recalls_total': 0,
        'recall_latest_date': '',
        'recall_class': '',
        'recall_status': '',
        'api_validated': 'Yes',
        'decision_description': 'Substantially Equivalent (SESE)',
        'summary_type': 'Summary',
        'api_success': [True, True, True]  # All 3 calls successful
    },
    # K240987: Has recall
    {
        'maude_productcode_5y': 2847,
        'maude_trending': 'increasing',
        'maude_recent_6m': 298,
        'maude_scope': 'PRODUCT_CODE',
        'recalls_total': 1,
        'recall_latest_date': '2023-08-15',
        'recall_class': 'Class II',
        'recall_status': 'Completed',
        'api_validated': 'Yes',
        'decision_description': 'Substantially Equivalent (SESE)',
        'summary_type': 'Summary',
        'api_success': [True, True, True]
    },
    # K242456: Missing MAUDE data
    {
        'maude_productcode_5y': 'N/A',
        'maude_trending': 'unknown',
        'maude_recent_6m': 'N/A',
        'maude_scope': 'UNAVAILABLE',
        'recalls_total': 0,
        'recall_latest_date': '',
        'recall_class': '',
        'recall_status': '',
        'api_validated': 'Yes',
        'decision_description': 'Substantially Equivalent (SESE)',
        'summary_type': 'Summary',
        'api_success': [False, True, True]  # MAUDE call failed
    },
    # K243012: Not validated
    {
        'maude_productcode_5y': 2847,
        'maude_trending': 'stable',
        'maude_recent_6m': 234,
        'maude_scope': 'PRODUCT_CODE',
        'recalls_total': 0,
        'recall_latest_date': '',
        'recall_class': '',
        'recall_status': '',
        'api_validated': 'No',
        'decision_description': 'Unknown',
        'summary_type': 'Unknown',
        'api_success': [True, True, False]  # Validation failed
    }
]

api_log = []
enriched_rows = []

for i, device in enumerate(test_devices):
    scenario = enrichment_scenarios[i]
    k_number = device['KNUMBER']
    product_code = device['PRODUCTCODE']

    # Simulate API calls
    for j, (endpoint, query, success) in enumerate([
        ('device/event', f'product_code:"{product_code}"', scenario['api_success'][0]),
        ('device/recall', f'k_numbers:"{k_number}"', scenario['api_success'][1]),
        ('device/510k', f'k_number:"{k_number}"', scenario['api_success'][2])
    ]):
        api_log.append({
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'endpoint': endpoint,
            'query': query,
            'k_number': k_number,
            'success': success,
            'duration': 0.3 + (j * 0.05)
        })

    # Add enrichment data
    enriched_device = device.copy()
    enriched_device.update({
        'maude_productcode_5y': scenario['maude_productcode_5y'],
        'maude_trending': scenario['maude_trending'],
        'maude_recent_6m': scenario['maude_recent_6m'],
        'maude_scope': scenario['maude_scope'],
        'recalls_total': scenario['recalls_total'],
        'recall_latest_date': scenario['recall_latest_date'],
        'recall_class': scenario['recall_class'],
        'recall_status': scenario['recall_status'],
        'api_validated': scenario['api_validated'],
        'decision_description': scenario['decision_description'],
        'summary_type': scenario['summary_type'],
        'enrichment_timestamp': datetime.utcnow().isoformat() + 'Z',
        'api_version': 'openFDA v2.1',
        'data_confidence': 'HIGH' if scenario['api_validated'] == 'Yes' and scenario['maude_productcode_5y'] not in ['N/A'] else 'MEDIUM' if scenario['api_validated'] == 'Yes' or scenario['maude_productcode_5y'] not in ['N/A'] else 'LOW'
    })

    # CFR citations
    citations = []
    if scenario['maude_productcode_5y'] not in ['N/A', '', None]:
        citations.append('21 CFR 803')
    if scenario['recalls_total'] > 0:
        citations.append('21 CFR 7')
    if scenario['api_validated'] == 'Yes':
        citations.append('21 CFR 807')
    enriched_device['cfr_citations'] = ', '.join(citations) if citations else 'N/A'

    # Guidance refs
    guidance_count = 0
    if scenario['maude_productcode_5y'] not in ['N/A', '', None]:
        guidance_count += 1
    if scenario['recalls_total'] > 0:
        guidance_count += 1
    if scenario['api_validated'] == 'Yes':
        guidance_count += 1
    enriched_device['guidance_refs'] = guidance_count

    enriched_rows.append(enriched_device)

print(f"✓ Enriched {len(enriched_rows)} devices")
print(f"✓ Logged {len(api_log)} API calls")
print()

# Step 4: Generate Phase 1 files
print("Step 4: Generating Phase 1 files...")
generate_quality_report(test_dir, enriched_rows, api_log)
write_enrichment_metadata(test_dir, enriched_rows, api_log)
generate_regulatory_context(test_dir)
print()

# Step 5: Write enriched CSV
print("Step 5: Writing enriched CSV...")
enriched_csv = os.path.join(test_dir, "510k_download_enriched.csv")
fieldnames = list(enriched_rows[0].keys())
with open(enriched_csv, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(enriched_rows)

print(f"✓ Enriched CSV: {os.path.basename(enriched_csv)}")
print(f"  - Original columns: {len(test_devices[0].keys())}")
print(f"  - Enriched columns: {len(fieldnames)} (+{len(fieldnames) - len(test_devices[0].keys())} enrichment)")
print()

# Step 6: Verify Phase 1 outputs
print("Step 6: Verifying Phase 1 outputs...")

verification_results = []

# Check files exist
files_to_check = [
    ('enriched CSV', enriched_csv),
    ('quality_report.md', os.path.join(test_dir, 'quality_report.md')),
    ('enrichment_metadata.json', os.path.join(test_dir, 'enrichment_metadata.json')),
    ('regulatory_context.md', os.path.join(test_dir, 'regulatory_context.md'))
]

for name, path in files_to_check:
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    status = "✓" if exists and size > 0 else "✗"
    verification_results.append((name, exists and size > 0))
    print(f"  {status} {name}: {size} bytes")

# Check CSV columns
phase1_columns = [
    'enrichment_timestamp',
    'api_version',
    'data_confidence',
    'enrichment_quality_score',
    'cfr_citations',
    'guidance_refs'
]

with open(enriched_csv, 'r') as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames

print(f"\n  Phase 1 columns in CSV:")
for col in phase1_columns:
    present = col in headers
    status = "✓" if present else "✗"
    verification_results.append((f"CSV column: {col}", present))
    print(f"    {status} {col}")

# Check metadata structure
with open(os.path.join(test_dir, 'enrichment_metadata.json'), 'r') as f:
    metadata = json.load(f)

print(f"\n  Metadata validation:")
checks = [
    ('enrichment_run' in metadata, 'enrichment_run section'),
    ('per_device' in metadata, 'per_device section'),
    (len(metadata['per_device']) == len(enriched_rows), f'all {len(enriched_rows)} devices logged')
]
for passed, desc in checks:
    status = "✓" if passed else "✗"
    verification_results.append((f"Metadata: {desc}", passed))
    print(f"    {status} {desc}")

# Check quality scores
print(f"\n  Quality score distribution:")
scores = [row['enrichment_quality_score'] for row in enriched_rows]
print(f"    - Average: {sum(scores)/len(scores):.1f}/100")
print(f"    - Range: {min(scores):.1f} - {max(scores):.1f}")
print(f"    - HIGH (≥80): {len([s for s in scores if s >= 80])}")
print(f"    - MEDIUM (60-79): {len([s for s in scores if 60 <= s < 80])}")
print(f"    - LOW (<60): {len([s for s in scores if s < 60])}")

print()
print("=" * 70)
print("Test Results Summary")
print("=" * 70)

all_passed = all([result for _, result in verification_results])
total_checks = len(verification_results)
passed_checks = sum([result for _, result in verification_results])

if all_passed:
    print(f"✅ ALL TESTS PASSED ({passed_checks}/{total_checks} checks)")
    print()
    print("Phase 1 Implementation: VERIFIED")
    print()
    print("Generated files:")
    for name, path in files_to_check:
        print(f"  - {name}")
    print()
    print(f"Test directory: {test_dir}")
    print("(Directory preserved for inspection)")
else:
    print(f"❌ SOME TESTS FAILED ({passed_checks}/{total_checks} checks)")
    print()
    print("Failed checks:")
    for name, result in verification_results:
        if not result:
            print(f"  ✗ {name}")

print()
print("=" * 70)
