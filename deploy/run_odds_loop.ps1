$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$envPath = Join-Path $repoRoot ".env"
$scriptPath = Join-Path $repoRoot "run_odds_loop.py"

if (Test-Path $envPath) {
  Get-Content $envPath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $idx = $line.IndexOf("=")
    if ($idx -lt 1) { return }
    $key = $line.Substring(0, $idx).Trim()
    $val = $line.Substring($idx + 1).Trim()
    if ($val.StartsWith('"') -and $val.EndsWith('"')) {
      $val = $val.Trim('"')
    } elseif ($val.StartsWith("'") -and $val.EndsWith("'")) {
      $val = $val.Trim("'")
    }
    if ($key) {
      Set-Item -Path "Env:$key" -Value $val
    }
  }
}

Set-Location $repoRoot

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pythonCmd) {
  & $pythonCmd.Source $scriptPath --interval-seconds 60 --jitter-seconds 5
  exit $LASTEXITCODE
}

$pyCmd = Get-Command py -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pyCmd) {
  & $pyCmd.Source -3 $scriptPath --interval-seconds 60 --jitter-seconds 5
  exit $LASTEXITCODE
}

Write-Output "Python not found. Install Python 3 and ensure it's on PATH."
exit 1
