param(
  [string[]]$ComposeFiles = @("docker-compose.prod.yml"),
  [int[]]$AllowedHostPorts = @(80, 443)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Error "docker command not found."
  exit 1
}

$composeArgs = @()
foreach ($file in $ComposeFiles) {
  if (-not (Test-Path $file)) {
    Write-Error "compose file not found: $file"
    exit 1
  }
  $composeArgs += @("-f", $file)
}

$configJson = & docker compose @composeArgs config --format json 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Error "docker compose config failed:`n$configJson"
  exit $LASTEXITCODE
}

$project = $configJson | ConvertFrom-Json
$portLines = New-Object System.Collections.Generic.List[object]

foreach ($serviceProperty in $project.services.PSObject.Properties) {
  $serviceName = $serviceProperty.Name
  $service = $serviceProperty.Value
  $portsProp = $service.PSObject.Properties["ports"]
  if ($null -eq $portsProp -or $null -eq $portsProp.Value) {
    continue
  }
  $servicePorts = @($portsProp.Value)

  foreach ($port in $servicePorts) {
    if ($null -eq $port.published -or "$($port.published)" -eq "") {
      continue
    }

    $hostPort = [int]$port.published
    $containerPort = [int]$port.target
    $portLines.Add(
      [PSCustomObject]@{
        Service = $serviceName
        HostPort = $hostPort
        ContainerPort = $containerPort
        Raw = ("{0}: {1}:{2}" -f $serviceName, $hostPort, $containerPort)
      }
    ) | Out-Null
  }
}

if (-not $portLines.Count) {
  Write-Host "No host ports exposed in merged compose config."
  exit 0
}

Write-Host "Exposed host port mappings:"
$portLines | ForEach-Object {
  Write-Host ("- {0}" -f $_.Raw)
}

$unexpected = @($portLines | Where-Object { $AllowedHostPorts -notcontains $_.HostPort })
if ($unexpected.Count) {
  Write-Host ""
  Write-Host "Unexpected host ports found (not in allowlist: $($AllowedHostPorts -join ', ')):"
  $unexpected | ForEach-Object {
    Write-Host ("- {0}" -f $_.Raw)
  }
  exit 2
}

Write-Host ""
Write-Host "Port exposure check passed."
exit 0
