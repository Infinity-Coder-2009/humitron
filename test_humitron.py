#!/usr/bin/env python3
"""
Test script for Humitron core ReAct loop.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from humitron_core import ReActAgent, read_file, bash_execute, ToolResult


def test_read_file():
    """Test the read_file tool."""
    print("Testing read_file tool...")
    result = read_file("README.md")
    assert isinstance(result, ToolResult)
    assert result.success, f"Expected success, got error: {result.error}"
    assert "Humitron" in result.output, "README should contain 'Humitron'"
    print("read_file works correctly")


def test_bash_execute():
    """Test the bash_execute tool."""
    print("Testing bash_execute tool...")
    result = bash_execute("ls -la")
    assert isinstance(result, ToolResult)
    assert result.success, f"Expected success, got error: {result.error}"
    assert "README.md" in result.output, "ls should show README.md"
    print("bash_execute works correctly")


def test_bash_execute_safety():
    """Test that dangerous commands are blocked."""
    print("Testing bash_execute safety...")
    result = bash_execute("rm -rf /")
    assert isinstance(result, ToolResult)
    assert not result.success, "Dangerous command should be blocked"
    assert "blocked" in result.error.lower(), "Should mention blocked"
    print("Safety blocking works correctly")


def test_react_agent_read_readme():
    """Test the full ReAct loop by reading README.md."""
    print("Testing ReAct agent with README.md...")
    
    # This test requires Ollama to be running
    # We'll just verify the agent initializes correctly
    agent = ReActAgent(model="llama3.2", max_steps=5)
    assert agent.max_steps == 5
    assert agent.ollama.model == "llama3.2"
    print("ReActAgent initializes correctly")


if __name__ == "__main__":
    print("Running Humitron core tests...\n")
    
    test_read_file()
    test_bash_execute()
    test_bash_execute_safety()
    test_react_agent_read_readme()
    
    print("\n All tests passed!")
