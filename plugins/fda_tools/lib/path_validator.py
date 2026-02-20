#!/usr/bin/env python3
"""
Output Path Validation (FDA-111)

Provides secure path validation for output file operations to prevent
arbitrary file write attacks (CWE-73: External Control of File Name or Path).

Features:
  1. Allowlist-based path validation
  2. Path traversal detection and blocking
  3. Sensitive directory protection
  4. Configurable safe zones

Security Model:
  - Only paths within allowlisted directories are permitted
  - Blocks writes to sensitive system paths (/etc/, /root/, etc.)
  - Prevents path traversal attacks (../, symlink following)
  - Validates parent directories exist
  - Comprehensive audit logging

Usage:
    from fda_tools.lib.path_validator import OutputPathValidator

    validator = OutputPathValidator()

    # Validate output path
    safe_path = validator.validate_output_path("/path/to/output.json")

    # Configure custom allowlist
    validator = OutputPathValidator(
        allowed_dirs=[
            "~/fda-510k-data/",
            "./output/",
            "/tmp/fda-*"
        ]
    )

    # Check if path is allowed
    if validator.is_path_allowed("/some/path"):
        # Safe to write
        pass

Validation Rules:
  1. Path must be within allowed directories
  2. Path must not contain ".." components
  3. Path must not be a symlink to blocked location
  4. Parent directory must exist or be creatable
  5. Path must not target sensitive system directories

References:
  - CWE-73: External Control of File Name or Path
  - OWASP: Path Traversal
  - FDA-111: Unvalidated Output Path Security Issue
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Union
import re

logger = logging.getLogger(__name__)


class PathValidationError(Exception):
    """Raised when output path validation fails."""
    pass


class OutputPathValidator:
    """
    Validates output file paths to prevent arbitrary file write attacks.

    Enforces allowlist-based path restrictions and prevents path traversal.
    """

    # Default allowed directories (expandable via constructor)
    DEFAULT_ALLOWED_DIRS = [
        "~/fda-510k-data/",     # Primary data directory
        "./",                    # Current working directory
        "/tmp/fda-",            # Temp files with fda- prefix
    ]

    # Blocked directories (always forbidden, regardless of allowlist)
    BLOCKED_DIRS = [
        "/etc/",
        "/root/",
        "/var/",
        "/usr/",
        "/bin/",
        "/sbin/",
        "/boot/",
        "/sys/",
        "/proc/",
        "/dev/",
        "/lib/",
        "/lib64/",
        "/opt/",
        "/srv/",
        "~/.ssh/",
        "~/.aws/",
        "~/.config/",
        "~/.local/bin/",
    ]

    # Maximum allowed path depth (to prevent directory traversal)
    MAX_PATH_DEPTH = 20

    def __init__(
        self,
        allowed_dirs: Optional[List[str]] = None,
        strict_mode: bool = True
    ):
        """
        Initialize path validator.

        Args:
            allowed_dirs: Custom list of allowed directories (replaces defaults if provided)
            strict_mode: If True, enforce strict validation (default: True)
        """
        self.allowed_dirs = allowed_dirs if allowed_dirs is not None else self.DEFAULT_ALLOWED_DIRS
        self.strict_mode = strict_mode

        # Expand and normalize allowed directories
        self._normalized_allowed_dirs = [
            self._normalize_path(d) for d in self.allowed_dirs
        ]

        # Expand and normalize blocked directories
        self._normalized_blocked_dirs = [
            self._normalize_path(d) for d in self.BLOCKED_DIRS
        ]

        logger.debug(
            f"Initialized PathValidator with {len(self.allowed_dirs)} allowed dirs, "
            f"strict_mode={self.strict_mode}"
        )

    def _normalize_path(self, path: str) -> Path:
        """
        Normalize and expand path.

        Args:
            path: Raw path string (may contain ~, ./, patterns)

        Returns:
            Normalized absolute Path object
        """
        # Expand user home directory
        expanded = os.path.expanduser(path)

        # Convert to absolute path (relative to cwd)
        abs_path = Path(expanded).resolve()

        return abs_path

    def _matches_pattern(self, path: Path, pattern: Path) -> bool:
        """
        Check if path matches a pattern (supports wildcards).

        Args:
            path: Path to check
            pattern: Pattern path (may contain * wildcards)

        Returns:
            True if path matches pattern
        """
        # Convert to strings for pattern matching
        path_str = str(path)
        pattern_str = str(pattern)

        # Handle wildcard patterns
        if '*' in pattern_str:
            # Convert to regex
            regex_pattern = pattern_str.replace('*', '.*')
            return bool(re.match(regex_pattern, path_str))

        # Direct prefix match
        return path_str.startswith(pattern_str)

    def _is_path_traversal(self, path: str) -> bool:
        """
        Detect path traversal attempts.

        Args:
            path: Path to check

        Returns:
            True if path contains traversal patterns
        """
        # Check for ".." components
        if '..' in Path(path).parts:
            return True

        # Check for multiple consecutive slashes (may bypass filters)
        if '//' in path or '\\\\' in path:
            return True

        # Check for encoded path separators
        if '%2e%2e' in path.lower() or '%2f' in path.lower():
            return True

        return False

    def _is_symlink_to_blocked(self, path: Path) -> bool:
        """
        Check if path is a symlink pointing to blocked directory.

        Args:
            path: Path to check

        Returns:
            True if path is a symlink to blocked location
        """
        if not path.exists():
            # Can't check non-existent paths
            return False

        if path.is_symlink():
            # Resolve symlink target
            target = path.resolve()

            # Check if target is in blocked directory
            for blocked_dir in self._normalized_blocked_dirs:
                if self._matches_pattern(target, blocked_dir):
                    return True

        return False

    def _check_path_depth(self, path: Path) -> None:
        """
        Check if path depth exceeds maximum.

        Args:
            path: Path to check

        Raises:
            PathValidationError: If path depth exceeds limit
        """
        depth = len(path.parts)
        if depth > self.MAX_PATH_DEPTH:
            raise PathValidationError(
                f"Path depth {depth} exceeds maximum {self.MAX_PATH_DEPTH}: {path}"
            )

    def is_path_allowed(self, path: Union[str, Path]) -> bool:
        """
        Check if path is allowed (non-raising version).

        Args:
            path: Path to validate

        Returns:
            True if path is allowed, False otherwise
        """
        try:
            self.validate_output_path(path, raise_on_error=True)
            return True
        except PathValidationError:
            return False

    def validate_output_path(
        self,
        path: Union[str, Path],
        raise_on_error: bool = True,
        create_parent: bool = False
    ) -> Optional[Path]:
        """
        Validate output file path for security.

        Args:
            path: Path to validate
            raise_on_error: If True, raise exception on validation failure
            create_parent: If True, create parent directory if missing

        Returns:
            Normalized absolute path if validation passes

        Raises:
            PathValidationError: If path fails validation
        """
        # Convert to string if Path object
        path_str = str(path)

        # Check for path traversal attempts
        if self._is_path_traversal(path_str):
            msg = f"Path traversal detected: {path_str}"
            logger.error(msg)
            if raise_on_error:
                raise PathValidationError(msg)
            return None

        # Normalize path
        normalized = self._normalize_path(path_str)

        # Check path depth
        try:
            self._check_path_depth(normalized)
        except PathValidationError as e:
            logger.error(str(e))
            if raise_on_error:
                raise
            return None

        # Check if path is in blocked directory
        for blocked_dir in self._normalized_blocked_dirs:
            if self._matches_pattern(normalized, blocked_dir):
                msg = f"Path blocked (sensitive directory): {normalized}"
                logger.error(msg)
                if raise_on_error:
                    raise PathValidationError(msg)
                return None

        # Check if path is allowed
        is_allowed = False
        for allowed_dir in self._normalized_allowed_dirs:
            if self._matches_pattern(normalized, allowed_dir):
                is_allowed = True
                break

        if not is_allowed:
            msg = (
                f"Path not in allowed directories: {normalized}\n"
                f"Allowed: {', '.join(str(d) for d in self._normalized_allowed_dirs)}"
            )
            logger.error(msg)
            if raise_on_error:
                raise PathValidationError(msg)
            return None

        # Check for symlink to blocked location
        if self._is_symlink_to_blocked(normalized):
            msg = f"Symlink to blocked directory: {normalized}"
            logger.error(msg)
            if raise_on_error:
                raise PathValidationError(msg)
            return None

        # Validate parent directory
        parent = normalized.parent
        if not parent.exists():
            if create_parent:
                try:
                    parent.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created parent directory: {parent}")
                except OSError as e:
                    msg = f"Failed to create parent directory {parent}: {e}"
                    logger.error(msg)
                    if raise_on_error:
                        raise PathValidationError(msg)
                    return None
            elif self.strict_mode:
                msg = f"Parent directory does not exist: {parent}"
                logger.error(msg)
                if raise_on_error:
                    raise PathValidationError(msg)
                return None

        # All checks passed
        logger.debug(f"Path validation passed: {normalized}")
        return normalized

    def add_allowed_dir(self, directory: str) -> None:
        """
        Add directory to allowlist.

        Args:
            directory: Directory path to allow
        """
        normalized = self._normalize_path(directory)
        if normalized not in self._normalized_allowed_dirs:
            self._normalized_allowed_dirs.append(normalized)
            self.allowed_dirs.append(directory)
            logger.info(f"Added allowed directory: {directory}")

    def remove_allowed_dir(self, directory: str) -> None:
        """
        Remove directory from allowlist.

        Args:
            directory: Directory path to remove
        """
        normalized = self._normalize_path(directory)
        if normalized in self._normalized_allowed_dirs:
            self._normalized_allowed_dirs.remove(normalized)
            self.allowed_dirs = [d for d in self.allowed_dirs if self._normalize_path(d) != normalized]
            logger.info(f"Removed allowed directory: {directory}")

    def get_allowed_dirs(self) -> List[Path]:
        """
        Get list of normalized allowed directories.

        Returns:
            List of allowed directory Paths
        """
        return self._normalized_allowed_dirs.copy()


# Singleton instance for convenience
_default_validator: Optional[OutputPathValidator] = None


def get_default_validator() -> OutputPathValidator:
    """
    Get default singleton validator instance.

    Returns:
        Default OutputPathValidator instance
    """
    global _default_validator
    if _default_validator is None:
        _default_validator = OutputPathValidator()
    return _default_validator


def validate_output_path(path: Union[str, Path], **kwargs) -> Optional[Path]:
    """
    Convenience function using default validator.

    Args:
        path: Path to validate
        **kwargs: Additional arguments to pass to validate_output_path()

    Returns:
        Validated path, or None if raise_on_error=False and validation fails

    Raises:
        PathValidationError: If validation fails and raise_on_error=True
    """
    validator = get_default_validator()
    return validator.validate_output_path(path, **kwargs)


if __name__ == "__main__":
    # CLI testing interface
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python3 path_validator.py <path-to-validate>")
        sys.exit(1)

    test_path = sys.argv[1]
    validator = get_default_validator()

    try:
        validated = validator.validate_output_path(test_path)
        print(f"✓ Path ALLOWED: {validated}")
        sys.exit(0)
    except PathValidationError as e:
        print(f"✗ Path BLOCKED: {e}")
        sys.exit(1)
