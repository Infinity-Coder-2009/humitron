# Humitron Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY config.yaml .env.example ./

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Create workspace directory
RUN mkdir -p /workspace

# Expose health check port
EXPOSE 8080

# Default command
CMD ["python", "-m", "humitron.ui.cli"]