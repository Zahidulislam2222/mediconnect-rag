FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies for document processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    wget \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY process.py .
COPY config.py .
COPY settings.py .
COPY processor.json .
COPY gemini_adapter.py .
COPY engine_adapter.py .

# Cache public tokenizer data at build time for network-isolated runtime.
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache
RUN python -c "import json,tiktoken; tiktoken.encoding_for_model(json.load(open('processor.json'))['tokenizer_model'])"

# Create data directories
ARG RAGANYTHING_UID=1000
RUN useradd --create-home --uid ${RAGANYTHING_UID} app \
    && mkdir -p /app/data /app/output /app/storage \
    && chown -R app:app /app

USER app

VOLUME ["/app/data", "/app/output", "/app/storage"]

ENTRYPOINT ["python", "process.py"]
