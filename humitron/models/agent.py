#!/usr/bin/env python3
"""Agent-related data models."""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class AgentMessage(BaseModel):
    """A message in the conversation."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class AgentState(BaseModel):
    """Current state of the agent."""
    messages: List[Dict[str, str]] = Field(default_factory=list)
    step_count: int = 0
    finished: bool = False
    final_answer: Optional[str] = None