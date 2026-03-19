param(
  [Parameter(Mandatory = $true)][string]$BackupDir
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupDir)) {
  throw "Backup directory not found: $BackupDir"
}

$regFile = Join-Path $BackupDir "internet_settings_before.reg"
$winhttpDump = Join-Path $BackupDir "winhttp_before_dump.txt"
$envJson = Join-Path $BackupDir "user_env_proxy_before.json"

if (Test-Path $regFile) {
  reg import $regFile | Out-Null
}

if (Test-Path $winhttpDump) {
  netsh -f $winhttpDump | Out-Null
} else {
  netsh winhttp reset proxy | Out-Null
}

if (Test-Path $envJson) {
  $saved = Get-Content $envJson -Raw | ConvertFrom-Json
  [Environment]::SetEnvironmentVariable("HTTP_PROXY", $null, "User")
  [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $null, "User")
  if ($saved.HTTP_PROXY_PRESENT -or $saved.HTTPS_PROXY_PRESENT) {
    Write-Output "INFO: User proxy env was present before backup and is intentionally not restored for secret hygiene."
  }
}

ipconfig /flushdns | Out-Null
Write-Output "RESTORE_OK"
