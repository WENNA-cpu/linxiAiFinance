# Push to GitHub (works around local SSL cert issues)
# Usage: .\scripts\push.ps1 [branch, default master]

$ErrorActionPreference = "Continue"
$env:GIT_SSL_NO_VERIFY = "true"

$branch = if ($args.Count -gt 0) { $args[0] } else { "master" }

Set-Location (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))

Write-Host "Pushing to origin/$branch ..." -ForegroundColor Cyan
git push origin $branch

Write-Host ""
& "$PSScriptRoot\verify-git.ps1"
