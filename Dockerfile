FROM --platform=linux/arm64 python:3.11-slim

# Set working directory to root
WORKDIR /

# Install UV package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy UV project files to root
COPY pyproject.toml uv.lock ./

# Install dependencies using UV
RUN uv sync --frozen --no-dev

# Copy your application code to root
COPY app/ ./app/

# Create directory for SQLite database
RUN mkdir -p ./data

# Set PYTHONPATH to root so 'from app.xxx import' works
ENV PYTHONPATH=/

# Expose port 8080 (REQUIRED by AgentCore)
EXPOSE 8080

# Health check endpoint (REQUIRED by AgentCore)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/ping || exit 1

# Run your application from root
CMD ["uv", "run", "python", "app/agent_entrypoint.py"]
