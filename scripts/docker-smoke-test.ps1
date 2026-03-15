$ErrorActionPreference = "Stop"

$baseUrl = "http://127.0.0.1:8000/api/v1"

Write-Host "Running Docker smoke test..." -ForegroundColor Cyan

$health = Invoke-RestMethod -Uri "$baseUrl/health"
if ($health.status -ne "ok") {
    throw "Health check failed."
}

$loginBody = @{
    phone = "13800000000"
    password = "admin123456"
} | ConvertTo-Json

$login = Invoke-RestMethod -Uri "$baseUrl/auth/login" -Method Post -ContentType "application/json" -Body $loginBody
$headers = @{ Authorization = "Bearer $($login.access_token)" }

$me = Invoke-RestMethod -Uri "$baseUrl/users/me" -Headers $headers
$cases = Invoke-RestMethod -Uri "$baseUrl/cases" -Headers $headers
$stats = Invoke-RestMethod -Uri "$baseUrl/stats/dashboard" -Headers $headers

Write-Host "Health: ok" -ForegroundColor Green
Write-Host "User: $($me.real_name) / $($me.phone)" -ForegroundColor Green
Write-Host "Cases: $($cases.Count)" -ForegroundColor Green
Write-Host "Stats: lawyers=$($stats.lawyer_count), cases=$($stats.case_count), pending=$($stats.pending_lawyer_count)" -ForegroundColor Green
Write-Host "Docker smoke test passed." -ForegroundColor Green
