# Wash decision inbox: Fabric pipeline structure

- **Date:** 2026-06-24T10:19:26.351-04:00
- **Owner:** Wash
- **Status:** Proposed for team review

## Decision

Represent the Fabric orchestration asset as `servicenow-demo/ServiceNow_Pipeline.DataPipeline/` and have it execute `00_API_Demo` -> `01_Ingest_Raw` -> `02_Transform_Curated` using `TridentNotebook` activities with `Succeeded` dependencies.

## Why

1. The pipeline maps cleanly to the existing Fabric Git integration folder convention already used for notebooks and the Lakehouse.
2. Success-only dependencies provide the required failure handling without custom branching.
3. Keeping `notebookId` and `workspaceId` blank lets Fabric bind notebook references by name after the workspace sync.

## Impact

1. Fabric users can run the main end-to-end notebook flow from one pipeline item.
2. The API smoke test is included up front and blocks ingestion when connectivity validation fails.
3. `03_HTML_to_Text` stays out of the main pipeline because its logic is already inlined into `02_Transform_Curated`.
