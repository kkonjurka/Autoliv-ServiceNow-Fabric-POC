# Autoliv ServiceNow to Microsoft Fabric POC — Validation Plan

**Document Date:** 2026-06-24  
**Author:** Zoe (Testing & Validation Specialist)  
**Status:** Ready for Demo Validation  

---

## Executive Summary

This validation plan defines how we verify that the Autoliv ServiceNow to Microsoft Fabric POC meets business and technical requirements. The plan covers:

1. **Smoke test checklist** — 14 pass/fail validations covering every major component
2. **Demo script** — a 10–15 minute end-to-end narrative for stakeholders
3. **Sample test questions** — 22 questions across structured, retrieval, attachment, and multi-tool paths, each with expected answer pattern and tool call list
4. **Expected output criteria** — what a good answer looks like for each agent type
5. **Known limitations** — honest disclosure of what this POC does not do

**Dataset at a glance:** 32 incidents (8 scenarios × 4 sites), 8 KB articles, 8 users, 8 assignment groups, 7 change requests, and mock attachment metadata.  
**Live API:** `https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io`

---

## Part 1: Smoke Test Checklist

Run tests in order. Stop at first failure and resolve before continuing.

**API base URL:** `https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io`

---

### **VA.1 — Mock API returns realistic ServiceNow-style data**

| Field | Detail |
|---|---|
| **What to test** | Incident endpoint returns well-formed records with all required ServiceNow-style fields |
| **How to test** | `curl https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io/api/v1/incidents?limit=3` |
| **Expected result** | HTTP 200; JSON array with incidents containing: `id`, `number`, `summary`, `state`, `priority`, `category_id`, `assignment_group_id`, `requester_id`, `opened_at`, `updated_at`, `work_notes`, `resolution_notes`, `attachments` |
| **Pass criteria** | ✅ HTTP 200; ✅ ≥ 1 incident returned; ✅ all required fields present and non-null; ✅ `priority` ∈ {`1 - Critical`, `2 - High`, `3 - Moderate`, `4 - Low`}; ✅ `state` ∈ {`Open`, `In Progress`, `Resolved`, `Closed`} |
| **Fail criteria** | ❌ Any HTTP 4xx/5xx; ❌ missing or null required fields; ❌ priority/state values outside allowed set; ❌ malformed JSON |

---

### **VA.2 — Mock API deployed to ACA with external HTTPS ingress**

| Field | Detail |
|---|---|
| **What to test** | Azure Container Apps deployment exists and is configured for external, HTTPS-only ingress |
| **How to test** | Azure Portal → Container Apps → `aca-servicenow-mock-api` → Ingress blade. Confirm "Ingress enabled", "External", "HTTPS Only" all set to true. |
| **Expected result** | ACA resource visible; ingress type = External; HTTPS enforced; container is Running with ≥ 1 replica |
| **Pass criteria** | ✅ ACA resource exists; ✅ Ingress = External; ✅ HTTPS-only = true; ✅ container state = Running |
| **Fail criteria** | ❌ ACA resource not found; ❌ ingress = Internal; ❌ HTTP allowed (not HTTPS-only); ❌ container state = Failed or provisioning |

---

### **VA.3 — Health endpoint validates from outside ACA**

| Field | Detail |
|---|---|
| **What to test** | The `/health` endpoint is reachable from any external network and returns a healthy status |
| **How to test** | From a machine outside Azure: `curl -w "\nHTTP: %{http_code} Time: %{time_total}s\n" https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io/health` |
| **Expected result** | HTTP 200; JSON body `{"status": "healthy", "timestamp": "..."}` ; round-trip time < 2 seconds |
| **Pass criteria** | ✅ HTTP 200; ✅ `status == "healthy"`; ✅ response time < 2 s; ✅ valid TLS certificate (no SSL warning) |
| **Fail criteria** | ❌ HTTP 5xx or connection refused; ❌ `status != "healthy"`; ❌ response time > 5 s; ❌ SSL/TLS certificate error |

---

### **VA.4 — SQLite seed data includes all entity types**

| Field | Detail |
|---|---|
| **What to test** | The SQLite-backed API serves all required entity domains: incidents, users, groups, categories, KB articles, work notes, resolution notes, change requests, SLAs, and attachments |
| **How to test** | Call each endpoint: `/api/v1/incidents`, `/api/v1/kb-articles`, `/api/v1/users`, `/api/v1/groups`, `/api/v1/changes` and check for non-empty responses |
| **Expected result** | Each endpoint returns HTTP 200 with ≥ 1 record; incidents show 32 total; KB articles show 8 total |
| **Pass criteria** | ✅ All endpoints return HTTP 200; ✅ incidents count = 32; ✅ KB articles count = 8; ✅ users, groups, categories, changes all return ≥ 1 record |
| **Fail criteria** | ❌ Any endpoint returns HTTP 404 or empty array; ❌ incident count < 32; ❌ KB article count < 8 |

---

### **VA.5 — Fabric ingestion calls the ACA API endpoint**

| Field | Detail |
|---|---|
| **What to test** | The Fabric notebook `01_Ingest_Raw` makes HTTP calls to the ACA URL and receives data successfully |
| **How to test** | Run notebook `01_Ingest_Raw`; inspect cell output logs for HTTP request lines and check for `200 OK` responses against the ACA base URL |
| **Expected result** | Log lines show `GET https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io/api/v1/...` with HTTP 200; no auth errors or timeouts |
| **Pass criteria** | ✅ HTTP 200 for all ingestion requests; ✅ row counts written to Bronze layer tables > 0; ✅ no 401/403/5xx errors in logs |
| **Fail criteria** | ❌ HTTP 401/403 (auth failure); ❌ HTTP 5xx or timeout; ❌ 0 rows written to any table |

---

### **VA.6 — Data ingested into real Fabric Lakehouse**

| Field | Detail |
|---|---|
| **What to test** | Bronze/staging Delta tables exist in the Fabric Lakehouse with non-zero row counts after ingestion |
| **How to test** | In Fabric workspace → Lakehouse → Tables: verify `stg_incidents`, `stg_kb_articles`, `stg_users`, `stg_groups`, `stg_work_notes`, `stg_attachments` exist. Run `SELECT COUNT(*) FROM stg_incidents` in a SQL notebook. |
| **Expected result** | `stg_incidents` = 32 rows; `stg_kb_articles` = 8 rows; all other staging tables ≥ 1 row |
| **Pass criteria** | ✅ All tables exist; ✅ `stg_incidents` row count = 32; ✅ `stg_kb_articles` row count = 8; ✅ no table has 0 rows |
| **Fail criteria** | ❌ Any table missing; ❌ any table has 0 rows; ❌ row counts don't match source API |

---

### **VA.7 — Transformations produce curated tables**

| Field | Detail |
|---|---|
| **What to test** | Notebook `02_Transform_Curated` produces Silver/curated Delta tables with correct joins and no orphaned foreign keys |
| **How to test** | Run notebook `02_Transform_Curated`; verify tables `dim_incident`, `dim_user`, `dim_group`, `dim_category`, `fact_incident_ticket`, `fact_work_note`, `fact_attachment`; run a join query: `SELECT COUNT(*) FROM fact_incident_ticket f JOIN dim_incident d ON f.incident_id = d.id` |
| **Expected result** | All curated tables exist; join returns 32 rows; no NULL `id` columns; cleaned text columns present |
| **Pass criteria** | ✅ All 7 curated tables exist; ✅ join count matches staging count; ✅ `id` columns never NULL; ✅ `cleaned_text` columns populated |
| **Fail criteria** | ❌ Any curated table missing; ❌ join count < staging count (broken FK); ❌ NULL ids; ❌ missing text columns |

---

### **VA.8 — HTML fields converted to cleaned text**

| Field | Detail |
|---|---|
| **What to test** | The transformation pipeline strips HTML tags from `description_html`, `content_html`, and work note fields, producing readable plain text |
| **How to test** | Query `stg_kb_articles` for any record and compare `content_html` to `content_text`. E.g., `SELECT content_html, content_text FROM stg_kb_articles WHERE id = 'kb-001'` |
| **Expected result** | `content_html` contains `<p>`, `<ul>`, `<li>`, etc.; `content_text` is the same content with all HTML tags removed and whitespace normalised |
| **Pass criteria** | ✅ No HTML tags in `content_text`; ✅ text is human-readable; ✅ semantic meaning preserved (keywords still present) |
| **Fail criteria** | ❌ HTML tags still present in `content_text`; ❌ text is empty or garbled; ❌ keyword content stripped |

---

### **VA.9 — Semantic model supports structured operational questions**

| Field | Detail |
|---|---|
| **What to test** | The published `ServiceNow_SemanticModel` in the Fabric workspace contains the required dimensions, measures, and relationships for operational reporting |
| **How to test** | Open Fabric workspace → `ServiceNow_SemanticModel` → Data view. Confirm tables: `Incidents`, `Users`, `Groups`, `Categories`, `KB_Articles`, `SLAs`. Run a DAX query: `EVALUATE SUMMARIZECOLUMNS('Incidents'[Priority], "Count", [Open Ticket Count])` |
| **Expected result** | DAX query returns a table with 4 rows (one per priority level); `Open Ticket Count` measure returns non-zero values |
| **Pass criteria** | ✅ All 6 tables visible; ✅ ≥ 4 measures visible (Ticket Volume, Open Ticket Count, Average Resolution Time, SLA Breach Count); ✅ DAX query executes without error; ✅ results match manual count from staging tables |
| **Fail criteria** | ❌ Model not found or not published; ❌ missing tables or measures; ❌ DAX query errors; ❌ measure values don't match staging data |

---

### **VA.10 — Ontology supports entity relationship traversal**

| Field | Detail |
|---|---|
| **What to test** | The ontology layer (notebook `04_Ontology_Graph` and Delta tables) correctly models entity relationships and allows traversal queries |
| **How to test** | Run notebook `04_Ontology_Graph`; verify Delta tables `ontology_nodes` and `ontology_edges` exist. Query: `SELECT * FROM ontology_edges WHERE source_type = 'Ticket' LIMIT 10` |
| **Expected result** | `ontology_edges` returns relationships: `assigned_to` (Ticket→Group), `opened_by` (Ticket→User), `references_kb` (Ticket→KB Article), `has_attachment` (Ticket→Attachment), `linked_to_change` (Ticket→Change Request) |
| **Pass criteria** | ✅ Both ontology tables exist with rows; ✅ ≥ 5 distinct relationship types; ✅ all 7 entity types represented as nodes; ✅ traversal query returns results |
| **Fail criteria** | ❌ Ontology tables missing or empty; ❌ fewer than 5 relationship types; ❌ any entity type missing from nodes |

---

### **VA.11 — Data Agent handles structured questions**

| Field | Detail |
|---|---|
| **What to test** | The Fabric Data Agent (`ServiceNow Operations Agent`) correctly answers a simple structured question using the semantic model |
| **How to test** | Open the Data Agent in Fabric and ask: *"How many high-priority incidents are currently open?"* |
| **Expected result** | Agent returns a numeric count grounded in the semantic model, e.g. "There are 8 high-priority open incidents." Answer includes citation of the `Open Ticket Count` measure and the `Priority = 2 - High` filter. |
| **Pass criteria** | ✅ Numeric answer returned; ✅ count matches manual query result; ✅ filter context stated (priority, open state); ✅ response time < 5 s |
| **Fail criteria** | ❌ Agent returns an error or "I don't know"; ❌ count doesn't match semantic model; ❌ no filter context stated; ❌ response time > 15 s |

---

### **VA.12 — Search/retrieval handles unstructured content**

| Field | Detail |
|---|---|
| **What to test** | The Azure AI Search index `servicenow-incidents` returns relevant results for a keyword query against KB article content and work note text |
| **How to test** | Run notebook `05_Index_Search` or call Azure AI Search directly: `POST /indexes/servicenow-incidents/docs/search` with body `{"search": "VPN certificate reconnect loop", "top": 5}` |
| **Expected result** | Returns ≥ 2 results from the `vpn-cert-loop` scenario; each result includes: `incident_id`, `summary`, `content_snippet`, and relevance `@search.score` > 0.5 |
| **Pass criteria** | ✅ ≥ 2 relevant results returned; ✅ results relate to VPN/certificate content; ✅ `@search.score` > 0.5 for top result; ✅ source IDs included |
| **Fail criteria** | ❌ 0 results returned; ❌ results are unrelated to query; ❌ no relevance scores; ❌ missing source citations |

---

### **VA.13 — Document/image/attachment path returns metadata**

| Field | Detail |
|---|---|
| **What to test** | The `get_attachment_metadata` tool returns realistic attachment metadata for a given incident, including filename, type, size, and a mock download URL |
| **How to test** | Invoke the Foundry orchestrator's `get_attachment_metadata` tool directly (or via `foundry-agent/app.py`) with `incident_id = "inc-001"` |
| **Expected result** | Returns a list of attachment objects; each includes: `filename`, `content_type`, `attachment_size` (bytes), `created_by`, `created_at`, `download_url` (mock) |
| **Pass criteria** | ✅ ≥ 1 attachment returned for a known incident; ✅ all metadata fields present; ✅ `download_url` is a valid URL format; ✅ file types are realistic (.log, .png, .sql, .pdf) |
| **Fail criteria** | ❌ Empty attachment list for known incident; ❌ missing metadata fields; ❌ `download_url` is null or malformed |

---

### **VA.14 — Foundry orchestrator returns grounded answers**

| Field | Detail |
|---|---|
| **What to test** | The Foundry orchestrator (`servicenow-orchestrator`) routes a complex multi-source question to the correct sub-tools and composes a grounded answer with citations |
| **How to test** | Invoke `foundry-agent/app.py` with: *"Find historical incidents similar to a VPN reconnect loop after password rotation. Show resolutions and any related KB articles."* |
| **Expected result** | Orchestrator calls `search_incidents` (for similar tickets), `search_knowledge` (for KB articles), and `query_fabric_data_agent` (for SLA/priority context); final answer cites incident IDs (e.g., INC0001001) and KB numbers (e.g., KB001001) |
| **Pass criteria** | ✅ ≥ 2 sub-tools invoked; ✅ answer cites real incident/KB IDs from seed data; ✅ resolution steps are grounded (not hallucinated); ✅ confidence level stated |
| **Fail criteria** | ❌ Only 1 tool invoked; ❌ citations reference IDs not in seed data; ❌ resolution steps contradict seed data; ❌ orchestrator errors or times out |

---

## Part 2: Demo Script

**Duration:** 10–15 minutes  
**Audience:** Stakeholders, customer, internal IT leadership  
**Pre-flight:** Complete the smoke test checklist (Part 1) at least 30 minutes before demo start. Have all browser tabs open and tested.

---

### **Step 1 — Set the Scene (1–2 min)**

> **What to say:**  
> "Autoliv runs a global IT support operation. When a technician opens a ticket, they often need to quickly figure out: has this happened before? How was it fixed? Are there relevant runbooks or docs? Today's POC shows how Microsoft Fabric and Azure AI can answer all of those questions automatically, starting from the moment a ticket is opened.
>
> The architecture has three layers: a Fabric semantic model for structured reporting, an Azure AI Search index for unstructured KB and notes retrieval, and a Foundry orchestrator that ties everything together. Let's walk through a real scenario."

> **Expected audience questions:**  
> *"Is this real ServiceNow data?"* — "Not in this POC. We're using a mock API hosted in Azure Container Apps that returns synthetic but realistic data. In production this would connect to the live ServiceNow instance."

> **Fallback:** If the browser is slow, show the architecture diagram in `docs/ARCHITECTURE.md` on screen while narrating.

---

### **Step 2 — Show the Live API (1–2 min)**

> **What to show:** Browser tab → `https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io/health`

> **What to say:**  
> "First, the source of truth: a FastAPI service deployed to Azure Container Apps. It exposes a ServiceNow-style REST API backed by SQLite, with 32 incidents across 8 issue scenarios, 8 KB articles, and a full set of attachments, work notes, and change records. Fabric ingests from here on a scheduled pipeline."

> Open `/api/v1/incidents?limit=2` to show the JSON payload live.

> **Expected questions:**  
> *"Why not connect to real ServiceNow?"* — "Real ServiceNow credentials are out of scope for the POC. The mock lets us iterate quickly while keeping the architecture identical. Swapping the base URL is the only change needed for production."

> **Fallback:** Show a pre-recorded screen capture of the API response if Azure is unreachable.

---

### **Step 3 — Fabric Ingestion & Lakehouse (2 min)**

> **What to show:** Microsoft Fabric workspace → Lakehouse → Tables list

> **What to say:**  
> "Every 24 hours, the ServiceNow Pipeline runs three notebooks: one to ingest raw data from the API into Delta tables, one to transform and clean it (including stripping HTML from work notes and descriptions), and a third to build the ontology graph. Here you can see the ingested tables—32 incident rows in `stg_incidents`, 8 KB articles in `stg_kb_articles`, and cleaned text throughout."

> Scroll to show `stg_incidents` row count and click into one row to show the `cleaned_text` vs. the `description_html` field.

> **Fallback:** Show a screenshot of the Lakehouse with row counts pre-captured if the Fabric workspace is slow to load.

---

### **Step 4 — Structured Question via Fabric Data Agent (2–3 min)**

> **What to show:** Fabric workspace → `ServiceNow Operations Agent`

> **What to say:**  
> "Now, a structured question. I'm asking the Fabric Data Agent: *'Which assignment groups have the most open incidents right now, and what's the SLA breach rate for each?'*"

> Submit the question and show the response.

> **Expected response:** Table showing assignment groups (Network Operations, Application Support, etc.), open incident count, and SLA breach rate—all grounded in the semantic model.

> **What to say:**  
> "Notice the agent cites which measure it used and applies the correct filter automatically. No SQL, no BI dashboard—just a question in plain English."

> **Expected questions:**  
> *"Can it do trend analysis?"* — "Yes. We have a Date dimension in the model. You can ask 'How has ticket volume changed week over week?'"

> **Fallback:** Paste the question into a DAX query in the semantic model's data view and show the equivalent result manually.

---

### **Step 5 — Unstructured Search Across KB & Notes (2 min)**

> **What to show:** Azure AI Search → `servicenow-incidents` index, or the Foundry orchestrator's `search_knowledge` tool output

> **What to say:**  
> "Structured data answers 'how many'—but engineers also need to know 'how was it fixed before?' That's where the search index comes in. I'm querying: *'Show KB articles about VPN certificate reconnect loops.'*"

> Run the query and show results with KB IDs, summaries, and relevance scores.

> **Expected response:** KB001001 "Troubleshoot VPN reconnect after certificate rotation" with a snippet and score ≥ 0.7.

> **Fallback:** Show the pre-indexed results by opening notebook `05_Index_Search` output cells.

---

### **Step 6 — Attachment Metadata Retrieval (1 min)**

> **What to show:** Foundry orchestrator or direct call to `get_attachment_metadata` tool

> **What to say:**  
> "When a ticket does have relevant documents—debug logs, screenshots, scripts—the attachment tool returns the metadata and a download link. Here I'm pulling attachments for INC0001001."

> Show the result: filename, type (.log, .png), size in bytes, created by, mock URL.

> **Expected questions:**  
> *"Are the actual files stored?"* — "Metadata only in this POC. In production, files would live in Azure Blob Storage or SharePoint, and the URL would be a real pre-signed link."

> **Fallback:** Show the `stg_attachments` table in the Lakehouse with attachment rows.

---

### **Step 7 — Foundry Orchestrator End-to-End (2–3 min)**

> **What to show:** `foundry-agent/app.py` or a chat interface wired to the orchestrator

> **What to say:**  
> "Finally, the orchestrator. This is the layer a Tier 1 support engineer would actually interact with. I'm asking a complex question that crosses all three paths: *'I have a new ticket about VPN reconnect loops after a password rotation. Find similar historical incidents, show how they were resolved, and pull any relevant KB articles and documents.'*"

> Submit the question. Narrate as the tool calls appear:

> "Watch the tool call log—it's calling `search_incidents` for similar tickets, `search_knowledge` for KB articles, and `get_attachment_metadata` for documents. Then it composes a single grounded answer."

> **Expected response outline:**
> - Similar incidents: INC0001001, INC0001002 — resolved by reissuing the device certificate via CHG001001
> - KB article: KB001001 — "Troubleshoot VPN reconnect after certificate rotation"
> - Attachments: cert-chain-diagram.png, vpn-debug.log
> - Recommended next steps grounded in those sources

> **What to say:**  
> "The answer is grounded — every recommendation has a source. No hallucination. The engineer can click to the KB article, review the resolution notes from the historical ticket, and know exactly what to try."

> **Expected questions:**  
> *"What if the question is ambiguous?"* — "The orchestrator is configured to state its confidence level and flag when a question needs human review. It won't guess."

> **Fallback:** Show a pre-run output from a saved session log in `foundry-agent/` if the live call fails.

---

### **Step 8 — Wrap-Up (1 min)**

> **What to say:**  
> "To summarise: we've shown data flowing from a mock ServiceNow API into Fabric, being shaped by a semantic model and a search index, and then made accessible through a multi-agent orchestrator that any support engineer can use in plain English. The architecture is production-ready in structure. Swapping mock data for real ServiceNow, adding Entra ID auth, and wiring up real Blob Storage are the next steps.
>
> Questions?"

---

## Part 3: Sample Test Questions

22 questions across 4 paths. For each: **question**, **expected answer pattern**, **tools invoked**.

> **Tool reference:**  
> `DATA_AGENT` = Fabric Data Agent (`query_fabric_data_agent`)  
> `SEARCH_KB` = Azure AI Search KB index (`search_knowledge`)  
> `SEARCH_INC` = Azure AI Search incidents index (`search_incidents`)  
> `ATTACH` = Attachment metadata tool (`get_attachment_metadata`)  
> `ORCHESTRATOR` = Foundry orchestrator (routes to above tools)

---

### Category A — Structured (Fabric Data Agent) — 6 Questions

**SQ-1**  
**Question:** "How many incidents are currently open across all assignment groups?"  
**Expected pattern:** Scalar count, e.g. "There are 16 open incidents across 8 assignment groups." Filters: state ∈ {Open, In Progress}.  
**Tools:** `DATA_AGENT`

---

**SQ-2**  
**Question:** "Which assignment group has the highest number of open high-priority tickets?"  
**Expected pattern:** Single group name + count, e.g. "Application Support has 3 open high-priority (P1/P2) incidents." Sorted descending by open count.  
**Tools:** `DATA_AGENT`

---

**SQ-3**  
**Question:** "What is the average resolution time for Critical (P1) incidents?"  
**Expected pattern:** Duration in hours, e.g. "Average resolution time for P1 incidents is 6.4 hours." Grounded in `Average Resolution Time` measure, filtered to P1 closed/resolved.  
**Tools:** `DATA_AGENT`

---

**SQ-4**  
**Question:** "How many SLA breaches have occurred in the last 30 days, broken down by priority?"  
**Expected pattern:** Table with Priority and Breach Count columns, e.g. P1=2, P2=4, P3=1. Grounded in `SLA Breach Count` measure with date filter.  
**Tools:** `DATA_AGENT`

---

**SQ-5**  
**Question:** "Show me all incidents opened in the last 7 days that are still unresolved."  
**Expected pattern:** Table with Incident Number, Summary, Priority, Assignment Group, Days Open. Filtered to state ∈ {Open, In Progress} and `opened_at` within the last 7 days.  
**Tools:** `DATA_AGENT`

---

**SQ-6**  
**Question:** "Which category has the highest ticket backlog right now?"  
**Expected pattern:** Single category name + count, e.g. "Network / VPN has the highest backlog with 5 open tickets." Grounded in `Backlog by Priority` measure grouped by category.  
**Tools:** `DATA_AGENT`

---

### Category B — Retrieval (Azure AI Search) — 6 Questions

**RQ-1**  
**Question:** "Find KB articles about VPN certificate reconnect issues."  
**Expected pattern:** List of ≥ 1 KB article with number (KB001001), title ("Troubleshoot VPN reconnect after certificate rotation"), summary snippet, and relevance score ≥ 0.6.  
**Tools:** `SEARCH_KB`

---

**RQ-2**  
**Question:** "Show me historical incidents where users had SSO login loops in a browser."  
**Expected pattern:** ≥ 1 incident from the `sso-browser-loop` scenario (INC0001005–INC0001008), with summary, resolution notes excerpt, and similarity score.  
**Tools:** `SEARCH_INC`

---

**RQ-3**  
**Question:** "Are there any KB articles about printer or label spooler errors?"  
**Expected pattern:** KB001007 ("Recover label printer after spooler service failure") with a content snippet and score ≥ 0.6.  
**Tools:** `SEARCH_KB`

---

**RQ-4**  
**Question:** "Find resolution patterns for tickets about warehouse scanner latency."  
**Expected pattern:** ≥ 1 incident from the `scanner-latency` scenario; resolution notes excerpt showing the fix (queue service restart + CHG001004).  
**Tools:** `SEARCH_INC`

---

**RQ-5**  
**Question:** "What KB articles cover SQL query timeout troubleshooting?"  
**Expected pattern:** KB001006 ("Diagnose and resolve SQL report query timeouts") with snippet and score ≥ 0.6.  
**Tools:** `SEARCH_KB`

---

**RQ-6**  
**Question:** "Find any tickets resolved by a change request that involved index rebuilds."  
**Expected pattern:** Incident(s) linked to CHG001005 ("Rebuild reporting indexes after ETL window"); incidents from the `fabric-refresh-delay` or `sql-timeout` scenarios with resolution notes citing the change.  
**Tools:** `SEARCH_INC`

---

### Category C — Attachments — 4 Questions

**AQ-1**  
**Question:** "What attachments are on incident INC0001001?"  
**Expected pattern:** List including at minimum: filename (e.g. `vpn-debug.log`), content_type (`text/plain`), attachment_size in bytes, created_by (user name), created_at (timestamp), mock download_url.  
**Tools:** `ATTACH`

---

**AQ-2**  
**Question:** "Are there any screenshots attached to tickets in the SSO browser loop scenario?"  
**Expected pattern:** ≥ 1 attachment with content_type `image/png` or `image/jpeg`, associated with an INC0001005–INC0001008 incident, including filename and size.  
**Tools:** `ATTACH`

---

**AQ-3**  
**Question:** "Show me all log files attached to incidents assigned to the Network Operations group."  
**Expected pattern:** List of attachments with `.log` extension tied to incidents with `assignment_group = Network Operations`. Includes incident number, filename, size, and mock URL for each.  
**Tools:** `ATTACH`

---

**AQ-4**  
**Question:** "Were there any PDF documents or runbooks attached to the Intune enrollment drift tickets?"  
**Expected pattern:** ≥ 1 attachment with content_type `application/pdf` or filename matching `*.pdf`/`*.docx`, associated with incidents from the `intune-enrollment-drift` scenario (INC0001029–INC0001032).  
**Tools:** `ATTACH`

---

### Category D — Multi-Tool Orchestration — 6 Questions

**MQ-1**  
**Question:** "I have a new ticket about VPN reconnect loops after a password rotation in Stockholm. What are the most similar historical incidents, how were they resolved, and which KB articles should I read?"  
**Expected pattern:** Composed answer with: (a) similar incidents from `vpn-cert-loop` scenario with resolution notes; (b) KB001001 citation; (c) recommended steps grounded in historical fix (reissue device cert, link to CHG001001). All references use real IDs from seed data.  
**Tools:** `SEARCH_INC` → `SEARCH_KB` → `DATA_AGENT` (for SLA context)

---

**MQ-2**  
**Question:** "How severe is the current open ticket backlog for the Endpoint Engineering group, and have they had similar backlogs before?"  
**Expected pattern:** (a) Current open count and SLA breach rate from semantic model; (b) trend context or comparison with historical patterns from search; (c) any related KB articles. Cites measure names and source IDs.  
**Tools:** `DATA_AGENT` → `SEARCH_INC` → `SEARCH_KB`

---

**MQ-3**  
**Question:** "A shared mailbox stopped syncing after a Windows patch in Detroit. Find similar incidents and any documents that could help the engineer."  
**Expected pattern:** Incidents from `shared-mailbox-drift` scenario; resolution notes referencing the Exchange Online re-consent fix; KB001004 ("Repair shared mailbox after Outlook profile corruption"); and any attachments (e.g. `mailbox-sync-diagnostic.log`) cited with mock URLs.  
**Tools:** `SEARCH_INC` → `SEARCH_KB` → `ATTACH`

---

**MQ-4**  
**Question:** "Give me a full situation report for the sql-timeout scenario: current open tickets, historical resolution rate, and any relevant runbooks."  
**Expected pattern:** (a) Current open count from `DATA_AGENT`; (b) resolution time statistics (% resolved within SLA); (c) similar closed incidents from `SEARCH_INC` with resolution notes; (d) KB001006 citation. Response structured as a mini-report with section headings.  
**Tools:** `DATA_AGENT` → `SEARCH_INC` → `SEARCH_KB`

---

**MQ-5**  
**Question:** "I need to escalate a P1 incident about Fabric dashboard refresh delays in Prague. What context should I include, and are there any related change requests or KB articles?"  
**Expected pattern:** (a) P1 escalation context from semantic model (SLA target, breach threshold); (b) similar incidents from `fabric-refresh-delay` scenario; (c) CHG001003 and CHG001005 cited as related changes; (d) KB001003 ("Recover Fabric report refresh after ETL window delay") cited with snippet.  
**Tools:** `DATA_AGENT` → `SEARCH_INC` → `SEARCH_KB`

---

**MQ-6**  
**Question:** "Across all resolved incidents, which change requests caused the most follow-on tickets, and what can we do to prevent recurrence?"  
**Expected pattern:** (a) Structured summary of change→incident links from semantic model; (b) CHG001001 (VPN cert rotation) and CHG001004 (scanner queue repair) identified as highest-impact changes; (c) KB articles for each scenario; (d) prevention recommendations grounded in resolution notes. Confidence level stated.  
**Tools:** `DATA_AGENT` → `SEARCH_INC` → `SEARCH_KB`

---

## Part 4: Expected Output Criteria

### Fabric Data Agent Responses

| Criterion | Good (Pass) | Bad (Fail) |
|---|---|---|
| **Format** | Direct sentence + compact table or bullet list; states filter context (priority, state, date range, group) | Wall of text; no filter context; unformatted JSON blob |
| **Accuracy** | Numeric values match manual DAX query or staging table count | Values differ from ground truth by more than rounding |
| **Citations** | States which measure was used (e.g. "based on Open Ticket Count measure") and which filters applied | No measure or filter context stated |
| **Handling unknowns** | Explicitly says "the semantic model does not contain that data" and recommends retrieval path | Fabricates an answer or returns a generic non-answer |
| **Response time** | < 5 seconds for simple aggregation; < 10 seconds for multi-dimension breakdown | > 15 seconds; timeout |

### Search / Retrieval Results

| Criterion | Good (Pass) | Bad (Fail) |
|---|---|---|
| **Relevance** | Top result `@search.score` ≥ 0.6; top result is topically related to the query | Top result score < 0.3; results are unrelated |
| **Ranking** | Most relevant document appears first or second | Higher-scoring but irrelevant documents ranked above on-topic results |
| **Source references** | Each result includes incident number (INCxxxxxxx) or KB number (KBxxxxxx) | No source IDs; "result 1, result 2" only |
| **Snippet quality** | Content snippet is ≥ 50 characters and semantically meaningful | Snippet is empty, truncated mid-word, or shows raw HTML |
| **Coverage** | Returns results from both KB articles and incident work notes when both exist | Only returns one content type regardless of query |

### Orchestrator Responses

| Criterion | Good (Pass) | Bad (Fail) |
|---|---|---|
| **Grounding** | Every recommendation cites a real incident ID, KB number, or change request number from seed data | Recommendations reference IDs that don't exist in seed data |
| **Multi-source synthesis** | Integrates results from ≥ 2 tools into a coherent narrative | Returns raw dump of one tool's output; other tools not used |
| **Confidence** | States confidence level (e.g. "High — 3 matching incidents found") or flags low-confidence responses | No confidence signal; presents uncertain answers as definitive |
| **Actionability** | Provides at least one concrete next step grounded in historical evidence | Generic advice not traceable to any source in the data |
| **Hallucination rate** | 0 fabricated references; if unsure, says so | Any cited ID, resolution step, or KB title that does not exist in seed data |
| **Response time** | < 15 seconds for multi-tool queries | > 30 seconds; partial response; tool call errors shown to user |

---

## Part 5: Known Limitations

These limitations are honest, not apologies. State them proactively in any stakeholder presentation.

---

### **L1 — SQLite is a mock stand-in, not real ServiceNow**

The API is backed by a SQLite database seeded with synthetic data. It behaves like ServiceNow's REST API (pagination, filtering, relationships) but contains no real incident records, no real user accounts, and no real organisational data. In production, the ingestion notebooks would point to the Autoliv ServiceNow instance using an OAuth service account; the Fabric transformation logic would remain unchanged.

---

### **L2 — No real binary attachments stored (metadata only)**

Attachment objects include filename, content type, file size, creator, and a mock download URL. No actual files (PDFs, PNGs, log files) are stored in this POC. Download URLs point to a placeholder path. In production, binary files would reside in Azure Blob Storage or SharePoint, with real pre-signed or SAS URLs returned by the attachment tool.

---

### **L3 — Embedding quality depends on Azure OpenAI availability**

The Azure AI Search indexes use vector embeddings generated by Azure OpenAI (`text-embedding-ada-002` or equivalent). If the Azure OpenAI endpoint is unavailable, throttled, or the deployment quota is exhausted at demo time, the vector search path will fall back to keyword-only BM25 search. Results will still be returned but with lower semantic relevance. Verify embedding status in Azure OpenAI Studio before the demo.

---

### **L4 — Data Agent requires a published semantic model**

The Fabric Data Agent (`ServiceNow Operations Agent`) only functions against a semantic model that has been published (not just saved as a draft) to the Fabric workspace, and that has been configured as the agent's data source. If the semantic model is unpublished, renamed, or the agent's source is de-linked, the Data Agent will return errors on all structured questions. The semantic model must also be refreshed after any ingestion run to reflect current data.

---

### **L5 — No production authentication or RBAC demonstrated**

The mock API accepts a demo bearer token (`demo-token-autoliv-poc-2026`) with no expiry, rotation, or user identity claims. The Fabric workspace uses personal credentials. The Foundry agent has no Entra ID integration. In production: the API would use Azure AD app registration + managed identity; Fabric workspace access would be governed by workspace roles; the Foundry orchestrator would run under a service principal with scoped permissions.

---

### **L6 — Dataset is limited to 32 incidents and 8 KB articles**

The seed dataset contains exactly 32 incidents (8 issue scenarios × 4 sites each) and 8 KB articles. This is sufficient to demonstrate all POC capabilities but is several orders of magnitude smaller than a production Autoliv ServiceNow instance. Search relevance, SLA statistics, and trend analysis will look different at scale. Semantic similarity scores may be inflated because the dataset is small and internally consistent. Do not extrapolate performance numbers from this POC to production.

---

## Part 6: Validation Checklist for Demo Day

Print or bookmark this checklist. Use it 30 minutes before demo start.

**30 Minutes Before Demo**
- [ ] All services running: ACA health endpoint returns HTTP 200
- [ ] Fabric workspace accessible; `stg_incidents` row count = 32
- [ ] Semantic model published and refreshed in Fabric workspace
- [ ] Azure AI Search index has documents (check index statistics in Azure Portal)
- [ ] Foundry orchestrator agent tested with at least one question (MQ-1)
- [ ] Run smoke tests VA.1, VA.3, VA.11, VA.12, VA.14 as a minimum pre-flight

**15 Minutes Before Demo**
- [ ] Browser tabs open: ACA `/health`, Fabric workspace, search index, Foundry orchestrator
- [ ] Presenter logged into Fabric with a workspace member account
- [ ] Notifications muted; browser dev console closed
- [ ] Fallback screenshots loaded in a backup folder (one per demo step)

**During Demo**
- [ ] Follow demo script (Part 2) — each step has a stated fallback
- [ ] Watch for tool call errors in orchestrator output
- [ ] If live query fails: pivot to pre-captured screenshot and continue narration
- [ ] Proactively state known limitations (Part 5) when audience questions arise

**After Demo**
- [ ] Collect stakeholder questions and record for next sprint
- [ ] Save orchestrator session logs for post-demo review
- [ ] Note any VA checklist items that showed marginal behaviour

---

## Appendix: Quick Validation Commands

### Validate ACA Health
```bash
curl -s -w "\nHTTP: %{http_code}  Time: %{time_total}s\n" \
  https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io/health
```

### Validate Incidents Endpoint (first 3 records)
```bash
curl -s \
  "https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io/api/v1/incidents?limit=3" \
  | python -m json.tool
```

### Validate KB Articles Count
```bash
curl -s \
  "https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io/api/v1/kb-articles" \
  | python -c "import sys,json; d=json.load(sys.stdin); print(f'KB article count: {len(d[\"items\"] if \"items\" in d else d)}')"
```

### Validate Fabric Staging Tables (SQL Notebook in Fabric)
```sql
SELECT 'stg_incidents' AS tbl, COUNT(*) AS row_count FROM stg_incidents
UNION ALL
SELECT 'stg_kb_articles', COUNT(*) FROM stg_kb_articles
UNION ALL
SELECT 'stg_work_notes', COUNT(*) FROM stg_work_notes
UNION ALL
SELECT 'stg_attachments', COUNT(*) FROM stg_attachments;
```

### Validate Semantic Model (DAX — Fabric DAX Query View)
```dax
EVALUATE
SUMMARIZECOLUMNS(
  'Incidents'[Priority],
  'Incidents'[State],
  "Ticket Count", [Ticket Volume],
  "Open Count", [Open Ticket Count]
)
ORDER BY 'Incidents'[Priority]
```

### Validate Azure AI Search Index
```bash
curl -s -X POST \
  "https://<SEARCH_SERVICE>.search.windows.net/indexes/servicenow-incidents/docs/search?api-version=2023-11-01" \
  -H "Content-Type: application/json" \
  -H "api-key: <SEARCH_QUERY_KEY>" \
  -d '{"search": "VPN certificate reconnect", "top": 3, "select": "id,summary,@search.score"}'
```

---

## Sign-Off

This validation plan covers all 14 required validation areas, provides 22 test questions across 4 query paths, defines concrete pass/fail criteria for every smoke test, and honestly documents the 6 known limitations of the POC.

**Plan Version:** 2.0  
**Created:** 2026-06-17  
**Revised:** 2026-06-24 — expanded to 22 test questions, added 4-field smoke test format, updated known limitations to reflect exact dataset sizes  
**Next Review:** After first live demo  
