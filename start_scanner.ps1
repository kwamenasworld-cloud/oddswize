# OddsWize Automated Scanner - PowerShell Script
# Run this script to start the automated odds scanner

Write-Host "========================================"
Write-Host "  OddsWize Automated Scanner"
Write-Host "  Scanning odds every 5 minutes"
Write-Host "========================================"
Write-Host ""
Write-Host "Press Ctrl+C to stop the scanner"
Write-Host ""

Set-Location $PSScriptRoot
python auto_scanner.py --with-api
