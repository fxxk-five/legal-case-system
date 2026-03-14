$ErrorActionPreference = "Stop"

$baseUrl = "http://127.0.0.1:8000/api/v1"

Write-Host "Running API smoke test..." -ForegroundColor Cyan

$loginBody = @{
    phone = "13800000000"
    password = "admin123456"
} | ConvertTo-Json

$login = Invoke-RestMethod -Uri "$baseUrl/auth/login" -Method Post -ContentType "application/json" -Body $loginBody
$headers = @{ Authorization = "Bearer $($login.access_token)" }

$me = Invoke-RestMethod -Uri "$baseUrl/users/me" -Headers $headers
$stats = Invoke-RestMethod -Uri "$baseUrl/stats/dashboard" -Headers $headers
$notifications = Invoke-RestMethod -Uri "$baseUrl/notifications" -Headers $headers
$cases = Invoke-RestMethod -Uri "$baseUrl/cases" -Headers $headers

Write-Host "User: $($me.real_name) / $($me.phone)" -ForegroundColor Green
Write-Host "Stats: lawyers=$($stats.lawyer_count), cases=$($stats.case_count), pending=$($stats.pending_lawyer_count)" -ForegroundColor Green
Write-Host "Notifications: $($notifications.Count)" -ForegroundColor Green
Write-Host "Cases: $($cases.Count)" -ForegroundColor Green
Write-Host "Smoke test passed." -ForegroundColor Green
