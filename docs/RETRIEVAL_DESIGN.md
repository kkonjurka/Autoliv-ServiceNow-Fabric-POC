# Retrieval Layer Design for Unstructured ServiceNow Content

**Author:** Jayne, Search/Retrieval Specialist  
**Date:** 2026-06-17  
**Status:** Design Phase  
**Target Audience:** Foundry Orchestrator, Fabric Data Agent, IT Support Operations

---

## Executive Summary

This document defines the retrieval layer for the Autoliv ServiceNow to Microsoft Fabric POC. The retrieval system indexes and searches unstructured ServiceNow content—KB articles, work notes, resolution notes, cleaned HTML text, and attachment metadata—to support IT support users in finding similar historical tickets, relevant knowledge, and supporting documents. The design uses Azure AI Search for vector and keyword indexing with metadata filtering, returning grounded references that link back to source incidents, KB articles, and attachments.

---

## 1. Retrieval Architecture Overview

The retrieval layer sits between the Foundry orchestrator and unstructured content sources:

```
Foundry Orchestrator
        ↓
   [Intent Router]
        ↓
   ┌───────────────────────────────────────┐
   │   Retrieval System (Azure AI Search)  │
   │                                       │
   │  ├─ Keyword Search (BM25)            │
   │  ├─ Vector Search (embeddings)        │
   │  └─ Hybrid Search (combined scoring)  │
   └───────────────────────────────────────┘
        ↓
   [Filtered Results with Metadata]
        ↓
   Foundry Orchestrator → Answer Composition
```

### Key Design Decisions

1. **Azure AI Search** is the search engine (keyword, vector, hybrid).
2. **Separated indexes** for different content types (articles, work notes, resolution notes) to allow targeted searches.
3. **Hybrid search** (BM25 + vector embeddings) balances keyword precision and semantic similarity.
4. **Metadata filters** allow scoped searches (e.g., by category, priority, date range, attachment type).
5. **Source links** in every result trace back to source incidents, KB articles, or attachments.

---

## 2. Content Scope and Indexing Strategy

### 2.1 Indexable Content Sources

The retrieval system indexes the following content types:

| Content Type | Source in ServiceNow | Purpose | Cleaned Text? |
|---|---|---|---|
| **Knowledge Articles** | KB table | Self-service KB search, resolution guidance | Yes (from rich_text field) |
| **Work Notes** | Incidents.work_notes | Historical approach notes, progress tracking | Yes (from cleaned_notes field) |
| **Resolution Notes** | Incidents.resolution_notes | How tickets were ultimately resolved | Yes (from cleaned_resolution field) |
| **Incident Descriptions** | Incidents.description | Issue context, symptoms, error messages | Yes (from cleaned_description field) |
| **Attachment Metadata** | Attachments table | Searchable metadata about attachments (names, types) | Metadata only, not binary content |
| **Document References** | Documents table | External document metadata, summaries | Metadata and description only |
| **Change References** | Changes table | Related change requests, deployment notes | Title, description, status |

### 2.2 Content NOT Indexed Directly

- Binary attachment files (screenshots, logs, scripts)—only searchable by metadata
- Image binary content—indexed by description/OCR text if provided
- Structured incident metrics (SLA times, priority, state)—handled by Fabric Data Agent
- User/group structured data—handled by Fabric Data Agent

---

## 3. Index Schema Design

### 3.1 Main Indexes

The retrieval system maintains **three primary indexes** in Azure AI Search:

#### Index 1: `kb-articles-index`
Indexes knowledge base articles for self-service and resolution guidance.

| Field | Type | Searchable | Filterable | Retrievable | Notes |
|---|---|---|---|---|---|
| `id` | String | No | Yes | Yes | Unique doc ID (kb_{article_id}) |
| `article_id` | String | No | Yes | Yes | Source KB article ID |
| `title` | String | Yes | Yes | Yes | KB article title |
| `content` | String | Yes | No | Yes | Cleaned text from KB article |
| `category` | String | No | Yes | Yes | Knowledge category |
| `subcategory` | String | No | Yes | Yes | Knowledge subcategory |
| `created_date` | DateTimeOffset | No | Yes | Yes | Creation date |
| `updated_date` | DateTimeOffset | No | Yes | Yes | Last update date |
| `view_count` | Int32 | No | Yes | Yes | Number of views (relevance signal) |
| `useful_count` | Int32 | No | Yes | Yes | Marked as useful count (relevance signal) |
| `vector` | Collection(Edm.Single) | Yes | No | No | Embedding vector (1536-dim) |
| `source_url` | String | No | No | Yes | Deep link to KB article in ServiceNow |

#### Index 2: `incident-content-index`
Indexes work notes, resolution notes, and descriptions from incidents for historical similarity and resolution pattern search.

| Field | Type | Searchable | Filterable | Retrievable | Notes |
|---|---|---|---|---|---|
| `id` | String | No | Yes | Yes | Unique doc ID (incident_{incident_id}_{content_type}) |
| `incident_id` | String | No | Yes | Yes | Source incident number |
| `incident_state` | String | No | Yes | Yes | closed, open, in_progress |
| `incident_summary` | String | Yes | No | Yes | Incident short description |
| `description` | String | Yes | No | Yes | Cleaned incident description |
| `work_notes` | String | Yes | No | Yes | Concatenated cleaned work notes |
| `resolution_notes` | String | Yes | No | Yes | Cleaned resolution notes (closed incidents only) |
| `content_type` | String | No | Yes | Yes | description, work_notes, or resolution_notes |
| `priority` | String | No | Yes | Yes | 1-5 priority level |
| `category` | String | No | Yes | Yes | Incident category |
| `subcategory` | String | No | Yes | Yes | Incident subcategory |
| `assigned_group` | String | No | Yes | Yes | Assignment group name |
| `business_service` | String | No | Yes | Yes | Business service / application |
| `created_date` | DateTimeOffset | No | Yes | Yes | When ticket was created |
| `updated_date` | DateTimeOffset | No | Yes | Yes | Last update |
| `closed_date` | DateTimeOffset | No | Yes | Yes | Closure date (if closed) |
| `resolution_time_minutes` | Int32 | No | Yes | Yes | Time to resolve in minutes (signals) |
| `reopen_count` | Int32 | No | Yes | Yes | Number of times reopened (signals) |
| `vector` | Collection(Edm.Single) | Yes | No | No | Embedding vector (1536-dim) |
| `incident_url` | String | No | No | Yes | Deep link to incident in ServiceNow |

#### Index 3: `attachments-index`
Indexes metadata about attachments, documents, and image references.

| Field | Type | Searchable | Filterable | Retrievable | Notes |
|---|---|---|---|---|---|
| `id` | String | No | Yes | Yes | Unique doc ID (attachment_{attachment_id}) |
| `attachment_id` | String | No | Yes | Yes | Source attachment ID |
| `file_name` | String | Yes | Yes | Yes | Name of the attachment (e.g., screenshot.png) |
| `file_type` | String | No | Yes | Yes | mime type or extension (png, log, sql, pdf) |
| `description` | String | Yes | No | Yes | Attachment description or OCR text for images |
| `incident_id` | String | No | Yes | Yes | Incident this attachment belongs to |
| `kb_article_id` | String | No | Yes | Yes | KB article this attachment belongs to |
| `document_id` | String | No | Yes | Yes | Document record ID |
| `attachment_type` | String | No | Yes | Yes | screenshot, log, script, document, image, other |
| `uploaded_date` | DateTimeOffset | No | Yes | Yes | Upload date |
| `size_bytes` | Int32 | No | Yes | Yes | File size in bytes |
| `mock_url` | String | No | No | Yes | Mock URL where attachment can be retrieved |
| `vector` | Collection(Edm.Single) | Yes | No | No | Embedding of description/OCR text |
| `incident_url` | String | No | No | Yes | Link back to source incident |

---

## 4. Metadata Filtering Strategy

Retrieval requests from the orchestrator include optional filters to scope results:

### 4.1 Common Filter Patterns

```
GET /search/kb-articles?q=network+timeout&$filter=(category eq 'Connectivity' or category eq 'Network') and updated_date gt 2025-01-01&top=10

GET /search/incidents?q=database+slow&$filter=incident_state eq 'closed' and resolution_time_minutes lt 480&top=5

GET /search/attachments?$filter=incident_id eq 'INC0123456' and (attachment_type eq 'log' or attachment_type eq 'script')&top=20
```

### 4.2 Filter Combinations Supported

| Use Case | Index | Filter(s) |
|---|---|---|
| KB articles in a category | kb-articles | `category`, `subcategory`, `updated_date` |
| Similar closed tickets | incident-content | `incident_state eq 'closed'`, `category`, `priority`, `assigned_group`, `closed_date` |
| Unresolved follow-up tickets | incident-content | `incident_state eq 'open'`, `priority`, `created_date` |
| Attachments for an incident | attachments | `incident_id`, `attachment_type` |
| High-effort tickets | incident-content | `resolution_time_minutes gt 240`, `reopen_count gt 0` |

---

## 5. Retrieval Patterns

### 5.1 Pattern 1: Similarity Search for Closed Tickets

**User scenario:** IT support agent has a new ticket and wants to see how similar issues were resolved historically.

**Request:**
```
POST /search/incidents/hybrid
{
  "search_text": "network timeout when connecting to database",
  "filters": {
    "incident_state": "closed",
    "category": "Database",
    "closed_date_gte": "2025-01-01"
  },
  "top": 5,
  "include_work_notes": true,
  "include_resolution_notes": true
}
```

**Result:** Top 5 closed incidents ranked by semantic similarity + metadata relevance, with work notes and resolution steps included.

### 5.2 Pattern 2: KB Article Search

**User scenario:** Searching for knowledge base articles on a specific topic.

**Request:**
```
POST /search/kb-articles/hybrid
{
  "search_text": "SSL certificate expiration",
  "filters": {
    "category": "Security",
    "useful_count_gte": 10
  },
  "top": 3
}
```

**Result:** Top 3 KB articles ranked by relevance + popularity signals.

### 5.3 Pattern 3: Follow-up Ticket Search

**User scenario:** Find other open, unresolved tickets in the same category to check for related issues.

**Request:**
```
POST /search/incidents/metadata
{
  "filters": {
    "incident_state": "open",
    "category": "Network",
    "assigned_group": "Network Support Team",
    "priority_lte": 2
  },
  "top": 10,
  "sort_by": "created_date desc"
}
```

**Result:** Open tickets in the same category/group, sorted by most recent.

### 5.4 Pattern 4: Attachment Search

**User scenario:** Find relevant logs or scripts related to an incident.

**Request:**
```
POST /search/attachments
{
  "search_text": "database connection error",
  "filters": {
    "incident_id": "INC0123456",
    "attachment_type": ["log", "script"]
  },
  "top": 10
}
```

**Result:** Attachment metadata and mock URLs, ranked by relevance to search text.

### 5.5 Pattern 5: Full Multi-Index Search

**User scenario:** Foundry orchestrator needs comprehensive search across KB, incidents, and attachments.

**Request:**
```
POST /search/multi
{
  "search_text": "password reset fails",
  "scope": ["kb", "incidents", "attachments"],
  "filters": {
    "category": "Authentication",
    "priority": [1, 2]
  },
  "top": 3,
  "per_index": true
}
```

**Result:** Top 3 results per index (KB, incidents, attachments), combined and ranked.

---

## 6. Search Ranking Strategy

Results are ranked using **hybrid scoring** that combines:

### 6.1 BM25 Scoring (Keyword Relevance)
- TF-IDF style keyword matching
- Weights: title (2x), description (1x), content (1x)
- Case-insensitive, stemming applied

### 6.2 Vector Similarity Scoring (Semantic Relevance)
- Cosine similarity against query embedding
- Uses Azure OpenAI embeddings (text-embedding-3-small, 1536-dim)
- Semantic understanding of synonyms and intent

### 6.3 Signal-Based Boosting
| Signal | Boost | Applied To |
|---|---|---|
| `useful_count > 50` | +0.2 | KB articles |
| `view_count > 100` | +0.15 | KB articles |
| `resolution_time_minutes < 120` | +0.25 | Closed incidents (quick resolution) |
| `reopen_count == 0` | +0.15 | Closed incidents (stable resolution) |
| `updated_date > 90 days ago` | +0.1 | All (freshness) |
| `priority == 1` | +0.2 | Incidents (critical = relevant) |

### 6.4 Final Score Composition
```
final_score = (0.6 × bm25_score) + (0.4 × vector_score) + signal_boosts
```

---

## 7. Embedding Strategy

### 7.1 Embedding Generation

**Model:** Azure OpenAI `text-embedding-3-small`
- **Dimensions:** 1536
- **Batch processing:** Generated during index creation/update
- **Query embeddings:** Generated at search time

### 7.2 Content Batched for Embedding

For each document added to an index:

1. **KB articles:** title + content (concatenated, truncated to 8192 tokens)
2. **Incidents:** summary + description + work_notes + resolution_notes (concatenated)
3. **Attachments:** file_name + description (concatenated)

### 7.3 Embedding Refresh Schedule

- **Initial index population:** During Fabric ingestion
- **Incremental updates:** When incidents/KB/attachments are updated in Fabric (daily or on-demand)
- **Batch size:** 100 documents per API call (Azure OpenAI rate limits)

---

## 8. Example Retrieval Result JSON Shape

### 8.1 KB Article Result

```json
{
  "id": "kb_12345",
  "type": "kb_article",
  "title": "How to Reset a Forgotten Password",
  "snippet": "To reset a forgotten password, navigate to the login page and click on 'Forgot Password'. You will receive a password reset link via email...",
  "score": 0.87,
  "metadata": {
    "article_id": "12345",
    "category": "Authentication",
    "subcategory": "Password Management",
    "created_date": "2024-06-15T00:00:00Z",
    "updated_date": "2026-02-20T00:00:00Z",
    "view_count": 287,
    "useful_count": 156
  },
  "source": {
    "type": "kb_article",
    "url": "https://mock-servicenow.example.com/kb_article?id=12345",
    "last_updated": "2026-02-20T00:00:00Z"
  },
  "match_details": {
    "keyword_match": "password reset",
    "semantic_match": "account access recovery",
    "search_terms": ["password", "reset", "forgot"]
  }
}
```

### 8.2 Incident (Closed Ticket) Result

```json
{
  "id": "incident_INC0654321_resolution",
  "type": "incident",
  "incident_number": "INC0654321",
  "summary": "Unable to connect to company VPN from home office",
  "state": "closed",
  "snippet": "Resolution: Verified that the client's VPN certificate had expired. Generated a new certificate through the certificate management system and provided the updated configuration file to the user. User confirmed access restored.",
  "score": 0.84,
  "metadata": {
    "priority": "2",
    "category": "Connectivity",
    "subcategory": "VPN",
    "assigned_group": "Network Support Team",
    "business_service": "Remote Access",
    "created_date": "2026-01-10T14:30:00Z",
    "closed_date": "2026-01-12T09:15:00Z",
    "resolution_time_minutes": 1665,
    "reopen_count": 0
  },
  "content_included": {
    "description": true,
    "work_notes": true,
    "resolution_notes": true
  },
  "work_notes_summary": [
    "2026-01-10 15:00 - Customer reports inability to connect. Requested certificate export from client.",
    "2026-01-11 10:30 - Reviewed certificate. Confirmed expired on 2026-01-09. Generated replacement.",
    "2026-01-12 08:45 - Delivered new cert config to customer. Standby for confirmation."
  ],
  "resolution": "Certificate renewal via certificate management portal resolved the issue.",
  "source": {
    "type": "incident",
    "url": "https://mock-servicenow.example.com/incident?id=INC0654321",
    "content_type": "resolution_notes"
  },
  "attachment_references": [
    {
      "attachment_id": "attach_789",
      "file_name": "vpn_certificate_new.conf",
      "type": "document"
    }
  ]
}
```

### 8.3 Attachment Result

```json
{
  "id": "attachment_attach_999",
  "type": "attachment",
  "file_name": "error_screenshot_20260613.png",
  "file_type": "image/png",
  "description": "Screenshot showing 'Connection Timeout' error dialog from database client application",
  "score": 0.76,
  "metadata": {
    "attachment_id": "attach_999",
    "attachment_type": "screenshot",
    "incident_id": "INC0789012",
    "uploaded_date": "2026-06-13T11:22:00Z",
    "size_bytes": 256000
  },
  "source": {
    "type": "attachment",
    "incident_url": "https://mock-servicenow.example.com/incident?id=INC0789012",
    "attachment_url": "https://mock-api.example.com/attachments/attach_999/error_screenshot_20260613.png",
    "retrieval_note": "Mock URL; actual binary not stored in search index"
  }
}
```

### 8.4 Multi-Index Search Result (Combined)

```json
{
  "query": "database connection timeout",
  "search_time_ms": 145,
  "results": {
    "kb_articles": [
      {
        "id": "kb_12345",
        "type": "kb_article",
        "title": "Troubleshooting Database Connection Issues",
        "score": 0.91,
        "url": "https://mock-servicenow.example.com/kb_article?id=12345"
      }
    ],
    "incidents": [
      {
        "id": "incident_INC0654321_resolution",
        "incident_number": "INC0654321",
        "summary": "Database timeout in production environment",
        "score": 0.88,
        "state": "closed",
        "url": "https://mock-servicenow.example.com/incident?id=INC0654321"
      },
      {
        "id": "incident_INC0445566_resolution",
        "incident_number": "INC0445566",
        "summary": "Intermittent connection timeout to reporting database",
        "score": 0.85,
        "state": "closed",
        "url": "https://mock-servicenow.example.com/incident?id=INC0445566"
      }
    ],
    "attachments": [
      {
        "id": "attachment_attach_999",
        "file_name": "database_error_log_20260613.log",
        "type": "attachment",
        "score": 0.79,
        "incident_id": "INC0654321",
        "url": "https://mock-api.example.com/attachments/attach_999/database_error_log.log"
      }
    ]
  }
}
```

---

## 9. Orchestrator Integration Points

The Foundry orchestrator calls the retrieval system at these points:

### 9.1 Intent Detection

```
User: "We've been seeing database timeouts in production. Have we seen this before?"

→ Orchestrator intent: HISTORICAL_SIMILARITY_SEARCH
  ├─ Extract keywords: ["database", "timeout", "production"]
  ├─ Inferred context: [category: "Database", priority: high]
  └─ Call retrieval → incident-content-index with closed tickets
```

### 9.2 Orchestrator Request Pattern

```python
# Pseudocode
def search_similar_incidents(user_query, context):
    results = retrieval_client.hybrid_search(
        index="incident-content-index",
        query=user_query,
        filters={
            "incident_state": "closed",
            "category": context.get("category", None),
            "priority_lte": 2  # critical/high
        },
        top=5
    )
    return format_for_answer_composition(results)
```

### 9.3 Result Grounding

Every retrieval result includes:
- **source_url**: Direct link to source incident/KB/attachment in mock ServiceNow
- **match_details**: Why this result matched (keyword vs. semantic)
- **metadata**: Relevant context (category, priority, resolution time, etc.)

The orchestrator uses these to compose grounded answers:

```
Answer: "We've resolved similar issues before. Incident INC0654321 
had the same symptoms and was resolved by certificate renewal 
(see resolution here: [URL]). Check the attached configuration 
file [attach_999] for the steps taken."
```

---

## 10. Deployment Considerations

### 10.1 Azure AI Search Configuration

**Service SKU:** Standard (sufficient for POC, scales to Premium for production)

**Index capacity:**
- Expected documents: ~10,000 KB articles + 50,000 incidents + 25,000 attachments = 85,000 total
- With semantic search: ~2 GB total storage
- Batch size for indexing: 100 documents per request

**Scheduling:**
- Initial indexing during Fabric ingestion setup
- Incremental updates: Triggered when Fabric data changes (daily or on-demand)
- Embedding refresh: Daily batch job or event-driven

### 10.2 Embedding Model Configuration

**Model:** `text-embedding-3-small` (Azure OpenAI)
- **Quota:** Reserve API quota for batch embedding during initial load
- **Cost:** ~0.02 USD per 1M tokens; POC budget: ~$0.05-0.10 for full indexing
- **Latency:** <100ms per embedding for queries

### 10.3 Access Control

- Retrieval API behind Azure API Management (if productionized)
- Foundry orchestrator authenticated via Managed Identity
- No direct user access to retrieval API (only through orchestrator)

---

## 11. Validation and Success Criteria

### 11.1 Index Health

- [ ] KB article index contains 100% of KB articles from Fabric
- [ ] Incident index contains 100% of closed incidents and recent open incidents
- [ ] Attachment index contains metadata for all attachments
- [ ] All embeddings generated successfully
- [ ] No documents with "empty_vector" error

### 11.2 Search Quality

- [ ] Keyword search returns relevant results in top 3 (BM25 precision)
- [ ] Vector search returns semantically similar results (synonym matching)
- [ ] Hybrid search outperforms keyword-only for 80%+ of queries
- [ ] Metadata filters work correctly (no false positives)
- [ ] Results ranked by combined score show sensible ordering

### 11.3 Performance

- [ ] Query latency <500ms for top-10 results
- [ ] Batch indexing completes 10,000 documents in <5 min
- [ ] No timeouts or quota errors under normal load

### 11.4 Grounding

- [ ] Every result includes source_url
- [ ] Every result includes relevant metadata
- [ ] Orchestrator can compose grounded answers with references
- [ ] No retrieval results missing links back to source

---

## 12. Future Enhancements

Beyond the POC:

1. **Personalization:** Boost results for the user's team/category
2. **Recency decay:** Lower scores for very old tickets
3. **AI-extracted tags:** Auto-generate resolution tags, symptom tags for better grouping
4. **Feedback loop:** Track which retrieved results led to ticket resolution, improve ranking
5. **Cross-language support:** If Autoliv spans multiple regions
6. **Real-time indexing:** Stream updates from ServiceNow API (webhooks) instead of batch
7. **Semantic reranking:** Second-pass ranking with a cross-encoder model
8. **Entity extraction:** Extract root cause, impacted service, affected users and index as entities

---

## 13. Summary and Next Steps

### Index Schema
- **kb-articles-index:** Title, content, category, metadata, embeddings
- **incident-content-index:** Description, work notes, resolution notes, metadata, embeddings
- **attachments-index:** File name, description, attachment type, metadata

### Metadata Filters
- Category, subcategory, priority, state, date ranges, attachment type, assignment group

### Retrieval Patterns
1. Similarity search for closed tickets
2. KB article search by topic
3. Open follow-up ticket search
4. Attachment search by metadata
5. Multi-index comprehensive search

### Result Shape
- Each result includes ID, snippet, score, metadata, and source URL
- Results ranked by hybrid score (60% BM25 + 40% vector + signals)
- All results grounded with links back to ServiceNow sources

### Next Actions
1. ✅ Design approved
2. ⬜ Create Python/C# indexing scripts to populate indexes from Fabric tables
3. ⬜ Implement search API (FastAPI or Azure Functions)
4. ⬜ Test hybrid search quality with sample queries
5. ⬜ Connect Foundry orchestrator to search API
6. ⬜ Validate end-to-end: user query → retrieval → grounded answer

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-17  
**Maintained By:** Jayne, Search/Retrieval Specialist
