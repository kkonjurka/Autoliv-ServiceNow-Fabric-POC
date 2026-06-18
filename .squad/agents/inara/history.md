# Inara — History

## Project Context
- **Project:** Autoliv ServiceNow to Microsoft Fabric POC
- **Stack:** Microsoft Fabric, Dataflow Gen2, Spark notebooks
- **User:** @kkonjuramicrosoft

## Learnings
- 2026-06-17: Land raw mock ServiceNow payloads in the Lakehouse first, then normalize from `/incidents/{id}` detail plus paginated asset and KB endpoints into curated Delta tables.
- 2026-06-17: Keep semantic-model tables relational and isolated from long-form retrieval text by publishing a separate `retrieval_documents` corpus with source IDs and metadata.


## Session Update (2026-06-17T18-52-27Z)

Kaylee's API schema available at mock-servicenow-api/app/database.py for Fabric integration

