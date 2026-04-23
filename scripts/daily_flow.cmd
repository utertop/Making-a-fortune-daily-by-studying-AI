@echo off
setlocal
set "REPO_ROOT=%~dp0.."
cd /d "%REPO_ROOT%"

if not exist ".venv\Scripts\python.exe" (
  echo Python virtual environment not found: .venv\Scripts\python.exe
  exit /b 1
)

".venv\Scripts\python.exe" "scripts\daily_flow.py" %*
