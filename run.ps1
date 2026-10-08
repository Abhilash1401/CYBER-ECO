# Powershell automated setup & launcher for Cyber Eco
param (
    [switch]$TestOnly,
    [switch]$Down
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if ($Down) {
    & "$PSScriptRoot\stop.ps1"
    exit 0
}

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example with secure random credentials..." -ForegroundColor Cyan
    Copy-Item ".env.example" ".env"

    $pgPass = "pg_" + [Guid]::NewGuid().ToString("N").Substring(0, 12)
    $minioPass = "minio_" + [Guid]::NewGuid().ToString("N").Substring(0, 12)
    $secretKey = "django-sec-" + [Guid]::NewGuid().ToString("N") + [Guid]::NewGuid().ToString("N")

    (Get-Content .env) `
        -replace 'POSTGRES_PASSWORD=CHANGE_ME_postgres_password', "POSTGRES_PASSWORD=$pgPass" `
        -replace 'MINIO_ROOT_PASSWORD=CHANGE_ME_minio_password', "MINIO_ROOT_PASSWORD=$minioPass" `
        -replace 'AWS_SECRET_ACCESS_KEY=CHANGE_ME_minio_password', "AWS_SECRET_ACCESS_KEY=$minioPass" `
        -replace 'DJANGO_SECRET_KEY=CHANGE_ME_generate_a_50_char_random_string', "DJANGO_SECRET_KEY=$secretKey" |
        Set-Content .env
    Write-Host ".env successfully generated with secure credentials." -ForegroundColor Green
}

if ($TestOnly) {
    Write-Host "Running tests..." -ForegroundColor Cyan
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker compose exec backend pytest
    } else {
        .\.venv\Scripts\pytest.exe backend
    }
    exit 0
}

Write-Host "Starting Cyber Eco platform..." -ForegroundColor Cyan

# Script block to poll for ports and automatically open default browser
$openBrowserJob = {
    param($urls)
    $maxWait = 60
    $waited = 0
    # Wait until port 3000 or 8000 is open
    while ($waited -lt $maxWait) {
        $p8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
        $p3000 = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
        if ($p8000 -and $p3000) {
            Start-Sleep -Seconds 1
            break
        }
        Start-Sleep -Seconds 1
        $waited++
    }
    foreach ($url in $urls) {
        Start-Process $url
    }
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Start-Job -ScriptBlock $openBrowserJob -ArgumentList @("http://127.0.0.1:3000", "http://127.0.0.1:8000/api/v1/docs/") | Out-Null
    docker compose up --build
} else {
    $env:DJANGO_SETTINGS_MODULE = "config.settings.local"
    .\.venv\Scripts\python.exe backend/manage.py migrate
    Write-Host "Starting Next.js Frontend server in background..." -ForegroundColor Cyan
    Start-Process cmd.exe -ArgumentList '/c', 'npm run dev' -WorkingDirectory "$PSScriptRoot\frontend" -WindowStyle Minimized

    Write-Host "Starting background task to open browser once services are ready..." -ForegroundColor Cyan
    Start-Job -ScriptBlock $openBrowserJob -ArgumentList @("http://127.0.0.1:3000", "http://127.0.0.1:8000/api/v1/docs/") | Out-Null

    Write-Host "Frontend server will be available at http://127.0.0.1:3000" -ForegroundColor Green
    Write-Host "Backend server running at http://127.0.0.1:8000" -ForegroundColor Green
    Write-Host "OpenAPI Swagger UI: http://127.0.0.1:8000/api/v1/docs/" -ForegroundColor Cyan
    Write-Host "Health Check:     http://127.0.0.1:8000/api/v1/health/" -ForegroundColor Cyan
    .\.venv\Scripts\python.exe backend/manage.py runserver 127.0.0.1:8000
}
