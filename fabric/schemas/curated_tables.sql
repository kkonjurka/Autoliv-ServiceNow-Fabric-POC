-- Curated Lakehouse/Warehouse tables for the Autoliv ServiceNow Fabric POC.

CREATE TABLE curated.users (
    user_id VARCHAR(50) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(320) NOT NULL,
    title VARCHAR(200) NULL,
    location VARCHAR(200) NULL,
    department VARCHAR(200) NULL,
    PRIMARY KEY (user_id)
);

CREATE TABLE curated.assignment_groups (
    assignment_group_id VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description VARCHAR(1000) NULL,
    escalation_email VARCHAR(320) NULL,
    PRIMARY KEY (assignment_group_id)
);

CREATE TABLE curated.categories (
    category_id VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    subcategory VARCHAR(200) NOT NULL,
    PRIMARY KEY (category_id)
);

CREATE TABLE curated.incidents (
    incident_id VARCHAR(50) NOT NULL,
    number VARCHAR(50) NOT NULL,
    short_description VARCHAR(500) NOT NULL,
    state VARCHAR(50) NOT NULL,
    priority VARCHAR(50) NOT NULL,
    impact VARCHAR(50) NOT NULL,
    urgency VARCHAR(50) NOT NULL,
    opened_at DATETIME2 NOT NULL,
    updated_at DATETIME2 NOT NULL,
    resolved_at DATETIME2 NULL,
    follow_up_required BIT NOT NULL,
    follow_up_reason VARCHAR(2000) NULL,
    requester_id VARCHAR(50) NOT NULL,
    assignee_id VARCHAR(50) NULL,
    assignment_group_id VARCHAR(50) NOT NULL,
    category_id VARCHAR(50) NOT NULL,
    description_text_clean VARCHAR(MAX) NULL,
    resolution_summary_text_clean VARCHAR(MAX) NULL,
    description_html VARCHAR(MAX) NULL,
    resolution_summary_html VARCHAR(MAX) NULL,
    PRIMARY KEY (incident_id)
);

CREATE TABLE curated.kb_articles (
    kb_article_id VARCHAR(50) NOT NULL,
    kb_article_number VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    audience VARCHAR(100) NOT NULL,
    category_id VARCHAR(50) NOT NULL,
    content_text_clean VARCHAR(MAX) NOT NULL,
    content_html VARCHAR(MAX) NULL,
    keywords VARCHAR(2000) NULL,
    published_at DATETIME2 NOT NULL,
    updated_at DATETIME2 NOT NULL,
    PRIMARY KEY (kb_article_id)
);

CREATE TABLE curated.work_notes (
    work_note_id VARCHAR(50) NOT NULL,
    incident_id VARCHAR(50) NOT NULL,
    author_user_id VARCHAR(50) NOT NULL,
    created_at DATETIME2 NOT NULL,
    note_text_clean VARCHAR(MAX) NOT NULL,
    note_html VARCHAR(MAX) NULL,
    PRIMARY KEY (work_note_id)
);

CREATE TABLE curated.resolution_notes (
    resolution_note_id VARCHAR(50) NOT NULL,
    incident_id VARCHAR(50) NOT NULL,
    author_user_id VARCHAR(50) NOT NULL,
    created_at DATETIME2 NOT NULL,
    note_text_clean VARCHAR(MAX) NOT NULL,
    note_html VARCHAR(MAX) NULL,
    PRIMARY KEY (resolution_note_id)
);

CREATE TABLE curated.change_requests (
    change_request_id VARCHAR(50) NOT NULL,
    number VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    state VARCHAR(50) NOT NULL,
    risk VARCHAR(50) NOT NULL,
    planned_start DATETIME2 NOT NULL,
    planned_end DATETIME2 NOT NULL,
    implemented_at DATETIME2 NULL,
    PRIMARY KEY (change_request_id)
);

CREATE TABLE curated.incident_changes (
    incident_id VARCHAR(50) NOT NULL,
    change_request_id VARCHAR(50) NOT NULL,
    relationship_type VARCHAR(100) NOT NULL
);

CREATE TABLE curated.slas (
    sla_id VARCHAR(50) NOT NULL,
    incident_id VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    stage VARCHAR(100) NOT NULL,
    target_hours DECIMAL(10, 2) NOT NULL,
    elapsed_hours DECIMAL(10, 2) NOT NULL,
    breached BIT NOT NULL,
    PRIMARY KEY (sla_id)
);

CREATE TABLE curated.attachments (
    attachment_id VARCHAR(50) NOT NULL,
    incident_id VARCHAR(50) NOT NULL,
    incident_number VARCHAR(50) NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    content_type VARCHAR(200) NOT NULL,
    description VARCHAR(2000) NULL,
    mock_url VARCHAR(1000) NOT NULL,
    uploaded_at DATETIME2 NOT NULL,
    file_size_kb INT NULL,
    PRIMARY KEY (attachment_id)
);

CREATE TABLE curated.images (
    image_id VARCHAR(50) NOT NULL,
    incident_id VARCHAR(50) NOT NULL,
    incident_number VARCHAR(50) NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    content_type VARCHAR(200) NOT NULL,
    description VARCHAR(2000) NULL,
    mock_url VARCHAR(1000) NOT NULL,
    uploaded_at DATETIME2 NOT NULL,
    width_px INT NULL,
    height_px INT NULL,
    PRIMARY KEY (image_id)
);

CREATE TABLE curated.documents (
    document_id VARCHAR(50) NOT NULL,
    incident_id VARCHAR(50) NOT NULL,
    incident_number VARCHAR(50) NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    content_type VARCHAR(200) NOT NULL,
    description VARCHAR(2000) NULL,
    mock_url VARCHAR(1000) NOT NULL,
    uploaded_at DATETIME2 NOT NULL,
    file_size_kb INT NULL,
    PRIMARY KEY (document_id)
);

CREATE TABLE curated.external_references (
    external_reference_id VARCHAR(50) NOT NULL,
    incident_id VARCHAR(50) NOT NULL,
    reference_type VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    url VARCHAR(1000) NOT NULL,
    source_system VARCHAR(100) NOT NULL,
    PRIMARY KEY (external_reference_id)
);

CREATE TABLE curated.incident_kb_links (
    incident_id VARCHAR(50) NOT NULL,
    kb_article_id VARCHAR(50) NOT NULL,
    relevance_reason VARCHAR(2000) NULL
);
