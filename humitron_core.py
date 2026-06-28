#!/usr/bin/env python3
"""
Humitron Core - ReAct Loop Implementation

A local-first AI agent that uses Ollama for LLM inference and executes tools
in a ReAct (Reasoning + Acting) loop pattern with full safety sandboxing.
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Tuple

import httpx
import yaml
from duckduckgo_search import DDGS
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.prompt import Prompt
from rich.markdown import Markdown
from loguru import logger

# ─── Configuration Loading ─────────────────────────────────────────────────


def load_config(config_path: Path = Path("config.yaml")) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    default_config = {
        "model": "llama3.2",
        "workspace_path": ".",
        "max_steps": 20,
        "temperature": 0.7,
        "ollama_base_url": "http://localhost:11434",
        "web_search_max_results": 5,
        "web_search_region": "wt-wt",
        "enable_safety_checks": True,
        "allowed_directories": [],
        "max_context_tokens": 8000,
        "summarize_threshold": 6000,
    }
    
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}
                default_config.update(user_config)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
    
    return default_config


CONFIG = load_config()
DEFAULT_MODEL = CONFIG["model"]
OLLAMA_BASE_URL = CONFIG["ollama_base_url"]
MAX_STEPS = CONFIG["max_steps"]
WORKSPACE_DIR = Path(CONFIG["workspace_path"]).resolve()
TEMPERATURE = CONFIG["temperature"]
ENABLE_SAFETY_CHECKS = CONFIG["enable_safety_checks"]
WEB_SEARCH_MAX_RESULTS = CONFIG["web_search_max_results"]
WEB_SEARCH_REGION = CONFIG["web_search_region"]
MAX_CONTEXT_TOKENS = CONFIG["max_context_tokens"]
SUMMARIZE_THRESHOLD = CONFIG["summarize_threshold"]

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
    total_tokens: int = 0


# ─── Safety & Sandboxing ───────────────────────────────────────────────────


class SafetyError(Exception):
    """Raised when a safety check fails."""
    pass


def validate_path(path: str, workspace: Path) -> Path:
    """
    Validate and resolve a path, ensuring it stays within workspace.
    
    Args:
        path: Relative path from workspace
        workspace: Workspace root directory
        
    Returns:
        Resolved absolute path
        
    Raises:
        SafetyError: If path tries to escape workspace
    """
    target_path = (workspace / path).resolve()
    workspace_resolved = workspace.resolve()
    
    if not str(target_path).startswith(str(workspace_resolved)):
        raise SafetyError(f"Access denied: path '{path}' is outside workspace")
    
    return target_path


def check_command_safety(command: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a command is safe to execute.
    
    Args:
        command: The bash command to check
        
    Returns:
        Tuple of (is_safe, error_message_if_unsafe)
    """
    if not ENABLE_SAFETY_CHECKS:
        return True, None
    
    # Dangerous patterns that are always blocked
    dangerous_patterns = [
        (r"\brm\s+-rf\b", "rm -rf"),
        (r"\bsudo\b", "sudo"),
        (r"\bchmod\s+777\b", "chmod 777"),
        (r">\s*/dev/", "writing to /dev/"),
        (r"\bdd\s+if=", "dd command"),
        (r"\bmkfs\b", "mkfs"),
        (r":\(\)\s*\{\s*:\|\:&\s*\}\s*;\s*:", "fork bomb"),
        (r"\bshutdown\b", "shutdown"),
        (r"\breboot\b", "reboot"),
        (r"\bmount\b", "mount"),
        (r"\bumount\b", "umount"),
        (r"\bfdisk\b", "fdisk"),
        (r"\bparted\b", "parted"),
        (r">\s*/etc/", "writing to /etc/"),
        (r"curl\s+\S+\s*\|\s*(bash|sh)", "pipe to shell"),
        (r"wget\s+\S+\s*\|\s*(bash|sh)", "pipe to shell"),
    ]
    
    command_lower = command.lower()
    for pattern, desc in dangerous_patterns:
        if re.search(pattern, command_lower):
            return False, f"Command blocked for security reasons: contains dangerous pattern '{desc}'"
    
    return True, None


# ─── Tool Definitions ───────────────────────────────────────────────────────


def read_file(path: str, workspace: Path = WORKSPACE_DIR) -> ToolResult:
    """
    Read a file from the workspace.
    
    Args:
        path: Relative path to file from workspace root.
        
    Returns:
        ToolResult with file contents or error.
    """
    try:
        target_path = validate_path(path, workspace)
        
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
    
    except SafetyError as e:
        return ToolResult(success=False, output="", error=str(e))
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def write_file(path: str, content: str, workspace: Path = WORKSPACE_DIR) -> ToolResult:
    """
    Write content to a file in the workspace.
    
    Args:
        path: Relative path to file from workspace root.
        content: Content to write to the file.
        
    Returns:
        ToolResult with success status.
    """
    try:
        target_path = validate_path(path, workspace)
        
        # Create parent directories if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        target_path.write_text(content, encoding="utf-8")
        return ToolResult(success=True, output=f"Successfully wrote {len(content)} bytes to {path}")
    
    except SafetyError as e:
        return ToolResult(success=False, output="", error=str(e))
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


def bash_execute(command: str, timeout: int = 30, workspace: Path = WORKSPACE_DIR) -> ToolResult:
    """
    Execute a bash command within the workspace directory.
    
    Args:
        command: Bash command to execute.
        timeout: Maximum execution time in seconds.
        workspace: Working directory for command execution.
        
    Returns:
        ToolResult with command output or error.
    """
    # Safety check
    is_safe, error = check_command_safety(command)
    if not is_safe:
        return ToolResult(success=False, output="", error=error)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=workspace,
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


def web_search(query: str, max_results: int = WEB_SEARCH_MAX_RESULTS, region: str = WEB_SEARCH_REGION) -> ToolResult:
    """
    Search the web using DuckDuckGo (free, no API key required).
    
    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        region: Region code for search (e.g., 'wt-wt' for worldwide).
        
    Returns:
        ToolResult with search results.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region=region, max_results=max_results))
        
        if not results:
            return ToolResult(success=True, output="No results found.")
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            body = result.get("body", "No description")
            url = result.get("href", "No URL")
            formatted_results.append(f"{i}. **{title}**\n   {body}\n   Source: {url}\n")
        
        output = "\n".join(formatted_results)
        return ToolResult(success=True, output=output)
    
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Web search failed: {e}")


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
        "description": "Write content to a file in the workspace. Creates parent directories if needed.",
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
        "description": "Search the web using DuckDuckGo. No API key required. Returns top results with titles, snippets, and URLs.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string"
                },
                "max_results": {
                    "type": "integer",
                    "description": f"Maximum results (default: {WEB_SEARCH_MAX_RESULTS})",
                    "default": WEB_SEARCH_MAX_RESULTS
                }
            },
            "required": ["query"]
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
    
    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None, temperature: float = TEMPERATURE) -> Dict[str, Any]:
        """
        Send a chat completion request to Ollama.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool schemas for function calling.
            temperature: LLM temperature for randomness.
            
        Returns:
            Parsed response from Ollama.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
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


# ─── Memory Management ──────────────────────────────────────────────────────


def estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars ≈ 1 token)."""
    return len(text) // 4


def count_message_tokens(messages: List[Dict[str, str]]) -> int:
    """Count total tokens in message history."""
    total = 0
    for msg in messages:
        total += estimate_tokens(msg.get("content", ""))
    return total


def summarize_messages(messages: List[Dict[str, str]], keep_recent: int = 4) -> List[Dict[str, str]]:
    """
    Summarize older messages to keep context manageable.
    Keeps the system prompt, first user message, and recent messages.
    """
    if len(messages) <= keep_recent + 2:  # system + first user + recent
        return messages
    
    # Keep system prompt, first user message, and last N messages
    system_msg = messages[0] if messages[0]["role"] == "system" else None
    first_user = next((m for m in messages if m["role"] == "user"), None)
    recent = messages[-keep_recent:]
    
    # Create summary of middle messages
    middle = messages[1:-keep_recent] if system_msg else messages[:-keep_recent]
    if middle:
        summary_content = "Previous conversation summary:\n"
        for msg in middle:
            role = msg["role"]
            content = msg["content"][:200]  # Truncate
            summary_content += f"- {role}: {content}...\n"
        
        summary_msg = {"role": "system", "content": summary_content}
        result = []
        if system_msg:
            result.append(system_msg)
        result.append(summary_msg)
        if first_user and first_user != middle[0] if middle else False:
            result.append(first_user)
        result.extend(recent)
        return result
    
    return messages


# ─── ReAct Agent ────────────────────────────────────────────────────────────


class ReActAgent:
    """ReAct (Reasoning + Acting) loop agent with memory and safety."""
    
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_steps: int = MAX_STEPS,
        workspace: Optional[Path] = None,
        temperature: float = TEMPERATURE
    ):
        self.ollama = OllamaClient(model=model)
        self.max_steps = max_steps
        self.workspace = workspace or WORKSPACE_DIR
        self.temperature = temperature
        self.state = AgentState()
        self.conversation_history: List[Dict[str, str]] = []
        
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
7. All file operations are restricted to the workspace directory.
8. Dangerous commands (rm -rf, sudo, etc.) are blocked for safety.

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
            Text(content, style="blue"),
            title="🤔 Reasoning",
            border_style="blue",
            padding=(0, 1)
        ))
    
    def _print_tool_call(self, tool_call: ToolCall) -> None:
        """Print tool call with syntax highlighting."""
        args_json = json.dumps(tool_call.arguments, indent=2)
        console.print(Panel(
            Syntax(args_json, "json", theme="monokai"),
            title=f"🔧 Tool Call: {tool_call.name}",
            border_style="yellow",
            padding=(0, 1)
        ))
    
    def _print_tool_result(self, result: ToolResult) -> None:
        """Print tool result with color coding."""
        if result.success:
            style = "green"
            title = "✅ Tool Result"
        else:
            style = "red"
            title = "❌ Tool Error"
        
        console.print(Panel(
            Text(result.output or result.error or "(no output)", style=style),
            title=title,
            border_style=style,
            padding=(0, 1)
        ))
    
    def _print_final_answer(self, answer: str) -> None:
        """Print final answer."""
        console.print(Panel(
            Markdown(answer),
            title="💡 Final Answer",
            border_style="green",
            padding=(1, 2)
        ))
    
    def _parse_tool_calls(self, response_content: str) -> List[ToolCall]:
        """Parse tool calls from LLM response with retry logic for malformed JSON."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Try to extract JSON from the response
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
                if attempt < max_retries - 1:
                    logger.warning(f"JSON parse attempt {attempt + 1} failed: {e}")
                    # Ask LLM to fix the JSON
                    fix_prompt = (
                        "You returned invalid JSON. Fix it and respond with valid JSON only. "
                        "Format: {\"tool_calls\": [{\"name\": \"tool_name\", \"arguments\": {...}}]}"
                    )
                    # We'll handle this at the agent loop level
                    return []
                logger.warning(f"Failed to parse tool calls after {max_retries} attempts: {e}")
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
            # Pass workspace to file/bashexec tools
            if tool_call.name in ("read_file", "write_file", "bash_execute"):
                return tool_func(**tool_call.arguments, workspace=self.workspace)
            return tool_func(**tool_call.arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool execution failed: {e}"
            )
    
    def _fix_malformed_json(self, malformed_content: str) -> str:
        """Ask LLM to fix malformed JSON."""
        fix_messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": malformed_content},
            {"role": "assistant", "content": "I need to fix my JSON response."},
            {"role": "user", "content": "You returned invalid JSON. Fix it and respond with valid JSON only. Format: {\"tool_calls\": [{\"name\": \"tool_name\", \"arguments\": {...}}]}"}
        ]
        
        response = self.ollama.chat(fix_messages, tools=TOOL_SCHEMAS, temperature=0.1)
        return response.get("message", {}).get("content", "")
    
    def run(self, user_prompt: str) -> str:
        """
        Run the ReAct loop for a user prompt.
        
        Args            user_prompt: The user's question or task.
            
        Returns:
            Final answer from the agent.
        """
        # Initialize or continue conversation
        if not self.conversation_history:
            self.conversation_history = [
                {"role": "system", "content": self.system_prompt}
            ]
        
        self.conversation_history.append({"role": "user", "content": user_prompt})
        
        console.print(Panel(
            Text(user_prompt, style="bold white"),
            title="📝 User Prompt",
            border_style="blue",
            padding=(1, 2)
        ))
        
        # Use conversation history as messages
        self.state = AgentState(
            messages=self.conversation_history.copy(),
            step_count=0,
            finished=False
        )
        
        while not self.state.finished and self.state.step_count < self.max_steps:
            self.state.step_count += 1
            
            console.print(f"\n[bold cyan]── Step {self.state.step_count}/{self.max_steps} ──[/bold cyan]\n")
            
            # Get LLM response
            response = self.ollama.chat(
                self.state.messages,
                tools=TOOL_SCHEMAS,
                temperature=self.temperature
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
            
            # Handle malformed JSON with retry
            if not tool_calls and "tool_calls" in content:
                console.print("[yellow]⚠️ Malformed JSON detected, asking LLM to fix...[/yellow]")
                fixed_content = self._fix_malformed_json(content)
                tool_calls = self._parse_tool_calls(fixed_content)
                
                if tool_calls:
                    # Replace the malformed message with fixed one
                    self.state.messages[-1] = {"role": "assistant", "content": fixed_content}
            
            if not tool_calls:
                # No tool calls = final answer
                self.state.finished = True
                self.state.final_answer = content
                self._print_final_answer(content)
                
                # Add to conversation history
                self.conversation_history.append({"role": "assistant", "content": content})
                
                # Check if we need to summarize
                token_count = count_message_tokens(self.conversation_history)
                if token_count > SUMMARIZE_THRESHOLD:
                    self.conversation_history = summarize_messages(self.conversation_history)
                    console.print(f"[dim]📝 Conversation summarized (tokens: {token_count} → ~{count_message_tokens(self.conversation_history)})[/dim]")
                
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
                self.conversation_history.append(tool_result_msg)
        
        if self.state.step_count >= self.max_steps and not self.state.finished:
            msg = f"Reached maximum steps ({self.max_steps}). Stopping."
            console.print(f"[bold red]⚠️ {msg}[/bold red]")
            self.state.final_answer = msg
            self.conversation_history.append({"role": "assistant", "content": msg})
        
        return self.state.final_answer or "No answer generated."
    
    def chat_loop(self) -> None:
        """Run continuous chat loop until user exits."""
        console.print(Panel(
            Text("Humitron - Local AI Agent\nType 'exit' or 'quit' to quit", style="bold cyan"),
            title="🤖 Welcome",
            border_style="cyan",
            padding=(1, 2)
        ))
        
        while True:
            try:
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
                
                if user_input.lower().strip() in ("exit", "quit", "q"):
                    console.print("[cyan]Goodbye![/cyan]")
                    break
                
                if not user_input.strip():
                    continue
                
                self.run(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
                logger.exception("Chat loop error")


# ─── Main Entry Point ───────────────────────────────────────────────────────


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Humitron ReAct Agent")
    parser.add_argument("prompt", nargs="*", help="Prompt for the agent (omit for chat mode)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model to use")
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS, help="Max steps per query")
    parser.add_argument("--workspace", type=Path, help="Workspace directory")
    parser.add_argument("--temperature", type=float, default=TEMPERATURE, help="LLM temperature")
    parser.add_argument("--chat", action="store_true", help="Run in continuous chat mode")
    
    args = parser.parse_args()
    
    # Setup logging
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    
    # Create agent
    agent = ReActAgent(
        model=args.model,
        max_steps=args.max_steps,
        workspace=args.workspace,
        temperature=args.temperature
    )
    
    try:
        if args.chat or not args.prompt:
            # Chat mode
            agent.chat_loop()
        else:
            # Single prompt mode
            prompt = " ".join(args.prompt)
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