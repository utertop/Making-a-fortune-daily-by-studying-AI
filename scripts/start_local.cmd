@echo off
setlocal
set "REPO_ROOT=%~dp0.."
cd /d "%REPO_ROOT%"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\start_local.ps1" %*
