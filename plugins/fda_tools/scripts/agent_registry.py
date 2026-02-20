#!/usr/bin/env python3
"""
FDA Regulatory Expert Agent Registry (FDA-73) -- Framework for managing,
discovering, and coordinating the FDA regulatory expert agent team.

Provides:
  1. Agent registration and discovery
  2. Capability-based agent selection
  3. Agent team assembly for device reviews
  4. Skill validation and completeness checking
  5. Agent coordination patterns

The registry discovers agents from the skills/ directory structure:
    skills/
        fda-{specialty}-expert/
            SKILL.md      -- Agent skill definition (required)
            agent.yaml    -- Agent configuration (required)
            references/   -- Reference materials (optional)

Usage:
    from agent_registry import AgentRegistry

    registry = AgentRegistry()
    agents = registry.list_agents()
    agent = registry.get_agent("fda-software-ai-expert")
    team = registry.assemble_team(device_type="SaMD", device_class="II")
    validation = registry.validate_all_agents()

    # CLI:
    python3 agent_registry.py list
    python3 agent_registry.py info fda-clinical-expert
    python3 agent_registry.py team --device-type SaMD --class II
    python3 agent_registry.py validate
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

# Try to import yaml; fall back to basic parsing if unavailable
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Agent Registry Constants
# ------------------------------------------------------------------

# Skills directory relative to this script
SKILLS_DIR = Path(__file__).parent.parent / "skills"

# Required files for a valid agent
REQUIRED_FILES = ["SKILL.md"]
RECOMMENDED_FILES = ["agent.yaml"]

# Agent capability categories
CAPABILITY_CATEGORIES = {
    "regulatory_pathway": [
        "510(k)", "PMA", "De Novo", "HDE", "IDE",
        "Breakthrough Device", "Pre-Sub",
    ],
    "device_specialty": [
        "cardiovascular", "orthopedic", "neurological", "ophthalmic",
        "dental", "radiology", "IVD", "SaMD", "combination_product",
    ],
    "functional_area": [
        "quality_systems", "biocompatibility", "sterilization",
        "software_validation", "clinical_evidence", "postmarket",
        "regulatory_strategy", "risk_management", "human_factors",
        "cybersecurity", "international",
    ],
    "regulatory_framework": [
        "21 CFR 820", "21 CFR 812", "21 CFR 814", "21 CFR 803",
        "ISO 13485", "ISO 14971", "IEC 62304", "ISO 10993",
        "IEC 60601", "IEC 62366",
    ],
}

# Device type to recommended agents mapping
DEVICE_AGENT_MAP = {
    "SaMD": [
        "fda-software-ai-expert",
        "fda-regulatory-strategy-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
    ],
    "cardiovascular": [
        "fda-cardiovascular-expert",
        "fda-biocompatibility-expert",
        "fda-clinical-expert",
        "fda-sterilization-expert",
        "fda-quality-expert",
    ],
    "orthopedic": [
        "fda-orthopedic-expert",
        "fda-biocompatibility-expert",
        "fda-sterilization-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
    ],
    "IVD": [
        "fda-ivd-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
        "fda-regulatory-strategy-expert",
    ],
    "combination_product": [
        "fda-combination-product-expert",
        "fda-biocompatibility-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
        "fda-regulatory-strategy-expert",
    ],
    "neurological": [
        "fda-neurology-expert",
        "fda-biocompatibility-expert",
        "fda-clinical-expert",
        "fda-software-ai-expert",
        "fda-quality-expert",
    ],
    "ophthalmic": [
        "fda-ophthalmic-expert",
        "fda-biocompatibility-expert",
        "fda-clinical-expert",
        "fda-sterilization-expert",
    ],
    "radiology": [
        "fda-radiology-expert",
        "fda-software-ai-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
    ],
    "generic": [
        "fda-regulatory-strategy-expert",
        "fda-quality-expert",
        "fda-clinical-expert",
        "fda-postmarket-expert",
    ],
}

# Submission pathway to required agents
PATHWAY_AGENT_MAP = {
    "510k": [
        "fda-regulatory-strategy-expert",
        "fda-quality-expert",
    ],
    "PMA": [
        "fda-regulatory-strategy-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
        "fda-postmarket-expert",
    ],
    "De Novo": [
        "fda-regulatory-strategy-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
    ],
    "IDE": [
        "fda-clinical-expert",
        "fda-regulatory-strategy-expert",
    ],
    "HDE": [
        "fda-regulatory-strategy-expert",
        "fda-clinical-expert",
    ],
}


# ------------------------------------------------------------------
# Universal Agent Catalog (170+ agents across 12 categories)
# ------------------------------------------------------------------

# Review dimensions for multi-dimensional agent selection
REVIEW_DIMENSIONS = [
    "code_quality",      # Code quality, best practices, bug detection
    "security",          # Security audits, vulnerability analysis, penetration testing
    "testing",           # Test automation, QA strategy, test coverage
    "documentation",     # Technical writing, API docs, user guides
    "performance",       # Performance optimization, bottleneck analysis
    "compliance",        # Regulatory compliance, audit frameworks, legal review
    "architecture",      # System design, architectural patterns, tech choices
    "operations",        # DevOps, deployment, incident response, monitoring
]

# Comprehensive catalog of all 170+ agents
# Each agent has: category, model, review_dimensions, languages, description
UNIVERSAL_AGENT_CATALOG = {
    # =================================================================
    # FDA REGULATORY AGENTS (20 agents)
    # =================================================================
    "fda-quality-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance", "code_quality"],
        "languages": [],
        "description": "FDA Quality Systems expert - 21 CFR 820, ISO 13485, design controls"
    },
    "fda-software-ai-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance", "code_quality", "testing"],
        "languages": ["python", "javascript", "typescript"],
        "description": "FDA Software & AI/ML expert - IEC 62304, PCCP, cybersecurity, V&V"
    },
    "fda-clinical-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA Clinical Affairs expert - IDE, clinical trials, statistical design"
    },
    "fda-biocompatibility-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA Biocompatibility expert - ISO 10993, biological evaluation"
    },
    "fda-sterilization-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA Sterilization expert - ISO 11135, ISO 11137, validation"
    },
    "fda-postmarket-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA Post-Market expert - MDR, recalls, vigilance, MAUDE"
    },
    "fda-regulatory-strategy-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA Regulatory Strategy expert - pathway selection, Pre-Sub, breakthrough"
    },
    "fda-cardiovascular-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA Cardiovascular devices expert - circulatory, cardiac devices"
    },
    "fda-orthopedic-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA Orthopedic devices expert - spinal, joint implants"
    },
    "fda-neurology-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA Neurology devices expert - neuro-stimulation, brain interfaces"
    },
    "fda-ophthalmic-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA Ophthalmic devices expert - vision correction, intraocular lenses"
    },
    "fda-ivd-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA In Vitro Diagnostic expert - lab tests, diagnostic assays"
    },
    "fda-combination-product-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA Combination Product expert - drug-device, biologic-device combinations"
    },
    "fda-international-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA International expert - EU MDR, IVDR, global harmonization"
    },
    "fda-radiology-expert": {
        "category": "fda",
        "model": "opus",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA Radiology devices expert - imaging, X-ray, MRI devices"
    },
    "fda-510k-knowledge": {
        "category": "fda",
        "model": "sonnet",
        "review_dimensions": ["compliance"],
        "languages": ["python"],
        "description": "FDA 510(k) pipeline knowledge - local data, scripts, workflow"
    },
    "fda-predicate-assessment": {
        "category": "fda",
        "model": "sonnet",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA predicate assessment - substantial equivalence, predicate validity"
    },
    "fda-safety-signal-triage": {
        "category": "fda",
        "model": "sonnet",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "FDA safety signal triage - recalls, MAUDE adverse events, complaints"
    },
    "fda-510k-submission-outline": {
        "category": "fda",
        "model": "sonnet",
        "review_dimensions": ["compliance", "documentation"],
        "languages": [],
        "description": "FDA 510(k) submission outlines - RTA readiness, evidence plans"
    },
    "fda-plugin-e2e-smoke": {
        "category": "fda",
        "model": "haiku",
        "review_dimensions": ["testing"],
        "languages": ["python"],
        "description": "FDA plugin smoke tests - deterministic live testing"
    },

    # =================================================================
    # VOLTAGENT QA/SECURITY AGENTS (15 agents)
    # =================================================================
    "voltagent-qa-sec:code-reviewer": {
        "category": "qa-sec",
        "model": "opus",
        "review_dimensions": ["code_quality", "testing"],
        "languages": ["python", "javascript", "typescript", "java", "go", "rust"],
        "description": "Code quality, best practices, bug detection, test coverage"
    },
    "voltagent-qa-sec:security-auditor": {
        "category": "qa-sec",
        "model": "opus",
        "review_dimensions": ["security", "compliance"],
        "languages": ["python", "javascript", "typescript", "java", "go"],
        "description": "Security audits, compliance assessments, vulnerability analysis"
    },
    "voltagent-qa-sec:test-automator": {
        "category": "qa-sec",
        "model": "sonnet",
        "review_dimensions": ["testing", "code_quality"],
        "languages": ["python", "javascript", "typescript", "java"],
        "description": "Build automated test frameworks, create test scripts, CI/CD integration"
    },
    "voltagent-qa-sec:qa-expert": {
        "category": "qa-sec",
        "model": "sonnet",
        "review_dimensions": ["testing", "code_quality"],
        "languages": [],
        "description": "QA strategy, test planning, quality metrics, comprehensive testing"
    },
    "voltagent-qa-sec:penetration-tester": {
        "category": "qa-sec",
        "model": "opus",
        "review_dimensions": ["security"],
        "languages": ["python", "bash"],
        "description": "Security penetration tests, active exploitation, vulnerability validation"
    },
    "voltagent-qa-sec:performance-engineer": {
        "category": "qa-sec",
        "model": "sonnet",
        "review_dimensions": ["performance", "code_quality"],
        "languages": ["python", "javascript", "typescript", "go", "rust"],
        "description": "Performance bottleneck identification, optimization, benchmarking"
    },
    "voltagent-qa-sec:compliance-auditor": {
        "category": "qa-sec",
        "model": "sonnet",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "Regulatory compliance, GDPR, HIPAA, PCI DSS, SOC 2, ISO standards"
    },
    "voltagent-qa-sec:architect-reviewer": {
        "category": "qa-sec",
        "model": "opus",
        "review_dimensions": ["architecture", "code_quality"],
        "languages": [],
        "description": "System design evaluation, architectural patterns, tech choices"
    },
    "voltagent-qa-sec:debugger": {
        "category": "qa-sec",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["python", "javascript", "typescript", "java", "go"],
        "description": "Bug diagnosis, root cause analysis, error log analysis"
    },
    "voltagent-qa-sec:error-detective": {
        "category": "qa-sec",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "operations"],
        "languages": [],
        "description": "Error correlation, root cause identification, failure prevention"
    },
    "voltagent-qa-sec:chaos-engineer": {
        "category": "qa-sec",
        "model": "sonnet",
        "review_dimensions": ["operations", "testing"],
        "languages": [],
        "description": "Chaos engineering, failure experiments, resilience testing"
    },
    "voltagent-qa-sec:accessibility-tester": {
        "category": "qa-sec",
        "model": "sonnet",
        "review_dimensions": ["testing", "compliance"],
        "languages": ["javascript", "typescript"],
        "description": "WCAG compliance, accessibility testing, assistive technology"
    },
    "voltagent-qa-sec:ad-security-reviewer": {
        "category": "qa-sec",
        "model": "sonnet",
        "review_dimensions": ["security"],
        "languages": ["powershell"],
        "description": "Active Directory security audits, privilege escalation risks"
    },
    "voltagent-qa-sec:powershell-security-hardening": {
        "category": "qa-sec",
        "model": "sonnet",
        "review_dimensions": ["security"],
        "languages": ["powershell"],
        "description": "PowerShell security hardening, least-privilege design"
    },
    "voltagent-qa-sec:security-engineer": {
        "category": "qa-sec",
        "model": "opus",
        "review_dimensions": ["security", "operations"],
        "languages": [],
        "description": "Comprehensive security solutions, automated controls, compliance programs"
    },

    # =================================================================
    # VOLTAGENT LANGUAGE SPECIALISTS (24 agents)
    # =================================================================
    "voltagent-lang:python-pro": {
        "category": "lang",
        "model": "opus",
        "review_dimensions": ["code_quality"],
        "languages": ["python"],
        "description": "Type-safe, production-ready Python code, modern async patterns"
    },
    "voltagent-lang:typescript-pro": {
        "category": "lang",
        "model": "opus",
        "review_dimensions": ["code_quality"],
        "languages": ["typescript"],
        "description": "Advanced TypeScript, complex generics, type-level programming"
    },
    "voltagent-lang:javascript-pro": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["javascript"],
        "description": "Modern JavaScript, ES2023+, async patterns, performance-critical code"
    },
    "voltagent-lang:rust-engineer": {
        "category": "lang",
        "model": "opus",
        "review_dimensions": ["code_quality", "performance"],
        "languages": ["rust"],
        "description": "Rust systems programming, memory safety, zero-cost abstractions"
    },
    "voltagent-lang:golang-pro": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "performance"],
        "languages": ["go"],
        "description": "Go concurrent programming, high-performance systems, microservices"
    },
    "voltagent-lang:java-architect": {
        "category": "lang",
        "model": "opus",
        "review_dimensions": ["code_quality", "architecture"],
        "languages": ["java"],
        "description": "Enterprise Java, Spring Boot, microservices, cloud-native"
    },
    "voltagent-lang:csharp-developer": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["csharp"],
        "description": "ASP.NET Core, cloud-native .NET, async patterns, dependency injection"
    },
    "voltagent-lang:cpp-pro": {
        "category": "lang",
        "model": "opus",
        "review_dimensions": ["code_quality", "performance"],
        "languages": ["cpp"],
        "description": "Modern C++20/23, template metaprogramming, systems programming"
    },
    "voltagent-lang:swift-expert": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["swift"],
        "description": "Native iOS/macOS development, SwiftUI, async/await, actor-based concurrency"
    },
    "voltagent-lang:kotlin-specialist": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["kotlin"],
        "description": "Kotlin coroutines, multiplatform code, Android/server-side development"
    },
    "voltagent-lang:php-pro": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["php"],
        "description": "PHP 8.3+, strict typing, Laravel/Symfony expertise"
    },
    "voltagent-lang:ruby-expert": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["ruby"],
        "description": "Ruby on Rails, full-stack development, Hotwire reactivity"
    },
    "voltagent-lang:elixir-expert": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["elixir"],
        "description": "Fault-tolerant systems, OTP patterns, Phoenix framework"
    },
    "voltagent-lang:sql-pro": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "performance"],
        "languages": ["sql"],
        "description": "Complex SQL queries, database schema design, query optimization"
    },
    "voltagent-lang:dotnet-core-expert": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["csharp"],
        "description": ".NET Core cloud-native, high-performance microservices, minimal APIs"
    },
    "voltagent-lang:dotnet-framework-4.8-expert": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["csharp"],
        "description": "Legacy .NET Framework 4.8, maintenance, modernization"
    },
    "voltagent-lang:powershell-5.1-expert": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "operations"],
        "languages": ["powershell"],
        "description": "PowerShell 5.1, Active Directory, Windows infrastructure automation"
    },
    "voltagent-lang:powershell-7-expert": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "operations"],
        "languages": ["powershell"],
        "description": "PowerShell 7+, cross-platform automation, Azure orchestration"
    },
    "voltagent-lang:angular-architect": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "architecture"],
        "languages": ["typescript"],
        "description": "Enterprise Angular 15+, RxJS patterns, micro-frontends"
    },
    "voltagent-lang:react-specialist": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["typescript", "javascript"],
        "description": "React 18+, performance optimization, advanced React patterns"
    },
    "voltagent-lang:vue-expert": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["typescript", "javascript"],
        "description": "Vue 3 Composition API, reactivity optimization, Nuxt 3"
    },
    "voltagent-lang:flutter-expert": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["dart"],
        "description": "Flutter 3+ cross-platform mobile, custom UI, state management"
    },
    "voltagent-lang:django-developer": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["python"],
        "description": "Django 4+ web applications, REST APIs, async views"
    },
    "voltagent-lang:laravel-specialist": {
        "category": "lang",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["php"],
        "description": "Laravel 10+, Eloquent ORM, queue systems, API performance"
    },

    # =================================================================
    # VOLTAGENT INFRASTRUCTURE (16 agents)
    # =================================================================
    "voltagent-infra:devops-engineer": {
        "category": "infra",
        "model": "opus",
        "review_dimensions": ["operations", "code_quality"],
        "languages": ["python", "bash", "yaml"],
        "description": "CI/CD pipelines, infrastructure automation, deployment workflows"
    },
    "voltagent-infra:kubernetes-specialist": {
        "category": "infra",
        "model": "sonnet",
        "review_dimensions": ["operations", "architecture"],
        "languages": ["yaml"],
        "description": "Kubernetes clusters, workload deployment, production troubleshooting"
    },
    "voltagent-infra:cloud-architect": {
        "category": "infra",
        "model": "opus",
        "review_dimensions": ["architecture", "operations"],
        "languages": [],
        "description": "Cloud infrastructure design, multi-cloud strategies, cost optimization"
    },
    "voltagent-infra:terraform-engineer": {
        "category": "infra",
        "model": "sonnet",
        "review_dimensions": ["operations"],
        "languages": ["hcl"],
        "description": "Terraform IaC, multi-cloud deployments, module architecture"
    },
    "voltagent-infra:sre-engineer": {
        "category": "infra",
        "model": "opus",
        "review_dimensions": ["operations", "performance"],
        "languages": [],
        "description": "SLO definition, error budget management, automation, fault tolerance"
    },
    "voltagent-infra:database-administrator": {
        "category": "infra",
        "model": "sonnet",
        "review_dimensions": ["operations", "performance"],
        "languages": ["sql"],
        "description": "Database performance, high-availability, disaster recovery"
    },
    "voltagent-infra:network-engineer": {
        "category": "infra",
        "model": "sonnet",
        "review_dimensions": ["operations", "security"],
        "languages": [],
        "description": "Cloud/hybrid network infrastructure, security, performance"
    },
    "voltagent-infra:deployment-engineer": {
        "category": "infra",
        "model": "sonnet",
        "review_dimensions": ["operations"],
        "languages": ["python", "bash"],
        "description": "CI/CD pipeline design, deployment automation strategies"
    },
    "voltagent-infra:incident-responder": {
        "category": "infra",
        "model": "sonnet",
        "review_dimensions": ["operations", "security"],
        "languages": [],
        "description": "Security breach response, evidence preservation, recovery"
    },
    "voltagent-infra:devops-incident-responder": {
        "category": "infra",
        "model": "sonnet",
        "review_dimensions": ["operations"],
        "languages": [],
        "description": "Production incidents, service failures, postmortems"
    },
    "voltagent-infra:platform-engineer": {
        "category": "infra",
        "model": "opus",
        "review_dimensions": ["operations", "architecture"],
        "languages": [],
        "description": "Internal developer platforms, self-service infrastructure, golden paths"
    },
    "voltagent-infra:security-engineer": {
        "category": "infra",
        "model": "opus",
        "review_dimensions": ["security", "operations"],
        "languages": [],
        "description": "Security automation, compliance programs, zero-trust architecture"
    },
    "voltagent-infra:azure-infra-engineer": {
        "category": "infra",
        "model": "sonnet",
        "review_dimensions": ["operations"],
        "languages": ["powershell"],
        "description": "Azure infrastructure, Entra ID, PowerShell automation, Bicep IaC"
    },
    "voltagent-infra:windows-infra-admin": {
        "category": "infra",
        "model": "sonnet",
        "review_dimensions": ["operations"],
        "languages": ["powershell"],
        "description": "Windows Server, Active Directory, DNS, DHCP, Group Policy"
    },
    "voltagent-infra:terragrunt-expert": {
        "category": "infra",
        "model": "sonnet",
        "review_dimensions": ["operations"],
        "languages": ["hcl"],
        "description": "Terragrunt orchestration, DRY configs, multi-environment deployments"
    },
    "voltagent-infra:postgres-pro": {
        "category": "infra",
        "model": "sonnet",
        "review_dimensions": ["performance", "operations"],
        "languages": ["sql"],
        "description": "PostgreSQL performance, high-availability replication, tuning"
    },

    # =================================================================
    # VOLTAGENT DATA & AI (12 agents)
    # =================================================================
    "voltagent-data-ai:ml-engineer": {
        "category": "data-ai",
        "model": "opus",
        "review_dimensions": ["code_quality"],
        "languages": ["python"],
        "description": "ML model deployment, serving infrastructure, automated retraining"
    },
    "voltagent-data-ai:data-scientist": {
        "category": "data-ai",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["python", "r"],
        "description": "Data analysis, predictive models, statistical insights"
    },
    "voltagent-data-ai:data-engineer": {
        "category": "data-ai",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "operations"],
        "languages": ["python", "sql"],
        "description": "Data pipelines, ETL/ELT processes, data infrastructure"
    },
    "voltagent-data-ai:ai-engineer": {
        "category": "data-ai",
        "model": "opus",
        "review_dimensions": ["code_quality"],
        "languages": ["python"],
        "description": "End-to-end AI systems, model training, production deployment"
    },
    "voltagent-data-ai:data-analyst": {
        "category": "data-ai",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": ["sql", "python"],
        "description": "Business data insights, dashboards, statistical analysis"
    },
    "voltagent-data-ai:llm-architect": {
        "category": "data-ai",
        "model": "opus",
        "review_dimensions": ["architecture"],
        "languages": ["python"],
        "description": "LLM systems, fine-tuning, RAG architectures, inference serving"
    },
    "voltagent-data-ai:mlops-engineer": {
        "category": "data-ai",
        "model": "sonnet",
        "review_dimensions": ["operations"],
        "languages": ["python"],
        "description": "ML infrastructure, experiment tracking, model versioning, automation"
    },
    "voltagent-data-ai:nlp-engineer": {
        "category": "data-ai",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["python"],
        "description": "Production NLP systems, text processing, language models"
    },
    "voltagent-data-ai:prompt-engineer": {
        "category": "data-ai",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Prompt design, optimization, testing, evaluation for LLMs"
    },
    "voltagent-data-ai:database-optimizer": {
        "category": "data-ai",
        "model": "sonnet",
        "review_dimensions": ["performance"],
        "languages": ["sql"],
        "description": "Slow query analysis, database performance, indexing strategies"
    },
    "voltagent-data-ai:machine-learning-engineer": {
        "category": "data-ai",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["python"],
        "description": "ML model deployment, optimization, serving at scale"
    },
    "voltagent-data-ai:postgres-pro": {
        "category": "data-ai",
        "model": "sonnet",
        "review_dimensions": ["performance"],
        "languages": ["sql"],
        "description": "PostgreSQL optimization, replication, scaling"
    },

    # =================================================================
    # VOLTAGENT CORE DEVELOPMENT (10 agents)
    # =================================================================
    "voltagent-core-dev:fullstack-developer": {
        "category": "core-dev",
        "model": "opus",
        "review_dimensions": ["code_quality"],
        "languages": ["python", "typescript", "javascript"],
        "description": "Complete features spanning database, API, and frontend"
    },
    "voltagent-core-dev:frontend-developer": {
        "category": "core-dev",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["typescript", "javascript"],
        "description": "React, Vue, Angular frontend applications, full-stack integration"
    },
    "voltagent-core-dev:backend-developer": {
        "category": "core-dev",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["python", "javascript", "java", "go"],
        "description": "Server-side APIs, microservices, backend systems"
    },
    "voltagent-core-dev:api-designer": {
        "category": "core-dev",
        "model": "sonnet",
        "review_dimensions": ["architecture", "documentation"],
        "languages": [],
        "description": "API design, OpenAPI specs, REST/GraphQL endpoints"
    },
    "voltagent-core-dev:microservices-architect": {
        "category": "core-dev",
        "model": "opus",
        "review_dimensions": ["architecture"],
        "languages": [],
        "description": "Distributed system architecture, microservices decomposition"
    },
    "voltagent-core-dev:graphql-architect": {
        "category": "core-dev",
        "model": "sonnet",
        "review_dimensions": ["architecture"],
        "languages": ["typescript", "javascript"],
        "description": "GraphQL schemas, federation, distributed graphs"
    },
    "voltagent-core-dev:mobile-developer": {
        "category": "core-dev",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["typescript", "swift", "kotlin"],
        "description": "Cross-platform mobile apps, React Native, Flutter"
    },
    "voltagent-core-dev:ui-designer": {
        "category": "core-dev",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": ["typescript", "javascript"],
        "description": "Visual interface design, design systems, component libraries"
    },
    "voltagent-core-dev:websocket-engineer": {
        "category": "core-dev",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["typescript", "javascript", "python"],
        "description": "Real-time bidirectional communication, WebSockets, Socket.IO"
    },
    "voltagent-core-dev:electron-pro": {
        "category": "core-dev",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["typescript", "javascript"],
        "description": "Electron desktop apps, native OS integration, cross-platform"
    },

    # =================================================================
    # VOLTAGENT DOMAINS (12 agents)
    # =================================================================
    "voltagent-domains:fintech-engineer": {
        "category": "domains",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "security", "compliance"],
        "languages": ["python", "javascript", "java"],
        "description": "Payment systems, financial integrations, compliance-heavy financial apps"
    },
    "voltagent-domains:blockchain-developer": {
        "category": "domains",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "security"],
        "languages": ["solidity", "rust", "javascript"],
        "description": "Smart contracts, DApps, blockchain protocols, Web3 integration"
    },
    "voltagent-domains:iot-engineer": {
        "category": "domains",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "operations"],
        "languages": ["python", "c", "cpp"],
        "description": "IoT solutions, device management, edge computing, cloud integration"
    },
    "voltagent-domains:game-developer": {
        "category": "domains",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "performance"],
        "languages": ["cpp", "csharp"],
        "description": "Game systems, graphics rendering, multiplayer networking"
    },
    "voltagent-domains:mobile-app-developer": {
        "category": "domains",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["swift", "kotlin", "dart"],
        "description": "iOS/Android mobile apps, native or cross-platform"
    },
    "voltagent-domains:payment-integration": {
        "category": "domains",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "security", "compliance"],
        "languages": ["python", "javascript"],
        "description": "Payment systems, payment gateways, PCI compliance, fraud prevention"
    },
    "voltagent-domains:embedded-systems": {
        "category": "domains",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "performance"],
        "languages": ["c", "cpp"],
        "description": "Firmware, microcontrollers, RTOS-based applications"
    },
    "voltagent-domains:m365-admin": {
        "category": "domains",
        "model": "sonnet",
        "review_dimensions": ["operations"],
        "languages": ["powershell"],
        "description": "Microsoft 365 automation, Exchange, Teams, SharePoint, Graph API"
    },
    "voltagent-domains:api-documenter": {
        "category": "domains",
        "model": "sonnet",
        "review_dimensions": ["documentation"],
        "languages": [],
        "description": "API documentation, OpenAPI specs, interactive documentation portals"
    },
    "voltagent-domains:seo-specialist": {
        "category": "domains",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "SEO optimization, technical audits, keyword strategy, rankings"
    },
    "voltagent-domains:quant-analyst": {
        "category": "domains",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": ["python", "r"],
        "description": "Quantitative trading strategies, financial models, risk analytics"
    },
    "voltagent-domains:risk-manager": {
        "category": "domains",
        "model": "sonnet",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "Enterprise risk identification, quantification, mitigation, compliance"
    },

    # =================================================================
    # VOLTAGENT META-COORDINATION (9 agents)
    # =================================================================
    "voltagent-meta:multi-agent-coordinator": {
        "category": "meta",
        "model": "opus",
        "review_dimensions": [],
        "languages": [],
        "description": "Coordinate multiple concurrent agents, shared state, distributed failures"
    },
    "voltagent-meta:task-distributor": {
        "category": "meta",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Distribute tasks across agents/workers, queue management, load balancing"
    },
    "voltagent-meta:workflow-orchestrator": {
        "category": "meta",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Business process workflows, state machines, error handling, transactions"
    },
    "voltagent-meta:agent-organizer": {
        "category": "meta",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Assemble and optimize multi-agent teams, task decomposition, coordination"
    },
    "voltagent-meta:context-manager": {
        "category": "meta",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Manage shared state, information retrieval, data sync for multi-agent systems"
    },
    "voltagent-meta:error-coordinator": {
        "category": "meta",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Coordinated error handling, failure detection, cascade prevention"
    },
    "voltagent-meta:it-ops-orchestrator": {
        "category": "meta",
        "model": "sonnet",
        "review_dimensions": ["operations"],
        "languages": [],
        "description": "Orchestrate IT ops tasks across PowerShell, .NET, infrastructure, Azure, M365"
    },
    "voltagent-meta:knowledge-synthesizer": {
        "category": "meta",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Extract actionable patterns from agent interactions, organizational learning"
    },
    "voltagent-meta:performance-monitor": {
        "category": "meta",
        "model": "sonnet",
        "review_dimensions": ["performance", "operations"],
        "languages": [],
        "description": "Track system metrics, detect anomalies, optimize resource usage"
    },

    # =================================================================
    # VOLTAGENT BUSINESS (11 agents)
    # =================================================================
    "voltagent-biz:product-manager": {
        "category": "biz",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Product strategy, feature prioritization, roadmap planning"
    },
    "voltagent-biz:technical-writer": {
        "category": "biz",
        "model": "sonnet",
        "review_dimensions": ["documentation"],
        "languages": [],
        "description": "Technical documentation, API references, user guides, SDK docs"
    },
    "voltagent-biz:business-analyst": {
        "category": "biz",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Business process analysis, requirements gathering, process improvements"
    },
    "voltagent-biz:scrum-master": {
        "category": "biz",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Agile facilitation, sprint planning, retrospectives, impediment removal"
    },
    "voltagent-biz:project-manager": {
        "category": "biz",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Project planning, execution tracking, risk management, stakeholder coordination"
    },
    "voltagent-biz:sales-engineer": {
        "category": "biz",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Technical pre-sales, solution architecture, proof-of-concept, demos"
    },
    "voltagent-biz:customer-success-manager": {
        "category": "biz",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Customer health, retention strategies, upsell opportunities, LTV maximization"
    },
    "voltagent-biz:legal-advisor": {
        "category": "biz",
        "model": "sonnet",
        "review_dimensions": ["compliance"],
        "languages": [],
        "description": "Contract drafting, compliance review, IP protection, legal risk assessment"
    },
    "voltagent-biz:content-marketer": {
        "category": "biz",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Content strategy, SEO-optimized marketing, multi-channel campaigns"
    },
    "voltagent-biz:ux-researcher": {
        "category": "biz",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "User research, behavior analysis, usability testing, persona development"
    },
    "voltagent-biz:wordpress-master": {
        "category": "biz",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": ["php", "javascript"],
        "description": "WordPress architecture, custom themes/plugins, enterprise multisite"
    },

    # =================================================================
    # VOLTAGENT DEV EXPERIENCE (13 agents)
    # =================================================================
    "voltagent-dev-exp:refactoring-specialist": {
        "category": "dev-exp",
        "model": "opus",
        "review_dimensions": ["code_quality"],
        "languages": ["python", "javascript", "typescript", "java"],
        "description": "Transform complex code into clean, maintainable systems"
    },
    "voltagent-dev-exp:mcp-developer": {
        "category": "dev-exp",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["typescript", "python"],
        "description": "Build MCP servers/clients connecting AI to external tools and data"
    },
    "voltagent-dev-exp:cli-developer": {
        "category": "dev-exp",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["python", "javascript", "typescript", "go"],
        "description": "Command-line tools, terminal apps, cross-platform CLI"
    },
    "voltagent-dev-exp:tooling-engineer": {
        "category": "dev-exp",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["python", "javascript", "typescript"],
        "description": "Developer tools, CLIs, code generators, build tools, IDE extensions"
    },
    "voltagent-dev-exp:documentation-engineer": {
        "category": "dev-exp",
        "model": "sonnet",
        "review_dimensions": ["documentation"],
        "languages": [],
        "description": "Comprehensive documentation systems, API docs, tutorials, guides"
    },
    "voltagent-dev-exp:dx-optimizer": {
        "category": "dev-exp",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "operations"],
        "languages": [],
        "description": "Developer workflow optimization, build times, feedback loops, testing efficiency"
    },
    "voltagent-dev-exp:git-workflow-manager": {
        "category": "dev-exp",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Git workflows, branching strategies, merge management"
    },
    "voltagent-dev-exp:dependency-manager": {
        "category": "dev-exp",
        "model": "sonnet",
        "review_dimensions": ["security", "code_quality"],
        "languages": [],
        "description": "Dependency audits, vulnerability scanning, version conflicts, bundle optimization"
    },
    "voltagent-dev-exp:build-engineer": {
        "category": "dev-exp",
        "model": "sonnet",
        "review_dimensions": ["performance"],
        "languages": [],
        "description": "Build performance optimization, compilation times, build system scaling"
    },
    "voltagent-dev-exp:legacy-modernizer": {
        "category": "dev-exp",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "architecture"],
        "languages": [],
        "description": "Modernize legacy systems, incremental migration, technical debt reduction"
    },
    "voltagent-dev-exp:powershell-module-architect": {
        "category": "dev-exp",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["powershell"],
        "description": "PowerShell module architecture, profile systems, cross-version compatibility"
    },
    "voltagent-dev-exp:powershell-ui-architect": {
        "category": "dev-exp",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["powershell"],
        "description": "PowerShell desktop GUIs (WinForms, WPF) and terminal UIs (TUIs)"
    },
    "voltagent-dev-exp:slack-expert": {
        "category": "dev-exp",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "security"],
        "languages": ["typescript", "javascript", "python"],
        "description": "Slack app development, Slack API integrations, security review"
    },

    # =================================================================
    # VOLTAGENT RESEARCH (6 agents)
    # =================================================================
    "voltagent-research:market-researcher": {
        "category": "research",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Market analysis, consumer behavior, competitive landscapes, opportunity sizing"
    },
    "voltagent-research:competitive-analyst": {
        "category": "research",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Competitor analysis, market benchmarking, competitive positioning"
    },
    "voltagent-research:trend-analyst": {
        "category": "research",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Emerging patterns, industry shifts, future scenarios, strategic planning"
    },
    "voltagent-research:research-analyst": {
        "category": "research",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Comprehensive research, synthesis into insights, trend identification, reporting"
    },
    "voltagent-research:search-specialist": {
        "category": "research",
        "model": "haiku",
        "review_dimensions": [],
        "languages": [],
        "description": "Advanced search strategies, query optimization, targeted information retrieval"
    },
    "voltagent-research:data-researcher": {
        "category": "research",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Discover, collect, validate data from multiple sources for analysis"
    },

    # =================================================================
    # PLUGIN AGENTS (20+ agents)
    # =================================================================
    "agent-sdk-dev:agent-sdk-verifier-py": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "compliance"],
        "languages": ["python"],
        "description": "Verify Python Agent SDK apps follow best practices and documentation"
    },
    "agent-sdk-dev:agent-sdk-verifier-ts": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "compliance"],
        "languages": ["typescript"],
        "description": "Verify TypeScript Agent SDK apps follow best practices"
    },
    "code-simplifier:code-simplifier": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["python", "javascript", "typescript"],
        "description": "Simplify code for clarity, consistency, maintainability while preserving functionality"
    },
    "feature-dev:code-reviewer": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "testing"],
        "languages": ["python", "javascript", "typescript"],
        "description": "Code review for project guidelines, style guides, best practices"
    },
    "feature-dev:code-architect": {
        "category": "plugins",
        "model": "opus",
        "review_dimensions": ["architecture", "code_quality"],
        "languages": [],
        "description": "Design feature architectures, analyze codebase patterns, implementation blueprints"
    },
    "feature-dev:code-explorer": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Analyze codebase features, trace execution, map architecture, document dependencies"
    },
    "pr-review-toolkit:code-reviewer": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": [],
        "description": "Review code for project guidelines, style violations, best practices"
    },
    "pr-review-toolkit:pr-test-analyzer": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": ["testing"],
        "languages": [],
        "description": "Review PR test coverage quality and completeness, identify gaps"
    },
    "pr-review-toolkit:silent-failure-hunter": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "security"],
        "languages": [],
        "description": "Identify silent failures, inadequate error handling, inappropriate fallbacks"
    },
    "pr-review-toolkit:comment-analyzer": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": ["documentation", "code_quality"],
        "languages": [],
        "description": "Analyze code comments for accuracy, completeness, maintainability"
    },
    "pr-review-toolkit:type-design-analyzer": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": ["code_quality"],
        "languages": ["typescript", "python"],
        "description": "Analyze type design for encapsulation, invariants, best practices"
    },
    "hookify:conversation-analyzer": {
        "category": "plugins",
        "model": "haiku",
        "review_dimensions": [],
        "languages": [],
        "description": "Analyze conversation transcripts to find behaviors worth preventing with hooks"
    },
    "plugin-dev:plugin-validator": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": ["code_quality", "compliance"],
        "languages": ["typescript", "python"],
        "description": "Validate plugin structure, configuration, best practices"
    },
    "plugin-dev:agent-creator": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": [],
        "description": "Create plugin agents with proper structure and configuration"
    },
    "plugin-dev:skill-reviewer": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": ["documentation"],
        "languages": [],
        "description": "Review plugin skills for completeness and best practices"
    },
    "huggingface-skills:AGENTS": {
        "category": "plugins",
        "model": "sonnet",
        "review_dimensions": [],
        "languages": ["python"],
        "description": "Hugging Face Hub operations, model/dataset management"
    },
}


# ------------------------------------------------------------------
# YAML Frontmatter Parser (fallback when PyYAML not available)
# ------------------------------------------------------------------

def _parse_frontmatter(content: str) -> Dict:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}

    end_idx = content.index("---", 3) if "---" in content[3:] else -1
    if end_idx < 0:
        return {}

    yaml_text = content[3:end_idx + 3].strip()

    if HAS_YAML:
        try:
            return yaml.safe_load(yaml_text) or {}  # type: ignore
        except yaml.YAMLError:  # type: ignore
            pass

    # Fallback: basic key-value parsing
    result = {}
    for line in yaml_text.split("\n"):
        line = line.strip()
        if ":" in line and not line.startswith("#"):
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


# Allowed top-level keys in agent.yaml configuration files.
# Any keys outside this set are rejected to prevent injection of
# unexpected configuration directives.
ALLOWED_AGENT_YAML_KEYS = {
    "name", "description", "model", "tools", "max_context",
    "temperature", "expertise", "regulatory_knowledge", "standards",
    "deficiency_patterns", "output_standards", "agent_type",
    "capabilities", "review_areas", "specialization",
}


def _validate_yaml_schema(data: Dict, source: str = "unknown") -> Dict:
    """Validate parsed YAML data against the allowed agent config schema.

    Rejects any top-level keys not in ALLOWED_AGENT_YAML_KEYS to prevent
    injection of unexpected configuration directives.

    Args:
        data: Parsed YAML dictionary.
        source: Source file description for logging.

    Returns:
        The validated data dict (unmodified if all keys are allowed).

    Raises:
        ValueError: If unknown keys are detected.
    """
    if not isinstance(data, dict):
        logger.warning("YAML schema validation: expected dict, got %s in %s", type(data).__name__, source)
        return {}

    unknown_keys = set(data.keys()) - ALLOWED_AGENT_YAML_KEYS
    if unknown_keys:
        logger.warning(
            "YAML schema validation: rejecting unknown keys %s in %s",
            unknown_keys, source
        )
        # Return only the allowed keys rather than rejecting entirely,
        # so existing agents with extra fields degrade gracefully
        return {k: v for k, v in data.items() if k in ALLOWED_AGENT_YAML_KEYS}

    return data


def _parse_yaml_file(path: Path) -> Dict:
    """Parse a YAML file using safe_load and validate against schema.

    Uses yaml.safe_load (SafeLoader) to prevent arbitrary code
    execution from malicious YAML payloads. Additionally validates
    parsed data against the allowed agent config schema.
    """
    try:
        content = path.read_text(encoding="utf-8")
        if HAS_YAML:
            try:
                data = yaml.safe_load(content) or {}  # type: ignore
                return _validate_yaml_schema(data, source=str(path))
            except Exception as yaml_err:  # type: ignore
                # Catch any YAML parsing errors (ParserError, ScannerError, etc.)
                logger.warning("YAML parsing error in %s: %s - falling back to basic parsing", path, yaml_err)
                # Fall through to basic parsing
        # Fallback: basic parsing
        result = {}
        for line in content.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith("#") and not line.startswith("-"):
                key, _, value = line.partition(":")
                result[key.strip()] = value.strip()
        return _validate_yaml_schema(result, source=str(path))
    except (OSError, ValueError) as e:
        logger.warning("Failed to parse YAML file %s: %s", path, e)
        return {}


# ==================================================================
# Agent Registry
# ==================================================================

class AgentRegistry:
    """Registry for discovering, managing, and coordinating FDA
    regulatory expert agents.

    Scans the skills/ directory for agent definitions and provides
    capability-based selection and team assembly.
    """

    def __init__(self, skills_dir: Optional[Path] = None):
        """Initialize the agent registry.

        Args:
            skills_dir: Path to skills directory. Defaults to
                       project skills/ directory.
        """
        self._skills_dir = skills_dir or SKILLS_DIR
        self._agents: Dict[str, Dict] = {}
        self._loaded = False

    def _ensure_loaded(self):
        """Lazy-load agent definitions on first access."""
        if not self._loaded:
            self._scan_agents()
            self._loaded = True

    def _validate_path_within_base(self, path: Path, base: Path) -> bool:
        """Validate that a resolved path stays within the base directory.

        Prevents path traversal attacks by ensuring resolved paths
        (with symlinks and '..' sequences resolved) remain within the
        expected base directory boundary.

        Args:
            path: Path to validate (will be resolved).
            base: Base directory that the path must reside within.

        Returns:
            True if path is safely within base, False otherwise.
        """
        try:
            resolved = path.resolve()
            resolved_base = base.resolve()
            resolved.relative_to(resolved_base)
            return True
        except ValueError:
            logger.warning(
                "Path traversal attempt blocked: %s escapes base %s",
                path, base
            )
            return False

    def _scan_agents(self):
        """Scan skills directory for agent definitions.

        All discovered paths are validated against the base skills
        directory to prevent path traversal via symlinks or '..'
        sequences.
        """
        base_path = self._skills_dir.resolve()

        if not base_path.exists() or not base_path.is_dir():
            logger.warning("Skills directory does not exist or is not a directory: %s", self._skills_dir)
            return

        for agent_dir in sorted(base_path.iterdir()):
            if not agent_dir.is_dir():
                continue
            if agent_dir.name.startswith("."):
                continue

            # Validate agent directory stays within skills base
            if not self._validate_path_within_base(agent_dir, base_path):
                continue

            skill_path = agent_dir / "SKILL.md"
            if not skill_path.exists():
                continue

            # Validate SKILL.md path stays within skills base
            if not self._validate_path_within_base(skill_path, base_path):
                continue

            agent = self._load_agent(agent_dir)
            if agent:
                self._agents[agent["name"]] = agent

    def _load_agent(self, agent_dir: Path) -> Optional[Dict]:
        """Load a single agent definition from its directory.

        All file paths derived from agent_dir are validated to stay
        within the skills base directory before access.

        Args:
            agent_dir: Path to agent directory.

        Returns:
            Agent definition dict or None if invalid.
        """
        base_path = self._skills_dir.resolve()
        skill_path = agent_dir / "SKILL.md"
        yaml_path = agent_dir / "agent.yaml"

        # Validate all paths before any file I/O
        if not self._validate_path_within_base(skill_path, base_path):
            return None
        if yaml_path.exists() and not self._validate_path_within_base(yaml_path, base_path):
            return None

        try:
            skill_content = skill_path.read_text(encoding="utf-8")
        except OSError:
            return None

        # Parse frontmatter
        frontmatter = _parse_frontmatter(skill_content)
        name = frontmatter.get("name", agent_dir.name)
        description = frontmatter.get("description", "")

        # Parse agent.yaml if exists
        yaml_config = {}
        if yaml_path.exists():
            yaml_config = _parse_yaml_file(yaml_path)

        # Check for references directory (with path validation)
        refs_dir = agent_dir / "references"
        has_references = False
        ref_count = 0
        if refs_dir.exists() and self._validate_path_within_base(refs_dir, base_path):
            has_references = refs_dir.is_dir() and any(refs_dir.iterdir())
            ref_count = len(list(refs_dir.iterdir())) if has_references else 0

        # Extract capabilities from description and skill content
        capabilities = self._extract_capabilities(description, skill_content)

        # Determine agent type
        agent_type = self._determine_agent_type(name)

        # Measure content size
        skill_lines = len(skill_content.split("\n"))
        skill_words = len(skill_content.split())

        return {
            "name": name,
            "directory": str(agent_dir),
            "description": description,
            "type": agent_type,
            "has_skill_md": True,
            "has_agent_yaml": yaml_path.exists(),
            "has_references": has_references,
            "reference_count": ref_count,
            "skill_lines": skill_lines,
            "skill_words": skill_words,
            "capabilities": capabilities,
            "yaml_config": yaml_config,
            "frontmatter": frontmatter,
        }

    def _extract_capabilities(self, description: str, content: str) -> List[str]:
        """Extract capability tags from description and content."""
        caps = set()
        combined = (description + " " + content[:2000]).lower()

        # Check all capability categories
        for category, keywords in CAPABILITY_CATEGORIES.items():
            for kw in keywords:
                if kw.lower() in combined:
                    caps.add(kw)

        return sorted(caps)

    def _determine_agent_type(self, name: str) -> str:
        """Determine agent type from naming convention."""
        if "expert" in name:
            return "expert"
        elif "support" in name:
            return "support"
        elif "integration" in name:
            return "integration"
        elif "knowledge" in name:
            return "knowledge"
        elif "smoke" in name or "test" in name:
            return "testing"
        else:
            return "skill"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_agents(self, agent_type: str = "") -> List[Dict]:
        """List all registered agents.

        Args:
            agent_type: Optional filter by type (expert, support, etc.).

        Returns:
            List of agent summary dicts.
        """
        self._ensure_loaded()
        agents = list(self._agents.values())
        if agent_type:
            agents = [a for a in agents if a["type"] == agent_type]
        return sorted(agents, key=lambda a: a["name"])

    def get_agent(self, name: str) -> Optional[Dict]:
        """Get a specific agent by name.

        Args:
            name: Agent name (e.g., 'fda-software-ai-expert').

        Returns:
            Agent definition dict or None.
        """
        self._ensure_loaded()
        return self._agents.get(name)

    def search_agents(self, query: str) -> List[Dict]:
        """Search agents by keyword in name or description.

        Args:
            query: Search query string.

        Returns:
            Matching agents sorted by relevance.
        """
        self._ensure_loaded()
        query_lower = query.lower()
        results = []
        for agent in self._agents.values():
            score = 0
            if query_lower in agent["name"].lower():
                score += 10
            if query_lower in agent["description"].lower():
                score += 5
            if any(query_lower in cap.lower() for cap in agent["capabilities"]):
                score += 3
            if score > 0:
                results.append((score, agent))

        results.sort(key=lambda x: x[0], reverse=True)
        return [agent for _, agent in results]

    def find_agents_by_capability(self, capability: str) -> List[Dict]:
        """Find agents with a specific capability.

        Args:
            capability: Capability keyword (e.g., 'ISO 10993', 'cybersecurity').

        Returns:
            Matching agents.
        """
        self._ensure_loaded()
        cap_lower = capability.lower()
        return [
            agent for agent in self._agents.values()
            if any(cap_lower in cap.lower() for cap in agent["capabilities"])
        ]

    def assemble_team(
        self,
        device_type: str = "generic",
        submission_pathway: str = "",
        device_class: str = "",
        additional_capabilities: Optional[List[str]] = None,
    ) -> Dict:
        """Assemble an expert team for a device review.

        Args:
            device_type: Device type (SaMD, cardiovascular, etc.).
            submission_pathway: Pathway (510k, PMA, De Novo, IDE, HDE).
            device_class: Device class (I, II, III).
            additional_capabilities: Extra capabilities needed.

        Returns:
            Team assembly with core, specialty, and support agents.
        """
        self._ensure_loaded()

        # Get recommended agents for device type
        device_agents = DEVICE_AGENT_MAP.get(device_type, DEVICE_AGENT_MAP["generic"])

        # Add pathway-specific agents
        pathway_agents = PATHWAY_AGENT_MAP.get(submission_pathway, [])

        # Combine and deduplicate
        all_agent_names: List[str] = []
        seen: Set[str] = set()
        for name in device_agents + pathway_agents:
            if name not in seen:
                all_agent_names.append(name)
                seen.add(name)

        # Add agents for additional capabilities
        if additional_capabilities:
            for cap in additional_capabilities:
                cap_agents = self.find_agents_by_capability(cap)
                for agent in cap_agents:
                    if agent["name"] not in seen:
                        all_agent_names.append(agent["name"])
                        seen.add(agent["name"])

        # Class III always needs clinical expert and postmarket
        if device_class == "III":
            for name in ["fda-clinical-expert", "fda-postmarket-expert"]:
                if name not in seen:
                    all_agent_names.append(name)
                    seen.add(name)

        # Resolve agent objects
        core_agents = []
        specialty_agents = []
        unavailable = []

        for name in all_agent_names:
            agent = self._agents.get(name)
            if agent:
                if agent["type"] == "expert":
                    if name in device_agents[:2]:
                        core_agents.append(agent)
                    else:
                        specialty_agents.append(agent)
                else:
                    specialty_agents.append(agent)
            else:
                unavailable.append(name)

        return {
            "device_type": device_type,
            "submission_pathway": submission_pathway,
            "device_class": device_class,
            "team_size": len(core_agents) + len(specialty_agents),
            "core_agents": [
                {"name": a["name"], "type": a["type"], "role": "core"}
                for a in core_agents
            ],
            "specialty_agents": [
                {"name": a["name"], "type": a["type"], "role": "specialty"}
                for a in specialty_agents
            ],
            "unavailable_agents": unavailable,
            "coordination_pattern": self._recommend_pattern(
                len(core_agents) + len(specialty_agents)
            ),
        }

    def _recommend_pattern(self, team_size: int) -> Dict:
        """Recommend coordination pattern based on team size."""
        if team_size <= 3:
            return {
                "pattern": "peer-to-peer",
                "description": "Small team, direct coordination between agents",
                "overhead": "low",
            }
        elif team_size <= 6:
            return {
                "pattern": "master-worker",
                "description": "Lead reviewer coordinates specialist agents",
                "overhead": "medium",
            }
        else:
            return {
                "pattern": "hierarchical",
                "description": "Lead reviewer with sub-team leads for each domain",
                "overhead": "medium-high",
            }

    def validate_all_agents(self) -> Dict:
        """Validate all registered agents for completeness.

        Returns:
            Validation report with pass/fail for each agent and overall score.
        """
        self._ensure_loaded()

        results = []
        total_score = 0
        max_score = 0

        for name, agent in sorted(self._agents.items()):
            validation = self._validate_agent(agent)
            results.append(validation)
            total_score += validation["score"]
            max_score += validation["max_score"]

        overall_score = round(total_score / max_score * 100) if max_score > 0 else 0

        return {
            "total_agents": len(results),
            "overall_score": overall_score,
            "agents": results,
            "summary": {
                "fully_complete": sum(1 for r in results if r["status"] == "COMPLETE"),
                "partial": sum(1 for r in results if r["status"] == "PARTIAL"),
                "minimal": sum(1 for r in results if r["status"] == "MINIMAL"),
            },
        }

    def _validate_agent(self, agent: Dict) -> Dict:
        """Validate a single agent definition."""
        issues = []
        score = 0
        max_score = 100

        # SKILL.md exists (required)
        if agent["has_skill_md"]:
            score += 20
        else:
            issues.append("CRITICAL: Missing SKILL.md")

        # agent.yaml exists (recommended)
        if agent["has_agent_yaml"]:
            score += 15
        else:
            issues.append("WARNING: Missing agent.yaml")

        # Description exists and is meaningful
        if agent["description"] and len(agent["description"]) > 50:
            score += 15
        elif agent["description"]:
            score += 8
            issues.append("MINOR: Description too short (<50 chars)")
        else:
            issues.append("WARNING: No description")

        # SKILL.md content depth
        if agent["skill_lines"] >= 200:
            score += 20
        elif agent["skill_lines"] >= 100:
            score += 12
            issues.append("MINOR: SKILL.md could be more comprehensive")
        elif agent["skill_lines"] >= 50:
            score += 6
            issues.append("WARNING: SKILL.md is minimal")
        else:
            issues.append("WARNING: SKILL.md is very short")

        # References exist
        if agent["has_references"]:
            score += 10
        else:
            # Not all agents need references
            score += 5

        # Capabilities extracted
        if len(agent["capabilities"]) >= 5:
            score += 10
        elif len(agent["capabilities"]) >= 2:
            score += 5
        else:
            issues.append("MINOR: Few capabilities detected")

        # Frontmatter complete
        fm = agent["frontmatter"]
        if "name" in fm and "description" in fm:
            score += 10
        elif "name" in fm:
            score += 5
            issues.append("MINOR: Frontmatter missing description")
        else:
            issues.append("WARNING: Frontmatter incomplete")

        status = "COMPLETE" if score >= 80 else "PARTIAL" if score >= 50 else "MINIMAL"

        return {
            "name": agent["name"],
            "type": agent["type"],
            "score": score,
            "max_score": max_score,
            "status": status,
            "issues": issues,
        }

    def get_statistics(self) -> Dict:
        """Get registry statistics.

        Returns:
            Statistics about registered agents.
        """
        self._ensure_loaded()

        types = {}
        total_lines = 0
        total_refs = 0
        with_yaml = 0
        with_refs = 0

        for agent in self._agents.values():
            t = agent["type"]
            types[t] = types.get(t, 0) + 1
            total_lines += agent["skill_lines"]
            total_refs += agent["reference_count"]
            if agent["has_agent_yaml"]:
                with_yaml += 1
            if agent["has_references"]:
                with_refs += 1

        return {
            "total_agents": len(self._agents),
            "agent_types": types,
            "agents_with_yaml": with_yaml,
            "agents_with_references": with_refs,
            "total_skill_lines": total_lines,
            "total_reference_files": total_refs,
            "avg_skill_lines": round(total_lines / max(len(self._agents), 1)),
        }


# ==================================================================
# Universal Agent Registry (Extends AgentRegistry for 170+ agents)
# ==================================================================

class UniversalAgentRegistry(AgentRegistry):
    """Extended registry supporting ALL 170+ agents across 12 categories.

    Extends the base AgentRegistry to include not just FDA agents from
    the skills/ directory, but also voltagent specialists, plugin agents,
    and other specialized agents from the universal catalog.

    Provides multi-dimensional agent discovery:
    - By review dimension (code_quality, security, testing, etc.)
    - By programming language
    - By category (fda, qa-sec, lang, infra, data-ai, etc.)
    - By model tier (opus, sonnet, haiku)

    Usage:
        registry = UniversalAgentRegistry()

        # Find all agents for a review dimension
        security_agents = registry.find_agents_by_review_dimension("security")

        # Find language-specific agents
        python_agents = registry.find_agents_by_language("python")

        # Find all agents in a category
        qa_agents = registry.find_agents_by_category("qa-sec")

        # Get full catalog
        all_agents = registry.discover_all_agents()
    """

    def __init__(self, skills_dir: Optional[Path] = None):
        """Initialize the universal agent registry.

        Args:
            skills_dir: Path to skills directory for FDA agents.
        """
        super().__init__(skills_dir)
        self._universal_agents: Dict[str, Dict] = {}
        self._universal_loaded = False

    def _ensure_universal_loaded(self):
        """Lazy-load universal agent catalog on first access."""
        if not self._universal_loaded:
            self._load_universal_catalog()
            self._universal_loaded = True

    def _load_universal_catalog(self):
        """Load all agents from the universal catalog.

        Merges FDA agents from skills/ directory with agents from
        the UNIVERSAL_AGENT_CATALOG constant.
        """
        # First load FDA agents from skills/ directory
        self._ensure_loaded()

        # Copy FDA agents to universal registry
        for name, agent in self._agents.items():
            catalog_metadata = UNIVERSAL_AGENT_CATALOG.get(name, {})
            self._universal_agents[name] = {
                **agent,
                "source": "skills_directory",
                "catalog_metadata": catalog_metadata,
                # Add category from catalog or default to 'fda'
                "category": catalog_metadata.get("category", "fda"),
                "model": catalog_metadata.get("model", "opus"),
                "review_dimensions": catalog_metadata.get("review_dimensions", []),
                "languages": catalog_metadata.get("languages", []),
            }

        # Add all agents from universal catalog
        for name, metadata in UNIVERSAL_AGENT_CATALOG.items():
            if name not in self._universal_agents:
                # Agent not in skills/ directory, use catalog metadata
                self._universal_agents[name] = {
                    "name": name,
                    "source": "universal_catalog",
                    "category": metadata["category"],
                    "model": metadata["model"],
                    "review_dimensions": metadata["review_dimensions"],
                    "languages": metadata["languages"],
                    "description": metadata["description"],
                    "type": "universal",
                }

    def discover_all_agents(self) -> Dict[str, List[str]]:
        """Discover agents from all sources.

        Returns dict organized by category:
            {
                "fda": ["fda-quality-expert", "fda-software-ai-expert", ...],
                "qa-sec": ["voltagent-qa-sec:code-reviewer", ...],
                ...
            }

        Returns:
            Dict mapping category to list of agent names.
        """
        self._ensure_universal_loaded()

        # Organize by category
        by_category: Dict[str, List[str]] = {}
        for name, agent in self._universal_agents.items():
            category = agent.get("category", "unknown")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(name)

        # Sort agents within each category
        for category in by_category:
            by_category[category].sort()

        return by_category

    def find_agents_by_review_dimension(self, dimension: str) -> List[Dict]:
        """Find agents with a specific review dimension capability.

        Review dimensions:
            - code_quality: Code quality, best practices, bug detection
            - security: Security audits, vulnerability analysis
            - testing: Test automation, QA strategy, test coverage
            - documentation: Technical writing, API docs, user guides
            - performance: Performance optimization, bottleneck analysis
            - compliance: Regulatory compliance, audit frameworks
            - architecture: System design, architectural patterns
            - operations: DevOps, deployment, incident response

        Args:
            dimension: Review dimension name.

        Returns:
            List of agent dicts with this review dimension, sorted by
            relevance (primary dimension match > model tier).
        """
        self._ensure_universal_loaded()

        if dimension not in REVIEW_DIMENSIONS:
            logger.warning("Unknown review dimension: %s", dimension)
            return []

        matching_agents = []
        for name, agent in self._universal_agents.items():
            review_dims = agent.get("review_dimensions", [])
            if isinstance(review_dims, list) and dimension in review_dims:
                # Score by position in review_dimensions list (earlier = higher priority)
                primary_score = 0 if review_dims[0] == dimension else 1
                # Model tier scoring (opus=3, sonnet=2, haiku=1)
                model = agent.get("model", "haiku")
                model_score = {"opus": 3, "sonnet": 2, "haiku": 1}.get(model, 0)

                matching_agents.append({
                    **agent,
                    "_relevance_score": (primary_score * 100) + model_score
                })

        # Sort by relevance (lower primary_score = better, higher model_score = better)
        matching_agents.sort(key=lambda a: a["_relevance_score"], reverse=True)

        # Remove temporary scoring field
        for agent in matching_agents:
            agent.pop("_relevance_score", None)

        return matching_agents

    def find_agents_by_language(self, language: str) -> List[Dict]:
        """Find agents with expertise in a specific programming language.

        Args:
            language: Language name (python, typescript, javascript, rust, etc.).

        Returns:
            List of agent dicts supporting this language, sorted by model tier.
        """
        self._ensure_universal_loaded()

        language_lower = language.lower()
        matching_agents = []

        for name, agent in self._universal_agents.items():
            languages = agent.get("languages", [])
            if isinstance(languages, list) and any(
                language_lower == lang.lower() for lang in languages
            ):
                model = agent.get("model", "haiku")
                model_score = {"opus": 3, "sonnet": 2, "haiku": 1}.get(model, 0)
                matching_agents.append({
                    **agent,
                    "_model_score": model_score
                })

        # Sort by model tier (opus > sonnet > haiku)
        matching_agents.sort(key=lambda a: a["_model_score"], reverse=True)

        # Remove temporary scoring field
        for agent in matching_agents:
            agent.pop("_model_score", None)

        return matching_agents

    def find_agents_by_category(self, category: str) -> List[Dict]:
        """Find all agents in a specific category.

        Categories:
            - fda: FDA regulatory agents
            - qa-sec: QA and security agents
            - lang: Language-specific agents
            - infra: Infrastructure agents
            - data-ai: Data and AI agents
            - core-dev: Core development agents
            - domains: Domain-specific agents
            - meta: Meta-coordination agents
            - biz: Business agents
            - dev-exp: Developer experience agents
            - research: Research agents
            - plugins: Plugin agents

        Args:
            category: Category name.

        Returns:
            List of agent dicts in this category, sorted by name.
        """
        self._ensure_universal_loaded()

        matching_agents = []
        for name, agent in self._universal_agents.items():
            if agent.get("category") == category:
                matching_agents.append(agent)

        # Sort by name
        matching_agents.sort(key=lambda a: a["name"])

        return matching_agents

    def get_universal_agent(self, name: str) -> Optional[Dict]:
        """Get a specific agent from the universal registry.

        Args:
            name: Agent name (e.g., 'fda-software-ai-expert' or
                  'voltagent-qa-sec:code-reviewer').

        Returns:
            Agent definition dict or None.
        """
        self._ensure_universal_loaded()
        return self._universal_agents.get(name)

    def search_universal_agents(
        self,
        query: str,
        review_dimension: str = "",
        language: str = "",
        category: str = "",
    ) -> List[Dict]:
        """Search universal agents with multiple filters.

        Args:
            query: Search query (matches name or description).
            review_dimension: Optional review dimension filter.
            language: Optional language filter.
            category: Optional category filter.

        Returns:
            Matching agents sorted by relevance.
        """
        self._ensure_universal_loaded()

        query_lower = query.lower()
        results = []

        for name, agent in self._universal_agents.items():
            # Apply filters
            if category and agent.get("category") != category:
                continue

            if review_dimension:
                review_dims = agent.get("review_dimensions", [])
                if review_dimension not in review_dims:
                    continue

            if language:
                languages = agent.get("languages", [])
                if not any(language.lower() == lang.lower() for lang in languages):
                    continue

            # Score by query match
            score = 0
            if query_lower in agent["name"].lower():
                score += 10
            if query_lower in agent.get("description", "").lower():
                score += 5

            if score > 0 or not query:
                results.append((score, agent))

        # Sort by score (descending)
        results.sort(key=lambda x: x[0], reverse=True)

        return [agent for _, agent in results]

    def get_statistics(self) -> Dict:
        """Get registry statistics for all agents.

        Returns:
            Statistics about universal agent registry.
        """
        self._ensure_universal_loaded()

        # Get base stats from FDA agents
        base_stats = super().get_statistics()

        # Count universal agents by category
        categories: Dict[str, int] = {}
        by_model: Dict[str, int] = {}
        by_review_dim: Dict[str, int] = {}
        by_language: Dict[str, int] = {}

        for agent in self._universal_agents.values():
            cat = agent.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

            model = agent.get("model", "unknown")
            by_model[model] = by_model.get(model, 0) + 1

            for dim in agent.get("review_dimensions", []):
                by_review_dim[dim] = by_review_dim.get(dim, 0) + 1

            for lang in agent.get("languages", []):
                by_language[lang] = by_language.get(lang, 0) + 1

        return {
            **base_stats,
            "total_universal_agents": len(self._universal_agents),
            "agents_by_category": categories,
            "agents_by_model": by_model,
            "agents_by_review_dimension": by_review_dim,
            "agents_by_language": by_language,
        }


# ==================================================================
# Agent Team Coordinator
# ==================================================================

class AgentTeamCoordinator:
    """Coordinates multi-agent review workflows.

    Provides patterns for assembling and coordinating expert agent teams
    for device reviews, including task assignment, dependency management,
    and result aggregation.
    """

    def __init__(self, registry: Optional[AgentRegistry] = None):
        """Initialize with an agent registry.

        Args:
            registry: Agent registry instance.
        """
        self.registry = registry or AgentRegistry()

    def create_review_plan(
        self,
        device_name: str,
        device_type: str = "generic",
        submission_pathway: str = "510k",
        device_class: str = "II",
    ) -> Dict:
        """Create a multi-agent review plan.

        Args:
            device_name: Device name.
            device_type: Device type category.
            submission_pathway: Regulatory pathway.
            device_class: FDA device class.

        Returns:
            Review plan with phases, tasks, and agent assignments.
        """
        # Assemble team
        team = self.registry.assemble_team(
            device_type=device_type,
            submission_pathway=submission_pathway,
            device_class=device_class,
        )

        # Define review phases
        phases = [
            {
                "phase": 1,
                "name": "Initial Assessment",
                "description": "Device classification, pathway verification, initial risk assessment",
                "assigned_agents": [
                    a["name"] for a in team["core_agents"][:2]
                ],
                "dependencies": [],
                "estimated_hours": 4,
            },
            {
                "phase": 2,
                "name": "Specialist Review",
                "description": "Domain-specific technical review (biocompatibility, software, clinical, etc.)",
                "assigned_agents": [
                    a["name"] for a in team["specialty_agents"]
                ],
                "dependencies": [1],
                "estimated_hours": 8,
                "parallel": True,
            },
            {
                "phase": 3,
                "name": "Quality & Compliance",
                "description": "QMS compliance, design control, and documentation review",
                "assigned_agents": [
                    a["name"] for a in team["core_agents"]
                    if "quality" in a["name"]
                ] or [team["core_agents"][0]["name"]] if team["core_agents"] else [],
                "dependencies": [1],
                "estimated_hours": 4,
            },
            {
                "phase": 4,
                "name": "Integration & Deficiency Report",
                "description": "Aggregate findings, resolve conflicts, generate unified report",
                "assigned_agents": [
                    a["name"] for a in team["core_agents"][:1]
                ],
                "dependencies": [2, 3],
                "estimated_hours": 4,
            },
        ]

        total_hours = sum(p["estimated_hours"] for p in phases)

        return {
            "device_name": device_name,
            "device_type": device_type,
            "submission_pathway": submission_pathway,
            "device_class": device_class,
            "team": team,
            "phases": phases,
            "total_estimated_hours": total_hours,
            "coordination_pattern": team["coordination_pattern"],
        }

    def get_agent_task_matrix(self, review_plan: Dict) -> List[Dict]:
        """Generate a task assignment matrix from a review plan.

        Args:
            review_plan: Review plan from create_review_plan().

        Returns:
            List of task assignments.
        """
        tasks = []
        for phase in review_plan.get("phases", []):
            for agent_name in phase.get("assigned_agents", []):
                tasks.append({
                    "phase": phase["phase"],
                    "phase_name": phase["name"],
                    "agent": agent_name,
                    "description": phase["description"],
                    "dependencies": phase.get("dependencies", []),
                    "parallel": phase.get("parallel", False),
                    "estimated_hours": (
                        phase["estimated_hours"] / max(len(phase["assigned_agents"]), 1)
                    ),
                })
        return tasks


# ==================================================================
# CLI Entry Point
# ==================================================================

def main():
    parser = argparse.ArgumentParser(
        description="FDA Regulatory Expert Agent Registry (FDA-73)"
    )
    subparsers = parser.add_subparsers(dest="command")

    # list command
    list_p = subparsers.add_parser("list", help="List all agents")
    list_p.add_argument("--type", default="", help="Filter by type")
    list_p.add_argument("--json", action="store_true")

    # info command
    info_p = subparsers.add_parser("info", help="Show agent details")
    info_p.add_argument("name", help="Agent name")
    info_p.add_argument("--json", action="store_true")

    # team command
    team_p = subparsers.add_parser("team", help="Assemble review team")
    team_p.add_argument("--device-type", default="generic", help="Device type")
    team_p.add_argument("--pathway", default="510k", help="Submission pathway")
    team_p.add_argument("--class", dest="device_class", default="II", help="Device class")
    team_p.add_argument("--json", action="store_true")

    # validate command
    val_p = subparsers.add_parser("validate", help="Validate all agents")
    val_p.add_argument("--json", action="store_true")

    # stats command
    stats_p = subparsers.add_parser("stats", help="Registry statistics")
    stats_p.add_argument("--json", action="store_true")

    # search command
    search_p = subparsers.add_parser("search", help="Search agents")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--json", action="store_true")

    args = parser.parse_args()
    registry = AgentRegistry()

    if args.command == "list":
        agents = registry.list_agents(agent_type=args.type)
        if args.json:
            print(json.dumps([{
                "name": a["name"], "type": a["type"],
                "description": a["description"][:100],
            } for a in agents], indent=2))
        else:
            print(f"Registered Agents: {len(agents)}")
            for a in agents:
                yaml_mark = "Y" if a["has_agent_yaml"] else "N"
                refs_mark = "Y" if a["has_references"] else "N"
                print(f"  [{a['type']:10s}] {a['name']:40s} yaml:{yaml_mark} refs:{refs_mark} lines:{a['skill_lines']}")

    elif args.command == "info":
        agent = registry.get_agent(args.name)
        if agent:
            if args.json:
                # Remove non-serializable content
                safe = {k: v for k, v in agent.items() if k != "yaml_config" or isinstance(v, (str, int, float, bool, list, dict, type(None)))}
                print(json.dumps(safe, indent=2, default=str))
            else:
                print(f"Agent: {agent['name']}")
                print(f"Type: {agent['type']}")
                print(f"Description: {agent['description'][:200]}")
                print(f"SKILL.md: {agent['skill_lines']} lines, {agent['skill_words']} words")
                print(f"agent.yaml: {'Yes' if agent['has_agent_yaml'] else 'No'}")
                print(f"References: {agent['reference_count']} files")
                print(f"Capabilities: {', '.join(agent['capabilities'][:10])}")
        else:
            print(f"Agent not found: {args.name}")

    elif args.command == "team":
        team = registry.assemble_team(
            device_type=args.device_type,
            submission_pathway=args.pathway,
            device_class=args.device_class,
        )
        if args.json:
            print(json.dumps(team, indent=2))
        else:
            print(f"Team for {args.device_type} ({args.pathway}, Class {args.device_class}):")
            print(f"Team size: {team['team_size']}")
            print(f"Core agents:")
            for a in team["core_agents"]:
                print(f"  - {a['name']}")
            print(f"Specialty agents:")
            for a in team["specialty_agents"]:
                print(f"  - {a['name']}")
            if team["unavailable_agents"]:
                print(f"Unavailable:")
                for name in team["unavailable_agents"]:
                    print(f"  - {name}")
            pattern = team["coordination_pattern"]
            print(f"Coordination: {pattern['pattern']} ({pattern['description']})")

    elif args.command == "validate":
        report = registry.validate_all_agents()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"Agent Validation Report")
            print(f"Overall Score: {report['overall_score']}%")
            print(f"Total Agents: {report['total_agents']}")
            summary = report["summary"]
            print(f"  Complete: {summary['fully_complete']}")
            print(f"  Partial: {summary['partial']}")
            print(f"  Minimal: {summary['minimal']}")
            print()
            for agent in report["agents"]:
                status_char = "+" if agent["status"] == "COMPLETE" else "~" if agent["status"] == "PARTIAL" else "-"
                print(f"  [{status_char}] {agent['name']:40s} {agent['score']}/{agent['max_score']} {agent['status']}")
                for issue in agent["issues"]:
                    print(f"      {issue}")

    elif args.command == "stats":
        stats = registry.get_statistics()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"Registry Statistics:")
            print(f"  Total Agents: {stats['total_agents']}")
            print(f"  With YAML: {stats['agents_with_yaml']}")
            print(f"  With References: {stats['agents_with_references']}")
            print(f"  Total SKILL.md Lines: {stats['total_skill_lines']}")
            print(f"  Avg Lines per Agent: {stats['avg_skill_lines']}")
            print(f"  Agent Types:")
            for t, count in stats["agent_types"].items():
                print(f"    {t}: {count}")

    elif args.command == "search":
        results = registry.search_agents(args.query)
        if args.json:
            print(json.dumps([{
                "name": a["name"], "type": a["type"],
            } for a in results], indent=2))
        else:
            print(f"Search results for '{args.query}': {len(results)} found")
            for a in results:
                print(f"  {a['name']} ({a['type']})")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
