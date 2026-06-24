# Azure AI Search — Index Setup

This folder contains the Azure AI Search index definitions and deployment tooling for the Autoliv ServiceNow Fabric POC retrieval layer.

## Indexes

| Index | File | Purpose |
|---|---|---|
| `kb-articles-index` | `indexes/kb-articles-index.json` | KB article full-text + vector search |
| `incident-content-index` | `indexes/incident-content-index.json` | Work notes, resolution notes, descriptions |
| `attachments-index` | `indexes/attachments-index.json` | Attachment metadata keyword + vector search |

All indexes use **1536-dimension vectors** (text-embedding-ada-002) and support hybrid search (BM25 + HNSW cosine).

---

## Prerequisites

- Azure AI Search service (Basic tier or above for semantic search)
- Azure OpenAI deployment of `text-embedding-ada-002`
- `curl` and `python3` available in your shell (for `deploy-indexes.sh`)

---

## Configuration

Set the following environment variables before deploying:

```bash
export AZURE_SEARCH_ENDPOINT="https://<your-service>.search.windows.net"
export AZURE_SEARCH_ADMIN_KEY="<your-admin-key>"
export AZURE_OPENAI_ENDPOINT="https://<your-openai>.openai.azure.com"
```

Optionally override the API version (defaults to `2024-05-01-preview`):

```bash
export SEARCH_API_VERSION="2024-05-01-preview"
```

---

## Deploy Indexes

```bash
chmod +x search/deploy-indexes.sh
./search/deploy-indexes.sh
```

The script uses HTTP `PUT` (create-or-update) against the Azure AI Search REST API. Each index is deployed idempotently — re-running the script safely updates existing indexes.

---

## Query Utilities

`query_utils.py` in this folder provides Python functions for hybrid search across all three indexes:

```python
from search.query_utils import search_kb_articles, search_incidents, search_attachments

results = search_kb_articles("password reset fails", filters={"category": "Authentication"}, top=5)
for r in results:
    print(r["title"], r["score"])
```

See `query_utils.py` for full API documentation.

---

## Index Schema Notes

### `kb-articles-index`
- **Key field:** `id` (format: `kb_{article_id}`)
- **Vector field:** `vector` (1536-dim cosine HNSW)
- **Semantic config:** title → content → category/subcategory
- **Scoring boosts:** `useful_count`, `view_count`, freshness (90-day window)

### `incident-content-index`
- **Key field:** `id` (format: `incident_{incident_id}_{content_type}`)
- **`content_type`:** one of `description`, `work_notes`, `resolution_notes`
- **Vector field:** `vector` (1536-dim cosine HNSW)
- **Semantic config:** summary → resolution_notes → work_notes → description

### `attachments-index`
- **Key field:** `id` (format: `attachment_{attachment_id}`)
- **Vector field:** `vector` (1536-dim, embedded from `file_name + description`)
- **No scoring profile** — keyword + filter-based search is primary pattern

---

## Environment Variable Reference

| Variable | Required | Description |
|---|---|---|
| `AZURE_SEARCH_ENDPOINT` | Yes | Search service base URL |
| `AZURE_SEARCH_ADMIN_KEY` | Yes | Admin API key |
| `AZURE_OPENAI_ENDPOINT` | Yes | OpenAI resource URI for vectorizer |
| `AZURE_OPENAI_API_KEY` | For queries | API key used by `query_utils.py` |
| `SEARCH_API_VERSION` | No | Defaults to `2024-05-01-preview` |
