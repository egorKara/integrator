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
    $OutputPath = Join-Path $reportsRoot "p0_network_check_after_$timestamp.log"
}

"P0 Network Check AFTER - $timestamp" | Out-File -FilePath $OutputPath -Encoding utf8
"=== Host ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
hostname | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== Date ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
Get-Date | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== Routes ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
Get-NetRoute | Sort-Object -Property DestinationPrefix,RouteMetric | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== IP Interfaces ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
Get-NetIPInterface | Sort-Object -Property InterfaceMetric | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== IP Config ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
Get-NetIPAddress | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== DNS Client Server Addresses ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
Get-DnsClientServerAddress | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== DNS Suffix Search List ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
Get-DnsClientGlobalSetting | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== DNS Resolve (ifconfig.me) ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
Resolve-DnsName ifconfig.me -ErrorAction SilentlyContinue | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== IPv6 Interfaces ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
Get-NetIPInterface -AddressFamily IPv6 | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== IPv6 Addresses ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
Get-NetIPAddress -AddressFamily IPv6 | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== IP Forwarding ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
Get-NetIPInterface | Select-Object ifIndex,InterfaceAlias,AddressFamily,Forwarding | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== ICS Service ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
Get-Service -Name SharedAccess -ErrorAction SilentlyContinue | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== Netsh Routing ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
netsh interface ipv4 show interface | Out-File -FilePath $OutputPath -Append -Encoding utf8
netsh interface ipv4 show route | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== WinHTTP Proxy ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
netsh winhttp show proxy | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== WinINET Proxy ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' | Select-Object ProxyEnable,ProxyServer,ProxyOverride | Out-File -FilePath $OutputPath -Append -Encoding utf8
"=== Firewall Rules (P0) ===" | Out-File -FilePath $OutputPath -Append -Encoding utf8
Get-NetFirewallRule -DisplayName "P0-Block-DNS-UDP-Ethernet","P0-Block-DNS-TCP-Ethernet" -ErrorAction Ignore | Out-File -FilePath $OutputPath -Append -Encoding utf8
$OutputPath
