#!/usr/bin/env python3
"""
FDA Data Manifest Validator -- JSON Schema Validation for data_manifest.json.

Provides validation functionality for FDA project data manifest files using
JSON Schema Draft 2020-12. Ensures data integrity, validates required fields,
and produces helpful error messages for debugging.

Schema Version Support:
    - 1.0.0: Initial schema with 510(k) and PMA support
    - Migration helpers for future schema updates

Usage:
    from manifest_validator import (
        validate_manifest,
        validate_manifest_file,
        ValidationError,
        get_schema_version,
    )

    # Validate in-memory manifest
    try:
        validate_manifest(manifest_dict)
        print("Manifest is valid")
    except ValidationError as e:
        print(f"Validation failed: {e}")

    # Validate manifest file
    errors = validate_manifest_file("/path/to/data_manifest.json")
    if errors:
        for error in errors:
            print(f"  - {error}")

    # Check schema version
    version = get_schema_version(manifest_dict)
    if version != CURRENT_SCHEMA_VERSION:
        print("Migration required")
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import jsonschema
    from jsonschema import Draft202012Validator, validators
    _JSONSCHEMA_AVAILABLE = True
except ImportError:
    _JSONSCHEMA_AVAILABLE = False

# Current schema version
CURRENT_SCHEMA_VERSION = "1.0.0"

# Schema file path (relative to this module)
SCHEMA_PATH = Path(__file__).parent.parent / "data" / "schemas" / "data_manifest.schema.json"


class ValidationError(Exception):
    """Raised when manifest validation fails.

    Attributes:
        message: Human-readable error message
        errors: List of validation error details
        manifest_path: Optional path to the manifest file that failed validation
    """

    def __init__(
        self,
        message: str,
        errors: Optional[List[str]] = None,
        manifest_path: Optional[str] = None,
    ):
        self.message = message
        self.errors = errors or []
        self.manifest_path = manifest_path
        super().__init__(message)

    def __str__(self) -> str:
        if self.manifest_path:
            base = f"Validation failed for {self.manifest_path}: {self.message}"
        else:
            base = f"Validation failed: {self.message}"

        if self.errors:
            error_list = "\n".join(f"  - {e}" for e in self.errors)
            return f"{base}\n{error_list}"
        return base


class SchemaNotFoundError(Exception):
    """Raised when the JSON schema file cannot be found."""
    pass


class JsonSchemaNotInstalledError(Exception):
    """Raised when jsonschema package is not installed."""

    def __init__(self):
        message = (
            "jsonschema package is required for manifest validation. "
            "Install it with: pip install jsonschema"
        )
        super().__init__(message)


def _load_schema() -> Dict[str, Any]:
    """Load the data_manifest JSON schema.

    Returns:
        Schema dictionary.

    Raises:
        SchemaNotFoundError: If schema file does not exist.
    """
    if not SCHEMA_PATH.exists():
        raise SchemaNotFoundError(
            f"Schema file not found at {SCHEMA_PATH}. "
            "Ensure data/schemas/data_manifest.schema.json exists."
        )

    with open(SCHEMA_PATH) as f:
        return json.load(f)


def _format_validation_error(error: "jsonschema.ValidationError") -> str:
    """Format a jsonschema ValidationError into a human-readable message.

    Args:
        error: ValidationError instance from jsonschema.

    Returns:
        Formatted error message string.
    """
    path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"

    # Special formatting for common error types
    if error.validator == "required":
        missing = error.message.split("'")[1]
        return f"Missing required field '{missing}' at {path}"

    elif error.validator == "type":
        expected = error.validator_value
        actual = type(error.instance).__name__
        return f"Type mismatch at '{path}': expected {expected}, got {actual}"

    elif error.validator == "pattern":
        pattern = error.validator_value
        value = error.instance
        return f"Pattern mismatch at '{path}': '{value}' does not match pattern '{pattern}'"

    elif error.validator == "additionalProperties":
        # Extract the additional property name from the error
        if error.absolute_path:
            extra_props = [k for k in error.instance.keys()
                          if k not in error.schema.get("properties", {})]
            if extra_props:
                return f"Additional property not allowed at '{path}': {extra_props[0]}"
        return f"Additional properties not allowed at '{path}'"

    elif error.validator == "format":
        fmt = error.validator_value
        value = error.instance
        return f"Format error at '{path}': '{value}' is not a valid {fmt}"

    elif error.validator == "minimum" or error.validator == "maximum":
        limit = error.validator_value
        value = error.instance
        return f"Value constraint at '{path}': {value} violates {error.validator} {limit}"

    elif error.validator == "minLength" or error.validator == "maxLength":
        limit = error.validator_value
        actual = len(error.instance)
        return f"Length constraint at '{path}': length {actual} violates {error.validator} {limit}"

    # Default fallback
    return f"Validation error at '{path}': {error.message}"


def validate_manifest(
    manifest: Dict[str, Any],
    strict: bool = True,
) -> Tuple[bool, List[str]]:
    """Validate a data_manifest dictionary against the JSON schema.

    Args:
        manifest: Manifest dictionary to validate.
        strict: If True, raise ValidationError on failure. If False, return errors list.

    Returns:
        Tuple of (is_valid: bool, errors: List[str]).

    Raises:
        ValidationError: If strict=True and validation fails.
        JsonSchemaNotInstalledError: If jsonschema package is not installed.
        SchemaNotFoundError: If schema file is missing.
    """
    if not _JSONSCHEMA_AVAILABLE:
        raise JsonSchemaNotInstalledError()

    schema = _load_schema()
    validator = Draft202012Validator(schema)

    # Collect all validation errors
    errors = []
    for error in validator.iter_errors(manifest):
        errors.append(_format_validation_error(error))

    if errors:
        if strict:
            raise ValidationError(
                f"Manifest validation failed with {len(errors)} error(s)",
                errors=errors,
            )
        return False, errors

    return True, []


def validate_manifest_file(
    manifest_path: str,
    strict: bool = False,
) -> Tuple[bool, List[str]]:
    """Validate a data_manifest.json file.

    Args:
        manifest_path: Path to the manifest file.
        strict: If True, raise ValidationError on failure. If False, return errors list.

    Returns:
        Tuple of (is_valid: bool, errors: List[str]).

    Raises:
        ValidationError: If strict=True and validation fails.
        FileNotFoundError: If manifest file does not exist.
        json.JSONDecodeError: If manifest file is not valid JSON.
    """
    path = Path(manifest_path)
    if not path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

    with open(path) as f:
        try:
            manifest = json.load(f)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in manifest file: {e}"
            if strict:
                raise ValidationError(
                    error_msg,
                    errors=[str(e)],
                    manifest_path=str(manifest_path),
                )
            return False, [error_msg]

    try:
        is_valid, errors = validate_manifest(manifest, strict=False)
    except (JsonSchemaNotInstalledError, SchemaNotFoundError) as e:
        if strict:
            raise ValidationError(
                str(e),
                manifest_path=str(manifest_path),
            )
        return False, [str(e)]

    if not is_valid and strict:
        raise ValidationError(
            f"Manifest validation failed with {len(errors)} error(s)",
            errors=errors,
            manifest_path=str(manifest_path),
        )

    return is_valid, errors


def get_schema_version(manifest: Dict[str, Any]) -> Optional[str]:
    """Extract schema version from a manifest.

    Args:
        manifest: Manifest dictionary.

    Returns:
        Schema version string (e.g., '1.0.0'), or None if not present.
    """
    return manifest.get("schema_version")


def check_schema_version_compatibility(manifest: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if manifest schema version is compatible with current version.

    Args:
        manifest: Manifest dictionary.

    Returns:
        Tuple of (is_compatible: bool, message: str).
    """
    version = get_schema_version(manifest)

    if version is None:
        return False, (
            "Manifest is missing 'schema_version' field. "
            "This may be a legacy manifest that needs migration."
        )

    if version == CURRENT_SCHEMA_VERSION:
        return True, f"Schema version {version} matches current version"

    # Parse version components
    try:
        manifest_parts = [int(x) for x in version.split(".")]
        current_parts = [int(x) for x in CURRENT_SCHEMA_VERSION.split(".")]
    except (ValueError, AttributeError):
        return False, f"Invalid schema version format: {version}"

    # Check for major version mismatch (breaking changes)
    if manifest_parts[0] != current_parts[0]:
        return False, (
            f"Major version mismatch: manifest uses {version}, "
            f"current is {CURRENT_SCHEMA_VERSION}. Migration required."
        )

    # Check for minor version (backward compatible)
    if manifest_parts[1] < current_parts[1]:
        return True, (
            f"Minor version mismatch: manifest uses {version}, "
            f"current is {CURRENT_SCHEMA_VERSION}. Upgrade recommended but not required."
        )

    # Future version
    if manifest_parts[1] > current_parts[1]:
        return False, (
            f"Manifest schema version {version} is newer than current {CURRENT_SCHEMA_VERSION}. "
            "Please upgrade the FDA tools package."
        )

    return True, f"Schema version {version} is compatible"


def add_schema_version(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Add schema_version field to a legacy manifest.

    Args:
        manifest: Manifest dictionary (may be modified in-place).

    Returns:
        Updated manifest dictionary with schema_version field.
    """
    if "schema_version" not in manifest:
        manifest["schema_version"] = CURRENT_SCHEMA_VERSION
    return manifest


def create_minimal_manifest(project_name: str) -> Dict[str, Any]:
    """Create a minimal valid manifest for a new project.

    Args:
        project_name: Name of the project.

    Returns:
        Minimal manifest dictionary that passes validation.
    """
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "project": project_name,
        "created_at": now,
        "last_updated": now,
        "product_codes": [],
        "queries": {},
    }


def validate_and_repair(
    manifest: Dict[str, Any],
    add_defaults: bool = True,
) -> Tuple[Dict[str, Any], List[str]]:
    """Validate a manifest and attempt to repair common issues.

    Args:
        manifest: Manifest dictionary to validate and repair.
        add_defaults: If True, add missing optional fields with default values.

    Returns:
        Tuple of (repaired_manifest: dict, repair_log: List[str]).

    Note:
        This function does NOT raise ValidationError. It returns the repaired
        manifest and a log of repairs made. Caller should validate the result
        if strict validation is required.
    """
    repairs = []
    repaired = manifest.copy()

    # Add schema version if missing
    if "schema_version" not in repaired:
        repaired["schema_version"] = CURRENT_SCHEMA_VERSION
        repairs.append("Added missing schema_version field")

    # Add timestamps if missing
    now = datetime.now(timezone.utc).isoformat()
    if add_defaults:
        if "created_at" not in repaired:
            repaired["created_at"] = now
            repairs.append("Added missing created_at timestamp")

        if "last_updated" not in repaired:
            repaired["last_updated"] = now
            repairs.append("Added missing last_updated timestamp")

        if "product_codes" not in repaired:
            repaired["product_codes"] = []
            repairs.append("Added missing product_codes array")

        if "queries" not in repaired:
            repaired["queries"] = {}
            repairs.append("Added missing queries object")

    # Remove additional properties not in schema
    allowed_top_level = {
        "schema_version", "project", "created_at", "last_updated",
        "product_codes", "queries", "fingerprints", "total_pmas",
        "total_sseds_downloaded", "total_sections_extracted",
        "pma_entries", "search_cache",
    }
    extra_keys = set(repaired.keys()) - allowed_top_level
    for key in extra_keys:
        del repaired[key]
        repairs.append(f"Removed additional property: {key}")

    return repaired, repairs


# CLI interface for standalone validation
def main():
    """CLI interface for manifest validation."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Validate FDA data manifest files against JSON schema"
    )
    parser.add_argument(
        "manifest_path",
        help="Path to data_manifest.json file to validate",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Attempt to repair common validation issues",
    )
    parser.add_argument(
        "--output",
        help="Write repaired manifest to this path (requires --repair)",
    )
    parser.add_argument(
        "--check-version",
        action="store_true",
        dest="check_version",
        help="Check schema version compatibility only",
    )

    args = parser.parse_args()

    # Load manifest
    try:
        with open(args.manifest_path) as f:
            manifest = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.manifest_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Check version only
    if args.check_version:
        is_compatible, message = check_schema_version_compatibility(manifest)
        print(message)
        sys.exit(0 if is_compatible else 1)

    # Repair mode
    if args.repair:
        repaired, repairs = validate_and_repair(manifest)

        if repairs:
            print(f"Applied {len(repairs)} repair(s):")
            for repair in repairs:
                print(f"  - {repair}")
        else:
            print("No repairs needed")

        # Validate repaired manifest
        is_valid, errors = validate_manifest(repaired, strict=False)
        if is_valid:
            print("Repaired manifest is valid")

            # Write output if requested
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(repaired, f, indent=2)
                print(f"Wrote repaired manifest to {args.output}")
            else:
                print("\nRepaired manifest (not saved):")
                print(json.dumps(repaired, indent=2))

            sys.exit(0)
        else:
            print(f"\nValidation failed with {len(errors)} error(s) after repair:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)

    # Standard validation
    is_valid, errors = validate_manifest_file(args.manifest_path, strict=False)

    if is_valid:
        print(f"✓ Manifest is valid: {args.manifest_path}")
        version = get_schema_version(manifest)
        if version:
            print(f"  Schema version: {version}")
        sys.exit(0)
    else:
        print(f"✗ Manifest validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
