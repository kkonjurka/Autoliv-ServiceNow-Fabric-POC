# Mock ServiceNow API deployment

This deployment packages the FastAPI mock ServiceNow API from `mock-servicenow-api\` into a container image, publishes it to Azure Container Registry (ACR), and deploys it to Azure Container Apps (ACA) with external HTTPS ingress.

## Prerequisites

- Azure CLI with permission to create resource groups, ACR, and ACA resources
- Docker Desktop or Docker Engine for local image validation
- PowerShell 7+ or Bash
- A local `.env` file copied from the repository-root `.env.example`

## Naming conventions

- **Container image:** `<acr-login-server>/<CONTAINER_IMAGE_NAME>:<CONTAINER_IMAGE_TAG>`
- **Azure Container App:** the `AZURE_CONTAINER_APP_NAME` value from `.env`
- **Public endpoint format:** `https://<azure-container-app-name>.<generated-suffix>.<region>.azurecontainerapps.io`
- **Health check path:** `/health`

Recommended defaults:

| Setting | Default |
| --- | --- |
| `CONTAINER_IMAGE_NAME` | `servicenow-mock-api` |
| `AZURE_CONTAINER_APP_NAME` | `aca-servicenow-mock-api` |
| `AZURE_CONTAINER_APPS_ENV_NAME` | `acae-autoliv-servicenow-poc` |

## Configuration file

From the repository root:

```powershell
Copy-Item .env.example .env
```

Populate `.env` with Azure subscription and resource names before deploying. Quote any value that contains spaces if you plan to use the Bash deploy script. Keep secrets only in `.env`, CI/CD secret stores, or ACA secrets.

## Docker build details

`mock-servicenow-api\Dockerfile` is a multi-stage build that:

1. Installs Python dependencies into a virtual environment in a builder stage.
2. Copies the FastAPI app and the seeded SQLite database into the runtime image.
3. Exposes port `8000`.
4. Starts the API with `python -m app.main`.

The image bundles `mock-servicenow-api\data\servicenow_mock.sqlite` at build time. For Azure deployments, the deploy scripts set `SERVICENOW_RESEED_ON_STARTUP=true` so asset mock URLs are regenerated with the live ACA HTTPS hostname.

## Local Docker validation

Build locally from the repository root:

```powershell
docker build -t servicenow-mock-api:local .\mock-servicenow-api
```

Run the container:

```powershell
docker run --rm -p 8000:8000 `
  -e SERVICENOW_RESEED_ON_STARTUP=true `
  -e MOCK_URL_BASE=http://localhost:8000 `
  servicenow-mock-api:local
```

Validate the health endpoint in another terminal:

```powershell
Invoke-RestMethod http://localhost:8000/health | ConvertTo-Json -Depth 4
```

Expected result: JSON with `"status": "ok"` plus seeded incident and KB article counts.

## Azure Container Registry push steps

The deployment scripts use `az acr build`, which builds inside ACR and pushes automatically. If you want a manual Docker push flow instead:

```powershell
az acr login --name $env:AZURE_CONTAINER_REGISTRY_NAME
docker build -t "$($env:AZURE_CONTAINER_REGISTRY_NAME).azurecr.io/$($env:CONTAINER_IMAGE_NAME):$($env:CONTAINER_IMAGE_TAG)" .\mock-servicenow-api
docker push "$($env:AZURE_CONTAINER_REGISTRY_NAME).azurecr.io/$($env:CONTAINER_IMAGE_NAME):$($env:CONTAINER_IMAGE_TAG)"
```

## Azure Container Apps deployment

### PowerShell

```powershell
.\deploy\deploy-aca.ps1
```

### Bash

```bash
bash ./deploy/deploy-aca.sh
```

Both scripts:

1. Load settings from repository-root `.env`
2. Ensure the resource group exists
3. Ensure the ACR instance exists and has admin access enabled for the deployment
4. Ensure the ACA environment exists
5. Build and push the image with `az acr build`
6. Create or update the ACA app with external ingress on port `8000`
7. Read the generated ACA FQDN
8. Update `MOCK_URL_BASE` to the live HTTPS endpoint and create a fresh revision
9. Validate `GET /health`

## Health check validation

After deployment, verify:

```powershell
Invoke-RestMethod "$env:MOCK_SERVICENOW_API_BASE_URL/health" | ConvertTo-Json -Depth 4
```

If you did not export the URL into your shell, retrieve it directly:

```powershell
$fqdn = az containerapp show `
  --name $env:AZURE_CONTAINER_APP_NAME `
  --resource-group $env:AZURE_RESOURCE_GROUP `
  --query properties.configuration.ingress.fqdn `
  -o tsv
Invoke-RestMethod "https://$fqdn/health" | ConvertTo-Json -Depth 4
```

## Rollback and redeploy notes

- **Redeploy same app:** update `CONTAINER_IMAGE_TAG` in `.env` and rerun a deploy script.
- **Rollback:** set `CONTAINER_IMAGE_TAG` back to the last known-good tag and rerun the deploy script.
- **Current persistence model:** ACA container storage is ephemeral. The SQLite database is bundled with the image, and the deployment scripts intentionally reseed on startup for deterministic demo data.
- **Future durable state:** if the demo later needs mutable or persistent data, move SQLite off the container filesystem and onto Azure Files, Azure SQL, or another managed durable store.

## Environment variables reference

### Deployment settings (`.env`)

| Variable | Purpose | Secret |
| --- | --- | --- |
| `AZURE_SUBSCRIPTION_ID` | Subscription targeted by `az account set` | Yes |
| `AZURE_TENANT_ID` | Tenant for CI/CD service principal or workload identity | Yes |
| `AZURE_CLIENT_ID` | Client/application ID for CI/CD auth | Yes |
| `AZURE_CLIENT_SECRET` | Service principal secret when OIDC is not used | Yes |
| `AZURE_LOCATION` | Azure region for RG, ACR, and ACA | No |
| `AZURE_RESOURCE_GROUP` | Resource group name | No |
| `AZURE_CONTAINER_REGISTRY_NAME` | ACR resource name | No |
| `AZURE_CONTAINER_REGISTRY_SKU` | ACR SKU, usually `Basic` for the POC | No |
| `AZURE_CONTAINER_APPS_ENV_NAME` | ACA managed environment name | No |
| `AZURE_CONTAINER_APP_NAME` | ACA application name | No |
| `CONTAINER_IMAGE_NAME` | Repository/image name inside ACR | No |
| `CONTAINER_IMAGE_TAG` | Deployable image tag | No |
| `CONTAINER_PORT` | Exposed application port (`8000`) | No |
| `ACA_CPU` | CPU allocation for the app | No |
| `ACA_MEMORY` | Memory allocation for the app | No |
| `ACA_MIN_REPLICAS` | Minimum replica count | No |
| `ACA_MAX_REPLICAS` | Maximum replica count | No |

### Runtime settings passed to ACA

| Variable | Purpose | Secret |
| --- | --- | --- |
| `SERVICENOW_API_HOST` | Binds uvicorn to `0.0.0.0` | No |
| `SERVICENOW_API_PORT` | Container listening port (`8000`) | No |
| `SERVICENOW_DB_PATH` | SQLite file path inside the container | No |
| `SERVICENOW_RESEED_ON_STARTUP` | Forces deterministic reseed on ACA revision startup | No |
| `MOCK_URL_BASE` | Public base URL used to generate attachment/document/image mock URLs | No |
| `API_AUTH_HEADER_NAME` | Optional future auth header name | No |
| `API_AUTH_HEADER_VALUE` | Optional future auth header value; store in ACA secrets if the API adds auth | Yes |

## CI/CD secret guidance

Use GitHub Actions secrets or Azure DevOps variable groups for:

- `AZURE_SUBSCRIPTION_ID`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET` (unless you use OIDC/federated credentials)
- `API_AUTH_HEADER_VALUE` if demo authentication is added later

Do not commit Azure client secrets, Fabric tokens, registry passwords, or runtime API secrets to source control.
