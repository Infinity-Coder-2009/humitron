#!/usr/bin/env python3
"""Unit tests for Humitron tools."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from humitron.tools.file_ops import read_file, write_file
from humitron.tools.bash import bash_execute
from humitron.tools.web import web_search
from humitron.models.tools import ToolResult
from humitron.config.loader import Config


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Override config workspace
        original_workspace = Config.workspace_path
        Config.workspace_path = tmpdir
        yield Path(tmpdir)
        Config.workspace_path = original_workspace


class TestFileOps:
    """Tests for file operations."""

    def test_read_file_success(self, temp_workspace):
        """Test reading an existing file."""
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Hello, World!")

        result = read_file("test.txt")

        assert result.success is True
        assert result.output == "Hello, World!"
        assert result.error is None

    def test_read_file_not_found(self, temp_workspace):
        """Test reading a non-existent file."""
        result = read_file("nonexistent.txt")

        assert result.success is False
        assert "File not found" in result.error

    def test_read_file_outside_workspace(self, temp_workspace):
        """Test reading a file outside workspace."""
        with tempfile.TemporaryDirectory() as outside_dir:
            outside_file = Path(outside_dir) / "secret.txt"
            outside_file.write_text("Secret!")

            result = read_file(str(outside_file))

            assert result.success is False
            assert "Access denied" in result.error

    def test_write_file_success(self, temp_workspace):
        """Test writing a file."""
        result = write_file("new_file.txt", "Test content")

        assert result.success is True
        assert "Successfully wrote" in result.output

        # Verify file was created
        written_file = temp_workspace / "new_file.txt"
        assert written_file.exists()
        assert written_file.read_text() == "Test content"

    def test_write_file_creates_directories(self, temp_workspace):
        """Test writing a file creates parent directories."""
        result = write_file("subdir/nested/file.txt", "Nested content")

        assert result.success is True

        written_file = temp_workspace / "subdir" / "nested" / "file.txt"
        assert written_file.exists()
        assert written_file.read_text() == "Nested content"

    def test_write_file_outside_workspace(self, temp_workspace):
        """Test writing a file outside workspace."""
        with tempfile.TemporaryDirectory() as outside_dir:
            outside_path = Path(outside_dir) / "secret.txt"

            result = write_file(str(outside_path), "Secret!")

            assert result.success is False
            assert "Access denied" in result.error


class TestBashExecute:
    """Tests for bash execution."""

    def test_bash_execute_success(self, temp_workspace):
        """Test executing a simple command."""
        result = bash_execute("echo 'Hello, World!'")

        assert result.success is True
        assert "Hello, World!" in result.output

    def test_bash_execute_failure(self, temp_workspace):
        """Test executing a failing command."""
        result = bash_execute("false")

        assert result.success is False
        assert "Exit code" in result.error

    def test_bash_execute_dangerous_rm_rf_root(self, temp_workspace):
        """Test that rm -rf / is blocked."""
        result = bash_execute("rm -rf /")

        assert result.success is False
        assert "blocked" in result.error.lower()

    def test_bash_execute_dangerous_sudo(self, temp_workspace):
        """Test that sudo is blocked."""
        result = bash_execute("sudo ls")

        assert result.success is False
        assert "blocked" in result.error.lower()

    def test_bash_execute_dangerous_chmod_777(self, temp_workspace):
        """Test that chmod 777 is blocked."""
        result = bash_execute("chmod 777 /etc/passwd")

        assert result.success is False
        assert "blocked" in result.error.lower()

    def test_bash_execute_dangerous_fork_bomb(self, temp_workspace):
        """Test that fork bomb is blocked."""
        result = bash_execute(":(){ :|:& };:")

        assert result.success is False
        assert "blocked" in result.error.lower()

    def test_bash_execute_chained_dangerous(self, temp_workspace):
        """Test that chained dangerous commands are blocked."""
        result = bash_execute("echo hello && rm -rf /")

        assert result.success is False
        assert "blocked" in result.error.lower()

    def test_bash_execute_timeout(self, temp_workspace):
        """Test command timeout."""
        result = bash_execute("sleep 10", timeout=1)

        assert result.success is False
        assert "timed out" in result.error.lower()


class TestWebSearch:
    """Tests for web search."""

    @patch("humitron.tools.web.urllib.request.urlopen")
    def test_web_search_success(self, mock_urlopen, temp_workspace):
        """Test successful web search."""
        # Mock HTML response
        mock_html = """
        <html>
            <a class="result__snippet" href="https://example.com">Test snippet</a>
            <a class="result__url">Example Title</a>
        </html>
        """
        mock_response = MagicMock()
        mock_response.read.return_value = mock_html.encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)
        mock_urlopen.return_value = mock_response

        result = web_search("test query")

        assert result.success is True
        assert "test query" in result.output.lower()

    @patch("humitron.tools.web.urllib.request.urlopen")
    def test_web_search_no_results(self, mock_urlopen, temp_workspace):
        """Test web search with no results."""
        mock_html = "<html><body>No results</body></html>"
        mock_response = MagicMock()
        mock_response.read.return_value = mock_html.encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)
        mock_urlopen.return_value = mock_response

        result = web_search("test query")

        assert result.success is True
        assert "no structured results" in result.output.lower()

    @patch("humitron.tools.web.urllib.request.urlopen")
    def test_web_search_network_error(self, mock_urlopen, temp_workspace):
        """Test web search network error."""
        mock_urlopen.side_effect = Exception("Network error")

        result = web_search("test query")

        assert result.success is False
        assert "failed" in result.error.lower()


class TestSafety:
    """Tests for safety utilities."""

    def test_is_path_in_workspace(self, temp_workspace):
        """Test path validation."""
        from humitron.utils.safety import is_path_in_workspace

        inside_file = temp_workspace / "inside.txt"
        inside_file.write_text("test")

        with tempfile.TemporaryDirectory() as outside_dir:
            outside_file = Path(outside_dir) / "outside.txt"
            outside_file.write_text("test")

            assert is_path_in_workspace(inside_file) is True
            assert is_path_in_workspace(outside_file) is False

    def test_is_command_dangerous(self, temp_workspace):
        """Test dangerous command detection."""
        from humitron.utils.safety import is_command_dangerous

        dangerous_commands = [
            "rm -rf /",
            "rm -rf *",
            "sudo ls",
            "chmod 777 /etc/passwd",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
            ":(){ :|:& };:",
            "shutdown -h now",
            "reboot",
            "echo test > /dev/sda",
            "chown -R root /",
            "rm -rf / && echo done",
            "echo hello; rm -rf /",
        ]

        for cmd in dangerous_commands:
            dangerous, reason = is_command_dangerous(cmd)
            assert dangerous is True, f"Command should be dangerous: {cmd}"
            assert "blocked" in reason.lower()

        safe_commands = [
            "ls -la",
            "echo hello",
            "cat file.txt",
            "grep pattern file.txt",
            "python script.py",
            "git status",
        ]

        for cmd in safe_commands:
            dangerous, reason = is_command_dangerous(cmd)
            assert dangerous is False, f"Command should be safe: {cmd}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])