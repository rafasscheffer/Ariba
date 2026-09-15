@echo off
cd /d "%~dp0"
BrasmoAribaMonitor.exe status
start "" "%~dp0reports"
