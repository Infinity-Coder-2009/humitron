#!/usr/bin/env python3
"""Tool-related data models."""
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional


class ToolCall(BaseModel):
    """Represents a tool call from the LLM.

    Attributes:
        name: Name of the tool to call.
        arguments: Arguments to pass to the tool.
    """
    name: str
    arguments: Dict[str, Any]


class ToolResult(BaseModel):
    """Result of a tool execution.

    Attributes:
        success: Whether the tool executed successfully.
        output: Tool output on success.
        error: Error message on failure.
    """
    success: bool
    output: str
    error: Optional[str] = None