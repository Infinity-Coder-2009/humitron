#!/usr/bin/env python3
"""Task planning and orchestration for multi-step operations."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from humitron.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TaskStep:
    """A single step in a task plan.

    Attributes:
        description: Human-readable description of the step.
        tool: Tool name to use.
        arguments: Arguments for the tool.
        depends_on: List of step indices this step depends on.
    """
    description: str
    tool: str
    arguments: Dict[str, Any]
    depends_on: List[int] = None

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


class TaskPlanner:
    """Plans and executes multi-step tasks.

    Breaks down complex user requests into sequences of tool calls
    with proper dependency ordering.
    """

    def __init__(self):
        """Initialize task planner."""
        self.steps: List[TaskStep] = []

    def create_plan(self, user_prompt: str, available_tools: List[str]) -> List[TaskStep]:
        """Create a task plan from user prompt.

        This is a simple heuristic-based planner. In production,
        this could use an LLM to generate plans.

        Args:
            user_prompt: User's request.
            available_tools: List of available tool names.

        Returns:
            List of TaskStep objects.
        """
        # Simple keyword-based planning
        prompt_lower = user_prompt.lower()
        steps = []

        # Check for file operations
        if "read" in prompt_lower or "examine" in prompt_lower or "look at" in prompt_lower:
            if "read_file" in available_tools:
                steps.append(TaskStep(
                    description="Read relevant files",
                    tool="read_file",
                    arguments={"path": ""}  # Will be filled by agent
                ))

        if "write" in prompt_lower or "create" in prompt_lower or "save" in prompt_lower:
            if "write_file" in available_tools:
                steps.append(TaskStep(
                    description="Write output to file",
                    tool="write_file",
                    arguments={"path": "", "content": ""}
                ))

        # Check for bash operations
        if "run" in prompt_lower or "execute" in prompt_lower or "command" in prompt_lower:
            if "bash_execute" in available_tools:
                steps.append(TaskStep(
                    description="Execute command",
                    tool="bash_execute",
                    arguments={"command": ""}
                ))

        # Check for web search
        if "search" in prompt_lower or "find" in prompt_lower or "look up" in prompt_lower:
            if "web_search" in available_tools:
                steps.append(TaskStep(
                    description="Search the web",
                    tool="web_search",
                    arguments={"query": ""}
                ))

        # Default: let agent handle it
        if not steps:
            logger.debug("No specific plan created, agent will handle directly")

        self.steps = steps
        return steps

    def execute_plan(
        self,
        steps: List[TaskStep],
        tool_executor: callable
    ) -> List[Dict[str, Any]]:
        """Execute a task plan.

        Args:
            steps: List of task steps.
            tool_executor: Function to execute tools (tool_name, arguments) -> result.

        Returns:
            List of step results.
        """
        results = []

        for i, step in enumerate(steps):
            logger.info(f"Executing step {i+1}/{len(steps)}: {step.description}")

            # Check dependencies
            for dep_idx in step.depends_on:
                if dep_idx >= len(results):
                    logger.warning(f"Dependency {dep_idx} not yet resolved")

            # Execute tool
            try:
                result = tool_executor(step.tool, step.arguments)
                results.append({
                    "step": i,
                    "description": step.description,
                    "tool": step.tool,
                    "success": result.success,
                    "output": result.output,
                    "error": result.error
                })
            except Exception as e:
                logger.error(f"Step {i} failed: {e}")
                results.append({
                    "step": i,
                    "description": step.description,
                    "tool": step.tool,
                    "success": False,
                    "output": "",
                    "error": str(e)
                })

        return results