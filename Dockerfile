# ImaniPay Blockchain Service Dockerfile
# Multi-stage build for optimized production image

# ========================================================================
# Stage 1: Build Dependencies
# ========================================================================
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# ========================================================================
# Stage 2: Runtime Image
# ========================================================================
FROM python:3.11-slim as runtime

# Set metadata labels
LABEL maintainer="ImaniPay Team <dev@imanipay.com>" \
      org.opencontainers.image.title="ImaniPay Blockchain Service" \
      org.opencontainers.image.description="Cross-border payment platform for Africa" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/imanipay-africa/imanipay-blockchain-service" \
      org.opencontainers.image.url="https://imanipay.com" \
      org.opencontainers.image.vendor="ImaniPay" \
      org.opencontainers.image.licenses="MIT"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    ENVIRONMENT=production \
    PORT=8000

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r imanipay && \
    useradd -r -g imanipay -d /app -s /bin/bash imanipay

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create application directory
WORKDIR /app

# Copy application code
COPY --chown=imanipay:imanipay . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R imanipay:imanipay /app

# Switch to non-root user
USER imanipay

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ========================================================================
# Stage 3: Development Image (Optional)
# ========================================================================
FROM runtime as development

# Switch back to root for development tools installation
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    htop \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy development requirements
COPY requirements-dev.txt /tmp/requirements-dev.txt

# Install development Python packages
RUN pip install --no-cache-dir -r /tmp/requirements-dev.txt

# Switch back to non-root user
USER imanipay

# Override command for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ========================================================================
# Build Instructions:
# ========================================================================
# 
# Build production image:
# docker build --target runtime -t imanipay-blockchain-service:latest .
#
# Build development image:
# docker build --target development -t imanipay-blockchain-service:dev .
#
# Build with build args:
# docker build \
#   --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
#   --build-arg VERSION=1.0.0 \
#   --build-arg VCS_REF=$(git rev-parse --short HEAD) \
#   -t imanipay-blockchain-service:latest .
#
# Run container:
# docker run -d \
#   --name imanipay-api \
#   -p 8000:8000 \
#   --env-file .env.production \
#   imanipay-blockchain-service:latest
#
# ========================================================================

