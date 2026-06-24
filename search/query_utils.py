"""
query_utils.py — Azure AI Search query utilities for the ServiceNow retrieval layer.

All functions use the Azure AI Search REST API directly (no SDK) for portability
across Fabric notebooks, local scripts, and cloud functions.

Required environment variables:
    AZURE_SEARCH_ENDPOINT   — e.g. https://my-service.search.windows.net
    AZURE_SEARCH_ADMIN_KEY  — Admin or query API key
    AZURE_OPENAI_ENDPOINT   — e.g. https://my-openai.openai.azure.com
    AZURE_OPENAI_API_KEY    — Azure OpenAI API key
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT — defaults to "text-embedding-ada-002"
    SEARCH_API_VERSION      — defaults to "2024-05-01-preview"
"""

from __future__ import annotations

import os
from typing import Any

import requests

# ── Configuration ─────────────────────────────────────────────────────────────

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
API_VERSION = os.getenv("SEARCH_API_VERSION", "2024-05-01-preview")
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

_SEARCH_HEADERS = {
    "Content-Type": "application/json",
    "api-key": SEARCH_API_KEY,
}


# ── Embedding helper ──────────────────────────────────────────────────────────

def _get_embedding(text: str) -> list[float]:
    """Generate a 1536-dim embedding via Azure OpenAI text-embedding-ada-002."""
    url = (
        f"{OPENAI_ENDPOINT}/openai/deployments/{EMBEDDING_DEPLOYMENT}"
        f"/embeddings?api-version={OPENAI_API_VERSION}"
    )
    payload = {"input": text, "model": EMBEDDING_DEPLOYMENT}
    headers = {"Content-Type": "application/json", "api-key": OPENAI_API_KEY}
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


# ── Internal search dispatcher ────────────────────────────────────────────────

def _hybrid_search(
    index_name: str,
    query: str,
    vector_field: str,
    select_fields: list[str],
    semantic_config: str,
    filters: dict[str, Any] | None = None,
    top: int = 5,
) -> list[dict[str, Any]]:
    """
    Execute a hybrid search (BM25 + vector) with optional OData filter string.

    ``filters`` may be either:
    - A plain dict mapping field name → value (e.g. ``{"category": "Network"}``)
    - A dict with a single ``"$filter"`` key containing a raw OData expression
    """
    url = f"{SEARCH_ENDPOINT}/indexes/{index_name}/docs/search?api-version={API_VERSION}"

    embedding = _get_embedding(query)

    odata_filter = _build_filter(filters)

    payload: dict[str, Any] = {
        "search": query,
        "searchMode": "any",
        "queryType": "semantic",
        "semanticConfiguration": semantic_config,
        "vectorQueries": [
            {
                "kind": "vector",
                "vector": embedding,
                "fields": vector_field,
                "k": top * 2,
            }
        ],
        "select": ", ".join(select_fields),
        "top": top,
        "captions": "extractive",
        "answers": "extractive|count-3",
    }

    if odata_filter:
        payload["filter"] = odata_filter

    response = requests.post(url, json=payload, headers=_SEARCH_HEADERS, timeout=30)
    response.raise_for_status()
    return response.json().get("value", [])


def _keyword_search(
    index_name: str,
    query: str,
    select_fields: list[str],
    filters: dict[str, Any] | None = None,
    top: int = 5,
) -> list[dict[str, Any]]:
    """Execute a keyword-only (BM25) search with optional OData filter."""
    url = f"{SEARCH_ENDPOINT}/indexes/{index_name}/docs/search?api-version={API_VERSION}"

    odata_filter = _build_filter(filters)

    payload: dict[str, Any] = {
        "search": query or "*",
        "searchMode": "any",
        "queryType": "simple",
        "select": ", ".join(select_fields),
        "top": top,
    }

    if odata_filter:
        payload["filter"] = odata_filter

    response = requests.post(url, json=payload, headers=_SEARCH_HEADERS, timeout=30)
    response.raise_for_status()
    return response.json().get("value", [])


def _build_filter(filters: dict[str, Any] | None) -> str:
    """Convert a simple field→value dict into an OData filter expression.

    Pass ``{"$filter": "..."}`` to use a raw OData string directly.
    """
    if not filters:
        return ""
    if "$filter" in filters:
        return filters["$filter"]

    clauses: list[str] = []
    for field, value in filters.items():
        if isinstance(value, list):
            inner = " or ".join(f"{field} eq '{v}'" for v in value)
            clauses.append(f"({inner})")
        elif isinstance(value, str):
            clauses.append(f"{field} eq '{value}'")
        elif isinstance(value, (int, float)):
            clauses.append(f"{field} eq {value}")
        elif isinstance(value, bool):
            clauses.append(f"{field} eq {'true' if value else 'false'}")
    return " and ".join(clauses)


# ── Public API ────────────────────────────────────────────────────────────────

def search_kb_articles(
    query: str,
    filters: dict[str, Any] | None = None,
    top: int = 5,
) -> list[dict[str, Any]]:
    """
    Hybrid search (BM25 + vector) over the kb-articles-index.

    Args:
        query:   Natural language search query.
        filters: Optional field filters, e.g. ``{"category": "Security"}``.
                 Supports list values for OR matching, e.g. ``{"category": ["Network", "VPN"]}``.
                 Pass ``{"$filter": "<odata>"}`` for a raw OData expression.
        top:     Maximum number of results to return (default 5).

    Returns:
        List of formatted retrieval result dicts (see ``format_retrieval_result``).
    """
    select_fields = [
        "id", "article_id", "title", "content", "category", "subcategory",
        "created_date", "updated_date", "view_count", "useful_count", "source_url",
    ]
    hits = _hybrid_search(
        index_name="kb-articles-index",
        query=query,
        vector_field="vector",
        select_fields=select_fields,
        semantic_config="kb-semantic-config",
        filters=filters,
        top=top,
    )
    return [format_retrieval_result(hit, source_type="kb_article") for hit in hits]


def search_incidents(
    query: str,
    filters: dict[str, Any] | None = None,
    top: int = 5,
) -> list[dict[str, Any]]:
    """
    Hybrid search (BM25 + vector) over the incident-content-index.

    Typical filter patterns:
        - Closed tickets: ``{"incident_state": "closed"}``
        - By category:    ``{"category": "Database", "incident_state": "closed"}``
        - By priority:    ``{"priority": ["1", "2"]}``
        - Raw OData:      ``{"$filter": "resolution_time_minutes lt 480"}``

    Args:
        query:   Natural language search query.
        filters: Optional field filters (see above).
        top:     Maximum number of results to return (default 5).

    Returns:
        List of formatted retrieval result dicts (see ``format_retrieval_result``).
    """
    select_fields = [
        "id", "incident_id", "incident_state", "incident_summary",
        "description", "work_notes", "resolution_notes", "content_type",
        "priority", "category", "subcategory", "assigned_group", "business_service",
        "created_date", "updated_date", "closed_date",
        "resolution_time_minutes", "reopen_count", "incident_url",
    ]
    hits = _hybrid_search(
        index_name="incident-content-index",
        query=query,
        vector_field="vector",
        select_fields=select_fields,
        semantic_config="incident-semantic-config",
        filters=filters,
        top=top,
    )
    return [format_retrieval_result(hit, source_type="incident") for hit in hits]


def search_attachments(
    query: str,
    filters: dict[str, Any] | None = None,
    top: int = 5,
) -> list[dict[str, Any]]:
    """
    Keyword search over the attachments-index.

    Typical filter patterns:
        - By incident:         ``{"incident_id": "INC0123456"}``
        - By type:             ``{"attachment_type": ["log", "script"]}``
        - By incident + type:  ``{"incident_id": "INC0123456", "attachment_type": "log"}``

    Args:
        query:   Free-text search query (searches file_name and description).
        filters: Optional field filters (see above).
        top:     Maximum number of results to return (default 5).

    Returns:
        List of formatted retrieval result dicts (see ``format_retrieval_result``).
    """
    select_fields = [
        "id", "attachment_id", "file_name", "file_type", "description",
        "incident_id", "kb_article_id", "document_id", "attachment_type",
        "uploaded_date", "size_bytes", "mock_url", "incident_url",
    ]
    hits = _keyword_search(
        index_name="attachments-index",
        query=query,
        select_fields=select_fields,
        filters=filters,
        top=top,
    )
    return [format_retrieval_result(hit, source_type="attachment") for hit in hits]


# ── Result formatter ──────────────────────────────────────────────────────────

def format_retrieval_result(
    hit: dict[str, Any],
    source_type: str | None = None,
) -> dict[str, Any]:
    """
    Normalise a raw Azure AI Search hit into the standard grounding format:

    {
        "source_type": "kb_article" | "incident" | "attachment",
        "source_id":   "<article_id | incident_id | attachment_id>",
        "title":       "<human-readable title>",
        "snippet":     "<most relevant text excerpt>",
        "url":         "<deep link to source record>",
        "score":       0.85,
        "metadata":    { ... }
    }
    """
    score = hit.get("@search.score", 0.0)

    # Prefer semantic captions as the snippet when available.
    captions = hit.get("@search.captions", [])
    snippet = captions[0].get("text", "") if captions else ""

    detected_type = source_type or _infer_source_type(hit)

    if detected_type == "kb_article":
        source_id = hit.get("article_id", hit.get("id", ""))
        title = hit.get("title", "")
        snippet = snippet or (hit.get("content", "") or "")[:300]
        url = hit.get("source_url", "")
        metadata = {
            "category": hit.get("category"),
            "subcategory": hit.get("subcategory"),
            "created_date": hit.get("created_date"),
            "updated_date": hit.get("updated_date"),
            "view_count": hit.get("view_count"),
            "useful_count": hit.get("useful_count"),
        }

    elif detected_type == "incident":
        source_id = hit.get("incident_id", hit.get("id", ""))
        title = hit.get("incident_summary", f"Incident {source_id}")
        content_type = hit.get("content_type", "")
        body = (
            hit.get("resolution_notes")
            or hit.get("work_notes")
            or hit.get("description")
            or ""
        )
        snippet = snippet or body[:300]
        if content_type and not snippet.startswith(content_type):
            snippet = f"[{content_type}] {snippet}"
        url = hit.get("incident_url", "")
        metadata = {
            "incident_state": hit.get("incident_state"),
            "content_type": content_type,
            "priority": hit.get("priority"),
            "category": hit.get("category"),
            "subcategory": hit.get("subcategory"),
            "assigned_group": hit.get("assigned_group"),
            "business_service": hit.get("business_service"),
            "created_date": hit.get("created_date"),
            "closed_date": hit.get("closed_date"),
            "resolution_time_minutes": hit.get("resolution_time_minutes"),
            "reopen_count": hit.get("reopen_count"),
        }

    elif detected_type == "attachment":
        source_id = hit.get("attachment_id", hit.get("id", ""))
        title = hit.get("file_name", source_id)
        snippet = snippet or (hit.get("description") or "")[:300]
        url = hit.get("mock_url") or hit.get("incident_url", "")
        metadata = {
            "file_type": hit.get("file_type"),
            "attachment_type": hit.get("attachment_type"),
            "incident_id": hit.get("incident_id"),
            "kb_article_id": hit.get("kb_article_id"),
            "uploaded_date": hit.get("uploaded_date"),
            "size_bytes": hit.get("size_bytes"),
        }

    else:
        source_id = hit.get("id", "")
        title = source_id
        snippet = snippet or ""
        url = ""
        metadata = {}

    return {
        "source_type": detected_type,
        "source_id": source_id,
        "title": title,
        "snippet": snippet,
        "url": url,
        "score": round(float(score), 4),
        "metadata": {k: v for k, v in metadata.items() if v is not None},
    }


def _infer_source_type(hit: dict[str, Any]) -> str:
    """Heuristically infer source type from the fields present in the hit."""
    doc_id = hit.get("id", "")
    if doc_id.startswith("kb_"):
        return "kb_article"
    if doc_id.startswith("incident_"):
        return "incident"
    if doc_id.startswith("attachment_"):
        return "attachment"
    if "article_id" in hit:
        return "kb_article"
    if "incident_id" in hit and "content_type" in hit:
        return "incident"
    if "attachment_id" in hit:
        return "attachment"
    return "unknown"
