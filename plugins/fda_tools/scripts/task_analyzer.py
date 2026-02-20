#!/usr/bin/env python3
"""
Task Analyzer - AI-powered task classification for agent selection

Analyzes task descriptions and contexts to generate multi-dimensional
task profiles used for optimal agent team selection.

Key capabilities:
  1. Language and framework detection
  2. Domain identification (healthcare, fintech, blockchain, etc.)
  3. Multi-dimensional review scoring (security, testing, performance, etc.)
  4. Complexity estimation
  5. Linear issue metadata extraction

Usage:
    from task_analyzer import TaskAnalyzer

    analyzer = TaskAnalyzer()

    # Analyze a task description
    profile = analyzer.analyze_task(
        "Fix authentication vulnerability in FastAPI endpoint",
        {"files": ["api/auth.py"]}
    )

    # Extract metadata from Linear issue
    profile = analyzer.extract_linear_metadata(linear_issue_dict)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Task Profile Data Structure
# ------------------------------------------------------------------

@dataclass
class TaskProfile:
    """Multi-dimensional profile of a task for agent selection.

    Attributes:
        task_type: Type of task (code_review, feature_dev, bug_fix, etc.)
        languages: Detected programming languages
        frameworks: Detected frameworks
        domains: Business/technical domains
        review_dimensions: Importance scores (0-1) for each review dimension
        complexity: Complexity level (low, medium, high, critical)
        estimated_scope: Time scope estimate (hours, days, weeks)
        critical_files: Files mentioned in the task
        keywords: Extracted keywords
        raw_description: Original task description
    """
    task_type: str = "unknown"
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    review_dimensions: Dict[str, float] = field(default_factory=dict)
    complexity: str = "medium"
    estimated_scope: str = "hours"
    critical_files: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    raw_description: str = ""


# ------------------------------------------------------------------
# Pattern Definitions for Detection
# ------------------------------------------------------------------

# Language detection patterns
LANGUAGE_PATTERNS = {
    "python": [r"\bpython\b", r"\.py\b", r"\bpytest\b", r"\bdjango\b", r"\bflask\b", r"\bfastapi\b"],
    "typescript": [r"\btypescript\b", r"\.ts\b", r"\.tsx\b"],
    "javascript": [r"\bjavascript\b", r"\.js\b", r"\.jsx\b", r"\bnode\.js\b", r"\bnpm\b"],
    "rust": [r"\brust\b", r"\.rs\b", r"\bcargo\b"],
    "go": [r"\bgolang\b", r"\bgo\b", r"\.go\b"],
    "java": [r"\bjava\b", r"\.java\b", r"\bspring\b", r"\bmaven\b", r"\bgradle\b"],
    "csharp": [r"\bc#\b", r"\bcsharp\b", r"\.cs\b", r"\b\.net\b", r"\basp\.net\b"],
    "cpp": [r"\bc\+\+\b", r"\.cpp\b", r"\.h\b", r"\.hpp\b"],
    "sql": [r"\bsql\b", r"\bpostgres\b", r"\bmysql\b", r"\.sql\b"],
    "bash": [r"\bbash\b", r"\.sh\b", r"\bshell\b"],
    "powershell": [r"\bpowershell\b", r"\.ps1\b"],
}

# Framework detection patterns
FRAMEWORK_PATTERNS = {
    "react": [r"\breact\b", r"\bjsx\b", r"\btsx\b"],
    "vue": [r"\bvue\b", r"\bvuex\b", r"\bnuxt\b"],
    "angular": [r"\bangular\b", r"\btypescript\b.*\bcomponent\b"],
    "fastapi": [r"\bfastapi\b", r"\bpydantic\b"],
    "django": [r"\bdjango\b", r"\bdrf\b"],
    "flask": [r"\bflask\b"],
    "express": [r"\bexpress\b", r"\bnode\.js\b"],
    "spring": [r"\bspring\b", r"\bspring boot\b"],
    "dotnet": [r"\b\.net\b", r"\basp\.net\b"],
}

# Domain detection patterns
DOMAIN_PATTERNS = {
    "healthcare": [r"\bhealthcare\b", r"\bfda\b", r"\bhipaa\b", r"\bmedical\b", r"\b510\(k\)\b", r"\bpma\b"],
    "fintech": [r"\bfintech\b", r"\bpayment\b", r"\bbanking\b", r"\bpci\b"],
    "blockchain": [r"\bblockchain\b", r"\bcrypto\b", r"\bweb3\b", r"\bsmart contract\b"],
    "api": [r"\bapi\b", r"\brest\b", r"\bgraphql\b", r"\bendpoint\b"],
    "frontend": [r"\bfrontend\b", r"\bui\b", r"\bux\b"],
    "backend": [r"\bbackend\b", r"\bserver\b", r"\bdatabase\b"],
}

# Task type patterns
TASK_TYPE_PATTERNS = {
    "security_audit": [r"\bsecurity\b", r"\bvulnerability\b", r"\bpenetration\b", r"\baudit\b"],
    "code_review": [r"\breview\b", r"\bcode quality\b", r"\brefactor\b"],
    "bug_fix": [r"\bbug\b", r"\bfix\b", r"\berror\b", r"\bissue\b"],
    "feature_dev": [r"\bfeature\b", r"\bimplement\b", r"\badd\b", r"\bnew\b"],
    "testing": [r"\btest\b", r"\bcoverage\b", r"\bqa\b"],
    "documentation": [r"\bdocs\b", r"\bdocumentation\b", r"\breadme\b"],
    "refactoring": [r"\brefactor\b", r"\bcleanup\b", r"\brestructure\b"],
    "deployment": [r"\bdeploy\b", r"\bci\/cd\b", r"\bpipeline\b"],
}

# Review dimension keyword patterns
DIMENSION_KEYWORDS = {
    "security": [
        "authentication", "authorization", "encryption", "vulnerability",
        "XXE", "injection", "CSRF", "XSS", "SQL injection",
        "penetration", "audit", "security", "credentials", "secrets",
    ],
    "testing": [
        "test", "coverage", "pytest", "unittest", "e2e", "integration",
        "test suite", "QA", "test automation", "mock", "stub",
    ],
    "performance": [
        "slow", "optimization", "latency", "bottleneck", "memory leak",
        "performance", "speed", "caching", "database optimization",
    ],
    "documentation": [
        "readme", "docs", "API documentation", "comments", "docstring",
        "documentation", "guide", "tutorial", "reference",
    ],
    "code_quality": [
        "refactor", "cleanup", "code quality", "best practices", "lint",
        "code review", "maintainability", "readability", "DRY", "SOLID",
    ],
    "compliance": [
        "compliance", "regulatory", "audit", "FDA", "HIPAA", "GDPR",
        "PCI DSS", "SOC 2", "ISO", "CFR", "regulation",
    ],
    "architecture": [
        "architecture", "design", "pattern", "microservices", "monolith",
        "system design", "scalability", "distributed", "infrastructure",
    ],
    "operations": [
        "deploy", "CI/CD", "pipeline", "DevOps", "infrastructure",
        "monitoring", "logging", "incident", "production", "ops",
    ],
}


# ------------------------------------------------------------------
# Task Analyzer
# ------------------------------------------------------------------

class TaskAnalyzer:
    """AI-powered task analysis for agent selection.

    Analyzes task descriptions and contexts to generate multi-dimensional
    task profiles including language detection, framework identification,
    domain classification, and review dimension scoring.
    """

    def __init__(self):
        """Initialize the task analyzer."""
        pass

    def analyze_task(
        self,
        task_description: str,
        task_context: Optional[Dict] = None
    ) -> TaskProfile:
        """Analyze a task and generate a multi-dimensional profile.

        Args:
            task_description: Task description text
            task_context: Optional context dict with keys like:
                - files: List of file paths
                - labels: List of labels/tags
                - comments: List of comment strings

        Returns:
            TaskProfile with detected languages, frameworks, domains,
            and review dimension importance scores.
        """
        if task_context is None:
            task_context = {}

        # Combine description and context for analysis
        combined_text = task_description.lower()
        if task_context.get("files"):
            combined_text += " " + " ".join(task_context["files"]).lower()
        if task_context.get("labels"):
            combined_text += " " + " ".join(task_context["labels"]).lower()
        if task_context.get("comments"):
            combined_text += " " + " ".join(task_context["comments"]).lower()

        # Extract languages
        languages = self._detect_languages(combined_text)

        # Extract frameworks
        frameworks = self._detect_frameworks(combined_text)

        # Extract domains
        domains = self._detect_domains(combined_text)

        # Determine task type
        task_type = self._determine_task_type(combined_text)

        # Score review dimensions
        review_dimensions = self._score_review_dimensions(combined_text)

        # Estimate complexity
        complexity = self._estimate_complexity(task_description, task_context)

        # Estimate scope
        estimated_scope = self._estimate_scope(complexity, len(task_context.get("files", [])))

        # Extract critical files
        critical_files = task_context.get("files", [])

        # Extract keywords
        keywords = self._extract_keywords(task_description)

        return TaskProfile(
            task_type=task_type,
            languages=languages,
            frameworks=frameworks,
            domains=domains,
            review_dimensions=review_dimensions,
            complexity=complexity,
            estimated_scope=estimated_scope,
            critical_files=critical_files,
            keywords=keywords,
            raw_description=task_description,
        )

    def extract_linear_metadata(self, linear_issue: Dict) -> TaskProfile:
        """Extract metadata from a Linear issue and generate task profile.

        Args:
            linear_issue: Linear issue dict with keys like:
                - title: Issue title
                - description: Issue description
                - labels: List of label objects
                - comments: List of comment objects

        Returns:
            TaskProfile generated from Linear issue metadata.
        """
        # Extract text fields
        title = linear_issue.get("title", "")
        description = linear_issue.get("description", "")

        # Extract labels
        labels = []
        for label in linear_issue.get("labels", []):
            if isinstance(label, dict):
                labels.append(label.get("name", ""))
            else:
                labels.append(str(label))

        # Extract comments
        comments = []
        for comment in linear_issue.get("comments", []):
            if isinstance(comment, dict):
                comments.append(comment.get("body", ""))
            else:
                comments.append(str(comment))

        # Extract file paths from description (code blocks, file references)
        files = self._extract_file_paths(description)

        # Analyze combined data
        full_description = f"{title} {description}"
        context = {
            "files": files,
            "labels": labels,
            "comments": comments,
        }

        return self.analyze_task(full_description, context)

    def _detect_languages(self, text: str) -> List[str]:
        """Detect programming languages in text.

        Args:
            text: Lowercase text to analyze

        Returns:
            List of detected language names
        """
        detected = []
        for language, patterns in LANGUAGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detected.append(language)
                    break  # Move to next language
        return sorted(set(detected))

    def _detect_frameworks(self, text: str) -> List[str]:
        """Detect frameworks in text.

        Args:
            text: Lowercase text to analyze

        Returns:
            List of detected framework names
        """
        detected = []
        for framework, patterns in FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detected.append(framework)
                    break
        return sorted(set(detected))

    def _detect_domains(self, text: str) -> List[str]:
        """Detect business/technical domains in text.

        Args:
            text: Lowercase text to analyze

        Returns:
            List of detected domain names
        """
        detected = []
        for domain, patterns in DOMAIN_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detected.append(domain)
                    break
        return sorted(set(detected))

    def _determine_task_type(self, text: str) -> str:
        """Determine task type from text.

        Args:
            text: Lowercase text to analyze

        Returns:
            Task type string
        """
        # Score each task type by keyword matches
        scores = {}
        for task_type, patterns in TASK_TYPE_PATTERNS.items():
            score = sum(1 for pattern in patterns if re.search(pattern, text, re.IGNORECASE))
            if score > 0:
                scores[task_type] = score

        # Return highest-scoring type, or "unknown"
        if scores:
            return max(scores, key=scores.get)  # type: ignore
        return "unknown"

    def _score_review_dimensions(self, text: str) -> Dict[str, float]:
        """Score review dimensions based on keyword presence.

        Args:
            text: Lowercase text to analyze

        Returns:
            Dict mapping dimension name to importance score (0-1)
        """
        scores = {}
        for dimension, keywords in DIMENSION_KEYWORDS.items():
            # Count matching keywords
            matches = sum(1 for keyword in keywords if keyword.lower() in text)

            # Normalize to 0-1 scale (max score = 1.0 if 3+ keywords match)
            score = min(matches / 3.0, 1.0)

            if score > 0:
                scores[dimension] = score

        return scores

    def _estimate_complexity(
        self,
        description: str,
        context: Dict
    ) -> str:
        """Estimate task complexity.

        Complexity levels:
        - low: Single file, < 100 lines
        - medium: 2-5 files, 100-500 lines
        - high: 6-10 files, 500-2000 lines
        - critical: > 10 files or > 2000 lines

        Args:
            description: Task description
            context: Task context dict

        Returns:
            Complexity level string
        """
        file_count = len(context.get("files", []))

        # Estimate lines changed from description keywords
        if any(word in description.lower() for word in ["major", "complete", "overhaul", "rewrite"]):
            estimated_lines = 2000
        elif any(word in description.lower() for word in ["refactor", "restructure", "redesign"]):
            estimated_lines = 500
        elif any(word in description.lower() for word in ["fix", "patch", "tweak"]):
            estimated_lines = 50
        else:
            estimated_lines = 200  # Default

        # Complexity scoring
        if file_count > 10 or estimated_lines > 2000:
            return "critical"
        elif file_count >= 6 or estimated_lines > 500:
            return "high"
        elif file_count >= 2 or estimated_lines > 100:
            return "medium"
        else:
            return "low"

    def _estimate_scope(self, complexity: str, file_count: int) -> str:
        """Estimate time scope for task.

        Args:
            complexity: Complexity level
            file_count: Number of files affected

        Returns:
            Scope string: "hours", "days", or "weeks"
        """
        if complexity == "critical" or file_count > 15:
            return "weeks"
        elif complexity == "high" or file_count > 5:
            return "days"
        else:
            return "hours"

    def _extract_keywords(self, description: str) -> List[str]:
        """Extract important keywords from description.

        Args:
            description: Task description

        Returns:
            List of keywords
        """
        # Simple keyword extraction: words >= 4 chars, not common words
        common_words = {
            "this", "that", "with", "from", "have", "been", "will",
            "your", "them", "would", "make", "about", "know", "into",
        }

        words = re.findall(r'\b\w{4,}\b', description.lower())
        keywords = [w for w in words if w not in common_words]

        # Return unique keywords, limit to 20
        return list(set(keywords))[:20]

    def _extract_file_paths(self, text: str) -> List[str]:
        """Extract file paths from text.

        Looks for:
        - Paths with file extensions (e.g., src/main.py)
        - Code blocks with file references

        Args:
            text: Text to analyze

        Returns:
            List of file paths
        """
        # Pattern: word characters, slashes, dots for file paths
        pattern = r'\b[\w\-_]+(?:/[\w\-_.]+)+\.\w+\b'
        matches = re.findall(pattern, text)

        return list(set(matches))[:50]  # Limit to 50 files
