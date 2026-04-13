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

function To-RelPath {
    param([string]$FullPath)

    $relative = $FullPath.Substring($ProjectRoot.Length).TrimStart("\", "/")
    return $relative.Replace("\", "/")
}

function Get-MdLinksFromFile {
    param([string]$Path)

    $content = Get-Content -Path $Path -Raw -Encoding utf8
    $pattern = '`((?:docs|plans)/[^`]+?\.md)`'
    return @([regex]::Matches($content, $pattern) |
        ForEach-Object { $_.Groups[1].Value.Replace("\", "/") } |
        Sort-Object -Unique)
}

$coreFiles = @(
    "docs/README.md",
    "docs/current-project-status.md",
    "docs/documentation-map.md",
    "docs/role-based-reading-map.md",
    "docs/restructure-overall-assessment-2026-03-26.md"
)

$allMdFiles = Get-ChildItem -Path docs, plans -Recurse -File -Filter *.md
$allDocPaths = $allMdFiles | ForEach-Object { To-RelPath $_.FullName } | Sort-Object -Unique

$missingCoreFiles = @()
foreach ($file in $coreFiles) {
    if (-not (Test-Path $file)) {
        $missingCoreFiles += $file
    }
}

$linkErrors = @()
$checkedLinks = 0
foreach ($file in $coreFiles) {
    if (-not (Test-Path $file)) {
        continue
    }

    $links = Get-MdLinksFromFile -Path $file
    foreach ($link in $links) {
        if ($link -match "\*") {
            continue
        }

        $checkedLinks += 1
        if (-not (Test-Path $link)) {
            $linkErrors += "$file -> $link"
        }
    }
}

$indexFile = "docs/documentation-map.md"
$indexLinks = @()
if (Test-Path $indexFile) {
    $indexLinks = Get-MdLinksFromFile -Path $indexFile
}

$missingInIndex = @(Compare-Object -ReferenceObject $allDocPaths -DifferenceObject $indexLinks |
    Where-Object { $_.SideIndicator -eq "<=" } |
    Select-Object -ExpandProperty InputObject)

$bomFailures = @()
foreach ($file in $allMdFiles) {
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    if ($bytes.Length -lt 3 -or $bytes[0] -ne 239 -or $bytes[1] -ne 187 -or $bytes[2] -ne 191) {
        $bomFailures += (To-RelPath $file.FullName)
    }
}

$hasError = $false

Write-Host "[docs-integrity] Project root: $ProjectRoot"
Write-Host "[docs-integrity] Core files: $($coreFiles.Count)"
Write-Host "[docs-integrity] Markdown files under docs+plans: $($allDocPaths.Count)"
Write-Host "[docs-integrity] Checked links in core files: $checkedLinks"
Write-Host "[docs-integrity] Index entries: $(@($indexLinks).Count)"

if ($missingCoreFiles.Count -gt 0) {
    $hasError = $true
    Write-Host "[docs-integrity] Missing core files:"
    $missingCoreFiles | ForEach-Object { Write-Host "  - $_" }
}

if ($linkErrors.Count -gt 0) {
    $hasError = $true
    Write-Host "[docs-integrity] Broken links in core files:"
    $linkErrors | ForEach-Object { Write-Host "  - $_" }
}

if ($missingInIndex.Count -gt 0) {
    $hasError = $true
    Write-Host "[docs-integrity] Missing entries in docs/documentation-map.md:"
    $missingInIndex | ForEach-Object { Write-Host "  - $_" }
}

if ($bomFailures.Count -gt 0) {
    $hasError = $true
    Write-Host "[docs-integrity] Files not encoded as UTF-8 with BOM:"
    $bomFailures | ForEach-Object { Write-Host "  - $_" }
}

if ($hasError) {
    Write-Host "[docs-integrity] FAIL"
    exit 1
}

Write-Host "[docs-integrity] PASS"
exit 0
