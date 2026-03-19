param(
  [Parameter(Mandatory = $false)][string]$EnvFile = "C:\integrator\.env.local",
  [Parameter(Mandatory = $false)][int]$BridgePort = 19080,
  [Parameter(Mandatory = $false)][string]$UpstreamHost = "208.214.160.156",
  [Parameter(Mandatory = $false)][int]$UpstreamPort = 50101,
  [Parameter(Mandatory = $false)][string]$ProxyUser = "",
  [Parameter(Mandatory = $false)][string]$CredTarget = "",
  [Parameter(Mandatory = $false)][switch]$SetUserEnv
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

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

function Stop-AllBridgeProcesses {
  $pids = @()
  $procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'us_socks_bridge.py' }
  foreach ($p in $procs) {
    $pids += [int]$p.ProcessId
    Stop-Process -Id ([int]$p.ProcessId) -Force -ErrorAction SilentlyContinue
  }
  return $pids
}

function Refresh-WinInet {
  if (-not ("WinInet.Native" -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
namespace WinInet {
  public class Native {
    [DllImport("wininet.dll", SetLastError = true)]
    public static extern bool InternetSetOption(IntPtr hInternet, int dwOption, IntPtr lpBuffer, int dwBufferLength);
  }
}
"@
  }
  [WinInet.Native]::InternetSetOption([IntPtr]::Zero, 37, [IntPtr]::Zero, 0) | Out-Null
  [WinInet.Native]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0) | Out-Null
}

if (-not (Test-Path "C:\integrator\us_socks_bridge.py")) {
  throw "Bridge script not found: C:\integrator\us_socks_bridge.py"
}

$python = $null
foreach ($p in @("C:\integrator\.venv\Scripts\python.exe","C:\integrator\venv\Scripts\python.exe")) {
  if (Test-Path $p) { $python = $p; break }
}
if (-not $python) { $python = "python" }

$envMap = @{}
if (Test-Path $EnvFile) {
  $envMap = Load-EnvMap $EnvFile
}
if ([string]::IsNullOrWhiteSpace($ProxyUser)) {
  $ProxyUser = $envMap["PROXY_USER"]
}
if ([string]::IsNullOrWhiteSpace($CredTarget)) {
  $CredTarget = $envMap["PROXY_CRED_TARGET"]
}
if ([string]::IsNullOrWhiteSpace($ProxyUser) -or [string]::IsNullOrWhiteSpace($CredTarget)) {
  throw "Missing required proxy auth values (ProxyUser/CredTarget or EnvFile)."
}

. "C:\integrator\proxy_credman.ps1"
$credObj = Get-CredManGenericCredential -TargetName $CredTarget
if ($null -eq $credObj -or [string]::IsNullOrWhiteSpace($credObj.Password) -or $credObj.UserName -ne $ProxyUser) {
  throw "Credential lookup failed for target: $CredTarget"
}

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$report = "C:\integrator\reports\system_us_proxy_enable_$ts.log"
$bridgeLog = "C:\integrator\reports\system_us_proxy_bridge_$ts.log"
$stateFile = "C:\integrator\reports\system_us_proxy_state.json"
$runtimeCfg = "C:\integrator\reports\system_us_proxy_runtime.json"
$runRegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$runName = "IntegratorUSProxyBridge"

"START $(Get-Date -Format s)" | Out-File -FilePath $report -Encoding utf8

$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
$oldProxyEnable = $null
$oldProxyServer = $null
$oldProxyOverride = $null
try { $oldProxyEnable = Get-ItemPropertyValue -Path $regPath -Name ProxyEnable -ErrorAction Stop } catch {}
try { $oldProxyServer = Get-ItemPropertyValue -Path $regPath -Name ProxyServer -ErrorAction Stop } catch {}
try { $oldProxyOverride = Get-ItemPropertyValue -Path $regPath -Name ProxyOverride -ErrorAction Stop } catch {}
$old = [pscustomobject]@{
  HTTP_PROXY = [Environment]::GetEnvironmentVariable("HTTP_PROXY", "User")
  HTTPS_PROXY = [Environment]::GetEnvironmentVariable("HTTPS_PROXY", "User")
  ALL_PROXY = [Environment]::GetEnvironmentVariable("ALL_PROXY", "User")
  NO_PROXY = [Environment]::GetEnvironmentVariable("NO_PROXY", "User")
  ProxyEnable = $oldProxyEnable
  ProxyServer = $oldProxyServer
  ProxyOverride = $oldProxyOverride
  RunValue = $null
}
$oldRunValue = $null
try {
  $oldRunValue = Get-ItemPropertyValue -Path $runRegPath -Name $runName -ErrorAction Stop
} catch {}
$currentLocalSocks = "socks=127.0.0.1:{0}" -f $BridgePort
$looksManaged = $false
if ($oldProxyEnable -eq 1 -and [string]$oldProxyServer -eq $currentLocalSocks) {
  $looksManaged = $true
}
if ([string]::IsNullOrWhiteSpace([string]$oldRunValue) -eq $false) {
  $looksManaged = $true
}
if ([string]$old.HTTP_PROXY -like "socks5://127.0.0.1:*") {
  $looksManaged = $true
}
if ([string]$old.HTTPS_PROXY -like "socks5://127.0.0.1:*") {
  $looksManaged = $true
}
if ([string]$old.ALL_PROXY -like "socks5://127.0.0.1:*") {
  $looksManaged = $true
}
if ($looksManaged) {
  $old.HTTP_PROXY = $null
  $old.HTTPS_PROXY = $null
  $old.ALL_PROXY = $null
  $old.NO_PROXY = $null
  $old.ProxyEnable = 0
  $old.ProxyServer = $null
  $old.ProxyOverride = $null
  $old.RunValue = $null
} else {
  $old.RunValue = $oldRunValue
}
$old | ConvertTo-Json | Out-File -FilePath $stateFile -Encoding utf8
"STATE_SAVED=$stateFile" | Out-File -FilePath $report -Append -Encoding utf8

$runtime = [pscustomobject]@{
  BridgePort = $BridgePort
  ProxyHost = $UpstreamHost
  ProxyPort = $UpstreamPort
  ProxyUser = $ProxyUser
  CredTarget = $CredTarget
  Python = $python
}
$runtime | ConvertTo-Json | Out-File -FilePath $runtimeCfg -Encoding utf8
"RUNTIME_CFG=$runtimeCfg" | Out-File -FilePath $report -Append -Encoding utf8

$killed = Stop-AllBridgeProcesses
if (@($killed).Count -gt 0) {
  "PREV_BRIDGE_STOP=$(@($killed) -join ',')" | Out-File -FilePath $report -Append -Encoding utf8
}

$env:BRIDGE_UP_USER = $ProxyUser
$env:BRIDGE_UP_PASS = $credObj.Password
$bridgeArgs = @(
  "C:\integrator\us_socks_bridge.py",
  "--listen-host", "127.0.0.1",
  "--listen-port", "$BridgePort",
  "--upstream-host", "$UpstreamHost",
  "--upstream-port", "$UpstreamPort",
  "--log-file", "$bridgeLog"
)
$bridgeProc = Start-Process -FilePath $python -ArgumentList $bridgeArgs -PassThru -WindowStyle Hidden
Remove-Item Env:\BRIDGE_UP_USER -ErrorAction SilentlyContinue
Remove-Item Env:\BRIDGE_UP_PASS -ErrorAction SilentlyContinue

"BRIDGE_PID=$($bridgeProc.Id)" | Out-File -FilePath $report -Append -Encoding utf8
"BRIDGE_LOG=$bridgeLog" | Out-File -FilePath $report -Append -Encoding utf8

if (-not (Wait-Port -hostName "127.0.0.1" -port $BridgePort -timeoutSec 12)) {
  throw "Bridge did not start in time."
}
"BRIDGE_READY=YES" | Out-File -FilePath $report -Append -Encoding utf8

$localSocks = "socks5://127.0.0.1:$BridgePort"
if ($SetUserEnv.IsPresent) {
  [Environment]::SetEnvironmentVariable("HTTP_PROXY", $localSocks, "User")
  [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $localSocks, "User")
  [Environment]::SetEnvironmentVariable("ALL_PROXY", $localSocks, "User")
  [Environment]::SetEnvironmentVariable("NO_PROXY", "localhost,127.0.0.1,::1", "User")
  $env:HTTP_PROXY = $localSocks
  $env:HTTPS_PROXY = $localSocks
  $env:ALL_PROXY = $localSocks
  $env:NO_PROXY = "localhost,127.0.0.1,::1"
  "ENV_USER_PROXY=SET" | Out-File -FilePath $report -Append -Encoding utf8
} else {
  "ENV_USER_PROXY=UNCHANGED" | Out-File -FilePath $report -Append -Encoding utf8
}

Set-ItemProperty -Path $regPath -Name ProxyEnable -Value 1 -Type DWord
Set-ItemProperty -Path $regPath -Name ProxyServer -Value ("socks=127.0.0.1:{0}" -f $BridgePort)
Set-ItemProperty -Path $regPath -Name ProxyOverride -Value "<local>;localhost;127.0.0.1"
Refresh-WinInet
"WININET_PROXY=SET socks=127.0.0.1:$BridgePort" | Out-File -FilePath $report -Append -Encoding utf8

$runCmd = "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\integrator\start_system_us_proxy_bridge.ps1"
Set-ItemProperty -Path $runRegPath -Name $runName -Value $runCmd
"BRIDGE_AUTOSTART=SET" | Out-File -FilePath $report -Append -Encoding utf8

$probe = (& curl.exe -sS -m 20 -x ("socks5://127.0.0.1:{0}" -f $BridgePort) "https://api.ipify.org?format=json" 2>&1) | Out-String
$probeExit = $LASTEXITCODE
"PROBE_EXIT=$probeExit" | Out-File -FilePath $report -Append -Encoding utf8
$probe | Out-File -FilePath $report -Append -Encoding utf8
if ($probeExit -ne 0) {
  throw "Probe failed through local bridge."
}

"END $(Get-Date -Format s)" | Out-File -FilePath $report -Append -Encoding utf8
Write-Output $report
