#!/usr/bin/env python3
"""
Test script for Humitron core ReAct loop.
"""

import sys
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from humitron_core import (
    ReActAgent, 
    read_file, 
    write_file, 
    bash_execute, 
    web_search,
    ToolResult,
    validate_path,
    check_command_safety,
    SafetyError,
    WORKSPACE_DIR
)


def test_read_file():
    """Test the read_file tool."""
    print("Testing read_file tool...")
    result = read_file("README.md")
    assert isinstance(result, ToolResult)
    assert result.success, f"Expected success, got error: {result.error}"
    assert "Humitron" in result.output, "README should contain 'Humitron'"
    print("✅ read_file works correctly")


def test_write_file():
    """Test the write_file tool."""
    print("Testing write_file tool...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        result = write_file("test.txt", "Hello Humitron", workspace=tmp_path)
        assert isinstance(result, ToolResult)
        assert result.success, f"Expected success, got error: {result.error}"
        
        # Verify file was written
        read_result = read_file("test.txt", workspace=tmp_path)
        assert read_result.success
        assert read_result.output == "Hello Humitron"
    print("✅ write_file works correctly")


def test_bash_execute():
    """Test the bash_execute tool."""
    print("Testing bash_execute tool...")
    result = bash_execute("ls -la")
    assert isinstance(result, ToolResult)
    assert result.success, f"Expected success, got error: {result.error}"
    assert "README.md" in result.output, "ls should show README.md"
    print("✅ bash_execute works correctly")


def test_bash_execute_safety():
    """Test that dangerous commands are blocked."""
    print("Testing bash_execute safety...")
    
    # Test various dangerous commands
    dangerous_commands = [
        "rm -rf /",
        "sudo ls",
        "chmod 777 /etc/passwd",
        "dd if=/dev/zero of=/dev/sda",
        "mkfs.ext4 /dev/sda1",
        ":(){ :|:& };:",
        "shutdown -h now",
        "reboot",
    ]
    
    for cmd in dangerous_commands:
        result = bash_execute(cmd)
        assert isinstance(result, ToolResult)
        assert not result.success, f"Dangerous command should be blocked: {cmd}"
        assert "blocked" in result.error.lower(), f"Should mention blocked for: {cmd}"
    
    print("✅ Safety blocking works correctly")


def test_validate_path():
    """Test path validation and sandboxing."""
    print("Testing path validation...")
    
    # Valid path within workspace
    valid_path = validate_path("README.md", WORKSPACE_DIR)
    assert valid_path.exists()
    assert valid_path.is_file()
    
    # Invalid path outside workspace
    try:
        validate_path("../../etc/passwd", WORKSPACE_DIR)
        assert False, "Should have raised SafetyError"
    except SafetyError:
        pass  # Expected
    
    print("✅ Path validation works correctly")


def test_check_command_safety():
    """Test command safety checker."""
    print("Testing command safety checker...")
    
    safe_commands = ["ls -la", "echo hello", "cat file.txt", "grep pattern file.txt", "python script.py"]
    for cmd in safe_commands:
        is_safe, error = check_command_safety(cmd)
        assert is_safe, f"Safe command blocked: {cmd} - {error}"
        assert error is None
    
    dangerous_commands = ["rm -rf /", "sudo ls", "chmod 777 file"]
    for cmd in dangerous_commands:
        is_safe, error = check_command_safety(cmd)
        assert not is_safe, f"Dangerous command allowed: {cmd}"
        assert error is not None
    
    print("✅ Command safety checker works correctly")


def test_web_search():
    """Test web search (requires internet)."""
    print("Testing web search...")
    try:
        result = web_search("Python programming language", max_results=3)
        assert isinstance(result, ToolResult)
        # May succeed or fail depending on network
        if result.success:
            assert "Python" in result.output
            print("✅ Web search works correctly")
        else:
            print(f"⚠️ Web search failed (network issue): {result.error}")
    except Exception as e:
        print(f"⚠️ Web search error (network issue): {e}")


def test_react_agent():
    """Test the ReAct agent initialization."""
    print("Testing ReAct agent...")
    agent = ReActAgent(model="llama3.2", max_steps=5)
    assert agent.max_steps == 5
    assert agent.ollama.model == "llama3.2"
    assert agent.workspace == WORKSPACE_DIR
    print("✅ ReActAgent initializes correctly")


def test_integration_write_read():
    """Integration test: write a file then read it back."""
    print("Testing write + read integration...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        agent = ReActAgent(workspace=tmp_path, max_steps=5)
        
        # Write file
        write_result = write_file("test.txt", "Hello Humitron", workspace=tmp_path)
        assert write_result.success
        
        # Read file
        read_result = read_file("test.txt", workspace=tmp_path)
        assert read_result.success
        assert read_result.output == "Hello Humitron"
    
    print("✅ Integration test passed")


if __name__ == "__main__":
    print("Running Humitron core tests...\n")
    
    test_read_file()
    test_write_file()
    test_bash_execute()
    test_bash_execute_safety()
    test_validate_path()
    test_check_command_safety()
    test_web_search()
    test_react_agent()
    test_integration_write_read()
    
    print("\n✅ All tests passed!")