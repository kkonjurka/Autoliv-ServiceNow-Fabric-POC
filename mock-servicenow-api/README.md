# Mock ServiceNow API

SQLite-backed FastAPI service for the Autoliv ServiceNow to Microsoft Fabric POC. The service seeds realistic incidents, knowledge articles, notes, SLA records, attachments, images, documents, change requests, and external references so Fabric notebooks and ingestion flows can call a demo-friendly API.

## What is included

- 32 seeded incidents with open and closed states, repeated symptom clusters, and linked resolution patterns
- 8 knowledge articles with HTML-rich content plus cleaned text fields
- Assignment groups, users, categories, change requests, SLAs, work notes, resolution notes, and incident-to-change links
- Attachment, image, and document metadata with mock URLs
- FastAPI endpoints for health, paginated incidents, filtered searches, open follow-up views, knowledge articles, and asset metadata

## Project layout

```text
mock-servicenow-api\
  app\
    main.py
    database.py
    models.py
    routes\
      incidents.py
      kb_articles.py
      attachments.py
      health.py
    seed\
      seed_data.py
  tests\
    test_api.py
  requirements.txt
  Dockerfile
  .env.example
```

## Endpoints

- `GET /health`
- `GET /incidents`
- `GET /incidents/history/search`
- `GET /incidents/follow-up/open`
- `GET /incidents/{incident_id}`
- `GET /kb-articles`
- `GET /attachments`
- `GET /images`
- `GET /documents`

## Filters and behavior

### Incidents

`GET /incidents` supports:

- `page`
- `page_size`
- `state`
- `priority`
- `category`
- `assignment_group`
- `updated_since`
- `requester`

Example:

```powershell
Invoke-WebRequest "http://localhost:8000/incidents?page=1&page_size=5&state=In%20Progress&category=Database" | Select-Object -Expand Content
```

### Historical incidents

`GET /incidents/history/search` supports:

- `keyword` (required)
- `category`
- `page`
- `page_size`

### Open follow-up tickets

`GET /incidents/follow-up/open` supports:

- `limit`

### Knowledge articles

`GET /kb-articles` supports:

- `page`
- `page_size`
- `category`
- `keyword`

### Assets

`GET /attachments`, `GET /images`, and `GET /documents` support:

- `page`
- `page_size`
- `incident_id`

## Local setup

1. From the repository root, change into the API folder:

   ```powershell
   Set-Location .\mock-servicenow-api
   ```

2. Copy the environment template:

   ```powershell
   Copy-Item .env.example .env
   ```

3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Run the API:

   ```powershell
   python -m app.main
   ```

5. Smoke test:

   ```powershell
   python -m pytest -q
   ```

The database is created automatically at `SERVICENOW_DB_PATH` and reseeded on startup when `SERVICENOW_RESEED_ON_STARTUP=true`.

## Docker

Build and run locally:

```powershell
docker build -t servicenow-mock-api .
docker run --rm -p 8000:8000 servicenow-mock-api
```
