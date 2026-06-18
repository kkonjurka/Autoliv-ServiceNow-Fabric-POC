from contextlib import closing

from fastapi import APIRouter

from app.database import get_connection, get_database_path

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    with closing(get_connection()) as connection:
        incident_count = connection.execute("SELECT COUNT(1) FROM incidents").fetchone()[0]
        kb_count = connection.execute("SELECT COUNT(1) FROM kb_articles").fetchone()[0]

    return {
        "status": "ok",
        "database_path": str(get_database_path()),
        "incident_count": incident_count,
        "kb_article_count": kb_count,
    }
