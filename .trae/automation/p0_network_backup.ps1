param(
    [string]$OutputPath
)

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$reportsRoot = Join-Path $repoRoot "reports"
if (-not (Test-Path $reportsRoot)) {
    New-Item -ItemType Directory -Path $reportsRoot -Force | Out-Null
}
if (-not $OutputPath) {
    $OutputPath = Join-Path $reportsRoot "p0_network_backup_$timestamp.xml"
}

$dns = Get-DnsClientServerAddress
$ipInterfaces = Get-NetIPInterface
$ipv6Bindings = Get-NetAdapterBinding -ComponentID ms_tcpip6 | Select-Object Name, Enabled
$routes = Get-NetRoute
$winHttp = netsh winhttp show proxy
$winInet = Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' | Select-Object ProxyEnable, ProxyServer, ProxyOverride
$ics = Get-Service -Name SharedAccess -ErrorAction SilentlyContinue | Select-Object Status, Name, StartType

$state = [ordered]@{
    Timestamp = $timestamp
    Dns = $dns
    IPInterfaces = $ipInterfaces
    IPv6Bindings = $ipv6Bindings
    Routes = $routes
    WinHTTPProxy = $winHttp
    WinINETProxy = $winInet
    ICS = $ics
}

$state | Export-Clixml -Path $OutputPath
$OutputPath
