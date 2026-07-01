#!/usr/bin/env python3
"""Bash execution tool for Humitron."""

import re
import subprocess
from typing import Tuple
from humitron.models.tools import ToolResult
from humitron.config.loader import get_config
from humitron.utils.safety import is_command_dangerous, DANGEROUS_REGEX
from humitron.utils.logging import get_logger

logger = get_logger(__name__)

WORKSPACE_DIR = Path(get_config().workspace_path).resolve()


def bash_execute(command: str, timeout: int = 30) -> ToolResult:
    """Execute a bash command within the workspace directory.

    Args:
        command: Bash command to execute.
        timeout: Maximum execution time in seconds.

    Returns:
        ToolResult with command output or error.

    Raises:
        ToolResult with error if command is dangerous or execution fails.
    """
    logger.debug(f"Executing command: {command}")

    # Safety check: block dangerous commands
    dangerous, reason = is_command_dangerous(command)
    if dangerous:
        logger.warning(f"Command blocked: {reason}")
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

        success = result.returncode == 0
        if success:
            logger.debug(f"Command succeeded: {command}")
        else:
            logger.warning(f"Command failed (exit {result.returncode}): {command}")

        return ToolResult(
            success=success,
            output=output.strip(),
            error=None if success else f"Exit code: {result.returncode}"
        )

    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds: {command}")
        return ToolResult(
            success=False,
            output="",
            error=f"Command timed out after {timeout} seconds"
        )
    except Exception as e:
        logger.error(f"Error executing command {command}: {e}")
        return ToolResult(success=False, output="", error=str(e))