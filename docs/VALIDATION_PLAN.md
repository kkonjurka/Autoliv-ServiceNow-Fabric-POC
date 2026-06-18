# Autoliv ServiceNow to Microsoft Fabric POC — Validation Plan

**Document Date:** 2026-06-17  
**Author:** Zoe (Testing & Validation Specialist)  
**Status:** Ready for Demo Validation  

---

## Executive Summary

This validation plan defines how we verify that the Autoliv ServiceNow to Microsoft Fabric POC meets business and technical requirements. The plan includes:

1. **Smoke test checklist** — quick pass/fail validation of all major components
2. **Demo script** — step-by-step show-and-tell narrative for stakeholders
3. **Sample test questions** — 7 representative questions covering structured, unstructured, and attachment scenarios
4. **Expected output criteria** — how to recognize a successful answer
5. **Known limitations** — what the POC does not do

This document ensures that all 14 validation areas (API, Azure hosting, Fabric ingestion, semantic model, agents, and retrieval) are tested before any customer-facing demo.

---

## Part 1: Smoke Test Checklist

Use this checklist to quickly validate that all major components are operational. Run tests in order; stop at first failure.

### **API & Azure Hosting Validation**

- [ ] **VA.1: Mock API returns realistic ServiceNow-style data**
  - **Test:** `curl https://<ACA_API_BASE_URL>/health`
  - **Expected:** HTTP 200, JSON response with `{ "status": "healthy", "timestamp": "..." }`
  - **Owner:** Validate before moving to next test

- [ ] **VA.2: Mock API is deployed to Azure Container Apps with external HTTPS ingress**
  - **Test:** Confirm ACA deployment in Azure Portal; check "Ingress" tab shows "External" and "HTTPS"
  - **Expected:** ACA is running, HTTPS endpoint is reachable from public internet
  - **Owner:** Deployment verification complete

- [ ] **VA.3: Health endpoint validates successfully from outside Azure Container Apps**
  - **Test:** `curl https://<ACA_API_BASE_URL>/health` from any external network
  - **Expected:** HTTP 200 response within 2 seconds
  - **Owner:** Network/ingress is working

- [ ] **VA.4: SQLite seed data includes all required domains**
  - **Test:** `curl https://<ACA_API_BASE_URL>/api/v1/incidents` (returns paginated incidents with links to users, groups, KB articles, notes, attachments)
  - **Expected:** JSON array with at least 1 incident; verify fields: id, summary, state, priority, category, assigned_group, requester, created_date, updated_date, work_notes, resolution_notes, attachments
  - **Owner:** Seed data is loaded

### **Fabric Ingestion Validation**

- [ ] **VA.5: Fabric ingestion calls the Azure Container Apps API endpoint**
  - **Test:** Monitor Fabric Dataflow Gen2 or pipeline run logs; confirm HTTP calls to `https://<ACA_API_BASE_URL>/api/v1/...`
  - **Expected:** No authentication errors; HTTP 200 responses; data rows flowing into Fabric
  - **Owner:** Fabric is connected to ACA API

- [ ] **VA.6: Data is ingested into a real Fabric Lakehouse or Warehouse**
  - **Test:** Open Fabric workspace > Lakehouse/Warehouse > verify tables: `stg_incidents`, `stg_users`, `stg_groups`, `stg_categories`, `stg_kb_articles`, `stg_work_notes`, `stg_resolution_notes`, `stg_changes`, `stg_slas`, `stg_attachments`
  - **Expected:** Tables exist with row counts > 0
  - **Owner:** Data has been persisted to Fabric storage

- [ ] **VA.7: Transformations produce curated Fabric tables**
  - **Test:** Query curated layer tables: `dim_incident`, `dim_user`, `dim_group`, `dim_category`, `fact_incident_ticket`, `fact_work_note`, `fact_attachment`
  - **Expected:** Tables exist; columns include cleaned text, relationships, and metadata; no NULL id fields
  - **Owner:** Transformation layer is deployed

### **Data Cleaning & Semantic Model Validation**

- [ ] **VA.8: HTML-like fields are converted to cleaned text**
  - **Test:** Query `fact_work_note` table; select a work note with HTML tags; compare `raw_text` vs. `cleaned_text`
  - **Expected:** `cleaned_text` has HTML tags removed, plain text readable, preserves meaning
  - **Owner:** Text transformation is working

- [ ] **VA.9: Deployed Fabric semantic model supports structured questions**
  - **Test:** Open Fabric workspace > Semantic Model > verify tables: `Incidents`, `Users`, `Groups`, `Categories`, `KB Articles`, `SLAs`
  - **Expected:** Model includes dimensions (date, user, group, category, priority, state) and measures (ticket volume, open count, average resolution time, SLA breach count)
  - **Owner:** Semantic model is deployed

### **Agent & Retrieval Validation**

- [ ] **VA.10: Ontology layer supports scoped entity relationship traversal**
  - **Test:** Review ontology node list; verify nodes for Ticket, User, Group, Category, KB Article, Attachment, Change Request
  - **Expected:** Ontology file or knowledge graph includes relationships: "Ticket opened by User", "Ticket assigned to Group", "Ticket references KB Article", "Ticket has Attachment"
  - **Owner:** Ontology design is documented

- [ ] **VA.11: Deployed Fabric Data Agent flow handles structured questions**
  - **Test:** Invoke Fabric Data Agent flow with query: "How many high-priority incidents are open?"
  - **Expected:** Agent returns numeric answer with reference to semantic model measures (e.g., "12 high-priority incidents are currently open")
  - **Owner:** Agent is deployed and functional

- [ ] **VA.12: Search/retrieval flow handles unstructured content**
  - **Test:** Query search index with keywords: "database connection error"
  - **Expected:** Returns work notes, KB articles, and resolution notes that mention "database connection error" with relevance scores
  - **Owner:** Retrieval index is built

- [ ] **VA.13: Document/image/attachment path returns relevant metadata and URLs**
  - **Test:** Query attachment tool with incident id; retrieve attachment list
  - **Expected:** Returns attachment metadata: filename, file type, size, incident id, created date; includes mock download URL
  - **Owner:** Attachment retrieval is working

- [ ] **VA.14: Foundry orchestrator returns grounded answers with references**
  - **Test:** Invoke Foundry orchestrator with multi-part question: "What tickets in the database had similar symptoms to my current issue, and what resolved them?"
  - **Expected:** Orchestrator combines Fabric Data Agent (for ticket list), search retrieval (for symptoms), and references sources (incident ids, KB article ids, work note excerpts)
  - **Owner:** Orchestrator integration is working

---

## Part 2: Demo Script

**Duration:** 15–20 minutes  
**Audience:** Stakeholders, customer, internal IT leadership  
**Setup Time:** 5 minutes (ensure all systems running, validate smoke test checklist passed)

### **Section 1: Context (2 minutes)**

**Narrator:** Zoe (Testing/Validation Specialist)

> "Today we're showing the Autoliv ServiceNow to Microsoft Fabric POC. The goal is to help IT support staff resolve tickets faster by finding historically similar tickets, related KB articles, documents, and other supporting references—all powered by an actual Microsoft Fabric semantic model and a multi-agent Foundry architecture.
>
> Here's what we've built:
> - A mock ServiceNow API running in Azure Container Apps
> - ServiceNow data ingested into Microsoft Fabric
> - A Fabric semantic model for structured ticket questions
> - A search index for unstructured KB articles and notes
> - A Foundry orchestrator that brings all these together
>
> Let me walk you through a real support scenario."

### **Section 2: The Scenario (1 minute)**

**Setup:**

Display the scenario on screen:

> **IT Support Ticket #INC-2847**  
> **Requester:** Jane Doe  
> **Title:** Database connection pooling timeouts on app server  
> **Description:** Application logs show "connection pool exhausted" errors. App has been stable for 6 months. No recent deployments.

**Narrator:**

> "One of our support engineers, Jane, has opened a ticket. She's seen this type of issue before, but she's not sure which ticket. Let's ask the system to help her find similar historical tickets and show her how they were resolved."

### **Section 3: Structured Query to Fabric Data Agent (3 minutes)**

**Live Demo:**

1. **Show:** Open Fabric workspace in browser. Navigate to Fabric Data Agent flow.
2. **Input:** Ask the question: "Show me all open incidents assigned to the Database Support group with priority P2 or higher, ordered by age."
3. **Expected Output:**
   - Agent queries the semantic model
   - Returns table: Incident ID, Summary, Priority, Created Date, Days Open
   - Shows 3–5 open tickets

**Narrator:**

> "The Fabric Data Agent just queried the semantic model and found all high-priority database-related tickets. Notice it pulled directly from our Fabric Lakehouse using the semantic model—no SQL needed. Jane can now see what else the Database Support group is juggling."

### **Section 4: Unstructured Search Across KB & Notes (3 minutes)**

**Live Demo:**

1. **Show:** Switch to search/retrieval interface (e.g., Azure AI Search or search flow).
2. **Input:** Ask the question: "Show me any KB articles or work notes about database connection pooling issues."
3. **Expected Output:**
   - Returns 2–3 KB articles with summaries
   - Returns 1–2 work notes from closed incidents
   - Each result shows source (KB article ID, incident ID, timestamp) and relevance score

**Narrator:**

> "Now the search layer kicks in. It's looking across all our KB articles and work notes for anything related to connection pooling. Notice that it's returning actual historical solutions—this work note here shows exactly how the database team fixed a similar issue 3 months ago."

### **Section 5: Attachment/Document Retrieval (2 minutes)**

**Live Demo:**

1. **Show:** Query attachment tool with an incident ID from the search results.
2. **Input:** Select one of the historical incidents and ask: "Show me any attachments or documents from this ticket."
3. **Expected Output:**
   - Returns list of attachments: filename, type (log file, screenshot, SQL script, PDF), created date
   - Includes mock download URLs
   - Shows which attachment was added by which user

**Narrator:**

> "Notice that the historical ticket had three attachments: a screenshot of the error, a SQL query used to diagnose the pool exhaustion, and the resolution script. Jane can reference any of these without leaving the support system."

### **Section 6: Foundry Orchestrator End-to-End (4 minutes)**

**Live Demo:**

1. **Show:** Switch to Foundry orchestrator interface (e.g., chat-like interface or agent flow).
2. **Input:** Ask a complex question:  
   **"We have an incident about database connection pooling timeouts. Find similar historical tickets, show me how they were resolved, and tell me which KB articles and documents might be useful."**
3. **Expected Output:**
   - Orchestrator invokes Fabric Data Agent to search structured ticket data
   - Orchestrator invokes search retrieval for KB articles and notes
   - Orchestrator invokes attachment tool for documents
   - Returns a composed answer:

   > **Suggested Resolution for INC-2847:**  
   > **Similar Historical Tickets:**  
   > - INC-2101 (2025-03-15): "Connection pool exhausted after config change" — Resolved in 4 hours by increasing pool size.  
   > - INC-2684 (2025-08-22): "Database connection timeouts" — Resolved in 2 hours by restarting the application server.  
   >
   > **Relevant KB Articles:**  
   > - KB-1042: "Database Connection Pool Sizing Best Practices"  
   > - KB-1089: "Troubleshooting Database Timeouts"  
   >
   > **Supporting Documents:**  
   > - [SQL diagnostic query.sql](link) — Run this to check pool status  
   > - [Connection pool config guide.pdf](link) — Configuration reference  
   >
   > **Recommended Next Steps:**  
   > 1. Check application pool size in config (see KB-1042)  
   > 2. Run the diagnostic SQL query provided  
   > 3. If pool is small, increase size and restart app server (see INC-2684 resolution)

**Narrator:**

> "This is the orchestrator in action. It's taking a complex, messy question and breaking it down into three specialized agents:
> 1. The Fabric Data Agent found similar historical tickets.
> 2. The search layer found relevant KB articles and notes.
> 3. The attachment tool found supporting documents.
>
> The orchestrator then composed all that into a grounded, actionable answer with references. Jane can now see a clear path to resolution, backed by historical data."

### **Section 7: Key Takeaway (1 minute)**

**Narrator:**

> "What we've shown today is an end-to-end AI-assisted ticketing system built on:
> - **Real data:** Actual Fabric Lakehouse and semantic model, not mock files.
> - **Multi-agent architecture:** Specialized agents for structured queries, unstructured search, and document retrieval—orchestrated by Foundry.
> - **Grounded answers:** Every suggestion is backed by a reference to historical tickets, KB articles, or documents.
> - **User-friendly:** Support staff don't need to know SQL or understand the backend; they just ask questions in natural language.
>
> Questions?"

---

## Part 3: Sample Test Questions

Use these questions to validate that the POC can handle various types of queries. Ask them in order after the smoke test checklist passes.

### **Question 1: Structured Ticket Query**

**Category:** Structured data, Fabric semantic model  
**Question:** "How many incidents are currently open and assigned to the Database Support group?"

**Expected Output:**
- Numeric answer: "12 incidents are currently open in the Database Support group."
- Source: Fabric semantic model
- Time to answer: < 2 seconds

**Success Criteria:**
- ✓ Correct count (verify manually in Fabric table)
- ✓ Correct filter (Database Support group)
- ✓ Correct state (open/not closed)

---

### **Question 2: Structured KPI/Measure**

**Category:** Structured data, Fabric semantic model measures  
**Question:** "What is the average time to resolve a P1 incident this month?"

**Expected Output:**
- Numeric answer: "Average resolution time for P1 incidents is 8.5 hours."
- Source: Fabric semantic model (fact table + date dimension)
- Time to answer: < 2 seconds

**Success Criteria:**
- ✓ Correct measure (average resolution time)
- ✓ Correct filter (P1 priority, current month)
- ✓ Matches manual calculation from seed data

---

### **Question 3: Unstructured Knowledge Search**

**Category:** Unstructured content, search/vector retrieval  
**Question:** "Show me KB articles about SSH certificate errors."

**Expected Output:**
- List of 2–4 KB articles with:
  - Title
  - Summary snippet (first 100 characters)
  - Source ID (KB-XXXX)
  - Relevance score (0.0–1.0)
- Time to answer: < 3 seconds

**Success Criteria:**
- ✓ Articles contain keyword "SSH" or "certificate"
- ✓ Relevance score is plausible (higher for more relevant articles)
- ✓ Return at least 1 result

---

### **Question 4: Unstructured Historical Similarity**

**Category:** Unstructured content, historical incident search  
**Question:** "Find tickets similar to: 'Service is down after a database migration.'"

**Expected Output:**
- List of 1–3 closed incidents with:
  - Incident ID
  - Summary
  - Similarity score
  - How it was resolved (work notes excerpt)
- Time to answer: < 3 seconds

**Success Criteria:**
- ✓ Results mention "database", "migration", or "down/outage"
- ✓ Similarity score is reasonable (0.7–1.0 for good matches)
- ✓ At least 1 result with resolution notes

---

### **Question 5: Attachment/Document Metadata**

**Category:** Attachment retrieval  
**Question:** "What attachments are on incident INC-1523?"

**Expected Output:**
- List of attachments with:
  - Filename
  - File type (e.g., .log, .sql, .pdf, .png)
  - Size (bytes)
  - Created date
  - Created by (user)
  - Mock download URL
- Time to answer: < 1 second

**Success Criteria:**
- ✓ At least 1 attachment returned
- ✓ File types are realistic (not all .txt files)
- ✓ Dates are within seed data date range

---

### **Question 6: Multi-Step Orchestration**

**Category:** Foundry orchestrator, combining multiple sources  
**Question:** "I have a ticket about network latency between data centers. Find similar historical tickets, show me the resolution, and any documents that might help."

**Expected Output:**
- Composed narrative answer including:
  - 1–2 similar historical incidents (from Fabric Data Agent)
  - How those incidents were resolved (from search retrieval)
  - 1–2 relevant KB articles or documents (from attachment/search tool)
  - References (incident IDs, KB IDs, document names)
- Time to answer: < 5 seconds

**Success Criteria:**
- ✓ Answer includes results from multiple sources (not just one agent)
- ✓ Sources are cited (e.g., "See INC-2345, resolved by...")
- ✓ Advice is actionable
- ✓ No hallucinations (all references match real seed data)

---

### **Question 7: Cross-Domain Ontology Traversal**

**Category:** Semantic relationships, ontology layer  
**Question:** "Show me all the changes and follow-up incidents related to the change CR-5432."

**Expected Output:**
- List of incidents with:
  - Incident ID
  - Summary
  - Relationship to change (e.g., "opened after", "caused by")
  - Date of incident relative to change
- Time to answer: < 2 seconds

**Success Criteria:**
- ✓ Returns incidents that actually link to CR-5432 in seed data
- ✓ Relationships are semantically correct
- ✓ At least 1 follow-up incident found (if seed data includes one)

---

## Part 4: Expected Output Criteria

For each validation area, here are acceptance criteria:

| Validation Area | What Success Looks Like | What Failure Looks Like |
|---|---|---|
| **VA.1: Realistic API data** | API returns incidents with all fields (id, summary, state, priority, category, requester, dates, notes). Data values are plausible (priority ∈ {P1, P2, P3, P4}, state ∈ {open, in_progress, closed}). | API returns incomplete records, missing fields, malformed JSON, or non-plausible values (e.g., priority = "urgent", state = "unknown"). |
| **VA.2: Azure hosting** | ACA deployment exists in Azure Portal. Ingress tab shows "External" and "HTTPS" enabled. | ACA doesn't exist, ingress is "Internal" only, or HTTPS is not enabled. |
| **VA.3: Health endpoint** | `curl https://<URL>/health` returns HTTP 200 with JSON status "healthy". Latency < 2 seconds. | Returns HTTP 5xx, "unhealthy" status, timeouts, or SSL certificate errors. |
| **VA.4: Seed data domains** | API endpoints return data for incidents, users, groups, categories, KB articles, notes, changes, SLAs, attachments. Each domain has ≥ 1 record. | Any domain is missing, empty, or returns errors. |
| **VA.5: Fabric calls ACA** | Dataflow/pipeline logs show HTTP GET requests to `https://<ACA_URL>/api/v1/...`. No auth errors. HTTP status 200. | Logs show connection errors, timeouts, 401/403 auth failures, or no requests to ACA. |
| **VA.6: Data in Fabric** | Lakehouse/Warehouse has tables with data. Row counts > 0. Tables match ACA API domains. | Tables are empty (0 rows), missing, or contain wrong data. |
| **VA.7: Curated tables** | Tables like `dim_incident`, `fact_work_note`, `dim_user` exist. Joins work. No NULL id fields. | Tables don't exist, have broken foreign keys, or missing critical columns. |
| **VA.8: Text cleaning** | HTML tags removed from cleaned text. Output is readable. Meaning preserved. | HTML tags still present, gibberish output, or meaning corrupted. |
| **VA.9: Semantic model** | Model includes dimensions (date, user, group, category, priority, state) and measures (volume, count, avg time, SLA breaches). Queries work in Fabric. | Model is incomplete, missing dimensions/measures, or queries fail. |
| **VA.10: Ontology** | Ontology document/graph includes at least 6 entity types and 5 relationship types. Relationships are named (e.g., "opened_by", "assigned_to"). | Ontology is missing, incomplete, or relationships are undefined. |
| **VA.11: Fabric Data Agent** | Agent answers structured questions in < 2 seconds. Answers are accurate. Answer references the semantic model. | Agent fails to answer, returns wrong answer, or doesn't cite sources. |
| **VA.12: Search/retrieval** | Keyword search returns relevant results. Relevance scores are reasonable. Results include source references. | No results returned, results are irrelevant, or no source citations. |
| **VA.13: Attachments** | Tool returns attachment metadata (filename, type, size, date). At least 1 attachment per incident. Includes mock URL. | No attachments returned, missing metadata, or invalid URLs. |
| **VA.14: Foundry orchestrator** | Orchestrator composes answers from multiple sources. Answers are grounded and cited. No hallucinations. | Orchestrator fails, answers are generic, or references don't exist in data. |

---

## Part 5: Known Limitations & Disclaimers

Before demo day, disclose the following limitations to stakeholders:

### **Scope Limitations**

1. **Mock Data Only**
   - This POC uses fictional, synthetically generated ServiceNow data (SQLite seed file).
   - In production, Fabric would ingest real ServiceNow API data, not mock data.
   - The POC demonstrates the *architecture and capability*, not production data.

2. **Limited Historical Data**
   - Seed data includes ~50 incidents and ~20 KB articles.
   - Production systems have millions of historical tickets.
   - POC validation questions are tailored to seed data; real queries may need broader indexes.

3. **No User Authentication**
   - The mock API uses a simple HTTP header for demo auth, not OAuth or AD.
   - Production Fabric deployments would use Entra ID, service principals, or Azure managed identity.

4. **No Real Attachment Files**
   - Attachments are represented as metadata (filename, size, type) with mock download URLs.
   - Actual binary files (images, PDFs, logs) are not stored in the POC.
   - Production would link to Azure Blob Storage or SharePoint for real files.

### **Functional Limitations**

5. **Search Index is Static**
   - The search/vector index is built once during initial Fabric ingestion.
   - In a live system, new work notes, KB articles, and tickets would be re-indexed automatically.
   - POC requires manual re-indexing if seed data changes.

6. **Ontology is Scoped**
   - Ontology includes only ticket-related entities (Ticket, User, Group, Category, KB Article, Attachment, Change).
   - Production may include CMDB data, business services, dependencies, and other domains.

7. **Foundry Orchestrator is Simplified**
   - Orchestrator is a single agent that routes to sub-agents.
   - Production may use agentic loops, guardrails, human-in-the-loop, and advanced routing.

8. **No Agentic Reasoning Loop**
   - Agent responses are generated in single pass.
   - Production agents may refine answers via chain-of-thought or iterative sub-queries.

### **Performance & Scale Limitations**

9. **Response Times Are Artificial**
   - Query times are fast (< 2 seconds) because seed data is small.
   - Production systems with millions of rows may see higher latency; performance optimization would be needed.

10. **No Rate Limiting or Throttling**
    - The mock API has no rate limiting.
    - Production APIs would implement throttling, caching, and load balancing.

11. **No Audit or Change History**
    - Changes to tickets are not logged.
    - Production systems would track who changed what and when.

### **Integration Limitations**

12. **No Real Incident Modification**
    - The API is read-only for the POC.
    - Production would allow ticket updates, note creation, and assignment changes from Fabric/Foundry.

13. **No ServiceNow Sync**
    - This is one-way: ServiceNow API → Fabric.
    - Production may require bi-directional sync (e.g., agent suggestions are written back to ServiceNow).

14. **No Multi-Language Support**
    - Questions and answers are English-only in the POC.
    - Production Autoliv deployment may need support for German, Swedish, or other languages.

### **Disclaimer for Stakeholders**

> **"This POC is a proof of architecture, not production software. It demonstrates how ServiceNow data can be ingested into Fabric, shaped into a semantic model, and queried by a multi-agent system. The data is fictional, the scale is small, and some production features (authentication, bi-directional sync, agentic loops, multi-language) are not implemented. However, the end-to-end flow is real, and it validates that the architecture can work for Autoliv's support use case."**

---

## Part 6: Validation Checklist for Demo Day

Print or bookmark this checklist. Use it 1 hour before demo start:

**1 Hour Before Demo**
- [ ] Confirm all services are running (ACA, Fabric, Foundry)
- [ ] Run smoke test checklist (Part 1) — all 14 validations must pass
- [ ] Test sample questions (Part 3) — spot-check at least Q1, Q6, Q7
- [ ] Verify demo script narrative and timing

**15 Minutes Before Demo**
- [ ] Clear browser cache and cookies (fresh demo state)
- [ ] Open all required browser tabs (Fabric, ACA health endpoint, search interface, Foundry orchestrator)
- [ ] Confirm stakeholders are logged in or have guest access
- [ ] Mute notifications and background processes

**During Demo**
- [ ] Follow demo script narrative (Part 2) — hit each section on time
- [ ] Watch for errors (browser console, API logs)
- [ ] If a live query fails, have a screenshot or recording as fallback
- [ ] Disclose known limitations (Part 5) when asked

**After Demo**
- [ ] Collect feedback from stakeholders
- [ ] Note any questions for the team
- [ ] Save logs and screenshots for post-demo analysis

---

## Appendix: Validation Tool Commands

For quick validation testing, use these commands:

### **Validate ACA API Health**
```bash
curl -X GET https://<ACA_API_BASE_URL>/health \
  -H "Authorization: Bearer <DEMO_AUTH_TOKEN>" \
  -w "\nHTTP Status: %{http_code}\n"
```

### **Validate Incidents Data**
```bash
curl -X GET https://<ACA_API_BASE_URL>/api/v1/incidents?limit=5 \
  -H "Authorization: Bearer <DEMO_AUTH_TOKEN>"
```

### **Validate Fabric Ingestion**
```powershell
# In Fabric workspace, open SQL Notebook
SELECT COUNT(*) as incident_count FROM dbo.stg_incidents;
SELECT COUNT(*) as work_note_count FROM dbo.stg_work_notes;
```

### **Validate Semantic Model**
```powershell
# In Fabric workspace, open Semantic Model
# Run DAX query
EVALUATE
SUMMARIZECOLUMNS(
  'Incidents'[Priority],
  "Count", COUNTX('Incidents', 'Incidents'[Incident_ID])
)
```

### **Validate Search Index**
```bash
# Example using Azure AI Search REST API
curl -X POST https://<SEARCH_SERVICE>.search.windows.net/indexes/kb-articles/docs/search?api-version=2023-11-01 \
  -H "Content-Type: application/json" \
  -H "api-key: <SEARCH_API_KEY>" \
  -d '{
    "search": "database connection",
    "top": 5
  }'
```

---

## Sign-Off

This validation plan is approved for use in demo validation and customer-facing presentations. All 14 validation areas are covered. Smoke test checklist is executable. Demo script is ready.

**Plan Version:** 1.0  
**Created:** 2026-06-17  
**Next Review:** After first live demo  
