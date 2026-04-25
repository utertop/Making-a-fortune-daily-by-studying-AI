param(
    [int]$ApiPort = 8000,
    [int]$WebPort = 3100,
    [switch]$Lan,
    [switch]$NoScheduler,
    [switch]$ForceLocalScheduler
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$NextCmd = Join-Path $RepoRoot "apps\web\node_modules\.bin\next.cmd"
$TaskSchedulerMarker = Join-Path $RepoRoot "data\windows_task_scheduler_enabled.json"

if (-not (Test-Path $PythonExe)) {
    throw "Python virtual environment not found: $PythonExe"
}

if (-not (Test-Path $NextCmd)) {
    throw "Next.js command shim not found. Run scripts\install_web_deps.cmd first."
}

$BindHost = if ($Lan) { "0.0.0.0" } else { "127.0.0.1" }
$DisplayHost = if ($Lan) { "0.0.0.0" } else { "127.0.0.1" }
$LocalIp = $null

if ($Lan) {
    try {
        $LocalIp = Get-NetIPAddress -AddressFamily IPv4 |
            Where-Object {
                $_.IPAddress -notlike "127.*" -and
                $_.IPAddress -notlike "169.254.*" -and
                $_.PrefixOrigin -ne "WellKnown"
            } |
            Select-Object -First 1 -ExpandProperty IPAddress
    } catch {
        $LocalIp = $null
    }
}

$WindowsTaskSchedulerManaged = Test-Path $TaskSchedulerMarker
$StartLocalScheduler = (-not $NoScheduler) -and ((-not $WindowsTaskSchedulerManaged) -or $ForceLocalScheduler)

Start-Process powershell -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-NoExit",
    "-Command",
    "Set-Location '$RepoRoot'; .\.venv\Scripts\python.exe -m uvicorn apps.api.app.main:app --reload --host $BindHost --port $ApiPort"
)

Start-Process powershell -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-NoExit",
    "-Command",
    "Set-Location '$RepoRoot\apps\web'; npm.cmd run dev -- -H $BindHost -p $WebPort"
)

if ($StartLocalScheduler) {
    Start-Process powershell -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-NoExit",
        "-Command",
        "Set-Location '$RepoRoot'; .\.venv\Scripts\python.exe scripts\local_scheduler.py"
    )
}

Write-Host "AI Signal Radar local services are starting."
Write-Host "API: http://$DisplayHost`:$ApiPort"
Write-Host "Web: http://$DisplayHost`:$WebPort"
if ($NoScheduler) {
    Write-Host "Scheduler: disabled"
} elseif ($WindowsTaskSchedulerManaged -and -not $ForceLocalScheduler) {
    Write-Host "Scheduler: managed by Windows Task Scheduler"
} else {
    Write-Host "Scheduler: enabled"
}

if ($Lan -and $LocalIp) {
    Write-Host "LAN API: http://$LocalIp`:$ApiPort"
    Write-Host "LAN Web: http://$LocalIp`:$WebPort"
}

if ($Lan -and -not $LocalIp) {
    Write-Host "LAN mode is enabled, but no local IPv4 address was detected automatically."
    Write-Host "Run ipconfig and open http://<your-ip>:$WebPort from another device on the same network."
}
