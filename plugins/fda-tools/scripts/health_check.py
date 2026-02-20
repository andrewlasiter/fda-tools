#!/usr/bin/env python3
"""Health check script for FDA Tools Docker container.

This script performs comprehensive health checks to ensure the container
is functioning properly. Exit code 0 indicates healthy, non-zero indicates unhealthy.

Health checks:
1. Python environment validation
2. Core dependencies availability
3. File system accessibility
4. Configuration validation
5. Optional: Database connectivity
6. Optional: Redis connectivity

Usage:
    python health_check.py
    python health_check.py --verbose
    python health_check.py --skip-network

Exit codes:
    0: Healthy
    1: Unhealthy (generic failure)
    2: Configuration error
    3: Dependency error
    4: Network error
"""

import sys
import os
import logging
from pathlib import Path
from typing import Tuple, List
import argparse


class HealthChecker:
    """Comprehensive health checker for FDA Tools container."""

    def __init__(self, verbose: bool = False, skip_network: bool = False):
        """Initialize health checker.

        Args:
            verbose: Enable verbose logging
            skip_network: Skip network-based checks (database, Redis)
        """
        self.verbose = verbose
        self.skip_network = skip_network
        self.issues: List[str] = []

        # Configure logging
        log_level = logging.DEBUG if verbose else logging.WARNING
        logging.basicConfig(
            level=log_level,
            format='%(levelname)s: %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def check_python_environment(self) -> bool:
        """Check Python environment and version."""
        try:
            version = sys.version_info
            if version.major < 3 or (version.major == 3 and version.minor < 9):
                self.issues.append(f"Python version {version.major}.{version.minor} is too old")
                return False
            self.logger.debug(f"Python version: {version.major}.{version.minor}.{version.micro}")
            return True
        except Exception as e:
            self.issues.append(f"Python environment check failed: {e}")
            return False

    def check_core_dependencies(self) -> bool:
        """Check core Python dependencies are importable."""
        required_modules = [
            'requests',
            'pandas',
            'numpy',
            'jinja2',
            'bs4',  # beautifulsoup4
            'lxml',
            'fitz',  # PyMuPDF
            'keyring',
            'tenacity',
        ]

        all_available = True
        for module in required_modules:
            try:
                __import__(module)
                self.logger.debug(f"✓ Module '{module}' available")
            except ImportError as e:
                self.issues.append(f"Required module '{module}' not available: {e}")
                all_available = False

        return all_available

    def check_file_system(self) -> bool:
        """Check file system directories are accessible."""
        required_dirs = [
            os.getenv('FDA_DATA_DIR', '/data'),
            os.getenv('FDA_CACHE_DIR', '/cache'),
            os.getenv('FDA_LOG_DIR', '/logs'),
        ]

        all_accessible = True
        for dir_path in required_dirs:
            path = Path(dir_path)
            try:
                # Check if directory exists and is writable
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                    self.logger.debug(f"Created directory: {dir_path}")

                # Test write access
                test_file = path / '.health_check'
                test_file.touch()
                test_file.unlink()
                self.logger.debug(f"✓ Directory accessible: {dir_path}")

            except Exception as e:
                self.issues.append(f"Directory '{dir_path}' not accessible: {e}")
                all_accessible = False

        return all_accessible

    def check_configuration(self) -> bool:
        """Check configuration file exists and is valid."""
        config_file = os.getenv('FDA_CONFIG_FILE', '/app/plugins/fda-tools/config.toml')
        config_path = Path(config_file)

        try:
            if not config_path.exists():
                self.issues.append(f"Configuration file not found: {config_file}")
                return False

            # Try to parse TOML (basic validation)
            try:
                import tomli
                with open(config_path, 'rb') as f:
                    tomli.load(f)
                self.logger.debug(f"✓ Configuration valid: {config_file}")
            except ImportError:
                # tomli not available, just check file is readable
                with open(config_path, 'r') as f:
                    content = f.read()
                    if len(content) < 10:
                        self.issues.append(f"Configuration file appears empty: {config_file}")
                        return False
                self.logger.debug(f"✓ Configuration readable: {config_file}")

            return True

        except Exception as e:
            self.issues.append(f"Configuration check failed: {e}")
            return False

    def check_database_connection(self) -> bool:
        """Check database connectivity (if configured)."""
        if self.skip_network:
            self.logger.debug("Skipping database check (--skip-network)")
            return True

        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            self.logger.debug("Database not configured, skipping")
            return True

        try:
            import psycopg2
            conn = psycopg2.connect(database_url, connect_timeout=5)
            conn.close()
            self.logger.debug("✓ Database connection successful")
            return True
        except ImportError:
            self.logger.debug("psycopg2 not installed, skipping database check")
            return True
        except Exception as e:
            self.issues.append(f"Database connection failed: {e}")
            return False

    def check_redis_connection(self) -> bool:
        """Check Redis connectivity (if configured)."""
        if self.skip_network:
            self.logger.debug("Skipping Redis check (--skip-network)")
            return True

        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            self.logger.debug("Redis not configured, skipping")
            return True

        try:
            import redis
            r = redis.from_url(redis_url, socket_connect_timeout=5)
            r.ping()
            self.logger.debug("✓ Redis connection successful")
            return True
        except ImportError:
            self.logger.debug("redis not installed, skipping Redis check")
            return True
        except Exception as e:
            self.issues.append(f"Redis connection failed: {e}")
            return False

    def check_fda_tools_importable(self) -> bool:
        """Check FDA tools package is importable."""
        try:
            # Try to import core modules
            sys.path.insert(0, '/app')
            from lib import config
            from lib import auth
            self.logger.debug("✓ FDA tools package importable")
            return True
        except Exception as e:
            self.issues.append(f"FDA tools package import failed: {e}")
            return False

    def run_all_checks(self) -> Tuple[bool, List[str]]:
        """Run all health checks.

        Returns:
            Tuple of (is_healthy, list_of_issues)
        """
        checks = [
            ("Python environment", self.check_python_environment),
            ("Core dependencies", self.check_core_dependencies),
            ("File system", self.check_file_system),
            ("Configuration", self.check_configuration),
            ("FDA tools import", self.check_fda_tools_importable),
            ("Database connection", self.check_database_connection),
            ("Redis connection", self.check_redis_connection),
        ]

        all_passed = True
        for check_name, check_func in checks:
            try:
                result = check_func()
                if result:
                    self.logger.info(f"✓ {check_name}: PASS")
                else:
                    self.logger.error(f"✗ {check_name}: FAIL")
                    all_passed = False
            except Exception as e:
                self.logger.error(f"✗ {check_name}: ERROR - {e}")
                self.issues.append(f"{check_name} raised exception: {e}")
                all_passed = False

        return all_passed, self.issues


def main() -> int:
    """Main health check entry point.

    Returns:
        Exit code (0 = healthy, non-zero = unhealthy)
    """
    parser = argparse.ArgumentParser(
        description='FDA Tools container health check'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--skip-network',
        action='store_true',
        help='Skip network-based checks (database, Redis)'
    )

    args = parser.parse_args()

    checker = HealthChecker(verbose=args.verbose, skip_network=args.skip_network)
    is_healthy, issues = checker.run_all_checks()

    if is_healthy:
        print("✓ Container is healthy")
        return 0
    else:
        print("✗ Container is unhealthy")
        print("\nIssues found:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
