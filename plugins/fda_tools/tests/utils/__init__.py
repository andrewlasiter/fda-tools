"""
Test utilities package for FDA Tools E2E testing.

Provides comprehensive helper modules for:
- E2E workflow testing (e2e_helpers.py)
- Regulatory compliance validation (regulatory_validators.py)
- Test data factories and fixtures
- Mock objects and API simulators

Version: 1.0.0
Date: 2026-02-20
Issue: FDA-174 (QA-001)
"""

from .e2e_helpers import (
    E2EWorkflowRunner,
    E2EAssertions,
    E2EDataManager,
    WorkflowStage,
    WorkflowResult,
)

from .regulatory_validators import (
    RegulatoryValidator,
    CFRValidator,
    EStarValidator,
    PredicateValidator,
    SubstantialEquivalenceValidator,
    ValidationResult,
    ValidationSeverity,
)

__all__ = [
    # E2E Helpers
    "E2EWorkflowRunner",
    "E2EAssertions",
    "E2EDataManager",
    "WorkflowStage",
    "WorkflowResult",
    # Regulatory Validators
    "RegulatoryValidator",
    "CFRValidator",
    "EStarValidator",
    "PredicateValidator",
    "SubstantialEquivalenceValidator",
    "ValidationResult",
    "ValidationSeverity",
]
