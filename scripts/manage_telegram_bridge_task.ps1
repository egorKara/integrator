param(
    [ValidateSet("install", "uninstall", "start", "stop", "status", "restart")]
    [string]$Action = "install",
    [string]$TaskName = "IntegratorTelegramBridge",
    [string]$LogDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$daemonScript = Join-Path $repoRoot "scripts\run_telegram_bridge_daemon.ps1"

function Test-RequiredEnv {
    $required = @("TELEGRAM_BOT_TOKEN", "TELEGRAM_BRIDGE_ALLOWED_CHAT_IDS", "TELEGRAM_BRIDGE_REPO")
    $missing = @()
    foreach ($name in $required) {
        $value = [Environment]::GetEnvironmentVariable($name, "User")
        if (-not $value) {
            $value = [Environment]::GetEnvironmentVariable($name, "Process")
        }
        if (-not $value) {
            $missing += $name
        }
    }
    if ($missing.Count -gt 0) {
        throw ("missing_env:" + ($missing -join ","))
    }
    $probe = "from github_api import load_github_token; raise SystemExit(0 if bool(load_github_token()) else 1)"
    & python -c $probe | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "missing_env:GITHUB_TOKEN_OR_FILE"
    }
}

function New-TaskParts {
    param([string]$Name, [string]$Script, [string]$Logs)
    $quotedScript = "`"$Script`""
    $argLog = ""
    if ($Logs) {
        $argLog = " -LogDir `"$Logs`""
    }
    $args = "-NoProfile -ExecutionPolicy Bypass -File $quotedScript$argLog"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $args -WorkingDirectory $repoRoot
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Hours 0)
    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
    return @{
        action = $action
        trigger = $trigger
        settings = $settings
        principal = $principal
    }
}

switch ($Action) {
    "install" {
        Test-RequiredEnv
        $parts = New-TaskParts -Name $TaskName -Script $daemonScript -Logs $LogDir
        Register-ScheduledTask -TaskName $TaskName -Action $parts.action -Trigger $parts.trigger -Settings $parts.settings -Principal $parts.principal -Force | Out-Null
        Start-ScheduledTask -TaskName $TaskName
        Write-Output "task_installed:$TaskName"
    }
    "uninstall" {
        if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
            Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
            Write-Output "task_removed:$TaskName"
        } else {
            Write-Output "task_absent:$TaskName"
        }
    }
    "start" {
        Start-ScheduledTask -TaskName $TaskName
        Write-Output "task_started:$TaskName"
    }
    "stop" {
        Stop-ScheduledTask -TaskName $TaskName
        Write-Output "task_stopped:$TaskName"
    }
    "restart" {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Start-ScheduledTask -TaskName $TaskName
        Write-Output "task_restarted:$TaskName"
    }
    "status" {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if (-not $task) {
            Write-Output "task_absent:$TaskName"
            break
        }
        $info = Get-ScheduledTaskInfo -TaskName $TaskName
        [pscustomobject]@{
            TaskName = $TaskName
            State = "$($task.State)"
            LastTaskResult = $info.LastTaskResult
            LastRunTime = $info.LastRunTime
            NextRunTime = $info.NextRunTime
        } | ConvertTo-Json -Compress
    }
}
