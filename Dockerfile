# Multi-stage build for Humitron
# Run in isolation: docker run -it humitron

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy lock file for reproducible builds
COPY requirements-lock.txt .

# Install from lock file (NOT requirements.txt)
RUN pip install --no-cache-dir -r requirements-lock.txt

# Copy source code
COPY src/ ./src/
COPY config.yaml .

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app /app

# Create non-root user for security
RUN useradd -m -u 1000 humitron && chown -R humitron:humitron /app
USER humitron

# Expose ports
EXPOSE 8000 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command
CMD ["python", "-m", "humitron.api.server", "--host", "0.0.0.0", "--port", "8000"]