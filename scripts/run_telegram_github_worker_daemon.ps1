param(
    [string]$LogDir = "",
    [int]$PollSeconds = 90
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $LogDir) {
    $LogDir = Join-Path $RepoRoot "reports\telegram_github_worker_logs"
}
if ($PollSeconds -lt 30) {
    $PollSeconds = 30
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$LogFile = Join-Path $LogDir "worker.log"

Set-Location -Path $RepoRoot

$workerArgs = @("-m", "tools.telegram_github_worker", "--json")
$executorArgs = @("-m", "tools.telegram_github_executor", "--json")
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pyLauncher) {
    $WorkerExec = $pyLauncher.Source
    $workerArgs = @("-3") + $workerArgs
    $executorArgs = @("-3") + $executorArgs
} elseif ($pythonCmd) {
    $WorkerExec = $pythonCmd.Source
} else {
    throw "python_not_found"
}

$tokenFile = ([string][Environment]::GetEnvironmentVariable("GITHUB_TOKEN_FILE", "User")).Trim()
if (-not $tokenFile) {
    $tokenFile = ([string][Environment]::GetEnvironmentVariable("INTEGRATOR_GITHUB_TOKEN_FILE", "User")).Trim()
}
if (-not $tokenFile) {
    $tokenFile = Join-Path $env:USERPROFILE ".integrator\secrets\github_token.txt"
}
[Environment]::SetEnvironmentVariable("GITHUB_TOKEN", $null, "Process")
[Environment]::SetEnvironmentVariable("GH_TOKEN", $null, "Process")
[Environment]::SetEnvironmentVariable("GITHUB_TOKEN_FILE", $tokenFile, "Process")
[Environment]::SetEnvironmentVariable("INTEGRATOR_GITHUB_TOKEN_FILE", $tokenFile, "Process")

while ($true) {
    $started = Get-Date -Format o
    "[$started] worker_start exec=$WorkerExec token_file=$tokenFile poll_seconds=$PollSeconds" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    try {
        & $WorkerExec @workerArgs 2>&1 | Out-File -FilePath $LogFile -Encoding utf8 -Append
        $workerExitCode = $LASTEXITCODE
        & $WorkerExec @executorArgs 2>&1 | Out-File -FilePath $LogFile -Encoding utf8 -Append
        $executorExitCode = $LASTEXITCODE
        if ($workerExitCode -ne 0) {
            $exitCode = $workerExitCode
        } else {
            $exitCode = $executorExitCode
        }
    } catch {
        $exitCode = 1
        $_ | Out-File -FilePath $LogFile -Encoding utf8 -Append
    }
    $finished = Get-Date -Format o
    "[$finished] worker_exit code=$exitCode" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    Start-Sleep -Seconds $PollSeconds
}
