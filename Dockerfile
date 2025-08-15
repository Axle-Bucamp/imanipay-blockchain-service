# ImaniPay Blockchain Service Dockerfile (UV-based)
# Multi-stage build for optimized production image

# ========================================================================
# Stage 1: Build Dependencies
# ========================================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm as builder

ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Install build dependencies
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
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY . .

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python dependencies using uv
RUN uv pip install .

# ========================================================================
# Stage 2: Runtime Image
# ========================================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm as runtime

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

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    ENVIRONMENT=production \
    PORT=8000 \
    UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN groupadd -r imanipay && \
    useradd -r -g imanipay -d /app -s /bin/bash imanipay

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=imanipay:imanipay . .

RUN mkdir -p /app/logs /app/data && \
    chown -R imanipay:imanipay /app

USER imanipay

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use uv to run uvicorn
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ========================================================================
# Stage 3: Development Image
# ========================================================================
FROM runtime as development
USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    htop \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python dependencies using uv
RUN uv pip install .

USER imanipay

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
