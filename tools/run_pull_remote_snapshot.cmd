@echo off
setlocal
cd /d C:\Users\admin\OneDrive\Documents\GitHub\Arbitrage
py tools\pull_remote_snapshot.py --dedupe --save-db
