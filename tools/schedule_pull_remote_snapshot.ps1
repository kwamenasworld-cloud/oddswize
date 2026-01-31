$ErrorActionPreference = "Stop"

$repoRoot = "C:\Users\admin\OneDrive\Documents\GitHub\Arbitrage"
$scriptPath = Join-Path $repoRoot "tools\run_pull_remote_snapshot.cmd"
$taskName = "OddsWizeHistoryPull"

if (-not (Test-Path $scriptPath)) {
    Write-Error "Runner not found: $scriptPath"
}

$existing = schtasks /Query /TN $taskName 2>$null
if ($LASTEXITCODE -eq 0) {
    schtasks /Delete /TN $taskName /F | Out-Null
}

schtasks /Create /TN $taskName /SC MINUTE /MO 15 /TR "`"$scriptPath`"" /F | Out-Null
Write-Output "Scheduled task '$taskName' to run every 15 minutes."
