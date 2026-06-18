import os
import sqlite3
from contextlib import closing
from pathlib import Path

from app.seed.seed_data import seed_database

DEFAULT_DB_PATH = Path("data") / "servicenow_mock.sqlite"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    employee_number TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT NOT NULL,
    department TEXT NOT NULL,
    manager_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assignment_groups (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    escalation_email TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    subcategory TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kb_articles (
    id TEXT PRIMARY KEY,
    number TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    category_id TEXT NOT NULL,
    audience TEXT NOT NULL,
    content_html TEXT NOT NULL,
    content_text TEXT NOT NULL,
    keywords TEXT NOT NULL,
    published_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    number TEXT NOT NULL UNIQUE,
    short_description TEXT NOT NULL,
    description_html TEXT NOT NULL,
    description_text TEXT NOT NULL,
    state TEXT NOT NULL,
    priority TEXT NOT NULL,
    category_id TEXT NOT NULL,
    assignment_group_id TEXT NOT NULL,
    requester_id TEXT NOT NULL,
    assignee_id TEXT,
    impact TEXT NOT NULL,
    urgency TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    follow_up_required INTEGER NOT NULL DEFAULT 0,
    follow_up_reason TEXT,
    resolution_summary_html TEXT,
    resolution_summary_text TEXT,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (assignment_group_id) REFERENCES assignment_groups(id),
    FOREIGN KEY (requester_id) REFERENCES users(id),
    FOREIGN KEY (assignee_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS work_notes (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    note_html TEXT NOT NULL,
    note_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (incident_id) REFERENCES incidents(id),
    FOREIGN KEY (author_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS resolution_notes (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    note_html TEXT NOT NULL,
    note_text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (incident_id) REFERENCES incidents(id),
    FOREIGN KEY (author_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS change_requests (
    id TEXT PRIMARY KEY,
    number TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    state TEXT NOT NULL,
    risk TEXT NOT NULL,
    planned_start TEXT NOT NULL,
    planned_end TEXT NOT NULL,
    implemented_at TEXT
);

CREATE TABLE IF NOT EXISTS incident_change_links (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    change_request_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    FOREIGN KEY (incident_id) REFERENCES incidents(id),
    FOREIGN KEY (change_request_id) REFERENCES change_requests(id)
);

CREATE TABLE IF NOT EXISTS slas (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    name TEXT NOT NULL,
    stage TEXT NOT NULL,
    target_hours REAL NOT NULL,
    elapsed_hours REAL NOT NULL,
    breached INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    content_type TEXT NOT NULL,
    file_size_kb INTEGER NOT NULL,
    description TEXT NOT NULL,
    mock_url TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

CREATE TABLE IF NOT EXISTS images (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    content_type TEXT NOT NULL,
    width_px INTEGER NOT NULL,
    height_px INTEGER NOT NULL,
    description TEXT NOT NULL,
    mock_url TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    content_type TEXT NOT NULL,
    file_size_kb INTEGER NOT NULL,
    description TEXT NOT NULL,
    mock_url TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

CREATE TABLE IF NOT EXISTS external_references (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    reference_type TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    source_system TEXT NOT NULL,
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

CREATE TABLE IF NOT EXISTS incident_kb_links (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    kb_article_id TEXT NOT NULL,
    relevance_reason TEXT NOT NULL,
    FOREIGN KEY (incident_id) REFERENCES incidents(id),
    FOREIGN KEY (kb_article_id) REFERENCES kb_articles(id)
);

CREATE INDEX IF NOT EXISTS idx_incidents_state ON incidents(state);
CREATE INDEX IF NOT EXISTS idx_incidents_priority ON incidents(priority);
CREATE INDEX IF NOT EXISTS idx_incidents_updated_at ON incidents(updated_at);
CREATE INDEX IF NOT EXISTS idx_incidents_requester ON incidents(requester_id);
CREATE INDEX IF NOT EXISTS idx_incidents_group ON incidents(assignment_group_id);
CREATE INDEX IF NOT EXISTS idx_incidents_category ON incidents(category_id);
CREATE INDEX IF NOT EXISTS idx_work_notes_incident ON work_notes(incident_id);
CREATE INDEX IF NOT EXISTS idx_resolution_notes_incident ON resolution_notes(incident_id);
CREATE INDEX IF NOT EXISTS idx_slas_incident ON slas(incident_id);
CREATE INDEX IF NOT EXISTS idx_attachments_incident ON attachments(incident_id);
CREATE INDEX IF NOT EXISTS idx_images_incident ON images(incident_id);
CREATE INDEX IF NOT EXISTS idx_documents_incident ON documents(incident_id);
CREATE INDEX IF NOT EXISTS idx_external_references_incident ON external_references(incident_id);
CREATE INDEX IF NOT EXISTS idx_incident_kb_links_incident ON incident_kb_links(incident_id);
"""


def get_database_path() -> Path:
    configured_path = os.getenv("SERVICENOW_DB_PATH", str(DEFAULT_DB_PATH))
    return Path(configured_path)


def get_mock_base_url() -> str:
    return os.getenv("MOCK_URL_BASE", "http://localhost:8000").rstrip("/")


def should_reseed_on_startup() -> bool:
    return os.getenv("SERVICENOW_RESEED_ON_STARTUP", "true").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def get_connection() -> sqlite3.Connection:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.commit()


def has_seed_data(connection: sqlite3.Connection) -> bool:
    row = connection.execute("SELECT COUNT(1) AS count FROM incidents").fetchone()
    return bool(row and row["count"])


def init_database(reseed: bool | None = None) -> None:
    with closing(get_connection()) as connection:
        create_schema(connection)
        if reseed is None:
            reseed = should_reseed_on_startup()
        if reseed or not has_seed_data(connection):
            seed_database(connection, base_url=get_mock_base_url())
            connection.commit()
