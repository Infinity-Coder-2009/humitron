#!/usr/bin/env python3
"""
LLM Provider Abstraction for Humitron.

Supports multiple LLM backends with a unified interface:
- Ollama (local)
- OpenAI (cloud)
- Anthropic (cloud)
- OpenRouter (cloud gateway)
"""

import asyncio
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from pydantic import BaseModel


@dataclass
class LLMResponse:
    """Unified response from any LLM provider."""
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    raw_response: Optional[Dict] = None


@dataclass
class LLMMessage:
    """Unified message format."""
    role: str  # system, user, assistant, tool
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)

    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> LLMResponse:
        """Send a chat completion request."""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[LLMResponse, None]:
        """Stream chat completion."""
        pass

    async def close(self):
        await self.client.aclose()

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 chars per token."""
        return max(1, len(text) // 4)

    def _count_message_tokens(self, messages: List[LLMMessage]) -> int:
        total = 0
        for m in messages:
            total += self._estimate_tokens(m.content)
            total += 4  # role overhead
            if m.tool_calls:
                total += self._estimate_tokens(json.dumps(m.tool_calls))
        return total


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        super().__init__(model=model, base_url=base_url.rstrip("/"))

    async def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "options": {"temperature": temperature},
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            resp = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

            msg = data.get("message", {})
            content = msg.get("content", "")

            # Parse tool calls from Ollama format
            tool_calls = None
            if "tool_calls" in msg:
                tool_calls = msg["tool_calls"]

            input_tokens = self._count_message_tokens(messages)
            output_tokens = self._estimate_tokens(content)

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=self.model,
                raw_response=data,
            )
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to Ollama at {self.base_url}. Is it running?") from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama API error: {e.response.status_code} - {e.response.text}") from e

    async def chat_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[LLMResponse, None]:
        # For now, yield single response (Ollama streaming is more complex)
        resp = await self.chat(messages, tools, temperature, stream=False)
        yield resp


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (GPT-4, GPT-3.5, etc.)."""

    def __init__(
        self,
        model: str = "gpt-4-turbo",
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
    ):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key.")
        super().__init__(model=model, api_key=api_key, base_url=base_url.rstrip("/"))
        self.client.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def _convert_tools(self, tools: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """Convert our tool format to OpenAI function calling format."""
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in tools
        ]

    async def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }

        # Add tool calls if present in messages
        for m in messages:
            if m.tool_calls:
                payload["messages"][-1]["tool_calls"] = m.tool_calls
            if m.tool_call_id:
                payload["messages"][-1]["tool_call_id"] = m.tool_call_id

        openai_tools = self._convert_tools(tools)
        if openai_tools:
            payload["tools"] = openai_tools
            payload["tool_choice"] = "auto"

        try:
            resp = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

            choice = data["choices"][0]
            msg = choice["message"]
            content = msg.get("content", "") or ""

            tool_calls = None
            if msg.get("tool_calls"):
                tool_calls = [
                    {
                        "name": tc["function"]["name"],
                        "arguments": json.loads(tc["function"]["arguments"]),
                    }
                    for tc in msg["tool_calls"]
                ]

            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", self._count_message_tokens(messages))
            output_tokens = usage.get("completion_tokens", self._estimate_tokens(content))

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=self.model,
                raw_response=data,
            )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"OpenAI API error: {e.response.status_code} - {e.response.text}") from e

    async def chat_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[LLMResponse, None]:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": True,
        }

        openai_tools = self._convert_tools(tools)
        if openai_tools:
            payload["tools"] = openai_tools
            payload["tool_choice"] = "auto"

        async with self.client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        choice = data["choices"][0]
                        delta = choice.get("delta", {})

                        content = delta.get("content", "")
                        if content:
                            yield LLMResponse(
                                content=content,
                                model=self.model,
                            )

                        # Handle tool calls in stream (simplified)
                        if delta.get("tool_calls"):
                            # Tool calls streaming is complex; defer to non-stream for now
                            pass

                    except json.JSONDecodeError:
                        pass


class AnthropicProvider(LLMProvider):
    """Anthropic API provider (Claude 3 Opus, Sonnet, Haiku)."""

    def __init__(
        self,
        model: str = "claude-3-sonnet-20240229",
        api_key: Optional[str] = None,
        base_url: str = "https://api.anthropic.com/v1",
    ):
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key.")
        super().__init__(model=model, api_key=api_key, base_url=base_url.rstrip("/"))
        self.client.headers.update({
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        })

    def _convert_tools(self, tools: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """Convert to Anthropic tool format."""
        if not tools:
            return None
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"],
            }
            for t in tools
        ]

    def _convert_messages(self, messages: List[LLMMessage]) -> tuple:
        """Convert messages to Anthropic format (system prompt separate)."""
        system = ""
        anthropic_messages = []

        for m in messages:
            if m.role == "system":
                system += m.content + "\n"
            elif m.role == "tool":
                # Tool results are user messages with tool_result content
                try:
                    tool_data = json.loads(m.content)
                    anthropic_messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_data.get("tool_call_id", "unknown"),
                                "content": tool_data.get("result", ""),
                            }
                        ],
                    })
                except json.JSONDecodeError:
                    anthropic_messages.append({"role": "user", "content": m.content})
            else:
                anthropic_messages.append({"role": m.role, "content": m.content})

        return system.strip(), anthropic_messages

    async def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> LLMResponse:
        system, anthropic_messages = self._convert_messages(messages)

        payload = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": 4096,
            "temperature": temperature,
            "stream": stream,
        }

        if system:
            payload["system"] = system

        anthropic_tools = self._convert_tools(tools)
        if anthropic_tools:
            payload["tools"] = anthropic_tools

        try:
            resp = await self.client.post(
                f"{self.base_url}/messages",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

            content_blocks = data.get("content", [])
            text_content = ""
            tool_calls = []

            for block in content_blocks:
                if block["type"] == "text":
                    text_content += block["text"]
                elif block["type"] == "tool_use":
                    tool_calls.append({
                        "name": block["name"],
                        "arguments": block["input"],
                    })

            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", self._count_message_tokens(messages))
            output_tokens = usage.get("output_tokens", self._estimate_tokens(text_content))

            return LLMResponse(
                content=text_content,
                tool_calls=tool_calls if tool_calls else None,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=self.model,
                raw_response=data,
            )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Anthropic API error: {e.response.status_code} - {e.response.text}") from e

    async def chat_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[LLMResponse, None]:
        payload = {
            "model": self.model,
            "messages": self._convert_messages(messages)[1],
            "max_tokens": 4096,
            "temperature": temperature,
            "stream": True,
        }

        system, _ = self._convert_messages(messages)
        if system:
            payload["system"] = system

        anthropic_tools = self._convert_tools(tools)
        if anthropic_tools:
            payload["tools"] = anthropic_tools

        async with self.client.stream(
            "POST",
            f"{self.base_url}/messages",
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    yield LLMResponse(content=text, model=self.model)
                    except json.JSONDecodeError:
                        pass


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider (gateway to 100+ models)."""

    def __init__(
        self,
        model: str = "openai/gpt-4-turbo",
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OpenRouter API key required. Set OPENROUTER_API_KEY env var or pass api_key.")
        super().__init__(model=model, api_key=api_key, base_url=base_url.rstrip("/"))
        self.client.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/humitron/humitron",
            "X-Title": "Humitron",
        })

    async def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> LLMResponse:
        # OpenRouter uses OpenAI-compatible API
        openai_provider = OpenAIProvider(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
        )
        openai_provider.client = self.client
        return await openai_provider.chat(messages, tools, temperature, stream)

    async def chat_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[LLMResponse, None]:
        openai_provider = OpenAIProvider(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
        )
        openai_provider.client = self.client
        async for chunk in openai_provider.chat_stream(messages, tools, temperature):
            yield chunk


# Provider factory
_PROVIDER_MAP = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "openrouter": OpenRouterProvider,
}


def get_provider_class(provider_name: str) -> type:
    """Get provider class by name."""
    provider_name = provider_name.lower()
    if provider_name not in _PROVIDER_MAP:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(_PROVIDER_MAP.keys())}")
    return _PROVIDER_MAP[provider_name]


def detect_provider(model: str) -> str:
    """Auto-detect provider from model name."""
    model_lower = model.lower()
    if model_lower.startswith(("gpt-", "o1-", "o3-")):
        return "openai"
    if model_lower.startswith(("claude-", "claude3-")):
        return "anthropic"
    if "/" in model or model_lower in ("gpt-4", "gpt-3.5-turbo", "claude-3-opus", "claude-3-sonnet"):
        return "openrouter"
    return "ollama"


def create_provider(
    model: str,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMProvider:
    """Factory function to create the appropriate provider."""
    provider = provider or detect_provider(model)
    provider_class = get_provider_class(provider)
    return provider_class(model=model, api_key=api_key, base_url=base_url)


# Cost estimation per 1K tokens (USD)
MODEL_COSTS = {
    # OpenAI
    "gpt-4": (0.03, 0.06),
    "gpt-4-turbo": (0.01, 0.03),
    "gpt-4o": (0.005, 0.015),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-3.5-turbo": (0.0005, 0.0015),
    "o1-preview": (0.015, 0.06),
    "o1-mini": (0.003, 0.012),
    # Anthropic
    "claude-3-opus": (0.015, 0.075),
    "claude-3-sonnet": (0.003, 0.015),
    "claude-3-haiku": (0.00025, 0.00125),
    "claude-3-5-sonnet": (0.003, 0.015),
    # OpenRouter (varies, use OpenAI pricing as baseline)
    # Local models
    "llama3.2": (0.0, 0.0),
    "llama3.1": (0.0, 0.0),
    "mistral": (0.0, 0.0),
    "phi4": (0.0, 0.0),
    "codellama": (0.0, 0.0),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a given model and token usage."""
    model_key = model.lower()
    # Try exact match first
    if model_key in MODEL_COSTS:
        in_cost, out_cost = MODEL_COSTS[model_key]
    else:
        # Try prefix match
        in_cost, out_cost = 0.0, 0.0
        for prefix, (ic, oc) in MODEL_COSTS.items():
            if model_key.startswith(prefix):
                in_cost, out_cost = ic, oc
                break
    return (input_tokens / 1000) * in_cost + (output_tokens / 1000) * out_cost