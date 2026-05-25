$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    throw "Virtual environment not found. Run .\scripts\setup.ps1 first."
}

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& "venv\Scripts\Activate.ps1"
python run.py
