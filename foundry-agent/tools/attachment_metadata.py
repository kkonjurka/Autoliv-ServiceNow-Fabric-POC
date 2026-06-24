"""Tool: get_attachment_metadata

Calls Azure AI Search against the `attachments` index to retrieve metadata for
non-text assets attached to ServiceNow tickets: screenshots, log files, scripts,
documents, and other uploaded files.

Environment variables required:
    AZURE_SEARCH_ENDPOINT  — e.g. https://<service>.search.windows.net
    AZURE_SEARCH_KEY       — admin or query key
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

_SEARCH_API_VERSION = "2024-05-01-preview"
_ATTACHMENTS_INDEX = "attachments"
_DEFAULT_TOP_K = 10

AssetType = str  # "attachment" | "document" | "image" | "screenshot" | "log" | "script" | "url"


def get_attachment_metadata(
    ticket_id: str,
    related_ticket_ids: list[str] | None = None,
    asset_types: list[AssetType] | None = None,
    keywords: list[str] | None = None,
    top_k: int = _DEFAULT_TOP_K,
) -> dict[str, Any]:
    """Retrieve attachment and document metadata for a ticket or related tickets.

    Searches the Azure AI Search attachments index for files, images, logs, and
    documents associated with the given ticket IDs. Optionally filters by asset
    type and keywords found in file names or summaries.

    Args:
        ticket_id:          Primary ticket identifier (sys_id or number).
        related_ticket_ids: Optional list of related ticket IDs to include in scope.
        asset_types:        Filter to these asset categories. Supported values:
                              "attachment", "document", "image", "screenshot",
                              "log", "script", "url"
                            Defaults to all types when omitted.
        keywords:           Optional list of keywords to match in file names or
                            summaries (e.g., ["error", "vpn", "screenshot"]).
        top_k:              Maximum number of assets to return (1–20, default 10).

    Returns:
        dict with keys:
            assets (list[dict]):  Each asset contains:
                                    asset_id (str)
                                    asset_type (str)
                                    title (str):           file name or document title
                                    summary (str | None):  AI-generated description
                                    url (str | None):      download or view URL
                                    related_ticket_id (str): which ticket owns it
            confidence (float):   0.0–1.0 (1.0 when ticket_id is an exact match,
                                  lower for related tickets with no direct match).
            error (str | None):   Present only when the call fails.
    """
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
    api_key = os.environ.get("AZURE_SEARCH_KEY", "")

    if not endpoint:
        return _error_response("AZURE_SEARCH_ENDPOINT is not configured.")
    if not ticket_id:
        return _error_response("ticket_id is required.")

    all_ticket_ids = [ticket_id] + (related_ticket_ids or [])
    url = (
        f"{endpoint}/indexes/{_ATTACHMENTS_INDEX}/docs/search"
        f"?api-version={_SEARCH_API_VERSION}"
    )
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    ticket_filter = " or ".join(
        f"ticket_id eq '{tid}'" for tid in all_ticket_ids
    )
    filters = [f"({ticket_filter})"]

    if asset_types:
        type_filter = " or ".join(f"asset_type eq '{at}'" for at in asset_types)
        filters.append(f"({type_filter})")

    keyword_query = " ".join(keywords) if keywords else "*"

    search_body: dict[str, Any] = {
        "search": keyword_query,
        "top": max(1, min(20, top_k)),
        "select": "id,asset_type,title,summary,url,ticket_id",
        "filter": " and ".join(filters),
        "orderby": "ticket_id asc",
    }

    try:
        resp = requests.post(url, json=search_body, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Azure AI Search (attachments) request failed: %s", exc)
        return _error_response(str(exc))

    hits = resp.json().get("value", [])
    assets = [
        {
            "asset_id": hit.get("id", ""),
            "asset_type": hit.get("asset_type", "attachment"),
            "title": hit.get("title", ""),
            "summary": hit.get("summary") or None,
            "url": hit.get("url") or None,
            "related_ticket_id": hit.get("ticket_id", ""),
        }
        for hit in hits
    ]

    # Confidence is high when direct ticket matches exist, lower for related-only.
    direct_matches = [a for a in assets if a["related_ticket_id"] == ticket_id]
    confidence = 1.0 if direct_matches else (0.6 if assets else 0.0)

    return {"assets": assets, "confidence": confidence, "error": None}


def _error_response(message: str) -> dict[str, Any]:
    return {"assets": [], "confidence": 0.0, "error": message}
