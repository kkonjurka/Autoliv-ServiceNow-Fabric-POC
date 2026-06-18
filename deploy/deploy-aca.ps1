[CmdletBinding()]
param(
    [switch]$SkipHealthCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Import-EnvFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    Get-Content -Path $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $parts = $line -split "=", 2
        if ($parts.Count -eq 2) {
            [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
        }
    }
}

function Get-RequiredSetting {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Required setting '$Name' is missing. Copy .env.example to .env and populate it first."
    }

    return $value
}

function Test-AzResource {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Command
    )

    & az @Command *> $null
    return $LASTEXITCODE -eq 0
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$envFile = Join-Path $repoRoot ".env"
$apiDir = Join-Path $repoRoot "mock-servicenow-api"
$dockerfilePath = Join-Path $apiDir "Dockerfile"

if (-not (Test-Path $envFile)) {
    throw "Missing $envFile. Copy .env.example to .env before running this script."
}

Import-EnvFile -Path $envFile

$subscriptionId = Get-RequiredSetting -Name "AZURE_SUBSCRIPTION_ID"
$location = Get-RequiredSetting -Name "AZURE_LOCATION"
$resourceGroup = Get-RequiredSetting -Name "AZURE_RESOURCE_GROUP"
$acrName = Get-RequiredSetting -Name "AZURE_CONTAINER_REGISTRY_NAME"
$acrSku = Get-RequiredSetting -Name "AZURE_CONTAINER_REGISTRY_SKU"
$containerAppsEnvName = Get-RequiredSetting -Name "AZURE_CONTAINER_APPS_ENV_NAME"
$containerAppName = Get-RequiredSetting -Name "AZURE_CONTAINER_APP_NAME"
$imageName = Get-RequiredSetting -Name "CONTAINER_IMAGE_NAME"
$imageTag = Get-RequiredSetting -Name "CONTAINER_IMAGE_TAG"
$containerPort = Get-RequiredSetting -Name "CONTAINER_PORT"
$cpu = Get-RequiredSetting -Name "ACA_CPU"
$memory = Get-RequiredSetting -Name "ACA_MEMORY"
$minReplicas = Get-RequiredSetting -Name "ACA_MIN_REPLICAS"
$maxReplicas = Get-RequiredSetting -Name "ACA_MAX_REPLICAS"
$dbPath = Get-RequiredSetting -Name "SERVICENOW_DB_PATH"
$apiHost = Get-RequiredSetting -Name "SERVICENOW_API_HOST"
$apiPort = Get-RequiredSetting -Name "SERVICENOW_API_PORT"

$reseedOnStartup = [Environment]::GetEnvironmentVariable("SERVICENOW_RESEED_ON_STARTUP", "Process")
if ([string]::IsNullOrWhiteSpace($reseedOnStartup)) {
    $reseedOnStartup = "true"
}

Write-Host "Setting Azure subscription..."
az account set --subscription $subscriptionId --only-show-errors
az extension add --name containerapp --upgrade --only-show-errors | Out-Null
az provider register --namespace Microsoft.App --wait --only-show-errors | Out-Null
az provider register --namespace Microsoft.OperationalInsights --wait --only-show-errors | Out-Null

Write-Host "Ensuring resource group exists..."
$groupExists = az group exists --name $resourceGroup | Out-String
if ($groupExists.Trim().ToLowerInvariant() -ne "true") {
    az group create --name $resourceGroup --location $location --only-show-errors | Out-Null
}

Write-Host "Ensuring Azure Container Registry exists..."
if (-not (Test-AzResource -Command @("acr", "show", "--name", $acrName, "--resource-group", $resourceGroup, "--only-show-errors"))) {
    az acr create --name $acrName --resource-group $resourceGroup --location $location --sku $acrSku --admin-enabled true --only-show-errors | Out-Null
}
else {
    az acr update --name $acrName --resource-group $resourceGroup --admin-enabled true --only-show-errors | Out-Null
}

$acrLoginServer = az acr show --name $acrName --resource-group $resourceGroup --query loginServer -o tsv --only-show-errors
$acrUsername = az acr credential show --name $acrName --query username -o tsv --only-show-errors
$acrPassword = az acr credential show --name $acrName --query passwords[0].value -o tsv --only-show-errors
$fullImageName = "$acrLoginServer/$imageName`:$imageTag"

Write-Host "Ensuring Azure Container Apps environment exists..."
if (-not (Test-AzResource -Command @("containerapp", "env", "show", "--name", $containerAppsEnvName, "--resource-group", $resourceGroup, "--only-show-errors"))) {
    az containerapp env create --name $containerAppsEnvName --resource-group $resourceGroup --location $location --only-show-errors | Out-Null
}

Write-Host "Building and pushing the image with az acr build..."
az acr build --registry $acrName --image "$imageName`:$imageTag" --file $dockerfilePath $apiDir --only-show-errors

$initialEnvVars = @(
    "SERVICENOW_API_HOST=$apiHost",
    "SERVICENOW_API_PORT=$apiPort",
    "SERVICENOW_DB_PATH=$dbPath",
    "SERVICENOW_RESEED_ON_STARTUP=$reseedOnStartup",
    "MOCK_URL_BASE=https://placeholder.invalid"
)

Write-Host "Creating or updating Azure Container App..."
if (Test-AzResource -Command @("containerapp", "show", "--name", $containerAppName, "--resource-group", $resourceGroup, "--only-show-errors")) {
    az containerapp update `
        --name $containerAppName `
        --resource-group $resourceGroup `
        --image $fullImageName `
        --cpu $cpu `
        --memory $memory `
        --min-replicas $minReplicas `
        --max-replicas $maxReplicas `
        --set-env-vars @initialEnvVars `
        --registry-server $acrLoginServer `
        --registry-username $acrUsername `
        --registry-password $acrPassword `
        --only-show-errors | Out-Null
}
else {
    az containerapp create `
        --name $containerAppName `
        --resource-group $resourceGroup `
        --environment $containerAppsEnvName `
        --image $fullImageName `
        --target-port $containerPort `
        --ingress external `
        --cpu $cpu `
        --memory $memory `
        --min-replicas $minReplicas `
        --max-replicas $maxReplicas `
        --env-vars @initialEnvVars `
        --registry-server $acrLoginServer `
        --registry-username $acrUsername `
        --registry-password $acrPassword `
        --only-show-errors | Out-Null
}

$fqdn = az containerapp show --name $containerAppName --resource-group $resourceGroup --query properties.configuration.ingress.fqdn -o tsv --only-show-errors
if ([string]::IsNullOrWhiteSpace($fqdn)) {
    throw "Azure Container App did not return an FQDN."
}

$baseUrl = "https://$fqdn"
$healthUrl = "$baseUrl/health"

Write-Host "Updating MOCK_URL_BASE to $baseUrl and forcing a reseed-aware revision..."
az containerapp update `
    --name $containerAppName `
    --resource-group $resourceGroup `
    --set-env-vars "MOCK_URL_BASE=$baseUrl" "SERVICENOW_RESEED_ON_STARTUP=true" `
    --only-show-errors | Out-Null

if (-not $SkipHealthCheck) {
    Write-Host "Validating $healthUrl ..."
    $lastError = $null
    for ($attempt = 1; $attempt -le 18; $attempt++) {
        try {
            $response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 30
            if ($response.status -eq "ok") {
                Write-Host "Health check passed."
                break
            }

            $lastError = "Health endpoint returned unexpected payload."
        }
        catch {
            $lastError = $_
        }

        if ($attempt -eq 18) {
            throw "Health check failed for $healthUrl. Last error: $lastError"
        }

        Start-Sleep -Seconds 10
    }
}

Write-Host ""
Write-Host "Deployment complete."
Write-Host "Image: $fullImageName"
Write-Host "Container App: $containerAppName"
Write-Host "Endpoint: $baseUrl"
Write-Host "Health: $healthUrl"
