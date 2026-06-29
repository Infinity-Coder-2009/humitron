#!/usr/bin/env python3
"""Tool registry for Humitron."""

from humitron.tools.file_ops import read_file, write_file
from humitron.tools.bash import bash_execute
from humitron.tools.web import web_search
from humitron.models.tools import ToolResult
from typing import Callable, Dict, Any, List

# Registry of available tools
TOOLS: Dict[str, Callable[..., ToolResult]] = {
    "read_file": read_file,
    "write_file": write_file,
    "bash_execute": bash_execute,
    "web_search": web_search,
}

# Tool schemas for LLM function calling
TOOL_SCHEMAS = [
    {
        "name": "read_file",
        "description": "Read a file from the workspace. Use this to examine code, config, or any text file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file from workspace root"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file in the workspace. Creates directories if needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file from workspace root"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "bash_execute",
        "description": "Execute a bash command in the workspace directory. Use for running scripts, listing files, grep, etc. Dangerous commands are blocked.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 30)",
                    "default": 30
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo (free, no API key). Returns top results with snippets.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
]