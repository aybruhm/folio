# Base stage - build dependencies
FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=UTF-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY api/pyproject.toml .
COPY api/uv.lock .
RUN pip install uv && uv pip install --system -t /install -r pyproject.toml


# Runtime stage - hardened image
FROM dhi.io/python:3.13-debian12

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=UTF-8

WORKDIR /app

USER 78545:78545

# Copy Python dependencies only (no build tools needed at runtime)
COPY --chown=78545:78545 --from=builder /install /opt/python/lib/python3.13/site-packages
COPY --chown=78545:78545 api/ .

EXPOSE 8000
