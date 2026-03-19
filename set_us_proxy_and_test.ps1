param(
  [Parameter(Mandatory = $true)][string]$ProxyHost,
  [Parameter(Mandatory = $true)][int]$ProxyPort,
  [Parameter(Mandatory = $true)][string]$ProxyUser,
  [Parameter(Mandatory = $false)][string]$ProxyPass = "",
  [Parameter(Mandatory = $false)][string]$ProxyProtocol = "http",
  [Parameter(Mandatory = $false)][string]$CredTarget = "",
  [Parameter(Mandatory = $false)][switch]$PersistUserProxyEnv
)

$ErrorActionPreference = "Stop"
$helper = "C:\integrator\proxy_credman.ps1"
if ([string]::IsNullOrWhiteSpace($ProxyPass)) {
  if ([string]::IsNullOrWhiteSpace($CredTarget)) {
    throw "ProxyPass is empty and CredTarget is not provided."
  }
  if (-not (Test-Path $helper)) {
    throw "CredMan helper not found: $helper"
  }
  . $helper
  $credObj = Get-CredManGenericCredential -TargetName $CredTarget
  if ($null -eq $credObj) {
    throw "Credential not found in Windows Credential Manager: $CredTarget"
  }
  if ($credObj.UserName -ne $ProxyUser) {
    throw "Credential user mismatch for $CredTarget"
  }
  $ProxyPass = $credObj.Password
}

$report = "C:\integrator\reports\us_proxy_apply_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$proxyUri = "${ProxyProtocol}://${ProxyHost}:${ProxyPort}"

"START $(Get-Date -Format s)" | Out-File -FilePath $report -Encoding utf8
"PROXY=$proxyUri" | Out-File -FilePath $report -Append -Encoding utf8

if ($ProxyProtocol -eq "http") {
  try {
    netsh winhttp set proxy $proxyUri | Out-File -FilePath $report -Append -Encoding utf8
  } catch {
    "WINHTTP_SET_FAIL: $($_.Exception.Message)" | Out-File -FilePath $report -Append -Encoding utf8
  }
} else {
  "WINHTTP_SKIP_FOR_PROTOCOL=$ProxyProtocol" | Out-File -FilePath $report -Append -Encoding utf8
}

if ($PersistUserProxyEnv.IsPresent) {
  $env:HTTP_PROXY = "${ProxyProtocol}://${ProxyUser}:${ProxyPass}@${ProxyHost}:${ProxyPort}"
  $env:HTTPS_PROXY = "${ProxyProtocol}://${ProxyUser}:${ProxyPass}@${ProxyHost}:${ProxyPort}"
  [Environment]::SetEnvironmentVariable("HTTP_PROXY", $env:HTTP_PROXY, "User")
  [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $env:HTTPS_PROXY, "User")
  "USER_ENV_SET=YES" | Out-File -FilePath $report -Append -Encoding utf8
} else {
  "USER_ENV_SET=NO" | Out-File -FilePath $report -Append -Encoding utf8
}

$cred = "{0}:{1}" -f $ProxyUser, $ProxyPass
& curl.exe -sS -m 25 -x $proxyUri --proxy-user $cred "https://api.ipify.org?format=json" | Out-File -FilePath $report -Append -Encoding utf8
if ($LASTEXITCODE -ne 0) {
  "IPIFY_FAIL_EXIT=$LASTEXITCODE" | Out-File -FilePath $report -Append -Encoding utf8
}
& curl.exe -sS -m 25 -x $proxyUri --proxy-user $cred "https://ipinfo.io/json" | Out-File -FilePath $report -Append -Encoding utf8
if ($LASTEXITCODE -ne 0) {
  "IPINFO_FAIL_EXIT=$LASTEXITCODE" | Out-File -FilePath $report -Append -Encoding utf8
}

"END $(Get-Date -Format s)" | Out-File -FilePath $report -Append -Encoding utf8
Write-Output $report
