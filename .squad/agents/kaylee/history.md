# Kaylee — History

## Project Context
- **Project:** Autoliv ServiceNow to Microsoft Fabric POC
- **Stack:** SQLite, API framework (Node.js or Python)
- **User:** @kkonjuramicrosoft

## Learnings
- `mock-servicenow-api\app\database.py` owns SQLite schema creation and startup initialization, with separate tables for incidents, notes, KB links, incident-change links, SLAs, attachments, images, documents, and external references.
- `mock-servicenow-api\app\seed\seed_data.py` seeds scenario-based mock data anchored to the provided CURRENT_DATETIME constant and stores both HTML-rich and cleaned text fields for downstream retrieval.
- `mock-servicenow-api\app\routes\incidents.py`, `kb_articles.py`, and `attachments.py` follow a paginated list plus focused detail pattern, with incident detail aggregating all related domains in one response for Fabric-friendly ingestion.


## Session Update (2026-06-17T18-52-27Z)

API schema finalized at mock-servicenow-api/app/database.py — 32 incident templates, 8 KB article corpus

