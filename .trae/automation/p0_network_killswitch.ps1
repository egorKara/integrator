param(
    [ValidateSet("Enable", "Disable")] [string]$Mode = "Enable",
    [string]$InterfaceAlias = "Ethernet",
    [string]$TunnelAlias = "wgo0",
    [string]$BackupPath,
    [string]$LogPath
)

$ruleName = "P0-Block-All-Ethernet"
$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
if (-not $LogPath) {
    $LogPath = "C:\Users\egork\Documents\trae_projects\integrator\reports\p0_killswitch_$((Get-Date).ToString('yyyyMMdd_HHmmss')).log"
}

"$timestamp Mode=$Mode Interface=$InterfaceAlias Tunnel=$TunnelAlias" | Out-File -FilePath $LogPath -Append -Encoding utf8

if ($Mode -eq "Enable") {
    Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName $ruleName -Direction Outbound -Action Block -InterfaceAlias $InterfaceAlias -Profile Any | Out-Null
    $routes = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -InterfaceAlias $InterfaceAlias -ErrorAction SilentlyContinue
    if ($routes) {
        $routes | Remove-NetRoute -Confirm:$false -ErrorAction SilentlyContinue
    }
    "Kill-switch enabled"
} else {
    Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
    if ($BackupPath -and (Test-Path $BackupPath)) {
        $backup = Import-Clixml -Path $BackupPath
        foreach ($route in $backup.Routes) {
            if ($route.DestinationPrefix -eq "0.0.0.0/0" -and $route.ifIndex -and $route.NextHop) {
                New-NetRoute -DestinationPrefix $route.DestinationPrefix -InterfaceIndex $route.ifIndex -NextHop $route.NextHop -ErrorAction SilentlyContinue | Out-Null
            }
        }
    }
    "Kill-switch disabled"
}
