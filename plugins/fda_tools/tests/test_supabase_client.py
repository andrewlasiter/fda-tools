"""
Tests for FDA-219: SupabaseClient singleton.

Uses monkeypatching to avoid real network calls.
"""

import importlib
import os
import sys
import types
import unittest
from unittest.mock import ANY, MagicMock, patch


# ── helpers ──────────────────────────────────────────────────────────


def _reload_module():
    """Force-reload supabase_client to reset the singleton between tests."""
    mod_name = "plugins.fda_tools.lib.supabase_client"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    return importlib.import_module(mod_name)


def _make_fake_supabase():
    """Return a minimal fake supabase module."""
    fake = types.ModuleType("supabase")
    mock_client = MagicMock()
    fake.create_client = MagicMock(return_value=mock_client)
    fake.Client = type(mock_client)
    return fake, mock_client


# ── tests ─────────────────────────────────────────────────────────────


class TestSupabaseClientInit(unittest.TestCase):
    def setUp(self):
        # Ensure env vars are absent before each test
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_SECRET_KEY", None)

    def test_raises_if_url_missing(self):
        mod = _reload_module()
        mod.SupabaseClient.reset()
        with self.assertRaises(EnvironmentError) as ctx:
            mod.SupabaseClient.get_instance().client
        self.assertIn("SUPABASE_URL", str(ctx.exception))

    def test_raises_if_key_missing(self):
        os.environ["SUPABASE_URL"] = "https://fake.supabase.co"
        mod = _reload_module()
        mod.SupabaseClient.reset()
        with self.assertRaises(EnvironmentError) as ctx:
            mod.SupabaseClient.get_instance().client
        self.assertIn("SUPABASE_SECRET_KEY", str(ctx.exception))

    def test_helpful_error_message_for_url(self):
        mod = _reload_module()
        mod.SupabaseClient.reset()
        try:
            mod.SupabaseClient.get_instance().client
        except EnvironmentError as exc:
            self.assertIn("export", str(exc).lower())

    def test_init_with_valid_env_vars(self):
        os.environ["SUPABASE_URL"] = "https://fake.supabase.co"
        os.environ["SUPABASE_SECRET_KEY"] = "service-role-secret"
        mod = _reload_module()
        mod.SupabaseClient.reset()

        fake_supabase, mock_client = _make_fake_supabase()
        with patch.dict(sys.modules, {"supabase": fake_supabase}):
            instance = mod.SupabaseClient.get_instance()
            client = instance.client
            fake_supabase.create_client.assert_called_once_with(
                "https://fake.supabase.co",
                "service-role-secret",
                options=ANY,
            )
            self.assertIsNotNone(client)

    def tearDown(self):
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_SECRET_KEY", None)


class TestSupabaseClientSingleton(unittest.TestCase):
    def setUp(self):
        os.environ["SUPABASE_URL"] = "https://fake.supabase.co"
        os.environ["SUPABASE_SECRET_KEY"] = "service-role-secret"

    def tearDown(self):
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_SECRET_KEY", None)

    def test_returns_same_instance(self):
        mod = _reload_module()
        mod.SupabaseClient.reset()
        fake_supabase, _ = _make_fake_supabase()
        with patch.dict(sys.modules, {"supabase": fake_supabase}):
            a = mod.SupabaseClient.get_instance()
            b = mod.SupabaseClient.get_instance()
            self.assertIs(a, b)

    def test_reset_creates_new_instance(self):
        mod = _reload_module()
        mod.SupabaseClient.reset()
        fake_supabase, _ = _make_fake_supabase()
        with patch.dict(sys.modules, {"supabase": fake_supabase}):
            a = mod.SupabaseClient.get_instance()
            mod.SupabaseClient.reset()
            b = mod.SupabaseClient.get_instance()
            self.assertIsNot(a, b)


class TestSupabaseClientKeyNotLogged(unittest.TestCase):
    """Verify the secret key never appears in repr or log output."""

    def setUp(self):
        os.environ["SUPABASE_URL"] = "https://fake.supabase.co"
        os.environ["SUPABASE_SECRET_KEY"] = "SUPER_SECRET_DO_NOT_LOG"

    def tearDown(self):
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_SECRET_KEY", None)

    def test_repr_does_not_contain_secret(self):
        mod = _reload_module()
        mod.SupabaseClient.reset()
        fake_supabase, _ = _make_fake_supabase()
        with patch.dict(sys.modules, {"supabase": fake_supabase}):
            instance = mod.SupabaseClient.get_instance()
            _ = instance.client  # trigger init
            self.assertNotIn("SUPER_SECRET_DO_NOT_LOG", repr(instance))


class TestSupabaseClientPing(unittest.TestCase):
    def setUp(self):
        os.environ["SUPABASE_URL"] = "https://fake.supabase.co"
        os.environ["SUPABASE_SECRET_KEY"] = "service-role-secret"

    def tearDown(self):
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_SECRET_KEY", None)

    def test_ping_returns_true_on_success(self):
        mod = _reload_module()
        mod.SupabaseClient.reset()
        fake_supabase, mock_client = _make_fake_supabase()
        mock_client.rpc.return_value.execute.return_value = None

        with patch.dict(sys.modules, {"supabase": fake_supabase}):
            instance = mod.SupabaseClient.get_instance()
            _ = instance.client  # init
            result = instance.ping()
        self.assertTrue(result)

    def test_ping_returns_false_on_error(self):
        mod = _reload_module()
        mod.SupabaseClient.reset()
        fake_supabase, mock_client = _make_fake_supabase()
        mock_client.rpc.return_value.execute.side_effect = ConnectionError("network down")

        with patch.dict(sys.modules, {"supabase": fake_supabase}):
            instance = mod.SupabaseClient.get_instance()
            _ = instance.client
            result = instance.ping()
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
