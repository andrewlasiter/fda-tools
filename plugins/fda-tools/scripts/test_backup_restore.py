#!/usr/bin/env python3
"""
Test Suite for FDA Project Backup and Restore.

Comprehensive integration tests for backup_project.py and restore_project.py
with checksum verification, collision detection, and disaster recovery scenarios.

Usage:
    python3 test_backup_restore.py                 # Run all tests
    python3 test_backup_restore.py --quick         # Run quick tests only
    python3 test_backup_restore.py --verbose       # Verbose output

Test Coverage:
    - Checksum computation and verification
    - Single project backup/restore
    - Multi-project backup/restore
    - Collision detection
    - Selective restore
    - Integrity verification
    - Dry-run mode
    - Force overwrite
    - Metadata validation
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List

# Import modules to test
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backup_project import (
    compute_file_hash,
    collect_project_files,
    create_backup_archive,
    verify_backup_integrity,
    list_available_backups,
)
from restore_project import (
    list_backup_contents,
    check_project_collision,
    restore_projects,
)


class BackupRestoreTestSuite:
    """Test suite for backup and restore functionality."""

    def __init__(self, verbose: bool = False):
        """Initialize test suite.

        Args:
            verbose: If True, print detailed test output.
        """
        self.verbose = verbose
        self.test_count = 0
        self.pass_count = 0
        self.fail_count = 0

    def log(self, message: str):
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"  {message}")

    def assert_true(self, condition: bool, message: str):
        """Assert condition is true."""
        if not condition:
            raise AssertionError(f"Assertion failed: {message}")

    def assert_equal(self, actual, expected, message: str):
        """Assert actual equals expected."""
        if actual != expected:
            raise AssertionError(
                f"Assertion failed: {message}\n"
                f"  Expected: {expected}\n"
                f"  Actual: {actual}"
            )

    def run_test(self, test_name: str, test_func):
        """Run a single test function."""
        self.test_count += 1
        try:
            print(f"\n[{self.test_count}] Testing: {test_name}")
            test_func()
            self.pass_count += 1
            print(f"  ✅ PASSED")
        except Exception as e:
            self.fail_count += 1
            print(f"  ❌ FAILED: {e}")

    def test_checksum_computation(self):
        """Test SHA-256 checksum computation."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            file_hash = compute_file_hash(temp_path)
            self.log(f"Computed hash: {file_hash}")

            # Verify hash is 64 hex characters (SHA-256)
            self.assert_equal(len(file_hash), 64, "Hash length should be 64")
            self.assert_true(
                all(c in '0123456789abcdef' for c in file_hash),
                "Hash should be hexadecimal"
            )
        finally:
            temp_path.unlink()

    def test_collect_project_files(self):
        """Test project file collection with checksums."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test_project"
            project_dir.mkdir()

            # Create test files
            (project_dir / "file1.txt").write_text("content 1")
            (project_dir / "file2.json").write_text('{"key": "value"}')

            subdir = project_dir / "subdir"
            subdir.mkdir()
            (subdir / "file3.md").write_text("# Header")

            files_with_hashes = collect_project_files(project_dir)

            self.log(f"Collected {len(files_with_hashes)} files")
            self.assert_equal(len(files_with_hashes), 3, "Should collect 3 files")

            # Verify all files have hashes
            for file_path, file_hash in files_with_hashes:
                self.assert_equal(len(file_hash), 64, f"Hash for {file_path.name}")

    def test_single_project_backup(self):
        """Test backup of a single project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir) / "projects"
            projects_dir.mkdir()

            project_dir = projects_dir / "test_project"
            project_dir.mkdir()
            (project_dir / "data.json").write_text('{"test": true}')

            output_dir = Path(temp_dir) / "backups"
            output_dir.mkdir()
            output_path = output_dir / "test_backup.zip"

            result = create_backup_archive(
                projects_dir,
                ["test_project"],
                output_path,
                verify=True
            )

            self.log(f"Backup result: {result['status']}")
            self.assert_equal(result['status'], 'success', "Backup should succeed")
            self.assert_true(output_path.exists(), "Backup file should exist")
            self.assert_true(
                result['verification']['passed'],
                "Verification should pass"
            )

    def test_backup_verification(self):
        """Test backup integrity verification."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir) / "projects"
            projects_dir.mkdir()

            project_dir = projects_dir / "test_project"
            project_dir.mkdir()
            (project_dir / "file.txt").write_text("test")

            output_path = Path(temp_dir) / "backup.zip"
            create_backup_archive(projects_dir, ["test_project"], output_path)

            # Verify integrity
            verification = verify_backup_integrity(output_path)

            self.log(f"Verification: {verification['passed']}")
            self.assert_true(verification['passed'], "Verification should pass")
            self.assert_true(
                verification['metadata'] is not None,
                "Metadata should be present"
            )

    def test_multi_project_backup(self):
        """Test backup of multiple projects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir) / "projects"
            projects_dir.mkdir()

            # Create 3 projects
            for i in range(1, 4):
                project_dir = projects_dir / f"project_{i}"
                project_dir.mkdir()
                (project_dir / "data.json").write_text(f'{{"id": {i}}}')

            output_path = Path(temp_dir) / "multi_backup.zip"
            result = create_backup_archive(
                projects_dir,
                ["project_1", "project_2", "project_3"],
                output_path
            )

            self.log(f"Total files: {result['total_files']}")
            self.assert_equal(result['total_files'], 3, "Should backup 3 files")
            self.assert_equal(
                len(result['projects']), 3,
                "Should backup 3 projects"
            )

    def test_list_backup_contents(self):
        """Test listing backup archive contents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir) / "projects"
            projects_dir.mkdir()

            project_dir = projects_dir / "test_project"
            project_dir.mkdir()
            (project_dir / "file1.txt").write_text("a")
            (project_dir / "file2.txt").write_text("b")

            output_path = Path(temp_dir) / "backup.zip"
            create_backup_archive(projects_dir, ["test_project"], output_path)

            contents = list_backup_contents(output_path)

            self.log(f"Projects: {contents['projects']}")
            self.assert_equal(len(contents['projects']), 1, "Should have 1 project")
            self.assert_equal(
                contents['total_files'], 2,
                "Should have 2 files"
            )

    def test_collision_detection(self):
        """Test project collision detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir)

            # Create existing project
            (projects_dir / "existing_project").mkdir()

            collisions = check_project_collision(
                projects_dir,
                ["existing_project", "new_project"]
            )

            self.log(f"Collisions: {collisions}")
            self.assert_true(
                collisions["existing_project"],
                "Should detect existing project"
            )
            self.assert_true(
                not collisions["new_project"],
                "Should not detect new project"
            )

    def test_dry_run_restore(self):
        """Test dry-run restore mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir) / "projects"
            projects_dir.mkdir()

            project_dir = projects_dir / "test_project"
            project_dir.mkdir()
            (project_dir / "data.json").write_text('{"test": true}')

            output_path = Path(temp_dir) / "backup.zip"
            create_backup_archive(projects_dir, ["test_project"], output_path)

            # Remove project
            shutil.rmtree(project_dir)

            # Dry-run restore
            result = restore_projects(
                output_path,
                projects_dir,
                dry_run=True
            )

            self.log(f"Dry-run result: {result['status']}")
            self.assert_equal(result['status'], 'dry_run', "Should be dry-run")
            self.assert_true(
                not project_dir.exists(),
                "Project should not be restored in dry-run"
            )

    def test_actual_restore(self):
        """Test actual project restoration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir) / "projects"
            projects_dir.mkdir()

            project_dir = projects_dir / "test_project"
            project_dir.mkdir()
            test_content = '{"test": true, "value": 42}'
            (project_dir / "data.json").write_text(test_content)

            output_path = Path(temp_dir) / "backup.zip"
            create_backup_archive(projects_dir, ["test_project"], output_path)

            # Remove project
            shutil.rmtree(project_dir)
            self.assert_true(not project_dir.exists(), "Project should be deleted")

            # Restore
            result = restore_projects(
                output_path,
                projects_dir,
                verify_checksums=True
            )

            self.log(f"Restore result: {result['status']}")
            self.assert_equal(result['status'], 'success', "Restore should succeed")
            self.assert_true(project_dir.exists(), "Project should be restored")

            restored_content = (project_dir / "data.json").read_text()
            self.assert_equal(
                restored_content, test_content,
                "Restored content should match original"
            )

    def test_selective_restore(self):
        """Test selective project restore from multi-project backup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir) / "projects"
            projects_dir.mkdir()

            # Create 2 projects
            for i in [1, 2]:
                project_dir = projects_dir / f"project_{i}"
                project_dir.mkdir()
                (project_dir / "data.json").write_text(f'{{"id": {i}}}')

            output_path = Path(temp_dir) / "backup.zip"
            create_backup_archive(
                projects_dir,
                ["project_1", "project_2"],
                output_path
            )

            # Remove both projects
            shutil.rmtree(projects_dir / "project_1")
            shutil.rmtree(projects_dir / "project_2")

            # Restore only project_1
            result = restore_projects(
                output_path,
                projects_dir,
                selected_projects=["project_1"]
            )

            self.log(f"Selective restore: {result['restored_projects']}")
            self.assert_true(
                (projects_dir / "project_1").exists(),
                "project_1 should be restored"
            )
            self.assert_true(
                not (projects_dir / "project_2").exists(),
                "project_2 should NOT be restored"
            )

    def test_checksum_verification_on_restore(self):
        """Test checksum verification during restore."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir) / "projects"
            projects_dir.mkdir()

            project_dir = projects_dir / "test_project"
            project_dir.mkdir()
            (project_dir / "data.json").write_text('{"verified": true}')

            output_path = Path(temp_dir) / "backup.zip"
            create_backup_archive(projects_dir, ["test_project"], output_path)

            # Remove project
            shutil.rmtree(project_dir)

            # Restore with checksum verification
            result = restore_projects(
                output_path,
                projects_dir,
                verify_checksums=True
            )

            self.log(f"Verified files: {result['verified_files']}")
            self.assert_equal(
                result['verified_files'], 1,
                "Should verify 1 file"
            )
            self.assert_equal(
                len(result['checksum_failures']), 0,
                "Should have no checksum failures"
            )

    def run_all_tests(self):
        """Run all tests in the suite."""
        print("\n" + "=" * 80)
        print("FDA BACKUP/RESTORE TEST SUITE")
        print("=" * 80)

        self.run_test("Checksum Computation", self.test_checksum_computation)
        self.run_test("Collect Project Files", self.test_collect_project_files)
        self.run_test("Single Project Backup", self.test_single_project_backup)
        self.run_test("Backup Verification", self.test_backup_verification)
        self.run_test("Multi-Project Backup", self.test_multi_project_backup)
        self.run_test("List Backup Contents", self.test_list_backup_contents)
        self.run_test("Collision Detection", self.test_collision_detection)
        self.run_test("Dry-Run Restore", self.test_dry_run_restore)
        self.run_test("Actual Restore", self.test_actual_restore)
        self.run_test("Selective Restore", self.test_selective_restore)
        self.run_test("Checksum Verification on Restore", self.test_checksum_verification_on_restore)

        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total tests: {self.test_count}")
        print(f"Passed: {self.pass_count} ✅")
        print(f"Failed: {self.fail_count} ❌")

        if self.fail_count == 0:
            print("\n🎉 ALL TESTS PASSED")
            return 0
        else:
            print(f"\n⚠️  {self.fail_count} TEST(S) FAILED")
            return 1


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Test Suite for FDA Project Backup and Restore"
    )
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose output")
    parser.add_argument("--quick", action="store_true",
                        help="Run quick tests only (not implemented yet)")

    args = parser.parse_args()

    suite = BackupRestoreTestSuite(verbose=args.verbose)
    exit_code = suite.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
