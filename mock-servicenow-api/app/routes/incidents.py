import math
from contextlib import closing
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.database import get_connection
from app.models import IncidentDetail, IncidentListItem, PaginatedIncidentsResponse

router = APIRouter(prefix="/incidents", tags=["incidents"])

INCIDENT_SELECT = """
SELECT
    i.id,
    i.number,
    i.short_description,
    i.description_html,
    i.description_text,
    i.state,
    i.priority,
    i.impact,
    i.urgency,
    i.opened_at,
    i.updated_at,
    i.resolved_at,
    i.follow_up_required,
    i.follow_up_reason,
    i.resolution_summary_html,
    i.resolution_summary_text,
    c.id AS category_id,
    c.name AS category_name,
    c.subcategory AS category_subcategory,
    ag.id AS assignment_group_id,
    ag.name AS assignment_group_name,
    ag.description AS assignment_group_description,
    ag.escalation_email AS assignment_group_escalation_email,
    req.id AS requester_id,
    req.full_name AS requester_name,
    req.email AS requester_email,
    req.title AS requester_title,
    req.location AS requester_location,
    req.department AS requester_department,
    ass.id AS assignee_id,
    ass.full_name AS assignee_name,
    ass.email AS assignee_email,
    ass.title AS assignee_title,
    ass.location AS assignee_location,
    ass.department AS assignee_department
FROM incidents i
JOIN categories c ON c.id = i.category_id
JOIN assignment_groups ag ON ag.id = i.assignment_group_id
JOIN users req ON req.id = i.requester_id
LEFT JOIN users ass ON ass.id = i.assignee_id
"""


def build_category(row: Any) -> dict[str, str]:
    return {
        "id": row["category_id"],
        "name": row["category_name"],
        "subcategory": row["category_subcategory"],
    }


def build_user(row: Any, prefix: str) -> dict[str, str] | None:
    user_id = row[f"{prefix}_id"]
    if not user_id:
        return None
    return {
        "id": user_id,
        "full_name": row[f"{prefix}_name"],
        "email": row[f"{prefix}_email"],
        "title": row[f"{prefix}_title"],
        "location": row[f"{prefix}_location"],
        "department": row[f"{prefix}_department"],
    }


def build_assignment_group(row: Any) -> dict[str, str]:
    return {
        "id": row["assignment_group_id"],
        "name": row["assignment_group_name"],
        "description": row["assignment_group_description"],
        "escalation_email": row["assignment_group_escalation_email"],
    }


def build_incident_summary(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "number": row["number"],
        "short_description": row["short_description"],
        "state": row["state"],
        "priority": row["priority"],
        "impact": row["impact"],
        "urgency": row["urgency"],
        "opened_at": row["opened_at"],
        "updated_at": row["updated_at"],
        "resolved_at": row["resolved_at"],
        "follow_up_required": bool(row["follow_up_required"]),
        "requester": build_user(row, "requester"),
        "assignee": build_user(row, "assignee"),
        "assignment_group": build_assignment_group(row),
        "category": build_category(row),
    }


def build_pagination(page: int, page_size: int, total_items: int) -> dict[str, int]:
    total_pages = max(1, math.ceil(total_items / page_size)) if total_items else 0
    return {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
    }


def split_keywords(raw_keywords: str) -> list[str]:
    return [keyword.strip() for keyword in raw_keywords.split(",") if keyword.strip()]


def fetch_note_rows(connection, table_name: str, incident_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"""
        SELECT
            n.id,
            n.note_html,
            n.note_text,
            n.created_at,
            u.id AS author_id,
            u.full_name AS author_name,
            u.email AS author_email,
            u.title AS author_title,
            u.location AS author_location,
            u.department AS author_department
        FROM {table_name} n
        JOIN users u ON u.id = n.author_id
        WHERE n.incident_id = ?
        ORDER BY n.created_at ASC
        """,
        (incident_id,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "created_at": row["created_at"],
            "note_html": row["note_html"],
            "note_text": row["note_text"],
            "author": {
                "id": row["author_id"],
                "full_name": row["author_name"],
                "email": row["author_email"],
                "title": row["author_title"],
                "location": row["author_location"],
                "department": row["author_department"],
            },
        }
        for row in rows
    ]


def fetch_assets(connection, table_name: str, incident_id: str) -> list[dict[str, Any]]:
    extra_fields = {
        "attachments": "a.file_size_kb",
        "documents": "a.file_size_kb",
        "images": "a.width_px, a.height_px",
    }[table_name]
    rows = connection.execute(
        f"""
        SELECT
            a.id,
            a.incident_id,
            i.number AS incident_number,
            a.file_name,
            a.content_type,
            a.description,
            a.mock_url,
            a.uploaded_at,
            {extra_fields}
        FROM {table_name} a
        JOIN incidents i ON i.id = a.incident_id
        WHERE a.incident_id = ?
        ORDER BY a.uploaded_at ASC
        """,
        (incident_id,),
    ).fetchall()
    assets = []
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
        assets.append(payload)
    return assets


def fetch_related_kb_articles(connection, incident_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            kb.id,
            kb.number,
            kb.title,
            kb.audience,
            kb.content_html,
            kb.content_text,
            kb.keywords,
            kb.published_at,
            kb.updated_at,
            c.id AS category_id,
            c.name AS category_name,
            c.subcategory AS category_subcategory,
            ikl.relevance_reason
        FROM incident_kb_links ikl
        JOIN kb_articles kb ON kb.id = ikl.kb_article_id
        JOIN categories c ON c.id = kb.category_id
        WHERE ikl.incident_id = ?
        ORDER BY kb.number ASC
        """,
        (incident_id,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "number": row["number"],
            "title": row["title"],
            "audience": row["audience"],
            "content_html": row["content_html"],
            "content_text": row["content_text"],
            "keywords": split_keywords(row["keywords"]),
            "published_at": row["published_at"],
            "updated_at": row["updated_at"],
            "relevance_reason": row["relevance_reason"],
            "category": {
                "id": row["category_id"],
                "name": row["category_name"],
                "subcategory": row["category_subcategory"],
            },
        }
        for row in rows
    ]


def fetch_change_requests(connection, incident_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            chg.id,
            chg.number,
            chg.title,
            chg.state,
            chg.risk,
            chg.planned_start,
            chg.planned_end,
            chg.implemented_at,
            icl.relationship_type
        FROM incident_change_links icl
        JOIN change_requests chg ON chg.id = icl.change_request_id
        WHERE icl.incident_id = ?
        ORDER BY chg.number ASC
        """,
        (incident_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_slas(connection, incident_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, name, stage, target_hours, elapsed_hours, breached
        FROM slas
        WHERE incident_id = ?
        ORDER BY name ASC
        """,
        (incident_id,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "stage": row["stage"],
            "target_hours": row["target_hours"],
            "elapsed_hours": row["elapsed_hours"],
            "breached": bool(row["breached"]),
        }
        for row in rows
    ]


def fetch_external_references(connection, incident_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, reference_type, title, url, source_system
        FROM external_references
        WHERE incident_id = ?
        ORDER BY title ASC
        """,
        (incident_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def build_filters(
    *,
    state: str | None,
    priority: str | None,
    category: str | None,
    assignment_group: str | None,
    updated_since: datetime | None,
    requester: str | None,
) -> tuple[str, list[Any]]:
    conditions: list[str] = []
    parameters: list[Any] = []

    if state:
        conditions.append("LOWER(i.state) = LOWER(?)")
        parameters.append(state)
    if priority:
        conditions.append("LOWER(i.priority) = LOWER(?)")
        parameters.append(priority)
    if category:
        conditions.append("(LOWER(c.id) = LOWER(?) OR LOWER(c.name) = LOWER(?) OR LOWER(c.subcategory) = LOWER(?))")
        parameters.extend([category, category, category])
    if assignment_group:
        conditions.append("(LOWER(ag.id) = LOWER(?) OR LOWER(ag.name) = LOWER(?))")
        parameters.extend([assignment_group, assignment_group])
    if updated_since:
        conditions.append("i.updated_at >= ?")
        parameters.append(updated_since.isoformat())
    if requester:
        conditions.append("(LOWER(req.id) = LOWER(?) OR LOWER(req.full_name) = LOWER(?) OR LOWER(req.email) = LOWER(?))")
        parameters.extend([requester, requester, requester])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where_clause, parameters


@router.get("", response_model=PaginatedIncidentsResponse)
def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    state: str | None = Query(None),
    priority: str | None = Query(None),
    category: str | None = Query(None),
    assignment_group: str | None = Query(None),
    updated_since: datetime | None = Query(None),
    requester: str | None = Query(None),
) -> dict[str, Any]:
    where_clause, parameters = build_filters(
        state=state,
        priority=priority,
        category=category,
        assignment_group=assignment_group,
        updated_since=updated_since,
        requester=requester,
    )
    offset = (page - 1) * page_size

    with closing(get_connection()) as connection:
        total_items = connection.execute(
            f"""
            SELECT COUNT(1)
            FROM incidents i
            JOIN categories c ON c.id = i.category_id
            JOIN assignment_groups ag ON ag.id = i.assignment_group_id
            JOIN users req ON req.id = i.requester_id
            {where_clause}
            """,
            parameters,
        ).fetchone()[0]
        rows = connection.execute(
            f"""
            {INCIDENT_SELECT}
            {where_clause}
            ORDER BY i.updated_at DESC, i.number ASC
            LIMIT ? OFFSET ?
            """,
            [*parameters, page_size, offset],
        ).fetchall()

    return {
        "pagination": build_pagination(page, page_size, total_items),
        "items": [build_incident_summary(row) for row in rows],
    }


@router.get("/history/search", response_model=PaginatedIncidentsResponse)
def search_historical_incidents(
    keyword: str = Query(..., min_length=2),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> dict[str, Any]:
    conditions = ["i.state IN ('Resolved', 'Closed')"]
    parameters: list[Any] = []
    keyword_pattern = f"%{keyword}%"
    conditions.append(
        """
        (
            i.short_description LIKE ?
            OR i.description_text LIKE ?
            OR COALESCE(i.resolution_summary_text, '') LIKE ?
            OR EXISTS (
                SELECT 1 FROM work_notes wn
                WHERE wn.incident_id = i.id AND wn.note_text LIKE ?
            )
            OR EXISTS (
                SELECT 1 FROM resolution_notes rn
                WHERE rn.incident_id = i.id AND rn.note_text LIKE ?
            )
        )
        """
    )
    parameters.extend([keyword_pattern] * 5)
    if category:
        conditions.append("(LOWER(c.id) = LOWER(?) OR LOWER(c.name) = LOWER(?) OR LOWER(c.subcategory) = LOWER(?))")
        parameters.extend([category, category, category])

    where_clause = f"WHERE {' AND '.join(conditions)}"
    offset = (page - 1) * page_size

    with closing(get_connection()) as connection:
        total_items = connection.execute(
            f"""
            SELECT COUNT(1)
            FROM incidents i
            JOIN categories c ON c.id = i.category_id
            {where_clause}
            """,
            parameters,
        ).fetchone()[0]
        rows = connection.execute(
            f"""
            {INCIDENT_SELECT}
            {where_clause}
            ORDER BY i.updated_at DESC, i.number ASC
            LIMIT ? OFFSET ?
            """,
            [*parameters, page_size, offset],
        ).fetchall()

    return {
        "pagination": build_pagination(page, page_size, total_items),
        "items": [build_incident_summary(row) for row in rows],
    }


@router.get("/follow-up/open", response_model=list[IncidentListItem])
def list_open_follow_up_tickets(limit: int = Query(10, ge=1, le=50)) -> list[dict[str, Any]]:
    with closing(get_connection()) as connection:
        rows = connection.execute(
            f"""
            {INCIDENT_SELECT}
            WHERE i.follow_up_required = 1
              AND i.state IN ('New', 'In Progress', 'On Hold')
            ORDER BY i.updated_at ASC, i.number ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [build_incident_summary(row) for row in rows]


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: str) -> dict[str, Any]:
    with closing(get_connection()) as connection:
        row = connection.execute(
            f"""
            {INCIDENT_SELECT}
            WHERE i.id = ? OR i.number = ?
            """,
            (incident_id, incident_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Incident not found")

        incident = build_incident_summary(row)
        incident.update(
            {
                "description_html": row["description_html"],
                "description_text": row["description_text"],
                "follow_up_reason": row["follow_up_reason"],
                "resolution_summary_html": row["resolution_summary_html"],
                "resolution_summary_text": row["resolution_summary_text"],
                "related_kb_articles": fetch_related_kb_articles(connection, row["id"]),
                "work_notes": fetch_note_rows(connection, "work_notes", row["id"]),
                "resolution_notes": fetch_note_rows(connection, "resolution_notes", row["id"]),
                "change_requests": fetch_change_requests(connection, row["id"]),
                "slas": fetch_slas(connection, row["id"]),
                "attachments": fetch_assets(connection, "attachments", row["id"]),
                "images": fetch_assets(connection, "images", row["id"]),
                "documents": fetch_assets(connection, "documents", row["id"]),
                "external_references": fetch_external_references(connection, row["id"]),
            }
        )

    return incident
