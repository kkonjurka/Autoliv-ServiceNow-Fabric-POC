# Fabric notebook source

# CELL ********************

"""Fabric smoke-test notebook for the live mock ServiceNow API."""

# ## Notebook purpose
# Run this notebook first to prove the mock API is reachable from Fabric and to preview
# the main data shapes before launching the full raw ingestion and curated transforms.

# CELL ********************

# ## Configure the smoke test
# This cell defines the live API URL, request timeout, DataFrame display helper, and
# small utilities for fetching JSON payloads with the `requests` library.

from __future__ import annotations

import os
from typing import Any

import requests
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

DEFAULT_API_BASE_URL = os.getenv(
    "MOCK_SERVICENOW_API_BASE_URL",
    "https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io",
).rstrip("/")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("SERVICENOW_REQUEST_TIMEOUT_SECONDS", "30"))
LIST_PAGE_SIZE = int(os.getenv("SERVICENOW_SMOKE_TEST_PAGE_SIZE", "5"))

spark.sparkContext.setLogLevel("WARN")

api_summary_rows: list[dict[str, Any]] = []


def fetch_json(relative_path: str, params: dict[str, Any] | None = None) -> tuple[dict[str, Any], int]:
    response = requests.get(
        f"{DEFAULT_API_BASE_URL}{relative_path}",
        params=params,
        headers={"Accept": "application/json"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json(), response.status_code


def render_df(df: DataFrame, title: str, row_limit: int = 20) -> None:
    print(f"\n=== {title} ===")
    limited_df = df.limit(row_limit)
    try:
        display(limited_df)  # type: ignore[name-defined]
    except NameError:
        limited_df.show(row_limit, truncate=False)


def field_inventory_df(endpoint_name: str, payload: dict[str, Any]) -> DataFrame:
    if "items" in payload and payload["items"]:
        field_names = sorted(payload["items"][0].keys())
    else:
        field_names = sorted(payload.keys())
    return spark.createDataFrame([(endpoint_name, field_name) for field_name in field_names], ["endpoint", "field_name"])


print(f"API base URL: {DEFAULT_API_BASE_URL}")
print(f"Request timeout: {REQUEST_TIMEOUT_SECONDS} seconds")
print(f"Smoke-test page size: {LIST_PAGE_SIZE}")

# CELL ********************

# ## Call the incidents list endpoint
# This cell proves the list endpoint is live, shows the total incident count reported by
# the API, previews key columns, and lists the top-level fields present in each record.

incident_list_payload, incident_list_status = fetch_json(
    "/incidents",
    params={"page": 1, "page_size": LIST_PAGE_SIZE},
)
incident_items = incident_list_payload.get("items", [])
incident_pagination = incident_list_payload.get("pagination", {})
if not incident_items:
    raise ValueError("The incidents list endpoint is reachable but returned no records for the smoke test.")
incident_list_df = spark.createDataFrame(incident_items)

print(
    f"Incidents list returned {len(incident_items)} records on page 1 "
    f"out of {incident_pagination.get('total_items', len(incident_items))} total incidents."
)
print(f"Pagination metadata: {incident_pagination}")

render_df(
    incident_list_df.select(
        "id",
        "number",
        "short_description",
        "state",
        "priority",
        "impact",
        "urgency",
        F.col("requester.full_name").alias("requester_name"),
        F.col("assignee.full_name").alias("assignee_name"),
        F.col("assignment_group.name").alias("assignment_group_name"),
        "opened_at",
        "updated_at",
    ),
    "Incident list sample",
)
render_df(field_inventory_df("incidents_list", incident_list_payload), "Incident list field inventory", row_limit=50)

api_summary_rows.append(
    {
        "endpoint": "/incidents",
        "status_code": incident_list_status,
        "records_returned": len(incident_items),
        "total_records_reported": incident_pagination.get("total_items", len(incident_items)),
        "demo_note": "Paged incident summary records",
    }
)

# CELL ********************

# ## Call the incident detail endpoint
# This cell grabs the first incident ID from the list response, fetches the full nested
# incident detail payload, and highlights related-note, KB, and file-reference counts.

selected_incident_id = incident_items[0]["id"]
incident_detail_payload, incident_detail_status = fetch_json(f"/incidents/{selected_incident_id}")
incident_detail_df = spark.createDataFrame([incident_detail_payload])

print(f"Fetched detail for incident ID: {selected_incident_id}")

render_df(
    incident_detail_df.select(
        "id",
        "number",
        "short_description",
        "state",
        "priority",
        "impact",
        "urgency",
        F.col("requester.full_name").alias("requester_name"),
        F.col("assignee.full_name").alias("assignee_name"),
        F.col("assignment_group.name").alias("assignment_group_name"),
        F.size("work_notes").alias("work_note_count"),
        F.size("resolution_notes").alias("resolution_note_count"),
        F.size("related_kb_articles").alias("related_kb_article_count"),
        F.size("change_requests").alias("change_request_count"),
        F.size("slas").alias("sla_count"),
        F.size("attachments").alias("attachment_count"),
        F.size("images").alias("image_count"),
        F.size("documents").alias("document_count"),
    ),
    "Incident detail summary",
)

render_df(
    incident_detail_df.select(
        F.explode_outer("work_notes").alias("work_note")
    ).select(
        F.col("work_note.author.full_name").alias("author_name"),
        F.col("work_note.created_at").alias("created_at"),
        F.col("work_note.note_html").alias("note_html"),
        F.col("work_note.note_text").alias("note_text"),
    ),
    "Incident work note sample",
)

render_df(
    incident_detail_df.select(
        F.explode_outer("related_kb_articles").alias("kb_article")
    ).select(
        F.col("kb_article.id").alias("kb_article_id"),
        F.col("kb_article.number").alias("kb_article_number"),
        F.col("kb_article.title").alias("kb_article_title"),
        F.col("kb_article.relevance_reason").alias("relevance_reason"),
    ),
    "Incident-related KB sample",
)

api_summary_rows.append(
    {
        "endpoint": f"/incidents/{selected_incident_id}",
        "status_code": incident_detail_status,
        "records_returned": 1,
        "total_records_reported": 1,
        "demo_note": (
            f"{len(incident_detail_payload.get('work_notes', []))} work notes, "
            f"{len(incident_detail_payload.get('related_kb_articles', []))} KB links, "
            f"{len(incident_detail_payload.get('attachments', []))} attachments"
        ),
    }
)

# CELL ********************

# ## Call the knowledge article list endpoint
# This cell previews article titles, audience, categories, and keyword arrays so the
# user can quickly confirm the API is returning usable KB content.

kb_payload, kb_status = fetch_json(
    "/kb-articles",
    params={"page": 1, "page_size": LIST_PAGE_SIZE},
)
kb_items = kb_payload.get("items", [])
kb_pagination = kb_payload.get("pagination", {})
if not kb_items:
    raise ValueError("The KB articles endpoint is reachable but returned no records for the smoke test.")
kb_df = spark.createDataFrame(kb_items)

print(
    f"KB articles returned {len(kb_items)} records on page 1 "
    f"out of {kb_pagination.get('total_items', len(kb_items))} total articles."
)
print(f"Pagination metadata: {kb_pagination}")

render_df(
    kb_df.select(
        "id",
        "number",
        "title",
        "audience",
        F.col("category.name").alias("category_name"),
        F.col("category.subcategory").alias("category_subcategory"),
        F.array_join("keywords", ", ").alias("keywords"),
        "published_at",
        "updated_at",
    ),
    "KB article sample",
)
render_df(field_inventory_df("kb_articles", kb_payload), "KB article field inventory", row_limit=50)

api_summary_rows.append(
    {
        "endpoint": "/kb-articles",
        "status_code": kb_status,
        "records_returned": len(kb_items),
        "total_records_reported": kb_pagination.get("total_items", len(kb_items)),
        "demo_note": "Paged knowledge article summaries",
    }
)

# CELL ********************

# ## Call the attachment list endpoint
# This cell previews file metadata available for downstream ingestion, including file
# names, MIME types, sizes, and the incident each attachment belongs to.

attachment_payload, attachment_status = fetch_json(
    "/attachments",
    params={"page": 1, "page_size": LIST_PAGE_SIZE},
)
attachment_items = attachment_payload.get("items", [])
attachment_pagination = attachment_payload.get("pagination", {})
if not attachment_items:
    raise ValueError("The attachments endpoint is reachable but returned no records for the smoke test.")
attachment_df = spark.createDataFrame(attachment_items)

print(
    f"Attachments returned {len(attachment_items)} records on page 1 "
    f"out of {attachment_pagination.get('total_items', len(attachment_items))} total attachments."
)
print(f"Pagination metadata: {attachment_pagination}")

render_df(
    attachment_df.select(
        "id",
        "incident_id",
        "incident_number",
        "file_name",
        "content_type",
        "file_size_kb",
        "width_px",
        "height_px",
        "uploaded_at",
        "mock_url",
    ),
    "Attachment sample",
)
render_df(field_inventory_df("attachments", attachment_payload), "Attachment field inventory", row_limit=50)

api_summary_rows.append(
    {
        "endpoint": "/attachments",
        "status_code": attachment_status,
        "records_returned": len(attachment_items),
        "total_records_reported": attachment_pagination.get("total_items", len(attachment_items)),
        "demo_note": "Paged attachment metadata",
    }
)

# CELL ********************

# ## Summarize the smoke test
# This final cell rolls the endpoint checks into one summary table so a reviewer can
# quickly confirm connectivity, response status, and record counts at a glance.

api_summary_df = spark.createDataFrame(api_summary_rows)

render_df(
    api_summary_df.select(
        "endpoint",
        "status_code",
        "records_returned",
        "total_records_reported",
        "demo_note",
    ),
    "API smoke-test summary",
    row_limit=20,
)

print("Smoke test completed successfully.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
