# RAG-Anything — Multimodal Document Processor

Processes PDFs, Office docs, images, tables, equations through RAG-Anything (built on LightRAG) with Gemini 2.5 Flash.

## Usage

```bash
# Build the image first (one time)
cd configs
docker compose --profile rag build raganything

# Process a single document
docker compose --profile rag run --rm raganything /app/data/inputs/document.pdf

# Process all documents in the inputs directory
docker compose --profile rag run --rm raganything --dir /app/data/inputs/

# Query the knowledge base after processing
docker compose --profile rag run --rm raganything --query "What are the main findings?" --mode hybrid
```

## Query Modes
- `naive` — Simple keyword matching
- `local` — Local context search
- `global` — Global knowledge graph search
- `hybrid` — Combined local + global (recommended)

## Files
- `Dockerfile` — Container image definition
- `requirements.txt` — Python dependencies (raganything 1.2.10)
- `config.py` — Gemini LLM/embedding/vision model configuration
- `process.py` — CLI tool for processing documents and querying

## Configuration
Uses the same `GEMINI_API_KEY`, `LLM_MODEL`, `EMBEDDING_MODEL`, and `EMBEDDING_DIM` from `configs/.env`.

## Data Directories
- `/app/data` — Mounted from `lightrag/data/` (shared with LightRAG)
- `/app/output` — Parsed document output (mounted from `ragAnything/output/`)
- `/app/storage` — RAG-Anything knowledge graph storage (mounted from `ragAnything/storage/`)
