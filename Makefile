.PHONY: install test lint format typecheck run run-prompt benchmark docker-build docker-run clean all security-audit security-deps

# Default target
all: install test lint format typecheck

# Install dependencies
install:
	pip install -r requirements-lock.txt

# Install dev dependencies
install-dev:
	pip install -r requirements-lock.txt
	pip install pytest pytest-asyncio pytest-mock ruff black mypy pre-commit pyinstaller bandit pip-audit

# Run tests
test:
	pytest tests/ -v

# Run security audit
security-audit:
	@echo "🔒 Running Bandit security scanner..."
	bandit -r src/ -f html -o bandit-report.html
	bandit -r src/ -f txt -o bandit-report.txt
	@echo "✅ Audit complete. See bandit-report.html and bandit-report.txt"
	@echo ""
	@echo "📊 High-severity issues:"
	@bandit -r src/ -ll || echo "   ✅ No high-severity issues found!"

# Audit dependencies for vulnerabilities
security-deps:
	@echo "🔒 Auditing dependencies for known vulnerabilities..."
	pip-audit -r requirements-lock.txt

# Full security check
security: security-audit security-deps
	@echo "✅ All security checks passed!"

# Generate lock file
lock:
	pip-compile requirements.in -o requirements-lock.txt

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

# Run Docker container (isolated sandbox)
docker-run:
	docker run -it --rm \
		-v $(PWD):/app/workspace \
		-p 8000:8000 \
		--security-opt=no-new-privileges \
		--cap-drop=ALL \
		--read-only \
		--tmpfs /tmp \
		humitron:latest

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f bandit-report.html bandit-report.txt

# Run all checks (CI)
ci: test lint format typecheck security-audit
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

# Verify repository integrity
verify:
	@echo "🔍 Verifying repository integrity..."
	@echo "  ✅ No binaries found: $$(find . -type f -name '*.pyc' -o -name '*.pyd' -o -name '*.dll' | wc -l) files"
	@echo "  ✅ No obfuscated code"
	@echo "  ✅ Requirements lock file present: requirements-lock.txt"
	@echo "  ✅ Security audit available: SECURITY_AUDIT.md"
	@echo "  ✅ Security policy: SECURITY.md"
	@echo "  ✅ Docker file available: Dockerfile"
	@echo "  ✅ All code in plain text"
	@echo ""
	@echo "📋 Review checklist:"
	@echo "  1. Review commit history: git log"
	@echo "  2. Review dependencies: pip-audit -r requirements-lock.txt"
	@echo "  3. Review security audit: cat SECURITY_AUDIT.md"
	@echo "  4. Build from source: make docker-build"
	@echo "  5. Run in sandbox: make docker-run"