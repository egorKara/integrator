param(
  [Parameter(Mandatory = $false)][string]$EnvFile = "C:\integrator\.env.local",
  [Parameter(Mandatory = $false)][string]$BrowserExe = "",
  [Parameter(Mandatory = $false)][string]$Url = "https://translate.google.com/",
  [Parameter(Mandatory = $false)][int]$BridgePort = 19080,
  [Parameter(Mandatory = $false)][string]$UpstreamHost = "208.214.160.156",
  [Parameter(Mandatory = $false)][int]$UpstreamPort = 50101,
  [Parameter(Mandatory = $false)][string]$ProxyUser = "",
  [Parameter(Mandatory = $false)][string]$CredTarget = "",
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

function Resolve-BrowserExe([string]$candidate) {
  if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path $candidate)) {
    return $candidate
  }
  $candidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles(x86)\Microsoft\Edge\Application\msedge.exe"
  )
  foreach ($p in $candidates) {
    if (Test-Path $p) { return $p }
  }
  throw "Browser executable not found. Provide -BrowserExe."
}

if (-not (Test-Path "C:\integrator\us_socks_bridge.py")) {
  throw "Bridge script not found: C:\integrator\us_socks_bridge.py"
}
if (-not (Test-Path "C:\integrator\proxy_credman.ps1")) {
  throw "CredMan helper not found: C:\integrator\proxy_credman.ps1"
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

$BrowserExe = Resolve-BrowserExe $BrowserExe
$browserProcName = [IO.Path]::GetFileNameWithoutExtension($BrowserExe)

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$report = "C:\integrator\reports\chromium_us_proxy_working_$ts.log"
$bridgeLog = "C:\integrator\reports\chromium_us_proxy_bridge_$ts.log"
$stateFile = "C:\integrator\reports\chromium_us_proxy_state.json"

"START $(Get-Date -Format s)" | Out-File -FilePath $report -Encoding utf8
"BROWSER_EXE=$BrowserExe" | Out-File -FilePath $report -Append -Encoding utf8
"URL=$Url" | Out-File -FilePath $report -Append -Encoding utf8
"UPSTREAM=$UpstreamHost`:$UpstreamPort" | Out-File -FilePath $report -Append -Encoding utf8
"BRIDGE=127.0.0.1`:$BridgePort" | Out-File -FilePath $report -Append -Encoding utf8
"PYTHON=$python" | Out-File -FilePath $report -Append -Encoding utf8
"CRED_TARGET=$CredTarget" | Out-File -FilePath $report -Append -Encoding utf8
"PROXY_USER=$ProxyUser" | Out-File -FilePath $report -Append -Encoding utf8

$killedBridge = Stop-AllBridgeProcesses
if (@($killedBridge).Count -gt 0) {
  "PREV_BRIDGE_STOP=$(@($killedBridge) -join ',')" | Out-File -FilePath $report -Append -Encoding utf8
}

if ($ForceCloseExisting.IsPresent) {
  Get-Process -Name $browserProcName -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  "BROWSER_EXISTING=TERMINATED" | Out-File -FilePath $report -Append -Encoding utf8
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

$browserArgs = @(
  "--proxy-server=socks5://127.0.0.1:$BridgePort",
  "--proxy-bypass-list=<-loopback>",
  "--disable-quic",
  "--dns-over-https-mode=off",
  "--new-window",
  $Url
)
$browserProc = Start-Process -FilePath $BrowserExe -ArgumentList $browserArgs -PassThru
"BROWSER_LAUNCH=OK" | Out-File -FilePath $report -Append -Encoding utf8
"BROWSER_PID=$($browserProc.Id)" | Out-File -FilePath $report -Append -Encoding utf8

$state = [pscustomobject]@{
  started_at = (Get-Date).ToString("s")
  browser_exe = $BrowserExe
  browser_pid = $browserProc.Id
  bridge_pid = $bridgeProc.Id
  bridge_port = $BridgePort
  bridge_log = $bridgeLog
  report = $report
}
$state | ConvertTo-Json | Out-File -FilePath $stateFile -Encoding utf8
"STATE_FILE=$stateFile" | Out-File -FilePath $report -Append -Encoding utf8
"END $(Get-Date -Format s)" | Out-File -FilePath $report -Append -Encoding utf8

Write-Output $report
