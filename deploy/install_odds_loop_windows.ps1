$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$cmdPath = Join-Path $startupDir "OddsWize Odds Loop.cmd"
$psScript = Join-Path $repoRoot "deploy\\run_odds_loop.ps1"

if (-not (Test-Path $startupDir)) {
  New-Item -ItemType Directory -Path $startupDir | Out-Null
}

$cmdContent = @"
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "$psScript"
"@

Set-Content -Path $cmdPath -Value $cmdContent -Encoding ASCII
Write-Output "Startup entry created at $cmdPath"

Start-Process -FilePath "powershell" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$psScript`""
Write-Output "Odds loop started."
