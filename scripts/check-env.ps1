$ErrorActionPreference = "SilentlyContinue"

$tools = @(
    @{ Name = "Python"; Command = "python"; Args = @("--version") },
    @{ Name = "Node.js"; Command = "node"; Args = @("--version") },
    @{ Name = "PostgreSQL"; Command = "psql"; Args = @("--version") },
    @{ Name = "Redis CLI"; Command = "redis-cli"; Args = @("--version") },
    @{ Name = "Docker"; Command = "docker"; Args = @("--version") },
    @{ Name = "Git"; Command = "git"; Args = @("--version") },
    @{ Name = "VS Code"; Command = "code"; Args = @("--version") }
)

Write-Host "Checking local development tools..." -ForegroundColor Cyan
Write-Host ""

foreach ($tool in $tools) {
    $command = Get-Command $tool.Command

    if ($null -eq $command) {
        Write-Host ("[MISSING] {0}" -f $tool.Name) -ForegroundColor Yellow
        continue
    }

    $output = & $tool.Command @($tool.Args) 2>&1 | Select-Object -First 1
    Write-Host ("[OK] {0}: {1}" -f $tool.Name, $output) -ForegroundColor Green
}

Write-Host ""
Write-Host "Manual checks still recommended:" -ForegroundColor Cyan
Write-Host "- Confirm PostgreSQL server is running"
Write-Host "- Confirm Redis server is running"
Write-Host "- Confirm VS Code extensions are installed"
