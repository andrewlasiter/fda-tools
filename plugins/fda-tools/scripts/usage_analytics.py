#!/usr/bin/env python3
"""
FDA Usage Analytics -- Opt-in Anonymous Usage Tracking (FDA-53).

Provides privacy-respecting, opt-in local analytics for the FDA Plugin.
All data is stored locally in ~/fda-510k-data/.analytics/usage.jsonl.
No data is transmitted externally. The user must explicitly enable
analytics via --enable-analytics in configure.py or by calling
UsageAnalytics.enable() programmatically.

Tracked metrics (when enabled):
    - command_name: Which command was invoked (e.g., "batchfetch", "extract")
    - execution_time_ms: Wall-clock duration of the command
    - success: Whether the command completed without error (bool)
    - product_code_count: Number of product codes processed (int)
    - timestamp: ISO 8601 UTC timestamp
    - plugin_version: Plugin version string
    - session_id: Random per-session UUID (not tied to user identity)

Privacy guarantees:
    - All data stored locally only (never transmitted)
    - No personally identifiable information (PII) collected
    - No API keys, project names, or device details recorded
    - User can delete analytics at any time (rm -rf ~/fda-510k-data/.analytics)
    - Disabled by default; requires explicit opt-in

Usage:
    from usage_analytics import UsageAnalytics

    analytics = UsageAnalytics()

    # Check if enabled
    if analytics.is_enabled():
        analytics.track_command("batchfetch", execution_time_ms=1234,
                                success=True, product_code_count=5)

    # Or use the context manager for automatic timing
    with analytics.track("extract", product_code_count=3):
        # ... run command ...
        pass

    # Enable/disable
    analytics.enable()
    analytics.disable()

    # View summary
    summary = analytics.get_summary(days=30)
    analytics.print_summary(days=30)

CLI:
    python3 usage_analytics.py --enable          # Enable analytics
    python3 usage_analytics.py --disable         # Disable analytics
    python3 usage_analytics.py --status          # Show current status
    python3 usage_analytics.py --summary         # Show usage summary (last 30 days)
    python3 usage_analytics.py --summary --days 7  # Last 7 days
    python3 usage_analytics.py --export          # Export analytics as JSON
    python3 usage_analytics.py --clear           # Delete all analytics data
    python3 usage_analytics.py --privacy         # Show privacy policy
"""

import argparse
import contextlib
import json
import logging
import os
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

# Import plugin version
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from version import PLUGIN_VERSION
except ImportError:
    PLUGIN_VERSION = "0.0.0"


# Analytics directory and files
ANALYTICS_DIR = Path(os.path.expanduser("~/fda-510k-data/.analytics"))
USAGE_FILE = ANALYTICS_DIR / "usage.jsonl"
CONFIG_FILE = ANALYTICS_DIR / "config.json"

# Privacy policy text
PRIVACY_POLICY = """
FDA Plugin Usage Analytics -- Privacy Policy
=============================================

1. PURPOSE
   Usage analytics help improve the FDA Plugin by understanding which
   commands are used most frequently, typical execution times, and
   common failure patterns. This information guides development
   priorities and performance optimization.

2. DATA COLLECTED (when enabled)
   - Command name (e.g., "batchfetch", "extract", "review")
   - Execution time in milliseconds
   - Success or failure status (boolean)
   - Number of product codes processed (count only)
   - Timestamp (UTC)
   - Plugin version
   - Anonymous session identifier (random UUID, not tied to identity)

3. DATA NOT COLLECTED
   - No personally identifiable information (PII)
   - No API keys or authentication tokens
   - No project names or file paths
   - No device names, K-numbers, or product codes
   - No network traffic or IP addresses
   - No operating system or hardware details beyond what is above

4. DATA STORAGE
   - All data is stored locally at:
     ~/fda-510k-data/.analytics/usage.jsonl
   - Data is NEVER transmitted to any external server
   - Data is stored in plain-text JSONL format (human-readable)

5. USER CONTROL
   - Analytics are DISABLED by default
   - Enable: python3 usage_analytics.py --enable
   - Disable: python3 usage_analytics.py --disable
   - Delete all data: python3 usage_analytics.py --clear
   - View data: python3 usage_analytics.py --export
   - View summary: python3 usage_analytics.py --summary

6. DATA RETENTION
   - No automatic data expiration
   - User can delete data at any time
   - Deleting the analytics directory removes all data:
     rm -rf ~/fda-510k-data/.analytics

7. CHANGES TO THIS POLICY
   - Any changes to data collection will require re-consent
   - The --enable flag must be re-issued after policy changes
""".strip()


class UsageAnalytics:
    """Opt-in local usage analytics for the FDA Plugin.

    All data is stored locally in JSONL format. No data is ever
    transmitted externally.

    Attributes:
        analytics_dir: Path to the analytics directory.
        usage_file: Path to the JSONL usage log.
        config_file: Path to the config JSON file.
        session_id: Random UUID for this session.
    """

    def __init__(
        self,
        analytics_dir: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """Initialize usage analytics.

        Args:
            analytics_dir: Override path for analytics directory.
                Default: ~/fda-510k-data/.analytics/
            session_id: Override session ID. Default: random UUID.
        """
        self.analytics_dir = Path(analytics_dir) if analytics_dir else ANALYTICS_DIR
        self.usage_file = self.analytics_dir / "usage.jsonl"
        self.config_file = self.analytics_dir / "config.json"
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self._config_cache: Optional[Dict[str, Any]] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load analytics configuration.

        Returns:
            Configuration dict with at least {"enabled": bool}.
        """
        if self._config_cache is not None:
            return self._config_cache

        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
                self._config_cache = config
                return config
            except (json.JSONDecodeError, OSError) as e:
                logger.debug("Could not load analytics config: %s", e)

        return {"enabled": False}

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save analytics configuration.

        Args:
            config: Configuration dict to persist.
        """
        try:
            self.analytics_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
            self._config_cache = config
        except OSError as e:
            logger.warning("Could not save analytics config: %s", e)

    def is_enabled(self) -> bool:
        """Check if analytics collection is enabled.

        Returns:
            True if the user has explicitly enabled analytics.
        """
        config = self._load_config()
        return config.get("enabled", False)

    def enable(self) -> None:
        """Enable analytics collection.

        Creates the analytics directory and config file. Must be called
        explicitly by the user (opt-in).
        """
        config = self._load_config()
        config["enabled"] = True
        config["enabled_at"] = datetime.now(timezone.utc).isoformat()
        config["plugin_version_at_enable"] = PLUGIN_VERSION
        self._save_config(config)
        logger.info("Usage analytics enabled. Data stored locally at %s", self.analytics_dir)

    def disable(self) -> None:
        """Disable analytics collection.

        Existing data is preserved but no new data is recorded.
        """
        config = self._load_config()
        config["enabled"] = False
        config["disabled_at"] = datetime.now(timezone.utc).isoformat()
        self._save_config(config)
        logger.info("Usage analytics disabled.")

    def track_command(
        self,
        command_name: str,
        execution_time_ms: int = 0,
        success: bool = True,
        product_code_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record a command execution event.

        Does nothing if analytics is disabled.

        Args:
            command_name: Name of the command (e.g., "batchfetch").
            execution_time_ms: Wall-clock time in milliseconds.
            success: Whether the command completed without error.
            product_code_count: Number of product codes processed.
            metadata: Optional additional metadata (no PII).

        Returns:
            True if the event was recorded, False if analytics is disabled.
        """
        if not self.is_enabled():
            return False

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "command_name": command_name,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "product_code_count": product_code_count,
            "plugin_version": PLUGIN_VERSION,
        }

        if metadata:
            # Only allow safe metadata keys (no strings that could contain PII)
            safe_keys = {"query_type", "cache_hit", "api_calls", "result_count",
                         "dry_run", "mode", "error_type"}
            event["metadata"] = {
                k: v for k, v in metadata.items()
                if k in safe_keys
            }

        try:
            self.analytics_dir.mkdir(parents=True, exist_ok=True)
            with open(self.usage_file, "a") as f:
                f.write(json.dumps(event) + "\n")
            return True
        except OSError as e:
            logger.debug("Could not write analytics event: %s", e)
            return False

    @contextlib.contextmanager
    def track(
        self,
        command_name: str,
        product_code_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Context manager for automatic command timing.

        Usage:
            with analytics.track("batchfetch", product_code_count=5) as ctx:
                # run command
                ctx["result_count"] = 150

        Args:
            command_name: Name of the command.
            product_code_count: Number of product codes.
            metadata: Optional metadata dict.

        Yields:
            A mutable dict that can be updated with additional metadata.
        """
        ctx: Dict[str, Any] = {"success": True}
        start = time.monotonic()

        try:
            yield ctx
        except Exception:
            ctx["success"] = False
            raise
        finally:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            merged_metadata = {**(metadata or {}), **{
                k: v for k, v in ctx.items()
                if k not in ("success",)
            }}
            self.track_command(
                command_name,
                execution_time_ms=elapsed_ms,
                success=ctx.get("success", True),
                product_code_count=product_code_count,
                metadata=merged_metadata if merged_metadata else None,
            )

    def load_events(
        self,
        days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Load events from the usage log.

        Args:
            days: If provided, only return events from the last N days.

        Returns:
            List of event dictionaries.
        """
        if not self.usage_file.exists():
            return []

        events = []
        cutoff = None
        if days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        try:
            with open(self.usage_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if cutoff is not None:
                        ts = event.get("timestamp", "")
                        try:
                            event_time = datetime.fromisoformat(ts)
                            if event_time.tzinfo is None:
                                event_time = event_time.replace(tzinfo=timezone.utc)
                            if event_time < cutoff:
                                continue
                        except (ValueError, TypeError):
                            continue

                    events.append(event)
        except OSError as e:
            logger.debug("Could not read analytics file: %s", e)

        return events

    def get_summary(
        self,
        days: Optional[int] = 30,
    ) -> Dict[str, Any]:
        """Generate a summary of usage analytics.

        Args:
            days: Number of days to include (default: 30). None = all time.

        Returns:
            Summary dictionary:
            {
                "period_days": int,
                "total_events": int,
                "unique_sessions": int,
                "commands": {"name": {"count": N, "avg_ms": N, "success_rate": float}},
                "daily_counts": {"YYYY-MM-DD": int},
                "top_commands": [("name", count)],
                "success_rate": float,
                "avg_execution_time_ms": float,
                "total_product_codes": int,
            }
        """
        events = self.load_events(days=days)

        if not events:
            return {
                "period_days": days,
                "total_events": 0,
                "unique_sessions": 0,
                "commands": {},
                "daily_counts": {},
                "top_commands": [],
                "success_rate": 0.0,
                "avg_execution_time_ms": 0.0,
                "total_product_codes": 0,
            }

        # Aggregate
        command_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total_ms": 0, "successes": 0, "product_codes": 0}
        )
        daily_counts: Dict[str, int] = Counter()
        sessions = set()
        total_ms = 0
        total_successes = 0
        total_product_codes = 0

        for event in events:
            cmd = event.get("command_name", "unknown")
            ms = event.get("execution_time_ms", 0)
            success = event.get("success", True)
            pc_count = event.get("product_code_count", 0)
            session = event.get("session_id", "")

            command_stats[cmd]["count"] += 1
            command_stats[cmd]["total_ms"] += ms
            command_stats[cmd]["product_codes"] += pc_count
            if success:
                command_stats[cmd]["successes"] += 1
                total_successes += 1

            total_ms += ms
            total_product_codes += pc_count
            sessions.add(session)

            # Daily count
            ts = event.get("timestamp", "")
            if ts:
                day = ts[:10]  # YYYY-MM-DD
                daily_counts[day] += 1

        # Build command summary
        commands = {}
        for cmd, stats in command_stats.items():
            count = stats["count"]
            commands[cmd] = {
                "count": count,
                "avg_ms": round(stats["total_ms"] / count) if count > 0 else 0,
                "success_rate": round(stats["successes"] / count, 3) if count > 0 else 0.0,
                "product_codes": stats["product_codes"],
            }

        top_commands = sorted(commands.items(), key=lambda x: x[1]["count"], reverse=True)

        return {
            "period_days": days,
            "total_events": len(events),
            "unique_sessions": len(sessions),
            "commands": commands,
            "daily_counts": dict(sorted(daily_counts.items())),
            "top_commands": [(name, info["count"]) for name, info in top_commands[:10]],
            "success_rate": round(total_successes / len(events), 3) if events else 0.0,
            "avg_execution_time_ms": round(total_ms / len(events)) if events else 0,
            "total_product_codes": total_product_codes,
        }

    def print_summary(self, days: int = 30) -> None:
        """Print a formatted usage summary to stdout.

        Args:
            days: Number of days to summarize.
        """
        summary = self.get_summary(days=days)

        print()
        print("=" * 60)
        print(f"FDA Plugin Usage Analytics -- Last {days} Day(s)")
        print("=" * 60)
        print(f"  Total commands:        {summary['total_events']}")
        print(f"  Unique sessions:       {summary['unique_sessions']}")
        print(f"  Overall success rate:  {summary['success_rate']:.1%}")
        print(f"  Avg execution time:    {summary['avg_execution_time_ms']}ms")
        print(f"  Product codes processed: {summary['total_product_codes']}")
        print()

        if summary["top_commands"]:
            print("Top Commands:")
            print(f"  {'Command':<25} {'Count':>6} {'Avg ms':>8} {'Success':>8}")
            print(f"  {'-'*25} {'-'*6} {'-'*8} {'-'*8}")
            for name, count in summary["top_commands"]:
                info = summary["commands"][name]
                print(f"  {name:<25} {count:>6} {info['avg_ms']:>8} {info['success_rate']:>7.0%}")
            print()

        if summary["daily_counts"]:
            print("Daily Activity (last 7 days):")
            sorted_days = sorted(summary["daily_counts"].items(), reverse=True)[:7]
            for day, count in sorted_days:
                bar = "#" * min(count, 40)
                print(f"  {day}: {bar} ({count})")
            print()

        print("=" * 60)

    def clear(self) -> bool:
        """Delete all analytics data.

        Returns:
            True if data was cleared, False if no data existed.
        """
        cleared = False

        if self.usage_file.exists():
            try:
                self.usage_file.unlink()
                cleared = True
            except OSError as e:
                logger.warning("Could not delete usage file: %s", e)

        return cleared

    def export(self) -> List[Dict[str, Any]]:
        """Export all analytics events as a list of dicts.

        Returns:
            All recorded events.
        """
        return self.load_events(days=None)


def main():
    """CLI entry point for usage analytics management."""
    parser = argparse.ArgumentParser(
        description="FDA Plugin Usage Analytics -- Opt-in Local Tracking (FDA-53)"
    )
    parser.add_argument("--enable", action="store_true",
                        help="Enable usage analytics collection")
    parser.add_argument("--disable", action="store_true",
                        help="Disable usage analytics collection")
    parser.add_argument("--status", action="store_true",
                        help="Show current analytics status")
    parser.add_argument("--summary", action="store_true",
                        help="Show usage summary")
    parser.add_argument("--days", type=int, default=30,
                        help="Number of days for summary (default: 30)")
    parser.add_argument("--export", action="store_true",
                        help="Export all analytics as JSON")
    parser.add_argument("--clear", action="store_true",
                        help="Delete all analytics data")
    parser.add_argument("--privacy", action="store_true",
                        help="Show privacy policy")

    args = parser.parse_args()
    analytics = UsageAnalytics()

    if args.privacy:
        print(PRIVACY_POLICY)

    elif args.enable:
        analytics.enable()
        print("Usage analytics ENABLED.")
        print(f"Data will be stored at: {analytics.analytics_dir}")
        print()
        print("Privacy: All data is stored locally. No data is transmitted externally.")
        print("To view the privacy policy: python3 usage_analytics.py --privacy")
        print("To disable: python3 usage_analytics.py --disable")
        print("To delete all data: python3 usage_analytics.py --clear")

    elif args.disable:
        analytics.disable()
        print("Usage analytics DISABLED.")
        print("Existing data is preserved. To delete: python3 usage_analytics.py --clear")

    elif args.status:
        enabled = analytics.is_enabled()
        config = analytics._load_config()
        print()
        print("FDA Plugin Usage Analytics Status")
        print("-" * 40)
        print(f"  Enabled:        {'YES' if enabled else 'NO'}")
        print(f"  Data directory:  {analytics.analytics_dir}")

        if analytics.usage_file.exists():
            size_kb = analytics.usage_file.stat().st_size / 1024
            event_count = len(analytics.load_events())
            print(f"  Events recorded: {event_count}")
            print(f"  Data size:       {size_kb:.1f} KB")
        else:
            print("  Events recorded: 0")
            print("  Data size:       0 KB")

        if enabled and config.get("enabled_at"):
            print(f"  Enabled at:      {config['enabled_at']}")
        if not enabled and config.get("disabled_at"):
            print(f"  Disabled at:     {config['disabled_at']}")
        print()

    elif args.summary:
        if not analytics.is_enabled() and not analytics.usage_file.exists():
            print("Analytics is not enabled. Enable with: python3 usage_analytics.py --enable")
            return
        analytics.print_summary(days=args.days)

    elif args.export:
        events = analytics.export()
        print(json.dumps(events, indent=2))

    elif args.clear:
        cleared = analytics.clear()
        if cleared:
            print("All analytics data has been deleted.")
        else:
            print("No analytics data to delete.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
