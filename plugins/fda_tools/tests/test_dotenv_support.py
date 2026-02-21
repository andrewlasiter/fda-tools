"""Tests for .env file loading and credential validation (FDA-148).

Coverage:
- _load_dotenv() loads .env from standard search paths
- _load_dotenv() does not override already-set env vars
- _load_dotenv() silently skips when no .env file exists
- validate_credentials() raises ValueError for missing required keys
- validate_credentials() logs warning for missing optional keys
- validate_credentials() returns correct presence mapping
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from fda_tools.lib.secure_config import validate_credentials


class TestLoadDotenv:
    """Tests for _load_dotenv() .env file loading."""

    def test_loads_env_from_file(self, tmp_path):
        """Values from .env file appear as env vars."""
        from fda_tools.lib.secure_config import _load_dotenv

        env_file = tmp_path / ".env"
        env_file.write_text("FDA_TEST_DOTENV_LOAD=hello_from_dotenv\n")

        # Ensure var not set before test
        os.environ.pop("FDA_TEST_DOTENV_LOAD", None)

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            _load_dotenv()

        assert os.environ.get("FDA_TEST_DOTENV_LOAD") == "hello_from_dotenv"
        os.environ.pop("FDA_TEST_DOTENV_LOAD", None)

    def test_does_not_override_existing_env_vars(self, tmp_path):
        """Pre-set env vars are NOT overridden by .env file (override=False)."""
        from fda_tools.lib.secure_config import _load_dotenv

        env_file = tmp_path / ".env"
        env_file.write_text("FDA_TEST_OVERRIDE_VAR=from_dotenv\n")
        os.environ["FDA_TEST_OVERRIDE_VAR"] = "already_set"

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            _load_dotenv()

        assert os.environ["FDA_TEST_OVERRIDE_VAR"] == "already_set"
        os.environ.pop("FDA_TEST_OVERRIDE_VAR", None)

    def test_silently_skips_when_no_dotenv_file(self, tmp_path):
        """No error raised when no .env file exists in any search dir."""
        from fda_tools.lib.secure_config import _load_dotenv

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        # Patch cwd and home to dirs without .env
        with patch("pathlib.Path.cwd", return_value=empty_dir), patch(
            "pathlib.Path.home", return_value=empty_dir
        ):
            _load_dotenv()  # Must not raise


class TestValidateCredentials:
    """Tests for validate_credentials() startup validation."""

    def test_raises_for_missing_required_credential(self):
        """ValueError raised if required credential is not set."""
        with patch(
            "fda_tools.lib.secure_config.get_default_config"
        ) as mock_config:
            mock_config.return_value.get_api_key.return_value = None
            with pytest.raises(ValueError, match="Required credential"):
                validate_credentials(required=["bridge"])

    def test_no_error_when_required_credential_present(self):
        """No error when required credential is available."""
        with patch(
            "fda_tools.lib.secure_config.get_default_config"
        ) as mock_config:
            mock_config.return_value.get_api_key.return_value = "test-key-value"
            result = validate_credentials(required=["bridge"])
            assert result["bridge"] is True

    def test_returns_false_for_missing_optional_credential(self):
        """Missing optional credentials return False in the mapping."""
        with patch(
            "fda_tools.lib.secure_config.get_default_config"
        ) as mock_config:
            mock_config.return_value.get_api_key.return_value = None
            result = validate_credentials(optional=["openfda"])
            assert result["openfda"] is False

    def test_returns_true_for_present_optional_credential(self):
        """Present optional credentials return True in the mapping."""
        with patch(
            "fda_tools.lib.secure_config.get_default_config"
        ) as mock_config:
            mock_config.return_value.get_api_key.return_value = "some-key"
            result = validate_credentials(optional=["gemini"])
            assert result["gemini"] is True

    def test_empty_call_returns_empty_dict(self):
        """validate_credentials() with no args returns empty dict."""
        result = validate_credentials()
        assert result == {}

    def test_mixed_required_and_optional(self):
        """Both required and optional keys handled correctly."""
        def side_effect(key_type):
            return "key-value" if key_type == "bridge" else None

        with patch(
            "fda_tools.lib.secure_config.get_default_config"
        ) as mock_config:
            mock_config.return_value.get_api_key.side_effect = side_effect
            result = validate_credentials(required=["bridge"], optional=["openfda"])
            assert result["bridge"] is True
            assert result["openfda"] is False

    def test_error_message_includes_env_var_name(self):
        """ValueError message includes the env var to set."""
        with patch(
            "fda_tools.lib.secure_config.get_default_config"
        ) as mock_config:
            mock_config.return_value.get_api_key.return_value = None
            with pytest.raises(ValueError, match="BRIDGE_API_KEY"):
                validate_credentials(required=["bridge"])

    def test_multiple_missing_required_listed_in_error(self):
        """All missing required credentials listed in ValueError."""
        with patch(
            "fda_tools.lib.secure_config.get_default_config"
        ) as mock_config:
            mock_config.return_value.get_api_key.return_value = None
            with pytest.raises(ValueError) as exc_info:
                validate_credentials(required=["bridge", "openfda"])
            assert "bridge" in str(exc_info.value)
            assert "openfda" in str(exc_info.value)
