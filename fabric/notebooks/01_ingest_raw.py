"""Fabric notebook to ingest raw ServiceNow-style API payloads into a Lakehouse."""

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

DEFAULT_API_BASE_URL = os.getenv("MOCK_SERVICENOW_API_BASE_URL", "https://replace-with-container-app-url").rstrip("/")
PAGE_SIZE = int(os.getenv("SERVICENOW_PAGE_SIZE", "50"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("SERVICENOW_REQUEST_TIMEOUT_SECONDS", "60"))
LOAD_TS_UTC = datetime.now(timezone.utc)
LOAD_STAMP = LOAD_TS_UTC.strftime("%Y%m%dT%H%M%SZ")
LOAD_DATE = LOAD_TS_UTC.strftime("%Y-%m-%d")
LAKEHOUSE_ROOT = PurePosixPath("/lakehouse/default/Files/raw/servicenow")
MANIFEST_TABLE = os.getenv("SERVICENOW_RAW_MANIFEST_TABLE", "raw_api_manifest")


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


def _notebook_fs():
    try:
        from notebookutils import mssparkutils

        return mssparkutils.fs
    except Exception:
        return None


def fetch_json(relative_path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    query_string = f"?{urlencode(params)}" if params else ""
    request = Request(f"{DEFAULT_API_BASE_URL}{relative_path}{query_string}", headers={"Accept": "application/json"})
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def write_json_payload(relative_path: PurePosixPath, payload: dict[str, Any]) -> str:
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
    return LAKEHOUSE_ROOT / dataset_name / "list" / f"load_date={LOAD_DATE}" / f"page_{page_number:04d}.json"


def detail_output_path(dataset_name: str, entity_id: str) -> PurePosixPath:
    safe_id = entity_id.replace("/", "_")
    return LAKEHOUSE_ROOT / dataset_name / "detail" / f"load_date={LOAD_DATE}" / f"{safe_id}.json"


def ingest_paginated_collection(
    *,
    dataset_name: str,
    endpoint: str,
    page_size: int = PAGE_SIZE,
    extra_params: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[ManifestEntry]]:
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


def ingest_incident_details(incident_ids: Iterable[str]) -> list[ManifestEntry]:
    manifest: list[ManifestEntry] = []
    for incident_id in incident_ids:
        payload = fetch_json(f"/incidents/{incident_id}")
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
    return manifest


def write_manifest_table(spark: SparkSession, manifest_entries: list[ManifestEntry]) -> None:
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


incident_summaries, incident_manifest = ingest_paginated_collection(
    dataset_name="incidents",
    endpoint="/incidents",
)
incident_detail_manifest = ingest_incident_details(item["id"] for item in incident_summaries)

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
