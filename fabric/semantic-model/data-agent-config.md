# Fabric Data Agent Configuration Guidance

**Owner:** Book, Semantic Modeler  
**Date:** 2026-06-17T15:02:35.115-04:00

## 1. Purpose

Point the Fabric Data Agent at the published semantic model for structured operational ticket questions. The Data Agent should answer backlog, SLA, priority, category, support-group, service, KB reuse, and resolution-pattern questions without touching raw landing tables.

## 2. Recommended setup flow

1. Publish the semantic model built from `fabric/semantic-model/model.tmdl`.
2. Certify or mark the model as the approved business layer for the POC workspace.
3. Expose friendly dimensions and measures only; hide surrogate keys, bridge-table internals, and long HTML/text columns.
4. Add column and measure descriptions before enabling the Data Agent.
5. Test the agent with representative operational questions from support users.

## 3. Semantic objects to expose

### Primary dimensions

- Date
- User / Requester
- Assignment Group
- Category / Subcategory
- Business Service / Application
- Priority
- State / Status
- Resolution Code
- Knowledge Article
- Attachment / Document Type
- Resolution Pattern

### Preferred measures

- Ticket Volume
- Open Ticket Count
- Backlog by Priority
- Avg Resolution Time (Hours)
- SLA Breach Count
- Reopen Rate
- Aging Open Tickets
- Resolution Pattern Frequency
- KB Article Reuse Count

## 4. Synonyms and descriptions

| Semantic object | Add synonyms | Description to expose |
| --- | --- | --- |
| `Ticket Volume` | incidents, ticket count, case volume | Total tickets in the current filters |
| `Open Ticket Count` | active tickets, unresolved tickets, backlog | Tickets currently in open operational states |
| `Assignment Group` | support team, resolver group | Group currently responsible for ticket handling |
| `Business Service` | application, platform, supported service | Service or application impacted by the ticket |
| `Category` | issue type, domain | Top-level support classification |
| `Resolution Pattern` | fix pattern, remediation pattern | Canonical resolution approach derived from closed-ticket notes |
| `KB Article Reuse Count` | KB usage, article usage | Number of tickets linked to KB articles |

## 5. Allowed and blocked question domains

### Allowed

- Open ticket counts and backlog summaries
- Trends by date, category, group, service, state, and priority
- SLA breach counts
- Resolution time summaries
- KB reuse and resolution-pattern frequency
- Ticket aging by open-age bucket

### Blocked or routed elsewhere

- Full-text retrieval from KB articles, work notes, or resolution notes
- Similar-incident narrative search
- Attachment/document/image content understanding
- Free-form troubleshooting recommendations without structured evidence

Route blocked domains to search/vector retrieval or the attachment/document path.

## 6. Example agent instructions

```text
You answer only structured questions over the approved Fabric semantic model for the Autoliv ServiceNow POC.

Use the semantic model's published dimensions and measures for ticket operations, SLA, backlog, category, support-group, service, KB reuse, and resolution-pattern questions.

Rules:
1. Prefer measures over row-level reasoning.
2. If the question asks for long-form note content, attachments, screenshots, logs, or documents, return that the request should go to retrieval or the asset tool path.
3. If a measure is marked preview, say so explicitly.
4. Summaries should name the applied filters when they materially change the answer.
5. Do not invent ticket relationships that are not present in the model.
```

## 7. Example test prompts

1. How many open critical tickets are assigned to Network Operations?
2. What is the average resolution time for Database incidents this week?
3. Which business services had the most SLA breaches this month?
4. Which KB articles are reused most often for Operations tickets?
5. What resolution patterns appear most often for Identity incidents?
6. Show backlog by priority for the Data Platform group.

## 8. Deployment notes

1. Keep the semantic model small and business-labeled for the POC.
2. Prefer stable measure names; Fabric Data Agent quality depends heavily on naming and descriptions.
3. Revalidate the agent whenever measure definitions, state mapping, or bridge logic changes.
