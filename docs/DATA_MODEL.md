# Fabric Data Model

Prepared on 2026-06-17 for the Autoliv ServiceNow to Microsoft Fabric POC.

## Curated table inventory

| Table | Grain | Key fields | Purpose |
| --- | --- | --- | --- |
| `incidents` | One row per incident | `incident_id`, `number`, `requester_id`, `assignee_id`, `assignment_group_id`, `category_id` | Core ticket fact for backlog, SLA, aging, reopen/follow-up, and resolution analysis |
| `users` | One row per user exposed by the API | `user_id`, `email`, `department` | Shared dimension for requester, assignee, and note author analysis |
| `assignment_groups` | One row per support group | `assignment_group_id`, `name` | Assignment and support workload dimension |
| `categories` | One row per category/subcategory pair | `category_id`, `name`, `subcategory` | Shared incident/KB topic dimension |
| `kb_articles` | One row per KB article | `kb_article_id`, `kb_article_number`, `category_id` | Structured KB metadata for reuse and coverage reporting |
| `work_notes` | One row per work note | `work_note_id`, `incident_id`, `author_user_id` | Timeline of investigation activity |
| `resolution_notes` | One row per resolution note | `resolution_note_id`, `incident_id`, `author_user_id` | Resolution-specific narrative linked to tickets |
| `change_requests` | One row per change request | `change_request_id`, `number` | Dimension for remediation/change tracking |
| `incident_changes` | One row per incident/change relationship | `incident_id`, `change_request_id`, `relationship_type` | Bridge table between tickets and changes |
| `slas` | One row per SLA record | `sla_id`, `incident_id` | SLA attainment and breach analytics |
| `attachments` | One row per attachment metadata asset | `attachment_id`, `incident_id`, `mock_url` | Attachment lookup path for document/log tools |
| `images` | One row per image metadata asset | `image_id`, `incident_id`, `mock_url` | Screenshot/image tool routing metadata |
| `documents` | One row per document metadata asset | `document_id`, `incident_id`, `mock_url` | Document retrieval metadata |
| `external_references` | One row per external reference | `external_reference_id`, `incident_id`, `url` | Traceability to external systems and evidence |
| `incident_kb_links` | One row per incident/article relationship | `incident_id`, `kb_article_id` | Bridge table for KB reuse analysis |

## Separate unstructured output

| Table | Grain | Purpose |
| --- | --- | --- |
| `retrieval_documents` | One row per cleaned text asset (`incident_description`, `incident_resolution_summary`, `work_note`, `resolution_note`, `kb_article`) | Search/vector-ready corpus with source IDs and metadata JSON |

## Relationship model

- `incidents.requester_id` → `users.user_id`
- `incidents.assignee_id` → `users.user_id`
- `work_notes.author_user_id` → `users.user_id`
- `resolution_notes.author_user_id` → `users.user_id`
- `incidents.assignment_group_id` → `assignment_groups.assignment_group_id`
- `incidents.category_id` → `categories.category_id`
- `kb_articles.category_id` → `categories.category_id`
- `work_notes.incident_id`, `resolution_notes.incident_id`, `slas.incident_id`, `attachments.incident_id`, `images.incident_id`, `documents.incident_id`, `external_references.incident_id` → `incidents.incident_id`
- `incident_changes.incident_id` → `incidents.incident_id`
- `incident_changes.change_request_id` → `change_requests.change_request_id`
- `incident_kb_links.incident_id` → `incidents.incident_id`
- `incident_kb_links.kb_article_id` → `kb_articles.kb_article_id`
- `retrieval_documents.incident_id` and `retrieval_documents.kb_article_id` point back to the structured entities used for grounding

## Transformation assumptions

1. Raw ingestion lands API payloads exactly as returned by the mock ServiceNow API into Lakehouse `Files/raw/servicenow/...`, preserving pagination envelopes and full incident-detail documents.
2. `/incidents` is used only to discover paginated IDs; `/incidents/{id}` is the authoritative source for nested notes, SLAs, KB links, change requests, and external references.
3. `/attachments`, `/images`, and `/documents` are the authoritative source for asset metadata because they already expose incident number plus asset-specific shape.
4. HTML cleaning prefers the HTML field when present and falls back to the API's plain-text field when HTML is null.
5. Structured curated tables retain descriptive metadata and cleaned text needed for analytics, but the retrieval/search path is isolated in `retrieval_documents`.
6. The API does not expose every SQLite source column for users (for example `employee_number` and `manager_name`), so the curated `users` table is limited to fields surfaced by the API contract.
7. Keywords are flattened to a comma-separated string in `kb_articles` for warehouse compatibility; the original array remains in raw JSON.

## Ingestion and transformation flow

1. `fabric/notebooks/01_ingest_raw.py`
   - Calls the Azure Container Apps-hosted mock API
   - Paginates `/incidents`, `/kb-articles`, `/attachments`, `/images`, and `/documents`
   - Fans out to `/incidents/{id}` for full-detail payloads
   - Lands raw JSON plus a `raw_api_manifest` Delta table
2. `fabric/notebooks/03_html_to_text.py`
   - Removes HTML tags, scripts/styles, normalizes whitespace, and registers Spark UDFs
3. `fabric/notebooks/02_transform_curated.py`
   - Reads landed JSON
   - Normalizes nested collections into relational tables
   - Writes curated Delta tables plus `retrieval_documents`

## Data dictionary

### `incidents`

| Column | Meaning |
| --- | --- |
| `incident_id` | Stable incident surrogate from the API/source system |
| `number` | Human-readable incident number such as `INC0001234` |
| `state`, `priority`, `impact`, `urgency` | Operational status attributes for backlog and SLA slicing |
| `opened_at`, `updated_at`, `resolved_at` | Event timestamps used for trend, aging, and resolution measures |
| `follow_up_required`, `follow_up_reason` | Flags tickets needing continued action |
| `requester_id`, `assignee_id`, `assignment_group_id`, `category_id` | Foreign keys into user/group/category dimensions |
| `description_text_clean`, `resolution_summary_text_clean` | Cleaned text retained for lightweight ticket context |

### `users`

| Column | Meaning |
| --- | --- |
| `user_id` | User key from the API |
| `full_name`, `email`, `title`, `location`, `department` | User profile attributes available through the mock routes |

### `assignment_groups`

| Column | Meaning |
| --- | --- |
| `assignment_group_id` | Support group key |
| `name`, `description`, `escalation_email` | Group metadata for ownership reporting |

### `categories`

| Column | Meaning |
| --- | --- |
| `category_id` | Category key shared by incidents and KB articles |
| `name`, `subcategory` | Topic hierarchy used in semantic filtering |

### `kb_articles`

| Column | Meaning |
| --- | --- |
| `kb_article_id`, `kb_article_number` | Stable and human-readable KB identifiers |
| `title`, `audience`, `category_id` | Structured article metadata |
| `content_text_clean`, `content_html` | Cleaned retrieval text plus original HTML payload |
| `keywords` | Flattened keyword list for filtering or boosting |
| `published_at`, `updated_at` | Knowledge freshness timestamps |

### `work_notes` and `resolution_notes`

| Column | Meaning |
| --- | --- |
| Note ID | Stable note key |
| `incident_id` | Parent incident |
| `author_user_id` | Note author |
| `created_at` | Note timestamp |
| `note_text_clean`, `note_html` | Cleaned and original note content |

### `change_requests` and `incident_changes`

| Column | Meaning |
| --- | --- |
| `change_request_id`, `number`, `title`, `state`, `risk` | Change record metadata |
| `planned_start`, `planned_end`, `implemented_at` | Change timing fields |
| `incident_changes.relationship_type` | Nature of the incident/change relationship |

### `slas`

| Column | Meaning |
| --- | --- |
| `sla_id` | SLA row key |
| `incident_id` | Parent ticket |
| `name`, `stage` | SLA definition and lifecycle stage |
| `target_hours`, `elapsed_hours`, `breached` | SLA performance metrics |

### `attachments`, `images`, `documents`

| Column | Meaning |
| --- | --- |
| Asset ID | Stable asset key per domain |
| `incident_id`, `incident_number` | Parent ticket references |
| `file_name`, `content_type`, `description` | Tool-facing asset metadata |
| `mock_url` | Retrieval/download URL for a downstream document or image tool |
| `uploaded_at` | Asset timestamp |
| `file_size_kb` / `width_px` / `height_px` | Domain-specific metadata |

### `external_references`

| Column | Meaning |
| --- | --- |
| `external_reference_id` | Reference row key |
| `incident_id` | Parent ticket |
| `reference_type`, `title`, `url`, `source_system` | Link-out metadata for external evidence |

### `incident_kb_links`

| Column | Meaning |
| --- | --- |
| `incident_id`, `kb_article_id` | Bridge keys |
| `relevance_reason` | Why the article is tied to the incident |

### `retrieval_documents`

| Column | Meaning |
| --- | --- |
| `retrieval_document_id` | Unique retrieval corpus key |
| `source_type` | `incident_description`, `incident_resolution_summary`, `work_note`, `resolution_note`, or `kb_article` |
| `source_id` | Source row key from the originating table |
| `incident_id`, `kb_article_id` | Back-pointers for grounded results |
| `title` | Retrieval display label |
| `clean_text`, `html_source` | Search-ready content and original HTML |
| `updated_at`, `metadata_json` | Freshness and extra filter/routing metadata |

## Support for the semantic model and agent architecture

- **Semantic model path:** `incidents` is the central fact table; `users`, `assignment_groups`, `categories`, and `change_requests` provide dimensions/bridges needed for ticket volume, backlog, SLA, resolution time, follow-up, and KB reuse metrics.
- **Fabric Data Agent path:** The structured tables keep joins explicit and avoid nested JSON, which makes SQL- and semantic-model-based answers predictable.
- **Retrieval path:** `retrieval_documents` isolates cleaned narrative content for vector or keyword indexing without polluting the analytics model.
- **Document/image/attachment tool path:** `attachments`, `images`, and `documents` keep only metadata plus `mock_url`, enabling a separate file-aware toolchain to resolve binaries or previews on demand.
