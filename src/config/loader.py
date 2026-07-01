#!/usr/bin/env python3
"""
Configuration management for Humitron.

Loads configuration from config.yaml, environment variables, and .env file.
Environment variables take precedence over config.yaml.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


@dataclass
class Config:
    """Main configuration for Humitron.
    
    Attributes:
        model: Ollama model to use for inference.
        workspace_path: Working directory for file operations.
        max_steps: Maximum number of ReAct steps per query.
        temperature: LLM temperature for sampling.
        ollama_base_url: Base URL for Ollama API.
        max_tokens_per_session: Token budget per session.
        max_tokens_per_call: Token limit per LLM call.
        reserve_tokens: Reserved tokens for system prompt.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        enable_mcp: Whether to enable MCP server integration.
        enable_trajectory_logging: Whether to log agent trajectories.
        trajectory_log_dir: Directory for trajectory logs.
        health_check_port: Port for health check endpoint.
        enable_prometheus: Whether to enable Prometheus metrics.
        prometheus_port: Port for Prometheus metrics.
        rate_limit_requests_per_minute: Rate limit for requests.
        rate_limit_tokens_per_day: Daily token rate limit.
        sandbox_mode: Whether to run in sandboxed mode.
    """
    model: str = "llama3.2"
    workspace_path: str = str(Path.cwd())
    max_steps: int = 20
    temperature: float = 0.7
    ollama_base_url: str = "http://localhost:11434"
    max_tokens_per_session: int = 100_000
    max_tokens_per_call: int = 8_000
    reserve_tokens: int = 1_000
    log_level: str = "INFO"
    enable_mcp: bool = False
    enable_trajectory_logging: bool = True
    trajectory_log_dir: str = "trajectories"
    health_check_port: int = 8080
    enable_prometheus: bool = False
    prometheus_port: int = 9090
    rate_limit_requests_per_minute: int = 60
    rate_limit_tokens_per_day: int = 1_000_000
    sandbox_mode: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables.
        
        Returns:
            Config instance populated from environment variables.
        """
        return cls(
            model=os.getenv("HUMITRON_MODEL", "llama3.2"),
            workspace_path=os.getenv("HUMITRON_WORKSPACE", str(Path.cwd())),
            max_steps=int(os.getenv("HUMITRON_MAX_STEPS", "20")),
            temperature=float(os.getenv("HUMITRON_TEMPERATURE", "0.7")),
            ollama_base_url=os.getenv("HUMITRON_OLLAMA_URL", "http://localhost:11434"),
            max_tokens_per_session=int(os.getenv("HUMITRON_MAX_TOKENS_SESSION", "100000")),
            max_tokens_per_call=int(os.getenv("HUMITRON_MAX_TOKENS_CALL", "8000")),
            log_level=os.getenv("HUMITRON_LOG_LEVEL", "INFO"),
            enable_mcp=os.getenv("HUMITRON_ENABLE_MCP", "false").lower() == "true",
            enable_trajectory_logging=os.getenv("HUMITRON_TRAJECTORY_LOGGING", "true").lower() == "true",
            health_check_port=int(os.getenv("HUMITRON_HEALTH_PORT", "8080")),
            enable_prometheus=os.getenv("HUMITRON_PROMETHEUS", "false").lower() == "true",
            prometheus_port=int(os.getenv("HUMITRON_PROMETHEUS_PORT", "9090")),
            rate_limit_requests_per_minute=int(os.getenv("HUMITRON_RATE_LIMIT_RPM", "60")),
            rate_limit_tokens_per_day=int(os.getenv("HUMITRON_RATE_LIMIT_TPD", "1000000")),
            sandbox_mode=os.getenv("HUMITRON_SANDBOX", "false").lower() == "true",
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary.
        
        Returns:
            Dictionary representation of the config.
        """
        return {
            "model": self.model,
            "workspace_path": self.workspace_path,
            "max_steps": self.max_steps,
            "temperature": self.temperature,
            "ollama_base_url": self.ollama_base_url,
            "max_tokens_per_session": self.max_tokens_per_session,
            "max_tokens_per_call": self.max_tokens_per_call,
            "reserve_tokens": self.reserve_tokens,
            "log_level": self.log_level,
            "enable_mcp": self.enable_mcp,
            "enable_trajectory_logging": self.enable_trajectory_logging,
            "trajectory_log_dir": self.trajectory_log_dir,
            "health_check_port": self.health_check_port,
            "enable_prometheus": self.enable_prometheus,
            "prometheus_port": self.prometheus_port,
            "rate_limit_requests_per_minute": self.rate_limit_requests_per_minute,
            "rate_limit_tokens_per_day": self.rate_limit_tokens_per_day,
            "sandbox_mode": self.sandbox_mode,
        }


CONFIG_PATH = Path("config.yaml")
_config: Optional[Config] = None


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from YAML file or environment.
    
    Priority: environment variables > config.yaml > defaults
    
    Args:
        config_path: Optional path to config file. Defaults to config.yaml.
        
    Returns:
        Config instance with loaded settings.
        
    Raises:
        yaml.YAMLError: If config.yaml is malformed.
        FileNotFoundError: If config_path is specified but doesn't exist.
    """
    global _config
    
    if _config is not None:
        return _config
    
    path = config_path or CONFIG_PATH
    
    if path.exists():
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
            # Merge with env overrides
            env_config = Config.from_env()
            merged = {**data, **{k: v for k, v in env_config.to_dict().items() if v is not None}}
            _config = Config(**merged)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Could not parse config.yaml: {e}")
        except Exception as e:
            raise RuntimeError(f"Could not load config.yaml: {e}")
    else:
        _config = Config.from_env()
    
    return _config


def get_config() -> Config:
    """Get the current configuration.
    
    Returns:
        Current Config instance.
    """
    if _config is None:
        return load_config()
    return _config


def save_config(config: Config, config_path: Optional[Path] = None) -> None:
    """Save configuration to YAML file.
    
    Args:
        config: Config instance to save.
        config_path: Optional path to save to. Defaults to config.yaml.
    """
    global _config
    path = config_path or CONFIG_PATH
    with open(path, "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False)
    _config = config