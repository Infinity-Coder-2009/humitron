#!/usr/bin/env python3
"""Unit tests for Humitron configuration."""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from humitron.config.loader import Config, load_config, get_config, save_config


class TestConfig:
    """Tests for Config dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()

        assert config.model == "llama3.2"
        assert config.max_steps == 20
        assert config.temperature == 0.7
        assert config.log_level == "INFO"

    def test_config_from_env(self):
        """Test configuration from environment variables."""
        with patch.dict(os.environ, {
            "HUMITRON_MODEL": "mistral",
            "HUMITRON_MAX_STEPS": "10",
            "HUMITRON_TEMPERATURE": "0.5",
            "HUMITRON_LOG_LEVEL": "DEBUG",
        }):
            config = Config.from_env()

            assert config.model == "mistral"
            assert config.max_steps == 10
            assert config.temperature == 0.5
            assert config.log_level == "DEBUG"

    def test_config_to_dict(self):
        """Test config serialization."""
        config = Config(model="test-model", max_steps=5)
        data = config.to_dict()

        assert data["model"] == "test-model"
        assert data["max_steps"] == 5
        assert "temperature" in data


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_from_yaml(self):
        """Test loading config from YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
model: "custom-model"
max_steps: 15
temperature: 0.8
""")
            f.flush()

            try:
                config = load_config(Path(f.name))

                assert config.model == "custom-model"
                assert config.max_steps == 15
                assert config.temperature == 0.8
            finally:
                os.unlink(f.name)

    def test_load_config_env_overrides_yaml(self):
        """Test environment variables override YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("model: yaml-model\n")
            f.flush()

            try:
                with patch.dict(os.environ, {"HUMITRON_MODEL": "env-model"}):
                    config = load_config(Path(f.name))
                    assert config.model == "env-model"
            finally:
                os.unlink(f.name)

    def test_load_config_missing_file(self):
        """Test loading config when file doesn't exist."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config(Path("/nonexistent/config.yaml"))

            # Should fall back to defaults
            assert config.model == "llama3.2"
            assert config.max_steps == 20


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_config(self):
        """Test saving config to YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            try:
                config = Config(model="saved-model", max_steps=7)
                save_config(config, Path(f.name))

                # Reload and verify
                loaded = load_config(Path(f.name))
                assert loaded.model == "saved-model"
                assert loaded.max_steps == 7
            finally:
                os.unlink(f.name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])