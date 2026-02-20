"""
Security tests for alert_sender.py - SSRF Prevention (FDA-99)

Tests CWE-918 Server-Side Request Forgery vulnerability fixes:
- URL scheme validation (HTTPS only)
- Private IP range blocking (10.x, 172.16-31.x, 192.168.x, 169.254.x)
- Localhost/loopback blocking
- Cloud metadata endpoint blocking (AWS, GCP, Azure)
- DNS resolution verification (prevents DNS rebinding)

Compliance: OWASP Top 10 A10:2021, CWE-918, NIST 800-53 SC-7
"""

import os
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import from package

from alert_sender import _validate_webhook_url, _is_private_ip, send_webhook


# ============================================================================
# CRITICAL: Private IP Detection Tests
# ============================================================================

class TestPrivateIPDetection:
    """Test _is_private_ip() function for comprehensive IP range coverage."""

    def test_private_ip_10_network(self):
        """Verify 10.x.x.x range is detected as private."""
        assert _is_private_ip("10.0.0.1") is True
        assert _is_private_ip("10.255.255.255") is True

    def test_private_ip_172_network(self):
        """Verify 172.16.x.x - 172.31.x.x range is detected as private."""
        assert _is_private_ip("172.16.0.1") is True
        assert _is_private_ip("172.31.255.255") is True

    def test_private_ip_192_network(self):
        """Verify 192.168.x.x range is detected as private."""
        assert _is_private_ip("192.168.0.1") is True
        assert _is_private_ip("192.168.255.255") is True

    def test_loopback_ipv4(self):
        """Verify 127.x.x.x loopback range is detected."""
        assert _is_private_ip("127.0.0.1") is True
        assert _is_private_ip("127.255.255.255") is True

    def test_link_local_169(self):
        """Verify 169.254.x.x link-local range is detected (AWS metadata)."""
        assert _is_private_ip("169.254.169.254") is True  # AWS/GCP/Azure metadata

    def test_loopback_ipv6(self):
        """Verify IPv6 loopback is detected."""
        assert _is_private_ip("::1") is True

    def test_ipv6_link_local(self):
        """Verify IPv6 link-local is detected."""
        assert _is_private_ip("fe80::1") is True

    def test_public_ip_allowed(self):
        """Verify legitimate public IPs are not flagged as private."""
        assert _is_private_ip("8.8.8.8") is False          # Google DNS
        assert _is_private_ip("1.1.1.1") is False          # Cloudflare DNS
        assert _is_private_ip("93.184.216.34") is False    # example.com

    def test_invalid_ip_rejected(self):
        """Verify invalid IP strings are rejected (safety measure)."""
        assert _is_private_ip("not-an-ip") is True
        assert _is_private_ip("999.999.999.999") is True


# ============================================================================
# CRITICAL: URL Validation Tests
# ============================================================================

class TestURLValidation:
    """Test _validate_webhook_url() for SSRF attack prevention."""

    def test_https_required(self):
        """Verify only HTTPS scheme is allowed (HTTP rejected)."""
        with pytest.raises(ValueError, match="Only HTTPS webhooks allowed"):
            _validate_webhook_url("http://example.com/webhook")

    def test_ftp_scheme_rejected(self):
        """Verify non-HTTP schemes are rejected."""
        with pytest.raises(ValueError, match="Only HTTPS webhooks allowed"):
            _validate_webhook_url("ftp://example.com/file")

    def test_file_scheme_rejected(self):
        """Verify file:// scheme is rejected."""
        with pytest.raises(ValueError, match="Only HTTPS webhooks allowed"):
            _validate_webhook_url("file:///etc/passwd")

    def test_empty_url_rejected(self):
        """Verify empty URL is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_webhook_url("")

    def test_localhost_hostname_blocked(self):
        """Verify 'localhost' hostname is blocked."""
        with pytest.raises(ValueError, match="cannot target localhost"):
            _validate_webhook_url("https://localhost/webhook")

    def test_127_loopback_blocked(self):
        """Verify 127.x.x.x loopback IPs are blocked."""
        with pytest.raises(ValueError, match="cannot target localhost"):
            _validate_webhook_url("https://127.0.0.1/webhook")

    def test_aws_metadata_ip_blocked(self):
        """Verify AWS metadata endpoint IP is blocked."""
        with pytest.raises(ValueError, match="resolves to private IP|cloud metadata"):
            _validate_webhook_url("https://169.254.169.254/latest/meta-data/")

    def test_aws_metadata_domain_blocked(self):
        """Verify AWS metadata endpoint domain patterns are blocked."""
        # Note: IP address URLs are caught by DNS resolution check or cloud metadata check
        with pytest.raises(ValueError, match="cloud metadata|private IP"):
            _validate_webhook_url("https://169.254.169.254/api/")

    @patch('socket.getaddrinfo')
    def test_private_ip_10_dns_blocked(self, mock_getaddrinfo):
        """Verify DNS resolution to 10.x.x.x is blocked."""
        # Mock DNS resolution to private IP
        mock_getaddrinfo.return_value = [
            (2, 1, 6, '', ('10.0.0.5', 443))  # Resolves to private 10.x network
        ]

        with pytest.raises(ValueError, match="resolves to private IP"):
            _validate_webhook_url("https://internal.company.com/webhook")

    @patch('socket.getaddrinfo')
    def test_private_ip_192_dns_blocked(self, mock_getaddrinfo):
        """Verify DNS resolution to 192.168.x.x is blocked."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, '', ('192.168.1.100', 443))
        ]

        with pytest.raises(ValueError, match="resolves to private IP"):
            _validate_webhook_url("https://router.local/api")

    @patch('socket.getaddrinfo')
    def test_valid_public_https_allowed(self, mock_getaddrinfo):
        """Verify legitimate public HTTPS webhooks are allowed."""
        # Mock DNS resolution to public IP (Cloudflare)
        mock_getaddrinfo.return_value = [
            (2, 1, 6, '', ('1.1.1.1', 443))
        ]

        result = _validate_webhook_url("https://hooks.slack.com/services/...")
        assert result == "https://hooks.slack.com/services/..."

    @patch('socket.getaddrinfo')
    def test_dns_failure_handled(self, mock_getaddrinfo):
        """Verify DNS resolution failures are handled gracefully."""
        import socket
        mock_getaddrinfo.side_effect = socket.gaierror("Name or service not known")

        with pytest.raises(ValueError, match="DNS resolution failed"):
            _validate_webhook_url("https://nonexistent.invalid.tld/webhook")


# ============================================================================
# Integration: send_webhook() Security Tests
# ============================================================================

class TestSendWebhookSecurity:
    """Test send_webhook() integration with SSRF prevention."""

    def test_ssrf_attack_blocked_in_send_webhook(self):
        """Verify send_webhook() rejects SSRF attack URLs."""
        alerts = [{"type": "test", "severity": "info"}]
        settings = {}

        # Attempt SSRF to AWS metadata
        result = send_webhook(alerts, settings, webhook_url="https://169.254.169.254/api")

        assert result["success"] is False
        assert "Invalid webhook URL" in result["error"]
        assert ("cloud metadata" in result["error"] or "private IP" in result["error"])

    def test_localhost_blocked_in_send_webhook(self):
        """Verify send_webhook() blocks localhost URLs."""
        alerts = [{"type": "test", "severity": "info"}]
        settings = {}

        result = send_webhook(alerts, settings, webhook_url="https://localhost:8080/hook")

        assert result["success"] is False
        assert "Invalid webhook URL" in result["error"]
        assert "localhost" in result["error"]

    def test_http_scheme_blocked_in_send_webhook(self):
        """Verify send_webhook() enforces HTTPS."""
        alerts = [{"type": "test", "severity": "info"}]
        settings = {}

        result = send_webhook(alerts, settings, webhook_url="http://example.com/webhook")

        assert result["success"] is False
        assert "Invalid webhook URL" in result["error"]
        assert "HTTPS" in result["error"]

    @patch('urllib.request.urlopen')
    @patch('socket.getaddrinfo')
    def test_valid_webhook_succeeds(self, mock_getaddrinfo, mock_urlopen):
        """Verify valid public webhook URLs are allowed and processed."""
        # Mock DNS resolution to public IP
        mock_getaddrinfo.return_value = [
            (2, 1, 6, '', ('93.184.216.34', 443))  # example.com
        ]

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        alerts = [{"type": "new_clearance", "product_code": "TEST"}]
        settings = {}

        result = send_webhook(alerts, settings, webhook_url="https://example.com/webhook")

        assert result["success"] is True
        assert "HTTP 200" in result["message"]


# ============================================================================
# Attack Scenario Tests
# ============================================================================

class TestAttackScenarios:
    """Test realistic SSRF attack scenarios from issue description."""

    def test_attack_aws_metadata_credential_theft(self):
        """Test scenario: Attacker tries to steal AWS credentials via metadata."""
        # Attacker sets webhook_url in settings file
        malicious_url = "https://169.254.169.254/latest/meta-data/iam/security-credentials/"

        with pytest.raises(ValueError, match="cloud metadata|private IP"):
            _validate_webhook_url(malicious_url)

    @patch('socket.getaddrinfo')
    def test_attack_internal_redis(self, mock_getaddrinfo):
        """Test scenario: Attacker tries to interact with internal Redis."""
        # Internal Redis at 10.0.0.50
        mock_getaddrinfo.return_value = [
            (2, 1, 6, '', ('10.0.0.50', 6379))
        ]

        with pytest.raises(ValueError, match="private IP.*10\\."):
            _validate_webhook_url("https://redis.internal/command")

    @patch('socket.getaddrinfo')
    def test_attack_internal_database(self, mock_getaddrinfo):
        """Test scenario: Attacker tries to access internal database."""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, '', ('172.16.0.100', 5432))  # PostgreSQL
        ]

        with pytest.raises(ValueError, match="private IP.*172\\."):
            _validate_webhook_url("https://db.internal/query")

    def test_attack_localhost_service_scanning(self):
        """Test scenario: Attacker tries to scan localhost services."""
        # Try various localhost ports
        localhost_urls = [
            "https://localhost:8080/admin",
            "https://127.0.0.1:6379/",  # Redis
            "https://127.0.0.1:5432/",  # PostgreSQL
        ]

        for url in localhost_urls:
            with pytest.raises(ValueError, match="localhost|loopback"):
                _validate_webhook_url(url)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
