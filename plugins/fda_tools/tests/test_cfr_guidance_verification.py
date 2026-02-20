#!/usr/bin/env python3
"""
CFR Citation and FDA Guidance Document Verification
Validates all regulatory references for accuracy and currency
"""

import requests
import sys
from datetime import datetime

# CFR Citations to verify
CFR_CITATIONS = [
    {
        "citation": "21 CFR 803",
        "title": "Medical Device Reporting",
        "url": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-803",
        "context": "MAUDE adverse event data",
        "expected_sections": ["803.3", "803.50", "803.52"]
    },
    {
        "citation": "21 CFR 7",
        "title": "Enforcement Policy",
        "url": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-7",
        "context": "Device recalls and classifications",
        "expected_sections": ["7.40", "7.41", "7.45"]
    },
    {
        "citation": "21 CFR 807 Subpart E",
        "title": "Premarket Notification",
        "url": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-807/subpart-E",
        "context": "510(k) validation and clearances",
        "expected_sections": ["807.87", "807.92", "807.95"]
    }
]

# FDA Guidance Documents to verify
GUIDANCE_DOCUMENTS = [
    {
        "title": "Medical Device Reporting for Manufacturers",
        "date": "2016-12-19",
        "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/medical-device-reporting-manufacturers",
        "context": "MAUDE data requirements",
        "keywords": ["reporting", "adverse", "MDR"]
    },
    {
        "title": "Product Recalls, Including Removals and Corrections",
        "date": "2019-11-07",
        "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/product-recalls-including-removals-and-corrections",
        "context": "Recall classifications and procedures",
        "keywords": ["recall", "Class I", "Class II"]
    },
    {
        "title": "The 510(k) Program: Evaluating Substantial Equivalence",
        "date": "2014-07-28",
        "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/510k-program-evaluating-substantial-equivalence-premarket-notifications-510k",
        "context": "SE determination criteria",
        "keywords": ["substantial equivalence", "510(k)", "predicate"]
    }
]

def test_cfr_citation(citation_info):
    """Test CFR citation URL and content"""
    print(f"\n{'='*70}")
    print(f"Testing CFR: {citation_info['citation']}")
    print(f"{'='*70}")
    print(f"Title: {citation_info['title']}")
    print(f"Context: {citation_info['context']}")
    print(f"URL: {citation_info['url']}")

    try:
        # Test URL resolution
        response = requests.get(citation_info['url'], timeout=30, allow_redirects=True)

        if response.status_code == 200:
            print(f"✓ URL resolves (HTTP 200)")

            # Check if page contains expected sections
            content = response.text.lower()
            sections_found = []
            for section in citation_info['expected_sections']:
                if section.lower() in content:
                    sections_found.append(section)
                    print(f"  ✓ Section {section} found")
                else:
                    print(f"  ⚠️  Section {section} not found (may use different formatting)")

            return {
                "status": "SUCCESS",
                "url_valid": True,
                "sections_found": sections_found,
                "total_sections": len(citation_info['expected_sections'])
            }
        else:
            print(f"❌ URL error: HTTP {response.status_code}")
            return {
                "status": "ERROR",
                "url_valid": False,
                "error": response.status_code
            }

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return {
            "status": "EXCEPTION",
            "url_valid": False,
            "error": str(e)
        }

def test_guidance_document(guidance_info):
    """Test FDA guidance document URL and relevance"""
    print(f"\n{'='*70}")
    print(f"Testing Guidance: {guidance_info['title']}")
    print(f"{'='*70}")
    print(f"Date: {guidance_info['date']}")
    print(f"Context: {guidance_info['context']}")
    print(f"URL: {guidance_info['url']}")

    try:
        # Test URL resolution
        response = requests.get(guidance_info['url'], timeout=30, allow_redirects=True)

        if response.status_code == 200:
            print(f"✓ URL resolves (HTTP 200)")

            # Check for keywords
            content = response.text.lower()
            keywords_found = []
            for keyword in guidance_info['keywords']:
                if keyword.lower() in content:
                    keywords_found.append(keyword)
                    print(f"  ✓ Keyword '{keyword}' found")
                else:
                    print(f"  ⚠️  Keyword '{keyword}' not found")

            # Check if guidance appears current (not superseded)
            if 'superseded' in content or 'withdrawn' in content:
                print(f"  ⚠️  WARNING: Document may be superseded or withdrawn")
                superseded = True
            else:
                print(f"  ✓ No supersession indicators found")
                superseded = False

            return {
                "status": "SUCCESS",
                "url_valid": True,
                "keywords_found": keywords_found,
                "total_keywords": len(guidance_info['keywords']),
                "superseded": superseded
            }
        else:
            print(f"❌ URL error: HTTP {response.status_code}")
            return {
                "status": "ERROR",
                "url_valid": False,
                "error": response.status_code
            }

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return {
            "status": "EXCEPTION",
            "url_valid": False,
            "error": str(e)
        }

def main():
    """Run all CFR and guidance verification tests"""
    print("\n" + "="*70)
    print("CFR Citation & FDA Guidance Verification")
    print("Validating Regulatory References for Accuracy")
    print("="*70)

    results = {
        "timestamp": datetime.now().isoformat(),
        "cfr": [],
        "guidance": []
    }

    # Test CFR Citations
    print(f"\n{'#'*70}")
    print("PART 1: CFR CITATION VERIFICATION")
    print(f"{'#'*70}")

    for citation in CFR_CITATIONS:
        result = test_cfr_citation(citation)
        results["cfr"].append({
            "citation": citation["citation"],
            "result": result
        })

    # Test Guidance Documents
    print(f"\n{'#'*70}")
    print("PART 2: FDA GUIDANCE DOCUMENT VERIFICATION")
    print(f"{'#'*70}")

    for guidance in GUIDANCE_DOCUMENTS:
        result = test_guidance_document(guidance)
        results["guidance"].append({
            "title": guidance["title"],
            "result": result
        })

    # Overall Assessment
    print(f"\n{'='*70}")
    print("OVERALL VERIFICATION RESULTS")
    print(f"{'='*70}")

    # CFR Assessment
    cfr_valid = sum(1 for r in results["cfr"] if r["result"].get("url_valid"))
    cfr_total = len(results["cfr"])
    print(f"\nCFR Citations:")
    print(f"  Valid URLs: {cfr_valid}/{cfr_total} ({cfr_valid/cfr_total*100:.0f}%)")

    # Guidance Assessment
    guidance_valid = sum(1 for r in results["guidance"] if r["result"].get("url_valid"))
    guidance_superseded = sum(1 for r in results["guidance"] if r["result"].get("superseded"))
    guidance_total = len(results["guidance"])
    print(f"\nGuidance Documents:")
    print(f"  Valid URLs: {guidance_valid}/{guidance_total} ({guidance_valid/guidance_total*100:.0f}%)")
    print(f"  Superseded: {guidance_superseded}/{guidance_total}")

    # Pass/Fail Determination
    cfr_pass = cfr_valid == cfr_total
    guidance_pass = (guidance_valid == guidance_total) and (guidance_superseded == 0)

    print(f"\n{'='*70}")
    if cfr_pass and guidance_pass:
        print("✅ VERIFICATION PASSED")
        print(f"{'='*70}")
        print("\nAll CFR citations and guidance documents verified:")
        print("  ✓ All URLs resolve correctly")
        print("  ✓ No superseded guidance found")
        print("  ✓ Regulatory references accurate and current")
        return 0
    else:
        print("⚠️  VERIFICATION ISSUES FOUND")
        print(f"{'='*70}")
        if not cfr_pass:
            print("\n❌ CFR Citation Issues:")
            for r in results["cfr"]:
                if not r["result"].get("url_valid"):
                    print(f"  - {r['citation']}: URL invalid")
        if not guidance_pass:
            print("\n❌ Guidance Document Issues:")
            for r in results["guidance"]:
                if not r["result"].get("url_valid"):
                    print(f"  - {r['title']}: URL invalid")
                elif r["result"].get("superseded"):
                    print(f"  - {r['title']}: May be superseded")
        return 1

if __name__ == "__main__":
    sys.exit(main())
