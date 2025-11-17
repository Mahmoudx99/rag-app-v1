FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install base requirements (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the sentence-transformer model during build
# This prevents runtime downloads and network requests
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy and install chat/LLM integration requirements (separate layer)
COPY requirements-chat.txt .
RUN pip install --no-cache-dir -r requirements-chat.txt

# Copy application code
COPY app/ /app/app/

# Create data directories
RUN mkdir -p /data/uploads /data/chromadb

# Set environment variables to use offline mode at runtime
# This prevents the model from trying to check for updates
ENV TRANSFORMERS_OFFLINE=1
ENV HF_HUB_OFFLINE=1
ENV HF_DATASETS_OFFLINE=1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
