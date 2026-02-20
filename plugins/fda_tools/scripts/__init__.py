"""FDA Tools Plugin - Scripts Package

This __init__.py enables proper Python package imports and pytest
coverage measurement for the scripts directory.

Public API exports for commonly used modules and classes.

REFACTORED: Uses import_helpers (FDA-17 / GAP-015) for safe imports.
"""

import os
import sys

# Import helpers for safe optional imports (using package imports)
from fda_tools.lib.import_helpers import safe_import, safe_import_from

# Core API client (most frequently imported)
result = safe_import(
    'scripts.fda_api_client',
    'FDAClient',
    alternative_names=['fda_api_client']
)
FDAClient = result.module

# Data stores
result = safe_import(
    'scripts.pma_data_store',
    'PMADataStore',
    alternative_names=['pma_data_store']
)
PMADataStore = result.module

# FDA data store functions
fda_store_result = safe_import(
    'scripts.fda_data_store',
    alternative_names=['fda_data_store']
)
if fda_store_result.success:
    imports = safe_import_from(
        'fda_data_store',
        ['get_projects_dir', 'load_manifest', 'save_manifest', 'make_query_key']
    )
    get_projects_dir = imports['get_projects_dir']
    load_manifest = imports['load_manifest']
    save_manifest = imports['save_manifest']
    make_query_key = imports['make_query_key']
else:
    get_projects_dir = None
    load_manifest = None
    save_manifest = None
    make_query_key = None

# Cache integrity (GAP-011)
cache_result = safe_import(
    'scripts.cache_integrity',
    alternative_names=['cache_integrity']
)
if cache_result.success:
    imports = safe_import_from(
        'cache_integrity',
        ['integrity_read', 'integrity_write', 'verify_checksum', 'invalidate_corrupt_file']
    )
    integrity_read = imports['integrity_read']
    integrity_write = imports['integrity_write']
    verify_checksum = imports['verify_checksum']
    invalidate_corrupt_file = imports['invalidate_corrupt_file']
else:
    integrity_read = None
    integrity_write = None
    verify_checksum = None
    invalidate_corrupt_file = None

# Unified predicate analyzer
result = safe_import(
    'scripts.unified_predicate',
    'UnifiedPredicateAnalyzer',
    alternative_names=['unified_predicate']
)
UnifiedPredicateAnalyzer = result.module

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
