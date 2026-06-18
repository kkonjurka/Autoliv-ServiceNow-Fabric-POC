# Foundry Multi-Agent Orchestration Design

Date: 2026-06-17T14:52:27-04:00

## Purpose

Design a Foundry orchestration pattern for the POC that keeps structured, unstructured, and attachment-heavy retrieval on separate paths. The orchestrator is responsible for intent understanding, tool selection, result fusion, and grounded answer generation; it is not the system of record for all data.

## Design Principles

1. Keep the architecture multi-agent and multi-system.
2. Route structured questions to the Fabric Data Agent, not to search.
3. Route KB/work-note/resolution-note retrieval to search/vector retrieval, not to the semantic model.
4. Route documents, screenshots, logs, scripts, and attachment metadata to a dedicated attachment tool path.
5. Require citations, source IDs, and confidence signaling in every final answer.
6. Separate observed facts from suggested next actions.

## Reference Pattern

```text
User
  |
  v
Foundry Orchestrator Agent
  |-- Tool 1: Fabric Data Agent query path
  |      -> Deployed Fabric Data Agent
  |      -> Fabric semantic model / curated structured tables
  |
  |-- Tool 2: Search / vector retrieval path
  |      -> Azure AI Search or equivalent retrieval layer
  |      -> KB articles, work notes, resolution notes, cleaned HTML, similar tickets
  |
  |-- Tool 3: Document / image / attachment path
         -> Attachment metadata service / document summarizer / image descriptor
         -> URLs, logs, scripts, screenshots, document summaries
```

## Agent Responsibility Matrix

| Component | Primary responsibility | Inputs | Outputs | Must not own |
| --- | --- | --- | --- | --- |
| Foundry Orchestrator Agent | Detect intent, choose tool path, merge evidence, produce grounded response | User question, conversation context, tool results | Final answer with citations, confidence, escalation guidance | Direct semantic reasoning over raw structured data, monolithic retrieval over all stores |
| Fabric Data Agent | Answer structured operational questions over semantic model data | Natural-language question, optional filters | Open ticket lists, SLA state, priority/category summaries, counts, semantic-model facts | KB/article retrieval, attachment inspection |
| Search / vector retrieval | Retrieve similar incidents and unstructured support content | Query text, ticket context, issue terms | Similar tickets, KBs, work notes, resolution notes, cleaned HTML excerpts | SLA/backlog rollups, attachment metadata |
| Document / image / attachment tool path | Retrieve non-tabular evidence and references | Ticket IDs, related ticket IDs, keywords, asset filters | Attachment metadata, image descriptions, document summaries, log/script references, URLs | Semantic-model aggregation, similarity ranking over general text corpus |
| Human support reviewer | Approve actions and validate suggestions before execution | Grounded answer, cited evidence | Final human decision | Automated final change approval |

## Tool Routing Logic

### Intent-to-tool routing

| User intent | Primary path | Secondary path | Orchestrator behavior |
| --- | --- | --- | --- |
| Open tickets, SLA, backlog, priority, category, aging, trends | Fabric Data Agent | None unless user asks for supporting notes | Call Fabric first and summarize directly |
| Similar incidents, prior fixes, work notes, resolution notes, cleaned HTML | Search / vector retrieval | Fabric if status/priority context is also needed | Search first, then optionally cross-check current ticket facts in Fabric |
| KBs, documents, known issue guidance | Search / vector retrieval | Attachment path for linked docs/files | Retrieve text evidence, then fetch referenced assets if needed |
| Screenshots, logs, scripts, attachments, URLs | Document / image / attachment path | Search if user also wants context from notes | Fetch asset metadata and summarize only what the tool returns |
| Suggested resolution | Fabric + Search at minimum | Attachment path when evidence includes logs/scripts/screenshots | Gather evidence first, then draft a recommendation with confidence and human-review wording |

### Orchestration sequence

1. Classify the request into one or more evidence classes: structured, unstructured, asset-based, or recommendation.
2. Call the minimum required tool set.
3. If the question asks for a recommendation, require at least two grounded evidence sources unless the answer is purely tabular.
4. Normalize outputs into a shared citation model: `source_type`, `source_id`, `title`, `snippet`, `url`, `confidence`.
5. Compose the answer in this order:
   - direct answer
   - supporting evidence
   - references
   - confidence / review note
6. If evidence conflicts, say so explicitly and prefer the freshest authoritative source.

### Routing heuristics

- Use the Fabric path when the request contains words like `open`, `high priority`, `SLA`, `backlog`, `category`, `count`, `aging`, or `follow-up`.
- Use search when the request contains `similar`, `historical`, `resolved`, `knowledge article`, `KB`, `work note`, `resolution note`, or `how was this fixed`.
- Use the attachment path when the request contains `attachment`, `document`, `screenshot`, `image`, `log`, `script`, or `file`.
- Use multi-tool routing when the user asks for both operational facts and suggested action.

## Example System Instructions for the Orchestrator

```text
You are the Autoliv support orchestration agent in Azure AI Foundry.

Your job is to decide which specialized system should answer each part of the user's request:
- Use the Fabric Data Agent for structured ticket, SLA, priority, category, backlog, and semantic-model questions.
- Use search/vector retrieval for KB articles, work notes, resolution notes, cleaned HTML content, and similar historical tickets.
- Use the attachment tool path for screenshots, logs, scripts, documents, image descriptions, attachment metadata, and URLs.

Rules:
1. Do not answer from memory when a tool can provide evidence.
2. Do not treat search results as authoritative for structured counts or SLA rollups.
3. Do not treat semantic-model answers as evidence for document or attachment contents.
4. Prefer the smallest set of tool calls that can fully answer the request.
5. When composing a recommendation, separate facts, inferred pattern, and suggested next steps.
6. Cite every material claim with source identifiers or URLs.
7. If evidence is weak, conflicting, or missing, say so and recommend human review.
8. Never imply that a suggestion has been executed; you only recommend.

Final answer format:
- Answer
- Evidence
- References
- Confidence / human review
```

## Example Tool / Function Contracts

The orchestrator should interact with three callable tool contracts. The underlying runtime can map them to Foundry A2A, `fabric_iq_preview`, Azure AI Search, OpenAPI, MCP, or client-side function execution as needed.

### 1. `query_fabric_data_agent`

```json
{
  "name": "query_fabric_data_agent",
  "description": "Ask the deployed Fabric Data Agent about structured ticket and semantic-model questions.",
  "parameters": {
    "type": "object",
    "properties": {
      "question": {
        "type": "string",
        "description": "Natural-language question for the Fabric Data Agent."
      },
      "filters": {
        "type": "object",
        "description": "Optional structured filters such as priority, status, category, assignee group, or date range.",
        "additionalProperties": {
          "type": ["string", "number", "boolean"]
        }
      },
      "max_rows": {
        "type": "integer",
        "minimum": 1,
        "maximum": 50,
        "default": 10
      }
    },
    "required": ["question"],
    "additionalProperties": false
  },
  "returns": {
    "type": "object",
    "properties": {
      "answer_text": { "type": "string" },
      "rows": { "type": "array" },
      "citations": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "source_type": { "type": "string", "enum": ["fabric_data_agent", "semantic_model", "curated_table"] },
            "source_id": { "type": "string" },
            "title": { "type": "string" }
          },
          "required": ["source_type", "source_id"]
        }
      },
      "confidence": { "type": "number" }
    },
    "required": ["answer_text", "citations", "confidence"]
  }
}
```

### 2. `search_support_knowledge`

```json
{
  "name": "search_support_knowledge",
  "description": "Retrieve similar tickets, KB articles, work notes, resolution notes, and cleaned HTML content.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Issue description or search query."
      },
      "ticket_id": {
        "type": "string",
        "description": "Optional current ticket identifier."
      },
      "content_types": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["similar_ticket", "kb_article", "work_note", "resolution_note", "cleaned_html"]
        }
      },
      "top_k": {
        "type": "integer",
        "minimum": 1,
        "maximum": 20,
        "default": 5
      }
    },
    "required": ["query"],
    "additionalProperties": false
  },
  "returns": {
    "type": "object",
    "properties": {
      "results": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "source_type": { "type": "string" },
            "source_id": { "type": "string" },
            "title": { "type": "string" },
            "snippet": { "type": "string" },
            "url": { "type": "string" },
            "score": { "type": "number" }
          },
          "required": ["source_type", "source_id", "snippet"]
        }
      },
      "confidence": { "type": "number" }
    },
    "required": ["results", "confidence"]
  }
}
```

### 3. `get_ticket_assets`

```json
{
  "name": "get_ticket_assets",
  "description": "Retrieve attachment metadata, image descriptions, document summaries, logs, scripts, and URLs related to a ticket or issue.",
  "parameters": {
    "type": "object",
    "properties": {
      "ticket_id": {
        "type": "string"
      },
      "related_ticket_ids": {
        "type": "array",
        "items": { "type": "string" }
      },
      "asset_types": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["attachment", "document", "image", "screenshot", "log", "script", "url"]
        }
      },
      "keywords": {
        "type": "array",
        "items": { "type": "string" }
      },
      "top_k": {
        "type": "integer",
        "minimum": 1,
        "maximum": 20,
        "default": 10
      }
    },
    "required": ["ticket_id"],
    "additionalProperties": false
  },
  "returns": {
    "type": "object",
    "properties": {
      "assets": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "asset_id": { "type": "string" },
            "asset_type": { "type": "string" },
            "title": { "type": "string" },
            "summary": { "type": "string" },
            "url": { "type": "string" },
            "related_ticket_id": { "type": "string" }
          },
          "required": ["asset_id", "asset_type"]
        }
      },
      "confidence": { "type": "number" }
    },
    "required": ["assets", "confidence"]
  }
}
```

## End-to-End Conversation Flows

### Scenario 1: Similar historical tickets and how they were resolved

1. User: "Find similar historical tickets for VPN timeout errors and summarize how they were resolved."
2. Orchestrator classifies as unstructured retrieval with summarization.
3. Orchestrator calls `search_support_knowledge` with `content_types=["similar_ticket","resolution_note","work_note"]`.
4. Search returns top similar incidents and resolution excerpts.
5. Orchestrator groups common fixes, cites ticket IDs, and states the dominant resolution pattern.

Why this route: resolution history lives primarily in notes and KB-style content, not in semantic aggregates.

### Scenario 2: Open high-priority tickets that need follow-up

1. User: "Show open high-priority tickets that need follow-up."
2. Orchestrator classifies as structured operational analysis.
3. Orchestrator calls `query_fabric_data_agent` with filters like `status=open`, `priority=high`, and follow-up criteria.
4. Fabric Data Agent returns rows, counts, owners, age, and SLA context.
5. Orchestrator answers with the ticket list, highlights overdue items, and cites the semantic source.

Why this route: the semantic model is the authoritative source for current operational state.

### Scenario 3: KB articles, documents, and attachments for a specific issue

1. User: "Retrieve KB articles and documents for SAP login failures, and include any related screenshots or logs."
2. Orchestrator classifies as mixed retrieval.
3. Orchestrator calls `search_support_knowledge` for KBs and related notes.
4. Orchestrator calls `get_ticket_assets` for documents, screenshots, and logs tied to matching tickets.
5. Orchestrator returns a grouped answer: KB articles first, then related documents/assets with URLs.

Why this route: text evidence and attachment evidence come from different stores and should stay separated until the final response.

### Scenario 4: Grounded suggested resolution with references

1. User: "Based on this open ticket, suggest a likely resolution and include references."
2. Orchestrator calls `query_fabric_data_agent` to confirm current ticket state, priority, ownership, and SLA risk.
3. Orchestrator calls `search_support_knowledge` to find similar resolved incidents, KBs, and resolution notes.
4. If logs, scripts, or screenshots are mentioned, orchestrator calls `get_ticket_assets`.
5. Orchestrator drafts:
   - confirmed current facts
   - most likely resolution pattern
   - recommended next steps
   - explicit confidence level
   - human review note
   - references

Why this route: recommendations must be grounded in both current structured state and historical evidence.

## Guardrails for Grounding, Confidence, and Human Review

### Grounding

- Every material claim must cite at least one source ID or URL.
- Use Fabric citations for structured facts and search/asset citations for supporting evidence.
- Do not convert weak semantic similarity into fact; label it as a similar case or supporting pattern.
- If no supporting evidence is found, say that directly instead of fabricating a likely answer.

### Confidence

- High confidence: structured answer from Fabric or multiple converging historical results.
- Medium confidence: one strong retrieval pattern plus partial structured confirmation.
- Low confidence: sparse, conflicting, or stale evidence.
- Final answers should expose confidence in plain language, not only numeric form.

### Human review

- Any suggested resolution must be framed as a recommendation for analyst review.
- Do not imply approval to close a ticket, change production configuration, or contact a customer automatically.
- Surface ambiguity when multiple categories/issues overlap.
- Escalate to human review when:
  - confidence is low
  - the current ticket has no close historical match
  - evidence conflicts across systems
  - the issue involves security, safety, regulated workflows, or missing attachments

## Foundry Mapping Notes

- Recommended orchestrator type: Foundry prompt agent.
- Fabric path mapping: A2A call to the deployed Fabric Data Agent, or a `fabric_iq_preview` wrapper when that is the deployment standard.
- Search path mapping: Azure AI Search vector-semantic hybrid retrieval or equivalent retrieval service.
- Asset path mapping: OpenAPI, MCP, or client-side function tool wrapping the document/image/attachment service.

## Counts for this design

- Agent count: 2
- Tool count: 3
- Scenario count: 4
