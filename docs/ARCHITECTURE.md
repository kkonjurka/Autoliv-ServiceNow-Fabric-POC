# Autoliv ServiceNow to Microsoft Fabric POC Architecture Plan

Date: 2026-06-17T14:52:27-04:00
Owner: Mal (Lead / Architect)

## 1. Objective

Build a minimum viable proof of concept that:

1. Exposes mock ServiceNow-style operational data through a SQLite-backed API.
2. Hosts that mock API in Azure Container Apps for shared HTTPS access.
3. Ingests the API into a real Microsoft Fabric Lakehouse or Warehouse.
4. Produces curated structured tables plus cleaned text/reference assets.
5. Deploys a Fabric semantic model, a scoped ontology layer, a Fabric Data Agent, and a Foundry-coordinated multi-agent experience.

## 2. Minimum Viable Demo Path

The fastest demo path is:

1. Build a read-only mock ServiceNow API backed by seeded SQLite.
2. Containerize it and deploy it to Azure Container Apps with `/health` and public HTTPS ingress.
3. Ingest incidents, users, groups, categories, KB articles, notes, changes, SLAs, and reference metadata into a Fabric Lakehouse.
4. Curate normalized Fabric tables and generate cleaned text from HTML-like fields.
5. Build a semantic model over the curated structured tables.
6. Deploy a Fabric Data Agent for structured operational questions.
7. Add one retrieval/index path for KB articles, work notes, and resolution notes.
8. Keep attachments, images, documents, and logs on a separate metadata-first path.
9. Define a Foundry orchestrator that routes across the structured, unstructured, and attachment/document paths.

## 3. Text Architecture Diagram

```text
IT Support User
   |
   v
Azure AI Foundry Orchestrator
   |------------------------------|-------------------------------|
   |                              |                               |
   v                              v                               v
Fabric Data Agent            Retrieval Service               Attachment/Document Tool
(structured route)           (unstructured route)            (metadata/reference route)
   |                              |                               |
   v                              v                               v
Fabric Semantic Model        Cleaned text index            Fabric attachment/document/image
   |                          + vector/search store         metadata + URLs + summaries
   v                              ^
Curated Fabric tables ------------|
   ^
   |
Fabric ingestion (Dataflow Gen2 / Pipeline / Notebook)
   ^
   |
Azure Container Apps-hosted Mock ServiceNow API
   ^
   |
SQLite seed database
```

## 4. Architecture Boundaries

### Source system boundary

- **Inside boundary:** SQLite schema, seed data, API contracts, pagination/filtering/search behavior.
- **Outside boundary:** Real ServiceNow connectivity, real ServiceNow auth, live upstream operational ownership.

### Hosting boundary

- **Inside boundary:** Container image, Azure Container Registry, Azure Container Apps, runtime configuration, health checks.
- **Outside boundary:** Enterprise-grade HA, durable mutable storage, private networking hardening beyond demo needs.

### Fabric data boundary

- **Inside boundary:** Raw landing, normalization, curated tables, relationship tables, cleaned text outputs, metadata preservation.
- **Outside boundary:** Full enterprise MDM, cross-domain data federation, production retention/governance automation.

### Semantic/ontology boundary

- **Inside boundary:** POC semantic model for ticket operations and a scoped ontology built from business entities.
- **Outside boundary:** Full enterprise knowledge graph, broad cross-department ontology, global taxonomy governance.

### Agent boundary

- **Inside boundary:** Foundry orchestration, Fabric Data Agent for structured questions, retrieval for unstructured text, separate attachment/document/image path.
- **Outside boundary:** Single-agent design, free-form direct access to raw source data, generalized enterprise copilots.

## 5. Mocked vs Production Direction

| Area | POC mock | Production direction |
| --- | --- | --- |
| Operational source | SQLite-backed API that mimics ServiceNow | Direct ServiceNow API ingestion, or approved interim mirrored enterprise source |
| API auth | Demo header or lightweight token if needed | Enterprise identity, secret rotation, managed auth |
| Source persistence | Read-only or reset-on-deploy SQLite | Durable operational systems outside the POC container |
| Hosting | Azure Container Apps public HTTPS endpoint | Hardened network path, managed identity, monitored release pipeline |
| Ingestion cadence | Manual or scheduled demo runs | Reliable orchestrated incremental ingestion |
| Text cleanup | Deterministic HTML-to-clean-text transforms | Production text normalization, richer enrichment and governance |
| Semantic model scope | Focused ticket-ops model | Broader domain model aligned to ServiceNow and business standards |
| Ontology scope | Small scoped graph from semantic entities | Managed ontology lifecycle and domain expansion |
| Retrieval corpus | KB, work notes, resolution notes, metadata refs | Larger indexed corpus with enterprise access controls |
| Attachments/documents | Metadata-first with mock URLs and summaries | Actual secure document pipelines, OCR/extraction, entitlement-aware access |
| Agent orchestration | Foundry design centered on three tool paths | Hardened orchestration, observability, policy controls, feedback loops |

## 6. Implementation Plan

### Phase 1 - Backend/API and SQLite seed data

Deliver:

- SQLite schema for incidents, users, groups, categories, changes, incident-change links, SLAs, KB articles, work notes, resolution notes, attachments, images, documents, and references.
- Seed data with open/closed incidents, similar historical cases, and HTML-like content.
- API endpoints for health, incidents, single incident detail, similar tickets, open follow-up tickets, KB articles, and reference metadata.

Exit criteria:

- Local API returns realistic data.
- Filtering and pagination work.
- Single incident payload includes related entities.

### Phase 2 - Containerization and Azure Container Apps

Deliver:

- Dockerfile and startup flow that ships or initializes the SQLite seed database.
- Azure Container Registry push path.
- Azure Container App with external HTTPS ingress.
- Runtime configuration contract for Fabric callers.

Exit criteria:

- Public `/health` is green.
- Core API endpoints respond through HTTPS.

### Phase 3 - Fabric ingestion

Deliver:

- One chosen ingestion mechanism: **Dataflow Gen2 first preference**, then pipeline, then notebook if transformation flexibility is needed.
- Raw landing zone in Fabric Lakehouse or Warehouse.
- Repeatable ingestion of all in-scope entities from the ACA endpoint.

Exit criteria:

- Fabric can pull from the ACA API.
- Raw row counts match source expectations.

### Phase 4 - Transformation and curated Fabric tables

Deliver:

- Curated normalized tables for structured analytics.
- Relationship tables linking incidents to users, groups, changes, KBs, attachments, images, documents, and references.
- Cleaned text outputs from HTML-like KB and note content.

Exit criteria:

- Curated tables support joins without raw API dependence.
- Clean text is preserved separately from original markup.

### Phase 5 - Semantic model and ontology layer

Deliver:

- Fabric semantic model with ticket operations dimensions and measures.
- Scoped ontology artifact or documented implementation path built from semantic entities.

Exit criteria:

- Structured operational questions can be answered from the semantic model.
- Ontology relationships map to ticket-resolution use cases.

### Phase 6 - Fabric Data Agent

Deliver:

- Deployed or deployable Fabric Data Agent connected to the semantic model.

Exit criteria:

- Agent answers structured questions on backlog, SLA status, aging, category trends, and resolution patterns.

### Phase 7 - Retrieval/index design

Deliver:

- Search/vector path for cleaned KB, work notes, resolution notes, and similar incidents.
- Grounding metadata back to incident, KB, document, and attachment references.

Exit criteria:

- Retrieval returns grounded sources for unstructured support questions.

### Phase 8 - Foundry orchestration design

Deliver:

- Foundry orchestrator contract that routes:
  - structured questions to Fabric Data Agent
  - unstructured narrative questions to retrieval
  - attachment/document/image requests to the separate metadata path

Exit criteria:

- No monolithic agent assumption.
- Every answer path preserves source attribution.

### Phase 9 - Tests and smoke checks

Deliver:

- API smoke tests
- Container health validation
- Fabric ingestion validation
- Curated data row-count checks
- Semantic model and Data Agent sample questions
- Retrieval grounding checks

### Phase 10 - Demo documentation

Deliver:

- Demo runbook
- Validation checklist
- Example user questions and expected answer routes

## 7. Component Responsibilities

| Component | Responsibility | Must not own |
| --- | --- | --- |
| Mock API | ServiceNow-like contract and demo data source | Fabric modeling, semantic logic, orchestration |
| Azure Container Apps | Shared HTTPS hosting for the mock API | Durable transactional storage strategy |
| Fabric ingestion | Pull raw source data into Fabric | End-user question answering |
| Curated Fabric tables | Normalized business entities and relationships | Vector search orchestration |
| Semantic model | Structured business measures and dimensions | Document/image retrieval |
| Ontology layer | Scoped business relationships for agent reasoning | Full enterprise graph ambitions |
| Fabric Data Agent | Structured semantic-model Q&A | Full text retrieval or attachment parsing |
| Retrieval/index layer | KB/work-note/resolution-note search and similarity | Structured metric calculation |
| Attachment/document/image path | Reference metadata, URLs, summaries, file-type routing | Semantic model responsibilities |
| Foundry orchestrator | Intent routing, composition, grounding | Direct raw-source analytics |

## 8. Recommended First Demo Scope

Prioritize:

1. Incidents
2. Users
3. Assignment groups
4. Categories/subcategories
5. KB articles
6. Work notes
7. Resolution notes
8. SLAs
9. Change requests
10. Attachment/document/image metadata

Defer unless needed:

- Ticket creation or mutation
- Full attachment content processing
- Bidirectional ServiceNow sync
- Broad non-incident modules

## 9. Risks

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| Overloading the Fabric Data Agent | It will not reliably cover unstructured and attachment-heavy questions alone | Enforce three-path design: structured, retrieval, attachment/document |
| Weak mock data realism | Demo will fail to show useful similarity and resolution patterns | Seed repeated symptom clusters, varied priorities, and grounded references |
| Fabric ingestion brittleness | Shared demo depends on stable ACA-to-Fabric connectivity | Prefer simple ingestion pattern, keep API schema stable, validate row counts |
| HTML/text cleanup quality | Poor cleaned text weakens retrieval accuracy | Preserve raw HTML and clean text side by side for debugging |
| Attachment ambiguity | Users will expect logs, screenshots, and scripts to appear in answers | Start metadata-first, preserve URLs/summaries, clearly label non-indexed assets |
| Scope sprawl | POC may drift into production-grade platform work | Lock MVP to incident-resolution scenarios and Prompt 10 order |
| Missing deployability | Documentation-only assets would undercut the demo | Require deployable Fabric semantic model/Data Agent artifacts or concrete deployment path |

## 10. Open Questions

1. Should the POC focus purely on direct mock API to Fabric, or keep an interim Snowflake/mirrored-data option visible?
2. Which Fabric ingestion option is preferred by the team for the first pass: Dataflow Gen2, pipeline, or notebook?
3. Is the first demo strictly incidents plus supporting references, or must it include broader ServiceNow modules?
4. What exact attachment types matter most in the first demo: screenshots, logs, scripts, documents, or all?
5. What minimum evidence is required to call the semantic model and Fabric Data Agent "deployable" in this repository?
6. Where will retrieval/index assets physically live for the POC, and what service will back search/vector queries?
7. Are there Autoliv naming standards or semantic entities that should shape the curated model before implementation starts?

## 11. Implementation Decision Summary

1. Keep the mock API outside Fabric and treat Fabric as the authoritative demo data layer after ingestion.
2. Use Azure Container Apps as the shared HTTPS hosting boundary for the mock source.
3. Separate the architecture into three answer paths: structured semantic, unstructured retrieval, and attachment/document/image retrieval.
4. Build the ontology from curated semantic/business entities, not directly from raw landing tables.
5. Optimize for demo completeness and grounded answers rather than production hardening.

## 12. Recommended Specialist Ownership

| Workstream | Primary specialist |
| --- | --- |
| Architecture governance, scope, and review | Mal |
| Mock ServiceNow API, SQLite schema, and seed data | Backend/API specialist |
| Containerization, ACR, and Azure Container Apps deployment | Azure deployment specialist |
| Fabric ingestion, curated tables, and transformations | Data engineering specialist |
| Semantic model and ontology implementation | Semantic model and ontology specialist |
| Retrieval/index design for KB and notes | Search/retrieval specialist |
| Foundry routing and multi-agent orchestration | Foundry orchestration specialist |
| Smoke checks and demo validation | Testing and validation specialist |
| Demo runbook and storytelling | Documentation/demo specialist |
