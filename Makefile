.PHONY: install test lint format typecheck audit run run-prompt benchmark docker-build docker-run clean all

# Default target
all: install test lint format typecheck audit

# Install from lock file (always!)
install:
	pip install -r requirements-lock.txt

# Install for development
install-dev:
	pip install -e ".[dev]" -r requirements-lock.txt

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

# Security audit with bandit
audit:
	bandit -r src/ -f txt -o bandit-report.txt
	bandit -r src/ -f html -o bandit-report.html
	@echo "Security audit complete. Review bandit-report.html"

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

# Run Docker container (isolated!)
docker-run:
	docker run -it --rm \
		-v $(PWD):/workspace \
		humitron:latest

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Run all checks (tests + lint + format + typecheck + audit)
ci: test lint format typecheck audit
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

# Verify dependencies (audit them!)
verify-deps:
	pip install pip-audit
	pip-audit
	@echo "Dependencies verified. No known vulnerabilities."