#!/usr/bin/env python3
"""
Humitron Agent - ReAct Loop Implementation with Safety & Memory

A local-first AI agent that uses Ollama for LLM inference and executes tools
in a ReAct (Reasoning + Acting) loop pattern with strict sandboxing.
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import yaml
from pydantic import BaseModel, Field, ValidationError
from loguru import logger

from humitron.config.loader import get_config, Config
from humitron.models.tools import ToolCall, ToolResult
from humitron.models.agent import AgentState, AgentMessage
from humitron.tools.registry import TOOLS, TOOL_SCHEMAS
from humitron.memory.conversation import ConversationMemory
from humitron.utils.safety import is_command_dangerous
from humitron.utils.logging import get_logger

logger = get_logger(__name__)


class OllamaClient:
    """Client for communicating with local Ollama instance."""
    
    def __init__(self, base_url: str = None, model: str = None):
        """Initialize Ollama client.
        
        Args:
            base_url: Ollama base URL. Defaults to config value.
            model: Model name. Defaults to config value.
        """
        config = get_config()
        self.base_url = (base_url or config.ollama_base_url).rstrip("/")
        self.model = model or config.model
        self.client = httpx.Client(timeout=120.0)
        logger.debug(f"Initialized Ollama client: {self.base_url}, model={self.model}")
    
    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Send a chat completion request to Ollama.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool schemas for function calling.
            
        Returns:
            Parsed response from Ollama.
            
        Raises:
            ConnectionError: If cannot connect to Ollama.
            RuntimeError: If Ollama API returns an error.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": get_config().temperature,
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
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Is Ollama running? Try: ollama serve"
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"Ollama API error: {e.response.status_code} - {e.response.text}") from e


class ReActAgent:
    """ReAct (Reasoning + Acting) loop agent with safety and memory."""
    
    def __init__(
        self,
        model: str = None,
        max_steps: int = None,
        workspace: Optional[Path] = None,
        temperature: float = None
    ):
        """Initialize ReAct agent.
        
        Args:
            model: Ollama model to use. Defaults to config.
            max_steps: Maximum steps per query. Defaults to config.
            workspace: Workspace directory. Defaults to config.
            temperature: LLM temperature. Defaults to config.
        """
        config = get_config()
        self.model = model or config.model
        self.max_steps = max_steps or config.max_steps
        self.temperature = temperature or config.temperature
        
        if workspace:
            self.workspace_dir = workspace.resolve()
        else:
            self.workspace_dir = Path(config.workspace_path).resolve()
        
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        self.ollama = OllamaClient(model=self.model)
        self.ollama.client.timeout = 120.0
        self.memory = ConversationMemory(max_tokens=config.max_tokens_per_call)
        
        # System prompt that teaches the agent how to use tools
        self.system_prompt = self._build_system_prompt()
        
        # Initialize memory with system prompt
        self.memory.add_message("system", self.system_prompt)
        logger.info(f"Initialized ReActAgent: model={self.model}, max_steps={self.max_steps}")
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with tool descriptions.
        
        Returns:
            System prompt string.
        """
        tool_descriptions = "\n".join([
            f"- {t['name']}: {t['description']}"
            for t in TOOL_SCHEMAS
        ])
        
        return f"""You are Humitron, a helpful AI assistant that can use tools to accomplish tasks.

You have access to the following tools:
{tool_descriptions}

WORKSPACE: {self.workspace_dir}

SAFETY RULES (CRITICAL - NEVER VIOLATE):
1. ALL file operations are restricted to the workspace directory: {self.workspace_dir}
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
    
    def _parse_tool_calls(self, response_content: str) -> List[ToolCall]:
        """Parse tool calls from LLM response with retry logic for malformed JSON.
        
        Args:
            response_content: Raw response content from LLM.
            
        Returns:
            List of parsed ToolCall objects.
        """
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
        """Execute a tool call and return result.
        
        Args:
            tool_call: ToolCall to execute.
            
        Returns:
            ToolResult from execution.
        """
        tool_func = TOOLS.get(tool_call.name)
        if not tool_func:
            logger.error(f"Unknown tool: {tool_call.name}")
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {tool_call.name}"
            )
        
        try:
            logger.debug(f"Executing tool: {tool_call.name} with args: {tool_call.arguments}")
            return tool_func(**tool_call.arguments)
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_call.name}: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"Tool execution failed: {e}"
            )
    
    def _handle_json_parse_error(self) -> str:
        """Send error back to LLM and get corrected JSON.
        
        Returns:
            Corrected response content from LLM.
        """
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
        """Run the ReAct loop for a user prompt.
        
        Args:
            user_prompt: The user's question or task.
            
        Returns:
            Final answer from the agent.
            
        Raises:
            ConnectionError: If Ollama is not available.
            RuntimeError: If an unexpected error occurs.
        """
        # Add user prompt to memory
        self.memory.add_message("user", user_prompt)
        
        logger.info(f"Starting ReAct loop for prompt: {user_prompt[:100]}...")
        
        step = 0
        while step < self.max_steps:
            step += 1
            
            logger.debug(f"Step {step}/{self.max_steps}")
            
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
                    logger.warning("Response looks like JSON but couldn't parse. Asking for correction...")
                    content = self._handle_json_parse_error()
                    tool_calls = self._parse_tool_calls(content)
                    if not tool_calls:
                        # Give up, treat as final answer
                        self.memory.messages[-1] = {"role": "assistant", "content": content}
                        logger.info("Returning final answer (after JSON correction attempt)")
                        return content
                else:
                    logger.info("Returning final answer")
                    return content
            
            # Execute each tool call
            for tool_call in tool_calls:
                result = self._execute_tool(tool_call)
                
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
        logger.warning(msg)
        return msg