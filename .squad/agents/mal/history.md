# Mal — History

## Project Context
- **Project:** Autoliv ServiceNow to Microsoft Fabric POC
- **Stack:** SQLite, Azure Container Apps, Microsoft Fabric, Fabric Data Agent, Azure AI Foundry
- **User:** @kkonjuramicrosoft

## Learnings
- 2026-06-17T14:52:27-04:00: The POC architecture should enforce three answer paths: Fabric Data Agent for structured questions, retrieval for cleaned KB/work-note/resolution text, and a separate metadata-first attachment/document/image path.
- 2026-06-17T14:52:27-04:00: Treat the SQLite-backed API and Azure Container Apps deployment as the mock source-system boundary, while Fabric curated tables become the authoritative demo data layer.
- 2026-06-17T14:52:27-04:00: Key planning artifacts are `docs/ARCHITECTURE.md` and `.squad/decisions/inbox/mal-architecture-plan.md`.


## Session Update (2026-06-17T18-52-27Z)

All agents completed outputs; architecture validated against deliverables

