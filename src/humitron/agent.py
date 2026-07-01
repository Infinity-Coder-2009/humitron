#!/usr/bin/env python3
"""
Humitron Agent - ReAct Loop Implementation with Multi-Provider LLM Support

A local-first AI agent that uses Ollama for local inference or cloud providers
(OpenAI, Anthropic, OpenRouter) with a ReAct (Reasoning + Acting) loop pattern.
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
from humitron.llm import create_provider, LLMProvider, LLMResponse, LLMMessage, estimate_cost

logger = get_logger(__name__)


class ReActAgent:
    """ReAct (Reasoning + Acting) loop agent with safety and memory."""

    def __init__(
        self,
        model: str = None,
        max_steps: int = None,
        workspace: Optional[Path] = None,
        temperature: float = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize ReAct agent."""
        config = get_config()
        self.model = model or config.model
        self.max_steps = max_steps or config.max_steps
        self.temperature = temperature or config.temperature
        self.provider_name = provider
        self.api_key = api_key
        self.base_url = base_url

        if workspace:
            self.workspace_dir = workspace.resolve()
        else:
            self.workspace_dir = Path(config.workspace_path).resolve()

        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Create LLM provider
        self.llm: LLMProvider = create_provider(
            model=self.model,
            provider=self.provider_name,
            api_key=self.api_key,
            base_url=self.base_url,
        )

        self.memory = ConversationMemory(max_tokens=config.max_tokens_per_call)

        # System prompt that teaches the agent how to use tools
        self.system_prompt = self._build_system_prompt()

        # Initialize memory with system prompt
        self.memory.add_message("system", self.system_prompt)
        logger.info(f"Initialized ReActAgent: model={self.model}, provider={self.llm.__class__.__name__}, max_steps={self.max_steps}")

    def _build_system_prompt(self) -> str:
        """Build the system prompt with tool descriptions."""
        tool_descriptions = "\n".join([
            f"- {t['name']}: {t['description']}"
            for t in TOOL_SCHEMAS
        ])

        provider_info = f"Provider: {self.llm.__class__.__name__}"
        if hasattr(self.llm, 'model'):
            provider_info += f" ({self.llm.model})"

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
        """Parse tool calls from LLM response with retry logic for malformed JSON."""
        try:
            if "tool_calls" in response_content:
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
        """Send error back to LLM and get corrected JSON."""
        error_msg = "You returned invalid JSON. Fix it and respond with valid JSON only."
        self.memory.add_message("user", error_msg)

        messages = [LLMMessage(role=m["role"], content=m["content"]) for m in self.memory.get_messages()]
        response = self.llm.chat(messages, tools=TOOL_SCHEMAS, temperature=self.temperature)

        content = response.content
        self.memory.add_message("assistant", content)
        return content

    def run(self, user_prompt: str) -> Tuple[str, Dict]:
        """
        Run the ReAct loop for a user prompt.

        Returns:
            Tuple of (final_answer, cost_info)
        """
        # Add user prompt to memory
        self.memory.add_message("user", user_prompt)

        logger.info(f"Starting ReAct loop for prompt: {user_prompt[:100]}...")

        total_input_tokens = 0
        total_output_tokens = 0
        step = 0

        while step < self.max_steps:
            step += 1

            logger.debug(f"Step {step}/{self.max_steps}")

            # Check if we need to summarize
            if self.memory.should_summarize():
                self.memory.summarize_middle(self.llm)

            # Get LLM response
            messages = [LLMMessage(role=m["role"], content=m["content"]) for m in self.memory.get_messages()]
            response = self.llm.chat(
                messages,
                tools=TOOL_SCHEMAS,
                temperature=self.temperature,
            )

            # Track token usage
            total_input_tokens += response.input_tokens
            total_output_tokens += response.output_tokens

            assistant_message = response.content
            self.memory.add_message("assistant", assistant_message)

            # Check for tool calls
            tool_calls = self._parse_tool_calls(assistant_message)

            # If no tool calls found but content looks like JSON, try parsing again
            if not tool_calls and assistant_message.strip().startswith("{"):
                try:
                    data = json.loads(assistant_message)
                    if "name" in data and "arguments" in data:
                        tool_calls = [ToolCall(**data)]
                    elif "tool_calls" in data:
                        tool_calls = [ToolCall(**tc) for tc in data.get("tool_calls", [])]
                except json.JSONDecodeError:
                    pass

            # If still no tool calls, this is the final answer
            if not tool_calls:
                if assistant_message.strip().startswith("{") and "tool_calls" not in assistant_message:
                    logger.warning("Response looks like JSON but couldn't parse. Asking for correction...")
                    assistant_message = self._handle_json_parse_error()
                    tool_calls = self._parse_tool_calls(assistant_message)
                    if not tool_calls:
                        self.memory.messages[-1] = {"role": "assistant", "content": assistant_message}
                        logger.info("Returning final answer (after JSON correction attempt)")
                        cost = estimate_cost(self.model, total_input_tokens, total_output_tokens)
                        return assistant_message, {
                            "total_tokens": total_input_tokens + total_output_tokens,
                            "input_tokens": total_input_tokens,
                            "output_tokens": total_output_tokens,
                            "estimated_cost": cost,
                            "model": self.model,
                        }
                else:
                    logger.info("Returning final answer")
                    cost = estimate_cost(self.model, total_input_tokens, total_output_tokens)
                    return assistant_message, {
                        "total_tokens": total_input_tokens + total_output_tokens,
                        "input_tokens": total_input_tokens,
                        "output_tokens": total_output_tokens,
                        "estimated_cost": cost,
                        "model": self.model,
                    }

            # Execute each tool call
            for tool_call in tool_calls:
                result = self._execute_tool(tool_call)

                # Add tool result to conversation memory
                tool_result_msg = {
                    "role": "tool",
                    "content": json.dumps({
                        "name": tool_call.name,
                        "result": result.output if result.success else result.error,
                        "success": result.success,
                    })
                }
                self.memory.add_message("tool", tool_result_msg["content"])

        # Max steps reached
        msg = f"Reached maximum steps ({self.max_steps}). Stopping."
        logger.warning(msg)
        cost = estimate_cost(self.model, total_input_tokens, total_output_tokens)
        return msg, {
            "total_tokens": total_input_tokens + total_output_tokens,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "estimated_cost": cost,
            "model": self.model,
        }

    async def run_stream(self, user_prompt: str):
        """
        Run the ReAct loop with streaming responses.

        Yields:
            Dict with type and data for SSE streaming
        """
        self.memory.add_message("user", user_prompt)

        total_input_tokens = 0
        total_output_tokens = 0
        step = 0

        while step < self.max_steps:
            step += 1

            if self.memory.should_summarize():
                self.memory.summarize_middle(self.llm)

            messages = [LLMMessage(role=m["role"], content=m["content"]) for m in self.memory.get_messages()]

            # Stream the response
            full_content = ""
            tool_calls_buffer = None

            async for chunk in self.llm.chat_stream(messages, TOOL_SCHEMAS, self.temperature):
                if chunk.content:
                    full_content += chunk.content
                    yield {"type": "content", "data": {"content": chunk.content}}

                if chunk.tool_calls:
                    tool_calls_buffer = chunk.tool_calls

                total_output_tokens += 1  # Rough estimate per chunk

            if full_content:
                total_input_tokens += sum(len(m.content) // 4 for m in messages)
                self.memory.add_message("assistant", full_content)

            # Parse tool calls from full content
            tool_calls = self._parse_tool_calls(full_content)

            if not tool_calls and full_content.strip().startswith("{"):
                try:
                    data = json.loads(full_content)
                    if "name" in data and "arguments" in data:
                        tool_calls = [ToolCall(**data)]
                    elif "tool_calls" in data:
                        tool_calls = [ToolCall(**tc) for tc in data.get("tool_calls", [])]
                except json.JSONDecodeError:
                    pass

            if not tool_calls:
                cost = estimate_cost(self.model, total_input_tokens, total_output_tokens)
                yield {"type": "done", "data": {"cost": {
                    "total_tokens": total_input_tokens + total_output_tokens,
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                    "estimated_cost": cost,
                    "model": self.model,
                }}}
                return

            # Yield thinking if present
            if full_content and "tool_calls" not in full_content:
                yield {"type": "thinking", "data": {"thinking": full_content}}

            # Execute tools
            for tool_call in tool_calls:
                tool_call_id = f"call_{int(time.time() * 1000)}"
                yield {"type": "tool_call", "data": {
                    "tool_call_id": tool_call_id,
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                }}

                result = self._execute_tool(tool_call)

                yield {"type": "tool_result", "data": {
                    "tool_call_id": tool_call_id,
                    "success": result.success,
                    "result": result.output if result.success else result.error,
                }}

                tool_result_msg = {
                    "role": "tool",
                    "content": json.dumps({
                        "name": tool_call.name,
                        "result": result.output if result.success else result.error,
                        "success": result.success,
                    })
                }
                self.memory.add_message("tool", tool_result_msg["content"])

        # Max steps
        yield {"type": "error", "data": {"message": f"Reached maximum steps ({self.max_steps})"}}

    def close(self):
        """Clean up resources."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.llm.close())
            else:
                loop.run_until_complete(self.llm.close())
        except Exception:
            pass  # Best effort cleanup