[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $PSScriptRoot
Set-Location $projectDir

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required to install the pre-commit hook."
}

$hookSource = Join-Path $PSScriptRoot "pre-commit"
if (-not (Test-Path $hookSource)) {
    throw "Pre-commit hook source not found at $hookSource."
}

$hookDestination = (& git rev-parse --git-path hooks/pre-commit).Trim()
if ($LASTEXITCODE -ne 0 -or -not $hookDestination) {
    throw "Unable to locate this repository's Git hooks directory."
}

if (-not [System.IO.Path]::IsPathRooted($hookDestination)) {
    $hookDestination = Join-Path $projectDir $hookDestination
}

$hookDirectory = Split-Path -Parent $hookDestination
New-Item -ItemType Directory -Force -Path $hookDirectory | Out-Null
Copy-Item -Force -Path $hookSource -Destination $hookDestination

Write-Host "Pre-commit hook installed at $hookDestination."
