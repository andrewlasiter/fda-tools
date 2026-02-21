#!/usr/bin/env python3
"""
Combination Product Detector - Interactive Demo

Demonstrates detection of drug-device, device-biologic, and drug-device-biologic
combination products with RHO assignment per 21 CFR Part 3.

Usage:
    python3 demo_combination_detector.py

Author: FDA Tools Plugin Development Team
Date: 2026-02-14
"""

from fda_tools.lib.combination_detector import detect_combination_product


def print_result(device_name: str, result: dict):
    """Pretty-print detection result."""
    print(f"\n{'='*70}")
    print(f"DEVICE: {device_name}")
    print('='*70)

    print(f"\n🔍 DETECTION RESULT:")
    print(f"   Combination Product: {'YES' if result['is_combination'] else 'NO'}")
    if result['is_combination']:
        print(f"   Type: {result['combination_type']}")
        print(f"   Confidence: {result['confidence']}")

    print(f"\n🏛️  RHO ASSIGNMENT:")
    print(f"   RHO: {result['rho_assignment']}")
    print(f"   Rationale: {result['rho_rationale']}")
    if result['consultation_required']:
        print(f"   Consultation Required: {result['consultation_required']}")

    print(f"\n📋 REGULATORY PATHWAY:")
    print(f"   {result['regulatory_pathway']}")

    if result['detected_components']:
        print(f"\n🧬 DETECTED COMPONENTS ({len(result['detected_components'])}):")
        for comp in result['detected_components'][:10]:  # Show max 10
            print(f"   • {comp}")
        if len(result['detected_components']) > 10:
            print(f"   ... and {len(result['detected_components']) - 10} more")

    if result['recommendations']:
        print(f"\n📝 REGULATORY RECOMMENDATIONS:")
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"   {i}. {rec}")

    print()


def main():
    """Run demo scenarios."""
    print("\n" + "="*70)
    print(" COMBINATION PRODUCT DETECTOR - INTERACTIVE DEMO")
    print(" FDA Tools Plugin - Sprint 3 Implementation")
    print("="*70)

    # Scenario 1: Drug-Eluting Stent (Sharma's example)
    print("\n\n" + "▶"*35)
    print("SCENARIO 1: Drug-Eluting Coronary Stent")
    print("▶"*35)

    result = detect_combination_product(
        device_description="Cobalt-chromium coronary stent with paclitaxel-eluting polymer coating for inhibition of neointimal hyperplasia",
        trade_name="CardioStent DES Pro",
        intended_use="Treatment of de novo coronary artery lesions in native coronary arteries"
    )
    print_result("CardioStent DES Pro (Drug-Eluting Stent)", result)

    # Scenario 2: Drug-Coated Balloon
    print("\n\n" + "▶"*35)
    print("SCENARIO 2: Drug-Coated Angioplasty Balloon")
    print("▶"*35)

    result = detect_combination_product(
        device_description="Percutaneous transluminal angioplasty balloon catheter with drug-coated surface containing sirolimus for peripheral intervention",
        trade_name="VascuBalloon DCB",
        intended_use="Dilation of stenotic peripheral arteries in the femoropopliteal segment"
    )
    print_result("VascuBalloon DCB (Drug-Coated Balloon)", result)

    # Scenario 3: Antibiotic Bone Cement
    print("\n\n" + "▶"*35)
    print("SCENARIO 3: Antibiotic-Loaded Bone Cement")
    print("▶"*35)

    result = detect_combination_product(
        device_description="Polymethyl methacrylate (PMMA) bone cement with gentamicin antibiotic for prevention of prosthetic joint infection",
        trade_name="OrthoCement-G",
        intended_use="Fixation of orthopedic prostheses with antimicrobial protection in hip and knee arthroplasty"
    )
    print_result("OrthoCement-G (Antibiotic Bone Cement)", result)

    # Scenario 4: Collagen Wound Matrix
    print("\n\n" + "▶"*35)
    print("SCENARIO 4: Collagen Dermal Matrix")
    print("▶"*35)

    result = detect_combination_product(
        device_description="Acellular bovine pericardium collagen matrix for soft tissue reconstruction, decellularized and cross-linked",
        trade_name="DermMatrix Plus",
        intended_use="Temporary wound coverage and reinforcement of soft tissue defects"
    )
    print_result("DermMatrix Plus (Collagen Matrix)", result)

    # Scenario 5: Cell-Based Product
    print("\n\n" + "▶"*35)
    print("SCENARIO 5: Cell-Seeded Cartilage Scaffold")
    print("▶"*35)

    result = detect_combination_product(
        device_description="Tissue-engineered cell-seeded scaffold with autologous chondrocytes for articular cartilage repair",
        trade_name="CartiGrow Cell Therapy System",
        intended_use="Regeneration of focal cartilage defects in the knee joint"
    )
    print_result("CartiGrow Cell Therapy (Cell-Seeded Scaffold)", result)

    # Scenario 6: Complex Combination (Drug-Device-Biologic)
    print("\n\n" + "▶"*35)
    print("SCENARIO 6: Complex Combination Product")
    print("▶"*35)

    result = detect_combination_product(
        device_description="Collagen scaffold with drug-eluting coating containing recombinant growth factor BMP-2 and autologous bone marrow cells for spinal fusion",
        trade_name="OsteoGen Fusion Pro",
        intended_use="Bone regeneration and fusion in lumbar spine procedures"
    )
    print_result("OsteoGen Fusion Pro (Drug-Device-Biologic)", result)

    # Scenario 7: Standard Device (No Combination)
    print("\n\n" + "▶"*35)
    print("SCENARIO 7: Standard Bare Metal Stent (Control)")
    print("▶"*35)

    result = detect_combination_product(
        device_description="Cobalt-chromium coronary stent for mechanical vessel support, drug-free design",
        trade_name="MetalStent Basic",
        intended_use="Treatment of coronary artery stenosis"
    )
    print_result("MetalStent Basic (Standard Device)", result)

    # Scenario 8: Silver-Coated Device
    print("\n\n" + "▶"*35)
    print("SCENARIO 8: Antimicrobial Silver-Coated Catheter")
    print("▶"*35)

    result = detect_combination_product(
        device_description="Central venous catheter with silver-coated antimicrobial surface for infection reduction",
        trade_name="SilverLine CVC",
        intended_use="Central venous access with antimicrobial protection"
    )
    print_result("SilverLine CVC (Silver-Coated Catheter)", result)

    # Summary
    print("\n\n" + "="*70)
    print(" DEMO COMPLETE")
    print("="*70)
    print("\n📊 SUMMARY:")
    print("   • 8 device scenarios tested")
    print("   • Drug-device combinations: 4 (DES, DCB, bone cement, silver catheter)")
    print("   • Device-biologic combinations: 2 (collagen matrix, cell scaffold)")
    print("   • Drug-device-biologic: 1 (complex fusion product)")
    print("   • Standard devices: 1 (bare metal stent)")
    print("\n🎯 KEY CAPABILITIES DEMONSTRATED:")
    print("   ✅ Drug-device detection (HIGH/MEDIUM confidence)")
    print("   ✅ Device-biologic detection (cell-based vs acellular)")
    print("   ✅ RHO assignment per 21 CFR Part 3")
    print("   ✅ PMOA-based regulatory pathway determination")
    print("   ✅ OCP RFD recommendation for complex products")
    print("   ✅ Exclusion logic (drug-free devices)")
    print("\n📚 FDA REFERENCES:")
    print("   • 21 CFR Part 3 - Product Jurisdiction")
    print("   • 21 CFR 3.7 - Request for Designation (RFD)")
    print("   • FDA Guidance (2011): Classification of Products as Drugs and Devices")
    print("   • FDA Guidance (2013): Premarket Assessment of Combination Products")
    print("\n✨ For production use, integrate via:")
    print("   /fda:draft device-description --project YOUR_PROJECT")
    print("   (Auto-detects combination products and generates Section 15)")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    main()
