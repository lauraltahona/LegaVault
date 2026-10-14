# Inicia la interfaz de LegalVault (React + Vite).
# Uso:  .\start-frontend.ps1

$ErrorActionPreference = "Stop"
$frontend = Join-Path $PSScriptRoot "frontend"

Set-Location -LiteralPath $frontend

if (-not (Test-Path -LiteralPath (Join-Path $frontend "node_modules"))) {
    Write-Host "Instalando dependencias del frontend (solo la primera vez)..." -ForegroundColor Yellow
    npm install
}

Write-Host "Interfaz LegalVault  ->  http://localhost:5173" -ForegroundColor Cyan
Write-Host "(Ctrl+C para detener)" -ForegroundColor DarkGray

npm run dev
