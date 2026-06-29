.PHONY: install test run clean lint format typecheck help

# Default target
help:
	@echo "Humitron - Local-first AI Agent"
	@echo ""
	@echo "Available commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make test        - Run test suite"
	@echo "  make run         - Run the CLI agent"
	@echo "  make clean       - Remove cache files"
	@echo "  make lint        - Run ruff linter"
	@echo "  make format      - Format code with black"
	@echo "  make typecheck   - Run mypy type checker"
	@echo "  make all         - Run format, lint, typecheck, test"

# Install dependencies
install:
	pip install -e ".[dev]"

# Run tests
test:
	python -m pytest tests/ -v

# Run the CLI agent
run:
	python -m humitron.ui.cli

# Run with a prompt
run-prompt:
	python -m humitron.ui.cli "$(PROMPT)"

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/ 2>/dev/null || true

# Run linter
lint:
	ruff check src/ tests/

# Format code
format:
	black src/ tests/

# Type check
typecheck:
	mypy src/

# Run all checks
all: format lint typecheck test

# Docker commands
docker-build:
	docker build -t humitron:latest .

docker-run:
	docker run -it --rm -v $(PWD):/workspace humitron:latest

# Development setup
dev-setup: install
	pre-commit install

# Benchmark
benchmark:
	python scripts/benchmark.py --queries 10 --steps 5