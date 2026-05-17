Write-Host "Installing SupportLens backend dependencies..." -ForegroundColor Cyan

$packages = @(
    "fastapi",
    "uvicorn[standard]",
    "sqlalchemy",
    "pydantic",
    "pydantic-settings",
    "httpx",
    "numpy",
    "scikit-learn",
    "python-multipart",
    "aiofiles",
    "python-dateutil",
    "sentence-transformers",
    "faiss-cpu",
    "torch",
    "transformers"
)

foreach ($pkg in $packages) {
    Write-Host "  Installing $pkg..." -ForegroundColor Yellow
    & python -m pip install $pkg -q 2>&1 | Out-Null
    Write-Host "  ✓ $pkg" -ForegroundColor Green
}

Write-Host "`nInstalling spacy..." -ForegroundColor Yellow
& python -m pip install spacy -q 2>&1 | Out-Null
& python -m spacy download en_core_web_sm -q 2>&1 | Out-Null
Write-Host "  ✓ spacy + en_core_web_sm" -ForegroundColor Green

Write-Host "`nAll backend dependencies installed!" -ForegroundColor Cyan

Write-Host "`nInstalling frontend dependencies..." -ForegroundColor Cyan
Set-Location "$PSScriptRoot\frontend"
& npm install 2>&1 | Select-Object -Last 5
Write-Host "  ✓ Frontend npm packages installed" -ForegroundColor Green

Write-Host "`nSetup complete! Run .\start.ps1 to launch SupportLens." -ForegroundColor Green
