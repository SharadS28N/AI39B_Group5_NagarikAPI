Param(
    [switch]$ForceRecreateVenv
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if ($ForceRecreateVenv -and (Test-Path "venv")) {
    Remove-Item -Recurse -Force "venv"
}

if (-not (Test-Path "venv")) {
    python -m venv venv
}

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& "venv\Scripts\Activate.ps1"

python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

Write-Host "Setup complete."
Write-Host "Next: .\scripts\dev.ps1"
