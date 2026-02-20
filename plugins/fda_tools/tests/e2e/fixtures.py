"""
Shared Fixtures for End-to-End Tests
====================================

Provides reusable fixtures for E2E test scenarios including:
- Temporary project environments
- Sample device data
- Mock API clients
- Configuration templates
- Test data generators

Usage:
    from tests.e2e.fixtures import e2e_project, sample_device_data

Version: 1.0.0
Date: 2026-02-20
Issue: FDA-186
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
import pytest


# =============================================================================
# Test Data Templates
# =============================================================================

def get_sample_device_profile(product_code: str = "DQY", device_class: str = "II") -> Dict[str, Any]:
    """Generate sample device profile for testing.
    
    Args:
        product_code: FDA product code
        device_class: Device classification (I, II, III)
        
    Returns:
        Dict containing device profile structure
    """
    return {
        "device_info": {
            "product_code": product_code,
            "device_class": device_class,
            "trade_name": f"Test Device {product_code}",
            "common_name": "Test Medical Device",
            "regulation_number": "21 CFR 870.1200",
            "review_panel": "CV" if product_code == "DQY" else "GU"
        },
        "intended_use": "For diagnostic testing in cardiovascular applications",
        "indications_for_use": "Indicated for use in adult patients with suspected cardiovascular conditions",
        "device_description": "A sterile, single-use diagnostic catheter system",
        "technological_characteristics": {
            "materials": ["Polyurethane", "Stainless Steel"],
            "sterilization_method": "EO",
            "shelf_life_months": 36,
            "single_use": True
        },
        "standards": [
            {
                "standard_id": "ISO 10993-1",
                "title": "Biological evaluation of medical devices",
                "consensus": True
            },
            {
                "standard_id": "ISO 11135",
                "title": "Sterilization of health care products - Ethylene oxide",
                "consensus": True
            }
        ]
    }


def get_sample_predicate_data(k_number: str = "K123456") -> Dict[str, Any]:
    """Generate sample predicate device data.
    
    Args:
        k_number: K-number for predicate device
        
    Returns:
        Dict containing predicate device data
    """
    return {
        "k_number": k_number,
        "device_name": "Predicate Device Name",
        "applicant": "Test Manufacturer Inc",
        "decision_date": "2024-01-15",
        "decision_description": "Substantially Equivalent (SE)",
        "product_code": "DQY",
        "review_advisory_committee": "CV",
        "statement": "This device is substantially equivalent to the predicate"
    }


def get_sample_review_data() -> Dict[str, Any]:
    """Generate sample review.json data.
    
    Returns:
        Dict containing review data structure
    """
    return {
        "predicates": [
            {
                "k_number": "K123456",
                "device_name": "Primary Predicate",
                "similarity_score": 0.92,
                "accepted": True,
                "ranking": 1
            },
            {
                "k_number": "K234567",
                "device_name": "Secondary Predicate",
                "similarity_score": 0.85,
                "accepted": True,
                "ranking": 2
            }
        ],
        "review_scores": {
            "overall_similarity": 0.88,
            "technological_similarity": 0.90,
            "clinical_similarity": 0.85
        },
        "review_date": "2024-02-15",
        "reviewer": "automated"
    }


def get_sample_standards_lookup() -> List[Dict[str, Any]]:
    """Generate sample standards_lookup.json data.
    
    Returns:
        List of applicable standards
    """
    return [
        {
            "standard_id": "ISO 10993-1",
            "title": "Biological evaluation of medical devices - Part 1: Evaluation and testing",
            "recognized": True,
            "category": "Biocompatibility"
        },
        {
            "standard_id": "ISO 11135",
            "title": "Sterilization of health care products - Ethylene oxide",
            "recognized": True,
            "category": "Sterilization"
        },
        {
            "standard_id": "IEC 60601-1",
            "title": "Medical electrical equipment - Part 1: General requirements",
            "recognized": True,
            "category": "Electrical Safety"
        }
    ]


# =============================================================================
# Project Environment Fixtures
# =============================================================================

class E2ETestProject:
    """Context manager for temporary E2E test project environments.
    
    Creates isolated project directory with proper structure and cleanup.
    
    Usage:
        with E2ETestProject("test_510k") as project_dir:
            # Run tests
            pass
    """
    
    def __init__(self, project_name: str = "e2e_test_project"):
        """Initialize test project.
        
        Args:
            project_name: Name for the test project
        """
        self.project_name = project_name
        self.temp_dir = None
        self.project_path = None
        
    def __enter__(self) -> Path:
        """Create temporary project directory.
        
        Returns:
            Path to project directory
        """
        self.temp_dir = tempfile.mkdtemp(prefix=f"fda_e2e_{self.project_name}_")
        self.project_path = Path(self.temp_dir)
        
        # Create standard project structure
        (self.project_path / "data").mkdir(exist_ok=True)
        (self.project_path / "draft").mkdir(exist_ok=True)
        (self.project_path / "reports").mkdir(exist_ok=True)
        (self.project_path / "safety_cache").mkdir(exist_ok=True)
        
        return self.project_path
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary project directory."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)


@pytest.fixture
def e2e_project():
    """Pytest fixture providing temporary E2E test project.
    
    Yields:
        Path to temporary project directory
    """
    with E2ETestProject() as project_dir:
        yield project_dir


@pytest.fixture
def e2e_project_with_device_profile(e2e_project):
    """Pytest fixture providing project with device_profile.json.
    
    Yields:
        Path to project directory with device_profile.json
    """
    device_profile = get_sample_device_profile()
    profile_path = e2e_project / "device_profile.json"
    
    with open(profile_path, 'w') as f:
        json.dump(device_profile, f, indent=2)
        
    yield e2e_project


@pytest.fixture
def e2e_project_complete(e2e_project):
    """Pytest fixture providing fully populated test project.
    
    Includes:
        - device_profile.json
        - review.json
        - standards_lookup.json
        - Predicate data files
    
    Yields:
        Path to complete project directory
    """
    # Device profile
    device_profile = get_sample_device_profile()
    with open(e2e_project / "device_profile.json", 'w') as f:
        json.dump(device_profile, f, indent=2)
    
    # Review data
    review_data = get_sample_review_data()
    with open(e2e_project / "review.json", 'w') as f:
        json.dump(review_data, f, indent=2)
    
    # Standards
    standards_data = get_sample_standards_lookup()
    with open(e2e_project / "standards_lookup.json", 'w') as f:
        json.dump(standards_data, f, indent=2)
    
    # Predicate data files
    data_dir = e2e_project / "data"
    for i, pred in enumerate(review_data["predicates"], 1):
        pred_data = get_sample_predicate_data(pred["k_number"])
        pred_file = data_dir / f"predicate_{i}_{pred['k_number']}.json"
        with open(pred_file, 'w') as f:
            json.dump(pred_data, f, indent=2)
    
    yield e2e_project


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_device_data():
    """Fixture providing sample device profile data.
    
    Returns:
        Dict with device profile
    """
    return get_sample_device_profile()


@pytest.fixture
def sample_predicate_data():
    """Fixture providing sample predicate device data.
    
    Returns:
        Dict with predicate data
    """
    return get_sample_predicate_data()


@pytest.fixture
def sample_review_data():
    """Fixture providing sample review data.
    
    Returns:
        Dict with review data
    """
    return get_sample_review_data()


@pytest.fixture
def sample_standards_data():
    """Fixture providing sample standards data.
    
    Returns:
        List of standards dicts
    """
    return get_sample_standards_lookup()


# =============================================================================
# Test Data Generators
# =============================================================================

def generate_test_k_numbers(count: int = 5, base_year: int = 2024) -> List[str]:
    """Generate list of test K-numbers.
    
    Args:
        count: Number of K-numbers to generate
        base_year: Starting year (last 2 digits used)
        
    Returns:
        List of K-number strings
    """
    year_suffix = str(base_year)[-2:]
    return [f"K{year_suffix}{i:04d}" for i in range(1000, 1000 + count)]


def generate_api_response(
    total_count: int,
    result_items: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """Generate mock FDA API response structure.
    
    Args:
        total_count: Total results count
        result_items: List of result items (or None for empty)
        
    Returns:
        Dict with API response structure
    """
    return {
        "meta": {
            "disclaimer": "Do not rely on openFDA to make decisions regarding medical care.",
            "license": "https://open.fda.gov/license/",
            "last_updated": "2024-02-15",
            "results": {
                "skip": 0,
                "limit": 100,
                "total": total_count
            }
        },
        "results": result_items or []
    }


@pytest.fixture
def test_k_numbers():
    """Fixture providing list of test K-numbers.
    
    Returns:
        List of 5 test K-numbers
    """
    return generate_test_k_numbers(5)


@pytest.fixture  
def mock_api_response():
    """Fixture providing mock API response generator.
    
    Returns:
        Function to generate API responses
    """
    return generate_api_response
