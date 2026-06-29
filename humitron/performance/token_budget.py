#!/usr/bin/env python3
"""
Token Budgeting & Context Management for Humitron.

Tracks token usage, enforces budgets, and implements smart context trimming
to prevent runaway costs and context overload.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import hashlib


@dataclass
class TokenUsage:
    """Token usage statistics for a session."""
    session_id: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    estimated_cost_usd: float = 0.0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_llm_call(self, input_tokens: int, output_tokens: int, model: str = "llama3.2") -> None:
        """Record an LLM call."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_tokens = self.total_input_tokens + self.total_output_tokens
        self.llm_calls += 1
        self.last_updated = datetime.now().isoformat()
        
        # Rough cost estimation (local models = $0, cloud models vary)
        # These are per 1K tokens estimates
        cost_per_1k = {
            "gpt-4": 0.03,
            "gpt-4-turbo": 0.01,
            "gpt-3.5-turbo": 0.0015,
            "claude-3-opus": 0.015,
            "claude-3-sonnet": 0.003,
            "llama3.2": 0.0,  # Local
            "mistral": 0.0,   # Local
        }
        rate = cost_per_1k.get(model, 0.0)
        self.estimated_cost_usd += (input_tokens + output_tokens) / 1000 * rate
    
    def add_tool_call(self) -> None:
        """Record a tool call."""
        self.tool_calls += 1
        self.last_updated = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "started_at": self.started_at,
            "last_updated": self.last_updated,
        }


class TokenCounter:
    """
    Estimates token counts for text using character-based approximation.
    
    For more accuracy, integrate with tiktoken when available.
    """
    
    # Rough approximation: 4 chars = 1 token for English
    CHARS_PER_TOKEN = 4
    
    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Estimate token count for a string."""
        if not text:
            return 0
        return max(1, len(text) // cls.CHARS_PER_TOKEN)
    
    @classmethod
    def estimate_messages_tokens(cls, messages: List[Dict[str, str]]) -> int:
        """Estimate tokens for a list of messages."""
        total = 0
        for msg in messages:
            # Role + content + overhead
            total += cls.estimate_tokens(msg.get("role", ""))
            total += cls.estimate_tokens(msg.get("content", ""))
            total += 4  # Overhead per message
        return total
    
    @classmethod
    def estimate_tool_tokens(cls, tool_name: str, arguments: Dict) -> int:
        """Estimate tokens for a tool call."""
        args_str = json.dumps(arguments)
        return cls.estimate_tokens(f"{tool_name}: {args_str}")


class TokenBudgetManager:
    """
    Manages token budgets per session with automatic context trimming.
    
    Features:
    - Per-session token budgets
    - Automatic summarization when budget exceeded
    - Sliding window context preservation
    - Semantic similarity-based trimming
    """
    
    def __init__(
        self,
        max_tokens_per_session: int = 100_000,
        max_tokens_per_call: int = 8_000,
        reserve_tokens: int = 1_000,
        ollama_client: Any = None
    ):
        self.max_tokens_per_session = max_tokens_per_session
        self.max_tokens_per_call = max_tokens_per_call
        self.reserve_tokens = reserve_tokens
        self.ollama_client = ollama_client
        
        self.session_usage: Dict[str, TokenUsage] = {}
        self.session_messages: Dict[str, List[Dict]] = {}
    
    def get_usage(self, session_id: str) -> TokenUsage:
        """Get or create token usage for a session."""
        if session_id not in self.session_usage:
            self.session_usage[session_id] = TokenUsage(session_id=session_id)
        return self.session_usage[session_id]
    
    def record_llm_call(
        self,
        session_id: str,
        messages: List[Dict[str, str]],
        response: Dict[str, Any],
        model: str = "llama3.2"
    ) -> None:
        """Record token usage from an LLM call."""
        usage = self.get_usage(session_id)
        
        # Estimate input tokens
        input_tokens = TokenCounter.estimate_messages_tokens(messages)
        
        # Extract output tokens from response if available
        output_tokens = 0
        if "message" in response and "content" in response["message"]:
            output_tokens = TokenCounter.estimate_tokens(response["message"]["content"])
        
        usage.add_llm_call(input_tokens, output_tokens, model)
    
    def record_tool_call(self, session_id: str) -> None:
        """Record a tool call."""
        self.get_usage(session_id).add_tool_call()
    
    def check_budget(self, session_id: str) -> Tuple[bool, str]:
        """
        Check if session is within token budget.
        
        Returns:
            (within_budget, message)
        """
        usage = self.get_usage(session_id)
        
        if usage.total_tokens >= self.max_tokens_per_session:
            return False, (
                f"Session token budget exceeded: "
                f"{usage.total_tokens}/{self.max_tokens_per_session} tokens used. "
                f"Estimated cost: ${usage.estimated_cost_usd:.4f}"
            )
        
        # Warning at 80%
        if usage.total_tokens >= self.max_tokens_per_session * 0.8:
            return True, (
                f"⚠️ Token budget at 80%: "
                f"{usage.total_tokens}/{self.max_tokens_per_session} tokens used."
            )
        
        return True, ""
    
    def trim_context_if_needed(
        self,
        session_id: str,
        messages: List[Dict[str, str]],
        system_prompt: str
    ) -> List[Dict[str, str]]:
        """
        Trim conversation context if it exceeds the per-call limit.
        
        Uses sliding window: keeps system prompt, first user message,
        last N messages, and summarizes the middle.
        """
        current_tokens = TokenCounter.estimate_messages_tokens(messages)
        
        if current_tokens <= self.max_tokens_per_call - self.reserve_tokens:
            return messages
        
        # Need to trim - use sliding window with summarization
        if self.ollama_client and len(messages) > 6:
            return self._summarize_middle(messages, system_prompt)
        else:
            return self._sliding_window(messages, system_prompt)
    
    def _sliding_window(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str
    ) -> List[Dict[str, str]]:
        """Simple sliding window: keep first 2 and last N messages."""
        # Always keep system prompt
        system_msg = next((m for m in messages if m["role"] == "system"), None)
        other_messages = [m for m in messages if m["role"] != "system"]
        
        if not system_msg:
            system_msg = {"role": "system", "content": system_prompt}
        
        # Keep first user message and last N messages
        keep_start = min(2, len(other_messages))
        keep_end = max(0, len(other_messages) - keep_start)
        
        # Calculate how many we can keep
        budget = self.max_tokens_per_call - self.reserve_tokens
        system_tokens = TokenCounter.estimate_tokens(system_msg["content"])
        available = budget - system_tokens
        
        kept = []
        tokens_used = 0
        
        # Add from end (most recent first)
        for msg in reversed(other_messages):
            msg_tokens = TokenCounter.estimate_tokens(msg.get("content", "")) + 4
            if tokens_used + msg_tokens <= available:
                kept.insert(0, msg)
                tokens_used += msg_tokens
            else:
                break
        
        return [system_msg] + kept
    
    def _summarize_middle(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str
    ) -> List[Dict[str, str]]:
        """Summarize middle portion of conversation using LLM."""
        system_msg = next((m for m in messages if m["role"] == "system"), None)
        other_messages = [m for m in messages if m["role"] != "system"]
        
        if len(other_messages) <= 4:
            return self._sliding_window(messages, system_prompt)
        
        # Split: keep first 2, summarize middle, keep last 2
        keep_start = other_messages[:2]
        keep_end = other_messages[-2:]
        middle = other_messages[2:-2]
        
        if not middle:
            return [system_msg] + keep_start + keep_end if system_msg else keep_start + keep_end
        
        # Create summary prompt
        conversation_text = "\n".join(
            f"{m['role']}: {m['content'][:500]}" for m in middle
        )
        
        summary_prompt = f"""Summarize this conversation history concisely, preserving key facts, decisions, and context:

{conversation_text}

Provide a brief summary:"""
        
        try:
            response = self.ollama_client.chat([
                {"role": "system", "content": "You are a helpful assistant that summarizes conversations concisely."},
                {"role": "user", "content": summary_prompt}
            ])
            summary = response.get("message", {}).get("content", "Summary unavailable")
            
            # Record the summarization call
            # (In practice, you'd pass session_id here)
            
            summary_msg = {
                "role": "system",
                "content": f"[Previous conversation summary]: {summary}"
            }
            
            result = []
            if system_msg:
                result.append(system_msg)
            result.extend(keep_start)
            result.append(summary_msg)
            result.extend(keep_end)
            
            return result
            
        except Exception as e:
            print(f"Failed to summarize: {e}")
            return self._sliding_window(messages, system_prompt)
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        usage = self.get_usage(session_id)
        return usage.to_dict()
    
    def reset_session(self, session_id: str) -> None:
        """Reset token tracking for a session."""
        self.session_usage.pop(session_id, None)
        self.session_messages.pop(session_id, None)


# Global token budget manager
_token_budget_manager: Optional[TokenBudgetManager] = None


def get_token_budget_manager(
    max_tokens: int = 100_000,
    ollama_client: Any = None
) -> TokenBudgetManager:
    """Get or create the global token budget manager."""
    global _token_budget_manager
    if _token_budget_manager is None:
        _token_budget_manager = TokenBudgetManager(
            max_tokens_per_session=max_tokens,
            ollama_client=ollama_client
        )
    return _token_budget_manager