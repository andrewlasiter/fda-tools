"""FDA Tools - AI-powered tools for FDA medical device regulatory work.

This package provides tools for 510(k) submission preparation, predicate analysis,
and FDA regulatory intelligence.

Main modules:
    - lib: Core library modules (gap analysis, enrichment, validation)
    - scripts: CLI tools and automation scripts
    - tests: Comprehensive test suite

Example usage:
    >>> from fda_tools.lib import GapAnalyzer, FDAEnrichment
    >>> from fda_tools.scripts import FDAClient

    >>> analyzer = GapAnalyzer()
    >>> gaps = analyzer.detect_testing_gaps(device_data)
"""

__version__ = "5.36.0"
__author__ = "Andrew Lasiter"
__license__ = "MIT"

# Public API exports for convenience
# Users can import directly: from fda_tools import GapAnalyzer
try:
    # Core library exports (using relative imports)
    from .lib.gap_analyzer import GapAnalyzer
    from .lib.fda_enrichment import FDAEnrichment
    from .lib.predicate_ranker import PredicateRanker
    from .lib.expert_validator import ExpertValidator
    from .lib.combination_detector import CombinationProductDetector
    from .lib.ecopy_exporter import eCopyExporter
    from .lib.disclaimers import (
        get_csv_header_disclaimer,
        get_html_banner_disclaimer,
        get_markdown_header_disclaimer,
    )
    from .lib.import_helpers import safe_import, safe_import_from
    from .lib.logging_config import setup_logging, get_logger
    from .lib.secure_config import SecureConfig

    # Script module exports (using relative imports)
    from .scripts.fda_api_client import FDAClient
    from .scripts.fda_data_store import get_projects_dir, load_manifest, save_manifest

    __all__ = [
        # Version
        "__version__",
        # Library
        "GapAnalyzer",
        "FDAEnrichment",
        "PredicateRanker",
        "ExpertValidator",
        "CombinationProductDetector",
        "eCopyExporter",
        "get_csv_header_disclaimer",
        "get_html_banner_disclaimer",
        "get_markdown_header_disclaimer",
        "safe_import",
        "safe_import_from",
        "setup_logging",
        "get_logger",
        "SecureConfig",
        # Scripts
        "FDAClient",
        "get_projects_dir",
        "load_manifest",
        "save_manifest",
    ]
except ImportError:
    # Graceful degradation if modules not available
    __all__ = ["__version__"]
