param(
  [Parameter(Mandatory = $false)][string]$EnvFile = "C:\integrator\.env.local",
  [Parameter(Mandatory = $false)][string]$CometExe = "C:\Users\egork\AppData\Local\Perplexity\Comet\Application\comet.exe",
  [Parameter(Mandatory = $false)][int]$BridgePort = 19080,
  [Parameter(Mandatory = $false)][switch]$ForceCloseExisting = $true
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

if (-not (Test-Path $EnvFile)) {
  throw "Env file not found: $EnvFile"
}
if (-not (Test-Path $CometExe)) {
  throw "Comet executable not found: $CometExe"
}

$python = $null
$pyCandidates = @(
  "C:\integrator\.venv\Scripts\python.exe",
  "C:\integrator\venv\Scripts\python.exe"
)
foreach ($p in $pyCandidates) {
  if (Test-Path $p) { $python = $p; break }
}
if (-not $python) {
  $python = "python"
}

$envMap = Load-EnvMap $EnvFile
$proxyHost = $envMap["PROXY_IP"]
$proxyPort = [int]$envMap["PROXY_PORT"]
$proxyUser = $envMap["PROXY_USER"]
$credTarget = $envMap["PROXY_CRED_TARGET"]

if ([string]::IsNullOrWhiteSpace($proxyHost) -or [string]::IsNullOrWhiteSpace($proxyUser) -or [string]::IsNullOrWhiteSpace($credTarget)) {
  throw "Missing required proxy values in $EnvFile"
}

. "C:\integrator\proxy_credman.ps1"
$credObj = Get-CredManGenericCredential -TargetName $credTarget
if ($null -eq $credObj -or [string]::IsNullOrWhiteSpace($credObj.Password) -or $credObj.UserName -ne $proxyUser) {
  throw "Credential lookup failed for target: $credTarget"
}

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$report = "C:\integrator\reports\comet_us_proxy_working_$ts.log"
$bridgeLog = "C:\integrator\reports\comet_us_proxy_bridge_$ts.log"
$stateFile = "C:\integrator\reports\comet_us_proxy_bridge_state.json"

"START $(Get-Date -Format s)" | Out-File -FilePath $report -Encoding utf8
"PYTHON=$python" | Out-File -FilePath $report -Append -Encoding utf8
"COMET_EXE=$CometExe" | Out-File -FilePath $report -Append -Encoding utf8
"UPSTREAM=$proxyHost`:$proxyPort" | Out-File -FilePath $report -Append -Encoding utf8
"BRIDGE=127.0.0.1`:$BridgePort" | Out-File -FilePath $report -Append -Encoding utf8

if (Test-Path $stateFile) {
  try {
    $state = Get-Content $stateFile -Raw | ConvertFrom-Json
    if ($state.bridge_pid) {
      Stop-Process -Id ([int]$state.bridge_pid) -Force -ErrorAction SilentlyContinue
      "PREV_BRIDGE_STOP=YES" | Out-File -FilePath $report -Append -Encoding utf8
    }
  } catch {}
}

$killedBridge = Stop-AllBridgeProcesses
if (@($killedBridge).Count -gt 0) {
  "PREV_BRIDGE_GLOBAL_STOP=$(@($killedBridge) -join ',')" | Out-File -FilePath $report -Append -Encoding utf8
}

if ($ForceCloseExisting.IsPresent) {
  Get-Process -Name "comet" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  "COMET_EXISTING=TERMINATED" | Out-File -FilePath $report -Append -Encoding utf8
}

$env:BRIDGE_UP_USER = $proxyUser
$env:BRIDGE_UP_PASS = $credObj.Password
$bridgeArgs = @(
  "C:\integrator\us_socks_bridge.py",
  "--listen-host", "127.0.0.1",
  "--listen-port", "$BridgePort",
  "--upstream-host", "$proxyHost",
  "--upstream-port", "$proxyPort",
  "--log-file", "$bridgeLog"
)
$bridgeProc = Start-Process -FilePath $python -ArgumentList $bridgeArgs -PassThru -WindowStyle Hidden
Remove-Item Env:\BRIDGE_UP_USER -ErrorAction SilentlyContinue
Remove-Item Env:\BRIDGE_UP_PASS -ErrorAction SilentlyContinue

"BRIDGE_PID=$($bridgeProc.Id)" | Out-File -FilePath $report -Append -Encoding utf8
"BRIDGE_LOG=$bridgeLog" | Out-File -FilePath $report -Append -Encoding utf8

if (-not (Wait-Port -hostName "127.0.0.1" -port $BridgePort -timeoutSec 12)) {
  "BRIDGE_READY=NO" | Out-File -FilePath $report -Append -Encoding utf8
  throw "Bridge did not start in time. See $bridgeLog and $report"
}
"BRIDGE_READY=YES" | Out-File -FilePath $report -Append -Encoding utf8

$probe = (& curl.exe -sS -m 20 -x ("socks5://127.0.0.1:{0}" -f $BridgePort) "https://api.ipify.org?format=json" 2>&1) | Out-String
$probeExit = $LASTEXITCODE
"BRIDGE_PROBE_EXIT=$probeExit" | Out-File -FilePath $report -Append -Encoding utf8
$probe | Out-File -FilePath $report -Append -Encoding utf8
if ($probeExit -ne 0) {
  throw "Bridge probe failed. See $report and $bridgeLog"
}

$cometArgs = @(
  "--proxy-server=socks5://127.0.0.1:$BridgePort",
  "--new-window",
  "https://ipinfo.io/json"
)
$cometProc = Start-Process -FilePath $CometExe -ArgumentList $cometArgs -PassThru
"COMET_LAUNCH=OK" | Out-File -FilePath $report -Append -Encoding utf8
"COMET_PID=$($cometProc.Id)" | Out-File -FilePath $report -Append -Encoding utf8

$state = [pscustomobject]@{
  started_at = (Get-Date).ToString("s")
  bridge_pid = $bridgeProc.Id
  bridge_port = $BridgePort
  bridge_log = $bridgeLog
  report = $report
}
$state | ConvertTo-Json | Out-File -FilePath $stateFile -Encoding utf8
"STATE_FILE=$stateFile" | Out-File -FilePath $report -Append -Encoding utf8
"END $(Get-Date -Format s)" | Out-File -FilePath $report -Append -Encoding utf8

Write-Output $report
