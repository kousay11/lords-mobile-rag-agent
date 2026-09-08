$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

docker compose --env-file .env.example config | Out-Null
python -m compileall -q Ai_services scripts

Write-Host "Infrastructure configuration and Python syntax are valid."
