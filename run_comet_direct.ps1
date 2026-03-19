param(
  [Parameter(Mandatory = $false)][string]$CometExe = "C:\Users\egork\AppData\Local\Perplexity\Comet\Application\comet.exe",
  [Parameter(Mandatory = $false)][switch]$ForceCloseExisting = $true
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $CometExe)) {
  throw "Comet executable not found: $CometExe"
}

if ($ForceCloseExisting.IsPresent) {
  Get-Process -Name "comet" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}

$proc = Start-Process -FilePath $CometExe -ArgumentList @("--new-window","https://ipinfo.io/json") -PassThru
Write-Output "COMET_DIRECT_OK PID=$($proc.Id)"
