param(
    [string]$ProjectRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    $ProjectRoot = (Resolve-Path $ProjectRoot).Path
}

Set-Location $ProjectRoot

if (-not (Test-Path ".git")) {
    throw "Current directory is not a git repository: $ProjectRoot"
}

$hooksPath = ".githooks"
if (-not (Test-Path $hooksPath)) {
    throw "Missing hooks directory: $hooksPath"
}

& git config --local core.hooksPath $hooksPath
if ($LASTEXITCODE -ne 0) {
    throw "Failed to set local git core.hooksPath."
}

$configuredPath = (& git config --local --get core.hooksPath).Trim()

Write-Host "[git-hooks] Project root: $ProjectRoot"
Write-Host "[git-hooks] Configured core.hooksPath: $configuredPath"
Write-Host "[git-hooks] Hooks ready:"
Write-Host "  - .githooks/pre-commit"
Write-Host "  - .githooks/pre-push"
