#!/usr/bin/env python3
"""Tests for JSON parsing and retry logic."""

import pytest
from unittest.mock import MagicMock, patch

from humitron.agent import ReActAgent
from humitron.models.tools import ToolCall


class TestJSONParsing:
    """Tests for JSON parsing with retry logic."""
    
    @pytest.fixture
    def agent(self):
        """Create agent with mocked Ollama."""
        with patch("humitron.agent.OllamaClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            agent = ReActAgent(model="llama3.2", max_steps=5)
            agent.ollama = mock_client
            return agent, mock_client
    
    def test_parse_valid_json_with_tool_calls(self, agent):
        """Test parsing valid JSON with tool_calls."""
        agent_obj, _ = agent
        
        response = '{"tool_calls": [{"name": "read_file", "arguments": {"path": "test.txt"}}]}'
        tool_calls = agent_obj._parse_tool_calls(response)
        
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "read_file"
        assert tool_calls[0].arguments == {"path": "test.txt"}
    
    def test_parse_json_with_extra_text(self, agent):
        """Test parsing JSON embedded in text."""
        agent_obj, _ = agent
        
        response = 'Here is the tool call: {"tool_calls": [{"name": "bash_execute", "arguments": {"command": "ls"}}]}'
        tool_calls = agent_obj._parse_tool_calls(response)
        
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "bash_execute"
    
    def test_parse_malformed_json_returns_empty(self, agent):
        """Test that malformed JSON returns empty list."""
        agent_obj, _ = agent
        
        response = '{"tool_calls": [{"name": "read_file", "arguments": {"path": "test.txt"}}}'  # Missing closing brace
        tool_calls = agent_obj._parse_tool_calls(response)
        
        assert len(tool_calls) == 0
    
    def test_parse_empty_response(self, agent):
        """Test parsing empty response."""
        agent_obj, _ = agent
        
        response = ""
        tool_calls = agent_obj._parse_tool_calls(response)
        
        assert len(tool_calls) == 0
    
    def test_parse_plain_text_response(self, agent):
        """Test parsing plain text (no JSON)."""
        agent_obj, _ = agent
        
        response = "This is a plain text response without any tool calls."
        tool_calls = agent_obj._parse_tool_calls(response)
        
        assert len(tool_calls) == 0
    
    def test_handle_json_parse_error_retries(self, agent):
        """Test JSON parse error handling retries with corrected JSON."""
        agent_obj, mock_client = agent
        
        # First response is malformed, second is corrected
        mock_client.chat.side_effect = [
            {"message": {"content": '{"tool_calls": [malformed'}},  # First call (malformed)
            {"message": {"content": '{"tool_calls": [{"name": "read_file", "arguments": {"path": "test.txt"}}]}'}},  # Retry
        ]
        
        agent_obj.memory.add_message("assistant", '{"tool_calls": [malformed}')
        
        corrected = agent_obj._handle_json_parse_error()
        
        assert '{"tool_calls": [{"name": "read_file"' in corrected
        assert mock_client.chat.call_count == 1  # One retry call


if __name__ == "__main__":
    pytest.main([__file__, "-v"])