# Verify git commits and remote sync (PowerShell-safe)
# Usage: .\scripts\verify-git.ps1

$ErrorActionPreference = "Continue"
$env:GIT_SSL_NO_VERIFY = "true"

Set-Location (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))

Write-Host "=== Recent commits ===" -ForegroundColor Cyan
git log -3 --oneline

Write-Host ""
Write-Host "=== Working tree ===" -ForegroundColor Cyan
git status -sb

Write-Host ""
Write-Host "=== Fetch origin/master ===" -ForegroundColor Cyan
git fetch origin master 2>&1 | ForEach-Object { Write-Host $_ }

$local = (git rev-parse HEAD).Trim()
$remote = (git rev-parse origin/master).Trim()

Write-Host ""
Write-Host "=== Local vs remote ===" -ForegroundColor Cyan
Write-Host "local:  $local"
Write-Host "remote: $remote"

if ($local -eq $remote) {
    Write-Host ""
    Write-Host "OK: in sync with origin/master" -ForegroundColor Green
    exit 0
}

$ahead = @(git log origin/master..HEAD --oneline)
if ($ahead.Count -gt 0) {
    Write-Host ""
    Write-Host "Unpushed commits:" -ForegroundColor Yellow
    $ahead | Out-Host
    Write-Host "Run: .\scripts\push.ps1" -ForegroundColor Yellow
    exit 1
}

$behind = @(git log HEAD..origin/master --oneline)
if ($behind.Count -gt 0) {
    Write-Host ""
    Write-Host "Local is behind remote. Run: git pull" -ForegroundColor Yellow
    $behind | Out-Host
    exit 1
}

exit 0
