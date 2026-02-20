#!/usr/bin/env python3
"""
FDA-192: Blue-Green Deployment Update Coordinator

Zero-downtime database updates using PostgreSQL logical replication and PgBouncer.

Usage:
    python3 update_coordinator.py prepare      # Setup GREEN database replication
    python3 update_coordinator.py refresh      # Detect deltas and update GREEN
    python3 update_coordinator.py switch       # Switch to GREEN (atomic)
    python3 update_coordinator.py rollback     # Rollback to BLUE
    python3 update_coordinator.py status       # Check replication and connection status

Features:
    - PostgreSQL logical replication (BLUE → GREEN)
    - Delta detection via FDA API date filters
    - Integrity verification before switch
    - Atomic PgBouncer config switch via SIGHUP (<10 second RTO)
    - Instant rollback capability
    - 24-hour BLUE standby window
"""

import argparse
import hashlib
import hmac
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from fda_tools.lib.postgres_database import PostgreSQLDatabase
    _POSTGRES_AVAILABLE = True
except ImportError:
    _POSTGRES_AVAILABLE = False
    print("ERROR: PostgreSQLDatabase module not available")
    sys.exit(1)

try:
    from fda_tools.scripts.fda_api_client import FDAClient
    _API_CLIENT_AVAILABLE = True
except ImportError:
    _API_CLIENT_AVAILABLE = False
    print("ERROR: FDAClient module not available")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
BLUE_PORT = 5432
GREEN_PORT = 5433
PGBOUNCER_PORT = 6432
PGBOUNCER_CONTAINER = "fda_pgbouncer"
REPLICATION_TIMEOUT = 300  # 5 minutes
REPLICATION_CHECK_INTERVAL = 5  # seconds
SWITCH_TIMEOUT = 30  # seconds
STANDBY_WINDOW_HOURS = 24

ENDPOINTS = ["510k", "classification", "maude", "recalls", "pma", "udi", "enforcement"]


class UpdateCoordinatorError(Exception):
    """Base exception for update coordinator errors."""
    pass


class ReplicationError(UpdateCoordinatorError):
    """Replication setup or sync failed."""
    pass


class VerificationError(UpdateCoordinatorError):
    """Integrity verification failed."""
    pass


class SwitchError(UpdateCoordinatorError):
    """PgBouncer switch failed."""
    pass


class UpdateCoordinator:
    """Zero-downtime database update coordinator using blue-green deployment.
    
    Manages PostgreSQL logical replication, delta detection, integrity verification,
    and atomic PgBouncer switching with rollback capability.
    """
    
    def __init__(
        self,
        blue_host: str = "localhost",
        blue_port: int = BLUE_PORT,
        green_host: str = "localhost",
        green_port: int = GREEN_PORT,
        pgbouncer_host: str = "localhost",
        pgbouncer_port: int = PGBOUNCER_PORT
    ):
        """Initialize update coordinator.
        
        Args:
            blue_host: BLUE database host
            blue_port: BLUE database port
            green_host: GREEN database host
            green_port: GREEN database port
            pgbouncer_host: PgBouncer host
            pgbouncer_port: PgBouncer port
        """
        self.blue_host = blue_host
        self.blue_port = blue_port
        self.green_host = green_host
        self.green_port = green_port
        self.pgbouncer_host = pgbouncer_host
        self.pgbouncer_port = pgbouncer_port
        
        # Initialize database connections
        self.blue_db = PostgreSQLDatabase(host=blue_host, port=blue_port, pool_size=5)
        self.green_db = None  # Initialized when needed
        
        # Initialize FDA API client for delta detection
        self.api_client = FDAClient()
        
        # Track switch state
        self.state_file = Path.home() / ".fda-tools" / "blue_green_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_state(self) -> Dict:
        """Load blue-green state from file."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {
            "active_db": "blue",
            "last_switch": None,
            "last_refresh": {},
            "standby_expires": None
        }
    
    def _save_state(self, state: Dict):
        """Save blue-green state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def prepare_green_database(self) -> bool:
        """Setup logical replication from BLUE to GREEN.
        
        Returns:
            True if successful, False otherwise
            
        Raises:
            ReplicationError: If setup fails
        """
        logger.info("Preparing GREEN database with logical replication from BLUE...")
        
        # Step 1: Start GREEN container
        logger.info("Starting GREEN PostgreSQL container...")
        try:
            subprocess.run(
                ["docker-compose", "--profile", "blue-green", "up", "-d", "postgres-green"],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise ReplicationError(f"Failed to start GREEN container: {e.stderr}")
        
        # Wait for GREEN to be healthy
        logger.info("Waiting for GREEN database to be healthy...")
        time.sleep(10)
        
        # Step 2: Initialize GREEN database connection
        self.green_db = PostgreSQLDatabase(host=self.green_host, port=self.green_port, pool_size=5)
        
        # Step 3: Create publication on BLUE
        logger.info("Creating publication on BLUE database...")
        with self.blue_db.get_connection() as conn:
            with conn.cursor() as cur:
                # Drop existing publication if exists
                cur.execute("DROP PUBLICATION IF EXISTS blue_pub")
                # Create new publication for all tables
                cur.execute("CREATE PUBLICATION blue_pub FOR ALL TABLES")
                conn.commit()
        
        # Step 4: Create subscription on GREEN
        logger.info("Creating subscription on GREEN database...")
        connection_string = f"host={self.blue_host} port={self.blue_port} dbname=fda_offline user=fda_user password=fda_password"
        
        with self.green_db.get_connection() as conn:
            with conn.cursor() as cur:
                # Drop existing subscription if exists
                cur.execute("DROP SUBSCRIPTION IF EXISTS green_sub")
                # Create new subscription
                cur.execute(
                    f"CREATE SUBSCRIPTION green_sub "
                    f"CONNECTION '{connection_string}' "
                    f"PUBLICATION blue_pub"
                )
                conn.commit()
        
        # Step 5: Wait for initial sync
        logger.info("Waiting for initial replication sync...")
        sync_complete = self._wait_for_sync(timeout=REPLICATION_TIMEOUT)
        
        if not sync_complete:
            raise ReplicationError("Replication sync timeout - GREEN not ready")
        
        logger.info("✅ GREEN database prepared successfully")
        return True
    
    def _wait_for_sync(self, timeout: int = 300) -> bool:
        """Wait for replication sync to complete.
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            True if sync complete, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self.blue_db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT state FROM pg_stat_replication WHERE application_name = 'green_sub'")
                    result = cur.fetchone()
                    
                    if result and result[0] == 'streaming':
                        logger.info("Replication sync complete (streaming)")
                        return True
            
            logger.debug(f"Waiting for sync... ({int(time.time() - start_time)}s)")
            time.sleep(REPLICATION_CHECK_INTERVAL)
        
        return False
    
    def detect_deltas(self, endpoint: str, since_timestamp: Optional[float] = None) -> List[str]:
        """Find records modified since timestamp using FDA API.
        
        Args:
            endpoint: Endpoint name (510k, classification, etc.)
            since_timestamp: Unix timestamp of last refresh (None = all records)
            
        Returns:
            List of modified record IDs
        """
        logger.info(f"Detecting deltas for {endpoint} since {since_timestamp}...")
        
        if since_timestamp is None:
            # No previous refresh, return empty (use full migration instead)
            logger.info("No previous refresh timestamp, skipping delta detection")
            return []
        
        # Convert timestamp to date string for FDA API
        since_date = datetime.fromtimestamp(since_timestamp).strftime("%Y%m%d")
        now_date = datetime.now().strftime("%Y%m%d")
        
        # Query FDA API with date range filter
        # Example: decision_date:[20260101+TO+20260220]
        date_filter = f"[{since_date}+TO+{now_date}]"
        
        # Build search parameter based on endpoint
        if endpoint == "510k":
            search_param = f"decision_date:{date_filter}"
        elif endpoint in ["maude", "recalls", "enforcement"]:
            search_param = f"date_received:{date_filter}"
        elif endpoint == "pma":
            search_param = f"decision_date:{date_filter}"
        else:
            # classification, udi don't have date filters
            logger.warning(f"Endpoint {endpoint} doesn't support date filtering")
            return []
        
        # Fetch records (limit to 1000 for safety)
        logger.info(f"Querying FDA API: {search_param}")
        response = self.api_client._request(endpoint, {"search": search_param, "limit": "1000"})
        
        if not response or "error" in response:
            logger.error(f"FDA API query failed: {response}")
            return []
        
        results = response.get("results", [])
        logger.info(f"Found {len(results)} modified records")
        
        # Extract record IDs
        id_fields = {
            "510k": "k_number",
            "classification": "product_code",
            "maude": "event_key",
            "recalls": "recall_number",
            "pma": "pma_number",
            "udi": "di",
            "enforcement": "recall_number"
        }
        
        id_field = id_fields.get(endpoint)
        if not id_field:
            return []
        
        record_ids = [r.get(id_field) for r in results if r.get(id_field)]
        logger.info(f"Extracted {len(record_ids)} record IDs")
        
        return record_ids
    
    def apply_updates(self, endpoint: str, record_ids: List[str]) -> int:
        """Update GREEN database with modified records.
        
        Args:
            endpoint: Endpoint name
            record_ids: List of record IDs to update
            
        Returns:
            Number of records updated
        """
        if not record_ids:
            logger.info(f"No updates to apply for {endpoint}")
            return 0
        
        logger.info(f"Applying {len(record_ids)} updates to GREEN database for {endpoint}...")
        
        updated_count = 0
        
        for record_id in record_ids:
            # Fetch from API
            response = self.api_client._request(endpoint, {"search": f'{id_fields[endpoint]}:"{record_id}"', "limit": "1"})
            
            if not response or "error" in response or not response.get("results"):
                logger.warning(f"Failed to fetch {endpoint} {record_id}")
                continue
            
            data = response["results"][0]
            
            # Upsert into GREEN database
            try:
                self.green_db.upsert_record(endpoint, record_id, data)
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to upsert {endpoint} {record_id}: {e}")
        
        logger.info(f"✅ Applied {updated_count}/{len(record_ids)} updates to GREEN")
        return updated_count
    
    def verify_integrity(self) -> Tuple[bool, Dict]:
        """Verify GREEN database integrity before switch.
        
        Returns:
            Tuple of (pass/fail, verification report dict)
        """
        logger.info("Verifying GREEN database integrity...")
        
        report = {
            "row_counts": {},
            "replication_lag": None,
            "overall_pass": True
        }
        
        # Check row counts for each endpoint
        for endpoint in ENDPOINTS:
            with self.blue_db.get_connection() as blue_conn:
                with blue_conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM fda_{endpoint}")
                    blue_count = cur.fetchone()[0]
            
            with self.green_db.get_connection() as green_conn:
                with green_conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM fda_{endpoint}")
                    green_count = cur.fetchone()[0]
            
            match = (blue_count == green_count)
            report["row_counts"][endpoint] = {
                "blue": blue_count,
                "green": green_count,
                "match": match
            }
            
            if not match:
                logger.error(f"Row count mismatch for {endpoint}: BLUE={blue_count}, GREEN={green_count}")
                report["overall_pass"] = False
        
        # Check replication lag
        with self.blue_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT EXTRACT(EPOCH FROM (NOW() - replay_lag)) "
                    "FROM pg_stat_replication "
                    "WHERE application_name = 'green_sub'"
                )
                result = cur.fetchone()
                if result:
                    report["replication_lag"] = result[0]
                    if result[0] > 60:  # More than 1 minute lag
                        logger.warning(f"High replication lag: {result[0]:.1f} seconds")
                        report["overall_pass"] = False
        
        if report["overall_pass"]:
            logger.info("✅ Integrity verification passed")
        else:
            logger.error("❌ Integrity verification failed")
        
        return report["overall_pass"], report
    
    def switch_to_green(self) -> bool:
        """Switch PgBouncer from BLUE to GREEN with zero downtime.
        
        Returns:
            True if successful, False otherwise
            
        Raises:
            SwitchError: If switch fails
        """
        logger.info("Switching PgBouncer to GREEN database...")
        
        # Verify integrity first
        passed, report = self.verify_integrity()
        if not passed:
            raise SwitchError(f"Integrity verification failed: {report}")
        
        # Update PgBouncer config
        self._update_pgbouncer_config(GREEN_PORT)
        
        # Send SIGHUP to reload
        self._reload_pgbouncer()
        
        # Update state
        state = self._load_state()
        state["active_db"] = "green"
        state["last_switch"] = datetime.now().isoformat()
        state["standby_expires"] = (datetime.now() + timedelta(hours=STANDBY_WINDOW_HOURS)).isoformat()
        self._save_state(state)
        
        logger.info("✅ Successfully switched to GREEN database")
        return True
    
    def rollback_to_blue(self) -> bool:
        """Instant rollback to BLUE database.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Rolling back to BLUE database...")
        
        # Update PgBouncer config
        self._update_pgbouncer_config(BLUE_PORT)
        
        # Send SIGHUP to reload
        self._reload_pgbouncer()
        
        # Update state
        state = self._load_state()
        state["active_db"] = "blue"
        state["last_switch"] = datetime.now().isoformat()
        self._save_state(state)
        
        logger.info("✅ Successfully rolled back to BLUE database")
        return True
    
    def _update_pgbouncer_config(self, port: int):
        """Update PgBouncer config to point to specified port.
        
        Args:
            port: Database port (5432 for BLUE, 5433 for GREEN)
        """
        # Read current config from container
        try:
            result = subprocess.run(
                ["docker", "exec", PGBOUNCER_CONTAINER, "cat", "/etc/pgbouncer/pgbouncer.ini"],
                capture_output=True,
                text=True,
                check=True
            )
            config = result.stdout
        except subprocess.CalledProcessError as e:
            raise SwitchError(f"Failed to read PgBouncer config: {e.stderr}")
        
        # Update port in [databases] section
        lines = config.split('\n')
        updated_lines = []
        for line in lines:
            if line.startswith('fda_offline = '):
                # Replace port number
                updated_line = f"fda_offline = host=localhost port={port} dbname=fda_offline"
                updated_lines.append(updated_line)
                logger.debug(f"Updated config line: {updated_line}")
            else:
                updated_lines.append(line)
        
        updated_config = '\n'.join(updated_lines)
        
        # Write updated config back to container
        try:
            subprocess.run(
                ["docker", "exec", "-i", PGBOUNCER_CONTAINER, "sh", "-c", "cat > /etc/pgbouncer/pgbouncer.ini"],
                input=updated_config,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise SwitchError(f"Failed to write PgBouncer config: {e}")
    
    def _reload_pgbouncer(self):
        """Send SIGHUP to PgBouncer for hot reload."""
        logger.info("Reloading PgBouncer configuration...")
        try:
            subprocess.run(
                ["docker", "kill", "-s", "SIGHUP", PGBOUNCER_CONTAINER],
                check=True,
                capture_output=True
            )
            logger.info("PgBouncer reload signal sent")
            time.sleep(2)  # Wait for reload
        except subprocess.CalledProcessError as e:
            raise SwitchError(f"Failed to reload PgBouncer: {e.stderr}")
    
    def get_status(self) -> Dict:
        """Get current blue-green deployment status.
        
        Returns:
            Status dict with active_db, replication state, etc.
        """
        state = self._load_state()
        
        # Check replication status
        replication_status = None
        with self.blue_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT state FROM pg_stat_replication WHERE application_name = 'green_sub'")
                result = cur.fetchone()
                if result:
                    replication_status = result[0]
        
        return {
            "active_db": state.get("active_db", "blue"),
            "last_switch": state.get("last_switch"),
            "standby_expires": state.get("standby_expires"),
            "replication_status": replication_status
        }
    
    def close(self):
        """Close database connections."""
        if self.blue_db:
            self.blue_db.close()
        if self.green_db:
            self.green_db.close()


def main():
    """CLI for update coordinator."""
    parser = argparse.ArgumentParser(description="Blue-Green Deployment Update Coordinator")
    parser.add_argument(
        "command",
        choices=["prepare", "refresh", "switch", "rollback", "status"],
        help="Command to execute"
    )
    parser.add_argument(
        "--endpoint",
        choices=ENDPOINTS,
        help="Endpoint to refresh (for 'refresh' command)"
    )
    
    args = parser.parse_args()
    
    coordinator = UpdateCoordinator()
    
    try:
        if args.command == "prepare":
            coordinator.prepare_green_database()
        
        elif args.command == "refresh":
            if not args.endpoint:
                print("ERROR: --endpoint required for refresh command")
                return 1
            
            state = coordinator._load_state()
            last_refresh = state.get("last_refresh", {}).get(args.endpoint)
            
            deltas = coordinator.detect_deltas(args.endpoint, last_refresh)
            updated = coordinator.apply_updates(args.endpoint, deltas)
            
            # Update last refresh timestamp
            state["last_refresh"][args.endpoint] = time.time()
            coordinator._save_state(state)
            
            print(f"✅ Refreshed {args.endpoint}: {updated} records updated")
        
        elif args.command == "switch":
            coordinator.switch_to_green()
        
        elif args.command == "rollback":
            coordinator.rollback_to_blue()
        
        elif args.command == "status":
            status = coordinator.get_status()
            print(json.dumps(status, indent=2))
        
        return 0
    
    except (ReplicationError, VerificationError, SwitchError) as e:
        logger.error(f"Command failed: {e}")
        return 1
    except KeyboardInterrupt:
        logger.warning("Command interrupted by user")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1
    finally:
        coordinator.close()


if __name__ == "__main__":
    sys.exit(main())
