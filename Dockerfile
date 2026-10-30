# Dockerfile for QUAN AI BRAIN
# Multi-stage build for production

# ==================== BUILD STAGE
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY pyproject.toml .
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# ==================== TEST STAGE
FROM python:3.11-slim as test

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy source code
COPY . .

# Run tests
RUN python -m pytest tests/ -v --tb=short

# ==================== PRODUCTION STAGE
FROM python:3.11-slim as production

# Create non-root user
RUN groupadd -r quanai && useradd -r -g quanai quanai

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY --chown=quanai:quanai src/ ./src/
COPY --chown=quanai:quanai data/ ./data/
COPY --chown=quanai:quanai tools/ ./tools/
COPY --chown=quanai:quanai docs/ ./docs/
COPY --chown=quanai:quanai pyproject.toml .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/backups && \
    chown -R quanai:quanai /app

# Switch to non-root user
USER quanai

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/v1/memory/health || exit 1

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    APP_ENV=production

# Entry point
ENTRYPOINT ["python", "-m", "quan_ai_brain.web.server"]
CMD ["--host", "0.0.0.0", "--port", "8080"]

# ==================== DEVELOPMENT STAGE
FROM python:3.11 as development

WORKDIR /app

# Install development dependencies
RUN pip install pytest pytest-cov black flake8 mypy ipython

# Copy everything
COPY . .

# Expose port
EXPOSE 8080

# Development entry point
CMD ["python", "-m", "quan_ai_brain.web.server", "--host", "0.0.0.0", "--port", "8080", "--debug"]