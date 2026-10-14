# Inicia API y frontend en dos ventanas de PowerShell separadas.
# Uso:  .\start-all.ps1

$raiz = $PSScriptRoot

Write-Host "Iniciando API (backend)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $raiz "start-backend.ps1")
)

Start-Sleep -Seconds 3

Write-Host "Iniciando interfaz (frontend)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $raiz "start-frontend.ps1")
)

Write-Host ""
Write-Host "Listo. Abre http://localhost:5173 en el navegador." -ForegroundColor Green
Write-Host "Para detenerlos, cierra las dos ventanas o pulsa Ctrl+C en cada una." -ForegroundColor DarkGray
