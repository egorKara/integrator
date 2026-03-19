param(
    [string]$LogDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $LogDir) {
    $LogDir = Join-Path $RepoRoot "reports\telegram_bridge_logs"
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$LogFile = Join-Path $LogDir "bridge.log"

Set-Location -Path $RepoRoot

$bridgeArgs = @("-m", "tools.telegram_remote_bridge", "--json")
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pyLauncher) {
    $BridgeExec = $pyLauncher.Source
    $bridgeArgs = @("-3") + $bridgeArgs
} elseif ($pythonCmd) {
    $BridgeExec = $pythonCmd.Source
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
    "[$started] bridge_start exec=$BridgeExec token_file=$tokenFile" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    try {
        & $BridgeExec @bridgeArgs 2>&1 | Out-File -FilePath $LogFile -Encoding utf8 -Append
        $exitCode = $LASTEXITCODE
    } catch {
        $exitCode = 1
        $_ | Out-File -FilePath $LogFile -Encoding utf8 -Append
    }
    $finished = Get-Date -Format o
    "[$finished] bridge_exit code=$exitCode" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    Start-Sleep -Seconds 5
}
