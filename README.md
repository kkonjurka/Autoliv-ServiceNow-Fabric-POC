# Autoliv ServiceNow to Microsoft Fabric POC

## Overview

This proof of concept demonstrates how Autoliv ServiceNow data can be deployed into Microsoft Fabric and shaped into a Fabric semantic model, ontology layer, Fabric Data Agent, and multi-agent Foundry architecture for AI-assisted ticket resolution.

The POC uses a mock ServiceNow connector implemented as an API backed by SQLite. SQLite is only a stand-in for ServiceNow API data during the demo. The target production direction is direct ServiceNow API ingestion into Fabric, with an interim option to reuse Snowflake or mirrored Fabric Delta tables if required.

## Confirmed deployment scope

This POC is intended to deploy actual data assets into Microsoft Fabric, not just produce local "Fabric-style" files.

Confirmed Fabric deliverables:

1. A Fabric workspace for the POC.
2. A Fabric Lakehouse or Warehouse that stores the ingested mock ServiceNow data.
3. Curated Fabric tables for incidents, users, groups, categories, KB articles, work notes, resolution notes, changes, SLAs, attachments, images, documents, and references.
4. A Fabric semantic model built over the curated structured tables.
5. An ontology layer built from the semantic model/business entities.
6. A Fabric Data Agent connected to the semantic model or curated Fabric data.
7. Supporting retrieval/index assets for unstructured text and attachment/document/image metadata.
8. A Foundry orchestrator agent that references the Fabric Data Agent and other retrieval/tool paths.

The SQLite API should live outside Fabric as the mock source system. For local development it can run on a developer machine or container. For the shared demo it must be hosted as a lightweight HTTPS service in Azure Container Apps so Fabric ingestion can call it over HTTPS. Fabric should consume the API as if it were ServiceNow, then persist the data into Fabric-owned storage.

## Azure Container Apps hosting requirement

The mock ServiceNow API should be containerized and deployed to Azure Container Apps.

Required Azure hosting components:

1. Containerized mock ServiceNow API application.
2. SQLite seed database bundled with the container image or initialized at container startup.
3. Azure Container Registry or equivalent registry for the API container image.
4. Azure Container Apps environment.
5. Azure Container App with external HTTPS ingress enabled.
6. Health endpoint, such as `/health`, for deployment validation.
7. Public HTTPS base URL that Fabric ingestion can call.
8. Configuration values documented for Fabric ingestion, including API base URL and any demo authentication/header values.

For the POC, SQLite can be read-only or reset-on-deploy if persistence is not required. If demo edits or ticket creation are added later, move mutable state to Azure Files, Azure SQL, or another durable store rather than relying on ephemeral container storage.

## Credential configuration

Use `.env.example` as the committed template for deployment settings. Copy it to `.env` for local work:

```powershell
Copy-Item .env.example .env
```

Fill in `.env` with local deployment values. Do **not** commit `.env`; it is excluded by `.gitignore`.

Recommended credential approach:

| Scenario | Credential location | Notes |
| --- | --- | --- |
| Local developer deployment | Azure CLI login plus `.env` for resource names | Prefer `az login`; avoid storing client secrets locally unless needed |
| CI/CD deployment | GitHub Actions secrets or Azure DevOps variable groups | Store `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, and federated credential or secret outside git |
| Demo API runtime configuration | Azure Container Apps secrets/environment variables | Store API keys and runtime settings in ACA configuration, not source code |
| Fabric/Foundry configuration | Secure deployment variables or service connections | Do not place Fabric tokens or Foundry keys in committed files |

Never commit Azure client secrets, API keys, Fabric tokens, ServiceNow credentials, or customer data exports.

The `.env.example` file includes placeholders for:

- Azure subscription, tenant, and service principal values
- Resource group and region
- Azure Container Registry
- Azure Container Apps environment and app names
- Container image name and tag
- Mock API demo authentication header
- Fabric workspace, Lakehouse/Warehouse, semantic model, and Data Agent names
- Foundry project and orchestrator agent names
- The Azure Container Apps API base URL after deployment

## Deployment process

The deployment process should move from source mock API to Azure Container Apps, then into Fabric and Foundry.

### 1. Prepare local configuration

1. Copy `.env.example` to `.env`.
2. Fill in Azure resource names and subscription values.
3. Sign in locally with Azure CLI:

```powershell
az login
az account set --subscription $env:AZURE_SUBSCRIPTION_ID
```

For CI/CD, use GitHub Actions secrets or Azure DevOps service connections instead of local interactive login.

### 2. Build the mock ServiceNow API

1. Implement the SQLite-backed API.
2. Add seed data for incidents, users, KB articles, work notes, resolution notes, SLAs, attachments, images, documents, and references.
3. Add `/health` and representative data endpoints.
4. Validate the API locally.

### 3. Containerize the API

1. Add a Dockerfile.
2. Bundle or initialize the SQLite seed database at startup.
3. Expose the configured container port.
4. Build and run the image locally.
5. Validate `/health` and core API routes from the running container.

### 4. Publish the image

1. Create or reuse an Azure Container Registry.
2. Build and tag the mock API image.
3. Push the image to the registry.
4. Confirm the image and tag are available.

### 5. Deploy to Azure Container Apps

1. Create or reuse the Azure resource group.
2. Create the Azure Container Apps environment.
3. Deploy the container app with external HTTPS ingress enabled.
4. Configure runtime environment variables and secrets.
5. Validate the public `/health` endpoint.
6. Save the public API base URL into `.env` as `MOCK_SERVICENOW_API_BASE_URL`.

### 6. Ingest into Fabric

1. Create or select the Fabric workspace.
2. Create the Fabric Lakehouse or Warehouse.
3. Configure Dataflow Gen2, Fabric pipeline, or notebook ingestion to call the Azure Container Apps API endpoint.
4. Land raw API data into Fabric.
5. Transform raw data into curated Fabric tables.
6. Validate row counts, relationships, and cleaned text outputs.

### 7. Build the semantic model and ontology layer

1. Build the Fabric/Power BI semantic model over curated Fabric tables.
2. Add dimensions and measures for ticket volume, backlog, SLA status, aging tickets, average resolution time, reopen rate, category trends, and KB reuse.
3. Build the scoped ontology layer from the semantic model/business entities.
4. Validate representative operational and relationship questions.

### 8. Deploy the Fabric Data Agent and Foundry orchestrator

1. Create the Fabric Data Agent against the semantic model or curated Fabric data.
2. Configure the search/vector retrieval path for cleaned KB, notes, and resolution text.
3. Configure the document/image/attachment retrieval path.
4. Create the Foundry orchestrator agent.
5. Register the Fabric Data Agent and retrieval tools with the orchestrator.
6. Validate end-to-end user scenarios with grounded references.

### 9. Validate the demo

1. Confirm the Azure Container Apps API is reachable over HTTPS.
2. Confirm Fabric ingestion succeeds from the ACA endpoint.
3. Confirm curated Fabric tables are populated.
4. Confirm the semantic model answers structured questions.
5. Confirm the ontology layer supports scoped entity relationships.
6. Confirm the Fabric Data Agent answers operational ticket questions.
7. Confirm retrieval returns KB, notes, documents, images, and attachment references.
8. Confirm the Foundry orchestrator returns grounded responses with citations or source links.

## Business objective

The first target audience is internal IT and support staff. The solution should help them resolve tickets faster by finding historically similar incidents, surfacing prior resolution patterns, retrieving relevant knowledge articles, and providing grounded references such as ticket links, KB articles, document links, screenshots, logs, or other attachments.

A future phase may support end-user self-service, where users can ask questions and open tickets with human-in-the-loop review.

## Meeting-derived direction

The Autoliv and Microsoft discussion aligned on these core principles:

1. Start with business requirements, then shape the semantic model and architecture.
2. Use a multi-agent architecture rather than one monolithic agent.
3. Use Fabric Data Agents for structured relational and semantic-model questions.
4. Use search/vector retrieval for unstructured text such as KB articles, work notes, and resolution notes.
5. Use separate processing or tools for attachments, images, logs, and documents.
6. Build ontology from the semantic model where possible, not directly from raw lakehouse tables.
7. Keep the ontology scoped and small for the POC; split into sub-models if it grows too large.
8. Treat data formatting, semantic modeling, ontology design, and retrieval design as the main challenges, not just connector implementation.

## POC architecture

```text
Mock ServiceNow API hosted in Azure Container Apps
  |
  v
SQLite mock ServiceNow database
  |
  v
Fabric pipeline / Dataflow Gen2 / notebook ingestion
  |
  v
Fabric Lakehouse or Warehouse tables
  |
  +--> Structured semantic model
  |      |
  |      +--> Fabric Data Agent
  |
  +--> Cleaned text and reference index
  |      |
  |      +--> Search / vector retrieval
  |
  +--> Attachment, document, and image metadata
         |
         +--> Document / image tool or agent

Foundry orchestrator agent
  |
  +--> Fabric Data Agent
  +--> Search / vector retrieval
  +--> Document / image tool or agent
  |
  v
IT support user experience
```

## Mock ServiceNow data requirements

### Structured ticket data

The SQLite-backed mock API should include representative ServiceNow-style tables and fields:

| Entity | Example fields |
| --- | --- |
| Incidents | incident_id, number, short_description, description, state, priority, impact, urgency, category, subcategory, assignment_group_id, assigned_to_user_id, requester_user_id, opened_at, updated_at, resolved_at, closed_at, resolution_code |
| Users | user_id, name, email, department, location, manager_id, active |
| Assignment groups | group_id, name, owner_user_id, support_tier, business_service |
| Change requests | change_id, number, state, risk, impacted_service, planned_start, planned_end |
| Incident-change links | incident_id, change_id, relationship_type |
| SLAs | incident_id, sla_name, target_duration, elapsed_duration, breached, due_at |
| Categories | category_id, category, subcategory, business_service |

### Semi-structured and unstructured content

The POC should include fields that simulate real ServiceNow text content:

| Content type | Purpose |
| --- | --- |
| KB article HTML | Simulate ServiceNow knowledge article body content |
| Cleaned KB text | Search/vector-ready version of KB HTML |
| Work notes | Internal troubleshooting history |
| Resolution notes | Final remediation steps and outcomes |
| Customer-facing comments | Content that may be returned to requesters |
| Linked references | Related incident, KB, document, and external URLs |

Important correction: references to "HTTP code" in the early draft should be treated as **HTML/text content** from ServiceNow KB articles, work notes, and resolution fields.

### Documents, images, attachments, and reference metadata

The mock dataset should include attachment/reference metadata even if the files themselves are mocked:

| Entity | Example fields |
| --- | --- |
| Attachments | attachment_id, incident_id, file_name, file_type, url, content_summary, extracted_text, created_at |
| Images | image_id, incident_id, url, caption, extracted_description, related_kb_id |
| Documents | document_id, title, url, document_type, source_system, summary, related_category |
| External references | reference_id, incident_id, kb_id, title, url, reference_type |

Attachment types should include realistic examples such as screenshots, logs, SQL scripts, diagnostic files, and linked documents.

## Fabric deployment and data preparation

The POC should show how raw ServiceNow-style data becomes AI-ready:

1. Containerize and host the SQLite-backed mock ServiceNow API in Azure Container Apps.
2. Use Fabric ingestion, such as Dataflow Gen2, Fabric pipeline, or notebook-based ingestion, to call the mock API.
3. Land mock API data into a Fabric Lakehouse or Warehouse.
4. Normalize core entities such as incidents, users, groups, categories, KB articles, attachments, and change requests into curated Fabric tables.
5. Convert HTML fields into cleaned text while preserving meaningful links.
6. Extract metadata from attachments, documents, and images.
7. Maintain relationship tables between incidents, KB articles, documents, images, changes, users, and support groups.
8. Produce structured tables for semantic modeling and separate text/reference indexes for retrieval.

The SQLite database and API are source-system mocks. The authoritative demo data layer should be in Fabric after ingestion.

## Semantic model

The semantic model should support operational ticket analytics and AI grounding.

The semantic model should be built in Fabric/Power BI over the curated Fabric tables, not only documented locally.

### Suggested dimensions

- Date
- User/requester
- Assignment group
- Category/subcategory
- Business service/application
- Priority
- State/status
- Resolution code
- Knowledge article
- Attachment/document type

### Suggested measures

- Ticket volume
- Open ticket count
- Backlog by priority
- Average resolution time
- SLA breach count
- Reopen rate
- Aging open tickets
- Ticket volume by category
- Resolution pattern frequency
- KB article reuse count

## Ontology

The ontology should be built from the semantic model where possible and kept scoped for the POC. The POC should include an actual ontology layer artifact or implementation path, not only a conceptual diagram.

### Core nodes

- Ticket
- User/requester
- Support group
- Category/subcategory
- Business service/application
- Knowledge article
- Attachment
- Document
- Image
- Change request
- Resolution pattern

### Core relationships

- Ticket was opened by User
- Ticket is assigned to Support group
- Ticket belongs to Category/subcategory
- Ticket impacts Business service/application
- Ticket references Knowledge article
- Ticket has Attachment
- Ticket has Image
- Ticket relates to Change request
- Ticket was resolved by Resolution pattern
- Knowledge article applies to Category/subcategory

If the ontology becomes too broad, split it into multiple semantic sub-models and ontologies instead of creating one oversized graph.

## Agent architecture

The recommended design is a multi-agent architecture coordinated by a Foundry orchestrator agent.

| Agent/tool | Responsibility |
| --- | --- |
| Foundry orchestrator agent | Routes user intent, coordinates tools/agents, composes final grounded answers |
| Fabric Data Agent | Deployed Fabric Data Agent that answers structured questions over incidents, users, groups, priorities, SLAs, categories, and semantic model measures |
| Search/vector retrieval | Retrieves KB articles, work notes, resolution notes, cleaned HTML text, and similar historical tickets |
| Document/image/attachment agent or tool | Retrieves attachment metadata, image descriptions, document summaries, logs, scripts, and related URLs |

Fabric Data Agents should not be expected to handle all semi-structured and unstructured content alone.

## Example user experiences

### Similar historical ticket lookup

User asks:

```text
Find tickets similar to this new VPN connectivity incident and summarize how they were resolved.
```

Expected result:

- Similar historical tickets
- Shared symptoms
- Most common resolution pattern
- Related KB articles
- Supporting ticket and document links

### Open ticket follow-up

User asks:

```text
Show high-priority open tickets for the finance application that have not been updated in the last three days.
```

Expected result:

- Filtered open ticket list
- Priority, owner, age, last update, SLA status
- Suggested follow-up actions

### Knowledge and reference retrieval

User asks:

```text
What KB articles, screenshots, logs, or scripts should I reference for this database timeout issue?
```

Expected result:

- Relevant KB articles
- Related attachments and documents
- Similar historical incident links
- Explanation of why each reference is relevant

## Demo success criteria

The demo should show:

1. Mock ServiceNow API returning realistic incident, KB, user, metadata, and attachment data from SQLite.
2. Data ingested from the mock API into a real Fabric Lakehouse or Warehouse.
3. Cleaned text extracted from HTML-like fields.
4. A deployed Fabric semantic model with entities and measures for operational ticket analysis.
5. A scoped ontology layer over ServiceNow business entities.
6. A deployed Fabric Data Agent structured query flow.
7. At least one search/vector retrieval flow for unstructured ticket or KB content.
8. At least one document/image/attachment reference retrieval flow.
9. A Foundry orchestrator agent that combines results and returns grounded references.

## Open questions

1. Will the interim architecture reuse Snowflake mirrored data, or should the POC focus only on direct ServiceNow API to Fabric?
2. What real ServiceNow API access or representative export can be provided?
3. Does Autoliv already have a ServiceNow semantic/data model that should be reused?
4. Which ServiceNow modules are in scope for the first demo: incidents only, or incidents plus KB, users, changes, and attachments?
5. What are the highest-value support scenarios for the first show-and-tell?
6. What attachment types are most important: screenshots, logs, scripts, documents, or all of them?
7. What confidence, citation, or approval requirements should be applied before the assistant recommends a resolution?

## Action items

1. Get access to the real ServiceNow API or a representative export.
2. Get or define the current ServiceNow semantic model/data model.
3. Clarify gaps in the existing ServiceNow, Snowflake, and Fabric flow.
4. Build a Fabric and Foundry POC using SQLite-backed ServiceNow-like data as the source system mock.
5. Demonstrate structured ticket querying, historical similarity search, KB/reference retrieval, and attachment/document metadata retrieval.
6. Prepare a show-and-tell using mocked or partial data.
7. Validate whether Snowflake remains part of the interim architecture or whether the target should be direct ServiceNow API to Fabric ingestion.

## Next steps: production deployment for agents

After the POC validates the architecture, productionize the agent stack in stages.

### 1. Replace the mock source

1. Replace the SQLite-backed mock API with real ServiceNow API ingestion.
2. Use ServiceNow OAuth or approved enterprise authentication.
3. Confirm rate limits, pagination, incremental loads, and attachment access patterns.
4. Define whether Snowflake remains an interim source or is bypassed.

### 2. Harden the Fabric data estate

1. Move from demo seed data to production ServiceNow tables and APIs.
2. Add incremental ingestion, retry handling, and data quality checks.
3. Define medallion-style raw, curated, and serving layers.
4. Add sensitivity labels and access controls.
5. Validate security trimming for users, support groups, and restricted tickets.

### 3. Productionize the semantic model

1. Review the semantic model with IT support and reporting stakeholders.
2. Certify dimensions, measures, relationships, and business definitions.
3. Add deployment pipelines for dev/test/prod semantic model promotion.
4. Add refresh monitoring and ownership.

### 4. Productionize the ontology layer

1. Confirm the final entity and relationship scope.
2. Keep the ontology small enough for reliable traversal and explainability.
3. Split into multiple ontologies or semantic sub-models if the scope expands.
4. Validate ontology outputs against known support workflows.

### 5. Productionize the Fabric Data Agent

1. Connect the Data Agent to the certified semantic model or curated Fabric data.
2. Define allowed question domains and blocked domains.
3. Add grounding instructions, answer format rules, and escalation behavior.
4. Test with representative support personas and ticket scenarios.
5. Monitor quality, latency, and incorrect-answer patterns.

### 6. Productionize retrieval agents/tools

1. Move cleaned KB, work notes, resolution notes, and document metadata into the approved retrieval store.
2. Add indexing refresh jobs aligned with Fabric ingestion.
3. Preserve links back to ServiceNow records, KB articles, documents, images, and attachments.
4. Add metadata filters for category, priority, business service, geography, and support group.
5. Validate retrieval quality with known resolved incidents.

### 7. Productionize the Foundry orchestrator

1. Register the Fabric Data Agent, retrieval tools, and document/image tools as orchestrator capabilities.
2. Define routing rules for structured, unstructured, and attachment-heavy questions.
3. Require grounded answers with source references.
4. Add human-in-the-loop review before ticket updates, customer-facing responses, or ticket creation.
5. Add telemetry, evaluation sets, and continuous quality monitoring.

### 8. Establish operational governance

1. Define owners for Fabric ingestion, semantic model, ontology, Data Agent, retrieval index, and Foundry orchestrator.
2. Create release gates for prompt, model, schema, and ontology changes.
3. Add test sets for similar-ticket search, open-ticket follow-up, KB retrieval, and attachment reference retrieval.
4. Add security review for ServiceNow permissions and user-visible outputs.
5. Define a support process for bad answers, missing references, and data freshness issues.
