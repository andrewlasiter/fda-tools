"""
Monitoring Manager - Real-Time Monitoring and Alerting for FDA Tools Enterprise

Provides enterprise-grade monitoring with:
1. Real-time security violation detection and alerting
2. LLM provider health monitoring (Ollama, Anthropic, OpenAI)
3. Performance metrics collection and querying
4. Multi-destination alert delivery (email, Slack, webhook)
5. Unusual activity detection with threshold-based rules
6. Alert lifecycle management (create, acknowledge, resolve)

Author: FDA Tools Development Team
Date: 2026-02-16
Version: 1.0.0
"""

import os
import json
import uuid
import time
import logging
import sys
import threading
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from copy import deepcopy

logger = logging.getLogger("fda-monitoring")


class AlertType(str, Enum):
    """Types of monitoring alerts."""
    SECURITY_VIOLATION = "security_violation"
    LLM_PROVIDER_DOWN = "llm_provider_down"
    PERMISSION_DENIED = "permission_denied"
    UNUSUAL_ACTIVITY = "unusual_activity"
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_DEGRADED = "performance_degraded"
    SIGNATURE_FAILURE = "signature_failure"
    TENANT_BREACH = "tenant_breach"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Alert:
    """
    Monitoring alert with full context.

    Attributes:
        alert_id: Unique alert identifier
        alert_type: Type of alert
        severity: Severity level
        timestamp: ISO 8601 creation timestamp
        user_id: Related user (if applicable)
        message: Human-readable alert message
        details: Additional context
        resolved: Whether alert has been resolved
        resolved_at: Resolution timestamp
        resolved_by: User who resolved the alert
        acknowledged: Whether alert has been acknowledged
        acknowledged_at: Acknowledgment timestamp
    """
    alert_id: str
    alert_type: str
    severity: str
    timestamp: str
    user_id: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize alert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Deserialize alert from dictionary."""
        return cls(
            alert_id=data['alert_id'],
            alert_type=data['alert_type'],
            severity=data['severity'],
            timestamp=data['timestamp'],
            user_id=data.get('user_id'),
            message=data.get('message', ''),
            details=data.get('details', {}),
            resolved=data.get('resolved', False),
            resolved_at=data.get('resolved_at'),
            resolved_by=data.get('resolved_by'),
            acknowledged=data.get('acknowledged', False),
            acknowledged_at=data.get('acknowledged_at')
        )


@dataclass
class Metric:
    """
    Performance metric data point.

    Attributes:
        metric_name: Name of the metric
        value: Metric value
        timestamp: ISO 8601 timestamp
        tags: Key-value tags for filtering
    """
    metric_name: str
    value: float
    timestamp: str
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metric to dictionary."""
        return asdict(self)


class MonitoringManager:
    """
    Real-time monitoring and alerting for FDA Tools enterprise.

    Monitors security events, LLM provider health, and performance
    metrics. Sends alerts via email, Slack, and webhooks.

    Usage:
        monitor = MonitoringManager(
            alert_email="alerts@device-corp.com",
            alert_slack_webhook="https://hooks.slack.com/services/..."
        )
        monitor.send_alert(
            AlertType.SECURITY_VIOLATION,
            AlertSeverity.HIGH,
            "Multiple failed login attempts",
            details={"user_id": "usr_001", "attempt_count": 5}
        )
    """

    def __init__(
        self,
        alert_email: Optional[str] = None,
        alert_slack_webhook: Optional[str] = None,
        alert_webhook: Optional[str] = None,
        metrics_dir: Optional[str] = None,
        alerts_dir: Optional[str] = None
    ):
        """
        Initialize monitoring manager.

        Args:
            alert_email: Email address for alert delivery
            alert_slack_webhook: Slack webhook URL for alert delivery
            alert_webhook: Generic webhook URL for alert delivery
            metrics_dir: Directory for metrics storage
            alerts_dir: Directory for alerts storage
        """
        self.alert_email = alert_email
        self.alert_slack_webhook = alert_slack_webhook
        self.alert_webhook = alert_webhook

        if metrics_dir is None:
            metrics_dir = os.path.expanduser(
                "~/.claude/fda-tools-metrics"
            )
        if alerts_dir is None:
            alerts_dir = os.path.expanduser(
                "~/.claude/fda-tools-alerts"
            )

        self.metrics_dir = Path(metrics_dir)
        self.alerts_dir = Path(alerts_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.alerts_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._alerts: Dict[str, Alert] = {}
        self._metrics_buffer: List[Metric] = []
        self._failure_counts: Dict[str, int] = defaultdict(int)
        self._failure_timestamps: Dict[str, List[float]] = defaultdict(list)

        # Configuration
        self._failure_threshold = 5
        self._failure_window_seconds = 300  # 5 minutes
        self._metrics_flush_interval = 60  # seconds
        self._health_check_interval = 300  # 5 minutes

        # Load existing alerts
        self._load_alerts()

    # ========================================
    # Alert Management
    # ========================================

    def send_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Alert:
        """
        Create and send an alert.

        Args:
            alert_type: Type of alert
            severity: Severity level
            message: Human-readable alert message
            details: Optional additional context
            user_id: Optional related user

        Returns:
            Created Alert object
        """
        alert_id = "alert_{}".format(uuid.uuid4().hex[:12])
        now = datetime.now(timezone.utc).isoformat() + 'Z'

        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type.value if isinstance(alert_type, AlertType) else alert_type,
            severity=severity.value if isinstance(severity, AlertSeverity) else severity,
            timestamp=now,
            user_id=user_id,
            message=message,
            details=details or {},
            resolved=False
        )

        with self._lock:
            self._alerts[alert_id] = alert
            self._save_alert(alert)

        # Deliver alert via configured channels
        self._deliver_alert(alert)

        logger.warning(
            "ALERT [%s/%s]: %s (user=%s)",
            alert.alert_type, alert.severity,
            alert.message, alert.user_id or "system"
        )

        return deepcopy(alert)

    def get_alerts(
        self,
        since: Optional[datetime] = None,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        Query alerts with filters.

        Args:
            since: Only return alerts after this time
            severity: Filter by severity
            alert_type: Filter by alert type
            resolved: Filter by resolution status
            limit: Maximum alerts to return

        Returns:
            List of Alert objects (newest first)
        """
        with self._lock:
            alerts = list(self._alerts.values())

        # Apply filters
        filtered = []
        for alert in alerts:
            if since:
                alert_time = datetime.fromisoformat(
                    alert.timestamp.rstrip('Z')
                ).replace(tzinfo=timezone.utc)
                if alert_time < since:
                    continue

            if severity and alert.severity != severity:
                continue

            if alert_type and alert.alert_type != alert_type:
                continue

            if resolved is not None and alert.resolved != resolved:
                continue

            filtered.append(deepcopy(alert))

        # Sort by timestamp (newest first)
        filtered.sort(key=lambda a: a.timestamp, reverse=True)

        return filtered[:limit]

    def resolve_alert(
        self,
        alert_id: str,
        resolved_by: Optional[str] = None
    ) -> Optional[Alert]:
        """
        Mark an alert as resolved.

        Args:
            alert_id: Alert to resolve
            resolved_by: User who resolved the alert

        Returns:
            Updated Alert or None if not found
        """
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert is None:
                return None

            alert.resolved = True
            alert.resolved_at = datetime.now(timezone.utc).isoformat() + 'Z'
            alert.resolved_by = resolved_by

            self._save_alert(alert)

        return deepcopy(alert)

    def acknowledge_alert(
        self,
        alert_id: str
    ) -> Optional[Alert]:
        """
        Acknowledge an alert (mark as seen).

        Args:
            alert_id: Alert to acknowledge

        Returns:
            Updated Alert or None if not found
        """
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert is None:
                return None

            alert.acknowledged = True
            alert.acknowledged_at = (
                datetime.now(timezone.utc).isoformat() + 'Z'
            )

            self._save_alert(alert)

        return deepcopy(alert)

    # ========================================
    # LLM Provider Monitoring
    # ========================================

    def check_ollama_health(self) -> Tuple[bool, Optional[str]]:
        """
        Check Ollama LLM provider health.

        Returns:
            Tuple of (healthy, error_message)
        """
        try:
            import requests
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                models = response.json().get('models', [])
                return True, None
            else:
                error = "Ollama returned status {}".format(
                    response.status_code
                )
                return False, error
        except ImportError:
            return False, "requests library not available"
        except Exception as e:
            return False, str(e)

    def monitor_llm_providers(self) -> Dict[str, Any]:
        """
        Check health of all configured LLM providers.

        Returns:
            Dictionary with provider health status
        """
        status = {
            'ollama': {'healthy': False, 'error': None},
            'anthropic': {'healthy': False, 'error': None},
            'openai': {'healthy': False, 'error': None}
        }

        # Check Ollama
        healthy, error = self.check_ollama_health()
        status['ollama'] = {'healthy': healthy, 'error': error}

        # Check Anthropic (API key presence)
        if os.environ.get('ANTHROPIC_API_KEY'):
            status['anthropic'] = {'healthy': True, 'error': None}
        else:
            status['anthropic'] = {
                'healthy': False,
                'error': 'ANTHROPIC_API_KEY not set'
            }

        # Check OpenAI (API key presence)
        if os.environ.get('OPENAI_API_KEY'):
            status['openai'] = {'healthy': True, 'error': None}
        else:
            status['openai'] = {
                'healthy': False,
                'error': 'OPENAI_API_KEY not set'
            }

        # Record metrics
        for provider, info in status.items():
            self.record_metric(
                "llm_provider_health",
                1.0 if info['healthy'] else 0.0,
                tags={'provider': provider}
            )

        return status

    def alert_on_llm_failure(
        self,
        provider: str,
        error: str
    ) -> Alert:
        """
        Send alert when an LLM provider fails.

        Args:
            provider: Provider name
            error: Error message

        Returns:
            Created Alert
        """
        return self.send_alert(
            alert_type=AlertType.LLM_PROVIDER_DOWN,
            severity=AlertSeverity.HIGH,
            message="LLM provider '{}' is down: {}".format(provider, error),
            details={
                'provider': provider,
                'error': error,
                'impact': 'Commands requiring LLM may fail'
            }
        )

    # ========================================
    # Performance Monitoring
    # ========================================

    def record_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record a performance metric.

        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional key-value tags
        """
        metric = Metric(
            metric_name=metric_name,
            value=value,
            timestamp=datetime.now(timezone.utc).isoformat() + 'Z',
            tags=tags or {}
        )

        with self._lock:
            self._metrics_buffer.append(metric)

            # Auto-flush if buffer is large
            if len(self._metrics_buffer) >= 100:
                self._flush_metrics()

    def get_metrics(
        self,
        metric_name: str,
        since: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Query metrics with filters.

        Args:
            metric_name: Metric name to query
            since: Only return metrics after this time
            tags: Optional tag filters
            limit: Maximum metrics to return

        Returns:
            List of metric dictionaries
        """
        # Flush buffer first
        with self._lock:
            self._flush_metrics()

        # Read from metrics file
        metrics_file = self.metrics_dir / "metrics.jsonl"
        results = []

        if not metrics_file.exists():
            return results

        try:
            with open(metrics_file, 'r') as f:
                for line in f:
                    if len(results) >= limit:
                        break

                    try:
                        metric = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue

                    if metric.get('metric_name') != metric_name:
                        continue

                    if since:
                        m_time = datetime.fromisoformat(
                            metric['timestamp'].rstrip('Z')
                        ).replace(tzinfo=timezone.utc)
                        if m_time < since:
                            continue

                    if tags:
                        m_tags = metric.get('tags', {})
                        if not all(
                            m_tags.get(k) == v for k, v in tags.items()
                        ):
                            continue

                    results.append(metric)
        except OSError as e:
            print(f"Warning: Failed to read metrics file: {e}", file=sys.stderr)

        return results

    def flush_metrics(self) -> int:
        """
        Force flush metrics buffer to disk.

        Returns:
            Number of metrics flushed
        """
        with self._lock:
            return self._flush_metrics()

    # ========================================
    # Security Monitoring
    # ========================================

    def detect_unusual_activity(self, user_id: str) -> bool:
        """
        Detect unusual activity for a user based on failure rate.

        Args:
            user_id: User to check

        Returns:
            True if unusual activity detected
        """
        now = time.time()
        window_start = now - self._failure_window_seconds

        with self._lock:
            # Clean old timestamps
            self._failure_timestamps[user_id] = [
                ts for ts in self._failure_timestamps[user_id]
                if ts > window_start
            ]

            recent_failures = len(self._failure_timestamps[user_id])

        if recent_failures >= self._failure_threshold:
            self.send_alert(
                alert_type=AlertType.UNUSUAL_ACTIVITY,
                severity=AlertSeverity.HIGH,
                message=(
                    "Unusual activity detected for user '{}': "
                    "{} failures in {} seconds".format(
                        user_id, recent_failures,
                        self._failure_window_seconds
                    )
                ),
                user_id=user_id,
                details={
                    'failure_count': recent_failures,
                    'window_seconds': self._failure_window_seconds,
                    'threshold': self._failure_threshold
                }
            )
            return True

        return False

    def record_failure(self, user_id: str, failure_type: str) -> None:
        """
        Record a failure event for a user.

        Args:
            user_id: User who experienced the failure
            failure_type: Type of failure
        """
        now = time.time()

        with self._lock:
            self._failure_counts[user_id] += 1
            self._failure_timestamps[user_id].append(now)

        # Check if threshold reached
        self.detect_unusual_activity(user_id)

        # Record metric
        self.record_metric(
            "user_failure",
            1.0,
            tags={'user_id': user_id, 'failure_type': failure_type}
        )

    def alert_on_security_violation(
        self,
        user_id: str,
        violation: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """
        Send alert for a security violation.

        Args:
            user_id: User involved
            violation: Description of the violation
            details: Optional additional context

        Returns:
            Created Alert
        """
        return self.send_alert(
            alert_type=AlertType.SECURITY_VIOLATION,
            severity=AlertSeverity.CRITICAL,
            message="Security violation by '{}': {}".format(
                user_id, violation
            ),
            user_id=user_id,
            details=details or {}
        )

    def alert_on_permission_denied(
        self,
        user_id: str,
        command: str,
        reason: str
    ) -> Alert:
        """
        Send alert for permission denial.

        Args:
            user_id: User who was denied
            command: Command that was attempted
            reason: Denial reason

        Returns:
            Created Alert
        """
        self.record_failure(user_id, "permission_denied")

        return self.send_alert(
            alert_type=AlertType.PERMISSION_DENIED,
            severity=AlertSeverity.MEDIUM,
            message="Permission denied for '{}' on command '{}'".format(
                user_id, command
            ),
            user_id=user_id,
            details={'command': command, 'reason': reason}
        )

    def alert_on_tenant_breach(
        self,
        user_id: str,
        organization_id: str,
        target_path: str
    ) -> Alert:
        """
        Send critical alert for cross-tenant access attempt.

        Args:
            user_id: User attempting breach
            organization_id: User's organization
            target_path: Path they tried to access

        Returns:
            Created Alert
        """
        return self.send_alert(
            alert_type=AlertType.TENANT_BREACH,
            severity=AlertSeverity.CRITICAL,
            message=(
                "Cross-tenant access attempt by '{}' (org: {}). "
                "Attempted path: {}".format(
                    user_id, organization_id, target_path
                )
            ),
            user_id=user_id,
            details={
                'organization_id': organization_id,
                'target_path': target_path,
                'action_taken': 'blocked'
            }
        )

    # ========================================
    # Health Check
    # ========================================

    def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.

        Returns:
            Dictionary with full health report
        """
        llm_status = self.monitor_llm_providers()

        # Count active alerts
        active_alerts = self.get_alerts(resolved=False)
        critical_count = sum(
            1 for a in active_alerts if a.severity == "critical"
        )
        high_count = sum(
            1 for a in active_alerts if a.severity == "high"
        )

        # Determine overall health
        if critical_count > 0:
            overall = "critical"
        elif high_count > 0:
            overall = "degraded"
        elif not any(s['healthy'] for s in llm_status.values()):
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            'overall_status': overall,
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
            'llm_providers': llm_status,
            'alerts': {
                'total_active': len(active_alerts),
                'critical': critical_count,
                'high': high_count,
                'medium': sum(
                    1 for a in active_alerts if a.severity == "medium"
                ),
                'low': sum(
                    1 for a in active_alerts if a.severity == "low"
                )
            },
            'metrics': {
                'buffer_size': len(self._metrics_buffer),
                'metrics_dir': str(self.metrics_dir)
            }
        }

    # ========================================
    # Alert Delivery
    # ========================================

    def _deliver_alert(self, alert: Alert) -> None:
        """
        Deliver alert to configured destinations.

        Delivery is best-effort -- failures are logged but do not
        prevent alert creation.

        Args:
            alert: Alert to deliver
        """
        if self.alert_email:
            try:
                self._send_email_alert(alert)
            except Exception as e:
                logger.error(
                    "Failed to send email alert: %s", e
                )

        if self.alert_slack_webhook:
            try:
                self._send_slack_alert(alert)
            except Exception as e:
                logger.error(
                    "Failed to send Slack alert: %s", e
                )

        if self.alert_webhook:
            try:
                self._send_webhook_alert(alert)
            except Exception as e:
                logger.error(
                    "Failed to send webhook alert: %s", e
                )

    def _send_email_alert(self, alert: Alert) -> None:
        """
        Send alert via email.

        Args:
            alert: Alert to send
        """
        # Log the email that would be sent (actual SMTP requires configuration)
        logger.info(
            "EMAIL ALERT to %s: [%s/%s] %s",
            self.alert_email,
            alert.severity.upper() if isinstance(alert.severity, str) else alert.severity,
            alert.alert_type,
            alert.message
        )

        # In production, use smtplib:
        # import smtplib
        # from email.mime.text import MIMEText
        # msg = MIMEText(alert.message)
        # msg['Subject'] = "FDA Tools Alert [{severity}]: {type}".format(...)
        # msg['From'] = "alerts@fda-tools.local"
        # msg['To'] = self.alert_email
        # with smtplib.SMTP('localhost') as server:
        #     server.send_message(msg)

    def _send_slack_alert(self, alert: Alert) -> None:
        """
        Send alert to Slack via webhook.

        Args:
            alert: Alert to send
        """
        severity_emoji = {
            'low': 'information_source',
            'medium': 'warning',
            'high': 'rotating_light',
            'critical': 'fire'
        }

        emoji = severity_emoji.get(alert.severity, 'bell')

        payload = {
            "text": ":{}: *{}* [{}]: {}".format(
                emoji,
                alert.alert_type,
                alert.severity.upper() if isinstance(alert.severity, str) else alert.severity,
                alert.message
            ),
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "FDA Tools Alert"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": alert.message
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Severity:*\n{}".format(
                                alert.severity
                            )
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Type:*\n{}".format(
                                alert.alert_type
                            )
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Time:*\n{}".format(
                                alert.timestamp
                            )
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*User:*\n{}".format(
                                alert.user_id or "system"
                            )
                        }
                    ]
                }
            ]
        }

        try:
            import requests
            requests.post(
                self.alert_slack_webhook,
                json=payload,
                timeout=10
            )
        except ImportError:
            logger.warning("requests library not available for Slack alerts")

    def _send_webhook_alert(self, alert: Alert) -> None:
        """
        Send alert to generic webhook.

        Args:
            alert: Alert to send
        """
        try:
            import requests
            requests.post(
                self.alert_webhook,
                json=alert.to_dict(),
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
        except ImportError:
            logger.warning("requests library not available for webhook alerts")

    # ========================================
    # Internal Helpers
    # ========================================

    def _save_alert(self, alert: Alert) -> None:
        """Save alert to disk."""
        alert_file = self.alerts_dir / "{}.json".format(alert.alert_id)
        try:
            with open(alert_file, 'w') as f:
                json.dump(alert.to_dict(), f, indent=2, default=str)
        except OSError as e:
            print(f"Warning: Failed to save alert {alert.alert_id}: {e}", file=sys.stderr)

        # Also append to alerts log
        log_file = self.alerts_dir / "alerts.jsonl"
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(alert.to_dict()) + '\n')
        except OSError as e:
            print(f"Warning: Failed to append to alerts log: {e}", file=sys.stderr)

    def _load_alerts(self) -> None:
        """Load alerts from disk."""
        if not self.alerts_dir.exists():
            return

        for alert_file in self.alerts_dir.glob("alert_*.json"):
            try:
                with open(alert_file, 'r') as f:
                    data = json.load(f)
                alert = Alert.from_dict(data)
                self._alerts[alert.alert_id] = alert
            except (json.JSONDecodeError, KeyError, OSError):
                continue

    def _flush_metrics(self) -> int:
        """
        Flush metrics buffer to disk. Must be called with lock held.

        Returns:
            Number of metrics flushed
        """
        if not self._metrics_buffer:
            return 0

        metrics_file = self.metrics_dir / "metrics.jsonl"
        count = len(self._metrics_buffer)

        try:
            with open(metrics_file, 'a') as f:
                for metric in self._metrics_buffer:
                    f.write(json.dumps(metric.to_dict()) + '\n')
            self._metrics_buffer.clear()
        except OSError as e:
            print(f"Warning: Failed to flush metrics to disk: {e}", file=sys.stderr)

        return count

    @property
    def alert_count(self) -> int:
        """Get total number of alerts."""
        with self._lock:
            return len(self._alerts)

    @property
    def active_alert_count(self) -> int:
        """Get number of unresolved alerts."""
        with self._lock:
            return sum(
                1 for a in self._alerts.values() if not a.resolved
            )


# Global singleton
_monitoring_manager_instance: Optional[MonitoringManager] = None


def get_monitoring_manager(
    alert_email: Optional[str] = None,
    alert_slack_webhook: Optional[str] = None,
    alert_webhook: Optional[str] = None
) -> MonitoringManager:
    """
    Get global MonitoringManager instance (singleton pattern).

    Args:
        alert_email: Optional email for alerts
        alert_slack_webhook: Optional Slack webhook
        alert_webhook: Optional generic webhook

    Returns:
        MonitoringManager instance
    """
    global _monitoring_manager_instance
    if _monitoring_manager_instance is None:
        _monitoring_manager_instance = MonitoringManager(
            alert_email=alert_email,
            alert_slack_webhook=alert_slack_webhook,
            alert_webhook=alert_webhook
        )
    return _monitoring_manager_instance
