#!/usr/bin/env python3
"""
Tests for MCP Server Integrity Verification (FDA-113)

Tests SRI hash verification, hash pinning, fallback mechanisms,
and security audit logging for MCP server endpoints.
"""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from fda_tools.lib.mcp_integrity import (
    MCPIntegrityVerifier,
    MCPIntegrityError,
)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory with test .mcp.json."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create test .mcp.json
    mcp_config = {
        "mcpServers": {
            "pubmed": {
                "type": "http",
                "url": "https://pubmed.mcp.claude.com/mcp"
            },
            "c-trials": {
                "type": "http",
                "url": "https://mcp.deepsense.ai/clinical_trials/mcp"
            }
        }
    }
    with open(config_dir / ".mcp.json", 'w') as f:
        json.dump(mcp_config, f)

    return config_dir


@pytest.fixture
def verifier(temp_config_dir):
    """Create MCPIntegrityVerifier instance with temp config."""
    return MCPIntegrityVerifier(config_dir=temp_config_dir)


class TestMCPIntegrityVerifier:
    """Test suite for MCP integrity verification."""

    def test_init_creates_verifier(self, temp_config_dir):
        """Test verifier initialization."""
        verifier = MCPIntegrityVerifier(config_dir=temp_config_dir)
        assert verifier.config_dir == temp_config_dir
        assert verifier.mcp_config_path == temp_config_dir / ".mcp.json"
        assert verifier.integrity_path == temp_config_dir / ".mcp.integrity.json"

    def test_load_mcp_config(self, verifier):
        """Test loading MCP configuration."""
        config = verifier._load_mcp_config()
        assert "mcpServers" in config
        assert "pubmed" in config["mcpServers"]
        assert "c-trials" in config["mcpServers"]

    def test_load_integrity_data_creates_empty(self, verifier):
        """Test loading integrity data creates empty structure if missing."""
        data = verifier._load_integrity_data()
        assert "servers" in data
        assert "fallbacks" in data
        assert data["servers"] == {}
        assert data["fallbacks"] == {}

    def test_compute_hash(self, verifier):
        """Test SRI hash computation."""
        content = b"test content"
        hash_value = verifier._compute_hash(content)

        # Should start with sha384-
        assert hash_value.startswith("sha384-")

        # Should be deterministic
        hash_value2 = verifier._compute_hash(content)
        assert hash_value == hash_value2

        # Different content should produce different hash
        different_hash = verifier._compute_hash(b"different content")
        assert hash_value != different_hash

    @patch('urllib.request.urlopen')
    def test_fetch_server_response_success(self, mock_urlopen, verifier):
        """Test successful server response fetch."""
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = b"test response"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        content = verifier._fetch_server_response("https://example.com/mcp")
        assert content == b"test response"

    @patch('urllib.request.urlopen')
    def test_fetch_server_response_failure(self, mock_urlopen, verifier):
        """Test server response fetch failure."""
        mock_urlopen.side_effect = Exception("Network error")

        with pytest.raises(MCPIntegrityError, match="Unexpected error fetching"):
            verifier._fetch_server_response("https://example.com/mcp")

    @patch.object(MCPIntegrityVerifier, '_fetch_server_response')
    def test_verify_server_first_time(self, mock_fetch, verifier):
        """Test first-time verification (no expected hash)."""
        mock_fetch.return_value = b"server response"

        # First verification should succeed and register hash
        result = verifier.verify_server("test-server", "https://example.com/mcp")
        assert result is True

        # Hash should be saved
        integrity_data = verifier._load_integrity_data()
        assert "test-server" in integrity_data["servers"]
        assert "hash" in integrity_data["servers"]["test-server"]
        assert integrity_data["servers"]["test-server"]["hash"].startswith("sha384-")

    @patch.object(MCPIntegrityVerifier, '_fetch_server_response')
    def test_verify_server_hash_match(self, mock_fetch, verifier):
        """Test verification with matching hash."""
        test_content = b"server response"
        mock_fetch.return_value = test_content

        # Register initial hash
        expected_hash = verifier._compute_hash(test_content)
        verifier.update_hash("test-server", "https://example.com/mcp", expected_hash)

        # Verification should pass
        result = verifier.verify_server("test-server", "https://example.com/mcp")
        assert result is True

    @patch.object(MCPIntegrityVerifier, '_fetch_server_response')
    def test_verify_server_hash_mismatch(self, mock_fetch, verifier):
        """Test verification with hash mismatch (security event)."""
        # Register hash for one content
        original_content = b"original response"
        expected_hash = verifier._compute_hash(original_content)
        verifier.update_hash("test-server", "https://example.com/mcp", expected_hash)

        # Server now returns different content
        mock_fetch.return_value = b"CHANGED response"

        # Should raise integrity error
        with pytest.raises(MCPIntegrityError, match="Integrity verification failed"):
            verifier.verify_server("test-server", "https://example.com/mcp")

    @patch.object(MCPIntegrityVerifier, '_fetch_server_response')
    def test_verify_server_update_on_mismatch(self, mock_fetch, verifier):
        """Test automatic hash update on mismatch."""
        # Register hash for one content
        original_content = b"original response"
        expected_hash = verifier._compute_hash(original_content)
        verifier.update_hash("test-server", "https://example.com/mcp", expected_hash)

        # Server returns different content
        new_content = b"updated response"
        mock_fetch.return_value = new_content

        # Should update hash instead of failing
        result = verifier.verify_server(
            "test-server",
            "https://example.com/mcp",
            update_on_mismatch=True
        )
        assert result is True

        # Hash should be updated
        integrity_data = verifier._load_integrity_data()
        new_hash = verifier._compute_hash(new_content)
        assert integrity_data["servers"]["test-server"]["hash"] == new_hash

    @patch.object(MCPIntegrityVerifier, '_fetch_server_response')
    def test_update_hash(self, mock_fetch, verifier):
        """Test manual hash update."""
        mock_fetch.return_value = b"test content"

        new_hash = verifier.update_hash("test-server", "https://example.com/mcp")

        # Should save hash with metadata
        integrity_data = verifier._load_integrity_data()
        server_data = integrity_data["servers"]["test-server"]

        assert server_data["hash"] == new_hash
        assert server_data["url"] == "https://example.com/mcp"
        assert server_data["pinned"] is True
        assert "verified_at" in server_data

    @patch.object(MCPIntegrityVerifier, 'verify_server')
    def test_verify_all_servers(self, mock_verify, verifier):
        """Test verification of all configured servers."""
        mock_verify.return_value = True

        results = verifier.verify_all_servers()

        # Should verify both configured servers
        assert len(results) == 2
        assert "pubmed" in results
        assert "c-trials" in results
        assert results["pubmed"] is True
        assert results["c-trials"] is True

        # Should have called verify_server for each
        assert mock_verify.call_count == 2

    @patch.object(MCPIntegrityVerifier, 'verify_server')
    def test_verify_all_servers_with_failures(self, mock_verify, verifier):
        """Test verification when some servers fail."""
        # pubmed passes, c-trials fails
        mock_verify.side_effect = [True, MCPIntegrityError("Hash mismatch")]

        results = verifier.verify_all_servers()

        assert results["pubmed"] is True
        assert results["c-trials"] is False

    def test_add_fallback(self, verifier):
        """Test adding fallback URL."""
        verifier.add_fallback("pubmed", "https://backup.pubmed.com/mcp")

        integrity_data = verifier._load_integrity_data()
        assert "pubmed" in integrity_data["fallbacks"]
        assert "https://backup.pubmed.com/mcp" in integrity_data["fallbacks"]["pubmed"]

    def test_add_fallback_duplicate(self, verifier):
        """Test adding duplicate fallback URL."""
        verifier.add_fallback("pubmed", "https://backup.pubmed.com/mcp")
        verifier.add_fallback("pubmed", "https://backup.pubmed.com/mcp")

        integrity_data = verifier._load_integrity_data()
        fallbacks = integrity_data["fallbacks"]["pubmed"]

        # Should only appear once
        assert fallbacks.count("https://backup.pubmed.com/mcp") == 1

    def test_get_fallbacks(self, verifier):
        """Test retrieving fallback URLs."""
        verifier.add_fallback("pubmed", "https://backup1.pubmed.com/mcp")
        verifier.add_fallback("pubmed", "https://backup2.pubmed.com/mcp")

        fallbacks = verifier.get_fallbacks("pubmed")
        assert len(fallbacks) == 2
        assert "https://backup1.pubmed.com/mcp" in fallbacks
        assert "https://backup2.pubmed.com/mcp" in fallbacks

    def test_get_fallbacks_none(self, verifier):
        """Test retrieving fallbacks when none exist."""
        fallbacks = verifier.get_fallbacks("nonexistent-server")
        assert fallbacks == []

    @patch.object(MCPIntegrityVerifier, '_fetch_server_response')
    def test_get_verification_status(self, mock_fetch, verifier):
        """Test comprehensive verification status."""
        mock_fetch.return_value = b"test content"

        # Verify one server
        verifier.update_hash("pubmed", "https://pubmed.mcp.claude.com/mcp")

        # Add fallback
        verifier.add_fallback("pubmed", "https://backup.pubmed.com/mcp")

        status = verifier.get_verification_status()

        # Check overall counts
        assert status["total_servers"] == 2
        assert status["verified_servers"] == 1  # only pubmed verified
        assert status["unverified_servers"] == 1  # c-trials not verified

        # Check server details
        assert "pubmed" in status["servers"]
        pubmed_status = status["servers"]["pubmed"]
        assert pubmed_status["has_integrity_hash"] is True
        assert pubmed_status["pinned"] is True
        assert len(pubmed_status["fallbacks"]) == 1

        assert "c-trials" in status["servers"]
        trials_status = status["servers"]["c-trials"]
        assert trials_status["has_integrity_hash"] is False

    @patch.object(MCPIntegrityVerifier, '_fetch_server_response')
    def test_persistence_across_instances(self, mock_fetch, temp_config_dir):
        """Test integrity data persists across verifier instances."""
        mock_fetch.return_value = b"test content"

        # Create first verifier and update hash
        verifier1 = MCPIntegrityVerifier(config_dir=temp_config_dir)
        hash1 = verifier1.update_hash("test-server", "https://example.com/mcp")

        # Create second verifier and load data
        verifier2 = MCPIntegrityVerifier(config_dir=temp_config_dir)
        integrity_data = verifier2._load_integrity_data()

        # Should have persisted hash
        assert "test-server" in integrity_data["servers"]
        assert integrity_data["servers"]["test-server"]["hash"] == hash1

    @patch.object(MCPIntegrityVerifier, '_fetch_server_response')
    def test_concurrent_hash_updates(self, mock_fetch, verifier):
        """Test multiple hash updates."""
        mock_fetch.return_value = b"content"

        # Update multiple servers
        hash1 = verifier.update_hash("server1", "https://server1.com/mcp")
        hash2 = verifier.update_hash("server2", "https://server2.com/mcp")

        integrity_data = verifier._load_integrity_data()

        # Both should be saved
        assert "server1" in integrity_data["servers"]
        assert "server2" in integrity_data["servers"]
        assert integrity_data["servers"]["server1"]["hash"] == hash1
        assert integrity_data["servers"]["server2"]["hash"] == hash2

    def test_integrity_file_format(self, verifier):
        """Test integrity file has correct JSON structure."""
        verifier.add_fallback("pubmed", "https://backup.pubmed.com/mcp")

        # Read file directly
        with open(verifier.integrity_path, 'r') as f:
            data = json.load(f)

        # Verify structure
        assert "servers" in data
        assert "fallbacks" in data
        assert isinstance(data["servers"], dict)
        assert isinstance(data["fallbacks"], dict)

    @patch.object(MCPIntegrityVerifier, '_fetch_server_response')
    def test_hash_algorithm_consistency(self, mock_fetch, verifier):
        """Test hash algorithm is SHA-384."""
        mock_fetch.return_value = b"test"

        hash_value = verifier.update_hash("test", "https://example.com/mcp")

        # Should use sha384
        assert hash_value.startswith("sha384-")
        assert verifier.HASH_ALGORITHM == "sha384"
