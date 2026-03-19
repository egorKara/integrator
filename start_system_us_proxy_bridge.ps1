$ErrorActionPreference = "Stop"

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
    Start-Sleep -Milliseconds 250
  }
  return $false
}

$cfgPath = "C:\integrator\reports\system_us_proxy_runtime.json"
if (-not (Test-Path $cfgPath)) {
  exit 0
}

$cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
$bridgePort = [int]$cfg.BridgePort
$proxyHost = [string]$cfg.ProxyHost
$proxyPort = [int]$cfg.ProxyPort
$proxyUser = [string]$cfg.ProxyUser
$credTarget = [string]$cfg.CredTarget
$python = [string]$cfg.Python

if (Wait-Port -hostName "127.0.0.1" -port $bridgePort -timeoutSec 1) {
  exit 0
}

if (-not (Test-Path $python)) {
  if (Test-Path "C:\integrator\.venv\Scripts\python.exe") { $python = "C:\integrator\.venv\Scripts\python.exe" }
  elseif (Test-Path "C:\integrator\venv\Scripts\python.exe") { $python = "C:\integrator\venv\Scripts\python.exe" }
  else { $python = "python" }
}

. "C:\integrator\proxy_credman.ps1"
$credObj = Get-CredManGenericCredential -TargetName $credTarget
if ($null -eq $credObj -or [string]::IsNullOrWhiteSpace($credObj.Password) -or $credObj.UserName -ne $proxyUser) {
  exit 2
}

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$bridgeLog = "C:\integrator\reports\system_us_proxy_bridge_autostart_$ts.log"

$env:BRIDGE_UP_USER = $proxyUser
$env:BRIDGE_UP_PASS = $credObj.Password
Start-Process -FilePath $python -ArgumentList @(
  "C:\integrator\us_socks_bridge.py",
  "--listen-host", "127.0.0.1",
  "--listen-port", "$bridgePort",
  "--upstream-host", "$proxyHost",
  "--upstream-port", "$proxyPort",
  "--log-file", "$bridgeLog"
) -WindowStyle Hidden | Out-Null
Remove-Item Env:\BRIDGE_UP_USER -ErrorAction SilentlyContinue
Remove-Item Env:\BRIDGE_UP_PASS -ErrorAction SilentlyContinue
