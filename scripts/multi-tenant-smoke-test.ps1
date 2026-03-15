$ErrorActionPreference = "Stop"

$timestamp = [DateTimeOffset]::Now.ToUnixTimeSeconds().ToString()
$suffix = $timestamp.Substring([Math]::Max(0, $timestamp.Length - 4))
$tenantCode = "org-$suffix"
$adminPhone = "139$suffix"
$lawyerPhone = "137$suffix"

$backendDir = "D:\code\law\legal-case-system\backend"
$pythonExe = Join-Path $backendDir "venv\Scripts\python.exe"

$process = Start-Process `
  -FilePath $pythonExe `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8010" `
  -WorkingDirectory $backendDir `
  -PassThru

Start-Sleep -Seconds 4

try {
  $createBody = @{
    name = "Org Demo $suffix"
    contact_name = "Admin Zhang"
    admin_phone = $adminPhone
    admin_password = "Admin123456"
    admin_real_name = "Admin Zhang"
    tenant_code = $tenantCode
  } | ConvertTo-Json

  $create = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8010/api/v1/tenants/organization" `
    -Method Post `
    -ContentType "application/json" `
    -Body $createBody

  $loginBody = @{
    phone = $adminPhone
    password = "Admin123456"
    tenant_code = $tenantCode
  } | ConvertTo-Json

  $login = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8010/api/v1/auth/login" `
    -Method Post `
    -ContentType "application/json" `
    -Body $loginBody

  $headers = @{
    Authorization = "Bearer $($login.access_token)"
  }

  $me = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8010/api/v1/users/me" `
    -Headers $headers

  $joinBody = @{
    tenant_code = $tenantCode
    phone = $lawyerPhone
    password = "Lawyer123456"
    real_name = "Lawyer Li"
  } | ConvertTo-Json

  $join = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8010/api/v1/tenants/join" `
    -Method Post `
    -ContentType "application/json" `
    -Body $joinBody

  $approve = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8010/api/v1/tenants/members/$($join.user_id)/approve" `
    -Method Patch `
    -Headers $headers

  $lawyerLoginBody = @{
    phone = $lawyerPhone
    password = "Lawyer123456"
    tenant_code = $tenantCode
  } | ConvertTo-Json

  $lawyerLogin = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8010/api/v1/auth/login" `
    -Method Post `
    -ContentType "application/json" `
    -Body $lawyerLoginBody

  Write-Output "TENANT_CODE=$tenantCode"
  Write-Output "ADMIN_PHONE=$adminPhone"
  Write-Output "LAWYER_PHONE=$lawyerPhone"
  Write-Output "TENANT_ID=$($create.tenant.id)"
  Write-Output "JOIN_USER_ID=$($join.user_id)"
  Write-Output "APPROVE_STATUS=$($approve.status)"
  Write-Output "ADMIN_ROLE=$($me.role)"
  Write-Output "LAWYER_LOGIN_OK=$(-not [string]::IsNullOrWhiteSpace($lawyerLogin.access_token))"
}
finally {
  if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
    Stop-Process -Id $process.Id
  }
}
