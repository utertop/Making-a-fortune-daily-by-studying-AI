@echo off
setlocal
set "REPO_ROOT=%~dp0.."
cd /d "%REPO_ROOT%\apps\web"

npm.cmd install --cache "%REPO_ROOT%\.npm-cache"
