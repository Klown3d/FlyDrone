$ErrorActionPreference = 'Stop'
$project = 'C:\Users\Gerof\OneDrive\Escritorio\Trabajos\FlyDrone'
Set-Location -LiteralPath $project
$env:PYTHONPATH = (Resolve-Path 'src').Path
Clear-Host
Write-Host 'FLYDRONE - GATE PROSPECTIVO DE CONECTIVIDAD NULA' -ForegroundColor Cyan
Write-Host '=================================================='
Write-Host '21 condiciones, 12 casos cada una, 252 vuelos.'
Write-Host 'No cierres esta ventana mientras se ejecuta.' -ForegroundColor Yellow
Write-Host ''
& '.\.venv\Scripts\python.exe' -m flydrone.simulation.connectome_null_protocol run --config configs/quadrotor_integrated_v4_connectome_null_prospective.yaml
Write-Host ''
if ($LASTEXITCODE -eq 0) {
    Write-Host 'GATE FINALIZADO. Los resultados fueron guardados.' -ForegroundColor Green
} else {
    Write-Host ("La ejecución terminó con código {0}." -f $LASTEXITCODE) -ForegroundColor Red
}
Write-Host 'Presiona Enter para cerrar.'
Read-Host
