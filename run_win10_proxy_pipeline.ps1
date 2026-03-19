param(
  [Parameter(Mandatory = $false)][string]$EnvFile = "C:\integrator\.env.local"
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = "C:\integrator\reports\proxy_backup_$ts"
$report = "C:\integrator\reports\win10_proxy_pipeline_$ts.log"
$restoreScript = "C:\integrator\restore_win10_inet_access.ps1"

New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

function Write-Report([string]$line) {
  $line | Out-File -FilePath $report -Append -Encoding utf8
}

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

function Get-JsonIp([string]$text) {
  try {
    return ($text | ConvertFrom-Json).ip
  } catch {
    return $null
  }
}

function Invoke-CurlCapture {
  param(
    [Parameter(Mandatory = $true)][string[]]$Args
  )

  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $raw = (& curl.exe @Args 2>&1) | Out-String
    $code = $LASTEXITCODE
  }
  finally {
    $ErrorActionPreference = $prev
  }
  [pscustomobject]@{
    Output = $raw
    ExitCode = $code
  }
}

"START $(Get-Date -Format s)" | Out-File -FilePath $report -Encoding utf8
Write-Report "BACKUP_DIR=$backupDir"

if (-not (Test-Path $EnvFile)) {
  throw "Env file not found: $EnvFile"
}

$envMap = Load-EnvMap $EnvFile
$proxyHost = $envMap["PROXY_IP"]
$proxyPort = [int]$envMap["PROXY_PORT"]
$proxyUser = $envMap["PROXY_USER"]
$proxyProtocol = $envMap["PROXY_PROTOCOL"]
$credTarget = $envMap["PROXY_CRED_TARGET"]

if ([string]::IsNullOrWhiteSpace($proxyHost) -or [string]::IsNullOrWhiteSpace($proxyUser) -or [string]::IsNullOrWhiteSpace($proxyProtocol) -or [string]::IsNullOrWhiteSpace($credTarget)) {
  throw "Missing required proxy fields in $EnvFile"
}

Copy-Item -Path $EnvFile -Destination "$backupDir\env.local.backup" -Force
Copy-Item -Path "C:\integrator\set_us_proxy_and_test.ps1" -Destination "$backupDir\set_us_proxy_and_test.ps1.backup" -Force

reg export "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" "$backupDir\internet_settings_before.reg" /y | Out-Null
netsh winhttp dump | Out-File -FilePath "$backupDir\winhttp_before_dump.txt" -Encoding utf8
netsh winhttp show proxy | Out-File -FilePath "$backupDir\winhttp_before_show.txt" -Encoding utf8
ipconfig /all | Out-File -FilePath "$backupDir\ipconfig_before.txt" -Encoding utf8
route print | Out-File -FilePath "$backupDir\route_before.txt" -Encoding utf8
Get-DnsClientServerAddress | Format-Table -AutoSize | Out-File -FilePath "$backupDir\dns_before.txt" -Encoding utf8

$envBackup = @{
  HTTP_PROXY_PRESENT = -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("HTTP_PROXY", "User"))
  HTTPS_PROXY_PRESENT = -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("HTTPS_PROXY", "User"))
}
$envBackup | ConvertTo-Json | Out-File -FilePath "$backupDir\user_env_proxy_before.json" -Encoding utf8

[Environment]::SetEnvironmentVariable("HTTP_PROXY", $null, "User")
[Environment]::SetEnvironmentVariable("HTTPS_PROXY", $null, "User")

Write-Report "APPLY_PROXY_START"
$applyLog = powershell -ExecutionPolicy Bypass -File "C:\integrator\set_us_proxy_and_test.ps1" -ProxyHost $proxyHost -ProxyPort $proxyPort -ProxyUser $proxyUser -ProxyProtocol $proxyProtocol -CredTarget $credTarget
Write-Report "APPLY_LOG=$applyLog"

$proxyUri = "{0}://{1}:{2}" -f $proxyProtocol, $proxyHost, $proxyPort

. "C:\integrator\proxy_credman.ps1"
$credObj = Get-CredManGenericCredential -TargetName $credTarget
if ($null -eq $credObj -or $credObj.UserName -ne $proxyUser -or [string]::IsNullOrWhiteSpace($credObj.Password)) {
  throw "Credential lookup failed for target: $credTarget"
}
$cred = "{0}:{1}" -f $proxyUser, $credObj.Password

$direct = Invoke-CurlCapture -Args @("-sS","-m","20","https://api.ipify.org?format=json")
$proxy = Invoke-CurlCapture -Args @("-sS","-m","25","-x",$proxyUri,"--proxy-user",$cred,"https://api.ipify.org?format=json")
$ipInfo = Invoke-CurlCapture -Args @("-sS","-m","25","-x",$proxyUri,"--proxy-user",$cred,"https://ipinfo.io/json")

$directRaw = $direct.Output
$proxyRaw = $proxy.Output
$ipInfoRaw = $ipInfo.Output

$directRaw | Out-File -FilePath "$backupDir\verify_direct_ipify.txt" -Encoding utf8
$proxyRaw | Out-File -FilePath "$backupDir\verify_proxy_ipify.txt" -Encoding utf8
$ipInfoRaw | Out-File -FilePath "$backupDir\verify_proxy_ipinfo.txt" -Encoding utf8

$directIp = Get-JsonIp $directRaw
$proxyIp = Get-JsonIp $proxyRaw

Write-Report "VERIFY_DIRECT_IP=$directIp"
Write-Report "VERIFY_DIRECT_EXIT=$($direct.ExitCode)"
Write-Report "VERIFY_PROXY_IP=$proxyIp"
Write-Report "VERIFY_PROXY_EXIT=$($proxy.ExitCode)"
Write-Report "VERIFY_IPINFO_EXIT=$($ipInfo.ExitCode)"
if ($proxyIp) {
  Write-Report "VERIFY_PROXY_STATUS=OK"
} else {
  Write-Report "VERIFY_PROXY_STATUS=FAIL"
}

Write-Report "RESTORE_SCRIPT=$restoreScript"
Write-Report "RESTORE_CMD=powershell -ExecutionPolicy Bypass -File $restoreScript -BackupDir `"$backupDir`""
Write-Report "END $(Get-Date -Format s)"

Write-Output $report
