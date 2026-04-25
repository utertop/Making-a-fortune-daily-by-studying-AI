param(
    [switch]$Preview
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$MarkerPath = Join-Path $RepoRoot "data\windows_task_scheduler_enabled.json"
$TaskPath = "\AI Signal Radar\"
$TaskNames = @("Morning Push", "Afternoon Push", "Soft Deadline", "Hard Deadline", "Login Catchup")

foreach ($taskName in $TaskNames) {
    if ($Preview) {
        Write-Host "[preview] Unregister task $TaskPath$taskName"
        continue
    }

    try {
        if ($taskName -eq "Login Catchup") {
            $null = & schtasks.exe /Delete /TN "$TaskPath$taskName" /F
            if ($LASTEXITCODE -ne 0) {
                throw "Task not found"
            }
            Write-Host "Unregistered task: $TaskPath$taskName"
        } else {
            Unregister-ScheduledTask -TaskPath $TaskPath -TaskName $taskName -Confirm:$false -ErrorAction Stop
            Write-Host "Unregistered task: $TaskPath$taskName"
        }
    } catch {
        Write-Host "Task not found or already removed: $TaskPath$taskName"
    }
}

if (-not $Preview -and (Test-Path $MarkerPath)) {
    Remove-Item -LiteralPath $MarkerPath -Force
    Write-Host "Windows Task Scheduler mode disabled."
}
