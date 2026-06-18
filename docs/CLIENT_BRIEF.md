# Autoliv ServiceNow to Microsoft Fabric POC
## Client Brief & Demo Documentation

**Prepared:** June 17, 2026  
**Project:** Autoliv ServiceNow to Microsoft Fabric Proof of Concept  
**Audience:** Autoliv business and technical stakeholders  

---

## Executive Summary

This proof of concept demonstrates how Autoliv's ServiceNow operational data can be transformed into an intelligent, AI-ready architecture using Microsoft Fabric and Foundry. Rather than simply connecting to ServiceNow, this POC showcases how to **shape structured and unstructured support data** so that AI can answer operational questions, find similar historical tickets, retrieve relevant knowledge articles and documents, and help IT support teams resolve issues faster.

The POC deploys real data assets into Microsoft Fabric—a Lakehouse, curated tables, a semantic model, and a Fabric Data Agent—paired with search/vector retrieval and document/image tooling, all orchestrated by a Foundry agent. This multi-agent architecture enables IT support staff to ask business-meaningful questions and receive grounded, referenced answers in seconds.

The architecture separates concerns by design: structured ticket analytics flow through the Fabric Data Agent; unstructured knowledge articles and historical notes flow through search and vector retrieval; and attachments, logs, documents, and images are handled through dedicated document/image tools. This layered approach ensures each component excels at its specific task while the Foundry orchestrator intelligently routes questions to the right tool and synthesizes results.

---

## Business Problem & Desired Outcome

### Current State
Autoliv's IT support teams resolve ServiceNow tickets daily using a combination of manual search, historical recall, and broad document repositories. Finding similar historical tickets, retrieving relevant knowledge articles, and composing resolution steps is time-consuming and inconsistent, leading to longer mean-time-to-resolution (MTTR) and ticket rework.

### Desired Outcome
Enable Autoliv's IT support staff to resolve tickets **faster and more consistently** by:
- Instantly finding similar historical tickets and understanding how they were resolved
- Automatically retrieving relevant knowledge articles, logs, scripts, and attachments
- Receiving AI-generated suggested resolutions grounded in historical data and references
- Reducing mean-time-to-resolution through intelligent recommendation and retrieval
- Building organizational knowledge by capturing and reusing successful resolution patterns

### Target Users
**Phase 1 (POC):** Internal IT and support staff resolving ServiceNow tickets.  
**Phase 2 (Future):** End-user self-service, where employees can open tickets and receive AI-assisted guidance with human-in-the-loop review.

---

## Current-State vs Target-State Architecture

### Current State: Manual, Siloed Data
```
ServiceNow CMDB / Incidents
     ↓
IT Staff Manual Search
     ├─→ Ticket database
     ├─→ KB articles (separate system or search)
     ├─→ Attachments/logs (manual download)
     └─→ Spreadsheets and tribal knowledge

Result: High MTTR, inconsistent resolution, knowledge loss
```

### Target State: Unified, AI-Ready Architecture
```
ServiceNow API
     ↓
Microsoft Fabric Lakehouse
     ├─→ Curated Semantic Model (for structured analytics)
     ├─→ Vector Index (for unstructured KB, notes, descriptions)
     └─→ Document/Image Index (for attachments, logs, screenshots)
     ↓
Multi-Agent Orchestration
     ├─→ Fabric Data Agent (structured questions)
     ├─→ Search/Vector Retrieval (KB articles, historical notes)
     └─→ Document/Image Tools (attachments, logs, scripts)
     ↓
IT Support User Experience (unified intelligence)

Result: Low MTTR, consistent resolution, captured knowledge
```

---

## POC Architecture Explanation

The POC follows a **modular, multi-agent design** deployed into real Microsoft Fabric infrastructure:

### Data Flow
1. **Mock ServiceNow API** (Azure Container Apps): A containerized, HTTPS-accessible API backed by SQLite that simulates ServiceNow data—incidents, users, KB articles, work notes, attachments, changes, and SLAs.
   - *Note: SQLite is a POC mock. Production uses direct ServiceNow API ingestion into Fabric.*

2. **Fabric Ingestion** (Dataflow Gen2 or Fabric Pipelines): Automatically calls the mock API, lands raw data into the Fabric Lakehouse or Warehouse, and orchestrates transformations.

3. **Fabric Lakehouse/Warehouse** (Real Fabric Storage): Hosts all ingested and curated data. This is the single source of truth for the demo and production path.

4. **Transformation & Curation** (Fabric Notebooks/Spark): Normalizes raw API data into clean, queryable tables:
   - Structured: incidents, users, groups, categories, changes, SLAs
   - Semi-structured: cleaned text from HTML fields (KB articles, work notes, resolution notes)
   - Unstructured metadata: attachment references, images, document summaries, external links

5. **Fabric Semantic Model** (Power BI / Fabric Semantic Model): Built on top of curated Fabric tables, defining dimensions, measures, and relationships for operational analytics.

6. **Ontology Layer** (Knowledge Graph / Business Entity Model): A scoped, relationship-based representation of tickets, users, categories, knowledge articles, and changes—derives from the semantic model, not raw tables.

### Tool Layers
```
┌─────────────────────────────────────────────────────┐
│         Foundry Orchestrator Agent                   │
│  (Routes intent, selects tools, composes answers)   │
└──────────────┬──────────────────────────────────────┘
               │
       ┌───────┼───────┬──────────────────┐
       ▼       ▼       ▼                  ▼
  ┌─────────┐┌──────────┐┌──────────────┐┌─────────────┐
  │ Fabric  ││ Search / ││ Document /   ││ Ontology    │
  │ Data    ││ Vector   ││ Image        ││ / Scoped    │
  │ Agent   ││Retrieval ││ Tools        ││ Relationships
  │(Struct.)││(Unstruc)││(References) ││             │
  └─────────┘└──────────┘└──────────────┘└─────────────┘
```

---

## Data Model Overview

The POC data model spans structured and unstructured content, designed for both semantic analytics and AI retrieval:

### Structured Core Tables
| Entity | Purpose | Key Fields |
|--------|---------|-----------|
| **Incidents** | Support tickets | incident_id, number, short_description, description, state, priority, category, assigned_to_group, opened_at, resolved_at, resolution_code |
| **Users** | Support staff & requesters | user_id, name, email, department, manager_id, active |
| **Assignment Groups** | Support teams | group_id, name, support_tier, business_service |
| **Categories** | Ticket classification | category_id, category, subcategory, business_service |
| **Change Requests** | Related infrastructure changes | change_id, state, risk, impacted_service, planned_start, planned_end |
| **SLAs** | Service level agreements | sla_id, incident_id, sla_name, target_duration, elapsed, breached, due_at |

### Semi-Structured & Unstructured Content
| Content Type | Purpose | Processing |
|--------------|---------|-----------|
| **KB Articles** | Knowledge base HTML | Cleaned to searchable text, indexed for vector retrieval |
| **Work Notes** | Internal troubleshooting history | HTML/text → cleaned, chronological narrative |
| **Resolution Notes** | Final remediation steps | Cleaned text, extracted patterns and best practices |
| **Comments** | Customer-facing communication | Preserved for context and retrieval |
| **Attachment Metadata** | References to screenshots, logs, scripts | Extracted descriptions, links, file types |
| **Images & Documents** | Related visual/document references | Summaries, captions, related KB mappings |

### Relationship Tables
| Relationship | Purpose |
|--------------|---------|
| Incident → Change | Links tickets to infrastructure changes |
| Incident → KB Article | Cross-references knowledge articles |
| Incident → Attachment/Image | Links supporting files and references |
| Incident → Historical Similar | Similarity scoring and grouping |
| Category → KB Article | Maps knowledge to issue classification |

---

## Semantic Model & Ontology Explanation

### Semantic Model
The Fabric semantic model is a **business-layer abstraction** built on curated Lakehouse tables, enabling operational analytics:

**Dimensions:**
- Time (opened, resolved, updated dates)
- User (requester, assigned agent, support manager)
- Support Group & Department
- Category / Subcategory / Business Service
- Ticket State (new, in-progress, resolved, closed)
- Priority & Impact / Urgency
- Knowledge Article
- Change Request

**Measures:**
- Ticket Volume (open, closed, total by period)
- Average Resolution Time
- SLA Breach Count & Percentage
- Reopen Rate (closed tickets reopened within 30 days)
- Backlog by Priority (aging open tickets)
- Category Trends (volume, resolution rate, quality)
- KB Article Reuse Count (how often KB articles solve problems)

**Purpose:** Enable business questions like:
- "How many high-priority tickets are overdue?"
- "What is the average time to resolve incidents in the Database category?"
- "Which KB articles are most effective for our top issues?"
- "How do we perform against SLAs by support group?"

### Ontology Layer
The ontology is a **scoped, relationship-centric model** derived from the semantic model, designed for AI grounding and entity traversal:

**Core Entities:**
- **Ticket** – specific incident/problem
- **User** – requester, assignee, manager
- **Support Group** – team that resolves tickets
- **Category** – issue classification
- **Knowledge Article** – solution reference
- **Attachment/Document/Image** – supporting references
- **Change Request** – related infrastructure change
- **Resolution Pattern** – common fix types

**Core Relationships:**
- Ticket _was opened by_ User  
- Ticket _is assigned to_ Support Group  
- Ticket _belongs to_ Category  
- Ticket _impacts_ Business Service  
- Ticket _was resolved using_ Resolution Pattern  
- Ticket _references_ Knowledge Article  
- Ticket _has attachment_ Document/Image/Log  
- Ticket _relates to_ Change Request  
- Knowledge Article _applies to_ Category  

**Scoping for POC:** The ontology is intentionally small and focused on ticket resolution patterns. If it grows beyond ~20 entities, split into multiple sub-models (e.g., "ticket resolution," "change management," "KB categorization") rather than creating one oversized graph.

**Purpose:** Enable AI agents to:
- Traverse from a ticket to similar historical tickets (via Category, Resolution Pattern, or similarity)
- Find relevant knowledge articles (via Category or Content similarity)
- Identify supporting documents and attachments (direct relationships)
- Compose grounded answers with entity references and citations

---

## Multi-Agent Architecture Explanation

The POC uses a **multi-agent, task-specialized architecture** rather than a single monolithic agent:

### Agent Roles & Responsibilities

#### 1. Foundry Orchestrator Agent
**Role:** Router, composer, and final response handler  
**Responsibility:**
- Understands user intent and question type
- Routes queries to appropriate specialists (Data Agent, Retrieval, Document Tools)
- Combines partial results and synthesizes final, grounded answers
- Manages confidence, cites sources, escalates uncertain queries
- Handles complex questions that require multiple tools

**Example Workflow:**
```
User: "What's similar to ticket #4521 that we've resolved?"
Orchestrator:
  1. Parses intent: "find similar historical tickets + resolutions"
  2. Routes to Fabric Data Agent: "What category and priority matches ticket #4521?"
  3. Routes to Search/Vector: "Find other resolved tickets in that category"
  4. Routes to Document Tools: "Any attached logs or scripts we used?"
  5. Composes: "We found 3 similar tickets (links), all in the Database category.
     Here's how they were resolved (grounded steps). These scripts were attached (links)."
```

#### 2. Fabric Data Agent
**Role:** Structured data specialist  
**Responsibility:**
- Answers questions about incidents, users, groups, priorities, SLAs, categories
- Aggregates metrics (ticket volume, resolution time, SLA breaches)
- Supports semantic model measures and relationships
- Works over curated Fabric tables and the deployed semantic model
- Provides precise, queryable results

**Example Queries:**
- "How many open high-priority incidents are assigned to Database Support?"
- "Which categories have the highest SLA breach rate this month?"
- "What's our average resolution time for Networking tickets?"

#### 3. Search / Vector Retrieval
**Role:** Unstructured content specialist  
**Responsibility:**
- Retrieves knowledge articles, work notes, resolution notes
- Returns semantically similar content (not just keyword matches)
- Surfaces cleaned text and relevant passages
- Supports queries about "how we've solved this before"
- Returns references (KB article IDs, links)

**Example Queries:**
- "What KB articles apply to password reset issues?"
- "Show me historical work notes from similar tickets"
- "Find common resolution patterns for this error message"

#### 4. Document / Image / Attachment Tools
**Role:** Reference and supporting content specialist  
**Responsibility:**
- Retrieves attachment metadata and descriptions
- Surfaces logs, scripts, diagnostic outputs, and screenshots
- Provides document summaries and external links
- Returns attachment URLs and metadata
- Enables "show me the log file" and "find the troubleshooting script" patterns

**Example Queries:**
- "What logs or diagnostic scripts are attached to resolved Database tickets?"
- "Find the screenshot that shows this error"
- "Where's the SQL script we used last time for this issue?"

### Why Multi-Agent?
1. **Specialization:** Each agent excels at its specific domain (structure, semantics, unstructured content, references)
2. **Maintainability:** Updating KB retrieval logic doesn't risk breaking structured queries
3. **Performance:** Tools are optimized for their content type (structured query engines are fast; vector retrieval is accurate for semantics)
4. **Extensibility:** Adding new capabilities (e.g., change management, incident prioritization) doesn't require rewriting the whole system
5. **Transparency:** IT staff can understand why a tool was called and what it found

---

## Demo Flow

### Setup & Intro (2 minutes)
1. **Show the mock ServiceNow API**: Display the containerized API running in Azure Container Apps with HTTPS ingress. Explain that SQLite is a POC mock; production uses direct ServiceNow API ingestion.
2. **Show the API data**: Call a sample endpoint (e.g., `/incidents`, `/kb-articles`) to show realistic ServiceNow-style data: incidents, users, KB articles, attachments, work notes.

### Data in Fabric (3 minutes)
3. **Show Fabric Lakehouse**: Display raw ingested data (incidents, users, KB articles) in Lakehouse tables.
4. **Show curated tables**: Display transformed tables—cleaned KB articles (HTML → text), normalized incident relationships, attachment metadata extracts.
5. **Show cleaned text example**: Display a KB article that has been converted from HTML to clean searchable text, preserving links and structure.

### Semantic Model & Ontology (2 minutes)
6. **Show Fabric semantic model**: Display the Power BI or Fabric semantic model with dimensions and measures—show a sample report: "Tickets by Category," "Open Backlog by Priority," "SLA Performance."
7. **Show ontology layer**: Display the ontology/knowledge graph structure—entities (Ticket, User, Category, KB) and relationships.

### Fabric Data Agent (3 minutes)
8. **Ask a structured question**: "How many high-priority incidents are currently open, and what's the average time to resolve them?"
   - **Show the Fabric Data Agent response:** Grounded in the semantic model, includes structured numbers, links to affected categories.

### Search / Vector Retrieval (3 minutes)
9. **Ask a "similar tickets" question**: "What's similar to ticket #4521 that we've resolved, and how?"
   - **Show retrieval results:** Historical tickets with similar categories, work notes, and resolution steps.

10. **Ask a KB / reference question**: "What KB articles and scripts apply to Database connectivity issues?"
    - **Show retrieval results:** Ranked KB articles with cleaned text passages, attached script URLs, and relevance scores.

### Document / Image Tools (2 minutes)
11. **Ask a "show me the evidence" question**: "What logs or screenshots are attached to Database tickets we've resolved recently?"
    - **Show results:** Attachment metadata, descriptions, image captions, document summaries, and download links.

### Foundry Orchestrator Synthesis (3 minutes)
12. **Ask a complex question that requires multiple tools**: "I have a ticket similar to #4521. What's the most likely resolution, and where can I find the supporting docs?"
    - **Show the orchestrator combining results:**
      - Structured: Related tickets and their resolution codes (from Fabric Data Agent)
      - Unstructured: Relevant KB articles and work notes (from Search/Vector Retrieval)
      - References: Attached logs and scripts (from Document Tools)
    - **Show the final synthesized answer:** "This looks like a Database connectivity issue. The most common resolution is [steps]. Here's the KB article [link], similar resolved tickets [links], and the diagnostic script [link]."

### Production Path & Next Steps (2 minutes)
13. **Discuss production direction:** Explain the path from mock SQLite to production ServiceNow API, Fabric deployment, and ongoing optimization.
14. **Address open questions** from stakeholders.
15. **Next steps:** Pilot with IT support team, refine prompts and retrieval tuning, expand to end-user self-service.

---

## Open Questions

As we refine the POC and move toward production, these questions should be addressed:

### Data & Integration
1. **ServiceNow API Authentication:** Will we use OAuth 2.0, API tokens, or service account credentials? How frequently should we sync (real-time, daily, on-demand)?
2. **Data Scope:** Should we ingest all ServiceNow tables, or start with Incidents + related tables (Users, Categories, Changes, SLAs)? How deep should we go into historical data?
3. **Fabric Storage Strategy:** Should we use a Lakehouse (for flexibility) or Warehouse (for analytics performance)? Do we need both for different workloads?

### Semantic Model & Ontology
4. **Semantic Model Complexity:** How detailed should the semantic model be? Are there Autoliv-specific metrics (e.g., business service dependencies, cost centers, impact tiers) that should be included?
5. **Ontology Scope:** Are there Autoliv business entities or relationships beyond tickets, users, and KB that should be modeled (e.g., supply chain impact, manufacturing systems)?
6. **Custom Categorization:** Should we introduce Autoliv-specific incident categories, resolution codes, or patterns not in standard ServiceNow?

### Agent & Retrieval Design
7. **KB Retrieval Quality:** Should we index all KB articles, or curate a subset for the POC? How do we score relevance (keyword, semantic similarity, citation frequency)?
8. **Historical Similarity:** How should we define "similar tickets"? By category, priority, error message similarity, or a hybrid score?
9. **Attachment Processing:** How detailed should attachment extraction be? Should we OCR images, parse logs, and extract structured data from scripts?

### User Experience & Deployment
10. **User Feedback Loop:** How will IT support staff refine results, rate answer quality, and provide feedback for model improvement?
11. **Confidence & Escalation:** At what confidence threshold should the orchestrator offer human review or escalation?
12. **Fabric Data Agent Integration:** Should the Fabric Data Agent be exposed as a separate tool, or only through the Foundry orchestrator?
13. **Performance & Latency:** Are there latency requirements for response time? Should we cache common queries?

### Governance & Rollout
14. **Pilot Scope:** Which support group or business service should pilot first?
15. **Data Privacy:** Are there Autoliv data privacy or compliance constraints (e.g., PII redaction, data residency)?
16. **Access Control:** Should different support tiers (Tier 1, 2, 3) have different agent/retrieval access?

---

## Next-Step Recommendations

### Immediate (Weeks 1–2)
1. **Validate the POC demo**: Run the full demo with Autoliv technical stakeholders to confirm data, architecture, and value proposition align with expectations.
2. **Identify pilot group**: Select an internal IT support group (e.g., Database Support, Network Support) to participate in a 2–4 week pilot.
3. **Refine semantic model**: Work with pilot group to identify any missing dimensions, measures, or categories specific to Autoliv.

### Short-term (Weeks 3–6)
4. **Pilot with IT support staff**: Deploy the POC to pilot users with a lightweight interface (e.g., Teams bot, web chat, Copilot plugin).
5. **Collect feedback**: Document question types, answer quality ratings, and suggestions for improvement.
6. **Tune retrieval & prompts**: Refine KB retrieval relevance, semantic similarity, and orchestrator prompts based on pilot feedback.
7. **Measure MTTR improvement**: Compare resolution times and quality before and after POC use.

### Medium-term (Weeks 7–12)
8. **Plan production ingestion**: Design real ServiceNow API integration (authentication, sync frequency, data scope, error handling).
9. **Scale semantic model**: Expand the semantic model to cover additional Autoliv business services and operational needs.
10. **Extend retrieval**: Add document indexing (internal runbooks, Autoliv-specific troubleshooting guides, vendor documentation).
11. **Automation & SLA impact**: Measure and demonstrate MTTR improvement, SLA compliance gains, and knowledge retention.

### Long-term (Months 4–6)
12. **Expand to end-user self-service**: Design and pilot an end-user-facing interface (self-service ticket creation, guided troubleshooting, human-in-the-loop review).
13. **Multi-system integration**: Consider extending the architecture to other Autoliv systems (HR, Finance, Supply Chain) as similar use cases emerge.
14. **Productionization**: Move from POC infrastructure to production-grade hosting, monitoring, disaster recovery, and compliance.

### Key Success Metrics
- **MTTR Reduction:** 20–30% faster ticket resolution
- **Agent Adoption:** 70%+ of pilot group using the tool within 2 weeks
- **Answer Quality:** 80%+ of AI-generated suggestions rated as "helpful or better" by support staff
- **KB Reuse:** Increase in KB article citations and reuse within support teams
- **SLA Improvement:** Measurable improvement in SLA compliance during pilot

---

## Conclusion

This POC demonstrates that Autoliv's support operations can be transformed by **shaping data for intelligence**: moving from siloed systems and manual search to a unified, AI-ready architecture in Microsoft Fabric. The value is not in the connector; it's in semantic modeling, intelligent retrieval, multi-agent orchestration, and knowledge capture.

By the end of the POC pilot, Autoliv's IT support teams should be able to resolve tickets faster, with more confidence, and with repeatable, grounded references to historical solutions, knowledge articles, and supporting documentation.

We're ready to begin the demo and pilot phase. Let's transform how Autoliv supports operations.

---

**Contact:** @kkonjuramicrosoft  
**Last Updated:** June 17, 2026
