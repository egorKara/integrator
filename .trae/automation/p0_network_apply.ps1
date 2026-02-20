param(
    [string]$BackupPath
)

$rules = @(
    "P0-Block-DNS-UDP-Ethernet",
    "P0-Block-DNS-TCP-Ethernet"
)

foreach ($rule in $rules) {
    Get-NetFirewallRule -DisplayName $rule -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
}

New-NetFirewallRule -DisplayName "P0-Block-DNS-UDP-Ethernet" -Direction Outbound -Action Block -Protocol UDP -RemotePort 53 -InterfaceAlias "Ethernet" | Out-Null
New-NetFirewallRule -DisplayName "P0-Block-DNS-TCP-Ethernet" -Direction Outbound -Action Block -Protocol TCP -RemotePort 53 -InterfaceAlias "Ethernet" | Out-Null

Set-NetIPInterface -AddressFamily IPv4 -Forwarding Disabled
Set-NetIPInterface -AddressFamily IPv6 -Forwarding Disabled

Disable-NetAdapterBinding -Name "Ethernet" -ComponentID ms_tcpip6 -ErrorAction SilentlyContinue

if ($BackupPath -and (Test-Path $BackupPath)) {
    $backup = Import-Clixml -Path $BackupPath
}

"Applied P0 changes"
