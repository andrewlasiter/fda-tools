#!/usr/bin/env python3
"""
Alert delivery module for FDA Monitor.

Supports webhook (POST) and stdout (JSON) delivery.
Reads alert JSON from ~/fda-510k-data/monitor_alerts/.
Config from ~/.claude/fda-tools.local.md.

Audit logging (FDA-122 / 21 CFR Part 11):
  Every delivery attempt is durably recorded to a JSON Lines audit log.
  Logs rotate daily and when a single file reaches MAX_AUDIT_FILE_BYTES.
  Files older than AUDIT_RETENTION_DAYS are automatically pruned.
  Use query_audit_log() / export_audit_csv() for compliance reports.
"""

import csv
import fcntl
import gzip
import ipaddress
import io
import json
import os
import re
import socket
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_ALERT_DIR = os.path.expanduser("~/fda-510k-data/monitor_alerts")
DEFAULT_AUDIT_DIR = os.path.expanduser("~/fda-510k-data/monitor_alerts/audit")
SETTINGS_PATH = os.path.expanduser("~/.claude/fda-tools.local.md")

# Audit log limits (FDA-122)
MAX_AUDIT_FILE_BYTES: int = 100 * 1024 * 1024   # 100 MB per log file
AUDIT_RETENTION_DAYS: int = 1095                 # 3 years (21 CFR Part 11)


# ============================================================================
# Audit Logger (FDA-122 / 21 CFR Part 11)
# ============================================================================

class AuditLogger:
    """Persistent, append-only audit log for FDA alert deliveries.

    Each delivery attempt produces one JSON Lines record written durably
    to disk via an ``fcntl`` exclusive lock + atomic append.

    File naming convention:
        ``audit_YYYY-MM-DD.jsonl``       — active log for today
        ``audit_YYYY-MM-DD_001.jsonl``   — size-rotation overflow files
        ``audit_YYYY-MM-DD.jsonl.gz``    — compressed archive of completed days

    Retention:
        Files older than ``AUDIT_RETENTION_DAYS`` (1095 days / 3 years) are
        automatically deleted to comply with FDA data-retention policies.

    Args:
        log_dir: Directory for audit files.  Created on first write.
    """

    def __init__(self, log_dir: Optional[str] = None) -> None:
        self.log_dir = Path(log_dir or DEFAULT_AUDIT_DIR)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append(self, record: Dict[str, Any]) -> None:
        """Write *record* as a JSON line to today's audit file.

        Acquires an exclusive ``fcntl`` lock on the log file before
        writing so concurrent processes cannot interleave partial records.

        Args:
            record: Audit event dict.  A ``"logged_at"`` field is added
                automatically if not already present.
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)

        if "logged_at" not in record:
            record = {**record, "logged_at": datetime.now(timezone.utc).isoformat()}

        line = json.dumps(record, ensure_ascii=False) + "\n"
        encoded = line.encode("utf-8")

        log_path = self._active_log_path()

        # Acquire exclusive lock, append, release.
        with open(log_path, "ab") as fh:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX)
                fh.write(encoded)
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

        # Trigger rotation if file now exceeds the size limit.
        if log_path.stat().st_size >= MAX_AUDIT_FILE_BYTES:
            self._rotate(log_path)

    def prune(self) -> List[str]:
        """Delete audit files older than ``AUDIT_RETENTION_DAYS``.

        Returns:
            List of file names that were deleted.
        """
        if not self.log_dir.exists():
            return []

        cutoff = datetime.now(timezone.utc).date() - timedelta(days=AUDIT_RETENTION_DAYS)
        deleted: List[str] = []

        for f in self.log_dir.iterdir():
            if not f.name.startswith("audit_"):
                continue
            file_date = self._date_from_filename(f.name)
            if file_date and file_date < cutoff:
                f.unlink(missing_ok=True)
                deleted.append(f.name)

        return deleted

    def query(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        status: Optional[str] = None,
        method: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Read audit records matching the given filters.

        Args:
            since: ISO date string (inclusive lower bound on ``logged_at``).
            until: ISO date string (inclusive upper bound on ``logged_at``).
            status: Filter by ``status`` field (e.g. ``"success"``, ``"failed"``).
            method: Filter by ``method`` field (e.g. ``"webhook"``, ``"stdout"``).

        Returns:
            List of matching audit record dicts, sorted by ``logged_at``.
        """
        records: List[Dict[str, Any]] = []

        for log_path in self._all_log_paths():
            for line in self._read_lines(log_path):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue

                logged_at = rec.get("logged_at", "")
                if since and logged_at < since:
                    continue
                if until and logged_at > until:
                    continue
                if status and rec.get("status") != status:
                    continue
                if method and rec.get("method") != method:
                    continue
                records.append(rec)

        records.sort(key=lambda r: r.get("logged_at", ""))
        return records

    def export_csv(
        self,
        records: List[Dict[str, Any]],
        output_path: Optional[str] = None,
    ) -> str:
        """Export *records* to CSV format.

        Args:
            records: List of audit record dicts (e.g. from :meth:`query`).
            output_path: File path to write.  If ``None``, returns the CSV
                as a string.

        Returns:
            CSV text (also written to *output_path* if provided).
        """
        if not records:
            return ""

        # Collect all keys across records, keeping a stable order.
        fieldnames: List[str] = []
        seen: set = set()
        priority = ["logged_at", "method", "status", "alert_count",
                    "response_code", "recipient", "error"]
        for key in priority:
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
        for rec in records:
            for key in rec:
                if key not in seen:
                    fieldnames.append(key)
                    seen.add(key)

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow({k: rec.get(k, "") for k in fieldnames})

        csv_text = buf.getvalue()

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(csv_text, encoding="utf-8")

        return csv_text

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _active_log_path(self) -> Path:
        """Return the path for today's active log file."""
        today = date.today().isoformat()
        base = self.log_dir / f"audit_{today}.jsonl"
        if not base.exists():
            return base

        # If today's base file already exceeds the limit, find or create
        # the next numbered overflow file.
        if base.stat().st_size < MAX_AUDIT_FILE_BYTES:
            return base

        idx = 1
        while True:
            candidate = self.log_dir / f"audit_{today}_{idx:03d}.jsonl"
            if not candidate.exists() or candidate.stat().st_size < MAX_AUDIT_FILE_BYTES:
                return candidate
            idx += 1

    def _rotate(self, log_path: Path) -> None:
        """Gzip-compress *log_path* to an archive alongside it."""
        archive = log_path.with_suffix(log_path.suffix + ".gz")
        try:
            with open(log_path, "rb") as src, gzip.open(archive, "wb") as dst:
                dst.write(src.read())
            log_path.unlink()
        except OSError:
            pass  # Rotation is best-effort; original file preserved on failure

    def _all_log_paths(self) -> List[Path]:
        """Return all plain and gzip'd audit log paths, oldest first."""
        if not self.log_dir.exists():
            return []
        paths = [
            f for f in self.log_dir.iterdir()
            if f.name.startswith("audit_") and f.suffix in (".jsonl", ".gz")
        ]
        paths.sort(key=lambda p: p.name)
        return paths

    @staticmethod
    def _date_from_filename(name: str) -> Optional[date]:
        """Extract a :class:`date` from an audit filename."""
        m = re.match(r"audit_(\d{4}-\d{2}-\d{2})", name)
        if not m:
            return None
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            return None

    @staticmethod
    def _read_lines(log_path: Path) -> List[str]:
        """Read lines from a plain or gzip'd log file."""
        try:
            if log_path.suffix == ".gz":
                with gzip.open(log_path, "rt", encoding="utf-8") as fh:
                    return fh.readlines()
            with open(log_path, encoding="utf-8") as fh:
                return fh.readlines()
        except OSError:
            return []


# Module-level default logger (may be replaced in tests).
_default_audit_logger: Optional[AuditLogger] = None


def _get_audit_logger() -> AuditLogger:
    """Return (or lazily create) the module-level :class:`AuditLogger`."""
    global _default_audit_logger
    if _default_audit_logger is None:
        _default_audit_logger = AuditLogger()
    return _default_audit_logger


# ============================================================================
# Security: SSRF Prevention (FDA-99 / CWE-918)
# ============================================================================

def _is_private_ip(ip_str):
    """Check if an IP address is in a private range.

    Args:
        ip_str: IP address string (IPv4 or IPv6)

    Returns:
        True if IP is private/link-local/loopback, False otherwise

    Security: FDA-99 (CWE-918) - Prevents SSRF to internal networks
    """
    try:
        ip = ipaddress.ip_address(ip_str)

        # Check for private, loopback, link-local, and multicast ranges
        return (
            ip.is_private or          # 10.x, 172.16-31.x, 192.168.x, fd00::/8
            ip.is_loopback or         # 127.x, ::1
            ip.is_link_local or       # 169.254.x, fe80::/10
            ip.is_multicast or        # 224.x-239.x, ff00::/8
            ip.is_reserved or         # Reserved ranges
            ip.is_unspecified         # 0.0.0.0, ::
        )
    except ValueError:
        # Invalid IP address
        return True  # Reject invalid IPs as a safety measure


def _validate_webhook_url(url):
    """Validate webhook URL to prevent SSRF attacks.

    Args:
        url: Webhook URL string

    Returns:
        Validated URL string

    Raises:
        ValueError: If URL is invalid or points to private network

    Security: FDA-99 (CWE-918) - SSRF Prevention
    Implements OWASP SSRF Prevention Cheat Sheet recommendations:
    1. Scheme validation (HTTPS only)
    2. Private IP range blocking
    3. DNS resolution verification (prevents DNS rebinding)
    """
    if not url:
        raise ValueError("Webhook URL cannot be empty")

    # Parse URL
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {url}") from e

    # 1. Validate scheme (HTTPS only for security)
    if parsed.scheme != "https":
        raise ValueError(
            f"Security: Only HTTPS webhooks allowed (got: {parsed.scheme}://). "
            f"This prevents credential leakage and MitM attacks."
        )

    # 2. Validate hostname exists
    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"URL must contain a valid hostname: {url}")

    # 3. Block localhost and loopback
    localhost_patterns = ["localhost", "127.", "::1", "0.0.0.0"]
    hostname_lower = hostname.lower()
    if any(pattern in hostname_lower for pattern in localhost_patterns):
        raise ValueError(
            f"Security: Webhook URL cannot target localhost/loopback addresses. "
            f"Hostname: {hostname}"
        )

    # 4. DNS resolution and IP validation (prevents DNS rebinding)
    try:
        # Resolve hostname to IP address(es)
        addr_info = socket.getaddrinfo(hostname, None, family=socket.AF_UNSPEC)
        resolved_ips = [info[4][0] for info in addr_info]

        # Check each resolved IP for private ranges
        for ip_str in resolved_ips:
            if _is_private_ip(ip_str):
                raise ValueError(
                    f"Security: Webhook URL resolves to private IP address. "
                    f"Hostname '{hostname}' → {ip_str}. "
                    f"Private IPs blocked: 10.x, 172.16-31.x, 192.168.x, 169.254.x, 127.x"
                )
    except socket.gaierror as e:
        raise ValueError(f"DNS resolution failed for hostname '{hostname}': {e}") from e
    except ValueError:
        # Re-raise our security errors
        raise
    except Exception as e:
        raise ValueError(f"Error validating webhook URL '{hostname}': {e}") from e

    # 5. Block AWS/GCP/Azure metadata endpoints (belt-and-suspenders)
    cloud_metadata_domains = [
        "169.254.169.254",          # AWS/GCP/Azure link-local
        "metadata.google.internal",  # GCP
        "metadata.azure.com",        # Azure
    ]
    if any(domain in hostname_lower for domain in cloud_metadata_domains):
        raise ValueError(
            f"Security: Webhook URL cannot target cloud metadata services. "
            f"Hostname: {hostname}"
        )

    return url


def load_settings():
    """Load alert configuration from settings file."""
    settings = {
        "webhook_url": None,
        "alert_severity_threshold": "info",
        "alert_frequency": "immediate",
    }
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH) as f:
            content = f.read()
        for key in settings:
            m = re.search(rf"{key}:\s*(.+)", content)
            if m:
                val = m.group(1).strip()
                if val != "null":
                    settings[key] = val
    return settings


def load_alerts(alert_dir=None, since_date=None):
    """Load alerts from the alert directory.

    Args:
        alert_dir: Path to alert directory. Default: ~/fda-510k-data/monitor_alerts/
        since_date: Only load alerts from this date forward (YYYY-MM-DD string).

    Returns:
        List of alert dicts with date metadata.
    """
    alert_dir = Path(alert_dir or DEFAULT_ALERT_DIR)
    if not alert_dir.exists():
        return []

    all_alerts = []
    for alert_file in sorted(alert_dir.glob("*.json")):
        file_date = alert_file.stem  # e.g., "2026-02-05"
        if since_date and file_date < since_date:
            continue
        try:
            with open(alert_file) as f:
                data = json.load(f)
            for alert in data.get("alerts", []):
                alert["_file_date"] = file_date
                all_alerts.append(alert)
        except (json.JSONDecodeError, OSError):
            continue

    return all_alerts


def filter_by_severity(alerts, threshold="info"):
    """Filter alerts by severity threshold.

    Severity levels: critical > warning > info
    """
    severity_order = {"critical": 3, "warning": 2, "info": 1}
    threshold_val = severity_order.get(threshold, 1)
    return [a for a in alerts if severity_order.get(a.get("severity", "info"), 1) >= threshold_val]


def format_alert_text(alert):
    """Format a single alert as human-readable text."""
    atype = alert.get("type", "unknown")
    severity = alert.get("severity", "info").upper()
    file_date = alert.get("_file_date", "")

    lines = [f"[{severity}] {atype} — {file_date}"]

    if atype == "new_clearance":
        lines.append(f"  Device: {alert.get('device_name', 'N/A')}")
        lines.append(f"  K-number: {alert.get('knumber', 'N/A')}")
        lines.append(f"  Applicant: {alert.get('applicant', 'N/A')}")
        lines.append(f"  Product Code: {alert.get('product_code', 'N/A')}")
    elif atype == "recall":
        lines.append(f"  Firm: {alert.get('recalling_firm', 'N/A')}")
        lines.append(f"  Classification: {alert.get('classification', 'N/A')}")
        lines.append(f"  Reason: {alert.get('reason', 'N/A')}")
    elif atype == "maude_event":
        lines.append(f"  Event Type: {alert.get('event_type', 'N/A')}")
        lines.append(f"  Count Since Last: {alert.get('count_since_last', 'N/A')}")
        lines.append(f"  Product Code: {alert.get('product_code', 'N/A')}")
    elif atype == "guidance_update":
        lines.append(f"  Title: {alert.get('title', 'N/A')}")
        lines.append(f"  URL: {alert.get('url', 'N/A')}")
    elif atype == "standard_update":
        lines.append(f"  Standard: {alert.get('standard', 'N/A')}")
        lines.append(f"  Old: {alert.get('old_version', 'N/A')} -> New: {alert.get('new_version', 'N/A')}")
        lines.append(f"  Transition: {alert.get('transition_deadline', 'N/A')}")
        lines.append(f"  Action: {alert.get('action_required', 'N/A')}")
    else:
        for k, v in alert.items():
            if not k.startswith("_"):
                lines.append(f"  {k}: {v}")

    return "\n".join(lines)


def format_alert_json(alerts):
    """Format alerts as machine-readable JSON for cron output."""
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "alert_count": len(alerts),
        "alerts": [],
    }
    for alert in alerts:
        clean = {k: v for k, v in alert.items() if not k.startswith("_")}
        clean["date"] = alert.get("_file_date", "")
        output["alerts"].append(clean)
    return json.dumps(output, indent=2)


def send_webhook(alerts, settings, webhook_url=None):
    """Send alerts via webhook POST.

    Args:
        alerts: List of alert dicts.
        settings: Config dict.
        webhook_url: Override URL (uses settings webhook_url if not provided).

    Returns:
        dict with success status and message.

    Security: FDA-99 (CWE-918) - URL validated to prevent SSRF attacks
    """
    url = webhook_url or settings.get("webhook_url")
    if not url:
        return {"success": False, "error": "No webhook_url configured"}

    # Security: Validate webhook URL to prevent SSRF (FDA-99 / CWE-918)
    try:
        url = _validate_webhook_url(url)
    except ValueError as e:
        return {"success": False, "error": f"Invalid webhook URL: {e}"}

    payload = {
        "source": "fda-tools-monitor",
        "version": "4.8.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "alert_count": len(alerts),
        "alerts": [{k: v for k, v in a.items() if not k.startswith("_")} for a in alerts],
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "FDA-Plugin-Monitor/4.8.0",
        },
        method="POST",
    )

    # FDA-107: Create SSL context with certificate verification enabled
    ssl_context = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as resp:
            status = resp.status
            return {"success": status < 400, "message": f"Webhook response: HTTP {status}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_stdout(alerts, cron_mode=False):
    """Output alerts to stdout.

    Args:
        alerts: List of alert dicts.
        cron_mode: If True, output machine-readable JSON. If False, human-readable text.

    Returns:
        dict with success status.
    """
    if cron_mode:
        print(format_alert_json(alerts))
    else:
        for alert in alerts:
            print(format_alert_text(alert))
            print()
    return {"success": True, "message": f"Output {len(alerts)} alerts to stdout"}


def deliver_alerts(alerts, method="stdout", settings=None, audit_logger=None, **kwargs):
    """Deliver alerts via the specified method.

    Every delivery attempt is recorded to the persistent audit log
    (FDA-122 / 21 CFR Part 11).  Use ``audit_logger=...`` to override the
    logger in tests; pass ``audit_logger=False`` to disable logging.

    Args:
        alerts: List of alert dicts.
        method: One of 'webhook', 'stdout'.
        settings: Config dict (loaded from file if None).
        audit_logger: :class:`AuditLogger` instance, ``False`` to disable, or
            ``None`` to use the module default.
        **kwargs: Additional args passed to the delivery function.

    Returns:
        dict with success status and message.
    """
    if not alerts:
        return {"success": True, "message": "No alerts to deliver"}

    if settings is None:
        settings = load_settings()

    # Filter by severity threshold
    threshold = settings.get("alert_severity_threshold", "info")
    filtered = filter_by_severity(alerts, threshold)
    if not filtered:
        return {"success": True, "message": f"No alerts above {threshold} threshold"}

    if method == "webhook":
        result = send_webhook(filtered, settings, **kwargs)
    elif method == "stdout":
        result = send_stdout(filtered, **kwargs)
    else:
        result = {"success": False, "error": f"Unknown delivery method: {method}"}

    # --- Audit log (FDA-122 / 21 CFR Part 11) ---------------------------
    if audit_logger is not False:
        logger = audit_logger if isinstance(audit_logger, AuditLogger) else _get_audit_logger()
        _severity_counts = {}
        for a in filtered:
            sev = a.get("severity", "info")
            _severity_counts[sev] = _severity_counts.get(sev, 0) + 1

        audit_record: Dict[str, Any] = {
            "method": method,
            "alert_count": len(filtered),
            "severity_counts": _severity_counts,
            "status": "success" if result.get("success") else "failed",
            "message": result.get("message"),
            "error": result.get("error"),
        }
        if method == "webhook":
            webhook_url = kwargs.get("webhook_url") or (settings or {}).get("webhook_url", "")
            # Redact credentials from URL before storing
            try:
                parsed = urllib.parse.urlparse(webhook_url or "")
                audit_record["recipient"] = parsed.netloc  # host:port only, no path/token
            except Exception:
                audit_record["recipient"] = ""

        try:
            logger.append(audit_record)
            # Opportunistically prune old files on each write (cheap if no old files).
            logger.prune()
        except Exception as exc:  # noqa: BLE001 — audit failure must not break delivery
            print(f"Warning: Audit log write failed: {exc}", file=sys.stderr)

    return result


def main():
    """CLI entry point for alert delivery."""
    import argparse

    parser = argparse.ArgumentParser(description="FDA Monitor Alert Sender")
    parser.add_argument("--method", choices=["webhook", "stdout"],
                        default="stdout", help="Delivery method")
    parser.add_argument("--alert-dir", help="Alert directory path")
    parser.add_argument("--since", help="Only send alerts since date (YYYY-MM-DD)")
    parser.add_argument("--cron", action="store_true", help="Machine-readable JSON output")
    parser.add_argument("--webhook-url", help="Override webhook URL")
    parser.add_argument("--test", action="store_true", help="Send a test alert")
    args = parser.parse_args()

    settings = load_settings()

    if args.test:
        test_alerts = [{
            "type": "new_clearance",
            "product_code": "TEST",
            "device_name": "Test Device (Alert System Verification)",
            "knumber": "K999999",
            "applicant": "TEST COMPANY",
            "decision_date": date.today().strftime("%Y%m%d"),
            "severity": "info",
            "_file_date": date.today().isoformat(),
        }]
        result = deliver_alerts(test_alerts, method=args.method, settings=settings,
                                cron_mode=args.cron, webhook_url=args.webhook_url)
    else:
        alerts = load_alerts(alert_dir=args.alert_dir, since_date=args.since)
        result = deliver_alerts(alerts, method=args.method, settings=settings,
                                cron_mode=args.cron, webhook_url=args.webhook_url)

    if not result.get("success"):
        print(f"ERROR: {result.get('error')}", file=sys.stderr)
        sys.exit(1)
    elif args.method != "stdout":
        print(result.get("message", "Done"))


if __name__ == "__main__":
    main()
