param(
    [switch]$Preview
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$StartupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$StartupScriptPath = Join-Path $StartupDir "AI Signal Radar Login Catchup.cmd"
$MarkerPath = Join-Path $RepoRoot "data\windows_startup_catchup_enabled.json"

if ($Preview) {
    Write-Host "[preview] Remove startup script: $StartupScriptPath"
    return
}

if (Test-Path $StartupScriptPath) {
    Remove-Item -LiteralPath $StartupScriptPath -Force
    Write-Host "Removed startup script: $StartupScriptPath"
} else {
    Write-Host "Startup script not found: $StartupScriptPath"
}

if (Test-Path $MarkerPath) {
    Remove-Item -LiteralPath $MarkerPath -Force
    Write-Host "Startup catch-up marker removed."
}
