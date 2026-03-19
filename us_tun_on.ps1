param(
  [Parameter(Mandatory = $false)][string]$EnvFile = "C:\integrator\.env.local",
  [Parameter(Mandatory = $false)][string]$SingBoxExe = "C:\integrator\bin\sing-box.exe",
  [Parameter(Mandatory = $false)][string]$TemplatePath = "C:\integrator\us_tun_singbox.template.json",
  [Parameter(Mandatory = $false)][string]$TunInterfaceName = "us-tun",
  [Parameter(Mandatory = $false)][switch]$ForceStopHiddify
)

$ErrorActionPreference = "Stop"

function Ensure-Admin {
  $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Administrator rights required."
  }
}

function Load-EnvMap([string]$path) {
  $map = @{}
  Get-Content $path | ForEach-Object {
    if ($_ -match '^[^#].*=') {
      $k, $v = $_.Split('=', 2)
      $map[$k.Trim()] = $v.Trim()
    }
  }
  return $map
}

function Wait-Port([string]$hostName, [int]$port, [int]$timeoutSec) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  while ($sw.Elapsed.TotalSeconds -lt $timeoutSec) {
    try {
      $c = New-Object System.Net.Sockets.TcpClient
      $iar = $c.BeginConnect($hostName, $port, $null, $null)
      $ok = $iar.AsyncWaitHandle.WaitOne(500)
      if ($ok -and $c.Connected) {
        $c.Close()
        return $true
      }
      $c.Close()
    } catch {}
    Start-Sleep -Milliseconds 300
  }
  return $false
}

function Wait-Interface([string]$name, [int]$timeoutSec) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  while ($sw.Elapsed.TotalSeconds -lt $timeoutSec) {
    $a = Get-NetAdapter -Name $name -ErrorAction SilentlyContinue
    if ($null -ne $a) {
      return $true
    }
    Start-Sleep -Milliseconds 500
  }
  return $false
}

function Get-EthernetDefaultRoute {
  $routes = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue |
    Where-Object { $_.InterfaceAlias -notmatch '^tun' -and $_.InterfaceAlias -ne 'us-tun' } |
    Sort-Object RouteMetric,InterfaceMetric
  return $routes | Select-Object -First 1
}

Ensure-Admin

if (-not (Test-Path $EnvFile)) { throw "Env file not found: $EnvFile" }
if (-not (Test-Path $TemplatePath)) { throw "Template not found: $TemplatePath" }
if (-not (Test-Path $SingBoxExe)) { throw "sing-box not found: $SingBoxExe" }

$envMap = Load-EnvMap $EnvFile
$proxyIp = $envMap["PROXY_IP"]
$proxyPort = [int]$envMap["PROXY_PORT"]
$proxyUser = $envMap["PROXY_USER"]
$credTarget = $envMap["PROXY_CRED_TARGET"]

if ([string]::IsNullOrWhiteSpace($proxyIp) -or [string]::IsNullOrWhiteSpace($proxyUser) -or [string]::IsNullOrWhiteSpace($credTarget)) {
  throw "Missing required proxy values in $EnvFile"
}

. "C:\integrator\proxy_credman.ps1"
$credObj = Get-CredManGenericCredential -TargetName $credTarget
if ($null -eq $credObj -or [string]::IsNullOrWhiteSpace($credObj.Password) -or $credObj.UserName -ne $proxyUser) {
  throw "Credential lookup failed for target: $credTarget"
}

$h = Get-Process Hiddify -ErrorAction SilentlyContinue
if ($h -and -not $ForceStopHiddify.IsPresent) {
  throw "Hiddify is running. Stop it first or use -ForceStopHiddify."
}
if ($h -and $ForceStopHiddify.IsPresent) {
  Stop-Process -Id $h.Id -Force -ErrorAction SilentlyContinue
}

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$reports = "C:\integrator\reports"
if (-not (Test-Path $reports)) { New-Item -ItemType Directory -Path $reports -Force | Out-Null }
$report = Join-Path $reports "us_tun_on_$ts.log"
$runtimeConfig = Join-Path $reports "us_tun_singbox_runtime.json"
$stateFile = Join-Path $reports "us_tun_state.json"

"START $(Get-Date -Format s)" | Out-File -FilePath $report -Encoding utf8

$defaultRoute = Get-EthernetDefaultRoute
if ($null -eq $defaultRoute) { throw "Ethernet default route not found." }
$gateway = [string]$defaultRoute.NextHop
$ifIndex = [int]$defaultRoute.IfIndex
"DEFAULT_ROUTE_IFACE=$($defaultRoute.InterfaceAlias)" | Out-File -FilePath $report -Append -Encoding utf8
"DEFAULT_ROUTE_GW=$gateway" | Out-File -FilePath $report -Append -Encoding utf8

$existingHostRoute = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix "$proxyIp/32" -ErrorAction SilentlyContinue | Select-Object -First 1
$routeAdded = $false
if ($null -eq $existingHostRoute) {
  route add $proxyIp mask 255.255.255.255 $gateway metric 1 if $ifIndex | Out-Null
  $routeAdded = $true
  "PROXY_HOST_ROUTE=ADDED" | Out-File -FilePath $report -Append -Encoding utf8
} else {
  "PROXY_HOST_ROUTE=EXISTS" | Out-File -FilePath $report -Append -Encoding utf8
}

$template = Get-Content $TemplatePath -Raw
$template = $template.Replace("__PROXY_IP__", $proxyIp)
$template = $template.Replace("__PROXY_PORT__", [string]$proxyPort)
$template = $template.Replace("__PROXY_USER__", $proxyUser)
$template = $template.Replace("__PROXY_PASS__", $credObj.Password)
$runtimeConfig | Out-Null
$template | Out-File -FilePath $runtimeConfig -Encoding utf8
"RUNTIME_CONFIG=$runtimeConfig" | Out-File -FilePath $report -Append -Encoding utf8

$running = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
  $_.Name -match 'sing-box' -and $_.CommandLine -match [regex]::Escape($runtimeConfig)
}
if ($running) {
  "SINGBOX_ALREADY_RUNNING=$($running.ProcessId)" | Out-File -FilePath $report -Append -Encoding utf8
} else {
  $p = Start-Process -FilePath $SingBoxExe -ArgumentList @("run","-c",$runtimeConfig) -PassThru -WindowStyle Hidden
  "SINGBOX_PID=$($p.Id)" | Out-File -FilePath $report -Append -Encoding utf8
}

if (-not (Wait-Interface -name $TunInterfaceName -timeoutSec 12)) {
  throw "TUN interface not ready: $TunInterfaceName"
}
"TUN_READY=YES" | Out-File -FilePath $report -Append -Encoding utf8

$egress = (& curl.exe -sS -m 20 -x socks5h://127.0.0.1:19080 https://api.ipify.org?format=json 2>&1) | Out-String
"EGRESS_CHECK=$($egress.Trim())" | Out-File -FilePath $report -Append -Encoding utf8

$state = [pscustomobject]@{
  CreatedAt = (Get-Date -Format s)
  ProxyIp = $proxyIp
  Gateway = $gateway
  IfIndex = $ifIndex
  RouteAdded = $routeAdded
  RuntimeConfig = $runtimeConfig
  TunInterfaceName = $TunInterfaceName
}
$state | ConvertTo-Json | Out-File -FilePath $stateFile -Encoding utf8
"STATE_FILE=$stateFile" | Out-File -FilePath $report -Append -Encoding utf8
"END $(Get-Date -Format s)" | Out-File -FilePath $report -Append -Encoding utf8
Write-Output $report
