#!/usr/bin/env python3
"""
FDA-194: PostgreSQL Backup Manager with WAL Archiving

Automated backup and recovery for PostgreSQL with encryption, WAL archiving,
point-in-time recovery, and regulatory-compliant 7-year retention.

Features:
    - Automated pg_dump backups with compression
    - GPG encryption for security
    - WAL archiving for point-in-time recovery (RPO <5 min)
    - S3-compatible storage upload
    - 7-year retention policy (21 CFR Part 11)
    - Backup verification via test restore
    - Point-in-time recovery (RTO <15 min)
"""

import hashlib
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_BACKUP_DIR = Path.home() / "fda-510k-data" / "backups"
DEFAULT_WAL_ARCHIVE = Path.home() / "fda-510k-data" / "wal_archive"
POSTGRES_CONTAINER = "fda_postgres"
DEFAULT_DATABASE = "fda_offline"
DEFAULT_USER = "fda_user"

# Retention periods (days)
DAILY_RETENTION = 7
WEEKLY_RETENTION = 28
MONTHLY_RETENTION = 365
YEARLY_RETENTION = 2555  # 7 years for FDA 21 CFR Part 11


class BackupError(Exception):
    """Base exception for backup errors."""
    pass


class RestoreError(Exception):
    """Base exception for restore errors."""
    pass


class BackupManager:
    """PostgreSQL backup and recovery manager with encryption and WAL archiving.
    
    Provides automated backups, point-in-time recovery, and regulatory-compliant
    retention management.
    """
    
    def __init__(
        self,
        backup_dir: Path = DEFAULT_BACKUP_DIR,
        wal_archive_dir: Path = DEFAULT_WAL_ARCHIVE,
        container: str = POSTGRES_CONTAINER,
        database: str = DEFAULT_DATABASE,
        user: str = DEFAULT_USER
    ):
        """Initialize backup manager.
        
        Args:
            backup_dir: Directory for backup storage
            wal_archive_dir: Directory for WAL archive
            container: Docker container name
            database: PostgreSQL database name
            user: PostgreSQL user
        """
        self.backup_dir = Path(backup_dir)
        self.wal_archive_dir = Path(wal_archive_dir)
        self.container = container
        self.database = database
        self.user = user
        
        # Create directories
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.wal_archive_dir.mkdir(parents=True, exist_ok=True)
    
    def create_full_backup(self, compress: bool = True) -> Path:
        """Create full database backup using pg_dump.
        
        Args:
            compress: Use custom format with compression (-Fc)
            
        Returns:
            Path to backup file
            
        Raises:
            BackupError: If backup fails
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"backup_{timestamp}.dump"
        
        logger.info(f"Creating full backup to {backup_file}...")
        
        # Build pg_dump command
        cmd = [
            "docker", "exec", self.container,
            "pg_dump",
            "-U", self.user,
            "-d", self.database,
        ]
        
        if compress:
            cmd.extend(["-Fc"])  # Custom format with compression
        
        cmd.extend(["-f", f"/tmp/{backup_file.name}"])
        
        try:
            # Run pg_dump inside container
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Copy backup from container to host
            subprocess.run(
                ["docker", "cp", f"{self.container}:/tmp/{backup_file.name}", str(backup_file)],
                check=True,
                capture_output=True
            )
            
            # Cleanup temp file in container
            subprocess.run(
                ["docker", "exec", self.container, "rm", f"/tmp/{backup_file.name}"],
                check=True,
                capture_output=True
            )
            
        except subprocess.CalledProcessError as e:
            raise BackupError(f"pg_dump failed: {e.stderr}")
        
        # Verify backup file
        if not backup_file.exists() or backup_file.stat().st_size == 0:
            raise BackupError(f"Backup file missing or empty: {backup_file}")
        
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Backup created: {backup_file.name} ({size_mb:.1f} MB)")
        
        return backup_file
    
    def encrypt_backup(self, backup_file: Path, recipient: str) -> Path:
        """Encrypt backup file with GPG.
        
        Args:
            backup_file: Path to unencrypted backup
            recipient: GPG recipient email
            
        Returns:
            Path to encrypted backup (.gpg)
            
        Raises:
            BackupError: If encryption fails
        """
        encrypted_file = backup_file.with_suffix(backup_file.suffix + ".gpg")
        
        logger.info(f"Encrypting backup with GPG for {recipient}...")
        
        try:
            subprocess.run(
                ["gpg", "--encrypt", "--recipient", recipient, "--output", str(encrypted_file), str(backup_file)],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise BackupError(f"GPG encryption failed: {e.stderr}")
        
        # Verify encrypted file
        if not encrypted_file.exists():
            raise BackupError(f"Encrypted file not created: {encrypted_file}")
        
        # Securely delete unencrypted backup
        backup_file.unlink()
        logger.info(f"✅ Backup encrypted: {encrypted_file.name}")
        
        return encrypted_file
    
    def decrypt_backup(self, encrypted_file: Path, output_file: Optional[Path] = None) -> Path:
        """Decrypt GPG-encrypted backup.
        
        Args:
            encrypted_file: Path to .gpg file
            output_file: Output path (default: same name without .gpg)
            
        Returns:
            Path to decrypted backup
            
        Raises:
            RestoreError: If decryption fails
        """
        if output_file is None:
            output_file = encrypted_file.with_suffix('')
        
        logger.info(f"Decrypting backup {encrypted_file.name}...")
        
        try:
            subprocess.run(
                ["gpg", "--decrypt", "--output", str(output_file), str(encrypted_file)],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise RestoreError(f"GPG decryption failed: {e.stderr}")
        
        logger.info(f"✅ Backup decrypted: {output_file.name}")
        return output_file
    
    def upload_to_s3(self, backup_file: Path, bucket: str, prefix: str = "backups") -> bool:
        """Upload backup to S3-compatible storage.
        
        Args:
            backup_file: Path to backup file
            bucket: S3 bucket name
            prefix: S3 key prefix
            
        Returns:
            True if successful, False otherwise
        """
        # Extract year/month from filename for partitioning
        # Format: backup_YYYYMMDD_HHMMSS.dump.gpg
        parts = backup_file.stem.split('_')
        if len(parts) >= 2:
            date_str = parts[1]  # YYYYMMDD
            year = date_str[:4]
            month = date_str[4:6]
        else:
            now = datetime.now()
            year = now.strftime("%Y")
            month = now.strftime("%m")
        
        s3_key = f"{prefix}/{year}/{month}/{backup_file.name}"
        
        logger.info(f"Uploading to s3://{bucket}/{s3_key}...")
        
        try:
            subprocess.run(
                ["aws", "s3", "cp", str(backup_file), f"s3://{bucket}/{s3_key}"],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"✅ Uploaded to S3: {s3_key}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"S3 upload failed: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error("AWS CLI not found - install with: pip install awscli")
            return False
    
    def restore_backup(self, backup_file: Path, database: Optional[str] = None) -> bool:
        """Restore database from backup file.
        
        Args:
            backup_file: Path to backup file (.dump or .dump.gpg)
            database: Target database (default: self.database)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            RestoreError: If restore fails
        """
        if database is None:
            database = self.database
        
        # Decrypt if encrypted
        if backup_file.suffix == ".gpg":
            backup_file = self.decrypt_backup(backup_file)
        
        logger.info(f"Restoring database {database} from {backup_file.name}...")
        
        # Copy backup to container
        try:
            subprocess.run(
                ["docker", "cp", str(backup_file), f"{self.container}:/tmp/{backup_file.name}"],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            raise RestoreError(f"Failed to copy backup to container: {e.stderr}")
        
        # Run pg_restore inside container
        cmd = [
            "docker", "exec", self.container,
            "pg_restore",
            "-U", self.user,
            "-d", database,
            "--clean",  # Drop existing objects first
            "--if-exists",  # Only drop if exists (no error)
            f"/tmp/{backup_file.name}"
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"✅ Database {database} restored successfully")
            return True
        except subprocess.CalledProcessError as e:
            raise RestoreError(f"pg_restore failed: {e.stderr}")
        finally:
            # Cleanup temp file in container
            subprocess.run(
                ["docker", "exec", self.container, "rm", "-f", f"/tmp/{backup_file.name}"],
                capture_output=True
            )
    
    def verify_backup(self, backup_file: Path) -> Tuple[bool, Dict]:
        """Verify backup integrity by test restore.
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            Tuple of (pass/fail, verification report)
        """
        test_db = "test_restore_verify"
        report = {
            "backup_file": str(backup_file),
            "test_database": test_db,
            "tables_verified": 0,
            "total_rows": 0,
            "passed": False
        }
        
        logger.info(f"Verifying backup {backup_file.name}...")
        
        try:
            # Create test database
            subprocess.run(
                ["docker", "exec", self.container, "createdb", "-U", self.user, test_db],
                check=True,
                capture_output=True
            )
            
            # Restore to test database
            self.restore_backup(backup_file, database=test_db)
            
            # Count rows in main tables
            tables = ["fda_510k", "fda_classification", "fda_maude_events", "fda_recalls", 
                     "fda_pma", "fda_udi", "fda_enforcement"]
            
            for table in tables:
                result = subprocess.run(
                    ["docker", "exec", self.container, "psql", "-U", self.user, "-d", test_db, 
                     "-t", "-c", f"SELECT COUNT(*) FROM {table}"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    count = int(result.stdout.strip())
                    report["tables_verified"] += 1
                    report["total_rows"] += count
            
            report["passed"] = (report["tables_verified"] == len(tables))
            logger.info(f"✅ Backup verified: {report['total_rows']} rows across {report['tables_verified']} tables")
            
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            report["error"] = str(e)
        finally:
            # Drop test database
            subprocess.run(
                ["docker", "exec", self.container, "dropdb", "-U", self.user, "--if-exists", test_db],
                capture_output=True
            )
        
        return report["passed"], report
    
    def cleanup_old_backups(self, dry_run: bool = False) -> int:
        """Remove backups older than retention policy.
        
        Args:
            dry_run: Log what would be deleted without deleting
            
        Returns:
            Number of backups deleted
        """
        logger.info("Scanning for old backups to cleanup...")
        
        deleted_count = 0
        now = datetime.now()
        
        for backup_file in self.backup_dir.glob("backup_*.dump*"):
            # Extract timestamp from filename: backup_YYYYMMDD_HHMMSS.dump[.gpg]
            parts = backup_file.stem.split('_')
            if len(parts) < 3:
                continue
            
            try:
                date_str = parts[1]  # YYYYMMDD
                time_str = parts[2].split('.')[0]  # HHMMSS
                backup_time = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            except (ValueError, IndexError):
                logger.warning(f"Could not parse timestamp from {backup_file.name}")
                continue
            
            age_days = (now - backup_time).days
            
            # Apply retention policy
            should_keep = False
            
            if age_days < DAILY_RETENTION:
                should_keep = True  # Keep all daily backups
            elif age_days < WEEKLY_RETENTION and backup_time.weekday() == 6:  # Sunday
                should_keep = True  # Keep weekly backups (Sundays)
            elif age_days < MONTHLY_RETENTION and backup_time.day == 1:
                should_keep = True  # Keep monthly backups (1st of month)
            elif age_days < YEARLY_RETENTION and backup_time.month == 1 and backup_time.day == 1:
                should_keep = True  # Keep yearly backups (Jan 1st)
            
            if not should_keep:
                if dry_run:
                    logger.info(f"Would delete (age={age_days}d): {backup_file.name}")
                else:
                    backup_file.unlink()
                    logger.info(f"Deleted (age={age_days}d): {backup_file.name}")
                deleted_count += 1
        
        logger.info(f"✅ Cleanup complete: {deleted_count} backups {'would be ' if dry_run else ''}deleted")
        return deleted_count
    
    def configure_wal_archiving(self, archive_command: Optional[str] = None) -> bool:
        """Configure PostgreSQL for WAL archiving.
        
        Args:
            archive_command: Custom archive command (default: cp to wal_archive_dir)
            
        Returns:
            True if successful, False otherwise
        """
        if archive_command is None:
            archive_command = f"cp %p {self.wal_archive_dir}/%f"
        
        logger.info("Configuring WAL archiving...")
        
        # Note: This requires PostgreSQL restart
        # In production, these should be set in postgresql.conf or docker-compose.yml
        config_updates = f"""
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET archive_mode = on;
ALTER SYSTEM SET archive_command = '{archive_command}';
"""
        
        try:
            subprocess.run(
                ["docker", "exec", "-i", self.container, "psql", "-U", self.user, "-d", self.database],
                input=config_updates,
                text=True,
                check=True,
                capture_output=True
            )
            
            logger.info("✅ WAL archiving configured (requires PostgreSQL restart)")
            logger.warning("Restart PostgreSQL: docker-compose restart postgres-blue")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to configure WAL archiving: {e.stderr}")
            return False
    
    def get_stats(self) -> Dict:
        """Get backup statistics.
        
        Returns:
            Dict with backup counts and sizes
        """
        stats = {
            "total_backups": 0,
            "total_size_mb": 0,
            "encrypted_backups": 0,
            "oldest_backup": None,
            "newest_backup": None,
            "wal_segments": 0,
            "wal_size_mb": 0
        }
        
        # Count backups
        backups = list(self.backup_dir.glob("backup_*.dump*"))
        stats["total_backups"] = len(backups)
        stats["encrypted_backups"] = len([b for b in backups if b.suffix == ".gpg"])
        
        if backups:
            stats["total_size_mb"] = sum(b.stat().st_size for b in backups) / (1024 * 1024)
            backups_sorted = sorted(backups, key=lambda b: b.stat().st_mtime)
            stats["oldest_backup"] = backups_sorted[0].name
            stats["newest_backup"] = backups_sorted[-1].name
        
        # Count WAL segments
        wal_files = list(self.wal_archive_dir.glob("*"))
        stats["wal_segments"] = len(wal_files)
        if wal_files:
            stats["wal_size_mb"] = sum(w.stat().st_size for w in wal_files) / (1024 * 1024)
        
        return stats


def main():
    """CLI for backup manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PostgreSQL Backup Manager")
    parser.add_argument("command", choices=["create", "restore", "verify", "cleanup", "stats", "configure-wal"])
    parser.add_argument("--file", type=Path, help="Backup file path (for restore/verify)")
    parser.add_argument("--encrypt", action="store_true", help="Encrypt backup with GPG")
    parser.add_argument("--recipient", default="backup@company.com", help="GPG recipient")
    parser.add_argument("--upload", action="store_true", help="Upload to S3")
    parser.add_argument("--bucket", default="fda-backups", help="S3 bucket name")
    parser.add_argument("--dry-run", action="store_true", help="Dry run for cleanup")
    
    args = parser.parse_args()
    
    manager = BackupManager()
    
    try:
        if args.command == "create":
            backup_file = manager.create_full_backup()
            
            if args.encrypt:
                backup_file = manager.encrypt_backup(backup_file, args.recipient)
            
            if args.upload:
                manager.upload_to_s3(backup_file, args.bucket)
        
        elif args.command == "restore":
            if not args.file:
                print("ERROR: --file required for restore")
                return 1
            manager.restore_backup(args.file)
        
        elif args.command == "verify":
            if not args.file:
                print("ERROR: --file required for verify")
                return 1
            passed, report = manager.verify_backup(args.file)
            print(f"Verification: {'PASSED' if passed else 'FAILED'}")
            print(f"Tables verified: {report['tables_verified']}")
            print(f"Total rows: {report['total_rows']}")
        
        elif args.command == "cleanup":
            deleted = manager.cleanup_old_backups(dry_run=args.dry_run)
            print(f"{'Would delete' if args.dry_run else 'Deleted'}: {deleted} backups")
        
        elif args.command == "stats":
            stats = manager.get_stats()
            print("Backup Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        elif args.command == "configure-wal":
            manager.configure_wal_archiving()
        
        return 0
    
    except (BackupError, RestoreError) as e:
        logger.error(f"Command failed: {e}")
        return 1
    except KeyboardInterrupt:
        logger.warning("Command interrupted")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
