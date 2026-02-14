#!/usr/bin/env python3
"""
Alert delivery module for FDA Monitor.

Supports webhook (POST) and stdout (JSON) delivery.
Reads alert JSON from ~/fda-510k-data/monitor_alerts/.
Config from ~/.claude/fda-tools.local.md.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, date, timezone
from pathlib import Path


DEFAULT_ALERT_DIR = os.path.expanduser("~/fda-510k-data/monitor_alerts")
SETTINGS_PATH = os.path.expanduser("~/.claude/fda-tools.local.md")


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
    """
    url = webhook_url or settings.get("webhook_url")
    if not url:
        return {"success": False, "error": "No webhook_url configured"}

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

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
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


def deliver_alerts(alerts, method="stdout", settings=None, **kwargs):
    """Deliver alerts via the specified method.

    Args:
        alerts: List of alert dicts.
        method: One of 'webhook', 'stdout'.
        settings: Config dict (loaded from file if None).
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
        return send_webhook(filtered, settings, **kwargs)
    elif method == "stdout":
        return send_stdout(filtered, **kwargs)
    else:
        return {"success": False, "error": f"Unknown delivery method: {method}"}


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
