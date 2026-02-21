#!/usr/bin/env python3
"""Import Helper Utilities

Provides safe import patterns with proper error handling and logging.
Eliminates duplicate try/except (ImportError, Exception) patterns across scripts.

Created as part of FDA-17 (GAP-015) refactoring effort.

Usage:
from fda_tools.lib.import_helpers import safe_import, try_optional_import, ImportResult

    # For optional dependencies with fallback
    sklearn = try_optional_import('sklearn', package_name='scikit-learn')
    if sklearn.success:
        from sklearn.ensemble import RandomForestRegressor

    # For conditional module imports
    result = safe_import('annual_report_tracker', 'AnnualReportTracker')
    if result.success:
        tracker = result.module.AnnualReportTracker(store=store)
"""

import logging
import importlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, List, Callable

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Result of an import attempt with detailed status information.

    Attributes:
        success: Whether the import succeeded
        module: The imported module (or None if failed)
        error: The exception that occurred (or None if succeeded)
        error_type: Type of error ('import', 'attribute', 'syntax', 'other')
        fallback_used: Whether a fallback value was used
    """
    success: bool
    module: Optional[Any] = None
    error: Optional[Exception] = None
    error_type: Optional[str] = None
    fallback_used: bool = False

    def __bool__(self) -> bool:
        """Allow boolean evaluation: if result: ..."""
        return self.success


def safe_import(
    module_name: str,
    class_or_function_name: Optional[str] = None,
    *,
    fallback: Optional[Any] = None,
    required: bool = False,
    log_level: int = logging.DEBUG,
    alternative_names: Optional[List[str]] = None,
) -> ImportResult:
    """Safely import a module or specific attribute with proper error handling.

    This function separates ImportError (missing package) from other exceptions
    (broken code, syntax errors) and provides detailed logging.

    Args:
        module_name: Name of the module to import (e.g., 'fda_api_client')
        class_or_function_name: Optional specific class/function to extract
        fallback: Value to return if import fails (default: None)
        required: If True, log at WARNING level for failures (default: DEBUG)
        log_level: Logging level for optional dependencies (default: DEBUG)
        alternative_names: Alternative module names to try (e.g., ['scripts.module', 'module'])

    Returns:
        ImportResult with success status, module/attribute, and error details

    Examples:
        # Import entire module
        result = safe_import('pandas')
        if result.success:
            pd = result.module
            df = pd.DataFrame(...)

        # Import specific class
        result = safe_import('annual_report_tracker', 'AnnualReportTracker')
        if result.success:
            AnnualReportTracker = result.module
            tracker = AnnualReportTracker()

        # With fallback and alternatives
        result = safe_import(
            'fda_http',
            'create_session',
            fallback=lambda: requests.Session(),
            alternative_names=['scripts.fda_http']
        )
        create_session = result.module if result.success else result.fallback
    """
    module_names_to_try = [module_name]
    if alternative_names:
        module_names_to_try.extend(alternative_names)

    last_error = None
    last_error_type = None

    for name in module_names_to_try:
        try:
            # Attempt module import
            module = importlib.import_module(name)

            # If specific attribute requested, extract it
            if class_or_function_name:
                try:
                    attr = getattr(module, class_or_function_name)
                    logger.log(
                        log_level,
                        f"Successfully imported {class_or_function_name} from {name}"
                    )
                    return ImportResult(
                        success=True,
                        module=attr,
                        error=None,
                        error_type=None,
                        fallback_used=False
                    )
                except AttributeError as e:
                    last_error = e
                    last_error_type = 'attribute'
                    logger.log(
                        logging.WARNING if required else log_level,
                        f"Module {name} exists but missing attribute {class_or_function_name}: {e}"
                    )
                    continue  # Try next alternative
            else:
                logger.log(log_level, f"Successfully imported module {name}")
                return ImportResult(
                    success=True,
                    module=module,
                    error=None,
                    error_type=None,
                    fallback_used=False
                )

        except ImportError as e:
            last_error = e
            last_error_type = 'import'
            logger.log(
                logging.WARNING if required else log_level,
                f"Module {name} not available (not installed or not in path): {e}"
            )
            continue  # Try next alternative

        except SyntaxError as e:
            # Syntax errors indicate broken code, should be logged as errors
            last_error = e
            last_error_type = 'syntax'
            logger.error(
                f"Syntax error in module {name} (broken code): {e}",
                exc_info=True
            )
            break  # Don't try alternatives for syntax errors

        except Exception as e:
            # Other exceptions (TypeError, ValueError, etc.) indicate bugs
            last_error = e
            last_error_type = 'other'
            logger.error(
                f"Unexpected error importing {name}: {type(e).__name__}: {e}",
                exc_info=True
            )
            break  # Don't try alternatives for unexpected errors

    # All attempts failed
    target_desc = f"{class_or_function_name} from {module_name}" if class_or_function_name else module_name
    logger.log(
        logging.WARNING if required else log_level,
        f"Failed to import {target_desc} (tried {len(module_names_to_try)} alternatives)"
    )

    return ImportResult(
        success=False,
        module=fallback,
        error=last_error,
        error_type=last_error_type,
        fallback_used=fallback is not None
    )


def try_optional_import(
    module_name: str,
    *,
    package_name: Optional[str] = None,
    min_version: Optional[str] = None,
    log_level: int = logging.DEBUG
) -> ImportResult:
    """Try importing an optional dependency with helpful error messages.

    Args:
        module_name: Module to import (e.g., 'sklearn')
        package_name: Package name for pip install (e.g., 'scikit-learn')
        min_version: Minimum required version (e.g., '1.0.0')
        log_level: Logging level for import failures

    Returns:
        ImportResult with success status and module

    Example:
        sklearn = try_optional_import('sklearn', package_name='scikit-learn', min_version='1.0.0')
        if sklearn.success:
            from sklearn.ensemble import RandomForestRegressor
        else:
            print(f"scikit-learn not available, some features disabled")
    """
    result = safe_import(module_name, log_level=log_level)

    if not result.success:
        pkg_name = package_name or module_name
        logger.log(
            log_level,
            f"Optional dependency '{pkg_name}' not available. "
            f"Install with: pip install {pkg_name}"
        )
        return result

    # Check version if specified
    if min_version and result.module:
        try:
            import importlib.metadata
            installed_version = importlib.metadata.version(package_name or module_name)

            # Simple version comparison (assumes semantic versioning)
            from packaging import version
            if version.parse(installed_version) < version.parse(min_version):
                logger.warning(
                    f"Module {module_name} version {installed_version} is below "
                    f"minimum required version {min_version}"
                )
        except Exception as e:
            logger.debug(f"Could not verify version for {module_name}: {e}")

    return result


def safe_import_from(
    module_name: str,
    names: List[str],
    *,
    required: bool = False,
    log_level: int = logging.DEBUG
) -> dict:
    """Safely import multiple names from a module.

    Args:
        module_name: Module to import from
        names: List of names to import
        required: Whether to log failures as warnings
        log_level: Logging level for optional imports

    Returns:
        Dictionary mapping name -> imported object (or None if failed)

    Example:
        imports = safe_import_from('fda_data_store', [
            'get_projects_dir',
            'load_manifest',
            'save_manifest'
        ])
        get_projects_dir = imports['get_projects_dir']
        load_manifest = imports['load_manifest']
    """
    result = {}
    module_result = safe_import(module_name, required=required, log_level=log_level)

    if not module_result.success:
        # Module not available, return all None
        return {name: None for name in names}

    module = module_result.module
    for name in names:
        try:
            result[name] = getattr(module, name)
        except AttributeError:
            logger.log(
                logging.WARNING if required else log_level,
                f"Module {module_name} missing attribute {name}"
            )
            result[name] = None

    return result


def conditional_import(
    condition: Callable[[], bool],
    module_name: str,
    class_or_function_name: Optional[str] = None,
    **kwargs
) -> ImportResult:
    """Conditionally import a module only if a condition is met.

    Useful for environment-specific imports or feature flags.

    Args:
        condition: Callable that returns True if import should be attempted
        module_name: Module to import
        class_or_function_name: Optional specific attribute
        **kwargs: Additional arguments passed to safe_import

    Returns:
        ImportResult (success=False if condition not met)

    Example:
        # Only import on Linux
        result = conditional_import(
            lambda: sys.platform == 'linux',
            'linux_specific_module'
        )
    """
    if not condition():
        logger.debug(f"Skipping import of {module_name} (condition not met)")
        return ImportResult(
            success=False,
            module=None,
            error=None,
            error_type='condition_not_met',
            fallback_used=False
        )

    return safe_import(module_name, class_or_function_name, **kwargs)


# Convenience function for backward compatibility with existing patterns
def try_import_with_alternatives(*module_names: str) -> ImportResult:
    """Try importing from a list of alternative module names.

    This is a convenience wrapper for the common pattern of trying
    both 'scripts.module' and 'module' imports.

    Args:
        *module_names: Module names to try in order

    Returns:
        ImportResult for first successful import, or failed result

    Example:
        result = try_import_with_alternatives(
            'scripts.fda_api_client',
            'fda_api_client'
        )
        if result.success:
            FDAClient = result.module.FDAClient
    """
    if not module_names:
        raise ValueError("Must provide at least one module name")

    first_name = module_names[0]
    alternatives = list(module_names[1:]) if len(module_names) > 1 else None

    return safe_import(first_name, alternative_names=alternatives)


def parse_fda_date(date_str: str) -> Optional[datetime]:
    """Parse an FDA date string in YYYYMMDD or YYYY-MM-DD format.

    Consolidates the duplicate _parse_date() implementations previously found
    in pas_monitor.py and annual_report_tracker.py.

    Args:
        date_str: Date string in YYYYMMDD (FDA default) or YYYY-MM-DD format.

    Returns:
        Parsed datetime object, or None if input is empty or parsing fails.

    Examples:
        parse_fda_date("20240615")   # -> datetime(2024, 6, 15)
        parse_fda_date("2024-06-15") # -> datetime(2024, 6, 15)
        parse_fda_date("")           # -> None
        parse_fda_date("bad-input")  # -> None (with debug log)
    """
    if not date_str:
        return None

    # Try YYYYMMDD format (FDA default)
    try:
        return datetime.strptime(date_str[:8], "%Y%m%d")
    except (ValueError, TypeError):
        logger.debug("parse_fda_date: YYYYMMDD format failed for %r, trying ISO format", date_str)

    # Try YYYY-MM-DD format
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        logger.debug("parse_fda_date: all formats failed for %r", date_str)

    return None


__all__ = [
    'ImportResult',
    'safe_import',
    'try_optional_import',
    'safe_import_from',
    'conditional_import',
    'try_import_with_alternatives',
    'parse_fda_date',
]
