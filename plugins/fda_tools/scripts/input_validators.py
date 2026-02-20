#!/usr/bin/env python3
"""
Input Validation Module for FDA Tools CLI Scripts.

Provides shared validation functions for all CLI arguments to prevent:
- Product code injection / malformed queries
- Path traversal attacks
- Invalid K-number formats
- Excessively long arguments (DoS prevention)

Regulatory basis: 21 CFR Part 11 compliance requires that electronic
records systems validate input data to ensure data integrity.

Usage:
    from input_validators import (
        validate_product_code,
        validate_k_number,
        validate_project_name,
        validate_path_safe,
    )

    # Raises ValueError on invalid input
    code = validate_product_code(args.product_code)
    k_num = validate_k_number(args.k_number)
    name = validate_project_name(args.project)
    path = validate_path_safe(args.output_dir, base_dir)
"""

import os
import re
from typing import List, Optional


# Maximum argument lengths (DoS prevention)
MAX_PRODUCT_CODE_LENGTH = 3
MAX_K_NUMBER_LENGTH = 8  # e.g., K2412345
MAX_PROJECT_NAME_LENGTH = 128
MAX_PATH_LENGTH = 4096

# Regex patterns
PRODUCT_CODE_PATTERN = re.compile(r'^[A-Z]{3}$')
K_NUMBER_PATTERN = re.compile(r'^[KkPp]\d{6,7}$')
PROJECT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_\-\.]{0,127}$')
PMA_NUMBER_PATTERN = re.compile(r'^P\d{6}(?:/S\d{3,4})?$', re.IGNORECASE)


def validate_product_code(code: str) -> str:
    """Validate and normalize an FDA product code.

    Product codes are exactly 3 uppercase ASCII letters (e.g., DQY, OVE).

    Args:
        code: Raw product code input.

    Returns:
        Normalized (uppercase) product code.

    Raises:
        ValueError: If the code is not exactly 3 uppercase letters.
    """
    if not code or not isinstance(code, str):
        raise ValueError("Product code must be a non-empty string")

    code = code.strip().upper()

    if len(code) > MAX_PRODUCT_CODE_LENGTH:
        raise ValueError(
            f"Product code must be exactly 3 letters, got {len(code)} chars"
        )

    if not PRODUCT_CODE_PATTERN.match(code):
        raise ValueError(
            f"Invalid product code '{code}'. "
            f"Must be exactly 3 uppercase letters (e.g., DQY, OVE)"
        )

    return code


def validate_product_codes(codes: List[str]) -> List[str]:
    """Validate a list of product codes.

    Args:
        codes: List of raw product code strings.

    Returns:
        List of validated, normalized product codes.

    Raises:
        ValueError: If any code is invalid.
    """
    if not codes:
        raise ValueError("At least one product code is required")
    return [validate_product_code(c) for c in codes]


def validate_k_number(k_number: str) -> str:
    """Validate and normalize a 510(k) K-number.

    K-numbers follow the pattern K followed by 6-7 digits (e.g., K241335).
    PMA numbers follow P followed by 6 digits (e.g., P170019).

    Args:
        k_number: Raw K-number input.

    Returns:
        Normalized K-number (uppercase first letter).

    Raises:
        ValueError: If the K-number does not match expected format.
    """
    if not k_number or not isinstance(k_number, str):
        raise ValueError("K-number must be a non-empty string")

    k_number = k_number.strip().upper()

    if len(k_number) > MAX_K_NUMBER_LENGTH:
        raise ValueError(
            f"K-number too long: {len(k_number)} chars (max {MAX_K_NUMBER_LENGTH})"
        )

    if not K_NUMBER_PATTERN.match(k_number):
        raise ValueError(
            f"Invalid K-number '{k_number}'. "
            f"Must match pattern K######[#] (e.g., K241335)"
        )

    return k_number


def validate_k_numbers(k_numbers: str) -> List[str]:
    """Validate a comma-separated list of K-numbers.

    Args:
        k_numbers: Comma-separated string of K-numbers.

    Returns:
        List of validated K-numbers.

    Raises:
        ValueError: If any K-number is invalid.
    """
    if not k_numbers or not isinstance(k_numbers, str):
        raise ValueError("K-numbers must be a non-empty comma-separated string")

    parts = [kn.strip() for kn in k_numbers.split(",") if kn.strip()]
    if not parts:
        raise ValueError("No valid K-numbers found in input")

    return [validate_k_number(kn) for kn in parts]


def validate_project_name(name: str) -> str:
    """Validate a project name for safe filesystem use.

    Project names must be alphanumeric with hyphens, underscores, and dots.
    No path separators allowed (prevents traversal).

    Args:
        name: Raw project name input.

    Returns:
        Validated project name.

    Raises:
        ValueError: If the name contains unsafe characters.
    """
    if not name or not isinstance(name, str):
        raise ValueError("Project name must be a non-empty string")

    name = name.strip()

    if len(name) > MAX_PROJECT_NAME_LENGTH:
        raise ValueError(
            f"Project name too long: {len(name)} chars (max {MAX_PROJECT_NAME_LENGTH})"
        )

    # Check for path separators (traversal prevention)
    if os.sep in name or "/" in name or "\\" in name:
        raise ValueError(
            f"Project name must not contain path separators: '{name}'"
        )

    # Check for parent directory traversal
    if ".." in name:
        raise ValueError(
            f"Project name must not contain '..': '{name}'"
        )

    if not PROJECT_NAME_PATTERN.match(name):
        raise ValueError(
            f"Invalid project name '{name}'. "
            f"Must be alphanumeric with optional hyphens, underscores, and dots"
        )

    return name


def validate_path_safe(
    user_path: str, base_dir: Optional[str] = None
) -> str:
    """Validate and canonicalize a file path, preventing traversal.

    If a base_dir is provided, ensures the resolved path is within
    that directory (prevents path traversal attacks like ../../etc/).

    Args:
        user_path: Raw path input from user.
        base_dir: Optional base directory to constrain path within.

    Returns:
        Canonicalized absolute path.

    Raises:
        ValueError: If the path escapes the base directory or is invalid.
    """
    if not user_path or not isinstance(user_path, str):
        raise ValueError("Path must be a non-empty string")

    if len(user_path) > MAX_PATH_LENGTH:
        raise ValueError(
            f"Path too long: {len(user_path)} chars (max {MAX_PATH_LENGTH})"
        )

    # Resolve to absolute path
    resolved = os.path.realpath(os.path.expanduser(user_path))

    if base_dir:
        base_resolved = os.path.realpath(os.path.expanduser(base_dir))
        # Ensure resolved path is within base_dir
        if not resolved.startswith(base_resolved + os.sep) and resolved != base_resolved:
            raise ValueError(
                f"Path traversal detected: '{user_path}' resolves outside "
                f"base directory '{base_dir}'"
            )

    return resolved


def validate_pma_number(pma_number: str) -> str:
    """Validate a PMA number.

    PMA numbers follow the pattern P followed by 6 digits, optionally
    with a supplement suffix /S### or /S#### (e.g., P170019, P170019/S001).

    Args:
        pma_number: Raw PMA number input.

    Returns:
        Normalized PMA number (uppercase).

    Raises:
        ValueError: If the PMA number does not match expected format.
    """
    if not pma_number or not isinstance(pma_number, str):
        raise ValueError("PMA number must be a non-empty string")

    pma_number = pma_number.strip().upper()

    if not PMA_NUMBER_PATTERN.match(pma_number):
        raise ValueError(
            f"Invalid PMA number '{pma_number}'. "
            f"Must match pattern P###### (e.g., P170019)"
        )

    return pma_number


def validate_positive_int(value: str, name: str = "value", max_val: int = 100000) -> int:
    """Validate that a string is a positive integer within bounds.

    Args:
        value: Raw string value.
        name: Name of the parameter (for error messages).
        max_val: Maximum allowed value.

    Returns:
        Validated integer.

    Raises:
        ValueError: If the value is not a positive integer or exceeds max.
    """
    try:
        num = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be a positive integer, got '{value}'")

    if num <= 0:
        raise ValueError(f"{name} must be positive, got {num}")

    if num > max_val:
        raise ValueError(f"{name} too large: {num} (max {max_val})")

    return num
