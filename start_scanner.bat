@echo off
echo ========================================
echo   OddsWize Automated Scanner
echo   Scanning odds every 5 minutes
echo ========================================
echo.
echo Press Ctrl+C to stop the scanner
echo.

cd /d "%~dp0"
python auto_scanner.py --with-api

pause
