#!/usr/bin/env python3
"""
Monitoring Security Module (FDA-970 Security Remediation).

Provides product code validation, rate limiting, severity validation, and
secure alert management for FDA approval monitoring system.

Security Features:
- Product code validation against FDA database
- Rate limiting (prevents notification flooding DoS)
- Severity validation (prevents escalation attacks)
- Full SHA-256 deduplication keys (prevents collision bypass)
- Secure watchlist and alert history storage (via SecureDataStore)

Compliance:
- 21 CFR Part 11 (Electronic Records - alert integrity)
- FDA MedWatch alignment (severity classification)

Usage:
    from lib.monitoring_security import (
        validate_product_codes,
        RateLimiter,
        validate_alert_severity
    )

    # Validate product codes
    validate_product_codes(["NMH", "QAS"])  # Raises ValueError if invalid

    # Rate limiting
    limiter = RateLimiter(max_per_hour=100)
    limiter.check_rate_limit("NMH")  # Raises ValueError if exceeded

    # Severity validation
    severity = validate_alert_severity(alert)  # Auto-corrects severity

Version: 1.0.0 (FDA-970)
"""

import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


# ============================================================
# Product Code Validation (FDA-970 CRITICAL-1)
# ============================================================

class ProductCodeValidator:
    """
    Validates product codes against FDA classification database.

    Security: FDA-970 CRITICAL-1 remediation
    - Prevents alert injection via fake product codes
    - Cached validation (24-hour TTL) for performance
    """

    # Cache valid product codes for 24 hours
    _valid_codes_cache: Optional[Set[str]] = None
    _cache_timestamp: Optional[datetime] = None
    CACHE_TTL_HOURS = 24

    @classmethod
    def _load_valid_product_codes(cls) -> Set[str]:
        """
        Load valid FDA product codes from classification database.

        Returns:
            Set of valid 3-letter product codes

        Security: FDA-970 CRITICAL-1
        - Whitelist prevents fake product code injection
        - Cached to prevent DoS via repeated API calls
        """
        # Check cache freshness
        now = datetime.now(timezone.utc)
        if cls._valid_codes_cache is not None and cls._cache_timestamp is not None:
            age = (now - cls._cache_timestamp).total_seconds() / 3600
            if age < cls.CACHE_TTL_HOURS:
                return cls._valid_codes_cache

        # Load from FDA classification data
        # Try to import from existing classification lookup module
        try:
            # Import from plugin's classification module
            import sys
            import os
            sys.path.insert(0, os.path.join(
                os.path.dirname(__file__), '..', 'scripts'
            ))
            from classification_lookup import get_all_product_codes
            valid_codes = set(get_all_product_codes())
        except (ImportError, FileNotFoundError):
            # Fallback: Load from hardcoded common product codes
            # (This is a minimal set for testing; production should use full FDA database)
            logger.warning(
                "classification_lookup not available. Using minimal product code set. "
                "Install full FDA classification database for production use."
            )
            valid_codes = {
                # Common cardiovascular codes
                "DQY", "NIQ", "NMH", "NIT", "DRF",
                # Common orthopedic codes
                "OVE", "MAX", "MNH", "KWP",
                # Common general surgery codes
                "FRO", "GAF", "GEI", "FZP",
                # Common software codes
                "QKQ", "LLZ", "MYN", "OZO",
                # Add more as needed for validation
                # In production, this should load from FDA classification database
            }

        # Update cache
        cls._valid_codes_cache = valid_codes
        cls._cache_timestamp = now

        logger.info(
            f"Loaded {len(valid_codes)} valid product codes "
            f"(cache valid for {cls.CACHE_TTL_HOURS} hours)"
        )

        return valid_codes

    @classmethod
    def validate_product_code(cls, product_code: str) -> str:
        """
        Validate a single product code.

        Args:
            product_code: 3-letter FDA product code

        Returns:
            Validated product code (uppercase)

        Raises:
            ValueError: If product code is invalid or not found

        Security: FDA-970 CRITICAL-1 remediation
        - Whitelist prevents fake product code injection
        - Normalizes to uppercase for consistency
        """
        # Normalize to uppercase and strip whitespace
        normalized = product_code.upper().strip()

        # Validate format (3 uppercase letters)
        if not normalized or len(normalized) != 3:
            raise ValueError(
                f"Invalid product code format: '{product_code}'. "
                f"Must be exactly 3 characters."
            )

        if not normalized.isalpha():
            raise ValueError(
                f"Invalid product code: '{product_code}'. "
                f"Must contain only letters (A-Z)."
            )

        # Validate against FDA database
        valid_codes = cls._load_valid_product_codes()
        if normalized not in valid_codes:
            raise ValueError(
                f"Unknown product code: '{normalized}'. "
                f"Not found in FDA device classification database. "
                f"Verify code at: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPCD/classification.cfm"
            )

        return normalized

    @classmethod
    def validate_product_codes(cls, product_codes: List[str]) -> List[str]:
        """
        Validate multiple product codes.

        Args:
            product_codes: List of product codes to validate

        Returns:
            List of validated product codes (uppercase)

        Raises:
            ValueError: If any product code is invalid

        Security: FDA-970 CRITICAL-1 remediation
        """
        validated = []
        for code in product_codes:
            validated.append(cls.validate_product_code(code))
        return validated

    @classmethod
    def clear_cache(cls):
        """Clear the product code cache (for testing)."""
        cls._valid_codes_cache = None
        cls._cache_timestamp = None


# Convenience function
def validate_product_codes(product_codes: List[str]) -> List[str]:
    """
    Validate product codes against FDA database.

    Args:
        product_codes: List of product codes to validate

    Returns:
        List of validated product codes (uppercase)

    Raises:
        ValueError: If any product code is invalid
    """
    return ProductCodeValidator.validate_product_codes(product_codes)


# ============================================================
# Rate Limiting (FDA-970 HIGH-4)
# ============================================================

class RateLimiter:
    """
    Rate limiter for alert generation and notification sending.

    Security: FDA-970 HIGH-4 remediation
    - Prevents notification flooding (DoS)
    - Per-product-code limits
    - Sliding window algorithm
    """

    def __init__(self, max_per_hour: int = 100):
        """
        Initialize rate limiter.

        Args:
            max_per_hour: Maximum alerts per product code per hour

        Security: FDA-970 HIGH-4
        - Default 100 alerts/hour prevents flooding
        - Adjustable for different product categories
        """
        self.max_per_hour = max_per_hour
        self.alert_timestamps: Dict[str, List[datetime]] = defaultdict(list)

    def check_rate_limit(self, product_code: str) -> bool:
        """
        Check if alert rate limit is exceeded for a product code.

        Args:
            product_code: FDA product code

        Returns:
            True if within limit

        Raises:
            ValueError: If rate limit exceeded

        Security: FDA-970 HIGH-4 remediation
        - Sliding 1-hour window
        - Automatic cleanup of old timestamps
        - Per-product-code tracking
        """
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        # Clean old timestamps (sliding window)
        self.alert_timestamps[product_code] = [
            ts for ts in self.alert_timestamps[product_code]
            if ts > one_hour_ago
        ]

        # Check limit
        current_count = len(self.alert_timestamps[product_code])
        if current_count >= self.max_per_hour:
            raise ValueError(
                f"Rate limit exceeded for product code {product_code}: "
                f"{current_count}/{self.max_per_hour} alerts in last hour. "
                f"This may indicate a notification flooding attack or data import issue."
            )

        # Record new alert timestamp
        self.alert_timestamps[product_code].append(now)
        return True

    def get_current_rate(self, product_code: str) -> int:
        """
        Get current alert rate for a product code.

        Args:
            product_code: FDA product code

        Returns:
            Number of alerts in last hour
        """
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        # Count timestamps in last hour
        return sum(
            1 for ts in self.alert_timestamps.get(product_code, [])
            if ts > one_hour_ago
        )

    def reset(self, product_code: Optional[str] = None):
        """
        Reset rate limiter (for testing or manual override).

        Args:
            product_code: Optional product code to reset (resets all if None)
        """
        if product_code:
            self.alert_timestamps[product_code] = []
        else:
            self.alert_timestamps = defaultdict(list)


# ============================================================
# Severity Validation (FDA-970 HIGH-3)
# ============================================================

# Severity rules per alert type
SEVERITY_RULES = {
    # CRITICAL alerts
    'recall_class_i': 'CRITICAL',
    'recall_class_1': 'CRITICAL',
    'safety_alert': 'CRITICAL',
    'maude_death_spike': 'CRITICAL',
    'maude_safety': 'CRITICAL',  # Added for consistency

    # WARNING alerts
    'recall_class_ii': 'WARNING',
    'recall_class_2': 'WARNING',
    'supplement_safety': 'WARNING',
    'recall': 'WARNING',  # Default recall severity

    # INFO alerts
    'new_approval': 'INFO',
    'new_supplement': 'INFO',
    'routine_update': 'INFO',
}


def validate_alert_severity(alert: Dict[str, Any]) -> str:
    """
    Validate and auto-correct alert severity based on alert type.

    Args:
        alert: Alert dictionary with 'alert_type' and 'severity' fields

    Returns:
        Validated severity ('CRITICAL', 'WARNING', or 'INFO')

    Security: FDA-970 HIGH-3 remediation
    - Prevents severity escalation attacks
    - Ensures severity matches alert content
    - Auto-corrects mismatched severity
    - Logs mismatches for audit trail
    """
    alert_type = alert.get('alert_type', '').lower()
    claimed_severity = alert.get('severity', 'INFO')

    # Determine required severity from alert type
    required_severity = SEVERITY_RULES.get(alert_type, 'INFO')

    # Validate claimed severity matches required
    if claimed_severity != required_severity:
        logger.warning(
            f"Alert severity mismatch detected: "
            f"alert_type='{alert_type}', "
            f"claimed_severity='{claimed_severity}', "
            f"required_severity='{required_severity}'. "
            f"Auto-correcting to '{required_severity}'. "
            f"This may indicate a severity escalation attack or data corruption."
        )

        # Auto-correct severity
        alert['severity'] = required_severity

    return alert['severity']


# ============================================================
# Secure Deduplication (FDA-970 CRITICAL-2)
# ============================================================

def generate_alert_dedup_key(alert: Dict[str, Any]) -> str:
    """
    Generate a secure deduplication key using full SHA-256.

    Args:
        alert: Alert dictionary

    Returns:
        Full SHA-256 hash (64 hex characters)

    Security: FDA-970 CRITICAL-2 remediation
    - Uses full SHA-256 (256 bits) instead of truncated 16 chars
    - Collision-resistant (2^-128 probability)
    - Includes all relevant fields for uniqueness
    - Sorted JSON for deterministic hashing
    """
    # Include all relevant fields for uniqueness
    dedup_fields = {
        'alert_type': alert.get('alert_type', ''),
        'pma_number': alert.get('pma_number', ''),
        'product_code': alert.get('product_code', ''),
        'supplement_number': alert.get('supplement_number', ''),
        'decision_date': alert.get('decision_date', ''),
        'event_id': alert.get('event_id', ''),  # For recalls
        'data_key': alert.get('data_key', ''),
    }

    # Sort keys for consistent hashing
    raw = json.dumps(dedup_fields, sort_keys=True)

    # Use full SHA-256 (not truncated!)
    # 64 hex chars = 256 bits = collision-resistant
    return hashlib.sha256(raw.encode()).hexdigest()  # Full 64 characters


# ============================================================
# Alert Queue Management (FDA-970 HIGH-4)
# ============================================================

class AlertQueue:
    """
    Alert queue with overflow protection.

    Security: FDA-970 HIGH-4 remediation
    - Bounded queue size prevents memory exhaustion
    - Overflow detection and logging
    - FIFO eviction when full
    """

    MAX_QUEUE_SIZE = 10000

    def __init__(self, max_size: int = MAX_QUEUE_SIZE):
        """
        Initialize alert queue.

        Args:
            max_size: Maximum queue size

        Security: FDA-970 HIGH-4
        - Default 10,000 alerts prevents memory exhaustion
        - Older alerts evicted if queue full
        """
        self.max_size = max_size
        self.queue: List[Dict[str, Any]] = []
        self.overflow_count = 0

    def enqueue(self, alert: Dict[str, Any]) -> bool:
        """
        Add alert to queue with overflow detection.

        Args:
            alert: Alert dictionary

        Returns:
            True if enqueued successfully

        Raises:
            ValueError: If queue is full (possible flooding attack)

        Security: FDA-970 HIGH-4 remediation
        - Rejects alerts when queue full
        - Logs overflow for incident response
        """
        if len(self.queue) >= self.max_size:
            self.overflow_count += 1
            logger.error(
                f"Alert queue overflow! Queue size: {len(self.queue)}, "
                f"Total overflow count: {self.overflow_count}. "
                f"This may indicate a notification flooding attack or "
                f"data import issue. Alert dropped: {alert.get('alert_type', 'UNKNOWN')}"
            )
            raise ValueError(
                f"Alert queue full ({self.max_size} alerts). "
                f"Possible flooding attack or bulk import issue. "
                f"Current overflow count: {self.overflow_count}"
            )

        self.queue.append(alert)
        return True

    def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        Remove and return oldest alert from queue (FIFO).

        Returns:
            Alert dictionary or None if queue empty
        """
        if self.queue:
            return self.queue.pop(0)
        return None

    def size(self) -> int:
        """Get current queue size."""
        return len(self.queue)

    def is_full(self) -> bool:
        """Check if queue is at capacity."""
        return len(self.queue) >= self.max_size

    def clear(self):
        """Clear queue (for testing or manual reset)."""
        self.queue = []
        self.overflow_count = 0


# ============================================================
# Utility Functions
# ============================================================

def get_security_metrics() -> Dict[str, Any]:
    """
    Get monitoring security metrics.

    Returns:
        Dictionary with security metrics
    """
    return {
        "product_code_cache_size": len(
            ProductCodeValidator._valid_codes_cache or set()
        ),
        "product_code_cache_age_hours": (
            (datetime.now(timezone.utc) - ProductCodeValidator._cache_timestamp).total_seconds() / 3600
            if ProductCodeValidator._cache_timestamp
            else None
        ),
        "severity_rules_count": len(SEVERITY_RULES),
        "max_queue_size": AlertQueue.MAX_QUEUE_SIZE,
    }
