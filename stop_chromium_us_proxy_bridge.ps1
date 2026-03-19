param(
  [Parameter(Mandatory = $false)][string]$StateFile = "C:\integrator\reports\chromium_us_proxy_state.json",
  [Parameter(Mandatory = $false)][switch]$StopAllBridgeProcesses = $true
)

$ErrorActionPreference = "Stop"

function Stop-AllBridgeProcesses {
  $pids = @()
  $procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'us_socks_bridge.py' }
  foreach ($p in $procs) {
    $pids += [int]$p.ProcessId
    Stop-Process -Id ([int]$p.ProcessId) -Force -ErrorAction SilentlyContinue
  }
  return $pids
}

$stopped = @()
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$report = "C:\integrator\reports\chromium_us_proxy_stop_$ts.log"
"START $(Get-Date -Format s)" | Out-File -FilePath $report -Encoding utf8
"STATE_FILE=$StateFile" | Out-File -FilePath $report -Append -Encoding utf8

if (Test-Path $StateFile) {
  try {
    $state = Get-Content $StateFile -Raw | ConvertFrom-Json
    if ($state.browser_pid) {
      Stop-Process -Id ([int]$state.browser_pid) -Force -ErrorAction SilentlyContinue
      $stopped += "BROWSER_PID=$($state.browser_pid)"
    }
    if ($state.bridge_pid) {
      Stop-Process -Id ([int]$state.bridge_pid) -Force -ErrorAction SilentlyContinue
      $stopped += "BRIDGE_PID=$($state.bridge_pid)"
    }
  } catch {}
  Remove-Item $StateFile -Force -ErrorAction SilentlyContinue
  $stopped += "STATE_FILE_REMOVED=YES"
} else {
  $stopped += "STATE_FILE_MISSING=YES"
}

if ($StopAllBridgeProcesses.IsPresent) {
  $killed = Stop-AllBridgeProcesses
  if (@($killed).Count -gt 0) {
    $stopped += "BRIDGE_GLOBAL_STOP=$(@($killed) -join ',')"
  }
}

($stopped -join "`n") | Out-File -FilePath $report -Append -Encoding utf8
"END $(Get-Date -Format s)" | Out-File -FilePath $report -Append -Encoding utf8
Write-Output $report
