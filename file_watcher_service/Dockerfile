# ============================================================================
# Multi-Stage Build for File Watcher Service
# Lightweight event-driven file monitoring service
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Minimal build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal runtime image
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/

# Create directories for watched folder and processed tracking
RUN mkdir -p /data/watch /data/processed

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1

CMD ["python", "-m", "app.main"]
