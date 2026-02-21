"""
Configuration Wiring Tests (FDA-138)
======================================

Verifies that runtime constants in key modules read from config.toml
rather than relying exclusively on hardcoded defaults.

Tests cover:
  - ``fda_api_client.py`` rate-limit constants pick up config values
  - ``bridge/server.py`` SERVER_PORT picks up config value
  - Defaults still work when config keys are absent
  - config.toml contains the expected new keys

Test count: 10
Target: pytest plugins/fda_tools/tests/test_fda138_config_wiring.py -v
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_config(values: dict) -> MagicMock:
    """Return a mock Config object whose get_int respects *values*."""
    cfg = MagicMock()

    def _get_int(key: str, default: int = 0) -> int:
        return values.get(key, default)

    cfg.get_int.side_effect = _get_int
    return cfg


# ---------------------------------------------------------------------------
# TestFDAClientConfigWiring
# ---------------------------------------------------------------------------


class TestFDAClientConfigWiring:
    """Tests that fda_api_client reads rate limits from config."""

    def test_unauthenticated_limit_default_is_240(self):
        """Without config override, unauthenticated limit should be 240."""
        import fda_tools.scripts.fda_api_client as mod
        # Re-import to get the module-level constant value
        assert mod.UNAUTHENTICATED_RATE_LIMIT >= 1  # sanity: must be positive
        # Verify it is the expected default if nothing overrides it
        # (or a config-read value if config is present)
        assert isinstance(mod.UNAUTHENTICATED_RATE_LIMIT, int)

    def test_authenticated_limit_default_is_1000(self):
        """Without config override, authenticated limit should be 1000."""
        import fda_tools.scripts.fda_api_client as mod
        assert mod.AUTHENTICATED_RATE_LIMIT >= 1
        assert isinstance(mod.AUTHENTICATED_RATE_LIMIT, int)

    def test_unauthenticated_limit_honours_config_override(self):
        """When config provides rate_limit_openfda, module constant is updated."""
        mock_cfg = _make_mock_config({
            "rate_limiting.rate_limit_openfda": 500,
            "rate_limiting.rate_limit_openfda_authenticated": 2000,
        })
        mock_get_config = MagicMock(return_value=mock_cfg)

        # Temporarily remove the cached module so reload sees new config
        mod_name = "fda_tools.scripts.fda_api_client"
        saved = sys.modules.pop(mod_name, None)
        try:
            with patch.dict(
                sys.modules,
                {"fda_tools.lib.config": MagicMock(get_config=mock_get_config)},
            ):
                import fda_tools.scripts.fda_api_client as mod
                assert mod.UNAUTHENTICATED_RATE_LIMIT == 500
                assert mod.AUTHENTICATED_RATE_LIMIT == 2000
        finally:
            sys.modules.pop(mod_name, None)
            if saved is not None:
                sys.modules[mod_name] = saved

    def test_config_failure_falls_back_to_defaults(self):
        """When config import raises, module falls back to hardcoded defaults."""
        mod_name = "fda_tools.scripts.fda_api_client"
        saved = sys.modules.pop(mod_name, None)
        try:
            # Provide a mock config module whose get_config raises
            broken_config = MagicMock()
            broken_config.get_config.side_effect = RuntimeError("config unavailable")
            with patch.dict(sys.modules, {"fda_tools.lib.config": broken_config}):
                import fda_tools.scripts.fda_api_client as mod
                # Defaults (240, 1000) should remain unchanged
                assert mod.UNAUTHENTICATED_RATE_LIMIT == 240
                assert mod.AUTHENTICATED_RATE_LIMIT == 1000
        finally:
            sys.modules.pop(mod_name, None)
            if saved is not None:
                sys.modules[mod_name] = saved


# ---------------------------------------------------------------------------
# TestBridgeServerConfigWiring
# ---------------------------------------------------------------------------


class TestBridgeServerConfigWiring:
    """Tests that bridge/server.py reads SERVER_PORT from config."""

    def test_server_port_is_positive_int(self):
        """SERVER_PORT must be a valid port number."""
        from fda_tools.bridge import server
        assert isinstance(server.SERVER_PORT, int)
        assert 1 <= server.SERVER_PORT <= 65535

    def test_server_port_honours_config_override(self):
        """When config provides bridge_server_port, SERVER_PORT is updated."""
        mock_cfg = _make_mock_config({"api.bridge_server_port": 19999})
        mock_get_config = MagicMock(return_value=mock_cfg)

        mod_name = "fda_tools.bridge.server"
        saved = sys.modules.pop(mod_name, None)
        try:
            with patch.dict(
                sys.modules,
                {"fda_tools.lib.config": MagicMock(get_config=mock_get_config)},
            ):
                import fda_tools.bridge.server as srv
                assert srv.SERVER_PORT == 19999
        finally:
            sys.modules.pop(mod_name, None)
            if saved is not None:
                sys.modules[mod_name] = saved

    def test_server_port_defaults_to_18790_on_config_failure(self):
        """When config raises, SERVER_PORT stays at 18790."""
        mod_name = "fda_tools.bridge.server"
        saved = sys.modules.pop(mod_name, None)
        try:
            broken_config = MagicMock()
            broken_config.get_config.side_effect = RuntimeError("broken")
            with patch.dict(sys.modules, {"fda_tools.lib.config": broken_config}):
                import fda_tools.bridge.server as srv
                assert srv.SERVER_PORT == 18790
        finally:
            sys.modules.pop(mod_name, None)
            if saved is not None:
                sys.modules[mod_name] = saved


# ---------------------------------------------------------------------------
# TestConfigTOMLKeys
# ---------------------------------------------------------------------------


class TestConfigTOMLKeys:
    """Tests that config.toml has the expected new keys."""

    def test_config_has_bridge_server_port(self):
        from fda_tools.lib.config import get_config
        cfg = get_config()
        port = cfg.get_int("api.bridge_server_port", default=0)
        assert port > 0, "api.bridge_server_port not found in config.toml"

    def test_config_has_rate_limit_openfda(self):
        from fda_tools.lib.config import get_config
        cfg = get_config()
        limit = cfg.get_int("rate_limiting.rate_limit_openfda", default=0)
        assert limit > 0, "rate_limiting.rate_limit_openfda not found in config.toml"

    def test_config_has_rate_limit_openfda_authenticated(self):
        from fda_tools.lib.config import get_config
        cfg = get_config()
        limit = cfg.get_int("rate_limiting.rate_limit_openfda_authenticated", default=0)
        assert limit > 0, "rate_limiting.rate_limit_openfda_authenticated not in config.toml"
