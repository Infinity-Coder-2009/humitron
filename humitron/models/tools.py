#!/usr/bin/env python3
"""Tool-related data models."""
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional


class ToolCall(BaseModel):
    """Represents a tool call from the LLM."""
    name: str
    arguments: Dict[str, Any]


class ToolResult(BaseModel):
    """Result of a tool execution."""
    success: bool
    output: str
    error: Optional[str] = None