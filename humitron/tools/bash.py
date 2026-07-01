#!/usr/bin/env python3
"""Bash execution tool for Humitron."""
import re
import subprocess
from typing import Tuple
from humitron.models.tools import ToolResult
from humitron.config.settings import get_config
from humitron.safety.commands import is_command_dangerous, DANGEROUS_REGEX

WORKSPACE_DIR = Path(get_config().workspace_path).resolve()


def bash_execute(command: str, timeout: int = 30) -> ToolResult:
    """
    Execute a bash command within the workspace directory.
    
    Args:
        command: Bash command to execute.
        timeout: Maximum execution time in seconds.
        
    Returns:
        ToolResult with command output or error.
    """
    # Safety check: block dangerous commands
    dangerous, reason = is_command_dangerous(command)
    if dangerous:
        return ToolResult(
            success=False,
            output="",
            error="Command blocked for security reasons."
        )
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        
        return ToolResult(
            success=result.returncode == 0,
            output=output.strip(),
            error=None if result.returncode == 0 else f"Exit code: {result.returncode}"
        )
    
    except subprocess.TimeoutExpired:
        return ToolResult(
            success=False,
            output="",
            error=f"Command timed out after {timeout} seconds"
        )
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))