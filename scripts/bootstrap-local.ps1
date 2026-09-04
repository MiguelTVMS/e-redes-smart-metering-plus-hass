[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $PSScriptRoot
Set-Location $projectDir

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory)]
        [scriptblock] $Command,
        [Parameter(Mandatory)]
        [string] $FailureMessage
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install it with: winget install --exact --id astral-sh.uv"
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required. Install it with: winget install --exact --id Docker.DockerDesktop"
}

Invoke-NativeCommand -Command { docker info --format "{{.ServerVersion}}" } `
    -FailureMessage "Docker Desktop is installed but its engine is not running."

Write-Host "Locating Python 3.14..."
& uv python find 3.14 *> $null
if ($LASTEXITCODE -ne 0) {
    & uv python install 3.14
    if ($LASTEXITCODE -ne 0) {
        & uv python find 3.14 *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "uv could not install or locate Python 3.14."
        }

        Write-Warning "uv reported an installation-link error, but Python 3.14 is available and will be used."
    }
}

$venvPython = Join-Path $projectDir ".venv\Scripts\python.exe"
$reuseVenv = $false
if (Test-Path $venvPython) {
    & $venvPython -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 14))"
    $reuseVenv = $LASTEXITCODE -eq 0
}

if ($reuseVenv) {
    Write-Host "Reusing the existing Python 3.14 environment..."
}
else {
    Write-Host "Creating the local Python environment..."
    Invoke-NativeCommand -Command { uv venv --clear --python 3.14 .venv } `
        -FailureMessage "Failed to create the local Python 3.14 environment."
}

Write-Host "Installing development dependencies..."
Invoke-NativeCommand `
    -Command { uv pip install --link-mode copy --python $venvPython -r requirements_dev.txt } `
    -FailureMessage "Failed to install development dependencies."

Write-Host "Installing the Git pre-commit hook..."
& "$PSScriptRoot\install-hooks.ps1"

Write-Host ""
Write-Host "Local development environment is ready."
Write-Host "Run 'make ha-up' to start Home Assistant."
Write-Host "Open http://localhost:8123 after it starts."
