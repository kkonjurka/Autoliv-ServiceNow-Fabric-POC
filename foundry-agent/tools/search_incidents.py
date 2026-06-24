"""Tool: search_incidents

Calls Azure AI Search (vector search) against the `incident-content` index to find
historically similar incidents based on symptom or error description. Used for
identifying prior resolution patterns and recommending fixes.

Environment variables required:
    AZURE_SEARCH_ENDPOINT        — e.g. https://<service>.search.windows.net
    AZURE_SEARCH_KEY             — admin or query key
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
_INCIDENT_INDEX = "incident-content"
_DEFAULT_TOP_K = 5


def search_incidents(
    query: str,
    ticket_id: str | None = None,
    top_k: int = _DEFAULT_TOP_K,
) -> dict[str, Any]:
    """Find similar historical incidents via vector search.

    Searches the incident-content Azure AI Search index for past incidents whose
    descriptions, work notes, or resolution notes closely match the supplied query.
    Results are filtered to resolved/closed incidents so that only completed cases
    with confirmed resolutions are surfaced.

    Args:
        query:      Issue description, error message, or symptom text. More detail
                    produces better similarity results.
        ticket_id:  Optional ID of the current open ticket. When provided, the
                    current ticket is excluded from results to avoid self-matches.
        top_k:      Maximum number of similar incidents to return (1–20, default 5).

    Returns:
        dict with keys:
            results (list[dict]):  Each result contains:
                                     source_type: "similar_ticket"
                                     source_id (str):   incident sys_id or number
                                     title (str):       incident short_description
                                     snippet (str):     most relevant excerpt
                                     url (str | None):  link to the incident record
                                     score (float):     similarity score 0–1
                                     resolution_note (str | None): resolution text
            confidence (float):    0.0–1.0 derived from top result score.
            error (str | None):    Present only when the call fails.
    """
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
    api_key = os.environ.get("AZURE_SEARCH_KEY", "")

    if not endpoint:
        return _error_response("AZURE_SEARCH_ENDPOINT is not configured.")

    embedding = _embed(query)

    url = (
        f"{endpoint}/indexes/{_INCIDENT_INDEX}/docs/search"
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
        "top": max(1, min(20, top_k)),
        "select": "id,number,short_description,resolution_notes,snippet,url,state",
        "queryLanguage": "en-US",
        # Only return resolved / closed incidents to ensure resolution data exists.
        "filter": "state eq 'Resolved' or state eq 'Closed'",
    }

    if embedding:
        search_body["vectorQueries"] = [
            {
                "kind": "vector",
                "vector": embedding,
                "fields": "content_vector",
                "k": max(1, min(20, top_k)),
            }
        ]

    if ticket_id:
        existing_filter = search_body.get("filter", "")
        exclusion = f"id ne '{ticket_id}' and number ne '{ticket_id}'"
        search_body["filter"] = (
            f"({existing_filter}) and ({exclusion})"
            if existing_filter
            else exclusion
        )

    try:
        resp = requests.post(url, json=search_body, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Azure AI Search (incidents) request failed: %s", exc)
        return _error_response(str(exc))

    hits = resp.json().get("value", [])
    results = [
        {
            "source_type": "similar_ticket",
            "source_id": hit.get("id") or hit.get("number", ""),
            "title": hit.get("short_description", ""),
            "snippet": hit.get("snippet", hit.get("short_description", ""))[:500],
            "url": hit.get("url"),
            "score": hit.get("@search.score", 0.0),
            "resolution_note": (hit.get("resolution_notes") or "")[:500] or None,
        }
        for hit in hits
    ]

    confidence = _score_to_confidence(results[0]["score"] if results else 0.0)
    return {"results": results, "confidence": confidence, "error": None}


def _embed(text: str) -> list[float] | None:
    """Generate a query embedding via Azure OpenAI."""
    aoai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    aoai_key = os.environ.get("AZURE_OPENAI_KEY", "")
    deployment = os.environ.get(
        "AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"
    )

    if not aoai_endpoint:
        logger.warning("AZURE_OPENAI_ENDPOINT not set; using keyword-only search.")
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
    return min(1.0, score / 4.0)


def _error_response(message: str) -> dict[str, Any]:
    return {"results": [], "confidence": 0.0, "error": message}
