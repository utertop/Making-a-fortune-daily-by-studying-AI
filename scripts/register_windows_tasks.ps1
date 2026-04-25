param(
    [switch]$Preview
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RunnerScript = Join-Path $RepoRoot "scripts\run_scheduled_job.ps1"
$CatchupCmd = Join-Path $RepoRoot "scripts\run_login_catchup.cmd"
$MarkerPath = Join-Path $RepoRoot "data\windows_task_scheduler_enabled.json"
$TaskPath = "\AI Signal Radar\"

if (-not (Test-Path $RunnerScript)) {
    throw "Runner script not found: $RunnerScript"
}
if (-not (Test-Path $CatchupCmd)) {
    throw "Catch-up wrapper not found: $CatchupCmd"
}

$taskSpecs = @(
    @{
        Name = "Morning Push"
        JobName = "morning_push"
        Description = "AI Signal Radar 08:00 Feishu morning push"
        Hour = 8
        Minute = 0
    },
    @{
        Name = "Afternoon Push"
        JobName = "afternoon_push"
        Description = "AI Signal Radar 14:00 Feishu afternoon push"
        Hour = 14
        Minute = 0
    },
    @{
        Name = "Soft Deadline"
        JobName = "soft_deadline"
        Description = "AI Signal Radar 21:30 soft deadline reminder"
        Hour = 21
        Minute = 30
    },
    @{
        Name = "Hard Deadline"
        JobName = "hard_deadline"
        Description = "AI Signal Radar 23:00 hard deadline reminder"
        Hour = 23
        Minute = 0
        TriggerType = "Daily"
    },
    @{
        Name = "Login Catchup"
        JobName = "catchup"
        Description = "AI Signal Radar login catch-up for missed jobs"
        TriggerType = "AtLogOn"
    }
)

$principalUser = if ($env:USERDOMAIN) {
    "$($env:USERDOMAIN)\$($env:USERNAME)"
} else {
    $env:USERNAME
}

if (-not $Preview) {
    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -MultipleInstances IgnoreNew

    $principal = New-ScheduledTaskPrincipal -UserId $principalUser -LogonType Interactive -RunLevel Limited
}

foreach ($spec in $taskSpecs) {
    $actionArgs = if ($spec.JobName -eq "catchup") {
        "`"$CatchupCmd`""
    } else {
        "-NoProfile -ExecutionPolicy Bypass -File `"$RunnerScript`" -JobName $($spec.JobName)"
    }

    if ($Preview) {
        Write-Host "[preview] Register task $TaskPath$($spec.Name) -> $actionArgs"
        continue
    }

    if ($spec.TriggerType -eq "AtLogOn") {
        $taskName = "$TaskPath$($spec.Name)"
        $tr = $actionArgs
        $runUser = $env:USERNAME
        $command = @(
            "/Create",
            "/SC", "ONLOGON",
            "/TN", $taskName,
            "/TR", $tr,
            "/RU", $runUser,
            "/RL", "LIMITED",
            "/F"
        )
        $null = & schtasks.exe @command
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to register logon catch-up task: $taskName"
        }
        Write-Host "Registered task: $taskName"
        continue
    } else {
        $startTime = Get-Date -Hour $spec.Hour -Minute $spec.Minute -Second 0
        $trigger = New-ScheduledTaskTrigger -Daily -At $startTime
    }
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs -WorkingDirectory $RepoRoot

    Register-ScheduledTask `
        -TaskPath $TaskPath `
        -TaskName $spec.Name `
        -Description $spec.Description `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Force | Out-Null

    Write-Host "Registered task: $TaskPath$($spec.Name)"
}

if (-not $Preview) {
    $markerPayload = @{
        enabled = $true
        registered_at = (Get-Date).ToString("o")
        task_path = $TaskPath
        tasks = $taskSpecs | ForEach-Object { $_.Name }
    }
    New-Item -ItemType Directory -Path (Split-Path $MarkerPath -Parent) -Force | Out-Null
    $markerPayload | ConvertTo-Json -Depth 4 | Set-Content -Path $MarkerPath -Encoding UTF8
    Write-Host "Windows Task Scheduler mode enabled."
}
