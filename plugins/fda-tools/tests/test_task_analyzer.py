#!/usr/bin/env python3
"""
Tests for TaskAnalyzer - AI-powered task classification

Tests cover:
1. Language detection (Python, TypeScript, JavaScript, Rust, Go, etc.)
2. Framework detection (React, FastAPI, Django, Spring, etc.)
3. Domain identification (healthcare, fintech, blockchain, API, etc.)
4. Review dimension scoring
5. Complexity estimation
6. Linear metadata extraction
"""

import pytest
from task_analyzer import TaskAnalyzer, TaskProfile


class TestLanguageDetection:
    """Test language detection from task descriptions and file paths."""

    def setup_method(self):
        self.analyzer = TaskAnalyzer()

    def test_python_detection(self):
        task = "Fix authentication bug in FastAPI endpoint"
        profile = self.analyzer.analyze_task(task, {"files": ["api/auth.py"]})
        assert "python" in profile.languages

    def test_typescript_detection(self):
        task = "Add React component for user profile"
        profile = self.analyzer.analyze_task(task, {"files": ["components/UserProfile.tsx"]})
        assert "typescript" in profile.languages

    def test_javascript_detection(self):
        task = "Fix validation in Node.js server"
        profile = self.analyzer.analyze_task(task, {"files": ["server.js"]})
        assert "javascript" in profile.languages

    def test_rust_detection(self):
        task = "Optimize performance in Rust backend"
        profile = self.analyzer.analyze_task(task, {"files": ["src/main.rs"]})
        assert "rust" in profile.languages

    def test_go_detection(self):
        task = "Implement Go microservice for payments"
        profile = self.analyzer.analyze_task(task, {"files": ["payment/handler.go"]})
        assert "go" in profile.languages

    def test_multiple_languages(self):
        task = "Full stack feature with TypeScript frontend and Python backend"
        profile = self.analyzer.analyze_task(task, {"files": ["api/auth.py", "components/Login.tsx"]})
        assert "python" in profile.languages
        assert "typescript" in profile.languages


class TestFrameworkDetection:
    """Test framework detection from task descriptions."""

    def setup_method(self):
        self.analyzer = TaskAnalyzer()

    def test_react_detection(self):
        task = "Add React component with hooks"
        profile = self.analyzer.analyze_task(task, {})
        assert "react" in profile.frameworks

    def test_fastapi_detection(self):
        task = "Build FastAPI endpoint for user registration"
        profile = self.analyzer.analyze_task(task, {})
        assert "fastapi" in profile.frameworks

    def test_django_detection(self):
        task = "Create Django REST framework serializer"
        profile = self.analyzer.analyze_task(task, {})
        assert "django" in profile.frameworks

    def test_spring_detection(self):
        task = "Implement Spring Boot microservice"
        profile = self.analyzer.analyze_task(task, {})
        assert "spring" in profile.frameworks


class TestDomainIdentification:
    """Test domain identification from task descriptions."""

    def setup_method(self):
        self.analyzer = TaskAnalyzer()

    def test_healthcare_domain(self):
        task = "FDA 510(k) submission validation for medical device"
        profile = self.analyzer.analyze_task(task, {})
        assert "healthcare" in profile.domains or "fda" in profile.domains

    def test_fintech_domain(self):
        task = "Implement payment processing with PCI compliance"
        profile = self.analyzer.analyze_task(task, {})
        assert "fintech" in profile.domains or "payment" in profile.domains

    def test_blockchain_domain(self):
        task = "Smart contract audit for Ethereum DApp"
        profile = self.analyzer.analyze_task(task, {})
        assert "blockchain" in profile.domains

    def test_api_domain(self):
        task = "REST API design and documentation"
        profile = self.analyzer.analyze_task(task, {})
        assert "api" in profile.domains


class TestDimensionScoring:
    """Test review dimension scoring heuristics."""

    def setup_method(self):
        self.analyzer = TaskAnalyzer()

    def test_security_dimension_high(self):
        task = "Fix SQL injection vulnerability in authentication endpoint"
        profile = self.analyzer.analyze_task(task, {})
        assert profile.review_dimensions.get("security", 0) > 0.7

    def test_testing_dimension_high(self):
        task = "Add comprehensive test coverage for user service"
        profile = self.analyzer.analyze_task(task, {})
        assert profile.review_dimensions.get("testing", 0) > 0.7

    def test_performance_dimension_high(self):
        task = "Optimize slow database queries and reduce latency"
        profile = self.analyzer.analyze_task(task, {})
        assert profile.review_dimensions.get("performance", 0) > 0.7

    def test_documentation_dimension_high(self):
        task = "Write comprehensive API documentation with examples"
        profile = self.analyzer.analyze_task(task, {})
        assert profile.review_dimensions.get("documentation", 0) > 0.7

    def test_code_quality_dimension_present(self):
        task = "Refactor legacy code to improve maintainability"
        profile = self.analyzer.analyze_task(task, {})
        assert profile.review_dimensions.get("code_quality", 0) > 0.5


class TestComplexityEstimation:
    """Test complexity estimation logic."""

    def setup_method(self):
        self.analyzer = TaskAnalyzer()

    def test_low_complexity_single_file(self):
        task = "Fix typo in README"
        profile = self.analyzer.analyze_task(task, {"files": ["README.md"]})
        assert profile.complexity in ["low", "trivial"]

    def test_medium_complexity_multiple_files(self):
        task = "Add validation to user registration flow"
        profile = self.analyzer.analyze_task(task, {"files": ["api/auth.py", "models/user.py", "validators.py"]})
        assert profile.complexity in ["medium", "low"]

    def test_high_complexity_many_files(self):
        task = "Redesign authentication system with OAuth2"
        context = {"files": [f"auth/file{i}.py" for i in range(10)]}
        profile = self.analyzer.analyze_task(task, context)
        assert profile.complexity in ["high", "critical", "medium"]


class TestTaskTypeClassification:
    """Test task type classification."""

    def setup_method(self):
        self.analyzer = TaskAnalyzer()

    def test_security_audit_type(self):
        task = "Security audit of authentication system"
        profile = self.analyzer.analyze_task(task, {})
        assert profile.task_type == "security_audit"

    def test_bug_fix_type(self):
        task = "Fix null pointer exception in payment handler"
        profile = self.analyzer.analyze_task(task, {})
        assert profile.task_type == "bug_fix"

    def test_feature_development_type(self):
        task = "Implement new user dashboard with analytics"
        profile = self.analyzer.analyze_task(task, {})
        assert profile.task_type in ["feature_dev", "feature_development"]

    def test_refactoring_type(self):
        task = "Refactor legacy codebase to modern patterns"
        profile = self.analyzer.analyze_task(task, {})
        assert profile.task_type == "refactoring"

    def test_documentation_type(self):
        task = "Write API documentation and usage examples"
        profile = self.analyzer.analyze_task(task, {})
        assert profile.task_type == "documentation"


class TestLinearMetadataExtraction:
    """Test Linear issue metadata extraction."""

    def setup_method(self):
        self.analyzer = TaskAnalyzer()

    def test_extract_from_linear_issue(self):
        linear_issue = {
            "title": "[SECURITY] Fix XSS vulnerability",
            "description": "Authentication endpoint has XSS vulnerability in user input validation",
            "labels": [{"name": "security"}, {"name": "high-priority"}],
        }
        profile = self.analyzer.extract_linear_metadata(linear_issue)

        assert profile.task_type in ["security_audit", "bug_fix", "security"]
        assert profile.review_dimensions.get("security", 0) > 0.5

    def test_extract_languages_from_description(self):
        linear_issue = {
            "title": "Add TypeScript types",
            "description": "Add proper TypeScript type definitions to React components",
            "labels": [],
        }
        profile = self.analyzer.extract_linear_metadata(linear_issue)

        assert "typescript" in profile.languages

    def test_extract_keywords_from_title(self):
        linear_issue = {
            "title": "Performance optimization for database queries",
            "description": "Slow queries need optimization",
            "labels": [],
        }
        profile = self.analyzer.extract_linear_metadata(linear_issue)

        assert "performance" in profile.keywords or "optimization" in profile.keywords


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
