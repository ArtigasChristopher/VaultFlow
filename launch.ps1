# VaultFlow Launch Script
# This script starts the backend and n8n using Docker, then opens the frontend in Chrome.

Write-Host "Starting VaultFlow services with Docker Compose..." -ForegroundColor Cyan

# Start Docker containers
docker compose up -d

Write-Host "Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if containers are running
$containers = docker ps --filter "name=vaultflow" --format "{{.Names}}"
if ($containers.Count -lt 2) {
    Write-Host "Warning: Some containers might not be running correctly. Check 'docker ps'." -ForegroundColor Red
}

Write-Host "Opening Frontend in Chrome..." -ForegroundColor Green

# Get the absolute path to index.html
$frontendPath = "$PSScriptRoot\frontend\index.html"

# Open in Chrome (assuming it's in the PATH or standard location)
# If Chrome is not found, it will open with default browser
try {
    Start-Process "chrome.exe" $frontendPath -ErrorAction Stop
} catch {
    Write-Host "Chrome not found. Opening with default browser." -ForegroundColor Yellow
    Start-Process $frontendPath
}

Write-Host "VaultFlow is ready!" -ForegroundColor Green
Write-Host "Backend: http://localhost:8000"
Write-Host "n8n: http://localhost:5678"
