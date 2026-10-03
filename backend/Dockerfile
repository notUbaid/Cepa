FROM python:3.12-slim

WORKDIR /app

# Install system utilities and multimedia libraries for image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU first to prevent heavy GPU package downloads
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend codebase
COPY . .

# Ensure storage, weights, and static directories exist and configure non-root user
RUN useradd -u 10001 -m -s /bin/bash appuser && \
    mkdir -p storage weights static && \
    chown -R appuser:appuser /app

USER appuser

# Configure production environment
ENV BACKEND_ENV=production \
    PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
