# Work Routing

How to decide who handles what.

## Routing Table

| Work Type | Route To | Examples |
|-----------|----------|----------|
| Architecture, scope, work breakdown | Mal | Design decisions, implementation plans, trade-offs, code review |
| Mock API, SQLite schema, seed data | Kaylee | API endpoints, database schema, mock data generation |
| Containerization, Azure deployment | Wash | Dockerfile, Azure Container Apps, CI/CD, infra config |
| Fabric ingestion, data transforms | Inara | Lakehouse tables, Dataflow Gen2, HTML-to-text, data dictionary |
| Semantic model, ontology, Data Agent | Book | Dimensions, measures, ontology nodes, Fabric Data Agent config |
| Multi-agent orchestration, Foundry | River | Orchestrator prompts, tool contracts, agent routing logic |
| Search, retrieval, KB, documents | Jayne | Search index, vector retrieval, document/image/attachment path |
| Testing, validation, demo scripts | Zoe | Smoke tests, validation plans, demo verification |
| Documentation, storytelling | Simon | Executive summary, demo narrative, client materials |
| Code review | Mal, Zoe | Review PRs, check quality, suggest improvements |
| Scope & priorities | Mal | What to build next, trade-offs, decisions |
| Session logging | Scribe | Automatic — never needs routing |

## Issue Routing

| Label | Action | Who |
|-------|--------|-----|
| `squad` | Triage: analyze issue, assign `squad:{member}` label | Lead |
| `squad:{name}` | Pick up issue and complete the work | Named member |

### How Issue Assignment Works

1. When a GitHub issue gets the `squad` label, the **Lead** triages it — analyzing content, assigning the right `squad:{member}` label, and commenting with triage notes.
2. When a `squad:{member}` label is applied, that member picks up the issue in their next session.
3. Members can reassign by removing their label and adding another member's label.
4. The `squad` label is the "inbox" — untriaged issues waiting for Lead review.

## Rules

1. **Eager by default** — spawn all agents who could usefully start work, including anticipatory downstream work.
2. **Scribe always runs** after substantial work, always as `mode: "background"`. Never blocks.
3. **Quick facts → coordinator answers directly.** Don't spawn an agent for "what port does the server run on?"
4. **When two agents could handle it**, pick the one whose domain is the primary concern.
5. **"Team, ..." → fan-out.** Spawn all relevant agents in parallel as `mode: "background"`.
6. **Anticipate downstream work.** If a feature is being built, spawn the tester to write test cases from requirements simultaneously.
7. **Issue-labeled work** — when a `squad:{member}` label is applied to an issue, route to that member. The Lead handles all `squad` (base label) triage.
