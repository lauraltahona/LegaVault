# Inicia la API de LegalVault (FastAPI + Uvicorn).
# Uso:  .\start-backend.ps1

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
$backend = Join-Path $raiz "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Host "No se encontró el entorno virtual en backend\.venv" -ForegroundColor Yellow
    Write-Host "Créelo una sola vez con:" -ForegroundColor Yellow
    Write-Host "  cd backend"
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

Set-Location -LiteralPath $backend
Write-Host "API LegalVault  ->  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Documentación   ->  http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "(Ctrl+C para detener)" -ForegroundColor DarkGray

& $python -m uvicorn app.main:app --reload --port 8000
