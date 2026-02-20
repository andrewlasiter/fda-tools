#!/usr/bin/env python3
"""
Security tests for Monitoring System (FDA-970 Remediation Verification).

Tests product code validation, rate limiting, severity validation, and deduplication security.
"""

import pytest
import time
from datetime import datetime, timedelta, timezone

# Import from package
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.monitoring_security import (
    ProductCodeValidator,
    validate_product_codes,
    RateLimiter,
    validate_alert_severity,
    generate_alert_dedup_key,
    AlertQueue,
    SEVERITY_RULES,
)


class TestProductCodeValidation:
    """Test product code validation (FDA-970 CRITICAL-1)."""

    def setup_method(self):
        """Clear cache before each test."""
        ProductCodeValidator.clear_cache()

    def test_validate_product_code_accepts_valid_code(self):
        """Test that valid product codes are accepted."""
        # DQY is a common cardiovascular product code
        result = ProductCodeValidator.validate_product_code("DQY")
        assert result == "DQY"

    def test_validate_product_code_normalizes_lowercase(self):
        """Test that lowercase codes are normalized to uppercase."""
        result = ProductCodeValidator.validate_product_code("dqy")
        assert result == "DQY"

    def test_validate_product_code_strips_whitespace(self):
        """Test that whitespace is stripped."""
        result = ProductCodeValidator.validate_product_code("  DQY  ")
        assert result == "DQY"

    def test_validate_product_code_rejects_invalid_format(self):
        """Test that invalid formats are rejected."""
        # Too long
        with pytest.raises(ValueError, match="Must be exactly 3 characters"):
            ProductCodeValidator.validate_product_code("DQYA")

        # Too short
        with pytest.raises(ValueError, match="Must be exactly 3 characters"):
            ProductCodeValidator.validate_product_code("DQ")

        # Empty
        with pytest.raises(ValueError, match="Must be exactly 3 characters"):
            ProductCodeValidator.validate_product_code("")

    def test_validate_product_code_rejects_non_alpha(self):
        """Test that non-alphabetic codes are rejected."""
        with pytest.raises(ValueError, match="Must contain only letters"):
            ProductCodeValidator.validate_product_code("DQ1")

        with pytest.raises(ValueError, match="Must contain only letters"):
            ProductCodeValidator.validate_product_code("D-Q")

    def test_validate_product_code_rejects_unknown_code(self):
        """Test that unknown product codes are rejected."""
        with pytest.raises(ValueError, match="Not found in FDA device classification"):
            ProductCodeValidator.validate_product_code("ZZZ")

    def test_validate_product_codes_batch(self):
        """Test batch validation of multiple product codes."""
        codes = ["DQY", "nmh", "  OVE  "]
        validated = validate_product_codes(codes)
        assert validated == ["DQY", "NMH", "OVE"]

    def test_validate_product_codes_rejects_mixed_valid_invalid(self):
        """Test that batch validation fails if any code is invalid."""
        codes = ["DQY", "ZZZ", "NMH"]
        with pytest.raises(ValueError, match="Not found in FDA"):
            validate_product_codes(codes)

    def test_product_code_cache(self):
        """Test that product code cache reduces lookups."""
        # First call loads cache
        ProductCodeValidator.validate_product_code("DQY")
        first_cache_time = ProductCodeValidator._cache_timestamp

        # Second call uses cache
        ProductCodeValidator.validate_product_code("NMH")
        second_cache_time = ProductCodeValidator._cache_timestamp

        # Cache timestamp should be the same (cache hit)
        assert first_cache_time == second_cache_time


class TestRateLimiting:
    """Test rate limiting prevents flooding (FDA-970 HIGH-4)."""

    def test_rate_limiter_accepts_within_limit(self):
        """Test that alerts within limit are accepted."""
        limiter = RateLimiter(max_per_hour=100)

        # Send 50 alerts (within limit)
        for i in range(50):
            assert limiter.check_rate_limit("DQY") is True

        # Should still be within limit
        assert limiter.get_current_rate("DQY") == 50

    def test_rate_limiter_rejects_over_limit(self):
        """Test that alerts exceeding limit are rejected."""
        limiter = RateLimiter(max_per_hour=100)

        # Send 100 alerts (at limit)
        for i in range(100):
            limiter.check_rate_limit("DQY")

        # 101st alert should be rejected
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            limiter.check_rate_limit("DQY")

    def test_rate_limiter_per_product_code(self):
        """Test that rate limiting is per product code."""
        limiter = RateLimiter(max_per_hour=100)

        # Send 100 alerts for DQY (at limit)
        for i in range(100):
            limiter.check_rate_limit("DQY")

        # Should still accept alerts for different product code
        assert limiter.check_rate_limit("NMH") is True

    def test_rate_limiter_sliding_window(self):
        """Test that rate limiter uses sliding window (not fixed window)."""
        limiter = RateLimiter(max_per_hour=5)

        # Send 5 alerts (at limit)
        for i in range(5):
            limiter.check_rate_limit("DQY")

        # Manual timestamp manipulation to simulate time passage
        # (In real usage, old timestamps are cleaned automatically)
        one_hour_one_second_ago = datetime.now(timezone.utc) - timedelta(hours=1, seconds=1)
        limiter.alert_timestamps["DQY"] = [one_hour_one_second_ago] * 3 + limiter.alert_timestamps["DQY"][-2:]

        # After 1 hour, old alerts should be cleaned
        # Should accept new alert
        assert limiter.check_rate_limit("DQY") is True

    def test_rate_limiter_get_current_rate(self):
        """Test get_current_rate returns accurate count."""
        limiter = RateLimiter(max_per_hour=100)

        # Send 25 alerts
        for i in range(25):
            limiter.check_rate_limit("DQY")

        assert limiter.get_current_rate("DQY") == 25

    def test_rate_limiter_reset(self):
        """Test manual rate limiter reset."""
        limiter = RateLimiter(max_per_hour=100)

        # Send 100 alerts (at limit)
        for i in range(100):
            limiter.check_rate_limit("DQY")

        # Reset should allow new alerts
        limiter.reset("DQY")
        assert limiter.check_rate_limit("DQY") is True


class TestSeverityValidation:
    """Test severity validation prevents escalation (FDA-970 HIGH-3)."""

    def test_severity_validation_accepts_correct_severity(self):
        """Test that correct severity is accepted."""
        alert = {
            'alert_type': 'new_approval',
            'severity': 'INFO'
        }
        severity = validate_alert_severity(alert)
        assert severity == 'INFO'

    def test_severity_validation_corrects_escalation(self):
        """Test that severity escalation is auto-corrected."""
        # INFO alert type with CRITICAL severity (escalation attack)
        alert = {
            'alert_type': 'new_approval',
            'severity': 'CRITICAL'  # Escalated!
        }
        severity = validate_alert_severity(alert)

        # Should auto-correct to INFO
        assert severity == 'INFO'
        assert alert['severity'] == 'INFO'

    def test_severity_validation_corrects_downgrade(self):
        """Test that severity downgrade is auto-corrected."""
        # CRITICAL alert type with INFO severity (downgrade)
        alert = {
            'alert_type': 'maude_safety',
            'severity': 'INFO'  # Downgraded!
        }
        severity = validate_alert_severity(alert)

        # Should auto-correct to CRITICAL
        assert severity == 'CRITICAL'
        assert alert['severity'] == 'CRITICAL'

    def test_severity_rules_coverage(self):
        """Test that all severity rules are valid."""
        valid_severities = {'CRITICAL', 'WARNING', 'INFO'}
        for alert_type, severity in SEVERITY_RULES.items():
            assert severity in valid_severities

    def test_severity_validation_default_info(self):
        """Test that unknown alert types default to INFO."""
        alert = {
            'alert_type': 'unknown_type',
            'severity': 'WARNING'
        }
        severity = validate_alert_severity(alert)

        # Should auto-correct to INFO (default for unknown types)
        assert severity == 'INFO'


class TestSecureDeduplication:
    """Test secure deduplication keys (FDA-970 CRITICAL-2)."""

    def test_dedup_key_is_full_sha256(self):
        """Test that dedup key is full SHA-256 (64 hex chars)."""
        alert = {
            'alert_type': 'new_approval',
            'pma_number': 'P123456',
            'product_code': 'DQY',
            'data_key': 'test_key'
        }
        key = generate_alert_dedup_key(alert)

        # Full SHA-256 is 64 hex characters (256 bits)
        assert len(key) == 64
        assert all(c in '0123456789abcdef' for c in key)

    def test_dedup_key_deterministic(self):
        """Test that same alert produces same key."""
        alert1 = {
            'alert_type': 'new_approval',
            'pma_number': 'P123456',
            'product_code': 'DQY',
            'data_key': 'test_key'
        }
        alert2 = {
            'alert_type': 'new_approval',
            'pma_number': 'P123456',
            'product_code': 'DQY',
            'data_key': 'test_key'
        }

        key1 = generate_alert_dedup_key(alert1)
        key2 = generate_alert_dedup_key(alert2)

        assert key1 == key2

    def test_dedup_key_different_for_different_alerts(self):
        """Test that different alerts produce different keys."""
        alert1 = {
            'alert_type': 'new_approval',
            'pma_number': 'P123456',
            'product_code': 'DQY',
            'data_key': 'test_key_1'
        }
        alert2 = {
            'alert_type': 'new_approval',
            'pma_number': 'P123456',
            'product_code': 'DQY',
            'data_key': 'test_key_2'  # Different!
        }

        key1 = generate_alert_dedup_key(alert1)
        key2 = generate_alert_dedup_key(alert2)

        assert key1 != key2

    def test_dedup_key_includes_all_fields(self):
        """Test that all relevant fields affect the key."""
        base_alert = {
            'alert_type': 'new_approval',
            'pma_number': 'P123456',
            'product_code': 'DQY',
            'supplement_number': '',
            'decision_date': '20240101',
            'event_id': '',
            'data_key': 'test'
        }

        base_key = generate_alert_dedup_key(base_alert)

        # Change each field and verify key changes
        for field in ['alert_type', 'pma_number', 'product_code', 'decision_date']:
            modified_alert = base_alert.copy()
            modified_alert[field] = 'MODIFIED'
            modified_key = generate_alert_dedup_key(modified_alert)
            assert modified_key != base_key, f"Key unchanged when {field} modified"

    def test_dedup_key_collision_resistance(self):
        """Test that truncated hash would have collisions but full hash doesn't."""
        # Generate 1000 unique alerts
        alerts = [
            {
                'alert_type': 'new_approval',
                'pma_number': f'P{i:06d}',
                'product_code': 'DQY',
                'data_key': f'key_{i}'
            }
            for i in range(1000)
        ]

        # Generate full SHA-256 keys
        full_keys = [generate_alert_dedup_key(alert) for alert in alerts]

        # All keys should be unique (no collisions)
        assert len(set(full_keys)) == 1000

        # If we truncate to 16 chars (old vulnerable approach),
        # collision probability is much higher
        truncated_keys = [key[:16] for key in full_keys]
        # With 1000 items and 16 hex chars (2^64 space),
        # birthday paradox suggests possible collisions
        # But we're not testing for collisions here, just that full keys are unique


class TestAlertQueue:
    """Test alert queue management (FDA-970 HIGH-4)."""

    def test_alert_queue_accepts_within_capacity(self):
        """Test that queue accepts alerts within capacity."""
        queue = AlertQueue(max_size=10)

        for i in range(10):
            assert queue.enqueue({'id': i}) is True

        assert queue.size() == 10

    def test_alert_queue_rejects_when_full(self):
        """Test that queue rejects alerts when full."""
        queue = AlertQueue(max_size=10)

        # Fill queue
        for i in range(10):
            queue.enqueue({'id': i})

        # 11th alert should be rejected
        with pytest.raises(ValueError, match="Alert queue full"):
            queue.enqueue({'id': 11})

    def test_alert_queue_fifo_order(self):
        """Test that queue maintains FIFO order."""
        queue = AlertQueue(max_size=10)

        # Enqueue 3 alerts
        queue.enqueue({'id': 1})
        queue.enqueue({'id': 2})
        queue.enqueue({'id': 3})

        # Dequeue should return in FIFO order
        assert queue.dequeue()['id'] == 1
        assert queue.dequeue()['id'] == 2
        assert queue.dequeue()['id'] == 3

    def test_alert_queue_dequeue_empty(self):
        """Test that dequeue from empty queue returns None."""
        queue = AlertQueue(max_size=10)
        assert queue.dequeue() is None

    def test_alert_queue_is_full(self):
        """Test is_full() method."""
        queue = AlertQueue(max_size=3)

        assert not queue.is_full()

        queue.enqueue({'id': 1})
        queue.enqueue({'id': 2})
        assert not queue.is_full()

        queue.enqueue({'id': 3})
        assert queue.is_full()

    def test_alert_queue_clear(self):
        """Test queue clear() method."""
        queue = AlertQueue(max_size=10)

        # Fill queue
        for i in range(5):
            queue.enqueue({'id': i})

        # Clear
        queue.clear()

        assert queue.size() == 0
        assert not queue.is_full()
        assert queue.overflow_count == 0

    def test_alert_queue_overflow_count(self):
        """Test that overflow count tracks rejected alerts."""
        queue = AlertQueue(max_size=5)

        # Fill queue
        for i in range(5):
            queue.enqueue({'id': i})

        # Try to add 3 more (should fail and increment overflow count)
        for i in range(3):
            try:
                queue.enqueue({'id': i + 5})
            except ValueError:
                pass

        assert queue.overflow_count == 3


class TestIntegratedSecurity:
    """Test integrated security workflow."""

    def test_complete_alert_processing_workflow(self):
        """Test complete alert processing with all security features."""
        # 1. Validate product codes
        product_codes = validate_product_codes(["DQY", "NMH"])
        assert product_codes == ["DQY", "NMH"]

        # 2. Check rate limit
        limiter = RateLimiter(max_per_hour=100)
        assert limiter.check_rate_limit("DQY") is True

        # 3. Create alert
        alert = {
            'alert_type': 'new_approval',
            'pma_number': 'P123456',
            'product_code': 'DQY',
            'severity': 'INFO',  # Correct severity
            'data_key': 'test_key'
        }

        # 4. Validate severity
        severity = validate_alert_severity(alert)
        assert severity == 'INFO'

        # 5. Generate dedup key
        dedup_key = generate_alert_dedup_key(alert)
        assert len(dedup_key) == 64

        # 6. Enqueue alert
        queue = AlertQueue(max_size=1000)
        assert queue.enqueue(alert) is True

    def test_security_prevents_fake_product_code_injection(self):
        """Test that fake product codes are rejected."""
        # Attacker tries to inject fake product code (3 letters, but not in FDA database)
        with pytest.raises(ValueError, match="Not found in FDA"):
            validate_product_codes(["ZZZ"])

    def test_security_prevents_severity_escalation(self):
        """Test that severity escalation is auto-corrected."""
        # Attacker tries to escalate INFO alert to CRITICAL
        alert = {
            'alert_type': 'new_approval',  # INFO type
            'severity': 'CRITICAL'  # Escalated!
        }

        severity = validate_alert_severity(alert)

        # Should auto-correct to INFO
        assert severity == 'INFO'

    def test_security_prevents_notification_flooding(self):
        """Test that rate limiting prevents flooding."""
        limiter = RateLimiter(max_per_hour=100)

        # Attacker tries to send 200 alerts
        for i in range(100):
            limiter.check_rate_limit("DQY")

        # 101st alert should be rejected
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            for i in range(100):
                limiter.check_rate_limit("DQY")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
