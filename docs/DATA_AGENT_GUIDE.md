# Fabric Data Agent Guide

## 1. Create the Data Agent in Fabric

1. Publish or sync the semantic model at `servicenow-demo\ServiceNow_SemanticModel.SemanticModel` into the Fabric workspace.
2. In the Fabric portal, open the target workspace and confirm `ServiceNow_SemanticModel` is visible and refreshable.
3. Select **New** > **AI** > **Data agent**.
4. Name the agent something explicit such as `ServiceNow Operations Agent`.
5. Choose **ServiceNow_SemanticModel** as the structured data source.
6. In the source-selection step, keep the agent scoped to business-friendly objects:
   - Tables: `incidents`, `slas`, `categories`, `assignment_groups`, `kb_articles`, `incident_kb_links`
   - Measures: `Ticket Volume`, `Open Ticket Count`, `Backlog by Priority`, `Average Resolution Time`, `SLA Breach Count`, `Aging Open Tickets`
7. Hide technical fields that are not useful in natural-language responses unless they help with grounding (`incident_id`, `assignment_group_id`, `category_id`, `kb_article_id`).
8. Add synonyms during setup:
   - incidents = tickets, cases
   - assignment group = support group, resolver group, team
   - category = topic, issue type
   - KB article = knowledge article, runbook, article
   - SLA breach = missed SLA, breach, overdue SLA
9. Save the agent and run a quick validation prompt before sharing it.

## 2. Recommended grounding setup

Use the semantic model as the primary grounding source for structured answers.

Recommended settings:

- **Primary source:** `ServiceNow_SemanticModel`
- **Default response scope:** current filter context only; do not invent filters
- **Grounding preference:** measures first, then dimension attributes, then supporting IDs/names
- **Detail behavior:** include assignment group, category, priority, and date context whenever the answer depends on them
- **Fallback behavior:** if the question needs long-form note or KB text, hand off to retrieval content rather than fabricating from the semantic model

## 3. Suggested system instructions / prompt

Use a system prompt similar to this:

> You are the ServiceNow Operations Data Agent for the Autoliv Fabric POC. Answer only from the published semantic model `ServiceNow_SemanticModel`. Prefer business-friendly names over technical keys. Use model measures when possible. Be explicit about filters, time windows, priorities, assignment groups, and categories used in the answer. If the semantic model does not contain the requested long-form narrative or evidence, say so and recommend the retrieval or ontology path instead of guessing. Keep answers concise, structured, and grounded.

Optional tone add-on:

> When returning tables, sort by the most operationally important value first (for example highest open count, highest breach rate, or oldest aging ticket).

## 4. Response formatting guidance

Recommended response format:

1. **Direct answer** — one sentence with the main result.
2. **Breakdown** — short bullet list or compact table when grouped by assignment group, category, or priority.
3. **Filters used** — state open-state logic, date range, or priority filter when relevant.
4. **Follow-up hint** — suggest a next analytical slice if helpful.

Example formatting rule:

- Counts and rates: round to whole numbers or one decimal place.
- Duration metrics: return hours with one decimal place.
- Top-N outputs: default to 5 unless the user asks otherwise.
- Aging lists: include incident number, short description, priority, assignment group, and age.

## 5. Example questions the agent should handle

- How many open incidents are assigned to the Network Support group?
- What is the average resolution time for Priority 1 incidents?
- Show me the SLA breach rate by assignment group.
- Which categories have the most open tickets?
- List aging high-priority tickets not updated in 3 days.

## 6. Configuration notes for those example questions

| Question type | Semantic-model behavior |
| --- | --- |
| Open ticket counts | Use `Open Ticket Count` filtered by assignment group, category, or priority. |
| Resolution duration | Use `Average Resolution Time` and make the incident priority filter explicit. |
| SLA breach rate | Use `SLA Breach Count` with grouped assignment-group context; if you add a denominator later, expose a breach-rate measure too. |
| Category backlog | Use `Backlog by Priority` or `Open Ticket Count` with `categories[name]` and `categories[subcategory]`. |
| Aging ticket lists | Use open-state filters plus aging logic; if “not updated in 3 days” is required, extend the semantic model with an `updated_at` field or a dedicated stale-ticket measure before promising exact answers. |

## 7. Recommended publishing checklist

1. Confirm the semantic model relationships are active and resolve cleanly in Fabric.
2. Validate the six core measures with manual spot checks.
3. Add descriptions to tables, columns, and measures before exposing the model to the agent.
4. Test each sample question in preview.
5. Verify the agent refuses unsupported narrative/evidence requests and redirects to retrieval or ontology assets.
6. Share the agent only after one analyst and one support user both confirm the wording is business-friendly.
