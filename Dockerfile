# Humitron - Local-first AI Agent with Security Sandboxing
# Run Humitron in an isolated Docker container for maximum security

# Build stage - for security auditing
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy lock file and install exact dependency versions
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt

# Copy source code
COPY src/ ./src/
COPY config.yaml .
COPY README.md .
COPY SECURITY.md .
COPY SECURITY_AUDIT.md .

# Security audit stage
FROM builder AS auditor

# Install security tools
RUN pip install --no-cache-dir bandit==1.7.9 pip-audit==2.7.3

# Run security audits
RUN mkdir -p /app/security-reports

# Run Bandit (Python security linter)
RUN bandit -r src/ -f html -o /app/security-reports/bandit-report.html || true
RUN bandit -r src/ -f txt -o /app/security-reports/bandit-report.txt || true

# Run pip-audit (dependency vulnerability scanner)
RUN pip-audit -r requirements-lock.txt --output /app/security-reports/pip-audit-report.json || true

# Check: fail build if high-severity issues found
RUN bandit -r src/ -ll && echo "✅ No high-severity issues found"

# Runtime stage
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create non-root user for runtime (security best practice)
RUN useradd -m -u 1000 humitron && \
    mkdir -p /app/workspace /app/trajectories && \
    chown -R humitron:humitron /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app /app
COPY --from=auditor /app/security-reports /app/security-reports

# Set ownership
RUN chown -R humitron:humitron /app

USER humitron

# Volume for workspace (mounted from host)
VOLUME ["/app/workspace"]

# Expose ports
EXPOSE 8000 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run Humitron backend server
ENTRYPOINT ["python", "-m", "humitron.api.server", "--host", "0.0.0.0", "--port", "8000"]

# Alternative: Run in CLI mode
# ENTRYPOINT ["python", "-m", "humitron.ui.cli"]