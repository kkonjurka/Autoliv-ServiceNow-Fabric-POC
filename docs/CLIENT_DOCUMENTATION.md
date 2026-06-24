# Autoliv ServiceNow to Microsoft Fabric — Proof of Concept
## Client Documentation

**Prepared:** June 24, 2026
**Project:** Autoliv ServiceNow to Microsoft Fabric POC
**Audience:** Autoliv Business and Technical Stakeholders
**Prepared by:** Microsoft

---

## 1. Executive Summary

This proof of concept demonstrates how Autoliv's ServiceNow IT support data can be transformed into an intelligent, AI-ready architecture using Microsoft Fabric and Azure AI Foundry. Rather than simply connecting a pipeline, this POC shows what it takes to **shape, model, and orchestrate** support data so that AI can answer operational questions, surface similar historical tickets, retrieve relevant knowledge articles, and help support teams resolve issues faster. The POC deploys real Microsoft Fabric assets—a Lakehouse, curated Delta tables, a semantic model, an ontology, and a Fabric Data Agent—paired with Azure AI Search and an Azure AI Foundry orchestrator. The result is a working, end-to-end demonstration of AI-assisted ticket resolution grounded in Autoliv's own data patterns and resolution history.

---

## 2. Business Problem

Autoliv's IT support teams handle a high volume of ServiceNow incidents daily. Finding the right answer requires manually searching ticket history, digging through knowledge base articles stored in separate systems, and relying on the recall of experienced engineers. This process is:

- **Slow:** Support engineers spend significant time locating historical context before beginning resolution.
- **Inconsistent:** Resolution quality depends on who picks up the ticket and what they remember.
- **Knowledge-lossy:** Effective resolution patterns discovered in one ticket rarely make it into a findable, structured form for the next engineer.
- **Siloed:** Tickets, KB articles, work notes, logs, scripts, and attachments live in different places with no unified retrieval path.

The cumulative effect is elevated mean-time-to-resolution (MTTR), ticket rework, follow-up queues, and knowledge that exists only in the heads of senior staff.

---

## 3. Desired Outcome

The goal is to give Autoliv IT support users a single, AI-assisted interface that:

1. **Surfaces similar historical tickets** and how they were resolved, grounded in actual notes and resolution patterns.
2. **Answers structured operational questions** ("How many critical tickets are open for Network Support this week?") from live semantic data without writing SQL.
3. **Retrieves knowledge articles, work notes, and resolution documentation** relevant to the current issue.
4. **Provides access to supporting evidence**—attachments, logs, scripts, screenshots—through a dedicated asset retrieval path.
5. **Suggests a likely resolution path** grounded in historical evidence, with cited sources and a human-review checkpoint before any action is taken.

**Phase 1:** Internal IT support staff resolving open tickets.
**Phase 2:** End-user self-service, where employees receive AI-assisted guidance when opening or tracking their own tickets.

---

## 4. Current-State vs. Target-State Architecture

### Current State: Manual, Siloed Resolution

```
ServiceNow (Incidents, KB, Notes, Attachments)
     |
     ↓
IT Support Engineer
     ├── Manual search in ServiceNow ticket history
     ├── Browse KB articles (separate system or portal)
     ├── Download attachments/logs manually
     └── Rely on institutional memory and spreadsheets

Result: High MTTR · Inconsistent resolution · Knowledge loss
```

Key pain points:
- No unified view across tickets, articles, notes, and files
- No structured way to find "what worked last time for this type of issue"
- No SLA risk visibility without running manual reports
- Knowledge concentrated in experienced individuals, not in the system

### Target State: Unified, AI-Ready Architecture

```
ServiceNow API
     ↓
Microsoft Fabric Lakehouse (curated, governed data layer)
     ├── Semantic Model → structured analytics and backlog visibility
     ├── Ontology → entity relationships for intelligent traversal
     ├── Retrieval Index → KB articles, work notes, resolution narratives
     └── Asset Metadata → attachments, logs, screenshots, documents
     ↓
Azure AI Foundry Orchestrator
     ├── Fabric Data Agent  (structured ticket/SLA questions)
     ├── AI Search Retrieval (historical notes, KB articles)
     └── Asset Tool         (attachment metadata and file references)
     ↓
IT Support User Experience — grounded, cited, consistent answers

Result: Lower MTTR · Consistent resolution · Captured knowledge
```

---

## 5. POC Architecture Explanation

The POC follows a modular, multi-layer design deployed into real Microsoft Fabric and Azure infrastructure. Every component has a defined role and a clear production upgrade path.

### 5.1 Component Overview

| Layer | Component | What it does |
|---|---|---|
| **Source** | Mock ServiceNow API | Containerized Flask API backed by SQLite that simulates ServiceNow data contracts — incidents, users, groups, KB articles, work notes, SLAs, change requests, and attachment metadata |
| **Hosting** | Azure Container Apps | Provides public HTTPS access to the mock API so Microsoft Fabric can ingest from it during the POC |
| **Ingestion** | Fabric Lakehouse Notebooks | Notebook-based ingestion that pages through all API endpoints and lands raw JSON in the Lakehouse `Files/raw/` zone |
| **Curation** | Fabric Transform Notebooks | Normalize raw JSON into structured Delta tables; strip HTML from narrative fields to produce clean text for retrieval |
| **Semantic layer** | Fabric Semantic Model | Star-schema model with fact tables, dimensions, bridge tables, measures, and DAX definitions built over curated tables |
| **Ontology** | Fabric Ontology Notebook | Graph of nodes (Incident, User, Group, Category, KB Article, etc.) and typed edges (OPENED_BY, REFERENCES_KB, RESOLVED_BY_PATTERN, etc.) materialized as Delta tables |
| **Structured Q&A** | Fabric Data Agent | Points at the published semantic model; answers natural-language questions about ticket volume, SLA status, backlog, aging, and resolution patterns |
| **Unstructured retrieval** | Azure AI Search | Indexes the cleaned text corpus (KB articles, work notes, resolution notes, incident descriptions) for hybrid keyword + semantic similarity search |
| **Asset retrieval** | Asset Tool (Foundry) | Retrieves attachment metadata, document summaries, image descriptions, log/script references, and mock URLs for a given ticket |
| **Orchestration** | Azure AI Foundry Agent | Intent classification, tool routing, result fusion, grounding, citation assembly, and human-review flagging |

### 5.2 End-to-End Data Flow

```
1. Mock ServiceNow API (Azure Container Apps)
        ↓  HTTPS JSON
2. Fabric Ingest Notebooks → Raw landing zone (Files/raw/)
        ↓  Spark transform
3. Fabric Transform Notebooks → Curated Delta tables + retrieval_documents
        ↓
   ┌────────────────────────────────────────────────────────┐
   │                   Microsoft Fabric                     │
   │  • incidents • users • assignment_groups • categories  │
   │  • kb_articles • work_notes • resolution_notes • slas  │
   │  • change_requests • attachments • images • documents  │
   │  • ontology_nodes • ontology_edges                     │
   └────────────────────────────────────────────────────────┘
        ↓                     ↓                     ↓
4. Fabric Semantic Model   Retrieval corpus     Asset metadata
   (star schema + DAX)     (retrieval_documents) (attachment tables)
        ↓                     ↓                     ↓
5. Fabric Data Agent    Azure AI Search         Asset Tool
   (structured Q&A)     (hybrid retrieval)      (file references)
        ↓                     ↓                     ↓
6.         Azure AI Foundry Orchestrator
           (intent → route → fuse → cite → answer)
                         ↓
7.              IT Support User
```

### 5.3 POC Scope Boundaries

| Area | What the POC shows | What it intentionally defers |
|---|---|---|
| Source data | Realistic 32-incident, 8-KB-article mock dataset matching ServiceNow data shapes | Real-time ServiceNow API connectivity, OAuth, and change detection |
| Hosting | Shared public HTTPS endpoint on Azure Container Apps | Private networking, managed identity, enterprise-grade HA |
| Ingestion | Full notebook-based ingestion of all entity types | Scheduled incremental ingestion, CDC patterns |
| Fabric assets | Real Lakehouse, real semantic model, real Data Agent | Production data governance, retention policies, row-level security |
| Retrieval | Hybrid keyword + semantic search over cleaned text corpus | Full embedding pipeline at scale, access-controlled retrieval |
| Orchestration | Foundry agent with three-path routing and citation model | Policy controls, audit logging, feedback loops |

---

## 6. Data Model Overview

The curated Fabric Lakehouse contains **15 structured Delta tables** and **1 unified retrieval corpus**, organized into three logical zones.

### 6.1 Structured Tables

#### Core Fact Tables

| Table | Grain | Purpose |
|---|---|---|
| `incidents` | One row per incident | Central ticket fact — state, priority, impact, urgency, timestamps, follow-up flags, cleaned description and resolution text |
| `slas` | One row per SLA record per incident | SLA breach detection and elapsed/target analysis |

#### Dimension Tables

| Table | Purpose |
|---|---|
| `users` | Shared dimension for requesters, assignees, and note authors |
| `assignment_groups` | Support team ownership and escalation metadata |
| `categories` | Category/subcategory hierarchy shared by incidents and KB articles |
| `kb_articles` | KB article metadata with cleaned content for retrieval and reuse reporting |
| `change_requests` | Change record metadata for change-impact analysis |

#### Relationship / Note Tables

| Table | Purpose |
|---|---|
| `work_notes` | Timeline of investigation activity per incident |
| `resolution_notes` | Resolution-specific narrative attached to closed tickets |
| `incident_changes` | Bridge between incidents and change requests |
| `incident_kb_links` | Bridge between incidents and KB articles used during resolution |

#### Asset Metadata Tables

| Table | Purpose |
|---|---|
| `attachments` | File attachment metadata — name, type, size, mock URL |
| `images` | Screenshot and image metadata — name, dimensions, description |
| `documents` | Document metadata — name, type, summary, mock URL |
| `external_references` | Links to external evidence, vendor docs, and source systems |

### 6.2 Retrieval Corpus

| Table | Purpose |
|---|---|
| `retrieval_documents` | One clean-text row per indexable artifact (incident descriptions, resolution summaries, work notes, resolution notes, KB article content) with back-pointer IDs for grounding |

### 6.3 Key Relationships

```
incidents ──→ users            (requester, assignee)
incidents ──→ assignment_groups
incidents ──→ categories
incidents ──→ slas
incidents ──→ work_notes
incidents ──→ resolution_notes
incidents ──→ attachments / images / documents
incidents ──→ external_references
incidents ──M:M→ change_requests   (via incident_changes)
incidents ──M:M→ kb_articles       (via incident_kb_links)
kb_articles ──→ categories
retrieval_documents ──→ incidents / kb_articles  (grounding back-pointers)
```

---

## 7. Semantic Model and Ontology

### 7.1 The Semantic Model

The Fabric semantic model sits above the curated tables and provides a business-friendly, query-optimized layer that the Fabric Data Agent uses to answer structured questions without writing SQL.

**Shape:** Star schema centered on `FactTickets` and `FactSla`, with bridge tables for KB reuse, asset references, change linkage, and resolution patterns.

**Key dimensions:** `DimDate` (role-played for opened/resolved/updated), `DimUser` (role-played for requester/assignee), `DimAssignmentGroup`, `DimCategory`, `DimPriority`, `DimState`, `DimKnowledgeArticle`, `DimResolutionPattern`

**Key measures:**

| Measure | What it answers |
|---|---|
| Ticket Volume | How many tickets in any filter slice? |
| Open Ticket Count | How many tickets are still open? |
| Avg Resolution Time (Hours) | How long does it typically take to resolve? |
| SLA Breach Count | How many tickets missed their SLA target? |
| Reopen Rate | What fraction of resolved tickets were reopened? |
| Aging Open Tickets | Which tickets have been open the longest? |
| Resolution Pattern Frequency | Which fix patterns appear most often? |
| KB Article Reuse Count | Which articles are cited most in resolutions? |

**Example questions the semantic model answers:**
- "How many open tickets are currently assigned to Network Support, and what are the priority levels?"
- "What is the average resolution time for Database / SQL Performance incidents this month?"
- "Which business services have the highest SLA breach count over the last 30 days?"
- "Which KB articles are reused most often for critical or high-priority incidents?"

### 7.2 The Ontology

The ontology extends the semantic model into a **graph of business entities and their relationships**, stored as `ontology_nodes` and `ontology_edges` Delta tables. Where the semantic model answers *how many*, the ontology answers *how are things connected*.

**Node types:** Incident, User, AssignmentGroup, Category, BusinessService, KnowledgeArticle, Attachment, Document, Image, ChangeRequest, ResolutionPattern

**Key edge types:**

| Relationship | Meaning |
|---|---|
| `OPENED_BY` | Which user opened this ticket? |
| `ASSIGNED_TO` | Which group owns this ticket? |
| `BELONGS_TO_CATEGORY` | What topic does this ticket fall under? |
| `REFERENCES_KB` | Which KB articles were used to resolve this? |
| `RESOLVED_BY_PATTERN` | What canonical fix pattern was applied? |
| `RELATES_TO_CHANGE` | What change request is tied to this incident? |
| `HAS_ATTACHMENT / HAS_DOCUMENT / HAS_IMAGE` | What supporting evidence exists? |

**Example questions the ontology enables:**
- "Starting from this ticket, which KB articles, change requests, and supporting files are connected?"
- "Which other tickets were resolved by the same fix pattern and impacted the same service?"
- "For Network Support, which categories and services are most commonly linked through resolved tickets?"

### 7.3 Why Both Matter

The semantic model handles aggregation and analytics. The ontology handles traversal and relationship reasoning. Together, they give the Fabric Data Agent and Foundry orchestrator the context to answer both "show me the numbers" and "show me the connections."

---

## 8. Multi-Agent Architecture

### 8.1 Why Multi-Agent?

A single AI agent connected to all data sources produces brittle, unpredictable results. Different question types require different retrieval strategies:

- Structured questions (counts, SLAs, priorities) need SQL-backed semantic models, not free-text search.
- Narrative questions (how was this fixed, what does this KB article say) need text retrieval, not database aggregation.
- Asset questions (show me the log, find the screenshot) need metadata-aware file retrieval, not either of the above.

Mixing these in one agent leads to hallucinated aggregates, missed evidence, and inconsistent citations. The three-path design keeps each component doing what it does best.

### 8.2 Architecture

```
IT Support User
      |
      ↓
Azure AI Foundry Orchestrator
      |
      ├── Tool 1: query_fabric_data_agent
      │       → Fabric Data Agent
      │       → Fabric Semantic Model
      │       → Curated Delta tables
      │       Best for: counts, SLA, backlog, priorities, trends
      │
      ├── Tool 2: search_support_knowledge
      │       → Azure AI Search (hybrid retrieval)
      │       → retrieval_documents corpus
      │       → KB articles, work notes, resolution notes, similar tickets
      │       Best for: historical context, narrative resolution, KB lookup
      │
      └── Tool 3: get_ticket_assets
              → Asset metadata tables
              → Attachment / document / image paths
              → Mock URLs and file summaries
              Best for: logs, scripts, screenshots, document references
```

### 8.3 Routing Logic

| User asks about... | Primary tool | Secondary tool |
|---|---|---|
| Open tickets, backlog, SLA, priority, category counts, aging | Fabric Data Agent | — |
| Similar tickets, how was this fixed, work notes, resolution notes | AI Search | Fabric (for current state context) |
| KB articles, documented procedures, known issues | AI Search | Asset tool (for linked files) |
| Logs, scripts, screenshots, attachments, documents | Asset tool | AI Search (for context) |
| Suggested resolution with references | Fabric + AI Search | Asset tool (when evidence includes files) |

### 8.4 Answer Format

Every Foundry response follows a consistent structure:
1. **Direct answer** — the factual response
2. **Supporting evidence** — what data backs the answer
3. **References** — cited source IDs (ticket numbers, KB article IDs, asset URLs)
4. **Confidence / human review note** — how strong the evidence is, and whether a human should review before acting

No action is ever taken automatically. Every suggested resolution is framed as a recommendation for human review.

---

## 9. Open Questions for Autoliv

The following questions should be resolved to move from POC to pilot.

| # | Question | Why it matters |
|---|---|---|
| 1 | Which ServiceNow version and edition is Autoliv running? | API version, available fields, and connector options vary by edition |
| 2 | What authentication method is available for ServiceNow API access? | OAuth, basic auth, and service accounts have different integration paths in Fabric |
| 3 | What is the typical daily incident volume and total record history? | Determines ingestion cadence, Fabric capacity sizing, and index scale |
| 4 | Are there existing ServiceNow data models, field customizations, or naming standards we should align to? | Custom fields and extended tables may require schema mapping |
| 5 | Which KB article types and namespaces are in scope? | ServiceNow can have multiple KB instances with different access controls |
| 6 | What attachment types are most critical? (logs, scripts, screenshots, documents) | Determines which asset pipeline paths to prioritize |
| 7 | Is there an existing Fabric or Power BI environment, and what capacity tier? | Affects workspace placement, Direct Lake vs. import mode decisions |
| 8 | Are there data residency, compliance, or sensitivity labeling requirements? | May affect where data lands, who can query it, and what governance tooling is needed |
| 9 | Is there an existing CMDB or service catalog that should inform the business service dimension? | Currently proxied from category and group data; a real CMDB would improve accuracy |
| 10 | What is the intended first audience — all IT staff, a specific team, a pilot group? | Scopes access controls, role-based filtering, and rollout sequencing |

---

## 10. Next-Step Recommendations

### Phase 1 → Pilot: Validate with Real Data (4–8 weeks)

1. **Connect to real ServiceNow** — Replace the mock API with a read-only ServiceNow API connection. Validate that API field shapes match the curated schema. Map any custom fields.
2. **Ingest a scoped real dataset** — Pull 90–180 days of incident history from one or two support teams. Validate row counts, field completeness, and data quality.
3. **Refine the semantic model** — Align measures, dimensions, and business service mappings to Autoliv's actual support structure and terminology.
4. **Calibrate retrieval** — Index real KB articles and resolution notes; evaluate retrieval relevance with actual support engineers asking actual questions.
5. **Run user acceptance testing** — Have 2–3 support engineers use the Foundry agent on real tickets. Collect feedback on answer quality, citation accuracy, and missing capabilities.

### Phase 2 → Production: Harden and Scale (8–16 weeks)

1. **Incremental ingestion** — Move from full-refresh notebooks to scheduled incremental ingestion using Fabric Dataflow Gen2 or pipeline orchestration.
2. **Access control** — Apply row-level security on the semantic model, scoped retrieval indices, and role-based access in Foundry.
3. **Governance and lineage** — Activate Fabric data lineage, sensitivity labels, and audit logging.
4. **Feedback loop** — Capture agent interaction quality signals (thumbs up/down, escalations) to improve retrieval ranking and orchestrator routing over time.
5. **Expand scope** — Extend to additional ServiceNow modules (changes, problems, service requests) and Phase 2 end-user self-service scenarios.
6. **Production observability** — Add Foundry agent monitoring, latency dashboards, and alert thresholds for retrieval quality degradation.

### Key Messaging for Internal Champions

- The value of this architecture is not the connector — it is the **data shaping, semantic modeling, ontology, retrieval design, and orchestration** that turns raw ServiceNow data into grounded AI answers.
- Microsoft Fabric is not just a data store here — it is the **authoritative intelligence layer** that makes the AI agent trustworthy.
- The POC already deploys **real Fabric assets**: a real Lakehouse, a real semantic model, a real Fabric Data Agent. This is not a mockup of the end state — it is a working foundation.
- The SQLite database is a POC **convenience stand-in** for ServiceNow, not part of the target architecture. Everything built around it is designed for production ServiceNow ingestion.

---

*Live mock API: `https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io`*

*For technical questions, contact the Microsoft POC team.*
