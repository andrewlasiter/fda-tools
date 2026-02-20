#!/usr/bin/env python3
"""
Secure Argparse Helpers (FDA-111)

Provides secure argument parsing with automatic output path validation.

Drop-in replacement for argparse with security enhancements:
  - Automatic path validation for --output arguments
  - Directory traversal protection
  - Sensitive directory blocking
  - Comprehensive logging

Usage:
    from fda_tools.lib.secure_argparse import create_secure_parser

    # Instead of argparse.ArgumentParser()
    parser = create_secure_parser(description="My script")

    # Add output argument with automatic validation
    parser.add_output_argument("--output", default="output.json")

    args = parser.parse_args()

    # args.output is now a validated Path object
    with open(args.output, 'w') as f:
        json.dump(data, f)

References:
  - FDA-111: Unvalidated Output Path Security Issue
  - lib/path_validator.py: Core path validation logic
"""

import argparse
import logging
from pathlib import Path
from typing import Any, Optional, Union

from fda_tools.lib.path_validator import (
    OutputPathValidator,
    PathValidationError,
)

logger = logging.getLogger(__name__)


class SecureArgumentParser(argparse.ArgumentParser):
    """
    ArgumentParser with automatic output path validation.

    Drop-in replacement for argparse.ArgumentParser that validates
    output paths to prevent arbitrary file write attacks.
    """

    def __init__(self, *args, **kwargs):
        """Initialize secure parser with path validator."""
        super().__init__(*args, **kwargs)
        self._path_validator = OutputPathValidator()
        self._output_args: list[str] = []

    def add_output_argument(
        self,
        *name_or_flags: str,
        default: Optional[str] = None,
        help: Optional[str] = None,
        required: bool = False,
        create_parent: bool = True,
        **kwargs: Any
    ) -> argparse.Action:
        """
        Add output path argument with automatic validation.

        This is a convenience method that adds an argument and registers
        it for automatic path validation during parse_args().

        Args:
            *name_or_flags: Argument name(s) (e.g., '--output', '-o')
            default: Default output path
            help: Help text for argument
            required: Whether argument is required
            create_parent: Create parent directory if missing (default: True)
            **kwargs: Additional arguments to pass to add_argument()

        Returns:
            The argparse Action object

        Example:
            parser.add_output_argument(
                '--output', '-o',
                default='./output/data.json',
                help='Output file path',
                required=False
            )
        """
        # Store for validation
        dest = kwargs.get('dest')
        if dest is None:
            # Extract dest from flag
            for flag in name_or_flags:
                if flag.startswith('--'):
                    dest = flag[2:].replace('-', '_')
                    break
                elif flag.startswith('-'):
                    dest = flag[1:]

        if dest:
            self._output_args.append(dest)

        # Store create_parent preference
        if not hasattr(self, '_output_arg_config'):
            self._output_arg_config = {}
        self._output_arg_config[dest] = {
            'create_parent': create_parent
        }

        # Add argument normally
        return self.add_argument(
            *name_or_flags,
            default=default,
            help=help,
            required=required,
            **kwargs
        )

    def parse_args(self, args=None, namespace=None):
        """
        Parse arguments with automatic output path validation.

        Overrides argparse.ArgumentParser.parse_args() to add security validation
        for all output arguments registered with add_output_argument().

        Args:
            args: Arguments to parse (defaults to sys.argv)
            namespace: Namespace object to populate

        Returns:
            Populated namespace with validated paths

        Raises:
            PathValidationError: If any output path fails validation
            SystemExit: If argument parsing fails (standard argparse behavior)
        """
        # Parse arguments normally
        parsed = super().parse_args(args, namespace)

        # Validate all output arguments
        for arg_name in self._output_args:
            value = getattr(parsed, arg_name, None)

            if value is None:
                # No value provided, skip validation
                continue

            # Get configuration
            config = getattr(self, '_output_arg_config', {}).get(arg_name, {})
            create_parent = config.get('create_parent', True)

            # Validate path
            try:
                validated = self._path_validator.validate_output_path(
                    value,
                    raise_on_error=True,
                    create_parent=create_parent
                )

                # Replace string value with validated Path
                setattr(parsed, arg_name, validated)

                logger.info(f"Validated output path for --{arg_name}: {validated}")

            except PathValidationError as e:
                logger.error(f"Invalid output path for --{arg_name}: {e}")
                self.error(f"Invalid output path for --{arg_name}: {e}")

        return parsed


def create_secure_parser(
    description: Optional[str] = None,
    **kwargs: Any
) -> SecureArgumentParser:
    """
    Create a secure argument parser with path validation.

    Drop-in replacement for argparse.ArgumentParser() with automatic
    output path security validation.

    Args:
        description: Script description
        **kwargs: Additional arguments to pass to ArgumentParser

    Returns:
        SecureArgumentParser instance

    Example:
        parser = create_secure_parser(description="My FDA script")
        parser.add_output_argument("--output", default="output.json")
        args = parser.parse_args()
    """
    return SecureArgumentParser(description=description, **kwargs)


# Migration helper: Validate existing argparse output arguments
def validate_parsed_output(
    args: argparse.Namespace,
    output_arg_names: list[str],
    create_parent: bool = True
) -> argparse.Namespace:
    """
    Validate output paths in existing parsed arguments.

    Use this for gradual migration of existing scripts to path validation.

    Args:
        args: Parsed argparse namespace
        output_arg_names: List of argument names to validate (e.g., ['output', 'export_file'])
        create_parent: Create parent directories if missing

    Returns:
        Updated namespace with validated paths

    Raises:
        PathValidationError: If any path fails validation

    Example:
        # Existing script with standard argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--output', default='output.json')
        args = parser.parse_args()

        # Add validation
        from fda_tools.lib.secure_argparse import validate_parsed_output
        args = validate_parsed_output(args, ['output'])
    """
    validator = OutputPathValidator()

    for arg_name in output_arg_names:
        value = getattr(args, arg_name, None)

        if value is None:
            continue

        # Validate
        validated = validator.validate_output_path(
            value,
            raise_on_error=True,
            create_parent=create_parent
        )

        # Replace with validated Path
        setattr(args, arg_name, validated)

    return args
