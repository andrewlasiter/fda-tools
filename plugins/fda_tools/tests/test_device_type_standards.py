#!/usr/bin/env python3
"""
Test Device-Type Specific Standards Database Integration

Tests that the 4 device-type standards databases are properly structured
and can be loaded by the draft command.
"""

import json
import os
import sys
from pathlib import Path

# Find plugin root - standards are in plugins/fda-tools/data/standards/
plugin_root = Path(__file__).parent.parent / "plugins" / "fda-tools"
standards_dir = plugin_root / "data" / "standards"

def test_standards_files_exist():
    """Test that all 4 standards JSON files exist"""
    print("=" * 80)
    print("TEST 1: Standards Files Exist")
    print("=" * 80)

    required_files = [
        "standards_robotics.json",
        "standards_neurostim.json",
        "standards_ivd.json",
        "standards_samd.json"
    ]

    all_exist = True
    for filename in required_files:
        filepath = standards_dir / filename
        exists = filepath.exists()
        status = "✅ PASS" if exists else "❌ FAIL"
        print(f"{status}: {filename} {'exists' if exists else 'NOT FOUND'}")
        all_exist = all_exist and exists

    return all_exist

def test_json_schema_valid():
    """Test that all JSON files have valid schema"""
    print("\n" + "=" * 80)
    print("TEST 2: JSON Schema Validation")
    print("=" * 80)

    required_fields = ["category", "product_codes", "applicable_standards"]
    standard_fields = ["number", "title", "applicability", "sections"]

    all_valid = True
    for json_file in standards_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)

            # Check top-level fields
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                print(f"❌ FAIL: {json_file.name} missing fields: {missing_fields}")
                all_valid = False
                continue

            # Check product_codes is a list
            if not isinstance(data["product_codes"], list):
                print(f"❌ FAIL: {json_file.name} product_codes must be a list")
                all_valid = False
                continue

            # Check applicable_standards is a list
            if not isinstance(data["applicable_standards"], list):
                print(f"❌ FAIL: {json_file.name} applicable_standards must be a list")
                all_valid = False
                continue

            # Check each standard has required fields
            for i, std in enumerate(data["applicable_standards"]):
                missing_std_fields = [field for field in standard_fields if field not in std]
                if missing_std_fields:
                    print(f"❌ FAIL: {json_file.name} standard #{i} missing: {missing_std_fields}")
                    all_valid = False

            if all_valid:
                print(f"✅ PASS: {json_file.name} - valid schema, {len(data['applicable_standards'])} standards")

        except json.JSONDecodeError as e:
            print(f"❌ FAIL: {json_file.name} - invalid JSON: {e}")
            all_valid = False
        except Exception as e:
            print(f"❌ FAIL: {json_file.name} - error: {e}")
            all_valid = False

    return all_valid

def test_product_code_mapping():
    """Test that all product codes are mapped correctly"""
    print("\n" + "=" * 80)
    print("TEST 3: Product Code Mapping")
    print("=" * 80)

    expected_mapping = {
        # Robotics
        "QBH": "standards_robotics.json",
        "OZO": "standards_robotics.json",
        "QPA": "standards_robotics.json",
        # Neurostimulators
        "GZB": "standards_neurostim.json",
        "OLO": "standards_neurostim.json",
        "LWV": "standards_neurostim.json",
        # IVD
        "JJE": "standards_ivd.json",
        "LCX": "standards_ivd.json",
        "OBP": "standards_ivd.json",
        # SaMD
        "QIH": "standards_samd.json",
        "QJT": "standards_samd.json",
        "POJ": "standards_samd.json"
    }

    all_mapped = True
    for product_code, expected_file in expected_mapping.items():
        filepath = standards_dir / expected_file
        if not filepath.exists():
            print(f"❌ FAIL: {product_code} maps to {expected_file} which doesn't exist")
            all_mapped = False
            continue

        with open(filepath) as f:
            data = json.load(f)

        if product_code in data["product_codes"]:
            print(f"✅ PASS: {product_code} → {expected_file} ({data['category']})")
        else:
            print(f"❌ FAIL: {product_code} not found in {expected_file} product_codes")
            all_mapped = False

    return all_mapped

def test_expert_requested_standards():
    """Test that expert-requested standards are present"""
    print("\n" + "=" * 80)
    print("TEST 4: Expert-Requested Standards Present")
    print("=" * 80)

    expert_standards = {
        "standards_robotics.json": [
            ("ISO 13482:2014", "Rodriguez - Robotics expert"),
            ("IEC 80601-2-77:2019", "Rodriguez - Surgical robotics specific")
        ],
        "standards_neurostim.json": [
            ("IEC 60601-2-10:2012", "Anderson - Neurostimulator specific"),
            ("ISO 14708-3:2017", "Anderson - Implantable neurostimulators")
        ],
        "standards_ivd.json": [
            ("CLSI EP05-A3:2014", "Park - IVD precision"),
            ("CLSI EP09c:2018", "Park - IVD method comparison")
        ],
        "standards_samd.json": [
            ("IEC 62304:2006/AMD1:2015", "Kim - Software lifecycle"),
            ("IEC 62366-1:2015", "Kim - Usability"),
            ("AAMI TIR57:2016", "Kim - Cybersecurity")
        ]
    }

    all_present = True
    for filename, standards_list in expert_standards.items():
        filepath = standards_dir / filename
        with open(filepath) as f:
            data = json.load(f)

        standard_numbers = [std["number"] for std in data["applicable_standards"]]

        for std_number, expert_req in standards_list:
            if std_number in standard_numbers:
                print(f"✅ PASS: {std_number} found ({expert_req})")
            else:
                print(f"❌ FAIL: {std_number} NOT FOUND - requested by {expert_req}")
                all_present = False

    return all_present

def test_standards_counts():
    """Test that standards counts match specifications"""
    print("\n" + "=" * 80)
    print("TEST 5: Standards Count Verification")
    print("=" * 80)

    expected_counts = {
        "standards_robotics.json": 8,
        "standards_neurostim.json": 9,
        "standards_ivd.json": 11,
        "standards_samd.json": 8
    }

    all_correct = True
    for filename, expected_count in expected_counts.items():
        filepath = standards_dir / filename
        with open(filepath) as f:
            data = json.load(f)

        actual_count = len(data["applicable_standards"])
        if actual_count == expected_count:
            print(f"✅ PASS: {filename} has {actual_count} standards (expected {expected_count})")
        else:
            print(f"❌ FAIL: {filename} has {actual_count} standards (expected {expected_count})")
            all_correct = False

    return all_correct

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("DEVICE-TYPE SPECIFIC STANDARDS DATABASE TEST SUITE")
    print("=" * 80)
    print(f"Plugin Root: {plugin_root}")
    print(f"Standards Dir: {standards_dir}")
    print()

    # Run all tests
    results = {
        "Files Exist": test_standards_files_exist(),
        "JSON Schema Valid": test_json_schema_valid(),
        "Product Code Mapping": test_product_code_mapping(),
        "Expert-Requested Standards": test_expert_requested_standards(),
        "Standards Counts": test_standards_counts()
    }

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "=" * 80)
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("=" * 80)
        return 0
    else:
        print(f"⚠️  SOME TESTS FAILED ({passed}/{total} passed)")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(main())
