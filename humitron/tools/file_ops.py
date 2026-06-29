#!/usr/bin/env python3
"""File operation tools for Humitron."""
from pathlib import Path
from typing import Any, Dict
from humitron.models.tools import ToolResult
from humitron.config.settings import get_config
from humitron.safety.paths import is_path_in_workspace

WORKSPACE_DIR = Path(get_config().workspace_path).resolve()


def read_file(path: str) -> ToolResult:
    """
    Read a file from the workspace.
    
    Args:
        path: Relative path to file from workspace root.
        
    Returns:
        ToolResult with file contents or error.
    """
    try:
        target_path = (WORKSPACE_DIR / path).resolve()
        
        # Security check: ensure path is within workspace
        if not is_path_in_workspace(target_path):
            return ToolResult(
                success=False,
                output="",
                error=f"Access denied: path '{path}' is outside workspace"
            )
        
        if not target_path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"File not found: {path}"
            )
        
        if not target_path.is_file():
            return ToolResult(
                success=False,
                output="",
                error=f"Not a file: {path}"
            )
        
        content = target_path.read_text(encoding="utf-8")
        return ToolResult(success=True, output=content)
    
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def write_file(path: str, content: str) -> ToolResult:
    """
    Write content to a file in the workspace.
    
    Args:
        path: Relative path to file from workspace root.
        content: Content to write to the file.
        
    Returns:
        ToolResult with success status or error.
    """
    try:
        target_path = (WORKSPACE_DIR / path).resolve()
        
        # Security check: ensure path is within workspace
        if not is_path_in_workspace(target_path):
            return ToolResult(
                success=False,
                output="",
                error=f"Access denied: path '{path}' is outside workspace"
            )
        
        # Create parent directories if they don't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        target_path.write_text(content, encoding="utf-8")
        return ToolResult(success=True, output=f"Successfully wrote {len(content)} characters to {path}")
    
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))