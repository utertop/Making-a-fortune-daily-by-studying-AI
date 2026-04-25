param(
    [ValidateSet("morning_push", "afternoon_push", "soft_deadline", "hard_deadline")]
    [string]$JobName,
    [switch]$Catchup,
    [switch]$Preview
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    throw "Python virtual environment not found: $PythonExe"
}

if (-not $Catchup -and -not $JobName) {
    throw "Provide -JobName or use -Catchup."
}

$arguments = @("scripts\local_scheduler.py")
if ($Catchup) {
    $arguments += "--run-catchup-now"
} else {
    $arguments += @("--run-now", $JobName)
}
if ($Preview) {
    $arguments += "--preview"
}

Set-Location $RepoRoot
& $PythonExe @arguments
exit $LASTEXITCODE
