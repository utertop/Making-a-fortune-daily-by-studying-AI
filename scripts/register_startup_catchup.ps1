param(
    [switch]$Preview
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$StartupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$StartupScriptPath = Join-Path $StartupDir "AI Signal Radar Login Catchup.cmd"
$RunnerScript = Join-Path $RepoRoot "scripts\run_login_catchup.cmd"
$MarkerPath = Join-Path $RepoRoot "data\windows_startup_catchup_enabled.json"

if (-not (Test-Path $RunnerScript)) {
    throw "Login catch-up runner not found: $RunnerScript"
}

$content = @(
    "@echo off"
    "setlocal"
    "cd /d `"$RepoRoot`""
    "call `"$RunnerScript`""
) -join "`r`n"

if ($Preview) {
    Write-Host "[preview] Create startup script: $StartupScriptPath"
    Write-Host $content
    return
}

New-Item -ItemType Directory -Path $StartupDir -Force | Out-Null
Set-Content -Path $StartupScriptPath -Value $content -Encoding ASCII

$markerPayload = @{
    enabled = $true
    registered_at = (Get-Date).ToString("o")
    startup_script = $StartupScriptPath
}
New-Item -ItemType Directory -Path (Split-Path $MarkerPath -Parent) -Force | Out-Null
$markerPayload | ConvertTo-Json -Depth 4 | Set-Content -Path $MarkerPath -Encoding UTF8

Write-Host "Startup catch-up enabled: $StartupScriptPath"
