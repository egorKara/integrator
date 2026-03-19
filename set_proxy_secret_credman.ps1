param(
  [Parameter(Mandatory = $false)][string]$EnvFile = "C:\integrator\.env.local",
  [Parameter(Mandatory = $false)][string]$TargetName = "integrator/proxy/us",
  [Parameter(Mandatory = $false)][string]$ProxyUser
)

$ErrorActionPreference = "Stop"
$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8

if (-not $ProxyUser) {
  if (Test-Path $EnvFile) {
    $envMap = @{}
    Get-Content $EnvFile | ForEach-Object {
      if ($_ -match '^[^#].*=') {
        $k, $v = $_.Split('=', 2)
        $envMap[$k.Trim()] = $v.Trim()
      }
    }
    $ProxyUser = $envMap["PROXY_USER"]
  }
}

if ([string]::IsNullOrWhiteSpace($ProxyUser)) {
  throw "Proxy user is required."
}

$securePass = Read-Host "Enter proxy password for PROXY_USER=$ProxyUser" -AsSecureString
$plain = [Runtime.InteropServices.Marshal]::PtrToStringUni([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePass))
if ([string]::IsNullOrWhiteSpace($plain)) {
  throw "Empty password is not allowed."
}

cmdkey /generic:$TargetName /user:$ProxyUser /pass:$plain | Out-Null
Write-Output "CREDMAN_SAVED Target=$TargetName User=$ProxyUser"
