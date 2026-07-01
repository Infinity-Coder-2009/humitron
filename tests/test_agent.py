#!/usr/bin/env python3
"""Unit tests for Humitron agent."""

import pytest
from unittest.mock import MagicMock, patch

from humitron.agent import ReActAgent, OllamaClient
from humitron.models.tools import ToolCall, ToolResult
from humitron.tools.registry import TOOL_SCHEMAS


class TestOllamaClient:
    """Tests for OllamaClient."""

    @patch("humitron.agent.httpx.Client")
    def test_chat_success(self, mock_client_class):
        """Test successful chat request."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Hello!"}
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = OllamaClient(base_url="http://localhost:11434", model="llama3.2")
        result = client.chat([{"role": "user", "content": "Hi"}])

        assert result["message"]["content"] == "Hello!"
        mock_client.post.assert_called_once()

    @patch("humitron.agent.httpx.Client")
    def test_chat_connection_error(self, mock_client_class):
        """Test connection error handling."""
        import httpx
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_class.return_value = mock_client

        client = OllamaClient(base_url="http://localhost:11434", model="llama3.2")

        with pytest.raises(ConnectionError):
            client.chat([{"role": "user", "content": "Hi"}])

    @patch("humitron.agent.httpx.Client")
    def test_chat_http_error(self, mock_client_class):
        """Test HTTP error handling."""
        import httpx
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=mock_response
        )
        mock_client_class.return_value = mock_client

        client = OllamaClient(base_url="http://localhost:11434", model="llama3.2")

        with pytest.raises(RuntimeError):
            client.chat([{"role": "user", "content": "Hi"}])


class TestReActAgent:
    """Tests for ReActAgent."""

    @pytest.fixture
    def mock_ollama(self):
        """Create agent with mocked Ollama."""
        with patch("humitron.agent.OllamaClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            agent = ReActAgent(model="llama3.2", max_steps=5)
            agent.ollama = mock_client
            yield agent, mock_client

    def test_init(self, mock_ollama):
        """Test agent initialization."""
        agent, _ = mock_ollama

        assert agent.max_steps == 5
        assert agent.model == "llama3.2"
        assert len(agent.memory.messages) == 1  # System prompt
        assert agent.memory.messages[0]["role"] == "system"

    def test_parse_tool_calls_valid(self, mock_ollama):
        """Test parsing valid tool calls."""
        agent, _ = mock_ollama

        response = '{"tool_calls": [{"name": "read_file", "arguments": {"path": "test.txt"}}]}'
        tool_calls = agent._parse_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0].name == "read_file"
        assert tool_calls[0].arguments == {"path": "test.txt"}

    def test_parse_tool_calls_invalid_json(self, mock_ollama):
        """Test parsing invalid JSON."""
        agent, _ = mock_ollama

        response = '{"tool_calls": [{"name": "read_file", "arguments": {"path": "test.txt"}}}'  # Missing closing brace
        tool_calls = agent._parse_tool_calls(response)

        assert len(tool_calls) == 0

    def test_parse_tool_calls_no_tool_calls(self, mock_ollama):
        """Test parsing response without tool calls."""
        agent, _ = mock_ollama

        response = "This is a normal response."
        tool_calls = agent._parse_tool_calls(response)

        assert len(tool_calls) == 0

    def test_parse_tool_calls_direct_format(self, mock_ollama):
        """Test parsing direct tool call format."""
        agent, _ = mock_ollama

        response = '{"name": "read_file", "arguments": {"path": "test.txt"}}'
        tool_calls = agent._parse_tool_calls(response)

        # Current implementation doesn't handle this format in _parse_tool_calls
        # It's handled in run() method
        assert len(tool_calls) == 0

    def test_execute_tool_unknown(self, mock_ollama):
        """Test executing unknown tool."""
        agent, _ = mock_ollama

        tool_call = ToolCall(name="unknown_tool", arguments={})
        result = agent._execute_tool(tool_call)

        assert result.success is False
        assert "Unknown tool" in result.error

    def test_execute_tool_success(self, mock_ollama):
        """Test executing known tool."""
        agent, _ = mock_ollama

        # Mock the read_file tool
        with patch("humitron.agent.read_file") as mock_read:
            mock_read.return_value = ToolResult(success=True, output="File content")

            tool_call = ToolCall(name="read_file", arguments={"path": "test.txt"})
            result = agent._execute_tool(tool_call)

            assert result.success is True
            assert result.output == "File content"

    def test_run_no_tool_calls(self, mock_ollama):
        """Test run with no tool calls (direct answer)."""
        agent, mock_client = mock_ollama

        mock_client.chat.return_value = {
            "message": {"content": "This is the answer."}
        }

        result = agent.run("What is 2+2?")

        assert result == "This is the answer."
        assert mock_client.chat.call_count == 1

    def test_run_with_tool_calls(self, mock_ollama):
        """Test run with tool calls."""
        agent, mock_client = mock_ollama

        # First call returns tool call, second returns final answer
        mock_client.chat.side_effect = [
            {
                "message": {
                    "content": '{"tool_calls": [{"name": "read_file", "arguments": {"path": "test.txt"}}]}'
                }
            },
            {
                "message": {"content": "The file contains hello world."}
            }
        ]

        with patch("humitron.agent.read_file") as mock_read:
            mock_read.return_value = ToolResult(success=True, output="hello world")

            result = agent.run("Read test.txt")

            assert "hello world" in result.lower() or "contains" in result.lower()
            assert mock_client.chat.call_count == 2

    def test_run_max_steps(self, mock_ollama):
        """Test run stops at max steps."""
        agent, mock_client = mock_ollama

        # Always return tool calls
        mock_client.chat.return_value = {
            "message": {
                "content": '{"tool_calls": [{"name": "read_file", "arguments": {"path": "test.txt"}}]}'
            }
        }

        with patch("humitron.agent.read_file") as mock_read:
            mock_read.return_value = ToolResult(success=True, output="content")

            result = agent.run("Do something")

            assert "maximum steps" in result.lower()
            assert mock_client.chat.call_count == agent.max_steps


if __name__ == "__main__":
    pytest.main([__file__, "-v"])