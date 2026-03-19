param(
    [string]$TunnelAlias = "tun0",
    [string]$ReportsRoot = "C:\integrator\reports",
    [string]$RepoRoot = "C:\integrator",
    [string]$EnvFile = "C:\integrator\.env.local",
    [string]$ProxyIp = "",
    [string[]]$RequiredTcpHosts = @("api.ipify.org","www.youtube.com","openai.com"),
    [switch]$AutoRollbackOnFailure,
    [switch]$Elevated
)

$ErrorActionPreference = "Stop"

function Ensure-AdminAndRelaunch {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($isAdmin) {
        return
    }
    if ($Elevated) {
        throw "Elevation required but failed."
    }
    $argParts = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSCommandPath`"",
        "-TunnelAlias", "`"$TunnelAlias`"",
        "-ReportsRoot", "`"$ReportsRoot`"",
        "-RepoRoot", "`"$RepoRoot`"",
        "-EnvFile", "`"$EnvFile`""
    )
    if ($ProxyIp) {
        $argParts += @("-ProxyIp", "`"$ProxyIp`"")
    }
    if ($RequiredTcpHosts -and $RequiredTcpHosts.Count -gt 0) {
        $joined = ($RequiredTcpHosts -join ",")
        $argParts += @("-RequiredTcpHosts", "`"$joined`"")
    }
    if ($AutoRollbackOnFailure.IsPresent) {
        $argParts += "-AutoRollbackOnFailure"
    }
    $argParts += "-Elevated"
    Start-Process powershell -Verb RunAs -Wait -ArgumentList ($argParts -join " ")
    exit 0
}

function Normalize-RequiredHosts {
    if ($RequiredTcpHosts.Count -eq 1 -and $RequiredTcpHosts[0] -match ",") {
        $script:RequiredTcpHosts = $RequiredTcpHosts[0].Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    }
}

function Resolve-ProxyIpFromEnv {
    if ($ProxyIp) {
        return $ProxyIp
    }
    if (-not (Test-Path $EnvFile)) {
        return ""
    }
    $line = Get-Content $EnvFile | Where-Object { $_ -match '^PROXY_IP=' } | Select-Object -First 1
    if (-not $line) {
        return ""
    }
    return ($line -replace '^PROXY_IP=', '').Trim()
}

function Write-Report {
    param([string]$Message)
    $Message | Out-File -FilePath $script:ReportPath -Append -Encoding utf8
}

function Test-TcpHosts {
    param([string]$Stage)
    $results = @()
    foreach ($targetHost in $RequiredTcpHosts) {
        $ok = $false
        try {
            $r = Test-NetConnection $targetHost -Port 443 -WarningAction SilentlyContinue
            $ok = [bool]$r.TcpTestSucceeded
        } catch {
            $ok = $false
        }
        $results += [PSCustomObject]@{
            Stage = $Stage
            Host = $targetHost
            Port = 443
            TcpOk = $ok
        }
    }
    return $results
}

function Invoke-NetworkCollect {
    param([string]$Tag)
    $collectScript = Join-Path $RepoRoot ".trae\automation\p0_network_collect.ps1"
    if (-not (Test-Path $collectScript)) {
        return ""
    }
    $target = Join-Path $ReportsRoot ("p0_network_check_{0}_{1}.log" -f $Tag, $script:Timestamp)
    $out = & $collectScript -OutputPath $target
    if ($out) {
        Write-Report ("COLLECT_{0}={1}" -f $Tag.ToUpper(), $out)
    }
    return $target
}

function Invoke-NetworkBackup {
    $backupScript = Join-Path $RepoRoot ".trae\automation\p0_network_backup.ps1"
    if (-not (Test-Path $backupScript)) {
        throw "Backup script not found: $backupScript"
    }
    $path = & $backupScript
    Write-Report ("BACKUP_PATH={0}" -f $path)
    return $path
}

function Disable-Tunnel {
    param([string]$Alias)
    Disable-NetAdapter -Name $Alias -Confirm:$false -ErrorAction Stop
}

function Enable-Tunnel {
    param([string]$Alias)
    Enable-NetAdapter -Name $Alias -Confirm:$false -ErrorAction SilentlyContinue
}

function Invoke-Rollback {
    param([string]$BackupPath)
    $rollbackScript = Join-Path $RepoRoot ".trae\automation\p0_network_rollback.ps1"
    $killswitchScript = Join-Path $RepoRoot ".trae\automation\p0_network_killswitch.ps1"
    if (Test-Path $rollbackScript) {
        & $rollbackScript -BackupPath $BackupPath | Out-Null
        Write-Report "ROLLBACK_P0_NETWORK=OK"
    } else {
        Write-Report "ROLLBACK_P0_NETWORK=SKIP"
    }
    if (Test-Path $killswitchScript) {
        & $killswitchScript -Mode Disable -InterfaceAlias Ethernet -BackupPath $BackupPath | Out-Null
        Write-Report "ROLLBACK_KILLSWITCH=OK"
    } else {
        Write-Report "ROLLBACK_KILLSWITCH=SKIP"
    }
    ipconfig /flushdns | Out-Null
    Write-Report "DNS_FLUSH=OK"
}

Ensure-AdminAndRelaunch
Normalize-RequiredHosts

if (-not (Test-Path $ReportsRoot)) {
    New-Item -ItemType Directory -Path $ReportsRoot -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ReportPath = Join-Path $ReportsRoot ("safe_tun0_off_test_{0}.log" -f $Timestamp)
$ProxyIp = Resolve-ProxyIpFromEnv

"SAFE_TUN0_OFF_TEST START $((Get-Date).ToString("s"))" | Out-File -FilePath $ReportPath -Encoding utf8
Write-Report ("TUNNEL_ALIAS={0}" -f $TunnelAlias)
Write-Report ("AUTO_ROLLBACK={0}" -f $AutoRollbackOnFailure.IsPresent)
Write-Report ("REQUIRED_TCP_HOSTS={0}" -f ($RequiredTcpHosts -join ","))
if ($ProxyIp) {
    Write-Report ("PROXY_IP={0}" -f $ProxyIp)
}

$backupPath = Invoke-NetworkBackup
$preCollect = Invoke-NetworkCollect -Tag "before"

$adapter = Get-NetAdapter -Name $TunnelAlias -ErrorAction SilentlyContinue
if (-not $adapter) {
    Write-Report "TUNNEL_PRESENT=NO"
    Write-Report "SAFE_TUN0_OFF_TEST END $(Get-Date -Format s)"
    Write-Output $ReportPath
    exit 2
}

$wasUp = $adapter.Status -eq "Up"
Write-Report ("TUNNEL_WAS_UP={0}" -f $wasUp)

if ($ProxyIp) {
    try {
        $preRoute = Find-NetRoute -RemoteIPAddress $ProxyIp | Select-Object -First 1
        if ($preRoute) {
            Write-Report ("PRE_PROXY_ROUTE_IFACE={0}" -f $preRoute.InterfaceAlias)
            Write-Report ("PRE_PROXY_ROUTE_NEXTHOP={0}" -f $preRoute.NextHop)
        }
    } catch {
        Write-Report "PRE_PROXY_ROUTE=ERR"
    }
}

$preTcp = Test-TcpHosts -Stage "before"
$preTcp | ConvertTo-Json -Depth 4 | Out-File -FilePath $ReportPath -Append -Encoding utf8

$disableOk = $false
if ($wasUp) {
    try {
        Disable-Tunnel -Alias $TunnelAlias
        Start-Sleep -Seconds 4
        $disableOk = $true
        Write-Report "TUNNEL_DISABLE=OK"
    } catch {
        Write-Report ("TUNNEL_DISABLE=ERR:{0}" -f $_.Exception.Message)
    }
} else {
    Write-Report "TUNNEL_DISABLE=SKIP_ALREADY_DOWN"
}

$postTcp = Test-TcpHosts -Stage "after"
$postTcp | ConvertTo-Json -Depth 4 | Out-File -FilePath $ReportPath -Append -Encoding utf8

$postOkCount = ($postTcp | Where-Object { $_.TcpOk }).Count
$requiredCount = $RequiredTcpHosts.Count
Write-Report ("POST_TCP_OK={0}/{1}" -f $postOkCount, $requiredCount)

if ($ProxyIp) {
    try {
        $postRoute = Find-NetRoute -RemoteIPAddress $ProxyIp | Select-Object -First 1
        if ($postRoute) {
            Write-Report ("POST_PROXY_ROUTE_IFACE={0}" -f $postRoute.InterfaceAlias)
            Write-Report ("POST_PROXY_ROUTE_NEXTHOP={0}" -f $postRoute.NextHop)
        }
    } catch {
        Write-Report "POST_PROXY_ROUTE=ERR"
    }
}

$failed = $postOkCount -lt $requiredCount
Write-Report ("RESULT_FAILED={0}" -f $failed)

if ($failed -and $AutoRollbackOnFailure.IsPresent) {
    Write-Report "AUTO_ROLLBACK=START"
    if ($wasUp) {
        Enable-Tunnel -Alias $TunnelAlias
        Start-Sleep -Seconds 3
        Write-Report "TUNNEL_ENABLE=OK"
    }
    Invoke-Rollback -BackupPath $backupPath
    Write-Report "AUTO_ROLLBACK=END"
}

$postCollect = Invoke-NetworkCollect -Tag "after"
Write-Report ("COLLECT_AFTER={0}" -f $postCollect)
Write-Report ("SAFE_TUN0_OFF_TEST END {0}" -f (Get-Date -Format s))
Write-Output $ReportPath
