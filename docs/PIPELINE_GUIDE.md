# Fabric pipeline guide

## What was added

This repo now includes a Fabric Git integration pipeline item at `servicenow-demo/ServiceNow_Pipeline.DataPipeline/`.

The pipeline runs these notebooks in order:

1. `00_API_Demo` (optional validation step included in the pipeline)
2. `01_Ingest_Raw`
3. `02_Transform_Curated`

`02_Transform_Curated` only runs when ingestion succeeds, and ingestion only runs when the API validation step succeeds.

## How to use it in Fabric

1. Sync the `servicenow-demo` Git folder into the `servicenow-demo` Fabric workspace.
2. Confirm the workspace shows the new `ServiceNow_Pipeline` pipeline item.
3. Open the pipeline and verify Fabric resolved the notebook references by name.
4. Attach `ServiceNow_Lakehouse` to the notebooks if that has not already been done.
5. Run `ServiceNow_Pipeline` for the end-to-end flow.

## Notes

- The pipeline JSON intentionally leaves `workspaceId` and `notebookId` blank because Fabric resolves notebook references after sync.
- If `00_API_Demo` fails, the pipeline stops before ingestion.
- `03_HTML_to_Text` is not part of the main pipeline because its helper logic is already inlined into `02_Transform_Curated`.
