# SupportLens — Start All Services
Write-Host "`n🔍 SupportLens — Starting All Services`n" -ForegroundColor Cyan

# Check Ollama
Write-Host "Checking Ollama..." -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3
    Write-Host "  ✓ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Ollama not detected. Starting Ollama..." -ForegroundColor Red
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# Start Backend
Write-Host "`nStarting Backend (FastAPI)..." -ForegroundColor Yellow
$backendDir = "$PSScriptRoot\backend"
$backendJob = Start-Process -FilePath "python" -ArgumentList "-m uvicorn main:app --reload --port 8000" -WorkingDirectory $backendDir -PassThru -WindowStyle Normal
Write-Host "  ✓ Backend starting at http://localhost:8000" -ForegroundColor Green
Write-Host "  ✓ API docs at http://localhost:8000/docs" -ForegroundColor Green

# Wait for backend
Write-Host "`nWaiting for backend to be ready..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 2
    try {
        $h = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 2
        Write-Host "  ✓ Backend ready! Tickets: $($h.tickets_count), KB: $($h.kb_articles_count)" -ForegroundColor Green
        $ready = $true
        break
    } catch {}
    Write-Host "  ... waiting ($i/20)" -ForegroundColor DarkGray
}
if (-not $ready) { Write-Host "  ! Backend took too long — check the backend window for errors" -ForegroundColor Yellow }

# Start Frontend
Write-Host "`nStarting Frontend (Vite React)..." -ForegroundColor Yellow
$frontendDir = "$PSScriptRoot\frontend"

# Install deps if needed
if (-not (Test-Path "$frontendDir\node_modules")) {
    Write-Host "  Installing npm dependencies..." -ForegroundColor Yellow
    $npmInstall = Start-Process -FilePath "npm" -ArgumentList "install" -WorkingDirectory $frontendDir -Wait -PassThru
    Write-Host "  ✓ npm install complete" -ForegroundColor Green
}

$frontendJob = Start-Process -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory $frontendDir -PassThru -WindowStyle Normal
Write-Host "  ✓ Frontend starting at http://localhost:5173" -ForegroundColor Green

Start-Sleep -Seconds 3

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  SupportLens is RUNNING!" -ForegroundColor Green
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "  API docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Health:    http://localhost:8000/health" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor Cyan

# Open browser
Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"

Write-Host "Press any key to stop all services..." -ForegroundColor DarkGray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Cleanup
if ($backendJob) { Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue }
if ($frontendJob) { Stop-Process -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue }
Write-Host "Services stopped." -ForegroundColor Yellow
