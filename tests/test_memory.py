#!/usr/bin/env python3
"""Unit tests for Humitron memory."""

import pytest
from unittest.mock import MagicMock

from humitron.memory.conversation import ConversationMemory


class TestConversationMemory:
    """Tests for ConversationMemory."""

    def test_add_message(self):
        """Test adding messages."""
        memory = ConversationMemory()

        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi there!")

        assert len(memory.messages) == 2
        assert memory.messages[0]["role"] == "user"
        assert memory.messages[0]["content"] == "Hello"
        assert memory.messages[1]["role"] == "assistant"
        assert memory.messages[1]["content"] == "Hi there!"

    def test_get_messages(self):
        """Test getting messages."""
        memory = ConversationMemory()
        memory.add_message("user", "Test")

        messages = memory.get_messages()

        assert len(messages) == 1
        assert messages[0]["content"] == "Test"

        # Verify it's a copy
        messages.append({"role": "user", "content": "Modified"})
        assert len(memory.messages) == 1

    def test_estimate_tokens(self):
        """Test token estimation."""
        memory = ConversationMemory()

        # 4 chars ≈ 1 token
        assert memory.estimate_tokens("") == 0
        assert memory.estimate_tokens("test") == 1
        assert memory.estimate_tokens("1234") == 1
        assert memory.estimate_tokens("12345") == 1
        assert memory.estimate_tokens("12345678") == 2

    def test_total_tokens(self):
        """Test total token counting."""
        memory = ConversationMemory()
        memory.add_message("user", "Hello")  # ~1 token
        memory.add_message("assistant", "Hi there!")  # ~2 tokens

        total = memory.total_tokens()
        assert total >= 3

    def test_should_summarize(self):
        """Test summarization trigger."""
        memory = ConversationMemory(max_tokens=100)

        # Add small messages
        memory.add_message("user", "Hi")
        assert memory.should_summarize() is False

        # Add large message
        memory.add_message("assistant", "x" * 500)  # ~125 tokens
        assert memory.should_summarize() is True

    def test_summarize_middle(self):
        """Test conversation summarization."""
        memory = ConversationMemory(max_tokens=100)

        # Add enough messages to trigger summarization
        for i in range(10):
            memory.add_message("user", f"Message {i}" * 20)

        # Mock Ollama client
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "message": {"content": "Summary of conversation"}
        }

        original_count = len(memory.messages)
        memory.summarize_middle(mock_client)

        # Should have fewer messages after summarization
        assert len(memory.messages) < original_count
        assert memory.summary_count == 1

        # Check summary message exists
        summary_msgs = [m for m in memory.messages if "Summary" in m.get("content", "")]
        assert len(summary_msgs) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])