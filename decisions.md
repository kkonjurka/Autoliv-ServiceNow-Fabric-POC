# Decision: Fabric Semantic Model and Scoped Ontology

**Date:** 2026-06-17T15:02:35.115-04:00  
**Author:** Book, Semantic Modeler  
**Status:** Proposed  
**Requester:** @kkonjuramicrosoft

---

## Decision Statement

Design the Fabric business layer for the POC as:

1. A **ticket-centered semantic model** with `FactTickets` as the core fact table
2. A separate **`FactSla`** table for SLA analysis
3. Bridge tables for **KB reuse, assets, changes, and resolution patterns**
4. A scoped ontology generated from semantic entities for tickets, users, groups, categories, services, KBs, assets, changes, and resolution patterns
5. A Fabric Data Agent pointed at the published semantic model for structured operational questions only

---

## Problem

The POC needs a business-friendly semantic layer that:

- Answers structured operational questions about backlog, priorities, SLAs, aging, categories, groups, services, and KB reuse
- Keeps ontology scope intentionally small and explainable
- Preserves separation between structured analytics and unstructured retrieval
- Supports a Fabric Data Agent without exposing raw lakehouse complexity

The curated source tables are broad enough to support analytics, but the POC still needs explicit semantic choices for grain, dimensions, measures, and graph relationships.

---

## Proposed Solution

### 1. Semantic model shape

- `FactTickets` at one row per incident
- `FactSla` at one row per SLA record
- Conformed dimensions for date, user, assignment group, category, business service, priority, state, resolution code, KB article, and asset type
- Derived `DimResolutionPattern` for normalized fix patterns

### 2. Bridge strategy

- `BridgeTicketKnowledgeArticle` for ticket-to-KB reuse
- `BridgeTicketAsset` for attachment, image, and document references
- `BridgeTicketChange` for incident-to-change relationships
- `BridgeTicketResolutionPattern` for derived fix-pattern relationships

### 3. Ontology scope

Nodes:
- Ticket
- User/requester
- Support group
- Category/subcategory
- Business service
- Knowledge article
- Attachment
- Document
- Image
- Change request
- Resolution pattern

Relationships:
- Ticket opened by User
- Ticket assigned to Group
- Ticket belongs to Category
- Ticket impacts Business Service
- Ticket references KB
- Ticket has Attachment / Document / Image
- Ticket relates to Change
- Ticket resolved by Pattern

### 4. Fabric Data Agent boundary

The Data Agent should answer only structured semantic-model questions. Narrative note retrieval, similar-incident search, and attachment/image/document inspection stay on separate tool paths.

---

## Rationale

### Why a ticket-centered star?

- Most support questions start from incident volume, backlog, aging, category, group, or service
- `FactTickets` gives a clean grain for those questions
- It keeps Data Agent answers interpretable

### Why split SLA into its own fact?

- A ticket can carry multiple SLA rows
- Separate SLA grain avoids ambiguous ticket duplication
- It makes breach logic clearer and easier to validate

### Why use bridges?

- KB articles, assets, changes, and resolution patterns are naturally many-to-many with tickets
- Bridges preserve relationship fidelity without bloating the ticket fact
- The same bridges can directly feed ontology edges

### Why derive the ontology from the semantic model?

- It keeps business definitions aligned across analytics and graph traversal
- It avoids recreating logic from raw source tables in two places
- It supports explainable graph outputs for the POC

---

## Trade-offs

| Choice | Pros | Cons |
| --- | --- | --- |
| Ticket-centered star schema | Clear, business-friendly, Data Agent ready | Needs bridges for richer relationships |
| Derived business service dimension | Allows service slicing now | Temporary until CMDB/service source exists |
| Derived resolution pattern dimension | Enables pattern frequency and ontology links | Requires normalization logic and confidence handling |
| Distinct-ticket SLA breach counting | Easier business interpretation | Hides multiple breached SLA rows unless separately reported |

---

## Success Criteria

- [ ] Semantic model answers required structured ticket questions
- [ ] All required dimensions and measures are defined and named clearly
- [ ] SLA analysis does not duplicate ticket counts
- [ ] KB reuse and resolution-pattern questions work through explicit bridges
- [ ] Ontology node and edge scope stays small enough for explainable traversal
- [ ] Fabric Data Agent routing remains limited to structured domains

---

## Dependencies

- Curated Fabric tables from Inara
- Published semantic model in Fabric
- Agreement on business-service derivation rules
- A derived reopen signal if `Reopen Rate` is to be treated as production-ready

---

## Implementation Sequence

1. Create semantic-layer views and bridge tables in Fabric
2. Build dimensions, facts, and measures in the semantic model
3. Validate KPI definitions with sample questions
4. Configure the Fabric Data Agent against the published model
5. Export node and relationship views from the semantic model for ontology use

---

## Document Links

- `docs/SEMANTIC_MODEL.md`
- `fabric/semantic-model/model.tmdl`
- `fabric/semantic-model/data-agent-config.md`

---

## Next Action

Review the semantic design with the Fabric modeling and retrieval owners, then implement the semantic-layer views and publish the model in Fabric.


---

# Decision: Fabric Data Layer for the ServiceNow POC

**Date:** 2026-06-17  
**Author:** Inara, Data Engineer  
**Status:** Proposed  
**Requester:** @kkonjuramicrosoft

---

## Decision Statement

Implement the Fabric data layer as a three-step pattern:
- **Raw landing notebook** that copies paginated mock ServiceNow API JSON into the Lakehouse
- **Curated transformation notebook** that normalizes nested incident detail into relational Delta tables
- **Separate retrieval corpus table** that stores cleaned narrative text apart from the semantic-model tables

---

## Problem

The POC needs one Fabric-ready path that supports both:
1. Structured analytics for the semantic model and Fabric Data Agent
2. Cleaned unstructured content for retrieval over KB articles, notes, and ticket narratives

The source API exposes a mix of paginated collections and deeply nested incident details, so the data layer must preserve raw fidelity first and then flatten the model without mixing analytical facts and retrieval text.

---

## Proposed Solution

### 1. Raw landing

- Notebook: `fabric/notebooks/01_ingest_raw.py`
- Land raw payloads under `Files/raw/servicenow/<dataset>/<list|detail>/load_date=YYYY-MM-DD/`
- Persist a `raw_api_manifest` Delta table for lineage (`dataset_name`, endpoint, page/detail, landed path, extracted timestamp)

### 2. Curated structured model

Normalize raw data into these required tables:
- `incidents`
- `users`
- `assignment_groups`
- `categories`
- `kb_articles`
- `work_notes`
- `resolution_notes`
- `change_requests`
- `incident_changes`
- `slas`
- `attachments`
- `images`
- `documents`
- `external_references`
- `incident_kb_links`

### 3. Retrieval corpus split

- Additional table: `retrieval_documents`
- One row per cleaned text asset from incident descriptions, resolution summaries, work notes, resolution notes, and KB articles
- Carries source IDs plus metadata JSON for downstream indexing

### 4. HTML cleaning

- Notebook: `fabric/notebooks/03_html_to_text.py`
- Remove markup, ignore `script/style`, normalize whitespace, and register Spark UDFs
- Prefer HTML as the canonical text source, with fallback to the API plain-text field

---

## Rationale

### Why raw JSON first?
- Preserves the exact API contract for replay/debugging
- Supports future incremental reprocessing without re-calling the API
- Keeps pagination envelopes available for ingestion validation

### Why use incident detail as the main source?
- `/incidents/{id}` is the only route that exposes notes, SLAs, change links, KB links, and references in one payload
- It reduces join ambiguity compared with reconstructing relationships from list endpoints alone

### Why split retrieval text from curated facts?
- Semantic models want stable, narrow, relational tables
- Retrieval wants long-form cleaned text with richer payload metadata
- Keeping them separate prevents narrative content from bloating fact tables

---

## Trade-offs

| Choice | Pros | Cons |
| --- | --- | --- |
| Fan out to every incident detail | Complete nested data capture | More API calls than list-only ingestion |
| Separate retrieval table | Clean semantic model, easier indexing | One extra transform/output to maintain |
| Asset metadata only in Fabric | Lightweight and tool-friendly | Binary/file contents need a separate retrieval path |
| API-shaped users table | Matches ingestible contract | Source-only user columns remain unavailable unless the API is extended |

---

## Success Criteria

- [ ] Raw API payloads land in the Lakehouse with traceable manifest rows
- [ ] Required curated tables materialize as normalized Delta tables
- [ ] Cleaned text is available separately for retrieval/indexing
- [ ] Incident, KB, change, SLA, note, and asset relationships remain joinable by explicit keys
- [ ] Output design supports both semantic model and agent/retrieval architecture

---

## Dependencies

- Azure Container Apps-hosted mock API available at `MOCK_SERVICENOW_API_BASE_URL`
- Fabric Lakehouse attached to the notebook session
- Follow-on semantic model work consumes curated structured tables
- Follow-on retrieval work consumes `retrieval_documents` and asset metadata tables

---

## Implementation Sequence

1. Run `01_ingest_raw.py` to land raw JSON and manifest rows
2. Run `03_html_to_text.py` to register cleaning helpers if needed
3. Run `02_transform_curated.py` to write curated Delta tables
4. Validate row counts, foreign-key completeness, and cleaned text outputs
5. Hand off curated tables to semantic-model and retrieval owners

---

## Document Links

- **Design Doc:** `docs/DATA_MODEL.md`
- **Schema DDL:** `fabric/schemas/curated_tables.sql`, `fabric/schemas/retrieval_tables.sql`
- **Related Prompt:** `SQUAD_PROMPTS.md` > Prompt 4

---

**Stakeholders:** Book (semantic model), Jayne (retrieval), River (orchestration)  
**Review Status:** ⏳ Pending team review  
**Decision Owner:** Inara, Data Engineer


---

# Decision: Retrieval Layer Design for Unstructured ServiceNow Content

**Date:** 2026-06-17  
**Author:** Jayne, Search/Retrieval Specialist  
**Status:** Proposed  
**Requester:** @kkonjuramicrosoft

---

## Decision Statement

Design and document the retrieval layer for the Autoliv ServiceNow to Microsoft Fabric POC using:
- **Azure AI Search** for indexing and searching unstructured content (KB articles, work notes, resolution notes)
- **Three separate indexes** (KB articles, incident content, attachments) for targeted search
- **Hybrid search** (BM25 keyword + vector embeddings) for combined relevance
- **Metadata filtering** to scope results by category, priority, state, date range, and attachment type
- **Grounded references** linking every result back to source incidents, KB articles, and attachments

---

## Problem

The POC needs to enable IT support users to:
1. Find similar historical tickets and how they were resolved
2. Search for relevant knowledge base articles
3. Locate related attachments, logs, and documents
4. Receive answers grounded with references to source incidents

Current design requires a clear retrieval architecture that:
- Distinguishes between structured (Fabric Data Agent) and unstructured (retrieval) paths
- Supports keyword and semantic search
- Returns rich metadata without storing binary files
- Maintains traceability back to source systems

---

## Proposed Solution

### 1. Three-Index Architecture

**Index 1: KB Articles** (`kb-articles-index`)
- Searchable fields: title, content
- Filterable: category, subcategory, created_date, updated_date
- Signals: view_count, useful_count (for relevance boosting)
- Purpose: Self-service KB search and resolution guidance

**Index 2: Incident Content** (`incident-content-index`)
- Searchable fields: description, work_notes, resolution_notes, summary
- Filterable: incident_state (open/closed), priority, category, assigned_group, created_date, closed_date, resolution_time_minutes, reopen_count
- Signals: quick resolution time (boost), no reopens (boost), priority level
- Purpose: Historical similarity search for how similar issues were resolved

**Index 3: Attachments** (`attachments-index`)
- Searchable fields: file_name, description
- Filterable: incident_id, kb_article_id, attachment_type, uploaded_date, file_type
- Purpose: Find relevant attachments (logs, scripts, screenshots, documents)

### 2. Hybrid Search Ranking

Combine three scoring components:

1. **BM25 Keyword Matching** (60% weight)
   - TF-IDF style relevance
   - Title weighted 2x higher than content

2. **Vector Similarity** (40% weight)
   - Cosine similarity against query embedding
   - Captures semantic synonyms and intent

3. **Signal Boosting** (+0.1 to +0.25)
   - Quick resolution time: +0.25 (indicates effective solution)
   - No reopens: +0.15 (indicates stable resolution)
   - Popular KB articles: +0.15-0.20 (useful_count signal)
   - Freshness: +0.10 (recent updates)
   - Critical priority: +0.20 (relevance signal for high-impact issues)

### 3. Metadata Filtering

Support common filter patterns:
- **KB search:** Category, subcategory, date range
- **Incident search:** State (closed/open), priority, category, assignment group, date range, resolution time
- **Attachment search:** Incident ID, attachment type, file type

Filters applied **after** keyword/vector search to reduce false negatives.

### 4. Grounded Results

Every retrieval result includes:
- **source_url:** Direct link to incident/KB/attachment in mock ServiceNow
- **metadata:** Category, priority, resolution time, signals
- **match_details:** Why the result matched (keyword vs. semantic)
- **content:** Snippet of title, description, or resolution notes

### 5. Embedding Strategy

- **Model:** Azure OpenAI `text-embedding-3-small` (1536-dim)
- **Timing:** Generate embeddings during Fabric ingestion setup
- **Refresh:** Daily batch updates when incidents/KB/attachments change
- **Cost:** ~$0.05-0.10 for full POC indexing

---

## Rationale

### Why Azure AI Search?
- Native hybrid search (BM25 + vector in single query)
- Metadata filtering support
- Scales to production easily
- Integrates with Azure OpenAI for embeddings

### Why Three Separate Indexes?
- **Isolation:** Different search patterns for KB, incidents, attachments
- **Flexibility:** Can update KB index independently from incident index
- **Performance:** Smaller indexes = faster queries
- **Clarity:** Easier for orchestrator to route queries to appropriate index

### Why Hybrid Search?
- **Keyword precision:** BM25 catches exact phrase matches
- **Semantic recall:** Vectors find synonyms and related concepts
- **Best of both:** Outperforms keyword-only or vector-only for most queries

### Why Separate from Fabric Data Agent?
- **Structured vs. Unstructured:** Fabric Data Agent handles metrics, counts, aggregations (structured)
- **Different models:** KB/work notes use text analysis; structured data uses SQL/DAX
- **Scalability:** Retrieval system designed for document search, not aggregations

---

## Trade-offs

| Choice | Pros | Cons |
|--------|------|------|
| **Hybrid search** (BM25 + vector) | Best quality, captures both precision and recall | Slightly higher cost per query than keyword-only |
| **Three separate indexes** | Cleaner design, easier updates | More maintenance, higher storage |
| **Mock embeddings** (not actual binary) | Keeps POC lightweight, focus on architecture | Limited to metadata/text, not image visual search |
| **Signal boosting** | Simple, effective, interpretable | Requires tuning per domain |
| **Metadata filters** (pre-sort, post-search) | Better for structured fields | Cannot filter during vector scoring |

---

## Success Criteria

**Index Health:**
- [ ] 100% of KB articles indexed
- [ ] 100% of incidents indexed
- [ ] All embeddings generated successfully
- [ ] No documents with vector errors

**Search Quality:**
- [ ] Keyword search: relevant results in top 3
- [ ] Vector search: semantic matches found (synonyms, related concepts)
- [ ] Hybrid search: outperforms keyword-only in 80%+ of test queries
- [ ] Metadata filters: no false positives, correct filtering

**Performance:**
- [ ] Query latency: <500ms for top-10 results
- [ ] Batch indexing: 10,000 documents in <5 minutes
- [ ] No timeouts or quota errors

**Grounding:**
- [ ] Every result has source_url
- [ ] Every result has relevant metadata
- [ ] Orchestrator can compose grounded answers with references

---

## Dependencies

- Fabric ingestion complete (data available to index)
- Azure AI Search service provisioned (Standard SKU minimum)
- Azure OpenAI embeddings API accessible
- Foundry orchestrator design finalized (knows how to call retrieval API)

---

## Implementation Sequence

1. **Phase 1:** Create indexing scripts (Python) to populate all three indexes from Fabric tables
2. **Phase 2:** Implement search API (FastAPI endpoint or Azure Functions) with hybrid search
3. **Phase 3:** Test search quality with sample queries (manually and automated)
4. **Phase 4:** Connect Foundry orchestrator to search API
5. **Phase 5:** End-to-end validation (user query → retrieval → orchestrator answer)

---

## Open Questions / Future Decisions

1. **Personalization:** Should results be boosted for the user's team/category? (Deferred to v2)
2. **Real-time indexing:** Stream updates from Fabric vs. daily batch? (Daily batch for POC)
3. **Semantic reranking:** Use cross-encoder for second-pass ranking? (Deferred to v2)
4. **Entity extraction:** Extract root cause, affected service, and index separately? (Deferred to v2)
5. **Multi-language:** Support queries in multiple languages? (English-only for POC)

---

## Document Links

- **Design Doc:** docs/RETRIEVAL_DESIGN.md
- **Related Decisions:** None yet
- **Related Prompts:** SQUAD_PROMPTS.md > Prompt 6

---

**Stakeholders:** Foundry specialist (@TBD), Fabric data modeler (@TBD)  
**Review Status:** ⏳ Pending team review  
**Decision Owner:** Jayne, Search/Retrieval Specialist

---

## Next Action

Team review and approval → Implementation begins with Phase 1 indexing scripts.


---

# Kaylee API design inbox

## Proposed implementation choices

- Use FastAPI with the Python standard-library `sqlite3` driver so the mock connector stays lightweight and easy to run locally or in a small container.
- Initialize schema and seed data at startup through `mock-servicenow-api\app\database.py`, with reseeding controlled by environment variables for predictable demos.
- Keep attachments, images, and documents in separate tables instead of a single polymorphic asset table so downstream Fabric ingestion can land them into separate curated tables without extra transformation.
- Model incident relationships explicitly through `incident_kb_links` and `incident_change_links`, and return those related records from `GET /incidents/{incident_id}` for a single denormalized retrieval path.
- Store both HTML-like source fields and cleaned text fields for incidents, notes, and KB articles to support structured ingestion plus search and retrieval scenarios.


---

# Mal Architecture Plan Decision

Date: 2026-06-17T14:52:27-04:00
Requested by: @kkonjuramicrosoft

## Summary

The Autoliv ServiceNow to Microsoft Fabric POC should be delivered as a three-path architecture:

1. **Structured path:** curated Fabric tables -> semantic model -> Fabric Data Agent
2. **Unstructured path:** cleaned KB/work-note/resolution text -> search/vector retrieval
3. **Reference path:** attachment/document/image metadata -> separate retrieval/tool path

## Key Decisions

1. The SQLite-backed mock ServiceNow API remains outside Fabric and exists only as the demo source-system stand-in.
2. Azure Container Apps is the required shared hosting layer for the mock API because Fabric must ingest from a public HTTPS endpoint.
3. Fabric becomes the authoritative demo data layer after ingestion; raw source data should not be queried directly by end-user agents.
4. The ontology stays intentionally scoped and is built from curated semantic/business entities rather than raw landing tables.
5. The minimum viable demo prioritizes incident-resolution scenarios, grounded references, and deployable Fabric assets over production hardening.

## Minimum Viable Demo Scope

- Incidents, users, groups, categories, changes, SLAs
- KB articles, work notes, resolution notes
- Attachment/document/image metadata and URLs
- Fabric ingestion, curated tables, semantic model, Fabric Data Agent
- Retrieval/index design and Foundry orchestration contract

## Watchouts

- Do not collapse the design into one agent.
- Do not force unstructured content into only the Fabric Data Agent.
- Do not blur the line between mocked SQLite source behavior and target production ServiceNow ingestion.
- Do not leave semantic model or Data Agent outcomes as concept-only artifacts.


---

# River Orchestration Design Decision

Date: 2026-06-17T14:52:27-04:00

## Decision

Adopt a multi-agent, multi-system Foundry orchestration pattern for the POC:

1. A Foundry orchestrator agent handles intent detection, tool routing, evidence fusion, and final grounded response generation.
2. A deployed Fabric Data Agent remains the authoritative path for structured ticket, SLA, priority, category, backlog, and semantic-model questions.
3. Search/vector retrieval remains the authoritative path for KB articles, work notes, resolution notes, cleaned HTML content, and similar historical tickets.
4. A separate document/image/attachment tool path remains responsible for screenshots, logs, scripts, document summaries, attachment metadata, and URLs.

## Rationale

- This follows the README meeting direction to avoid one monolithic agent over all data.
- It preserves clean system boundaries between structured analytics, unstructured retrieval, and non-tabular asset access.
- It supports grounded suggested resolutions by combining evidence instead of overloading a single subsystem.

## Consequences

- The orchestrator must maintain routing rules and a normalized citation format across tool results.
- Recommendation-style answers will often require multiple tool calls before synthesis.
- Human review remains mandatory for suggested resolutions and any low-confidence response.

## Design Counts

- Agent count: 2
- Tool count: 3
- Scenario count: 4


---

# Wash deployment configuration decision

Date: 2026-06-17T15:01:54.176-04:00

## Decision

- Package the mock ServiceNow API as a multi-stage Python container image that includes the seeded SQLite database at build time.
- Deploy the image to Azure Container Apps behind external HTTPS ingress on port `8000`.
- Use Azure Container Registry as the image registry and build/push with `az acr build` from the deployment scripts.
- Keep deployment values in repository-root `.env` and document CI/CD secrets separately from committed files.
- Force `SERVICENOW_RESEED_ON_STARTUP=true` during ACA deployments so generated mock asset URLs use the live ACA hostname.

## Rationale

- Bundling the SQLite file satisfies the POC requirement to ship a demo-ready source system without extra storage dependencies.
- Using ACA with external ingress provides the public HTTPS endpoint Microsoft Fabric needs for ingestion.
- Reseeding on ACA startup keeps demo URLs stable and correct even though ACA filesystem state is ephemeral between revisions.

## Consequences

- The demo dataset is deterministic but not durable; redeployments and restarts can reset it.
- ACR admin credentials are enabled during deployment for simple image pulls in this POC; production hardening should move to managed identity-based pulls.
- If write persistence becomes important, the SQLite file should move to durable storage or be replaced with a managed database service.


---

# Decision: Validation Plan Architecture

**Date:** 2026-06-17  
**Author:** Zoe (Testing & Validation Specialist)  
**Status:** Proposed for Review  

## Decision

Created a comprehensive validation plan (docs/VALIDATION_PLAN.md) that serves as the single source of truth for POC validation, demo preparation, and quality assurance.

## Rationale

1. **All-in-One Framework:** The validation plan covers all 14 required validation areas from Prompt 8, eliminating the need for scattered test documents.

2. **Executable Checklist:** The smoke test checklist is designed for quick pass/fail validation before demos. Each test is specific, includes expected output, and can be run by any team member.

3. **Demo-Ready Narrative:** The demo script provides a 15-20 minute customer-facing narrative with three real scenarios (structured query, unstructured search, multi-agent orchestration). This ensures consistent storytelling and reduces demo improvisation.

4. **Sample Questions Cover Spectrum:** Seven test questions cover:
   - Structured queries (Fabric semantic model)
   - Unstructured search (KB articles, work notes)
   - Attachment retrieval (metadata and documents)
   - Multi-step orchestration (Foundry combining all sources)
   - Ontology traversal (semantic relationships)

5. **Transparency on Limitations:** Documenting 14 known limitations upfront builds trust with stakeholders and sets realistic expectations. This prevents "why doesn't it do X?" questions after demo.

6. **Reusable for Multiple Demos:** Plan can be used for internal reviews, customer-facing presentations, and go/no-go decisions.

## What the Plan Does NOT Do

- Does not implement tests; specifies test steps to be executed by team members
- Does not replace continuous integration or automated testing; is a pre-demo validation gate
- Does not address production readiness; is scoped to POC validation only

## Next Steps

1. **Team Review:** All agents should review the validation plan and propose amendments.
2. **Dry Run:** Run the smoke test checklist (Part 1) once all services are deployed to validate feasibility.
3. **Demo Rehearsal:** Zoe should rehearse the demo script with the team 2 days before customer demo.
4. **Day-of Checklist:** Use the "Validation Checklist for Demo Day" (Part 6) as the pre-demo gate.

## Decision Owners

- **Primary:** Zoe (Testing/Validation)
- **Approval:** Lead Architect (confirms alignment with architecture)
- **Execution:** All team members (follow checklist during validation)

