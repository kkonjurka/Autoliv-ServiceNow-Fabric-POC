# Squad Prompts for the Autoliv ServiceNow to Fabric POC

These prompts are designed for [Squad](https://github.com/bradygaster/squad), a human-led AI agent team workflow for GitHub Copilot.

Use them from a project directory after initializing Squad:

```bash
npm install -g @bradygaster/squad-cli
squad init --preset default
copilot --agent squad --yolo
```

Then paste the prompts below as needed.

## Prompt 1: Set up the Squad team

```text
I'm starting a new POC project. Set up the team.

Project name: Autoliv ServiceNow to Microsoft Fabric POC

Project goal:
Build a mock ServiceNow-to-Fabric proof of concept that deploys ServiceNow-like operational data into Microsoft Fabric and uses it to build an actual Fabric semantic model, ontology layer, Fabric Data Agent, and multi-agent Foundry architecture for AI-assisted ticket resolution.

Important context:
- This is based on an Autoliv and Microsoft ServiceNow data discussion.
- The first target users are internal IT/support staff.
- The core business goal is to help support users resolve tickets faster by finding historically similar tickets, open follow-up tickets, KB articles, documents, image references, logs, scripts, and other supporting references.
- The POC should use a mock ServiceNow connector implemented as an API backed by SQLite.
- SQLite is only a POC stand-in for ServiceNow API data. The target production direction is direct ServiceNow API ingestion into Fabric.
- The SQLite API should live outside Fabric as the mock source system. For local development it can run locally or in a container. For the shared demo it must be containerized and hosted as a lightweight HTTPS service in Azure Container Apps so Fabric can ingest from it.
- The POC must deploy data into a real Fabric Lakehouse or Warehouse, not only generate local Fabric-style files.
- The POC must build an actual Fabric semantic model and Fabric Data Agent over the deployed Fabric data.
- The architecture should be multi-agent, not one monolithic agent.
- Fabric Data Agents should be used for structured relational/semantic-model questions.
- Search/vector retrieval should be used for unstructured text such as KB articles, HTML fields, work notes, and resolution notes.
- Documents, images, logs, scripts, and attachments should have a separate retrieval/tooling path.
- Foundry should act as the orchestrator over the Fabric Data Agent, search/vector system, and document/image/attachment tool path.

Please propose a Squad team with specialists for:
1. Technical architecture and work breakdown
2. Mock ServiceNow API and SQLite schema
3. Azure Container Apps deployment and DevOps
4. Fabric deployment, data modeling, and transformations
5. Semantic model and ontology design
6. Foundry agent orchestration and prompt/tool design
7. Retrieval/search for KB, notes, documents, and images
8. Testing and demo validation
9. Documentation and demo storytelling

After proposing the team, create routing guidance so tasks are delegated to the right specialists.
```

## Prompt 2: Lead architect kickoff

```text
Team, begin the architecture planning for the Autoliv ServiceNow to Microsoft Fabric POC.

Read README.md first and treat it as the source of truth.

Deliverables:
1. Create a concise implementation plan.
2. Identify the minimum viable demo path.
3. Define architecture boundaries for the POC.
4. Identify what is explicitly mocked versus what represents the target production design.
5. Identify risks and open questions.

Architecture requirements:
- Mock ServiceNow API backed by SQLite
- Azure Container Apps hosting for the mock ServiceNow API
- Fabric ingestion using Dataflow Gen2, Fabric pipeline, or notebook-based ingestion
- Real Fabric Lakehouse or Warehouse normalized tables
- Cleaned text generated from HTML-like ServiceNow content
- Deployed Fabric semantic model
- Scoped ontology layer built from the semantic model/business entities
- Multi-agent architecture coordinated by Foundry
- Deployed Fabric Data Agent for structured questions
- Search/vector retrieval for unstructured content
- Separate document/image/attachment path

Do not implement yet. Produce a plan and assign work to specialists.
```

## Prompt 3: Backend/API specialist

```text
Backend/API specialist, design and implement the mock ServiceNow connector.

Read README.md first and follow the POC scope.

Goal:
Create an API backed by SQLite that simulates ServiceNow data expected from the real ServiceNow API.

Required data domains:
- Incidents
- Users
- Assignment groups
- Categories/subcategories
- Knowledge articles
- Work notes
- Resolution notes
- Change requests
- Incident-change relationships
- SLAs
- Attachments
- Images
- Documents
- External references

Required API behavior:
1. Return paginated incident data.
2. Filter incidents by state, priority, category, assignment group, updated date, and requester.
3. Retrieve a single incident with related notes, KB articles, attachments, images, documents, and references.
4. Search historical incidents by keyword and category.
5. Return open tickets that need follow-up.
6. Return KB articles and cleaned text fields.
7. Return attachment/document/image metadata and mock URLs.

Data requirements:
- Seed realistic mock records.
- Include open and closed tickets.
- Include similar historical tickets with shared symptoms and resolution patterns.
- Include HTML-like KB/article fields and cleaned text versions.
- Include realistic attachment types such as screenshots, logs, SQL scripts, and documents.

Implementation requirements:
- Keep the design simple and demo-friendly.
- Do not hard-code all responses in route handlers; use SQLite tables.
- Include clear setup/run instructions.
- Add tests or smoke checks for the key endpoints.

When finished, report the endpoint list, schema summary, seed data summary, and validation results.
```

## Prompt 3A: Azure Container Apps deployment specialist

```text
Azure deployment specialist, containerize and deploy the mock ServiceNow API to Azure Container Apps.

Read README.md first and follow the confirmed hosting scope.

Goal:
Host the SQLite-backed mock ServiceNow API as a lightweight HTTPS service in Azure Container Apps so Microsoft Fabric can ingest from it.

Required deliverables:
1. Dockerfile or equivalent container build configuration for the mock ServiceNow API.
2. Startup process that makes the SQLite seed database available inside the container.
3. Health endpoint validation, such as GET /health.
4. Azure Container Registry or equivalent image registry publishing steps.
5. Azure Container Apps environment definition.
6. Azure Container App deployment with external HTTPS ingress enabled.
7. Environment variables/configuration documentation.
8. Public HTTPS API base URL for Fabric ingestion.
9. Deployment validation commands.
10. Rollback/redeploy notes for demo reliability.
11. Use .env.example as the committed configuration template and .env as the ignored local file for developer-specific values.
12. Document which values should become GitHub Actions secrets or Azure DevOps variable group entries for CI/CD.

POC persistence guidance:
- SQLite can be bundled with the image or initialized at startup.
- It is acceptable for the demo API to reset on redeploy.
- If mutable demo scenarios are added, document that persistent state should move to Azure Files, Azure SQL, or another durable store.

Security guidance:
- Keep the demo simple, but do not expose secrets in source code.
- If demo authentication is needed, use environment variables or managed configuration.
- Document any required headers Fabric ingestion must send.
- Do not commit Azure client secrets, API keys, Fabric tokens, ServiceNow credentials, or customer data exports.
- Prefer Azure CLI login for local deployment and workload identity/service principal secrets stored outside git for automation.

When finished, report:
- Container image name
- Azure Container App name
- Public HTTPS endpoint
- Health check result
- Fabric ingestion configuration values
- Known limitations
```

## Prompt 4: Data engineering and Fabric modeling specialist

```text
Data engineering specialist, design and implement the Fabric deployment and data preparation layer for the mock ServiceNow data.

Read README.md first.

Goal:
Show how raw ServiceNow-style API data is ingested into a real Fabric Lakehouse or Warehouse and becomes normalized Fabric tables plus AI-ready text/reference assets.

Deliverables:
1. Define normalized Fabric table schemas for incidents, users, groups, categories, KB articles, work notes, resolution notes, changes, SLAs, attachments, images, documents, and references.
2. Create ingestion logic from the Azure Container Apps-hosted mock API into Fabric using Dataflow Gen2, Fabric pipeline, or notebook-based ingestion.
3. Create transformation logic from raw Fabric landing tables into curated analytical tables.
4. Convert HTML-like fields into cleaned text.
5. Preserve meaningful URLs and references.
6. Create relationship tables between incidents, KB articles, documents, images, attachments, changes, users, and support groups.
7. Produce a small data dictionary.

Important modeling requirements:
- Keep structured and unstructured representations separate.
- Structured tables support semantic model and Fabric Data Agent questions.
- Cleaned text/reference outputs support search/vector retrieval.
- Attachment/image/document metadata supports a separate document/image/attachment tool or agent path.

When finished, report:
- Curated table list
- Key fields
- Relationship model
- Transformation assumptions
- How the outputs support the semantic model and agent architecture
```

## Prompt 5: Semantic model and ontology specialist

```text
Semantic model and ontology specialist, design and implement the Fabric semantic model and scoped ontology layer for the Autoliv ServiceNow POC.

Read README.md first.

Goal:
Create a deployed Fabric semantic model and ontology layer that help IT support users ask operational and resolution-oriented questions over ServiceNow data.

Semantic model requirements:
- Dimensions: date, user/requester, assignment group, category/subcategory, business service/application, priority, state/status, resolution code, KB article, attachment/document type.
- Measures: ticket volume, open ticket count, backlog by priority, average resolution time, SLA breach count, reopen rate, aging open tickets, ticket volume by category, resolution pattern frequency, KB article reuse count.
- Support structured questions suitable for a deployed Fabric Data Agent.

Ontology requirements:
- Build ontology from the semantic model where possible.
- Keep it intentionally scoped for the POC.
- Include nodes for Ticket, User/requester, Support group, Category/subcategory, Business service/application, Knowledge article, Attachment, Document, Image, Change request, and Resolution pattern.
- Include relationships such as Ticket was opened by User, Ticket is assigned to Support group, Ticket references Knowledge article, Ticket has Attachment, Ticket relates to Change request, and Ticket was resolved by Resolution pattern.

Deliverables:
1. Fabric semantic model design and implementation guidance.
2. Ontology node and relationship design plus implementation path.
3. Example business questions the semantic model can answer.
4. Example graph traversal questions the ontology can support.
5. Guidance on when to split into multiple semantic sub-models or ontologies.

When finished, report the model in markdown tables and include assumptions.
```

## Prompt 6: Search and retrieval specialist

```text
Search/retrieval specialist, design the retrieval layer for unstructured ServiceNow content.

Read README.md first.

Goal:
Design how the POC searches across KB articles, cleaned HTML text, work notes, resolution notes, documents, images, logs, scripts, and references.

Requirements:
1. Use cleaned text from KB articles, work notes, and resolution notes as retrieval content.
2. Preserve links back to source incidents, KB articles, documents, and attachments.
3. Include attachment/image/document metadata in retrieval results.
4. Support historical similarity search across closed incidents.
5. Support open-ticket follow-up search.
6. Return grounded references with every answer.

Design questions to answer:
- What content should be indexed?
- What metadata filters are required?
- What fields should be returned to the orchestrator?
- How should images and attachments be represented if the actual binary files are not stored in the POC?
- How should retrieved results be ranked?

When finished, report:
- Index schema
- Metadata fields
- Retrieval patterns
- Example queries
- Example retrieval result JSON shape
```

## Prompt 7: Foundry agent orchestration specialist

```text
Foundry/agent specialist, design the multi-agent orchestration pattern for the POC.

Read README.md first.

Goal:
Design a Foundry orchestrator agent that coordinates a deployed Fabric Data Agent, search/vector retrieval, and a document/image/attachment tool path.

Required agent/tool roles:
1. Foundry orchestrator agent: understands user intent, chooses tools, combines results, returns grounded answers.
2. Fabric Data Agent: deployed against the Fabric semantic model or curated Fabric data to answer structured ticket, SLA, priority, category, backlog, and semantic model questions.
3. Search/vector retrieval: retrieves KB articles, work notes, resolution notes, cleaned HTML content, and similar historical tickets.
4. Document/image/attachment tool or agent: retrieves attachment metadata, image descriptions, document summaries, logs, scripts, and URLs.

Required user scenarios:
- Find similar historical tickets and summarize how they were resolved.
- Show open high-priority tickets that need follow-up.
- Retrieve KB articles and documents for a specific issue.
- Find related screenshots, logs, scripts, or attachments.
- Compose a grounded suggested resolution with references.

Deliverables:
1. Agent responsibility matrix.
2. Tool routing logic.
3. Example system instructions for the orchestrator.
4. Example tool/function contracts.
5. Example end-to-end conversation flows.
6. Guardrails for grounding, confidence, and human review.

Important constraint:
Do not design this as one agent over all data. The meeting direction was explicitly multi-agent and multi-system.
```

## Prompt 8: Test and demo validation specialist

```text
Testing/demo specialist, create a validation plan for the Autoliv ServiceNow to Fabric POC.

Read README.md first.

Goal:
Define how we prove the demo works and aligns to the business requirements.

Required validation areas:
1. Mock API returns realistic ServiceNow-style data.
2. Mock API is deployed to Azure Container Apps with external HTTPS ingress.
3. Health endpoint validates successfully from outside Azure Container Apps.
4. SQLite seed data includes incidents, users, groups, categories, KB articles, work notes, resolution notes, changes, SLAs, attachments, images, documents, and references.
5. Fabric ingestion calls the Azure Container Apps API endpoint.
6. Data is ingested into a real Fabric Lakehouse or Warehouse.
7. Transformations produce curated Fabric tables.
8. HTML-like fields are converted to cleaned text.
9. Deployed Fabric semantic model supports structured operational questions.
10. Ontology layer supports scoped entity relationship traversal.
11. Deployed Fabric Data Agent flow handles structured questions.
12. Search/retrieval flow handles unstructured content.
13. Document/image/attachment path returns relevant metadata and URLs.
14. Foundry orchestrator returns grounded answers with references.

Create:
- Smoke test checklist
- Demo script
- Sample test questions
- Expected output criteria
- Known limitations to disclose

When finished, provide a concise validation plan that can be used before a customer-facing show-and-tell.
```

## Prompt 9: Documentation and storytelling specialist

```text
Documentation/demo storytelling specialist, create client-ready documentation for the Autoliv ServiceNow to Fabric POC.

Read README.md first.

Goal:
Prepare clear materials that explain the business value, architecture, demo flow, and next steps.

Deliverables:
1. Executive summary.
2. Business problem and desired outcome.
3. Current-state versus target-state architecture.
4. POC architecture explanation.
5. Data model overview.
6. Semantic model and ontology explanation.
7. Multi-agent architecture explanation.
8. Demo flow.
9. Open questions.
10. Next-step recommendations.

Messaging guidance:
- Emphasize that the value is not only connector work; the value comes from data shaping, semantic modeling, ontology scoping, retrieval design, and multi-agent orchestration.
- Be clear that SQLite is a mock POC stand-in hosted outside Fabric, not the target production architecture.
- Be clear that the POC deploys actual data assets into Fabric, including a Lakehouse or Warehouse, semantic model, and Fabric Data Agent.
- Be clear that Fabric Data Agents are for structured questions and should be combined with search/vector and document/image tooling.
- Keep the first phase focused on internal IT support users.
- Mention future end-user self-service as a later phase.
```

## Prompt 10: End-to-end build execution

```text
Team, implement the minimum viable Autoliv ServiceNow to Microsoft Fabric POC.

Read README.md first and use the previous Squad plan and decisions as context.

Minimum viable demo requirements:
1. Mock ServiceNow API backed by SQLite.
2. Seeded realistic ServiceNow-style data.
3. API containerized and hosted in Azure Container Apps with external HTTPS ingress.
4. Endpoints for incidents, similar historical tickets, open follow-up tickets, KB articles, and attachment/document/image references.
5. Data ingested into a real Fabric Lakehouse or Warehouse from the Azure Container Apps API endpoint.
6. Curated Fabric tables and transformation scripts.
7. Cleaned text generated from HTML-like fields.
8. Deployed Fabric semantic model or deployable semantic model artifact.
9. Ontology layer documentation and implementation path.
10. Deployed Fabric Data Agent or deployable Data Agent configuration.
11. Multi-agent Foundry orchestration documentation.
12. Demo script and smoke test checklist.

Prioritize demo completeness and clarity over production hardening.

Implementation order:
1. Backend/API and SQLite seed data
2. Containerize API and deploy it to Azure Container Apps
3. Fabric ingestion into Lakehouse or Warehouse from the Azure Container Apps endpoint
4. Data transformation and curated Fabric tables
5. Fabric semantic model and ontology layer
6. Fabric Data Agent
7. Retrieval/index design
8. Foundry orchestration design
9. Tests/smoke checks
10. Demo documentation

Escalate if:
- The architecture drifts into a single-agent design
- Unstructured content is being forced into only the Fabric Data Agent path
- The POC no longer clearly distinguishes SQLite mock implementation from production ServiceNow API ingestion
- The mock API is not hosted in Azure Container Apps for the shared demo
- The data is not actually deployed into Fabric
- The semantic model or Data Agent is only documented and not deployable
- The demo cannot return grounded references

When finished, report what was built, how to run it, how to validate it, and what remains for productionization.
```

## Prompt 11: GitHub issue creation prompt

```text
Team, create GitHub issues for the Autoliv ServiceNow to Fabric POC.

Read README.md and SQUAD_PROMPTS.md first.

Create issues for:
1. Mock ServiceNow API and SQLite schema
2. Seed realistic ServiceNow data
3. Containerize mock ServiceNow API
4. Deploy mock API to Azure Container Apps
5. Configure safe deployment credentials using .env.example, ignored .env, and CI/CD secrets
6. Fabric ingestion into Lakehouse or Warehouse from the Azure Container Apps endpoint
7. Fabric transformation layer and curated tables
8. HTML-to-clean-text processing
9. Fabric semantic model implementation
10. Ontology layer implementation
11. Fabric Data Agent implementation
12. Search/vector retrieval design
13. Document/image/attachment retrieval path
14. Foundry orchestrator agent design
15. Production deployment steps for agents
16. Smoke tests and demo validation
17. Client-ready demo documentation

Each issue should include:
- Objective
- Scope
- Acceptance criteria
- Owner recommendation
- Dependencies

Do not create issues until you confirm the repository and issue tracker are available.
```

## Prompt 12: Show-and-tell preparation prompt

```text
Team, prepare the show-and-tell narrative for the Autoliv ServiceNow to Microsoft Fabric POC.

Read README.md first.

Audience:
Autoliv business and technical stakeholders.

Message:
This POC demonstrates how ServiceNow data can be transformed into a semantic and agent-ready architecture using Microsoft Fabric and Foundry. The point is not only to connect to ServiceNow; the point is to shape structured and unstructured support data so AI can answer operational questions, find similar historical tickets, retrieve references, and help IT support teams resolve issues faster.

Demo flow:
1. Show mock ServiceNow API hosted in Azure Container Apps and explain SQLite as a POC stand-in for ServiceNow.
2. Show Fabric ingestion from the mock API into a real Fabric Lakehouse or Warehouse.
3. Show normalized curated Fabric tables.
4. Show cleaned text from ServiceNow HTML/work notes/resolution notes.
5. Show deployed semantic model and operational measures.
6. Show scoped ontology layer.
7. Show Fabric Data Agent answering a structured open-ticket question.
8. Ask a similar historical-ticket question.
9. Ask for KB/document/image references.
10. Show Foundry orchestrator combining structured, unstructured, and attachment results.
11. Close with production path and open questions.

Create:
- Talk track
- Demo script
- Expected questions and answers
- Risks/limitations slide content
- Recommended next steps
```
