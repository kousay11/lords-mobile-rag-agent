[CmdletBinding()]
param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Warning "Created .env from .env.example. Replace all development secrets before sharing or deploying."
}

$composeArgs = @("compose", "--env-file", ".env", "up", "-d")
if ($Build) { $composeArgs += "--build" }
& docker @composeArgs
