$ErrorActionPreference = "Stop"

function Get-HttpErrorMessage {
  param(
    [Parameter(Mandatory = $true)]
    [System.Management.Automation.ErrorRecord]$ErrorRecord
  )

  if ($ErrorRecord.ErrorDetails -and $ErrorRecord.ErrorDetails.Message) {
    return $ErrorRecord.ErrorDetails.Message
  }

  return $ErrorRecord.Exception.Message
}

function Wait-BackendReady {
  param(
    [Parameter(Mandatory = $true)]
    [string]$HealthUrl,
    [int]$MaxRetries = 40,
    [int]$DelaySeconds = 1
  )

  for ($i = 1; $i -le $MaxRetries; $i++) {
    try {
      $resp = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 3
      if ($resp.status -eq "ok") {
        return
      }
    }
    catch {
      Start-Sleep -Seconds $DelaySeconds
    }
  }

  throw "Backend did not become ready in time: $HealthUrl"
}

$timestampSeed = [DateTimeOffset]::Now.ToUnixTimeMilliseconds().ToString()
$suffix = $timestampSeed.Substring([Math]::Max(0, $timestampSeed.Length - 8)).PadLeft(8, "0")
$tenantCode = "org-$suffix"
$adminPhone = "139$suffix"
$lawyerPhone = "137$suffix"
$wechatCode = "invite-lawyer-$suffix"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $repoRoot "backend"
$pythonExe = Join-Path $backendDir "venv\\Scripts\\python.exe"
$baseUrl = "http://127.0.0.1:8010/api/v1"
$healthUrl = "$baseUrl/health"

if (-not (Test-Path $pythonExe)) {
  throw "Python executable not found: $pythonExe"
}

$backendProcess = Start-Process `
  -FilePath $pythonExe `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8010" `
  -WorkingDirectory $backendDir `
  -PassThru

try {
  Wait-BackendReady -HealthUrl $healthUrl

  $createBody = @{
    name = "Org Demo $suffix"
    contact_name = "Admin Zhang"
    admin_phone = $adminPhone
    admin_password = "Admin123456"
    admin_real_name = "Admin Zhang"
    tenant_code = $tenantCode
  } | ConvertTo-Json

  $create = Invoke-RestMethod `
    -Uri "$baseUrl/tenants/organization" `
    -Method Post `
    -ContentType "application/json" `
    -Body $createBody

  $loginBody = @{
    phone = $adminPhone
    password = "Admin123456"
    tenant_code = $tenantCode
  } | ConvertTo-Json

  $adminLogin = Invoke-RestMethod `
    -Uri "$baseUrl/auth/login" `
    -Method Post `
    -ContentType "application/json" `
    -Body $loginBody

  $adminHeaders = @{
    Authorization = "Bearer $($adminLogin.access_token)"
  }

  $miniHeaders = @{
    "X-Client-Platform" = "mini-program"
    "X-Client-Source" = "wx-mini"
  }

  $invite = Invoke-RestMethod `
    -Uri "$baseUrl/users/invite-lawyer" `
    -Method Post `
    -Headers $adminHeaders

  if (-not $invite.token) {
    throw "Invite response missing token: $($invite | ConvertTo-Json -Compress)"
  }

  $wxLoginBody = @{
    code = $wechatCode
    lawyer_invite_token = $invite.token
  } | ConvertTo-Json

  $wxLogin = Invoke-RestMethod `
    -Uri "$baseUrl/auth/wx-mini-login" `
    -Method Post `
    -ContentType "application/json" `
    -Headers $miniHeaders `
    -Body $wxLoginBody

  if (-not $wxLogin.need_bind_phone -or -not $wxLogin.wx_session_ticket) {
    throw "wx-mini-login unexpected payload: $($wxLogin | ConvertTo-Json -Compress)"
  }

  $wxPhoneBody = @{
    phone_code = $lawyerPhone
    wx_session_ticket = $wxLogin.wx_session_ticket
    lawyer_invite_token = $invite.token
    real_name = "Lawyer Li"
  } | ConvertTo-Json

  $wxPhoneLogin = Invoke-RestMethod `
    -Uri "$baseUrl/auth/wx-mini-phone-login" `
    -Method Post `
    -ContentType "application/json" `
    -Headers $miniHeaders `
    -Body $wxPhoneBody

  if ($wxPhoneLogin.login_state -ne "PENDING_APPROVAL") {
    throw "Expected PENDING_APPROVAL, got: $($wxPhoneLogin | ConvertTo-Json -Compress)"
  }
  if (-not $wxPhoneLogin.user.id) {
    throw "Pending user id missing: $($wxPhoneLogin | ConvertTo-Json -Compress)"
  }

  $pendingUserId = [int]$wxPhoneLogin.user.id

  $approve = Invoke-RestMethod `
    -Uri "$baseUrl/users/$pendingUserId/approve" `
    -Method Patch `
    -Headers $adminHeaders

  $wxReloginBody = @{
    code = $wechatCode
  } | ConvertTo-Json

  $lawyerLogin = Invoke-RestMethod `
    -Uri "$baseUrl/auth/wx-mini-login" `
    -Method Post `
    -ContentType "application/json" `
    -Headers $miniHeaders `
    -Body $wxReloginBody

  if (-not $lawyerLogin.access_token) {
    throw "Lawyer re-login missing access token: $($lawyerLogin | ConvertTo-Json -Compress)"
  }

  $lawyerHeaders = @{
    Authorization = "Bearer $($lawyerLogin.access_token)"
    "X-Client-Platform" = "mini-program"
    "X-Client-Source" = "wx-mini"
  }

  $lawyerMe = Invoke-RestMethod `
    -Uri "$baseUrl/users/me" `
    -Headers $lawyerHeaders

  Write-Output "TENANT_CODE=$tenantCode"
  Write-Output "TENANT_ID=$($create.tenant.id)"
  Write-Output "ADMIN_PHONE=$adminPhone"
  Write-Output "LAWYER_PHONE=$lawyerPhone"
  Write-Output "INVITE_TOKEN=$($invite.token)"
  Write-Output "PENDING_USER_ID=$pendingUserId"
  Write-Output "PENDING_LOGIN_STATE=$($wxPhoneLogin.login_state)"
  Write-Output "APPROVE_STATUS=$($approve.status)"
  Write-Output "LAWYER_ROLE=$($lawyerMe.role)"
  Write-Output "LAWYER_STATUS=$($lawyerMe.status)"
  Write-Output "LAWYER_LOGIN_OK=$(-not [string]::IsNullOrWhiteSpace($lawyerLogin.access_token))"
}
catch {
  $message = Get-HttpErrorMessage -ErrorRecord $_
  Write-Error "Smoke test failed: $message"
  throw
}
finally {
  if ($backendProcess -and (Get-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $backendProcess.Id
  }
}
