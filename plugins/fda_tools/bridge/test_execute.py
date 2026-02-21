#!/usr/bin/env python3
"""
Test script for execute_fda_command subprocess execution.

Tests:
1. Basic command execution
2. Argument parsing with shlex
3. Timeout enforcement
4. Exit code handling
5. Output capture (stdout/stderr)
"""

import os
import sys
import time
import tempfile
from pathlib import Path

from fda_tools.bridge.server import execute_fda_command, SCRIPTS_DIR, COMMANDS_DIR


def create_test_script(script_path, content, executable=True):
    """Create a test Python script."""
    script_path.write_text(content)
    if executable:
        os.chmod(script_path, 0o755)


def create_test_command(command_path):
    """Create a test command .md file."""
    command_path.write_text("# Test Command\n\nTest command description.")


def test_basic_execution():
    """Test basic command execution with success."""
    print("Test 1: Basic execution")

    # Create test script that prints and exits 0
    test_script = SCRIPTS_DIR / "test_basic.py"
    create_test_script(test_script, """#!/usr/bin/env python3
print("Test output")
""")

    # Create test command
    test_command = COMMANDS_DIR / "test-basic.md"
    create_test_command(test_command)

    try:
        result = execute_fda_command(
            command="test-basic",
            args=None,
            user_id="test_user",
            session_id="test_session",
            channel="test"
        )

        assert result["success"] == True
        assert "Test output" in result["result"]
        assert result["command_metadata"]["exit_code"] == 0
        print("✓ Basic execution passed")

    finally:
        test_script.unlink(missing_ok=True)
        test_command.unlink(missing_ok=True)


def test_argument_parsing():
    """Test argument parsing with spaces and quotes."""
    print("\nTest 2: Argument parsing")

    # Create test script that echoes args
    test_script = SCRIPTS_DIR / "test_args.py"
    create_test_script(test_script, """#!/usr/bin/env python3
import sys
print("Args:", sys.argv[1:])
""")

    test_command = COMMANDS_DIR / "test-args.md"
    create_test_command(test_command)

    try:
        result = execute_fda_command(
            command="test-args",
            args='--flag "value with spaces" --number 42',
            user_id="test_user",
            session_id="test_session",
            channel="test"
        )

        assert result["success"] == True
        assert "--flag" in result["result"]
        assert "value with spaces" in result["result"]
        print("✓ Argument parsing passed")

    finally:
        test_script.unlink(missing_ok=True)
        test_command.unlink(missing_ok=True)


def test_timeout_enforcement():
    """Test timeout enforcement."""
    print("\nTest 3: Timeout enforcement")

    # Create test script that sleeps forever
    test_script = SCRIPTS_DIR / "test_timeout.py"
    create_test_script(test_script, """#!/usr/bin/env python3
import time
print("Starting...")
time.sleep(120)
print("Done")
""")

    test_command = COMMANDS_DIR / "test-timeout.md"
    create_test_command(test_command)

    try:
        # Set short timeout via environment
        old_timeout = os.environ.get("FDA_BRIDGE_COMMAND_TIMEOUT")
        os.environ["FDA_BRIDGE_COMMAND_TIMEOUT"] = "2"

        start = time.time()
        result = execute_fda_command(
            command="test-timeout",
            args=None,
            user_id="test_user",
            session_id="test_session",
            channel="test"
        )
        duration = time.time() - start

        assert result["success"] == False
        assert "timed out" in result["error"]
        assert duration < 5, f"Timeout took {duration}s, expected < 5s"
        print(f"✓ Timeout enforcement passed (took {duration:.2f}s)")

    finally:
        if old_timeout:
            os.environ["FDA_BRIDGE_COMMAND_TIMEOUT"] = old_timeout
        else:
            os.environ.pop("FDA_BRIDGE_COMMAND_TIMEOUT", None)
        test_script.unlink(missing_ok=True)
        test_command.unlink(missing_ok=True)


def test_exit_code_handling():
    """Test handling of non-zero exit codes."""
    print("\nTest 4: Exit code handling")

    # Create test script that exits with error
    test_script = SCRIPTS_DIR / "test_error.py"
    create_test_script(test_script, """#!/usr/bin/env python3
import sys
print("Error message")
sys.stderr.write("Error on stderr\\n")
sys.exit(1)
""")

    test_command = COMMANDS_DIR / "test-error.md"
    create_test_command(test_command)

    try:
        result = execute_fda_command(
            command="test-error",
            args=None,
            user_id="test_user",
            session_id="test_session",
            channel="test"
        )

        assert result["success"] == False
        assert result["command_metadata"]["exit_code"] == 1
        assert "Error message" in result["result"]
        assert "Error on stderr" in result["result"]
        print("✓ Exit code handling passed")

    finally:
        test_script.unlink(missing_ok=True)
        test_command.unlink(missing_ok=True)


def test_command_not_found():
    """Test handling of non-existent commands."""
    print("\nTest 5: Command not found")

    result = execute_fda_command(
        command="nonexistent-command",
        args=None,
        user_id="test_user",
        session_id="test_session",
        channel="test"
    )

    assert result["success"] == False
    assert "Command not found" in result["error"]
    print("✓ Command not found handling passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing execute_fda_command subprocess execution")
    print("=" * 60)

    try:
        test_basic_execution()
        test_argument_parsing()
        test_timeout_enforcement()
        test_exit_code_handling()
        test_command_not_found()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
