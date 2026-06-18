#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
API_DIR="${REPO_ROOT}/mock-servicenow-api"
DOCKERFILE_PATH="${API_DIR}/Dockerfile"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Copy .env.example to .env before running this script." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

require_setting() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "${value}" ]]; then
    echo "Required setting '${name}' is missing. Copy .env.example to .env and populate it first." >&2
    exit 1
  fi
}

for setting in \
  AZURE_SUBSCRIPTION_ID \
  AZURE_LOCATION \
  AZURE_RESOURCE_GROUP \
  AZURE_CONTAINER_REGISTRY_NAME \
  AZURE_CONTAINER_REGISTRY_SKU \
  AZURE_CONTAINER_APPS_ENV_NAME \
  AZURE_CONTAINER_APP_NAME \
  CONTAINER_IMAGE_NAME \
  CONTAINER_IMAGE_TAG \
  CONTAINER_PORT \
  ACA_CPU \
  ACA_MEMORY \
  ACA_MIN_REPLICAS \
  ACA_MAX_REPLICAS \
  SERVICENOW_API_HOST \
  SERVICENOW_API_PORT \
  SERVICENOW_DB_PATH; do
  require_setting "${setting}"
done

SERVICENOW_RESEED_ON_STARTUP="${SERVICENOW_RESEED_ON_STARTUP:-true}"

echo "Setting Azure subscription..."
az account set --subscription "${AZURE_SUBSCRIPTION_ID}" --only-show-errors
az extension add --name containerapp --upgrade --only-show-errors >/dev/null
az provider register --namespace Microsoft.App --wait --only-show-errors >/dev/null
az provider register --namespace Microsoft.OperationalInsights --wait --only-show-errors >/dev/null

echo "Ensuring resource group exists..."
if [[ "$(az group exists --name "${AZURE_RESOURCE_GROUP}")" != "true" ]]; then
  az group create \
    --name "${AZURE_RESOURCE_GROUP}" \
    --location "${AZURE_LOCATION}" \
    --only-show-errors >/dev/null
fi

echo "Ensuring Azure Container Registry exists..."
if ! az acr show --name "${AZURE_CONTAINER_REGISTRY_NAME}" --resource-group "${AZURE_RESOURCE_GROUP}" --only-show-errors >/dev/null 2>&1; then
  az acr create \
    --name "${AZURE_CONTAINER_REGISTRY_NAME}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --location "${AZURE_LOCATION}" \
    --sku "${AZURE_CONTAINER_REGISTRY_SKU}" \
    --admin-enabled true \
    --only-show-errors >/dev/null
else
  az acr update \
    --name "${AZURE_CONTAINER_REGISTRY_NAME}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --admin-enabled true \
    --only-show-errors >/dev/null
fi

ACR_LOGIN_SERVER="$(az acr show --name "${AZURE_CONTAINER_REGISTRY_NAME}" --resource-group "${AZURE_RESOURCE_GROUP}" --query loginServer -o tsv --only-show-errors)"
ACR_USERNAME="$(az acr credential show --name "${AZURE_CONTAINER_REGISTRY_NAME}" --query username -o tsv --only-show-errors)"
ACR_PASSWORD="$(az acr credential show --name "${AZURE_CONTAINER_REGISTRY_NAME}" --query passwords[0].value -o tsv --only-show-errors)"
FULL_IMAGE_NAME="${ACR_LOGIN_SERVER}/${CONTAINER_IMAGE_NAME}:${CONTAINER_IMAGE_TAG}"

echo "Ensuring Azure Container Apps environment exists..."
if ! az containerapp env show --name "${AZURE_CONTAINER_APPS_ENV_NAME}" --resource-group "${AZURE_RESOURCE_GROUP}" --only-show-errors >/dev/null 2>&1; then
  az containerapp env create \
    --name "${AZURE_CONTAINER_APPS_ENV_NAME}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --location "${AZURE_LOCATION}" \
    --only-show-errors >/dev/null
fi

echo "Building and pushing the image with az acr build..."
az acr build \
  --registry "${AZURE_CONTAINER_REGISTRY_NAME}" \
  --image "${CONTAINER_IMAGE_NAME}:${CONTAINER_IMAGE_TAG}" \
  --file "${DOCKERFILE_PATH}" \
  "${API_DIR}" \
  --only-show-errors

declare -a ENV_VARS=(
  "SERVICENOW_API_HOST=${SERVICENOW_API_HOST}"
  "SERVICENOW_API_PORT=${SERVICENOW_API_PORT}"
  "SERVICENOW_DB_PATH=${SERVICENOW_DB_PATH}"
  "SERVICENOW_RESEED_ON_STARTUP=${SERVICENOW_RESEED_ON_STARTUP}"
  "MOCK_URL_BASE=https://placeholder.invalid"
)

echo "Creating or updating Azure Container App..."
if az containerapp show --name "${AZURE_CONTAINER_APP_NAME}" --resource-group "${AZURE_RESOURCE_GROUP}" --only-show-errors >/dev/null 2>&1; then
  az containerapp update \
    --name "${AZURE_CONTAINER_APP_NAME}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --image "${FULL_IMAGE_NAME}" \
    --cpu "${ACA_CPU}" \
    --memory "${ACA_MEMORY}" \
    --min-replicas "${ACA_MIN_REPLICAS}" \
    --max-replicas "${ACA_MAX_REPLICAS}" \
    --set-env-vars "${ENV_VARS[@]}" \
    --registry-server "${ACR_LOGIN_SERVER}" \
    --registry-username "${ACR_USERNAME}" \
    --registry-password "${ACR_PASSWORD}" \
    --only-show-errors >/dev/null
else
  az containerapp create \
    --name "${AZURE_CONTAINER_APP_NAME}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --environment "${AZURE_CONTAINER_APPS_ENV_NAME}" \
    --image "${FULL_IMAGE_NAME}" \
    --target-port "${CONTAINER_PORT}" \
    --ingress external \
    --cpu "${ACA_CPU}" \
    --memory "${ACA_MEMORY}" \
    --min-replicas "${ACA_MIN_REPLICAS}" \
    --max-replicas "${ACA_MAX_REPLICAS}" \
    --env-vars "${ENV_VARS[@]}" \
    --registry-server "${ACR_LOGIN_SERVER}" \
    --registry-username "${ACR_USERNAME}" \
    --registry-password "${ACR_PASSWORD}" \
    --only-show-errors >/dev/null
fi

FQDN="$(az containerapp show --name "${AZURE_CONTAINER_APP_NAME}" --resource-group "${AZURE_RESOURCE_GROUP}" --query properties.configuration.ingress.fqdn -o tsv --only-show-errors)"
if [[ -z "${FQDN}" ]]; then
  echo "Azure Container App did not return an FQDN." >&2
  exit 1
fi

BASE_URL="https://${FQDN}"
HEALTH_URL="${BASE_URL}/health"

echo "Updating MOCK_URL_BASE to ${BASE_URL} and forcing a reseed-aware revision..."
az containerapp update \
  --name "${AZURE_CONTAINER_APP_NAME}" \
  --resource-group "${AZURE_RESOURCE_GROUP}" \
  --set-env-vars "MOCK_URL_BASE=${BASE_URL}" "SERVICENOW_RESEED_ON_STARTUP=true" \
  --only-show-errors >/dev/null

if [[ "${1:-}" != "--skip-health-check" ]]; then
  echo "Validating ${HEALTH_URL} ..."
  for attempt in {1..18}; do
    if curl --silent --show-error --fail "${HEALTH_URL}" >/dev/null; then
      echo "Health check passed."
      break
    fi

    if [[ "${attempt}" == "18" ]]; then
      echo "Health check failed for ${HEALTH_URL}." >&2
      exit 1
    fi

    sleep 10
  done
fi

echo
echo "Deployment complete."
echo "Image: ${FULL_IMAGE_NAME}"
echo "Container App: ${AZURE_CONTAINER_APP_NAME}"
echo "Endpoint: ${BASE_URL}"
echo "Health: ${HEALTH_URL}"
