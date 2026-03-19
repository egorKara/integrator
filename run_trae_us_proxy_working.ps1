param(
  [Parameter(Mandatory = $false)][string]$TraeExe = "C:\Users\egork\AppData\Local\Programs\Trae\Trae.exe",
  [Parameter(Mandatory = $false)][int]$BridgePort = 19080,
  [Parameter(Mandatory = $false)][string]$UserDataDir = "C:\integrator\reports\trae_profile_proxy",
  [Parameter(Mandatory = $false)][switch]$ForceCloseExisting
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

if (-not (Test-Path $TraeExe)) {
  throw "Trae executable not found: $TraeExe"
}
if (-not (Test-Path $UserDataDir)) {
  New-Item -ItemType Directory -Path $UserDataDir -Force | Out-Null
}

$bridgeOk = $false
try {
  $probe = (& curl.exe -sS -m 20 -x ("socks5://127.0.0.1:{0}" -f $BridgePort) "https://api.ipify.org?format=json" 2>&1) | Out-String
  if ($LASTEXITCODE -eq 0 -and $probe.Length -gt 0) { $bridgeOk = $true }
} catch {}
if (-not $bridgeOk) {
  throw "Local bridge 127.0.0.1:$BridgePort is not ready."
}

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$report = "C:\integrator\reports\trae_us_proxy_working_$ts.log"
"START $(Get-Date -Format s)" | Out-File -FilePath $report -Encoding utf8
"TRAE_EXE=$TraeExe" | Out-File -FilePath $report -Append -Encoding utf8
"BRIDGE=127.0.0.1`:$BridgePort" | Out-File -FilePath $report -Append -Encoding utf8
"USER_DATA_DIR=$UserDataDir" | Out-File -FilePath $report -Append -Encoding utf8

if ($ForceCloseExisting.IsPresent) {
  Get-Process -Name "Trae" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  "TRAE_EXISTING=TERMINATED" | Out-File -FilePath $report -Append -Encoding utf8
}

$env:HTTP_PROXY = $null
$env:HTTPS_PROXY = $null
$env:ALL_PROXY = $null
$env:NO_PROXY = $null
$env:http_proxy = $null
$env:https_proxy = $null
$env:all_proxy = $null
$env:no_proxy = $null

$traeArgs = @(
  "--proxy-server=socks5://127.0.0.1:$BridgePort",
  "--disable-quic",
  "--user-data-dir=$UserDataDir"
)
$traeProc = Start-Process -FilePath $TraeExe -ArgumentList $traeArgs -PassThru
"TRAE_LAUNCH=OK" | Out-File -FilePath $report -Append -Encoding utf8
"TRAE_PID=$($traeProc.Id)" | Out-File -FilePath $report -Append -Encoding utf8
"TRAE_ARGS=$($traeArgs -join ' ')" | Out-File -FilePath $report -Append -Encoding utf8

Start-Sleep -Seconds 3
$proc = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "Trae.exe" } | Select-Object -First 1 ProcessId,CommandLine
if ($proc) {
  "TRAE_CMD=$($proc.CommandLine)" | Out-File -FilePath $report -Append -Encoding utf8
}

"END $(Get-Date -Format s)" | Out-File -FilePath $report -Append -Encoding utf8
Write-Output $report
