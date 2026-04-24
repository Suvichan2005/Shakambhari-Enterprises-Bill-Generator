param(
    [Parameter(Mandatory=$true)][string]$ProjectId,
    [Parameter(Mandatory=$true)][string]$SpreadsheetId,
    [Parameter(Mandatory=$true)][string]$BucketName,
    [string]$ServiceName = "shakambhari-invoices",
    [string]$Region = "asia-south1",
    [string]$ServiceAccountEmail,
    [string]$AppPassword,
    [string]$FlaskSecretKey
)

$ErrorActionPreference = "Stop"

if (-not $AppPassword) {
    throw "AppPassword is required. Pass -AppPassword 'your-strong-password'"
}

if (-not $FlaskSecretKey) {
    $existingService = gcloud run services describe $ServiceName --region $Region --project $ProjectId --format=json 2>$null
    if ($LASTEXITCODE -eq 0 -and $existingService) {
        try {
            $serviceObj = $existingService | ConvertFrom-Json
            $existingSecret = $serviceObj.spec.template.spec.containers[0].env |
                Where-Object { $_.name -eq 'FLASK_SECRET_KEY' } |
                Select-Object -First 1

            if ($existingSecret -and $existingSecret.value) {
                $FlaskSecretKey = $existingSecret.value
                Write-Host "Reusing existing FLASK_SECRET_KEY from current Cloud Run service."
            }
        }
        catch {
            # Fall back to generated key below.
        }
    }

    if (-not $FlaskSecretKey) {
        $FlaskSecretKey = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
        Write-Host "Generated FLASK_SECRET_KEY automatically."
    }
}

if (-not $ServiceAccountEmail) {
    $ServiceAccountEmail = "shakambhari-app@$ProjectId.iam.gserviceaccount.com"
    Write-Host "Using default Cloud Run service account: $ServiceAccountEmail"
}

Push-Location $PSScriptRoot
try {
    py -3 preflight_check.py
    if ($LASTEXITCODE -ne 0) {
        throw "Preflight failed. Fix issues before deploy."
    }

    gcloud config set project $ProjectId

    gcloud services enable run.googleapis.com cloudbuild.googleapis.com sheets.googleapis.com storage.googleapis.com

    gcloud run deploy $ServiceName `
        --source . `
        --region $Region `
        --platform managed `
        --allow-unauthenticated `
        --service-account $ServiceAccountEmail `
        --set-env-vars "GOOGLE_CLOUD_PROJECT=$ProjectId,SPREADSHEET_ID=$SpreadsheetId,GCS_BUCKET_NAME=$BucketName,FLASK_SECRET_KEY=$FlaskSecretKey,APP_PASSWORD=$AppPassword,FLASK_ENV=production,SESSION_COOKIE_SECURE=true"

    if ($LASTEXITCODE -ne 0) {
        throw "Cloud Run deployment failed."
    }

    Write-Host "Deployment completed successfully." -ForegroundColor Green
}
finally {
    Pop-Location
}
