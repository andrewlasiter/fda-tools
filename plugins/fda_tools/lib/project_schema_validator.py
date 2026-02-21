"""JSON Schema validation for FDA 510(k) project data files (FDA-147).

Validates the three core project data files against their JSON Schema definitions:
- device_profile.json  — device specification extracted from 510(k) data
- review.json          — predicate device evaluation results
- standards_lookup.json — applicable consensus standards

Usage::

    from fda_tools.lib.project_schema_validator import validate_project_file, validate_project_dir

    # Validate a single file
    result = validate_project_file(Path("project/device_profile.json"))
    if not result.valid:
        for error in result.errors:
            print(error)

    # Validate all files in a project directory
    results = validate_project_dir(Path("project/"))
    for filename, result in results.items():
        if not result.valid:
            print(f"{filename}: {result.error_summary()}")

    # Validate a dict in memory
    result = validate_dict(data, "device_profile")

Schema files live in:
    plugins/fda_tools/data/schemas/<schema_type>.schema.json
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import jsonschema
    from jsonschema import Draft7Validator
    from jsonschema.exceptions import ValidationError as _JsonschemaValidationError

    _JSONSCHEMA_AVAILABLE = True
except ImportError:  # pragma: no cover
    _JSONSCHEMA_AVAILABLE = False

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Schema registry
# -------------------------------------------------------------------

_SCHEMAS_DIR = Path(__file__).parent.parent / "data" / "schemas"

#: Maps schema type name → schema filename (without directory)
SCHEMA_FILENAMES: Dict[str, str] = {
    "device_profile": "device_profile.schema.json",
    "review": "review.schema.json",
    "standards_lookup": "standards_lookup.schema.json",
}

#: Maps project file basename → schema type name
PROJECT_FILE_SCHEMAS: Dict[str, str] = {
    "device_profile.json": "device_profile",
    "review.json": "review",
    "standards_lookup.json": "standards_lookup",
}

# Cache loaded schemas so disk I/O happens only once per process
_schema_cache: Dict[str, Dict[str, Any]] = {}


# -------------------------------------------------------------------
# Public result type
# -------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Result of validating a project JSON file against its schema.

    Attributes:
        valid: True if the document passed schema validation.
        errors: List of human-readable error messages.
        schema_type: The schema type used for validation (e.g. "device_profile").
        source_path: Optional path to the file that was validated.
    """

    valid: bool
    errors: List[str] = field(default_factory=list)
    schema_type: str = ""
    source_path: Optional[Path] = None

    def error_summary(self) -> str:
        """Return a compact one-line error summary."""
        if self.valid:
            return "OK"
        count = len(self.errors)
        first = self.errors[0] if self.errors else "unknown error"
        return f"{count} error(s): {first}" + ("…" if count > 1 else "")

    def __bool__(self) -> bool:
        return self.valid


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------


def _load_schema(schema_type: str) -> Dict[str, Any]:
    """Load and cache a JSON schema by type name.

    Args:
        schema_type: One of the keys in SCHEMA_FILENAMES.

    Returns:
        Schema dict.

    Raises:
        ValueError: If schema_type is not recognised.
        FileNotFoundError: If the schema file does not exist.
    """
    if schema_type in _schema_cache:
        return _schema_cache[schema_type]

    filename = SCHEMA_FILENAMES.get(schema_type)
    if filename is None:
        raise ValueError(
            f"Unknown schema type: {schema_type!r}. "
            f"Valid types: {sorted(SCHEMA_FILENAMES)}"
        )

    schema_path = _SCHEMAS_DIR / filename
    if not schema_path.is_file():
        raise FileNotFoundError(
            f"Schema file not found: {schema_path}. "
            "Ensure data/schemas/ directory is present in the package."
        )

    with schema_path.open("r", encoding="utf-8") as fh:
        schema = json.load(fh)

    _schema_cache[schema_type] = schema
    return schema


def _format_validation_error(err: "_JsonschemaValidationError") -> str:
    """Convert a jsonschema ValidationError into a readable message.

    Args:
        err: jsonschema ValidationError instance.

    Returns:
        Human-readable error string.
    """
    path = " → ".join(str(p) for p in err.absolute_path) if err.absolute_path else "root"
    return f"[{path}] {err.message}"


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------


def validate_dict(
    data: Dict[str, Any],
    schema_type: str,
    *,
    source_path: Optional[Path] = None,
) -> ValidationResult:
    """Validate an in-memory dict against a named JSON schema (FDA-147).

    Args:
        data: Dictionary to validate.
        schema_type: Schema type key — one of "device_profile", "review",
            "standards_lookup".
        source_path: Optional file path for error reporting.

    Returns:
        ValidationResult with .valid and .errors populated.
    """
    if not _JSONSCHEMA_AVAILABLE:
        logger.warning("jsonschema not installed; skipping schema validation")
        return ValidationResult(valid=True, schema_type=schema_type, source_path=source_path)

    try:
        schema = _load_schema(schema_type)
    except (ValueError, FileNotFoundError) as exc:
        return ValidationResult(
            valid=False,
            errors=[str(exc)],
            schema_type=schema_type,
            source_path=source_path,
        )

    validator = Draft7Validator(schema)
    raw_errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))

    if not raw_errors:
        return ValidationResult(valid=True, schema_type=schema_type, source_path=source_path)

    messages = [_format_validation_error(e) for e in raw_errors]
    return ValidationResult(
        valid=False,
        errors=messages,
        schema_type=schema_type,
        source_path=source_path,
    )


def validate_project_file(path: Path) -> ValidationResult:
    """Validate a project JSON file against its schema (FDA-147).

    The schema type is inferred from the filename:
    - ``device_profile.json`` → device_profile schema
    - ``review.json`` → review schema
    - ``standards_lookup.json`` → standards_lookup schema

    Args:
        path: Path to the JSON file to validate.

    Returns:
        ValidationResult. If the file cannot be parsed as JSON, valid=False
        with a descriptive error.
    """
    path = Path(path)
    filename = path.name

    schema_type = PROJECT_FILE_SCHEMAS.get(filename)
    if schema_type is None:
        return ValidationResult(
            valid=False,
            errors=[
                f"No schema registered for {filename!r}. "
                f"Recognised files: {sorted(PROJECT_FILE_SCHEMAS)}"
            ],
            source_path=path,
        )

    if not path.is_file():
        return ValidationResult(
            valid=False,
            errors=[f"File not found: {path}"],
            schema_type=schema_type,
            source_path=path,
        )

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        return ValidationResult(
            valid=False,
            errors=[f"Invalid JSON: {exc}"],
            schema_type=schema_type,
            source_path=path,
        )
    except OSError as exc:
        return ValidationResult(
            valid=False,
            errors=[f"Cannot read file: {exc}"],
            schema_type=schema_type,
            source_path=path,
        )

    return validate_dict(data, schema_type, source_path=path)


def validate_project_dir(project_dir: Path) -> Dict[str, ValidationResult]:
    """Validate all recognised project JSON files in a directory (FDA-147).

    Args:
        project_dir: Path to the project directory.

    Returns:
        Dict mapping filename → ValidationResult for each recognised file
        found in the directory. Files that don't exist are omitted.
    """
    project_dir = Path(project_dir)
    results: Dict[str, ValidationResult] = {}

    for filename in PROJECT_FILE_SCHEMAS:
        candidate = project_dir / filename
        if candidate.is_file():
            results[filename] = validate_project_file(candidate)

    return results
