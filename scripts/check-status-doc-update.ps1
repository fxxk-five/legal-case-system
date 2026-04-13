param(
    [string]$ProjectRoot,
    [string]$BaseRef,
    [string]$HeadRef
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    $ProjectRoot = (Resolve-Path $ProjectRoot).Path
}

Set-Location $ProjectRoot

$statusDoc = "docs/current-project-status.md"

function Normalize-RepoPath {
    param([string]$Path)

    return $Path.Replace("\", "/").Trim()
}

function Should-IgnorePath {
    param([string]$Path)

    $ignorePatterns = @(
        '^docs/(?!current-project-status\.md$)',
        '^plans/',
        '^\.runtime/',
        '^\.pytest_cache/',
        '^\.npm-cache/',
        '^\.claude/',
        '^storage/',
        '^mini-program/unpackage/',
        '^web-frontend/dist/',
        '^backend/venv/',
        '^backend/\.runtime/',
        '^backend/test_results\.txt$',
        '^upload-smoke\.txt$',
        '^TEST-ANALYSIS-REPORT\.md$'
    )

    foreach ($pattern in $ignorePatterns) {
        if ($Path -match $pattern) {
            return $true
        }
    }

    return $false
}

function Get-ChangedPaths {
    if (-not [string]::IsNullOrWhiteSpace($BaseRef)) {
        $resolvedHeadRef = if ([string]::IsNullOrWhiteSpace($HeadRef)) { "HEAD" } else { $HeadRef }
        $output = & git diff --name-only --diff-filter=ACDMRTUXB $BaseRef $resolvedHeadRef
        if ($LASTEXITCODE -ne 0) {
            throw "git diff failed for base '$BaseRef' and head '$resolvedHeadRef'."
        }

        return @($output |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            ForEach-Object { Normalize-RepoPath $_ } |
            Sort-Object -Unique)
    }

    $statusOutput = & git status --porcelain=v1 --untracked-files=all
    if ($LASTEXITCODE -ne 0) {
        throw "git status failed."
    }

    $paths = @()
    foreach ($line in $statusOutput) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $entry = $line.Substring(3).Trim()
        if ($entry -match ' -> ') {
            $entry = ($entry -split ' -> ')[-1].Trim()
        }

        if (-not [string]::IsNullOrWhiteSpace($entry)) {
            $paths += Normalize-RepoPath $entry
        }
    }

    return @($paths | Sort-Object -Unique)
}

$changedPaths = @(Get-ChangedPaths)
$statusDocTouched = $changedPaths -contains $statusDoc
$relevantPaths = @(
    $changedPaths |
        Where-Object {
            $_ -ne $statusDoc -and -not (Should-IgnorePath $_)
        }
)

Write-Host "[status-doc] Project root: $ProjectRoot"
Write-Host "[status-doc] Changed paths: $($changedPaths.Count)"
Write-Host "[status-doc] Relevant non-doc changes: $($relevantPaths.Count)"
Write-Host "[status-doc] Status doc touched: $statusDocTouched"

if ($relevantPaths.Count -eq 0) {
    Write-Host "[status-doc] PASS - no relevant non-doc changes detected."
    exit 0
}

if (-not $statusDocTouched) {
    Write-Host "[status-doc] FAIL - relevant changes detected without updating $statusDoc"
    Write-Host "[status-doc] Relevant paths:"
    $relevantPaths | ForEach-Object { Write-Host "  - $_" }
    Write-Host "[status-doc] Please update docs/current-project-status.md with change summary, affected modules, validation result, and status conclusion."
    exit 1
}

Write-Host "[status-doc] PASS - status doc updated together with relevant changes."
exit 0
