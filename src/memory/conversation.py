#!/usr/bin/env python3
"""Conversation memory management with summarization for long contexts."""

import json
from typing import List, Dict, Optional
from humitron.config.loader import get_config
from humitron.utils.logging import get_logger

logger = get_logger(__name__)


class ConversationMemory:
    """Manages conversation history with summarization for long contexts.
    
    Attributes:
        messages: List of conversation messages.
        max_tokens: Maximum token budget before summarization.
        summary_count: Number of times conversation has been summarized.
    """
    
    def __init__(self, max_tokens: int = 8000):
        """Initialize conversation memory.
        
        Args:
            max_tokens: Maximum tokens before triggering summarization.
        """
        self.messages: List[Dict[str, str]] = []
        self.max_tokens = max_tokens
        self.summary_count = 0
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to history.
        
        Args:
            role: Message role (system, user, assistant, tool).
            content: Message content.
        """
        self.messages.append({"role": role, "content": content})
        logger.debug(f"Added {role} message ({len(content)} chars)")
    
    def get_messages(self) -> List[Dict[str, str]]:
        """Get all messages.
        
        Returns:
            Copy of message list.
        """
        return self.messages.copy()
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token).
        
        Args:
            text: Text to estimate tokens for.
            
        Returns:
            Estimated token count.
        """
        return len(text) // 4
    
    def total_tokens(self) -> int:
        """Estimate total tokens in conversation.
        
        Returns:
            Total estimated tokens.
        """
        return sum(self.estimate_tokens(m.get("content", "")) for m in self.messages)
    
    def should_summarize(self) -> bool:
        """Check if conversation needs summarization.
        
        Returns:
            True if token count exceeds max_tokens.
        """
        return self.total_tokens() > self.max_tokens
    
    def summarize_middle(self, ollama_client) -> None:
        """Summarize the middle portion of conversation to reduce tokens.
        
        Args:
            ollama_client: OllamaClient instance for generating summary.
        """
        if len(self.messages) < 6:
            logger.debug("Not enough messages to summarize")
            return
        
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
            
            logger.info(f"Conversation summarized (tokens reduced, summary #{self.summary_count})")
        except Exception as e:
            logger.warning(f"Failed to summarize conversation: {e}")