#!/bin/bash
# Enhanced ingestion: generate hypothetical questions, then ingest into LightRAG
#
# This script:
#   1. Generates HyDE questions for all knowledge base documents
#   2. Ingests the augmented documents into LightRAG
#
# Usage: bash scripts/ingest-with-questions.sh
#
# Prerequisites:
#   - GEMINI_API_KEY set in environment (or .env file)
#   - LightRAG running at LIGHTRAG_URL (default: http://localhost:9621)
#   - Python 3.10+ and scripts/requirements-hyde.txt dependencies installed

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ "${1-}" != "--environment-loaded" ]; then
    exec python3 "$SCRIPT_DIR/ingestion_environment.py" "$@"
fi
shift
LIGHTRAG_URL="${LIGHTRAG_URL:-http://localhost:9621}"
KNOWLEDGE_DIR="$(cd "$SCRIPT_DIR/../knowledge/medical" && pwd)"
AUGMENTED_DIR="$KNOWLEDGE_DIR/augmented"

echo "═══════════════════════════════════════════════════════"
echo "  MediConnect Enhanced RAG Ingestion (HyDE + LightRAG)"
echo "═══════════════════════════════════════════════════════"
echo ""

# Check prerequisites
if [ -z "$GEMINI_API_KEY" ]; then
    echo "ERROR: GEMINI_API_KEY is required. Set it in environment or configs/.env"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 is required"
    exit 1
fi

# ── Step 1: Generate hypothetical questions ─────────────────────────
echo "Step 1: Generating hypothetical questions..."
echo ""

python3 "$SCRIPT_DIR/generate-questions.py" \
    --dir "$KNOWLEDGE_DIR/faqs" \
    --output "$AUGMENTED_DIR/faqs"

python3 "$SCRIPT_DIR/generate-questions.py" \
    --dir "$KNOWLEDGE_DIR/policies" \
    --output "$AUGMENTED_DIR/policies"

echo ""

# ── Step 2: Ingest augmented documents into LightRAG ────────────────
echo "Step 2: Ingesting augmented documents into LightRAG at $LIGHTRAG_URL"
echo ""

count=0
failed=0

for file in $(find "$AUGMENTED_DIR" -name "*.md" -type f | sort); do
    filename=$(basename "$file")
    echo -n "  Ingesting: $filename ... "

    response=$(curl -s -w "%{http_code}" -X POST "$LIGHTRAG_URL/documents" \
        -H "Content-Type: application/json" \
        -d "{\"content\": $(python3 -c "import json,sys; print(json.dumps(open(sys.argv[1]).read()))" "$file"), \"metadata\": {\"source\": \"$filename\", \"workspace\": \"mediconnect\", \"augmented\": true}}" \
        -o /dev/null)

    if [ "$response" = "200" ] || [ "$response" = "201" ]; then
        echo "OK"
        count=$((count + 1))
    else
        echo "FAILED (HTTP $response)"
        failed=$((failed + 1))
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Ingestion complete: $count succeeded, $failed failed"
echo "  Augmented docs at: $AUGMENTED_DIR"
echo "═══════════════════════════════════════════════════════"
