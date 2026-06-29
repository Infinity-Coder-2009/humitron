#!/usr/bin/env python3
"""
Humitron Core - ReAct Loop Implementation with Safety & Memory

A local-first AI agent that uses Ollama for LLM inference and executes tools
in a ReAct (Reasoning + Acting) loop pattern with strict sandboxing.
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
from pydantic import BaseModel, Field, ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.prompt import Prompt
from rich.markdown import Markdown
from loguru import logger

# ─── Configuration Loading ─────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "model": "llama3.2",
    "workspace_path": str(Path.cwd()),
    "max_steps": 20,
    "temperature": 0.7,
    "ollama_base_url": "http://localhost:11434",
}

CONFIG_PATH = Path("config.yaml")

console = Console()


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml or return defaults."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                user_config = yaml.safe_load(f) or {}
            # Merge with defaults
            config = {**DEFAULT_CONFIG, **user_config}
            return config
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load config.yaml: {e}[/yellow]")
    return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to config.yaml."""
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


config = load_config()

MODEL = config["model"]
WORKSPACE_DIR = Path(config["workspace_path"]).resolve()
MAX_STEPS = config["max_steps"]
TEMPERATURE = config["temperature"]
OLLAMA_BASE_URL = config["ollama_base_url"]

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


# ─── Safety: Dangerous Command Detection ────────────────────────────────────

# Patterns that are NEVER allowed - these can destroy systems
DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",           # rm -rf /
    r"rm\s+-rf\s+\*",          # rm -rf *
    r"sudo\s+",                # sudo anything
    r"chmod\s+777",            # chmod 777
    r"dd\s+if=",               # dd if= (disk destroyer)
    r"mkfs\s+",                # mkfs (format filesystem)
    r":\(\)\s*\{\s*:\|\:&\s*\}\s*;\s*:",  # fork bomb :(){ :|:& };:
    r"shutdown",               # shutdown
    r"reboot",                 # reboot
    r"halt",                   # halt
    r"poweroff",               # poweroff
    r">\s*/dev/",              # redirect to device
    r"chown\s+-R\s+root",      # chown -R root
    r"chgrp\s+-R\s+root",      # chgrp -R root
]

# Commands that are allowed but with restrictions
ALLOWED_COMMANDS = [
    "ls", "cat", "head", "tail", "grep", "find", "wc", "echo",
    "pwd", "mkdir", "touch", "cp", "mv", "rm",  # rm without -rf /
    "python", "python3", "pip", "npm", "node",
    "git", "curl", "wget", "tar", "gzip", "gunzip",
    "cd", "which", "whereis", "man", "info",
]

# Compile dangerous patterns for performance
DANGEROUS_REGEX = [re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS]


def is_command_dangerous(command: str) -> Tuple[bool, str]:
    """
    Check if a command contains dangerous patterns.
    
    Returns:
        Tuple of (is_dangerous, reason)
    """
    command = command.strip()
    
    # Check each dangerous pattern
    for pattern in DANGEROUS_REGEX:
        if pattern.search(command):
            return True, f"Command blocked for security reasons: matches dangerous pattern"
    
    # Additional check: rm -rf on root or home
    if re.search(r"rm\s+-rf\s+(/|~|\$HOME|\.)", command):
        return True, "Command blocked for security reasons: rm -rf on sensitive paths"
    
    # Check for command chaining that could hide dangerous commands
    if "&&" in command or "||" in command or ";" in command:
        # Split and check each part
        parts = re.split(r"[;&|]", command)
        for part in parts:
            dangerous, reason = is_command_dangerous(part.strip())
            if dangerous:
                return True, reason
    
    return False, ""


def is_path_in_workspace(path: Path) -> bool:
    """Check if a path is within the workspace directory."""
    try:
        resolved = path.resolve()
        return str(resolved).startswith(str(WORKSPACE_DIR))
    except Exception:
        return False


# ─── Tool Implementations ───────────────────────────────────────────────────


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


def web_search(query: str, max_results: int = 5) -> ToolResult:
    """
    Search the web using DuckDuckGo HTML (free, no API key).
    
    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        
    Returns:
        ToolResult with search results or error.
    """
    try:
        import urllib.parse
        import urllib.request
        from html.parser import HTMLParser
        
        # Simple HTML parser to extract results
        class DDGParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self.in_result = False
                self.current = {}
                self.capture_text = False
                self.tag_stack = []
            
            def handle_starttag(self, tag, attrs):
                self.tag_stack.append(tag)
                attrs_dict = dict(attrs)
                
                if tag == "a" and attrs_dict.get("class") == "result__snippet":
                    self.in_result = True
                    self.current = {"url": attrs_dict.get("href", "")}
                elif tag == "a" and attrs_dict.get("class") == "result__url":
                    self.capture_text = True
                    self.current["title"] = ""
            
            def handle_endtag(self, tag):
                if self.tag_stack:
                    self.tag_stack.pop()
                if tag == "a" and self.in_result:
                    self.in_result = False
                    if self.current.get("snippet"):
                        self.results.append(self.current)
                        self.current = {}
                elif tag == "a" and self.capture_text:
                    self.capture_text = False
            
            def handle_data(self, data):
                if self.in_result and data.strip():
                    self.current["snippet"] = data.strip()
                elif self.capture_text and data.strip():
                    self.current["title"] = data.strip()
        
        # Build search URL
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        # Make request with a browser-like user agent
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8")
        
        # Parse results
        parser = DDGParser()
        parser.feed(html)
        
        if not parser.results:
            # Fallback: try to extract from page text
            return ToolResult(
                success=True,
                output=f"Search completed for '{query}'. No structured results found. Try a different query."
            )
        
        # Format results
        output_lines = [f"Search results for: {query}\n"]
        for i, result in enumerate(parser.results[:max_results], 1):
            title = result.get("title", "No title")
            snippet = result.get("snippet", "No snippet")
            url = result.get("url", "No URL")
            output_lines.append(f"{i}. {title}")
            output_lines.append(f"   {snippet}")
            output_lines.append(f"   URL: {url}\n")
        
        return ToolResult(success=True, output="\n".join(output_lines))
    
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Web search failed: {str(e)}")


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


# ─── Ollama Client ──────────────────────────────────────────────────────────


class OllamaClient:
    """Client for communicating with local Ollama instance."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = MODEL):
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


class ConversationMemory:
    """Manages conversation history with summarization for long contexts."""
    
    def __init__(self, max_tokens: int = 8000):
        self.messages: List[Dict[str, str]] = []
        self.max_tokens = max_tokens
        self.summary_count = 0
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to history."""
        self.messages.append({"role": role, "content": content})
    
    def get_messages(self) -> List[Dict[str, str]]:
        """Get all messages."""
        return self.messages.copy()
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)."""
        return len(text) // 4
    
    def total_tokens(self) -> int:
        """Estimate total tokens in conversation."""
        return sum(self.estimate_tokens(m.get("content", "")) for m in self.messages)
    
    def should_summarize(self) -> bool:
        """Check if conversation needs summarization."""
        return self.total_tokens() > self.max_tokens
    
    def summarize_middle(self, ollama_client: OllamaClient) -> None:
        """Summarize the middle portion of conversation to reduce tokens."""
        if len(self.messages) < 6:
            return  # Not enough to summarize
        
        # Keep first 2 (system + first user) and last 2 messages
        # Summarize the middle
        keep_start = 2
        keep_end = 2
        middle = self.messages[keep_start:-keep_end]
        
        if not middle:
            return
        
        # Create summary prompt
        conversation_text = "\n".join(
            f"{m['role']}: {m['content'][:500]}" for m in middle
        )
        
        summary_prompt = f"""Summarize this conversation history concisely, preserving key facts, decisions, and context:

{conversation_text}

Provide a brief summary:"""
        
        try:
            response = ollama_client.chat([
                {"role": "system", "content": "You are a helpful assistant that summarizes conversations."},
                {"role": "user", "content": summary_prompt}
            ])
            summary = response.get("message", {}).get("content", "Summary unavailable")
            
            # Replace middle with summary
            self.summary_count += 1
            summary_msg = {
                "role": "system",
                "content": f"[Conversation Summary #{self.summary_count}]: {summary}"
            }
            self.messages = self.messages[:keep_start] + [summary_msg] + self.messages[-keep_end:]
            
            console.print(f"[dim]📝 Conversation summarized (tokens reduced)[/dim]")
        except Exception as e:
            logger.warning(f"Failed to summarize conversation: {e}")


# ─── ReAct Agent ────────────────────────────────────────────────────────────


class ReActAgent:
    """ReAct (Reasoning + Acting) loop agent with safety and memory."""
    
    def __init__(
        self,
        model: str = MODEL,
        max_steps: int = MAX_STEPS,
        workspace: Optional[Path] = None,
        temperature: float = TEMPERATURE
    ):
        global WORKSPACE_DIR
        WORKSPACE_DIR = workspace or WORKSPACE_DIR
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        
        self.ollama = OllamaClient(model=model)
        self.ollama.client.timeout = 120.0
        self.max_steps = max_steps
        self.memory = ConversationMemory(max_tokens=8000)
        self.temperature = temperature
        
        # System prompt that teaches the agent how to use tools
        self.system_prompt = self._build_system_prompt()
        
        # Initialize memory with system prompt
        self.memory.add_message("system", self.system_prompt)
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with tool descriptions."""
        tool_descriptions = "\n".join([
            f"- {t['name']}: {t['description']}"
            for t in TOOL_SCHEMAS
        ])
        
        return f"""You are Humitron, a helpful AI assistant that can use tools to accomplish tasks.

You have access to the following tools:
{tool_descriptions}

WORKSPACE: {WORKSPACE_DIR}

SAFETY RULES (CRITICAL - NEVER VIOLATE):
1. ALL file operations are restricted to the workspace directory: {WORKSPACE_DIR}
2. NEVER attempt to access files outside the workspace
3. NEVER use dangerous commands: rm -rf /, sudo, chmod 777, dd, mkfs, fork bombs, shutdown
4. The system will BLOCK any dangerous command automatically

WORKFLOW:
1. Think step by step. Show your reasoning before each tool call.
2. Use tools when you need information or need to perform actions.
3. Tool calls must be in the specified JSON format.
4. After each tool result, continue reasoning or provide the final answer.
5. Maximum {self.max_steps} steps per task.
6. When you have enough information, provide a clear final answer without calling more tools.
7. All file operations are restricted to the workspace directory.
8. Dangerous commands (rm -rf, sudo, etc.) are blocked for safety.

TOOL CALL FORMAT (you MUST respond with valid JSON only when calling tools):
{{
  "tool_calls": [
    {{
      "name": "tool_name",
      "arguments": {{"param": "value"}}
    }}
  ]
}}

If you don't need to call a tool, just respond normally with your final answer.

IMPORTANT: If you need to call a tool, respond ONLY with the JSON object above. No extra text, no markdown, no explanation - just the JSON.
"""
    
    def _print_thinking(self, content: str) -> None:
        """Print agent's reasoning in blue."""
        console.print(Panel(
            Text(content, style="blue"),
            title="🧠 Reasoning",
            border_style="blue",
            padding=(0, 1)
        ))
    
    def _print_tool_call(self, tool_call: ToolCall) -> None:
        """Print tool call in yellow with syntax highlighting."""
        args_json = json.dumps(tool_call.arguments, indent=2)
        console.print(Panel(
            Syntax(args_json, "json", theme="monokai"),
            title=f"🔧 Tool Call: {tool_call.name}",
            border_style="yellow",
            padding=(0, 1)
        ))
    
    def _print_tool_result(self, result: ToolResult) -> None:
        """Print tool result in green (success) or red (error)."""
        if result.success:
            style = "green"
            title = "✅ Tool Output"
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
        """Print final answer in bold white."""
        console.print(Panel(
            Markdown(answer),
            title="💬 Final Answer",
            border_style="green",
            padding=(1, 2)
        ))
    
    )
    
    def _print_error(self, error: str) -> None:
        """Print error in red."""
        console.print(Panel(
            Text(error, style="bold red"),
            title="⚠️ Error",
            border_style="red",
            padding=(1, 2)
        ))
    
    def _parse_tool_calls(self, response_content: str) -> List[ToolCall]:
        """Parse tool calls from LLM response with retry logic for malformed JSON."""
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
        except (json.JSONDecodeError, KeyError, TypeError, ValidationError) as e:
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
    
    def _handle_json_parse_error(self) -> str:
        """Send error back to LLM and get corrected JSON."""
        error_msg = "You returned invalid JSON. Fix it and respond with valid JSON only."
        self.memory.add_message("user", error_msg)
        
        response = self.ollama.chat(
            self.memory.get_messages(),
            tools=TOOL_SCHEMAS
        )
        
        content = response.get("message", {}).get("content", "")
        self.memory.add_message("assistant", content)
        return content
    
    def run(self, user_prompt: str) -> str:
        """
        Run the ReAct loop for a user prompt.
        
        Args:
            user_prompt: The user's question or task.
            
        Returns:
            Final answer from the agent.
        """
        # Add user prompt to memory
        self.memory.add_message("user", user_prompt)
        
        console.print(Panel(
            Text(user_prompt, style="bold white"),
            title="📝 User Prompt",
            border_style="blue",
            padding=(1, 2)
        ))
        
        step = 0
        while step < self.max_steps:
            step += 1
            
            console.print(f"\n[bold cyan]── Step {step}/{self.max_steps} ──[/bold cyan]\n")
            
            # Check if we need to summarize
            if self.memory.should_summarize():
                self.memory.summarize_middle(self.ollama)
            
            # Get LLM response
            response = self.ollama.chat(
                self.memory.get_messages(),
                tools=TOOL_SCHEMAS
            )
            
            assistant_message = response.get("message", {})
            content = assistant_message.get("content", "")
            
            # Add to memory
            self.memory.add_message("assistant", content)
            
            # Check for tool calls
            tool_calls = self._parse_tool_calls(content)
            
            # If no tool calls found but content looks like JSON, try parsing again
            if not tool_calls and content.strip().startswith("{"):
                # Maybe it's a direct tool call without "tool_calls" wrapper
                try:
                    data = json.loads(content)
                    if "name" in data and "arguments" in data:
                        tool_calls = [ToolCall(**data)]
                    elif "tool_calls" in data:
                        tool_calls = [ToolCall(**tc) for tc in data.get("tool_calls", [])]
                except json.JSONDecodeError:
                    pass
            
            # If still no tool calls, this is the final answer
            if not tool_calls:
                # But if it looks like malformed JSON, ask for correction
                if content.strip().startswith("{") and "tool_calls" not in content:
                    console.print("[yellow]⚠️ Response looks like JSON but couldn't parse. Asking for correction...[/yellow]")
                    content = self._handle_json_parse_error()
                    tool_calls = self._parse_tool_calls(content)
                    if not tool_calls:
                        # Give up, treat as final answer
                        self.memory.messages[-1] = {"role": "assistant", "content": content}
                        self._print_final_answer(content)
                        return content
                else:
                    self._print_final_answer(content)
                    return content
            
            # Print reasoning (content before tool calls)
            if content and "tool_calls" not in content:
                self._print_thinking(content)
            
            # Execute each tool call
            for tool_call in tool_calls:
                self._print_tool_call(tool_call)
                result = self._execute_tool(tool_call)
                self._print_tool_result(result)
                
                # Add tool result to conversation memory
                tool_result_msg = {
                    "role": "tool",
                    "content": json.dumps({
                        "name": tool_call.name,
                        "result": result.output if result.success else result.error,
                        "success": result.success
                    })
                }
                self.memory.add_message("tool", tool_result_msg["content"])
        
        # Max steps reached
        msg = f"Reached maximum steps ({self.max_steps}). Stopping."
        self._print_error(msg)
        return msg


# ─── Interactive Chat Loop ──────────────────────────────────────────────────


def run_chat_loop(agent: ReActAgent) -> None:
    """Run continuous chat loop until user types 'exit'."""
    console.print(Panel(
        Markdown("""
# 🤖 Humitron - Local AI Agent

**Commands:**
- Type your question or task
- Type `exit` or `quit` to leave
- Type `clear` to reset conversation history
- Type `config` to show current configuration
"""),
        title="Welcome to Humitron",
        border_style="cyan",
        padding=(1, 2)
    ))
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            
            if user_input.lower().strip() in ("exit", "quit"):
                console.print("[yellow]👋 Goodbye![/yellow]")
                break
            
            if user_input.lower().strip() == "clear":
                agent.memory = ConversationMemory()
                agent.memory.add_message("system", agent.system_prompt)
                console.print("[green]✨ Conversation history cleared.[/green]")
                continue
            
            if user_input.lower().strip() == "config":
                console.print(Panel(
                    Syntax(yaml.dump(config), "yaml", theme="monokai"),
                    title="⚙️ Current Configuration",
                    border_style="cyan"
                ))
                continue
            
            if not user_input.strip():
                continue
            
            agent.run(user_input)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
        except EOFError:
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            logger.exception("Chat loop error")


# ─── Main Entry Point ───────────────────────────────────────────────────────


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Humitron ReAct Agent")
    parser.add_argument("prompt", nargs="*", help="Prompt for the agent (optional, starts chat loop if omitted)")
    parser.add_argument("--model", default=MODEL, help="Ollama model to use")
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS, help="Max steps per query")
    parser.add_argument("--workspace", type=Path, help="Workspace directory")
    parser.add_argument("--temperature", type=float, default=TEMPERATURE, help="LLM temperature")
    parser.add_argument("--no-chat", action="store_true", help="Run single prompt and exit (no chat loop)")
    
    args = parser.parse_args()
    
    # Create agent
    agent = ReActAgent(
        model=args.model,
        max_steps=args.max_steps,
        workspace=args.workspace,
        temperature=args.temperature
    )
    
    # If prompt provided, run single query
    if args.prompt:
        prompt = " ".join(args.prompt)
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
    else:
        # Run interactive chat loop
        try:
            run_chat_loop(agent)
        except ConnectionError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            console.print("[yellow]Make sure Ollama is running: [bold]ollama serve[/bold][/yellow]")
            sys.exit(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Goodbye![/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            logger.exception("Chat error")
            sys.exit(1)


if __name__ == "__main__":
    main()