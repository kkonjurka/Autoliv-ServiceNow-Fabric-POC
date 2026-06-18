# Inara — History

## Project Context
- **Project:** Autoliv ServiceNow to Microsoft Fabric POC
- **Stack:** Microsoft Fabric, Dataflow Gen2, Spark notebooks
- **User:** @kkonjuramicrosoft

## Learnings

- 2026-06-18T15:58:22.510-04:00: Fabric Git integration for this POC should sync from the repo subfolder `servicenow-demo/`, where each workspace item lives in native `<ItemName>.<ItemType>` folders with `.platform` metadata.
- 2026-06-18T15:58:22.510-04:00: The Fabric-synced notebooks are `servicenow-demo/01_Ingest_Raw.Notebook`, `servicenow-demo/02_Transform_Curated.Notebook`, and `servicenow-demo/03_HTML_to_Text.Notebook`, and the attached Lakehouse placeholder is `servicenow-demo/ServiceNow_Lakehouse.Lakehouse`.
- 2026-06-18T15:58:22.510-04:00: Default ServiceNow ingestion should target the live ACA mock API at `https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io` so the synced notebook runs without manual endpoint edits.
- 2026-06-17: Land raw mock ServiceNow payloads in the Lakehouse first, then normalize from `/incidents/{id}` detail plus paginated asset and KB endpoints into curated Delta tables.
- 2026-06-17: Keep semantic-model tables relational and isolated from long-form retrieval text by publishing a separate `retrieval_documents` corpus with source IDs and metadata.


## Session Update (2026-06-17T18-52-27Z)

Kaylee's API schema available at mock-servicenow-api/app/database.py for Fabric integration

