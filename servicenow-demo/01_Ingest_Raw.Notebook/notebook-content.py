# Fabric notebook source

# CELL ********************

"""Fabric notebook to ingest raw ServiceNow-style API payloads into a Lakehouse."""

# ## Notebook purpose
# Run this notebook after the API smoke test to land raw JSON responses in the Lakehouse.
# It is the raw-ingestion stage of the pipeline and creates the source files used by the
# downstream curated transform notebook.

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pyspark.sql import Row, SparkSession
from pyspark.sql.functions import current_timestamp

DEFAULT_API_BASE_URL = os.getenv("MOCK_SERVICENOW_API_BASE_URL", "https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io").rstrip("/")
PAGE_SIZE = int(os.getenv("SERVICENOW_PAGE_SIZE", "50"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("SERVICENOW_REQUEST_TIMEOUT_SECONDS", "60"))
LOAD_TS_UTC = datetime.now(timezone.utc)
LOAD_STAMP = LOAD_TS_UTC.strftime("%Y%m%dT%H%M%SZ")
LOAD_DATE = LOAD_TS_UTC.strftime("%Y-%m-%d")
LAKEHOUSE_ROOT = PurePosixPath("Files/raw/servicenow")
MANIFEST_TABLE = os.getenv("SERVICENOW_RAW_MANIFEST_TABLE", "raw_api_manifest")

# ## Define the manifest record shape
# Each manifest row tracks which endpoint was called, what file was written, and when
# the extraction happened so later notebooks can audit the raw landing process.

@dataclass(frozen=True)
class ManifestEntry:
    dataset_name: str
    record_type: str
    endpoint: str
    page_number: int | None
    entity_id: str | None
    item_count: int | None
    landed_path: str
    extracted_at_utc: str


def safe_create_df(items: list[dict[str, Any]]):
    """Create a Spark DataFrame from nested API rows without brittle schema inference."""
    json_rows = [json.dumps(item) for item in items]
    return spark.read.json(spark.sparkContext.parallelize(json_rows))


def overwrite_delta_table(items: list[dict[str, Any]], table_name: str) -> None:
    """Persist one raw API dataset to an overwriteable Delta table in the Lakehouse."""
    if not items:
        raise ValueError(f"No records were available to write {table_name}.")
    safe_create_df(items).write.mode("overwrite").format("delta").saveAsTable(table_name)


def _notebook_fs():
    """Return Fabric's filesystem helper when running in a notebook, else None locally."""
    try:
        from notebookutils import mssparkutils

        return mssparkutils.fs
    except Exception:
        return None


def fetch_json(relative_path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fetch one JSON payload from the mock ServiceNow API."""
    query_string = f"?{urlencode(params)}" if params else ""
    request = Request(f"{DEFAULT_API_BASE_URL}{relative_path}{query_string}", headers={"Accept": "application/json"})
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def write_json_payload(relative_path: PurePosixPath, payload: dict[str, Any]) -> str:
    """Write a raw JSON payload to Lakehouse Files or a local fallback path."""
    payload_text = json.dumps(payload, indent=2, sort_keys=True)
    target_path = str(relative_path)
    fs = _notebook_fs()

    if fs:
        fs.mkdirs(str(relative_path.parent))
        fs.put(target_path, payload_text, True)
        return target_path

    local_path = Path.cwd() / Path(*relative_path.parts[1:])
    os.makedirs(local_path.parent, exist_ok=True)
    with open(local_path, "w", encoding="utf-8") as handle:
        handle.write(payload_text)
    return str(local_path)


def page_output_path(dataset_name: str, page_number: int) -> PurePosixPath:
    """Build the landing path for one paginated list response."""
    return LAKEHOUSE_ROOT / dataset_name / "list" / f"load_date={LOAD_DATE}" / f"page_{page_number:04d}.json"


def detail_output_path(dataset_name: str, entity_id: str) -> PurePosixPath:
    """Build the landing path for one detail response using a filesystem-safe ID."""
    safe_id = entity_id.replace("/", "_")
    return LAKEHOUSE_ROOT / dataset_name / "detail" / f"load_date={LOAD_DATE}" / f"{safe_id}.json"


def ingest_paginated_collection(
    *,
    dataset_name: str,
    endpoint: str,
    page_size: int = PAGE_SIZE,
    extra_params: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[ManifestEntry]]:
    """Fetch every page for one list endpoint and return all items plus manifest rows."""
    page_number = 1
    items: list[dict[str, Any]] = []
    manifest: list[ManifestEntry] = []

    while True:
        params = {"page": page_number, "page_size": page_size, **(extra_params or {})}
        payload = fetch_json(endpoint, params)
        page_items = payload.get("items", [])
        landed_path = write_json_payload(page_output_path(dataset_name, page_number), payload)
        manifest.append(
            ManifestEntry(
                dataset_name=dataset_name,
                record_type="page",
                endpoint=f"{endpoint}?{urlencode(params)}",
                page_number=page_number,
                entity_id=None,
                item_count=len(page_items),
                landed_path=landed_path,
                extracted_at_utc=LOAD_TS_UTC.isoformat(),
            )
        )
        items.extend(page_items)

        total_pages = int(payload.get("pagination", {}).get("total_pages", page_number))
        if page_number >= total_pages or not page_items:
            break
        page_number += 1

    return items, manifest


def ingest_incident_details(incident_ids: Iterable[str]) -> tuple[list[dict[str, Any]], list[ManifestEntry]]:
    """Fetch and land the full detail payload for every incident ID collected from the list API."""
    detail_payloads: list[dict[str, Any]] = []
    manifest: list[ManifestEntry] = []
    for incident_id in incident_ids:
        payload = fetch_json(f"/incidents/{incident_id}")
        detail_payloads.append(payload)
        landed_path = write_json_payload(detail_output_path("incidents", incident_id), payload)
        manifest.append(
            ManifestEntry(
                dataset_name="incidents",
                record_type="detail",
                endpoint=f"/incidents/{incident_id}",
                page_number=None,
                entity_id=incident_id,
                item_count=None,
                landed_path=landed_path,
                extracted_at_utc=LOAD_TS_UTC.isoformat(),
            )
        )
    return detail_payloads, manifest


def write_manifest_table(spark: SparkSession, manifest_entries: list[ManifestEntry]) -> None:
    """Append manifest metadata so each raw-ingestion run is traceable in Delta."""
    manifest_rows = [
        Row(
            dataset_name=entry.dataset_name,
            record_type=entry.record_type,
            endpoint=entry.endpoint,
            page_number=entry.page_number,
            entity_id=entry.entity_id,
            item_count=entry.item_count,
            landed_path=entry.landed_path,
            extracted_at_utc=entry.extracted_at_utc,
        )
        for entry in manifest_entries
    ]
    manifest_df = spark.createDataFrame(manifest_rows).withColumn("landed_at_utc", current_timestamp())
    (
        manifest_df.write.mode("append")
        .format("delta")
        .option("mergeSchema", "true")
        .saveAsTable(MANIFEST_TABLE)
    )


def list_landed_files(root: PurePosixPath) -> list[str]:
    """List JSON files written for the current load date under the raw landing area."""
    fs = _notebook_fs()
    if fs:
        landed_files: list[str] = []

        def _normalize(path: str) -> str:
            return path.replace("/lakehouse/default/", "", 1) if path.startswith("/lakehouse/default/") else path

        def _walk(path: str) -> None:
            for entry in fs.ls(path):
                if getattr(entry, "isDir", False):
                    _walk(entry.path)
                else:
                    landed_files.append(_normalize(entry.path))

        _walk(str(root))
        return sorted(path for path in landed_files if f"load_date={LOAD_DATE}" in path)

    local_root = Path.cwd() / Path(*root.parts[1:])
    return sorted(
        str(path.relative_to(Path.cwd())).replace("\\", "/")
        for path in local_root.rglob("*.json")
        if f"load_date={LOAD_DATE}" in str(path)
    )

# ## Ingest the raw API entities
# Fetch the incident list first, then use those IDs to fetch nested incident details.
# The remaining collection endpoints are landed page-by-page as raw JSON snapshots.

incident_summaries, incident_manifest = ingest_paginated_collection(
    dataset_name="incidents",
    endpoint="/incidents",
)
incident_details, incident_detail_manifest = ingest_incident_details(item["id"] for item in incident_summaries)

# These datasets supply the KB content and file metadata used by later curated transforms.
kb_articles, kb_manifest = ingest_paginated_collection(
    dataset_name="kb_articles",
    endpoint="/kb-articles",
)
attachments, attachment_manifest = ingest_paginated_collection(
    dataset_name="attachments",
    endpoint="/attachments",
)
images, image_manifest = ingest_paginated_collection(
    dataset_name="images",
    endpoint="/images",
)
documents, document_manifest = ingest_paginated_collection(
    dataset_name="documents",
    endpoint="/documents",
)

# Persist the raw API entities as Delta tables so Lakehouse Explorer shows each landed stage.
overwrite_delta_table(incident_summaries, "raw_incidents_list")
overwrite_delta_table(incident_details, "raw_incidents_detail")
overwrite_delta_table(kb_articles, "raw_kb_articles")
overwrite_delta_table(attachments, "raw_attachments")

# Persist one manifest entry per landed file so the pipeline has an auditable load ledger.
write_manifest_table(
    spark,
    [
        *incident_manifest,
        *incident_detail_manifest,
        *kb_manifest,
        *attachment_manifest,
        *image_manifest,
        *document_manifest,
    ],
)

print(
    {
        "load_stamp": LOAD_STAMP,
        "incident_pages": len(incident_manifest),
        "incident_details": len(incident_detail_manifest),
        "kb_articles": len(kb_articles),
        "attachments": len(attachments),
        "images": len(images),
        "documents": len(documents),
    }
)

# CELL ********************

# ## Review what landed in raw storage
# This cell gives a simple run summary: which files were written, how many records came
# from each entity type, and a sample raw payload to confirm the landing format.

landed_files = list_landed_files(LAKEHOUSE_ROOT)
files_df = spark.createDataFrame(
    [Row(file_path=file_path) for file_path in landed_files],
    "file_path string",
)

entity_count_df = spark.createDataFrame(
    [
        Row(entity_type="incidents", record_count=len(incident_summaries)),
        Row(entity_type="kb_articles", record_count=len(kb_articles)),
        Row(entity_type="attachments", record_count=len(attachments)),
        Row(entity_type="images", record_count=len(images)),
        Row(entity_type="documents", record_count=len(documents)),
    ]
)

sample_raw_path = None
if incident_detail_manifest:
    sample_raw_path = incident_detail_manifest[0].landed_path
elif incident_manifest:
    sample_raw_path = incident_manifest[0].landed_path

print("Files written during this ingestion run:")
display(files_df)

print("Record counts by entity type:")
display(entity_count_df)

print("Sample raw payload preview:")
if sample_raw_path:
    sample_raw_df = spark.read.option("multiLine", True).json(sample_raw_path)
    display(sample_raw_df.limit(5))
else:
    print("No sample raw payload was available for preview.")

# Present a clear completion message so notebook users know the raw load finished successfully.
summary_message = (
    f"✅ Ingestion complete. {len(incident_summaries)} incidents, "
    f"{len(kb_articles)} KB articles, {len(attachments)} attachments, "
    f"{len(images)} images, {len(documents)} documents ingested."
)

if "displayHTML" in globals():
    displayHTML(
        f"""
        <div style="padding:12px 16px;border-radius:8px;background:#e8f5e9;border:1px solid #66bb6a;">
          <strong>{summary_message}</strong><br/>
          <span>Files written: {len(landed_files)}</span>
        </div>
        """
    )

print(summary_message)

# CELL ********************

# ## Review the persisted raw Delta tables
# This cell confirms the raw notebook wrote Delta tables alongside the JSON files and shows
# the row counts that should now appear under the Lakehouse Explorer Tables experience.

raw_table_counts_df = spark.createDataFrame(
    [
        ("raw_attachments", spark.table("raw_attachments").count()),
        ("raw_incidents_detail", spark.table("raw_incidents_detail").count()),
        ("raw_incidents_list", spark.table("raw_incidents_list").count()),
        ("raw_kb_articles", spark.table("raw_kb_articles").count()),
    ],
    ["table_name", "record_count"],
).orderBy("table_name")

print("Persisted raw table counts:")
display(raw_table_counts_df)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
