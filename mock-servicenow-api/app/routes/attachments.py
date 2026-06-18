import math
from contextlib import closing
from typing import Any

from fastapi import APIRouter, Query

from app.database import get_connection
from app.models import PaginatedAssetsResponse

router = APIRouter(tags=["assets"])


def build_pagination(page: int, page_size: int, total_items: int) -> dict[str, int]:
    total_pages = max(1, math.ceil(total_items / page_size)) if total_items else 0
    return {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
    }


def list_assets(
    table_name: str,
    page: int,
    page_size: int,
    incident_id: str | None,
) -> dict[str, Any]:
    extra_select = {
        "attachments": "asset.file_size_kb",
        "documents": "asset.file_size_kb",
        "images": "asset.width_px, asset.height_px",
    }[table_name]
    conditions = []
    parameters: list[Any] = []
    if incident_id:
        conditions.append("(asset.incident_id = ? OR i.number = ?)")
        parameters.extend([incident_id, incident_id])
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * page_size

    with closing(get_connection()) as connection:
        total_items = connection.execute(
            f"""
            SELECT COUNT(1)
            FROM {table_name} asset
            JOIN incidents i ON i.id = asset.incident_id
            {where_clause}
            """,
            parameters,
        ).fetchone()[0]
        rows = connection.execute(
            f"""
            SELECT
                asset.id,
                asset.incident_id,
                i.number AS incident_number,
                asset.file_name,
                asset.content_type,
                asset.description,
                asset.mock_url,
                asset.uploaded_at,
                {extra_select}
            FROM {table_name} asset
            JOIN incidents i ON i.id = asset.incident_id
            {where_clause}
            ORDER BY asset.uploaded_at DESC, asset.file_name ASC
            LIMIT ? OFFSET ?
            """,
            [*parameters, page_size, offset],
        ).fetchall()

    items = []
    for row in rows:
        payload = {
            "id": row["id"],
            "incident_id": row["incident_id"],
            "incident_number": row["incident_number"],
            "file_name": row["file_name"],
            "content_type": row["content_type"],
            "description": row["description"],
            "mock_url": row["mock_url"],
            "uploaded_at": row["uploaded_at"],
        }
        if "file_size_kb" in row.keys():
            payload["file_size_kb"] = row["file_size_kb"]
        if "width_px" in row.keys():
            payload["width_px"] = row["width_px"]
            payload["height_px"] = row["height_px"]
        items.append(payload)

    return {
        "pagination": build_pagination(page, page_size, total_items),
        "items": items,
    }


@router.get("/attachments", response_model=PaginatedAssetsResponse)
def get_attachments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    incident_id: str | None = Query(None),
) -> dict[str, Any]:
    return list_assets("attachments", page, page_size, incident_id)


@router.get("/images", response_model=PaginatedAssetsResponse)
def get_images(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    incident_id: str | None = Query(None),
) -> dict[str, Any]:
    return list_assets("images", page, page_size, incident_id)


@router.get("/documents", response_model=PaginatedAssetsResponse)
def get_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    incident_id: str | None = Query(None),
) -> dict[str, Any]:
    return list_assets("documents", page, page_size, incident_id)
