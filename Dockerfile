# Recon — The Integration Readiness Engine
# Production Container Image

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy packaging configuration and install dependencies
COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install "fastapi>=0.104.0" "uvicorn[standard]>=0.24.0" "pydantic>=2.4.0" "python-multipart>=0.0.6" "click>=8.1.0"

# Copy application source tree
COPY src/ ./src/
COPY benchmarks/ ./benchmarks/

# Install recon package in non-editable mode
RUN pip install .

# Create non-root user for security hardening
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["python", "-m", "recon.cli", "serve", "--host", "0.0.0.0", "--port", "8000"]
