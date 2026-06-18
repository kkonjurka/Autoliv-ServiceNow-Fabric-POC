# Fabric Git integration deployment guide

This guide connects the `servicenow-demo` Microsoft Fabric workspace to the GitHub repository `kkonjurka/Autoliv-ServiceNow-Fabric-POC` and syncs the Fabric-native workspace items stored under `/servicenow-demo`.

## 1. Prerequisites

Before you start, confirm all of the following:

1. The `servicenow-demo` workspace exists in Microsoft Fabric.
2. The workspace is on a Fabric capacity that supports Git integration (F2 or higher).
3. Your GitHub account is connected in Fabric and has access to `kkonjurka/Autoliv-ServiceNow-Fabric-POC`.
4. The `main` branch exists in the GitHub repository.
5. The repository contains the `/servicenow-demo` folder with the Fabric item structure.
6. The live mock ServiceNow API is reachable at `https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io`.

## 2. Connect the workspace to GitHub

1. Open the Fabric portal.
2. Open the `servicenow-demo` workspace.
3. In the workspace header, select **Workspace settings**.
4. In the settings pane, open **Git integration**.
5. Choose **GitHub** as the Git provider.
6. Sign in to GitHub if Fabric prompts you.
7. For **Repository**, choose `kkonjurka/Autoliv-ServiceNow-Fabric-POC`.
8. For **Branch**, select `main`.
9. For **Git folder**, enter `/servicenow-demo`.
10. Review the branch and folder one more time so Fabric points at the workspace subfolder instead of the repo root.
11. Select **Connect and sync**.
12. Wait for the initial sync to finish.

## 3. What you should see after sync

After the sync completes:

1. The notebooks `01_Ingest_Raw`, `02_Transform_Curated`, and `03_HTML_to_Text` appear automatically in the workspace.
2. The `ServiceNow_Lakehouse` Lakehouse item is created in the workspace.
3. Fabric tracks future notebook and Lakehouse changes through the same Git connection.

## 4. Attach each notebook to the Lakehouse

The synced notebooks need a Lakehouse attachment before you run them.

1. Open `01_Ingest_Raw`.
2. In the left **Explorer** pane, locate **Lakehouses**.
3. Select **Add lakehouse** or **Attach lakehouse**.
4. Choose `ServiceNow_Lakehouse` and confirm.
5. Repeat the same steps for `03_HTML_to_Text`.
6. Repeat the same steps for `02_Transform_Curated`.
7. Save each notebook if Fabric prompts you after attaching the Lakehouse.

## 5. Run the notebooks in order

Run the notebooks in this order:

1. **01_Ingest_Raw**
   - Calls the live Azure Container Apps mock API.
   - Pulls incidents, KB articles, attachments, images, and documents.
   - Lands raw JSON into the Lakehouse and writes the raw manifest table.
2. **03_HTML_to_Text**
   - Registers the HTML-cleaning helpers used for text normalization.
3. **02_Transform_Curated**
   - Reads the landed raw JSON.
   - Normalizes incidents, users, groups, categories, KB, notes, SLAs, changes, and asset metadata.
   - Writes the curated analytical tables plus `retrieval_documents`.

## 6. Validation checks after the run

After the notebook run finishes, confirm:

1. Raw files exist under the Lakehouse `Files/raw/servicenow/...` path.
2. The `raw_api_manifest` table contains entries for list pages and incident detail payloads.
3. Curated tables such as `incidents`, `users`, `assignment_groups`, `kb_articles`, `slas`, `attachments`, `documents`, and `retrieval_documents` are populated.
4. Cleaned text columns such as incident descriptions, resolution summaries, work notes, and KB content no longer contain HTML markup.

## 7. Next steps

After data ingestion and transformation are working:

1. Build the semantic model using the guidance in `docs/SEMANTIC_MODEL.md` and the TMDL source under `fabric/semantic-model/model.tmdl`.
2. Configure the Fabric Data Agent using `fabric/semantic-model/data-agent-config.md`.
3. Continue with the broader deployment flow described in `docs/DEPLOYMENT.md`.
