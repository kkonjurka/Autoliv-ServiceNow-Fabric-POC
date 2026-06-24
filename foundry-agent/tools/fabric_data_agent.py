"""Tool: query_fabric_data_agent

Calls the deployed Microsoft Fabric Data Agent REST endpoint to answer structured
operational questions over the ServiceNow semantic model (open tickets, SLA state,
priority/category summaries, backlog, aging, counts).

Environment variables required:
    FABRIC_DATA_AGENT_ENDPOINT  — full REST URL of the deployed Fabric Data Agent
    FABRIC_WORKSPACE_ID         — Fabric workspace GUID
    AZURE_TENANT_ID             — used by DefaultAzureCredential
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

logger = logging.getLogger(__name__)

_FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
_DEFAULT_MAX_ROWS = 10


def query_fabric_data_agent(
    question: str,
    filters: dict[str, str | int | bool] | None = None,
    max_rows: int = _DEFAULT_MAX_ROWS,
) -> dict[str, Any]:
    """Query the Fabric Data Agent for structured ticket and semantic-model questions.

    Routes questions about open tickets, SLA status, backlog, priority, category,
    aging, and counts to the deployed Fabric Data Agent. Returns a structured answer
    with row-level data and citations.

    Args:
        question:  Natural-language question for the Fabric Data Agent.
        filters:   Optional structured filters. Supported keys:
                     - priority (str): "1-Critical", "2-High", "3-Moderate", "4-Low"
                     - status (str): "Open", "In Progress", "Resolved", "Closed"
                     - category (str): e.g. "Network", "SAP", "Hardware"
                     - assignee_group (str)
                     - date_from (str): ISO-8601 date string
                     - date_to (str): ISO-8601 date string
        max_rows:  Maximum number of ticket rows to return (1–50, default 10).

    Returns:
        dict with keys:
            answer_text (str):   Plain-language answer from the Fabric Data Agent.
            rows (list[dict]):   Raw row data (may be empty for aggregate answers).
            citations (list):    List of citation objects:
                                   source_type: "fabric_data_agent" | "semantic_model"
                                                | "curated_table"
                                   source_id (str)
                                   title (str)
            confidence (float):  0.0–1.0 confidence score.
            error (str | None):  Present only when the call fails.
    """
    endpoint = os.environ.get("FABRIC_DATA_AGENT_ENDPOINT", "").rstrip("/")
    workspace_id = os.environ.get("FABRIC_WORKSPACE_ID", "")

    if not endpoint:
        return _error_response("FABRIC_DATA_AGENT_ENDPOINT is not configured.")

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), _FABRIC_SCOPE
    )
    token = token_provider()

    payload: dict[str, Any] = {
        "userQuestion": question,
        "workspaceId": workspace_id,
        "maxRows": max(1, min(50, max_rows)),
    }
    if filters:
        payload["filters"] = filters

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{endpoint}/query",
            json=payload,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Fabric Data Agent request failed: %s", exc)
        return _error_response(str(exc))

    data = resp.json()
    return {
        "answer_text": data.get("answerText", ""),
        "rows": data.get("rows", []),
        "citations": _normalize_fabric_citations(data.get("citations", [])),
        "confidence": float(data.get("confidence", 0.5)),
        "error": None,
    }


def _normalize_fabric_citations(raw: list[dict]) -> list[dict]:
    normalized = []
    for item in raw:
        normalized.append(
            {
                "source_type": item.get("sourceType", "fabric_data_agent"),
                "source_id": item.get("sourceId", ""),
                "title": item.get("title", ""),
            }
        )
    return normalized


def _error_response(message: str) -> dict[str, Any]:
    return {
        "answer_text": "",
        "rows": [],
        "citations": [],
        "confidence": 0.0,
        "error": message,
    }
