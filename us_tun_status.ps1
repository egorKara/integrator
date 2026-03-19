param(
  [Parameter(Mandatory = $false)][string]$TunInterfaceName = "us-tun",
  [Parameter(Mandatory = $false)][string]$StateFile = "C:\integrator\reports\us_tun_state.json"
)

$ErrorActionPreference = "Stop"

$status = [ordered]@{}

$h = Get-Process Hiddify -ErrorAction SilentlyContinue | Select-Object -First 1 Id,StartTime
if ($h) {
  $status["HiddifyRunning"] = $true
  $status["HiddifyPid"] = $h.Id
} else {
  $status["HiddifyRunning"] = $false
}

$tun = Get-NetAdapter -Name $TunInterfaceName -ErrorAction SilentlyContinue
if ($tun) {
  $status["TunPresent"] = $true
  $status["TunStatus"] = $tun.Status
  $status["TunIfIndex"] = $tun.IfIndex
} else {
  $status["TunPresent"] = $false
}

$proc = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'sing-box' } | Select-Object -First 1 ProcessId,CommandLine
if ($proc) {
  $status["SingBoxRunning"] = $true
  $status["SingBoxPid"] = [int]$proc.ProcessId
  $status["SingBoxCmd"] = [string]$proc.CommandLine
} else {
  $status["SingBoxRunning"] = $false
}

$bridge = Get-NetTCPConnection -LocalPort 19080 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 LocalAddress,LocalPort,OwningProcess
if ($bridge) {
  $status["Bridge19080"] = $true
  $status["BridgePid"] = $bridge.OwningProcess
} else {
  $status["Bridge19080"] = $false
}

if (Test-Path $StateFile) {
  $state = Get-Content $StateFile -Raw | ConvertFrom-Json
  $status["StateFile"] = $StateFile
  $status["ProxyIp"] = [string]$state.ProxyIp
  $route = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix ("{0}/32" -f [string]$state.ProxyIp) -ErrorAction SilentlyContinue | Select-Object -First 1 InterfaceAlias,NextHop,RouteMetric
  if ($route) {
    $status["ProxyRouteInterface"] = [string]$route.InterfaceAlias
    $status["ProxyRouteNextHop"] = [string]$route.NextHop
  }
}

$status["IpifyDirect"] = ((curl.exe -sS -m 15 https://api.ipify.org?format=json) | Out-String).Trim()
$status | ConvertTo-Json -Depth 5
