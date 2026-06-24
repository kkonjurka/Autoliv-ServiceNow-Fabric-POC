# Fabric notebook source

# CELL ********************

"""
05_Index_Search — Push curated ServiceNow Delta table content into Azure AI Search.

Pipeline:
  1. Read curated Delta tables (kb_articles, incidents, attachments)
  2. Build search documents matching the index schemas
  3. Generate embeddings via Azure OpenAI (text-embedding-ada-002, 1536-dim)
  4. Upload documents to Azure AI Search in batches of 100
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T

# CELL ********************

# ── Configuration ─────────────────────────────────────────────────────────────
# Update these values or set them as Fabric Environment secrets / notebook widgets.

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY", "")
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
SEARCH_API_VERSION = os.getenv("SEARCH_API_VERSION", "2024-05-01-preview")

SOURCE_DATABASE = os.getenv("SERVICENOW_CURATED_DATABASE", "")

BATCH_SIZE = 100          # Azure AI Search and OpenAI recommended batch size
EMBED_RETRY_DELAY = 5     # Seconds to wait on rate-limit retry
SERVICENOW_BASE_URL = os.getenv("SERVICENOW_BASE_URL", "https://mock-servicenow.example.com")

print("Configuration loaded.")
print(f"  Search endpoint : {SEARCH_ENDPOINT or '(not set — update AZURE_SEARCH_ENDPOINT)'}")
print(f"  OpenAI endpoint : {OPENAI_ENDPOINT or '(not set — update AZURE_OPENAI_ENDPOINT)'}")
print(f"  Source database : {SOURCE_DATABASE or '(default — no prefix)'}")

# CELL ********************

# ── Helpers ───────────────────────────────────────────────────────────────────

def qualify(table: str) -> str:
    return f"{SOURCE_DATABASE}.{table}" if SOURCE_DATABASE else table


def read_table(table_name: str, required: bool = True) -> DataFrame:
    full_name = qualify(table_name)
    if spark.catalog.tableExists(full_name):
        return spark.table(full_name)
    if required:
        raise ValueError(f"Required curated table not found: {full_name}")
    print(f"  [WARN] Optional table not found, skipping: {full_name}")
    return spark.createDataFrame([], T.StructType([]))


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Batch-embed texts via Azure OpenAI. Handles rate limiting with one retry."""
    url = (
        f"{OPENAI_ENDPOINT}/openai/deployments/{EMBEDDING_DEPLOYMENT}"
        f"/embeddings?api-version={OPENAI_API_VERSION}"
    )
    headers = {"Content-Type": "application/json", "api-key": OPENAI_API_KEY}
    payload = {"input": texts, "model": EMBEDDING_DEPLOYMENT}

    for attempt in range(2):
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code == 429 and attempt == 0:
            retry_after = int(resp.headers.get("Retry-After", EMBED_RETRY_DELAY))
            print(f"  [RATE LIMIT] Waiting {retry_after}s before retry…")
            time.sleep(retry_after)
            continue
        resp.raise_for_status()
        data = resp.json()["data"]
        data.sort(key=lambda x: x["index"])
        return [item["embedding"] for item in data]

    raise RuntimeError("Embedding request failed after retry.")


def upload_documents(index_name: str, documents: list[dict[str, Any]]) -> int:
    """Upload a batch of documents to Azure AI Search. Returns count of indexed docs."""
    if not documents:
        return 0
    url = f"{SEARCH_ENDPOINT}/indexes/{index_name}/docs/index?api-version={SEARCH_API_VERSION}"
    headers = {"Content-Type": "application/json", "api-key": SEARCH_API_KEY}
    payload = {
        "value": [{"@search.action": "mergeOrUpload", **doc} for doc in documents]
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    results = resp.json().get("value", [])
    failed = [r for r in results if not r.get("status", True)]
    if failed:
        print(f"  [WARN] {len(failed)} documents failed to index: {failed[:3]}")
    return len(results) - len(failed)


def index_in_batches(
    index_name: str,
    rows: list[dict[str, Any]],
    embed_field: str,
    embed_text_fn,
) -> int:
    """Embed and index rows in batches of BATCH_SIZE. Returns total indexed count."""
    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        texts = [embed_text_fn(r) for r in batch]
        vectors = get_embeddings(texts)
        for row, vec in zip(batch, vectors):
            row[embed_field] = vec
        count = upload_documents(index_name, batch)
        total += count
        print(f"  Batch {i // BATCH_SIZE + 1}: {count}/{len(batch)} documents indexed")
    return total

# CELL ********************

# ── 1. Index KB Articles ───────────────────────────────────────────────────────

print("=" * 60)
print("Step 1: Indexing KB Articles → kb-articles-index")
print("=" * 60)

kb_df = read_table("kb_articles")
kb_rows = kb_df.collect()
print(f"  Loaded {len(kb_rows)} KB articles from Delta table.")

kb_docs: list[dict[str, Any]] = []
for row in kb_rows:
    article_id = str(row["article_id"] if hasattr(row, "article_id") else row["sys_id"] or "")
    doc: dict[str, Any] = {
        "id": f"kb_{article_id}",
        "article_id": article_id,
        "title": str(row["title"] or ""),
        "content": str(row["body_clean"] if "body_clean" in row.asDict() else row.get("text_clean", "") or ""),
        "category": str(row.get("category", "") or ""),
        "subcategory": str(row.get("subcategory", "") or ""),
        "view_count": int(row.get("view_count", 0) or 0),
        "useful_count": int(row.get("useful_count", 0) or 0),
        "source_url": f"{SERVICENOW_BASE_URL}/kb_article?id={article_id}",
    }
    if row.get("published_date") or row.get("created_at"):
        val = row.get("published_date") or row.get("created_at")
        doc["created_date"] = val.isoformat() + "Z" if hasattr(val, "isoformat") else str(val)
    if row.get("updated_at") or row.get("updated_date"):
        val = row.get("updated_at") or row.get("updated_date")
        doc["updated_date"] = val.isoformat() + "Z" if hasattr(val, "isoformat") else str(val)
    kb_docs.append(doc)

def _kb_embed_text(doc: dict) -> str:
    return f"{doc['title']} {doc['content']}"[:8000]

kb_indexed = index_in_batches("kb-articles-index", kb_docs, "vector", _kb_embed_text)
print(f"\n✓ KB articles indexed: {kb_indexed} / {len(kb_docs)}")

# CELL ********************

# ── 2. Index Incident Content ──────────────────────────────────────────────────

print("=" * 60)
print("Step 2: Indexing Incident Content → incident-content-index")
print("=" * 60)

incidents_df = read_table("incidents")
incidents_rows = incidents_df.collect()
print(f"  Loaded {len(incidents_rows)} incidents from Delta table.")

incident_docs: list[dict[str, Any]] = []

for row in incidents_rows:
    row_dict = row.asDict()
    incident_id = str(row_dict.get("number") or row_dict.get("incident_id") or row_dict.get("sys_id") or "")
    state = str(row_dict.get("state", "") or "")
    summary = str(row_dict.get("short_description") or row_dict.get("incident_summary", "") or "")
    category = str(row_dict.get("category", "") or "")
    subcategory = str(row_dict.get("subcategory", "") or "")
    priority = str(row_dict.get("priority", "") or "")
    assigned_group = str(row_dict.get("assignment_group", "") or row_dict.get("assigned_group", "") or "")
    business_service = str(row_dict.get("business_service", "") or "")
    resolution_time = int(row_dict.get("resolution_time_minutes", 0) or 0)
    reopen_count = int(row_dict.get("reopen_count", 0) or 0)
    incident_url = f"{SERVICENOW_BASE_URL}/incident?id={incident_id}"

    def _ts(field_name: str) -> str | None:
        val = row_dict.get(field_name)
        if val is None:
            return None
        return val.isoformat() + "Z" if hasattr(val, "isoformat") else str(val)

    base: dict[str, Any] = {
        "incident_id": incident_id,
        "incident_state": state,
        "incident_summary": summary,
        "priority": priority,
        "category": category,
        "subcategory": subcategory,
        "assigned_group": assigned_group,
        "business_service": business_service,
        "resolution_time_minutes": resolution_time,
        "reopen_count": reopen_count,
        "incident_url": incident_url,
    }
    for ts_field in ("created_date", "created_at", "sys_created_on"):
        val = _ts(ts_field)
        if val:
            base["created_date"] = val
            break
    for ts_field in ("updated_date", "updated_at", "sys_updated_on"):
        val = _ts(ts_field)
        if val:
            base["updated_date"] = val
            break
    for ts_field in ("closed_date", "closed_at", "resolved_at"):
        val = _ts(ts_field)
        if val:
            base["closed_date"] = val
            break

    content_fields = {
        "description": str(row_dict.get("description_clean") or row_dict.get("description") or ""),
        "work_notes": str(row_dict.get("work_notes_clean") or row_dict.get("work_notes") or ""),
        "resolution_notes": str(row_dict.get("resolution_notes_clean") or row_dict.get("close_notes") or ""),
    }

    for content_type, text in content_fields.items():
        if not text.strip():
            continue
        doc = {
            **base,
            "id": f"incident_{incident_id}_{content_type}",
            "content_type": content_type,
            "description": content_fields["description"],
            "work_notes": content_fields["work_notes"],
            "resolution_notes": content_fields["resolution_notes"],
        }
        incident_docs.append(doc)

print(f"  Prepared {len(incident_docs)} incident content documents.")

def _incident_embed_text(doc: dict) -> str:
    parts = [
        doc.get("incident_summary", ""),
        doc.get("description", ""),
        doc.get("work_notes", ""),
        doc.get("resolution_notes", ""),
    ]
    return " ".join(p for p in parts if p).strip()[:8000]

incident_indexed = index_in_batches("incident-content-index", incident_docs, "vector", _incident_embed_text)
print(f"\n✓ Incident content documents indexed: {incident_indexed} / {len(incident_docs)}")

# CELL ********************

# ── 3. Index Attachments ───────────────────────────────────────────────────────

print("=" * 60)
print("Step 3: Indexing Attachments → attachments-index")
print("=" * 60)

attachments_df = read_table("attachments", required=False)
attachments_rows = attachments_df.collect()
print(f"  Loaded {len(attachments_rows)} attachments from Delta table.")

attachment_docs: list[dict[str, Any]] = []
for row in attachments_rows:
    row_dict = row.asDict()
    attachment_id = str(row_dict.get("attachment_id") or row_dict.get("sys_id") or "")
    file_name = str(row_dict.get("filename") or row_dict.get("file_name", "") or "")
    content_type = str(row_dict.get("content_type") or row_dict.get("file_type", "") or "")
    description = str(row_dict.get("description") or "")
    incident_id = str(row_dict.get("incident_id") or "")
    kb_article_id = str(row_dict.get("kb_article_id") or "")
    document_id = str(row_dict.get("document_id") or "")
    size = int(row_dict.get("file_size") or row_dict.get("size_bytes", 0) or 0)
    mock_url = f"{SERVICENOW_BASE_URL}/attachment?id={attachment_id}"
    incident_url = f"{SERVICENOW_BASE_URL}/incident?id={incident_id}" if incident_id else ""

    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    type_map = {
        "png": "screenshot", "jpg": "screenshot", "jpeg": "screenshot", "gif": "screenshot",
        "log": "log", "txt": "log",
        "sql": "script", "ps1": "script", "sh": "script", "py": "script",
        "pdf": "document", "docx": "document", "xlsx": "document",
    }
    attachment_type = type_map.get(ext, "other")

    doc: dict[str, Any] = {
        "id": f"attachment_{attachment_id}",
        "attachment_id": attachment_id,
        "file_name": file_name,
        "file_type": content_type,
        "description": description,
        "incident_id": incident_id,
        "kb_article_id": kb_article_id,
        "document_id": document_id,
        "attachment_type": attachment_type,
        "size_bytes": size,
        "mock_url": mock_url,
        "incident_url": incident_url,
    }
    val = row_dict.get("created_at") or row_dict.get("uploaded_date") or row_dict.get("sys_created_on")
    if val:
        doc["uploaded_date"] = val.isoformat() + "Z" if hasattr(val, "isoformat") else str(val)
    attachment_docs.append(doc)

def _attachment_embed_text(doc: dict) -> str:
    return f"{doc['file_name']} {doc['description']}".strip()[:2000]

attachment_indexed = index_in_batches("attachments-index", attachment_docs, "vector", _attachment_embed_text)
print(f"\n✓ Attachments indexed: {attachment_indexed} / {len(attachment_docs)}")

# CELL ********************

# ── Summary ────────────────────────────────────────────────────────────────────

print()
print("=" * 60)
print("Indexing Complete — Summary")
print("=" * 60)
print(f"  kb-articles-index      : {kb_indexed:>6} documents")
print(f"  incident-content-index : {incident_indexed:>6} documents")
print(f"  attachments-index      : {attachment_indexed:>6} documents")
print(f"  ─────────────────────────────────────")
print(f"  Total                  : {kb_indexed + incident_indexed + attachment_indexed:>6} documents")
print()
print("Next step: Run 06_RAG_Query.Notebook to test retrieval.")

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "language_info": {
# META     "name": "python"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse_name": "ServiceNow_Lakehouse",
# META       "default_schema": "dbo"
# META     }
# META   }
# META }
