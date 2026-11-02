$ErrorActionPreference = 'Stop'
$project = 'C:\Users\Gerof\OneDrive\Escritorio\Trabajos\FlyDrone'
$report = Join-Path $project 'results\simulation\quadrotor_integrated_v4_prospective\report.json'
$processPattern = '*quadrotor_integrated_v4_prospective*'

while ($true) {
    Clear-Host
    Write-Host 'FLYDRONE - GATE V4' -ForegroundColor Cyan
    Write-Host '===================='
    Write-Host 'Resultados ya completados:'
    Write-Host '  FlyWire completo       28/30'
    Write-Host '  Sin PFL2               29/30'
    Write-Host '  Sin hDeltaB             4/30'
    Write-Host '  Sin Delta7/PFL3         0/30'
    Write-Host '  Readout directo        30/30'
    Write-Host ''
    if (Test-Path -LiteralPath $report) {
        $data = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
        Write-Host 'GATE FINALIZADO' -ForegroundColor Green
        Write-Host ("Aprobado: {0}" -f $data.passes_gate)
        Write-Host ''
        $data.summary | Select-Object controller,successes,episodes,median_maximum_cross_track_m | Format-Table -AutoSize
        Write-Host 'Criterios:'
        $data.criteria.PSObject.Properties | ForEach-Object {
            Write-Host ("  {0}: {1}" -f $_.Name,$_.Value)
        }
        break
    }
    $running = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -like 'python*' -and $_.CommandLine -like $processPattern
    }
    if ($running) {
        Write-Host 'Estado: ejecutando controlador convencional...' -ForegroundColor Yellow
        Write-Host 'El reporte final aparecera automaticamente.'
    } else {
        Write-Host 'La ejecucion ya no esta activa y aun no existe reporte.' -ForegroundColor Red
        break
    }
    Start-Sleep -Seconds 3
}
Write-Host ''
Write-Host 'Presiona Enter para cerrar.'
Read-Host
