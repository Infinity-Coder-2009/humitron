"""Humitron - Local-first AI Agent with MCP Integration, Memory, and Multi-Agent Support."""

__version__ = "0.2.0"
__author__ = "Humitron Contributors"

from humitron.agent import ReActAgent
from humitron.config.loader import get_config, Config

__all__ = ["ReActAgent", "get_config", "Config"]