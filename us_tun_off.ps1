param(
  [Parameter(Mandatory = $false)][string]$StateFile = "C:\integrator\reports\us_tun_state.json"
)

$ErrorActionPreference = "Stop"

function Ensure-Admin {
  $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Administrator rights required."
  }
}

Ensure-Admin

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$report = "C:\integrator\reports\us_tun_off_$ts.log"
"START $(Get-Date -Format s)" | Out-File -FilePath $report -Encoding utf8

$runtimeConfig = $null
$proxyIp = $null
$routeAdded = $false

if (Test-Path $StateFile) {
  $state = Get-Content $StateFile -Raw | ConvertFrom-Json
  $runtimeConfig = [string]$state.RuntimeConfig
  $proxyIp = [string]$state.ProxyIp
  $routeAdded = [bool]$state.RouteAdded
}

$proc = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
  $_.Name -match 'sing-box' -and ($null -eq $runtimeConfig -or $_.CommandLine -match [regex]::Escape($runtimeConfig))
}
foreach ($p in $proc) {
  Stop-Process -Id ([int]$p.ProcessId) -Force -ErrorAction SilentlyContinue
  "SINGBOX_STOP=$([int]$p.ProcessId)" | Out-File -FilePath $report -Append -Encoding utf8
}

if ($proxyIp -and $routeAdded) {
  route delete $proxyIp | Out-Null
  "PROXY_HOST_ROUTE=DELETED" | Out-File -FilePath $report -Append -Encoding utf8
}

if ($runtimeConfig -and (Test-Path $runtimeConfig)) {
  Remove-Item $runtimeConfig -Force -ErrorAction SilentlyContinue
  "RUNTIME_CONFIG=DELETED" | Out-File -FilePath $report -Append -Encoding utf8
}

if (Test-Path $StateFile) {
  Remove-Item $StateFile -Force -ErrorAction SilentlyContinue
  "STATE_FILE=DELETED" | Out-File -FilePath $report -Append -Encoding utf8
}

ipconfig /flushdns | Out-Null
"DNS_FLUSH=OK" | Out-File -FilePath $report -Append -Encoding utf8
"END $(Get-Date -Format s)" | Out-File -FilePath $report -Append -Encoding utf8
Write-Output $report
