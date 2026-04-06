FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for document processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY process.py .
COPY config.py .

# Create data directories
RUN mkdir -p /app/data /app/output /app/storage

VOLUME ["/app/data", "/app/output", "/app/storage"]

ENTRYPOINT ["python", "process.py"]
