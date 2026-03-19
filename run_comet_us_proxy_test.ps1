param(
  [Parameter(Mandatory = $false)][string]$EnvFile = "C:\integrator\.env.local",
  [Parameter(Mandatory = $false)][string]$CometExe = "C:\Users\egork\AppData\Local\Perplexity\Comet\Application\comet.exe",
  [Parameter(Mandatory = $false)][switch]$ForceCloseExisting = $true,
  [Parameter(Mandatory = $false)][switch]$LaunchAnyway
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

function Invoke-CurlCapture {
  param(
    [Parameter(Mandatory = $true)][string[]]$Args
  )
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $raw = (& curl.exe @Args 2>&1) | Out-String
    $code = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $prev
  }
  [pscustomobject]@{
    ExitCode = $code
    Output = $raw
  }
}

if (-not (Test-Path $EnvFile)) {
  throw "Env file not found: $EnvFile"
}
if (-not (Test-Path $CometExe)) {
  throw "Comet executable not found: $CometExe"
}

$envMap = Load-EnvMap $EnvFile
$proxyHost = $envMap["PROXY_IP"]
$proxyPort = $envMap["PROXY_PORT"]
$proxyUser = $envMap["PROXY_USER"]
$proxyProtocol = $envMap["PROXY_PROTOCOL"]
$credTarget = $envMap["PROXY_CRED_TARGET"]

if ([string]::IsNullOrWhiteSpace($proxyHost) -or [string]::IsNullOrWhiteSpace($proxyPort) -or [string]::IsNullOrWhiteSpace($proxyUser) -or [string]::IsNullOrWhiteSpace($proxyProtocol) -or [string]::IsNullOrWhiteSpace($credTarget)) {
  throw "Missing required proxy values in $EnvFile"
}

. "C:\integrator\proxy_credman.ps1"
$credObj = Get-CredManGenericCredential -TargetName $credTarget
if ($null -eq $credObj -or [string]::IsNullOrWhiteSpace($credObj.Password) -or $credObj.UserName -ne $proxyUser) {
  throw "Credential lookup failed for target: $credTarget"
}

$proxyUri = "{0}://{1}:{2}" -f $proxyProtocol, $proxyHost, $proxyPort
$proxyAuthUri = "{0}://{1}:{2}@{3}:{4}" -f $proxyProtocol, $proxyUser, $credObj.Password, $proxyHost, $proxyPort
$cred = "{0}:{1}" -f $proxyUser, $credObj.Password

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$report = "C:\integrator\reports\comet_us_proxy_test_$ts.log"
"START $(Get-Date -Format s)" | Out-File -FilePath $report -Encoding utf8
"COMET_EXE=$CometExe" | Out-File -FilePath $report -Append -Encoding utf8
"PROXY_URI=$proxyUri" | Out-File -FilePath $report -Append -Encoding utf8

$proxyTest = Invoke-CurlCapture -Args @("-sS","-m","25","-x",$proxyUri,"--proxy-user",$cred,"https://api.ipify.org?format=json")
$ipInfo = Invoke-CurlCapture -Args @("-sS","-m","25","-x",$proxyUri,"--proxy-user",$cred,"https://ipinfo.io/json")
$proxyNoAuth = Invoke-CurlCapture -Args @("-sS","-m","12","-x",$proxyUri,"https://api.ipify.org?format=json")

"VERIFY_PROXY_EXIT=$($proxyTest.ExitCode)" | Out-File -FilePath $report -Append -Encoding utf8
$proxyTest.Output | Out-File -FilePath $report -Append -Encoding utf8
"VERIFY_IPINFO_EXIT=$($ipInfo.ExitCode)" | Out-File -FilePath $report -Append -Encoding utf8
$ipInfo.Output | Out-File -FilePath $report -Append -Encoding utf8
"VERIFY_PROXY_NOAUTH_EXIT=$($proxyNoAuth.ExitCode)" | Out-File -FilePath $report -Append -Encoding utf8
$proxyNoAuth.Output | Out-File -FilePath $report -Append -Encoding utf8

if ($proxyTest.ExitCode -ne 0) {
  "COMET_LAUNCH=SKIPPED_PROXY_FAIL" | Out-File -FilePath $report -Append -Encoding utf8
  "END $(Get-Date -Format s)" | Out-File -FilePath $report -Append -Encoding utf8
  throw "Proxy verification failed. See $report"
}

if ($proxyNoAuth.ExitCode -ne 0 -and -not $LaunchAnyway.IsPresent) {
  "COMET_LAUNCH=SKIPPED_AUTH_PROXY_CHROMIUM_LIMIT" | Out-File -FilePath $report -Append -Encoding utf8
  "END $(Get-Date -Format s)" | Out-File -FilePath $report -Append -Encoding utf8
  throw "Authenticated proxy detected. Chromium-based Comet may not load tabs with --proxy-server credentials. Use local proxy bridge or run with -LaunchAnyway."
}

if ($ForceCloseExisting.IsPresent) {
  Get-Process -Name "comet" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  "COMET_EXISTING=TERMINATED" | Out-File -FilePath $report -Append -Encoding utf8
}

$args = @(
  "--proxy-server=$proxyAuthUri",
  "--new-window",
  "https://ipinfo.io/json"
)

$proc = Start-Process -FilePath $CometExe -ArgumentList $args -PassThru
"COMET_LAUNCH=OK" | Out-File -FilePath $report -Append -Encoding utf8
"COMET_PID=$($proc.Id)" | Out-File -FilePath $report -Append -Encoding utf8
"CHECK_URL=https://ipinfo.io/json" | Out-File -FilePath $report -Append -Encoding utf8
"END $(Get-Date -Format s)" | Out-File -FilePath $report -Append -Encoding utf8

Write-Output $report
