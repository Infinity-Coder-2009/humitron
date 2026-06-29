.PHONY: install test lint format typecheck run run-prompt benchmark docker-build docker-run clean all

# Default target
all: install test lint format typecheck

# Install dependencies
install:
	pip install -e ".[dev]"

# Run tests
test:
	pytest tests/ -v

# Lint with ruff
lint:
	ruff check src/ tests/

# Format with black
format:
	black src/ tests/

# Type check with mypy
typecheck:
	mypy src/

# Run interactive chat
run:
	python -m humitron.ui.cli

# Run single prompt
run-prompt:
	python -m humitron.ui.cli $(PROMPT)

# Run with custom options
run-custom:
	python -m humitron.ui.cli --model $(MODEL) --max-steps $(STEPS) "$(PROMPT)"

# Benchmark
benchmark:
	python scripts/benchmark.py --model $(MODEL) --queries $(QUERIES)

# Build Docker image
docker-build:
	docker build -t humitron:latest .

# Run Docker container
docker-run:
	docker run -it --rm \
		-v $(PWD):/workspace \
		-v /var/run/docker.sock:/var/run/docker.sock \
		humitron:latest

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Run all checks
ci: test lint format typecheck
	@echo "All checks passed!"

# Development: run with auto-reload
dev:
	python -m humitron.ui.cli --log-level DEBUG

# Build Python backend executable
build-backend:
	python scripts/build_backend.py

# Package for distribution
package: clean install build-backend
	@echo "Package ready in dist/"