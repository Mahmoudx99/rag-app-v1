# ============================================================================
# Multi-Stage Build for Backend Service
# Optimized for CPU-only execution (no GPU dependencies)
# Reduces image size from ~7GB to ~2-3GB
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Builder - Install build dependencies and compile packages
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build-time system dependencies
# These are only needed for compiling packages, not runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt requirements-chat.txt ./

# Install Python packages to /install directory
# Using --prefix to install to custom location for easy copying
RUN pip install --no-cache-dir --prefix=/install \
    -r requirements.txt \
    -r requirements-chat.txt

# ----------------------------------------------------------------------------
# Stage 2: Model Downloader - Download ML models in separate layer
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS model-downloader

# Copy Python packages from builder
COPY --from=builder /install /usr/local

# Download sentence-transformer model
# This layer is cached separately and only rebuilds if model changes
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('all-MiniLM-L6-v2')"

# ----------------------------------------------------------------------------
# Stage 3: Runtime - Minimal runtime image
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install only runtime system dependencies (if any needed)
# Most build tools are NOT needed at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy pre-downloaded models from model-downloader stage
COPY --from=model-downloader /root/.cache /root/.cache

# Copy application code (changes frequently, so this is last)
COPY app/ /app/app/

# Create data directories
RUN mkdir -p /data/watch /data/processed

# Set environment variables
# Offline mode prevents runtime downloads and checks
ENV TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
