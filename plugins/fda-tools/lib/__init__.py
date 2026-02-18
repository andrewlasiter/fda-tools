"""FDA Tools Plugin - Library Package

This __init__.py enables proper Python package imports and pytest
coverage measurement for the lib directory.

Public API exports for the FDA Tools library modules.

NOTE: Lazy imports below are wrapped in try/except to avoid import
errors when optional dependencies are not installed.
"""

# Gap Analysis
try:
    from lib.gap_analyzer import (
        GapAnalyzer,
        detect_missing_device_data,
        detect_weak_predicates,
        detect_testing_gaps,
        analyze_all_gaps,
    )
except ImportError:
    try:
        from gap_analyzer import (
            GapAnalyzer,
            detect_missing_device_data,
            detect_weak_predicates,
            detect_testing_gaps,
            analyze_all_gaps,
        )
    except ImportError:
        GapAnalyzer = None
        detect_missing_device_data = None
        detect_weak_predicates = None
        detect_testing_gaps = None
        analyze_all_gaps = None

# Predicate Analysis
try:
    from lib.predicate_ranker import PredicateRanker, rank_predicates
except ImportError:
    try:
        from predicate_ranker import PredicateRanker, rank_predicates
    except ImportError:
        PredicateRanker = None
        rank_predicates = None

try:
    from lib.predicate_diversity import (
        PredicateDiversityAnalyzer,
        analyze_predicate_diversity,
    )
except ImportError:
    try:
        from predicate_diversity import (
            PredicateDiversityAnalyzer,
            analyze_predicate_diversity,
        )
    except ImportError:
        PredicateDiversityAnalyzer = None
        analyze_predicate_diversity = None

# Enrichment and Validation
try:
    from lib.fda_enrichment import FDAEnrichment
except ImportError:
    try:
        from fda_enrichment import FDAEnrichment
    except ImportError:
        FDAEnrichment = None

try:
    from lib.expert_validator import ExpertValidator
except ImportError:
    try:
        from expert_validator import ExpertValidator
    except ImportError:
        ExpertValidator = None

try:
    from lib.manifest_validator import (
        ValidationError,
        SchemaNotFoundError,
        JsonSchemaNotInstalledError,
    )
except ImportError:
    try:
        from manifest_validator import (
            ValidationError,
            SchemaNotFoundError,
            JsonSchemaNotInstalledError,
        )
    except ImportError:
        ValidationError = None
        SchemaNotFoundError = None
        JsonSchemaNotInstalledError = None

# Combination Product Detection
try:
    from lib.combination_detector import (
        CombinationProductDetector,
        detect_combination_product,
    )
except ImportError:
    try:
        from combination_detector import (
            CombinationProductDetector,
            detect_combination_product,
        )
    except ImportError:
        CombinationProductDetector = None
        detect_combination_product = None

# Export utilities
try:
    from lib.ecopy_exporter import eCopyExporter, export_ecopy
except ImportError:
    try:
        from ecopy_exporter import eCopyExporter, export_ecopy
    except ImportError:
        eCopyExporter = None
        export_ecopy = None

# Disclaimers
try:
    from lib.disclaimers import (
        get_csv_header_disclaimer,
        get_html_banner_disclaimer,
        get_html_footer_disclaimer,
        get_markdown_header_disclaimer,
        get_json_disclaimers_section,
    )
except ImportError:
    try:
        from disclaimers import (
            get_csv_header_disclaimer,
            get_html_banner_disclaimer,
            get_html_footer_disclaimer,
            get_markdown_header_disclaimer,
            get_json_disclaimers_section,
        )
    except ImportError:
        get_csv_header_disclaimer = None
        get_html_banner_disclaimer = None
        get_html_footer_disclaimer = None
        get_markdown_header_disclaimer = None
        get_json_disclaimers_section = None

# Import Helpers (FDA-17 / GAP-015)
try:
    from lib.import_helpers import (
        ImportResult,
        safe_import,
        try_optional_import,
        safe_import_from,
        conditional_import,
        try_import_with_alternatives,
    )
except ImportError:
    try:
        from import_helpers import (
            ImportResult,
            safe_import,
            try_optional_import,
            safe_import_from,
            conditional_import,
            try_import_with_alternatives,
        )
    except ImportError:
        ImportResult = None
        safe_import = None
        try_optional_import = None
        safe_import_from = None
        conditional_import = None
        try_import_with_alternatives = None

# Logging Configuration (FDA-18 / GAP-014)
try:
    from lib.logging_config import (  # type: ignore
        setup_logging,
        get_logger,
        get_audit_logger,
        AuditLogger,
        add_logging_args,
        apply_logging_args,
        reset_logging,
    )
except ImportError:
    try:
        from logging_config import (  # type: ignore
            setup_logging,
            get_logger,
            get_audit_logger,
            AuditLogger,
            add_logging_args,
            apply_logging_args,
            reset_logging,
        )
    except ImportError:
        setup_logging = None
        get_logger = None
        get_audit_logger = None
        AuditLogger = None
        add_logging_args = None
        apply_logging_args = None
        reset_logging = None

# HDE Support (FDA-44)
try:
    from lib.hde_support import (
        HDESubmissionOutline,
        PrevalenceValidator,
        ProbableBenefitAnalyzer,
        IRBApprovalTracker,
        AnnualDistributionReport,
        generate_hde_outline,
        validate_hde_prevalence,
        generate_probable_benefit_template,
    )
except ImportError:
    try:
        from hde_support import (
            HDESubmissionOutline,
            PrevalenceValidator,
            ProbableBenefitAnalyzer,
            IRBApprovalTracker,
            AnnualDistributionReport,
            generate_hde_outline,
            validate_hde_prevalence,
            generate_probable_benefit_template,
        )
    except ImportError:
        HDESubmissionOutline = None
        PrevalenceValidator = None
        ProbableBenefitAnalyzer = None
        IRBApprovalTracker = None
        AnnualDistributionReport = None
        generate_hde_outline = None
        validate_hde_prevalence = None
        generate_probable_benefit_template = None

# RWE Integration (FDA-41)
try:
    from lib.rwe_integration import (
        RWEDataSourceConnector,
        RWDQualityAssessor,
        RWESubmissionTemplate,
        create_rwe_connector,
        assess_rwd_quality,
        generate_rwe_template,
    )
except ImportError:
    try:
        from rwe_integration import (
            RWEDataSourceConnector,
            RWDQualityAssessor,
            RWESubmissionTemplate,
            create_rwe_connector,
            assess_rwd_quality,
            generate_rwe_template,
        )
    except ImportError:
        RWEDataSourceConnector = None
        RWDQualityAssessor = None
        RWESubmissionTemplate = None
        create_rwe_connector = None
        assess_rwd_quality = None
        generate_rwe_template = None

# De Novo Support (FDA-45)
try:
    from lib.de_novo_support import (
        DeNovoSubmissionOutline,
        SpecialControlsProposal,
        DeNovoRiskAssessment,
        BenefitRiskAnalysis,
        PathwayDecisionTree,
        PredicateSearchDocumentation,
        generate_de_novo_outline,
        generate_special_controls,
        evaluate_pathway,
        perform_benefit_risk_analysis,
    )
except ImportError:
    try:
        from de_novo_support import (
            DeNovoSubmissionOutline,
            SpecialControlsProposal,
            DeNovoRiskAssessment,
            BenefitRiskAnalysis,
            PathwayDecisionTree,
            PredicateSearchDocumentation,
            generate_de_novo_outline,
            generate_special_controls,
            evaluate_pathway,
            perform_benefit_risk_analysis,
        )
    except ImportError:
        DeNovoSubmissionOutline = None
        SpecialControlsProposal = None
        DeNovoRiskAssessment = None
        BenefitRiskAnalysis = None
        PathwayDecisionTree = None
        PredicateSearchDocumentation = None
        generate_de_novo_outline = None
        generate_special_controls = None
        evaluate_pathway = None
        perform_benefit_risk_analysis = None

__all__ = [
    # Gap Analysis
    'GapAnalyzer',
    'detect_missing_device_data',
    'detect_weak_predicates',
    'detect_testing_gaps',
    'analyze_all_gaps',
    # Predicate Analysis
    'PredicateRanker',
    'rank_predicates',
    'PredicateDiversityAnalyzer',
    'analyze_predicate_diversity',
    # Enrichment
    'FDAEnrichment',
    # Validation
    'ExpertValidator',
    'ValidationError',
    'SchemaNotFoundError',
    'JsonSchemaNotInstalledError',
    # Combination Products
    'CombinationProductDetector',
    'detect_combination_product',
    # Export
    'eCopyExporter',
    'export_ecopy',
    # Disclaimers
    'get_csv_header_disclaimer',
    'get_html_banner_disclaimer',
    'get_html_footer_disclaimer',
    'get_markdown_header_disclaimer',
    'get_json_disclaimers_section',
    # Import Helpers
    'ImportResult',
    'safe_import',
    'try_optional_import',
    'safe_import_from',
    'conditional_import',
    'try_import_with_alternatives',
    # Logging Configuration
    'setup_logging',
    'get_logger',
    'get_audit_logger',
    'AuditLogger',
    'add_logging_args',
    'apply_logging_args',
    'reset_logging',
    # HDE Support (FDA-44)
    'HDESubmissionOutline',
    'PrevalenceValidator',
    'ProbableBenefitAnalyzer',
    'IRBApprovalTracker',
    'AnnualDistributionReport',
    'generate_hde_outline',
    'validate_hde_prevalence',
    'generate_probable_benefit_template',
    # RWE Integration (FDA-41)
    'RWEDataSourceConnector',
    'RWDQualityAssessor',
    'RWESubmissionTemplate',
    'create_rwe_connector',
    'assess_rwd_quality',
    'generate_rwe_template',
    # De Novo Support (FDA-45)
    'DeNovoSubmissionOutline',
    'SpecialControlsProposal',
    'DeNovoRiskAssessment',
    'BenefitRiskAnalysis',
    'PathwayDecisionTree',
    'PredicateSearchDocumentation',
    'generate_de_novo_outline',
    'generate_special_controls',
    'evaluate_pathway',
    'perform_benefit_risk_analysis',
]
