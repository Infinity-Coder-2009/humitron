#!/usr/bin/env python3
"""File operation tools for Humitron."""

from pathlib import Path
from typing import Any, Dict
from humitron.models.tools import ToolResult
from humitron.config.loader import get_config
from humitron.utils.safety import is_path_in_workspace
from humitron.utils.logging import get_logger

logger = get_logger(__name__)

WORKSPACE_DIR = Path(get_config().workspace_path).resolve()


def read_file(path: str) -> ToolResult:
    """Read a file from the workspace.

    Args:
        path: Relative path to file from workspace root.

    Returns:
        ToolResult with file contents or error.

    Raises:
        ToolResult with error if file not found or access denied.
    """
    logger.debug(f"Reading file: {path}")
    try:
        target_path = (WORKSPACE_DIR / path).resolve()

        # Security check: ensure path is within workspace
        if not is_path_in_workspace(target_path):
            logger.warning(f"Access denied: path '{path}' is outside workspace")
            return ToolResult(
                success=False,
                output="",
                error=f"Access denied: path '{path}' is outside workspace"
            )

        if not target_path.exists():
            logger.warning(f"File not found: {path}")
            return ToolResult(
                success=False,
                output="",
                error=f"File not found: {path}"
            )

        if not target_path.is_file():
            logger.warning(f"Not a file: {path}")
            return ToolResult(
                success=False,
                output="",
                error=f"Not a file: {path}"
            )

        content = target_path.read_text(encoding="utf-8")
        logger.debug(f"Successfully read {len(content)} characters from {path}")
        return ToolResult(success=True, output=content)

    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        return ToolResult(success=False, output="", error=str(e))


def write_file(path: str, content: str) -> ToolResult:
    """Write content to a file in the workspace.

    Args:
        path: Relative path to file from workspace root.
        content: Content to write to the file.

    Returns:
        ToolResult with success status or error.

    Raises:
        ToolResult with error if access denied or write fails.
    """
    logger.debug(f"Writing file: {path} ({len(content)} characters)")
    try:
        target_path = (WORKSPACE_DIR / path).resolve()

        # Security check: ensure path is within workspace
        if not is_path_in_workspace(target_path):
            logger.warning(f"Access denied: path '{path}' is outside workspace")
            return ToolResult(
                success=False,
                output="",
                error=f"Access denied: path '{path}' is outside workspace"
            )

        # Create parent directories if they don't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        target_path.write_text(content, encoding="utf-8")
        logger.info(f"Successfully wrote {len(content)} characters to {path}")
        return ToolResult(success=True, output=f"Successfully wrote {len(content)} characters to {path}")

    except Exception as e:
        logger.error(f"Error writing file {path}: {e}")
        return ToolResult(success=False, output="", error=str(e))