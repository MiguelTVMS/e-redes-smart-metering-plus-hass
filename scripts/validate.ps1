[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $PSScriptRoot
Set-Location $projectDir

$venvScripts = Join-Path $projectDir ".venv\Scripts"
$venvPython = Join-Path $venvScripts "python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Local Python environment not found. Run 'make bootstrap' first."
}

$env:Path = "$venvScripts;$env:Path"

function Invoke-ValidationCommand {
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

Invoke-ValidationCommand -Command { black custom_components/ } `
    -FailureMessage "Black formatting failed."
Invoke-ValidationCommand -Command { isort custom_components/ } `
    -FailureMessage "isort formatting failed."
Invoke-ValidationCommand -Command { ruff check --fix custom_components/ } `
    -FailureMessage "Ruff automatic fixes failed."
Invoke-ValidationCommand -Command { black tests/ scripts/ } `
    -FailureMessage "Test and script Black formatting failed."
Invoke-ValidationCommand -Command { isort tests/ scripts/ } `
    -FailureMessage "Test and script isort formatting failed."
Invoke-ValidationCommand -Command { ruff check --fix tests/ scripts/ } `
    -FailureMessage "Test and script Ruff automatic fixes failed."

Invoke-ValidationCommand -Command { black --check --diff custom_components/ } `
    -FailureMessage "Black validation failed."
Invoke-ValidationCommand -Command { isort --check-only --diff custom_components/ } `
    -FailureMessage "isort validation failed."
Invoke-ValidationCommand -Command { ruff check custom_components/ } `
    -FailureMessage "Ruff validation failed."
Invoke-ValidationCommand -Command { black --check --diff tests/ scripts/ } `
    -FailureMessage "Test and script Black validation failed."
Invoke-ValidationCommand -Command { isort --check-only --diff tests/ scripts/ } `
    -FailureMessage "Test and script isort validation failed."
Invoke-ValidationCommand -Command { ruff check tests/ scripts/ } `
    -FailureMessage "Test and script Ruff validation failed."
Invoke-ValidationCommand -Command { mypy custom_components/ } `
    -FailureMessage "Mypy validation failed."
Invoke-ValidationCommand -Command { docker compose --profile tools run --rm --build tests } `
    -FailureMessage "Pytest failed."
