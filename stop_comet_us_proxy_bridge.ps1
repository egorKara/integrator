$ErrorActionPreference = "Stop"

$stateFile = "C:\integrator\reports\comet_us_proxy_bridge_state.json"
$stopped = @()

if (Test-Path $stateFile) {
  try {
    $state = Get-Content $stateFile -Raw | ConvertFrom-Json
    if ($state.bridge_pid) {
      Stop-Process -Id ([int]$state.bridge_pid) -Force -ErrorAction SilentlyContinue
      $stopped += "BRIDGE_PID=$($state.bridge_pid)"
    }
  } catch {}
  Remove-Item $stateFile -Force -ErrorAction SilentlyContinue
}

$globalBridge = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'us_socks_bridge.py' }
foreach ($p in $globalBridge) {
  Stop-Process -Id ([int]$p.ProcessId) -Force -ErrorAction SilentlyContinue
  $stopped += "BRIDGE_GLOBAL_PID=$($p.ProcessId)"
}

Get-Process -Name "comet" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
$stopped += "COMET=TERMINATED"

$direct = Start-Process -FilePath "C:\Users\egork\AppData\Local\Perplexity\Comet\Application\comet.exe" -ArgumentList @("--new-window","https://ipinfo.io/json") -PassThru
$stopped += "COMET_DIRECT_PID=$($direct.Id)"

$stopped -join "; " | Write-Output
