#!/usr/bin/env bash
# deploy-indexes.sh — Deploy Azure AI Search index definitions via REST API.
# Usage: ./search/deploy-indexes.sh
#
# Required environment variables:
#   AZURE_SEARCH_ENDPOINT   — e.g. https://my-search-service.search.windows.net
#   AZURE_SEARCH_ADMIN_KEY  — Admin API key for the search service
#   AZURE_OPENAI_ENDPOINT   — Used to populate the vectorizer resourceUri in index JSON
#
# Optional:
#   SEARCH_API_VERSION      — Default: 2024-05-01-preview

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INDEX_DIR="${SCRIPT_DIR}/indexes"
API_VERSION="${SEARCH_API_VERSION:-2024-05-01-preview}"

# ── Validate required variables ──────────────────────────────────────────────
: "${AZURE_SEARCH_ENDPOINT:?AZURE_SEARCH_ENDPOINT must be set}"
: "${AZURE_SEARCH_ADMIN_KEY:?AZURE_SEARCH_ADMIN_KEY must be set}"
: "${AZURE_OPENAI_ENDPOINT:?AZURE_OPENAI_ENDPOINT must be set}"

echo "==> Deploying Azure AI Search indexes"
echo "    Search service : ${AZURE_SEARCH_ENDPOINT}"
echo "    OpenAI endpoint: ${AZURE_OPENAI_ENDPOINT}"
echo "    API version    : ${API_VERSION}"
echo ""

# ── Helper: deploy one index ──────────────────────────────────────────────────
deploy_index() {
    local index_file="$1"
    local index_name
    index_name=$(python3 -c "import json,sys; print(json.load(open('${index_file}'))['name'])")

    echo "--> Deploying index: ${index_name} (from $(basename "${index_file}"))"

    # Substitute AZURE_OPENAI_ENDPOINT placeholder in the JSON before uploading.
    local payload
    payload=$(sed "s|\${AZURE_OPENAI_ENDPOINT}|${AZURE_OPENAI_ENDPOINT}|g" "${index_file}")

    local url="${AZURE_SEARCH_ENDPOINT}/indexes/${index_name}?api-version=${API_VERSION}"

    http_status=$(echo "${payload}" | curl -s -o /dev/null -w "%{http_code}" \
        -X PUT "${url}" \
        -H "Content-Type: application/json" \
        -H "api-key: ${AZURE_SEARCH_ADMIN_KEY}" \
        --data-binary @-)

    if [[ "${http_status}" == "200" ]]; then
        echo "    [OK] Index updated (HTTP ${http_status})"
    elif [[ "${http_status}" == "201" ]]; then
        echo "    [OK] Index created (HTTP ${http_status})"
    else
        echo "    [ERROR] Unexpected HTTP status ${http_status} for index ${index_name}" >&2
        exit 1
    fi
}

# ── Deploy all three indexes ──────────────────────────────────────────────────
deploy_index "${INDEX_DIR}/kb-articles-index.json"
deploy_index "${INDEX_DIR}/incident-content-index.json"
deploy_index "${INDEX_DIR}/attachments-index.json"

echo ""
echo "==> All indexes deployed successfully."
echo ""

# ── Optional: list indexes to confirm ────────────────────────────────────────
echo "--> Listing indexes on service:"
curl -s -X GET \
    "${AZURE_SEARCH_ENDPOINT}/indexes?api-version=${API_VERSION}&\$select=name,fields" \
    -H "api-key: ${AZURE_SEARCH_ADMIN_KEY}" | \
    python3 -c "
import json, sys
data = json.load(sys.stdin)
for idx in data.get('value', []):
    field_count = len(idx.get('fields', []))
    print(f'  • {idx[\"name\"]} ({field_count} fields)')
"
