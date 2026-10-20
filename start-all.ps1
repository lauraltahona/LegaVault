# Inicia API y frontend en dos ventanas de PowerShell separadas.
# Uso:  .\start-all.ps1

$raiz = $PSScriptRoot

# Nota: la línea va como un SOLO string y la ruta va entre comillas dobles,
# porque Start-Process no cita los elementos de un array (la ruta tiene espacios).
function Abrir-Ventana([string]$script) {
    $ruta = Join-Path $raiz $script
    $arg = '-NoProfile -NoExit -ExecutionPolicy Bypass -File "' + $ruta + '"'
    Start-Process powershell -ArgumentList $arg
}

Write-Host "Iniciando API (backend)..." -ForegroundColor Cyan
Abrir-Ventana "start-backend.ps1"

Start-Sleep -Seconds 3

Write-Host "Iniciando interfaz (frontend)..." -ForegroundColor Cyan
Abrir-Ventana "start-frontend.ps1"

Write-Host ""
Write-Host "Listo. Abre http://localhost:5173 en el navegador." -ForegroundColor Green
Write-Host "Para detenerlos, cierra las dos ventanas o pulsa Ctrl+C en cada una." -ForegroundColor DarkGray
