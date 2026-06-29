#!/usr/bin/env python3
"""
Trajectory Logging System for Humitron.

Logs every step of agent execution to structured JSON files for
debugging, evaluation, and analysis.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from threading import Lock


@dataclass
class TrajectoryStep:
    """A single step in the agent's trajectory.
    
    Attributes:
        step_number: Sequential step number.
        timestamp: ISO format timestamp.
        step_type: Type of step (llm_call, tool_call, tool_result, reasoning, final_answer).
        content: Step content as dictionary.
        duration_ms: Optional duration in milliseconds.
        token_count: Optional token count.
    """
    step_number: int
    timestamp: str
    step_type: str  # "llm_call", "tool_call", "tool_result", "reasoning", "final_answer"
    content: Dict[str, Any]
    duration_ms: Optional[float] = None
    token_count: Optional[int] = None


@dataclass
class Trajectory:
    """Complete trajectory of an agent session.
    
    Attributes:
        trajectory_id: Unique trajectory identifier.
        session_id: Session identifier.
        user_id: Optional user identifier.
        start_time: Session start time (ISO format).
        end_time: Optional session end time.
        user_prompt: Original user prompt.
        final_answer: Final answer if completed.
        steps: List of trajectory steps.
        metadata: Additional metadata.
        success: Whether trajectory completed successfully.
        error: Error message if failed.
    """
    trajectory_id: str
    session_id: str
    user_id: Optional[str]
    start_time: str
    end_time: Optional[str] = None
    user_prompt: str = ""
    final_answer: Optional[str] = None
    steps: List[TrajectoryStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation.
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trajectory":
        """Create Trajectory from dictionary.
        
        Args:
            data: Dictionary with trajectory data.
            
        Returns:
            Trajectory instance.
        """
        steps = [TrajectoryStep(**s) for s in data.get("steps", [])]
        data["steps"] = steps
        return cls(**data)


class TrajectoryLogger:
    """
    Logs agent trajectories to JSON files.
    
    Thread-safe, supports concurrent sessions.
    """
    
    def __init__(self, log_dir: Path = Path("trajectories")):
        """Initialize trajectory logger.
        
        Args:
            log_dir: Directory to store trajectory logs.
        """
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_trajectory: Optional[Trajectory] = None
        self._lock = Lock()
        self._step_counter = 0
    
    def start_trajectory(
        self,
        user_prompt: str,
        session_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Trajectory:
        """Start a new trajectory.
        
        Args:
            user_prompt: User's prompt.
            session_id: Session identifier.
            user_id: Optional user identifier.
            metadata: Optional metadata.
            
        Returns:
            Started Trajectory instance.
        """
        with self._lock:
            self._step_counter = 0
            trajectory = Trajectory(
                trajectory_id=str(uuid.uuid4())[:8],
                session_id=session_id,
                user_id=user_id,
                start_time=datetime.now().isoformat(),
                user_prompt=user_prompt,
                metadata=metadata or {}
            )
            self.current_trajectory = trajectory
            return trajectory
    
    def log_step(
        self,
        step_type: str,
        content: Dict[str, Any],
        duration_ms: Optional[float] = None,
        token_count: Optional[int] = None
    ) -> TrajectoryStep:
        """Log a step in the current trajectory.
        
        Args:
            step_type: Type of step.
            content: Step content.
            duration_ms: Optional duration in milliseconds.
            token_count: Optional token count.
            
        Returns:
            Logged TrajectoryStep.
            
        Raises:
            RuntimeError: If no active trajectory.
        """
        with self._lock:
            if not self.current_trajectory:
                raise RuntimeError("No active trajectory. Call start_trajectory first.")
            
            self._step_counter += 1
            step = TrajectoryStep(
                step_number=self._step_counter,
                timestamp=datetime.now().isoformat(),
                step_type=step_type,
                content=content,
                duration_ms=duration_ms,
                token_count=token_count
            )
            self.current_trajectory.steps.append(step)
            return step
    
    def log_llm_call(
        self,
        messages: List[Dict[str, str]],
        response: Dict[str, Any],
        duration_ms: float,
        token_count: Optional[int] = None
    ) -> TrajectoryStep:
        """Log an LLM call.
        
        Args:
            messages: Messages sent to LLM.
            response: LLM response.
            duration_ms: Call duration in milliseconds.
            token_count: Optional token count.
            
        Returns:
            Logged TrajectoryStep.
        """
        return self.log_step(
            step_type="llm_call",
            content={
                "messages": messages,
                "response": response
            },
            duration_ms=duration_ms,
            token_count=token_count
        )
    
    def log_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> TrajectoryStep:
        """Log a tool call.
        
        Args:
            tool_name: Name of tool called.
            arguments: Tool arguments.
            
        Returns:
            Logged TrajectoryStep.
        """
        return self.log_step(
            step_type="tool_call",
            content={
                "tool": tool_name,
                "arguments": arguments
            }
        )
    
    def log_tool_result(
        self,
        tool_name: str,
        result: Dict[str, Any],
        duration_ms: float
    ) -> TrajectoryStep:
        """Log a tool result.
        
        Args:
            tool_name: Name of tool.
            result: Tool result.
            duration_ms: Execution duration in milliseconds.
            
        Returns:
            Logged TrajectoryStep.
        """
        return self.log_step(
            step_type="tool_result",
            content={
                "tool": tool_name,
                "result": result
            },
            duration_ms=duration_ms
        )
    
    def log_reasoning(self, reasoning: str) -> TrajectoryStep:
        """Log agent reasoning.
        
        Args:
            reasoning: Reasoning text.
            
        Returns:
            Logged TrajectoryStep.
        """
        return self.log_step(
            step_type="reasoning",
            content={"reasoning": reasoning}
        )
    
    def log_final_answer(self, answer: str) -> TrajectoryStep:
        """Log the final answer.
        
        Args:
            answer: Final answer text.
            
        Returns:
            Logged TrajectoryStep.
        """
        return self.log_step(
            step_type="final_answer",
            content={"answer": answer}
        )
    
    def end_trajectory(
        self,
        final_answer: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> Trajectory:
        """End the current trajectory and save to disk.
        
        Args:
            final_answer: Optional final answer.
            success: Whether trajectory succeeded.
            error: Optional error message.
            
        Returns:
            Completed Trajectory instance.
            
        Raises:
            RuntimeError: If no active trajectory.
        """
        with self._lock:
            if not self.current_trajectory:
                raise RuntimeError("No active trajectory.")
            
            self.current_trajectory.end_time = datetime.now().isoformat()
            self.current_trajectory.final_answer = final_answer
            self.current_trajectory.success = success
            self.current_trajectory.error = error
            
            # Save to file
            self._save_trajectory(self.current_trajectory)
            
            trajectory = self.current_trajectory
            self.current_trajectory = None
            return trajectory
    
    def _save_trajectory(self, trajectory: Trajectory) -> Path:
        """Save trajectory to JSON file.
        
        Args:
            trajectory: Trajectory to save.
            
        Returns:
            Path to saved file.
        """
        # Create date-based subdirectory
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = self.log_dir / date_str
        date_dir.mkdir(exist_ok=True)
        
        # Filename: session_id_trajectory_id.json
        filename = f"{trajectory.session_id}_{trajectory.trajectory_id}.json"
        filepath = date_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(trajectory.to_dict(), f, indent=2, default=str)
        
        return filepath
    
    def load_trajectory(self, trajectory_id: str, date: Optional[str] = None) -> Optional[Trajectory]:
        """Load a trajectory by ID.
        
        Args:
            trajectory_id: Trajectory ID to load.
            date: Optional date string (YYYY-MM-DD).
            
        Returns:
            Trajectory if found, None otherwise.
        """
        if date:
            date_dir = self.log_dir / date
        else:
            # Search all date directories
            for date_dir in sorted(self.log_dir.iterdir()):
                if date_dir.is_dir():
                    for file in date_dir.glob(f"*_{trajectory_id}.json"):
                        with open(file) as f:
                            return Trajectory.from_dict(json.load(f))
            return None
        
        for file in date_dir.glob(f"*_{trajectory_id}.json"):
            with open(file) as f:
                return Trajectory.from_dict(json.load(f))
        
        return None
    
    def list_trajectories(
        self,
        date: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Trajectory]:
        """List trajectories with optional filters.
        
        Args:
            date: Optional date filter.
            session_id: Optional session filter.
            user_id: Optional user filter.
            limit: Maximum number of trajectories.
            
        Returns:
            List of trajectories.
        """
        trajectories = []
        
        date_dirs = [self.log_dir / date] if date else sorted(self.log_dir.iterdir())
        
        for date_dir in date_dirs:
            if not date_dir.is_dir():
                continue
            
            for file in sorted(date_dir.glob("*.json"), reverse=True):
                if len(trajectories) >= limit:
                    break
                
                try:
                    with open(file) as f:
                        traj = Trajectory.from_dict(json.load(f))
                    
                    if session_id and traj.session_id != session_id:
                        continue
                    if user_id and traj.user_id != user_id:
                        continue
                    
                    trajectories.append(traj)
                except Exception as e:
                    print(f"Error loading {file}: {e}")
        
        return trajectories


# Global trajectory logger instance
_trajectory_logger: Optional[TrajectoryLogger] = None


def get_trajectory_logger() -> TrajectoryLogger:
    """Get or create the global trajectory logger.
    
    Returns:
        Global TrajectoryLogger instance.
    """
    global _trajectory_logger
    if _trajectory_logger is None:
        _trajectory_logger = TrajectoryLogger()
    return _trajectory_logger