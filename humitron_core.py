#!/usr/bin/env python3
"""
Humitron Core - ReAct Loop Implementation

A local-first AI agent that uses Ollama for LLM inference and executes tools
in a ReAct (Reasoning + Acting) loop pattern.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

import httpx
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from loguru import logger

# ─── Configuration ──────────────────────────────────────────────────────────

DEFAULT_MODEL = "llama3.2"
OLLAMA_BASE_URL = "http://localhost:11434"
MAX_STEPS = 15
WORKSPACE_DIR = Path.cwd()  # Restrict tools to current working directory

console = Console()

# ─── Data Models ────────────────────────────────────────────────────────────


class ToolCall(BaseModel):
    """Represents a tool call from the LLM."""
    name: str
    arguments: Dict[str, Any]


class ToolResult(BaseModel):
    """Result of a tool execution."""
    success: bool
    output: str
    error: Optional[str] = None


class AgentState(BaseModel):
    """Current state of the agent."""
    messages: List[Dict[str, str]] = Field(default_factory=list)
    step_count: int = 0
    finished: bool = False
    final_answer: Optional[str] = None


# ─── Tool Definitions ───────────────────────────────────────────────────────


def read_file(path: str) -> ToolResult:
    """
    Read a file from the workspace.
    
    Args:
        path: Relative path to file from workspace root.
        
    Returns:
        ToolResult with file contents or error.
    """
    try:
        # Resolve path relative to workspace, ensure it stays within workspace
        target_path = (WORKSPACE_DIR / path).resolve()
        
        # Security check: ensure path is within workspace
        if not str(target_path).startswith(str(WORKSPACE_DIR.resolve())):
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


def bash_execute(command: str, timeout: int = 30) -> ToolResult:
    """
    Execute a bash command within the workspace directory.
    
    Args:
        command: Bash command to execute.
        timeout: Maximum execution time in seconds.
        
    Returns:
        ToolResult with command output or error.
    """
    # Security: restrict to safe commands (basic allowlist approach)
    # In production, you'd want more sophisticated sandboxing
    dangerous_patterns = ["rm -rf", "sudo", "chmod 777", "> /dev/", "dd if="]
    for pattern in dangerous_patterns:
        if pattern in command:
            return ToolResult(
                success=False,
                output="",
                error=f"Command blocked for safety: contains '{pattern}'"
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


# Registry of available tools
TOOLS: Dict[str, Callable[..., ToolResult]] = {
    "read_file": read_file,
    "bash_execute": bash_execute,
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
        "name": "bash_execute",
        "description": "Execute a bash command in the workspace directory. Use for running scripts, listing files, grep, etc.",
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
    }
]


# ─── Ollama Client ──────────────────────────────────────────────────────────


class OllamaClient:
    """Client for communicating with local Ollama instance."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = DEFAULT_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.Client(timeout=120.0)
    
    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Send a chat completion request to Ollama.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool schemas for function calling.
            
        Returns:
            Parsed response from Ollama.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for more deterministic tool use
            }
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        try:
            response = self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Is Ollama running? Try: ollama serve"
            )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama API error: {e.response.status_code} - {e.response.text}")


# ─── ReAct Agent ────────────────────────────────────────────────────────────


class ReActAgent:
    """ReAct (Reasoning + Acting) loop agent."""
    
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_steps: int = MAX_STEPS,
        workspace: Optional[Path] = None
    ):
        self.ollama = OllamaClient(model=model)
        self.max_steps = max_steps
        self.workspace = workspace or WORKSPACE_DIR
        self.state = AgentState()
        
        # System prompt that teaches the agent how to use tools
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with tool descriptions."""
        tool_descriptions = "\n".join([
            f"- {t['name']}: {t['description']}"
            for t in TOOL_SCHEMAS
        ])
        
        return f"""You are Humitron, a helpful AI assistant that can use tools to accomplish tasks.

You have access to the following tools:
{tool_descriptions}

WORKSPACE: {self.workspace}

RULES:
1. Think step by step. Show your reasoning before each tool call.
2. Use tools when you need information or need to perform actions.
3. Tool calls must be in the specified JSON format.
4. After each tool result, continue reasoning or provide the final answer.
5. Maximum {self.max_steps} steps per task.
6. When you have enough information, provide a clear final answer without calling more tools.

TOOL CALL FORMAT:
When you need to call a tool, respond with a JSON object in this exact format:
{{
  "tool_calls": [
    {{
      "name": "tool_name",
      "arguments": {{"param": "value"}}
    }}
  ]
}}

If you don't need to call a tool, just respond normally with your final answer."""
    
    def _print_thinking(self, content: str) -> None:
        """Print agent's thinking with nice formatting."""
        console.print(Panel(
            Text(content, style="cyan"),
            title="Thinking",
            border_style="cyan",
            padding=(0, 1)
        ))
    
    def _print_tool_call(self, tool_call: ToolCall) -> None:
        """Print tool call with syntax highlighting."""
        args_json = json.dumps(tool_call.arguments, indent=2)
        console.print(Panel(
            Syntax(args_json, "json", theme="monokai"),
            title=f"Tool Call: {tool_call.name}",
            border_style="yellow",
            padding=(0, 1)
        ))
    
    def _print_tool_result(self, result: ToolResult) -> None:
        """Print tool result with color coding."""
        if result.success:
            style = "green"
            title = "Tool Result"
        else:
            style = "red"
            title = "Tool Error"
        
        console.print(Panel(
            Text(result.output or result.error or "(no output)", style=style),
            title=title,
            border_style=style,
            padding=(0, 1)
        ))
    
    def _print_final_answer(self, answer: str) -> None:
        """Print final answer."""
        console.print(Panel(
            Text(answer, style="bold white"),
            title="Final Answer",
            border_style="green",
            padding=(1, 2)
        ))
    
    def _parse_tool_calls(self, response_content: str) -> List[ToolCall]:
        """Parse tool calls from LLM response."""
        try:
            # Try to extract JSON from the response
            # Look for tool_calls pattern
            if "tool_calls" in response_content:
                # Find JSON object in the response
                start = response_content.find("{")
                end = response_content.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = response_content[start:end]
                    data = json.loads(json_str)
                    return [ToolCall(**tc) for tc in data.get("tool_calls", [])]
            return []
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse tool calls: {e}")
            return []
    
    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call and return result."""
        tool_func = TOOLS.get(tool_call.name)
        if not tool_func:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {tool_call.name}"
            )
        
        try:
            return tool_func(**tool_call.arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool execution failed: {e}"
            )
    
    def run(self, user_prompt: str) -> str:
        """
        Run the ReAct loop for a user prompt.
        
        Args:
            user_prompt: The user's question or task.
            
        Returns:
            Final answer from the agent.
        """
        # Initialize conversation
        self.state = AgentState(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            step_count=0,
            finished=False
        )
        
        console.print(Panel(
            Text(user_prompt, style="bold white"),
            title="📝 User Prompt",
            border_style="blue",
            padding=(1, 2)
        ))
        
        while not self.state.finished and self.state.step_count < self.max_steps:
            self.state.step_count += 1
            
            console.print(f"\n[bold cyan]── Step {self.state.step_count}/{self.max_steps} ──[/bold cyan]\n")
            
            # Get LLM response
            response = self.ollama.chat(
                self.state.messages,
                tools=TOOL_SCHEMAS
            )
            
            assistant_message = response.get("message", {})
            content = assistant_message.get("content", "")
            
            # Add assistant message to history
            self.state.messages.append({"role": "assistant", "content": content})
            
            # Print thinking (content before any tool calls)
            if content and "tool_calls" not in content:
                self._print_thinking(content)
            
            # Parse and execute tool calls
            tool_calls = self._parse_tool_calls(content)
            
            if not tool_calls:
                # No tool calls = final answer
                self.state.finished = True
                self.state.final_answer = content
                self._print_final_answer(content)
                break
            
            # Execute each tool call
            for tool_call in tool_calls:
                self._print_tool_call(tool_call)
                result = self._execute_tool(tool_call)
                self._print_tool_result(result)
                
                # Add tool result to conversation
                tool_result_msg = {
                    "role": "tool",
                    "content": json.dumps({
                        "name": tool_call.name,
                        "result": result.output if result.success else result.error,
                        "success": result.success
                    })
                }
                self.state.messages.append(tool_result_msg)
        
        if self.state.step_count >= self.max_steps and not self.state.finished:
            msg = f"Reached maximum steps ({self.max_steps}). Stopping."
            console.print(f"[bold red]⚠️ {msg}[/bold red]")
            self.state.final_answer = msg
        
        return self.state.final_answer or "No answer generated."


# ─── Main Entry Point ───────────────────────────────────────────────────────


def main():
    """Main entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Humitron ReAct Agent")
    parser.add_argument("prompt", nargs="*", help="Prompt for the agent")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model to use")
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS, help="Max steps per query")
    parser.add_argument("--workspace", type=Path, help="Workspace directory")
    
    args = parser.parse_args()
    
    # Default test prompt if none provided
    prompt = " ".join(args.prompt) if args.prompt else "Read the README.md file and summarize it."
    
    # Setup logging
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    
    # Create and run agent
    agent = ReActAgent(
        model=args.model,
        max_steps=args.max_steps,
        workspace=args.workspace
    )
    
    try:
        agent.run(prompt)
    except ConnectionError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print("[yellow]Make sure Ollama is running: [bold]ollama serve[/bold][/yellow]")
        console.print(f"[yellow]And the model is pulled: [bold]ollama pull {args.model}[/bold][/yellow]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Agent error")
        sys.exit(1)


if __name__ == "__main__":
    main()
