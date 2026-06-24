# Deploy: ServiceNow Orchestrator Agent to Azure AI Foundry

This guide walks through deploying the `servicenow-orchestrator` agent to Azure AI
Foundry end-to-end, from prerequisites through validation.

---

## 1. Prerequisites

| Requirement | Notes |
|---|---|
| Azure subscription | Must have Contributor on the resource group |
| Azure AI Foundry project | Create at [ai.azure.com](https://ai.azure.com) |
| `gpt-4o` deployment | Deploy in your Foundry project under **Models + endpoints** |
| `text-embedding-ada-002` deployment | Deploy in the same Azure OpenAI resource |
| Azure AI Search service | Standard tier or above for semantic/vector search |
| Microsoft Fabric workspace | Workspace must contain the deployed Fabric Data Agent |
| Azure CLI ≥ 2.60 | `az --version` to verify |
| Python ≥ 3.11 | `python --version` to verify |

---

## 2. Environment Setup

### 2a. Copy and fill the environment file

```powershell
# From repo root
Copy-Item .env.example .env
notepad .env
```

Fill in the following values in `.env`:

```dotenv
# Azure identity
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<service-principal-or-leave-blank-for-az-login>

# Azure AI Foundry project
AZURE_AI_PROJECT_CONNECTION_STRING=<connection-string-from-foundry-project-overview>
FOUNDRY_ORCHESTRATOR_AGENT_NAME=servicenow-orchestrator
FOUNDRY_MODEL=gpt-4o

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://<your-search-service>.search.windows.net
AZURE_SEARCH_KEY=<your-search-query-key>

# Azure OpenAI (embeddings)
AZURE_OPENAI_ENDPOINT=https://<your-aoai-resource>.openai.azure.com
AZURE_OPENAI_KEY=<your-aoai-key>
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-ada-002

# Microsoft Fabric Data Agent
FABRIC_DATA_AGENT_ENDPOINT=https://api.fabric.microsoft.com/v1/workspaces/<workspace-id>/dataAgents/<agent-id>
FABRIC_WORKSPACE_ID=<workspace-guid>
```

> **Never commit `.env`.** It is listed in `.gitignore`.

### 2b. Find the Foundry project connection string

1. Open [Azure AI Foundry](https://ai.azure.com).
2. Select your project.
3. Go to **Settings → Project details**.
4. Copy the **Connection string** value.

### 2c. Find the Fabric Data Agent endpoint

1. Open [Microsoft Fabric](https://app.fabric.microsoft.com).
2. Go to your workspace → **Data Agents**.
3. Select the **ServiceNow Support Data Agent**.
4. Copy the **REST endpoint** from the agent details pane.

---

## 3. Install Dependencies

```powershell
cd foundry-agent
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 4. Local Testing

### 4a. Load environment variables

```powershell
# PowerShell — load .env from repo root
Get-Content ..\\.env | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}
```

### 4b. Run a single test query

```powershell
python app.py --query "Show open high-priority tickets that need follow-up"
```

### 4c. Run the interactive loop

```powershell
python app.py
```

Type queries at the `You:` prompt. Type `quit` to exit.

### 4d. Validate tool routing

Run each query below and verify the correct tool is called (check `INFO` log lines):

| Query | Expected tool(s) |
|---|---|
| `How many P1 tickets are open in the Network category?` | `query_fabric_data_agent` |
| `Find KB articles for SAP login failures` | `search_knowledge` |
| `Find similar historical incidents for VPN timeout errors` | `search_incidents` |
| `List attachments on ticket INC0012345` | `get_attachment_metadata` |
| `Suggest a resolution for this open SAP ticket` | `query_fabric_data_agent` + `search_incidents` |

---

## 5. Azure AI Search Index Setup

The agent expects three indexes in your Azure AI Search service. Create them via the
Azure Portal or with the REST API:

### 5a. `kb-articles` index

Required fields: `id`, `title`, `content_type` (`kb_article`), `snippet`, `url`,
`content_vector` (1536-dim, `text-embedding-ada-002`).

### 5b. `incident-content` index

Required fields: `id`, `number`, `short_description`, `resolution_notes`, `snippet`,
`url`, `state` (`Resolved` | `Closed`), `content_type`
(`work_note` | `resolution_note` | `cleaned_html`),
`content_vector` (1536-dim).

### 5c. `attachments` index

Required fields: `id`, `asset_type`, `title`, `summary`, `url`, `ticket_id`.

Enable **semantic configuration** named `default` on `kb-articles` and
`incident-content` indexes. Point the semantic configuration at `snippet` or
`short_description` as the primary content field.

---

## 6. Deployment to Azure AI Foundry

### Option A — Azure AI Foundry Portal (simplest)

1. Navigate to your Foundry project → **Agents**.
2. Click **New agent**.
3. Set name: `servicenow-orchestrator`, model: `gpt-4o`.
4. Paste the contents of `instructions.md` as the **System message**.
5. Under **Functions**, import each entry from `tool_schemas.json`.
6. Save and test with the built-in playground.

### Option B — SDK deployment via `app.py` (recommended for CI/CD)

The first call to `app.py --query "..."` automatically creates the agent in your
Foundry project using `_get_or_create_agent()`. Subsequent calls reuse the existing
agent by name.

```powershell
# One-time bootstrap + first query
python app.py --query "Health check: list open tickets"
```

### Option C — Azure Developer CLI (azd)

If an `azure.yaml` is present at the repo root:

```powershell
azd up
```

To deploy only the agent configuration without infrastructure changes:

```powershell
azd deploy foundry-agent
```

---

## 7. Updating the Agent

To update the system instructions after editing `instructions.md`:

```powershell
# Delete the existing agent so app.py recreates it with new instructions
az rest --method DELETE \
  --url "https://management.azure.com/subscriptions/$env:AZURE_SUBSCRIPTION_ID/resourceGroups/$env:AZURE_RESOURCE_GROUP/providers/Microsoft.MachineLearningServices/workspaces/$env:FOUNDRY_PROJECT_NAME/agents/servicenow-orchestrator?api-version=2024-04-01"

python app.py --query "Health check"
```

Or update in-place via the Foundry Portal → **Agents → servicenow-orchestrator →
Edit system message**.

---

## 8. Validation Queries

Run these after deployment to verify end-to-end routing:

```text
1. How many tickets are currently open and breaching SLA?
   Expected: Fabric Data Agent called; structured ticket counts returned.

2. Find KB articles for SAP login failures and summarize the fix.
   Expected: search_knowledge called with content_types=["kb_article"].

3. Find the 5 most similar historical incidents to a VPN timeout error.
   Expected: search_incidents called; top results include resolution_note.

4. What attachments are on ticket INC0012345?
   Expected: get_attachment_metadata called; asset list returned.

5. Based on an open P2 network outage ticket, suggest a resolution with references.
   Expected: query_fabric_data_agent + search_incidents both called; answer includes
             Evidence, References, and Confidence sections.
```

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `AZURE_AI_PROJECT_CONNECTION_STRING is not set` | Missing env var | Set in `.env` and reload |
| `401 Unauthorized` from Azure AI Search | Wrong API key | Re-copy query key from Azure Portal |
| `400` from Fabric Data Agent endpoint | Wrong endpoint URL | Verify URL in Fabric workspace → Data Agents |
| Agent responds without calling tools | Model hedging | Lower `temperature` in `agent.yaml` or add explicit routing examples to instructions |
| Empty `results` from search | Index not populated | Run ingestion notebooks in `servicenow-demo/` to populate indexes |
| Embedding call fails | Missing `AZURE_OPENAI_ENDPOINT` | Set env var; tool falls back to keyword search |
