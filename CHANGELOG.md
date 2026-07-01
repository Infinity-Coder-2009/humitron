# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-06-29

### Added
- Full cloud provider support (OpenAI, Anthropic, OpenRouter) via unified LLM provider abstraction
- Streaming SSE responses in FastAPI backend
- Real-time cost tracking per session
- Tauri desktop app with native sidecar for Python backend
- Welcome wizard for first-run setup (Ollama check, model pull, workspace selection)
- Dark/light theme with system detection
- Session management (create, rename, delete, switch)
- GitHub Actions workflows for CI and cross-platform installer builds
- PyInstaller bundling for single-file backend executable
- Comprehensive test suite (tools, memory, agent, config, JSON parsing)
- MCP (Model Context Protocol) client integration
- Trajectory logging for debugging/evaluation
- Token budget management with automatic summarization

### Changed
- Refactored entire codebase into clean, maintainable package structure
- Replaced monolithic `humitron_core.py` with modular `src/humitron/` package
- Migrated from single-file to proper Python package with `pyproject.toml`

### Fixed
- JSON parsing retry logic for malformed LLM responses
- Path sandboxing for all file operations
- Command injection prevention in bash executor
- Token counting for cost estimation

## [0.1.0] - 2024-06-15

### Added
- Initial ReAct agent implementation
- Basic tool set (read_file, write_file, bash_execute, web_search)
- Ollama integration
- Simple CLI interface
- Configuration via YAML and environment variables