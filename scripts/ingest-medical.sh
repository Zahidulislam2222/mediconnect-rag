#!/bin/bash
# Ingest medical knowledge into LightRAG
# Run: bash scripts/ingest-medical.sh
#
# Pushes FAQ documents, policies, and subscription info to LightRAG.
# Doctor blog articles should be synced separately from DynamoDB.

LIGHTRAG_URL="${LIGHTRAG_URL:-http://localhost:9621}"
KNOWLEDGE_DIR="$(cd "$(dirname "$0")/../knowledge/medical" && pwd)"

echo "Ingesting medical knowledge into LightRAG at $LIGHTRAG_URL"
echo "Knowledge directory: $KNOWLEDGE_DIR"
echo ""

count=0
failed=0

for file in $(find "$KNOWLEDGE_DIR" -name "*.md" -type f | sort); do
    filename=$(basename "$file")
    echo -n "  Ingesting: $filename ... "

    response=$(curl -s -w "%{http_code}" -X POST "$LIGHTRAG_URL/documents" \
        -H "Content-Type: application/json" \
        -d "{\"content\": $(python3 -c "import json,sys; print(json.dumps(open(sys.argv[1]).read()))" "$file"), \"metadata\": {\"source\": \"$filename\", \"workspace\": \"mediconnect\"}}" \
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
echo "Ingestion complete: $count succeeded, $failed failed"
