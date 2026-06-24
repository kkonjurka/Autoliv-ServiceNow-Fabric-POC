"""Tool: search_knowledge

Calls Azure AI Search (hybrid vector + keyword) to retrieve KB articles, work notes,
resolution notes, and cleaned HTML content from the `kb-articles` and
`incident-content` indexes.

Environment variables required:
    AZURE_SEARCH_ENDPOINT        — e.g. https://<service>.search.windows.net
    AZURE_SEARCH_KEY             — admin or query key (or use managed identity)
    AZURE_OPENAI_ENDPOINT        — for generating query embeddings
    AZURE_OPENAI_EMBEDDING_MODEL — deployment name, default "text-embedding-ada-002"
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

_SEARCH_API_VERSION = "2024-05-01-preview"
_EMBEDDING_DIMS = 1536
_KB_INDEX = "kb-articles"
_INCIDENT_CONTENT_INDEX = "incident-content"
_DEFAULT_TOP_K = 5

ContentType = str  # "kb_article" | "work_note" | "resolution_note" | "cleaned_html"


def search_knowledge(
    query: str,
    ticket_id: str | None = None,
    content_types: list[ContentType] | None = None,
    top_k: int = _DEFAULT_TOP_K,
) -> dict[str, Any]:
    """Retrieve KB articles, work notes, resolution notes, and cleaned HTML content.

    Performs a hybrid (vector + keyword) search against the Azure AI Search
    kb-articles and incident-content indexes. Results are ranked by relevance and
    returned with citation metadata.

    Args:
        query:         Issue description or search query text.
        ticket_id:     Optional current ticket ID to scope or exclude from results.
        content_types: Filter results to these types. Supported values:
                         "kb_article", "work_note", "resolution_note", "cleaned_html"
                       Defaults to all types when omitted.
        top_k:         Maximum number of results to return (1–20, default 5).

    Returns:
        dict with keys:
            results (list[dict]):  Each result contains:
                                     source_type (str)
                                     source_id (str)
                                     title (str)
                                     snippet (str)
                                     url (str | None)
                                     score (float)
            confidence (float):    0.0–1.0 derived from top result score.
            error (str | None):    Present only when the call fails.
    """
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
    api_key = os.environ.get("AZURE_SEARCH_KEY", "")

    if not endpoint:
        return _error_response("AZURE_SEARCH_ENDPOINT is not configured.")

    embedding = _embed(query)
    results: list[dict] = []

    target_indexes = _resolve_indexes(content_types)

    for index_name in target_indexes:
        index_results = _search_index(
            endpoint=endpoint,
            api_key=api_key,
            index_name=index_name,
            query=query,
            embedding=embedding,
            content_types=content_types,
            ticket_id=ticket_id,
            top_k=top_k,
        )
        results.extend(index_results)

    results.sort(key=lambda r: r["score"], reverse=True)
    results = results[:top_k]

    confidence = _score_to_confidence(results[0]["score"] if results else 0.0)
    return {"results": results, "confidence": confidence, "error": None}


def _resolve_indexes(content_types: list[str] | None) -> list[str]:
    if not content_types:
        return [_KB_INDEX, _INCIDENT_CONTENT_INDEX]
    kb_types = {"kb_article"}
    incident_types = {"work_note", "resolution_note", "cleaned_html"}
    indexes = []
    types_set = set(content_types)
    if types_set & kb_types:
        indexes.append(_KB_INDEX)
    if types_set & incident_types:
        indexes.append(_INCIDENT_CONTENT_INDEX)
    return indexes or [_KB_INDEX, _INCIDENT_CONTENT_INDEX]


def _search_index(
    endpoint: str,
    api_key: str,
    index_name: str,
    query: str,
    embedding: list[float] | None,
    content_types: list[str] | None,
    ticket_id: str | None,
    top_k: int,
) -> list[dict]:
    url = (
        f"{endpoint}/indexes/{index_name}/docs/search"
        f"?api-version={_SEARCH_API_VERSION}"
    )
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    search_body: dict[str, Any] = {
        "search": query,
        "queryType": "semantic",
        "semanticConfiguration": "default",
        "top": top_k,
        "select": "id,title,content_type,snippet,url,ticket_id",
        "queryLanguage": "en-US",
    }

    if embedding:
        search_body["vectorQueries"] = [
            {
                "kind": "vector",
                "vector": embedding,
                "fields": "content_vector",
                "k": top_k,
            }
        ]

    filters = []
    if content_types:
        escaped = [f"content_type eq '{ct}'" for ct in content_types]
        filters.append(f"({' or '.join(escaped)})")
    if ticket_id:
        filters.append(f"ticket_id ne '{ticket_id}'")
    if filters:
        search_body["filter"] = " and ".join(filters)

    try:
        resp = requests.post(url, json=search_body, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Azure AI Search (%s) request failed: %s", index_name, exc)
        return []

    return [
        {
            "source_type": hit.get("content_type", "kb_article"),
            "source_id": hit.get("id", ""),
            "title": hit.get("title", ""),
            "snippet": hit.get("snippet", hit.get("content", ""))[:500],
            "url": hit.get("url"),
            "score": hit.get("@search.score", 0.0),
        }
        for hit in resp.json().get("value", [])
    ]


def _embed(text: str) -> list[float] | None:
    """Generate a query embedding via Azure OpenAI."""
    aoai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    aoai_key = os.environ.get("AZURE_OPENAI_KEY", "")
    deployment = os.environ.get(
        "AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"
    )

    if not aoai_endpoint:
        logger.warning("AZURE_OPENAI_ENDPOINT not set; falling back to keyword search.")
        return None

    url = (
        f"{aoai_endpoint}/openai/deployments/{deployment}/embeddings"
        "?api-version=2024-02-01"
    )
    headers = {"Content-Type": "application/json", "api-key": aoai_key}
    try:
        resp = requests.post(
            url, json={"input": text}, headers=headers, timeout=10
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    except Exception as exc:
        logger.warning("Embedding generation failed: %s", exc)
        return None


def _score_to_confidence(score: float) -> float:
    """Map a raw search score (0–4 typical range) to a 0–1 confidence."""
    return min(1.0, score / 4.0)


def _error_response(message: str) -> dict[str, Any]:
    return {"results": [], "confidence": 0.0, "error": message}
