$ErrorActionPreference = "Stop"

$baseUrl = "http://127.0.0.1:8000/api/v1"

Write-Host "Getting demo case invite path..." -ForegroundColor Cyan

$loginBody = @{
    phone = "13800000000"
    password = "admin123456"
} | ConvertTo-Json

$login = Invoke-RestMethod -Uri "$baseUrl/auth/login" -Method Post -ContentType "application/json" -Body $loginBody
$headers = @{ Authorization = "Bearer $($login.access_token)" }

$cases = Invoke-RestMethod -Uri "$baseUrl/cases" -Headers $headers
if (-not $cases -or $cases.Count -eq 0) {
    throw "No demo cases found. Please initialize demo data first."
}

$targetCase = $cases[0]
$inviteUrl = "$baseUrl/cases/$($targetCase.id)/invite-qrcode"
$invite = Invoke-RestMethod -Uri $inviteUrl -Headers $headers

Write-Host "Demo case:" -ForegroundColor Green
Write-Host "Case number: $($targetCase.case_number)" -ForegroundColor Green
Write-Host "Title: $($targetCase.title)" -ForegroundColor Green
Write-Host "Case ID: $($targetCase.id)" -ForegroundColor Green
Write-Host ""
Write-Host "Mini-program path:" -ForegroundColor Yellow
Write-Host $invite.path -ForegroundColor Yellow
