$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
& "$PSScriptRoot\.venv\Scripts\python.exe" -m flydrone.visualization.gate_replay_3d
