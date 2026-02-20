"""
Test Data Generation for End-to-End Tests
=========================================

Provides realistic test data generation for various scenarios:
- Device profiles (Class I, II, III)
- Predicate devices
- FDA clearances and recalls
- Standards and regulations
- Clinical data
- Safety data

Version: 1.0.0
Date: 2026-02-20
Issue: FDA-186
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random


# =============================================================================
# Device Profile Generators
# =============================================================================

def generate_device_profile(
    product_code: str = "DQY",
    device_class: str = "II",
    device_type: str = "cardiovascular",
    include_software: bool = False,
    combination_product: bool = False
) -> Dict[str, Any]:
    """Generate comprehensive device profile for testing.
    
    Args:
        product_code: FDA product code
        device_class: Device classification (I, II, III)
        device_type: Device type category
        include_software: Include software/SaMD characteristics
        combination_product: Include drug/biologic components
        
    Returns:
        Complete device profile dict
    """
    profile = {
        "device_info": {
            "product_code": product_code,
            "device_class": device_class,
            "trade_name": f"Test {device_type.title()} Device",
            "common_name": f"{device_type.title()} Medical Device",
            "regulation_number": _get_regulation_number(product_code, device_class),
            "review_panel": _get_review_panel(device_type)
        },
        "intended_use": f"For use in {device_type} applications for diagnostic and therapeutic purposes",
        "indications_for_use": f"Indicated for use in adult patients requiring {device_type} intervention",
        "device_description": _generate_device_description(device_type, include_software),
        "technological_characteristics": _generate_tech_characteristics(
            device_type, include_software, combination_product
        ),
        "standards": _generate_applicable_standards(device_type, include_software),
        "materials": _generate_materials(device_type),
        "sterilization": _generate_sterilization_info(device_type)
    }
    
    if include_software:
        profile["software_characteristics"] = _generate_software_characteristics()
    
    if combination_product:
        profile["combination_characteristics"] = _generate_combination_characteristics()
    
    return profile


def _get_regulation_number(product_code: str, device_class: str) -> str:
    """Get CFR regulation number based on product code."""
    class_map = {
        "I": "807.87",
        "II": "807.85", 
        "III": "814.20"
    }
    base_cfr = "21 CFR"
    
    # Product code specific mappings
    if product_code.startswith("D"):
        return f"{base_cfr} 870.{class_map.get(device_class, '1200')}"
    elif product_code.startswith("O"):
        return f"{base_cfr} 888.{class_map.get(device_class, '3000')}"
    else:
        return f"{base_cfr} {class_map.get(device_class, '807.87')}"


def _get_review_panel(device_type: str) -> str:
    """Get FDA review panel code based on device type."""
    panel_map = {
        "cardiovascular": "CV",
        "orthopedic": "OR",
        "neurological": "NE",
        "ophthalmic": "OP",
        "general": "GU",
        "radiology": "RA"
    }
    return panel_map.get(device_type.lower(), "GU")


def _generate_device_description(device_type: str, include_software: bool) -> str:
    """Generate device description text."""
    base_desc = f"A sterile, single-use {device_type} device designed for diagnostic and therapeutic applications. "
    
    if include_software:
        base_desc += "The device includes integrated software for data acquisition, processing, and analysis. "
    
    base_desc += "The device consists of biocompatible materials suitable for patient contact."
    
    return base_desc


def _generate_tech_characteristics(
    device_type: str,
    include_software: bool,
    combination_product: bool
) -> Dict[str, Any]:
    """Generate technological characteristics."""
    chars = {
        "materials": _generate_materials(device_type),
        "sterilization_method": "EO",
        "shelf_life_months": 36,
        "single_use": True,
        "latex_free": True,
        "dehp_free": True
    }
    
    if include_software:
        chars["software_level"] = "Moderate"
        chars["cybersecurity_required"] = True
    
    if combination_product:
        chars["combination_type"] = "drug_device"
        chars["drug_component"] = "Heparin coating"
    
    return chars


def _generate_materials(device_type: str) -> List[str]:
    """Generate list of device materials."""
    common_materials = ["Polyurethane", "Stainless Steel 316L", "Silicone"]
    
    type_specific = {
        "cardiovascular": ["Nitinol", "PTFE"],
        "orthopedic": ["Titanium Alloy", "PEEK", "UHMWPE"],
        "neurological": ["Platinum-Iridium"],
        "ophthalmic": ["PMMA", "Acrylic"]
    }
    
    materials = common_materials.copy()
    if device_type in type_specific:
        materials.extend(type_specific[device_type])
    
    return materials[:4]  # Limit to 4 materials


def _generate_sterilization_info(device_type: str) -> Dict[str, Any]:
    """Generate sterilization information."""
    return {
        "method": "EO",
        "standard": "ISO 11135",
        "validated": True,
        "residuals_tested": True
    }


def _generate_applicable_standards(
    device_type: str,
    include_software: bool
) -> List[Dict[str, Any]]:
    """Generate list of applicable standards."""
    standards = [
        {
            "standard_id": "ISO 10993-1",
            "title": "Biological evaluation of medical devices - Part 1",
            "consensus": True,
            "category": "Biocompatibility"
        },
        {
            "standard_id": "ISO 11135",
            "title": "Sterilization of health care products - Ethylene oxide",
            "consensus": True,
            "category": "Sterilization"
        }
    ]
    
    # Device type specific standards
    if device_type == "cardiovascular":
        standards.append({
            "standard_id": "ISO 10555-1",
            "title": "Intravascular catheters - Sterile and single-use catheters",
            "consensus": True,
            "category": "Device Specific"
        })
    
    if include_software:
        standards.extend([
            {
                "standard_id": "IEC 62304",
                "title": "Medical device software - Software life cycle processes",
                "consensus": True,
                "category": "Software"
            },
            {
                "standard_id": "IEC 62366-1",
                "title": "Medical devices - Application of usability engineering",
                "consensus": True,
                "category": "Human Factors"
            }
        ])
    
    return standards


def _generate_software_characteristics() -> Dict[str, Any]:
    """Generate software characteristics for SaMD devices."""
    return {
        "software_level": "Moderate",
        "samd_classification": "Class II",
        "software_version": "1.0.0",
        "programming_language": "C++",
        "operating_system": "Embedded Linux",
        "cybersecurity": {
            "encryption": "AES-256",
            "authentication": "Role-based access control",
            "audit_logging": True
        },
        "algorithms": [
            {
                "name": "Signal Processing Algorithm",
                "purpose": "Filter and analyze sensor data",
                "validation_status": "Validated"
            }
        ]
    }


def _generate_combination_characteristics() -> Dict[str, Any]:
    """Generate combination product characteristics."""
    return {
        "combination_type": "drug_device",
        "drug_component": {
            "name": "Heparin Sodium",
            "purpose": "Anticoagulant coating",
            "amount": "100 USP units per device"
        },
        "lead_center": "CDRH",
        "rld_designation": "Device-led combination product"
    }


# =============================================================================
# Predicate Device Generators
# =============================================================================

def generate_predicates(
    count: int = 3,
    product_code: str = "DQY",
    base_year: int = 2023
) -> List[Dict[str, Any]]:
    """Generate list of predicate devices.
    
    Args:
        count: Number of predicates to generate
        product_code: Product code for predicates
        base_year: Base year for K-numbers
        
    Returns:
        List of predicate device dicts
    """
    predicates = []
    
    for i in range(count):
        year = base_year - i
        k_number = f"K{str(year)[-2:]}{random.randint(1000, 9999)}"
        
        predicate = {
            "k_number": k_number,
            "device_name": f"Predicate Device {i+1}",
            "applicant": f"Manufacturer {chr(65 + i)} Inc",
            "decision_date": f"{year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "decision_description": "Substantially Equivalent (SE)",
            "product_code": product_code,
            "review_advisory_committee": _get_review_panel("cardiovascular"),
            "statement": "Device is substantially equivalent to predicate",
            "similarity_score": round(0.95 - (i * 0.05), 2),
            "accepted": True,
            "ranking": i + 1
        }
        
        predicates.append(predicate)
    
    return predicates


# =============================================================================
# FDA API Response Generators
# =============================================================================

def generate_fda_clearance_response(
    product_code: str = "DQY",
    count: int = 10,
    start_year: int = 2024
) -> Dict[str, Any]:
    """Generate mock FDA clearance API response.
    
    Args:
        product_code: Product code to query
        count: Number of clearances to generate
        start_year: Starting year for clearances
        
    Returns:
        FDA API response dict
    """
    results = []
    
    for i in range(count):
        # Generate K-number
        year_offset = i // 100
        year = start_year - year_offset
        k_num = f"K{str(year)[-2:]}{1000 + i:04d}"
        
        # Generate decision date
        days_offset = i * 10
        decision_date = (
            datetime(year, 1, 1) + timedelta(days=days_offset)
        ).strftime("%Y-%m-%d")
        
        clearance = {
            "k_number": k_num,
            "device_name": f"Test Device {i+1}",
            "applicant": f"Test Manufacturer {chr(65 + (i % 26))}",
            "decision_date": decision_date,
            "decision_description": "Substantially Equivalent (SE)",
            "product_code": product_code,
            "review_advisory_committee": _get_review_panel("cardiovascular"),
            "third_party_flag": "N" if i % 5 != 0 else "Y",
            "expedited_review_flag": "N" if i % 10 != 0 else "Y"
        }
        
        results.append(clearance)
    
    return {
        "meta": {
            "disclaimer": "Do not rely on openFDA to make decisions regarding medical care.",
            "license": "https://open.fda.gov/license/",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "results": {
                "skip": 0,
                "limit": count,
                "total": count
            }
        },
        "results": results
    }


def generate_fda_recall_response(
    product_code: str = "DQY",
    count: int = 5
) -> Dict[str, Any]:
    """Generate mock FDA recall API response.
    
    Args:
        product_code: Product code
        count: Number of recalls to generate
        
    Returns:
        FDA recall API response dict
    """
    results = []
    
    for i in range(count):
        recall = {
            "product_code": product_code,
            "recall_number": f"Z-{2024 - i}-{random.randint(1000, 9999)}",
            "recall_initiation_date": f"{2024 - i}-{random.randint(1, 12):02d}-01",
            "classification": ["Class I", "Class II", "Class III"][i % 3],
            "status": "Ongoing" if i < 2 else "Completed",
            "reason_for_recall": f"Potential safety issue {i+1}",
            "product_description": f"Recalled device {i+1}"
        }
        
        results.append(recall)
    
    return {
        "meta": {
            "results": {
                "skip": 0,
                "limit": count,
                "total": count
            }
        },
        "results": results
    }


# =============================================================================
# Test Scenario Generators
# =============================================================================

def generate_510k_workflow_data(
    scenario: str = "traditional"
) -> Dict[str, Any]:
    """Generate complete data set for 510(k) workflow test.
    
    Args:
        scenario: Workflow scenario (traditional, special, abbreviated)
        
    Returns:
        Dict with all required test data
    """
    include_software = scenario in ["special", "samd"]
    combination = scenario == "combination"
    
    return {
        "device_profile": generate_device_profile(
            product_code="DQY",
            device_class="II",
            device_type="cardiovascular",
            include_software=include_software,
            combination_product=combination
        ),
        "predicates": generate_predicates(count=3, product_code="DQY"),
        "fda_clearances": generate_fda_clearance_response(product_code="DQY", count=50),
        "fda_recalls": generate_fda_recall_response(product_code="DQY", count=3),
        "scenario_type": scenario
    }


def generate_edge_case_data(edge_case: str) -> Dict[str, Any]:
    """Generate data for edge case scenarios.
    
    Args:
        edge_case: Edge case type (sparse_data, class_u, samd, combination)
        
    Returns:
        Edge case test data
    """
    if edge_case == "sparse_data":
        return {
            "device_profile": generate_device_profile(product_code="GEI"),
            "predicates": [],  # No predicates found
            "fda_clearances": generate_fda_clearance_response(count=2),  # Very few
            "fda_recalls": generate_fda_recall_response(count=0)  # No recalls
        }
    
    elif edge_case == "class_u":
        profile = generate_device_profile(device_class="U", combination_product=True)
        profile["device_info"]["regulation_number"] = "21 CFR 807.92(a)(N)"
        return {
            "device_profile": profile,
            "predicates": generate_predicates(count=1),
            "fda_clearances": generate_fda_clearance_response(count=10)
        }
    
    elif edge_case == "samd":
        return {
            "device_profile": generate_device_profile(
                product_code="QKQ",
                include_software=True
            ),
            "predicates": generate_predicates(count=2, product_code="QKQ"),
            "fda_clearances": generate_fda_clearance_response(product_code="QKQ", count=25)
        }
    
    elif edge_case == "combination":
        return {
            "device_profile": generate_device_profile(
                product_code="FRO",
                combination_product=True
            ),
            "predicates": generate_predicates(count=2, product_code="FRO"),
            "fda_clearances": generate_fda_clearance_response(product_code="FRO", count=15)
        }
    
    return {}
