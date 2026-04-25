@echo off
setlocal
set "REPO_ROOT=%~dp0.."
cd /d "%REPO_ROOT%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\run_scheduled_job.ps1" -Catchup
