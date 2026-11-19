@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows\install.ps1" -SourcePath "%~dp0."
if errorlevel 1 pause
