#!/usr/bin/env python3
"""
Input Validation Library for FDA Tools (FDA-124).

Provides typed, reusable validation functions for all CLI arguments and
API inputs to prevent injection, path traversal, and malformed-data bugs.

Complements ``lib/path_validator.py`` (output-path allowlisting) and
``lib/secure_argparse.py`` (argparse integration) with FDA-domain-specific
validators and general-purpose guards for email, URL, and JSON.

Regulatory basis: 21 CFR Part 11 compliance requires that electronic
records systems validate input data to ensure data integrity.

Validators raise ``ValueError`` on invalid input.  All string inputs are
stripped of leading/trailing whitespace before validation.

Usage::

    from fda_tools.lib.input_validators import (
        validate_product_code,
        validate_k_number,
        validate_project_name,
        validate_path_safe,
        validate_email,
        validate_url,
        validate_json_schema,
    )

    code = validate_product_code(args.product_code)       # "DQY"
    kn   = validate_k_number(args.k_number)               # "K241335"
    name = validate_project_name(args.project)            # "my-device"
    path = validate_path_safe(args.output, base_dir)      # "/safe/abs/path"
    addr = validate_email(args.email)                     # "user@example.com"
    url  = validate_url(args.webhook)                     # "https://example.com/hook"
    validate_json_schema(data_dict, schema_dict)          # raises on violation
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_PRODUCT_CODE_LENGTH = 3
MAX_K_NUMBER_LENGTH = 8        # e.g. K2412345
MAX_PROJECT_NAME_LENGTH = 128
MAX_PATH_LENGTH = 4096
MAX_EMAIL_LENGTH = 254         # RFC 5321
MAX_URL_LENGTH = 2048

# Regex patterns
_PRODUCT_CODE_RE = re.compile(r"^[A-Z]{3}$")
_K_NUMBER_RE = re.compile(r"^[KkPp]\d{6,7}$")
_PROJECT_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-\.]{0,127}$")
_PMA_NUMBER_RE = re.compile(r"^P\d{6}(?:/S\d{3,4})?$", re.IGNORECASE)

# Simplified RFC-5322-compliant email pattern (local@domain)
# Deliberately avoids full RFC complexity while rejecting obviously invalid addresses.
_EMAIL_LOCAL_RE = re.compile(r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+$")
_EMAIL_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

# Allowed URL schemes
_ALLOWED_SCHEMES = frozenset({"http", "https"})


# ---------------------------------------------------------------------------
# FDA-specific validators
# ---------------------------------------------------------------------------


def validate_product_code(code: str) -> str:
    """Validate and normalise an FDA product code.

    Product codes are exactly 3 uppercase ASCII letters (e.g. DQY, OVE).

    Args:
        code: Raw product code input.

    Returns:
        Normalised (uppercase) product code.

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

    if not _PRODUCT_CODE_RE.match(code):
        raise ValueError(
            f"Invalid product code '{code}'. "
            f"Must be exactly 3 uppercase letters (e.g. DQY, OVE)"
        )

    return code


def validate_product_codes(codes: List[str]) -> List[str]:
    """Validate a list of product codes.

    Args:
        codes: List of raw product code strings.

    Returns:
        List of validated, normalised product codes.

    Raises:
        ValueError: If any code is invalid.
    """
    if not codes:
        raise ValueError("At least one product code is required")
    return [validate_product_code(c) for c in codes]


def validate_k_number(k_number: str) -> str:
    """Validate and normalise a 510(k) K-number or PMA P-number.

    K-numbers: K followed by 6-7 digits (e.g. K241335).
    P-numbers: P followed by 6-7 digits (e.g. P170019).

    Args:
        k_number: Raw K-number input.

    Returns:
        Normalised K-number (uppercase).

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

    if not _K_NUMBER_RE.match(k_number):
        raise ValueError(
            f"Invalid K-number '{k_number}'. "
            f"Must match pattern K######[#] or P######[#] (e.g. K241335)"
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


def validate_pma_number(pma_number: str) -> str:
    """Validate a PMA number.

    PMA numbers follow the pattern P followed by 6 digits, optionally
    with a supplement suffix /S### or /S#### (e.g. P170019, P170019/S001).

    Args:
        pma_number: Raw PMA number input.

    Returns:
        Normalised PMA number (uppercase).

    Raises:
        ValueError: If the PMA number does not match expected format.
    """
    if not pma_number or not isinstance(pma_number, str):
        raise ValueError("PMA number must be a non-empty string")

    pma_number = pma_number.strip().upper()

    if not _PMA_NUMBER_RE.match(pma_number):
        raise ValueError(
            f"Invalid PMA number '{pma_number}'. "
            f"Must match pattern P###### or P######/S### (e.g. P170019)"
        )

    return pma_number


def validate_project_name(name: str) -> str:
    """Validate a project name for safe filesystem use.

    Project names must start with an alphanumeric character, followed by
    alphanumerics, hyphens, underscores, or dots.  Path separators and
    parent-directory references are rejected.

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

    if os.sep in name or "/" in name or "\\" in name:
        raise ValueError(
            f"Project name must not contain path separators: '{name}'"
        )

    if ".." in name:
        raise ValueError(f"Project name must not contain '..': '{name}'")

    if not _PROJECT_NAME_RE.match(name):
        raise ValueError(
            f"Invalid project name '{name}'. "
            f"Must be alphanumeric with optional hyphens, underscores, and dots"
        )

    return name


def validate_path_safe(
    user_path: str, base_dir: Optional[str] = None
) -> str:
    """Validate and canonicalise a file path, preventing traversal.

    If *base_dir* is provided, ensures the resolved path is within that
    directory (prevents path-traversal attacks like ``../../etc/``).

    Args:
        user_path: Raw path input from user.
        base_dir: Optional base directory to constrain path within.

    Returns:
        Canonicalised absolute path.

    Raises:
        ValueError: If the path escapes the base directory or is invalid.
    """
    if not user_path or not isinstance(user_path, str):
        raise ValueError("Path must be a non-empty string")

    if len(user_path) > MAX_PATH_LENGTH:
        raise ValueError(
            f"Path too long: {len(user_path)} chars (max {MAX_PATH_LENGTH})"
        )

    resolved = os.path.realpath(os.path.expanduser(user_path))

    if base_dir:
        base_resolved = os.path.realpath(os.path.expanduser(base_dir))
        if (
            not resolved.startswith(base_resolved + os.sep)
            and resolved != base_resolved
        ):
            raise ValueError(
                f"Path traversal detected: '{user_path}' resolves outside "
                f"base directory '{base_dir}'"
            )

    return resolved


def validate_positive_int(
    value: str, name: str = "value", max_val: int = 100_000
) -> int:
    """Validate that a string is a positive integer within bounds.

    Args:
        value: Raw string value.
        name: Parameter name used in error messages.
        max_val: Maximum allowed value (inclusive).

    Returns:
        Validated integer.

    Raises:
        ValueError: If the value is not a positive integer or exceeds *max_val*.
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


# ---------------------------------------------------------------------------
# New validators (FDA-124)
# ---------------------------------------------------------------------------


def validate_email(address: str) -> str:
    """Validate an email address (RFC 5321 simplified).

    Checks structural validity — local@domain — without performing DNS
    resolution.  Rejects addresses with control characters or obvious
    injection payloads.

    Args:
        address: Raw email address string.

    Returns:
        Lowercase-normalised email address.

    Raises:
        ValueError: If the address is structurally invalid.
    """
    if not address or not isinstance(address, str):
        raise ValueError("Email address must be a non-empty string")

    address = address.strip()

    if len(address) > MAX_EMAIL_LENGTH:
        raise ValueError(
            f"Email address too long: {len(address)} chars (max {MAX_EMAIL_LENGTH})"
        )

    # Must contain exactly one '@'
    parts = address.split("@")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid email address '{address}': must contain exactly one '@'"
        )

    local, domain = parts

    if not local:
        raise ValueError(f"Invalid email address '{address}': empty local part")

    if not domain:
        raise ValueError(f"Invalid email address '{address}': empty domain part")

    if not _EMAIL_LOCAL_RE.match(local):
        raise ValueError(
            f"Invalid email address '{address}': "
            f"local part contains invalid characters"
        )

    if not _EMAIL_DOMAIN_RE.match(domain):
        raise ValueError(
            f"Invalid email address '{address}': "
            f"domain '{domain}' is not a valid hostname"
        )

    return address.lower()


def validate_url(url: str, *, allow_schemes: Optional[List[str]] = None) -> str:
    """Validate an HTTP/HTTPS URL.

    Ensures the URL has a scheme, netloc (hostname), and no credentials
    embedded in the URL (prevents SSRF via @ injection).

    Args:
        url: Raw URL string.
        allow_schemes: Allowed URI schemes.  Defaults to ``["http", "https"]``.

    Returns:
        The validated URL (stripped of whitespace).

    Raises:
        ValueError: If the URL is structurally invalid or uses a disallowed scheme.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    url = url.strip()

    if len(url) > MAX_URL_LENGTH:
        raise ValueError(f"URL too long: {len(url)} chars (max {MAX_URL_LENGTH})")

    allowed = frozenset(allow_schemes) if allow_schemes else _ALLOWED_SCHEMES

    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise ValueError(f"Could not parse URL '{url}': {exc}") from exc

    if not parsed.scheme:
        raise ValueError(f"URL '{url}' is missing a scheme (http/https)")

    if parsed.scheme not in allowed:
        raise ValueError(
            f"URL scheme '{parsed.scheme}' is not allowed. "
            f"Allowed schemes: {sorted(allowed)}"
        )

    if not parsed.netloc:
        raise ValueError(f"URL '{url}' is missing a hostname")

    # Reject embedded credentials (user:pass@host)
    if parsed.username or parsed.password:
        raise ValueError(
            f"URL '{url}' must not contain embedded credentials"
        )

    return url


def validate_json_schema(data: Any, schema: Any) -> None:
    """Validate *data* against a simplified JSON schema (stdlib-only).

    Supports a subset of JSON Schema draft-07:

    * ``type``: ``"object"``, ``"array"``, ``"string"``, ``"number"``,
      ``"integer"``, ``"boolean"``, ``"null"``
    * ``required``: list of required property names (for object types)
    * ``properties``: nested sub-schemas for object properties
    * ``items``: sub-schema applied to all array items
    * ``minLength`` / ``maxLength``: string length constraints
    * ``minimum`` / ``maximum``: numeric bounds (inclusive)
    * ``enum``: allowed values list

    Args:
        data: The Python object to validate.
        schema: A dict describing the expected structure (see above).

    Raises:
        ValueError: If *data* does not conform to *schema*.
        TypeError: If *schema* is not a dict.
    """
    if not isinstance(schema, dict):
        raise TypeError(f"Schema must be a dict, got {type(schema).__name__}")

    _validate_node(data, schema, path="$")


# ---------------------------------------------------------------------------
# JSON schema internals
# ---------------------------------------------------------------------------

_JSON_TYPE_MAP: Dict[str, Any] = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


def _validate_node(value: Any, schema: Dict[str, Any], path: str) -> None:
    """Recursively validate *value* against *schema* at *path*."""

    # type check
    expected_type = schema.get("type")
    if expected_type is not None:
        py_type = _JSON_TYPE_MAP.get(expected_type)
        if py_type is None:
            raise ValueError(f"Unknown schema type '{expected_type}' at {path}")
        # bool is a subclass of int; reject bool when integer/number expected
        if expected_type in ("number", "integer") and isinstance(value, bool):
            raise ValueError(
                f"{path}: expected {expected_type}, got boolean"
            )
        if not isinstance(value, py_type):
            raise ValueError(
                f"{path}: expected {expected_type}, "
                f"got {type(value).__name__}"
            )

    # enum check
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(
            f"{path}: value {value!r} not in allowed values {schema['enum']}"
        )

    # string constraints
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ValueError(
                f"{path}: string length {len(value)} < "
                f"minLength {schema['minLength']}"
            )
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ValueError(
                f"{path}: string length {len(value)} > "
                f"maxLength {schema['maxLength']}"
            )

    # numeric constraints
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(
                f"{path}: value {value} < minimum {schema['minimum']}"
            )
        if "maximum" in schema and value > schema["maximum"]:
            raise ValueError(
                f"{path}: value {value} > maximum {schema['maximum']}"
            )

    # object constraints
    if isinstance(value, dict):
        required = schema.get("required", [])
        for req_key in required:
            if req_key not in value:
                raise ValueError(
                    f"{path}: missing required property '{req_key}'"
                )
        props = schema.get("properties", {})
        for prop_name, prop_schema in props.items():
            if prop_name in value:
                _validate_node(
                    value[prop_name], prop_schema, path=f"{path}.{prop_name}"
                )

    # array constraints
    if isinstance(value, list):
        items_schema = schema.get("items")
        if items_schema is not None:
            for idx, item in enumerate(value):
                _validate_node(item, items_schema, path=f"{path}[{idx}]")
