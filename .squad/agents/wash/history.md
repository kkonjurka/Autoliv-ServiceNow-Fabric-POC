# Wash — History

## Project Context
- **Project:** Autoliv ServiceNow to Microsoft Fabric POC
- **Stack:** Docker, Azure Container Apps, Azure CLI
- **User:** @kkonjuramicrosoft

## Learnings
- 2026-06-24T10:19:26.351-04:00: Added a Fabric Git integration DataPipeline item that runs 00_API_Demo -> 01_Ingest_Raw -> 02_Transform_Curated with success-only dependencies and blank notebook/workspace IDs for Fabric name resolution.
- 2026-06-17T15:01:54.176-04:00: Added Azure Container Apps deployment assets for the mock ServiceNow API, including a multi-stage Dockerfile, ACR/ACA deployment scripts, and deployment documentation.
- 2026-06-17T15:01:54.176-04:00: ACA deployments intentionally reseed the bundled SQLite database at startup so generated mock asset URLs match the live HTTPS Container App hostname.


## Session Update (2026-06-17T18-52-27Z)

Deployment verified LIVE at ACA endpoint

