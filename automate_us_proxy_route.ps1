param(
  [ValidateSet("VerifyRoute","EnsureEthernetHostRoute","DeleteHostRoute","RollbackLatest")]
  [string]$Action = "VerifyRoute",
  [string]$ProxyIp = "",
  [string]$PreferredInterfaceAlias = "Ethernet",
  [string]$EnvFile = "C:\integrator\.env.local",
  [string]$ReportsRoot = "C:\integrator\reports",
  [switch]$Persist,
  [switch]$Elevated
)

$ErrorActionPreference = "Stop"

function Get-ProxyIpFromEnv([string]$path) {
  if (-not (Test-Path $path)) {
    return $null
  }
  $line = Get-Content $path | Where-Object { $_ -match '^PROXY_IP=' } | Select-Object -First 1
  if (-not $line) {
    return $null
  }
  return ($line -replace '^PROXY_IP=', '').Trim()
}

function Get-EthernetDefaultRoute([string]$alias) {
  return Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' |
    Where-Object { $_.InterfaceAlias -eq $alias } |
    Sort-Object RouteMetric |
    Select-Object -First 1
}

function Ensure-AdminAndRelaunch([string]$actionName) {
  $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
  $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  if ($isAdmin) {
    return
  }
  if ($Elevated) {
    throw "Elevation required but failed."
  }
  $args = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$PSCommandPath`"",
    "-Action", $actionName,
    "-ProxyIp", $ProxyIp,
    "-PreferredInterfaceAlias", "`"$PreferredInterfaceAlias`"",
    "-EnvFile", "`"$EnvFile`"",
    "-ReportsRoot", "`"$ReportsRoot`"",
    "-Elevated"
  )
  if ($Persist) {
    $args += "-Persist"
  }
  Start-Process powershell -Verb RunAs -Wait -ArgumentList ($args -join " ")
  exit 0
}

function Show-CurrentRoute([string]$ip) {
  $route = Find-NetRoute -RemoteIPAddress $ip | Select-Object IPAddress,InterfaceAlias,InterfaceIndex,NextHop,RouteMetric
  $route | Format-Table -AutoSize
}

function Ensure-HostRouteViaEthernet([string]$ip, [string]$alias) {
  Ensure-AdminAndRelaunch -actionName "EnsureEthernetHostRoute"
  $eth = Get-EthernetDefaultRoute -alias $alias
  if (-not $eth) {
    throw "Ethernet default route not found for alias: $alias"
  }
  $existing = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix "$ip/32" -ErrorAction SilentlyContinue |
    Where-Object { $_.InterfaceAlias -eq $alias -and $_.NextHop -eq $eth.NextHop }
  if ($existing) {
    Write-Output "ROUTE_ALREADY_PRESENT"
    Show-CurrentRoute -ip $ip
    return
  }
  $persistArg = ""
  if ($Persist) {
    $persistArg = "-p "
  }
  $cmd = "route {0}ADD {1} MASK 255.255.255.255 {2} METRIC 1 IF {3}" -f $persistArg, $ip, $eth.NextHop, $eth.ifIndex
  cmd /c $cmd | Out-Null
  Write-Output "ROUTE_ADDED"
  Show-CurrentRoute -ip $ip
}

function Remove-HostRoute([string]$ip) {
  Ensure-AdminAndRelaunch -actionName "DeleteHostRoute"
  cmd /c "route DELETE $ip" | Out-Null
  Write-Output "ROUTE_DELETED"
  Show-CurrentRoute -ip $ip
}

function Rollback-LatestPipeline() {
  $latestLog = Get-ChildItem -Path $ReportsRoot -Filter "win10_proxy_pipeline_*.log" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if (-not $latestLog) {
    throw "Pipeline log not found in $ReportsRoot"
  }
  $backupLine = Get-Content $latestLog.FullName | Where-Object { $_ -match '^BACKUP_DIR=' } | Select-Object -First 1
  if (-not $backupLine) {
    throw "BACKUP_DIR not found in $($latestLog.FullName)"
  }
  $backupDir = ($backupLine -replace '^BACKUP_DIR=', '').Trim()
  if (-not (Test-Path $backupDir)) {
    throw "Backup dir from latest log not found: $backupDir"
  }
  & "C:\integrator\restore_win10_inet_access.ps1" -BackupDir $backupDir
  Write-Output "ROLLBACK_FROM=$backupDir"
}

if ([string]::IsNullOrWhiteSpace($ProxyIp)) {
  $ProxyIp = Get-ProxyIpFromEnv -path $EnvFile
}
if ([string]::IsNullOrWhiteSpace($ProxyIp) -and $Action -ne "RollbackLatest") {
  throw "PROXY_IP not provided and not found in $EnvFile"
}

switch ($Action) {
  "VerifyRoute" {
    Show-CurrentRoute -ip $ProxyIp
  }
  "EnsureEthernetHostRoute" {
    Ensure-HostRouteViaEthernet -ip $ProxyIp -alias $PreferredInterfaceAlias
  }
  "DeleteHostRoute" {
    Remove-HostRoute -ip $ProxyIp
  }
  "RollbackLatest" {
    Rollback-LatestPipeline
  }
}
