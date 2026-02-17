"""FDA Tools Plugin - Scripts Package

This __init__.py enables proper Python package imports and pytest
coverage measurement for the scripts directory.

Public API exports for commonly used modules and classes.
"""

# Core API client (most frequently imported)
try:
    from scripts.fda_api_client import FDAClient
except ImportError:
    try:
        from fda_api_client import FDAClient
    except ImportError:
        FDAClient = None

# Data stores
try:
    from scripts.pma_data_store import PMADataStore
except ImportError:
    try:
        from pma_data_store import PMADataStore
    except ImportError:
        PMADataStore = None

try:
    from scripts.fda_data_store import (
        get_projects_dir,
        load_manifest,
        save_manifest,
        make_query_key,
    )
except ImportError:
    try:
        from fda_data_store import (
            get_projects_dir,
            load_manifest,
            save_manifest,
            make_query_key,
        )
    except ImportError:
        get_projects_dir = None
        load_manifest = None
        save_manifest = None
        make_query_key = None

# Cache integrity (GAP-011)
try:
    from scripts.cache_integrity import (
        integrity_read,
        integrity_write,
        verify_checksum,
        invalidate_corrupt_file,
    )
except ImportError:
    try:
        from cache_integrity import (
            integrity_read,
            integrity_write,
            verify_checksum,
            invalidate_corrupt_file,
        )
    except ImportError:
        integrity_read = None
        integrity_write = None
        verify_checksum = None
        invalidate_corrupt_file = None

# Unified predicate analyzer
try:
    from scripts.unified_predicate import UnifiedPredicateAnalyzer
except ImportError:
    try:
        from unified_predicate import UnifiedPredicateAnalyzer
    except ImportError:
        UnifiedPredicateAnalyzer = None

__all__ = [
    # API Client
    'FDAClient',
    # Data stores
    'PMADataStore',
    'get_projects_dir',
    'load_manifest',
    'save_manifest',
    'make_query_key',
    # Cache integrity
    'integrity_read',
    'integrity_write',
    'verify_checksum',
    'invalidate_corrupt_file',
    # Analysis
    'UnifiedPredicateAnalyzer',
]
