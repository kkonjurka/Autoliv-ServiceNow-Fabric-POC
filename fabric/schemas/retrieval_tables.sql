-- Retrieval-oriented tables remain separate from the semantic-model star schema.

CREATE TABLE retrieval.retrieval_documents (
    retrieval_document_id VARCHAR(100) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(50) NOT NULL,
    incident_id VARCHAR(50) NULL,
    kb_article_id VARCHAR(50) NULL,
    title VARCHAR(500) NOT NULL,
    clean_text VARCHAR(MAX) NOT NULL,
    html_source VARCHAR(MAX) NULL,
    updated_at DATETIME2 NOT NULL,
    metadata_json VARCHAR(MAX) NULL,
    PRIMARY KEY (retrieval_document_id)
);
