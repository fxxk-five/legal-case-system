param(
  [string]$MiniProgramDir = "mini-program",
  [string]$HBuilderCliPath = "",
  [string]$WechatCliPath = "",
  [switch]$SkipCompile,
  [switch]$SkipWechatOpen
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Resolve-ExistingPath {
  param([string[]]$Candidates)

  foreach ($candidate in $Candidates) {
    if ([string]::IsNullOrWhiteSpace($candidate)) {
      continue
    }
    if (Test-Path $candidate) {
      return (Resolve-Path $candidate).Path
    }
  }

  return $null
}

function Find-HBuilderCli {
  param([string]$ExplicitPath)

  $candidates = @(
    $ExplicitPath,
    $env:HBUILDERX_CLI,
    (Join-Path $env:ProgramFiles "HBuilderX\cli.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "HBuilderX\cli.exe")
  )

  $downloads = Join-Path $env:USERPROFILE "Downloads"
  if (Test-Path $downloads) {
    $downloadMatches = Get-ChildItem $downloads -Directory -Filter "HBuilderX*" -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending |
      ForEach-Object { Join-Path $_.FullName "HBuilderX\cli.exe" }
    $candidates += @($downloadMatches)
  }

  return Resolve-ExistingPath $candidates
}

function Find-WechatCli {
  param([string]$ExplicitPath)

  $candidates = @(
    $ExplicitPath,
    $env:WECHAT_DEVTOOLS_CLI,
    "D:\application\微信web开发者工具\cli.bat",
    (Join-Path $env:ProgramFiles "Tencent\微信web开发者工具\cli.bat"),
    (Join-Path ${env:ProgramFiles(x86)} "Tencent\微信web开发者工具\cli.bat"),
    (Join-Path $env:LOCALAPPDATA "微信开发者工具\cli.bat")
  )

  foreach ($root in @("D:\application", $env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA)) {
    if ([string]::IsNullOrWhiteSpace($root) -or -not (Test-Path $root)) {
      continue
    }

    $rootMatches = Get-ChildItem $root -Directory -ErrorAction SilentlyContinue |
      ForEach-Object {
        $exeCandidate = Join-Path $_.FullName "wechatdevtools.exe"
        if (Test-Path $exeCandidate) {
          Join-Path $_.FullName "cli.bat"
        }
      }

    $candidates += @($rootMatches)
  }

  return Resolve-ExistingPath $candidates
}

function Add-CheckResult {
  param(
    [System.Collections.Generic.List[object]]$Results,
    [string]$Name,
    [string]$Status,
    [string]$Detail
  )

  $Results.Add(
    [PSCustomObject]@{
      Name = $Name
      Status = $Status
      Detail = $Detail
    }
  ) | Out-Null
}

function Invoke-CheckedCommand {
  param(
    [string]$CommandPath,
    [string[]]$Arguments,
    [string]$Label,
    [string[]]$FailurePatterns = @()
  )

  Write-Host ("`n[{0}] {1} {2}" -f $Label, $CommandPath, ($Arguments -join " ")) -ForegroundColor Cyan

  $previousPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "SilentlyContinue"

    if (@(".bat", ".cmd") -contains [System.IO.Path]::GetExtension($CommandPath).ToLowerInvariant()) {
      $argumentText = ($Arguments | ForEach-Object {
        if ($_ -match '\s') {
          '"' + $_ + '"'
        }
        else {
          $_
        }
      }) -join " "
      $cmdLine = ('"{0}" {1}' -f $CommandPath, $argumentText).Trim()
      $output = & cmd.exe /c $cmdLine 2>&1 | Out-String
    }
    else {
      $output = & $CommandPath @Arguments 2>&1 | Out-String
    }
  }
  finally {
    $ErrorActionPreference = $previousPreference
  }

  $output = ($output | Out-String).Trim()
  if ($LASTEXITCODE -ne 0) {
    if ([string]::IsNullOrWhiteSpace($output)) {
      throw "$Label failed with exit code $LASTEXITCODE."
    }
    throw "$Label failed with exit code $LASTEXITCODE.`n$output"
  }

  foreach ($pattern in $FailurePatterns) {
    if (-not [string]::IsNullOrWhiteSpace($pattern) -and $output.Contains($pattern)) {
      throw "$Label failed.`n$output"
    }
  }

  if (-not [string]::IsNullOrWhiteSpace($output)) {
    Write-Host $output
  }

  return $output
}

$results = New-Object System.Collections.Generic.List[object]
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$miniProgramPath = (Resolve-Path (Join-Path $repoRoot $MiniProgramDir)).Path
$manifestPath = Join-Path $miniProgramPath "manifest.json"
$sourceProjectConfigPath = Join-Path $miniProgramPath "project.config.json"
$mpWeixinDistPath = Join-Path $miniProgramPath "unpackage\dist\dev\mp-weixin"
$compiledProjectConfigPath = Join-Path $mpWeixinDistPath "project.config.json"

if (-not (Test-Path $manifestPath)) {
  Write-Error "manifest not found: $manifestPath"
  exit 1
}

$manifest = Get-Content $manifestPath -Encoding UTF8 -Raw | ConvertFrom-Json
$manifestAppId = $manifest.'mp-weixin'.appid
if ([string]::IsNullOrWhiteSpace($manifestAppId)) {
  Write-Error "manifest.json missing mp-weixin appid."
  exit 1
}

$hbuilderCli = Find-HBuilderCli -ExplicitPath $HBuilderCliPath
$wechatCli = Find-WechatCli -ExplicitPath $WechatCliPath

if (-not $hbuilderCli) {
  Write-Error "HBuilderX CLI not found. Set HBUILDERX_CLI or pass -HBuilderCliPath."
  exit 1
}

if (-not $wechatCli) {
  Write-Error "WeChat DevTools CLI not found. Set WECHAT_DEVTOOLS_CLI or pass -WechatCliPath."
  exit 1
}

$hbuilderExe = Resolve-ExistingPath @((Join-Path (Split-Path $hbuilderCli -Parent) "HBuilderX.exe"))
$wechatExe = Resolve-ExistingPath @(
  (Join-Path (Split-Path $wechatCli -Parent) "微信开发者工具.exe"),
  (Join-Path (Split-Path $wechatCli -Parent) "wechatdevtools.exe")
)

Add-CheckResult -Results $results -Name "repo-root" -Status "ok" -Detail $repoRoot
Add-CheckResult -Results $results -Name "mini-program-dir" -Status "ok" -Detail $miniProgramPath
Add-CheckResult -Results $results -Name "manifest-appid" -Status "ok" -Detail $manifestAppId
Add-CheckResult -Results $results -Name "hbuilder-cli" -Status "ok" -Detail $hbuilderCli
Add-CheckResult -Results $results -Name "wechat-cli" -Status "ok" -Detail $wechatCli

if ($hbuilderExe) {
  Add-CheckResult -Results $results -Name "hbuilder-exe" -Status "ok" -Detail $hbuilderExe
}

if ($wechatExe) {
  Add-CheckResult -Results $results -Name "wechat-exe" -Status "ok" -Detail $wechatExe
}

if (Test-Path $sourceProjectConfigPath) {
  Add-CheckResult -Results $results -Name "source-project-config" -Status "warn" -Detail "unexpected file exists at $sourceProjectConfigPath"
}
else {
  Add-CheckResult -Results $results -Name "source-project-config" -Status "ok" -Detail "source directory has no project.config.json (expected)"
}

$hbuilderOpenOutput = Invoke-CheckedCommand -CommandPath $hbuilderCli -Arguments @("open") -Label "HBuilderX open"
Add-CheckResult -Results $results -Name "hbuilder-open" -Status "ok" -Detail ($hbuilderOpenOutput -replace "\s+", " ")
Start-Sleep -Seconds 3

$hbuilderVersion = Invoke-CheckedCommand -CommandPath $hbuilderCli -Arguments @("--version") -Label "HBuilderX version" -FailurePatterns @("未检测到已打开的HBuilderX")
Add-CheckResult -Results $results -Name "hbuilder-version" -Status "ok" -Detail ($hbuilderVersion -replace "\s+", " ")

$projectOpenOutput = Invoke-CheckedCommand -CommandPath $hbuilderCli -Arguments @("project", "open", "--path", $miniProgramPath) -Label "HBuilderX project open" -FailurePatterns @("未检测到已打开的HBuilderX")
Add-CheckResult -Results $results -Name "hbuilder-project-open" -Status "ok" -Detail ($projectOpenOutput -replace "\s+", " ")

if (-not $SkipCompile) {
  $compileFailurePatterns = @(
    "未检测到已打开的HBuilderX",
    "编译失败",
    "Module Error",
    "Module build failed",
    "Errors compiling template",
    "语法错误"
  )
  $compileArgs = @("launch", "mp-weixin", "--project", $miniProgramPath, "--compile", "true", "--continue-on-error", "false")
  $compileOutput = Invoke-CheckedCommand -CommandPath $hbuilderCli -Arguments $compileArgs -Label "HBuilderX compile" -FailurePatterns $compileFailurePatterns
  Add-CheckResult -Results $results -Name "hbuilder-compile" -Status "ok" -Detail ($compileOutput -replace "\s+", " ")
}
else {
  Add-CheckResult -Results $results -Name "hbuilder-compile" -Status "skip" -Detail "skipped by -SkipCompile"
}

if (-not (Test-Path $compiledProjectConfigPath)) {
  Write-Error "compiled project config not found: $compiledProjectConfigPath"
  exit 1
}

$compiledConfig = Get-Content $compiledProjectConfigPath -Encoding UTF8 -Raw | ConvertFrom-Json
$compiledAppId = $compiledConfig.appid
if ($compiledAppId -ne $manifestAppId) {
  Write-Error "appid mismatch: manifest=$manifestAppId compiled=$compiledAppId"
  exit 1
}

Add-CheckResult -Results $results -Name "compiled-project-config" -Status "ok" -Detail $compiledProjectConfigPath
Add-CheckResult -Results $results -Name "compiled-appid" -Status "ok" -Detail $compiledAppId

$wechatLoginOutput = Invoke-CheckedCommand -CommandPath $wechatCli -Arguments @("islogin", "--lang", "zh") -Label "WeChat DevTools login"
if ($wechatLoginOutput -match '"login"\s*:\s*true') {
  Add-CheckResult -Results $results -Name "wechat-login" -Status "ok" -Detail ($wechatLoginOutput -replace "\s+", " ")
}
else {
  Write-Error "WeChat DevTools CLI is not logged in: $wechatLoginOutput"
  exit 1
}

if (-not $SkipWechatOpen) {
  $wechatOpenOutput = Invoke-CheckedCommand -CommandPath $wechatCli -Arguments @("open", "--project", $mpWeixinDistPath, "--lang", "zh") -Label "WeChat DevTools open"
  Add-CheckResult -Results $results -Name "wechat-open" -Status "ok" -Detail ($wechatOpenOutput -replace "\s+", " ")
}
else {
  Add-CheckResult -Results $results -Name "wechat-open" -Status "skip" -Detail "skipped by -SkipWechatOpen"
}

Write-Host "`nMini-program toolchain preflight summary:" -ForegroundColor Green
$results | Format-Table -AutoSize | Out-String | Write-Host

$warnings = @($results | Where-Object { $_.Status -eq "warn" })
if ($warnings.Count) {
  Write-Host "Warnings:" -ForegroundColor Yellow
  $warnings | ForEach-Object {
    Write-Host ("- {0}: {1}" -f $_.Name, $_.Detail) -ForegroundColor Yellow
  }
}

Write-Host "`nMini-program toolchain preflight passed." -ForegroundColor Green
exit 0


