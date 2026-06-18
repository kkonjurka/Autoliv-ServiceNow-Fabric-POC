import math
from contextlib import closing
from typing import Any

from fastapi import APIRouter, Query

from app.database import get_connection
from app.models import PaginatedKnowledgeArticlesResponse

router = APIRouter(prefix="/kb-articles", tags=["kb-articles"])


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


def build_article(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "number": row["number"],
        "title": row["title"],
        "audience": row["audience"],
        "content_html": row["content_html"],
        "content_text": row["content_text"],
        "keywords": split_keywords(row["keywords"]),
        "published_at": row["published_at"],
        "updated_at": row["updated_at"],
        "category": {
            "id": row["category_id"],
            "name": row["category_name"],
            "subcategory": row["category_subcategory"],
        },
    }


@router.get("", response_model=PaginatedKnowledgeArticlesResponse)
def list_kb_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category: str | None = Query(None),
    keyword: str | None = Query(None),
) -> dict[str, Any]:
    conditions: list[str] = []
    parameters: list[Any] = []

    if category:
        conditions.append("(LOWER(c.id) = LOWER(?) OR LOWER(c.name) = LOWER(?) OR LOWER(c.subcategory) = LOWER(?))")
        parameters.extend([category, category, category])
    if keyword:
        keyword_pattern = f"%{keyword}%"
        conditions.append(
            "(kb.title LIKE ? OR kb.content_text LIKE ? OR kb.keywords LIKE ?)"
        )
        parameters.extend([keyword_pattern, keyword_pattern, keyword_pattern])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * page_size

    with closing(get_connection()) as connection:
        total_items = connection.execute(
            f"""
            SELECT COUNT(1)
            FROM kb_articles kb
            JOIN categories c ON c.id = kb.category_id
            {where_clause}
            """,
            parameters,
        ).fetchone()[0]
        rows = connection.execute(
            f"""
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
                c.subcategory AS category_subcategory
            FROM kb_articles kb
            JOIN categories c ON c.id = kb.category_id
            {where_clause}
            ORDER BY kb.updated_at DESC, kb.number ASC
            LIMIT ? OFFSET ?
            """,
            [*parameters, page_size, offset],
        ).fetchall()

    return {
        "pagination": build_pagination(page, page_size, total_items),
        "items": [build_article(row) for row in rows],
    }
